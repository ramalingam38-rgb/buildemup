"""
BuildemUp† — Component 10 — schema unit tests.

Per C10 SPEC v1.0 LOCKED § 2 (Contract / Schema). Covers:
  - dataclass construction happy paths
  - __post_init__ invariant rejection
  - RiserGroup multi-anchor rejection (v1)
  - TrapArmEstimate likely <= upper enforcement
  - RemediationHint kind / severity / retry_priority validation
  - WetZonePlan Inv 10/20 enforcement
  - module constants present and well-formed
  - compute_scoring_weights_hash determinism

†= placeholder name marker.
"""
from __future__ import annotations

import pytest

from buildemup.components.c10 import (
    EPSILON,
    LIKELY_BOUND_FACTORS_BY_FIXTURE,
    SERIALIZATION_PRECISION,
    EnforcementMode,
    ForcedCultureOverride,
    PlacementRiskLevel,
    RemediationHint,
    RiserAnchor,
    RiserGroup,
    TrapArmEstimate,
    TruncationReason,
    WallScoreVector,
    WetZoneCapacityWeights,
    WetZonePerformanceBudgets,
    WetZonePlan,
    WetZonePlanConfig,
    WetZoneRiskBreakdown,
    WetZoneScoringWeights,
    compute_scoring_weights_hash,
)


# =============================================================================
# Module constants
# =============================================================================


class TestModuleConstants:

    def test_epsilon_is_finite_positive(self):
        assert EPSILON > 0
        assert EPSILON < 1e-3

    def test_serialization_precision_is_six(self):
        assert SERIALIZATION_PRECISION == 6

    def test_likely_bound_factors_covers_v1_fixture_set(self):
        expected = {
            "water_closet", "lavatory", "shower", "bathtub",
            "kitchen_sink", "utility_sink", "floor_drain",
        }
        assert set(LIKELY_BOUND_FACTORS_BY_FIXTURE.keys()) == expected

    def test_likely_bound_factors_in_unit_interval(self):
        for ft, factor in LIKELY_BOUND_FACTORS_BY_FIXTURE.items():
            assert 0.0 < factor <= 1.0, (
                f"factor for {ft} = {factor} outside (0, 1]"
            )


# =============================================================================
# Enums
# =============================================================================


class TestEnums:

    def test_enforcement_mode_values(self):
        assert EnforcementMode.WARN.value == "warn"
        assert EnforcementMode.STRICT.value == "strict"

    def test_placement_risk_level_values(self):
        assert {e.value for e in PlacementRiskLevel} == {"low", "medium", "high"}

    def test_truncation_reason_values(self):
        assert TruncationReason.COMPLETED.value == "completed"
        assert TruncationReason.MAX_STATES.value == "max_states"
        assert TruncationReason.INFEASIBLE_TERMINATED.value == "infeasible_terminated"


# =============================================================================
# TrapArmEstimate
# =============================================================================


class TestTrapArmEstimate:

    def test_construct_happy_path(self):
        e = TrapArmEstimate(upper_bound_m=2.0, likely_bound_m=1.5)
        assert e.upper_bound_m == 2.0
        assert e.likely_bound_m == 1.5

    def test_likely_equal_to_upper_ok(self):
        e = TrapArmEstimate(upper_bound_m=1.0, likely_bound_m=1.0)
        assert e.likely_bound_m == e.upper_bound_m

    def test_likely_above_upper_rejected(self):
        with pytest.raises(ValueError, match="likely_bound_m"):
            TrapArmEstimate(upper_bound_m=1.0, likely_bound_m=1.5)

    def test_negative_upper_rejected(self):
        with pytest.raises(ValueError, match="upper_bound_m"):
            TrapArmEstimate(upper_bound_m=-1.0, likely_bound_m=0.0)

    def test_negative_likely_rejected(self):
        with pytest.raises(ValueError, match="likely_bound_m"):
            TrapArmEstimate(upper_bound_m=2.0, likely_bound_m=-0.5)

    def test_frozen(self):
        e = TrapArmEstimate(upper_bound_m=2.0, likely_bound_m=1.0)
        with pytest.raises(Exception):
            e.upper_bound_m = 99.0      # type: ignore[misc]


# =============================================================================
# RemediationHint
# =============================================================================


