"""Tests for Component 3a Session 3 (Option generation).

Per SPEC v0.2.1a Section 2.2 — verifies that OptionGenerator.generate_options
produces correctly-shaped real options for each of the 10 ExtremeCases,
replacing S2's placeholder pair.

Reuses fixture helpers from S2's test file (replicated at top of this
file per Q9 — test isolation, not import).
"""
import unittest
from typing import Optional

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
    ExtremeCase, ExtremeCaseId, ExtremeCaseCategory,
    ResolutionOption, ResolutionProbability,
    CostConfidence,
)
from buildemup.components.c03a.option_generator import OptionGenerator
from buildemup.components.c03a.detector import _make_placeholder_options


# ──────────────────────────────────────────────────────────────────────
# Helpers (replicated from S2 test file per Q9 — isolation)
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


def _make_gap_analysis(blocking=(), soft=(), passed=(), cost_estimate=None):
    """Build a minimal DesignGapAnalysis for fixtures."""
    practical = _make_report(blocking=blocking, soft=soft, passed=passed,
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
                 city="chennai",
                 include_balcony=False):
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
            base_rooms = [
                RoomRequirement(RoomType.BEDROOM_REGULAR,
                                count=bedroom_count),
                RoomRequirement(RoomType.BATHROOM_COMMON, count=1),
                RoomRequirement(RoomType.KITCHEN, count=1),
                RoomRequirement(RoomType.LIVING, count=1),
            ]
            if include_balcony:
                base_rooms.append(
                    RoomRequirement(RoomType.BALCONY, count=1)
                )
            rooms = tuple(base_rooms)
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


# Per-EC category mapping (used by all-EC subTest)
_EC_TO_CATEGORY = {
    ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE: ExtremeCaseCategory.SPATIAL,
    ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT: ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_003_NO_PARKING_POSITION: ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_004_FAR_EXCEEDED: ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED: ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE: ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED: ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW: ExtremeCaseCategory.BUDGET,
    ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW: ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_010_APPROVAL_BLOCKER: ExtremeCaseCategory.APPROVAL,
}


def _make_extreme_case(
    case_id: ExtremeCaseId = ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
    category: Optional[ExtremeCaseCategory] = None,
    blocking_gap_ids: tuple[str, ...] = (),
    user_facing_message: str = "test message",
    framing_line: str = "test framing line",
    resolution_probability: ResolutionProbability = ResolutionProbability.NOT_APPLICABLE,
    options: Optional[tuple[ResolutionOption, ...]] = None,
) -> ExtremeCase:
    """Build a minimal ExtremeCase fixture with placeholder options.

    Mirrors the placeholder pattern S2's detector uses. S3's
    generate_options() produces a NEW tuple of real options; we don't
    mutate the input.
    """
    if options is None:
        options = _make_placeholder_options()
    if category is None:
        category = _EC_TO_CATEGORY.get(case_id, ExtremeCaseCategory.SPATIAL)
    return ExtremeCase(
        case_id=case_id, category=category,
        blocking_gap_ids=blocking_gap_ids,
        user_facing_message=user_facing_message,
        framing_line=framing_line,
        resolution_probability=resolution_probability,
        options=options,
        detected_at_iteration=0,
    )


def _make_cost_estimate(exact_inr: float = 15_000_000.0) -> CostEstimate:
    """Build a CostEstimate for EC-008 / EC-009 fixtures."""
    return CostEstimate(
        exact_value=exact_inr,
        range_min=exact_inr * 0.85,
        range_max=exact_inr * 1.15,
        confidence="HIGH", source="C7 cost engine",
    )


# ──────────────────────────────────────────────────────────────────────
# Tests — option counts (one per EC + EC-010 LOW variant)
# ──────────────────────────────────────────────────────────────────────

