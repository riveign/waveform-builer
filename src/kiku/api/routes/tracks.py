"""Track search, detail, and suggest-next endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    AffinityListItem,
    PaginatedTracksResponse,
    SuggestNextItem,
    SuggestNextResponse,
    TrackAffinitiesResponse,
    TrackAffinityRequest,
    TrackAffinityResponse,
    TrackFeaturesResponse,
    TrackRatingRequest,
    TrackResponse,
    TrackSetAppearance,
    TransitionScoreBreakdown,
)
from kiku.db.models import Track
from kiku.db.store import autocomplete_artists, autocomplete_labels, search_tracks

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


def _track_to_response(t: Track) -> TrackResponse:
    import json as _json

    from kiku.energy import get_track_energy
    from kiku.setbuilder.scoring import genre_to_family

    af = t.audio_features
    te = get_track_energy(t)
    conflict = t.energy_conflict
    conflict_resp = None
    if conflict:
        from kiku.api.schemas import EnergyConflictResponse
        conflict_resp = EnergyConflictResponse(**conflict)

    # Parse playlist_tags JSON
    tags: list[str] = []
    if t.playlist_tags:
        try:
            tags = _json.loads(t.playlist_tags)
        except (ValueError, TypeError):
            pass

    genre = t.dir_genre or t.rb_genre
    family = genre_to_family(genre).capitalize() if genre else None

    return TrackResponse(
        id=t.id,
        title=t.title,
        artist=t.artist,
        album=t.album,
        label=t.label,
        bpm=t.bpm,
        key=t.key,
        rating=t.rating,
        genre=genre,
        energy=t.dir_energy,
        duration_sec=t.duration_sec,
        play_count=t.play_count,
        kiku_play_count=t.kiku_play_count,
        has_waveform=af is not None and af.waveform_detail is not None,
        has_features=af is not None and af.energy is not None,
        resolved_energy=te.zone,
        energy_source=te.source,
        energy_confidence=te.confidence,
        energy_value=te.numeric,
        energy_label=te.label,
        energy_conflict=conflict_resp,
        date_added=t.date_added,
        release_year=t.release_year,
        track_number=t.track_number,
        disc_number=t.disc_number,
        comment=t.comment,
        playlist_tags=tags,
        genre_family=family,
    )


@router.get("/search", response_model=PaginatedTracksResponse)
def track_search(
    search: str | None = None,
    title: str | None = None,
    artist: list[str] | None = Query(None),
    genre: list[str] | None = Query(None),
    key: list[str] | None = Query(None),
    label: list[str] | None = Query(None),
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    energy: str | None = None,
    energy_zone: str | None = None,
    rating_min: int | None = None,
    plays_min: int | None = None,
    plays_max: int | None = None,
    sort: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    tracks, total = search_tracks(
        db,
        search=search,
        title=title,
        artist=artist,
        genre=genre,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        energy=energy,
        energy_zone=energy_zone,
        key=key,
        label=label,
        rating_min=rating_min,
        plays_min=plays_min,
        plays_max=plays_max,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return PaginatedTracksResponse(
        items=[_track_to_response(t) for t in tracks],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/autocomplete/artists", response_model=list[str])
def artists_autocomplete(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return autocomplete_artists(db, q, limit=limit)


@router.get("/autocomplete/labels", response_model=list[str])
def labels_autocomplete(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return autocomplete_labels(db, q, limit=limit)


@router.get("/{track_id}", response_model=TrackResponse)
def track_detail(track_id: int, db: Session = Depends(get_db)):
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return _track_to_response(track)


@router.patch("/{track_id}/rating", response_model=TrackResponse)
def update_track_rating(
    track_id: int,
    body: TrackRatingRequest,
    db: Session = Depends(get_db),
) -> TrackResponse:
    """Update a track's star rating (0 clears, 1-5 sets)."""
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    track.rating = body.rating if body.rating > 0 else None
    track.rating_source = "kiku"
    db.commit()
    db.refresh(track)
    return _track_to_response(track)


@router.post("/{track_id}/played", status_code=204)
def record_played(track_id: int, db: Session = Depends(get_db)):
    """Increment kiku_play_count when a track has been listened to for >60s in the player."""
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    track.kiku_play_count = (track.kiku_play_count or 0) + 1
    db.commit()
    return


