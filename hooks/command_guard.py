#!/usr/bin/env python3
"""bob-kit dangerous-command guard (IBM Bob lifecycle hook, PreToolUse on execute_command).

Blocks irreversible or high-impact commands the agent should never run on its own; the user
can still run them manually. Edit RULES to fit your team. Exit 2 = block, 0 = allow; any
internal error exits 0 (fail-open) so a broken hook never blocks Bob.

Optional strict mode: set BOBKIT_STRICT_GIT=1 in the environment Bob runs in to also block
`git commit` and `git push` (the bob-kit skills already never commit unless asked).
"""
import json
import os
import re
import shlex
import sys

# (reason, regex applied to each sub-command, case-insensitive)
RULES = [
    ("force push rewrites shared history", r"^git\s+push\b.*\s(-f|--force|--force-with-lease|--force-if-includes)\b|^git\s+push\b.*\s\+\S+"),
    ("discards local work (git reset --hard)", r"^git\s+reset\b.*--hard\b"),
    ("deletes untracked files (git clean -f)", r"^git\s+clean\b.*\s-\w*f"),
    ("discards all local changes", r"^git\s+(checkout|restore)\b(?!.*--staged)(?!.*\s-S\b).*\s(--\s+)?\.$"),
    ("deletes branches or tags on the remote", r"^git\s+push\b.*\s(--delete|-d)\b|^git\s+push\s+\S+\s+:\S+"),
    ("applies or destroys infrastructure", r"^(terraform|tofu|terragrunt)\s+(apply|destroy|import|state\s+(rm|mv|push))\b"),
    ("changes a Kubernetes cluster directly (use GitOps)",
     r"^(kubectl|oc)\s+(?!.*--dry-run)(\S+\s+)*?(delete|apply|create|replace|patch|edit|scale|drain|cordon|uncordon|taint|rollout\s+(restart|undo)|set\s+image)(\s|$)"),
    ("deletes a Helm release", r"^helm\s+(?!.*--dry-run)(uninstall|delete|rollback)\b"),
    ("deletes or rolls back an Argo CD application", r"^argocd\s+app\s+(delete|rollback|terminate-op)\b"),
    ("deletes IBM Cloud resources", r"^(ibmcloud|ic)\s+.*\b(delete|rm|remove|purge|disable)\b"),
    ("destructive SQL (DROP/TRUNCATE/DELETE without WHERE)",
     r"^(psql|sqlplus|sql|sqlcl|mysql|mariadb|sqlcmd|db2|clickhouse-client)\b.*(\bdrop\s+(table|schema|database|user|index|view)\b|\btruncate\b|\bdelete\s+from\s+[\w.\"]+\s*(;|\"|'|$))"),
    ("publishes an artifact", r"^(npm|pnpm|yarn)\s+publish\b|^(mvn|\./mvnw)\b.*\bdeploy\b|^(gradle|\./gradlew)\b.*\bpublish"),
    ("pipes a downloaded script into a shell", r"^(curl|wget)\b.*\|\s*(sudo\s+)?(sh|bash|zsh|python3?)\b"),
    ("runs with elevated privileges", r"^sudo\b"),
    ("removes Docker data broadly", r"^docker\s+(system\s+prune|volume\s+(rm|prune))\b"),
]
STRICT_GIT = [("commits or pushes (strict mode)", r"^git\s+(commit|push)\b")]
SPLIT = re.compile(r"\s*(?:&&|\|\||;|\n)\s*")
DANGEROUS_RM_TARGETS = {"/", "/*", "~", "~/", "~/*", "$HOME", "${HOME}", "$HOME/", ".", "./", "..", "../", "*", "./*", "../*"}


def command_of(tool_input):
    if isinstance(tool_input, dict):
        for k in ("command", "cmd", "commandLine", "script"):
            if isinstance(tool_input.get(k), str):
                return tool_input[k], tool_input.get("cwd") or ""
        texts = [v for v in tool_input.values() if isinstance(v, str)]
        return (max(texts, key=len) if texts else ""), ""
    return (tool_input if isinstance(tool_input, str) else ""), ""


def rm_problem(part, cwd):
    try:
        words = shlex.split(part)
    except ValueError:
        words = part.split()
    if not words or words[0] not in ("rm", "sudo"):
        return None
    if words[0] == "sudo":
        words = words[1:]
        if not words or words[0] != "rm":
            return None
    flags = "".join(w.lstrip("-") for w in words[1:] if w.startswith("-") and not w.startswith("--")) + \
            " ".join(w for w in words[1:] if w.startswith("--"))
    recursive = "r" in flags.lower() or "recursive" in flags
    if not recursive:
        return None
    root = os.path.realpath(cwd or os.getcwd())
    for target in (w for w in words[1:] if not w.startswith("-")):
        if target in DANGEROUS_RM_TARGETS or target.startswith(("~", "$HOME", "${HOME}")):
            return f"recursive delete of '{target}'"
        resolved = os.path.realpath(os.path.join(root, os.path.expanduser(target)))
        if resolved != root and not resolved.startswith(root + os.sep):
            return f"recursive delete outside the project ('{target}')"
        if resolved == root:
            return "recursive delete of the whole project"
    return None


def main():
    event = json.load(sys.stdin)
    if event.get("hook_event_name") != "PreToolUse":
        return 0
    command, cwd = command_of(event.get("tool_input"))
    cwd = cwd or event.get("cwd") or ""
    if not command.strip():
        return 0
    rules = RULES + (STRICT_GIT if os.environ.get("BOBKIT_STRICT_GIT") == "1" else [])
    for part in (p.strip() for p in SPLIT.split(command) if p.strip()):
        part_no_env = re.sub(r"^(\w+=\S*\s+)+", "", part)          # FOO=bar cmd …
        problem = rm_problem(part_no_env, cwd)
        if not problem:
            for reason, rx in rules:
                if re.search(rx, part_no_env, re.I):
                    problem = reason
                    break
        if problem:
            sys.stderr.write(f"[bob-kit command-guard] Blocked: {problem}: `{part_no_env[:200]}`. "
                             "Run it yourself if it is really intended.\n")
            print(f"Blocked by command-guard ({problem}). Ask the user to run this command manually if it is intended.")
            return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail-open
        sys.stderr.write(f"[bob-kit command-guard] internal error, allowing: {exc}\n")
        sys.exit(0)
