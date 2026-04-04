# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Unify the three energy sources (dir_energy tags, ML predictions, tinder-approved) into a single resolved energy zone per track with clear provenance, using a cascading trust hierarchy: **tinder-approved > dir_energy > ML prediction**. Surface source disagreements as teaching moments in the UI so DJs learn why different signals sometimes conflict.

## Mid-Level Objectives (MLO)

1. **ADD** a resolved energy accessor that returns the highest-trust energy zone per track, following the cascade: approved > dir_energy > predicted
2. **ADD** conflict detection between dir_energy and energy_predicted — expose disagreements via API
3. **UPDATE** `energy_fit()` scoring to use the resolved energy instead of the current fragmented logic
4. **UPDATE** TrackResponse API to include `resolved_energy`, `energy_sources` (all available), and `energy_conflict` flag
5. **UPDATE** the tinder queue to optionally surface tracks where dir_energy and ML disagree (teaching opportunity)
6. **ADD** frontend UI indicator when energy sources disagree — show both values with a "why they differ" explanation
7. **ENSURE** training data pipeline respects the trust hierarchy (approved labels > dir_energy > nothing)

## Details (DT)

### Current State
- `dir_energy` (string): From directory parsing. 975/4,119 tracks. High trust, set at import time.
- `energy_predicted` (string): ML classifier output. 1,970 tracks. Variable confidence.
- `energy_confidence` (float): ML confidence score. 0.0–1.0.
- `energy_source` (string): "manual", "auto", or "approved".
- `audio_features.energy` (float): Raw Essentia energy 0.0–1.0. Not a zone, but a numeric signal.

### Trust Hierarchy
```
tinder-approved (energy_source="approved")  →  confidence: 1.0 (DJ explicitly confirmed/overrode)
dir_energy                                   →  confidence: 0.9 (DJ's own folder structure)
ML prediction (energy_source="auto")         →  confidence: energy_confidence (model's own score)
untagged                                     →  confidence: null (no zone available)
```

### Conflict Scenarios
1. **dir_energy="peak", predicted="warmup"**: Folder says peak, model hears warmup. Teaching moment: "Your folder says peak, but the audio profile suggests warmup — worth a listen?"
2. **dir_energy="build", predicted="build"**: Agreement. High confidence even without tinder.
3. **approved="drive", dir_energy="peak"**: DJ explicitly chose drive via tinder, overriding both folder and model.

### Key Files
- `src/kiku/db/models.py` — Track model (lines 32-63)
- `src/kiku/setbuilder/scoring.py` — `energy_fit()` (lines 102-114)
- `src/kiku/setbuilder/constraints.py` — `ENERGY_TAG_VALUES`, `dir_energy_to_numeric()` (lines 83-127)
- `src/kiku/analysis/autotag.py` — Training data, ZONE_MAP, ENERGY_ZONES
- `src/kiku/api/routes/tinder.py` — Tinder endpoints
- `src/kiku/api/routes/tracks.py` — TrackResponse, search, suggest-next
- `src/kiku/db/store.py` — `save_tinder_decision()` (lines 394-419)

### Constraints
- No new DB columns or migrations — resolved energy is computed, not stored
- Do not break existing set building or tinder flows
- Teaching moments should use Kiku voice (warm, concise, the experienced DJ friend)
- `audio_features.energy` (numeric 0.0–1.0) remains the primary signal for `energy_fit()` scoring — resolved zone is the fallback when audio features are missing

### Testing
- Unit: Test resolved energy accessor with all priority combinations
- Unit: Test conflict detection logic
- API: Test TrackResponse includes new fields
- Integration: Verify set building uses resolved energy correctly

## Behavior

You are implementing a craft-mentorship feature. The merge logic should be invisible when sources agree (just works), but educational when they disagree. Frame disagreements as learning opportunities, not errors. The DJ's explicit choices (tinder) always win. Their folder structure (dir_energy) is their curation signal. The model is the apprentice learning from both.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Current State Analysis

#### The Fragmentation Problem

Kiku has three independent sources of energy zone information for tracks:

