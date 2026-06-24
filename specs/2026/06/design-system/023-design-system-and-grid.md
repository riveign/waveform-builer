# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Kiku's UI lacks a design system: 6+ inconsistent button styles, ad-hoc spacing, no
spacing/type scale, no grid, and incomplete accessibility. Build a proper, tokenized
design system and component library for the Svelte 5 frontend — grounded in research of
established design systems — so the whole app keeps consistent proportions, meets
accessibility standards, and shares a single source of visual truth. Replace the current
cyan accent with **deep pine green** as the main color. Ship a standalone
`/design-system` showcase route to review the system in isolation **before** migrating
the rest of the app.

## Mid-Level Objectives (MLO)
- **RESEARCH** established design systems (Material 3, Radix, Tailwind, shadcn/ui, IBM
  Carbon, Shopify Polaris) as a base — extract patterns for token architecture, spacing
  & type scales, the grid, focus/a11y handling, and component API design.
- **BUILD** a token layer as CSS custom properties: a full **pine** color ramp, a spacing
  scale, a type scale, radius, and elevation. Dark-only theme, but use **semantic** token
  naming (e.g. `--surface`, `--on-surface`, `--accent`) so values trace back to a small
  primitive palette.
- **DEFINE** a clear **12-column grid system** plus a thin layout/spacing utility layer
  (`.stack`, `.cluster`, grid helpers) for consistent proportions across the app.
- **CREATE** shared Svelte primitives — at minimum `Button` (variants/sizes/states incl.
  visible focus rings), `Stack`, `Grid` — to replace the fragmented per-component buttons.
- **ENSURE** accessibility: visible focus rings on every interactive element, WCAG AA
  contrast for pine-on-dark, keyboard navigation, correct ARIA.
- **ADD** a standalone `/design-system` showcase route that exercises every token,
  utility, and primitive in isolation, before any app-wide migration.

## Details (DT)

### Current State
- Frontend: SvelteKit + Svelte 5 runes, TypeScript, adapter-static, SSR off.
- Styling: pure scoped Svelte `<style>` blocks + 16 CSS variables in `src/app.css`. No
  Tailwind, no PostCSS, no CSS framework.
- Current palette is a **dark** theme with cyan accent `--accent: #00CED1`.
- 76 components under `src/lib/components/`, grouped by domain (set/, hunt/, dna/,
  library/, tinder/, waveform/, player/). No shared `Button`. Buttons differ in padding
  (3×8 / 4×10 / 5×10 / 6×14 / 8×16), radius (3/4/6px), and font-size (11/12/13px).
- Spacing is ad-hoc: 4/6/8/12/16px scattered, no scale. Radius ad-hoc: 3/4/6/8px.
- Routing is a flat SPA — one `+page.svelte`, views switched inside `Workspace.svelte`.
  A new route slots in at `src/routes/design-system/+page.svelte`.
- A11y partial: ARIA roles/labels exist; custom buttons lack visible focus rings.

### Pine Palette (decided)
- Primary `#1F6F54`, hover `#25855E`, press/dim `#185C45`, light tint/on-accent `#3FB489`.
- Build a full ramp (e.g. 50→900) around these so semantic tokens can reference steps.
- Pine **replaces** cyan as the main action color. Keep energy colors
  (low/mid/high) and the coral destructive color unless research says otherwise.

### Tooling Decision (LOCKED — do not re-litigate)
- Enhance the existing **CSS-variable token system** + a **thin hand-rolled grid/utility
  layer** + **shared Svelte primitives**.
- **NO Tailwind. NO new build dependencies.**
- Migrate the 76 components **gradually** AFTER the showcase proves the system. This spec
  delivers the foundation + showcase, not the full migration.

### Constraints
- Minimal changes; DO NOT OVERCOMPLICATE; DO NOT OVERSIMPLIFY.
- Efficiency in UX/perf reflected in every implementation.
- Follow Kiku branding & voice (BRANDING.md / CLAUDE.md): the showcase copy uses Kiku
  voice (set/flow/your library, not playlist/sequence/data).
- Dark-only theme; tokenized for possible future light mode but not building it now.
- Frontend type-check must pass: `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`.

### Out of Scope (this spec)
- Migrating all 76 existing components to the new primitives (gradual, follow-up work).
- Light theme.
- Any backend / Python changes.

