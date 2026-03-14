"""Library statistics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from djsetbuilder.analysis.insights import (
    bpm_histogram,
    camelot_distribution,
    energy_genre_heatmap,
    mood_quadrant,
)
from djsetbuilder.api.deps import get_db
from djsetbuilder.api.schemas import BpmBin, LibraryStatsResponse, MoodPoint
from djsetbuilder.db.store import library_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/library", response_model=LibraryStatsResponse)
def stats_library(db: Session = Depends(get_db)):
    s = library_stats(db)
    return LibraryStatsResponse(**s)


@router.get("/camelot", response_model=dict[str, dict[str, int]])
def stats_camelot(db: Session = Depends(get_db)):
    """Camelot key distribution: position (1-12) -> mode (A/B) -> count."""
    try:
        dist = camelot_distribution(db)
        return {str(k): v for k, v in dist.items()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bpm-histogram", response_model=list[BpmBin])
def stats_bpm_histogram(
    db: Session = Depends(get_db),
    bin_width: float = Query(2.0, ge=0.5, le=20.0),
    bpm_min: float = Query(90.0, ge=0.0),
    bpm_max: float = Query(200.0, le=300.0),
):
    """BPM histogram binned by genre family."""
    try:
        bins = bpm_histogram(db, bin_width=bin_width, bpm_min=bpm_min, bpm_max=bpm_max)
        return [BpmBin(**b) for b in bins]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/energy-genre", response_model=dict[str, dict[str, int]])
def stats_energy_genre(db: Session = Depends(get_db)):
    """Energy level x genre family cross-tabulation for heatmap."""
    try:
        return energy_genre_heatmap(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mood-scatter", response_model=list[MoodPoint])
def stats_mood_scatter(db: Session = Depends(get_db)):
    """Mood scatter data: happy-sad (x) vs aggressive-relaxed (y)."""
    try:
        points = mood_quadrant(db)
        return [MoodPoint(**p) for p in points]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
