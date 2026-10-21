# Angular troubleshooting

Method: reproduce → read the exact error code (`https://angular.dev/errors/NG0xxx`) → root cause → minimal fix → verify.

## Install and `ng update`

| Symptom | Action |
| --- | --- |
| `ERESOLVE` peer dependency conflict | Find a library version supporting the target Angular. `--force`/`--legacy-peer-deps` only with user approval, documented |
| "Repository is not clean" | Ask the user to commit or stash; never discard or commit for them |
| Wrong CLI version used | Use `npx ng …` (local CLI) |
| Node or TypeScript not supported | Align with https://angular.dev/reference/versions (v22: Node ≥ 22.12, TS 6) |

## Compiler and template

| Error | Fix |
| --- | --- |
| `NG8001` unknown element | Import the component in `imports` (or its NgModule); check selector |
| `NG8002` can't bind to 'x' | Import the directive or fix the input name/alias |
| `NG8004` no pipe found | Import the pipe |
| Component "is not standalone" / "must be part of an NgModule" (after v19) | Set `standalone: false` for NgModule-declared items, or import it as standalone |
| `@for` missing `track` | Add `track item.id` |
| New strict-template errors | Fix the types; don't disable strictness |
| `=== null` checks fail (v22) | Template `?.` now yields `undefined`; use `== null` |

## Runtime

| Error | Fix |
| --- | --- |
| `NG0100` ExpressionChangedAfterItHasBeenChecked | Derive with `computed()` or set state earlier; no `setTimeout` workaround |
| `NG0200` circular DI | Extract shared logic into a third service |
| `NG0201` / `NullInjectorError` | Provide it (`providedIn: 'root'`, `app.config.ts`, route or module `providers`) |
| `NG0203` `inject()` outside injection context | Call in a field initialiser/constructor, or `runInInjectionContext` |
| `NG0600` signal write in `computed` | Move the write to an event handler |
| `NG05xx` hydration mismatch | Make SSR output deterministic; guard browser APIs with `afterNextRender`/`isPlatformBrowser`; `ngSkipHydration` last resort |
| UI not updating (OnPush/zoneless) | Use signals or immutable updates; `markForCheck()` only in legacy code |
| SSR returns HTTP 400 (v22) | Configure `allowedHosts` (+ `trustProxyHeaders` behind a proxy) |
| Upload progress missing (v22) | Fetch backend: keep `withXhr()` |
| Child route params changed (v22) | `paramsInheritanceStrategy: 'always'`; set `'emptyOnly'` or adapt |

## Tests

| Symptom | Fix |
| --- | --- |
| Jasmine APIs fail under Vitest/Jest | Replace `jasmine.createSpyObj`/`spyOn` with `vi.fn()`/`vi.spyOn` (or `jest.*`) |
| `fakeAsync` fails in zoneless tests | `await fixture.whenStable()` or the runner's fake timers |
| DOM not updated | `fixture.componentRef.setInput()`, then `await fixture.whenStable()` |

## Bundle size

Budget exceeded: `ng build --stats-json`, inspect with `npx esbuild-visualizer` or `source-map-explorer`, lazy load heavy libraries. Fix CommonJS warnings with ESM alternatives; use `allowedCommonJsDependencies` only with justification.

## Stuck

Build a minimal reproduction with the same version, search angular/angular issues with the exact error and version, and report what is confirmed vs suspected.
