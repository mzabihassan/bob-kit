# Angular API availability (v18 → latest)

Use to check that an API exists in the project's version before generating it. "Preview" = developer preview / experimental at that version. Confirm doubtful cases in `node_modules/@angular/*` typings; Node/TypeScript/RxJS ranges are at https://angular.dev/reference/versions. For versions newer than this table, read the release notes before using new APIs.

## Available in every supported version (v18+)

Standalone components, functional guards/resolvers/interceptors, `inject()`, `DestroyRef`/`takeUntilDestroyed`, typed reactive forms, `NgOptimizedImage`, `hostDirectives`, `withComponentInputBinding`, `signal`/`computed`, stable `@if/@for/@switch/@defer`, `application` (esbuild) builder, `<ng-content>` fallback, Material 3. `input()`, `output()`, `model()`, `viewChild()`/`contentChild()` exist (preview in v18, stable in v19).

## By version

| Version | Added or changed |
| --- | --- |
| 18 | Zoneless experimental (`provideExperimentalZonelessChangeDetection`), forms `events` stream, route redirect functions. 18.1 `@let` (preview) |
| 19 | `standalone: true` is the default (NgModule declarations need `standalone: false`), signal inputs/outputs/model/queries stable, `@let` stable, `linkedSignal` and `resource`/`rxResource` (experimental), incremental hydration (preview), route-level SSR render mode. 19.2 `httpResource` (experimental) |
| 20 | `effect`, `linkedSignal`, `toSignal`, `afterRenderEffect` stable; incremental hydration stable; zoneless preview (`provideZonelessChangeDetection`), stable in 20.2; `*ngIf/*ngFor/ngSwitch` deprecated; new style guide (no `.component` suffix in `ng new`); template `**`, `in`, template literals; `animate.enter/leave` (20.2) |
| 21 | Zoneless default for new apps, Signal Forms (experimental), Vitest default for new projects, Angular Aria (preview) |
| 22 | `OnPush` default (migration adds `Eager` to existing components), Fetch default for `HttpClient` (`withXhr()` keeps XHR), strict templates default, `resource`/`httpResource` and Signal Forms stable, `@Service()` and `injectAsync()`, router `paramsInheritanceStrategy: 'always'`, SSR `allowedHosts` enforced, template `?.` returns `undefined`. Needs Node ≥ 22.12 and TypeScript 6 |

## Two styles coexist in v18+ codebases

Follow the style the project uses; do not mix them inside one file.

| Concern | NgModule / decorator style | Standalone / signal style |
| --- | --- | --- |
| Declaration | `@NgModule` declarations | `imports` on the component |
| Bootstrap | `bootstrapModule(AppModule)` | `bootstrapApplication(App, appConfig)` |
| DI | constructor injection | `inject()` |
| Inputs/outputs | `@Input`/`@Output` + `EventEmitter` | `input()`, `output()`, `model()` |
| Queries | `@ViewChild`/`@ContentChild` | `viewChild()`/`contentChild()` |
| Templates | `*ngIf`, `*ngFor` + `trackBy` (deprecated v20) | `@if`, `@for … track`, `@switch`, `@let`, `@defer` |
| State | RxJS services, NgRx Store | signals, `computed`, `linkedSignal`, NgRx SignalStore |
| Async data | `subscribe` / `async` pipe | `toSignal`, `resource`/`httpResource` (experimental until v22) |
| Host bindings | `@HostBinding`/`@HostListener` | `host: {}` metadata |
| Forms | Reactive (typed) or template-driven | same; Signal Forms v21+ (stable v22) |
| Change detection | Zone.js + `Default` | `OnPush` + signals, zoneless (stable v20.2) |
| Tests | Karma/Jasmine, Jest | Vitest (default for new projects v21+), Jest |
