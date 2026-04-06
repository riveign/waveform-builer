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

### Verified Line Numbers (corrected from audit reports)

The MUX audit reports contain stale line references for route endpoints. Verified against live code:

| Reference | Audit Says | Actual | File |
|-----------|-----------|--------|------|
| `create_set` endpoint | L311-329 | **L311-329** | `src/kiku/api/routes/sets.py` |
| `add_track` endpoint | L367-376 | **L367-376** | `src/kiku/api/routes/sets.py` |
| `remove_track` endpoint | L379-388 | **L379-388** | `src/kiku/api/routes/sets.py` |
| `reorder_tracks` endpoint | L391-402 | **L391-402** | `src/kiku/api/routes/sets.py` |
| `delete_set` endpoint | L356-364 | **L356-364** | `src/kiku/api/routes/sets.py` |
| `list_sets` endpoint | L405-426 | **L405-426** | `src/kiku/api/routes/sets.py` |
| `set_detail` endpoint | L429-443 | **L429-443** | `src/kiku/api/routes/sets.py` |
| `suggest_next` endpoint | L279+ | **L279** | `src/kiku/api/routes/tracks.py` |
| `build_set` 1-indexed position | L232 | **L230** (`position=i + 1`) | `src/kiku/setbuilder/planner.py` |
| `SetCreateRequest` schema | L268-271 | **L268-271** | `src/kiku/api/schemas.py` |
| `SetAddTrackRequest` schema | L280-282 | **L280-282** | `src/kiku/api/schemas.py` |
| `add_track_to_set` DB fn | L287-325 | **L287-325** | `src/kiku/db/store.py` |
| `reorder_set_tracks` DB fn | L363-411 | **L363-411** | `src/kiku/db/store.py` |
| `transition_score` | L294 | **L294** | `src/kiku/setbuilder/scoring.py` |
| `score_replacement` | L324 | **L324** | `src/kiku/setbuilder/scoring.py` |
| `score_transitions` | L378+ | **L378** | `src/kiku/setbuilder/scoring.py` |
| `replace_track` endpoint | L777-791 | **L777-791** | `src/kiku/api/routes/sets.py` |
| `get_replacements` endpoint | L677-774 | **L677-774** | `src/kiku/api/routes/sets.py` |

Note: The sentinel review claimed stale line numbers but the audit references are actually correct against current code. The sentinel's "actual" lines were wrong.

### Backend Findings

**1. Position Indexing Inconsistency (CONFIRMED)**

`build_set()` at `planner.py:230` saves positions as `i + 1` (1-based). All other paths use 0-based:
- `add_track_to_set()` (`store.py:307,310`) -- 0-based
- `reorder_set_tracks()` (`store.py:399`) -- 0-based (enumerate)
- `import_playlist()` (`service.py:190`) -- 0-based (enumerate)
- `import_cdj_history()` (`service.py:349`) -- 0-based

The test fixture at `tests/api/conftest.py:47` seeds positions 1-5 (1-based), matching the build path. This means existing built sets in the DB use 1-based positions. The fix should be in `planner.py` only (change to 0-based), but must account for existing data.

**2. No transition_score on manual add (CONFIRMED)**

`add_track_to_set()` (`store.py:320`) creates `SetTrack` without `transition_score`. The score is only computed during `build_set()` (planner.py:227) and is set to `None` during `replace_track_in_set()` (store.py:442). The spec's Phase 1 requirement to compute score on add is validated as a real gap.

**3. No `source` field on create (CONFIRMED)**

`create_set()` at `sets.py:314-318` creates a `Set` without setting `source`. The `Set` model has a `source` column (models.py) that supports "kiku", "manual", "m3u8", "rb_playlist", "cdj_history". Adding `source: str | None = None` to `SetCreateRequest` is straightforward.

**4. No `duration_min` recomputation on add/remove (CONFIRMED)**

