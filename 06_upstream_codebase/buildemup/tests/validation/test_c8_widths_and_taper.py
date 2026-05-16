"""Validation tests for C8 width selection + junction propagation + taper.

Per C8 SPEC v0.5 LOCKED § 4.3 / § 4.3.1 / § 4.10 / § 14.20.
"""
from __future__ import annotations

import pytest

from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08 import (
    CorridorDesignConfig,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
    WidthPropagation,
)
from buildemup.components.c08.junction_propagation import (
    propagate_junction_widths,
)
from buildemup.components.c08.width_selection import resolve_taper_zone_m
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c8_fixtures import make_grid_minimal, make_segment


# ─── Taper zone resolution ──────────────────────────────────


def test_resolve_taper_default_uses_bay_min():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=4.0)
    cfg = CorridorDesignConfig()
    taper, truncated = resolve_taper_zone_m(cfg, grid, segment_length_m=10.0)
    assert taper == 3.0  # min(bay_x, bay_y)
    assert truncated is False


def test_resolve_taper_truncates_when_too_large():
    """Per § 4.3.1: truncate to length/2 when 2×default > length."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig()
    taper, truncated = resolve_taper_zone_m(cfg, grid, segment_length_m=4.0)
    assert taper == 2.0  # 4.0 / 2
    assert truncated is True


def test_resolve_taper_explicit_default_overrides():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.0)
    cfg = CorridorDesignConfig(taper_zone_m_default=1.5)
    taper, truncated = resolve_taper_zone_m(cfg, grid, segment_length_m=10.0)
    assert taper == 1.5
    assert truncated is False


def test_resolve_taper_explicit_default_still_truncates():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.0)
    cfg = CorridorDesignConfig(taper_zone_m_default=5.0)
    taper, truncated = resolve_taper_zone_m(cfg, grid, segment_length_m=4.0)
    assert taper == 2.0
    assert truncated is True


# ─── Junction propagation: JUNCTION_LOCAL_ONLY (default) ──────


def _make_l_shape_segments(primary_w: float, branch_w: float):
    """Build PRIMARY (E-running) + BRANCH (N-running) meeting at (5, 5)."""
    p_start = CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0))
    p_end = CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0))
    primary = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY, start=p_start, end=p_end,
        constant_width_m=primary_w, start_width_m=primary_w, end_width_m=primary_w,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.EAST,
    )
    b_start = CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0))
    b_end = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(5.0, 10.0))
    branch = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH, start=b_start, end=b_end,
        constant_width_m=branch_w, start_width_m=branch_w, end_width_m=branch_w,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.NORTH,
    )
    return [primary, branch]


def test_junction_local_wide_primary_unchanged():
    """Per § 4.10: PRIMARY (1.65) is the wide one; unchanged."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig()
    segs = _make_l_shape_segments(primary_w=1.65, branch_w=1.20)
    new_segs, _ = propagate_junction_widths(segs, config=cfg, grid=grid)
    assert new_segs[0].constant_width_m == 1.65
    assert new_segs[0].start_width_m == 1.65
    assert new_segs[0].end_width_m == 1.65


def test_junction_local_narrow_branch_widens_at_junction():
    """BRANCH (1.20) gets junction-end widened to 1.65 (junction-max)."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig()
    segs = _make_l_shape_segments(primary_w=1.65, branch_w=1.20)
    new_segs, _ = propagate_junction_widths(segs, config=cfg, grid=grid)
    branch = new_segs[1]
    assert branch.constant_width_m == 1.20  # middle unchanged
    assert branch.start_width_m == 1.65  # junction-end widened
    assert branch.end_width_m == 1.20  # far end unchanged


def test_junction_local_branch_taper_truncated_at_short_length():
    """Per § 4.3.1: 5m segment with bay=3.3m → taper truncated to 2.5m."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig()
    segs = _make_l_shape_segments(primary_w=1.65, branch_w=1.20)
    new_segs, trace = propagate_junction_widths(segs, config=cfg, grid=grid)
    branch = new_segs[1]
    assert branch.taper_zone_m == 2.5
    assert any("truncated" in t for t in trace)


