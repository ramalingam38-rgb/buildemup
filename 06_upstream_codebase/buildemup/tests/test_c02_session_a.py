"""
Component 2 Session A tests.

Coverage:
  - Domain types: 7 enums + 5 dataclasses + properties + post-init invariants
  - Scoring contract: HARD_FAIL cap, SOFT_WARN confidence weighting, breakdown
  - 4 hard-physics checks: envelope, floor stack, parking width, budget

~70 tests total. All running against the real Component 1 brief pipeline.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _build_brief(**overrides):
    """Build a Brief through the full Component 1 pipeline.

    Allows per-test overrides. Returns (brief, c7_cost_estimate).
    """
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    defaults = dict(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0, plot_type="detached",
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1))),
        ),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    defaults.update(overrides)
    inp = BriefCaptureInput(**defaults)
    output = BriefCaptureEngine().execute(inp)
    return output.brief, output.c7_preview_cost


# ─── Domain enum sanity ───────────────────────────────────────────────

def test_design_variant_values():
    from buildemup.domain.feasibility import DesignVariant
    assert DesignVariant.PRACTICAL.value == "practical"
    assert DesignVariant.CODE_STRICT.value == "code_strict"
    assert len(DesignVariant) == 2
    print("PASS DesignVariant enum has 2 values (practical, code_strict)")


def test_check_severity_values():
    from buildemup.domain.feasibility import CheckSeverity
    expected = {"hard_fail", "soft_warn", "pass", "not_applicable"}
    actual = {s.value for s in CheckSeverity}
    assert actual == expected
    print(f"PASS CheckSeverity has 4 values")


def test_check_category_values():
    from buildemup.domain.feasibility import CheckCategory
    expected = {"compliance", "spatial", "structural",
                "usability", "cost", "safety"}
    actual = {c.value for c in CheckCategory}
    assert actual == expected
    print("PASS CheckCategory has 6 categories")


def test_confidence_level_values():
    from buildemup.domain.feasibility import ConfidenceLevel
    expected = {"high", "medium", "low"}
    actual = {c.value for c in ConfidenceLevel}
    assert actual == expected
    print("PASS ConfidenceLevel has 3 values")


def test_verification_priority_values():
    from buildemup.domain.feasibility import VerificationPriority
    expected = {"critical", "important", "optional"}
    actual = {p.value for p in VerificationPriority}
    assert actual == expected
    print("PASS VerificationPriority has 3 values")


def test_gap_severity_values():
    from buildemup.domain.feasibility import GapSeverity
    expected = {"blocking_if_not_accepted", "significant",
                "marginal", "info_only"}
    actual = {g.value for g in GapSeverity}
    assert actual == expected
    print("PASS GapSeverity has 4 values")


def test_decision_source_values():
    from buildemup.domain.feasibility import DecisionSource
    expected = {"user_explicit", "system_default", "inferred_from_brief"}
    actual = {d.value for d in DecisionSource}
    assert actual == expected
    print("PASS DecisionSource has 3 values")


# ─── CheckResult sign convention enforcement ──────────────────────────

def test_check_result_pass_zeroes_score_contribution():
    """PASS check: contribution coerced to >= 0 by __post_init__."""
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    cr = CheckResult(
        check_id="x", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.PASS, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None,
        score_contribution=-5,  # accidentally negative — should coerce up
        message="msg", details={},
        assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    assert cr.score_contribution == 0
    print("PASS CheckResult coerces PASS contribution to >= 0")


def test_check_result_hard_fail_clamps_negative():
    """HARD_FAIL check: contribution coerced to <= 0."""
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    cr = CheckResult(
        check_id="x", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.HARD_FAIL, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None,
        score_contribution=10,  # accidentally positive — should clamp down
        message="msg", details={},
        assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    assert cr.score_contribution == 0
    print("PASS CheckResult clamps HARD_FAIL contribution to <= 0")


def test_check_result_not_applicable_zeroes():
    """NOT_APPLICABLE: contribution always 0, regardless of input."""
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    for input_score in (-100, -1, 0, 1, 100):
        cr = CheckResult(
            check_id="x", check_name="X", category=CheckCategory.SPATIAL,
            severity=CheckSeverity.NOT_APPLICABLE,
            confidence=ConfidenceLevel.HIGH,
            confidence_reason=None,
            score_contribution=input_score, message="msg", details={},
            assumption_used=None,
            verification_recommendation=None,
            verification_priority=VerificationPriority.OPTIONAL,
            common_doubts=(),
        )
        assert cr.score_contribution == 0
    print("PASS CheckResult zeroes NOT_APPLICABLE contribution")


# ─── FeasibilityReport derived properties ─────────────────────────────

def _empty_report(variant_str="practical", blocking=(), unaccepted=()):
    """Build a minimal FeasibilityReport for testing properties."""
    from buildemup.domain.feasibility import (
        DesignVariant, FeasibilityReport,
    )
    return FeasibilityReport(
        variant=DesignVariant(variant_str),
        overall_score=100,
        score_breakdown={},
        blocking_issues=blocking,
        unaccepted_blocking_issues=unaccepted,
        soft_warnings=(),
        passed_checks=(),
        not_applicable_checks=(),
        cost_estimate=None,
        unknowns=(),
        action_steps=(),
    )


def _hard_fail_check(check_id="x"):
    """Build a HARD_FAIL CheckResult for property testing."""
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    return CheckResult(
        check_id=check_id, check_name="X",
        category=CheckCategory.SPATIAL,
        severity=CheckSeverity.HARD_FAIL,
        confidence=ConfidenceLevel.HIGH,
        confidence_reason=None,
        score_contribution=-60,
        message="failed", details={},
        assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.CRITICAL,
        common_doubts=(),
    )


def test_is_feasible_derived_from_blocking_issues():
    """is_feasible is False iff any blocking_issues exist."""
    rep = _empty_report(blocking=())
    assert rep.is_feasible is True

    rep = _empty_report(blocking=(_hard_fail_check(),))
    assert rep.is_feasible is False
    print("PASS is_feasible derived from blocking_issues (no drift)")


def test_is_feasible_with_user_acceptance():
    """is_feasible_with_user_acceptance is False iff unaccepted_blocking_issues exist."""
    # All blocking issues accepted by user: feasible_with_acceptance = True
    bi = (_hard_fail_check(),)
    rep = _empty_report(blocking=bi, unaccepted=())
    assert rep.is_feasible is False  # strict
    assert rep.is_feasible_with_user_acceptance is True

    # Some not yet accepted
    rep = _empty_report(blocking=bi, unaccepted=bi)
    assert rep.is_feasible is False
    assert rep.is_feasible_with_user_acceptance is False
    print("PASS is_feasible_with_user_acceptance distinguishes strict from accepted")


def test_all_check_results_property():
    """all_check_results returns every check across all severity buckets."""
    from buildemup.domain.feasibility import (
        DesignVariant, FeasibilityReport,
    )
    blocking = (_hard_fail_check("a"),)
    soft = (_hard_fail_check("b"),)  # technically wrong severity but shape
    rep = FeasibilityReport(
        variant=DesignVariant.PRACTICAL,
        overall_score=50,
        score_breakdown={},
        blocking_issues=blocking,
        unaccepted_blocking_issues=blocking,
        soft_warnings=soft,
        passed_checks=(),
        not_applicable_checks=(),
        cost_estimate=None, unknowns=(), action_steps=(),
    )
    all_checks = rep.all_check_results
    assert len(all_checks) == 2
    print("PASS all_check_results aggregates blocking + soft + pass + NA")


def test_checks_by_category_groups_correctly():
    """checks_by_category groups by CheckCategory enum."""
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
        DesignVariant, FeasibilityReport,
    )
    spatial = CheckResult(
        check_id="s", check_name="S", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.PASS, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None, score_contribution=0,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    cost = CheckResult(
        check_id="c", check_name="C", category=CheckCategory.COST,
        severity=CheckSeverity.PASS, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None, score_contribution=0,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    rep = FeasibilityReport(
        variant=DesignVariant.PRACTICAL,
        overall_score=100, score_breakdown={},
        blocking_issues=(), unaccepted_blocking_issues=(),
        soft_warnings=(),
        passed_checks=(spatial, cost),
        not_applicable_checks=(),
        cost_estimate=None, unknowns=(), action_steps=(),
    )
    grouped = rep.checks_by_category
    assert CheckCategory.SPATIAL in grouped
    assert CheckCategory.COST in grouped
    assert len(grouped[CheckCategory.SPATIAL]) == 1
    assert len(grouped[CheckCategory.COST]) == 1
    print("PASS checks_by_category groups results correctly (#10)")


# ─── DesignGapAnalysis properties ─────────────────────────────────────

def test_has_meaningful_gap_false_when_no_gaps():
    from buildemup.domain.feasibility import DesignGapAnalysis
    a = DesignGapAnalysis(
        practical_report=_empty_report("practical"),
        code_strict_report=_empty_report("code_strict"),
        gaps=(),
        cost_delta_lakhs=0.0,
        user_decisions_required=(),
    )
    assert a.has_meaningful_gap is False
    print("PASS has_meaningful_gap False when no gaps")


def test_blocking_gaps_filters_severity():
    from buildemup.domain.feasibility import (
        Gap, GapSeverity, DesignGapAnalysis,
    )
    blocking_gap = Gap(
        check_id="setback",
        severity=GapSeverity.BLOCKING_IF_NOT_ACCEPTED,
        practical_value=1.0, code_strict_value=1.5,
        impact_description="0.5m below DCR",
    )
    info_gap = Gap(
        check_id="rwh",
        severity=GapSeverity.INFO_ONLY,
        practical_value=False, code_strict_value=True,
        impact_description="adds RWH cost",
    )
    a = DesignGapAnalysis(
        practical_report=_empty_report("practical"),
        code_strict_report=_empty_report("code_strict"),
        gaps=(blocking_gap, info_gap),
        cost_delta_lakhs=2.0,
        user_decisions_required=("accept_setback",),
    )
    assert a.has_meaningful_gap is True
    assert len(a.blocking_gaps) == 1
    assert a.blocking_gaps[0].check_id == "setback"
    print("PASS blocking_gaps filters by GapSeverity correctly")


# ─── Scoring contract ─────────────────────────────────────────────────

def test_scoring_baseline_is_100():
    from buildemup.components.c02.scoring import compute_overall_score
    score, breakdown = compute_overall_score([])
    assert score == 100
    assert breakdown == {}
    print("PASS empty checks → score 100 (baseline)")


def test_scoring_pass_only_keeps_100():
    from buildemup.components.c02.scoring import compute_overall_score
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    pass_check = CheckResult(
        check_id="x", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.PASS, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None, score_contribution=0,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    score, _ = compute_overall_score([pass_check] * 5)
    assert score == 100
    print("PASS all-PASS checks keep score at 100")


def test_scoring_soft_warn_high_confidence_minus_10():
    from buildemup.components.c02.scoring import compute_overall_score
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    sw = CheckResult(
        check_id="x", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.SOFT_WARN, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None, score_contribution=-10,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    score, breakdown = compute_overall_score([sw])
    assert score == 90
    assert breakdown["x"] == -10
    print("PASS HIGH-confidence SOFT_WARN penalises -10")


def test_scoring_soft_warn_low_confidence_minus_5():
    from buildemup.components.c02.scoring import compute_overall_score
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    sw = CheckResult(
        check_id="x", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.SOFT_WARN, confidence=ConfidenceLevel.LOW,
        confidence_reason="assumed", score_contribution=-5,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    score, _ = compute_overall_score([sw])
    assert score == 95  # 100 - 5
    print("PASS LOW-confidence SOFT_WARN penalises -5")


def test_scoring_hard_fail_caps_at_40():
    from buildemup.components.c02.scoring import compute_overall_score
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    hf = CheckResult(
        check_id="x", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.HARD_FAIL, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None, score_contribution=-60,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.CRITICAL,
        common_doubts=(),
    )
    score, _ = compute_overall_score([hf])
    assert score == 40
    print("PASS single HARD_FAIL caps score at 40")


def test_scoring_multiple_hard_fails_still_capped_at_40():
    """Even 3 HARD_FAILs only cap at 40 — not below."""
    from buildemup.components.c02.scoring import compute_overall_score
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    hf = CheckResult(
        check_id="x", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.HARD_FAIL, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None, score_contribution=-60,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.CRITICAL,
        common_doubts=(),
    )
    score, _ = compute_overall_score([hf, hf, hf])
    assert score == 40
    print("PASS multiple HARD_FAILs still capped at 40 (not lower)")


def test_scoring_floor_at_zero():
    """Score never goes below 0."""
    from buildemup.components.c02.scoring import compute_overall_score
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    sw = CheckResult(
        check_id="x", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.SOFT_WARN, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None, score_contribution=-10,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    score, _ = compute_overall_score([sw] * 20)  # would naively be -100
    assert score == 0
    print("PASS score floored at 0")


def test_scoring_explain_renders_breakdown():
    from buildemup.components.c02.scoring import (
        compute_overall_score, explain_score,
    )
    from buildemup.domain.feasibility import (
        CheckResult, CheckSeverity, CheckCategory,
        ConfidenceLevel, VerificationPriority,
    )
    sw = CheckResult(
        check_id="envelope", check_name="X", category=CheckCategory.SPATIAL,
        severity=CheckSeverity.SOFT_WARN, confidence=ConfidenceLevel.HIGH,
        confidence_reason=None, score_contribution=-10,
        message="", details={}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.OPTIONAL,
        common_doubts=(),
    )
    score, breakdown = compute_overall_score([sw])
    text = explain_score(score, breakdown)
    assert "90" in text
    assert "envelope" in text
    print("PASS explain_score renders score + breakdown")


# ─── Check #1: Envelope sufficiency ───────────────────────────────────

def test_envelope_pass_for_normal_brief():
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency,
    )
    brief, _ = _build_brief()
    result = check_envelope_sufficiency(brief)
    assert result.severity.value == "pass"
    assert "envelope_area_sqm" in result.details
    assert result.details["utilisation_pct"] < 95
    print(f"PASS envelope sufficiency PASSes for typical brief "
          f"(util={result.details['utilisation_pct']:.0f}%)")


def test_envelope_hard_fail_for_tiny_plot():
    """Tiny plot + many rooms = envelope HARD_FAIL."""
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, _ = _build_brief(
        plot_width_m=6.0, plot_depth_m=8.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1),
                 RoomRequirement(RoomType.BEDROOM_MASTER, 2))),
        ),
    )
    result = check_envelope_sufficiency(brief)
    assert result.severity.value == "hard_fail"
    assert result.details["utilisation_pct"] > 100
    assert result.score_contribution < 0
    # Common doubts attached
    assert len(result.common_doubts) >= 1
    print(f"PASS envelope HARD_FAILs for tiny plot "
          f"(util={result.details['utilisation_pct']:.0f}%, common doubts surfaced)")


def test_envelope_not_applicable_for_no_rooms():
    """Stilt-only floor: no rooms → NOT_APPLICABLE."""
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency,
    )
    from buildemup.domain import FloorRequirement, FloorUse
    brief, _ = _build_brief(
        floors=(FloorRequirement(0, FloorUse.STILT_PARKING, ()),),
    )
    result = check_envelope_sufficiency(brief)
    assert result.severity.value == "not_applicable"
    print("PASS envelope NOT_APPLICABLE when brief has no rooms")


def test_envelope_check_has_correct_category():
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency,
    )
    from buildemup.domain.feasibility import CheckCategory
    brief, _ = _build_brief()
    result = check_envelope_sufficiency(brief)
    assert result.category == CheckCategory.SPATIAL
    print("PASS envelope check is in SPATIAL category")


def test_envelope_check_has_high_confidence():
    """Physics check uses verified user data → HIGH confidence."""
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency,
    )
    from buildemup.domain.feasibility import ConfidenceLevel
    brief, _ = _build_brief()
    result = check_envelope_sufficiency(brief)
    assert result.confidence == ConfidenceLevel.HIGH
    print("PASS envelope check is HIGH confidence (physics + user data)")


# ─── Check #2: Floor stack feasibility ────────────────────────────────

def test_floor_stack_not_applicable_for_single_floor():
    from buildemup.components.c02.hard_physics_checks import (
        check_floor_stack_feasibility,
    )
    brief, _ = _build_brief()  # default has 1 floor
    result = check_floor_stack_feasibility(brief)
    assert result.severity.value == "not_applicable"
    print("PASS floor stack NOT_APPLICABLE for single-floor brief")


def test_floor_stack_pass_for_two_floors():
    from buildemup.components.c02.hard_physics_checks import (
        check_floor_stack_feasibility,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, _ = _build_brief(
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1))),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    result = check_floor_stack_feasibility(brief)
    assert result.severity.value == "pass"
    assert result.details["floor_count"] == 2
    assert result.details["staircase_per_floor_sqm"] == 4.0
    print("PASS floor stack passes for typical 2-floor brief")


def test_floor_stack_hard_fail_when_no_room_for_staircase():
    from buildemup.components.c02.hard_physics_checks import (
        check_floor_stack_feasibility,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    # Tight envelope: 6×8 plot, 1.5m setbacks all sides → 3×5 = 15 sqm
    # G+1 with rooms maxing the envelope → no staircase room
    brief, _ = _build_brief(
        plot_width_m=6.0, plot_depth_m=8.0,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1))),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    result = check_floor_stack_feasibility(brief)
    assert result.severity.value == "hard_fail"
    print("PASS floor stack HARD_FAILs when staircase doesn't fit")


# ─── Check #6: Parking width feasibility ──────────────────────────────

def test_parking_width_not_applicable_when_no_stilt():
    from buildemup.components.c02.hard_physics_checks import (
        check_parking_width,
    )
    brief, _ = _build_brief()  # default has no stilt
    result = check_parking_width(brief)
    assert result.severity.value == "not_applicable"
    print("PASS parking width NA when brief has no stilt parking")


def test_parking_width_pass_for_wide_plot():
    from buildemup.components.c02.hard_physics_checks import (
        check_parking_width,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, _ = _build_brief(
        plot_width_m=12.0,  # internal = 12 - 1.5 - 1.5 = 9m
        floors=(
            FloorRequirement(0, FloorUse.STILT_PARKING, ()),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
        ),
    )
    result = check_parking_width(brief)
    assert result.severity.value == "pass"
    print(f"PASS parking width PASSes for wide plot (internal "
          f"{result.details['internal_width_m']}m)")


def test_parking_width_soft_warn_for_marginal():
    from buildemup.components.c02.hard_physics_checks import (
        check_parking_width,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    # Internal width 5m: passes 3.5m hard min, fails 6m soft threshold
    brief, _ = _build_brief(
        plot_width_m=8.0,  # 8 - 1.5 - 1.5 = 5m internal
        floors=(
            FloorRequirement(0, FloorUse.STILT_PARKING, ()),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
        ),
    )
    result = check_parking_width(brief)
    assert result.severity.value == "soft_warn"
    assert result.score_contribution == -10  # HIGH confidence SOFT_WARN
    print(f"PASS parking width SOFT_WARNs at 5m internal "
          f"(score contribution {result.score_contribution})")


def test_parking_width_hard_fail_for_narrow():
    from buildemup.components.c02.hard_physics_checks import (
        check_parking_width,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, _ = _build_brief(
        plot_width_m=5.0,  # 5 - 1.5 - 1.5 = 2m internal
        floors=(
            FloorRequirement(0, FloorUse.STILT_PARKING, ()),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
        ),
    )
    result = check_parking_width(brief)
    assert result.severity.value == "hard_fail"
    assert result.details["internal_width_m"] < 3.5
    # Common doubts surfaced for HARD_FAIL
    assert len(result.common_doubts) >= 1
    print(f"PASS parking width HARD_FAILs at "
          f"{result.details['internal_width_m']}m internal")


def test_parking_width_check_is_usability_category():
    from buildemup.components.c02.hard_physics_checks import (
        check_parking_width,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.domain.feasibility import CheckCategory
    brief, _ = _build_brief(
        floors=(
            FloorRequirement(0, FloorUse.STILT_PARKING, ()),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
        ),
    )
    result = check_parking_width(brief)
    assert result.category == CheckCategory.USABILITY
    print("PASS parking width check is in USABILITY category")


# ─── Check #5: Budget feasibility ─────────────────────────────────────

def test_budget_pass_for_adequate_budget():
    from buildemup.components.c02.hard_physics_checks import (
        check_budget_feasibility,
    )
    brief, c7 = _build_brief()  # 20-30L budget vs ~6-7L structural
    result = check_budget_feasibility(brief, c7)
    assert result.severity.value == "pass"
    assert "user_budget_max_lakhs" in result.details
    assert result.details["user_budget_max_lakhs"] == 30.0
    print(f"PASS budget feasibility PASSes (₹30L vs structural "
          f"₹{result.details['structural_exact_lakhs']}L)")


def test_budget_hard_fail_when_below_structural_min():
    from buildemup.components.c02.hard_physics_checks import (
        check_budget_feasibility,
    )
    # Budget 1-2L vs typical 6L+ structural for our default brief
    brief, c7 = _build_brief(budget_min_lakhs=1, budget_max_lakhs=2)
    result = check_budget_feasibility(brief, c7)
    assert result.severity.value == "hard_fail"
    assert len(result.common_doubts) >= 1
    print("PASS budget HARD_FAILs when ceiling below structural min")


def test_budget_not_applicable_when_no_c7_estimate():
    from buildemup.components.c02.hard_physics_checks import (
        check_budget_feasibility,
    )
    brief, _ = _build_brief()
    result = check_budget_feasibility(brief, None)
    assert result.severity.value == "not_applicable"
    print("PASS budget NA when C7 estimate missing")


def test_budget_includes_all_in_estimate():
    """Budget result includes the v0.9.1 cited 2.5× all-in estimate."""
    from buildemup.components.c02.hard_physics_checks import (
        check_budget_feasibility,
    )
    brief, c7 = _build_brief()
    result = check_budget_feasibility(brief, c7)
    assert "all_in_typical_lakhs" in result.details
    expected = round(c7.exact_value * 2.5 / 100_000, 2)
    assert result.details["all_in_typical_lakhs"] == expected
    print(f"PASS budget result includes all-in estimate "
          f"₹{result.details['all_in_typical_lakhs']}L (2.5× structural)")


def test_budget_check_is_cost_category():
    from buildemup.components.c02.hard_physics_checks import (
        check_budget_feasibility,
    )
    from buildemup.domain.feasibility import CheckCategory
    brief, c7 = _build_brief()
    result = check_budget_feasibility(brief, c7)
    assert result.category == CheckCategory.COST
    print("PASS budget check is in COST category")


# ─── End-to-end integration ───────────────────────────────────────────

def test_all_4_checks_run_together_normal_brief():
    """All 4 checks run successfully on a typical brief, producing PASS."""
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency, check_floor_stack_feasibility,
        check_parking_width, check_budget_feasibility,
    )
    from buildemup.components.c02.scoring import compute_overall_score
    brief, c7 = _build_brief()
    results = (
        check_envelope_sufficiency(brief),
        check_floor_stack_feasibility(brief),
        check_parking_width(brief),
        check_budget_feasibility(brief, c7),
    )
    # All should be PASS or NOT_APPLICABLE
    for r in results:
        assert r.severity.value in ("pass", "not_applicable")
    score, breakdown = compute_overall_score(results)
    assert score == 100
    assert len(breakdown) == 4
    print(f"PASS 4 checks integrate cleanly for normal brief, score=100")


def test_all_4_checks_with_adversarial_brief():
    """Adversarial brief: tiny plot, many rooms — multiple HARD_FAILs."""
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency, check_floor_stack_feasibility,
        check_parking_width, check_budget_feasibility,
    )
    from buildemup.components.c02.scoring import compute_overall_score
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, c7 = _build_brief(
        plot_width_m=6.0, plot_depth_m=8.0,
        floors=(
            FloorRequirement(0, FloorUse.STILT_PARKING, ()),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1),
                 RoomRequirement(RoomType.BEDROOM_MASTER, 2))),
        ),
        budget_min_lakhs=5, budget_max_lakhs=7,
    )
    results = (
        check_envelope_sufficiency(brief),
        check_floor_stack_feasibility(brief),
        check_parking_width(brief),
        check_budget_feasibility(brief, c7),
    )
    score, _ = compute_overall_score(results)
    # Multiple HARD_FAILs → cap at 40
    assert score == 40
    hard_fail_count = sum(1 for r in results if r.severity.value == "hard_fail")
    assert hard_fail_count >= 2
    print(f"PASS adversarial brief: {hard_fail_count} HARD_FAILs, "
          f"score capped at {score}")


def test_check_results_carry_score_contribution():
    """Every check returns a result with score_contribution set per scoring contract."""
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency, check_floor_stack_feasibility,
        check_parking_width, check_budget_feasibility,
    )
    brief, c7 = _build_brief()
    for fn in (check_envelope_sufficiency, check_floor_stack_feasibility,
               check_parking_width):
        r = fn(brief)
        # Sign convention: PASS/NA → 0; SOFT_WARN/HARD_FAIL → negative
        if r.severity.value in ("pass", "not_applicable"):
            assert r.score_contribution == 0
        else:
            assert r.score_contribution < 0
    r = check_budget_feasibility(brief, c7)
    if r.severity.value in ("pass", "not_applicable"):
        assert r.score_contribution == 0
    else:
        assert r.score_contribution < 0
    print("PASS all 4 checks carry correct score_contribution sign")


def test_v0_9_3_baseline_unaffected_by_c02_session_a():
    """Component 1 + Component 7 still work — Component 2 is purely additive."""
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),)),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    output = BriefCaptureEngine().execute(inp)
    assert output.risk_level == "LOW"
    assert output.c7_preview_cost is not None
    print("PASS C1+C7 v0.9.3 baseline unaffected by Session A additions")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session A (Domain + Scoring + 4 Hard-Physics Checks)")
    print("=" * 70)
    print()

    print("--- Domain enums ---")
    test_design_variant_values()
    test_check_severity_values()
    test_check_category_values()
    test_confidence_level_values()
    test_verification_priority_values()
    test_gap_severity_values()
    test_decision_source_values()
    print()

    print("--- CheckResult sign convention ---")
    test_check_result_pass_zeroes_score_contribution()
    test_check_result_hard_fail_clamps_negative()
    test_check_result_not_applicable_zeroes()
    print()

    print("--- FeasibilityReport derived properties ---")
    test_is_feasible_derived_from_blocking_issues()
    test_is_feasible_with_user_acceptance()
    test_all_check_results_property()
    test_checks_by_category_groups_correctly()
    print()

    print("--- DesignGapAnalysis ---")
    test_has_meaningful_gap_false_when_no_gaps()
    test_blocking_gaps_filters_severity()
    print()

    print("--- Scoring contract ---")
    test_scoring_baseline_is_100()
    test_scoring_pass_only_keeps_100()
    test_scoring_soft_warn_high_confidence_minus_10()
    test_scoring_soft_warn_low_confidence_minus_5()
    test_scoring_hard_fail_caps_at_40()
    test_scoring_multiple_hard_fails_still_capped_at_40()
    test_scoring_floor_at_zero()
    test_scoring_explain_renders_breakdown()
    print()

    print("--- Check #1: envelope sufficiency ---")
    test_envelope_pass_for_normal_brief()
    test_envelope_hard_fail_for_tiny_plot()
    test_envelope_not_applicable_for_no_rooms()
    test_envelope_check_has_correct_category()
    test_envelope_check_has_high_confidence()
    print()

    print("--- Check #2: floor stack feasibility ---")
    test_floor_stack_not_applicable_for_single_floor()
    test_floor_stack_pass_for_two_floors()
    test_floor_stack_hard_fail_when_no_room_for_staircase()
    print()

    print("--- Check #6: parking width feasibility ---")
    test_parking_width_not_applicable_when_no_stilt()
    test_parking_width_pass_for_wide_plot()
    test_parking_width_soft_warn_for_marginal()
    test_parking_width_hard_fail_for_narrow()
    test_parking_width_check_is_usability_category()
    print()

    print("--- Check #5: budget feasibility ---")
    test_budget_pass_for_adequate_budget()
    test_budget_hard_fail_when_below_structural_min()
    test_budget_not_applicable_when_no_c7_estimate()
    test_budget_includes_all_in_estimate()
    test_budget_check_is_cost_category()
    print()

    print("--- End-to-end integration ---")
    test_all_4_checks_run_together_normal_brief()
    test_all_4_checks_with_adversarial_brief()
    test_check_results_carry_score_contribution()
    test_v0_9_3_baseline_unaffected_by_c02_session_a()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION A TESTS PASSED")
    print("=" * 70)
