"""Tests for Component 3a Session 6 — orchestrator happy paths.

Per locked S6 SPEC v1.0 § 7.1 — verifies ExtremeCaseGate.start +
apply_user_decision over the no-blocker path, single-iteration paths,
multi-iteration paths, and transition-banner edge cases.

Test strategy (Q12): inject a fake c2_runner; patch
ExtremeCaseDetector.detect + OptionGenerator.generate_options to
return prepared ExtremeCases with real options. The orchestrator's
wiring is exercised end-to-end against real S4 (apply +
error_formatter), S5 (counterfactual + preflight) and the real
GateState / GateTermination logic.
"""
from __future__ import annotations

import unittest
from typing import Optional
from unittest.mock import patch

from buildemup.components.c02.feasibility_input import FeasibilityInput
from buildemup.components.c03a.gate_state import (
    GateState,
    GateTerminationReason,
    TransitionBannerEvent,
)
from buildemup.components.c03a_extreme_case_gate import ExtremeCaseGate
from buildemup.domain.brief import Brief, BudgetRange
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.extreme_case import (
    BriefMode,
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
# Fixtures (replicated inline per c3a test convention)
# ─────────────────────────────────────────────────────────────────

def _make_brief() -> Brief:
    plot = Plot(
        width_m=10.0, depth_m=12.0,
        facing=PlotOrientation.NORTH, city="chennai",
        road_width_m=6.0, plot_type=PlotType.DETACHED,
    )
    floor = FloorRequirement(
        floor_number=0, floor_use=FloorUse.RESIDENTIAL,
        rooms=(
            RoomRequirement(RoomType.BEDROOM_REGULAR, count=2),
            RoomRequirement(RoomType.BATHROOM_COMMON, count=1),
            RoomRequirement(RoomType.KITCHEN, count=1),
            RoomRequirement(RoomType.LIVING, count=1),
        ),
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


def _option(option_id: str, *, recommended: bool = False,
            is_different_plot: bool = False,
            is_preview: bool = False,
            requires_action: Optional[str] = None,
            description: Optional[str] = None) -> ResolutionOption:
    return ResolutionOption(
        option_id=option_id,
        description=description or f"description for {option_id}",
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


def _case(case_id: ExtremeCaseId,
          *,
          category: Optional[ExtremeCaseCategory] = None,
          options: Optional[tuple[ResolutionOption, ...]] = None,
          iteration: int = 0) -> ExtremeCase:
    """Build a minimal ExtremeCase with real (non-placeholder) options."""
    if options is None:
        options = (_option(f"{case_id.name}_OPT_A"),
                   _option(f"{case_id.name}_OPT_B"))
    if category is None:
        category = _DEFAULT_CATEGORY[case_id]
    return ExtremeCase(
        case_id=case_id, category=category,
        blocking_gap_ids=("GAP_1",),
        user_facing_message=f"message for {case_id.value}",
        framing_line="trade-offs are necessary",
        resolution_probability=ResolutionProbability.NOT_APPLICABLE,
        options=options,
        detected_at_iteration=iteration,
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


def _detect_seq(*case_tuples: tuple[ExtremeCase, ...]):
    """Helper: build a side_effect list for ExtremeCaseDetector.detect.

    Each positional argument is the tuple to return on the corresponding
    .detect() call. The orchestrator calls detect once per C2 run
    (start + each apply_user_decision iteration).
    """
    return list(case_tuples)


def _make_runner(gap: DesignGapAnalysis):
    """Build a fake c2_runner that always returns the same gap analysis
    and records calls. Returns (runner, calls_list) tuple."""
    calls: list[tuple[Brief, Optional[FeasibilityInput]]] = []

    def runner(brief: Brief, fi: Optional[FeasibilityInput]) -> DesignGapAnalysis:
        calls.append((brief, fi))
        return gap

    return runner, calls


# ─────────────────────────────────────────────────────────────────
# Test module helper: detector + options patches as a context
# ─────────────────────────────────────────────────────────────────

class _DetectorPatch:
    """Context manager that patches detector.detect + option_generator.

    Pass `detect_returns` as a list — each call to detect pops one element.
    OptionGenerator.generate_options returns case.options unchanged so
    the orchestrator's _generate_real_options is a no-op pass-through
    (cases already have real options in fixtures).
    """
    _DETECTOR_PATH = "buildemup.components.c03a_extreme_case_gate.ExtremeCaseDetector.detect"
    _OPTGEN_PATH = "buildemup.components.c03a_extreme_case_gate.OptionGenerator.generate_options"

    def __init__(self, detect_returns):
        self._detect_returns = list(detect_returns)
        self._d_patcher = patch(self._DETECTOR_PATH)
        self._o_patcher = patch(self._OPTGEN_PATH)
        self.detect_mock = None
        self.optgen_mock = None

    def __enter__(self):
        self.detect_mock = self._d_patcher.start()
        self.optgen_mock = self._o_patcher.start()
        self.detect_mock.side_effect = self._detect_returns
        # OptionGenerator pass-through: return the case's existing options
        self.optgen_mock.side_effect = (
            lambda case, brief, gap, co: case.options
        )
        return self

    def __exit__(self, *exc):
        self._d_patcher.stop()
        self._o_patcher.stop()


# ─────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────

class TestStartNoBlockers(unittest.TestCase):
    """Test 1 — start() with no blockers returns done immediately."""

    def test_start_with_no_blockers_returns_done_immediately(self):
        gap = _make_gap_analysis()
        runner, calls = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)
        brief = _make_brief()

        with _DetectorPatch([()]):
            state = gate.start(session_id="sess-1", brief=brief)

        self.assertTrue(state.is_done)
        self.assertEqual(state.termination_reason, GateTerminationReason.SUCCESS)
        self.assertEqual(state.remaining_cases, ())
        self.assertEqual(state.iteration_count, 0)
        self.assertIsNotNone(state.final_resolved_brief)
        self.assertEqual(state.final_resolved_brief.mode, BriefMode.BUILDABLE)
        self.assertTrue(state.final_resolved_brief.is_layout_ready)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], brief)


class TestStartWithBlockers(unittest.TestCase):
    """Test 2 — start() with blockers builds preflight and sorts cases.

    Detector returns three cases in detection order:
      EC-008 (BUDGET), EC-001 (SPATIAL), EC-005 (LEGAL).
    Priority sort should put LEGAL first, SPATIAL second, BUDGET last.
    """

    def test_start_with_blockers_builds_preflight_and_sorts(self):
        cases = (
            _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW),
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
            _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED),
        )
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([cases]):
            state = gate.start(session_id="sess-2", brief=_make_brief())

        self.assertFalse(state.is_done)
        self.assertEqual(len(state.remaining_cases), 3)
        # Priority order: LEGAL (EC-005) → SPATIAL (EC-001) → BUDGET (EC-008)
        self.assertEqual(state.remaining_cases[0].case_id,
                         ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        self.assertEqual(state.remaining_cases[1].case_id,
                         ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)
        self.assertEqual(state.remaining_cases[2].case_id,
                         ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW)
        # Preflight is built with the full case set
        self.assertIsNotNone(state.preflight)
        self.assertEqual(state.preflight.total_blocker_count, 3)
        self.assertEqual(state.iteration_count, 0)
        # No transition banner on iter 0
        self.assertIsNone(state.transition_banner)


class TestApplyAdvancesToNext(unittest.TestCase):
    """Test 3 — apply_user_decision advances to the next case in queue."""

    def test_apply_decision_advances_to_next_case(self):
        # Iter 0: two cases. Iter 1 (after first apply): one case left.
        case1 = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        case2 = _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)
        gap = _make_gap_analysis()
        runner, calls = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(case1, case2), (case2,)]):
            s0 = gate.start(session_id="sess-3", brief=_make_brief())
            s1 = gate.apply_user_decision(
                state=s0,
                case_id=case1.case_id,
                chosen_option_id=case1.options[0].option_id,
                user_acknowledged_at="2026-04-30T12:00:00Z",
            )

        self.assertFalse(s1.is_done)
        self.assertEqual(s1.iteration_count, 1)
        self.assertEqual(len(s1.remaining_cases), 1)
        self.assertEqual(s1.remaining_cases[0].case_id, case2.case_id)
        self.assertEqual(len(s1.decisions_so_far), 1)
        self.assertEqual(s1.decisions_so_far[0].iteration_index, 0)
        self.assertEqual(
            s1.decisions_so_far[0].user_acknowledged_at,
            "2026-04-30T12:00:00Z",
        )
        # per-case count incremented for the resolved case
        self.assertEqual(
            s1.per_case_iteration_counts[case1.case_id.value], 1,
        )
        # c2_runner was called once at start + once after apply = 2
        self.assertEqual(len(calls), 2)


