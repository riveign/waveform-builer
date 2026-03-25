"""Set listing, detail, transition, cue, and mutation endpoints."""

from __future__ import annotations

import base64
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    CueCreateRequest,
    CueResponse,
    ReplaceTrackRequest,
    ReplacementCandidate,
    ReplacementBreakdown,
    ReplacementContext,
    ReplacementSuggestionsResponse,
    SetAddTrackRequest,
    SetBuildRequest,
    SetCreateRequest,
    SetDetailResponse,
    SetReorderTracksRequest,
    SetResponse,
    SetTrackResponse,
    SetUpdateRequest,
    SetWaveformTrackResponse,
    TrackSummary,
    TransitionResponse,
    TransitionScoreBreakdown,
)
from kiku.db.models import Set, Track, TransitionCue
from kiku.db.store import (
    add_track_to_set,
    delete_cue,
    get_cues_for_set_track,
    reorder_set_tracks,
    remove_track_from_set,
    replace_track_in_set,
    save_cue,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sets", tags=["sets"])


def _set_track_response(st) -> SetTrackResponse:
    t = st.track
    af = t.audio_features if t else None
    conflict = t.energy_conflict if t else None
    conflict_resp = None
    if conflict:
        from kiku.api.schemas import EnergyConflictResponse
        conflict_resp = EnergyConflictResponse(**conflict)
    return SetTrackResponse(
        position=st.position,
        track_id=st.track_id,
        title=t.title if t else None,
        artist=t.artist if t else None,
        bpm=t.bpm if t else None,
        key=t.key if t else None,
        genre=(t.dir_genre or t.rb_genre) if t else None,
        energy=(t.dir_energy or t.energy_predicted) if t else None,
        duration_sec=t.duration_sec if t else None,
        transition_score=st.transition_score,
        has_waveform=af is not None and af.waveform_detail is not None,
        energy_source=t.energy_source if t else None,
        energy_conflict=conflict_resp,
    )


def _sse_event(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@router.post("/build")
def build_set_sse(body: SetBuildRequest, db: Session = Depends(get_db)):
    """Build a DJ set using beam search. Returns SSE stream with progress and result."""
    from kiku.setbuilder.constraints import resolve_energy
    from kiku.setbuilder.planner import build_set

    def generate():
        yield _sse_event("started", json.dumps({
            "name": body.name,
            "total_duration_min": body.duration_min,
            "energy_preset": body.energy_preset,
        }))

        try:
            energy_profile = resolve_energy(body.energy_preset)
            bpm_range = None
            if body.bpm_min is not None and body.bpm_max is not None:
                bpm_range = (body.bpm_min, body.bpm_max)

            seed_title = None
            if body.seed_track_id is not None:
                track = db.get(Track, body.seed_track_id)
                if not track:
                    yield _sse_event("error", json.dumps({"detail": "Seed track not found"}))
                    return
                seed_title = track.title

            # Convert per-request weight overrides if provided
            weights_dict = body.weights.model_dump() if body.weights else None
            if weights_dict:
                from kiku.config import validate_scoring_weights
                validate_scoring_weights(weights_dict)

            result = build_set(
                session=db,
                duration_min=body.duration_min,
                energy_profile=energy_profile,
                genres=body.genre_filter,
                bpm_range=bpm_range,
                seed_title=seed_title,
                beam_width=body.beam_width,
                set_name=body.name,
                prefer_playlists=body.playlist_preference,
                weights=weights_dict,
                discovery_density=body.discovery_density,
            )

            if result is None:
                yield _sse_event("error", json.dumps({"detail": "Could not build set — no matching tracks or seed"}))
                return

            # Emit per-track progress events so the frontend can
            # render tracks incrementally as they "appear".
            ordered_tracks = sorted(result.tracks, key=lambda st: st.position)
            total_tracks = len(ordered_tracks)
            for st in ordered_tracks:
                t = st.track
                yield _sse_event("track_added", json.dumps({
                    "track_id": st.track_id,
                    "title": t.title if t else None,
                    "artist": t.artist if t else None,
                    "position": st.position,
                    "bpm": t.bpm if t else None,
                    "key": t.key if t else None,
                    "energy": t.dir_energy if t else None,
                    "score": round(st.transition_score, 3) if st.transition_score else None,
                    "total_tracks_so_far": st.position,
                    "total_tracks": total_tracks,
                }))
                time.sleep(0.05)

            yield _sse_event("complete", json.dumps({
                "set_id": result.id,
                "name": result.name,
                "track_count": total_tracks,
                "duration_min": result.duration_min,
            }))

        except Exception as exc:
            logger.exception("Set build failed")
            yield _sse_event("error", json.dumps({"detail": str(exc)}))

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("", response_model=SetResponse, status_code=201)
def create_set(body: SetCreateRequest, db: Session = Depends(get_db)):
    """Create an empty set."""
    set_ = Set(
        name=body.name,
        energy_profile=body.energy_profile,
        genre_filter=json.dumps(body.genre_filter) if body.genre_filter else None,
    )
    db.add(set_)
    db.commit()
    db.refresh(set_)
    return SetResponse(
        id=set_.id,
        name=set_.name,
        created_at=set_.created_at,
        duration_min=set_.duration_min,
        track_count=0,
    )


@router.put("/{set_id}", response_model=SetResponse)
def update_set(set_id: int, body: SetUpdateRequest, db: Session = Depends(get_db)):
    """Update set metadata."""
    set_ = db.get(Set, set_id)
    if not set_:
        raise HTTPException(status_code=404, detail="Set not found")
    if body.name is not None:
        set_.name = body.name
    if body.energy_profile is not None:
        set_.energy_profile = body.energy_profile
    if body.genre_filter is not None:
        set_.genre_filter = json.dumps(body.genre_filter)
    db.commit()
    db.refresh(set_)
    return SetResponse(
        id=set_.id,
        name=set_.name,
        created_at=set_.created_at,
        duration_min=set_.duration_min,
        track_count=len(set_.tracks),
    )


@router.delete("/{set_id}", status_code=204)
def delete_set(set_id: int, db: Session = Depends(get_db)):
    """Delete a set and its tracks/cues (cascade)."""
    set_ = db.get(Set, set_id)
    if not set_:
        raise HTTPException(status_code=404, detail="Set not found")
    db.delete(set_)
    db.commit()
    return Response(status_code=204)


@router.post("/{set_id}/tracks", response_model=list[SetTrackResponse])
def add_track(set_id: int, body: SetAddTrackRequest, db: Session = Depends(get_db)):
    """Add a track to a set at a specific position."""
    try:
        tracks = add_track_to_set(db, set_id, body.track_id, body.position)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)
    return [_set_track_response(st) for st in tracks]


@router.delete("/{set_id}/tracks/{track_id}", status_code=204)
def remove_track(set_id: int, track_id: int, db: Session = Depends(get_db)):
    """Remove a track from a set."""
    try:
        removed = remove_track_from_set(db, set_id, track_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not removed:
        raise HTTPException(status_code=404, detail="Track not in set")
    return Response(status_code=204)


@router.put("/{set_id}/tracks/reorder", response_model=list[SetTrackResponse])
def reorder_tracks(
    set_id: int, body: SetReorderTracksRequest, db: Session = Depends(get_db)
):
    """Reorder tracks within a set (for drag-and-drop)."""
    try:
        tracks = reorder_set_tracks(db, set_id, body.track_ids)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)
    return [_set_track_response(st) for st in tracks]


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
    s = db.get(Set, set_id)
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
    s = db.get(Set, set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    result = []
    for st in sorted(s.tracks, key=lambda st: st.position):
        t = st.track
        af = t.audio_features if t else None
        wf_b64 = None
        if af and af.waveform_overview:
            wf_b64 = base64.b64encode(af.waveform_overview).decode("ascii")
        conflict = t.energy_conflict if t else None
        conflict_resp = None
        if conflict:
            from kiku.api.schemas import EnergyConflictResponse
            conflict_resp = EnergyConflictResponse(**conflict)
        result.append(SetWaveformTrackResponse(
            position=st.position,
            track_id=st.track_id,
            title=t.title if t else None,
            artist=t.artist if t else None,
            bpm=t.bpm if t else None,
            key=t.key if t else None,
            genre=(t.dir_genre or t.rb_genre) if t else None,
            energy=(t.dir_energy or t.energy_predicted) if t else None,
            duration_sec=t.duration_sec if t else None,
            transition_score=st.transition_score,
            waveform_overview=wf_b64,
            energy_source=t.energy_source if t else None,
            energy_conflict=conflict_resp,
        ))
    return result


@router.get("/{set_id}/transition/{index}", response_model=TransitionResponse)
def set_transition(
    set_id: int,
    index: int,
    discovery_density: float = 0.0,
    db: Session = Depends(get_db),
):
    """Get transition detail between track at `index` and `index+1`."""
    s = db.get(Set, set_id)
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
    from kiku.setbuilder.camelot import harmonic_score
    from kiku.setbuilder.scoring import (
        bpm_compatibility,
        energy_fit,
        genre_coherence,
        track_quality,
    )

    h = harmonic_score(t_a.key, t_b.key)
    e = energy_fit(t_b, 0.5)  # neutral target for display
    b = bpm_compatibility(t_a.bpm, t_b.bpm)
    g = genre_coherence(t_a.dir_genre or t_a.rb_genre, t_b.dir_genre or t_b.rb_genre)
    q, label = track_quality(t_b, discovery_density=discovery_density)

    from kiku.config import SCORING_WEIGHTS as w
    total = w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b + w["genre_coherence"] * g + w["track_quality"] * q

    af_a = t_a.audio_features
    af_b = t_b.audio_features

    wf_a = base64.b64encode(af_a.waveform_overview).decode("ascii") if af_a and af_a.waveform_overview else None
    wf_b = base64.b64encode(af_b.waveform_overview).decode("ascii") if af_b and af_b.waveform_overview else None
    bt_a = base64.b64encode(af_a.beat_positions).decode("ascii") if af_a and af_a.beat_positions else None
    bt_b = base64.b64encode(af_b.beat_positions).decode("ascii") if af_b and af_b.beat_positions else None

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
            discovery_label=label,
            set_appearances=None,
        ),
        bpm_a=t_a.bpm,
        bpm_b=t_b.bpm,
        key_a=t_a.key,
        key_b=t_b.key,
        waveform_a_overview=wf_a,
        waveform_b_overview=wf_b,
        beats_a=bt_a,
        beats_b=bt_b,
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
    if not db.get(Set, set_id):
        raise HTTPException(status_code=404, detail="Set not found")
    if not db.get(Track, track_id):
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


# ── Replace Track endpoints ──


def _track_summary(t: Track) -> TrackSummary:
    return TrackSummary(
        track_id=t.id,
        title=t.title,
        artist=t.artist,
        bpm=t.bpm,
        key=t.key,
        genre=t.dir_genre or t.rb_genre,
    )


def _track_response(t: Track):
    """Build a TrackResponse from a Track model."""
    from kiku.api.schemas import EnergyConflictResponse, TrackResponse

    af = t.audio_features
    resolved_zone, source, confidence = t.resolved_energy_zone
    conflict = t.energy_conflict
    conflict_resp = None
    if conflict:
        conflict_resp = EnergyConflictResponse(**conflict)
    return TrackResponse(
        id=t.id,
        title=t.title,
        artist=t.artist,
        album=t.album,
        bpm=t.bpm,
        key=t.key,
        rating=t.rating,
        genre=t.dir_genre or t.rb_genre,
        energy=t.dir_energy or t.energy_predicted,
        duration_sec=t.duration_sec,
        play_count=t.play_count,
        kiku_play_count=t.kiku_play_count,
        has_waveform=af is not None and af.waveform_overview is not None,
        has_features=af is not None,
        resolved_energy=resolved_zone,
        energy_source=source,
        energy_confidence=confidence,
        energy_conflict=conflict_resp,
    )


@router.get("/{set_id}/tracks/{position}/replacements", response_model=ReplacementSuggestionsResponse)
def get_replacements(
    set_id: int,
    position: int,
    n: int = 10,
    genre_filter: str | None = None,
    discovery_density: float = 0.0,
    db: Session = Depends(get_db),
):
    """Find replacement candidates for the track at a given position.

    Scores candidates against both neighbors (prev and next track).
    """
    from sqlalchemy import or_

    from kiku.config import BPM_TOLERANCE
    from kiku.setbuilder.scoring import score_replacement

    s = db.get(Set, set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    ordered = sorted(s.tracks, key=lambda st: st.position)
    if position < 0 or position >= len(ordered):
        raise HTTPException(status_code=404, detail="Invalid position")

    current_st = ordered[position]
    current_track = current_st.track
    prev_track = ordered[position - 1].track if position > 0 else None
    next_track = ordered[position + 1].track if position < len(ordered) - 1 else None

    # Compute energy target at this position from set's energy_profile
    energy_target = 0.5
    if s.energy_profile:
        try:
            from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string
            try:
                profile = parse_energy_json(s.energy_profile)
            except (json.JSONDecodeError, KeyError):
                profile = parse_energy_string(s.energy_profile)
            # Estimate elapsed time based on position
            total_tracks = len(ordered)
            total_dur = s.duration_min or 120
            elapsed = (position / max(total_tracks - 1, 1)) * total_dur
            energy_target = profile.target_energy_at(elapsed)
        except Exception:
            pass

    # Collect existing track IDs to exclude
    set_track_ids = {st.track_id for st in ordered}

    # BPM pre-filter: use the average BPM of neighbors for filtering
    ref_bpms = [t.bpm for t in [prev_track, next_track] if t and t.bpm and t.bpm > 0]
    ref_bpm = sum(ref_bpms) / len(ref_bpms) if ref_bpms else (current_track.bpm or 0)

    q = db.query(Track).filter(Track.id.notin_(set_track_ids))
    if ref_bpm and ref_bpm > 0:
        bpm_lo = ref_bpm * (1 - BPM_TOLERANCE * 2)
        bpm_hi = ref_bpm * (1 + BPM_TOLERANCE * 2)
        q = q.filter(Track.bpm.between(bpm_lo, bpm_hi))

    if genre_filter:
        genres = [g.strip() for g in genre_filter.split(",")]
        genre_conditions = [Track.dir_genre.ilike(f"%{g}%") for g in genres]
        q = q.filter(or_(*genre_conditions))

    candidates = q.all()

    # Score each candidate
    scored = []
    for cand in candidates:
        combined, incoming, outgoing = score_replacement(
            cand, prev_track, next_track, target_energy=energy_target,
            discovery_density=discovery_density,
        )
        scored.append((cand, combined, incoming, outgoing))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:n]

    # Build response
    result_candidates = []
    for cand, combined, incoming, outgoing in top:
        result_candidates.append(ReplacementCandidate(
            track=_track_response(cand),
            combined_score=combined,
            incoming_breakdown=ReplacementBreakdown(**incoming) if incoming else None,
            outgoing_breakdown=ReplacementBreakdown(**outgoing) if outgoing else None,
        ))

    context = ReplacementContext(
        prev_track=_track_summary(prev_track) if prev_track else None,
        next_track=_track_summary(next_track) if next_track else None,
        energy_target=round(energy_target, 3),
        position=position,
    )

    return ReplacementSuggestionsResponse(context=context, candidates=result_candidates)


@router.post("/{set_id}/tracks/{position}/replace", response_model=list[SetTrackResponse])
def replace_track(
    set_id: int,
    position: int,
    body: ReplaceTrackRequest,
    db: Session = Depends(get_db),
):
    """Replace the track at a given position with a new track."""
    try:
        tracks = replace_track_in_set(db, set_id, position, body.new_track_id)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)
    return [_set_track_response(st) for st in tracks]
