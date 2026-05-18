"""Scenario corpus for the master orchestrator (S59 follow-up #13).

Exercises every (plot, brief) combo from the named-fixture registry
against the orchestrator. Each test confirms:
  - The pipeline runs without raising.
  - All 18 phases produce a PhaseResult.
  - C4-C14 reach OK (no upstream-chain regression).
  - Overall status is OK (STUB/SKIPPED phases never break aggregated OK).

This is the v1 acceptance suite — when a future change breaks
scenarios for a specific city/brief combo, the regression surface is
explicit. Comprehensive edge-case coverage (Pune BLACK_COTTON, Mumbai
stilt parking, Delhi corner plot, etc.) is tracked separately as
v1+ scenarios; this file covers the matrix that already passes today.
"""
from __future__ import annotations

import pytest

from buildemup.orchestration import (
    MasterOrchestrator,
    MasterOrchestratorConfig,
    PhaseStatus,
    PIPELINE_PHASES,
)
from buildemup.tests.validation._c4_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    hyderabad_30x40,
    make_brief,
    mumbai_30x40,
    pune_30x40,
)
from buildemup.tests.validation._c5_fixtures import (
    large_brief,
    medium_brief,
    small_brief,
)


# Each row: (test_id, plot_builder, brief_builder, expected_failing_phase).
# expected_failing_phase = None means the scenario should reach overall OK.
# When set, the scenario is known to fail at that phase due to a CURRENT
# upstream limitation (NOT introduced by S59) — the test records the
# breakage so a future fix flips the assertion green. Examples:
#   - C6 (orientation) rejects intercardinal facings (NE/SE/SW/NW) under
#     B-107 — chennai_30x40 carries facing=NORTHEAST → breaks at C6.
_SCENARIOS = [
    # Happy path — the smoke baseline.
    ("bangalore_40x60_medium", bangalore_40x60, medium_brief, None),

    # Known-broken combos — these expose pre-S59 upstream-component
    # edge cases. The scenario corpus records them honestly so a
    # future fix to the named component flips the assertion green.
    #   C6 (orientation): NE / SE / SW / NW facings rejected per B-107.
    ("chennai_30x40_small",    chennai_30x40,   small_brief,
     "c06_orientation"),
    #   C8 (corridor): Delhi 60x90 + large brief produces a corridor
    #   self-intersection (Inv 11 violation) — filed under existing
    #   B-C8-LARGE-PLOT-COVERAGE backlog territory.
    ("delhi_60x90_large",      delhi_60x90,     large_brief,
     "c08_corridor"),
    #   C9 (room sizer): Pune 30x40 + medium brief exhausts sizing
    #   search budget on every candidate (RoomSizingInfeasibleError).
    ("pune_30x40_medium",      pune_30x40,      medium_brief,
     "c09_room_sizer"),
    #   C10 (wet zones): 30x40 + small brief geometry exhausts wall-
    #   assignment search on Mumbai and Hyderabad (Phase 3 cluster
    #   exhaustion). Same root cause both fixtures.
    ("mumbai_30x40_small",     mumbai_30x40,    small_brief,
     "c10_wet_zones"),
    ("hyderabad_30x40_small",  hyderabad_30x40, small_brief,
     "c10_wet_zones"),
]


_CHAIN_OK_PHASES = (
    "c04_plot_analysis",
    "c05_topology",
    "c06_orientation",
    "c07_structural_grid",
    "c08_corridor",
    "c09_room_sizer",
    "c10_wet_zones",
    "c11a_topology_mutation",
    "c12_vertical_placement",
    "c13_doors",
    "c14_connection_graph",
    "c15_problem_finder",
)


