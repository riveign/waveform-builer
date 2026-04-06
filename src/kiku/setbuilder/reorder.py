"""Reorder algorithms — optimize track order for flow."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from kiku.db.models import Track
from kiku.setbuilder.constraints import EnergyProfile
from kiku.setbuilder.scoring import transition_score


@dataclass
class OrderChange:
    """Describes a single track movement."""

    track_id: int
    track_title: str | None
    from_position: int
    to_position: int
    explanation: str


def score_full_sequence(
    tracks: list[Track],
    energy_profile: EnergyProfile | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    """Score a full track sequence using position-aware energy targets."""
    if len(tracks) < 2:
        return 1.0
    total = 0.0
    elapsed = 0.0
    for i in range(1, len(tracks)):
        target_e = energy_profile.target_energy_at(elapsed) if energy_profile else 0.5
        total += transition_score(tracks[i - 1], tracks[i], target_energy=target_e, weights=weights)
        elapsed += (tracks[i - 1].duration_sec or 360) / 60
    return total / (len(tracks) - 1)


def optimize_gentle(
    tracks: list[Track],
    energy_profile: EnergyProfile | None = None,
    weights: dict[str, float] | None = None,
    max_iterations: int = 50,
    window: int = 3,
) -> tuple[list[Track], list[OrderChange]]:
    """Local swap optimization. Iteratively improves pairs within a window.

    Returns (new_order, changes).
    """
    current = list(tracks)
    best_score = score_full_sequence(current, energy_profile, weights)
    original_positions = {t.id: i for i, t in enumerate(tracks)}
    improved = True
    iteration = 0

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(len(current)):
            for j in range(i + 1, min(i + window + 1, len(current))):
                candidate = list(current)
                candidate[i], candidate[j] = candidate[j], candidate[i]
                new_score = score_full_sequence(candidate, energy_profile, weights)
                if new_score > best_score:
                    current = candidate
                    best_score = new_score
                    improved = True

    changes = _diff_orders(tracks, current, original_positions, energy_profile)
    return current, changes


def optimize_full(
    tracks: list[Track],
    energy_profile: EnergyProfile | None = None,
    weights: dict[str, float] | None = None,
    iterations: int = 5000,
    initial_temp: float = 1.0,
    cooling_rate: float = 0.995,
) -> tuple[list[Track], list[OrderChange]]:
    """Simulated annealing over the full sequence.

    Returns (best_order, changes).
    """
    n = len(tracks)
    if n < 2:
        return list(tracks), []

    current = list(tracks)
    current_score = score_full_sequence(current, energy_profile, weights)
    best = list(current)
    best_score = current_score
    original_positions = {t.id: i for i, t in enumerate(tracks)}
    temp = initial_temp

    for _ in range(iterations):
        i, j = random.sample(range(n), 2)
        candidate = list(current)
        candidate[i], candidate[j] = candidate[j], candidate[i]
        new_score = score_full_sequence(candidate, energy_profile, weights)

        delta = new_score - current_score
        if delta > 0 or (temp > 0 and random.random() < math.exp(delta / temp)):
            current = candidate
            current_score = new_score
            if current_score > best_score:
                best = list(current)
                best_score = current_score

        temp *= cooling_rate

    changes = _diff_orders(tracks, best, original_positions, energy_profile)
    return best, changes


def get_energy_curve(
    tracks: list[Track],
    energy_profile: EnergyProfile | None = None,
) -> list[float]:
    """Get energy values for each track position."""
    from kiku.energy import get_track_energy

    return [get_track_energy(t).numeric for t in tracks]


def _diff_orders(
    original: list[Track],
    proposed: list[Track],
    original_positions: dict[int, int],
    energy_profile: EnergyProfile | None = None,
) -> list[OrderChange]:
    """Compare original and proposed orders, generate change explanations."""
    from kiku.energy import get_track_energy

    changes: list[OrderChange] = []
    for new_pos, track in enumerate(proposed):
        old_pos = original_positions.get(track.id, new_pos)
        if old_pos != new_pos:
            te = get_track_energy(track)
            explanation = f"energy ({te.numeric:.2f})"
            if energy_profile:
                elapsed = sum((proposed[j].duration_sec or 360) / 60 for j in range(new_pos))
                target = energy_profile.target_energy_at(elapsed)
                explanation += f" better fits target ({target:.2f}) at this position"
            else:
                explanation += " improves transition flow at this position"

            changes.append(OrderChange(
                track_id=track.id,
                track_title=track.title,
                from_position=old_pos,
                to_position=new_pos,
                explanation=explanation,
            ))

    return changes
