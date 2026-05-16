"""
BuildemUp† — Component 3a domain tests (Session 1).

Tests for `domain/extreme_case.py`. Per SPEC v0.2.1 Section 9.1 — covers:
  - Round-trip serialization (frozen dataclasses are hashable + immutable)
  - __post_init__ validation invariants for each type
  - CostConfidence helper properties (uncertainty_pct, default_caveat_language)
  - CostImpact.build() factory
  - ResolvedBrief mode-specific consistency rules
  - BriefChangeIntegrityError classification

Total: ~12 test methods (slight overshoot of the 7-test target; spec said ~7
but the coverage is ~12 because each EC-related invariant gets a focused test).
"""
import unittest
from datetime import datetime, timezone

from buildemup.domain.extreme_case import (
    # Enums
    ExtremeCaseCategory,
    ExtremeCaseId,
    ResolutionProbability,
    BriefMode,
    CostConfidence,
    # Dataclasses
    BriefChange,
    CostImpact,
    ResolutionOption,
    ExtremeCase,
    ExtremeDecision,
    ExtremeDecisionLog,
    CounterfactualSummary,
    PreflightSummary,
    PreviewModeAcknowledgment,
    ResolvedBrief,
    # Other
    BriefChangeIntegrityError,
    DEFAULT_COUNTERFACTUAL_FRAMING,
    EXTREME_CASE_DOMAIN_TYPE_NAMES,
)


def _make_brief_change(field_path="rooms.bedroom_3", op="DELETE",
                       desc="Remove bedroom 3"):
    """Helper: build a default-valid BriefChange."""
    return BriefChange(
        field_path=field_path,
        operation=op,
        new_value=None,
        description=desc,
    )


def _make_option(option_id="EC_001_OPT_A", *, recommended=False,
                 reason=None, is_preview=False, brief_changes=None):
    """Helper: build a default-valid ResolutionOption."""
    if brief_changes is None and not is_preview:
        brief_changes = (_make_brief_change(),)
    elif is_preview:
        brief_changes = ()
    return ResolutionOption(
        option_id=option_id,
        description=f"option {option_id}",
        impact_summary="Saves ~120 sqft",
        cost_impact=None,
        space_impact_sqft=-120,
        recommended=recommended,
        recommendation_reason=reason,
        requires_brief_change=brief_changes,
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=is_preview,
    )


def _make_extreme_case(*, options=None, iteration=0):
    """Helper: build a default-valid ExtremeCase with at least 2 options."""
    if options is None:
        options = (_make_option("EC_001_OPT_A"), _make_option("EC_001_OPT_B"))
    return ExtremeCase(
        case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
        category=ExtremeCaseCategory.SPATIAL,
        blocking_gap_ids=("GAP_001",),
        user_facing_message="Your plot fits about 750 sqft per floor.",
        framing_line="One of these trade-offs is necessary.",
        resolution_probability=ResolutionProbability.NOT_APPLICABLE,
        options=options,
        detected_at_iteration=iteration,
    )


# ═════════════════════════════════════════════════════════════════════════
# Test 1 — Enums
# ═════════════════════════════════════════════════════════════════════════

class TestEnums(unittest.TestCase):
    """Verify all 5 enums have expected members and value strings."""

    def test_extreme_case_category_members(self):
        self.assertEqual(ExtremeCaseCategory.SPATIAL.value, "SPATIAL")
        self.assertEqual(ExtremeCaseCategory.LEGAL.value, "LEGAL")
        self.assertEqual(ExtremeCaseCategory.BUDGET.value, "BUDGET")
        self.assertEqual(ExtremeCaseCategory.SITE.value, "SITE")
        self.assertEqual(ExtremeCaseCategory.APPROVAL.value, "APPROVAL")

    def test_extreme_case_id_has_all_10(self):
        ids = {e.value for e in ExtremeCaseId}
        expected = {f"EC_{i:03d}" for i in range(1, 11)}
        self.assertEqual(ids, expected)

    def test_brief_mode_members(self):
        self.assertEqual(BriefMode.BUILDABLE.value, "BUILDABLE")
        self.assertEqual(BriefMode.PREVIEW.value, "PREVIEW")

    def test_cost_confidence_uncertainty_pct(self):
        """v0.2.1 critique #3: uncertainty_pct drives caveat strength."""
        self.assertEqual(CostConfidence.HIGH.uncertainty_pct, 15)
        self.assertEqual(CostConfidence.MEDIUM.uncertainty_pct, 25)
        self.assertEqual(CostConfidence.LOW.uncertainty_pct, 40)

    def test_cost_confidence_caveat_language(self):
        """v0.2.1 critique #3: LOW + MEDIUM get caveats; HIGH does not."""
        self.assertIsNone(CostConfidence.HIGH.default_caveat_language)
        self.assertIn("approximately", CostConfidence.MEDIUM.default_caveat_language)
        self.assertIn("±40%", CostConfidence.LOW.default_caveat_language)


