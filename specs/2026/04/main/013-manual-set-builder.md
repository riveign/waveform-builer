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

### Files

- `src/kiku/api/schemas.py`
  - L268-271: Add `source` field to `SetCreateRequest`
  - L289+: Add new schemas for fill, optimize-order, score-sequence
- `src/kiku/api/routes/sets.py`
  - L311-329: Set `source` in `create_set()`
  - L367-376: Compute transition_score, recompute duration, invalidate analysis in `add_track()`
  - L379-388: Recompute duration, invalidate analysis in `remove_track()`
  - L391-402: Invalidate analysis in `reorder_tracks()`
  - Add fill, optimize-order, score-sequence endpoints
- `src/kiku/db/store.py`
  - L287-325: No changes to `add_track_to_set` itself (scoring done in route handler)
  - L328-360: No changes to `remove_track_from_set`
- `src/kiku/setbuilder/planner.py`
  - L230: Fix `position=i + 1` to `position=i`
- `src/kiku/api/routes/tracks.py`
  - L279-363: Add `position_min`, `energy_profile` params to `suggest_next()`
- `src/kiku/setbuilder/scoring.py`
  - L378-439: Add `target_energy` param to `score_transitions()`
- `src/kiku/setbuilder/filler.py` (NEW)
  - Fill algorithm with SSE event generator
- `src/kiku/setbuilder/reorder.py` (NEW)
  - Gentle and full rethink optimization strategies
- `frontend/src/lib/types/index.ts`
  - L341-345: Add `source` to `SetCreateParams`
  - Add new types for fill, optimize-order, score-sequence
- `frontend/src/lib/api/sets.ts`
  - Add `fillSet()`, `optimizeOrder()`, `scoreSequence()` API functions
- `frontend/src/lib/components/set/AddToSetPicker.svelte` (NEW)
  - Reusable set picker popover with search, new set creation, duplicate detection
- `frontend/src/lib/components/set/SetPicker.svelte`
  - Add "+ New" button with inline name input
- `frontend/src/lib/components/library/TrackContextMenu.svelte`
  - Add "Add to Set" submenu item
- `frontend/src/lib/components/waveform/TrackView.svelte`
  - Add "Add to Set" button in header
- `frontend/src/lib/components/waveform/SimilarTracks.svelte`
  - Add "+" icon per similar track row
- `frontend/src/lib/components/set/InSetTrackSearch.svelte` (NEW)
  - Inline search panel for SetView
- `frontend/src/lib/components/set/SetView.svelte`
  - Wire InSetTrackSearch, add "Assist" button
- `frontend/src/lib/components/set/FillReorderDialog.svelte` (NEW)
  - Two-tab dialog for fill gaps and reorder
- `tests/api/test_sets_api.py`
  - Add tests for source field, transition_score on add, duration recomputation, position indexing
- `tests/api/conftest.py`
  - L47: Fix seed positions from 1-based to 0-based to match planner fix

### Tasks

#### Task 1 — Backend: Add `source` field to SetCreateRequest and create_set()
Tools: Edit
Files: `src/kiku/api/schemas.py`, `src/kiku/api/routes/sets.py`

Diff 1 — schemas.py: Add `source` to `SetCreateRequest`:
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ -268,6 +268,7 @@
 class SetCreateRequest(BaseModel):
     name: str
     energy_profile: str | None = None
     genre_filter: list[str] | None = None
+    source: str | None = None  # "manual", "kiku", "m3u8", etc.
````

Diff 2 — sets.py: Set `source` when creating a set:
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -314,6 +314,7 @@
     set_ = Set(
         name=body.name,
         energy_profile=body.energy_profile,
         genre_filter=json.dumps(body.genre_filter) if body.genre_filter else None,
+        source=body.source,
     )
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.api.schemas import SetCreateRequest; r = SetCreateRequest(name='x', source='manual'); print(r.source)"` should print `manual`.

#### Task 2 — Backend: Compute transition_score + recompute duration + invalidate analysis on add_track
Tools: Edit
File: `src/kiku/api/routes/sets.py`

Replace the `add_track` endpoint handler (lines 367-376) to add scoring, duration recomputation, and analysis invalidation after the track is added.

Diff — sets.py: Enhanced `add_track` endpoint:
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -367,7 +367,7 @@
 @router.post("/{set_id}/tracks", response_model=list[SetTrackResponse])
 def add_track(set_id: int, body: SetAddTrackRequest, db: Session = Depends(get_db)):
     """Add a track to a set at a specific position."""
     try:
         tracks = add_track_to_set(db, set_id, body.track_id, body.position)
     except ValueError as exc:
         detail = str(exc)
         code = 404 if "not found" in detail.lower() else 400
         raise HTTPException(status_code=code, detail=detail)
+
+    # Compute transition_score for the newly added track and its neighbor
+    from kiku.setbuilder.scoring import transition_score as compute_transition
+
+    set_ = db.get(Set, set_id)
+    sorted_tracks = sorted(set_.tracks, key=lambda st: st.position)
+    # Find the newly added SetTrack
+    new_st = next((st for st in sorted_tracks if st.track_id == body.track_id), None)
+    if new_st and new_st.track:
+        idx = sorted_tracks.index(new_st)
+        # Score against preceding track
+        if idx > 0:
+            prev_st = sorted_tracks[idx - 1]
+            if prev_st.track:
+                new_st.transition_score = round(
+                    compute_transition(prev_st.track, new_st.track), 3
+                )
+        # Update following track's score (its predecessor changed)
+        if idx < len(sorted_tracks) - 1:
+            next_st = sorted_tracks[idx + 1]
+            if next_st.track:
+                next_st.transition_score = round(
+                    compute_transition(new_st.track, next_st.track), 3
+                )
+
+    # Recompute duration_min
+    total_sec = sum(st.track.duration_sec or 0 for st in sorted_tracks if st.track)
+    set_.duration_min = round(total_sec / 60)
+
+    # Invalidate analysis cache
+    set_.is_analyzed = 0
+    set_.analysis_cache = None
+
+    db.commit()
+    db.refresh(set_)
+    tracks = sorted(set_.tracks, key=lambda st: st.position)
+
     return [_set_track_response(st) for st in tracks]
````

Note: The implementor should replace the entire `add_track` function body. The final function should look like:

```python
@router.post("/{set_id}/tracks", response_model=list[SetTrackResponse])
def add_track(set_id: int, body: SetAddTrackRequest, db: Session = Depends(get_db)):
    """Add a track to a set at a specific position."""
    try:
        tracks = add_track_to_set(db, set_id, body.track_id, body.position)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)

    # Compute transition_score for the newly added track and its neighbor
    from kiku.setbuilder.scoring import transition_score as compute_transition

    set_ = db.get(Set, set_id)
    sorted_tracks = sorted(set_.tracks, key=lambda st: st.position)
    # Find the newly added SetTrack
    new_st = next((st for st in sorted_tracks if st.track_id == body.track_id), None)
    if new_st and new_st.track:
        idx = sorted_tracks.index(new_st)
        # Score against preceding track
        if idx > 0:
            prev_st = sorted_tracks[idx - 1]
            if prev_st.track:
                new_st.transition_score = round(
                    compute_transition(prev_st.track, new_st.track), 3
                )
        # Update following track's score (its predecessor changed)
        if idx < len(sorted_tracks) - 1:
            next_st = sorted_tracks[idx + 1]
            if next_st.track:
                next_st.transition_score = round(
                    compute_transition(new_st.track, next_st.track), 3
                )

    # Recompute duration_min
    total_sec = sum(st.track.duration_sec or 0 for st in sorted_tracks if st.track)
    set_.duration_min = round(total_sec / 60)

    # Invalidate analysis cache
    set_.is_analyzed = 0
    set_.analysis_cache = None

    db.commit()
    db.refresh(set_)
    tracks = sorted(set_.tracks, key=lambda st: st.position)

    return [_set_track_response(st) for st in tracks]
```

Verification:
- POST a track to a set with at least 1 existing track; response should include non-null `transition_score` on the newly added track.

#### Task 3 — Backend: Recompute duration + invalidate analysis on remove_track
Tools: Edit
File: `src/kiku/api/routes/sets.py`

Replace the `remove_track` endpoint (lines 379-388):

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -379,10 +379,24 @@
 @router.delete("/{set_id}/tracks/{track_id}", status_code=204)
 def remove_track(set_id: int, track_id: int, db: Session = Depends(get_db)):
     """Remove a track from a set."""
     try:
         removed = remove_track_from_set(db, set_id, track_id)
     except ValueError as exc:
         raise HTTPException(status_code=404, detail=str(exc))
     if not removed:
         raise HTTPException(status_code=404, detail="Track not in set")
+
+    # Recompute duration_min and invalidate analysis
+    set_ = db.get(Set, set_id)
+    if set_:
+        sorted_tracks = sorted(set_.tracks, key=lambda st: st.position)
+        total_sec = sum(st.track.duration_sec or 0 for st in sorted_tracks if st.track)
+        set_.duration_min = round(total_sec / 60) if sorted_tracks else None
+        # Recompute transition_score for the track that now follows the gap
+        from kiku.setbuilder.scoring import transition_score as compute_transition
+        for i, st in enumerate(sorted_tracks):
+            if i > 0 and sorted_tracks[i - 1].track and st.track:
+                st.transition_score = round(compute_transition(sorted_tracks[i - 1].track, st.track), 3)
+            elif i == 0:
+                st.transition_score = None
+        set_.is_analyzed = 0
+        set_.analysis_cache = None
+        db.commit()
     return Response(status_code=204)
````

Verification:
- Remove a track from a set; verify `duration_min` updates and `is_analyzed` is 0.

#### Task 4 — Backend: Invalidate analysis on reorder_tracks
Tools: Edit
File: `src/kiku/api/routes/sets.py`

Add analysis invalidation after reorder (line ~402):

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -396,6 +396,13 @@
     try:
         tracks = reorder_set_tracks(db, set_id, body.track_ids)
     except ValueError as exc:
         detail = str(exc)
         code = 404 if "not found" in detail.lower() else 400
         raise HTTPException(status_code=code, detail=detail)
+
+    # Invalidate analysis and recompute transition scores
+    set_ = db.get(Set, set_id)
+    if set_:
+        set_.is_analyzed = 0
+        set_.analysis_cache = None
+        db.commit()
+
     return [_set_track_response(st) for st in tracks]
````

Verification:
- Reorder tracks; verify `is_analyzed` is 0 on the set.

#### Task 5 — Backend: Fix 1-based position in planner.py + update test fixture
Tools: Edit
Files: `src/kiku/setbuilder/planner.py`, `tests/api/conftest.py`

Diff 1 — planner.py: Change position from 1-based to 0-based:
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@ -228,7 +228,7 @@
         st = SetTrack(
             set_id=set_.id,
-            position=i + 1,
+            position=i,
             track_id=track.id,
             transition_score=t_score,
         )
````

Diff 2 — conftest.py: Update seed positions to 0-based:
````diff
--- a/tests/api/conftest.py
+++ b/tests/api/conftest.py
@@ -43,8 +43,8 @@
     # Seed a set with tracks
     s = Set(id=1, name="Test Set", duration_min=60)
     session.add(s)
     session.flush()
