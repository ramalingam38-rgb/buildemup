"""Tests for Component 3a Session 6 — termination paths.

Per locked S6 SPEC v1.0 § 7.2 — verifies the five terminal conditions:
  - MAX_ITERATIONS_REACHED (precedence #2)
  - PER_CASE_LIMIT_REACHED (precedence #3)
  - USER_ABORTED
  - PREVIEW_MODE (with mandatory acknowledgment + Q14/C1: gap_analysis
    reflects last-buildable-state, not preview re-run)
  - CBA_VERIFICATION_PAUSED

SUCCESS termination is exercised in test_c03a_session6_orchestrator_happy
(test_apply_three_decisions_resolves_all). Here we focus on non-success
exits.
"""
from __future__ import annotations

import unittest
from typing import Optional
from unittest.mock import patch

from buildemup.components.c02.feasibility_input import FeasibilityInput
from buildemup.components.c03a.gate_state import GateTerminationReason
from buildemup.components.c03a_extreme_case_gate import ExtremeCaseGate
from buildemup.domain.brief import Brief, BudgetRange
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.extreme_case import (
    BriefMode,
    ExtremeCase,
    ExtremeCaseCategory,
    ExtremeCaseId,
    PreviewModeAcknowledgment,
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
# Fixtures (replicated inline)
# ─────────────────────────────────────────────────────────────────

def _make_brief() -> Brief:
    plot = Plot(
        width_m=10.0, depth_m=12.0,
        facing=PlotOrientation.NORTH, city="chennai",
        road_width_m=6.0, plot_type=PlotType.DETACHED,
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


def _option(option_id: str, *,
            requires_action: Optional[str] = None,
            is_preview: bool = False,
            is_different_plot: bool = False,
            recommended: bool = False) -> ResolutionOption:
    return ResolutionOption(
        option_id=option_id,
        description=f"description for {option_id}",
        impact_summary="impact summary",
        cost_impact=None, space_impact_sqft=10,
        recommended=recommended,
        recommendation_reason="recommended" if recommended else None,
        requires_brief_change=(),
        requires_action=requires_action,
        risk_advisory=None,
        is_preview_mode=is_preview,
        is_different_plot_option=is_different_plot,
    )


_DEFAULT_CATEGORY = {
    ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE:    ExtremeCaseCategory.SPATIAL,
    ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT:        ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_003_NO_PARKING_POSITION:            ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_004_FAR_EXCEEDED:                   ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED:       ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE: ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED:         ExtremeCaseCategory.LEGAL,
    ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW:    ExtremeCaseCategory.BUDGET,
    ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW:  ExtremeCaseCategory.SITE,
    ExtremeCaseId.EC_010_APPROVAL_BLOCKER:               ExtremeCaseCategory.APPROVAL,
}


def _case(case_id: ExtremeCaseId,
          *,
          options: Optional[tuple[ResolutionOption, ...]] = None,
          iteration: int = 0) -> ExtremeCase:
    if options is None:
        options = (_option(f"{case_id.name}_OPT_A"),
                   _option(f"{case_id.name}_OPT_B"))
    return ExtremeCase(
        case_id=case_id, category=_DEFAULT_CATEGORY[case_id],
        blocking_gap_ids=("GAP_1",),
        user_facing_message=f"message for {case_id.value}",
        framing_line="trade-offs are necessary",
        resolution_probability=ResolutionProbability.NOT_APPLICABLE,
        options=options, detected_at_iteration=iteration,
    )


def _make_runner(gap: DesignGapAnalysis):
    calls: list[tuple[Brief, Optional[FeasibilityInput]]] = []

    def runner(brief, fi):
        calls.append((brief, fi))
        return gap

    return runner, calls


class _DetectorPatch:
    _DETECTOR_PATH = "buildemup.components.c03a_extreme_case_gate.ExtremeCaseDetector.detect"
    _OPTGEN_PATH = "buildemup.components.c03a_extreme_case_gate.OptionGenerator.generate_options"

    def __init__(self, detect_returns):
        self._returns = list(detect_returns)
        self._dp = patch(self._DETECTOR_PATH)
        self._op = patch(self._OPTGEN_PATH)

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

class TestMaxIterations(unittest.TestCase):
    """Test 1 — MAX_ITERATIONS_REACHED fires when iteration_count hits 7
    with non-empty cases on detect. Precedence rule: SUCCESS > MAX > PER_CASE.
    """

    def test_max_iterations_termination(self):
        # 7 successful applies, each on a DIFFERENT case_id so the
        # per-case counter never reaches PER_CASE_LIMIT=3. After the
        # 7th apply iteration_count == MAX_ITERATIONS=7 and the detector
        # still returns a case → MAX_ITERATIONS_REACHED fires
        # (precedence rule: SUCCESS > MAX > PER_CASE).
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        # 8 distinct ECs — one to surface, then a fresh one on each iter
        case_ids = [
            ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
            ExtremeCaseId.EC_003_NO_PARKING_POSITION,
            ExtremeCaseId.EC_004_FAR_EXCEEDED,
            ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED,
            ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED,
            ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW,
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
        ]
        cases = [_case(cid) for cid in case_ids]

        # detect call sequence: each call returns one fresh, distinct case.
        # start → cases[0]; after apply 1 → cases[1]; … ; after apply 7 → cases[7].
        # 8 detect calls total: 1 at start + 7 after each apply.
        detect_seq = [(c,) for c in cases]

        with _DetectorPatch(detect_seq):
            s = gate.start(session_id="sess-max", brief=_make_brief())
            for i in range(ExtremeCaseGate.MAX_ITERATIONS):
                head = s.remaining_cases[0]
                s = gate.apply_user_decision(
                    state=s, case_id=head.case_id,
                    chosen_option_id=head.options[0].option_id,
                    user_acknowledged_at=f"2026-04-30T1{i}:00:00Z",
                )
                if s.is_done:
                    break

        self.assertTrue(s.is_done)
        self.assertEqual(
            s.termination_reason,
            GateTerminationReason.MAX_ITERATIONS_REACHED,
        )
        self.assertEqual(s.iteration_count, ExtremeCaseGate.MAX_ITERATIONS)
        self.assertIsNotNone(s.final_resolved_brief)
        # Q11: aborted ResolvedBrief is mode=BUILDABLE, is_layout_ready=False
        self.assertEqual(s.final_resolved_brief.mode, BriefMode.BUILDABLE)
        self.assertFalse(s.final_resolved_brief.is_layout_ready)
        self.assertTrue(s.final_resolved_brief.decision_log.aborted)
        self.assertEqual(
            s.final_resolved_brief.decision_log.abort_reason,
            "MAX_ITERATIONS_REACHED",
        )


class TestPerCaseLimit(unittest.TestCase):
    """Test 2 — PER_CASE_LIMIT_REACHED fires when same case_id resolved
    PER_CASE_LIMIT=3 times and still appears in remaining cases.
    """

    def test_per_case_limit_termination(self):
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        # The same case keeps coming back. Every apply increments
        # per_case_iteration_counts[case_id]; after 3rd apply, the
        # case is still in remaining cases, so PER_CASE_LIMIT fires.
        case = _case(ExtremeCaseId.EC_004_FAR_EXCEEDED)

        with _DetectorPatch([
            (case,),   # start
            (case,),   # after apply 1 (per-case=1)
            (case,),   # after apply 2 (per-case=2)
            (case,),   # after apply 3 (per-case=3) — termination fires
        ]):
            s = gate.start(session_id="sess-per", brief=_make_brief())
            for i in range(3):
                s = gate.apply_user_decision(
                    state=s, case_id=case.case_id,
                    chosen_option_id=case.options[0].option_id,
                    user_acknowledged_at=f"2026-04-30T1{i}:00:00Z",
                )
                if s.is_done:
                    break

        self.assertTrue(s.is_done)
        self.assertEqual(
            s.termination_reason,
            GateTerminationReason.PER_CASE_LIMIT_REACHED,
        )
        self.assertEqual(
            s.per_case_iteration_counts[case.case_id.value], 3,
        )
        self.assertEqual(s.iteration_count, 3)
        self.assertEqual(
            s.final_resolved_brief.decision_log.abort_reason,
            "PER_CASE_LIMIT_REACHED",
        )


class TestUserAbort(unittest.TestCase):
    """Test 3 — apply_user_abort returns terminal USER_ABORTED state."""

    def test_user_abort_terminal_state(self):
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)
        case_a = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        case_b = _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)

        with _DetectorPatch([(case_a, case_b)]):
            s0 = gate.start(session_id="sess-abort", brief=_make_brief())
        # No further detection calls — apply_user_abort doesn't run C2.
        s1 = gate.apply_user_abort(s0)

        self.assertTrue(s1.is_done)
        self.assertEqual(
            s1.termination_reason, GateTerminationReason.USER_ABORTED,
        )
        self.assertIsNotNone(s1.final_resolved_brief)
        self.assertEqual(
            s1.final_resolved_brief.mode, BriefMode.BUILDABLE,
        )
        self.assertFalse(s1.final_resolved_brief.is_layout_ready)
        self.assertEqual(
            s1.final_resolved_brief.decision_log.abort_reason,
            "USER_ABORTED",
        )

    def test_user_abort_on_terminal_state_raises(self):
        # Sanity: aborting a terminal state is a programmer error.
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)
        with _DetectorPatch([()]):
            s0 = gate.start(session_id="sess-abort-2", brief=_make_brief())
        with self.assertRaises(ValueError) as ctx:
            gate.apply_user_abort(s0)
        self.assertIn("terminal state", str(ctx.exception))


