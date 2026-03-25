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