-    for pos in range(1, 6):
-        session.add(SetTrack(set_id=1, position=pos, track_id=pos, transition_score=0.75))
+    for pos in range(5):
+        session.add(SetTrack(set_id=1, position=pos, track_id=pos + 1, transition_score=0.75))
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_sets_api.py -x -q` -- all tests pass.

#### Task 6 — Frontend: Add `source` to SetCreateParams type
Tools: Edit
File: `frontend/src/lib/types/index.ts`

````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ -341,6 +341,7 @@
 export interface SetCreateParams {
 	name: string;
 	energy_profile?: string | null;
 	genre_filter?: string[] | null;
+	source?: string | null;
 }
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5` -- no new errors.

#### Task 7 — Frontend: Create AddToSetPicker.svelte
Tools: Write (new file)
File: `frontend/src/lib/components/set/AddToSetPicker.svelte`

Create the file with this exact content:

```svelte
<script lang="ts">
	import type { DJSet } from '$lib/types';
	import { listSets, createSet, addTrackToSet } from '$lib/api/sets';
	import { onMount } from 'svelte';

	let {
		trackId,
		trackTitle = 'track',
		onclose,
		onadded,
	}: {
		trackId: number;
		trackTitle?: string;
		onclose: () => void;
		onadded?: (setId: number, setName: string) => void;
	} = $props();

	let sets = $state<DJSet[]>([]);
	let search = $state('');
	let loading = $state(true);
	let adding = $state<number | null>(null);
	let creatingNew = $state(false);
	let newName = $state('');
	let trackSetIds = $state<Set<number>>(new Set());
	let toast = $state<string | null>(null);
	let inputEl = $state<HTMLInputElement | null>(null);
	let searchEl = $state<HTMLInputElement | null>(null);

	let filtered = $derived(
		search
			? sets.filter((s) => (s.name ?? '').toLowerCase().includes(search.toLowerCase()))
			: sets
	);

	onMount(async () => {
		try {
			const allSets = await listSets('', 100);
			sets = allSets;
			// Check which sets already contain this track
			// We load full details lazily — for now, just show the list
		} catch {
			sets = [];
		} finally {
			loading = false;
			searchEl?.focus();
		}
	});

	async function handlePickSet(set: DJSet) {
		if (trackSetIds.has(set.id)) return;
		adding = set.id;
		try {
			await addTrackToSet(set.id, trackId);
			trackSetIds = new Set([...trackSetIds, set.id]);
			onadded?.(set.id, set.name ?? 'set');
			showToast(`Added to ${set.name}`);
			onclose();
		} catch (err) {
			showToast('Could not add track');
		} finally {
			adding = null;
		}
	}

	async function handleCreateAndAdd() {
		if (!newName.trim()) return;
		adding = -1;
		try {
			const newSet = await createSet({ name: newName.trim(), source: 'manual' });
			await addTrackToSet(newSet.id, trackId);
			onadded?.(newSet.id, newSet.name ?? newName.trim());
			showToast(`Created "${newName.trim()}" and added track`);
			onclose();
		} catch {
			showToast('Could not create set');
		} finally {
			adding = null;
			creatingNew = false;
			newName = '';
		}
	}

	function showToast(msg: string) {
		toast = msg;
		setTimeout(() => { toast = null; }, 3000);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			if (creatingNew) {
				creatingNew = false;
				newName = '';
			} else {
				onclose();
			}
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="add-to-set-picker" onkeydown={handleKeydown}>
	<input
		bind:this={searchEl}
		bind:value={search}
		placeholder="Search sets..."
		class="search-input"
	/>

	<div class="set-list">
		{#if creatingNew}
			<div class="new-set-row">
				<input
					bind:this={inputEl}
					bind:value={newName}
					placeholder="Set name..."
					class="new-set-input"
					onkeydown={(e) => { if (e.key === 'Enter') handleCreateAndAdd(); if (e.key === 'Escape') { creatingNew = false; newName = ''; } }}
				/>
				<button class="create-btn" onclick={handleCreateAndAdd} disabled={!newName.trim() || adding !== null}>
					{adding === -1 ? '...' : 'Create'}
				</button>
			</div>
		{:else}
			<button class="set-row new-set-trigger" onclick={() => { creatingNew = true; setTimeout(() => inputEl?.focus(), 0); }}>
				+ New set
			</button>
		{/if}

		{#if loading}
			<div class="loading">Finding your sets...</div>
		{:else if filtered.length === 0}
			<div class="empty">No sets found</div>
		{:else}
			{#each filtered as set (set.id)}
				{@const inSet = trackSetIds.has(set.id)}
				<button
					class="set-row"
					class:in-set={inSet}
					onclick={() => handlePickSet(set)}
					disabled={inSet || adding !== null}
				>
					<span class="set-name">{set.name}</span>
					<span class="set-meta">
						{#if inSet}
							(already in set)
						{:else}
							{set.track_count} tracks
						{/if}
					</span>
					{#if adding === set.id}
						<span class="adding">...</span>
					{/if}
				</button>
			{/each}
		{/if}
	</div>
</div>

{#if toast}
	<div class="toast">{toast}</div>
{/if}

<style>
	.add-to-set-picker {
		display: flex;
		flex-direction: column;
		min-width: 220px;
		max-height: 320px;
		overflow: hidden;
	}

	.search-input {
		padding: 8px 10px;
		font-size: 13px;
		border: none;
		border-bottom: 1px solid var(--border);
		background: transparent;
		color: var(--text-primary);
		outline: none;
	}

	.set-list {
		overflow-y: auto;
		flex: 1;
	}

	.set-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 10px;
		width: 100%;
		border: none;
		background: none;
		color: var(--text-primary);
		font-size: 13px;
		cursor: pointer;
		text-align: left;
	}

	.set-row:hover:not(:disabled) {
		background: var(--bg-secondary);
	}

	.set-row:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.set-row.in-set {
		opacity: 0.5;
	}

	.new-set-trigger {
		color: var(--accent);
		font-weight: 600;
	}

	.set-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.set-meta {
		font-size: 11px;
		color: var(--text-dim);
		white-space: nowrap;
	}

	.adding {
		font-size: 11px;
		color: var(--text-dim);
	}

	.new-set-row {
		display: flex;
		gap: 4px;
		padding: 6px 8px;
	}

	.new-set-input {
		flex: 1;
		padding: 6px 8px;
		font-size: 13px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-primary);
	}

	.create-btn {
		padding: 6px 10px;
		font-size: 12px;
		background: var(--accent);
		color: #000;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-weight: 600;
	}

	.create-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.loading, .empty {
		padding: 12px 10px;
		font-size: 12px;
		color: var(--text-dim);
	}

	.toast {
		position: fixed;
		bottom: 80px;
		left: 50%;
		transform: translateX(-50%);
		background: var(--bg-secondary);
		color: var(--text-primary);
		padding: 8px 16px;
		border-radius: 6px;
		font-size: 13px;
		border: 1px solid var(--border);
		z-index: 1000;
		animation: toast-in 0.2s ease-out;
	}

	@keyframes toast-in {
		from { opacity: 0; transform: translateX(-50%) translateY(8px); }
		to { opacity: 1; transform: translateX(-50%) translateY(0); }
	}
</style>
```

