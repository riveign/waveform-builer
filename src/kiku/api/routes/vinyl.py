"""Putting a record on the shelf, from the browser.

Search is deliberately cheap: Discogs' search response already carries the
sleeve, catalogue number, year, label and format, so the picker is built from
one call. The full release — and its tracklist — is fetched only for the
pressing the DJ actually picks.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    VinylImportRequest,
    VinylImportResponse,
    VinylPreviewResponse,
    VinylPreviewRow,
    VinylReleaseSummary,
    VinylSearchResponse,
    VinylSearchResult,
)
from kiku.db.models import Track, VinylRelease

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vinyl", tags=["vinyl"])


@router.get("/search", response_model=VinylSearchResponse)
def vinyl_search(
    q: str = Query(..., min_length=1, description="Catalogue number, barcode, artist, or title"),
    vinyl_only: bool = True,
    limit: int = 12,
    db: Session = Depends(get_db),
):
    """Find a pressing. One Discogs call, everything the picker needs."""
    from kiku.metadata.sources.discogs import DiscogsSource
    from kiku.vinyl.search import detect_query, search_pressings

    src = DiscogsSource()
    if not src.available():
        raise HTTPException(
            status_code=503,
            detail="Discogs isn't set up yet — add a token with `kiku config set discogs.token <TOKEN>`.",
        )

    kind = detect_query(q)
    try:
        results = search_pressings(src, q, kind=kind, vinyl_only=vinyl_only, limit=limit)
    except Exception:
        logger.exception("Discogs search failed for %r", q)
        raise HTTPException(
            status_code=502, detail="Couldn't reach Discogs just now — try that again."
        ) from None

    owned = {
        r.discogs_release_id
        for r in db.query(VinylRelease.discogs_release_id).all()
        if r.discogs_release_id
    }
    return VinylSearchResponse(
        query=q,
        kind=kind,
        results=[
            VinylSearchResult(**{**r, "already_owned": str(r["id"]) in owned}) for r in results
        ],
    )


@router.get("/preview", response_model=VinylPreviewResponse)
def vinyl_preview(
    release_id: str | None = None,
    url: str | None = None,
    fill_bpm: bool = True,
    db: Session = Depends(get_db),
):
    """The tracklist, with every BPM Kiku can work out before you type one.

    `url` accepts a Discogs or Bandcamp release link, for records the search
    can't find — which is most white labels.
    """
    from kiku.vinyl.importer import build_preview, is_a_pressing
    from kiku.vinyl.resolve import candidate_from_release_id, candidate_from_url

    if not release_id and not url:
        raise HTTPException(status_code=400, detail="Give me a release id or a link.")

    try:
        candidate = candidate_from_url(url) if url else candidate_from_release_id(release_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception:
        logger.exception("Release lookup failed (release_id=%s url=%s)", release_id, url)
        raise HTTPException(
            status_code=502, detail="Couldn't read that release — try the link again."
        ) from None

    if candidate is None:
        raise HTTPException(status_code=404, detail="Nothing at that link.")

    preview = build_preview(db, candidate)
    rows = [
        VinylPreviewRow(
            position=r.position_raw,
            side=r.side,
            index=r.index,
            title=r.title,
            artist=r.artist,
            duration_sec=r.duration_sec,
            already_on_shelf=r.existing_track_id is not None,
        )
        for r in preview.rows
    ]

    if fill_bpm:
        _fill_bpms(db, candidate.artist, rows, genre=candidate.genre)

    return VinylPreviewResponse(
        source=candidate.source,
        source_id=candidate.source_id,
        album=candidate.album,
        artist=candidate.artist,
        label=candidate.label,
        catalog_number=candidate.catalog_number,
        year=candidate.year,
        country=candidate.country,
        format=candidate.format,
        cover_url=candidate.cover_url,
        genre=candidate.genre,
        is_pressing=is_a_pressing(candidate.format),
        already_owned=preview.is_reimport,
        rows=rows,
    )


def _fill_bpms(
    db: Session,
    album_artist: str | None,
    rows: list[VinylPreviewRow],
    *,
    genre: str | None = None,
) -> None:
    """Walk the provenance ladder for each side, sharing one HTTP client.

    The tempo prior is drawn from the part of the library that resembles this
    record. Using the whole library pushed a 1971 rock LP's correct 103 BPM up
    to 154.5, because a techno collection recognises 155 and does not recognise
    103.
    """
    import httpx

    from kiku.vinyl.bpm import USER_AGENT, find_bpm, library_tempo_prior

    prior = library_tempo_prior(db, genre=genre)
    with httpx.Client(
        timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        for row in rows:
            finding = find_bpm(
                db,
                row.artist or album_artist,
                row.title,
                prior=prior,
                genre=genre,
                client=client,
            )
            row.bpm = finding.bpm
            row.key = finding.key
            row.bpm_source = finding.source
            row.bpm_note = finding.note
            row.matched_track_id = finding.matched_track_id


@router.post("/import", response_model=VinylImportResponse)
def vinyl_import(req: VinylImportRequest, db: Session = Depends(get_db)):
    """Write the pressing and its sides, with whatever numbers the DJ confirmed."""
    from kiku.vinyl.importer import NotAPressing, apply_import, set_manual_bpm_key
    from kiku.vinyl.resolve import candidate_from_release_id, candidate_from_url

    try:
        candidate = (
            candidate_from_url(req.url) if req.url else candidate_from_release_id(req.release_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    if candidate is None:
        raise HTTPException(status_code=404, detail="Nothing at that link.")

    try:
        release = apply_import(
            db, candidate, acquired_on=req.acquired_on, notes=req.notes, force=req.force
        )
    except NotAPressing as e:
        raise HTTPException(status_code=409, detail=str(e)) from None

    # Numbers the DJ kept, each stamped with the rung it came off. Only what was
    # typed or confirmed is `manual`; an estimate stays an estimate, so a better
    # source later is still allowed to improve it.
    applied = 0
    for side in req.sides or []:
        if side.bpm is None and not side.key:
            continue
        track = (
            db.query(Track)
            .filter(Track.vinyl_release_id == release.id, Track.vinyl_position == side.position)
            .first()
        )
        if track is None:
            continue
        try:
            set_manual_bpm_key(
                db, track.id, bpm=side.bpm, key=side.key, source=side.source or "manual"
            )
            applied += 1
        except ValueError:
            logger.warning("Rejected BPM %s for side %s", side.bpm, side.position)

    sides = db.query(Track).filter(Track.vinyl_release_id == release.id).all()
    return VinylImportResponse(
        release=_summary(db, release),
        sides_written=len(sides),
        bpms_applied=applied,
        unplannable=sum(1 for t in sides if not t.bpm),
    )


@router.get("/releases", response_model=list[VinylReleaseSummary])
def vinyl_releases(db: Session = Depends(get_db)):
    """The shelf."""
    rows = db.query(VinylRelease).order_by(VinylRelease.artist, VinylRelease.title).all()
    return [_summary(db, r) for r in rows]


@router.delete("/releases/{release_id}", status_code=204)
def vinyl_release_delete(release_id: int, db: Session = Depends(get_db)):
    """Take a record off the shelf, with the sides that came in with it."""
    from kiku.vinyl.importer import remove_release

    try:
        remove_release(db, release_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def _summary(db: Session, release: VinylRelease) -> VinylReleaseSummary:
    sides = db.query(Track).filter(Track.vinyl_release_id == release.id).all()
    return VinylReleaseSummary(
        id=release.id,
        title=release.title,
        artist=release.artist,
        label=release.label,
        catalog_number=release.catalog_number,
        year=release.year,
        format=release.format,
        cover_url=release.cover_url,
        side_count=release.side_count,
        sides=len(sides),
        plannable=sum(1 for t in sides if t.bpm),
        without_length=sum(1 for t in sides if not t.duration_sec),
    )
