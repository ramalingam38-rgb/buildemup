"""
C16 Phase α — Geometric envelope assembly
============================================

Per v0.5 LOCKED spec § 3 Phase α:

INPUT:
    - SelectionResult (already validated)
    - UpstreamInputBundle (concrete C7/C9/C10/C12/C13/C14/C4 outputs)
    - JurisdictionProfile
    - RenderingConfig

PROCESSING:
    1. For each floor in MultiFloorPlacedCandidate.per_floor_placements:
       a. Convert C12.PlacedRoom (metres, envelope-SW origin) →
          C16.RoomGeometry (mm, LocalBuildingFrame origin).
       b. Build internal-partition WallSegments from C12.SharedEdge
          (the internal walls between rooms).
       c. Build perimeter WallSegments from C7.Grid.wall_segments.
       d. Build ColumnGeometry from C7.Grid.columns.
       e. Build PlumbingStack from C10.WetZonePlan.riser_groups.
       f. Build DoorGeometry from C13.Door + matching SharedEdge.
       g. (Window: empty for v1; B-C16-WINDOW-UPSTREAM-CONTRACT)
       h. Assign ElementIdentity to every element via
          compute_element_identity (R7b).
       i. R19 bounds check at every emitted coord via
          effective_*_bounds.
       j. Build FloorGeometry with the floor's own ElementIdentity.
       k. Collect WallCandidates for the orientation hierarchy.
    2. Compute LocalBuildingFrame orientation per R29 hierarchy.
    3. If JurisdictionProfile.orientation_lock present: validate per
       R29d (must be within EPSILON_ANGLE_DEG of a hierarchy candidate).
    4. Build GeospatialReference.

OUTPUT:
    EnvelopeAssembly carrying:
      - floor_geometries: tuple[FloorGeometry, ...]
      - local_building_frame: LocalBuildingFrame (marker)
      - geospatial_reference: GeospatialReference
      - orientation_decision: OrientationDecision (audit trail)
      - per_floor_wall_candidates: tuple[tuple[WallCandidate, ...], ...]
        (so Phase γ/δ can re-use without recomputing)

R-INVARIANTS ENFORCED HERE:
    R7a — banker's-rounded mm via upstream_adapter.m_to_mm
    R7b — stable IDs via compute_element_identity
    R19 — coordinate bounds via effective_*_bounds
    R29 — orientation hierarchy
    R29b — orientation_basis recorded on GeospatialReference
    R29c — semantic_identity_hash tiebreaks
    R29d — OrientationLock plausibility
    R33  — uniform C16_IDENTITY_GENERATION across all elements
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from buildemup.components.c16.config import (
    RenderingConfig,
    effective_building_bounds,
    effective_plot_bounds,
)
from buildemup.components.c16.contracts import (
    GeospatialReference,
    JurisdictionProfile,
    LocalBuildingFrame,
    SelectionResult,
)
from buildemup.components.c16.errors import (
    GeometryInconsistencyError,
    MissingUpstreamDataError,
)
from buildemup.components.c16.orientation import (
    OrientationDecision,
    WallCandidate,
    all_hierarchy_candidates,
    compute_orientation,
    validate_orientation_lock,
)
from buildemup.components.c16.schema import (
    ColumnGeometry,
    DoorGeometry,
    ElementIdentity,
    FloorGeometry,
    PlumbingStack,
    RoomGeometry,
    WallSegment,
    WindowGeometry,
    compute_element_identity,
)
from buildemup.components.c16.contracts import ElementKind
from buildemup.components.c16.upstream_adapter import (
    UpstreamInputBundle,
    m_to_mm,
    sorted_by_floor_label,
)


# ============================================================
# Phase α output
# ============================================================

@dataclass(frozen=True)
class EnvelopeAssembly:
    """Phase α's contract to downstream phases."""
    floor_geometries:        tuple[FloorGeometry, ...]
    local_building_frame:    LocalBuildingFrame
    geospatial_reference:    GeospatialReference
    orientation_decision:    OrientationDecision
    per_floor_wall_candidates: tuple[tuple[WallCandidate, ...], ...]


