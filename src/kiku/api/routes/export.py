"""Export endpoints for DJ sets."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.db.models import Set, TransitionCue
from kiku.export.rekordbox_xml import export_set_to_xml

router = APIRouter(prefix="/api/sets", tags=["export"])


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
            transition_cues.setdefault(c.track_id, []).append({
                "name": c.name,
                "type": c.cue_type,
                "start": c.start_sec,
                "end": c.end_sec,
                "num": c.hot_cue_num,
            })

    output_path = export_set_to_xml(s, transition_cues=transition_cues)
    return FileResponse(
        path=str(output_path),
        media_type="application/xml",
        filename=f"{s.name or 'set'}.xml",
    )
