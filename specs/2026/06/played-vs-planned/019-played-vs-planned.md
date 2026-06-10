# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Close the feedback loop from the gig back into Kiku. A DJ plans a set in Kiku, plays the gig, and what actually happened on the dancefloor never comes back into the tool. Link an imported real-world set (M3U8 exported from Rekordbox history, via the spec 010 import path) to the Kiku set it was planned from, and generate a **deviation analysis with teaching moments**: where the DJ deviated from the plan (tracks cut, tracks added, order changes, energy-zone jumps), what the deviation suggests about the room and the DJ's instinct, and what it teaches about future planning. This is the core of the v1.1 "Play" milestone — Kiku stops being only a planner and starts being a mentor that watches the student perform. Revives spec 010 Phase 2/3 (set DNA + build-from-import groundwork).

## Mid-Level Objectives (MLO)
- ADD a link between a played (imported) set and the planned (Kiku) set it was based on — DB migration plus link/unlink API
- CREATE a deviation engine that diffs the played set against the planned set at track level (kept in place, moved, cut, added) and arc level (planned energy curve vs played energy sequence, BPM drift, key journey)
- GENERATE teaching moments for deviations in the Kiku mentor voice — never blame, frame deviations as the room speaking ("you jumped two energy zones at track 7 — the floor probably asked for it early; your warmups may be longer than your rooms want")
- EXPOSE comparison via API (`compare` endpoint returning the structured deviation report, cached like set analysis) and CLI (`kiku compare <played> <planned>` or equivalent)
- BUILD a frontend comparison view: side-by-side or interleaved timeline showing planned vs played, deviation badges, energy-curve overlay (planned target curve vs played actual), and the teaching moments panel
- SUGGEST candidate planned sets automatically when importing an M3U8 (track-overlap heuristic) so linking is one click, not a chore
- ENSURE unit tests for the deviation engine and teaching-moment generation, plus API tests for link + compare endpoints

## Details (DT)

### Existing groundwork to reuse
- Spec 010 import: `sets.source` ("m3u8"), `sets.source_ref`, `set_tracks.inferred_energy` / `inference_source`, `POST /api/sets/import/m3u8`, `kiku import-playlist`
- Spec 011 analysis: `analyze_set()` orchestrator, arc analysis (energy shape, key style, BPM style), teaching-moment engine, `sets.analysis_cache` JSON caching pattern
- Energy resolution: `resolve_energy()` cascading trust (approved > dir_energy > predicted); position-based inference for untagged tracks already exists on imported sets
- Track matching: imported sets already resolve to library track IDs, so the diff is ID-based, not fuzzy

### Deviation taxonomy (track level)
- **Kept**: same track, same relative position
- **Moved**: same track, different position (report displacement and what it did to the arc)
- **Cut**: planned but not played
- **Added**: played but not planned (the most interesting category — what did the DJ reach for under pressure?)

### Arc-level comparison
- Planned side has an explicit `energy_profile` target curve; played side has resolved/inferred energies per track — overlay both
- Detect energy-zone jumps in the played set relative to the planned curve (early peaks, skipped warmup, double peaks)
- BPM trajectory and key-journey style comparison using the spec 011 arc analyzers

### Constraints
- No new analysis dependencies; pure diff + existing scoring/analysis modules
- Cache the comparison result (same pattern as `analysis_cache`) and invalidate when either set changes
- Linking is optional and reversible — an imported set with no plan is still valid (freestyle sets are Phase 2 learning material, out of scope here)
- Voice per BRANDING.md: deviations are information, not mistakes; the DJ's ear may have been right and the copy must allow for that

### Testing
- Unit: deviation engine over synthetic set pairs (identical, fully reordered, cut/added mixes, energy-jump cases); teaching-moment selection per deviation type
- API: link/unlink endpoints, compare endpoint (200 with report, 404 unlinked, cache behavior)
- E2E (manual acceptance): import a real Rekordbox M3U8, link to the Kiku set it came from, view comparison in UI

## Behavior
You are a senior engineer on Kiku. Honor the 7 product principles (BRANDING.md) — especially "Show the Why" and "The Story Comes First" — in every user-facing string. Reuse the spec 010/011 machinery rather than building parallel paths.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Data model & migrations
- `Set` (src/kiku/db/models.py:131-144): already has `source` ("kiku"/"manual"/"m3u8"/"rb_playlist"), `source_ref`, `is_analyzed` (Integer 0/1), `analysis_cache` (Text JSON). New columns needed: `planned_set_id` (FK sets.id, nullable) + `comparison_cache` (Text JSON) + reuse the 0/1-flag pattern if needed.
- `SetTrack` (models.py:148-160): composite PK (set_id, position), `track_id`, `transition_score`, `inferred_energy`, `inference_source` ("interpolation"/"position"). Imported sets resolve to library track IDs, so the diff is **ID-based** — no fuzzy matching needed.
- Alembic pattern (alembic/versions/, 11 files): plain `op.add_column()` / `op.create_index()`, no batch_alter_table; linear `down_revision` chain. Most recent style: `4b88935a2dcc_add_import_columns_and_file_path_index.py`.

### Import flow (hook point for candidate suggestion)
- `import_playlist()` (src/kiku/import_playlist/service.py:111-217): dedups on `source_ref` (134-148), calls `match_tracks()` (66-108; exact_path → nocase_path → fuzzy_filename), creates Set with `source="m3u8"` (180-187), inserts SetTracks (190-195), returns `ImportResult` dataclass (24-34).
- Candidate-suggestion hook: after set creation (~line 187) compute track-overlap (Jaccard on track_id sets) against sets with `source="kiku"`, return ranked candidates in `ImportResult` → surfaces in `ImportResultResponse` (schemas.py:543-553) for one-click linking in UI.

### Analysis engine (reuse, don't rebuild)
- `analyze_set()` (src/kiku/analysis/set_analyzer.py:66-122) returns `SetAnalysisResult` {transitions: list[TransitionAnalysis], arc: ArcAnalysis, overall_score, set_patterns, analyzed_at}; writes `analysis_cache` + `is_analyzed=1` at 118-120.
- `ArcAnalysis` (40-48): `energy_curve: list[float]`, `energy_shape` ("flat"/"ramp-up"/"wind-down"/"peak-valley"/"roller-coaster"/"journey"), `key_journey`, `key_style`, `bpm_range`, `bpm_drift`, `bpm_style`, `genre_segments` — directly comparable per side.
- Teaching engine (src/kiku/analysis/teaching.py): `transition_teaching_moment()` (12-45, tiered ≥0.8 / 0.6-0.8 / <0.6) and `detect_set_patterns()` (152-215). New deviation moments follow the same module/style.
- Energy inference: `_infer_energy()` (set_analyzer.py:138-179) fills `inferred_energy` via neighbor interpolation or position ratio; `get_track_energy()` (src/kiku/energy.py:146-189) returns `TrackEnergy` {zone, numeric, source, confidence, label}; target curve via `EnergyProfile.target_energy_at()` (src/kiku/setbuilder/constraints.py:28-46); `zone_to_numeric()` (constraints.py:135-139).
- Cache invalidation precedent: add/remove/reorder track mutations in src/kiku/api/routes/sets.py:452-487 set `is_analyzed=0; analysis_cache=None` — `comparison_cache` must be cleared in the same places (on either linked set).

### API & CLI patterns
- Analyze endpoints as the model (routes/sets.py:182-212): `POST /{set_id}/analyze` (computes + caches), `GET /{set_id}/analysis` (404 if no cache); ValueError → 404 pattern. Schemas: `SetAnalysisResponse`/`ArcAnalysisResponse`/`TransitionAnalysisResponse` (schemas.py:559-587).
- CLI model: `analyze_set_cmd` (src/kiku/cli.py:621-684) — resolves set by ID or fuzzy name, prints summary + transition table + pattern bullets.

### Frontend
- `SetView.svelte` swaps `timeline-scroll` content between SetTimeline and TransitionDetail via `activeTransitionIndex` (lines 229-247, 354-380); analysis loads via `ui.pendingAnalysis` → `getSetAnalysis()` fallback → auto-analyze (179-217). A comparison mode slots into this same swap mechanism.
- `EnergyFlowChart.svelte` already renders dual datasets (actual colored-by-deviation + dashed target, lines 100-136) and parses both JSON and string `energy_profile` (33-70); extending with a third "played" curve = one more dataset entry.
- `SetTrackCard.svelte` title-row already hosts conditional badges (EnergyConflictBadge at 116-118) — deviation badges (kept/moved/cut/added) follow the same slot; BpmBadge's deviation color pattern is the style reference.
- `TransitionDetail.svelte` `.two-col` grid (222-227) is the proven side-by-side layout to reuse for planned|played columns.
- `ImportPlaylistDialog.svelte`: link-to-planned step fits after the force checkbox, before the result panel; `SetPicker.svelte` (props `{onselect, refreshSignal}`) is reusable as the planned-set selector.
- `ui.svelte.ts` fields (6-12) include `selectedSetId`, `timelineViewMode`, `pendingAnalysis`; comparison state can extend here.
- API client (src/lib/api/sets.ts): `analyzeSet`/`getSetAnalysis`/`importPlaylist` are the function templates; types in src/lib/types/index.ts (`SetAnalysis`, `ArcAnalysis`, `ImportResult` at 550-561).

### Test landscape
- Unit (tests/test_set_analysis.py:1-197): MagicMock-based track/set synthesis (`_mock_track()`), direct calls to private analyzers (`_classify_energy_shape`, `_detect_genre_segments`) — deviation engine tests follow this style.
- API (tests/api/conftest.py:18-102): `db_session` fixture seeds 20 tracks + 1 set with 5 SetTracks; `client` fixture overrides `get_db`. test_sets_api.py shows endpoint test pattern. Gap noted: planner/filler/reorder untested (out of scope here).

### Strategy

**Backend first, pure-diff core, UI last.**
1. **Migration**: add `planned_set_id` (nullable FK) + `comparison_cache` (Text) to sets — one Alembic revision, plain `op.add_column()`.
2. **Deviation engine** — new module `src/kiku/analysis/set_compare.py`: `compare_sets(db, played_id, planned_id) -> SetComparisonResult`. Track diff on track_id multisets → kept/moved (with displacement)/cut/added; arc diff reuses `analyze_set()` per side (`ArcAnalysis` vs `ArcAnalysis`) plus planned `energy_profile` target curve vs played resolved energies (via `get_track_energy()` + `inferred_energy` fallback). Zone-jump detection: consecutive played energies vs planned curve at same elapsed position, flag jumps ≥2 zone boundaries.
3. **Deviation teaching moments** — extend `teaching.py` with `deviation_teaching_moment(kind, context)` per taxonomy entry + `detect_deviation_patterns()` (e.g. "your adds cluster in the peak — you reach for energy under pressure"). Voice per BRANDING.md: room-speaking framing, never blame.
4. **API**: `PUT /api/sets/{id}/link` + `DELETE /api/sets/{id}/link` (set/clear `planned_set_id`), `POST /api/sets/{id}/compare` (compute + cache), `GET /api/sets/{id}/comparison` (cached, 404 if none) — mirrors analyze/analysis pair. Candidate suggestion added to `ImportResult` (Jaccard ≥ ~0.3, top 3).
5. **CLI**: `kiku compare <played> [<planned>]` (planned defaults to linked set) modeled on `analyze_set_cmd` output style.
6. **Frontend**: comparison mode in SetView (banner when a set is linked / candidates exist), reuse `.two-col` for planned|played timelines with deviation badges on SetTrackCard, third dataset on EnergyFlowChart, teaching-moments panel reusing analysis-bar styling; link step in ImportPlaylistDialog using SetPicker.
7. **Cache invalidation**: clear `comparison_cache` wherever `analysis_cache` is cleared, on both sides of the link (lookup by `planned_set_id` reverse FK).

**Testing strategy**
- Unit `tests/test_set_compare.py`: synthetic pairs — identical (all kept), full reorder (all moved + displacement signs), cut/added mixes, energy-jump fixtures; teaching-moment selection per deviation kind; candidate-suggestion Jaccard ranking.
- API `tests/api/test_compare_api.py`: link/unlink (200/404/self-link 400), compare (200 report, 404 unlinked), cache hit + invalidation on track mutation.
- E2E acceptance (manual): import real Rekordbox M3U8 → auto-suggested candidate → link → comparison view renders.
- Expected coverage: deviation engine + teaching fully unit-tested; all new endpoints covered; frontend type-checked via svelte-check (no frontend test harness exists yet).

## Plan

### Files
- alembic/versions/c9d0e1f2a3b4_add_planned_set_link_and_comparison_cache.py (NEW)
  - One revision: `planned_set_id` (Integer, nullable) + `comparison_cache` (Text) on `sets`. down_revision = `b8c9d0e1f2a3` (current head).
- src/kiku/db/models.py
  - L131-145 `Set`: add `planned_set_id` + `comparison_cache` columns.
