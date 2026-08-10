"""Set use-cases.

What a set *is* and what you can do to one, expressed once, so the HTTP routes and
the CLI cannot drift apart (docs/notes/OBS-006/E6). The clearest instance: resolving
a set from "an id or part of a name" was hand-written in five CLI commands, each
with its own `int()`-in-a-try and its own `ilike`, and absent from the API entirely.

The rules here:

- Nothing in this module knows about HTTP. It raises `SetNotFound` / `SetInvalid`;
  the route maps those to status codes and the CLI prints them.
- Nothing here formats a response. Serialization belongs to whoever is talking.
- Callers own the session. These functions commit, because a use-case is the unit
  of work, but they never open or close one.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from kiku.db.models import Set

# How long a soft-deleted set stays recoverable before it is purged for good.
SOFT_DELETE_DAYS = 3


class SetError(Exception):
    """Base for set use-case failures."""


class SetNotFound(SetError):
    """The set (or something it points at) does not exist."""


class SetInvalid(SetError):
    """The request is understood but not allowed."""


# ── Finding sets ───────────────────────────────────────────────────────


def get(session: Session, set_id: int) -> Set:
    """Fetch a set by id, or raise."""
    set_ = session.get(Set, set_id)
    if not set_:
        raise SetNotFound("Set not found")
    return set_


def resolve(session: Session, ref: str | int) -> Set:
    """Fetch a set by id *or* by a fragment of its name.

    Every CLI command that takes a set had its own copy of this — an `int()` in a
    try block, then an `ilike`. One of them is now enough.
    """
    try:
        set_ = session.get(Set, int(ref))
    except (TypeError, ValueError):
        set_ = session.query(Set).filter(Set.name.ilike(f"%{ref}%")).first()
    if not set_:
        raise SetNotFound(f"Couldn't find set '{ref}'.")
    return set_


def list_active(session: Session, search: str | None = None, limit: int = 20) -> list[Set]:
    purge_expired(session)
    q = session.query(Set).filter(Set.deleted_at.is_(None))
    if search:
        q = q.filter(Set.name.ilike(f"%{search}%"))
    return q.order_by(Set.created_at.desc()).limit(limit).all()


def list_trashed(session: Session) -> list[Set]:
    purge_expired(session)
    return (
        session.query(Set).filter(Set.deleted_at.isnot(None)).order_by(Set.deleted_at.desc()).all()
    )


# ── Lifecycle ──────────────────────────────────────────────────────────


def create(
    session: Session,
    name: str | None,
    energy_profile: str | None = None,
    genre_filter: list[str] | None = None,
    source: str | None = None,
) -> Set:
    set_ = Set(
        name=name,
        energy_profile=energy_profile,
        genre_filter=json.dumps(genre_filter) if genre_filter else None,
        source=source,
    )
    session.add(set_)
    session.commit()
    session.refresh(set_)
    return set_


def update(
    session: Session,
    set_id: int,
    name: str | None = None,
    energy_profile: str | None = None,
    genre_filter: list[str] | None = None,
) -> Set:
    set_ = get(session, set_id)
    if name is not None:
        set_.name = name
    if energy_profile is not None:
        set_.energy_profile = energy_profile
    if genre_filter is not None:
        set_.genre_filter = json.dumps(genre_filter)
    session.commit()
    session.refresh(set_)
    return set_


def soft_delete(session: Session, set_id: int) -> None:
    """Move a set to the trash. Recoverable for SOFT_DELETE_DAYS."""
    set_ = get(session, set_id)
    set_.deleted_at = datetime.now().isoformat()
    session.commit()


def restore(session: Session, set_id: int) -> Set:
    set_ = get(session, set_id)
    set_.deleted_at = None
    session.commit()
    return set_


def purge_expired(session: Session) -> int:
    """Hard-delete sets that have sat in the trash past the grace period.

    ISO timestamps sort chronologically as strings, so a string comparison is safe.
    Returns how many were purged.
    """
    cutoff = (datetime.now() - timedelta(days=SOFT_DELETE_DAYS)).isoformat()
    expired = session.query(Set).filter(Set.deleted_at.isnot(None), Set.deleted_at < cutoff).all()
    if not expired:
        return 0
    for s in expired:
        session.delete(s)
    session.commit()
    return len(expired)


# ── Caches ─────────────────────────────────────────────────────────────


def invalidate_analysis(session: Session, set_: Set) -> None:
    """Anything that changes a set's contents makes its analysis a lie."""
    set_.is_analyzed = 0
    set_.analysis_cache = None
    clear_comparison_caches(session, set_)


def clear_comparison_caches(session: Session, set_: Set) -> None:
    """Clear comparisons touching this set — its own, and any played set linked to it."""
    set_.comparison_cache = None
    for linked in session.query(Set).filter(Set.planned_set_id == set_.id).all():
        linked.comparison_cache = None


# ── Analysis ───────────────────────────────────────────────────────────


def analyze(session: Session, set_id: int) -> dict[str, Any]:
    """Score a set's transitions and arc.

    Returns a plain dict so both callers can render it however they like.
    `analyze_set` already writes `analysis_cache` itself, so this does not — the
    cache and this return value are the same shape by construction.
    """
    from kiku.analysis.set_analyzer import analyze_set

    try:
        result = analyze_set(session, set_id)
    except ValueError as e:
        raise SetNotFound(str(e)) from e

    data = asdict(result)
    # A tuple is not JSON.
    data["arc"]["bpm_range"] = list(data["arc"]["bpm_range"])
    return data


