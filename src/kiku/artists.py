"""Artist-string token matcher.

Splits a plain ``artist`` string into normalized whole-word tokens so a
requested artist matches collaborations (e.g. "Bicep" matches
"Bicep & Chroma" and "X feat. Bicep") but NOT substrings ("Bicepz", "Maxx").

Shared utility: Phases B (build preferences) and C (multi-anchor pins) reuse it.
"""

from __future__ import annotations

import re

# Word-boundary separators. Punctuation separators (,&+/) are literal and
# may sit flush against names. Word separators (feat/ft/vs/x/with) match only
# as whole words flanked by whitespace, so "Maxx"/"Sixx" are never split and a
# leading/trailing bare "X" artist token survives. ``feat``/``ft``/``vs``
# tolerate an optional trailing dot.
_SEPARATOR_RE = re.compile(
    r"(?:\s*(?:,|&|\+|/)\s*)"
    r"|(?:\s+(?:feat\.?|ft\.?|vs\.?|x|with)\s+)",
    re.IGNORECASE,
)


def artist_tokens(s: str | None) -> set[str]:
    """Split an artist string into normalized whole-name tokens.

    Lowercased, whitespace-trimmed, empties dropped. Returns an empty set
    for None/blank input.
    """
    if not s:
        return set()
    parts = _SEPARATOR_RE.split(s)
    return {p.strip().lower() for p in parts if p and p.strip()}


def artist_matches(requested: str | None, candidate_artist: str | None) -> bool:
    """True when the requested artist is one of the candidate's tokens.

    Both sides are tokenized; a match needs the (single) requested token to
    be present among the candidate's tokens. Case- and whitespace-insensitive.
    """
    req = artist_tokens(requested)
    if not req:
        return False
    cand = artist_tokens(candidate_artist)
    return bool(req & cand)
