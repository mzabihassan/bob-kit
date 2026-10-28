# Fix patterns

Smallest correct fix first: native HTML before ARIA, the shared component before each page, the project's UI kit mechanism (Angular Material, PrimeNG, MUI, Vuetify…) before custom code. Keep the visual design: a fix that changes appearance (focus ring, contrast, target size) goes through the design tokens, agreed with the user.

## Names, roles and semantics

- Clickable `div`/`span` → `<button type="button">` (actions) or `<a href>` (navigation). If a custom element must stay: `role`, `tabindex="0"`, Enter and Space handlers, and state attributes.
- Icon-only button: visible text if possible, else `aria-label`; the icon gets `aria-hidden="true"`. Images: meaningful `alt`, `alt=""` when decorative; informative inline SVG: `role="img"` plus a text alternative (RGAA 1.1); decorative SVG: `aria-hidden="true"`.
- Structure: one `h1`, headings without skipped levels, `header`/`nav`/`main`/`footer` landmarks, a skip link to `main` (RGAA 12.7), lists as `ul`/`ol`, data tables with `caption` and `th scope`.
- Language: `<html lang="fr">` (or the page language), `lang` on passages in another language. A unique, descriptive `<title>` per page or route.
- ARIA: do not override native semantics, never `aria-hidden="true"` on focusable content, `aria-label` only on interactive elements or landmarks, and keep `aria-expanded`, `aria-selected`, `aria-current` in sync with the state.

## Keyboard and focus

- Never remove the focus indicator; replace `outline: none` with a `:focus-visible` style of 3:1 contrast. No positive `tabindex`; DOM order = visual order.
- Focus not obscured (WCAG 2.2): `scroll-padding-top` equal to the sticky header height; banners and chat widgets must not cover the focused element.
- Dialogs: prefer the UI kit's dialog (Angular Material `MatDialog`, CDK `Dialog`) or native `<dialog>` opened with `showModal()` (focus inside, Escape, inert background). Otherwise: move focus in, trap it (`cdkTrapFocus` in Angular), close on Escape, return focus to the trigger; check the return on every browser in scope.
- SPA navigation: update the page title on each route (Angular route `title`, React Router or Next.js metadata, vue-router `afterEach`) and move focus to the main heading or announce the new page. Next.js App Router includes a route announcer; Angular and Vue need it explicitly.
- Widgets (menu, tabs, combobox, tree, accordion): follow the ARIA Authoring Practices keyboard model, or use a maintained accessible library already in the project.

## Forms

- A visible `<label for>` for every field; group related controls with `fieldset`/`legend`; required fields stated in text (`required` + visible mention).
- Errors: text next to the field, `aria-invalid="true"`, `aria-describedby` pointing to the message; on submit, move focus to the first invalid field or to an error summary with links.
- `autocomplete` on personal data fields (`email`, `given-name`, `tel`, `street-address`…), RGAA 11.13.
- Accessible authentication (WCAG 2.2): never block paste, keep `autocomplete="current-password"` / `one-time-code`, offer an alternative to cognitive puzzles. Redundant entry: pre-fill what the user already gave in the same process.

## Dynamic content

- Status messages (saved, results count, toasts): a live region present in the DOM before the update, `role="status"` (polite) or `role="alert"` (urgent only). Angular: CDK `LiveAnnouncer.announce()`; React and Vue: a shared announcer component.
- Loading: `aria-busy` on the region, and announce the result, not every spinner tick. Do not steal focus on background updates.
- Time limits: let the user extend or disable them; auto-moving content (carousel) gets pause controls.

## Visual

- Contrast (text 4.5:1, large text and UI parts 3:1): fix the token or the component state (hover, focus, disabled, error), not one-off colours. When the fix belongs to the palette, hand over to the `design-system` skill if it is installed, or propose the token change.
- Not by colour alone: add text, an icon or an underline (links in body text).
- Reflow and zoom: no fixed widths on text containers, no `user-scalable=no`, content usable at 320 CSS px and 200 % zoom; text spacing overrides must not clip text (avoid fixed heights).
- Target size (WCAG 2.2): at least 24×24 CSS px through `min-width`/`min-height` or padding, without scaling the icon.
- Dragging (WCAG 2.2): a single-pointer alternative (buttons to move items, an input for a slider value).
- Motion: wrap non-essential animation in `@media (prefers-reduced-motion: reduce)`.

## Framework notes

- **Angular**: `@angular/cdk/a11y` (`FocusTrap`, `FocusMonitor`, `LiveAnnouncer`), Angular Aria where the project uses it, Material's built-in focus management; template lint via angular-eslint `templateAccessibility`.
- **React**: refs and `useEffect` for focus moves after render; `eslint-plugin-jsx-a11y`; component tests with Testing Library queries by role (`getByRole('button', { name: 'Payer' })`), which double as accessibility checks.
- **Vue**: template refs plus `nextTick()` before moving focus; `eslint-plugin-vuejs-accessibility`.
- **Plain HTML/JS**: native elements and `<dialog>`; progressive enhancement for widgets.

After each fix, re-run the affected automated check and repeat the manual step that revealed the issue (keyboard path, screen reader announcement) before calling it fixed.