### Testing
- **Type-check**: `npx svelte-check` clean after changes.
- **Visual/manual**: `/design-system` route renders every token swatch, the spacing &
  type scales, the 12-col grid demo, and all `Button` variants/sizes/states.
- **A11y**: keyboard-tab through the showcase shows a visible focus ring on every
  interactive element; verify pine-on-dark text/contrast meets WCAG AA (document ratios).

## Behavior
You are a senior frontend engineer and design-systems practitioner. Plan and implement the
most effective, efficient, accessible, and well-formed changes to achieve the objectives
above. Ground decisions in the RESEARCH stage; respect the locked tooling decision; keep
the footprint minimal and the showcase honest (every claim in the showcase must be real).

# AI Section
Critical: AI can ONLY modify this section.

## Research

Synthesis of four parallel research streams (token architecture, scales & grid,
accessibility, pine ramp) plus two prior review reports. All three review MUST-FIX
blockers are resolved below. Report paths under
`tmp/mux/20260624-1436-spec-023-research/research/` and
`tmp/mux/20260624-1431-spec-023-review/review/`.

### 1. Reference Systems (what we borrowed)

| System | Contribution we adopt |
|---|---|
| **Radix Colors** | The 12-step scale where the *same step number = same UI role* across every palette: bg(1–2) → subtle bg(3) → UI fill(4–5) → borders(6–8, 8=focus) → solid brand(9–10) → text(11–12). Resolves "brand fill = step 9, brand *text on dark* = step 11/12". |
| **Radix Themes** | The `accentColor` indirection: components read `--accent-9..12`; one variable re-points which ramp those resolve to. This is the exact pine-flip mechanism, reproduced in plain CSS. |
| **Material 3** | The `on-*` pairing — every surface/fill names its own legible foreground (`--on-accent`). This is how the showcase proves contrast per-token. |
| **IBM Carbon** | Dark `$layer` model: surfaces lighten with each nesting level. Kiku's existing `--bg-primary→secondary→tertiary→hover→active` ladder IS already a Carbon layer model — formalize as `--surface-1..3`, don't reinvent. Plus the 2px spacing mini-unit for density. |
| **shadcn/ui** | Pure CSS-var `base`/`-foreground` pairs (no scale numbers) + the `--ring` and `--radius` tokens — the most direct fit for a no-Tailwind hand-rolled system. |
| **Polaris / EightShapes** | The 3-tier taxonomy (Global→Alias→Component = primitive→semantic→component) and `category-role-variant-state` naming. |

Depth: `research/001-token-architecture.md`.

### 2. Recommended Token Taxonomy (3 tiers)

`--<category>-<role>[-<variant|state>]`, kebab-case, no namespace prefix (single app).
Components consume **Tier 2 only**; primitives never referenced directly.

- **Tier 1 — Primitives**: `--pine-50..950` (table §4), parallel `--cyan-500/600` (kept for reversible flip), `--gray-50..950` (formalized from existing `--bg-*`/`--text-*`), status `--green-500`/`--orange-500`/`--red-500`/`--coral-500`.
- **Tier 2 — Semantic**: surfaces `--surface-1..3` + `--surface-hover/active/waveform`; foreground `--text-1..4`; accent via indirection `--accent-9/10/11` + `--accent-contrast`, role aliases `--accent`/`--accent-hover`/`--accent-text`/`--on-accent`; borders `--border-subtle/strong`; `--focus-ring`; status `--energy-low/mid/high` + `--destructive`.
- **Tier 3 — Component** (tiny — Button only, since 6+ button geometries is the core pain): `--btn-bg`/`--btn-bg-hover`/`--btn-fg`/`--btn-radius`/`--btn-focus`.

**Existing-20-var aliasing map** (all 20 live vars stay defined, re-pointed → **zero of the 76 components change**; verified in `frontend/src/app.css:2-21`):

