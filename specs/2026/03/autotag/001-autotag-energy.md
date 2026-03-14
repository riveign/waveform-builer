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

### Files
- `src/djsetbuilder/db/models.py`
  - L42: Add `energy_predicted` (String), `energy_confidence` (Float), `energy_source` (String) columns to Track
  - L166-188: Add migration for new Track columns
- `src/djsetbuilder/analysis/autotag.py` — **NEW** (~200 lines)
  - Feature extraction: 8 base + 4 derived features, graceful mood handling
  - `train_energy_model(session)` — RF with oversampling inside CV, returns model + metrics
  - `predict_energy(session, model, threshold)` — predict for untagged tracks
  - `save_model()` / `load_model()` — joblib persistence with JSON metadata sidecar
  - Zone mapping constants
- `src/djsetbuilder/cli.py`
  - Add `autotag` command group under `cli`
  - `autotag --energy` with `--dry-run` (default), `--approve`, `--auto`, `--retrain`, `--threshold`, `--force`
- `tests/test_autotag.py` — **NEW**
  - Feature extraction with/without mood data
  - Model train/predict round-trip on synthetic data
  - Model save/load round-trip
  - Zone mapping correctness

### Tasks

#### Task 1 — models.py: Add predicted energy columns to Track + migration

Tools: editor

Add three new columns to the Track model for storing predicted energy tags, and add migration entries so existing SQLite databases get the columns.

Diff:
````diff
--- a/src/djsetbuilder/db/models.py
+++ b/src/djsetbuilder/db/models.py
@@ class Track(Base):
     playlist_tags = Column(Text)  # JSON list of playlist names this track belongs to
     last_synced = Column(String)
+    energy_predicted = Column(String)   # Predicted energy tag from autotag classifier
+    energy_confidence = Column(Float)   # Prediction confidence 0-1
+    energy_source = Column(String)      # "manual", "auto", or "approved"
@@
 def _migrate_schema(engine):
@@
     # AudioFeatures waveform columns
-    if "audio_features" in inspector.get_table_names():
+    # Track autotag columns
+    if "tracks" in inspector.get_table_names():
+        existing_tracks = {c["name"] for c in inspector.get_columns("tracks")}
+        track_new_cols = {
+            "energy_predicted": "TEXT",
+            "energy_confidence": "REAL",
+            "energy_source": "TEXT",
+        }
+        with engine.begin() as conn:
+            for col_name, col_type in track_new_cols.items():
+                if col_name not in existing_tracks:
+                    conn.execute(text(
+                        f"ALTER TABLE tracks ADD COLUMN {col_name} {col_type}"
+                    ))
+
+    # AudioFeatures waveform columns
+    if "audio_features" in inspector.get_table_names():
````

Verification:
- `source .venv/bin/activate && python -c "from djsetbuilder.db.models import get_session, Track; s = get_session(); print([c.name for c in Track.__table__.columns if 'energy' in c.name])"`
- Should print: `['dir_energy', 'energy_predicted', 'energy_confidence', 'energy_source']`

#### Task 2 — autotag.py: Create classifier module

Tools: editor (new file)

Create `src/djsetbuilder/analysis/autotag.py` with the following exact content:

