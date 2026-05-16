"""
C17 — Advisory-tone lint (R2 enforcement)
===========================================

Per C17 v0.2 § 7.1 (carried forward in v0.3): every advisory string
(signal_explanation, advisory_note, conversation_language, headline_summary,
disclaimer) MUST pass the banned-phrase check before being emitted in a
QuoteComparisonReport.

Banned categories (spec § 7.1):
    accusation     : "overcharging", "fraud", "scam", "cheating", "ripping off"
    confrontation  : "do not pay", "refuse to pay", "demand immediately",
                     "must demand"
    suspicion      : "hidden charges", "trying to charge", "marked up",
                     "padding the bill", "suspicious"
    character      : "trustworthy", "untrustworthy", "credible", "not credible"
    visual-hierarchy: "warning", "alert", "danger"
    person-frame   : any phrase characterising the contractor as a person/business

Failure mode: emitting a banned phrase is a hard contract violation
(AdvisoryToneViolationError — LocalQuoteError tier). NEVER WARN-mode
suppressed; lint failures are upstream bugs in the template, not
runtime data anomalies.

Rule 11 self-analysis:
  1. Case-insensitive substring match. "Overcharging" / "OVERCHARGING"
     / "over-charging" — the first two caught by .lower(); the third
     fails (hyphen). Documented limitation; B-C17-LINT-TOKENIZATION
     suggested if false negatives appear in real-world templates.
  2. Word-boundary subtleties: "alert" is banned, "alerted" technically
     contains it but isn't an alert-frame. Mitigation: we match on
     "alert" surrounded by non-letter chars OR at string boundaries.
     Implemented via regex \\b boundaries.
  3. The phrase "do not pay" is multi-word; .split() approaches break.
     We use substring match against a normalised string (spaces
     collapsed, lowered).
  4. The "person-frame" rule from spec is qualitative; we encode it
     by adding "the contractor is" / "this contractor" / etc. as
     banned phrases. This is HEURISTIC, not exhaustive — false
     negatives possible.

Public surface:
    lint_advisory_text(text, field_name)        — raises on violation
    is_advisory_clean(text)        -> bool      — non-raising check
    BANNED_PHRASES                              — tuple, importable for tests
"""

from __future__ import annotations

import re
from typing import Final, Iterable, Tuple

from buildemup.components.c17.errors import AdvisoryToneViolationError


# ============================================================
# § 1 — BANNED PHRASE TABLE (spec § 7.1)
# ============================================================
#
# Substring match on lowered text. Phrases that need word-boundary
# matching are in BANNED_WORD_BOUNDARY (regex \\b…\\b).

BANNED_PHRASES_SUBSTRING: Final[Tuple[str, ...]] = (
    # Accusation
    "overcharging",
    "over-charging",
    "ripping off",
    "rip off",
    "fraud",
    "scam",
    "cheating",

    # Confrontation
    "do not pay",
    "don't pay",
    "refuse to pay",
    "demand immediately",
    "must demand",
    "you must refuse",

    # Suspicion / framing
    "hidden charges",
    "hidden costs",
    "trying to charge",
    "marked up",
    "padding the bill",
    "suspicious",
    "shady",
    "dishonest",

    # Character (R13 — itemization quality ⊥ competence)
    "trustworthy",
    "untrustworthy",
    "not credible",
    "credible contractor",
    "incompetent",
    "unprofessional",

    # Person-frame
    "the contractor is overcharging",
    "this contractor is",
    "your contractor is trying",
)
"""Substring banned phrases (case-insensitive). Spec § 7.1 v0.2 expanded
list, carried forward unchanged in v0.3."""


BANNED_WORD_BOUNDARY: Final[Tuple[str, ...]] = (
    # Visual-hierarchy words — banned standalone but allowed in
    # compound technical terms ("alert color is red" would be allowed;
    # we ban naked "alert" / "warning" / "danger" in advisory text).
    "warning",
    "alert",
    "danger",
)
"""Word-boundary banned tokens. Matched as \\btoken\\b in lowered text."""


_WORD_BOUNDARY_RE = {
    tok: re.compile(rf"\b{re.escape(tok)}\b")
    for tok in BANNED_WORD_BOUNDARY
}


def _normalise(text: str) -> str:
    """Collapse internal whitespace; lower-case."""
    return " ".join(text.lower().split())


# ============================================================
# § 2 — PUBLIC SURFACE
# ============================================================

def find_banned_phrase(text: str) -> str:
    """Return the first banned phrase found, or '' if clean.

    Pure inspection helper — does NOT raise. Used by both
    `is_advisory_clean` and `lint_advisory_text`. Returning the
    first match is intentional: the caller's job is to fix templates,
    not to enumerate every violation."""
    if not text:
        return ""
    normalised = _normalise(text)
    for phrase in BANNED_PHRASES_SUBSTRING:
        if phrase in normalised:
            return phrase
    for tok in BANNED_WORD_BOUNDARY:
        if _WORD_BOUNDARY_RE[tok].search(normalised):
            return tok
    return ""


def is_advisory_clean(text: str) -> bool:
    """True iff `text` passes the R2 lint. Non-raising."""
    return find_banned_phrase(text) == ""


def lint_advisory_text(text: str, *, field_name: str) -> None:
    """Raise AdvisoryToneViolationError on R2 violation.

    Called by phases at every emission point. `field_name` identifies
    the dataclass field for diagnostic purposes (helps debug WHICH
    template emitted a banned phrase)."""
    banned = find_banned_phrase(text)
    if banned:
        raise AdvisoryToneViolationError(
            f"R2 lint violation: field {field_name!r} contains banned "
            f"phrase {banned!r}. C17 v0.2 § 7.1 prohibits this in "
            f"user-facing advisory text. Fix the template, do not "
            f"WARN-suppress.",
            banned_phrase=banned,
            offending_field=field_name,
            offending_text=text,
        )


def lint_all(strings: Iterable[tuple[str, str]]) -> None:
    """Convenience: lint a batch of (field_name, text) pairs.

    Stops at the first violation (consistent with single-string lint).
    Phases use this for bulk-emission boundaries (e.g., the report
    bundle just before signing)."""
    for field_name, text in strings:
        lint_advisory_text(text, field_name=field_name)