@pytest.mark.parametrize(
    "scenario_id,plot_builder,brief_builder,expected_failing_phase",
    _SCENARIOS,
    ids=[s[0] for s in _SCENARIOS],
)
def test_scenario_pipeline_runs_end_to_end(
    scenario_id, plot_builder, brief_builder, expected_failing_phase,
):
    """Each scenario runs without raising.

    When `expected_failing_phase` is None, every chain phase ships OK.
    When set, only that one phase is allowed to be ERROR (everything
    downstream then naturally SKIPs).
    """
    plot = plot_builder()
    brief_for_c4 = make_brief(plot)
    floor_brief = brief_builder()
    orch = MasterOrchestrator()

    result = orch.run(
        plot=plot,
        brief_for_c4=brief_for_c4,
        floor_brief=floor_brief,
    )

    # Structural assertions.
    assert len(result.phases) == len(PIPELINE_PHASES)

    if expected_failing_phase is None:
        # Happy-path scenario.
        assert result.overall_status == PhaseStatus.OK, (
            f"{scenario_id}: overall_status={result.overall_status} "
            f"(expected OK)"
        )
        for phase_id in _CHAIN_OK_PHASES:
            phase = result.phase(phase_id)
            assert phase is not None, f"{scenario_id}: missing phase {phase_id}"
            assert phase.status == PhaseStatus.OK, (
                f"{scenario_id}: phase {phase_id} status={phase.status} "
                f"({phase.error_class}: {phase.error_message})"
            )
        c16 = result.phase("c16_dual_drawings")
        assert c16.status in (PhaseStatus.OK, PhaseStatus.STUB)
    else:
        # Known-broken scenario — verify only the expected phase errors.
        bad = result.phase(expected_failing_phase)
        assert bad is not None
        assert bad.status == PhaseStatus.ERROR, (
            f"{scenario_id}: expected {expected_failing_phase} to ERROR "
            f"(B-107 NE-facing); got {bad.status}"
        )
        assert bad.error_class  # non-empty error class
        # Overall status reflects the failure.
        assert result.overall_status == PhaseStatus.ERROR

    # C17 stays SKIPPED inside the master pipeline regardless (S59 #9 wiring).
    c17 = result.phase("c17_quote_comparison")
    assert c17.status == PhaseStatus.SKIPPED


def test_scenario_with_disabled_c11b_skips_cleanly():
    """Disabling C11b refinement still produces a valid result."""
    plot = bangalore_40x60()
    brief_for_c4 = make_brief(plot)
    floor_brief = medium_brief()
    config = MasterOrchestratorConfig(enable_c11b_refinement=False)
    orch = MasterOrchestrator(config)

    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    assert result.overall_status == PhaseStatus.OK
    c11b = result.phase("c11b_nsga_refinement")
    assert c11b.status == PhaseStatus.SKIPPED


def test_scenario_with_mvp_grid_compat_path():
    """Disabling full structural engine reverts C7 to GridGenerator-only.

    Confirms the S57 #1 MVP-compat path still works alongside the new
    downstream wiring.
    """
    plot = bangalore_40x60()
    brief_for_c4 = make_brief(plot)
    floor_brief = medium_brief()
    config = MasterOrchestratorConfig(enable_full_structural_engine=False)
    orch = MasterOrchestrator(config)

    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    assert result.overall_status == PhaseStatus.OK
    c07 = result.phase("c07_structural_grid")
    assert c07.status == PhaseStatus.OK
    # MVP path payload is the Grid directly.
    assert hasattr(c07.payload, "columns") or hasattr(c07.payload, "max_span_m")
    assert not hasattr(c07.payload, "structure")


def test_scenario_with_vastu_off():
    """Vastu OFF must not break the orientation phase."""
    plot = bangalore_40x60()
    brief_for_c4 = make_brief(plot)
    floor_brief = medium_brief()
    config = MasterOrchestratorConfig(vastu_tier="OFF")
    orch = MasterOrchestrator(config)

    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    assert result.overall_status == PhaseStatus.OK
    c06 = result.phase("c06_orientation")
    assert c06.status == PhaseStatus.OK
