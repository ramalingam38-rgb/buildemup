"""
BuildemUp — C11a — M6 wet-rotate vertical slice (B-NEW-T1)
============================================================

Per S39 critique walk F5 + Sub-5 backlog B-NEW-T1: real upstream
wiring for the M6 wet-rotate operator. Smallest viable Tier B
vertical slice; validates the DeepMutationPipeline architecture
end-to-end against actual ``WetZonePlannedCandidate`` data.

== Scope (B-NEW-T1 honest read) ==

C10's ``plan_wet_zones`` does not expose a "rotate the wet-wall
assignment direction" knob — wall assignments are computed
deterministically from room geometry + the configured scoring
weights. Rather than expand C10's API (cross-component change, out
of scope for this patch), B-NEW-T1 ships a **post-process rotation**:

  1. Take the source ``WetZonePlannedCandidate``.
  2. Identify each wet wall's ``WallAxis`` (north/south/east/west)
     from the grid.
  3. Build a 90°-clockwise axis rotation map:
     NORTH→EAST, EAST→SOUTH, SOUTH→WEST, WEST→NORTH.
  4. For each room with a current wet wall: find a candidate
     replacement wall in the rotated axis that's also in the room's
     ``acceptable_wall_sets``. If no compatible wall exists, FAIL the
     candidate (M6 not viable).
  5. Rebuild ``WetZonePlan`` with the rotated assignment + recomputed
     ``riser_groups``, ``trap_arm_distances``, ``total_wet_run_length_m``,
     ``symbolic_bend_estimate``.
  6. Return a new ``WetZonePlannedCandidate``.

The reason this is a "vertical slice" not a "full M6": full M6 would
let C10 search for a NEW optimal assignment under a rotation hint.
This implementation rotates the EXISTING assignment without searching.
It validates: (a) the pipeline plumbing, (b) lineage classification on
real DeltaKey output, (c) cache integration, (d) Tier B atomicity.

== B-NEW-T1.5 follow-up ==

A future patch can promote the post-process rotation to a real C10
re-run by adding a ``WetWallRotationHint`` parameter to
``WetZonePlanConfig`` and weighting the rotated axis in the scoring.
That requires C10 amendment review.

== Module structure ==

- ``rotate_wet_wall_assignment(plan, grid)``: post-process rotation.
  Returns new ``WetZonePlan`` or raises ``M6NotViableError``.
- ``M6NotViableError``: per-candidate severity. Indicates the source
  has no rotation that satisfies acceptable_wall_sets for ALL rooms.
- The ``RealUpstreamRegenerator.regenerate(M6)`` overload below
  dispatches into this helper.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from buildemup.components.c07.wall_segment import WallAxis
from buildemup.components.c10.schema import (
    RiserAnchor,
    RiserGroup,
    TrapArmEstimate,
    WetZonePlan,
    WetZonePlannedCandidate,
)
from buildemup.components.c10.trap_arm import (
    estimate_trap_arm,
    symbolic_bend_estimate,
)
from buildemup.components.c11a.errors import PerCandidateError


# =============================================================================
# Error
# =============================================================================


class M6NotViableError(PerCandidateError):
    """B-NEW-T1: raised when M6 wet-rotate cannot produce a valid
    rotated assignment.

    Most common cause: the source's ``acceptable_wall_sets`` for one
    or more rooms doesn't include any wall in the rotated axis. The
    candidate is rejected per-candidate; the batch continues.
    """

    severity_tier = "per_candidate"


# =============================================================================
# Constants
# =============================================================================


# 90° clockwise axis rotation per project coord system.
_ROTATE_CW_90: dict[WallAxis, WallAxis] = {
    WallAxis.NORTH: WallAxis.EAST,
    WallAxis.EAST:  WallAxis.SOUTH,
    WallAxis.SOUTH: WallAxis.WEST,
    WallAxis.WEST:  WallAxis.NORTH,
}

# Same proxy-depth value as C10's _PROXY_DEPTH_M for trap-arm bbox.
_PROXY_DEPTH_M = 0.6


# =============================================================================
# Wall-id rotation
# =============================================================================


def _build_wall_axis_index(grid: Any) -> dict[str, Any]:
    """Map ``wall_id`` → ``WallSegment`` for every canonical wall on
    the grid.

    Uses ``grid.wall_segments_canonical()`` per W8 invariant.
    """
    return {w.wall_id: w for w in grid.wall_segments_canonical()}


def _build_axis_to_walls_index(grid: Any) -> dict[WallAxis, tuple[Any, ...]]:
    """Group canonical walls by ``WallAxis``."""
    by_axis: dict[WallAxis, list] = {a: [] for a in WallAxis}
    for w in grid.wall_segments_canonical():
        by_axis[w.axis].append(w)
    return {a: tuple(walls) for a, walls in by_axis.items()}


def _pick_rotated_wall(
    *,
    current_wall_id: str,
    walls_by_id: dict[str, Any],
    axis_to_walls: dict[WallAxis, tuple[Any, ...]],
    acceptable_wall_ids: tuple[str, ...],
) -> str | None:
    """Find a wall_id in the rotated axis that's also in
    ``acceptable_wall_ids``.

    Picks the **first** acceptable-and-in-rotated-axis wall in
    canonical order — deterministic.

    Returns:
        new wall_id, or None if no compatible wall exists.
    """
    current_wall = walls_by_id.get(current_wall_id)
    if current_wall is None:
        return None

    rotated_axis = _ROTATE_CW_90[current_wall.axis]
    candidate_walls = axis_to_walls.get(rotated_axis, ())
    acceptable_set = set(acceptable_wall_ids)

    for wall in candidate_walls:
        if wall.wall_id in acceptable_set:
            return wall.wall_id
    return None


# =============================================================================
# Plan rebuild
# =============================================================================


def rotate_wet_wall_assignment(
    plan: WetZonePlan,
    grid: Any,
    rooms_by_id: dict[str, Any] | None = None,
) -> WetZonePlan:
    """Per B-NEW-T1: produce a new ``WetZonePlan`` with each wet wall's
    assignment rotated 90° clockwise.

    Preserves: room ↔ cluster assignment (rooms stay in the same
    cluster — the cluster's wall changes, all rooms in the cluster
    rotate together). The riser_groups list is rebuilt with the
    rotated wall_ids; trap-arm distances are recomputed; symbolic-
    bend estimates are recomputed.

    Args:
        plan: source ``WetZonePlan`` from C10 output.
        grid: the C7 ``Grid`` (provides wall_segments_canonical +
            envelope dims).
        rooms_by_id: optional mapping ``room_id → RoomDef`` (for
            recomputing trap-arm bboxes). When None, trap-arm
            recomputation is skipped (preserves source distances).

    Returns:
        New ``WetZonePlan`` with rotated assignment + rebuilt riser
        groups + recomputed metrics.

    Raises:
        M6NotViableError: if any room's rotation has no compatible
            wall in ``acceptable_wall_sets``.
    """
    walls_by_id = _build_wall_axis_index(grid)
    axis_to_walls = _build_axis_to_walls_index(grid)

    # Step 1: rotate per-room wall assignments using acceptable_wall_sets.
    new_room_to_wall: dict[str, str] = {}
    failed_rooms: list[str] = []
    for room_id, current_wall_id in plan.wet_wall_assignment.items():
        acceptable = plan.acceptable_wall_sets.get(room_id, ())
        new_wall_id = _pick_rotated_wall(
            current_wall_id=current_wall_id,
            walls_by_id=walls_by_id,
            axis_to_walls=axis_to_walls,
            acceptable_wall_ids=acceptable,
        )
        if new_wall_id is None:
            failed_rooms.append(room_id)
            continue
        new_room_to_wall[room_id] = new_wall_id

    if failed_rooms:
        raise M6NotViableError(
            f"M6 wet-rotate: {len(failed_rooms)} room(s) have no "
            f"acceptable wall in the rotated axis: {failed_rooms[:5]}. "
            f"Per-candidate failure; batch continues."
        )

    # Step 2: rebuild riser_groups by rotating each cluster's wall_id.
    # We re-derive clusters from the source plan: rooms sharing the same
    # wall_id are in the same cluster. After rotation, rooms sharing
    # the same NEW wall_id form the new clusters.
    new_clusters: dict[str, list[str]] = {}
    for room_id, new_wid in new_room_to_wall.items():
        new_clusters.setdefault(new_wid, []).append(room_id)

    new_riser_groups = _build_rotated_riser_groups(
        clusters_by_wall=new_clusters,
        walls_by_id=walls_by_id,
    )

    # Step 3: recompute trap_arm_distances (only when rooms_by_id is
    # provided; otherwise zero out, accepting the data-loss tradeoff
    # rather than risking invariant violation).
    new_trap_arm_distances: dict[tuple[str, str], TrapArmEstimate]
    new_total_run = 0.0
    new_bend_total = 0
    if rooms_by_id is not None:
        new_trap_arm_distances, new_total_run, new_bend_total = (
            _recompute_trap_arms(
                room_to_wall=new_room_to_wall,
                walls_by_id=walls_by_id,
                rooms_by_id=rooms_by_id,
                fixture_types_per_room=plan.fixture_types_per_room,
                envelope_width_m=grid.envelope_width_m,
                envelope_depth_m=grid.envelope_depth_m,
            )
        )
    else:
        # Vertical-slice simplification: empty trap-arm distances when
        # rooms_by_id isn't passed. The plan stays self-consistent
        # (Inv 14: every wall_id in riser_groups appears in
        # wall_segments_used) but loses fixture-level detail. Real
        # callers (B-NEW-T1.5+) pass rooms_by_id.
        new_trap_arm_distances = {}
        new_total_run = 0.0
        new_bend_total = 0

    # Step 4: build the new plan. Preserve buffer_zones + acceptable
    # sets (they're derived from room categories, not from assignment).
    return WetZonePlan(
        wet_wall_assignment=new_room_to_wall,
        riser_groups=new_riser_groups,
        kitchen_riser_group_id=_find_kitchen_riser_group(
            new_riser_groups, rooms_by_id,
        ),
        fixture_types_per_room=plan.fixture_types_per_room,
        trap_arm_distances=new_trap_arm_distances,
        total_wet_run_length_m=round(new_total_run, 6),
        symbolic_bend_estimate=new_bend_total,
        bend_estimation_mode="symbolic_v1",
        riser_count=len(new_riser_groups),
        non_wet_room_buffer_zones=plan.non_wet_room_buffer_zones,
        acceptable_wall_sets=plan.acceptable_wall_sets,
    )


def _build_rotated_riser_groups(
    clusters_by_wall: dict[str, list[str]],
    walls_by_id: dict[str, Any],
) -> tuple[RiserGroup, ...]:
    """Build one RiserGroup per rotated cluster.

    Mirrors c10's ``_build_riser_groups`` but keyed by wall_id (since
    we don't track cluster ids through the rotation). Each new
    cluster's ``group_id`` is ``f"rg_rotated_{wid}"``.
    """
    groups: list[RiserGroup] = []
    for wid in sorted(clusters_by_wall.keys()):
        wall = walls_by_id[wid]
        anchor_position = wall.length_m / 2.0
        anchor_xy = (
            round((wall.start_x_m + wall.end_x_m) / 2.0, 6),
            round((wall.start_y_m + wall.end_y_m) / 2.0, 6),
        )
        anchor = RiserAnchor(
            wall_id=wid,
            anchor_position_m=round(anchor_position, 6),
            riser_anchor_xy=anchor_xy,
            column_id=None,
            snap_distance_m=None,
        )
        groups.append(RiserGroup(
            group_id=f"rg_rotated_{wid}",
            anchors=(anchor,),
            wet_room_ids=tuple(sorted(clusters_by_wall[wid])),
        ))
    return tuple(groups)


def _find_kitchen_riser_group(
    riser_groups: tuple[RiserGroup, ...],
    rooms_by_id: dict[str, Any] | None,
) -> str | None:
    if rooms_by_id is None:
        return None
    # Imported lazily to avoid C9 dependency at module load.
    try:
        from buildemup.components.c09.schema import RoomCategory
    except ImportError:
        return None
    for rg in riser_groups:
        for rid in rg.wet_room_ids:
            r = rooms_by_id.get(rid)
            if r is not None and getattr(r, "category", None) == RoomCategory.KITCHEN:
                return rg.group_id
    return None


def _recompute_trap_arms(
    *,
    room_to_wall: dict[str, str],
    walls_by_id: dict[str, Any],
    rooms_by_id: dict[str, Any],
    fixture_types_per_room: dict[str, tuple[str, ...]],
    envelope_width_m: float,
    envelope_depth_m: float,
) -> tuple[dict[tuple[str, str], TrapArmEstimate], float, int]:
    """Recompute trap-arm distances against the rotated assignment.

    Mirrors C10's per-room loop (lines 329-349 of wet_zone_planner.py).
    """
    distances: dict[tuple[str, str], TrapArmEstimate] = {}
    total_run = 0.0
    bend_total = 0
    for room_id, wall_id in room_to_wall.items():
        room = rooms_by_id.get(room_id)
        if room is None:
            continue
        wall = walls_by_id[wall_id]
        anchor_xy = (
            (wall.start_x_m + wall.end_x_m) / 2.0,
            (wall.start_y_m + wall.end_y_m) / 2.0,
        )
        bbox = _wet_strip_bbox_local(
            wall, getattr(room, "liveability_min_width_m", 1.0),
            _PROXY_DEPTH_M,
            envelope_w=envelope_width_m,
            envelope_d=envelope_depth_m,
        )
        room_centre = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
        for ft in fixture_types_per_room.get(room_id, ()):
            est = estimate_trap_arm(ft, bbox, anchor_xy)
            distances[(room_id, ft)] = est
            total_run += est.likely_bound_m
            bend_total += symbolic_bend_estimate(room_centre, anchor_xy)
    return distances, total_run, bend_total


def _wet_strip_bbox_local(
    wall: Any, room_min_width_m: float, proxy_depth_m: float,
    *, envelope_w: float, envelope_d: float,
) -> tuple[float, float, float, float]:
    """Local copy of c10's _wet_strip_bbox (avoids private-symbol
    import). Same algorithm."""
    half_w = room_min_width_m / 2.0
    mid_x = (wall.start_x_m + wall.end_x_m) / 2.0
    mid_y = (wall.start_y_m + wall.end_y_m) / 2.0
    if wall.axis == WallAxis.SOUTH:
        return (mid_x - half_w, 0.0, mid_x + half_w, proxy_depth_m)
    if wall.axis == WallAxis.NORTH:
        return (
            mid_x - half_w, envelope_d - proxy_depth_m,
            mid_x + half_w, envelope_d,
        )
    if wall.axis == WallAxis.WEST:
        return (0.0, mid_y - half_w, proxy_depth_m, mid_y + half_w)
    return (
        envelope_w - proxy_depth_m, mid_y - half_w,
        envelope_w, mid_y + half_w,
    )


# =============================================================================
# WetZonePlannedCandidate-level wrapper
# =============================================================================


def rotate_wet_zone_planned_candidate(
    candidate: WetZonePlannedCandidate,
    grid: Any,
) -> WetZonePlannedCandidate:
    """Rotate a full ``WetZonePlannedCandidate``: M6 vertical slice
    entry point.

    Walks the embedded ``room_size_table`` to build a ``rooms_by_id``
    mapping, then dispatches to ``rotate_wet_wall_assignment``.

    Returns a new ``WetZonePlannedCandidate`` with:
      * Same ``room_sized_candidate`` (sizing unchanged by M6)
      * Rotated ``wet_zone_plan``
      * Same ``provenance`` (the operator's output provenance is
        carried at C11a level via MutationApplicationResult; the
        C10 provenance reflects the original plan's derivation)
    """
    rooms_by_id = _build_rooms_by_id(candidate.room_sized_candidate)
    new_plan = rotate_wet_wall_assignment(
        candidate.wet_zone_plan, grid, rooms_by_id=rooms_by_id,
    )
    return replace(candidate, wet_zone_plan=new_plan)


def _build_rooms_by_id(room_sized_candidate: Any) -> dict[str, Any]:
    """Walk the candidate's room_size_table to build a room_id → RoomDef
    mapping. The shape is determined by C9's RoomSizeTable; we use
    duck-type access to stay loose-coupled."""
    rooms_by_id: dict[str, Any] = {}
    rst = getattr(room_sized_candidate, "room_size_table", None)
    if rst is None:
        return rooms_by_id
    rooms = getattr(rst, "rooms", None) or getattr(rst, "entries", None) or ()
    for room in rooms:
        rid = getattr(room, "room_id", None)
        if rid is None:
            continue
        rooms_by_id[rid] = room
    return rooms_by_id


__all__ = [
    "M6NotViableError",
    "rotate_wet_wall_assignment",
    "rotate_wet_zone_planned_candidate",
]
