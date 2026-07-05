"""Directional slot-recommendation ranker.

Given a set, a slot ``position``, a ``mode`` (insert | replace) and a named
directional ``intent`` (push_higher | brighten | cool_down | hold), rank the
DJ's OWN tracks that make that harmonic move while still mixing cleanly out of
the predecessor AND into the FIXED successor. Reuses ``score_replacement`` (the
both-neighbor scorer) — no parallel scorer. Library excavation only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from kiku.config import BPM_TOLERANCE
from kiku.db.models import Set, Track
from kiku.setbuilder.camelot import (
    camelot_str,
    harmonic_score,
    intent_allowed_keys,
    intent_energy_delta,
    move_targets,
    parse_camelot,
)
from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string
from kiku.setbuilder.scoring import score_replacement

# Harmonic scores >= this read as a clean mix (same 1.0 / adjacent 0.85 / mode
# flip 0.8); below it a transition turns harsh. Grounds the honesty caveat.
CLEAN_THRESHOLD = 0.8

_MOVE_NAMES = {
    "push_higher": "energy boost",
    "brighten": "brighten",
    "cool_down": "cool down",
    "hold": "hold",
}


@dataclass
class SlotPick:
    """One ranked slot candidate with its harmonic move and any honesty caveat."""

    track: Track
    from_key: str | None  # the predecessor's key the move departs from
    to_key: str | None  # the candidate's key
    move: str  # human-readable move description (Show the Why)
    energy_shift: float  # the applied energy-target shift
    score: float  # both-neighbor combined score
    incoming_breakdown: dict | None
    outgoing_breakdown: dict | None
    caveat: str | None  # set when the slot resists the requested move


def _resolve_neighbors(ordered_tracks: list, position: int, mode: str):
    """Resolve ``(prev, next)`` tracks for a slot per ``mode``.

    insert at N  -> neighbors are tracks N and N+1 (the set grows between them)
    replace at N -> neighbors are N-1 and N+1 (track N is dropped)
    """
    total = len(ordered_tracks)
    if mode == "insert":
        prev = ordered_tracks[position] if 0 <= position < total else None
        nxt = ordered_tracks[position + 1] if position + 1 < total else None
    else:  # replace
        prev = ordered_tracks[position - 1] if position > 0 else None
        nxt = ordered_tracks[position + 1] if position + 1 < total else None
    return prev, nxt


def _achievable_alt(prev_key: str | None, next_key: str | None):
    """Find the directional alt whose target keeps BOTH harmonic sides clean.

    Returns ``(alt_intent, alt_target_key_str)`` maximizing ``min(both sides)``
    with both ``>= CLEAN_THRESHOLD``, or ``None`` when no directional alt is
    both-clean.
    """
    best = None
    best_min = -1.0
    for alt in ("push_higher", "brighten", "cool_down"):
        for tgt in move_targets(prev_key, alt):
            tgt_str = camelot_str(tgt)
            m = min(
                harmonic_score(prev_key, tgt_str),
                harmonic_score(tgt_str, next_key),
            )
            if m >= CLEAN_THRESHOLD and m > best_min:
                best_min = m
                best = (alt, tgt_str)
    return best


def _build_caveat(prev, cand, nxt, intent: str) -> str | None:
    """Return an honesty caveat when the slot resists the requested move, else None.

    Trips when the move mixes cleanly OUT of the predecessor
    (``h_in >= T``) but the FIXED successor drags a harmonic side below clean
    (``min < T``). Names the achievable move and the anchor that resists — the
    teaching, not an afterthought. Guards missing neighbors and ``hold``.
    """
    if prev is None or nxt is None or intent == "hold":
        return None
    h_in = harmonic_score(prev.key, cand.key)
    h_out = harmonic_score(cand.key, nxt.key)
    if h_in < CLEAN_THRESHOLD or min(h_in, h_out) >= CLEAN_THRESHOLD:
        return None  # move side already unclean (not our promise), or both clean
    requested_name = _MOVE_NAMES.get(intent, intent)
    alt = _achievable_alt(prev.key, nxt.key)
    if alt:
        alt_intent, alt_to = alt
        alt_name = _MOVE_NAMES.get(alt_intent, alt_intent)
        return (
            f"The next track ({nxt.key}) pulls back toward it, so the cleanest "
            f"move here is a {alt_name} ({prev.key}→{alt_to}), not a full "
            f"{requested_name}."
        )
    return (
        f"The next track ({nxt.key}) resists a clean {requested_name} here — "
        f"holding a compatible key mixes smoother than forcing the move."
    )


def _build_move(prev, cand, nxt, intent: str, energy_shift: float, caveat: str | None) -> str:
    """Build the move description shown on every pick (never a bare ranked list)."""
    move_name = _MOVE_NAMES.get(intent, intent)
    from_key = prev.key if prev else None
    to_key = cand.key
    shift = f"{energy_shift:+.2f}"
    head = f"{from_key} → {to_key} {move_name}" if from_key else f"{to_key} {move_name}"
    if caveat:
        return f"{head} ({shift} energy) — see the caveat below."
    if nxt is not None:
        # Only promise a clean blend when the outgoing side actually holds up.
        # The caveat is suppressed for `hold` and for already-unclean incoming
        # sides, so this claim must be checked here — never call a clash clean.
        h_out = harmonic_score(cand.key, nxt.key)
        if h_out >= CLEAN_THRESHOLD:
            return f"{head}, {shift} energy, mixes into {nxt.key} clean."
        return f"{head}, {shift} energy — the blend into {nxt.key} is a stretch."
    return f"{head}, {shift} energy."


def rank_slot_picks(
    session: Session,
    set_id: int,
    position: int,
    mode: str,
    intent: str,
    allowed_keys: set[str] | None = None,
    energy_delta: float | None = None,
    n: int = 10,
    weights: dict[str, float] | None = None,
    discovery_density: float = 0.0,
) -> list[SlotPick]:
    """Rank owned tracks that make the requested directional move at a slot.

    Returns up to ``n`` picks ordered by both-neighbor score (descending), each
    carrying its harmonic move and an honesty caveat when the slot resists it.
    Returns an empty list when the set is missing, the position is out of range,
    or nothing owned fits the requested move.
    """
    s = session.get(Set, set_id)
    if not s:
        return []

    ordered = sorted(s.tracks, key=lambda st: st.position)
    ordered_tracks = [st.track for st in ordered]
    set_track_ids = {st.track_id for st in ordered}
    total = len(ordered_tracks)
    if position < 0 or position >= total:
        return []

    prev, nxt = _resolve_neighbors(ordered_tracks, position, mode)

    # Energy profile (JSON first, then string fallback) -> baseline target.
    profile = None
    if s.energy_profile:
        try:
            try:
                profile = parse_energy_json(s.energy_profile)
            except (json.JSONDecodeError, KeyError):
                profile = parse_energy_string(s.energy_profile)
        except Exception:
            profile = None
    baseline = 0.5
    if profile is not None:
        elapsed = (position / max(total - 1, 1)) * (s.duration_min or 120)
        baseline = profile.target_energy_at(elapsed)

    # Directional shift: explicit override else the intent's shift.
    energy_shift = energy_delta if energy_delta is not None else intent_energy_delta(intent)
    shifted_target = min(1.0, max(0.0, baseline + energy_shift))

    # Key constraint: explicit override else derived from the intent, measured
    # against the PREVIOUS neighbor (mixing OUT of the predecessor is the move).
    prev_key = prev.key if prev else None
    if allowed_keys is not None:
        key_filter = {camelot_str(pc) for k in allowed_keys if (pc := parse_camelot(k))}
        key_filter = key_filter or None
    else:
        key_filter = intent_allowed_keys(prev_key, intent)

    # Candidate pool: exclude in-set, BPM pre-filter around the neighbours
    # (mirrors get_replacements: a +/-2*BPM_TOLERANCE window).
    q = session.query(Track).filter(Track.id.notin_(set_track_ids))
    ref_bpms = [t.bpm for t in (prev, nxt) if t and t.bpm and t.bpm > 0]
    ref_bpm = sum(ref_bpms) / len(ref_bpms) if ref_bpms else 0
    if ref_bpm and ref_bpm > 0:
        q = q.filter(
            Track.bpm.between(ref_bpm * (1 - BPM_TOLERANCE * 2), ref_bpm * (1 + BPM_TOLERANCE * 2))
        )
    candidates = q.all()

    picks: list[SlotPick] = []
    for cand in candidates:
        # Library excavation only, and never re-suggest a track already in the
        # set (the SQL notin_ filter enforces this too; this guard keeps the
        # exclusion explicit for any candidate pool).
        if cand.id in set_track_ids:
            continue
        # Hard key filter when a constraint is present (drop keyless / off-key).
        if key_filter is not None:
            pc = parse_camelot(cand.key)
            if pc is None or camelot_str(pc) not in key_filter:
                continue
        combined, incoming, outgoing = score_replacement(
            cand, prev, nxt, target_energy=shifted_target,
            weights=weights, discovery_density=discovery_density,
        )
        caveat = _build_caveat(prev, cand, nxt, intent)
        move = _build_move(prev, cand, nxt, intent, energy_shift, caveat)
        picks.append(SlotPick(
            track=cand,
            from_key=prev.key if prev else None,
            to_key=cand.key,
            move=move,
            energy_shift=round(energy_shift, 3),
            score=combined,
            incoming_breakdown=incoming,
            outgoing_breakdown=outgoing,
            caveat=caveat,
        ))

    picks.sort(key=lambda p: p.score, reverse=True)
    return picks[:n]
