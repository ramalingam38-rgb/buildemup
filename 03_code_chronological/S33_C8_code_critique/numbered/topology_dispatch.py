"""
BuildemUp† — Component 8 (Corridor Designer) — Topology dispatch module.

Per C8 SPEC v0.5 LOCKED § 4.1 + § 4.4 + § 14.1.2.

Topology dispatch is the algorithm core. Given an OrientedCandidate +
ZoneBandEnvelopes + width + grid, produce CorridorSegments + endpoints.

Four topology kinds (per C5 § 3):
  - STRIP (T1 small, no corridor): degenerate path; no segments.
  - STRIP (T2/T3 linear): single PRIMARY segment.
  - CENTRAL_SPINE: PRIMARY through envelope center + ENTRY_STUB.
  - L_SHAPE: PRIMARY + BRANCH meeting at JUNCTION.
  - COURTYARD: 4 LOOP_ARM segments around central open core.

Each topology dispatcher returns a tuple of CorridorSegments. Endpoints
are anchored to ZoneBandEnvelopes per § 4.4.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    CorridorSketch,
    TopologyCandidate,
    TopologyKind,
    ZoneBand,
)
from buildemup.components.c06.schema import OrientedCandidate
from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08.errors import CorridorDispatchError
from buildemup.components.c08.schema import (
    CorridorDesignConfig,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
    ZoneBandEnvelope,
)
from buildemup.components.c08.spatial_model import find_envelope_for_band
from buildemup.components.c08.tolerances import STRUCTURAL_M, ARITHMETIC_M
from buildemup.domain.envelope import PlotOrientation

ARITHMETIC_M_FOR_STUB = ARITHMETIC_M  # local alias for B-138 stub-length zero check


def snap_junctions(
    segments: tuple[CorridorSegment, ...],
    epsilon_m: float = STRUCTURAL_M,
) -> tuple[CorridorSegment, ...]:
    """B-134 (S33): force every JUNCTION endpoint to a canonical coordinate.

    Per § 4.7 step 2: at every JUNCTION, after both adjoining segments are
    placed, force junction endpoint to exact coordinates — prevents
    EPSILON_M-scale drift from accumulating across multi-segment paths.

    Algorithm: bucket all JUNCTION endpoints by quantized coordinate
    (at half-epsilon), then within each bucket replace every endpoint's
    coordinate with the bucket's first-encountered value (the canonical
    representative). This is idempotent — running it twice gives the same
    result as running it once.

    For paths constructed via single-tuple-shared dispatchers (most v1
    dispatchers), this is a no-op safety net. For future paths constructed
    by composing sub-corridors (B-NNN follow-up work) it ensures Inv 4
    geometric-connectivity is robust against FP drift.

    Args:
        segments: tuple of CorridorSegment to normalize.
        epsilon_m: coordinate-quantization tolerance.

    Returns:
        New tuple of segments with junction endpoints snapped to canonical
        coordinates. Non-JUNCTION endpoints are unchanged.
    """
    from dataclasses import replace as _replace
    if not segments:
        return segments
    q = max(epsilon_m / 2.0, 1.0e-12)

    # Pass 1: bucket every JUNCTION endpoint by quantized key, recording
    # the canonical (first-seen) raw coordinate.
    canonical: dict[tuple[int, int], tuple[float, float]] = {}
    for seg in segments:
        for ep in (seg.start, seg.end):
            if ep.kind == CorridorEndpointKind.JUNCTION:
                key = (round(ep.point_m[0] / q), round(ep.point_m[1] / q))
                if key not in canonical:
                    canonical[key] = ep.point_m

    if not canonical:
        return segments

    # Pass 2: rebuild segments with canonical coordinates substituted.
    snapped: list[CorridorSegment] = []
    for seg in segments:
        new_start = seg.start
        new_end = seg.end
        if seg.start.kind == CorridorEndpointKind.JUNCTION:
            key = (round(seg.start.point_m[0] / q), round(seg.start.point_m[1] / q))
            canon = canonical.get(key)
            if canon is not None and canon != seg.start.point_m:
                new_start = _replace(seg.start, point_m=canon)
        if seg.end.kind == CorridorEndpointKind.JUNCTION:
            key = (round(seg.end.point_m[0] / q), round(seg.end.point_m[1] / q))
            canon = canonical.get(key)
            if canon is not None and canon != seg.end.point_m:
                new_end = _replace(seg.end, point_m=canon)
        if new_start is seg.start and new_end is seg.end:
            snapped.append(seg)
        else:
            snapped.append(_replace(seg, start=new_start, end=new_end))
    return tuple(snapped)


def _facing_axis(facing: PlotOrientation) -> str:
    """Return 'x' if facing EAST/WEST, 'y' if facing NORTH/SOUTH."""
    if facing in (PlotOrientation.EAST, PlotOrientation.WEST):
        return "x"
    if facing in (PlotOrientation.NORTH, PlotOrientation.SOUTH):
        return "y"
    raise ValueError(
        f"_facing_axis: facing must be cardinal; got {facing.value}"
    )


def _is_cardinal(d: PlotOrientation) -> bool:
    return d in (
        PlotOrientation.NORTH,
        PlotOrientation.EAST,
        PlotOrientation.SOUTH,
        PlotOrientation.WEST,
    )


def _envelope_center_along(
    envelope_width_m: float, envelope_depth_m: float, axis: str,
) -> float:
    if axis == "x":
        return envelope_width_m / 2.0
    return envelope_depth_m / 2.0


def _resolve_band_attachment(
    endpoint_pt: tuple[float, float],
    envelopes: tuple[ZoneBandEnvelope, ...],
) -> tuple[ZoneBand | None, PlotOrientation | None, int | None]:
    """B-137 (S33): identify which ZoneBandEnvelope this BAND_ATTACHMENT
    endpoint serves, by centroid-distance projection.

    Per § 4.4: BAND_ATTACHMENT endpoints carry ``attached_band``,
    ``attached_direction``, and ``attached_envelope_id`` so that the
    validator's Inv 6 ("PUBLIC, SERVICE, PRIVATE bands each have ≥ 1
    BAND_ATTACHMENT") is satisfiable from real data, not vacuously.

    Algorithm: for each envelope, compute Euclidean distance from
    ``endpoint_pt`` to ``envelope.centroid_m``; pick the closest envelope.
    Ties (rare in practice with cardinal-strip envelopes) break on first.

    Args:
        endpoint_pt: (x, y) of the endpoint in plot-local coords.
        envelopes: tuple of ZoneBandEnvelope from spatial_model.

    Returns:
        ``(attached_band, attached_direction, attached_envelope_id)`` for
        the closest envelope. All None if envelopes is empty (defensive
        — the caller produces an unattached endpoint).
    """
    if not envelopes:
        return None, None, None
    px, py = endpoint_pt
    best_idx = 0
    best_dist_sq = float("inf")
    for i, env in enumerate(envelopes):
        cx, cy = env.centroid_m
        dx = cx - px
        dy = cy - py
        d2 = dx * dx + dy * dy
        if d2 < best_dist_sq:
            best_dist_sq = d2
            best_idx = i
    chosen = envelopes[best_idx]
    return chosen.band, chosen.direction, best_idx


def _band_attachment_endpoint(
    endpoint_pt: tuple[float, float],
    envelopes: tuple[ZoneBandEnvelope, ...],
) -> CorridorEndpoint:
    """Construct a fully-tagged BAND_ATTACHMENT endpoint per B-137."""
    band, direction, env_id = _resolve_band_attachment(endpoint_pt, envelopes)
    return CorridorEndpoint(
        kind=CorridorEndpointKind.BAND_ATTACHMENT,
        point_m=endpoint_pt,
        attached_band=band,
        attached_direction=direction,
        attached_envelope_id=env_id,
    )


# =============================================================================
# Topology dispatchers
# =============================================================================


def dispatch_strip_no_corridor(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    envelopes: tuple[ZoneBandEnvelope, ...],
    *,
    config: CorridorDesignConfig,
) -> tuple[CorridorSegment, ...]:
    """STRIP topology with no corridor (T1 small plot).

    Per § 4.1 first row + § 4.3.2. Returns empty segments tuple; the
    has_corridor flag is set by the caller.
    """
    return ()


def dispatch_strip_linear(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    envelopes: tuple[ZoneBandEnvelope, ...],
    width_m: float,
    *,
    config: CorridorDesignConfig,
) -> tuple[CorridorSegment, ...]:
    """STRIP topology (T2/T3): single PRIMARY segment.

    Per § 4.1 second row. Single segment between facing-edge envelope and
    opposite-edge envelope. ENTRY at facing end; BAND_ATTACHMENT into
    perpendicular envelopes.
    """
    plot = oriented_candidate.topology_candidate
    sketch = plot.corridor_sketch
    facing = sketch.runs_along
    if not _is_cardinal(facing):
        raise CorridorDispatchError(
            f"STRIP linear requires cardinal runs_along; got {facing.value}",
            topology_kind=TopologyKind.STRIP.value,
            failure_phase="endpoint_construction",
        )

    # Centerline coord: envelope center along the perpendicular axis
    runs_axis = _facing_axis(facing)
    if runs_axis == "y":
        # corridor runs along y → centerline is x
        centerline = grid.envelope_width_m / 2.0
        if facing == PlotOrientation.NORTH:
            start_pt = (centerline, 0.0)
            end_pt = (centerline, grid.envelope_depth_m)
        else:  # SOUTH
            start_pt = (centerline, grid.envelope_depth_m)
            end_pt = (centerline, 0.0)
        length = grid.envelope_depth_m
    else:  # runs_axis == "x"
        centerline = grid.envelope_depth_m / 2.0
        if facing == PlotOrientation.EAST:
            start_pt = (0.0, centerline)
            end_pt = (grid.envelope_width_m, centerline)
        else:  # WEST
            start_pt = (grid.envelope_width_m, centerline)
            end_pt = (0.0, centerline)
        length = grid.envelope_width_m

    entry = CorridorEndpoint(
        kind=CorridorEndpointKind.ENTRY,
        point_m=start_pt,
        attached_direction=facing,
    )
    far_end = _band_attachment_endpoint(end_pt, envelopes)

    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=entry,
        end=far_end,
        constant_width_m=width_m,
        start_width_m=width_m,
        end_width_m=width_m,
        taper_zone_m=0.0,
        length_m=length,
        runs_along=facing,
    )
    return (seg,)


def dispatch_central_spine(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    envelopes: tuple[ZoneBandEnvelope, ...],
    width_m: float,
    *,
    config: CorridorDesignConfig,
) -> tuple[CorridorSegment, ...]:
    """CENTRAL_SPINE topology.

    Per § 4.1 third row. PRIMARY along corridor_sketch.runs_along axis through
    envelope center; ENTRY_STUB from facing-edge to spine; BAND_ATTACHMENTs
    both sides.
    """
    plot = oriented_candidate.topology_candidate
    sketch = plot.corridor_sketch
    spine_axis_facing = sketch.runs_along
    if not _is_cardinal(spine_axis_facing):
        raise CorridorDispatchError(
            f"CENTRAL_SPINE requires cardinal runs_along; got {spine_axis_facing.value}",
            topology_kind=TopologyKind.CENTRAL_SPINE.value,
            failure_phase="endpoint_construction",
        )

    spine_axis = _facing_axis(spine_axis_facing)
    if spine_axis == "y":
        # spine runs N/S
        spine_x = grid.envelope_width_m / 2.0
        spine_start = (spine_x, 0.0)
        spine_end = (spine_x, grid.envelope_depth_m)
        spine_length = grid.envelope_depth_m
    else:  # x
        spine_y = grid.envelope_depth_m / 2.0
        spine_start = (0.0, spine_y)
        spine_end = (grid.envelope_width_m, spine_y)
        spine_length = grid.envelope_width_m

    spine_start_ep = _band_attachment_endpoint(spine_start, envelopes)
    spine_end_ep = _band_attachment_endpoint(spine_end, envelopes)

    # B-138 (S33): ENTRY_STUB construction.
    #
    # CENTRAL_SPINE has two cases:
    #
    # (a) plot_facing aligns with spine_axis_facing (or its opposite): the
    #     spine itself runs from facing-edge to opposite-edge, and the facing
    #     end IS the entry. No stub needed; spine_start becomes the ENTRY.
    #
    # (b) plot_facing is perpendicular to spine_axis_facing: the spine runs
    #     across the plot, but the entry must come from plot.facing. An
    #     ENTRY_STUB segment connects the plot.facing edge to the spine
    #     perpendicular to it, joining at a JUNCTION on the spine.
    #
    # Pre-B-138 v1 behavior: case (b) was unimplemented; only case (a) shipped.
    plot_facing = oriented_candidate.topology_candidate.corridor_sketch.runs_along
    plot_facing_axis = _facing_axis(plot_facing)

    same_axis = (plot_facing_axis == spine_axis)
    if same_axis:
        # Case (a): facing aligns with spine axis. Make spine_start the ENTRY.
        # Choose the spine end nearest plot_facing so ENTRY is at the right
        # edge: e.g., if plot_facing == NORTH, the entry is at y=0; if SOUTH,
        # at y=envelope_depth.
        if plot_facing == spine_axis_facing:
            entry_pt = spine_start
            far_pt = spine_end
            far_ep = spine_end_ep
        else:
            # Opposite cardinal — start/end are flipped for ENTRY orientation.
            entry_pt = spine_end
            far_pt = spine_start
            far_ep = spine_start_ep
        primary = CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY,
            start=CorridorEndpoint(
                kind=CorridorEndpointKind.ENTRY,
                point_m=entry_pt,
                attached_direction=plot_facing,
            ),
            end=far_ep,
            constant_width_m=width_m,
            start_width_m=width_m,
            end_width_m=width_m,
            taper_zone_m=0.0,
            length_m=spine_length,
            runs_along=spine_axis_facing,
        )
        return (primary,)

    # Case (b): plot_facing perpendicular to spine_axis. Build ENTRY_STUB.
    stub_width_m = config.entry_stub_width_m
    # The stub runs along plot_facing axis (perpendicular to the spine).
    # Stub endpoint on the plot.facing edge:
    if plot_facing == PlotOrientation.NORTH:
        stub_start_pt = (grid.envelope_width_m / 2.0, 0.0)
    elif plot_facing == PlotOrientation.SOUTH:
        stub_start_pt = (grid.envelope_width_m / 2.0, grid.envelope_depth_m)
    elif plot_facing == PlotOrientation.EAST:
        stub_start_pt = (0.0, grid.envelope_depth_m / 2.0)
    elif plot_facing == PlotOrientation.WEST:
        stub_start_pt = (grid.envelope_width_m, grid.envelope_depth_m / 2.0)
    else:
        # Already gated above; defensive
        raise CorridorDispatchError(
            f"CENTRAL_SPINE ENTRY_STUB requires cardinal plot.facing; "
            f"got {plot_facing.value}",
            topology_kind=TopologyKind.CENTRAL_SPINE.value,
            failure_phase="endpoint_construction",
        )

    # The junction point lies on the spine at the projection of stub_start_pt
    # onto the spine. For a y-axis spine (spine_x is fixed), the junction is
    # at (spine_x, stub_start_pt[1]). For an x-axis spine: (stub_start_pt[0], spine_y).
    if spine_axis == "y":
        junction_pt = (spine_start[0], stub_start_pt[1])
        stub_length = abs(stub_start_pt[0] - junction_pt[0])
    else:  # spine_axis == "x"
        junction_pt = (stub_start_pt[0], spine_start[1])
        stub_length = abs(stub_start_pt[1] - junction_pt[1])

    if stub_length <= ARITHMETIC_M_FOR_STUB:
        # Degenerate — junction collides with stub_start. Treat as case (a):
        # spine itself is the entry path. (Should be unreachable in practice
        # for well-formed envelopes.)
        primary = CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY,
            start=CorridorEndpoint(
                kind=CorridorEndpointKind.ENTRY,
                point_m=spine_start,
                attached_direction=plot_facing,
            ),
            end=spine_end_ep,
            constant_width_m=width_m,
            start_width_m=width_m,
            end_width_m=width_m,
            taper_zone_m=0.0,
            length_m=spine_length,
            runs_along=spine_axis_facing,
        )
        return (primary,)

    # Junction endpoints (shared between stub and spine).
    junction_ep_for_stub = CorridorEndpoint(
        kind=CorridorEndpointKind.JUNCTION,
        point_m=junction_pt,
    )
    junction_ep_for_spine_a = CorridorEndpoint(
        kind=CorridorEndpointKind.JUNCTION,
        point_m=junction_pt,
    )
    junction_ep_for_spine_b = CorridorEndpoint(
        kind=CorridorEndpointKind.JUNCTION,
        point_m=junction_pt,
    )

    # Stub: ENTRY at plot-facing edge, JUNCTION at spine.
    stub = CorridorSegment(
        kind=CorridorSegmentKind.ENTRY_STUB,
        start=CorridorEndpoint(
            kind=CorridorEndpointKind.ENTRY,
            point_m=stub_start_pt,
            attached_direction=plot_facing,
        ),
        end=junction_ep_for_stub,
        constant_width_m=stub_width_m,
        start_width_m=stub_width_m,
        end_width_m=stub_width_m,
        taper_zone_m=0.0,
        length_m=stub_length,
        runs_along=plot_facing,
    )

    # Spine is split at the junction into two PRIMARY segments. (Single
    # spine segment with mid-point JUNCTION is not representable in the
    # current schema where each segment has start+end endpoints; splitting
    # is the natural representation.)
    if spine_axis == "y":
        # spine runs along y; junction at (spine_x, jy).
        jy = junction_pt[1]
        # Segment A: from spine_start to junction.
        if abs(jy - spine_start[1]) > ARITHMETIC_M_FOR_STUB:
            spine_a = CorridorSegment(
                kind=CorridorSegmentKind.PRIMARY,
                start=spine_start_ep,
                end=junction_ep_for_spine_a,
                constant_width_m=width_m,
                start_width_m=width_m,
                end_width_m=width_m,
                taper_zone_m=0.0,
                length_m=abs(jy - spine_start[1]),
                runs_along=spine_axis_facing,
            )
        else:
            spine_a = None
        # Segment B: from junction to spine_end.
        if abs(spine_end[1] - jy) > ARITHMETIC_M_FOR_STUB:
            spine_b = CorridorSegment(
                kind=CorridorSegmentKind.PRIMARY,
                start=junction_ep_for_spine_b,
                end=spine_end_ep,
                constant_width_m=width_m,
                start_width_m=width_m,
                end_width_m=width_m,
                taper_zone_m=0.0,
                length_m=abs(spine_end[1] - jy),
                runs_along=spine_axis_facing,
            )
        else:
            spine_b = None
    else:
        jx = junction_pt[0]
        if abs(jx - spine_start[0]) > ARITHMETIC_M_FOR_STUB:
            spine_a = CorridorSegment(
                kind=CorridorSegmentKind.PRIMARY,
                start=spine_start_ep,
                end=junction_ep_for_spine_a,
                constant_width_m=width_m,
                start_width_m=width_m,
                end_width_m=width_m,
                taper_zone_m=0.0,
                length_m=abs(jx - spine_start[0]),
                runs_along=spine_axis_facing,
            )
        else:
            spine_a = None
        if abs(spine_end[0] - jx) > ARITHMETIC_M_FOR_STUB:
            spine_b = CorridorSegment(
                kind=CorridorSegmentKind.PRIMARY,
                start=junction_ep_for_spine_b,
                end=spine_end_ep,
                constant_width_m=width_m,
                start_width_m=width_m,
                end_width_m=width_m,
                taper_zone_m=0.0,
                length_m=abs(spine_end[0] - jx),
                runs_along=spine_axis_facing,
            )
        else:
            spine_b = None

    out = [stub]
    if spine_a is not None:
        out.append(spine_a)
    if spine_b is not None:
        out.append(spine_b)
    return tuple(out)


def dispatch_l_shape(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    envelopes: tuple[ZoneBandEnvelope, ...],
    width_m: float,
    *,
    config: CorridorDesignConfig,
) -> tuple[CorridorSegment, ...]:
    """L_SHAPE topology.

    Per § 4.1 fourth row. One PRIMARY arm + one BRANCH arm meeting at a
    JUNCTION; both axis-aligned. ENTRY on the longer arm by default.

    For v1 we anchor the L's corner at the envelope center; PRIMARY runs
    along the sketch.runs_along; BRANCH runs perpendicular.
    """
    plot = oriented_candidate.topology_candidate
    sketch = plot.corridor_sketch
    primary_facing = sketch.runs_along
    if not _is_cardinal(primary_facing):
        raise CorridorDispatchError(
            f"L_SHAPE requires cardinal runs_along; got {primary_facing.value}",
            topology_kind=TopologyKind.L_SHAPE.value,
            failure_phase="endpoint_construction",
        )

    # Junction at envelope center
    junction_x = grid.envelope_width_m / 2.0
    junction_y = grid.envelope_depth_m / 2.0
    junction_pt = (junction_x, junction_y)

    primary_axis = _facing_axis(primary_facing)
    if primary_axis == "x":
        # PRIMARY runs E/W; BRANCH runs N/S
        primary_start_pt = (0.0, junction_y) if primary_facing == PlotOrientation.EAST else (grid.envelope_width_m, junction_y)
        branch_facing = PlotOrientation.NORTH  # arbitrary; perpendicular cardinal
        branch_end_pt = (junction_x, grid.envelope_depth_m)
        primary_length = grid.envelope_width_m / 2.0
        branch_length = grid.envelope_depth_m / 2.0
    else:  # primary_axis == 'y'
        primary_start_pt = (junction_x, 0.0) if primary_facing == PlotOrientation.NORTH else (junction_x, grid.envelope_depth_m)
        branch_facing = PlotOrientation.EAST
        branch_end_pt = (grid.envelope_width_m, junction_y)
        primary_length = grid.envelope_depth_m / 2.0
        branch_length = grid.envelope_width_m / 2.0

    junction_ep_primary = CorridorEndpoint(
        kind=CorridorEndpointKind.JUNCTION,
        point_m=junction_pt,
    )
    junction_ep_branch = CorridorEndpoint(
        kind=CorridorEndpointKind.JUNCTION,
        point_m=junction_pt,
    )

    entry_ep = CorridorEndpoint(
        kind=CorridorEndpointKind.ENTRY,
        point_m=primary_start_pt,
        attached_direction=primary_facing,
    )
    branch_end_ep = _band_attachment_endpoint(branch_end_pt, envelopes)

    primary = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=entry_ep,
        end=junction_ep_primary,
        constant_width_m=width_m,
        start_width_m=width_m,
        end_width_m=width_m,
        taper_zone_m=0.0,
        length_m=primary_length,
        runs_along=primary_facing,
    )
    branch = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH,
        start=junction_ep_branch,
        end=branch_end_ep,
        constant_width_m=width_m,
        start_width_m=width_m,
        end_width_m=width_m,
        taper_zone_m=0.0,
        length_m=branch_length,
        runs_along=branch_facing,
    )
    return (primary, branch)


def dispatch_courtyard(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    envelopes: tuple[ZoneBandEnvelope, ...],
    width_m: float,
    *,
    config: CorridorDesignConfig,
) -> tuple[CorridorSegment, ...]:
    """COURTYARD topology.

    Per § 4.1 fifth row. Four LOOP_ARM segments forming a closed loop around
    the central open core (envelope_width-2t, envelope_depth-2t rectangle).
    ENTRY on the arm matching plot.facing.

    Loop arms run along the perimeter at offset = corridor_width/2 from each
    inner core edge (so the corridor wall is on the perimeter side and the
    loop sits between perimeter-edge and core).
    """
    plot = oriented_candidate.topology_candidate
    plot_facing = plot.corridor_sketch.runs_along
    if not _is_cardinal(plot_facing):
        raise CorridorDispatchError(
            f"COURTYARD requires cardinal facing; got {plot_facing.value}",
            topology_kind=TopologyKind.COURTYARD.value,
            failure_phase="endpoint_construction",
        )

    inner_clear = config.courtyard_loop_inner_clear_m
    # Place the loop-corridor band along the inner perimeter, of width=width_m,
    # leaving a central core of (envelope_width - 2*(width_m + inner_clear)) ×
    # (envelope_depth - 2*(width_m + inner_clear)). For v1, we keep the
    # corridor along the OUTER edges of the buildable envelope (i.e., the
    # outer-most perimeter band of width=width_m), which means the inner
    # core area is what's left.
    w = width_m
    ew = grid.envelope_width_m
    ed = grid.envelope_depth_m

    # Centerlines for each arm:
    south_centerline_y = w / 2.0
    north_centerline_y = ed - w / 2.0
    west_centerline_x = w / 2.0
    east_centerline_x = ew - w / 2.0

    # Arm corner points (the 4 corners of the loop)
    sw = (w / 2.0, w / 2.0)  # not used directly; using arm endpoints
    # We model the 4 arms as:
    #   south arm: (0, south_y) to (ew, south_y)  ← horizontal across south
    #   east  arm: (east_x, 0) to (east_x, ed)    ← vertical along east
    #   north arm: (ew, north_y) to (0, north_y)  ← horizontal across north
    #   west  arm: (west_x, ed) to (west_x, 0)    ← vertical along west
    # Each arm meets the next at a JUNCTION at the corner.
    # For simplicity, each arm spans the full envelope dimension; junction
    # overlap is handled at area-accounting time.

    arms_data = [
        # (kind, start_pt, end_pt, runs_along, length)
        ("south", (0.0, south_centerline_y), (ew, south_centerline_y), PlotOrientation.EAST, ew),
        ("east", (east_centerline_x, 0.0), (east_centerline_x, ed), PlotOrientation.NORTH, ed),
        ("north", (ew, north_centerline_y), (0.0, north_centerline_y), PlotOrientation.WEST, ew),
        ("west", (west_centerline_x, ed), (west_centerline_x, 0.0), PlotOrientation.SOUTH, ed),
    ]

    # Map plot_facing to which arm gets the ENTRY
    entry_arm_label = {
        PlotOrientation.SOUTH: "south",
        PlotOrientation.EAST: "east",
        PlotOrientation.NORTH: "north",
        PlotOrientation.WEST: "west",
    }.get(plot_facing, "south")

    segments: list[CorridorSegment] = []
    for label, start_pt, end_pt, runs_along, length in arms_data:
        if label == entry_arm_label:
            start_ep = CorridorEndpoint(
                kind=CorridorEndpointKind.ENTRY,
                point_m=start_pt,
                attached_direction=plot_facing,
            )
        else:
            start_ep = CorridorEndpoint(
                kind=CorridorEndpointKind.JUNCTION,
                point_m=start_pt,
            )
        end_ep = CorridorEndpoint(
            kind=CorridorEndpointKind.JUNCTION,
            point_m=end_pt,
        )
        segments.append(CorridorSegment(
            kind=CorridorSegmentKind.LOOP_ARM,
            start=start_ep,
            end=end_ep,
            constant_width_m=w,
            start_width_m=w,
            end_width_m=w,
            taper_zone_m=0.0,
            length_m=length,
            runs_along=runs_along,
        ))
    return tuple(segments)


# =============================================================================
# Public dispatch
# =============================================================================


def dispatch_topology(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    envelopes: tuple[ZoneBandEnvelope, ...],
    width_m: float,
    *,
    config: CorridorDesignConfig,
    candidate_index: int = 0,
) -> tuple[CorridorSegment, ...]:
    """Public dispatch on TopologyKind. Per § 4.1.

    Args:
        oriented_candidate: from C6.
        grid: from C7.
        envelopes: derived from C8 spatial_model.
        width_m: chosen corridor width.
        config: tunables.
        candidate_index: position in input tuple (for error diagnostics).

    Returns:
        Tuple of CorridorSegment representing the corridor body. Empty
        tuple for STRIP-with-no-corridor.

    Raises:
        CorridorDispatchError on any geometric inconsistency.
    """
    plot = oriented_candidate.topology_candidate
    kind = plot.kind
    sketch = plot.corridor_sketch

    if kind == TopologyKind.STRIP:
        if sketch.position == CorridorPosition.NONE:
            return dispatch_strip_no_corridor(
                oriented_candidate, grid, envelopes, config=config,
            )
        return dispatch_strip_linear(
            oriented_candidate, grid, envelopes, width_m, config=config,
        )

    if kind == TopologyKind.CENTRAL_SPINE:
        return dispatch_central_spine(
            oriented_candidate, grid, envelopes, width_m, config=config,
        )

    if kind == TopologyKind.L_SHAPE:
        # Defensive: L_SHAPE needs ≥ 2 distinct cardinal directions in
        # refined_zone_bands per § 6.
        directions = {
            d for d in oriented_candidate.orientation.refined_zone_bands.values()
            if _is_cardinal(d)
        }
        if len(directions) < 2:
            raise CorridorDispatchError(
                f"L_SHAPE requires >= 2 distinct cardinal directions in "
                f"refined_zone_bands; got {len(directions)}",
                candidate_index=candidate_index,
                topology_kind=kind.value,
                failure_phase="endpoint_construction",
                suggested_alternative_topologies=(TopologyKind.STRIP.value,),
            )
        return dispatch_l_shape(
            oriented_candidate, grid, envelopes, width_m, config=config,
        )

    if kind == TopologyKind.COURTYARD:
        return dispatch_courtyard(
            oriented_candidate, grid, envelopes, width_m, config=config,
        )

    raise CorridorDispatchError(
        f"Unknown TopologyKind: {kind!r}",
        candidate_index=candidate_index,
        topology_kind=str(kind),
        failure_phase="endpoint_construction",
    )


__all__ = [
    "dispatch_topology",
    "dispatch_strip_no_corridor",
    "dispatch_strip_linear",
    "dispatch_central_spine",
    "dispatch_l_shape",
    "dispatch_courtyard",
]
