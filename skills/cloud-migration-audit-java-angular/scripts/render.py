"""Renderers of the cloud migration audit: Markdown report, action plan, checklist and standalone HTML dashboard.

Everything is generated from cloud-migration-findings.json, so the four documents always agree with
the source of truth and with each other. Deterministic, self-contained HTML (inline CSS, inline SVG,
a few lines of JavaScript for filters), no external resources. Standard library only.
"""
import html
import json
import re
from collections import OrderedDict

from catalog import DOMAINS, SEVERITIES, STATUSES
from findings import RESILIENCE_CONTROLS, SECURITY_CONTROLS

ST_ICON = {"DONE": "✅", "PARTIALLY DONE": "🟡", "NOT DONE": "❌", "NOT VERIFIED": "❔", "NOT APPLICABLE": "⚪"}
SEV_ICON = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵", "INFO": "⚪"}
VERDICT_ICON = {"GO": "🟢", "CONDITIONAL GO": "🟠", "NO-GO": "🔴"}
PRIO_TITLE = OrderedDict(P0="P0 — Production blockers", P1="P1 — High priority", P2="P2 — Important improvements",
                         P3="P3 — Low-risk optimisations")


def ref(e):
    return f"`{e['repo']}:{e['file']}" + (f":{e['line']}`" if e.get("line") else "`")


def refs(evidence, n=4):
    out = ", ".join(ref(e) for e in evidence[:n])
    return out + (f" (+{len(evidence) - n})" if len(evidence) > n else "") if out else "—"


def bar(pct, width=20):
    n = int(round(width * pct / 100.0))
    return "█" * n + "░" * (width - n)


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def lang_of(code):
    s = code.lstrip()
    if s.startswith("<"):
        return "xml"
    if re.search(r"^\s*(apiVersion|kind|spec|resources|metadata|[\w.-]+:\s*$)", code, re.M) and not re.search(r";\s*$", code, re.M):
        return "yaml"
    if re.search(r"^\s*(server|spring|management|[\w-]+\.[\w.-]+)\s*[=:]", code, re.M) and "{" not in code:
        return "properties"
    if re.search(r"^\s*(FROM|RUN|USER|COPY|ENTRYPOINT)\b", code, re.M):
        return "dockerfile"
    if re.search(r"\b(public|private|class|@\w+|import)\b", code) and ";" in code:
        return "java"
    if re.search(r"\b(const|export|import|=>|interface)\b", code):
        return "typescript"
    if re.search(r"^\s*(location|server|add_header|listen)\b", code, re.M):
        return "nginx"
    return "text"


def finding_block(f, level="###"):
    w = [f"{level} {f['id']} · {SEV_ICON[f['severity']]} {f['severity']} · {f['title']}", ""]
    w.append(f"**Control:** {f['control']}" + (f" (also {', '.join(f['related_controls'])})" if f.get("related_controls") else "")
             + f" · **Priority:** {f['priority']} · **Type:** {f['kind']}"
             + (" · **Production blocker**" if f["blocker"] else "") + (" · **Cross-repository**" if f["cross_repo"] else "")
             + f" · **Repositories:** {', '.join(f['repos']) or '—'}" + (f" · **Effort:** {f['effort']}" if f.get("effort") else ""))
    w.append("")
    if f["evidence"]:
        w.append("**Evidence**")
        w += [f"- {ref(e)} — {e['note']}" for e in f["evidence"]]
        w.append("")
    w += [f"**Failure scenario and impact.** {f['impact']}", "", f"**Remediation.** {f['remediation']}", ""]
    if f.get("example"):
        w += [f"```{lang_of(f['example'])}", f["example"], "```", ""]
    w += [f"**Validation.** {f['validation']}", "", f"**Acceptance criteria.** {f['acceptance']}", ""]
    if f.get("runtime_check"):
        w += [f"**Needs live verification.** {f['runtime_check']}", ""]
    if f.get("depends_on"):
        w += [f"**Depends on:** {', '.join(f['depends_on'])}", ""]
    return w


def control_table(controls, findings_by_ctrl):
    w = ["| Control | Status | Assessment | Evidence | Findings |", "| --- | --- | --- | --- | --- |"]
    for c in controls:
        fs = ", ".join(f["id"] for f in findings_by_ctrl.get(c["id"], [])) or "—"
        w.append(f"| **{c['id']}** {cell(c['title'])} | {ST_ICON[c['status']]} {c['status']} | {cell(c['summary'])} | "
                 f"{refs(c['evidence'], 3)} | {fs} |")
    return w


