# bob-kit — IBM Bob skills & modes

A collection of reusable **skills** and custom **modes** for [IBM Bob](https://www.ibm.com/products/bob).

## Layout

```
skills/          # one folder per skill, each with a SKILL.md entry point
  angular2-developer/
  spring-boot-developer/
  sonarqube-java-angular/
  security-findings-remediation/
  gitlab-ci-engineer/
  sql-database-engineer/
modes/           # custom Bob modes (coming soon)
```

## Skills

| Skill | Description |
|-------|-------------|
| [angular2-developer](skills/angular2-developer/SKILL.md) | Build, review, debug and migrate Angular applications (v18 → latest). Reads the project's `AGENTS.md`, rules, lint config and existing code first and follows their conventions. Loads one supporting file per task to keep token use low, and never commits unless asked. |
| [spring-boot-developer](skills/spring-boot-developer/SKILL.md) | Senior/Staff Java 17–21 and Spring Boot engineer for enterprise and banking systems: features, bug fixes, safe refactoring of legacy code, architecture and code review, JUnit 5/Mockito/Testcontainers testing, SonarQube quality, JPA/SQL performance and version migrations. Adapts rigour to the task, follows the project's conventions, never commits unless asked, and ends with a prioritised technical report. |
| [sonarqube-java-angular](skills/sonarqube-java-angular/SKILL.md) | Improves SonarQube results on Java/Spring Boot and Angular projects with the best impact/effort ratio: Quality Gate and real security/reliability risks first, then quick coverage wins found by `scripts/coverage_hotspots.py` (JaCoCo/LCOV ranking), safe minimal issue fixes and hotspot reviews, measured before and after. No metric gaming. |
| [security-findings-remediation](skills/security-findings-remediation/SKILL.md) | Triage and fix Fortify (SAST), Nexus IQ (dependencies, licences) and Sysdig (images, posture, runtime) findings: release-gate blockers and exploitable issues first, mass fixes through dependency/base-image upgrades, minimal code fixes, justified waivers for the security team, and rescan evidence. Never games the scanner. |
| [gitlab-ci-engineer](skills/gitlab-ci-engineer/SKILL.md) | Diagnose failing GitLab pipelines from the job logs and write or improve `.gitlab-ci.yml` for Java/Spring Boot, Angular/React and container projects: rules, DAG, caches, artifacts, templates/components, security stages and GitOps promotion to Argo CD. Respects central templates and governance; never bypasses gates or leaks secrets. |
| [sql-database-engineer](skills/sql-database-engineer/SKILL.md) | Oracle and PostgreSQL for enterprise Java apps: plan-based query tuning and indexing, zero-downtime Flyway/Liquibase migrations, locking/deadlock/isolation issues, SQL and PL/SQL/PL/pgSQL, and Oracle to PostgreSQL migration with the semantic traps that silently change results. Read-only on shared databases unless asked. |

## Usage

Copy a skill folder into your project's `.bob/skills/` directory (or your global Bob skills directory):

```bash
cp -R skills/angular2-developer /path/to/project/.bob/skills/
```
