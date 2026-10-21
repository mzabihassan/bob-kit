#!/usr/bin/env python3
"""Extract the de facto design system of a frontend code base.

Scans CSS/SCSS/Less, templates and TS/JS(X) for colours, typography, spacing,
radii, shadows, z-indexes, breakpoints, CSS custom properties, SCSS variables
and Tailwind utilities; clusters near-duplicate colours (OKLab), computes WCAG
contrast, token coverage and scale adherence. Read-only on the sources; writes
only into --out: summary.md, extracted.json, tokens.draft.json (W3C DTCG) and
palette.html.

Example:
  python3 extract_design_tokens.py frontend/src --out /tmp/ds-report
"""
import argparse
import colorsys
import fnmatch
import html
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

SKIP_DIRS = {".git", "node_modules", "dist", "build", "target", ".angular", "coverage", ".next", "out",
             "vendor", ".gradle", ".idea", ".vscode", "storybook-static", "__pycache__"}
STYLE_EXT = {".css", ".scss", ".sass", ".less", ".styl"}
MARKUP_EXT = {".html", ".htm", ".vue", ".svelte"}
SCRIPT_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs"}
DEFAULT_EXCLUDES = ["*.min.css", "*.min.js", "*.spec.ts", "*.test.ts", "*.test.tsx", "*.spec.tsx", "*.stories.*",
                    "*/assets/fonts/*", "*/generated/*"]
NAMED = {"white": "#ffffff", "black": "#000000"}

HEX = re.compile(r"(?<![\w&.#])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
HEX_IN_SCRIPT = re.compile(r"""(?<=["'`(\s:,\[])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])""")
RGB = re.compile(r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})(?:\s*[,/]\s*([\d.]+%?))?\s*\)")
HSL = re.compile(r"hsla?\(\s*([\d.]+)(?:deg)?\s*[, ]\s*([\d.]+)%\s*[, ]\s*([\d.]+)%(?:\s*[,/]\s*([\d.]+%?))?\s*\)")
DECL = re.compile(r"(?<![\w$-])(?P<prop>-?[a-zA-Z][a-zA-Z-]*)\s*:\s*(?P<val>[^;{}\n]+)")
# JS/TS style objects: a value ends at a comma unless it is a quoted string (e.g. 'rgba(0, 0, 0, .3)')
DECL_SCRIPT = re.compile(r"""(?<![\w$-])(?P<prop>[a-zA-Z][a-zA-Z-]*)\s*:\s*(?P<val>'[^'\n]*'|"[^"\n]*"|[^;,{}\n]+)""")
CUSTOM_DEF = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+);")
CUSTOM_USE = re.compile(r"var\(\s*(--[\w-]+)")
SCSS_DEF = re.compile(r"^\s*(\$[\w-]+)\s*:\s*([^;]+);", re.M)
SCSS_USE = re.compile(r"\$[\w-]+")
MEDIA = re.compile(r"@media[^{]*?\(\s*(min|max)-width\s*:\s*([\d.]+)(px|em|rem)")
LENGTH = re.compile(r"(-?\d*\.?\d+)(px|rem|em)\b")
TW_COLOR = re.compile(r"\b(?:bg|text|border|ring|fill|stroke|from|via|to|outline|divide|placeholder|accent|caret|decoration)-"
                      r"([a-z]+)-(50|100|200|300|400|500|600|700|800|900|950)\b")
TW_ARBITRARY = re.compile(r"\b[a-z-]+-\[([^\]\s]+)\]")

COLOR_PROPS = {"color", "fill", "stroke", "caret-color", "accent-color", "text-decoration-color"}
BG_PROPS = {"background", "background-color"}
BORDER_PROPS = {"border", "border-color", "border-top", "border-right", "border-bottom", "border-left",
                "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
                "outline", "outline-color", "column-rule-color"}
SPACING_PROPS = {"margin", "margin-top", "margin-right", "margin-bottom", "margin-left", "margin-inline",
                 "margin-block", "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
                 "padding-inline", "padding-block", "gap", "row-gap", "column-gap", "inset", "top", "right",
                 "bottom", "left"}
RADIUS_PROPS = {"border-radius", "border-top-left-radius", "border-top-right-radius", "border-bottom-left-radius",
                "border-bottom-right-radius"}
KNOWN_PROPS = (COLOR_PROPS | BG_PROPS | BORDER_PROPS | SPACING_PROPS | RADIUS_PROPS |
               {"font-family", "font-size", "font-weight", "line-height", "letter-spacing", "box-shadow",
                "z-index", "transition", "transition-duration", "animation-duration", "font"})
