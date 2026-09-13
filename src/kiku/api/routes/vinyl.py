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
    TrackResponse,
    VinylImportRequest,
    VinylImportResponse,
    VinylPreviewResponse,
    VinylPreviewRow,
    VinylReleaseDetail,
    VinylReleaseSummary,
    VinylSearchResponse,
    VinylSearchResult,
    VinylSide,
    VinylSidePatch,
    VinylTwinRef,
    VinylTwinRequest,
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

    from kiku.vinyl.twins import link_release

    link_release(db, release)
    db.commit()

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


@router.get("/releases/{release_id}", response_model=VinylReleaseDetail)
def vinyl_release_detail(release_id: int, db: Session = Depends(get_db)):
    """One record, the sides on it in pressing order, and which you own as files.

    Suggestions are worked out on read and never stored: a guess that goes stale
    when the library changes is worse than one recomputed in a tenth of a second.
    """
    from kiku.vinyl.twins import match_release

    release = _release_or_404(db, release_id)
    rows = _sides_of(db, release_id)
    digital = _tracks_by_id(db, [t.duplicate_of_track_id for t in rows])
    suggestions = {g.vinyl_track_id: g.digital for g in match_release(db, release).suggestions}
    return VinylReleaseDetail(
        release=_summary(db, release),
        sides=[_side(t, digital.get(t.duplicate_of_track_id), suggestions.get(t.id)) for t in rows],
    )


@router.get("/releases/{release_id}/digital", response_model=list[TrackResponse])
def vinyl_release_digital(release_id: int, db: Session = Depends(get_db)):
    """The files behind a record, in pressing order — what "play" plays."""
    from kiku.api.routes.tracks import _track_to_response

    _release_or_404(db, release_id)
    rows = _sides_of(db, release_id)
    digital = _tracks_by_id(db, [t.duplicate_of_track_id for t in rows])
    return [
        _track_to_response(digital[t.duplicate_of_track_id], t)
        for t in rows
        if t.duplicate_of_track_id in digital
    ]


@router.patch("/sides/{track_id}", response_model=VinylSide)
def vinyl_side_patch(track_id: int, patch: VinylSidePatch, db: Session = Depends(get_db)):
    """Correct a side by hand.

    Anything set here is `manual` — it outranks every automatic source, so a
    wrong estimate stays corrected.
    """
    from kiku.vinyl.importer import set_manual_bpm_key

    _vinyl_side_or_404(db, track_id)
    duration = None
    if patch.length:
        try:
            mins, _, secs = patch.length.partition(":")
            duration = int(mins) * 60 + int(secs or 0)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"'{patch.length}' doesn't look like a length — try 6:12."
            ) from None

    try:
        track = set_manual_bpm_key(
            db, track_id, bpm=patch.bpm, key=patch.key, duration_sec=duration, source="manual"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return _side_with_twin(db, track)


@router.put("/sides/{track_id}/twin", response_model=VinylSide)
def vinyl_side_link(track_id: int, req: VinylTwinRequest, db: Session = Depends(get_db)):
    """This side is that file. Its BPM and key come from your analysis unless you typed them."""
    from kiku.vinyl.twins import link

    side = _vinyl_side_or_404(db, track_id)
    digital = db.get(Track, req.digital_track_id)
    if digital is None:
        raise HTTPException(status_code=404, detail="That file isn't in your library any more.")
    try:
        link(db, side, digital)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    db.commit()
    return _side_with_twin(db, side)


@router.delete("/sides/{track_id}/twin/{digital_track_id}", response_model=VinylSide)
def vinyl_side_unlink(track_id: int, digital_track_id: int, db: Session = Depends(get_db)):
    """ "Not it" — unlinks the file if it was linked, and never suggests it again."""
    from kiku.vinyl.twins import reject

    side = _vinyl_side_or_404(db, track_id)
    reject(db, side, digital_track_id)
    db.commit()
    return _side_with_twin(db, side)


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
        digital=sum(1 for t in sides if t.duplicate_of_track_id),
    )


def _release_or_404(db: Session, release_id: int) -> VinylRelease:
    release = db.get(VinylRelease, release_id)
    if release is None:
        raise HTTPException(status_code=404, detail=f"No record #{release_id} on the shelf.")
    return release


def _vinyl_side_or_404(db: Session, track_id: int) -> Track:
    track = db.get(Track, track_id)
    if track is None or track.medium != "vinyl":
        raise HTTPException(status_code=404, detail="That side isn't on the shelf.")
    return track


def _sides_of(db: Session, release_id: int) -> list[Track]:
    return (
        db.query(Track)
        .filter(Track.vinyl_release_id == release_id)
        .order_by(Track.disc_number, Track.track_number, Track.id)
        .all()
    )


def _tracks_by_id(db: Session, ids: list[int | None]) -> dict[int, Track]:
    wanted = {i for i in ids if i}
    if not wanted:
        return {}
    return {t.id: t for t in db.query(Track).filter(Track.id.in_(wanted))}


def _twin_ref(t: Track | None) -> VinylTwinRef | None:
    if t is None:
        return None
    return VinylTwinRef(track_id=t.id, title=t.title, artist=t.artist, album=t.album)


def _side(t: Track, digital: Track | None = None, suggestion=None) -> VinylSide:
    return VinylSide(
        track_id=t.id,
        position=t.vinyl_position,
        side=t.disc_number,
        index=t.track_number,
        title=t.title,
        artist=t.artist,
        bpm=t.bpm,
        key=t.key,
        duration_sec=t.duration_sec,
        bpm_source=t.bpm_source,
        key_source=t.key_source,
        enrichment_status=t.enrichment_status,
        digital=_twin_ref(digital),
        suggestion=(
            VinylTwinRef(
                track_id=suggestion.id,
                title=suggestion.title,
                artist=suggestion.artist,
                album=suggestion.album,
            )
            if suggestion is not None and digital is None
            else None
        ),
    )


def _side_with_twin(db: Session, t: Track) -> VinylSide:
    """A side after an edit. The suggestion isn't recomputed — the record view
    refetches when it needs one."""
    digital = db.get(Track, t.duplicate_of_track_id) if t.duplicate_of_track_id else None
    return _side(t, digital)