class TestEachECProducesOptions(unittest.TestCase):
    """One test per EC verifies option count + Preview Mode last."""

    def test_ec001_produces_six_options(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
        )
        brief = _make_brief(plot_width_m=4, plot_depth_m=5,
                             bedroom_count=3, floors_count=1)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        self.assertEqual(len(opts), 6)
        self.assertTrue(opts[-1].is_preview_mode)

    def test_ec002_produces_four_options(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
        )
        brief = _make_brief(plot_width_m=4.27, bedroom_count=2)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        self.assertEqual(len(opts), 4)
        self.assertTrue(opts[-1].is_preview_mode)

    def test_ec010_low_produces_three_options(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
            resolution_probability=ResolutionProbability.LOW,
        )
        opts = OptionGenerator.generate_options(
            case, _make_brief(), _make_gap_analysis(),
        )
        self.assertEqual(len(opts), 3)
        # For LOW, the first option (different plot) must be RECOMMENDED
        self.assertTrue(opts[0].recommended)
        self.assertIn("DIFFERENT_PLOT", opts[0].option_id)
        self.assertTrue(opts[-1].is_preview_mode)

    def test_ec010_medium_produces_four_options(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
            resolution_probability=ResolutionProbability.MEDIUM,
        )
        opts = OptionGenerator.generate_options(
            case, _make_brief(), _make_gap_analysis(),
        )
        self.assertEqual(len(opts), 4)
        self.assertTrue(opts[-1].is_preview_mode)


# ──────────────────────────────────────────────────────────────────────
# Tests — Preview Mode invariant
# ──────────────────────────────────────────────────────────────────────

class TestPreviewModeAlwaysLast(unittest.TestCase):
    def test_preview_mode_is_last_for_all_ecs(self):
        for case_id in ExtremeCaseId:
            with self.subTest(case_id=case_id):
                rp = (ResolutionProbability.MEDIUM
                      if case_id == ExtremeCaseId.EC_010_APPROVAL_BLOCKER
                      else ResolutionProbability.NOT_APPLICABLE)
                case = _make_extreme_case(
                    case_id=case_id, resolution_probability=rp,
                )
                brief = _make_brief(include_balcony=True)
                # EC-008 + EC-009 need cost_estimate
                if case_id == ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW:
                    gap = _make_gap_analysis(
                        cost_estimate=_make_cost_estimate(15_000_000),
                    )
                elif case_id == ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW:
                    soil = _make_check(
                        "soil_type", severity=CheckSeverity.SOFT_WARN,
                        category=CheckCategory.STRUCTURAL,
                        details={"requires_pile": True,
                                 "pile_cost_inr": 1_500_000,
                                 "soil_class": "soft clay"},
                    )
                    gap = _make_gap_analysis(
                        soft=(soil,),
                        cost_estimate=_make_cost_estimate(8_000_000),
                    )
                else:
                    gap = _make_gap_analysis()
                opts = OptionGenerator.generate_options(case, brief, gap)
                self.assertGreaterEqual(len(opts), 2)
                self.assertTrue(opts[-1].is_preview_mode,
                                f"{case_id}: preview not last")
                # Verify Preview Mode option has empty brief change
                self.assertEqual(opts[-1].requires_brief_change, ())


# ──────────────────────────────────────────────────────────────────────
# Tests — co-fire promotion (EC-002 ↔ EC-006)
# ──────────────────────────────────────────────────────────────────────

class TestCoFirePromotion(unittest.TestCase):
    def test_ec002_different_plot_promoted_when_ec006_co_fires(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
        )
        brief = _make_brief(plot_width_m=4.27, bedroom_count=2)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
            co_fired_case_ids=(
                ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
            ),
        )
        different_plot = next(
            o for o in opts if "DIFFERENT_PLOT" in o.option_id
        )
        self.assertTrue(different_plot.recommended)
        self.assertIsNotNone(different_plot.recommendation_reason)

    def test_ec002_different_plot_not_promoted_when_alone(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
        )
        brief = _make_brief(plot_width_m=4.27, bedroom_count=2)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        different_plot = next(
            o for o in opts if "DIFFERENT_PLOT" in o.option_id
        )
        self.assertFalse(different_plot.recommended)

    def test_ec006_different_plot_promoted_when_ec002_co_fires(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
        )
        brief = _make_brief()
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
            co_fired_case_ids=(
                ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
            ),
        )
        different_plot = next(
            o for o in opts if "DIFFERENT_PLOT" in o.option_id
        )
        self.assertTrue(different_plot.recommended)


