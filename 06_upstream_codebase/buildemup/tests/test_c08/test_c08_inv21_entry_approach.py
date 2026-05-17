"""
Tests for B-NEW-L (S38): C8 entry approach compatibility — Inv 21.

Verifies ``validate_entry_approach()`` per the predicate contract:

  - Cardinal facings (N/S/E/W) require the ENTRY endpoint on one
    specific envelope edge.
  - Intercardinal facings (NE/NW/SE/SW) accept either of the two
    adjacent edges.
  - Vacuous-pass cases: has_corridor=False, paths with no ENTRY endpoints.
  - Tolerance respects DEFAULT_EPSILON_M.

Per C8 SPEC v0.6 LOCKED + B-NEW-L v0.1 PROPOSED.
"""
from __future__ import annotations

import pytest

from buildemup.components.c05.schema import ConnectivityType, ZoneBand
from buildemup.components.c08.schema import (
    DEFAULT_EPSILON_M,
    ConsumptionBand,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorPath,
    CorridorSegment,
    CorridorSegmentKind,
    GridAlignmentReport,
    WidthQuantization,
)
from buildemup.components.c08.validator import validate_entry_approach
from buildemup.domain.envelope import PlotOrientation


# Test envelope dimensions
W = 10.0
D = 12.0


def _make_segment(
    start_pt: tuple[float, float],
    end_pt: tuple[float, float],
    *,
    start_kind: CorridorEndpointKind = CorridorEndpointKind.ENTRY,
    end_kind: CorridorEndpointKind = CorridorEndpointKind.BAND_ATTACHMENT,
    runs_along: PlotOrientation = PlotOrientation.EAST,
) -> CorridorSegment:
    length_m = (
        (end_pt[0] - start_pt[0]) ** 2 + (end_pt[1] - start_pt[1]) ** 2
    ) ** 0.5
    return CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=CorridorEndpoint(kind=start_kind, point_m=start_pt),
        end=CorridorEndpoint(kind=end_kind, point_m=end_pt),
        constant_width_m=1.2, start_width_m=1.2, end_width_m=1.2,
        taper_zone_m=0.0, length_m=length_m,
        runs_along=runs_along,
    )


def _make_path(*segments: CorridorSegment, has_corridor: bool = True) -> CorridorPath:
    total_len = sum(s.length_m for s in segments) if segments else 0.0
    return CorridorPath(
        has_corridor=has_corridor,
        segments=tuple(segments),
        envelopes=(),
        total_length_m=total_len,
        total_area_m2=0.0,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=ConnectivityType.LINEAR,
        grid_alignment=GridAlignmentReport(
            quantization_used=WidthQuantization.GRID_FRACTIONS,
            edges_aligned_count=0, edges_total_count=0,
            tapered_edges_count=0, grid_alignment_score=1.0,
        ),
    )


# =============================================================================
# Cardinal — happy paths
# =============================================================================


def test_inv21_north_entry_on_north_edge_passes() -> None:
    """NORTH-facing plot: ENTRY at y=envelope_depth passes."""
    seg = _make_segment(start_pt=(5.0, D), end_pt=(5.0, 6.0),
                        runs_along=PlotOrientation.NORTH)
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.NORTH)
    assert ok is True
    assert reason is None


