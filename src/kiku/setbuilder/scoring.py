"""Transition scoring between tracks."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from kiku.config import BPM_TOLERANCE, SCORING_WEIGHTS
from kiku.db.models import Track
from kiku.setbuilder.camelot import harmonic_score
from kiku.setbuilder.constraints import dir_energy_to_numeric, zone_to_numeric

# ── Genre Families ──────────────────────────────────────────────────────
GENRE_FAMILIES: dict[str, list[str]] = {
    "techno": ["techno", "hard techno", "rumble techno", "acid techno",
                "dub techno", "techno groove", "hypno", "hypno techno",
                "classic techno", "deep techno", "hardstyle techno"],
    "house": ["house", "deep house", "tech house", "afro house",
              "funky house", "hard house", "speed house"],
    "groove": ["hard groove", "hardgroove", "light groove", "ghetto groove"],
    "trance": ["trance", "hard trance"],
    "breaks": ["breaks", "dnb", "garage"],
    "electronic": ["electro", "acid", "bounce", "nu disco", "indie dance"],
    "other": ["dub", "new wave", "post punk", "nacional"],
}

# ── Rekordbox Genre → Kiku Family ─────────────────────────────────────
# Maps Rekordbox genre strings (lowercased) to one of the 7 Kiku families.
# Covers all 89 distinct rb_genre values found in the library.
# Ambiguous mappings are annotated with comments.
RB_GENRE_TO_FAMILY: dict[str, str] = {
    # ── Techno ──
    "techno": "techno",
    "techno (raw / deep / hypnotic)": "techno",
    "techno (raw  deep  hypnotic)": "techno",          # encoding variant
    "techno (peak time / driving)": "techno",
    "techno (peak time  driving)": "techno",            # encoding variant
    "techno (peak time / driving / hard)": "techno",
    "hard techno": "techno",
    "minimal": "techno",
    "minimal / deep tech": "techno",
    "minimal  deep tech": "techno",                     # encoding variant
    "deep tech": "techno",
    "peak time": "techno",
    "melodic house & techno": "techno",                 # Beatport category, techno-leaning
    "hypno": "techno",
    # ── House ──
    "house": "house",
    "deep house": "house",
    "tech house": "house",
    "afro house": "house",
    "afro / latin / brazilian": "house",                # Afro house adjacent
    "bass house": "house",
    "electro house": "house",
    "electro house/electroclash": "house",
    "funky house": "house",
    "funky / groove / jackin' house": "house",
    "jackin house": "house",
    "latin house": "house",
    "organic house": "house",
    "organic house / downtempo": "house",               # organic house primary
    "progressive house": "house",
    "soulful house": "house",
    "mainstage": "house",                               # big-room house
    # ── Groove ──
    "disco": "groove",
    "disco / nu-disco": "groove",
    "nu disco": "groove",
    "nu disco / disco": "groove",
    "nu disco / indie dance": "groove",                 # nu disco primary
    "funk/rare groove": "groove",
    "soul / funk / disco": "groove",
    "indie dance": "groove",                            # groove-adjacent
    # ── Trance ──
    "trance": "trance",
    "trance (main floor)": "trance",
    "trance (raw / deep / hypnotic)": "trance",
    "trance (raw  deep  hypnotic)": "trance",           # encoding variant
    "deep trance": "trance",
    "psy-trance": "trance",
    "uplifting trance/progressive trance": "trance",
    "hard dance / hardcore": "trance",                  # hard dance closer to trance family
    # ── Breaks ──
    "breaks": "breaks",
    "breaks / breakbeat / uk bass": "breaks",
    "breaks  breakbeat  uk bass": "breaks",             # encoding variant
    "drum & bass": "breaks",
    "garage": "breaks",
    "uk garage / bassline": "breaks",
    "uk garage  bassline": "breaks",                    # encoding variant
    "dubstep": "breaks",                                # bass music → breaks family
    "bass / club": "breaks",
    "bass  club": "breaks",                             # encoding variant
    "bounce": "breaks",                                 # bass-heavy → breaks
    # ── Electronic ──
    "electro": "electronic",
    "electro (classic / detroit / modern)": "electronic",
    "electronic": "electronic",
    "electronica": "electronic",
    "electronica / downtempo": "electronic",
    "electrónica": "electronic",                        # Spanish variant
    "experimental/electronic": "electronic",
    "ambient / experimental": "electronic",
    "ambient  experimental": "electronic",              # encoding variant
    "balearic/downtempo": "electronic",
    "dub": "electronic",                                # electronic production style
    "dance / electro pop": "electronic",
    "dance/electro pop": "electronic",
    "dance / pop": "electronic",
    "dance  pop": "electronic",                         # encoding variant
    "dance": "electronic",
    "europop": "electronic",
    "loop samples": "electronic",                       # DJ tools
    "dj tools": "electronic",
    # ── Other ──
    "pop": "other",
    "pop/rock": "other",
    "rock": "other",
    "blues": "other",
    "hip-hop/rap": "other",
    "alternativa & indie": "other",
    "indie/alternative": "other",
    "américa latina": "other",
    "latin music": "other",
    "bandas sonoras de cine": "other",                  # film soundtracks
    "world music": "other",
    "underreview": "other",                             # uncategorized
}

# Reverse lookup: genre name → family name
_GENRE_TO_FAMILY: dict[str, str] = {
    genre: family
    for family, members in GENRE_FAMILIES.items()
    for genre in members
}
# Merge Rekordbox mappings (RB map takes priority for shared keys)
_GENRE_TO_FAMILY.update(RB_GENRE_TO_FAMILY)

COMPATIBLE_FAMILIES: set[frozenset[str]] = {
    frozenset({"techno", "groove"}),
    frozenset({"techno", "electronic"}),
    frozenset({"house", "groove"}),
    frozenset({"house", "electronic"}),
}


def genre_to_family(genre: str | None) -> str:
    """Map a genre name to its family. Returns 'other' if unrecognized."""
    if not genre:
        return "other"
    return _GENRE_TO_FAMILY.get(genre.lower().strip(), "other")


def bpm_compatibility(bpm_a: float | None, bpm_b: float | None) -> float:
    """Score BPM compatibility (0-1). Allows ±6% and double/half time."""
    if not bpm_a or not bpm_b or bpm_a <= 0 or bpm_b <= 0:
        return 0.5  # Unknown — neutral

    ratio = bpm_b / bpm_a

    # Check direct compatibility
    diff_pct = abs(ratio - 1.0)
    if diff_pct <= BPM_TOLERANCE:
        return 1.0 - (diff_pct / BPM_TOLERANCE) * 0.3  # 0.7-1.0

    # Check double time
    diff_double = abs(ratio - 2.0)
    if diff_double <= BPM_TOLERANCE:
        return 0.6

    # Check half time
    diff_half = abs(ratio - 0.5)
    if diff_half <= BPM_TOLERANCE:
        return 0.6

    # Larger BPM gap
    if diff_pct <= 0.12:
        return 0.3
    return 0.1


def genre_coherence(genre_a: str | None, genre_b: str | None) -> float:
    """Score genre compatibility between two tracks."""
    if not genre_a or not genre_b:
        return 0.5

    ga = genre_a.lower().strip()
    gb = genre_b.lower().strip()

    if ga == gb:
        return 1.0

    family_a = _GENRE_TO_FAMILY.get(ga)
    family_b = _GENRE_TO_FAMILY.get(gb)

    if family_a and family_b:
        if family_a == family_b:
            return 0.8
        if frozenset({family_a, family_b}) in COMPATIBLE_FAMILIES:
            return 0.5
        return 0.2

    return 0.3


def energy_fit(track: Track, target_energy: float) -> float:
    """Score how well a track's energy matches the target.

    Priority: audio_features.energy (numeric) > resolved zone > 0.5 (neutral).
    """
    # Prefer audio-analyzed energy if available
    if track.audio_features and track.audio_features.energy is not None:
        track_energy = track.audio_features.energy
    else:
        # Use resolved zone (approved > dir_energy > predicted)
        resolved_zone, _source, _conf = track.resolved_energy_zone
        track_energy = zone_to_numeric(resolved_zone)

    if track_energy is None:
        return 0.5  # Unknown — neutral

    diff = abs(track_energy - target_energy)
    return max(0.0, 1.0 - diff * 2.0)


def track_quality(
    track: Track,
    prefer_playlists: list[str] | None = None,
    discovery_density: float = 0.0,
    set_appearance_count: int = 0,
) -> tuple[float, str | None]:
    """Score track quality based on rating, play count, playlist membership, and discovery/density bias (0-1).

    Returns (score, discovery_label). discovery_label is None when no label applies.
    """
    score = 0.0

    # Rating: 0-5 stars, normalize to 0-1 (unrated gets 0.3)
    if track.rating and track.rating > 0:
        score += 0.4 * (track.rating / 5.0)
    else:
        score += 0.4 * 0.3

    # Play familiarity (20% of track_quality)
    combined_plays = min((track.play_count or 0) + (track.kiku_play_count or 0), 10)
    ratio = combined_plays / 10.0
    dd = discovery_density
    if dd < 0:
        alpha = abs(dd)
        play_signal = (1 - alpha) * ratio + alpha * (1 - ratio)
    elif dd > 0:
        alpha = dd
        play_signal = (1 - alpha) * ratio + alpha * (ratio ** 0.5)
    else:
        play_signal = ratio
    score += 0.2 * play_signal

    # Set density (10% of track_quality)
    density = min(set_appearance_count, 6) / 6.0
    if dd < 0:
        alpha = abs(dd)
        density_signal = (1 - alpha) * density + alpha * (1 - density)
    elif dd > 0:
        alpha = dd
        density_signal = (1 - alpha) * density + alpha * (density ** 0.5)
    else:
        density_signal = density
    score += 0.1 * density_signal

    # Playlist membership boost
    if prefer_playlists and track.playlist_tags:
        try:
            tags = json.loads(track.playlist_tags)
            matching = sum(1 for t in tags if any(p.lower() in t.lower() for p in prefer_playlists))
            score += 0.3 * min(matching / len(prefer_playlists), 1.0)
        except (json.JSONDecodeError, TypeError):
            pass

    # Compute discovery label
    discovery_label: str | None = None
    if dd < -0.3 and combined_plays <= 1:
        discovery_label = "fresh pick"
    elif dd < -0.3 and combined_plays <= 4:
        discovery_label = "rarely played"
    elif dd > 0.3 and set_appearance_count >= 2:
        discovery_label = "battle-tested"
    elif dd > 0.3 and combined_plays >= 7:
        discovery_label = "crowd favorite"

    return score, discovery_label


def transition_score(
    from_track: Track,
    to_track: Track,
    target_energy: float = 0.5,
    prefer_playlists: list[str] | None = None,
    weights: dict[str, float] | None = None,
    discovery_density: float = 0.0,
    set_appearance_counts: dict[int, int] | None = None,
) -> float:
    """Compute overall transition score between two tracks.

    Args:
        weights: Optional per-request weight overrides. Falls back to global SCORING_WEIGHTS.
    """
    w = weights if weights is not None else SCORING_WEIGHTS

    h = harmonic_score(from_track.key, to_track.key)
    e = energy_fit(to_track, target_energy)
    b = bpm_compatibility(from_track.bpm, to_track.bpm)
    g = genre_coherence(
        from_track.dir_genre or from_track.rb_genre,
        to_track.dir_genre or to_track.rb_genre,
    )
    sac = (set_appearance_counts or {}).get(to_track.id, 0)
    q, _ = track_quality(to_track, prefer_playlists, discovery_density, sac)

    return (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
            + w["genre_coherence"] * g + w["track_quality"] * q)


def score_replacement(
    candidate: Track,
    prev_track: Track | None,
    next_track: Track | None,
    target_energy: float = 0.5,
    weights: dict[str, float] | None = None,
    discovery_density: float = 0.0,
    set_appearance_counts: dict[int, int] | None = None,
) -> tuple[float, dict | None, dict | None]:
    """Score a candidate as a replacement considering both neighbors.

    Returns (combined_score, incoming_breakdown, outgoing_breakdown).
    Breakdowns are dicts with keys: harmonic, energy_fit, bpm_compat, genre_coherence, track_quality, total.
    """
    w = weights if weights is not None else SCORING_WEIGHTS

    def _breakdown(from_t: Track, to_t: Track) -> dict:
        h = harmonic_score(from_t.key, to_t.key)
        e = energy_fit(to_t, target_energy)
        b = bpm_compatibility(from_t.bpm, to_t.bpm)
        g = genre_coherence(
            from_t.dir_genre or from_t.rb_genre,
            to_t.dir_genre or to_t.rb_genre,
        )
        sac = (set_appearance_counts or {}).get(to_t.id, 0)
        q, label = track_quality(to_t, discovery_density=discovery_density, set_appearance_count=sac)
        total = (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
                 + w["genre_coherence"] * g + w["track_quality"] * q)
        return {
            "harmonic": round(h, 3),
            "energy_fit": round(e, 3),
            "bpm_compat": round(b, 3),
            "genre_coherence": round(g, 3),
            "track_quality": round(q, 3),
            "total": round(total, 3),
            "discovery_label": label,
            "set_appearances": sac,
        }

    incoming = _breakdown(prev_track, candidate) if prev_track else None
    outgoing = _breakdown(candidate, next_track) if next_track else None

    if incoming and outgoing:
        combined = (incoming["total"] + outgoing["total"]) / 2
    elif incoming:
        combined = incoming["total"]
    elif outgoing:
        combined = outgoing["total"]
    else:
        combined, _ = track_quality(candidate, discovery_density=discovery_density)

    return round(combined, 3), incoming, outgoing


def score_transitions(
    session: Session,
    from_track: Track,
    n: int = 10,
    genre_filter: list[str] | None = None,
    weights: dict[str, float] | None = None,
    exclude_ids: list[int] | None = None,
    discovery_density: float = 0.0,
    set_appearance_counts: dict[int, int] | None = None,
) -> list[tuple[Track, float]]:
    """Find and score best transitions from a given track."""
    q = session.query(Track).filter(Track.id != from_track.id)

    if exclude_ids:
        q = q.filter(Track.id.notin_(exclude_ids))

    # BPM pre-filter
    if from_track.bpm and from_track.bpm > 0:
        bpm_lo = from_track.bpm * (1 - BPM_TOLERANCE * 2)
        bpm_hi = from_track.bpm * (1 + BPM_TOLERANCE * 2)
        q = q.filter(Track.bpm.between(bpm_lo, bpm_hi))

    if genre_filter:
        genre_conditions = [Track.dir_genre.ilike(f"%{g}%") for g in genre_filter]
        q = q.filter(
            Track.dir_genre.isnot(None),
            *[],  # SQLAlchemy or_
        )
        from sqlalchemy import or_
        q = q.filter(or_(*genre_conditions))

    candidates = q.all()

    scored = []
    for track in candidates:
        score = transition_score(from_track, track, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts)
        scored.append((track, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]
