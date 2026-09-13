"""Turn "here's where I found it" into a tracklist.

There is no universal trick. Measured against real shops: Hardwax publishes no
structured data at all, Boomkat returns 403 to anything automated, and Juno and
Beatport put the tracklist behind no pattern worth trusting. So each site is its
own small reader, and every one of them breaks the day that shop redesigns.

Which is why this module fails *loudly* — a link it can't read comes back as a
clear "I couldn't read that", never as a half-empty record. The floor underneath
it all is the DJ typing the sides in, because a white label is on no website.
"""

from __future__ import annotations

import logging
import re

from kiku.metadata.models import ReleaseCandidate

logger = logging.getLogger(__name__)

_DISCOGS_RE = re.compile(r"discogs\.com/.*?release/(\d+)", re.IGNORECASE)
_BANDCAMP_RE = re.compile(r"^https?://[^/]+\.bandcamp\.com/album/", re.IGNORECASE)


class UnreadableLink(ValueError):
    """We reached the page but couldn't find a record in it."""


def candidate_from_release_id(release_id: str | None) -> ReleaseCandidate | None:
    """Read a Discogs release we already know the id of."""
    from kiku.metadata.sources.discogs import DiscogsSource

    if not release_id:
        raise ValueError("No release id given.")
    src = DiscogsSource()
    if not src.available():
        raise ValueError(
            "Discogs isn't set up yet — add a token with `kiku config set discogs.token <TOKEN>`."
        )
    return src.fetch_url(f"https://www.discogs.com/release/{release_id}")


def candidate_from_url(url: str | None) -> ReleaseCandidate | None:
    """Read a release from wherever the DJ found it.

    Discogs and Bandcamp are read properly — Kiku already understands both.
    Anything else is refused by name rather than half-parsed, so the DJ knows to
    type it in instead of trusting a record that only looks complete.
    """
    if not url or not url.strip():
        raise ValueError("No link given.")
    url = url.strip()

    if _DISCOGS_RE.search(url):
        from kiku.metadata.sources.discogs import DiscogsSource

        src = DiscogsSource()
        if not src.available():
            raise ValueError(
                "That's a Discogs link, but Discogs isn't set up yet — "
                "add a token with `kiku config set discogs.token <TOKEN>`."
            )
        return src.fetch_url(url)

    if _BANDCAMP_RE.match(url):
        from kiku.metadata.sources.bandcamp import BandcampSource

        return BandcampSource().fetch_url(url)

    raise UnreadableLink(
        "Kiku can read Discogs and Bandcamp links. For anywhere else, type the "
        "record in yourself — sides and titles — and it'll work just the same."
    )


def readable_sources() -> list[dict]:
    """What a pasted link can be, and how completely it can be read.

    Surfaced to the UI so the promise on screen matches what actually works.
    """
    from kiku.metadata.sources.discogs import DiscogsSource

    return [
        {
            "name": "Discogs",
            "reads": "full tracklist",
            "available": DiscogsSource().available(),
            "example": "https://www.discogs.com/release/28715971",
        },
        {
            "name": "Bandcamp",
            "reads": "full tracklist",
            "available": True,
            "example": "https://label.bandcamp.com/album/the-ep",
        },
    ]
