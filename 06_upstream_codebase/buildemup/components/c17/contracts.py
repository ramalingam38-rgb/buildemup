"""
C17 — Quote Comparison Engine — input contracts (upstream surface)
====================================================================

This module pins the SHAPE of every type C17 receives at its
boundary:

    ParsedQuote / ParsedQuoteLine   — output of the upstream parser
                                       (OCR + Claude API). Parser is
                                       OUT OF SCOPE for C17 (spec § 1).
                                       v1.0 ships with this contract;
                                       parser team builds against it.

    ProjectBOQ / ProjectBOQItem     — assembled from C7 cost estimates,
                                       C16 dual-drawing bundle metadata,
                                       and RateProvider rates. Phase β
                                       does the assembly; this is the
                                       output of phase β consumed by
                                       phases γ–ζ.

The output schema (QuoteComparisonReport) lives in schema.py.

Rule 11 self-analysis:
    1. ParsedQuote has both `line_items` AND `lump_sum_lines` — the
       parser may or may not pre-classify lines. Phase α normalises;
       so the boundary accepts both shapes. Documented.
    2. ProjectBOQItem.brand/grade/is_code are Optional[str], not str.
       BOQ items derived from generic categories may have no brand;
       still useful as fuzzy-match candidates. Phase γ's match-basis
       reflects what's actually present.
    3. ParsedQuote.line_items may be empty for a quote that is 100%
       lump-sum (e.g. one "Total: ₹35L" line). Phase α handles this
       — DecompositionAcknowledgment.style='turnkey_bundles' fires.
    4. We do NOT validate signatures at construction (sha256 may not
       yet be computed at parse time). Orchestrator phase α validates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Tuple

from buildemup.components.c16.contracts import AttestedValue
from buildemup.components.c17.errors import (
    C17ConfigurationError,
    ParsedQuoteShapeError,
)
from buildemup.components.c17.versioning import (
    HARD_CEILING_LINE_AMOUNT_INR,
    HARD_CEILING_PARSED_QUOTE_LINE_COUNT,
    HARD_CEILING_QUOTE_TOTAL_INR,
    SUPPORTED_DOMAIN_SCOPES,
    SUPPORTED_JURISDICTIONS,
)


# ============================================================
# § 1 — PARSED QUOTE (upstream parser → C17 boundary)
# ============================================================

@dataclass(frozen=True)
class ParsedQuoteLine:
    """One line item from the upstream-parsed contractor quote.

    `line_id` is supplied by the parser and MUST be unique within a
    ParsedQuote (phase α validates). v1.0 expects sequential
    identifiers like "L001"–"L500".

    quantity / rate / total may all be Optional — a quote may have
    a labelled line with "₹2,50,000" total but no quantity/unit
    breakdown. That's a legitimate input; phase α classifies it as
    a lump-sum candidate."""

    line_id:        str
    raw_label:      str        # verbatim from the contractor's document
    quantity:       Optional[float]
    unit:           str        # may be empty for lump-sum lines
    rate:           Optional[float]
    total:          float      # required — every line has a ₹ figure
    is_lump_sum_hint: bool = False
    """Parser may flag obvious lump-sum lines (e.g., "Painting works")
    so phase α doesn't have to re-detect. Hint only — α can override."""

    raw_notes:      str = ""   # any annotation the parser captured

    def __post_init__(self) -> None:
        if not self.line_id:
            raise ParsedQuoteShapeError(
                "ParsedQuoteLine.line_id must be non-empty.",
                offending_field="line_id",
                offending_value=self.line_id,
            )
        if not self.raw_label:
            raise ParsedQuoteShapeError(
                f"ParsedQuoteLine[{self.line_id}].raw_label must be non-empty.",
                offending_field="raw_label",
                offending_value=self.raw_label,
            )
        if self.total < 0:
            raise ParsedQuoteShapeError(
                f"ParsedQuoteLine[{self.line_id}].total must be >= 0; "
                f"got {self.total}.",
                offending_field="total",
                offending_value=self.total,
            )
        if self.total > HARD_CEILING_LINE_AMOUNT_INR:
            raise ParsedQuoteShapeError(
                f"ParsedQuoteLine[{self.line_id}].total ({self.total}) "
                f"exceeds hard ceiling ₹1 crore.",
                offending_field="total",
                offending_value=self.total,
            )
        if self.quantity is not None and self.quantity < 0:
            raise ParsedQuoteShapeError(
                f"ParsedQuoteLine[{self.line_id}].quantity must be >= 0; "
                f"got {self.quantity}.",
                offending_field="quantity",
                offending_value=self.quantity,
            )
        if self.rate is not None and self.rate < 0:
            raise ParsedQuoteShapeError(
                f"ParsedQuoteLine[{self.line_id}].rate must be >= 0; "
                f"got {self.rate}.",
                offending_field="rate",
                offending_value=self.rate,
            )


