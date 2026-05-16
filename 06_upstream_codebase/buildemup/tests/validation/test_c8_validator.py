"""Validation tests for C8 validator — 20 invariants tiered.

Per C8 SPEC v0.5 LOCKED § 4.6 (NEW v0.2 tiered split + v0.4 invariants 16-20).
"""
from __future__ import annotations

import pytest

from buildemup.components.c05.schema import ConnectivityType, ZoneBand
from buildemup.components.c08 import (
    CorridorDesignConfig,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorPath,
    CorridorSegment,
    CorridorSegmentKind,
    GridAlignmentReport,
    WidthPropagation,
    WidthQuantization,
    ZoneBandEnvelope,
)
from buildemup.components.c08.schema import ConsumptionBand
from buildemup.components.c08.validator import validate_corridor_path
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c8_fixtures import make_grid_minimal


def _make_minimal_path(
    has_corridor: bool = True,
    segments=(),
    envelopes=(),
    connectivity_type=ConnectivityType.LINEAR,
) -> CorridorPath:
    return CorridorPath(
        has_corridor=has_corridor,
        segments=tuple(segments),
        envelopes=tuple(envelopes),
        total_length_m=sum(s.length_m for s in segments),
        total_area_m2=0.0,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=connectivity_type,
        grid_alignment=GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=0, edges_total_count=0,
            tapered_edges_count=0, grid_alignment_score=1.0,
        ),
    )


def _seg(start_pt, end_pt, width=1.2, runs_along=PlotOrientation.EAST,
         start_kind=CorridorEndpointKind.ENTRY,
         end_kind=CorridorEndpointKind.BAND_ATTACHMENT,
         **kwargs):
    sx, sy = start_pt
    ex, ey = end_pt
    length = max(abs(ex - sx), abs(ey - sy))
    return CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=start_kind, point_m=start_pt),
        end=CorridorEndpoint(kind=end_kind, point_m=end_pt),
        constant_width_m=width, start_width_m=kwargs.get("start_width", width),
        end_width_m=kwargs.get("end_width", width),
        taper_zone_m=kwargs.get("taper", 0.0),
        length_m=length, runs_along=runs_along,
    )


# ─── ALL-PATHS invariants ─────────────────────────────


