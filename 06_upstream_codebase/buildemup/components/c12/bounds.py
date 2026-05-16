"""
BuildemUp — Component 12 — geometric bounds utilities
======================================================

Per C12 SPEC v1.0 LOCKED.

Helper functions for envelope / room rectangle bounds checking.
Used by Phase 1 placement, Phase 0b reachability, and shared-edge
derivation.

All functions are pure / deterministic / ε-aware per v0.2-A7
(default ε = 1mm = 0.001 m).
"""
from __future__ import annotations

from typing import Final

# v0.2-A7: ε-tolerance for geometric comparisons. Aligned with
# v0.2-A8's 20mm alignment tolerance scale: ε is 20× finer than
# alignment tolerance, which is the right precision separation.
DEFAULT_EPSILON_M: Final[float] = 0.001  # 1mm

# v0.2-A4 rule #4: coordinate snapping resolution. Aligned with
# typical C7-Grid resolution. Snapping prevents floating-point
# drift from breaking Inv 7 byte-equal replay.
DEFAULT_GRID_SNAP_M: Final[float] = 0.05  # 50mm


def rectangle_contains(
    outer_x: float,
    outer_y: float,
    outer_w: float,
    outer_d: float,
    inner_x: float,
    inner_y: float,
    inner_w: float,
    inner_d: float,
    *,
    epsilon_m: float = DEFAULT_EPSILON_M,
) -> bool:
    """True iff the inner rectangle is entirely contained within the
    outer rectangle, with ε-tolerance on the boundary.

    Used by Inv 1 (PlacedRoom inside envelope) verification.
    """
    return (
        inner_x >= outer_x - epsilon_m
        and inner_y >= outer_y - epsilon_m
        and inner_x + inner_w <= outer_x + outer_w + epsilon_m
        and inner_y + inner_d <= outer_y + outer_d + epsilon_m
    )


def rectangles_overlap(
    ax: float, ay: float, aw: float, ad: float,
    bx: float, by: float, bw: float, bd: float,
    *,
    epsilon_m: float = DEFAULT_EPSILON_M,
) -> bool:
    """True iff two rectangles overlap in interior (touching edges
    do NOT count as overlap; that's adjacency).

    Used by Inv 2 (no two PlacedRooms overlap) verification.

    Strict-less-than with ε buffer: rectangles that share an edge
    (a touches b on a wall) are NOT considered overlapping.
    """
    return (
        ax + aw > bx + epsilon_m
        and bx + bw > ax + epsilon_m
        and ay + ad > by + epsilon_m
        and by + bd > ay + epsilon_m
    )


def snap_to_grid(value: float, *, grid_m: float = DEFAULT_GRID_SNAP_M) -> float:
    """Snap a coordinate to the deterministic grid resolution.

    Per v0.2-A4 canonicalization rule #4: prevents FP drift from
    breaking byte-equal replay (Inv 7). Uses round-half-even
    (banker's rounding) via Python's built-in ``round`` for
    determinism across runs."""
    if grid_m <= 0.0:
        raise ValueError(f"grid_m must be positive; got {grid_m}.")
    return round(value / grid_m) * grid_m


def axis_overlap_length(
    a_start: float, a_end: float,
    b_start: float, b_end: float,
    *,
    epsilon_m: float = DEFAULT_EPSILON_M,
) -> float:
    """Length of overlap between two 1D intervals [a_start, a_end]
    and [b_start, b_end].

    Returns 0.0 if the intervals don't overlap or touch only at a
    point. Used by shared-edge derivation (§ 3.6).
    """
    lo = max(a_start, b_start)
    hi = min(a_end, b_end)
    overlap = hi - lo
    return overlap if overlap > epsilon_m else 0.0


__all__ = [
    "DEFAULT_EPSILON_M",
    "DEFAULT_GRID_SNAP_M",
    "rectangle_contains",
    "rectangles_overlap",
    "snap_to_grid",
    "axis_overlap_length",
]
