---
id: OBS-008
title: Design system maturity and component composability
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

Spec 023 built a design system and migrated twelve surfaces to it. This note measures what
actually stuck, and whether components compose or merely coexist.

> **Re-check 2026-08-09 — [[PLN-001]]/P6.** **K2 is closed**: the four structural
> primitives exist and all six dialogs share one shell. **K3's LOC estimate was wrong** —
> the dialogs shrank 10%, not the ~40% implied, because chrome was ~50 lines each and the
> rest is domain content. **K4 half-closed**: the gallery now documents every primitive,
> but nothing still verifies it stays in sync. E2's 123 hex literals are largely untouched.
> **K5 stands, weakened**: behaviour composes better than it did, not yet fully.

## D — Definitions

- **D1 · Primitive.** A component with no domain knowledge — usable on any surface.
- **D2 · Token adherence.** Fraction of colour/space decisions expressed as `var(--…)`
  rather than literals.

## E — Evidence

- **E1 · A three-tier token system exists and is used.** `tokens.primitives.css` (85
  declarations) + `tokens.semantic.css` (165) + `canvasPalette.ts` for chart colours.
  `var(--…)` is referenced **2,033 times** across components.
- **E2 · Token adherence is high but not total.** 123 hardcoded hex literals remain, spread
  across 16 of 92 component files. Ratio of tokenised to literal colour references is
  roughly **16:1**.
- **E3 · The primitive set is small.** 12 primitives: `Button`, `Chip`, `Grid`,
  `HarmonyIcon`, `MenuItem`, `MenuSeparator`, `Menu`, `MetronomeIcon`, `SegmentedControl`,
  `Stack`, `StarRating`, `icon-types.ts`.
- **E4 · Notable absences from the primitive set.** No `Modal`/`Dialog`, no `Input`, no
  `Select`, no `Tooltip`, no `Skeleton`/`Spinner`, no `EmptyState`, no `Toast`.
- **E5 · The absences are re-implemented downstream.** Five separate dialog components
  exist as bespoke files — `BuildSetDialog` (781), `FillReorderDialog` (493),
  `ImportPlaylistDialog` (478), `ReplaceTrackModal` (549), `FixMetadataModal` (435),
  plus `MusicBrainzMatchModal` — ~2,700 LOC of dialog, each with its own chrome, backdrop,
  and dismissal handling. A shared `Modal` primitive is a known deferred item of spec 026.
- **E6 · Loading and empty states are likewise re-implemented** — 26 components carry their
  own `loading`/`error` state (`OBS-005/E3`) and render their own markup for it.
- **E7 · There is a living gallery.** `routes/design-system/+page.svelte` is 1,488 LOC and
  renders the primitives. It is a dev route, not a build-time artifact, and nothing
  verifies that it stays in sync with the primitives it documents.
- **E8 · Component-level docs exist for exactly three components.**
  `frontend/docs/design-system/` holds `track-card.md`, `related-track-card.md`,
  `content-conventions.md`, and `ui-ux-improvements.md` (a backlog).
- **E9 · Accessibility work is real but partial.** `focusTrap` and `rovingFocus` actions
  exist and are applied; the transport scrubber carries `role="slider"`. Nothing enforces
  this — there is no axe/a11y check in any gate (`OBS-002/K1`).
- **E10 · Domain components are large.** `TrackCard` 1,119 LOC, `SearchFilters` 955,
  `SetView` 909, `RelatedTrackCard` 639.

## K — Conclusions

- **K1 · The token layer is the most mature part of the frontend.** E1's 2,033 references
  against 250 declarations is a real, consistently-applied system, not a token file that
  someone wrote once. E2's 16 files are a finite, closeable list — a day of work, not a
  project.
- **K2 · The primitive layer stopped halfway.** E3+E4: the twelve primitives that exist are
  the *decorative* ones (buttons, chips, icons, rating). The ones missing are the
  *structural* ones — modal, input, empty state, skeleton — which are precisely the ones
  whose absence forces duplication.
- **K3 · E5+E6 quantify the cost of K2 at ~2,700 LOC of dialog plus 26 copies of a load
  state.** This, together with `OBS-005/K2`, explains `OBS-001/K3`: the oversized frontend
  files are large because they each re-implement the same three missing primitives.
- **K4 · The design system is documented for humans, unverified by machines.** E7+E9: a
  1,488-LOC gallery nobody diffs and a11y actions nobody checks. Both degrade silently.
- **K5 · Composability is the frontend's real deficit, and it is structural, not stylistic.**
  Styling composes (K1). Behaviour does not (K2, K3).
