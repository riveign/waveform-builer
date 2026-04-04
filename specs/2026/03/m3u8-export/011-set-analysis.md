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
