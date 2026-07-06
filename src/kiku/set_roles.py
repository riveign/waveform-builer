"""Set-role affinity tags — a DJ curation axis independent of energy, key, or genre.

A track can carry any combination of these roles, and a role never restricts where
the track may be placed in a set (non-exclusive, non-restrictive). See spec 027.
"""
from __future__ import annotations

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
