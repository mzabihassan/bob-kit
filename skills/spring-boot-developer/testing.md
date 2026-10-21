# Testing strategy

A test earns its place by catching a realistic regression or documenting a rule. Coverage is a by-product, not the goal. Follow the project's test conventions (naming, AssertJ vs Hamcrest, BDD style, fixtures, base classes) before your own.

## Choose the level by what can break

| Change | Primary tests |
| --- | --- |
| Business rule, calculation, state transition | Fast unit tests on the domain/service, parameterised over edge cases. No Spring context |
| Controller contract (validation, status codes, JSON shape, security) | `@WebMvcTest` (+ `@MockitoBean`/`@MockBean`) or MockMvc/`RestTestClient` per project |
| Repository query, mapping, constraint, transaction/locking behaviour | `@DataJpaTest` or `@SpringBootTest` on a **real database via Testcontainers** (H2 hides dialect, locking and constraint differences) |
| Integration with HTTP/MQ/Kafka | WireMock / Testcontainers (Kafka, IBM MQ, RabbitMQ), contract tests (Spring Cloud Contract, Pact) if the project uses them |
| Cross-cutting flow (payment end to end, batch job) | A few `@SpringBootTest` scenario tests covering happy path and key failures |
| Bug fix | First a test that reproduces the bug and fails, then the fix |

## Writing meaningful tests

- Name tests after behaviour (`rejectsTransferWhenBalanceIsInsufficient`), one reason to fail each, Arrange–Act–Assert.
- Edge cases worth covering: boundaries (0, limits, max scale), null/empty, duplicates, ordering, time (end of month, leap years, DST, time zones, cut-off), concurrency (two updates of the same aggregate), partial failure and retry.
- `@ParameterizedTest` (`@CsvSource`, `@MethodSource`) for rule tables; it makes business rules readable to reviewers.
- Mock only what you do not own or what is slow/non-deterministic (external systems, clock, random). Do not mock value objects, mappers or the class under test. Prefer fakes for repositories in pure unit tests when interactions get complex.
- Verify outcomes (returned values, persisted state, published messages) over interactions; use `verify` for side effects that are the actual requirement (an audit entry written, a message sent once).
- Inject `Clock` instead of calling `now()`; avoid `Thread.sleep` (Awaitility for async).
- Keep integration tests fast: reuse Testcontainers (singleton containers or `@ServiceConnection` on Boot 3.1+), avoid `@DirtiesContext`, limit distinct context configurations so Spring caches them.
- A flaky test is a defect: find the shared state, timing or ordering cause; do not retry it into green.

## SonarQube and coverage in existing projects

- Read the quality gate first (usually based on **new code**: coverage, duplications, reliability/security ratings, hotspots reviewed). Focus effort on the gate's actual conditions.
- Raising coverage on legacy code: prioritise by risk × change frequency (core business services, calculations, recently buggy classes), not by easiest lines. Characterisation tests on hot spots are worth more than getters/setters tests.
- Exclusions are legitimate for generated code, DTOs/config classes and `main` methods when agreed by the team; configure them in the build/Sonar properties, not by gaming tests.
- Fix issues by severity and real impact; mark false positives with a justification. Do not suppress rules wholesale.
- Optional, for critical logic: mutation testing (PIT) reveals tests that execute code without asserting on it.

## Regression risk analysis

For Standard and Significant changes, list in the report which behaviours could regress and which tests cover them; call out the untested ones explicitly.
