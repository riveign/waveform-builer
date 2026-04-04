"""Unified energy resolution for tracks.

Single source of truth for energy zone, numeric value, and provenance.
All consumers should use get_track_energy() instead of accessing raw fields.
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


@dataclass(frozen=True, slots=True)
class TrackEnergy:
    """Resolved energy for a track."""

    zone: str | None       # Canonical zone: warmup, build, drive, peak, close
    numeric: float         # 0-1 value, always available
    source: str            # Provenance: "approved", "dir_energy", "predicted", "audio", "none"
    confidence: float      # 0-1 trust level
    label: str             # Human-readable: "build (folder)", "drive (estimated)"


# Fixed fallback boundaries (used when no calibration file exists)
_FALLBACK_ZONE_BOUNDARIES: list[tuple[float, str]] = [
    (0.40, "warmup"),
    (0.63, "build"),
    (0.80, "drive"),
    (1.01, "peak"),  # 1.01 so 1.0 maps to peak
]

# Module-level calibration cache
_calibration: dict | None = None
_calibration_loaded: bool = False


def _load_calibration() -> dict | None:
    """Lazy-load energy calibration from data/energy_calibration.json."""
    global _calibration, _calibration_loaded
    if _calibration_loaded:
        return _calibration

    _calibration_loaded = True
    cal_path = Path("data/energy_calibration.json")
    if not cal_path.exists():
        _calibration = None
        return None

    try:
        _calibration = json.loads(cal_path.read_text())
        logger.info("Loaded energy calibration (%d samples)", _calibration.get("training_samples", 0))
    except Exception:
        logger.warning("Failed to load energy calibration, using fallback boundaries")
        _calibration = None
    return _calibration


def reset_calibration_cache() -> None:
    """Reset the calibration cache (for testing or after retrain)."""
    global _calibration, _calibration_loaded
    _calibration = None
    _calibration_loaded = False


def _get_zone_boundaries() -> list[tuple[float, str]]:
    """Get zone boundaries — calibrated if available, fallback otherwise."""
    cal = _load_calibration()
    if cal and "zone_boundaries" in cal:
        return [(b, z) for b, z in cal["zone_boundaries"]]
    return _FALLBACK_ZONE_BOUNDARIES


def composite_energy_score(af: AudioFeatures) -> float | None:
    """Compute composite energy score from multiple audio features.

    Uses calibration weights if available. Returns None if calibration
    is not loaded or required features are missing.
    """
    cal = _load_calibration()
    if cal is None:
        return None

    weights = cal.get("composite_weights")
    ranges = cal.get("feature_ranges")
    if not weights or not ranges:
        return None

    from kiku.analysis.autotag import extract_features, feature_names

    features = extract_features(af)
    if features is None:
        return None

    names = feature_names()
    score = 0.0
    for i, name in enumerate(names):
        if name not in weights or name not in ranges:
            continue
        fr = ranges[name]
        rng = fr["max"] - fr["min"]
        normalized = (features[i] - fr["min"]) / rng if rng > 0 else 0.5
        score += weights[name] * normalized

    return score


def numeric_to_zone(energy: float) -> str:
    """Derive zone label from numeric energy value.

    Uses calibrated boundaries when available, fallback otherwise.
    "close" is positional (end of set), not derivable from energy alone.
    """
    for threshold, zone in _get_zone_boundaries():
        if energy < threshold:
            return zone
    return "peak"


_SOURCE_LABELS: dict[str, str] = {
    "approved": "",           # DJ confirmed — no qualifier needed
    "dir_energy": "folder",
    "predicted": "estimated",
    "audio": "from audio",
    "none": "",
}


def format_energy_label(zone: str | None, source: str) -> str:
    """Format human-readable energy label with provenance."""
    if zone is None:
        return "unknown"
    qualifier = _SOURCE_LABELS.get(source, source)
    if qualifier:
        return f"{zone} ({qualifier})"
    return zone


def get_track_energy(track: Track) -> TrackEnergy:
    """Unified energy resolution for a track.

    Combines zone cascade (approved > dir_energy > predicted) with
    numeric precision from audio_features.energy.
    """
    from kiku.analysis.autotag import resolve_energy
    from kiku.setbuilder.constraints import zone_to_numeric

    zone, source, confidence = resolve_energy(track)

    # Numeric resolution:
    # 1. audio_features.energy (Essentia, highest precision, 98.7% coverage)
    # 2. zone_to_numeric(resolved_zone) (from cascade)
    # 3. 0.5 (neutral fallback)
    if track.audio_features and track.audio_features.energy is not None:
        numeric = track.audio_features.energy
        if zone is None:
            # Try composite score for better zone derivation
            comp = composite_energy_score(track.audio_features)
            if comp is not None:
                zone = numeric_to_zone(comp)
                source = "audio"
                confidence = 0.6  # Composite-derived, better than raw but not explicit
            else:
                zone = numeric_to_zone(numeric)
                source = "audio"
                confidence = 0.5  # Raw energy only — heavily skewed
    else:
        numeric = zone_to_numeric(zone) if zone else 0.5
        if numeric is None:
            numeric = 0.5
        if zone is None:
            source = "none"

    label = format_energy_label(zone, source)

    return TrackEnergy(
        zone=zone,
        numeric=numeric,
        source=source,
        confidence=confidence,
        label=label,
    )
