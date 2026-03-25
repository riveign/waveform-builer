# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Add a Discovery/Density slider to the set builder that lets the DJ choose between surfacing fresh, unplayed tracks (discovery) or battle-tested favorites (density). Also record in-app play counts when a track is listened to for >60 seconds in the Kiku player, stored separately from Rekordbox sync data so both signals remain accurate.

## Mid-Level Objectives (MLO)

### Backend Scoring + API
- ADD `kiku_play_count` column to Track model + Alembic migration (Integer, default 0)
- ADD cross-set density query helper (`track_id → set appearance count` via `set_tracks` JOIN)
- MODIFY `track_quality()` to accept `discovery_density` float parameter (-1.0 to +1.0)
  - Reshape play_count sub-component: discovery inverts signal, density amplifies it
  - ADD set density sub-component (10% of track_quality, taken from play_count's 30% → 20%)
- ADD `discovery_density` parameter to `SetBuildRequest` and suggest-next query params
- ADD `POST /api/tracks/{track_id}/played` endpoint (increment `kiku_play_count`)
- ADD `discovery_label` and `set_appearances` to `TransitionScoreBreakdown`
- UPDATE `score_replacement()` to also accept `discovery_density`

### Frontend Play Recording
- ADD `listenedSeconds` accumulator to global player store (`player.svelte.ts`)
  - Track real elapsed time via `timeupdate` delta guard (`Math.abs(time - lastTimeUpdate) < 2`)
  - Fire `POST /api/tracks/{id}/played` when threshold crossed
  - Session-scoped `Set<number>` dedup (one increment per track per page load)
- ADD same accumulator to set playback store (`playback.svelte.ts`)
  - Per-deck tracking for A/B deck architecture
  - Express mode (~45s snippets) intentionally below threshold

### Frontend Discovery/Density UI
- CREATE `DiscoveryDensitySlider.svelte` component
  - Range -100 to +100 (integer), divided by 100 for API
  - Context-sensitive labels: "Fresh picks" / "Lean fresh" / "Balanced" / "Lean proven" / "Battle-tested"
  - Context-sensitive subtext explaining current bias
- ADD slider to `BuildSetDialog.svelte` between Energy arc and Genre filter sections
- PASS `discovery_density` to build-set and suggest-next API calls
- ADD discovery/density labels to score breakdown in TransitionInspector and suggest-next results

## Details (DT)

### Scoring Formula

**Sub-component weight redistribution** (within track_quality, 20% of total score):

| Sub-component | Before | After |
|---------------|--------|-------|
| Rating | 40% | 40% (unchanged) |
| Play familiarity | 30% | 20% |
| Set density | 0% | 10% (new) |
| Playlist membership | 30% | 30% (unchanged) |

**Play familiarity signal** (20% of track_quality):
- Combined plays = `min(play_count + kiku_play_count, 10) / 10`
- `discovery_density < 0`: Blend toward inverted (alpha = abs(dd)), `(1-α) × ratio + α × (1-ratio)`
- `discovery_density > 0`: Blend toward amplified (alpha = dd), `(1-α) × ratio + α × ratio^0.5`

**Set density signal** (10% of track_quality):
- `density = min(set_appearance_count, 6) / 6`
- Same blending logic as play familiarity

### Discovery Labels

| Condition | Label |
|-----------|-------|
| `dd < -0.3` AND 0-1 total plays | "fresh pick" |
| `dd < -0.3` AND 2-4 total plays | "rarely played" |
| `dd > 0.3` AND 2+ set appearances | "battle-tested" |
| `dd > 0.3` AND 7+ total plays | "crowd favorite" |
| Otherwise | null |

### Edge Cases
- **Seeking**: Delta guard prevents seeks from inflating counter (jump > 2s = skip)
- **Paused**: `timeupdate` stops firing when paused — no accumulation
- **Express mode**: 45s < 60s threshold — intentionally doesn't count
- **Page reload**: Counter resets — acceptable loss, no server-side session needed
- **Session dedup**: `Set<number>` in frontend prevents double-count per page load
- **Sync integrity**: `kiku_play_count` never touched by `kiku sync` — Rekordbox owns `play_count`

### Implementation Phases
Phase 1: Backend Scoring + API → Phase 2: Frontend Play Recording → Phase 3: Frontend Discovery/Density UI

### Source Material
Full design spec with formulas, mockups, and examples: `tmp/mux/20260322-1303-discovery-density-playcount/deliverable/discovery-density-spec.md`

## Behavior

You are a senior engineer implementing a scoring system extension. The discovery/density slider modifies the EXISTING track_quality dimension — it does NOT add a 6th scoring dimension. Keep the weight system at 5 dimensions. Pre-compute set_appearance_counts in a single batch query before beam search. The `kiku_play_count` column is Kiku-internal and must never be overwritten by Rekordbox sync.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Scoring System (`src/kiku/setbuilder/scoring.py`)

**`track_quality()` — line 227**
```python
def track_quality(track: Track, prefer_playlists: list[str] | None = None) -> float:
```
- Returns float 0-1
- Sub-components: rating (40%), play_count (30%), playlist_membership (30%)
- Play count: `plays = min(track.play_count or 0, 10)` — uses only `play_count`, no `kiku_play_count` yet
- No `discovery_density` parameter; no set-density signal

**`transition_score()` — line 253**
```python
def transition_score(
    from_track: Track,
    to_track: Track,
    target_energy: float = 0.5,
    prefer_playlists: list[str] | None = None,
    weights: dict[str, float] | None = None,
) -> float:
```
- Calls `track_quality(to_track, prefer_playlists)` on line 274 — does NOT pass `discovery_density` or `set_appearance_counts`
- Weight dict keys: `harmonic`, `energy_fit`, `bpm_compat`, `genre_coherence`, `track_quality`

**`score_replacement()` — line 280**
```python
def score_replacement(
    candidate: Track,
    prev_track: Track | None,
    next_track: Track | None,
    target_energy: float = 0.5,
    weights: dict[str, float] | None = None,
) -> tuple[float, dict | None, dict | None]:
```
- Inner `_breakdown()` (line 294) calls `track_quality(to_t)` — no playlists, no discovery_density
- Returns (combined_score, incoming_breakdown_dict, outgoing_breakdown_dict)
- Breakdown dict keys: `harmonic`, `energy_fit`, `bpm_compat`, `genre_coherence`, `track_quality`, `total`

**`score_transitions()` — line 329**
```python
def score_transitions(
    session: Session,
    from_track: Track,
    n: int = 10,
    genre_filter: list[str] | None = None,
    weights: dict[str, float] | None = None,
    exclude_ids: list[int] | None = None,
) -> list[tuple[Track, float]]:
```
- Calls `transition_score(from_track, track, weights=weights)` on line 362 — no `prefer_playlists`, no `discovery_density`

**Weight constants** — in `src/kiku/config.py` lines 71-84:
- Default: `harmonic: 0.25, energy_fit: 0.20, bpm_compat: 0.20, genre_coherence: 0.15, track_quality: 0.20`
- `SCORING_WEIGHT_KEYS` tuple on line 86
- `validate_scoring_weights()` line 96 — validates keys match `SCORING_WEIGHT_KEYS` and sum to ~1.0

### API Endpoints

**Build set SSE** — `src/kiku/api/routes/sets.py` line 81-162
- Router: `APIRouter(prefix="/api/sets", tags=["sets"])` (line 49)
- Handler: `build_set_sse(body: SetBuildRequest, db)` (line 82)
- `SetBuildRequest` — `src/kiku/api/schemas.py` lines 217-228:
  - Fields: `name, duration_min, energy_preset, genre_filter, bpm_min, bpm_max, seed_track_id, beam_width, playlist_preference, weights`
  - No `discovery_density` field yet
- Passes `weights_dict` to `planner.build_set()` — no `discovery_density` forwarding

**Suggest-next** — `src/kiku/api/routes/tracks.py` lines 122-203
- Handler: `suggest_next(track_id, n, set_id, genre_filter, w_harmonic, w_energy_fit, w_bpm_compat, w_genre_coherence, w_track_quality, db)`
- Calls `score_transitions()` then recomputes breakdown per candidate
- Breakdown recomputation (lines 180-199) calls `track_quality(cand)` directly — no discovery_density
- No `discovery_density` query param yet

**Replacements** — `src/kiku/api/routes/sets.py` lines 510-605
- Handler: `get_replacements(set_id, position, n, genre_filter, db)` (line 511)
- Calls `score_replacement(cand, prev_track, next_track, target_energy=energy_target)` on line 580
- No `discovery_density` param or forwarding

**Track endpoints** — `src/kiku/api/routes/tracks.py`
- Router: `APIRouter(prefix="/api/tracks", tags=["tracks"])` (line 20)
- Endpoints: `/search`, `/autocomplete/artists`, `/autocomplete/labels`, `/{track_id}`, `/{track_id}/suggest-next`, `/{track_id}/features`
- No `POST /{track_id}/played` endpoint yet

**Router registration** — `src/kiku/api/main.py` lines 34-42:
- All routers registered via `app.include_router(module.router)` in `create_app()`

### Database Models (`src/kiku/db/models.py`)

**Track model** — lines 32-77:
| Column | Type | Line |
|--------|------|------|
| id | Integer PK | 35 |
| rb_id | String unique | 36 |
| title | String | 37 |
| artist | String | 38 |
| album | String | 39 |
| label | String | 40 |
| rb_genre | String | 41 |
| dir_genre | String | 42 |
| dir_energy | String | 43 |
| bpm | Float | 44 |
| key | String | 45 |
| rating | Integer | 46 |
| color | String | 47 |
| comment | Text | 48 |
| duration_sec | Float | 49 |
| file_path | String | 50 |
| file_hash | String | 51 |
| date_added | String | 52 |
| play_count | Integer default=0 | 53 |
| release_year | Integer | 54 |
| acquired_month | String | 55 |
| playlist_tags | Text | 56 |
| last_synced | String | 57 |
| energy_predicted | String | 58 |
| energy_confidence | Float | 59 |
| energy_source | String | 60 |

- No `kiku_play_count` column yet
- Properties: `resolved_energy_zone` (line 66), `energy_conflict` (line 72)

**SetTrack model** — lines 134-143:
- Columns: `set_id` (FK sets.id, PK), `position` (PK), `track_id` (FK tracks.id), `transition_score` (Float)
- Relationships: `set_` → Set, `track` → Track

**Set model** — lines 121-131:
- Columns: `id`, `name`, `created_at`, `duration_min`, `energy_profile` (Text JSON), `genre_filter` (Text JSON)
- Relationship: `tracks` → SetTrack list

### Sync (`src/kiku/db/sync.py`)

- Line 198: `play_count=_safe_int(rb_track.DJPlayCount)` — sync overwrites `play_count` from Rekordbox
- Lines 204-209: update loop sets ALL `track_data` keys on existing tracks
- Confirms: `kiku_play_count` must be a separate column that sync never touches (sync only writes `play_count`)

### Set Builder / Planner (`src/kiku/setbuilder/planner.py`)

**`build_set()` — line 77**
```python
def build_set(
    session: Session,
    duration_min: int = 120,
    energy_profile: EnergyProfile | None = None,
    genres: list[str] | None = None,
    bpm_range: tuple[float, float] | None = None,
    seed_title: str | None = None,
    beam_width: int = DEFAULT_BEAM_WIDTH,
    set_name: str | None = None,
    prefer_playlists: list[str] | None = None,
    weights: dict[str, float] | None = None,
) -> Set | None:
```
- No `discovery_density` parameter yet
- Beam search loop (line 125): calls `transition_score(current, cand, target_energy=target_e, prefer_playlists=prefer_playlists, weights=weights)` on line 160
- Post-save re-score on line 222: `transition_score(prev_track, track, prefer_playlists=prefer_playlists, weights=weights)`
- `_get_candidate_pool()` (line 21): returns all Track objects matching genre/BPM — `set_appearance_counts` could be batch-queried at this point

### Frontend Player Store (`frontend/src/lib/stores/player.svelte.ts`)

- State variables: lines 31-43 — `currentTrack`, `status`, `currentTime`, `duration`, `volume`, `isMuted`, `mode`, `queue`, `queueIndex`, `setId`, `ws`
- `registerPlayer()` — line 79: binds WaveSurfer event listeners
- **`onTimeUpdate` handler** — line 82-84:
  ```typescript
  const onTimeUpdate = (time: number) => {
      currentTime = time;
  };
  ```
  - Simply sets `currentTime` — NO listen tracking, no delta guard, no threshold check
  - This is where `listenedSeconds` accumulator and delta guard need to be added
- `loadAndPlay()` — line 59: sets `currentTrack`, resets `currentTime = 0` — track change point
- `play()` — line 148: single track mode, calls `loadAndPlay(track)`
- `playSet()` — line 226: set mode, loads queue
- `getPlayerStore()` — line 282: exposes read-only state + actions
- **No session-scoped dedup Set<number>** yet

### Frontend Playback Store (`frontend/src/lib/stores/playback.svelte.ts`)

- A/B deck architecture, state variables lines 15-26
- `EXPRESS_SNIPPET_SEC = 45` (line 9) — below 60s threshold, intentionally won't trigger
- **`onDeckTimeUpdate()` — line 323-337**:
  ```typescript
  function onDeckTimeUpdate(deck: DeckId, time: number) {
      if (deck !== activeDeck) return;
      currentTime = time;
      if (mode !== 'express') return;
      if (status !== 'playing') return;
      const track = tracks[currentIndex];
      if (!track) return;
      const snippetEnd = snippetStart(track) + EXPRESS_SNIPPET_SEC;
      if (time >= snippetEnd) { advanceToNext(); }
  }
  ```
  - Only tracks time for express-mode auto-advance; no listen accumulation
  - Track change occurs in `advanceToNext()` (line 194) and `advanceToPrev()` (line 227)
  - `currentIndex` identifies the current track; `tracks[currentIndex].track_id` gives the ID
- `startPlayback()` — line 272: resets state for new set playback
- `stopPlayback()` — line 250: cleanup

### Frontend BuildSetDialog (`frontend/src/lib/components/set/BuildSetDialog.svelte`)

- Form state (lines 48-56): `name`, `durationMin`, `energyPreset`, `selectedGenres`, `bpmMin`, `bpmMax`, `useSeedTrack`, `beamWidth`, `scoringWeights`
- No `discoveryDensity` state variable yet
- `handleSubmit()` — line 119-163: builds `SetBuildParams` object, calls `onbuild?.(params)`
- Field layout order in template (line 204-381):
  1. Set Name (line 206)
  2. Duration + Exploration Depth row (line 221)
  3. Energy Preset — `EnergyPresetPicker` (line 258)
  4. Genre Filter chips (line 263)
  5. BPM Range (line 315)
  6. Scoring Weights — `ScoringWeightsSliders` (line 346)
  7. Starting Track / Seed (line 349)
- Spec says: "ADD slider between Energy arc and Genre filter sections" — that's between lines 261 and 263

### Score Breakdown Display (`frontend/src/lib/components/set/ScoreBreakdown.svelte`)

- Lines 1-41: accepts `breakdown: TransitionScoreBreakdown` prop
- `dimensions` array (lines 34-40): 5 dimension objects with `key`, `label`, `weight`, `color`
- `TEACHING` record (lines 15-21): per-dimension teaching strings for high/mid/low ranges
- Renders each dimension as a labeled bar with teaching note
- No `discovery_label` or `set_appearances` display yet
- Also used by: `TransitionDetail.svelte`, `TransitionIndicator.svelte`, `ReplaceTrackModal.svelte`

### Frontend Types (`frontend/src/lib/types/index.ts`)

- `TransitionScoreBreakdown` — line 118-125: `harmonic, energy_fit, bpm_compat, genre_coherence, track_quality, total`
- `SetBuildParams` — line 262-273: no `discovery_density` field
- `SuggestNextItem` — line 296-300: `track, score, breakdown`
- `ReplacementBreakdown` — line 416-423: same 5+total fields
- `Track` — line 7-25: has `play_count` but no `kiku_play_count`

### Test Patterns

**Test directory structure**: `tests/` with:
- `test_scoring.py` — unit tests for `bpm_compatibility`, `genre_coherence` (12 tests, no track_quality tests)
- `tests/api/conftest.py` — shared fixtures: `db_session` (in-memory SQLite), `client` (FastAPI TestClient)
  - Seeds 20 tracks (id 1-20), 1 set with 5 tracks, tinder predictions, hunt session
  - Track seed: `play_count=i` (1-20), `rating=3`, `bpm=120+i`
- `tests/api/test_tracks_api.py` — tests for search, detail, suggest-next endpoints
- `tests/api/test_sets_api.py` — tests for set CRUD
- `tests/api/test_config_api.py`, `test_tinder_api.py`, `test_hunt_api.py`
- Pattern: `def test_<action>(client):` using the `client` fixture, assert status codes + JSON structure

### Alembic Migrations

- Config: `alembic/env.py` — uses `kiku.config.get_db_url()` and `kiku.db.models.Base.metadata`
- Versions dir: `alembic/versions/`
- Latest migration: `16f80a5c17e9_add_label_column_to_tracks.py` (down_revision: `455598dafd10`)
- Pattern: auto-generated revision ID, descriptive slug filename, `upgrade()/downgrade()` with `op.add_column()/op.drop_column()`
- New migration: `alembic revision --autogenerate -m "add kiku_play_count column to tracks"` after adding column to model

### Strategy

**Phase 1: Backend Scoring + API**
1. Add `kiku_play_count = Column(Integer, default=0)` to Track model (after `play_count`, line 53)
2. Alembic migration: `add_column('tracks', Column('kiku_play_count', Integer, server_default='0'))`
3. Modify `track_quality()` signature: add `discovery_density: float = 0.0`, `set_appearance_count: int = 0`
   - Redistribute sub-weights: rating 40%, play_familiarity 20%, set_density 10%, playlist 30%
   - Combined plays = `min((play_count or 0) + (kiku_play_count or 0), 10) / 10`
   - Apply blending based on discovery_density sign/magnitude
   - Set density: `min(set_appearance_count, 6) / 6` with same blending
   - Compute discovery_label based on conditions
   - Return tuple `(score, discovery_label)` OR keep return as float and compute label separately
4. Update `transition_score()` to accept and forward `discovery_density`, `set_appearance_counts: dict[int, int] | None`
5. Update `score_replacement()` similarly
6. Update `score_transitions()` similarly
7. Add `discovery_label` and `set_appearances` to `TransitionScoreBreakdown` schema (optional fields)
8. Add `discovery_density` to `SetBuildRequest` schema (float, default 0.0)
9. Add `discovery_density` query param to `suggest_next()` endpoint
10. Wire `discovery_density` through `build_set_sse()` → `planner.build_set()` → `transition_score()`
11. Add batch query helper for set_appearance_counts in planner (single `SELECT track_id, COUNT(*) FROM set_tracks GROUP BY track_id`)
12. Add `POST /api/tracks/{track_id}/played` endpoint in tracks router
13. Add `kiku_play_count` to `TrackResponse` schema
14. Verify sync.py does NOT reference `kiku_play_count` (confirmed — it only writes `play_count`)

**Phase 2: Frontend Play Recording**
1. In `player.svelte.ts`: add `listenedSeconds` accumulator, `lastTimeUpdate` for delta guard, session-scoped `Set<number>` dedup
2. Modify `onTimeUpdate` handler: compute delta, guard `Math.abs(time - lastTimeUpdate) < 2`, accumulate, fire POST at 60s threshold
3. Reset `listenedSeconds` on track change (in `loadAndPlay()`)
4. In `playback.svelte.ts`: similar per-deck tracking in `onDeckTimeUpdate()`, only for builder mode (express is below threshold)

**Phase 3: Frontend Discovery/Density UI**
1. Create `DiscoveryDensitySlider.svelte` — range -100 to +100, context labels
2. Add to `BuildSetDialog.svelte` between Energy arc (line 261) and Genre filter (line 263)
3. Add `discovery_density` to `SetBuildParams` type
4. Pass through to API calls
5. Add discovery labels to `ScoreBreakdown.svelte` and `TransitionScoreBreakdown` type

**Testing approach:**
- Unit tests in `tests/test_scoring.py`: test `track_quality()` with discovery_density at -1, 0, +1; test label generation
- API tests in `tests/api/`: test `POST /api/tracks/{id}/played` (increment + 404), test `discovery_density` param on build/suggest-next
- Extend `conftest.py` seed data: add `kiku_play_count` to some tracks, add more set_tracks for density testing

## Plan
<!-- Filled by /spec PLAN -->

## Plan Review
<!-- Filled if required to validate plan -->

## Implement
<!-- Filled by /spec IMPLEMENT -->

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation updates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
