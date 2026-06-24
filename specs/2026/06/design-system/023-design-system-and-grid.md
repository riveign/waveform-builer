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
- Styling: pure scoped Svelte `<style>` blocks + 20 CSS variables in `src/app.css`. No
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

A complete, file-by-file dry-run of IMPLEMENT. Honors all LOCKED decisions: **NO Tailwind,
NO new build deps, dark-only**. The app **stays cyan** after this spec — pine renders only
inside the `[data-theme="pine"]` showcase subtree. The 76 components and the live cyan→pine
flip are **OUT of scope** (deferred to a separate spec).

### Open-decision sign-offs (resolved here, per Research §8)

| Deferred decision | PLAN resolution |
|---|---|
| Final `--focus-ring` value | **`#5FD0A8`** (10.25:1 vs bg `#0D0D0D`; 3.20:1 vs pine-600 fill — clears 3:1 on both sides; pine-400 only clears bg, not the fill). |
| `--on-accent` color | **`#FFFFFF`** (6.07:1 on pine-600). NOT black (3.20:1), NOT pine-400 (2.59:1). |
| 9px→10px type promotion | **YES** — `--text-2xs: 10px` is the floor; no `9px` token. (9px fails practical legibility.) |
| Fix the two hardcoded `#000` accent buttons in-scope? | **NO** — out of scope this spec (those files are among the 76 unmigrated components). The showcase Button primitive ships correct (`--on-accent: #FFFFFF`) as the proof-of-adoption. The `#000` regression only manifests on the deliberate future flip; flagged there. |
| Which route adopts `.grid-12` first | **Only `/design-system`** (mandatory). No in-app pane adopts it this spec. |
| `--accent` stays cyan? | **YES** — `:root` accent source points at `--cyan-*`; confirmed. |

### Files

New files (4):
- `frontend/src/lib/styles/tokens.primitives.css`
  - Tier-1 primitives: `--pine-50..950` (Research §4), `--cyan-500/600` (flip-reversible), `--gray-50..950` (formalized from existing `--bg-*`/`--text-*`), status `--green-500`/`--orange-500`/`--red-500`/`--coral-500`. NO semantic refs here.
- `frontend/src/lib/styles/tokens.semantic.css`
  - Tier-2 semantic: `--accent-source` indirection (`--accent-9/10/11` + `--accent-contrast`), role aliases (`--accent`/`--accent-hover`/`--accent-pressed`/`--accent-text`/`--on-accent`), `--surface-1..3` + states, `--text-1..4`, `--border-subtle/default/strong`, `--focus-ring*`, status semantics, spacing `--space-*`, type `--text-*`/`--lh-*`/`--font-weight-*`, `--radius-*`, `--elev-*`, motion `--dur-*`/`--ease-*` + `prefers-reduced-motion`. Tier-3 `--btn-*`. Global `:focus-visible`.
- `frontend/src/lib/styles/utilities.css`
  - `.grid-12` + `.grid-12--condensed`, `.col-span-1..12`, `.stack` (+variants), `.cluster` (+variants).
- `frontend/src/lib/components/primitives/Button.svelte`
  - Native `<button>` primitive: variant/size/state, focus ring, ARIA, loading/disabled.
- `frontend/src/lib/components/primitives/Stack.svelte`
  - Presentational `<div class="stack">`, `gap` prop → `--stack-gap`.
- `frontend/src/lib/components/primitives/Grid.svelte`
  - Presentational `<div class="grid-12">`, `columns`/`gap`/`condensed` props.
- `frontend/src/routes/design-system/+page.svelte`
  - Showcase route, scopes `data-theme="pine"`.
- `frontend/src/routes/design-system/+page.ts`
  - `export const prerender = false;` (SPA model — matches `+layout.ts`).

Modified files (1):
- `frontend/src/app.css`
  - `@import` the 3 token files at the very top (before `:root`); replace the 20 hardcoded
    var values in `:root` with **aliases** onto the semantic layer; keep `--panel-width`/
    `--header-height` as bare values; update `input:focus`/`select:focus` to keep the new
    global `:focus-visible` ring; keep the existing `button{}` reset.

Cascade / import order (load order matters — primitives must define before semantic references them):
1. `@import './lib/styles/tokens.primitives.css';`  (Tier 1 — raw hexes)
2. `@import './lib/styles/tokens.semantic.css';`    (Tier 2 — references Tier 1)
3. `@import './lib/styles/utilities.css';`           (classes that reference Tier 2)
4. existing `:root { … }` legacy-alias block + resets (references Tier 2)

