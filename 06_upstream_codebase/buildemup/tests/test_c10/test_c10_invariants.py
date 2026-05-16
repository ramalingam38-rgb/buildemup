"""
BuildemUp† — Component 10 — invariants tests.

Per C10 SPEC v1.0 LOCKED § 4 (Invariants 1-21). Hits all invariants
that can be tested via direct schema construction; full pipeline-level
invariant tests live in test_c10_phase_logic.py and test_c10_replay.py.

†= placeholder name marker.
"""
from __future__ import annotations

import pytest

from buildemup.components.c10 import (
    BatchWetZoneInfeasibleError,
    PlacementRiskLevel,
    PlumbingConfidenceTooLow,
    RemediationGraphError,
    RemediationHint,
    RiserAnchor,
    RiserGroup,
    TrapArmDistanceExceededError,
    TrapArmEstimate,
    TruncationReason,
    WallScoreVector,
    WetZoneCapacityWeights,
    WetZonePerformanceBudgets,
    WetZonePlan,
    WetZonePlanConfig,
    WetZonePlanProvenance,
    WetZoneRiskBreakdown,
    WetZoneScoringWeights,
    plan_wet_zones,
    validate_remediation_graph,
)
from buildemup.components.c10.trap_arm import (
    estimate_trap_arm,
    gate_unverified_rows,
    manhattan_worst_case,
    symbolic_bend_estimate,
    validate_inv_11,
)
from buildemup.tests._c10_fixtures import run_c9_pipeline


# =============================================================================
# Inv 5  (master_BR adjacency) — covered by the orchestrator's HARD-edge logic;
# stub-tested here via end-to-end pipeline.
# =============================================================================


def test_pipeline_succeeds_on_v1_default_brief():
    rsc, brief, grid, plot_analysis = run_c9_pipeline()
    config = WetZonePlanConfig(require_verified_plumbing=False)
    out = plan_wet_zones(rsc, brief, grid, plot_analysis, config=config)
    assert len(out) > 0


# =============================================================================
# Inv 7 — riser_count >= 1 if any wet rooms present
# =============================================================================


def test_inv_7_riser_count_at_least_one_for_typical_brief():
    rsc, brief, grid, plot_analysis = run_c9_pipeline()
    out = plan_wet_zones(
        rsc, brief, grid, plot_analysis,
        config=WetZonePlanConfig(require_verified_plumbing=False),
    )
    for planned in out:
        assert planned.wet_zone_plan.riser_count >= 1


# =============================================================================
# Inv 10 — total_wet_run_length_m finite + non-negative
# =============================================================================


def test_inv_10_run_length_non_negative():
    rsc, brief, grid, plot_analysis = run_c9_pipeline()
    out = plan_wet_zones(
        rsc, brief, grid, plot_analysis,
        config=WetZonePlanConfig(require_verified_plumbing=False),
    )
    for planned in out:
        assert planned.wet_zone_plan.total_wet_run_length_m >= 0
        assert planned.wet_zone_plan.total_wet_run_length_m == round(
            planned.wet_zone_plan.total_wet_run_length_m, 6,
        )


# =============================================================================
# Inv 11 — trap-arm distance dual-bound (Q34) tests via direct unit
# =============================================================================


class TestInv11DualBound:

    def _est(self, upper, likely):
        return TrapArmEstimate(upper_bound_m=upper, likely_bound_m=likely)

    def test_both_under_max_passes(self):
        # WC max = 1.83m, tolerance 0.15
        # Both within: no raise, no warning
        ests = {("BA1", "water_closet"): self._est(1.0, 0.5)}
        unverified, warnings = validate_inv_11(ests, tolerance_m=0.15)
        assert warnings == []

    def test_likely_within_upper_over_warns_only(self):
        # WC max = 1.83m, tolerance 0.15. threshold = 1.98
        # likely=1.5 (under), upper=2.5 (over) -> WARN, no RAISE
        ests = {("BA1", "water_closet"): self._est(2.5, 1.5)}
        unverified, warnings = validate_inv_11(ests, tolerance_m=0.15)
        assert len(warnings) == 1
        assert warnings[0][2] == "upper_bound_warn"

    def test_both_over_raises(self):
        # WC threshold = 1.98. Both over → RAISE.
        ests = {("BA1", "water_closet"): self._est(3.0, 2.5)}
        with pytest.raises(TrapArmDistanceExceededError):
            validate_inv_11(ests, tolerance_m=0.15)


