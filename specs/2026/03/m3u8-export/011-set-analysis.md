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

### Files
- `src/kiku/analysis/teaching.py` (NEW)
  - Teaching moment generator: per-transition explanations, set-level pattern detection
- `src/kiku/analysis/set_analyzer.py` (NEW)
  - Core `analyze_set()` orchestrator: score transitions, compute arc, infer energy, cache results
- `src/kiku/api/schemas.py`
  - Add `TransitionAnalysisResponse`, `ArcAnalysisResponse`, `SetAnalysisResponse`
- `src/kiku/api/routes/sets.py`
  - Add `POST /{set_id}/analyze` and `GET /{set_id}/analysis` endpoints
- `src/kiku/cli.py`
  - Add `kiku analyze <set>` command
- `frontend/src/lib/types/index.ts`
  - Add `TransitionAnalysis`, `ArcAnalysis`, `SetAnalysis` interfaces
- `frontend/src/lib/api/sets.ts`
  - Add `analyzeSet()` and `getSetAnalysis()` functions
- `frontend/src/lib/components/set/SetAnalysisView.svelte` (NEW)
  - Analysis display: transition list with teaching moments, arc summary, set patterns
- `frontend/src/lib/components/set/SetView.svelte`
  - Add "Analysis" button and integrate SetAnalysisView
- `tests/test_set_analysis.py` (NEW)
  - Unit tests for teaching, energy inference, arc classification
- `tests/api/test_analysis_api.py` (NEW)
  - API integration tests for analyze/analysis endpoints

### Tasks

#### Task 1 — teaching.py: Create teaching moments engine

Tools: editor
File: `src/kiku/analysis/teaching.py` (NEW)

````diff
--- /dev/null
+++ b/src/kiku/analysis/teaching.py
@@ -0,0 +1,189 @@
+"""Teaching moments engine — explains why transitions work or struggle."""
+
+from __future__ import annotations
+
+from kiku.setbuilder.camelot import harmonic_score, parse_camelot
+from kiku.setbuilder.scoring import genre_to_family
+
+
+# ── Per-Transition Teaching ─────────────────────────────────────────────
+
+
+def transition_teaching_moment(
+    scores: dict,
+    key_a: str | None,
+    key_b: str | None,
+    bpm_a: float | None,
+    bpm_b: float | None,
+    genre_a: str | None,
+    genre_b: str | None,
+) -> tuple[str, str | None]:
+    """Generate a teaching moment and optional suggestion for a transition.
+
+    Returns (teaching_moment, suggestion). suggestion is None for strong transitions.
+    """
+    total = scores.get("total", 0.0)
+    parts: list[str] = []
+    suggestion: str | None = None
+
+    # ── Strong transition (>= 0.8) — celebrate ──
+    if total >= 0.8:
+        parts.append(_explain_strength(scores, key_a, key_b, bpm_a, bpm_b))
+        return " ".join(parts), None
+
+    # ── Good transition (0.6-0.8) — acknowledge ──
+    if total >= 0.6:
+        parts.append(_explain_good(scores, key_a, key_b, bpm_a, bpm_b, genre_a, genre_b))
+        # Mild suggestion if one dimension drags
+        weakest = _weakest_dimension(scores)
+        if weakest and scores.get(weakest, 1.0) < 0.5:
+            suggestion = _suggest_improvement(weakest, scores, bpm_a, bpm_b, key_a, key_b)
+        return " ".join(parts), suggestion
+
+    # ── Weak transition (< 0.6) — constructive ──
+    parts.append(_explain_weakness(scores, key_a, key_b, bpm_a, bpm_b, genre_a, genre_b))
+    weakest = _weakest_dimension(scores)
+    if weakest:
+        suggestion = _suggest_improvement(weakest, scores, bpm_a, bpm_b, key_a, key_b)
+    return " ".join(parts), suggestion
+
+
+def _explain_strength(
+    scores: dict, key_a: str | None, key_b: str | None,
+    bpm_a: float | None, bpm_b: float | None,
+) -> str:
+    """Celebrate a strong transition."""
+    h = scores.get("harmonic", 0)
+    e = scores.get("energy_fit", 0)
+
+    if h >= 0.85 and key_a and key_b:
+        ca, cb = parse_camelot(key_a), parse_camelot(key_b)
+        if ca and cb and ca == cb:
+            base = f"Both tracks in {key_a} — perfect harmonic match."
+        else:
+            base = f"Clean key movement from {key_a} to {key_b}."
+    elif e >= 0.8:
+        base = "Energy flows naturally here."
+    else:
+        base = "Everything clicks on this transition."
+
+    return base + " Your ear picked this."
+
+
+def _explain_good(
+    scores: dict, key_a: str | None, key_b: str | None,
+    bpm_a: float | None, bpm_b: float | None,
+    genre_a: str | None, genre_b: str | None,
+) -> str:
+    """Acknowledge a solid transition."""
+    h = scores.get("harmonic", 0)
+    b = scores.get("bpm_compat", 0)
+
+    parts = []
+    if h >= 0.8 and key_a and key_b:
+        parts.append(f"The key shift from {key_a} to {key_b} keeps it moving.")
+    elif b >= 0.8 and bpm_a and bpm_b:
+        parts.append(f"Tempo stays locked at {bpm_a:.0f}–{bpm_b:.0f} BPM.")
+    else:
+        parts.append("Solid transition — the pieces fit together.")
+
+    # Note what adds character
+    if genre_a and genre_b and genre_to_family(genre_a) != genre_to_family(genre_b):
+        parts.append("The genre shift adds character.")
+
+    return " ".join(parts)
+
+
+def _explain_weakness(
+    scores: dict, key_a: str | None, key_b: str | None,
+    bpm_a: float | None, bpm_b: float | None,
+    genre_a: str | None, genre_b: str | None,
+) -> str:
+    """Constructive feedback for a weak transition."""
+    weakest = _weakest_dimension(scores)
+
+    if weakest == "harmonic" and key_a and key_b:
+        return f"Key clash between {key_a} and {key_b} — this creates tension on the floor."
+    if weakest == "bpm_compat" and bpm_a and bpm_b:
+        diff_pct = abs(bpm_b - bpm_a) / bpm_a * 100 if bpm_a > 0 else 0
+        return f"The BPM jump is {diff_pct:.0f}% — that's a noticeable shift."
+    if weakest == "energy_fit":
+        return "Big energy change here — the floor might feel the drop."
+    if weakest == "genre_coherence":
+        fa = genre_to_family(genre_a) if genre_a else "unknown"
+        fb = genre_to_family(genre_b) if genre_b else "unknown"
+        return f"Jumping from {fa} to {fb} — bold genre shift."
+
+    return "This transition has some rough edges."
+
+
+def _weakest_dimension(scores: dict) -> str | None:
+    """Find the lowest-scoring dimension (excluding total and track_quality)."""
+    dims = ["harmonic", "energy_fit", "bpm_compat", "genre_coherence"]
+    valid = {d: scores[d] for d in dims if d in scores}
+    if not valid:
+        return None
+    return min(valid, key=valid.get)  # type: ignore[arg-type]
+
+
+def _suggest_improvement(
+    weakest: str, scores: dict,
+    bpm_a: float | None, bpm_b: float | None,
+    key_a: str | None, key_b: str | None,
+) -> str:
+    """Suggest how to improve based on the weakest dimension."""
+    if weakest == "harmonic":
+        if key_a:
+            ca = parse_camelot(key_a)
+            if ca:
+                adj_keys = [f"{(ca[0] % 12) + 1}{ca[1]}", f"{((ca[0] - 2) % 12) + 1}{ca[1]}"]
+                return f"Try a track in {' or '.join(adj_keys)} for a smoother key transition."
+        return "Look for a track with a compatible key."
+    if weakest == "bpm_compat" and bpm_a and bpm_b:
+        mid_bpm = (bpm_a + bpm_b) / 2
+        return f"A bridge track around {mid_bpm:.0f} BPM could smooth this jump."
+    if weakest == "energy_fit":
+        return "Consider a track that bridges the energy gap gradually."
+    if weakest == "genre_coherence":
+        return "A cross-genre track could ease this transition."
+    return "Consider rearranging tracks around this point."
+
+
+# ── Set-Level Patterns ──────────────────────────────────────────────────
+
+
+def detect_set_patterns(
+    transitions: list[dict],
+    energy_curve: list[float],
+    key_journey: list[str | None],
+    bpm_values: list[float | None],
+) -> list[str]:
+    """Detect set-level teaching patterns from aggregated data.
+
+    Args:
+        transitions: list of score dicts (one per transition)
+        energy_curve: energy value per track position
+        key_journey: Camelot key per track position
+        bpm_values: BPM per track position
+    """
+    patterns: list[str] = []
+
+    if not transitions:
+        return patterns
+
+    # Average scores per dimension
+    avg = {}
+    for dim in ["harmonic", "energy_fit", "bpm_compat", "genre_coherence"]:
+        values = [t.get(dim, 0.5) for t in transitions]
+        avg[dim] = sum(values) / len(values) if values else 0.5
+
+    # Strongest dimension
+    best_dim = max(avg, key=avg.get)  # type: ignore[arg-type]
+    dim_labels = {
+        "harmonic": "key relationships",
+        "energy_fit": "energy flow",
+        "bpm_compat": "tempo consistency",
+        "genre_coherence": "genre cohesion",
+    }
+    if avg[best_dim] >= 0.7:
+        patterns.append(
+            f"Your strongest suit is {dim_labels[best_dim]} — "
+            f"averaging {avg[best_dim]:.2f}. That's a signature element of your style."
+        )
+
+    # Energy arc shape
+    if len(energy_curve) >= 3:
+        mid = len(energy_curve) // 2
+        start_avg = sum(energy_curve[:mid]) / mid if mid > 0 else 0
+        end_avg = sum(energy_curve[mid:]) / (len(energy_curve) - mid)
+        if end_avg > start_avg + 0.15:
+            patterns.append("You build energy over the set — classic journey arc.")
+        elif start_avg > end_avg + 0.15:
+            patterns.append("You front-load energy and cool down — bold opening strategy.")
+        elif max(energy_curve) - min(energy_curve) < 0.2:
+            patterns.append("You keep energy steady — hypnotic, consistent vibe.")
+
+    # Key adventure
+    valid_keys = [k for k in key_journey if k]
+    if len(valid_keys) >= 3:
+        unique_keys = len(set(valid_keys))
+        ratio = unique_keys / len(valid_keys)
+        if ratio < 0.3:
+            patterns.append("You stay close to home key — that's deep harmonic focus.")
+        elif ratio > 0.7:
+            patterns.append("You explore the Camelot wheel widely — adventurous harmonic ear.")
+
+    # Weak spot
+    weakest_dim = min(avg, key=avg.get)  # type: ignore[arg-type]
+    if avg[weakest_dim] < 0.5:
+        patterns.append(
+            f"Your transitions could use work on {dim_labels[weakest_dim]} "
+            f"(averaging {avg[weakest_dim]:.2f}). Focus here to level up."
+        )
+
+    return patterns
````

