"""
C17 — Quote Comparison Engine — error hierarchy
=================================================

Per C17 v0.2 § 4 (unchanged in v0.3).

TWO-TIER design (mirrors C13 / C14 / C15 / C16):

    LocalQuoteError       — always halts regardless of strict_mode.
                            Indicates a contract/config problem that
                            cannot be salvaged by partial output.

    PerQuoteLineError     — STRICT mode raises; WARN mode collects
                            into FailedComparisonRecord and the report
                            continues with the affected line surfaced
                            in unmatched_quote_lines or as a
                            human_verification_recommended tier match.

This split mirrors the spec § 5 failure-mode contract: local errors
are global problems (jurisdiction not supported, RateProvider broken,
upstream-schema drift) while per-line errors are problems with one
specific quote line that the orchestrator quarantines without taking
the whole report down — preserving R17 (report-level escape valve).
"""

from __future__ import annotations

from typing import Any, Optional


# ============================================================
# § 1 — BASE
# ============================================================

class QuoteComparisonError(Exception):
    """Root of the C17 error hierarchy.

    Never raised directly. Always raised as one of the two-tier
    subtypes below so that orchestrator routing (STRICT vs WARN) is
    unambiguous."""


# ============================================================
# § 2 — LOCAL (always-halt) tier
# ============================================================

class LocalQuoteError(QuoteComparisonError):
    """Always halts. Indicates a contract/config problem that cannot
    be salvaged. Bypasses strict_mode/WARN-mode entirely.

    Subtypes describe SHAPE of the local failure:
        UpstreamSchemaDriftError      — C7/C16 version mismatch or
                                        schema shape C17 doesn't recognize.
        C17ConfigurationError         — config bound exceeds hard
                                        ceiling per spec § 6.
        JurisdictionNotSupportedError — jurisdiction outside
                                        SUPPORTED_JURISDICTIONS.
        RateProviderUnavailableError  — no RateProvider for the
                                        declared jurisdiction.
        ParsedQuoteShapeError         — ParsedQuote violates structural
                                        invariants (empty, > 500 lines,
                                        signature mismatch).
    """