`@import` rules are valid at the top of `app.css` and resolved by Vite at build — no new
build dep. `+layout.svelte` already does `import '../app.css'`, so all four cascade globally.

### Tasks

#### Task 1 — Create `tokens.primitives.css` (Tier 1)
Tools: editor (new file)
File: `frontend/src/lib/styles/tokens.primitives.css`
Diff:
````diff
--- /dev/null
+++ b/frontend/src/lib/styles/tokens.primitives.css
@@
+/* ===========================================================================
+ * Tier 1 — PRIMITIVES (raw palette). Components NEVER reference these directly;
+ * only tokens.semantic.css does. Defining pine here costs nothing visually until
+ * the accent source re-points (Research §3 flip strategy).
+ * =========================================================================== */
+:root {
+  /* --- Pine ramp (OKLCH-even, hue ~165°; Research §4) --- */
+  --pine-50:  #E8F8F0;
+  --pine-100: #D3F0E2;
+  --pine-200: #B5E2CD;
+  --pine-300: #8ACDAF;
+  --pine-400: #3FB489; /* decided: light tint / text-on-dark (7.50:1 on #0D0D0D) */
+  --pine-500: #25855E; /* decided: hover fill */
+  --pine-600: #1F6F54; /* decided: PRIMARY action fill */
+  --pine-700: #185C45; /* decided: press / dim */
+  --pine-800: #164735;
+  --pine-900: #123226;
+  --pine-950: #0C2018;
+
+  /* --- Cyan ramp (current accent; kept so the flip stays reversible) --- */
+  --cyan-500: #00CED1; /* current --accent */
+  --cyan-600: #00A8AB; /* current --accent-dim */
+
+  /* --- Gray ramp (formalized from existing --bg-*/--text-*) --- */
+  --gray-950: #0D0D0D; /* current --bg-primary */
+  --gray-900: #12121A; /* current --waveform-bg */
+  --gray-850: #1A1B23; /* current --bg-secondary */
+  --gray-800: #242631; /* current --bg-tertiary */
+  --gray-750: #2E3040; /* current --bg-hover */
+  --gray-700: #383A4A; /* current --bg-active */
+  --gray-600: #3F414A; /* current --border */
+  --gray-500: #555555; /* current --border-focus */
+  --gray-400: #666666; /* current --text-dim */
+  --gray-300: #7A7B82; /* current --text-tertiary */
+  --gray-200: #A0A1A7; /* current --text-secondary */
+  --gray-50:  #F5F5F0; /* current --text-primary */
+
+  /* --- Status primitives --- */
+  --green-500:  #4CAF50; /* energy-low */
+  --orange-500: #FF9800; /* energy-mid */
+  --red-500:    #F44336; /* energy-high */
+  --coral-500:  #FF6B6B; /* destructive */
+}
````
Verification: file exists; 11 pine + 2 cyan + 12 gray + 4 status vars. No `var(--…)` references (primitives only).