def test_junction_local_branch_middle_meets_inv20():
    """Constant middle ≥ length / 2."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig()
    segs = _make_l_shape_segments(primary_w=1.65, branch_w=1.20)
    new_segs, _ = propagate_junction_widths(segs, config=cfg, grid=grid)
    branch = new_segs[1]
    assert branch.constant_middle_length_m >= branch.length_m / 2.0


def test_junction_local_equal_widths_no_inflation():
    """When both segments have same width, neither widens."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig()
    segs = _make_l_shape_segments(primary_w=1.20, branch_w=1.20)
    new_segs, _ = propagate_junction_widths(segs, config=cfg, grid=grid)
    for seg in new_segs:
        assert seg.start_width_m == 1.20
        assert seg.end_width_m == 1.20
        assert seg.constant_width_m == 1.20


# ─── Junction propagation: GLOBAL_MAX_INHERITANCE ──────


def test_global_max_inflates_branch_entirely():
    """Per § 14.20 (deprecated v0.3): BRANCH inflates entirely to junction-max."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig(width_propagation=WidthPropagation.GLOBAL_MAX_INHERITANCE)
    segs = _make_l_shape_segments(primary_w=1.65, branch_w=1.20)
    new_segs, trace = propagate_junction_widths(segs, config=cfg, grid=grid)
    branch = new_segs[1]
    assert branch.constant_width_m == 1.65  # FULLY inflated
    assert branch.start_width_m == 1.65
    assert branch.end_width_m == 1.65
    assert branch.taper_zone_m == 0.0  # no taper in global-max mode
    assert any("global_max" in t for t in trace)


# ─── Junction propagation: INDEPENDENT_WIDTHS ──────


def test_independent_widths_no_propagation():
    """Per § 14.20: no propagation; mismatch logged."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig(width_propagation=WidthPropagation.INDEPENDENT_WIDTHS)
    segs = _make_l_shape_segments(primary_w=1.65, branch_w=1.20)
    new_segs, trace = propagate_junction_widths(segs, config=cfg, grid=grid)
    primary, branch = new_segs
    assert primary.constant_width_m == 1.65
    assert branch.constant_width_m == 1.20
    # Step discontinuity logged
    assert any("step" in t for t in trace)


def test_independent_widths_no_log_when_equal():
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.3)
    cfg = CorridorDesignConfig(width_propagation=WidthPropagation.INDEPENDENT_WIDTHS)
    segs = _make_l_shape_segments(primary_w=1.20, branch_w=1.20)
    _, trace = propagate_junction_widths(segs, config=cfg, grid=grid)
    assert all("step" not in t for t in trace)


# ─── No junction → no change ──────────────────────────


def test_no_junctions_returns_unchanged():
    """Single segment, no JUNCTION endpoints → no propagation."""
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.0)
    cfg = CorridorDesignConfig()
    seg = make_segment(width_m=1.2)
    new_segs, trace = propagate_junction_widths([seg], config=cfg, grid=grid)
    assert new_segs[0] is seg or (
        new_segs[0].constant_width_m == seg.constant_width_m
        and new_segs[0].start_width_m == seg.start_width_m
        and new_segs[0].end_width_m == seg.end_width_m
    )


def test_empty_segments_returns_empty():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.0)
    cfg = CorridorDesignConfig()
    new_segs, trace = propagate_junction_widths([], config=cfg, grid=grid)
    assert new_segs == []
    assert trace == []


# ─── Multi-junction (T-style) ─────────────────────


def test_three_segments_at_one_junction():
    """3-way junction: all segments meet at one point; junction_max wins."""
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.0)
    cfg = CorridorDesignConfig()
    # Three segments: E-running, W-running, N-running, all meeting at (5,5)
    e_seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(10.0, 5.0)),
        constant_width_m=1.5, start_width_m=1.5, end_width_m=1.5,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.EAST,
    )
    w_seg = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH,
        start=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0)),
        constant_width_m=1.0, start_width_m=1.0, end_width_m=1.0,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.EAST,
    )
    n_seg = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(5.0, 10.0)),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.NORTH,
    )
    new_segs, _ = propagate_junction_widths([e_seg, w_seg, n_seg], config=cfg, grid=grid)
    # All three should have junction-max (1.5) at the junction end
    for seg in new_segs:
        if seg.end.point_m == (5.0, 5.0):
            assert seg.end_width_m == 1.5
        if seg.start.point_m == (5.0, 5.0):
            assert seg.start_width_m == 1.5
