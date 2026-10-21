# Where the declared system lives

Read these before judging the code: they define what the team *intended*. Versions matter (theming APIs changed a lot); check the installed version's docs via Context7 when available.

| Stack | Where to look | Notes |
| --- | --- | --- |
| Plain CSS / SCSS | `:root { --… }` blocks, `_variables.scss`, `_tokens.scss`, SCSS maps (`$colors: (…)`), mixins for typography and breakpoints | The script lists custom properties defined but never used, and used but never defined |
| Angular Material | Theme SCSS: M2 `mat.define-palette` / `mat.define-light-theme`; M3 (experimental in 17.2, stable from 18) `mat.define-theme`, or the `mat.theme(…)` mixin on recent versions, with system variables `--mat-sys-*`; component overrides (`mat.button-overrides` etc. on recent versions) | Map recommendations onto the theme API and system variables instead of overriding component CSS |
| PrimeNG | Recent versions: design-token presets (`definePreset`, Aura/Lara/Nora) with primitive, semantic and component tokens; older versions: theme CSS files and SCSS variables | Its token tiers map directly to the three-tier proposal |
| Tailwind CSS | v3: `tailwind.config.js` (`theme` / `theme.extend`); v4: `@theme { --color-…; }` in CSS; plugins | Arbitrary values (`text-[#123456]`, `p-[13px]`) bypass the theme: the script counts them |
| React + MUI | `createTheme({ palette, typography, spacing, shape, breakpoints, components })`; `sx` props and `styled()` calls | Hardcoded values in `sx` are the usual drift |
| styled-components / Emotion | `ThemeProvider` theme object; tagged template literals | Values not coming from `props.theme` are hardcoded |
| Bootstrap | SCSS variable overrides before the import (`$primary`, `$spacer`, `$grid-breakpoints`), CSS variables `--bs-*` | |
| IBM Carbon | `@carbon/styles` themes (`white`, `g10`, `g90`, `g100`) and tokens (`$background`, `$text-primary`, `$layer-*`) | Usage should go through Carbon tokens rather than raw palette values |
| Design-token files | `tokens.json` (W3C DTCG `$value`/`$type`), Tokens Studio exports, Style Dictionary configuration | The best source of truth when they exist and are actually built into the code |
| Brand guidelines / Figma | PDF or Confluence brand guide, Figma library (through an MCP server if configured) | Compare the brand palette with the code's canonical colours |

## Component inventory

- Angular: `@Component` selectors in shared or UI libraries (`grep -rn "selector:" --include=*.ts`), Angular Material and PrimeNG components used in templates (`<mat-…>`, `<p-…>`), `*.stories.ts`.
- React: exported components in `components/`, `ui/` or design-system packages, UI kit imports (`@mui/material`, …), `*.stories.tsx`.
- For each core component (button, input, select, checkbox, dialog, table, card, alert or toast, tabs, navigation): the number of implementations, variants, sizes, states (hover, focus-visible, active, disabled, loading, error), keyboard and ARIA support, and whether it is documented (Storybook, README).
- Duplicates are a key finding: several implementations of the same component usually mean several sources of colours and spacing.
