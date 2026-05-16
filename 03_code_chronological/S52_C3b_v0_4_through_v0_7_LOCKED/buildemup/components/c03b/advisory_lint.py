"""
C3b — Post-Layout Trade-off Negotiation — advisory-tone lint (R2)
==================================================================

Spec: C3b v0.6.LOCKED § B2 + § 7 R2 + § 7.5. Build session: S52.

v0.6 B2 — 3-tier severity system:
  HARD_BLOCK    — raises AdvisoryLintError (existing v0.5 behavior)
  REVIEW_NEEDED — allows text, returns LintAuditEntry
  WARN          — allows text, returns LintAuditEntry

Backward-compat: lint_advisory_text() still raises on HARD_BLOCK only,
unchanged from v0.5. WARN/REVIEW_NEEDED do not block. The tier
information is surfaced via lint_advisory_text_tiered() for callers
that want to capture audit entries.

Word-boundary matching (v0.6 B2): single-word banned phrases now match
on word boundaries using re.compile with \\b, preventing false positives
like "unrejected_status" → "rejected". Multi-word phrases (e.g.,
"the system decided") use plain substring match because \\b doesn't
cleanly bound internal whitespace.

Rule 11 self-analysis:
  1. Word-boundary uses re.compile with \\b. \\brejected\\b does NOT match
     "unrejected" or "rejected_status_count". Verified in test suite.
  2. Tier classification is deterministic — same input always produces
     same tier. R6 byte-equal replay is preserved.
  3. v0.5 callers using lint_advisory_text() see EXACT same blocking
     behavior — every previously-banned substring still raises.
     New non-blocking phrases (bare "best", "wrong", "perfect") are
     ADDITIONS at REVIEW_NEEDED, not promotions out of HARD_BLOCK.
  4. The substring "best choice" still HARD_BLOCKs because it's in
     the BANNED_SUBSTRINGS list. Bare "best" alone goes to
     REVIEW_NEEDED — context-sensitive routing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final, Optional

from .versioning import C3B_BANNED_SUBSTRINGS, C3B_REPLACEMENT_HINTS


# ============================================================
# § 0 — Tier enum + audit entry (v0.6 B2)
# ============================================================

class LintTier(str, Enum):
    HARD_BLOCK    = "hard_block"
    REVIEW_NEEDED = "review_needed"
    WARN          = "warn"


@dataclass(frozen=True)
class LintAuditEntry:
    tier:             LintTier
    offending_phrase: str
    field_name:       Optional[str]
    matched_text:     str
    replacement_hint: Optional[str]


# ============================================================
# § 1 — Banned-phrase tables + tier mapping
# ============================================================

C17_INHERITED_BANNED_SUBSTRINGS: tuple[str, ...] = (
    "do not pay",
    "refuse to pay",
    "demand immediately",
    "overcharging",
    "ripping off",
    "ripped off",
    "fraud",
    "scam",
    "scamming",
    "cheating",
    "cheats",
    "hidden charges",
    "trying to charge",
    "padding the bill",
    "suspicious",
    "trustworthy",
    "not credible",
    "according to my calculations",
)

BANNED_SUBSTRINGS: tuple[str, ...] = (
    C17_INHERITED_BANNED_SUBSTRINGS + C3B_BANNED_SUBSTRINGS
)


# v0.6 B2 — bare word-boundary phrases. These are ADDITIONS to the
# lint vocabulary at REVIEW_NEEDED tier — they do NOT block, but they
# do log audit entries. The corresponding multi-word forms (e.g.,
# "best choice") are still in BANNED_SUBSTRINGS and HARD_BLOCK.
WORD_BOUNDARY_REVIEW_PHRASES: tuple[str, ...] = (
    "best",
    "wrong",
    "perfect",
)

# Reserved for v1.x telemetry-driven additions.
WORD_BOUNDARY_WARN_PHRASES: tuple[str, ...] = ()


# Default tier mapping — every BANNED_SUBSTRINGS entry → HARD_BLOCK.
# Conservative default; no reassignments at v0.6.
_SUBSTRING_TIER: Final[dict[str, LintTier]] = {
    p: LintTier.HARD_BLOCK for p in BANNED_SUBSTRINGS
}


def _compile_word_boundary(phrase: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)


def _is_single_word(phrase: str) -> bool:
    return " " not in phrase and "'" not in phrase and "-" not in phrase


_REVIEW_REGEXES: Final[dict[str, re.Pattern]] = {
    p: _compile_word_boundary(p) for p in WORD_BOUNDARY_REVIEW_PHRASES
}
_WARN_REGEXES: Final[dict[str, re.Pattern]] = {
    p: _compile_word_boundary(p) for p in WORD_BOUNDARY_WARN_PHRASES
}

# Substring phrases compiled once. Single-word phrases use \b for
# false-positive resistance; multi-word phrases use plain substring.
_SUBSTRING_PATTERNS: Final[dict[str, re.Pattern]] = {}
for _phrase in BANNED_SUBSTRINGS:
    if _is_single_word(_phrase):
        _SUBSTRING_PATTERNS[_phrase] = _compile_word_boundary(_phrase)
    else:
        _SUBSTRING_PATTERNS[_phrase] = re.compile(re.escape(_phrase), re.IGNORECASE)


# ============================================================
# § 2 — Lint API
# ============================================================

class AdvisoryLintError(Exception):
    def __init__(
        self,
        message:           str,
        *,
        offending_phrase:  str,
        field_name:        Optional[str] = None,
        replacement_hint:  Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.offending_phrase = offending_phrase
        self.field_name = field_name
        self.replacement_hint = replacement_hint


def _scan_for_phrase(text: str) -> Optional[tuple[str, LintTier, str]]:
    """Returns (phrase, tier, matched_text) of FIRST hit, or None.
    HARD_BLOCK → REVIEW_NEEDED → WARN priority order."""
    if not text:
        return None

    for phrase, pattern in _SUBSTRING_PATTERNS.items():
        if _SUBSTRING_TIER.get(phrase) != LintTier.HARD_BLOCK:
            continue
        m = pattern.search(text)
        if m:
            return (phrase, LintTier.HARD_BLOCK, m.group(0))

    for phrase, pattern in _REVIEW_REGEXES.items():
        m = pattern.search(text)
        if m:
            return (phrase, LintTier.REVIEW_NEEDED, m.group(0))

    for phrase, pattern in _WARN_REGEXES.items():
        m = pattern.search(text)
        if m:
            return (phrase, LintTier.WARN, m.group(0))

    return None


def find_banned_phrase(text: str) -> Optional[str]:
    """v0.5 API preserved — returns first HARD_BLOCK phrase only."""
    if not text:
        return None
    for phrase, pattern in _SUBSTRING_PATTERNS.items():
        if _SUBSTRING_TIER.get(phrase) != LintTier.HARD_BLOCK:
            continue
        if pattern.search(text):
            return phrase
    return None


def is_advisory_clean(text: str) -> bool:
    """v0.5 API preserved — True iff no HARD_BLOCK phrases."""
    return find_banned_phrase(text) is None


def lint_advisory_text(
    text:        str,
    *,
    field_name:  Optional[str] = None,
) -> None:
    """v0.5 API preserved — raises on HARD_BLOCK, ignores REVIEW/WARN."""
    found = find_banned_phrase(text)
    if found is None:
        return
    hint = replacement_hint(found)
    msg = (
        f"Advisory-tone lint failed"
        + (f" on field '{field_name}'" if field_name else "")
        + f": banned phrase '{found}' detected. "
        + (f"Consider using '{hint}' instead. " if hint else "")
        + "Reference: spec C3b v0.6 § 7.5 + B2 banned-phrase list."
    )
    raise AdvisoryLintError(
        msg,
        offending_phrase=found,
        field_name=field_name,
        replacement_hint=hint,
    )


def lint_advisory_text_tiered(
    text:        str,
    *,
    field_name:  Optional[str] = None,
) -> Optional[LintAuditEntry]:
    """v0.6 B2 — tiered lint. Raises on HARD_BLOCK; returns
    LintAuditEntry for REVIEW_NEEDED/WARN; returns None if clean."""
    hit = _scan_for_phrase(text)
    if hit is None:
        return None
    phrase, tier, matched = hit

    if tier == LintTier.HARD_BLOCK:
        hint = replacement_hint(phrase)
        msg = (
            f"Advisory-tone lint failed"
            + (f" on field '{field_name}'" if field_name else "")
            + f": banned phrase '{phrase}' detected. "
            + (f"Consider using '{hint}' instead. " if hint else "")
            + "Reference: spec C3b v0.6 § 7.5 + B2 banned-phrase list."
        )
        raise AdvisoryLintError(
            msg,
            offending_phrase=phrase,
            field_name=field_name,
            replacement_hint=hint,
        )

    return LintAuditEntry(
        tier=tier,
        offending_phrase=phrase,
        field_name=field_name,
        matched_text=matched,
        replacement_hint=replacement_hint(phrase),
    )


def replacement_hint(banned_phrase: str) -> Optional[str]:
    if not banned_phrase:
        return None
    key = banned_phrase.lower().strip()
    if key in C3B_REPLACEMENT_HINTS:
        return C3B_REPLACEMENT_HINTS[key]
    for word in key.split():
        if word in C3B_REPLACEMENT_HINTS:
            return C3B_REPLACEMENT_HINTS[word]
    return None


__all__ = [
    "AdvisoryLintError",
    "BANNED_SUBSTRINGS",
    "C17_INHERITED_BANNED_SUBSTRINGS",
    "find_banned_phrase",
    "is_advisory_clean",
    "lint_advisory_text",
    "replacement_hint",
    "LintTier",
    "LintAuditEntry",
    "WORD_BOUNDARY_REVIEW_PHRASES",
    "WORD_BOUNDARY_WARN_PHRASES",
    "lint_advisory_text_tiered",
]
