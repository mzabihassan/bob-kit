#!/usr/bin/env python3
"""Summarise axe-core results into a short, prioritised accessibility findings table.

Reads one or more axe-core JSON results (from @axe-core/playwright, @axe-core/cli
--save/--stdout, cypress-axe or axe.run() output written to disk): a results object,
a list of them, or any JSON containing them. Groups violations by rule across pages,
ranks them, and maps each rule to WCAG success criteria, RGAA 4.1.2 criteria and
EN 301 549 clauses using the rule tags (axe-core 4.11+ carries RGAA-* and EN-9.* tags;
older versions fall back to the official RGAA <-> WCAG correspondence). Lists the
"incomplete" items that need a manual decision and the RGAA criteria that received
no automated signal at all, which must be checked manually.
Standard library only; reads files, never modifies anything.

Examples:
  python3 axe_summary.py axe-results/*.json
  python3 axe_summary.py results.json --top 15 --out a11y-report/
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

IMPACT_RANK = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3, None: 4}

# RGAA 4.1.2 themes and number of criteria (106 in total).
RGAA_THEMES = {1: ("Images", 9), 2: ("Cadres", 2), 3: ("Couleurs", 3), 4: ("Multimédia", 13), 5: ("Tableaux", 8),
               6: ("Liens", 2), 7: ("Scripts", 5), 8: ("Éléments obligatoires", 10),
               9: ("Structuration de l'information", 4), 10: ("Présentation de l'information", 14),
               11: ("Formulaires", 13), 12: ("Navigation", 11), 13: ("Consultation", 12)}

# WCAG 2.1 success criterion -> RGAA 4.1.2 criteria, derived from the official RGAA dataset
# (github.com/DISIC/accessibilite.numerique.gouv.fr, RGAA/criteres.json, Licence Ouverte 2.0).
WCAG_TO_RGAA = {
    "1.1.1": ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.9", "4.7", "4.8", "4.9", "6.1", "6.2", "7.2", "10.2",
              "13.3", "13.4", "13.5", "13.6"],
    "1.2.1": ["4.1", "4.2"], "1.2.2": ["4.3", "4.4"], "1.2.3": ["4.1", "4.2"], "1.2.5": ["4.5", "4.6"],
    "1.3.1": ["3.1", "5.1", "5.2", "5.4", "5.5", "5.6", "5.7", "5.8", "7.3", "8.9", "9.1", "9.2", "9.3", "9.4", "10.1",
              "10.2", "11.1", "11.5", "11.6", "11.7", "11.8", "12.6", "13.3", "13.4"],
    "1.3.2": ["5.3", "8.10", "10.1", "10.3", "10.8", "13.3", "13.4"], "1.3.3": ["10.9", "10.10"], "1.3.4": ["13.9"],
    "1.3.5": ["11.13"], "1.4.1": ["3.1", "10.6", "10.7", "10.9", "10.10"], "1.4.2": ["4.10"], "1.4.3": ["3.2", "10.5"],
    "1.4.4": ["10.4"], "1.4.5": ["1.8"], "1.4.10": ["10.11"], "1.4.11": ["3.3"], "1.4.12": ["10.12"],
    "1.4.13": ["10.13"], "2.1.1": ["4.11", "4.12", "7.3", "10.14", "12.9", "12.11"], "2.1.2": ["4.11", "4.12", "12.9"],
    "2.1.4": ["12.10"], "2.2.1": ["13.1", "13.8"], "2.2.2": ["13.1", "13.8"], "2.3.1": ["13.7"],
    "2.4.1": ["9.1", "12.6", "12.7", "13.3", "13.4"], "2.4.2": ["8.5", "8.6"],
    "2.4.3": ["10.3", "12.7", "12.8", "13.3", "13.4"], "2.4.4": ["6.1", "6.2"], "2.4.5": ["12.1", "12.3", "12.4"],
    "2.4.6": ["9.1", "11.1", "11.2"], "2.4.7": ["7.3", "10.7"], "2.5.1": ["13.10"], "2.5.2": ["13.11"],
    "2.5.3": ["6.1", "7.1", "11.2", "11.9"], "2.5.4": ["13.12"], "3.1.1": ["8.3", "8.4", "13.3", "13.4"],
    "3.1.2": ["8.7", "8.8"], "3.2.1": ["7.4", "13.2"], "3.2.2": ["7.4"], "3.2.3": ["12.2", "12.4", "12.5", "12.7"],
    "3.2.4": ["11.3"], "3.3.1": ["11.10"], "3.3.2": ["11.1", "11.2", "11.4", "11.5", "11.6", "11.7", "11.10"],
    "3.3.3": ["11.11"], "3.3.4": ["11.12"], "4.1.1": ["8.1", "8.2"],
    "4.1.2": ["1.2", "1.3", "1.9", "2.1", "2.2", "4.13", "5.3", "7.1", "7.2", "8.2", "9.1", "10.8", "11.1", "11.9",
              "12.6", "13.3", "13.4"],
    "4.1.3": ["7.5"],
}
# Success criteria added by WCAG 2.2 at level A/AA: required by EN 301 549 V4.1.1, not part of RGAA 4.1.2.
WCAG22_NEW = {"2.4.11", "2.5.7", "2.5.8", "3.2.6", "3.3.7", "3.3.8"}


def sc_key(sc):
    return tuple(int(p) for p in sc.split("."))


def find_results(data):
    """Yield every axe results object (a dict with a 'violations' list) found in the JSON."""
    if isinstance(data, dict):
        if isinstance(data.get("violations"), list):
            yield data
            return
        for value in data.values():
            yield from find_results(value)
    elif isinstance(data, list):
        for item in data:
            yield from find_results(item)


def parse_tags(tags):
    """Return (wcag SCs, level label, rgaa criteria, rgaa via fallback, EN clauses) from axe rule tags."""
    scs = sorted({f"{m.group(1)}.{m.group(2)}.{m.group(3)}" for t in tags
                  for m in [re.fullmatch(r"wcag(\d)(\d)(\d{1,2})", t)] if m}, key=sc_key)
    levels = []
    if any(t in ("wcag2a", "wcag21a", "wcag22a") for t in tags):
        levels.append("A")
    if any(t in ("wcag2aa", "wcag21aa", "wcag22aa") for t in tags):
        levels.append("AA")
    if "wcag2aaa" in tags:
        levels.append("AAA")
    if "best-practice" in tags:
        levels.append("best practice")
    rgaa = sorted({".".join(t[5:].split(".")[:2]) for t in tags if re.fullmatch(r"RGAA-\d+\.\d+\.\d+", t)},
                  key=sc_key)
    fallback = False
    if not rgaa:
        mapped = sorted({c for sc in scs for c in WCAG_TO_RGAA.get(sc, [])}, key=sc_key)
        if mapped:
            rgaa, fallback = mapped, True
    en = sorted({t[3:] for t in tags if re.fullmatch(r"EN-9(\.\d+)+", t)}, key=sc_key)
    return scs, "/".join(levels) or "-", rgaa, fallback, en


def target_text(target):
    """axe node targets: a list per frame; shadow DOM targets are nested lists."""
    parts = [" >>> ".join(t) if isinstance(t, list) else str(t) for t in target or []]
    return " | ".join(parts)


def is_required(scs, levels, rgaa_tagged):
    """Mandatory today: an RGAA-tagged rule, or a WCAG 2.0/2.1 A/AA criterion (WCAG 2.2 additions are recommended
    until EN 301 549 V4.1.1 is cited or RGAA 5 applies)."""
    wcag_a_aa = any(l in ("A", "AA") for l in levels.split("/"))
    return rgaa_tagged or (wcag_a_aa and any(sc not in WCAG22_NEW for sc in scs))


def priority(impact, required):
    rank = IMPACT_RANK.get(impact, 4)
    if required and rank <= 1:
        return "P1"
    if (required and rank == 2) or (not required and rank <= 1):
        return "P2"
    return "P3"


def summarise(paths):
    rules, incomplete, signalled, pages, axe_versions = {}, defaultdict(lambda: {"nodes": 0, "pages": set()}), set(), set(), set()
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"skip {path}: {exc}", file=sys.stderr)
            continue
        for i, res in enumerate(find_results(data)):
            page = res.get("url") or f"{os.path.basename(path)}#{i + 1}"
            pages.add(page)
            version = (res.get("testEngine") or {}).get("version")
            if version:
                axe_versions.add(version)
            # Only real RGAA-* tags count as an automated signal: the WCAG fallback is too broad for this.
            for bucket in ("violations", "incomplete", "passes"):
                for rule in res.get(bucket) or []:
                    signalled.update(".".join(t[5:].split(".")[:2]) for t in rule.get("tags") or []
                                     if re.fullmatch(r"RGAA-\d+\.\d+\.\d+", t))
            for rule in res.get("violations") or []:
                rid = rule.get("id", "?")
                entry = rules.setdefault(rid, {"id": rid, "impact": rule.get("impact"), "tags": rule.get("tags") or [],
                                                "help": rule.get("help", ""), "helpUrl": rule.get("helpUrl", ""),
                                                "nodes": set(), "pages": set(), "targets": []})
                if IMPACT_RANK.get(rule.get("impact"), 4) < IMPACT_RANK.get(entry["impact"], 4):
                    entry["impact"] = rule.get("impact")
                entry["pages"].add(page)
                for node in rule.get("nodes") or []:
                    t = target_text(node.get("target"))
                    entry["nodes"].add((page, t))  # the same element scanned twice counts once
                    if t and t not in entry["targets"] and len(entry["targets"]) < 3:
                        entry["targets"].append(t)
            for rule in res.get("incomplete") or []:
                item = incomplete[rule.get("id", "?")]
                item["nodes"] += len(rule.get("nodes") or [])
                item["pages"].add(page)
                item["help"] = rule.get("help", "")

    findings = []
    for r in rules.values():
        scs, levels, rgaa, fallback, en = parse_tags(r["tags"])
        required = is_required(scs, levels, bool(rgaa) and not fallback)
        findings.append({
            "priority": priority(r["impact"], required), "mandatory": required, "rule": r["id"],
            "impact": r["impact"] or "-",
            "pages": len(r["pages"]), "nodes": len(r["nodes"]), "wcag": scs, "level": levels,
            "wcag22_only": [sc for sc in scs if sc in WCAG22_NEW], "rgaa": rgaa, "rgaa_from_wcag": fallback,
            "en301549": en, "help": r["help"], "helpUrl": r["helpUrl"], "examples": r["targets"],
        })
    findings.sort(key=lambda f: (f["priority"], IMPACT_RANK.get(f["impact"], 4), -f["pages"], -f["nodes"], f["rule"]))
    all_criteria = [f"{t}.{n}" for t, (_, count) in RGAA_THEMES.items() for n in range(1, count + 1)]
    unsignalled = [c for c in all_criteria if c not in signalled] if signalled else None  # None: no RGAA tags
    review = sorted(({"rule": k, "nodes": v["nodes"], "pages": len(v["pages"]), "help": v["help"]}
                     for k, v in incomplete.items()), key=lambda x: (-x["pages"], -x["nodes"], x["rule"]))
    return {"pages": sorted(pages), "axe_versions": sorted(axe_versions), "findings": findings,
            "needs_review": review, "rgaa_without_automated_signal": unsignalled}


def rgaa_cell(f):
    if not f["rgaa"]:
        return "WCAG 2.2 only" if f["wcag22_only"] else "-"
    if f["rgaa_from_wcag"] and len(f["rgaa"]) > 3:
        return f"several (via WCAG {', '.join(f['wcag'])})"
    return ", ".join(f["rgaa"]) + (" (via WCAG)" if f["rgaa_from_wcag"] else "")


def to_markdown(summary, top):
    f_all = summary["findings"]
    lines = [f"# Automated accessibility findings (axe-core {', '.join(summary['axe_versions']) or 'version unknown'})", "",
             f"{len(summary['pages'])} page(s) or state(s) scanned, {len(f_all)} failing rule(s), "
             f"{sum(f['nodes'] for f in f_all)} failing element(s). Automated checks cover only part of WCAG/RGAA: "
             "this is not a conformance result.", "",
             "| Priority | Status | Rule | Impact | Pages | Elements | WCAG (level) | RGAA 4.1.2 | EN 301 549 | Example |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for f in f_all[:top]:
        wcag = ", ".join(f["wcag"]) or "-"
        example = (f["examples"][0] if f["examples"] else "").replace("|", "\\|")
        status = "mandatory" if f["mandatory"] else "recommended"
        lines.append(f"| {f['priority']} | {status} | [{f['rule']}]({f['helpUrl']}) | {f['impact']} | {f['pages']} | {f['nodes']} | "
                     f"{wcag} ({f['level']}) | {rgaa_cell(f)} | {', '.join(f['en301549']) or '-'} | `{example}` |")
    if len(f_all) > top:
        lines.append(f"\n{len(f_all) - top} more rule(s) in the JSON output.")
    if summary["needs_review"]:
        lines += ["", "## Needs manual review (axe 'incomplete')", ""]
        lines += [f"- {r['rule']}: {r['nodes']} element(s) on {r['pages']} page(s) — {r['help']}"
                  for r in summary["needs_review"][:10]]
    unsignalled = summary["rgaa_without_automated_signal"]
    if unsignalled is None:
        lines += ["", "## RGAA coverage", "", "No RGAA tags in these results (axe-core older than 4.11): "
                  "all 106 RGAA criteria need a manual check, and RGAA mappings above come from WCAG."]
        return "\n".join(lines) + "\n"
    lines += ["", f"## RGAA criteria with no automated signal ({len(unsignalled)} of 106)", "",
              "Test these manually; the other criteria still need a manual confirmation, since a passing rule "
              "covers only part of a criterion.", ""]
    by_theme = defaultdict(list)
    for c in unsignalled:
        by_theme[int(c.split(".")[0])].append(c)
    lines += [f"- {t}. {RGAA_THEMES[t][0]}: {', '.join(cs)}" for t, cs in sorted(by_theme.items())]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", help="axe-core JSON result files (globs allowed)")
    ap.add_argument("--top", type=int, default=25, help="rules shown in the Markdown table (default 25)")
    ap.add_argument("--out", help="directory for summary.md and summary.json (default: print Markdown)")
    args = ap.parse_args(argv)
    paths = sorted({p for pattern in args.inputs for p in (glob.glob(pattern) or [pattern])})
    summary = summarise(paths)
    if not summary["pages"]:
        print("no axe-core results found in the inputs", file=sys.stderr)
        return 1
    markdown = to_markdown(summary, args.top)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as fh:
            fh.write(markdown)
        with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
        print(f"wrote {os.path.join(args.out, 'summary.md')} and summary.json")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
