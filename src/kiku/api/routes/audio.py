"""Audio streaming endpoint with Range request support and on-the-fly transcoding."""

from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.db.models import Track
from kiku.db.sync import _normalize_path

router = APIRouter(prefix="/api/audio", tags=["audio"])

MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
}

# Formats browsers can play natively
BROWSER_NATIVE = {".mp3", ".wav", ".ogg", ".m4a"}


@router.get("/{track_id}")
def stream_audio(track_id: int, request: Request, db: Session = Depends(get_db)):
    track = db.get(Track, track_id)
    if not track or not track.file_path:
        raise HTTPException(status_code=404, detail="Track not found")

    path = Path(_normalize_path(track.file_path))
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    suffix = path.suffix.lower()

    # AIFF, FLAC, and other non-native formats: transcode to MP3 via FFmpeg
    if suffix not in BROWSER_NATIVE:
        return _transcode_stream(path)

    # Native formats: serve directly with Range support
    file_size = path.stat().st_size
    content_type = MIME_TYPES.get(suffix, "application/octet-stream")

    range_header = request.headers.get("range")
    if range_header:
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1

        def iter_range():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            iter_range(),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
            },
        )

    return FileResponse(
        path=str(path),
        media_type=content_type,
        headers={"Accept-Ranges": "bytes"},
    )


def _transcode_stream(path: Path) -> StreamingResponse:
    """Transcode audio to MP3 on the fly via FFmpeg."""
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-i", str(path),
            "-f", "mp3",
            "-ab", "192k",
            "-vn",           # no video
            "-loglevel", "error",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    def iter_chunks():
        try:
            while True:
                chunk = proc.stdout.read(8192)
                if not chunk:
                    break
                yield chunk
        finally:
            proc.stdout.close()
            proc.wait()

    return StreamingResponse(
        iter_chunks(),
        media_type="audio/mpeg",
    )
