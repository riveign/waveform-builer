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
