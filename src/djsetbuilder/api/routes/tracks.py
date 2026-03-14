"""Track search and detail endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from djsetbuilder.api.deps import get_db
from djsetbuilder.api.schemas import TrackFeaturesResponse, TrackResponse
from djsetbuilder.db.models import Track
from djsetbuilder.db.store import search_tracks

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


def _track_to_response(t: Track) -> TrackResponse:
    af = t.audio_features
    return TrackResponse(
        id=t.id,
        title=t.title,
        artist=t.artist,
        album=t.album,
        bpm=t.bpm,
        key=t.key,
        rating=t.rating,
        genre=t.dir_genre or t.rb_genre,
        energy=t.dir_energy,
        duration_sec=t.duration_sec,
        play_count=t.play_count,
        has_waveform=af is not None and af.waveform_detail is not None,
        has_features=af is not None and af.energy is not None,
    )


@router.get("/search", response_model=list[TrackResponse])
def track_search(
    title: str | None = None,
    artist: str | None = None,
    genre: str | None = None,
    key: str | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    energy: str | None = None,
    rating_min: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    tracks = search_tracks(
        db,
        title=title,
        artist=artist,
        genre=genre,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        energy=energy,
        key=key,
        rating_min=rating_min,
        limit=limit,
    )
    return [_track_to_response(t) for t in tracks]


@router.get("/{track_id}", response_model=TrackResponse)
def track_detail(track_id: int, db: Session = Depends(get_db)):
    track = db.query(Track).get(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return _track_to_response(track)


@router.get("/{track_id}/features", response_model=TrackFeaturesResponse)
def track_features(track_id: int, db: Session = Depends(get_db)):
    track = db.query(Track).get(track_id)
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