| Legacy var (keep, alias) | New semantic target | Notes |
|---|---|---|
| `--bg-primary` | `var(--surface-1)` | app bg |
| `--bg-secondary` | `var(--surface-2)` | panels |
| `--bg-tertiary` | `var(--surface-3)` | inputs / raised |
| `--bg-hover` | `var(--surface-hover)` | |
| `--bg-active` | `var(--surface-active)` | |
| `--border` | `var(--border-subtle)` | |
| `--border-focus` | `var(--border-strong)` | |
| `--text-primary` | `var(--text-1)` | |
| `--text-secondary` | `var(--text-2)` | |
| `--text-tertiary` | `var(--text-3)` | |
| `--text-dim` | `var(--text-4)` | |
| `--accent` | `var(--accent-9)` | **stays cyan until deliberate flip** |
| `--accent-dim` | `var(--accent-10)` | |
| `--accent-coral` | `var(--destructive)` | |
| `--energy-low` | `var(--energy-low)` | name == legacy; keep |
| `--energy-mid` | `var(--energy-mid)` | |
| `--energy-high` | `var(--energy-high)` | |
| `--waveform-bg` | `var(--surface-waveform)` | |
| `--panel-width` | unchanged (`500px`) | layout primitive, not color |
| `--header-height` | unchanged (`48px`) | layout primitive |

### 3. Pine Flip Strategy (RESOLVES review MUST-FIX #1 — flip recolors everything)

The flip is decoupled at the **token** level via Radix-style `accentColor` indirection.
Three moving parts:

1. **Both ramps exist as primitives** — `--cyan-*` and `--pine-*` defined unconditionally in `:root`. Defining pine costs nothing visually; nothing references it yet.
2. **One source-of-truth indirection** in `:root`: `--accent-9: var(--cyan-500)` (etc.). Because legacy `--accent` aliases `--accent-9`, all 58 files / 60 `var(--accent)` refs stay cyan. **No flip happens.**
3. **Showcase scopes pine to its own subtree** — `design-system/+page.svelte` sets `data-theme="pine"` on its root and overrides ONLY the accent source within that scope:

```css
[data-theme="pine"] {
  --accent-9:  var(--pine-600);  /* #1F6F54 fill */
  --accent-10: var(--pine-500);  /* #25855E hover */
  --accent-11: var(--pine-400);  /* #3FB489 text-on-dark, 7.50:1 */
  --accent-contrast: #FFFFFF;    /* on-fill label, 6.07:1 — NOT black/#3FB489 */
}
```

CSS custom properties inherit, so every descendant of `[data-theme="pine"]` resolves
pine while the rest of the app still resolves cyan. **True isolation, zero risk to the
76 components.** The later live flip is a **single one-line edit** to the `:root` source
(`--accent-9: var(--pine-600)`) — one reviewable diff, deferred to a separate spec.
Scope via `data-theme` (not a class) so the same mechanism carries an eventual light
theme. Global `:focus-visible` (§5) is also decoupled — fixes a11y app-wide with no
component edits.

### 4. Pine Ramp (50→950, OKLCH-even at hue ~165°)

OKLCH-generated (perceptually uniform, hue-stable — same method as Tailwind v4 / Radix),
the 4 decided anchors snapped to their exact hex. Source: `research/004-pine-ramp.md`.

```css
:root {
  --pine-50:  #E8F8F0;
  --pine-100: #D3F0E2;
  --pine-200: #B5E2CD;
  --pine-300: #8ACDAF;
  --pine-400: #3FB489; /* decided: light tint / text-on-dark */
  --pine-500: #25855E; /* decided: hover */
  --pine-600: #1F6F54; /* decided: PRIMARY action fill */
  --pine-700: #185C45; /* decided: press / dim */
  --pine-800: #164735;
  --pine-900: #123226;
  --pine-950: #0C2018;
}
```

### 5. Contrast / A11y Resolution (RESOLVES review MUST-FIX #2 WCAG + #3 hardcoded `#000`)

All ratios computed via WCAG 2.x relative luminance against bg `#0D0D0D`. Thresholds:
body text 4.5:1 (SC 1.4.3); large text (≥24px / ≥18.66px bold) & UI components /
focus indicators 3:1 (1.4.3 / 1.4.11).

**The role split (the load-bearing a11y fact):**

| Pine token | Hex | vs #0D0D0D | Role — what it MAY do |
|---|---|---:|---|
| `--pine-400` | `#3FB489` | **7.50:1** | **TEXT-on-dark** (AA + AAA body), links, focus geometry. The ONLY decided hex safe as body text on dark. |
| `--pine-500` | `#25855E` | 4.25:1 | hover fill, large-text/UI accent (≥3:1). FAILS body text. |
| `--pine-600` | `#1F6F54` | **3.20:1** | **UI/large-text/solid fills ONLY** — button bg, borders, large headings. **NEVER body text.** |
| `--pine-700` | `#185C45` | 2.46:1 | press/dim fill, subtle border. Non-text only. |