# ═════════════════════════════════════════════════════════════════════════
# Test 2 — BriefChange validation
# ═════════════════════════════════════════════════════════════════════════

class TestBriefChange(unittest.TestCase):

    def test_valid_brief_change(self):
        bc = _make_brief_change()
        self.assertEqual(bc.field_path, "rooms.bedroom_3")
        self.assertEqual(bc.operation, "DELETE")

    def test_empty_field_path_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            BriefChange(
                field_path="",
                operation="DELETE",
                new_value=None,
                description="x",
            )
        self.assertIn("field_path", str(ctx.exception))

    def test_invalid_operation_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            BriefChange(
                field_path="rooms.bed",
                operation="MUTATE",  # not in allowed set
                new_value=None,
                description="x",
            )
        self.assertIn("operation", str(ctx.exception))

    def test_empty_description_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            BriefChange(
                field_path="rooms.bed",
                operation="DELETE",
                new_value=None,
                description="",
            )
        self.assertIn("description", str(ctx.exception))


# ═════════════════════════════════════════════════════════════════════════
# Test 3 — CostImpact + factory
# ═════════════════════════════════════════════════════════════════════════

class TestCostImpact(unittest.TestCase):

    def test_valid_triple(self):
        ci = CostImpact(
            low_inr=300_000,
            midpoint_inr=400_000,
            high_inr=500_000,
            confidence=CostConfidence.HIGH,
            derivation="from C7 cost engine",
        )
        self.assertEqual(ci.midpoint_inr, 400_000)

    def test_triple_ordering_enforced(self):
        """low <= mid <= high invariant."""
        with self.assertRaises(ValueError):
            CostImpact(
                low_inr=500_000,
                midpoint_inr=400_000,  # mid < low
                high_inr=600_000,
                confidence=CostConfidence.HIGH,
                derivation="x",
            )

    def test_build_factory_auto_fills_low_caveat(self):
        """v0.2.1 critique #3: build() auto-populates caveat for LOW."""
        ci = CostImpact.build(
            low=300_000, mid=400_000, high=500_000,
            confidence=CostConfidence.LOW,
            derivation="estimated rough",
        )
        self.assertEqual(ci.uncertainty_pct, 40)
        self.assertIsNotNone(ci.caveat_language)
        self.assertIn("±40%", ci.caveat_language)

    def test_build_factory_no_caveat_for_high(self):
        """HIGH confidence needs no caveat."""
        ci = CostImpact.build(
            low=300_000, mid=400_000, high=500_000,
            confidence=CostConfidence.HIGH,
            derivation="from C7 cost engine",
        )
        self.assertEqual(ci.uncertainty_pct, 15)
        self.assertIsNone(ci.caveat_language)

    def test_empty_derivation_rejected(self):
        with self.assertRaises(ValueError):
            CostImpact(
                low_inr=300_000,
                midpoint_inr=400_000,
                high_inr=500_000,
                confidence=CostConfidence.HIGH,
                derivation="",
            )


# ═════════════════════════════════════════════════════════════════════════
# Test 4 — ResolutionOption validation
# ═════════════════════════════════════════════════════════════════════════