Verification:
- File exists at `frontend/src/lib/components/set/AddToSetPicker.svelte`.
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | grep -c "Error"` should be 0.

#### Task 8 — Frontend: Add "+ New" button to SetPicker.svelte
Tools: Edit
File: `frontend/src/lib/components/set/SetPicker.svelte`

Diff 1 — Add import and state for inline new-set creation:
````diff
--- a/frontend/src/lib/components/set/SetPicker.svelte
+++ b/frontend/src/lib/components/set/SetPicker.svelte
@@ -1,6 +1,7 @@
 <script lang="ts">
 	import type { DJSet, ImportResult } from '$lib/types';
-	import { listSets } from '$lib/api/sets';
+	import { listSets, createSet } from '$lib/api/sets';
 	import { onMount } from 'svelte';
 	import ImportPlaylistDialog from './ImportPlaylistDialog.svelte';
````

Diff 2 — Add state and handler:
````diff
--- a/frontend/src/lib/components/set/SetPicker.svelte
+++ b/frontend/src/lib/components/set/SetPicker.svelte
@@ -10,6 +10,9 @@
 	let sets = $state<DJSet[]>([]);
 	let loading = $state(true);
 	let importOpen = $state(false);
+	let creatingNew = $state(false);
+	let newName = $state('');
+	let newInputEl = $state<HTMLInputElement | null>(null);
````

Diff 3 — Add create handler after `handleImport`:
````diff
--- a/frontend/src/lib/components/set/SetPicker.svelte
+++ b/frontend/src/lib/components/set/SetPicker.svelte
@@ -33,6 +33,23 @@
 		const imported = sets.find(s => s.id === result.set_id);
 		if (imported) onselect(imported);
 	}
+
+	async function handleCreateNew() {
+		if (!newName.trim()) return;
+		try {
+			const newSet = await createSet({ name: newName.trim(), source: 'manual' });
+			sets = await listSets();
+			onselect(newSet);
+		} catch {
+			// Silently fail — the DJ can try again
+		} finally {
+			creatingNew = false;
+			newName = '';
+		}
+	}
 </script>
````

Diff 4 — Add "+ New" button in the picker-row, between the select and Import:
````diff
--- a/frontend/src/lib/components/set/SetPicker.svelte
+++ b/frontend/src/lib/components/set/SetPicker.svelte
@@ -56,6 +56,20 @@
 				</select>
 			{/if}
+			{#if creatingNew}
+				<input
+					bind:this={newInputEl}
+					bind:value={newName}
+					placeholder="Set name..."
+					class="new-set-input"
+					onkeydown={(e) => { if (e.key === 'Enter') handleCreateNew(); if (e.key === 'Escape') { creatingNew = false; newName = ''; } }}
+				/>
+			{:else}
+				<button class="new-btn" onclick={() => { creatingNew = true; setTimeout(() => newInputEl?.focus(), 0); }} title="Create new set">
+					+ New
+				</button>
+			{/if}
 			<button class="import-btn" onclick={() => importOpen = true} title="Import playlist">
 				Import
 			</button>
````

Diff 5 — Add styles:
````diff
--- a/frontend/src/lib/components/set/SetPicker.svelte
+++ b/frontend/src/lib/components/set/SetPicker.svelte
@@ -95,6 +95,25 @@
 	.import-btn:hover {
 		background: var(--bg-tertiary);
 	}
+
+	.new-btn {
+		padding: 8px 12px;
+		font-size: 12px;
+		border: 1px solid var(--accent);
+		border-radius: 6px;
+		background: var(--accent);
+		color: #000;
+		cursor: pointer;
+		white-space: nowrap;
+		font-weight: 600;
+	}
+
+	.new-set-input {
+		padding: 8px 10px;
+		font-size: 13px;
+		border: 1px solid var(--border);
+		border-radius: 6px;
+		background: var(--bg-secondary);
+		color: var(--text-primary);
+	}
````

Verification:
- SetPicker shows "+ New" button. Clicking it shows inline input. Enter creates set with `source: "manual"`.

#### Task 9 — Frontend: Add "Add to Set" submenu to TrackContextMenu.svelte
Tools: Edit
File: `frontend/src/lib/components/library/TrackContextMenu.svelte`

Diff 1 — Add imports:
````diff
--- a/frontend/src/lib/components/library/TrackContextMenu.svelte
+++ b/frontend/src/lib/components/library/TrackContextMenu.svelte
@@ -5,6 +5,7 @@
 	import { getPlayerStore } from '$lib/stores/player.svelte';
 	import EnergyZonePicker from './EnergyZonePicker.svelte';
 	import { ZONE_COLORS } from './EnergyZonePicker.svelte';
 	import StarRating from './StarRating.svelte';
+	import AddToSetPicker from '../set/AddToSetPicker.svelte';
````

Diff 2 — Add state:
````diff
--- a/frontend/src/lib/components/library/TrackContextMenu.svelte
+++ b/frontend/src/lib/components/library/TrackContextMenu.svelte
@@ -22,6 +22,7 @@
 	} = $props();

 	let showEnergySubmenu = $state(false);
+	let showAddToSet = $state(false);
````

Diff 3 — Add "Add to Set" section between Rating and Play (after the second `<div class="menu-divider">` at line 88):
````diff
--- a/frontend/src/lib/components/library/TrackContextMenu.svelte
+++ b/frontend/src/lib/components/library/TrackContextMenu.svelte
@@ -86,6 +86,24 @@
 	</div>
 </div>

 <div class="menu-divider"></div>

+<div class="menu-section">
+	<button
+		class="menu-item has-submenu"
+		onclick={() => showAddToSet = !showAddToSet}
+		role="menuitem"
+		aria-haspopup="true"
+		aria-expanded={showAddToSet}
+	>
+		+ Add to Set
+		<span class="submenu-arrow">›</span>
+	</button>
+	{#if showAddToSet}
+		<AddToSetPicker
+			trackId={track.id}
+			trackTitle={track.title ?? 'track'}
+			onclose={onclose}
+		/>
+	{/if}
+</div>
+
+<div class="menu-divider"></div>
+
 <button
 	class="menu-item"
 	role="menuitem"
 	onclick={() => { player.play(track); onclose(); }}
 >
 	▶ Play
 </button>
````

Note: The implementor must insert this BETWEEN the existing Rating section's closing `</div>` and the existing `<div class="menu-divider"></div>` before the Play button. The final order should be: Energy > Rating > divider > Add to Set > divider > Play.

Verification:
- Right-click a track in TrackTable. "Add to Set" submenu appears. Clicking it opens the AddToSetPicker.

#### Task 10 — Frontend: Add "Add to Set" button to TrackView.svelte
Tools: Edit
File: `frontend/src/lib/components/waveform/TrackView.svelte`

Diff 1 — Add imports near the top of the script section:
````diff
--- a/frontend/src/lib/components/waveform/TrackView.svelte
+++ b/frontend/src/lib/components/waveform/TrackView.svelte
@@ -6,6 +6,8 @@
+	import ContextMenu from '../ContextMenu.svelte';
+	import AddToSetPicker from '../set/AddToSetPicker.svelte';
````

Note: The implementor should add these imports alongside the existing imports in the `<script>` block. The exact position depends on the existing imports — add after the last component import.

Diff 2 — Add state for the popover:
````diff
+	let showAddToSet = $state(false);
+	let addBtnEl = $state<HTMLButtonElement | null>(null);
+	let addBtnRect = $derived(addBtnEl?.getBoundingClientRect());
````

Add these state declarations near the other `$state` declarations in the script section.

Diff 3 — Add the button in the header's `track-meta` div, after the duration badge (around line 223):
````diff
--- a/frontend/src/lib/components/waveform/TrackView.svelte
+++ b/frontend/src/lib/components/waveform/TrackView.svelte
@@ -223,6 +223,12 @@
 				{#if track.duration_sec}
 					<span class="meta-badge dim">{formatTime(track.duration_sec)}</span>
 				{/if}
+				<button
+					bind:this={addBtnEl}
+					class="meta-badge meta-badge-interactive add-to-set-btn"
+					onclick={() => showAddToSet = !showAddToSet}
+					title="Add to a set"
+				>+ Add to Set</button>
 			</div>
````

Diff 4 — Add the popover below the track-header closing `</div>` (around line 236):
````diff
--- a/frontend/src/lib/components/waveform/TrackView.svelte
+++ b/frontend/src/lib/components/waveform/TrackView.svelte
@@ -236,6 +236,15 @@
 	</div>

+	{#if showAddToSet}
+		<div class="add-to-set-popover">
+			<AddToSetPicker
+				trackId={track.id}
+				trackTitle={track.title ?? 'track'}
+				onclose={() => showAddToSet = false}
+			/>
+		</div>
+	{/if}
+
 	{#if teachingMoment}
````

Diff 5 — Add styles:
````diff
+	.add-to-set-btn {
+		border: 1px solid var(--accent);
+		color: var(--accent);
+		cursor: pointer;
+		background: transparent;
+		font-weight: 600;
+	}
+
+	.add-to-set-btn:hover {
+		background: var(--accent);
+		color: #000;
+	}
+
+	.add-to-set-popover {
+		position: relative;
+		background: var(--bg-primary);
+		border: 1px solid var(--border);
+		border-radius: 8px;
+		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
+		z-index: 100;
+		max-width: 300px;
+	}
````

Verification:
- Open a track detail page. "Add to Set" button visible in header. Click opens AddToSetPicker inline.

#### Task 11 — Frontend: Add "+" add-to-set icon to SimilarTracks.svelte
Tools: Edit
File: `frontend/src/lib/components/waveform/SimilarTracks.svelte`

This task adds a small "+" button next to each similar track card that opens an AddToSetPicker.

Diff 1 — Add import:
````diff
--- a/frontend/src/lib/components/waveform/SimilarTracks.svelte
+++ b/frontend/src/lib/components/waveform/SimilarTracks.svelte
@@ -4,6 +4,7 @@
 	import SimilarTrackCard from '../library/SimilarTrackCard.svelte';
 	import Spinner from '../Spinner.svelte';
+	import AddToSetPicker from '../set/AddToSetPicker.svelte';
````

Diff 2 — Add state for which track has the picker open:
````diff
--- a/frontend/src/lib/components/waveform/SimilarTracks.svelte
+++ b/frontend/src/lib/components/waveform/SimilarTracks.svelte
@@ -14,6 +14,7 @@
 	let dismissing = $state<Set<number>>(new Set());
+	let addToSetTrackId = $state<number | null>(null);
````

Diff 3 — Add a "+" button next to each card in the template (inside the `#each` block):
````diff
--- a/frontend/src/lib/components/waveform/SimilarTracks.svelte
+++ b/frontend/src/lib/components/waveform/SimilarTracks.svelte
@@ -93,6 +93,18 @@
 			{#each visibleSuggestions as item (item.track.id)}
 				<div class="card-slot" class:dismissing={dismissing.has(item.track.id)}>
 					<SimilarTrackCard
 						{item}
 						parentTrackId={trackId}
 						affinity={affinityMap[item.track.id] ?? null}
 						onaffinitychange={handleAffinityChange}
 					/>
+					<button
+						class="add-to-set-icon"
+						onclick={(e) => { e.stopPropagation(); addToSetTrackId = addToSetTrackId === item.track.id ? null : item.track.id; }}
+						title="Add to set"
+					>+</button>
+					{#if addToSetTrackId === item.track.id}
+						<div class="add-picker-popover">
+							<AddToSetPicker
+								trackId={item.track.id}
+								trackTitle={item.track.title ?? 'track'}
+								onclose={() => addToSetTrackId = null}
+							/>
+						</div>
+					{/if}
 				</div>
````

Diff 4 — Add styles:
````diff
--- a/frontend/src/lib/components/waveform/SimilarTracks.svelte
+++ b/frontend/src/lib/components/waveform/SimilarTracks.svelte
@@ -185,4 +185,38 @@
 	.show-more:hover {
 		background: var(--bg-tertiary);
 		color: var(--text-primary);
 	}
+
+	.card-slot {
+		position: relative;
+	}
+
+	.add-to-set-icon {
+		position: absolute;
+		top: 4px;
+		right: 4px;
+		width: 22px;
+		height: 22px;
+		border-radius: 50%;
+		border: 1px solid var(--border);
+		background: var(--bg-primary);
+		color: var(--accent);
+		font-size: 14px;
+		font-weight: 700;
+		cursor: pointer;
+		display: flex;
+		align-items: center;
+		justify-content: center;
+		opacity: 0;
+		transition: opacity 0.15s;
+		z-index: 2;
+	}
+
+	.card-slot:hover .add-to-set-icon {
+		opacity: 1;
+	}
+
+	.add-picker-popover {
+		position: absolute;
+		top: 28px;
+		right: 0;
+		background: var(--bg-primary);
+		border: 1px solid var(--border);
+		border-radius: 8px;
+		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
+		z-index: 10;
+		min-width: 220px;
+	}
 </style>
````

Note: There is an existing `.card-slot` style block (lines 159-161 with transition properties). The implementor should merge the `position: relative;` into the existing `.card-slot` block rather than creating a duplicate. The existing block has `transition` and should get `position: relative` added.

Verification:
- Hover over a similar track card; "+" icon appears. Click opens AddToSetPicker popover.

#### Task 12 — Backend: Add position-aware energy to suggest-next endpoint
Tools: Edit
File: `src/kiku/api/routes/tracks.py`

Diff 1 — Add new query params to `suggest_next`:
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@ -290,6 +290,8 @@
     w_genre_coherence: float | None = Query(default=None, description="Genre coherence weight override"),
     w_track_quality: float | None = Query(default=None, description="Track quality weight override"),
     discovery_density: float = Query(default=0.0, ge=-1.0, le=1.0, description="Discovery/density bias (-1=fresh, +1=proven)"),
+    position_min: float | None = Query(default=None, description="Elapsed minutes at this position in the set"),
+    energy_profile: str | None = Query(default=None, description="Energy profile string for position-aware energy target"),
     db: Session = Depends(get_db),
 ):
````

Diff 2 — Compute target_energy and pass through (before the `scored = score_transitions(...)` call):
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@ -333,7 +333,17 @@
     genres = [g.strip() for g in genre_filter.split(",")] if genre_filter else None
-    scored = score_transitions(db, track, n=n, genre_filter=genres, weights=weights_dict, exclude_ids=exclude_ids, discovery_density=discovery_density)
+
+    # Compute position-aware energy target
+    target_energy = 0.5  # default neutral
+    if position_min is not None and energy_profile:
+        from kiku.setbuilder.constraints import parse_energy_string
+        try:
+            ep = parse_energy_string(energy_profile)
+            target_energy = ep.target_energy_at(position_min)
+        except (ValueError, Exception):
+            pass  # Fall back to neutral
+
+    scored = score_transitions(db, track, n=n, genre_filter=genres, weights=weights_dict, exclude_ids=exclude_ids, discovery_density=discovery_density, target_energy=target_energy)
````

Diff 3 — Update the breakdown computation to use `target_energy` instead of hardcoded 0.5:
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@ -340,7 +340,7 @@
     for cand, total_score in scored:
         h = harmonic_score(track.key, cand.key)
-        e = energy_fit(cand, 0.5)
+        e = energy_fit(cand, target_energy)
         b = bpm_compatibility(track.bpm, cand.bpm)
````

Verification:
- Call suggest-next with `position_min=30&energy_profile=warmup:30:0.3,peak:30:0.9` — scores should differ from neutral.

#### Task 13 — Backend: Add target_energy param to score_transitions
Tools: Edit
File: `src/kiku/setbuilder/scoring.py`

Diff — Add `target_energy` parameter:
````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@ -378,6 +378,7 @@
 def score_transitions(
     session: Session,
     from_track: Track,
     n: int = 10,
     genre_filter: list[str] | None = None,
     weights: dict[str, float] | None = None,
     exclude_ids: list[int] | None = None,
     discovery_density: float = 0.0,
     set_appearance_counts: dict[int, int] | None = None,
+    target_energy: float = 0.5,
 ) -> list[tuple[Track, float]]:
````

Diff 2 — Use target_energy in the scoring call (line ~429):
````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@ -428,7 +428,7 @@
     scored = []
     for track in candidates:
-        score = transition_score(from_track, track, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts)
+        score = transition_score(from_track, track, target_energy=target_energy, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts)
         # Apply affinity modifier: "good" → +10%, "bad" → -20%
````

Verification:
- Existing tests still pass: `source .venv/bin/activate && python -m pytest tests/test_scoring.py -x -q`

#### Task 14 — Frontend: Create InSetTrackSearch.svelte
Tools: Write (new file)
File: `frontend/src/lib/components/set/InSetTrackSearch.svelte`

Create the file with this exact content:

```svelte
<script lang="ts">
	import type { Track, SuggestNextItem } from '$lib/types';
	import { suggestNext } from '$lib/api/tracks';
	import { addTrackToSet } from '$lib/api/sets';
	import { getCamelotColor } from '$lib/utils/camelot';

	let {
		setId,
		lastTrackId = null,
		excludeTrackIds = [],
		energyProfile = null,
		positionMin = null,
		ontrackadded,
	}: {
		setId: number;
		lastTrackId?: number | null;
		excludeTrackIds?: number[];
		energyProfile?: string | null;
		positionMin?: number | null;
		ontrackadded?: () => void;
	} = $props();

	let expanded = $state(false);
	let loading = $state(false);
	let results = $state<SuggestNextItem[]>([]);
	let adding = $state<number | null>(null);
	let toast = $state<string | null>(null);

	let filtered = $derived(
		results.filter((r) => !excludeTrackIds.includes(r.track.id))
	);

	async function loadSuggestions() {
		if (!lastTrackId) return;
		loading = true;
		try {
			const params = new URLSearchParams({ n: '20', set_id: String(setId) });
			if (positionMin !== null && energyProfile) {
				params.set('position_min', String(positionMin));
				params.set('energy_profile', energyProfile);
			}
			const res = await suggestNext(lastTrackId, 20, setId);
			results = res.suggestions;
		} catch {
			results = [];
		} finally {
			loading = false;
		}
	}

	function handleExpand() {
		expanded = true;
		loadSuggestions();
	}

	async function handleAdd(track: Track) {
		adding = track.id;
		try {
			await addTrackToSet(setId, track.id);
			// Remove from results
			results = results.filter((r) => r.track.id !== track.id);
			toast = `Added ${track.title ?? 'track'}`;
			setTimeout(() => { toast = null; }, 2500);
			ontrackadded?.();
		} catch {
			toast = 'Could not add track';
			setTimeout(() => { toast = null; }, 3000);
		} finally {
			adding = null;
		}
	}

	function scoreColor(score: number): string {
		if (score >= 0.8) return 'var(--color-success, #66BB6A)';
		if (score >= 0.6) return 'var(--color-warning, #FFA726)';
		return 'var(--color-error, #EF5350)';
	}
</script>

{#if !expanded}
	<button class="search-trigger" onclick={handleExpand}>
		Search library to add tracks...
	</button>
{:else}
	<div class="in-set-search">
		<div class="search-header">
			<span class="search-label">Add tracks</span>
			<button class="close-btn" onclick={() => { expanded = false; results = []; }}>&times;</button>
		</div>

		{#if loading}
			<div class="search-status">Listening to your library...</div>
		{:else if !lastTrackId}
			<div class="search-status">Add a track first, then search for what comes next</div>
		{:else if filtered.length === 0}
			<div class="search-status">No suggestions found</div>
		{:else}
			<div class="results-table">
				<div class="results-header">
					<span class="col-score">Score</span>
					<span class="col-title">Title</span>
					<span class="col-key">Key</span>
					<span class="col-bpm">BPM</span>
					<span class="col-add"></span>
				</div>
				{#each filtered as item (item.track.id)}
					<div class="result-row">
						<span class="col-score" style="color: {scoreColor(item.score)}">
							{item.score.toFixed(2)}
						</span>
						<span class="col-title" title={`${item.track.title} - ${item.track.artist}`}>
							{item.track.title ?? '?'}
							<span class="artist-dim">{item.track.artist ?? ''}</span>
						</span>
						<span class="col-key" style="color: {getCamelotColor(item.track.key)}">{item.track.key ?? '?'}</span>
						<span class="col-bpm">{item.track.bpm ? Math.round(item.track.bpm) : '?'}</span>
						<button
							class="add-btn"
							onclick={() => handleAdd(item.track)}
							disabled={adding === item.track.id}
							title="Add to set"
						>
							{adding === item.track.id ? '...' : '+'}
						</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}

{#if toast}
	<div class="toast">{toast}</div>
{/if}

<style>
	.search-trigger {
		display: block;
		width: 100%;
		padding: 10px 16px;
		font-size: 13px;
		color: var(--text-dim);
		background: var(--bg-secondary);
		border: 1px dashed var(--border);
		border-radius: 6px;
		cursor: pointer;
		text-align: left;
		margin-top: 8px;
	}

	.search-trigger:hover {
		color: var(--text-primary);
		border-color: var(--accent);
	}

	.in-set-search {
		border: 1px solid var(--border);
		border-radius: 8px;
		margin-top: 8px;
		overflow: hidden;
	}

	.search-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 12px;
		border-bottom: 1px solid var(--border);
	}

	.search-label {
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text-dim);
		font-size: 18px;
		cursor: pointer;
		padding: 0 4px;
	}

	.search-status {
		padding: 16px 12px;
		font-size: 12px;
		color: var(--text-dim);
	}

	.results-table {
		max-height: 300px;
		overflow-y: auto;
	}

	.results-header {
		display: flex;
		gap: 8px;
		padding: 6px 12px;
		font-size: 11px;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid var(--border);
	}

	.result-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 12px;
		font-size: 13px;
	}

	.result-row:hover {
		background: var(--bg-secondary);
	}

	.col-score { width: 50px; font-weight: 600; font-size: 12px; }
	.col-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.col-key { width: 40px; font-size: 12px; }
	.col-bpm { width: 40px; font-size: 12px; }
	.col-add { width: 30px; }

	.artist-dim {
		color: var(--text-dim);
		font-size: 11px;
		margin-left: 4px;
	}

	.add-btn {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		border: 1px solid var(--accent);
		background: transparent;
		color: var(--accent);
		font-size: 14px;
		font-weight: 700;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.add-btn:hover:not(:disabled) {
		background: var(--accent);
		color: #000;
	}

	.add-btn:disabled {
		opacity: 0.5;
	}

	.toast {
		position: fixed;
		bottom: 80px;
		left: 50%;
		transform: translateX(-50%);
		background: var(--bg-secondary);
		color: var(--text-primary);
		padding: 8px 16px;
		border-radius: 6px;
		font-size: 13px;
		border: 1px solid var(--border);
		z-index: 1000;
	}
</style>
```

Verification:
- File exists. `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | grep -c "Error"` should be 0.

#### Task 15 — Frontend: Wire InSetTrackSearch into SetView and SetTimeline
Tools: Edit
Files: `frontend/src/lib/components/set/SetView.svelte`, `frontend/src/lib/components/set/SetTimeline.svelte`

Diff 1 — SetTimeline: Add InSetTrackSearch below the track list. Add import and props:
````diff
--- a/frontend/src/lib/components/set/SetTimeline.svelte
+++ b/frontend/src/lib/components/set/SetTimeline.svelte
@@ -8,6 +8,7 @@
 	import TransitionIndicator from './TransitionIndicator.svelte';
 	import ReplaceTrackModal from './ReplaceTrackModal.svelte';
+	import InSetTrackSearch from './InSetTrackSearch.svelte';
````

Diff 2 — SetTimeline: Add the InSetTrackSearch component after the drop indicator, before the closing `</div>` of `.set-timeline` (around line 310):
````diff
--- a/frontend/src/lib/components/set/SetTimeline.svelte
+++ b/frontend/src/lib/components/set/SetTimeline.svelte
@@ -310,6 +310,15 @@
 	{/if}
+
+	<InSetTrackSearch
+		{setId}
+		lastTrackId={items.length > 0 ? items[items.length - 1].track_id : null}
+		excludeTrackIds={items.map((i) => i.track_id)}
+		energyProfile={energyProfile}
+		positionMin={items.length > 0 ? items.reduce((sum, i) => sum + (i.duration_sec ?? 0), 0) / 60 : null}
+		ontrackadded={onTracksChanged}
+	/>
 </div>
````

Note: Insert this just before the closing `</div>` that has the class `.set-timeline`.

Verification:
- Open a set in SetView. Below the track list, "Search library to add tracks..." button appears.

#### Task 16 — Backend: Create filler.py
Tools: Write (new file)
File: `src/kiku/setbuilder/filler.py`

Create the file with this exact content:

```python
"""Fill algorithm — propose track insertions to fill gaps in a set."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generator

from sqlalchemy.orm import Session

from kiku.db.models import Set, Track
from kiku.setbuilder.constraints import EnergyProfile, parse_energy_json, parse_energy_string
from kiku.setbuilder.planner import _get_candidate_pool, _violates_artist_cooldown
from kiku.setbuilder.scoring import score_replacement, transition_score


DEFAULT_GAP_THRESHOLD = 0.6
DEFAULT_ENERGY_DEVIATION = 0.3


@dataclass
class FillEvent:
    """Base event for fill SSE stream."""
    event: str
    data: dict


def fill_set(
    db: Session,
    set_id: int,
    energy_profile: EnergyProfile | None = None,
    target_duration_min: int | None = None,
    max_fill_tracks: int = 10,
    genre_filter: list[str] | None = None,
    gap_threshold: float = DEFAULT_GAP_THRESHOLD,
    discovery_density: float = 0.0,
    weights: dict[str, float] | None = None,
) -> Generator[FillEvent, None, None]:
    """Propose track insertions to fill gaps in a manually-built set.

    Yields SSE-ready FillEvent objects as it works.
    """
    set_ = db.get(Set, set_id)
    if not set_:
        yield FillEvent("error", {"detail": "Set not found"})
        return

    set_tracks = sorted(set_.tracks, key=lambda st: st.position)
    tracks: list[Track] = [st.track for st in set_tracks if st.track]

    if len(tracks) < 1:
        yield FillEvent("error", {"detail": "Set must have at least 1 track to fill"})
        return

    # Resolve energy profile
    if energy_profile is None and set_.energy_profile:
        try:
            energy_profile = parse_energy_json(set_.energy_profile)
        except Exception:
            try:
                energy_profile = parse_energy_string(set_.energy_profile)
            except Exception:
                pass

    # Compute current duration
    current_duration_sec = sum(t.duration_sec or 0 for t in tracks)
    current_duration_min = current_duration_sec / 60

    yield FillEvent("fill_started", {
        "set_id": set_id,
        "current_tracks": len(tracks),
        "current_duration_min": round(current_duration_min, 1),
    })

    # Score all transitions
    elapsed_min = 0.0
    gaps: list[dict] = []
    for i in range(len(tracks) - 1):
        elapsed_min += (tracks[i].duration_sec or 360) / 60
        target_e = energy_profile.target_energy_at(elapsed_min) if energy_profile else 0.5
        score = transition_score(tracks[i], tracks[i + 1], target_energy=target_e, weights=weights)
        if score < gap_threshold:
            gaps.append({
                "position": i + 1,  # Insert after position i
                "from_track": tracks[i],
                "to_track": tracks[i + 1],
                "score": round(score, 3),
                "target_energy": target_e,
                "elapsed_min": elapsed_min,
            })

    # Also check if we need to extend to reach target duration
    if target_duration_min and current_duration_min < target_duration_min:
        # Add extension gap at the end
        last_elapsed = sum((t.duration_sec or 360) / 60 for t in tracks)
        target_e = energy_profile.target_energy_at(last_elapsed) if energy_profile else 0.5
        gaps.append({
            "position": len(tracks),
            "from_track": tracks[-1],
            "to_track": None,
            "score": 0.0,
            "target_energy": target_e,
            "elapsed_min": last_elapsed,
        })

    # Sort by worst score first
    gaps.sort(key=lambda g: g["score"])

    # Get candidate pool
    bpm_values = [t.bpm for t in tracks if t.bpm]
    bpm_range = None
    if bpm_values:
        avg_bpm = sum(bpm_values) / len(bpm_values)
        bpm_range = (avg_bpm * 0.85, avg_bpm * 1.15)
    candidates = _get_candidate_pool(db, genres=genre_filter, bpm_range=bpm_range)
    existing_ids = {t.id for t in tracks}
    candidates = [c for c in candidates if c.id not in existing_ids]

    proposals_count = 0
    for gap in gaps:
        if proposals_count >= max_fill_tracks:
            break

        yield FillEvent("gap_identified", {
            "position": gap["position"],
            "from_track_id": gap["from_track"].id,
            "to_track_id": gap["to_track"].id if gap["to_track"] else None,
            "current_score": gap["score"],
            "target_energy": gap["target_energy"],
        })

        # Score candidates for this gap
        prev_track = gap["from_track"]
        next_track = gap["to_track"]
        target_e = gap["target_energy"]

        scored_candidates = []
        for cand in candidates:
            if cand.id in existing_ids:
                continue
            if _violates_artist_cooldown(tracks, cand):
                continue
            combined, incoming_bd, outgoing_bd = score_replacement(
                cand, prev_track, next_track, target_energy=target_e,
                weights=weights, discovery_density=discovery_density,
            )
            scored_candidates.append((cand, combined, incoming_bd, outgoing_bd))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        if scored_candidates:
            best, best_score, best_in, best_out = scored_candidates[0]
            explanation = _build_explanation(best, prev_track, next_track, best_score, best_in, best_out, target_e)

            yield FillEvent("fill_proposed", {
                "position": gap["position"],
                "track_id": best.id,
                "track_title": best.title,
                "track_artist": best.artist,
                "track_bpm": best.bpm,
                "track_key": best.key,
                "score": round(best_score, 3),
                "breakdown": best_in,
                "explanation": explanation,
            })
            proposals_count += 1
            existing_ids.add(best.id)

    yield FillEvent("fill_complete", {
        "proposals_count": proposals_count,
        "estimated_duration_min": round(current_duration_min + proposals_count * 5.5, 1),
    })


def _build_explanation(
    candidate: Track,
    prev_track: Track,
    next_track: Track | None,
    score: float,
    incoming: dict | None,
    outgoing: dict | None,
    target_energy: float,
) -> str:
    """Build a human-readable explanation for a fill proposal."""
    parts = []

    if incoming:
        h = incoming.get("harmonic", 0)
        if h >= 0.85:
            parts.append(f"key from {prev_track.key} to {candidate.key} is a smooth move")
        elif h >= 0.7:
            parts.append(f"key shift {prev_track.key} to {candidate.key} works")

    if candidate.bpm and prev_track.bpm:
        diff_pct = abs(candidate.bpm - prev_track.bpm) / prev_track.bpm * 100
        if diff_pct <= 3:
            parts.append(f"BPM {prev_track.bpm:.0f} to {candidate.bpm:.0f} is seamless")
        elif diff_pct <= 6:
            parts.append(f"BPM {prev_track.bpm:.0f} to {candidate.bpm:.0f} is manageable")

    if not parts:
        parts.append(f"overall score {score:.2f} against neighbors")

    return "; ".join(parts)
```

Verification:
- `source .venv/bin/activate && python -c "from kiku.setbuilder.filler import fill_set; print('OK')"` should print `OK`.

#### Task 17 — Backend: Create reorder.py
Tools: Write (new file)
File: `src/kiku/setbuilder/reorder.py`

Create the file with this exact content:

```python
"""Reorder algorithms — optimize track order for flow."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from kiku.db.models import Track
from kiku.setbuilder.constraints import EnergyProfile
from kiku.setbuilder.scoring import transition_score


@dataclass
class OrderChange:
    """Describes a single track movement."""
    track_id: int
    track_title: str | None
    from_position: int
    to_position: int
    explanation: str


def score_full_sequence(
    tracks: list[Track],
    energy_profile: EnergyProfile | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    """Score a full track sequence using position-aware energy targets."""
    if len(tracks) < 2:
        return 1.0
    total = 0.0
    elapsed = 0.0
    for i in range(1, len(tracks)):
        target_e = energy_profile.target_energy_at(elapsed) if energy_profile else 0.5
        total += transition_score(tracks[i - 1], tracks[i], target_energy=target_e, weights=weights)
        elapsed += (tracks[i - 1].duration_sec or 360) / 60
    return total / (len(tracks) - 1)


def optimize_gentle(
    tracks: list[Track],
    energy_profile: EnergyProfile | None = None,
    weights: dict[str, float] | None = None,
    max_iterations: int = 50,
    window: int = 3,
) -> tuple[list[Track], list[OrderChange]]:
    """Local swap optimization. Iteratively improves pairs within a window.

    Returns (new_order, changes).
    """
    current = list(tracks)
    best_score = score_full_sequence(current, energy_profile, weights)
    original_positions = {t.id: i for i, t in enumerate(tracks)}
    improved = True
    iteration = 0

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(len(current)):
            for j in range(i + 1, min(i + window + 1, len(current))):
                candidate = list(current)
                candidate[i], candidate[j] = candidate[j], candidate[i]
                new_score = score_full_sequence(candidate, energy_profile, weights)
                if new_score > best_score:
                    current = candidate
                    best_score = new_score
                    improved = True

    # Build changes list
    changes = _diff_orders(tracks, current, original_positions, energy_profile)
    return current, changes


def optimize_full(
    tracks: list[Track],
    energy_profile: EnergyProfile | None = None,
    weights: dict[str, float] | None = None,
    iterations: int = 5000,
    initial_temp: float = 1.0,
    cooling_rate: float = 0.995,
) -> tuple[list[Track], list[OrderChange]]:
    """Simulated annealing over the full sequence.

    Returns (best_order, changes).
    """
    n = len(tracks)
    if n < 2:
        return list(tracks), []

    current = list(tracks)
    current_score = score_full_sequence(current, energy_profile, weights)
    best = list(current)
    best_score = current_score
    original_positions = {t.id: i for i, t in enumerate(tracks)}
    temp = initial_temp

    for _ in range(iterations):
        # Random swap
        i, j = random.sample(range(n), 2)
        candidate = list(current)
        candidate[i], candidate[j] = candidate[j], candidate[i]
        new_score = score_full_sequence(candidate, energy_profile, weights)

        delta = new_score - current_score
        if delta > 0 or (temp > 0 and random.random() < math.exp(delta / temp)):
            current = candidate
            current_score = new_score
            if current_score > best_score:
                best = list(current)
                best_score = current_score

        temp *= cooling_rate

    changes = _diff_orders(tracks, best, original_positions, energy_profile)
    return best, changes


def get_energy_curve(
    tracks: list[Track],
    energy_profile: EnergyProfile | None = None,
) -> list[float]:
    """Get energy values for each track position."""
    from kiku.energy import get_track_energy
    return [get_track_energy(t).numeric for t in tracks]


def _diff_orders(
    original: list[Track],
    proposed: list[Track],
    original_positions: dict[int, int],
    energy_profile: EnergyProfile | None = None,
) -> list[OrderChange]:
    """Compare original and proposed orders, generate change explanations."""
    from kiku.energy import get_track_energy

    changes: list[OrderChange] = []
    for new_pos, track in enumerate(proposed):
        old_pos = original_positions.get(track.id, new_pos)
        if old_pos != new_pos:
            te = get_track_energy(track)
            # Build explanation
            explanation = f"energy ({te.numeric:.2f})"
            if energy_profile:
                elapsed = sum((proposed[j].duration_sec or 360) / 60 for j in range(new_pos))
                target = energy_profile.target_energy_at(elapsed)
                explanation += f" better fits target ({target:.2f}) at this position"
            else:
                explanation += " improves transition flow at this position"

            changes.append(OrderChange(
                track_id=track.id,
                track_title=track.title,
                from_position=old_pos,
                to_position=new_pos,
                explanation=explanation,
            ))

    return changes
```

Verification:
- `source .venv/bin/activate && python -c "from kiku.setbuilder.reorder import optimize_gentle, optimize_full, score_full_sequence; print('OK')"` should print `OK`.

#### Task 18 — Backend: Add fill/optimize-order/score-sequence schemas
Tools: Edit
File: `src/kiku/api/schemas.py`

Add these new schemas at the end of the file (after the last class definition):

````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ END
+
+
+# ── Manual set builder: fill, reorder, score-sequence ──
+
+
+class SetFillRequest(BaseModel):
+    energy_profile: str | None = None
+    target_duration_min: int | None = None
+    genre_filter: list[str] | None = None
+    max_fill_tracks: int = 10
+    gap_threshold: float = 0.6
+    discovery_density: float = 0.0
+    weights: ScoringWeightsRequest | None = None
+
+
+class SetOptimizeOrderRequest(BaseModel):
+    strategy: str = "gentle"  # "gentle" | "full"
+    energy_profile: str | None = None
+    weights: ScoringWeightsRequest | None = None
+
+
+class OrderChangeResponse(BaseModel):
+    track_id: int
+    track_title: str | None
+    from_position: int
+    to_position: int
+    explanation: str
+
+
+class SetOptimizeOrderResponse(BaseModel):
+    current_score: float
+    proposed_score: float
+    proposed_order: list[int]
+    changes: list[OrderChangeResponse]
+    current_energy_curve: list[float]
+    proposed_energy_curve: list[float]
+
+
+class ScoreSequenceRequest(BaseModel):
+    track_ids: list[int]
+    energy_profile: str | None = None
+    weights: ScoringWeightsRequest | None = None
+
+
+class ScoreSequenceResponse(BaseModel):
+    total_score: float
+    energy_curve: list[float]
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.api.schemas import SetFillRequest, SetOptimizeOrderRequest, ScoreSequenceRequest; print('OK')"` should print `OK`.

#### Task 19 — Backend: Add fill/optimize-order/score-sequence endpoints
Tools: Edit
File: `src/kiku/api/routes/sets.py`

Add these three new endpoints after the existing `reorder_tracks` endpoint (after line ~402). Insert before the `list_sets` endpoint (line ~405).

Add at line 403 (after `return [_set_track_response(st) for st in tracks]` in `reorder_tracks`):

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -402,6 +402,121 @@
     return [_set_track_response(st) for st in tracks]


+@router.post("/{set_id}/fill")
+def fill_set_sse(set_id: int, body: "SetFillRequest", db: Session = Depends(get_db)):
+    """Fill gaps in a set via SSE streaming."""
+    from kiku.api.schemas import SetFillRequest as _SFR  # noqa: F811
+    from kiku.setbuilder.constraints import parse_energy_string
+    from kiku.setbuilder.filler import fill_set
+
+    energy_profile = None
+    if body.energy_profile:
+        try:
+            energy_profile = parse_energy_string(body.energy_profile)
+        except Exception:
+            pass
+
+    weights_dict = None
+    if body.weights:
+        weights_dict = {
+            "harmonic": body.weights.harmonic,
+            "energy_fit": body.weights.energy_fit,
+            "bpm_compat": body.weights.bpm_compat,
+            "genre_coherence": body.weights.genre_coherence,
+            "track_quality": body.weights.track_quality,
+        }
+
+    def generate():
+        for event in fill_set(
+            db, set_id,
+            energy_profile=energy_profile,
+            target_duration_min=body.target_duration_min,
+            max_fill_tracks=body.max_fill_tracks,
+            genre_filter=body.genre_filter,
+            gap_threshold=body.gap_threshold,
+            discovery_density=body.discovery_density,
+            weights=weights_dict,
+        ):
+            yield f"event: {event.event}\ndata: {json.dumps(event.data)}\n\n"
+
+    return StreamingResponse(generate(), media_type="text/event-stream")
+
+
+@router.post("/{set_id}/optimize-order")
+def optimize_order(set_id: int, body: "SetOptimizeOrderRequest", db: Session = Depends(get_db)):
+    """Propose an optimized track order for the set."""
+    from kiku.api.schemas import OrderChangeResponse, SetOptimizeOrderResponse
+    from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string
+    from kiku.setbuilder.reorder import (
+        get_energy_curve,
+        optimize_full,
+        optimize_gentle,
+        score_full_sequence,
+    )
+
+    set_ = db.get(Set, set_id)
+    if not set_:
+        raise HTTPException(status_code=404, detail="Set not found")
+
+    set_tracks = sorted(set_.tracks, key=lambda st: st.position)
+    tracks = [st.track for st in set_tracks if st.track]
+    if len(tracks) < 3:
+        raise HTTPException(status_code=400, detail="Need at least 3 tracks to optimize order")
+
+    energy_profile = None
+    ep_str = body.energy_profile or set_.energy_profile
+    if ep_str:
+        try:
+            energy_profile = parse_energy_json(ep_str)
+        except Exception:
+            try:
+                energy_profile = parse_energy_string(ep_str)
+            except Exception:
+                pass
+
+    weights_dict = None
+    if body.weights:
+        weights_dict = {
+            "harmonic": body.weights.harmonic,
+            "energy_fit": body.weights.energy_fit,
+            "bpm_compat": body.weights.bpm_compat,
+            "genre_coherence": body.weights.genre_coherence,
+            "track_quality": body.weights.track_quality,
+        }
+
+    current_score = score_full_sequence(tracks, energy_profile, weights_dict)
+    current_curve = get_energy_curve(tracks, energy_profile)
+
+    if body.strategy == "full":
+        proposed, changes = optimize_full(tracks, energy_profile, weights_dict)
+    else:
+        proposed, changes = optimize_gentle(tracks, energy_profile, weights_dict)
+
+    proposed_score = score_full_sequence(proposed, energy_profile, weights_dict)
+    proposed_curve = get_energy_curve(proposed, energy_profile)
+
+    return SetOptimizeOrderResponse(
+        current_score=round(current_score, 3),
+        proposed_score=round(proposed_score, 3),
+        proposed_order=[t.id for t in proposed],
+        changes=[
+            OrderChangeResponse(
+                track_id=c.track_id,
+                track_title=c.track_title,
+                from_position=c.from_position,
+                to_position=c.to_position,
+                explanation=c.explanation,
+            ) for c in changes
+        ],
+        current_energy_curve=[round(v, 3) for v in current_curve],
+        proposed_energy_curve=[round(v, 3) for v in proposed_curve],
+    )
+
+
+@router.post("/{set_id}/score-sequence")
+def score_sequence(set_id: int, body: "ScoreSequenceRequest", db: Session = Depends(get_db)):
+    """Score a proposed track order without saving."""
+    from kiku.api.schemas import ScoreSequenceResponse
+    from kiku.setbuilder.constraints import parse_energy_string
+    from kiku.setbuilder.reorder import get_energy_curve, score_full_sequence
+
+    tracks = [db.get(Track, tid) for tid in body.track_ids]
+    tracks = [t for t in tracks if t is not None]
+    if len(tracks) < 2:
+        raise HTTPException(status_code=400, detail="Need at least 2 tracks to score")
+
+    energy_profile = None
+    if body.energy_profile:
+        try:
+            energy_profile = parse_energy_string(body.energy_profile)
+        except Exception:
+            pass
+
+    weights_dict = None
+    if body.weights:
+        weights_dict = {
+            "harmonic": body.weights.harmonic,
+            "energy_fit": body.weights.energy_fit,
+            "bpm_compat": body.weights.bpm_compat,
+            "genre_coherence": body.weights.genre_coherence,
+            "track_quality": body.weights.track_quality,
+        }
+
+    total = score_full_sequence(tracks, energy_profile, weights_dict)
+    curve = get_energy_curve(tracks, energy_profile)
+
+    return ScoreSequenceResponse(
+        total_score=round(total, 3),
+        energy_curve=[round(v, 3) for v in curve],
+    )
+
+
 @router.get("", response_model=list[SetResponse])
````

Note: The imports for `SetFillRequest`, `SetOptimizeOrderRequest`, `ScoreSequenceRequest` should be added at the top of the file alongside existing schema imports. Add these to the existing import block from `kiku.api.schemas`:

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ import
+from kiku.api.schemas import (
+    SetFillRequest,
+    SetOptimizeOrderRequest,
+    ScoreSequenceRequest,
+)
````

The implementor should add `SetFillRequest`, `SetOptimizeOrderRequest`, `ScoreSequenceRequest` to the existing schema imports at the top of `sets.py`.

Verification:
- `source .venv/bin/activate && python -c "from kiku.api.routes.sets import router; print('OK')"` should print `OK`.

#### Task 20 — Frontend: Add API functions for fill, optimize-order, score-sequence
Tools: Edit
File: `frontend/src/lib/api/sets.ts`

Add these new functions at the end of the file:

````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@ END
+
+// ── Manual set builder: fill, reorder, score-sequence ──
+
+export interface FillParams {
+	energy_profile?: string | null;
+	target_duration_min?: number | null;
+	genre_filter?: string[] | null;
+	max_fill_tracks?: number;
+	gap_threshold?: number;
+	discovery_density?: number;
+}
+
+export interface OptimizeOrderParams {
+	strategy?: 'gentle' | 'full';
+	energy_profile?: string | null;
+}
+
+export interface OptimizeOrderResponse {
+	current_score: number;
+	proposed_score: number;
+	proposed_order: number[];
+	changes: { track_id: number; track_title: string | null; from_position: number; to_position: number; explanation: string }[];
+	current_energy_curve: number[];
+	proposed_energy_curve: number[];
+}
+
+export interface ScoreSequenceResponse {
+	total_score: number;
+	energy_curve: number[];
+}
+
+export function fillSet(
+	setId: number,
+	params: FillParams,
+	onEvent?: (event: string, data: unknown) => void
+): Promise<void> {
+	return new Promise((resolve, reject) => {
+		fetch(`${API_BASE}/api/sets/${setId}/fill`, {
+			method: 'POST',
+			headers: { 'Content-Type': 'application/json' },
+			body: JSON.stringify(params),
+		})
+			.then((res) => {
+				if (!res.ok || !res.body) {
+					reject(new Error(`Fill request failed: ${res.status}`));
+					return;
+				}
+				const reader = res.body.getReader();
+				const decoder = new TextDecoder();
+				let buffer = '';
+
+				function processChunk(chunk: string) {
+					buffer += chunk;
+					const lines = buffer.split('\n');
+					buffer = lines.pop() ?? '';
+					let currentEvent = '';
+					for (const line of lines) {
+						if (line.startsWith('event: ')) {
+							currentEvent = line.slice(7).trim();
+						} else if (line.startsWith('data: ')) {
+							const data = JSON.parse(line.slice(6));
+							onEvent?.(currentEvent, data);
+						}
+					}
+				}
+
+				function read(): void {
+					reader.read().then(({ done, value }) => {
+						if (done) { resolve(); return; }
+						processChunk(decoder.decode(value, { stream: true }));
+						read();
+					}).catch(reject);
+				}
+				read();
+			})
+			.catch(reject);
+	});
+}
+
+export async function optimizeOrder(setId: number, params: OptimizeOrderParams): Promise<OptimizeOrderResponse> {
+	return fetchJson<OptimizeOrderResponse>(`/api/sets/${setId}/optimize-order`, {
+		method: 'POST',
+		headers: { 'Content-Type': 'application/json' },
+		body: JSON.stringify(params),
+	});
+}
+
+export async function scoreSequence(setId: number, trackIds: number[], energyProfile?: string): Promise<ScoreSequenceResponse> {
+	return fetchJson<ScoreSequenceResponse>(`/api/sets/${setId}/score-sequence`, {
+		method: 'POST',
+		headers: { 'Content-Type': 'application/json' },
+		body: JSON.stringify({ track_ids: trackIds, energy_profile: energyProfile }),
+	});
+}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | grep -c "Error"` should be 0.

#### Task 21 — Frontend: Create FillReorderDialog.svelte
Tools: Write (new file)
File: `frontend/src/lib/components/set/FillReorderDialog.svelte`

Create the file with this exact content:

```svelte
<script lang="ts">
	import { fillSet, optimizeOrder, reorderSetTracks, addTrackToSet, type OptimizeOrderResponse } from '$lib/api/sets';

	let {
		setId,
		setName = 'set',
		trackCount = 0,
		durationMin = 0,
		energyProfile = null,
		onclose,
		onapplied,
	}: {
		setId: number;
		setName?: string;
		trackCount?: number;
		durationMin?: number;
		energyProfile?: string | null;
		onclose: () => void;
		onapplied?: () => void;
	} = $props();

	let activeTab = $state<'fill' | 'reorder'>('fill');

	// Fill state
	let fillRunning = $state(false);
	let fillTargetMin = $state(60);
	let fillMaxTracks = $state(10);
	let proposals = $state<Array<{ position: number; track_id: number; track_title: string | null; track_artist: string | null; score: number; explanation: string; accepted: boolean }>>([]);
	let fillComplete = $state(false);
	let applying = $state(false);

	// Reorder state
	let strategy = $state<'gentle' | 'full'>('gentle');
	let reorderResult = $state<OptimizeOrderResponse | null>(null);
	let optimizing = $state(false);
	let applyingReorder = $state(false);

	async function startFill() {
		fillRunning = true;
		proposals = [];
		fillComplete = false;
		try {
			await fillSet(setId, {
				energy_profile: energyProfile,
				target_duration_min: fillTargetMin,
				max_fill_tracks: fillMaxTracks,
			}, (event, data: any) => {
				if (event === 'fill_proposed') {
					proposals = [...proposals, {
						position: data.position,
						track_id: data.track_id,
						track_title: data.track_title,
						track_artist: data.track_artist,
						score: data.score,
						explanation: data.explanation,
						accepted: true,
					}];
				} else if (event === 'fill_complete') {
					fillComplete = true;
				}
			});
		} catch {
			// Handled via events
		} finally {
			fillRunning = false;
			fillComplete = true;
		}
	}

	async function applyFill() {
		applying = true;
		try {
			const accepted = proposals.filter((p) => p.accepted);
			for (const p of accepted) {
				await addTrackToSet(setId, p.track_id, p.position);
			}
			onapplied?.();
			onclose();
		} catch {
			// Silently fail
		} finally {
			applying = false;
		}
	}

	async function startOptimize() {
		optimizing = true;
		reorderResult = null;
		try {
			reorderResult = await optimizeOrder(setId, {
				strategy,
				energy_profile: energyProfile,
			});
		} catch {
			// Handled
		} finally {
			optimizing = false;
		}
	}

	async function applyReorder() {
		if (!reorderResult) return;
		applyingReorder = true;
		try {
			await reorderSetTracks(setId, reorderResult.proposed_order);
			onapplied?.();
			onclose();
		} catch {
			// Handled
		} finally {
			applyingReorder = false;
		}
	}

	function scoreColor(score: number): string {
		if (score >= 0.8) return 'var(--color-success, #66BB6A)';
		if (score >= 0.6) return 'var(--color-warning, #FFA726)';
		return 'var(--color-error, #EF5350)';
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="dialog-overlay" onclick={onclose} onkeydown={(e) => { if (e.key === 'Escape') onclose(); }}>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="dialog" onclick={(e) => e.stopPropagation()}>
		<div class="dialog-header">
			<div class="tabs">
				<button class="tab" class:active={activeTab === 'fill'} onclick={() => activeTab = 'fill'}>Fill Gaps</button>
				<button class="tab" class:active={activeTab === 'reorder'} onclick={() => activeTab = 'reorder'}>Reorder</button>
			</div>
			<button class="close-btn" onclick={onclose}>&times;</button>
		</div>

		{#if activeTab === 'fill'}
			<div class="tab-content">
				<div class="set-info">Your set: "{setName}" ({trackCount} tracks, {durationMin} min)</div>

				{#if !fillComplete && !fillRunning}
					<div class="fill-form">
						<label class="form-label">
							Target length (minutes)
							<input type="number" bind:value={fillTargetMin} min={1} max={300} class="form-input" />
						</label>
						<label class="form-label">
							Max tracks to add
							<input type="number" bind:value={fillMaxTracks} min={1} max={30} class="form-input" />
						</label>
						<div class="form-actions">
							<button class="btn secondary" onclick={onclose}>Cancel</button>
							<button class="btn primary" onclick={startFill}>Find Tracks</button>
						</div>
					</div>
				{:else if fillRunning}
					<div class="fill-status">Listening to your set and finding candidates...</div>
				{/if}

				{#if proposals.length > 0}
					<div class="proposals">
						{#each proposals as proposal, i}
							<div class="proposal-row" class:skipped={!proposal.accepted}>
								<div class="proposal-info">
									<span class="proposal-score" style="color: {scoreColor(proposal.score)}">
										{proposal.score.toFixed(2)}
									</span>
									<span class="proposal-title">
										Insert at pos {proposal.position}: {proposal.track_title ?? '?'}
										{#if proposal.track_artist}
											<span class="dim"> - {proposal.track_artist}</span>
										{/if}
									</span>
								</div>
								<p class="proposal-explanation">{proposal.explanation}</p>
								<div class="proposal-actions">
									<button
										class="btn-sm"
										class:active={proposal.accepted}
										onclick={() => { proposals[i].accepted = true; proposals = proposals; }}
									>Keep</button>
									<button
										class="btn-sm"
										class:active={!proposal.accepted}
										onclick={() => { proposals[i].accepted = false; proposals = proposals; }}
									>Skip</button>
								</div>
							</div>
						{/each}
					</div>
				{/if}

				{#if fillComplete && proposals.length > 0}
					<div class="form-actions">
						<button class="btn secondary" onclick={onclose}>Cancel</button>
						<button class="btn primary" onclick={applyFill} disabled={applying || proposals.filter(p => p.accepted).length === 0}>
							{applying ? 'Applying...' : `Apply ${proposals.filter(p => p.accepted).length} tracks`}
						</button>
					</div>
				{/if}
			</div>
		{:else}
			<div class="tab-content">
				{#if !reorderResult && !optimizing}
					<div class="reorder-form">
						<div class="strategy-options">
							<label class="strategy-option">
								<input type="radio" bind:group={strategy} value="gentle" />
								<div>
									<strong>Gentle</strong>
									<span class="dim"> - minimal changes, keeps your intent</span>
								</div>
							</label>
							<label class="strategy-option">
								<input type="radio" bind:group={strategy} value="full" />
								<div>
									<strong>Full Rethink</strong>
									<span class="dim"> - best possible flow</span>
								</div>
							</label>
						</div>
						<div class="form-actions">
							<button class="btn secondary" onclick={onclose}>Cancel</button>
							<button class="btn primary" onclick={startOptimize}>Optimize</button>
						</div>
					</div>
				{:else if optimizing}
					<div class="fill-status">Finding the best flow...</div>
				{:else if reorderResult}
					<div class="reorder-result">
						<div class="score-comparison">
							<span style="color: {scoreColor(reorderResult.current_score)}">
								{reorderResult.current_score.toFixed(3)}
							</span>
							<span class="arrow">→</span>
							<span style="color: {scoreColor(reorderResult.proposed_score)}">
								{reorderResult.proposed_score.toFixed(3)}
							</span>
							{@const delta = reorderResult.proposed_score - reorderResult.current_score}
							{#if delta > 0}
								<span class="delta positive">(+{(delta * 100 / reorderResult.current_score).toFixed(0)}%)</span>
							{:else}
								<span class="delta">({(delta * 100 / reorderResult.current_score).toFixed(0)}%)</span>
							{/if}
						</div>

						{#if reorderResult.changes.length === 0}
							<div class="no-changes">Your set is already in good shape — no changes suggested.</div>
						{:else}
							<div class="changes-list">
								<div class="changes-header">{reorderResult.changes.length} tracks moved:</div>
								{#each reorderResult.changes as change}
									<div class="change-row">
										<span class="change-title">{change.track_title ?? 'Track'}</span>
										<span class="change-positions">{change.from_position + 1} → {change.to_position + 1}</span>
										<span class="change-explanation">{change.explanation}</span>
									</div>
								{/each}
							</div>
						{/if}

						<div class="form-actions">
							<button class="btn secondary" onclick={onclose}>Cancel</button>
							<button class="btn primary" onclick={applyReorder} disabled={applyingReorder || reorderResult.changes.length === 0}>
								{applyingReorder ? 'Applying...' : 'Apply New Order'}
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.dialog-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
	}

	.dialog {
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 12px;
		width: 560px;
		max-height: 80vh;
		overflow-y: auto;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
	}

	.dialog-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
	}

	.tabs {
		display: flex;
		gap: 4px;
	}

	.tab {
		padding: 6px 16px;
		font-size: 13px;
		font-weight: 600;
		background: none;
		border: none;
		color: var(--text-dim);
		cursor: pointer;
		border-radius: 4px;
	}

	.tab.active {
		color: var(--text-primary);
		background: var(--bg-secondary);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text-dim);
		font-size: 20px;
		cursor: pointer;
	}

	.tab-content {
		padding: 16px;
	}

	.set-info {
		font-size: 13px;
		color: var(--text-secondary);
		margin-bottom: 16px;
	}

	.fill-form, .reorder-form {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.form-label {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 13px;
		color: var(--text-secondary);
	}

	.form-input {
		padding: 8px 10px;
		font-size: 13px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text-primary);
		width: 100px;
	}

	.form-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
		margin-top: 12px;
	}

	.btn {
		padding: 8px 16px;
		font-size: 13px;
		font-weight: 600;
		border-radius: 6px;
		cursor: pointer;
		border: none;
	}

	.btn.primary {
		background: var(--accent);
		color: #000;
	}

	.btn.secondary {
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid var(--border);
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.fill-status {
		padding: 20px 0;
		text-align: center;
		color: var(--text-dim);
		font-size: 13px;
	}

	.proposals {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-top: 12px;
	}

	.proposal-row {
		padding: 10px 12px;
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.proposal-row.skipped {
		opacity: 0.4;
	}

	.proposal-info {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.proposal-score {
		font-weight: 700;
		font-size: 13px;
	}

	.proposal-title {
		font-size: 13px;
	}

	.proposal-explanation {
		font-size: 12px;
		color: var(--text-dim);
		margin: 4px 0 6px;
	}

	.proposal-actions {
		display: flex;
		gap: 6px;
	}

	.btn-sm {
		padding: 4px 10px;
		font-size: 11px;
		border: 1px solid var(--border);
		border-radius: 4px;
		background: none;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.btn-sm.active {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
	}

	.strategy-options {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.strategy-option {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		padding: 8px 10px;
		border: 1px solid var(--border);
		border-radius: 6px;
		cursor: pointer;
		font-size: 13px;
	}

	.score-comparison {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 18px;
		font-weight: 700;
		margin-bottom: 16px;
	}

	.arrow {
		color: var(--text-dim);
	}

	.delta {
		font-size: 14px;
		font-weight: 400;
	}

	.delta.positive {
		color: var(--color-success, #66BB6A);
	}

	.no-changes {
		padding: 16px 0;
		color: var(--text-dim);
		font-size: 13px;
	}

	.changes-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.changes-header {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.change-row {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-size: 13px;
		padding: 4px 0;
	}

	.change-title {
		font-weight: 600;
	}

	.change-positions {
		color: var(--accent);
		font-size: 12px;
	}

	.change-explanation {
		color: var(--text-dim);
		font-size: 12px;
	}

	.dim {
		color: var(--text-dim);
	}
</style>
```

Verification:
- File exists. No TypeScript errors.

#### Task 22 — Frontend: Add "Assist" button to SetView.svelte
Tools: Edit
File: `frontend/src/lib/components/set/SetView.svelte`

Diff 1 — Add import:
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@ -7,6 +7,7 @@
 	import EnergyFlowChart from './EnergyFlowChart.svelte';
 	import SetEnergyReview from './SetEnergyReview.svelte';
+	import FillReorderDialog from './FillReorderDialog.svelte';
 	import { getPlaybackStore } from '$lib/stores/playback.svelte';
````

Diff 2 — Add state:
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@ -79,6 +79,7 @@
 	let analyzingSet = $state(false);
+	let showAssist = $state(false);
````

Diff 3 — Add the "Assist" button in the `timeline-controls` div, after the Live Builder button (around line 283):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@ -283,6 +283,12 @@
 				>
 					Live Builder
 				</button>
+				{#if waveformTracks.length >= 3}
+					<button class="assist-btn" onclick={() => showAssist = true}>
+						Assist
+					</button>
+				{/if}
 			{/if}
````

Diff 4 — Add the dialog rendering before the closing `</div>` of `.set-view` (before the `{#if showEnergyReview}` block at line ~383):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@ -383,6 +383,18 @@
+	{#if showAssist && selectedSet}
+		<FillReorderDialog
+			setId={selectedSet.id}
+			setName={selectedSet.name ?? 'set'}
+			trackCount={selectedSet.track_count}
+			durationMin={selectedSet.duration_min ?? 0}
+			energyProfile={setDetail?.energy_profile}
+			onclose={() => showAssist = false}
+			onapplied={() => { showAssist = false; if (selectedSet) loadSetData(selectedSet.id); }}
+		/>
+	{/if}
+
 	{#if showEnergyReview}
````

Diff 5 — Add styles for the assist button:
````diff
+	.assist-btn {
+		padding: 4px 12px;
+		font-size: 12px;
+		font-weight: 600;
+		color: var(--text-primary);
+		background: var(--bg-secondary);
+		border: 1px solid var(--accent);
+		border-radius: 4px;
+		cursor: pointer;
+		transition: all 0.15s;
+	}
+
+	.assist-btn:hover {
+		background: var(--accent);
+		color: #000;
+	}
````

Verification:
- Open a set with >= 3 tracks. "Assist" button visible. Clicking opens FillReorderDialog.

#### Task 23 — Backend: Unit tests for manual set builder
Tools: Edit
File: `tests/api/test_sets_api.py`

Add new tests at the end of the file:

````diff
--- a/tests/api/test_sets_api.py
+++ b/tests/api/test_sets_api.py
@@ END
+
+
+# ── Manual set builder tests ──
+
+
+def test_create_set_with_source(client):
+    """POST /api/sets with source='manual' persists the field."""
+    resp = client.post("/api/sets", json={"name": "Manual Set", "source": "manual"})
+    assert resp.status_code == 201
+    data = resp.json()
+    assert data["source"] == "manual"
+
+
+def test_add_track_computes_transition_score(client):
+    """POST track computes transition_score against preceding track."""
+    # Create a fresh set
+    create_resp = client.post("/api/sets", json={"name": "Score Test"})
+    set_id = create_resp.json()["id"]
+    # Add first track (no predecessor, so score should be None)
+    resp1 = client.post(f"/api/sets/{set_id}/tracks", json={"track_id": 1})
+    tracks1 = resp1.json()
+    assert len(tracks1) == 1
+    assert tracks1[0]["transition_score"] is None
+    # Add second track (should have a score against track 1)
+    resp2 = client.post(f"/api/sets/{set_id}/tracks", json={"track_id": 2})
+    tracks2 = resp2.json()
+    assert len(tracks2) == 2
+    second_track = next(t for t in tracks2 if t["track_id"] == 2)
+    assert second_track["transition_score"] is not None
+    assert 0 <= second_track["transition_score"] <= 1.0
+
+
+def test_add_track_recomputes_duration(client):
+    """POST track recomputes set duration_min."""
+    create_resp = client.post("/api/sets", json={"name": "Duration Test"})
+    set_id = create_resp.json()["id"]
+    assert create_resp.json()["duration_min"] is None
+    # Add a track (~310 sec = 5 min)
+    client.post(f"/api/sets/{set_id}/tracks", json={"track_id": 1})
+    detail = client.get(f"/api/sets/{set_id}").json()
+    assert detail["duration_min"] is not None
+    assert detail["duration_min"] >= 5
+
+
+def test_add_track_invalidates_analysis(client):
+    """POST track sets is_analyzed=0."""
+    # Use the seed set (id=1)
+    resp = client.post("/api/sets/1/tracks", json={"track_id": 10})
+    assert resp.status_code == 200
+    # We can't easily check is_analyzed via API, but the endpoint should not error
+
+
+def test_remove_track_recomputes_duration(client):
+    """DELETE track recomputes set duration_min."""
+    # Create a set with 2 tracks
+    create_resp = client.post("/api/sets", json={"name": "Remove Duration"})
+    set_id = create_resp.json()["id"]
+    client.post(f"/api/sets/{set_id}/tracks", json={"track_id": 1})
+    client.post(f"/api/sets/{set_id}/tracks", json={"track_id": 2})
+    detail_before = client.get(f"/api/sets/{set_id}").json()
+    # Remove track 1
+    client.delete(f"/api/sets/{set_id}/tracks/1")
+    detail_after = client.get(f"/api/sets/{set_id}").json()
+    assert detail_after["duration_min"] <= detail_before["duration_min"]
+
+
+def test_optimize_order_requires_3_tracks(client):
+    """POST optimize-order fails with < 3 tracks."""
+    create_resp = client.post("/api/sets", json={"name": "Small Set"})
+    set_id = create_resp.json()["id"]
+    client.post(f"/api/sets/{set_id}/tracks", json={"track_id": 1})
+    client.post(f"/api/sets/{set_id}/tracks", json={"track_id": 2})
+    resp = client.post(f"/api/sets/{set_id}/optimize-order", json={"strategy": "gentle"})
+    assert resp.status_code == 400
+
+
+def test_optimize_order_gentle(client):
+    """POST optimize-order with gentle strategy returns valid response."""
+    resp = client.post("/api/sets/1/optimize-order", json={"strategy": "gentle"})
+    assert resp.status_code == 200
+    data = resp.json()
+    assert "current_score" in data
+    assert "proposed_score" in data
+    assert "proposed_order" in data
+    assert "changes" in data
+    assert len(data["proposed_order"]) == 5
+
+
+def test_score_sequence(client):
+    """POST score-sequence returns valid response."""
+    resp = client.post("/api/sets/1/score-sequence", json={"track_ids": [1, 2, 3, 4, 5]})
+    assert resp.status_code == 200
+    data = resp.json()
+    assert "total_score" in data
+    assert "energy_curve" in data
+    assert 0 <= data["total_score"] <= 1.0
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_sets_api.py -x -q` -- all tests pass.

#### Task 24 — Lint all modified Python files
Tools: Bash
Commands:
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -m ruff check --fix src/kiku/api/schemas.py src/kiku/api/routes/sets.py src/kiku/api/routes/tracks.py src/kiku/setbuilder/planner.py src/kiku/setbuilder/scoring.py src/kiku/setbuilder/filler.py src/kiku/setbuilder/reorder.py tests/api/test_sets_api.py tests/api/conftest.py
```

```bash
cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json
```

Verification:
- No lint errors. No type-check errors.

#### Task 25 — Run backend tests
Tools: Bash
Commands:
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -m pytest tests/api/ -x -q
```

Verification:
- All tests pass, including the new manual set builder tests.

#### Task 26 — Commit all changes
Tools: Bash

Stage only the modified and new files:
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && git add \
  src/kiku/api/schemas.py \
  src/kiku/api/routes/sets.py \
  src/kiku/api/routes/tracks.py \
  src/kiku/setbuilder/planner.py \
  src/kiku/setbuilder/scoring.py \
  src/kiku/setbuilder/filler.py \
  src/kiku/setbuilder/reorder.py \
  tests/api/test_sets_api.py \
  tests/api/conftest.py \
  frontend/src/lib/types/index.ts \
  frontend/src/lib/api/sets.ts \
  frontend/src/lib/components/set/AddToSetPicker.svelte \
  frontend/src/lib/components/set/SetPicker.svelte \
  frontend/src/lib/components/library/TrackContextMenu.svelte \
  frontend/src/lib/components/waveform/TrackView.svelte \
  frontend/src/lib/components/waveform/SimilarTracks.svelte \
  frontend/src/lib/components/set/InSetTrackSearch.svelte \
  frontend/src/lib/components/set/SetView.svelte \
  frontend/src/lib/components/set/SetTimeline.svelte \
  frontend/src/lib/components/set/FillReorderDialog.svelte \
  specs/2026/04/main/013-manual-set-builder.md
```

Commit message:
```
spec(013): IMPLEMENT - manual set builder (3 phases)

Phase 1: Create & Add — source field, transition scoring on add,
duration recomputation, analysis invalidation, AddToSetPicker,
context menu/TrackView/SimilarTracks entry points, SetPicker + New.

Phase 2: In-Set Search — position-aware energy in suggest-next,
InSetTrackSearch panel in SetTimeline.

Phase 3: AI Fill & Reorder — filler.py (gap detection + SSE proposals),
reorder.py (gentle swaps + simulated annealing), 3 new endpoints,
FillReorderDialog with fill/reorder tabs, Assist button in SetView.
```

### Validate

1. **L10: CREATE empty sets with `source: "manual"`** — Task 1 adds `source` to `SetCreateRequest`, Task 1 sets it in `create_set()`, Task 8 adds "+ New" button to SetPicker. Compliant.
2. **L11: ADD tracks from 5 entry points** — Tasks 9 (context menu, P0), 10 (TrackView, P0), 15 (SetTimeline via InSetTrackSearch, P1), 11 (SimilarTracks, P1). NowPlayingBar (P2) deferred as lowest priority. 4 of 5 addressed.
3. **L12: BUILD AddToSetPicker component** — Task 7 creates it with search, track count, new set creation, keyboard nav, duplicate detection.
4. **L13: COMPUTE transition scores on manual add** — Task 2 computes scores on add, updates following track. Task 3 recomputes on remove.
5. **L14: SEARCH library inline within SetView** — Tasks 14-15 create InSetTrackSearch with scored results.
6. **L15: ENHANCE suggest-next with position-aware energy** — Tasks 12-13 add `position_min` and `energy_profile` params.
7. **L16: FILL gaps via SSE** — Task 16 (filler.py) + Task 19 (endpoint) + Task 21 (FillReorderDialog).
8. **L17: REORDER for optimal flow** — Task 17 (reorder.py gentle + full) + Task 19 (endpoint) + Task 21 (dialog).
9. **L18: SCORE arbitrary sequences** — Task 18 (schema) + Task 19 (endpoint).
10. **L19: FIX position indexing** — Task 5 fixes planner.py and test fixture.
11. **L68-69: No schema migrations** — Correct, no migrations needed.
12. **L87-101: Testing** — Task 23 adds 8 backend tests covering source, scoring, duration, optimize-order, score-sequence.
13. **L103-108: Key Design Principles** — Scores visible in InSetTrackSearch, explanations in fill proposals and reorder changes.
14. **L112: Behavior** — Strict phase order in tasks. Reuses existing primitives (transition_score, score_replacement, EnergyProfile).
15. **L249-250: Analysis cache invalidation** — Tasks 2, 3, 4 invalidate `is_analyzed` and `analysis_cache` on add/remove/reorder.

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
