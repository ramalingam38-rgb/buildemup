"""
BuildemUp — Component 12 — slicing-tree placement algorithm
============================================================

Per C12 SPEC v1.0 LOCKED § 3.1.

Algorithm (Knecht & König 2010 slicing-kd-tree, simplified for
rectangular envelopes):

1. Sort rooms by area DESC (largest first). For canonical-ordering
   ties, break by room_id lex-ASC (per v0.2-A4 rule #1 +
   canonicalization rule #6 fixed-axis ordering).

2. Choose bisection axis: vertical first, then horizontal on
   backtrack (per v0.2-A4 rule #6 fixed iteration order).

3. Recursively partition the envelope:
   - At each node: split into two sub-rectangles.
   - Assign each room to one side based on area-balanced bipartition.
   - Recurse on each side.
   - Leaf: a single room placed in its sub-rectangle, top-left aligned.

4. Backtrack on infeasibility:
   - If a leaf can't fit (sub-rectangle smaller than room dims):
     return None to the parent.
   - Parent tries alternative cut positions in canonical order
     (cut fraction varies in 0.1 increments from balanced toward
     extremes).
   - If all alternatives exhausted: bubble up the backtrack.

5. Worst case: O(n!) per the spec acknowledgment. For typical n ≤ 15
   the heuristic is fast (O(n log n) expected).

The implementation is INTENTIONALLY iteration-deterministic:
every choice point uses a fixed canonical order. This guarantees
Inv 7 byte-equal replay across runs given identical inputs +
configuration.
"""
from __future__ import annotations

from typing import Literal

from ..bounds import DEFAULT_GRID_SNAP_M, snap_to_grid
from ..errors import GeometricInfeasibilityError
from ..schema import PlacedRoom
from .room_spec import RoomSpec


# Bisection axis choices in their CANONICAL TRY ORDER (per v0.2-A4
# rule #6): always try vertical (x-axis cut) first, then horizontal
# (y-axis cut) on backtrack. This deterministic order is the
# replay-stability guarantee.
_AXIS_TRY_ORDER: tuple[Literal["vertical", "horizontal"], ...] = (
    "vertical", "horizontal",
)

# Cut fraction try order: balanced (0.5) first, then biased
# alternatives toward extremes. Deterministic, canonical.
_CUT_FRACTION_TRY_ORDER: tuple[float, ...] = (
    0.50, 0.40, 0.60, 0.30, 0.70, 0.25, 0.75,
)


def _candidate_cut_fractions(
    cut_extent: float,
    rooms: tuple[RoomSpec, ...],
    axis: str,
) -> tuple[float, ...]:
    """Build a canonical-ordered tuple of cut fractions to try.

    Includes:
      - The base balanced/biased set (_CUT_FRACTION_TRY_ORDER)
      - ADAPTIVE: fractions corresponding to actual room-dim ratios
        on this axis, so the algorithm tries cuts that match exact
        room dimensions (handles cases where a fixed-set fraction
        doesn't divide the envelope cleanly).

    Output is sorted by distance from 0.5 (balanced first, biased
    second) then by value (canonical tie-break) for determinism.
    """
    # Adaptive: extract dim ratios from rooms on this axis.
    adaptive_fractions: set[float] = set()
    for room in rooms:
        dim = room.target_width_m if axis == "vertical" else room.target_depth_m
        if cut_extent > 0:
            f = dim / cut_extent
            if 0.05 < f < 0.95:
                # Snap to 0.0001 precision for de-dup + replay
                # determinism without losing exact-fit precision.
                adaptive_fractions.add(round(f, 4))

    candidates = set(_CUT_FRACTION_TRY_ORDER) | adaptive_fractions
    # Canonical sort: distance from balance first, then value ASC.
    return tuple(sorted(
        candidates,
        key=lambda f: (abs(f - 0.5), f),
    ))


