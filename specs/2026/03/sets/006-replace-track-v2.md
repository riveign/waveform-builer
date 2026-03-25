# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Evolve the Replace Track feature from a basic swap tool into a context-aware track surgery system. The DJ should be able to audition replacements with waveform previews and crossfade simulations, filter candidates intelligently, detect weak spots across an entire set, and undo swaps — all while understanding *why* each candidate fits or doesn't.

## Mid-Level Objectives (MLO)

- **AUDITION** replacement candidates with full waveform previews and crossfade simulations against neighboring tracks, so the DJ hears the transition in context before committing
- **EXPLAIN** every suggestion — hovering a score reveals which dimensions (harmonic, BPM, energy, genre, quality) are strong or weak, for both incoming and outgoing transitions
- **FILTER** candidates inside the modal by genre family, energy zone, or key — the backend already supports `genre_filter`, extend to other dimensions
- **DETECT** weak spots across the full set (transitions scoring below threshold) and offer batch replacement suggestions
- **UNDO** replacements — track every swap in a history log, allow one-click revert to previous track
- **OPTIMIZE** globally — rank candidates not just by local neighbor fit, but by how much they improve the overall set's score and energy arc

## Details (DT)

### Tier 1 — Quick Wins

#### Genre Filter in Modal
Add a chip selector at the top of the candidate list. The backend `GET .../replacements?genre_filter=techno,house` already supports this. Frontend-only change in `ReplaceTrackModal.svelte`.

#### "Why This?" Score Tooltip
On hover over a candidate's combined score, show a popover with the full breakdown for both directions:
- Incoming (prev → candidate): harmonic, energy_fit, bpm_compat, genre_coherence, track_quality
- Outgoing (candidate → next): same 5 dimensions
Data already lives in `incoming_breakdown` / `outgoing_breakdown` on each `ReplacementCandidate`.

#### Waveform Preview
Replace the raw `<audio>` element with `WavesurferPlayer` so the DJ sees spectral waveform while previewing. Check `has_waveform`, fetch via existing `GET /api/tracks/{id}/waveform/overview`. May need a collapsible waveform section in the modal to manage height.

### Tier 2 — Deeper Integration

#### Transition Preview (Crossfade Audition)
Let the DJ hear the actual crossfade: last 10s of prev track fading into the candidate, or the candidate fading into the next track. Reuse the `AudioContext` + `GainNode` crossfade pattern from `playback.svelte.ts`.

#### A/B Comparison View
Side-by-side waveforms: current track vs selected candidate, aligned at a beat or cue point. Reuse `TransitionDetail`'s dual-player + `CueOverlay` pattern.

#### Batch Weak Spot Detection
Scan the set for transitions below a threshold (e.g. < 0.5). Highlight them in the timeline with a warning badge. Offer "Fix weak spots" which opens Replace modal for each in sequence.
- New endpoint: `GET /api/sets/{id}/weak-transitions?threshold=0.5`
- Timeline badge on `TransitionIndicator` for low scores

### Tier 3 — Advanced

#### Smart Suggestions (Global Score Delta)
After local scoring (current approach), compute how much the overall set score changes. Sum transition scores with the candidate in place vs the current track. Show the delta: "+0.12 overall improvement".
- New function `score_replacement_global()` — recomputes both adjacent transition scores
- Limit to top-N from local scoring first (performance)

#### Replacement History + Undo
Track every swap in a `ReplacementLog` table (set_id, position, old_track_id, new_track_id, timestamp). Show history in modal footer or SetView panel. One-click revert.
- New DB model, migration, CRUD endpoints

#### Energy Arc Preview
When hovering a candidate, overlay a preview of the new energy curve on the `EnergyFlowChart` — showing how swapping this track changes the set's energy narrative vs the target.

### Existing Architecture (v1)

```
Backend:
  score_replacement()     → scoring.py   (both-neighbor scoring)
  replace_track_in_set()  → store.py     (atomic position swap)
  GET  .../replacements   → sets.py      (candidate search + scoring)
  POST .../replace        → sets.py      (execute swap)

Frontend:
  ReplaceTrackModal.svelte  → modal UI (context bar, candidates, audio preview)
  SetTimeline.svelte        → swap icon trigger on hover
  sets.ts                   → API client (getReplacements, replaceTrackInSet)
```

### Principles to Follow

- **Show the Why**: Every score must be explainable — no black box rankings
- **Your Library Is the Lesson**: Candidates come from the DJ's own collection only
- **The Arc Over the Moment**: Consider the whole set's narrative, not just adjacent tracks
- **Grow the Ear**: Crossfade audition builds the DJ's instinct for transitions
- **Opinions You Can See Through**: Transparent scoring with visible breakdowns

---

# AI Section
<!-- AI stages go below. Do not modify Human Section above. -->

## Stage: CREATE

**Created**: 2026-03-20
**Status**: CREATED
**Branch**: main
**Spec path**: specs/2026/03/sets/006-replace-track-v2.md

### Summary
Evolution of the Replace Track feature from v1 (basic swap with scored candidates) to v2 (waveform previews, crossfade audition, score tooltips, genre filtering, batch weak spot detection, undo history, global score optimization). Three implementation tiers from quick frontend wins to deep backend integration.

### Implementation Order (Suggested)
1. Tier 1: Genre filter → Score tooltip → Waveform preview
2. Tier 2: Crossfade audition → A/B comparison → Batch weak spots
3. Tier 3: Global score delta → Undo history → Energy arc preview

### Dependencies
- v1 complete (commits `00020bd`, `f3e7f68`)
- Existing waveform endpoints, playback store crossfade engine, EnergyFlowChart
- No new external dependencies expected
