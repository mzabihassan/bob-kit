# Code review

Review like a technical lead: find what would hurt in production or slow the team down, and say clearly what is fine. Judge against the project's conventions, not personal taste.

## Output

For each finding: **severity**, `file:line`, the problem, why it matters (concrete failure scenario), and the suggested fix. Separate blocking findings from suggestions. End with a short overall assessment (ready / ready with fixes / needs rework). If there is nothing significant, say so.

| Severity | Examples |
| --- | --- |
| **Blocker** | Wrong financial result, data loss or corruption, security vulnerability, broken contract or migration, build/test failure |
| **Major** | Race condition, transaction boundary error, missing error/timeout handling, N+1 on a hot path, missing tests for risky logic, sensitive data in logs |
| **Minor** | Maintainability issue, inconsistency with project conventions, weak test, unclear naming |
| **Nit** | Style the formatter does not catch; mention sparingly |

## What to look at, in order of value

1. **Behaviour**: does it do what the requirement says, including error and edge paths? Any unintended behaviour change in a refactor?
2. **Data integrity**: transaction boundaries, `@Transactional` pitfalls (self-invocation, checked exceptions, remote calls inside), locking and concurrency, idempotency, money handling (`BigDecimal`, rounding, currency).
3. **Security**: authorisation per object, input validation, injection, secrets, sensitive data in logs/responses, dependency risk.
4. **Compatibility**: API/JSON/DB/message/config changes and migration safety for rolling deployments.
5. **Resilience and performance**: timeouts, retries on non-idempotent calls, unbounded queries or collections, N+1, blocking calls in reactive code, resource leaks.
6. **Design**: fits the existing architecture and layering; no speculative abstraction; no duplicated business rule; complexity proportional to the problem.
7. **Tests**: cover the risky behaviour and edge cases, assert outcomes, are deterministic, use the right level (real DB for queries).
8. **Readability**: names reveal intent, methods are focused, comments explain *why*.

## Spring/JPA traps worth checking every time

`@Transactional` on private methods or called from the same class; `LazyInitializationException` hidden by open-in-view; `EAGER` `@ManyToOne`; collection fetch join with pagination; `equals/hashCode` on entities via Lombok `@Data`; field injection; `@Value` defaults hiding missing config; `catch (Exception e)` that swallows or logs and continues; `Optional.get()` without check; mutable static state; `new BigDecimal(double)`; `LocalDateTime.now()` without a clock in business logic; missing timeouts on HTTP clients.
