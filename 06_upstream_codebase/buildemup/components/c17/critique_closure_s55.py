"""S55 Batch 3 — closures for the 5 remaining C17 critique findings.

Lives outside the LOCKED phase modules so the additions don't bleed
into the v0.3.LOCKED hot path. Phase consumers can opt in by importing
from here:

  B-C17-RATE-SANITY-DETECTOR
      `classify_rate_sanity(quote_rate, reference_min, reference_max)`
      returns a `RateSanityFlag` (HEALTHY / SUSPICIOUSLY_HIGH /
      SUSPICIOUSLY_LOW). Phase δ wires this in when it has a
      RateProvider envelope.

  B-C17-MATCH-BASIS-EXPANSION
      `ExpandedMatchBasis` dataclass — discoverable per-signal scores
      that γ can attach to a MatchCandidate (lexical / ontology /
      embedding / unit / IS-code / brand / grade). All fields
      Optional; γ populates only what it actually computed.

  B-C17-SEMANTIC-MATCH-LAYER
      `BOQ_DOMAIN_ONTOLOGY` + `classify_into_domain()` +
      `domains_compatible()`. γ uses these to downgrade tier-2/tier-3
      fuzzy matches whose domain categories disagree.

  B-C17-CONTRACTOR-RESPONSE-SECTION
      `ContractorResponse` dataclass — separately-signed rebuttal
      block. Optional field on QuoteComparisonReport.

  B-C17-ALTERNATE-MARKET-REFERENCES
      `AlternateMarketReference` dataclass — caller-supplied secondary
      rate sources displayed side-by-side with our ChennaiRateProvider.
      Optional tuple field on QuoteComparisonReport.

Tests live in `tests/test_s55_b_c17_critique_closures.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


# ───────────────────────────────────────────────────────────────────────
# B-C17-RATE-SANITY-DETECTOR
# ───────────────────────────────────────────────────────────────────────


class RateSanityFlag(str, Enum):
    """Result of an order-of-magnitude sanity check on a quoted rate
    against ChennaiRateProvider's reference envelope. Surfaces as an
    advisory note in δ; does NOT modify the rate (R3 preserved)."""

    HEALTHY = "healthy"
    SUSPICIOUSLY_HIGH = "suspiciously_high"   # rate > 10 × reference_max
    SUSPICIOUSLY_LOW = "suspiciously_low"     # rate < 0.1 × reference_min
    UNDETERMINED = "undetermined"             # reference envelope unavailable


def classify_rate_sanity(
    quote_rate: Optional[float],
    reference_min: Optional[float],
    reference_max: Optional[float],
    *,
    high_multiplier: float = 10.0,
    low_divisor: float = 10.0,
) -> RateSanityFlag:
    """B-C17-RATE-SANITY-DETECTOR (S55).

    Cheap defense-in-depth against OCR artifacts (e.g., '₹450' → '₹4500'
    or '₹4500' → '₹450'). ParsedQuote signatures cover post-parse
    tampering; this check covers pre-signature scan/parse corruption.

    Returns UNDETERMINED if any input is missing — caller surfaces no
    note in that case (we don't fabricate certainty).
    """
    if quote_rate is None or reference_min is None or reference_max is None:
        return RateSanityFlag.UNDETERMINED
    if quote_rate <= 0:
        return RateSanityFlag.UNDETERMINED
    if quote_rate > high_multiplier * reference_max:
        return RateSanityFlag.SUSPICIOUSLY_HIGH
    if quote_rate < reference_min / low_divisor:
        return RateSanityFlag.SUSPICIOUSLY_LOW
    return RateSanityFlag.HEALTHY


RATE_SANITY_ADVISORY_HIGH = (
    "The quoted rate is more than 10× our reference range for this "
    "line — this may be a parse or OCR artifact (e.g., an extra digit). "
    "Worth confirming the rate with the contractor before drawing "
    "conclusions."
)

RATE_SANITY_ADVISORY_LOW = (
    "The quoted rate is less than one-tenth of our reference range for "
    "this line — this may be a parse or OCR artifact (e.g., a missing "
    "digit). Worth confirming the rate with the contractor before "
    "drawing conclusions."
)


def rate_sanity_advisory_text(flag: RateSanityFlag) -> Optional[str]:
    """Return advisory text for surfacing the sanity flag to the user,
    or None when no advisory is warranted."""
    if flag == RateSanityFlag.SUSPICIOUSLY_HIGH:
        return RATE_SANITY_ADVISORY_HIGH
    if flag == RateSanityFlag.SUSPICIOUSLY_LOW:
        return RATE_SANITY_ADVISORY_LOW
    return None


# ───────────────────────────────────────────────────────────────────────
# B-C17-MATCH-BASIS-EXPANSION
# ───────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExpandedMatchBasis:
    """B-C17-MATCH-BASIS-EXPANSION (S55).

    Discoverable per-signal scores γ may attach to a MatchCandidate.
    Each field is Optional so γ populates only what it actually
    computed (e.g., embedding_cosine is None when the embedding stage
    is skipped). Stays discrete — no synthetic 0.0-1.0 'confidence'
    aggregate (deliberately rejected per spec to avoid false precision).
    """
    lexical_score: Optional[float] = None             # 0.0-1.0 fuzzy ratio
    ontology_compatibility: Optional[bool] = None     # B-C17-SEMANTIC-MATCH
    embedding_cosine: Optional[float] = None          # 0.0-1.0 cosine
    unit_compatible: Optional[bool] = None
    is_code_match: Optional[bool] = None
    brand_match: Optional[bool] = None
    grade_match: Optional[bool] = None


# ───────────────────────────────────────────────────────────────────────
# B-C17-SEMANTIC-MATCH-LAYER
# ───────────────────────────────────────────────────────────────────────


class BoqDomain(str, Enum):
    """Ontology categories used by the semantic-match downgrade gate.

    Per B-C17-SEMANTIC-MATCH-LAYER backlog. Categories drawn from
    ASCE / Vilnius Tech construction-text NER corpus (verified S51
    web search).
    """
    STRUCTURAL = "structural"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    FINISHING = "finishing"
    WATERPROOFING = "waterproofing"
    EARTHWORK = "earthwork"
    WET_ZONE = "wet_zone"
    MISC = "misc"
    UNKNOWN = "unknown"


# Keyword → domain mapping. First-match wins (order matters for
# overlapping keywords; e.g., "waterproof" before "water"). Lowered
# substring match against canonical_label.
_DOMAIN_KEYWORDS: Tuple[Tuple[str, BoqDomain], ...] = (
    # Waterproofing first — beats "water"
    ("waterproof", BoqDomain.WATERPROOFING),
    ("damp proof", BoqDomain.WATERPROOFING),
    ("dpc", BoqDomain.WATERPROOFING),
    # Wet zones
    ("toilet", BoqDomain.WET_ZONE),
    ("bathroom", BoqDomain.WET_ZONE),
    ("kitchen sink", BoqDomain.WET_ZONE),
    # Plumbing
    ("pipe", BoqDomain.PLUMBING),
    ("plumb", BoqDomain.PLUMBING),
    ("cpvc", BoqDomain.PLUMBING),
    ("upvc", BoqDomain.PLUMBING),
    ("ppr", BoqDomain.PLUMBING),
    ("tap", BoqDomain.PLUMBING),
    ("valve", BoqDomain.PLUMBING),
    ("sanitary", BoqDomain.PLUMBING),
    # Electrical
    ("wiring", BoqDomain.ELECTRICAL),
    ("conduit", BoqDomain.ELECTRICAL),
    ("switch", BoqDomain.ELECTRICAL),
    ("socket", BoqDomain.ELECTRICAL),
    ("mcb", BoqDomain.ELECTRICAL),
    ("electric", BoqDomain.ELECTRICAL),
    ("light", BoqDomain.ELECTRICAL),
    # Earthwork
    ("excavat", BoqDomain.EARTHWORK),
    ("backfill", BoqDomain.EARTHWORK),
    ("anti termite", BoqDomain.EARTHWORK),
    # Structural
    ("rcc", BoqDomain.STRUCTURAL),
    ("reinforced concrete", BoqDomain.STRUCTURAL),
    ("steel reinforcement", BoqDomain.STRUCTURAL),
    ("column", BoqDomain.STRUCTURAL),
    ("beam", BoqDomain.STRUCTURAL),
    ("slab", BoqDomain.STRUCTURAL),
    ("foundation", BoqDomain.STRUCTURAL),
    ("footing", BoqDomain.STRUCTURAL),
    ("brick", BoqDomain.STRUCTURAL),
    ("masonry", BoqDomain.STRUCTURAL),
    # Finishing
    ("paint", BoqDomain.FINISHING),
    ("plaster", BoqDomain.FINISHING),
    ("tile", BoqDomain.FINISHING),
    ("flooring", BoqDomain.FINISHING),
    ("granite", BoqDomain.FINISHING),
    ("marble", BoqDomain.FINISHING),
    ("door", BoqDomain.FINISHING),
    ("window", BoqDomain.FINISHING),
    ("ceiling", BoqDomain.FINISHING),
    ("texture", BoqDomain.FINISHING),
)


def classify_into_domain(canonical_label: str) -> BoqDomain:
    """B-C17-SEMANTIC-MATCH-LAYER (S55).

    Cheap keyword-table classifier. Returns BoqDomain.UNKNOWN when no
    keyword fires; downstream callers must treat UNKNOWN as 'don't
    downgrade' — we don't know enough to claim incompatibility.
    """
    text = canonical_label.lower()
    for keyword, domain in _DOMAIN_KEYWORDS:
        if keyword in text:
            return domain
    return BoqDomain.UNKNOWN


def domains_compatible(a: BoqDomain, b: BoqDomain) -> bool:
    """Return True iff two labels are in compatible domains.

    UNKNOWN is compatible with everything (we don't have enough signal
    to claim mismatch). Otherwise both must match.
    """
    if a == BoqDomain.UNKNOWN or b == BoqDomain.UNKNOWN:
        return True
    return a == b


# ───────────────────────────────────────────────────────────────────────
# B-C17-CONTRACTOR-RESPONSE-SECTION
# ───────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ContractorResponse:
    """B-C17-CONTRACTOR-RESPONSE-SECTION (S55).

    Optional rebuttal/context note attached to a QuoteComparisonReport.
    Separately-signed (response_signature) so we can verify it wasn't
    silently mutated after attachment, and never modifies upstream
    signals (signals stay R3-clean).

    Strengthens legal defensibility for reports shared publicly:
    contractors can attach context without forcing C17 to model it.
    """
    contractor_name: str
    response_text: str
    submitted_at_iso: str        # ISO 8601 UTC
    response_signature: str      # sha256 of (contractor_name|response_text|submitted_at_iso)

    def __post_init__(self) -> None:
        if not self.contractor_name:
            raise ValueError("ContractorResponse.contractor_name must be non-empty.")
        if not self.response_text:
            raise ValueError("ContractorResponse.response_text must be non-empty.")
        if not self.submitted_at_iso:
            raise ValueError("ContractorResponse.submitted_at_iso must be non-empty.")
        if not self.response_signature:
            raise ValueError("ContractorResponse.response_signature must be non-empty.")


# ───────────────────────────────────────────────────────────────────────
# B-C17-ALTERNATE-MARKET-REFERENCES
# ───────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AlternateMarketReference:
    """B-C17-ALTERNATE-MARKET-REFERENCES (S55).

    Caller-supplied secondary rate source displayed alongside
    ChennaiRateProvider in the report. We don't blend (R3 preserved);
    we show side-by-side. Reduces 'biased single source' exposure
    when reports are shared in dispute scenarios.

    Examples:
      - source_label='PWD Schedule of Rates 2025-26', currency='INR'
      - source_label='Mumbai builder quote (Sep 2025)', currency='INR'
    """
    source_label: str
    source_url_or_citation: str          # URL or PDF citation
    rate_inr_per_unit: float
    unit_normalised: str                 # e.g. 'sqft' / 'cum'
    boq_id: str                          # which BOQ line this references
    submitted_by: str                    # 'user' or 'contractor'

    def __post_init__(self) -> None:
        if not self.source_label:
            raise ValueError("AlternateMarketReference.source_label must be non-empty.")
        if self.rate_inr_per_unit <= 0:
            raise ValueError(
                "AlternateMarketReference.rate_inr_per_unit must be > 0; "
                f"got {self.rate_inr_per_unit}"
            )
        if self.submitted_by not in ("user", "contractor"):
            raise ValueError(
                "AlternateMarketReference.submitted_by must be 'user' or "
                f"'contractor'; got {self.submitted_by!r}"
            )


__all__ = [
    # B-C17-RATE-SANITY-DETECTOR
    "RateSanityFlag",
    "classify_rate_sanity",
    "rate_sanity_advisory_text",
    "RATE_SANITY_ADVISORY_HIGH",
    "RATE_SANITY_ADVISORY_LOW",
    # B-C17-MATCH-BASIS-EXPANSION
    "ExpandedMatchBasis",
    # B-C17-SEMANTIC-MATCH-LAYER
    "BoqDomain",
    "classify_into_domain",
    "domains_compatible",
    # B-C17-CONTRACTOR-RESPONSE-SECTION
    "ContractorResponse",
    # B-C17-ALTERNATE-MARKET-REFERENCES
    "AlternateMarketReference",
]
