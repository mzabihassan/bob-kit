"""Findings model of the cloud migration audit: schemas, agent result checks, merge, metrics, decision, comparison.

Agents write results files (one per agent group, plus one for cross-repository correlation); the
main task writes a summary file. merge() turns them into the single source of truth
(cloud-migration-findings.json): every catalog control gets exactly one status, findings get
stable IDs (carried over from the previous audit when they match), metrics follow fixed formulas
and the GO / CONDITIONAL GO / NO-GO decision follows fixed rules. Deterministic: same inputs and
date give the same output. Standard library only.
"""
import hashlib
import os
import re
from collections import Counter, OrderedDict

from catalog import BY_ID, CONTROLS, DOMAINS, SEVERITIES, STATUSES

SCHEMA_VERSION = "1.0"
KINDS = ["confirmed", "potential"]
EFFORTS = ["S", "M", "L"]
PRIORITY = {"CRITICAL": "P0", "HIGH": "P1", "MEDIUM": "P2", "LOW": "P3", "INFO": "P3"}
CONSERVATIVE = {"NOT DONE": 0, "PARTIALLY DONE": 1, "NOT VERIFIED": 2, "DONE": 3, "NOT APPLICABLE": 4}
SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}
SECURITY_CONTROLS = {"K8S-12", "K8S-15", "K8S-16", "K8S-17", "CTR-01", "CTR-03", "CTR-04", "CTR-05", "CTR-06", "CTR-07",
                     "CTR-08", "CICD-03", "CICD-10", "CICD-12", "APP-09", "APP-16", "WEB-03", "WEB-04", "WEB-05", "WEB-06"}
RESILIENCE_CONTROLS = {c["id"] for c in CONTROLS if c["domain"] == "ARCH"} | {
    "APP-01", "APP-03", "APP-06", "APP-07", "APP-11", "APP-14", "K8S-03", "K8S-04", "K8S-05", "K8S-06", "K8S-07", "K8S-08",
    "K8S-09", "K8S-10", "K8S-19", "OPS-06", "OPS-07", "OPS-11"}

EVIDENCE = {"type": "object", "required": ["repo", "file", "note"], "properties": {
    "repo": {"type": "string", "minLength": 1}, "file": {"type": "string", "minLength": 1},
    "line": {"type": "integer"}, "note": {"type": "string", "minLength": 3}}}
RESULT_SCHEMA = {"type": "object", "required": ["group", "controls", "findings"], "properties": {
    "group": {"type": "string", "pattern": r"^[a-z][a-z0-9-]*$"},
    "controls": {"type": "array", "items": {"type": "object", "required": ["id", "status", "summary"], "properties": {
        "id": {"type": "string", "pattern": r"^[A-Z][A-Z0-9]*-\d{2}$"}, "status": {"enum": STATUSES},
        "summary": {"type": "string", "minLength": 5}, "evidence": {"type": "array", "items": EVIDENCE},
        "repos": {"type": "array", "items": {"type": "string"}}, "remediation": {"type": "string", "minLength": 10},
        "severity": {"enum": SEVERITIES}}}},
    "findings": {"type": "array", "items": {"type": "object", "required": [
        "key", "control", "title", "severity", "kind", "repos", "evidence", "impact", "remediation", "validation", "acceptance"],
        "properties": {
            "key": {"type": "string", "pattern": r"^[a-z0-9][a-z0-9-]{1,60}$"}, "control": {"type": "string", "pattern": r"^[A-Z][A-Z0-9]*-\d{2}$"},
            "title": {"type": "string", "minLength": 8}, "severity": {"enum": SEVERITIES}, "kind": {"enum": KINDS},
            "repos": {"type": "array", "items": {"type": "string"}}, "evidence": {"type": "array", "items": EVIDENCE},
            "impact": {"type": "string", "minLength": 10}, "remediation": {"type": "string", "minLength": 10},
            "example": {"type": "string"}, "validation": {"type": "string", "minLength": 5},
            "acceptance": {"type": "string", "minLength": 5}, "effort": {"enum": EFFORTS}, "blocker": {"type": "boolean"},
            "depends_on": {"type": "array", "items": {"type": "string"}}, "runtime_check": {"type": "string"},
            "related_controls": {"type": "array", "items": {"type": "string", "pattern": r"^[A-Z][A-Z0-9]*-\d{2}$"}}}}},
    "notes": {"type": "string"}}}
