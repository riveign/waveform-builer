---
id: OBS-004
title: Frontend architecture, routing, and delivery shape
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

Establishes the structural shape of the SvelteKit app — what the framework is being asked
to do, and what it is not — before judging whether it should be rebuilt.

> **Re-check 2026-08-09 — resolved by [[PLN-001]]/P4.** E2–E7 record the single-route
> shape that `CLM-002` derives from. **K2, K3, K4 and K5 no longer hold** — see **K6**.
> K1 (the stack is not the problem) is unchanged and was the basis for not rebuilding.

## D — Definitions

- **D1 · Surface.** One of the six top-level things the DJ can be looking at: Track, Set,
  DNA, Tinder, Hunt, Albums.

## E — Evidence

- **E1 · Stack is current-generation.** Svelte `^5.51`, SvelteKit `^2.50`, Vite `^7.3`,
  TypeScript `^5.9`. Runes are force-enabled for all first-party files
  (`svelte.config.js` → `dynamicCompileOptions: { runes: true }`). Runtime deps are three:
  `chart.js`, `wavesurfer.js`, `svelte-dnd-action`. No component framework, no CSS
  framework, no state library.
- **E2 · There is exactly one real route.** `src/routes/` contains `+layout.svelte`,
  `+page.svelte`, and `design-system/+page.svelte` (a dev-only gallery). All six surfaces
  (D1) live inside `Workspace.svelte`.
- **E3 · Surface selection is an in-memory variable.** `ui.activeTab` is a module-level
  `$state<Tab>` in `stores/ui.svelte.ts`, switched by an `{#if}/{:else if}` ladder in
  `Workspace.svelte` and by number-key shortcuts 1–6.
- **E4 · Nothing is reflected in the URL.** No query params, no route params, no
  `pushState`. `ui.selectedTrack`, `ui.selectedSetId`, `ui.selectedTrackInSet`,
  `ui.setViewMode` are all in-memory only.
- **E5 · SSR and prerendering are off.** `+layout.ts` sets `ssr = false` and
  `prerender = false`; `adapter-static` with `fallback: 'index.html'`. It is a pure SPA.
- **E6 · No code splitting across surfaces.** `vite build` emits one dominant client chunk,
  `nodes/2.*.js` at **540 KB** uncompressed, out of a ~1.0 MB total build. Because E2 puts
  everything behind one route, SvelteKit's per-route splitting has nothing to split on.
- **E7 · No error boundary.** No `svelte:boundary` and no `+error.svelte` anywhere.
- **E8 · Keyboard shortcuts are centralised but ad-hoc.** `Workspace.svelte` owns a single
  `handleKeydown` covering both playback transport and tab switching, guarded by a manual
  `target.tagName === 'INPUT' | 'SELECT' | 'TEXTAREA'` check.
- **E9 · Accessibility groundwork exists.** `lib/actions/focusTrap.ts` and
  `lib/actions/rovingFocus.ts` are first-party actions, applied to grids and modals.

## K — Conclusions

- **K1 · The technology choices are not the problem.** Svelte 5 runes + Kit 2 + Vite 7 is
  the current generation, not a legacy stack. Three runtime dependencies for a 92-component
  app is unusually disciplined; most comparable apps carry a component library, a CSS
  framework, and a data-fetching library.
- **K2 · The app uses ~10% of its framework.** SvelteKit's routing, `load` functions,
  SSR, prerendering, form actions, and per-route code splitting are all inert (E2, E5, E6).
  It is a hand-rolled SPA wearing a SvelteKit shell.
- **K3 · Three concrete user-visible costs follow from E4.** No deep links (you cannot send
  or bookmark "this set" or "this track"), no browser back/forward, and a full state reset
  on refresh. For a tool whose whole pitch is *teaching* — where the DJ wants to return to
  a specific transition and study it — this is a product-level gap, not a polish item.
- **K4 · E6 is a symptom, not a disease.** The 540 KB chunk is large because of E2. Fixing
  routing fixes the bundle for free; there is no separate bundle-optimisation project.
- **K5 · E7 means any uncaught render error blanks the entire app**, because there is one
  route and no boundary at any level.

- **K6 · Resolved 2026-08-09.** Six surfaces became six routes under an `(app)` group,
  with `/track/[[id]]` and `/set/[[id]]` carrying their subject in the path, `?t=` the
  focused track and `?view=` the layout. Consequences, each closing a K above:
  - K3's three costs are gone: deep links work, Back/Forward walk surfaces, refresh
    preserves both the set and the row inside it. Verified in Chromium.
  - K4 held exactly as predicted — splitting came free with routing. Initial JS fell from
    **700 KB on every route** to 253–612 KB by route; the landing route `/track` is
    **292 KB, −58%**. The design-system gallery left the app path entirely.
  - K5 closed by `+error.svelte`; a bad id renders a page instead of blanking the app.
  - K2 is narrower now: `load()`, routing and per-route splitting are all in use. SSR and
    form actions remain unused, which is the deliberate SPA choice (E5), not debt.
- **K7 · A dead-state bug fell out of the tracing.** `ui.selectedSetId` had two writers
  (`SetAppearances`, build-complete) and no reader, so "jump to this set" silently did
  nothing in both places. Moving set identity into the path fixed it by construction —
  the class of bug that disappears when state has one home.

## Q — Open

- **Q1.** Does the personal-server / PWA arc need SSR, or is SPA + service worker enough?
  Determines whether E5 stays a deliberate choice or becomes debt.
