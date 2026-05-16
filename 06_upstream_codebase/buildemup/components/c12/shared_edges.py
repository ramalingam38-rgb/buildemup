"""
BuildemUp — Component 12 — shared edge derivation
==================================================

Per C12 SPEC v1.0 LOCKED § 3.6 — derive SharedEdge tuples from a
set of PlacedRooms.

Composition of three amendments:
- v0.2-A7: ε-aware overlap computation (1mm default) + grid snapping
- v0.2-A9: NBC 2016 doorway-feasibility validation on shared edges
- v0.4-A2: room-category resolution via RoomCategory + alias map

Algorithm (§ 3.6 step 1-4):
1. For each pair (R_a, R_b) of placed rooms in canonical order:
   a. Compute geometric overlap on each axis with ε-tolerance.
   b. If overlap length > ε on EXACTLY ONE axis (and the other axis
      is touching at the wall, within ε) → shared edge candidate.
   c. Snap coordinates to C7-Grid resolution.
   d. Reject if snapped overlap length < general NBC minimum
      (0.75 m) — too short for any door.
2. Compute min_required_clear_width_m per NBC 2016 category-pair
   minima.
3. doorway_feasible = (overlap_length_m >= min_required_clear_width_m).
4. Return canonical lex-ASC sorted tuple of SharedEdges.
"""
from __future__ import annotations

from typing import Final

from .bounds import (
    DEFAULT_EPSILON_M,
    DEFAULT_GRID_SNAP_M,
    axis_overlap_length,
    snap_to_grid,
)
from .input_resolution import (
    NBC_2016_DOORWAY_MIN_GENERAL_M,
    doorway_minimum_for_pair,
)
from .schema import PlacedRoom, SharedEdge


# General-purpose fallback: any shared edge shorter than the NBC 2016
# general doorway minimum (0.75 m) is rejected outright because no
# door can fit. Categories with higher minima (bedroom 0.9, main 1.0)
# may still be infeasible even at longer lengths.
MIN_SHARED_EDGE_LENGTH_M: Final[float] = NBC_2016_DOORWAY_MIN_GENERAL_M


def _detect_shared_axis(
    a: PlacedRoom, b: PlacedRoom, epsilon_m: float
) -> str | None:
    """Detect whether two rooms share a wall, and on which axis.

    Returns:
      - "vertical"   if they share a vertical wall (touching on x-axis
                       boundary, overlapping on y-axis)
      - "horizontal" if they share a horizontal wall (touching on
                       y-axis boundary, overlapping on x-axis)
      - None         if they are not adjacent
    """
    # X-axis boundaries:
    #   a's right edge:  a.x_m + a.width_m
    #   a's left edge:   a.x_m
    #   b's right edge:  b.x_m + b.width_m
    #   b's left edge:   b.x_m
    a_x_right = a.x_m + a.width_m
    b_x_right = b.x_m + b.width_m
    a_y_top = a.y_m + a.depth_m
    b_y_top = b.y_m + b.depth_m

    # Touching on x-axis boundary (within ε) means they share a
    # VERTICAL wall, IF they overlap on the y-axis.
    if abs(a_x_right - b.x_m) <= epsilon_m or abs(b_x_right - a.x_m) <= epsilon_m:
        # Check y-axis overlap is meaningful
        y_overlap = axis_overlap_length(
            a.y_m, a_y_top, b.y_m, b_y_top, epsilon_m=epsilon_m
        )
        if y_overlap > 0.0:
            return "vertical"

    # Touching on y-axis boundary (within ε) means they share a
    # HORIZONTAL wall, IF they overlap on the x-axis.
    if abs(a_y_top - b.y_m) <= epsilon_m or abs(b_y_top - a.y_m) <= epsilon_m:
        # Check x-axis overlap is meaningful
        x_overlap = axis_overlap_length(
            a.x_m, a_x_right, b.x_m, b_x_right, epsilon_m=epsilon_m
        )
        if x_overlap > 0.0:
            return "horizontal"

    return None


