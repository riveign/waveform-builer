"""MFCC-based acoustic similarity search."""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from djsetbuilder.db.models import AudioFeatures, Track
from djsetbuilder.db.store import get_track_by_title


def _deserialize_mfcc(blob: bytes, dim: int = 13) -> np.ndarray:
    """Deserialize MFCC vector from blob."""
    return np.frombuffer(blob, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def find_similar(
    session: Session,
    query: str,
    n: int = 10,
) -> list[tuple[Track, float]]:
    """Find tracks acoustically similar to the query track.

    Returns list of (Track, similarity_score) sorted by similarity descending.
    """
    target = get_track_by_title(session, query)
    if not target or not target.audio_features or not target.audio_features.mfcc_mean:
        return []

    target_mean = _deserialize_mfcc(target.audio_features.mfcc_mean)
    target_var = _deserialize_mfcc(target.audio_features.mfcc_var)
    # Combined feature vector
    target_vec = np.concatenate([target_mean, target_var])

    # Get all tracks with MFCC data
    candidates = (
        session.query(Track)
        .join(AudioFeatures)
        .filter(
            AudioFeatures.mfcc_mean.isnot(None),
            Track.id != target.id,
        )
        .all()
    )

    scored = []
    for track in candidates:
        af = track.audio_features
        if not af.mfcc_mean:
            continue

        cand_mean = _deserialize_mfcc(af.mfcc_mean)
        cand_var = _deserialize_mfcc(af.mfcc_var)
        cand_vec = np.concatenate([cand_mean, cand_var])

        sim = cosine_similarity(target_vec, cand_vec)
        scored.append((track, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]