# ──────────────────────────────────────────────────────────────────────
# Tests — special action handlers
# ──────────────────────────────────────────────────────────────────────

class TestCBAVerifyOption(unittest.TestCase):
    def test_ec006_includes_cba_verify_with_correct_action(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
        )
        opts = OptionGenerator.generate_options(
            case, _make_brief(city="chennai"), _make_gap_analysis(),
        )
        cba = next((o for o in opts if "CBA" in o.option_id), None)
        self.assertIsNotNone(cba, "EC-006 must include a CBA verify option")
        self.assertEqual(cba.requires_action, "EMAIL_CBA_CHECKLIST")
        self.assertEqual(cba.requires_brief_change, ())


class TestPauseForUserVerification(unittest.TestCase):
    def test_ec009_defer_via_soil_test_uses_pause_action(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW,
        )
        soil = _make_check(
            "soil_type", severity=CheckSeverity.SOFT_WARN,
            category=CheckCategory.STRUCTURAL,
            details={"requires_pile": True, "pile_cost_inr": 1_500_000,
                     "soil_class": "soft clay"},
        )
        gap = _make_gap_analysis(
            soft=(soil,),
            cost_estimate=_make_cost_estimate(8_000_000),
        )
        opts = OptionGenerator.generate_options(case, _make_brief(), gap)
        defer = next(
            o for o in opts if "DEFER_VIA_SOIL_TEST" in o.option_id
        )
        self.assertEqual(defer.requires_action,
                         "PAUSE_FOR_USER_VERIFICATION")
        self.assertEqual(defer.requires_brief_change, ())
        self.assertTrue(defer.recommended,
                        "Defer via soil test must be RECOMMENDED")


# ──────────────────────────────────────────────────────────────────────
# Tests — CostImpact structure (Transparency Triple)
# ──────────────────────────────────────────────────────────────────────

class TestCostImpactStructure(unittest.TestCase):
    def test_options_with_cost_impact_have_transparency_triple(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
        )
        brief = _make_brief(plot_width_m=4, plot_depth_m=5,
                             bedroom_count=3, floors_count=1)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        add_floor = next(
            o for o in opts if "ADD_FLOOR" in o.option_id
        )
        self.assertIsNotNone(add_floor.cost_impact)
        self.assertLessEqual(add_floor.cost_impact.low_inr,
                             add_floor.cost_impact.midpoint_inr)
        self.assertLessEqual(add_floor.cost_impact.midpoint_inr,
                             add_floor.cost_impact.high_inr)
        # Factory should auto-fill caveat + uncertainty for MEDIUM
        self.assertEqual(add_floor.cost_impact.confidence,
                         CostConfidence.MEDIUM)
        self.assertEqual(add_floor.cost_impact.uncertainty_pct, 25)


# ──────────────────────────────────────────────────────────────────────
# Tests — proceed-anyway absence in legal/regulatory ECs
# ──────────────────────────────────────────────────────────────────────

class TestNoProceedAnywayForLegalECs(unittest.TestCase):
    def _no_proceed_in(self, case_id, **kwargs):
        rp = kwargs.pop("resolution_probability",
                        ResolutionProbability.NOT_APPLICABLE)
        case = _make_extreme_case(case_id=case_id,
                                   resolution_probability=rp)
        brief = _make_brief(**kwargs)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        for o in opts:
            self.assertNotIn(
                "PROCEED_ANYWAY", o.option_id,
                f"{case_id} must not include a PROCEED_ANYWAY option "
                f"(legal/regulatory)",
            )

    def test_ec004_has_no_proceed_anyway(self):
        self._no_proceed_in(ExtremeCaseId.EC_004_FAR_EXCEEDED)

    def test_ec005_has_no_proceed_anyway(self):
        self._no_proceed_in(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)

    def test_ec006_has_no_proceed_anyway(self):
        self._no_proceed_in(
            ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
        )

    def test_ec007_has_no_proceed_anyway(self):
        self._no_proceed_in(ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED)

    def test_ec010_low_has_no_proceed_anyway(self):
        self._no_proceed_in(
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
            resolution_probability=ResolutionProbability.LOW,
        )

    def test_ec010_medium_has_no_proceed_anyway(self):
        self._no_proceed_in(
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
            resolution_probability=ResolutionProbability.MEDIUM,
        )


