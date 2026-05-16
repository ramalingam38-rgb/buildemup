"""Tests for Component 3a Session 4 — reason-aware error formatter.

Per locked S4 SPEC v0.1 § 9.2 — verifies that
error_formatter.format_validation_error_for_user:
  - picks the correct template per classification
  - substitutes context fields cleanly
  - falls back to UNKNOWN message for unrecognized classifications
  - appends ' Try a different option.' to non-UNKNOWN messages
  - never returns empty / never returns HTML or markdown

The applier produces these errors; the formatter is a pure render
layer. We construct errors directly here to test the render
behaviour in isolation.
"""
import unittest

from buildemup.domain.extreme_case import (
    BriefChangeIntegrityError,
    ResolutionOption,
    BriefChange,
)
from buildemup.components.c03a.error_formatter import (
    format_validation_error_for_user,
)


# ─────────────────────────────────────────────────────────────────
# Fixture builders
# ─────────────────────────────────────────────────────────────────

def _option(description: str = "Drop balcony 2") -> ResolutionOption:
    """Build a ResolutionOption fixture with a non-empty
    requires_brief_change so __post_init__ accepts it.
    """
    return ResolutionOption(
        option_id="OPT_TEST",
        description=description,
        impact_summary="Test summary",
        cost_impact=None,
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(
            BriefChange(
                field_path="setbacks.front_m",
                operation="INCREMENT",
                new_value=0.0,
                description="placeholder",
            ),
        ),
        requires_action=None,
        risk_advisory=None,
    )


def _err(classification: str, **context) -> BriefChangeIntegrityError:
    return BriefChangeIntegrityError(
        f"test error for {classification}",
        classification=classification,
        context=context,
    )


_SUFFIX = " Try a different option."


# ─────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────

