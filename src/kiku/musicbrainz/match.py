"""Fuzzy match a Kiku album's tracks against a MusicBrainz release tracklist."""

from __future__ import annotations

import re
from typing import Iterable

try:
    from thefuzz import fuzz  # type: ignore
except ImportError:  # pragma: no cover
    fuzz = None


_PAREN_VARIANTS = re.compile(
    r"\(\s*(original mix|extended mix|radio edit|club mix|original|edit|mix)\s*\)",
    re.IGNORECASE,
)
_FEAT = re.compile(r"\s*(feat\.|ft\.|featuring)\s+[^()\[\]]+", re.IGNORECASE)
_REMIX_PAREN = re.compile(r"\([^()]*\bremix\b[^()]*\)", re.IGNORECASE)
_REMIX_BRACKET = re.compile(r"\[[^\[\]]*\bremix\b[^\[\]]*\]", re.IGNORECASE)
_WS = re.compile(r"\s+")


def normalize_title(title: str | None) -> str:
    """Strip parenthetical mix variants, feat. tags, remix suffixes; lowercase + collapse whitespace."""
    if not title:
        return ""
    s = title.lower()
    s = _PAREN_VARIANTS.sub(" ", s)
    s = _FEAT.sub(" ", s)
    s = _REMIX_PAREN.sub(" ", s)
    s = _REMIX_BRACKET.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def _score(a: str, b: str) -> float:
    if fuzz is None:  # pragma: no cover
        return 1.0 if a == b else 0.0
    return float(fuzz.token_set_ratio(a, b)) / 100.0


def match_tracklist(
    kiku_tracks: Iterable[dict],
    mb_recordings: list[dict],
) -> list[dict]:
    """Greedy bipartite match by normalized-title similarity.

    Inputs:
        kiku_tracks: iterable of {"id": int, "title": str}
        mb_recordings: list of {"position": int, "disc": int, "title": str, ...}

    Output: list of per-Kiku-track mapping dicts:
        {"track_id", "mb_position", "mb_disc", "mb_title", "confidence"}

    Tracks with no MB match get mb_position=None and confidence=0.
    """
    kiku_list = list(kiku_tracks)
    # Pre-normalize all titles
    kiku_norm = [(t, normalize_title(t.get("title"))) for t in kiku_list]
    mb_norm = [(r, normalize_title(r.get("title"))) for r in mb_recordings]

    # Score every (kiku, mb) pair
    scored: list[tuple[float, int, int]] = []  # (score, kiku_idx, mb_idx)
    for ki, (_, kn) in enumerate(kiku_norm):
        for mi, (_, mn) in enumerate(mb_norm):
            if not kn or not mn:
                continue
            scored.append((_score(kn, mn), ki, mi))

    scored.sort(reverse=True)
    used_kiku: set[int] = set()
    used_mb: set[int] = set()
    chosen: dict[int, tuple[int, float]] = {}  # kiku_idx -> (mb_idx, score)

    for score, ki, mi in scored:
        if ki in used_kiku or mi in used_mb:
            continue
        chosen[ki] = (mi, score)
        used_kiku.add(ki)
        used_mb.add(mi)

    results: list[dict] = []
    for ki, (kt, _) in enumerate(kiku_norm):
        if ki in chosen:
            mi, score = chosen[ki]
            rec = mb_norm[mi][0]
            results.append({
                "track_id": kt["id"],
                "mb_position": rec.get("position"),
                "mb_disc": rec.get("disc", 1),
                "mb_title": rec.get("title"),
                "confidence": round(score, 3),
            })
        else:
            results.append({
                "track_id": kt["id"],
                "mb_position": None,
                "mb_disc": None,
                "mb_title": None,
                "confidence": 0.0,
            })
    return results
