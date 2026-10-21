# Angular migration playbook (v18 → latest)

For version upgrades and pattern migrations (standalone, control flow, signals, zoneless, test runner). Respect any upgrade policy in the project's instructions (branch naming, supported versions). Never commit or push unless the user explicitly asks; pause after each hop so the user can review and commit.

## 1. Pre-flight (never skip)

1. Record `npx ng version`, `node -v`, current branch. `ng update` needs a clean working tree: if it is dirty, ask the user to commit or stash (never discard, never commit for them).
2. Build (`--configuration production`) and tests must pass **before** upgrading. If they already fail, stop and report.
3. List Angular-dependent libraries (Material/CDK, NgRx, PrimeNG, ngx-*, Nx, Ionic, Storybook, Jest presets…) and confirm each has a release for the target version. Flag blockers first.
4. Read https://angular.dev/update-guide?v=<from>-<to>&l=3 for each hop and note the manual steps.

## 2. Upgrade loop (one major at a time)

For each N → N+1:
1. Update Node/TypeScript if the target requires it (https://angular.dev/reference/versions); include CI images, Dockerfiles, `.nvmrc`, `engines`.
2. `npx ng update @angular/core@<N+1> @angular/cli@<N+1>` (try `--dry-run` first). Nx workspaces: `nx migrate` instead.
3. `npx ng update @angular/material@<N+1>` and other libraries that follow Angular majors.
4. Review every file the schematics changed and every TODO they inserted.
5. Build, test, run the app; fix with `troubleshooting.md`.
6. Stop and report the hop's result with a suggested message (`chore(deps): upgrade Angular to v<N+1>`). The next hop needs a clean tree, so continue only after the user has committed or explicitly asked you to commit.

Example: 18 → 22 is four sequential hops, never one jump.

## 3. What each hop changes

| Hop | Watch out for |
| --- | --- |
| 18 → 19 | `standalone` becomes default: migration adds `standalone: false` to NgModule declarations. Signal input/queries stable. `resource` APIs experimental only |
| 19 → 20 | Node 20 required. `*ngIf/*ngFor/ngSwitch` deprecated (still work). `effect` timing changed when it became stable; `resource` option renames (`request` → `params`, `loader` → `stream` for streams) if used. Zoneless provider renamed to `provideZonelessChangeDetection` |
| 20 → 21 | New projects are zoneless/Vitest; existing apps keep Zone.js and their runner. Signal Forms experimental |
| 21 → 22 | Node ≥ 22.12, TS 6. `OnPush` default (migration adds `Eager`; remove it per component with tests). Fetch backend (`withXhr()` for upload progress). `?.` yields `undefined` (check `=== null`). Router params inheritance `'always'` (set `'emptyOnly'` to keep). SSR `allowedHosts` enforced (HTTP 400 otherwise). Strict templates on: fix types, don't disable. `canMatch` third parameter (auto-migrated) |

After each hop, manually test risk areas: nested routes and params, forms (custom `ControlValueAccessor`), file upload, SSR pages, third-party widgets.

## 4. Pattern migrations (official schematics)

Only when asked or in the team's plan; one at a time, after the version upgrade is green. List what the installed version offers with `npx ng g @angular/core: --help`.

| Migration | Schematic (`ng g @angular/core:<name>`) |
| --- | --- |
| NgModules → standalone | `standalone` (run its modes in order) |
| Structural directives → control flow | `control-flow` |
| Constructor DI → `inject()` | `inject` |
| `@Input` / `@Output` / queries → signals | `signal-input-migration`, `output-migration`, `signal-queries-migration` |
| Eager routes → lazy | `route-lazy-loading` |
| Karma → Vitest | per the installed version's docs |

## 5. Common pitfalls and their fixes

Check these before and after each migration; most "it worked before" bugs come from here.

### Zone.js → zoneless (and OnPush)

- Order: make every component OnPush-safe first, optionally pass through `provideZoneChangeDetection({ eventCoalescing: true })`, then switch to `provideZonelessChangeDetection()` (`provideExperimentalZonelessChangeDetection()` in v18–19). Remove `zone.js` from **both** build and test `polyfills`.
- View stops updating after `setTimeout`, `setInterval`, promises, websockets or third-party callbacks (maps, charts, editors, payment SDKs): nothing schedules change detection any more. Write the result into a signal (preferred) or call `ChangeDetectorRef.markForCheck()`.
- In-place mutation (`array.push`, `obj.x = …`) on inputs or service state no longer re-renders under OnPush/zoneless: replace with immutable updates.
- `NgZone.onStable`, `onMicrotaskEmpty`, `isStable` no longer drive anything: use `afterNextRender` / `afterEveryRender` (`afterRender` before v20). `runOutsideAngular`/`run` become no-ops; remove them progressively.
- SSR waits for app stability: async work outside `HttpClient`/router (custom fetch, timers) must be wrapped with `PendingTasks`, or the page renders too early.
- Libraries that rely on Zone (old ngx-* widgets, some charting/grid wrappers): check their zoneless support; wrap their events into signals if needed.
- Tests: `fakeAsync`/`tick`/`flush`/`waitForAsync` need Zone. Add `provideZonelessChangeDetection()` to `TestBed`, then use `await fixture.whenStable()` or the runner's fake timers.

### Decorators → signals

- Forgetting the call: `@if (isOpen)` on a signal is always truthy. Templates and code must read `isOpen()`.
- Signal inputs are read-only: code that assigned to an `@Input` (`this.value = x`) must use `model()` (two-way), `linkedSignal()` (local override reset by the input) or a separate local signal. The migration schematic skips such inputs and leaves a TODO: review each one.
- `ngOnChanges` still fires but is usually replaceable by `computed()` (derived value) or `effect()` (side effect).
- `effect()` used to copy one signal into another causes extra renders and loops: use `computed()` or `linkedSignal()`; wrap reads that must not track in `untracked()`. Since v19 effects may write signals and run during change detection: re-check timing-sensitive code; in tests use `TestBed.tick()` (`TestBed.flushEffects()` before v20).
- Signals notify only on a new reference (`Object.is`): `update(list => [...list, item])`, never mutate then `set(sameRef)`.
- `toSignal()` must run in an injection context (field initialiser), subscribes immediately and starts as `undefined` unless `initialValue` or `requireSync: true`. Never call it inside a getter or method (new subscription each call).
- `toObservable()` emits asynchronously (through an effect), not synchronously on `set`.
- `viewChild()` is `undefined` until the view is created; read it in `computed`/`afterNextRender`, not the constructor. `viewChild.required()` throws if read too early.

### State management

- Upgrade NgRx (or NGXS, Akita/Elf) to the release matching the Angular major in the same hop: `npx ng update @ngrx/store@<N>`. Standalone apps: `StoreModule.forRoot` → `provideStore`, `EffectsModule` → `provideEffects`, feature state via route `providers`.
- Don't create two sources of truth: read the store with `store.selectSignal()` instead of copying store state into local signals. An `effect()` that dispatches an action which updates the state it reads loops.
- `BehaviorSubject` services → signals: keep the public API stable during the transition (expose `toObservable(state)` or keep the observable getter) so existing subscribers don't break; migrate consumers afterwards.
- NgRx SignalStore: update only through `patchState` with new objects; keep `withMethods` side effects out of `withComputed`.

### Standalone and DI

- Providers moved from an NgModule to route `providers` create a **new instance per route injector**: singletons silently split (duplicated caches, lost state). Keep app-wide services `providedIn: 'root'` or in `app.config.ts`.
- `Module.forRoot()` → its `provideX()` function, or `importProvidersFrom(Module.forRoot())` when the library has none.
- `SharedModule` re-exports disappear: each standalone component must import what its template uses (`NG8001/8002/8004` otherwise). Tests move items from `declarations` to `imports`.

### Templates and control flow

- `@for` requires `track`: use a stable id; `track $index` on reorderable or mutable lists reuses the wrong DOM (inputs keep stale values). Convert `trackBy` functions to `track fn(item)` or `track item.id`.
- Check migrated `ng-template` + `else` references and `*ngIf="x as y"` aliases (`@if (x; as y)`); the schematic leaves complex cases untouched.

### RxJS, forms, theming, tests

- RxJS 7+: `toPromise()` → `firstValueFrom`/`lastValueFrom` (`lastValueFrom` throws `EmptyError` if the stream completes without a value); `subscribe(next, error)` → observer object.
- Custom `ControlValueAccessor` under OnPush: `writeValue` must update a signal or call `markForCheck()`, otherwise the control shows stale values.
- Reactive Forms → Signal Forms (v21+): form by form, freeze the submitted payload with tests first, keep `ControlValueAccessor` components until last.
- Material 2 → 3 theming: SCSS theme API changes (`mat.theme`, `mat.define-theme`, system tokens); styles overriding Material internals break. Migrate the theme once, then fix overrides.
- Karma is deprecated: keep the existing runner during a version upgrade; switch to Vitest/Jest as a separate migration. Align `jest-preset-angular` with the Angular major.

## 6. Rollback

If a hop fails and cannot be fixed, report it and offer to restore: `git restore . && git clean -n` (show the files `clean` would remove and ask before `-f`). Keep `package.json` and the lockfile consistent.
