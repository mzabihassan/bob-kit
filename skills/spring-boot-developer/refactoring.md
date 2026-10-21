# Refactoring and legacy code

Goal: make the code easier to change **without changing what it does**. A refactor that alters behaviour is a bug, even if the new behaviour looks better — that is a separate, explicit change.

## 1. Understand before touching

- Read the code path end to end, including what Spring wires implicitly: proxies (`@Transactional`, `@Cacheable`, `@Async`), AOP aspects, event listeners, `@Scheduled` jobs, conditional beans and profiles.
- Find every caller: IDE/grep for usages, but also reflection, SpEL, JSON/XML mapping by name, Spring bean names and qualifiers, native queries, messaging consumers and other services calling the API.
- Use history: `git log -p`/`blame` on the area often explains odd code (a production incident, a regulator request, a client-specific rule). Odd-looking code that encodes a business rule stays until someone confirms it is obsolete.
- Identify what is observable from outside: API responses, DB writes, messages published, files produced, logs/metrics others alert on, timing (cut-offs, batch windows).

## 2. Secure the behaviour

- If tests are weak, write characterisation tests first: capture current outputs for representative and edge inputs (including the "wrong-looking" ones), at the level that is cheapest to observe (service, controller slice, or approval/snapshot of a generated file).
- For high-risk areas, consider a parallel run or comparing old and new implementation outputs on recorded production-like data.

## 3. Change in small, green steps

- One refactoring move at a time; compile and run tests after each. Keep refactoring and behaviour changes in separate commits (suggested to the user, never committed without being asked).
- Useful moves: extract method/class around a named concept, guard clauses instead of nested `if`, introduce a parameter or value object for data clumps (amount + currency, period), replace boolean flag arguments with explicit methods, split a god service by use case, move logic next to the data it uses, replace a conditional with polymorphism **only** when variants are many or growing.
- Complex business logic: make the rules visible first (name intermediate results, tabulate decision logic, extract pure functions), then simplify. Pure functions are easy to test exhaustively.

## 4. Backward compatibility checklist

Before finishing, confirm nothing changed unintentionally in:
- REST/SOAP contracts: paths, status codes, JSON field names and formats (Jackson naming, date formats, null vs absent), error payloads.
- Database: column names/types, constraints, sequence usage, transaction boundaries, locking behaviour.
- Messages and files: schemas, field order in fixed-width/CSV formats, encodings, topic/queue names.
- Configuration: property names (use `@DeprecatedConfigurationProperty` or keep aliases), bean names used by other modules, profiles.
- Serialized state: objects in caches, HTTP sessions or queues read by the previous version during rolling deployment.

## 5. Smells worth fixing — and when to leave them

| Smell | Fix when | Leave when |
| --- | --- | --- |
| Long method / god class | You need to change it, or it causes frequent bugs/conflicts | Stable, rarely touched, well tested |
| Duplicated logic | The copies must stay in sync (same business rule) | Similar-looking code that evolves independently |
| Deep inheritance, "Base*" utilities | It blocks testing or forces unrelated behaviour | Shallow and cohesive |
| Interface with one implementation | Nothing depends on the abstraction | It is a real boundary (port, external system, test double needed) |
| Anemic domain + transaction-script services | Rules are scattered and duplicated | Simple CRUD; the project consistently uses this style |
| Primitive obsession (amount as `BigDecimal`, ids as `String`) | Mix-ups are plausible (currency, account vs customer id) | Purely technical code |
| Static helpers / singletons | They hide I/O or state and block testing | Pure, stateless functions |

## 6. Legacy and larger restructurings

- Introduce seams (constructor injection, extracted interface at the boundary, adapter around a static or external call) to get code under test.
- Strangler fig or branch-by-abstraction for replacing a component; feature toggles to switch progressively and roll back without redeploying.
- When proposing an architectural improvement, state: problem with evidence (incidents, change frequency, coupling, defect rate), proposed target, incremental path, cost, risk and what happens if nothing is done. Let the team decide.

## 7. Performance refactoring

Measure first (profiling, SQL statistics, `EXPLAIN`, JFR, load test), change one thing, measure again, report numbers. Typical wins: N+1 queries, missing indexes, chatty remote calls (batch them), unbounded result sets, excessive object mapping, synchronous calls that can be parallelised safely.

## 8. Version migrations

- Always one step at a time, with the build green before starting. Read the official migration guide for each step (via Context7 when available).
- **Spring Boot 2.7 → 3.x**: Java 17 minimum; `javax.*` → `jakarta.*` (OpenRewrite recipes help); Spring Security 6 (`SecurityFilterChain`, `authorizeHttpRequests`, `requestMatchers`); Hibernate 6 (query and type changes, sequence naming, implicit joins); trailing-slash matching removed; Sleuth replaced by Micrometer Tracing; add `spring-boot-properties-migrator` temporarily to detect renamed properties. Upgrade to the latest 2.7.x first and remove deprecations.
- **Boot 3.x minors and 4.x**: read the release notes for each version (deprecations removed, dependency upgrades); check third-party starters for compatibility.
- **Java 17 → 21**: update toolchain/`maven.compiler.release`, CI images and Docker base images; upgrade bytecode-dependent tools (Lombok, Mockito/Byte Buddy, JaCoCo, ArchUnit, Sonar scanner). Adopt new features gradually; virtual threads are an opt-in decision with load testing.
