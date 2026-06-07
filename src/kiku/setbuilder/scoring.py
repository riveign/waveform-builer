"""Transition scoring between tracks."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from kiku.config import BPM_TOLERANCE, SCORING_WEIGHTS
from kiku.db.models import Track
from kiku.setbuilder.camelot import harmonic_score
from kiku.setbuilder.constraints import dir_energy_to_numeric, zone_to_numeric
from kiku.vibe import resolve_vibe, vibe_distance

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
    frozenset({"house", "trance"}),       # progressive house <-> trance
    frozenset({"groove", "electronic"}),   # disco/funk <-> electronica
    frozenset({"breaks", "electronic"}),   # breakbeat <-> electronic
    frozenset({"techno", "trance"}),       # hard trance <-> techno overlap
}

# Keyword fallback for dir_genre values not in _GENRE_TO_FAMILY.
# Order matters: more specific keywords first to avoid false positives.
_KEYWORD_FALLBACKS: list[tuple[str, str]] = [
    ("techno", "techno"),
    ("house", "house"),
    ("trance", "trance"),
    ("breakbeat", "breaks"),
    ("drum and bass", "breaks"),
    ("dnb", "breaks"),
    ("breaks", "breaks"),
    ("groove", "groove"),
    ("disco", "groove"),
    ("funk", "groove"),
    ("hypno", "techno"),
]


def genre_to_family(genre: str | None) -> str:
    """Map a genre name to its family. Returns 'other' if unrecognized.

    Tries exact dict lookup first, then keyword-based fallback for
    dir_genre values like "Hard Techno Dark", "Techno Acid", "House Deep".
    """
    if not genre:
        return "other"
    key = genre.lower().strip()
    # Exact match (covers both GENRE_FAMILIES and RB_GENRE_TO_FAMILY)
    family = _GENRE_TO_FAMILY.get(key)
    if family:
        return family
    # Keyword fallback for custom dir_genre names
    for keyword, fam in _KEYWORD_FALLBACKS:
        if keyword in key:
            return fam
    return "other"


def _resolve_genre_family(track: Track) -> str:
    """Resolve the best genre family for a track.

    Tries dir_genre first, then rb_genre.  Prefers whichever yields a
    non-"other" family so that a rich rb_genre isn't shadowed by an
    unmapped dir_genre folder name.
    """
    for genre_str in [track.dir_genre, track.rb_genre]:
        if genre_str:
            family = genre_to_family(genre_str)
            if family != "other":
                return family
    # Both mapped to "other" or both None — return whatever we got
    return genre_to_family(track.dir_genre or track.rb_genre)


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
    """Score genre compatibility between two tracks.

    Uses genre_to_family() which includes keyword fallback, so custom
    dir_genre names like "Hard Techno Dark" resolve correctly.
    """
    if not genre_a or not genre_b:
        return 0.5

    ga = genre_a.lower().strip()
    gb = genre_b.lower().strip()

    if ga == gb:
        return 1.0

    family_a = genre_to_family(genre_a)
    family_b = genre_to_family(genre_b)

    if family_a == family_b:
        return 0.8
    if frozenset({family_a, family_b}) in COMPATIBLE_FAMILIES:
        return 0.5
    # Both are "other" — we can't tell, give neutral score
    if family_a == "other" and family_b == "other":
        return 0.4
    return 0.2


def genre_momentum_bonus(
    preceding_tracks: list[Track],
    candidate: Track,
    window: int = 3,
) -> float:
    """Bonus/penalty for genre continuity with recent tracks.

    Returns a value in [-0.1, +0.1] that should be added to the
    transition score.  Rewards staying in-family, mildly rewards
    compatible-family moves, penalizes random jumps.
    """
    if not preceding_tracks:
        return 0.0
    recent = preceding_tracks[-window:]
    families = [_resolve_genre_family(t) for t in recent]
    cand_family = _resolve_genre_family(candidate)

    same_count = sum(1 for f in families if f == cand_family)
    compat_count = sum(
        1 for f in families
        if f != cand_family
        and (
            frozenset({f, cand_family}) in COMPATIBLE_FAMILIES
            or f == "other"
            or cand_family == "other"
        )
    )

    ratio = (same_count + 0.5 * compat_count) / len(families)
    # Map ratio to bonus: 1.0 → +0.1, 0.5 → 0.0, 0.0 → -0.1
    return (ratio - 0.5) * 0.2


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


def _best_genre_str(track: Track) -> str | None:
    """Return the genre string that maps to the best (non-'other') family.

    Tries dir_genre first, falls back to rb_genre.  Returns whichever
    maps to a real family, or whichever is available.
    """
    for g in [track.dir_genre, track.rb_genre]:
        if g and genre_to_family(g) != "other":
            return g
    return track.dir_genre or track.rb_genre


# ── Vibe ─────────────────────────────────────────────────────────────────
# Vibe enters scoring as a bounded additive term (like genre-momentum and
# BPM-progression bonuses) so the five normalized weights — and their
# validation and the weights UI — are untouched. At full strength the term
# shifts a transition score by roughly ±0.3.
_VIBE_SPAN = 0.3  # max ± shift at vibe_strength = 1.0


def vibe_target_fit(track: Track, target_vibe: tuple[float, float]) -> float:
    """How close a track's vibe sits to the target vibe (1 = on target)."""
    v = resolve_vibe(track)
    return 1.0 - vibe_distance((v.brightness, v.density), target_vibe)


