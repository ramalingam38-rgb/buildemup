"""Tests for Component 3a Session 2 (Detection logic).

Per SPEC v0.2.1 Section 9.2 — covers all 10 ECs with positive + negative
fixtures, plus edge cases (no blockers, EC-004 vs EC-010 dedup).

Hand-crafts DesignGapAnalysis and Brief fixtures via small helpers.
"""
import unittest

from buildemup.domain.brief import Brief, BudgetRange, CostEstimate
from buildemup.domain.plot import Plot, PlotType
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.setbacks import Setbacks
from buildemup.domain.floor_requirement import (
    FloorRequirement, RoomRequirement, FloorUse, RoomType,
)
from buildemup.domain.feasibility import (
    DesignGapAnalysis, FeasibilityReport, DesignVariant,
    CheckResult, CheckSeverity, CheckCategory, ConfidenceLevel,
    VerificationPriority,
)
from buildemup.domain.extreme_case import (
    ExtremeCaseId, ResolutionProbability,
)
from buildemup.components.c03a.detector import ExtremeCaseDetector


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _make_check(check_id, severity=CheckSeverity.HARD_FAIL,
                category=CheckCategory.COMPLIANCE, details=None):
    """Build a minimal CheckResult for fixtures."""
    return CheckResult(
        check_id=check_id,
        check_name=check_id,
        category=category,
        severity=severity,
        confidence=ConfidenceLevel.HIGH,
        confidence_reason=None,
        score_contribution=-15,
        message=f"test message for {check_id}",
        details=details or {},
        assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.IMPORTANT,
        common_doubts=(),
    )


def _make_report(blocking=(), soft=(), passed=(), na=(),
                 cost_estimate=None):
    """Build a minimal FeasibilityReport for fixtures."""
    return FeasibilityReport(
        variant=DesignVariant.PRACTICAL,
        overall_score=40,
        score_breakdown={},
        blocking_issues=blocking,
        unaccepted_blocking_issues=blocking,
        soft_warnings=soft,
        passed_checks=passed,
        not_applicable_checks=na,
        cost_estimate=cost_estimate,
        unknowns=(),
        action_steps=(),
    )


def _make_gap_analysis(blocking=(), soft=(), cost_estimate=None):
    """Build a minimal DesignGapAnalysis for fixtures."""
    practical = _make_report(blocking=blocking, soft=soft,
                              cost_estimate=cost_estimate)
    code_strict = _make_report(blocking=(), cost_estimate=cost_estimate)
    return DesignGapAnalysis(
        practical_report=practical,
        code_strict_report=code_strict,
        gaps=(),
        cost_delta_lakhs=0.0,
        user_decisions_required=(),
    )


def _make_brief(*, plot_width_m=10.0, plot_depth_m=12.0,
                 floors_count=2, bedroom_count=2,
                 budget_max_lakhs=80,
                 user_setbacks=None, nbc_setbacks=None,
                 city="chennai"):
    """Build a minimal Brief for fixtures.

    Default: 10m × 12m plot, G+1, 2 bedrooms, ₹70-80L budget, Chennai.
    """
    plot = Plot(
        width_m=float(plot_width_m), depth_m=float(plot_depth_m),
        facing=PlotOrientation.NORTH, city=city,
        road_width_m=6.0,
        plot_type=PlotType.DETACHED,
    )
    user_sb = user_setbacks or Setbacks(1.5, 1.5, 1.0, 1.0)
    nbc_sb = nbc_setbacks or Setbacks(1.5, 1.5, 1.5, 1.5)

    floors = []
    for i in range(floors_count):
        rooms = ()
        if i == 0:
            rooms = (
                RoomRequirement(RoomType.BEDROOM_REGULAR,
                                count=bedroom_count),
                RoomRequirement(RoomType.BATHROOM_COMMON, count=1),
                RoomRequirement(RoomType.KITCHEN, count=1),
                RoomRequirement(RoomType.LIVING, count=1),
            )
        floors.append(FloorRequirement(
            floor_number=i,
            floor_use=FloorUse.RESIDENTIAL,
            rooms=rooms,
        ))

    return Brief(
        plot=plot,
        user_stated_setbacks=user_sb,
        nbc_compliant_setbacks=nbc_sb,
        floors=tuple(floors),
        budget_range=BudgetRange(min_lakhs=max(1, budget_max_lakhs - 10),
                                  max_lakhs=budget_max_lakhs),
    )


# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────