TOKEN_REF = re.compile(r"var\(--|\$[\w-]|theme\(|mat\.|map-get|map\.get|@[a-zA-Z]|\btheme\.|\btokens?\.")


def kebab(prop):
    return re.sub(r"([a-z])([A-Z])", r"\1-\2", prop).lower()


def norm_hex(h):
    h = h.lower()
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    return "#" + h


def parse_colors(text, script):
    """Yield (hex6, alpha) for every colour literal in text."""
    for m in (HEX_IN_SCRIPT if script else HEX).finditer(text):
        h = norm_hex(m.group(1))
        alpha = round(int(h[7:9], 16) / 255, 2) if len(h) == 9 else 1.0
        yield h[:7], alpha
    for m in RGB.finditer(text):
        r, g, b = (min(255, int(x)) for x in m.groups()[:3])
        yield "#%02x%02x%02x" % (r, g, b), parse_alpha(m.group(4))
    for m in HSL.finditer(text):
        h, s, l = float(m.group(1)) % 360 / 360, float(m.group(2)) / 100, float(m.group(3)) / 100
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        yield "#%02x%02x%02x" % tuple(round(c * 255) for c in (r, g, b)), parse_alpha(m.group(4))


def parse_alpha(a):
    if not a:
        return 1.0
    return round(float(a[:-1]) / 100 if a.endswith("%") else float(a), 2)


