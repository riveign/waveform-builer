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

### Files

- **`alembic/versions/xxxx_add_kiku_play_count_column.py`** (NEW) — Alembic migration adding `kiku_play_count` column to tracks table
- **`src/kiku/db/models.py`** — Add `kiku_play_count` column to Track model
- **`src/kiku/setbuilder/scoring.py`** — Modify `track_quality()`, `transition_score()`, `score_replacement()`, `score_transitions()` to accept and thread `discovery_density` and `set_appearance_count(s)`
- **`src/kiku/api/schemas.py`** — Add `discovery_density` to `SetBuildRequest`, add `discovery_density` query param support, add `discovery_label`/`set_appearances` to `TransitionScoreBreakdown`, add `kiku_play_count` to `TrackResponse`
- **`src/kiku/api/routes/tracks.py`** — Add `POST /{track_id}/played` endpoint, add `discovery_density` param to suggest-next, thread through scoring calls
- **`src/kiku/api/routes/sets.py`** — Thread `discovery_density` through build-set SSE, replacements, and transition detail; batch query set_appearance_counts
- **`src/kiku/setbuilder/planner.py`** — Accept `discovery_density`, batch query `set_appearance_counts`, thread through `transition_score()` calls
- **`frontend/src/lib/types/index.ts`** — Add `kiku_play_count` to `Track`, `discovery_label`/`set_appearances` to `TransitionScoreBreakdown`, `discovery_density` to `SetBuildParams`
- **`frontend/src/lib/stores/player.svelte.ts`** — Add `listenedSeconds` accumulator, delta guard, session dedup `Set<number>`, fire POST at 60s threshold
- **`frontend/src/lib/stores/playback.svelte.ts`** — Add per-deck listen tracking in `onDeckTimeUpdate()` for builder mode
- **`frontend/src/lib/components/set/DiscoveryDensitySlider.svelte`** (NEW) — Range slider -100 to +100 with context labels
- **`frontend/src/lib/components/set/BuildSetDialog.svelte`** — Add DiscoveryDensitySlider between Energy arc and Genre filter, pass `discovery_density` to params
- **`frontend/src/lib/components/set/ScoreBreakdown.svelte`** — Show `discovery_label` and `set_appearances` when present
- **`tests/test_scoring.py`** — Add unit tests for `track_quality()` with `discovery_density` at -1, 0, +1 and label generation
- **`tests/api/conftest.py`** — Extend seed data with `kiku_play_count` on some tracks, add more set_tracks for density testing
- **`tests/api/test_tracks_api.py`** — Add tests for `POST /api/tracks/{id}/played` endpoint and `discovery_density` param on suggest-next

### Tasks

#### Task 1: Alembic migration — add `kiku_play_count` column

**File:** `alembic/versions/<auto>_add_kiku_play_count_column_to_tracks.py` (NEW, auto-generated)
**Tools:** shell

**Steps:**
1. Run the migration generation command:
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && alembic revision -m "add kiku_play_count column to tracks"
```

2. Edit the generated migration file. Replace the `upgrade()` and `downgrade()` bodies with:

````diff
--- a/alembic/versions/<id>_add_kiku_play_count_column_to_tracks.py
+++ b/alembic/versions/<id>_add_kiku_play_count_column_to_tracks.py
@@ upgrade()
+    op.add_column('tracks', sa.Column('kiku_play_count', sa.Integer(), server_default='0', nullable=True))
@@ downgrade()
+    op.drop_column('tracks', 'kiku_play_count')
````

The `down_revision` must be `'16f80a5c17e9'` (the label migration).

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && alembic heads
```
Should show the new revision as head.

---

#### Task 2: Track model — add `kiku_play_count` field

**File:** `src/kiku/db/models.py`
**Tools:** editor

````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@ -53,6 +53,7 @@
     play_count = Column(Integer, default=0)