class TestEC001(unittest.TestCase):
    def test_ec001_fires_when_envelope_too_small(self):
        """Tiny plot, big brief → envelope can't hold the rooms."""
        brief = _make_brief(plot_width_m=4, plot_depth_m=5,
                             bedroom_count=3, floors_count=1)
        gap = _make_gap_analysis()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(
            ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE, case_ids
        )

    def test_ec001_does_not_fire_when_envelope_sufficient(self):
        """Big plot, small brief → no EC-001."""
        brief = _make_brief(plot_width_m=15, plot_depth_m=20,
                             bedroom_count=2, floors_count=2)
        gap = _make_gap_analysis()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertNotIn(
            ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE, case_ids
        )


class TestEC002(unittest.TestCase):
    def test_ec002_fires_at_severe_tier_2bhk(self):
        """4.27m ≈ 14 ft → severe tier for 2BHK."""
        brief = _make_brief(plot_width_m=4.27, plot_depth_m=15,
                             bedroom_count=2)
        gap = _make_gap_analysis()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT, case_ids)

    def test_ec002_does_not_fire_at_physical_tier(self):
        """3.35m ≈ 11 ft → physical tier; HARD_FAIL handled upstream."""
        brief = _make_brief(plot_width_m=3.35, plot_depth_m=15,
                             bedroom_count=2)
        gap = _make_gap_analysis()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertNotIn(
            ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT, case_ids
        )

    def test_ec002_does_not_fire_at_comfortable_tier(self):
        """6.0m → comfortable for 2BHK (>= 5.5m)."""
        brief = _make_brief(plot_width_m=6, plot_depth_m=15,
                             bedroom_count=2)
        gap = _make_gap_analysis()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertNotIn(
            ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT, case_ids
        )


class TestEC003(unittest.TestCase):
    def test_ec003_fires_when_parking_check_blocking(self):
        gap = _make_gap_analysis(blocking=(
            _make_check("parking_width_feasibility",
                        category=CheckCategory.USABILITY),
        ))
        brief = _make_brief()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(ExtremeCaseId.EC_003_NO_PARKING_POSITION, case_ids)


class TestEC004(unittest.TestCase):
    def test_ec004_fires_when_far_blocking(self):
        gap = _make_gap_analysis(blocking=(
            _make_check("far_compliance", details={
                "actual_far": 2.5, "city_max_far": 2.0,
                "total_built_area_sqm": 250, "plot_area_sqm": 100,
            }),
        ))
        brief = _make_brief()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(ExtremeCaseId.EC_004_FAR_EXCEEDED, case_ids)


class TestEC005(unittest.TestCase):
    def test_ec005_fires_when_coverage_blocking(self):
        gap = _make_gap_analysis(blocking=(
            _make_check("ground_coverage_compliance", details={
                "actual_gc_pct": 75, "city_max_gc_pct": 65,
            }),
        ))
        brief = _make_brief()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(
            ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED, case_ids
        )


class TestEC006(unittest.TestCase):
    def test_ec006_fires_when_user_setbacks_below_nbc(self):
        """User wants tiny setbacks; envelope below min buildable."""
        user_sb = Setbacks(0.5, 0.5, 0.5, 0.5)
        nbc_sb = Setbacks(1.5, 1.5, 1.5, 1.5)
        brief = _make_brief(plot_width_m=5, plot_depth_m=6,
                             user_setbacks=user_sb, nbc_setbacks=nbc_sb,
                             bedroom_count=3, floors_count=1)
        gap = _make_gap_analysis()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(
            ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
            case_ids,
        )

    def test_ec006_does_not_fire_when_user_setbacks_equal_nbc(self):
        """If user followed code, EC-001 covers; EC-006 dedups."""
        sb = Setbacks(1.5, 1.5, 1.5, 1.5)
        brief = _make_brief(plot_width_m=4, plot_depth_m=5,
                             user_setbacks=sb, nbc_setbacks=sb,
                             bedroom_count=3, floors_count=1)
        gap = _make_gap_analysis()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertNotIn(
            ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
            case_ids,
        )


class TestEC007(unittest.TestCase):
    def test_ec007_fires_when_stilt_mandate_blocking(self):
        gap = _make_gap_analysis(blocking=(
            _make_check("stilt_mandate_compliance", details={
                "estimated_height_m": 16.0, "stilt_threshold_m": 15.0,
            }),
        ))
        brief = _make_brief(city="mumbai")
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED, case_ids)


