"""Validation tests for C8 area accounting.

Per C8 SPEC v0.5 LOCKED § 4.8 / § 14.14 / § 14.20.
"""
from __future__ import annotations

import pytest

from buildemup.components.c08 import (
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
)
from buildemup.components.c08.area_accounting import (
    decompose_segment,
    polygon_union_area_m2,
    segment_additive_area_m2,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c8_fixtures import make_segment


# ─── Single-segment additive area ──────────────────────────────


def test_uniform_segment_area_2m_x_1_2m():
    """2m × 1.2m uniform → 2.4 m²."""
    seg = make_segment(width_m=1.2, start_pt=(0.0, 5.0), end_pt=(2.0, 5.0))
    assert segment_additive_area_m2(seg) == pytest.approx(2.4, abs=1e-6)


def test_tapered_segment_area_spec_419_worked_example():
    """Per spec § 4.8 worked example: 1m taper 1.0 → 1.5 = 1.25 m²."""
    # Build a 2m segment with a 1m start-taper from 1.0 → 1.5 and constant 1.5 middle
    # length=2, taper_zone=1, start_width=1.0, constant=1.5, end_width=1.5
    # Region 1 (taper): 1m × (1.0+1.5)/2 = 1.25 m² (matches spec example exactly)
    # Region 2 (middle): 1m × 1.5 = 1.5 m²
    # Total: 2.75 m²
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(2.0, 5.0)),
        constant_width_m=1.5, start_width_m=1.0, end_width_m=1.5,
        taper_zone_m=1.0, length_m=2.0, runs_along=PlotOrientation.EAST,
    )
    total = segment_additive_area_m2(seg)
    assert total == pytest.approx(1.25 + 1.5, abs=1e-6)


def test_tapered_segment_decomposition_count():
    """One end tapered (1.0→1.5), one constant: 3 primitives (rect+2tris+rect)."""
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(2.0, 5.0)),
        constant_width_m=1.5, start_width_m=1.0, end_width_m=1.5,
        taper_zone_m=1.0, length_m=2.0, runs_along=PlotOrientation.EAST,
    )
    primitives = decompose_segment(seg)
    # Region 1 (taper-start): 1 inner rect + 2 right-triangles = 3
    # Region 2 (middle): 1 rect
    # Region 3 (no taper-end): 0
    assert len(primitives) == 4


def test_uniform_segment_decomposition_count():
    """No taper: 1 primitive (just middle rect)."""
    seg = make_segment(width_m=1.2, start_pt=(0.0, 5.0), end_pt=(10.0, 5.0))
    primitives = decompose_segment(seg)
    assert len(primitives) == 1


# ─── Multi-segment union area: spec verification cases ────────


def test_l_shape_v0_3_union_7m2():
    """Spec § 4.8 v0.3 case: two perpendicular 4m × 1m segments → 7.0 m²."""
    h = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 0.5)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(4.0, 0.5)),
        constant_width_m=1.0, start_width_m=1.0, end_width_m=1.0,
        taper_zone_m=0.0, length_m=4.0, runs_along=PlotOrientation.EAST,
    )
    v = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.5, 0.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(0.5, 4.0)),
        constant_width_m=1.0, start_width_m=1.0, end_width_m=1.0,
        taper_zone_m=0.0, length_m=4.0, runs_along=PlotOrientation.NORTH,
    )
    union = polygon_union_area_m2([h, v], cell_m=0.01)
    assert union == pytest.approx(7.0, abs=0.05)


def test_strip_single_segment_area_equals_additive():
    """One segment: union == additive (no overlap to subtract)."""
    seg = make_segment(width_m=1.2, start_pt=(0.0, 5.0), end_pt=(10.0, 5.0))
    union = polygon_union_area_m2([seg], cell_m=0.01)
    additive = segment_additive_area_m2(seg)
    assert union == pytest.approx(additive, abs=0.05)


def test_two_disjoint_segments_union_equals_sum():
    """Disjoint segments: union = sum."""
    s1 = make_segment(width_m=1.0, start_pt=(0.0, 1.0), end_pt=(5.0, 1.0))
    s2 = make_segment(width_m=1.0, start_pt=(0.0, 8.0), end_pt=(5.0, 8.0))
    union = polygon_union_area_m2([s1, s2], cell_m=0.01)
    add = segment_additive_area_m2(s1) + segment_additive_area_m2(s2)
    assert union == pytest.approx(add, abs=0.05)


def test_empty_segments_union_zero():
    union = polygon_union_area_m2([], cell_m=0.01)
    assert union == 0.0


# ─── Bounding box and primitives ────────────────────────


def test_north_segment_decomposition_axes():
    """N-running segment decomposes correctly (axis transposed)."""
    seg = make_segment(
        runs_along=PlotOrientation.NORTH,
        start_pt=(5.0, 0.0), end_pt=(5.0, 10.0),
        width_m=1.2,
    )
    primitives = decompose_segment(seg)
    assert len(primitives) == 1
    # The single rect should span x = [5 - 0.6, 5 + 0.6], y = [0, 10]
    p = primitives[0]
    assert p.x_min == pytest.approx(4.4, abs=1e-6)
    assert p.x_max == pytest.approx(5.6, abs=1e-6)
    assert p.y_min == pytest.approx(0.0, abs=1e-6)
    assert p.y_max == pytest.approx(10.0, abs=1e-6)


def test_segment_with_two_end_tapers():
    """Both ends taper: 5 primitives (3 from start-zone + 1 middle rect... wait
    the structure is 3 + 1 + 3 = 7 primitives when both sides taper)."""
    # length=12, taper=2, start=1.0, constant=1.5, end=1.0
    # Region 1: 3 primitives (taper-start)
    # Region 2: 1 rect (middle, length 8)
    # Region 3: 3 primitives (taper-end)
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(12.0, 5.0)),
        constant_width_m=1.5, start_width_m=1.0, end_width_m=1.0,
        taper_zone_m=2.0, length_m=12.0, runs_along=PlotOrientation.EAST,
    )
    primitives = decompose_segment(seg)
    assert len(primitives) == 7