**Button label = white, not black.** Text ON `--pine-600 #1F6F54`:
`#FFFFFF` = **6.07:1** (AA ✓) → `--on-accent: #FFFFFF`. The current hardcoded
`color:#000` = **3.20:1 → FAILS**; `#3FB489` on the fill = 2.59:1 → also fails. The old
cyan+black was 10.75:1, so the recolor silently regresses unless `#000`→white. The
hardcoded `#000` in `set/BuildProgress.svelte:304` and `set/BuildSetDialog.svelte:887`
must adopt `--on-accent` or they ship at 3.20:1 (flag for the in-scope showcase /
proof-of-adoption button).

**Focus ring — systemic fix** (today: `0` `:focus-visible`, `10` `outline:none`). Use
`outline` + `outline-offset` so the ring sits in the gap against the page bg (not the
fill — a pine-tint ring directly on the pine fill is only ~2.3–3.2:1). `--focus-ring`
candidates: `#5FD0A8` (10.25:1 vs bg, 3.20:1 vs pine fill — clears 3:1 both sides), or
`--pine-400 #3FB489` (7.50:1 vs bg). Global rule, specificity 0 so components can still
override:

```css
:root { --focus-ring: #5FD0A8; --focus-ring-width: 2px; --focus-ring-offset: 2px; }

:where(a, button, input, select, textarea, [tabindex]):focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
:focus:not(:focus-visible) { outline: none; }
```

`:focus-visible` (keyboard/AT, not mouse), 2px+ offset → meets SC 2.4.13. Native
`<button>` in the Button primitive picks this up automatically. Depth:
`research/003-accessibility.md`.

### 6. Scale Tokens (spacing / type / radius / elevation / motion)

**Spacing** — 4px hybrid with a 2px mini-unit (Carbon density model); every current ad-hoc value (`4/6/8/12/16`) lands on a step, so these are additive aliases with zero relayout churn:

```css
--space-0:0; --space-px:1px; --space-2xs:2px; --space-xs:4px; --space-sm:6px;
--space-md:8px; --space-lg:12px; --space-xl:16px; --space-2xl:20px; --space-3xl:24px;
--space-4xl:32px; --space-5xl:48px; --space-6xl:64px;
```
(Series: 0,1,2,4,6,8,12,16,20,24,32,48,64. A `--space-40px` step can be added in PLAN if needed; current UI does not use 40px in-component.)

**Type** — compact, integer-snapped, ~1.2 ratio at the readable end, anchored at 12px body:

| Token | px | line-height | maps current |
|---|---|---|---|
| `--text-2xs` | 10 | 1.45 | 9→10 (promote), 10 |
| `--text-xs` | 11 | 1.45 | 11 |
| `--text-sm` | 12 | 1.4 | 12 (body default) |
| `--text-base` | 13 | 1.4 | 13 |
| `--text-md` | 14 | 1.4 | 14 |
| `--text-lg` | 16 | 1.3 | new |
| `--text-xl` | 20 | 1.2 | new |
| `--text-2xl` | 24 | 1.2 | new |

Weights: `--font-weight-regular:400 / -medium:500 / -semibold:600`. The 9px→10px promotion is a PLAN sign-off item (a11y vs exact density).

**Radius** — collapse `2/3/4/6/8/10/12` chaos → 5 + full:
```css
--radius-xs:2px; --radius-sm:4px; --radius-md:6px; --radius-lg:8px; --radius-xl:12px;
--radius-full:9999px;
```

**Elevation** — border-first (drop-shadows read poorly on `#0D0D0D`): `--elev-0:none` (border only), `--elev-1` raised panel, `--elev-2` dropdown, `--elev-3` modal; border tokens `--border-subtle/default/strong` as 1px rgba whites. Real shadow reserved for floating layers only.

**Motion** — `--dur-fast:120ms / --dur-base:200ms / --dur-slow:320ms` + Material-3 easings (`--ease-standard/decelerate/accelerate`); all collapse to `0.01ms` under `prefers-reduced-motion: reduce` (token-driven so no component touches a literal). Depth: `research/002-scales-and-grid.md`.

### 7. 12-Column Grid + Utilities

