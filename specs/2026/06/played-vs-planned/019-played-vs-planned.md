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
