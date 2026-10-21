# Java / Spring Boot tests for coverage

Use the project's stack (JUnit 4 vs 5, Mockito version, AssertJ/Hamcrest, Spring Boot version). Check version-sensitive APIs via Context7 when unsure.

## Cheapest test level that gives confidence

| Target | Approach |
| --- | --- |
| Utilities, calculators, validators, value objects, enums | Plain JUnit 5, no Spring, no mocks. `@ParameterizedTest` with `@CsvSource`/`@MethodSource`/`@EnumSource` to cover every branch in a few lines |
| Mappers (manual or MapStruct) | Instantiate the mapper (MapStruct: `Mappers.getMapper(X.class)` or the generated `XImpl` when it has no Spring dependencies); assert field mapping, nulls, nested objects, collections |
| Services | `@ExtendWith(MockitoExtension.class)`, `@Mock` collaborators, `@InjectMocks` or constructor call. Cover each decision branch and exception path. Stub only what the branch needs (strict stubs flag the rest) |
| Controllers | `@WebMvcTest(XController.class)` + mocked service (`@MockitoBean` on Boot 3.4+, `@MockBean` before). One test per status code/validation path covers the controller and the `@ControllerAdvice` |
| Exception handlers | Through `@WebMvcTest`, or direct instantiation when they are simple mappers from exception to response |
| Repositories with custom queries | `@DataJpaTest` on the project's test database (Testcontainers if already used). Not for derived methods without logic: they add little value |
| Security configuration | `@WebMvcTest` with `spring-security-test` (`@WithMockUser`, `jwt()`), assert allowed vs denied |
| Scheduled jobs / batch steps | Call the job's method or the processor/writer directly with mocks; test scheduling configuration only if it has logic |
| Transactional behaviour, locking, real SQL | Integration test (`@SpringBootTest` or `@DataJpaTest`) on a real database. Worth it only when that behaviour is the risk |

Avoid `@SpringBootTest` for logic that a plain unit test can cover. It is slow, and each new context configuration makes the suite slower.

## Getting many branches covered with little code

- Read the uncovered lines and branches in the JaCoCo HTML (`target/site/jacoco/index.html`): red is a missed line, yellow is a partly covered branch. Write one parameterised test per decision table rather than one test per line.
- Exercise branches through the public method; if a private method is unreachable, it may be dead code (report it rather than testing it via reflection).
- Cover exception paths with `assertThrows`/`assertThatThrownBy` and check the message or type that callers rely on.
- Use `ArgumentCaptor` or the returned value to assert real outcomes; `verify` only for side effects that matter (saved, published, audited).
- Builders/fixtures already in the test sources: reuse them; add a small factory method if three tests need the same object.

## Testability fixes (small, justified production changes)

Only when a test is otherwise impossible or absurdly expensive: inject a `Clock` instead of `now()`, replace field injection with constructor injection, extract a pure method from a large one, narrow a `private static` I/O call behind an injected collaborator. Mention each one in the report as a production change.

## JaCoCo and Sonar setup checks

- Maven: `jacoco-maven-plugin` with `prepare-agent` and `report`. If Surefire/Failsafe define `argLine`, use `<argLine>@{argLine} …</argLine>`, otherwise the agent is silently dropped (0% coverage).
- Integration tests with Failsafe need their own `prepare-agent-integration`/merge, or Sonar only sees unit-test coverage.
- Multi-module: a `report-aggregate` module, or list every module report in `sonar.coverage.jacoco.xmlReportPaths`.
- Gradle: `jacocoTestReport { reports { xml.required = true } }` and `test { finalizedBy jacocoTestReport }`.
- Sonar reads XML reports only (`sonar.coverage.jacoco.xmlReportPaths`); make sure the path matches where the report is generated in CI.
- Run a single module quickly: `./mvnw -pl <module> -am test jacoco:report` or `./gradlew :<module>:test :<module>:jacocoTestReport`.