SUMMARY_SCHEMA = {"type": "object", "required": ["executive_summary", "architecture"], "properties": {
    "title": {"type": "string"}, "executive_summary": {"type": "string", "minLength": 20},
    "architecture": {"type": "string", "minLength": 20}, "migration_context": {"type": "string"},
    "components": {"type": "array", "items": {"type": "object", "required": ["name", "repo", "description"], "properties": {
        "name": {"type": "string"}, "repo": {"type": "string"}, "description": {"type": "string"}}}},
    "key_risks": {"type": "array", "items": {"type": "string"}}, "decision_rationale": {"type": "string"},
    "access": {"type": "string"}}}


def findings_schema():
    """JSON Schema (draft 2020-12) of cloud-migration-findings.json, for external consumers."""
    ev = {"type": "object", "required": ["repo", "file", "note"], "properties": {"repo": {"type": "string"}, "file": {"type": "string"},
                                                                               "line": {"type": "integer"}, "note": {"type": "string"}}}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Cloud migration audit findings",
        "type": "object", "required": ["schema_version", "audit", "repositories", "controls", "findings", "metrics", "decision"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "audit": {"type": "object", "required": ["date", "title", "catalog_controls", "agents"]},
            "repositories": {"type": "array", "items": {"type": "object", "required": ["label", "roles"]}},
            "architecture": {"type": "object"}, "summary": {"type": "object"},
            "controls": {"type": "array", "items": {
                "type": "object",
                "required": ["id", "domain", "title", "status", "summary", "evidence", "repos", "runtime", "gate", "assessed"],
                "properties": {"status": {"enum": STATUSES}, "evidence": {"type": "array", "items": ev}}}},
            "findings": {"type": "array", "items": {"type": "object", "required": [
                "id", "key", "control", "domain", "title", "severity", "priority", "kind", "blocker", "cross_repo", "repos", "evidence",
                "impact", "remediation", "validation", "acceptance"], "properties": {
                "id": {"type": "string", "pattern": r"^[A-Z][A-Z0-9]*-\d{2}-F\d+$"}, "severity": {"enum": SEVERITIES},
                "priority": {"enum": ["P0", "P1", "P2", "P3"]}, "kind": {"enum": KINDS}, "evidence": {"type": "array", "items": ev}}}},
            "metrics": {"type": "object"}, "decision": {"type": "object", "required": ["verdict", "conditions", "blockers"],
                                                        "properties": {"verdict": {"enum": ["GO", "CONDITIONAL GO", "NO-GO"]}}},
            "comparison": {"type": ["object", "null"]}, "conflicts": {"type": "array"}, "warnings": {"type": "array"}}}


def validate_schema(obj, schema, path="$"):
    """Minimal JSON Schema subset: type, required, properties, items, enum, const, pattern, minLength."""
    errs = []
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
    if t:
        allowed = t if isinstance(t, list) else [t]
        ok = any(isinstance(obj, types[x]) and not (x == "integer" and isinstance(obj, bool)) for x in allowed)
        if not ok:
            return [f"{path}: expected {t}, got {type(obj).__name__}"]
    if "enum" in schema and obj not in schema["enum"]:
        errs.append(f"{path}: {obj!r} not in {schema['enum']}")
    if "const" in schema and obj != schema["const"]:
        errs.append(f"{path}: expected {schema['const']!r}")
    if isinstance(obj, str):
        if len(obj.strip()) < schema.get("minLength", 0):
            errs.append(f"{path}: too short (min {schema['minLength']} characters)")
        if "pattern" in schema and not re.search(schema["pattern"], obj):
            errs.append(f"{path}: {obj!r} does not match {schema['pattern']}")
    if isinstance(obj, dict):
        for k in schema.get("required", []):
            if k not in obj:
                errs.append(f"{path}: missing '{k}'")
        for k, sub in schema.get("properties", {}).items():
            if k in obj:
                errs += validate_schema(obj[k], sub, f"{path}.{k}")
    if isinstance(obj, list) and "items" in schema:
        for i, item in enumerate(obj):
            errs += validate_schema(item, schema["items"], f"{path}[{i}]")
    return errs


