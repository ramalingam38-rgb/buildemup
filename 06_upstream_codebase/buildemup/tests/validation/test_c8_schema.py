"""Validation tests for C8 schema dataclasses + invariants.

Per C8 SPEC v0.5 LOCKED § 3 (Output schema) + dataclass __post_init__ checks.
"""
from __future__ import annotations

import pytest

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c08.schema import (
    ALLOWED_JUNCTION_ANGLES_DEG,
    DEFAULT_BAND_PRIORITY_ORDER,
    DEFAULT_EPSILON_M,
    DEFAULT_UNDER_COMFORT_PENALTY_RATIO,
    GRID_FRACTION_CANDIDATES,
    ConsumptionBand,
    CorridorDesignConfig,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
    GridAlignmentReport,
    WidthPropagation,
    WidthQuantization,
    ZoneBandEnvelope,
)
from buildemup.domain.envelope import PlotOrientation


# ─── Constants ──────────────────────────────────────────────────────────


def test_grid_fraction_candidates_count():
    """Per § 14.2: 5 fractions {1/4, 1/3, 1/2, 2/3, 3/4}."""
    assert len(GRID_FRACTION_CANDIDATES) == 5


def test_grid_fraction_candidates_values():
    expected = {0.25, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.75}
    actual = set(GRID_FRACTION_CANDIDATES)
    # Compare via sorted lists for FP tolerance
    assert sorted(actual) == pytest.approx(sorted(expected), abs=1e-9)


def test_allowed_junction_angles():
    """Per § 4.6 invariant 13: only cardinal angles allowed."""
    assert ALLOWED_JUNCTION_ANGLES_DEG == frozenset({0.0, 90.0, 180.0, 270.0})


def test_default_band_priority_order_excludes_circulation():
    """Per § 14.7: CIRCULATION has no envelope; not in priority order."""
    assert ZoneBand.CIRCULATION not in DEFAULT_BAND_PRIORITY_ORDER


def test_default_band_priority_order_has_three_bands():
    assert len(DEFAULT_BAND_PRIORITY_ORDER) == 3
    assert set(DEFAULT_BAND_PRIORITY_ORDER) == {
        ZoneBand.PUBLIC, ZoneBand.PRIVATE, ZoneBand.SERVICE,
    }


def test_default_epsilon_is_sub_construction_tolerance():
    """1mm; sub-construction-tolerance per § 3."""
    assert DEFAULT_EPSILON_M == 0.001


def test_under_comfort_penalty_default_is_2():
    """Per § 14.19."""
    assert DEFAULT_UNDER_COMFORT_PENALTY_RATIO == 2.0


# ─── ZoneBandEnvelope ──────────────────────────────────────────────────


def test_zone_band_envelope_basic():
    env = ZoneBandEnvelope(
        band=ZoneBand.PUBLIC, direction=PlotOrientation.NORTH,
        x_min_m=0.0, y_min_m=8.0, x_max_m=10.0, y_max_m=10.0,
    )
    assert env.width_m == 10.0
    assert env.depth_m == 2.0
    assert env.centroid_m == (5.0, 9.0)


def test_zone_band_envelope_rejects_inverted_x():
    with pytest.raises(ValueError, match="x_min_m"):
        ZoneBandEnvelope(
            band=ZoneBand.PUBLIC, direction=PlotOrientation.NORTH,
            x_min_m=10.0, y_min_m=0.0, x_max_m=5.0, y_max_m=10.0,
        )


def test_zone_band_envelope_rejects_inverted_y():
    with pytest.raises(ValueError, match="y_min_m"):
        ZoneBandEnvelope(
            band=ZoneBand.PUBLIC, direction=PlotOrientation.NORTH,
            x_min_m=0.0, y_min_m=10.0, x_max_m=10.0, y_max_m=5.0,
        )