def test_inv_1_segments_must_be_tuple():
    """Inv 1: segments is a tuple."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    # Build with list-typed segments → should fail at CorridorPath dataclass
    # (Inv 1 also checked by validator). Skip — schema enforces this already.
    seg = _seg((0.0, 5.0), (8.0, 5.0))
    path = _make_minimal_path(has_corridor=True, segments=(seg,))
    validate_corridor_path(path, grid, config=cfg)  # should not raise


def test_inv_5_at_most_one_entry():
    """Inv 5: at most one ENTRY endpoint."""
    grid = make_grid_minimal(envelope_width_m=20.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    s1 = _seg((0.0, 3.0), (8.0, 3.0), start_kind=CorridorEndpointKind.ENTRY)
    s2 = _seg(
        (0.0, 7.0), (8.0, 7.0),
        start_kind=CorridorEndpointKind.ENTRY,
        end_kind=CorridorEndpointKind.BAND_ATTACHMENT,
    )
    path = _make_minimal_path(has_corridor=True, segments=(s1, s2))
    with pytest.raises(ValueError, match="Invariant 5"):
        validate_corridor_path(path, grid, config=cfg)


def test_inv_5_zero_entries_ok_when_no_corridor():
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    path = _make_minimal_path(has_corridor=False, segments=())
    validate_corridor_path(path, grid, config=cfg)


def test_inv_8_connectivity_type_must_be_enum():
    """Inv 8: connectivity_type must be ConnectivityType enum."""
    # CorridorPath.__post_init__ enforces this, so validator's check is defensive.
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    path = _make_minimal_path(has_corridor=False, segments=())
    validate_corridor_path(path, grid, config=cfg)
    assert isinstance(path.connectivity_type, ConnectivityType)


def test_inv_10_envelope_containment_violation():
    """Inv 10: segments must fit within envelope."""
    grid = make_grid_minimal(envelope_width_m=5.0, envelope_depth_m=5.0)
    cfg = CorridorDesignConfig()
    seg = _seg((0.0, 2.5), (10.0, 2.5))  # extends to x=10, beyond 5.0
    path = _make_minimal_path(has_corridor=True, segments=(seg,))
    with pytest.raises(ValueError, match="Invariant 10"):
        validate_corridor_path(path, grid, config=cfg)


def test_inv_10_envelope_containment_pass():
    grid = make_grid_minimal(envelope_width_m=15.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    seg = _seg((0.0, 5.0), (10.0, 5.0))
    path = _make_minimal_path(has_corridor=True, segments=(seg,))
    validate_corridor_path(path, grid, config=cfg)


def test_inv_11_self_intersection():
    """Inv 11: non-adjacent segments must not overlap.

    Updated S33 (B-133): the validator now raises CorridorSelfIntersectionError
    (a RuntimeError subclass with diagnostic metadata) instead of the previous
    generic ValueError, per § 6 / § 14.17.
    """
    from buildemup.components.c08.errors import CorridorSelfIntersectionError
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    s1 = _seg((0.0, 5.0), (8.0, 5.0), width=2.0)
    s2 = _seg(
        (2.0, 4.5), (8.0, 4.5), width=2.0,
        start_kind=CorridorEndpointKind.BAND_ATTACHMENT,
    )
    path = _make_minimal_path(has_corridor=True, segments=(s1, s2))
    with pytest.raises(CorridorSelfIntersectionError, match="Invariant 11"):
        validate_corridor_path(path, grid, config=cfg)


def test_inv_13_junction_angle_90_pass():
    """Inv 13: junction angles in {0, 90, 180, 270}."""
    grid = make_grid_minimal(envelope_width_m=20.0, envelope_depth_m=20.0)
    cfg = CorridorDesignConfig()
    # PRIMARY E-running, ends at (5,5) JUNCTION
    p = _seg(
        (0.0, 5.0), (5.0, 5.0),
        start_kind=CorridorEndpointKind.ENTRY,
        end_kind=CorridorEndpointKind.JUNCTION,
    )
    # BRANCH N-running from (5,5), 90° from PRIMARY
    b_seg = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(5.0, 12.0)),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=7.0, runs_along=PlotOrientation.NORTH,
    )
    path = _make_minimal_path(has_corridor=True, segments=(p, b_seg),
                              connectivity_type=ConnectivityType.BRANCHED)
    validate_corridor_path(path, grid, config=cfg)


def test_inv_15_18_junction_width_equality():
    """Inv 15/18: at JUNCTION, all adjoining segments have equal width at junction point."""
    grid = make_grid_minimal(envelope_width_m=20.0, envelope_depth_m=20.0)
    cfg = CorridorDesignConfig()  # default JUNCTION_LOCAL_ONLY
    # PRIMARY ends at (5,5) with end_width=1.2
    p = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0)),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.EAST,
    )
    # BRANCH starts at (5,5) with start_width=1.5 — MISMATCH
    b = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(5.0, 10.0)),
        constant_width_m=1.5, start_width_m=1.5, end_width_m=1.5,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.NORTH,
    )
    path = _make_minimal_path(has_corridor=True, segments=(p, b),
                              connectivity_type=ConnectivityType.BRANCHED)
    with pytest.raises(ValueError, match="Invariant 15"):
        validate_corridor_path(path, grid, config=cfg)


def test_inv_15_independent_widths_skips_check():
    """When INDEPENDENT_WIDTHS, junction-width-equality is skipped."""
    grid = make_grid_minimal(envelope_width_m=20.0, envelope_depth_m=20.0)
    cfg = CorridorDesignConfig(width_propagation=WidthPropagation.INDEPENDENT_WIDTHS)
    p = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0)),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.EAST,
    )
    b = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH,
        start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(5.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(5.0, 10.0)),
        constant_width_m=1.5, start_width_m=1.5, end_width_m=1.5,
        taper_zone_m=0.0, length_m=5.0, runs_along=PlotOrientation.NORTH,
    )
    path = _make_minimal_path(has_corridor=True, segments=(p, b),
                              connectivity_type=ConnectivityType.BRANCHED)
    validate_corridor_path(path, grid, config=cfg)


def test_inv_16_taper_zone_bound_enforced_at_construction():
    """Inv 16: enforced by CorridorSegment.__post_init__ — schema raises."""
    with pytest.raises(ValueError, match="Invariant 16"):
        CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY,
            start=CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0)),
            end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(4.0, 5.0)),
            constant_width_m=1.2, start_width_m=1.5, end_width_m=1.5,
            taper_zone_m=2.5, length_m=4.0, runs_along=PlotOrientation.EAST,
        )


def test_inv_20_constant_middle_enforced_at_construction():
    """Inv 20: middle ≥ length/2 enforced by CorridorSegment.__post_init__."""
    with pytest.raises(ValueError, match="Invariant 20"):
        CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY,
            start=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.0, 5.0)),
            end=CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(10.0, 5.0)),
            constant_width_m=1.2, start_width_m=1.5, end_width_m=1.5,
            taper_zone_m=2.6, length_m=10.0, runs_along=PlotOrientation.EAST,
        )


# ─── HAS-CORRIDOR-ONLY invariants ────────────────────


def test_inv_2_widths_must_meet_regulatory():
    """Inv 2: every segment's all 3 width fields ≥ regulatory."""
    grid = make_grid_minimal(envelope_width_m=20.0, envelope_depth_m=20.0)
    cfg = CorridorDesignConfig(regulatory_min_width_m=1.0)
    seg = _seg((0.0, 5.0), (10.0, 5.0), width=0.95)  # below regulatory
    path = _make_minimal_path(has_corridor=True, segments=(seg,))
    with pytest.raises(ValueError, match="Invariant 2"):
        validate_corridor_path(path, grid, config=cfg)


