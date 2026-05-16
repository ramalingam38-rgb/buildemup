"""Validation tests for C8 topology dispatch.

Per C8 SPEC v0.5 LOCKED § 4.1 — STRIP / CENTRAL_SPINE / L_SHAPE / COURTYARD.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    TopologyKind,
)
from buildemup.components.c08 import (
    CorridorDesignConfig,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
    design_corridors,
)
from buildemup.components.c08.topology_dispatch import (
    dispatch_central_spine,
    dispatch_courtyard,
    dispatch_l_shape,
    dispatch_strip_linear,
    dispatch_strip_no_corridor,
    dispatch_topology,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c8_fixtures import (
    chennai_30x40,
    make_grid,
    make_grid_minimal,
    real_pipeline,
)


def _strip_oc(oriented):
    for oc in oriented:
        if oc.topology_candidate.kind == TopologyKind.STRIP:
            return oc
    return None


def _spine_oc(oriented):
    for oc in oriented:
        if oc.topology_candidate.kind == TopologyKind.CENTRAL_SPINE:
            return oc
    return None


def _l_shape_oc(oriented):
    for oc in oriented:
        if oc.topology_candidate.kind == TopologyKind.L_SHAPE:
            return oc
    return None


# ─── STRIP ──────────────────────────────────────────────


def test_strip_no_corridor_returns_empty():
    oriented, _, grid = real_pipeline()
    oc = _strip_oc(oriented)
    if oc is None:
        pytest.skip("no STRIP candidate")
    cfg = CorridorDesignConfig()
    result = dispatch_strip_no_corridor(oc, grid, (), config=cfg)
    assert result == ()


def test_strip_linear_returns_one_segment():
    oriented, _, grid = real_pipeline()
    oc = _strip_oc(oriented)
    if oc is None:
        pytest.skip("no STRIP candidate")
    cfg = CorridorDesignConfig()
    result = dispatch_strip_linear(oc, grid, (), 1.2, config=cfg)
    assert len(result) == 1
    assert result[0].kind == CorridorSegmentKind.PRIMARY


def test_strip_linear_segment_has_entry():
    oriented, _, grid = real_pipeline()
    oc = _strip_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    seg = dispatch_strip_linear(oc, grid, (), 1.2, config=cfg)[0]
    assert (
        seg.start.kind == CorridorEndpointKind.ENTRY
        or seg.end.kind == CorridorEndpointKind.ENTRY
    )


def test_strip_linear_axis_aligned_to_facing():
    oriented, _, grid = real_pipeline()
    oc = _strip_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    seg = dispatch_strip_linear(oc, grid, (), 1.2, config=cfg)[0]
    facing = oc.topology_candidate.corridor_sketch.runs_along
    assert seg.runs_along == facing


# ─── CENTRAL_SPINE ──────────────────────────────────


def test_central_spine_returns_one_segment():
    oriented, _, grid = real_pipeline()
    oc = _spine_oc(oriented)
    if oc is None:
        pytest.skip("no CENTRAL_SPINE")
    cfg = CorridorDesignConfig()
    result = dispatch_central_spine(oc, grid, (), 1.2, config=cfg)
    assert len(result) == 1
    assert result[0].kind == CorridorSegmentKind.PRIMARY


def test_central_spine_through_envelope_center():
    oriented, _, grid = real_pipeline()
    oc = _spine_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    seg = dispatch_central_spine(oc, grid, (), 1.2, config=cfg)[0]
    facing = oc.topology_candidate.corridor_sketch.runs_along
    if facing in (PlotOrientation.NORTH, PlotOrientation.SOUTH):
        # spine runs N/S; constant x = envelope_width / 2
        assert seg.start.point_m[0] == pytest.approx(grid.envelope_width_m / 2.0)
        assert seg.end.point_m[0] == pytest.approx(grid.envelope_width_m / 2.0)
    else:
        assert seg.start.point_m[1] == pytest.approx(grid.envelope_depth_m / 2.0)
        assert seg.end.point_m[1] == pytest.approx(grid.envelope_depth_m / 2.0)


def test_central_spine_full_envelope_length():
    oriented, _, grid = real_pipeline()
    oc = _spine_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    seg = dispatch_central_spine(oc, grid, (), 1.2, config=cfg)[0]
    facing = oc.topology_candidate.corridor_sketch.runs_along
    if facing in (PlotOrientation.NORTH, PlotOrientation.SOUTH):
        assert seg.length_m == pytest.approx(grid.envelope_depth_m)
    else:
        assert seg.length_m == pytest.approx(grid.envelope_width_m)


# ─── L_SHAPE ────────────────────────────────────────


def test_l_shape_returns_two_segments():
    oriented, _, grid = real_pipeline()
    oc = _l_shape_oc(oriented)
    if oc is None:
        pytest.skip("no L_SHAPE")
    cfg = CorridorDesignConfig()
    result = dispatch_l_shape(oc, grid, (), 1.2, config=cfg)
    assert len(result) == 2


def test_l_shape_has_primary_and_branch():
    oriented, _, grid = real_pipeline()
    oc = _l_shape_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    primary, branch = dispatch_l_shape(oc, grid, (), 1.2, config=cfg)
    assert primary.kind == CorridorSegmentKind.PRIMARY
    assert branch.kind == CorridorSegmentKind.BRANCH


def test_l_shape_segments_meet_at_junction():
    oriented, _, grid = real_pipeline()
    oc = _l_shape_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    primary, branch = dispatch_l_shape(oc, grid, (), 1.2, config=cfg)
    # primary.end and branch.start should both be JUNCTION at same point
    assert primary.end.kind == CorridorEndpointKind.JUNCTION
    assert branch.start.kind == CorridorEndpointKind.JUNCTION
    assert primary.end.point_m == pytest.approx(branch.start.point_m)


def test_l_shape_segments_perpendicular():
    oriented, _, grid = real_pipeline()
    oc = _l_shape_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    primary, branch = dispatch_l_shape(oc, grid, (), 1.2, config=cfg)

    def axis(o):
        return "x" if o in (PlotOrientation.EAST, PlotOrientation.WEST) else "y"
    assert axis(primary.runs_along) != axis(branch.runs_along)


# ─── COURTYARD ─────────────────────────────────────


def test_courtyard_returns_four_loop_arms():
    """Manually build a COURTYARD-like OC by replacing kind on a CENTRAL_SPINE."""
    oriented, _, grid = real_pipeline()
    oc = _spine_oc(oriented) or _strip_oc(oriented)
    if oc is None:
        pytest.skip()
    new_sketch = replace(
        oc.topology_candidate.corridor_sketch,
        position=CorridorPosition.PERIMETER,
        connectivity_type=ConnectivityType.LOOP,
    )
    new_cand = replace(
        oc.topology_candidate,
        kind=TopologyKind.COURTYARD,
        corridor_sketch=new_sketch,
    )
    new_oc = replace(oc, topology_candidate=new_cand)

    cfg = CorridorDesignConfig()
    result = dispatch_courtyard(new_oc, grid, (), 1.2, config=cfg)
    assert len(result) == 4
    for seg in result:
        assert seg.kind == CorridorSegmentKind.LOOP_ARM


def test_courtyard_has_one_entry():
    oriented, _, grid = real_pipeline()
    oc = _spine_oc(oriented) or _strip_oc(oriented)
    if oc is None:
        pytest.skip()
    new_sketch = replace(
        oc.topology_candidate.corridor_sketch,
        position=CorridorPosition.PERIMETER,
        connectivity_type=ConnectivityType.LOOP,
    )
    new_cand = replace(
        oc.topology_candidate,
        kind=TopologyKind.COURTYARD,
        corridor_sketch=new_sketch,
    )
    new_oc = replace(oc, topology_candidate=new_cand)
    cfg = CorridorDesignConfig()
    arms = dispatch_courtyard(new_oc, grid, (), 1.2, config=cfg)
    n_entries = sum(
        1 for arm in arms
        if arm.start.kind == CorridorEndpointKind.ENTRY
        or arm.end.kind == CorridorEndpointKind.ENTRY
    )
    assert n_entries == 1


# ─── Public dispatch ───────────────────────────────


def test_dispatch_topology_strip_no_corridor():
    oriented, _, grid = real_pipeline()
    oc = _strip_oc(oriented)
    if oc is None:
        pytest.skip()
    new_sketch = replace(
        oc.topology_candidate.corridor_sketch,
        position=CorridorPosition.NONE,
    )
    new_cand = replace(oc.topology_candidate, corridor_sketch=new_sketch)
    new_oc = replace(oc, topology_candidate=new_cand)
    cfg = CorridorDesignConfig()
    result = dispatch_topology(new_oc, grid, (), 1.2, config=cfg, candidate_index=0)
    assert result == ()


def test_dispatch_topology_routes_to_strip():
    oriented, _, grid = real_pipeline()
    oc = _strip_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    result = dispatch_topology(oc, grid, (), 1.2, config=cfg, candidate_index=0)
    assert len(result) == 1


def test_dispatch_topology_routes_to_l_shape():
    oriented, _, grid = real_pipeline()
    oc = _l_shape_oc(oriented)
    if oc is None:
        pytest.skip()
    cfg = CorridorDesignConfig()
    result = dispatch_topology(oc, grid, (), 1.2, config=cfg, candidate_index=0)
    assert len(result) == 2


def test_dispatch_topology_preserves_candidate_index_in_error():
    """Bad L_SHAPE → CorridorDispatchError with candidate_index."""
    from types import MappingProxyType
    from buildemup.components.c05.schema import ZoneBand
    from buildemup.components.c08 import CorridorDispatchError

    oriented, _, grid = real_pipeline()
    oc = _l_shape_oc(oriented)
    if oc is None:
        pytest.skip()
    bad_orient = replace(
        oc.orientation,
        refined_zone_bands=MappingProxyType({
            ZoneBand.PUBLIC: PlotOrientation.NORTH,
            ZoneBand.PRIVATE: PlotOrientation.NORTH,
        }),
    )
    bad_oc = replace(oc, orientation=bad_orient)
    cfg = CorridorDesignConfig()
    try:
        dispatch_topology(bad_oc, grid, (), 1.2, config=cfg, candidate_index=42)
    except CorridorDispatchError as e:
        assert e.candidate_index == 42
        assert e.failure_phase == "endpoint_construction"


# ─── End-to-end: design_corridors works ────────────


def test_design_corridors_e2e():
    """Pipeline: C5→C6→C7→C8 produces results for all candidate kinds."""
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    assert len(designed) == len(oriented)
    for d in designed:
        assert d.corridor_path is not None


def test_design_corridors_cardinality_preserved():
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    assert len(designed) == len(oriented)
    # Position pairing
    for i, d in enumerate(designed):
        assert d.oriented_candidate is oriented[i]


def test_design_corridors_provenance_populated():
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        assert d.provenance is not None
        assert len(d.provenance.rule_trace) > 0
        if d.corridor_path.has_corridor:
            assert d.provenance.envelope_area_consumed_m2 > 0
            assert d.provenance.envelope_area_fraction > 0


def test_design_corridors_empty_inputs():
    _, pa, grid = real_pipeline()
    designed = design_corridors((), grid, pa)
    assert designed == ()
