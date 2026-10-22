#!/usr/bin/env python3
"""bob-kit project context (IBM Bob lifecycle hook, SessionStart).

Prints a short project baseline that Bob adds to the model context at session start: git branch
and state, detected stack versions (Java, Spring Boot, Angular, React, TypeScript, Node) and the
instruction files present. Read-only, fast, and silent on any error (exit 0 always).
"""
import json
import os
import re
import subprocess
import sys

SKIP = {".git", "node_modules", "target", "build", "dist", ".angular", ".gradle", "coverage", ".next", "vendor"}
INSTRUCTION_FILES = ["AGENTS.md", "CLAUDE.md", ".bobrules", "CONTRIBUTING.md", ".github/copilot-instructions.md"]


def git(cwd, *args):
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def find(root, names, depth=3):
    found = []
    for d, dirs, files in os.walk(root):
        rel_depth = os.path.relpath(d, root).count(os.sep)
        dirs[:] = [x for x in dirs if x not in SKIP and not x.startswith(".")] if rel_depth < depth else []
        found += [os.path.join(d, f) for f in files if f in names]
    return found


def maven(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    boot = re.search(r"<parent>.*?<artifactId>spring-boot-starter-parent</artifactId>\s*<version>([^<]+)</version>", text, re.S)
    if boot:
        out.append(f"Spring Boot {boot.group(1)}")
    elif "spring-boot" in text:
        v = re.search(r"<spring-boot\.version>([^<]+)<", text)
        out.append(f"Spring Boot {v.group(1)}" if v else "Spring Boot (BOM)")
    java = re.search(r"<(?:java\.version|maven\.compiler\.release|maven\.compiler\.source)>([^<]+)<", text)
    if java:
        out.append(f"Java {java.group(1)}")
    return out


def gradle(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    boot = re.search(r"org\.springframework\.boot['\"]?\)?\s*version\s*['\"]([^'\"]+)", text)
    if boot:
        out.append(f"Spring Boot {boot.group(1)}")
    java = re.search(r"(?:languageVersion\s*(?:=|\.set\()\s*JavaLanguageVersion\.of\((\d+)\)|sourceCompatibility\s*=\s*['\"]?(?:JavaVersion\.VERSION_)?([\d_.]+))", text)
    if java:
        out.append(f"Java {(java.group(1) or java.group(2)).replace('_', '.')}")
    return out


def npm(path):
    try:
        with open(path, encoding="utf-8") as fh:
            pkg = json.load(fh)
    except (OSError, ValueError):
        return []
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    out = [f"{label} {deps[name]}" for name, label in (("@angular/core", "Angular"), ("react", "React"), ("next", "Next.js"),
                                                       ("vue", "Vue"), ("typescript", "TypeScript"), ("vitest", "Vitest"),
                                                       ("jest", "Jest"), ("karma", "Karma")) if name in deps]
    if pkg.get("engines", {}).get("node"):
        out.append(f"Node {pkg['engines']['node']}")
    return out


def main():
    event = json.load(sys.stdin)
    root = git(event.get("cwd") or os.getcwd(), "rev-parse", "--show-toplevel") or event.get("cwd") or os.getcwd()
    lines = ["[bob-kit project context]"]
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch:
        dirty = len([l for l in git(root, "status", "--porcelain").splitlines() if l.strip()])
        ahead_behind = git(root, "rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        sync = ""
        if ahead_behind:
            behind, ahead = ahead_behind.split()
            sync = f", {ahead} ahead / {behind} behind upstream"
        last = git(root, "log", "-1", "--format=%h %s (%cr)")
        lines.append(f"Git: branch {branch}, {dirty} changed file(s){sync}; last commit {last}")
    stack = []
    for p in find(root, {"pom.xml"})[:4]:
        stack += [f"{s} [{os.path.relpath(p, root)}]" for s in maven(p)]
    for p in find(root, {"build.gradle", "build.gradle.kts"})[:4]:
        stack += [f"{s} [{os.path.relpath(p, root)}]" for s in gradle(p)]
    for p in find(root, {"package.json"})[:4]:
        stack += [f"{s} [{os.path.relpath(p, root)}]" for s in npm(p)]
    nvmrc = os.path.join(root, ".nvmrc")
    if os.path.isfile(nvmrc):
        stack.append(f"Node {open(nvmrc).read().strip()} [.nvmrc]")
    if stack:
        lines.append("Stack: " + "; ".join(dict.fromkeys(stack)))
    present = [f for f in INSTRUCTION_FILES if os.path.isfile(os.path.join(root, f))]
    rules = [d for d in (".bob/rules",) if os.path.isdir(os.path.join(root, d))]
    rules += sorted(d for d in os.listdir(os.path.join(root, ".bob")) if d.startswith("rules-")) if os.path.isdir(os.path.join(root, ".bob")) else []
    if present or rules:
        lines.append("Project instructions to follow: " + ", ".join(present + rules))
    if len(lines) > 1:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never block or break a session start
        sys.stderr.write(f"[bob-kit project-context] internal error: {exc}\n")
        sys.exit(0)
