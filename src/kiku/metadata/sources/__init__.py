"""Source registry — resolve a source by name and list what's usable."""

from __future__ import annotations

from kiku.metadata.sources.bandcamp import BandcampSource
from kiku.metadata.sources.base import MetadataSource
from kiku.metadata.sources.discogs import DiscogsSource
from kiku.metadata.sources.musicbrainz import MusicBrainzSource
from kiku.metadata.sources.tags import TagsSource

# Order = display/priority order in UI and CLI help.
_FACTORIES = {
    "bandcamp": BandcampSource,
    "musicbrainz": MusicBrainzSource,
    "discogs": DiscogsSource,
    "tags": TagsSource,
}

SOURCE_NAMES = tuple(_FACTORIES.keys())

# How each source is reached, surfaced to the UI so it can render the right input.
SOURCE_LOOKUP_MODE = {
    "bandcamp": "url",
    "musicbrainz": "search",
    "discogs": "search",  # also accepts a release URL
    "tags": "files",
}


def get_source(name: str) -> MetadataSource:
    factory = _FACTORIES.get(name)
    if factory is None:
        raise ValueError(f"Unknown metadata source: {name!r} (have {', '.join(SOURCE_NAMES)})")
    return factory()


def available_sources() -> list[dict]:
    """Describe each source for the UI: name, lookup mode, whether usable now."""
    out: list[dict] = []
    for name in SOURCE_NAMES:
        try:
            src = get_source(name)
            avail = src.available()
        except Exception:  # noqa: BLE001
            avail = False
        out.append({
            "name": name,
            "lookup_mode": SOURCE_LOOKUP_MODE[name],
            "available": avail,
        })
    return out


__all__ = ["get_source", "available_sources", "SOURCE_NAMES", "SOURCE_LOOKUP_MODE"]
