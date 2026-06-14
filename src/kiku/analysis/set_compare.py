"""Played-vs-planned comparison engine — diffs a played set against the plan it came from."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from kiku.analysis.set_analyzer import analyze_set
from kiku.analysis.teaching import detect_deviation_patterns, deviation_teaching_moment
from kiku.db.models import Set
from kiku.energy import get_track_energy
from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string

# A jump of roughly two energy zones on the 0-1 scale
ENERGY_JUMP_THRESHOLD = 0.3


@dataclass
class TrackDeviation:
    kind: str  # "kept" | "moved" | "cut" | "added"
    track_id: int
    title: str | None
    artist: str | None
    planned_position: int | None
    played_position: int | None
    displacement: int | None  # played_position - planned_position (moved only)
    teaching_moment: str


@dataclass
class EnergyDeviation:
    position: int
    track_id: int
    planned_energy: float
    played_energy: float
    delta: float
    teaching_moment: str


@dataclass
class ArcComparison:
    planned_shape: str
    played_shape: str
    planned_key_style: str
    played_key_style: str
    planned_bpm_style: str
    played_bpm_style: str
    planned_bpm_range: list[float]
    played_bpm_range: list[float]
    bpm_drift_delta: float
    planned_curve: list[float]  # target energy sampled at each played position
    played_curve: list[float]


@dataclass
class SetComparisonResult:
    played_set_id: int
    planned_set_id: int
    played_name: str | None
    planned_name: str | None
    kept_count: int
    moved_count: int
    cut_count: int
    added_count: int
    track_deviations: list[TrackDeviation]
    energy_deviations: list[EnergyDeviation]
    arc: ArcComparison
    deviation_patterns: list[str]
    compared_at: str


# ── Pure diff helpers (unit-testable without a DB) ─────────────────────


def diff_tracks(planned_ids: list[int], played_ids: list[int]) -> list[dict]:
    """Diff two track-id sequences into kept/moved/cut/added entries.

    Handles duplicate track ids as multisets: each played occurrence consumes
    the earliest unconsumed planned occurrence of the same id.
    """
    planned_pos: dict[int, list[int]] = defaultdict(list)
    for pos, tid in enumerate(planned_ids):
        planned_pos[tid].append(pos)

    entries: list[dict] = []
    for pos, tid in enumerate(played_ids):
        if planned_pos.get(tid):
            p = planned_pos[tid].pop(0)
            if p == pos:
                entries.append({
                    "kind": "kept", "track_id": tid,
                    "planned_position": p, "played_position": pos, "displacement": None,
                })
            else:
                entries.append({
                    "kind": "moved", "track_id": tid,
                    "planned_position": p, "played_position": pos, "displacement": pos - p,
                })
        else:
            entries.append({
                "kind": "added", "track_id": tid,
                "planned_position": None, "played_position": pos, "displacement": None,
            })

    for tid, positions in planned_pos.items():
        for p in positions:
            entries.append({
                "kind": "cut", "track_id": tid,
                "planned_position": p, "played_position": None, "displacement": None,
            })

    # Stable order: played order first, then cuts by planned position
    entries.sort(key=lambda e: (
        e["played_position"] is None,
        e["played_position"] if e["played_position"] is not None else e["planned_position"],
    ))
    return entries


def detect_energy_jumps(
    planned_curve: list[float],
    played_curve: list[float],
    threshold: float = ENERGY_JUMP_THRESHOLD,
) -> list[tuple[int, float]]:
    """Flag positions where played energy deviates from the planned curve by >= threshold.

    Returns (position, delta) tuples with delta = played - planned.
    """
    jumps: list[tuple[int, float]] = []
    for i, (planned, played) in enumerate(zip(planned_curve, played_curve)):
        delta = round(played - planned, 3)
        if abs(delta) >= threshold:
            jumps.append((i, delta))
    return jumps


def _resample(curve: list[float], count: int) -> list[float]:
    """Linearly resample a curve to `count` points."""
    if not curve or count <= 0:
        return [0.5] * max(count, 0)
    if len(curve) == 1:
        return [curve[0]] * count
    out: list[float] = []
    for i in range(count):
        t = (i / max(count - 1, 1)) * (len(curve) - 1)
        lo = int(t)
        hi = min(lo + 1, len(curve) - 1)
        frac = t - lo
        out.append(round(curve[lo] * (1 - frac) + curve[hi] * frac, 3))
    return out


# ── Core comparison ─────────────────────────────────────────────────────


def _planned_target_curve(planned: Set, planned_arc_curve: list[float], count: int) -> list[float]:
    """Target energy at each played position: explicit profile first, planned arc as fallback."""
    if planned.energy_profile:
        try:
            try:
                profile = parse_energy_json(planned.energy_profile)
            except (json.JSONDecodeError, KeyError, TypeError):
                profile = parse_energy_string(planned.energy_profile)
            total = profile.total_duration_min or planned.duration_min or 120
            return [
                round(profile.target_energy_at((i / max(count - 1, 1)) * total), 3)
                for i in range(count)
            ]
        except (ValueError, KeyError, TypeError):
            pass
    return _resample(planned_arc_curve, count)


def _played_energies(set_tracks) -> list[float]:
    """Resolved energy per played track: track cascade first, inferred fallback, neutral last."""
    energies: list[float] = []
    for st in set_tracks:
        if st.track is not None:
            te = get_track_energy(st.track)
            if te.numeric is not None:
                energies.append(round(te.numeric, 3))
                continue
        if st.inferred_energy is not None:
            energies.append(round(st.inferred_energy, 3))
        else:
            energies.append(0.5)
    return energies


def compare_sets(db: Session, played_id: int, planned_id: int) -> SetComparisonResult:
    """Compare a played set against its plan and cache the result on the played set."""
    played = db.get(Set, played_id)
    if not played:
        raise ValueError(f"Set {played_id} not found")
    planned = db.get(Set, planned_id)
    if not planned:
        raise ValueError(f"Set {planned_id} not found")
    if played_id == planned_id:
        raise ValueError("A set can't be compared against itself")

    # Arc analysis per side (also infers energy for untagged tracks)
    played_analysis = analyze_set(db, played_id)
    planned_analysis = analyze_set(db, planned_id)

    played_sts = sorted(played.tracks, key=lambda st: st.position)
    planned_sts = sorted(planned.tracks, key=lambda st: st.position)

    # Track-level diff (ID-based — imported sets resolve to library track ids)
    planned_ids = [st.track_id for st in planned_sts]
    played_ids = [st.track_id for st in played_sts]
    raw_entries = diff_tracks(planned_ids, played_ids)

    track_lookup = {st.track_id: st.track for st in planned_sts + played_sts if st.track}
    deviations: list[TrackDeviation] = []
    for e in raw_entries:
        t = track_lookup.get(e["track_id"])
        deviations.append(TrackDeviation(
            kind=e["kind"],
            track_id=e["track_id"],
            title=t.title if t else None,
            artist=t.artist if t else None,
            planned_position=e["planned_position"],
            played_position=e["played_position"],
            displacement=e["displacement"],
            teaching_moment=deviation_teaching_moment(
                e["kind"],
                title=t.title if t else None,
                displacement=e["displacement"],
            ),
        ))

    # Energy: planned target curve sampled at played positions vs played resolved energies
    played_curve = _played_energies(played_sts)
    planned_curve = _planned_target_curve(
        planned, planned_analysis.arc.energy_curve, len(played_sts)
    )

    energy_deviations: list[EnergyDeviation] = []
    for pos, delta in detect_energy_jumps(planned_curve, played_curve):
        energy_deviations.append(EnergyDeviation(
            position=pos,
            track_id=played_sts[pos].track_id,
            planned_energy=planned_curve[pos],
            played_energy=played_curve[pos],
            delta=delta,
            teaching_moment=deviation_teaching_moment(
                "energy_jump", delta=delta, position=pos,
            ),
        ))

    arc = ArcComparison(
        planned_shape=planned_analysis.arc.energy_shape,
        played_shape=played_analysis.arc.energy_shape,
        planned_key_style=planned_analysis.arc.key_style,
        played_key_style=played_analysis.arc.key_style,
        planned_bpm_style=planned_analysis.arc.bpm_style,
        played_bpm_style=played_analysis.arc.bpm_style,
        planned_bpm_range=list(planned_analysis.arc.bpm_range),
        played_bpm_range=list(played_analysis.arc.bpm_range),
        bpm_drift_delta=round(played_analysis.arc.bpm_drift - planned_analysis.arc.bpm_drift, 1),
        planned_curve=planned_curve,
        played_curve=played_curve,
    )

    kinds = [d.kind for d in deviations]
    patterns = detect_deviation_patterns(
        [(d.kind, d.played_position) for d in deviations],
        [round(p - q, 3) for p, q in zip(played_curve, planned_curve)],
        len(played_sts),
    )

    result = SetComparisonResult(
        played_set_id=played_id,
        planned_set_id=planned_id,
        played_name=played.name,
        planned_name=planned.name,
        kept_count=kinds.count("kept"),
        moved_count=kinds.count("moved"),
        cut_count=kinds.count("cut"),
        added_count=kinds.count("added"),
        track_deviations=deviations,
        energy_deviations=energy_deviations,
        arc=arc,
        deviation_patterns=patterns,
        compared_at=datetime.now().isoformat(),
    )

    # Cache on the played set (same pattern as analysis_cache)
    played.comparison_cache = json.dumps(asdict(result))
    db.commit()

    return result
