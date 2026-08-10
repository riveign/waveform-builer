"""Set listing, detail, transition, cue, and mutation endpoints."""

from __future__ import annotations

import base64
import json
import logging
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    ArtistPickItem,
    ArtistPicksResponse,
    CueCreateRequest,
    CueResponse,
    ImportResultResponse,
    OrderChangeResponse,
    PlannedSetCandidate,
    ReplacementBreakdown,
    ReplacementCandidate,
    ReplacementContext,
    ReplacementSuggestionsResponse,
    ReplaceTrackRequest,
    ScoreSequenceRequest,
    ScoreSequenceResponse,
    SetAddTrackRequest,
    SetAnalysisResponse,
    SetBuildRequest,
    SetComparisonResponse,
    SetCreateRequest,
    SetDetailResponse,
    SetFillRequest,
    SetLinkRequest,
    SetOptimizeOrderRequest,
    SetOptimizeOrderResponse,
    SetReorderTracksRequest,
    SetResponse,
    SetTrackResponse,
    SetUpdateRequest,
    SetWaveformTrackResponse,
    SlotSuggestionItem,
    SlotSuggestionsResponse,
    TrackSummary,
    TransitionResponse,
    TransitionScoreBreakdown,
    UnmatchedTrack,
)
from kiku.db.models import Set, Track
from kiku.db.store import (
    add_track_to_set,
    delete_cue,
    get_cues_for_set_track,
    remove_track_from_set,
    reorder_set_tracks,
    replace_track_in_set,
    save_cue,
)
from kiku.services import sets as sets_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sets", tags=["sets"])


def _set_track_response(st) -> SetTrackResponse:
    from kiku.energy import get_track_energy

    t = st.track
    af = t.audio_features if t else None
    conflict = t.energy_conflict if t else None
    conflict_resp = None
    if conflict:
        from kiku.api.schemas import EnergyConflictResponse

        conflict_resp = EnergyConflictResponse(**conflict)

    te = get_track_energy(t) if t else None
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
        resolved_energy=te.zone if te else None,
        energy_source=te.source if te else None,
        energy_confidence=te.confidence if te else None,
        energy_value=te.numeric if te else None,
        energy_label=te.label if te else None,
        energy_conflict=conflict_resp,
    )