# ──────────────────────────────────────────────────────────────────────
# Tests — recommendation logic (thresholds)
# ──────────────────────────────────────────────────────────────────────

class TestRecommendationLogic(unittest.TestCase):
    def test_ec001_drop_room_option_targets_lowest_priority(self):
        """When a balcony exists, option A targets the balcony (lowest
        priority in the cut order, comes before bedroom/kitchen/living).
        """
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
        )
        brief = _make_brief(include_balcony=True)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        opt_a = next(o for o in opts
                     if "DROP_LOWEST_PRIORITY_ROOM" in o.option_id)
        # Balcony is the lowest-priority cuttable room in our priority list
        self.assertIn("balcony", opt_a.description.lower())
        bc = opt_a.requires_brief_change[0]
        self.assertIn("balcony", bc.field_path)
        self.assertEqual(bc.operation, "INCREMENT")
        self.assertEqual(bc.new_value, -1)

    def test_ec008_phase_construction_recommended_when_gap_50_to_65(self):
        """Phase construction is RECOMMENDED when budget gap is 50-65%."""
        # budget = 80L = 8_000_000 INR
        # estimate = 12_400_000 → gap = 55%
        brief = _make_brief(budget_max_lakhs=80)
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW,
        )
        gap = _make_gap_analysis(
            cost_estimate=_make_cost_estimate(12_400_000),
        )
        opts = OptionGenerator.generate_options(case, brief, gap)
        phase = next(o for o in opts
                     if "PHASE_CONSTRUCTION" in o.option_id)
        self.assertTrue(phase.recommended)
        self.assertIsNotNone(phase.recommendation_reason)

    def test_ec008_phase_construction_not_recommended_when_gap_too_high(self):
        """Phase construction NOT recommended when gap > 65%."""
        # budget = 80L → estimate = 16_000_000 → gap = 100%
        brief = _make_brief(budget_max_lakhs=80)
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW,
        )
        gap = _make_gap_analysis(
            cost_estimate=_make_cost_estimate(16_000_000),
        )
        opts = OptionGenerator.generate_options(case, brief, gap)
        phase = next(o for o in opts
                     if "PHASE_CONSTRUCTION" in o.option_id)
        self.assertFalse(phase.recommended)

    def test_ec003_metro_recommends_stilt(self):
        """In metro cities, stilt parking is RECOMMENDED (not dropping)."""
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_003_NO_PARKING_POSITION,
        )
        brief = _make_brief(city="mumbai")
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        stilt = next(o for o in opts if "STILT_PARKING" in o.option_id)
        drop = next(
            o for o in opts if "DROP_COVERED_PARKING" in o.option_id
        )
        self.assertTrue(stilt.recommended,
                        "Mumbai (metro) should recommend stilt parking")
        self.assertFalse(drop.recommended,
                         "Mumbai (metro) should NOT recommend dropping "
                         "covered parking")

    def test_ec003_tier2_recommends_dropping_covered(self):
        """In tier-2/3 cities, dropping covered parking is RECOMMENDED."""
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_003_NO_PARKING_POSITION,
        )
        brief = _make_brief(city="chennai")
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        stilt = next(o for o in opts if "STILT_PARKING" in o.option_id)
        drop = next(
            o for o in opts if "DROP_COVERED_PARKING" in o.option_id
        )
        self.assertTrue(drop.recommended,
                        "Chennai (tier-2) should recommend dropping "
                        "covered parking")
        self.assertFalse(stilt.recommended,
                         "Chennai (tier-2) should NOT recommend stilt")


# ──────────────────────────────────────────────────────────────────────
# Tests — BriefChange operation enum compliance
# ──────────────────────────────────────────────────────────────────────