class TestResolutionOption(unittest.TestCase):

    def test_valid_non_recommended_option(self):
        opt = _make_option("EC_001_OPT_A")
        self.assertFalse(opt.recommended)
        self.assertIsNone(opt.recommendation_reason)

    def test_recommended_requires_reason(self):
        """If recommended=True, recommendation_reason must be set."""
        with self.assertRaises(ValueError) as ctx:
            _make_option("EC_001_OPT_A", recommended=True, reason=None)
        self.assertIn("recommendation_reason", str(ctx.exception))

    def test_recommended_with_reason_valid(self):
        opt = _make_option("EC_001_OPT_A", recommended=True,
                           reason="best fit if shortfall < 200 sqft")
        self.assertTrue(opt.recommended)
        self.assertEqual(opt.recommendation_reason,
                         "best fit if shortfall < 200 sqft")

    def test_preview_mode_no_brief_changes(self):
        """Preview Mode option must have empty requires_brief_change."""
        opt = _make_option("EC_001_OPT_PREVIEW", is_preview=True)
        self.assertEqual(opt.requires_brief_change, ())
        self.assertTrue(opt.is_preview_mode)

    def test_preview_mode_with_brief_changes_rejected(self):
        """Preview sets a flag, not mutations — invariant."""
        bc = _make_brief_change()
        with self.assertRaises(ValueError) as ctx:
            ResolutionOption(
                option_id="EC_X_OPT_PREVIEW",
                description="preview",
                impact_summary="see what your brief looks like",
                cost_impact=None,
                space_impact_sqft=0,
                recommended=False,
                recommendation_reason=None,
                requires_brief_change=(bc,),  # WRONG for Preview
                requires_action=None,
                risk_advisory=None,
                is_preview_mode=True,
            )
        self.assertIn("Preview Mode", str(ctx.exception))

    # ─── B-027 tests — is_different_plot_option field + validation ─────

    def test_resolution_option_is_different_plot_option_defaults_false(self):
        """B-027: default value of is_different_plot_option is False."""
        opt = ResolutionOption(
            option_id="OPT_TEST",
            description="Test",
            impact_summary="X",
            cost_impact=None,
            space_impact_sqft=0,
            recommended=False,
            recommendation_reason=None,
            requires_brief_change=(),
            requires_action=None,
            risk_advisory=None,
        )
        self.assertFalse(opt.is_different_plot_option)
        self.assertFalse(opt.is_preview_mode)

    def test_resolution_option_is_different_plot_option_can_be_set_true(self):
        """B-027: the field accepts True with a valid configuration."""
        opt = ResolutionOption(
            option_id="OPT_TEST",
            description="Different plot",
            impact_summary="Look for a different plot",
            cost_impact=None,
            space_impact_sqft=0,
            recommended=False,
            recommendation_reason=None,
            requires_brief_change=(),
            requires_action=None,
            risk_advisory=None,
            is_different_plot_option=True,
        )
        self.assertTrue(opt.is_different_plot_option)

    def test_resolution_option_mutual_exclusivity_raises(self):
        """B-027 P1: __post_init__ rejects is_preview_mode=True AND
        is_different_plot_option=True together (mutually exclusive)."""
        with self.assertRaises(ValueError) as ctx:
            ResolutionOption(
                option_id="OPT_BAD",
                description="Bad",
                impact_summary="X",
                cost_impact=None,
                space_impact_sqft=0,
                recommended=False,
                recommendation_reason=None,
                requires_brief_change=(),
                requires_action=None,
                risk_advisory=None,
                is_preview_mode=True,
                is_different_plot_option=True,
            )
        self.assertIn("mutually exclusive", str(ctx.exception))

    def test_resolution_option_different_plot_structural_constraints_raise(
        self,
    ):
        """B-027 P6: __post_init__ rejects is_different_plot_option=True
        with non-empty requires_brief_change OR non-None requires_action.

        Different-plot abandons the brief; therefore it cannot modify the
        brief or trigger an in-app action.
        """
        bc = BriefChange(
            field_path="setbacks.front_m",
            operation="SET",
            new_value=2.0,
            description="placeholder",
        )

        # Non-empty requires_brief_change → ValueError
        with self.assertRaises(ValueError) as ctx:
            ResolutionOption(
                option_id="OPT",
                description="d",
                impact_summary="i",
                cost_impact=None,
                space_impact_sqft=0,
                recommended=False,
                recommendation_reason=None,
                requires_brief_change=(bc,),  # NOT ()
                requires_action=None,
                risk_advisory=None,
                is_different_plot_option=True,
            )
        self.assertIn("requires_brief_change must be empty",
                      str(ctx.exception))

        # Non-None requires_action → ValueError
        with self.assertRaises(ValueError) as ctx2:
            ResolutionOption(
                option_id="OPT",
                description="d",
                impact_summary="i",
                cost_impact=None,
                space_impact_sqft=0,
                recommended=False,
                recommendation_reason=None,
                requires_brief_change=(),
                requires_action="EMAIL_CBA_CHECKLIST",  # NOT None
                risk_advisory=None,
                is_different_plot_option=True,
            )
        self.assertIn("requires_action must be None",
                      str(ctx2.exception))


