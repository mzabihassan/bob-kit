#!/usr/bin/env python3
"""Rank source files by coverage gain per unit of test effort.

Reads JaCoCo XML and/or LCOV reports (Java, Angular/TypeScript), estimates how
easy each file is to test from its source, and prints the best quick wins.
Standard library only; reads files, never modifies anything.

Examples:
  python3 coverage_hotspots.py target/site/jacoco/jacoco.xml --src .
  python3 coverage_hotspots.py **/jacoco.xml coverage/lcov.info --top 15
  git diff --name-only origin/main... > changed.txt
  python3 coverage_hotspots.py jacoco.xml --changed changed.txt   # new-code focus
"""
import argparse
import fnmatch
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", ".angular", ".gradle", "coverage", ".idea"}
DEFAULT_EXCLUDES = [
    "*/generated/*", "*/generated-sources/*", "*MapperImpl.java", "*Application.java",
    "*Test.java", "*Tests.java", "*IT.java", "*.spec.ts", "*.test.ts", "*.module.ts",
    "*/main.ts", "*/environment*.ts", "*/polyfills.ts", "*/test.ts",
]
INFRA_JAVA = re.compile(r"\b(EntityManager|JdbcTemplate|RestTemplate|WebClient|RestClient|HttpClient|KafkaTemplate|JmsTemplate|"
                        r"Files\.|new File\(|Socket|Thread\.sleep|System\.getenv|@Scheduled|@KafkaListener|@JmsListener)\b")
INFRA_TS = re.compile(r"\b(window\.|document\.|localStorage|sessionStorage|setTimeout|setInterval|ElementRef|Renderer2|"
                      r"WebSocket|IntersectionObserver|navigator\.)")
JAVA_PRIMITIVE = {"String", "int", "long", "boolean", "double", "Integer", "Long", "Boolean", "BigDecimal",
                  "Duration", "Clock", "Logger"}


class FileCov:
    __slots__ = ("path", "lang", "lines", "lines_missed", "branches", "branches_missed", "source")

    def __init__(self, path, lang):
        self.path, self.lang = path, lang
        self.lines = self.lines_missed = self.branches = self.branches_missed = 0
        self.source = None


def parse_jacoco(path, out):
    root = ET.parse(path).getroot()  # external DTD is not fetched by ElementTree
    for pkg in root.iter("package"):
        pname = pkg.get("name", "")
        for sf in pkg.findall("sourcefile"):
            rel = f"{pname}/{sf.get('name')}" if pname else sf.get("name")
            fc = out.setdefault(("java", rel), FileCov(rel, "java"))
            for c in sf.findall("counter"):
                missed, covered = int(c.get("missed", 0)), int(c.get("covered", 0))
                if c.get("type") == "LINE":
                    fc.lines += missed + covered
                    fc.lines_missed += missed
                elif c.get("type") == "BRANCH":
                    fc.branches += missed + covered
                    fc.branches_missed += missed


