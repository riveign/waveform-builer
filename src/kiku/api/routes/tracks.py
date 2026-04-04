"""Track search, detail, and suggest-next endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    PaginatedTracksResponse,
    SuggestNextItem,
    SuggestNextResponse,
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
    """Extract embedded artwork from a track's audio file."""
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    if not track.file_path:
        raise HTTPException(status_code=404, detail="No file path for this track")

    from kiku.db.paths import normalize_path

    file_path = normalize_path(track.file_path)

    import os

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    try:
        import mutagen

        audio = mutagen.File(file_path)
        if audio is None:
            raise HTTPException(status_code=404, detail="Could not read audio file")

        image_data: bytes | None = None
        mime_type = "image/jpeg"

        # ID3 (MP3, AIFF)
        if hasattr(audio, "tags") and audio.tags:
            for key in audio.tags:
                if key.startswith("APIC"):
                    apic = audio.tags[key]
                    image_data = apic.data
                    mime_type = apic.mime or "image/jpeg"
                    break

        # MP4/M4A
        if image_data is None and hasattr(audio, "tags") and audio.tags and "covr" in audio.tags:
            covers = audio.tags["covr"]
            if covers:
                image_data = bytes(covers[0])
                mime_type = "image/jpeg"

        # FLAC
        if image_data is None and hasattr(audio, "pictures"):
            pics = audio.pictures
            if pics:
                image_data = pics[0].data
                mime_type = pics[0].mime or "image/jpeg"

        if not image_data:
            raise HTTPException(status_code=404, detail="No embedded artwork")

        return Response(
            content=image_data,
            media_type=mime_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to extract artwork")


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
    scored = score_transitions(db, track, n=n, genre_filter=genres, weights=weights_dict, exclude_ids=exclude_ids, discovery_density=discovery_density)

    w = weights_dict if weights_dict else SCORING_WEIGHTS
    suggestions = []
    for cand, total_score in scored:
        h = harmonic_score(track.key, cand.key)
        e = energy_fit(cand, 0.5)
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
        ml_genre=af.ml_genre,
        ml_genre_confidence=af.ml_genre_confidence,
        energy_intro=af.energy_intro,
        energy_body=af.energy_body,
        energy_outro=af.energy_outro,
        verified_bpm=af.verified_bpm,
        verified_key=af.verified_key,
    )