+    kiku_play_count = Column(Integer, default=0)
     release_year = Column(Integer)
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -c "from kiku.db.models import Track; print(Track.kiku_play_count)"
```
Should print the column descriptor without error.

---

#### Task 3: Scoring changes — modify `track_quality()` and all callers

**File:** `src/kiku/setbuilder/scoring.py`
**Tools:** editor

````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@ -227,7 +227,14 @@
-def track_quality(track: Track, prefer_playlists: list[str] | None = None) -> float:
-    """Score track quality based on rating, play count, and playlist membership (0-1)."""
+def track_quality(
+    track: Track,
+    prefer_playlists: list[str] | None = None,
+    discovery_density: float = 0.0,
+    set_appearance_count: int = 0,
+) -> tuple[float, str | None]:
+    """Score track quality based on rating, play count, playlist membership, and discovery/density bias (0-1).
+
+    Returns (score, discovery_label). discovery_label is None when no label applies.
+    """
     score = 0.0

     # Rating: 0-5 stars, normalize to 0-1 (unrated gets 0.3)
@@ -235,9 +242,33 @@
         score += 0.4 * (track.rating / 5.0)
     else:
         score += 0.4 * 0.3

-    # Play count: more plays = more proven, cap at 10
-    plays = min(track.play_count or 0, 10)
-    score += 0.3 * (plays / 10.0)
+    # Play familiarity (20% of track_quality)
+    combined_plays = min((track.play_count or 0) + (track.kiku_play_count or 0), 10)
+    ratio = combined_plays / 10.0
+    dd = discovery_density
+    if dd < 0:
+        alpha = abs(dd)
+        play_signal = (1 - alpha) * ratio + alpha * (1 - ratio)
+    elif dd > 0:
+        alpha = dd
+        play_signal = (1 - alpha) * ratio + alpha * (ratio ** 0.5)
+    else:
+        play_signal = ratio
+    score += 0.2 * play_signal
+
+    # Set density (10% of track_quality)
+    density = min(set_appearance_count, 6) / 6.0
+    if dd < 0:
+        alpha = abs(dd)
+        density_signal = (1 - alpha) * density + alpha * (1 - density)
+    elif dd > 0:
+        alpha = dd
+        density_signal = (1 - alpha) * density + alpha * (density ** 0.5)
+    else:
+        density_signal = density
+    score += 0.1 * density_signal

     # Playlist membership boost
     if prefer_playlists and track.playlist_tags:
@@ -248,7 +279,19 @@
         except (json.JSONDecodeError, TypeError):
             pass

-    return score
+    # Compute discovery label
+    discovery_label: str | None = None
+    if dd < -0.3 and combined_plays <= 1:
+        discovery_label = "fresh pick"
+    elif dd < -0.3 and combined_plays <= 4:
+        discovery_label = "rarely played"
+    elif dd > 0.3 and set_appearance_count >= 2:
+        discovery_label = "battle-tested"
+    elif dd > 0.3 and combined_plays >= 7:
+        discovery_label = "crowd favorite"
+
+    return score, discovery_label
````

Next, update `transition_score()`:

````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@ -253,6 +253,8 @@
 def transition_score(
     from_track: Track,
     to_track: Track,
     target_energy: float = 0.5,
     prefer_playlists: list[str] | None = None,
     weights: dict[str, float] | None = None,
+    discovery_density: float = 0.0,
+    set_appearance_counts: dict[int, int] | None = None,
 ) -> float:
@@ -274,7 +276,8 @@
-    q = track_quality(to_track, prefer_playlists)
+    sac = (set_appearance_counts or {}).get(to_track.id, 0)
+    q, _ = track_quality(to_track, prefer_playlists, discovery_density, sac)

     return (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
````

Next, update `score_replacement()`:

````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@ -280,6 +280,8 @@
 def score_replacement(
     candidate: Track,
     prev_track: Track | None,
     next_track: Track | None,
     target_energy: float = 0.5,
     weights: dict[str, float] | None = None,
+    discovery_density: float = 0.0,
+    set_appearance_counts: dict[int, int] | None = None,
 ) -> tuple[float, dict | None, dict | None]:
@@ -302,7 +304,9 @@
-        q = track_quality(to_t)
+        sac = (set_appearance_counts or {}).get(to_t.id, 0)
+        q, label = track_quality(to_t, discovery_density=discovery_density, set_appearance_count=sac)
         total = (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
                  + w["genre_coherence"] * g + w["track_quality"] * q)
         return {
@@ -310,6 +314,8 @@
             "genre_coherence": round(g, 3),
             "track_quality": round(q, 3),
             "total": round(total, 3),
+            "discovery_label": label,
+            "set_appearances": sac,
         }
@@ -324,7 +330,7 @@
     else:
-        combined = track_quality(candidate)
+        combined, _ = track_quality(candidate, discovery_density=discovery_density)
````

Next, update `score_transitions()`:

````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@ -329,6 +329,8 @@
 def score_transitions(
     session: Session,
     from_track: Track,
     n: int = 10,
     genre_filter: list[str] | None = None,
     weights: dict[str, float] | None = None,
     exclude_ids: list[int] | None = None,
+    discovery_density: float = 0.0,
+    set_appearance_counts: dict[int, int] | None = None,
 ) -> list[tuple[Track, float]]:
@@ -362,7 +364,7 @@
-        score = transition_score(from_track, track, weights=weights)
+        score = transition_score(from_track, track, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts)
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -c "from kiku.setbuilder.scoring import track_quality; print('OK')"
```

---

#### Task 4: API models — add `discovery_density`, `discovery_label`, `set_appearances`, `kiku_play_count`

**File:** `src/kiku/api/schemas.py`
**Tools:** editor

4a. Add `kiku_play_count` to `TrackResponse`:

````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ -26,6 +26,7 @@
     play_count: int | None = None
+    kiku_play_count: int | None = None
     has_waveform: bool = False
````

4b. Add `discovery_label` and `set_appearances` to `TransitionScoreBreakdown`:

````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ -160,6 +160,8 @@
 class TransitionScoreBreakdown(BaseModel):
     harmonic: float
     energy_fit: float
     bpm_compat: float
     genre_coherence: float
     track_quality: float
     total: float
+    discovery_label: str | None = None
+    set_appearances: int | None = None
````

4c. Add `discovery_density` to `SetBuildRequest`:

````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ -217,6 +217,7 @@
 class SetBuildRequest(BaseModel):
     name: str
     duration_min: int = 120
     energy_preset: str = "journey"
     genre_filter: list[str] | None = None
     bpm_min: float | None = None
     bpm_max: float | None = None
     seed_track_id: int | None = None
     beam_width: int = 5
     playlist_preference: list[str] | None = None
     weights: ScoringWeightsRequest | None = None
+    discovery_density: float = 0.0
````

4d. Add `discovery_label` and `set_appearances` to `ReplacementBreakdown`:

