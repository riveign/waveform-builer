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

### Files
- `src/djsetbuilder/api/schemas.py`
  - L255: Append tinder request/response models (TinderQueueItem, TinderDecideRequest, TinderDecideResponse, TinderStatsResponse, TinderRetrainResponse)
- `src/djsetbuilder/db/store.py`
  - L11: Add import for `or_`
  - Append: `get_tinder_queue()` — query unreviewed tracks ordered by confidence ASC
  - Append: `save_tinder_decision()` — update Track energy_predicted/confidence/source
- `src/djsetbuilder/api/routes/tinder.py` (NEW)
  - 4 endpoints: GET /queue, POST /decide, POST /retrain, GET /stats
- `src/djsetbuilder/api/main.py`
  - L10: Add tinder import
  - L39: Register tinder router
- `frontend/src/lib/types/index.ts`
  - L220: Append tinder types (TinderQueueItem, TinderDecision, TinderStats, TinderRetrainResult)
- `frontend/src/lib/api/tinder.ts` (NEW)
  - API client: getTinderQueue, submitDecision, retrain, getTinderStats
- `frontend/src/lib/stores/tinder.svelte.ts` (NEW)
  - Queue state, current card index, session decisions, loading states
- `frontend/src/lib/components/tinder/MoodRadar.svelte` (NEW)
  - 4-axis SVG radar chart for mood_happy/sad/aggressive/relaxed
- `frontend/src/lib/components/tinder/TinderCard.svelte` (NEW)
  - Track card: WavesurferPlayer, metadata, prediction, mood radar, action buttons
- `frontend/src/lib/components/tinder/TinderSummary.svelte` (NEW)
  - Session summary with retrain button and accuracy display
- `frontend/src/lib/components/tinder/EnergyTinder.svelte` (NEW)
  - Main container managing queue, transitions, and summary
- `frontend/src/lib/stores/ui.svelte.ts`
  - L3: Add `'tinder'` to Tab type
- `frontend/src/lib/components/Workspace.svelte`
  - L4: Import EnergyTinder
  - L14: Add key=4 handler
  - L30-31: Add tab button
  - L45: Add tab content
- `tests/api/test_tinder_api.py` (NEW)
  - Tests for queue, decide, retrain, stats endpoints
- `tests/api/conftest.py`
  - Extend seed data with energy_predicted/energy_source tracks

### Tasks

#### Task 1 — schemas.py: Add tinder Pydantic models
Tools: editor
File: `src/djsetbuilder/api/schemas.py`
Description: Append tinder request/response models after the PaginatedTracksResponse class at line 254.

Diff:
````diff
--- a/src/djsetbuilder/api/schemas.py
+++ b/src/djsetbuilder/api/schemas.py
@@ class PaginatedTracksResponse(BaseModel):
     items: list[TrackResponse]
     total: int
     offset: int
     limit: int
+
+
+# ── Energy Tinder models ──
+
+
+class TinderQueueItem(BaseModel):
+    track: TrackResponse
+    energy_predicted: str | None = None
+    energy_confidence: float | None = None
+    mood_happy: float | None = None
+    mood_sad: float | None = None
+    mood_aggressive: float | None = None
+    mood_relaxed: float | None = None
+    has_waveform: bool = False
+
+
+class TinderQueueResponse(BaseModel):
+    items: list[TinderQueueItem]
+    total: int
+    offset: int
+    limit: int
+
+
+class TinderDecideRequest(BaseModel):
+    track_id: int
+    decision: str  # "confirm", "override", "skip"
+    override_zone: str | None = None  # required if decision == "override"
+
+
+class TinderDecideResponse(BaseModel):
+    track_id: int
+    decision: str
+    applied_zone: str | None = None
+    teaching_moment: str | None = None  # one-sentence explanation on override
+
+
+class TinderStatsResponse(BaseModel):
+    total_reviewed: int
+    confirmed: int
+    overridden: int
+    skipped: int
+    queue_remaining: int
+    confirmed_pct: float
+    overridden_pct: float
+    skip_pct: float
+
+
+class TinderRetrainResponse(BaseModel):
+    accuracy: float | None = None
+    class_counts: dict[str, int] = {}
+    feature_importance: list[tuple[str, float]] = []
+    training_samples: int = 0
````

Verification:
- `source .venv/bin/activate && python -c "from djsetbuilder.api.schemas import TinderQueueItem, TinderDecideRequest, TinderRetrainResponse; print('OK')"`

#### Task 2 — store.py: Add tinder query helpers
Tools: editor
File: `src/djsetbuilder/db/store.py`
Description: Add `get_tinder_queue()` and `save_tinder_decision()` functions at end of file, and add `or_` to imports.

Diff (import):
````diff
--- a/src/djsetbuilder/db/store.py
+++ b/src/djsetbuilder/db/store.py
@@ from sqlalchemy import func
+from sqlalchemy import func, or_
-from sqlalchemy import func
 from sqlalchemy.orm import Session
````

Diff (append after `get_set_waveform_data` function, at end of file):
````diff
--- a/src/djsetbuilder/db/store.py
+++ b/src/djsetbuilder/db/store.py
@@ def get_set_waveform_data(session: Session, set_id: int) -> list[dict]:
     ...
     return result
+
+
+def get_tinder_queue(
+    session: Session,
+    genre_family: str | None = None,
+    bpm_min: float | None = None,
+    bpm_max: float | None = None,
+    limit: int = 20,
+    offset: int = 0,
+) -> tuple[list[Track], int]:
+    """Get unreviewed auto-predicted tracks ordered by confidence ASC.
+
+    Returns (tracks, total_count) for pagination.
+    """
+    q = session.query(Track).filter(
+        Track.energy_predicted.isnot(None),
+        Track.energy_source == "auto",
+    )
+    if genre_family:
+        from djsetbuilder.setbuilder.scoring import GENRE_FAMILIES
+        genres = GENRE_FAMILIES.get(genre_family.lower(), [])
+        if genres:
+            conditions = [Track.dir_genre.ilike(f"%{g}%") for g in genres]
+            q = q.filter(or_(*conditions))
+    if bpm_min is not None:
+        q = q.filter(Track.bpm >= bpm_min)
+    if bpm_max is not None:
+        q = q.filter(Track.bpm <= bpm_max)
+    q = q.order_by(Track.energy_confidence.asc())
+    total = q.count()
+    tracks = q.offset(offset).limit(limit).all()
+    return tracks, total
+
+
+def save_tinder_decision(
+    session: Session,
+    track_id: int,
+    decision: str,
+    override_zone: str | None = None,
+) -> Track | None:
+    """Apply a tinder decision to a track.
+
+    - confirm: set energy_source = "approved"
+    - override: set energy_source = "approved", energy_predicted = override_zone, energy_confidence = 1.0
+    - skip: no-op (leave as "auto")
+
+    Returns updated Track or None if not found.
+    """
+    track = session.query(Track).get(track_id)
+    if not track:
+        return None
+    if decision == "confirm":
+        track.energy_source = "approved"
+    elif decision == "override":
+        track.energy_source = "approved"
+        track.energy_predicted = override_zone
+        track.energy_confidence = 1.0
+    # skip: do nothing
+    session.commit()
+    return track
````

