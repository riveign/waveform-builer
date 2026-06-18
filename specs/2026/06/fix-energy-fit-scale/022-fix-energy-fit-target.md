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