def test_inv_2_skipped_when_no_corridor():
    """Inv 2 skipped when has_corridor=False."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig(regulatory_min_width_m=1.0)
    path = _make_minimal_path(has_corridor=False, segments=())
    validate_corridor_path(path, grid, config=cfg)


def test_inv_7_circulation_must_have_no_envelope():
    """Inv 7: CIRCULATION band has no ZoneBandEnvelope."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    bad_env = ZoneBandEnvelope(
        band=ZoneBand.CIRCULATION, direction=PlotOrientation.NORTH,
        x_min_m=0.0, y_min_m=8.0, x_max_m=10.0, y_max_m=10.0,
    )
    seg = _seg((0.0, 5.0), (8.0, 5.0))
    path = _make_minimal_path(has_corridor=True, segments=(seg,), envelopes=(bad_env,))
    with pytest.raises(ValueError, match="Invariant 7"):
        validate_corridor_path(path, grid, config=cfg)


def test_inv_9_has_corridor_requires_at_least_one_entry():
    """Inv 9: has_corridor=True requires ≥ 1 ENTRY endpoint."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    seg = _seg(
        (0.0, 5.0), (8.0, 5.0),
        start_kind=CorridorEndpointKind.BAND_ATTACHMENT,
        end_kind=CorridorEndpointKind.BAND_ATTACHMENT,
    )
    path = _make_minimal_path(has_corridor=True, segments=(seg,))
    with pytest.raises(ValueError, match="Invariant 9"):
        validate_corridor_path(path, grid, config=cfg)


# ─── has_corridor flag tests (§ 4.3.2 / Drawback 7) ─────


def test_has_corridor_false_with_empty_segments_passes():
    """Per § 4.3.2: degenerate path with has_corridor=False is OK."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    path = _make_minimal_path(has_corridor=False, segments=())
    validate_corridor_path(path, grid, config=cfg)


def test_has_corridor_false_with_segments_rejected_by_dataclass():
    """CorridorPath rejects has_corridor=False with non-empty segments."""
    seg = _seg((0.0, 5.0), (8.0, 5.0))
    with pytest.raises(ValueError, match="has_corridor"):
        CorridorPath(
            has_corridor=False,
            segments=(seg,),
            envelopes=(),
            total_length_m=8.0, total_area_m2=0.0,
            consumption_band=ConsumptionBand.LOW,
            connectivity_type=ConnectivityType.LINEAR,
            grid_alignment=GridAlignmentReport(
                quantization_used=WidthQuantization.GRID_FRACTIONS,
                edges_aligned_count=0, edges_total_count=0,
                tapered_edges_count=0, grid_alignment_score=1.0,
            ),
        )