- src/kiku/analysis/teaching.py
  - Append `deviation_teaching_moment()` + `detect_deviation_patterns()` after `detect_set_patterns()` (L215).
- src/kiku/analysis/set_compare.py (NEW)
  - `diff_tracks()`, `detect_energy_jumps()`, `_resample()`, `_planned_target_curve()`, `_played_energies()`, `compare_sets()` + dataclasses.
- src/kiku/api/schemas.py
  - L141-150 `SetDetailResponse`: add `source`, `planned_set_id`.
  - L537-553: add `PlannedSetCandidate`; `ImportResultResponse` += `planned_candidates`.
  - After `SetAnalysisResponse` (L588): `SetLinkRequest`, `TrackDeviationResponse`, `EnergyDeviationResponse`, `ArcComparisonResponse`, `SetComparisonResponse`.
- src/kiku/import_playlist/service.py
  - L6 `field` import; L24-34 `ImportResult` += `planned_candidates`; new `suggest_planned_sets()`; call after commit in `import_playlist()` (L197) and include in result (L204-217).
- src/kiku/api/routes/sets.py
  - L15-38 import block: `PlannedSetCandidate`, `SetComparisonResponse`, `SetLinkRequest`.
  - L169-179 import return: pass `planned_candidates`.
  - After `get_set_analysis` (L212): `_clear_comparison_caches()` helper + 4 endpoints (PUT/DELETE `/link`, POST `/compare`, GET `/comparison`).
  - L452-454 (add_track), L486-487 (remove_track), L505-508 (reorder): clear comparison caches.
  - L690-698 `set_detail`: pass `source` + `planned_set_id`.
- src/kiku/cli.py
  - Insert `compare_cmd` between `analyze_set_cmd` (ends L684) and `serve` (L687).
- frontend/src/lib/types/index.ts
  - L97-105 `SetDetail` += `source`, `planned_set_id`; L550-561 `ImportResult` += `planned_candidates`; new `PlannedSetCandidate`, `TrackDeviation`, `EnergyDeviation`, `ArcComparison`, `SetComparison`.
- frontend/src/lib/api/sets.ts
  - L1-15 type import; after `getSetAnalysis` (L257): `linkSet`, `unlinkSet`, `compareSet`, `getSetComparison`.
- frontend/src/lib/components/set/EnergyFlowChart.svelte
  - Props (L18-25) += `plannedCurve`; third dataset in `buildChartData()` (L122-136); legend + tooltip + reactive effect updates.
- frontend/src/lib/components/set/SetComparison.svelte (NEW)
  - Two-col planned|played lists with deviation badges, arc chips, teaching panel.
- frontend/src/lib/components/set/SetView.svelte
  - Imports (L1-9), state (L82-83), handlers (after L177), `loadSetData` (L179-217), controls (L262-272), chart prop (L322-327), timeline-scroll swap (L354-380), styles.
- frontend/src/lib/components/set/ImportPlaylistDialog.svelte
  - Candidate link step in success panel (after warnings, L177-183), `doLink()`, styles. Candidates come from the import response — no SetPicker reuse (SetPicker imports this dialog; reuse would be circular).
- tests/test_set_compare.py (NEW)
  - Pure-diff, energy-jump, teaching-moment, pattern, and Jaccard tests.
- tests/api/test_compare_api.py (NEW)
  - link/unlink (200/400/404), compare (200/404), comparison cache + invalidation (both sides).

### Tasks

#### Task 1 — Alembic migration: planned_set_id + comparison_cache
Tools: editor (Write new file), shell
File: `alembic/versions/c9d0e1f2a3b4_add_planned_set_link_and_comparison_cache.py` (NEW — exact full content):
````diff
--- /dev/null
+++ b/alembic/versions/c9d0e1f2a3b4_add_planned_set_link_and_comparison_cache.py
@@
+"""add planned set link and comparison cache
+
+Revision ID: c9d0e1f2a3b4
+Revises: b8c9d0e1f2a3
+Create Date: 2026-06-10
+
+"""
+from typing import Sequence, Union
+
+from alembic import op
+import sqlalchemy as sa
+
+
+# revision identifiers, used by Alembic.
+revision: str = 'c9d0e1f2a3b4'
+down_revision: Union[str, None] = 'b8c9d0e1f2a3'
+branch_labels: Union[str, Sequence[str], None] = None
+depends_on: Union[str, Sequence[str], None] = None
+
+
+def upgrade() -> None:
+    # Sets table: played -> planned link + cached comparison report
+    op.add_column('sets', sa.Column('planned_set_id', sa.Integer(), nullable=True))
+    op.add_column('sets', sa.Column('comparison_cache', sa.Text(), nullable=True))
+
+
+def downgrade() -> None:
+    op.drop_column('sets', 'comparison_cache')
+    op.drop_column('sets', 'planned_set_id')
````
Notes: plain `op.add_column()` (no batch_alter_table) per repo pattern (`4b88935a2dcc_*.py`). SQLite does not enforce the FK on added columns; the FK lives in the model (Task 2) like `set_tracks.track_id`.

Verification:
- `source .venv/bin/activate && alembic upgrade head` → no error.
- `source .venv/bin/activate && python -c "import sqlite3; c=sqlite3.connect('data/dj_library.db'); print([r[1] for r in c.execute('PRAGMA table_info(sets)')])"` → includes `planned_set_id`, `comparison_cache`.

#### Task 2 — models.py: Set columns
Tools: editor
Diff:
````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@
     source = Column(String)  # "kiku", "manual", "m3u8", "rb_playlist"
     source_ref = Column(Text)  # Original filename or playlist name
     is_analyzed = Column(Integer, default=0)  # Whether analysis has been run
     analysis_cache = Column(Text)  # JSON blob for cached analysis (Phase 2)
+    planned_set_id = Column(Integer, ForeignKey("sets.id"), nullable=True)  # Played set -> the plan it came from
+    comparison_cache = Column(Text)  # JSON blob for cached played-vs-planned comparison
 
     tracks = relationship("SetTrack", back_populates="set_", cascade="all, delete-orphan")
````
Verification:
- `source .venv/bin/activate && python -c "from kiku.db.models import Set; print(Set.planned_set_id, Set.comparison_cache)"`.

#### Task 3 — teaching.py: deviation teaching moments + patterns
Tools: editor
Append at END of `src/kiku/analysis/teaching.py` (after `detect_set_patterns`, L215). Voice per BRANDING.md: deviations are the room speaking, never mistakes.
Diff:
````diff
--- a/src/kiku/analysis/teaching.py
+++ b/src/kiku/analysis/teaching.py
@@
         patterns.append(
             f"Your transitions could use work on {dim_labels[weakest_dim]} "
             f"(averaging {avg[weakest_dim]:.2f}). Focus here to level up."
         )
 
     return patterns
+
+
+# ── Deviation Teaching (played vs planned) ──────────────────────────────
+
+
+def deviation_teaching_moment(
+    kind: str,
+    *,
+    title: str | None = None,
+    displacement: int | None = None,
+    delta: float | None = None,
+    position: int | None = None,
+) -> str:
+    """Explain a played-vs-planned deviation — the room speaking, never a mistake."""
+    name = title or "This track"
+
+    if kind == "kept":
+        return f"{name} landed right where you planned it — the room agreed."
+
+    if kind == "moved":
+        d = displacement or 0
+        if d < 0:
+            return (
+                f"You pulled {name} {abs(d)} slot{'s' if abs(d) != 1 else ''} earlier — "
+                "the floor probably asked for it sooner."
+            )
+        return (
+            f"You held {name} back {d} slot{'s' if d != 1 else ''} — "
+            "you waited until the room was ready for it."
+        )
+
+    if kind == "cut":
+        return f"{name} stayed in the bag — the night told you it didn't fit."
+
+    if kind == "added":
+        return f"{name} wasn't in the plan — your instinct reached for what the room needed."
+
+    if kind == "energy_jump":
+        pos_label = f"track {position + 1}" if position is not None else "this point"
+        if delta is not None and delta > 0:
+            return (
+                f"You ran {delta:+.2f} above the planned curve at {pos_label} — "
+                "the floor probably asked for it early."
+            )
+        return (
+            f"You eased {abs(delta or 0):.2f} below the planned curve at {pos_label} — "
+            "reading the room beats following the script."
+        )
+
+    return "The plan and the night disagreed here — listen to what the room was saying."
+
+
+def detect_deviation_patterns(
+    deviations: list[tuple[str, int | None]],
+    energy_deltas: list[float],
+    played_count: int,
+) -> list[str]:
+    """Detect set-level deviation patterns across a played-vs-planned comparison.
+
+    `deviations` is (kind, played_position) per track entry; `energy_deltas`
+    is played minus planned energy per played position.
+    """
+    patterns: list[str] = []
+    if not deviations:
+        return patterns
+
+    kinds = [k for k, _ in deviations]
+    planned_total = kinds.count("kept") + kinds.count("moved") + kinds.count("cut")
+
+    # Played the plan straight through
+    if all(k == "kept" for k in kinds):
+        patterns.append(
+            "You played it exactly as planned — either discipline, "
+            "or a plan that already knew the room."
+        )
+        return patterns
+
+    # Adds clustering late — reaching for energy under pressure
+    add_positions = [p for k, p in deviations if k == "added" and p is not None]
+    if played_count >= 3 and len(add_positions) >= 2:
+        late = sum(1 for p in add_positions if p >= played_count * 2 / 3)
+        if late / len(add_positions) > 0.6:
+            patterns.append(
+                "Your adds cluster late in the set — under pressure you reach "
+                "for energy. Stock your peak shelf deeper next time."
+            )
+
+    # Heavy cuts — plans longer than the room wants
+    if planned_total > 0 and kinds.count("cut") / planned_total > 0.3:
+        patterns.append(
+            "You cut over a third of the plan — your plans may be longer "
+            "than your rooms want."
+        )
+
+    # Running hotter/cooler than the plan
+    if energy_deltas:
+        avg_delta = sum(energy_deltas) / len(energy_deltas)
+        if avg_delta > 0.15:
+            patterns.append(
+                "You ran hotter than the plan all night — your warmups may be "
+                "longer than your rooms want."
+            )
+        elif avg_delta < -0.15:
+            patterns.append(
+                "You ran cooler than the plan — the room wanted depth, not lift. "
+                "Trust that read."
+            )
+
+    return patterns
````
Verification:
- `source .venv/bin/activate && python -c "from kiku.analysis.teaching import deviation_teaching_moment as m, detect_deviation_patterns as p; print(m('added', title='X')); print(p([('kept',0)],[0.0],1))"`.