def _sse_event(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@router.post("/import/m3u8", response_model=ImportResultResponse)
async def import_m3u8_playlist(
    file: UploadFile | None = File(None),
    file_path: str | None = Form(None),
    name: str | None = Form(None),
    force: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Import a Rekordbox M3U8 playlist as a new set.

    Accepts either a file upload (multipart) or a file_path (form field).
    Matches tracks to the library — never creates new track rows.
    """
    from kiku.import_playlist.m3u8 import parse_m3u8
    from kiku.import_playlist.service import import_playlist

    # Get content from upload or file path
    if file is not None:
        raw = await file.read()
        content = raw.decode("utf-8-sig")
        source_path = file.filename or "upload.m3u8"
    elif file_path:
        from pathlib import Path

        p = Path(file_path)
        if not p.exists():
            raise HTTPException(status_code=400, detail=f"File not found: {file_path}")
        content = p.read_text(encoding="utf-8-sig")
        source_path = file_path
    else:
        raise HTTPException(status_code=400, detail="Provide a file upload or file_path")

    # Validate it looks like M3U8
    if not content.strip().startswith("#EXTM3U") and not any(
        line.strip().startswith("#EXTINF:") for line in content.splitlines()[:20]
    ):
        raise HTTPException(
            status_code=400,
            detail="This doesn't look like an M3U8 file — check the file format",
        )

    parse_result = parse_m3u8(content, source_path=source_path)

    if not parse_result.tracks:
        raise HTTPException(status_code=400, detail="No tracks found in the playlist file")

    result = import_playlist(db, parse_result, name=name, force=force)

    # Duplicate set detected (not forced)
    if result.duplicate_set_id is not None:
        return ImportResultResponse(
            set_id=result.duplicate_set_id,
            name=result.name,
            source=result.source,
            total_tracks=result.total_tracks,
            matched_count=0,
            unmatched_count=0,
            unmatched_paths=[],
            match_methods={},
            warnings=[
                f"Already imported as set {result.duplicate_set_id}. Use force=true to re-import."
            ],
            duplicate_set_id=result.duplicate_set_id,
        )

    # Zero matches
    if result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="None of the tracks matched your library. Check path aliases or sync from Rekordbox first.",
        )

    return ImportResultResponse(
        set_id=result.set_id,
        name=result.name,
        source=result.source,
        total_tracks=result.total_tracks,
        matched_count=result.matched_count,
        unmatched_count=result.unmatched_count,
        unmatched_paths=[UnmatchedTrack(**u) for u in result.unmatched],
        match_methods=result.match_methods,
        warnings=result.warnings,
        planned_candidates=[PlannedSetCandidate(**c) for c in result.planned_candidates],
    )


@router.post("/{set_id}/analyze", response_model=SetAnalysisResponse)
def analyze_set_endpoint(set_id: int, db: Session = Depends(get_db)):
    """Trigger full analysis on a set: score transitions, compute arc, generate teaching moments."""
    try:
        return sets_service.analyze(db, set_id)
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{set_id}/analysis", response_model=SetAnalysisResponse)
def get_set_analysis(set_id: int, db: Session = Depends(get_db)):
    """Get cached analysis for a set. Returns 404 if not yet analyzed."""
    try:
        return sets_service.cached_analysis(db, set_id)
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Played vs Planned (link + compare) ──


@router.put("/{set_id}/link")
def link_set(set_id: int, body: SetLinkRequest, db: Session = Depends(get_db)):
    """Link a played (imported) set to the planned Kiku set it was based on."""
    try:
        sets_service.link_to_plan(db, set_id, body.planned_set_id)
    except sets_service.SetInvalid as e:
        raise HTTPException(status_code=400, detail=str(e))
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"set_id": set_id, "planned_set_id": body.planned_set_id}


@router.delete("/{set_id}/link", status_code=204)
def unlink_set(set_id: int, db: Session = Depends(get_db)):
    """Remove the planned-set link. Linking is optional and reversible."""
    try:
        sets_service.unlink_from_plan(db, set_id)
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(status_code=204)


@router.post("/{set_id}/compare", response_model=SetComparisonResponse)
def compare_set_endpoint(set_id: int, db: Session = Depends(get_db)):
    """Compare a played set against its linked plan. Computes and caches the deviation report."""
    try:
        return sets_service.compare(db, set_id)
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{set_id}/comparison", response_model=SetComparisonResponse)
def get_set_comparison(set_id: int, db: Session = Depends(get_db)):
    """Get the cached played-vs-planned comparison. 404 if not compared yet."""
    try:
        return sets_service.cached_comparison(db, set_id)
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/build")
def build_set_sse(body: SetBuildRequest, db: Session = Depends(get_db)):
    """Build a DJ set using beam search. Returns SSE stream with progress and result."""
    from kiku.setbuilder.constraints import resolve_energy
    from kiku.setbuilder.planner import build_set

    def generate():
        yield _sse_event(
            "started",
            json.dumps(
                {
                    "name": body.name,
                    "total_duration_min": body.duration_min,
                    "energy_preset": body.energy_preset,
                }
            ),
        )

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

            end_title = None
            if body.end_track_id is not None:
                end_track = db.get(Track, body.end_track_id)
                if not end_track:
                    yield _sse_event("error", json.dumps({"detail": "Ending track not found"}))
                    return
                end_title = end_track.title

            # Resolve the optional vibe preset to a (brightness, density) target
            from kiku.vibe import resolve_preset

            preset_vibe = resolve_preset(body.vibe_preset)
            if body.vibe_preset and preset_vibe is None:
                yield _sse_event(
                    "error", json.dumps({"detail": f"Unknown vibe '{body.vibe_preset}'"})
                )
                return

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
                end_title=end_title,
                preset_vibe=preset_vibe,
                vibe_intensity=body.vibe_intensity,
                preferred_artists=body.preferred_artists,
                artist_intensity=body.artist_intensity,
            )

            if result is None:
                yield _sse_event(
                    "error",
                    json.dumps({"detail": "Could not build set — no matching tracks or seed"}),
                )
                return

            # Emit per-track progress events so the frontend can
            # render tracks incrementally as they "appear".
            from kiku.energy import get_track_energy

            ordered_tracks = sorted(result.tracks, key=lambda st: st.position)
            total_tracks = len(ordered_tracks)
            from kiku.vibe import resolve_vibe

            for st in ordered_tracks:
                t = st.track
                te = get_track_energy(t) if t else None
                tv = resolve_vibe(t) if t else None
                yield _sse_event(
                    "track_added",
                    json.dumps(
                        {
                            "track_id": st.track_id,
                            "title": t.title if t else None,
                            "artist": t.artist if t else None,
                            "position": st.position,
                            "bpm": t.bpm if t else None,
                            "key": t.key if t else None,
                            "energy": t.dir_energy if t else None,
                            "resolved_energy": te.zone if te else None,
                            "energy_value": te.numeric if te else None,
                            "energy_source": te.source if te else None,
                            "vibe_brightness": round(tv.brightness, 3) if tv else None,
                            "vibe_density": round(tv.density, 3) if tv else None,
                            "vibe_label": tv.label if tv else None,
                            "score": round(st.transition_score, 3) if st.transition_score else None,
                            "total_tracks_so_far": st.position,
                            "total_tracks": total_tracks,
                        }
                    ),
                )
                time.sleep(0.05)

            yield _sse_event(
                "complete",
                json.dumps(
                    {
                        "set_id": result.id,
                        "name": result.name,
                        "track_count": total_tracks,
                        "duration_min": result.duration_min,
                    }
                ),
            )

            # Auto-analyze the freshly built set
            try:
                from dataclasses import asdict

                from kiku.analysis.set_analyzer import analyze_set as _analyze_set

                analysis_result = _analyze_set(db, result.id)
                analysis_data = asdict(analysis_result)
                analysis_data["arc"]["bpm_range"] = list(analysis_data["arc"]["bpm_range"])
                yield _sse_event("analyzed", json.dumps(analysis_data))
            except Exception as analyze_exc:
                logger.warning("Auto-analysis after build failed: %s", analyze_exc)

        except Exception as exc:
            logger.exception("Set build failed")
            yield _sse_event("error", json.dumps({"detail": str(exc)}))

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/vibe-presets")
def get_vibe_presets():
    """List the vibe presets a DJ can build toward, with their vibe coordinates."""
    from kiku.vibe import VIBE_PRESETS, vibe_label

    return {
        "presets": [
            {
                "name": name,
                "brightness": brightness,
                "density": density,
                "label": vibe_label(brightness, density),
            }
            for name, (brightness, density) in VIBE_PRESETS.items()
        ]
    }


@router.post("", response_model=SetResponse, status_code=201)
def create_set(body: SetCreateRequest, db: Session = Depends(get_db)):
    """Create an empty set."""
    set_ = sets_service.create(
        db,
        name=body.name,
        energy_profile=body.energy_profile,
        genre_filter=body.genre_filter,
        source=body.source,
    )
    return SetResponse(
        id=set_.id,
        name=set_.name,
        created_at=set_.created_at,
        duration_min=set_.duration_min,
        track_count=0,
        source=set_.source,
    )


@router.put("/{set_id}", response_model=SetResponse)
def update_set(set_id: int, body: SetUpdateRequest, db: Session = Depends(get_db)):
    """Update set metadata."""
    try:
        set_ = sets_service.update(
            db,
            set_id,
            name=body.name,
            energy_profile=body.energy_profile,
            genre_filter=body.genre_filter,
        )
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SetResponse(
        id=set_.id,
        name=set_.name,
        created_at=set_.created_at,
        duration_min=set_.duration_min,
        track_count=len(set_.tracks),
        source=set_.source,
    )


@router.delete("/{set_id}", status_code=204)
def delete_set(set_id: int, db: Session = Depends(get_db)):
    """Soft-delete a set — move it to the trash, recoverable for a few days."""
    try:
        sets_service.soft_delete(db, set_id)
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(status_code=204)


@router.post("/{set_id}/restore", response_model=SetResponse)
def restore_set(set_id: int, db: Session = Depends(get_db)):
    """Recover a soft-deleted set from the trash."""
    try:
        set_ = sets_service.restore(db, set_id)
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SetResponse(
        id=set_.id,
        name=set_.name,
        created_at=set_.created_at,
        duration_min=set_.duration_min,
        track_count=len(set_.tracks),
        source=set_.source,
    )


@router.post("/{set_id}/tracks", response_model=list[SetTrackResponse])
def add_track(set_id: int, body: SetAddTrackRequest, db: Session = Depends(get_db)):
    """Add a track to a set at a specific position."""
    try:
        add_track_to_set(db, set_id, body.track_id, body.position)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)

    # Compute transition_score for the newly added track and its neighbor
    from kiku.setbuilder.scoring import transition_score as compute_transition

    set_ = db.get(Set, set_id)
    sorted_tracks = sorted(set_.tracks, key=lambda st: st.position)
    new_st = next((st for st in sorted_tracks if st.track_id == body.track_id), None)
    if new_st and new_st.track:
        idx = sorted_tracks.index(new_st)
        if idx > 0:
            prev_st = sorted_tracks[idx - 1]
            if prev_st.track:
                new_st.transition_score = round(compute_transition(prev_st.track, new_st.track), 3)
        if idx < len(sorted_tracks) - 1:
            next_st = sorted_tracks[idx + 1]
            if next_st.track:
                next_st.transition_score = round(compute_transition(new_st.track, next_st.track), 3)

    # Recompute duration_min
    total_sec = sum(st.track.duration_sec or 0 for st in sorted_tracks if st.track)
    set_.duration_min = round(total_sec / 60)

    # Invalidate analysis cache
    sets_service.invalidate_analysis(db, set_)

    db.commit()
    db.refresh(set_)
    tracks = sorted(set_.tracks, key=lambda st: st.position)
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

    # Recompute duration_min and invalidate analysis
    set_ = db.get(Set, set_id)
    if set_:
        sorted_tracks = sorted(set_.tracks, key=lambda st: st.position)
        total_sec = sum(st.track.duration_sec or 0 for st in sorted_tracks if st.track)
        set_.duration_min = round(total_sec / 60) if sorted_tracks else None
        # Recompute transition_score for the track that now follows the gap
        from kiku.setbuilder.scoring import transition_score as compute_transition

        for i, st in enumerate(sorted_tracks):
            if i > 0 and sorted_tracks[i - 1].track and st.track:
                st.transition_score = round(
                    compute_transition(sorted_tracks[i - 1].track, st.track), 3
                )
            elif i == 0:
                st.transition_score = None
        sets_service.invalidate_analysis(db, set_)
        db.commit()
    return Response(status_code=204)


@router.put("/{set_id}/tracks/reorder", response_model=list[SetTrackResponse])
def reorder_tracks(set_id: int, body: SetReorderTracksRequest, db: Session = Depends(get_db)):
    """Reorder tracks within a set (for drag-and-drop)."""
    try:
        tracks = reorder_set_tracks(db, set_id, body.track_ids)
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)

    # Invalidate analysis cache
    set_ = db.get(Set, set_id)
    if set_:
        sets_service.invalidate_analysis(db, set_)
        db.commit()

    return [_set_track_response(st) for st in tracks]


@router.post("/{set_id}/fill")
def fill_set_sse(set_id: int, body: SetFillRequest, db: Session = Depends(get_db)):
    """Fill gaps in a set via SSE streaming."""
    from kiku.setbuilder.constraints import parse_energy_string
    from kiku.setbuilder.filler import fill_set

    energy_profile = None
    if body.energy_profile:
        try:
            energy_profile = parse_energy_string(body.energy_profile)
        except Exception:
            pass

    weights_dict = None
    if body.weights:
        weights_dict = {
            "harmonic": body.weights.harmonic,
            "energy_fit": body.weights.energy_fit,
            "bpm_compat": body.weights.bpm_compat,
            "genre_coherence": body.weights.genre_coherence,
            "track_quality": body.weights.track_quality,
        }

    def generate():
        for event in fill_set(
            db,
            set_id,
            energy_profile=energy_profile,
            target_duration_min=body.target_duration_min,
            max_fill_tracks=body.max_fill_tracks,
            genre_filter=body.genre_filter,
            gap_threshold=body.gap_threshold,
            discovery_density=body.discovery_density,
            weights=weights_dict,
        ):
            yield f"event: {event.event}\ndata: {json.dumps(event.data)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{set_id}/optimize-order", response_model=SetOptimizeOrderResponse)
def optimize_order(set_id: int, body: SetOptimizeOrderRequest, db: Session = Depends(get_db)):
    """Propose an optimized track order for the set."""
    from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string
    from kiku.setbuilder.reorder import (
        get_energy_curve,
        optimize_full,
        optimize_gentle,
        score_full_sequence,
    )

    set_ = db.get(Set, set_id)
    if not set_:
        raise HTTPException(status_code=404, detail="Set not found")

    set_tracks = sorted(set_.tracks, key=lambda st: st.position)
    tracks = [st.track for st in set_tracks if st.track]
    if len(tracks) < 3:
        raise HTTPException(status_code=400, detail="Need at least 3 tracks to optimize order")

    energy_profile = None
    ep_str = body.energy_profile or set_.energy_profile
    if ep_str:
        try:
            energy_profile = parse_energy_json(ep_str)
        except Exception:
            try:
                energy_profile = parse_energy_string(ep_str)
            except Exception:
                pass

    weights_dict = None
    if body.weights:
        weights_dict = {
            "harmonic": body.weights.harmonic,
            "energy_fit": body.weights.energy_fit,
            "bpm_compat": body.weights.bpm_compat,
            "genre_coherence": body.weights.genre_coherence,
            "track_quality": body.weights.track_quality,
        }

    current_score = score_full_sequence(tracks, energy_profile, weights_dict)
    current_curve = get_energy_curve(tracks, energy_profile)

    if body.strategy == "full":
        proposed, changes = optimize_full(tracks, energy_profile, weights_dict)
    else:
        proposed, changes = optimize_gentle(tracks, energy_profile, weights_dict)

    proposed_score = score_full_sequence(proposed, energy_profile, weights_dict)
    proposed_curve = get_energy_curve(proposed, energy_profile)

    return SetOptimizeOrderResponse(
        current_score=round(current_score, 3),
        proposed_score=round(proposed_score, 3),
        proposed_order=[t.id for t in proposed],
        changes=[
            OrderChangeResponse(
                track_id=c.track_id,
                track_title=c.track_title,
                from_position=c.from_position,
                to_position=c.to_position,
                explanation=c.explanation,
            )
            for c in changes
        ],
        current_energy_curve=[round(v, 3) for v in current_curve],
        proposed_energy_curve=[round(v, 3) for v in proposed_curve],
    )


@router.post("/{set_id}/score-sequence", response_model=ScoreSequenceResponse)
def score_sequence(set_id: int, body: ScoreSequenceRequest, db: Session = Depends(get_db)):
    """Score a proposed track order without saving."""
    from kiku.setbuilder.constraints import parse_energy_string
    from kiku.setbuilder.reorder import get_energy_curve, score_full_sequence

    tracks = [db.get(Track, tid) for tid in body.track_ids]
    tracks = [t for t in tracks if t is not None]
    if len(tracks) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 tracks to score")

    energy_profile = None
    if body.energy_profile:
        try:
            energy_profile = parse_energy_string(body.energy_profile)
        except Exception:
            pass

    weights_dict = None
    if body.weights:
        weights_dict = {
            "harmonic": body.weights.harmonic,
            "energy_fit": body.weights.energy_fit,
            "bpm_compat": body.weights.bpm_compat,
            "genre_coherence": body.weights.genre_coherence,
            "track_quality": body.weights.track_quality,
        }

    total = score_full_sequence(tracks, energy_profile, weights_dict)
    curve = get_energy_curve(tracks, energy_profile)

    return ScoreSequenceResponse(
        total_score=round(total, 3),
        energy_curve=[round(v, 3) for v in curve],
    )


@router.get("", response_model=list[SetResponse])
def list_sets(
    search: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    sets = sets_service.list_active(db, search=search, limit=limit)
    return [
        SetResponse(
            id=s.id,
            name=s.name,
            created_at=s.created_at,
            duration_min=s.duration_min,
            track_count=len(s.tracks),
            source=s.source,
        )
        for s in sets
    ]


@router.get("/deleted", response_model=list[SetResponse])
def list_deleted_sets(db: Session = Depends(get_db)):
    """List soft-deleted sets (the trash), most recently deleted first."""
    sets = sets_service.list_trashed(db)
    return [
        SetResponse(
            id=s.id,
            name=s.name,
            created_at=s.created_at,
            duration_min=s.duration_min,
            track_count=len(s.tracks),
            source=s.source,
            deleted_at=s.deleted_at,
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
        source=s.source,
        planned_set_id=s.planned_set_id,
        tracks=[_set_track_response(st) for st in tracks],
    )


@router.get("/{set_id}/waveforms", response_model=list[SetWaveformTrackResponse])
def set_waveforms(set_id: int, db: Session = Depends(get_db)):
    """Bulk load waveform overviews for all tracks in a set (for timeline rendering)."""
    s = db.get(Set, set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    from kiku.energy import get_track_energy

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
        te = get_track_energy(t) if t else None
        result.append(
            SetWaveformTrackResponse(
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
                resolved_energy=te.zone if te else None,
                energy_source=te.source if te else None,
                energy_confidence=te.confidence if te else None,
                energy_value=te.numeric if te else None,
                energy_label=te.label if te else None,
                energy_conflict=conflict_resp,
            )
        )
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

    total = (
        w["harmonic"] * h
        + w["energy_fit"] * e
        + w["bpm_compat"] * b
        + w["genre_coherence"] * g
        + w["track_quality"] * q
    )

    af_a = t_a.audio_features
    af_b = t_b.audio_features

    wf_a = (
        base64.b64encode(af_a.waveform_overview).decode("ascii")
        if af_a and af_a.waveform_overview
        else None
    )
    wf_b = (
        base64.b64encode(af_b.waveform_overview).decode("ascii")
        if af_b and af_b.waveform_overview
        else None
    )
    bt_a = (
        base64.b64encode(af_a.beat_positions).decode("ascii")
        if af_a and af_a.beat_positions
        else None
    )
    bt_b = (
        base64.b64encode(af_b.beat_positions).decode("ascii")
        if af_b and af_b.beat_positions
        else None
    )

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
    from kiku.energy import get_track_energy

    af = t.audio_features
    te = get_track_energy(t)
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
        resolved_energy=te.zone,
        energy_source=te.source,
        energy_confidence=te.confidence,
        energy_value=te.numeric,
        energy_label=te.label,
        energy_conflict=conflict_resp,
    )


@router.get(
    "/{set_id}/tracks/{position}/replacements", response_model=ReplacementSuggestionsResponse
)
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
    try:
        result = sets_service.replacement_candidates(
            db,
            set_id,
            position,
            n=n,
            genre_filter=genre_filter,
            discovery_density=discovery_density,
        )
    except sets_service.SetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))

    candidates = [
        ReplacementCandidate(
            track=_track_response(cand),
            combined_score=combined,
            incoming_breakdown=ReplacementBreakdown(**incoming) if incoming else None,
            outgoing_breakdown=ReplacementBreakdown(**outgoing) if outgoing else None,
        )
        for cand, combined, incoming, outgoing in result["candidates"]
    ]
    context = ReplacementContext(
        prev_track=_track_summary(result["prev_track"]) if result["prev_track"] else None,
        next_track=_track_summary(result["next_track"]) if result["next_track"] else None,
        energy_target=result["energy_target"],
        position=result["position"],
    )

    return ReplacementSuggestionsResponse(context=context, candidates=candidates)


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


@router.get("/{set_id}/artist-picks", response_model=ArtistPicksResponse)
def get_artist_picks(
    set_id: int,
    artist: str,
    n: int = 5,
    discovery_density: float = 0.0,
    db: Session = Depends(get_db),
):
    """Rank an artist's owned tracks by their best fit anywhere in the set.

    Library excavation only — every pick is a track the DJ already owns.
    Returns an empty pick list (200) when the artist owns nothing new here.
    """
    from kiku.setbuilder.artist_picks import rank_artist_picks

    s = db.get(Set, set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    ranked = rank_artist_picks(
        db,
        set_id,
        artist,
        n=n,
        discovery_density=discovery_density,
    )

    _BD_FIELDS = {
        "harmonic",
        "energy_fit",
        "bpm_compat",
        "genre_coherence",
        "track_quality",
        "total",
        "discovery_label",
        "set_appearances",
    }
    picks = [
        ArtistPickItem(
            track=_track_response(p.track),
            position=p.position,
            score=p.score,
            breakdown=(
                TransitionScoreBreakdown(
                    **{k: v for k, v in p.breakdown.items() if k in _BD_FIELDS}
                )
                if p.breakdown
                else None
            ),
            reason=p.reason,
        )
        for p in ranked
    ]
    return ArtistPicksResponse(set_id=set_id, artist=artist, picks=picks)


@router.get("/{set_id}/slots/{position}/suggestions", response_model=SlotSuggestionsResponse)
def get_slot_suggestions(
    set_id: int,
    position: int,
    mode: str = "insert",
    intent: str = "hold",
    allowed_keys: str | None = None,
    energy_delta: float | None = None,
    n: int = 10,
    db: Session = Depends(get_db),
):
    """Rank owned tracks that make a directional move at a slot, both-neighbor aware.

    ``mode`` (insert|replace) + ``intent`` (push_higher|brighten|cool_down|hold)
    name the slot and the direction; Kiku answers with tracks the DJ already
    owns, each reporting the harmonic move and any caveat when the slot resists
    it. Library excavation only.
    """
    from kiku.setbuilder.camelot import camelot_str, intent_energy_delta, parse_camelot
    from kiku.setbuilder.slot_picks import rank_slot_picks

    s = db.get(Set, set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    if mode not in ("insert", "replace"):
        raise HTTPException(status_code=400, detail="mode must be 'insert' or 'replace'")
    if intent not in ("push_higher", "brighten", "cool_down", "hold"):
        raise HTTPException(
            status_code=400,
            detail="intent must be one of push_higher, brighten, cool_down, hold",
        )

    ordered = sorted(s.tracks, key=lambda st: st.position)
    if position < 0 or position >= len(ordered):
        raise HTTPException(status_code=404, detail="Invalid position")

    keys: set[str] | None = None
    if allowed_keys:
        raw = [k.strip() for k in allowed_keys.split(",") if k.strip()]
        if raw:
            # Canonicalize to Camelot; an all-invalid list stays an empty set
            # (matches nothing) so the response never echoes a filter it didn't
            # actually apply.
            keys = {camelot_str(pc) for k in raw if (pc := parse_camelot(k))}

    ranked = rank_slot_picks(
        db,
        set_id,
        position,
        mode,
        intent,
        allowed_keys=keys,
        energy_delta=energy_delta,
        n=n,
    )

    _BD_FIELDS = {
        "harmonic",
        "energy_fit",
        "bpm_compat",
        "genre_coherence",
        "track_quality",
        "total",
        "discovery_label",
        "set_appearances",
    }

    def _bd(b: dict | None) -> ReplacementBreakdown | None:
        if not b:
            return None
        return ReplacementBreakdown(**{k: v for k, v in b.items() if k in _BD_FIELDS})

    resolved_delta = energy_delta if energy_delta is not None else intent_energy_delta(intent)
    suggestions = [
        SlotSuggestionItem(
            track=_track_response(p.track),
            from_key=p.from_key,
            to_key=p.to_key,
            move=p.move,
            energy_shift=p.energy_shift,
            score=p.score,
            incoming_breakdown=_bd(p.incoming_breakdown),
            outgoing_breakdown=_bd(p.outgoing_breakdown),
            caveat=p.caveat,
        )
        for p in ranked
    ]
    return SlotSuggestionsResponse(
        set_id=set_id,
        position=position,
        mode=mode,
        intent=intent,
        allowed_keys=sorted(keys) if keys else None,
        energy_delta=round(resolved_delta, 3),
        suggestions=suggestions,
    )
