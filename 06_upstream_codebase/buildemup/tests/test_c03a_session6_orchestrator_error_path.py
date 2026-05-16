"""Tests for Component 3a Session 6 — error paths.

Per locked S6 SPEC v1.0 § 7.3 — verifies:
  1. apply_brief_changes raising BriefChangeIntegrityError surfaces via
     state.last_error_message + last_error_option_id and grows
     failed_option_ids_for_current_case (P3).
  2. After error, the user picks a different option that succeeds —
     the error fields clear and the case advances.
  3. Invalid chosen_option_id (not in current case's options) raises
     ValueError before any apply attempt.
"""
from __future__ import annotations

import unittest
from typing import Optional
from unittest.mock import patch

from buildemup.components.c03a_extreme_case_gate import ExtremeCaseGate
from buildemup.domain.brief import Brief, BudgetRange
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.extreme_case import (
    BriefChange,
    ExtremeCase,
    ExtremeCaseCategory,
    ExtremeCaseId,
    ResolutionOption,
    ResolutionProbability,
)
from buildemup.domain.feasibility import (
    DesignGapAnalysis,
    DesignVariant,
    FeasibilityReport,
)
from buildemup.domain.floor_requirement import (
    FloorRequirement,
    FloorUse,
    RoomRequirement,
    RoomType,
)
from buildemup.domain.plot import Plot, PlotType
from buildemup.domain.setbacks import Setbacks


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

def _make_brief() -> Brief:
    plot = Plot(
        width_m=10.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=6.0, plot_type=PlotType.DETACHED,
    )
    floor = FloorRequirement(
        floor_number=0, floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(RoomType.BEDROOM_REGULAR, count=2),
               RoomRequirement(RoomType.KITCHEN, count=1),
               RoomRequirement(RoomType.LIVING, count=1),
               RoomRequirement(RoomType.BATHROOM_COMMON, count=1)),
    )
    return Brief(
        plot=plot,
        user_stated_setbacks=Setbacks(1.5, 1.5, 1.0, 1.0),
        nbc_compliant_setbacks=Setbacks(1.5, 1.5, 1.5, 1.5),
        floors=(floor,),
        budget_range=BudgetRange(min_lakhs=70, max_lakhs=80),
    )


def _make_gap_analysis() -> DesignGapAnalysis:
    rep = FeasibilityReport(
        variant=DesignVariant.PRACTICAL, overall_score=40,
        score_breakdown={}, blocking_issues=(),
        unaccepted_blocking_issues=(), soft_warnings=(),
        passed_checks=(), not_applicable_checks=(),
        cost_estimate=None, unknowns=(), action_steps=(),
    )
    return DesignGapAnalysis(
        practical_report=rep, code_strict_report=rep,
        gaps=(), cost_delta_lakhs=0.0, user_decisions_required=(),
    )


# A BriefChange that resolves to an unknown handler → triggers
# BriefChangeIntegrityError inside apply_brief_change. We use this to
# make the orchestrator's Branch C error path observable.
_BAD_CHANGE = BriefChange(
    field_path="this.path.does.not.exist",
    operation="SET",
    new_value=None,
    description="bad change for error path testing",
)


def _option(option_id: str, *,
            requires_brief_change=(),
            description: Optional[str] = None) -> ResolutionOption:
    return ResolutionOption(
        option_id=option_id,
        description=description or f"description for {option_id}",
        impact_summary="impact summary",
        cost_impact=None, space_impact_sqft=10,
        recommended=False, recommendation_reason=None,
        requires_brief_change=requires_brief_change,
        requires_action=None, risk_advisory=None,
        is_preview_mode=False, is_different_plot_option=False,
    )


def _case(case_id: ExtremeCaseId,
          *,
          options: tuple[ResolutionOption, ...]) -> ExtremeCase:
    return ExtremeCase(
        case_id=case_id, category=ExtremeCaseCategory.LEGAL,
        blocking_gap_ids=("GAP_1",),
        user_facing_message=f"message for {case_id.value}",
        framing_line="trade-offs are necessary",
        resolution_probability=ResolutionProbability.NOT_APPLICABLE,
        options=options, detected_at_iteration=0,
    )


def _make_runner(gap: DesignGapAnalysis):
    calls = []

    def runner(brief, fi):
        calls.append((brief, fi))
        return gap

    return runner, calls


class _DetectorPatch:
    _D = "buildemup.components.c03a_extreme_case_gate.ExtremeCaseDetector.detect"
    _O = "buildemup.components.c03a_extreme_case_gate.OptionGenerator.generate_options"

    def __init__(self, returns):
        self._returns = list(returns)
        self._dp = patch(self._D)
        self._op = patch(self._O)

    def __enter__(self):
        d = self._dp.start()
        o = self._op.start()
        d.side_effect = self._returns
        o.side_effect = lambda case, brief, gap, co: case.options
        return self

    def __exit__(self, *exc):
        self._dp.stop()
        self._op.stop()