def vibe_continuity(from_track: Track, to_track: Track) -> float:
    """How smoothly two adjacent tracks' vibes connect (1 = no jump).

    A low score is the jarring dark→happy clash the DJ wants to catch.
    """
    a = resolve_vibe(from_track)
    b = resolve_vibe(to_track)
    return 1.0 - vibe_distance((a.brightness, a.density), (b.brightness, b.density))


def vibe_term(
    from_track: Track | None,
    to_track: Track,
    target_vibe: tuple[float, float] | None,
    vibe_strength: float,
) -> tuple[float, dict | None]:
    """Bounded additive vibe contribution and a breakdown for transparency.

    Returns (contribution, breakdown). contribution is 0.0 when vibe is off.
    """
    if vibe_strength <= 0 or target_vibe is None:
        return 0.0, None
    fit = vibe_target_fit(to_track, target_vibe)
    cont = vibe_continuity(from_track, to_track) if from_track is not None else fit
    # Fit leads (it's what steers toward the chosen vibe); continuity smooths.
    combined = 0.7 * fit + 0.3 * cont
    # Map [0,1] combined → [-span, +span], scaled by strength.
    contribution = vibe_strength * _VIBE_SPAN * (combined - 0.5) * 2.0
    breakdown = {
        "target_fit": round(fit, 3),
        "continuity": round(cont, 3),
        "contribution": round(contribution, 3),
    }
    return contribution, breakdown


def transition_score(
    from_track: Track,
    to_track: Track,
    target_energy: float = 0.5,
    prefer_playlists: list[str] | None = None,
    weights: dict[str, float] | None = None,
    discovery_density: float = 0.0,
    set_appearance_counts: dict[int, int] | None = None,
    target_vibe: tuple[float, float] | None = None,
    vibe_strength: float = 0.0,
) -> float:
    """Compute overall transition score between two tracks.

    Args:
        weights: Optional per-request weight overrides. Falls back to global SCORING_WEIGHTS.
        target_vibe: Optional (brightness, density) target for this point in the set.
        vibe_strength: How strongly vibe steers selection (0 = off, 1 = full).
    """
    w = weights if weights is not None else SCORING_WEIGHTS

    h = harmonic_score(from_track.key, to_track.key)
    e = energy_fit(to_track, target_energy)
    b = bpm_compatibility(from_track.bpm, to_track.bpm)
    # Use _resolve_genre_family to pick the best genre string per track
    from_genre = _best_genre_str(from_track)
    to_genre = _best_genre_str(to_track)
    g = genre_coherence(from_genre, to_genre)
    sac = (set_appearance_counts or {}).get(to_track.id, 0)
    q, _ = track_quality(to_track, prefer_playlists, discovery_density, sac)

    base = (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
            + w["genre_coherence"] * g + w["track_quality"] * q)
    vibe_contribution, _ = vibe_term(from_track, to_track, target_vibe, vibe_strength)
    return base + vibe_contribution


