#!/usr/bin/env python3
"""Cloud migration audit engine (Java/Spring Boot + Angular on Kubernetes): discovery, agent briefs, checks, reports.

Commands (all read-only on the audited repositories; everything is written under --out):
  discover --repo LABEL=PATH ... --out DIR   map the repositories, print the inventory (leads, not verdicts)
  briefs   --out DIR [--agents auto|6|3]     write one self-contained brief per audit agent (auto: 3 or 6 by size)
  controls [--domain ARCH,APP]               print the control catalog
  check    FILE... [--out DIR]               validate agent results files (schema and audit rules)
  build    --out DIR [--date YYYY-MM-DD] [--previous FILE] [--no-compare]
                                             merge results, write the five reports, validate them
  validate --out DIR                         re-validate the generated reports
  schema                                     print the JSON Schema of cloud-migration-findings.json

Example:
  python3 audit.py discover --repo air-back=../air-back --repo air-ui=../air-ui --repo air-cd=../air-cd --out cloud-migration-audit
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import catalog  # noqa: E402
import discover  # noqa: E402
import findings as fmodel  # noqa: E402
import render  # noqa: E402

ARTIFACTS = {"json": "cloud-migration-findings.json", "md": "cloud-migration-audit.md", "html": "cloud-migration-audit.html",
             "plan": "cloud-migration-action-plan.md", "checklist": "cloud-migration-checklist.md"}
ROLES = {"backend": "Java/Spring Boot and distributed-architecture", "kubernetes": "Kubernetes and cloud infrastructure",
         "containers": "Docker and DevSecOps", "delivery": "GitLab CI/CD, JFrog and Argo CD",
         "frontend": "Angular and end-to-end integration", "operations": "observability and production resilience",
         "platform": "Kubernetes, container security and delivery (GitLab CI/CD, JFrog, Argo CD)",
         "frontend-ops": "Angular end-to-end integration, observability and production resilience"}


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def workdir(out):
    w = os.path.join(out, "work")
    os.makedirs(w, exist_ok=True)
    return w


def cmd_discover(a):
    inv = discover.run(a.repo)
    w = workdir(a.out)
    dump(inv, os.path.join(w, "inventory.json"))
    with open(os.path.join(w, "inventory.md"), "w", encoding="utf-8") as fh:
        fh.write(discover.render_inventory(inv))
    sys.stdout.write(discover.render_inventory(inv, full=False))
    n = recommended_agents(inv)
    sys.stdout.write(f"\nWritten: {os.path.join(w, 'inventory.json')} and inventory.md. Next: audit.py briefs --out {a.out} "
                     f"(writes {n} agent briefs, the number recommended for this size)\n")
    return 0


def control_lines(domains):  # used by `controls`
    out = []
    for c in catalog.CONTROLS:
        if c["domain"] in domains:
            flags = ", ".join(x for x, on in (("gate", c["gate"]), ("needs live access to fully verify", c["runtime"])) if on)
            out.append(f"- **{c['id']}** {c['title']} — DONE when: {c['done']} Applies: {c['applies']}. "
                       f"Default severity if missing: {c['severity']}" + (f" ({flags})" if flags else "") + ".")
    return out


def cmd_controls(a):
    doms = [d.strip() for d in (a.domain or ",".join(catalog.DOMAINS)).split(",")]
    for d in doms:
        if d not in catalog.DOMAINS:
            sys.exit(f"unknown domain {d}; domains: {', '.join(catalog.DOMAINS)}")
        print(f"## {d} — {catalog.DOMAINS[d]}")
        print("\n".join(control_lines([d])))
    return 0


BRIEF = """# Cloud migration audit — brief for the {role} agent

You audit a Java/Spring Boot + Angular application migrated from on-premise servers to containers on Kubernetes (IBM Cloud),
built by GitLab CI, stored in JFrog and deployed by Argo CD/Helm. Your domains: {domains}. Act as a senior specialist: find
what was harmless on one on-premise server and breaks with several pods, restarts, rolling updates and cloud networking.

