"""Tests for Component 3a Session 5 — counterfactual builder.

Per locked S5 SPEC v1.0 § 7.1 — verifies build_counterfactual:
  - 2-alternative cap enforced (3 in → 2 out)
  - empty alternatives when only chosen option present
  - recommended sorts before non-recommended
  - distance tie-break when both unrecommended
  - Preview Mode rendered with neutral special-case phrasing
  - chosen_outcome matches chosen.impact_summary
  - default framing line used
  - P1: acronym preservation in _format_would_have
  - P1: normal Title Case lowercasing in _format_would_have

Replicates fixture builders inline (per Q10 — test isolation, not
import).
"""
import unittest

from buildemup.domain.extreme_case import (
    BriefChange,
    CounterfactualSummary,
    DEFAULT_COUNTERFACTUAL_FRAMING,
    ExtremeCaseId,
    ExtremeDecision,
    ResolutionOption,
)
from buildemup.components.c03a.counterfactual import (
    build_counterfactual,
    _format_would_have,
)


# ─────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────

def _option(
    *,
    option_id: str,
    description: str = "Test option",
    impact_summary: str = "Drops 1 thing, saves something",
    space_impact_sqft: int = 0,
    recommended: bool = False,
    recommendation_reason: str = None,
    is_preview_mode: bool = False,
) -> ResolutionOption:
    """Build a ResolutionOption fixture.

    Default: non-Preview, non-recommended, with a placeholder BriefChange
    so __post_init__ accepts it. (Preview Mode rejects non-empty
    requires_brief_change so that branch uses an empty tuple.)
    """
    if is_preview_mode:
        rbc = ()
    else:
        rbc = (
            BriefChange(
                field_path="setbacks.front_m",
                operation="INCREMENT",
                new_value=0.0,
                description="placeholder for fixture",
            ),
        )

    if recommended and recommendation_reason is None:
        recommendation_reason = "test recommendation reason"

    return ResolutionOption(
        option_id=option_id,
        description=description,
        impact_summary=impact_summary,
        cost_impact=None,
        space_impact_sqft=space_impact_sqft,
        recommended=recommended,
        recommendation_reason=recommendation_reason,
        requires_brief_change=rbc,
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=is_preview_mode,
    )


def _decision(
    chosen_option_id: str,
    presented_options: tuple[ResolutionOption, ...],
) -> ExtremeDecision:
    """Build an ExtremeDecision fixture pointing at one of the options."""
    chosen_desc = next(
        o.description for o in presented_options
        if o.option_id == chosen_option_id
    )
    return ExtremeDecision(
        case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
        chosen_option_id=chosen_option_id,
        chosen_option_description=chosen_desc,
        presented_options=presented_options,
        user_acknowledged_at="2026-04-30T10:00:00Z",
        iteration_index=0,
    )


# ─────────────────────────────────────────────────────────────────
# Tests — public API behaviour (§ 7.1 tests 1-7)
# ─────────────────────────────────────────────────────────────────