def srgb_to_linear(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(hex6):
    return tuple(int(hex6[i:i + 2], 16) for i in (1, 3, 5))


def oklab(hex6):
    r, g, b = (srgb_to_linear(c) for c in rgb(hex6))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def delta_e(a, b):
    return math.dist(oklab(a), oklab(b))


def luminance(hex6):
    r, g, b = (srgb_to_linear(c) for c in rgb(hex6))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def to_px(value, unit, base=16):
    v = float(value)
    return v * base if unit in ("rem", "em") else v


def role_of(prop):
    if prop in COLOR_PROPS:
        return "text"
    if prop in BG_PROPS:
        return "background"
    if prop in BORDER_PROPS:
        return "border"
    if prop == "box-shadow":
        return "shadow"
    return "other"


def iter_files(roots, excludes):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                p = os.path.join(d, f)
                ext = os.path.splitext(f)[1].lower()
                if ext not in STYLE_EXT | MARKUP_EXT | SCRIPT_EXT:
                    continue
                if any(fnmatch.fnmatch(p, g) or fnmatch.fnmatch(f, g) for g in excludes):
                    continue
                yield p


def cluster(colors, threshold):
    """Greedy clustering by usage: the most used colour of a group is its canonical value."""
    clusters = []
    for hexv, count in colors.most_common():
        for c in clusters:
            if delta_e(hexv, c["canonical"]) <= threshold:
                c["members"].append({"hex": hexv, "count": count})
                c["count"] += count
                break
        else:
            clusters.append({"canonical": hexv, "count": count, "members": [{"hex": hexv, "count": count}]})
    return clusters


def scale_summary(values, grid=4, top=12):
    c = Counter(round(v, 2) for v in values if v > 0)
    on_grid = sum(n for v, n in c.items() if abs(v / grid - round(v / grid)) < 1e-6)
    total = sum(c.values())
    return {"distinct": len(c), "occurrences": total,
            "on_grid_pct": round(100 * on_grid / total, 1) if total else None,
            "most_used": [[v, n] for v, n in c.most_common(top)]}


def detect_stack(roots):
    found = {}
    for root in roots:
        base = root if os.path.isdir(root) else os.path.dirname(root)
        for up in [base] + [os.path.abspath(os.path.join(base, *[".."] * i)) for i in range(1, 4)]:
            pj = os.path.join(up, "package.json")
            if os.path.isfile(pj):
                try:
                    with open(pj) as fh:
                        pkg = json.load(fh)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                except (ValueError, OSError):
                    deps = {}
                for name in ("@angular/core", "@angular/material", "primeng", "react", "@mui/material", "tailwindcss",
                             "bootstrap", "styled-components", "@emotion/react", "@chakra-ui/react", "vue", "@carbon/react",
                             "@ng-bootstrap/ng-bootstrap"):
                    if name in deps:
                        found[name] = deps[name]
                break
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="+", help="source directories or files to scan")
    ap.add_argument("--out", required=True, help="output directory (created; only files written)")
    ap.add_argument("--exclude", action="append", default=[], help="extra glob to exclude (repeatable)")
    ap.add_argument("--threshold", type=float, default=0.03, help="OKLab distance for near-duplicate colours")
    ap.add_argument("--base-font", type=float, default=16, help="px per rem/em")
    a = ap.parse_args()

    colors_by_role = defaultdict(Counter)
    color_files = defaultdict(set)
    alpha_variants = defaultdict(set)
    fonts, weights, line_heights = Counter(), Counter(), Counter()
    font_sizes, spacing, radii, shadows, zidx, durations = [], [], [], Counter(), Counter(), Counter()
    coverage = defaultdict(lambda: {"tokenized": 0, "hardcoded": 0})
    custom_defs, custom_uses, scss_defs, scss_uses = {}, Counter(), {}, Counter()
    breakpoints, tw_colors, tw_arbitrary = Counter(), Counter(), Counter()
    files_scanned = 0

    for path in iter_files(a.roots, DEFAULT_EXCLUDES + a.exclude):
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        files_scanned += 1
        ext = os.path.splitext(path)[1].lower()
        script = ext in SCRIPT_EXT
        rel = os.path.relpath(path)

        for name, val in CUSTOM_DEF.findall(text):
            custom_defs.setdefault(name, val.strip())
        custom_uses.update(CUSTOM_USE.findall(text))
        if ext in {".scss", ".sass"}:
            defs = dict(SCSS_DEF.findall(text))
            for k, v in defs.items():
                scss_defs.setdefault(k, v.strip())
            scss_uses.update(t for t in SCSS_USE.findall(text))
        for kind, val, unit in MEDIA.findall(text):
            breakpoints[f"{kind}-width {round(to_px(val, unit, a.base_font))}px"] += 1
        if script or ext in MARKUP_EXT:
            tw_colors.update(f"{c}-{s}" for c, s in TW_COLOR.findall(text))
            tw_arbitrary.update(TW_ARBITRARY.findall(text))

        for m in (DECL_SCRIPT if script else DECL).finditer(text):
            prop = kebab(m.group("prop"))
            if prop not in KNOWN_PROPS or prop.startswith("--"):
                continue
            val = m.group("val").strip().strip("'\"`").rstrip(",")
            tokenized = bool(TOKEN_REF.search(val))
            role = role_of(prop)
            found_color = False
            for hexv, alpha in parse_colors(" " + val + " ", script):
                found_color = True
                colors_by_role[role][hexv] += 1
                color_files[hexv].add(rel)
                if alpha < 1:
                    alpha_variants[hexv].add(alpha)
            if not found_color:
                for word in re.findall(r"\b(white|black)\b", val):
                    colors_by_role[role][NAMED[word]] += 1
                    color_files[NAMED[word]].add(rel)
                    found_color = True
            if role != "other" or prop in COLOR_PROPS:
                if found_color or tokenized:
                    coverage["color"]["tokenized" if tokenized and not found_color else "hardcoded"] += 1
            lengths = [to_px(v, u, a.base_font) for v, u in LENGTH.findall(val)]
            if script and not lengths and re.fullmatch(r"-?\d+(\.\d+)?", val):
                lengths = [float(val)]
            category = ("spacing" if prop in SPACING_PROPS else "font-size" if prop == "font-size"
                        else "radius" if prop in RADIUS_PROPS else None)
            if category:
                if tokenized:
                    coverage[category]["tokenized"] += 1
                elif lengths:
                    coverage[category]["hardcoded"] += 1
                    {"spacing": spacing, "font-size": font_sizes, "radius": radii}[category].extend(abs(x) for x in lengths)
            if prop == "font-family" and not tokenized:
                fonts[val.split(",")[0].strip().strip("'\"")] += 1
            elif prop == "font-weight" and not tokenized:
                weights[val] += 1
            elif prop == "line-height" and not tokenized:
                line_heights[val] += 1
            elif prop == "box-shadow" and not tokenized:
                shadows[re.sub(r"\s+", " ", val)] += 1
            elif prop == "z-index" and not tokenized:
                zidx[val] += 1
            elif prop in ("transition", "transition-duration", "animation-duration"):
                durations.update(re.findall(r"\d*\.?\d+m?s\b", val))


    # colours declared as tokens (custom properties / SCSS variables)
    declared_colors = Counter()
    for src in (custom_defs, scss_defs):
        for name, val in src.items():
            for hexv, _ in parse_colors(" " + val + " ", False):
                declared_colors[hexv] += 1
                colors_by_role["token"][hexv] += 1
                color_files[hexv].add("(token)")

    all_colors = Counter()
    for role, c in colors_by_role.items():
        all_colors.update(c)
    clusters = cluster(all_colors, a.threshold)
    palette = []
    for i, c in enumerate(clusters, 1):
        hexv = c["canonical"]
        roles = {r: colors_by_role[r][m["hex"]] for r in colors_by_role for m in c["members"] if colors_by_role[r][m["hex"]]}
        palette.append({
            "id": f"color-{i:02d}", "hex": hexv, "uses": c["count"], "variants": c["members"],
            "roles": dict(Counter({r: sum(colors_by_role[r][m["hex"]] for m in c["members"]) for r in roles})),
            "declared_as_token": any(m["hex"] in declared_colors for m in c["members"]),
            "contrast_vs_white": contrast(hexv, "#ffffff"), "contrast_vs_black": contrast(hexv, "#000000"),
            "alpha_variants": sorted(set().union(*(alpha_variants.get(m["hex"], set()) for m in c["members"]))),
            "files": len(set().union(*(color_files[m["hex"]] for m in c["members"]))),
        })
    # candidate pairs between perceptual groups: most used background groups x text groups (canonical values)
    bg_groups = sorted((p for p in palette if p["roles"].get("background")), key=lambda p: -p["roles"]["background"])[:3]
    backgrounds = [p["hex"] for p in bg_groups] or ["#ffffff"]
    text_colors = sorted((p for p in palette if p["roles"].get("text")), key=lambda p: -p["roles"]["text"])
    contrast_checks = []
    for t in text_colors[:15]:
        for bg in backgrounds:
            if t["hex"] != bg:
                ratio = contrast(t["hex"], bg)
                contrast_checks.append({"text": t["hex"], "background": bg, "ratio": ratio,
                                        "aa_normal": ratio >= 4.5, "aa_large": ratio >= 3.0})

    def ratio_estimate(vals):
        common = sorted({v for v, n in Counter(round(x) for x in vals).most_common(8) if v > 0})
        steps = [b / a for a, b in zip(common, common[1:]) if a]
        return round(sorted(steps)[len(steps) // 2], 3) if steps else None

    result = {
        "files_scanned": files_scanned, "stack": detect_stack(a.roots),
        "colors": {"distinct": len(all_colors), "clusters": len(clusters),
                   "near_duplicate_groups": sum(1 for c in clusters if len(c["members"]) > 1), "palette": palette},
        "contrast_checks": sorted(contrast_checks, key=lambda x: x["ratio"]),
        "typography": {"families": fonts.most_common(10), "sizes": scale_summary(font_sizes, grid=2),
                       "size_ratio_estimate": ratio_estimate(font_sizes), "weights": weights.most_common(10),
                       "line_heights": line_heights.most_common(10)},
        "spacing": scale_summary(spacing, grid=4), "radius": scale_summary(radii, grid=2),
        "shadows": {"distinct": len(shadows), "most_used": shadows.most_common(8)},
        "z_index": {"distinct": len(zidx), "values": zidx.most_common(15)},
        "durations": durations.most_common(10), "breakpoints": breakpoints.most_common(12),
        "tokens": {"custom_properties_defined": len(custom_defs), "custom_properties_used": len(custom_uses),
                   "defined_never_used": sorted(set(custom_defs) - set(custom_uses))[:50],
                   "used_never_defined": sorted(set(custom_uses) - set(custom_defs))[:50],
                   "scss_variables_defined": len(scss_defs)},
        "coverage": {k: {**v, "tokenized_pct": round(100 * v["tokenized"] / (v["tokenized"] + v["hardcoded"]), 1)
                         if v["tokenized"] + v["hardcoded"] else None} for k, v in coverage.items()},
        "tailwind": {"palette_classes": tw_colors.most_common(20), "arbitrary_values": tw_arbitrary.most_common(20)},
    }

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "extracted.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    dtcg = {"color": {"primitive": {p["id"]: {"$type": "color", "$value": p["hex"],
                                              "$extensions": {"bob-kit": {"uses": p["uses"], "roles": p["roles"]}}}
                                    for p in palette[:40]}},
            "dimension": {"spacing": {f"s{i}": {"$type": "dimension", "$value": f"{v:g}px"}
                                      for i, (v, _) in enumerate(sorted(result["spacing"]["most_used"]), 1)},
                          "font-size": {f"fs{i}": {"$type": "dimension", "$value": f"{v:g}px"}
                                        for i, (v, _) in enumerate(sorted(result["typography"]["sizes"]["most_used"]), 1)},
                          "radius": {f"r{i}": {"$type": "dimension", "$value": f"{v:g}px"}
                                     for i, (v, _) in enumerate(sorted(result["radius"]["most_used"]), 1)}}}
    with open(os.path.join(a.out, "tokens.draft.json"), "w") as fh:
        json.dump(dtcg, fh, indent=2)
    write_html(os.path.join(a.out, "palette.html"), result)
    summary = render_summary(result)
    with open(os.path.join(a.out, "summary.md"), "w") as fh:
        fh.write(summary)
    print(summary)
    print(f"\nWritten: {', '.join(sorted(os.listdir(a.out)))} in {a.out}")