# ============================================================
# Bounds enforcement (R19)
# ============================================================

def _check_bounds(
    *,
    x_mm:    int,
    y_mm:    int,
    config:  RenderingConfig,
    label:   str,
) -> None:
    """R19: every emitted coord ∈ effective_plot_bounds.

    Per v0.3 A4, FloorGeometry coordinates live in LocalBuildingFrame.
    Per v0.4 A7 / v0.5 A4 — building bounds are effective ceiling.
    """
    bx, by, _, _ = effective_building_bounds(config)
    # LocalBuildingFrame can have negative coords (basement/balcony),
    # but typical residential building stays in [0, building_max].
    # We use the absolute magnitude for the X/Y check.
    if abs(x_mm) > bx:
        raise GeometryInconsistencyError(
            f"R19 violation: {label} x_mm={x_mm} exceeds building "
            f"bound ±{bx}.",
            invariant_id="R19",
            offending_ids=(label,),
        )
    if abs(y_mm) > by:
        raise GeometryInconsistencyError(
            f"R19 violation: {label} y_mm={y_mm} exceeds building "
            f"bound ±{by}.",
            invariant_id="R19",
            offending_ids=(label,),
        )


# ============================================================
# Phase α
# ============================================================

def execute_phase_alpha(
    *,
    selection_result:     SelectionResult,
    upstream_inputs:      UpstreamInputBundle,
    jurisdiction_profile: JurisdictionProfile,
    config:               RenderingConfig,
) -> EnvelopeAssembly:
    """Phase α main entry point.

    Raises:
        MissingUpstreamDataError — required upstream field is None/empty
        GeometryInconsistencyError — R19 bounds or R24 referential
        OrientationLockMismatchError — R29d implausible lock
    """
    mfc = upstream_inputs.multifloor_candidate
    if mfc is None:
        raise MissingUpstreamDataError(
            "Phase α: upstream_inputs.multifloor_candidate is None.",
            missing_field="multifloor_candidate",
            upstream_component="c12_vertical_alignment",
        )

    per_floor = getattr(mfc, "per_floor_placements", None)
    if not per_floor:
        raise MissingUpstreamDataError(
            "Phase α: MultiFloorPlacedCandidate has empty per_floor_placements.",
            missing_field="multifloor_candidate.per_floor_placements",
            upstream_component="c12_vertical_alignment",
        )

    sorted_floors = sorted_by_floor_label(per_floor)

    floor_geometries:           list[FloorGeometry] = []
    per_floor_wall_candidates:  list[tuple[WallCandidate, ...]] = []
    all_orient_walls:           list[WallCandidate] = []

    for floor_index, (floor_label, placed_candidate) in enumerate(sorted_floors):
        floor_elevation_mm = floor_index * m_to_mm(
            upstream_inputs.typical_floor_height_m
        )

        # ------------ Rooms (from C12) ------------
        rooms: list[RoomGeometry] = []
        placed_rooms = getattr(placed_candidate, "placed_rooms", ())
        for pr in placed_rooms:
            x_mm = m_to_mm(getattr(pr, "x_m", 0.0))
            y_mm = m_to_mm(getattr(pr, "y_m", 0.0))
            w_mm = m_to_mm(getattr(pr, "width_m", 0.0))
            d_mm = m_to_mm(getattr(pr, "depth_m", 0.0))
            room_id = getattr(pr, "room_id", "")
            category = getattr(pr, "category", "")
            if not room_id:
                raise MissingUpstreamDataError(
                    "Phase α: PlacedRoom carries empty room_id.",
                    missing_field="placed_rooms[i].room_id",
                    upstream_component="c12_vertical_alignment",
                )
            _check_bounds(
                x_mm=x_mm, y_mm=y_mm, config=config,
                label=f"floor:{floor_label}/room:{room_id}",
            )
            geometry_payload = {
                "x_mm": x_mm, "y_mm": y_mm,
                "width_mm": w_mm, "depth_mm": d_mm,
            }
            full_payload = {
                **geometry_payload,
                "room_id": room_id,
                "category": category,
            }
            identity = compute_element_identity(
                element_kind=ElementKind.WALL_INTERNAL_PARTITION,
                # We use a kind for the hash domain; rooms are not in
                # ElementKind taxonomy, so we anchor under a stable kind.
                # Stable-hash-domain choice documented for R27.
                floor_level=floor_index,
                geometry_defining_payload=geometry_payload,
                full_payload=full_payload,
            )
            rooms.append(RoomGeometry(
                identity=identity,
                room_id=room_id,
                category=category,
                x_mm=x_mm,
                y_mm=y_mm,
                width_mm=w_mm,
                depth_mm=d_mm,
            ))

        # ------------ Perimeter walls (from C7 Grid) ------------
        walls: list[WallSegment] = []
        wall_candidates_for_orientation: list[WallCandidate] = []
        grid = upstream_inputs.grids_by_floor.get(floor_label)
        if grid is not None:
            grid_walls = getattr(grid, "wall_segments", ())
            for w in grid_walls:
                wall_id = getattr(w, "wall_id", "")
                sx = m_to_mm(getattr(w, "start_x_m", 0.0))
                sy = m_to_mm(getattr(w, "start_y_m", 0.0))
                ex = m_to_mm(getattr(w, "end_x_m", 0.0))
                ey = m_to_mm(getattr(w, "end_y_m", 0.0))
                length_mm = m_to_mm(getattr(w, "length_m", 0.0))
                tags = getattr(w, "tags", frozenset())
                # Tag strings (works with either WallTag enum or str)
                tag_strs = frozenset(
                    (t.value if hasattr(t, "value") else str(t)) for t in tags
                )
                is_external = "external" in tag_strs
                is_load_bearing = "load_bearing" in tag_strs
                kind = (
                    ElementKind.WALL_EXTERNAL if is_external
                    else (
                        ElementKind.WALL_INTERNAL_LOAD_BEARING if is_load_bearing
                        else ElementKind.WALL_INTERNAL_PARTITION
                    )
                )
                _check_bounds(
                    x_mm=sx, y_mm=sy, config=config,
                    label=f"floor:{floor_label}/wall:{wall_id}/start",
                )
                _check_bounds(
                    x_mm=ex, y_mm=ey, config=config,
                    label=f"floor:{floor_label}/wall:{wall_id}/end",
                )
                geometry_payload = {
                    "start_x_mm": sx, "start_y_mm": sy,
                    "end_x_mm":   ex, "end_y_mm":   ey,
                }
                full_payload = {
                    **geometry_payload,
                    "wall_id": wall_id,
                    "tags":    sorted(tag_strs),
                    "kind":    kind.value,
                }
                identity = compute_element_identity(
                    element_kind=kind,
                    floor_level=floor_index,
                    geometry_defining_payload=geometry_payload,
                    full_payload=full_payload,
                )
                walls.append(WallSegment(
                    identity=identity,
                    wall_id=wall_id,
                    element_kind=kind,
                    start_x_mm=sx,
                    start_y_mm=sy,
                    end_x_mm=ex,
                    end_y_mm=ey,
                ))
                wall_candidates_for_orientation.append(WallCandidate(
                    wall_id=wall_id,
                    start_x_mm=sx,
                    start_y_mm=sy,
                    end_x_mm=ex,
                    end_y_mm=ey,
                    length_mm=length_mm,
                    semantic_identity_hash=identity.semantic_identity_hash,
                    is_external=is_external,
                    has_main_entry=False,  # set in door loop below
                ))

        # ------------ Internal partition walls (from C12 SharedEdge) ------------
        # Build a lookup: room_id → PlacedRoom (for geometric reference)
        room_by_id = {}
        for pr in placed_rooms:
            room_by_id[getattr(pr, "room_id", "")] = pr
        shared_edges = getattr(placed_candidate, "shared_edges", ())
        for se in shared_edges:
            room_a = getattr(se, "room_a_id", "")
            room_b = getattr(se, "room_b_id", "")
            axis = getattr(se, "axis", "horizontal")
            ovs = m_to_mm(getattr(se, "overlap_start_m", 0.0))
            ove = m_to_mm(getattr(se, "overlap_end_m", 0.0))
            wall_id = f"int:{room_a}<->{room_b}"
            # Resolve the partition's perpendicular coordinate against
            # the actual room geometries. C12 invariant: room_a_id <
            # room_b_id lex-ASC. The shared boundary is whichever face
            # of room_a touches room_b.
            #
            # "horizontal" axis = wall runs along X (overlap is in X).
            # The boundary Y is either room_a's max-Y (room_b above) or
            # room_a's min-Y (room_b below).
            #
            # "vertical" axis = wall runs along Y (overlap is in Y).
            # The boundary X is either room_a's max-X (room_b right) or
            # room_a's min-X (room_b left).
            ra = room_by_id.get(room_a)
            rb = room_by_id.get(room_b)
            if ra is None or rb is None:
                # Edge references unknown room — surface as R20 inconsistency
                raise GeometryInconsistencyError(
                    f"Phase α: SharedEdge ({room_a}, {room_b}) on floor "
                    f"{floor_label} references room not in placed_rooms.",
                    invariant_id="R20",
                    offending_ids=(room_a, room_b),
                )
            ra_x_mm = m_to_mm(getattr(ra, "x_m", 0.0))
            ra_y_mm = m_to_mm(getattr(ra, "y_m", 0.0))
            ra_w_mm = m_to_mm(getattr(ra, "width_m", 0.0))
            ra_d_mm = m_to_mm(getattr(ra, "depth_m", 0.0))
            rb_x_mm = m_to_mm(getattr(rb, "x_m", 0.0))
            rb_y_mm = m_to_mm(getattr(rb, "y_m", 0.0))
            if axis == "horizontal":
                # Wall along X at fixed Y; pick the Y where room_a and
                # room_b touch (within EPSILON_COORD_MM).
                ra_top    = ra_y_mm + ra_d_mm
                ra_bottom = ra_y_mm
                if abs(ra_top - rb_y_mm) <= 1:
                    boundary_y = ra_top
                elif abs(ra_bottom - (rb_y_mm + m_to_mm(getattr(rb, "depth_m", 0.0)))) <= 1:
                    boundary_y = ra_bottom
                else:
                    # Rooms aren't actually adjacent — degenerate; use ra_top
                    # as best-effort, log via documented behavior
                    boundary_y = ra_top
                sx, sy, ex, ey = ovs, boundary_y, ove, boundary_y
            else:
                # Vertical: wall along Y at fixed X
                ra_right = ra_x_mm + ra_w_mm
                ra_left  = ra_x_mm
                if abs(ra_right - rb_x_mm) <= 1:
                    boundary_x = ra_right
                elif abs(ra_left - (rb_x_mm + m_to_mm(getattr(rb, "width_m", 0.0)))) <= 1:
                    boundary_x = ra_left
                else:
                    boundary_x = ra_right
                sx, sy, ex, ey = boundary_x, ovs, boundary_x, ove
            _check_bounds(x_mm=sx, y_mm=sy, config=config,
                          label=f"floor:{floor_label}/partition:{wall_id}/start")
            _check_bounds(x_mm=ex, y_mm=ey, config=config,
                          label=f"floor:{floor_label}/partition:{wall_id}/end")
            geometry_payload = {
                "start_x_mm": sx, "start_y_mm": sy,
                "end_x_mm":   ex, "end_y_mm":   ey,
            }
            full_payload = {
                **geometry_payload,
                "wall_id":  wall_id,
                "room_a":   room_a,
                "room_b":   room_b,
                "kind":     ElementKind.WALL_INTERNAL_PARTITION.value,
            }
            identity = compute_element_identity(
                element_kind=ElementKind.WALL_INTERNAL_PARTITION,
                floor_level=floor_index,
                geometry_defining_payload=geometry_payload,
                full_payload=full_payload,
            )
            walls.append(WallSegment(
                identity=identity,
                wall_id=wall_id,
                element_kind=ElementKind.WALL_INTERNAL_PARTITION,
                start_x_mm=sx, start_y_mm=sy,
                end_x_mm=ex, end_y_mm=ey,
            ))

        # ------------ Doors (from C13 + C12 SharedEdge) ------------
        doors: list[DoorGeometry] = []
        edge_map = {
            (getattr(se, "room_a_id", ""), getattr(se, "room_b_id", "")): se
            for se in shared_edges
        }
        floor_doors = upstream_inputs.doors_by_floor.get(floor_label, ())
        for d in floor_doors:
            room_a = getattr(d, "room_a_id", "")
            room_b = getattr(d, "room_b_id", "")
            edge = edge_map.get((room_a, room_b))
            if edge is None:
                # Door references an edge that doesn't exist — upstream bug
                raise GeometryInconsistencyError(
                    f"Phase α: Door references non-existent SharedEdge "
                    f"({room_a}, {room_b}) on floor {floor_label}.",
                    invariant_id="R20",  # geometry parity surfaces this
                    offending_ids=(room_a, room_b),
                )
            edge_axis = getattr(edge, "axis", "horizontal")
            overlap_start_mm = m_to_mm(getattr(edge, "overlap_start_m", 0.0))
            pos_mm = m_to_mm(getattr(d, "position_along_edge_m", 0.0))
            clear_width_mm = m_to_mm(getattr(d, "clear_width_m", 0.0))
            leaf_mm = m_to_mm(getattr(d, "leaf_thickness_m", 0.0))
            is_main = bool(getattr(d, "is_main_entry", False))
            swing = getattr(d, "swing_direction", "into_room_a")
            hinge = getattr(d, "hinge_side", "start")
            # Resolve boundary coordinate the door sits on, against
            # actual PlacedRoom geometry (same logic as internal walls).
            ra = room_by_id.get(room_a)
            rb = room_by_id.get(room_b)
            if ra is None or rb is None:
                raise GeometryInconsistencyError(
                    f"Phase α: Door ({room_a}, {room_b}) references room "
                    f"not in placed_rooms on floor {floor_label}.",
                    invariant_id="R20",
                    offending_ids=(room_a, room_b),
                )
            ra_x_mm = m_to_mm(getattr(ra, "x_m", 0.0))
            ra_y_mm = m_to_mm(getattr(ra, "y_m", 0.0))
            ra_w_mm = m_to_mm(getattr(ra, "width_m", 0.0))
            ra_d_mm = m_to_mm(getattr(ra, "depth_m", 0.0))
            rb_x_mm = m_to_mm(getattr(rb, "x_m", 0.0))
            rb_y_mm = m_to_mm(getattr(rb, "y_m", 0.0))
            rb_w_mm = m_to_mm(getattr(rb, "width_m", 0.0))
            rb_d_mm = m_to_mm(getattr(rb, "depth_m", 0.0))
            if edge_axis == "horizontal":
                # Horizontal edge: wall along X at fixed Y → door anchor
                # has variable X (overlap_start + position) and fixed Y
                # at the boundary.
                if abs((ra_y_mm + ra_d_mm) - rb_y_mm) <= 1:
                    boundary_y = ra_y_mm + ra_d_mm
                elif abs(ra_y_mm - (rb_y_mm + rb_d_mm)) <= 1:
                    boundary_y = ra_y_mm
                else:
                    boundary_y = ra_y_mm + ra_d_mm
                ax, ay = overlap_start_mm + pos_mm, boundary_y
            else:
                # Vertical edge: wall along Y at fixed X.
                if abs((ra_x_mm + ra_w_mm) - rb_x_mm) <= 1:
                    boundary_x = ra_x_mm + ra_w_mm
                elif abs(ra_x_mm - (rb_x_mm + rb_w_mm)) <= 1:
                    boundary_x = ra_x_mm
                else:
                    boundary_x = ra_x_mm + ra_w_mm
                ax, ay = boundary_x, overlap_start_mm + pos_mm
            _check_bounds(x_mm=ax, y_mm=ay, config=config,
                          label=f"floor:{floor_label}/door:{room_a}<->{room_b}")
            door_id = f"door:{room_a}<->{room_b}"
            geometry_payload = {
                "anchor_x_mm":    ax,
                "anchor_y_mm":    ay,
                "axis":           edge_axis,
                "clear_width_mm": clear_width_mm,
            }
            full_payload = {
                **geometry_payload,
                "room_a":          room_a,
                "room_b":          room_b,
                "swing_direction": swing,
                "hinge_side":      hinge,
                "is_main_entry":   is_main,
            }
            kind = (
                ElementKind.DOOR_EXTERNAL if is_main
                else ElementKind.DOOR_INTERNAL
            )
            identity = compute_element_identity(
                element_kind=kind,
                floor_level=floor_index,
                geometry_defining_payload=geometry_payload,
                full_payload=full_payload,
            )
            doors.append(DoorGeometry(
                identity=identity,
                door_id=door_id,
                room_a_id=room_a,
                room_b_id=room_b,
                axis=edge_axis,
                anchor_x_mm=ax,
                anchor_y_mm=ay,
                clear_width_mm=clear_width_mm,
                swing_direction=swing,
                hinge_side=hinge,
                leaf_thickness_mm=leaf_mm,
                is_main_entry=is_main,
                element_kind=kind,
            ))
            # Mark main-entry walls for R29 hierarchy step 2.
            # Heuristic: the wall on the floor whose start/end coords
            # are closest to the door anchor is the entry-wall.
            # We do this by recomputing the WallCandidate tuple with
            # has_main_entry updated.
            if is_main and wall_candidates_for_orientation:
                # Tag the lex-min wall_id wall whose axis matches.
                # Simple deterministic rule: pick the EXTERNAL wall
                # whose start/end span contains the anchor along the
                # door's axis. If none matches, no tagging happens
                # (degenerate; R29 falls through to step 3).
                updated: list[WallCandidate] = []
                tagged = False
                for wc in wall_candidates_for_orientation:
                    matches = False
                    if not tagged and wc.is_external:
                        if edge_axis == "horizontal":
                            # External wall is horizontal too; anchor in its X span
                            wall_min_x = min(wc.start_x_mm, wc.end_x_mm)
                            wall_max_x = max(wc.start_x_mm, wc.end_x_mm)
                            wall_min_y = min(wc.start_y_mm, wc.end_y_mm)
                            wall_max_y = max(wc.start_y_mm, wc.end_y_mm)
                            if (
                                wall_min_x <= ax <= wall_max_x
                                and abs(ay - wall_min_y) <= 1
                                and abs(ay - wall_max_y) <= 1
                            ):
                                matches = True
                        else:
                            wall_min_y = min(wc.start_y_mm, wc.end_y_mm)
                            wall_max_y = max(wc.start_y_mm, wc.end_y_mm)
                            wall_min_x = min(wc.start_x_mm, wc.end_x_mm)
                            wall_max_x = max(wc.start_x_mm, wc.end_x_mm)
                            if (
                                wall_min_y <= ay <= wall_max_y
                                and abs(ax - wall_min_x) <= 1
                                and abs(ax - wall_max_x) <= 1
                            ):
                                matches = True
                    if matches:
                        updated.append(WallCandidate(
                            wall_id=wc.wall_id,
                            start_x_mm=wc.start_x_mm,
                            start_y_mm=wc.start_y_mm,
                            end_x_mm=wc.end_x_mm,
                            end_y_mm=wc.end_y_mm,
                            length_mm=wc.length_mm,
                            semantic_identity_hash=wc.semantic_identity_hash,
                            is_external=wc.is_external,
                            has_main_entry=True,
                        ))
                        tagged = True
                    else:
                        updated.append(wc)
                wall_candidates_for_orientation = updated

        # ------------ Columns (from C7 Grid) ------------
        columns: list[ColumnGeometry] = []
        if grid is not None:
            for c in getattr(grid, "columns", ()):
                grid_label = getattr(c, "grid_label", "")
                cx = m_to_mm(getattr(c, "x_m", 0.0))
                cy = m_to_mm(getattr(c, "y_m", 0.0))
                on_perimeter = bool(getattr(c, "on_perimeter", False))
                _check_bounds(x_mm=cx, y_mm=cy, config=config,
                              label=f"floor:{floor_label}/column:{grid_label}")
                # Standard column cross-section (per Indian RCC practice):
                # 230×300 for G+1, 300×300 for G+2+. Default to 230×230.
                col_w_mm = 230
                col_d_mm = 230
                geometry_payload = {
                    "x_mm": cx, "y_mm": cy,
                    "width_mm": col_w_mm, "depth_mm": col_d_mm,
                }
                full_payload = {
                    **geometry_payload,
                    "column_id":    grid_label,
                    "on_perimeter": on_perimeter,
                }
                identity = compute_element_identity(
                    element_kind=ElementKind.COLUMN,
                    floor_level=floor_index,
                    geometry_defining_payload=geometry_payload,
                    full_payload=full_payload,
                )
                columns.append(ColumnGeometry(
                    identity=identity,
                    column_id=grid_label,
                    x_mm=cx,
                    y_mm=cy,
                    width_mm=col_w_mm,
                    depth_mm=col_d_mm,
                    on_perimeter=on_perimeter,
                ))

        # ------------ Plumbing stacks (from C10 WetZonePlan) ------------
        stacks: list[PlumbingStack] = []
        plan = upstream_inputs.wet_zone_plans_by_floor.get(floor_label)
        if plan is not None:
            for rg in getattr(plan, "riser_groups", ()):
                group_id = getattr(rg, "group_id", "")
                anchors = getattr(rg, "anchors", ())
                wet_room_ids = tuple(getattr(rg, "wet_room_ids", ()))
                if not anchors:
                    raise MissingUpstreamDataError(
                        f"Phase α: WetZonePlan RiserGroup {group_id} "
                        f"has empty anchors tuple on floor {floor_label}.",
                        missing_field="riser_groups[i].anchors",
                        upstream_component="c10_wet_zone_planner",
                    )
                anchor = anchors[0]   # v1: exactly 1 anchor per group
                anchor_xy = getattr(anchor, "riser_anchor_xy", (0.0, 0.0))
                ax = m_to_mm(anchor_xy[0])
                ay = m_to_mm(anchor_xy[1])
                anchor_wall_id = getattr(anchor, "wall_id", "")
                _check_bounds(x_mm=ax, y_mm=ay, config=config,
                              label=f"floor:{floor_label}/stack:{group_id}")
                # All risers default to FRESH_WATER for v1. C10 doesn't
                # explicitly tag stack kind in the consumed surface; this
                # is documented as B-C16-STACK-KIND-FROM-C10.
                kind = ElementKind.PLUMBING_STACK_FRESH_WATER
                geometry_payload = {
                    "x_mm": ax, "y_mm": ay, "wall_id": anchor_wall_id,
                }
                full_payload = {
                    **geometry_payload,
                    "group_id":        group_id,
                    "serves_room_ids": list(sorted(wet_room_ids)),
                }
                identity = compute_element_identity(
                    element_kind=kind,
                    floor_level=floor_index,
                    geometry_defining_payload=geometry_payload,
                    full_payload=full_payload,
                )
                stacks.append(PlumbingStack(
                    identity=identity,
                    stack_id=group_id,
                    element_kind=kind,
                    x_mm=ax,
                    y_mm=ay,
                    wall_id=anchor_wall_id,
                    serves_room_ids=tuple(sorted(wet_room_ids)),
                ))

        # ------------ Floor's own ElementIdentity ------------
        # Per v0.3 A3: geometry_id of the floor = semantic hash of
        # the geometry-defining content (excluding annotations).
        floor_geometry_defining = {
            "floor_level":         floor_index,
            "floor_elevation_mm":  floor_elevation_mm,
            "rooms": tuple(
                r.identity.semantic_identity_hash for r in rooms
            ),
            "walls": tuple(
                w.identity.semantic_identity_hash for w in walls
            ),
            "columns": tuple(
                c.identity.semantic_identity_hash for c in columns
            ),
            "doors": tuple(
                d.identity.semantic_identity_hash for d in doors
            ),
            "plumbing_stacks": tuple(
                s.identity.semantic_identity_hash for s in stacks
            ),
        }
        floor_full = {
            **floor_geometry_defining,
            "floor_label": floor_label,
        }
        floor_identity = compute_element_identity(
            element_kind=ElementKind.SLAB_FLOOR,
            floor_level=floor_index,
            geometry_defining_payload=floor_geometry_defining,
            full_payload=floor_full,
        )

        # Sort tuples canonically for byte-equal replay (Inv R7c).
        # Rooms: by room_id; walls: by wall_id; doors: by door_id;
        # columns: by column_id; stacks: by stack_id.
        floor_geometries.append(FloorGeometry(
            floor_level=floor_index,
            floor_elevation_mm=floor_elevation_mm,
            identity=floor_identity,
            rooms=tuple(sorted(rooms, key=lambda r: r.room_id)),
            walls=tuple(sorted(walls, key=lambda w: w.wall_id)),
            doors=tuple(sorted(doors, key=lambda d: d.door_id)),
            windows=(),   # v1: no upstream window source (B-C16-WINDOW-UPSTREAM-CONTRACT)
            columns=tuple(sorted(columns, key=lambda c: c.column_id)),
            plumbing_stacks=tuple(sorted(stacks, key=lambda s: s.stack_id)),
        ))

        per_floor_wall_candidates.append(tuple(wall_candidates_for_orientation))
        all_orient_walls.extend(wall_candidates_for_orientation)

    # ------------ Orientation hierarchy (R29) ------------
    orientation_walls = tuple(all_orient_walls)
    decision = compute_orientation(
        walls=orientation_walls,
        jurisdiction_profile=jurisdiction_profile,
    )

    # R29d — OrientationLock plausibility
    if jurisdiction_profile.orientation_lock is not None:
        candidates = all_hierarchy_candidates(
            walls=orientation_walls,
            jurisdiction_profile=jurisdiction_profile,
        )
        validate_orientation_lock(
            lock=jurisdiction_profile.orientation_lock,
            candidate_decisions=candidates,
        )
        # Honor the lock — use locked orientation, but record basis from lock
        decision = OrientationDecision(
            orientation_deg=(
                jurisdiction_profile.orientation_lock.locked_x_axis_orientation_deg
            ),
            basis=jurisdiction_profile.orientation_lock.locked_origin_basis,
            chosen_wall_id=decision.chosen_wall_id,
        )

    # ------------ GeospatialReference ------------
    # The plot-aligned coords + plot North arrow come from C4 PlotAnalysis
    # in production; default to 0 if absent (sub-floor-bound buildings).
    plot_north = 0.0
    plot_analysis = upstream_inputs.plot_analysis
    if plot_analysis is not None:
        sp = getattr(plot_analysis, "sun_path", None)
        if sp is not None:
            plot_north = float(getattr(sp, "true_north_deg", 0.0))

    geospatial = GeospatialReference(
        local_origin_in_plot_mm=(0, 0),    # building SW = plot SW for residential
        rotation_from_plot_north_deg=decision.orientation_deg,
        plot_north_arrow_orientation_deg=plot_north,
        orientation_basis=decision.basis,
    )

    return EnvelopeAssembly(
        floor_geometries=tuple(floor_geometries),
        local_building_frame=LocalBuildingFrame(),
        geospatial_reference=geospatial,
        orientation_decision=decision,
        per_floor_wall_candidates=tuple(per_floor_wall_candidates),
    )
