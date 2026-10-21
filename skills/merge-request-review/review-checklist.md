# Review checklist

Go through the areas the change touches, in this order of value. Skip what does not apply.

## 1. Behaviour

- Does the change do what the MR or issue says, including edge cases (empty, null, limits, duplicates, time zones, concurrency) and error paths?
- In a refactoring MR: is behaviour strictly unchanged? Mixed refactoring and behaviour changes are a finding on their own (hard to review and to revert).
- Are feature flags, configuration defaults and migrations consistent with the rollout plan?

## 2. Data integrity

- Transaction boundaries (`@Transactional` on the right layer, no remote calls inside transactions), concurrent updates (locking, `@Version`, conditional updates), idempotency of retried operations, duplicate prevention.
- Money and precision (`BigDecimal`, rounding, currency), dates and time zones.
- Database migrations: backward compatible with the version still running (expand → contract), lock impact on large tables, applied migrations never edited, rollback or forward-fix plan.

## 3. Security

- Input validation, injection (SQL, path, log, command), XSS (`innerHTML`, `dangerouslySetInnerHTML`, `bypassSecurityTrust*`), SSRF, deserialisation.
- Authorisation on every new endpoint or action, including object-level ownership; no security relaxations (CSRF, CORS, permit-all) without justification.
- Secrets, tokens or personal data committed, logged or returned to clients; new dependencies (licence, maintenance, known vulnerabilities).

## 4. Compatibility

Public APIs (paths, status codes, JSON fields and formats), messages and file formats, database schema, configuration property names, feature behaviour other teams rely on. Breaking changes need versioning or a migration path, and a mention in the MR.

## 5. Resilience and performance

Timeouts and retries on remote calls (retries only for idempotent operations), unbounded queries or collections, N+1 queries, missing pagination, heavy work on request threads or in UI render paths, memory or connection leaks, blocking calls in reactive code.

## 6. Tests

New behaviour and bug fixes are tested at the right level, assert outcomes rather than interactions, cover edge and error cases, are deterministic, and would fail without the change. No disabled or weakened tests, no lowered quality gates.

## 7. Operability

Meaningful logs (no sensitive data, correlation id), metrics and health checks for new components, configuration per environment, deployment manifests and CI changes consistent with the code change, documentation or runbooks updated when behaviour changes.

## 8. Design and conventions

Fits the existing architecture and layering; no speculative abstraction or duplicated business rules; names reveal intent; complexity proportional to the problem; follows `AGENTS.md`/rules, lint and formatting conventions. A deviation from the project's conventions without a reason is a finding even if the code is otherwise fine.

## Specialised checklists

When the corresponding skills are installed next to this one (same `skills/` directory), use their checklists for deeper reviews:

| Area | File |
| --- | --- |
| Java / Spring Boot / JPA | `../spring-boot-developer/code-review.md` (banking concerns: `../spring-boot-developer/banking.md`) |
| Angular | `../angular2-developer/review-checklist.md` |
| React | `../react-developer/review-checklist.md` |
| SQL, migrations, locking | `../sql-database-engineer/schema-migrations.md`, `../sql-database-engineer/concurrency-transactions.md` |
| Security-sensitive code | `../security-findings-remediation/fortify.md` (categories and real fixes) |
| `.gitlab-ci.yml` | `../gitlab-ci-engineer/security-governance.md` |
| Kubernetes / Argo CD manifests | `../argocd-gitops/workload-manifests.md` |
| Tests and coverage | `../sonarqube-java-angular/java-tests.md`, `../sonarqube-java-angular/angular-tests.md` |

If they are not installed, the sections above are sufficient.
