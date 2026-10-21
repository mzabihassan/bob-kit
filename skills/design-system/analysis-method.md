# Analysis method

## Palette

1. **Near-duplicates**: the script groups colours whose OKLab distance is ≤ 0.03 (barely distinguishable); the most used value is the canonical one. Review the groups: two values may be intentionally different (e.g. hover states); then they are not duplicates but need explicit tokens.
2. **Roles**: from where each colour is used (text, background, border, shadow, token definitions) and from variable names, assign semantic roles: brand or primary, secondary or accent, surfaces (background, card, overlay), text (primary, secondary, disabled, inverse), border or divider, focus, and status (success, warning, error, info). A colour with no clear role and few uses is a candidate for removal.
3. **Ramps**: group remaining colours by hue into ramps (e.g. blue 50–900). Gaps or irregular lightness steps show where a ramp needs regenerating; generate missing steps in OKLCH for perceptually even lightness.
4. **Alpha**: transparent variants (`rgba`, 8-digit hex) usually encode overlays and states; propose explicit tokens (`overlay.scrim`, `state.hover`) instead of ad-hoc alphas.

## Contrast (WCAG 2.2 AA)

- Text: 4.5:1 normal, 3:1 for large text (≥ 24px, or ≥ 18.66px bold). Non-text UI (borders of inputs, icons, focus indicators): 3:1 against adjacent colours.
- The script tests the most used text colours against the most used backgrounds: open the files behind failing pairs to confirm they are really used together. Always check: secondary or placeholder text, disabled states (exempt, but must still be identifiable), text on brand colours (buttons), links, error text, focus rings.
- For each failure, propose the nearest accessible colour in the same hue (adjust OKLCH lightness) and state its ratio.

## Scales

| Scale | Healthy pattern | Findings to report |
| --- | --- | --- |
| Spacing | Few values on a 4px or 8px grid (4, 8, 12, 16, 24, 32, 48, 64) | Off-grid values (7px, 13px, 15px), the number of distinct values, the share on the grid |
| Font size | A modular scale (ratio around 1.125 to 1.333) with 6–9 steps, in `rem` | Too many sizes, sizes 1px apart, px instead of rem (zoom and accessibility) |
| Font weight, line height | 2–4 weights; line heights by role (body around 1.5, headings 1.1–1.3) | Unused weights loaded, inconsistent line heights |
| Radius | 3–5 values (none, sm, md, lg, full) | Many near-identical radii |
| Elevation | 3–5 shadow levels | Many unique shadows |
| z-index | A named layer scale (dropdown, sticky, overlay, modal, toast) | Arbitrary values (999, 9999) |
| Breakpoints | One set shared by CSS and the framework | Several conflicting breakpoint sets |
| Motion | 2–3 durations and easings; `prefers-reduced-motion` respected | Many durations, no reduced-motion handling |

## Tokens and coverage

- **Coverage** per category: share of declarations using tokens (custom properties, SCSS variables, theme references) versus hardcoded values. Report it per category and for the worst folders or components.
- **Hygiene**: tokens defined but never used (dead), used but never defined (broken or defined in a library), tokens whose names describe values (`--blue-500` used as "primary" everywhere) instead of intent.
- **Dark mode / themes**: are colours switched through semantic tokens (one place), or overridden component by component? Count hardcoded colours that would break a dark theme.

## Proposed token architecture (three tiers)

```
primitive   color.blue.600 = #1a73e8          (raw palette, never used directly by components)
semantic    color.action.primary = {color.blue.600}
            color.text.secondary = {color.grey.700}
component   button.primary.background = {color.action.primary}
```
Use W3C DTCG JSON (`$value`, `$type`, aliases `{…}`) as the neutral format, then map it to the stack: CSS custom properties, SCSS, Tailwind theme, Angular Material system variables, PrimeNG preset, MUI theme. Names describe intent, use one convention (dot or kebab), and avoid encoding values in names at the semantic tier.

## Maturity level

| Level | Description |
| --- | --- |
| 0 — Ad hoc | Values hardcoded everywhere, no shared tokens |
| 1 — Declared | Tokens or a theme exist, but most code bypasses them |
| 2 — Adopted | Most styles use tokens; near-duplicates and off-scale values remain |
| 3 — Systematised | Semantic tokens, shared components with documented variants and states, contrast checked |
| 4 — Governed | Tokens versioned and built from one source, components documented (Storybook), lint rules (e.g. Stylelint) prevent hardcoded values, changes reviewed |

## Prioritising recommendations

Rank by impact and effort, accessibility first:
1. Contrast failures on core flows (low effort, high impact).
2. Introduce or fix semantic tokens for colours and replace the most used hardcoded values (high impact).
3. Consolidate near-duplicate colours and off-scale spacing or font sizes (medium effort, steady gains).
4. Merge duplicate components (higher effort, high long-term impact).
5. Governance: Stylelint rules (e.g. `color-no-hex` or a plugin enforcing tokens), documentation, token pipeline (Style Dictionary).