class TestPreviewMode(unittest.TestCase):
    """Test 4 — PREVIEW_MODE termination with mandatory acknowledgment.

    Asserts (per Q14/C1) that gap_analysis on the ResolvedBrief equals
    state.current_gap_analysis at the moment Preview Mode was picked
    — i.e., the LAST BUILDABLE state, not a re-run on the preview.
    """

    def test_preview_mode_terminal_with_acknowledgment(self):
        gap = _make_gap_analysis()
        runner, calls = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        # Build a case whose LAST option is Preview Mode (per spec § 6
        # UI rule: Preview Mode option must be last).
        regular = _option("EC_001_OPT_A")
        preview_opt = _option("EC_001_OPT_PREVIEW", is_preview=True)
        case = _case(
            ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            options=(regular, preview_opt),
        )

        with _DetectorPatch([(case,)]):
            s0 = gate.start(session_id="sess-preview", brief=_make_brief())

        # Capture gap reference for the last-buildable assertion below
        last_buildable_gap = s0.current_gap_analysis

        ack = PreviewModeAcknowledgment(
            user_acknowledged_at="2026-04-30T20:00:00Z",
            acknowledgment_text=(
                "I understand this cannot be legally approved or built as-is."
            ),
            user_session_id="sess-preview",
        )
        s1 = gate.apply_user_decision(
            state=s0, case_id=case.case_id,
            chosen_option_id=preview_opt.option_id,
            user_acknowledged_at="2026-04-30T20:00:00Z",
            preview_mode_acknowledgment=ack,
        )

        self.assertTrue(s1.is_done)
        self.assertEqual(
            s1.termination_reason, GateTerminationReason.PREVIEW_MODE,
        )
        rb = s1.final_resolved_brief
        self.assertIsNotNone(rb)
        self.assertEqual(rb.mode, BriefMode.PREVIEW)
        self.assertTrue(rb.is_layout_ready)  # PREVIEW is a valid output mode
        self.assertIs(rb.preview_mode_acknowledgment, ack)
        # Q14 / C1: gap_analysis on PREVIEW reflects last buildable state
        self.assertIs(rb.final_feasibility, last_buildable_gap)
        # C2 was NOT re-run when Preview Mode was picked
        self.assertEqual(len(calls), 1)
        # PREVIEW mode populates relaxed_constraints from EC mapping
        self.assertEqual(rb.relaxed_constraints, ("AREA_VS_ENVELOPE",))
        # decision_log records the preview acknowledgement signal
        self.assertEqual(
            rb.decision_log.abort_reason, "USER_CHOSE_PREVIEW_MODE",
        )

    def test_preview_mode_without_acknowledgment_raises(self):
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)
        preview_opt = _option("EC_001_OPT_PREVIEW", is_preview=True)
        case = _case(
            ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            options=(_option("EC_001_OPT_A"), preview_opt),
        )
        with _DetectorPatch([(case,)]):
            s = gate.start(session_id="sess-preview-2", brief=_make_brief())
        with self.assertRaises(ValueError) as ctx:
            gate.apply_user_decision(
                state=s, case_id=case.case_id,
                chosen_option_id=preview_opt.option_id,
                user_acknowledged_at="2026-04-30T20:00:00Z",
                preview_mode_acknowledgment=None,
            )
        self.assertIn("acknowledgment", str(ctx.exception).lower())