class TestApplyThreeDecisions(unittest.TestCase):
    """Test 4 — three apply_user_decision calls resolve all cases."""

    def test_apply_three_decisions_resolves_all(self):
        c1 = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        c2 = _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)
        c3 = _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW)
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        # detect call sequence:
        #   start          → (c1, c2, c3)   priority: LEGAL → SPATIAL → BUDGET
        #   after apply 1  → (c2, c3)
        #   after apply 2  → (c3,)
        #   after apply 3  → ()              SUCCESS
        with _DetectorPatch([
            (c1, c2, c3),
            (c2, c3),
            (c3,),
            (),
        ]):
            s = gate.start(session_id="sess-4", brief=_make_brief())
            for case in (c1, c2, c3):
                s = gate.apply_user_decision(
                    state=s,
                    case_id=case.case_id,
                    chosen_option_id=case.options[0].option_id,
                    user_acknowledged_at=f"2026-04-30T1{case.case_id.value[3]}:00:00Z",
                )

        self.assertTrue(s.is_done)
        self.assertEqual(s.termination_reason, GateTerminationReason.SUCCESS)
        self.assertEqual(s.iteration_count, 3)
        self.assertEqual(len(s.decisions_so_far), 3)
        self.assertIsNotNone(s.final_resolved_brief)
        self.assertEqual(s.final_resolved_brief.mode, BriefMode.BUILDABLE)
        self.assertTrue(s.final_resolved_brief.is_layout_ready)
        # 3 counterfactuals — one per decision
        self.assertEqual(len(s.final_resolved_brief.counterfactuals), 3)


