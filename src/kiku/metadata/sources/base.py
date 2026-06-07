"""The contract every metadata source implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from kiku.metadata.models import ReleaseCandidate


@runtime_checkable
class MetadataSource(Protocol):
    """A place to look up release metadata.

    Sources differ in how you reach them: Bandcamp takes a pasted album URL,
    MusicBrainz/Discogs take an album+artist query, embedded tags take the
    album's own files. A source implements whichever entry points it supports
    and raises `LookupUnsupported` for the rest.
    """

    name: str

    def available(self) -> bool:
        """False when the source can't be used (e.g. Discogs without a token)."""
        ...

    def search(self, album: str, artist: str, *, limit: int = 3) -> list[ReleaseCandidate]:
        """Find candidate releases by album + artist text."""
        ...

    def fetch_url(self, url: str) -> ReleaseCandidate | None:
        """Build a candidate from a direct release URL (Bandcamp/Discogs)."""
        ...


class LookupUnsupported(RuntimeError):
    """Raised when a source is asked for a lookup mode it doesn't offer."""


class SourceUnavailable(RuntimeError):
    """Raised when a source is configured-off or missing credentials."""