class TestRemediationHint:

    def _make(self, **overrides):
        defaults = dict(
            kind="manual_review",
            parameter="x",
            current_value=1,
            suggested_value=2,
            severity="high",
            human_readable="hi",
            retry_priority=99,
        )
        defaults.update(overrides)
        return RemediationHint(**defaults)

    def test_construct_happy_path(self):
        h = self._make()
        assert h.kind == "manual_review"
        assert h.retry_priority == 99
        assert h.mutually_exclusive_with == ()
        assert h.expected_success_probability is None

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValueError, match="kind"):
            self._make(kind="not_a_kind")

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValueError, match="severity"):
            self._make(severity="medium-low")

    def test_empty_parameter_rejected(self):
        with pytest.raises(ValueError, match="parameter"):
            self._make(parameter="")

    def test_retry_priority_must_be_int(self):
        with pytest.raises(TypeError):
            self._make(retry_priority="high")

    def test_mutually_exclusive_with_must_be_tuple(self):
        with pytest.raises(TypeError):
            self._make(mutually_exclusive_with=["x", "y"])

    def test_mutually_exclusive_with_entries_must_be_str(self):
        with pytest.raises(TypeError):
            self._make(mutually_exclusive_with=(1, 2))

    def test_expected_success_probability_in_unit_interval(self):
        with pytest.raises(ValueError):
            self._make(expected_success_probability=1.5)
        with pytest.raises(ValueError):
            self._make(expected_success_probability=-0.1)

    def test_expected_success_probability_at_bounds_ok(self):
        h0 = self._make(expected_success_probability=0.0)
        h1 = self._make(expected_success_probability=1.0)
        assert h0.expected_success_probability == 0.0
        assert h1.expected_success_probability == 1.0


# =============================================================================
# RiserGroup
# =============================================================================


class TestRiserGroup:

    def _anchor(self) -> RiserAnchor:
        return RiserAnchor(
            wall_id="WALL_NORTH", anchor_position_m=2.5,
            riser_anchor_xy=(2.5, 5.0), column_id=None, snap_distance_m=None,
        )

    def test_construct_with_one_anchor_ok(self):
        rg = RiserGroup(
            group_id="rg1",
            anchors=(self._anchor(),),
            wet_room_ids=("BATHROOM_1",),
        )
        assert len(rg.anchors) == 1
        assert rg.wet_room_ids == ("BATHROOM_1",)

    def test_zero_anchors_rejected(self):
        with pytest.raises(ValueError, match="exactly 1 anchor"):
            RiserGroup(group_id="rg1", anchors=(), wet_room_ids=("X",))

    def test_two_anchors_rejected(self):
        with pytest.raises(ValueError, match="exactly 1 anchor"):
            RiserGroup(
                group_id="rg1",
                anchors=(self._anchor(), self._anchor()),
                wet_room_ids=("X",),
            )

    def test_empty_wet_room_ids_rejected(self):
        with pytest.raises(ValueError, match="wet_room_ids"):
            RiserGroup(
                group_id="rg1",
                anchors=(self._anchor(),),
                wet_room_ids=(),
            )


# =============================================================================
# WetZonePlanConfig
# =============================================================================


class TestWetZonePlanConfig:

    def test_default_construction(self):
        c = WetZonePlanConfig()
        # production-default per § 5
        assert c.require_verified_plumbing is True
        assert c.scoring_profile == "neutral"
        assert c.enforcement_mode == EnforcementMode.WARN
        assert c.pooja_adjacency_mode == "strict"
        assert c.trap_arm_tolerance_m == 0.15
        assert isinstance(c.scoring_weights, WetZoneScoringWeights)
        assert isinstance(c.capacity_weights, WetZoneCapacityWeights)
        assert isinstance(c.performance_budgets, WetZonePerformanceBudgets)

    def test_override_require_verified_plumbing(self):
        c = WetZonePlanConfig(require_verified_plumbing=False)
        assert c.require_verified_plumbing is False


# =============================================================================
# WetZoneCapacityWeights
# =============================================================================


class TestWetZoneCapacityWeights:

    def test_default_weights_v1_set(self):
        w = WetZoneCapacityWeights()
        assert w.fixture_capacity_weights["water_closet"] == 2.0
        assert w.fixture_capacity_weights["shower"] == 1.5
        assert w.fixture_capacity_weights["lavatory"] == 1.0
        assert w.fixture_capacity_weights["kitchen_sink"] == 1.0
        assert w.fixture_capacity_weights["utility_sink"] == 1.0
        assert w.fixture_capacity_weights["floor_drain"] == 0.5

    def test_default_minimum_riser_spacing(self):
        w = WetZoneCapacityWeights()
        assert w.minimum_riser_spacing_m == 3.0


# =============================================================================
# WetZoneScoringWeights + hash
# =============================================================================