# ═════════════════════════════════════════════════════════════════════════
# Test 5 — ExtremeCase validation
# ═════════════════════════════════════════════════════════════════════════

class TestExtremeCase(unittest.TestCase):

    def test_valid_case_with_two_options(self):
        ec = _make_extreme_case()
        self.assertEqual(ec.case_id, ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)
        self.assertEqual(len(ec.options), 2)

    def test_at_least_two_options_required(self):
        single = (_make_option("EC_001_OPT_A"),)
        with self.assertRaises(ValueError) as ctx:
            _make_extreme_case(options=single)
        self.assertIn("at least 2 options", str(ctx.exception))

    def test_framing_line_required(self):
        """Per critique #8: framing line is the psychological layer."""
        with self.assertRaises(ValueError) as ctx:
            ExtremeCase(
                case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
                category=ExtremeCaseCategory.SPATIAL,
                blocking_gap_ids=("G1",),
                user_facing_message="Plot fits 750.",
                framing_line="",  # WRONG
                resolution_probability=ResolutionProbability.NOT_APPLICABLE,
                options=(_make_option("A"), _make_option("B")),
                detected_at_iteration=0,
            )
        self.assertIn("framing_line", str(ctx.exception))

    def test_preview_mode_must_be_last_option(self):
        """Section 6 UI rule: Preview Mode is always the last option shown."""
        opts_wrong_order = (
            _make_option("EC_001_OPT_PREVIEW", is_preview=True),  # WRONG: first
            _make_option("EC_001_OPT_A"),
        )
        with self.assertRaises(ValueError) as ctx:
            _make_extreme_case(options=opts_wrong_order)
        self.assertIn("LAST option", str(ctx.exception))

    def test_preview_mode_last_option_valid(self):
        opts_correct = (
            _make_option("EC_001_OPT_A"),
            _make_option("EC_001_OPT_B"),
            _make_option("EC_001_OPT_PREVIEW", is_preview=True),
        )
        ec = _make_extreme_case(options=opts_correct)
        self.assertEqual(len(ec.options), 3)
        self.assertTrue(ec.options[-1].is_preview_mode)

    def test_negative_iteration_rejected(self):
        with self.assertRaises(ValueError):
            _make_extreme_case(iteration=-1)


# ═════════════════════════════════════════════════════════════════════════
# Test 6 — ExtremeDecision (Q3 Level B logging invariant)
# ═════════════════════════════════════════════════════════════════════════

class TestExtremeDecision(unittest.TestCase):

    def test_chosen_option_must_be_in_presented_set(self):
        """Q3 Level B: chosen_option_id must appear in presented_options."""
        opt_a = _make_option("EC_001_OPT_A")
        opt_b = _make_option("EC_001_OPT_B")
        with self.assertRaises(ValueError) as ctx:
            ExtremeDecision(
                case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
                chosen_option_id="EC_001_OPT_GHOST",  # not in set!
                chosen_option_description="ghost",
                presented_options=(opt_a, opt_b),
                user_acknowledged_at="2026-04-29T12:00:00Z",
                iteration_index=0,
            )
        self.assertIn("not in presented_options", str(ctx.exception))

    def test_valid_decision(self):
        opt_a = _make_option("EC_001_OPT_A")
        opt_b = _make_option("EC_001_OPT_B")
        d = ExtremeDecision(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            chosen_option_id="EC_001_OPT_A",
            chosen_option_description="option EC_001_OPT_A",
            presented_options=(opt_a, opt_b),
            user_acknowledged_at="2026-04-29T12:00:00Z",
            iteration_index=0,
        )
        self.assertEqual(d.chosen_option_id, "EC_001_OPT_A")
        self.assertEqual(len(d.presented_options), 2)


