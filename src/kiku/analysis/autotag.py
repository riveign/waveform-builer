"""Energy autotag classifier — learns from the DJ's own tags."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from kiku.db.models import AudioFeatures, Track

# Zone mapping: granular tag → zone
ZONE_MAP: dict[str, str] = {
    "low": "warmup", "warmup": "warmup",
    "mid": "build", "dance": "build",
    "up": "drive", "high": "drive",
    "fast": "peak", "peak": "peak",
    "closing": "close",
}

# All valid granular energy tags
ENERGY_TAGS = list(ZONE_MAP.keys())

# Feature names (order matters — must match extraction)
BASE_FEATURES = [
    "energy", "loudness_lufs", "spectral_centroid", "spectral_complexity",
    "danceability", "energy_intro", "energy_body", "energy_outro",
]
MOOD_FEATURES = ["mood_happy", "mood_sad", "mood_aggressive", "mood_relaxed"]
DERIVED_FEATURES = ["build_shape", "drop_shape", "intro_body_ratio", "outro_body_ratio"]
MOOD_DERIVED = ["aggression_ratio"]

DEFAULT_MODEL_DIR = Path("data")
MODEL_FILENAME = "energy_model.pkl"
META_FILENAME = "energy_model_meta.json"


def extract_features(af: AudioFeatures) -> np.ndarray | None:
    """Extract feature vector from an AudioFeatures row.

    Returns None if required base features are missing.
    """
    # Base features (required)
    base = []
    for feat in BASE_FEATURES:
        val = getattr(af, feat, None)
        if val is None:
            return None
        base.append(float(val))

    # Derived from energy curve
    intro, body, outro = af.energy_intro, af.energy_body, af.energy_outro
    if intro is not None and body is not None and outro is not None:
        base.append(body - intro)                    # build_shape
        base.append(body - outro)                    # drop_shape
        base.append(intro / (body + 0.001))          # intro_body_ratio
        base.append(outro / (body + 0.001))          # outro_body_ratio
    else:
        base.extend([0.0, 0.0, 0.0, 0.0])

    # Mood features (optional — use if available, fill 0 if not)
    for feat in MOOD_FEATURES:
        val = getattr(af, feat, None)
        base.append(float(val) if val is not None else 0.0)

    # Mood derived
    aggressive = getattr(af, "mood_aggressive", None)
    relaxed = getattr(af, "mood_relaxed", None)
    if aggressive is not None and relaxed is not None:
        base.append(aggressive / (relaxed + 0.01))
    else:
        base.append(0.0)

    return np.array(base, dtype=np.float32)


def feature_names() -> list[str]:
    """Return ordered feature names matching extract_features output."""
    return BASE_FEATURES + DERIVED_FEATURES + MOOD_FEATURES + MOOD_DERIVED


def _load_training_data(
    session: Session, include_approved: bool = True,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load feature matrix X, label array y, and tag list from DB.

    Training data = tracks with manual dir_energy OR approved predictions.
    """
    query = (
        session.query(Track, AudioFeatures)
        .join(AudioFeatures)
        .filter(AudioFeatures.energy.isnot(None))
    )

    X_list, y_list = [], []
    for track, af in query.all():
        # Determine label source
        tag = None
        if track.dir_energy:
            tag = track.dir_energy.lower()
        elif include_approved and track.energy_source == "approved" and track.energy_predicted:
            tag = track.energy_predicted.lower()

        if tag is None or tag not in ZONE_MAP:
            continue

        features = extract_features(af)
        if features is None:
            continue

        X_list.append(features)
        y_list.append(tag)

    return np.array(X_list), np.array(y_list), y_list