def check_result(res, inventory=None):
    """Errors and warnings of one agent results file (schema + audit rules)."""
    errors = validate_schema(res, RESULT_SCHEMA)
    warnings = []
    if errors:
        return errors, warnings
    from discover import leaks  # sibling module
    for path, text in _strings(res):
        kinds = leaks(text, (inventory or {}).get("secret_hashes", []))
        if kinds:
            errors.append(f"{path}: contains {', '.join(kinds)}: write the key and its location instead, never the value")
    labels = {r["label"] for r in (inventory or {}).get("repos", [])} | {"runtime"}  # runtime: file = read-only command run
    paths = (inventory or {}).get("paths", {})
    status, uncovered = {}, []
    for i, c in enumerate(res["controls"]):
        where = f"controls[{i}] {c['id']}"
        if c["id"] not in BY_ID:
            errors.append(f"{where}: unknown control (see `audit.py controls`)")
            continue
        if c["id"] in status:
            errors.append(f"{where}: assessed twice in this file")
        status[c["id"]] = c["status"]
        if c["status"] == "DONE" and not c.get("evidence"):
            errors.append(f"{where}: DONE needs evidence (file and line that prove it)")
        if c["status"] in ("PARTIALLY DONE", "NOT DONE") and not c.get("remediation") and not any(
                f["control"] == c["id"] or c["id"] in f.get("related_controls", []) for f in res["findings"]):
            uncovered.append(c["id"])
        if c["status"] == "NOT DONE" and BY_ID[c["id"]]["runtime"] and not c.get("evidence"):
            errors.append(f"{where}: platform-side control: absence in the repositories does not prove it is missing. "
                          "Use NOT VERIFIED, or cite the evidence that shows the gap")
    if uncovered:
        errors.append(f"{len(uncovered)} PARTIALLY DONE/NOT DONE control(s) without remediation: {', '.join(uncovered)}. For each, "
                      "either add \"remediation\" (and optionally \"severity\") to its control entry, or list it in the "
                      "related_controls of the finding with the same root cause")
    keys = Counter(f["key"] for f in res["findings"])
    for i, f in enumerate(res["findings"]):
        where = f"findings[{i}] {f['key']}"
        if keys[f["key"]] > 1:
            errors.append(f"{where}: duplicate key")
        if f["control"] not in BY_ID:
            errors.append(f"{where}: unknown control {f['control']}")
        st = status.get(f["control"])
        for rc in f.get("related_controls", []):
            if rc not in BY_ID or rc == f["control"]:
                errors.append(f"{where}: related control {rc} is unknown or the finding's own control")
            elif status.get(rc) == "DONE" and SEV_RANK[f["severity"]] <= SEV_RANK["MEDIUM"]:
                errors.append(f"{where}: related control {rc} is DONE but this finding is {f['severity']}")
        if st == "DONE" and SEV_RANK[f["severity"]] <= SEV_RANK["MEDIUM"]:
            errors.append(f"{where}: control {f['control']} is DONE but this finding is {f['severity']}: use PARTIALLY DONE "
                          "or lower the severity to LOW/INFO if it is only an observation")
        if st == "NOT APPLICABLE":
            errors.append(f"{where}: control {f['control']} is NOT APPLICABLE but has a finding")
        if not f["evidence"] and f["kind"] == "confirmed":
            errors.append(f"{where}: a confirmed finding needs evidence")
        if not f["evidence"] and not f.get("runtime_check"):
            warnings.append(f"{where}: no evidence and no runtime_check: say what proves or would prove it")
    for item in [e for c in res["controls"] for e in c.get("evidence", [])] + [e for f in res["findings"] for e in f["evidence"]]:
        if labels and item["repo"] not in labels:
            errors.append(f"evidence repo '{item['repo']}' is not one of {sorted(labels)}")
        elif item["repo"] in paths and item["repo"] != "runtime":
            full = os.path.join(paths[item["repo"]], item["file"])
            if not os.path.exists(full):
                errors.append(f"evidence file {item['repo']}:{item['file']} does not exist")
            elif item.get("line"):
                try:
                    with open(full, encoding="utf-8", errors="replace") as fh:
                        n = sum(1 for _ in fh)
                    if item["line"] > n or item["line"] < 1:
                        errors.append(f"evidence {item['repo']}:{item['file']}:{item['line']} is beyond the end of the file ({n} lines)")
                except OSError:
                    pass
    return errors, warnings