@dataclass(frozen=True)
class ParsedQuote:
    """The output of the upstream OCR-and-Claude-API quote parser.

    Per spec § 1: the parser is OUT OF SCOPE for C17. This dataclass
    is the BOUNDARY between parser and C17. v1.0 ships with this
    contract pinned; future parser work builds against it.

    Hard-ceiling validation at construction (spec § 6):
      - line_items length ≤ 500
      - quote_total_inr ≤ ₹50 crore
      - per-line total ≤ ₹1 crore (enforced in ParsedQuoteLine)"""

    parsed_quote_id:        str         # parser-assigned UUID
    contractor_label:       str         # contractor's stated name (display only)
    quote_date_iso:         str         # ISO 8601 — when contractor issued the quote
    quote_total_inr:        float       # ₹ total (parser may sum from lines)

    line_items:             Tuple[ParsedQuoteLine, ...]

    # Parser-supplied signature; orchestrator phase α verifies
    parsed_quote_signature: str         # sha256 of canonicalised JSON

    # Optional pre-classification by parser (used as hint, not authoritative)
    parser_hint_decomposition_style: Optional[str] = None

    def __post_init__(self) -> None:
        if len(self.line_items) > HARD_CEILING_PARSED_QUOTE_LINE_COUNT:
            raise ParsedQuoteShapeError(
                f"ParsedQuote.line_items length ({len(self.line_items)}) "
                f"exceeds hard ceiling "
                f"{HARD_CEILING_PARSED_QUOTE_LINE_COUNT} (spec § 6).",
                offending_field="line_items",
                offending_value=len(self.line_items),
            )
        if self.quote_total_inr > HARD_CEILING_QUOTE_TOTAL_INR:
            raise ParsedQuoteShapeError(
                f"ParsedQuote.quote_total_inr ({self.quote_total_inr}) "
                f"exceeds hard ceiling ₹50 crore "
                f"({HARD_CEILING_QUOTE_TOTAL_INR}).",
                offending_field="quote_total_inr",
                offending_value=self.quote_total_inr,
            )
        if self.quote_total_inr < 0:
            raise ParsedQuoteShapeError(
                f"ParsedQuote.quote_total_inr must be >= 0; "
                f"got {self.quote_total_inr}.",
                offending_field="quote_total_inr",
                offending_value=self.quote_total_inr,
            )

        # Duplicate line_id check
        seen: set[str] = set()
        for li in self.line_items:
            if li.line_id in seen:
                raise ParsedQuoteShapeError(
                    f"ParsedQuote: duplicate line_id {li.line_id!r}.",
                    offending_field="line_id",
                    offending_value=li.line_id,
                )
            seen.add(li.line_id)


# ============================================================
# § 2 — PROJECT BOQ (phase β output)
# ============================================================

# Category taxonomy mirrors RateProvider categories. Phase β maps
# C7/C16 outputs into these BOQ categories.
BOQCategory = Literal[
    "structural_rcc",       # foundations, columns, beams, slabs
    "structural_steel",     # rebar
    "masonry",              # brickwork, blockwork, plaster
    "plumbing",             # WC, sink, taps, pipework
    "electrical",           # wiring, switches, fixtures
    "doors_windows",
    "flooring",
    "painting",
    "waterproofing",
    "miscellaneous",        # site clearance, scaffolding, etc.
]


