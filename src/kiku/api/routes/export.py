"""Export endpoints for DJ sets."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.db.models import Set, TransitionCue
from kiku.export.rekordbox_xml import export_set_to_xml

router = APIRouter(prefix="/api/sets", tags=["export"])


@router.post("/{set_id}/export/m3u8")
def export_m3u8(
    set_id: int,
    platform: str = "macos",
    with_metadata: bool = False,
    db: Session = Depends(get_db),
):
    s = db.get(Set, set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    from kiku.export.m3u8 import export_set_to_m3u8

    result = export_set_to_m3u8(
        s,
        target_platform=platform,
        with_metadata=with_metadata,
    )
    return FileResponse(
        path=result.path,
        media_type="audio/x-mpegurl",
        filename=f"{s.name or 'set'}.m3u8",
        headers=_skip_headers(result),
    )


@router.post("/{set_id}/export/rekordbox")
def export_rekordbox(set_id: int, db: Session = Depends(get_db)):
    s = db.get(Set, set_id)
    if not s:
        raise HTTPException(status_code=404, detail="Set not found")

    # Gather cues
    cues = (
        db.query(TransitionCue)
        .filter(TransitionCue.set_id == set_id)
        .order_by(TransitionCue.track_id, TransitionCue.start_sec)
        .all()
    )
    transition_cues = None
    if cues:
        transition_cues: dict[int, list[dict]] = {}
        for c in cues:
            transition_cues.setdefault(c.track_id, []).append(
                {
                    "name": c.name,
                    "type": c.cue_type,
                    "start": c.start_sec,
                    "end": c.end_sec,
                    "num": c.hot_cue_num,
                }
            )

    result = export_set_to_xml(s, transition_cues=transition_cues)
    return FileResponse(
        path=result.path,
        media_type="application/xml",
        filename=f"{s.name or 'set'}.xml",
        headers=_skip_headers(result),
    )


def _skip_headers(result) -> dict[str, str]:
    """Tracks with no file can't be in the playlist — say so in the response.

    A downloaded file has nowhere to carry a message, so the count and the list
    ride along as headers and the UI surfaces them next to the download.
    """
    if not result.skipped:
        return {}
    listing = "; ".join(f"{s.artist or '?'} - {s.title} ({s.reason})" for s in result.skipped)
    return {
        "X-Kiku-Skipped-Count": str(len(result.skipped)),
        # Header values must be latin-1; a title with an em dash would 500 the
        # response otherwise.
        "X-Kiku-Skipped": listing.encode("ascii", "replace").decode("ascii"),
    }