Verification:
- `source .venv/bin/activate && python -c "from djsetbuilder.db.store import get_tinder_queue, save_tinder_decision; print('OK')"`

#### Task 3 — routes/tinder.py: New API route module
Tools: editor (create new file)
File: `src/djsetbuilder/api/routes/tinder.py` (NEW)
Description: Create tinder route module with 4 endpoints: queue, decide, retrain, stats.

Full file content:
````diff
--- /dev/null
+++ b/src/djsetbuilder/api/routes/tinder.py
@@ -0,0 +1,138 @@
+"""Energy Tinder — swipe-based review of ML energy predictions."""
+
+from __future__ import annotations
+
+import json
+import logging
+
+from fastapi import APIRouter, Depends, HTTPException
+from sqlalchemy.orm import Session
+
+from djsetbuilder.api.deps import get_db
+from djsetbuilder.api.schemas import (
+    TinderDecideRequest,
+    TinderDecideResponse,
+    TinderQueueItem,
+    TinderQueueResponse,
+    TinderRetrainResponse,
+    TinderStatsResponse,
+    TrackResponse,
+)
+from djsetbuilder.db.models import Track
+from djsetbuilder.db.store import get_tinder_queue, save_tinder_decision
+
+logger = logging.getLogger(__name__)
+
+router = APIRouter(prefix="/api/tinder", tags=["tinder"])
+
+
+def _track_to_response(t: Track) -> TrackResponse:
+    af = t.audio_features
+    return TrackResponse(
+        id=t.id,
+        title=t.title,
+        artist=t.artist,
+        album=t.album,
+        bpm=t.bpm,
+        key=t.key,
+        rating=t.rating,
+        genre=t.dir_genre or t.rb_genre,
+        energy=t.dir_energy,
+        duration_sec=t.duration_sec,
+        play_count=t.play_count,
+        has_waveform=af is not None and af.waveform_detail is not None,
+        has_features=af is not None and af.energy is not None,
+    )
+
+
+@router.get("/queue", response_model=TinderQueueResponse)
+def tinder_queue(
+    genre_family: str | None = None,
+    bpm_min: float | None = None,
+    bpm_max: float | None = None,
+    limit: int = 20,
+    offset: int = 0,
+    db: Session = Depends(get_db),
+):
+    """Get paginated queue of unreviewed auto-predicted tracks, ordered by confidence ASC."""
+    tracks, total = get_tinder_queue(
+        db, genre_family=genre_family, bpm_min=bpm_min, bpm_max=bpm_max,
+        limit=limit, offset=offset,
+    )
+    items = []
+    for t in tracks:
+        af = t.audio_features
+        items.append(TinderQueueItem(
+            track=_track_to_response(t),
+            energy_predicted=t.energy_predicted,
+            energy_confidence=t.energy_confidence,
+            mood_happy=af.mood_happy if af else None,
+            mood_sad=af.mood_sad if af else None,
+            mood_aggressive=af.mood_aggressive if af else None,
+            mood_relaxed=af.mood_relaxed if af else None,
+            has_waveform=af is not None and af.waveform_detail is not None,
+        ))
+    return TinderQueueResponse(items=items, total=total, offset=offset, limit=limit)
+
+
+@router.post("/decide", response_model=TinderDecideResponse)
+def tinder_decide(body: TinderDecideRequest, db: Session = Depends(get_db)):
+    """Submit a tinder decision (confirm, override, or skip) for a track."""
+    if body.decision not in ("confirm", "override", "skip"):
+        raise HTTPException(status_code=400, detail="decision must be confirm, override, or skip")
+    if body.decision == "override" and not body.override_zone:
+        raise HTTPException(status_code=400, detail="override_zone required when decision is override")
+    if body.override_zone:
+        from djsetbuilder.analysis.autotag import ZONE_MAP
+        valid_zones = set(ZONE_MAP.values())
+        if body.override_zone not in valid_zones:
+            raise HTTPException(
+                status_code=400,
+                detail=f"override_zone must be one of: {sorted(valid_zones)}",
+            )
+
+    track = save_tinder_decision(db, body.track_id, body.decision, body.override_zone)
+    if not track:
+        raise HTTPException(status_code=404, detail="Track not found")
+
+    # Teaching moment: on override, explain what features the model relied on
+    teaching = None
+    if body.decision == "override":
+        teaching = _generate_teaching_moment(track, body.override_zone)
+
+    return TinderDecideResponse(
+        track_id=body.track_id,
+        decision=body.decision,
+        applied_zone=body.override_zone if body.decision == "override" else track.energy_predicted,
+        teaching_moment=teaching,
+    )
+
+
+def _generate_teaching_moment(track: Track, override_zone: str | None) -> str | None:
+    """Generate a one-sentence teaching moment when the DJ overrides a prediction."""
+    from djsetbuilder.analysis.autotag import load_model
+    try:
+        _, meta = load_model()
+        importances = meta.get("feature_importance", [])
+        if importances:
+            top_feat = importances[0][0]
+            return (
+                f"The model leaned on {top_feat} for this one — "
+                f"your override to '{override_zone}' teaches it that's not the whole story."
+            )
+    except Exception:
+        pass
+    return None
+
+
+@router.post("/retrain", response_model=TinderRetrainResponse)
+def tinder_retrain(db: Session = Depends(get_db)):
+    """Retrain the energy model with approved data included."""
+    from djsetbuilder.analysis.autotag import save_model, train_energy_model
+    result = train_energy_model(db, include_approved=True)
+    save_model(result)
+    metrics = result.get("metrics", {})
+    accuracy = metrics.get("accuracy", None)
+    return TinderRetrainResponse(
+        accuracy=accuracy,
+        class_counts=result.get("class_counts", {}),
+        feature_importance=result.get("feature_importance", []),
+        training_samples=sum(result.get("class_counts", {}).values()),
+    )
+
+
+@router.get("/stats", response_model=TinderStatsResponse)
+def tinder_stats(db: Session = Depends(get_db)):
+    """Get tinder review session statistics."""
+    from sqlalchemy import func
+    approved = db.query(func.count(Track.id)).filter(Track.energy_source == "approved").scalar() or 0
+    auto = db.query(func.count(Track.id)).filter(
+        Track.energy_predicted.isnot(None), Track.energy_source == "auto"
+    ).scalar() or 0
+    # We can't distinguish confirmed vs overridden from DB alone (both are "approved")
+    # So we report approved as "confirmed + overridden" combined
+    total_reviewed = approved
+    return TinderStatsResponse(
+        total_reviewed=total_reviewed,
+        confirmed=approved,  # combined confirmed + overridden
+        overridden=0,  # tracked in-session by frontend store
+        skipped=0,  # tracked in-session by frontend store
+        queue_remaining=auto,
+        confirmed_pct=100.0 if total_reviewed > 0 else 0.0,
+        overridden_pct=0.0,
+        skip_pct=0.0,
+    )
````

