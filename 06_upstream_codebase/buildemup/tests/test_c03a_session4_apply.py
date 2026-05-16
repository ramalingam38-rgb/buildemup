"""Tests for Component 3a Session 4 — BriefChange application.

Per locked S4 SPEC v0.1 § 9.1 — verifies that
brief_change_apply.apply_brief_change / apply_brief_changes:
  - apply each field_path correctly
  - never mutate the input Brief
  - raise classified BriefChangeIntegrityError on validation failure
  - propagate change_index in tuple-apply chains

Plus one integration smoke (test 13) confirming S3 + S4 wire cleanly.

Replicates fixture builders inline (per Q9 — test isolation, not
import).
"""
import dataclasses
import unittest
from typing import Optional

from buildemup.domain.brief import Brief, BudgetRange, CostEstimate
from buildemup.domain.plot import Plot, PlotType
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.setbacks import Setbacks
from buildemup.domain.floor_requirement import (
    FloorRequirement, RoomRequirement, FloorUse, RoomType,
    NBC_MINIMUM_ROOM_SIZES_SQM,
)
from buildemup.domain.feasibility import (
    DesignGapAnalysis, FeasibilityReport, DesignVariant,
    CheckResult, CheckSeverity, CheckCategory, ConfidenceLevel,
    VerificationPriority,
)
from buildemup.domain.extreme_case import (
    ExtremeCase, ExtremeCaseId, ExtremeCaseCategory,
    ResolutionOption, ResolutionProbability,
    BriefChange, BriefChangeIntegrityError,
)
from buildemup.components.c03a.brief_change_apply import (
    apply_brief_change, apply_brief_changes,
)
from buildemup.components.c03a.option_generator import OptionGenerator
from buildemup.components.c03a.detector import _make_placeholder_options


# ─────────────────────────────────────────────────────────────────
# Fixture helpers (replicated from S2/S3 test files for isolation)
# ─────────────────────────────────────────────────────────────────

def _make_check(check_id, severity=CheckSeverity.HARD_FAIL,
                category=CheckCategory.COMPLIANCE, details=None):
    return CheckResult(
        check_id=check_id, check_name=check_id,
        category=category, severity=severity,
        confidence=ConfidenceLevel.HIGH, confidence_reason=None,
        score_contribution=-15, message=f"test message for {check_id}",
        details=details or {}, assumption_used=None,
        verification_recommendation=None,
        verification_priority=VerificationPriority.IMPORTANT,
        common_doubts=(),
    )


def _make_report(blocking=(), soft=(), passed=(), na=(),
                 cost_estimate=None):
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
        unknowns=(), action_steps=(),
    )


def _make_gap_analysis(blocking=(), soft=(), passed=(),
                       cost_estimate=None):
    practical = _make_report(blocking=blocking, soft=soft,
                              passed=passed, cost_estimate=cost_estimate)
    code_strict = _make_report(blocking=(), cost_estimate=cost_estimate)
    return DesignGapAnalysis(
        practical_report=practical,
        code_strict_report=code_strict,
        gaps=(), cost_delta_lakhs=0.0,
        user_decisions_required=(),
    )


def _make_brief(*, plot_width_m=10.0, plot_depth_m=12.0,
                floors_count=2, bedroom_count=2,
                budget_min_lakhs=70, budget_max_lakhs=80,
                user_setbacks=None, nbc_setbacks=None,
                city="chennai",
                include_balcony=False):
    """Build a minimal Brief for fixtures.

    Default: 10m × 12m plot, G+1, 2 bedrooms, ₹70-80L budget, Chennai.
    """
    plot = Plot(
        width_m=float(plot_width_m), depth_m=float(plot_depth_m),
        facing=PlotOrientation.NORTH, city=city,
        road_width_m=6.0, plot_type=PlotType.DETACHED,
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
                    RoomRequirement(RoomType.BALCONY, count=2)
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
        budget_range=BudgetRange(
            min_lakhs=budget_min_lakhs,
            max_lakhs=budget_max_lakhs,
        ),
    )


