"""Best-fit-anywhere artist pick ranker.

Given an open set and an artist name, rank that artist's owned tracks
(collaborations included) by the best insertion gap in the set. Reuses
``score_replacement`` (two-neighbor insertion scoring) — no new scorer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from kiku.artists import artist_matches
from kiku.db.models import Set, Track
from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string
from kiku.setbuilder.scoring import score_replacement


@dataclass
class ArtistPick:
    """One ranked artist pick with its best insertion slot."""

    track: Track
    position: int  # suggested insertion gap (0..len(set))
    score: float  # best-gap combined score
    breakdown: dict  # breakdown dict at the chosen gap (score_replacement shape)
    reason: str  # mentor-voice teaching line


def _energy_target_at_gap(profile, gap: int, gap_count: int, duration_min: float) -> float:
    """Energy target for an insertion at ``gap`` from its positional fraction."""
    if profile is None:
        return 0.5
    fraction = gap / max(gap_count, 1)
    elapsed = fraction * (duration_min or 120)
    return profile.target_energy_at(elapsed)


def _reason_for(breakdown: dict, position: int) -> str:
    """Build a warm teaching line from the dominant breakdown dimension.

    Mirrors the phrasing style of analysis/teaching.py. Never blames.
    """
    pos_label = f"fits at position {position + 1}"
    if not breakdown:
        return f"{pos_label} — a fresh face for this stretch of the set."
    dims = {
        "harmonic": breakdown.get("harmonic", 0.0),
        "energy_fit": breakdown.get("energy_fit", 0.0),
        "bpm_compat": breakdown.get("bpm_compat", 0.0),
        "genre_coherence": breakdown.get("genre_coherence", 0.0),
    }
    dominant = max(dims, key=lambda k: dims[k])
    phrases = {
        "harmonic": "the keys lock in cleanly here",
        "energy_fit": "it sits right on the energy you're shaping",
        "bpm_compat": "the tempo glues straight in",
        "genre_coherence": "it keeps the genre thread running",
    }
    return f"{pos_label} — {phrases[dominant]}."


def rank_artist_picks(
    session: Session,
    set_id: int,
    artist: str,
    n: int = 5,
    weights: dict[str, float] | None = None,
    discovery_density: float = 0.0,
) -> list[ArtistPick]:
    """Rank an artist's owned tracks by their best insertion gap in the set.

    Returns up to ``n`` picks ordered by best-gap score (descending). Returns
    an empty list when the set is missing or the artist owns nothing new.
    """
    s = session.get(Set, set_id)
    if not s:
        return []

    ordered = sorted(s.tracks, key=lambda st: st.position)
    set_track_ids = {st.track_id for st in ordered}
    ordered_tracks = [st.track for st in ordered]

    # Parse energy profile (JSON first, then string fallback).
    profile = None
    if s.energy_profile:
        try:
            try:
                profile = parse_energy_json(s.energy_profile)
            except (json.JSONDecodeError, KeyError):
                profile = parse_energy_string(s.energy_profile)
        except Exception:
            profile = None

    duration_min = s.duration_min or 120
    gap_count = len(ordered_tracks)

    # Candidate pool: ilike prefilter at the DB, then exact token gate.
    prefilter = (
        session.query(Track)
        .filter(Track.artist.isnot(None), Track.artist.ilike(f"%{artist}%"))
        .all()
    )
    candidates = [
        t
        for t in prefilter
        if t.id not in set_track_ids and artist_matches(artist, t.artist)
    ]

    picks: list[ArtistPick] = []
    for cand in candidates:
        best_score = float("-inf")
        best_gap = 0
        best_breakdown: dict = {}
        # Gaps 0..gap_count: before first track, between, after last.
        for gap in range(gap_count + 1):
            prev_track = ordered_tracks[gap - 1] if gap > 0 else None
            next_track = ordered_tracks[gap] if gap < gap_count else None
            target_energy = _energy_target_at_gap(profile, gap, gap_count, duration_min)
            combined, incoming, outgoing = score_replacement(
                cand, prev_track, next_track, target_energy=target_energy,
                weights=weights, discovery_density=discovery_density,
            )
            if combined > best_score:
                best_score = combined
                best_gap = gap
                # Prefer the incoming (prev→cand) breakdown; fall back to outgoing.
                best_breakdown = incoming or outgoing or {}
        picks.append(ArtistPick(
            track=cand,
            position=best_gap,
            score=round(best_score, 3),
            breakdown=best_breakdown,
            reason=_reason_for(best_breakdown, best_gap),
        ))

    picks.sort(key=lambda p: p.score, reverse=True)
    return picks[:n]
