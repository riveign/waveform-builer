"""Transparent vibe derivation for tracks.

A track's *vibe* is the thing that makes two harmonically-and-energetically
compatible tracks still feel wrong together: one is dark and hypnotic, the next
is bright and euphoric. We capture it as two explainable axes derived entirely
from features we already extract — no new dependencies, no black-box ML, and
every coefficient is documented so a DJ can read exactly why a track reads as
"dark" or "busy".

Axes (both 0-1):
    brightness  — dark ↔ bright. The "dark/deep vs happy" axis.
    density     — spacious/hypnotic ↔ busy/driving.

brightness = 0.45·mode + 0.40·centroid_norm + 0.15·high_band_ratio
    mode             major key = 1.0, minor key = 0.0 (from the Camelot letter)
    centroid_norm    spectral_centroid normalized to library percentiles
    high_band_ratio  (midhigh + high) band energy / total band energy
    (when band data is absent the weights collapse to 0.55·mode + 0.45·centroid)

density = 0.55·complexity_norm + 0.45·danceability
    complexity_norm  spectral_complexity normalized to library percentiles
    danceability     Essentia danceability (already 0-1-ish)

Normalization ranges come from library-wide robust percentiles (5th/95th) stored
in data/vibe_calibration.json, mirroring the energy-calibration pattern. Without
a calibration file, fixed fallback ranges are used.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiku.db.models import AudioFeatures, Track

logger = logging.getLogger(__name__)

CALIBRATION_PATH = Path("data/vibe_calibration.json")

# Fallback normalization ranges (used when no calibration file exists).
# Centroid in Hz, complexity is the Essentia ZCR-proxy scale.
_FALLBACK_RANGES: dict[str, tuple[float, float]] = {
    "spectral_centroid": (800.0, 3200.0),
    "spectral_complexity": (2.0, 18.0),
}

# Derivation coefficients (documented in the module docstring).
_BRIGHT_W = {"mode": 0.45, "centroid": 0.40, "high_band": 0.15}
_BRIGHT_W_NO_BANDS = {"mode": 0.55, "centroid": 0.45}
_DENSITY_W = {"complexity": 0.55, "danceability": 0.45}


# ── Vibe presets ─────────────────────────────────────────────────────────
# Descriptors that match how DJs actually talk, each a target point in vibe
# space (brightness, density).
VIBE_PRESETS: dict[str, tuple[float, float]] = {
    "dark & deep": (0.15, 0.35),
    "hypnotic": (0.30, 0.25),
    "rolling": (0.50, 0.65),
    "driving": (0.50, 0.80),
    "melodic": (0.70, 0.45),
    "euphoric": (0.90, 0.60),
    "raw / peak": (0.45, 0.90),
}


@dataclass(frozen=True, slots=True)
class Vibe:
    """A track's resolved vibe."""

    brightness: float   # 0 (dark) .. 1 (bright)
    density: float       # 0 (spacious) .. 1 (busy)
    source: str          # "stored", "derived", or "none"
    label: str           # human-readable, e.g. "dark & spacious"


# ── Calibration ──────────────────────────────────────────────────────────
_calibration: dict | None = None
_calibration_loaded = False


def _load_calibration() -> dict | None:
    global _calibration, _calibration_loaded
    if _calibration_loaded:
        return _calibration
    _calibration_loaded = True
    if not CALIBRATION_PATH.exists():
        _calibration = None
        return None
    try:
        _calibration = json.loads(CALIBRATION_PATH.read_text())
    except Exception:
        logger.warning("Failed to load vibe calibration, using fallback ranges")
        _calibration = None
    return _calibration


def reset_calibration_cache() -> None:
    """Reset the calibration cache (for tests or after a re-calibrate)."""
    global _calibration, _calibration_loaded
    _calibration = None
    _calibration_loaded = False


