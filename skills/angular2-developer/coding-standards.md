# Angular coding standards

These are defaults. The project's instructions and observed conventions win: same file naming (`.component.ts` suffix or not), folder layout, state library, forms style, UI kit, styling approach and test style as the surrounding code. Use the idiom column of `version-reference.md` that matches the project's era.

## Architecture

- Follow the existing structure (feature folders, Nx libs, `core/`/`shared/`, domain layers). If there is none: `features/<feature>/`, `core/` for app-wide singletons, `shared/` for reusable UI.
- NgModule codebase: keep adding to modules unless the team has started a standalone migration. Standalone codebase: no new NgModules.
- Lazy load feature routes; use `@defer` for heavy below-the-fold UI.
- Container components call services; presentational components only take inputs and emit outputs.

## Components

- `OnPush` unless the project deliberately uses `Default`/`Eager` (v22 defaults to OnPush). Never mutate inputs or objects in place.
- Keep templates logic-light: derive values in `computed()` or pure pipes/getters on memoised data, not method calls.
- Lists always have a stable identity: `track item.id` or `trackBy`.
- Images: `NgOptimizedImage`. Prefer `[class.x]`/`[style.x]` to `ngClass`/`ngStyle` for simple cases.

## State and async

- Use the project's state solution (NgRx Store/Effects, NgRx SignalStore, Akita/Elf, NGXS, plain services). Do not introduce a new one without asking.
- Signals for synchronous UI state, `computed` for derived state; `effect` only for side effects leaving Angular (storage, logging, third-party DOM), never to copy signals.
- RxJS for event streams, websockets and complex orchestration. Every manual `subscribe` is cleaned up (`async` pipe, `takeUntilDestroyed`, or the project's pattern). Avoid nested subscribes; use `switchMap`/`concatMap`/`exhaustMap` deliberately.
- Cover loading, error and empty states for every async view.

## Forms

- Keep the form technology already used in the feature. Reactive forms: typed, `nonNullable` where applicable. Signal Forms only on v21+ and only when the team uses or asks for them.
- Validation errors are accessible: label, `aria-invalid`, `aria-describedby`.

## HTTP

- Data access goes through services (or the project's API layer / generated clients, e.g. OpenAPI). No `HttpClient` in presentational components.
- Interceptors in the project's style (functional `withInterceptors` for standalone apps, class-based `HTTP_INTERCEPTORS` where the project already uses them).
- Base URLs and tokens come from environment config or injection tokens, never literals. Handle errors at a boundary and show a user-facing message.

## Accessibility and UI

- Semantic HTML first; CDK a11y, Angular Aria (v21+) or the project's UI kit (Material, PrimeNG…) for complex widgets. Keyboard reachable, visible focus, WCAG 2.2 AA.
- Use the project's design tokens, theme and styling method (SCSS, Tailwind, CSS modules); no hard-coded colours if tokens exist.

## Security

- No `innerHTML` with untrusted data, no `bypassSecurityTrust*` without a written reason. SSR: configure allowed hosts, never cache credentialed responses in transfer state.

## Testing

- Same runner and style as existing specs (Jasmine/Karma, Jest, Vitest; TestBed, Testing Library, harnesses, Cypress/Playwright for e2e).
- Test behaviour through the DOM, not private methods. HTTP via `HttpTestingController` and `provideHttpClientTesting()`.
- OnPush/zoneless: `fixture.componentRef.setInput()` then `await fixture.whenStable()`.
- Every bug fix gets a test that would have caught it.

## TypeScript

- Respect the project's strictness; do not loosen `tsconfig` to make code compile. No new `any`; no non-null assertion without a reason.
