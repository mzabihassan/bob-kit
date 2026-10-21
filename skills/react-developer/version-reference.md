# React API availability (18 → latest)

Check that an API exists in the project's version before generating it. Confirm doubtful cases in `node_modules/@types/react` or on react.dev; for versions newer than this table, read the release notes first.

## By version

| Version | Added or changed |
| --- | --- |
| 18.0 | `createRoot`/`hydrateRoot`, automatic batching everywhere, `useTransition`/`startTransition`, `useDeferredValue`, `useId`, `useSyncExternalStore`, `useInsertionEffect`, streaming SSR with Suspense; StrictMode mounts, unmounts and remounts effects in development |
| 18.3 | Deprecation warnings for everything removed in 19: upgrade to 18.3 first |
| 19.0 | Actions (async functions in transitions), `useActionState`, `useFormStatus` (react-dom), `useOptimistic`, `use()` (promises and context), `ref` as a regular prop (`forwardRef` optional), `<Context>` as provider, ref cleanup functions, `<title>`/`<meta>`/`<link>` hoisting, stylesheet `precedence`, resource preloading APIs (`preload`, `preinit`), Server Components and Server Actions (through frameworks), better hydration error diffs. **Removed**: `propTypes` checks, `defaultProps` on function components, legacy context, string refs, `createFactory`, `ReactDOM.render`/`hydrate`/`unmountComponentAtNode`/`findDOMNode`, `react-test-renderer/shallow`. TypeScript: `useRef` needs an argument, the global `JSX` namespace becomes `React.JSX` |
| 19.1 | Owner stacks in development (`captureOwnerStack`), Suspense and debugging improvements |
| 19.2 | `<Activity mode="visible" \| "hidden">` (keeps hidden UI state, unmounts its effects), `useEffectEvent` (non-reactive logic used by effects), `cacheSignal` (Server Components), partial pre-rendering APIs, React performance tracks in DevTools; `eslint-plugin-react-hooks` with React Compiler rules |

**React Compiler 1.0** (October 2025, stable): build-time automatic memoisation (Babel plugin, also wired through Vite, Next.js and Expo). Works with React 17+ (with `react-compiler-runtime` before 19). When it is enabled, avoid adding manual `useMemo`/`useCallback`/`memo` except where profiling shows a need; follow its lint rules.

**Tooling status**: Create React App is deprecated (February 2025): migrate to Vite or a framework. React Router v7 merged Remix (library mode or framework mode; imports from `react-router`). Next.js versions differ a lot (App Router, caching, middleware, bundler): read the docs of the installed major version.

## Two styles coexist in React 18+ codebases

Follow the style the project uses; do not mix them inside one file.

| Concern | Older style | Current style |
| --- | --- | --- |
| Components | Class components, HOCs, render props | Function components and custom hooks |
| Types | `propTypes`, `defaultProps` | TypeScript props with default parameters |
| Refs | `forwardRef`, callback or `createRef` | `ref` as a prop (19+), `useRef` |
| Context | `<Ctx.Provider>`, `useContext` | `<Ctx>` (19+), `use(Ctx)` (19+) |
| Server data | `useEffect` + `fetch` + local state | TanStack Query/SWR, framework loaders, Server Components (framework) |
| Forms and mutations | Controlled inputs + `onSubmit` handlers, Formik | React Hook Form; Actions + `useActionState`/`useFormStatus` (19+) |
| Global state | Redux (legacy), large Contexts | Redux Toolkit, Zustand, or local state plus server-state libraries |
| Memoisation | Manual `useMemo`/`useCallback`/`React.memo` | React Compiler where enabled; manual only where measured |
| Entry point | `ReactDOM.render` (removed in 19) | `createRoot(container).render(<App />)` |
| Tests | Enzyme (unmaintained), `react-test-renderer` | Testing Library + Vitest/Jest, MSW, Playwright |
