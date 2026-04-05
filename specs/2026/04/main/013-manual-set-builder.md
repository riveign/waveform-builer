# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Enable DJs to build sets track by track — create an empty set, add tracks from anywhere in the app, search and score candidates inline, then optionally ask Kiku to fill gaps and reorder for better flow. This closes the core curation gap: Kiku can auto-build (beam search) and import (M3U8), but has no deliberate manual path. The manual builder puts the DJ back in the creative loop while keeping scoring and teaching tools within arm's reach.

## Mid-Level Objectives (MLO)

1. **CREATE** empty sets from SetPicker and AddToSetPicker with `source: "manual"` — inline name input, no modal, no energy profile required upfront
2. **ADD** tracks to any set from 5 entry points: right-click context menu (P0), track detail page (P0), set timeline (P1), similar tracks (P1), now playing bar (P2)
3. **BUILD** a reusable `AddToSetPicker` component — popover with set search, track count, "New Set" quick-create, keyboard navigation, duplicate detection
4. **COMPUTE** transition scores on manual add — score against preceding track (and update following track's score), recompute `duration_min` on every add/remove
5. **SEARCH** library inline within SetView — `InSetTrackSearch` panel with filters, transition score preview, insertion point selection (click between tracks to target a gap)
6. **ENHANCE** suggest-next endpoint with position-aware energy targets — accept `position_min` and `energy_profile` params, derive `target_energy` from set's energy curve at that position
7. **FILL** gaps via SSE streaming — `POST /api/sets/{id}/fill` identifies weak transitions (score < 0.6) and energy deviations, proposes insertions with scores and explanations, DJ keeps/skips each proposal
8. **REORDER** for optimal flow — `POST /api/sets/{id}/optimize-order` with two strategies: Gentle (local neighbor swaps, minimal disruption) and Full Rethink (simulated annealing), before/after comparison with explanations for every moved track
9. **SCORE** arbitrary sequences — `POST /api/sets/{id}/score-sequence` utility endpoint for before/after comparisons without saving
10. **FIX** position indexing — standardize `planner.py:232` from 1-based to 0-based to match all other paths

## Details (DT)

### Implementation Phases

**Phase 1: Create and Add (foundation)** — 2-3 days
- Backend: `source` field on `SetCreateRequest`, transition score on `add_track_to_set()`, duration recomputation, position indexing fix
- Frontend: `AddToSetPicker.svelte`, SetPicker "+ New" button, TrackContextMenu "Add to Set" submenu, TrackView button, SimilarTracks "+" icon, toast notifications
- Files to create: `frontend/src/lib/components/set/AddToSetPicker.svelte`
- Files to modify: `src/kiku/api/schemas.py`, `src/kiku/api/routes/sets.py`, `src/kiku/db/store.py`, `src/kiku/setbuilder/planner.py`, `frontend/src/lib/components/set/SetPicker.svelte`, `frontend/src/lib/components/library/TrackContextMenu.svelte`, `frontend/src/lib/components/waveform/TrackView.svelte`, `frontend/src/lib/components/waveform/SimilarTracks.svelte`

**Phase 2: In-Set Search and Scoring** — 2-3 days
- Backend: `position_min` and `energy_profile` params on suggest-next, pass `target_energy` through `score_transitions()`
- Frontend: `InSetTrackSearch.svelte` with filters + scored results, insertion point selection in SetTimeline, colored score badges
- Files to create: `frontend/src/lib/components/set/InSetTrackSearch.svelte`
- Files to modify: `src/kiku/api/routes/tracks.py`, `src/kiku/setbuilder/scoring.py`, `frontend/src/lib/components/set/SetView.svelte`, `frontend/src/lib/components/set/SetTimeline.svelte`

**Phase 3: AI Fill and Reorder** — 3-5 days
- Backend: `src/kiku/setbuilder/filler.py` (fill algorithm + SSE events), `src/kiku/setbuilder/reorder.py` (gentle + full strategies), 3 new API endpoints, new schemas
- Frontend: `FillReorderDialog.svelte` (two tabs — Fill Gaps + Reorder), "AI Assist" button in SetView (visible when >= 3 tracks), energy curve visualization, before/after comparison
- Files to create: `src/kiku/setbuilder/filler.py`, `src/kiku/setbuilder/reorder.py`, `frontend/src/lib/components/set/FillReorderDialog.svelte`

### API Surface

**Modified endpoints:**
- `POST /api/sets` — accept `source` field
- `POST /api/sets/{id}/tracks` — compute transition_score, recompute duration_min, return score in response
- `DELETE /api/sets/{id}/tracks/{track_id}` — recompute duration_min
- `GET /api/tracks/{id}/suggest-next` — add `position_min`, `energy_profile` optional params

**New endpoints:**
- `POST /api/sets/{id}/fill` (SSE) — events: `fill_started`, `gap_identified`, `fill_proposed`, `fill_complete`
- `POST /api/sets/{id}/optimize-order` — returns current/proposed scores, proposed order, changes with explanations, energy curves
- `POST /api/sets/{id}/score-sequence` — score a proposed track order without saving

### Fill Algorithm

Gap identification: transitions with score < 0.6 OR energy deviation > 0.3 from profile. Configurable gap threshold. For each gap, use `score_replacement()` pattern against both neighbors with position energy target. Also extend before/after set bounds if target_duration_min not reached. Proposals streamed via SSE, capped at `max_fill_tracks` (default 10).

Reuses existing primitives: `transition_score()`, `score_replacement()`, `EnergyProfile.target_energy_at()`, `_get_candidate_pool()`, `_violates_artist_cooldown()`.

### Reorder Algorithm

**Gentle** (default): Iterative neighbor swaps within window of 3-5 positions. Accept improving swaps only. Max 50 iterations. Fast, predictable, minimal disruption.

**Full Rethink**: Simulated annealing — 5,000 iterations, initial_temp=1.0, cooling_rate=0.995. Random swaps accepted probabilistically. Better results but more disruptive. Bounded complexity: O(iterations * N) where N = track count.

### Database

No schema migrations required. Existing columns: `sets.source`, `sets.duration_min`, `set_tracks.transition_score`. All need to be properly populated on manual operations.

### Edge Cases

- Empty set: InSetTrackSearch scores without a preceding track (show all results unsorted or sort by energy fit to position 0)
- Single-track set: Fill can extend both before and after; reorder is a no-op
- Reorder on < 3 tracks: disable the button, show tooltip "Need at least 3 tracks to optimize order"
- Track already in set: AddToSetPicker shows "(already in set)" badge, prevents duplicate add
- Stale transition scores after reorder: recompute all scores inline after any reorder operation

### Sentinel Review Notes (8/10)

- Gap threshold (0.6) should be configurable via fill request params — ADDRESSED in `SetFillRequest.gap_threshold`
- Empty set edge cases need explicit handling — ADDRESSED above
- Reorder complexity bounded by iteration cap — ADDRESSED (50 for gentle, 5,000 for SA)

### Testing

**Unit tests:**
- `transition_score` computed correctly on `add_track_to_set()` (both directions: preceding and following)
- `duration_min` recomputed on add/remove
- `source` field persisted on set creation
- Position-aware energy target in suggest-next
- Fill algorithm identifies weak transitions (score < threshold)
- Gentle reorder improves total score monotonically
- Full reorder converges (final score >= initial score)
- `score-sequence` returns consistent scores

**E2E tests:**
- Create empty set -> add 3 tracks -> verify scores and duration
- Fill + apply flow: seed 3 tracks -> fill -> accept proposals -> verify set updated
- Reorder flow: seed 5 tracks -> optimize -> apply -> verify new order and scores
- AddToSetPicker: renders set list, creates new set inline, adds track, shows toast

### Key Design Principles

- "Show the Why": Every score, every fill proposal, every reorder change comes with an explanation
- "Your Library Is the Lesson": Only the DJ's own tracks, scored against the DJ's own curation signals
- "The Story Comes First": Fill/reorder serves the DJ's intent prompt, not the algorithm's opinion
- DJ stays in the creative loop: proposals are suggestions, not directives

## Behavior

You are a senior fullstack engineer implementing a manual set builder for a DJ tool. The feature spans backend (Python/FastAPI) and frontend (SvelteKit/TypeScript). Implement in strict phase order — Phase 1 must be fully working before starting Phase 2. Reuse existing scoring primitives (`transition_score`, `score_replacement`, `EnergyProfile`) rather than reimplementing. Follow existing SSE patterns from `build_set_sse` for the fill endpoint. Keep UI lightweight — inline inputs over modals, popovers over pages. Every user-facing score must have a visible explanation.

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