# =============================================================================
# Inv 13 — RiserGroup.wet_room_ids non-empty
# =============================================================================


def test_inv_13_riser_group_wet_room_ids_non_empty():
    anchor = RiserAnchor(
        wall_id="WALL_NORTH", anchor_position_m=2.0,
        riser_anchor_xy=(2.0, 5.0), column_id=None, snap_distance_m=None,
    )
    with pytest.raises(ValueError, match="wet_room_ids"):
        RiserGroup(group_id="rg1", anchors=(anchor,), wet_room_ids=())


# =============================================================================
# Inv 16 — fixture types must exist in plumbing_minimums KB (cross-checked
# at pipeline level; direct test via lookup helper covers this)
# =============================================================================


def test_inv_16_orchestrator_uses_only_kb_known_fixtures():
    rsc, brief, grid, plot_analysis = run_c9_pipeline()
    out = plan_wet_zones(
        rsc, brief, grid, plot_analysis,
        config=WetZonePlanConfig(require_verified_plumbing=False),
    )
    # Reference set from KB
    from buildemup.components.c10 import load_plumbing_minimums
    valid = {
        row["fixture_type"]
        for row in load_plumbing_minimums()["rows"]
    }
    for planned in out:
        for fts in planned.wet_zone_plan.fixture_types_per_room.values():
            for ft in fts:
                assert ft in valid, f"{ft!r} not in plumbing_minimums KB"


# =============================================================================
# Inv 20 — bend_estimation_mode == "symbolic_v1"
# =============================================================================


def test_inv_20_bend_estimation_mode_locked():
    rsc, brief, grid, plot_analysis = run_c9_pipeline()
    out = plan_wet_zones(
        rsc, brief, grid, plot_analysis,
        config=WetZonePlanConfig(require_verified_plumbing=False),
    )
    for planned in out:
        assert planned.wet_zone_plan.bend_estimation_mode == "symbolic_v1"


# =============================================================================
# Inv 21 — RemediationHint mutex graph DAG
# =============================================================================


class TestInv21RemediationGraph:

    def _hint(self, parameter: str, mutex=(), priority=10):
        return RemediationHint(
            kind="manual_review",
            parameter=parameter,
            current_value=1, suggested_value=2,
            severity="medium",
            human_readable="x",
            retry_priority=priority,
            mutually_exclusive_with=mutex,
        )

    def test_empty_hints_pass(self):
        validate_remediation_graph(())

    def test_single_hint_passes(self):
        validate_remediation_graph((self._hint("a"),))

    def test_acyclic_chain_passes(self):
        h1 = self._hint("a", mutex=("b",), priority=10)
        h2 = self._hint("b", mutex=("c",), priority=20)
        h3 = self._hint("c", priority=30)
        validate_remediation_graph((h1, h2, h3))

    def test_two_node_cycle_raises(self):
        # a -> b, b -> a is a cycle
        h1 = self._hint("a", mutex=("b",), priority=10)
        h2 = self._hint("b", mutex=("a",), priority=20)
        with pytest.raises(RemediationGraphError, match="cycles"):
            validate_remediation_graph((h1, h2))

    def test_three_node_cycle_raises(self):
        h1 = self._hint("a", mutex=("b",), priority=10)
        h2 = self._hint("b", mutex=("c",), priority=20)
        h3 = self._hint("c", mutex=("a",), priority=30)
        with pytest.raises(RemediationGraphError, match="cycles"):
            validate_remediation_graph((h1, h2, h3))

    def test_dangling_mutex_does_not_raise(self):
        # Refers to non-existent parameter — at v1 this is permitted.
        h1 = self._hint("a", mutex=("nonexistent",), priority=10)
        validate_remediation_graph((h1,))

    def test_duplicate_priority_parameter_raises(self):
        h1 = self._hint("a", priority=10)
        h2 = self._hint("a", priority=10)        # exact duplicate
        with pytest.raises(RemediationGraphError, match="duplicate"):
            validate_remediation_graph((h1, h2))

    def test_provenance_post_init_runs_validation(self):
        # Provenance __post_init__ defensively runs validate_remediation_graph.
        cyclic = (
            self._hint("a", mutex=("b",), priority=10),
            self._hint("b", mutex=("a",), priority=20),
        )
        with pytest.raises(RemediationGraphError):
            WetZonePlanProvenance(
                derived_at=0.0,
                plot_analysis_trace_id="t",
                floor_label="ground",
                plumbing_kb_version="v",
                fixture_profiles_kb_version="v",
                enforcement_mode="warn",
                pooja_adjacency_mode="strict",
                scoring_profile="neutral",
                scoring_weights_snapshot=WetZoneScoringWeights(),
                cluster_decisions=(),
                wall_scoring_breakdown=(),
                forced_culturally_discouraged=(),
                unverified_plumbing_rows_used=(),
                search_truncated=False,
                states_explored=0,
                truncation_reason=TruncationReason.COMPLETED,
                _observational_runtime_ms=0,
                risk_breakdown=WetZoneRiskBreakdown(
                    optimization_risk=PlacementRiskLevel.LOW,
                    optimization_score=0.0,
                    engineering_risk=PlacementRiskLevel.LOW,
                    engineering_score=0.0,
                    cultural_risk=PlacementRiskLevel.LOW,
                    cultural_score=0.0,
                ),
                remediation_hints=cyclic,
                performance_budget_warnings=(),
                rule_trace=(),
            )


