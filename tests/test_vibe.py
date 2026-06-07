"""Tests for the transparent vibe model and its use in scoring + planning."""

from unittest.mock import MagicMock

import pytest

import kiku.vibe as vibe
from kiku.setbuilder.planner import _end_affinity, _end_pull, _make_vibe_arc
from kiku.setbuilder.scoring import vibe_continuity, vibe_target_fit, vibe_term
from kiku.vibe import (
    VIBE_PRESETS,
    derive_vibe,
    resolve_preset,
    resolve_vibe,
    vibe_distance,
    vibe_label,
)


@pytest.fixture(autouse=True)
def force_fallback_ranges(monkeypatch):
    """Force fallback normalization ranges so tests are deterministic
    regardless of any data/vibe_calibration.json on disk."""
    monkeypatch.setattr(vibe, "_calibration", None)
    monkeypatch.setattr(vibe, "_calibration_loaded", True)
    yield


def _af(**kw):
    af = MagicMock()
    for field in (
        "spectral_centroid", "spectral_complexity", "danceability",
        "band_low_overview", "band_midlow_overview",
        "band_midhigh_overview", "band_high_overview",
        "vibe_brightness", "vibe_density",
    ):
        setattr(af, field, kw.get(field))
    return af


def _track(key=None, af=None):
    t = MagicMock()
    t.key = key
    t.audio_features = af
    return t


def _stored(brightness, density):
    """A track whose vibe is already stored on its audio_features."""
    return _track(af=_af(vibe_brightness=brightness, vibe_density=density))


# ── Derivation ──────────────────────────────────────────────────────────
def test_major_key_reads_brighter_than_minor():
    """Same timbre, opposite mode → major key reads brighter."""
    major = _track(key="8B", af=_af(spectral_centroid=2000.0))
    minor = _track(key="8A", af=_af(spectral_centroid=2000.0))
    bmaj, _ = derive_vibe(major)
    bmin, _ = derive_vibe(minor)
    assert bmaj > bmin


def test_brighter_timbre_reads_brighter():
    """Same key, higher spectral centroid → brighter vibe."""
    dull = _track(key="8A", af=_af(spectral_centroid=900.0))
    bright = _track(key="8A", af=_af(spectral_centroid=3000.0))
    assert derive_vibe(bright)[0] > derive_vibe(dull)[0]


def test_no_bands_falls_back_to_mode_and_centroid():
    """With centroid mid-range (0.5) and major key, brightness uses the
    0.55/0.45 fallback split: 0.55*1.0 + 0.45*0.5 = 0.775."""
    t = _track(key="8B", af=_af(spectral_centroid=2000.0))
    brightness, _ = derive_vibe(t)
    assert brightness == pytest.approx(0.775, abs=0.01)


def test_density_from_complexity_and_danceability():
    t = _track(key="8A", af=_af(spectral_complexity=10.0, danceability=0.5))
    _, density = derive_vibe(t)
    # complexity_norm = (10-2)/16 = 0.5 ; 0.55*0.5 + 0.45*0.5 = 0.5
    assert density == pytest.approx(0.5, abs=0.01)


def test_derive_returns_none_without_signal():
    assert derive_vibe(_track(key=None, af=None)) is None


def test_high_band_ratio_raises_brightness():
    """More energy in the upper bands → brighter."""
    dark_bands = _af(spectral_centroid=2000.0, band_low_overview=b"x",
                     band_midlow_overview=b"x", band_midhigh_overview=b"x",
                     band_high_overview=b"x")
    # Patch _band_mean to simulate bass-heavy vs treble-heavy spectra.
    bassy = _track(key="8A", af=dark_bands)
    import numpy as np
    dark_bands.band_low_overview = np.array([1.0, 1.0], dtype=np.float32).tobytes()
    dark_bands.band_midlow_overview = np.array([0.8, 0.8], dtype=np.float32).tobytes()
    dark_bands.band_midhigh_overview = np.array([0.1, 0.1], dtype=np.float32).tobytes()
    dark_bands.band_high_overview = np.array([0.05, 0.05], dtype=np.float32).tobytes()
    b_bassy, _ = derive_vibe(bassy)

    bright_bands = _af(spectral_centroid=2000.0)
    bright_bands.band_low_overview = np.array([0.1, 0.1], dtype=np.float32).tobytes()
    bright_bands.band_midlow_overview = np.array([0.2, 0.2], dtype=np.float32).tobytes()
    bright_bands.band_midhigh_overview = np.array([0.9, 0.9], dtype=np.float32).tobytes()
    bright_bands.band_high_overview = np.array([1.0, 1.0], dtype=np.float32).tobytes()
    trebly = _track(key="8A", af=bright_bands)
    b_trebly, _ = derive_vibe(trebly)

    assert b_trebly > b_bassy