class TestEC008(unittest.TestCase):
    def test_ec008_fires_when_cost_exceeds_budget_1_5x(self):
        """80L * 1.5 = 120L; 150L > 120L → EC-008 fires."""
        cost = CostEstimate(
            exact_value=15_000_000,  # 150L
            range_min=12_000_000, range_max=18_000_000,
            confidence="HIGH", source="C7",
        )
        gap = _make_gap_analysis(cost_estimate=cost)
        brief = _make_brief(budget_max_lakhs=80)
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(
            ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW, case_ids
        )

    def test_ec008_does_not_fire_at_1_25x_tier(self):
        """1.25x is C2's job, not detector's. 100L <= 80L*1.5=120L."""
        cost = CostEstimate(
            exact_value=10_000_000,  # 100L
            range_min=9_000_000, range_max=11_000_000,
            confidence="HIGH", source="C7",
        )
        gap = _make_gap_analysis(cost_estimate=cost)
        brief = _make_brief(budget_max_lakhs=80)
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertNotIn(
            ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW, case_ids
        )


class TestEC009(unittest.TestCase):
    def test_ec009_fires_when_pile_pushes_over_budget(self):
        """80L base + 15L pile = 95L > 75L * 1.2 = 90L → fires."""
        soil_check = _make_check(
            "soil_type", category=CheckCategory.STRUCTURAL,
            severity=CheckSeverity.SOFT_WARN,
            details={
                "requires_pile": True,
                "pile_cost_inr": 1_500_000,  # 15L
                "soil_class": "soft clay",
            },
        )
        cost = CostEstimate(
            exact_value=8_000_000,  # 80L
            range_min=7_000_000, range_max=9_000_000,
            confidence="HIGH", source="C7",
        )
        practical = _make_report(soft=(soil_check,), cost_estimate=cost)
        code_strict = _make_report(cost_estimate=cost)
        gap = DesignGapAnalysis(
            practical_report=practical,
            code_strict_report=code_strict,
            gaps=(), cost_delta_lakhs=0.0,
            user_decisions_required=(),
        )
        brief = _make_brief(budget_max_lakhs=75)
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(
            ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW, case_ids
        )


class TestEC010(unittest.TestCase):
    def test_ec010_fires_for_water_course_low_probability(self):
        gap = _make_gap_analysis(blocking=(
            _make_check("water_course_clearance",
                        category=CheckCategory.COMPLIANCE),
        ))
        brief = _make_brief()
        cases = ExtremeCaseDetector.detect(gap, brief)
        ec010_cases = [c for c in cases
                        if c.case_id == ExtremeCaseId.EC_010_APPROVAL_BLOCKER]
        self.assertEqual(len(ec010_cases), 1)
        self.assertEqual(ec010_cases[0].resolution_probability,
                          ResolutionProbability.LOW)

    def test_ec010_classifies_ht_line_as_low(self):
        gap = _make_gap_analysis(blocking=(
            _make_check("electric_line_clearance",
                        category=CheckCategory.SAFETY,
                        details={"line_type": "HT"}),
        ))
        brief = _make_brief()
        cases = ExtremeCaseDetector.detect(gap, brief)
        ec010 = [c for c in cases
                 if c.case_id == ExtremeCaseId.EC_010_APPROVAL_BLOCKER][0]
        self.assertEqual(ec010.resolution_probability,
                          ResolutionProbability.LOW)


class TestEdgeCases(unittest.TestCase):
    def test_no_blockers_returns_empty_tuple(self):
        """On a comfortable plot with no C2 blockers, expect 0 ECs."""
        gap = _make_gap_analysis()
        brief = _make_brief(plot_width_m=15, plot_depth_m=20)
        cases = ExtremeCaseDetector.detect(gap, brief)
        self.assertEqual(len(cases), 0)

    def test_ec010_does_not_fire_for_far_blocker(self):
        """FAR is EC-004, NOT EC-010. Verify dedup."""
        gap = _make_gap_analysis(blocking=(
            _make_check("far_compliance", details={
                "actual_far": 2.5, "city_max_far": 2.0,
                "total_built_area_sqm": 250, "plot_area_sqm": 100,
            }),
        ))
        brief = _make_brief()
        cases = ExtremeCaseDetector.detect(gap, brief)
        case_ids = [c.case_id for c in cases]
        self.assertIn(ExtremeCaseId.EC_004_FAR_EXCEEDED, case_ids)
        self.assertNotIn(
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER, case_ids
        )


if __name__ == "__main__":
    unittest.main()
