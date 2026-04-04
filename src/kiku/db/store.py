"""Query helpers for the DJ library database."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from kiku.db.models import AudioFeatures, Track, TransitionCue


def get_track_by_title(session: Session, title: str) -> Optional[Track]:
    """Find a track by title (case-insensitive partial match)."""
    return (
        session.query(Track)
        .filter(Track.title.ilike(f"%{title}%"))
        .first()
    )


def autocomplete_artists(session: Session, q: str, limit: int = 20) -> list[str]:
    """Return distinct artist names matching a prefix/substring."""
    rows = (
        session.query(Track.artist)
        .filter(Track.artist.isnot(None), Track.artist.ilike(f"%{q}%"))
        .distinct()
        .order_by(Track.artist)
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows]


def autocomplete_labels(session: Session, q: str, limit: int = 20) -> list[str]:
    """Return distinct label names matching a prefix/substring."""
    rows = (
        session.query(Track.label)
        .filter(Track.label.isnot(None), Track.label != "", Track.label.ilike(f"%{q}%"))
        .distinct()
        .order_by(Track.label)
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows]


def search_tracks(
    session: Session,
    title: str | None = None,
    artist: str | list[str] | None = None,
    genre: str | list[str] | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    energy: str | None = None,
    *,
    energy_zone: str | None = None,
    key: str | list[str] | None = None,
    label: str | list[str] | None = None,
    rating_min: int | None = None,
    plays_min: int | None = None,
    plays_max: int | None = None,
    sort: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Track], int]:
    """Search tracks with multiple filters.

    Returns (tracks, total_count) to support pagination.
    genre/key/artist/label accept a single string or list of strings (OR-matched).
    sort: "recent" | "plays" (desc) | "plays_asc" (asc).
    search: free-text OR-match across title, artist, and label.
    plays_min/plays_max: filter by combined play count (Rekordbox + Kiku).
    """
    q = session.query(Track)
    if search:
        pattern = f"%{search}%"
        q = q.filter(or_(
            Track.title.ilike(pattern),
            Track.artist.ilike(pattern),
            Track.label.ilike(pattern),
        ))
    if title:
        q = q.filter(Track.title.ilike(f"%{title}%"))
    if artist:
        artists = [artist] if isinstance(artist, str) else artist
        artist_conditions = [Track.artist.ilike(f"%{a}%") for a in artists]
        q = q.filter(or_(*artist_conditions))
    if label:
        labels = [label] if isinstance(label, str) else label
        label_conditions = [Track.label.ilike(f"%{lb}%") for lb in labels]
        q = q.filter(or_(*label_conditions))
    if genre:
        genres = [genre] if isinstance(genre, str) else genre
        genre_conditions = []
        for g in genres:
            genre_conditions.append(Track.dir_genre.ilike(f"%{g}%"))
            genre_conditions.append(Track.rb_genre.ilike(f"%{g}%"))
        q = q.filter(or_(*genre_conditions))
    if bpm_min is not None:
        q = q.filter(Track.bpm >= bpm_min)
    if bpm_max is not None:
        q = q.filter(Track.bpm <= bpm_max)
    if energy:
        q = q.filter(Track.dir_energy.ilike(f"%{energy}%"))
    if energy_zone:
        # Match tracks whose resolved energy maps to this zone:
        # dir_energy tags that map to the zone, OR energy_predicted = zone
        from kiku.analysis.autotag import ZONE_MAP
        matching_tags = [tag for tag, z in ZONE_MAP.items() if z == energy_zone.lower()]
        conditions = [Track.dir_energy.ilike(tag) for tag in matching_tags]
        conditions.append(Track.energy_predicted == energy_zone.lower())
        q = q.filter(or_(*conditions))
    if key:
        keys = [key] if isinstance(key, str) else key
        key_conditions = [Track.key.ilike(f"%{k}%") for k in keys]
        q = q.filter(or_(*key_conditions))
    if rating_min is not None:
        q = q.filter(Track.rating >= rating_min)
    if plays_min is not None:
        combined = func.coalesce(Track.play_count, 0) + func.coalesce(Track.kiku_play_count, 0)
        q = q.filter(combined >= plays_min)
    if plays_max is not None:
        combined = func.coalesce(Track.play_count, 0) + func.coalesce(Track.kiku_play_count, 0)
        q = q.filter(combined <= plays_max)
    if sort == "recent":
        q = q.order_by(func.coalesce(Track.date_added, Track.last_synced).desc())
    elif sort == "plays":
        combined = func.coalesce(Track.play_count, 0) + func.coalesce(Track.kiku_play_count, 0)
        q = q.order_by(combined.desc())
    elif sort == "plays_asc":
        combined = func.coalesce(Track.play_count, 0) + func.coalesce(Track.kiku_play_count, 0)
        q = q.order_by(combined.asc())
    total = q.count()
    tracks = q.offset(offset).limit(limit).all()
    return tracks, total


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

    # Energy distribution — uses resolved zones from all sources
    from kiku.energy import get_track_energy
    from collections import Counter
    all_tracks = session.query(Track).all()
    zone_counts: Counter[str] = Counter()
    for t in all_tracks:
        te = get_track_energy(t)
        if te.zone:
            zone_counts[te.zone] += 1
    energy_rows = sorted(zone_counts.items(), key=lambda x: -x[1])

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
    cue = session.get(TransitionCue, cue_id)
    if cue:
        session.delete(cue)
        session.commit()
        return True
    return False


def add_track_to_set(
    session: Session, set_id: int, track_id: int, position: int | None = None
) -> list:
    """Add a track to a set at a given position (or at the end).

    Returns the updated list of SetTrack objects sorted by position.
    """
    from kiku.db.models import Set, SetTrack

    set_ = session.get(Set, set_id)
    if not set_:
        raise ValueError("Set not found")

    track = session.get(Track, track_id)
    if not track:
        raise ValueError("Track not found")

    existing = sorted(set_.tracks, key=lambda st: st.position)

    if position is None:
        position = len(existing)

    # Clamp position to valid range
    position = max(0, min(position, len(existing)))

    # Shift positions of tracks at or after the insertion point.
    # Iterate in reverse order (highest position first) to avoid
    # hitting the UNIQUE constraint on (set_id, position).
    for st in reversed(existing):
        if st.position >= position:
            st.position = st.position + 1
            session.flush()

    new_st = SetTrack(set_id=set_id, position=position, track_id=track_id)
    session.add(new_st)
    session.commit()
    session.refresh(set_)

    return sorted(set_.tracks, key=lambda st: st.position)


def remove_track_from_set(session: Session, set_id: int, track_id: int) -> bool:
    """Remove a track from a set and recompact positions.

    Returns True if removed, False if not found.
    """
    from kiku.db.models import Set, SetTrack

    set_ = session.get(Set, set_id)
    if not set_:
        raise ValueError("Set not found")

    # Find the SetTrack entry for this track
    target = None
    for st in set_.tracks:
        if st.track_id == track_id:
            target = st
            break

    if target is None:
        return False

    removed_pos = target.position
    session.delete(target)
    session.flush()

    # Recompact: shift down tracks that were after the removed one
    remaining = [st for st in set_.tracks if st.track_id != track_id]
    for st in remaining:
        if st.position > removed_pos:
            st.position = st.position - 1

    session.commit()
    return True


def reorder_set_tracks(
    session: Session, set_id: int, track_ids: list[int]
) -> list:
    """Reorder tracks in a set to match the given track_ids order.

    Returns the updated list of SetTrack objects sorted by position.
    Raises ValueError if track_ids don't match the set's tracks.
    """
    from kiku.db.models import Set, SetTrack

    set_ = session.get(Set, set_id)
    if not set_:
        raise ValueError("Set not found")

    existing = {st.track_id: st for st in set_.tracks}
    existing_ids = set(existing.keys())
    provided_ids = set(track_ids)

    if existing_ids != provided_ids:
        missing = existing_ids - provided_ids
        extra = provided_ids - existing_ids
        parts = []
        if missing:
            parts.append(f"missing: {sorted(missing)}")
        if extra:
            parts.append(f"unknown: {sorted(extra)}")
        raise ValueError(f"track_ids mismatch: {', '.join(parts)}")

    if len(track_ids) != len(set(track_ids)):
        raise ValueError("Duplicate track IDs in reorder list")

    # Delete all existing SetTrack rows and recreate with new positions
    for st in list(set_.tracks):
        session.delete(st)
    session.flush()

    for pos, tid in enumerate(track_ids):
        new_st = SetTrack(
            set_id=set_id,
            position=pos,
            track_id=tid,
            transition_score=existing[tid].transition_score,
        )
        session.add(new_st)

    session.commit()
    session.refresh(set_)

    return sorted(set_.tracks, key=lambda st: st.position)


def replace_track_in_set(
    session: Session, set_id: int, position: int, new_track_id: int
) -> list:
    """Replace the track at a given position with a new track.

    Returns the updated list of SetTrack objects sorted by position.
    Raises ValueError if set, position, or track not found.
    """
    from kiku.db.models import Set, SetTrack

    set_ = session.get(Set, set_id)
    if not set_:
        raise ValueError("Set not found")

    track = session.get(Track, new_track_id)
    if not track:
        raise ValueError("Track not found")

    target = None
    for st in set_.tracks:
        if st.position == position:
            target = st
            break

    if target is None:
        raise ValueError(f"No track at position {position}")

    target.track_id = new_track_id
    target.transition_score = None  # will be recomputed by frontend/caller
    session.commit()
    session.refresh(set_)

    return sorted(set_.tracks, key=lambda st: st.position)


def get_set_waveform_data(session: Session, set_id: int) -> list[dict]:
    """Bulk load waveform overviews for all tracks in a set."""
    from kiku.db.models import Set, SetTrack

    set_ = session.get(Set, set_id)
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


def get_tinder_queue(
    session: Session,
    genre_family: str | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    include_conflicts: bool = False,
    track_ids: list[int] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Track], int]:
    """Get unreviewed auto-predicted tracks ordered by confidence ASC.

    When include_conflicts=True, also includes tracks where dir_energy and
    energy_predicted map to different zones (regardless of energy_source).

    Returns (tracks, total_count) for pagination.
    """
    if track_ids is not None:
        # Set-scoped review: include any track that isn't approved yet
        # (auto-predicted, no prediction, or conflicts)
        q = session.query(Track).filter(
            Track.id.in_(track_ids),
            or_(
                Track.energy_source == "auto",
                Track.energy_source.is_(None),
            ),
        )
    elif include_conflicts:
        # Include auto-predicted AND conflict tracks
        from kiku.analysis.autotag import ZONE_MAP
        q = session.query(Track).filter(
            Track.energy_predicted.isnot(None),
            or_(
                Track.energy_source == "auto",
                # Tracks with both dir_energy and predicted set (potential conflicts)
                Track.dir_energy.isnot(None),
            ),
        )
    else:
        q = session.query(Track).filter(
            Track.energy_predicted.isnot(None),
            Track.energy_source == "auto",
        )
    if genre_family:
        from kiku.setbuilder.scoring import GENRE_FAMILIES
        genres = GENRE_FAMILIES.get(genre_family.lower(), [])
        if genres:
            conditions = [Track.dir_genre.ilike(f"%{g}%") for g in genres]
            q = q.filter(or_(*conditions))
    if bpm_min is not None:
        q = q.filter(Track.bpm >= bpm_min)
    if bpm_max is not None:
        q = q.filter(Track.bpm <= bpm_max)
    q = q.order_by(Track.energy_confidence.asc())
    total = q.count()
    tracks = q.offset(offset).limit(limit).all()
    return tracks, total


def save_tinder_decision(
    session: Session,
    track_id: int,
    decision: str,
    override_zone: str | None = None,
) -> Track | None:
    """Apply a tinder decision to a track.

    - confirm: set energy_source = "approved"
    - override: set energy_source = "approved", energy_predicted = override_zone, energy_confidence = 1.0
    - skip: no-op (leave as "auto")

    Returns updated Track or None if not found.
    """
    track = session.get(Track, track_id)
    if not track:
        return None
    if decision == "confirm":
        track.energy_source = "approved"
    elif decision == "override":
        track.energy_source = "approved"
        track.energy_predicted = override_zone
        track.energy_confidence = 1.0
    # skip: do nothing
    session.commit()
    return track


# ── Hunt session CRUD ─────────────────────────────────────────────────


def create_hunt_session(
    session: Session, url: str, platform: str, title: str | None = None,
    uploader: str | None = None,
) -> "HuntSession":
    """Create a new hunt session."""
    from kiku.db.models import HuntSession

    hunt = HuntSession(url=url, platform=platform, title=title, uploader=uploader)
    session.add(hunt)
    session.flush()
    return hunt


def get_hunt_session(session: Session, hunt_id: int) -> "HuntSession | None":
    """Get a hunt session by ID with tracks eagerly loaded."""
    from kiku.db.models import HuntSession

    return session.query(HuntSession).filter_by(id=hunt_id).first()


def list_hunt_sessions(session: Session, limit: int = 20, offset: int = 0) -> tuple[list, int]:
    """List hunt sessions ordered by creation date desc."""
    from sqlalchemy import func

    from kiku.db.models import HuntSession

    total = session.query(func.count(HuntSession.id)).scalar() or 0
    hunts = (
        session.query(HuntSession)
        .order_by(HuntSession.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return hunts, total


def save_hunt_tracks(
    session: Session, hunt_id: int, tracks: list[dict],
) -> list:
    """Save extracted tracks to a hunt session."""
    import json

    from kiku.db.models import HuntSession, HuntTrack

    hunt = session.query(HuntSession).filter_by(id=hunt_id).first()
    if not hunt:
        return []

    results = []
    for t in tracks:
        ht = HuntTrack(
            session_id=hunt_id,
            position=t.get("position", 0),
            raw_text=t.get("raw_text"),
            artist=t.get("artist"),
            title=t.get("title"),
            remix_info=t.get("remix_info"),
            original_artist=t.get("original_artist"),
            original_title=t.get("original_title"),
            confidence=t.get("confidence", 0.0),
            source=t.get("source"),
            timestamp_sec=t.get("timestamp_sec"),
            matched_track_id=t.get("matched_track_id"),
            match_score=t.get("match_score"),
            acquisition_status=t.get("acquisition_status", "unowned"),
            purchase_links=json.dumps(t.get("purchase_links", {})),
        )
        session.add(ht)
        results.append(ht)

    hunt.track_count = len(tracks)
    hunt.owned_count = sum(1 for t in tracks if t.get("acquisition_status") == "owned")
    hunt.status = "complete"
    session.flush()
    return results


def update_hunt_track_status(
    session: Session, hunt_track_id: int, status: str,
) -> "HuntTrack | None":
    """Update acquisition status of a hunt track (e.g. 'wanted', 'owned')."""
    from kiku.db.models import HuntTrack

    ht = session.query(HuntTrack).filter_by(id=hunt_track_id).first()
    if ht:
        ht.acquisition_status = status
        session.flush()
    return ht


# ── OAuth token CRUD ─────────────────────────────────────────────────


def save_oauth_token(
    session: Session, provider: str, access_token: str,
    refresh_token: str | None = None, expires_at: str | None = None,
    user_id: str | None = None, username: str | None = None,
    avatar_url: str | None = None,
) -> "OAuthToken":
    """Create or update an OAuth token for a provider."""
    from kiku.db.models import OAuthToken

    token = session.query(OAuthToken).filter_by(provider=provider).first()
    if token:
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = expires_at
        token.user_id = user_id
        token.username = username
        token.avatar_url = avatar_url
    else:
        token = OAuthToken(
            provider=provider, access_token=access_token,
            refresh_token=refresh_token, expires_at=expires_at,
            user_id=user_id, username=username, avatar_url=avatar_url,
        )
        session.add(token)
    session.flush()
    return token


def get_oauth_token(session: Session, provider: str) -> "OAuthToken | None":
    """Get stored OAuth token for a provider."""
    from kiku.db.models import OAuthToken

    return session.query(OAuthToken).filter_by(provider=provider).first()


def delete_oauth_token(session: Session, provider: str) -> bool:
    """Remove stored OAuth token. Returns True if deleted."""
    from kiku.db.models import OAuthToken

    token = session.query(OAuthToken).filter_by(provider=provider).first()
    if token:
        session.delete(token)
        session.flush()
        return True
    return False


def update_oauth_token(
    session: Session, provider: str,
    access_token: str, refresh_token: str | None = None,
    expires_at: str | None = None,
) -> "OAuthToken | None":
    """Update just the token fields (used after refresh)."""
    from kiku.db.models import OAuthToken

    token = session.query(OAuthToken).filter_by(provider=provider).first()
    if token:
        token.access_token = access_token
        if refresh_token:
            token.refresh_token = refresh_token
        if expires_at:
            token.expires_at = expires_at
        session.flush()
    return token