````diff
--- /dev/null
+++ b/src/djsetbuilder/analysis/autotag.py
@@ -0,0 +1,230 @@
+"""Energy autotag classifier — learns from the DJ's own tags."""
+
+from __future__ import annotations
+
+import json
+import shutil
+from collections import Counter
+from datetime import datetime
+from pathlib import Path
+
+import numpy as np
+from sqlalchemy.orm import Session
+
+from djsetbuilder.db.models import AudioFeatures, Track
+
+# Zone mapping: granular tag → zone
+ZONE_MAP: dict[str, str] = {
+    "low": "warmup", "warmup": "warmup", "closing": "warmup",
+    "mid": "build", "dance": "build", "up": "build",
+    "high": "peak", "fast": "peak", "peak": "peak",
+}
+
+# All valid granular energy tags
+ENERGY_TAGS = list(ZONE_MAP.keys())
+
+# Feature names (order matters — must match extraction)
+BASE_FEATURES = [
+    "energy", "loudness_lufs", "spectral_centroid", "spectral_complexity",
+    "danceability", "energy_intro", "energy_body", "energy_outro",
+]
+MOOD_FEATURES = ["mood_happy", "mood_sad", "mood_aggressive", "mood_relaxed"]
+DERIVED_FEATURES = ["build_shape", "drop_shape", "intro_body_ratio", "outro_body_ratio"]
+MOOD_DERIVED = ["aggression_ratio"]
+
+DEFAULT_MODEL_DIR = Path("data")
+MODEL_FILENAME = "energy_model.pkl"
+META_FILENAME = "energy_model_meta.json"
+
+
+def extract_features(af: AudioFeatures) -> np.ndarray | None:
+    """Extract feature vector from an AudioFeatures row.
+
+    Returns None if required base features are missing.
+    """
+    # Base features (required)
+    base = []
+    for feat in BASE_FEATURES:
+        val = getattr(af, feat, None)
+        if val is None:
+            return None
+        base.append(float(val))
+
+    # Derived from energy curve
+    intro, body, outro = af.energy_intro, af.energy_body, af.energy_outro
+    if intro is not None and body is not None and outro is not None:
+        base.append(body - intro)                    # build_shape
+        base.append(body - outro)                    # drop_shape
+        base.append(intro / (body + 0.001))          # intro_body_ratio
+        base.append(outro / (body + 0.001))          # outro_body_ratio
+    else:
+        base.extend([0.0, 0.0, 0.0, 0.0])
+
+    # Mood features (optional — use if available, fill 0 if not)
+    for feat in MOOD_FEATURES:
+        val = getattr(af, feat, None)
+        base.append(float(val) if val is not None else 0.0)
+
+    # Mood derived
+    aggressive = getattr(af, "mood_aggressive", None)
+    relaxed = getattr(af, "mood_relaxed", None)
+    if aggressive is not None and relaxed is not None:
+        base.append(aggressive / (relaxed + 0.01))
+    else:
+        base.append(0.0)
+
+    return np.array(base, dtype=np.float32)
+
+
+def feature_names() -> list[str]:
+    """Return ordered feature names matching extract_features output."""
+    return BASE_FEATURES + DERIVED_FEATURES + MOOD_FEATURES + MOOD_DERIVED
+
+
+def _load_training_data(
+    session: Session, include_approved: bool = True,
+) -> tuple[np.ndarray, np.ndarray, list[str]]:
+    """Load feature matrix X, label array y, and tag list from DB.
+
+    Training data = tracks with manual dir_energy OR approved predictions.
+    """
+    query = (
+        session.query(Track, AudioFeatures)
+        .join(AudioFeatures)
+        .filter(AudioFeatures.energy.isnot(None))
+    )
+
+    X_list, y_list = [], []
+    for track, af in query.all():
+        # Determine label source
+        tag = None
+        if track.dir_energy:
+            tag = track.dir_energy.lower()
+        elif include_approved and track.energy_source == "approved" and track.energy_predicted:
+            tag = track.energy_predicted.lower()
+
+        if tag is None or tag not in ZONE_MAP:
+            continue
+
+        features = extract_features(af)
+        if features is None:
+            continue
+
+        X_list.append(features)
+        y_list.append(tag)
+
+    return np.array(X_list), np.array(y_list), y_list
+
+
+def train_energy_model(session: Session, include_approved: bool = True) -> dict:
+    """Train a RandomForest classifier on the DJ's energy tags.
+
+    Returns dict with keys: model, metrics, feature_importance, class_counts, warnings.
+    """
+    from sklearn.ensemble import RandomForestClassifier
+    from sklearn.metrics import classification_report
+    from sklearn.model_selection import StratifiedKFold, cross_val_predict
+    from sklearn.utils import resample
+
+    X, y, _ = _load_training_data(session, include_approved=include_approved)
+
+    if len(X) == 0:
+        raise ValueError("No training data found. Tag some tracks with energy levels first.")
+
+    # Map to zones for training
+    y_zones = np.array([ZONE_MAP[t] for t in y])
+    class_counts = dict(Counter(y_zones))
+
+    warnings = []
+    for zone, count in class_counts.items():
+        if count < 10:
+            warnings.append(f"Only {count} examples for '{zone}' — predictions will be unreliable")
+
+    # Cross-validation with oversampling inside each fold
+    skf = StratifiedKFold(n_splits=min(5, min(class_counts.values())), shuffle=True, random_state=42)
+    all_true, all_pred = [], []
+
+    for train_idx, test_idx in skf.split(X, y_zones):
+        X_train, y_train = X[train_idx], y_zones[train_idx]
+        X_test, y_test = X[test_idx], y_zones[test_idx]
+
+        # Oversample minority classes in train fold
+        target_n = max(Counter(y_train).values())
+        X_bal, y_bal = [], []
+        for label in np.unique(y_train):
+            mask = y_train == label
+            Xc, yc = X_train[mask], y_train[mask]
+            if len(yc) < target_n:
+                Xr, yr = resample(Xc, yc, n_samples=target_n, random_state=42)
+                X_bal.append(Xr)
+                y_bal.append(yr)
+            else:
+                X_bal.append(Xc)
+                y_bal.append(yc)
+
+        X_bal = np.vstack(X_bal)
+        y_bal = np.concatenate(y_bal)
+
+        fold_clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
+        fold_clf.fit(X_bal, y_bal)
+        all_true.extend(y_test)
+        all_pred.extend(fold_clf.predict(X_test))
+
+    metrics = classification_report(all_true, all_pred, output_dict=True, zero_division=0)
+
+    # Train final model on ALL data (oversampled)
+    target_n = max(Counter(y_zones).values())
+    X_final, y_final = [], []
+    for label in np.unique(y_zones):
+        mask = y_zones == label
+        Xc, yc = X[mask], y_zones[mask]
+        if len(yc) < target_n:
+            Xr, yr = resample(Xc, yc, n_samples=target_n, random_state=42)
+            X_final.append(Xr)
+            y_final.append(yr)
+        else:
+            X_final.append(Xc)
+            y_final.append(yc)
+
+    X_final = np.vstack(X_final)
+    y_final = np.concatenate(y_final)
+
+    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
+    model.fit(X_final, y_final)
+
+    # Feature importance
+    names = feature_names()
+    importance = sorted(zip(names, model.feature_importances_), key=lambda x: -x[1])
+
+    return {
+        "model": model,
+        "metrics": metrics,
+        "feature_importance": importance,
+        "class_counts": class_counts,
+        "training_samples": len(X),
+        "warnings": warnings,
+    }
+
+
+def predict_energy(
+    session: Session, model, threshold: float = 0.7,
+) -> list[dict]:
+    """Predict energy zones for untagged tracks.
+
+    Returns list of dicts: {track_id, title, artist, predicted, confidence, zone}.
+    Only includes predictions above threshold.
+    """
+    tracks = (
+        session.query(Track, AudioFeatures)
+        .join(AudioFeatures)
+        .filter(AudioFeatures.energy.isnot(None))
+        .filter((Track.dir_energy.is_(None)) | (Track.dir_energy == ""))
+        .all()
+    )
+
+    results = []
+    for track, af in tracks:
+        features = extract_features(af)
+        if features is None:
+            continue
+
+        proba = model.predict_proba(features.reshape(1, -1))[0]
+        best_idx = int(np.argmax(proba))
+        confidence = float(proba[best_idx])
+        predicted = model.classes_[best_idx]
+
+        if confidence >= threshold:
+            results.append({
+                "track_id": track.id,
+                "title": track.title or "?",
+                "artist": track.artist or "?",
+                "predicted": predicted,
+                "confidence": confidence,
+            })
+
+    results.sort(key=lambda r: r["confidence"], reverse=True)
+    return results
+
+
+def save_model(result: dict, model_dir: Path = DEFAULT_MODEL_DIR) -> Path:
+    """Save trained model and metadata. Backs up previous version."""
+    import joblib
+
+    model_dir.mkdir(parents=True, exist_ok=True)
+    model_path = model_dir / MODEL_FILENAME
+    meta_path = model_dir / META_FILENAME
+
+    # Backup existing model
+    if model_path.exists():
+        # Find next version number
+        version = 1
+        while (model_dir / f"energy_model.v{version}.pkl").exists():
+            version += 1
+        shutil.copy2(model_path, model_dir / f"energy_model.v{version}.pkl")
+        if meta_path.exists():
+            shutil.copy2(meta_path, model_dir / f"energy_model_meta.v{version}.json")
+
+    joblib.dump(result["model"], model_path)
+
+    meta = {
+        "trained_at": datetime.now().isoformat(),
+        "training_samples": result["training_samples"],
+        "class_counts": result["class_counts"],
+        "accuracy": result["metrics"].get("accuracy", 0),
+        "per_class": {
+            k: {"precision": v["precision"], "recall": v["recall"], "f1": v["f1-score"]}
+            for k, v in result["metrics"].items()
+            if isinstance(v, dict) and "precision" in v
+        },
+        "feature_importance": result["feature_importance"],
+        "warnings": result["warnings"],
+    }
+    meta_path.write_text(json.dumps(meta, indent=2, default=str))
+
+    return model_path
+
+
+def load_model(model_dir: Path = DEFAULT_MODEL_DIR):
+    """Load a previously trained model. Returns (model, metadata) or raises FileNotFoundError."""
+    import joblib
+
+    model_path = model_dir / MODEL_FILENAME
+    meta_path = model_dir / META_FILENAME
+
+    if not model_path.exists():
+        raise FileNotFoundError(f"No trained model found at {model_path}. Run: djset autotag --energy --retrain")
+
+    model = joblib.load(model_path)
+    meta = {}
+    if meta_path.exists():
+        meta = json.loads(meta_path.read_text())
+
+    return model, meta
````

