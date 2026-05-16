"""Tests for Component 3a Session 5 — preflight summary builder.

Per locked S5 SPEC v1.0 § 7.2 — verifies build_preflight_summary:
  - singular phrasing for 1 case (non-critical)
  - P3 critical singular phrasing for 1 critical case
  - multi-blocker phrasing without critical breakdown
  - P3 multi-blocker phrasing WITH critical breakdown
  - early_plot_hint = None when no triggering condition
  - P2 hint with one reason inlined (EC-006 only)
  - P2 hint with two reasons joined with " and "
  - P2 hint with three reasons joined with ", and "
  - dedup + first-seen order preserved for categories
  - classify_case_severity returns correct class for each EC

Replicates fixture builders inline (per Q10 — test isolation, not
import).
"""
import unittest

from buildemup.domain.extreme_case import (
    ExtremeCase,
    ExtremeCaseCategory,
    ExtremeCaseId,
    PreflightSummary,
    ResolutionOption,
    ResolutionProbability,
    BriefChange,
)
from buildemup.components.c03a.preflight import (
    build_preflight_summary,
    classify_case_severity,
    _unique_categories_preserving_order,
    _format_category_list,
    _build_early_plot_hint,
    _build_severity_aware_message,
)


# ─────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────

# Map case_id → category (mirrors S2/S3/S4 test fixture pattern)
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


def _placeholder_options() -> tuple[ResolutionOption, ...]:
    """Build a 2-option placeholder set for ExtremeCase fixture
    construction (case __post_init__ requires ≥2 options)."""
    rbc = (
        BriefChange(
            field_path="setbacks.front_m", operation="INCREMENT",
            new_value=0.0, description="placeholder",
        ),
    )
    return (
        ResolutionOption(
            option_id="OPT_A", description="A", impact_summary="X",
            cost_impact=None, space_impact_sqft=0, recommended=False,
            recommendation_reason=None, requires_brief_change=rbc,
            requires_action=None, risk_advisory=None,
        ),
        ResolutionOption(
            option_id="OPT_B", description="B", impact_summary="Y",
            cost_impact=None, space_impact_sqft=0, recommended=False,
            recommendation_reason=None, requires_brief_change=rbc,
            requires_action=None, risk_advisory=None,
        ),
    )


def _case(
    case_id: ExtremeCaseId,
    *,
    resolution_probability: ResolutionProbability = (
        ResolutionProbability.NOT_APPLICABLE
    ),
) -> ExtremeCase:
    """Build a minimal ExtremeCase fixture."""
    return ExtremeCase(
        case_id=case_id,
        category=_EC_TO_CATEGORY[case_id],
        blocking_gap_ids=(),
        user_facing_message="test message",
        framing_line="test framing",
        resolution_probability=resolution_probability,
        options=_placeholder_options(),
        detected_at_iteration=0,
    )


# ─────────────────────────────────────────────────────────────────
# Tests — public API behaviour (§ 7.2 tests 1-9)
# ─────────────────────────────────────────────────────────────────