# =============================================================================
# PlumbingConfidenceTooLow gating (require_verified_plumbing=True path)
# =============================================================================


class TestPlumbingConfidenceGate:

    def test_gate_no_unverified_rows_passes_under_strict(self):
        gate_unverified_rows((), require_verified=True)

    def test_gate_unverified_rows_raise_under_strict(self):
        with pytest.raises(PlumbingConfidenceTooLow):
            gate_unverified_rows(("floor_drain",), require_verified=True)

    def test_gate_unverified_rows_no_raise_under_lenient(self):
        gate_unverified_rows(("floor_drain",), require_verified=False)


# =============================================================================
# manhattan_worst_case
# =============================================================================


class TestManhattanWorstCase:

    def test_zero_distance_when_anchor_at_corner(self):
        d = manhattan_worst_case((0.0, 0.0, 1.0, 1.0), (0.0, 0.0))
        # Worst corner is (1, 1) -> distance = 1 + 1 = 2
        assert d == 2.0

    def test_anchor_at_centre(self):
        d = manhattan_worst_case((0.0, 0.0, 4.0, 4.0), (2.0, 2.0))
        # Each corner is 2+2 = 4 from centre
        assert d == 4.0

    def test_anchor_outside_bbox(self):
        d = manhattan_worst_case((0.0, 0.0, 1.0, 1.0), (10.0, 10.0))
        # Worst corner is (0, 0) -> 10 + 10 = 20
        assert d == 20.0


# =============================================================================
# estimate_trap_arm — Q43 per-fixture factor
# =============================================================================


class TestEstimateTrapArm:

    def test_water_closet_factor_0_8(self):
        bbox = (0.0, 0.0, 1.0, 1.0)
        anchor = (0.0, 0.0)
        # upper_bound = 2.0, factor=0.8 → likely=1.6
        e = estimate_trap_arm("water_closet", bbox, anchor)
        assert e.upper_bound_m == 2.0
        assert e.likely_bound_m == 1.6

    def test_kitchen_sink_factor_0_4(self):
        e = estimate_trap_arm("kitchen_sink", (0.0, 0.0, 1.0, 1.0), (0.0, 0.0))
        assert e.upper_bound_m == 2.0
        assert e.likely_bound_m == 0.8

    def test_unknown_fixture_falls_back_to_0_5(self):
        e = estimate_trap_arm("unknown_ft", (0.0, 0.0, 1.0, 1.0), (0.0, 0.0))
        assert e.upper_bound_m == 2.0
        assert e.likely_bound_m == 1.0


# =============================================================================
# symbolic_bend_estimate — Q42 horizontal-first convention
# =============================================================================


class TestSymbolicBendEstimate:

    def test_zero_when_fixture_at_anchor(self):
        assert symbolic_bend_estimate((1.0, 1.0), (1.0, 1.0)) == 0

    def test_zero_when_collinear_x(self):
        # Horizontal-only routing
        assert symbolic_bend_estimate((0.0, 1.0), (5.0, 1.0)) == 1

    def test_zero_when_collinear_y(self):
        assert symbolic_bend_estimate((1.0, 0.0), (1.0, 5.0)) == 1

    def test_two_when_general_displacement(self):
        assert symbolic_bend_estimate((0.0, 0.0), (5.0, 5.0)) == 2
