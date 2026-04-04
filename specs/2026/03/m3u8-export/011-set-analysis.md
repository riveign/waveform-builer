# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Analyze imported sets to teach DJs why their freestyle sessions work. Phase 2 of the Import → Analyze → Build feature: score every transition in an imported set using the existing 5-dimension scoring system, compute arc-level analysis (energy flow, key progression, BPM drift), generate teaching moments that explain *why* each transition succeeds or struggles, and infer energy zones for untagged tracks based on their position in the set. The DJ sees their own instincts reflected back with language — turning "I felt it" into "here's what your ear already knows."

## Mid-Level Objectives (MLO)

- CREATE `src/kiku/analysis/set_analyzer.py` — orchestrator that takes a set ID and produces a full `SetAnalysis` result
- IMPLEMENT per-transition scoring: iterate all adjacent pairs, call existing `harmonic_score`, `bpm_compatibility`, `genre_coherence`, `energy_fit`, `track_quality` — store as `TransitionAnalysis` objects
- IMPLEMENT arc analysis across the full set:
  - **Energy arc**: plot resolved energy zone per track position, detect ramp-ups, plateaus, dips, and recoveries
  - **Key progression**: track Camelot wheel movement, identify key journeys (staying close vs. adventurous leaps)
  - **BPM drift**: compute BPM delta across the set, flag large jumps vs. smooth rides
  - **Genre flow**: detect genre clustering, deliberate switches, and genre journey patterns
- IMPLEMENT teaching moments engine (`src/kiku/analysis/teaching.py`):
  - For each transition, generate 1-2 sentence explanations: "This works because both tracks share the same Camelot key and the energy steps up naturally"
  - Flag weak transitions with constructive suggestions: "The BPM jump here is 12% — try a track around 128 BPM to bridge the gap"
  - Identify set-level patterns: "You tend to build energy through key changes rather than BPM — that's a signature move"
- IMPLEMENT energy inference from position (`inferred_energy` / `inference_source` columns on `set_tracks`):
  - For tracks without energy tags, infer energy from neighboring tracks and set position
  - Write inferred values to `set_tracks.inferred_energy` with `inference_source = "position"`
  - Never overwrite existing energy data from tags or tinder
- ADD API endpoint `GET /api/sets/{set_id}/analysis` — returns full `SetAnalysisResponse`
- ADD API endpoint `POST /api/sets/{set_id}/analyze` — triggers analysis, stores result in `sets.analysis_cache`, sets `is_analyzed = 1`
- ADD CLI command `kiku analyze <set>` — runs analysis, prints summary to terminal with teaching moments
- CREATE frontend `SetAnalysisView.svelte` — display transition scores, arc charts, and teaching moments
- UPDATE `sets.analysis_cache` column (already exists from spec 010 migration) to store JSON analysis blob
- ENSURE analysis is re-runnable: re-analyzing overwrites previous cache
- ADD tests: unit tests for teaching moment generation, integration tests for the analysis pipeline

## Details (DT)

### Data Structures

```python
@dataclass
class TransitionAnalysis:
    position: int  # index in set (0 = first transition)
    track_a_id: int
    track_b_id: int
    scores: dict  # {harmonic, energy_fit, bpm_compat, genre_coherence, track_quality, total}
    teaching_moment: str  # 1-2 sentence explanation
    suggestion: str | None  # constructive suggestion if score < threshold

@dataclass
class ArcAnalysis:
    energy_curve: list[float]  # energy value per track position
    energy_shape: str  # "ramp-up", "peak-valley", "flat", "roller-coaster", etc.
    key_journey: list[str]  # Camelot keys in order
    key_style: str  # "home-key", "adventurous", "chromatic walk"
    bpm_range: tuple[float, float]  # min, max BPM in set
    bpm_drift: float  # total BPM change start→end
    bpm_style: str  # "steady", "gradual build", "volatile"
    genre_segments: list[dict]  # [{genre_family, start_pos, end_pos}]

@dataclass
class SetAnalysis:
    set_id: int
    track_count: int
    transition_count: int
    transitions: list[TransitionAnalysis]
    arc: ArcAnalysis
    overall_score: float  # weighted average of all transition scores
    set_patterns: list[str]  # set-level teaching observations
    analyzed_at: str  # ISO timestamp
```

### Teaching Moments Rules