#### Task 4 — set_compare.py: deviation engine (NEW module)
Tools: editor (Write new file)
File: `src/kiku/analysis/set_compare.py` (exact full content):
````diff
--- /dev/null
+++ b/src/kiku/analysis/set_compare.py
@@
+"""Played-vs-planned comparison engine — diffs a played set against the plan it came from."""
+
+from __future__ import annotations
+
+import json
+from collections import defaultdict
+from dataclasses import asdict, dataclass
+from datetime import datetime
+
+from sqlalchemy.orm import Session
+
+from kiku.analysis.set_analyzer import analyze_set
+from kiku.analysis.teaching import detect_deviation_patterns, deviation_teaching_moment
+from kiku.db.models import Set
+from kiku.energy import get_track_energy
+from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string
+
+# A jump of roughly two energy zones on the 0-1 scale
+ENERGY_JUMP_THRESHOLD = 0.3
+
+
+@dataclass
+class TrackDeviation:
+    kind: str  # "kept" | "moved" | "cut" | "added"
+    track_id: int
+    title: str | None
+    artist: str | None
+    planned_position: int | None
+    played_position: int | None
+    displacement: int | None  # played_position - planned_position (moved only)
+    teaching_moment: str
+
+
+@dataclass
+class EnergyDeviation:
+    position: int
+    track_id: int
+    planned_energy: float
+    played_energy: float
+    delta: float
+    teaching_moment: str
+
+
+@dataclass
+class ArcComparison:
+    planned_shape: str
+    played_shape: str
+    planned_key_style: str
+    played_key_style: str
+    planned_bpm_style: str
+    played_bpm_style: str
+    planned_bpm_range: list[float]
+    played_bpm_range: list[float]
+    bpm_drift_delta: float
+    planned_curve: list[float]  # target energy sampled at each played position
+    played_curve: list[float]
+
+
+@dataclass
+class SetComparisonResult:
+    played_set_id: int
+    planned_set_id: int
+    played_name: str | None
+    planned_name: str | None
+    kept_count: int
+    moved_count: int
+    cut_count: int
+    added_count: int
+    track_deviations: list[TrackDeviation]
+    energy_deviations: list[EnergyDeviation]
+    arc: ArcComparison
+    deviation_patterns: list[str]
+    compared_at: str
+
+
+# ── Pure diff helpers (unit-testable without a DB) ─────────────────────
+
+
+def diff_tracks(planned_ids: list[int], played_ids: list[int]) -> list[dict]:
+    """Diff two track-id sequences into kept/moved/cut/added entries.
+
+    Handles duplicate track ids as multisets: each played occurrence consumes
+    the earliest unconsumed planned occurrence of the same id.
+    """
+    planned_pos: dict[int, list[int]] = defaultdict(list)
+    for pos, tid in enumerate(planned_ids):
+        planned_pos[tid].append(pos)
+
+    entries: list[dict] = []
+    for pos, tid in enumerate(played_ids):
+        if planned_pos.get(tid):
+            p = planned_pos[tid].pop(0)
+            if p == pos:
+                entries.append({
+                    "kind": "kept", "track_id": tid,
+                    "planned_position": p, "played_position": pos, "displacement": None,
+                })
+            else:
+                entries.append({
+                    "kind": "moved", "track_id": tid,
+                    "planned_position": p, "played_position": pos, "displacement": pos - p,
+                })
+        else:
+            entries.append({
+                "kind": "added", "track_id": tid,
+                "planned_position": None, "played_position": pos, "displacement": None,
+            })
+
+    for tid, positions in planned_pos.items():
+        for p in positions:
+            entries.append({
+                "kind": "cut", "track_id": tid,
+                "planned_position": p, "played_position": None, "displacement": None,
+            })
+
+    # Stable order: played order first, then cuts by planned position
+    entries.sort(key=lambda e: (
+        e["played_position"] is None,
+        e["played_position"] if e["played_position"] is not None else e["planned_position"],
+    ))
+    return entries
+
+
+def detect_energy_jumps(
+    planned_curve: list[float],
+    played_curve: list[float],
+    threshold: float = ENERGY_JUMP_THRESHOLD,
+) -> list[tuple[int, float]]:
+    """Flag positions where played energy deviates from the planned curve by >= threshold.
+
+    Returns (position, delta) tuples with delta = played - planned.
+    """
+    jumps: list[tuple[int, float]] = []
+    for i, (planned, played) in enumerate(zip(planned_curve, played_curve)):
+        delta = round(played - planned, 3)
+        if abs(delta) >= threshold:
+            jumps.append((i, delta))
+    return jumps
+
+
+def _resample(curve: list[float], count: int) -> list[float]:
+    """Linearly resample a curve to `count` points."""
+    if not curve or count <= 0:
+        return [0.5] * max(count, 0)
+    if len(curve) == 1:
+        return [curve[0]] * count
+    out: list[float] = []
+    for i in range(count):
+        t = (i / max(count - 1, 1)) * (len(curve) - 1)
+        lo = int(t)
+        hi = min(lo + 1, len(curve) - 1)
+        frac = t - lo
+        out.append(round(curve[lo] * (1 - frac) + curve[hi] * frac, 3))
+    return out
+
+
+# ── Core comparison ─────────────────────────────────────────────────────
+
+
+def _planned_target_curve(planned: Set, planned_arc_curve: list[float], count: int) -> list[float]:
+    """Target energy at each played position: explicit profile first, planned arc as fallback."""
+    if planned.energy_profile:
+        try:
+            try:
+                profile = parse_energy_json(planned.energy_profile)
+            except (json.JSONDecodeError, KeyError, TypeError):
+                profile = parse_energy_string(planned.energy_profile)
+            total = profile.total_duration_min or planned.duration_min or 120
+            return [
+                round(profile.target_energy_at((i / max(count - 1, 1)) * total), 3)
+                for i in range(count)
+            ]
+        except (ValueError, KeyError, TypeError):
+            pass
+    return _resample(planned_arc_curve, count)
+
+
+def _played_energies(set_tracks) -> list[float]:
+    """Resolved energy per played track: track cascade first, inferred fallback, neutral last."""
+    energies: list[float] = []
+    for st in set_tracks:
+        if st.track is not None:
+            te = get_track_energy(st.track)
+            if te.numeric is not None:
+                energies.append(round(te.numeric, 3))
+                continue
+        if st.inferred_energy is not None:
+            energies.append(round(st.inferred_energy, 3))
+        else:
+            energies.append(0.5)
+    return energies
+
+
+def compare_sets(db: Session, played_id: int, planned_id: int) -> SetComparisonResult:
+    """Compare a played set against its plan and cache the result on the played set."""
+    played = db.get(Set, played_id)
+    if not played:
+        raise ValueError(f"Set {played_id} not found")
+    planned = db.get(Set, planned_id)
+    if not planned:
+        raise ValueError(f"Set {planned_id} not found")
+    if played_id == planned_id:
+        raise ValueError("A set can't be compared against itself")
+
+    # Arc analysis per side (also infers energy for untagged tracks)
+    played_analysis = analyze_set(db, played_id)
+    planned_analysis = analyze_set(db, planned_id)
+
+    played_sts = sorted(played.tracks, key=lambda st: st.position)
+    planned_sts = sorted(planned.tracks, key=lambda st: st.position)
+
+    # Track-level diff (ID-based — imported sets resolve to library track ids)
+    planned_ids = [st.track_id for st in planned_sts]
+    played_ids = [st.track_id for st in played_sts]
+    raw_entries = diff_tracks(planned_ids, played_ids)
+
+    track_lookup = {st.track_id: st.track for st in planned_sts + played_sts if st.track}
+    deviations: list[TrackDeviation] = []
+    for e in raw_entries:
+        t = track_lookup.get(e["track_id"])
+        deviations.append(TrackDeviation(
+            kind=e["kind"],
+            track_id=e["track_id"],
+            title=t.title if t else None,
+            artist=t.artist if t else None,
+            planned_position=e["planned_position"],
+            played_position=e["played_position"],
+            displacement=e["displacement"],
+            teaching_moment=deviation_teaching_moment(
+                e["kind"],
+                title=t.title if t else None,
+                displacement=e["displacement"],
+            ),
+        ))
+
+    # Energy: planned target curve sampled at played positions vs played resolved energies
+    played_curve = _played_energies(played_sts)
+    planned_curve = _planned_target_curve(
+        planned, planned_analysis.arc.energy_curve, len(played_sts)
+    )
+
+    energy_deviations: list[EnergyDeviation] = []
+    for pos, delta in detect_energy_jumps(planned_curve, played_curve):
+        energy_deviations.append(EnergyDeviation(
+            position=pos,
+            track_id=played_sts[pos].track_id,
+            planned_energy=planned_curve[pos],
+            played_energy=played_curve[pos],
+            delta=delta,
+            teaching_moment=deviation_teaching_moment(
+                "energy_jump", delta=delta, position=pos,
+            ),
+        ))
+
+    arc = ArcComparison(
+        planned_shape=planned_analysis.arc.energy_shape,
+        played_shape=played_analysis.arc.energy_shape,
+        planned_key_style=planned_analysis.arc.key_style,
+        played_key_style=played_analysis.arc.key_style,
+        planned_bpm_style=planned_analysis.arc.bpm_style,
+        played_bpm_style=played_analysis.arc.bpm_style,
+        planned_bpm_range=list(planned_analysis.arc.bpm_range),
+        played_bpm_range=list(played_analysis.arc.bpm_range),
+        bpm_drift_delta=round(played_analysis.arc.bpm_drift - planned_analysis.arc.bpm_drift, 1),
+        planned_curve=planned_curve,
+        played_curve=played_curve,
+    )
+
+    kinds = [d.kind for d in deviations]
+    patterns = detect_deviation_patterns(
+        [(d.kind, d.played_position) for d in deviations],
+        [round(p - q, 3) for p, q in zip(played_curve, planned_curve)],
+        len(played_sts),
+    )
+
+    result = SetComparisonResult(
+        played_set_id=played_id,
+        planned_set_id=planned_id,
+        played_name=played.name,
+        planned_name=planned.name,
+        kept_count=kinds.count("kept"),
+        moved_count=kinds.count("moved"),
+        cut_count=kinds.count("cut"),
+        added_count=kinds.count("added"),
+        track_deviations=deviations,
+        energy_deviations=energy_deviations,
+        arc=arc,
+        deviation_patterns=patterns,
+        compared_at=datetime.now().isoformat(),
+    )
+
+    # Cache on the played set (same pattern as analysis_cache)
+    played.comparison_cache = json.dumps(asdict(result))
+    db.commit()
+
+    return result
````
Verification:
- `source .venv/bin/activate && python -c "from kiku.analysis.set_compare import diff_tracks; print(diff_tracks([1,2,3],[3,1,2]))"` → three `moved` entries with displacements −2, +1, +1.

#### Task 5 — schemas.py: comparison + candidate + link models
Tools: editor
Three diffs in `src/kiku/api/schemas.py`.

Diff 1 — `SetDetailResponse` (L141):
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
 class SetDetailResponse(BaseModel):
     id: int
     name: str | None = None
     created_at: str | None = None
     duration_min: int | None = None
     energy_profile: str | None = None
     genre_filter: str | None = None
+    source: str | None = None
+    planned_set_id: int | None = None
     tracks: list[SetTrackResponse] = []
````

Diff 2 — candidate model + `ImportResultResponse` field (L537-553):
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
 class UnmatchedTrack(BaseModel):
     path: str
     title: str | None = None
     line: int
 
 
+class PlannedSetCandidate(BaseModel):
+    set_id: int
+    name: str | None = None
+    overlap: float  # Jaccard overlap (0-1) on track ids
+    shared_tracks: int
+
+
 class ImportResultResponse(BaseModel):
     set_id: int
     name: str
     source: str
     total_tracks: int
     matched_count: int
     unmatched_count: int
     unmatched_paths: list[UnmatchedTrack] = []
     match_methods: dict[str, int] = {}
     warnings: list[str] = []
     duplicate_set_id: int | None = None
+    planned_candidates: list[PlannedSetCandidate] = []
````

Diff 3 — comparison models after `SetAnalysisResponse` (L588, before `# ── SoundCloud models ──`):
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
 class SetAnalysisResponse(BaseModel):
     set_id: int
     track_count: int
     transition_count: int
     transitions: list[TransitionAnalysisResponse]
     arc: ArcAnalysisResponse
     overall_score: float
     set_patterns: list[str]
     analyzed_at: str
 
 
+# ── Set Comparison models (played vs planned) ──
+
+
+class SetLinkRequest(BaseModel):
+    planned_set_id: int
+
+
+class TrackDeviationResponse(BaseModel):
+    kind: str  # "kept" | "moved" | "cut" | "added"
+    track_id: int
+    title: str | None = None
+    artist: str | None = None
+    planned_position: int | None = None
+    played_position: int | None = None
+    displacement: int | None = None
+    teaching_moment: str
+
+
+class EnergyDeviationResponse(BaseModel):
+    position: int
+    track_id: int
+    planned_energy: float
+    played_energy: float
+    delta: float
+    teaching_moment: str
+
+
+class ArcComparisonResponse(BaseModel):
+    planned_shape: str
+    played_shape: str
+    planned_key_style: str
+    played_key_style: str
+    planned_bpm_style: str
+    played_bpm_style: str
+    planned_bpm_range: list[float]
+    played_bpm_range: list[float]
+    bpm_drift_delta: float
+    planned_curve: list[float]
+    played_curve: list[float]
+
+
+class SetComparisonResponse(BaseModel):
+    played_set_id: int
+    planned_set_id: int
+    played_name: str | None = None
+    planned_name: str | None = None
+    kept_count: int
+    moved_count: int
+    cut_count: int
+    added_count: int
+    track_deviations: list[TrackDeviationResponse]
+    energy_deviations: list[EnergyDeviationResponse]
+    arc: ArcComparisonResponse
+    deviation_patterns: list[str]
+    compared_at: str
+
+
 # ── SoundCloud models ──
````
Verification:
- `source .venv/bin/activate && python -c "from kiku.api.schemas import SetComparisonResponse, SetLinkRequest, PlannedSetCandidate; print('ok')"`.

#### Task 6 — import service: planned-set candidate suggestion
Tools: editor
Three diffs in `src/kiku/import_playlist/service.py`.

Diff 1 — imports + `ImportResult` field:
````diff
--- a/src/kiku/import_playlist/service.py
+++ b/src/kiku/import_playlist/service.py
@@
 import unicodedata
-from dataclasses import dataclass
+from dataclasses import dataclass, field
 from pathlib import PurePosixPath
@@
 @dataclass
 class ImportResult:
     set_id: int
     name: str
     source: str
     total_tracks: int
     matched_count: int
     unmatched_count: int
     unmatched: list[dict]  # [{path, title, line}]
     match_methods: dict[str, int]
     warnings: list[str]
     duplicate_set_id: int | None = None  # Set if source_ref already exists
+    planned_candidates: list[dict] = field(default_factory=list)  # [{set_id, name, overlap, shared_tracks}]
````

