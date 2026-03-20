"""Generate purchase search URLs for unowned tracks."""

from __future__ import annotations

from urllib.parse import quote_plus

STORES = {
    "beatport": "https://www.beatport.com/search?q={query}",
    "traxsource": "https://www.traxsource.com/search?term={query}",
    "bandcamp": "https://bandcamp.com/search?q={query}",
    "juno": "https://www.junodownload.com/search/?q%5Ball%5D%5B%5D={query}",
}


def generate_purchase_links(artist: str, title: str) -> dict[str, str]:
    """Generate search URLs for all supported stores.

    Args:
        artist: Track artist.
        title: Track title.

    Returns:
        Dict of {store_name: search_url}.
    """
    query = quote_plus(f"{artist} {title}")
    return {store: url.format(query=query) for store, url in STORES.items()}