def test_inv21_south_entry_on_south_edge_passes() -> None:
    """SOUTH-facing plot: ENTRY at y=0 passes."""
    seg = _make_segment(start_pt=(5.0, 0.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.SOUTH)
    assert ok is True
    assert reason is None


def test_inv21_east_entry_on_east_edge_passes() -> None:
    """EAST-facing plot: ENTRY at x=envelope_width passes."""
    seg = _make_segment(start_pt=(W, 6.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.EAST)
    assert ok is True
    assert reason is None


def test_inv21_west_entry_on_west_edge_passes() -> None:
    """WEST-facing plot: ENTRY at x=0 passes."""
    seg = _make_segment(start_pt=(0.0, 6.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.WEST)
    assert ok is True
    assert reason is None


# =============================================================================
# Cardinal — wrong-edge failures
# =============================================================================


def test_inv21_north_entry_on_south_edge_fails() -> None:
    """NORTH-facing plot but ENTRY is on south edge → fail."""
    seg = _make_segment(start_pt=(5.0, 0.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.NORTH)
    assert ok is False
    assert reason is not None
    assert "Inv 21" in reason
    assert "north" in reason.lower()


def test_inv21_east_entry_on_west_edge_fails() -> None:
    """EAST-facing plot but ENTRY is on west edge → fail."""
    seg = _make_segment(start_pt=(0.0, 6.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.EAST)
    assert ok is False
    assert reason is not None
    assert "Inv 21" in reason


def test_inv21_south_entry_on_north_edge_fails() -> None:
    seg = _make_segment(start_pt=(5.0, D), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.SOUTH)
    assert ok is False
    assert "Inv 21" in (reason or "")


def test_inv21_west_entry_on_east_edge_fails() -> None:
    seg = _make_segment(start_pt=(W, 6.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.WEST)
    assert ok is False
    assert "Inv 21" in (reason or "")


# =============================================================================
# Intercardinal — accept either of two adjacent edges
# =============================================================================


def test_inv21_ne_accepts_north_edge() -> None:
    """NE-facing plot: ENTRY on north edge passes."""
    seg = _make_segment(start_pt=(5.0, D), end_pt=(5.0, 6.0),
                        runs_along=PlotOrientation.NORTH)
    path = _make_path(seg)
    ok, _ = validate_entry_approach(path, W, D, PlotOrientation.NORTHEAST)
    assert ok is True


def test_inv21_ne_accepts_east_edge() -> None:
    """NE-facing plot: ENTRY on east edge also passes."""
    seg = _make_segment(start_pt=(W, 6.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, _ = validate_entry_approach(path, W, D, PlotOrientation.NORTHEAST)
    assert ok is True


def test_inv21_ne_rejects_south_edge() -> None:
    """NE-facing plot: ENTRY on south edge fails (not adjacent to NE)."""
    seg = _make_segment(start_pt=(5.0, 0.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.NORTHEAST)
    assert ok is False
    assert reason is not None and "Inv 21" in reason


def test_inv21_sw_accepts_south_edge() -> None:
    seg = _make_segment(start_pt=(5.0, 0.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, _ = validate_entry_approach(path, W, D, PlotOrientation.SOUTHWEST)
    assert ok is True


def test_inv21_sw_accepts_west_edge() -> None:
    seg = _make_segment(start_pt=(0.0, 6.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    ok, _ = validate_entry_approach(path, W, D, PlotOrientation.SOUTHWEST)
    assert ok is True


def test_inv21_sw_rejects_north_edge() -> None:
    seg = _make_segment(start_pt=(5.0, D), end_pt=(5.0, 6.0),
                        runs_along=PlotOrientation.NORTH)
    path = _make_path(seg)
    ok, _ = validate_entry_approach(path, W, D, PlotOrientation.SOUTHWEST)
    assert ok is False


# =============================================================================
# Vacuous-pass cases
# =============================================================================


def test_inv21_no_corridor_passes() -> None:
    """has_corridor=False → vacuous pass regardless of facing."""
    path = _make_path(has_corridor=False)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.NORTH)
    assert ok is True
    assert reason is None


def test_inv21_no_entry_endpoints_passes() -> None:
    """Path with corridor but no ENTRY endpoints → vacuous pass.

    Some topologies legitimately use BAND_ATTACHMENT-only endpoints
    (Inv 9 enforces ENTRY presence for topologies that need it; Inv 21
    intentionally does not double-cover).
    """
    seg = _make_segment(
        start_pt=(2.0, 6.0), end_pt=(8.0, 6.0),
        start_kind=CorridorEndpointKind.BAND_ATTACHMENT,
        end_kind=CorridorEndpointKind.BAND_ATTACHMENT,
    )
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.NORTH)
    assert ok is True
    assert reason is None


# =============================================================================
# Multi-ENTRY + tolerance edge cases
# =============================================================================


def test_inv21_multiple_entry_endpoints_all_must_pass() -> None:
    """Path with two ENTRY endpoints — both must lie on a valid edge."""
    seg1 = _make_segment(
        start_pt=(0.0, 6.0), end_pt=(5.0, 6.0),
        start_kind=CorridorEndpointKind.ENTRY,
        end_kind=CorridorEndpointKind.JUNCTION,
    )
    # Second segment with a second ENTRY endpoint elsewhere on west edge
    seg2 = _make_segment(
        start_pt=(0.0, 8.0), end_pt=(5.0, 8.0),
        start_kind=CorridorEndpointKind.ENTRY,
        end_kind=CorridorEndpointKind.JUNCTION,
    )
    path = _make_path(seg1, seg2)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.WEST)
    assert ok is True, f"both should pass: reason={reason}"


def test_inv21_multi_entry_one_invalid_fails() -> None:
    """Path with two ENTRY endpoints — one off-edge → fail (any-fails)."""
    seg1 = _make_segment(
        start_pt=(0.0, 6.0), end_pt=(5.0, 6.0),
        start_kind=CorridorEndpointKind.ENTRY,
        end_kind=CorridorEndpointKind.JUNCTION,
    )
    seg2 = _make_segment(
        start_pt=(3.0, 8.0),  # not on any edge
        end_pt=(5.0, 8.0),
        start_kind=CorridorEndpointKind.ENTRY,
        end_kind=CorridorEndpointKind.JUNCTION,
    )
    path = _make_path(seg1, seg2)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.WEST)
    assert ok is False
    assert reason is not None and "Inv 21" in reason


def test_inv21_endpoint_within_tolerance_passes() -> None:
    """Endpoint just within DEFAULT_EPSILON_M of the edge passes."""
    seg = _make_segment(
        start_pt=(0.0 + DEFAULT_EPSILON_M / 2.0, 6.0),
        end_pt=(5.0, 6.0),
    )
    path = _make_path(seg)
    ok, _ = validate_entry_approach(path, W, D, PlotOrientation.WEST)
    assert ok is True


def test_inv21_endpoint_outside_tolerance_fails() -> None:
    """Endpoint just outside DEFAULT_EPSILON_M of the edge fails."""
    # 0.01m off the west edge — well beyond the 0.001m default epsilon.
    seg = _make_segment(
        start_pt=(0.01, 6.0),
        end_pt=(5.0, 6.0),
    )
    path = _make_path(seg)
    ok, reason = validate_entry_approach(path, W, D, PlotOrientation.WEST)
    assert ok is False
    assert reason is not None and "Inv 21" in reason


def test_inv21_predicate_is_pure() -> None:
    """Predicate does not mutate inputs — calling it twice yields the
    same result."""
    seg = _make_segment(start_pt=(5.0, 0.0), end_pt=(5.0, 6.0))
    path = _make_path(seg)
    r1 = validate_entry_approach(path, W, D, PlotOrientation.SOUTH)
    r2 = validate_entry_approach(path, W, D, PlotOrientation.SOUTH)
    assert r1 == r2
    # The CorridorPath is frozen so we just confirm it's still usable.
    assert path.has_corridor is True
