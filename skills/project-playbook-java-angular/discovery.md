# Discovery: from the scan to verified facts

The scan answers "what is there and where". Reading answers "how it works and why". Read to fill the facts each page needs (below), not to explore. A typical medium project needs 15–25 targeted reads in the main task; more means you are exploring.

## Reading order

1. The scan's **Read next** list, in order. Read entry points and configuration whole when short; otherwise read ranges.
2. Per page, the facts still missing (table below). Find them with `grep` (one query per fact, several queries in one turn), then read the matching ranges.
3. Stop when every planned section has its facts or a `TBD`.

| Page | Facts to establish | Where they usually are |
| --- | --- | --- |
| Home | What the system does in two sentences, users, main capabilities, owners | README intro, `spring.application.name`, route names, entity names, `CODEOWNERS` |
| Quick start | Tool versions, required services (DB, broker, IdP), env vars, run and test commands, local URLs and ports, seed data, default dev credentials *process* | Scan tables, `.nvmrc`, wrappers, compose files, `application-dev*`, `proxy.conf*`, npm scripts, README "Development" |
| Product and domain | Key workflows end to end, domain terms, business rules that shape the code | Controllers + services of the main entities, route list, enums/status fields, validation annotations, README, ADRs |
| Architecture | Style (layered, hexagonal, package-by-feature), module responsibilities, frontend structure and state, FE↔BE contract (base URL, proxy, auth header, error format, CORS), persistence and migrations, integrations, security model, cross-cutting (validation, transactions, caching, i18n) | Package tree, security config, `@ControllerAdvice`, interceptors, `app.config.ts`/`app.module.ts`, `environment*.ts`, migrations, clients/listeners |
| APIs and integrations | Endpoint groups and conventions (versioning, pagination, errors), OpenAPI location and UI URL, outbound systems with protocol and config key, messaging topics/queues | Scan endpoint table, OpenAPI spec, springdoc config, `*Client`/Feign, listeners, `application*.yml` integration keys |
| Codebase guide | Annotated tree, entry points, core services, "where to change what" | Scan modules and package tree, two or three representative files per layer |
| Development workflow | Branching, commit and MR rules, code style tooling, test pyramid and commands, coverage gates, architectural rules (ArchUnit, lint boundaries), how to add an endpoint / screen / migration | `CONTRIBUTING`, `AGENTS.md`, MR templates, git conventions in the scan, lint/format configs, `pom.xml` plugins, ArchUnit tests, one recent feature's files |
| CI/CD and environments | Pipeline stages and gates, artifacts and registry, deployment path (GitOps, Helm, manual), environments and their differences, promotion and rollback | CI file(s) and includes, Dockerfile/Jib, Helm values per env, overlays, Argo CD apps, profile files |
| Operations | Health and readiness endpoints, metrics, logs format and where to see them, tracing, alerting, scheduled jobs, runbook links | Actuator config, logback config, micrometer deps, `@Scheduled`, existing runbooks |
| Troubleshooting | Problems already met and their fix | README "troubleshooting/FAQ", quick-start verification failures, comments like "workaround", known-issue docs |

## Verification

- **Read** facts are verified by the file you cite; cite the line for behaviour (`SecurityConfiguration.java:58`).
- **Commands**: run them only if the user allowed it in the framing step and the toolchain is present. Keep output out of the context:
  `./mvnw -q -DskipTests package > /tmp/pb-build.log 2>&1; echo "exit=$?"; tail -n 20 /tmp/pb-build.log`
  Same pattern for `npm ci`, `npm run build`, unit tests. Never start long-lived servers you cannot stop, never call shared environments, never use real credentials. A command you did not run is labelled *not verified*.
- **Documented** facts (README, wiki) that the code contradicts: the code wins; record the discrepancy as a finding for the team.
- **Inferred** facts (naming, structure) carry the *Inferred* label and, where it matters, a `TBD` to confirm.

## Project shapes

- **Monorepo** (JHipster-style `src/main/webapp`, or `backend/` + `frontend/`): one scan; Quick start covers both, and whether the Maven build also builds the frontend (frontend-maven-plugin).
- **Separate repositories**: scan them together (`project_scan.py ../api ../ui`); paths are prefixed with the repository label; the playbook covers both, and `--source-url label=URL` links each. If one repository is not available, say so and mark its facts `TBD`.
- **API-first** (OpenAPI Generator): controllers implement generated interfaces; the spec is the endpoint reference, generated code lives under `target/`: explain the regenerate step.
- **Multi-module Maven / Gradle, Nx workspaces**: document modules and their dependency direction; the "where to change what" table becomes per module.
- **NgModule vs standalone, zone vs zoneless**: state what the project uses (from the scan), not what Angular recommends.
- **Pipelines or deployment in another repository** (central CI templates, GitOps repo): document the link and what the project controls; mark the rest `TBD`.

## Subagent brief (large projects)

One `spawn_subagent` per area, in parallel when possible. Each brief is self-contained:

```
Read-only task. Do not modify any file.
Repository: <path>. Project map: <tmp>/playbook-scan/scan.md (read only its "<Backend|Frontend|CI/CD…>" sections first).
Goal: establish the facts below for a developer onboarding playbook. For each fact give the evidence as `path:line`
and a label: verified (read in code/config) or inferred (deduced from names/structure); list what you could not find.
Facts: <the rows of the discovery table for this area, adapted to the project>.
Read narrowly: grep/glob first, then ranges; do not read generated code, lockfiles or tests beyond one example per kind.
Return at most 80 lines of Markdown: facts grouped by topic, no file contents, no code excerpt longer than 5 lines,
never any secret value (name the key and the location instead).
```

Merge the returned facts sheets; read a cited range yourself only when a fact is surprising or central (security, data, money flows).
