# Angular migration playbook

Use for version upgrades and for pattern migrations (standalone, control flow, signals, Signal Forms, zoneless, Vitest).

## 1. Pre-flight (never skip)

<Steps>
<Step>
Record the baseline: `npx ng version`, `node -v`, `git status` (working tree must be clean), current branch.
</Step>

<Step>
Confirm the build and tests pass **before** upgrading: `ng build --configuration production` and the unit test command. If they already fail, stop and report — do not mix pre-existing failures with migration failures.
</Step>

<Step>
List third-party Angular dependencies (Material/CDK, NgRx, PrimeNG, ngx-*, Nx, Ionic, Storybook…) and check that each has a release supporting the target Angular version. Flag blockers before starting.
</Step>

<Step>
Open the official guide for the exact path: `https://angular.dev/update-guide?v=<from>-<to>&l=3` and note manual steps.
</Step>

<Step>
Create a dedicated branch (e.g. `chore/angular-22-upgrade`). One major version = at least one commit.
</Step>
</Steps>

## 2. Version upgrade loop (one major at a time)

For each major N → N+1:

<Steps>
<Step>
Update the toolchain if the target requires it (Node, TypeScript). For v22: Node ≥ 22.12 and TypeScript 6.
</Step>

<Step>
Run `npx ng update @angular/core@<N+1> @angular/cli@<N+1>` (add `--dry-run` first to preview). Never edit Angular versions manually.
</Step>

<Step>
Update ecosystem packages in the same step when they follow Angular's versions: `npx ng update @angular/material@<N+1>` (also updates CDK), then other libraries.
</Step>

<Step>
Read the migration output. Review every file the schematics changed and every `TODO`/comment they inserted.
</Step>

<Step>
Build, test, run the app. Fix errors using `troubleshooting.md`. Commit: `chore(deps): upgrade Angular to v<N+1>`.
</Step>
</Steps>

Never jump several majors in one `ng update` (e.g. 18 → 22 is four sequential upgrades).

## 3. Angular 21 → 22 checklist

| Change | Auto-migrated | What to check manually |
| --- | --- | --- |
| Node ≥ 22.12, TypeScript 6 | No | Update CI images, Dockerfiles, `.nvmrc`, `engines` |
| `OnPush` default | Yes — adds `ChangeDetectionStrategy.Eager` to components without an explicit strategy | Later, remove `Eager` component by component and test each |
| HttpClient uses Fetch | Yes — adds `withXhr()` where needed | Upload progress UI, interceptors relying on XHR specifics, SSR |
| `?.` returns `undefined` instead of `null` | Partial — wraps expressions for review | Templates comparing with `=== null`, pipes or inputs expecting `null` |
| `paramsInheritanceStrategy: 'always'` | No | Routes reading `ActivatedRoute.params` in children; set `'emptyOnly'` to keep old behaviour |
| `canMatch` third parameter | Yes | Custom guard tests |
| `strictTemplates` on | — | New template type errors: fix types rather than disabling strictness |
| SSR `allowedHosts` enforced | No | Add all production/staging hosts, or SSR returns HTTP 400 |
| Transfer cache skips credentialed requests | No | Pages relying on cached authenticated data during hydration |
| CDK breaking changes (a11y, drag-drop, menu) | Partly | Read the Material/CDK changelog for 22.0 |

Risk areas to test manually after v22: routing with nested params, forms (especially custom `ControlValueAccessor`), file uploads, SSR pages, components that mutated inputs/objects in place (exposed by OnPush).

## 4. Pattern migrations (official schematics)

Run each as a separate commit, after the version upgrade is green. Check exact schematic names with `ng generate @angular/core: --help` for the installed version.

| Migration | Command |
| --- | --- |
| NgModules → standalone | `ng g @angular/core:standalone` (run its modes in order) |
| `*ngIf/*ngFor/ngSwitch` → control flow | `ng g @angular/core:control-flow` |
| Constructor DI → `inject()` | `ng g @angular/core:inject` |
| `@Input` → `input()` | `ng g @angular/core:signal-input-migration` |
| `@Output` → `output()` | `ng g @angular/core:output-migration` |
| Queries → signal queries | `ng g @angular/core:signal-queries-migration` |
| Lazy routes to `loadComponent` | `ng g @angular/core:route-lazy-loading` |
| Self-closing tags | `ng g @angular/core:self-closing-tag` |
| Karma → Vitest | `ng g @angular/core:migrate-karma-to-vitest` then `refactor-jasmine-vitest` (names per v22 docs — verify) |

## 5. Zone.js → zoneless

1. Ensure components are `OnPush`-safe: no in-place mutation of inputs, state in signals or immutable objects.
2. Replace `NgZone.onStable`/`onMicrotaskEmpty` usages; `NgZone.run` becomes unnecessary.
3. Add `provideZonelessChangeDetection()` and remove `zone.js` from `polyfills` in `angular.json` (and from test polyfills).
4. Tests: replace `fakeAsync`/`tick` relying on Zone with `await fixture.whenStable()` or fake timers of the test runner.
5. Check third-party libraries that assumed Zone triggering change detection.

## 6. Reactive Forms → Signal Forms (v22)

- Only when asked. Migrate form by form, never all at once.
- Keep existing `ControlValueAccessor` components through the compatibility layer, then migrate them last.
- Re-map validators (`Validators.required` → schema `required()`, async validators → `validateHttp()` with debounce).
- Keep the submitted payload shape identical; add tests on the payload before migrating.

## 7. Rollback

- Each step is a commit, so rollback is `git revert <sha>` of the failing step.
- Keep the lockfile in the same commit as the `package.json` change.
- Do not push or open a PR without the user's approval.
