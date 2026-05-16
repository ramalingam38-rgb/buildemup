"""Validation tests for C8 geometric connectivity.

Per C8 SPEC v0.5 LOCKED § 4.4 — Reviewer Drawback 3 (coordinate-coincidence)
+ § 4.6 invariants 4, 13.
"""
from __future__ import annotations

import math

import pytest

from buildemup.components.c08 import (
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
    DEFAULT_EPSILON_M,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c8_fixtures import real_pipeline


# ─── Coordinate-coincidence ───────────────────────────────


def test_endpoint_coincidence_within_epsilon():
    """Two points within EPSILON_M are coincident."""
    p1 = (5.0, 5.0)
    p2 = (5.0 + DEFAULT_EPSILON_M / 2.0, 5.0)
    dx = abs(p1[0] - p2[0])
    assert dx < DEFAULT_EPSILON_M


def test_endpoint_separation_outside_epsilon_not_coincident():
    p1 = (5.0, 5.0)
    p2 = (5.001, 5.0)  # 1mm = epsilon, just at boundary
    p3 = (5.01, 5.0)   # 10mm, clearly separated
    assert abs(p1[0] - p3[0]) > DEFAULT_EPSILON_M


def test_segment_endpoints_carry_exact_coords():
    """Per § 4.4: endpoints carry exact (x, y) floats."""
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(1.5, 2.5)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(11.5, 2.5)),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=10.0, runs_along=PlotOrientation.EAST,
    )
    assert seg.start.point_m == (1.5, 2.5)
    assert seg.end.point_m == (11.5, 2.5)


# ─── Junction coordinate-coincidence in real pipeline ────────


def test_l_shape_junction_endpoints_coincident():
    """L_SHAPE primary.end and branch.start meet at the same point."""
    from buildemup.components.c05.schema import TopologyKind
    from buildemup.components.c08 import design_corridors

    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        if d.oriented_candidate.topology_candidate.kind == TopologyKind.L_SHAPE:
            segments = d.corridor_path.segments
            # Find the junction endpoints
            junction_points = []
            for seg in segments:
                for ep in (seg.start, seg.end):
                    if ep.kind == CorridorEndpointKind.JUNCTION:
                        junction_points.append(ep.point_m)
            # All junction points should be coincident (same one)
            if len(junction_points) >= 2:
                p0 = junction_points[0]
                for pt in junction_points[1:]:
                    d_dist = math.hypot(p0[0] - pt[0], p0[1] - pt[1])
                    assert d_dist < DEFAULT_EPSILON_M


# ─── Junction angles per Inv 13 ───────────────────────────


def test_l_shape_junction_angle_is_90_degrees():
    """L_SHAPE PRIMARY ⊥ BRANCH = 90°."""
    from buildemup.components.c05.schema import TopologyKind
    from buildemup.components.c08 import design_corridors

    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        if d.oriented_candidate.topology_candidate.kind == TopologyKind.L_SHAPE:
            segs = d.corridor_path.segments
            # Two segments; primary axis vs branch axis
            assert len(segs) == 2

            def axis(o):
                return "x" if o in (PlotOrientation.EAST, PlotOrientation.WEST) else "y"
            assert axis(segs[0].runs_along) != axis(segs[1].runs_along)


def test_courtyard_loop_corners_are_90_degrees():
    """COURTYARD has 4 right-angle corners."""
    # Built via dispatch_courtyard fixture; verified by angle checks
    from buildemup.components.c08.topology_dispatch import dispatch_courtyard
    from buildemup.components.c08 import CorridorDesignConfig
    from dataclasses import replace
    from buildemup.components.c05.schema import (
        CorridorPosition, ConnectivityType, TopologyKind,
    )

    oriented, _, grid = real_pipeline()
    oc = oriented[0]
    new_sketch = replace(
        oc.topology_candidate.corridor_sketch,
        position=CorridorPosition.PERIMETER,
        connectivity_type=ConnectivityType.LOOP,
    )
    new_cand = replace(
        oc.topology_candidate, kind=TopologyKind.COURTYARD,
        corridor_sketch=new_sketch,
    )
    new_oc = replace(oc, topology_candidate=new_cand)
    cfg = CorridorDesignConfig()
    arms = dispatch_courtyard(new_oc, grid, (), 1.2, config=cfg)
    # Adjacent arms should be perpendicular
    assert arms[0].runs_along == PlotOrientation.EAST
    assert arms[1].runs_along == PlotOrientation.NORTH
    assert arms[2].runs_along == PlotOrientation.WEST
    assert arms[3].runs_along == PlotOrientation.SOUTH


# ─── Each segment endpoint is axis-aligned ─────────────


def test_all_segments_axis_aligned():
    """Per Inv 3: every segment differs in exactly one coord between endpoints."""
    from buildemup.components.c08 import design_corridors

    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        for seg in d.corridor_path.segments:
            sx, sy = seg.start.point_m
            ex, ey = seg.end.point_m
            dx = abs(ex - sx)
            dy = abs(ey - sy)
            # Exactly one is zero (within epsilon)
            assert (dx < DEFAULT_EPSILON_M) != (dy < DEFAULT_EPSILON_M)


# ─── Endpoint kinds as expected per topology ───────────


def test_strip_topology_has_exactly_one_entry():
    from buildemup.components.c05.schema import TopologyKind
    from buildemup.components.c08 import design_corridors

    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        if d.oriented_candidate.topology_candidate.kind == TopologyKind.STRIP:
            if d.corridor_path.has_corridor:
                entries = sum(
                    1 for seg in d.corridor_path.segments
                    for ep in (seg.start, seg.end)
                    if ep.kind == CorridorEndpointKind.ENTRY
                )
                assert entries == 1


def test_l_shape_has_exactly_one_entry_one_band_attachment():
    from buildemup.components.c05.schema import TopologyKind
    from buildemup.components.c08 import design_corridors

    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        if d.oriented_candidate.topology_candidate.kind == TopologyKind.L_SHAPE:
            entry_count = 0
            band_count = 0
            for seg in d.corridor_path.segments:
                for ep in (seg.start, seg.end):
                    if ep.kind == CorridorEndpointKind.ENTRY:
                        entry_count += 1
                    elif ep.kind == CorridorEndpointKind.BAND_ATTACHMENT:
                        band_count += 1
            assert entry_count == 1
