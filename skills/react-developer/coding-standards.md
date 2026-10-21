# React coding standards

These are defaults. The project's instructions and observed conventions win: folder layout (feature folders, `components/`/`hooks/`), file naming, styling approach, state and data libraries, form library and test style.

## Components and hooks

- Function components with typed props (`type Props = { … }`), default values through parameters. Keep components focused; extract a custom hook when logic is reused or obscures the markup.
- Follow the Rules of Hooks and the `react-hooks` lint rules; never silence `exhaustive-deps`. A missing dependency is usually a design problem: move the logic into the event handler, derive it during render, or use `useEffectEvent` (19.2+) for non-reactive logic.
- **You might not need an effect**: derive values during render instead of syncing state with `useEffect`; handle user events in handlers; reset state with a `key`; fetch data with the project's data library or framework loaders rather than ad-hoc effects.
- State: keep it minimal and local; lift it only as far as needed; avoid duplicated or derived state. Never mutate state or props: create new objects and arrays.
- Lists have stable, unique `key`s (ids, not array indexes for reorderable lists).
- Memoisation: if the React Compiler is enabled, write plain code. Otherwise use `useMemo`/`useCallback`/`memo` only for measured costs or referential stability that matters (dependencies of effects, memoised children).

## Data, state and forms

- Server state (fetched data) belongs to the project's server-state solution (TanStack Query, SWR, RTK Query, framework loaders or Server Components); client state to local state, Context (for low-frequency values) or the project's store (Redux Toolkit, Zustand). Do not introduce a new library without asking.
- Handle loading, error and empty states for every async view; cancel or ignore stale requests (`AbortController`, the library's built-ins).
- Forms: use the project's form library and validation schemas (e.g. React Hook Form + Zod). With React 19, Actions and `useActionState` are fine for framework or server mutations when the project uses them. Errors are associated with fields (`aria-describedby`, `aria-invalid`).
- API access goes through a typed client or service layer, with base URLs from configuration. Anything in the client bundle, including environment variables exposed by the build tool (`VITE_*`, `NEXT_PUBLIC_*`), is public: never put secrets there.

## Frameworks (when present)

- Next.js App Router: Server Components by default; `'use client'` only on the interactive leaves; never import server-only code (secrets, database) into client components; Server Actions validate inputs and check authorisation like any public endpoint.
- React Router: follow the mode used (library or framework, loaders and actions). Lazy-load routes for large applications.

## Accessibility and security

- Semantic HTML first (`button`, `a href`, `label`, headings); keyboard support and visible focus; ARIA only when there is no native element; target WCAG 2.2 AA. Use the UI kit's accessible components.
- Never use `dangerouslySetInnerHTML` with untrusted content without sanitising it (e.g. DOMPurify); validate URLs from data (`javascript:` links); do not store tokens in `localStorage` when the project uses secure cookies.

## TypeScript

Respect the project's strictness; no new `any`; type events and refs precisely (`React.ChangeEvent<HTMLInputElement>`, `useRef<HTMLDivElement>(null)`); prefer union types for component variants.

## Testing

- Same runner and libraries as the existing tests (Vitest or Jest, Testing Library, MSW, Playwright or Cypress).
- Test behaviour as a user sees it: query by role and label (`getByRole('button', { name: /save/i })`), interact with `@testing-library/user-event`, await async UI with `findBy…`/`waitFor`. Do not test implementation details (state values, internal functions, snapshot dumps of large trees).
- Mock the network at the boundary with MSW (or the project's approach) rather than mocking hooks or modules everywhere; test custom hooks with `renderHook`.
- Every bug fix gets a test that would have caught it. Cover error and empty states, not only the happy path.
- e2e tests for critical user journeys only; keep them independent and deterministic.
