"""On-demand album cover art resolution.

A cover resolver that tries sources in order — disk cache → embedded tags →
Cover Art Archive (only when an MB release is already known) → iTunes → Deezer —
caches the winner to disk, and NEVER raises to the caller. Artwork is presentation,
so fetches are silent; the only guardrail against a wrong cover is a fuzzy-match
confidence threshold, and the winning source is always recorded so the UI can show it.
"""

from kiku.artwork.resolver import (
    embedded_cover_bytes,
    resolve_album_cover,
)

__all__ = ["embedded_cover_bytes", "resolve_album_cover"]