Diff 2 — new function after `match_tracks()` (L108), before `import_playlist()`:
````diff
--- a/src/kiku/import_playlist/service.py
+++ b/src/kiku/import_playlist/service.py
@@
         if matched:
             results.append(TrackMatchResult(mt, matched, "fuzzy_filename"))
         else:
             results.append(TrackMatchResult(mt, None, "unmatched"))
 
     return results
 
 
+def suggest_planned_sets(
+    session: Session,
+    track_ids: list[int],
+    *,
+    exclude_set_id: int | None = None,
+    threshold: float = 0.3,
+    top_n: int = 3,
+) -> list[dict]:
+    """Rank Kiku-built sets by Jaccard track overlap with an imported set.
+
+    Returns up to `top_n` candidates with overlap >= threshold:
+    [{"set_id", "name", "overlap", "shared_tracks"}, ...]
+    """
+    played = set(track_ids)
+    if not played:
+        return []
+
+    q = session.query(Set).filter(Set.source == "kiku")
+    if exclude_set_id is not None:
+        q = q.filter(Set.id != exclude_set_id)
+
+    candidates: list[dict] = []
+    for s in q.all():
+        planned = {st.track_id for st in s.tracks}
+        if not planned:
+            continue
+        shared = len(played & planned)
+        union = len(played | planned)
+        overlap = shared / union if union else 0.0
+        if overlap >= threshold:
+            candidates.append({
+                "set_id": s.id,
+                "name": s.name,
+                "overlap": round(overlap, 3),
+                "shared_tracks": shared,
+            })
+
+    candidates.sort(key=lambda c: c["overlap"], reverse=True)
+    return candidates[:top_n]
+
+
 def import_playlist(
````

Diff 3 — call it inside `import_playlist()` after commit (L197) and return it:
````diff
--- a/src/kiku/import_playlist/service.py
+++ b/src/kiku/import_playlist/service.py
@@
     session.commit()
 
+    # Suggest candidate planned sets (Jaccard overlap on track ids)
+    candidates = suggest_planned_sets(
+        session,
+        [m.matched_track.id for m in matched],
+        exclude_set_id=new_set.id,
+    )
+
     # Count match methods
     method_counts: dict[str, int] = {}
     for m in matched:
         method_counts[m.match_method] = method_counts.get(m.match_method, 0) + 1
@@
         match_methods=method_counts,
         warnings=parse_result.warnings,
+        planned_candidates=candidates,
     )
````
Verification:
- `source .venv/bin/activate && python -c "from kiku.import_playlist.service import suggest_planned_sets, ImportResult; print(ImportResult.__dataclass_fields__['planned_candidates'])"`.

#### Task 7 — routes/sets.py: link + compare endpoints
Tools: editor
Two diffs in `src/kiku/api/routes/sets.py`.

Diff 1 — schema imports (L15-38 block):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
     CueCreateRequest,
     CueResponse,
     ImportResultResponse,
+    PlannedSetCandidate,
     SetAnalysisResponse,
+    SetComparisonResponse,
+    SetLinkRequest,
     ReplaceTrackRequest,
````

Diff 2 — helper + 4 endpoints inserted after `get_set_analysis` (ends `return json.loads(s.analysis_cache)`, L212) and before `@router.post("/build")`:
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
     return json.loads(s.analysis_cache)
 
 
+# ── Played vs Planned (link + compare) ──
+
+
+def _clear_comparison_caches(db: Session, set_: Set) -> None:
+    """Clear comparison caches touching this set — its own and any played set linked to it."""
+    set_.comparison_cache = None
+    for linked in db.query(Set).filter(Set.planned_set_id == set_.id).all():
+        linked.comparison_cache = None
+
+
+@router.put("/{set_id}/link")
+def link_set(set_id: int, body: SetLinkRequest, db: Session = Depends(get_db)):
+    """Link a played (imported) set to the planned Kiku set it was based on."""
+    s = db.get(Set, set_id)
+    if not s:
+        raise HTTPException(status_code=404, detail="Set not found")
+    if body.planned_set_id == set_id:
+        raise HTTPException(
+            status_code=400,
+            detail="A set can't be its own plan — pick the set you built in Kiku",
+        )
+    planned = db.get(Set, body.planned_set_id)
+    if not planned:
+        raise HTTPException(status_code=404, detail="Planned set not found")
+
+    s.planned_set_id = body.planned_set_id
+    s.comparison_cache = None
+    db.commit()
+    return {"set_id": set_id, "planned_set_id": body.planned_set_id}
+
+
+@router.delete("/{set_id}/link", status_code=204)
+def unlink_set(set_id: int, db: Session = Depends(get_db)):
+    """Remove the planned-set link. Linking is optional and reversible."""
+    s = db.get(Set, set_id)
+    if not s:
+        raise HTTPException(status_code=404, detail="Set not found")
+    s.planned_set_id = None
+    s.comparison_cache = None
+    db.commit()
+    return Response(status_code=204)
+
+
+@router.post("/{set_id}/compare", response_model=SetComparisonResponse)
+def compare_set_endpoint(set_id: int, db: Session = Depends(get_db)):
+    """Compare a played set against its linked plan. Computes and caches the deviation report."""
+    from dataclasses import asdict
+
+    from kiku.analysis.set_compare import compare_sets
+
+    s = db.get(Set, set_id)
+    if not s:
+        raise HTTPException(status_code=404, detail="Set not found")
+    if not s.planned_set_id:
+        raise HTTPException(
+            status_code=404,
+            detail="No planned set linked — link one first with PUT /link",
+        )
+
+    try:
+        result = compare_sets(db, set_id, s.planned_set_id)
+    except ValueError as e:
+        raise HTTPException(status_code=404, detail=str(e))
+
+    return asdict(result)
+
+
+@router.get("/{set_id}/comparison", response_model=SetComparisonResponse)
+def get_set_comparison(set_id: int, db: Session = Depends(get_db)):
+    """Get the cached played-vs-planned comparison. 404 if not compared yet."""
+    s = db.get(Set, set_id)
+    if not s:
+        raise HTTPException(status_code=404, detail="Set not found")
+    if not s.comparison_cache:
+        raise HTTPException(
+            status_code=404,
+            detail="Set hasn't been compared yet. Use POST /compare first.",
+        )
+    return json.loads(s.comparison_cache)
+
+
 @router.post("/build")
````
Verification:
- `source .venv/bin/activate && python -c "from kiku.api.main import create_app; app=create_app(); paths=[r.path for r in app.routes]; assert '/api/sets/{set_id}/link' in paths and '/api/sets/{set_id}/compare' in paths and '/api/sets/{set_id}/comparison' in paths; print('ok')"`.

#### Task 8 — routes/sets.py: cache invalidation + candidates + set_detail
Tools: editor
Four diffs in `src/kiku/api/routes/sets.py`.

Diff 1 — import endpoint passes candidates (final return, L169-179):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
         unmatched_paths=[UnmatchedTrack(**u) for u in result.unmatched],
         match_methods=result.match_methods,
         warnings=result.warnings,
+        planned_candidates=[PlannedSetCandidate(**c) for c in result.planned_candidates],
     )
````

Diff 2 — `add_track` invalidation (L452-454):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
     # Invalidate analysis cache
     set_.is_analyzed = 0
     set_.analysis_cache = None
+    _clear_comparison_caches(db, set_)
 
     db.commit()
     db.refresh(set_)
````

Diff 3 — `remove_track` invalidation (L486-488):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
             elif i == 0:
                 st.transition_score = None
         set_.is_analyzed = 0
         set_.analysis_cache = None
+        _clear_comparison_caches(db, set_)
         db.commit()
     return Response(status_code=204)
````

Diff 4 — `reorder_tracks` invalidation (L504-509) and `set_detail` fields (L690-698):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
     # Invalidate analysis cache
     set_ = db.get(Set, set_id)
     if set_:
         set_.is_analyzed = 0
         set_.analysis_cache = None
+        _clear_comparison_caches(db, set_)
         db.commit()
 
     return [_set_track_response(st) for st in tracks]
@@
     return SetDetailResponse(
         id=s.id,
         name=s.name,
         created_at=s.created_at,
         duration_min=s.duration_min,
         energy_profile=s.energy_profile,
         genre_filter=s.genre_filter,
+        source=s.source,
+        planned_set_id=s.planned_set_id,
         tracks=[_set_track_response(st) for st in tracks],
     )
````
Verification:
- `source .venv/bin/activate && python -m py_compile src/kiku/api/routes/sets.py` → no output.

#### Task 9 — cli.py: `kiku compare` command
Tools: editor
Insert between the end of `analyze_set_cmd` (L684, `console.print("\n[dim]Analysis cached. View in the app or re-run to update.[/]")`) and the `serve` command decorator (L687).
Diff:
````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@
     console.print("\n[dim]Analysis cached. View in the app or re-run to update.[/]")
 
 
+@cli.command("compare")
+@click.argument("played_set")
+@click.argument("planned_set", required=False)
+def compare_cmd(played_set: str, planned_set: str | None):
+    """Compare a played set against the plan it came from.
+
+    Shows where you deviated — and what the room was telling you.
+    Pass set ids or name fragments. Planned defaults to the linked set.
+    """
+    from kiku.analysis.set_compare import compare_sets
+    from kiku.db.models import Set, get_session
+
+    session = get_session()
+
+    def _resolve(ref: str) -> Set | None:
+        try:
+            return session.get(Set, int(ref))
+        except ValueError:
+            return session.query(Set).filter(Set.name.ilike(f"%{ref}%")).first()
+
+    played = _resolve(played_set)
+    if not played:
+        console.print(f"[red]Couldn't find set '{played_set}'.[/]")
+        return
+
+    if planned_set:
+        planned = _resolve(planned_set)
+        if not planned:
+            console.print(f"[red]Couldn't find set '{planned_set}'.[/]")
+            return
+    elif played.planned_set_id:
+        planned = session.get(Set, played.planned_set_id)
+        if not planned:
+            console.print("[red]The linked planned set no longer exists.[/]")
+            return
+    else:
+        console.print(
+            "[yellow]No planned set linked. Pass it explicitly: "
+            "kiku compare <played> <planned>[/]"
+        )
+        return
+
+    console.print(f"[cyan]Comparing '{played.name}' against the plan '{planned.name}'...[/]")
+    try:
+        result = compare_sets(session, played.id, planned.id)
+    except ValueError as e:
+        console.print(f"[red]{e}[/]")
+        return
+
+    console.print(f"\n[bold]{played.name}[/] vs plan [bold]{planned.name}[/]")
+    console.print(
+        f"Kept: [green]{result.kept_count}[/] | Moved: [yellow]{result.moved_count}[/] | "
+        f"Cut: [red]{result.cut_count}[/] | Added: [cyan]{result.added_count}[/]"
+    )
+    console.print(
+        f"Arc: planned [cyan]{result.arc.planned_shape}[/] → played [cyan]{result.arc.played_shape}[/] | "
+        f"BPM drift delta: [cyan]{result.arc.bpm_drift_delta:+.1f}[/]"
+    )
+
+    deviations = [d for d in result.track_deviations if d.kind != "kept"]
+    if deviations:
+        table = Table()
+        table.add_column("Track")
+        table.add_column("Deviation")
+        table.add_column("What it says", style="dim")
+        for d in deviations:
+            if d.kind == "moved" and d.displacement is not None:
+                label = f"moved {d.displacement:+d}"
+            else:
+                label = d.kind
+            table.add_row(d.title or f"#{d.track_id}", label, d.teaching_moment)
+        console.print(table)
+
+    if result.energy_deviations:
+        console.print("\n[bold]Energy jumps:[/]")
+        for ed in result.energy_deviations:
+            console.print(f"  Track {ed.position + 1}: {ed.delta:+.2f} — {ed.teaching_moment}")
+
+    if result.deviation_patterns:
+        console.print("\n[bold]What the room told you:[/]")
+        for p in result.deviation_patterns:
+            console.print(f"  {p}")
+
+    console.print("\n[dim]Comparison cached. View it in the app or re-run to update.[/]")
+
+
 @cli.command()
 @click.option("--port", default=8000, help="HTTP port for the API server")
````
Verification:
- `source .venv/bin/activate && kiku compare --help` → shows the command help.

#### Task 10 — frontend types
Tools: editor
Two diffs in `frontend/src/lib/types/index.ts` (TAB indentation).

Diff 1 — `SetDetail` (L97-105):
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@
 export interface SetDetail {
 	id: number;
 	name: string | null;
 	created_at: string | null;
 	duration_min: number | null;
 	energy_profile: string | null;
 	genre_filter: string | null;
+	source: string | null;
+	planned_set_id: number | null;
 	tracks: SetTrack[];
 }
````

Diff 2 — `ImportResult` + new comparison types (L550-561, before `// ── SoundCloud types ──`):
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@
 export interface ImportResult {
 	set_id: number;
 	name: string;
 	source: string;
 	total_tracks: number;
 	matched_count: number;
 	unmatched_count: number;
 	unmatched_paths: UnmatchedTrack[];
 	match_methods: Record<string, number>;
 	warnings: string[];
 	duplicate_set_id: number | null;
+	planned_candidates: PlannedSetCandidate[];
 }