def _strings(obj, path="$"):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")


STOP = set("a an the and or of to in on for with without by at from is are be not no as it its this that into per across "
           "every each all any via when than more less".split())


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower().replace("-", " ")) if len(w) > 2 and w not in STOP}


def _same_problem(a, b):
    """Findings of two agents describe the same problem: same control and a shared evidence file, or a shared evidence
    line (or file) and close titles (Jaccard of significant words)."""
    files = {(e["repo"], e["file"]) for e in a["evidence"]} & {(e["repo"], e["file"]) for e in b["evidence"]}
    if not files:
        return False
    if a["control"] == b["control"]:
        return True
    lines = {(e["repo"], e["file"], e.get("line")) for e in a["evidence"] if e.get("line")} & \
            {(e["repo"], e["file"], e.get("line")) for e in b["evidence"] if e.get("line")}
    wa, wb = _words(a["title"]), _words(b["title"])
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= (0.25 if lines else 0.34)


def first_sentence(text, limit=110):
    """First sentence (not cut at 'e.g.' or 'i.e.'), shortened at a word boundary."""
    s = re.split(r"(?<!e\.g)(?<!i\.e)(?<!etc)\.\s", text.strip(), maxsplit=1)[0].rstrip(".")
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"


def _evidence_key(e):
    return (e["repo"], e["file"], e.get("line") or 0, e["note"])


def _union_evidence(*lists):
    seen = OrderedDict()
    for lst in lists:
        for e in lst or []:
            seen.setdefault(_evidence_key(e)[:3], {k: e[k] for k in ("repo", "file", "line", "note") if k in e})
    return sorted(seen.values(), key=lambda e: (e["repo"], e["file"], e.get("line") or 0))


