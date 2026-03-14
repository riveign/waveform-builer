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

### Training Data Inventory
- **971 tracks** have both `dir_energy` tags AND audio features (viable training set)
- **3,095 tracks** are untagged but have audio features (prediction candidates)
- Class distribution is heavily imbalanced:
  - `mid`: 371, `up`: 355, `dance`: 95, `peak`: 60, `warmup`: 44, `low`: 40, `high`: 4, `closing`: 2
  - As 3 zones: **build: 821** (85%), warmup: 86 (9%), peak: 64 (7%)

### Feature Availability
| Feature | Available | Notes |
|---------|-----------|-------|
| energy | 4,066 | Essentia global energy |
| loudness_lufs | 4,066 | Integrated loudness |
| spectral_centroid | 4,066 | Brightness |
| spectral_complexity | 4,066 | Harmonic density |
| danceability | 4,066 | Essentia danceability |
| energy_intro/body/outro | 4,066 | Energy curve segments |
| mood_happy/sad/aggressive/relaxed | **0** | Analyzer running in separate session |

### Feature Discrimination Analysis
Per-class feature means show **weak separation** with current features:
- `energy`: Nearly identical across all classes (0.91–0.99) — not discriminative
- `loudness_lufs`: Slight differences (-8.2 to -9.5 LUFS) — mild signal
- `spectral_centroid`: Best current signal — Peak=1461, Low=1204 (brighter = higher energy)
- `danceability`: Weak — Dance=1.62 vs Up=1.35, but overlapping distributions
- `energy_curve shape` (body-intro, body-outro): Warmup has highest build shape (0.084) but noisy

### Model Experiments

| Model | Classes | Accuracy | Peak F1 | Warmup F1 | Notes |
|-------|---------|----------|---------|-----------|-------|
| RF vanilla | 3 zones | 84% | 0.06 | 0.10 | Predicts "build" for everything |
| RF balanced weights | 3 zones | 84% | 0.00 | 0.06 | Weights alone don't help |
| RF custom weights (10:1:8) | 3 zones | 83% | 0.00 | 0.08 | Same problem |
| RF oversampled (inside CV) | 3 zones | 83% | 0.10 | 0.19 | Best so far, still poor |
| RF vanilla | 9 granular | 39% | — | — | Too many classes, too few samples |
| GBT merged | 6 classes | 41% | — | — | Not enough signal |

**Feature importance** (RF, 9-class): loudness (0.18), complexity (0.17), danceability (0.17), centroid (0.16) — relatively flat, no dominant feature.

### Key Finding
**Current audio features cannot reliably separate energy zones.** The 84% accuracy is an illusion — the model achieves it by predicting "build" for 98% of inputs. Peak and warmup recall are near-zero (3-13%). The features are too similar across classes without mood data.

**Mood features are critical.** `mood_aggressive` vs `mood_relaxed` and `mood_happy` vs `mood_sad` should provide the missing separation axis. The Essentia mood analyzer is currently running in a separate session.

### Affected Files
- `src/djsetbuilder/analysis/insights.py` — add training data stats
- `src/djsetbuilder/analysis/autotag.py` — **NEW** — classifier training, prediction, model persistence
- `src/djsetbuilder/db/models.py` — add `energy_predicted`, `energy_confidence`, `energy_source` columns to Track
- `src/djsetbuilder/cli.py` — add `autotag` command group
- `data/energy_model.pkl` — serialized model + metadata
- `tests/test_autotag.py` — **NEW**

### Existing Test Patterns
- Tests use `pytest` with fixtures in `tests/test_*.py`
- `test_scoring.py`, `test_camelot.py`, `test_constraints.py` — unit tests for scoring/camelot/constraints
- No test DB fixtures — tests use direct function calls with mock data
- No integration tests currently

### Strategy

#### Approach: Two-phase classifier
1. **Phase A (now)**: Build infrastructure with current features. Model will have honest low accuracy on warmup/peak. Ship it with clear confidence scores and warnings. The DJ gets value from high-confidence build predictions even if peak/warmup are unreliable.
2. **Phase B (after mood analysis)**: Retrain with mood features. Expected significant improvement in peak/warmup separation. The `--retrain` command handles this seamlessly.

#### Implementation plan
1. Add DB columns for predicted energy (`energy_predicted`, `energy_confidence`, `energy_source` on Track)
2. Create `src/djsetbuilder/analysis/autotag.py`:
   - `train_energy_model(session)` — trains RF with oversampling, returns model + metrics
   - `predict_energy(session, model)` — predicts for untagged tracks
   - `save_model(model, metadata, path)` / `load_model(path)` — persistence with joblib
   - Feature engineering: base features + derived (curve shape, ratios)
   - Graceful handling of missing mood features (use if available, skip if not)
3. Add `djset autotag --energy` CLI with `--dry-run`, `--approve`, `--auto`, `--retrain`, `--threshold`
4. Show training report: accuracy, per-class F1, feature importance, class distribution warning
5. On prediction: color-code by confidence (green >0.8, yellow 0.6-0.8, red <0.6)

#### Testing strategy
- **Unit tests** (`tests/test_autotag.py`):
  - Feature extraction with/without mood data
  - Model training with synthetic data (known-separable classes)
  - Prediction output format and confidence scores
  - Model serialization round-trip
  - Retraining incorporates approved predictions
- **Integration**: `djset autotag --energy --dry-run` on real DB (manual verification)

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