# ═════════════════════════════════════════════════════════════════════════
# Test 7 — CounterfactualSummary (v0.2.1 critique #5: max 2 alternatives)
# ═════════════════════════════════════════════════════════════════════════

class TestCounterfactualSummary(unittest.TestCase):

    def test_default_framing_line(self):
        cf = CounterfactualSummary(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            chosen_option_id="EC_001_OPT_A",
            chosen_outcome="Saved 120 sqft",
            alternatives=(),
        )
        self.assertEqual(cf.framing_line, DEFAULT_COUNTERFACTUAL_FRAMING)
        self.assertIn("no single 'correct' choice", cf.framing_line)

    def test_max_two_alternatives_enforced(self):
        """v0.2.1 critique #5: hard cap at 2."""
        three_alts = (
            ("OPT_B", "Option B", "would have done X"),
            ("OPT_C", "Option C", "would have done Y"),
            ("OPT_D", "Option D", "would have done Z"),
        )
        with self.assertRaises(ValueError) as ctx:
            CounterfactualSummary(
                case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
                chosen_option_id="EC_001_OPT_A",
                chosen_outcome="Saved 120 sqft",
                alternatives=three_alts,
            )
        self.assertIn("max 2", str(ctx.exception))

    def test_two_alternatives_ok(self):
        two_alts = (
            ("OPT_B", "Option B", "would have done X"),
            ("OPT_C", "Option C", "would have done Y"),
        )
        cf = CounterfactualSummary(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            chosen_option_id="EC_001_OPT_A",
            chosen_outcome="Saved 120 sqft",
            alternatives=two_alts,
        )
        self.assertEqual(len(cf.alternatives), 2)

    def test_alternative_tuple_shape_enforced(self):
        """Each alternative must be (option_id, description, would_have)."""
        with self.assertRaises(ValueError) as ctx:
            CounterfactualSummary(
                case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
                chosen_option_id="EC_001_OPT_A",
                chosen_outcome="Saved 120 sqft",
                alternatives=(("OPT_B", "only two fields"),),  # missing third
            )
        self.assertIn("(option_id, description, would_have_text)",
                      str(ctx.exception))


# ═════════════════════════════════════════════════════════════════════════
# Test 8 — PreflightSummary (v0.2.1 critique #2 + #4)
# ═════════════════════════════════════════════════════════════════════════

class TestPreflightSummary(unittest.TestCase):

    def test_valid_summary(self):
        ps = PreflightSummary(
            total_blocker_count=3,
            blocker_categories=(
                ExtremeCaseCategory.LEGAL,
                ExtremeCaseCategory.SPATIAL,
            ),
            summary_message="We found 3 constraints affecting your plan.",
        )
        self.assertEqual(ps.total_blocker_count, 3)
        self.assertIsNone(ps.early_plot_hint)  # default

    def test_with_early_plot_hint(self):
        """Per critique #4: early hint surfaces when severe single-EC fires."""
        ps = PreflightSummary(
            total_blocker_count=1,
            blocker_categories=(ExtremeCaseCategory.SITE,),
            summary_message="We found 1 constraint affecting your plan.",
            early_plot_hint="Heads up: this plot may not be the right fit.",
        )
        self.assertIsNotNone(ps.early_plot_hint)

    def test_zero_blocker_count_rejected(self):
        """Preflight only built when blockers exist."""
        with self.assertRaises(ValueError) as ctx:
            PreflightSummary(
                total_blocker_count=0,
                blocker_categories=(),
                summary_message="",
            )
        self.assertIn(">= 1", str(ctx.exception))


