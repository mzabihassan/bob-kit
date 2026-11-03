#!/usr/bin/env python3
"""Scan every skill with NVIDIA SkillSpector (static mode) and fail on any finding not justified in a baseline.

Each skill is scanned on its own, with tools/skillspector/<skill>.yaml as baseline when it exists (SkillSpector
does not accept a baseline in a recursive scan). A baseline lists suppression rules (rule id + file + matched
text) with the reason each match is a false positive; anything else makes the scan fail.

Requires SkillSpector (Python >= 3.12), pinned like the CI job:
  pip install "skillspector @ git+https://github.com/NVIDIA/SkillSpector@091a509b3d6ba8ff5be528966e1f43c2e68cf214"

Run from the repository root:  python3 tools/scan_skills.py [--out <report-dir>] [--skillspector <path>]
Exit status: 0 no unjustified finding, 1 unjustified findings or failed scans, 2 SkillSpector not found.
"""
import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
BASELINES = os.path.join(ROOT, "tools", "skillspector")


def scan(exe, skill, out_dir):
    report = os.path.join(out_dir, f"{skill}.json")
    cmd = [exe, "scan", os.path.join(SKILLS, skill), "--no-llm", "--format", "json", "--output", report]
    baseline = os.path.join(BASELINES, f"{skill}.yaml")
    if os.path.isfile(baseline):
        cmd += ["--baseline", baseline, "--show-suppressed"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    # Exit 1 only means a risk score above the threshold: the findings themselves are checked below.
    if r.returncode not in (0, 1) or not os.path.isfile(report):
        return skill, None, (r.stderr or r.stdout).strip()[-500:]
    with open(report, encoding="utf-8") as fh:
        return skill, json.load(fh), ""


def unused_rules(skill, suppressed):
    """Baseline rules that no longer match anything: remove them so the baseline never hides more than needed."""
    path = os.path.join(BASELINES, f"{skill}.yaml")
    try:
        import yaml  # installed with SkillSpector
    except ImportError:
        return []
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        rules = (yaml.safe_load(fh) or {}).get("rules") or []

    def glob(value, pattern):
        return fnmatch.fnmatch((value or "").lower(), pattern.replace("**", "*").lower())

    def matches(rule, f):
        if rule.get("id") and not glob(f.get("id"), rule["id"]):
            return False
        if rule.get("path") and not glob((f.get("location") or {}).get("file"), rule["path"]):
            return False
        texts = (f.get("message"), f.get("finding"), f.get("matched_text"))
        return not rule.get("message") or any(glob(t, rule["message"]) for t in texts)

    return [r for r in rules if not any(matches(r, f) for f in suppressed)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", help="keep the JSON report of each skill in this folder")
    ap.add_argument("--skillspector", default=shutil.which("skillspector"), help="SkillSpector executable")
    ap.add_argument("--jobs", type=int, default=4, help="skills scanned in parallel (default 4)")
    args = ap.parse_args()
    if not args.skillspector:
        print("SkillSpector not found: install it (see the header of this script) or pass --skillspector", file=sys.stderr)
        return 2
    skills = sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))
    orphans = sorted(f[:-5] for f in os.listdir(BASELINES) if f.endswith(".yaml") and f[:-5] not in skills)
    out_dir = args.out or tempfile.mkdtemp(prefix="skillspector-")
    os.makedirs(out_dir, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(lambda s: scan(args.skillspector, s, out_dir), skills))

    failed, active_total, suppressed_total = [], 0, 0
    print(f"{'skill':42} {'score':>5} {'active':>6} {'justified':>9}  coverage")
    for skill, report, error in results:
        if report is None:
            failed.append(f"{skill}: scan failed: {error}")
            print(f"{skill:42} {'-':>5} {'-':>6} {'-':>9}  scan failed")
            continue
        issues, suppressed = report.get("issues") or [], report.get("suppressed") or []
        active_total += len(issues)
        suppressed_total += len(suppressed)
        coverage = (report.get("analysis_completeness") or {}).get("coverage_percent")
        score = (report.get("risk_assessment") or {}).get("score")
        print(f"{skill:42} {score if score is not None else '-':>5} {len(issues):>6} {len(suppressed):>9}  {coverage}%")
        if not report.get("execution_successful", True):
            failed.append(f"{skill}: SkillSpector reported an unsuccessful execution")
        for i in issues:
            loc = i.get("location") or {}
            failed.append(f"{skill}/{loc.get('file')}:{loc.get('start_line')} {i.get('id')} {i.get('severity')} "
                          f"{i.get('finding') or i.get('pattern') or ''}: {i.get('explanation', '')[:120]}")
        for rule in unused_rules(skill, suppressed):
            print(f"WARNING {skill}: baseline rule matches nothing, remove it: {rule.get('id')} {rule.get('path')} {rule.get('message')}")
    for name in orphans:
        print(f"WARNING baseline without skill: tools/skillspector/{name}.yaml")
    print(f"\n{len(skills)} skills, {active_total} unjustified finding(s), {suppressed_total} justified in baselines. "
          f"Reports: {out_dir}")
    for f in failed:
        print(f"FAIL {f}")
    if failed:
        print("Fix the skill, or if the match is a false positive add a scoped rule with its reason to "
              "tools/skillspector/<skill>.yaml (id + path, plus the matched text when the finding has one).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
