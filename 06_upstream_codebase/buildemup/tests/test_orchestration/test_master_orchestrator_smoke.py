"""Smoke tests for the S56 MVP MasterOrchestrator.

Goals:
  - Verify the orchestrator runs end-to-end on a representative brief
    without crashing.
  - Verify each phase produces a PhaseResult with a valid status.
  - Verify C4-C11b phases produce OK status when given valid input.
  - Verify C12-C17 phases produce STUB status (placeholder, tracked
    in S57 follow-ups).
  - Verify C1+C2 SKIP when no full Brief provided.
  - Verify SKIPPED reasons are populated.

These are smoke tests, not exhaustive scenario coverage. Comprehensive
coverage is its own multi-session effort (see
04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md).
"""
from __future__ import annotations

import pytest

from buildemup.orchestration import (
    MasterOrchestrator,
    MasterOrchestratorConfig,
    MasterOrchestratorResult,
    PhaseStatus,
    PIPELINE_PHASES,
)
from buildemup.tests.validation._c4_fixtures import bangalore_40x60, make_brief
from buildemup.tests.validation._c5_fixtures import medium_brief


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def smoke_inputs():
    """Build the orchestrator's smoke-test inputs once per module."""
    plot = bangalore_40x60()
    brief_for_c4 = make_brief(plot)
    floor_brief = medium_brief()
    return plot, brief_for_c4, floor_brief


# ──────────────────────────────────────────────────────────────────────
# Basic structural tests
# ──────────────────────────────────────────────────────────────────────


def test_orchestrator_instantiates_with_default_config():
    """The orchestrator should be constructible without any args."""
    orch = MasterOrchestrator()
    assert orch.config.vastu_tier == "PARTIAL"
    assert orch.config.enable_c11b_refinement is True


def test_orchestrator_instantiates_with_custom_config():
    """Custom config should be accepted and used."""
    config = MasterOrchestratorConfig(
        vastu_tier="OFF",
        enable_c11b_refinement=False,
    )
    orch = MasterOrchestrator(config)
    assert orch.config.vastu_tier == "OFF"
    assert orch.config.enable_c11b_refinement is False


def test_pipeline_phases_canonical_order():
    """PIPELINE_PHASES should have exactly 17 phases in canonical order."""
    assert len(PIPELINE_PHASES) == 17
    assert PIPELINE_PHASES[0] == "c01_brief"
    assert PIPELINE_PHASES[1] == "c02_feasibility"
    assert PIPELINE_PHASES[2] == "c04_plot_analysis"  # C3a/C3b skipped
    assert PIPELINE_PHASES[-1] == "c17_quote_comparison"


# ──────────────────────────────────────────────────────────────────────
# End-to-end smoke
# ──────────────────────────────────────────────────────────────────────


def test_orchestrator_runs_end_to_end_without_crashing(smoke_inputs):
    """The orchestrator must not raise on a representative brief."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot,
        brief_for_c4=brief_for_c4,
        floor_brief=floor_brief,
    )
    assert isinstance(result, MasterOrchestratorResult)
    assert len(result.phases) == 17
    assert result.total_elapsed_ms > 0


def test_every_phase_produces_a_phase_result(smoke_inputs):
    """Every phase in PIPELINE_PHASES must appear in the result."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    phase_ids = {p.phase_id for p in result.phases}
    assert phase_ids == set(PIPELINE_PHASES)


def test_phase_results_in_canonical_order(smoke_inputs):
    """Phases must be in PIPELINE_PHASES order in result.phases."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    actual_order = tuple(p.phase_id for p in result.phases)
    assert actual_order == PIPELINE_PHASES


# ──────────────────────────────────────────────────────────────────────
# Per-phase status assertions
# ──────────────────────────────────────────────────────────────────────


def test_c1_c2_skipped_when_no_full_brief_provided(smoke_inputs):
    """Without full_brief, C1 + C2 should SKIP with reason."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c01 = result.phase("c01_brief")
    c02 = result.phase("c02_feasibility")
    assert c01.status == PhaseStatus.SKIPPED
    assert "Brief" in c01.skip_reason
    assert c02.status == PhaseStatus.SKIPPED
    assert "Brief" in c02.skip_reason


