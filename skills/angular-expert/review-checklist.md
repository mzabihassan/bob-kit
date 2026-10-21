# Angular code review checklist

Report each finding with: severity (Critical, High, Medium, Low), file and line, problem, recommended fix, and the reason.

## Severity guide

- **Critical**: security flaw (XSS via `bypassSecurityTrust*`, secrets in code, SSRF), data loss, app crash, broken build.
- **High**: memory leak, wrong data shown, broken accessibility for a core flow, OnPush/zoneless bug that hides updates, missing error handling on API calls.
- **Medium**: performance issue, deprecated API, missing tests for new behaviour, maintainability problem.
- **Low**: style, naming, minor readability.

## Correctness and reactivity

- [ ] Signals used for state; no in-place mutation of objects held in signals or passed as inputs.
- [ ] `computed()` is pure (no writes, no HTTP).
- [ ] `effect()` not used to sync signals together.
- [ ] Every manual `subscribe` is cleaned up (`takeUntilDestroyed`, `async` pipe, or resource API).
- [ ] `@for` has a meaningful `track` key.
- [ ] Async states covered: loading, error, empty.

## Version fit

- [ ] Only APIs available in the project's Angular version; experimental APIs flagged.
- [ ] No new NgModules, `*ngIf/*ngFor`, `@Input/@Output` decorators in new code (unless the project's convention requires them).
- [ ] No deprecated APIs (check IDE strike-through / `@deprecated` in typings).

## Security

- [ ] No `innerHTML` with untrusted data; no `bypassSecurityTrust*` without justification.
- [ ] No secrets, tokens or environment URLs hardcoded.
- [ ] Credentials-bearing requests not cached in SSR transfer state.
- [ ] SSR `allowedHosts` configured.

## Accessibility

- [ ] Semantic elements; buttons are `<button>`, links are `<a href>`.
- [ ] Labels for every form control; errors linked with `aria-describedby`.
- [ ] Keyboard navigation and visible focus; complex widgets via Angular Aria/CDK.
- [ ] Images have meaningful `alt` (or empty for decorative).

## Performance

- [ ] OnPush (or v22 default) respected; no heavy function calls in templates.
- [ ] Heavy features lazy loaded (`loadComponent`, `@defer`, `injectAsync`).
- [ ] Images via `NgOptimizedImage`.
- [ ] No full-library imports where a subpath exists.

## Tests

- [ ] New behaviour and bug fixes have tests.
- [ ] Tests assert user-visible behaviour, not implementation details.
- [ ] Edge cases and error paths covered.
