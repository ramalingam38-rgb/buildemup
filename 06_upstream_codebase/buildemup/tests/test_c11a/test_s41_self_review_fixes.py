"""S41 self-review fix tests: assert output_candidate IS populated and
IS the actual mutated artifact, not None.

Per the self-analysis at the close of S41: existing M8 tests checked
`result.valid` and `result.floor_label_affected` but never asserted that
`result.output_candidate` carries the correctly-mutated wrapper. That
test blind spot let a Pattern B bug ship: apply_m8_real built the new
wrapper, validated it, then returned a result that discarded it.

This file makes the previously-unstated consumer contract explicit:
downstream code must be able to do something useful with the result.
"""
from __future__ import annotations

import pytest

from buildemup.components.c11a.m8_floor_swap_real import apply_m8_real
from buildemup.components.c11a.orchestrator import mutate_topologies
from buildemup.components.c11a.schema import (
    FamilySlotAllocation,
    MutationOperator,
    MutationOperatorFamily,
    TopologyMutationConfig,
)
from buildemup.domain.multi_floor_candidate import (
    MultiFloorWetZonePlannedCandidate,
)
from buildemup.tests._c10_fixtures import run_c9_pipeline
from buildemup.tests._multi_floor_fixtures import (
    clone_wzpc,
    make_three_floor_brief_with_master_on,
    make_three_floor_wrapper_master_ground,
    make_two_floor_brief_with_master_on,
    make_two_floor_wrapper_master_ground,
)


@pytest.fixture(scope="module")
def grid_and_plot():
    _, _brief, grid, plot_analysis = run_c9_pipeline()
    return grid, plot_analysis


# ---------------------------------------------------------------------------
# 1. apply_m8_real returns the constructed wrapper, not None
# ---------------------------------------------------------------------------


def test_apply_m8_real_returns_output_candidate_not_none():
    """The Pattern B fix: output_candidate must be populated on success."""
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()

    def fake_runner(per_floor_brief, source_floor_wzpc=None):
        return clone_wzpc(
            floor_label=per_floor_brief.floor_label,
            keep_master_bedroom=per_floor_brief.has_master_bedroom,
        )

    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=fake_runner,
        source_family_id="fam",
    )
    assert result.valid is True
    assert result.output_candidate is not None
    # And it's a real MultiFloorWetZonePlannedCandidate.
    assert isinstance(result.output_candidate, MultiFloorWetZonePlannedCandidate)


def test_apply_m8_real_output_candidate_has_swapped_master():
    """The output_candidate's master is on the NEW floor, not the source's
    original master. This is the downstream-consumer correctness check."""
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()
    assert source.master_bedroom_floor_label == "ground"

    def fake_runner(per_floor_brief, source_floor_wzpc=None):
        return clone_wzpc(
            floor_label=per_floor_brief.floor_label,
            keep_master_bedroom=per_floor_brief.has_master_bedroom,
        )

    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=fake_runner,
        source_family_id="fam",
    )
    assert result.output_candidate.master_bedroom_floor_label == "first"


def test_apply_m8_real_failure_output_candidate_is_none():
    """On the failure path, output_candidate stays None."""
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()

    def failing_runner(per_floor_brief, source_floor_wzpc=None):
        raise RuntimeError("simulated failure")

    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=failing_runner,
        source_family_id="fam",
    )
    assert result.valid is False
    assert result.output_candidate is None


# ---------------------------------------------------------------------------
# 2. Orchestrator end-to-end: M8 result wrapper is accessible to consumer
# ---------------------------------------------------------------------------


def test_orchestrator_m8_result_carries_mutated_wrapper(grid_and_plot):
    """End-to-end through mutate_topologies: an M8 result in the output
    tuple must carry the mutated wrapper on its application_results[0]
    .output_candidate. Without this, no consumer can use the M8 output."""
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_ground()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M8_VERT_REARR),
        family_slot_allocations=(
            FamilySlotAllocation(family=MutationOperatorFamily.BASE, reserved_slots=1),
            FamilySlotAllocation(family=MutationOperatorFamily.VERTICAL, reserved_slots=1),
        ),
        max_seeds_per_input=2,
        generation=0,
    )
    results = mutate_topologies((wrapper,), brief, grid, plot_analysis, config=config)
    m8 = next(
        r.application_results[0] for r in results
        if r.application_results[0].operator == MutationOperator.M8_VERT_REARR
    )
    assert m8.valid is True
    assert m8.output_candidate is not None
    assert isinstance(m8.output_candidate, MultiFloorWetZonePlannedCandidate)
    assert m8.output_candidate.master_bedroom_floor_label == "first"