def merge(results, inventory, summary, previous=None, date=None, groups=None):
    conflicts, warnings = [], []
    # Controls: one status per catalog control, conservative when agents disagree.
    assessed = {}
    for res in results:
        for c in res["controls"]:
            assessed.setdefault(c["id"], []).append((res["group"], c))
    controls = []
    for cat in CONTROLS:
        items = assessed.get(cat["id"], [])
        if not items:
            controls.append(OrderedDict(
                id=cat["id"], domain=cat["domain"], title=cat["title"], done_criteria=cat["done"], applies=cat["applies"],
                status="NOT VERIFIED", summary="Not assessed in this audit run.", evidence=[], repos=[], runtime=cat["runtime"],
                gate=cat["gate"], default_severity=cat["severity"], assessed=False, sources=[]))
            continue
        statuses = sorted({c["status"] for _, c in items}, key=lambda s: CONSERVATIVE[s])
        chosen = statuses[0]
        if len(statuses) > 1:
            conflicts.append({"control": cat["id"], "assessments": {g: c["status"] for g, c in items}, "kept": chosen})
        main = next(c for _, c in items if c["status"] == chosen)
        repos = sorted({r for _, c in items for r in c.get("repos", [])} | {e["repo"] for _, c in items for e in c.get("evidence", [])})
        controls.append(OrderedDict(
            id=cat["id"], domain=cat["domain"], title=cat["title"], done_criteria=cat["done"], applies=cat["applies"],
            status=chosen, summary=main["summary"].strip(), evidence=_union_evidence(*[c.get("evidence") for _, c in items]),
            repos=repos, runtime=cat["runtime"], gate=cat["gate"], default_severity=cat["severity"], assessed=True,
            sources=sorted({g for g, _ in items})))
    by_ctrl = {c["id"]: c for c in controls}

    # Findings: dedupe by (control, key) and by (control, first evidence location); keep the highest severity.
    raw = []
    for res in results:
        covered = {f["control"] for f in res["findings"]} | {rc for f in res["findings"] for rc in f.get("related_controls", [])}
        for f in res["findings"]:
            raw.append(dict(f, group=res["group"]))
        for c in res["controls"]:
            if c["status"] in ("PARTIALLY DONE", "NOT DONE") and c.get("remediation") and c["id"] not in covered:
                cat = BY_ID[c["id"]]
                default = cat["severity"] if SEV_RANK[cat["severity"]] >= SEV_RANK["MEDIUM"] else "MEDIUM"
                raw.append({"key": c["id"].lower() + "-gap", "control": c["id"], "group": res["group"],
                            "title": f"{cat['title']} — {c['status'].lower()}: {first_sentence(c['remediation'])}",
                            "severity": c.get("severity") or default, "kind": "confirmed" if c.get("evidence") else "potential",
                            "repos": sorted(set(c.get("repos", [])) | {e["repo"] for e in c.get("evidence", [])}),
                            "evidence": c.get("evidence", []), "impact": c["summary"], "remediation": c["remediation"],
                            "validation": f"Check that the control is met: {cat['done']}", "acceptance": cat["done"]})
    merged = OrderedDict()
    loc_index = {}
    for f in sorted(raw, key=lambda f: (f["control"], f["key"], SEV_RANK[f["severity"]], f["group"])):
        first = (f["evidence"][0]["repo"], f["evidence"][0]["file"], f["evidence"][0].get("line")) if f["evidence"] else None
        k = (f["control"], f["key"])
        target = merged.get(k) or (loc_index.get((f["control"],) + first) if first and first[2] else None)
        if target:
            if SEV_RANK[f["severity"]] < SEV_RANK[target["severity"]]:
                target["severity"] = f["severity"]
            target["evidence"] = _union_evidence(target["evidence"], f["evidence"])
            target["repos"] = sorted(set(target["repos"]) | set(f["repos"]))
            target["blocker"] = target.get("blocker", False) or f.get("blocker", False)
            target["groups"] = sorted(set(target["groups"]) | {f["group"]})
            target["related_controls"] = sorted(set(target.get("related_controls", [])) | set(f.get("related_controls", [])))
            if f["kind"] == "confirmed":
                target["kind"] = "confirmed"
            continue
        g = dict(f)
        g["groups"] = [f["group"]]
        g["evidence"] = _union_evidence(f["evidence"])
        merged[k] = g
        if first and first[2]:
            loc_index[(f["control"],) + first] = g
    findings = list(merged.values())

    # Different agents, one root cause seen from two domains: same first evidence line, or a shared evidence file and close
    # titles. Keep the most severe as the finding; the other control becomes a related control.
    by_loc, kept, alias = {}, [], {}
    for f in sorted(findings, key=lambda f: (SEV_RANK[f["severity"]], not f.get("blocker"), f["control"], f["key"])):
        loc = (f["evidence"][0]["repo"], f["evidence"][0]["file"], f["evidence"][0].get("line")) if f["evidence"] else None
        t = by_loc.get(loc) if loc and loc[2] else None
        if not t:
            t = next((k for k in kept if not set(k["groups"]) & set(f["groups"]) and _same_problem(k, f)), None)
        if t and not set(t["groups"]) & set(f["groups"]):
            if f["control"] != t["control"]:
                t["related_controls"] = sorted((set(t.get("related_controls", [])) | {f["control"]} |
                                                set(f.get("related_controls", []))) - {t["control"]})
            t["evidence"] = _union_evidence(t["evidence"], f["evidence"])
            t["repos"] = sorted(set(t["repos"]) | set(f["repos"]))
            t["groups"] = sorted(set(t["groups"]) | set(f["groups"]))
            t["blocker"] = t.get("blocker", False) or f.get("blocker", False)
            alias[f["key"]] = t["key"]
            warnings.append(f"'{f['key']}' ({f['control']}, {'/'.join(f['groups'])}) merged into '{t['key']}' ({t['control']}): same problem")
            continue
        if loc and loc[2]:
            by_loc.setdefault(loc, f)
        kept.append(f)
    findings = kept

    # A control with an open MEDIUM+ finding cannot stay DONE.
    for f in findings:
        for rc in f.get("related_controls", []):
            r = by_ctrl.get(rc)
            if r and r["status"] == "DONE" and SEV_RANK[f["severity"]] <= SEV_RANK["MEDIUM"]:
                warnings.append(f"{rc} was DONE but the {f['severity']} finding '{f['key']}' relates to it: set to PARTIALLY DONE")
                r["status"] = "PARTIALLY DONE"
        c = by_ctrl[f["control"]]
        if c["status"] == "DONE" and SEV_RANK[f["severity"]] <= SEV_RANK["MEDIUM"]:
            warnings.append(f"{c['id']} was DONE but has the {f['severity']} finding '{f['key']}': set to PARTIALLY DONE")
            c["status"] = "PARTIALLY DONE"
        elif c["status"] in ("NOT VERIFIED", "NOT APPLICABLE") and f["kind"] == "confirmed":
            warnings.append(f"{c['id']} was {c['status']} but has the confirmed finding '{f['key']}': set to NOT DONE")
            c["status"] = "NOT DONE"
        c["repos"] = sorted(set(c["repos"]) | set(f["repos"]))

    # Stable IDs: reuse the previous ID of the same (control, key) or the same first evidence file, else the next number.
    prev = {f["id"]: f for f in (previous or {}).get("findings", [])}
    used, next_n = set(), Counter()
    for f in prev.values():
        n = int(f["id"].rsplit("-F", 1)[1])
        next_n[f["control"]] = max(next_n[f["control"]], n)
    for f in sorted(findings, key=lambda f: (f["control"], f["key"])):
        match = next((p for p in prev.values() if p["control"] == f["control"] and p["key"] == f["key"] and p["id"] not in used), None)
        if not match and f["evidence"]:
            match = next((p for p in prev.values() if p["control"] == f["control"] and p["id"] not in used and p.get("evidence")
                          and p["evidence"][0]["file"] == f["evidence"][0]["file"] and p["evidence"][0]["repo"] == f["evidence"][0]["repo"]), None)
        if match:
            f["id"] = match["id"]
        else:
            next_n[f["control"]] += 1
            f["id"] = f"{f['control']}-F{next_n[f['control']]}"
        used.add(f["id"])
    key_to_id = {f["key"]: f["id"] for f in findings}
    key_to_id.update({a: key_to_id[t] for a, t in alias.items() if t in key_to_id})
    out_findings = []
    for f in sorted(findings, key=lambda f: (SEV_RANK[f["severity"]], f["control"], f["id"])):
        deps = sorted({key_to_id.get(d, d) for d in f.get("depends_on", [])})
        unknown = [d for d in deps if d not in key_to_id.values() and d not in BY_ID]
        if unknown:
            warnings.append(f"{f['id']}: depends_on {unknown} matches no finding key/ID or control")
        blocker = bool(f.get("blocker")) or f["severity"] == "CRITICAL"
        out_findings.append(OrderedDict(
            id=f["id"], key=f["key"], control=f["control"], domain=BY_ID[f["control"]]["domain"], title=f["title"].strip(),
            severity=f["severity"], priority="P0" if blocker else PRIORITY[f["severity"]], kind=f["kind"], blocker=blocker,
            cross_repo=len(set(f["repos"]) | {e["repo"] for e in f["evidence"]}) > 1, repos=sorted(f["repos"]),
            evidence=f["evidence"], impact=f["impact"].strip(), remediation=f["remediation"].strip(),
            example=(f.get("example") or "").strip(), validation=f["validation"].strip(), acceptance=f["acceptance"].strip(),
            effort=f.get("effort"), depends_on=deps, runtime_check=(f.get("runtime_check") or "").strip(),
            related_controls=sorted(set(f.get("related_controls", [])) - {f["control"]}), sources=f["groups"]))

    m = metrics(controls, out_findings, inventory)
    decision = decide(controls, out_findings)
    doc = OrderedDict(
        schema_version=SCHEMA_VERSION,
        audit=OrderedDict(date=date, title=(summary or {}).get("title") or "Cloud migration audit",
                          scope="Java/Spring Boot + Angular application migrated from on-premise to the cloud",
                          method="Static analysis of the repositories; runtime controls need live access and stay NOT VERIFIED without it.",
                          access=(summary or {}).get("access", "Repositories only (no cluster, cloud account, JFrog or Argo CD access)."),
                          catalog_controls=len(CONTROLS), agents=sorted(groups or {r["group"] for r in results}),
                          tool="bob-kit cloud-migration-audit-java-angular"),
        repositories=[OrderedDict((k, r[k]) for k in ("label", "roles", "head", "branch", "dirty", "provider", "files")) for r in inventory["repos"]],
        architecture=OrderedDict(summary=(summary or {}).get("architecture", ""), migration_context=(summary or {}).get("migration_context", ""),
                                 components=(summary or {}).get("components", []),
                                 stack={k: [f"{a} {b}".replace(" dependency", "") for a, b, _ in v] for k, v in inventory.get("stack", {}).items()}),
        summary=OrderedDict(executive_summary=(summary or {}).get("executive_summary", ""), key_risks=(summary or {}).get("key_risks", []),
                            decision_rationale=(summary or {}).get("decision_rationale", ""),
                            notes={r["group"]: r.get("notes", "") for r in results if r.get("notes")}),
        controls=controls, findings=out_findings, metrics=m, decision=decision,
        comparison=compare(previous, controls, out_findings, m, decision) if previous else None,
        conflicts=conflicts, warnings=warnings)
    return doc