@router.get("/{track_id}/artwork")
def track_artwork(track_id: int, db: Session = Depends(get_db)):
    """Serve a track's artwork: its own embedded art, else its album's cover.

    Never 500s — embedded extraction soft-fails to None, and a track with no
    embedded art inherits the album cover via the resolver (so the Tracks table
    and Now Playing bar fill in too). A clean 404 is the only failure the client
    sees; the frontend hides the <img> on 404.
    """
    import os

    from fastapi.responses import FileResponse

    from kiku.artwork.resolver import embedded_cover_bytes, resolve_album_cover
    from kiku.db.paths import normalize_path

    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # 1. Embedded artwork on the file itself (soft-fail, never raises).
    if track.file_path:
        file_path = normalize_path(track.file_path)
        if os.path.isfile(file_path):
            emb = embedded_cover_bytes(file_path)
            if emb:
                content, mime = emb
                return Response(
                    content=content,
                    media_type=mime,
                    headers={"Cache-Control": "public, max-age=3600"},
                )

    # 2. Inherit the album cover (resolver: cache → CAA → iTunes → Deezer).
    if track.album:
        from kiku.metadata.album_key import album_key, resolve_album_artist

        artist, _ = resolve_album_artist(db, track.album)
        result = resolve_album_cover(db, album_key(track.album, artist))
        if result is not None:
            path, _source = result
            return FileResponse(
                path,
                media_type=_image_media_type(path.suffix),
                headers={"Cache-Control": "public, max-age=86400"},
            )

    raise HTTPException(status_code=404, detail="No artwork available")


def _image_media_type(suffix: str) -> str:
    return "image/png" if suffix.lower().lstrip(".") == "png" else "image/jpeg"


@router.get("/{track_id}/sets", response_model=list[TrackSetAppearance])
def track_sets(track_id: int, db: Session = Depends(get_db)):
    """Return all sets that contain this track."""
    from kiku.db.models import Set, SetTrack as SetTrackModel

    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    rows = (
        db.query(SetTrackModel, Set)
        .join(Set, SetTrackModel.set_id == Set.id)
        .filter(SetTrackModel.track_id == track_id)
        .order_by(Set.created_at.desc())
        .all()
    )

    return [
        TrackSetAppearance(
            set_id=s.id,
            set_name=s.name,
            position=st.position,
            created_at=s.created_at,
        )
        for st, s in rows
    ]


@router.get("/{track_id}/suggest-next", response_model=SuggestNextResponse)
def suggest_next(
    track_id: int,
    n: int = Query(default=10, ge=1, le=50),
    set_id: int | None = Query(default=None, description="Exclude tracks already in this set"),
    genre_filter: str | None = Query(default=None, description="Comma-separated genre filter"),
    w_harmonic: float | None = Query(default=None, description="Harmonic weight override"),
    w_energy_fit: float | None = Query(default=None, description="Energy fit weight override"),
    w_bpm_compat: float | None = Query(default=None, description="BPM compatibility weight override"),
    w_genre_coherence: float | None = Query(default=None, description="Genre coherence weight override"),
    w_track_quality: float | None = Query(default=None, description="Track quality weight override"),
    discovery_density: float = Query(default=0.0, ge=-1.0, le=1.0, description="Discovery/density bias (-1=fresh, +1=proven)"),
    position_min: float | None = Query(default=None, description="Elapsed minutes at this position in the set"),
    energy_profile: str | None = Query(default=None, description="Energy profile string for position-aware energy target"),
    db: Session = Depends(get_db),
):
    """Suggest best next tracks based on transition scoring."""
    from kiku.config import SCORING_WEIGHTS, validate_scoring_weights
    from kiku.db.models import SetTrack
    from kiku.setbuilder.camelot import harmonic_score
    from kiku.setbuilder.scoring import (
        bpm_compatibility,
        energy_fit,
        genre_coherence,
        score_transitions,
        track_quality,
    )

    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Collect track IDs to exclude (tracks already in the set)
    exclude_ids: list[int] | None = None
    if set_id is not None:
        exclude_ids = [
            row.track_id
            for row in db.query(SetTrack.track_id).filter(SetTrack.set_id == set_id).all()
        ]

    # Build per-request weights if any overrides provided
    weight_overrides = {
        "harmonic": w_harmonic,
        "energy_fit": w_energy_fit,
        "bpm_compat": w_bpm_compat,
        "genre_coherence": w_genre_coherence,
        "track_quality": w_track_quality,
    }
    weights_dict = None
    if any(v is not None for v in weight_overrides.values()):
        weights_dict = {k: (v if v is not None else SCORING_WEIGHTS[k]) for k, v in weight_overrides.items()}
        try:
            validate_scoring_weights(weights_dict)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    genres = [g.strip() for g in genre_filter.split(",")] if genre_filter else None

    # Compute position-aware energy target
    target_energy = 0.5  # default neutral
    if position_min is not None and energy_profile:
        from kiku.setbuilder.constraints import parse_energy_string

        try:
            ep = parse_energy_string(energy_profile)
            target_energy = ep.target_energy_at(position_min)
        except Exception:
            pass  # Fall back to neutral

    scored = score_transitions(db, track, n=n, genre_filter=genres, weights=weights_dict, exclude_ids=exclude_ids, discovery_density=discovery_density, target_energy=target_energy)

    w = weights_dict if weights_dict else SCORING_WEIGHTS
    suggestions = []
    for cand, total_score in scored:
        h = harmonic_score(track.key, cand.key)
        e = energy_fit(cand, target_energy)
        b = bpm_compatibility(track.bpm, cand.bpm)
        g = genre_coherence(
            track.dir_genre or track.rb_genre,
            cand.dir_genre or cand.rb_genre,
        )
        q, label = track_quality(cand, discovery_density=discovery_density)

        suggestions.append(SuggestNextItem(
            track=_track_to_response(cand),
            score=round(total_score, 3),
            breakdown=TransitionScoreBreakdown(
                harmonic=round(h, 3),
                energy_fit=round(e, 3),
                bpm_compat=round(b, 3),
                genre_coherence=round(g, 3),
                track_quality=round(q, 3),
                total=round(total_score, 3),
                discovery_label=label,
                set_appearances=None,
            ),
        ))

    return SuggestNextResponse(source_track_id=track_id, suggestions=suggestions)


