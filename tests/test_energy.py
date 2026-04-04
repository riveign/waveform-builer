"""Tests for the unified energy resolution module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kiku.energy import (
    TrackEnergy,
    composite_energy_score,
    format_energy_label,
    get_track_energy,
    numeric_to_zone,
    reset_calibration_cache,
    _FALLBACK_ZONE_BOUNDARIES,
)


@pytest.fixture(autouse=True)
def _reset_calibration():
    """Ensure tests start with clean calibration state."""
    reset_calibration_cache()
    yield
    reset_calibration_cache()


def _make_track(
    dir_energy: str | None = None,
    energy_predicted: str | None = None,
    energy_confidence: float | None = None,
    energy_source: str | None = None,
    audio_energy: float | None = None,
    audio_features_obj: MagicMock | None = None,
) -> MagicMock:
    """Create a mock Track with optional energy fields."""
    track = MagicMock()
    track.dir_energy = dir_energy
    track.energy_predicted = energy_predicted
    track.energy_confidence = energy_confidence
    track.energy_source = energy_source

    if audio_features_obj is not None:
        track.audio_features = audio_features_obj
    elif audio_energy is not None:
        af = MagicMock()
        af.energy = audio_energy
        track.audio_features = af
    else:
        track.audio_features = None

    return track


def _make_audio_features(**kwargs) -> MagicMock:
    """Create a mock AudioFeatures with all base fields."""
    af = MagicMock()
    defaults = {
        "energy": 0.85,
        "loudness_lufs": -8.0,
        "spectral_centroid": 3000.0,
        "spectral_complexity": 50.0,
        "danceability": 0.7,
        "energy_intro": 0.6,
        "energy_body": 0.85,
        "energy_outro": 0.5,
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(af, k, v)
    return af


# ── numeric_to_zone (fallback boundaries) ────────────────────────────


class TestNumericToZone:
    """Tests use fallback boundaries (no calibration file)."""

    def test_warmup_low(self):
        assert numeric_to_zone(0.0) == "warmup"

    def test_warmup_boundary(self):
        assert numeric_to_zone(0.39) == "warmup"

    def test_build_at_boundary(self):
        assert numeric_to_zone(0.40) == "build"

    def test_build_mid(self):
        assert numeric_to_zone(0.55) == "build"

    def test_drive_at_boundary(self):
        assert numeric_to_zone(0.63) == "drive"

    def test_drive_mid(self):
        assert numeric_to_zone(0.72) == "drive"

    def test_peak_at_boundary(self):
        assert numeric_to_zone(0.80) == "peak"

    def test_peak_max(self):
        assert numeric_to_zone(1.0) == "peak"


class TestNumericToZoneCalibrated:
    """Tests with calibrated boundaries."""

    def test_uses_calibrated_boundaries(self):
        cal = {
            "zone_boundaries": [(0.30, "warmup"), (0.50, "build"), (0.70, "drive"), (1.01, "peak")],
            "composite_weights": {},
            "feature_ranges": {},
        }
        with patch("kiku.energy._load_calibration", return_value=cal):
            assert numeric_to_zone(0.25) == "warmup"
            assert numeric_to_zone(0.35) == "build"
            assert numeric_to_zone(0.60) == "drive"
            assert numeric_to_zone(0.90) == "peak"

    def test_missing_calibration_uses_fallback(self):
        with patch("kiku.energy._load_calibration", return_value=None):
            # Should use _FALLBACK_ZONE_BOUNDARIES
            assert numeric_to_zone(0.55) == "build"
            assert numeric_to_zone(0.80) == "peak"


# ── composite_energy_score ────────────────────────────────────────────


class TestCompositeEnergyScore:
    def test_returns_none_without_calibration(self):
        af = _make_audio_features()
        with patch("kiku.energy._load_calibration", return_value=None):
            assert composite_energy_score(af) is None

    def test_returns_float_with_calibration(self):
        from kiku.analysis.autotag import feature_names
        names = feature_names()
        # Ranges must encompass the mock values (e.g. spectral_centroid=3000)
        range_map = {
            "energy": (0.0, 1.0), "loudness_lufs": (-30.0, 0.0),
            "spectral_centroid": (0.0, 6000.0), "spectral_complexity": (0.0, 100.0),
            "danceability": (0.0, 1.0), "energy_intro": (0.0, 1.0),
            "energy_body": (0.0, 1.0), "energy_outro": (0.0, 1.0),
            "build_shape": (-1.0, 1.0), "drop_shape": (-1.0, 1.0),
            "intro_body_ratio": (0.0, 2.0), "outro_body_ratio": (0.0, 2.0),
        }
        cal = {
            "composite_weights": {n: 1.0 / len(names) for n in names},
            "feature_ranges": {n: {"min": range_map.get(n, (0.0, 1.0))[0], "max": range_map.get(n, (0.0, 1.0))[1]} for n in names},
        }
        af = _make_audio_features()
        with patch("kiku.energy._load_calibration", return_value=cal):
            score = composite_energy_score(af)
            assert score is not None
            assert 0.0 <= score <= 1.5  # Weighted sum of normalized features

    def test_returns_none_when_features_missing(self):
        cal = {
            "composite_weights": {"energy": 1.0},
            "feature_ranges": {"energy": {"min": 0.0, "max": 1.0}},
        }
        af = MagicMock()
        af.energy = None  # Missing required feature
        af.loudness_lufs = None
        af.spectral_centroid = None
        af.spectral_complexity = None
        af.danceability = None
        af.energy_intro = None
        af.energy_body = None
        af.energy_outro = None
        with patch("kiku.energy._load_calibration", return_value=cal):
            assert composite_energy_score(af) is None

    def test_handles_zero_range_features(self):
        """Features with min==max should normalize to 0.5."""
        from kiku.analysis.autotag import feature_names
        names = feature_names()
        cal = {
            "composite_weights": {n: 1.0 / len(names) for n in names},
            "feature_ranges": {n: {"min": 0.5, "max": 0.5} for n in names},  # zero range
        }
        af = _make_audio_features()
        with patch("kiku.energy._load_calibration", return_value=cal):
            score = composite_energy_score(af)
            assert score is not None
            assert abs(score - 0.5) < 0.01  # All features normalize to 0.5


# ── format_energy_label ──────────────────────────────────────────────


class TestFormatEnergyLabel:
    def test_approved_no_qualifier(self):
        assert format_energy_label("drive", "approved") == "drive"

    def test_dir_energy_folder(self):
        assert format_energy_label("build", "dir_energy") == "build (folder)"

    def test_predicted_estimated(self):
        assert format_energy_label("peak", "predicted") == "peak (estimated)"

    def test_audio_derived(self):
        assert format_energy_label("warmup", "audio") == "warmup (from audio)"

    def test_none_zone(self):
        assert format_energy_label(None, "none") == "unknown"


# ── get_track_energy ─────────────────────────────────────────────────


class TestGetTrackEnergy:
    def test_approved_with_audio(self):
        """Approved zone wins, but numeric comes from audio features."""
        track = _make_track(
            energy_predicted="drive",
            energy_source="approved",
            energy_confidence=0.95,
            audio_energy=0.75,
        )
        te = get_track_energy(track)
        assert te.zone == "drive"
        assert te.source == "approved"
        assert te.numeric == 0.75
        assert te.confidence == 0.95
        assert te.label == "drive"

    def test_dir_energy_with_audio(self):
        """Dir energy zone, Essentia numeric."""
        track = _make_track(dir_energy="peak", audio_energy=0.88)
        te = get_track_energy(track)
        assert te.zone == "peak"
        assert te.source == "dir_energy"
        assert te.numeric == 0.88
        assert te.confidence == 1.0
        assert te.label == "peak (folder)"

    def test_predicted_only(self):
        """ML prediction with no audio features."""
        track = _make_track(
            energy_predicted="build",
            energy_source="auto",
            energy_confidence=0.65,
        )
        te = get_track_energy(track)
        assert te.zone == "build"
        assert te.source == "predicted"
        assert te.numeric == 0.55  # zone_to_numeric("build")
        assert te.confidence == 0.65
        assert te.label == "build (estimated)"

    def test_audio_only_no_calibration(self):
        """Audio-only track without calibration — uses raw energy with lower confidence."""
        track = _make_track(audio_energy=0.23)
        # No calibration → composite returns None → falls back to raw numeric
        with patch("kiku.energy.composite_energy_score", return_value=None):
            te = get_track_energy(track)
            assert te.zone == "warmup"
            assert te.source == "audio"
            assert te.numeric == 0.23
            assert te.confidence == 0.5  # Lower confidence for raw-only

    def test_audio_only_with_composite(self):
        """Audio-only track with composite score derives zone from composite."""
        track = _make_track(audio_energy=0.85)
        # Composite returns a value in the build range (fallback boundaries)
        with patch("kiku.energy.composite_energy_score", return_value=0.50):
            te = get_track_energy(track)
            assert te.zone == "build"
            assert te.source == "audio"
            assert te.numeric == 0.85  # Raw energy preserved for visualization
            assert te.confidence == 0.6  # Composite confidence

    def test_no_energy_at_all(self):
        """Track with zero energy data."""
        track = _make_track()
        te = get_track_energy(track)
        assert te.zone is None
        assert te.source == "none"
        assert te.numeric == 0.5
        assert te.confidence == 0.0
        assert te.label == "unknown"

    def test_approved_overrides_dir_energy(self):
        """Approved wins over dir_energy when both present."""
        track = _make_track(
            dir_energy="peak",
            energy_predicted="drive",
            energy_source="approved",
            energy_confidence=1.0,
            audio_energy=0.72,
        )
        te = get_track_energy(track)
        assert te.zone == "drive"
        assert te.source == "approved"

    def test_dir_energy_overrides_predicted(self):
        """Dir energy wins over predicted when both present."""
        track = _make_track(
            dir_energy="warmup",
            energy_predicted="peak",
            energy_source="auto",
            energy_confidence=0.8,
            audio_energy=0.25,
        )
        te = get_track_energy(track)
        assert te.zone == "warmup"
        assert te.source == "dir_energy"

    def test_audio_high_energy_maps_to_peak(self):
        """Audio-only track with high energy maps to peak zone (no calibration)."""
        track = _make_track(audio_energy=0.92)
        with patch("kiku.energy.composite_energy_score", return_value=None):
            te = get_track_energy(track)
            assert te.zone == "peak"
            assert te.numeric == 0.92

    def test_audio_mid_energy_maps_to_build(self):
        """Audio-only track with mid energy maps to build zone (no calibration)."""
        track = _make_track(audio_energy=0.55)
        with patch("kiku.energy.composite_energy_score", return_value=None):
            te = get_track_energy(track)
            assert te.zone == "build"

    def test_frozen_dataclass(self):
        """TrackEnergy should be immutable."""
        te = TrackEnergy(zone="build", numeric=0.55, source="dir_energy", confidence=1.0, label="build (folder)")
        with pytest.raises(AttributeError):
            te.zone = "peak"  # type: ignore[misc]


# ── reset_calibration_cache ──────────────────────────────────────────


class TestCalibrationCache:
    def test_reset_clears_cache(self):
        """After reset, calibration is reloaded on next access."""
        from kiku.energy import _calibration_loaded
        reset_calibration_cache()
        from kiku import energy
        assert energy._calibration_loaded is False
        assert energy._calibration is None
