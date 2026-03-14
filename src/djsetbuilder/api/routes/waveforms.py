"""Waveform data endpoints — pre-computed peaks as base64 float32."""

from __future__ import annotations

import base64

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from djsetbuilder.api.deps import get_db
from djsetbuilder.api.schemas import (
    WaveformBandsResponse,
    WaveformDetailResponse,
    WaveformResponse,
)
from djsetbuilder.db.models import Track

router = APIRouter(prefix="/api/waveforms", tags=["waveforms"])


def _blob_to_b64(blob: bytes | None) -> str | None:
    if blob is None:
        return None
    return base64.b64encode(blob).decode("ascii")


def _get_track_with_waveform(track_id: int, db: Session) -> Track:
    track = db.query(Track).get(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    af = track.audio_features
    if not af or af.waveform_overview is None:
        raise HTTPException(status_code=404, detail="No waveform data for this track")
    return track


@router.get("/{track_id}/overview", response_model=WaveformResponse)
def waveform_overview(track_id: int, db: Session = Depends(get_db)):
    track = _get_track_with_waveform(track_id, db)
    af = track.audio_features
    return WaveformResponse(
        envelope=_blob_to_b64(af.waveform_overview),
        sr=af.waveform_sr or 22050,
        hop=af.waveform_hop or 512,
        duration_sec=track.duration_sec or 0,
    )


@router.get("/{track_id}/detail", response_model=WaveformDetailResponse)
def waveform_detail(track_id: int, db: Session = Depends(get_db)):
    track = _get_track_with_waveform(track_id, db)
    af = track.audio_features
    if af.waveform_detail is None:
        raise HTTPException(status_code=404, detail="No detail waveform data")
    return WaveformDetailResponse(
        envelope=_blob_to_b64(af.waveform_detail),
        beats=_blob_to_b64(af.beat_positions),
        sr=af.waveform_sr or 22050,
        hop=af.waveform_hop or 512,
        duration_sec=track.duration_sec or 0,
    )


@router.get("/{track_id}/bands", response_model=WaveformBandsResponse)
def waveform_bands(track_id: int, db: Session = Depends(get_db)):
    track = _get_track_with_waveform(track_id, db)
    af = track.audio_features
    if af.band_low is None:
        raise HTTPException(status_code=404, detail="No frequency band data")
    return WaveformBandsResponse(
        low=_blob_to_b64(af.band_low),
        midlow=_blob_to_b64(af.band_midlow),
        midhigh=_blob_to_b64(af.band_midhigh),
        high=_blob_to_b64(af.band_high),
        sr=af.waveform_sr or 22050,
        hop=af.waveform_hop or 512,
        duration_sec=track.duration_sec or 0,
    )
