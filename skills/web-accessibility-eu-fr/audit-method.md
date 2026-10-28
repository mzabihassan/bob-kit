# Audit and review method

## Scope

Agree on: the reference (see `standards.md`), the pages or screens (sample), the states to test (empty, error, loading, logged in, open dialog or menu), the breakpoints (desktop and 320 CSS px wide), and where the report goes. For a review, the scope is the diff and the components it touches.

## Protocol

1. **Automated pass** on each page and state (see `tooling.md`), summarised with `scripts/axe_summary.py`. It finds a minority of issues; treat it as triage.
2. **Static pass** on the source: targeted searches for the patterns below, in the shared components first (one fix there fixes every page).
3. **Manual pass** on the running app for what automation cannot judge (checklist below). Record what was tested, with which browser and assistive technology.
4. **Confirm before reporting:** every finding has a location and evidence (rule result, code line, or observed behaviour). An axe `incomplete` item is a question, not a finding, until checked. A code smell is a finding only if it makes a criterion's test fail; otherwise list it as an observation, without a criterion.

Static search patterns (adapt the globs to the stack). Combine them into one or two `grep` calls with alternation (for example `outline:\s*(none|0)|tabindex="[1-9]|user-scalable=no|maximum-scale=1`), not one call per pattern:

| Smell | Search |
| --- | --- |
| Clickable non-interactive element | `(click)=` / `onClick=` / `@click=` on `div`, `span`, `li`, `img` |
| Removed focus outline | `outline: none` / `outline: 0` without a `:focus-visible` replacement |
| Positive tabindex | `tabindex="[1-9]` |
| Unlabelled control | `<input`, `<select`, `<textarea` without `<label for>`, `aria-label` or `aria-labelledby` |
| Placeholder as label | `placeholder=` on fields with no label |
| Icon-only button | `<button>` containing only an icon or SVG, no text or `aria-label` |
| ARIA misuse | `role="button"` without `tabindex` and key handling; `aria-hidden="true"` on focusable content |
| Blocked zoom | `user-scalable=no`, `maximum-scale=1` |
| Motion without opt-out | animations with no `prefers-reduced-motion` query |

## Manual checklist (beyond automation)

- **Keyboard**: everything reachable and operable with Tab, Shift+Tab, Enter, Space, arrows, Escape; logical order; no trap; visible focus never hidden by sticky elements; skip link works.
- **Screen reader** (NVDA + Firefox or JAWS + Chrome on Windows, VoiceOver + Safari on macOS/iOS, TalkBack on Android): names, roles and states announced; headings and landmarks give the structure; dynamic messages (errors, toasts, results count) announced; page title changes on SPA navigation.
- **Forms**: visible labels, required fields indicated in text, errors identified in text and linked to the field, focus moved to the first error or an error summary, `autocomplete` on personal data, no time limit without control, redundant entry avoided.
- **Dialogs and widgets**: focus moves into the dialog, stays there, returns to the trigger on close; Escape closes; menus, tabs, comboboxes and accordions follow the ARIA Authoring Practices keyboard model.
- **Visual**: contrast in real context (text on images, hover, focus, disabled, error states); information not conveyed by colour alone; zoom to 200 % and reflow at 320 CSS px without loss; text spacing override (line height 1.5, letter 0.12em, word 0.16em, paragraph 2em) without clipping; target size 24×24 CSS px.
- **Content**: meaningful alternatives (decorative images hidden), language of page and passages, consistent navigation and help, captions and transcripts for media, no flashing.

## Priority

| Priority | Rule |
| --- | --- |
| P1 | Blocks a task for some users on a core journey (cannot log in, submit, pay, close a dialog), or a critical/serious failure of a mandatory criterion |
| P2 | Moderate failure of a mandatory criterion, or a critical/serious failure of a recommended item (WCAG 2.2 addition not yet mandatory, best practice) |
| P3 | Minor failures, and moderate or minor recommended items (best practices, AAA) |

Order the work by priority, then by reach (shared component first) and effort. `axe_summary.py` applies the same P1–P3 rule to automated findings; raise or lower it with what you observed.

## Finding format

`[P1] Checkout — "Payer" button has no accessible name` · WCAG 4.1.2 (A) · RGAA 11.9 · EN 9.4.1.2 · `src/app/checkout/pay-button.component.html:12` · Evidence: axe `button-name`, NVDA reads "bouton" · Impact: screen reader users cannot identify the action · Fix: add visible text or `aria-label="Payer"` · Effort: S · Status: automated / manual / both.

## Report

1. **Scope**: reference and version, pages and states, tools and versions, browsers and assistive technologies, date.
2. **Summary**: P1/P2/P3 counts, the journeys blocked, the three first actions. Never state a compliance level or rate unless a full manual audit of the sample was done with the RGAA method.
3. **Findings** grouped by component or journey, in the format above.
4. **Not tested**: criteria and states not covered (the script lists RGAA criteria with no automated signal), so nobody reads silence as conformance.
5. **Next steps**: fixes in reviewable batches, the regression checks to add (see `tooling.md`), and the RGAA audit or statement work if the organisation needs one.