class TestBuildCounterfactual(unittest.TestCase):

    # --- 1: 3 rejected → 2 alternatives (cap enforced) -------------
    def test_counterfactual_basic_three_rejected_options(self):
        """3 rejected options → exactly 2 alternatives in result."""
        opts = (
            _option(option_id="OPT_A", description="Drop balcony",
                    space_impact_sqft=-15),
            _option(option_id="OPT_B", description="Reduce kitchen",
                    space_impact_sqft=-30),
            _option(option_id="OPT_C", description="Add floor",
                    space_impact_sqft=400),
            _option(option_id="OPT_D", description="Accept NBC mins",
                    space_impact_sqft=-5),
        )
        decision = _decision("OPT_A", opts)
        result = build_counterfactual(decision)
        self.assertIsInstance(result, CounterfactualSummary)
        self.assertEqual(len(result.alternatives), 2)
        # The alternatives are NOT the chosen option
        alt_ids = {alt[0] for alt in result.alternatives}
        self.assertNotIn("OPT_A", alt_ids)

    # --- 2: only chosen → empty alternatives -----------------------
    def test_counterfactual_with_only_chosen_returns_empty_alternatives(self):
        """presented_options has just the chosen → alternatives=().

        Defensive case — ExtremeCase.__post_init__ requires ≥2 options
        per case, so in practice presented_options always has ≥2 entries.
        But handle it cleanly if it ever happens.
        """
        opts = (
            _option(option_id="OPT_A", description="Solo option"),
        )
        decision = _decision("OPT_A", opts)
        result = build_counterfactual(decision)
        self.assertEqual(result.alternatives, ())

    # --- 3: recommended sorts first --------------------------------
    def test_counterfactual_recommended_alternative_sorts_first(self):
        """One non-recommended + one recommended → recommended is alternatives[0]."""
        opts = (
            _option(option_id="CHOSEN", description="Chosen",
                    space_impact_sqft=0),
            _option(option_id="NOT_REC", description="Not recommended",
                    space_impact_sqft=-100, recommended=False),
            _option(option_id="REC", description="Recommended",
                    space_impact_sqft=-10, recommended=True),
        )
        decision = _decision("CHOSEN", opts)
        result = build_counterfactual(decision)
        # First alternative is the recommended one
        self.assertEqual(result.alternatives[0][0], "REC")

    # --- 4: distance tie-break when both unrecommended -------------
    def test_counterfactual_distance_tiebreak_when_both_unrecommended(self):
        """Two non-recommended, different space_impacts → larger-distance
        ranks first.
        """
        opts = (
            _option(option_id="CHOSEN", description="Chosen",
                    space_impact_sqft=0),
            _option(option_id="SMALL_DIST", description="Small impact",
                    space_impact_sqft=10),
            _option(option_id="BIG_DIST", description="Big impact",
                    space_impact_sqft=500),
        )
        decision = _decision("CHOSEN", opts)
        result = build_counterfactual(decision)
        self.assertEqual(result.alternatives[0][0], "BIG_DIST")
        self.assertEqual(result.alternatives[1][0], "SMALL_DIST")

    # --- 5: Preview Mode neutral phrasing ---------------------------
    def test_counterfactual_preview_mode_alternative_uses_neutral_phrasing(self):
        """Preview Mode rejected → alternatives string contains
        'watermarked' + 'not buildable'.
        """
        opts = (
            _option(option_id="CHOSEN", description="Chosen real",
                    space_impact_sqft=-10),
            _option(option_id="PREVIEW",
                    description="Preview Mode (see watermarked layout)",
                    impact_summary="Shows watermarked dream layout",
                    is_preview_mode=True,
                    space_impact_sqft=0),
        )
        decision = _decision("CHOSEN", opts)
        result = build_counterfactual(decision)
        self.assertEqual(len(result.alternatives), 1)
        preview_alt = result.alternatives[0]
        self.assertEqual(preview_alt[0], "PREVIEW")
        # The "would have" string must mention key Preview Mode aspects
        would_have = preview_alt[2]
        self.assertIn("watermarked", would_have)
        self.assertIn("not buildable", would_have)

    # --- 6: chosen_outcome matches chosen.impact_summary -----------
    def test_counterfactual_chosen_outcome_matches_chosen_impact_summary(self):
        """result.chosen_outcome == chosen.impact_summary."""
        opts = (
            _option(option_id="CHOSEN", description="Chosen",
                    impact_summary="Drops 1 balcony, saves 18 sqft",
                    space_impact_sqft=-18),
            _option(option_id="OTHER", description="Other",
                    space_impact_sqft=-10),
        )
        decision = _decision("CHOSEN", opts)
        result = build_counterfactual(decision)
        self.assertEqual(
            result.chosen_outcome, "Drops 1 balcony, saves 18 sqft",
        )

    # --- 7: default framing line ----------------------------------
    def test_counterfactual_uses_default_framing_line(self):
        """result.framing_line == DEFAULT_COUNTERFACTUAL_FRAMING."""
        opts = (
            _option(option_id="CHOSEN", description="Chosen",
                    space_impact_sqft=0),
            _option(option_id="OTHER", description="Other",
                    space_impact_sqft=-10),
        )
        decision = _decision("CHOSEN", opts)
        result = build_counterfactual(decision)
        self.assertEqual(result.framing_line, DEFAULT_COUNTERFACTUAL_FRAMING)


