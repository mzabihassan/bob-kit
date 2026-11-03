#!/usr/bin/env python3
"""Security regression tests of the bob-kit scripts and hooks against hostile repositories.

The skills read repositories that may be untrusted (a supplier's code, a fresh clone). Each case
replays an attack and checks it has no effect:
- a repository whose .git/config sets core.fsmonitor to a command: git must not run it
  (scripts and hooks call git with command-line overrides);
- symbolic links pointing outside the analysed tree: their targets must not be read;
- javascript:/data:/vbscript: URLs in Markdown pages, in any case or HTML-encoded: the Confluence preview
  must not keep them.

Run from the repository root:  python3 tools/test_security.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")
MARKER_TEXT = "outside-the-repo.intranet"  # appears only in files outside the analysed trees


def run(args, **kw):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=120, **kw)


def git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True)


def trapped_repo(base):
    """A repository whose own config runs a command on `git status`, plus symbolic links to outside files."""
    repo, outside = os.path.join(base, "evil"), os.path.join(base, "outside")
    os.makedirs(os.path.join(repo, "src/main/resources"))
    os.makedirs(os.path.join(repo, "src/main/resources/db/migration"))
    os.makedirs(os.path.join(repo, "styles"))
    os.makedirs(outside)
    with open(os.path.join(outside, "target.properties"), "w") as fh:
        fh.write(f"spring.datasource.url=jdbc:postgresql://{MARKER_TEXT}:5432/x\nserver.port=4242\n")
    with open(os.path.join(outside, "pom.xml"), "w") as fh:
        fh.write("<project><parent><artifactId>spring-boot-starter-parent</artifactId><version>9.9.9</version></parent></project>")
    with open(os.path.join(outside, "theme.css"), "w") as fh:
        fh.write(".x { color: #123456; }\n")
    with open(os.path.join(repo, "src/main/resources/db/migration/V1__init.sql"), "w") as fh:
        fh.write("create table t (id int);\n")
    with open(os.path.join(repo, "a.txt"), "w") as fh:
        fh.write("x\n")
    subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True, capture_output=True)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    hook = os.path.join(base, "fsmonitor.sh")
    with open(hook, "w") as fh:
        fh.write(f"#!/bin/sh\ntouch {base}/PWNED-$$\necho\n")
    os.chmod(hook, 0o755)
    git(repo, "config", "core.fsmonitor", hook)
    os.symlink(os.path.join(outside, "target.properties"), os.path.join(repo, "src/main/resources/application.properties"))
    os.symlink(os.path.join(outside, "pom.xml"), os.path.join(repo, "pom.xml"))
    os.symlink(os.path.join(outside, "theme.css"), os.path.join(repo, "styles/theme.css"))
    with open(os.path.join(repo, "styles/own.css"), "w") as fh:
        fh.write(".y { color: #abcdef; }\n")
    return repo


def pwned(base):
    found = [f for f in os.listdir(base) if f.startswith("PWNED-")]
    for f in found:
        os.remove(os.path.join(base, f))
    return bool(found)


def main():
    checks, failed = 0, []

    def expect(cond, label):
        nonlocal checks
        checks += 1
        if not cond:
            failed.append(label)

    base = tempfile.mkdtemp(prefix="bobkit-sec-")
    try:
        repo = trapped_repo(base)
        out = os.path.join(base, "audit")
        r = run([os.path.join(SK, "cloud-migration-audit-java-angular/scripts/audit.py"), "discover", f"--repo=evil={repo}", "--out", out])
        expect(r.returncode == 0, f"cloud audit discover runs on a hostile repo: {r.stderr[-200:]}")
        expect(not pwned(base), "cloud audit discover: repository fsmonitor command not executed")
        inv = open(os.path.join(out, "work", "inventory.json")).read()
        expect(MARKER_TEXT not in inv and "4242" not in inv and "9.9.9" not in inv, "cloud audit discover: symbolic links out of the repo not read")
        expect(json.loads(inv)["repos"][0]["head"] is not None, "cloud audit discover: git state still read")

        r = run([os.path.join(SK, "project-playbook-java-angular/scripts/project_scan.py"), repo])
        expect(r.returncode == 0 and not pwned(base), "project_scan: fsmonitor command not executed")
        expect(MARKER_TEXT not in r.stdout and "4242" not in r.stdout and "9.9.9" not in r.stdout, "project_scan: symbolic links out of the repo not read")

        r = run([os.path.join(SK, "release-change-management/scripts/release_changes.py"), "HEAD..HEAD", "--repo", repo])
        expect(r.returncode == 0 and not pwned(base), f"release_changes: fsmonitor command not executed: {r.stderr[-200:]}")

        css_out = os.path.join(base, "ds")
        r = run([os.path.join(SK, "design-system/scripts/extract_design_tokens.py"), os.path.join(repo, "styles"), "--out", css_out])
        extracted = open(os.path.join(css_out, "extracted.json")).read() if r.returncode == 0 else ""
        expect("#abcdef" in extracted and "#123456" not in extracted, "extract_design_tokens: symbolic link out of the tree not read")

        sys.path.insert(0, os.path.join(SK, "sonarqube-java-angular/scripts"))
        os.symlink(os.path.join(base, "outside", "pom.xml"), os.path.join(repo, "Leak.java"))
        with open(os.path.join(repo, "Own.java"), "w") as fh:
            fh.write("class Own {}\n")
        import coverage_hotspots  # noqa: E402
        idx = coverage_hotspots.index_sources([repo])
        expect("Own.java" in idx and "Leak.java" not in idx, "coverage_hotspots: symbolic link out of the tree not indexed")

        event = json.dumps({"hook_event_name": "SessionStart", "cwd": repo})
        r = run([os.path.join(ROOT, "hooks/project_context.py")], input=event)
        expect(r.returncode == 0 and not pwned(base), "project_context hook: fsmonitor command not executed")
        expect("9.9.9" not in r.stdout, "project_context hook: symbolic link out of the repo not read")
        expect("Git: branch main" in r.stdout, "project_context hook: git state still read")

        event = json.dumps({"hook_event_name": "PreToolUse", "cwd": repo, "tool_name": "write_file",
                            "tool_input": {"path": "src/main/resources/db/migration/V1__init.sql", "content": "x"}})
        r = run([os.path.join(ROOT, "hooks/migration_guard.py")], input=event)
        expect(r.returncode == 2 and not pwned(base), "migration_guard hook: still blocks, fsmonitor command not executed")

        pages = os.path.join(base, "pages")
        os.makedirs(pages)
        with open(os.path.join(pages, "00-home.md"), "w") as fh:
            fh.write("---\ntitle: Home\n---\n# Home\n[a](javascript:alert(1)) [b](data:text/html,x) [c](JaVaScRiPt:alert(2)) "
                     "![i](javascript:alert(3)) [e](&#106;avascript:alert(4)) [v](vbscript:x) [ok](https://example.com/x) "
                     "[rel](docs/x.md) `a/b.java`\n")
        os.symlink(os.path.join(base, "outside", "target.properties"), os.path.join(pages, "01-leak.md"))
        r = run([os.path.join(SK, "project-playbook-java-angular/scripts/confluence_export.py"), pages, "--out", os.path.join(base, "conf"),
                 "--source-url", "https://git.example.com/app/blob/abc"])
        page = open(os.path.join(base, "conf", "playbook.html")).read() if r.returncode == 0 else ""
        low = page.lower()
        expect(page and "javascript:" not in low and "data:text/html" not in low, "confluence_export: javascript:/data: URLs removed")
        markup = re.sub(r"(?s)<script.*?</script>", "", page)  # the preview's own script builds image sources
        hrefs = re.findall(r'(?:href|src)="([^"]*)"', markup)
        expect(page and all(re.match(r"(https?:|mailto:|#)", h) for h in hrefs),
               f"confluence_export: only http(s), mailto and anchor links, whatever the case or HTML encoding: {hrefs}")
        expect('href="https://example.com/x"' in page and 'href="https://git.example.com/app/blob/abc/docs/x.md"' in page,
               "confluence_export: web links and repository file links kept")
        expect(MARKER_TEXT not in page, "confluence_export: page symlinked from outside the folder not read")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    for f in failed:
        print(f"FAIL {f}")
    print(f"{checks - len(failed)}/{checks} security checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
