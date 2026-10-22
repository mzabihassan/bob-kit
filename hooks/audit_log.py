#!/usr/bin/env python3
"""bob-kit audit log (IBM Bob lifecycle hook, PostToolUse).

Appends one JSON line per tool call (UTC time, session, tool, files, command) to a local audit
file, for traceability of what the agent did. Tool outputs are not stored (they may contain data);
secrets in commands are redacted. Default location: ~/.bob/audit/<project>.jsonl
(override with BOBKIT_AUDIT_DIR). Never blocks: always exits 0.
"""
import datetime
import json
import os
import re
import sys

PATH_KEYS = ("path", "file_path", "filePath", "file", "target_file", "filename")
REDACT = [
    (re.compile(r"(?i)(authorization:\s*(?:bearer|basic)\s+)\S+"), r"\1***"),
    (re.compile(r"(?i)((?:password|passwd|pwd|token|secret|api[_-]?key)[=:]\s*)\S+"), r"\1***"),
    (re.compile(r"(?i)(\b(?:mysql|mariadb)\b.*?\s-p)(?!\s)\S+"), r"\1***"),          # mysql -pSECRET
    (re.compile(r"([a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s@/]+@"), r"\1***@"),           # scheme://user:pass@
    (re.compile(r"\b(gl(?:pat|dt|rt)-|gh[pousr]_|github_pat_|xox[abprs]-|ATATT3|AKIA|ASIA)[0-9A-Za-z_=-]+"), r"\1***"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_.-]+"), "eyJ***"),
]


def redact(text):
    for rx, repl in REDACT:
        text = rx.sub(repl, text)
    return text


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    cwd = event.get("cwd") or os.getcwd()
    record = {
        "time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "session": event.get("session_id"),
        "project": cwd,
        "tool": event.get("tool_name"),
        "path": next((tool_input[k] for k in PATH_KEYS if isinstance(tool_input.get(k), str)), None),
        "command": redact(tool_input["command"])[:500] if isinstance(tool_input.get("command"), str) else None,
        "response_chars": len(event.get("tool_response") or ""),
    }
    directory = os.environ.get("BOBKIT_AUDIT_DIR") or os.path.join(os.path.expanduser("~"), ".bob", "audit")
    os.makedirs(directory, exist_ok=True)
    name = re.sub(r"[^\w.-]+", "_", os.path.basename(os.path.normpath(cwd)) or "project")
    with open(os.path.join(directory, f"{name}.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({k: v for k, v in record.items() if v is not None}, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"[bob-kit audit-log] internal error: {exc}\n")
    sys.exit(0)
