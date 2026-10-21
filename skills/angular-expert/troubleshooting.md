# Angular troubleshooting guide

Method: reproduce → read the exact error code → locate the root cause → minimal fix → verify. Look up any `NG0xxx` code at `https://angular.dev/errors/NG0xxx`.

## Install and `ng update` failures

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `ERESOLVE unable to resolve dependency tree` | A library's `peerDependencies` does not yet allow the new Angular version | Find a compatible library version. Use `--force`/`--legacy-peer-deps` only with explicit user approval, and document it |
| `ng update` refuses: "Repository is not clean" | Uncommitted changes | Commit or stash first (do not discard without asking) |
| "The installed Angular CLI version is outdated" / wrong version used | Global CLI differs from local | Use `npx ng …` |
| `Node.js version vX is not supported` | Toolchain too old for target | v22 needs Node ≥ 22.12 |
| TypeScript version error during build | TS outside supported range | v22 needs TypeScript 6; align `typescript` in devDependencies |

## Compiler / template errors

| Error | Meaning | Fix |
| --- | --- | --- |
| `NG8001` 'x' is not a known element | Component not imported in the standalone `imports` (or module) | Add the import; check selector spelling |
| `NG8002` Can't bind to 'x' | Unknown input or missing directive import | Import the directive or fix the input name/alias |
| `NG8004` No pipe found | Pipe not imported | Add pipe to `imports` |
| New errors after v22 `strictTemplates` | Types were wrong before, now checked | Fix types (`input<T>()`, narrowing with `@if (x; as v)`) rather than disabling strictness |
| `@for` must have a `track` expression | Required by control flow | Add `track item.id` |
| Element matched by multiple components (v22) | Selector collision | Rename selectors or narrow them |
| Comparison with `null` fails after `?.` change (v22) | `?.` now yields `undefined` | Compare with `== null` or check the migration-wrapped expression |

## Runtime errors

| Error | Cause | Fix |
| --- | --- | --- |
| `NG0100` ExpressionChangedAfterItHasBeenChecked | Value changed during a check (often set in `ngAfterViewInit` or by a child) | Derive with `computed()`, move logic earlier, or restructure; do not wrap in `setTimeout` as a fix |
| `NG0200` Circular dependency in DI | Services inject each other | Extract the shared logic into a third service, or use a lazy `inject` inside a method |
| `NG0201` / `NullInjectorError: No provider for X` | Missing provider (common after standalone migration) | Add `provideX()` in `app.config.ts`, `providedIn: 'root'` / `@Service()`, or route `providers` |
| `NG0203` inject() must be called from an injection context | `inject()` called in a callback/method | Call in field initialiser/constructor, or use `runInInjectionContext` |
| `NG0600` Writing to signals is not allowed in a computed | Side effect in `computed()` | Move the write to an event handler or `effect()` |
| `NG0602` signal read in disallowed context | Signal read inside a reactive context that forbids it | Use `untracked()` or restructure |
| `NG0500`-range hydration mismatch | Server and client DOM differ (random IDs, dates, `window` access, invalid HTML nesting) | Make rendering deterministic; guard browser APIs with `afterNextRender` / `isPlatformBrowser`; use `ngSkipHydration` only as a last resort with a TODO |
| UI not updating after zoneless/OnPush | State mutated in place or changed outside signals | Use signals or immutable updates; call `markForCheck()` only for legacy code |
| HTTP 400 on every SSR request (v22) | `allowedHosts` does not list the host | Configure `allowedHosts` (and `trustProxyHeaders` behind a proxy) |
| Upload progress no longer reported (v22) | Fetch backend | Keep `withXhr()` for those requests/app |
| Child route lost/gained params (v22) | New `paramsInheritanceStrategy: 'always'` | Set `'emptyOnly'` or adapt code reading params |

## Tests

| Symptom | Cause | Fix |
| --- | --- | --- |
| Tests pass in Karma, fail in Vitest | Jasmine APIs (`spyOn`, `jasmine.createSpyObj`, `done`) | Run the jasmine→vitest refactor schematic; replace with `vi.fn()` / `vi.spyOn` |
| `fakeAsync` errors in zoneless tests | `fakeAsync` needs Zone | Use `await fixture.whenStable()` or runner fake timers |
| DOM not updated in test | OnPush / zoneless | `fixture.componentRef.setInput()`, then `await fixture.whenStable()` |

## Build size / performance

- Budget exceeded: run `ng build --stats-json` and inspect with `npx esbuild-visualizer` or `source-map-explorer`. Look for eagerly imported heavy libraries (moment, lodash full import, charting, PDF) and lazy load them.
- `CommonJS or AMD dependencies can cause optimization bailouts`: replace the dependency with an ESM version or add it to `allowedCommonJsDependencies` only with justification.

## When stuck

1. Create a minimal reproduction (new `ng new` app with the same version + the failing snippet).
2. Search the error on github.com/angular/angular issues with the exact version.
3. Report clearly what is confirmed vs suspected.