| Source | Tracks | Coverage | Trust | How Written |
|--------|--------|----------|-------|-------------|
| `dir_energy` (folder tags) | 990 | 23.9% | High -- DJ's own curation | `sync.py`, `scan.py` from directory names |
| `energy_predicted` (ML) | 2,006 | 48.3% | Low -- 47% model accuracy | `autotag.py` prediction pipeline |
| `energy_source="approved"` (tinder) | 72 | 1.7% | Highest -- DJ explicitly reviewed | `store.py` tinder decision handler |
| No zone data | 1,160 | 28.0% | N/A | -- |

Additionally, `audio_features.energy` (Essentia numeric 0-1) covers 4,097 of 4,150 tracks (98.7%) and is the **primary signal** used by `energy_fit()` scoring. The zone system is a parallel classification layer that rarely affects scoring.

**Overlap is near-zero**: Only 6 tracks have both `dir_energy` AND `energy_predicted`. All 6 disagree. This is by design -- `predict_energy()` filters to tracks WHERE `dir_energy IS NULL`.

#### Where Fragmentation Hurts

1. **API response inconsistency**: `_track_to_response()` sends `energy=t.dir_energy`, `_set_track_response()` sends `energy=(t.dir_energy or t.energy_predicted)`, `build_set_sse()` sends `energy=t.dir_energy`. Three endpoints, three field conventions.

2. **Statistics blindness**: `library_stats()`, `energy_genre_heatmap()`, `enhanced_stats()`, and `library_gaps()` all query ONLY `dir_energy`. This means 48% of the library's ML-predicted energy data is invisible to stats and DNA views.

3. **Frontend duplication**: Three separate `normalizeEnergy()` / `parseEnergy()` functions in `EnergyFlowChart.svelte`, `SetTimeline.svelte`, and `SetTrackCard.svelte` each hardcode the same `ENERGY_LABEL_MAP`.

4. **Seed selection bypass**: `_pick_seed()` in `planner.py` uses `dir_energy_to_numeric(t.dir_energy)` directly, bypassing `resolved_energy_zone`. This means tinder-approved zones and ML predictions are ignored for seed track selection.

5. **3 numeric conversion paths**: `dir_energy_to_numeric()`, `zone_to_numeric()`, and raw `audio_features.energy` overlap but use different lookup approaches. `energy_fit()` has its own inline resolution priority.

### Trust Hierarchy

The existing cascade in `resolve_energy()` (`src/kiku/analysis/autotag.py:49-74`) is well-designed:

```
Priority 1: approved (tinder)  -- confidence from track or 1.0
Priority 2: dir_energy (folder) -- confidence 1.0
Priority 3: predicted (ML auto) -- confidence from model
Priority 4: none               -- (None, "none", 0.0)
```

**Why it's insufficient (despite being correct)**:

1. **Not universally used**: `_pick_seed()`, build SSE events, and stats endpoints bypass it entirely.
2. **Returns zone strings, not numerics**: Consumers that need a 0-1 value must call `zone_to_numeric()` on the result, adding a second step that some callers skip.
3. **Doesn't incorporate `audio_features.energy`**: The raw Essentia signal (which is the most complete source at 98.7%) sits in a completely separate resolution path inside `energy_fit()`.
4. **No composability**: The function returns a 3-tuple `(zone, source, confidence)` which is awkward to use in contexts that just need a number or just need a label.

### Numeric vs Zone Duality

This is the fundamental tension in the energy system:

| Aspect | `audio_features.energy` (numeric) | Zone System (zone labels) |
|--------|-----------------------------------|--------------------------|
| Coverage | 98.7% (4,097 tracks) | 72.0% (2,990 tracks via dir_energy OR predicted) |
| Precision | Continuous 0-1 | 5 discrete buckets |
| Provenance | Essentia analysis (automated) | DJ curation + ML + tinder |
| Used by scoring | PRIMARY signal in `energy_fit()` | FALLBACK when audio features missing |
| Used by display | Never shown to user directly | Shown as zone labels, colored badges |
| Trust level | Objective (algorithmic) | Subjective (DJ taste) |
| Teaching value | Low (opaque number) | High (named zones with stories) |

**The duality is a feature, not a bug.** The numeric value is for scoring precision. The zone label is for human understanding. The merge should not collapse these into one -- it should connect them properly.