def test_zone_band_envelope_rejects_non_zoneband():
    with pytest.raises(TypeError, match="band"):
        ZoneBandEnvelope(
            band="public",  # type: ignore[arg-type]
            direction=PlotOrientation.NORTH,
            x_min_m=0.0, y_min_m=8.0, x_max_m=10.0, y_max_m=10.0,
        )


def test_zone_band_envelope_rejects_non_orientation():
    with pytest.raises(TypeError, match="direction"):
        ZoneBandEnvelope(
            band=ZoneBand.PUBLIC,
            direction="N",  # type: ignore[arg-type]
            x_min_m=0.0, y_min_m=8.0, x_max_m=10.0, y_max_m=10.0,
        )


# ─── CorridorEndpoint ──────────────────────────────────────────────────


def test_corridor_endpoint_basic():
    ep = CorridorEndpoint(
        kind=CorridorEndpointKind.ENTRY, point_m=(5.0, 0.0),
    )
    assert ep.kind == CorridorEndpointKind.ENTRY
    assert ep.point_m == (5.0, 0.0)


def test_corridor_endpoint_rejects_non_tuple():
    with pytest.raises(TypeError, match="point_m"):
        CorridorEndpoint(
            kind=CorridorEndpointKind.ENTRY,
            point_m=[5.0, 0.0],  # type: ignore[arg-type]
        )


def test_corridor_endpoint_rejects_3d_point():
    with pytest.raises(TypeError, match="point_m"):
        CorridorEndpoint(
            kind=CorridorEndpointKind.ENTRY,
            point_m=(5.0, 0.0, 0.0),  # type: ignore[arg-type]
        )


# ─── CorridorSegment ──────────────────────────────────────────────────


def test_corridor_segment_basic_uniform_width():
    s = CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(10.0, 5.0))
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY, start=s, end=e,
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=10.0, runs_along=PlotOrientation.EAST,
    )
    assert seg.length_m == 10.0
    assert seg.has_taper is False
    assert seg.constant_middle_length_m == 10.0


def test_corridor_segment_tapered_at_one_end():
    s = CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.0, 5.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(10.0, 5.0))
    seg = CorridorSegment(
        kind=CorridorSegmentKind.BRANCH, start=s, end=e,
        constant_width_m=1.2, start_width_m=1.5, end_width_m=1.2,
        taper_zone_m=2.5, length_m=10.0, runs_along=PlotOrientation.EAST,
    )
    assert seg.has_taper is True
    # Only start has taper, so middle = 10 - 2.5 = 7.5
    assert seg.constant_middle_length_m == 7.5


def test_corridor_segment_rejects_non_axis_aligned():
    s = CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 0.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(10.0, 5.0))
    with pytest.raises(ValueError, match="axis-aligned"):
        CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY, start=s, end=e,
            constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
            taper_zone_m=0.0, length_m=11.18, runs_along=PlotOrientation.EAST,
        )


def test_corridor_segment_rejects_zero_length():
    s = CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(5.0, 5.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(5.0, 5.0))
    with pytest.raises(ValueError, match="non-zero length"):
        CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY, start=s, end=e,
            constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
            taper_zone_m=0.0, length_m=0.001, runs_along=PlotOrientation.EAST,
        )


def test_corridor_segment_rejects_negative_width():
    s = CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(10.0, 5.0))
    with pytest.raises(ValueError, match="constant_width_m"):
        CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY, start=s, end=e,
            constant_width_m=-0.5, start_width_m=1.2, end_width_m=1.2,
            taper_zone_m=0.0, length_m=10.0, runs_along=PlotOrientation.EAST,
        )


def test_corridor_segment_rejects_inv16_taper_too_long():
    """Inv 16: taper_zone_m ≤ length_m / 2."""
    s = CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.0, 5.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(4.0, 5.0))
    with pytest.raises(ValueError, match="Invariant 16"):
        CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY, start=s, end=e,
            constant_width_m=1.2, start_width_m=1.5, end_width_m=1.5,
            taper_zone_m=2.5, length_m=4.0, runs_along=PlotOrientation.EAST,
        )


