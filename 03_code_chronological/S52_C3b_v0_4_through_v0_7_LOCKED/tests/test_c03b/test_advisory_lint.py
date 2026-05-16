"""Tests for C3b advisory-tone lint (R2 enforcement, spec § 7.5)."""
from __future__ import annotations

import pytest

from buildemup.components.c03b.advisory_lint import (
    AdvisoryLintError,
    BANNED_SUBSTRINGS,
    C17_INHERITED_BANNED_SUBSTRINGS,
    find_banned_phrase,
    is_advisory_clean,
    lint_advisory_text,
    replacement_hint,
)


# ============================================================
# find_banned_phrase — basic positive / negative cases
# ============================================================

def test_clean_text_returns_none():
    assert find_banned_phrase("You could move the kitchen east.") is None


def test_empty_text_returns_none():
    assert find_banned_phrase("") is None


def test_detects_should():
    """Spec § 7.5: 'you should' is banned (coercive)."""
    found = find_banned_phrase("You should move the kitchen.")
    assert found == "you should"


def test_detects_must():
    found = find_banned_phrase("You must add a balcony.")
    assert found == "you must"


def test_detects_best_tweak():
    found = find_banned_phrase("This is the best tweak option.")
    assert found == "best tweak"


def test_detects_system_decided():
    """Engine-centric / no-agency phrasing. The list contains both
    'the system decided' and 'system decided' — the longer phrase
    appears first in the tuple and wins the substring match."""
    found = find_banned_phrase("The system decided to remove this.")
    # Either phrase is a valid banned hit; we just check the function
    # returned a banned phrase (the strongest possible test —
    # ordering details are implementation choice)
    assert found in ("the system decided", "system decided")


def test_detects_auto_fix():
    found = find_banned_phrase("We'll auto-fix this for you.")
    assert found == "we'll auto-fix"


def test_detects_tweak_failed():
    found = find_banned_phrase("Your tweak failed.")
    assert found == "tweak failed"


def test_detects_rejected_as_action():
    """Spec § 7.5: 'rejected' as user-facing language → use 'couldn't
    be surfaced'. Both 'rejected' and 'you rejected' are banned;
    whichever the substring matcher finds first is fine."""
    found = find_banned_phrase("You rejected this option.")
    assert found in ("rejected", "you rejected")


def test_case_insensitive():
    """Match is case-insensitive."""
    assert find_banned_phrase("YOU SHOULD do this") == "you should"
    assert find_banned_phrase("You Should do this") == "you should"


# ============================================================
# C17 inherited list
# ============================================================

def test_c17_inherited_overcharging_detected():
    """C17 R2 base — accusatory framing banned in C3b too."""
    assert find_banned_phrase("The contractor is overcharging.") == "overcharging"


def test_c17_inherited_fraud_detected():
    assert find_banned_phrase("This looks like fraud.") == "fraud"


def test_c17_inherited_suspicious_detected():
    assert find_banned_phrase("This rate is suspicious.") == "suspicious"


# ============================================================
# is_advisory_clean — boolean form
# ============================================================

def test_is_advisory_clean_true():
    assert is_advisory_clean("You could consider this option.") is True


def test_is_advisory_clean_false():
    assert is_advisory_clean("You must accept this.") is False


def test_is_advisory_clean_empty_is_clean():
    assert is_advisory_clean("") is True


# ============================================================
# lint_advisory_text — raises with structured info
# ============================================================

def test_lint_clean_text_no_raise():
    lint_advisory_text("You could move the kitchen east.")
    lint_advisory_text("An alternative: leave it as-is.")


def test_lint_raises_with_offending_phrase():
    with pytest.raises(AdvisoryLintError) as excinfo:
        lint_advisory_text("You should move this.", field_name="test_field")
    assert excinfo.value.offending_phrase == "you should"
    assert excinfo.value.field_name == "test_field"


def test_lint_error_message_mentions_phrase():
    with pytest.raises(AdvisoryLintError) as excinfo:
        lint_advisory_text("You must do this.")
    assert "you must" in str(excinfo.value)


def test_lint_error_message_mentions_replacement():
    with pytest.raises(AdvisoryLintError) as excinfo:
        lint_advisory_text("You should change this.")
    # The replacement hint for 'should' is 'could'
    assert "could" in str(excinfo.value)


def test_lint_error_references_spec():
    """Error message points to the spec section that defined the rule."""
    with pytest.raises(AdvisoryLintError) as excinfo:
        lint_advisory_text("Best tweak is this one.")
    assert "C3b" in str(excinfo.value) or "spec" in str(excinfo.value).lower()


# ============================================================
# replacement_hint
# ============================================================

def test_replacement_for_should():
    assert replacement_hint("should") == "could"


def test_replacement_for_must():
    assert replacement_hint("must") == "may want to"


def test_replacement_for_rejected():
    assert replacement_hint("rejected") == "couldn't be surfaced as a tweak"


def test_replacement_for_unknown_returns_none():
    assert replacement_hint("xyzbananas") is None


def test_replacement_for_empty_returns_none():
    assert replacement_hint("") is None


def test_replacement_handles_compound_phrase():
    """Root-form fallback: 'must do' → uses 'must' hint."""
    # 'must do' isn't directly in C3B_REPLACEMENT_HINTS,
    # but the first word 'must' is.
    assert replacement_hint("must do") == "may want to"


# ============================================================
# Banned list integrity
# ============================================================

def test_banned_substrings_includes_inherited():
    """C17 inherited list is a strict subset of full BANNED_SUBSTRINGS."""
    for phrase in C17_INHERITED_BANNED_SUBSTRINGS:
        assert phrase in BANNED_SUBSTRINGS


def test_banned_substrings_has_c3b_additions():
    """Spec § 7.5 additions present."""
    assert "you should" in BANNED_SUBSTRINGS
    assert "best tweak" in BANNED_SUBSTRINGS
    assert "system decided" in BANNED_SUBSTRINGS
