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


def _classify_artist(artist_count: int, any_artist: str | None) -> tuple[str, bool]:
    """Resolve album_artist + is_compilation from aggregate counts.

    COUNT(DISTINCT) and MIN() both ignore NULLs in SQL, so:
      0 → all NULL → "Unknown Artist"
      1 → single artist → use it
      >1 → "Various Artists" + compilation
    """
    if artist_count > 1:
        return "Various Artists", True
    if artist_count == 1 and any_artist:
        return any_artist, False
    return "Unknown Artist", False


def _resolve_album_artist(session: Session, album: str) -> tuple[str, bool]:
    """Single-album lookup used by detail endpoints (tracks / cover / MB)."""
    row = (
        session.query(
            func.count(func.distinct(Track.artist)).label("artist_count"),
            func.min(Track.artist).label("any_artist"),
        )
        .filter(Track.album == album)
        .one()
    )
    return _classify_artist(row.artist_count or 0, row.any_artist)


def _batch_cover_track_ids(session: Session, album_names: list[str]) -> dict[str, int]:
    """Return {album_name: cover_track_id} for the given albums in one query.

    Cover track = lowest (disc_number, track_number, file_path) per album.
    """
    if not album_names:
        return {}
    row_num = func.row_number().over(
        partition_by=Track.album,
        order_by=(
            Track.disc_number.is_(None),
            Track.disc_number.asc(),
            Track.track_number.is_(None),
            Track.track_number.asc(),
            Track.file_path.asc(),
        ),
    ).label("rn")
    subq = (
        session.query(Track.id.label("tid"), Track.album.label("alb"), row_num)
        .filter(Track.album.in_(album_names))
        .subquery()
    )
    rows = session.query(subq.c.alb, subq.c.tid).filter(subq.c.rn == 1).all()
    return {alb: tid for alb, tid in rows}