def parse_lcov(path, out):
    base = os.path.dirname(os.path.abspath(path))
    cur, rec = None, {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if line.startswith("SF:"):
                cur = out.setdefault(("ts", line[3:]), FileCov(line[3:], "ts"))
                cur.source = base
                rec = {"LF": 0, "LH": 0, "BRF": 0, "BRH": 0}
            elif cur is not None and line == "end_of_record":
                cur.lines += rec["LF"]
                cur.lines_missed += rec["LF"] - rec["LH"]
                cur.branches += rec["BRF"]
                cur.branches_missed += rec["BRF"] - rec["BRH"]
                cur = None
            elif cur is not None and ":" in line:
                key, _, val = line.partition(":")
                if key in rec and val.isdigit():
                    rec[key] = int(val)


def index_sources(roots):
    idx = {}
    for root in roots:
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                if f.endswith((".java", ".ts")):
                    idx.setdefault(f, []).append(os.path.join(d, f))
    return idx


def resolve(fc, idx, roots):
    if fc.lang == "ts":
        base = fc.source or "."
        cands = [fc.path] + [os.path.join(r, fc.path) for r in roots]
        b = base
        for _ in range(4):
            cands.append(os.path.join(b, fc.path))
            b = os.path.dirname(b)
        for c in cands:
            if os.path.isfile(c):
                return os.path.normpath(c)
    name = os.path.basename(fc.path)
    suffix = fc.path.replace("\\", "/")
    for p in idx.get(name, []):
        if p.replace("\\", "/").endswith(suffix):
            return p
    return None


def has_test(src):
    if not src:
        return False
    d, f = os.path.split(src)
    if f.endswith(".ts"):
        stem = f[:-3]
        return any(os.path.isfile(os.path.join(d, stem + s)) for s in (".spec.ts", ".test.ts"))
    stem = f[:-5]
    test_dir = d.replace(os.sep + "main" + os.sep, os.sep + "test" + os.sep)
    return any(os.path.isfile(os.path.join(test_dir, stem + s)) for s in ("Test.java", "Tests.java", "IT.java"))


def classify(fc, text):
    name = os.path.basename(fc.path)
    if fc.lang == "ts":
        for suffix, kind in ((".pipe.ts", "pipe"), ("validator", "validator"), ("util", "util"), ("helper", "util"),
                             (".guard.ts", "guard"), (".interceptor.ts", "interceptor"), (".resolver.ts", "resolver"),
                             (".service.ts", "service"), (".store.ts", "store"), (".component.ts", "component")):
            if suffix in name.lower():
                return kind
        return "component" if text and "@Component" in text else "ts"
    t = text or ""
    lname = name.lower()
    if "@RestController" in t or "@Controller" in t:
        return "controller"
    if "@ControllerAdvice" in t or "@RestControllerAdvice" in t:
        return "exception-handler"
    if "@Configuration" in t or "SecurityFilterChain" in t:
        return "config"
    if "@Entity" in t:
        return "entity"
    if re.search(r"\b(record|enum)\s+\w+", t) and "class " not in t:
        return "value"
    for key, kind in (("mapper", "mapper"), ("converter", "mapper"), ("validator", "validator"), ("util", "util"),
                      ("helper", "util"), ("calculator", "logic"), ("policy", "logic"), ("rule", "logic"),
                      ("service", "service"), ("job", "job"), ("scheduler", "job"), ("listener", "job")):
        if key in lname:
            return kind
    if "@Service" in t or "@Component" in t:
        return "service"
    return "class"


def count_deps(fc, text):
    if not text:
        return None
    if fc.lang == "ts":
        return len(re.findall(r"\binject\(", text)) + len(re.findall(r"(?:private|protected|public|readonly)\s+\w+\s*:\s*[A-Z]\w*", text))
    fields = re.findall(r"private\s+final\s+([A-Z][\w<>,\s]*?)\s+\w+\s*;", text)
    deps = [f for f in fields if f.split("<")[0].strip() not in JAVA_PRIMITIVE]
    return len(deps) + len(re.findall(r"@Autowired", text))


EASY_KINDS = {"pipe", "validator", "util", "mapper", "value", "exception-handler", "logic"}
HARD_KINDS = {"config", "job"}


def effort(kind, deps, infra, tested):
    score = 1 if kind in EASY_KINDS else 3 if kind in HARD_KINDS else 2
    if deps is not None:
        score += 1 if deps >= 4 else 0
        score += 1 if deps >= 7 else 0
    score += 1 if infra else 0
    score -= 1 if tested else 0
    return max(1, min(4, score))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("reports", nargs="+", help="jacoco.xml and/or lcov.info files")
    ap.add_argument("--src", action="append", help="source roots to resolve files (default: current dir)")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--min-missed", type=int, default=5, help="ignore files with fewer missed lines+branches")
    ap.add_argument("--exclude", action="append", default=[], help="extra glob to exclude (repeatable)")
    ap.add_argument("--changed", help="file listing changed paths (one per line) to focus on new code")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    roots = a.src or ["."]

    files = {}
    for r in a.reports:
        with open(r, "rb") as fh:
            head = fh.read(512)
        (parse_jacoco if b"<report" in head or head.lstrip().startswith(b"<?xml") else parse_lcov)(r, files)
    if not files:
        sys.exit("No coverage data found in the given reports.")

    changed = None
    if a.changed:
        with open(a.changed, encoding="utf-8") as fh:
            changed = [l.strip().replace("\\", "/") for l in fh if l.strip()]

    idx = index_sources(roots) if any(f.lang == "java" for f in files.values()) else {}
    excludes = DEFAULT_EXCLUDES + a.exclude
    total = sum(f.lines + f.branches for f in files.values())
    covered = sum(f.lines - f.lines_missed + f.branches - f.branches_missed for f in files.values())

    rows = []
    for fc in files.values():
        src = resolve(fc, idx, roots)
        shown = os.path.normpath(src or fc.path).replace("\\", "/")
        if any(fnmatch.fnmatch(shown, g) or fnmatch.fnmatch("/" + shown, g) for g in excludes):
            continue
        if changed is not None and not any(shown.endswith(c) or c.endswith(fc.path) for c in changed):
            continue
        missed = fc.lines_missed + fc.branches_missed
        if missed < a.min_missed:
            continue
        text = None
        if src:
            with open(src, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        kind = classify(fc, text)
        deps = count_deps(fc, text)
        infra = bool(text and (INFRA_TS if fc.lang == "ts" else INFRA_JAVA).search(text))
        tested = has_test(src)
        eff = effort(kind, deps, infra, tested)
        gain = 100.0 * missed / total if total else 0.0
        size = fc.lines + fc.branches
        rows.append({
            "file": shown, "kind": kind, "missed_lines": fc.lines_missed, "missed_branches": fc.branches_missed,
            "coverage": round(100.0 * (size - missed) / size, 1) if size else 0.0,
            "deps": deps, "infra": infra, "has_test": tested, "effort": eff,
            "max_gain_pp": round(gain, 2), "score": round(gain / eff, 3),
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    top = rows[: a.top]
    baseline = 100.0 * covered / total if total else 0.0
    upper = sum(r["max_gain_pp"] for r in top)

    if a.json:
        print(json.dumps({"baseline_pct": round(baseline, 2), "top_upper_bound_pp": round(upper, 2), "candidates": top}, indent=2))
        return
    print(f"Baseline (lines+branches, Sonar-style approximation): {baseline:.1f}%  [{covered}/{total}]")
    print(f"Top {len(top)} fully covered: +{upper:.1f} pp (upper bound); at ~70% of missed: +{upper * 0.7:.1f} pp\n")
    print("| # | File | Kind | Missed L/B | Cov % | Deps | Test? | Effort | Max gain pp |")
    print("|---|------|------|-----------|-------|------|-------|--------|-------------|")
    for i, r in enumerate(top, 1):
        deps = "?" if r["deps"] is None else r["deps"]
        flag = " infra" if r["infra"] else ""
        print(f"| {i} | {r['file']} | {r['kind']}{flag} | {r['missed_lines']}/{r['missed_branches']} | {r['coverage']} | "
              f"{deps} | {'yes' if r['has_test'] else 'no'} | {r['effort']} | {r['max_gain_pp']} |")
    print("\nEffort 1 = trivial, 4 = hard (heuristic from kind, injected deps, infrastructure use, existing test). "
          "Verify each candidate by reading it before writing tests.")


if __name__ == "__main__":
    main()
