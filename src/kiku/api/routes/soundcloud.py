"""SoundCloud integration — OAuth flow, browsing, and chase-to-hunt."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    HuntSessionResponse,
    SCChaseRequest,
    SCConnectResponse,
    SCLikesResponse,
    SCPlaylistResponse,
    SCStatusResponse,
    SCTrackResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/soundcloud", tags=["soundcloud"])


def _get_redirect_uri(request: Request) -> str:
    """Build callback URL from current request."""
    return str(request.url_for("soundcloud_callback"))


def _build_client(db: Session):
    """Build a SoundCloudClient from stored token, with auto-refresh callback."""
    from kiku.db.store import get_oauth_token, update_oauth_token
    from kiku.soundcloud.client import SoundCloudClient

    token = get_oauth_token(db, "soundcloud")
    if not token:
        raise HTTPException(status_code=401, detail="SoundCloud not connected")

    def on_refresh(new_access, new_refresh, expires_at):
        update_oauth_token(db, "soundcloud", new_access, new_refresh, expires_at)
        db.commit()

    return SoundCloudClient(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        on_token_refresh=on_refresh,
    )


@router.get("/status", response_model=SCStatusResponse)
def soundcloud_status(db: Session = Depends(get_db)):
    """Check if SoundCloud is connected."""
    from kiku.db.store import get_oauth_token

    token = get_oauth_token(db, "soundcloud")
    if not token:
        return SCStatusResponse(connected=False)
    return SCStatusResponse(
        connected=True,
        username=token.username,
        avatar_url=token.avatar_url,
        user_id=token.user_id,
    )


@router.get("/connect", response_model=SCConnectResponse)
def soundcloud_connect(request: Request):
    """Get OAuth authorization URL."""
    from kiku.soundcloud.oauth import get_auth_url

    redirect_uri = _get_redirect_uri(request)
    auth_url = get_auth_url(redirect_uri)
    return SCConnectResponse(auth_url=auth_url)


@router.get("/callback", response_class=HTMLResponse, name="soundcloud_callback")
def soundcloud_callback(code: str, request: Request, db: Session = Depends(get_db)):
    """OAuth callback — exchange code, store token, close popup."""
    from datetime import datetime, timedelta

    from kiku.db.store import save_oauth_token
    from kiku.soundcloud.client import SoundCloudClient
    from kiku.soundcloud.oauth import exchange_code

    redirect_uri = _get_redirect_uri(request)
    token_data = exchange_code(code, redirect_uri)

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_at = None
    if "expires_in" in token_data:
        expires_at = (datetime.now() + timedelta(seconds=token_data["expires_in"])).isoformat()

    # Fetch user profile
    client = SoundCloudClient(access_token)
    me = client.get_me()

    save_oauth_token(
        db,
        provider="soundcloud",
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        user_id=str(me.get("id", "")),
        username=me.get("username"),
        avatar_url=me.get("avatar_url"),
    )
    db.commit()

    return HTMLResponse("""
        <html><body><script>
            window.opener.postMessage('sc-connected', '*');
            window.close();
        </script><p>Connected! You can close this window.</p></body></html>
    """)


@router.delete("/disconnect")
def soundcloud_disconnect(db: Session = Depends(get_db)):
    """Remove stored SoundCloud token."""
    from kiku.db.store import delete_oauth_token

    deleted = delete_oauth_token(db, "soundcloud")
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="No SoundCloud connection found")
    return {"ok": True}


@router.get("/playlists", response_model=list[SCPlaylistResponse])
def soundcloud_playlists(db: Session = Depends(get_db)):
    """List user's SoundCloud playlists."""
    client = _build_client(db)
    playlists = client.get_playlists()

    return [
        SCPlaylistResponse(
            id=p.get("id", 0),
            title=p.get("title", "Untitled"),
            track_count=p.get("track_count", 0),
            permalink_url=p.get("permalink_url", ""),
            artwork_url=p.get("artwork_url"),
            duration_ms=p.get("duration", 0),
        )
        for p in playlists
    ]


@router.get("/likes", response_model=SCLikesResponse)
def soundcloud_likes(cursor: str | None = None, db: Session = Depends(get_db)):
    """Get liked tracks (paginated)."""
    client = _build_client(db)
    data = client.get_likes(cursor=cursor)

    tracks = []
    for item in data["collection"]:
        # Likes API wraps tracks in {track: {...}} or returns track directly
        t = item.get("track", item) if isinstance(item, dict) else item
        if not isinstance(t, dict):
            continue
        user = t.get("user", {})
        tracks.append(SCTrackResponse(
            id=t.get("id", 0),
            title=t.get("title", ""),
            artist=user.get("username"),
            permalink_url=t.get("permalink_url", ""),
            artwork_url=t.get("artwork_url"),
            duration_ms=t.get("duration", 0),
            genre=t.get("genre"),
            bpm=t.get("bpm"),
        ))

    # Extract cursor from next_href
    next_cursor = None
    if data.get("next_href"):
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(data["next_href"])
        qs = parse_qs(parsed.query)
        next_cursor = qs.get("cursor", [None])[0]

    return SCLikesResponse(tracks=tracks, next_cursor=next_cursor)