def _range_for(feature: str) -> tuple[float, float]:
    cal = _load_calibration()
    if cal and feature in cal.get("feature_ranges", {}):
        fr = cal["feature_ranges"][feature]
        return float(fr["min"]), float(fr["max"])
    return _FALLBACK_RANGES[feature]


def _norm(value: float | None, feature: str) -> float | None:
    if value is None:
        return None
    lo, hi = _range_for(feature)
    if hi <= lo:
        return 0.5
    return _clamp((value - lo) / (hi - lo))


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


# ── Mode from key ────────────────────────────────────────────────────────
def _mode_score(key: str | None) -> float | None:
    """Major key → 1.0 (brighter), minor → 0.0 (darker). None if unknown."""
    from kiku.setbuilder.camelot import parse_camelot

    parsed = parse_camelot(key)
    if parsed is None:
        return None
    _num, letter = parsed
    return 1.0 if letter == "B" else 0.0


# ── Band ratio ───────────────────────────────────────────────────────────
def _band_mean(blob: bytes | None) -> float | None:
    if not blob:
        return None
    try:
        import numpy as np

        arr = np.frombuffer(blob, dtype=np.float32)
        if arr.size == 0:
            return None
        return float(arr.mean())
    except Exception:
        return None


def _high_band_ratio(af: AudioFeatures) -> float | None:
    """(midhigh + high) / (all four bands), from the overview envelopes."""
    low = _band_mean(af.band_low_overview)
    midlow = _band_mean(af.band_midlow_overview)
    midhigh = _band_mean(af.band_midhigh_overview)
    high = _band_mean(af.band_high_overview)
    if None in (low, midlow, midhigh, high):
        return None
    total = low + midlow + midhigh + high
    if total <= 0:
        return None
    return _clamp((midhigh + high) / total)


# ── Derivation ───────────────────────────────────────────────────────────
def derive_vibe(track: Track) -> tuple[float, float] | None:
    """Derive (brightness, density) from a track's existing features.

    Returns None if there isn't enough signal (no audio features and no key).
    """
    af = track.audio_features
    mode = _mode_score(track.key)
    centroid = _norm(af.spectral_centroid, "spectral_centroid") if af else None
    high_ratio = _high_band_ratio(af) if af else None

    brightness = _weighted_brightness(mode, centroid, high_ratio)

    density = None
    if af is not None:
        complexity = _norm(af.spectral_complexity, "spectral_complexity")
        dance = _clamp(af.danceability) if af.danceability is not None else None
        density = _weighted_density(complexity, dance)

    if brightness is None and density is None:
        return None
    # Fill a missing axis with neutral so callers always get a usable point.
    return (brightness if brightness is not None else 0.5,
            density if density is not None else 0.5)


def _weighted_brightness(
    mode: float | None, centroid: float | None, high_ratio: float | None
) -> float | None:
    if high_ratio is not None and mode is not None and centroid is not None:
        w = _BRIGHT_W
        return _clamp(w["mode"] * mode + w["centroid"] * centroid
                      + w["high_band"] * high_ratio)
    # No band data — collapse to mode + centroid.
    parts = {"mode": mode, "centroid": centroid}
    available = {k: v for k, v in parts.items() if v is not None}
    if not available:
        return None
    w = _BRIGHT_W_NO_BANDS
    total_w = sum(w[k] for k in available)
    return _clamp(sum(w[k] * v for k, v in available.items()) / total_w)


def _weighted_density(complexity: float | None, dance: float | None) -> float | None:
    parts = {"complexity": complexity, "danceability": dance}
    available = {k: v for k, v in parts.items() if v is not None}
    if not available:
        return None
    w = _DENSITY_W
    total_w = sum(w[k] for k in available)
    return _clamp(sum(w[k] * v for k, v in available.items()) / total_w)