class TestBriefChangeOperations(unittest.TestCase):
    """Verify all generated BriefChanges use only the S1 _ALLOWED_OPS:
    {DELETE, SET, INCREMENT}. 'DECREMENT' is forbidden — Q2.
    """
    _ALLOWED = ("DELETE", "SET", "INCREMENT")

    def test_all_brief_changes_use_allowed_operations(self):
        """Iterate over every EC + every option + every brief change."""
        for case_id in ExtremeCaseId:
            with self.subTest(case_id=case_id):
                rp = (ResolutionProbability.MEDIUM
                      if case_id == ExtremeCaseId.EC_010_APPROVAL_BLOCKER
                      else ResolutionProbability.NOT_APPLICABLE)
                case = _make_extreme_case(
                    case_id=case_id, resolution_probability=rp,
                )
                brief = _make_brief(include_balcony=True)
                if case_id == ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW:
                    gap = _make_gap_analysis(
                        cost_estimate=_make_cost_estimate(15_000_000),
                    )
                elif case_id == ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW:
                    soil = _make_check(
                        "soil_type", severity=CheckSeverity.SOFT_WARN,
                        category=CheckCategory.STRUCTURAL,
                        details={"requires_pile": True,
                                 "pile_cost_inr": 1_500_000,
                                 "soil_class": "soft clay"},
                    )
                    gap = _make_gap_analysis(
                        soft=(soil,),
                        cost_estimate=_make_cost_estimate(8_000_000),
                    )
                else:
                    gap = _make_gap_analysis()
                opts = OptionGenerator.generate_options(case, brief, gap)
                for opt in opts:
                    for bc in opt.requires_brief_change:
                        self.assertIn(
                            bc.operation, self._ALLOWED,
                            f"{case_id} {opt.option_id}: operation "
                            f"{bc.operation!r} not in S1 _ALLOWED_OPS",
                        )


# ──────────────────────────────────────────────────────────────────────
# Tests — dispatch invariant
# ──────────────────────────────────────────────────────────────────────

class TestDispatchCoverage(unittest.TestCase):
    def test_every_extreme_case_id_has_a_builder(self):
        """OptionGenerator must dispatch every ExtremeCaseId to a
        builder — no silent fallthrough.
        """
        for case_id in ExtremeCaseId:
            with self.subTest(case_id=case_id):
                rp = (ResolutionProbability.MEDIUM
                      if case_id == ExtremeCaseId.EC_010_APPROVAL_BLOCKER
                      else ResolutionProbability.NOT_APPLICABLE)
                case = _make_extreme_case(
                    case_id=case_id, resolution_probability=rp,
                )
                brief = _make_brief()
                if case_id == ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW:
                    gap = _make_gap_analysis(
                        cost_estimate=_make_cost_estimate(15_000_000),
                    )
                elif case_id == ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW:
                    soil = _make_check(
                        "soil_type", severity=CheckSeverity.SOFT_WARN,
                        category=CheckCategory.STRUCTURAL,
                        details={"requires_pile": True,
                                 "pile_cost_inr": 1_500_000,
                                 "soil_class": "soft clay"},
                    )
                    gap = _make_gap_analysis(
                        soft=(soil,),
                        cost_estimate=_make_cost_estimate(8_000_000),
                    )
                else:
                    gap = _make_gap_analysis()
                opts = OptionGenerator.generate_options(case, brief, gap)
                self.assertGreaterEqual(len(opts), 2,
                                        f"{case_id}: < 2 options")


# ──────────────────────────────────────────────────────────────────────
# Tests — precondition guards (Drawback #3b: don't emit BriefChanges
# that would push the brief below MIN_BEDROOMS / MIN_FLOORS)
# ──────────────────────────────────────────────────────────────────────