@router.get("/{track_id}/features", response_model=TrackFeaturesResponse)
def track_features(track_id: int, db: Session = Depends(get_db)):
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    af = track.audio_features
    if not af or af.energy is None:
        raise HTTPException(status_code=404, detail="No audio features for this track")
    return TrackFeaturesResponse(
        track_id=af.track_id,
        energy=af.energy,
        danceability=af.danceability,
        loudness_lufs=af.loudness_lufs,
        spectral_centroid=af.spectral_centroid,
        spectral_complexity=af.spectral_complexity,
        mood_happy=af.mood_happy,
        mood_sad=af.mood_sad,
        mood_aggressive=af.mood_aggressive,
        mood_relaxed=af.mood_relaxed,
        vibe_brightness=af.vibe_brightness,
        vibe_density=af.vibe_density,
        ml_genre=af.ml_genre,
        ml_genre_confidence=af.ml_genre_confidence,
        energy_intro=af.energy_intro,
        energy_body=af.energy_body,
        energy_outro=af.energy_outro,
        verified_bpm=af.verified_bpm,
        verified_key=af.verified_key,
    )


# ── Track Affinity endpoints ──────────────────────────────────────────


def _canonical_pair(id_a: int, id_b: int) -> tuple[int, int]:
    """Return (smaller, larger) for canonical storage ordering."""
    return (min(id_a, id_b), max(id_a, id_b))


@router.post("/{track_id}/affinity", response_model=TrackAffinityResponse)
def set_affinity(
    track_id: int,
    body: TrackAffinityRequest,
    db: Session = Depends(get_db),
):
    """Mark two tracks as 'good' or 'bad' together. Upserts if pair exists."""
    from kiku.db.models import TrackAffinity

    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    other = db.get(Track, body.other_track_id)
    if not other:
        raise HTTPException(status_code=404, detail="Other track not found")

    if track_id == body.other_track_id:
        raise HTTPException(status_code=422, detail="Cannot create affinity between a track and itself")

    a_id, b_id = _canonical_pair(track_id, body.other_track_id)

    existing = (
        db.query(TrackAffinity)
        .filter(TrackAffinity.track_a_id == a_id, TrackAffinity.track_b_id == b_id)
        .first()
    )

    if existing:
        existing.affinity = body.affinity
        db.commit()
        db.refresh(existing)
        return TrackAffinityResponse(
            id=existing.id,
            track_a_id=existing.track_a_id,
            track_b_id=existing.track_b_id,
            affinity=existing.affinity,
        )

    new = TrackAffinity(track_a_id=a_id, track_b_id=b_id, affinity=body.affinity)
    db.add(new)
    db.commit()
    db.refresh(new)
    return TrackAffinityResponse(
        id=new.id,
        track_a_id=new.track_a_id,
        track_b_id=new.track_b_id,
        affinity=new.affinity,
    )


@router.delete("/{track_id}/affinity/{other_id}", status_code=204)
def delete_affinity(
    track_id: int,
    other_id: int,
    db: Session = Depends(get_db),
):
    """Remove affinity between two tracks."""
    from kiku.db.models import TrackAffinity

    a_id, b_id = _canonical_pair(track_id, other_id)

    row = (
        db.query(TrackAffinity)
        .filter(TrackAffinity.track_a_id == a_id, TrackAffinity.track_b_id == b_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Affinity not found for this pair")

    db.delete(row)
    db.commit()


@router.get("/{track_id}/affinities", response_model=TrackAffinitiesResponse)
def list_affinities(
    track_id: int,
    db: Session = Depends(get_db),
):
    """Return all affinities for a track, with full TrackResponse for each partner."""
    from sqlalchemy import or_

    from kiku.db.models import TrackAffinity

    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    rows = (
        db.query(TrackAffinity)
        .filter(
            or_(
                TrackAffinity.track_a_id == track_id,
                TrackAffinity.track_b_id == track_id,
            )
        )
        .all()
    )

    items = []
    for row in rows:
        partner_id = row.track_b_id if row.track_a_id == track_id else row.track_a_id
        partner = db.get(Track, partner_id)
        if partner:
            items.append(
                AffinityListItem(
                    track_id=partner_id,
                    affinity=row.affinity,
                    track=_track_to_response(partner),
                )
            )

    return TrackAffinitiesResponse(affinities=items)
