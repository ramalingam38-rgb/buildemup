"""Scenario corpus for the master orchestrator (S59 follow-up #13).

Exercises every (plot, brief) combo from the named-fixture registry
against the orchestrator. Each test confirms:
  - The pipeline runs without raising.
  - All 17 phases produce a PhaseResult.
  - For happy-path scenarios: C4-C14 reach OK; overall status is OK.
  - For known-broken scenarios: the named component phase degrades to
    STUB (S59 extended — the orchestrator now gracefully downgrades
    every known component-level failure to STUB rather than ERROR-
    cascading the pipeline). overall_status stays OK because STUB
    phases don't trip aggregation.

The underlying component bugs (B-107 intercardinal, C8 self-
intersection, C9 sizing exhaustion, C10 wall-assignment exhaustion)
all remain open at the component level; the orchestrator surface
just degrades gracefully so the UI can display the limitation
honestly. When a component-level fix lands, flip the assertion to
expect OK and remove the entry from `_KNOWN_BROKEN_DOWNGRADES`.

Comprehensive edge-case coverage (Pune BLACK_COTTON, Mumbai stilt
parking, Delhi corner plot, etc.) is tracked separately as v1+
scenarios; this file covers the named-fixture matrix.
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


# Each row: (test_id, plot_builder, brief_builder, downgraded_phase).
# downgraded_phase = None means the scenario reaches overall OK with
# every chain phase OK. When set, that phase is known to STUB-degrade
# due to a CURRENT component-level limitation; the orchestrator
# converts the underlying exception to a graceful STUB result so the
# pipeline doesn't cascade-error and the UI surface can show the
# limitation honestly. Overall status remains OK in both branches.
_SCENARIOS = [
    # Happy path — the smoke baseline.
    ("bangalore_40x60_medium", bangalore_40x60, medium_brief, None),

    # Known-broken combos — orchestrator gracefully degrades each to
    # STUB on the named phase. The underlying component bug remains
    # open; closing it means changing the assertion below to None.
    #   C6 (orientation): NE/SE/SW/NW facings rejected per B-107.
    ("chennai_30x40_small",    chennai_30x40,   small_brief,
     "c06_orientation"),
    #   C8 (corridor): Delhi 60x90 + large brief produces a corridor
    #   self-intersection (Inv 11) — B-C8-LARGE-PLOT-COVERAGE.
    ("delhi_60x90_large",      delhi_60x90,     large_brief,
     "c08_corridor"),
    #   C9 (room sizer): Pune 30x40 + medium brief exhausts sizing
    #   search budget on every candidate.
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
    "scenario_id,plot_builder,brief_builder,downgraded_phase",
    _SCENARIOS,
    ids=[s[0] for s in _SCENARIOS],
)
def test_scenario_pipeline_runs_end_to_end(
    scenario_id, plot_builder, brief_builder, downgraded_phase,
):
    """Each scenario runs without raising.

    When `downgraded_phase` is None, every chain phase ships OK and
    overall_status is OK. When set, that one phase ships STUB
    (orchestrator graceful-downgrade — S59 extended), every phase
    downstream of it SKIPs cleanly, and overall_status stays OK
    because STUB doesn't trip aggregation.
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
    # overall_status is OK regardless — STUB does not cascade to ERROR.
    assert result.overall_status == PhaseStatus.OK, (
        f"{scenario_id}: overall_status={result.overall_status} "
        f"(expected OK; only ERROR would flip aggregation)"
    )

    if downgraded_phase is None:
        # Happy-path scenario — every chain phase OK.
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
        # Known-broken scenario — orchestrator downgrades the named
        # phase to STUB with a populated stub_reason. Everything
        # downstream SKIPs because its `is None` guard fires.
        degraded = result.phase(downgraded_phase)
        assert degraded is not None
        assert degraded.status == PhaseStatus.STUB, (
            f"{scenario_id}: expected {downgraded_phase} to STUB-"
            f"degrade gracefully; got {degraded.status}"
        )
        assert degraded.stub_reason, (
            f"{scenario_id}: downgraded phase {downgraded_phase} must "
            f"carry a populated stub_reason for the UI to display."
        )

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
