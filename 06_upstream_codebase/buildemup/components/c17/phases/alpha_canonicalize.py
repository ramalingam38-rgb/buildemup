"""
C17 — Phase α — Quote canonicalization
========================================

Input:  ParsedQuote (parser output)
Output: tuple[QuoteLineCanonical, ...]  +  DecompositionAcknowledgment

Responsibilities:
  1. Validate ParsedQuote (post-construction hard-ceiling check).
  2. Verify parsed_quote_signature matches what we'd compute.
  3. Canonicalize labels: strip, lower, collapse whitespace.
  4. Compute total_per_line_inferred = quantity * rate when both
     present; cross-check against the stated total.
  5. Classify the quote's decomposition style (line_itemized / turnkey /
     labor_material / room_based / milestone_based / hybrid / unknown).
  6. Detect informal-construction-arrangement heuristic signals
     (spec § 1.4) and surface advisory flag.

Per spec § 3 phase γ section: phase α now PRECEDES phase γ's matching;
its decomposition classification is consumed by phase γ.

Rule 11 self-analysis:
  1. The decomposition classifier is heuristic — no labelled corpus
     in v1.0. We use signal-counts not weighted scores; calibration
     is via B-C17-DECOMPOSITION-CALIBRATION. Documented.
  2. Cross-check of stated vs computed total uses
     EPSILON_AMOUNT_INR — banker's-rounding tolerance.
  3. Empty quotes (0 line_items) → 'turnkey_bundles' if quote_total
     > 0 else error. Edge case captured.
  4. Parser hint is a hint, not authoritative. We use it as
     tiebreaker only; our own detection overrides if confident.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from buildemup.components.c17.advisory_lint import lint_advisory_text
from buildemup.components.c17.cache_keys import compute_parsed_quote_signature
from buildemup.components.c17.config import C17RuntimeConfig
from buildemup.components.c17.contracts import ParsedQuote, ParsedQuoteLine
from buildemup.components.c17.errors import (
    ParsedQuoteShapeError,
    QuoteLineCanonicalizationError,
    UpstreamSchemaDriftError,
)
from buildemup.components.c17.schema import DecompositionAcknowledgment
from buildemup.components.c17.versioning import (
    EPSILON_AMOUNT_INR,
    INFORMAL_HEURISTIC_BRAND_SPEC_MIN_PCT,
    INFORMAL_HEURISTIC_LINE_COUNT_MIN,
    INFORMAL_HEURISTIC_LUMP_SUM_MAX_PCT,
    INFORMAL_HEURISTIC_UNIT_RATE_MIN_PCT,
)


# ============================================================
# § 1 — CANONICAL LINE TYPE (intermediate, not user-facing)
# ============================================================


class ArithmeticMismatchSeverity(str, Enum):
    """B-C17-ARITHMETIC-MISMATCH-INDICATOR (S55 Batch 3).

    Classifies a `qty × rate ≠ stated_total` discrepancy. Surfaces in
    phase ζ as a structured indicator instead of an opaque raw_notes
    string.

    Bands (per backlog spec):
      NONE: no quantity/rate, or the delta is below EPSILON_AMOUNT_INR.
      ROUNDING: Δ < 1% of stated total — banker's-rounding; silent.
      OCR_OR_ARITHMETIC_ERROR: 1% ≤ Δ < 10% — informational indicator.
      SUSPICIOUS_DISCREPANCY: Δ ≥ 10% — advisory surfaced to user.
    """
    NONE = "none"
    ROUNDING = "rounding"
    OCR_OR_ARITHMETIC_ERROR = "ocr_or_arithmetic_error"
    SUSPICIOUS_DISCREPANCY = "suspicious_discrepancy"


@dataclass(frozen=True)
class QuoteLineCanonical:
    """Phase α output. NOT in QuoteComparisonReport schema — purely
    intermediate. Phases β / γ / δ / ε / ζ consume tuples of these."""

    line_id:           str
    raw_label:         str        # verbatim
    canonical_label:   str        # lower, stripped, whitespace-collapsed
    quantity:          Optional[float]
    unit_normalised:   str        # e.g. "sqft" / "cum" / "bag" / "" for lump
    rate:              Optional[float]
    total:             float
    is_lump_sum:       bool       # phase α classification (definitive)
    parser_hint_used:  bool       # provenance — was hint authoritative?
    raw_notes:         str = ""
    # B-C17-ARITHMETIC-MISMATCH-INDICATOR (S55 Batch 3)
    arithmetic_mismatch_severity: ArithmeticMismatchSeverity = (
        ArithmeticMismatchSeverity.NONE
    )
    arithmetic_mismatch_delta_pct: Optional[float] = None


# ============================================================
# § 2 — LABEL CANONICALIZATION
# ============================================================

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s.\-/]+")


def _canon_label(s: str) -> str:
    """Lower, strip outer ws, collapse internal ws, drop most punctuation."""
    out = s.lower().strip()
    out = _PUNCT_RE.sub(" ", out)
    out = _WS_RE.sub(" ", out)
    return out.strip()


# ============================================================
# § 3 — UNIT NORMALISATION
# ============================================================

_UNIT_SYNONYMS: dict[str, str] = {
    # Volume / area
    "sqft":  "sqft", "sq.ft": "sqft", "sq ft": "sqft", "sft": "sqft",
    "sqm":   "sqm",  "sq.m":  "sqm",  "sq m":  "sqm",  "m2":  "sqm",
    "cft":   "cft",  "cu.ft": "cft",
    "cum":   "cum",  "cu.m":  "cum",  "m3":    "cum",
    "rft":   "rft",  "rmt":   "rmt",  "rm":    "rmt",
    # Mass
    "kg":    "kg",   "kgs":   "kg",
    "tonne": "tonne","tonnes": "tonne","mt":   "tonne",
    # Bags / each
    "bag":   "bag",  "bags":  "bag",
    "nos":   "nos",  "no":    "nos",  "no.":   "nos",
    "each":  "nos",  "ea":    "nos",
    # Lump
    "ls":    "ls",   "lump":  "ls",   "lumpsum": "ls",  "lump sum": "ls",
    "":      "",     # empty stays empty (true lump-sum lines)
}


def _normalise_unit(unit: str) -> str:
    """Map common spelling variants to canonical unit code."""
    key = unit.strip().lower()
    return _UNIT_SYNONYMS.get(key, key)


def _is_lump_sum_unit(unit: str) -> bool:
    return unit == "ls" or unit == ""


# ============================================================
# § 4 — PHASE α ENTRY
# ============================================================

@dataclass(frozen=True)
class PhaseAlphaOutput:
    """Bundled output of phase α."""
    canonical_lines:        Tuple[QuoteLineCanonical, ...]
    decomposition_ack:      DecompositionAcknowledgment
    informal_signal_count:  int      # for spec § 1.4 escalation
    quote_total_inr:        float    # echoed from ParsedQuote
    verified_signature:     str      # signature we computed


def run_phase_alpha(
    parsed_quote: ParsedQuote,
    *,
    config: C17RuntimeConfig,
) -> PhaseAlphaOutput:
    """Phase α entry point."""
    # 1. Verify signature
    computed_sig = compute_parsed_quote_signature(parsed_quote)
    if parsed_quote.parsed_quote_signature and parsed_quote.parsed_quote_signature != computed_sig:
        raise UpstreamSchemaDriftError(
            "ParsedQuote.parsed_quote_signature does not match what C17 "
            f"computed. Provided={parsed_quote.parsed_quote_signature!r}, "
            f"computed={computed_sig!r}. Possible parser-version mismatch "
            "or in-flight mutation.",
            upstream_component="upstream_parser",
            expected_version=None,
            observed_version=None,
        )

    # 2. Canonicalize each line
    canonical: list[QuoteLineCanonical] = []
    for li in parsed_quote.line_items:
        canonical.append(_canon_line(li, config=config))

    canonical_tuple = tuple(canonical)

    # 3. Classify decomposition + informal-arrangement detection
    decomp_ack, informal_count = _classify_decomposition(
        canonical_tuple,
        parser_hint=parsed_quote.parser_hint_decomposition_style,
        quote_total_inr=parsed_quote.quote_total_inr,
    )

    # 4. Lint advisory text from the decomposition ack (defence-in-depth)
    lint_advisory_text(decomp_ack.advisory_note,
                       field_name="DecompositionAcknowledgment.advisory_note")

    return PhaseAlphaOutput(
        canonical_lines=canonical_tuple,
        decomposition_ack=decomp_ack,
        informal_signal_count=informal_count,
        quote_total_inr=parsed_quote.quote_total_inr,
        verified_signature=computed_sig,
    )


# ============================================================
# § 5 — PER-LINE CANONICALIZATION
# ============================================================

def _canon_line(
    li: ParsedQuoteLine,
    *,
    config: C17RuntimeConfig,
) -> QuoteLineCanonical:
    """Canonicalize one line. Single-line errors are PerQuoteLineError
    and routed by orchestrator (STRICT vs WARN)."""
    canon = _canon_label(li.raw_label)
    if not canon:
        raise QuoteLineCanonicalizationError(
            f"Line[{li.line_id}] label canonicalizes to empty string.",
            line_id=li.line_id,
            reason="empty canonical label",
        )

    unit_norm = _normalise_unit(li.unit)

    # Compute / cross-check total
    mismatch_severity = ArithmeticMismatchSeverity.NONE
    mismatch_delta_pct: Optional[float] = None
    if li.quantity is not None and li.rate is not None:
        computed = li.quantity * li.rate
        delta = abs(computed - li.total)
        if delta > EPSILON_AMOUNT_INR and li.total != 0.0:
            # B-C17-ARITHMETIC-MISMATCH-INDICATOR severity bands.
            delta_pct = (delta / abs(li.total)) * 100.0
            mismatch_delta_pct = delta_pct
            if delta_pct < 1.0:
                mismatch_severity = ArithmeticMismatchSeverity.ROUNDING
            elif delta_pct < 10.0:
                mismatch_severity = (
                    ArithmeticMismatchSeverity.OCR_OR_ARITHMETIC_ERROR
                )
            else:
                mismatch_severity = (
                    ArithmeticMismatchSeverity.SUSPICIOUS_DISCREPANCY
                )

        if abs(computed - li.total) > max(EPSILON_AMOUNT_INR, 0.01 * li.total):
            # Significant mismatch — record but don't fail.
            # The CONTRACTOR's total is authoritative for R3 (we don't
            # blend); but we surface the inconsistency in raw_notes.
            note = (
                f"qty×rate computed ₹{computed:.2f} differs from "
                f"stated total ₹{li.total:.2f}"
            )
            # We append, not replace, to preserve parser provenance.
            new_notes = (li.raw_notes + " | " + note).strip(" |") if li.raw_notes else note
        else:
            new_notes = li.raw_notes
    else:
        new_notes = li.raw_notes

    # Lump-sum classification:
    #   - parser hint (is_lump_sum_hint=True) → respect unless we have
    #     a clear unit and quantity (then override)
    #   - quantity AND rate present AND unit non-empty → NOT lump
    #   - unit empty / "ls" / total but no quantity → lump
    parser_hint_authoritative = False
    if li.quantity is not None and li.rate is not None and not _is_lump_sum_unit(unit_norm):
        is_lump = False
    elif _is_lump_sum_unit(unit_norm) or li.quantity is None or li.rate is None:
        is_lump = True
    else:
        is_lump = li.is_lump_sum_hint
        parser_hint_authoritative = li.is_lump_sum_hint

    return QuoteLineCanonical(
        line_id=li.line_id,
        raw_label=li.raw_label,
        canonical_label=canon,
        quantity=li.quantity,
        unit_normalised=unit_norm,
        rate=li.rate,
        total=li.total,
        is_lump_sum=is_lump,
        parser_hint_used=parser_hint_authoritative,
        raw_notes=new_notes,
        arithmetic_mismatch_severity=mismatch_severity,
        arithmetic_mismatch_delta_pct=mismatch_delta_pct,
    )


# ============================================================
# § 6 — DECOMPOSITION CLASSIFIER + INFORMAL-ARRANGEMENT DETECTOR
# ============================================================

# Room-based markers
_ROOM_TOKENS = (
    "bedroom", "kitchen", "living", "dining", "bathroom", "toilet",
    "balcony", "utility", "pooja", "puja", "stair", "lobby", "porch",
)

# Milestone-based markers
_MILESTONE_TOKENS = (
    "foundation", "plinth", "rcc", "slab", "roof", "finish", "handover",
    "milestone", "stage", "phase", "rough", "completion",
)

# Labor-material split markers
_LABOR_TOKENS = ("labor", "labour", "mistry")
_MATERIAL_TOKENS = ("material", "supply")

# Turnkey / bundle markers
_TURNKEY_TOKENS = (
    "turnkey", "package", "complete", "all-inclusive", "bundled", "lumpsum work",
)


def _classify_decomposition(
    lines: Tuple[QuoteLineCanonical, ...],
    *,
    parser_hint: Optional[str],
    quote_total_inr: float,
) -> tuple[DecompositionAcknowledgment, int]:
    """Returns (DecompositionAcknowledgment, informal_signal_count)."""
    n = len(lines)
    if n == 0:
        # Empty quote with non-zero total → turnkey
        if quote_total_inr > 0:
            return (
                DecompositionAcknowledgment(
                    detected_decomposition_style="turnkey_bundles",
                    alignment_quality_indicator="low",
                    advisory_note=(
                        "Your contractor's quote arrived as a single overall "
                        "figure with no line-item breakdown. This is a "
                        "legitimate quoting style. Our line-by-line comparison "
                        "won't apply directly; we've focused on the overall "
                        "total. It's worth asking the contractor for a written "
                        "breakdown of what's included."
                    ),
                ),
                0,
            )
        raise ParsedQuoteShapeError(
            "ParsedQuote has zero line_items AND zero quote_total_inr — "
            "no content to compare.",
            offending_field="line_items",
            offending_value=0,
        )

    n_lump = sum(1 for l in lines if l.is_lump_sum)
    n_line_itemized = n - n_lump

    pct_lump_count = (n_lump / n) * 100.0
    pct_lump_value = (
        sum(l.total for l in lines if l.is_lump_sum) / quote_total_inr * 100.0
        if quote_total_inr > 0
        else 0.0
    )
    pct_unit_rate = (n_line_itemized / n) * 100.0

    # Token scans on canonical labels
    n_room = sum(
        1 for l in lines if any(t in l.canonical_label for t in _ROOM_TOKENS)
    )
    n_milestone = sum(
        1 for l in lines if any(t in l.canonical_label for t in _MILESTONE_TOKENS)
    )
    n_labor = sum(
        1 for l in lines if any(t in l.canonical_label for t in _LABOR_TOKENS)
    )
    n_material = sum(
        1 for l in lines if any(t in l.canonical_label for t in _MATERIAL_TOKENS)
    )
    n_turnkey = sum(
        1 for l in lines if any(t in l.canonical_label for t in _TURNKEY_TOKENS)
    )

    # Decision tree (heuristic; tunable per B-C17-DECOMPOSITION-CALIBRATION)
    # Priority: explicit-turnkey > room > milestone > labor/material split
    # > line-itemized > hybrid > unknown.

    style: str
    alignment: str

    if pct_lump_value >= 60.0 or n_turnkey >= max(1, n * 0.3):
        style = "turnkey_bundles"
        alignment = "low"
    elif n_room >= max(2, n * 0.4) and pct_unit_rate >= 30.0:
        style = "room_based"
        alignment = "moderate"
    elif n_milestone >= max(2, n * 0.4):
        style = "milestone_based"
        alignment = "low"
    elif n_labor >= max(1, n * 0.2) and n_material >= max(1, n * 0.2):
        style = "labor_material_split"
        alignment = "moderate"
    elif pct_unit_rate >= 75.0:
        style = "line_itemized"
        alignment = "high"
    elif pct_unit_rate >= 30.0:
        style = "hybrid"
        alignment = "moderate"
    else:
        style = "unknown"
        alignment = "low"

    # If our detection is uncertain (unknown/hybrid) and the parser
    # provided a hint, lean into the hint.
    if style in ("unknown", "hybrid") and parser_hint in (
        "line_itemized", "turnkey_bundles", "labor_material_split",
        "room_based", "milestone_based",
    ):
        style = parser_hint
        alignment = "moderate"

    advisory_note = _decomposition_advisory(style)

    # Informal-construction heuristic count (spec § 1.4)
    informal_signals = 0
    # Signal 1: <10% of lines have brand/grade — we can only check
    # this indirectly (no brand field on QuoteLineCanonical), but
    # the unit-rate ratio + line count proxy this. We use a coarse
    # version: if pct_unit_rate is low AND n_line_itemized > 0, count.
    if pct_unit_rate < INFORMAL_HEURISTIC_UNIT_RATE_MIN_PCT:
        informal_signals += 1
    # Signal 2: lump-sum dominance
    if pct_lump_value > INFORMAL_HEURISTIC_LUMP_SUM_MAX_PCT:
        informal_signals += 1
    # Signal 3: scope-as-prose (very few lines for residential)
    if n < INFORMAL_HEURISTIC_LINE_COUNT_MIN:
        informal_signals += 1

    return (
        DecompositionAcknowledgment(
            detected_decomposition_style=style,  # type: ignore[arg-type]
            alignment_quality_indicator=alignment,  # type: ignore[arg-type]
            advisory_note=advisory_note,
        ),
        informal_signals,
    )


def _decomposition_advisory(style: str) -> str:
    """Per-style advisory notes (R2 lint-clean templates)."""
    return {
        "line_itemized": (
            "Your contractor's quote is itemised line by line. "
            "Our line-by-line comparison applies directly."
        ),
        "turnkey_bundles": (
            "Your contractor's quote uses turnkey bundles rather than "
            "line-item rates. This is a legitimate quoting style. Some "
            "of our line-by-line comparisons may not apply directly; "
            "we've focused on the bundle totals and key materials."
        ),
        "labor_material_split": (
            "Your contractor's quote separates labour from materials. "
            "This is a legitimate quoting style. Our line-by-line "
            "comparison adapts to this structure where it can."
        ),
        "room_based": (
            "Your contractor's quote is priced per room or area. "
            "This is a legitimate quoting style. Our comparison runs "
            "at the room aggregate level rather than per material."
        ),
        "milestone_based": (
            "Your contractor's quote is priced per construction stage "
            "(foundation, slab, finish, etc.). This is a legitimate "
            "quoting style. Per-stage comparisons may not map cleanly "
            "to our material BOQ; treat the comparison as a directional "
            "reference rather than a line-by-line check."
        ),
        "hybrid": (
            "Your contractor's quote mixes several pricing styles "
            "(some line items, some bundles). Our comparison engages "
            "where the structure aligns; some sections will be "
            "compared at coarser granularity."
        ),
        "unknown": (
            "Your contractor's quote arrived in a structure our "
            "automated comparison can't classify with high confidence. "
            "The signals below are partial. We'd suggest discussing "
            "specific items with the contractor for the parts that "
            "feel unclear."
        ),
    }[style]
