"""Query helpers for the DJ library database."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from djsetbuilder.db.models import AudioFeatures, Track, TransitionCue


def get_track_by_title(session: Session, title: str) -> Optional[Track]:
    """Find a track by title (case-insensitive partial match)."""
    return (
        session.query(Track)
        .filter(Track.title.ilike(f"%{title}%"))
        .first()
    )


def search_tracks(
    session: Session,
    title: str | None = None,
    artist: str | None = None,
    genre: str | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    energy: str | None = None,
    *,
    key: str | None = None,
    rating_min: int | None = None,
    limit: int = 50,
) -> list[Track]:
    """Search tracks with multiple filters."""
    q = session.query(Track)
    if title:
        q = q.filter(Track.title.ilike(f"%{title}%"))
    if artist:
        q = q.filter(Track.artist.ilike(f"%{artist}%"))
    if genre:
        q = q.filter(
            (Track.dir_genre.ilike(f"%{genre}%"))
            | (Track.rb_genre.ilike(f"%{genre}%"))
        )
    if bpm_min is not None:
        q = q.filter(Track.bpm >= bpm_min)
    if bpm_max is not None:
        q = q.filter(Track.bpm <= bpm_max)
    if energy:
        q = q.filter(Track.dir_energy.ilike(f"%{energy}%"))
    if key:
        q = q.filter(Track.key.ilike(f"%{key}%"))
    if rating_min is not None:
        q = q.filter(Track.rating >= rating_min)
    return q.limit(limit).all()


def get_tracks_with_features(session: Session) -> list[Track]:
    """Get all tracks that have audio features analyzed."""
    return (
        session.query(Track)
        .join(AudioFeatures)
        .all()
    )


def get_unanalyzed_tracks(session: Session) -> list[Track]:
    """Get tracks that haven't been analyzed yet."""
    return (
        session.query(Track)
        .outerjoin(AudioFeatures)
        .filter(AudioFeatures.track_id.is_(None))
        .all()
    )


def get_partially_analyzed_tracks(session: Session) -> list[Track]:
    """Get tracks that have an audio_features row but are missing core features.

    This catches tracks processed by --waveform-only that still need
    full Essentia/Librosa analysis (energy, danceability, MFCCs).
    """
    return (
        session.query(Track)
        .join(AudioFeatures)
        .filter(AudioFeatures.energy.is_(None))
        .all()
    )


def library_stats(session: Session) -> dict:
    """Compute library statistics for the stats command."""
    total = session.query(func.count(Track.id)).scalar()
    analyzed = (
        session.query(func.count(AudioFeatures.track_id)).scalar()
    )

    # Genre distribution (from directory parsing)
    genre_rows = (
        session.query(Track.dir_genre, func.count(Track.id))
        .filter(Track.dir_genre.isnot(None))
        .group_by(Track.dir_genre)
        .order_by(func.count(Track.id).desc())
        .all()
    )

    # Energy distribution
    energy_rows = (
        session.query(Track.dir_energy, func.count(Track.id))
        .filter(Track.dir_energy.isnot(None))
        .group_by(Track.dir_energy)
        .order_by(func.count(Track.id).desc())
        .all()
    )

    # BPM range
    bpm_min = session.query(func.min(Track.bpm)).filter(Track.bpm > 0).scalar()
    bpm_max = session.query(func.max(Track.bpm)).filter(Track.bpm > 0).scalar()
    bpm_avg = session.query(func.avg(Track.bpm)).filter(Track.bpm > 0).scalar()

    # Key distribution
    key_rows = (
        session.query(Track.key, func.count(Track.id))
        .filter(Track.key.isnot(None))
        .group_by(Track.key)
        .order_by(func.count(Track.id).desc())
        .all()
    )

    # Top artists
    artist_rows = (
        session.query(Track.artist, func.count(Track.id))
        .filter(Track.artist.isnot(None))
        .group_by(Track.artist)
        .order_by(func.count(Track.id).desc())
        .limit(20)
        .all()
    )

    return {
        "total_tracks": total,
        "analyzed_tracks": analyzed,
        "genres": dict(genre_rows),
        "energies": dict(energy_rows),
        "bpm_min": bpm_min,
        "bpm_max": bpm_max,
        "bpm_avg": round(bpm_avg, 1) if bpm_avg else None,
        "keys": dict(key_rows),
        "top_artists": dict(artist_rows),
    }


def get_cues_for_set_track(
    session: Session, set_id: int, track_id: int
) -> list[TransitionCue]:
    """Get all cue points for a specific track within a set."""
    return (
        session.query(TransitionCue)
        .filter(TransitionCue.set_id == set_id, TransitionCue.track_id == track_id)
        .order_by(TransitionCue.start_sec)
        .all()
    )


def save_cue(
    session: Session,
    set_id: int,
    track_id: int,
    position: int,
    name: str,
    cue_type: str,
    start_sec: float,
    end_sec: float | None = None,
    hot_cue_num: int = -1,
) -> TransitionCue:
    """Create a transition cue point."""
    cue = TransitionCue(
        set_id=set_id,
        track_id=track_id,
        position=position,
        name=name,
        cue_type=cue_type,
        start_sec=start_sec,
        end_sec=end_sec,
        hot_cue_num=hot_cue_num,
    )
    session.add(cue)
    session.commit()
    return cue


def delete_cue(session: Session, cue_id: int) -> bool:
    """Delete a cue point by ID."""
    cue = session.query(TransitionCue).get(cue_id)
    if cue:
        session.delete(cue)
        session.commit()
        return True
    return False


def get_set_waveform_data(session: Session, set_id: int) -> list[dict]:
    """Bulk load waveform overviews for all tracks in a set."""
    from djsetbuilder.db.models import Set, SetTrack

    set_ = session.query(Set).get(set_id)
    if not set_:
        return []

    result = []
    for st in sorted(set_.tracks, key=lambda s: s.position):
        track = st.track
        af = track.audio_features
        result.append({
            "position": st.position,
            "track_id": track.id,
            "title": track.title,
            "artist": track.artist,
            "bpm": track.bpm,
            "key": track.key,
            "duration_sec": track.duration_sec,
            "transition_score": st.transition_score,
            "has_waveform": af is not None and af.waveform_overview is not None,
        })
    return result