+
+export interface PlannedSetCandidate {
+	set_id: number;
+	name: string | null;
+	overlap: number;
+	shared_tracks: number;
+}
+
+// ── Played vs Planned comparison types ──
+
+export interface TrackDeviation {
+	kind: 'kept' | 'moved' | 'cut' | 'added';
+	track_id: number;
+	title: string | null;
+	artist: string | null;
+	planned_position: number | null;
+	played_position: number | null;
+	displacement: number | null;
+	teaching_moment: string;
+}
+
+export interface EnergyDeviation {
+	position: number;
+	track_id: number;
+	planned_energy: number;
+	played_energy: number;
+	delta: number;
+	teaching_moment: string;
+}
+
+export interface ArcComparison {
+	planned_shape: string;
+	played_shape: string;
+	planned_key_style: string;
+	played_key_style: string;
+	planned_bpm_style: string;
+	played_bpm_style: string;
+	planned_bpm_range: number[];
+	played_bpm_range: number[];
+	bpm_drift_delta: number;
+	planned_curve: number[];
+	played_curve: number[];
+}
+
+export interface SetComparison {
+	played_set_id: number;
+	planned_set_id: number;
+	played_name: string | null;
+	planned_name: string | null;
+	kept_count: number;
+	moved_count: number;
+	cut_count: number;
+	added_count: number;
+	track_deviations: TrackDeviation[];
+	energy_deviations: EnergyDeviation[];
+	arc: ArcComparison;
+	deviation_patterns: string[];
+	compared_at: string;
+}
````
Verification:
- Covered by `svelte-check` in Task 18.

#### Task 11 — frontend API client
Tools: editor
Two diffs in `frontend/src/lib/api/sets.ts` (TAB indentation).

Diff 1 — type import (L1-15):
````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@
 	SetAnalysis,
 	SetBuildComplete,
 	SetBuildParams,
+	SetComparison,
 	SetCreateParams,
````

Diff 2 — new functions after `getSetAnalysis` (ends L257), before `// ── Manual set builder...`:
````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@
 export async function getSetAnalysis(setId: number): Promise<SetAnalysis> {
 	const res = await fetch(`${API_BASE}/api/sets/${setId}/analysis`);
 	if (!res.ok) {
 		const err = await res.json().catch(() => ({ detail: 'Not analyzed yet' }));
 		throw new Error(err.detail || 'Not analyzed yet');
 	}
 	return res.json();
 }
 
+
+// ── Played vs Planned: link + compare ──
+
+export async function linkSet(setId: number, plannedSetId: number): Promise<void> {
+	await fetchJson(`/api/sets/${setId}/link`, {
+		method: 'PUT',
+		headers: { 'Content-Type': 'application/json' },
+		body: JSON.stringify({ planned_set_id: plannedSetId }),
+	});
+}
+
+export async function unlinkSet(setId: number): Promise<void> {
+	await fetch(`${API_BASE}/api/sets/${setId}/link`, { method: 'DELETE' });
+}
+
+export async function compareSet(setId: number): Promise<SetComparison> {
+	const res = await fetch(`${API_BASE}/api/sets/${setId}/compare`, { method: 'POST' });
+	if (!res.ok) {
+		const err = await res.json().catch(() => ({ detail: "Couldn't compare this set" }));
+		throw new Error(err.detail || "Couldn't compare this set");
+	}
+	return res.json();
+}
+
+export async function getSetComparison(setId: number): Promise<SetComparison> {
+	const res = await fetch(`${API_BASE}/api/sets/${setId}/comparison`);
+	if (!res.ok) {
+		const err = await res.json().catch(() => ({ detail: 'Not compared yet' }));
+		throw new Error(err.detail || 'Not compared yet');
+	}
+	return res.json();
+}
 
 // ── Manual set builder: fill, reorder, score-sequence ──
````
Verification:
- Covered by `svelte-check` in Task 18.

#### Task 12 — EnergyFlowChart: plannedCurve overlay prop
Tools: editor
Five diffs in `frontend/src/lib/components/set/EnergyFlowChart.svelte` (TAB indentation).

Diff 1 — props (L18-25):
````diff
--- a/frontend/src/lib/components/set/EnergyFlowChart.svelte
+++ b/frontend/src/lib/components/set/EnergyFlowChart.svelte
@@
 	interface Props {
 		tracks: SetWaveformTrack[];
 		energyProfile?: string | null;
 		selectedIndex?: number;
 		onTrackClick?: (index: number) => void;
+		plannedCurve?: number[] | null;
 	}
 
-	let { tracks, energyProfile, selectedIndex, onTrackClick }: Props = $props();
+	let { tracks, energyProfile, selectedIndex, onTrackClick, plannedCurve = null }: Props = $props();
````

Diff 2 — third dataset in `buildChartData()` (after the Target dataset block, L122-136):
````diff
--- a/frontend/src/lib/components/set/EnergyFlowChart.svelte
+++ b/frontend/src/lib/components/set/EnergyFlowChart.svelte
@@
 		// Target energy curve (only if profile exists)
 		if (hasTarget) {
 			datasets.push({
 				label: 'Target',
 				data: targetValues,
 				borderColor: 'rgba(255, 255, 255, 0.35)',
 				borderWidth: 1.5,
 				borderDash: [6, 4],
 				pointRadius: 0,
 				pointHoverRadius: 0,
 				tension: 0.3,
 				fill: false,
 				order: 2,
 			});
 		}
+
+		// Planned curve overlay (played-vs-planned comparison)
+		if (plannedCurve && plannedCurve.length === tracks.length) {
+			datasets.push({
+				label: 'Planned',
+				data: plannedCurve,
+				borderColor: 'rgba(186, 104, 200, 0.8)',
+				borderWidth: 1.5,
+				borderDash: [2, 3],
+				pointRadius: 0,
+				pointHoverRadius: 0,
+				tension: 0.3,
+				fill: false,
+				order: 3,
+			});
+		}
 
 		return { labels, datasets };
````