def _pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


def _status_block(items):
    cnt = Counter(c["status"] for c in items)
    applicable = len(items) - cnt["NOT APPLICABLE"]
    assessed = cnt["DONE"] + cnt["PARTIALLY DONE"] + cnt["NOT DONE"]
    return OrderedDict(total=len(items), applicable=applicable, done=cnt["DONE"], partially_done=cnt["PARTIALLY DONE"],
                       not_done=cnt["NOT DONE"], not_verified=cnt["NOT VERIFIED"], not_applicable=cnt["NOT APPLICABLE"],
                       completion_pct=_pct(cnt["DONE"], applicable), coverage_pct=_pct(assessed, applicable),
                       completion_upper_bound_pct=_pct(cnt["DONE"] + cnt["NOT VERIFIED"], applicable))


def metrics(controls, findings, inventory):
    sev = Counter(f["severity"] for f in findings)
    by_repo = OrderedDict()
    for r in inventory["repos"]:
        label = r["label"]
        rc = [c for c in controls if label in c["repos"]]
        rf = [f for f in findings if label in f["repos"] or any(e["repo"] == label for e in f["evidence"])]
        block = _status_block(rc)
        block["findings"] = OrderedDict((s, sum(1 for f in rf if f["severity"] == s)) for s in SEVERITIES)
        by_repo[label] = block
    by_domain = OrderedDict()
    for d in DOMAINS:
        block = _status_block([c for c in controls if c["domain"] == d])
        block["findings"] = OrderedDict((s, sum(1 for f in findings if f["domain"] == d and f["severity"] == s)) for s in SEVERITIES)
        by_domain[d] = block
    return OrderedDict(
        formulas=OrderedDict(
            completion="DONE / applicable controls x 100 (applicable = all controls except NOT APPLICABLE)",
            coverage="(DONE + PARTIALLY DONE + NOT DONE) / applicable controls x 100: share of controls whose state is established by evidence",
            completion_upper_bound="(DONE + NOT VERIFIED) / applicable controls x 100: best case if every unverified control turned out done",
            note="NOT VERIFIED is never counted as done; a high completion with a low coverage is not a readiness signal."),
        overall=_status_block(controls), by_domain=by_domain, by_repo=by_repo,
        findings=OrderedDict(total=len(findings), by_severity=OrderedDict((s, sev[s]) for s in SEVERITIES),
                             by_priority=OrderedDict((p, sum(1 for f in findings if f["priority"] == p)) for p in ("P0", "P1", "P2", "P3")),
                             confirmed=sum(1 for f in findings if f["kind"] == "confirmed"),
                             potential=sum(1 for f in findings if f["kind"] == "potential"),
                             cross_repo=sum(1 for f in findings if f["cross_repo"])),
        blockers=[f["id"] for f in findings if f["blocker"]],
        unassessed_controls=[c["id"] for c in controls if not c["assessed"]])


