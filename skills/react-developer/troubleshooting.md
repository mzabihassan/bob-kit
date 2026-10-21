# React troubleshooting

Method: reproduce, then read the exact message and the component stack (React DevTools, owner stacks in 19.1+), find the root cause, apply the minimal fix and verify.

## Runtime

| Symptom | Cause | Fix |
| --- | --- | --- |
| "Too many re-renders" / "Maximum update depth exceeded" | State set during render, or an effect that updates its own dependency | Move the update to an event handler; derive the value during render; fix the dependency (often an object or function recreated each render) |
| Effect runs twice in development | StrictMode remounting effects (React 18+) | Expected: make the effect idempotent with a proper cleanup (abort fetches, unsubscribe) |
| Stale values in callbacks, timers or listeners | Closure captured an old render's values | Correct dependencies, the functional updater `setX(x => …)`, a ref for the latest value, or `useEffectEvent` (19.2+) |
| "Cannot update a component while rendering a different component" | A child calls a parent's setter during render | Call it in an effect or an event handler, or lift the computation |
| "Rendered more/fewer hooks than expected" | A hook called conditionally or after an early return | Call hooks unconditionally at the top level |
| List items keep the wrong state, or inputs lose focus | Missing or unstable `key` (index, random) | A stable id as the key; never generate keys during render |
| "Can't perform a React state update on an unmounted component", memory leaks | Async work not cancelled | `AbortController` or the data library's cancellation; clean up subscriptions |
| Hydration mismatch (SSR, Next.js) | Different output on server and client: dates, random ids, `window`/`localStorage` during render, invalid HTML nesting, browser extensions | Deterministic render (`useId` for ids), browser-only code in effects or client components, valid nesting; `suppressHydrationWarning` only for intentional differences such as timestamps |
| "Objects are not valid as a React child" | Rendering an object or a Date | Render a field or a formatted string |
| A prop is unexpectedly `undefined` after upgrading to 19 | `defaultProps` on a function component is ignored | Default parameters |
| "Invalid hook call" | Two copies of React (linked packages, monorepo), or a hook outside a component | `npm ls react` and dedupe; call hooks only in components or custom hooks |

## Tests

| Symptom | Cause | Fix |
| --- | --- | --- |
| "An update … was not wrapped in act(…)" | Async state updates after the test's assertions | `await` user events, use `findBy…`/`waitFor`, mock timers properly; do not wrap everything in `act` blindly |
| Element not found but it is on screen | Querying before an async render, wrong role or name | `findByRole`, check the accessible name with `screen.debug()` or `logRoles` |
| Network calls in tests | Real `fetch` | MSW handlers (or the project's approach); fail on unhandled requests |
| Flaky timers | Real timers or mixed fake timers | Use the runner's fake timers consistently with `user-event`'s `advanceTimers` option |

## Build and bundle

- TypeScript errors after upgrading `@types/react`: run the types codemod; fix `useRef`, `JSX` namespace and children typing issues.
- Environment variables are `undefined`: the wrong prefix for the build tool (`VITE_*`, `NEXT_PUBLIC_*`), or `process.env` used in a Vite client bundle.
- Large bundle: analyse it (`vite-bundle-visualizer`, `@next/bundle-analyzer`, `source-map-explorer`); lazy-load routes and heavy components (`React.lazy`, `next/dynamic`); import only the needed parts of libraries (icons, date and chart libraries).