Verification:
- File exists at `src/kiku/analysis/teaching.py`
- `python -c "from kiku.analysis.teaching import transition_teaching_moment, detect_set_patterns; print('OK')"`

#### Task 2 — set_analyzer.py: Core set analyzer

Tools: editor
File: `src/kiku/analysis/set_analyzer.py` (NEW)

````diff
--- /dev/null
+++ b/src/kiku/analysis/set_analyzer.py
@@ -0,0 +1,228 @@
+"""Set analysis engine — scores transitions, computes arcs, generates teaching moments."""
+
+from __future__ import annotations
+
+import json
+from dataclasses import asdict, dataclass
+from datetime import datetime
+
+from sqlalchemy.orm import Session
+
+from kiku.analysis.autotag import ZONE_MAP, resolve_energy
+from kiku.analysis.teaching import detect_set_patterns, transition_teaching_moment
+from kiku.db.models import Set, SetTrack, Track
+from kiku.setbuilder.camelot import harmonic_score, parse_camelot
+from kiku.setbuilder.constraints import zone_to_numeric
+from kiku.setbuilder.scoring import (
+    bpm_compatibility,
+    energy_fit,
+    genre_coherence,
+    track_quality,
+)
+from kiku.config import SCORING_WEIGHTS
+
+
+# ── Data Structures ─────────────────────────────────────────────────────
+
+
+@dataclass
+class TransitionAnalysis:
+    position: int
+    track_a_id: int
+    track_b_id: int
+    scores: dict
+    teaching_moment: str
+    suggestion: str | None
+
+
+@dataclass
+class ArcAnalysis:
+    energy_curve: list[float]
+    energy_shape: str
+    key_journey: list[str | None]
+    key_style: str
+    bpm_range: tuple[float, float]
+    bpm_drift: float
+    bpm_style: str
+    genre_segments: list[dict]
+
+
+@dataclass
+class SetAnalysisResult:
+    set_id: int
+    track_count: int
+    transition_count: int
+    transitions: list[TransitionAnalysis]
+    arc: ArcAnalysis
+    overall_score: float
+    set_patterns: list[str]
+    analyzed_at: str
+
+
+# ── Core Analyzer ───────────────────────────────────────────────────────
+
+
+def analyze_set(db: Session, set_id: int) -> SetAnalysisResult:
+    """Run full analysis on a set: score transitions, compute arc, generate teaching moments.
+
+    Also infers energy for untagged tracks and caches the result.
+    """
+    s = db.get(Set, set_id)
+    if not s:
+        raise ValueError(f"Set {set_id} not found")
+
+    set_tracks = sorted(s.tracks, key=lambda st: st.position)
+    tracks = [st.track for st in set_tracks]
+
+    if len(tracks) < 2:
+        raise ValueError(f"Set {set_id} needs at least 2 tracks for analysis")
+
+    # 1. Infer energy for untagged tracks
+    _infer_energy(db, set_tracks, tracks)
+
+    # 2. Score all transitions
+    transitions = _score_transitions(tracks, set_tracks)
+
+    # 3. Compute arc analysis
+    arc = _compute_arc(tracks)
+
+    # 4. Detect set-level patterns
+    score_dicts = [t.scores for t in transitions]
+    set_patterns = detect_set_patterns(
+        score_dicts,
+        arc.energy_curve,
+        arc.key_journey,
+        [t.bpm for t in tracks],
+    )
+
+    # 5. Overall score
+    totals = [t.scores["total"] for t in transitions]
+    overall_score = round(sum(totals) / len(totals), 3) if totals else 0.0
+
+    result = SetAnalysisResult(
+        set_id=set_id,
+        track_count=len(tracks),
+        transition_count=len(transitions),
+        transitions=transitions,
+        arc=arc,
+        overall_score=overall_score,
+        set_patterns=set_patterns,
+        analyzed_at=datetime.now().isoformat(),
+    )
+
+    # 6. Cache result
+    s.analysis_cache = json.dumps(asdict(result))
+    s.is_analyzed = 1
+    db.commit()
+
+    return result
+
+
+# ── Energy Inference ────────────────────────────────────────────────────
+
+
+def _get_track_energy(track: Track) -> float | None:
+    """Get energy value from existing sources (not inferred)."""
+    if track.audio_features and track.audio_features.energy is not None:
+        return track.audio_features.energy
+    zone, source, _conf = resolve_energy(track)
+    if zone and source != "none":
+        return zone_to_numeric(zone)
+    return None
+
+
+def _infer_energy(db: Session, set_tracks: list[SetTrack], tracks: list[Track]) -> None:
+    """Infer energy for tracks that lack energy data, based on position and neighbors."""
+    energies: list[float | None] = [_get_track_energy(t) for t in tracks]
+    n = len(tracks)
+
+    for i, (st, e) in enumerate(zip(set_tracks, energies)):
+        if e is not None:
+            continue  # Already has energy — skip
+
+        # Try neighbor interpolation
+        prev_e = energies[i - 1] if i > 0 else None
+        next_e = energies[i + 1] if i < n - 1 else None
+
+        if prev_e is not None and next_e is not None:
+            inferred = round((prev_e + next_e) / 2, 3)
+            source = "interpolation"
+        elif prev_e is not None:
+            inferred = prev_e
+            source = "interpolation"
+        elif next_e is not None:
+            inferred = next_e
+            source = "interpolation"
+        else:
+            # Position-based fallback
+            ratio = i / max(n - 1, 1)
+            if ratio < 0.2:
+                inferred = 0.3  # warmup
+            elif ratio < 0.4:
+                inferred = 0.55  # build
+            elif ratio < 0.7:
+                inferred = 0.75  # drive/peak
+            elif ratio < 0.85:
+                inferred = 0.9  # peak
+            else:
+                inferred = 0.4  # close
+            source = "position"
+
+        st.inferred_energy = inferred
+        st.inference_source = source
+        energies[i] = inferred  # Update for next neighbor lookups
+
+    db.flush()
+
+
+# ── Transition Scoring ──────────────────────────────────────────────────
+
+
+def _score_transitions(tracks: list[Track], set_tracks: list[SetTrack]) -> list[TransitionAnalysis]:
+    """Score all adjacent transitions in the set."""
+    w = SCORING_WEIGHTS
+    results = []
+
+    for i in range(len(tracks) - 1):
+        t_a, t_b = tracks[i], tracks[i + 1]
+
+        h = harmonic_score(t_a.key, t_b.key)
+        # Use inferred energy if available for target
+        st_b = set_tracks[i + 1]
+        target_e = st_b.inferred_energy if st_b.inferred_energy is not None else 0.5
+        e = energy_fit(t_b, target_e)
+        b = bpm_compatibility(t_a.bpm, t_b.bpm)
+        g = genre_coherence(
+            t_a.dir_genre or t_a.rb_genre,
+            t_b.dir_genre or t_b.rb_genre,
+        )
+        q, _ = track_quality(t_b)
+
+        total = (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
+                 + w["genre_coherence"] * g + w["track_quality"] * q)
+
+        scores = {
+            "harmonic": round(h, 3),
+            "energy_fit": round(e, 3),
+            "bpm_compat": round(b, 3),
+            "genre_coherence": round(g, 3),
+            "track_quality": round(q, 3),
+            "total": round(total, 3),
+        }
+
+        teaching, suggestion = transition_teaching_moment(
+            scores,
+            t_a.key, t_b.key,
+            t_a.bpm, t_b.bpm,
+            t_a.dir_genre or t_a.rb_genre,
+            t_b.dir_genre or t_b.rb_genre,
+        )
+
+        results.append(TransitionAnalysis(
+            position=i,
+            track_a_id=t_a.id,
+            track_b_id=t_b.id,
+            scores=scores,
+            teaching_moment=teaching,
+            suggestion=suggestion,
+        ))
+
+    return results
+
+
+# ── Arc Analysis ────────────────────────────────────────────────────────
+
+
+def _compute_arc(tracks: list[Track]) -> ArcAnalysis:
+    """Compute arc-level analysis across the full set."""
+    # Energy curve
+    energy_curve = []
+    for t in tracks:
+        e = _get_track_energy(t)
+        energy_curve.append(e if e is not None else 0.5)
+
+    energy_shape = _classify_energy_shape(energy_curve)
+
+    # Key journey
+    key_journey = [t.key for t in tracks]
+    key_style = _classify_key_style(key_journey)
+
+    # BPM
+    bpms = [t.bpm for t in tracks if t.bpm and t.bpm > 0]
+    bpm_range = (min(bpms), max(bpms)) if bpms else (0.0, 0.0)
+    bpm_drift = round(bpms[-1] - bpms[0], 1) if len(bpms) >= 2 else 0.0
+    bpm_style = _classify_bpm_style(bpms)
+
+    # Genre segments
+    genre_segments = _detect_genre_segments(tracks)
+
+    return ArcAnalysis(
+        energy_curve=[round(e, 3) for e in energy_curve],
+        energy_shape=energy_shape,
+        key_journey=key_journey,
+        key_style=key_style,
+        bpm_range=bpm_range,
+        bpm_drift=bpm_drift,
+        bpm_style=bpm_style,
+        genre_segments=genre_segments,
+    )
+
+
+def _classify_energy_shape(curve: list[float]) -> str:
+    if len(curve) < 2:
+        return "too-short"
+    mid = len(curve) // 2
+    first_half = sum(curve[:mid]) / mid if mid > 0 else 0
+    second_half = sum(curve[mid:]) / (len(curve) - mid)
+    peak_pos = curve.index(max(curve))
+    valley_pos = curve.index(min(curve))
+    spread = max(curve) - min(curve)
+
+    if spread < 0.15:
+        return "flat"
+    if peak_pos < len(curve) * 0.4 and valley_pos > len(curve) * 0.6:
+        return "peak-valley"
+    if second_half > first_half + 0.1:
+        return "ramp-up"
+    if first_half > second_half + 0.1:
+        return "wind-down"
+    # Check for multiple peaks
+    peaks = sum(1 for i in range(1, len(curve) - 1)
+                if curve[i] > curve[i-1] and curve[i] > curve[i+1])
+    if peaks >= 3:
+        return "roller-coaster"
+    return "journey"
+
+
+def _classify_key_style(keys: list[str | None]) -> str:
+    valid = [k for k in keys if k]
+    if len(valid) < 2:
+        return "unknown"
+    unique = len(set(valid))
+    ratio = unique / len(valid)
+    if ratio <= 0.3:
+        return "home-key"
+    if ratio >= 0.7:
+        return "adventurous"
+    return "chromatic-walk"
+
+
+def _classify_bpm_style(bpms: list[float]) -> str:
+    if len(bpms) < 2:
+        return "unknown"
+    spread = max(bpms) - min(bpms)
+    if spread < 3:
+        return "steady"
+    drift = abs(bpms[-1] - bpms[0])
+    if drift > 10:
+        return "gradual-build" if bpms[-1] > bpms[0] else "gradual-drop"
+    if spread > 15:
+        return "volatile"
+    return "gentle-drift"
+
+
+def _detect_genre_segments(tracks: list[Track]) -> list[dict]:
+    """Detect contiguous genre family segments."""
+    from kiku.setbuilder.scoring import genre_to_family
+    segments: list[dict] = []
+    current_family = None
+    start_pos = 0
+
+    for i, t in enumerate(tracks):
+        family = genre_to_family(t.dir_genre or t.rb_genre)
+        if family != current_family:
+            if current_family is not None:
+                segments.append({"genre_family": current_family, "start_pos": start_pos, "end_pos": i - 1})
+            current_family = family
+            start_pos = i
+
+    if current_family is not None:
+        segments.append({"genre_family": current_family, "start_pos": start_pos, "end_pos": len(tracks) - 1})
+
+    return segments
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.analysis.set_analyzer import analyze_set; print('OK')"`

