"""
C17 — Phase δ — Signal derivation (rate_delta, PriceSignal)
==============================================================

Input:  PhaseAlphaOutput (canonical lines + decomposition)
        PhaseBetaOutput  (ProjectBOQ — for our_rate lookup)
        PhaseGammaOutput (match candidates with tiers)
Output: tuple[MatchedLine, ...] — fully-populated MatchedLine records

Responsibilities:
  1. For each MatchCandidate, compute rate_delta_pct and total_delta
     as LOCALLY_DERIVED AttestedValues (R3 — never blend quote_rate
     and our_rate AuthorityKinds).
  2. Bin rate_delta_pct into a PriceSignal per the thresholds in
     versioning.py (§ 6).
  3. Apply R5 downgrade:
       - ABOVE_REFERENCE_RANGE requires tier ∈ {high, medium}.
         Low-conf matches → ABOVE_TYPICAL.
       - HUMAN_VERIFICATION_RECOMMENDED matches → signal=None.
  4. Apply spec § 26.2 bundle-tier downgrade:
       - If detected_decomposition_style != "line_itemized" AND this
         particular match is on a bundle-context line (we lack
         per-line bundle context in v1.0, so we apply the downgrade
         uniformly when the WHOLE quote is non-line-itemized).
  5. Emit signal_explanation as R2-lint-clean advisory text.
  6. Surface SignalDerivationError for unrecoverable arithmetic
     (rate=0, NaN, inf).

Rule 11 self-analysis:
  1. The v1.0 simplification of "whole quote is non-line-itemized →
     apply bundle downgrade uniformly" is documented:
     B-C17-PER-LINE-BUNDLE-CONTEXT can refine later.
  2. signal_explanation templates are hard-coded; lint at emission
     would catch any drift. We DO lint here (defence in depth).
  3. our_rate_median may be 0 if RateProvider misconfiguration —
     handled with SignalDerivationError, NOT a silent /0.
  4. The "BELOW_TYPICAL" v0.1 enum collapsed into WITHIN_TYPICAL
     in v0.2 (spec § 2.3) — code reflects this; the only "below"
     signal is BELOW_TYPICAL_QUALITY_RISK at < -20%.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from buildemup.components.c16.contracts import (
    AttestedValue,
    AuthorityKind,
    CheckProvenance,
)
from buildemup.components.c17.advisory_lint import lint_advisory_text
from buildemup.components.c17.config import C17RuntimeConfig
from buildemup.components.c17.contracts import ProjectBOQ, ProjectBOQItem
from buildemup.components.c17.errors import SignalDerivationError
from buildemup.components.c17.phases.alpha_canonicalize import (
    PhaseAlphaOutput,
    QuoteLineCanonical,
)
from buildemup.components.c17.phases.beta_boq_assembly import PhaseBetaOutput
from buildemup.components.c17.phases.gamma_matching import (
    MatchCandidate,
    PhaseGammaOutput,
)
from buildemup.components.c17.schema import (
    FailedComparisonRecord,
    MatchConfidenceTier,
    MatchedLine,
    PriceSignal,
)
from buildemup.components.c17.versioning import (
    BUNDLE_THRESHOLD_INFLATION_FACTOR,
    C17_VERSION,
    EPSILON_RATE_DELTA_PCT,
    PRICE_SIGNAL_ABOVE_REFERENCE_PCT,
    PRICE_SIGNAL_ABOVE_TYPICAL_PCT,
    PRICE_SIGNAL_BELOW_QUALITY_RISK_PCT,
    PRICE_SIGNAL_WITHIN_TYPICAL_PCT,
)


@dataclass(frozen=True)
class PhaseDeltaOutput:
    matched_lines:    Tuple[MatchedLine, ...]
    failures:         Tuple[FailedComparisonRecord, ...]


# ============================================================
# § 1 — PHASE δ ENTRY
# ============================================================

def run_phase_delta(
    alpha_output: PhaseAlphaOutput,
    beta_output:  PhaseBetaOutput,
    gamma_output: PhaseGammaOutput,
    *,
    config:        C17RuntimeConfig,
) -> PhaseDeltaOutput:
    """Phase δ entry point."""
    # Index inputs for fast lookup
    quote_by_id = {ql.line_id: ql for ql in alpha_output.canonical_lines}
    boq_by_id = {it.boq_id: it for it in beta_output.project_boq.items}

    # Whole-quote bundle flag (spec § 26.2 simplification for v1.0)
    is_bundle_quote = (
        alpha_output.decomposition_ack.detected_decomposition_style
        != "line_itemized"
    )

    matched: List[MatchedLine] = []
    failures: List[FailedComparisonRecord] = []

    for cand in gamma_output.candidates:
        try:
            ml = _build_matched_line(
                cand,
                quote_line=quote_by_id[cand.line_id],
                boq_item=boq_by_id[cand.boq_id],
                is_bundle_quote=is_bundle_quote,
            )
            matched.append(ml)
        except SignalDerivationError as exc:
            if config.strict_mode == "strict":
                raise
            failures.append(FailedComparisonRecord(
                line_id=exc.line_id,
                failure_phase="delta",
                error_class="SignalDerivationError",
                error_message=str(exc),
                error_metadata=f"reason={exc.reason!r}",
            ))

    # Canonical sort by line_id for R6 determinism
    matched.sort(key=lambda m: m.line_id)

    return PhaseDeltaOutput(
        matched_lines=tuple(matched),
        failures=tuple(failures),
    )


# ============================================================
# § 2 — BUILD ONE MATCHED LINE
# ============================================================

def _build_matched_line(
    cand: MatchCandidate,
    *,
    quote_line: QuoteLineCanonical,
    boq_item:   ProjectBOQItem,
    is_bundle_quote: bool,
) -> MatchedLine:
    """Compute rate_delta_pct, total_delta, and PriceSignal for one
    candidate. Apply R5 downgrade + § 26.2 bundle downgrade."""

    # Defensive arithmetic guards
    if quote_line.rate is None or quote_line.quantity is None:
        # Insufficient data case — not a signal-derivation error per se
        # but a structural issue; surface INSUFFICIENT_DATA signal.
        return _build_insufficient_data_line(cand, quote_line, boq_item)

    our_rate_median_v = float(boq_item.rate_median.value)
    if our_rate_median_v <= 0 or math.isnan(our_rate_median_v) or math.isinf(our_rate_median_v):
        raise SignalDerivationError(
            f"Cannot compute rate_delta_pct for line[{cand.line_id}]: "
            f"our_rate_median is {our_rate_median_v} (boq_id={cand.boq_id}).",
            line_id=cand.line_id,
            reason=f"our_rate_median={our_rate_median_v}",
        )

    quote_rate_v = float(quote_line.rate)
    if math.isnan(quote_rate_v) or math.isinf(quote_rate_v):
        raise SignalDerivationError(
            f"Cannot compute rate_delta_pct for line[{cand.line_id}]: "
            f"quote_rate is {quote_rate_v}.",
            line_id=cand.line_id,
            reason=f"quote_rate={quote_rate_v}",
        )

    # rate_delta_pct = (quote - ours) / ours × 100
    rate_delta_pct = (quote_rate_v - our_rate_median_v) / our_rate_median_v * 100.0
    # total_delta = quote_total - our_total
    quote_total_v = float(quote_line.total)
    our_total_v = our_rate_median_v * float(quote_line.quantity)
    total_delta_v = quote_total_v - our_total_v

    # Provenance strings — note the AttestedValue derivation_note
    # MUST be non-empty for LOCALLY_DERIVED.
    rate_delta_av = AttestedValue(
        value=rate_delta_pct,
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note=(
            f"(quote_rate {quote_rate_v} - our_rate_median {our_rate_median_v}) "
            f"/ our_rate_median × 100"
        ),
    )
    total_delta_av = AttestedValue(
        value=total_delta_v,
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note=(
            f"quote_total {quote_total_v} - "
            f"(our_rate_median {our_rate_median_v} × quote_quantity {quote_line.quantity})"
        ),
    )

    quote_quantity_av = AttestedValue(
        value=float(quote_line.quantity),
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source=f"upstream_parser.line[{cand.line_id}].quantity",
    )
    quote_rate_av = AttestedValue(
        value=quote_rate_v,
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source=f"upstream_parser.line[{cand.line_id}].rate",
    )
    quote_total_av = AttestedValue(
        value=quote_total_v,
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source=f"upstream_parser.line[{cand.line_id}].total",
    )
    our_total_av = AttestedValue(
        value=our_total_v,
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note=(
            f"our_rate_median {our_rate_median_v} × quote_quantity {quote_line.quantity}"
        ),
    )

    # Tier coercion + R5 downgrade
    tier: MatchConfidenceTier = cand.tier  # type: ignore[assignment]

    # Compute raw signal
    raw_signal = _bin_to_price_signal(rate_delta_pct)

    # Apply R5: ABOVE_REFERENCE_RANGE requires high/medium match
    signal: Optional[PriceSignal]
    if tier == "human_verification_recommended":
        signal = None
    else:
        if raw_signal == PriceSignal.ABOVE_REFERENCE_RANGE and tier == "low":
            signal = PriceSignal.ABOVE_TYPICAL
        else:
            signal = raw_signal

    # Apply § 26.2 bundle-tier downgrade
    if is_bundle_quote and signal is not None:
        signal = _bundle_downgrade(signal)
        # Also widen the "within typical" zone via inflation factor —
        # if |rate_delta| was within (inflated_within_threshold), bump
        # to WITHIN_TYPICAL.
        inflated_within = (
            PRICE_SIGNAL_WITHIN_TYPICAL_PCT * BUNDLE_THRESHOLD_INFLATION_FACTOR
        )
        if abs(rate_delta_pct) <= inflated_within:
            signal = PriceSignal.WITHIN_TYPICAL

    # signal_explanation
    explanation = _signal_explanation(
        signal=signal,
        tier=tier,
        is_bundle_quote=is_bundle_quote,
        rate_delta_pct=rate_delta_pct,
        boq_label=boq_item.label,
    )
    lint_advisory_text(explanation, field_name="MatchedLine.signal_explanation")

    # Build the MatchedLine
    return MatchedLine(
        line_id=cand.line_id,
        quote_label=quote_line.raw_label,
        matched_boq_id=boq_item.boq_id,
        matched_boq_label=boq_item.label,
        match_confidence_tier=tier,
        match_basis=cand.basis,  # type: ignore[arg-type]
        quote_quantity=quote_quantity_av,
        quote_unit=quote_line.unit_normalised,
        quote_rate=quote_rate_av,
        quote_total=quote_total_av,
        our_quantity=boq_item.quantity,
        our_rate_median=boq_item.rate_median,
        our_rate_min=boq_item.rate_min,
        our_rate_max=boq_item.rate_max,
        our_total=our_total_av,
        rate_delta_pct=rate_delta_av,
        total_delta=total_delta_av,
        signal=signal,
        signal_explanation=explanation,
        provenance=CheckProvenance(
            upstream_component="c17_quote_comparison_engine",
            check_id=f"price_signal.{cand.line_id}",
            upstream_version=C17_VERSION,
            attested_field_name="signal",
        ),
    )


def _build_insufficient_data_line(
    cand: MatchCandidate,
    quote_line: QuoteLineCanonical,
    boq_item:   ProjectBOQItem,
) -> MatchedLine:
    """When quote_quantity or quote_rate is missing, we emit a
    MatchedLine with signal=INSUFFICIENT_DATA and zero deltas.

    Per R5 + § 2.3: this is distinct from signal=None (which is
    the tier-4 case). INSUFFICIENT_DATA explicitly says "we have a
    match but the line's price data is incomplete; can't derive
    a signal." The downstream renderer surfaces this differently
    from a no-signal tier-4 match."""
    quote_quantity_av = AttestedValue(
        value=float(quote_line.quantity) if quote_line.quantity is not None else 0.0,
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source=f"upstream_parser.line[{cand.line_id}].quantity_or_zero",
    )
    quote_rate_av = AttestedValue(
        value=float(quote_line.rate) if quote_line.rate is not None else 0.0,
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source=f"upstream_parser.line[{cand.line_id}].rate_or_zero",
    )
    quote_total_av = AttestedValue(
        value=float(quote_line.total),
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source=f"upstream_parser.line[{cand.line_id}].total",
    )
    zero_delta = AttestedValue(
        value=0.0,
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note="signal=INSUFFICIENT_DATA — quote rate/qty missing; delta set to 0",
    )
    explanation = (
        f"The {boq_item.label} line's quantity or unit rate isn't "
        "clearly stated in the quote. It's worth asking the contractor "
        "to confirm the breakdown so we can run a meaningful comparison."
    )
    lint_advisory_text(explanation, field_name="MatchedLine.signal_explanation")
    tier: MatchConfidenceTier = cand.tier  # type: ignore[assignment]
    # R5: if tier-4, signal MUST be None — override INSUFFICIENT_DATA
    signal: Optional[PriceSignal] = (
        None if tier == "human_verification_recommended"
        else PriceSignal.INSUFFICIENT_DATA
    )
    return MatchedLine(
        line_id=cand.line_id,
        quote_label=quote_line.raw_label,
        matched_boq_id=boq_item.boq_id,
        matched_boq_label=boq_item.label,
        match_confidence_tier=tier,
        match_basis=cand.basis,  # type: ignore[arg-type]
        quote_quantity=quote_quantity_av,
        quote_unit=quote_line.unit_normalised,
        quote_rate=quote_rate_av,
        quote_total=quote_total_av,
        our_quantity=boq_item.quantity,
        our_rate_median=boq_item.rate_median,
        our_rate_min=boq_item.rate_min,
        our_rate_max=boq_item.rate_max,
        our_total=AttestedValue(
            value=float(boq_item.total_median.value),
            authority=AuthorityKind.LOCALLY_DERIVED,
            derivation_note="passed through from project BOQ total_median",
        ),
        rate_delta_pct=zero_delta,
        total_delta=zero_delta,
        signal=signal,
        signal_explanation=explanation,
        provenance=CheckProvenance(
            upstream_component="c17_quote_comparison_engine",
            check_id=f"price_signal.{cand.line_id}",
            upstream_version=C17_VERSION,
            attested_field_name="signal",
        ),
    )


# ============================================================
# § 3 — PRICE SIGNAL BINNING
# ============================================================

def _bin_to_price_signal(rate_delta_pct: float) -> PriceSignal:
    """Bin rate_delta_pct into a PriceSignal per spec § 6 thresholds.

    Epsilon-aware: |Δ| < EPSILON_RATE_DELTA_PCT collapses to
    WITHIN_TYPICAL. Avoids spurious tier flips from floating-point
    noise."""
    if abs(rate_delta_pct) < EPSILON_RATE_DELTA_PCT:
        return PriceSignal.WITHIN_TYPICAL

    if rate_delta_pct > PRICE_SIGNAL_ABOVE_REFERENCE_PCT:
        return PriceSignal.ABOVE_REFERENCE_RANGE
    if rate_delta_pct > PRICE_SIGNAL_ABOVE_TYPICAL_PCT:
        return PriceSignal.ABOVE_TYPICAL
    if rate_delta_pct >= -PRICE_SIGNAL_WITHIN_TYPICAL_PCT:
        return PriceSignal.WITHIN_TYPICAL
    if rate_delta_pct < PRICE_SIGNAL_BELOW_QUALITY_RISK_PCT:
        return PriceSignal.BELOW_TYPICAL_QUALITY_RISK
    # In [-20%, -5%) — per spec § 2.3 (v0.2), this collapses to
    # WITHIN_TYPICAL (no accusation of contractor losing money).
    return PriceSignal.WITHIN_TYPICAL


def _bundle_downgrade(s: PriceSignal) -> PriceSignal:
    """Spec § 26.2: bundle-context matches downgrade one tier."""
    if s == PriceSignal.ABOVE_REFERENCE_RANGE:
        return PriceSignal.ABOVE_TYPICAL
    if s == PriceSignal.ABOVE_TYPICAL:
        return PriceSignal.WITHIN_TYPICAL
    return s


# ============================================================
# § 4 — SIGNAL EXPLANATION TEMPLATES (R2 lint-clean)
# ============================================================

def _signal_explanation(
    *,
    signal:           Optional[PriceSignal],
    tier:             MatchConfidenceTier,
    is_bundle_quote:  bool,
    rate_delta_pct:   float,
    boq_label:        str,
) -> str:
    """Reference-tone advisory text for the signal."""
    if signal is None:
        # Tier-4 match — explain WHY we didn't emit a signal
        return (
            f"We found a possible match for this line ({boq_label}), "
            "but our confidence in the match isn't high enough to emit "
            "a price comparison. It's worth confirming the line item "
            "with the contractor before drawing conclusions."
        )

    sign_str = f"{rate_delta_pct:+.1f}%"
    bundle_note = (
        " The quote uses a bundle structure rather than line-item "
        "rates, so this comparison is approximate."
        if is_bundle_quote else ""
    )

    # B-C17-LEGITIMATE-PREMIUM-DISCLAIMER (S55 Batch 3): one principle-
    # aligned sentence acknowledging that above-reference rates can have
    # legitimate sources. Stays advisory-tone-clean (R2 lint passes); we
    # explicitly do NOT model premium-spec / site-difficulty / urgency.
    _LEGITIMATE_PREMIUM_NOTE = (
        " Higher rates can reflect premium specifications, complex site "
        "conditions, or specialised workmanship — worth asking the "
        "contractor what's included."
    )

    if signal == PriceSignal.ABOVE_REFERENCE_RANGE:
        return (
            f"This rate is above our reference range for {boq_label} "
            f"in Chennai 2026 (delta {sign_str}). Worth asking the "
            f"contractor about the specification."
            f"{_LEGITIMATE_PREMIUM_NOTE}{bundle_note}"
        )
    if signal == PriceSignal.ABOVE_TYPICAL:
        return (
            f"This rate is above the typical range for {boq_label} "
            f"in Chennai 2026 (delta {sign_str}). Some variation here "
            f"is normal; the difference is worth a clarifying "
            f"question.{bundle_note}"
        )
    if signal == PriceSignal.WITHIN_TYPICAL:
        return (
            f"This rate is within the typical range for {boq_label} "
            f"in Chennai 2026 (delta {sign_str}).{bundle_note}"
        )
    if signal == PriceSignal.BELOW_TYPICAL_QUALITY_RISK:
        return (
            f"This rate is below our reference range for {boq_label} "
            f"in Chennai 2026 (delta {sign_str}). Lower rates can "
            "reflect bulk-buying or efficient operations, or can "
            "signal quality risk — it's worth asking the contractor "
            f"about the specification and brand they plan to use.{bundle_note}"
        )
    # INSUFFICIENT_DATA handled by _build_insufficient_data_line.
    return (
        f"The {boq_label} line's data is incomplete; we couldn't "
        f"derive a clean comparison.{bundle_note}"
    )
