#!/usr/bin/env python3
"""Summarise a release range from git: grouped changes, MR references,
breaking changes, risky files and a semantic-version proposal.

Read-only: runs `git log` and `git diff` only. Standard library only.

Examples:
  python3 release_changes.py v1.3.0..v1.4.0
  python3 release_changes.py v1.3.0..HEAD --repo ../payments-api --json
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys

CONVENTIONAL = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<desc>.+)$")
MR_REF = re.compile(r"(?:^|[\s(\[])(?P<proj>(?:[\w.-]+/)+[\w.-]+)?!(?P<iid>\d+)\b")
BREAKING_BODY = re.compile(r"^BREAKING[ -]CHANGE:\s*(.+)$", re.MULTILINE)
GROUPS = [
    ("feat", "Features"), ("fix", "Bug fixes"), ("security", "Security"), ("perf", "Performance"),
    ("refactor", "Refactoring"), ("revert", "Reverts"), ("docs", "Documentation"), ("test", "Tests"),
    ("build", "Build and dependencies"), ("deps", "Build and dependencies"), ("ci", "CI/CD"),
    ("chore", "Chores"), ("style", "Style"),
]
GROUP_TITLE = dict(GROUPS)
RISK_RULES = [
    ("Database migrations", ["*/db/migration/*", "*/migrations/*", "*/changelog/*.xml", "*/changelog/*.yaml",
                             "*/db/changelog*", "*.sql"]),
    ("Configuration", ["*application*.yml", "*application*.yaml", "*application*.properties", "*bootstrap*.yml",
                       "*values*.yaml", "*.env", "*environment*.ts", "*/config/*.json"]),
    ("Dependencies", ["*pom.xml", "*build.gradle", "*build.gradle.kts", "*libs.versions.toml", "*package.json",
                      "*package-lock.json", "*yarn.lock", "*pnpm-lock.yaml"]),
    ("API contracts", ["*openapi*.yaml", "*openapi*.yml", "*openapi*.json", "*swagger*", "*.proto", "*.avsc",
                       "*.graphql", "*Controller.java", "*Resource.java", "*Endpoint.java"]),
    ("Security configuration", ["*Security*.java", "*security*.ts", "*auth*.ts", "*Auth*.java", "*guard*.ts",
                                "*interceptor*.ts"]),
    ("Infrastructure and deployment", ["*Dockerfile*", "*.tf", "*/helm/*", "*/charts/*", "*/k8s/*",
                                       "*kustomization.yaml", "*/manifests/*", "*/argocd/*", "*/deploy/*"]),
    ("CI/CD", [".gitlab-ci.yml", "*.gitlab-ci.yml", ".gitlab/*", "*Jenkinsfile*", ".github/workflows/*"]),
]
SEMVER = re.compile(r"^(?P<prefix>[^\d]*)(?P<maj>\d+)\.(?P<min>\d+)\.(?P<pat>\d+)$")


def git(repo, *args):
    res = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if res.returncode != 0:
        first = (res.stderr.strip().splitlines() or ["unknown error"])[0]
        sys.exit(f"git {args[0]} failed: {first}")
    return res.stdout


def classify_paths(paths):
    found = {}
    for path in paths:
        p = "/" + path
        for label, globs in RISK_RULES:
            if any(fnmatch.fnmatch(p, g) or fnmatch.fnmatch(path, g) for g in globs):
                found.setdefault(label, []).append(path)
    return found


def propose_version(base_ref, breaking, has_feat):
    m = SEMVER.match(base_ref)
    if not m:
        return None
    maj, mi, pa = int(m["maj"]), int(m["min"]), int(m["pat"])
    if breaking:
        maj, mi, pa = (maj + 1, 0, 0) if maj > 0 else (0, mi + 1, 0)
    elif has_feat:
        mi, pa = mi + 1, 0
    else:
        pa += 1
    return f"{m['prefix']}{maj}.{mi}.{pa}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("range", help="FROM..TO (e.g. v1.3.0..v1.4.0 or v1.3.0..HEAD)")
    ap.add_argument("--repo", default=".", help="repository path (default: current directory)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.range.startswith("-") or ".." not in a.range:
        sys.exit("range must look like FROM..TO")
    base, _, head = a.range.partition("..")
    head = head.lstrip(".") or "HEAD"

    raw = git(a.repo, "log", "--format=%H%x1f%P%x1f%s%x1f%b%x1e", f"{base}..{head}")
    commits, mrs, breaking = [], {}, []
    for rec in filter(None, (r.strip("\n") for r in raw.split("\x1e"))):
        sha, parents, subject, body = (rec.split("\x1f") + ["", "", "", ""])[:4]
        is_merge = len(parents.split()) > 1
        body_lines = [l for l in body.splitlines() if l.strip()]
        # GitLab merge commits: "Merge branch 'x' into 'y'", then the MR title, then "See merge request g/p!123"
        title = body_lines[0] if is_merge and body_lines else subject
        for m in MR_REF.finditer(f"{subject}\n{body}"):
            mrs.setdefault(f"{m['proj'] or ''}!{m['iid']}", title)
        if is_merge:
            continue
        cm = CONVENTIONAL.match(subject)
        ctype = cm["type"].lower() if cm else "other"
        if cm and (cm["bang"] or BREAKING_BODY.search(body)):
            breaking.append({"sha": sha[:8], "subject": subject,
                             "note": (BREAKING_BODY.search(body) or [None, cm["desc"]])[1]})
        commits.append({"sha": sha[:8], "type": ctype, "scope": cm["scope"] if cm else None,
                        "subject": cm["desc"] if cm else subject})

    paths = [p for p in git(a.repo, "diff", "--name-only", base, head).splitlines() if p]
    risky = classify_paths(paths)
    has_feat = any(c["type"] == "feat" for c in commits)
    proposal = propose_version(base, bool(breaking), has_feat)
    conventional_share = sum(c["type"] != "other" for c in commits) / len(commits) if commits else 0

    result = {"range": f"{base}..{head}", "commits": len(commits), "files_changed": len(paths),
              "conventional_share": round(conventional_share, 2), "version_proposal": proposal,
              "breaking": breaking, "merge_requests": [{"ref": k, "title": v} for k, v in mrs.items()],
              "risky_files": risky, "changes": commits}
    if a.json:
        print(json.dumps(result, indent=2))
        return

    print(f"# Release {base}..{head}\n")
    print(f"{len(commits)} commits (merges excluded), {len(paths)} files changed, "
          f"{len(mrs)} MR references, {int(conventional_share * 100)}% conventional commits.")
    if proposal:
        print(f"Version proposal (SemVer from {base}): **{proposal}**"
              + (" (breaking changes)" if breaking else " (features)" if has_feat else " (fixes only)"))
    if conventional_share < 0.5 and commits:
        print("\n> Most commits are not Conventional Commits: grouping and the version proposal are unreliable; "
              "classify from the MR titles and descriptions instead.")
    if breaking:
        print("\n## Breaking changes")
        for b in breaking:
            print(f"- {b['note']} ({b['sha']})")
    print("\n## Risky areas to cover in the risk assessment and runbook")
    if not risky:
        print("- none detected by file patterns (still review the MRs)")
    for label, files in risky.items():
        shown = ", ".join(f"`{f}`" for f in files[:8]) + (f" … (+{len(files) - 8})" if len(files) > 8 else "")
        print(f"- **{label}** ({len(files)}): {shown}")
    if mrs:
        print("\n## Merge requests referenced")
        for ref, title in mrs.items():
            print(f"- {ref} {title}")
    print("\n## Changes")
    order = [t for t, _ in GROUPS] + ["other"]
    for t in sorted({c["type"] for c in commits}, key=lambda x: order.index(x) if x in order else len(order)):
        print(f"\n### {GROUP_TITLE.get(t, 'Other changes')}")
        for c in (c for c in commits if c["type"] == t):
            scope = f"**{c['scope']}**: " if c["scope"] else ""
            print(f"- {scope}{c['subject']} ({c['sha']})")


if __name__ == "__main__":
    main()
