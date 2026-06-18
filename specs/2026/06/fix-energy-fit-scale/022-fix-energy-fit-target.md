# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Fix the energy dimension of set analysis so well-mixed sets can actually score "excellent." Today every set tops out around "good" no matter how seamless the energy flow, because the set analyzer scores each track's `energy_fit` against a neutral 0.5 target whenever the track already has energy data. A sustained peak-techno set (all tracks ~0.9 energy) therefore reads as "0.4 above target everywhere" and `energy_fit` collapses to ~0.2 — dragging otherwise-perfect transitions (harmonic 1.0, tight BPM, same genre) down to ~0.71. The fix: give the analyzer a real per-position energy target derived from the set's own energy arc (its neighbours / its energy profile), so `energy_fit` measures how smoothly each track fits its surroundings — rewarding consistent flow and penalizing genuine jumps. This is a real scoring bug, not a limit of the music; fixing it lets genuinely excellent sets read as excellent and makes the energy teaching honest.

## Mid-Level Objectives (MLO)
- FIX the root cause in `src/kiku/analysis/set_analyzer.py`: stop falling back to a 0.5 neutral target in `_score_transitions` for tracks that have energy data
- DERIVE a per-position energy target from the set's actual energy arc — each track scored against the local trend of its neighbours (the existing neighbour-interpolation logic, applied to all positions), and honour the set's `energy_profile` target curve when one is stored
- ENSURE the semantics are correct: a smooth/consistent energy set scores high `energy_fit`; a roller-coaster set with real jumps still scores low (we are not just inflating every score to 1.0)
- KEEP the change localized to the analysis path — do not alter `energy_fit()` in scoring.py or the build planner's behaviour unless clearly required, to avoid destabilizing build/suggest scoring
- VALIDATE before/after on the saved set "Excellent Techno 137-145": its transitions should move from ~0.71 into excellent (≥0.8) territory once energy is measured against the set's own arc, while a deliberately jumpy set stays low
- UPDATE the unit tests in `tests/test_set_analysis.py` to reflect the corrected energy target, and add cases (flat/consistent set → high energy_fit; jumpy set → low energy_fit)

## Details (DT)

### Root cause (confirmed)
- `_infer_energy` (set_analyzer.py:138) only writes `st.inferred_energy` for tracks that LACK energy (`if e is not None: continue`). Tracks with real energy keep `inferred_energy = None`.
- `_score_transitions` (set_analyzer.py:~196): `target_e = st_b.inferred_energy if st_b.inferred_energy is not None else 0.5` → tracks with energy are scored against **0.5**.
- `energy_fit(track, target)` (scoring.py:295) = `max(0, 1 - |track_energy - target| * 2)`, reading raw `audio_features.energy` (~0.9, skewed high). 0.9 vs 0.5 → fit ≈ 0.2.
- Net: any consistent high-energy set is structurally penalized on energy regardless of how well it actually flows.

