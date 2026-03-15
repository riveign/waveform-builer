"""Energy Tinder — swipe-based review of ML energy predictions."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from djsetbuilder.api.deps import get_db
from djsetbuilder.api.schemas import (
    TinderDecideRequest,
    TinderDecideResponse,
    TinderQueueItem,
    TinderQueueResponse,
    TinderRetrainResponse,
    TinderStatsResponse,
    TrackResponse,
)
from djsetbuilder.db.models import Track
from djsetbuilder.db.store import get_tinder_queue, save_tinder_decision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tinder", tags=["tinder"])


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


@router.get("/queue", response_model=TinderQueueResponse)
def tinder_queue(
    genre_family: str | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get paginated queue of unreviewed auto-predicted tracks, ordered by confidence ASC."""
    tracks, total = get_tinder_queue(
        db, genre_family=genre_family, bpm_min=bpm_min, bpm_max=bpm_max,
        limit=limit, offset=offset,
    )
    items = []
    for t in tracks:
        af = t.audio_features
        items.append(TinderQueueItem(
            track=_track_to_response(t),
            energy_predicted=t.energy_predicted,
            energy_confidence=t.energy_confidence,
            mood_happy=af.mood_happy if af else None,
            mood_sad=af.mood_sad if af else None,
            mood_aggressive=af.mood_aggressive if af else None,
            mood_relaxed=af.mood_relaxed if af else None,
            has_waveform=af is not None and af.waveform_detail is not None,
        ))
    return TinderQueueResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("/decide", response_model=TinderDecideResponse)
def tinder_decide(body: TinderDecideRequest, db: Session = Depends(get_db)):
    """Submit a tinder decision (confirm, override, or skip) for a track."""
    if body.decision not in ("confirm", "override", "skip"):
        raise HTTPException(status_code=400, detail="decision must be confirm, override, or skip")
    if body.decision == "override" and not body.override_zone:
        raise HTTPException(status_code=400, detail="override_zone required when decision is override")
    if body.override_zone:
        from djsetbuilder.analysis.autotag import ZONE_MAP
        valid_zones = set(ZONE_MAP.values())
        if body.override_zone not in valid_zones:
            raise HTTPException(
                status_code=400,
                detail=f"override_zone must be one of: {sorted(valid_zones)}",
            )

    track = save_tinder_decision(db, body.track_id, body.decision, body.override_zone)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Teaching moment: on override, explain what features the model relied on
    teaching = None
    if body.decision == "override":
        teaching = _generate_teaching_moment(track, body.override_zone)

    return TinderDecideResponse(
        track_id=body.track_id,
        decision=body.decision,
        applied_zone=body.override_zone if body.decision == "override" else track.energy_predicted,
        teaching_moment=teaching,
    )


@router.get("/stats", response_model=TinderStatsResponse)
def tinder_stats(db: Session = Depends(get_db)):
    """Get review session statistics."""
    from sqlalchemy import func

    # Reviewed = approved tracks
    approved = (
        db.query(Track.energy_predicted, func.count(Track.id))
        .filter(Track.energy_source == "approved")
        .group_by(Track.energy_predicted)
        .all()
    )
    total_reviewed = sum(c for _, c in approved)

    # Remaining in queue
    queue_remaining = (
        db.query(func.count(Track.id))
        .filter(
            Track.energy_predicted.isnot(None),
            Track.energy_source == "auto",
        )
        .scalar()
    ) or 0

    # We track confirmed vs overridden by energy_confidence:
    # overridden tracks have confidence = 1.0 (set by save_tinder_decision)
    # confirmed tracks keep their original confidence < 1.0
    # This is an approximation — for exact counts we'd need a decision log table
    overridden = (
        db.query(func.count(Track.id))
        .filter(
            Track.energy_source == "approved",
            Track.energy_confidence == 1.0,
        )
        .scalar()
    ) or 0
    confirmed = total_reviewed - overridden

    # Skip count is not tracked (skip = no-op), report 0
    skipped = 0

    return TinderStatsResponse(
        total_reviewed=total_reviewed,
        confirmed=confirmed,
        overridden=overridden,
        skipped=skipped,
        queue_remaining=queue_remaining,
        confirmed_pct=round(confirmed / total_reviewed * 100, 1) if total_reviewed else 0,
        overridden_pct=round(overridden / total_reviewed * 100, 1) if total_reviewed else 0,
        skip_pct=0,
    )


@router.post("/retrain", response_model=TinderRetrainResponse)
def tinder_retrain(db: Session = Depends(get_db)):
    """Retrain the energy model with approved predictions included."""
    from djsetbuilder.analysis.autotag import save_model, train_energy_model

    try:
        result = train_energy_model(db, include_approved=True)
        save_model(result)
        return TinderRetrainResponse(
            accuracy=result["metrics"].get("accuracy"),
            class_counts=result["class_counts"],
            feature_importance=result["feature_importance"][:10],
            training_samples=result["training_samples"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Retrain failed")
        raise HTTPException(status_code=500, detail=f"Retrain failed: {e}")


def _generate_teaching_moment(track: Track, override_zone: str | None) -> str | None:
    """Generate a one-sentence teaching moment when the DJ overrides a prediction."""
    from pathlib import Path

    from djsetbuilder.analysis.autotag import META_FILENAME, DEFAULT_MODEL_DIR

    meta_path = DEFAULT_MODEL_DIR / META_FILENAME
    if not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text())
        importance = meta.get("feature_importance", [])
        if not importance:
            return None

        top_feature = importance[0][0] if importance else "unknown"
        # Humanize feature names
        friendly = {
            "energy": "overall energy level",
            "loudness_lufs": "loudness",
            "spectral_centroid": "brightness",
            "spectral_complexity": "spectral complexity",
            "danceability": "danceability",
            "energy_intro": "intro energy",
            "energy_body": "body energy",
            "energy_outro": "outro energy",
            "mood_happy": "happy mood",
            "mood_sad": "sad mood",
            "mood_aggressive": "aggression",
            "mood_relaxed": "relaxed mood",
            "build_shape": "energy build shape",
            "drop_shape": "energy drop shape",
            "intro_body_ratio": "intro-to-body ratio",
            "outro_body_ratio": "outro-to-body ratio",
            "aggression_ratio": "aggression ratio",
        }
        feat_name = friendly.get(top_feature, top_feature)
        original = track.energy_predicted or "unknown"

        return f"The model leaned on {feat_name} to predict {original} — you hear {override_zone}. This teaches it that {feat_name} alone doesn't decide the energy."
    except Exception:
        return None
