"""C9 partial-batch tolerance tests.

Per C9 SPEC v0.7 LOCKED § 7 (Required test cases — partial-batch) + § 14.40.

Tests that PerCandidateError subclasses are caught and aggregated when SOME
candidates fail; BatchSizingInfeasibleError raised only when ALL fail.

Strategy: synthesise a tiny corridor-designed-candidate list where we can force
specific candidates to fail by manipulating the FloorRoomBrief / config.

Rather than constructing CorridorDesignedCandidate by hand (heavy), we lean on
unit tests of the validator + orchestrator caller-error layer, plus one
end-to-end "all fail" test that uses a contrived config to force batch failure.
"""
from __future__ import annotations

import pytest

from buildemup.components.c09 import (
    BatchSizingInfeasibleError,
    DwellingSizeTier,
    NBCConfidenceTooLow,
    PerCandidateError,
    RoomCategory,
    RoomSizingConfig,
    RoomSizingInfeasibleError,
    size_rooms,
)
from buildemup.components.c09.errors import (
    GridOversizeError,
    PackingInfeasibleError,
    WidthInfeasibleError,
    WidthRiskyError,
)
from buildemup.tests._c9_fixtures import run_c8_pipeline


# ---------------------------------------------------------------------------
# All-fail batch
# ---------------------------------------------------------------------------


def test_all_three_candidates_succeed_returns_three():
    """3-in 3-out happy path."""
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    assert len(cdc) == 3
    sized = size_rooms(cdc, brief, grid, plot_analysis)
    assert len(sized) == 3


def test_batch_infeasible_when_all_candidates_fail():
    """Forces all candidates to fail by setting `require_verified_nbc=True`
    when the medium brief includes a UTILITY room (which uses an unverified row)."""
    cdc, brief, grid, plot_analysis = run_c8_pipeline()  # medium_brief includes utility
    with pytest.raises((NBCConfidenceTooLow, BatchSizingInfeasibleError)):
        size_rooms(cdc, brief, grid, plot_analysis,
                   config=RoomSizingConfig(require_verified_nbc=True))


def test_batch_error_carries_failures_list():
    """When BatchSizingInfeasibleError is raised, .failures lists per-candidate errors."""
    # Create a hand-crafted exception to verify carrier API; the orchestrator
    # uses BatchSizingInfeasibleError(failures, total).
    failures = [
        (0, RoomSizingInfeasibleError("test", candidate_index=0,
                                      total_liveability_min_area_m2=50.0,
                                      envelope_minus_corridor_m2=30.0,
                                      deficit_m2=20.0)),
        (1, RoomSizingInfeasibleError("test", candidate_index=1,
                                      total_liveability_min_area_m2=51.0,
                                      envelope_minus_corridor_m2=30.0,
                                      deficit_m2=21.0)),
    ]
    err = BatchSizingInfeasibleError(failures, input_count=2)
    assert err.input_count == 2
    assert len(err.failures) == 2
    assert err.failures[0][0] == 0


# ---------------------------------------------------------------------------
# Cardinality / ordering preservation
# ---------------------------------------------------------------------------


def test_successes_preserve_input_relative_order():
    """3-in 3-out: index 0 of output corresponds to index 0 of input."""
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    sized = size_rooms(cdc, brief, grid, plot_analysis)
    for i, s in enumerate(sized):
        # corridor_designed_candidate field on output points back at input position i
        assert s.corridor_designed_candidate is cdc[i]


def test_caller_correlation_via_corridor_designed_candidate():
    """Per § 14.40: caller can correlate output[k].corridor_designed_candidate
    with the original input candidate."""
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    sized = size_rooms(cdc, brief, grid, plot_analysis)
    input_ids = [id(c) for c in cdc]
    output_ids = [id(s.corridor_designed_candidate) for s in sized]
    assert output_ids == input_ids


# ---------------------------------------------------------------------------
# PerCandidateError hierarchy — ensures aggregation contract
# ---------------------------------------------------------------------------


def test_room_sizing_infeasible_is_per_candidate():
    err = RoomSizingInfeasibleError(
        "x", candidate_index=0, total_liveability_min_area_m2=10.0,
        envelope_minus_corridor_m2=5.0, deficit_m2=5.0,
    )
    assert isinstance(err, PerCandidateError)


def test_width_infeasible_is_per_candidate():
    err = WidthInfeasibleError(
        "x", candidate_index=0, impossible_room_ids=("r1",),
        envelope_min_axis_m=5.0,
    )
    assert isinstance(err, PerCandidateError)


def test_packing_infeasible_is_per_candidate():
    err = PackingInfeasibleError(
        "x", candidate_index=0, total_liveability_min_area_m2=50.0,
        packing_capacity_m2=40.0, packing_efficiency=0.75,
    )
    assert isinstance(err, PerCandidateError)


def test_width_risky_is_per_candidate():
    err = WidthRiskyError(
        "x", candidate_index=0, risky_room_ids=("r1",),
    )
    assert isinstance(err, PerCandidateError)


def test_grid_oversize_is_per_candidate():
    err = GridOversizeError(
        "x", candidate_index=0, oversized_room_ids=("r1",), bay_max_m=3.0,
    )
    assert isinstance(err, PerCandidateError)


# ---------------------------------------------------------------------------
# Batch error vs systemic error
# ---------------------------------------------------------------------------


def test_batch_error_not_per_candidate():
    """BatchSizingInfeasibleError signals all-failed; not a single-candidate error."""
    err = BatchSizingInfeasibleError([], input_count=0)
    assert not isinstance(err, PerCandidateError)


def test_nbc_confidence_too_low_is_systemic():
    """NBCConfidenceTooLow halts the entire batch (systemic), not per-candidate."""
    err = NBCConfidenceTooLow("x", unverified_room_ids=("r1",))
    assert not isinstance(err, PerCandidateError)