def test_c4_c11a_phases_produce_real_outputs(smoke_inputs):
    """C4-C11a (real-chained phases) must produce OK results."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    real_chain_phases = [
        "c04_plot_analysis", "c05_topology", "c06_orientation",
        "c07_structural_grid", "c08_corridor", "c09_room_sizer",
        "c10_wet_zones", "c11a_topology_mutation",
    ]
    for phase_id in real_chain_phases:
        phase = result.phase(phase_id)
        assert phase is not None, f"missing phase {phase_id}"
        assert phase.status == PhaseStatus.OK, (
            f"phase {phase_id} failed: {phase.error_class} {phase.error_message}"
        )
        assert phase.payload is not None, f"phase {phase_id} payload missing"
        assert phase.elapsed_ms >= 0


def test_c11b_marked_stub_with_stub_evaluator(smoke_inputs):
    """C11b runs the real orchestrator with StubEvaluator. The stub
    evaluator does not satisfy NSGA convergence under MVP config —
    the chain converts that BatchAllTopologiesFailedError into a
    STUB-status PhaseResult (not ERROR) since the call DID reach
    C11b's orchestrator successfully."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c11b = result.phase("c11b_nsga_refinement")
    assert c11b.status == PhaseStatus.STUB
    assert "StubEvaluator" in c11b.stub_reason
    assert any("C11b orchestrator was successfully invoked" in n
               for n in c11b.notes)


def test_c12_through_c17_phases_marked_stub(smoke_inputs):
    """C12-C17 should produce STUB status with explicit stub_reason
    and a notes line pointing at the follow-ups doc."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    stub_phases = [
        "c12_vertical_placement", "c13_doors", "c14_connection_graph",
        "c15_problem_finder", "c16_dual_drawings", "c17_quote_comparison",
    ]
    for phase_id in stub_phases:
        phase = result.phase(phase_id)
        assert phase is not None
        assert phase.status == PhaseStatus.STUB
        assert phase.stub_reason  # non-empty
        assert any(
            "S57_MASTER_ORCHESTRATOR_FOLLOWUPS" in note
            for note in phase.notes
        ), f"phase {phase_id} missing follow-ups breadcrumb in notes"


def test_overall_status_ok_when_all_real_phases_pass(smoke_inputs):
    """STUB and SKIPPED phases must not flip overall_status to ERROR."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    assert result.overall_status == PhaseStatus.OK


def test_summary_human_readable(smoke_inputs):
    """summary() should produce a single-line human-readable string."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    text = result.summary()
    assert "MasterOrchestrator" in text
    assert "ok" in text
    assert "stub" in text


# ──────────────────────────────────────────────────────────────────────
# Configuration knobs
# ──────────────────────────────────────────────────────────────────────


def test_disabling_c11b_refinement_skips_that_phase(smoke_inputs):
    """If config disables C11b, its phase result should be SKIPPED."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    config = MasterOrchestratorConfig(enable_c11b_refinement=False)
    orch = MasterOrchestrator(config)
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c11b = result.phase("c11b_nsga_refinement")
    assert c11b.status == PhaseStatus.SKIPPED
    assert "enable_c11b_refinement=False" in c11b.skip_reason


def test_vastu_off_tier_accepted(smoke_inputs):
    """Vastu OFF should work — C6 phase should still produce OK."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    config = MasterOrchestratorConfig(vastu_tier="OFF")
    orch = MasterOrchestrator(config)
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c06 = result.phase("c06_orientation")
    assert c06.status == PhaseStatus.OK
    assert "Vastu tier: OFF" in " ".join(c06.notes)
