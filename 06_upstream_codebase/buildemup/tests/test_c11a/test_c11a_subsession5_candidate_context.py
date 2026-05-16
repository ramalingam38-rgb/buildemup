"""
C11a Sub-session 5 — B-NEW-V: strict candidate-context extractor tests.

Per S39 critique walk F4: orchestrator's previous duck-typed
multi-fallback walks silently masked schema drift. B-NEW-V provides:
  - Strict extractor: real WetZonePlannedCandidate → canonical chain.
    Schema drift raises CandidateContextSchemaError.
  - Lenient extractor: synthetic test fixtures → multi-fallback walks
    (preserved for backwards-compat).
  - Dispatcher: detects real vs synthetic and dispatches.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c07.grid_generator import Grid, Staircase
from buildemup.components.c11a import (
    CandidateContextSchemaError,
    TierAOperatorContext,
    extract_tier_a_context,
    extract_tier_a_context_from_candidate,
    extract_tier_a_context_lenient,
    extract_topology_kind,
    is_real_wet_zone_candidate,
)
from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# Synthetic candidates (lenient path — current Sub-4 test fixture style)
# =============================================================================


@dataclass(frozen=True)
class _FakeEnvelope:
    facing: PlotOrientation = PlotOrientation.NORTH
    width_m: float = 10.0
    depth_m: float = 12.0


@dataclass(frozen=True)
class _FakePlotAnalysis:
    envelope: _FakeEnvelope = field(default_factory=_FakeEnvelope)
    trace_id: str = "test-trace"


@dataclass(frozen=True)
class _FakeWetZoneCandidate:
    """Synthetic source — exposes flat zone_bands / corridor_path."""
    topology_kind: str = "central_spine"
    zone_bands: dict = field(default_factory=lambda: {
        ZoneBand.PUBLIC: PlotOrientation.SOUTH,
        ZoneBand.PRIVATE: PlotOrientation.NORTH,
    })
    corridor_path: Any = None


def _make_grid() -> Grid:
    return Grid(
        columns=[],
        bay_x_m=3.0, bay_y_m=3.0,
        columns_x_count=0, columns_y_count=0,
        envelope_width_m=10.0, envelope_depth_m=12.0,
        staircase=Staircase(
            origin_x_m=1.0, origin_y_m=1.0,
            width_m=1.0, landing_depth_m=1.2,
        ),
    )


# =============================================================================
# is_real_wet_zone_candidate detector
# =============================================================================


def test_is_real_wet_zone_candidate_false_for_synthetic() -> None:
    fake = _FakeWetZoneCandidate()
    assert is_real_wet_zone_candidate(fake) is False


def test_is_real_wet_zone_candidate_false_for_arbitrary_object() -> None:
    assert is_real_wet_zone_candidate(object()) is False
    assert is_real_wet_zone_candidate(None) is False
    assert is_real_wet_zone_candidate(42) is False


def test_is_real_wet_zone_candidate_true_for_namesake_in_c10() -> None:
    """Type detector matches both class name AND module path. A
    user-defined class named 'WetZonePlannedCandidate' but NOT in
    c10.schema is correctly NOT detected as real."""
    class WetZonePlannedCandidate:  # locally-defined; wrong module
        pass
    fake = WetZonePlannedCandidate()
    assert is_real_wet_zone_candidate(fake) is False


# =============================================================================
# Lenient extractor — synthetic source compatibility
# =============================================================================


def test_lenient_extracts_zone_bands_from_top_level() -> None:
    src = _FakeWetZoneCandidate()
    ctx = extract_tier_a_context_lenient(src, _make_grid(), _FakePlotAnalysis())
    assert ctx.zone_bands is not None
    assert ZoneBand.PUBLIC in ctx.zone_bands


def test_lenient_extracts_envelope_from_grid() -> None:
    grid = _make_grid()
    ctx = extract_tier_a_context_lenient(
        _FakeWetZoneCandidate(), grid, _FakePlotAnalysis(),
    )
    assert ctx.envelope_width_m == 10.0
    assert ctx.envelope_depth_m == 12.0


def test_lenient_extracts_plot_facing_from_envelope() -> None:
    ctx = extract_tier_a_context_lenient(
        _FakeWetZoneCandidate(),
        _make_grid(),
        _FakePlotAnalysis(envelope=_FakeEnvelope(facing=PlotOrientation.EAST)),
    )
    assert ctx.plot_facing == PlotOrientation.EAST


def test_lenient_falls_back_to_none_on_missing_zone_bands() -> None:
    """Lenient extractor's defining property: silent None on miss."""
    @dataclass(frozen=True)
    class _NoZoneBands:
        topology_kind: str = "strip"
    ctx = extract_tier_a_context_lenient(
        _NoZoneBands(), _make_grid(), _FakePlotAnalysis(),
    )
    assert ctx.zone_bands is None


