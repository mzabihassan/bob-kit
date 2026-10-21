# Angular code review checklist

Report each finding with severity, file:line, problem, fix and reason. Review against the project's own instructions and conventions first; a deviation from them is a finding even if the code is otherwise idiomatic.

## Severity

- **Critical**: security flaw (XSS via `innerHTML`/`bypassSecurityTrust*`, secrets in code, SSRF), data loss, crash, broken build.
- **High**: memory leak, wrong data shown, broken accessibility in a core flow, OnPush/zoneless bug hiding updates, unhandled API errors.
- **Medium**: performance issue, deprecated API, missing tests, violation of project conventions.
- **Low**: style, naming, readability.

## Checks

- **Project fit**: follows `AGENTS.md`/rules, lint config, folder layout, naming, state library, forms style and UI kit already in use. No new pattern or dependency without a reason.
- **Version fit**: only APIs available in the project's Angular version; experimental APIs flagged; no deprecated APIs in new code.
- **Reactivity**: no in-place mutation of inputs or signal values; `computed` pure; `effect` not syncing signals; every `subscribe` cleaned up; no nested subscribes; lists tracked by a stable key.
- **Async UI**: loading, error and empty states handled.
- **Security**: no untrusted HTML, no hardcoded secrets/URLs, SSR allowed hosts set, no credentialed responses in transfer state.
- **Accessibility**: semantic elements, labelled controls, errors linked via `aria-describedby`, keyboard and visible focus, meaningful `alt`.
- **Performance**: OnPush respected, no costly calls in templates, heavy code lazy (`loadComponent`, `@defer`), `NgOptimizedImage`, no full-library imports.
- **Tests**: new behaviour and fixes tested in the project's style, through user-visible behaviour, including error paths.
