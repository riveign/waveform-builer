"""Transition scoring between tracks."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from djsetbuilder.config import BPM_TOLERANCE, SCORING_WEIGHTS
from djsetbuilder.db.models import Track
from djsetbuilder.setbuilder.camelot import harmonic_score
from djsetbuilder.setbuilder.constraints import dir_energy_to_numeric


def bpm_compatibility(bpm_a: float | None, bpm_b: float | None) -> float:
    """Score BPM compatibility (0-1). Allows ±6% and double/half time."""
    if not bpm_a or not bpm_b or bpm_a <= 0 or bpm_b <= 0:
        return 0.5  # Unknown — neutral

    ratio = bpm_b / bpm_a

    # Check direct compatibility
    diff_pct = abs(ratio - 1.0)
    if diff_pct <= BPM_TOLERANCE:
        return 1.0 - (diff_pct / BPM_TOLERANCE) * 0.3  # 0.7-1.0

    # Check double time
    diff_double = abs(ratio - 2.0)
    if diff_double <= BPM_TOLERANCE:
        return 0.6

    # Check half time
    diff_half = abs(ratio - 0.5)
    if diff_half <= BPM_TOLERANCE:
        return 0.6

    # Larger BPM gap
    if diff_pct <= 0.12:
        return 0.3
    return 0.1


def genre_coherence(genre_a: str | None, genre_b: str | None) -> float:
    """Score genre compatibility between two tracks."""
    if not genre_a or not genre_b:
        return 0.5

    ga = genre_a.lower().strip()
    gb = genre_b.lower().strip()

    if ga == gb:
        return 1.0

    # Define genre families
    families = {
        "techno": ["techno", "hard techno", "rumble techno", "acid techno",
                    "dub techno", "techno groove", "hypno", "hypno techno"],
        "house": ["house", "deep house", "tech house", "afro house",
                  "funky house", "hard house", "speed house"],
        "groove": ["hard groove", "hardgroove", "light groove", "ghetto groove"],
        "trance": ["trance", "hard trance"],
        "breaks": ["breaks", "dnb", "garage"],
        "electronic": ["electro", "acid", "bounce", "nu disco", "indie dance"],
        "other": ["dub", "new wave", "post punk", "nacional"],
    }

    family_a = None
    family_b = None
    for family, members in families.items():
        if ga in members:
            family_a = family
        if gb in members:
            family_b = family

    if family_a and family_b:
        if family_a == family_b:
            return 0.8
        # Some families are more compatible
        compatible = {
            frozenset({"techno", "groove"}),
            frozenset({"techno", "electronic"}),
            frozenset({"house", "groove"}),
            frozenset({"house", "electronic"}),
        }
        if frozenset({family_a, family_b}) in compatible:
            return 0.5
        return 0.2

    return 0.3


def energy_fit(track: Track, target_energy: float) -> float:
    """Score how well a track's energy matches the target."""
    # Prefer audio-analyzed energy if available
    if track.audio_features and track.audio_features.energy is not None:
        track_energy = track.audio_features.energy
    else:
        track_energy = dir_energy_to_numeric(track.dir_energy)

    if track_energy is None:
        return 0.5  # Unknown — neutral

    diff = abs(track_energy - target_energy)
    return max(0.0, 1.0 - diff * 2.0)


def track_quality(track: Track, prefer_playlists: list[str] | None = None) -> float:
    """Score track quality based on rating, play count, and playlist membership (0-1)."""
    score = 0.0

    # Rating: 0-5 stars, normalize to 0-1 (unrated gets 0.3)
    if track.rating and track.rating > 0:
        score += 0.4 * (track.rating / 5.0)
    else:
        score += 0.4 * 0.3

    # Play count: more plays = more proven, cap at 10
    plays = min(track.play_count or 0, 10)
    score += 0.3 * (plays / 10.0)

    # Playlist membership boost
    if prefer_playlists and track.playlist_tags:
        try:
            tags = json.loads(track.playlist_tags)
            matching = sum(1 for t in tags if any(p.lower() in t.lower() for p in prefer_playlists))
            score += 0.3 * min(matching / len(prefer_playlists), 1.0)
        except (json.JSONDecodeError, TypeError):
            pass

    return score


def transition_score(
    from_track: Track,
    to_track: Track,
    target_energy: float = 0.5,
    prefer_playlists: list[str] | None = None,
) -> float:
    """Compute overall transition score between two tracks."""
    w = SCORING_WEIGHTS

    h = harmonic_score(from_track.key, to_track.key)
    e = energy_fit(to_track, target_energy)
    b = bpm_compatibility(from_track.bpm, to_track.bpm)
    g = genre_coherence(
        from_track.dir_genre or from_track.rb_genre,
        to_track.dir_genre or to_track.rb_genre,
    )
    q = track_quality(to_track, prefer_playlists)

    return (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
            + w["genre_coherence"] * g + w["track_quality"] * q)


def score_transitions(
    session: Session,
    from_track: Track,
    n: int = 10,
    genre_filter: list[str] | None = None,
) -> list[tuple[Track, float]]:
    """Find and score best transitions from a given track."""
    q = session.query(Track).filter(Track.id != from_track.id)

    # BPM pre-filter
    if from_track.bpm and from_track.bpm > 0:
        bpm_lo = from_track.bpm * (1 - BPM_TOLERANCE * 2)
        bpm_hi = from_track.bpm * (1 + BPM_TOLERANCE * 2)
        q = q.filter(Track.bpm.between(bpm_lo, bpm_hi))

    if genre_filter:
        genre_conditions = [Track.dir_genre.ilike(f"%{g}%") for g in genre_filter]
        q = q.filter(
            Track.dir_genre.isnot(None),
            *[],  # SQLAlchemy or_
        )
        from sqlalchemy import or_
        q = q.filter(or_(*genre_conditions))

    candidates = q.all()

    scored = []
    for track in candidates:
        score = transition_score(from_track, track)
        scored.append((track, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]