#### Task 2 — Create `tokens.semantic.css` (Tier 2 + Tier 3 + focus + motion)
Tools: editor (new file)
File: `frontend/src/lib/styles/tokens.semantic.css`
Diff:
````diff
--- /dev/null
+++ b/frontend/src/lib/styles/tokens.semantic.css
@@
+/* ===========================================================================
+ * Tier 2 — SEMANTIC (intent). This is what components SHOULD consume.
+ * Tier 3 (--btn-*), the global :focus-visible rule, and motion live here too.
+ * =========================================================================== */
+:root {
+  /* --- THE FLIP LEVER (Research §3) -------------------------------------
+   * The accent source points at the CYAN ramp in :root, so the live app
+   * stays cyan. The /design-system showcase re-points ONLY these 4 vars
+   * inside [data-theme="pine"]. The future deliberate flip edits these 4
+   * lines here once. */
+  --accent-9:        var(--cyan-500); /* solid brand / action fill */
+  --accent-10:       var(--cyan-600); /* solid hover */
+  --accent-11:       var(--cyan-500); /* accent text on dark (cyan is light enough) */
+  --accent-contrast: #000000;         /* legible foreground ON accent-9 (cyan+black = 10.75:1) */
+
+  /* role aliases components actually use */
+  --accent:          var(--accent-9);
+  --accent-hover:    var(--accent-10);
+  --accent-pressed:  var(--accent-9);  /* cyan has no decided press; reuse fill (pine overrides) */
+  --accent-text:     var(--accent-11);
+  --on-accent:       var(--accent-contrast);
+
+  /* surfaces (Carbon layer ladder) */
+  --surface-1: var(--gray-950);  /* app bg */
+  --surface-2: var(--gray-850);  /* panel */
+  --surface-3: var(--gray-800);  /* raised / input bg */
+  --surface-hover:    var(--gray-750);
+  --surface-active:   var(--gray-700);
+  --surface-waveform: var(--gray-900);
+
+  /* foreground (shadcn/M3 on- pairing) */
+  --text-1: var(--gray-50);   /* primary */
+  --text-2: var(--gray-200);  /* secondary */
+  --text-3: var(--gray-300);  /* tertiary */
+  --text-4: var(--gray-400);  /* dim */
+
+  /* borders (Radix 6/7/8) — solid color tokens for border-color usage */
+  --border-subtle: var(--gray-600);
+  --border-default: var(--gray-600);
+  --border-strong: var(--gray-500);
+
+  /* status */
+  --energy-low:  var(--green-500);
+  --energy-mid:  var(--orange-500);
+  --energy-high: var(--red-500);
+  --destructive: var(--coral-500);
+
+  /* --- Focus ring (Research §5; systemic a11y fix) --- */
+  --focus-ring: #5FD0A8;        /* 10.25:1 vs bg, 3.20:1 vs pine-600 fill — clears 3:1 both sides */
+  --focus-ring-width: 2px;
+  --focus-ring-offset: 2px;
+
+  /* --- Spacing (Research §6; 4px hybrid + 2px mini-unit) --- */
+  --space-0: 0;
+  --space-px: 1px;
+  --space-2xs: 2px;
+  --space-xs: 4px;
+  --space-sm: 6px;
+  --space-md: 8px;
+  --space-lg: 12px;
+  --space-xl: 16px;
+  --space-2xl: 20px;
+  --space-3xl: 24px;
+  --space-4xl: 32px;
+  --space-5xl: 48px;
+  --space-6xl: 64px;
+
+  /* --- Type scale (Research §6; 12px body anchor, 9→10 promoted) --- */
+  --text-2xs: 10px;  --lh-2xs: 1.45;
+  --text-xs:  11px;  --lh-xs:  1.45;
+  --text-sm:  12px;  --lh-sm:  1.4;
+  --text-base:13px;  --lh-base:1.4;
+  --text-md:  14px;  --lh-md:  1.4;
+  --text-lg:  16px;  --lh-lg:  1.3;
+  --text-xl:  20px;  --lh-xl:  1.2;
+  --text-2xl: 24px;  --lh-2xl: 1.2;
+  --font-weight-regular: 400;
+  --font-weight-medium:  500;
+  --font-weight-semibold:600;
+
+  /* --- Radius (Research §6) --- */
+  --radius-xs:   2px;
+  --radius-sm:   4px;
+  --radius-md:   6px;
+  --radius-lg:   8px;
+  --radius-xl:   12px;
+  --radius-full: 9999px;
+
+  /* --- Elevation (Research §6; border-first on dark) --- */
+  --elev-0: none;
+  --elev-1: 0 1px 2px rgba(0,0,0,0.4);
+  --elev-2: 0 2px 8px rgba(0,0,0,0.5);
+  --elev-3: 0 8px 24px rgba(0,0,0,0.6);
+
+  /* --- Motion (Research §6) --- */
+  --dur-fast: 120ms;
+  --dur-base: 200ms;
+  --dur-slow: 320ms;
+  --ease-standard:   cubic-bezier(0.2, 0, 0, 1);
+  --ease-decelerate: cubic-bezier(0, 0, 0, 1);
+  --ease-accelerate: cubic-bezier(0.3, 0, 1, 1);
+
+  /* --- Tier 3 — Component (Button only) --- */
+  --btn-bg:       var(--accent);
+  --btn-bg-hover: var(--accent-hover);
+  --btn-fg:       var(--on-accent);
+  --btn-radius:   var(--radius-sm);
+  --btn-focus:    var(--focus-ring);
+}
+
+/* Global systemic focus ring — specificity 0 so components can still override.
+ * :focus-visible = keyboard/AT only (not mouse). outline+offset keeps the ring in
+ * the gap against the page bg (Research §5). */
+:where(a, button, input, select, textarea, [tabindex]):focus-visible {
+  outline: var(--focus-ring-width) solid var(--focus-ring);
+  outline-offset: var(--focus-ring-offset);
+}
+:focus:not(:focus-visible) { outline: none; }
+
+/* Reduced motion — collapse token durations so no component touches a literal. */
+@media (prefers-reduced-motion: reduce) {
+  :root {
+    --dur-fast: 0.01ms;
+    --dur-base: 0.01ms;
+    --dur-slow: 0.01ms;
+  }
+  *, *::before, *::after {
+    animation-duration: 0.01ms !important;
+    animation-iteration-count: 1 !important;
+    transition-duration: 0.01ms !important;
+    scroll-behavior: auto !important;
+  }
+}
````
Verification: every value here is a `var(--…)` to a Tier-1 primitive OR a scale literal (px/ms/cubic-bezier) OR `--accent-contrast: #000` (the documented on-cyan label). No raw color hex except `--focus-ring`/`--accent-contrast`.

