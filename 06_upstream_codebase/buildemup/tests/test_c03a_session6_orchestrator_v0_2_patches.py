"""Tests for Component 3a Session 6 — v0.2 patch coverage.

Per locked S6 SPEC v1.0 § 7.4 — verifies the four v0.2 critique-round-1
patches that aren't fully exercised by happy/termination/error tests:

  P3 (Q7) — failed_option_ids_for_current_case enforcement at the
            validation layer; backend doesn't trust UI to grey out
            failed options.
  P4 — feasibility_input is sticky on GateState and re-passed to the
       c2_runner on every iteration.
  P5 — user_acknowledged_at is caller-supplied; backend has no clock.
       Empty timestamp → ValueError. Non-empty → exact pass-through
       to ExtremeDecision.user_acknowledged_at.
  P6 (Q13) — different_plot_promoted is sticky once True. Subsequent
             cases also get is_different_plot_option promoted to
             recommended (Interpretation A).
"""
from __future__ import annotations

import unittest
from typing import Optional
from unittest.mock import patch

from buildemup.components.c02.feasibility_input import FeasibilityInput
from buildemup.components.c03a.gate_state import (
    DifferentPlotPromotionEvent,
)
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


def _option(option_id: str, *,
            requires_brief_change=(),
            is_different_plot: bool = False,
            recommended: bool = False) -> ResolutionOption:
    return ResolutionOption(
        option_id=option_id,
        description=f"description for {option_id}",
        impact_summary="impact summary",
        cost_impact=None, space_impact_sqft=10,
        recommended=recommended,
        recommendation_reason="recommended" if recommended else None,
        requires_brief_change=requires_brief_change,
        requires_action=None, risk_advisory=None,
        is_preview_mode=False,
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
          options: tuple[ResolutionOption, ...]) -> ExtremeCase:
    return ExtremeCase(
        case_id=case_id, category=_DEFAULT_CATEGORY[case_id],
        blocking_gap_ids=("GAP_1",),
        user_facing_message=f"message for {case_id.value}",
        framing_line="trade-offs are necessary",
        resolution_probability=ResolutionProbability.NOT_APPLICABLE,
        options=options, detected_at_iteration=0,
    )


def _make_runner(gap: DesignGapAnalysis):
    calls: list[tuple[Brief, Optional[FeasibilityInput]]] = []

    def runner(brief, fi):
        calls.append((brief, fi))
        return gap

    return runner, calls


_BAD_CHANGE = BriefChange(
    field_path="this.path.does.not.exist",
    operation="SET",
    new_value=None,
    description="intentionally bad change",
)


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

class TestP3FailedOptionRejected(unittest.TestCase):
    """P3 — re-selecting a previously-failed option_id raises ValueError
    at the validation layer (backend doesn't trust UI)."""

    def test_p3_failed_option_id_rejected_on_re_selection(self):
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
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(case,)]):
            s = gate.start(session_id="sess-p3", brief=_make_brief())
            # First attempt fails → option_id added to failed set
            s = gate.apply_user_decision(
                state=s, case_id=case.case_id,
                chosen_option_id=bad_opt.option_id,
                user_acknowledged_at="2026-04-30T22:00:00Z",
            )
            self.assertIn(
                bad_opt.option_id, s.failed_option_ids_for_current_case,
            )
            # Second attempt with the same option_id is rejected with a
            # clear ValueError BEFORE any apply attempt.
            with self.assertRaises(ValueError) as ctx:
                gate.apply_user_decision(
                    state=s, case_id=case.case_id,
                    chosen_option_id=bad_opt.option_id,
                    user_acknowledged_at="2026-04-30T22:30:00Z",
                )
            msg = str(ctx.exception)
            self.assertIn(bad_opt.option_id, msg)
            self.assertIn("previously failed", msg)
            self.assertIn("Pick a different option", msg)