#### Task 3 — schemas.py: Add SetAnalysis response models

Tools: editor
File: `src/kiku/api/schemas.py`

Append after the `ImportResultResponse` class (end of file, line ~502):

````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ -500,3 +500,40 @@
     match_methods: dict[str, int] = {}
     warnings: list[str] = []
     duplicate_set_id: int | None = None
+
+
+# ── Set Analysis models ──
+
+
+class TransitionAnalysisResponse(BaseModel):
+    position: int
+    track_a_id: int
+    track_b_id: int
+    scores: dict
+    teaching_moment: str
+    suggestion: str | None = None
+
+
+class ArcAnalysisResponse(BaseModel):
+    energy_curve: list[float]
+    energy_shape: str
+    key_journey: list[str | None]
+    key_style: str
+    bpm_range: list[float]  # JSON-friendly (not tuple)
+    bpm_drift: float
+    bpm_style: str
+    genre_segments: list[dict]
+
+
+class SetAnalysisResponse(BaseModel):
+    set_id: int
+    track_count: int
+    transition_count: int
+    transitions: list[TransitionAnalysisResponse]
+    arc: ArcAnalysisResponse
+    overall_score: float
+    set_patterns: list[str]
+    analyzed_at: str
````

Verification:
- `python -c "from kiku.api.schemas import SetAnalysisResponse; print('OK')"`

