"""Album browsing + MusicBrainz enrichment endpoints."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.routes.tracks import _track_to_response
from kiku.api.schemas import (
    AlbumResponse,
    AlbumTracksResponse,
    MBApplyRequest,
    MBApplyResponse,
    MBCandidate,
    MBCandidateRecording,
    MBMappingPreviewItem,
    MBMatchResponse,
    PaginatedAlbumsResponse,
)
from kiku.db.models import AlbumMetadata, Track

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/albums", tags=["albums"])


_WS_RE = re.compile(r"\s+")


def _normalize(s: str | None) -> str:
    if not s:
        return ""
    return _WS_RE.sub(" ", s.strip().lower())


def _album_key(album: str, artist: str) -> str:
    raw = f"{_normalize(album)}|{_normalize(artist)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _resolve_album_artist(session: Session, album: str) -> tuple[str, bool]:
    """Return (album_artist, is_compilation) for an album name.

    Compilation if 2+ distinct non-null artists, otherwise the single artist.
    """
    rows = (
        session.query(Track.artist)
        .filter(Track.album == album, Track.artist.isnot(None))
        .distinct()
        .all()
    )
    artists = sorted({a[0] for a in rows if a[0]})
    if len(artists) > 1:
        return "Various Artists", True
    if artists:
        return artists[0], False
    return "Unknown Artist", False


def _build_album_response(
    session: Session,
    album: str,
    artist: str,
    year: int | None,
    label: str | None,
    track_count: int,
    is_compilation: bool,
) -> AlbumResponse:
    key = _album_key(album, artist)

    # Pick cover track: lowest (disc_number, track_number, file_path) for this album
    cover_row = (
        session.query(Track.id)
        .filter(Track.album == album)
        .order_by(
            Track.disc_number.is_(None),
            Track.disc_number.asc(),
            Track.track_number.is_(None),
            Track.track_number.asc(),
            Track.file_path.asc(),
        )
        .limit(1)
        .first()
    )
    cover_id = cover_row[0] if cover_row else None

    md = session.get(AlbumMetadata, key)
    return AlbumResponse(
        album_key=key,
        album=album,
        artist=artist,
        year=year,
        label=label,
        track_count=track_count,
        cover_track_id=cover_id,
        is_compilation=is_compilation,
        mb_release_id=md.mb_release_id if md else None,
        match_status=md.match_status if md else None,
    )


def _find_album_by_key(session: Session, album_key: str) -> tuple[str, str, bool] | None:
    """Find the (album, album_artist, is_compilation) tuple matching an album_key.

    We don't store album→key mapping, so we iterate distinct albums and re-derive keys.
    For 3k+ albums this is fine; if it grows we can persist the mapping.
    """
    albums = session.query(Track.album).filter(Track.album.isnot(None)).distinct().all()
    for (album,) in albums:
        if not album:
            continue
        artist, is_comp = _resolve_album_artist(session, album)
        if _album_key(album, artist) == album_key:
            return album, artist, is_comp
    return None


@router.get("", response_model=PaginatedAlbumsResponse)
def list_albums(
    search: str | None = None,
    artist: list[str] | None = Query(None),
    label: list[str] | None = Query(None),
    year_min: int | None = None,
    year_max: int | None = None,
    sort: str = "artist",  # "artist" | "year" | "recent"
    limit: int = 60,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> PaginatedAlbumsResponse:
    # Aggregate per-album metadata first
    agg = (
        db.query(
            Track.album.label("album"),
            func.min(Track.release_year).label("year"),
            func.min(Track.label).label("label"),
            func.count(Track.id).label("track_count"),
            func.max(Track.date_added).label("latest_added"),
            func.count(func.distinct(Track.artist)).label("artist_count"),
        )
        .filter(Track.album.isnot(None), Track.album != "")
        .group_by(Track.album)
    )

    if search:
        like = f"%{search.lower()}%"
        agg = agg.filter(func.lower(Track.album).like(like))
    if label:
        agg = agg.filter(Track.label.in_(label))
    if year_min is not None:
        agg = agg.having(func.min(Track.release_year) >= year_min)
    if year_max is not None:
        agg = agg.having(func.min(Track.release_year) <= year_max)

    rows = agg.all()

    # Resolve album_artist per row + filter by artist if requested
    enriched: list[tuple[str, str, int | None, str | None, int, bool, str | None]] = []
    for r in rows:
        album_name = r.album
        a_artist, is_comp = _resolve_album_artist(db, album_name)
        if artist and a_artist not in artist:
            continue
        enriched.append((
            album_name, a_artist, r.year, r.label, r.track_count, is_comp, r.latest_added
        ))

    # Sort
    if sort == "year":
        enriched.sort(key=lambda x: (x[2] is None, -(x[2] or 0)))
    elif sort == "recent":
        enriched.sort(key=lambda x: (x[6] is None, x[6] or ""), reverse=True)
    else:
        enriched.sort(key=lambda x: (x[1].lower(), x[0].lower()))

    total = len(enriched)
    page = enriched[offset:offset + limit]

    items = [
        _build_album_response(db, album, artist_, year, lbl, cnt, is_comp)
        for album, artist_, year, lbl, cnt, is_comp, _ in page
    ]
    return PaginatedAlbumsResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{album_key}/tracks", response_model=AlbumTracksResponse)
def album_tracks(album_key: str, db: Session = Depends(get_db)) -> AlbumTracksResponse:
    resolved = _find_album_by_key(db, album_key)
    if not resolved:
        raise HTTPException(status_code=404, detail="Album not found")
    album_name, artist, is_comp = resolved

    tracks = (
        db.query(Track)
        .filter(Track.album == album_name)
        .order_by(
            Track.disc_number.is_(None),
            Track.disc_number.asc(),
            Track.track_number.is_(None),
            Track.track_number.asc(),
            Track.file_path.asc(),
        )
        .all()
    )

    year = next((t.release_year for t in tracks if t.release_year), None)
    label = next((t.label for t in tracks if t.label), None)

    album = _build_album_response(db, album_name, artist, year, label, len(tracks), is_comp)
    return AlbumTracksResponse(
        album=album,
        tracks=[_track_to_response(t) for t in tracks],
    )


@router.get("/{album_key}/cover")
def album_cover(album_key: str, db: Session = Depends(get_db)):
    """Serve the album cover, fetching from Cover Art Archive on first hit.

    Resolution order:
        1. On-disk cache → serve file
        2. AlbumMetadata.mb_release_id → fetch from CAA, cache, serve
        3. Fallback to the embedded artwork of the album's cover track (302 redirect)
        4. 404 if nothing is available
    """
    from kiku.musicbrainz.cover_art import (
        cached_cover_path,
        fetch_front_cover,
        is_cover_known_missing,
    )

    # 1. Cache hit
    cached = cached_cover_path(album_key)
    if cached:
        return FileResponse(
            cached,
            media_type=_image_media_type(cached.suffix),
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # 2. Try CAA if we have an MB release id and haven't already marked missing
    md = db.get(AlbumMetadata, album_key)
    if md and md.mb_release_id and not is_cover_known_missing(album_key):
        path = fetch_front_cover(md.mb_release_id, album_key)
        if path is not None:
            return FileResponse(
                path,
                media_type=_image_media_type(path.suffix),
                headers={"Cache-Control": "public, max-age=86400"},
            )

    # 3. Fallback: redirect to the embedded artwork of the album's cover track
    resolved = _find_album_by_key(db, album_key)
    if resolved:
        album_name, _, _ = resolved
        cover_row = (
            db.query(Track.id)
            .filter(Track.album == album_name)
            .order_by(
                Track.disc_number.is_(None),
                Track.disc_number.asc(),
                Track.track_number.is_(None),
                Track.track_number.asc(),
                Track.file_path.asc(),
            )
            .limit(1)
            .first()
        )
        if cover_row:
            return RedirectResponse(f"/api/tracks/{cover_row[0]}/artwork", status_code=302)

    # 4. Nothing
    raise HTTPException(status_code=404, detail="No cover available")


def _image_media_type(suffix: str) -> str:
    s = suffix.lower().lstrip(".")
    if s == "png":
        return "image/png"
    return "image/jpeg"


@router.post("/{album_key}/match-musicbrainz", response_model=MBMatchResponse)
def match_musicbrainz(album_key: str, db: Session = Depends(get_db)) -> MBMatchResponse:
    resolved = _find_album_by_key(db, album_key)
    if not resolved:
        raise HTTPException(status_code=404, detail="Album not found")
    album_name, artist, _ = resolved

    tracks = (
        db.query(Track)
        .filter(Track.album == album_name)
        .order_by(Track.file_path.asc())
        .all()
    )

    from kiku.musicbrainz.client import MusicBrainzClient
    from kiku.musicbrainz.match import match_tracklist

    client = MusicBrainzClient()
    try:
        candidates_raw = client.search_releases(album_name, artist, limit=3)
    except Exception as e:  # noqa: BLE001
        logger.exception("MusicBrainz search failed")
        raise HTTPException(status_code=502, detail=f"MusicBrainz search failed: {e}") from e

    candidates: list[MBCandidate] = []
    for cand in candidates_raw:
        mb_release_id = cand["id"]
        try:
            full = client.get_release(mb_release_id)
        except Exception:  # noqa: BLE001
            logger.warning("Skipping candidate %s: detail fetch failed", mb_release_id)
            continue

        recordings_raw: list[dict] = []
        for medium in full.get("media", []) or []:
            disc_no = medium.get("position", 1) or 1
            for tr in medium.get("tracks", []) or []:
                pos = tr.get("position")
                title = (tr.get("title") or "").strip()
                length = tr.get("length")
                if pos and title:
                    recordings_raw.append({
                        "position": int(pos),
                        "disc": int(disc_no),
                        "title": title,
                        "length_ms": int(length) if length else None,
                    })

        mapping = match_tracklist(
            [{"id": t.id, "title": t.title or ""} for t in tracks],
            recordings_raw,
        )
        preview = [
            MBMappingPreviewItem(
                track_id=m["track_id"],
                track_title=next((t.title for t in tracks if t.id == m["track_id"]), None),
                mb_position=m.get("mb_position"),
                mb_disc=m.get("mb_disc"),
                mb_title=m.get("mb_title"),
                confidence=m.get("confidence", 0.0),
            )
            for m in mapping
        ]

        label_info = full.get("label-info") or []
        label_name = None
        if label_info and label_info[0].get("label"):
            label_name = label_info[0]["label"].get("name")

        candidates.append(MBCandidate(
            mb_release_id=mb_release_id,
            title=full.get("title", album_name),
            artist=_format_mb_artist(full.get("artist-credit")),
            year=_year_from_date(full.get("date")),
            country=full.get("country"),
            label=label_name,
            track_count=sum(len(m.get("tracks") or []) for m in (full.get("media") or [])),
            recordings=[MBCandidateRecording(**r) for r in recordings_raw],
            score=float(cand.get("score", 0)) / 100.0 if cand.get("score") else 0.0,
            mapping_preview=preview,
        ))

    return MBMatchResponse(candidates=candidates)


@router.post("/{album_key}/apply-mb-mapping", response_model=MBApplyResponse)
def apply_mb_mapping(
    album_key: str,
    body: MBApplyRequest,
    db: Session = Depends(get_db),
) -> MBApplyResponse:
    resolved = _find_album_by_key(db, album_key)
    if not resolved:
        raise HTTPException(status_code=404, detail="Album not found")
    album_name, artist, _ = resolved

    valid_track_ids = {
        tid for (tid,) in db.query(Track.id).filter(Track.album == album_name).all()
    }

    updated = 0
    for m in body.mappings:
        if m.track_id not in valid_track_ids:
            continue
        if m.track_number is None:
            continue
        track = db.get(Track, m.track_id)
        if not track:
            continue
        track.track_number = m.track_number
        if m.disc_number is not None:
            track.disc_number = m.disc_number
        updated += 1

    md = db.get(AlbumMetadata, album_key)
    if md is None:
        md = AlbumMetadata(
            album_key=album_key,
            album=album_name,
            album_artist=artist,
        )
        db.add(md)
    md.mb_release_id = body.mb_release_id
    md.last_matched_at = datetime.utcnow()
    md.match_status = "applied"

    db.commit()

    return MBApplyResponse(
        updated_count=updated,
        album_key=album_key,
        mb_release_id=body.mb_release_id,
    )


def _format_mb_artist(artist_credit) -> str:
    if not artist_credit:
        return ""
    parts: list[str] = []
    for ac in artist_credit:
        if isinstance(ac, str):
            parts.append(ac)
        elif isinstance(ac, dict):
            name = ac.get("name") or (ac.get("artist") or {}).get("name", "")
            parts.append(name)
    return "".join(parts).strip() or "Various Artists"


def _year_from_date(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None