def _bipartition_by_area(
    rooms: tuple[RoomSpec, ...], target_fraction: float,
) -> tuple[tuple[RoomSpec, ...], tuple[RoomSpec, ...]]:
    """Partition rooms into two groups, attempting to match the
    area split target_fraction (group A area / total area).

    Greedy: rooms are pre-sorted area DESC. We assign each room to
    the side whose current area is furthest below its target.

    Determinism: same input order → same output partition.
    """
    if not rooms:
        return ((), ())

    total_area = sum(r.area_m2 for r in rooms)
    target_a_area = total_area * target_fraction

    side_a: list[RoomSpec] = []
    side_b: list[RoomSpec] = []
    a_area = 0.0
    b_area = 0.0

    for room in rooms:
        # Choose the side whose current area is furthest below its
        # target. Side A's target is target_a_area; side B's is
        # total_area - target_a_area.
        a_room_area_after = a_area + room.area_m2
        b_room_area_after = b_area + room.area_m2
        # Distance from target after adding to A:
        target_b_area = total_area - target_a_area
        # Prefer the side with greater room "headroom" relative to target.
        a_headroom = target_a_area - a_area
        b_headroom = target_b_area - b_area
        # Canonical tie-break: A wins on equal headroom.
        if a_headroom >= b_headroom:
            side_a.append(room)
            a_area = a_room_area_after
        else:
            side_b.append(room)
            b_area = b_room_area_after

    return (tuple(side_a), tuple(side_b))


def _place_single_room(
    room: RoomSpec,
    *,
    x: float, y: float, w: float, d: float,
    grid_m: float,
) -> PlacedRoom:
    """Place a single room in its allocated sub-rectangle. STRICT
    mode (v0.2-A3): must fit; otherwise raise.

    Top-left alignment (x, y) within the sub-rectangle. Coordinates
    snapped to grid per v0.2-A4 rule #4.
    """
    if room.target_width_m > w + 1e-9 or room.target_depth_m > d + 1e-9:
        raise GeometricInfeasibilityError(
            f"Room {room.room_id!r} (target "
            f"{room.target_width_m}x{room.target_depth_m}) does not "
            f"fit in sub-rectangle ({w}x{d})."
        )
    return PlacedRoom(
        room_id=room.room_id,
        category=room.category,
        x_m=snap_to_grid(x, grid_m=grid_m),
        y_m=snap_to_grid(y, grid_m=grid_m),
        width_m=snap_to_grid(room.target_width_m, grid_m=grid_m),
        depth_m=snap_to_grid(room.target_depth_m, grid_m=grid_m),
        operator_class_lineage=room.operator_class_lineage,
    )


