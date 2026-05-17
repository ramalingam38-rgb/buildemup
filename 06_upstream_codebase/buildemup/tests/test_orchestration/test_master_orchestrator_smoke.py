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


def test_c15_through_c17_phases_marked_stub(smoke_inputs):
    """C15-C17 should produce STUB status with explicit stub_reason
    and a notes line pointing at the follow-ups doc.

    C12 + C13 + C14 flipped to OK in S57 (follow-ups #4/#5/#6).
    """
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    stub_phases = [
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


def test_c12_phase_flips_to_ok_via_fallback_adapter(smoke_inputs):
    """C12 phase ships OK via the C11a→C12 fallback adapter (S57 #4).

    C11b ships STUB (no real EvaluatorProtocol yet — #3 deferred), so
    the orchestrator uses the MutatedTopologyCandidate adapter path.
    The phase is OK because the call to C12's place_and_align returned
    a PlacementBatchResult; per-candidate placement failures inside
    the batch are not phase-level failures.
    """
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c12 = result.phase("c12_vertical_placement")
    assert c12 is not None
    assert c12.status == PhaseStatus.OK, (
        f"C12 phase expected OK; got {c12.status} "
        f"({c12.error_class}: {c12.error_message})"
    )
    assert c12.payload is not None
    # Adapter path note must explain which path ran.
    note_text = " ".join(c12.notes)
    assert "Adapter path" in note_text
    # While C11b is STUB the fallback is the active path.
    assert "fallback" in note_text or "RefinedCandidate" in note_text


def test_c13_phase_flips_to_ok_via_place_doors(smoke_inputs):
    """C13 phase ships OK by piping C12's PlacedCandidates through
    place_doors (S57 #5). Per-candidate door-placement failures (the
    documented sparse-edge problem from C13's adversarial corpus) are
    captured inside the DoorPlacementBatchResult and don't fail the
    phase — that's working-as-designed."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c13 = result.phase("c13_doors")
    assert c13 is not None
    assert c13.status == PhaseStatus.OK, (
        f"C13 phase expected OK; got {c13.status} "
        f"({c13.error_class}: {c13.error_message})"
    )
    assert c13.payload is not None
    # The payload is a DoorPlacementBatchResult with successful + failed
    # tuples. Either may be empty depending on C12's edge density —
    # that's not a phase-level concern.
    assert hasattr(c13.payload, "successful")
    assert hasattr(c13.payload, "failed")


def test_c14_phase_flips_to_ok_via_circulation_batch(smoke_inputs):
    """C14 phase ships OK by analyzing C13's door placements with
    metadata built from C12 placed rooms (S57 #6).

    The metadata builder produces empty dict if there are no
    successful door placements upstream (the sparse-edge case); C14
    then returns an empty CirculationAnalysisBatchResult — still OK
    at the phase level because the call succeeded.
    """
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c14 = result.phase("c14_connection_graph")
    assert c14 is not None
    assert c14.status == PhaseStatus.OK, (
        f"C14 phase expected OK; got {c14.status} "
        f"({c14.error_class}: {c14.error_message})"
    )
    assert c14.payload is not None
    assert hasattr(c14.payload, "successful")
    assert hasattr(c14.payload, "failed")


def test_c7_full_engine_payload_carries_structure_and_cost(smoke_inputs):
    """C7 phase ships OK with the full StructuralGridEngine payload
    (grid + structure + foundation + cost) — S57 follow-up #1.

    Default config has enable_full_structural_engine=True at S57 close;
    payload is StructuralGridOutput with all four sub-outputs populated.
    """
    plot, brief_for_c4, floor_brief = smoke_inputs
    orch = MasterOrchestrator()  # defaults — full engine on
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c07 = result.phase("c07_structural_grid")
    assert c07 is not None
    assert c07.status == PhaseStatus.OK
    payload = c07.payload
    # Full-engine path has nested sub-outputs.
    assert hasattr(payload, "grid")
    assert hasattr(payload, "structure")
    assert hasattr(payload, "foundation")
    assert hasattr(payload, "cost")
    # Structure has sizing fields.
    assert payload.structure.column_size_mm > 0
    assert payload.structure.beam_depth_mm > 0
    assert payload.structure.total_concrete_cum > 0
    # Foundation has a type + design.
    assert payload.foundation.type
    assert payload.foundation.total_concrete_cum >= 0
    # Cost carries a TransparencyTriple.
    assert payload.cost.exact_value > 0


def test_c7_mvp_compat_path_returns_grid_directly(smoke_inputs):
    """Setting enable_full_structural_engine=False reverts C7 to the
    S56-MVP GridGenerator-only path; payload is the Grid object."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    config = MasterOrchestratorConfig(enable_full_structural_engine=False)
    orch = MasterOrchestrator(config)
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c07 = result.phase("c07_structural_grid")
    assert c07.status == PhaseStatus.OK
    # MVP-path payload IS the Grid (no .structure attribute).
    assert hasattr(c07.payload, "columns") or hasattr(c07.payload, "max_span_m")
    assert not hasattr(c07.payload, "structure")


def test_c11a_full_operator_suite_produces_more_variants(smoke_inputs):
    """With enable_full_mutation_operators=True, C11a runs M0 + M1-M9.

    The default M0_BASE-only run produces 1 variant per upstream
    wet-zoned candidate. Enabling the full suite should produce
    strictly more variants (M0 + applicable mutations, deduplicated).
    """
    plot, brief_for_c4, floor_brief = smoke_inputs

    default_orch = MasterOrchestrator()
    default_result = default_orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    default_c11a = default_result.phase("c11a_topology_mutation")
    default_variants = len(default_c11a.payload)

    full_config = MasterOrchestratorConfig(enable_full_mutation_operators=True)
    full_orch = MasterOrchestrator(full_config)
    full_result = full_orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    full_c11a = full_result.phase("c11a_topology_mutation")
    assert full_c11a.status == PhaseStatus.OK
    full_variants = len(full_c11a.payload)

    # Full operator suite must produce ≥ default. We don't pin an exact
    # count because some operators may be rejected for the smoke
    # fixture's geometry (M3*/M9* depend on staircase + entry positions
    # that may not apply).
    assert full_variants >= default_variants, (
        f"Full operator suite produced fewer variants ({full_variants}) "
        f"than M0_BASE-only ({default_variants}); operators must be "
        f"additive."
    )
    # The notes line should say which mode ran.
    notes_text = " ".join(full_c11a.notes)
    assert "full M0-M9" in notes_text


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
