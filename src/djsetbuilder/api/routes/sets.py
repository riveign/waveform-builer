"""Set listing, detail, transition, and cue endpoints."""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from djsetbuilder.api.deps import get_db
from djsetbuilder.api.schemas import (
    CueCreateRequest,
    CueResponse,
    SetDetailResponse,
    SetResponse,
    SetTrackResponse,
    SetWaveformTrackResponse,
    TransitionResponse,
    TransitionScoreBreakdown,
)
from djsetbuilder.db.models import Set, Track, TransitionCue
from djsetbuilder.db.store import delete_cue, get_cues_for_set_track, save_cue

router = APIRouter(prefix="/api/sets", tags=["sets"])


def _set_track_response(st) -> SetTrackResponse:
    t = st.track
    af = t.audio_features if t else None
    return SetTrackResponse(
        position=st.position,
        track_id=st.track_id,
        title=t.title if t else None,
        artist=t.artist if t else None,
        bpm=t.bpm if t else None,
        key=t.key if t else None,
        genre=(t.dir_genre or t.rb_genre) if t else None,
        energy=t.dir_energy if t else None,
        duration_sec=t.duration_sec if t else None,
        transition_score=st.transition_score,
        has_waveform=af is not None and af.waveform_detail is not None,
    )


@router.get("", response_model=list[SetResponse])
def list_sets(
    search: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(Set)
    if search:
        q = q.filter(Set.name.ilike(f"%{search}%"))
    q = q.order_by(Set.created_at.desc()).limit(limit)
    sets = q.all()
    return [
        SetResponse(
            id=s.id,
            name=s.name,
            created_at=s.created_at,
            duration_min=s.duration_min,
            track_count=len(s.tracks),
        )
        for s in sets
    ]


@router.get("/{set_id}", response_model=SetDetailResponse)
def set_detail(set_id: int, db: Session = Depends(get_db)):
    s = db.query(Set).get(set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")
    tracks = sorted(s.tracks, key=lambda st: st.position)
    return SetDetailResponse(
        id=s.id,
        name=s.name,
        created_at=s.created_at,
        duration_min=s.duration_min,
        energy_profile=s.energy_profile,
        genre_filter=s.genre_filter,
        tracks=[_set_track_response(st) for st in tracks],
    )


@router.get("/{set_id}/waveforms", response_model=list[SetWaveformTrackResponse])
def set_waveforms(set_id: int, db: Session = Depends(get_db)):
    """Bulk load waveform overviews for all tracks in a set (for timeline rendering)."""
    s = db.query(Set).get(set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    result = []
    for st in sorted(s.tracks, key=lambda st: st.position):
        t = st.track
        af = t.audio_features if t else None
        wf_b64 = None
        if af and af.waveform_overview:
            wf_b64 = base64.b64encode(af.waveform_overview).decode("ascii")
        result.append(SetWaveformTrackResponse(
            position=st.position,
            track_id=st.track_id,
            title=t.title if t else None,
            artist=t.artist if t else None,
            bpm=t.bpm if t else None,
            key=t.key if t else None,
            genre=(t.dir_genre or t.rb_genre) if t else None,
            energy=t.dir_energy if t else None,
            duration_sec=t.duration_sec if t else None,
            transition_score=st.transition_score,
            waveform_overview=wf_b64,
        ))
    return result


@router.get("/{set_id}/transition/{index}", response_model=TransitionResponse)
def set_transition(set_id: int, index: int, db: Session = Depends(get_db)):
    """Get transition detail between track at `index` and `index+1`."""
    s = db.query(Set).get(set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    tracks = sorted(s.tracks, key=lambda st: st.position)
    if index < 0 or index >= len(tracks) - 1:
        raise HTTPException(status_code=404, detail="Invalid transition index")

    st_a = tracks[index]
    st_b = tracks[index + 1]
    t_a = st_a.track
    t_b = st_b.track

    # Compute score breakdown
    from djsetbuilder.setbuilder.camelot import harmonic_score
    from djsetbuilder.setbuilder.scoring import (
        bpm_compatibility,
        energy_fit,
        genre_coherence,
        track_quality,
    )

    h = harmonic_score(t_a.key, t_b.key)
    e = energy_fit(t_b, 0.5)  # neutral target for display
    b = bpm_compatibility(t_a.bpm, t_b.bpm)
    g = genre_coherence(t_a.dir_genre or t_a.rb_genre, t_b.dir_genre or t_b.rb_genre)
    q = track_quality(t_b)

    from djsetbuilder.config import SCORING_WEIGHTS
    w = SCORING_WEIGHTS
    total = w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b + w["genre_coherence"] * g + w["track_quality"] * q

    af_a = t_a.audio_features
    af_b = t_b.audio_features

    wf_a = base64.b64encode(af_a.waveform_overview).decode("ascii") if af_a and af_a.waveform_overview else None
    wf_b = base64.b64encode(af_b.waveform_overview).decode("ascii") if af_b and af_b.waveform_overview else None

    return TransitionResponse(
        position=index,
        track_a=_set_track_response(st_a),
        track_b=_set_track_response(st_b),
        score_breakdown=TransitionScoreBreakdown(
            harmonic=round(h, 3),
            energy_fit=round(e, 3),
            bpm_compat=round(b, 3),
            genre_coherence=round(g, 3),
            track_quality=round(q, 3),
            total=round(total, 3),
        ),
        bpm_a=t_a.bpm,
        bpm_b=t_b.bpm,
        key_a=t_a.key,
        key_b=t_b.key,
        waveform_a_overview=wf_a,
        waveform_b_overview=wf_b,
    )


@router.get("/{set_id}/tracks/{track_id}/cues", response_model=list[CueResponse])
def list_cues(set_id: int, track_id: int, db: Session = Depends(get_db)):
    cues = get_cues_for_set_track(db, set_id, track_id)
    return [
        CueResponse(
            id=c.id,
            set_id=c.set_id,
            track_id=c.track_id,
            position=c.position,
            name=c.name,
            cue_type=c.cue_type,
            start_sec=c.start_sec,
            end_sec=c.end_sec,
            hot_cue_num=c.hot_cue_num,
            color=c.color,
            created_at=c.created_at,
        )
        for c in cues
    ]


@router.post("/{set_id}/tracks/{track_id}/cues", response_model=CueResponse)
def create_cue(
    set_id: int,
    track_id: int,
    body: CueCreateRequest,
    db: Session = Depends(get_db),
):
    if not db.query(Set).get(set_id):
        raise HTTPException(status_code=404, detail="Set not found")
    if not db.query(Track).get(track_id):
        raise HTTPException(status_code=404, detail="Track not found")

    cue = save_cue(
        db,
        set_id=set_id,
        track_id=track_id,
        position=body.position,
        name=body.name,
        cue_type=body.cue_type,
        start_sec=body.start_sec,
        end_sec=body.end_sec,
        hot_cue_num=body.hot_cue_num,
    )
    return CueResponse(
        id=cue.id,
        set_id=cue.set_id,
        track_id=cue.track_id,
        position=cue.position,
        name=cue.name,
        cue_type=cue.cue_type,
        start_sec=cue.start_sec,
        end_sec=cue.end_sec,
        hot_cue_num=cue.hot_cue_num,
        color=cue.color,
        created_at=cue.created_at,
    )


@router.delete("/cues/{cue_id}")
def remove_cue(cue_id: int, db: Session = Depends(get_db)):
    if not delete_cue(db, cue_id):
        raise HTTPException(status_code=404, detail="Cue not found")
    return {"ok": True}