class TestApplyCreatesNewBlocker(unittest.TestCase):
    """Test 5 — apply_user_decision can introduce a new blocker.

    Iter 0: detector returns case_A (EC-005).
    Iter 1: detector returns case_B (EC-008) — new case after resolving A.
    """

    def test_apply_decision_creates_new_blocker(self):
        case_a = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        case_b = _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW)
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(case_a,), (case_b,)]):
            s0 = gate.start(session_id="sess-5", brief=_make_brief())
            s1 = gate.apply_user_decision(
                state=s0,
                case_id=case_a.case_id,
                chosen_option_id=case_a.options[0].option_id,
                user_acknowledged_at="2026-04-30T13:00:00Z",
            )

        self.assertFalse(s1.is_done)
        self.assertEqual(len(s1.remaining_cases), 1)
        self.assertEqual(s1.remaining_cases[0].case_id, case_b.case_id)
        self.assertEqual(s1.iteration_count, 1)


class TestTransitionBannerFires(unittest.TestCase):
    """Test 6 — transition banner fires on iter 2 with case_id change.

    Asserts the typed TransitionBannerEvent shape (P1).
    """

    def test_transition_banner_fires_on_iter2_case_change(self):
        # We need 2 successful iterations leading to a different case
        # at iter 2:
        #   start: (A, B)            iter 0
        #   apply A → detect (B,)    iter 1 (no banner: same case continuing)
        #   apply B → detect (C,)    iter 2 (banner: B → C)
        case_a = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        case_b = _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)
        case_c = _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW)
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([
            (case_a, case_b),
            (case_b,),
            (case_c,),
        ]):
            s = gate.start(session_id="sess-6", brief=_make_brief())
            s = gate.apply_user_decision(
                state=s, case_id=case_a.case_id,
                chosen_option_id=case_a.options[0].option_id,
                user_acknowledged_at="2026-04-30T14:00:00Z",
            )
            self.assertIsNone(
                s.transition_banner,
                "iter 1: previous case was A, new case is B, but "
                "iteration is 1 (banner only fires iter ∈ {2,3})",
            )
            s = gate.apply_user_decision(
                state=s, case_id=case_b.case_id,
                chosen_option_id=case_b.options[0].option_id,
                user_acknowledged_at="2026-04-30T15:00:00Z",
            )

        self.assertEqual(s.iteration_count, 2)
        self.assertIsNotNone(s.transition_banner)
        self.assertIsInstance(s.transition_banner, TransitionBannerEvent)
        self.assertEqual(s.transition_banner.previous_case_id, case_b.case_id)
        self.assertEqual(s.transition_banner.new_case_id, case_c.case_id)
        self.assertEqual(
            s.transition_banner.previous_chosen_option_id,
            case_b.options[0].option_id,
        )
        # Description is FULL — UI truncates; we receive raw
        self.assertEqual(
            s.transition_banner.previous_chosen_option_description,
            case_b.options[0].description,
        )
        self.assertEqual(s.transition_banner.iteration, 2)