class TestP4FeasibilityInputCarried(unittest.TestCase):
    """P4 — feasibility_input is sticky on GateState and passed to the
    c2_runner on every iteration."""

    def test_p4_feasibility_input_passed_to_c2_on_every_iteration(self):
        gap = _make_gap_analysis()
        runner, calls = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        # Build a non-default FeasibilityInput. The default factory
        # produces a fresh one, so to compare identity later we capture
        # the exact instance we pass in.
        brief = _make_brief()
        fi = FeasibilityInput(brief=brief)

        c1 = _case(
            ExtremeCaseId.EC_004_FAR_EXCEEDED,
            options=(_option("EC_004_OPT_A"), _option("EC_004_OPT_B")),
        )
        c2 = _case(
            ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED,
            options=(_option("EC_005_OPT_X"), _option("EC_005_OPT_Y")),
        )

        with _DetectorPatch([(c1, c2), (c2,), ()]):
            s = gate.start(
                session_id="sess-p4", brief=brief, feasibility_input=fi,
            )
            # Iter 1
            s = gate.apply_user_decision(
                state=s, case_id=s.remaining_cases[0].case_id,
                chosen_option_id=s.remaining_cases[0].options[0].option_id,
                user_acknowledged_at="2026-04-30T23:00:00Z",
            )
            # Iter 2 (will resolve all → SUCCESS, but the C2 call must
            # still have used fi)
            s = gate.apply_user_decision(
                state=s, case_id=s.remaining_cases[0].case_id,
                chosen_option_id=s.remaining_cases[0].options[0].option_id,
                user_acknowledged_at="2026-04-30T23:30:00Z",
            )

        # Three c2_runner calls: start + 2 applies. All must have
        # been called with the SAME FeasibilityInput instance (P4).
        self.assertEqual(len(calls), 3)
        for i, (called_brief, called_fi) in enumerate(calls):
            self.assertIs(
                called_fi, fi,
                f"c2_runner call #{i} did not pass the supplied "
                f"feasibility_input through",
            )
        # Sticky on GateState too
        self.assertIs(s.feasibility_input, fi)


class TestP5UserAcknowledgedAtRequired(unittest.TestCase):
    """P5 — caller supplies user_acknowledged_at; empty raises; non-empty
    is stored exactly on the recorded ExtremeDecision."""

    def test_p5_user_acknowledged_at_required_and_used_in_decision(self):
        case = _case(
            ExtremeCaseId.EC_004_FAR_EXCEEDED,
            options=(_option("EC_004_OPT_A"), _option("EC_004_OPT_B")),
        )
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(case,), ()]):
            s = gate.start(session_id="sess-p5", brief=_make_brief())
            # Empty timestamp rejected
            with self.assertRaises(ValueError) as ctx:
                gate.apply_user_decision(
                    state=s, case_id=case.case_id,
                    chosen_option_id=case.options[0].option_id,
                    user_acknowledged_at="",
                )
            self.assertIn("user_acknowledged_at", str(ctx.exception))

            # Non-empty timestamp accepted; stored exactly
            ts = "2026-04-30T19:34:56Z"
            s = gate.apply_user_decision(
                state=s, case_id=case.case_id,
                chosen_option_id=case.options[0].option_id,
                user_acknowledged_at=ts,
            )

        self.assertEqual(len(s.decisions_so_far), 1)
        self.assertEqual(
            s.decisions_so_far[0].user_acknowledged_at, ts,
        )


class TestImmutabilityOfPerCaseCounts(unittest.TestCase):
    """Critique D-066 #2 — per_case_iteration_counts must be a read-only
    Mapping so the frozen-dataclass guarantee extends to its mapping
    members. Direct assignment should raise TypeError.

    Round-2 #2/#10 hardening: _freeze_counts copies its input before
    wrapping, so the GateState's mapping never shares storage with any
    caller-held dict reference. This test verifies that property by
    constructing a state via the orchestrator and asserting the
    standard mutation APIs raise.
    """

    def test_per_case_iteration_counts_rejects_mutation(self):
        case = _case(
            ExtremeCaseId.EC_004_FAR_EXCEEDED,
            options=(_option("EC_004_OPT_A"), _option("EC_004_OPT_B")),
        )
        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(case,), (case,)]):
            s = gate.start(session_id="sess-imm", brief=_make_brief())
            s = gate.apply_user_decision(
                state=s, case_id=case.case_id,
                chosen_option_id=case.options[0].option_id,
                user_acknowledged_at="2026-04-30T22:00:00Z",
            )

        # Read-only access works
        self.assertEqual(
            s.per_case_iteration_counts[case.case_id.value], 1,
        )
        # Direct mutation rejected
        with self.assertRaises(TypeError):
            s.per_case_iteration_counts["EC_999"] = 42  # type: ignore[index]
        with self.assertRaises(TypeError):
            del s.per_case_iteration_counts[case.case_id.value]  # type: ignore[arg-type]

    def test_freeze_counts_does_not_share_storage(self):
        """Round-2 #2/#10: _freeze_counts copies before wrapping, so
        the wrapped Mapping is decoupled from any caller-held dict."""
        from buildemup.components.c03a_extreme_case_gate import _freeze_counts

        source: dict[str, int] = {"EC_001": 1, "EC_002": 2}
        wrapped = _freeze_counts(source)
        # Mutate the source dict AFTER wrapping
        source["EC_001"] = 999
        source["EC_NEW"] = 1
        # The wrapped Mapping must be unaffected
        self.assertEqual(wrapped["EC_001"], 1)
        self.assertEqual(wrapped["EC_002"], 2)
        self.assertNotIn("EC_NEW", wrapped)