The current disconnect is that:
- `energy_fit()` uses the numeric path and rarely touches zones
- The UI shows zone labels that aren't used in scoring
- The DJ sees "warmup" but the scorer sees "0.23" (from Essentia), and these may not agree
- There's no place where the DJ can see: "Essentia says 0.23, which maps to warmup territory -- and your folder agrees"

### Consumer Impact Analysis

Based on the audit of 47 consumer sites across 38 backend files and 26 frontend files:

#### Already Zone-Agnostic (no changes needed)
- `energy_fit()` -- already does proper fallback (audio_features > resolved zone > 0.5)
- `transition_score()`, `score_replacement()`, `score_transitions()` -- delegate to `energy_fit()`
- `EnergyProfile`, `EnergySegment`, presets -- deal with target curves, not track energy
- Audio analysis (`analyzer.py`) -- writes `audio_features.energy`, not zones
- `TrackFeatures` API endpoint -- returns raw audio features
- `audio-preload.ts` -- no energy logic

#### Need Consistency Fixes (use resolved energy instead of raw fields)

| Consumer | Current Behavior | Fix |
|----------|-----------------|-----|
| `_pick_seed()` | Uses `dir_energy_to_numeric()` only | Use resolved zone numeric |
| `_set_track_response()` | `energy=(t.dir_energy or t.energy_predicted)` | Use `resolved_energy_zone` |
| `set_waveforms()` | Same OR pattern | Use `resolved_energy_zone` |
| `build_set_sse()` | `energy=t.dir_energy` only | Use `resolved_energy_zone` |
| `library_stats()` | Queries `dir_energy` only | Query resolved zones |
| `energy_genre_heatmap()` | `dir_energy` only | Query resolved zones |
| `enhanced_stats()` | `dir_energy` with 3-zone grouping | Query resolved zones with 5-zone grouping |
| `library_gaps()` | `dir_energy` only | Query resolved zones |
| CLI `search`, `build`, `show`, `stats` | Display `t.dir_energy or "?"` | Display resolved zone |

#### Frontend Deduplication Needed

| Component | Function | Action |
|-----------|----------|--------|
| `EnergyFlowChart.svelte` | `normalizeEnergy()` | Replace with shared utility |
| `SetTimeline.svelte` | `parseTrackEnergy()` | Replace with shared utility |
| `SetTrackCard.svelte` | `parseEnergy()` + `normalizedEnergy()` + `energyBarColor()` | Replace with shared utility |

#### Must Preserve Existing Behavior (high-risk consumers)
- **Tinder queue**: Filters by `energy_source == "auto"`. The `energy_source` field must remain.
- **Autotag training**: Uses `dir_energy` as ground truth labels. Must continue to distinguish source provenance.
- **`energy_conflict` detection**: Compares `dir_energy` vs `energy_predicted` raw fields. Source fields must remain.
- **Search filters**: `energy` param matches `dir_energy`, `energy_zone` param matches canonical zones. Both are useful.

### ML Model Assessment

#### Performance Reality

| Metric | Value | Assessment |
|--------|-------|-----------|
| Overall accuracy | 47.1% | Slightly better than random for 5 classes (20% baseline) |
| F1 macro-avg | 0.244 | Poor -- heavily skewed by class imbalance |
| "build" F1 | 0.57 | Acceptable for the majority class |
| "drive" F1 | 0.42 | Marginal |
| "warmup" F1 | 0.18 | Poor |
| "peak" F1 | 0.04 | Useless |
| "close" F1 | 0.00 | Zero -- only 2 training samples |

#### Root Causes
1. **Class imbalance**: 466 build vs 2 close training samples. `class_weight="balanced"` helps but can't overcome 233:1 ratios.
2. **Feature limitation**: 12 audio features can distinguish high/low energy but struggle with the semantic zones (warmup vs close have similar energy levels but different musical roles).
3. **Zone boundary ambiguity**: "build" (0.55) and "drive" (0.72) overlap significantly in audio features.

#### Recommendation: Keep but Demote