def _build_shared_edge(
    a: PlacedRoom,
    b: PlacedRoom,
    axis: str,
    *,
    epsilon_m: float,
    grid_m: float,
) -> SharedEdge | None:
    """Build a SharedEdge between two adjacent rooms on the given
    axis. Returns None if the snapped overlap length is too short
    for any doorway (< general NBC minimum).

    The (room_a_id, room_b_id) ordering in the returned SharedEdge
    is canonical lex-ASC, regardless of which room was passed first.
    """
    # Canonicalize ordering: ensure room_a_id < room_b_id lex-ASC.
    if a.room_id > b.room_id:
        a, b = b, a

    a_x_right = a.x_m + a.width_m
    b_x_right = b.x_m + b.width_m
    a_y_top = a.y_m + a.depth_m
    b_y_top = b.y_m + b.depth_m

    if axis == "vertical":
        # Shared wall is vertical; overlap runs along y-axis.
        raw_start = max(a.y_m, b.y_m)
        raw_end = min(a_y_top, b_y_top)
    else:  # horizontal
        # Shared wall is horizontal; overlap runs along x-axis.
        raw_start = max(a.x_m, b.x_m)
        raw_end = min(a_x_right, b_x_right)

    # Snap to grid per v0.2-A7 step 1c.
    snapped_start = snap_to_grid(raw_start, grid_m=grid_m)
    snapped_end = snap_to_grid(raw_end, grid_m=grid_m)
    snapped_length = snapped_end - snapped_start

    # Reject if too short for any door (general NBC minimum 0.75 m).
    if snapped_length < MIN_SHARED_EDGE_LENGTH_M:
        return None

    # Derive NBC minimum for this category pair.
    min_width = doorway_minimum_for_pair(a.category, b.category)
    doorway_feasible = snapped_length >= min_width

    return SharedEdge(
        room_a_id=a.room_id,
        room_b_id=b.room_id,
        axis="vertical" if axis == "vertical" else "horizontal",
        overlap_start_m=snapped_start,
        overlap_end_m=snapped_end,
        overlap_length_m=snapped_length,
        min_required_clear_width_m=min_width,
        doorway_feasible=doorway_feasible,
    )


def derive_shared_edges(
    placed_rooms: tuple[PlacedRoom, ...],
    *,
    epsilon_m: float = DEFAULT_EPSILON_M,
    grid_m: float = DEFAULT_GRID_SNAP_M,
) -> tuple[SharedEdge, ...]:
    """Derive the canonical lex-ASC sorted tuple of SharedEdges from
    a set of PlacedRooms.

    Per § 3.6 algorithm:
      1. Iterate pairs in canonical order (lex-ASC by room_id).
      2. Detect shared axis (vertical / horizontal / none) with ε.
      3. Build SharedEdge with grid-snapped coordinates.
      4. Reject sliver edges (< 0.75 m).
      5. Sort the result lex-ASC by (room_a_id, room_b_id).

    The returned tuple satisfies PlacedCandidate's
    shared_edges-must-be-sorted invariant.
    """
    # Canonical iteration order: lex-ASC by room_id (v0.2-A4 rule #1).
    sorted_rooms = sorted(placed_rooms, key=lambda r: r.room_id)

    edges: list[SharedEdge] = []
    for i in range(len(sorted_rooms)):
        for j in range(i + 1, len(sorted_rooms)):
            a = sorted_rooms[i]
            b = sorted_rooms[j]
            axis = _detect_shared_axis(a, b, epsilon_m)
            if axis is None:
                continue
            edge = _build_shared_edge(
                a, b, axis, epsilon_m=epsilon_m, grid_m=grid_m,
            )
            if edge is not None:
                edges.append(edge)

    # Canonical output ordering for PlacedCandidate.shared_edges.
    edges.sort(key=lambda e: (e.room_a_id, e.room_b_id))
    return tuple(edges)


__all__ = [
    "MIN_SHARED_EDGE_LENGTH_M",
    "derive_shared_edges",
]