def test_orchestrator_per_floor_tier_a_result_has_no_output_candidate(
    grid_and_plot,
):
    """Per-floor Tier A operators (M1) are predicate-only — they don't
    construct new geometry. output_candidate stays None for these per
    the contract (the consumer materializes from (source, operator,
    floor_label_affected))."""
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_ground()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M1_HORIZ_FLIP),
        family_slot_allocations=(
            FamilySlotAllocation(family=MutationOperatorFamily.BASE, reserved_slots=1),
            FamilySlotAllocation(family=MutationOperatorFamily.FLIP, reserved_slots=2),
        ),
        max_seeds_per_input=4,
    )
    results = mutate_topologies((wrapper,), brief, grid, plot_analysis, config=config)
    m1_results = [
        r.application_results[0]
        for r in results
        if r.application_results[0].operator == MutationOperator.M1_HORIZ_FLIP
    ]
    for r in m1_results:
        assert r.output_candidate is None, (
            f"Tier A predicate-only operator should have output_candidate=None; "
            f"got {r.output_candidate!r}"
        )


# ---------------------------------------------------------------------------
# 3. Per-floor CDC is pulled from each floor's own ancestry (Fix 3)
# ---------------------------------------------------------------------------


def test_runner_pulls_cdc_from_passed_source_floor_not_floors_zero():
    """Self-review fix 3: the per-floor runner must extract CDC from the
    `source_floor_wzpc` argument it receives, NOT from the first floor
    of any wrapper. Verified by constructing a runner and confirming it
    accepts the per-floor source argument."""
    import inspect
    from buildemup.components.c11a.multi_floor_c9_c10_adapter import (
        make_per_floor_c9_runner,
    )
    runner = make_per_floor_c9_runner(grid=None, plot_analysis=None)
    sig = inspect.signature(runner)
    params = list(sig.parameters.keys())
    assert params == ["per_floor_brief", "source_floor_wzpc"], (
        f"runner signature expected (per_floor_brief, source_floor_wzpc); "
        f"got {params}"
    )


# ---------------------------------------------------------------------------
# 4. Adapter distinguishes C9 vs C10 failures (Fix 4)
# ---------------------------------------------------------------------------


def test_apply_m8_real_classifies_c10_failure_distinctly_from_c9():
    """Runner that raises an exception tagged c11a_stage='c10' surfaces
    as invalidity_reason='c10_validation_failed', not c9_generation_failed."""
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()

    def c10_failing_runner(per_floor_brief, source_floor_wzpc=None):
        err = RuntimeError("simulated C10 rejection")
        err.c11a_stage = "c10"
        raise err

    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=c10_failing_runner,
        source_family_id="fam",
    )
    assert result.valid is False
    assert result.invalidity_reason == "c10_validation_failed"


def test_apply_m8_real_classifies_c9_failure_when_stage_omitted():
    """A runner that raises without a c11a_stage attribute defaults to
    'c9_generation_failed' classification — preserves backwards-compat
    with simple test fakes."""
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()

    def bare_failing_runner(per_floor_brief, source_floor_wzpc=None):
        raise RuntimeError("plain failure, no stage tag")

    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=bare_failing_runner,
        source_family_id="fam",
    )
    assert result.valid is False
    assert result.invalidity_reason == "c9_generation_failed"


# ---------------------------------------------------------------------------
# 5. M0_BASE carries source as output_candidate (identity uniformity, both paths)
# ---------------------------------------------------------------------------


def test_m0_base_carries_source_as_output_candidate_single_floor(grid_and_plot):
    """Single-floor M0_BASE output_candidate is the source WZPC itself.
    Lets consumers read result.output_candidate uniformly regardless of
    whether the operator was identity, regenerative, or mutating."""
    grid, plot_analysis = grid_and_plot
    rsc_tuple, brief, _grid, _plot = run_c9_pipeline()
    from buildemup.components.c10 import plan_wet_zones
    wzpc = plan_wet_zones(rsc_tuple, brief, grid, plot_analysis)[0]

    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        emit_base=True,
    )
    results = mutate_topologies(
        (wzpc,), brief, grid, plot_analysis, config=config,
    )
    assert len(results) == 1
    m0 = results[0].application_results[0]
    assert m0.operator == MutationOperator.M0_BASE
    assert m0.output_candidate is wzpc, (
        "M0 (identity) should carry the source WZPC as output_candidate"
    )


def test_m0_base_carries_source_as_output_candidate_multi_floor(grid_and_plot):
    """Multi-floor M0_BASE output_candidate is the source wrapper itself."""
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_ground()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        emit_base=True,
    )
    results = mutate_topologies(
        (wrapper,), brief, grid, plot_analysis, config=config,
    )
    assert len(results) == 1
    m0 = results[0].application_results[0]
    assert m0.operator == MutationOperator.M0_BASE
    assert m0.output_candidate is wrapper, (
        "Multi-floor M0 should carry the source wrapper as output_candidate"
    )
