"""Audio streaming endpoint with Range request support.

Browsers can't play AIFF, so AIFF (and anything else non-native) is converted
once to a 16-bit WAV in a small on-disk cache and served from there. A cached
file supports Range requests, so seeking works; a live transcode pipe doesn't.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.config import CONFIG_DIR
from kiku.db.models import Track
from kiku.db.sync import _normalize_path

router = APIRouter(prefix="/api/audio", tags=["audio"])

MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
}

# Formats browsers can play natively
BROWSER_NATIVE = set(MIME_TYPES)

AUDIO_CACHE_DIR = CONFIG_DIR / "cache" / "audio"
AUDIO_CACHE_MAX_BYTES = 4 * 1024**3  # ~80 tracks of 16-bit WAV
_prune_lock = threading.Lock()


@router.get("/{track_id}")
def stream_audio(track_id: int, db: Session = Depends(get_db)):
    track = db.get(Track, track_id)
    if not track or not track.file_path:
        raise HTTPException(status_code=404, detail="Track not found")

    path = Path(_normalize_path(track.file_path))
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    suffix = path.suffix.lower()
    if suffix in BROWSER_NATIVE:
        return FileResponse(path=str(path), media_type=MIME_TYPES[suffix])

    return FileResponse(path=str(_cached_wav(path)), media_type="audio/wav")


def _cached_wav(path: Path) -> Path:
    """Return a WAV copy of `path`, converting it on first request."""
    st = path.stat()
    key = hashlib.sha1(f"{path}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()
    target = AUDIO_CACHE_DIR / f"{key}.wav"

    if target.exists():
        os.utime(target)  # mark as recently used for pruning
        return target

    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f".{os.getpid()}-{threading.get_ident()}.tmp")
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(tmp),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Couldn't convert {path.name} for playback: {result.stderr.strip()[-300:]}",
        )
    os.replace(tmp, target)
    with _prune_lock:
        _prune_cache(keep=target)
    return target


def _prune_cache(keep: Path) -> None:
    """Drop least-recently-used WAVs until the cache fits its budget."""
    files = sorted(
        (f for f in AUDIO_CACHE_DIR.glob("*.wav") if f != keep),
        key=lambda f: f.stat().st_mtime,
    )
    total = keep.stat().st_size + sum(f.stat().st_size for f in files)
    for f in files:
        if total <= AUDIO_CACHE_MAX_BYTES:
            break
        total -= f.stat().st_size
        f.unlink(missing_ok=True)