Teaching moments follow the craft mentorship voice from BRANDING.md:
- **Strong transition (score ≥ 0.8)**: Celebrate and explain — "Clean key match (both 8A) with a gentle energy lift. Your ear picked this."
- **Good transition (0.6–0.8)**: Acknowledge and note — "The key shift from 5B to 6B keeps it moving. The BPM bump adds urgency."
- **Weak transition (< 0.6)**: Constructive, never blaming — "Big energy drop here — consider a bridge track to smooth the landing."
- **Set-level patterns**: "You built this set's energy through key changes more than BPM — that's a melodic builder's instinct."

### Energy Inference Logic

For tracks in a set that lack energy tags:
1. Check neighbors: if both neighbors have energy, interpolate
2. Check position ratio: early set → warmup zone, mid → build/drive, late → peak/close
3. Combine position heuristic with neighbor data when available
4. Write to `set_tracks.inferred_energy` (0.0–1.0 float) and `inference_source = "position"` or `"interpolation"`

### Existing Infrastructure

- `src/kiku/setbuilder/scoring.py` — `harmonic_score`, `bpm_compatibility`, `genre_coherence`, `energy_fit`, `track_quality`
- `src/kiku/setbuilder/camelot.py` — Camelot wheel utilities
- `src/kiku/api/routes/sets.py` — existing per-transition endpoint at `GET /{set_id}/transition/{index}`
- `sets.analysis_cache` TEXT column — already exists (spec 010 migration)
- `set_tracks.inferred_energy` FLOAT + `set_tracks.inference_source` VARCHAR — already exist (spec 010 migration)
- Energy zones: warmup, build, drive, peak, close (5 zones)

### Constraints

- Analysis MUST use existing scoring functions — do not duplicate scoring logic
- Teaching moment text MUST follow BRANDING.md voice guide (warm, concise, never blame the DJ)
- Analysis cache is JSON — keep it denormalized for fast reads, re-compute on demand
- Frontend arc visualization can use simple SVG or existing chart patterns (energy flow chart exists in set view)
- Analysis should handle sets of any size (2–100+ tracks) gracefully

### Testing

- Unit tests for teaching moment generation (strong/good/weak transitions)
- Unit tests for energy inference (interpolation, position-based, edge cases)
- Unit tests for arc classification (energy shape, key style, bpm style)
- Integration test: analyze a real imported set end-to-end
- Integration test: API endpoint returns valid SetAnalysisResponse

## Behavior

You are a senior AI engineer building a teaching tool for DJs. Every piece of analysis output should help the DJ understand *why* their instincts work — not just produce a score. Follow the craft mentorship tone: warm, direct, concise. Wisdom fits in a sentence. Frame set building as storytelling, not optimization.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Existing Scoring Infrastructure

All 5 scoring dimensions live in `src/kiku/setbuilder/scoring.py`:
- `harmonic_score(key_a, key_b)` → 1.0 (same), 0.85 (adjacent), 0.8 (mode switch), 0.5 (+/-2), 0.2 (clash) — in `camelot.py:68`
- `bpm_compatibility(bpm_a, bpm_b)` → 1.0–0.7 (±6%), 0.6 (double/half), 0.3 (±12%), 0.1 (beyond) — `scoring.py:155`
- `genre_coherence(genre_a, genre_b)` → 1.0/0.8/0.5/0.2 via `GENRE_FAMILIES` + `COMPATIBLE_FAMILIES` — `scoring.py:183`
- `energy_fit(track, target_energy)` → `max(0, 1 - diff*2)` — `scoring.py:207`
- `track_quality(track, ...)` → rating(40%) + play_familiarity(20%) + set_density(10%) + playlist(30%) — `scoring.py:227`
- `transition_score()` combines all 5 with configurable weights (default: harmonic 25%, energy 20%, BPM 20%, genre 15%, quality 20%) — `scoring.py:294`
- `score_replacement()` scores against both neighbors (incoming + outgoing) — `scoring.py:324`

Key insight: `transition_score()` takes a `target_energy` parameter (default 0.5) — for set analysis, we should compute target energy *from the set's actual energy curve* rather than using a neutral value. This makes energy_fit contextual to the set's narrative.

### Per-Transition API Already Exists

`GET /api/sets/{set_id}/transition/{index}` at `src/kiku/api/routes/sets.py:422` already computes score breakdown for a single transition. However:
- It uses a neutral `target_energy=0.5` hardcoded for display
- It requires individual calls per transition (N-1 calls for N tracks)
- No teaching moments or arc analysis

The set analysis endpoint should batch all transitions in one call and use position-aware target energy.

### Energy Resolution Chain

