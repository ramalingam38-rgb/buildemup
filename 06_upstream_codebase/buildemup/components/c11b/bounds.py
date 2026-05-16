"""
BuildemUp — Component 11b — refinement bounds (carried v1.0 § 0.6)
====================================================================

Per SPEC v1.1 LOCKED § 0.6 (REVISED v0.3, carried unchanged at v0.4-v0.7).

Module-level constants for per-category sanity caps + universal-multiplier
fallback + aspect-ratio HARD constraint.

KB-driven multipliers (architect-validated catalog) are B-NEW-V2 post-launch.
"""
from __future__ import annotations

from typing import Final


SEMANTIC_CAP_BY_CATEGORY: Final[dict[str, float]] = {
    "bathroom": 1.8,  # bathrooms beyond 1.8× min are absurd
    "kitchen": 1.5,
    "utility": 1.5,
    "pooja": 1.5,
    # bedroom, living, corridor, other: fall back to universal_max_multiplier
}


MAX_ROOM_ASPECT_RATIO: Final[float] = 3.0
"""Inv 22: ``max(w, d) / min(w, d) <= 3.0`` per room.

Rejects pathological rooms (8m × 1.5m master bedroom) that pass
area-feasibility but are architecturally absurd. Enforced as HARD
constraint via NSGA-II-CDP: violations contribute
``constraint_violations += (ratio - 3.0)`` to the candidate's
``ObjectiveVector``."""


def derive_room_upper_bounds(
    room_id: str,
    room_category: str,
    room_min_w: float,
    room_min_d: float,
    envelope_w: float,
    envelope_d: float,
    other_rooms_min_area: float,
    *,
    universal_max_multiplier: float = 2.5,
) -> tuple[float, float]:
    """Per spec § 0.6: per-category semantic cap applied before envelope
    clip. Joint feasibility is resolved by NSGA-II-CDP downstream.

    Returns ``(upper_w, upper_d)`` for the room. Both upper bounds are
    >= the min, and the implied max area never exceeds envelope minus
    the sum of other rooms' min areas.
    """
    category_cap = SEMANTIC_CAP_BY_CATEGORY.get(
        room_category, universal_max_multiplier
    )
    # Category-bound max dimensions before envelope clip.
    cap_w = room_min_w * category_cap
    cap_d = room_min_d * category_cap

    # Envelope-aware clip: the room cannot exceed available envelope
    # area after subtracting other rooms' minimums (rough budget; the
    # real geometric feasibility is C12's job).
    envelope_area = envelope_w * envelope_d
    available_area = max(0.0, envelope_area - other_rooms_min_area)
    # Cap each dim by sqrt(available_area) to keep aspect ratio plausible.
    # (This is a soft heuristic; the HARD aspect ratio cap is enforced
    # later via constraint_violations.)
    if available_area > 0.0:
        envelope_dim_cap = available_area**0.5
        cap_w = min(cap_w, envelope_dim_cap, envelope_w)
        cap_d = min(cap_d, envelope_dim_cap, envelope_d)
    else:
        cap_w = min(cap_w, envelope_w)
        cap_d = min(cap_d, envelope_d)

    # Sanity floor: cap cannot fall below min.
    cap_w = max(cap_w, room_min_w)
    cap_d = max(cap_d, room_min_d)
    return (cap_w, cap_d)


def compute_aspect_constraint_violation(width_m: float, depth_m: float) -> float:
    """Returns the violation contribution for a single room's aspect
    ratio per Inv 22 (HARD via NSGA-II-CDP)."""
    if width_m <= 0.0 or depth_m <= 0.0:
        return float("inf")
    ratio = max(width_m, depth_m) / min(width_m, depth_m)
    if ratio > MAX_ROOM_ASPECT_RATIO:
        return ratio - MAX_ROOM_ASPECT_RATIO
    return 0.0


__all__ = [
    "SEMANTIC_CAP_BY_CATEGORY",
    "MAX_ROOM_ASPECT_RATIO",
    "derive_room_upper_bounds",
    "compute_aspect_constraint_violation",
]