def decide(controls, findings):
    rules = [
        "NO-GO: any production blocker (a CRITICAL finding, or a finding marked as blocker).",
        "CONDITIONAL GO: no blocker, but HIGH findings, or gate controls that are not DONE (including NOT VERIFIED); "
        "each one becomes a condition to clear before or right after go-live, as agreed.",
        "GO: no blocker, no HIGH finding and every gate control DONE.",
    ]
    blockers = [f["id"] for f in findings if f["blocker"]]
    highs = [f for f in findings if f["severity"] == "HIGH" and not f["blocker"]]
    gates = [c for c in controls if c["gate"] and c["status"] not in ("DONE", "NOT APPLICABLE")]
    conditions = [f"Fix {f['id']}: {f['title']}" for f in highs]
    for c in gates:
        if c["status"] == "NOT VERIFIED":
            conditions.append(f"Verify {c['id']} ({c['title']})" + (": needs live access" if c["runtime"] else ""))
        elif not any(f["control"] == c["id"] or c["id"] in f.get("related_controls", []) for f in findings
                     if f["blocker"] or f["severity"] == "HIGH"):
            conditions.append(f"Complete {c['id']} ({c['title']}): {c['status']}")
    verdict = "NO-GO" if blockers else "CONDITIONAL GO" if conditions else "GO"
    return OrderedDict(verdict=verdict, rules=rules, blockers=blockers, conditions=conditions,
                       gate_controls_open=[c["id"] for c in gates])


