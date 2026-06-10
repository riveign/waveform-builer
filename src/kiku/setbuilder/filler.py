"""Fill algorithm — propose track insertions to fill gaps in a set."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generator

from sqlalchemy.orm import Session

from kiku.db.models import Set, Track
from kiku.setbuilder.constraints import EnergyProfile, parse_energy_json, parse_energy_string
from kiku.setbuilder.planner import _get_candidate_pool, _violates_artist_cooldown
from kiku.setbuilder.scoring import genre_momentum_bonus, score_replacement, transition_score


DEFAULT_GAP_THRESHOLD = 0.6


@dataclass
class FillEvent:
    """Base event for fill SSE stream."""

    event: str
    data: dict


def fill_set(
    db: Session,
    set_id: int,
    energy_profile: EnergyProfile | None = None,
    target_duration_min: int | None = None,
    max_fill_tracks: int = 10,
    genre_filter: list[str] | None = None,
    gap_threshold: float = DEFAULT_GAP_THRESHOLD,
    discovery_density: float = 0.0,
    weights: dict[str, float] | None = None,
) -> Generator[FillEvent, None, None]:
    """Propose track insertions to fill gaps in a manually-built set.

    Yields SSE-ready FillEvent objects as it works.
    """
    set_ = db.get(Set, set_id)
    if not set_:
        yield FillEvent("error", {"detail": "Set not found"})
        return

    set_tracks = sorted(set_.tracks, key=lambda st: st.position)
    tracks: list[Track] = [st.track for st in set_tracks if st.track]

    if len(tracks) < 1:
        yield FillEvent("error", {"detail": "Set must have at least 1 track to fill"})
        return

    # Resolve energy profile
    if energy_profile is None and set_.energy_profile:
        try:
            energy_profile = parse_energy_json(set_.energy_profile)
        except Exception:
            try:
                energy_profile = parse_energy_string(set_.energy_profile)
            except Exception:
                pass

    # Compute current duration
    current_duration_sec = sum(t.duration_sec or 0 for t in tracks)
    current_duration_min = current_duration_sec / 60

    yield FillEvent("fill_started", {
        "set_id": set_id,
        "current_tracks": len(tracks),
        "current_duration_min": round(current_duration_min, 1),
    })

    # Score all transitions and find gaps
    elapsed_min = 0.0
    gaps: list[dict] = []
    for i in range(len(tracks) - 1):
        elapsed_min += (tracks[i].duration_sec or 360) / 60
        target_e = energy_profile.target_energy_at(elapsed_min) if energy_profile else 0.5
        score = transition_score(tracks[i], tracks[i + 1], target_energy=target_e, weights=weights)
        if score < gap_threshold:
            gaps.append({
                "position": i + 1,
                "from_track": tracks[i],
                "to_track": tracks[i + 1],
                "score": round(score, 3),
                "target_energy": target_e,
                "elapsed_min": elapsed_min,
            })

    # Check if we need to extend to reach target duration
    if target_duration_min and current_duration_min < target_duration_min:
        last_elapsed = sum((t.duration_sec or 360) / 60 for t in tracks)
        target_e = energy_profile.target_energy_at(last_elapsed) if energy_profile else 0.5
        gaps.append({
            "position": len(tracks),
            "from_track": tracks[-1],
            "to_track": None,
            "score": 0.0,
            "target_energy": target_e,
            "elapsed_min": last_elapsed,
        })

    # Sort by worst score first
    gaps.sort(key=lambda g: g["score"])

    # Get candidate pool
    bpm_values = [t.bpm for t in tracks if t.bpm]
    bpm_range = None
    if bpm_values:
        avg_bpm = sum(bpm_values) / len(bpm_values)
        bpm_range = (avg_bpm * 0.85, avg_bpm * 1.15)
    candidates = _get_candidate_pool(db, genres=genre_filter, bpm_range=bpm_range)
    existing_ids = {t.id for t in tracks}
    candidates = [c for c in candidates if c.id not in existing_ids]

    proposals_count = 0
    for gap in gaps:
        if proposals_count >= max_fill_tracks:
            break

        yield FillEvent("gap_identified", {
            "position": gap["position"],
            "from_track_id": gap["from_track"].id,
            "to_track_id": gap["to_track"].id if gap["to_track"] else None,
            "current_score": gap["score"],
            "target_energy": gap["target_energy"],
        })

        # Score candidates for this gap
        prev_track = gap["from_track"]
        next_track = gap["to_track"]
        target_e = gap["target_energy"]

        # Gather preceding tracks for genre momentum context
        pos = gap["position"]
        preceding = tracks[:pos]  # tracks before the gap

        scored_candidates = []
        for cand in candidates:
            if cand.id in existing_ids:
                continue
            if _violates_artist_cooldown(tracks, cand):
                continue
            combined, incoming_bd, outgoing_bd = score_replacement(
                cand, prev_track, next_track, target_energy=target_e,
                weights=weights, discovery_density=discovery_density,
            )
            # Genre momentum: reward candidates continuing the genre arc
            momentum = genre_momentum_bonus(preceding, cand, window=3)
            combined = round(combined + momentum, 3)
            scored_candidates.append((cand, combined, incoming_bd, outgoing_bd))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        if scored_candidates:
            best, best_score, best_in, best_out = scored_candidates[0]
            explanation = _build_explanation(best, prev_track, next_track, best_score, best_in, best_out, target_e)

            yield FillEvent("fill_proposed", {
                "position": gap["position"],
                "track_id": best.id,
                "track_title": best.title,
                "track_artist": best.artist,
                "track_bpm": best.bpm,
                "track_key": best.key,
                "score": round(best_score, 3),
                "breakdown": best_in,
                "explanation": explanation,
            })
            proposals_count += 1
            existing_ids.add(best.id)

    yield FillEvent("fill_complete", {
        "proposals_count": proposals_count,
        "estimated_duration_min": round(current_duration_min + proposals_count * 5.5, 1),
    })


def _build_explanation(
    candidate: Track,
    prev_track: Track,
    next_track: Track | None,
    score: float,
    incoming: dict | None,
    outgoing: dict | None,
    target_energy: float,
) -> str:
    """Build a human-readable explanation for a fill proposal."""
    parts = []

    if incoming:
        h = incoming.get("harmonic", 0)
        if h >= 0.85:
            parts.append(f"key from {prev_track.key} to {candidate.key} is a smooth move")
        elif h >= 0.7:
            parts.append(f"key shift {prev_track.key} to {candidate.key} works")

    if candidate.bpm and prev_track.bpm:
        diff_pct = abs(candidate.bpm - prev_track.bpm) / prev_track.bpm * 100
        if diff_pct <= 3:
            parts.append(f"BPM {prev_track.bpm:.0f} to {candidate.bpm:.0f} is seamless")
        elif diff_pct <= 6:
            parts.append(f"BPM {prev_track.bpm:.0f} to {candidate.bpm:.0f} is manageable")

    if not parts:
        parts.append(f"overall score {score:.2f} against neighbors")

    return "; ".join(parts)
