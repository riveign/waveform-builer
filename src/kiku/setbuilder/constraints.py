"""Energy profiles, genre filters, and constraint definitions for set building."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class EnergySegment:
    """A segment of the energy profile."""

    name: str
    duration_min: int
    target_energy: float  # 0.0 - 1.0


@dataclass
class EnergyProfile:
    """Full energy profile for a set."""

    segments: list[EnergySegment]

    @property
    def total_duration_min(self) -> int:
        return sum(s.duration_min for s in self.segments)

    def target_energy_at(self, elapsed_min: float) -> float:
        """Get the target energy at a given time in the set.

        Interpolates linearly between segment boundaries.
        """
        cumulative = 0.0
        for i, seg in enumerate(self.segments):
            seg_end = cumulative + seg.duration_min
            if elapsed_min <= seg_end:
                # Within this segment
                if i == 0:
                    return seg.target_energy
                prev_energy = self.segments[i - 1].target_energy
                progress = (elapsed_min - cumulative) / seg.duration_min if seg.duration_min > 0 else 1.0
                return prev_energy + (seg.target_energy - prev_energy) * progress
            cumulative = seg_end

        # Past end — return last segment energy
        return self.segments[-1].target_energy if self.segments else 0.5


def parse_energy_string(s: str) -> EnergyProfile:
    """Parse energy string like 'warmup:30:0.3,build:20:0.6,peak:40:0.9,cooldown:20:0.4'."""
    segments = []
    for part in s.split(","):
        parts = part.strip().split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid energy segment: '{part}'. Expected 'name:minutes:energy'")
        name, minutes, energy = parts
        segments.append(EnergySegment(
            name=name.strip(),
            duration_min=int(minutes),
            target_energy=float(energy),
        ))
    return EnergyProfile(segments=segments)


def parse_energy_json(s: str) -> EnergyProfile:
    """Parse energy profile from JSON stored by planner.

    Expects a JSON string like:
    [{"name":"warmup","duration_min":30,"target_energy":0.3}, ...]
    """
    data = json.loads(s)
    segments = [
        EnergySegment(
            name=d["name"],
            duration_min=int(d["duration_min"]),
            target_energy=float(d["target_energy"]),
        )
        for d in data
    ]
    return EnergyProfile(segments=segments)


# Map directory energy tags to approximate numeric values
ENERGY_TAG_VALUES = {
    "low": 0.2,
    "warmup": 0.25,
    "closing": 0.3,
    "mid": 0.5,
    "dance": 0.6,
    "up": 0.7,
    "high": 0.8,
    "fast": 0.8,
    "peak": 0.9,
}


# ── Energy Presets ──────────────────────────────────────────────────────

DEFAULT_ENERGY_PRESETS: dict[str, str] = {
    "warmup": "warmup:40:0.3,build:30:0.5,groove:30:0.6",
    "peak-time": "hype:20:0.7,peak:50:0.9,sustain:30:0.8",
    "journey": "warmup:30:0.3,build:20:0.6,peak:40:0.9,cooldown:20:0.4",
    "afterhours": "deep:30:0.3,hypno:40:0.4,drift:30:0.25",
}


def get_energy_presets() -> dict[str, str]:
    """Return energy presets merged from defaults + TOML config."""
    from kiku.config import _load_toml

    toml = _load_toml()
    toml_presets = toml.get("energy_presets", {})
    return {**DEFAULT_ENERGY_PRESETS, **toml_presets}


def resolve_energy(energy_str: str) -> EnergyProfile:
    """Resolve an energy string — checks presets first, then raw format."""
    presets = get_energy_presets()
    raw = presets.get(energy_str.lower(), energy_str)
    return parse_energy_string(raw)


def dir_energy_to_numeric(tag: str | None) -> float | None:
    """Convert a directory energy tag to a 0-1 numeric value."""
    if not tag:
        return None
    return ENERGY_TAG_VALUES.get(tag.lower())
