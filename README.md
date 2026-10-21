# bob-kit — IBM Bob skills & modes

A collection of reusable **skills** and custom **modes** for [IBM Bob](https://www.ibm.com/products/bob).

## Layout

```
skills/          # one folder per skill, each with a SKILL.md entry point
  angular2-developer/
  react-developer/
  spring-boot-developer/
  sonarqube-java-angular/
  security-findings-remediation/
  gitlab-ci-engineer/
  sql-database-engineer/
  argocd-gitops/
  ibm-cloud-platform/
  merge-request-review/
  criticize-me/
  release-change-management/
  production-incident-investigation/
modes/           # custom Bob modes (custom_modes.yaml)
```

## Skills

| Skill | Description |
|-------|-------------|
| [angular2-developer](skills/angular2-developer/SKILL.md) | Build, review, debug and migrate Angular applications (v18 → latest). Reads the project's `AGENTS.md`, rules, lint config and existing code first and follows their conventions. Loads one supporting file per task to keep token use low, and never commits unless asked. |
| [react-developer](skills/react-developer/SKILL.md) | Build, review, debug, test and migrate React 18 → latest (Vite, Next.js, React Router) with TypeScript. Reads the project's rules, lint config and existing code first; version-aware (React 19.x APIs, React Compiler, removed APIs); one supporting file per task; never commits unless asked. |
| [spring-boot-developer](skills/spring-boot-developer/SKILL.md) | Senior/Staff Java 17–21 and Spring Boot engineer for enterprise and banking systems: features, bug fixes, safe refactoring of legacy code, architecture and code review, JUnit 5/Mockito/Testcontainers testing, SonarQube quality, JPA/SQL performance and version migrations. Adapts rigour to the task, follows the project's conventions, never commits unless asked, and ends with a prioritised technical report. |
| [sonarqube-java-angular](skills/sonarqube-java-angular/SKILL.md) | Improves SonarQube results on Java/Spring Boot and Angular projects with the best impact/effort ratio: Quality Gate and real security/reliability risks first, then quick coverage wins found by `scripts/coverage_hotspots.py` (JaCoCo/LCOV ranking), safe minimal issue fixes and hotspot reviews, measured before and after. No metric gaming. |
| [security-findings-remediation](skills/security-findings-remediation/SKILL.md) | Triage and fix Fortify (SAST), Nexus IQ (dependencies, licences) and Sysdig (images, posture, runtime) findings: release-gate blockers and exploitable issues first, mass fixes through dependency/base-image upgrades, minimal code fixes, justified waivers for the security team, and rescan evidence. Never games the scanner. |
| [gitlab-ci-engineer](skills/gitlab-ci-engineer/SKILL.md) | Diagnose failing GitLab pipelines from the job logs and write or improve `.gitlab-ci.yml` for Java/Spring Boot, Angular/React and container projects: rules, DAG, caches, artifacts, templates/components, security stages and GitOps promotion to Argo CD. Respects central templates and governance; never bypasses gates or leaks secrets. |
| [sql-database-engineer](skills/sql-database-engineer/SKILL.md) | Oracle and PostgreSQL for enterprise Java apps: plan-based query tuning and indexing, zero-downtime Flyway/Liquibase migrations, locking/deadlock/isolation issues, SQL and PL/SQL/PL/pgSQL, and Oracle to PostgreSQL migration with the semantic traps that silently change results. Read-only on shared databases unless asked. |
| [argocd-gitops](skills/argocd-gitops/SKILL.md) | Argo CD on Kubernetes/OpenShift: diagnose OutOfSync, sync failures, Degraded/Progressing apps; write Applications, ApplicationSets, Helm values and Kustomize overlays; promote the same artifact between environments and roll back with `git revert`. Spring Boot and Angular workload practices. Changes Git, not the cluster; read-only cluster access unless asked. |
| [ibm-cloud-platform](skills/ibm-cloud-platform/SKILL.md) | IBM Cloud for enterprise Java/Angular apps: OpenShift/IKS, Code Engine, Registry, Databases for PostgreSQL, COS, Secrets Manager, Key Protect/HPCS, Event Streams, VPC, IAM, trusted profiles, context-based restrictions, Cloud Logs and Monitoring, via the ibmcloud CLI, Terraform and Schematics. Infrastructure as code first, least privilege, private by default, read-only unless asked. |
| [merge-request-review](skills/merge-request-review/SKILL.md) | Technical-lead review of a GitLab MR (URL or `!id`), a commit, a range or compare URL, a tag or release range, a branch, or local uncommitted changes. Severity-ranked findings with failure scenarios and fixes, verified in an isolated worktree when useful; reuses the other skills' checklists; posts to GitLab only when asked. |
| [criticize-me](skills/criticize-me/SKILL.md) | Ruthless, logical self-critique of exactly one commit (required: SHA, `HEAD~n`, tag or commit URL). Attacks the approach, correctness, tests and the commit itself; every finding has evidence, a consequence and a confidence level; no softening, no invented problems; read-only and never posted anywhere. |
| [release-change-management](skills/release-change-management/SKILL.md) | Release notes (business and technical), changelog, version proposal, ITIL/ServiceNow change request with impact, risk and backout plan, deployment runbook, go/no-go and post-implementation review, built from the real change set with `scripts/release_changes.py` (git range → grouped changes, MRs, breaking changes, risky files). Prepares; never submits or tags unless asked. |
| [production-incident-investigation](skills/production-incident-investigation/SKILL.md) | On-call support for production incidents on Java/Spring Boot, Angular/React, Kubernetes/OpenShift, Oracle/PostgreSQL and IBM Cloud: mitigate first, find what changed, test hypotheses against metrics, logs, traces and JVM/database evidence, propose safe mitigations, keep a UTC timeline, draft status updates and a blameless post-mortem. Read-only in production unless the incident commander approves. |

## Modes

| Mode | Description |
|------|-------------|
| [tech-lead-reviewer](modes/README.md) | Reviews, audits and estimates without changing code; may only write review reports. |
| [security-remediator](modes/README.md) | Fixes security scanner findings; cannot edit CI pipelines, scanner or policy configuration. |

See [modes/README.md](modes/README.md) for installation and recommended approval settings.

## Usage

Copy a skill folder into your project's `.bob/skills/` directory (or your global Bob skills directory):

```bash
cp -R skills/angular2-developer /path/to/project/.bob/skills/
```
