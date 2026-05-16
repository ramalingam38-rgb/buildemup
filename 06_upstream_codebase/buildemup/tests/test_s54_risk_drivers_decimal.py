"""
S54-003 — regression test for risk_drivers decimal truncation bug.

The old `text.split(".")[0]` logic truncated messages at the first
decimal point in any number (e.g., "Front setback 0.4572m..." became
"Front setback 0"). Fixed in compute_risk_drivers to use ". " (period
+ space) as the sentence terminator.
"""
from __future__ import annotations

from buildemup.components.c01.soft_guide_engine import compute_risk_drivers
from buildemup.domain.brief import GuidanceMessage, GuidanceSeverity


def _msg(severity: GuidanceSeverity, context: str, text: str) -> GuidanceMessage:
    return GuidanceMessage(
        severity=severity,
        text=text,
        context=context,
        action_verb="review",
    )


# ─── The original bug: decimals truncated the message at "0" ─────────────

def test_decimal_setback_message_not_truncated():
    """The exact bug from the user's 20×30 ft brief — message with multiple
    decimals must come through intact (up to the first ". " sentence end).
    """
    msg = _msg(
        GuidanceSeverity.STRONG_CONCERN,
        "setback_front",
        "Front setback 0.4572m is 1.0m below the required 1.5m. "
        "This may not get municipal approval per TNCDBR 2019 (CMDA). "
        "Consider increasing the setback or reducing built-up area.",
    )
    drivers = compute_risk_drivers([msg], "HIGH")
    assert len(drivers) == 1
    # Critical: the full first sentence including the decimals must survive
    assert "0.4572m" in drivers[0], (
        f"Decimal value lost in truncation; got: {drivers[0]!r}"
    )
    assert "1.0m" in drivers[0]
    assert "1.5m" in drivers[0]
    # Must NOT be the old buggy truncation
    assert drivers[0] != "Critical: Front setback 0"


def test_first_sentence_only_not_full_paragraph():
    """We still want compact output — only the first sentence, not the
    entire 3-sentence message.
    """
    msg = _msg(
        GuidanceSeverity.STRONG_CONCERN,
        "setback_rear",
        "Rear setback 0.6m is below required. "
        "This is the second sentence. "
        "Third sentence here.",
    )
    drivers = compute_risk_drivers([msg], "HIGH")
    assert "Rear setback 0.6m is below required" in drivers[0]
    # The second/third sentences should be cut off
    assert "second sentence" not in drivers[0]
    assert "Third sentence" not in drivers[0]


def test_single_sentence_no_trailing_space():
    """A single-sentence message ending in '.' (no trailing space) should
    return the full message (minus the trailing period for display).
    """
    msg = _msg(
        GuidanceSeverity.STRONG_CONCERN,
        "setback_front",
        "Front setback 0.5m is non-compliant.",
    )
    drivers = compute_risk_drivers([msg], "HIGH")
    assert "0.5m" in drivers[0]
    # The whole sentence (sans trailing period) should be there
    assert "Front setback 0.5m is non-compliant" in drivers[0]


def test_no_period_in_message():
    """A message with no period at all should return the full text."""
    msg = _msg(
        GuidanceSeverity.STRONG_CONCERN,
        "setback_front",
        "Front setback 1.5m is non-compliant",
    )
    drivers = compute_risk_drivers([msg], "HIGH")
    assert "Front setback 1.5m is non-compliant" in drivers[0]


def test_long_message_truncated_at_100_chars():
    """The 100-char hard cap still works."""
    very_long = (
        "Front setback 0.45m is non-compliant and the explanation goes "
        "on and on and on with many additional details about exactly why "
        "this matters for your project plan."
    )
    msg = _msg(GuidanceSeverity.STRONG_CONCERN, "setback_front", very_long)
    drivers = compute_risk_drivers([msg], "HIGH")
    # 100 char cap applies
    assert len(drivers[0]) <= 110  # "Critical: " prefix adds ~10 chars
    # But the decimal still survives
    assert "0.45m" in drivers[0]


def test_biggest_issue_returns_useful_text():
    """The BIGGEST ISSUE field (=risk_drivers[0]) should be actionable,
    not just 'Critical: Front setback 0'.
    """
    messages = [
        _msg(GuidanceSeverity.STRONG_CONCERN, "setback_front",
             "Front setback 0.4572m is 1.0m below the required 1.5m. "
             "This may not get municipal approval."),
        _msg(GuidanceSeverity.STRONG_CONCERN, "setback_rear",
             "Rear setback 0.4572m is 1.0m below the required 1.5m. "
             "Same problem."),
    ]
    drivers = compute_risk_drivers(messages, "HIGH")
    biggest = drivers[0]
    # User should learn: which setback, by how much, against what target
    assert "Front setback" in biggest
    assert "0.4572m" in biggest
    assert "1.5m" in biggest
