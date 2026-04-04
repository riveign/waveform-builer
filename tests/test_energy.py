"""Tests for the unified energy resolution module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kiku.energy import (
    TrackEnergy,
    format_energy_label,
    get_track_energy,
    numeric_to_zone,
)


def _make_track(
    dir_energy: str | None = None,
    energy_predicted: str | None = None,
    energy_confidence: float | None = None,
    energy_source: str | None = None,
    audio_energy: float | None = None,
) -> MagicMock:
    """Create a mock Track with optional energy fields."""
    track = MagicMock()
    track.dir_energy = dir_energy
    track.energy_predicted = energy_predicted
    track.energy_confidence = energy_confidence
    track.energy_source = energy_source

    if audio_energy is not None:
        af = MagicMock()
        af.energy = audio_energy
        track.audio_features = af
    else:
        track.audio_features = None

    return track


# ── numeric_to_zone ──────────────────────────────────────────────────


class TestNumericToZone:
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

    def test_audio_only_no_zone(self):
        """Only audio features — zone derived from numeric."""
        track = _make_track(audio_energy=0.23)
        te = get_track_energy(track)
        assert te.zone == "warmup"
        assert te.source == "audio"
        assert te.numeric == 0.23
        assert te.confidence == 0.7
        assert te.label == "warmup (from audio)"

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
        """Audio-only track with high energy maps to peak zone."""
        track = _make_track(audio_energy=0.92)
        te = get_track_energy(track)
        assert te.zone == "peak"
        assert te.numeric == 0.92

    def test_audio_mid_energy_maps_to_build(self):
        """Audio-only track with mid energy maps to build zone."""
        track = _make_track(audio_energy=0.55)
        te = get_track_energy(track)
        assert te.zone == "build"

    def test_frozen_dataclass(self):
        """TrackEnergy should be immutable."""
        te = TrackEnergy(zone="build", numeric=0.55, source="dir_energy", confidence=1.0, label="build (folder)")
        with pytest.raises(AttributeError):
            te.zone = "peak"  # type: ignore[misc]