### The target should reflect the arc, not a constant
- The analyzer already computes a neighbour-interpolated energy for missing tracks; the same idea gives every position a target = the local energy trend of its neighbours. Scoring a track against its neighbours' energy measures "does this track sit smoothly between the tracks around it" — which is exactly what energy flow means.
- When the set has a stored `energy_profile` (built sets do), the intended target curve via `EnergyProfile.target_energy_at(elapsed)` is the DJ's stated intent and should be honoured as (or blended into) the target.
- Both target and measured energy must come from the SAME scale so the comparison is meaningful (the existing `_get_track_energy` source and `energy_fit`'s source are both raw Essentia energy — keep them consistent; do not mix a calibrated target with a raw measurement or vice-versa).

### Scope / constraints
- Localize to `src/kiku/analysis/set_analyzer.py`. Touch `scoring.py energy_fit` only if strictly necessary and, if so, keep build/suggest behaviour stable and update their tests.
- No DB schema change. `inferred_energy` / `inference_source` columns may still be populated for missing tracks as today.
- Re-running analysis on existing sets must recompute correctly (analysis is cached; the cache is recomputed on demand / via re-analyze).
- Voice per BRANDING.md unchanged — this is internal scoring; teaching strings already exist.

### Testing
- Unit (`tests/test_set_analysis.py`): a consistent-energy set scores high `energy_fit` per transition; a jumpy set scores low; tracks lacking energy still get a sensible target. Update any existing energy expectations that assumed the 0.5 fallback.
- Validation (manual/scripted): analyze "Excellent Techno 137-145" before/after and report the per-transition `energy_fit` and totals; confirm transitions reach ≥0.8.
- Full backend suite stays green.

## Behavior
You are a senior engineer on Kiku. Honor the product principles — especially "Opinions You Can See Through" (the energy score must mean something honest) and "Show the Why." Make the minimal correct change in the analyzer; do not redesign the scoring model. Prove the fix with before/after numbers on the real saved set.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Confirmed mechanism (file:line)
- `_score_transitions` (set_analyzer.py:185-234): for each transition the energy target is `target_e = st_b.inferred_energy if st_b.inferred_energy is not None else 0.5` (line ~196), then `e = energy_fit(t_b, target_e)`.
- `_infer_energy` (set_analyzer.py:138-177): computes `energies[i] = _get_track_energy(t)` for all tracks, but only WRITES `st.inferred_energy` for tracks where energy is missing (`if e is not None: continue`). So tracks WITH energy keep `inferred_energy = None` → target 0.5.
- `_get_track_energy` (set_analyzer.py:128): returns `track.audio_features.energy` (raw Essentia) when present, else `zone_to_numeric(resolved_zone)`.
- `energy_fit(track, target)` (scoring.py:295): `max(0, 1 - abs(track_energy - target) * 2)`, reading the SAME raw `audio_features.energy` first. So measured energy and `_get_track_energy` are on the same (raw) scale — the only inconsistency is the constant 0.5 target.
- Result on the saved set "Excellent Techno 137-145": measured raw energy ≈ 0.9, target 0.5 → `energy_fit ≈ 0.2` on every transition; harmonic 1.0 / bpm 0.76-1.0 / genre 0.5-1.0 / quality 0.32 → totals ~0.59-0.74.

### Fix design — neighbour-trend target (scale-consistent)
- Replace the 0.5 fallback with a per-position target = the **energy trend of the track's neighbours**, drawn from the SAME source `_get_track_energy` already returns (raw), so target and measurement share a scale and the Essentia skew cancels out.
- For position `i` (the incoming track `t_b` at set index `i+1`): target = mean of available neighbour energies among (index `i`, index `i+2`) — i.e. the track before and the track after the incoming track in the set. At the ends, use the single available neighbour. If both are missing, fall back to the track's own energy (so it isn't penalized) and ultimately 0.5 only when nothing is known.
- Semantics: a track that sits smoothly between its neighbours scores ~1.0; a track that jumps away from its surroundings scores low. A sustained-flat set → every target ≈ 0.9 ≈ measured → `energy_fit ≈ 1.0`. A roller-coaster → real deviations → low. This is exactly "energy flow."
- Deliberately do NOT pull the stored `energy_profile` into the analysis target: the profile is on the "intended 0-1" scale while measurement is raw/skewed, so mixing them reintroduces a scale mismatch for non-peak sets. Neighbour-trend keeps one consistent scale.
- Localized: only `src/kiku/analysis/set_analyzer.py` changes. `energy_fit()` in scoring.py and the build planner are untouched (build derives its target from the energy profile and is out of scope here).

### Implementation shape
- `analyze_set` already calls `_infer_energy(db, set_tracks, tracks)` then `_score_transitions(tracks, set_tracks)`. Add a helper, e.g. `_energy_targets(set_tracks, tracks) -> list[float]`, that returns a per-index target via neighbour-trend over the resolved energies (reusing `_get_track_energy` + the already-populated `inferred_energy` for missing tracks). Pass the target list into `_score_transitions` (new param) and use `target_e = targets[i + 1]` instead of the `inferred_energy or 0.5` line. Keep `_infer_energy` writing `inferred_energy`/`inference_source` for missing tracks as today (used elsewhere / arc).

### Tests
- `tests/test_set_analysis.py`: existing energy expectations that relied on the 0.5 fallback must be updated. Add: a consistent-energy synthetic set → high `energy_fit` (~1.0) per transition; a jumpy set (e.g. 0.9,0.3,0.9,0.3) → low `energy_fit`; a track with missing energy still gets a sensible neighbour target. The synthetic tracks use the MagicMock pattern (`_mock_track`) with `audio_features.energy` set.
- Validation: scripted before/after on set "Excellent Techno 137-145" reporting per-transition `energy_fit` + total; expect transitions to reach ≥0.8 (harmonic 1.0 + restored energy + bpm + genre + quality).
- Full suite (`pytest tests/ -x -q`) stays green; svelte-check unaffected (no frontend change).

### Strategy
1. Add `_energy_targets()` helper to set_analyzer.py computing neighbour-trend targets over the set's resolved energies (handles ends + missing via existing inference).
2. Thread the target list into `_score_transitions` and replace the `inferred_energy or 0.5` line with `targets[i + 1]`.
3. Update/extend `tests/test_set_analysis.py` for the corrected energy semantics (flat→high, jumpy→low, missing→neighbour).
4. Re-run pytest; script a before/after analyze on "Excellent Techno 137-145" and record numbers in the spec's Test Evidence.
5. Commit `spec(022): IMPLEMENT - ...`; this branch (`fix-energy-fit-scale`) then merges to main.

