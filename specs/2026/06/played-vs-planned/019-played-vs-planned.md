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
