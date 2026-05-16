"""
BuildemUp† — Component 8 (Corridor Designer) — Grid alignment module.

Per C8 SPEC v0.5 LOCKED § 4.2 / § 4.2.1 / § 14.9 / § 14.21.

Two functions:
  - ``derive_grid_lines(grid)`` — per § 4.2 / § 14.9: extracts (x_lines, y_lines)
    from grid.columns. Sorted, deduplicated.
  - ``find_edge_snap_pair(...)`` — per § 4.2 step 3-4: locates the nearest
    grid-line pair straddling a target centerline at the requested width.
    Per § 4.2.1: when multiple pairs match within epsilon, ties-break with
    envelope-symmetry secondary criterion (lower combined score wins).

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08.schema import CorridorDesignConfig


def derive_grid_lines(grid: Grid) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Derive (x_lines, y_lines) from grid.columns. Sorted + deduplicated.

    Per § 4.2 / § 14.9 — replaces the v0.1 phantom ``column_lines_x/y``
    fields. Lines are derived from actual column positions so
    Invariant 14 (every snap-line passes through ≥ 1 column) is satisfied
    by construction.
    """
    # Use a tolerance-aware dedup: round to 6 decimal places (sub-mm)
    x_set = sorted({round(c.x_m, 6) for c in grid.columns})
    y_set = sorted({round(c.y_m, 6) for c in grid.columns})
    return tuple(x_set), tuple(y_set)


def edge_snap_choice_score(
    pair: tuple[float, float],
    envelope_dim_m: float,
    target_centerline: float,
    config: CorridorDesignConfig,
) -> float:
    """Score the goodness of a candidate (low, high) grid-line pair.

    Per § 4.2.1. Lower is better. Combines:
      - primary: |pair_center - target_centerline|
      - secondary: |pair_center - envelope_center| / envelope_dim
                   weighted by ``config.envelope_symmetry_weight``.
    """
    g_low, g_high = pair
    pair_center = (g_low + g_high) / 2.0
    primary_dist = abs(pair_center - target_centerline)
    envelope_center = envelope_dim_m / 2.0
    if envelope_dim_m <= 0:
        symmetry_dist = 0.0
    else:
        symmetry_dist = abs(pair_center - envelope_center) / envelope_dim_m
    return primary_dist + config.envelope_symmetry_weight * symmetry_dist


def find_edge_snap_pair(
    grid_lines: tuple[float, ...],
    target_width_m: float,
    target_centerline_m: float,
    envelope_dim_m: float,
    config: CorridorDesignConfig,
) -> tuple[float, float] | None:
    """Find the best (g_low, g_high) pair such that the separation matches
    ``target_width_m`` within ``config.epsilon_m``.

    Per § 4.2 step 3-4 + § 4.2.1 envelope-symmetry secondary criterion.

    Args:
        grid_lines: sorted tuple of grid-line coordinates (1D).
        target_width_m: corridor width along the perpendicular axis.
        target_centerline_m: centerline coordinate the corridor wants to hit.
        envelope_dim_m: envelope extent along the same axis.
        config: tunables; supplies ``epsilon_m`` + ``envelope_symmetry_weight``.

    Returns:
        Best matching (g_low, g_high) pair, or None if no pair separation is
        within epsilon of target_width_m.
    """
    if not grid_lines:
        return None

    eps = config.epsilon_m
    candidates: list[tuple[float, float]] = []
    for i, gl in enumerate(grid_lines):
        for gh in grid_lines[i + 1:]:
            sep = gh - gl
            if abs(sep - target_width_m) <= eps:
                candidates.append((gl, gh))

    if not candidates:
        return None

    # Tie-break per § 4.2.1: minimum edge_snap_choice_score
    best = min(
        candidates,
        key=lambda p: edge_snap_choice_score(
            p, envelope_dim_m, target_centerline_m, config,
        ),
    )
    return best


__all__ = [
    "derive_grid_lines",
    "edge_snap_choice_score",
    "find_edge_snap_pair",
]