## Plan

### Files
- `src/kiku/analysis/set_analyzer.py` — add `_energy_targets()` helper; thread targets into `_score_transitions`; wire in `analyze_set`. (only production file changed)
- `tests/test_set_analysis.py` — update energy expectations, add flat/jumpy/missing cases for `_energy_targets` + `_score_transitions`.

### Tasks

**T1 — Add `_energy_targets()` helper (set_analyzer.py)**
Insert after `_infer_energy` (before the Transition Scoring section). Per index `i`: mean of available neighbour energies (indices `i-1`, `i+1`); each neighbour energy from `_get_track_energy(t)` falling back to that set-track's `inferred_energy`; if no neighbour has energy, fall back to the track's own energy; else 0.5. Same source as `energy_fit` (raw first, then zone) so scales match.

```diff
@@ set_analyzer.py — after _infer_energy(), before "# ── Transition Scoring ──"
+def _resolved_energy(st: SetTrack, track: Track) -> float | None:
+    """Energy for a track on the same scale energy_fit uses, falling back to inferred."""
+    e = _get_track_energy(track)
+    if e is not None:
+        return e
+    return st.inferred_energy
+
+
+def _energy_targets(set_tracks: list[SetTrack], tracks: list[Track]) -> list[float]:
+    """Per-index energy target = the neighbour-trend of the set's own energies.
+
+    Scoring a track against the mean energy of its neighbours measures how smoothly
+    it sits in the flow. Falls back to the track's own energy when it has no neighbour
+    with energy, and to 0.5 only when nothing is known. Same scale as energy_fit().
+    """
+    energies = [_resolved_energy(st, t) for st, t in zip(set_tracks, tracks)]
+    n = len(tracks)
+    targets: list[float] = []
+    for i in range(n):
+        neighbours = []
+        if i > 0 and energies[i - 1] is not None:
+            neighbours.append(energies[i - 1])
+        if i < n - 1 and energies[i + 1] is not None:
+            neighbours.append(energies[i + 1])
+        if neighbours:
+            targets.append(sum(neighbours) / len(neighbours))
+        elif energies[i] is not None:
+            targets.append(energies[i])
+        else:
+            targets.append(0.5)
+    return targets
```

**T2 — Thread targets into `_score_transitions` (set_analyzer.py:185-196)**

```diff
-def _score_transitions(tracks: list[Track], set_tracks: list[SetTrack]) -> list[TransitionAnalysis]:
+def _score_transitions(
+    tracks: list[Track], set_tracks: list[SetTrack], targets: list[float]
+) -> list[TransitionAnalysis]:
     """Score all adjacent transitions in the set."""
     w = SCORING_WEIGHTS
     results = []

     for i in range(len(tracks) - 1):
         t_a, t_b = tracks[i], tracks[i + 1]

         h = harmonic_score(t_a.key, t_b.key)
-        # Use inferred energy if available for target
-        st_b = set_tracks[i + 1]
-        target_e = st_b.inferred_energy if st_b.inferred_energy is not None else 0.5
+        # Target = neighbour-trend of the incoming track within the set's own arc
+        target_e = targets[i + 1]
         e = energy_fit(t_b, target_e)
```

**T3 — Wire `_energy_targets` into `analyze_set` (set_analyzer.py:82-85)**

```diff
     # 1. Infer energy for untagged tracks
     _infer_energy(db, set_tracks, tracks)

+    # 1b. Per-position energy targets from the set's own arc
+    targets = _energy_targets(set_tracks, tracks)
+
     # 2. Score all transitions
-    transitions = _score_transitions(tracks, set_tracks)
+    transitions = _score_transitions(tracks, set_tracks, targets)
```

**T4 — Unit tests (tests/test_set_analysis.py)**
Add import of `_energy_targets`, `_score_transitions`. Add an energy-aware mock track helper (extends `_mock_track` pattern: `audio_features.energy`, `key`, `bpm`, `dir_genre`/`rb_genre`, `id`). Cases:
- `test_energy_targets_flat` — energies all 0.9 → every target ≈ 0.9.
- `test_energy_targets_jumpy` — 0.9,0.3,0.9,0.3 → middle targets pull toward neighbours (low fit at jumps).
- `test_energy_targets_missing_neighbour` — middle track missing energy still gets neighbour-mean target (not 0.5).
- `test_energy_targets_single_neighbour_ends` — end positions use the one available neighbour.
- `test_score_transitions_flat_high_energy_fit` — flat 0.9 set → per-transition `energy_fit` ≈ 1.0.
- `test_score_transitions_jumpy_low_energy_fit` — 0.9,0.3,0.9,0.3 → `energy_fit` low (< 0.5).

