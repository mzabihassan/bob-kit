# React code review checklist

Report each finding with severity (Critical, High, Medium, Low), file and line, the problem, the recommended fix and the reason. Review against the project's own conventions first.

## Severity

- **Critical**: XSS (`dangerouslySetInnerHTML` with untrusted data, unvalidated URLs), secrets in client code, server-only code or data exposed to the client, broken build, crash of a core flow.
- **High**: wrong data shown, stale-state or race bugs, missing cleanup (leaks, duplicate requests), broken accessibility in a core flow, hydration errors, unhandled API errors.
- **Medium**: unnecessary effects or derived state, performance issues with real impact, deprecated APIs, missing tests, inconsistency with project conventions.
- **Low**: naming, style, minor readability.

## Checks

- **Project fit**: follows `AGENTS.md`/rules, lint config, folder layout, state, data and form libraries, styling approach and UI kit already in use.
- **Version fit**: only APIs available in the installed React and framework versions; no removed APIs (`defaultProps` on function components, string refs, `ReactDOM.render`) in code for React 19.
- **Hooks and state**: Rules of Hooks respected; no suppressed `exhaustive-deps`; no effects that only sync or derive state; immutable updates; stable keys; effects clean up.
- **Async UI**: loading, error and empty states; cancelled or ignored stale requests; no `useEffect` fetch waterfalls when a data library or loader exists.
- **Security**: no unsanitised HTML, safe URLs, no secrets in client environment variables, Server Actions and route handlers validate input and check authorisation.
- **Accessibility**: semantic elements, labels, keyboard support and focus management (dialogs, menus), meaningful `alt`, live regions for async messages.
- **Performance**: no expensive work in render without need, lazy-loaded heavy routes and components, no premature memoisation when the compiler is enabled, images sized and optimised.
- **Tests**: behaviour tested through roles and labels, network mocked at the boundary, edge and error cases covered, no brittle snapshots of large trees.
