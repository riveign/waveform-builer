# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Auto-classify energy zones (warmup/build/peak) for untagged tracks using audio features, trained on the user's existing ~975 manually tagged tracks as ground truth. The DJ's energy tags are personal and subjective — the model learns what *this DJ* means by each zone, then predicts for the remaining ~3,100 untagged tracks.

## Mid-Level Objectives (MLO)
- TRAIN a lightweight classifier on the user's existing `dir_energy` tags using audio features only — **BPM is explicitly excluded** (tempo and energy/mood are independent concepts)
- USE audio features as inputs: `energy`, `loudness_lufs`, `spectral_centroid`, `spectral_complexity`, `mood_happy`, `mood_sad`, `mood_aggressive`, `mood_relaxed`, `energy_intro`, `energy_body`, `energy_outro`, `danceability`
- MAP the 9 existing energy tags (`low`, `warmup`, `closing`, `mid`, `dance`, `up`, `high`, `fast`, `peak`) into 3 zones: warmup (1-3), build (4-6), peak (7-9), preserving the original granular tag as the prediction target
- OUTPUT confidence scores with each prediction so the DJ can review uncertain calls
- CREATE `djset autotag --energy` CLI command with modes:
  - `--dry-run`: show predictions without writing (default)
  - `--approve`: interactive review of suggestions, accept/reject per track
  - `--auto`: write all predictions above a confidence threshold
  - `--threshold 0.7`: minimum confidence to suggest (default 0.7)
- STORE predicted energy tags in a way that distinguishes them from manual tags (e.g., `dir_energy_predicted` column or a `predicted` flag)
- SUPPORT incremental retraining: when the DJ approves/corrects predictions or adds new manual tags, `djset autotag --energy --retrain` retrains the model incorporating all current tags (manual + approved predictions) as ground truth
- TRACK training lineage: store training metadata (date, sample count per class, accuracy, feature importance) alongside the model so the DJ can see how the model evolves over time

## Details (DT)

### Why BPM is excluded
A 125 BPM track can be peak energy (heavy kicks, distorted bass, aggressive mood). A 150 BPM track can be a deep warmup (minimal, hypnotic, low loudness). Speed and intensity are different dimensions. The classifier must learn energy from the *sound* of the music, not its tempo.

### Training data
- ~975 tracks have `dir_energy` tags (manual, from directory structure)
- These map to the `ENERGY_TAG_VALUES` dict in `constraints.py`
- The classifier should use the granular tags (all 9) as classes, not just the 3 zones
- Audio features come from the `audio_features` table — tracks without features should be skipped

### Feature engineering considerations
- Energy curve *shape* matters: `energy_body - energy_intro` (does it build?), `energy_body - energy_outro` (does it drop?)
- Mood ratios may be more useful than raw values: `mood_aggressive / (mood_relaxed + 0.01)`
- Missing features should be handled gracefully (some tracks may lack mood data if analysis is incomplete)

### Model choice
- scikit-learn is preferred (already a transitive dependency, lightweight)
- Random Forest or Gradient Boosting — interpretable, handles mixed feature types
- Model should be serialized to `data/` directory for reuse without retraining
- Include feature importance output so the DJ can understand what drives predictions

### Retraining loop
- The model improves through a feedback cycle: predict → DJ reviews → approvals become new training data → retrain → better predictions
- `--retrain` rebuilds the model from scratch using all tracks that have a confirmed energy tag (manual `dir_energy` + approved predictions)
- Report delta: "Model v2: trained on 1,847 tracks (was 975). Accuracy improved from 78% to 84%"
- Old model is backed up before overwriting (e.g., `data/energy_model.v1.pkl`)

### CLI UX
- `djset autotag --energy --dry-run` shows a Rich table: Title, Artist, Current Tag (if any), Predicted Tag, Confidence, with color coding by confidence level
- `djset autotag --energy --approve` same table but prompts Y/n per track (or batch)
- Summary at end: "Tagged X tracks (Y high confidence, Z medium confidence)"

### Constraints
- Must not overwrite existing manual `dir_energy` tags unless explicitly requested with `--force`
- Minimum training samples per class: warn if any energy tag has < 10 examples
- Cross-validation accuracy should be reported during training so the DJ knows if the model is trustworthy

## Behavior
You are building a teaching tool, not just a classifier. The DJ is learning to understand their own library. Feature importance, confidence scores, and explanations are as valuable as the predictions themselves. Frame outputs in the mentorship tone: help the DJ see patterns, not just accept labels.

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
