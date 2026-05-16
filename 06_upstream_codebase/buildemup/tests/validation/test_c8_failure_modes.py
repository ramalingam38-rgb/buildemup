"""Validation tests for C8 failure modes per spec § 6."""
from __future__ import annotations

import pytest

from buildemup.components.c04.schema import PlotShape
from buildemup.components.c07.grid_generator import GridGenerator
from buildemup.components.c08 import (
    CorridorDesignConfig,
    CorridorDispatchError,
    CorridorTooNarrowError,
    design_corridors,
)
from buildemup.components.c08.schema import WidthQuantization
from buildemup.components.c08.width_selection import select_grid_fraction_width
from buildemup.tests.validation._c8_fixtures import (
    chennai_30x40,
    make_grid,
    make_grid_minimal,
    make_plot_analysis,
    real_pipeline,
)


# ─── Input-type validation ──────────────────────────────────────────


def test_design_corridors_rejects_non_grid():
    oriented, pa, _ = real_pipeline()
    with pytest.raises(TypeError, match="grid"):
        design_corridors(oriented, "not a grid", pa)  # type: ignore[arg-type]


def test_design_corridors_rejects_non_plot_analysis():
    oriented, _, grid = real_pipeline()
    with pytest.raises(TypeError, match="plot_analysis"):
        design_corridors(oriented, grid, "not a PA")  # type: ignore[arg-type]


def test_design_corridors_rejects_non_oriented_in_tuple():
    _, pa, grid = real_pipeline()
    with pytest.raises(TypeError, match="oriented_candidates"):
        design_corridors(("not_oc",), grid, pa)  # type: ignore[arg-type]


def test_design_corridors_empty_returns_empty():
    _, pa, grid = real_pipeline()
    result = design_corridors((), grid, pa)
    assert result == ()


# ─── B-066: non-rectangular plot ──────────────────────────────────


def test_design_corridors_rejects_non_rectangular_plot():
    """Per § 6: PlotShape != RECTANGULAR raises NotImplementedError (B-066)."""
    from dataclasses import replace
    oriented, pa, grid = real_pipeline()
    bad_pa = replace(pa, shape=PlotShape.L_SHAPED)
    with pytest.raises(NotImplementedError, match="RECTANGULAR"):
        design_corridors(oriented, grid, bad_pa)


# ─── CorridorTooNarrowError ──────────────────────────────────────


def test_corridor_too_narrow_when_bay_too_small():
    """Per § 4.3 / B-NNN-B: bay so small no GRID_FRACTION ≥ regulatory."""
    grid = make_grid_minimal(
        bay_x_m=1.0, bay_y_m=1.0,  # 0.75×1=0.75 < regulatory 0.9
        envelope_width_m=10.0, envelope_depth_m=10.0,
    )
    cfg = CorridorDesignConfig(regulatory_min_width_m=0.9)
    with pytest.raises(CorridorTooNarrowError):
        select_grid_fraction_width(grid, cfg)


def test_corridor_too_narrow_carries_diagnostic_metadata():
    grid = make_grid_minimal(bay_x_m=1.0, bay_y_m=1.0)
    cfg = CorridorDesignConfig(regulatory_min_width_m=0.9)
    try:
        select_grid_fraction_width(grid, cfg)
    except CorridorTooNarrowError as e:
        assert e.bay_min_m == 1.0
        assert e.regulatory_min_width_m == 0.9
        assert e.candidate_widths_m is not None
        assert len(e.candidate_widths_m) == 5  # 5 GRID_FRACTIONS


# ─── L_SHAPE defensive ─────────────────────────────────────────────


def test_l_shape_with_one_cardinal_dispatches_error():
    """L_SHAPE requires ≥ 2 distinct cardinal directions."""
    from dataclasses import replace
    from types import MappingProxyType

    from buildemup.components.c05.schema import (
        TopologyKind, ZoneBand,
    )
    from buildemup.components.c08.topology_dispatch import dispatch_topology
    from buildemup.domain.envelope import PlotOrientation

    oriented, pa, grid = real_pipeline()
    # Find an L_SHAPE candidate; force its refined_zone_bands to all-NORTH
    target = None
    for oc in oriented:
        if oc.topology_candidate.kind == TopologyKind.L_SHAPE:
            target = oc
            break
    if target is None:
        pytest.skip("No L_SHAPE candidate in pipeline output")

    bad_orientation = replace(
        target.orientation,
        refined_zone_bands=MappingProxyType({
            ZoneBand.PUBLIC: PlotOrientation.NORTH,
            ZoneBand.PRIVATE: PlotOrientation.NORTH,
        }),
    )
    bad_oc = replace(target, orientation=bad_orientation)
    cfg = CorridorDesignConfig()
    with pytest.raises(CorridorDispatchError, match="distinct cardinal"):
        dispatch_topology(
            bad_oc, grid, (), 1.2,
            config=cfg, candidate_index=0,
        )


def test_corridor_dispatch_error_metadata():
    """CorridorDispatchError carries diagnostic metadata per § 14.23."""
    err = CorridorDispatchError(
        "topology dispatch failed",
        candidate_index=2,
        topology_kind="l_shape",
        failure_phase="endpoint_construction",
        suggested_alternative_topologies=("strip",),
    )
    assert err.candidate_index == 2
    assert err.topology_kind == "l_shape"
    assert err.failure_phase == "endpoint_construction"
    assert err.suggested_alternative_topologies == ("strip",)


# ─── Self-intersection error ─────────────────────────────────────


def test_self_intersection_error_carries_diagnostic():
    """Per § 14.17: programmer-error eager raise."""
    from buildemup.components.c08 import CorridorSelfIntersectionError
    err = CorridorSelfIntersectionError(
        "segments overlap outside junction",
        segment_a_index=0, segment_b_index=1,
        overlap_box=(0.0, 0.0, 1.0, 1.0),
    )
    assert err.segment_a_index == 0
    assert err.segment_b_index == 1
    assert err.overlap_box == (0.0, 0.0, 1.0, 1.0)
