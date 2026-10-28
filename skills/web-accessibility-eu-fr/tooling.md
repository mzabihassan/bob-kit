# Tooling

Use what the project already has. Adding a dependency, or running `npx` on a package that is not installed (it downloads code), needs the user's agreement.

## Detect

Look in `package.json` (and the lockfile for versions):

| Found | Use it for |
| --- | --- |
| `@playwright/test` + `@axe-core/playwright` | Page and state scans on the running app (preferred) |
| `cypress` + `cypress-axe` | Same, inside Cypress |
| `jest-axe` / `vitest-axe` with Testing Library | Component-level checks in unit tests |
| `@storybook/addon-a11y` | Component checks per story |
| `eslint-plugin-jsx-a11y`, angular-eslint `templateAccessibility`, `eslint-plugin-vuejs-accessibility` | Static template rules: run the project's lint |
| `pa11y` / `pa11y-ci`, `lighthouse` / `@lhci/cli` | URL scans already wired in CI |
| Playwright without the axe package | Propose `@axe-core/playwright` as a dev dependency (one package, reuses the browsers) |

Nothing at all: propose the smallest option for the need (Playwright + `@axe-core/playwright` for an app, `@axe-core/cli` for a few public URLs) and wait for agreement.

## Run and save results

Scan every page **and state** in scope (open the dialog, trigger the validation errors, expand the menu, log in), at desktop and mobile widths. Write raw results to an agreed folder outside the source tree (or git-ignored), then read only the summary: raw axe JSON is large.

Playwright:

```ts
import AxeBuilder from '@axe-core/playwright';
const results = await new AxeBuilder({ page }).analyze();       // default rule set, includes best practices
fs.writeFileSync(`a11y-results/${name}.json`, JSON.stringify(results));
```

Narrow with `.withTags([...])` only when asked: `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa` for WCAG; `RGAAv4` for the rules mapped to RGAA (axe-core 4.11+); `EN-301-549` for EN 301 549. `.include('#main')` / `.exclude(...)` to scope a component.

CLI, for public URLs: `axe <url> --save <file>.json` (add `--tags`, `--load-delay=2000` for slow SPAs). Unit tests: `expect(await axe(container)).toHaveNoViolations()` (jest-axe; vitest-axe is equivalent). Cypress: `cy.injectAxe(); cy.checkA11y();`.

Summarise:

```
python3 scripts/axe_summary.py a11y-results/*.json --out a11y-report/     # path relative to the skill directory
```

It writes `summary.md` (prioritised table with WCAG, RGAA and EN 301 549 mappings, `incomplete` items to review, RGAA criteria without automated signal) and `summary.json`. It accepts axe results objects, arrays of them (CLI output) or any JSON that contains them.

## What tools do not tell you

- axe aims for **few false positives, at the price of many false negatives**: it cannot judge alternative text quality, focus order, keyboard operability of custom widgets, meaningful sequence, announcements, or most WCAG 2.2 additions beyond target size.
- `incomplete` items (contrast over images or gradients, hidden content) need a human decision.
- Lighthouse's accessibility score runs a subset of axe; a score of 100 says nothing about conformance.
- Pa11y's default runner (HTML_CodeSniffer) reports differently from axe; use `--runner axe` to compare like with like.
- Never report "RGAA compliant" or "WCAG conformant" from tools. Report "no automated violation found on N pages and states", plus the manual checks done.

## Regression guard

After fixes, propose one cheap guard in the project's own test stack: an axe check on the fixed pages or components (`toHaveNoViolations`, or a Playwright test failing on new `critical`/`serious` violations), and the lint rules above if the project has ESLint but not the accessibility preset. Add it only with agreement.
