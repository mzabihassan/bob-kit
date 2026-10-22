#!/usr/bin/env python3
"""bob-kit secret guard (IBM Bob lifecycle hook).

PreToolUse (file writes): blocks writing content that contains a secret.
UserPromptSubmit: blocks a prompt that contains a secret before it reaches the model.

Exit 2 = block (Bob's contract); exit 0 = allow. Any internal error exits 0 (fail-open)
so a broken hook never blocks Bob. Secret values are never printed, only their kind.
To allow a deliberate fake value (test fixture), add `bob-allow-secret` on the same line.
"""
import json
import os
import re
import sys

ALLOW_MARKER = "bob-allow-secret"
PLACEHOLDER = re.compile(r"^(\$\{.*\}|<.*>|\{\{.*\}\}|%\(.*\)s|changeme|change-me|xxx+|\*+|\.\.\.|example\w*|dummy\w*|"
                         r"test\w*|fake\w*|placeholder|secret|password|none|null|true|false|redacted)$", re.I)

# (kind, regex, applies to prompts too)
PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?-----"), True),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), True),
    ("GitLab token", re.compile(r"\bgl(?:pat|dt|rt|cbt|ptt|ft)-[0-9A-Za-z_-]{20,}"), True),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[0-9A-Za-z]{36,}|github_pat_[0-9A-Za-z_]{22,})"), True),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}"), True),
    ("Atlassian API token", re.compile(r"\bATATT3[0-9A-Za-z_=-]{30,}"), True),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), True),
    ("JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), True),
    ("IBM Cloud API key", re.compile(r"(?i)(?:ibm_?cloud|ibmcloud|iam)[\w.-]*api[_-]?key[\"']?\s*[:=]\s*[\"']?(?P<v>[A-Za-z0-9_-]{40,})"), True),
    ("credentials in URL", re.compile(r"\b[a-z][a-z0-9+.-]{1,20}://(?P<u>[^\s:/@'\"]{1,64}):(?P<v>[^\s@/'\"]{3,})@"), True),
]
# Generic "key = value" credentials: only in configuration-like files (too noisy in code and prompts)
GENERIC = re.compile(r"(?i)(?:^|[\s\"'{,])(?:[\w.-]*(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|client[_-]?secret|"
                     r"private[_-]?key|auth[_-]?token|token))[\"']?\s*[:=]\s*[\"']?(?P<v>[^\s\"'#,;]{8,})")
CONFIG_EXT = (".yml", ".yaml", ".properties", ".env", ".json", ".xml", ".conf", ".cfg", ".ini", ".toml", ".tfvars", ".tf",
              ".npmrc", ".pypirc", "settings.xml")
PATH_KEYS = ("path", "file_path", "filePath", "file", "target_file", "filename")


def strings(obj):
    """All string values of a JSON object (tool_input field names are not documented, so scan them all)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def find_path(tool_input):
    if isinstance(tool_input, dict):
        for k in PATH_KEYS:
            if isinstance(tool_input.get(k), str):
                return tool_input[k]
    return ""


def is_placeholder(value):
    v = value.strip().strip("\"'")
    return bool(PLACEHOLDER.match(v)) or v.startswith(("${", "$(", "%", "{{", "<")) or "${" in v


def scan(text, path, prompt):
    findings = []
    config_like = path.lower().endswith(CONFIG_EXT) or os.path.basename(path).lower().startswith(".env")
    for lineno, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARKER in line:
            continue
        for kind, rx, in_prompt in PATTERNS:
            if prompt and not in_prompt:
                continue
            for m in rx.finditer(line):
                value = m.groupdict().get("v") or m.group(0)
                if kind in ("IBM Cloud API key", "credentials in URL") and is_placeholder(value):
                    continue
                findings.append((kind, lineno))
        if config_like and not prompt:
            for m in GENERIC.finditer(line):
                if not is_placeholder(m.group("v")):
                    findings.append(("credential in configuration", lineno))
    return findings


def main():
    event = json.load(sys.stdin)
    name = event.get("hook_event_name", "")
    if name == "UserPromptSubmit":
        findings = scan(event.get("prompt") or "", "", prompt=True)
        where = "your prompt"
    elif name == "PreToolUse":
        tool_input = event.get("tool_input") or {}
        path = find_path(tool_input)
        findings = []
        for s in strings(tool_input):
            if s != path:
                findings.extend(scan(s, path, prompt=False))
        where = path or event.get("tool_name", "the tool input")
    else:
        return 0
    if not findings:
        return 0
    kinds = sorted({k for k, _ in findings})
    lines = sorted({n for _, n in findings})[:10]
    sys.stderr.write(f"[bob-kit secret-guard] Blocked: {', '.join(kinds)} detected in {where} (line(s) {lines}). "
                     f"Use an environment variable or a secret manager reference instead. If this is a deliberate fake "
                     f"value, add '{ALLOW_MARKER}' on that line.\n")
    print(f"Blocked by secret-guard: {', '.join(kinds)} in {where}. Remove the secret and use a placeholder or a "
          f"secret reference.")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail-open: a broken hook must never block Bob
        sys.stderr.write(f"[bob-kit secret-guard] internal error, allowing: {exc}\n")
        sys.exit(0)