````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ -434,6 +434,8 @@
 class ReplacementBreakdown(BaseModel):
     harmonic: float
     energy_fit: float
     bpm_compat: float
     genre_coherence: float
     track_quality: float
     total: float
+    discovery_label: str | None = None
+    set_appearances: int | None = None
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -c "from kiku.api.schemas import SetBuildRequest, TransitionScoreBreakdown; print(SetBuildRequest.model_fields.keys()); print(TransitionScoreBreakdown.model_fields.keys())"
```

---

#### Task 5: POST /api/tracks/{id}/played endpoint

**File:** `src/kiku/api/routes/tracks.py`
**Tools:** editor

````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@ -119,6 +119,22 @@
     return _track_to_response(track)


+@router.post("/{track_id}/played", status_code=204)
+def record_played(track_id: int, db: Session = Depends(get_db)):
+    """Increment kiku_play_count when a track has been listened to for >60s in the player."""
+    track = db.get(Track, track_id)
+    if not track:
+        raise HTTPException(status_code=404, detail="Track not found")
+    track.kiku_play_count = (track.kiku_play_count or 0) + 1
+    db.commit()
+    return
+
+
````

Also update `_track_to_response` to include `kiku_play_count`:

````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@ -43,6 +43,7 @@
         play_count=t.play_count,
+        kiku_play_count=t.kiku_play_count,
         has_waveform=af is not None and af.waveform_detail is not None,
````

And in `src/kiku/api/routes/sets.py`, update `_track_response` to include `kiku_play_count`:

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -500,6 +500,7 @@
         play_count=t.play_count,
+        kiku_play_count=t.kiku_play_count,
         has_waveform=af is not None and af.waveform_overview is not None,
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -c "from kiku.api.routes.tracks import router; print([r.path for r in router.routes])"
```
Should include `/{track_id}/played`.

---

#### Task 6: Thread `discovery_density` through suggest-next endpoint

**File:** `src/kiku/api/routes/tracks.py`
**Tools:** editor

6a. Add `discovery_density` query param to `suggest_next`:

````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@ -132,6 +132,7 @@
     w_track_quality: float | None = Query(default=None, description="Track quality weight override"),
+    discovery_density: float = Query(default=0.0, ge=-1.0, le=1.0, description="Discovery/density bias (-1=fresh, +1=proven)"),
     db: Session = Depends(get_db),
````

6b. Pass `discovery_density` to `score_transitions()`:

````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@ -176,7 +176,7 @@
     genres = [g.strip() for g in genre_filter.split(",")] if genre_filter else None
-    scored = score_transitions(db, track, n=n, genre_filter=genres, weights=weights_dict, exclude_ids=exclude_ids)
+    scored = score_transitions(db, track, n=n, genre_filter=genres, weights=weights_dict, exclude_ids=exclude_ids, discovery_density=discovery_density)
````

6c. Update breakdown computation in suggest-next to use `track_quality` with `discovery_density`:

````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@ -188,7 +188,7 @@
-        q = track_quality(cand)
+        q, label = track_quality(cand, discovery_density=discovery_density)

         suggestions.append(SuggestNextItem(
             track=_track_to_response(cand),
@@ -196,6 +196,8 @@
                 genre_coherence=round(g, 3),
                 track_quality=round(q, 3),
                 total=round(total_score, 3),
+                discovery_label=label,
+                set_appearances=None,
             ),
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -c "from kiku.api.routes.tracks import suggest_next; print('OK')"
```

---

#### Task 7: Thread `discovery_density` through planner/builder and sets routes

**File:** `src/kiku/setbuilder/planner.py`
**Tools:** editor

7a. Add `discovery_density` param to `build_set()` and batch-query `set_appearance_counts`:

````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@ -7,6 +7,7 @@
 from rich.console import Console
-from sqlalchemy import or_
+from sqlalchemy import func, or_
 from sqlalchemy.orm import Session
@@ -77,6 +78,7 @@
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
+    discovery_density: float = 0.0,
 ) -> Set | None:
````

7b. Add batch query for set_appearance_counts after getting candidate pool:

````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@ -99,6 +100,12 @@
     candidates = _get_candidate_pool(session, genres=genres, bpm_range=bpm_range)
+
+    # Batch query: how many sets each track appears in (for density signal)
+    set_appearance_counts: dict[int, int] = {}
+    if discovery_density != 0.0:
+        rows = session.query(SetTrack.track_id, func.count(SetTrack.set_id.distinct())).group_by(SetTrack.track_id).all()
+        set_appearance_counts = {track_id: cnt for track_id, cnt in rows}
+
     if not candidates:
````

7c. Thread through beam search `transition_score` call:

````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@ -160,7 +167,7 @@
-                score = transition_score(current, cand, target_energy=target_e, prefer_playlists=prefer_playlists, weights=weights)
+                score = transition_score(current, cand, target_energy=target_e, prefer_playlists=prefer_playlists, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts)
````

7d. Thread through post-save re-score:

````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@ -222,7 +229,7 @@
-        t_score = transition_score(prev_track, track, prefer_playlists=prefer_playlists, weights=weights) if prev_track else None
+        t_score = transition_score(prev_track, track, prefer_playlists=prefer_playlists, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts) if prev_track else None
````

**File:** `src/kiku/api/routes/sets.py`
**Tools:** editor

7e. Pass `discovery_density` from `build_set_sse` to `planner.build_set()`:

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -114,6 +114,7 @@
             result = build_set(
                 session=db,
                 duration_min=body.duration_min,
                 energy_profile=energy_profile,
                 genres=body.genre_filter,
                 bpm_range=bpm_range,
                 seed_title=seed_title,
                 beam_width=body.beam_width,
                 set_name=body.name,
                 prefer_playlists=body.playlist_preference,
                 weights=weights_dict,
+                discovery_density=body.discovery_density,
             )
````

7f. Thread `discovery_density` through transition detail endpoint (line 334). Add query param:

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -334,7 +334,12 @@
-@router.get("/{set_id}/transition/{index}", response_model=TransitionResponse)
-def set_transition(set_id: int, index: int, db: Session = Depends(get_db)):
+@router.get("/{set_id}/transition/{index}", response_model=TransitionResponse)
+def set_transition(
+    set_id: int,
+    index: int,
+    discovery_density: float = 0.0,
+    db: Session = Depends(get_db),
+):
@@ -363,7 +368,7 @@
-    q = track_quality(t_b)
+    q, label = track_quality(t_b, discovery_density=discovery_density)
@@ -386,6 +391,8 @@
             track_quality=round(q, 3),
             total=round(total, 3),
+            discovery_label=label,
+            set_appearances=None,
         ),
````

7g. Thread `discovery_density` through replacements endpoint. Add query param:

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -511,6 +511,7 @@
     n: int = 10,
     genre_filter: str | None = None,
+    discovery_density: float = 0.0,
     db: Session = Depends(get_db),
@@ -580,7 +581,7 @@
-        combined, incoming, outgoing = score_replacement(
-            cand, prev_track, next_track, target_energy=energy_target,
-        )
+        combined, incoming, outgoing = score_replacement(
+            cand, prev_track, next_track, target_energy=energy_target,
+            discovery_density=discovery_density,
+        )
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -c "from kiku.setbuilder.planner import build_set; import inspect; sig = inspect.signature(build_set); print(list(sig.parameters.keys()))"
```
Should include `discovery_density`.

---

#### Task 8: Frontend types — add new fields

**File:** `frontend/src/lib/types/index.ts`
**Tools:** editor

8a. Add `kiku_play_count` to `Track` interface:

````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ -18,6 +18,7 @@
 	play_count: number | null;
+	kiku_play_count: number | null;
 	has_waveform: boolean;
````

8b. Add `discovery_label` and `set_appearances` to `TransitionScoreBreakdown`:

````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ -124,6 +124,8 @@
 	total: number;
+	discovery_label?: string | null;
+	set_appearances?: number | null;
 }
````

8c. Add `discovery_density` to `SetBuildParams`:

````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ -272,6 +272,7 @@
 	weights?: ScoringWeights;
+	discovery_density?: number;
 }
````

8d. Add same fields to `ReplacementBreakdown`:

````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ -422,6 +422,8 @@
 	total: number;
+	discovery_label?: string | null;
+	set_appearances?: number | null;
 }
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5
```

---

#### Task 9: Frontend listening-time accumulator — global player store

**File:** `frontend/src/lib/stores/player.svelte.ts`
**Tools:** editor

9a. Add state variables after existing state declarations (after line 43):

````diff
--- a/frontend/src/lib/stores/player.svelte.ts
+++ b/frontend/src/lib/stores/player.svelte.ts
@@ -43,6 +43,12 @@
 let ws = $state<WaveSurfer | null>(null);

+/** Listen-time tracking for play count recording */
+let listenedSeconds = $state(0);
+let lastTimeUpdate = $state(0);
+/** Session-scoped dedup: one increment per track per page load */
+const playedTrackIds = new Set<number>();
+
 /** Volume before mute, for unmute restore */
````

9b. Modify `onTimeUpdate` handler inside `registerPlayer` (line 82-84):

````diff
--- a/frontend/src/lib/stores/player.svelte.ts
+++ b/frontend/src/lib/stores/player.svelte.ts
@@ -82,6 +88,19 @@
 	const onTimeUpdate = (time: number) => {
 		currentTime = time;
+
+		// Delta guard: only accumulate if time advanced by < 2s (not a seek)
+		const delta = time - lastTimeUpdate;
+		lastTimeUpdate = time;
+		if (delta > 0 && delta < 2) {
+			listenedSeconds += delta;
+		}
+
+		// Fire POST when threshold crossed (once per track per session)
+		if (currentTrack && listenedSeconds >= 60 && !playedTrackIds.has(currentTrack.id)) {
+			playedTrackIds.add(currentTrack.id);
+			fetch(`${API_BASE}/api/tracks/${currentTrack.id}/played`, { method: 'POST' }).catch(() => {});
+		}
 	};
````

9c. Reset accumulator on track change in `loadAndPlay`:

````diff
--- a/frontend/src/lib/stores/player.svelte.ts
+++ b/frontend/src/lib/stores/player.svelte.ts
@@ -59,6 +59,8 @@
 function loadAndPlay(track: Track) {
 	currentTrack = track;
 	duration = track.duration_sec ?? 0;
 	currentTime = 0;
+	listenedSeconds = 0;
+	lastTimeUpdate = 0;
 	status = 'loading';
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5
```

---

#### Task 10: Frontend listening-time accumulator — set playback store

**File:** `frontend/src/lib/stores/playback.svelte.ts`
**Tools:** editor