# ─────────────────────────────────────────────────────────────────
# Tests — _format_would_have casing behaviour (§ 7.1 tests 8-9, P1)
# ─────────────────────────────────────────────────────────────────

class TestFormatWouldHaveCasing(unittest.TestCase):
    """P1 — Drawback 2 from critique round 1: acronym preservation."""

    # --- 8: acronyms preserved ------------------------------------
    def test_format_would_have_preserves_acronyms(self):
        """impact_summary starting with 'TNCDBR ...' stays
        'would have TNCDBR ...' (NOT 'tNCDBR' or 'tncdbr').
        """
        opt = _option(
            option_id="OPT",
            description="Variance request",
            impact_summary="TNCDBR variance required",
        )
        result = _format_would_have(opt)
        self.assertEqual(result, "would have TNCDBR variance required")
        self.assertNotIn("tNCDBR", result)
        self.assertNotIn("tncdbr", result)

    # --- 9: normal Title Case is lowercased ------------------------
    def test_format_would_have_lowercases_normal_titlecase(self):
        """'Drops 1 balcony, saves 18 sqft' → 'would have drops 1 ...'"""
        opt = _option(
            option_id="OPT",
            description="Drop balcony",
            impact_summary="Drops 1 balcony, saves 18 sqft",
        )
        result = _format_would_have(opt)
        self.assertEqual(
            result, "would have drops 1 balcony, saves 18 sqft",
        )

    # --- 9b: edge case — single-letter title -----------------------
    def test_format_would_have_handles_single_char_summary(self):
        """Single-uppercase-character summary → leave as-is (no 2nd char
        to inspect).
        """
        opt = _option(
            option_id="OPT", description="Bare",
            impact_summary="X",
        )
        result = _format_would_have(opt)
        # First char is uppercase, len < 2, so no transformation
        self.assertEqual(result, "would have X")

    # --- 9c: edge case — already-lowercase summary -----------------
    def test_format_would_have_leaves_lowercase_alone(self):
        """Summary already lowercased → no transformation."""
        opt = _option(
            option_id="OPT", description="Lower",
            impact_summary="drops 1 balcony, saves 18 sqft",
        )
        result = _format_would_have(opt)
        self.assertEqual(
            result, "would have drops 1 balcony, saves 18 sqft",
        )


# ─────────────────────────────────────────────────────────────────
# Defensive / pathological inputs
# ─────────────────────────────────────────────────────────────────

class TestBuildCounterfactualDefensive(unittest.TestCase):

    def test_counterfactual_raises_typeerror_if_space_impact_not_int(self):
        """Post-critique-round-2 D1 fix: contract assertion fails loudly
        if space_impact_sqft is somehow not an int (e.g., type contract
        relaxed to Optional[int] without updating the ranking logic).

        Construct a malformed option by abusing dataclass.replace to
        bypass __post_init__. In normal use this can't happen — the
        ResolutionOption type signature requires int — but we test the
        assertion fires anyway as the safety net.
        """
        import dataclasses
        opts = (
            _option(option_id="A", description="A"),
            _option(option_id="B", description="B"),
        )
        # Smuggle a None into space_impact_sqft. dataclasses.replace will
        # call __post_init__ but ResolutionOption's __post_init__ doesn't
        # type-check space_impact_sqft (it just checks option_id /
        # description / etc. are non-empty), so the None survives.
        bad_opt = dataclasses.replace(opts[1], space_impact_sqft=None)
        # Reconstruct decision with the malformed option
        decision = _decision("A", (opts[0], bad_opt))
        with self.assertRaises(TypeError) as ctx:
            build_counterfactual(decision)
        self.assertIn("space_impact_sqft", str(ctx.exception))
        self.assertIn("contract violated", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