def resolve_vibe(track: Track) -> Vibe:
    """Resolved vibe for a track: stored columns first, else derived live."""
    af = track.audio_features
    if af is not None and af.vibe_brightness is not None and af.vibe_density is not None:
        b, d = af.vibe_brightness, af.vibe_density
        return Vibe(b, d, "stored", vibe_label(b, d))

    derived = derive_vibe(track)
    if derived is None:
        return Vibe(0.5, 0.5, "none", "unknown")
    b, d = derived
    return Vibe(b, d, "derived", vibe_label(b, d))


# ── Labels ───────────────────────────────────────────────────────────────
def _brightness_word(b: float) -> str:
    if b < 0.30:
        return "dark"
    if b < 0.45:
        return "moody"
    if b < 0.60:
        return "neutral"
    if b < 0.78:
        return "bright"
    return "euphoric"


def _density_word(d: float) -> str:
    if d < 0.30:
        return "spacious"
    if d < 0.50:
        return "rolling"
    if d < 0.72:
        return "driving"
    return "busy"


def vibe_label(brightness: float, density: float) -> str:
    """Human-readable two-word vibe label, e.g. 'dark & spacious'."""
    return f"{_brightness_word(brightness)} & {_density_word(density)}"


def vibe_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Euclidean distance in vibe space, normalized to [0, 1].

    Max possible distance is sqrt(2) (opposite corners), so we divide by it.
    """
    db = a[0] - b[0]
    dd = a[1] - b[1]
    return _clamp((db * db + dd * dd) ** 0.5 / (2.0 ** 0.5))


def resolve_preset(name: str | None) -> tuple[float, float] | None:
    """Resolve a vibe preset name to a (brightness, density) target."""
    if not name:
        return None
    return VIBE_PRESETS.get(name.strip().lower())


# ── Calibration + backfill ───────────────────────────────────────────────
def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile (pct in [0, 100]). values must be sorted."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = (pct / 100.0) * (len(values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(values) - 1)
    frac = rank - lo
    return values[lo] + (values[hi] - values[lo]) * frac


def calibrate_vibe(session) -> dict:
    """Compute robust (5th/95th percentile) normalization ranges across the
    library and persist them to data/vibe_calibration.json.

    Returns the calibration dict.
    """
    from kiku.db.models import AudioFeatures

    ranges: dict[str, dict[str, float]] = {}
    sample_count = 0
    for feature in ("spectral_centroid", "spectral_complexity"):
        col = getattr(AudioFeatures, feature)
        rows = (
            session.query(col)
            .filter(col.isnot(None))
            .all()
        )
        vals = sorted(float(r[0]) for r in rows if r[0] is not None)
        sample_count = max(sample_count, len(vals))
        if vals:
            ranges[feature] = {
                "min": round(_percentile(vals, 5.0), 4),
                "max": round(_percentile(vals, 95.0), 4),
            }
        else:
            lo, hi = _FALLBACK_RANGES[feature]
            ranges[feature] = {"min": lo, "max": hi}

    calibration = {"feature_ranges": ranges, "training_samples": sample_count}
    CALIBRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALIBRATION_PATH.write_text(json.dumps(calibration, indent=2))
    reset_calibration_cache()
    return calibration


def backfill_vibe(session, recalibrate: bool = True) -> dict:
    """Derive and store vibe_brightness/vibe_density for every analyzed track.

    Operates purely on data already in the DB — no audio decoding. Returns
    {"updated": n, "skipped": m, "total": t}.
    """
    from kiku.db.models import Track

    if recalibrate:
        calibrate_vibe(session)

    tracks = (
        session.query(Track)
        .join(Track.audio_features)
        .all()
    )
    updated = skipped = 0
    for track in tracks:
        derived = derive_vibe(track)
        if derived is None:
            skipped += 1
            continue
        b, d = derived
        track.audio_features.vibe_brightness = round(b, 4)
        track.audio_features.vibe_density = round(d, 4)
        updated += 1
    session.commit()
    return {"updated": updated, "skipped": skipped, "total": len(tracks)}
