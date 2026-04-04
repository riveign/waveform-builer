"""Unified energy resolution for tracks.

Single source of truth for energy zone, numeric value, and provenance.
All consumers should use get_track_energy() instead of accessing raw fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiku.db.models import Track


@dataclass(frozen=True, slots=True)
class TrackEnergy:
    """Resolved energy for a track."""

    zone: str | None       # Canonical zone: warmup, build, drive, peak, close
    numeric: float         # 0-1 value, always available
    source: str            # Provenance: "approved", "dir_energy", "predicted", "audio", "none"
    confidence: float      # 0-1 trust level
    label: str             # Human-readable: "build (folder)", "drive (estimated)"


# Boundaries derived from ENERGY_TAG_VALUES midpoints in constraints.py
_ZONE_BOUNDARIES: list[tuple[float, str]] = [
    (0.40, "warmup"),
    (0.63, "build"),
    (0.80, "drive"),
    (1.01, "peak"),  # 1.01 so 1.0 maps to peak
]


def numeric_to_zone(energy: float) -> str:
    """Derive zone label from numeric energy value.

    Boundaries match the ENERGY_TAG_VALUES midpoints:
    warmup: 0.0-0.40, build: 0.40-0.63, drive: 0.63-0.80, peak: 0.80-1.0
    "close" is positional (end of set), not derivable from energy alone.
    """
    for threshold, zone in _ZONE_BOUNDARIES:
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
            zone = numeric_to_zone(numeric)
            source = "audio"
            confidence = 0.7  # Derived, not explicit
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
