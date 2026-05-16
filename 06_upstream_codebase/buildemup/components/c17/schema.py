"""
C17 — Quote Comparison Engine — schema (output dataclasses)
=============================================================

Per C17 v0.3 LOCKED spec § 2 (carries forward unchanged from v0.2 § 2)
plus v0.3 narrowings in § 7 (R15) and additions in § 26 / § 27.5.

This module defines the SHAPE of QuoteComparisonReport and every nested
type. Pure data — no logic, no IO, no imports from phases/. The phases
construct instances; the orchestrator wires them together.

R-invariant alignment (spec § 7):
    R1  — every numeric output is AttestedValue (or TransparencyTriple
          where Design Principles v3.1 Principle 2 applies)
    R8  — schema is public-versioned API; field additions = MINOR bump
    R12 — semantic compression discipline; every field justified
    R13 — ItemizationIndicators has NO aggregate score and NO tier
          label; carries mandatory "not contractor competence" clause
    R14 — every report carries RateStalenessDisclosure
    R15 (NARROWED v0.3) — NO field names imply prominence; no
          `is_headline`, `prominence`, `top_concern`, `primary_signal`
    R17 — ReportConfidence escape-valve fields
    R18 — DecompositionAcknowledgment for non-line-itemized quotes

Rule 11 self-analysis (worst issues considered):
    1. AttestedValue re-use: we import directly from c16.contracts.
       That's an UPSTREAM lock not a duplication — if C16 changes
       AttestedValue contract, C17 catches it via versioning check.
    2. PriceSignal is an Enum, not a Literal — chosen for type-checker
       friendliness and ability to add helper methods without churn.
       Backwards-compat: enum values are the exact strings the spec
       names, so json.dumps will produce R6-stable output.
    3. `signal=None` cases: a MatchedLine with no signal must NOT
       still have a signal_explanation. Phase δ guards this; the
       dataclass would let it slip. Documented in field comment.
    4. tuple[..., ...] vs list — tuples chosen throughout for
       determinism (immutable, replay-stable). All collection fields
       use tuple even if mutability would be more convenient.
    5. canonical_replay_signature, presentation_signature,
       schema_descriptor_digest — strings, computed by cache_keys.py
       at orchestrator-bundle time. Not validated at dataclass level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional, Tuple

# Re-exported upstream primitives — DO NOT redefine
from buildemup.components.c16.contracts import (
    AttestedValue,
    AuthorityKind,
    CheckProvenance,
)
from buildemup.components.c16.schema import AdvisoryFlag
from buildemup.utils.transparency import TransparencyTriple


# ============================================================
# § 1 — ENUMS (spec § 2.2, § 2.3, § 2.4, § 2.6, § 2.10)
# ============================================================

class PriceSignal(Enum):
    """Per spec § 2.3 (RENAMED v0.2 from PriceVerdict).

    Reference-anchored, never accusatory. Describes data position
    against rate range; does NOT make claims about contractor intent
    or quote quality. R2-aligned (advisory tone) and R5-aligned
    (low-confidence matches downgrade ABOVE_REFERENCE_RANGE →
    ABOVE_TYPICAL; HUMAN_VERIFICATION_RECOMMENDED → signal=None)."""

    ABOVE_REFERENCE_RANGE      = "above_reference_range"
    """rate_delta_pct > +20%, with match_confidence_tier ∈ {high, medium}.
    Per R5: low-confidence match with the same delta downgrades to
    ABOVE_TYPICAL. Per spec § 26.2: bundle-line matches downgrade
    one tier; +25% in a turnkey bundle → ABOVE_TYPICAL, not
    ABOVE_REFERENCE_RANGE."""

    ABOVE_TYPICAL              = "above_typical"
    """rate_delta_pct in (+5%, +20%] OR ABOVE_REFERENCE_RANGE
    downgraded per R5 / spec § 26.2."""

    WITHIN_TYPICAL             = "within_typical"
    """rate_delta_pct in [-5%, +5%]. Includes mild under-quote
    (BELOW_TYPICAL collapses here per spec § 2.3 — no accusation
    of contractor losing money below a soft band)."""

    BELOW_TYPICAL_QUALITY_RISK = "below_typical_quality_risk"
    """rate_delta_pct < -20%. Signals risk of corner-cutting on
    materials/labor. Per R2: the advisory_note MUST frame this as
    a clarifying question, NEVER as accusation."""

    INSUFFICIENT_DATA          = "insufficient_data"
    """quote_quantity, quote_rate, or our_rate is None / 0 /
    unparseable. The match exists structurally but no signal can
    be derived. Distinct from signal=None for
    HUMAN_VERIFICATION_RECOMMENDED tier matches (which are tier-4
    matches we explicitly DON'T signal-judge)."""


# Match confidence tier per spec § 2.2 (R4 — tiered, never continuous).
MatchConfidenceTier = Literal[
    "high",                              # IS code OR brand+grade exact
    "medium",                            # brand-only OR grade-only + unit
    "low",                               # name fuzzy + unit
    "human_verification_recommended",    # NEW v0.2 (R5: signal=None)
]


# Match basis taxonomy per spec § 2.2. Multi-valued tuple — one match
# can satisfy several criteria simultaneously.
MatchBasis = Literal[
    "is_code_match",
    "brand_grade_exact",
    "brand_only",
    "grade_only",
    "unit_compatible",
    "label_fuzzy_high",
    "label_fuzzy_medium",
    "label_fuzzy_low",
    "quantity_compatible",
]


# Gap interpretation per spec § 2.4. R16 mandates "likely_oversight"
# as the default — most generous reading. Other tiers REQUIRE positive
# evidence in the quote.
GapInterpretation = Literal[
    "likely_oversight",
    "possibly_omitted_intentionally",
    "may_be_deferred_to_later_phase",
    "insufficient_evidence_to_classify",
]


GapSeverity = Literal["critical", "important", "minor"]


# Decomposition style per spec § 2.6. R18: legitimate-but-different.
DecompositionStyle = Literal[
    "line_itemized",
    "turnkey_bundles",
    "labor_material_split",
    "room_based",
    "milestone_based",
    "hybrid",
    "unknown",
]


AlignmentQualityIndicator = Literal["high", "moderate", "low"]


# Itemization-indicator typing per spec § 2.9. R13 — pure data, NO
# aggregate tier characterising the contractor.
MarginTransparencyKind = Literal[
    "shown_explicitly",
    "embedded_in_rates",
    "not_detectable",
    "decomposition_does_not_apply",   # R18 — turnkey + similar
]

RateConsistencyKind = Literal[
    "consistent",
    "mixed",
    "highly_variable",
    "insufficient_matches",
]


# Report-confidence tier per spec § 2.10 (R17 escape valve).
ReportConfidenceTier = Literal[
    "high_signal",
    "moderate_signal",
    "high_ambiguity",
    "human_review_recommended",
]


# ============================================================
# § 2 — LEAF DATA TYPES
# ============================================================

@dataclass(frozen=True)
class RateStalenessDisclosure:
    """Per spec § 2.11 (NEW v0.2 — R14).

    Every report MUST carry one of these (R14 enforcement). Downstream
    renderer is contractually expected to surface these in every
    numeric display. v1.0 ships with Chennai-wide rates; micro-market
    granularity is B-C17-MICRO-MARKET-CALIBRATION."""

    rate_provider_kb_version:   str           # e.g. "Chennai_2026_Q2_v1"
    rate_provider_kb_date:      str           # ISO 8601 date
    rate_provider_locality:     str           # "Chennai-wide" at v1.0
    micro_market_caveat:        str           # standardised text
    market_volatility_caveat:   str           # standardised text
    recommended_review_cadence: str           # e.g. "60 days from now"

    def __post_init__(self) -> None:
        for fname, fval in (
            ("rate_provider_kb_version",   self.rate_provider_kb_version),
            ("rate_provider_kb_date",      self.rate_provider_kb_date),
            ("rate_provider_locality",     self.rate_provider_locality),
            ("micro_market_caveat",        self.micro_market_caveat),
            ("market_volatility_caveat",   self.market_volatility_caveat),
            ("recommended_review_cadence", self.recommended_review_cadence),
        ):
            if not isinstance(fval, str) or not fval:
                raise ValueError(
                    f"RateStalenessDisclosure.{fname} must be non-empty str "
                    f"(R14); got {fval!r}"
                )


# ============================================================
# § 3 — MATCHED LINE (spec § 2.2 — REVISED v0.2)
# ============================================================

@dataclass(frozen=True)
class MatchedLine:
    """One quote line matched against one BOQ item.

    R15 (NARROWED v0.3): NO field implies visual prominence. The
    `signal` field is NOT positioned for headline rendering; downstream
    consumers choose visual hierarchy. R5: low-confidence matches
    downgrade ABOVE_REFERENCE_RANGE → ABOVE_TYPICAL; tier-4
    (human_verification_recommended) matches emit signal=None."""

    # Identity
    line_id:               str       # canonical line id from ParsedQuote
    quote_label:           str       # verbatim from contractor
    matched_boq_id:        str
    matched_boq_label:     str

    # Match metadata
    match_confidence_tier: MatchConfidenceTier
    match_basis:           Tuple[MatchBasis, ...]

    # Quote-side AttestedValues (UPSTREAM_AUTHORITATIVE — from parsed quote)
    quote_quantity:        AttestedValue
    quote_unit:            str
    quote_rate:            AttestedValue
    quote_total:           AttestedValue

    # Our-side AttestedValues (UPSTREAM_AUTHORITATIVE — from RateProvider)
    our_quantity:          AttestedValue
    our_rate_median:       AttestedValue
    our_rate_min:          AttestedValue
    our_rate_max:          AttestedValue
    our_total:             AttestedValue          # LOCALLY_DERIVED

    # Derived deltas (LOCALLY_DERIVED — R3)
    rate_delta_pct:        AttestedValue
    total_delta:           AttestedValue

    # Signals
    signal:                Optional[PriceSignal]  # None when tier=4 (R5)
    signal_explanation:    str                    # advisory-tone (R2)

    # Provenance
    provenance:            CheckProvenance

    def __post_init__(self) -> None:
        # R5: tier-4 matches MUST have signal=None.
        if (
            self.match_confidence_tier == "human_verification_recommended"
            and self.signal is not None
        ):
            raise ValueError(
                "MatchedLine R5: human_verification_recommended tier MUST "
                f"have signal=None; got signal={self.signal!r}. "
                f"(line_id={self.line_id})"
            )

        # R15 narrowed: no positively-named prominence in basis values
        # (typing already enforces this; defense-in-depth check here is
        # for hand-constructed instances at runtime).
        for basis in self.match_basis:
            if "headline" in basis or "primary" in basis or "top" in basis:
                raise ValueError(
                    f"MatchedLine R15 (narrowed v0.3): match_basis value "
                    f"{basis!r} implies prominence — prohibited."
                )


# ============================================================
# § 4 — GAP INDICATOR (spec § 2.4 — RENAMED v0.2)
# ============================================================

@dataclass(frozen=True)
class GapIndicator:
    """A BOQ item not present in the contractor's quote.

    Per R16: `interpretation` defaults to 'likely_oversight' (most
    generous). Other tiers REQUIRE positive evidence in the quote
    (e.g., "labor only" notation → 'may_be_deferred_to_later_phase').
    C17 NEVER defaults to assuming hidden intent."""

    boq_id:                str
    boq_label:             str
    expected_quantity:     AttestedValue
    expected_unit:         str
    expected_total_low_high: Tuple[float, float]    # (low, high) ₹
    interpretation:        GapInterpretation
    severity:              GapSeverity
    advisory_note:         str        # R2 advisory-tone (lint-enforced)

    def __post_init__(self) -> None:
        lo, hi = self.expected_total_low_high
        if lo > hi:
            raise ValueError(
                f"GapIndicator.expected_total_low_high: low ({lo}) > "
                f"high ({hi}) — invalid range for boq_id={self.boq_id}."
            )
        if lo < 0 or hi < 0:
            raise ValueError(
                f"GapIndicator.expected_total_low_high must be non-negative; "
                f"got ({lo}, {hi}) for boq_id={self.boq_id}."
            )


# ============================================================
# § 5 — UNMATCHED QUOTE LINE
# ============================================================

@dataclass(frozen=True)
class UnmatchedQuoteLine:
    """A line in the contractor's quote that no BOQ item matched.

    Distinct from GapIndicator (which is the converse — BOQ items
    missing from the quote). Per spec § 2.1 — lex-ASC sort by line_id.

    May represent: legitimate scope-extras not in our BOQ, OCR-garbled
    lines, or lines we couldn't canonicalize even at tier-4 confidence.
    Per R2 the `advisory_note` MUST be reference-tone, never accusatory."""

    line_id:           str
    quote_label:       str
    quote_quantity:    Optional[AttestedValue]   # may be unparseable
    quote_unit:        str
    quote_rate:        Optional[AttestedValue]
    quote_total:       AttestedValue              # at minimum, ₹ stated
    advisory_note:     str


# ============================================================
# § 6 — LUMP SUM INDICATOR (spec § 2.5 — RENAMED v0.2)
# ============================================================

@dataclass(frozen=True)
class LumpSumIndicator:
    """A line item priced as a single ₹ figure with no unit-rate
    decomposition. Per spec § 2.5 — 'indicator', not 'suspicious'.
    The lump sum may have legitimate reasons; this flags it for the
    homeowner to clarify with the contractor.

    R2 enforcement: advisory_note follows reference-tone template
    ("Could you walk me through how you've priced {label}?")."""

    line_id:           str
    quote_label:       str
    quote_total:       AttestedValue
    pct_of_quote_total: AttestedValue        # LOCALLY_DERIVED
    advisory_note:     str


# ============================================================
# § 7 — DECOMPOSITION ACKNOWLEDGMENT (spec § 2.6 — NEW v0.2 / R18)
# ============================================================

@dataclass(frozen=True)
class DecompositionAcknowledgment:
    """Per spec § 2.6 (NEW v0.2 — R18 BOQ decomposition pluralism).

    A contractor's quote that decomposes work differently than our BOQ
    is **legitimate-but-different**, never a defect.
    `alignment_quality_indicator` is NOT a verdict on the contractor
    — it's a signal about how well our comparison can structurally
    engage with the quote.

    Per spec § 26: when style != 'line_itemized', bundle-level
    comparison is BEST-EFFORT (threshold inflation 3.0×, tier
    downgrade, ReportConfidence capped at moderate_signal)."""

    detected_decomposition_style: DecompositionStyle
    alignment_quality_indicator:  AlignmentQualityIndicator
    advisory_note:                str


# ============================================================
# § 8 — TOTAL COMPARISON (spec § 2.7 — REVISED v0.2)
# ============================================================

@dataclass(frozen=True)
class TotalComparison:
    """Per spec § 2.7 — savings framing replaced with conversation
    range. Reference-tone headline_summary. NEVER "quote is X higher,
    you're being overcharged Y."

    Design Principles v3.1 Principle 2 — `our_estimate_total` is a
    TransparencyTriple (range + midpoint + derivation)."""

    quote_total:                    AttestedValue        # UPSTREAM_AUTHORITATIVE
    our_estimate_total:             TransparencyTriple   # range + derivation
    delta_amount:                   AttestedValue        # LOCALLY_DERIVED
    delta_pct:                      AttestedValue        # LOCALLY_DERIVED
    headline_summary:               str                  # reference-tone
    potential_conversation_range:   Tuple[float, float]  # (low, high) ₹
    conversation_range_disclaimer:  str

    def __post_init__(self) -> None:
        lo, hi = self.potential_conversation_range
        if lo > hi:
            raise ValueError(
                "TotalComparison.potential_conversation_range: "
                f"low ({lo}) > high ({hi})."
            )


# ============================================================
# § 9 — DISCUSSION BASELINE (spec § 2.8 — RENAMED v0.2)
# ============================================================

@dataclass(frozen=True)
class DiscussionBaseline:
    """Per spec § 2.8 (RENAMED v0.2 from CounterOffer).

    `adjusted_total` = our_estimate_total + reasonable contractor margin
    (R9 — never undercut, never inflated beyond
    RateProvider.contractor_margin_range_pct().high).

    `conversation_language` is reference-tone advisory text the homeowner
    can use in their next conversation with the contractor. NEVER
    confrontational. NEVER frames the contractor as adversary."""

    adjusted_total:           TransparencyTriple
    reasonable_margin_pct:    AttestedValue       # UPSTREAM_AUTHORITATIVE
    conversation_language:    str                 # R2 lint-enforced
    disclaimer:               str


# ============================================================
# § 10 — ITEMIZATION INDICATORS (spec § 2.9 — R13)
# ============================================================

@dataclass(frozen=True)
class ItemizationIndicators:
    """Per spec § 2.9 (REPLACES v0.1 ContractorCredibility).

    **The biggest v0.2 change.** v0.1 had `score: int (0-100)` and
    `tier: Literal["trustworthy", "reasonable", "needs_scrutiny",
    "high_risk"]`. Both REMOVED in v0.2.

    Per R13: these are **quote-formatting indicators**, NOT
    contractor competence indicators. `advisory_note` MUST contain
    the mandatory clause distinguishing the two."""

    itemization_completeness_pct: AttestedValue       # LOCALLY_DERIVED
    lump_sum_count:               int
    lump_sum_pct_of_total:        AttestedValue       # LOCALLY_DERIVED
    critical_items_present:       Tuple[str, ...]
    critical_items_gap:           Tuple[str, ...]
    margin_transparency:          MarginTransparencyKind
    rate_consistency:             RateConsistencyKind
    advisory_note:                str

    # R13 mandatory clause — exact text checked at orchestrator
    # ratification time. Defined here as a class constant so the
    # test suite can import it directly.
    R13_MANDATORY_CLAUSE_SUBSTRING: str = field(
        default=(
            "These indicators reflect how the quote was written, not the "
            "quality of work the contractor will deliver."
        ),
        init=False,
    )

    def __post_init__(self) -> None:
        # R13 enforcement at construction — the mandatory clause MUST
        # appear in advisory_note (substring match, case-sensitive).
        if self.R13_MANDATORY_CLAUSE_SUBSTRING not in self.advisory_note:
            raise ValueError(
                "ItemizationIndicators R13 violation: advisory_note must "
                "include the mandatory 'not contractor competence' clause. "
                f"Required substring: {self.R13_MANDATORY_CLAUSE_SUBSTRING!r}"
            )


# ============================================================
# § 11 — REPORT CONFIDENCE (spec § 2.10 — NEW v0.2 / R17)
# ============================================================

@dataclass(frozen=True)
class ReportConfidence:
    """Per spec § 2.10 (NEW v0.2 — R17 escape valve).

    Meta-indicator for the REPORT itself, not for the contractor.
    When match quality is low, the report carries an explicit
    advisory_note recommending human review."""

    total_quote_lines:               int
    high_confidence_matches:         int
    medium_confidence_matches:       int
    low_confidence_matches:          int
    human_verification_recommended:  int
    unmatched_quote_lines:           int

    overall_report_tier:             ReportConfidenceTier
    advisory_note:                   str

    def __post_init__(self) -> None:
        # Sanity: tier counts should sum to ≤ total_quote_lines.
        # Equality is the strict case (every line categorized); ≤ allows
        # for upstream-cancelled lines that don't appear anywhere.
        accounted = (
            self.high_confidence_matches
            + self.medium_confidence_matches
            + self.low_confidence_matches
            + self.human_verification_recommended
            + self.unmatched_quote_lines
        )
        if accounted > self.total_quote_lines:
            raise ValueError(
                "ReportConfidence: tier counts "
                f"({accounted}) exceed total_quote_lines "
                f"({self.total_quote_lines})."
            )


# ============================================================
# § 12 — TOP-LEVEL REPORT (spec § 2.1)
# ============================================================

@dataclass(frozen=True)
class QuoteComparisonReport:
    """The QUOTE COMPARISON ENGINE output.

    R15 (NARROWED v0.3): C17 designates no headline field. Field order
    here serves replay-determinism (R6) only. The downstream renderer
    chooses visual hierarchy.

    R8: schema is public-versioned API. Field additions require MINOR
    bump of C17_REPORT_SCHEMA_VERSION. Renames/removals = MAJOR bump."""

    # Identity & provenance
    source_quote_signature:        str       # sha256 of parsed quote
    source_boq_signature:          str       # sha256 of project BOQ
    c17_version:                   str       # C17_VERSION constant
    c17_schema_version:            int       # C17_REPORT_SCHEMA_VERSION
    jurisdiction_profile_id:       str
    declared_domain_scope:         str

    # R14: every report carries rate staleness
    rate_staleness_disclosure:     RateStalenessDisclosure

    # Match output
    matched_lines:                 Tuple[MatchedLine, ...]
    missing_from_quote:            Tuple[GapIndicator, ...]
    unmatched_quote_lines:         Tuple[UnmatchedQuoteLine, ...]
    lump_sum_indicators:           Tuple[LumpSumIndicator, ...]

    # R18: every report acknowledges decomposition style
    decomposition_acknowledgment:  DecompositionAcknowledgment

    # Aggregates
    total_comparison:              TotalComparison
    discussion_baseline:           DiscussionBaseline
    itemization_indicators:        ItemizationIndicators

    # R17: report-level escape valve
    report_confidence:             ReportConfidence

    # Passthrough + provenance
    advisory_flags:                Tuple[AdvisoryFlag, ...]
    upstream_check_provenance:     Tuple[CheckProvenance, ...]

    # Signatures (R6, R7, R8)
    canonical_replay_signature:    str
    presentation_signature:        str
    schema_descriptor_digest:      str

    def __post_init__(self) -> None:
        # R15 (narrowed v0.3) defence-in-depth: no field name implies
        # prominence. Typing already enforces this; runtime check
        # catches hand-constructed mistakes.
        prohibited_substrings = (
            "headline_", "is_headline", "prominence", "_top_concern",
            "_primary_signal", "highlight_field",
        )
        for fname in self.__dataclass_fields__:
            for proh in prohibited_substrings:
                if proh in fname:
                    raise ValueError(
                        "QuoteComparisonReport R15 (narrowed v0.3): "
                        f"field {fname!r} implies prominence — prohibited."
                    )

        # Signature shape sanity
        for fname, val in (
            ("source_quote_signature",     self.source_quote_signature),
            ("source_boq_signature",       self.source_boq_signature),
            ("canonical_replay_signature", self.canonical_replay_signature),
            ("presentation_signature",     self.presentation_signature),
            ("schema_descriptor_digest",   self.schema_descriptor_digest),
        ):
            if not isinstance(val, str) or not val:
                raise ValueError(
                    f"QuoteComparisonReport.{fname} must be non-empty str."
                )


# ============================================================
# § 13 — FAILURE RECORD (orchestrator collects WARN-mode failures here)
# ============================================================

@dataclass(frozen=True)
class FailedComparisonRecord:
    """When orchestrator runs in WARN mode and a PerQuoteLineError
    fires, the offending line is collected here instead of halting
    the whole report. Surfaced via advisory_flags on the report.

    Per spec § 4: this is the WARN-mode counterpart to STRICT-mode
    exception raises. STRICT mode never produces this."""

    line_id:           str
    failure_phase:     Literal["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]
    error_class:       str           # e.g. "QuoteLineCanonicalizationError"
    error_message:     str
    error_metadata:    str           # JSON-stable representation of error attrs