- **Do NOT retrain** -- more training data from tinder is the bottleneck, not the algorithm
- **Do NOT deprecate** -- it provides some signal for 48% of the library that has no other zone data
- **DO mark as low-trust** -- show ML predictions with a visible "estimated" indicator
- **DO prioritize tinder reviews** -- 72 approved vs 1,934 in queue. Each tinder decision is worth more than model improvements
- **DO consider zone simplification** -- merging "close" into "warmup" would eliminate the worst-performing class (both are low-energy, the distinction is positional not timbral)

### Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Stats endpoints show different numbers after including ML data | High | Low | Expected change -- document that stats now include all sources |
| `_pick_seed()` change alters set building behavior | Medium | Medium | ML-predicted zones are noisy, but `audio_features.energy` still takes priority |
| Frontend `normalizeEnergy()` dedup introduces rendering bugs | Low | Low | Values are the same lookup table in all 3 components |
| Tinder queue filtering breaks | Low | High | `energy_source` field is preserved, no schema changes |
| `energy_conflict` detection changes | Low | Medium | Source fields (`dir_energy`, `energy_predicted`) are preserved |

#### Backward Compatibility

- **API responses**: Adding `resolved_energy` to endpoints that lack it is additive. Keeping `energy` field as `dir_energy` preserves backward compat. Phase this: add `resolved_energy` first, deprecate inconsistent `energy` field later.
- **CLI output**: Switching from `dir_energy or "?"` to resolved zone is a display change. Show source indicator: `"build (folder)"` vs `"build (estimated)"`.
- **Database**: No schema changes per spec constraint. All changes are at the application layer.

### Gap Analysis: Spec vs Implementation

The spec's 7 MLOs map to current implementation status:

| MLO | Status | Remaining Work |
|-----|--------|----------------|
| 1. Resolved energy accessor with cascade | **DONE** -- `resolve_energy()` in autotag.py, `resolved_energy_zone` property on Track | None |
| 2. Conflict detection via API | **DONE** -- `detect_energy_conflict()`, `energy_conflict` in TrackResponse | None |
| 3. `energy_fit()` uses resolved energy | **MOSTLY DONE** -- uses resolved zone as fallback; `_pick_seed()` still bypasses it | Fix `_pick_seed()` |
| 4. TrackResponse includes resolved fields | **PARTIALLY DONE** -- `_track_to_response()` has all fields; `_set_track_response()` and `set_waveforms()` are inconsistent | Unify API responses |
| 5. Tinder queue surfaces conflicts | **DONE** -- `include_conflicts` param, `SetEnergyReview` modal | None |
| 6. Frontend conflict UI indicator | **DONE** -- `EnergyConflictBadge.svelte` | None |
| 7. Training pipeline respects trust | **DONE** -- `_load_training_data()` uses dir_energy + approved | None |

**What remains is not new features but consistency and cleanup**:
1. Make all API endpoints use the same resolved energy logic
2. Fix `_pick_seed()` to use the cascade
3. Update stats to include ML-predicted data
4. Deduplicate frontend normalizeEnergy
5. Add source provenance to CLI display
6. Unify the 3 numeric conversion paths into one

## Plan

### Unified Energy Model Design

#### Core Principle: Compute, Don't Store

Per the spec constraint ("No new DB columns or migrations -- resolved energy is computed, not stored"), the unified model is a **utility layer**, not a schema change.

#### Single Source of Truth: `get_track_energy()`

Create a new central utility function that all consumers use:

```python
# src/kiku/energy.py (new module)

from kiku.analysis.autotag import resolve_energy, ZONE_MAP
from kiku.setbuilder.constraints import zone_to_numeric

def get_track_energy(track: Track) -> TrackEnergy:
    """Unified energy resolution for a track.

    Returns a TrackEnergy dataclass with:
    - zone: str | None  (canonical zone name)
    - numeric: float    (0-1 value, always available)
    - source: str       (provenance: "approved", "dir_energy", "predicted", "audio", "none")
    - confidence: float (0-1, trust level)
    - label: str        (human-readable: "build (folder)", "drive (estimated)")
    """
    zone, source, confidence = resolve_energy(track)

    # Numeric resolution priority:
    # 1. audio_features.energy (raw Essentia, highest precision)
    # 2. zone_to_numeric(resolved_zone) (from cascade)
    # 3. 0.5 (neutral fallback)
    if track.audio_features and track.audio_features.energy is not None:
        numeric = track.audio_features.energy
        if zone is None:
            # Derive zone from numeric value for display
            zone = numeric_to_zone(numeric)
            source = "audio"
    else:
        numeric = zone_to_numeric(zone) if zone else 0.5
        if zone is None:
            source = "none"

    label = _format_label(zone, source)

    return TrackEnergy(
        zone=zone,
        numeric=numeric,
        source=source,
        confidence=confidence,
        label=label,
    )
```