`Track.resolved_energy_zone` property (`models.py:68`) delegates to `analysis/autotag.py:resolve_energy()`:
- Priority: approved > dir_energy > predicted > None
- Returns `(zone, source, confidence)` tuple
- Zone names: warmup, build, drive, peak, close
- Numeric mapping in `constraints.py:84`: warmup=0.25, build=0.55, drive=0.72, peak=0.9, close=0.35

For set analysis energy inference: tracks *without* any energy source get values from set position + neighbor interpolation, written to `set_tracks.inferred_energy` / `inference_source`.

### DB Schema (Already Migrated)

`Set` model (`models.py:122`):
- `analysis_cache = Column(Text)` — JSON blob, ready for use
- `is_analyzed = Column(Integer, default=0)` — flag

`SetTrack` model (`models.py:139`):
- `inferred_energy = Column(Float)` — 0.0–1.0
- `inference_source = Column(String)` — "position", "interpolation"
- `transition_score = Column(Float)` — already exists (from build)

No migration needed. All columns exist from spec 010.

### Frontend Components (Reuse Opportunities)

- `EnergyFlowChart.svelte` — Chart.js line chart showing energy per track position. Already maps zone labels to numeric values. Can be extended to show analysis overlay (target curve vs. actual)
- `ScoreBreakdown.svelte` — Per-dimension bar chart with teaching notes. Already has a `TEACHING` map with 3-tier messages (high/mid/low). The set analysis teaching moments should follow this pattern but be more contextual.
- `TransitionDetail.svelte` — Shows waveforms + score breakdown for a transition pair
- `SetView.svelte` — Main set view with timeline, could host an "Analysis" tab/section
- `TransitionIndicator.svelte` — Color-coded transition quality between tracks in timeline

### Existing Analysis Module

`src/kiku/analysis/` contains:
- `autotag.py` — Energy zone resolver, ML classifier, tinder approval
- `analyzer.py` — Audio analysis pipeline (Essentia/Librosa features)
- `insights.py` — Existing but unexplored (potential home for teaching logic?)

The new `set_analyzer.py` fits naturally in this module. Teaching moments could go in a separate `teaching.py` for clarity.

### Test Patterns

- Unit tests use `MagicMock` for Track objects (`test_scoring.py:55`)
- API tests use `conftest.py` fixtures with in-memory SQLite, seeded tracks/sets (`tests/api/conftest.py`)
- Existing seed data: 20 tracks, 1 set with 5 tracks (positions 1-5), tracks have BPM/key/genre/energy
- Test patterns: direct function calls for unit tests, `TestClient` for API integration

The conftest already has a 5-track set — perfect for testing analysis. May need to add more varied tracks (different keys, genres, energies) for arc analysis tests.

### Strategy

**Module structure:**
1. `src/kiku/analysis/set_analyzer.py` — main `analyze_set()` function, orchestrates scoring + arc + teaching
2. `src/kiku/analysis/teaching.py` — teaching moment generator (per-transition + set-level patterns)
3. API: `POST /api/sets/{set_id}/analyze` (trigger) + `GET /api/sets/{set_id}/analysis` (read cache)
4. CLI: `kiku analyze <set>` — calls `analyze_set()`, prints summary
5. Frontend: `SetAnalysisView.svelte` — tab/section in SetView, reuses EnergyFlowChart + ScoreBreakdown

**Key design decisions:**
- Use existing `transition_score()` with position-derived `target_energy` (not neutral 0.5)
- Energy inference writes to `set_tracks` rows — persistent, re-computable
- Analysis cache is full JSON blob in `sets.analysis_cache` — denormalized for fast reads
- Teaching moments are generated from score breakdown + Camelot context, not stored separately
- Arc classification uses simple heuristics (no ML needed — pattern matching on energy/key/BPM sequences)

**Testing strategy:**
- Unit tests (`tests/test_set_analysis.py`):
  - Teaching moment generation: strong (≥0.8), good (0.6–0.8), weak (<0.6) transitions
  - Energy inference: interpolation between neighbors, position-based fallback, edge cases (first/last track)
  - Arc classification: energy shape detection, key style, BPM drift
  - 8–10 test cases
- API integration tests (`tests/api/test_analysis_api.py`):
  - POST analyze → sets is_analyzed=1 and populates analysis_cache
  - GET analysis returns valid response with transitions + arc + patterns
  - GET analysis on non-analyzed set returns 404 or empty
  - Re-analyze overwrites cache
  - 4–5 test cases
- Conftest updates: add tracks with varied keys/genres/energies for meaningful arc analysis

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