def _find_album_by_key(
    session: Session, album_key: str
) -> tuple[list[str], str, bool] | None:
    """Find the (album_names, album_artist, is_compilation) tuple matching an album_key.

    Multiple raw album names can normalize to the same key (e.g. casing variants
    like "Hard Work" / "Hard work"). All variants are returned so downstream
    queries can span them via `Track.album.in_(names)`.
    """
    rows = (
        session.query(
            Track.album.label("album"),
            func.count(func.distinct(Track.artist)).label("artist_count"),
            func.min(Track.artist).label("any_artist"),
        )
        .filter(Track.album.isnot(None), Track.album != "")
        .group_by(Track.album)
        .all()
    )
    matches: list[tuple[str, str, bool]] = []
    for album, artist_count, any_artist in rows:
        if not album:
            continue
        artist, is_comp = _classify_artist(artist_count or 0, any_artist)
        if _album_key(album, artist) == album_key:
            matches.append((album, artist, is_comp))
    if not matches:
        return None
    names = [m[0] for m in matches]
    artist = matches[0][1]
    is_comp = any(m[2] for m in matches)
    return names, artist, is_comp


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
    # One aggregation gives us everything we need to classify each album.
    # MIN(artist) doubles as the representative artist when artist_count == 1.
    agg = (
        db.query(
            Track.album.label("album"),
            func.min(Track.release_year).label("year"),
            func.min(Track.label).label("label"),
            func.count(Track.id).label("track_count"),
            func.max(Track.date_added).label("latest_added"),
            func.count(func.distinct(Track.artist)).label("artist_count"),
            func.min(Track.artist).label("any_artist"),
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

    # Merge raw album rows that normalize to the same album_key (casing/whitespace
    # variants). The first variant wins for display; track counts sum; year takes
    # the earliest; latest_added takes the max. `names` holds every raw album
    # string in this group so cover/track lookups can span all variants.
    merged: dict[str, list] = {}  # album_key → [names, artist, year, label, count, is_comp, latest_added]
    for r in rows:
        a_artist, is_comp = _classify_artist(r.artist_count or 0, r.any_artist)
        if artist and a_artist not in artist:
            continue
        key = _album_key(r.album, a_artist)
        if key in merged:
            existing = merged[key]
            existing[0].append(r.album)
            existing[4] += r.track_count
            if r.year is not None and (existing[2] is None or r.year < existing[2]):
                existing[2] = r.year
            if existing[3] is None and r.label:
                existing[3] = r.label
            if r.latest_added and (existing[6] is None or r.latest_added > existing[6]):
                existing[6] = r.latest_added
            existing[5] = existing[5] or is_comp
        else:
            merged[key] = [
                [r.album], a_artist, r.year, r.label, r.track_count, is_comp, r.latest_added,
            ]
    # Pack as (album_key, [names], artist, year, label, count, is_comp, latest_added)
    enriched: list[tuple[str, list[str], str, int | None, str | None, int, bool, str | None]] = [
        (k, *v) for k, v in merged.items()  # type: ignore[misc]
    ]

    if sort == "year":
        enriched.sort(key=lambda x: (x[3] is None, -(x[3] or 0)))
    elif sort == "recent":
        enriched.sort(key=lambda x: (x[7] is None, x[7] or ""), reverse=True)
    else:
        enriched.sort(key=lambda x: (x[2].lower(), x[1][0].lower()))

    total = len(enriched)
    page = enriched[offset:offset + limit]

    # Batch cover lookup across ALL name variants on the page, then re-key by album_key.
    all_page_names = [n for entry in page for n in entry[1]]
    cover_by_name = _batch_cover_track_ids(db, all_page_names)
    cover_by_key = {entry[0]: cover_by_name.get(entry[1][0]) for entry in page}
    # If the display name had no tracks (shouldn't happen but be safe), fall back to any variant.
    for entry in page:
        key = entry[0]
        if cover_by_key.get(key) is None:
            for n in entry[1]:
                if n in cover_by_name:
                    cover_by_key[key] = cover_by_name[n]
                    break
    page_keys = [entry[0] for entry in page]
    metadata_map: dict[str, AlbumMetadata] = (
        {
            md.album_key: md
            for md in db.query(AlbumMetadata)
            .filter(AlbumMetadata.album_key.in_(page_keys))
            .all()
        }
        if page_keys
        else {}
    )

    items: list[AlbumResponse] = []
    for key, names, art, year, lbl, cnt, is_comp, _ in page:
        md = metadata_map.get(key)
        items.append(AlbumResponse(
            album_key=key,
            album=names[0],
            artist=art,
            year=year,
            label=lbl,
            track_count=cnt,
            cover_track_id=cover_by_key.get(key),
            is_compilation=is_comp,
            mb_release_id=md.mb_release_id if md else None,
            match_status=md.match_status if md else None,
        ))
    return PaginatedAlbumsResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{album_key}/tracks", response_model=AlbumTracksResponse)
def album_tracks(album_key: str, db: Session = Depends(get_db)) -> AlbumTracksResponse:
    resolved = _find_album_by_key(db, album_key)
    if not resolved:
        raise HTTPException(status_code=404, detail="Album not found")
    album_names, artist, is_comp = resolved

    tracks = (
        db.query(Track)
        .filter(Track.album.in_(album_names))
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
    cover_id = tracks[0].id if tracks else None

    md = db.get(AlbumMetadata, album_key)
    album = AlbumResponse(
        album_key=album_key,
        album=album_names[0],
        artist=artist,
        year=year,
        label=label,
        track_count=len(tracks),
        cover_track_id=cover_id,
        is_compilation=is_comp,
        mb_release_id=md.mb_release_id if md else None,
        match_status=md.match_status if md else None,
    )
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
        album_names, _, _ = resolved
        cover_row = (
            db.query(Track.id)
            .filter(Track.album.in_(album_names))
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
    album_names, artist, _ = resolved
    album_name = album_names[0]

    tracks = (
        db.query(Track)
        .filter(Track.album.in_(album_names))
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
    album_names, artist, _ = resolved
    album_name = album_names[0]

    valid_track_ids = {
        tid for (tid,) in db.query(Track.id).filter(Track.album.in_(album_names)).all()
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