## Rules
- This brief is complete: do not activate skills and do not read other instruction files.
- Read-only. Never modify, build, start, deploy or run scripts from the repositories; never call clusters, JFrog or Argo CD.
- Evidence only: statuses and findings cite `repo` + repository-relative `file` + `line`. No evidence means NOT VERIFIED, never
  DONE. Configuration proves configuration, not runtime behaviour (`kind: potential` + `runtime_check` when it depends on it).
- Absence proves absence only for what must live in these repositories (code, manifests, Dockerfiles, pipelines). For
  platform-side controls (marked "platform") — backups, alert routing, dashboards, log shipping, DR, JFrog/Argo CD settings —
  nothing in Git means NOT VERIFIED, unless a file shows the gap (e.g. logs written to a file, `emptyDir` for data).
- Every PARTIALLY DONE/NOT DONE control needs a remediation. For a simple gap, put `remediation` (an action, e.g. "Add a
  PodDisruptionBudget …") on the control entry itself, with `severity` if it is not MEDIUM. Write a full finding only for significant problems (HIGH/CRITICAL, cross-
  repository, or needing a failure scenario and an example), one finding per root cause: list the other controls it breaks
  in `related_controls`. No finding for NOT VERIFIED controls: their summary says what evidence or access is missing.
- Never copy secret values, not even development ones: name the key and its location (the check rejects values).
- Cost: every turn re-sends your whole context. Pick the files to read from the leads below and read them in as few turns as
  possible (several reads in one response, line ranges for long files). Do not re-read a file, do not search the
  inventory unless a lead is missing, do not keep a todo list.

## Inputs
{repos}
- Full discovery inventory, only if a lead below is missing: `{inventory}`.

## Controls to assess (every one; one entry each). "gate": must be DONE for a GO; "platform": needs live access to fully verify
{controls}

## How to judge (your domains)
{guide}

## Leads from discovery (regex matches and mechanical comparisons: verify before using)
{signals}
{checks}

## Statuses and severities
- DONE: implemented and proven by evidence. PARTIALLY DONE: implemented but incomplete or risky. NOT DONE: required and
  missing. Both need a finding (own or via `related_controls`). NOT VERIFIED: cannot be proven either way here.
  NOT APPLICABLE: irrelevant to this architecture (say why).
- Severity is the risk, independent of the status: CRITICAL (data loss/corruption, security breach or outage likely in
  production: blocker), HIGH (likely production incident or serious exposure), MEDIUM (degraded behaviour or risk under
  specific conditions), LOW (hardening), INFO (observation).
- Calibrate: CRITICAL only when production data, money or security is directly at stake with no other safeguard (a usable
  secret in Git, a query that fails on a main flow, duplicated payments). Missing hardening (.dockerignore, headers, network
  policies, PDB) is MEDIUM or LOW. A risk you could not prove (`potential`) is at most HIGH. `blocker: true` is exceptional: a
  HIGH issue that alone makes production unacceptable; other HIGH findings become conditions of a CONDITIONAL GO.