The 12-col grid does **NOT** apply to the app shell (`display:flex; height:100vh`) or the
fixed two-pane `grid-template-columns: var(--panel-width) 1fr` (`--panel-width:500px`) —
those are intentionally fixed. The grid is an **opt-in `.grid-12` utility** for content
inside the `1fr` pane and the `/design-system` showcase. **Flexbox stays** for the shell,
toolbars, and most component-internal layout.

- `.grid-12` → `display:grid; grid-template-columns: repeat(12, minmax(0,1fr)); gap: var(--grid-gutter, var(--space-4xl))`. `minmax(0,1fr)` prevents track blowout from long track titles. `.grid-12--condensed` → 16px gutter.
- `.col-span-1..12` → `grid-column: span N`.
- `.stack` → `flex-direction:column; gap: var(--stack-gap, var(--space-md))` (Every-Layout, gap edition) + `--xs/sm/lg/xl` variants.
- `.cluster` → `flex-wrap:wrap; align-items:center; gap: var(--cluster-gap, var(--space-sm))` (chip rows, button groups) + `--between/end` justify + gap variants.

Svelte `<Stack>`/`<Grid>` primitives render a `div` with these utility classes and map a
`gap`/`columns` prop to the CSS custom property — primitive and raw utility share ONE
implementation, no duplicate CSS.

### 8. Corrections & Open Decisions for PLAN

**Factual correction (HUMAN-SECTION — cannot be edited by AI):** Current State line 36
says "16 CSS variables"; the actual count is **20** (verified `frontend/src/app.css:2-21`;
both reviews flagged this). The aliasing map in §2 enumerates all 20. **Flag for the human
to correct "16" → "20" in the Human Section** (AI is forbidden from editing it).

**Decisions deferred to PLAN:**
- Pin the final `--focus-ring` value (`#5FD0A8` vs `--pine-400 #3FB489`).
- Confirm `--on-accent: #FFFFFF` (not black, not `#3FB489`) and decide whether the two hardcoded-`#000` accent buttons are fixed in-scope (proof-of-adoption) or deferred.
- Decide the 9px→10px type promotion.
- Enumerate the exact Tier-3 Button token set + the variant×size×state matrix (variants primary/secondary/ghost/danger; sizes sm/md/lg; states default/hover/active/focus/disabled/loading) the showcase must render.
- Decide which content route(s) adopt `.grid-12` first (showcase is mandatory; an in-app pane is optional).
- Confirm `--accent` stays cyan this spec; the live cyan→pine flip + per-component migration ships as a separate, deliberate spec (review 002 Sequencing step 6).

### 9. Sources

- `tmp/mux/20260624-1436-spec-023-research/research/001-token-architecture.md` — 3-tier taxonomy, aliasing map, flip mechanism.
- `tmp/mux/20260624-1436-spec-023-research/research/002-scales-and-grid.md` — spacing/type/radius/elevation/motion + grid utilities.
- `tmp/mux/20260624-1436-spec-023-research/research/003-accessibility.md` — contrast math, focus-visible, ARIA/keyboard, acceptance gates.
- `tmp/mux/20260624-1436-spec-023-research/research/004-pine-ramp.md` — OKLCH ramp derivation + contrast matrix.
- `tmp/mux/20260624-1431-spec-023-review/review/001-spec-quality.md` / `002-technical-feasibility.md` — the 3 resolved MUST-FIXes.
- Radix Colors/Themes: https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale , https://www.radix-ui.com/themes/docs/theme/color
- Material 3 color roles: https://m3.material.io/styles/color/roles ; type: https://m3.material.io/styles/typography/applying-type
- IBM Carbon: https://carbondesignsystem.com/elements/color/overview/ , /elements/spacing/overview/ , /elements/2x-grid/overview/
- shadcn/ui theming: https://ui.shadcn.com/docs/theming ; EightShapes naming: https://medium.com/eightshapes-llc/naming-tokens-in-design-systems-9e86c7444676
- Every Layout (Stack/Cluster): https://every-layout.dev/layouts/stack/
- WCAG: SC 1.4.3 https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html , SC 1.4.11 https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html , SC 2.4.13 https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html
- MDN `:focus-visible` / `prefers-reduced-motion`: https://developer.mozilla.org/en-US/docs/Web/CSS/:focus-visible

## Plan
<!-- Filled by /spec PLAN -->

## Plan Review
<!-- Filled if required to validate plan -->

## Implement
<!-- Filled by /spec IMPLEMENT -->

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