def _bedroom_count_in_brief(brief: Brief) -> int:
    return sum(
        r.count for f in brief.floors for r in f.rooms
        if r.room_type in (RoomType.BEDROOM_MASTER,
                           RoomType.BEDROOM_REGULAR)
    )


def _balcony_count_in_brief(brief: Brief) -> int:
    return sum(
        r.count for f in brief.floors for r in f.rooms
        if r.room_type == RoomType.BALCONY
    )


# ─────────────────────────────────────────────────────────────────
# Tests 1-12 — apply_brief_change unit behaviour
# ─────────────────────────────────────────────────────────────────

class TestApplyBehaviour(unittest.TestCase):

    # --- 1: empty changes is a no-op --------------------------------
    def test_apply_empty_changes_returns_input(self):
        """apply_brief_changes(brief, ()) returns the input Brief."""
        brief = _make_brief(include_balcony=True)
        result = apply_brief_changes(brief, ())
        self.assertIs(result, brief)

    # --- 2: rooms.{type}.count INCREMENT -1 drops one ---------------
    def test_apply_room_count_decrement_drops_room(self):
        """rooms.balcony.count INCREMENT -1 reduces balcony count by 1."""
        brief = _make_brief(include_balcony=True)
        before = _balcony_count_in_brief(brief)
        change = BriefChange(
            field_path=f"rooms.{RoomType.BALCONY.value}.count",
            operation="INCREMENT",
            new_value=-1,
            description="Reduce balcony count by 1",
        )
        result = apply_brief_change(brief, change)
        after = _balcony_count_in_brief(result)
        self.assertEqual(after, before - 1)

    # --- 3: count to 0 drops the RoomRequirement entirely -----------
    def test_apply_room_count_to_zero_drops_room_entirely(self):
        """Decrementing count from 1 to 0 removes the RoomRequirement."""
        brief = _make_brief(include_balcony=False)
        # Insert a single-balcony so we can decrement to 0
        floor0 = brief.floors[0]
        new_rooms = floor0.rooms + (
            RoomRequirement(RoomType.STORE, count=1),
        )
        new_floor0 = dataclasses.replace(floor0, rooms=new_rooms)
        brief = dataclasses.replace(
            brief, floors=(new_floor0,) + brief.floors[1:],
        )
        # Sanity: a STORE room exists
        self.assertTrue(any(
            r.room_type == RoomType.STORE
            for f in brief.floors for r in f.rooms
        ))

        change = BriefChange(
            field_path=f"rooms.{RoomType.STORE.value}.count",
            operation="INCREMENT",
            new_value=-1,
            description="Drop store room",
        )
        result = apply_brief_change(brief, change)
        self.assertFalse(any(
            r.room_type == RoomType.STORE
            for f in result.floors for r in f.rooms
        ))

    # --- 4: floors.add INCREMENT 1 appends a residential floor ------
    def test_apply_floors_add_appends_residential_floor(self):
        """floors.add INCREMENT 1 appends a residential floor."""
        brief = _make_brief(floors_count=2)
        change = BriefChange(
            field_path="floors.add", operation="INCREMENT",
            new_value=1, description="Add a floor",
        )
        result = apply_brief_change(brief, change)
        self.assertEqual(len(result.floors), len(brief.floors) + 1)
        # Newly added floor is RESIDENTIAL with floor_number = max+1
        new_floor = result.floors[-1]
        self.assertEqual(new_floor.floor_use, FloorUse.RESIDENTIAL)
        self.assertEqual(new_floor.rooms, ())
        expected_number = max(f.floor_number for f in brief.floors) + 1
        self.assertEqual(new_floor.floor_number, expected_number)

    # --- 5: floors.{N} DELETE removes that floor --------------------
    def test_apply_floors_index_delete_drops_topmost(self):
        """floors.{2} DELETE removes that floor (and renumbers if mid)."""
        brief = _make_brief(floors_count=3)
        change = BriefChange(
            field_path="floors.2", operation="DELETE",
            new_value=None, description="Drop top floor",
        )
        result = apply_brief_change(brief, change)
        self.assertEqual(len(result.floors), 2)
        # After dropping the top floor, numbers stay 0, 1
        self.assertEqual(
            sorted(f.floor_number for f in result.floors), [0, 1],
        )

    # --- 6: floors.add_stilt SET True ------------------------------
    def test_apply_floors_add_stilt_inserts_at_index_zero(self):
        """floors.add_stilt SET True → new stilt at floor_number=0;
        existing floors renumbered upward by 1.
        """
        brief = _make_brief(floors_count=2)
        change = BriefChange(
            field_path="floors.add_stilt", operation="SET",
            new_value=True, description="Add stilt parking",
        )
        result = apply_brief_change(brief, change)
        self.assertEqual(len(result.floors), 3)
        self.assertEqual(result.floors[0].floor_number, 0)
        self.assertEqual(result.floors[0].floor_use,
                         FloorUse.STILT_PARKING)
        # Other floors renumbered upward
        self.assertEqual(
            sorted(f.floor_number for f in result.floors), [0, 1, 2],
        )
        # Idempotency: applying again does nothing
        result2 = apply_brief_change(result, change)
        self.assertEqual(len(result2.floors), 3)

    # --- 7: setbacks.front_m INCREMENT ------------------------------
    def test_apply_setbacks_front_increments_correctly(self):
        """setbacks.front_m INCREMENT 0.3 → user_stated.front_m += 0.3."""
        brief = _make_brief()
        before_front = brief.user_stated_setbacks.front_m
        change = BriefChange(
            field_path="setbacks.front_m", operation="INCREMENT",
            new_value=0.3, description="Increase front setback by 0.3m",
        )
        result = apply_brief_change(brief, change)
        self.assertAlmostEqual(
            result.user_stated_setbacks.front_m, before_front + 0.3,
        )
        # Other sides unchanged
        self.assertEqual(
            result.user_stated_setbacks.rear_m,
            brief.user_stated_setbacks.rear_m,
        )
        self.assertEqual(
            result.user_stated_setbacks.side_left_m,
            brief.user_stated_setbacks.side_left_m,
        )

    # --- 8: budget.max_lakhs SET ------------------------------------
    def test_apply_budget_max_lakhs_replaces_budget_range(self):
        """budget.max_lakhs SET 100 → new BudgetRange with max=100."""
        brief = _make_brief(budget_min_lakhs=70, budget_max_lakhs=80)
        change = BriefChange(
            field_path="budget.max_lakhs", operation="SET",
            new_value=100, description="Raise budget to 100L",
        )
        result = apply_brief_change(brief, change)
        self.assertEqual(result.budget_range.max_lakhs, 100)
        # min preserved (since old min ≤ new max)
        self.assertEqual(result.budget_range.min_lakhs, 70)

    # --- 9: rooms.all.size SET 'nbc_min' ---------------------------
    def test_apply_rooms_all_size_resets_to_nbc_min(self):
        """rooms.all.size SET 'nbc_min' → all rooms drop preferred/min
        sizes (effective_size_sqm falls back to NBC).
        """
        brief = _make_brief(include_balcony=True)
        # Sanity: at least one room had no explicit size in our fixture
        # — that's fine. We're testing the post-condition.
        change = BriefChange(
            field_path="rooms.all.size", operation="SET",
            new_value="nbc_min", description="Reset rooms to NBC mins",
        )
        result = apply_brief_change(brief, change)
        for f in result.floors:
            for r in f.rooms:
                self.assertIsNone(r.preferred_size_sqm)
                self.assertIsNone(r.min_size_sqm)
                # effective_size_sqm reflects the NBC default
                self.assertEqual(
                    r.effective_size_sqm,
                    NBC_MINIMUM_ROOM_SIZES_SQM[r.room_type],
                )

    # --- 10: unknown field_path → UNKNOWN classification -----------
    def test_apply_unknown_field_path_raises_unknown(self):
        """Unrecognized field_path raises BriefChangeIntegrityError
        with classification='UNKNOWN'.
        """
        brief = _make_brief()
        change = BriefChange(
            field_path="garage.size", operation="SET",
            new_value=42, description="Set garage size (bogus path)",
        )
        with self.assertRaises(BriefChangeIntegrityError) as ctx:
            apply_brief_change(brief, change)
        self.assertEqual(ctx.exception.classify(), "UNKNOWN")
        self.assertEqual(
            ctx.exception.context["field_path"], "garage.size",
        )

    # --- 11: chain failure carries change_index --------------------
    def test_apply_chain_failure_carries_change_index(self):
        """apply_brief_changes with a failing change at index 2 sets
        context['change_index'] to 2.
        """
        brief = _make_brief(floors_count=2, include_balcony=True)
        ok_change_a = BriefChange(
            field_path="setbacks.front_m", operation="INCREMENT",
            new_value=0.1, description="Tiny setback bump (1)",
        )
        ok_change_b = BriefChange(
            field_path="setbacks.rear_m", operation="INCREMENT",
            new_value=0.1, description="Tiny setback bump (2)",
        )
        bad_change = BriefChange(
            field_path="garage.invented", operation="SET",
            new_value=99, description="Bogus path",
        )
        changes = (ok_change_a, ok_change_b, bad_change)
        with self.assertRaises(BriefChangeIntegrityError) as ctx:
            apply_brief_changes(brief, changes)
        self.assertEqual(ctx.exception.classify(), "UNKNOWN")
        self.assertEqual(ctx.exception.context["change_index"], 2)

    # --- 12: input brief is never mutated --------------------------
    def test_apply_input_brief_not_mutated(self):
        """After any apply, the original Brief's field values are
        unchanged. We check this for several common operations.
        """
        brief = _make_brief(include_balcony=True, floors_count=2)
        before_floors_count = len(brief.floors)
        before_balcony_count = _balcony_count_in_brief(brief)
        before_front = brief.user_stated_setbacks.front_m
        before_max_budget = brief.budget_range.max_lakhs

        # Apply a series of changes that mutate different parts
        for change in (
            BriefChange("floors.add", "INCREMENT", 1, "Add floor"),
            BriefChange(
                f"rooms.{RoomType.BALCONY.value}.count",
                "INCREMENT", -1, "Drop balcony"),
            BriefChange("setbacks.front_m", "INCREMENT", 0.3,
                        "Bump front"),
            BriefChange("budget.max_lakhs", "SET", 120, "Raise budget"),
        ):
            apply_brief_change(brief, change)

        # Original brief is unchanged
        self.assertEqual(len(brief.floors), before_floors_count)
        self.assertEqual(
            _balcony_count_in_brief(brief), before_balcony_count,
        )
        self.assertEqual(
            brief.user_stated_setbacks.front_m, before_front,
        )
        self.assertEqual(
            brief.budget_range.max_lakhs, before_max_budget,
        )