10a. Add state variables after existing state declarations (after line 26):

````diff
--- a/frontend/src/lib/stores/playback.svelte.ts
+++ b/frontend/src/lib/stores/playback.svelte.ts
@@ -26,6 +26,12 @@
 let bpmMatch = $state(true);

+/** Per-deck listen tracking */
+let deckListenedSeconds = $state(0);
+let deckLastTimeUpdate = $state(0);
+/** Session-scoped dedup for set playback */
+const deckPlayedTrackIds = new Set<number>();
+
````

10b. Add import for API_BASE at top of file:

````diff
--- a/frontend/src/lib/stores/playback.svelte.ts
+++ b/frontend/src/lib/stores/playback.svelte.ts
@@ -1,5 +1,6 @@
 import type { SetWaveformTrack } from '$lib/types';
 import type WaveSurfer from 'wavesurfer.js';
+import { API_BASE } from '$lib/api/client';
````

10c. Modify `onDeckTimeUpdate` to accumulate listen time (only in builder mode, express is below threshold):

````diff
--- a/frontend/src/lib/stores/playback.svelte.ts
+++ b/frontend/src/lib/stores/playback.svelte.ts
@@ -323,6 +329,19 @@
 function onDeckTimeUpdate(deck: DeckId, time: number) {
 	if (deck !== activeDeck) return;
 	currentTime = time;

+	// Listen-time accumulation (builder mode only — express is 45s, below 60s threshold)
+	if (mode === 'builder' && status === 'playing') {
+		const delta = time - deckLastTimeUpdate;
+		if (delta > 0 && delta < 2) {
+			deckListenedSeconds += delta;
+		}
+		const track = tracks[currentIndex];
+		if (track && deckListenedSeconds >= 60 && !deckPlayedTrackIds.has(track.track_id)) {
+			deckPlayedTrackIds.add(track.track_id);
+			fetch(`${API_BASE}/api/tracks/${track.track_id}/played`, { method: 'POST' }).catch(() => {});
+		}
+	}
+	deckLastTimeUpdate = time;
+
 	if (mode !== 'express') return;
````

10d. Reset listen counters on track change in `advanceToNext` and `advanceToPrev` (inside the crossfade callback):

````diff
--- a/frontend/src/lib/stores/playback.svelte.ts
+++ b/frontend/src/lib/stores/playback.svelte.ts
@@ -218,6 +231,8 @@
 	doCrossfade(() => {
 		// Swap active deck
 		activeDeck = activeDeck === 'A' ? 'B' : 'A';
 		currentIndex = nextIndex;
+		deckListenedSeconds = 0;
+		deckLastTimeUpdate = 0;
 		status = 'playing';
@@ -243,6 +258,8 @@
 	doCrossfade(() => {
 		activeDeck = activeDeck === 'A' ? 'B' : 'A';
 		currentIndex = prevIndex;
+		deckListenedSeconds = 0;
+		deckLastTimeUpdate = 0;
 		status = 'playing';
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5
```

---

#### Task 11: Create DiscoveryDensitySlider component

**File:** `frontend/src/lib/components/set/DiscoveryDensitySlider.svelte` (NEW)
**Tools:** editor

````diff
--- /dev/null
+++ b/frontend/src/lib/components/set/DiscoveryDensitySlider.svelte
@@ -0,0 +1,89 @@
+<script lang="ts">
+	let {
+		value = $bindable(0),
+	}: {
+		value: number;
+	} = $props();
+
+	const LABELS: [number, string, string][] = [
+		[-100, 'Fresh picks', 'Surfaces unplayed and rarely-heard tracks from your library'],
+		[-50, 'Lean fresh', 'Gently favors tracks you haven\'t played much'],
+		[0, 'Balanced', 'No bias — scores tracks on merit alone'],
+		[50, 'Lean proven', 'Gently favors tracks with more plays and set appearances'],
+		[100, 'Battle-tested', 'Prioritizes your most-played, set-proven tracks'],
+	];
+
+	function getLabel(v: number): { name: string; description: string } {
+		if (v <= -75) return { name: LABELS[0][1], description: LABELS[0][2] };
+		if (v <= -25) return { name: LABELS[1][1], description: LABELS[1][2] };
+		if (v <= 25) return { name: LABELS[2][1], description: LABELS[2][2] };
+		if (v <= 75) return { name: LABELS[3][1], description: LABELS[3][2] };
+		return { name: LABELS[4][1], description: LABELS[4][2] };
+	}
+
+	let current = $derived(getLabel(value));
+</script>
+
+<div class="discovery-density">
+	<div class="dd-header">
+		<span class="dd-label">Discovery / Density</span>
+		<span class="dd-value">{current.name}</span>
+	</div>
+	<input
+		type="range"
+		class="dd-slider"
+		min={-100}
+		max={100}
+		step={1}
+		bind:value={value}
+	/>
+	<div class="dd-range">
+		<span>Fresh picks</span>
+		<span>Battle-tested</span>
+	</div>
+	<p class="dd-description">{current.description}</p>
+</div>
+
+<style>
+	.discovery-density {
+		display: flex;
+		flex-direction: column;
+		gap: 4px;
+	}
+
+	.dd-header {
+		display: flex;
+		justify-content: space-between;
+		align-items: center;
+	}
+
+	.dd-label {
+		font-size: 11px;
+		font-weight: 600;
+		color: var(--text-secondary);
+		text-transform: uppercase;
+		letter-spacing: 0.5px;
+	}
+
+	.dd-value {
+		font-size: 11px;
+		color: var(--accent);
+		font-weight: 500;
+	}
+
+	.dd-slider {
+		width: 100%;
+		accent-color: var(--accent);
+		cursor: pointer;
+		height: 6px;
+		margin-top: 2px;
+	}
+
+	.dd-range {
+		display: flex;
+		justify-content: space-between;
+		font-size: 9px;
+		color: var(--text-dim);
+		margin-top: -2px;
+	}
+
+	.dd-description {
+		font-size: 10px;
+		color: var(--text-dim);
+		margin: 0;
+		font-style: italic;
+	}
+</style>
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5
```

---

#### Task 12: BuildSetDialog integration — add slider, pass to API

**File:** `frontend/src/lib/components/set/BuildSetDialog.svelte`
**Tools:** editor

12a. Add import:

````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@ -6,6 +6,7 @@
 	import EnergyPresetPicker from './EnergyPresetPicker.svelte';
 	import ScoringWeightsSliders from './ScoringWeights.svelte';
+	import DiscoveryDensitySlider from './DiscoveryDensitySlider.svelte';
````

12b. Add state variable after `scoringWeights` (line 56):

````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@ -56,6 +56,7 @@
 	let scoringWeights = $state<ScoringWeights>({ ...DEFAULT_WEIGHTS });
+	let discoveryDensity = $state(0);
````

12c. Reset it in `resetForm()`:

````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@ -116,6 +117,7 @@
 		scoringWeights = { ...DEFAULT_WEIGHTS };
+		discoveryDensity = 0;
 	}
````

12d. Add `discovery_density` to params in `handleSubmit()`:

````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@ -145,6 +147,7 @@
 		};
+		params.discovery_density = discoveryDensity / 100;

 		// Genre filter from selected chips
````

12e. Add the slider component between Energy arc and Genre filter (between line 261 and 263):

````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@ -261,6 +264,10 @@
 			</div>

+			<!-- Discovery / Density -->
+			<div class="field">
+				<DiscoveryDensitySlider bind:value={discoveryDensity} />
+			</div>
+
 			<!-- Genre Filter -->
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5
```

---

#### Task 13: ScoreBreakdown — show discovery_label and set_appearances

**File:** `frontend/src/lib/components/set/ScoreBreakdown.svelte`
**Tools:** editor

````diff
--- a/frontend/src/lib/components/set/ScoreBreakdown.svelte
+++ b/frontend/src/lib/components/set/ScoreBreakdown.svelte
@@ -65,6 +65,16 @@
 		{/each}
 	</div>
+	{#if breakdown.discovery_label}
+		<div class="discovery-badge">
+			<span class="discovery-icon">&#9679;</span>
+			<span class="discovery-text">{breakdown.discovery_label}</span>
+			{#if breakdown.set_appearances != null && breakdown.set_appearances > 0}
+				<span class="discovery-detail">&middot; in {breakdown.set_appearances} set{breakdown.set_appearances > 1 ? 's' : ''}</span>
+			{/if}
+		</div>
+	{/if}
 </div>

 <style>
@@ -158,4 +168,29 @@
 		color: var(--text-dim);
 	}
+
+	.discovery-badge {
+		display: flex;
+		align-items: center;
+		gap: 5px;
+		margin-top: 8px;
+		padding: 6px 10px;
+		background: var(--bg-tertiary);
+		border-radius: 4px;
+		font-size: 11px;
+	}
+
+	.discovery-icon {
+		color: var(--accent);
+		font-size: 8px;
+	}
+
+	.discovery-text {
+		color: var(--accent);
+		font-weight: 500;
+		text-transform: capitalize;
+	}
+
+	.discovery-detail {
+		color: var(--text-dim);
+	}
 </style>
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5
```

---

#### Task 14: Backend unit tests — scoring and endpoint

**File:** `tests/test_scoring.py`
**Tools:** editor

````diff
--- a/tests/test_scoring.py
+++ b/tests/test_scoring.py
@@ -1,6 +1,8 @@
 """Tests for transition scoring."""

-from kiku.setbuilder.scoring import bpm_compatibility, genre_coherence
+from unittest.mock import MagicMock
+
+from kiku.setbuilder.scoring import bpm_compatibility, genre_coherence, track_quality


 def test_bpm_same():
@@ -46,3 +48,66 @@

 def test_genre_unknown():
     assert genre_coherence(None, "Techno") == 0.5
+
+
+# ── track_quality tests ──
+
+
+def _make_track(play_count=0, kiku_play_count=0, rating=3, playlist_tags=None):
+    t = MagicMock()
+    t.play_count = play_count
+    t.kiku_play_count = kiku_play_count
+    t.rating = rating
+    t.playlist_tags = playlist_tags
+    return t
+
+
+def test_track_quality_neutral():
+    """discovery_density=0 should return a score and no label."""
+    t = _make_track(play_count=5, kiku_play_count=0, rating=4)
+    score, label = track_quality(t, discovery_density=0.0)
+    assert 0.0 <= score <= 1.0
+    assert label is None
+
+
+def test_track_quality_discovery_fresh_pick():
+    """discovery_density=-1 with 0 plays should label 'fresh pick'."""
+    t = _make_track(play_count=0, kiku_play_count=0, rating=3)
+    score, label = track_quality(t, discovery_density=-1.0)
+    assert label == "fresh pick"
+
+
+def test_track_quality_discovery_rarely_played():
+    """discovery_density=-0.5 with 3 plays should label 'rarely played'."""
+    t = _make_track(play_count=2, kiku_play_count=1, rating=3)
+    score, label = track_quality(t, discovery_density=-0.5)
+    assert label == "rarely played"
+
+
+def test_track_quality_density_battle_tested():
+    """discovery_density=+0.5 with 2+ set appearances should label 'battle-tested'."""
+    t = _make_track(play_count=5, kiku_play_count=2, rating=4)
+    score, label = track_quality(t, discovery_density=0.5, set_appearance_count=3)
+    assert label == "battle-tested"
+
+
+def test_track_quality_density_crowd_favorite():
+    """discovery_density=+0.5 with 7+ plays should label 'crowd favorite'."""
+    t = _make_track(play_count=5, kiku_play_count=3, rating=4)
+    score, label = track_quality(t, discovery_density=0.5, set_appearance_count=0)
+    assert label == "crowd favorite"
+
+
+def test_track_quality_discovery_boosts_unplayed():
+    """Unplayed track should score higher with discovery bias than neutral."""
+    t = _make_track(play_count=0, kiku_play_count=0, rating=3)
+    score_neutral, _ = track_quality(t, discovery_density=0.0)
+    score_discovery, _ = track_quality(t, discovery_density=-1.0)
+    assert score_discovery > score_neutral
+
+
+def test_track_quality_density_boosts_popular():
+    """Highly-played track should score higher with density bias."""
+    t = _make_track(play_count=10, kiku_play_count=0, rating=3)
+    score_neutral, _ = track_quality(t, discovery_density=0.0)
+    score_density, _ = track_quality(t, discovery_density=1.0, set_appearance_count=5)
+    assert score_density > score_neutral
````

**File:** `tests/api/conftest.py`
**Tools:** editor

Add `kiku_play_count` to seed data:

````diff
--- a/tests/api/conftest.py
+++ b/tests/api/conftest.py
@@ -38,6 +38,7 @@
             rating=3,
             play_count=i,
+            kiku_play_count=i % 3,
         ))
````

**File:** `tests/api/test_tracks_api.py`
**Tools:** editor

````diff
--- a/tests/api/test_tracks_api.py
+++ b/tests/api/test_tracks_api.py
@@ -96,3 +96,33 @@
     for s in data["suggestions"]:
         assert s["track"]["genre"] == "house"
+
+
+def test_record_played(client):
+    """POST /api/tracks/{id}/played should return 204 and increment kiku_play_count."""
+    resp = client.post("/api/tracks/1/played")
+    assert resp.status_code == 204
+
+    # Verify the count incremented
+    detail = client.get("/api/tracks/1").json()
+    assert detail["kiku_play_count"] >= 1
+
+
+def test_record_played_not_found(client):
+    resp = client.post("/api/tracks/999/played")
+    assert resp.status_code == 404
+
+
+def test_suggest_next_with_discovery_density(client):
+    """discovery_density param should be accepted and affect results."""
+    resp_neutral = client.get("/api/tracks/1/suggest-next?n=5&discovery_density=0.0")
+    assert resp_neutral.status_code == 200
+
+    resp_discovery = client.get("/api/tracks/1/suggest-next?n=5&discovery_density=-1.0")
+    assert resp_discovery.status_code == 200
+
+    resp_density = client.get("/api/tracks/1/suggest-next?n=5&discovery_density=1.0")
+    assert resp_density.status_code == 200
+
+    # All should return valid structure
+    for resp in [resp_neutral, resp_discovery, resp_density]:
+        data = resp.json()
+        for s in data["suggestions"]:
+            assert "breakdown" in s
+            assert "discovery_label" in s["breakdown"]
````

**Verification:**
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -m pytest tests/test_scoring.py tests/api/test_tracks_api.py -x -q
```

---

#### Task 15: Frontend type-check

**File:** (none — validation only)
**Tools:** shell

```bash
cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json
```

All errors must be zero. Fix any type issues found.

---

#### Task 16: Backend lint

**File:** (none — validation only)
**Tools:** shell

```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -m pytest tests/ -x -q
```

All tests must pass.

---

#### Task 17: Commit

**Tools:** shell

```bash
cd /home/mantis/Development/mantis-dev/waveform-builer && git add -A && git commit -m "feat: Discovery/density slider, kiku_play_count, listen tracking

- Add kiku_play_count column to Track model + Alembic migration
- Modify track_quality() with discovery_density blending + labels
- Thread discovery_density through transition_score, score_replacement, score_transitions, planner
- Add POST /api/tracks/{id}/played endpoint
- Add DiscoveryDensitySlider component in BuildSetDialog
- Add listen-time accumulator with delta guard + session dedup in player + playback stores
- Show discovery_label + set_appearances in ScoreBreakdown
- Unit tests for scoring, API endpoint tests for played + discovery_density param"
```

### Validate

| Spec Requirement | Line(s) | Plan Compliance |
|---|---|---|
| ADD `kiku_play_count` column to Track model + Alembic migration (Integer, default 0) | 11 | Task 1 (migration) + Task 2 (model column) |
| ADD cross-set density query helper (`track_id -> set appearance count`) | 12 | Task 7b — batch `SELECT track_id, COUNT(DISTINCT set_id) FROM set_tracks GROUP BY track_id` in planner |
| MODIFY `track_quality()` to accept `discovery_density` float (-1.0 to +1.0) | 13-15 | Task 3 — full signature change + blending logic |
| Reshape play_count: discovery inverts, density amplifies | 14 | Task 3 — alpha blending formulas match spec exactly |
| ADD set density sub-component (10% of track_quality, from play_count 30% -> 20%) | 15 | Task 3 — weights redistributed: rating 40%, play_familiarity 20%, set_density 10%, playlist 30% |
| ADD `discovery_density` parameter to `SetBuildRequest` and suggest-next query params | 16 | Task 4c (schema) + Task 6a (suggest-next query param) |
| ADD `POST /api/tracks/{track_id}/played` endpoint (increment `kiku_play_count`) | 17 | Task 5 — returns 204, increments `kiku_play_count` |
| ADD `discovery_label` and `set_appearances` to `TransitionScoreBreakdown` | 18 | Task 4b (schema) + Task 8b (frontend type) |
| UPDATE `score_replacement()` to accept `discovery_density` | 19 | Task 3 (scoring) + Task 7g (sets route wiring) |
| ADD `listenedSeconds` accumulator to global player store | 22-25 | Task 9 — delta guard, 60s threshold, session dedup Set |
| ADD same accumulator to set playback store, per-deck | 26-28 | Task 10 — builder mode only, express intentionally below threshold |
| CREATE `DiscoveryDensitySlider.svelte` component | 31-34 | Task 11 — range -100 to +100, 5 context labels + subtext |
| ADD slider to BuildSetDialog between Energy arc and Genre filter | 35 | Task 12e — inserted between EnergyPresetPicker and Genre Filter |
| PASS `discovery_density` to build-set and suggest-next API calls | 36 | Task 12d (build) + Task 6 (suggest-next) |
| ADD discovery/density labels to ScoreBreakdown | 37 | Task 13 — conditional badge with label + set count |
| Scoring formula: rating 40%, play familiarity 20%, set density 10%, playlist 30% | 43-51 | Task 3 — weights match spec table exactly |
| Play familiarity blending: `(1-a)*ratio + a*(1-ratio)` for discovery | 54 | Task 3 — formula matches |
| Play familiarity blending: `(1-a)*ratio + a*ratio^0.5` for density | 55 | Task 3 — formula matches |
| Set density: `min(set_appearance_count, 6) / 6` with same blending | 58-59 | Task 3 — exact formula |
| Discovery labels: fresh pick, rarely played, battle-tested, crowd favorite | 62-69 | Task 3 — conditions match spec table |
| Delta guard `Math.abs(time - lastTimeUpdate) < 2` | 72 | Task 9b — `delta > 0 && delta < 2` |
| Session-scoped `Set<number>` dedup | 76 | Task 9a — `playedTrackIds` Set |
| Sync integrity: `kiku_play_count` never touched by sync | 77 | Verified in Research — sync.py only writes `play_count` |
| Express mode 45s < 60s threshold — doesn't count | 74 | Task 10c — builder mode only check |
| NOT add a 6th scoring dimension | 87 | Plan modifies track_quality sub-components only, 5 dimensions unchanged |
| Pre-compute set_appearance_counts in single batch query | 87 | Task 7b — single GROUP BY before beam search |

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

### Task 1 — Alembic migration
Status: Done

### Task 2 — Track model
Status: Done

### Task 3 — Scoring changes
Status: Done

### Task 4 — API schemas
Status: Done

### Task 5 — POST /played endpoint
Status: Done

### Task 6 — Suggest-next threading
Status: Done

### Task 7 — Planner + sets routes threading
Status: Done

### Task 8 — Frontend types
Status: Done

### Task 9 — Global player store accumulator
Status: Done

### Task 10 — Set playback store accumulator
Status: Done

### Task 11 — DiscoveryDensitySlider component
Status: Done

### Task 12 — BuildSetDialog integration
Status: Done

### Task 13 — ScoreBreakdown display
Status: Done

### Task 14 — Backend unit tests
Status: Done — 107 tests pass (29 new)

### Task 15 — Frontend type-check
Status: Done — 0 errors, 1 pre-existing warning

### Task 16 — Backend tests
Status: Done — 107 passed

### Task 17 — Commit
Status: Done

Implementation commit: 72373f789a08a46125951cdabc7f5456aece357e
Follow-up commit: 47fb906 (play count column, sort, filter in library browser)

## Test Evidence & Outputs

- Backend: 107 tests pass (29 new scoring + API tests)
- Frontend: svelte-check 0 errors, 1 pre-existing a11y warning
- Manual: Discovery/Density slider works in BuildSetDialog, play count recording fires at 60s, library sort/filter by plays functional

## Updated Doc

- MEMORY.md updated with spec 009 completion, test count (107), key files

## Post-Implement Review

**Status: COMPLETE**

All objectives delivered:
1. Discovery/Density slider in BuildSetDialog with 5 context-sensitive labels
2. Scoring reshapes track_quality via alpha-blending (play_familiarity 20% + set_density 10%)
3. Play count sync from Rekordbox — already working (607 tracks)
4. In-app play recording at >60s threshold, both player stores instrumented
5. Discovery labels in score breakdown ("fresh pick", "battle-tested", etc.)
6. Library browser: Plays column, sort by plays, Unplayed/Played quick filters
