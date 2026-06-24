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
<!-- Filled by /spec RESEARCH -->

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