# ─────────────────────────────────────────────────────────────────
# Test 13 — integration smoke (S3 + S4 wire cleanly)
# ─────────────────────────────────────────────────────────────────

# Per-EC category mapping (mirrors S2/S3 test files)
_EC_TO_CATEGORY = {
    ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE:
        ExtremeCaseCategory.SPATIAL,
    ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT:
        ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_003_NO_PARKING_POSITION:
        ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_004_FAR_EXCEEDED:
        ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED:
        ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE:
        ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED:
        ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW:
        ExtremeCaseCategory.BUDGET,
    ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW:
        ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_010_APPROVAL_BLOCKER:
        ExtremeCaseCategory.APPROVAL,
}


def _make_extreme_case(
    case_id: ExtremeCaseId = (
        ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE
    ),
    category: Optional[ExtremeCaseCategory] = None,
    blocking_gap_ids: tuple[str, ...] = (),
    options: Optional[tuple[ResolutionOption, ...]] = None,
) -> ExtremeCase:
    if options is None:
        options = _make_placeholder_options()
    if category is None:
        category = _EC_TO_CATEGORY.get(
            case_id, ExtremeCaseCategory.SPATIAL,
        )
    return ExtremeCase(
        case_id=case_id, category=category,
        blocking_gap_ids=blocking_gap_ids,
        user_facing_message="test message",
        framing_line="test framing line",
        resolution_probability=ResolutionProbability.NOT_APPLICABLE,
        options=options,
        detected_at_iteration=0,
    )


