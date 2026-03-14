# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
A Tinder-style swipe UI for reviewing energy and mood predictions — the DJ listens to each track playing in the browser, sees the model's prediction, and swipes to confirm, correct, or skip. Every decision feeds back into the training set, closing the human-in-the-loop retraining cycle from spec 001-autotag-energy.

## Mid-Level Objectives (MLO)
- BUILD a card-based UI in the existing Dash/SvelteKit app that shows one track at a time with: waveform player, predicted energy zone, confidence score, and current audio features
- PLAY the track audio directly in the browser (HTML5 audio element) so the DJ can listen before deciding
- PRESENT swipe actions: confirm prediction (right/green), override with correct zone (left/choose), skip (up/gray)
- DISPLAY the prediction alongside mood indicators (aggressive/relaxed, happy/sad axes) so the DJ builds intuition about what the model sees vs. what they feel
- STORE every decision (confirm, override, skip) in the DB — confirmed and overridden predictions become `energy_source = "approved"` training data
- SUPPORT batch sessions: DJ opens the tinder, reviews N tracks, closes — progress is saved, next session starts where they left off
- TRACK session stats: reviewed count, confirmed %, overridden %, skip rate, and how the model's accuracy evolves over sessions
- ENABLE one-click retrain after a review session: "You reviewed 50 tracks. Retrain model now?" which triggers `train_energy_model()` with the new approved data

## Details (DT)