@dataclass(frozen=True)
class ProjectBOQItem:
    """One BOQ line — assembled by phase β from C7 / C16 / RateProvider.

    NOT directly user-facing. Phase γ uses these as match candidates;
    phase ε aggregates them for TotalComparison. brand/grade/is_code
    are Optional because some BOQ items come from generic categories
    (e.g., "miscellaneous site work") with no IS-code mapping."""

    boq_id:           str
    label:            str            # canonical name, e.g. "Cement OPC 53"
    category:         BOQCategory
    quantity:         AttestedValue  # UPSTREAM_AUTHORITATIVE
    unit:             str

    # Rate range from RateProvider
    rate_median:      AttestedValue  # UPSTREAM_AUTHORITATIVE
    rate_min:         AttestedValue  # UPSTREAM_AUTHORITATIVE
    rate_max:         AttestedValue  # UPSTREAM_AUTHORITATIVE
    total_median:     AttestedValue  # LOCALLY_DERIVED (quantity × rate_median)

    # MaterialRate specificity (Optional — generic categories have no brand)
    brand:            Optional[str] = None
    grade:            Optional[str] = None
    is_code:          Optional[str] = None

    # Where this BOQ item originated upstream
    source_component: str = ""       # e.g. "c07_cost_estimator"
    source_section:   str = ""       # e.g. "structural_rcc.column_concrete"

    # Severity for GapIndicator if missing from quote
    severity_if_missing: Literal["critical", "important", "minor"] = "important"

    def __post_init__(self) -> None:
        if not self.boq_id:
            raise C17ConfigurationError(
                "ProjectBOQItem.boq_id must be non-empty.",
                offending_field="boq_id",
                offending_value=self.boq_id,
            )
        if not self.label:
            raise C17ConfigurationError(
                f"ProjectBOQItem[{self.boq_id}].label must be non-empty.",
                offending_field="label",
                offending_value=self.label,
            )
        if not self.unit:
            raise C17ConfigurationError(
                f"ProjectBOQItem[{self.boq_id}].unit must be non-empty.",
                offending_field="unit",
                offending_value=self.unit,
            )


@dataclass(frozen=True)
class ProjectBOQ:
    """The aggregated reference BOQ — phase β output, phase γ–ζ input.

    `boq_signature` is the sha256 over canonicalised items + version
    metadata. Computed by phase β; used in the report's source_boq_signature."""

    project_id:          str
    jurisdiction_profile_id: str
    declared_domain_scope:   str

    items:               Tuple[ProjectBOQItem, ...]
    boq_signature:       str            # sha256 of canonicalised items

    # Rate-provider provenance — propagates into RateStalenessDisclosure
    rate_provider_kb_version: str
    rate_provider_kb_date:    str       # ISO 8601
    rate_provider_locality:   str

    def __post_init__(self) -> None:
        if self.jurisdiction_profile_id not in SUPPORTED_JURISDICTIONS:
            raise C17ConfigurationError(
                f"ProjectBOQ.jurisdiction_profile_id "
                f"{self.jurisdiction_profile_id!r} not in "
                f"SUPPORTED_JURISDICTIONS={tuple(SUPPORTED_JURISDICTIONS)}.",
                offending_field="jurisdiction_profile_id",
                offending_value=self.jurisdiction_profile_id,
            )
        if self.declared_domain_scope not in SUPPORTED_DOMAIN_SCOPES:
            raise C17ConfigurationError(
                f"ProjectBOQ.declared_domain_scope "
                f"{self.declared_domain_scope!r} not in "
                f"SUPPORTED_DOMAIN_SCOPES={tuple(SUPPORTED_DOMAIN_SCOPES)}.",
                offending_field="declared_domain_scope",
                offending_value=self.declared_domain_scope,
            )
        # Duplicate boq_id check
        seen: set[str] = set()
        for it in self.items:
            if it.boq_id in seen:
                raise C17ConfigurationError(
                    f"ProjectBOQ: duplicate boq_id {it.boq_id!r}.",
                    offending_field="boq_id",
                    offending_value=it.boq_id,
                )
            seen.add(it.boq_id)


# ============================================================
# § 3 — ORCHESTRATOR MODE
# ============================================================

StrictMode = Literal["strict", "warn"]
"""Per spec § 4 / errors.py:
    'strict' — PerQuoteLineError raises immediately
    'warn'   — collected into FailedComparisonRecord; report continues"""