#### Task 3 — Create `utilities.css` (grid / stack / cluster)
Tools: editor (new file)
File: `frontend/src/lib/styles/utilities.css`
Diff:
````diff
--- /dev/null
+++ b/frontend/src/lib/styles/utilities.css
@@
+/* ===========================================================================
+ * Layout utilities (Research §7). Opt-in. The app shell stays flex; the fixed
+ * two-pane `grid-template-columns: var(--panel-width) 1fr` stays as-is. .grid-12
+ * is for content inside the 1fr pane and the /design-system showcase only.
+ * =========================================================================== */
+
+/* ---- 12-column grid (opt-in) ---- */
+.grid-12 {
+  display: grid;
+  grid-template-columns: repeat(12, minmax(0, 1fr)); /* minmax(0,…) prevents track blowout */
+  gap: var(--grid-gutter, var(--space-4xl));
+}
+.grid-12--condensed { --grid-gutter: var(--space-xl); } /* 16px */
+
+.col-span-1  { grid-column: span 1;  }
+.col-span-2  { grid-column: span 2;  }
+.col-span-3  { grid-column: span 3;  }
+.col-span-4  { grid-column: span 4;  }
+.col-span-5  { grid-column: span 5;  }
+.col-span-6  { grid-column: span 6;  }
+.col-span-7  { grid-column: span 7;  }
+.col-span-8  { grid-column: span 8;  }
+.col-span-9  { grid-column: span 9;  }
+.col-span-10 { grid-column: span 10; }
+.col-span-11 { grid-column: span 11; }
+.col-span-12 { grid-column: span 12; }
+
+/* ---- Stack: vertical rhythm via gap ---- */
+.stack {
+  display: flex;
+  flex-direction: column;
+  gap: var(--stack-gap, var(--space-md)); /* 8px default */
+}
+.stack--xs { --stack-gap: var(--space-xs); }
+.stack--sm { --stack-gap: var(--space-sm); }
+.stack--lg { --stack-gap: var(--space-lg); }
+.stack--xl { --stack-gap: var(--space-xl); }
+
+/* ---- Cluster: horizontal group, wraps, gap-based ---- */
+.cluster {
+  display: flex;
+  flex-wrap: wrap;
+  align-items: var(--cluster-align, center);
+  gap: var(--cluster-gap, var(--space-sm)); /* 6px default */
+}
+.cluster--between { justify-content: space-between; }
+.cluster--end     { justify-content: flex-end; }
+.cluster--xs { --cluster-gap: var(--space-xs); }
+.cluster--md { --cluster-gap: var(--space-md); }
+.cluster--lg { --cluster-gap: var(--space-lg); }
````
Verification: classes reference only Tier-2 `--space-*`. No color tokens.