Neither `add_track_to_set()` nor `remove_track_from_set()` update `Set.duration_min`. The field is only set during `build_set()` (planner.py:215) and `import_playlist()` (service.py:186).

**5. Suggest-next uses neutral energy target (CONFIRMED)**

`score_transitions()` at scoring.py:429 calls `transition_score()` without passing `target_energy`, defaulting to 0.5. The suggest-next endpoint at tracks.py:334 does the same. The spec's requirement to add `position_min` and `energy_profile` params is valid.

**6. No analysis_cache invalidation on manual changes**

The sentinel review (R8) correctly identified that `analysis_cache` and `is_analyzed` become stale after manual add/remove/reorder. No current code invalidates these on track mutations. This should be added.

**7. Existing reusable primitives verified**

| Primitive | File:Line | Reusable As-Is |
|-----------|-----------|----------------|
| `transition_score()` | `scoring.py:294` | Yes -- accepts target_energy, weights, discovery_density |
| `score_replacement()` | `scoring.py:324` | Yes -- scores against both neighbors |
| `energy_fit()` | `scoring.py:207` | Yes |
| `EnergyProfile.target_energy_at()` | `constraints.py:28` | Yes |
| `_violates_artist_cooldown()` | `planner.py:66` | Yes -- currently private but easily importable |
| `_get_candidate_pool()` | `planner.py:22` | Yes -- genre/BPM filtered pool |
| `parse_energy_json()` | `constraints.py:65` | Yes -- parses stored energy profiles |
| `parse_energy_string()` | `constraints.py:49` | Yes -- parses preset strings |

### Frontend Findings

**1. Entry points for "Add to Set" (CONFIRMED -- 5 gaps)**

- `TrackContextMenu.svelte` (L52-96): Has energy, rating, play -- no "Add to Set". This is the highest-leverage addition because it propagates to both TrackTable and SetTrackCard right-click.
- `TrackView.svelte`: Has play, energy, rating, SetAppearances, SimilarTracks -- no "Add to Set" button.
- `SimilarTracks.svelte`: Shows similar tracks but no add action.
- `NowPlayingBar.svelte`: No add-to-set action.
- `SetTimeline.svelte`: Drop zone exists (L132-159) but no inline "Add Track" button.

**2. SetPicker has no "New Set" button (CONFIRMED)**

`SetPicker.svelte` (L37-63): Only a `<select>` dropdown and "Import" button. The `createSet()` API function exists in `sets.ts:57-63` but is never called from any UI surface.

**3. Frontend API client is complete (CONFIRMED)**

`frontend/src/lib/api/sets.ts` already has all needed functions:
- `createSet()` (L57-63)
- `addTrackToSet()` (L154-164)
- `removeTrackFromSet()` (L166-168)
- `reorderSetTracks()` (L170-176)
- `listSets()` (L18-23)
- `getSet()` (L25-27)

**4. Existing manual-add patterns**

- Drag-and-drop: `TrackTable` -> `SetTimeline` via `application/x-kiku-track` (SetTimeline L132-159)
- SuggestNextPanel "Add" button (SuggestNextPanel.svelte L35-46): Calls `addTrackToSet()` then removes from list and fires `onAdd` callback
- Both use `addTrackToSet()` from `sets.ts` and refresh via callbacks

**5. Store/reactivity pattern for cross-panel updates**

SetTimeline receives `onTracksChanged` callback. SetView provides this to trigger re-fetch. When a track is added from outside (e.g., context menu), the set data needs refreshing. Current pattern: callbacks + explicit re-fetch via `getSet()`. No global store for set state -- all prop-drilled.

### Test Infrastructure

**Backend tests**: `tests/api/conftest.py` provides `db_session` (in-memory SQLite, 20 seed tracks, 1 seed set with 5 tracks at positions 1-5) and `client` (FastAPI TestClient with dependency override).