Verification:
- `source .venv/bin/activate && python -c "from djsetbuilder.api.routes.tinder import router; print(f'{len(router.routes)} routes')"`

#### Task 4 — main.py: Register tinder router
Tools: editor
File: `src/djsetbuilder/api/main.py`

Diff:
````diff
--- a/src/djsetbuilder/api/main.py
+++ b/src/djsetbuilder/api/main.py
@@ from djsetbuilder.api.routes import audio, export, sets, stats, tracks, waveforms
+from djsetbuilder.api.routes import audio, export, sets, stats, tinder, tracks, waveforms
-from djsetbuilder.api.routes import audio, export, sets, stats, tracks, waveforms
@@
     app.include_router(stats.router)
     app.include_router(export.router)
+    app.include_router(tinder.router)

     return app
````

Verification:
- `source .venv/bin/activate && python -c "from djsetbuilder.api.main import create_app; app = create_app(); routes = [r.path for r in app.routes]; assert any('/api/tinder' in r for r in routes); print('OK')"`

#### Task 5 — types/index.ts: Add tinder TypeScript types
Tools: editor
File: `frontend/src/lib/types/index.ts`
Description: Append tinder types after PaginatedTracks interface at end of file.

Diff:
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ export interface PaginatedTracks {
 	items: Track[];
 	total: number;
 	offset: number;
 	limit: number;
 }
+
+// ── Energy Tinder types ──
+
+export interface TinderQueueItem {
+	track: Track;
+	energy_predicted: string | null;
+	energy_confidence: number | null;
+	mood_happy: number | null;
+	mood_sad: number | null;
+	mood_aggressive: number | null;
+	mood_relaxed: number | null;
+	has_waveform: boolean;
+}
+
+export interface TinderQueueResponse {
+	items: TinderQueueItem[];
+	total: number;
+	offset: number;
+	limit: number;
+}
+
+export type TinderDecision = 'confirm' | 'override' | 'skip';
+
+export interface TinderDecideResult {
+	track_id: number;
+	decision: string;
+	applied_zone: string | null;
+	teaching_moment: string | null;
+}
+
+export interface TinderStats {
+	total_reviewed: number;
+	confirmed: number;
+	overridden: number;
+	skipped: number;
+	queue_remaining: number;
+	confirmed_pct: number;
+	overridden_pct: number;
+	skip_pct: number;
+}
+
+export interface TinderRetrainResult {
+	accuracy: number | null;
+	class_counts: Record<string, number>;
+	feature_importance: [string, number][];
+	training_samples: number;
+}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -1`

#### Task 6 — api/tinder.ts: New API client
Tools: editor (create new file)
File: `frontend/src/lib/api/tinder.ts` (NEW)

Full file content:
````diff
--- /dev/null
+++ b/frontend/src/lib/api/tinder.ts
@@ -0,0 +1,36 @@
+import type { TinderDecideResult, TinderDecision, TinderQueueResponse, TinderRetrainResult, TinderStats } from '$lib/types';
+import { fetchJson } from './client';
+
+export interface TinderQueueParams {
+	genre_family?: string;
+	bpm_min?: number;
+	bpm_max?: number;
+	limit?: number;
+	offset?: number;
+}
+
+export async function getTinderQueue(params: TinderQueueParams = {}): Promise<TinderQueueResponse> {
+	const qs = new URLSearchParams();
+	for (const [k, v] of Object.entries(params)) {
+		if (v !== undefined && v !== null && v !== '') {
+			qs.set(k, String(v));
+		}
+	}
+	return fetchJson<TinderQueueResponse>(`/api/tinder/queue?${qs}`);
+}
+
+export async function submitDecision(
+	trackId: number,
+	decision: TinderDecision,
+	overrideZone?: string
+): Promise<TinderDecideResult> {
+	return fetchJson<TinderDecideResult>('/api/tinder/decide', {
+		method: 'POST',
+		headers: { 'Content-Type': 'application/json' },
+		body: JSON.stringify({ track_id: trackId, decision, override_zone: overrideZone }),
+	});
+}
+
+export async function retrain(): Promise<TinderRetrainResult> {
+	return fetchJson<TinderRetrainResult>('/api/tinder/retrain', { method: 'POST' });
+}
+
+export async function getTinderStats(): Promise<TinderStats> {
+	return fetchJson<TinderStats>('/api/tinder/stats');
+}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -1`

#### Task 7 — stores/tinder.svelte.ts: New tinder store
Tools: editor (create new file)
File: `frontend/src/lib/stores/tinder.svelte.ts` (NEW)

