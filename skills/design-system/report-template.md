# Report template

Write the report in the user's language, as `design-system-report.md` in the agreed output folder, next to `palette.html` and the token files.

```markdown
# Design system report — <app> (<date>)

## Summary
Stack · files scanned · maturity level <0–4> · the three most important findings, with numbers.

## Key metrics (example values)
| Metric | Value | Target |
| --- | --- | --- |
| Distinct colour values → perceptual groups | 128 → 89 | ≤ 30 semantic tokens |
| Near-duplicate groups | 27 | 0 |
| Colour declarations using tokens | 26 % | ≥ 90 % |
| Spacing values on the 4px grid | 50 % | ≥ 95 % |
| Distinct font sizes | 14 | 6–9 |
| Contrast failures (confirmed) | 5 | 0 |
| Dead tokens / undefined tokens | 12 / 3 | 0 / 0 |

## Palette
Canonical colours with role, uses and contrast; near-duplicate groups to merge (canonical ← variants); colours without a role. Link to `palette.html`.

## Typography · Spacing · Radius · Elevation · Layers · Breakpoints · Motion
For each: what is used, the healthy target scale, the deviations (with counts and examples `file:line`).

## Accessibility
Confirmed contrast failures (pair, ratio, where, accessible alternative and its ratio), focus visibility, reduced motion.

## Components
Inventory of core components: implementations, variants, states, accessibility, documentation; duplicates.

## Declared vs de facto
What the theme or tokens declare versus what the code uses: unused declared values, widely used undeclared values, kit theming bypassed.

## Recommendations (prioritised)
| # | Recommendation | Impact | Effort | Evidence |
| --- | --- | --- | --- | --- |

## Migration plan
Step-by-step, each step reviewable and reversible: 1. add semantic tokens (no visual change); 2. fix contrast failures; 3. map near-duplicates to tokens, area by area; 4. replace hardcoded values (codemod or search-and-replace with review); 5. merge duplicate components; 6. add lint rules and documentation.

## Proposed tokens
Three-tier excerpt (primitive → semantic → component) in W3C DTCG; full file `tokens.proposed.json`; mapping to the stack (CSS variables, Material theme, PrimeNG preset, Tailwind theme, MUI theme).
```

Keep numbers traceable: each metric comes from `extracted.json` or from files you read. Remove sections that do not apply rather than leaving them empty.