def score_replacement(
    candidate: Track,
    prev_track: Track | None,
    next_track: Track | None,
    target_energy: float = 0.5,
    weights: dict[str, float] | None = None,
    discovery_density: float = 0.0,
    set_appearance_counts: dict[int, int] | None = None,
    target_vibe: tuple[float, float] | None = None,
    vibe_strength: float = 0.0,
) -> tuple[float, dict | None, dict | None]:
    """Score a candidate as a replacement considering both neighbors.

    Returns (combined_score, incoming_breakdown, outgoing_breakdown).
    Breakdowns are dicts with keys: harmonic, energy_fit, bpm_compat,
    genre_coherence, track_quality, vibe, total.
    """
    w = weights if weights is not None else SCORING_WEIGHTS

    def _breakdown(from_t: Track, to_t: Track) -> dict:
        h = harmonic_score(from_t.key, to_t.key)
        e = energy_fit(to_t, target_energy)
        b = bpm_compatibility(from_t.bpm, to_t.bpm)
        g = genre_coherence(
            _best_genre_str(from_t),
            _best_genre_str(to_t),
        )
        sac = (set_appearance_counts or {}).get(to_t.id, 0)
        q, label = track_quality(to_t, discovery_density=discovery_density, set_appearance_count=sac)
        base = (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
                + w["genre_coherence"] * g + w["track_quality"] * q)
        vibe_contribution, vibe_bd = vibe_term(from_t, to_t, target_vibe, vibe_strength)
        return {
            "harmonic": round(h, 3),
            "energy_fit": round(e, 3),
            "bpm_compat": round(b, 3),
            "genre_coherence": round(g, 3),
            "track_quality": round(q, 3),
            "vibe": vibe_bd,
            "total": round(base + vibe_contribution, 3),
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
    target_energy: float = 0.5,
) -> list[tuple[Track, float]]:
    """Find and score best transitions from a given track."""
    q = session.query(Track).filter(Track.id != from_track.id)

    if exclude_ids:
        q = q.filter(Track.id.notin_(exclude_ids))

    # BPM pre-filter — include direct range, double-time, and half-time
    from sqlalchemy import or_ as sql_or

    if from_track.bpm and from_track.bpm > 0:
        tol = BPM_TOLERANCE * 2  # 12% window each side
        bpm = from_track.bpm
        bpm_lo = bpm * (1 - tol)
        bpm_hi = bpm * (1 + tol)
        # Double-time range (e.g. 70 BPM source → 126-154 BPM candidates)
        dbl_lo = (bpm * 2) * (1 - tol)
        dbl_hi = (bpm * 2) * (1 + tol)
        # Half-time range (e.g. 140 BPM source → 61.6-78.4 BPM candidates)
        half_lo = (bpm * 0.5) * (1 - tol)
        half_hi = (bpm * 0.5) * (1 + tol)
        q = q.filter(
            sql_or(
                Track.bpm.between(bpm_lo, bpm_hi),
                Track.bpm.between(dbl_lo, dbl_hi),
                Track.bpm.between(half_lo, half_hi),
                Track.bpm.is_(None),  # don't exclude tracks missing BPM
            )
        )

    if genre_filter:
        genre_conditions = [Track.dir_genre.ilike(f"%{g}%") for g in genre_filter]
        genre_conditions += [Track.rb_genre.ilike(f"%{g}%") for g in genre_filter]
        q = q.filter(sql_or(*genre_conditions))

    candidates = q.all()

    # Load affinities for the source track to boost/penalize suggestions
    affinities = _load_affinities(session, from_track.id)

    scored = []
    for track in candidates:
        score = transition_score(from_track, track, target_energy=target_energy, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts)
        # Apply affinity modifier: "good" → +10%, "bad" → -20%
        aff = affinities.get(track.id)
        if aff == "good":
            score = min(score * 1.10, 1.0)
        elif aff == "bad":
            score = score * 0.80
        scored.append((track, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]


def _load_affinities(session: Session, track_id: int) -> dict[int, str]:
    """Load all affinities for a track as {partner_id: 'good'|'bad'}.

    Returns empty dict if the table doesn't exist yet (pre-migration).
    """
    try:
        from kiku.db.models import TrackAffinity
        from sqlalchemy import or_

        rows = (
            session.query(TrackAffinity)
            .filter(
                or_(
                    TrackAffinity.track_a_id == track_id,
                    TrackAffinity.track_b_id == track_id,
                )
            )
            .all()
        )
        result = {}
        for row in rows:
            partner = row.track_b_id if row.track_a_id == track_id else row.track_a_id
            result[partner] = row.affinity
        return result
    except Exception:
        # Table may not exist yet if migration hasn't run
        return {}