# ── Resolution ──────────────────────────────────────────────────────────
def test_resolve_prefers_stored():
    v = resolve_vibe(_stored(0.2, 0.3))
    assert v.source == "stored"
    assert v.brightness == 0.2 and v.density == 0.3


def test_resolve_derives_when_unstored():
    v = resolve_vibe(_track(key="8B", af=_af(spectral_centroid=2000.0)))
    assert v.source == "derived"


def test_resolve_none_when_no_signal():
    v = resolve_vibe(_track(key=None, af=None))
    assert v.source == "none"
    assert (v.brightness, v.density) == (0.5, 0.5)


# ── Labels, distance, presets ─────────────────────────────────────────────
def test_vibe_label_dark_vs_bright():
    assert "dark" in vibe_label(0.1, 0.2)
    assert "euphoric" in vibe_label(0.95, 0.5)


def test_vibe_distance_bounds():
    assert vibe_distance((0.0, 0.0), (0.0, 0.0)) == 0.0
    assert vibe_distance((0.0, 0.0), (1.0, 1.0)) == pytest.approx(1.0)


def test_resolve_preset_known_and_unknown():
    assert resolve_preset("dark & deep") == VIBE_PRESETS["dark & deep"]
    assert resolve_preset("DARK & DEEP") == VIBE_PRESETS["dark & deep"]
    assert resolve_preset("nonexistent") is None
    assert resolve_preset(None) is None


# ── Scoring integration ───────────────────────────────────────────────────
def test_target_fit_rewards_matching_vibe():
    dark = _stored(0.15, 0.35)
    bright = _stored(0.9, 0.6)
    target = (0.15, 0.35)
    assert vibe_target_fit(dark, target) > vibe_target_fit(bright, target)


def test_continuity_penalizes_jumps():
    a = _stored(0.2, 0.3)
    near = _stored(0.25, 0.35)
    far = _stored(0.9, 0.9)
    assert vibe_continuity(a, near) > vibe_continuity(a, far)


def test_vibe_term_off_when_strength_zero():
    contribution, breakdown = vibe_term(_stored(0.2, 0.3), _stored(0.2, 0.3), (0.15, 0.35), 0.0)
    assert contribution == 0.0 and breakdown is None


def test_vibe_term_steers_toward_target():
    prev = _stored(0.5, 0.5)
    dark = _stored(0.15, 0.35)
    bright = _stored(0.9, 0.6)
    target = (0.15, 0.35)
    c_dark, _ = vibe_term(prev, dark, target, 1.0)
    c_bright, _ = vibe_term(prev, bright, target, 1.0)
    assert c_dark > c_bright


# ── Planner: vibe arc + soft anchors ──────────────────────────────────────
def test_arc_preset_only_is_flat():
    arc = _make_vibe_arc(start_vibe=(0.7, 0.4), end_vibe=None, preset_vibe=(0.15, 0.35))
    assert arc(0.0) == (0.15, 0.35)
    assert arc(0.5) == (0.15, 0.35)
    assert arc(1.0) == (0.15, 0.35)


def test_arc_start_end_interpolates():
    arc = _make_vibe_arc(start_vibe=(0.2, 0.2), end_vibe=(0.8, 0.8), preset_vibe=None)
    assert arc(0.0) == (0.2, 0.2)
    assert arc(1.0) == (0.8, 0.8)
    mid = arc(0.5)
    assert mid[0] == pytest.approx(0.5) and mid[1] == pytest.approx(0.5)


def test_arc_preset_with_end_eases_to_end():
    arc = _make_vibe_arc(start_vibe=(0.7, 0.4), end_vibe=(0.9, 0.6), preset_vibe=(0.15, 0.35))
    # Body holds the preset; the very end eases toward the end anchor.
    assert arc(0.5) == (0.15, 0.35)
    assert arc(1.0) == pytest.approx((0.9, 0.6))


def test_arc_off_when_nothing_given():
    assert _make_vibe_arc(None, None, None) is None


def test_end_pull_only_in_final_stretch():
    assert _end_pull(0.5) == 0.0
    assert _end_pull(0.8) == 0.0
    assert _end_pull(1.0) > _end_pull(0.9) > 0.0


def test_end_affinity_higher_for_compatible_landing():
    end = _track(key="8A", af=_af(vibe_brightness=0.2, vibe_density=0.3))
    end.bpm = 128.0
    good = _track(key="8A", af=_af(vibe_brightness=0.22, vibe_density=0.32))
    good.bpm = 128.0
    bad = _track(key="3B", af=_af(vibe_brightness=0.9, vibe_density=0.9))
    bad.bpm = 100.0
    assert _end_affinity(good, end) > _end_affinity(bad, end)