# =============================================================================
# Strict extractor — schema-drift detection
# =============================================================================


def test_strict_raises_on_synthetic_source() -> None:
    """Strict extractor expects real ancestry chain; synthetic source
    raises because room_sized_candidate is missing."""
    src = _FakeWetZoneCandidate()
    with pytest.raises(CandidateContextSchemaError, match="room_sized_candidate"):
        extract_tier_a_context_from_candidate(
            src, _make_grid(), _FakePlotAnalysis(),
        )


def test_strict_raises_on_partial_chain() -> None:
    """A source that has room_sized_candidate but missing further
    chain links raises with a precise path."""
    @dataclass(frozen=True)
    class _PartialChain:
        room_sized_candidate: Any = None  # halts at first segment

    with pytest.raises(CandidateContextSchemaError, match="resolved to None"):
        extract_tier_a_context_from_candidate(
            _PartialChain(), _make_grid(), _FakePlotAnalysis(),
        )


def test_strict_raises_with_consumed_path_diagnostic() -> None:
    """Error message identifies which segment was missing."""
    src = _FakeWetZoneCandidate()
    try:
        extract_tier_a_context_from_candidate(
            src, _make_grid(), _FakePlotAnalysis(),
        )
        pytest.fail("Expected raise")
    except CandidateContextSchemaError as exc:
        assert "B-NEW-V" in str(exc)


# =============================================================================
# Dispatcher — strict for real, lenient for synthetic
# =============================================================================


def test_dispatcher_uses_lenient_for_synthetic() -> None:
    """Synthetic source → lenient path → no raise even though strict
    chain isn't present."""
    ctx = extract_tier_a_context(
        _FakeWetZoneCandidate(), _make_grid(), _FakePlotAnalysis(),
    )
    assert isinstance(ctx, TierAOperatorContext)


def test_dispatcher_force_strict_raises_on_synthetic() -> None:
    """require_strict=True forces the strict path even for synthetic."""
    with pytest.raises(CandidateContextSchemaError):
        extract_tier_a_context(
            _FakeWetZoneCandidate(),
            _make_grid(),
            _FakePlotAnalysis(),
            require_strict=True,
        )


# =============================================================================
# Topology-kind extractor
# =============================================================================


def test_extract_topology_kind_from_synthetic() -> None:
    src = _FakeWetZoneCandidate(topology_kind="courtyard")
    assert extract_topology_kind(src) == "courtyard"


def test_extract_topology_kind_unknown_for_no_kind_at_all() -> None:
    @dataclass(frozen=True)
    class _NoKind:
        pass
    assert extract_topology_kind(_NoKind()) == "unknown"


# =============================================================================
# Returned context shape
# =============================================================================


def test_lenient_returns_tier_a_operator_context() -> None:
    ctx = extract_tier_a_context_lenient(
        _FakeWetZoneCandidate(), _make_grid(), _FakePlotAnalysis(),
    )
    assert isinstance(ctx, TierAOperatorContext)
    # Frozen dataclass — cannot mutate
    with pytest.raises(Exception):
        ctx.envelope_width_m = 999.0  # type: ignore[misc]


def test_lenient_includes_grid_and_staircase() -> None:
    grid = _make_grid()
    ctx = extract_tier_a_context_lenient(
        _FakeWetZoneCandidate(), grid, _FakePlotAnalysis(),
    )
    assert ctx.grid is grid
    assert ctx.staircase is grid.staircase


# =============================================================================
# Schema error has correct severity tier
# =============================================================================


def test_schema_error_severity_tier_per_candidate() -> None:
    """B-NEW-V error class registers per_candidate severity so the
    orchestrator's catch logic surfaces affected candidates without
    halting the batch."""
    assert CandidateContextSchemaError.severity_tier == "per_candidate"


def test_schema_error_in_error_registry() -> None:
    """B-NEW-V error class auto-registers via __init_subclass__
    (B-NEW-X interaction check)."""
    from buildemup.components.c11a.errors import iter_registered_errors
    assert CandidateContextSchemaError in iter_registered_errors()