## Output
Write `{result}` in ONE write (UTF-8 JSON only):
```json
{{"group": "{group}",
 "controls": [{{"id": "ARCH-01", "status": "PARTIALLY DONE", "summary": "1 of 2 scheduled jobs holds a ShedLock lock.",
   "repos": ["air-back", "air-cd"],
   "evidence": [{{"repo": "air-back", "file": "src/main/java/com/acme/ReportJob.java", "line": 21, "note": "@SchedulerLock(name=\\"report\\")"}}]}},
  {{"id": "K8S-10", "status": "NOT DONE", "summary": "No PodDisruptionBudget for air-back (3 replicas in prod).",
   "evidence": [{{"repo": "air-cd", "file": "helm/air-back/values-prod.yaml", "line": 1, "note": "replicaCount: 3, no PDB template"}}],
   "remediation": "Add a PodDisruptionBudget template with minAvailable: 1 to the air-back chart.", "severity": "MEDIUM"}}],
 "findings": [{{"key": "invoicereminderjob-unlocked", "control": "ARCH-01", "related_controls": [], "severity": "HIGH",
   "kind": "confirmed", "blocker": false, "title": "InvoiceReminderJob runs on every replica and sends duplicate reminders",
   "repos": ["air-back", "air-cd"],
   "evidence": [{{"repo": "air-back", "file": "src/main/java/com/acme/InvoiceReminderJob.java", "line": 18, "note": "@Scheduled without lock"}},
                {{"repo": "air-cd", "file": "helm/air-back/values-prod.yaml", "line": 3, "note": "replicaCount: 3"}}],
   "impact": "With 3 replicas the job runs 3 times per period: each customer receives 3 reminders.",
   "remediation": "Add @SchedulerLock with lockAtMostFor longer than the job.",
   "example": "@SchedulerLock(name = \\"invoiceReminder\\", lockAtMostFor = \\"PT5M\\")",
   "validation": "Run 3 replicas in staging and count executions per period.",
   "acceptance": "Exactly one execution per period across replicas.", "effort": "S", "depends_on": [], "runtime_check": ""}}],
 "notes": "Two sentences on the architecture seen in your domains."}}
```
- `key`: lowercase kebab-case from the main component plus the problem; stable across audits. `effort`: S, M or L.
- Keep it tight: `impact` = the production failure scenario in 1–2 sentences; `remediation` 1–3 sentences specific to this
  code base; `example` at most 8 lines; one evidence item per distinct location.
- DONE controls with evidence matter: they show what is already migrated.
- Run `python3 {audit} check {result} --out {out}`. If it reports errors, fix all of them and rewrite the whole file in ONE
  write, then check once more (no piecemeal edits: each edit re-sends the file).

Your final answer is one line: `{group}: <n> controls assessed, <m> findings, written to {result}`.
"""


def guide_sections(path, doms):
    """Intro, the sections of the given domains and the severity hints of a guide file."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    parts = re.split(r"(?m)^## ", text)
    keep = [re.sub(r"^# .*\n+", "", parts[0]).strip()]
    for p in parts[1:]:
        head = p.split("\n", 1)[0]
        if any(head.startswith(d + " ") or head.startswith(d + "\u00a0") for d in doms) or head.startswith("Severity"):
            keep.append("### " + p.strip())
    return "\n\n".join(k for k in keep if k)


def recommended_agents(inv):
    code = sum(r.get("java_files", 0) + r.get("ts_files", 0) for r in inv["repos"])
    manifests = sum(r.get("yaml_files", 0) for r in inv["repos"])
    return "6" if code > 150 or manifests > 40 else "3"