class TestFormatter(unittest.TestCase):

    # --- 1: BEDROOM_COUNT_BELOW_MIN ---------------------------------
    def test_format_bedroom_below_min(self):
        """BEDROOM_COUNT_BELOW_MIN substitutes resulting_count,
        stated_min, and option_action correctly.
        """
        err = _err(
            "BEDROOM_COUNT_BELOW_MIN",
            resulting_count=1,
            stated_min=2,
            room_type="bedroom_regular",
        )
        opt = _option(description="Drop bedroom 3")
        out = format_validation_error_for_user(err, opt)
        self.assertIn("drop bedroom 3", out)         # option_action
        self.assertIn("only 1 bedroom", out)          # resulting_count
        self.assertIn("2-bedroom minimum", out)       # stated_min
        self.assertTrue(out.endswith(_SUFFIX))

    # --- 2: BUDGET_BELOW_THRESHOLD ----------------------------------
    def test_format_budget_below_threshold(self):
        """BUDGET_BELOW_THRESHOLD substitutes delta_l, est_l, budget_l."""
        err = _err(
            "BUDGET_BELOW_THRESHOLD",
            delta_l=20, est_l=130, budget_l=80,
        )
        opt = _option(description="Reduce budget by 20L")
        out = format_validation_error_for_user(err, opt)
        self.assertIn("₹20 L", out)
        self.assertIn("₹130 L", out)
        self.assertIn("₹80 L", out)
        self.assertIn("catastrophic threshold", out)
        self.assertTrue(out.endswith(_SUFFIX))

    # --- 3: ROOM_AREA_BELOW_NBC_MIN ---------------------------------
    def test_format_room_area_below_nbc_min(self):
        """ROOM_AREA_BELOW_NBC_MIN substitutes room_type, nbc_min_sqm."""
        err = _err(
            "ROOM_AREA_BELOW_NBC_MIN",
            room_type="kitchen",
            requested_size_sqm=4.0,
            nbc_min_sqm=5.0,
        )
        opt = _option(description="Set kitchen to 4 sqm")
        out = format_validation_error_for_user(err, opt)
        self.assertIn("kitchen", out)
        self.assertIn("5.0 sqm", out)
        self.assertTrue(out.endswith(_SUFFIX))

    # --- 4: FLOOR_COUNT_BELOW_MIN -----------------------------------
    def test_format_floor_count_below_min(self):
        """FLOOR_COUNT_BELOW_MIN substitutes resulting_count and
        stated_min.
        """
        err = _err(
            "FLOOR_COUNT_BELOW_MIN",
            resulting_count=0, stated_min=1,
        )
        opt = _option(description="Drop ground floor")
        out = format_validation_error_for_user(err, opt)
        self.assertIn("0 floor", out)
        self.assertIn("at least 1", out)
        self.assertTrue(out.endswith(_SUFFIX))

    # --- 5: UNKNOWN returns generic message -------------------------
    def test_format_unknown_returns_generic_message(self):
        """UNKNOWN classification → generic copy (no suffix)."""
        err = _err(
            "UNKNOWN",
            raw_message="something blew up",
            field_path="garage.size",
        )
        opt = _option(description="Some option")
        out = format_validation_error_for_user(err, opt)
        self.assertEqual(
            out,
            "This option doesn't work for your brief — try another.",
        )

    # --- 6: non-UNKNOWN always ends with the suffix -----------------
    def test_format_output_always_ends_with_suffix_or_unknown_msg(self):
        """Every non-UNKNOWN classification's output ends with
        ' Try a different option.'.
        """
        non_unknown_classifications = [
            ("BEDROOM_COUNT_BELOW_MIN",
             dict(resulting_count=1, stated_min=2,
                  room_type="bedroom_regular")),
            ("BUDGET_BELOW_THRESHOLD",
             dict(delta_l=10, est_l=100, budget_l=80)),
            ("FAR_EXCEEDED_BY_CHANGE",
             dict(city="chennai", requested_far=2.0, permitted_far=1.5)),
            ("ROOM_AREA_BELOW_NBC_MIN",
             dict(room_type="kitchen",
                  requested_size_sqm=4.0, nbc_min_sqm=5.0)),
            ("FLOOR_COUNT_BELOW_MIN",
             dict(resulting_count=0, stated_min=1)),
        ]
        opt = _option()
        for cls, ctx in non_unknown_classifications:
            with self.subTest(classification=cls):
                err = _err(cls, **ctx)
                out = format_validation_error_for_user(err, opt)
                self.assertTrue(
                    out.endswith(_SUFFIX),
                    msg=f"{cls} output did not end with suffix: {out!r}",
                )

    # --- 7: output never empty -------------------------------------
    def test_format_output_is_non_empty(self):
        """All classifications produce non-empty strings, even with
        empty context.
        """
        all_classifications = [
            "BEDROOM_COUNT_BELOW_MIN", "BUDGET_BELOW_THRESHOLD",
            "FAR_EXCEEDED_BY_CHANGE", "ROOM_AREA_BELOW_NBC_MIN",
            "FLOOR_COUNT_BELOW_MIN", "UNKNOWN",
            "TOTALLY_INVENTED_CLASS",  # falls through to UNKNOWN
        ]
        opt = _option()
        for cls in all_classifications:
            with self.subTest(classification=cls):
                err = _err(cls)  # empty context
                out = format_validation_error_for_user(err, opt)
                self.assertTrue(out)
                self.assertGreater(len(out.strip()), 0)

    # --- 8: output is plain text (no HTML / markdown) --------------
    def test_format_output_is_plain_text(self):
        """No <, >, **, ##, [, ] HTML/markdown leakage."""
        all_classifications = [
            ("BEDROOM_COUNT_BELOW_MIN",
             dict(resulting_count=1, stated_min=2,
                  room_type="bedroom_regular")),
            ("BUDGET_BELOW_THRESHOLD",
             dict(delta_l=10, est_l=100, budget_l=80)),
            ("FAR_EXCEEDED_BY_CHANGE",
             dict(city="chennai", requested_far=2.0,
                  permitted_far=1.5)),
            ("ROOM_AREA_BELOW_NBC_MIN",
             dict(room_type="kitchen",
                  requested_size_sqm=4.0, nbc_min_sqm=5.0)),
            ("FLOOR_COUNT_BELOW_MIN",
             dict(resulting_count=0, stated_min=1)),
            ("UNKNOWN", dict(raw_message="x", field_path="y")),
        ]
        forbidden_substrings = ("<", ">", "**", "##", "[", "]")
        opt = _option()
        for cls, ctx in all_classifications:
            with self.subTest(classification=cls):
                err = _err(cls, **ctx)
                out = format_validation_error_for_user(err, opt)
                for forbidden in forbidden_substrings:
                    self.assertNotIn(forbidden, out)


if __name__ == "__main__":
    unittest.main()