class TestTransitionBannerSilent(unittest.TestCase):
    """Test 7 — banner does NOT fire on iter 1 nor iter 4."""

    def test_transition_banner_does_not_fire_on_iter1_or_4(self):
        # iter 1: the banner predicate excludes iter 1 by spec. Build a
        # fresh session and verify after the first apply.
        a = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        b = _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(a, b), (b,)]):
            s = gate.start(session_id="sess-7a", brief=_make_brief())
            s = gate.apply_user_decision(
                state=s, case_id=a.case_id,
                chosen_option_id=a.options[0].option_id,
                user_acknowledged_at="2026-04-30T16:00:00Z",
            )
        self.assertEqual(s.iteration_count, 1)
        self.assertIsNone(s.transition_banner)

        # iter 4: simulate four successful applies that switch case_id
        # at the final step. We always pop the head of the remaining
        # queue to avoid relying on cases-input ordering vs priority
        # ordering. Detector returns one less case per call until the
        # last step where case_id changes from the resolved one.
        c1 = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        c2 = _case(ExtremeCaseId.EC_004_FAR_EXCEEDED)
        c3 = _case(ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED)
        c4 = _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)
        c5 = _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW)
        # Priority order: c1 + c2 + c3 (LEGAL) → c4 (SPATIAL) → c5 (BUDGET)
        runner2, _ = _make_runner(gap)
        gate2 = ExtremeCaseGate(c2_runner=runner2)

        with _DetectorPatch([
            (c1, c2, c3, c4, c5),    # start
            (c2, c3, c4, c5),         # after apply 1
            (c3, c4, c5),             # after apply 2
            (c4, c5),                 # after apply 3
            (c5,),                    # after apply 4 — case_id changes c4→c5
        ]):
            s = gate2.start(session_id="sess-7b", brief=_make_brief())
            for i in range(4):
                head = s.remaining_cases[0]
                s = gate2.apply_user_decision(
                    state=s, case_id=head.case_id,
                    chosen_option_id=head.options[0].option_id,
                    user_acknowledged_at=f"2026-04-30T1{i}:00:00Z",
                )

        self.assertEqual(s.iteration_count, 4)
        # iter 4 is OUT of {2,3} → no banner even though case_id changed
        self.assertIsNone(s.transition_banner)


if __name__ == "__main__":
    unittest.main()
