"""Validation tests for C8 has_corridor flag (§ 4.3.2 / Drawback 7).

Per C8 SPEC v0.5 LOCKED § 3 (NEW v0.2: has_corridor flag) + § 4.3.2.
Tests the validator-tier split (ALL-PATHS vs HAS-CORRIDOR-ONLY).
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
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorPath,
    CorridorSegment,
    CorridorSegmentKind,
    GridAlignmentReport,
    WidthQuantization,
    design_corridors,
)
from buildemup.components.c08.schema import ConsumptionBand
from buildemup.components.c08.validator import validate_corridor_path
from buildemup.tests.validation._c8_fixtures import (
    make_grid_minimal,
    real_pipeline,
)


# ─── has_corridor=False produced for STRIP+NONE ──────────


def test_strip_with_position_none_produces_has_corridor_false():
    """STRIP topology with CorridorPosition.NONE → has_corridor=False."""
    oriented, pa, grid = real_pipeline()
    # Find the STRIP candidate; force position=NONE
    target = None
    for oc in oriented:
        if oc.topology_candidate.kind == TopologyKind.STRIP:
            target = oc
            break
    if target is None:
        pytest.skip("no STRIP")

    new_sketch = replace(
        target.topology_candidate.corridor_sketch,
        position=CorridorPosition.NONE,
    )
    new_cand = replace(target.topology_candidate, corridor_sketch=new_sketch)
    new_oc = replace(target, topology_candidate=new_cand)

    designed = design_corridors((new_oc,), grid, pa)
    assert len(designed) == 1
    assert designed[0].corridor_path.has_corridor is False
    assert designed[0].corridor_path.segments == ()


def test_strip_with_position_none_has_total_length_zero():
    oriented, pa, grid = real_pipeline()
    target = None
    for oc in oriented:
        if oc.topology_candidate.kind == TopologyKind.STRIP:
            target = oc
            break
    if target is None:
        pytest.skip()
    new_sketch = replace(
        target.topology_candidate.corridor_sketch,
        position=CorridorPosition.NONE,
    )
    new_cand = replace(target.topology_candidate, corridor_sketch=new_sketch)
    new_oc = replace(target, topology_candidate=new_cand)
    designed = design_corridors((new_oc,), grid, pa)
    assert designed[0].corridor_path.total_length_m == 0.0
    assert designed[0].corridor_path.total_area_m2 == 0.0


def test_has_corridor_true_for_normal_strip():
    """Normal STRIP (CENTRAL position) → has_corridor=True."""
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        if d.oriented_candidate.topology_candidate.kind == TopologyKind.STRIP:
            if (d.oriented_candidate.topology_candidate
                    .corridor_sketch.position != CorridorPosition.NONE):
                assert d.corridor_path.has_corridor is True


def test_has_corridor_true_for_l_shape():
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        if d.oriented_candidate.topology_candidate.kind == TopologyKind.L_SHAPE:
            assert d.corridor_path.has_corridor is True


# ─── Validator tier split: HAS-CORRIDOR-ONLY skipped when False ────


def test_validator_inv_2_skipped_for_has_corridor_false():
    """Inv 2 (regulatory min) is HAS-CORRIDOR-ONLY; skipped when False."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig(regulatory_min_width_m=1.0)
    path = CorridorPath(
        has_corridor=False,
        segments=(),
        envelopes=(),
        total_length_m=0.0,
        total_area_m2=0.0,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=ConnectivityType.LINEAR,
        grid_alignment=GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=0, edges_total_count=0,
            tapered_edges_count=0, grid_alignment_score=1.0,
        ),
    )
    # No exception: HAS-CORRIDOR-ONLY invariants are skipped
    validate_corridor_path(path, grid, config=cfg)


def test_validator_inv_9_skipped_for_has_corridor_false():
    """Inv 9 (≥ 1 ENTRY) is HAS-CORRIDOR-ONLY; skipped when False."""
    grid = make_grid_minimal(envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    path = CorridorPath(
        has_corridor=False, segments=(), envelopes=(),
        total_length_m=0.0, total_area_m2=0.0,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=ConnectivityType.LINEAR,
        grid_alignment=GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=0, edges_total_count=0,
            tapered_edges_count=0, grid_alignment_score=1.0,
        ),
    )
    validate_corridor_path(path, grid, config=cfg)


# ─── Schema enforcement ──────────────────────────────


def test_has_corridor_false_must_have_empty_segments():
    """CorridorPath rejects has_corridor=False with non-empty segments."""
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(8.0, 5.0)),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=8.0,
        runs_along=__import__("buildemup.domain.envelope", fromlist=["PlotOrientation"]).PlotOrientation.EAST,
    )
    with pytest.raises(ValueError, match="has_corridor"):
        CorridorPath(
            has_corridor=False, segments=(seg,), envelopes=(),
            total_length_m=8.0, total_area_m2=0.0,
            consumption_band=ConsumptionBand.LOW,
            connectivity_type=ConnectivityType.LINEAR,
            grid_alignment=GridAlignmentReport(
                quantization_used=WidthQuantization.GRID_FRACTIONS,
                edges_aligned_count=0, edges_total_count=0,
                tapered_edges_count=0, grid_alignment_score=1.0,
            ),
        )


def test_has_corridor_true_can_have_segments():
    """CorridorPath accepts has_corridor=True with segments."""
    from buildemup.domain.envelope import PlotOrientation
    seg = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=CorridorEndpointKind.ENTRY, point_m=(0.0, 5.0)),
        end=CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=(8.0, 5.0)),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=8.0, runs_along=PlotOrientation.EAST,
    )
    path = CorridorPath(
        has_corridor=True, segments=(seg,), envelopes=(),
        total_length_m=8.0, total_area_m2=9.6,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=ConnectivityType.LINEAR,
        grid_alignment=GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=2, edges_total_count=2,
            tapered_edges_count=0, grid_alignment_score=1.0,
        ),
    )
    assert path.has_corridor is True


# ─── ConsumptionBand classification per § 4.9 ───────


def test_consumption_band_low_under_12_pct():
    """Per § 4.9: fraction < 0.12 → LOW."""
    oriented, pa, grid = real_pipeline()
    designed = design_corridors(oriented, grid, pa)
    for d in designed:
        if (d.corridor_path.has_corridor
                and d.provenance.envelope_area_fraction < 0.12):
            assert d.corridor_path.consumption_band == ConsumptionBand.LOW


def test_consumption_band_high_over_20_pct():
    """Manually verify boundary classification."""
    from buildemup.components.c08.corridor_designer import _classify_consumption_band
    cb = _classify_consumption_band(0.10, (0.12, 0.20))
    assert cb == ConsumptionBand.LOW
    cb = _classify_consumption_band(0.15, (0.12, 0.20))
    assert cb == ConsumptionBand.MEDIUM
    cb = _classify_consumption_band(0.25, (0.12, 0.20))
    assert cb == ConsumptionBand.HIGH


def test_consumption_band_default_thresholds():
    cfg = CorridorDesignConfig()
    assert cfg.consumption_band_thresholds == (0.12, 0.20)
