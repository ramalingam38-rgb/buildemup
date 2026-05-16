"""Validation tests for C8 spatial feasibility checks.

Per C8 SPEC v0.5 LOCKED § 4.7 — Reviewer Drawback 5 (envelope containment,
self-intersection, junction-only-overlap).
"""
from __future__ import annotations

import pytest

from buildemup.components.c08 import (
    CorridorDesignConfig,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
    design_corridors,
)
from buildemup.components.c08.validator import validate_corridor_path, _seg_bbox, _bboxes_overlap
from buildemup.components.c08.schema import (
    ConsumptionBand,
    CorridorPath,
    GridAlignmentReport,
    WidthQuantization,
)
from buildemup.components.c05.schema import ConnectivityType
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c8_fixtures import (
    make_grid_minimal,
    make_segment,
    real_pipeline,
)


# ─── Envelope containment ──────────────────────────────────


def test_envelope_containment_real_pipeline():
    """Per Inv 10: every segment within envelope."""
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        for seg in d.corridor_path.segments:
            x0, y0, x1, y1 = _seg_bbox(seg)
            assert x0 >= -1e-3
            assert y0 >= -1e-3
            assert x1 <= grid.envelope_width_m + 1e-3
            assert y1 <= grid.envelope_depth_m + 1e-3


def test_envelope_containment_violation_caught_by_validator():
    """Constructing a path with an out-of-envelope segment fails validator."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    # Segment extends from (5, 5) to (15, 5) — overshoots envelope
    bad_seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(5.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(15.0, 5.0)),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=10.0, runs_along=PlotOrientation.EAST,
    )
    path = CorridorPath(
        has_corridor=True,
        segments=(bad_seg,),
        envelopes=(),
        total_length_m=10.0,
        total_area_m2=12.0,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=ConnectivityType.LINEAR,
        grid_alignment=GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=2, edges_total_count=2,
            tapered_edges_count=0, grid_alignment_score=1.0,
        ),
    )
    cfg = CorridorDesignConfig()
    with pytest.raises(ValueError, match="Invariant 10"):
        validate_corridor_path(path, grid, config=cfg)


# ─── Self-intersection ────────────────────────────────


def test_no_self_intersection_real_pipeline():
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        # Validator was already called inside design_corridors — passing means OK
        assert d.corridor_path is not None


def test_overlapping_non_adjacent_segments_caught_by_validator():
    """Two parallel segments that overlap → Inv 11 violation."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    s1 = make_segment(width_m=2.0, start_pt=(0.0, 5.0), end_pt=(8.0, 5.0))
    # s2 overlaps s1's bbox but doesn't share any endpoint
    s2 = make_segment(
        width_m=2.0, start_pt=(2.0, 4.5), end_pt=(8.0, 4.5),
        start_kind=CorridorEndpointKind.BAND_ATTACHMENT,
    )
    path = CorridorPath(
        has_corridor=True,
        segments=(s1, s2),
        envelopes=(),
        total_length_m=16.0, total_area_m2=20.0,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=ConnectivityType.LINEAR,
        grid_alignment=GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=4, edges_total_count=4,
            tapered_edges_count=0, grid_alignment_score=1.0,
        ),
    )
    cfg = CorridorDesignConfig()
    # Updated S33 (B-133): typed exception per § 14.17.
    from buildemup.components.c08.errors import CorridorSelfIntersectionError
    with pytest.raises(CorridorSelfIntersectionError, match="Invariant 11"):
        validate_corridor_path(path, grid, config=cfg)


# ─── Junction-only overlap ───────────────────────────


def test_l_shape_junction_overlap_allowed():
    """Adjacent (sharing endpoint) segments may overlap at junction. Per Inv 12."""
    from buildemup.components.c05.schema import TopologyKind
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    found_l = False
    for d in designed:
        if d.oriented_candidate.topology_candidate.kind == TopologyKind.L_SHAPE:
            found_l = True
            assert d.corridor_path is not None
    assert found_l


# ─── Bbox overlap helper ───────────────────────────


def test_bbox_overlap_overlapping():
    a = (0.0, 0.0, 5.0, 5.0)
    b = (3.0, 3.0, 8.0, 8.0)
    assert _bboxes_overlap(a, b, 1e-3)


def test_bbox_overlap_disjoint():
    a = (0.0, 0.0, 5.0, 5.0)
    b = (6.0, 0.0, 10.0, 5.0)
    assert not _bboxes_overlap(a, b, 1e-3)


def test_bbox_overlap_touching_not_overlap():
    """Touching at a boundary (zero-area overlap) is NOT counted as overlap."""
    a = (0.0, 0.0, 5.0, 5.0)
    b = (5.0, 0.0, 10.0, 5.0)
    assert not _bboxes_overlap(a, b, 1e-3)


# ─── Segment bbox accounts for max width ───────────────


def test_seg_bbox_uses_max_width():
    """Bbox of a tapered segment uses max(start, constant, end) widths."""
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(10.0, 5.0)),
        constant_width_m=1.2, start_width_m=1.5, end_width_m=1.2,
        taper_zone_m=2.0, length_m=10.0, runs_along=PlotOrientation.EAST,
    )
    x0, y0, x1, y1 = _seg_bbox(seg)
    # Max width is 1.5; half = 0.75; bbox y in [5 - 0.75, 5 + 0.75]
    assert y0 == pytest.approx(4.25, abs=1e-6)
    assert y1 == pytest.approx(5.75, abs=1e-6)


# ─── Pipeline full feasibility ─────────────────────


def test_design_corridors_validator_passes_real_pipeline():
    """Pipeline produces valid corridors that pass the validator."""
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    # Validator runs inside design_corridors; if any path were invalid, it
    # would have raised ValueError. Reaching here means all 3 paths passed.
    assert len(designed) == len(oriented)


# ─── Width assignment fits envelope ──────────────


def test_strip_corridor_width_fits_envelope():
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        if not d.corridor_path.has_corridor:
            continue
        for seg in d.corridor_path.segments:
            x0, y0, x1, y1 = _seg_bbox(seg)
            assert (x1 - x0) <= grid.envelope_width_m + 1e-3
            assert (y1 - y0) <= grid.envelope_depth_m + 1e-3