class TestWetZoneScoringWeights:

    def test_default_weights_v1(self):
        w = WetZoneScoringWeights()
        assert w.weight_engineering == 1.0
        assert w.weight_cultural == 1.0
        assert w.weight_adjacency == 1.0
        assert w.column_alignment_bonus == 0.2
        assert w.wall_length_sufficiency_bonus == 0.1
        assert w.wall_reuse_penalty == -0.5

    def test_compute_scoring_weights_hash_is_deterministic(self):
        w = WetZoneScoringWeights()
        assert compute_scoring_weights_hash(w) == compute_scoring_weights_hash(w)

    def test_hash_changes_when_weights_change(self):
        w1 = WetZoneScoringWeights()
        w2 = WetZoneScoringWeights(weight_engineering=2.0)
        assert compute_scoring_weights_hash(w1) != compute_scoring_weights_hash(w2)

    def test_hash_is_sha256_hex(self):
        h = compute_scoring_weights_hash(WetZoneScoringWeights())
        assert len(h) == 64
        int(h, 16)        # parses as hex


# =============================================================================
# WallScoreVector
# =============================================================================


class TestWallScoreVector:

    def test_construct_happy_path(self):
        v = WallScoreVector(
            wall_id="WALL_N", category="bathroom",
            engineering_score=0.5, cultural_score=1.0, adjacency_score=0.0,
            scoring_profile_id="neutral",
            scoring_weights_hash="a" * 64,
        )
        assert v.wall_id == "WALL_N"
        assert v.scoring_profile_id == "neutral"


# =============================================================================
# ForcedCultureOverride
# =============================================================================


class TestForcedCultureOverride:

    def test_construct_happy_path(self):
        f = ForcedCultureOverride(
            room_id="BATHROOM_1", wall_id="WALL_NORTH",
            category="bathroom",
            rejected_alternatives=(("WALL_SOUTH", "capacity"),),
        )
        assert f.room_id == "BATHROOM_1"
        assert len(f.rejected_alternatives) == 1


# =============================================================================
# WetZoneRiskBreakdown
# =============================================================================


class TestWetZoneRiskBreakdown:

    def test_construct_happy_path(self):
        b = WetZoneRiskBreakdown(
            optimization_risk=PlacementRiskLevel.LOW, optimization_score=0.0,
            engineering_risk=PlacementRiskLevel.MEDIUM, engineering_score=1.5,
            cultural_risk=PlacementRiskLevel.HIGH, cultural_score=3.0,
        )
        assert b.optimization_risk == PlacementRiskLevel.LOW
        assert b.cultural_score == 3.0


# =============================================================================
# WetZonePerformanceBudgets
# =============================================================================


class TestWetZonePerformanceBudgets:

    def test_default_budgets(self):
        b = WetZonePerformanceBudgets()
        assert b.max_wall_score_vectors == 100
        assert b.max_provenance_rule_trace_entries == 500
        assert b.max_remediation_hints == 20


# =============================================================================
# WetZonePlan __post_init__ Inv 10 / Inv 20
# =============================================================================


def _empty_plan(**overrides) -> WetZonePlan:
    """Construct an empty-but-valid WetZonePlan for testing __post_init__."""
    defaults = dict(
        wet_wall_assignment={},
        riser_groups=(),
        kitchen_riser_group_id=None,
        fixture_types_per_room={},
        trap_arm_distances={},
        total_wet_run_length_m=0.0,
        symbolic_bend_estimate=0,
        bend_estimation_mode="symbolic_v1",
        riser_count=0,
        non_wet_room_buffer_zones=(),
        acceptable_wall_sets={},
    )
    defaults.update(overrides)
    return WetZonePlan(**defaults)


class TestWetZonePlanInvariants:

    def test_default_plan_valid(self):
        plan = _empty_plan()
        assert plan.total_wet_run_length_m == 0.0
        assert plan.bend_estimation_mode == "symbolic_v1"

    def test_inv_10_negative_run_rejected(self):
        with pytest.raises(ValueError, match="total_wet_run_length_m"):
            _empty_plan(total_wet_run_length_m=-1.0)

    def test_inv_20_bend_estimation_mode_rejected_when_not_symbolic_v1(self):
        with pytest.raises(ValueError, match="bend_estimation_mode"):
            _empty_plan(bend_estimation_mode="other")

    def test_negative_symbolic_bend_estimate_rejected(self):
        with pytest.raises(ValueError, match="symbolic_bend_estimate"):
            _empty_plan(symbolic_bend_estimate=-1)

    def test_negative_riser_count_rejected(self):
        with pytest.raises(ValueError, match="riser_count"):
            _empty_plan(riser_count=-1)

    def test_wall_segments_used_property(self):
        anchor = RiserAnchor(
            wall_id="WALL_NORTH", anchor_position_m=1.0,
            riser_anchor_xy=(1.0, 5.0), column_id=None, snap_distance_m=None,
        )
        plan = _empty_plan(
            riser_groups=(
                RiserGroup(
                    group_id="rg1", anchors=(anchor,),
                    wet_room_ids=("BATHROOM_1",),
                ),
            ),
        )
        assert plan.wall_segments_used == ("WALL_NORTH",)