class TestPreconditionGuards(unittest.TestCase):
    """When dropping a bedroom/floor would violate domain minima, the
    affected option must be emitted as informational only — empty
    requires_brief_change, recommended=False, advisory explaining why.
    Option count stays stable (spec invariants).
    """

    # EC-001 op B (Reduce room count) — guarded on bhk
    def test_ec001_opt_b_at_1bhk_is_informational(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
        )
        brief = _make_brief(bedroom_count=1)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        self.assertEqual(len(opts), 6, "Option count must stay 6")
        opt_b = next(o for o in opts if "REDUCE_ROOM_COUNT" in o.option_id)
        self.assertEqual(opt_b.requires_brief_change, ())
        self.assertFalse(opt_b.recommended)
        self.assertIsNotNone(opt_b.risk_advisory)
        self.assertIn("1BHK", opt_b.risk_advisory)

    def test_ec001_opt_b_at_2bhk_remains_actionable(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
        )
        brief = _make_brief(bedroom_count=2)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        opt_b = next(o for o in opts if "REDUCE_ROOM_COUNT" in o.option_id)
        # 2BHK → option B should carry a real BriefChange
        self.assertEqual(len(opt_b.requires_brief_change), 1)
        self.assertEqual(opt_b.requires_brief_change[0].operation,
                         "INCREMENT")
        self.assertEqual(opt_b.requires_brief_change[0].new_value, -1)

    # EC-002 op A (Reduce BHK) — guarded on bhk
    def test_ec002_opt_a_at_1bhk_is_informational(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
        )
        brief = _make_brief(bedroom_count=1, plot_width_m=4.27)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        self.assertEqual(len(opts), 4, "Option count must stay 4")
        opt_a = next(o for o in opts if "REDUCE_BHK" in o.option_id)
        self.assertEqual(opt_a.requires_brief_change, ())
        self.assertFalse(opt_a.recommended)
        self.assertIsNotNone(opt_a.risk_advisory)
        self.assertIn("1BHK", opt_a.risk_advisory)
        # Description must NOT contain "from 1BHK to 1BHK" (nonsense)
        self.assertNotIn("1BHK to 1BHK", opt_a.description)

    # EC-007 op B (Reduce floor count) — guarded on floor count
    def test_ec007_opt_b_at_single_floor_is_informational(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED,
        )
        brief = _make_brief(floors_count=1)
        opts = OptionGenerator.generate_options(
            case, brief, _make_gap_analysis(),
        )
        self.assertEqual(len(opts), 3, "Option count must stay 3")
        opt_b = next(
            o for o in opts if "REDUCE_FLOOR_COUNT" in o.option_id
        )
        self.assertEqual(opt_b.requires_brief_change, ())
        self.assertEqual(opt_b.space_impact_sqft, 0)
        self.assertIsNotNone(opt_b.risk_advisory)

    # EC-008 op B (chained reduce-scope) — bedroom decrement guarded
    def test_ec008_opt_b_at_1bhk_drops_bedroom_change_keeps_balcony(self):
        case = _make_extreme_case(
            case_id=ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW,
        )
        brief = _make_brief(bedroom_count=1, include_balcony=True)
        gap = _make_gap_analysis(
            cost_estimate=_make_cost_estimate(15_000_000),
        )
        opts = OptionGenerator.generate_options(case, brief, gap)
        opt_b = next(
            o for o in opts if "REDUCE_SCOPE_DRAMATICALLY" in o.option_id
        )
        # No bedroom decrement; balcony decrement should still be present
        bedroom_changes = [
            bc for bc in opt_b.requires_brief_change
            if "bedroom" in bc.field_path.lower()
        ]
        self.assertEqual(len(bedroom_changes), 0,
                         "1BHK brief must not produce a bedroom decrement")
        balcony_changes = [
            bc for bc in opt_b.requires_brief_change
            if "balcony" in bc.field_path.lower()
        ]
        self.assertEqual(len(balcony_changes), 1,
                         "Balcony decrement must remain")
        self.assertIsNotNone(opt_b.risk_advisory)
        self.assertIn("1BHK", opt_b.risk_advisory)