#### Task 4 — Wire token files + alias the 20 legacy vars in `app.css`
Tools: editor
Concise: prepend the 3 `@import`s; convert each of the 20 hardcoded `:root` values to a
semantic alias (zero of the 76 components change — they keep reading the same legacy names);
keep `--panel-width`/`--header-height` literal; keep `font-family`/`color`/`background`;
keep resets; the new global `:focus-visible` (Task 2) now governs focus, so `input:focus`/
`select:focus` keep `border-color: var(--accent)` but DROP the bare `outline: none`
(the `:focus:not(:focus-visible)` rule handles mouse; keyboard gets the ring).
Diff:
````diff
--- a/frontend/src/app.css
+++ b/frontend/src/app.css
@@
+@import './lib/styles/tokens.primitives.css';
+@import './lib/styles/tokens.semantic.css';
+@import './lib/styles/utilities.css';
+
 :root {
-	--bg-primary: #0D0D0D;
-	--bg-secondary: #1A1B23;
-	--bg-tertiary: #242631;
-	--bg-hover: #2E3040;
-	--bg-active: #383A4A;
-	--border: #3F414A;
-	--border-focus: #555;
-	--text-primary: #F5F5F0;
-	--text-secondary: #A0A1A7;
-	--text-dim: #666;
-	--text-tertiary: #7A7B82;
-	--accent: #00CED1;
-	--accent-dim: #00A8AB;
-	--accent-coral: #FF6B6B;
-	--energy-low: #4CAF50;
-	--energy-mid: #FF9800;
-	--energy-high: #F44336;
-	--waveform-bg: #12121A;
+	/* Legacy vars kept alive as ALIASES onto the semantic layer (Research §2).
+	 * Zero of the 76 components change; --accent stays CYAN until the deliberate flip. */
+	--bg-primary: var(--surface-1);
+	--bg-secondary: var(--surface-2);
+	--bg-tertiary: var(--surface-3);
+	--bg-hover: var(--surface-hover);
+	--bg-active: var(--surface-active);
+	--border: var(--border-subtle);
+	--border-focus: var(--border-strong);
+	--text-primary: var(--text-1);
+	--text-secondary: var(--text-2);
+	--text-tertiary: var(--text-3);
+	--text-dim: var(--text-4);
+	--accent: var(--accent-9);
+	--accent-dim: var(--accent-hover);
+	--accent-coral: var(--destructive);
+	--energy-low: var(--energy-low);
+	--energy-mid: var(--energy-mid);
+	--energy-high: var(--energy-high);
+	--waveform-bg: var(--surface-waveform);
 	--panel-width: 500px;
 	--header-height: 48px;
 
 	font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
 	color: var(--text-primary);
 	background: var(--bg-primary);
 }
@@
 input:focus, select:focus {
-	outline: none;
 	border-color: var(--accent);
 }
````
NOTE on self-reference: `--energy-low: var(--energy-low)` resolves because the
**semantic** `--energy-low` (Task 2, imported first) is the referenced value; CSS resolves
the `var()` against the already-cascaded semantic definition. If the type-checker or browser
flags a cycle (it will not — different cascade origin, same name is a re-declaration that
inherits the prior computed value is NOT guaranteed across the SAME `:root`), then IMPLEMENT
MUST instead point these three at the primitives directly: `--energy-low: var(--green-500)`,
`--energy-mid: var(--orange-500)`, `--energy-high: var(--red-500)`. **Prefer the primitive
form to avoid any same-name `var()` ambiguity.** (Decision: use the primitive form.)
Corrected lines for IMPLEMENT:
````diff
-	--energy-low: var(--energy-low);
-	--energy-mid: var(--energy-mid);
-	--energy-high: var(--energy-high);
+	--energy-low: var(--green-500);
+	--energy-mid: var(--orange-500);
+	--energy-high: var(--red-500);
````
Verification: app renders byte-identical colors (cyan accent intact); `npx svelte-check` clean.