@router.post("/chase", response_model=HuntSessionResponse)
def soundcloud_chase(body: SCChaseRequest, db: Session = Depends(get_db)):
    """Chase tracks from a SoundCloud playlist or liked selection.

    Creates a HuntSession, matches against library, generates purchase links.
    """
    from kiku.db.store import create_hunt_session, save_hunt_tracks
    from kiku.hunting.matcher import match_tracks
    from kiku.hunting.sources import generate_purchase_links

    client = _build_client(db)

    # Fetch SC tracks
    sc_tracks: list[dict] = []
    session_url = ""
    session_title = ""

    if body.playlist_id:
        sc_tracks = client.get_playlist_tracks(body.playlist_id)
        # Get playlist info for title
        playlists = client.get_playlists()
        pl = next((p for p in playlists if p.get("id") == body.playlist_id), None)
        session_title = pl.get("title", "SoundCloud Playlist") if pl else "SoundCloud Playlist"
        session_url = pl.get("permalink_url", f"soundcloud://playlist/{body.playlist_id}") if pl else ""
        source = "soundcloud_playlist"
    elif body.track_ids:
        # Chase selected likes — fetch full like list and filter
        all_likes: list[dict] = []
        cursor = None
        wanted_ids = set(body.track_ids)
        while True:
            page = client.get_likes(limit=50, cursor=cursor)
            for item in page["collection"]:
                t = item.get("track", item) if isinstance(item, dict) else item
                if isinstance(t, dict) and t.get("id") in wanted_ids:
                    all_likes.append(t)
            if len(all_likes) >= len(wanted_ids) or not page.get("next_href"):
                break
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(page["next_href"])
            qs = parse_qs(parsed.query)
            cursor = qs.get("cursor", [None])[0]

        sc_tracks = all_likes
        session_title = "SoundCloud Likes"
        session_url = "soundcloud://likes"
        source = "soundcloud_likes"
    else:
        raise HTTPException(status_code=400, detail="Provide playlist_id or track_ids")

    if not sc_tracks:
        raise HTTPException(status_code=404, detail="No tracks found")

    # Create hunt session
    hunt = create_hunt_session(
        db, url=session_url, platform="soundcloud",
        title=session_title, uploader=None,
    )
    hunt.status = "matching"
    db.flush()

    # Build track dicts for matching
    track_dicts = []
    for i, t in enumerate(sc_tracks):
        user = t.get("user", {})
        # Parse "Artist - Title" pattern from SC title
        sc_title = t.get("title", "")
        artist = user.get("username", "")
        title = sc_title

        if " - " in sc_title:
            parts = sc_title.split(" - ", 1)
            artist = parts[0].strip()
            title = parts[1].strip()

        track_dicts.append({
            "position": i + 1,
            "artist": artist,
            "title": title,
            "confidence": 1.0,
            "source": source,
            "raw_text": sc_title,
            "external_url": t.get("permalink_url"),
            "external_id": str(t.get("id", "")),
        })

    # Match against library
    matched = match_tracks(db, track_dicts)

    # Purchase links for unowned
    for t in matched:
        if t.get("acquisition_status") != "owned" and t.get("artist") and t.get("title"):
            t["purchase_links"] = generate_purchase_links(t["artist"], t["title"])

    # Save — need to extend save_hunt_tracks to handle external fields
    _save_hunt_tracks_with_external(db, hunt.id, matched)
    db.commit()

    db.refresh(hunt)

    # Re-use hunt.py serializer
    from kiku.api.routes.hunt import _hunt_session_to_response
    return _hunt_session_to_response(hunt)


def _save_hunt_tracks_with_external(session: Session, hunt_id: int, tracks: list[dict]):
    """Save hunt tracks including external_url and external_id fields."""
    from kiku.db.models import HuntSession, HuntTrack

    hunt = session.query(HuntSession).filter_by(id=hunt_id).first()
    if not hunt:
        return []

    results = []
    for t in tracks:
        ht = HuntTrack(
            session_id=hunt_id,
            position=t.get("position", 0),
            raw_text=t.get("raw_text"),
            artist=t.get("artist"),
            title=t.get("title"),
            remix_info=t.get("remix_info"),
            original_artist=t.get("original_artist"),
            original_title=t.get("original_title"),
            confidence=t.get("confidence", 0.0),
            source=t.get("source"),
            timestamp_sec=t.get("timestamp_sec"),
            matched_track_id=t.get("matched_track_id"),
            match_score=t.get("match_score"),
            acquisition_status=t.get("acquisition_status", "unowned"),
            purchase_links=json.dumps(t.get("purchase_links", {})),
            external_url=t.get("external_url"),
            external_id=t.get("external_id"),
        )
        session.add(ht)
        results.append(ht)

    hunt.track_count = len(tracks)
    hunt.owned_count = sum(1 for t in tracks if t.get("acquisition_status") == "owned")
    hunt.status = "complete"
    session.flush()
    return results