# ─────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────

class TestApplyBriefChangeError(unittest.TestCase):
    """Test 1 — BriefChange validation error surfaces via state."""

    def test_apply_brief_change_error_surfaces_via_state(self):
        bad_opt = _option(
            "EC_004_OPT_BAD",
            requires_brief_change=(_BAD_CHANGE,),
        )
        good_opt = _option("EC_004_OPT_GOOD")
        case = _case(
            ExtremeCaseId.EC_004_FAR_EXCEEDED,
            options=(bad_opt, good_opt),
        )

        gap = _make_gap_analysis()
        runner, calls = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(case,)]):
            s0 = gate.start(session_id="sess-err", brief=_make_brief())
            s1 = gate.apply_user_decision(
                state=s0, case_id=case.case_id,
                chosen_option_id=bad_opt.option_id,
                user_acknowledged_at="2026-04-30T22:00:00Z",
            )

        # Not done — case still in queue, ready for retry
        self.assertFalse(s1.is_done)
        self.assertEqual(s1.remaining_cases, s0.remaining_cases)
        # Error surfaces in last_error_* fields (P3 + S4 formatter)
        self.assertIsNotNone(s1.last_error_message)
        self.assertEqual(s1.last_error_option_id, bad_opt.option_id)
        # P3: failed option_id added to the frozenset
        self.assertIn(
            bad_opt.option_id, s1.failed_option_ids_for_current_case,
        )
        self.assertIsInstance(
            s1.failed_option_ids_for_current_case, frozenset,
        )
        # No advance: iteration_count unchanged, no decision logged,
        # no extra C2 call beyond the start() one.
        self.assertEqual(s1.iteration_count, 0)
        self.assertEqual(len(s1.decisions_so_far), 0)
        self.assertEqual(len(calls), 1)


class TestRecoveryAfterError(unittest.TestCase):
    """Test 2 — after error, user picks a different option that succeeds."""

    def test_after_error_user_picks_different_option(self):
        bad_opt = _option(
            "EC_004_OPT_BAD",
            requires_brief_change=(_BAD_CHANGE,),
        )
        good_opt = _option("EC_004_OPT_GOOD")
        case_a = _case(
            ExtremeCaseId.EC_004_FAR_EXCEEDED,
            options=(bad_opt, good_opt),
        )
        # Next iteration: detector returns a different case
        case_b = _case(
            ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED,
            options=(_option("EC_005_OPT_X"), _option("EC_005_OPT_Y")),
        )

        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(case_a,), (case_b,)]):
            s = gate.start(session_id="sess-recover", brief=_make_brief())
            # First attempt: bad option fails
            s = gate.apply_user_decision(
                state=s, case_id=case_a.case_id,
                chosen_option_id=bad_opt.option_id,
                user_acknowledged_at="2026-04-30T22:00:00Z",
            )
            self.assertIsNotNone(s.last_error_message)
            self.assertIn(
                bad_opt.option_id, s.failed_option_ids_for_current_case,
            )

            # Second attempt: good option succeeds
            s = gate.apply_user_decision(
                state=s, case_id=case_a.case_id,
                chosen_option_id=good_opt.option_id,
                user_acknowledged_at="2026-04-30T22:30:00Z",
            )

        # Error fields cleared on advance
        self.assertIsNone(s.last_error_message)
        self.assertIsNone(s.last_error_option_id)
        # Failed set resets when case advances (Q7)
        self.assertEqual(s.failed_option_ids_for_current_case, frozenset())
        # We're now on case_b
        self.assertEqual(s.remaining_cases[0].case_id, case_b.case_id)
        self.assertEqual(s.iteration_count, 1)
        self.assertEqual(len(s.decisions_so_far), 1)
        self.assertEqual(
            s.decisions_so_far[0].chosen_option_id, good_opt.option_id,
        )


class TestInvalidChosenOption(unittest.TestCase):
    """Test 3 — chosen_option_id not in current case's options raises."""

    def test_invalid_chosen_option_id_raises(self):
        case = _case(
            ExtremeCaseId.EC_004_FAR_EXCEEDED,
            options=(_option("EC_004_OPT_A"), _option("EC_004_OPT_B")),
        )
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(case,)]):
            s = gate.start(session_id="sess-bad-id", brief=_make_brief())
        with self.assertRaises(ValueError) as ctx:
            gate.apply_user_decision(
                state=s, case_id=case.case_id,
                chosen_option_id="EC_004_OPT_DOES_NOT_EXIST",
                user_acknowledged_at="2026-04-30T22:00:00Z",
            )
        msg = str(ctx.exception)
        self.assertIn("EC_004_OPT_DOES_NOT_EXIST", msg)
        self.assertIn("not in current case's options", msg)


if __name__ == "__main__":
    unittest.main()