# ═════════════════════════════════════════════════════════════════════════
# B-027 P5 — Structural presence test for is_different_plot_option
# ═════════════════════════════════════════════════════════════════════════
#
# Replaces v0.2's two string-matching invariants. This test never inspects
# option_id strings; it counts options by the structural flag and verifies
# against S3's documented contract per EC.
#
# CONTRACT (derived from code review during B-027 build, NOT from the
# pre-build spec which was wrong on this list):
#   ECs that emit exactly 1 different-plot option:
#     EC_002, EC_003, EC_006, EC_009, EC_010
#   ECs that emit 0 different-plot options:
#     EC_001, EC_004, EC_005, EC_007, EC_008
#
# The spec originally listed EC_004/005/007 as having different-plot
# options based on parent-spec assumptions; actual S3 source emits them
# only for EC_002/003/006/009/010. Spec → reality mismatch caught during
# B-027 build; contract here is the source of truth.

_ECS_WITH_DIFFERENT_PLOT_OPTION = frozenset({
    ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
    ExtremeCaseId.EC_003_NO_PARKING_POSITION,
    ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
    ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW,
    ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
})


def _generate_options_for_ec_via_s3(
    ec_id: ExtremeCaseId,
) -> tuple[ResolutionOption, ...]:
    """Drive each EC's S3 builder via a realistic fixture brief.

    Returns the option set S3 emits for the given EC. Used by the
    structural presence test to verify the is_different_plot_option
    contract.
    """
    case = _make_extreme_case(
        case_id=ec_id,
        # EC_010 needs a probability; LOW so it exercises the path that
        # emits the different-plot option (Option A in the LOW branch).
        resolution_probability=(
            ResolutionProbability.LOW
            if ec_id == ExtremeCaseId.EC_010_APPROVAL_BLOCKER
            else ResolutionProbability.NOT_APPLICABLE
        ),
    )
    # EC-specific brief tuning where defaults wouldn't trigger the right
    # builder branches. Most builders are tolerant; defaults work.
    if ec_id == ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT:
        brief = _make_brief(plot_width_m=4.27, bedroom_count=2)
    elif ec_id == ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE:
        brief = _make_brief(plot_width_m=4, plot_depth_m=5,
                             bedroom_count=3, floors_count=1)
    else:
        brief = _make_brief()
    return OptionGenerator.generate_options(
        case, brief, _make_gap_analysis(),
    )


class TestB027DifferentPlotOptionPresence(unittest.TestCase):
    """B-027 P5: structural invariant for is_different_plot_option.

    Counts options by the structural flag; never inspects option_id
    strings.
    """

    def test_different_plot_option_presence_per_ec(self):
        """Asserts S3's contract per EC.

        ECs in _ECS_WITH_DIFFERENT_PLOT_OPTION emit exactly 1 option
        with is_different_plot_option=True. All other ECs emit 0.

        Catches three failure modes:
          - S3 builder forgets to emit a different-plot option that
            should exist (count=0, expected=1)
          - S3 builder accidentally emits two (count=2, expected=1)
          - S3 builder accidentally emits a different-plot option in an
            EC that shouldn't have one (count=1, expected=0)
        """
        all_ec_ids = [
            ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
            ExtremeCaseId.EC_003_NO_PARKING_POSITION,
            ExtremeCaseId.EC_004_FAR_EXCEEDED,
            ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED,
            ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
            ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED,
            ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW,
            ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW,
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
        ]
        for ec_id in all_ec_ids:
            options = _generate_options_for_ec_via_s3(ec_id)
            count = sum(
                1 for o in options if o.is_different_plot_option
            )
            if ec_id in _ECS_WITH_DIFFERENT_PLOT_OPTION:
                self.assertEqual(
                    count, 1,
                    f"S3 contract violated: {ec_id.value} should emit "
                    f"exactly 1 different-plot option "
                    f"(is_different_plot_option=True); got {count}. "
                    f"Either the builder is missing a "
                    f"_build_different_plot_option call, or it's "
                    f"emitting multiple different-plot options.",
                )
            else:
                self.assertEqual(
                    count, 0,
                    f"S3 contract violated: {ec_id.value} should emit "
                    f"0 different-plot options; got {count}. The "
                    f"builder should not call "
                    f"_build_different_plot_option for this EC.",
                )


if __name__ == "__main__":
    unittest.main()
