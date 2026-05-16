"""
BuildemUp — Component 12 — reachability validation (Phase 0b)
==============================================================

Per C12 SPEC v1.0 LOCKED v0.2-A6:

> Phase 0b — Corridor zone reservation
>
> The FloorRoomBrief input contains a corridor_zones field (output
> of C8 Corridor Design). Each corridor zone is a rectangle in
> envelope coordinates representing a reserved circulation path.
>
> Before Phase 1 SFP begins, C12:
> 1. Marks each corridor zone rectangle as occupied (cannot be
>    placed-into).
> 2. Runs a reachability BFS over the planned room positions +
>    corridor zones to verify that every room is reachable from at
>    least one building entry point.
> 3. If reachability fails: emit CirculationInfeasibilityError
>    under STRICT, or record under WARN.

This module ships the BFS step (2). The occupancy step (1) is part
of the slicing-tree placement algorithm (S45 work).

Inv 11 (NEW v0.2): every PlacedRoom in a PlacedCandidate is
reachable via the corridor_zones graph from the FloorRoomBrief's
entry_points set.

ENTRY POINTS NOTE: per Walk #3 self-audit concern #2, the upstream
"entry_points" surface needs clarification. v1 assumes entry points
are derivable from C8 corridor_zones with kind=ENTRY_STUB; the
orchestrator passes these in explicitly. Fallback: if no entry
points are provided, treat all CorridorZones touching the envelope
boundary as entry candidates.
"""
from __future__ import annotations

from collections import deque
from typing import Iterable

from .bounds import DEFAULT_EPSILON_M
from .schema import PlacedRoom


def _zones_adjacent(
    z1_x: float, z1_y: float, z1_w: float, z1_d: float,
    z2_x: float, z2_y: float, z2_w: float, z2_d: float,
    *,
    epsilon_m: float,
) -> bool:
    """Two axis-aligned rectangles are adjacent if they touch on at
    least one edge (within ε) and overlap on the perpendicular axis.
    """
    z1_right = z1_x + z1_w
    z2_right = z2_x + z2_w
    z1_top = z1_y + z1_d
    z2_top = z2_y + z2_d

    # Vertical touch (sharing a vertical wall): right of one ≈ left of other
    if (
        abs(z1_right - z2_x) <= epsilon_m
        or abs(z2_right - z1_x) <= epsilon_m
    ):
        # y-axis overlap?
        y_overlap = min(z1_top, z2_top) - max(z1_y, z2_y)
        if y_overlap > epsilon_m:
            return True

    # Horizontal touch (sharing a horizontal wall): top of one ≈ bottom of other
    if (
        abs(z1_top - z2_y) <= epsilon_m
        or abs(z2_top - z1_y) <= epsilon_m
    ):
        # x-axis overlap?
        x_overlap = min(z1_right, z2_right) - max(z1_x, z2_x)
        if x_overlap > epsilon_m:
            return True

    return False


def _room_adjacent_to_zone(
    room: PlacedRoom,
    z_x: float, z_y: float, z_w: float, z_d: float,
    *,
    epsilon_m: float,
) -> bool:
    """Room is adjacent to a corridor zone iff they share a wall."""
    return _zones_adjacent(
        room.x_m, room.y_m, room.width_m, room.depth_m,
        z_x, z_y, z_w, z_d,
        epsilon_m=epsilon_m,
    )


def all_rooms_reachable(
    *,
    placed_rooms: tuple[PlacedRoom, ...],
    corridor_zones: tuple[tuple[float, float, float, float], ...],
    entry_zone_indices: Iterable[int],
    epsilon_m: float = DEFAULT_EPSILON_M,
) -> tuple[bool, tuple[str, ...]]:
    """Per Inv 11 (v0.2-A6): run a BFS over (corridor_zones, rooms)
    starting from each entry zone, and determine whether every room
    is reachable.

    Args:
      placed_rooms: the rooms in this candidate.
      corridor_zones: tuple of (x, y, w, d) per zone — typically
        derived from CorridorDesignedCandidate.corridor_zones.
      entry_zone_indices: indices into corridor_zones that touch the
        envelope boundary (i.e., function as building entries).
      epsilon_m: tolerance for wall-touching detection.

    Returns:
      (reachable: bool, unreachable_room_ids: tuple[str, ...])

    A degenerate case: if there are NO corridor zones AND no entry
    zones, but there's only ONE room, that room is trivially
    reachable (it IS the building). For >1 room with no corridors,
    rooms are unreachable from each other (architecturally
    infeasible).
    """
    entry_indices_set = set(entry_zone_indices)

    # Degenerate cases first.
    if not placed_rooms:
        return (True, ())

    if not corridor_zones:
        # No corridors → only single-room layouts are reachable.
        if len(placed_rooms) == 1:
            return (True, ())
        return (
            False,
            tuple(r.room_id for r in placed_rooms[1:]),
        )

    if not entry_indices_set:
        # No entry points → unreachable by definition.
        return (
            False,
            tuple(r.room_id for r in placed_rooms),
        )

    # Build the adjacency graph.
    # Nodes: corridor zones (0..n-1) + rooms (room_id strings)
    # Edges: zone-zone adjacency, zone-room adjacency.
    n_zones = len(corridor_zones)

    # zone-zone adjacency
    zone_adj: dict[int, list[int]] = {i: [] for i in range(n_zones)}
    for i in range(n_zones):
        for j in range(i + 1, n_zones):
            zi = corridor_zones[i]
            zj = corridor_zones[j]
            if _zones_adjacent(
                zi[0], zi[1], zi[2], zi[3],
                zj[0], zj[1], zj[2], zj[3],
                epsilon_m=epsilon_m,
            ):
                zone_adj[i].append(j)
                zone_adj[j].append(i)

    # zone-room adjacency
    zone_to_rooms: dict[int, list[str]] = {i: [] for i in range(n_zones)}
    for room in placed_rooms:
        for i, z in enumerate(corridor_zones):
            if _room_adjacent_to_zone(
                room, z[0], z[1], z[2], z[3], epsilon_m=epsilon_m,
            ):
                zone_to_rooms[i].append(room.room_id)

    # BFS from entry zones.
    visited_zones: set[int] = set()
    visited_rooms: set[str] = set()
    queue: deque[int] = deque(entry_indices_set)
    visited_zones.update(entry_indices_set)

    while queue:
        zi = queue.popleft()
        # Mark all rooms adjacent to this zone as reachable.
        for rid in zone_to_rooms[zi]:
            visited_rooms.add(rid)
        # Continue BFS through adjacent zones.
        for zj in zone_adj[zi]:
            if zj not in visited_zones:
                visited_zones.add(zj)
                queue.append(zj)

    all_room_ids = {r.room_id for r in placed_rooms}
    unreachable = sorted(all_room_ids - visited_rooms)

    return (len(unreachable) == 0, tuple(unreachable))


__all__ = [
    "all_rooms_reachable",
]