#### Task 5 — Create `Button.svelte` primitive
Tools: editor (new file)
File: `frontend/src/lib/components/primitives/Button.svelte`
Prop signature (Svelte 5 runes; matches ContextMenu/Spinner idiom):
````diff
--- /dev/null
+++ b/frontend/src/lib/components/primitives/Button.svelte
@@
+<script lang="ts">
+	import type { Snippet } from 'svelte';
+
+	let {
+		variant = 'primary',
+		size = 'md',
+		type = 'button',
+		disabled = false,
+		loading = false,
+		onclick,
+		children,
+	}: {
+		variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
+		size?: 'sm' | 'md' | 'lg';
+		type?: 'button' | 'submit' | 'reset';
+		disabled?: boolean;
+		loading?: boolean;
+		onclick?: (e: MouseEvent) => void;
+		children?: Snippet;
+	} = $props();
+</script>
+
+<button
+	{type}
+	class="btn btn--{variant} btn--{size}"
+	class:btn--loading={loading}
+	disabled={disabled || loading}
+	aria-busy={loading}
+	onclick={onclick}
+>
+	{#if loading}
+		<span class="btn__spinner" aria-hidden="true"></span>
+	{/if}
+	<span class="btn__label">{@render children?.()}</span>
+</button>
+
+<style>
+	.btn {
+		display: inline-flex;
+		align-items: center;
+		justify-content: center;
+		gap: var(--space-sm);
+		font-family: inherit;
+		font-weight: var(--font-weight-medium);
+		border: 1px solid transparent;
+		border-radius: var(--btn-radius);
+		cursor: pointer;
+		transition: background var(--dur-fast) var(--ease-standard),
+		            border-color var(--dur-fast) var(--ease-standard),
+		            color var(--dur-fast) var(--ease-standard);
+	}
+	/* sizes */
+	.btn--sm { padding: var(--space-xs) var(--space-md);  font-size: var(--text-xs);  }
+	.btn--md { padding: var(--space-sm) var(--space-lg);  font-size: var(--text-sm);  }
+	.btn--lg { padding: var(--space-md) var(--space-xl);  font-size: var(--text-base);}
+	/* variants */
+	.btn--primary {
+		background: var(--accent);
+		color: var(--on-accent);
+	}
+	.btn--primary:hover:not(:disabled) { background: var(--accent-hover); }
+	.btn--primary:active:not(:disabled) { background: var(--accent-pressed); }
+
+	.btn--secondary {
+		background: var(--surface-3);
+		color: var(--text-1);
+		border-color: var(--border-default);
+	}
+	.btn--secondary:hover:not(:disabled) { background: var(--surface-hover); }
+	.btn--secondary:active:not(:disabled) { background: var(--surface-active); }
+
+	.btn--ghost {
+		background: transparent;
+		color: var(--text-2);
+	}
+	.btn--ghost:hover:not(:disabled) { background: var(--surface-hover); color: var(--text-1); }
+
+	.btn--danger {
+		background: var(--destructive);
+		color: #FFFFFF;
+	}
+	.btn--danger:hover:not(:disabled) { filter: brightness(1.1); }
+
+	.btn:disabled { opacity: 0.5; cursor: not-allowed; }
+
+	/* loading spinner */
+	.btn__spinner {
+		width: 0.85em; height: 0.85em;
+		border: 2px solid currentColor;
+		border-top-color: transparent;
+		border-radius: var(--radius-full);
+		animation: btn-spin 0.7s linear infinite;
+	}
+	@keyframes btn-spin { to { transform: rotate(360deg); } }
+	@media (prefers-reduced-motion: reduce) {
+		.btn__spinner { animation: none; }
+	}
+	/* The global :where(...):focus-visible rule (tokens.semantic.css) supplies the ring. */
+</style>
````
ARIA notes baked in: native `<button>` → Enter/Space + tab order free; `disabled` attr
removes from tab order; `loading` sets `disabled || loading` + `aria-busy` and KEEPS the label
(no icon-only swap). Focus ring inherited from the global `:focus-visible`.
Verification: `npx svelte-check` clean; renders in showcase (Task 8).

#### Task 6 — Create `Stack.svelte` primitive
Tools: editor (new file)
File: `frontend/src/lib/components/primitives/Stack.svelte`
Diff:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/primitives/Stack.svelte
@@
+<script lang="ts">
+	import type { Snippet } from 'svelte';
+
+	let {
+		gap,
+		children,
+	}: {
+		/** Any --space-* value, e.g. "var(--space-lg)" or "16px". Defaults to .stack's 8px. */
+		gap?: string;
+		children?: Snippet;
+	} = $props();
+</script>
+
+<div class="stack" style={gap ? `--stack-gap: ${gap}` : undefined}>
+	{@render children?.()}
+</div>
+
+<!-- presentational only: no role, not focusable; .stack class lives in utilities.css -->
````
Verification: `npx svelte-check` clean; primitive shares the `.stack` CSS — no duplicate styles.

#### Task 7 — Create `Grid.svelte` primitive
Tools: editor (new file)
File: `frontend/src/lib/components/primitives/Grid.svelte`
Diff:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/primitives/Grid.svelte
@@
+<script lang="ts">
+	import type { Snippet } from 'svelte';
+
+	let {
+		gap,
+		condensed = false,
+		children,
+	}: {
+		/** Override grid gutter, e.g. "var(--space-xl)". */
+		gap?: string;
+		/** Use the 16px condensed gutter. */
+		condensed?: boolean;
+		children?: Snippet;
+	} = $props();
+</script>
+
+<div
+	class="grid-12"
+	class:grid-12--condensed={condensed}
+	style={gap ? `--grid-gutter: ${gap}` : undefined}
+>
+	{@render children?.()}
+</div>
+
+<!-- presentational only; children supply .col-span-N. .grid-12 lives in utilities.css -->
````
Verification: `npx svelte-check` clean; primitive shares `.grid-12` CSS.

#### Task 8 — Create `/design-system` showcase route
Tools: editor (2 new files)
File A: `frontend/src/routes/design-system/+page.ts`
Diff:
````diff
--- /dev/null
+++ b/frontend/src/routes/design-system/+page.ts
@@
+// SPA model — matches +layout.ts (ssr=false, adapter-static fallback index.html).
+export const prerender = false;
+export const ssr = false;
````
File B: `frontend/src/routes/design-system/+page.svelte`
Concise structure (full content authored at IMPLEMENT; this enumerates MANDATORY sections —
each must render REAL values, "honest showcase"). Root element sets `data-theme="pine"` so
pine resolves ONLY inside this subtree; the rest of the app stays cyan.
Required scoped pine override at the top of the `<style>` (Research §3):
````css
:global([data-theme="pine"]) {
  --accent-9:  var(--pine-600);  /* #1F6F54 fill */
  --accent-10: var(--pine-500);  /* #25855E hover */
  --accent-11: var(--pine-400);  /* #3FB489 text-on-dark, 7.50:1 */
  --accent-contrast: #FFFFFF;    /* on-fill label, 6.07:1 — NOT black, NOT #3FB489 */
  --accent-pressed: var(--pine-700);
}
````
(`:global(...)` is required because `data-theme` is on the page root and the override must
cascade to descendants; Svelte scopes plain selectors otherwise.)
Mandatory `<h1>` + `<h2>` sections (heading hierarchy for AT):
1. **Color & contrast** — each pine step `--pine-50..950` as a swatch with its **computed ratio
   vs `#0D0D0D`** and an **AA verdict** (text ≥4.5:1 / large-UI ≥3:1 / fail). Hardcode the ratios
   from Research §4 matrix: 400=7.50 (text ✓), 500=4.25 (large/UI), 600=3.20 (UI/large only),
   700=2.46 (non-text). Plus an `--on-accent` chip: white on pine-600 = 6.07:1 ✓.
2. **Spacing scale** — render each `--space-*` as a bar of that width with its px label.
3. **Type scale** — each `--text-*` as a line of sample text at that size + line-height.
4. **Radius** — boxes showing `--radius-xs..xl` + full.
5. **Elevation** — cards at `--elev-0..3`.
6. **12-col grid** — a `<Grid>` with `.col-span-*` children (e.g. 6+6, 4+4+4, 3×4) showing the columns.
7. **Button matrix** — `<Button>` for EVERY variant (primary/secondary/ghost/danger) × size
   (sm/md/lg), plus explicit disabled and loading examples per variant. Uses the pine fill
   (because scoped to `[data-theme="pine"]`).
8. **Focus-ring keyboard demo** — a row of buttons/inputs with copy "Tab through these to see
   the ring"; ring is the global `:focus-visible`.
Showcase copy uses Kiku voice (set/flow/your library; never playlist/sequence/data).
Verification: route renders at `/design-system`; pine visible ONLY here; `npx svelte-check` clean.

#### Task 9 — Type-check gate (the LOCKED test command)
Tools: shell
Command:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expect: **0 errors** (warnings acceptable if pre-existing). This is the spec's mandatory
type-check gate (Human Section L65, L73).

#### Task 10 — Manual showcase + no-regression render check
Tools: shell + browser
Commands:
- `cd frontend && npm run dev` (Vite dev server; `/api` proxy to :8000 unaffected).
- Open `/` → confirm accent is STILL cyan (`--accent` resolves `--cyan-500 #00CED1`); the app
  looks byte-identical to before this spec (the 20 aliases are value-preserving).
- Open `/design-system` → confirm: pine swatches + ratios render; spacing/type/radius/elevation
  scales render; 12-col grid demo renders; full Button matrix renders in PINE; Tab key shows a
  visible `#5FD0A8` focus ring on every interactive element.
- DevTools → emulate `prefers-reduced-motion: reduce` → confirm button hover/spinner do not animate.
Acceptance: app unchanged (cyan); showcase honest (every claim real); pine isolated to the showcase.

#### Task 11 — Commit (IMPLEMENT-stage commit; separate from this PLAN commit)
Tools: git
Commands:
- `git add -- frontend/src/lib/styles/tokens.primitives.css frontend/src/lib/styles/tokens.semantic.css frontend/src/lib/styles/utilities.css frontend/src/lib/components/primitives/Button.svelte frontend/src/lib/components/primitives/Stack.svelte frontend/src/lib/components/primitives/Grid.svelte frontend/src/routes/design-system/+page.svelte frontend/src/routes/design-system/+page.ts frontend/src/app.css`
- `BRANCH=$(git rev-parse --abbrev-ref HEAD); [ "$BRANCH" != "main" ] || { echo 'ERROR: On main' >&2; exit 2; }`
- `git commit -m "spec(023): IMPLEMENT - design system tokens, primitives, /design-system showcase"`

### Accessibility acceptance criteria (measurable — Research §5, §3 reports)

- [ ] **Pine role-split honored**: pine-600 (3.20:1) used ONLY as fill/border/large-text; pine-400 (7.50:1) the only step used as body text; pine-500 (4.25:1) large/UI only; pine-700 (2.46:1) non-text only. No pine ≥500 used as body text anywhere in the showcase.
- [ ] **On-accent = white**: button labels on pine-600 fill use `--on-accent: #FFFFFF` = 6.07:1 (NOT `#000` 3.20:1, NOT pine-400 2.59:1).
- [ ] **Focus ring**: `#5FD0A8` ≥3:1 vs BOTH page bg (10.25:1) AND pine-600 fill (3.20:1); ≥2px thick, ≥2px offset (SC 2.4.13); shown on keyboard focus only (`:focus-visible`), NOT mouse.
- [ ] **Keyboard**: Button activates on Enter + Space (native `<button>`); `disabled` Button skipped in tab order + non-activatable; `loading` Button exposes `aria-busy="true"` and keeps an accessible name.
- [ ] **Stack/Grid**: no ARIA role, not focusable, not in tab order.
- [ ] **Reduced motion**: under `prefers-reduced-motion: reduce`, no hover/focus/spinner animates; colors still change instantly.
- [ ] **Showcase honesty**: every pine swatch displays its real computed ratio + AA verdict.

### Validate (Human Section requirement → compliance)

- **RESEARCH-grounded token layer (HLO L6-12, MLO L15-21)** → Tasks 1-2 build pine ramp + spacing/type/radius/elevation as CSS custom properties, semantic naming, dark-only. `L88-315` research drives every value.
- **Replace cyan with pine as main color (HLO L11)** → pine ramp shipped as primitives; flip lever in place; live flip deferred to a separate spec per LOCKED decision (HLO "before migrating", DT L56-57). App stays cyan THIS spec.
- **12-col grid + utility layer (MLO L22-23, DT)** → Task 3 `.grid-12`/`.stack`/`.cluster`; grid opt-in, flex shell untouched (L271-277).
- **Svelte primitives Button/Stack/Grid (MLO L24-25)** → Tasks 5-7; native `<button>`, focus rings, ARIA.
- **Accessibility: focus rings, WCAG AA pine-on-dark, keyboard, ARIA (MLO L26-27, DT L72-77)** → Task 2 global `:focus-visible`; criteria above; ratios documented (L196-228).
- **`/design-system` showcase before migration (MLO L28-29, DT L42-43)** → Task 8; isolated `[data-theme="pine"]`; renders every token/utility/primitive.
- **NO Tailwind / NO new deps (DT L52-57, LOCKED)** → only CSS custom props + hand-rolled utilities + `.svelte` files; `@import` resolved by existing Vite. Zero package.json change.
- **Type-check passes (DT L65, L73)** → Task 9 gate.
- **Kiku voice in showcase copy (DT L62-64)** → Task 8 mandates set/flow/your-library wording.
- **Out of scope respected (DT L67-70)** → no migration of the 76 components, no light theme, no Python.

### Risks / verification

- **Flipping `--accent-source` globally is the deliberate FUTURE step (out of scope here).** The 4 `--accent-9/10/11/contrast` lines in `tokens.semantic.css :root` are the single edit point. When that future spec flips them to pine, the two hardcoded `#000` labels in `set/BuildProgress.svelte:304` and `set/BuildSetDialog.svelte:887` will regress to 3.20:1 — **flag carried forward to that spec** (must become `--on-accent`). They are NOT touched this spec.
- **No-regression proof**: the 20 legacy vars are value-preserving aliases (`--accent`→`--cyan-500`=`#00CED1`, etc.). Verification: load `/` and confirm the accent is identical cyan; `git stash` comparison of computed styles is byte-identical. The only intentional behavior change app-wide is the ADDITION of a keyboard `:focus-visible` ring (pure a11y improvement, specificity 0, overridable) and removal of the bare `outline:none` on `input/select:focus` (mouse focus still suppressed via `:focus:not(:focus-visible)`).
- **`@import` order risk**: primitives MUST import before semantic (semantic references primitive `var()`s). Task 4 fixes the order. If a primitive is referenced before definition, CSS `var()` resolves to `initial`/invalid → visible color break in the showcase only (caught by Task 10).
- **`:global()` necessity in the showcase**: Svelte scopes selectors; the `[data-theme="pine"]` override MUST be `:global(...)` or it won't cascade to `<Button>` children. Caught by Task 10 (buttons would render cyan if missed).

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