#### Zone-from-Numeric Derivation

When a track has `audio_features.energy` but no zone data (1,160 tracks), derive a zone label from the numeric value. This is explicitly a **computed approximation**, not a classification:

```python
def numeric_to_zone(energy: float) -> str:
    """Derive zone label from numeric energy value.

    Boundaries match the ENERGY_TAG_VALUES midpoints:
    warmup: 0.0-0.40, build: 0.40-0.63, drive: 0.63-0.80, peak: 0.80-1.0
    close: not derivable from numeric alone (it's positional, not energetic)
    """
    if energy < 0.40:
        return "warmup"
    elif energy < 0.63:
        return "build"
    elif energy < 0.80:
        return "drive"
    else:
        return "peak"
```

This is intentionally opinionated and visible ("Opinions You Can See Through"). The thresholds come directly from the existing `ENERGY_TAG_VALUES` midpoints.

#### Human-Readable Labels

Labels communicate provenance ("Show the Why"):

| Source | Label Example |
|--------|---------------|
| `approved` | `"drive"` (no qualifier -- DJ confirmed) |
| `dir_energy` | `"build (folder)"` |
| `predicted` | `"peak (estimated)"` |
| `audio` | `"warmup (from audio)"` |
| `none` | `"unknown"` |

### Database Changes

**None.** Per spec constraint, resolved energy remains computed. The existing schema fields are preserved:

- `tracks.dir_energy` -- kept, still written by sync/scan
- `tracks.energy_predicted` -- kept, still written by autotag/tinder
- `tracks.energy_confidence` -- kept
- `tracks.energy_source` -- kept
- `audio_features.energy` -- kept
- `set_tracks.inferred_energy` / `inference_source` -- kept (Phase 2 placeholder)

#### Why No New Columns Is Correct

1. **Denormalized `energy_value` would go stale** -- any sync, autotag, or tinder decision would need to recompute it, creating a cache invalidation problem.
2. **Computation is cheap** -- `resolve_energy()` is a few attribute lookups, no queries.
3. **Source provenance matters** -- consumers need to know WHY a value was chosen, not just the value. A single column loses this.
4. **Phase 2 needs flexibility** -- Set Analysis will add position-based inference, which is per-set-track, not per-track. The Track-level resolution and SetTrack-level inference are fundamentally different.

### Backend Changes

#### New Module: `src/kiku/energy.py`

Central energy utilities replacing the scattered conversion functions:

```
get_track_energy(track) -> TrackEnergy    # unified resolution (replaces inline logic)
numeric_to_zone(energy) -> str            # numeric -> zone label
format_energy_label(zone, source) -> str  # human-readable label
```

#### Files to Modify

| File | Change | Effort |
|------|--------|--------|
| `src/kiku/setbuilder/scoring.py` | `energy_fit()` calls `get_track_energy().numeric` instead of inline resolution | Small |
| `src/kiku/setbuilder/planner.py` | `_pick_seed()` calls `get_track_energy().numeric` instead of `dir_energy_to_numeric()` | Small |
| `src/kiku/api/routes/tracks.py` | `_track_to_response()` uses `get_track_energy()` for all energy fields | Small |
| `src/kiku/api/routes/sets.py` | `_set_track_response()`, `set_waveforms()`, `build_set_sse()`, `_track_response()` all use `get_track_energy()` | Medium |
| `src/kiku/analysis/insights.py` | `library_stats()`, `energy_genre_heatmap()`, `enhanced_stats()`, `library_gaps()` query resolved zones not just `dir_energy` | Medium |
| `src/kiku/db/store.py` | `library_stats()` includes ML-predicted zones in counts | Small |
| `src/kiku/cli.py` | Display commands show resolved zone + source indicator | Small |

