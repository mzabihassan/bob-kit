#!/usr/bin/env python3
"""bob-kit "done" notification (IBM Bob lifecycle hook, Stop).

Shows a desktop notification when Bob finishes, so you can switch tasks during long runs.
macOS (osascript), Linux (notify-send) and Windows (PowerShell toast via BurntToast if installed,
otherwise nothing). The message never includes the assistant's text. Always exits 0.
"""
import json
import os
import shutil
import subprocess
import sys


def main():
    event = json.load(sys.stdin)
    project = os.path.basename(os.path.normpath(event.get("cwd") or os.getcwd())) or "project"
    title, message = "IBM Bob", f"Task finished in {project}"
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    elif sys.platform.startswith("linux") and shutil.which("notify-send"):
        subprocess.run(["notify-send", title, message], capture_output=True, timeout=5)
    elif sys.platform == "win32" and shutil.which("powershell"):
        cmd = f"if (Get-Module -ListAvailable BurntToast) {{ New-BurntToastNotification -Text '{title}','{message}' }}"
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=8)
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"[bob-kit notify-done] {exc}\n")
    sys.exit(0)