def compare(prev, controls, findings, m, decision):
    prev_f = {f["id"]: f for f in prev.get("findings", [])}
    cur_f = {f["id"]: f for f in findings}
    prev_c = {c["id"]: c for c in prev.get("controls", [])}
    cur_c = {c["id"]: c for c in controls}
    resolved, unconfirmed = [], []
    for fid, f in sorted(prev_f.items()):
        if fid in cur_f:
            continue
        status = cur_c.get(f["control"], {}).get("status")
        item = OrderedDict(id=fid, control=f["control"], title=f["title"], control_status_now=status)
        (resolved if status in ("DONE", "NOT APPLICABLE") else unconfirmed).append(item)
    changes = [OrderedDict(control=cid, previous=prev_c[cid]["status"], current=c["status"],
                           direction=("improved" if CONSERVATIVE[c["status"]] > CONSERVATIVE[prev_c[cid]["status"]] else "regressed"))
               for cid, c in cur_c.items() if cid in prev_c and prev_c[cid]["status"] != c["status"]]
    po, co = prev.get("metrics", {}).get("overall", {}), m["overall"]
    return OrderedDict(
        previous_date=prev.get("audit", {}).get("date"), previous_verdict=prev.get("decision", {}).get("verdict"),
        current_verdict=decision["verdict"],
        completion=OrderedDict(previous=po.get("completion_pct"), current=co["completion_pct"],
                               delta=round(co["completion_pct"] - (po.get("completion_pct") or 0), 1)),
        coverage=OrderedDict(previous=po.get("coverage_pct"), current=co["coverage_pct"],
                             delta=round(co["coverage_pct"] - (po.get("coverage_pct") or 0), 1)),
        new=sorted(fid for fid in cur_f if fid not in prev_f), persisting=sorted(fid for fid in cur_f if fid in prev_f),
        resolved=resolved, unconfirmed=unconfirmed, control_changes=changes,
        rule="A previous finding counts as resolved only if its control is now DONE or NOT APPLICABLE; otherwise it is listed as "
             "'no longer reported' to confirm (a removed file does not prove a fix).")


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()[:10]