Existing relevant tests in `tests/api/test_sets_api.py`:
- `test_create_set` -- creates empty set, verifies track_count=0
- `test_add_track_to_set` -- appends track 10, verifies 6 tracks
- `test_remove_track_from_set` -- removes track 3, verifies 4 remain
- `test_reorder_set_tracks` -- reverses order [5,4,3,2,1]
- `test_build_set_sse` -- full SSE build flow

Scoring tests in `tests/test_scoring.py` cover `transition_score`, `bpm_compatibility`, `genre_coherence`, `track_quality`.

No frontend tests exist (no `*.test.ts`, `*.spec.ts`, or `__tests__/` directories found).

### Strategy

**Phase 1: Create and Add (foundation)**

Backend changes:
1. Add `source: str | None = None` to `SetCreateRequest` schema (schemas.py:268)
2. Set `source` in `create_set()` endpoint (sets.py:314)
3. Compute `transition_score` in `add_track_to_set()` or in the API endpoint handler -- prefer the endpoint handler since it has DB session access to load neighbor tracks and call `transition_score()`
4. Recompute `duration_min` on add/remove in the API handlers
5. Invalidate `is_analyzed`/`analysis_cache` on add/remove/reorder
6. Fix planner.py:230 position indexing (change `i + 1` to `i`) -- but must update test fixture seed data to match

Frontend changes:
1. Create `AddToSetPicker.svelte` -- popover with set search, track count, "New Set" inline create, duplicate detection
2. Add "+ New" button to `SetPicker.svelte` next to Import
3. Add "Add to Set" submenu to `TrackContextMenu.svelte` using AddToSetPicker
4. Add "Add to Set" button to `TrackView.svelte` header
5. Add "+" icon to `SimilarTracks.svelte` rows
6. Toast notifications on successful add

**Phase 2: In-Set Search and Scoring**

Backend changes:
1. Add `position_min` and `energy_profile` optional params to suggest-next endpoint
2. Derive `target_energy` from energy profile at given position
3. Pass `target_energy` through `score_transitions()`

Frontend changes:
1. Create `InSetTrackSearch.svelte` -- inline panel in SetView with filters + scored results
2. Insertion point selection in SetTimeline (click between tracks to target a gap)
3. Score badges on search results

**Phase 3: AI Fill and Reorder**

Backend changes:
1. Create `src/kiku/setbuilder/filler.py` -- gap identification, candidate scoring, SSE streaming
2. Create `src/kiku/setbuilder/reorder.py` -- gentle (neighbor swaps) and full (simulated annealing) strategies
3. Three new endpoints: `/fill` (SSE), `/optimize-order`, `/score-sequence`
4. New schemas: `SetFillRequest`, `SetOptimizeOrderRequest`, etc.

Frontend changes:
1. Create `FillReorderDialog.svelte` -- two tabs (Fill Gaps + Reorder), energy curve viz, before/after comparison
2. "Assist" button in SetView (visible when >= 3 tracks)

**Testing strategy:**
- Phase 1 unit tests: `test_create_set_with_source`, `test_add_track_computes_score`, `test_add_track_recomputes_duration`, `test_add_track_invalidates_analysis`, `test_position_indexing_consistency`
- Phase 2 unit tests: `test_suggest_next_with_energy_profile`, `test_suggest_next_position_aware`
- Phase 3 unit tests: `test_fill_identifies_weak_transitions`, `test_gentle_reorder_improves_score`, `test_full_reorder_converges`, `test_score_sequence_endpoint`
- All tests follow existing patterns in `tests/api/conftest.py` and `tests/api/test_sets_api.py`
- No frontend tests (project has none) -- manual verification per existing practice

**Key risks:**
- R1: Position indexing fix may break existing sets in the DB (mitigate: only fix going forward in planner.py, existing sets remain as-is since all read paths handle both)
- R2: analysis_cache staleness (mitigate: invalidate on every mutation)
- R3: Cross-panel reactivity when adding from context menu (mitigate: use callback chain or store subscription to trigger SetTimeline refresh)

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
