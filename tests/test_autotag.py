"""Tests for the energy autotag classifier."""

import json
from unittest.mock import MagicMock

import numpy as np
import pytest

from kiku.analysis.autotag import (
    ZONE_MAP,
    extract_features,
    feature_names,
)


def _make_af(**kwargs):
    """Create a mock AudioFeatures with given values."""
    af = MagicMock()
    defaults = {
        "energy": 0.9, "loudness_lufs": -8.0,
        "spectral_centroid": 1200.0, "spectral_complexity": 0.1,
        "danceability": 1.4, "energy_intro": 0.8,
        "energy_body": 0.9, "energy_outro": 0.85,
        "mood_happy": None, "mood_sad": None,
        "mood_aggressive": None, "mood_relaxed": None,
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(af, k, v)
    return af


class TestFeatureExtraction:
    def test_base_features_extracted(self):
        af = _make_af()
        features = extract_features(af)
        assert features is not None
        assert len(features) == len(feature_names())

    def test_missing_base_feature_returns_none(self):
        af = _make_af(energy=None)
        assert extract_features(af) is None

    def test_mood_features_filled_zero_when_missing(self):
        af = _make_af()
        features = extract_features(af)
        # Mood features are at indices 12-15, should be 0
        mood_start = len(feature_names()) - 5  # 4 mood + 1 derived
        assert all(features[mood_start:] == 0.0)

    def test_mood_features_used_when_present(self):
        af = _make_af(mood_happy=0.7, mood_sad=0.2, mood_aggressive=0.8, mood_relaxed=0.3)
        features = extract_features(af)
        names = feature_names()
        idx = names.index("mood_happy")
        assert features[idx] == pytest.approx(0.7)
        idx_agg = names.index("aggression_ratio")
        assert features[idx_agg] == pytest.approx(0.8 / (0.3 + 0.01), rel=1e-2)

    def test_derived_features_computed(self):
        af = _make_af(energy_intro=0.5, energy_body=0.9, energy_outro=0.7)
        features = extract_features(af)
        names = feature_names()
        assert features[names.index("build_shape")] == pytest.approx(0.4)
        assert features[names.index("drop_shape")] == pytest.approx(0.2)


class TestZoneMapping:
    def test_all_tags_have_zone(self):
        for tag in ["low", "warmup", "closing", "mid", "dance", "up", "high", "fast", "peak"]:
            assert tag in ZONE_MAP

    def test_zones_are_valid(self):
        assert set(ZONE_MAP.values()) == {"warmup", "build", "drive", "peak", "close"}


class TestModelPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        from kiku.analysis.autotag import load_model, save_model

        # Create a minimal mock model
        from sklearn.ensemble import RandomForestClassifier
        X = np.random.rand(30, 17)
        y = np.array(["warmup"] * 10 + ["build"] * 10 + ["peak"] * 10)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)

        result = {
            "model": model,
            "metrics": {"accuracy": 0.85},
            "feature_importance": [("loudness", 0.2), ("centroid", 0.15)],
            "class_counts": {"warmup": 10, "build": 10, "peak": 10},
            "training_samples": 30,
            "warnings": [],
        }

        path = save_model(result, model_dir=tmp_path)
        assert path.exists()
        assert (tmp_path / "energy_model_meta.json").exists()

        loaded_model, meta = load_model(model_dir=tmp_path)
        assert meta["accuracy"] == 0.85
        assert meta["training_samples"] == 30

        # Model should produce same predictions
        pred_orig = model.predict(X[:1])
        pred_loaded = loaded_model.predict(X[:1])
        assert pred_orig[0] == pred_loaded[0]
