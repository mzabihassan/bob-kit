# Java & Spring practices

Defaults for new code. The project's established conventions win; verify version-sensitive APIs (Context7 or official docs) against the versions in the build file.

## Modern Java, used when it helps

| Feature | Since | Use it for |
| --- | --- | --- |
| Records | 16 | DTOs, value objects, command/query objects, projections. Not JPA entities |
| Sealed types + pattern matching `switch` | 17 / 21 | Closed domain alternatives (payment outcome, event types) with exhaustive handling instead of `instanceof` chains or enums carrying logic |
| Text blocks | 15 | SQL, JSON fixtures in tests |
| `var` | 10 | Local variables whose type is obvious from the right-hand side; not where it hides meaning |
| Sequenced collections (`getFirst`, `reversed`) | 21 | Ordered collections |
| Virtual threads | 21 (Boot 3.2+: `spring.threads.virtual.enabled`) | Blocking I/O-heavy workloads. Check pinning (`synchronized` around blocking calls before Java 24), connection-pool sizing and `ThreadLocal`-heavy libraries first |

Prefer immutability, `Optional` only as a return type, streams when they read better than loops (not for side effects), and `java.time` for all dates (never `Date`/`Calendar` in new code).

## Spring

- Constructor injection with `final` fields; no field injection. One public constructor needs no `@Autowired`.
- Typed configuration via `@ConfigurationProperties` (records + `@Validated`) instead of scattered `@Value`. Profiles for environments; no environment URLs in code.
- Keep controllers thin (mapping, validation, status codes), business rules in services or the domain, persistence in repositories. Follow the project's style (layered, hexagonal ports/adapters) rather than introducing a new one.
- `@Transactional` belongs on the service/use-case boundary. Remember: it is proxy-based (self-invocation and private methods are not transactional), it rolls back only on unchecked exceptions by default (`rollbackFor` for checked), `readOnly = true` for queries. Never make remote calls (HTTP, MQ publish) inside a DB transaction unless you have an outbox or accept the inconsistency explicitly.
- HTTP clients (`RestClient` Boot 3.2+, `WebClient`, `RestTemplate` in older code): always set connect and read timeouts. Retry only idempotent operations, with backoff and a limit (Resilience4j or Spring Retry, following the project).
- `@Async`/scheduling: configure a bounded executor; propagate MDC/security context deliberately. Scheduled jobs in multi-instance deployments need a lock (ShedLock or equivalent).

## Persistence (JPA/Hibernate, SQL)

- Make `@ManyToOne`/`@OneToOne` `LAZY` (they are eager by default). Set `spring.jpa.open-in-view=false` in new projects; in existing ones, know whether it is on before reasoning about lazy loading.
- Detect and fix N+1 with fetch joins, `@EntityGraph` or DTO projections. Read-only screens and reports: DTO/interface projections or plain SQL, not entity graphs.
- Pagination with collection fetch joins paginates in memory (Hibernate warns `HHH000104` in 5.x, `HHH90003004` in 6.x): fetch ids first, then entities.
- Entities: `equals`/`hashCode` based on a stable business key or id-with-care, no Lombok `@Data`; `@Version` for optimistic locking on concurrently updated aggregates.
- Batch writes: `hibernate.jdbc.batch_size`, `order_inserts/updates`; `IDENTITY` generation disables insert batching (sequences do not). Bulk JPQL updates bypass the persistence context: clear or avoid stale entities afterwards.
- Schema changes only through the project's migration tool (Flyway/Liquibase), backward compatible with the running version (expand → migrate → contract). Never `ddl-auto=update` outside local dev.
- Performance work starts from evidence: SQL logs/statistics, `EXPLAIN` plans, slow-query logs, missing indexes on foreign keys and filter columns.

## REST APIs

- Resource-oriented URLs, correct status codes, `ProblemDetail` (RFC 9457, Boot 3) or the project's existing error format, consistently via `@RestControllerAdvice`. Never leak stack traces or internal identifiers.
- Bean Validation on request DTOs (`@Valid`); domain invariants still enforced in the domain.
- Evolve contracts compatibly: add optional fields, never rename/remove without versioning and a deprecation path; consumers should be tolerant readers. Keep the OpenAPI spec in sync (contract-first if the project is).
- Pagination for collections; idempotency keys for non-idempotent operations clients may retry (see `banking.md`).

## Security

- Spring Security 6: `SecurityFilterChain` beans with the lambda DSL (`WebSecurityConfigurerAdapter` is gone). Deny by default; method security (`@PreAuthorize`) for business-level authorisation; check object ownership, not just roles (IDOR).
- OAuth2 resource server/JWT validation per project standards; CSRF on for browser sessions; explicit CORS.
- Parameterised queries only; validate and size-limit uploads; encode output. Secrets from a vault or environment, never in `application.yml` committed to git.
- Keep dependencies patched (OWASP dependency-check, Dependabot/Renovate, Sonar security hotspots).

## Observability and errors

- SLF4J with parameters (`log.info("Paid {}", id)`), correct levels, one log per failure (log or rethrow, not both). Correlation id in MDC propagated across calls and async boundaries.
- Micrometer metrics for business-relevant events; Actuator endpoints restricted in production; health checks that reflect real dependencies.
- Exceptions: domain-specific types where callers react differently; never swallow; preserve the cause; translate at boundaries.

## Design patterns, with judgment

Use a pattern when its problem is present: Strategy for interchangeable rules selected at runtime, Template Method/composition for shared workflows with varying steps, Adapter/Anti-corruption layer for external or legacy systems, Factory when construction logic is genuinely complex, State for real state machines (payment lifecycle). A single implementation behind an interface, a builder for a three-field object or a "manager" class that only delegates are smells, not patterns.

## Build and delivery

- Use the wrapper (`mvnw`/`gradlew`) and the Spring Boot BOM / platform; no hand-pinned versions of managed dependencies without a reason.
- Respect enforcer/convergence, formatting (Spotless/Checkstyle) and ArchUnit rules already in the build.
- Containers: layered jars or buildpacks, non-root user, JVM memory sized to container limits, graceful shutdown (`server.shutdown=graceful`).