class TestBuildPreflightSummary(unittest.TestCase):

    # --- 1: 1 non-critical case → singular phrasing ----------------
    def test_preflight_single_case_singular_message(self):
        """1 non-critical case → 'We found 1 constraint... Let's work
        through it.'
        """
        cases = (_case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),)
        result = build_preflight_summary(cases)
        self.assertIsInstance(result, PreflightSummary)
        self.assertEqual(result.total_blocker_count, 1)
        self.assertEqual(
            result.summary_message,
            "We found 1 constraint affecting your plan. "
            "Let's work through it.",
        )
        self.assertIsNone(result.early_plot_hint)

    # --- 2: 1 critical case → P3 hard-blocker phrasing -------------
    def test_preflight_single_critical_case_message(self):
        """P3: 1 critical case → '1 hard blocker...' phrasing."""
        cases = (
            _case(ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE),
        )
        result = build_preflight_summary(cases)
        self.assertIn("1 hard blocker", result.summary_message)
        self.assertIn("may not be resolvable", result.summary_message)
        # And the early-plot-hint fires for EC-006
        self.assertIsNotNone(result.early_plot_hint)

    # --- 3: multi-case all moderate → standard plural phrasing -----
    def test_preflight_multi_case_plural_message_with_categories(self):
        """3 moderate cases, 2 categories → 'We found 3 constraints...
        Fixing one may affect the others.'
        """
        cases = (
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
            _case(ExtremeCaseId.EC_004_FAR_EXCEEDED),
            _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW),
        )
        result = build_preflight_summary(cases)
        self.assertIn("We found 3 constraints", result.summary_message)
        self.assertIn(
            "Fixing one may affect the others", result.summary_message,
        )
        # No critical-count clause when no critical cases
        self.assertNotIn("hard blocker", result.summary_message)
        self.assertIsNone(result.early_plot_hint)

    # --- 4: P3 multi-case with critical split ----------------------
    def test_preflight_multi_case_with_critical_split(self):
        """P3: 3 cases, 1 critical + 2 moderate → '1 is a hard blocker;
        the others are trade-offs'.
        """
        cases = (
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
            _case(ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE),
            _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW),
        )
        result = build_preflight_summary(cases)
        self.assertIn("We found 3 constraints", result.summary_message)
        self.assertIn(
            "1 is a hard blocker that may not be resolvable",
            result.summary_message,
        )
        self.assertIn(
            "the others are trade-offs", result.summary_message,
        )

    # --- 5: no triggering condition → early_plot_hint is None ------
    def test_preflight_no_early_plot_hint_when_none_severe(self):
        """Only EC-001 + EC-008 → early_plot_hint is None."""
        cases = (
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
            _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW),
        )
        result = build_preflight_summary(cases)
        self.assertIsNone(result.early_plot_hint)

    # --- 6: P2 hint with one reason (EC-006) -----------------------
    def test_preflight_early_plot_hint_one_reason_ec006(self):
        """P2: only EC-006 in tuple → hint contains the envelope reason
        exactly once.
        """
        cases = (
            _case(ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE),
        )
        result = build_preflight_summary(cases)
        self.assertIsNotNone(result.early_plot_hint)
        hint = result.early_plot_hint
        self.assertIn("buildable envelope is below typical", hint)
        # Other reasons absent
        self.assertNotIn("low probability of resolution", hint)
        self.assertNotIn("plot is narrow", hint)

    # --- 7: P2 hint with two reasons joined with " and " -----------
    def test_preflight_early_plot_hint_two_reasons_joined(self):
        """P2: EC-002 + EC-010 LOW → hint contains both reasons joined
        with ' and '.
        """
        cases = (
            _case(ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT),
            _case(
                ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
                resolution_probability=ResolutionProbability.LOW,
            ),
        )
        result = build_preflight_summary(cases)
        hint = result.early_plot_hint
        self.assertIsNotNone(hint)
        self.assertIn("low probability of resolution", hint)
        self.assertIn("plot is narrow", hint)
        # Joined with " and " (not ", and ")
        # Verify both reasons are connected by an "and" with no comma
        # before it
        self.assertNotIn(", and", hint)
        self.assertIn(" and ", hint)

    # --- 8: P2 hint with three reasons joined with ", and " --------
    def test_preflight_early_plot_hint_three_reasons_joined(self):
        """P2: EC-006 + EC-010 LOW + EC-002 → hint contains all three
        joined with ', and '.
        """
        cases = (
            _case(ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE),
            _case(
                ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
                resolution_probability=ResolutionProbability.LOW,
            ),
            _case(ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT),
        )
        result = build_preflight_summary(cases)
        hint = result.early_plot_hint
        self.assertIsNotNone(hint)
        self.assertIn("buildable envelope is below typical", hint)
        self.assertIn("low probability of resolution", hint)
        self.assertIn("plot is narrow", hint)
        # Three reasons → Oxford-like joining
        self.assertIn(", and", hint)

    # --- 9: dedup + first-seen order ------------------------------
    def test_preflight_categories_dedup_preserve_order(self):
        """Cases with duplicate categories → unique_categories has each
        once, in first-seen order.
        """
        cases = (
            _case(ExtremeCaseId.EC_004_FAR_EXCEEDED),       # LEGAL
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),  # SPATIAL
            _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED),    # LEGAL (dup)
        )
        result = build_preflight_summary(cases)
        # First seen → LEGAL, then SPATIAL; second LEGAL deduped
        self.assertEqual(len(result.blocker_categories), 2)
        self.assertEqual(
            result.blocker_categories,
            (ExtremeCaseCategory.LEGAL, ExtremeCaseCategory.SPATIAL),
        )


# ─────────────────────────────────────────────────────────────────
# Tests — classify_case_severity behaviour (§ 7.2 test 10, Q11)
# ─────────────────────────────────────────────────────────────────

class TestClassifySeverity(unittest.TestCase):
    """Q11: severity classification rules."""

    def testclassify_case_severity_returns_correct_class(self):
        """EC-006 → critical, EC-002 → critical, EC-010 LOW → critical,
        EC-010 HIGH → moderate, EC-001 → moderate, EC-008 → moderate.
        """
        ec006 = _case(
            ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
        )
        ec002 = _case(ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT)
        ec010_low = _case(
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
            resolution_probability=ResolutionProbability.LOW,
        )
        ec010_high = _case(
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
            resolution_probability=ResolutionProbability.HIGH,
        )
        ec010_medium = _case(
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
            resolution_probability=ResolutionProbability.MEDIUM,
        )
        ec001 = _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE)
        ec008 = _case(
            ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW,
        )

        self.assertEqual(classify_case_severity(ec006), "critical")
        self.assertEqual(classify_case_severity(ec002), "critical")
        self.assertEqual(classify_case_severity(ec010_low), "critical")
        self.assertEqual(classify_case_severity(ec010_high), "moderate")
        self.assertEqual(classify_case_severity(ec010_medium), "moderate")
        self.assertEqual(classify_case_severity(ec001), "moderate")
        self.assertEqual(classify_case_severity(ec008), "moderate")


