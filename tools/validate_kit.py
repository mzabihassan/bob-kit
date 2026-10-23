#!/usr/bin/env python3
"""Validate the bob-kit repository: skills, modes and hooks configuration.

Run from the repository root:  python3 tools/validate_kit.py
Checks:
- skills: SKILL.md frontmatter (name = folder, description, groups = mode slugs or tool groups, no
  'modes'), <Steps> tags, referenced files exist,
  supporting files are referenced, Python scripts compile;
- modes: custom_modes.yaml fields, slugs, tool groups, fileRegex compiles and passes the cases in
  tools/mode_regex_cases.json (needs PyYAML; skipped with a warning otherwise);
- hooks: settings.example.json schema and referenced scripts exist.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_FILES = {"AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "README.md", "CHANGELOG.md", "summary.md"}
GROUPS = {"read", "edit", "execute", "mcp", "skill", "workflow", "todo", "subtask", "subagent", "mode"}
HOOK_EVENTS = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"}
errors, warnings = [], []


def syntax_error(path):
    """Compile a Python file in memory (no .pyc written); return the error message or None."""
    try:
        with open(path, encoding="utf-8") as fh:
            compile(fh.read(), path, "exec")
    except SyntaxError as exc:
        return f"line {exc.lineno}: {exc.msg}"
    return None


def mode_slugs():
    """Slugs declared in modes/custom_modes.yaml (read without PyYAML)."""
    path = os.path.join(ROOT, "modes", "custom_modes.yaml")
    if not os.path.isfile(path):
        return set()
    return set(re.findall(r"^\s*- slug:\s*(\S+)", open(path, encoding="utf-8").read(), re.M))


def check_skills():
    base = os.path.join(ROOT, "skills")
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if not os.path.isdir(d):
            continue
        skill_md = os.path.join(d, "SKILL.md")
        if not os.path.isfile(skill_md):
            errors.append(f"skills/{name}: missing SKILL.md")
            continue
        text = open(skill_md, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            errors.append(f"skills/{name}: missing YAML frontmatter")
            continue
        fm = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
        if fm.get("name") != name:
            errors.append(f"skills/{name}: frontmatter name '{fm.get('name')}' != folder name")
        if not fm.get("description"):
            errors.append(f"skills/{name}: missing description")
        if "modes" in fm:
            errors.append(f"skills/{name}: Bob ignores 'modes'; use 'groups: [<mode-slug>]' to limit the skill to a mode")
        if "groups" in fm:
            # Bob offers the skill only in modes whose slug or tool groups match; a typo hides it everywhere.
            g = re.fullmatch(r"\[(.*)\]", fm["groups"].strip())
            values = [v.strip() for v in g.group(1).split(",") if v.strip()] if g else []
            if not values:
                errors.append(f"skills/{name}: groups must be a non-empty inline list, e.g. [security-remediator]")
            for v in values:
                if v not in GROUPS and v not in mode_slugs():
                    errors.append(f"skills/{name}: groups value '{v}' is neither a mode slug nor a tool group")
        body = text[m.end():]
        if "<Steps>" not in body or body.count("<Step>") != body.count("</Step>"):
            errors.append(f"skills/{name}: unbalanced or missing <Steps>/<Step> tags")
        refs = set(re.findall(r"`((?:scripts/)?[\w-]+\.(?:md|py|sh))`", body))
        for ref in sorted(refs - PROJECT_FILES):
            if not os.path.exists(os.path.join(d, ref)):
                errors.append(f"skills/{name}: references missing file {ref}")
        for root, _, files in os.walk(d):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), d)
                if f == "SKILL.md" or "__pycache__" in rel:
                    continue
                if rel not in refs:
                    warnings.append(f"skills/{name}: {rel} is not referenced from SKILL.md")
                if f.endswith(".py") and syntax_error(os.path.join(root, f)):
                    errors.append(f"skills/{name}/{rel}: does not compile: {syntax_error(os.path.join(root, f))}")


def check_modes():
    path = os.path.join(ROOT, "modes", "custom_modes.yaml")
    if not os.path.isfile(path):
        return
    try:
        import yaml
    except ImportError:
        warnings.append("modes: PyYAML not installed, custom_modes.yaml not validated (pip install pyyaml)")
        return
    data = yaml.safe_load(open(path, encoding="utf-8"))
    modes = data.get("customModes") or []
    slugs = [m.get("slug") for m in modes]
    if len(slugs) != len(set(slugs)):
        errors.append("modes: duplicate slugs")
    cases_path = os.path.join(ROOT, "tools", "mode_regex_cases.json")
    cases = json.load(open(cases_path)) if os.path.isfile(cases_path) else {}
    for m in modes:
        slug = m.get("slug") or "?"
        for field in ("slug", "name", "roleDefinition"):
            if not m.get(field):
                errors.append(f"modes/{slug}: missing {field}")
        if not re.fullmatch(r"[A-Za-z0-9-]+", slug):
            errors.append(f"modes/{slug}: invalid slug")
        for g in m.get("groups") or []:
            group = g[0] if isinstance(g, list) else g
            if group not in GROUPS:
                errors.append(f"modes/{slug}: unknown group {group}")
            if isinstance(g, list) and len(g) > 1 and g[1].get("fileRegex"):
                try:
                    rx = re.compile(g[1]["fileRegex"])
                except re.error as exc:
                    errors.append(f"modes/{slug}: fileRegex does not compile: {exc}")
                    continue
                c = cases.get(slug)
                if not c:
                    warnings.append(f"modes/{slug}: no fileRegex test cases in tools/mode_regex_cases.json")
                    continue
                errors.extend(f"modes/{slug}: fileRegex should allow {p}" for p in c["allow"] if not rx.search(p))
                errors.extend(f"modes/{slug}: fileRegex should deny {p}" for p in c["deny"] if rx.search(p))


def check_hooks():
    path = os.path.join(ROOT, "hooks", "settings.example.json")
    if not os.path.isfile(path):
        return
    try:
        data = json.load(open(path, encoding="utf-8"))
    except ValueError as exc:
        errors.append(f"hooks/settings.example.json: invalid JSON: {exc}")
        return
    for event, entries in (data.get("hooks") or {}).items():
        if event not in HOOK_EVENTS:
            errors.append(f"hooks: unknown event {event}")
        for entry in entries:
            if "matcher" in entry:
                if event not in ("PreToolUse", "PostToolUse"):
                    warnings.append(f"hooks: matcher on {event} is ignored by Bob")
                try:
                    re.compile(entry["matcher"])
                except re.error as exc:
                    errors.append(f"hooks: invalid matcher {entry['matcher']}: {exc}")
            for h in entry.get("hooks") or []:
                if h.get("type") != "command" or not h.get("command"):
                    errors.append(f"hooks/{event}: each hook needs type 'command' and a command")
                    continue
                script = re.search(r"\.bob/hooks/([\w.-]+)", h["command"])
                if script and not os.path.isfile(os.path.join(ROOT, "hooks", script.group(1))):
                    errors.append(f"hooks/{event}: script {script.group(1)} not found in hooks/")
    for f in os.listdir(os.path.join(ROOT, "hooks")):
        if f.endswith(".py") and syntax_error(os.path.join(ROOT, "hooks", f)):
            errors.append(f"hooks/{f}: does not compile: {syntax_error(os.path.join(ROOT, 'hooks', f))}")


def main():
    check_skills()
    check_modes()
    check_hooks()
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    skills = len([d for d in os.listdir(os.path.join(ROOT, "skills")) if os.path.isdir(os.path.join(ROOT, "skills", d))])
    print(f"{'FAILED' if errors else 'OK'}: {skills} skills, {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
