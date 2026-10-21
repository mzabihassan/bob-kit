# React migration playbook

Respect the project's upgrade policy. Never commit or push unless the user explicitly asks; pause after each step so the user can review and commit.

## Pre-flight

1. Record the versions (`npm ls react react-dom @types/react typescript`), Node version and current branch; the working tree should be clean (ask the user to commit or stash; never discard).
2. Type check, lint, tests and production build must pass **before** upgrading. If they already fail, stop and report.
3. Check every React-dependent library (UI kit, router, state, forms, testing libraries, charts, editors) for a release that supports the target version (peer dependencies, changelogs). Flag blockers first. Enzyme has no official adapter for React 18+: plan its replacement with Testing Library first.
4. One major step at a time; build, test and run the app after each step.

## React 17 → 18

- Replace `ReactDOM.render` with `createRoot(container).render(...)` (and `hydrate` with `hydrateRoot`).
- Automatic batching can change timing that tests or code relied on; `flushSync` only where truly needed.
- StrictMode in development now mounts, unmounts and remounts effects: effects without proper cleanup (subscriptions, timers, fetches) misbehave. Fix the cleanup instead of removing StrictMode.
- Update `@testing-library/react` (13+), and `@types/react` (children are no longer implicit in `React.FC`).

## React 18 → 19

1. Upgrade to **18.3** first and fix every deprecation warning.
2. Upgrade `react`, `react-dom`, `@types/react`, `@types/react-dom` together, plus libraries requiring it.
3. Run the codemods: `npx codemod@latest react/19/migration-recipe` (render APIs, string refs, legacy context…) and `npx types-react-codemod@latest preset-19 ./src` for type changes. Review every change.
4. Pitfalls:
   - **`defaultProps` on function components is silently ignored**: props become `undefined`. Convert to default parameters (search the code base, including libraries you own).
   - `propTypes` checks no longer run: rely on TypeScript.
   - `useRef()` needs an argument in the types; ref callbacks must not implicitly return a value; the global `JSX` namespace moved to `React.JSX`.
   - `react-test-renderer/shallow` is gone; `act` is imported from `react`.
   - Libraries that read `element.ref` or use removed APIs fail at runtime: upgrade or replace them.
5. `forwardRef` keeps working; migrating to `ref` as a prop is optional modernisation, done separately.

## Tooling and architecture migrations

- **Create React App → Vite** (CRA is deprecated): create the Vite config with the React plugin, move `index.html` to the root with a module script, rename `REACT_APP_*` variables to `VITE_*` (`import.meta.env`), replace `process.env` usages, set up aliases, SVG and asset handling, the proxy and Jest → Vitest (or keep Jest with its own config). Compare the production bundles and the behaviour.
- **React Router v6 → v7**: enable the v6 *future flags* one by one and fix warnings, then upgrade; imports move to `react-router`. Framework mode (formerly Remix) is a separate, optional migration.
- **Next.js Pages Router → App Router**: incremental, route by route (both routers coexist); data fetching moves to Server Components or route handlers; check caching semantics for the installed Next.js version.
- **Class → function components, Redux → Redux Toolkit, Context → a store**: only when asked or planned, one area at a time, with tests that pin the behaviour first.
- **Enabling the React Compiler**: start with the lint rules (fix the violations they report, which are also bugs), enable it on a directory or with opt-in annotations, measure, then widen; `"use no memo"` opts a component out while investigating.

## After each step

Type check, lint, unit tests, production build, and a manual or e2e pass over the risk areas: forms, routing and navigation, data loading and error states, authentication flows, components relying on refs or third-party widgets, SSR/hydration if used.