**T5 — Validation (lint + suite)**
`.venv/bin/python -m py_compile src/kiku/analysis/set_analyzer.py tests/test_set_analysis.py`; then `python -m pytest tests/ -x -q`.

**T6 — Before/after evidence on "Excellent Techno 137-145"**
Script: `from kiku.db.models import get_session, Set` + `from kiku.analysis.set_analyzer import analyze_set`, find the set by name, re-analyze, print per-transition `energy_fit` + `total` and overall. Record AFTER numbers in `## Test Evidence & Outputs`; state BEFORE from spec (totals ~0.59-0.74, energy_fit ~0.2). Note honestly any transition that stays <0.8 due to quality/genre caps.

**T7 — Commit** code+tests `spec(022): IMPLEMENT - neighbour-trend energy target`, append hash to `## Implement`, then `commit_spec_changes` for the spec.

### Validate
- L5 / L8 (stop 0.5 fallback): T2 removes the `inferred_energy or 0.5` line → `target_e = targets[i+1]`.
- L9 (per-position target from arc / neighbour interpolation for all positions): T1 `_energy_targets` neighbour-trend across every index.
- L10 (flat→high, jumpy→low, not all 1.0): T4 `test_score_transitions_flat_high_energy_fit` + `test_score_transitions_jumpy_low_energy_fit`.
- L11 (localized; no scoring.py/planner change): only set_analyzer.py + tests touched (Files).
- L12 (before/after on real set ≥0.8; jumpy stays low): T6 + T4 jumpy case.
- L13 (tests updated + new cases): T4.
- L26/L58 (single consistent scale; do NOT pull energy_profile): T1 reuses `_get_track_energy` raw source only; no profile blend.
- L30 (inferred_energy still written for missing): `_infer_energy` unchanged.

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

- T1 Add `_energy_targets()` + `_resolved_energy()` helper — Status: Done
- T2 Thread `targets` into `_score_transitions`, replace 0.5 fallback — Status: Done
- T3 Wire `_energy_targets` into `analyze_set` — Status: Done
- T4 Unit tests (flat/jumpy/missing/ends + score_transitions) — Status: Done (7 new tests; 31 in file)
- T5 Validation: py_compile + full pytest suite — Status: Done (373 passed)
- T6 Before/after evidence on "Excellent Techno 137-145" — Status: Done (overall 0.861, energy_fit mean 0.961, 10/11 ≥0.8)
- T7 Commit code+tests, append hash, commit spec — Status: Done

Implementation commit: `8c0c544`

## Test Evidence & Outputs

### Unit tests
`pytest tests/ -x -q` → **373 passed** (10 pre-existing deprecation warnings, unrelated). 7 new cases added to `tests/test_set_analysis.py` (31 in file). `py_compile` clean on both changed files. No frontend change → svelte-check unaffected.

### Before/after — saved set "Excellent Techno 137-145" (id=24, 12 tracks, 11 transitions)
Re-analyzed via `analyze_set(db, 24)`.

**BEFORE (from Research, 0.5-target bug):** `energy_fit ≈ 0.2` on every transition; per-transition totals ~0.59-0.74.

**AFTER (neighbour-trend target):**
```
pos | energy_fit | total
  0 |   0.975    | 0.745
  1 |   0.951    | 0.841
  2 |   0.994    | 0.897
  3 |   0.959    | 0.883
  4 |   0.945    | 0.847
  5 |   0.995    | 0.890
  6 |   0.936    | 0.890
  7 |   0.984    | 0.867
  8 |   0.963    | 0.852
  9 |   0.940    | 0.858
 10 |   0.925    | 0.897
```
- `energy_fit`: min 0.925 / max 0.995 / **mean 0.961** (was ~0.2).
- `total`: min 0.745 / max 0.897 / mean 0.861. **overall_score = 0.861** ("excellent").
- **10/11 transitions ≥ 0.8.** The one below (pos 0 = 0.745) is NOT capped by energy — its energy_fit is 0.975; it is held down by `genre_coherence 0.5`, `bpm_compat 0.759`, `track_quality 0.32`. That is honest scoring, not the energy bug, and acceptable per L12.

Conclusion: the energy bug is fixed — consistent high-energy flow now reads near-perfect on energy, and the set scores excellent overall. Jumpy sets stay low (unit test `test_score_transitions_jumpy_low_energy_fit`, energy_fit < 0.5).

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