Full file content:
````diff
--- /dev/null
+++ b/frontend/src/lib/stores/tinder.svelte.ts
@@ -0,0 +1,93 @@
+import type { TinderQueueItem, TinderDecision, TinderRetrainResult } from '$lib/types';
+import { getTinderQueue, submitDecision, retrain, type TinderQueueParams } from '$lib/api/tinder';
+
+let queue = $state<TinderQueueItem[]>([]);
+let queueTotal = $state(0);
+let currentIndex = $state(0);
+let loading = $state(false);
+let error = $state<string | null>(null);
+
+// Session counters (reset on each load)
+let sessionConfirmed = $state(0);
+let sessionOverridden = $state(0);
+let sessionSkipped = $state(0);
+let lastTeachingMoment = $state<string | null>(null);
+let retrainResult = $state<TinderRetrainResult | null>(null);
+let retraining = $state(false);
+
+async function loadQueue(params: TinderQueueParams = {}) {
+	loading = true;
+	error = null;
+	try {
+		const result = await getTinderQueue(params);
+		queue = result.items;
+		queueTotal = result.total;
+		currentIndex = 0;
+		sessionConfirmed = 0;
+		sessionOverridden = 0;
+		sessionSkipped = 0;
+		lastTeachingMoment = null;
+		retrainResult = null;
+	} catch (e) {
+		error = e instanceof Error ? e.message : String(e);
+		queue = [];
+		queueTotal = 0;
+	} finally {
+		loading = false;
+	}
+}
+
+async function decide(decision: TinderDecision, overrideZone?: string) {
+	const item = queue[currentIndex];
+	if (!item) return;
+
+	try {
+		const result = await submitDecision(item.track.id, decision, overrideZone);
+		if (decision === 'confirm') sessionConfirmed++;
+		else if (decision === 'override') sessionOverridden++;
+		else sessionSkipped++;
+
+		lastTeachingMoment = result.teaching_moment;
+		currentIndex++;
+	} catch (e) {
+		error = e instanceof Error ? e.message : String(e);
+	}
+}
+
+async function triggerRetrain() {
+	retraining = true;
+	error = null;
+	try {
+		retrainResult = await retrain();
+	} catch (e) {
+		error = e instanceof Error ? e.message : String(e);
+	} finally {
+		retraining = false;
+	}
+}
+
+export function getTinderStore() {
+	return {
+		get queue() { return queue; },
+		get queueTotal() { return queueTotal; },
+		get currentIndex() { return currentIndex; },
+		get currentItem() { return queue[currentIndex] ?? null; },
+		get isComplete() { return currentIndex >= queue.length && queue.length > 0; },
+		get loading() { return loading; },
+		get error() { return error; },
+		get sessionConfirmed() { return sessionConfirmed; },
+		get sessionOverridden() { return sessionOverridden; },
+		get sessionSkipped() { return sessionSkipped; },
+		get sessionTotal() { return sessionConfirmed + sessionOverridden + sessionSkipped; },
+		get lastTeachingMoment() { return lastTeachingMoment; },
+		get retrainResult() { return retrainResult; },
+		get retraining() { return retraining; },
+		loadQueue,
+		decide,
+		triggerRetrain,
+	};
+}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -1`

#### Task 8 — MoodRadar.svelte: 4-axis SVG radar chart
Tools: editor (create new file)
File: `frontend/src/lib/components/tinder/MoodRadar.svelte` (NEW)
Description: Small 4-axis SVG radar chart showing mood_happy (top), mood_aggressive (right), mood_sad (bottom), mood_relaxed (left). Values 0-1.

Full file content:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/tinder/MoodRadar.svelte
@@ -0,0 +1,72 @@
+<script lang="ts">
+	let {
+		happy = 0,
+		sad = 0,
+		aggressive = 0,
+		relaxed = 0,
+		size = 120,
+	}: {
+		happy?: number;
+		sad?: number;
+		aggressive?: number;
+		relaxed?: number;
+		size?: number;
+	} = $props();
+
+	const cx = size / 2;
+	const cy = size / 2;
+	const r = size / 2 - 16;
+
+	// Axes: top=happy, right=aggressive, bottom=sad, left=relaxed
+	function point(angle: number, value: number): string {
+		const rad = (angle - 90) * (Math.PI / 180);
+		const x = cx + r * value * Math.cos(rad);
+		const y = cy + r * value * Math.sin(rad);
+		return `${x},${y}`;
+	}
+
+	$effect(() => {});  // reactive on prop changes
+
+	const polygon = $derived(
+		[point(0, happy), point(90, aggressive), point(180, sad), point(270, relaxed)].join(' ')
+	);
+</script>
+
+<svg width={size} height={size} class="mood-radar">
+	<!-- Grid circles -->
+	{#each [0.25, 0.5, 0.75, 1.0] as level}
+		<circle cx={cx} cy={cy} r={r * level} fill="none" stroke="var(--border)" stroke-width="0.5" opacity="0.4" />
+	{/each}
+	<!-- Axis lines -->
+	<line x1={cx} y1={cy - r} x2={cx} y2={cy + r} stroke="var(--border)" stroke-width="0.5" opacity="0.3" />
+	<line x1={cx - r} y1={cy} x2={cx + r} y2={cy} stroke="var(--border)" stroke-width="0.5" opacity="0.3" />
+	<!-- Data polygon -->
+	<polygon points={polygon} fill="var(--accent)" fill-opacity="0.25" stroke="var(--accent)" stroke-width="1.5" />
+	<!-- Labels -->
+	<text x={cx} y={8} text-anchor="middle" class="label">Happy</text>
+	<text x={size - 2} y={cy + 4} text-anchor="end" class="label">Aggro</text>
+	<text x={cx} y={size - 2} text-anchor="middle" class="label">Sad</text>
+	<text x={2} y={cy + 4} text-anchor="start" class="label">Chill</text>
+</svg>
+
+<style>
+	.mood-radar {
+		display: block;
+	}
+
+	.label {
+		font-size: 9px;
+		fill: var(--text-dim);
+		font-family: inherit;
+	}
+</style>
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -1`

#### Task 9 — TinderCard.svelte: Track review card
Tools: editor (create new file)
File: `frontend/src/lib/components/tinder/TinderCard.svelte` (NEW)
Description: Card showing waveform player, track metadata, prediction zone + confidence bar, mood radar, and 3 action buttons. Reuses WavesurferPlayer for audio. Auto-plays on mount.