# ═════════════════════════════════════════════════════════════════════════
# Test 9 — PreviewModeAcknowledgment (v0.2.1 critique #1: CRITICAL)
# ═════════════════════════════════════════════════════════════════════════

class TestPreviewModeAcknowledgment(unittest.TestCase):

    def test_all_three_fields_required(self):
        """Audit invariant — all three fields are mandatory."""
        with self.assertRaises(ValueError):
            PreviewModeAcknowledgment(
                user_acknowledged_at="",
                acknowledgment_text="I understand...",
                user_session_id="sess-123",
            )
        with self.assertRaises(ValueError):
            PreviewModeAcknowledgment(
                user_acknowledged_at="2026-04-29T12:00:00Z",
                acknowledgment_text="",
                user_session_id="sess-123",
            )
        with self.assertRaises(ValueError):
            PreviewModeAcknowledgment(
                user_acknowledged_at="2026-04-29T12:00:00Z",
                acknowledgment_text="I understand...",
                user_session_id="",
            )

    def test_valid_acknowledgment(self):
        ack = PreviewModeAcknowledgment(
            user_acknowledged_at="2026-04-29T12:00:00Z",
            acknowledgment_text=(
                "I understand this cannot be legally approved or built as-is."
            ),
            user_session_id="sess-abc-123",
        )
        self.assertEqual(ack.user_session_id, "sess-abc-123")


# ═════════════════════════════════════════════════════════════════════════
# Test 10 — ExtremeDecisionLog
# ═════════════════════════════════════════════════════════════════════════

class TestExtremeDecisionLog(unittest.TestCase):

    def test_aborted_requires_reason(self):
        with self.assertRaises(ValueError) as ctx:
            ExtremeDecisionLog(
                started_at="2026-04-29T12:00:00Z",
                completed_at=None,
                decisions=(),
                iterations_used=2,
                aborted=True,
                abort_reason=None,  # WRONG
            )
        self.assertIn("abort_reason", str(ctx.exception))

    def test_reason_without_aborted_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            ExtremeDecisionLog(
                started_at="2026-04-29T12:00:00Z",
                completed_at="2026-04-29T12:30:00Z",
                decisions=(),
                iterations_used=2,
                aborted=False,
                abort_reason="USER_ABORTED",  # WRONG: inconsistent
            )
        self.assertIn("inconsistent", str(ctx.exception))

    def test_clean_finish_log(self):
        log = ExtremeDecisionLog(
            started_at="2026-04-29T12:00:00Z",
            completed_at="2026-04-29T12:30:00Z",
            decisions=(),
            iterations_used=3,
            aborted=False,
        )
        self.assertFalse(log.aborted)
        self.assertIsNone(log.abort_reason)


# ═════════════════════════════════════════════════════════════════════════
# Test 11 — ResolvedBrief mode-specific invariants
# ═════════════════════════════════════════════════════════════════════════

