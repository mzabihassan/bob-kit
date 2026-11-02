#!/usr/bin/env python3
"""Check the playbook's Markdown pages and turn them into a Confluence Cloud copy-paste bundle.

Input: a folder of Markdown files holding the pages; a file holds one page or several, each page
starting with a front matter block (`title`, optional `id`, `parent` and `labels`); pages link to
each other with `[text](page:<id>)`. Output, in --out:

- playbook.html — every page rendered, with a navigation tree and, per page, buttons that copy
  the title and the body as rich HTML ready to paste into the Confluence Cloud editor: headings,
  tables, lists, links, code blocks with their language, info/tip/warning panels, expands and
  status lozenges become native Confluence elements. Mermaid diagrams are rendered in the browser
  and pasted as images, with PNG/SVG downloads as a fallback.
- manifest.json — titles, hierarchy, labels and a hash per page; on the next run, the script
  lists which pages are new, changed or removed, so only those are updated in Confluence.

Validation (always run; exit code 1 on errors): front matter, unique titles, a single root page,
parents and page links that resolve, unclosed code fences, secrets (never written to the bundle),
leftover TODOs, empty sections, code blocks without a language, overlong pages, pages without any
file reference, and paragraphs duplicated across pages.

Standard library only; reads the pages, writes only into --out.

Examples:
  python3 confluence_export.py docs/playbook
  python3 confluence_export.py docs/playbook --out /tmp/playbook-confluence \\
      --source-url https://gitlab.example.com/group/app/-/blob/3f2a9c1
  python3 confluence_export.py docs/playbook --check     # validation only
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
from collections import Counter, OrderedDict

MERMAID_JS = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
PANELS = {"NOTE": "info", "INFO": "info", "TIP": "tip", "IMPORTANT": "note", "WARNING": "warning",
          "CAUTION": "error", "DANGER": "error", "SUCCESS": "success"}
PANEL_ICON = {"info": "ℹ️", "tip": "💡", "note": "📝", "warning": "⚠️", "error": "⛔", "success": "✅"}
STATUS_COLORS = {"neutral", "purple", "blue", "red", "yellow", "green"}
LANG_ALIASES = {"sh": "bash", "shell": "bash", "console": "bash", "zsh": "bash", "yml": "yaml", "ts": "typescript",
                "js": "javascript", "dockerfile": "docker", "text": "", "txt": "", "plain": "", "plaintext": "",
                "properties": "properties", "kt": "kotlin", "ps1": "powershell", "html": "html", "xml": "xml"}
SECRETS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitLab token", re.compile(r"\bgl(?:pat|dt|rt|cbt|ptt|ft)-[0-9A-Za-z_-]{20,}")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[0-9A-Za-z]{36,}|github_pat_[0-9A-Za-z_]{22,})")),
    ("Atlassian API token", re.compile(r"\bATATT3[0-9A-Za-z_=-]{30,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("credentials in URL", re.compile(r"\b[a-z][a-z0-9+.-]{1,20}://[^\s:/@'\"<>]{1,64}:(?!<)[^\s@/'\"<>]{3,}@")),
    ("password or key value", re.compile(r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|client[_-]?secret|token)\b[\"']?\s*[:=]\s*[\"']?"
                                          r"(?!<|\$\{|\{\{|\*\*\*|xxx|changeme|example|dummy|your|\.\.\.|…)[A-Za-z0-9+/=_\-!@#%^&]{12,}")),
]
TODO = re.compile(r"\b(TODO|FIXME|XXX|lorem ipsum)\b", re.I)


# ------------------------------------------------------------------ pages
def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def split_pages(path):
    """A file holds one page, or several pages each starting with a front matter block that has a title."""
    raw = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    starts = [m.start() for m in re.finditer(r"^---\n(?:(?!---\n).*\n){0,12}?title:.*\n(?:(?!---\n).*\n){0,12}?---\n", raw, re.M)]
    if not starts or starts[0] != 0:
        starts = [0] + starts
    return [(raw[a:b], raw.count("\n", 0, a)) for a, b in zip(starts, starts[1:] + [len(raw)]) if raw[a:b].strip()]


class Page:
    def __init__(self, path, raw, single, first_line=0):
        self.path, self.file, self.single = path, os.path.basename(path), single
        self.meta, self.body, self.line0 = {}, raw, first_line
        m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
        if m:
            for line in m.group(1).splitlines():
                k, sep, v = line.partition(":")
                if sep:
                    self.meta[k.strip().lower()] = v.strip().strip("\"'")
            self.body = raw[m.end():]
            self.line0 += raw.count("\n", 0, m.end())
        self.title = self.meta.get("title", "")
        self.parent = self.meta.get("parent", "")
        self.id = self.meta.get("id") or (slugify(os.path.splitext(self.file)[0]) if single else slugify(self.title))
        self.slug = self.id
        self.where = self.file if single else f"{self.file} «{self.title or '?'}»"
        self.labels = [x.strip() for x in self.meta.get("labels", "").split(",") if x.strip()]
        self.hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        self.words = len(re.findall(r"\w+", self.body))


# ------------------------------------------------------------------ Markdown -> HTML
class Renderer:
    """Markdown subset -> Confluence-friendly HTML. mode 'preview' (browser) or 'paste' (Confluence editor)."""

    def __init__(self, pages, page, mode, sources, space_url):
        self.by_file = {p.file: p for p in pages if p.single}
        self.by_file.update({f"page:{p.id}": p for p in pages})
        self.page, self.mode, self.sources, self.space_url = page, mode, sources, space_url
        self.diagrams = []
        self.last_heading = page.title

    # ---- inline
    def inline(self, text):
        out, pos = [], 0
        for m in re.finditer(r"(`+)(.+?)\1", text):
            out.append(self._inline_text(text[pos:m.start()]))
            out.append(self._code_span(m.group(2).strip()))
            pos = m.end()
        out.append(self._inline_text(text[pos:]))
        return "".join(out)

    def _code_span(self, code):
        link = self._source_link(code)
        # Confluence's code mark excludes every other mark: a linked file reference is pasted as a plain link.
        return f'<a href="{html.escape(link)}">{html.escape(code)}</a>' if link else f"<code>{html.escape(code)}</code>"

    def _source_link(self, ref):
        if not self.sources or " " in ref or not re.search(r"[\w-]\.[A-Za-z]{1,10}(:\d+(-\d+)?)?$|/", ref):
            return None
        label, path = None, ref
        if re.match(r"^[\w.-]+:[\w./-]", ref) and ref.split(":", 1)[0] in self.sources:
            label, path = ref.split(":", 1)
        base = self.sources.get(label) or self.sources.get(None)
        if not base or path.startswith(("http", "/", "-")) or "://" in path:
            return None
        m = re.match(r"^(.*?)(?::(\d+)(?:-(\d+))?)?$", path)
        file_path, start, end = m.group(1), m.group(2), m.group(3)
        anchor = f"#L{start}" + (f"-{end}" if end else "") if start else ""
        clean = re.sub(r"^(\./)+", "", file_path)
        return f"{base.rstrip('/')}/{clean}{anchor}"

    def _inline_text(self, t):
        if not t:
            return ""
        t = html.escape(t, quote=False)
        t = re.sub(r"\{\{status:(\w+):([^}]+)\}\}", self._status, t)
        t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}"/>', t)
        t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)", self._link, t)
        t = re.sub(r"&lt;(https?://[^\s&]+)&gt;", r'<a href="\1">\1</a>', t)
        t = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"<em>\1</em>", t)
        t = re.sub(r"(?<![\w])_(?=\S)(.+?)(?<=\S)_(?![\w])", r"<em>\1</em>", t)
        t = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"<s>\1</s>", t)
        return t

    def _status(self, m):
        color = m.group(1).lower() if m.group(1).lower() in STATUS_COLORS else "neutral"
        text = m.group(2).strip()
        return f'<span data-node-type="status" data-color="{color}" data-text="{text}" class="status s-{color}">{text}</span>'

    def _link(self, m):
        text, target = m.group(1), html.unescape(m.group(2))
        file, _, anchor = target.partition("#")
        if file in self.by_file:
            title = self.by_file[file].title
            if self.mode == "preview":
                return f'<a href="#page-{self.by_file[file].slug}">{text}</a>'
            if self.space_url:
                return f'<a href="{html.escape(self.space_url.rstrip("/") + "/" + title.replace(" ", "+"))}">{text}</a>'
            return text if text == html.escape(title, quote=False) else f"{text} (« {html.escape(title, quote=False)} »)"
        if not file and anchor:
            return text
        if not re.match(r"^[a-z][a-z0-9+.-]*:", file) or file.split(":", 1)[0] in self.sources:  # a repository file
            link = self._source_link(file)
            return f'<a href="{html.escape(link)}">{text}</a>' if link else f"{text} (<code>{html.escape(file)}</code>)"
        return f'<a href="{html.escape(target)}">{text}</a>'

    # ---- blocks
    def blocks(self, lines):
        out, i, n = [], 0, len(lines)
        while i < n:
            line = lines[i]
            s = line.strip()
            if not s:
                i += 1
                continue
            if s.startswith("<!--"):
                while i < n and "-->" not in lines[i]:
                    i += 1
                i += 1
                continue
            fence = re.match(r"^\s*(`{3,}|~{3,})\s*([\w+#.-]*)", line)
            if fence:
                mark, lang, body = fence.group(1), fence.group(2).lower(), []
                i += 1
                while i < n and not re.match(rf"^\s*{re.escape(mark[0])}{{{len(mark)},}}\s*$", lines[i]):
                    body.append(lines[i])
                    i += 1
                i += 1
                out.append(self.code_block(lang, "\n".join(body)))
                continue
            h = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
            if h:
                level = len(h.group(1))
                self.last_heading = re.sub(r"[*_`]", "", h.group(2))
                out.append(f"<h{level}>{self.inline(h.group(2))}</h{level}>")
                i += 1
                continue
            if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", line):
                out.append("<hr/>")
                i += 1
                continue
            if s.lower() == "<details>" or s.lower().startswith("<details>"):
                title, body, depth = "Details", [], 1
                i += 1
                while i < n:
                    low = lines[i].strip().lower()
                    if low.startswith("<details"):
                        depth += 1
                    if low.startswith("</details>"):
                        depth -= 1
                        if depth == 0:
                            break
                    sm = re.match(r"^\s*<summary>(.*?)</summary>\s*$", lines[i], re.I)
                    if sm and depth == 1 and title == "Details":
                        title = sm.group(1)
                    else:
                        body.append(lines[i])
                    i += 1
                i += 1
                inner = self.blocks(body)
                out.append(f'<div data-node-type="expand" data-title="{html.escape(re.sub("<[^>]+>", "", title))}" class="expand">'
                           f'<div class="expand-title">{html.escape(re.sub("<[^>]+>", "", title))}</div>{inner}</div>')
                continue
            if "|" in line and i + 1 < n and re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", lines[i + 1]):
                rows = [line]
                i += 2
                while i < n and "|" in lines[i] and lines[i].strip():
                    rows.append(lines[i])
                    i += 1
                out.append(self.table(rows))
                continue
            if s.startswith(">"):
                quote = []
                while i < n and lines[i].strip().startswith(">"):
                    quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                    i += 1
                out.append(self.quote(quote))
                continue
            if re.match(r"^\s*([-*+]|\d+[.)])\s+", line):
                start = i
                base = len(line) - len(line.lstrip())
                i += 1
                while i < n:
                    cur = lines[i]
                    if not cur.strip():
                        nxt = lines[i + 1] if i + 1 < n else ""
                        if nxt.strip() and (len(nxt) - len(nxt.lstrip()) > base or re.match(r"^\s*([-*+]|\d+[.)])\s+", nxt)
                                            and len(nxt) - len(nxt.lstrip()) >= base):
                            i += 1
                            continue
                        break
                    ind = len(cur) - len(cur.lstrip())
                    if ind < base or (ind == base and not re.match(r"^\s*([-*+]|\d+[.)])\s+", cur)
                                      and re.match(r"^\s*(#|>|```|~~~|\|)", cur)):
                        break
                    i += 1
                out.append(self.list_block(lines[start:i], base))
                continue
            para = [s]
            i += 1
            while i < n and lines[i].strip() and not re.match(r"^\s*(#{1,6}\s|```|~~~|>|<!--|<details|([-*+]|\d+[.)])\s+)", lines[i]) \
                    and not ("|" in lines[i] and i + 1 < n and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1])):
                para.append(lines[i].strip())
                i += 1
            text = "<br/>".join(self.inline(p.rstrip("\\").rstrip()) if p.endswith(("  ", "\\")) else self.inline(p) for p in [para[0]]) \
                if len(para) == 1 else self._join_para(para)
            out.append(f"<p>{text}</p>")
        return "\n".join(out)

    def _join_para(self, para):
        parts = []
        for k, p in enumerate(para):
            hard = p.endswith("\\") or p.endswith("  ")
            parts.append(self.inline(p.rstrip("\\").rstrip()) + ("<br/>" if hard and k < len(para) - 1 else ""))
        return " ".join(parts).replace("<br/> ", "<br/>")

    def list_block(self, lines, base):
        ordered = bool(re.match(r"^\s*\d+[.)]\s", lines[0]))
        items, cur = [], None
        for line in lines:
            ind = len(line) - len(line.lstrip())
            m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
            if m and ind == base:
                cur = [m.group(3)]
                items.append(cur)
            elif cur is not None:
                cur.append(line[base + 2:] if line[:base + 2].strip() == "" else line.strip())
        tag = "ol" if ordered else "ul"
        html_items = []
        for item in items:
            first = item[0]
            task = re.match(r"^\[([ xX])\]\s+(.*)$", first)
            if task:
                first = ("☑ " if task.group(1).lower() == "x" else "☐ ") + task.group(2)
            rest = item[1:]
            sub = [l for l in rest]
            # first line + following non-blank continuation lines form the item's paragraph
            para = [first]
            while sub and sub[0].strip() and not re.match(r"^\s*([-*+]|\d+[.)])\s+|^\s*(```|~~~|>|\|)", sub[0]):
                para.append(sub.pop(0).strip())
            body = self._join_para(para) if len(para) > 1 else self.inline(first)
            if sub and any(x.strip() for x in sub):
                indents = [len(x) - len(x.lstrip()) for x in sub if x.strip()]
                dedent = min(indents) if indents else 0
                body = f"<p>{body}</p>" + self.blocks([x[dedent:] for x in sub])
            html_items.append(f"<li>{body}</li>")
        return f"<{tag}>{''.join(html_items)}</{tag}>"

    def table(self, rows):
        def cells(row):
            row = row.strip()
            if row.startswith("|"):
                row = row[1:]
            if row.endswith("|") and not row.endswith("\\|"):
                row = row[:-1]
            return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row)]
        head = cells(rows[0])
        out = ["<table><tbody><tr>" + "".join(f"<th>{self.inline(c)}</th>" for c in head) + "</tr>"]
        for r in rows[1:]:
            cs = cells(r) + [""] * (len(head) - len(cells(r)))
            out.append("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in cs[:len(head)]) + "</tr>")
        return "".join(out) + "</tbody></table>"

    def quote(self, lines):
        m = re.match(r"^\s*\[!(\w+)\]\s*(.*)$", lines[0]) if lines else None
        if m and m.group(1).upper() in PANELS:
            kind = PANELS[m.group(1).upper()]
            rest = ([m.group(2)] if m.group(2).strip() else []) + lines[1:]
            return f'<div data-panel-type="{kind}" class="panel p-{kind}">{self.blocks(rest)}</div>'
        return f"<blockquote>{self.blocks(lines)}</blockquote>"

    def code_block(self, lang, code):
        if lang == "mermaid":
            idx = len(self.diagrams) + 1
            did = f"{self.page.slug}-diagram-{idx}"
            tm = re.match(r"^\s*%%\s*title:\s*(.+)$", code.splitlines()[0]) if code.strip() else None
            title = tm.group(1).strip() if tm else f"{self.last_heading} ({idx})" if idx > 1 else self.last_heading
            self.diagrams.append({"id": did, "title": title, "source": code})
            src = html.escape(code)
            if self.mode == "preview":
                return (f'<figure class="diagram" id="{did}"><div class="mermaid-src" hidden>{src}</div>'
                        f'<div class="mermaid-out">Rendering diagram…</div><figcaption>📊 {html.escape(title)} · '
                        f'<a href="#" data-dl="png" data-id="{did}">PNG</a> · <a href="#" data-dl="svg" data-id="{did}">SVG</a></figcaption></figure>')
            return (f'<p data-diagram-ref="{did}">[diagram {html.escape(title)}]</p>'
                    f'<div data-node-type="expand" data-title="Diagram source (Mermaid): {html.escape(title)}">'
                    f'<pre><code data-language="">{src}</code></pre></div>')
        lang = LANG_ALIASES.get(lang, lang)
        return f'<pre><code data-language="{lang}" class="language-{lang or "text"}">{html.escape(code)}</code></pre>'

    def render(self):
        lines = self.page.body.split("\n")
        k = 0
        while k < len(lines) and not lines[k].strip():
            k += 1
        if k < len(lines) and re.match(r"^#\s+", lines[k]):  # the page title goes in Confluence's title field
            lines = lines[k + 1:]
        return self.blocks(lines)


# ------------------------------------------------------------------ validation
def validate(pages):
    errors, warnings, info = [], [], []
    titles = Counter(p.title for p in pages)
    by_title = {p.title: p for p in pages}
    roots = [p for p in pages if not p.parent]
    ids = Counter(p.id for p in pages)
    known = {f"page:{p.id}" for p in pages} | {p.file for p in pages if p.single}
    for p in pages:
        where = p.where
        if ids[p.id] > 1:
            errors.append(f"{where}: duplicate page id «{p.id}» (set a unique `id` in its front matter)")
        if not p.title:
            errors.append(f"{where}: missing front matter `title`")
        if titles[p.title] > 1 and p.title:
            errors.append(f"{where}: duplicate title «{p.title}» (Confluence titles are unique per space)")
        if p.parent and p.parent not in by_title:
            errors.append(f"{where}: parent «{p.parent}» is not the title of another page")
        if p.body.count("```") % 2:
            errors.append(f"{where}: unclosed ``` code fence")
        for no, line in enumerate(p.body.splitlines(), 1):
            for kind, rx in SECRETS:
                if rx.search(line):
                    errors.append(f"{p.file}:{p.line0 + no}: looks like a {kind}: remove it (the value is not shown here)")
            if TODO.search(line):
                warnings.append(f"{p.file}:{p.line0 + no}: leftover {TODO.search(line).group(1)}")
        for m in re.finditer(r"\]\((page:[\w-]+|[^)\s#:/]+\.md)(#[^)]*)?\)", p.body):
            if m.group(1) not in known:
                errors.append(f"{where}: link to unknown page {m.group(1)} (use page:<id>; ids: {', '.join(sorted(ids))})")
        body_nc = re.sub(r"```.*?```", "[code]", p.body, flags=re.S)
        heads = re.findall(r"^(#{1,6})\s+(.+)$", body_nc, re.M)
        for a, b in zip(heads, heads[1:]):
            if len(b[0]) <= len(a[0]):
                seg = body_nc.split(a[0] + " " + a[1], 1)[-1].split(b[0] + " " + b[1], 1)[0]
                if not re.sub(r"<!--.*?-->", "", seg, flags=re.S).strip():
                    warnings.append(f"{where}: empty section «{a[1].strip()}» (remove it or write what is missing as TBD)")
        fence_open, bare = False, []
        for no, line in enumerate(p.body.splitlines(), 1):
            fm = re.match(r"^\s*```(\S*)\s*$", line)
            if fm:
                if not fence_open and not fm.group(1):
                    bare.append(str(p.line0 + no))
                fence_open = not fence_open
        if bare:
            warnings.append(f"{p.file}:{','.join(bare)}: code block without a language (use ```text for trees and plain output)")
        if p.words > 2500:
            warnings.append(f"{where}: {p.words} words; consider splitting it into child pages")
        if not re.search(r"`[\w.@:-]*/[\w./@-]+(:\d+(-\d+)?)?`|`[\w.-]+\.(java|ts|ya?ml|json|xml|properties|md|sql|gradle|kts)(:\d+)?`", p.body):
            warnings.append(f"{where}: no file reference: cite the files the page is based on")
        tbd = len(re.findall(r"\bTBD\b|❓", p.body))
        if tbd:
            info.append(f"{where}: {tbd} open point(s) (TBD)")
    if len(roots) != 1:
        errors.append(f"exactly one page must have no `parent` (the landing page); found {len(roots)}: "
                      + ", ".join(p.where for p in roots))
    seen = {}
    for p in pages:
        for para in re.split(r"\n\s*\n", re.sub(r"```.*?```", "", p.body, flags=re.S)):
            norm = re.sub(r"\s+", " ", para).strip().lower()
            if len(norm) >= 160 and not norm.startswith(("|", "#", "<!--")):
                if norm in seen and seen[norm] != p.where:
                    warnings.append(f"{p.where}: paragraph duplicated from {seen[norm]} (link to it instead)")
                seen.setdefault(norm, p.where)
    return errors, warnings, info


def check_files(pages, repos):
    """Warn about cited files (`path/File.ext`, `prefix:path/File.ext:12`) that do not exist in the repositories."""
    roots = {}
    for r in repos:
        label, sep, path = r.partition("=")
        roots[label if sep else None] = path if sep else r
    if not roots:
        return []
    out = []
    for p in pages:
        for no, line in enumerate(p.body.splitlines(), 1):
            for ref in re.findall(r"`([^`\s]+)`", line):
                label, path = None, ref
                if re.match(r"^[\w.-]+:[\w.]", ref) and ref.split(":", 1)[0] in roots:
                    label, path = ref.split(":", 1)
                path = re.sub(r":\d+(-\d+)?$", "", path)
                last = path.rstrip("/").split("/")[-1]
                if ("/" not in path or path.startswith(("/", "http")) or re.search(r"[*{}<>…:$]", path)
                        or not re.search(r"\.\w+$", last) or (label is None and None not in roots)):
                    continue
                if not os.path.exists(os.path.join(roots[label], path)):
                    out.append(f"{p.file}:{p.line0 + no}: cited file `{ref}` does not exist in the repository")
    return out


# ------------------------------------------------------------------ HTML bundle
CSS = """
:root{--bg:#fff;--fg:#172b4d;--muted:#5e6c84;--line:#dfe1e6;--nav:#f4f5f7;--accent:#0c66e4;--code:#f4f5f7;
--info:#e9f2ff;--tip:#dcfff1;--note:#f3f0ff;--warning:#fff7d6;--error:#ffeceb;--success:#dcfff1}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1d2125;--fg:#c7d1db;--muted:#9fadbc;--line:#38414a;
--nav:#22272b;--accent:#579dff;--code:#2c333a;--info:#092957;--tip:#164b35;--note:#352c63;--warning:#533f04;--error:#5d1f1a;--success:#164b35}}
*{box-sizing:border-box}a{color:var(--accent)}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"Segoe UI",Roboto,sans-serif}
.layout{display:flex;min-height:100vh}nav{width:290px;flex:none;background:var(--nav);border-right:1px solid var(--line);padding:16px;
position:sticky;top:0;height:100vh;overflow:auto}nav ul{list-style:none;padding-left:14px;margin:0}nav>ul{padding-left:0}
nav a{color:var(--fg);text-decoration:none;display:block;padding:2px 0}nav a:hover{color:var(--accent)}
main{flex:1;min-width:0;padding:16px 32px 80px;max-width:1100px}.guide{border:1px solid var(--line);border-radius:6px;padding:12px 16px;margin-bottom:24px}
.guide ol{margin:4px 0 0;padding-left:20px}section.page{border-top:3px solid var(--line);padding-top:12px;margin-top:40px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;color:var(--muted);font-size:13px}
button{font:inherit;font-size:13px;padding:4px 10px;border:1px solid var(--line);background:var(--nav);color:var(--fg);border-radius:4px;cursor:pointer}
button:hover{border-color:var(--accent)}.ok{color:#22a06b}.label{background:var(--code);border-radius:3px;padding:0 6px}
h1.ptitle{margin:4px 0 12px;font-size:26px}table{border-collapse:collapse;margin:8px 0;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}th{background:var(--nav)}
pre{background:var(--code);padding:10px 12px;border-radius:4px;overflow-x:auto}code{background:var(--code);padding:1px 4px;border-radius:3px;font-size:13px}
pre code{padding:0;background:none}main p,main li,main td,main th{overflow-wrap:anywhere}.panel{border-radius:4px;padding:2px 14px;margin:10px 0}.p-info{background:var(--info)}.p-tip{background:var(--tip)}
.p-note{background:var(--note)}.p-warning{background:var(--warning)}.p-error{background:var(--error)}.p-success{background:var(--success)}
.expand{border:1px solid var(--line);border-radius:4px;padding:4px 12px;margin:10px 0}.expand-title{font-weight:600}
.status{font-size:11px;font-weight:700;text-transform:uppercase;border-radius:3px;padding:1px 5px;background:var(--code)}
.s-green{background:#baf3db;color:#164b35}.s-red{background:#ffd5d2;color:#5d1f1a}.s-yellow{background:#f8e6a0;color:#533f04}
.s-blue{background:#cce0ff;color:#09326c}.s-purple{background:#dfd8fd;color:#352c63}
figure.diagram{margin:12px 0;border:1px solid var(--line);border-radius:4px;padding:8px;background:#fff;color:#172b4d;overflow-x:auto}
figcaption{font-size:13px;margin-top:6px}blockquote{border-left:3px solid var(--line);margin:8px 0;padding:0 12px;color:var(--muted)}
@media (max-width:800px){.layout{display:block}nav{position:static;width:auto;height:auto}main{padding:16px}}
"""

JS = r"""
const diagrams = {};
function toast(btn, text){const o=btn.textContent;btn.textContent=text;btn.classList.add('ok');setTimeout(()=>{btn.textContent=o;btn.classList.remove('ok')},1800);}
function pasteHtml(id){
  let h = document.getElementById('paste-'+id).innerHTML;
  return h.replace(/<p data-diagram-ref="([^"]+)">[\s\S]*?<\/p>/g, (m, ref) => {
    const d = diagrams[ref];
    const title = d ? d.title : ref;
    const img = d && d.png ? `<p><img src="${d.png}" alt="${title}"/></p>` : '';
    return img + `<p><em>📊 ${title}: drag ${ref}.png here if the image did not paste (download it with the PNG link under the diagram in the preview).</em></p>`;
  });
}
async function copyRich(htmlText, plain, btn){
  try {
    await navigator.clipboard.write([new ClipboardItem({'text/html': new Blob([htmlText],{type:'text/html'}),
                                                       'text/plain': new Blob([plain],{type:'text/plain'})})]);
    return toast(btn,'Copied ✓');
  } catch (e) {
    const box = document.createElement('div'); box.contentEditable = 'true'; box.innerHTML = htmlText;
    box.style.cssText = 'position:fixed;left:-9999px;top:0'; document.body.appendChild(box);
    const r = document.createRange(); r.selectNodeContents(box); const s = getSelection(); s.removeAllRanges(); s.addRange(r);
    const ok = document.execCommand('copy'); s.removeAllRanges(); box.remove();
    toast(btn, ok ? 'Copied ✓' : 'Copy failed: select the page and press Ctrl+C');
  }
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-copy]');
  if (b) {
    e.preventDefault();
    const id = b.dataset.id;
    if (b.dataset.copy === 'title') { navigator.clipboard.writeText(b.dataset.title).then(()=>toast(b,'Copied ✓'), ()=>toast(b,'Select the title')); }
    else { const h = pasteHtml(id); const t = document.getElementById('body-'+id).innerText; copyRich(h, t, b); }
  }
  const dl = e.target.closest('[data-dl]');
  if (dl) {
    e.preventDefault();
    const d = diagrams[dl.dataset.id];
    if (!d) return alert('The diagram is not rendered (Mermaid could not load).');
    const url = dl.dataset.dl === 'png' ? d.png : URL.createObjectURL(new Blob([d.svg],{type:'image/svg+xml'}));
    if (!url) return alert('PNG export is not available in this browser: use SVG.');
    const a = document.createElement('a'); a.href = url; a.download = dl.dataset.id + '.' + dl.dataset.dl; a.click();
  }
});
function svgToPng(svgText){
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => {
      const scale = 2, w = img.naturalWidth || 800, h = img.naturalHeight || 600;
      const c = document.createElement('canvas'); c.width = w*scale; c.height = h*scale;
      const ctx = c.getContext('2d'); ctx.fillStyle = '#fff'; ctx.fillRect(0,0,c.width,c.height); ctx.scale(scale,scale); ctx.drawImage(img,0,0,w,h);
      try { resolve(c.toDataURL('image/png')); } catch (e) { resolve(null); }
    };
    img.onerror = () => resolve(null);
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgText)));
  });
}
async function renderDiagrams(){
  const figs = document.querySelectorAll('figure.diagram');
  if (!figs.length) return;
  if (!window.mermaid) { figs.forEach(f => { f.querySelector('.mermaid-out').innerHTML = '<p>Mermaid could not be loaded (offline or blocked CDN): re-run the export with --mermaid-js pointing to a reachable copy. Source:</p><pre>'+f.querySelector('.mermaid-src').innerHTML+'</pre>'; }); return; }
  mermaid.initialize({startOnLoad:false, securityLevel:'strict', theme:'default', htmlLabels:false, flowchart:{htmlLabels:false}});
  let n = 0;
  for (const f of figs) {
    const src = f.querySelector('.mermaid-src').textContent.replace(/\\n/g, '<br/>');  // "\n" in labels means a line break
    try {
      const {svg} = await mermaid.render('mmd-' + (++n), src);
      f.querySelector('.mermaid-out').innerHTML = svg;
      const el = f.querySelector('svg'); const box = el.getBBox ? el.getBBox() : null;
      let s = svg;
      if (box && !/\swidth="\d/.test(svg.slice(0, 300))) { s = svg.replace('<svg ', `<svg width="${Math.ceil(box.width+box.x*2)}" height="${Math.ceil(box.height+box.y*2)}" `); }
      diagrams[f.id] = {title: f.dataset.title, svg: s, png: await svgToPng(s)};
    } catch (e) { f.querySelector('.mermaid-out').innerHTML = '<p>⚠️ Mermaid syntax error: ' + (e.message||e) + '</p>'; }
  }
  document.body.dataset.diagrams = 'done';
}
window.addEventListener('load', renderDiagrams);
"""


def tree_html(pages):
    children = {}
    for p in pages:
        children.setdefault(p.parent, []).append(p)

    def node(parent):
        items = children.get(parent, [])
        if not items:
            return ""
        return "<ul>" + "".join(f'<li><a href="#page-{p.slug}">{html.escape(p.title)}</a>{node(p.title)}</li>' for p in items) + "</ul>"
    return node("")


def build_html(pages, sources, space_url, mermaid_js, title):
    sections, all_diagrams = [], 0
    for p in pages:
        prev = Renderer(pages, p, "preview", sources, space_url)
        body = prev.render()
        paste = Renderer(pages, p, "paste", sources, space_url).render()
        for d in prev.diagrams:
            body = body.replace(f'<figure class="diagram" id="{d["id"]}">', f'<figure class="diagram" id="{d["id"]}" data-title="{html.escape(d["title"])}">')
        all_diagrams += len(prev.diagrams)
        labels = " ".join(f'<span class="label">{html.escape(l)}</span>' for l in p.labels)
        n_sections = len(re.findall(r"^##\s", p.body, re.M))
        toc_hint = " · after pasting, type <code>/toc</code> at the top" if n_sections >= 4 else ""
        sections.append(
            f'<section class="page" id="page-{p.slug}"><div class="bar"><span>{html.escape(p.file)} · id {html.escape(p.id)}</span>'
            f'<span>parent: {html.escape(p.parent or "— (landing page)")}</span>{labels}</div>'
            f'<h1 class="ptitle">{html.escape(p.title)}</h1>'
            f'<div class="bar"><button data-copy="title" data-id="{p.slug}" data-title="{html.escape(p.title)}">Copy title</button>'
            f'<button data-copy="body" data-id="{p.slug}">Copy page for Confluence</button><span>{p.words} words{toc_hint}</span></div>'
            f'<div id="body-{p.slug}">{body}</div><template id="paste-{p.slug}">{paste}</template></section>')
    script = f'<script src="{html.escape(mermaid_js)}"></script>' if all_diagrams else ""
    guide = ("<div class='guide'><strong>Paste into Confluence Cloud</strong><ol>"
             "<li>Create the pages in the order of the tree, each under its parent (the landing page first).</li>"
             "<li>For each page: <em>Copy title</em> → paste in the title field; <em>Copy page for Confluence</em> → paste in the body "
             "(Ctrl/Cmd+V, not “paste as plain text”).</li>"
             "<li>Check the result: panels, code blocks, expands and status lozenges should be native elements; "
             "if a diagram image is missing, download its PNG here and drag it onto the page.</li>"
             "<li>Add the labels shown above each page; on long pages type <code>/toc</code> at the top; on the landing page, "
             "<code>/children</code> lists the child pages.</li></ol></div>")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style>{script}</head><body><div class='layout'>"
            f"<nav><strong>{html.escape(title)}</strong>{tree_html(pages)}</nav><main>{guide}{''.join(sections)}</main></div>"
            f"<script>{JS}</script></body></html>")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", help="folder with the playbook's Markdown pages")
    ap.add_argument("--out", help="output folder (default: <pages>/confluence)")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--source-url", action="append", default=[],
                    help="base URL of the files at a fixed commit, to link `path` and `path:line` references "
                         "(e.g. https://gitlab.example.com/g/app/-/blob/<sha>); repeat as label=URL for several repositories")
    ap.add_argument("--space-url", help="Confluence space URL to turn page links into links by title "
                                        "(e.g. https://acme.atlassian.net/wiki/display/KEY); otherwise they become plain text")
    ap.add_argument("--repo", action="append", default=[],
                    help="repository root to check that cited files exist (path, or prefix=path for several repositories)")
    ap.add_argument("--mermaid-js", default=MERMAID_JS, help="Mermaid script URL or path, for networks that block the CDN")
    a = ap.parse_args()
    files = sorted(f for f in os.listdir(a.pages) if f.endswith(".md") and not f.startswith(("_", ".")) and f.lower() != "readme.md")
    if not files:
        sys.exit(f"no Markdown pages in {a.pages}")
    pages = []
    for f in files:
        chunks = split_pages(os.path.join(a.pages, f))
        for chunk, first_line in chunks:
            pages.append(Page(os.path.join(a.pages, f), chunk, len(chunks) == 1, first_line))
    errors, warnings, info = validate(pages)
    warnings += check_files(pages, a.repo)
    root = next((p for p in pages if not p.parent), pages[0])
    print(f"{len(pages)} pages, {sum(p.words for p in pages)} words; landing page «{root.title}»")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    for i in info:
        print("INFO ", i)
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s); nothing exported")
        return 1
    if a.check:
        print(f"OK: {len(warnings)} warning(s)")
        return 0
    sources = {}
    for s in a.source_url:
        label, sep, url = s.partition("=")
        if sep and not label.startswith("http"):
            sources[label] = url
        else:
            sources[None] = s
    if sources:
        used = Counter(m for p in pages for m in re.findall(r"`([\w.-]+):(?!\d)[\w.-]*/[^`\s]*`", p.body) if m != "localhost")
        missing = [lab for lab in used if lab not in sources and not re.fullmatch(r"https?", lab)]
        if missing and None not in sources:
            print("WARN  file references prefixed " + ", ".join(f"«{m}:» ({used[m]})" for m in missing)
                  + " are not linked: pass --source-url <prefix>=<URL> with exactly these prefixes")
    out = a.out or os.path.join(a.pages, "confluence")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "playbook.html"), "w", encoding="utf-8") as fh:
        fh.write(build_html(pages, sources, a.space_url, a.mermaid_js, root.title))
    manifest_path = os.path.join(out, "manifest.json")
    old = {}
    if os.path.isfile(manifest_path):
        try:
            old = {p["title"]: p for p in json.load(open(manifest_path, encoding="utf-8")).get("pages", [])}
        except (ValueError, KeyError):
            old = {}
    new = [OrderedDict(file=p.file, id=p.id, title=p.title, parent=p.parent, labels=p.labels, hash=p.hash, words=p.words) for p in pages]
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump({"landing": root.title, "pages": new}, fh, indent=1, ensure_ascii=False)
    if old:
        created = [p["title"] for p in new if p["title"] not in old]
        changed = [p["title"] for p in new if p["title"] in old and old[p["title"]]["hash"] != p["hash"]]
        removed = [t for t in old if t not in {p["title"] for p in new}]
        print("Since the last export: " + "; ".join(f"{k}: {', '.join(v) if v else 'none'}" for k, v in
                                                     (("new", created), ("changed", changed), ("removed", removed))))
        print("Update only these pages in Confluence; removed pages are archived there by hand.")
    print(f"OK: wrote {os.path.join(out, 'playbook.html')} and manifest.json ({len(warnings)} warning(s)). "
          "Open playbook.html in a browser and use the copy buttons.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