class UpstreamSchemaDriftError(LocalQuoteError):
    """An upstream component's output schema doesn't match what C17
    expects. Common triggers:
        - C7_VERSION on output != EXPECTED_C7_VERSION
        - C16 DualDrawingBundle missing fields C17 needs for BOQ assembly
        - C7 cost estimate not in canonical sorted order

    This is ALWAYS a contract bug — fix upstream or bump EXPECTED_*."""

    def __init__(
        self,
        message: str,
        *,
        upstream_component: str,
        expected_version: Optional[str] = None,
        observed_version: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.upstream_component = upstream_component
        self.expected_version = expected_version
        self.observed_version = observed_version


class C17ConfigurationError(LocalQuoteError):
    """C17 configuration constructed with values that violate hard
    ceilings (spec § 6), e.g. quote_total > ₹50 crore, line_items > 500,
    or unsupported declared_domain_scope.

    Per spec § 6 — fail fast at config/parse time, not at phase-γ time."""

    def __init__(
        self,
        message: str,
        *,
        offending_field: Optional[str] = None,
        offending_value: Any = None,
    ) -> None:
        super().__init__(message)
        self.offending_field = offending_field
        self.offending_value = offending_value


class JurisdictionNotSupportedError(LocalQuoteError):
    """jurisdiction_profile_id not in SUPPORTED_JURISDICTIONS
    (currently: only 'tn_cdbr_2019')."""

    def __init__(
        self,
        message: str,
        *,
        requested_jurisdiction: str,
        supported: frozenset[str],
    ) -> None:
        super().__init__(message)
        self.requested_jurisdiction = requested_jurisdiction
        self.supported = supported


class RateProviderUnavailableError(LocalQuoteError):
    """A RateProvider for the declared jurisdiction couldn't be
    constructed (KB load failure, missing rates category, version
    mismatch with EXPECTED_C7_VERSION)."""

    def __init__(
        self,
        message: str,
        *,
        jurisdiction: str,
        reason: str,
    ) -> None:
        super().__init__(message)
        self.jurisdiction = jurisdiction
        self.reason = reason


class ParsedQuoteShapeError(LocalQuoteError):
    """ParsedQuote violates structural invariants before phase α can
    canonicalize it (empty line_items, > 500 lines, total > ₹50 crore,
    single-line amount > ₹1 crore, sha256 mismatch, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        offending_field: Optional[str] = None,
        offending_value: Any = None,
    ) -> None:
        super().__init__(message)
        self.offending_field = offending_field
        self.offending_value = offending_value


class AdvisoryToneViolationError(LocalQuoteError):
    """R2 lint caught a banned phrase in an emitted advisory string.

    ALWAYS halts — escaping a banned phrase into a user-facing report
    is a contract violation regardless of strict_mode. This error
    means: somewhere in the codebase a hard-coded template uses
    banned language; fix the source. Never WARN-suppress."""

    def __init__(
        self,
        message: str,
        *,
        banned_phrase: str,
        offending_field: str,
        offending_text: str,
    ) -> None:
        super().__init__(message)
        self.banned_phrase = banned_phrase
        self.offending_field = offending_field
        self.offending_text = offending_text


# ============================================================
# § 3 — PER-LINE (strict-raise / warn-collect) tier
# ============================================================

class PerQuoteLineError(QuoteComparisonError):
    """STRICT mode → raised; WARN mode → caught + collected into
    FailedComparisonRecord. The report continues; the affected line
    surfaces in unmatched_quote_lines.

    Subtypes describe SHAPE of the per-line failure:
        QuoteLineCanonicalizationError — phase α can't normalize a line
                                         (malformed unit, unparseable
                                         numeric, blank label).
        BOQAssemblyError               — phase β can't derive an
                                         our_total for a BOQ line
                                         (missing RateProvider key,
                                         zero quantity).
        MatchingAmbiguityError         — phase γ candidate set is
                                         ambiguous beyond what
                                         human_verification_recommended
                                         can absorb (e.g. exact dup
                                         labels in BOQ).
        SignalDerivationError          — phase δ can't compute a
                                         signal (rate is 0 or
                                         non-numeric after canon).
    """


class QuoteLineCanonicalizationError(PerQuoteLineError):
    """Phase α — a single line can't be normalized into a canonical
    QuoteLineCanonical. STRICT raises; WARN drops the line into
    unmatched_quote_lines with an advisory."""

    def __init__(
        self,
        message: str,
        *,
        line_id: str,
        reason: str,
    ) -> None:
        super().__init__(message)
        self.line_id = line_id
        self.reason = reason


class BOQAssemblyError(PerQuoteLineError):
    """Phase β — a BOQ item can't be priced from C7/C16/RateProvider
    inputs (RateProvider KeyError, zero quantity, missing brand+grade
    in a context requiring exact match)."""

    def __init__(
        self,
        message: str,
        *,
        boq_id: str,
        reason: str,
    ) -> None:
        super().__init__(message)
        self.boq_id = boq_id
        self.reason = reason


class MatchingAmbiguityError(PerQuoteLineError):
    """Phase γ — match candidate set is so ambiguous that even
    human_verification_recommended doesn't fit (e.g., quote line
    matches >5 BOQ items with similar Levenshtein scores)."""

    def __init__(
        self,
        message: str,
        *,
        line_id: str,
        candidate_count: int,
    ) -> None:
        super().__init__(message)
        self.line_id = line_id
        self.candidate_count = candidate_count


class SignalDerivationError(PerQuoteLineError):
    """Phase δ — rate_delta_pct / total_delta can't be computed
    (rate is 0, infinity, NaN). The match exists but the signal can't
    be derived. WARN drops signal=None (treated as
    human_verification_recommended in ReportConfidence)."""

    def __init__(
        self,
        message: str,
        *,
        line_id: str,
        reason: str,
    ) -> None:
        super().__init__(message)
        self.line_id = line_id
        self.reason = reason