def _place_recursive(
    rooms: tuple[RoomSpec, ...],
    *,
    x: float, y: float, w: float, d: float,
    grid_m: float,
) -> tuple[PlacedRoom, ...] | None:
    """Recursively partition the sub-rectangle and place rooms.

    Returns:
      - A tuple of PlacedRooms (one per input room) on success.
      - None if no feasible partition was found (parent backtracks).
    """
    n = len(rooms)
    if n == 0:
        return ()
    if n == 1:
        try:
            return (_place_single_room(
                rooms[0], x=x, y=y, w=w, d=d, grid_m=grid_m,
            ),)
        except GeometricInfeasibilityError:
            return None

    # n >= 2: try axis choices in canonical order.
    for axis in _AXIS_TRY_ORDER:
        # Choose the longer dimension if possible — the slicing-tree
        # heuristic prefers cutting the longer side for balanced
        # sub-trees. Only override the axis order if the alternative
        # axis is significantly longer.
        # Canonical fallback: use the axis from _AXIS_TRY_ORDER as-is.

        # Cut along the chosen axis.
        if axis == "vertical":
            cut_extent = w  # cut at some x = x + cut_extent * fraction
        else:
            cut_extent = d  # cut at some y = y + cut_extent * fraction

        for fraction in _candidate_cut_fractions(cut_extent, rooms, axis):
            # Bipartition rooms by area target.
            side_a_rooms, side_b_rooms = _bipartition_by_area(
                rooms, target_fraction=fraction,
            )
            if not side_a_rooms or not side_b_rooms:
                continue  # degenerate partition, skip this fraction

            # Compute sub-rectangles for each side. Snap the cut
            # position to the grid resolution so sub-rectangles have
            # exact grid-aligned dimensions (prevents FP precision
            # issues where rooms fail by sub-millimetre amounts).
            cut_pos = snap_to_grid(cut_extent * fraction, grid_m=grid_m)
            # Guard against degenerate snapped cut.
            if cut_pos <= 0.0 or cut_pos >= cut_extent:
                continue
            if axis == "vertical":
                a_x, a_y, a_w, a_d = x, y, cut_pos, d
                b_x, b_y, b_w, b_d = x + cut_pos, y, w - cut_pos, d
            else:  # horizontal
                a_x, a_y, a_w, a_d = x, y, w, cut_pos
                b_x, b_y, b_w, b_d = x, y + cut_pos, w, d - cut_pos

            # Recurse on each side.
            placed_a = _place_recursive(
                side_a_rooms,
                x=a_x, y=a_y, w=a_w, d=a_d, grid_m=grid_m,
            )
            if placed_a is None:
                continue
            placed_b = _place_recursive(
                side_b_rooms,
                x=b_x, y=b_y, w=b_w, d=b_d, grid_m=grid_m,
            )
            if placed_b is None:
                continue

            # Both sides succeeded.
            return placed_a + placed_b

    # All axis/fraction combinations failed.
    return None


def place_rooms_slicing_tree(
    rooms: tuple[RoomSpec, ...],
    *,
    envelope_width_m: float,
    envelope_depth_m: float,
    grid_m: float = DEFAULT_GRID_SNAP_M,
) -> tuple[PlacedRoom, ...]:
    """Top-level slicing-tree placement.

    Per § 3.1:
      1. Sort rooms by area DESC, room_id lex-ASC on ties.
      2. Recursively partition the envelope.
      3. Return PlacedRooms sorted lex-ASC by room_id (PlacedCandidate
         invariant).

    Raises:
      GeometricInfeasibilityError if no feasible partition exists for
      the room set.
    """
    if envelope_width_m <= 0.0 or envelope_depth_m <= 0.0:
        raise GeometricInfeasibilityError(
            f"Envelope dims must be positive; got "
            f"{envelope_width_m}x{envelope_depth_m}."
        )

    # Quick infeasibility check: total area > envelope area
    total_area = sum(r.area_m2 for r in rooms)
    envelope_area = envelope_width_m * envelope_depth_m
    if total_area > envelope_area + 1e-9:
        raise GeometricInfeasibilityError(
            f"Total room area ({total_area:.2f} m²) exceeds envelope "
            f"area ({envelope_area:.2f} m²)."
        )

    # Canonical sort: area DESC, room_id lex-ASC on ties.
    # Negating area gives DESC sort; room_id ascending is canonical
    # tie-break.
    sorted_rooms = tuple(sorted(
        rooms,
        key=lambda r: (-r.area_m2, r.room_id),
    ))

    placed = _place_recursive(
        sorted_rooms,
        x=0.0, y=0.0,
        w=envelope_width_m, d=envelope_depth_m,
        grid_m=grid_m,
    )
    if placed is None:
        raise GeometricInfeasibilityError(
            f"No feasible slicing-tree partition found for "
            f"{len(rooms)} rooms in {envelope_width_m}x"
            f"{envelope_depth_m}m envelope."
        )

    # Return sorted lex-ASC by room_id (PlacedCandidate invariant).
    return tuple(sorted(placed, key=lambda p: p.room_id))


__all__ = ["place_rooms_slicing_tree"]