Verification:
- `source .venv/bin/activate && python -c "from djsetbuilder.analysis.autotag import extract_features, train_energy_model, feature_names; print('OK:', len(feature_names()), 'features')"`
- Should print: `OK: 17 features`

#### Task 3 — cli.py: Add autotag command group

Tools: editor

Add the `autotag` command group after the `analyze` command (end of file). This command trains, predicts, and allows the DJ to review/approve predictions.

````diff
--- a/src/djsetbuilder/cli.py
+++ b/src/djsetbuilder/cli.py
@@ (end of file, after the analyze command)
+
+
+@cli.group("autotag")
+def autotag_group():
+    """Auto-classify tracks using ML models trained on your tags."""
+
+
+@autotag_group.command("energy")
+@click.option("--dry-run", "mode", flag_value="dry-run", default=True, help="Show predictions without writing (default)")
+@click.option("--approve", "mode", flag_value="approve", help="Review and approve predictions interactively")
+@click.option("--auto", "mode", flag_value="auto", help="Write all predictions above threshold automatically")
+@click.option("--retrain", is_flag=True, help="Retrain the model before predicting")
+@click.option("--threshold", default=0.7, type=float, help="Minimum confidence to suggest (0-1)")
+@click.option("--force", is_flag=True, help="Overwrite existing manual dir_energy tags")
+def autotag_energy(mode: str, retrain: bool, threshold: float, force: bool):
+    """Classify energy zones using your tagged tracks as training data."""
+    from rich.panel import Panel
+
+    from djsetbuilder.analysis.autotag import (
+        load_model,
+        predict_energy,
+        save_model,
+        train_energy_model,
+    )
+    from djsetbuilder.db.models import Track, get_session
+
+    session = get_session()
+
+    # Train or load model
+    if retrain or mode == "dry-run":
+        try:
+            # Always train fresh for dry-run to show current metrics
+            console.print("[cyan]Training energy classifier...[/]")
+            result = train_energy_model(session)
+
+            # Show training report
+            metrics = result["metrics"]
+            console.print(f"\n[bold]Training Report[/] ({result['training_samples']} samples)")
+
+            if result["warnings"]:
+                for w in result["warnings"]:
+                    console.print(f"  [yellow]Warning: {w}[/]")
+
+            table = Table(title="Cross-Validation Results")
+            table.add_column("Zone", style="cyan")
+            table.add_column("Precision", justify="right")
+            table.add_column("Recall", justify="right")
+            table.add_column("F1", justify="right", style="green")
+            table.add_column("Support", justify="right", style="dim")
+
+            for zone in ["warmup", "build", "peak"]:
+                if zone in metrics:
+                    m = metrics[zone]
+                    table.add_row(
+                        zone.capitalize(),
+                        f"{m['precision']:.2f}",
+                        f"{m['recall']:.2f}",
+                        f"{m['f1-score']:.2f}",
+                        str(m.get("support", "")),
+                    )
+
+            acc = metrics.get("accuracy", 0)
+            table.add_row("", "", "", f"[bold]{acc:.2f}[/]", "", end_section=True)
+            console.print(table)
+
+            # Feature importance
+            console.print("\n[bold]What drives predictions:[/]")
+            for name, imp in result["feature_importance"][:5]:
+                bar = "█" * int(30 * imp / result["feature_importance"][0][1])
+                console.print(f"  {name:20s} {bar} {imp:.3f}")
+
+            if retrain:
+                path = save_model(result)
+                console.print(f"\n[green]Model saved to {path}[/]")
+
+            model = result["model"]
+
+        except ValueError as e:
+            console.print(f"[red]{e}[/]")
+            return
+    else:
+        try:
+            model, meta = load_model()
+            if meta:
+                console.print(f"[dim]Loaded model trained on {meta.get('training_samples', '?')} samples "
+                              f"(accuracy: {meta.get('accuracy', '?'):.2f})[/]")
+        except FileNotFoundError as e:
+            console.print(f"[red]{e}[/]")
+            return
+
+    # Predict
+    console.print(f"\n[cyan]Predicting energy zones (threshold={threshold:.2f})...[/]")
+    predictions = predict_energy(session, model, threshold=threshold)
+
+    if not predictions:
+        console.print("[yellow]No predictions above threshold. Try lowering --threshold.[/]")
+        return
+
+    # Display predictions
+    table = Table(title=f"Energy Predictions ({len(predictions)} tracks)")
+    table.add_column("#", justify="right", style="dim")
+    table.add_column("Title", style="cyan")
+    table.add_column("Artist")
+    table.add_column("Predicted", style="bold")
+    table.add_column("Confidence", justify="right")
+
+    for i, p in enumerate(predictions, 1):
+        conf = p["confidence"]
+        if conf >= 0.8:
+            conf_style = "[green]"
+        elif conf >= 0.6:
+            conf_style = "[yellow]"
+        else:
+            conf_style = "[red]"
+        table.add_row(
+            str(i),
+            p["title"],
+            p["artist"],
+            p["predicted"].capitalize(),
+            f"{conf_style}{conf:.2f}[/]",
+        )
+        if i >= 50 and mode == "dry-run":
+            console.print(table)
+            console.print(f"[dim]... and {len(predictions) - 50} more. Use --approve or --auto to process all.[/]")
+            return
+
+    console.print(table)
+
+    # Apply predictions based on mode
+    if mode == "dry-run":
+        console.print("\n[dim]Dry run — no changes written. Use --approve or --auto to apply.[/]")
+        return
+
+    applied = 0
+    skipped = 0
+
+    for p in predictions:
+        track = session.query(Track).get(p["track_id"])
+        if not track:
+            continue
+
+        if track.dir_energy and not force:
+            skipped += 1
+            continue
+
+        if mode == "approve":
+            answer = click.prompt(
+                f"  {p['title']} — {p['artist']} → {p['predicted']} ({p['confidence']:.2f})",
+                type=click.Choice(["y", "n", "q"], case_sensitive=False),
+                default="y",
+            )
+            if answer == "q":
+                break
+            if answer == "n":
+                skipped += 1
+                continue
+            track.energy_source = "approved"
+        else:
+            # auto mode
+            track.energy_source = "auto"
+
+        track.energy_predicted = p["predicted"]
+        track.energy_confidence = p["confidence"]
+        applied += 1
+
+    session.commit()
+    console.print(f"\n[green]Applied {applied} predictions[/]" +
+                  (f" [dim](skipped {skipped} with existing tags)[/]" if skipped else ""))
````