def render_summary(r):
    c, cov = r["colors"], r["coverage"]
    lines = [f"# Design system extraction — {r['files_scanned']} files",
             f"Stack: {', '.join(f'{k} {v}' for k, v in r['stack'].items()) or 'not detected'}", "",
             "## Colours",
             f"- {c['distinct']} distinct colour values → {c['clusters']} perceptual groups "
             f"({c['near_duplicate_groups']} groups of near-duplicates to consolidate)"]
    for p in c["palette"][:12]:
        roles = ", ".join(f"{k} {v}" for k, v in sorted(p["roles"].items(), key=lambda x: -x[1]))
        dup = f", merges {len(p['variants'])} values" if len(p["variants"]) > 1 else ""
        lines.append(f"- `{p['hex']}` ×{p['uses']} ({roles}{dup}) · contrast vs white {p['contrast_vs_white']}, "
                     f"vs black {p['contrast_vs_black']}{' · token' if p['declared_as_token'] else ''}")
    fails = [x for x in r["contrast_checks"] if not x["aa_normal"]]
    lines += ["", "## Contrast (text colours on the most used backgrounds — verify in context)",
              f"- {len(fails)} of {len(r['contrast_checks'])} candidate pairs below 4.5:1"]
    lines += [f"- `{x['text']}` on `{x['background']}`: {x['ratio']}:1" for x in fails[:8]]
    t = r["typography"]
    lines += ["", "## Typography",
              f"- Families: {', '.join(f'{f} ×{n}' for f, n in t['families'][:5]) or 'none found'}",
              f"- Font sizes: {t['sizes']['distinct']} distinct; most used "
              f"{', '.join(f'{v:g}px ×{n}' for v, n in t['sizes']['most_used'][:8])}; ratio ≈ {t['size_ratio_estimate']}",
              f"- Weights: {', '.join(f'{w} ×{n}' for w, n in t['weights'][:6])}",
              "", "## Spacing, radius, elevation, layers",
              f"- Spacing: {r['spacing']['distinct']} distinct values, {r['spacing']['on_grid_pct']}% on a 4px grid; most used "
              f"{', '.join(f'{v:g}px ×{n}' for v, n in r['spacing']['most_used'][:8])}",
              f"- Radius: {r['radius']['distinct']} distinct; most used {', '.join(f'{v:g}px ×{n}' for v, n in r['radius']['most_used'][:6])}",
              f"- Shadows: {r['shadows']['distinct']} distinct · z-index: {r['z_index']['distinct']} distinct values "
              f"({', '.join(v for v, _ in r['z_index']['values'][:8])})",
              f"- Breakpoints: {', '.join(f'{b} ×{n}' for b, n in r['breakpoints'][:8]) or 'none found'}",
              "", "## Tokens and coverage",
              f"- CSS custom properties: {r['tokens']['custom_properties_defined']} defined, {r['tokens']['custom_properties_used']} used; "
              f"{len(r['tokens']['defined_never_used'])} defined but never used, {len(r['tokens']['used_never_defined'])} used but not defined here"
              f"; SCSS variables: {r['tokens']['scss_variables_defined']}"]
    for k, v in cov.items():
        lines.append(f"- {k}: {v['tokenized_pct']}% tokenized ({v['tokenized']} via tokens, {v['hardcoded']} hardcoded)")
    if r["tailwind"]["palette_classes"] or r["tailwind"]["arbitrary_values"]:
        lines += ["", "## Tailwind",
                  f"- Palette classes: {', '.join(f'{k} ×{n}' for k, n in r['tailwind']['palette_classes'][:10])}",
                  f"- Arbitrary values (bypass the theme): {', '.join(f'{k} ×{n}' for k, n in r['tailwind']['arbitrary_values'][:10])}"]
    return "\n".join(lines) + "\n"