# ─────────────────────────────────────────────────────────────────
# Tests — helper functions (extra coverage)
# ─────────────────────────────────────────────────────────────────

class TestPreflightHelpers(unittest.TestCase):

    def test_format_category_list_one_item(self):
        result = _format_category_list((ExtremeCaseCategory.SPATIAL,))
        self.assertEqual(result, "spatial")

    def test_format_category_list_two_items(self):
        result = _format_category_list(
            (ExtremeCaseCategory.SPATIAL, ExtremeCaseCategory.LEGAL),
        )
        self.assertEqual(result, "spatial and legal")

    def test_format_category_list_three_items(self):
        result = _format_category_list((
            ExtremeCaseCategory.SPATIAL,
            ExtremeCaseCategory.LEGAL,
            ExtremeCaseCategory.BUDGET,
        ))
        self.assertEqual(result, "spatial, legal, and budget")

    def test_format_category_list_empty_returns_empty(self):
        result = _format_category_list(())
        self.assertEqual(result, "")

    def test_unique_categories_preserves_first_seen_order(self):
        cases = (
            _case(ExtremeCaseId.EC_004_FAR_EXCEEDED),       # LEGAL
            _case(ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW),  # BUDGET
            _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED),    # LEGAL (dup)
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),  # SPATIAL
        )
        result = _unique_categories_preserving_order(cases)
        self.assertEqual(
            result,
            (
                ExtremeCaseCategory.LEGAL,
                ExtremeCaseCategory.BUDGET,
                ExtremeCaseCategory.SPATIAL,
            ),
        )

    def test_build_early_plot_hint_none_when_no_triggers(self):
        cases = (
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
            _case(ExtremeCaseId.EC_004_FAR_EXCEEDED),
        )
        result = _build_early_plot_hint(cases)
        self.assertIsNone(result)

    def test_severity_aware_message_all_cases_critical(self):
        """Edge case: every case is critical (no 'others')."""
        msg = _build_severity_aware_message(
            total=2,
            categories=(
                ExtremeCaseCategory.LEGAL, ExtremeCaseCategory.SITE,
            ),
            critical_count=2,
        )
        self.assertIn("All 2 are hard blockers", msg)
        # "all critical" branch does NOT use the "the others are trade-offs"
        # clause — verify by checking the specific phrase, not just
        # "the others" (which appears in the standard "Fixing one may
        # affect the others." sentence).
        self.assertNotIn("the others are trade-offs", msg)
        self.assertNotIn("the other is a trade-off", msg)


# ─────────────────────────────────────────────────────────────────────
# B-027 P7 — backward-compat alias verification (post-code-critique #8)
# ─────────────────────────────────────────────────────────────────────

class TestB027ClassifyCaseSeverityAlias(unittest.TestCase):
    """B-027 P7: the deprecation wrapper _classify_severity emits a
    DeprecationWarning when called and returns the same value as
    classify_case_severity.

    Post-code-critique-round-2 D8: the previous pure-alias form was
    silent. The wrapper form makes any remaining callers loud (visible
    in test output / logs) so the TODO removal is easier to trigger
    once S6 ships.
    """

    def test_classify_case_severity_wrapper_emits_deprecation_warning(self):
        """The deprecated wrapper emits DeprecationWarning when called."""
        import warnings
        from buildemup.components.c03a.preflight import _classify_severity

        # Build a sample case to exercise the wrapper
        ec006 = _case(
            ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _classify_severity(ec006)
            self.assertEqual(len(caught), 1)
            self.assertTrue(
                issubclass(caught[0].category, DeprecationWarning)
            )
            self.assertIn(
                "_classify_severity is deprecated", str(caught[0].message)
            )

    def test_classify_case_severity_wrapper_returns_same_value(self):
        """The wrapper returns the same severity classification as the
        public function for the same input.
        """
        import warnings
        from buildemup.components.c03a.preflight import (
            classify_case_severity,
            _classify_severity,
        )
        # Try several cases to exercise both critical and moderate paths
        cases_to_check = [
            _case(ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE),
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
            _case(
                ExtremeCaseId.EC_010_APPROVAL_BLOCKER,
                resolution_probability=ResolutionProbability.LOW,
            ),
        ]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for c in cases_to_check:
                self.assertEqual(
                    _classify_severity(c),
                    classify_case_severity(c),
                    f"Wrapper output differs from public function for "
                    f"{c.case_id.value}",
                )


if __name__ == "__main__":
    unittest.main()