class TestResolvedBrief(unittest.TestCase):
    """The most invariant-heavy class. Mode (BUILDABLE vs PREVIEW) drives
    which fields must/must-not be populated.
    """

    def _make_log(self, aborted=False, reason=None):
        return ExtremeDecisionLog(
            started_at="2026-04-29T12:00:00Z",
            completed_at="2026-04-29T12:30:00Z" if not aborted else None,
            decisions=(),
            iterations_used=1,
            aborted=aborted,
            abort_reason=reason,
        )

    def _make_ack(self):
        return PreviewModeAcknowledgment(
            user_acknowledged_at="2026-04-29T12:30:00Z",
            acknowledgment_text="I understand this is not buildable.",
            user_session_id="sess-1",
        )

    def test_buildable_clean_minimal(self):
        rb = ResolvedBrief(
            original_brief="brief",
            revised_brief="brief",
            decision_log=self._make_log(),
            final_feasibility="gap_analysis",
            mode=BriefMode.BUILDABLE,
            is_layout_ready=True,
            counterfactuals=(),
            unresolved_blockers=(),
            relaxed_constraints=(),
        )
        self.assertEqual(rb.mode, BriefMode.BUILDABLE)
        self.assertTrue(rb.is_layout_ready)

    def test_buildable_must_not_have_unresolved_blockers(self):
        ec = _make_extreme_case()
        with self.assertRaises(ValueError) as ctx:
            ResolvedBrief(
                original_brief="brief",
                revised_brief="brief",
                decision_log=self._make_log(),
                final_feasibility="gap_analysis",
                mode=BriefMode.BUILDABLE,
                is_layout_ready=True,
                counterfactuals=(),
                unresolved_blockers=(ec,),  # WRONG for BUILDABLE
                relaxed_constraints=(),
            )
        self.assertIn("BUILDABLE must not have", str(ctx.exception))

    def test_buildable_must_not_have_preview_acknowledgment(self):
        with self.assertRaises(ValueError) as ctx:
            ResolvedBrief(
                original_brief="brief",
                revised_brief="brief",
                decision_log=self._make_log(),
                final_feasibility="gap_analysis",
                mode=BriefMode.BUILDABLE,
                is_layout_ready=True,
                counterfactuals=(),
                unresolved_blockers=(),
                relaxed_constraints=(),
                preview_mode_acknowledgment=self._make_ack(),  # WRONG
            )
        self.assertIn("BUILDABLE must not have", str(ctx.exception))

    def test_preview_requires_unresolved_blockers(self):
        with self.assertRaises(ValueError) as ctx:
            ResolvedBrief(
                original_brief="brief",
                revised_brief="brief",
                decision_log=self._make_log(
                    aborted=True, reason="USER_CHOSE_PREVIEW_MODE"),
                final_feasibility="gap_analysis",
                mode=BriefMode.PREVIEW,
                is_layout_ready=True,
                counterfactuals=(),
                unresolved_blockers=(),  # WRONG for PREVIEW
                relaxed_constraints=("FAR",),
                preview_mode_acknowledgment=self._make_ack(),
            )
        self.assertIn("unresolved_blockers", str(ctx.exception))

    def test_preview_requires_relaxed_constraints(self):
        ec = _make_extreme_case()
        with self.assertRaises(ValueError) as ctx:
            ResolvedBrief(
                original_brief="brief",
                revised_brief="brief",
                decision_log=self._make_log(
                    aborted=True, reason="USER_CHOSE_PREVIEW_MODE"),
                final_feasibility="gap_analysis",
                mode=BriefMode.PREVIEW,
                is_layout_ready=True,
                counterfactuals=(),
                unresolved_blockers=(ec,),
                relaxed_constraints=(),  # WRONG for PREVIEW
                preview_mode_acknowledgment=self._make_ack(),
            )
        self.assertIn("relaxed_constraints", str(ctx.exception))

    def test_preview_requires_acknowledgment(self):
        """v0.2.1 critique #1 CRITICAL: Preview Mode REQUIRES ack."""
        ec = _make_extreme_case()
        with self.assertRaises(ValueError) as ctx:
            ResolvedBrief(
                original_brief="brief",
                revised_brief="brief",
                decision_log=self._make_log(
                    aborted=True, reason="USER_CHOSE_PREVIEW_MODE"),
                final_feasibility="gap_analysis",
                mode=BriefMode.PREVIEW,
                is_layout_ready=True,
                counterfactuals=(),
                unresolved_blockers=(ec,),
                relaxed_constraints=("FAR",),
                preview_mode_acknowledgment=None,  # WRONG
            )
        self.assertIn("preview_mode_acknowledgment", str(ctx.exception))

    def test_preview_implies_layout_ready(self):
        """PREVIEW mode is a valid output, so is_layout_ready must be True."""
        ec = _make_extreme_case()
        with self.assertRaises(ValueError) as ctx:
            ResolvedBrief(
                original_brief="brief",
                revised_brief="brief",
                decision_log=self._make_log(
                    aborted=True, reason="USER_CHOSE_PREVIEW_MODE"),
                final_feasibility="gap_analysis",
                mode=BriefMode.PREVIEW,
                is_layout_ready=False,  # WRONG
                counterfactuals=(),
                unresolved_blockers=(ec,),
                relaxed_constraints=("FAR",),
                preview_mode_acknowledgment=self._make_ack(),
            )
        self.assertIn("PREVIEW always implies", str(ctx.exception))

    def test_aborted_with_layout_ready_only_for_preview(self):
        """USER_ABORTED + is_layout_ready=True is inconsistent."""
        with self.assertRaises(ValueError) as ctx:
            ResolvedBrief(
                original_brief="brief",
                revised_brief="brief",
                decision_log=self._make_log(
                    aborted=True, reason="USER_ABORTED"),
                final_feasibility="gap_analysis",
                mode=BriefMode.BUILDABLE,
                is_layout_ready=True,  # WRONG with USER_ABORTED
                counterfactuals=(),
                unresolved_blockers=(),
                relaxed_constraints=(),
            )
        self.assertIn("inconsistent", str(ctx.exception))

    def test_valid_preview_mode(self):
        """End-to-end valid PREVIEW ResolvedBrief."""
        ec = _make_extreme_case()
        rb = ResolvedBrief(
            original_brief="brief",
            revised_brief="brief",
            decision_log=self._make_log(
                aborted=True, reason="USER_CHOSE_PREVIEW_MODE"),
            final_feasibility="gap_analysis",
            mode=BriefMode.PREVIEW,
            is_layout_ready=True,
            counterfactuals=(),
            unresolved_blockers=(ec,),
            relaxed_constraints=("FAR", "GROUND_COVERAGE"),
            preview_mode_acknowledgment=self._make_ack(),
        )
        self.assertEqual(rb.mode, BriefMode.PREVIEW)
        self.assertTrue(rb.is_layout_ready)
        self.assertEqual(len(rb.unresolved_blockers), 1)