### Track Queue
- Queue = all tracks with `energy_predicted IS NOT NULL AND energy_source = "auto"` (not yet reviewed)
- Order by confidence ascending (show uncertain predictions first — that's where human input is most valuable)
- DJ can filter queue by genre family or BPM range

### Card Layout
- Large waveform with playback controls (play/pause, seek) — reuse existing waveform visualization
- Track metadata: title, artist, genre, BPM, key
- Prediction display: predicted zone (warmup/build/peak) with confidence bar
- Mood radar: show mood_happy, mood_sad, mood_aggressive, mood_relaxed as a small 4-axis spider/radar
- Action buttons: Confirm (keeps prediction), Override (dropdown to pick correct zone), Skip

### Audio Playback
- Use HTML5 `<audio>` element pointing to the track's `file_path`
- Auto-play when card appears, pause when swiping
- Consider serving audio through a local endpoint if file paths are on external drives

### Decision Storage
- On confirm: set `energy_source = "approved"`, keep `energy_predicted` as-is
- On override: set `energy_source = "approved"`, update `energy_predicted` to DJ's choice, store `energy_confidence = 1.0`
- On skip: leave `energy_source = "auto"`, don't include in training data
- All decisions logged with timestamp for session tracking

### Retraining Integration
- After review session ends, show summary: "Reviewed 47 tracks: 38 confirmed, 6 overridden, 3 skipped"
- Button: "Retrain model with new data" → calls `train_energy_model(include_approved=True)`
- Show before/after accuracy comparison

### Teaching Moment
- When the DJ overrides a prediction, briefly show which features confused the model (e.g., "Model predicted build because loudness was high, but you said warmup — this teaches the model that loudness alone doesn't mean energy")
- This is the Miyagi moment: learning through correcting

## Behavior
You are a senior AI engineer building an interactive music review tool. The UI must feel fast and fun — like swiping through tracks, not filling out forms. Prioritize audio playback latency and smooth transitions between cards. The teaching moments should be concise (one sentence) and appear non-intrusively.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Affected Files & Components

| Layer | File | Relevance |
|-------|------|-----------|
| **ML engine** | `src/djsetbuilder/analysis/autotag.py` | `train_energy_model(include_approved=True)`, `predict_energy()`, `extract_features()` — 17-dim RF classifier mapping 9 tags → 3 zones (warmup/build/peak). `ZONE_MAP` defines mappings. Feature importance available for teaching moments. |
| **DB models** | `src/djsetbuilder/db/models.py:57-59` | Track columns: `energy_predicted` (String), `energy_confidence` (Float), `energy_source` (String: "manual"/"auto"/"approved") |
| **Audio streaming** | `src/djsetbuilder/api/routes/audio.py` | `GET /api/audio/{track_id}` — HTTP Range support, FFmpeg transcoding for AIFF/FLAC → MP3. Already usable by wavesurfer.js. |
| **Waveform player** | `frontend/src/lib/components/waveform/WavesurferPlayer.svelte` | Props: trackId, peaks (base64), duration, beats. Uses `${API_BASE}/api/audio/${trackId}`. Emits timeupdate/play/pause. Reusable directly in tinder cards. |
| **Track view** | `frontend/src/lib/components/waveform/TrackView.svelte` | Loads waveform detail + features via `$effect` on track.id change. Reference for loading pattern. |
| **Workspace tabs** | `frontend/src/lib/components/Workspace.svelte` | 3 tabs (Track/Set/DNA) with keyboard shortcuts 1-3. Tab type defined in `ui.svelte.ts`. Add `'tinder'` tab with key=4. |
| **UI store** | `frontend/src/lib/stores/ui.svelte.ts` | `Tab` type union, `activeTab` state, `selectedTrack`. Extend Tab type with `'tinder'`. |
| **Track store** | `frontend/src/lib/stores/tracks.svelte.ts` | `search()` with paginated response. Reference for tinder queue store pattern. |
| **API schemas** | `src/djsetbuilder/api/schemas.py` | `TrackResponse` (has energy field), `TrackFeaturesResponse` (has all mood fields). Need new tinder-specific schemas. |
| **Stats API** | `src/djsetbuilder/api/routes/stats.py` | 5 endpoints for DNA viz. Reference for new tinder stats endpoint. |
| **Types** | `frontend/src/lib/types/index.ts` | `Track`, `TrackFeatures`, `MoodPoint` — need new `TinderTrack`, `TinderDecision`, `TinderSession` types. |
| **API clients** | `frontend/src/lib/api/tracks.ts` | `searchTracks()`, `getTrackFeatures()`, `suggestNext()`. Need new tinder API client. |
| **CLI** | `src/djsetbuilder/cli.py:763+` | `djset autotag energy --retrain` — calls same `train_energy_model()`. No changes needed. |
| **Tests** | `tests/test_autotag.py` | MagicMock AudioFeatures, `tmp_path` for model I/O, zone mapping tests. Pattern to follow. |
| **API tests** | `tests/api/conftest.py` | In-memory SQLite + TestClient with DI override. Seed data with 20 tracks. |

### Key Observations

1. **Queue query is straightforward** — `WHERE energy_predicted IS NOT NULL AND energy_source = 'auto' ORDER BY energy_confidence ASC` maps directly to SQLAlchemy.
2. **Audio already works** — `GET /api/audio/{track_id}` with Range headers. WavesurferPlayer.svelte can be reused as-is for card playback.
3. **Feature importance exists** — `train_energy_model()` returns `feature_importance` list. This powers the teaching moment: "Model saw high loudness → predicted build. You said warmup."
4. **Mood data available** — `TrackFeaturesResponse` already includes `mood_happy/sad/aggressive/relaxed`. No new analysis needed — just a radar chart component.
5. **No session tracking table** — Decisions are stored on the Track row itself (energy_source → "approved"). Session stats need either a new table or computed from Track timestamps.
6. **Retraining is synchronous** — `train_energy_model()` runs in-process. With ~4K tracks and 17 features, RF training takes <2 seconds. No async/SSE needed.

### Strategy

**Backend (3 new endpoints + 1 store function):**
1. `GET /api/tinder/queue` — paginated queue of unreviewed tracks (energy_source="auto") with features + waveform data, ordered by confidence ASC. Query params: genre_family, bpm_min, bpm_max, limit.
2. `POST /api/tinder/decide` — body: `{track_id, decision: "confirm"|"override"|"skip", override_zone?: string}`. Updates Track row. Returns next track in queue for prefetch.
3. `POST /api/tinder/retrain` — triggers `train_energy_model(include_approved=True)`. Returns metrics + feature importance for before/after comparison.
4. `GET /api/tinder/stats` — session summary: total reviewed, confirmed %, overridden %, skip rate, queue remaining.
5. New store function `get_tinder_queue()` in `store.py` for the queue query.

**Frontend (4 new components + 1 store + 1 API client):**
1. `EnergyTinder.svelte` — main container, manages queue state and card transitions
2. `TinderCard.svelte` — single track card: waveform (reuse WavesurferPlayer), metadata, prediction display, mood radar, action buttons
3. `MoodRadar.svelte` — 4-axis SVG radar chart (happy/sad/aggressive/relaxed)
4. `TinderSummary.svelte` — end-of-session summary with retrain button and accuracy comparison
5. `tinder.svelte.ts` — store managing queue, current card index, session decisions
6. `frontend/src/lib/api/tinder.ts` — API client for all tinder endpoints

**Integration:**
- Add `'tinder'` to Tab type in `ui.svelte.ts`
- Add tab in `Workspace.svelte` with keyboard shortcut `4`
- Teaching moment: on override, show top-2 feature importances from model metadata with one-sentence explanation

**Testing:**
- `tests/api/test_tinder_api.py` — queue ordering, decide confirm/override/skip, retrain trigger, stats computation
- Seed conftest with tracks having `energy_predicted` + `energy_source="auto"` at various confidence levels
- Frontend: manual testing (no Vitest setup exists yet)

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