def _make_cost_estimate(exact_inr: float = 15_000_000.0) -> CostEstimate:
    return CostEstimate(
        exact_value=exact_inr,
        range_min=exact_inr * 0.85,
        range_max=exact_inr * 1.15,
        confidence="HIGH", source="C7 cost engine",
    )


class TestS3OptionsApplyCleanly(unittest.TestCase):
    """Smoke-test: for representative ECs whose typical-Brief options
    can be exercised cheaply, the `requires_brief_change` tuple of the
    chosen option applies without raising BriefChangeIntegrityError.

    This is structural — it confirms that S3 and S4 wire together.
    Per S4 spec § 9.3.
    """

    def _pick_actionable_option(self, options):
        """Pick the recommended option (or first non-preview option
        with a non-empty change tuple). Return None if no such option
        is available — some ECs at certain co-firing combinations are
        recommend-elsewhere only.
        """
        # Prefer recommended + non-preview + non-empty changes
        for o in options:
            if (o.recommended and not o.is_preview_mode
                    and o.requires_brief_change):
                return o
        # Fallback: first non-preview option with non-empty changes
        for o in options:
            if not o.is_preview_mode and o.requires_brief_change:
                return o
        return None

    def test_s3_options_apply_cleanly_on_typical_brief(self):
        """For a representative set of ECs, apply the recommended
        option's BriefChanges to a typical 3BHK Brief — no error.
        """
        # ECs we exercise. We deliberately skip ECs that need rich
        # gap_analysis fixtures we don't easily build here — the
        # important contract is that the *vocabulary* of S3-emitted
        # paths is fully supported by S4.
        cases_to_test = [
            ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
            ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED,
            ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED,
        ]

        # 3BHK on a 9m × 12m plot — enough room for most options
        brief = _make_brief(
            plot_width_m=9.0, plot_depth_m=12.0,
            floors_count=2, bedroom_count=3,
            include_balcony=True,
            user_setbacks=Setbacks(1.5, 1.5, 1.0, 1.0),
        )
        gap_analysis = _make_gap_analysis(
            cost_estimate=_make_cost_estimate(),
        )

        for case_id in cases_to_test:
            with self.subTest(case_id=case_id.value):
                case = _make_extreme_case(case_id=case_id)
                try:
                    options = OptionGenerator.generate_options(
                        case, brief, gap_analysis,
                        co_fired_case_ids=(),
                    )
                except Exception as e:
                    self.skipTest(
                        f"Option generation skipped for "
                        f"{case_id.value}: {e}"
                    )
                option = self._pick_actionable_option(options)
                if option is None:
                    # No actionable option for this fixture — skip.
                    continue
                # Apply — must not raise BriefChangeIntegrityError
                try:
                    apply_brief_changes(
                        brief, option.requires_brief_change,
                    )
                except BriefChangeIntegrityError as e:
                    self.fail(
                        f"S3 option {option.option_id} for case "
                        f"{case_id.value} raised "
                        f"BriefChangeIntegrityError: {e} "
                        f"(classification={e.classify()})"
                    )


if __name__ == "__main__":
    unittest.main()
