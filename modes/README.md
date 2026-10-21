# bob-kit modes

Custom modes for IBM Bob, defined in [`custom_modes.yaml`](custom_modes.yaml). A mode sets Bob's role and the tool groups it may use; the bob-kit skills provide the know-how, so install the skills too.

| Mode | Purpose | Tool groups |
| --- | --- | --- |
| 🧭 `tech-lead-reviewer` | Reviews (MR, commit, branch, tag range, local changes), audits, impact analysis and estimates, without changing code | `read`, `edit` **only for review reports** (`reviews/*.md`, `docs/reviews/*.md`, `*REVIEW*.md`), `execute`, `mcp`, `skill`, `todo`, `mode` |
| 🛡️ `security-remediator` | Fixes Fortify, Nexus IQ, Sysdig and SonarQube security findings | `read`, `edit` **except** CI pipelines (`.gitlab-ci.yml`, `.gitlab/`, `.github/`, `Jenkinsfile`), scanner and policy configuration (`sonar-project.properties`, Fortify files) and `.bob/`, `execute`, `mcp`, `skill`, `todo` |

The `fileRegex` restrictions were tested with JavaScript regular expressions against allowed and denied example paths.

## Install

Project modes (shared with the team through git):

```bash
mkdir -p .bob && cp modes/custom_modes.yaml .bob/custom_modes.yaml   # or merge the entries into an existing file
```

Global modes: merge the entries into `~/.bob/settings/custom_modes.yaml` (Settings → Modes → Edit Global Modes). Project modes take precedence over global ones with the same slug. Optional per-mode rules can go in `.bob/rules-tech-lead-reviewer/` or `.bob/rules-security-remediator/` (files loaded alphabetically).

## Limiting commands

A mode can only allow or deny the whole `execute` group; it cannot restrict *which* commands run. Both modes need `execute` (to fetch MRs, build, test and scan), so their instructions ask for read-only or build-and-test commands only. To enforce it, use Bob's approval settings in `~/.bob/settings/settings.json`. They apply to **all modes**, so keep them compatible with your other work. For example:

```json
"approval": {
  "allowed_permissions": ["read", "skill", "todo", "mode"],
  "allowedExecutors": [{
    "toolId": "execute_command",
    "approvedCommands": ["git status", "git log", "git show", "git diff", "git fetch", "git worktree",
                         "glab mr view", "glab mr diff", "glab ci status", "./mvnw", "mvn", "./gradlew", "npm test", "npm ls"],
    "deniedCommands": ["git push", "git commit", "git merge", "git rebase", "git reset", "glab mr merge", "glab mr approve",
                       "kubectl delete", "kubectl apply", "argocd app sync", "rm -rf"]
  }]
}
```

Approved commands run without a prompt; anything else still asks for your approval; denied commands are always refused (denials take precedence). Check the current schema in the [approval settings docs](https://bob.ibm.com/docs/shell/configuration/approval-settings).