def test_corridor_segment_rejects_inv20_middle_too_short():
    """Inv 20: constant_middle_length ≥ length_m / 2."""
    s = CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(0.0, 5.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.JUNCTION, point_m=(10.0, 5.0))
    # Both ends have taper; middle = 10 - 2*2.6 = 4.8 < 5.0
    with pytest.raises(ValueError, match="Invariant 20"):
        CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY, start=s, end=e,
            constant_width_m=1.2, start_width_m=1.5, end_width_m=1.5,
            taper_zone_m=2.6, length_m=10.0, runs_along=PlotOrientation.EAST,
        )


def test_corridor_segment_length_must_match_geometry():
    s = CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(10.0, 5.0))
    with pytest.raises(ValueError, match="length_m"):
        CorridorSegment(
            kind=CorridorSegmentKind.PRIMARY, start=s, end=e,
            constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
            taper_zone_m=0.0, length_m=5.0,  # wrong length
            runs_along=PlotOrientation.EAST,
        )


def test_corridor_segment_immutable():
    """Frozen dataclass."""
    s = CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0))
    e = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(10.0, 5.0))
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY, start=s, end=e,
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=10.0, runs_along=PlotOrientation.EAST,
    )
    with pytest.raises(Exception):
        seg.constant_width_m = 1.5  # type: ignore[misc]


# ─── CorridorDesignConfig ──────────────────────────────────────────────


def test_config_defaults():
    cfg = CorridorDesignConfig()
    assert cfg.regulatory_min_width_m == 0.9
    assert cfg.comfort_target_width_m == 1.2
    assert cfg.width_quantization == WidthQuantization.GRID_FRACTIONS
    assert cfg.width_propagation == WidthPropagation.JUNCTION_LOCAL_ONLY
    assert cfg.under_comfort_penalty_ratio == 2.0


def test_config_rejects_comfort_below_regulatory():
    with pytest.raises(ValueError, match="comfort_target_width_m"):
        CorridorDesignConfig(
            regulatory_min_width_m=1.5,
            comfort_target_width_m=0.9,
        )


def test_config_rejects_negative_regulatory():
    with pytest.raises(ValueError, match="regulatory_min_width_m"):
        CorridorDesignConfig(regulatory_min_width_m=-0.5)


def test_config_rejects_invalid_consumption_thresholds():
    with pytest.raises(ValueError, match="consumption_band_thresholds"):
        CorridorDesignConfig(consumption_band_thresholds=(0.30, 0.20))


def test_config_effective_band_priority_default():
    cfg = CorridorDesignConfig()
    assert cfg.effective_band_priority_order() == DEFAULT_BAND_PRIORITY_ORDER


def test_config_effective_band_priority_override():
    custom = (ZoneBand.SERVICE, ZoneBand.PRIVATE, ZoneBand.PUBLIC)
    cfg = CorridorDesignConfig(band_priority_order=custom)
    assert cfg.effective_band_priority_order() == custom


# ─── GridAlignmentReport ──────────────────────────────────────────────


def test_grid_alignment_report_basic():
    r = GridAlignmentReport(
        quantization_used=WidthQuantization.GRID_FRACTIONS,
        edges_aligned_count=4,
        edges_total_count=4,
        tapered_edges_count=0,
        grid_alignment_score=1.0,
        chosen_width_fraction=0.5,
        chosen_bay_axis="x",
    )
    assert r.grid_alignment_score == 1.0


def test_grid_alignment_score_must_be_in_unit_interval():
    with pytest.raises(ValueError, match="grid_alignment_score"):
        GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=4, edges_total_count=4, tapered_edges_count=0,
            grid_alignment_score=1.5,
        )


def test_grid_alignment_axis_validation():
    with pytest.raises(ValueError, match="chosen_bay_axis"):
        GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=4, edges_total_count=4, tapered_edges_count=0,
            grid_alignment_score=1.0,
            chosen_bay_axis="z",
        )
