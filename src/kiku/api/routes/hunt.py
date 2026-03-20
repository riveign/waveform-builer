"""Track Hunter API — extract tracklists from DJ sets and find purchase sources."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    HuntListResponse,
    HuntRequest,
    HuntSessionResponse,
    HuntSessionSummary,
    HuntTrackResponse,
    HuntTrackUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hunt", tags=["hunt"])


def _hunt_track_to_response(ht) -> HuntTrackResponse:
    """Convert a HuntTrack model to response."""
    links = {}
    if ht.purchase_links:
        try:
            links = json.loads(ht.purchase_links)
        except (json.JSONDecodeError, TypeError):
            pass
    return HuntTrackResponse(
        id=ht.id,
        position=ht.position,
        artist=ht.artist,
        title=ht.title,
        remix_info=ht.remix_info,
        original_title=ht.original_title,
        confidence=ht.confidence or 0.0,
        source=ht.source,
        timestamp_sec=ht.timestamp_sec,
        matched_track_id=ht.matched_track_id,
        match_score=ht.match_score,
        acquisition_status=ht.acquisition_status or "unowned",
        purchase_links=links,
        raw_text=ht.raw_text,
    )


def _hunt_session_to_response(hunt) -> HuntSessionResponse:
    """Convert a HuntSession model to full response with tracks."""
    return HuntSessionResponse(
        id=hunt.id,
        url=hunt.url,
        platform=hunt.platform,
        title=hunt.title,
        uploader=hunt.uploader,
        status=hunt.status or "pending",
        track_count=hunt.track_count or 0,
        owned_count=hunt.owned_count or 0,
        created_at=hunt.created_at,
        tracks=[_hunt_track_to_response(ht) for ht in (hunt.tracks or [])],
    )


@router.post("", response_model=HuntSessionResponse)
def start_hunt(body: HuntRequest, db: Session = Depends(get_db)):
    """Start a new track hunt from a URL.

    Extracts tracklist from the given URL, matches against library,
    and generates purchase links for unowned tracks.
    """
    from kiku.db.store import create_hunt_session, save_hunt_tracks
    from kiku.hunting.extractor import detect_platform, extract_metadata
    from kiku.hunting.matcher import match_tracks
    from kiku.hunting.parsers.tracklist import (
        merge_tracklists,
        parse_chapters,
        parse_comments,
        parse_description,
    )
    from kiku.hunting.sources import generate_purchase_links

    # Detect platform
    platform = detect_platform(body.url)
    if not platform:
        raise HTTPException(status_code=400, detail="Unsupported URL — try YouTube, SoundCloud, or Mixcloud")

    # Create session
    hunt = create_hunt_session(db, url=body.url, platform=platform)
    hunt.status = "extracting"
    db.flush()

    # Extract metadata
    metadata = extract_metadata(body.url, include_comments=body.include_comments)
    if metadata.error:
        hunt.status = "error"
        hunt.error_message = metadata.error
        db.commit()
        raise HTTPException(status_code=422, detail=metadata.error)

    hunt.title = metadata.title
    hunt.uploader = metadata.uploader
    hunt.status = "matching"
    db.flush()

    # Parse tracklist from all sources
    desc_tracks = parse_description(metadata.description)
    chapter_tracks = parse_chapters(metadata.chapters)
    comment_tracks = parse_comments(metadata.comments)

    merged = merge_tracklists(chapter_tracks, desc_tracks, comment_tracks)

    if not merged:
        hunt.status = "complete"
        hunt.track_count = 0
        db.commit()
        return _hunt_session_to_response(hunt)

    # Convert to dicts for matching
    track_dicts = [
        {
            "position": t.position,
            "artist": t.artist,
            "title": t.title,
            "remix_info": t.remix_info,
            "original_title": t.original_title,
            "confidence": t.confidence,
            "source": t.source,
            "timestamp_sec": t.timestamp_sec,
            "raw_text": t.raw_text,
        }
        for t in merged
    ]

    # Match against library
    matched = match_tracks(db, track_dicts)

    # Generate purchase links for unowned tracks
    for t in matched:
        if t.get("acquisition_status") != "owned" and t.get("artist") and t.get("title"):
            t["purchase_links"] = generate_purchase_links(t["artist"], t["title"])

    # Save to DB
    save_hunt_tracks(db, hunt.id, matched)
    db.commit()

    # Reload to get relationships
    db.refresh(hunt)
    return _hunt_session_to_response(hunt)


@router.get("s", response_model=HuntListResponse)
def list_hunts(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List past hunt sessions."""
    from kiku.db.store import list_hunt_sessions

    hunts, total = list_hunt_sessions(db, limit=limit, offset=offset)
    items = [
        HuntSessionSummary(
            id=h.id,
            url=h.url,
            platform=h.platform,
            title=h.title,
            uploader=h.uploader,
            status=h.status or "pending",
            track_count=h.track_count or 0,
            owned_count=h.owned_count or 0,
            created_at=h.created_at,
        )
        for h in hunts
    ]
    return HuntListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{hunt_id}", response_model=HuntSessionResponse)
def get_hunt(hunt_id: int, db: Session = Depends(get_db)):
    """Get a hunt session with full tracklist."""
    from kiku.db.store import get_hunt_session

    hunt = get_hunt_session(db, hunt_id)
    if not hunt:
        raise HTTPException(status_code=404, detail="Hunt session not found")
    return _hunt_session_to_response(hunt)


@router.patch("/tracks/{track_id}", response_model=HuntTrackResponse)
def update_hunt_track(
    track_id: int,
    body: HuntTrackUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update a hunt track's acquisition status (e.g. mark as 'wanted')."""
    from kiku.db.store import update_hunt_track_status

    if body.acquisition_status not in ("wanted", "owned", "unowned"):
        raise HTTPException(status_code=400, detail="Status must be wanted, owned, or unowned")

    ht = update_hunt_track_status(db, track_id, body.acquisition_status)
    if not ht:
        raise HTTPException(status_code=404, detail="Hunt track not found")
    db.commit()
    return _hunt_track_to_response(ht)
