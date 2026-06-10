"""Candidate gating — never attach a cover that isn't this release.

Same precision discipline as the fix-album discovery path: token_sort_ratio
(which, unlike token_set_ratio, doesn't reward a candidate whose title is a
subset of ours) at a high threshold, on BOTH artist and album. Compilations
("Various Artists") have no meaningful album-artist, so they match on album alone.
"""

from __future__ import annotations

from kiku.musicbrainz.match import normalize_title

try:
    from thefuzz import fuzz  # type: ignore
except ImportError:  # pragma: no cover
    fuzz = None

THRESHOLD = 0.85

_VARIOUS = {"", "various", "various artists", "va", "v/a"}


def _ratio(a: str, b: str) -> float:
    if fuzz is None:  # pragma: no cover
        return 1.0 if a == b else 0.0
    return float(fuzz.token_sort_ratio(a, b)) / 100.0


def is_various(artist: str | None) -> bool:
    return (artist or "").strip().lower() in _VARIOUS


def score_candidate(
    our_artist: str | None,
    our_album: str | None,
    cand_artist: str | None,
    cand_album: str | None,
) -> float:
    """0..1 confidence that the candidate is our release.

    Album similarity is required; artist similarity is averaged in unless we're a
    compilation (then album alone decides). A candidate that fails the album test
    scores 0 so it can never win.
    """
    album_score = _ratio(normalize_title(our_album), normalize_title(cand_album))
    if album_score < THRESHOLD:
        return 0.0
    if is_various(our_artist):
        return album_score
    artist_score = _ratio(normalize_title(our_artist), normalize_title(cand_artist))
    if artist_score < THRESHOLD:
        return 0.0
    return (album_score + artist_score) / 2.0


def accept(score: float) -> bool:
    return score >= THRESHOLD