def cached_analysis(session: Session, set_id: int) -> dict[str, Any]:
    set_ = get(session, set_id)
    if not set_.is_analyzed or not set_.analysis_cache:
        raise SetNotFound("Set has not been analyzed yet. Use POST /analyze first.")
    return json.loads(set_.analysis_cache)


# ── Played vs planned ──────────────────────────────────────────────────


def link_to_plan(session: Session, set_id: int, planned_set_id: int) -> Set:
    set_ = get(session, set_id)
    if planned_set_id == set_id:
        raise SetInvalid("A set can't be its own plan — pick the set you built in Kiku")
    if not session.get(Set, planned_set_id):
        raise SetNotFound("Planned set not found")

    set_.planned_set_id = planned_set_id
    set_.comparison_cache = None
    session.commit()
    return set_


def unlink_from_plan(session: Session, set_id: int) -> Set:
    """Linking is optional and reversible, so this is never an error."""
    set_ = get(session, set_id)
    set_.planned_set_id = None
    set_.comparison_cache = None
    session.commit()
    return set_


def compare(session: Session, set_id: int) -> dict[str, Any]:
    """Compare a played set against its plan.

    `compare_sets` writes `comparison_cache` itself, same as `analyze` above.
    """
    from kiku.analysis.set_compare import compare_sets

    set_ = get(session, set_id)
    if not set_.planned_set_id:
        raise SetNotFound("No planned set linked — link one first with PUT /link")

    try:
        result = compare_sets(session, set_id, set_.planned_set_id)
    except ValueError as e:
        raise SetNotFound(str(e)) from e

    return asdict(result)


def cached_comparison(session: Session, set_id: int) -> dict[str, Any]:
    set_ = get(session, set_id)
    if not set_.comparison_cache:
        raise SetNotFound("Set hasn't been compared yet. Use POST /compare first.")
    return json.loads(set_.comparison_cache)


# ── Replacement candidates ─────────────────────────────────────────────


def replacement_candidates(
    session: Session,
    set_id: int,
    position: int,
    n: int = 10,
    genre_filter: str | None = None,
    discovery_density: float = 0.0,
) -> dict[str, Any]:
    """Rank tracks that could stand in for the one at `position`.

    Scored against *both* neighbours, because a replacement has to work coming in
    and going out. Returns plain data — the neighbours, the energy target used, and
    the ranked candidates with their score breakdowns — for the caller to render.
    """
    from sqlalchemy import or_

    from kiku.config import BPM_TOLERANCE
    from kiku.db.models import Track
    from kiku.setbuilder.scoring import score_replacement

    set_ = get(session, set_id)

    ordered = sorted(set_.tracks, key=lambda st: st.position)
    if position < 0 or position >= len(ordered):
        raise SetNotFound("Invalid position")

    current_track = ordered[position].track
    prev_track = ordered[position - 1].track if position > 0 else None
    next_track = ordered[position + 1].track if position < len(ordered) - 1 else None

    energy_target = _energy_target_at(set_, position, len(ordered))

    # Everything already in the set is disqualified — a replacement that duplicates
    # a track elsewhere in the set is not a replacement.
    set_track_ids = {st.track_id for st in ordered}

    # Pre-filter on the neighbours' tempo so scoring runs over a plausible pool
    # rather than the whole library.
    ref_bpms = [t.bpm for t in (prev_track, next_track) if t and t.bpm and t.bpm > 0]
    ref_bpm = (
        sum(ref_bpms) / len(ref_bpms) if ref_bpms else (current_track.bpm if current_track else 0)
    )

    q = session.query(Track).filter(Track.id.notin_(set_track_ids))
    if ref_bpm and ref_bpm > 0:
        q = q.filter(
            Track.bpm.between(ref_bpm * (1 - BPM_TOLERANCE * 2), ref_bpm * (1 + BPM_TOLERANCE * 2))
        )
    if genre_filter:
        genres = [g.strip() for g in genre_filter.split(",")]
        q = q.filter(or_(*[Track.dir_genre.ilike(f"%{g}%") for g in genres]))

    scored = []
    for cand in q.all():
        combined, incoming, outgoing = score_replacement(
            cand,
            prev_track,
            next_track,
            target_energy=energy_target,
            discovery_density=discovery_density,
        )
        scored.append((cand, combined, incoming, outgoing))

    scored.sort(key=lambda x: x[1], reverse=True)

    return {
        "prev_track": prev_track,
        "next_track": next_track,
        "energy_target": round(energy_target, 3),
        "position": position,
        "candidates": scored[:n],
    }


def _energy_target_at(set_: Set, position: int, total_tracks: int) -> float:
    """Where the set's energy curve should be at this slot.

    Falls back to a neutral 0.5 when the set has no profile, or one we cannot read.
    """
    if not set_.energy_profile:
        return 0.5
    from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string

    try:
        try:
            profile = parse_energy_json(set_.energy_profile)
        except (json.JSONDecodeError, KeyError):
            profile = parse_energy_string(set_.energy_profile)
    except ValueError:
        return 0.5

    elapsed = (position / max(total_tracks - 1, 1)) * (set_.duration_min or 120)
    return profile.target_energy_at(elapsed)