#### Files NOT to Modify
- `src/kiku/analysis/autotag.py` -- `resolve_energy()` stays as-is (it's the core cascade)
- `src/kiku/db/scan.py`, `src/kiku/db/sync.py` -- write `dir_energy` as before
- `src/kiku/api/routes/tinder.py` -- tinder flow is already correct
- `src/kiku/setbuilder/constraints.py` -- `ENERGY_TAG_VALUES`, `dir_energy_to_numeric()`, `zone_to_numeric()` stay as backward-compat utilities

#### `_pick_seed()` Fix

The current implementation bypasses the cascade:

```python
# CURRENT (inconsistent):
if t.audio_features and t.audio_features.energy is not None:
    return abs(t.audio_features.energy - target)
e = dir_energy_to_numeric(t.dir_energy)  # ignores approved + predicted!

# FIXED (uses unified resolution):
te = get_track_energy(t)
return abs(te.numeric - target)
```

#### Stats Endpoint Fix

The stats endpoints currently count only `dir_energy` tags, missing 48% of the library. After the fix:

```python
# CURRENT:
# Queries Track.dir_energy directly -- misses ML predictions

# FIXED:
# For each track, resolve energy zone via get_track_energy()
# Group by zone for stats
# Track provenance for transparency: "990 from folders, 1,934 estimated, 72 confirmed"
```

Note: This will change stats numbers. The "Energy Zone Breakdown" will go from showing ~990 tracks to ~2,990+ tracks. This is correct -- the previous stats were hiding half the library.

### Frontend Changes

#### Shared Energy Utility Module

Create `frontend/src/lib/utils/energy.ts`:

```typescript
// Zone-to-numeric mapping (single source of truth)
export const ENERGY_VALUES: Record<string, number> = {
  low: 0.2, warmup: 0.25, closing: 0.35, close: 0.35,
  mid: 0.5, build: 0.55, dance: 0.6,
  up: 0.7, drive: 0.72, high: 0.75,
  fast: 0.85, peak: 0.9,
};

export function normalizeEnergy(energy: string | null | undefined): number {
  if (!energy) return 0.5;
  return ENERGY_VALUES[energy.toLowerCase()] ?? 0.5;
}

export function energyColor(value: number): string {
  if (value < 0.4) return 'var(--energy-low)';    // green
  if (value < 0.65) return 'var(--energy-mid)';   // orange
  return 'var(--energy-high)';                     // red
}
```

#### Components to Update

| Component | Change |
|-----------|--------|
| `EnergyFlowChart.svelte` | Import from `energy.ts`, remove local `normalizeEnergy()` and `ENERGY_LABEL_MAP` |
| `SetTimeline.svelte` | Import from `energy.ts`, remove local `parseTrackEnergy()` and `ENERGY_LABEL_MAP` |
| `SetTrackCard.svelte` | Import from `energy.ts`, remove local `parseEnergy()`, `normalizedEnergy()`, `energyBarColor()` |
| `TrackTable.svelte` | Display `track.resolved_energy ?? track.energy ?? '?'` with source indicator |
| `SearchFilters.svelte` | Consider adding "Zone (all sources)" filter using `resolved_energy` |

#### Display Upgrades

- Show source indicator in track details: a small label ("folder", "estimated", "confirmed") next to zone badges
- When `energy_confidence < 0.6` for predicted tracks, show a subtle uncertainty indicator (e.g., dashed border on zone badge)
- This aligns with "Opinions You Can See Through" -- DJs see exactly where the zone comes from

### API Changes

#### Unified Energy Fields in All Track Responses

Every endpoint returning track data should include:

```json
{
  "energy": "Peak",
  "resolved_energy": "peak",
  "energy_value": 0.87,
  "energy_source": "dir_energy",
  "energy_confidence": 1.0,
  "energy_label": "peak (folder)",
  "energy_conflict": null
}
```

#### Endpoints to Standardize

| Endpoint | Current | After |
|----------|---------|-------|
| `_track_to_response()` | Has `resolved_energy`, `energy_source`, `energy_confidence`, `energy_conflict` | Add `energy_value`, `energy_label` |
| `_set_track_response()` | `energy=(dir_energy or predicted)`, `energy_source`, `energy_conflict` | Add `resolved_energy`, `energy_value`, `energy_confidence`, `energy_label` |
| `set_waveforms()` | Same as set track | Same additions |
| `build_set_sse()` track_added | `energy=dir_energy` only | Add `resolved_energy`, `energy_value`, `energy_source` |
| `_track_response()` (replace) | Has full fields | Add `energy_value`, `energy_label` |

#### New Schema Fields

Add to `TrackResponse` (Pydantic model):
- `energy_value: float | None` -- unified numeric energy
- `energy_label: str | None` -- human-readable zone + source

Add to `SetTrackResponse` / `WaveformTrackResponse`:
- `resolved_energy: str | None`
- `energy_value: float | None`
- `energy_confidence: float | None`
- `energy_label: str | None`

### Migration Strategy

Since there are no database changes, migration is purely at the application layer:

#### Step 1: Add Utility Module
Create `src/kiku/energy.py` with `get_track_energy()`, `numeric_to_zone()`, `format_energy_label()`. This is additive and breaks nothing.

#### Step 2: Wire API Responses
Update Pydantic schemas and response builders to include new fields. All new fields are optional/nullable, so existing clients are unaffected.

#### Step 3: Fix Inconsistencies
Update `_pick_seed()`, stats endpoints, and CLI display to use the unified utility. This changes behavior but in predictable ways (more data included, better resolution).

#### Step 4: Frontend Deduplication
Replace 3 inline normalizers with shared utility. This is a refactor with identical output.

#### Rollback Safety
Every step is independently deployable and reversible. No database changes mean rollback is just reverting code.

### Implementation Phases

#### Phase A: Core Utility + Scoring Fix (~30 min)

1. Create `src/kiku/energy.py` with `TrackEnergy` dataclass and `get_track_energy()`
2. Add `numeric_to_zone()` with documented thresholds
3. Add `format_energy_label()` for human-readable labels
4. Update `energy_fit()` to use `get_track_energy().numeric`
5. Fix `_pick_seed()` to use `get_track_energy().numeric`
6. Add tests for `get_track_energy()` with all source combinations

**Why first**: This is the highest-value change. It fixes the `_pick_seed()` bug and establishes the single utility that all subsequent changes build on.

#### Phase B: API Consistency (~45 min)

1. Add `energy_value`, `energy_label` to `TrackResponse` schema
2. Add `resolved_energy`, `energy_value`, `energy_confidence`, `energy_label` to set track schemas
3. Update `_track_to_response()` to use `get_track_energy()`
4. Update `_set_track_response()` to use `get_track_energy()`
5. Update `set_waveforms()` to use `get_track_energy()`
6. Update `build_set_sse()` track_added events
7. Update `_track_response()` (replace endpoint)
8. Add API tests for new fields

**Why second**: Frontend changes depend on the API providing consistent data.

#### Phase C: Stats + CLI (~30 min)

1. Update `library_stats()` to include resolved zones from all sources
2. Update `energy_genre_heatmap()` to use resolved zones
3. Update `enhanced_stats()` to use 5-zone grouping (not 3) with resolved zones
4. Update `library_gaps()` to use resolved zones
5. Update CLI display commands to show resolved zone + source indicator
6. Update CLI `search` energy display

**Why third**: Stats changes will alter visible numbers -- best done after core + API are stable.

#### Phase D: Frontend Dedup + Display (~45 min)

1. Create `frontend/src/lib/utils/energy.ts` with shared utilities
2. Refactor `EnergyFlowChart.svelte` to use shared utility
3. Refactor `SetTimeline.svelte` to use shared utility
4. Refactor `SetTrackCard.svelte` to use shared utility
5. Update `TrackTable.svelte` to show `resolved_energy` with source indicator
6. Add low-confidence visual indicator for predicted tracks
7. Type-check: `cd frontend && npx svelte-check`

**Why last**: Frontend is the presentation layer -- do it after data layer is consistent.

### Testing Plan

#### Unit Tests (src/kiku/energy.py)

| Test Case | Expected |
|-----------|----------|
| Track with approved + dir_energy + predicted | Returns approved zone, confidence from track |
| Track with dir_energy only | Returns dir_energy zone, confidence 1.0, source "dir_energy" |
| Track with predicted only (auto) | Returns predicted zone, confidence from model, source "predicted" |
| Track with audio_features.energy only (no zone) | Returns derived zone, numeric from Essentia, source "audio" |
| Track with no energy data at all | Returns None zone, 0.5 numeric, source "none" |
| Track with audio_features + dir_energy | Returns dir_energy zone (trust), Essentia numeric (precision) |
| Track with approved zone + audio_features disagree | Returns approved zone, Essentia numeric |
| `numeric_to_zone()` boundary values | 0.0 -> warmup, 0.39 -> warmup, 0.40 -> build, 0.63 -> drive, 0.80 -> peak |
| `format_energy_label()` all sources | Correct labels for each provenance type |

#### Integration Tests (API)

| Test Case | Expected |
|-----------|----------|
| `GET /api/tracks/search` response includes `energy_value` | Float present for tracks with audio features |
| `GET /api/sets/{id}` tracks include `resolved_energy`, `energy_value` | Consistent fields in set context |
| Set waveform response has same energy fields as set track response | Field parity |
| Build SSE track_added events include `resolved_energy` | Not just raw `dir_energy` |

#### Regression Tests

| Test Case | Expected |
|-----------|----------|
| Set building produces similar results after `_pick_seed()` fix | Verify seed selection is not dramatically different (energy values should be similar since audio_features dominates) |
| Tinder queue still filters by `energy_source == "auto"` | No change in tinder behavior |
| Autotag training still uses `dir_energy` as ground truth | No change in training pipeline |
| Conflict detection still works | `energy_conflict` returns same results |

#### Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Track with `dir_energy="Peak"` but `audio_features.energy=0.15` | Zone = "peak" (from folder), numeric = 0.15 (from Essentia). This disagreement is valid -- the DJ put it in Peak folder, but the audio is quiet. Not an error. |
| Track where `dir_energy` tag is not in ZONE_MAP | Falls through to predicted or none |
| Track with `energy_source="manual"` (never used in practice) | Treated same as approved (explicit human decision) |
| `energy_confidence=0.0` for auto-predicted | Still returns the prediction, but with 0.0 confidence visible to consumer |

### Decisions Requiring User Input

1. **Close zone handling**: Should "close" be merged into "warmup" for ML purposes (both are low-energy)? The model has 0.0 F1 on close. This is a product decision about whether close is a meaningful category or a positional one.
2. **Stats breakage notification**: The stats endpoints will show ~3x more tracks after including ML predictions. Should there be a visual indicator that stats now include estimated data?
3. **`energy_source="manual"` cleanup**: This value is defined but never used. Remove it from the codebase or repurpose it for manual overrides outside tinder?

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

### TODO

- [x] **A1**: Create `src/kiku/energy.py` — `TrackEnergy` dataclass, `get_track_energy()`, `numeric_to_zone()`, `format_energy_label()` | Status: Done
- [x] **A2**: Fix `_pick_seed()` in `planner.py` to use `get_track_energy()` | Status: Done
- [x] **A3**: Unit tests for `energy.py` (23 tests passing) | Status: Done
- [x] **B1**: Add `energy_value`, `energy_label` to API response schemas | Status: Done
- [x] **B2**: Update `_track_to_response()` in `tracks.py` to use `get_track_energy()` | Status: Done
- [x] **B3**: Update `_set_track_response()`, `set_waveforms()`, `build_set_sse()`, `_track_response()` in `sets.py` | Status: Done
- [x] **B4**: API tests — 54 existing tests pass, new fields additive | Status: Done
- [x] **C1**: Update `library_stats()`, `energy_genre_heatmap()`, `enhanced_stats()`, `library_gaps()` to use resolved zones | Status: Done
- [x] **C2**: Update CLI display (search, show set, show track) to show resolved zone with source label | Status: Done
- [x] **D1**: Create `frontend/src/lib/utils/energy.ts` shared utility | Status: Done
- [x] **D2**: Refactor `EnergyFlowChart.svelte`, `SetTimeline.svelte`, `SetTrackCard.svelte` to use shared utility | Status: Done
- [x] **D3**: Type-check frontend — 0 errors, 1 pre-existing warning | Status: Done

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
