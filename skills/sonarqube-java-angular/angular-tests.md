# Angular tests for coverage

Detect the project's runner and Angular version first: Karma/Jasmine (`karma.conf.js`, `@angular-devkit/build-angular:karma`), Jest (`jest.config.*`, `jest-preset-angular`), or Vitest (`@angular/build:unit-test`, `vitest.config.*`). Write tests in the existing style: spies (`jasmine.createSpyObj` vs `jest.fn`/`vi.fn`), harnesses, Testing Library. Match the APIs to the version (standalone vs NgModule, signals, functional guards/interceptors); check via Context7 when unsure.

## Cheapest approach per target

| Target | Approach |
| --- | --- |
| Pure functions, utils, mappers | Plain tests, no `TestBed` |
| Pipes | `new MyPipe()` (or with its injected dependencies faked) and call `transform` over a table of inputs |
| Validators (reactive forms) | Call the validator with `new FormControl(value)` / `FormGroup`; assert the `ValidationErrors` object or `null` |
| Services with `HttpClient` | `TestBed` with `provideHttpClient()` + `provideHttpClientTesting()` (or `HttpClientTestingModule` in older code); `HttpTestingController.expectOne`, flush success and error responses, `verify()` in `afterEach`. One setup covers many cases |
| Services with signals / state | Instantiate via `TestBed.inject`, call methods, read signals and `computed` values directly |
| RxJS logic | Subscribe and assert emitted values; for timing, use `fakeAsync`/`tick` (Zone-based apps), the runner's fake timers, or marble tests if the project already uses them |
| Functional guards / resolvers | `TestBed.runInInjectionContext(() => myGuard(route, state))` with faked services; cover allow, redirect (`UrlTree`) and deny |
| Functional interceptors | `provideHttpClient(withInterceptors([myInterceptor]))` + `provideHttpClientTesting()`; assert headers added and error handling |
| Class-based guards/interceptors | Instantiate with faked dependencies and call `canActivate`/`intercept` directly |
| Simple components | `TestBed.createComponent` with the component's real `imports`, faked services; set inputs with `fixture.componentRef.setInput()`; assert rendered text and emitted outputs; trigger events through the DOM |
| Reactive form components | Set control values, assert validity, error messages displayed and the submitted payload |

## Keep tests cheap and robust

- Fake services with small objects or spies instead of importing their real dependency trees. Use `NO_ERRORS_SCHEMA`/stub children only if the project already does; prefer overriding heavy child components with stubs.
- Test behaviour visible to users or callers (DOM text, emitted values, HTTP requests, navigation), not private fields or internal method calls.
- OnPush/zoneless components: after changing inputs or signals, `await fixture.whenStable()` (or `fixture.detectChanges()` in Zone apps).
- Cover error paths: HTTP error responses, empty lists, invalid form states. They are often the uncovered branches.
- Do not test Angular itself (that a binding binds) or third-party widgets.

## Coverage setup checks

- Generate LCOV: `ng test --no-watch --code-coverage` (Karma: `coverage/<app>/lcov.info`), Jest `--coverage` with the `lcov` reporter, Vitest `--coverage` with `@vitest/coverage-v8` or `-istanbul` (use what the project has installed).
- Sonar property: `sonar.javascript.lcov.reportPaths=coverage/<app>/lcov.info` (comma-separated for several apps/libs).
- 0% or missing files in Sonar usually means the `SF:` paths in the LCOV file do not match Sonar's source paths (absolute paths from another machine, a different base directory), or `sonar.sources`/`sonar.tests`/`sonar.exclusions` are misconfigured. Check before writing tests.
- `*.spec.ts` must be in `sonar.tests` (or excluded from `sonar.sources`) so tests are not counted as uncovered production code.
