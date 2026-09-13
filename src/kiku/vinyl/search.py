"""Work out what the DJ typed, and ask Discogs for it the right way.

A DJ holding a record knows it by whatever is printed on the thing in their
hand: the catalogue number on the spine, the barcode on the sleeve, or just the
one track they remember. Discogs answers all three, but only if you ask with the
matching parameter — measured, `release_title=AF 97&artist=Alarico` returns
nothing while free text finds the record whose A1 that is.
"""

from __future__ import annotations

import re

_BARCODE_RE = re.compile(r"^\d{8,14}$")
_CATNO_RE = re.compile(r"^[A-Za-z]{1,5}[\s\-]?\d{1,4}[A-Za-z]?$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_DASH_RE = re.compile(r"\s[-–]\s")


def detect_query(text: str) -> str:
    """Name the kind of thing the DJ typed, so the UI can say so out loud."""
    t = (text or "").strip()
    if not t:
        return "empty"
    if _URL_RE.match(t):
        return "url"
    if _BARCODE_RE.match(t):
        return "barcode"
    if _CATNO_RE.match(t):
        return "catno"
    if _DASH_RE.search(t):
        return "artist_title"
    return "text"


def _params_for(text: str, kind: str, limit: int, vinyl_only: bool) -> list[dict]:
    """Query shapes to try, best first. Later ones are rescues, not refinements."""
    base: dict = {"type": "release", "per_page": limit}
    if vinyl_only:
        # This is what stops the WAV edition of a record reaching the shelf.
        base["format"] = "Vinyl"

    t = text.strip()
    if kind == "barcode":
        return [{**base, "barcode": t}, {**base, "q": t}]
    if kind == "catno":
        return [{**base, "catno": t}, {**base, "q": t}]
    if kind == "artist_title":
        left, right = (p.strip() for p in _DASH_RE.split(t, 1))
        return [
            {**base, "artist": left, "release_title": right},
            {**base, "q": t},
        ]
    return [{**base, "q": t}]


def search_pressings(
    source, text: str, *, kind: str | None = None, vinyl_only: bool = True, limit: int = 12
) -> list[dict]:
    """Return picker-ready rows, collapsing repressings of the same record.

    Everything here comes out of the search response itself — no per-result
    fetch. The full release is read only once the DJ picks one.
    """
    kind = kind or detect_query(text)
    results: list[dict] = []
    for params in _params_for(text, kind, limit, vinyl_only):
        raw = source._get("/database/search", params=params) or {}
        results = raw.get("results") or []
        if results:
            break

    seen_master: dict[int, dict] = {}
    out: list[dict] = []
    for r in results:
        rid = r.get("id")
        if not rid:
            continue
        row = {
            "id": str(rid),
            "title": _strip_artist(r.get("title")),
            "artist": _artist_from_title(r.get("title")),
            "label": (r.get("label") or [None])[0],
            "catno": r.get("catno"),
            "year": r.get("year"),
            "country": r.get("country"),
            "format": ", ".join(r.get("format") or []) or None,
            "cover_url": r.get("cover_image") or r.get("thumb"),
            "have": (r.get("community") or {}).get("have"),
            "genre": ", ".join(r.get("style") or r.get("genre") or []) or None,
            "pressings": 1,
        }
        # Discogs lists every repressing separately. They are the same record to
        # a DJ, so collapse them and say how many there were.
        master = r.get("master_id")
        if master:
            first = seen_master.get(master)
            if first:
                first["pressings"] += 1
                continue
            seen_master[master] = row
        out.append(row)
    return out


def _artist_from_title(title: str | None) -> str | None:
    """Discogs packs "Artist - Release" into one string."""
    if not title or " - " not in title:
        return None
    artist = title.split(" - ", 1)[0].strip()
    return re.sub(r"\s*\(\d+\)$", "", artist) or None


def _strip_artist(title: str | None) -> str | None:
    if not title:
        return None
    return title.split(" - ", 1)[1].strip() if " - " in title else title.strip()