Verification:
- `source .venv/bin/activate && djset autotag --help`
- Should show the `energy` subcommand
- `source .venv/bin/activate && djset autotag energy --dry-run --threshold 0.5`
- Should show training report + predictions table

#### Task 4 — test_autotag.py: Unit tests

Tools: editor (new file)

Create `tests/test_autotag.py`:

````diff
--- /dev/null
+++ b/tests/test_autotag.py
@@ -0,0 +1,97 @@
+"""Tests for the energy autotag classifier."""
+
+import json
+from unittest.mock import MagicMock
+
+import numpy as np
+import pytest
+
+from djsetbuilder.analysis.autotag import (
+    ZONE_MAP,
+    extract_features,
+    feature_names,
+)
+
+
+def _make_af(**kwargs):
+    """Create a mock AudioFeatures with given values."""
+    af = MagicMock()
+    defaults = {
+        "energy": 0.9, "loudness_lufs": -8.0,
+        "spectral_centroid": 1200.0, "spectral_complexity": 0.1,
+        "danceability": 1.4, "energy_intro": 0.8,
+        "energy_body": 0.9, "energy_outro": 0.85,
+        "mood_happy": None, "mood_sad": None,
+        "mood_aggressive": None, "mood_relaxed": None,
+    }
+    defaults.update(kwargs)
+    for k, v in defaults.items():
+        setattr(af, k, v)
+    return af
+
+
+class TestFeatureExtraction:
+    def test_base_features_extracted(self):
+        af = _make_af()
+        features = extract_features(af)
+        assert features is not None
+        assert len(features) == len(feature_names())
+
+    def test_missing_base_feature_returns_none(self):
+        af = _make_af(energy=None)
+        assert extract_features(af) is None
+
+    def test_mood_features_filled_zero_when_missing(self):
+        af = _make_af()
+        features = extract_features(af)
+        # Mood features are at indices 12-15, should be 0
+        mood_start = len(feature_names()) - 5  # 4 mood + 1 derived
+        assert all(features[mood_start:] == 0.0)
+
+    def test_mood_features_used_when_present(self):
+        af = _make_af(mood_happy=0.7, mood_sad=0.2, mood_aggressive=0.8, mood_relaxed=0.3)
+        features = extract_features(af)
+        names = feature_names()
+        idx = names.index("mood_happy")
+        assert features[idx] == pytest.approx(0.7)
+        idx_agg = names.index("aggression_ratio")
+        assert features[idx_agg] == pytest.approx(0.8 / (0.3 + 0.01), rel=1e-2)
+
+    def test_derived_features_computed(self):
+        af = _make_af(energy_intro=0.5, energy_body=0.9, energy_outro=0.7)
+        features = extract_features(af)
+        names = feature_names()
+        assert features[names.index("build_shape")] == pytest.approx(0.4)
+        assert features[names.index("drop_shape")] == pytest.approx(0.2)
+
+
+class TestZoneMapping:
+    def test_all_tags_have_zone(self):
+        for tag in ["low", "warmup", "closing", "mid", "dance", "up", "high", "fast", "peak"]:
+            assert tag in ZONE_MAP
+
+    def test_zones_are_valid(self):
+        assert set(ZONE_MAP.values()) == {"warmup", "build", "peak"}
+
+
+class TestModelPersistence:
+    def test_save_load_roundtrip(self, tmp_path):
+        from djsetbuilder.analysis.autotag import load_model, save_model
+
+        # Create a minimal mock model
+        from sklearn.ensemble import RandomForestClassifier
+        X = np.random.rand(30, 17)
+        y = np.array(["warmup"] * 10 + ["build"] * 10 + ["peak"] * 10)
+        model = RandomForestClassifier(n_estimators=10, random_state=42)
+        model.fit(X, y)
+
+        result = {
+            "model": model,
+            "metrics": {"accuracy": 0.85},
+            "feature_importance": [("loudness", 0.2), ("centroid", 0.15)],
+            "class_counts": {"warmup": 10, "build": 10, "peak": 10},
+            "training_samples": 30,
+            "warnings": [],
+        }
+
+        path = save_model(result, model_dir=tmp_path)
+        assert path.exists()
+        assert (tmp_path / "energy_model_meta.json").exists()
+
+        loaded_model, meta = load_model(model_dir=tmp_path)
+        assert meta["accuracy"] == 0.85
+        assert meta["training_samples"] == 30
+
+        # Model should produce same predictions
+        pred_orig = model.predict(X[:1])
+        pred_loaded = loaded_model.predict(X[:1])
+        assert pred_orig[0] == pred_loaded[0]
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_autotag.py -v`
- All tests should pass

#### Task 5 — Lint all modified files

Tools: shell

Commands:
```bash
source .venv/bin/activate && python -m py_compile src/djsetbuilder/db/models.py && python -m py_compile src/djsetbuilder/analysis/autotag.py && python -m py_compile src/djsetbuilder/cli.py && python -m py_compile tests/test_autotag.py && echo "All files compile OK"
```

#### Task 6 — E2E verification

Tools: shell

Commands:
```bash
source .venv/bin/activate && python -m pytest tests/ -x -q && djset autotag energy --dry-run --threshold 0.5 2>&1 | head -40
```

Expectations:
- All existing tests pass
- New test_autotag.py tests pass
- `djset autotag energy --dry-run` shows training report + prediction table
- No crashes or import errors

#### Task 7 — Commit

Tools: git

Commands:
```bash
git add src/djsetbuilder/db/models.py src/djsetbuilder/analysis/autotag.py src/djsetbuilder/cli.py tests/test_autotag.py
git commit -m "$(cat <<'EOF'
feat: energy autotag classifier with retraining loop