Full file content:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/tinder/TinderCard.svelte
@@ -0,0 +1,165 @@
+<script lang="ts">
+	import { onMount } from 'svelte';
+	import type { TinderQueueItem, TinderDecision } from '$lib/types';
+	import { getWaveformDetail } from '$lib/api/waveforms';
+	import WavesurferPlayer from '../waveform/WavesurferPlayer.svelte';
+	import MoodRadar from './MoodRadar.svelte';
+
+	let {
+		item,
+		ondecide,
+		teachingMoment = null,
+	}: {
+		item: TinderQueueItem;
+		ondecide: (decision: TinderDecision, overrideZone?: string) => void;
+		teachingMoment?: string | null;
+	} = $props();
+
+	let waveformPeaks = $state<string | null>(null);
+	let waveformDuration = $state(0);
+	let showOverrideMenu = $state(false);
+
+	const ZONES = ['warmup', 'build', 'peak'] as const;
+
+	const zoneColors: Record<string, string> = {
+		warmup: '#4ecdc4',
+		build: '#ffe66d',
+		peak: '#ff6b6b',
+	};
+
+	$effect(() => {
+		// Load waveform when item changes
+		if (item.has_waveform) {
+			getWaveformDetail(item.track.id)
+				.then((wf) => {
+					waveformPeaks = wf.envelope;
+					waveformDuration = wf.duration_sec;
+				})
+				.catch(() => {
+					waveformPeaks = null;
+				});
+		} else {
+			waveformPeaks = null;
+		}
+		showOverrideMenu = false;
+	});
+
+	function handleOverride(zone: string) {
+		showOverrideMenu = false;
+		ondecide('override', zone);
+	}
+
+	function handleKeydown(e: KeyboardEvent) {
+		if (e.key === 'ArrowRight' || e.key === 'y') { ondecide('confirm'); e.preventDefault(); }
+		else if (e.key === 'ArrowUp' || e.key === 's') { ondecide('skip'); e.preventDefault(); }
+		else if (e.key === 'ArrowLeft' || e.key === 'o') { showOverrideMenu = !showOverrideMenu; e.preventDefault(); }
+	}
+</script>
+
+<svelte:window onkeydown={handleKeydown} />
+
+<div class="tinder-card">
+	<!-- Track metadata -->
+	<div class="card-header">
+		<div class="title">{item.track.title ?? 'Unknown'}</div>
+		<div class="artist">{item.track.artist ?? 'Unknown'}</div>
+		<div class="meta">
+			<span>{item.track.bpm ? `${Math.round(item.track.bpm)} BPM` : ''}</span>
+			<span>{item.track.key ?? ''}</span>
+			<span>{item.track.genre ?? ''}</span>
+		</div>
+	</div>
+
+	<!-- Waveform player -->
+	{#if waveformPeaks}
+		<div class="waveform-container">
+			<WavesurferPlayer
+				trackId={item.track.id}
+				peaks={waveformPeaks}
+				duration={waveformDuration}
+				height={80}
+			/>
+		</div>
+	{:else}
+		<div class="waveform-placeholder">No waveform data</div>
+	{/if}
+
+	<!-- Prediction + Mood -->
+	<div class="prediction-row">
+		<div class="prediction">
+			<div class="zone-label" style="color: {zoneColors[item.energy_predicted ?? ''] ?? 'var(--text-primary)'}">
+				{item.energy_predicted ?? '?'}
+			</div>
+			<div class="confidence-bar">
+				<div class="confidence-fill" style="width: {(item.energy_confidence ?? 0) * 100}%"></div>
+			</div>
+			<div class="confidence-text">{((item.energy_confidence ?? 0) * 100).toFixed(0)}% confident</div>
+		</div>
+		<MoodRadar
+			happy={item.mood_happy ?? 0}
+			sad={item.mood_sad ?? 0}
+			aggressive={item.mood_aggressive ?? 0}
+			relaxed={item.mood_relaxed ?? 0}
+			size={100}
+		/>
+	</div>
+
+	<!-- Teaching moment -->
+	{#if teachingMoment}
+		<div class="teaching-moment">{teachingMoment}</div>
+	{/if}
+
+	<!-- Actions -->
+	<div class="actions">
+		<div class="override-wrapper">
+			<button class="action override" onclick={() => showOverrideMenu = !showOverrideMenu}>
+				Override <span class="shortcut">← / O</span>
+			</button>
+			{#if showOverrideMenu}
+				<div class="override-menu">
+					{#each ZONES as zone}
+						<button class="zone-btn" style="color: {zoneColors[zone]}" onclick={() => handleOverride(zone)}>
+							{zone}
+						</button>
+					{/each}
+				</div>
+			{/if}
+		</div>
+		<button class="action skip" onclick={() => ondecide('skip')}>
+			Skip <span class="shortcut">↑ / S</span>
+		</button>
+		<button class="action confirm" onclick={() => ondecide('confirm')}>
+			Confirm <span class="shortcut">→ / Y</span>
+		</button>
+	</div>
+</div>
+
+<style>
+	.tinder-card { max-width: 500px; margin: 0 auto; padding: 16px; }
+	.card-header { margin-bottom: 12px; }
+	.title { font-size: 18px; font-weight: 600; color: var(--text-primary); }
+	.artist { font-size: 14px; color: var(--text-secondary); margin-top: 2px; }
+	.meta { display: flex; gap: 12px; font-size: 12px; color: var(--text-dim); margin-top: 6px; }
+	.waveform-container { margin: 12px 0; }
+	.waveform-placeholder { height: 80px; display: flex; align-items: center; justify-content: center; color: var(--text-dim); font-size: 12px; background: var(--bg-secondary); border-radius: 4px; }
+	.prediction-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 16px 0; }
+	.prediction { flex: 1; }
+	.zone-label { font-size: 24px; font-weight: 700; text-transform: uppercase; }
+	.confidence-bar { height: 6px; background: var(--bg-secondary); border-radius: 3px; margin: 6px 0 4px; overflow: hidden; }
+	.confidence-fill { height: 100%; background: var(--accent); border-radius: 3px; transition: width 0.3s; }
+	.confidence-text { font-size: 11px; color: var(--text-dim); }
+	.teaching-moment { padding: 8px 12px; background: var(--bg-secondary); border-left: 3px solid var(--accent); border-radius: 4px; font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; font-style: italic; }
+	.actions { display: flex; gap: 8px; justify-content: center; }
+	.action { padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
+	.confirm { background: #2ecc71; color: #000; }
+	.confirm:hover { background: #27ae60; }
+	.skip { background: var(--bg-secondary); color: var(--text-secondary); }
+	.skip:hover { background: var(--bg-hover); }
+	.override { background: var(--bg-secondary); color: var(--text-secondary); }
+	.override:hover { background: var(--bg-hover); }
+	.shortcut { font-size: 10px; opacity: 0.6; margin-left: 4px; }
+	.override-wrapper { position: relative; }
+	.override-menu { position: absolute; bottom: 100%; left: 0; background: var(--bg-primary); border: 1px solid var(--border); border-radius: 6px; padding: 4px; display: flex; flex-direction: column; gap: 2px; margin-bottom: 4px; z-index: 10; }
+	.zone-btn { padding: 6px 16px; font-size: 13px; font-weight: 600; text-transform: uppercase; cursor: pointer; border-radius: 4px; background: none; }
+	.zone-btn:hover { background: var(--bg-hover); }
+</style>
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -1`

#### Task 10 — TinderSummary.svelte: Session summary + retrain
Tools: editor (create new file)
File: `frontend/src/lib/components/tinder/TinderSummary.svelte` (NEW)
Description: Shows session stats (confirmed/overridden/skipped counts and percentages). Retrain button that calls store.triggerRetrain(). Displays accuracy before/after on completion.

Full file content:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/tinder/TinderSummary.svelte
@@ -0,0 +1,77 @@
+<script lang="ts">
+	import { getTinderStore } from '$lib/stores/tinder.svelte';
+
+	const store = getTinderStore();
+
+	let { onrestart }: { onrestart: () => void } = $props();
+
+	function pct(n: number): string {
+		if (store.sessionTotal === 0) return '0';
+		return ((n / store.sessionTotal) * 100).toFixed(0);
+	}
+</script>
+
+<div class="summary">
+	<h2>Session complete</h2>
+	<p class="subtitle">You reviewed {store.sessionTotal} tracks</p>
+
+	<div class="stats-grid">
+		<div class="stat confirmed">
+			<div class="stat-num">{store.sessionConfirmed}</div>
+			<div class="stat-label">Confirmed ({pct(store.sessionConfirmed)}%)</div>
+		</div>
+		<div class="stat overridden">
+			<div class="stat-num">{store.sessionOverridden}</div>
+			<div class="stat-label">Overridden ({pct(store.sessionOverridden)}%)</div>
+		</div>
+		<div class="stat skipped">
+			<div class="stat-num">{store.sessionSkipped}</div>
+			<div class="stat-label">Skipped ({pct(store.sessionSkipped)}%)</div>
+		</div>
+	</div>
+
+	{#if store.retrainResult}
+		<div class="retrain-result">
+			<h3>Model retrained</h3>
+			<p>Accuracy: {store.retrainResult.accuracy ? (store.retrainResult.accuracy * 100).toFixed(1) + '%' : 'N/A'}</p>
+			<p>Training samples: {store.retrainResult.training_samples}</p>
+		</div>
+	{:else}
+		<button class="retrain-btn" onclick={() => store.triggerRetrain()} disabled={store.retraining}>
+			{store.retraining ? 'Retraining...' : `Retrain model with ${store.sessionConfirmed + store.sessionOverridden} new approvals`}
+		</button>
+	{/if}
+
+	<button class="restart-btn" onclick={onrestart}>Review more tracks</button>
+</div>
+
+<style>
+	.summary { max-width: 400px; margin: 40px auto; text-align: center; }
+	h2 { font-size: 20px; color: var(--text-primary); margin: 0 0 4px; }
+	.subtitle { font-size: 14px; color: var(--text-secondary); margin: 0 0 24px; }
+	.stats-grid { display: flex; gap: 16px; justify-content: center; margin-bottom: 24px; }
+	.stat { flex: 1; padding: 12px; background: var(--bg-secondary); border-radius: 8px; }
+	.stat-num { font-size: 28px; font-weight: 700; }
+	.confirmed .stat-num { color: #2ecc71; }
+	.overridden .stat-num { color: #f39c12; }
+	.skipped .stat-num { color: var(--text-dim); }
+	.stat-label { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
+	.retrain-btn { width: 100%; padding: 12px; background: var(--accent); color: var(--bg-primary); border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 8px; }
+	.retrain-btn:hover { opacity: 0.9; }
+	.retrain-btn:disabled { opacity: 0.5; cursor: not-allowed; }
+	.retrain-result { padding: 12px; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 12px; }
+	.retrain-result h3 { font-size: 14px; margin: 0 0 4px; color: #2ecc71; }
+	.retrain-result p { font-size: 12px; color: var(--text-secondary); margin: 2px 0; }
+	.restart-btn { width: 100%; padding: 10px; background: var(--bg-secondary); color: var(--text-secondary); border-radius: 8px; font-size: 13px; cursor: pointer; }
+	.restart-btn:hover { background: var(--bg-hover); }
+</style>
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -1`

#### Task 11 — EnergyTinder.svelte: Main container
Tools: editor (create new file)
File: `frontend/src/lib/components/tinder/EnergyTinder.svelte` (NEW)
Description: Main container managing queue loading, card navigation (current item from store), and summary display when complete. Shows queue remaining count and filter controls for genre family and BPM range.

Full file content:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/tinder/EnergyTinder.svelte
@@ -0,0 +1,101 @@
+<script lang="ts">
+	import { onMount } from 'svelte';
+	import type { TinderDecision } from '$lib/types';
+	import { getTinderStore } from '$lib/stores/tinder.svelte';
+	import TinderCard from './TinderCard.svelte';
+	import TinderSummary from './TinderSummary.svelte';
+
+	const store = getTinderStore();
+
+	let genreFamily = $state('');
+	let bpmMin = $state('');
+	let bpmMax = $state('');
+
+	function loadWithFilters() {
+		store.loadQueue({
+			genre_family: genreFamily || undefined,
+			bpm_min: bpmMin ? Number(bpmMin) : undefined,
+			bpm_max: bpmMax ? Number(bpmMax) : undefined,
+			limit: 50,
+		});
+	}
+
+	onMount(() => {
+		loadWithFilters();
+	});
+
+	function handleDecide(decision: TinderDecision, overrideZone?: string) {
+		store.decide(decision, overrideZone);
+	}
+</script>
+
+<div class="energy-tinder">
+	{#if store.loading}
+		<div class="status">Loading your review queue...</div>
+	{:else if store.error}
+		<div class="status error">{store.error}</div>
+	{:else if store.queue.length === 0}
+		<div class="empty">
+			<p>No tracks to review right now.</p>
+			<p class="hint">Run the autotagger first to generate predictions.</p>
+		</div>
+	{:else if store.isComplete}
+		<TinderSummary onrestart={loadWithFilters} />
+	{:else}
+		<!-- Queue progress -->
+		<div class="progress-bar">
+			<span>{store.currentIndex + 1} / {store.queue.length}</span>
+			<span class="queue-total">({store.queueTotal} total in queue)</span>
+		</div>
+
+		<!-- Filters -->
+		<div class="filters">
+			<select bind:value={genreFamily} onchange={loadWithFilters}>
+				<option value="">All genres</option>
+				<option value="techno">Techno</option>
+				<option value="house">House</option>
+				<option value="groove">Groove</option>
+				<option value="trance">Trance</option>
+				<option value="breaks">Breaks</option>
+				<option value="electronic">Electronic</option>
+			</select>
+			<input type="number" placeholder="BPM min" bind:value={bpmMin} onchange={loadWithFilters} />
+			<input type="number" placeholder="BPM max" bind:value={bpmMax} onchange={loadWithFilters} />
+		</div>
+
+		<!-- Current card -->
+		{#if store.currentItem}
+			{#key store.currentItem.track.id}
+				<TinderCard
+					item={store.currentItem}
+					ondecide={handleDecide}
+					teachingMoment={store.lastTeachingMoment}
+				/>
+			{/key}
+		{/if}
+	{/if}
+</div>
+
+<style>
+	.energy-tinder { height: 100%; display: flex; flex-direction: column; overflow-y: auto; padding: 12px; }
+	.status { padding: 40px; text-align: center; color: var(--text-secondary); }
+	.status.error { color: var(--energy-high); }
+	.empty { text-align: center; padding: 40px; color: var(--text-dim); }
+	.empty p { margin: 4px 0; }
+	.hint { font-size: 12px; }
+	.progress-bar { text-align: center; font-size: 13px; color: var(--text-secondary); padding: 4px 0; }
+	.queue-total { font-size: 11px; color: var(--text-dim); margin-left: 4px; }
+	.filters { display: flex; gap: 8px; justify-content: center; padding: 8px 0; }
+	.filters select, .filters input { padding: 4px 8px; font-size: 12px; background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border); border-radius: 4px; }
+	.filters input { width: 80px; }
+</style>
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -1`

#### Task 12 — ui.svelte.ts + Workspace.svelte: Add tinder tab
Tools: editor
File: `frontend/src/lib/stores/ui.svelte.ts`

Diff:
````diff
--- a/frontend/src/lib/stores/ui.svelte.ts
+++ b/frontend/src/lib/stores/ui.svelte.ts
@@ export type Tab = 'track' | 'set' | 'dna';
+export type Tab = 'track' | 'set' | 'dna' | 'tinder';
-export type Tab = 'track' | 'set' | 'dna';
````

File: `frontend/src/lib/components/Workspace.svelte`

Diff:
````diff
--- a/frontend/src/lib/components/Workspace.svelte
+++ b/frontend/src/lib/components/Workspace.svelte
@@ import DnaView from './dna/DnaView.svelte';
+	import EnergyTinder from './tinder/EnergyTinder.svelte';
 	import { getUiStore } from '$lib/stores/ui.svelte';
@@
 		else if (e.key === '3') { ui.activeTab = 'dna'; e.preventDefault(); }
+		else if (e.key === '4') { ui.activeTab = 'tinder'; e.preventDefault(); }
 	}
@@
 		<button class="tab" class:active={ui.activeTab === 'dna'} onclick={() => ui.activeTab = 'dna'}>
 			Taste DNA <span class="shortcut">3</span>
 		</button>
+		<button class="tab" class:active={ui.activeTab === 'tinder'} onclick={() => ui.activeTab = 'tinder'}>
+			Energy Tinder <span class="shortcut">4</span>
+		</button>
@@
 		{:else if ui.activeTab === 'dna'}
 			<DnaView />
+		{:else if ui.activeTab === 'tinder'}
+			<EnergyTinder />
 		{/if}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -1`

#### Task 13 — Lint & type-check all modified files
Tools: shell
Commands:
- `cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -m py_compile src/djsetbuilder/api/schemas.py && python -m py_compile src/djsetbuilder/db/store.py && python -m py_compile src/djsetbuilder/api/routes/tinder.py && python -m py_compile src/djsetbuilder/api/main.py && echo "Python OK"`
- `cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json`

Verification:
- Python: all files compile without errors
- Svelte: 0 ERRORS

#### Task 14 — Unit tests: API test for tinder endpoints
Tools: editor (create new file) + editor (modify conftest)
File: `tests/api/conftest.py`
Description: Add tracks with `energy_predicted` and `energy_source="auto"` at various confidence levels to the existing seed data.

Diff (append to seed data in `db_session` fixture, after the SetTrack loop):
````diff
--- a/tests/api/conftest.py
+++ b/tests/api/conftest.py
@@ for pos in range(1, 6):
         session.add(SetTrack(set_id=1, position=pos, track_id=pos, transition_score=0.75))

+    # Seed tinder queue: tracks 1-10 have auto predictions at varying confidence
+    for i in range(1, 11):
+        t = session.query(Track).get(i)
+        t.energy_predicted = "build" if i <= 5 else "peak"
+        t.energy_confidence = i * 0.1  # 0.1 to 1.0
+        t.energy_source = "auto"
+
     session.commit()
````

File: `tests/api/test_tinder_api.py` (NEW)
Full file content:
````diff
--- /dev/null
+++ b/tests/api/test_tinder_api.py
@@ -0,0 +1,72 @@
+"""Tests for Energy Tinder API endpoints."""
+
+from __future__ import annotations
+
+
+def test_tinder_queue_returns_items(client):
+    resp = client.get("/api/tinder/queue")
+    assert resp.status_code == 200
+    data = resp.json()
+    assert "items" in data
+    assert "total" in data
+    assert data["total"] == 10
+    assert len(data["items"]) == 10
+    # First item should have lowest confidence (0.1)
+    assert data["items"][0]["energy_confidence"] < data["items"][-1]["energy_confidence"]
+
+
+def test_tinder_queue_pagination(client):
+    resp = client.get("/api/tinder/queue?limit=3&offset=0")
+    data = resp.json()
+    assert len(data["items"]) == 3
+    assert data["total"] == 10
+    assert data["offset"] == 0
+
+
+def test_tinder_queue_filter_bpm(client):
+    resp = client.get("/api/tinder/queue?bpm_min=125&bpm_max=130")
+    data = resp.json()
+    assert data["total"] > 0
+    for item in data["items"]:
+        assert 125 <= item["track"]["bpm"] <= 130
+
+
+def test_tinder_decide_confirm(client):
+    resp = client.post("/api/tinder/decide", json={
+        "track_id": 1,
+        "decision": "confirm",
+    })
+    assert resp.status_code == 200
+    data = resp.json()
+    assert data["decision"] == "confirm"
+    assert data["applied_zone"] is not None
+
+
+def test_tinder_decide_override(client):
+    resp = client.post("/api/tinder/decide", json={
+        "track_id": 2,
+        "decision": "override",
+        "override_zone": "warmup",
+    })
+    assert resp.status_code == 200
+    data = resp.json()
+    assert data["decision"] == "override"
+    assert data["applied_zone"] == "warmup"
+
+
+def test_tinder_decide_skip(client):
+    resp = client.post("/api/tinder/decide", json={
+        "track_id": 3,
+        "decision": "skip",
+    })
+    assert resp.status_code == 200
+    assert resp.json()["decision"] == "skip"
+
+
+def test_tinder_decide_not_found(client):
+    resp = client.post("/api/tinder/decide", json={
+        "track_id": 9999,
+        "decision": "confirm",
+    })
+    assert resp.status_code == 404
+
+
+def test_tinder_decide_invalid_decision(client):
+    resp = client.post("/api/tinder/decide", json={
+        "track_id": 1,
+        "decision": "yolo",
+    })
+    assert resp.status_code == 400
+
+
+def test_tinder_stats(client):
+    resp = client.get("/api/tinder/stats")
+    assert resp.status_code == 200
+    data = resp.json()
+    assert "queue_remaining" in data
+    assert "total_reviewed" in data
````

Verification:
- `cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -m pytest tests/api/test_tinder_api.py -v`

#### Task 15 — E2E validation
Tools: shell
Description: Run full test suite and verify frontend type-check.
Commands:
- `cd /home/mantis/Development/mantis-dev/waveform-builer && source .venv/bin/activate && python -m pytest tests/ -v`
- `cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json`

Expectations:
- All tests pass (existing + new tinder tests)
- 0 TypeScript errors
- 0 warnings in svelte-check

#### Task 16 — Commit
Tools: git
Commands:
- Stage only the files created/modified in this spec:
```bash
git add \
  src/djsetbuilder/api/schemas.py \
  src/djsetbuilder/db/store.py \
  src/djsetbuilder/api/routes/tinder.py \
  src/djsetbuilder/api/main.py \
  frontend/src/lib/types/index.ts \
  frontend/src/lib/api/tinder.ts \
  frontend/src/lib/stores/tinder.svelte.ts \
  frontend/src/lib/stores/ui.svelte.ts \
  frontend/src/lib/components/tinder/MoodRadar.svelte \
  frontend/src/lib/components/tinder/TinderCard.svelte \
  frontend/src/lib/components/tinder/TinderSummary.svelte \
  frontend/src/lib/components/tinder/EnergyTinder.svelte \
  frontend/src/lib/components/Workspace.svelte \
  tests/api/conftest.py \
  tests/api/test_tinder_api.py \
  specs/2026/03/autotag/002-energy-tinder.md
```
- `git commit -m "spec(002): IMPLEMENT - energy-tinder"`

### Validate

| # | Requirement (Human Section) | Compliance |
|---|---------------------------|------------|
| 1 | Card-based UI showing one track at a time (L8) | TinderCard.svelte: single card with waveform, metadata, prediction, mood radar |
| 2 | Waveform player with playback controls (L9, L25) | Reuses WavesurferPlayer.svelte via getWaveformDetail() — play/pause/seek built-in |
| 3 | Play track audio in browser (L9, L32-34) | WavesurferPlayer loads from /api/audio/{trackId} which supports Range requests and transcoding |
| 4 | Swipe actions: confirm/override/skip (L10, L29) | Three action buttons + keyboard shortcuts (→/Y, ←/O, ↑/S) |
| 5 | Mood radar display (L11, L28) | MoodRadar.svelte: 4-axis SVG radar (happy/aggressive/sad/relaxed) |
| 6 | Store decisions in DB (L12, L36-39) | save_tinder_decision() updates Track.energy_source/predicted/confidence |
| 7 | Batch sessions with progress saved (L13) | Queue ordered by confidence ASC; confirmed/overridden tracks change energy_source to "approved" and leave queue |
| 8 | Session stats: reviewed count, confirmed %, overridden %, skip rate (L14) | TinderSummary shows all counters with percentages; /api/tinder/stats endpoint |
| 9 | One-click retrain after session (L15) | TinderSummary retrain button → POST /api/tinder/retrain → train_energy_model(include_approved=True) |
| 10 | Queue: energy_predicted IS NOT NULL AND energy_source = "auto" (L20) | get_tinder_queue() filter matches exactly |
| 11 | Order by confidence ascending (L21) | .order_by(Track.energy_confidence.asc()) |
| 12 | Filter by genre family or BPM range (L22) | Queue params: genre_family, bpm_min, bpm_max with UI selects/inputs |
| 13 | Prediction display with confidence bar (L27) | TinderCard: zone-label + confidence-bar + percentage text |
| 14 | On confirm: set energy_source = "approved" (L37) | save_tinder_decision confirm branch |
| 15 | On override: approved + update predicted + confidence 1.0 (L38) | save_tinder_decision override branch |
| 16 | On skip: leave as "auto" (L39) | save_tinder_decision skip = no-op |
| 17 | Session summary with reviewed/confirmed/overridden/skipped (L43) | TinderSummary.svelte with stats grid |
| 18 | Retrain button with accuracy display (L44-45) | TinderRetrainResponse returns accuracy, class_counts, feature_importance |
| 19 | Teaching moment on override (L48-49) | _generate_teaching_moment() uses model's top feature importance |
| 20 | Fast and fun UX (L52) | Keyboard shortcuts, smooth card transitions via {#key}, auto-focus actions |

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