class TestP6DifferentPlotSticky(unittest.TestCase):
    """P6 (Q13 / Interpretation A) — once different_plot_promoted=True,
    every subsequent case surfaced gets is_different_plot_option marked
    recommended.

    Trigger condition: EC-002 + EC-006 co-fire on iter 0. Iter 1 surfaces
    a DIFFERENT case set that contains its own different-plot option;
    that option must also be recommended."""

    def test_p6_different_plot_promoted_persists_across_iterations(self):
        # Iter 0: EC-002 + EC-006 co-fire → promotion triggers.
        # The case surfaced (head after sort) has a different-plot option.
        ec002_dp = _option("EC_002_OPT_DIFFERENT_PLOT", is_different_plot=True)
        ec002 = _case(
            ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT,
            options=(_option("EC_002_OPT_A"), ec002_dp),
        )
        ec006_dp = _option("EC_006_OPT_DIFFERENT_PLOT", is_different_plot=True)
        ec006 = _case(
            ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
            options=(_option("EC_006_OPT_A"), ec006_dp),
        )

        # Iter 1: a DIFFERENT case (EC-005 LEGAL) — neither EC-002 nor
        # EC-006 — but it has its own different-plot option. P6 says
        # the promotion should still apply because different_plot_promoted
        # is sticky on GateState.
        ec005_dp = _option("EC_005_OPT_DIFFERENT_PLOT", is_different_plot=True)
        ec005 = _case(
            ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED,
            options=(_option("EC_005_OPT_A"), ec005_dp),
        )

        gap = _make_gap_analysis()
        runner, _ = _make_runner(gap)
        gate = ExtremeCaseGate(c2_runner=runner)

        with _DetectorPatch([(ec002, ec006), (ec005,)]):
            s0 = gate.start(session_id="sess-p6", brief=_make_brief())

            # Sanity: iter 0 trigger fired
            self.assertTrue(s0.different_plot_promoted)
            self.assertIsNotNone(s0.meta_banner)
            self.assertIsInstance(
                s0.meta_banner, DifferentPlotPromotionEvent,
            )
            self.assertEqual(
                s0.meta_banner.trigger, "EC002_AND_EC006_COFIRE",
            )
            self.assertEqual(s0.meta_banner.triggered_at_iteration, 0)
            # Both cases at iter 0 have their dp option promoted to recommended
            for c in s0.remaining_cases:
                dp_opts = [o for o in c.options if o.is_different_plot_option]
                self.assertTrue(dp_opts, f"case {c.case_id.value} has no DP")
                self.assertTrue(
                    all(o.recommended for o in dp_opts),
                    f"case {c.case_id.value} DP option not recommended on iter 0",
                )

            # Apply head; advance to iter 1 with EC-005 surfacing
            head = s0.remaining_cases[0]
            s1 = gate.apply_user_decision(
                state=s0, case_id=head.case_id,
                chosen_option_id=head.options[0].option_id,
                user_acknowledged_at="2026-04-30T23:00:00Z",
            )

        # Iter 1: EC-005 surfaced; even though neither EC-002 nor EC-006
        # is in the new case set, the sticky promoted flag means EC-005's
        # different-plot option is still recommended.
        self.assertFalse(s1.is_done)
        self.assertEqual(s1.remaining_cases[0].case_id, ec005.case_id)
        self.assertTrue(s1.different_plot_promoted)
        # Meta banner is sticky too (parent spec § 4.2 + invariant)
        self.assertIsNotNone(s1.meta_banner)
        # The DP option on EC-005 must be recommended (P6)
        ec005_options = s1.remaining_cases[0].options
        ec005_dp_opts = [
            o for o in ec005_options if o.is_different_plot_option
        ]
        self.assertEqual(len(ec005_dp_opts), 1)
        self.assertTrue(
            ec005_dp_opts[0].recommended,
            "P6 violated: EC-005's DP option not recommended on iter 1 "
            "even though different_plot_promoted is sticky True",
        )


if __name__ == "__main__":
    unittest.main()