# ═════════════════════════════════════════════════════════════════════════
# Test 12 — BriefChangeIntegrityError + classification + immutability
# ═════════════════════════════════════════════════════════════════════════

class TestBriefChangeIntegrityError(unittest.TestCase):

    def test_default_classification(self):
        err = BriefChangeIntegrityError("oops")
        self.assertEqual(err.classify(), "UNKNOWN")
        self.assertEqual(err.context, {})

    def test_with_classification_and_context(self):
        err = BriefChangeIntegrityError(
            "Bedroom count below min",
            classification="BEDROOM_COUNT_BELOW_MIN",
            context={"resulting_count": 1, "stated_min": 2},
        )
        self.assertEqual(err.classify(), "BEDROOM_COUNT_BELOW_MIN")
        self.assertEqual(err.context["resulting_count"], 1)


class TestImmutability(unittest.TestCase):
    """All dataclasses use frozen=True. Verify mutation is blocked."""

    def test_brief_change_immutable(self):
        bc = _make_brief_change()
        with self.assertRaises(Exception):  # FrozenInstanceError
            bc.field_path = "rooms.bath_1"

    def test_extreme_case_immutable(self):
        ec = _make_extreme_case()
        with self.assertRaises(Exception):
            ec.detected_at_iteration = 99


class TestDomainTypeNamesRegistration(unittest.TestCase):
    """v0.7.1 ComponentContract enforcement requires all domain types
    to be listed in EXTREME_CASE_DOMAIN_TYPE_NAMES.
    """

    def test_all_fifteen_types_registered(self):
        # 5 enums + 10 dataclasses = 15
        self.assertEqual(len(EXTREME_CASE_DOMAIN_TYPE_NAMES), 15)
        expected_enums = {
            "ExtremeCaseCategory", "ExtremeCaseId", "ResolutionProbability",
            "BriefMode", "CostConfidence",
        }
        expected_dataclasses = {
            "BriefChange", "CostImpact", "ResolutionOption", "ExtremeCase",
            "ExtremeDecision", "ExtremeDecisionLog", "CounterfactualSummary",
            "PreflightSummary", "PreviewModeAcknowledgment", "ResolvedBrief",
        }
        registered = set(EXTREME_CASE_DOMAIN_TYPE_NAMES)
        self.assertTrue(expected_enums.issubset(registered))
        self.assertTrue(expected_dataclasses.issubset(registered))


if __name__ == "__main__":
    unittest.main()
