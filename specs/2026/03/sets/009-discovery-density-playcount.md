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
<!-- Filled by explicit documentation updates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