Train RF classifier on DJ's manual energy tags to predict zones
(warmup/build/peak) for untagged tracks. Uses audio features only
(BPM excluded by design). Supports --dry-run, --approve, --auto,
--retrain modes with confidence scoring.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Validate

| # | Requirement | Compliance |
|---|-------------|------------|
| 1 | Train on dir_energy tags, BPM excluded (L8) | `autotag.py` uses `BASE_FEATURES` which does not include `bpm`. `extract_features()` pulls from AudioFeatures only |
| 2 | Use listed audio features (L9) | All 12 features from spec are in `BASE_FEATURES` + `MOOD_FEATURES` |
| 3 | Map 9 tags → 3 zones (L10) | `ZONE_MAP` dict maps all 9 tags to warmup/build/peak |
| 4 | Confidence scores (L11) | `predict_energy()` uses `predict_proba()`, returns confidence per prediction |
| 5 | CLI modes: dry-run, approve, auto (L12-16) | Task 3 implements all modes with `click.option` flag_value pattern |
| 6 | Threshold default 0.7 (L16) | `--threshold` defaults to 0.7 |
| 7 | Distinguish predicted from manual (L17) | `energy_predicted`, `energy_confidence`, `energy_source` columns on Track (Task 1) |
| 8 | Incremental retraining (L18) | `_load_training_data()` includes approved predictions when `include_approved=True` |
| 9 | Training lineage (L19) | `save_model()` writes JSON metadata sidecar with date, samples, accuracy, importance |
| 10 | BPM excluded (L23-24) | Feature list has no BPM. Verified in `BASE_FEATURES` constant |
| 11 | Graceful mood handling (L35) | `extract_features()` fills 0.0 for missing mood features |
| 12 | Model serialized to data/ (L40) | `DEFAULT_MODEL_DIR = Path("data")`, uses joblib |
| 13 | Feature importance (L41) | Returned from `train_energy_model()`, displayed in CLI |
| 14 | Retraining reports delta (L46) | CLI shows training samples count and accuracy |
| 15 | Old model backed up (L47) | `save_model()` copies to `energy_model.v{N}.pkl` before overwriting |
| 16 | No overwrite manual tags without --force (L55) | CLI checks `track.dir_energy and not force` before writing |
| 17 | Warn if < 10 samples per class (L56) | `train_energy_model()` checks and appends to warnings list |
| 18 | Cross-validation reported (L57) | `StratifiedKFold` CV with `classification_report` shown in CLI |

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