#### Task 4 — sets.py: Add analyze + analysis endpoints

Tools: editor
File: `src/kiku/api/routes/sets.py`

Step 4a — Add schema imports. Find the import block and add `SetAnalysisResponse`:

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -15,6 +15,7 @@
 from kiku.api.schemas import (
     CueCreateRequest,
     CueResponse,
+    SetAnalysisResponse,
     ImportResultResponse,
     ReplaceTrackRequest,
     ReplacementCandidate,
````

Step 4b — Add both endpoints. Append at end of file (after the last endpoint):

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ END_OF_FILE
+
+
+@router.post("/{set_id}/analyze", response_model=SetAnalysisResponse)
+def analyze_set_endpoint(set_id: int, db: Session = Depends(get_db)):
+    """Trigger full analysis on a set: score transitions, compute arc, generate teaching moments."""
+    from kiku.analysis.set_analyzer import analyze_set
+
+    try:
+        result = analyze_set(db, set_id)
+    except ValueError as e:
+        raise HTTPException(status_code=404, detail=str(e))
+
+    from dataclasses import asdict
+    data = asdict(result)
+    # Convert tuple to list for JSON
+    data["arc"]["bpm_range"] = list(data["arc"]["bpm_range"])
+    return data
+
+
+@router.get("/{set_id}/analysis", response_model=SetAnalysisResponse)
+def get_set_analysis(set_id: int, db: Session = Depends(get_db)):
+    """Get cached analysis for a set. Returns 404 if not yet analyzed."""
+    import json
+
+    s = db.get(Set, set_id)
+    if not s:
+        raise HTTPException(status_code=404, detail="Set not found")
+    if not s.is_analyzed or not s.analysis_cache:
+        raise HTTPException(status_code=404, detail="Set has not been analyzed yet. Use POST /analyze first.")
+
+    return json.loads(s.analysis_cache)
````

IMPORTANT: These endpoints MUST be placed BEFORE the `/{set_id}` catch-all routes to avoid FastAPI routing conflicts. Place them after the `import/m3u8` endpoint but before `/{set_id}` detail endpoint.

Verification:
- `source .venv/bin/activate && python -c "from kiku.api.routes.sets import router; print('OK')"`

#### Task 5 — cli.py: Add `kiku analyze` command

Tools: editor
File: `src/kiku/cli.py`

Add after the `import-playlist` command (around line 614):

````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@ AFTER_IMPORT_PLAYLIST_COMMAND
+
+
+@cli.command()
+@click.argument("set_name_or_id")
+def analyze(set_name_or_id: str):
+    """Analyze an imported set — score transitions, compute arc, generate teaching moments.
+
+    Shows why your transitions work and where to grow.
+    """
+    from kiku.analysis.set_analyzer import analyze_set
+    from kiku.db.models import Set, get_session
+
+    session = get_session()
+
+    # Resolve set by ID or name
+    try:
+        set_id = int(set_name_or_id)
+        s = session.get(Set, set_id)
+    except ValueError:
+        s = session.query(Set).filter(Set.name.ilike(f"%{set_name_or_id}%")).first()
+
+    if not s:
+        console.print(f"[red]Couldn't find set '{set_name_or_id}'.[/]")
+        return
+
+    console.print(f"[cyan]Analyzing set: {s.name}...[/]")
+    try:
+        result = analyze_set(session, s.id)
+    except ValueError as e:
+        console.print(f"[red]{e}[/]")
+        return
+
+    # Print summary
+    console.print(f"\n[bold]{s.name}[/] — {result.track_count} tracks, {result.transition_count} transitions")
+    console.print(f"Overall score: [bold {'green' if result.overall_score >= 0.7 else 'yellow' if result.overall_score >= 0.5 else 'red'}]{result.overall_score:.3f}[/]")
+    console.print(f"Energy shape: [cyan]{result.arc.energy_shape}[/] | Key style: [cyan]{result.arc.key_style}[/] | BPM: [cyan]{result.arc.bpm_style}[/]")
+
+    # Transitions
+    console.print(f"\n[bold]Transitions:[/]")
+    table = Table()
+    table.add_column("#", justify="right", style="dim")
+    table.add_column("Score")
+    table.add_column("Teaching Moment")
+    table.add_column("Suggestion", style="dim")
+    for t in result.transitions:
+        score_color = "green" if t.scores["total"] >= 0.7 else "yellow" if t.scores["total"] >= 0.5 else "red"
+        table.add_row(
+            str(t.position + 1),
+            f"[{score_color}]{t.scores['total']:.3f}[/]",
+            t.teaching_moment,
+            t.suggestion or "",
+        )
+    console.print(table)
+
+    # Set patterns
+    if result.set_patterns:
+        console.print(f"\n[bold]What your ear tells us:[/]")
+        for p in result.set_patterns:
+            console.print(f"  {p}")
+
+    console.print(f"\n[dim]Analysis cached. View in the app or re-run to update.[/]")
````

Verification:
- `source .venv/bin/activate && kiku analyze --help`

#### Task 6 — frontend types: Add SetAnalysis interfaces

Tools: editor
File: `frontend/src/lib/types/index.ts`

Append after the existing `TransitionDetail` interface (around line 144):

````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ AFTER_TransitionDetail
+
+export interface TransitionAnalysis {
+	position: number;
+	track_a_id: number;
+	track_b_id: number;
+	scores: TransitionScoreBreakdown & { total: number };
+	teaching_moment: string;
+	suggestion: string | null;
+}
+
+export interface ArcAnalysis {
+	energy_curve: number[];
+	energy_shape: string;
+	key_journey: (string | null)[];
+	key_style: string;
+	bpm_range: [number, number];
+	bpm_drift: number;
+	bpm_style: string;
+	genre_segments: { genre_family: string; start_pos: number; end_pos: number }[];
+}
+
+export interface SetAnalysis {
+	set_id: number;
+	track_count: number;
+	transition_count: number;
+	transitions: TransitionAnalysis[];
+	arc: ArcAnalysis;
+	overall_score: number;
+	set_patterns: string[];
+	analyzed_at: string;
+}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5`

#### Task 7 — frontend API: Add analyzeSet + getSetAnalysis

Tools: editor
File: `frontend/src/lib/api/sets.ts`

Append at end of file:

````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@ END_OF_FILE
+
+export async function analyzeSet(setId: number): Promise<SetAnalysis> {
+	const res = await fetch(`${API_BASE}/api/sets/${setId}/analyze`, { method: 'POST' });
+	if (!res.ok) {
+		const err = await res.json().catch(() => ({ detail: 'Analysis failed' }));
+		throw new Error(err.detail || 'Analysis failed');
+	}
+	return res.json();
+}
+
+export async function getSetAnalysis(setId: number): Promise<SetAnalysis> {
+	const res = await fetch(`${API_BASE}/api/sets/${setId}/analysis`);
+	if (!res.ok) {
+		const err = await res.json().catch(() => ({ detail: 'Not analyzed yet' }));
+		throw new Error(err.detail || 'Not analyzed yet');
+	}
+	return res.json();
+}
````

Also add the import for `SetAnalysis` type at the top of the file where other types are imported.

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5`

#### Task 8 — SetAnalysisView.svelte: Analysis display component

Tools: editor
File: `frontend/src/lib/components/set/SetAnalysisView.svelte` (NEW)

````diff
--- /dev/null
+++ b/frontend/src/lib/components/set/SetAnalysisView.svelte
@@ -0,0 +1,264 @@
+<script lang="ts">
+	import type { SetAnalysis } from '$lib/types';
+	import ScoreBreakdown from './ScoreBreakdown.svelte';
+
+	interface Props {
+		analysis: SetAnalysis;
+	}
+
+	let { analysis }: Props = $props();
+
+	function scoreColor(score: number): string {
+		if (score >= 0.7) return 'var(--color-success, #66BB6A)';
+		if (score >= 0.5) return 'var(--color-warning, #FFA726)';
+		return 'var(--color-error, #EF5350)';
+	}
+
+	const shapeLabels: Record<string, string> = {
+		'flat': 'Steady energy — hypnotic vibe',
+		'ramp-up': 'Building energy — classic journey',
+		'wind-down': 'Front-loaded energy — bold opener',
+		'peak-valley': 'Peak then valley — dramatic arc',
+		'roller-coaster': 'Multiple peaks — dynamic ride',
+		'journey': 'Natural flow — organic energy',
+		'too-short': 'Too short to classify',
+	};
+
+	const keyLabels: Record<string, string> = {
+		'home-key': 'Staying close — deep harmonic focus',
+		'adventurous': 'Exploring the wheel — wide key range',
+		'chromatic-walk': 'Gradual movement — chromatic walk',
+		'unknown': 'Not enough key data',
+	};
+
+	const bpmLabels: Record<string, string> = {
+		'steady': 'Locked tempo — consistent groove',
+		'gradual-build': 'Building tempo — rising energy',
+		'gradual-drop': 'Dropping tempo — winding down',
+		'volatile': 'Tempo jumps — dynamic pacing',
+		'gentle-drift': 'Gentle tempo drift',
+		'unknown': 'Not enough BPM data',
+	};
+
+	let expandedTransition = $state<number | null>(null);
+
+	function toggleTransition(pos: number) {
+		expandedTransition = expandedTransition === pos ? null : pos;
+	}
+</script>
+
+<div class="analysis-view">
+	<!-- Overall Score -->
+	<div class="overall-section">
+		<div class="overall-score" style="color: {scoreColor(analysis.overall_score)}">
+			{analysis.overall_score.toFixed(3)}
+		</div>
+		<div class="overall-label">
+			{analysis.track_count} tracks &middot; {analysis.transition_count} transitions
+		</div>
+	</div>
+
+	<!-- Arc Summary -->
+	<div class="arc-section">
+		<h3>Set Arc</h3>
+		<div class="arc-grid">
+			<div class="arc-item">
+				<span class="arc-label">Energy</span>
+				<span class="arc-value">{shapeLabels[analysis.arc.energy_shape] ?? analysis.arc.energy_shape}</span>
+			</div>
+			<div class="arc-item">
+				<span class="arc-label">Keys</span>
+				<span class="arc-value">{keyLabels[analysis.arc.key_style] ?? analysis.arc.key_style}</span>
+			</div>
+			<div class="arc-item">
+				<span class="arc-label">BPM</span>
+				<span class="arc-value">
+					{bpmLabels[analysis.arc.bpm_style] ?? analysis.arc.bpm_style}
+					{#if analysis.arc.bpm_range[0] > 0}
+						({analysis.arc.bpm_range[0].toFixed(0)}–{analysis.arc.bpm_range[1].toFixed(0)})
+					{/if}
+				</span>
+			</div>
+			{#if analysis.arc.genre_segments.length > 1}
+				<div class="arc-item">
+					<span class="arc-label">Genre Flow</span>
+					<span class="arc-value">
+						{analysis.arc.genre_segments.map((s) => s.genre_family).join(' → ')}
+					</span>
+				</div>
+			{/if}
+		</div>
+	</div>
+
+	<!-- Set Patterns -->
+	{#if analysis.set_patterns.length > 0}
+		<div class="patterns-section">
+			<h3>What your ear tells us</h3>
+			{#each analysis.set_patterns as pattern}
+				<p class="pattern">{pattern}</p>
+			{/each}
+		</div>
+	{/if}
+
+	<!-- Transitions -->
+	<div class="transitions-section">
+		<h3>Transitions</h3>
+		{#each analysis.transitions as t}
+			<button
+				class="transition-row"
+				class:weak={t.scores.total < 0.5}
+				class:strong={t.scores.total >= 0.7}
+				onclick={() => toggleTransition(t.position)}
+			>
+				<span class="t-pos">{t.position + 1}</span>
+				<span class="t-score" style="color: {scoreColor(t.scores.total)}">
+					{t.scores.total.toFixed(3)}
+				</span>
+				<span class="t-teaching">{t.teaching_moment}</span>
+			</button>
+			{#if expandedTransition === t.position}
+				<div class="transition-detail">
+					<ScoreBreakdown breakdown={t.scores} />
+					{#if t.suggestion}
+						<div class="suggestion">{t.suggestion}</div>
+					{/if}
+				</div>
+			{/if}
+		{/each}
+	</div>
+
+	<div class="analyzed-at">
+		Analyzed {new Date(analysis.analyzed_at).toLocaleString()}
+	</div>
+</div>
+
+<style>
+	.analysis-view {
+		display: flex;
+		flex-direction: column;
+		gap: 20px;
+		padding: 16px;
+	}
+
+	.overall-section {
+		text-align: center;
+		padding: 16px;
+		background: var(--bg-secondary);
+		border-radius: 8px;
+	}
+
+	.overall-score {
+		font-size: 36px;
+		font-weight: 700;
+		font-variant-numeric: tabular-nums;
+	}
+
+	.overall-label {
+		font-size: 13px;
+		color: var(--text-secondary);
+		margin-top: 4px;
+	}
+
+	h3 {
+		font-size: 14px;
+		text-transform: uppercase;
+		letter-spacing: 0.5px;
+		color: var(--text-secondary);
+		margin: 0 0 12px;
+	}
+
+	.arc-section {
+		background: var(--bg-secondary);
+		border-radius: 8px;
+		padding: 16px;
+	}
+
+	.arc-grid {
+		display: flex;
+		flex-direction: column;
+		gap: 8px;
+	}
+
+	.arc-item {
+		display: flex;
+		justify-content: space-between;
+		align-items: center;
+	}
+
+	.arc-label {
+		font-size: 12px;
+		color: var(--text-secondary);
+		min-width: 60px;
+	}
+
+	.arc-value {
+		font-size: 12px;
+		color: var(--text-primary);
+		text-align: right;
+	}
+
+	.patterns-section {
+		background: var(--bg-secondary);
+		border-radius: 8px;
+		padding: 16px;
+	}
+
+	.pattern {
+		font-size: 13px;
+		color: var(--text-primary);
+		margin: 6px 0;
+		line-height: 1.5;
+		font-style: italic;
+	}
+
+	.transitions-section {
+		display: flex;
+		flex-direction: column;
+		gap: 2px;
+	}
+
+	.transition-row {
+		display: flex;
+		align-items: center;
+		gap: 10px;
+		padding: 8px 12px;
+		background: var(--bg-secondary);
+		border: 1px solid transparent;
+		border-radius: 4px;
+		cursor: pointer;
+		text-align: left;
+		width: 100%;
+		font-family: inherit;
+		font-size: inherit;
+		color: inherit;
+	}
+
+	.transition-row:hover {
+		border-color: var(--border);
+	}
+
+	.transition-row.weak {
+		border-left: 3px solid var(--color-error, #EF5350);
+	}
+
+	.transition-row.strong {
+		border-left: 3px solid var(--color-success, #66BB6A);
+	}
+
+	.t-pos {
+		width: 24px;
+		font-size: 11px;
+		color: var(--text-dim);
+		text-align: right;
+		flex-shrink: 0;
+	}
+
+	.t-score {
+		width: 48px;
+		font-weight: 600;
+		font-variant-numeric: tabular-nums;
+		flex-shrink: 0;
+	}
+
+	.t-teaching {
+		font-size: 12px;
+		color: var(--text-primary);
+		flex: 1;
+	}
+
+	.transition-detail {
+		padding: 12px 12px 12px 46px;
+		background: var(--bg-tertiary);
+		border-radius: 0 0 4px 4px;
+		margin-top: -2px;
+	}
+
+	.suggestion {
+		margin-top: 10px;
+		padding: 8px 12px;
+		background: var(--bg-secondary);
+		border-left: 3px solid var(--accent);
+		border-radius: 2px;
+		font-size: 12px;
+		color: var(--text-secondary);
+		font-style: italic;
+	}
+
+	.analyzed-at {
+		font-size: 11px;
+		color: var(--text-dim);
+		text-align: right;
+	}
+</style>
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -10`

#### Task 9 — SetView.svelte: Integrate analysis button and view

Tools: editor
File: `frontend/src/lib/components/set/SetView.svelte`

Step 9a — Add imports at top of script:

````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@ -2,7 +2,8 @@
-	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData } from '$lib/types';
-	import { getSet, getSetWaveforms, getTransition, exportRekordbox, exportM3U8, deleteSet } from '$lib/api/sets';
+	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData, SetAnalysis } from '$lib/types';
+	import { getSet, getSetWaveforms, getTransition, exportRekordbox, exportM3U8, deleteSet, analyzeSet, getSetAnalysis } from '$lib/api/sets';
@@
 	import SetEnergyReview from './SetEnergyReview.svelte';
+	import SetAnalysisView from './SetAnalysisView.svelte';
````

Step 9b — Add state and functions after existing state declarations:

````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@ AFTER_EXISTING_STATE
+	let analysis = $state<SetAnalysis | null>(null);
+	let analyzingSet = $state(false);
+
+	async function handleAnalyze() {
+		if (!selectedSet) return;
+		analyzingSet = true;
+		try {
+			analysis = await analyzeSet(selectedSet.id);
+		} catch (e) {
+			console.error('Analysis failed:', e);
+		} finally {
+			analyzingSet = false;
+		}
+	}
+
+	async function loadCachedAnalysis(setId: number) {
+		try {
+			analysis = await getSetAnalysis(setId);
+		} catch {
+			analysis = null;
+		}
+	}
````

Step 9c — In the `loadSet` function (or wherever the set is loaded), add a call to `loadCachedAnalysis(set.id)` after loading waveforms.

Step 9d — Add the Analyze button and analysis view in the template, after the energy flow chart section:

````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@ AFTER_ENERGY_FLOW_CHART
+			<div class="analysis-section">
+				<button
+					class="analyze-btn"
+					onclick={handleAnalyze}
+					disabled={analyzingSet}
+				>
+					{analyzingSet ? 'Analyzing...' : analysis ? 'Re-analyze' : 'Analyze Set'}
+				</button>
+				{#if analysis}
+					<SetAnalysisView {analysis} />
+				{/if}
+			</div>
````

Add corresponding styles:

````diff
+	.analysis-section {
+		margin-top: 16px;
+	}
+
+	.analyze-btn {
+		padding: 8px 16px;
+		background: var(--accent);
+		color: var(--bg-primary);
+		border: none;
+		border-radius: 6px;
+		cursor: pointer;
+		font-size: 13px;
+		font-weight: 500;
+	}
+
+	.analyze-btn:hover:not(:disabled) {
+		opacity: 0.9;
+	}
+
+	.analyze-btn:disabled {
+		opacity: 0.5;
+		cursor: not-allowed;
+	}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -10`

#### Task 10 — Unit tests: teaching + energy inference + arc

Tools: editor
File: `tests/test_set_analysis.py` (NEW)

````diff
--- /dev/null
+++ b/tests/test_set_analysis.py
@@ -0,0 +1,132 @@
+"""Unit tests for set analysis: teaching moments, energy inference, arc classification."""
+
+from unittest.mock import MagicMock
+
+from kiku.analysis.teaching import transition_teaching_moment, detect_set_patterns
+from kiku.analysis.set_analyzer import (
+    _classify_energy_shape,
+    _classify_key_style,
+    _classify_bpm_style,
+    _get_track_energy,
+    _infer_energy,
+)
+
+
+# ── Teaching Moment Tests ───────────────────────────────────────────────
+
+
+def test_teaching_strong_transition():
+    """Strong transition (>= 0.8) should celebrate, no suggestion."""
+    scores = {"harmonic": 1.0, "energy_fit": 0.9, "bpm_compat": 0.95, "genre_coherence": 0.8, "track_quality": 0.6, "total": 0.85}
+    moment, suggestion = transition_teaching_moment(scores, "8A", "8A", 128.0, 128.0, "techno", "techno")
+    assert "Your ear picked this" in moment
+    assert suggestion is None
+
+
+def test_teaching_good_transition():
+    """Good transition (0.6-0.8) should acknowledge."""
+    scores = {"harmonic": 0.85, "energy_fit": 0.6, "bpm_compat": 0.7, "genre_coherence": 0.5, "track_quality": 0.5, "total": 0.65}
+    moment, suggestion = transition_teaching_moment(scores, "5B", "6B", 128.0, 130.0, "techno", "house")
+    assert len(moment) > 10
+
+
+def test_teaching_weak_transition():
+    """Weak transition (< 0.6) should be constructive with suggestion."""
+    scores = {"harmonic": 0.2, "energy_fit": 0.3, "bpm_compat": 0.4, "genre_coherence": 0.3, "track_quality": 0.4, "total": 0.3}
+    moment, suggestion = transition_teaching_moment(scores, "1A", "7B", 128.0, 150.0, "techno", "house")
+    assert len(moment) > 10
+    assert suggestion is not None
+
+
+def test_teaching_weak_bpm_jump():
+    """Weak BPM should explain the jump."""
+    scores = {"harmonic": 0.8, "energy_fit": 0.7, "bpm_compat": 0.1, "genre_coherence": 0.8, "track_quality": 0.5, "total": 0.55}
+    moment, suggestion = transition_teaching_moment(scores, "8A", "8A", 128.0, 160.0, "techno", "techno")
+    assert "BPM" in moment or "tempo" in moment.lower()
+
+
+# ── Energy Inference Tests ──────────────────────────────────────────────
+
+
+def _mock_track(energy=None, dir_energy=None, key="8A", bpm=128.0, genre="techno"):
+    t = MagicMock()
+    t.audio_features = MagicMock() if energy is not None else None
+    if energy is not None:
+        t.audio_features.energy = energy
+    t.dir_energy = dir_energy
+    t.key = key
+    t.bpm = bpm
+    t.dir_genre = genre
+    t.rb_genre = None
+    t.energy_source = None
+    t.energy_predicted = None
+    t.energy_confidence = None
+    t.id = id(t)
+    t.rating = 3
+    t.play_count = 5
+    t.kiku_play_count = 0
+    t.playlist_tags = None
+    return t
+
+
+def _mock_set_track():
+    st = MagicMock()
+    st.inferred_energy = None
+    st.inference_source = None
+    return st
+
+
+def test_infer_energy_interpolation():
+    """Tracks with both neighbors should interpolate."""
+    tracks = [_mock_track(energy=0.3), _mock_track(energy=None), _mock_track(energy=0.9)]
+    set_tracks = [_mock_set_track() for _ in tracks]
+    db = MagicMock()
+    _infer_energy(db, set_tracks, tracks)
+    assert set_tracks[1].inferred_energy == 0.6
+    assert set_tracks[1].inference_source == "interpolation"
+
+
+def test_infer_energy_position_fallback():
+    """Track with no neighbors should use position."""
+    tracks = [_mock_track(), _mock_track(), _mock_track()]
+    # All have no energy
+    for t in tracks:
+        t.audio_features = None
+        t.dir_energy = None
+    set_tracks = [_mock_set_track() for _ in tracks]
+    db = MagicMock()
+    _infer_energy(db, set_tracks, tracks)
+    # First track (position 0/2 = 0.0) should be warmup zone
+    assert set_tracks[0].inferred_energy == 0.3
+    assert set_tracks[0].inference_source == "position"
+
+
+def test_infer_energy_skips_existing():
+    """Tracks with existing energy should not be overwritten."""
+    tracks = [_mock_track(energy=0.8)]
+    set_tracks = [_mock_set_track()]
+    db = MagicMock()
+    _infer_energy(db, set_tracks, tracks)
+    assert set_tracks[0].inferred_energy is None  # Not touched
+
+
+# ── Arc Classification Tests ───────────────────────────────────────────
+
+
+def test_energy_shape_flat():
+    assert _classify_energy_shape([0.5, 0.5, 0.5, 0.5]) == "flat"
+
+
+def test_energy_shape_ramp_up():
+    assert _classify_energy_shape([0.2, 0.3, 0.5, 0.7, 0.9]) == "ramp-up"
+
+
+def test_key_style_home():
+    assert _classify_key_style(["8A", "8A", "8A", "8A"]) == "home-key"
+
+
+def test_key_style_adventurous():
+    assert _classify_key_style(["1A", "3B", "5A", "7B", "9A", "11B", "2A"]) == "adventurous"
+
+
+def test_bpm_style_steady():
+    assert _classify_bpm_style([128.0, 128.0, 128.5, 128.0]) == "steady"
+
+
+def test_bpm_style_volatile():
+    assert _classify_bpm_style([128.0, 145.0, 110.0, 140.0]) == "volatile"
+
+
+# ── Set Pattern Tests ──────────────────────────────────────────────────
+
+
+def test_detect_patterns_with_strong_harmonic():
+    """Should detect strongest dimension pattern."""
+    transitions = [
+        {"harmonic": 0.9, "energy_fit": 0.5, "bpm_compat": 0.5, "genre_coherence": 0.5},
+        {"harmonic": 0.85, "energy_fit": 0.6, "bpm_compat": 0.4, "genre_coherence": 0.5},
+    ]
+    patterns = detect_set_patterns(transitions, [0.3, 0.5, 0.7], ["8A", "8A", "9A"], [128.0, 128.0, 128.0])
+    assert any("key relationships" in p for p in patterns)
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_set_analysis.py -x -q`

#### Task 11 — API integration tests

Tools: editor
File: `tests/api/test_analysis_api.py` (NEW)

````diff
--- /dev/null
+++ b/tests/api/test_analysis_api.py
@@ -0,0 +1,51 @@
+"""Integration tests for set analysis API endpoints."""
+
+
+def test_analyze_set(client, db_session):
+    """POST /api/sets/1/analyze should return analysis with transitions."""
+    resp = client.post("/api/sets/1/analyze")
+    assert resp.status_code == 200
+    data = resp.json()
+    assert data["set_id"] == 1
+    assert data["track_count"] == 5
+    assert data["transition_count"] == 4
+    assert len(data["transitions"]) == 4
+    assert "teaching_moment" in data["transitions"][0]
+    assert "arc" in data
+    assert "energy_shape" in data["arc"]
+    assert "set_patterns" in data
+    assert data["overall_score"] > 0
+
+
+def test_get_analysis_cached(client, db_session):
+    """GET /api/sets/1/analysis should return cached data after analyze."""
+    # First analyze
+    client.post("/api/sets/1/analyze")
+    # Then read cache
+    resp = client.get("/api/sets/1/analysis")
+    assert resp.status_code == 200
+    data = resp.json()
+    assert data["set_id"] == 1
+    assert len(data["transitions"]) == 4
+
+
+def test_get_analysis_not_analyzed(client, db_session):
+    """GET on un-analyzed set should return 404."""
+    # Create a new set without analyzing
+    from kiku.db.models import Set, SetTrack
+    s = Set(id=99, name="Fresh Set")
+    db_session.add(s)
+    db_session.add(SetTrack(set_id=99, position=0, track_id=1))
+    db_session.add(SetTrack(set_id=99, position=1, track_id=2))
+    db_session.commit()
+
+    resp = client.get("/api/sets/99/analysis")
+    assert resp.status_code == 404
+
+
+def test_reanalyze_overwrites(client, db_session):
+    """Re-analyzing should overwrite cached analysis."""
+    resp1 = client.post("/api/sets/1/analyze")
+    ts1 = resp1.json()["analyzed_at"]
+
+    import time
+    time.sleep(0.01)
+
+    resp2 = client.post("/api/sets/1/analyze")
+    ts2 = resp2.json()["analyzed_at"]
+    assert ts2 > ts1
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_analysis_api.py -x -q`

#### Task 12 — Lint all modified files

Tools: shell
Commands:
```bash
source .venv/bin/activate && ruff check --fix src/kiku/analysis/teaching.py src/kiku/analysis/set_analyzer.py src/kiku/api/schemas.py src/kiku/api/routes/sets.py src/kiku/cli.py tests/test_set_analysis.py tests/api/test_analysis_api.py
```
```bash
cd frontend && npx svelte-check --tsconfig ./tsconfig.json
```

#### Task 13 — Commit

Tools: git
Commands:
```bash
git add \
  src/kiku/analysis/teaching.py \
  src/kiku/analysis/set_analyzer.py \
  src/kiku/api/schemas.py \
  src/kiku/api/routes/sets.py \
  src/kiku/cli.py \
  frontend/src/lib/types/index.ts \
  frontend/src/lib/api/sets.ts \
  frontend/src/lib/components/set/SetAnalysisView.svelte \
  frontend/src/lib/components/set/SetView.svelte \
  tests/test_set_analysis.py \
  tests/api/test_analysis_api.py
```
```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
[ "$BRANCH" != "main" ] || { echo 'ERROR: On main'; exit 2; }
git commit -m "spec(011): IMPLEMENT - set-analysis"
```

### Validate

| # | Requirement | Compliance |
|---|-------------|------------|
| 1 | CREATE `src/kiku/analysis/set_analyzer.py` (L10) | Task 2 creates full module with `analyze_set()` |
| 2 | IMPLEMENT per-transition scoring with existing functions (L11) | Task 2 `_score_transitions()` calls `harmonic_score`, `bpm_compatibility`, `genre_coherence`, `energy_fit`, `track_quality` |
| 3 | IMPLEMENT arc analysis: energy, key, BPM, genre (L12-16) | Task 2 `_compute_arc()` with `_classify_energy_shape`, `_classify_key_style`, `_classify_bpm_style`, `_detect_genre_segments` |
| 4 | IMPLEMENT teaching moments engine (L17-20) | Task 1 creates `teaching.py` with `transition_teaching_moment()` and `detect_set_patterns()` |
| 5 | IMPLEMENT energy inference (L21-24) | Task 2 `_infer_energy()` — interpolation + position fallback, never overwrites existing |
| 6 | ADD API endpoint GET analysis (L25) | Task 4 adds `GET /{set_id}/analysis` |
| 7 | ADD API endpoint POST analyze (L26) | Task 4 adds `POST /{set_id}/analyze` |
| 8 | ADD CLI `kiku analyze` (L27) | Task 5 adds Click command resolving by ID or name |
| 9 | CREATE frontend SetAnalysisView (L28) | Task 8 creates full Svelte 5 component |
| 10 | UPDATE analysis_cache (L29) | Task 2 `analyze_set()` writes JSON to `sets.analysis_cache`, sets `is_analyzed=1` |
| 11 | ENSURE re-runnable (L30) | Task 2 overwrites cache on each run; Task 11 tests re-analyze |
| 12 | ADD tests (L31) | Task 10 (unit: 12 tests) + Task 11 (API: 4 tests) |
| 13 | Use existing scoring functions, no duplication (L97) | Task 2 imports from `kiku.setbuilder.scoring` |
| 14 | BRANDING.md voice (L98) | Task 1 teaching messages follow warm/concise/constructive tone |
| 15 | JSON cache, denormalized (L99) | Task 2 stores full `asdict(result)` as JSON |
| 16 | Frontend reuses existing components (L100) | Task 8 imports ScoreBreakdown for expanded transitions |
| 17 | Handle 2–100+ tracks (L101) | Task 2 raises ValueError for <2, iterates for any N |
| 18 | Data structures match spec (L37-68) | Task 2 dataclasses match TransitionAnalysis, ArcAnalysis, SetAnalysis |
| 19 | Teaching moment tiers: strong/good/weak (L72-76) | Task 1 implements all 3 tiers with correct thresholds |
| 20 | Energy inference: neighbors → position fallback (L80-84) | Task 2 `_infer_energy()` follows exact cascade |

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
