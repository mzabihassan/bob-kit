# Angular coding standards

Apply these to new code. In existing code, follow the project's established conventions first; only modernise what the task touches, or when the user asks for it.

## Architecture

- Standalone components, directives and pipes only (no new NgModules).
- Bootstrap with `bootstrapApplication` + `app.config.ts` providers (`provideRouter`, `provideHttpClient`, `provideZonelessChangeDetection` when zoneless).
- Organise by feature (`features/<feature>/…`), with `core/` for app-wide singletons and `shared/` for reusable UI. Avoid a giant `shared` module-like barrel.
- Lazy load feature routes with `loadComponent` / `loadChildren`. Use `@defer` for heavy, below-the-fold UI.
- Smart (container) vs presentational components: presentational components take `input()`s and emit `output()`s, no service calls.

## Components

- `changeDetection: ChangeDetectionStrategy.OnPush` (default in v22; set it explicitly in v17–v21).
- Use `input()`, `input.required()`, `output()`, `model()`, `viewChild()`, `contentChild()`; avoid `@Input/@Output` decorators in new code.
- Use `inject()` instead of constructor injection.
- Keep templates free of heavy logic: move computations into `computed()`.
- Use built-in control flow (`@if`, `@for … track`, `@switch`, `@let`). Always give `@for` a stable `track` key (an id, not `$index` unless the list is static).
- Use `host: {}` in the decorator instead of `@HostBinding` / `@HostListener`.
- Use `NgOptimizedImage` (`ngSrc`) for images.
- Use class/style bindings (`[class.active]`, `[style.width.px]`) instead of `ngClass` / `ngStyle` for simple cases.

## State and reactivity

- Local and shared UI state: signals. Derived state: `computed()`. Writable derived state: `linkedSignal()`.
- `effect()` only for side effects that leave Angular (logging, localStorage, third-party DOM libraries). Never use an effect to copy one signal into another.
- Async data: `httpResource()` / `resource()` / `rxResource()` (stable in v22). Keep RxJS for event streams, websockets, complex orchestration; bridge with `toSignal()` / `toObservable()`.
- Unsubscribe automatically with `takeUntilDestroyed()` when you must subscribe.
- Services holding state expose readonly signals (`asReadonly()`) and mutation methods.

## Forms

- v22 projects starting new forms: Signal Forms.
- Existing Reactive Forms: keep them typed (`FormGroup<{...}>`, `nonNullable`), do not migrate unless asked.
- Validation messages must be accessible (associated with the field, `aria-invalid`, `aria-describedby`).

## HTTP

- `provideHttpClient(withFetch(), withInterceptors([...]))` — functional interceptors only.
- In v22, Fetch is the default; keep `withXhr()` only if upload progress events are required.
- Never hardcode base URLs or tokens. Use environment files / injection tokens.
- Handle errors at the boundary (interceptor or resource error state) and show a user-facing message.

## Accessibility

- Semantic HTML first; Angular Aria or CDK a11y for complex widgets.
- Every interactive element is keyboard reachable with visible focus.
- Target WCAG 2.2 AA (contrast, labels, focus order, live regions for async updates).

## Testing

- Unit: Vitest (default in v22) or the project's runner. Test behaviour through the DOM with `TestBed` and component harnesses.
- Zoneless/OnPush tests: use `await fixture.whenStable()` instead of relying on `fixture.detectChanges()` alone.
- HTTP: `provideHttpClientTesting()` + `HttpTestingController`.
- Add a test for every bug fix that would have caught the bug.

## Performance

- Watch the initial bundle budget in `angular.json`; investigate any budget warning instead of raising the budget.
- Prefer `@defer`, lazy routes and `injectAsync()` (v22) for rarely used heavy code.
- Avoid function calls in templates that are not pure signals/computed.

## Style

- Follow the Angular style guide on angular.dev (file names like `user-profile.ts` per the 2025 style guide if the project uses it; otherwise keep the existing `.component.ts` suffix convention).
- Strict TypeScript: no `any`, no non-null assertions without a comment explaining why.