def cmd_briefs(a):
    w = workdir(a.out)
    inv_path = os.path.join(w, "inventory.json")
    if not os.path.exists(inv_path):
        sys.exit("run `audit.py discover` first")
    inv = load(inv_path)
    out_abs = os.path.abspath(a.out)
    agents = recommended_agents(inv) if a.agents == "auto" else a.agents
    groups = catalog.GROUPS[agents]
    repos = "\n".join(f"- `{r['label']}` ({', '.join(r['roles'])}): `{inv['paths'][r['label']]}`" for r in inv["repos"])
    written = []
    for group, doms in groups.items():
        guides = []
        for g in sorted({catalog.GUIDES[d] for d in doms}):
            guides.append(guide_sections(os.path.join(os.path.dirname(HERE), g), [d for d in doms if catalog.GUIDES[d] == g]))
        checks = [c for c in inv["checks"] if any(cid.split("-")[0] in doms for cid in c["controls"])]
        chk = ["", "Cross-repository facts:"] if checks else []
        for c in checks:
            chk.append(f"- {c['id']} {c['title']}" + (f" — hint: {c['hint']}" if c["hint"] else ""))
            chk += [f"  - {f}" for f in c["facts"][:8]]
        controls = [f"- {c['id']} {c['title']}" + "".join(f" [{x}]" for x, on in (("gate", c["gate"]), ("platform", c["runtime"])) if on)
                    + f" — default severity {c['severity']}" + ("" if c["applies"] == "always" else f"; applies if {c['applies']}")
                    for c in catalog.CONTROLS if c["domain"] in doms]
        result = os.path.join(out_abs, "work", f"results-{group}.json")
        text = BRIEF.format(role=ROLES.get(group, group), domains=", ".join(f"{d} ({catalog.DOMAINS[d]})" for d in doms),
                            repos=repos, inventory=os.path.abspath(inv_path), controls="\n".join(controls), guide="\n\n".join(guides),
                            signals="\n".join(discover.signal_lines(inv, doms, per_signal=8)), checks="\n".join(chk), result=result,
                            group=group, audit=os.path.join(HERE, "audit.py"), out=out_abs)
        path = os.path.join(w, f"brief-{group}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        written.append((group, path))
    print(f"{len(written)} agent briefs written ({'recommended for the repository size' if a.agents == 'auto' else 'as requested'}). "
          "Spawn one subagent per brief, all in the same turn, with this message:")
    for group, path in written:
        print(f"- {group}: \"Read {path} and follow it exactly.\"")
    print(f"Each agent writes {os.path.join(out_abs, 'work', 'results-<group>.json')}. Meanwhile, do the correlation (correlation.md), "
          f"then write results-correlation.json and summary.json and run: audit.py build --out {a.out}")
    return 0


def check_files(files, out):
    inv = None
    if out and os.path.exists(os.path.join(out, "work", "inventory.json")):
        inv = load(os.path.join(out, "work", "inventory.json"))
    ok, results = True, []
    for path in files:
        try:
            res = load(path)
        except (OSError, ValueError) as exc:
            print(f"ERROR {path}: cannot read JSON: {exc}")
            ok = False
            continue
        errors, warnings = fmodel.check_result(res, inv)
        for e in errors:
            print(f"ERROR {os.path.basename(path)}: {e}")
        for x in warnings:
            print(f"WARN  {os.path.basename(path)}: {x}")
        if errors:
            ok = False
        else:
            results.append(res)
            print(f"OK    {os.path.basename(path)}: {len(res['controls'])} controls, {len(res['findings'])} findings")
    return ok, results


def cmd_check(a):
    ok, _ = check_files(a.files, a.out)
    return 0 if ok else 1


def run_id(inv, date):
    heads = "|".join(f"{r['label']}={r.get('head')}" for r in inv["repos"])
    return hashlib.sha256(f"{date}|{heads}".encode()).hexdigest()[:12]


def cmd_build(a):
    out = a.out
    w = workdir(out)
    inv = load(os.path.join(w, "inventory.json"))
    files = sorted(glob.glob(os.path.join(w, "results-*.json")))
    if not files:
        sys.exit(f"no results-*.json in {w}: the agents write them (see the briefs)")
    ok, results = check_files(files, out)
    if not ok:
        print("FAILED: fix the results files above, then run build again")
        return 1
    summary_path = os.path.join(w, "summary.json")
    draft = not os.path.exists(summary_path)
    summary = {} if draft else load(summary_path)
    errs = [] if draft else fmodel.validate_schema(summary, fmodel.SUMMARY_SCHEMA)
    if errs:
        print("\n".join(f"ERROR summary.json: {e}" for e in errs))
        return 1
    date = a.date or datetime.date.today().isoformat()
    rid = run_id(inv, date)
    existing = os.path.join(out, ARTIFACTS["json"])
    previous, base = None, None
    if a.previous:
        previous, base = load(a.previous), a.previous
    elif os.path.exists(existing) and not a.no_compare:
        old = load(existing)
        if old.get("audit", {}).get("run_id") != rid:
            hist = os.path.join(out, "history")
            os.makedirs(hist, exist_ok=True)
            base = os.path.join(hist, f"cloud-migration-findings-{old['audit'].get('date')}-{old['audit'].get('run_id')}.json")
            shutil.copyfile(existing, base)
            previous = old
        elif old.get("audit", {}).get("compared_with") and os.path.exists(os.path.join(out, old["audit"]["compared_with"])):
            base = os.path.join(out, old["audit"]["compared_with"])
            previous = load(base)
    groups = sorted({r["group"] for r in results})
    doc = fmodel.merge(results, inv, summary, previous, date, groups)
    doc["audit"]["run_id"] = rid
    doc["audit"]["compared_with"] = os.path.relpath(base, out) if base and os.path.abspath(base).startswith(os.path.abspath(out)) else base
    dump(doc, existing)
    for key, fn in (("md", render.md_report), ("plan", render.action_plan), ("checklist", render.checklist), ("html", render.html_report)):
        with open(os.path.join(out, ARTIFACTS[key]), "w", encoding="utf-8") as fh:
            fh.write(fn(doc))
    errors, warnings = validate(out, inv)
    if draft:
        warnings.insert(0, "DRAFT: no summary.json yet; review the leads below, write summary.json (correlation.md) and build again")
    m, d = doc["metrics"]["overall"], doc["decision"]
    print(f"Decision: {d['verdict']} · completion {m['completion_pct']}% ({m['done']}/{m['applicable']}) · coverage {m['coverage_pct']}% · "
          f"upper bound {m['completion_upper_bound_pct']}%")
    print("Controls: " + ", ".join(f"{k} {v}" for k, v in m.items() if k in ("done", "partially_done", "not_done", "not_verified", "not_applicable")))
    print("Findings: " + ", ".join(f"{k} {v}" for k, v in doc["metrics"]["findings"]["by_severity"].items()) +
          f" · blockers: {', '.join(d['blockers']) or 'none'}")
    for f in doc["findings"][:5]:
        print(f"  {f['id']} [{f['severity']}] {f['title']}")
    if doc.get("comparison"):
        c = doc["comparison"]
        print(f"Since {c['previous_date']}: completion {c['completion']['delta']:+}, coverage {c['coverage']['delta']:+}, new {len(c['new'])}, "
              f"resolved {len(c['resolved'])}, to confirm {len(c['unconfirmed'])}")
    st = {c["id"]: c["status"] for c in doc["controls"]}
    with_finding = {f["control"] for f in doc["findings"]} | {rc for f in doc["findings"] for rc in f.get("related_controls", [])}
    leads = [c for c in inv["checks"] if c["hint"] and not any(cid in with_finding for cid in c["controls"])
             and not all(st.get(cid) == "DONE" for cid in c["controls"])]
    for c in leads:
        print(f"LEAD  {c['id']} ({', '.join(c['controls'])}) has no finding yet: {c['hint']}")
    for x in doc["warnings"] + warnings:
        print(f"WARN  {x}")
    for c in doc["conflicts"]:
        print(f"WARN  conflicting statuses for {c['control']}: {c['assessments']} → kept {c['kept']}")
    for e in errors:
        print(f"ERROR {e}")
    print(("FAILED" if errors else "OK") + f": reports in {os.path.abspath(out)}: " + ", ".join(ARTIFACTS.values()))
    return 1 if errors else 0


def validate(out, inv=None):
    """Consistency of the generated reports with the findings file, and safety checks."""
    errors, warnings = [], []
    path = os.path.join(out, ARTIFACTS["json"])
    if not os.path.exists(path):
        return [f"missing {path}"], []
    doc = load(path)
    errors += [f"findings JSON: {e}" for e in fmodel.validate_schema(doc, fmodel.findings_schema())]
    if errors:
        return errors, warnings
    ids = [f["id"] for f in doc["findings"]]
    if len(ids) != len(set(ids)):
        errors.append("duplicate finding IDs")
    if [c["id"] for c in doc["controls"]] != [c["id"] for c in catalog.CONTROLS]:
        errors.append("controls do not match the catalog (one entry per control, catalog order)")
    for c in doc["controls"]:
        if c["status"] == "DONE" and not c["evidence"]:
            errors.append(f"{c['id']} is DONE without evidence")
    by_ctrl = {c["id"]: c for c in doc["controls"]}
    for f in doc["findings"]:
        c = by_ctrl.get(f["control"])
        if not c:
            errors.append(f"{f['id']}: unknown control")
        elif c["status"] == "DONE" and fmodel.SEV_RANK[f["severity"]] <= fmodel.SEV_RANK["MEDIUM"]:
            errors.append(f"{f['id']}: {f['severity']} finding under a DONE control")
    recomputed = fmodel.metrics(doc["controls"], doc["findings"], inv or {"repos": [{"label": r["label"]} for r in doc["repositories"]]})
    if recomputed["overall"] != doc["metrics"]["overall"] or recomputed["findings"] != doc["metrics"]["findings"]:
        errors.append("metrics do not match the controls and findings (file edited by hand?)")
    if fmodel.decide(doc["controls"], doc["findings"])["verdict"] != doc["decision"]["verdict"]:
        errors.append("decision does not follow the decision rules")
    texts = {}
    for key, name in ARTIFACTS.items():
        p = os.path.join(out, name)
        if not os.path.exists(p):
            errors.append(f"missing {name}")
            continue
        with open(p, encoding="utf-8") as fh:
            texts[key] = fh.read()
    for key in ("md", "plan", "html"):
        missing = [i for i in ids if i not in texts.get(key, "")]
        if missing:
            errors.append(f"{ARTIFACTS[key]} does not mention {', '.join(missing[:5])}")
    missing_c = [c["id"] for c in doc["controls"] if c["id"] not in texts.get("checklist", "")]
    if missing_c:
        errors.append(f"{ARTIFACTS['checklist']} does not list {', '.join(missing_c[:5])}")
    for key, text in texts.items():
        kinds = discover.leaks(text, (inv or {}).get("secret_hashes", []))
        if kinds:
            errors.append(f"{ARTIFACTS[key]} contains {', '.join(kinds)}: remove it from the results or summary file and build again")
    if inv and inv.get("paths"):
        for e in [e for c in doc["controls"] for e in c["evidence"]] + [e for f in doc["findings"] for e in f["evidence"]]:
            root = inv["paths"].get(e["repo"])
            if root and not os.path.exists(os.path.join(root, e["file"])):
                warnings.append(f"evidence file not found: {e['repo']}:{e['file']}")
    if "<script>" in texts.get("html", "") and texts["html"].count("<script>") != 1:
        warnings.append("unexpected script blocks in the HTML report")
    return errors, warnings


def cmd_validate(a):
    inv_path = os.path.join(a.out, "work", "inventory.json")
    errors, warnings = validate(a.out, load(inv_path) if os.path.exists(inv_path) else None)
    for x in warnings:
        print(f"WARN  {x}")
    for e in errors:
        print(f"ERROR {e}")
    print("FAILED" if errors else "OK")
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("discover")
    p.add_argument("--repo", action="append", required=True, help="LABEL=PATH (repeat for each repository)")
    p.add_argument("--out", required=True)
    p = sub.add_parser("briefs")
    p.add_argument("--out", required=True)
    p.add_argument("--agents", choices=["auto", "6", "3"], default="auto")
    p = sub.add_parser("controls")
    p.add_argument("--domain")
    p = sub.add_parser("check")
    p.add_argument("files", nargs="+")
    p.add_argument("--out")
    p = sub.add_parser("build")
    p.add_argument("--out", required=True)
    p.add_argument("--date", help="audit date (default: today); fix it to reproduce a report")
    p.add_argument("--previous", help="findings JSON of an earlier audit to compare with")
    p.add_argument("--no-compare", action="store_true")
    p = sub.add_parser("validate")
    p.add_argument("--out", required=True)
    sub.add_parser("schema")
    a = ap.parse_args()
    if a.cmd == "schema":
        print(json.dumps(fmodel.findings_schema(), indent=2))
        return 0
    return {"discover": cmd_discover, "briefs": cmd_briefs, "controls": cmd_controls, "check": cmd_check, "build": cmd_build,
            "validate": cmd_validate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
