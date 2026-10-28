# Collecting the change set

## 1. The range

```bash
git fetch --tags origin
git describe --tags --abbrev=0 HEAD^            # previous release tag (or the tag before a given one)
python3 scripts/release_changes.py v1.3.0..HEAD [--repo <path>] [--json]   # scripts/ is relative to this skill's directory
```

The script groups commits by Conventional Commit type, lists breaking changes (`type!:` or `BREAKING CHANGE:`), MR references (`!123`, `group/project!123`, GitLab merge commits), the files in risky areas (migrations, configuration, dependencies, API contracts, security configuration, infrastructure, CI) and proposes a SemVer version when the base is a `vX.Y.Z` tag. If most commits are not conventional, it says so: classify from the MRs instead.

## 2. Merge requests and tickets

- For each referenced MR: `glab mr view <iid>` (or `GET /projects/:id/merge_requests/:iid`) for the title, the description, labels (e.g. `type::feature`, `breaking`), the linked issues and the approvals. Merged MRs not referenced in commits: `glab mr list --merged --target-branch <branch>` filtered by merge date, or the milestone.
- Tickets (GitLab issues, Jira): business purpose, acceptance criteria, the requesting team. They are the source for business release notes.
- An MR without a ticket or a description is an open point for the change request, not something to make up.

## 3. Details that drive risk and runbook

| Item | How to find it | What to capture |
| --- | --- | --- |
| Database migrations | `git diff --name-only A B -- ':(glob)**/db/migration/**' ':(glob)**/changelog/**'` | Each migration, whether it is expand-only or destructive, its locking impact and duration on production volumes, its order relative to the deployment |
| Configuration | Diffs of `application*.yml`, Helm values, ConfigMaps, feature-flag definitions | New, changed or removed properties per environment, secrets to create or rotate (names only) |
| Dependencies | Diffs of `pom.xml`, `build.gradle*`, `package.json` and lockfiles | Framework and runtime upgrades (Spring Boot, Java, Angular, Node), security fixes they bring |
| API and message contracts | OpenAPI specs, controllers, DTOs, Avro or Protobuf schemas | Breaking or additive changes, consumers to notify, versioning |
| Infrastructure and deployment | Dockerfile, Terraform, Helm, Kustomize, Argo CD | Resource changes, new services, network flows, IAM changes |
| Quality and security evidence | The release commit's pipeline: tests, SonarQube Quality Gate, Fortify, Nexus IQ, Sysdig | Status and links; open waivers with their expiry |
| Other teams and systems | MR descriptions, integration configs | Coordinated deployments, partner notifications, ordering constraints |

## 4. Version number

Follow the project's scheme. With SemVer: breaking change → major (minor while in `0.x`), new feature → minor, fixes only → patch. Date-based or sprint-based schemes are fine if they are the convention. A release candidate (`-rc.1`) is promoted to the final version without rebuilding the artifact.
