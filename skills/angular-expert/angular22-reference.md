# Angular 22 reference

Angular v22 was released on 3 June 2026. Use this file as a quick reference; always confirm details against the installed typings (`node_modules/@angular/*`) and https://angular.dev, since minor releases (22.1, 22.2…) can change experimental APIs.

Status legend: **[stable]**, **[preview]** (developer preview), **[experimental]**.

## Toolchain requirements

| Item | Angular 22 |
| --- | --- |
| Node.js | 22.12.0 or later (Node 20 dropped) |
| TypeScript | 6.x required (5.x no longer supported) |
| Release cadence | Since v22: one major per year, with several minors in between. Verify on https://angular.dev/reference/releases |

## New defaults for new projects (and after migration)

| Area | v21 | v22 |
| --- | --- | --- |
| Change detection strategy | `Eager` (formerly `Default`) | `OnPush` |
| HttpClient backend | XHR (Fetch opt-in) | Fetch (`withXhr()` to keep XHR) |
| Strict templates | opt-in | on by default |
| Zoneless | default for new apps since v21 | unchanged (Zone.js still supported for existing apps) |
| Unit tests | Vitest opt-in | Vitest default for new projects |
| Router `paramsInheritanceStrategy` | `'emptyOnly'` | `'always'` |

## Reactivity

- `signal`, `computed`, `effect`, `linkedSignal`, `untracked` — [stable].
- `input()`, `output()`, `model()`, `viewChild()`, `contentChild()` signal queries — [stable]. Prefer them over decorators in new code.
- `resource()`, `rxResource()`, `httpResource()` — [stable] in v22. Use for async data instead of manual `subscribe` + flags.
  - `chain()` composes dependent resources and propagates loading/error states.
  - Resources can be cached with an id for SSR so the server value is reused on the client without a loading flash.
- `debounced()` signal utility — [experimental].

```ts
import { Component, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';

@Component({
  selector: 'app-user',
  template: `
    @if (user.isLoading()) { <p>Loading…</p> }
    @else if (user.error()) { <p role="alert">Could not load user.</p> }
    @else if (user.hasValue()) { <h2>{{ user.value().name }}</h2> }
  `,
})
export class UserComponent {
  readonly id = signal(1);
  readonly user = httpResource<User>(() => `/api/users/${this.id()}`);
}
```

## Signal Forms — [stable]

- Package: `@angular/forms/signals` (`form()`, schema validators, `[field]` binding — check the exact directive name in the installed version).
- v22 additions: `minDate()` / `maxDate()` validators, `getError()`, `reloadValidation()`, debounce on blur, debounced async validation inside `validateHttp()`.
- A compatibility layer lets existing `ControlValueAccessor` components work with Signal Forms during migration.
- Angular Material and Angular Aria support Signal Forms.
- Reactive Forms and template-driven forms are **not** removed: do not force a rewrite unless asked.

## Dependency injection

- `@Service()` — shorthand for `@Injectable({ providedIn: 'root' })`. The class must use `inject()`, not constructor injection.
- `injectAsync()` — lazy-loads a service (and its bundle) on first use, with an optional prefetch hook (e.g. on idle). Good for heavy, rarely used services (PDF export, charting, editors).
- Treat both as new APIs: check their stability label in the installed version before recommending them for production.

```ts
import { Service, inject, injectAsync } from '@angular/core';

@Service()
export class ReportService {
  private readonly http = inject(HttpClient);
  // Exact injectAsync signature: verify in @angular/core typings.
  private readonly pdf = injectAsync(() => import('./pdf-export.service').then(m => m.PdfExportService));
}
```

## Templates

- Control flow `@if`, `@for` (with mandatory `track`), `@switch`, `@defer`, `@let` — use instead of `*ngIf`, `*ngFor`, `ngSwitch`.
- v22: inline arrow functions, spread syntax, comments inside element attribute lists, several values in one `@switch` case.
- Exhaustive `@switch` checking: `@default never` raises a compile error when a union gains an unhandled member.
- Optional chaining `?.` now follows TypeScript semantics (returns `undefined`, not `null`). Migration wraps affected expressions for review.
- New compile-time errors: invalid `@for`, element matched by several components, inputs bound under the same alias.
- `@boundary` / `@error` error-boundary blocks — announced as in progress / experimental. Do not use in production code unless the installed version exposes them as stable.

## Router

- `paramsInheritanceStrategy` default is now `'always'`: child routes inherit parent params. Set `'emptyOnly'` in `provideRouter(..., withRouterConfig({ paramsInheritanceStrategy: 'emptyOnly' }))` to keep the old behaviour.
- `canMatch` guards receive a third mandatory parameter (auto-migrated).
- Route-level cleanup of providers/resources improves memory use in large apps.
- Navigation API integration — [experimental].

## SSR and security

- Incremental hydration is the default for SSR.
- `@angular/ssr`: `allowedHosts` is enforced; requests with other `Host` headers get HTTP 400. Configure it for every deployed domain.
- `trustProxyHeaders` option for apps behind a reverse proxy (`X-Forwarded-*`).
- HTTP transfer cache skips requests with cookies or `withCredentials`.
- Stricter sanitisation (SVG `href`/`xlink:href`, meta selectors) and SSRF hardening in `platform-server` and `HttpClient`.

## Accessibility — Angular Aria [stable]

- Package `@angular/aria`: headless, accessible patterns (combobox, listbox, menu, tabs, tree, autocomplete, multiselect…) with keyboard, focus and ARIA roles handled; you own markup and styles.
- Includes test harnesses and Signal Forms support.
- Prefer it over hand-written ARIA for custom design-system components.

## AI tooling

- Angular CLI MCP server (`ng mcp`) with dev-server tools and access to the signal/DI graph of a running dev app.
- Official Angular agent skills (`npx skills add …`).
- WebMCP (`declareExperimentalWebMcpTool()`, `provideExperimentalWebMcpForms()`) — [experimental], behind a Chrome flag. Prototype only.

## Sources

- https://angular.dev/events/v22
- https://blog.angular.dev/announcing-angular-v22-c52bb83a4664
- https://angular.dev/update-guide?v=21.0-22.0
- https://www.netlify.com/changelog/2026-06-01-support-for-angular-v22/
