#!/usr/bin/env python3
"""bob-kit migration guard (IBM Bob lifecycle hook, PreToolUse on file writes).

Blocks edits to Flyway *versioned* migrations (V<version>__<desc>.sql / .java) that already exist
on the default branch: they are probably applied somewhere, and editing them breaks Flyway's
checksum validation or silently diverges environments. New migrations, migrations created on the
current branch (not merged yet) and repeatable migrations (R__*.sql) are allowed.

Exit 2 = block, 0 = allow; any internal error exits 0 (fail-open).
"""
import json
import os
import re
import subprocess
import sys

VERSIONED = re.compile(r"(^|/)V\d+(?:[._]\d+)*__[^/]+\.(sql|java|kt)$")
PATH_KEYS = ("path", "file_path", "filePath", "file", "target_file", "filename")


def git(cwd, *args):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
    return r.stdout.strip() if r.returncode == 0 else None


def base_ref(cwd):
    """The default branch tip the current branch is based on (origin/HEAD, else main/master), else HEAD."""
    default = git(cwd, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    for ref in filter(None, [default, "origin/main", "origin/master", "main", "master"]):
        if git(cwd, "rev-parse", "--verify", "--quiet", ref + "^{commit}"):
            return git(cwd, "merge-base", "HEAD", ref) or ref
    return "HEAD"


def main():
    event = json.load(sys.stdin)
    if event.get("hook_event_name") != "PreToolUse":
        return 0
    tool_input = event.get("tool_input") or {}
    path = next((tool_input[k] for k in PATH_KEYS if isinstance(tool_input, dict) and isinstance(tool_input.get(k), str)), "")
    if not path or not VERSIONED.search(path.replace("\\", "/")):
        return 0
    cwd = event.get("cwd") or os.getcwd()
    top = git(cwd, "rev-parse", "--show-toplevel")
    if not top:
        return 0
    rel = os.path.relpath(os.path.realpath(os.path.join(cwd, path)), os.path.realpath(top)).replace(os.sep, "/")
    base = base_ref(top)
    exists_on_base = subprocess.run(["git", "-C", top, "cat-file", "-e", f"{base}:{rel}"],
                                    capture_output=True, timeout=5).returncode == 0
    if not exists_on_base:
        return 0
    sys.stderr.write(f"[bob-kit migration-guard] Blocked: {rel} is a Flyway versioned migration that already exists on the "
                     "default branch (probably applied). Create a new migration (next version) instead of editing it.\n")
    print(f"Blocked by migration-guard: {rel} is already merged; write a new versioned migration instead.")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail-open
        sys.stderr.write(f"[bob-kit migration-guard] internal error, allowing: {exc}\n")
        sys.exit(0)
