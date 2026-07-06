"""Set-role affinity tags — a DJ curation axis independent of energy, key, or genre.

A track can carry any combination of these roles, and a role never restricts where
the track may be placed in a set (non-exclusive, non-restrictive). See spec 027.
"""
from __future__ import annotations

from typing import Any

SET_ROLES: tuple[str, ...] = ("opener", "closer", "break")


def normalize_roles(roles: list[str]) -> list[str]:
    """Validate + dedupe roles against SET_ROLES, returned in canonical order.

    Raises ValueError on any unknown role.
    """
    unknown = [r for r in roles if r not in SET_ROLES]
    if unknown:
        raise ValueError(f"unknown set role(s): {', '.join(sorted(set(unknown)))}")
    present = set(roles)
    return [r for r in SET_ROLES if r in present]


def track_roles(track: Any) -> list[str]:
    """Parse a Track's stored ``set_roles`` (JSON Text) into a clean role list.

    Tolerant: returns [] on missing/blank/malformed data, and drops any value
    not in SET_ROLES.
    """
    import json

    raw = getattr(track, "set_roles", None)
    if not raw:
        return []
    try:
        roles = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(roles, list):
        return []
    return [r for r in roles if r in SET_ROLES]


def has_role(track: Any, role: str) -> bool:
    """True if the track carries the given set-role tag."""
    return role in track_roles(track)
