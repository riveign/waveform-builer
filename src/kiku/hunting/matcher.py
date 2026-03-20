"""Fuzzy match extracted tracks against the local Kiku library."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from kiku.db.models import Track
from kiku.hunting.parsers.common import normalize_name

logger = logging.getLogger(__name__)

# Minimum fuzzy score to consider a match
MATCH_THRESHOLD = 75


def match_tracks(
    session: Session,
    extracted: list[dict],
) -> list[dict]:
    """Match extracted tracks against the local library using fuzzy string matching.

    Args:
        session: DB session.
        extracted: List of dicts with 'artist' and 'title' keys.

    Returns:
        Same list with added 'matched_track_id', 'match_score', 'acquisition_status' fields.
    """
    try:
        from thefuzz import fuzz
    except ImportError:
        logger.warning("thefuzz not installed — skipping library matching")
        return extracted

    # Load all library tracks (artist, title) for matching
    library = session.query(Track.id, Track.artist, Track.title).filter(
        Track.artist.isnot(None),
        Track.title.isnot(None),
    ).all()

    # Pre-normalize library for speed
    lib_normalized = [
        (t.id, normalize_name(t.artist or ""), normalize_name(t.title or ""))
        for t in library
    ]

    for item in extracted:
        artist_norm = normalize_name(item.get("artist", ""))
        title_norm = normalize_name(item.get("title", ""))

        best_id = None
        best_score = 0.0

        for lib_id, lib_artist, lib_title in lib_normalized:
            # Combined score: weighted average of artist and title match
            artist_score = fuzz.ratio(artist_norm, lib_artist)
            title_score = fuzz.ratio(title_norm, lib_title)
            combined = (artist_score * 0.4 + title_score * 0.6) / 100.0

            if combined > best_score:
                best_score = combined
                best_id = lib_id

        if best_score >= MATCH_THRESHOLD / 100.0:
            item["matched_track_id"] = best_id
            item["match_score"] = round(best_score, 3)
            item["acquisition_status"] = "owned"
        else:
            item["matched_track_id"] = None
            item["match_score"] = round(best_score, 3) if best_score > 0.3 else None
            item["acquisition_status"] = "unowned"

    return extracted