def train_energy_model(session: Session, include_approved: bool = True) -> dict:
    """Train a RandomForest classifier on the DJ's energy tags.

    Returns dict with keys: model, metrics, feature_importance, class_counts, warnings.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report
    from sklearn.model_selection import StratifiedKFold
    from sklearn.utils import resample

    X, y, _ = _load_training_data(session, include_approved=include_approved)

    if len(X) == 0:
        raise ValueError("No training data found. Tag some tracks with energy levels first.")

    # Map to zones for training
    y_zones = np.array([ZONE_MAP[t] for t in y])
    class_counts = dict(Counter(y_zones))

    warnings = []
    for zone, count in class_counts.items():
        if count < 10:
            warnings.append(f"Only {count} examples for '{zone}' — predictions will be unreliable")

    # Cross-validation with oversampling inside each fold
    skf = StratifiedKFold(n_splits=min(5, min(class_counts.values())), shuffle=True, random_state=42)
    all_true, all_pred = [], []

    for train_idx, test_idx in skf.split(X, y_zones):
        X_train, y_train = X[train_idx], y_zones[train_idx]
        X_test, y_test = X[test_idx], y_zones[test_idx]

        # Oversample minority classes in train fold
        target_n = max(Counter(y_train).values())
        X_bal, y_bal = [], []
        for label in np.unique(y_train):
            mask = y_train == label
            Xc, yc = X_train[mask], y_train[mask]
            if len(yc) < target_n:
                Xr, yr = resample(Xc, yc, n_samples=target_n, random_state=42)
                X_bal.append(Xr)
                y_bal.append(yr)
            else:
                X_bal.append(Xc)
                y_bal.append(yc)

        X_bal = np.vstack(X_bal)
        y_bal = np.concatenate(y_bal)

        fold_clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
        fold_clf.fit(X_bal, y_bal)
        all_true.extend(y_test)
        all_pred.extend(fold_clf.predict(X_test))

    metrics = classification_report(all_true, all_pred, output_dict=True, zero_division=0)

    # Train final model on ALL data (oversampled)
    target_n = max(Counter(y_zones).values())
    X_final, y_final = [], []
    for label in np.unique(y_zones):
        mask = y_zones == label
        Xc, yc = X[mask], y_zones[mask]
        if len(yc) < target_n:
            Xr, yr = resample(Xc, yc, n_samples=target_n, random_state=42)
            X_final.append(Xr)
            y_final.append(yr)
        else:
            X_final.append(Xc)
            y_final.append(yc)

    X_final = np.vstack(X_final)
    y_final = np.concatenate(y_final)

    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_final, y_final)

    # Feature importance
    names = feature_names()
    importance = sorted(zip(names, model.feature_importances_), key=lambda x: -x[1])

    return {
        "model": model,
        "metrics": metrics,
        "feature_importance": importance,
        "class_counts": class_counts,
        "training_samples": len(X),
        "warnings": warnings,
    }


def predict_energy(
    session: Session, model, threshold: float = 0.7,
) -> list[dict]:
    """Predict energy zones for untagged tracks.

    Returns list of dicts: {track_id, title, artist, predicted, confidence, zone}.
    Only includes predictions above threshold.
    """
    tracks = (
        session.query(Track, AudioFeatures)
        .join(AudioFeatures)
        .filter(AudioFeatures.energy.isnot(None))
        .filter((Track.dir_energy.is_(None)) | (Track.dir_energy == ""))
        .all()
    )

    results = []
    for track, af in tracks:
        features = extract_features(af)
        if features is None:
            continue

        proba = model.predict_proba(features.reshape(1, -1))[0]
        best_idx = int(np.argmax(proba))
        confidence = float(proba[best_idx])
        predicted = model.classes_[best_idx]

        if confidence >= threshold:
            results.append({
                "track_id": track.id,
                "title": track.title or "?",
                "artist": track.artist or "?",
                "predicted": predicted,
                "confidence": confidence,
            })

    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results


def save_model(result: dict, model_dir: Path = DEFAULT_MODEL_DIR) -> Path:
    """Save trained model and metadata. Backs up previous version."""
    import joblib

    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / MODEL_FILENAME
    meta_path = model_dir / META_FILENAME

    # Backup existing model
    if model_path.exists():
        # Find next version number
        version = 1
        while (model_dir / f"energy_model.v{version}.pkl").exists():
            version += 1
        shutil.copy2(model_path, model_dir / f"energy_model.v{version}.pkl")
        if meta_path.exists():
            shutil.copy2(meta_path, model_dir / f"energy_model_meta.v{version}.json")

    joblib.dump(result["model"], model_path)

    meta = {
        "trained_at": datetime.now().isoformat(),
        "training_samples": result["training_samples"],
        "class_counts": result["class_counts"],
        "accuracy": result["metrics"].get("accuracy", 0),
        "per_class": {
            k: {"precision": v["precision"], "recall": v["recall"], "f1": v["f1-score"]}
            for k, v in result["metrics"].items()
            if isinstance(v, dict) and "precision" in v
        },
        "feature_importance": result["feature_importance"],
        "warnings": result["warnings"],
    }
    meta_path.write_text(json.dumps(meta, indent=2, default=str))

    return model_path


def load_model(model_dir: Path = DEFAULT_MODEL_DIR):
    """Load a previously trained model. Returns (model, metadata) or raises FileNotFoundError."""
    import joblib

    model_path = model_dir / MODEL_FILENAME
    meta_path = model_dir / META_FILENAME

    if not model_path.exists():
        raise FileNotFoundError(f"No trained model found at {model_path}. Run: kiku autotag energy --retrain")

    model = joblib.load(model_path)
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())

    return model, meta