Diff 3 — legend display in `createChart()` (L166):
````diff
--- a/frontend/src/lib/components/set/EnergyFlowChart.svelte
+++ b/frontend/src/lib/components/set/EnergyFlowChart.svelte
@@
 				plugins: {
 					legend: {
-						display: targetValues.some((v) => v !== null),
+						display: targetValues.some((v) => v !== null) || (plannedCurve?.length ?? 0) > 0,
 						position: 'bottom',
````

Diff 4 — tooltip label for overlay datasets (L213-217):
````diff
--- a/frontend/src/lib/components/set/EnergyFlowChart.svelte
+++ b/frontend/src/lib/components/set/EnergyFlowChart.svelte
@@
-								// Target dataset
-								const val = ctx.parsed.y;
-								if (val !== null) return `Target: ${val.toFixed(2)}`;
-								return '';
+								// Target / Planned overlay datasets
+								const val = ctx.parsed.y;
+								if (val !== null) return `${ctx.dataset.label ?? 'Target'}: ${val.toFixed(2)}`;
+								return '';
````

Diff 5 — `updateChart()` legend refresh + reactive dependency (L266-296):
````diff
--- a/frontend/src/lib/components/set/EnergyFlowChart.svelte
+++ b/frontend/src/lib/components/set/EnergyFlowChart.svelte
@@
 	function updateChart() {
 		if (!chart) return;
 		const { labels, datasets } = buildChartData();
 		chart.data.labels = labels;
 		chart.data.datasets = datasets;
+		const targetValues = parseEnergyProfile(energyProfile, tracks.length);
+		if (chart.options.plugins?.legend) {
+			chart.options.plugins.legend.display =
+				targetValues.some((v) => v !== null) || (plannedCurve?.length ?? 0) > 0;
+		}
 		chart.update('default');
 	}
@@
 	// Reactive updates when tracks, profile, or selection changes
 	$effect(() => {
 		// Touch reactive dependencies
 		void tracks;
 		void energyProfile;
 		void selectedIndex;
+		void plannedCurve;
 
 		if (chart) {
 			updateChart();
 		}
 	});
````
Verification:
- Covered by `svelte-check` in Task 18; visual check in Task 20 E2E (manual acceptance).

#### Task 13 — SetComparison.svelte (NEW component)
Tools: editor (Write new file)
File: `frontend/src/lib/components/set/SetComparison.svelte` (exact full content, TAB indentation):
````diff
--- /dev/null
+++ b/frontend/src/lib/components/set/SetComparison.svelte
@@
+<script lang="ts">
+	import type { SetComparison, TrackDeviation } from '$lib/types';
+
+	let {
+		comparison,
+		onback,
+	}: {
+		comparison: SetComparison;
+		onback: () => void;
+	} = $props();
+
+	const KIND_COLORS: Record<string, string> = {
+		kept: '#66BB6A',
+		moved: '#FFB74D',
+		cut: '#EF5350',
+		added: '#4FC3F7',
+	};
+
+	let plannedSide = $derived(
+		comparison.track_deviations
+			.filter((d) => d.planned_position !== null)
+			.sort((a, b) => (a.planned_position ?? 0) - (b.planned_position ?? 0))
+	);
+
+	let playedSide = $derived(
+		comparison.track_deviations
+			.filter((d) => d.played_position !== null)
+			.sort((a, b) => (a.played_position ?? 0) - (b.played_position ?? 0))
+	);
+
+	let teachingDeviations = $derived(
+		comparison.track_deviations.filter((d) => d.kind !== 'kept')
+	);
+
+	function badgeLabel(d: TrackDeviation): string {
+		if (d.kind === 'moved' && d.displacement !== null) {
+			return d.displacement > 0 ? `moved +${d.displacement}` : `moved ${d.displacement}`;
+		}
+		return d.kind;
+	}
+</script>
+
+<div class="comparison">
+	<div class="comparison-header">
+		<button class="back-btn" onclick={onback}>&larr; Timeline</button>
+		<span class="title">Planned vs played</span>
+		<span class="count" style="color: {KIND_COLORS.kept}">{comparison.kept_count} kept</span>
+		<span class="count" style="color: {KIND_COLORS.moved}">{comparison.moved_count} moved</span>
+		<span class="count" style="color: {KIND_COLORS.cut}">{comparison.cut_count} cut</span>
+		<span class="count" style="color: {KIND_COLORS.added}">{comparison.added_count} added</span>
+	</div>
+
+	<div class="arc-row">
+		<span class="arc-chip">arc: {comparison.arc.planned_shape} &rarr; {comparison.arc.played_shape}</span>
+		<span class="arc-chip">keys: {comparison.arc.planned_key_style} &rarr; {comparison.arc.played_key_style}</span>
+		<span class="arc-chip">bpm: {comparison.arc.planned_bpm_style} &rarr; {comparison.arc.played_bpm_style}</span>
+	</div>
+
+	<div class="two-col">
+		<div class="col">
+			<h3>Planned — {comparison.planned_name ?? 'plan'}</h3>
+			{#each plannedSide as d (d.kind + '-' + d.track_id + '-' + d.planned_position)}
+				<div class="dev-row" class:dimmed={d.kind === 'cut'}>
+					<span class="pos">{(d.planned_position ?? 0) + 1}</span>
+					<span class="track-title">{d.title ?? `Track ${d.track_id}`}</span>
+					<span class="badge" style="background: {KIND_COLORS[d.kind]}22; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
+				</div>
+			{/each}
+		</div>
+		<div class="col">
+			<h3>Played — {comparison.played_name ?? 'set'}</h3>
+			{#each playedSide as d (d.kind + '-' + d.track_id + '-' + d.played_position)}
+				<div class="dev-row">
+					<span class="pos">{(d.played_position ?? 0) + 1}</span>
+					<span class="track-title">{d.title ?? `Track ${d.track_id}`}</span>
+					<span class="badge" style="background: {KIND_COLORS[d.kind]}22; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
+				</div>
+			{/each}
+		</div>
+	</div>
+
+	{#if teachingDeviations.length > 0 || comparison.energy_deviations.length > 0 || comparison.deviation_patterns.length > 0}
+		<div class="teaching-panel">
+			<h3>What the room told you</h3>
+			{#each comparison.deviation_patterns as p}
+				<p class="pattern">{p}</p>
+			{/each}
+			{#each teachingDeviations as d}
+				<p class="moment">
+					<span class="badge" style="background: {KIND_COLORS[d.kind]}22; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
+					{d.teaching_moment}
+				</p>
+			{/each}
+			{#each comparison.energy_deviations as ed}
+				<p class="moment">
+					<span class="badge energy">energy {ed.delta > 0 ? '+' : ''}{ed.delta.toFixed(2)}</span>
+					{ed.teaching_moment}
+				</p>
+			{/each}
+		</div>
+	{/if}
+</div>
+
+<style>
+	.comparison {
+		padding: 12px 16px;
+	}
+
+	.comparison-header {
+		display: flex;
+		align-items: center;
+		gap: 12px;
+		margin-bottom: 8px;
+	}
+
+	.back-btn {
+		padding: 4px 10px;
+		font-size: 12px;
+		color: var(--text-primary);
+		background: var(--bg-tertiary);
+		border: 1px solid var(--border);
+		border-radius: 4px;
+	}
+
+	.back-btn:hover {
+		background: var(--accent);
+		color: #000;
+		border-color: var(--accent);
+	}
+
+	.title {
+		font-weight: 600;
+		font-size: 14px;
+		margin-right: auto;
+	}
+
+	.count {
+		font-size: 12px;
+		font-weight: 600;
+	}
+
+	.arc-row {
+		display: flex;
+		gap: 8px;
+		flex-wrap: wrap;
+		margin-bottom: 12px;
+	}
+
+	.arc-chip {
+		font-size: 11px;
+		color: var(--text-secondary);
+		padding: 2px 8px;
+		background: var(--bg-tertiary);
+		border-radius: 10px;
+	}
+
+	.two-col {
+		display: grid;
+		grid-template-columns: 1fr 1fr;
+		gap: 16px;
+		margin-bottom: 16px;
+	}
+
+	.col h3 {
+		font-size: 12px;
+		font-weight: 600;
+		text-transform: uppercase;
+		letter-spacing: 0.5px;
+		color: var(--text-secondary);
+		margin: 0 0 8px;
+	}
+
+	.dev-row {
+		display: flex;
+		align-items: center;
+		gap: 8px;
+		padding: 4px 8px;
+		border-radius: 4px;
+		margin-bottom: 2px;
+		background: var(--bg-secondary);
+	}
+
+	.dev-row.dimmed {
+		opacity: 0.55;
+	}
+
+	.pos {
+		font-size: 11px;
+		color: var(--text-dim);
+		width: 20px;
+		text-align: right;
+		font-variant-numeric: tabular-nums;
+	}
+
+	.track-title {
+		font-size: 13px;
+		flex: 1;
+		min-width: 0;
+		overflow: hidden;
+		text-overflow: ellipsis;
+		white-space: nowrap;
+	}
+
+	.badge {
+		font-size: 10px;
+		font-weight: 600;
+		padding: 1px 6px;
+		border-radius: 8px;
+		white-space: nowrap;
+	}
+
+	.badge.energy {
+		background: rgba(186, 104, 200, 0.15);
+		color: #BA68C8;
+	}
+
+	.teaching-panel {
+		background: var(--bg-secondary);
+		border-radius: 8px;
+		padding: 12px 16px;
+	}
+
+	.teaching-panel h3 {
+		font-size: 12px;
+		font-weight: 600;
+		text-transform: uppercase;
+		letter-spacing: 0.5px;
+		color: var(--text-secondary);
+		margin: 0 0 8px;
+	}
+
+	.pattern {
+		font-size: 13px;
+		font-style: italic;
+		color: var(--text-primary);
+		margin: 0 0 8px;
+	}
+
+	.moment {
+		font-size: 12px;
+		color: var(--text-secondary);
+		margin: 0 0 6px;
+		display: flex;
+		align-items: baseline;
+		gap: 8px;
+	}
+</style>
````
Verification:
- Covered by `svelte-check` in Task 18.

#### Task 14 — SetView.svelte: comparison mode
Tools: editor
Eight diffs in `frontend/src/lib/components/set/SetView.svelte` (TAB indentation).

Diff 1 — imports (L2-9):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
-	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData, SetAnalysis } from '$lib/types';
-	import { getSet, getSetWaveforms, getTransition, exportRekordbox, exportM3U8, deleteSet, analyzeSet, getSetAnalysis } from '$lib/api/sets';
+	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData, SetAnalysis, SetComparison as SetComparisonType } from '$lib/types';
+	import { getSet, getSetWaveforms, getTransition, exportRekordbox, exportM3U8, deleteSet, analyzeSet, getSetAnalysis, compareSet, getSetComparison, unlinkSet } from '$lib/api/sets';
 	import { getUiStore } from '$lib/stores/ui.svelte';
 	import SetPicker from './SetPicker.svelte';
 	import SetTimeline from './SetTimeline.svelte';
 	import TransitionDetail from './TransitionDetail.svelte';
 	import EnergyFlowChart from './EnergyFlowChart.svelte';
 	import SetEnergyReview from './SetEnergyReview.svelte';
+	import SetComparison from './SetComparison.svelte';
````

Diff 2 — state (L82-83):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	let analysis = $state<SetAnalysis | null>(null);
 	let analyzingSet = $state(false);
+	let comparison = $state<SetComparisonType | null>(null);
+	let comparing = $state(false);
+	let showComparison = $state(false);
````

Diff 3 — handlers after `handleAnalyze` (L177):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	async function handleAnalyze() {
 		if (!selectedSet) return;
 		analyzingSet = true;
 		try {
 			analysis = await analyzeSet(selectedSet.id);
 		} catch (e) {
 			console.error('Analysis failed:', e);
 		} finally {
 			analyzingSet = false;
 		}
 	}
+
+	async function handleCompare() {
+		if (!selectedSet || comparing) return;
+		comparing = true;
+		try {
+			comparison = await compareSet(selectedSet.id);
+			showComparison = true;
+		} catch (e) {
+			error = e instanceof Error ? e.message : String(e);
+		} finally {
+			comparing = false;
+		}
+	}
+
+	async function handleUnlink() {
+		if (!selectedSet) return;
+		try {
+			await unlinkSet(selectedSet.id);
+			comparison = null;
+			showComparison = false;
+			if (setDetail) setDetail = { ...setDetail, planned_set_id: null };
+		} catch (e) {
+			error = e instanceof Error ? e.message : String(e);
+		}
+	}
````

Diff 4 — `loadSetData` reset + cached comparison (L179-217):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 		transition = null;
 		activeTransitionIndex = -1;
 		analysis = null;
+		comparison = null;
+		showComparison = false;
@@
 			// Auto-analyze if no analysis exists and set has enough tracks
 			if (!analysis && waveforms.length >= 2) {
 				handleAnalyze();
 			}
+
+			// Load the cached comparison when this set is linked to a plan
+			if (detail.planned_set_id) {
+				try {
+					comparison = await getSetComparison(setId);
+				} catch {
+					comparison = null;
+				}
+			}
````

Diff 5 — controls: compare + unlink buttons (after the analyzing-status block, L270-272):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 			{:else if waveformTracks.length >= 2 && analyzingSet}
 				<span class="analyzing-status">Analyzing...</span>
 			{/if}
+			{#if setDetail?.planned_set_id}
+				<button class="compare-btn" onclick={handleCompare} disabled={comparing}>
+					{comparing ? 'Comparing...' : 'Planned vs played'}
+				</button>
+				<button class="unlink-btn" onclick={handleUnlink} title="Remove the link to the planned set">
+					Unlink
+				</button>
+			{/if}
````

Diff 6 — chart overlay prop (L322-327):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 						<EnergyFlowChart
 							tracks={waveformTracks}
 							energyProfile={setDetail?.energy_profile}
+							plannedCurve={showComparison && comparison ? comparison.arc.planned_curve : null}
 							selectedIndex={selectedChartIndex}
 							onTrackClick={handleChartTrackClick}
 						/>
````

Diff 7 — timeline-scroll swap (L354-356):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 				<div class="timeline-scroll">
-					{#if loadingTransition}
+					{#if showComparison && comparison}
+						<SetComparison {comparison} onback={() => { showComparison = false; }} />
+					{:else if loadingTransition}
 						<div class="status">Analyzing the transition...</div>
````

Diff 8 — styles (append after `.analyze-btn:disabled` rule, L638-641):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	.analyze-btn:disabled {
 		opacity: 0.5;
 		cursor: default;
 	}
+
+	.compare-btn {
+		padding: 4px 12px;
+		font-size: 12px;
+		font-weight: 600;
+		color: var(--text-primary);
+		background: var(--bg-tertiary);
+		border: 1px solid var(--border);
+		border-radius: 4px;
+		transition: all 0.15s;
+	}
+
+	.compare-btn:hover:not(:disabled) {
+		background: var(--accent);
+		color: #000;
+		border-color: var(--accent);
+	}
+
+	.compare-btn:disabled {
+		opacity: 0.5;
+		cursor: default;
+	}
+
+	.unlink-btn {
+		padding: 4px 8px;
+		font-size: 11px;
+		color: var(--text-dim);
+		background: transparent;
+		border: 1px solid var(--border);
+		border-radius: 4px;
+	}
+
+	.unlink-btn:hover {
+		color: var(--text-primary);
+	}
````
Note for Diff 5/6/7: the template inside `{#if selectedSet}` uses one extra TAB level relative to what is shown here; match the file's existing indentation exactly (the shown context lines are authoritative).

Verification:
- Covered by `svelte-check` in Task 18; behavior validated in Task 20.

#### Task 15 — ImportPlaylistDialog: one-click link step
Tools: editor
Four diffs in `frontend/src/lib/components/set/ImportPlaylistDialog.svelte` (TAB indentation). Candidates come from the import response (`planned_candidates`) — do NOT embed SetPicker here (SetPicker imports this dialog; that would be circular).

Diff 1 — imports + state (L1-20):
````diff
--- a/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
+++ b/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
@@
 	import type { ImportResult } from '$lib/types';
-	import { importPlaylist } from '$lib/api/sets';
+	import { importPlaylist, linkSet } from '$lib/api/sets';
@@
 	let result = $state<ImportResult | null>(null);
 	let dragOver = $state(false);
+	let linkedSetId = $state<number | null>(null);
+	let linking = $state(false);
+	let linkError = $state('');
````

Diff 2 — `reset()` + `doLink()` (L31-38, L69-86):
````diff
--- a/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
+++ b/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
@@
 	function reset() {
 		file = null;
 		nameOverride = '';
 		force = false;
 		loading = false;
 		error = '';
 		result = null;
+		linkedSetId = null;
+		linking = false;
+		linkError = '';
 	}
@@
 		} catch (err) {
 			error = err instanceof Error ? err.message : 'Import failed';
 		} finally {
 			loading = false;
 		}
 	}
+
+	async function doLink(plannedSetId: number) {
+		if (!result || linking) return;
+		linking = true;
+		linkError = '';
+		try {
+			await linkSet(result.set_id, plannedSetId);
+			linkedSetId = plannedSetId;
+		} catch (err) {
+			linkError = err instanceof Error ? err.message : "Couldn't link the sets";
+		} finally {
+			linking = false;
+		}
+	}
````

Diff 3 — candidate panel in the result branch (after the warnings block, before the Done actions, L177-188):
````diff
--- a/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
+++ b/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
@@
 				{#if result.warnings.length > 0}
 					<div class="warnings">
 						{#each result.warnings as w}
 							<p class="warning">{w}</p>
 						{/each}
 					</div>
 				{/if}
+
+				{#if result.planned_candidates.length > 0}
+					<div class="candidates">
+						<p class="candidates-title">
+							This looks like a set you planned in Kiku — link it to see how the night deviated:
+						</p>
+						{#each result.planned_candidates as c}
+							<button
+								class="candidate"
+								class:linked={linkedSetId === c.set_id}
+								onclick={() => doLink(c.set_id)}
+								disabled={linking || linkedSetId !== null}
+							>
+								{c.name ?? `Set ${c.set_id}`}
+								<span class="overlap">{Math.round(c.overlap * 100)}% shared</span>
+								{#if linkedSetId === c.set_id}<span class="linked-mark">linked</span>{/if}
+							</button>
+						{/each}
+						{#if linkError}
+							<p class="error">{linkError}</p>
+						{/if}
+					</div>
+				{/if}
 
 				<div class="actions">
 					<button class="primary" onclick={handleClose}>Done</button>
 				</div>
````

Diff 4 — styles (append at end of `<style>`, after `.warning` rule L408-412):
````diff
--- a/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
+++ b/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
@@
 	.warning {
 		color: var(--color-yellow, #f39c12);
 		font-size: 12px;
 		margin: 4px 0;
 	}
+
+	.candidates {
+		margin-bottom: 12px;
+	}
+
+	.candidates-title {
+		font-size: 13px;
+		color: var(--text-dim);
+		margin: 0 0 8px;
+	}
+
+	.candidate {
+		display: flex;
+		align-items: center;
+		gap: 8px;
+		width: 100%;
+		text-align: left;
+		margin-bottom: 6px;
+		background: var(--bg-secondary);
+		color: var(--text-primary);
+	}
+
+	.candidate.linked {
+		border-color: var(--accent);
+	}
+
+	.candidate:disabled:not(.linked) {
+		opacity: 0.5;
+	}
+
+	.overlap {
+		font-size: 11px;
+		color: var(--text-dim);
+		margin-left: auto;
+	}
+
+	.linked-mark {
+		font-size: 11px;
+		color: var(--accent);
+	}
````
Verification:
- Covered by `svelte-check` in Task 18; flow validated in Task 20.

#### Task 16 — unit tests: tests/test_set_compare.py (NEW)
Tools: editor (Write new file)
File: `tests/test_set_compare.py` (exact full content):
````diff
--- /dev/null
+++ b/tests/test_set_compare.py
@@
+"""Tests for the played-vs-planned comparison engine."""
+
+import pytest
+from sqlalchemy import create_engine
+from sqlalchemy.orm import sessionmaker
+from sqlalchemy.pool import NullPool
+
+from kiku.analysis.set_compare import detect_energy_jumps, diff_tracks
+from kiku.analysis.teaching import detect_deviation_patterns, deviation_teaching_moment
+from kiku.db.models import Base, Set, SetTrack, Track
+from kiku.import_playlist.service import suggest_planned_sets
+
+
+# ── Track diff ──────────────────────────────────────────────────────────
+
+
+def test_identical_sets_all_kept():
+    entries = diff_tracks([1, 2, 3], [1, 2, 3])
+    assert [e["kind"] for e in entries] == ["kept", "kept", "kept"]
+
+
+def test_full_reorder_all_moved_with_displacement():
+    entries = diff_tracks([1, 2, 3], [3, 1, 2])
+    by_id = {e["track_id"]: e for e in entries}
+    assert by_id[3]["kind"] == "moved" and by_id[3]["displacement"] == -2
+    assert by_id[1]["kind"] == "moved" and by_id[1]["displacement"] == 1
+    assert by_id[2]["kind"] == "moved" and by_id[2]["displacement"] == 1
+
+
+def test_cut_and_added_mix():
+    entries = diff_tracks([1, 2, 3, 4], [1, 9, 3])
+    by_id = {e["track_id"]: e for e in entries}
+    assert by_id[1]["kind"] == "kept"
+    assert by_id[3]["kind"] == "kept"
+    assert by_id[9]["kind"] == "added" and by_id[9]["planned_position"] is None
+    assert by_id[2]["kind"] == "cut" and by_id[2]["played_position"] is None
+    assert by_id[4]["kind"] == "cut"
+
+
+def test_duplicate_track_ids_pair_in_order():
+    entries = diff_tracks([7, 7], [7])
+    kinds = sorted(e["kind"] for e in entries)
+    assert kinds == ["cut", "kept"]
+
+
+def test_empty_planned_all_added():
+    entries = diff_tracks([], [1, 2])
+    assert [e["kind"] for e in entries] == ["added", "added"]
+
+
+# ── Energy jumps ────────────────────────────────────────────────────────
+
+
+def test_energy_jump_detection():
+    planned = [0.3, 0.4, 0.5, 0.6]
+    played = [0.3, 0.75, 0.5, 0.25]
+    jumps = detect_energy_jumps(planned, played)
+    assert (1, 0.35) in jumps
+    assert (3, -0.35) in jumps
+    assert all(pos not in (0, 2) for pos, _ in jumps)
+
+
+def test_no_jumps_when_curves_track():
+    assert detect_energy_jumps([0.3, 0.5], [0.35, 0.45]) == []
+
+
+# ── Deviation teaching moments ──────────────────────────────────────────
+
+
+@pytest.mark.parametrize("kind", ["kept", "moved", "cut", "added", "energy_jump"])
+def test_deviation_moment_never_blames(kind):
+    moment = deviation_teaching_moment(
+        kind, title="Test Track", displacement=2, delta=0.4, position=3
+    )
+    assert moment
+    for word in ("mistake", "wrong", "failed", "blame"):
+        assert word not in moment.lower()
+
+
+def test_moved_earlier_mentions_floor():
+    moment = deviation_teaching_moment("moved", title="Peak Tune", displacement=-3)
+    assert "earlier" in moment
+
+
+def test_added_frames_instinct():
+    moment = deviation_teaching_moment("added", title="Secret Weapon")
+    assert "wasn't in the plan" in moment
+
+
+# ── Deviation patterns ──────────────────────────────────────────────────
+
+
+def test_all_kept_pattern():
+    devs = [("kept", 0), ("kept", 1), ("kept", 2)]
+    patterns = detect_deviation_patterns(devs, [0.0, 0.0, 0.0], 3)
+    assert len(patterns) == 1
+    assert "exactly as planned" in patterns[0]
+
+
+def test_late_adds_pattern():
+    devs = [("kept", 0), ("kept", 1), ("added", 8), ("added", 9)]
+    patterns = detect_deviation_patterns(devs, [], 10)
+    assert any("cluster late" in p for p in patterns)
+
+
+def test_heavy_cuts_pattern():
+    devs = [("kept", 0), ("cut", None), ("cut", None)]
+    patterns = detect_deviation_patterns(devs, [], 1)
+    assert any("cut over a third" in p for p in patterns)
+
+
+def test_running_hot_pattern():
+    devs = [("kept", 0), ("moved", 1)]
+    patterns = detect_deviation_patterns(devs, [0.2, 0.3, 0.25], 3)
+    assert any("hotter than the plan" in p for p in patterns)
+
+
+# ── Candidate suggestion (Jaccard) ──────────────────────────────────────
+
+
+@pytest.fixture()
+def session(tmp_path):
+    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", poolclass=NullPool)
+    Base.metadata.create_all(engine)
+    s = sessionmaker(bind=engine)()
+    for i in range(1, 11):
+        s.add(Track(id=i, title=f"Track {i}", bpm=120.0 + i, duration_sec=300.0))
+    a = Set(id=1, name="Planned A", source="kiku")
+    b = Set(id=2, name="Planned B", source="kiku")
+    c = Set(id=3, name="Manual", source="manual")
+    s.add_all([a, b, c])
+    s.flush()
+    for pos, tid in enumerate([1, 2, 3, 4, 5]):
+        s.add(SetTrack(set_id=1, position=pos, track_id=tid))
+    for pos, tid in enumerate([6, 7, 8]):
+        s.add(SetTrack(set_id=2, position=pos, track_id=tid))
+    for pos, tid in enumerate([1, 2, 3]):
+        s.add(SetTrack(set_id=3, position=pos, track_id=tid))
+    s.commit()
+    yield s
+    s.close()
+    engine.dispose()
+
+
+def test_suggest_planned_sets_ranks_by_overlap(session):
+    candidates = suggest_planned_sets(session, [1, 2, 3, 4, 5])
+    assert candidates[0]["set_id"] == 1
+    assert candidates[0]["overlap"] == 1.0
+    assert candidates[0]["shared_tracks"] == 5
+
+
+def test_suggest_planned_sets_threshold_excludes_weak(session):
+    # One shared track each side -> Jaccard well below 0.3
+    candidates = suggest_planned_sets(session, [1, 6, 9, 10])
+    assert candidates == []
+
+
+def test_suggest_planned_sets_ignores_non_kiku_sets(session):
+    candidates = suggest_planned_sets(session, [1, 2, 3])
+    assert all(c["set_id"] != 3 for c in candidates)
+
+
+def test_suggest_planned_sets_excludes_self(session):
+    candidates = suggest_planned_sets(session, [1, 2, 3, 4, 5], exclude_set_id=1)
+    assert all(c["set_id"] != 1 for c in candidates)
````
Verification:
- `source .venv/bin/activate && python -m pytest tests/test_set_compare.py -x -q` → all pass.

#### Task 17 — API tests: tests/api/test_compare_api.py (NEW)
Tools: editor (Write new file)
File: `tests/api/test_compare_api.py` (exact full content). Reuses `client`/`db_session` fixtures from tests/api/conftest.py (set 1 = "Test Set" with tracks 1-5 at positions 0-4; 20 seeded tracks).
````diff
--- /dev/null
+++ b/tests/api/test_compare_api.py
@@
+"""API tests for played-vs-planned link + compare endpoints."""
+
+from kiku.db.models import Set, SetTrack
+
+
+def _seed_planned_set(db_session, set_id=2, track_ids=(1, 2, 3, 4, 5)):
+    planned = Set(id=set_id, name="Planned Set", source="kiku", duration_min=30)
+    db_session.add(planned)
+    db_session.flush()
+    for pos, tid in enumerate(track_ids):
+        db_session.add(SetTrack(set_id=set_id, position=pos, track_id=tid))
+    db_session.commit()
+    return planned
+
+
+# ── Link / unlink ──────────────────────────────────────────────────────
+
+
+def test_link_sets(client, db_session):
+    _seed_planned_set(db_session)
+    res = client.put("/api/sets/1/link", json={"planned_set_id": 2})
+    assert res.status_code == 200
+    assert res.json() == {"set_id": 1, "planned_set_id": 2}
+
+
+def test_link_self_returns_400(client, db_session):
+    res = client.put("/api/sets/1/link", json={"planned_set_id": 1})
+    assert res.status_code == 400
+
+
+def test_link_missing_planned_returns_404(client, db_session):
+    res = client.put("/api/sets/1/link", json={"planned_set_id": 999})
+    assert res.status_code == 404
+
+
+def test_link_missing_set_returns_404(client, db_session):
+    res = client.put("/api/sets/999/link", json={"planned_set_id": 1})
+    assert res.status_code == 404
+
+
+def test_unlink(client, db_session):
+    _seed_planned_set(db_session)
+    client.put("/api/sets/1/link", json={"planned_set_id": 2})
+    res = client.delete("/api/sets/1/link")
+    assert res.status_code == 204
+    assert db_session.get(Set, 1).planned_set_id is None
+
+
+def test_set_detail_exposes_link(client, db_session):
+    _seed_planned_set(db_session)
+    client.put("/api/sets/1/link", json={"planned_set_id": 2})
+    res = client.get("/api/sets/1")
+    assert res.status_code == 200
+    assert res.json()["planned_set_id"] == 2
+
+
+# ── Compare ────────────────────────────────────────────────────────────
+
+
+def test_compare_unlinked_returns_404(client, db_session):
+    res = client.post("/api/sets/1/compare")
+    assert res.status_code == 404
+
+
+def test_compare_returns_report_and_caches(client, db_session):
+    # Played set 1 has tracks 1-5; plan has 1,2,3 then 6,7 -> 3 kept, 2 added, 2 cut
+    _seed_planned_set(db_session, track_ids=(1, 2, 3, 6, 7))
+    client.put("/api/sets/1/link", json={"planned_set_id": 2})
+    res = client.post("/api/sets/1/compare")
+    assert res.status_code == 200
+    data = res.json()
+    assert data["kept_count"] == 3
+    assert data["added_count"] == 2
+    assert data["cut_count"] == 2
+    assert data["planned_set_id"] == 2
+    assert len(data["track_deviations"]) == 7
+    assert all(d["teaching_moment"] for d in data["track_deviations"])
+    assert len(data["arc"]["planned_curve"]) == 5
+    assert len(data["arc"]["played_curve"]) == 5
+    # Cached and served by GET
+    cached = client.get("/api/sets/1/comparison")
+    assert cached.status_code == 200
+    assert cached.json()["kept_count"] == 3
+
+
+def test_comparison_404_before_compare(client, db_session):
+    res = client.get("/api/sets/1/comparison")
+    assert res.status_code == 404
+
+
+def test_track_mutation_invalidates_comparison(client, db_session):
+    _seed_planned_set(db_session)
+    client.put("/api/sets/1/link", json={"planned_set_id": 2})
+    assert client.post("/api/sets/1/compare").status_code == 200
+    assert client.get("/api/sets/1/comparison").status_code == 200
+    # Mutating the played set clears its cached comparison
+    res = client.post("/api/sets/1/tracks", json={"track_id": 10, "position": 5})
+    assert res.status_code == 200
+    assert client.get("/api/sets/1/comparison").status_code == 404
+
+
+def test_planned_mutation_invalidates_comparison_on_played_side(client, db_session):
+    _seed_planned_set(db_session)
+    client.put("/api/sets/1/link", json={"planned_set_id": 2})
+    assert client.post("/api/sets/1/compare").status_code == 200
+    # Mutating the PLANNED set clears the played set's cache (reverse lookup)
+    res = client.post("/api/sets/2/tracks", json={"track_id": 10, "position": 5})
+    assert res.status_code == 200
+    assert client.get("/api/sets/1/comparison").status_code == 404
````
Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_compare_api.py -x -q` → all pass.

#### Task 18 — Lint & type-check all changed files
Tools: shell
Note: ruff and pyright are NOT installed in this repo/venv (verified: `command -v ruff` empty, `.venv/bin/python -m ruff` → No module named ruff). Use py_compile for Python and svelte-check for the frontend; if ruff happens to be available, prefer it.
Commands:
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer
source .venv/bin/activate
PYFILES="src/kiku/db/models.py src/kiku/analysis/teaching.py src/kiku/analysis/set_compare.py src/kiku/api/schemas.py src/kiku/api/routes/sets.py src/kiku/import_playlist/service.py src/kiku/cli.py alembic/versions/c9d0e1f2a3b4_add_planned_set_link_and_comparison_cache.py tests/test_set_compare.py tests/api/test_compare_api.py"
if command -v ruff >/dev/null 2>&1; then ruff check $PYFILES; else python -m py_compile $PYFILES && echo "py_compile OK"; fi
cd frontend && npx svelte-check --tsconfig ./tsconfig.json
```
Expectations:
- py_compile (or ruff) clean on all 10 Python files.
- `svelte-check` reports 0 NEW errors against types/index.ts, api/sets.ts, EnergyFlowChart.svelte, SetComparison.svelte, SetView.svelte, ImportPlaylistDialog.svelte (compare error count to a pre-change `git stash` run if any pre-existing errors surface).

#### Task 19 — Full backend test suite
Tools: shell
Commands:
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer
source .venv/bin/activate && python -m pytest tests/ -x -q
```
Expectations:
- All tests pass (182 pre-existing + ~20 new). Existing import-service and sets-API tests must not regress (`ImportResult.planned_candidates` and `ImportResultResponse.planned_candidates` both default to empty lists; `SetDetailResponse` new fields default to None).

#### Task 20 — E2E: import → suggest → link → compare
Tools: shell (scripted API loop) + manual UI acceptance
Pre-req: Task 1 migration applied (`alembic upgrade head`).

Scripted closed loop (export a real Kiku-built set, re-import it as "played", expect candidate suggestion = the source set, link, compare):
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer
source .venv/bin/activate
alembic upgrade head
kiku serve --port 8765 > /tmp/kiku_e2e_serve.log 2>&1 &
SERVER_PID=$!
sleep 4

SET_ID=$(curl -s 'http://localhost:8765/api/sets?limit=50' | jq '[.[] | select(.source=="kiku" and .track_count>=2)][0].id')
echo "Planned (Kiku-built) set: $SET_ID"
curl -s -X POST "http://localhost:8765/api/sets/$SET_ID/export/m3u8" -o /tmp/e2e_played.m3u8

IMPORT=$(curl -s -X POST http://localhost:8765/api/sets/import/m3u8 -F "file=@/tmp/e2e_played.m3u8" -F "name=E2E Played Set" -F "force=true")
echo "$IMPORT" | jq '{set_id, matched_count, planned_candidates}'
PLAYED_ID=$(echo "$IMPORT" | jq '.set_id')

# Expect: planned_candidates contains SET_ID with overlap ~1.0
curl -s -X PUT "http://localhost:8765/api/sets/$PLAYED_ID/link" -H 'Content-Type: application/json' -d "{\"planned_set_id\": $SET_ID}" | jq
curl -s -X POST "http://localhost:8765/api/sets/$PLAYED_ID/compare" | jq '{kept_count, moved_count, cut_count, added_count, deviation_patterns}'
curl -s "http://localhost:8765/api/sets/$PLAYED_ID/comparison" | jq '.compared_at'
curl -s "http://localhost:8765/api/sets/$PLAYED_ID" | jq '.planned_set_id'

# Cleanup: remove the E2E import, stop server
curl -s -X DELETE "http://localhost:8765/api/sets/$PLAYED_ID" -o /dev/null -w "delete: %{http_code}\n"
kill $SERVER_PID
```
Expectations:
- `planned_candidates` includes the source set with `overlap` ≈ 1.0.
- compare returns 200 with `kept_count` == track count (identical round-trip), "exactly as planned" in `deviation_patterns`.
- GET `/comparison` returns the cached report; set detail exposes `planned_set_id`.

Manual UI acceptance (Human Section L44): run `kiku serve` + `cd frontend && npm run dev`; in Set tab → Import Playlist → drop a real Rekordbox history M3U8 → candidate appears in success panel → click to link → open the imported set → "Planned vs played" button → comparison view shows two-col lists with badges, planned-curve overlay on the energy chart, and the teaching panel.

#### Task 21 — Commit implementation files
Tools: git
Commands:
```bash
cd /home/mantis/Development/mantis-dev/waveform-builer
BRANCH=$(git rev-parse --abbrev-ref HEAD); [ "$BRANCH" = "played-vs-planned" ] || { echo "ERROR: expected branch played-vs-planned, on $BRANCH" >&2; exit 2; }
git add -- \
  alembic/versions/c9d0e1f2a3b4_add_planned_set_link_and_comparison_cache.py \
  src/kiku/db/models.py \
  src/kiku/analysis/teaching.py \
  src/kiku/analysis/set_compare.py \
  src/kiku/api/schemas.py \
  src/kiku/api/routes/sets.py \
  src/kiku/import_playlist/service.py \
  src/kiku/cli.py \
  frontend/src/lib/types/index.ts \
  frontend/src/lib/api/sets.ts \
  frontend/src/lib/components/set/EnergyFlowChart.svelte \
  frontend/src/lib/components/set/SetComparison.svelte \
  frontend/src/lib/components/set/SetView.svelte \
  frontend/src/lib/components/set/ImportPlaylistDialog.svelte \
  tests/test_set_compare.py \
  tests/api/test_compare_api.py
git commit -m "spec(019): IMPLEMENT - played-vs-planned"
```
Notes: commit ONLY these 16 files. Never amend; never commit to main. Spec-file progress is committed separately by the stage workflow.

### Validate

Every Human Section requirement and how this Plan complies:

- **L5 HLO: link imported set to planned set + deviation analysis with teaching moments** — Tasks 1-2 (link columns), 4 (deviation engine), 3 (teaching), 7 (API), 14 (UI view).
- **L8 MLO: DB migration + link/unlink API** — Task 1 migration (`planned_set_id`, `comparison_cache`); Task 7 `PUT/DELETE /{set_id}/link`.
- **L9 MLO: deviation engine — track level (kept/moved/cut/added) + arc level (energy curve vs played, BPM drift, key journey)** — Task 4 `diff_tracks()` + `ArcComparison` (shapes, key styles, bpm styles/ranges, `bpm_drift_delta`, curves).
- **L10 MLO: teaching moments in mentor voice, never blame, room-speaking framing** — Task 3 copy ("the floor probably asked for it early", "your warmups may be longer than your rooms want"); blame-word regression test in Task 16.
- **L11 MLO: compare API cached like analysis + CLI** — Task 7 `POST /compare` + `GET /comparison` mirroring analyze/analysis; Task 9 `kiku compare <played> [<planned>]`.
- **L12 MLO: frontend comparison view — side-by-side timeline, deviation badges, energy overlay, teaching panel** — Task 13 two-col lists with badges + teaching panel; Task 12 planned-curve chart overlay; Task 14 view swap in `timeline-scroll`.
- **L13 MLO: candidate planned sets on import (track-overlap heuristic), one-click link** — Task 6 Jaccard `suggest_planned_sets()` (≥0.3, top 3); Task 15 one-click link buttons in the import success panel.
- **L14 MLO: unit tests for engine + teaching, API tests for link + compare** — Tasks 16 and 17.
- **L19 DT: reuse spec 010 import machinery** — Task 6 hooks into `import_playlist()` after set creation; no parallel import path.
- **L20 DT: reuse spec 011 `analyze_set()`, arc analysis, teaching engine, cache pattern** — Task 4 calls `analyze_set()` per side; Task 3 extends teaching.py; `comparison_cache` mirrors `analysis_cache`.
- **L21 DT: energy resolution cascade + position inference reuse** — Task 4 `_played_energies()` uses `get_track_energy()` then `inferred_energy` (filled by `analyze_set`'s `_infer_energy`).
- **L22 DT: ID-based diff, not fuzzy** — Task 4 diffs `track_id` sequences only.
- **L24-28 DT: deviation taxonomy kept/moved (displacement)/cut/added** — Task 4 `diff_tracks()` emits exactly these kinds with displacement on moved.
- **L31 DT: planned `energy_profile` target curve vs played resolved energies, overlay both** — Task 4 `_planned_target_curve()` (`target_energy_at()` sampling, arc fallback) + Task 12 overlay.
- **L32 DT: detect energy-zone jumps vs planned curve** — Task 4 `detect_energy_jumps()` (threshold 0.3 ≈ two zones) per elapsed position.
- **L33 DT: BPM trajectory + key-journey comparison via spec 011 arc analyzers** — Task 4 `ArcComparison` from both sides' `ArcAnalysis`.
- **L36 Constraint: no new dependencies; pure diff + existing modules** — only stdlib (`collections`, `dataclasses`, `json`) + existing kiku modules; no new packages anywhere.
- **L37 Constraint: cache comparison, invalidate when either set changes** — Task 4 caches on played set; Task 8 `_clear_comparison_caches()` in add/remove/reorder with reverse `planned_set_id` lookup; tested both sides in Task 17.
- **L38 Constraint: linking optional and reversible; unlinked imported sets stay valid** — `planned_set_id` nullable; DELETE /link (Task 7); UI Unlink (Task 14); compare without a link is a clean 404, everything else untouched.
- **L39 Constraint: voice per BRANDING.md, deviations are information, DJ's ear may have been right** — Task 3 ("Trust that read", "your instinct reached for what the room needed"); error copy uses "Couldn't…" not "error occurred" (Tasks 7, 9, 11, 15).
- **L42 Testing — unit: synthetic pairs (identical/reordered/cut-added/energy jumps) + teaching selection** — Task 16 covers all listed cases plus Jaccard ranking.
- **L43 Testing — API: link/unlink, compare 200/404, cache behavior** — Task 17 covers 200/400/404 link paths, compare 200 + 404 unlinked, cache hit + invalidation.
- **L44 Testing — E2E manual acceptance: import real M3U8, link, view comparison in UI** — Task 20 scripted loop + manual UI acceptance steps.
- **L47 Behavior: honor product principles, reuse 010/011 machinery** — "Show the Why": every deviation carries a teaching moment; "The Story Comes First": patterns speak about the room and the DJ's read; reuse is explicit in Tasks 4 and 6.

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

- [x] Task 1 — Alembic migration: planned_set_id + comparison_cache — Status: Done
- [x] Task 2 — models.py: Set columns — Status: Done
- [x] Task 3 — teaching.py: deviation teaching moments + patterns — Status: Done
- [x] Task 4 — set_compare.py: deviation engine (NEW module) — Status: Done
- [x] Task 5 — schemas.py: comparison + candidate + link models — Status: Done
- [x] Task 6 — import service: planned-set candidate suggestion — Status: Done
- [x] Task 7 — routes/sets.py: link + compare endpoints — Status: Done
- [x] Task 8 — routes/sets.py: cache invalidation + candidates + set_detail — Status: Done
- [x] Task 9 — cli.py: `kiku compare` command — Status: Done
- [x] Task 10 — frontend types — Status: Done
- [x] Task 11 — frontend API client — Status: Done
- [x] Task 12 — EnergyFlowChart: plannedCurve overlay prop — Status: Done
- [x] Task 13 — SetComparison.svelte (NEW component) — Status: Done
- [x] Task 14 — SetView.svelte: comparison mode — Status: Done
- [x] Task 15 — ImportPlaylistDialog: one-click link step — Status: Done
- [x] Task 16 — unit tests: tests/test_set_compare.py (NEW) — Status: Done (22 passed)
- [x] Task 17 — API tests: tests/api/test_compare_api.py (NEW) — Status: Done (11 passed)
- [x] Task 18 — Lint & type-check all changed files — Status: Done (py_compile OK; svelte-check 0 errors, 4 pre-existing warnings = baseline)
- [x] Task 19 — Full backend test suite — Status: Done (327 passed, 33 new; 5 failures in tests/test_energy.py are PRE-EXISTING at HEAD — stale data/energy_calibration.json shifts calibrated zone boundaries; unrelated to spec 019)
- [x] Task 20 — E2E: import → suggest → link → compare — Status: Done (adapted: no source="kiku" sets existed in DB — temporarily tagged set 20 as kiku, ran the closed loop [export → import → candidate overlap 1.0 → link → compare 10 kept + "exactly as planned" → cached GET → set detail planned_set_id=20 → CLI compare], then restored source=NULL and deleted the E2E import. Manual UI acceptance deferred to the DJ.)
- [x] Task 21 — Commit implementation files — Status: Done

### Notes
- All 21 tasks complete. 33 new tests (22 unit + 11 API), all passing.
- Pre-existing failure surfaced (NOT spec 019): 5 tests in tests/test_energy.py fail at HEAD too — stale data/energy_calibration.json (2026-04-25) shifts calibrated zone boundaries away from the fixed-boundary test expectations.
- svelte-check: 0 errors, 4 warnings — identical to pre-change baseline.
- E2E adaptation: live DB had no `source="kiku"` sets (older sets predate source tracking); set 20 was temporarily tagged for the closed-loop test and restored afterward. Manual UI acceptance (import real Rekordbox M3U8 → candidate → link → comparison view) deferred to the DJ.
- DB backup taken before migration: /tmp/dj_library_backup_spec019.db.

Implementation commit: 6baf4c1

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