class TestCBAVerification(unittest.TestCase):
    """Test 5 — CBA verification pauses the session without running C2."""

    def test_cba_verification_pauses(self):
        gap = _make_gap_analysis()
        runner, calls = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        cba_opt = _option(
            "EC_010_OPT_VERIFY_CBA",
            requires_action="EMAIL_CBA_CHECKLIST",
        )
        case = _case(
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
            options=(_option("EC_010_OPT_A"), cba_opt),
        )

        with _DetectorPatch([(case,)]):
            s0 = gate.start(session_id="sess-cba", brief=_make_brief())
        s1 = gate.apply_user_decision(
            state=s0, case_id=case.case_id,
            chosen_option_id=cba_opt.option_id,
            user_acknowledged_at="2026-04-30T21:00:00Z",
        )

        self.assertTrue(s1.is_done)
        self.assertEqual(
            s1.termination_reason,
            GateTerminationReason.CBA_VERIFICATION_PAUSED,
        )
        rb = s1.final_resolved_brief
        self.assertEqual(rb.mode, BriefMode.BUILDABLE)
        self.assertFalse(rb.is_layout_ready)
        self.assertEqual(
            rb.decision_log.abort_reason, "AWAITING_CBA_VERIFICATION",
        )
        # Decision recorded
        self.assertEqual(len(s1.decisions_so_far), 1)
        # C2 NOT re-run on CBA path
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
