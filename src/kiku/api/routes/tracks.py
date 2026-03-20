"""Track search, detail, and suggest-next endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    PaginatedTracksResponse,
    SuggestNextItem,
    SuggestNextResponse,
    TrackFeaturesResponse,
    TrackResponse,
    TransitionScoreBreakdown,
)
from kiku.db.models import Track
from kiku.db.store import autocomplete_artists, autocomplete_labels, search_tracks

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


def _track_to_response(t: Track) -> TrackResponse:
    af = t.audio_features
    resolved_zone, source, confidence = t.resolved_energy_zone
    conflict = t.energy_conflict
    conflict_resp = None
    if conflict:
        from kiku.api.schemas import EnergyConflictResponse
        conflict_resp = EnergyConflictResponse(**conflict)
    return TrackResponse(
        id=t.id,
        title=t.title,
        artist=t.artist,
        album=t.album,
        label=t.label,
        bpm=t.bpm,
        key=t.key,
        rating=t.rating,
        genre=t.dir_genre or t.rb_genre,
        energy=t.dir_energy,
        duration_sec=t.duration_sec,
        play_count=t.play_count,
        has_waveform=af is not None and af.waveform_detail is not None,
        has_features=af is not None and af.energy is not None,
        resolved_energy=resolved_zone,
        energy_source=source,
        energy_confidence=confidence,
        energy_conflict=conflict_resp,
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
    scored = score_transitions(db, track, n=n, genre_filter=genres, weights=weights_dict, exclude_ids=exclude_ids)

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
        q = track_quality(cand)

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