def md_report(doc):
    a, m, d = doc["audit"], doc["metrics"], doc["decision"]
    o = m["overall"]
    ctrls, fnds = doc["controls"], doc["findings"]
    by_ctrl = OrderedDict()
    for f in fnds:
        for cid in [f["control"]] + f.get("related_controls", []):
            by_ctrl.setdefault(cid, []).append(f)
    w = [f"# {a['title']}", "",
         f"Date: {a['date']} · Scope: {a['scope']} · Method: {a['method']} · Access: {a['access']}", ""]
    w += ["## 1. Executive summary", "",
          f"**Decision: {VERDICT_ICON[d['verdict']]} {d['verdict']}** · Migration completion **{o['completion_pct']}%** "
          f"(confirmed) · Audit coverage **{o['coverage_pct']}%** · {len(d['blockers'])} production blocker(s) · "
          f"{m['findings']['total']} finding(s): " + ", ".join(f"{v} {k}" for k, v in m["findings"]["by_severity"].items() if v), ""]
    if doc["summary"].get("executive_summary"):
        w += [doc["summary"]["executive_summary"], ""]
    top = [f for f in fnds if f["severity"] in ("CRITICAL", "HIGH")][:7]
    if top:
        w.append("**Most important risks**")
        w += [f"- {SEV_ICON[f['severity']]} **{f['id']}** {f['title']} ({', '.join(f['repos'])})" for f in top]
        w.append("")
    if doc["summary"].get("key_risks"):
        w += ["**Key observations**"] + [f"- {k}" for k in doc["summary"]["key_risks"]] + [""]
    w += ["## 2. Migration readiness assessment", "",
          f"| Indicator | Value |", "| --- | --- |",
          f"| Decision | {VERDICT_ICON[d['verdict']]} **{d['verdict']}** |",
          f"| Production blockers | {len(d['blockers'])} {('(' + ', '.join(d['blockers']) + ')') if d['blockers'] else ''} |",
          f"| Gate controls not DONE | {len(d['gate_controls_open'])} |",
          f"| Migration completion (confirmed) | {o['completion_pct']}% `{bar(o['completion_pct'])}` |",
          f"| Audit coverage | {o['coverage_pct']}% `{bar(o['coverage_pct'])}` |",
          f"| Completion if every unverified control were done | {o['completion_upper_bound_pct']}% |", "",
          "Decision rules:", ""] + [f"- {r}" for r in d["rules"]] + [""]
    if doc["summary"].get("decision_rationale"):
        w += [doc["summary"]["decision_rationale"], ""]
    w += ["## 3. Analysed repositories and detected architecture", "",
          "| Repository | Roles | Revision | Branch | Uncommitted changes | Files |", "| --- | --- | --- | --- | --- | --- |"]
    for r in doc["repositories"]:
        w.append(f"| {r['label']} | {', '.join(r['roles'])} | {r.get('head') or '—'} | {r.get('branch') or '—'} | "
                 f"{'yes' if r.get('dirty') else 'no' if r.get('dirty') is not None else '—'} | {r.get('files', '—')} |")
    w.append("")
    arch = doc["architecture"]
    if arch.get("summary"):
        w += [arch["summary"], ""]
    if arch.get("migration_context"):
        w += [f"**Migration context.** {arch['migration_context']}", ""]
    if arch.get("components"):
        w += ["| Component | Repository | Role |", "| --- | --- | --- |"] + \
             [f"| {cell(c['name'])} | {c['repo']} | {cell(c['description'])} |" for c in arch["components"]] + [""]
    for label, st in arch.get("stack", {}).items():
        if st:
            w.append(f"- **{label}**: {', '.join(st)}")
    w += ["", "## 4. End-to-end migration status overview", "",
          "| Domain | ✅ Done | 🟡 Partial | ❌ Not done | ❔ Not verified | ⚪ N/A | Completion | Coverage |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for dom, b in m["by_domain"].items():
        w.append(f"| {dom} — {DOMAINS[dom]} | {b['done']} | {b['partially_done']} | {b['not_done']} | {b['not_verified']} | "
                 f"{b['not_applicable']} | {b['completion_pct']}% `{bar(b['completion_pct'], 10)}` | {b['coverage_pct']}% |")
    w.append(f"| **All domains** | **{o['done']}** | **{o['partially_done']}** | **{o['not_done']}** | **{o['not_verified']}** | "
             f"**{o['not_applicable']}** | **{o['completion_pct']}%** | **{o['coverage_pct']}%** |")
    w += ["", "## 5. Migration completion and audit coverage metrics", ""]
    w += [f"- **Completion** = {m['formulas']['completion']}.", f"- **Coverage** = {m['formulas']['coverage']}.",
          f"- **Upper bound** = {m['formulas']['completion_upper_bound']}.", f"- {m['formulas']['note']}", "",
          f"Overall: {o['applicable']} applicable controls of {o['total']} → completion {o['done']}/{o['applicable']} = "
          f"{o['completion_pct']}%, coverage {o['done'] + o['partially_done'] + o['not_done']}/{o['applicable']} = {o['coverage_pct']}%.", "",
          "| Repository | Controls involved | Done | Partial | Not done | Not verified | Completion | Critical | High | Medium | Low | Info |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for label, b in m["by_repo"].items():
        fs = b["findings"]
        w.append(f"| {label} | {b['applicable']} | {b['done']} | {b['partially_done']} | {b['not_done']} | {b['not_verified']} | "
                 f"{b['completion_pct']}% | {fs['CRITICAL']} | {fs['HIGH']} | {fs['MEDIUM']} | {fs['LOW']} | {fs['INFO']} |")
    w += ["", "Findings by severity: " + " · ".join(f"{SEV_ICON[k]} {k} {v}" for k, v in m["findings"]["by_severity"].items()),
          f"Findings by type: {m['findings']['confirmed']} confirmed in code/configuration, {m['findings']['potential']} potential "
          f"(depend on runtime facts); {m['findings']['cross_repo']} cross-repository.", ""]
    if m["unassessed_controls"]:
        w += [f"Controls not assessed in this run (counted as NOT VERIFIED): {', '.join(m['unassessed_controls'])}.", ""]
    cmp_ = doc.get("comparison")
    if cmp_:
        w += ["**Changes since the previous audit**", "",
              f"- Previous audit {cmp_['previous_date']} ({cmp_['previous_verdict']}) → now {cmp_['current_verdict']}.",
              f"- Completion {cmp_['completion']['previous']}% → {cmp_['completion']['current']}% ({cmp_['completion']['delta']:+}); "
              f"coverage {cmp_['coverage']['previous']}% → {cmp_['coverage']['current']}% ({cmp_['coverage']['delta']:+}).",
              f"- New findings: {', '.join(cmp_['new']) or 'none'}; persisting: {len(cmp_['persisting'])}; "
              f"resolved: {', '.join(r['id'] for r in cmp_['resolved']) or 'none'}.",
              f"- No longer reported but control still not done (to confirm): "
              f"{', '.join(r['id'] + ' (' + str(r['control_status_now']) + ')' for r in cmp_['unconfirmed']) or 'none'}.",
              f"- Control status changes: " + (", ".join(f"{c['control']} {c['previous']} → {c['current']}" for c in cmp_["control_changes"]) or "none"),
              f"- {cmp_['rule']}", ""]
    w += ["## 6. Detailed audit results by domain", ""]
    for dom in DOMAINS:
        cs = [c for c in ctrls if c["domain"] == dom]
        w += [f"### {dom} — {DOMAINS[dom]}", ""] + control_table(cs, by_ctrl) + [""]
    for num, title, status in ((7, "Successfully migrated components", "DONE"), (8, "Partially migrated components", "PARTIALLY DONE"),
                               (9, "Missing migration requirements", "NOT DONE")):
        cs = [c for c in ctrls if c["status"] == status]
        w += [f"## {num}. {title}", ""]
        if not cs:
            w += ["None.", ""]
            continue
        for c in cs:
            fs = by_ctrl.get(c["id"], [])
            w.append(f"- **{c['id']}** {c['title']} — {c['summary']}" + (f" Evidence: {refs(c['evidence'], 3)}." if c["evidence"] else "")
                     + (f" Findings: {', '.join(f['id'] for f in fs)}." if fs else ""))
        w.append("")
    nv = [c for c in ctrls if c["status"] == "NOT VERIFIED"]
    w += ["## 10. Unverified controls and evidence gaps", "",
          "These controls are counted as incomplete. Runtime controls need live access (cluster, IBM Cloud account, JFrog, Argo CD) "
          "or evidence from the teams that operate them.", ""]
    if nv:
        w += ["| Control | Gate | Needs live access | Why not verified |", "| --- | --- | --- | --- |"]
        w += [f"| **{c['id']}** {cell(c['title'])} | {'yes' if c['gate'] else 'no'} | {'yes' if c['runtime'] else 'no'} | {cell(c['summary'])} |"
              for c in nv]
    else:
        w.append("None.")
    w += ["", "## 11. Critical production risks", ""]
    crit = [f for f in fnds if f["severity"] in ("CRITICAL", "HIGH") or f["blocker"]]
    for f in crit:
        w += finding_block(f)
    if not crit:
        w += ["No CRITICAL or HIGH finding.", ""]
    w += ["## 12. Cross-repository inconsistencies", ""]
    xr = [f for f in fnds if f["cross_repo"]]
    w += (["| Finding | Severity | Repositories | Summary |", "| --- | --- | --- | --- |"] +
          [f"| {f['id']} | {SEV_ICON[f['severity']]} {f['severity']} | {', '.join(sorted(set(f['repos']) | {e['repo'] for e in f['evidence']}))} | "
           f"{cell(f['title'])} |" for f in xr]) if xr else ["None found."]
    w += ["", "## 13. Security and resilience findings", ""]
    for label, ids in (("Security", SECURITY_CONTROLS), ("Resilience and multi-instance behaviour", RESILIENCE_CONTROLS)):
        fs = [f for f in fnds if f["control"] in ids]
        w += [f"**{label}**", ""]
        w += (["| Finding | Severity | Control | Summary |", "| --- | --- | --- | --- |"] +
              [f"| {f['id']} | {SEV_ICON[f['severity']]} {f['severity']} | {f['control']} | {cell(f['title'])} |" for f in fs]) if fs else ["None."]
        w.append("")
    w += ["## 14. Prioritised recommendations", "", "Full details, dependencies and acceptance criteria: `cloud-migration-action-plan.md`.", ""]
    for p, title in PRIO_TITLE.items():
        fs = [f for f in fnds if f["priority"] == p]
        if fs:
            w += [f"**{title}**"] + [f"{i}. **{f['id']}** {f['title']} — {f['remediation'].split('. ')[0].rstrip('.')}." for i, f in enumerate(fs, 1)] + [""]
    w += ["## 15. Validation and production readiness checklist", ""]
    for c in [c for c in ctrls if c["gate"]]:
        box = "x" if c["status"] in ("DONE", "NOT APPLICABLE") else " "
        w.append(f"- [{box}] **{c['id']}** {c['title']} — {ST_ICON[c['status']]} {c['status']}")
    tests = [f for f in fnds if f["priority"] in ("P0", "P1")]
    if tests:
        w += ["", "**Production tests required by the open P0/P1 findings**", ""] + [f"- [ ] {f['id']}: {f['validation']}" for f in tests]
    w += ["", "## 16. Final recommendation", "", f"### {VERDICT_ICON[d['verdict']]} {d['verdict']}", ""]
    if d["blockers"]:
        w += ["**Blockers to remove before production:**"] + [f"- {fid}: {next(f['title'] for f in fnds if f['id'] == fid)}" for fid in d["blockers"]] + [""]
    if d["conditions"]:
        w += ["**Conditions:**"] + [f"- {c}" for c in d["conditions"]] + [""]
    runtime = [c for c in ctrls if c["runtime"] and c["status"] == "NOT VERIFIED"]
    if runtime:
        w += ["**Remaining verifications that need live access:** " + ", ".join(f"{c['id']} ({c['title']})" for c in runtime), ""]
    other = [f for f in fnds if not (f["severity"] in ("CRITICAL", "HIGH") or f["blocker"])]
    if other:
        w += ["## Appendix — Other findings (MEDIUM, LOW, INFO)", ""]
        for f in other:
            w += finding_block(f)
    if doc.get("conflicts"):
        w += ["## Appendix — Conflicting assessments (resolved conservatively)", ""] + \
             [f"- {c['control']}: " + ", ".join(f"{g}={s}" for g, s in sorted(c["assessments"].items())) + f" → kept {c['kept']}"
              for c in doc["conflicts"]] + [""]
    return "\n".join(w).rstrip() + "\n"


def action_plan(doc):
    fnds, ctrls = doc["findings"], doc["controls"]
    w = [f"# Cloud migration action plan — {doc['audit']['title']}", "",
         f"Date: {doc['audit']['date']} · Decision: {VERDICT_ICON[doc['decision']['verdict']]} {doc['decision']['verdict']} · "
         f"Source of truth: `cloud-migration-findings.json`", "",
         "| Priority | Actions | Meaning |", "| --- | --- | --- |"]
    meaning = {"P0": "production blockers: fix before go-live", "P1": "HIGH risks: fix before go-live or under an agreed condition",
               "P2": "important improvements for the next iterations", "P3": "low-risk optimisations"}
    for p in PRIO_TITLE:
        w.append(f"| {p} | {sum(1 for f in fnds if f['priority'] == p)} | {meaning[p]} |")
    w.append("")
    for p, title in PRIO_TITLE.items():
        fs = [f for f in fnds if f["priority"] == p]
        if not fs:
            continue
        w += [f"## {title}", ""]
        for f in fs:
            files = sorted({f"{e['repo']}:{e['file']}" for e in f["evidence"]})
            w += [f"### {f['id']} — {f['title']}", "",
                  f"- **Related findings:** {f['id']} (control {f['control']})" + (f"; depends on {', '.join(f['depends_on'])}" if f["depends_on"] else ""),
                  f"- **Why:** {f['impact']}", f"- **Proposed implementation:** {f['remediation']}",
                  f"- **Affected repositories and files:** {', '.join(f'`{x}`' for x in files) or ', '.join(f['repos'])}",
                  f"- **Dependencies:** {', '.join(f['depends_on']) or 'none identified'}",
                  f"- **Estimated complexity:** {f.get('effort') or 'not estimated'}",
                  f"- **Validation steps:** {f['validation']}", f"- **Acceptance criteria:** {f['acceptance']}"]
            if f.get("runtime_check"):
                w.append(f"- **Live verification:** {f['runtime_check']}")
            w.append("")
            if f.get("example"):
                w += [f"```{lang_of(f['example'])}", f["example"], "```", ""]
    nv = [c for c in ctrls if c["status"] == "NOT VERIFIED" and c["gate"]]
    if nv:
        w += ["## Pending verifications (gate controls without evidence)", "",
              "| Control | How to obtain evidence |", "| --- | --- |"]
        w += [f"| **{c['id']}** {cell(c['title'])} | {'Live check (cluster, IBM Cloud, JFrog or Argo CD) or evidence from the platform team: ' if c['runtime'] else 'Evidence from the repositories or the owning team: '}"
              f"{cell(c['done_criteria'])} |" for c in nv]
        w.append("")
    return "\n".join(w).rstrip() + "\n"


def checklist(doc):
    by_ctrl = OrderedDict()
    for f in doc["findings"]:
        for cid in [f["control"]] + f.get("related_controls", []):
            by_ctrl.setdefault(cid, []).append(f["id"])
    o = doc["metrics"]["overall"]
    w = [f"# Cloud migration checklist — {doc['audit']['title']}", "",
         f"Date: {doc['audit']['date']} · Completion {o['completion_pct']}% · Coverage {o['coverage_pct']}% · "
         f"Decision {doc['decision']['verdict']}", "",
         "Legend: `[x]` done and verified · `[ ]` open (partial, not done or not verified) · `N/A` not applicable · 🚩 gate control", ""]
    for dom in DOMAINS:
        cs = [c for c in doc["controls"] if c["domain"] == dom]
        b = doc["metrics"]["by_domain"][dom]
        w += [f"## {dom} — {DOMAINS[dom]} ({b['done']}/{b['applicable']} done)", ""]
        for c in cs:
            flag = " 🚩" if c["gate"] else ""
            ids = f" → {', '.join(by_ctrl[c['id']])}" if c["id"] in by_ctrl else ""
            if c["status"] == "NOT APPLICABLE":
                w.append(f"- N/A {c['id']} {c['title']}{flag} — {c['summary']}")
            elif c["status"] == "DONE":
                w.append(f"- [x] {c['id']} {c['title']}{flag}")
            elif c["status"] == "NOT VERIFIED":
                w.append(f"- [ ] {c['id']} {c['title']}{flag} — ❔ pending validation" + (" (live access)" if c["runtime"] else "") + ids)
            else:
                w.append(f"- [ ] {c['id']} {c['title']}{flag} — {ST_ICON[c['status']]} {c['status']}{ids}")
        w.append("")
    tests = [f for f in doc["findings"] if f["priority"] in ("P0", "P1")]
    runtime = [c for c in doc["controls"] if c["runtime"] and c["status"] != "DONE" and c["status"] != "NOT APPLICABLE"]
    w += ["## Required production tests", ""]
    w += [f"- [ ] {f['id']}: {f['validation']}" for f in tests]
    w += [f"- [ ] {c['id']}: verify on the live platform — {c['done_criteria']}" for c in runtime]
    if not tests and not runtime:
        w.append("None.")
    return "\n".join(w).rstrip() + "\n"


# ------------------------------------------------------------------ HTML
COLORS = {"DONE": "#1f9d55", "PARTIALLY DONE": "#e0a100", "NOT DONE": "#d64545", "NOT VERIFIED": "#7a869a", "NOT APPLICABLE": "#c1c7d0"}
SEV_COLORS = {"CRITICAL": "#b42318", "HIGH": "#e8590c", "MEDIUM": "#d4a106", "LOW": "#2f6fd6", "INFO": "#8590a2"}
VERDICT_COLORS = {"GO": "#1f9d55", "CONDITIONAL GO": "#e8590c", "NO-GO": "#b42318"}

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--fg:#172b4d;--muted:#5e6c84;--line:#dfe1e6;--accent:#0c66e4;--code:#f1f2f4}
@media (prefers-color-scheme:dark){:root{--bg:#161a1d;--card:#1d2125;--fg:#c7d1db;--muted:#9fadbc;--line:#38414a;--accent:#579dff;--code:#22272b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent)}header{background:var(--card);border-bottom:1px solid var(--line);padding:18px 24px}
header h1{margin:0 0 4px;font-size:22px}header .meta{color:var(--muted);font-size:13px}
nav{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:8px 24px;display:flex;gap:16px;flex-wrap:wrap}
nav a{text-decoration:none;font-weight:600;font-size:13px}main{max-width:1280px;margin:0 auto;padding:20px 24px 60px}
section{margin-top:28px}h2{font-size:18px;border-bottom:2px solid var(--line);padding-bottom:6px}h3{font-size:15px;margin:18px 0 8px}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.kpi .v{font-size:28px;font-weight:700}.kpi .l{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.verdict{display:inline-block;color:#fff;font-weight:800;border-radius:6px;padding:6px 14px;font-size:18px}
.pill{display:inline-block;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:700;color:#fff;white-space:nowrap}
.bar{display:flex;height:16px;border-radius:4px;overflow:hidden;background:var(--line);min-width:120px}.bar span{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:10px;font-size:12px;color:var(--muted)}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}
table{border-collapse:collapse;width:100%;background:var(--card)}th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.03em}.tw{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
code{background:var(--code);border-radius:3px;padding:0 4px;font-size:12px}pre{background:var(--code);padding:10px;border-radius:6px;overflow-x:auto;font-size:12px}
details>summary{cursor:pointer;font-weight:600}details .body{padding:8px 0 4px}.filters{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.filters select,.filters input{font:inherit;padding:5px 8px;border:1px solid var(--line);border-radius:5px;background:var(--card);color:var(--fg)}
.blocker{border-left:4px solid #b42318}.muted{color:var(--muted)}.small{font-size:12px}ul.tight{margin:6px 0;padding-left:20px}
.hbar{display:flex;align-items:center;gap:8px;margin:4px 0}.hbar .lab{width:90px;font-size:12px}.hbar .track{flex:1;background:var(--line);border-radius:3px;height:12px}
.hbar .fill{height:12px;border-radius:3px}.hbar .n{width:30px;text-align:right;font-weight:700}
@media print{nav{display:none}details{open:true}}
@media (max-width:700px){main{padding:12px}header,nav{padding-left:12px;padding-right:12px}}
"""

JS = """
function applyFilters(){
  const v=id=>document.getElementById(id).value, q=v('f-q').toLowerCase();
  let shown=0;
  document.querySelectorAll('#findings tbody tr.f').forEach(tr=>{
    const ok=(!v('f-sev')||tr.dataset.sev===v('f-sev'))&&(!v('f-dom')||tr.dataset.dom===v('f-dom'))&&
      (!v('f-repo')||tr.dataset.repos.split(' ').includes(v('f-repo')))&&(!v('f-prio')||tr.dataset.prio===v('f-prio'))&&
      (!q||tr.textContent.toLowerCase().includes(q));
    tr.style.display=ok?'':'none'; if(ok)shown++;});
  document.getElementById('f-count').textContent=shown+' shown';
}
document.addEventListener('input',e=>{if(e.target.closest('.filters'))applyFilters();});
"""


def esc(x):
    return html.escape(str(x), quote=True)


def donut(counts, total):
    parts, off = [], 25.0
    for st in STATUSES:
        n = counts.get(st, 0)
        if not n or not total:
            continue
        pct = 100.0 * n / total
        parts.append(f'<circle r="15.915" cx="21" cy="21" fill="transparent" stroke="{COLORS[st]}" stroke-width="6" '
                     f'stroke-dasharray="{pct:.2f} {100 - pct:.2f}" stroke-dashoffset="{off:.2f}"><title>{esc(st)}: {n}</title></circle>')
        off -= pct
    return (f'<svg viewBox="0 0 42 42" width="170" height="170" role="img" aria-label="Control status distribution">'
            f'<circle r="15.915" cx="21" cy="21" fill="transparent" stroke="var(--line)" stroke-width="6"/>{"".join(parts)}'
            f'<text x="21" y="20" text-anchor="middle" font-size="6" font-weight="700" fill="currentColor">{total}</text>'
            f'<text x="21" y="26" text-anchor="middle" font-size="3" fill="currentColor">controls</text></svg>')


def stacked(b):
    total = b["total"] or 1
    segs = "".join(f'<span style="width:{100.0 * b[k] / total:.2f}%;background:{COLORS[st]}" title="{esc(st)}: {b[k]}"></span>'
                   for st, k in (("DONE", "done"), ("PARTIALLY DONE", "partially_done"), ("NOT DONE", "not_done"),
                                 ("NOT VERIFIED", "not_verified"), ("NOT APPLICABLE", "not_applicable")) if b[k])
    return f'<div class="bar">{segs}</div>'


def pill(text, color):
    return f'<span class="pill" style="background:{color}">{esc(text)}</span>'


def html_refs(evidence):
    return "".join(f"<li><code>{esc(e['repo'])}:{esc(e['file'])}{(':' + str(e['line'])) if e.get('line') else ''}</code> — {esc(e['note'])}</li>"
                   for e in evidence)


def html_report(doc):
    a, m, d = doc["audit"], doc["metrics"], doc["decision"]
    o = m["overall"]
    fnds, ctrls = doc["findings"], doc["controls"]
    counts = {st: sum(1 for c in ctrls if c["status"] == st) for st in STATUSES}
    legend = "".join(f'<span><i style="background:{COLORS[s]}"></i>{esc(s)} {counts[s]}</span>' for s in STATUSES)
    sev = m["findings"]["by_severity"]
    smax = max(sev.values() or [1]) or 1
    sevbars = "".join(f'<div class="hbar"><span class="lab">{esc(s)}</span><span class="track"><span class="fill" style="display:block;'
                      f'width:{100.0 * n / smax:.1f}%;background:{SEV_COLORS[s]}"></span></span><span class="n">{n}</span></div>'
                      for s, n in sev.items())
    w = [f"<header><h1>{esc(a['title'])}</h1><div class='meta'>{esc(a['date'])} · {esc(a['scope'])} · {esc(a['access'])}</div></header>",
         "<nav><a href='#dashboard'>Dashboard</a><a href='#decision'>Decision</a><a href='#domains'>Domains</a><a href='#repos'>Repositories</a>"
         "<a href='#blockers'>Blockers</a><a href='#findings'>Findings</a><a href='#controls'>Controls</a><a href='#gaps'>Evidence gaps</a>"
         "<a href='#plan'>Action plan</a></nav><main>"]
    w.append(f"<section id='dashboard'><div class='grid'>"
             f"<div class='card kpi'><div class='l'>Decision</div><div style='margin-top:6px'><span class='verdict' style='background:{VERDICT_COLORS[d['verdict']]}'>"
             f"{esc(d['verdict'])}</span></div><div class='small muted' style='margin-top:6px'>{len(d['blockers'])} blocker(s) · {len(d['conditions'])} condition(s)</div></div>"
             f"<div class='card kpi'><div class='l'>Migration completion</div><div class='v'>{o['completion_pct']}%</div>"
             f"<div class='small muted'>{o['done']} DONE / {o['applicable']} applicable · up to {o['completion_upper_bound_pct']}% if all unverified were done</div></div>"
             f"<div class='card kpi'><div class='l'>Audit coverage</div><div class='v'>{o['coverage_pct']}%</div>"
             f"<div class='small muted'>{o['done'] + o['partially_done'] + o['not_done']} established / {o['applicable']} · {o['not_verified']} not verified</div></div>"
             f"<div class='card kpi'><div class='l'>Findings</div><div class='v'>{m['findings']['total']}</div>"
             f"<div class='small muted'>{m['findings']['confirmed']} confirmed · {m['findings']['potential']} potential · {m['findings']['cross_repo']} cross-repository</div></div>"
             f"</div><div class='grid' style='margin-top:14px'><div class='card'><h3 style='margin-top:0'>Control status</h3>"
             f"<div style='display:flex;gap:16px;align-items:center;flex-wrap:wrap'>{donut(counts, len(ctrls))}<div class='legend' style='flex-direction:column'>{legend}</div></div></div>"
             f"<div class='card'><h3 style='margin-top:0'>Findings by severity</h3>{sevbars}</div>"
             f"<div class='card'><h3 style='margin-top:0'>Formulas</h3><p class='small'><b>Completion</b> = {esc(m['formulas']['completion'])}.<br>"
             f"<b>Coverage</b> = {esc(m['formulas']['coverage'])}.<br>{esc(m['formulas']['note'])}</p></div></div></section>")
    summ = doc["summary"]
    w.append("<section id='decision'><h2>Executive summary and decision</h2><div class='card'>")
    if summ.get("executive_summary"):
        w.append(f"<p>{esc(summ['executive_summary'])}</p>")
    if summ.get("decision_rationale"):
        w.append(f"<p><b>Rationale.</b> {esc(summ['decision_rationale'])}</p>")
    if d["conditions"]:
        w.append("<p><b>Conditions</b></p><ul class='tight'>" + "".join(f"<li>{esc(c)}</li>" for c in d["conditions"]) + "</ul>")
    w.append("<p class='small muted'>" + "<br>".join(esc(r) for r in d["rules"]) + "</p></div>")
    if doc["architecture"].get("summary"):
        w.append(f"<h3>Architecture</h3><div class='card'><p>{esc(doc['architecture']['summary'])}</p>"
                 + (f"<p><b>Migration context.</b> {esc(doc['architecture']['migration_context'])}</p>" if doc["architecture"].get("migration_context") else "")
                 + "</div>")
    cmp_ = doc.get("comparison")
    if cmp_:
        w.append(f"<h3>Progress since {esc(cmp_['previous_date'])}</h3><div class='card small'>Verdict {esc(cmp_['previous_verdict'])} → "
                 f"<b>{esc(cmp_['current_verdict'])}</b> · completion {cmp_['completion']['previous']}% → <b>{cmp_['completion']['current']}%</b> "
                 f"({cmp_['completion']['delta']:+}) · coverage {cmp_['coverage']['previous']}% → <b>{cmp_['coverage']['current']}%</b> "
                 f"({cmp_['coverage']['delta']:+}) · new {len(cmp_['new'])} · resolved {len(cmp_['resolved'])} · persisting {len(cmp_['persisting'])} · "
                 f"to confirm {len(cmp_['unconfirmed'])}</div>")
    w.append("</section>")
    w.append("<section id='domains'><h2>Status by domain</h2><div class='tw'><table><thead><tr><th>Domain</th><th>Distribution</th><th>Done</th>"
             "<th>Partial</th><th>Not done</th><th>Not verified</th><th>N/A</th><th>Completion</th><th>Coverage</th><th>Findings</th></tr></thead><tbody>")
    for dom, b in m["by_domain"].items():
        nf = sum(b["findings"].values())
        w.append(f"<tr><td><b>{dom}</b> {esc(DOMAINS[dom])}</td><td>{stacked(b)}</td><td>{b['done']}</td><td>{b['partially_done']}</td>"
                 f"<td>{b['not_done']}</td><td>{b['not_verified']}</td><td>{b['not_applicable']}</td><td><b>{b['completion_pct']}%</b></td>"
                 f"<td>{b['coverage_pct']}%</td><td>{nf}</td></tr>")
    w.append(f"</tbody></table></div><div class='legend' style='margin-top:6px'>{legend}</div></section>")
    w.append("<section id='repos'><h2>Repositories</h2><div class='tw'><table><thead><tr><th>Repository</th><th>Roles</th><th>Revision</th>"
             "<th>Controls involved</th><th>Distribution</th><th>Completion</th><th>Findings (C/H/M/L/I)</th></tr></thead><tbody>")
    for r in doc["repositories"]:
        b = m["by_repo"][r["label"]]
        fs = b["findings"]
        w.append(f"<tr><td><b>{esc(r['label'])}</b></td><td>{esc(', '.join(r['roles']))}</td><td><code>{esc(r.get('head') or '—')}</code> "
                 f"{esc(r.get('branch') or '')}</td><td>{b['applicable']}</td><td>{stacked(b)}</td><td>{b['completion_pct']}%</td>"
                 f"<td>{fs['CRITICAL']} / {fs['HIGH']} / {fs['MEDIUM']} / {fs['LOW']} / {fs['INFO']}</td></tr>")
    w.append("</tbody></table></div></section>")
    blockers = [f for f in fnds if f["blocker"]]
    w.append("<section id='blockers'><h2>Production blockers</h2>")
    w.append("".join(f"<div class='card blocker' style='margin-bottom:8px'>{pill(f['severity'], SEV_COLORS[f['severity']])} <b>{esc(f['id'])}</b> "
                     f"{esc(f['title'])}<div class='small muted'>{esc(f['impact'])}</div></div>" for f in blockers) or "<p>None.</p>")
    w.append("</section>")
    doms = sorted({f["domain"] for f in fnds})
    repos = sorted({r for f in fnds for r in f["repos"]})
    opt = lambda vals: "".join(f"<option>{esc(v)}</option>" for v in vals)
    w.append("<section id='findings'><h2>Findings</h2><div class='filters'>"
             f"<select id='f-sev'><option value=''>All severities</option>{opt(SEVERITIES)}</select>"
             f"<select id='f-prio'><option value=''>All priorities</option>{opt(['P0', 'P1', 'P2', 'P3'])}</select>"
             f"<select id='f-dom'><option value=''>All domains</option>{opt(doms)}</select>"
             f"<select id='f-repo'><option value=''>All repositories</option>{opt(repos)}</select>"
             f"<input id='f-q' type='search' placeholder='Search'><span id='f-count' class='small muted'>{len(fnds)} shown</span></div>"
             "<div class='tw'><table><thead><tr><th>ID</th><th>Severity</th><th>Priority</th><th>Finding</th><th>Repositories</th></tr></thead><tbody>")
    for f in fnds:
        body = (f"<p><b>Control</b> {esc(f['control'])} · <b>Type</b> {esc(f['kind'])}" + (" · <b>Blocker</b>" if f["blocker"] else "")
                + (f" · <b>Effort</b> {esc(f['effort'])}" if f.get("effort") else "") + "</p>"
                + (f"<p><b>Evidence</b></p><ul class='tight'>{html_refs(f['evidence'])}</ul>" if f["evidence"] else "")
                + f"<p><b>Impact.</b> {esc(f['impact'])}</p><p><b>Remediation.</b> {esc(f['remediation'])}</p>"
                + (f"<pre>{esc(f['example'])}</pre>" if f.get("example") else "")
                + f"<p><b>Validation.</b> {esc(f['validation'])}</p><p><b>Acceptance.</b> {esc(f['acceptance'])}</p>"
                + (f"<p><b>Live verification.</b> {esc(f['runtime_check'])}</p>" if f.get("runtime_check") else "")
                + (f"<p><b>Depends on</b> {esc(', '.join(f['depends_on']))}</p>" if f["depends_on"] else ""))
        w.append(f"<tr class='f' data-sev='{esc(f['severity'])}' data-dom='{esc(f['domain'])}' data-prio='{esc(f['priority'])}' "
                 f"data-repos='{esc(' '.join(f['repos']))}'><td><b>{esc(f['id'])}</b></td><td>{pill(f['severity'], SEV_COLORS[f['severity']])}</td>"
                 f"<td>{esc(f['priority'])}</td><td><details><summary>{esc(f['title'])}</summary><div class='body small'>{body}</div></details></td>"
                 f"<td>{esc(', '.join(f['repos']))}</td></tr>")
    w.append("</tbody></table></div></section>")
    w.append("<section id='controls'><h2>Controls by domain</h2>")
    for dom in DOMAINS:
        cs = [c for c in ctrls if c["domain"] == dom]
        w.append(f"<details {'open' if any(c['status'] in ('NOT DONE', 'PARTIALLY DONE') for c in cs) else ''}><summary>{dom} — {esc(DOMAINS[dom])} "
                 f"({m['by_domain'][dom]['done']}/{m['by_domain'][dom]['applicable']} done)</summary><div class='tw' style='margin:8px 0'><table><thead>"
                 "<tr><th>Control</th><th>Status</th><th>Assessment</th><th>Evidence</th></tr></thead><tbody>")
        for c in cs:
            ev = "".join(f"<div><code>{esc(e['repo'])}:{esc(e['file'])}{(':' + str(e['line'])) if e.get('line') else ''}</code></div>" for e in c["evidence"][:3])
            w.append(f"<tr><td><b>{esc(c['id'])}</b> {esc(c['title'])}{' 🚩' if c['gate'] else ''}</td><td>{pill(c['status'], COLORS[c['status']])}</td>"
                     f"<td class='small'>{esc(c['summary'])}</td><td class='small'>{ev or '—'}</td></tr>")
        w.append("</tbody></table></div></details>")
    w.append("<p class='small muted'>🚩 gate control: must be DONE (or verified) for a GO.</p></section>")
    nv = [c for c in ctrls if c["status"] == "NOT VERIFIED"]
    w.append("<section id='gaps'><h2>Unverified controls and evidence gaps</h2><div class='tw'><table><thead><tr><th>Control</th><th>Gate</th>"
             "<th>Live access</th><th>Why</th></tr></thead><tbody>" +
             "".join(f"<tr><td><b>{esc(c['id'])}</b> {esc(c['title'])}</td><td>{'yes' if c['gate'] else 'no'}</td><td>{'yes' if c['runtime'] else 'no'}</td>"
                     f"<td class='small'>{esc(c['summary'])}</td></tr>" for c in nv) + "</tbody></table></div></section>")
    w.append("<section id='plan'><h2>Action plan</h2>")
    for p, title in PRIO_TITLE.items():
        fs = [f for f in fnds if f["priority"] == p]
        if fs:
            w.append(f"<h3>{esc(title)}</h3><ol>" + "".join(f"<li><b>{esc(f['id'])}</b> {esc(f['title'])}<div class='small muted'>"
                                                          f"{esc(f['remediation'])}</div></li>" for f in fs) + "</ol>")
    w.append("</section></main>")
    data = json.dumps({"verdict": d["verdict"], "completion": o["completion_pct"], "coverage": o["coverage_pct"]})
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc(a['title'])}</title><style>{CSS}</style></head><body data-summary='{esc(data)}'>{''.join(w)}<script>{JS}</script></body></html>\n")