def write_html(path, r):
    esc = html.escape
    def badge(ratio):
        return f'<span class="b {"ok" if ratio >= 4.5 else "lg" if ratio >= 3 else "ko"}">{ratio}</span>'
    swatches = []
    for p in r["colors"]["palette"][:60]:
        variants = "".join(f'<i title="{esc(v["hex"])} ×{v["count"]}" style="background:{esc(v["hex"])}"></i>'
                           for v in p["variants"][1:8])
        roles = ", ".join(f"{esc(k)} {v}" for k, v in sorted(p["roles"].items(), key=lambda x: -x[1]))
        swatches.append(
            f'<figure><div class="sw" style="background:{esc(p["hex"])}"><span style="color:#fff">Aa</span>'
            f'<span style="color:#000">Aa</span></div><figcaption><b>{esc(p["hex"])}</b> ×{p["uses"]}'
            f'<br><small>{roles}</small><br>white {badge(p["contrast_vs_white"])} black {badge(p["contrast_vs_black"])}'
            f'{"<br><small>declared token</small>" if p["declared_as_token"] else ""}'
            f'{f"<div class=v><small>merges</small>{variants}</div>" if variants else ""}</figcaption></figure>')
    sizes = "".join(f'<div class="ts" style="font-size:{v:g}px">{v:g}px <small>×{n}</small> The quick brown fox</div>'
                    for v, n in sorted(r["typography"]["sizes"]["most_used"]))
    spaces = "".join(f'<div class="sp"><span style="width:{min(v, 400):g}px"></span>{v:g}px <small>×{n}</small></div>'
                     for v, n in sorted(r["spacing"]["most_used"]))
    radii = "".join(f'<div class="rd" style="border-radius:{v:g}px">{v:g}px<br><small>×{n}</small></div>'
                    for v, n in sorted(r["radius"]["most_used"]))
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Design System Palette</title><link rel="icon" href="data:,"><style>
:root{{--bg:#fafafa;--fg:#1d1d1f;--muted:#5f6368;--card:#fff;--line:#e2e2e5}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151517;--fg:#ececf0;--muted:#a0a0a8;--card:#1f1f23;--line:#33333a}}}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:1100px;margin:auto}} h2{{margin-top:40px;border-bottom:1px solid var(--line);padding-bottom:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}}
figure{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
.sw{{height:76px;border-bottom:1px solid var(--line);display:flex;justify-content:space-around;align-items:center;font-weight:600;font-size:20px}}
figcaption{{padding:8px 10px;font-size:12.5px;color:var(--muted)}} figcaption b{{color:var(--fg);font-family:ui-monospace,monospace}}
.b{{display:inline-block;padding:0 5px;border-radius:4px;font-weight:600;color:#fff}} .ok{{background:#1e7e34}} .lg{{background:#9a6700}} .ko{{background:#b42318}}
.v{{display:flex;gap:4px;align-items:center;margin-top:4px;flex-wrap:wrap}} .v i{{width:14px;height:14px;border-radius:3px;border:1px solid var(--line)}}
.ts{{margin:6px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} small{{color:var(--muted)}}
.sp{{display:flex;align-items:center;gap:10px;margin:4px 0;font-size:13px}} .sp span{{display:inline-block;height:12px;background:#4f6bed;border-radius:2px}}
.rds{{display:flex;flex-wrap:wrap;gap:12px}} .rd{{width:76px;height:76px;border:2px solid #4f6bed;display:flex;align-items:center;justify-content:center;text-align:center;font-size:12px}}
</style></head><body><main>
<h1>Design system — extracted palette</h1>
<p><small>{r['files_scanned']} files · {r['colors']['distinct']} colour values grouped into {r['colors']['clusters']} perceptual groups
({r['colors']['near_duplicate_groups']} with near-duplicates). Badges: WCAG contrast of white or black text on the colour
(green ≥ 4.5, amber ≥ 3, red &lt; 3).</small></p>
<h2>Palette</h2><div class="grid">{''.join(swatches)}</div>
<h2>Type scale</h2>{sizes or '<p><small>No font sizes found.</small></p>'}
<h2>Spacing</h2>{spaces or '<p><small>No spacing values found.</small></p>'}
<h2>Radius</h2><div class="rds">{radii or '<small>No radius values found.</small>'}</div>
</main></body></html>"""
    with open(path, "w") as fh:
        fh.write(doc)


if __name__ == "__main__":
    main()
