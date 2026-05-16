"""
C17 — Phase ζ — Indicators + ReportConfidence + advisory flags
=================================================================

Input:  PhaseAlphaOutput, PhaseBetaOutput, PhaseGammaOutput,
        PhaseDeltaOutput, PhaseEpsilonOutput
Output: tuple of:
        - GapIndicator[]        (BOQ items missing from quote — R16 default)
        - LumpSumIndicator[]    (quote lump-sum lines)
        - UnmatchedQuoteLine[]  (quote lines without any BOQ candidate)
        - ItemizationIndicators (R13 — no aggregate score)
        - ReportConfidence      (R17 — escape valve)
        - AdvisoryFlag[]        (per-phase failures + informal heuristic)
        - upstream_check_provenance[]

This is the final assembly phase. Orchestrator wraps these into
QuoteComparisonReport and computes signatures.

Rule 11 self-analysis:
  1. GapIndicator emission: any BOQ item without a corresponding
     match in PhaseGammaOutput.candidates becomes a gap. Per R16,
     interpretation defaults to "likely_oversight" — we never
     escalate to a worse classification without positive evidence
     in the quote (e.g., parser-extracted "labour only" tag — not
     yet implemented; defaults uniformly).
  2. UnmatchedQuoteLine emission: complement of MatchedLine — quote
     lines without a BOQ candidate.
  3. ItemizationIndicators (R13): NO aggregate score, NO contractor
     tier, mandatory clause in advisory_note. The R13 substring is
     enforced by ItemizationIndicators.__post_init__ at construction.
  4. ReportConfidence (R17): logic order matters —
       (a) ≥ 25% tier-4 OR ≥ 50% bundle-value → human_review_recommended
       (b) high+medium pct ≥ 75% → high_signal
       (c) high+medium pct ≥ 50% → moderate_signal
       (d) otherwise → high_ambiguity
     R17 takes priority over (b)/(c)/(d) tiers.
  5. Informal-construction signal-count from phase α: if ≥ 2 signals
     fire (spec § 1.4), we DOWNGRADE the report tier to
     human_review_recommended regardless of match quality, with the
     explicit advisory note from § 1.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from buildemup.components.c16.contracts import AttestedValue, AuthorityKind, CheckProvenance
from buildemup.components.c16.schema import AdvisoryFlag
from buildemup.components.c17.advisory_lint import lint_advisory_text
from buildemup.components.c17.contracts import ProjectBOQItem
from buildemup.components.c17.phases.alpha_canonicalize import (
    PhaseAlphaOutput,
    QuoteLineCanonical,
)
from buildemup.components.c17.phases.beta_boq_assembly import PhaseBetaOutput
from buildemup.components.c17.phases.delta_verdicting import PhaseDeltaOutput
from buildemup.components.c17.phases.epsilon_totals import PhaseEpsilonOutput
from buildemup.components.c17.phases.gamma_matching import PhaseGammaOutput
from buildemup.components.c17.schema import (
    GapIndicator,
    ItemizationIndicators,
    LumpSumIndicator,
    MatchedLine,
    PriceSignal,
    ReportConfidence,
    UnmatchedQuoteLine,
)
from buildemup.components.c17.versioning import (
    BUNDLE_PCT_DOMINANCE_THRESHOLD,
    C17_VERSION,
    REPORT_TIER_HIGH_SIGNAL_PCT,
    REPORT_TIER_HUMAN_REVIEW_PCT,
    REPORT_TIER_MODERATE_SIGNAL_PCT,
)


@dataclass(frozen=True)
class PhaseZetaOutput:
    missing_from_quote:        Tuple[GapIndicator, ...]
    lump_sum_indicators:       Tuple[LumpSumIndicator, ...]
    unmatched_quote_lines:     Tuple[UnmatchedQuoteLine, ...]
    itemization_indicators:    ItemizationIndicators
    report_confidence:         ReportConfidence
    advisory_flags:            Tuple[AdvisoryFlag, ...]
    upstream_check_provenance: Tuple[CheckProvenance, ...]


def run_phase_zeta(
    alpha_output:   PhaseAlphaOutput,
    beta_output:    PhaseBetaOutput,
    gamma_output:   PhaseGammaOutput,
    delta_output:   PhaseDeltaOutput,
    epsilon_output: PhaseEpsilonOutput,
) -> PhaseZetaOutput:
    """Phase ζ entry point."""
    # Build lookup tables
    boq_items = beta_output.project_boq.items
    boq_by_id: Dict[str, ProjectBOQItem] = {it.boq_id: it for it in boq_items}
    quote_lines = alpha_output.canonical_lines
    quote_by_id: Dict[str, QuoteLineCanonical] = {ql.line_id: ql for ql in quote_lines}
    matched_lines = delta_output.matched_lines

    matched_boq_ids = {ml.matched_boq_id for ml in matched_lines}
    matched_line_ids = {ml.line_id for ml in matched_lines}

    # ----------------------------------------------------------
    # 1. GapIndicators — BOQ items without a matched line
    # ----------------------------------------------------------
    gap_indicators = _build_gap_indicators(boq_items, matched_boq_ids)

    # ----------------------------------------------------------
    # 2. LumpSumIndicators — from phase α's lump-sum-classified lines
    # ----------------------------------------------------------
    lump_sum_indicators = _build_lump_sum_indicators(
        quote_lines=quote_lines,
        lump_sum_line_ids=gamma_output.lump_sum_line_ids,
        quote_total_inr=alpha_output.quote_total_inr,
    )

    # ----------------------------------------------------------
    # 3. UnmatchedQuoteLines — quote lines without any candidate
    # ----------------------------------------------------------
    unmatched_lines = _build_unmatched_quote_lines(
        quote_lines=quote_lines,
        unmatched_line_ids=gamma_output.unmatched_line_ids,
    )

    # ----------------------------------------------------------
    # 4. ItemizationIndicators (R13)
    # ----------------------------------------------------------
    itemization = _build_itemization_indicators(
        matched_lines=matched_lines,
        gap_indicators=gap_indicators,
        lump_sum_indicators=lump_sum_indicators,
        boq_items=boq_items,
        quote_total_inr=alpha_output.quote_total_inr,
        is_bundle_quote=(
            alpha_output.decomposition_ack.detected_decomposition_style
            != "line_itemized"
        ),
    )

    # ----------------------------------------------------------
    # 5. ReportConfidence (R17)
    # ----------------------------------------------------------
    report_conf = _build_report_confidence(
        matched_lines=matched_lines,
        unmatched_lines=unmatched_lines,
        total_quote_lines=len(quote_lines),
        informal_signal_count=alpha_output.informal_signal_count,
        is_bundle_quote=(
            alpha_output.decomposition_ack.detected_decomposition_style
            != "line_itemized"
        ),
        quote_total_inr=alpha_output.quote_total_inr,
        quote_lines=quote_lines,
        gamma_output=gamma_output,
    )

    # ----------------------------------------------------------
    # 6. AdvisoryFlags — collect failures + informal-construction note
    # ----------------------------------------------------------
    advisory_flags = _build_advisory_flags(
        beta_failures=beta_output.failures,
        delta_failures=delta_output.failures,
        informal_signal_count=alpha_output.informal_signal_count,
    )

    # ----------------------------------------------------------
    # 7. upstream_check_provenance — one CheckProvenance per BOQ item used
    # ----------------------------------------------------------
    provenance = tuple(
        CheckProvenance(
            upstream_component=ml.provenance.upstream_component,
            check_id=ml.provenance.check_id,
            upstream_version=ml.provenance.upstream_version,
            attested_field_name=ml.provenance.attested_field_name,
        )
        for ml in matched_lines
    )

    return PhaseZetaOutput(
        missing_from_quote=gap_indicators,
        lump_sum_indicators=lump_sum_indicators,
        unmatched_quote_lines=unmatched_lines,
        itemization_indicators=itemization,
        report_confidence=report_conf,
        advisory_flags=advisory_flags,
        upstream_check_provenance=provenance,
    )


# ============================================================
# § A — GAP INDICATORS (R16)
# ============================================================

def _build_gap_indicators(
    boq_items: Tuple[ProjectBOQItem, ...],
    matched_boq_ids: set[str],
) -> Tuple[GapIndicator, ...]:
    """Each BOQ item not matched becomes a GapIndicator. R16:
    interpretation defaults to 'likely_oversight' — most generous."""
    indicators: List[GapIndicator] = []
    for it in boq_items:
        if it.boq_id in matched_boq_ids:
            continue
        low = float(it.rate_min.value) * float(it.quantity.value)
        high = float(it.rate_max.value) * float(it.quantity.value)
        advisory = (
            f"{it.label} is typically included for this type of project. "
            "The quote doesn't appear to list it — worth confirming with "
            "the contractor whether it's included in another line, will "
            "be charged separately, or is owner-supplied."
        )
        lint_advisory_text(advisory, field_name="GapIndicator.advisory_note")
        indicators.append(GapIndicator(
            boq_id=it.boq_id,
            boq_label=it.label,
            expected_quantity=it.quantity,
            expected_unit=it.unit,
            expected_total_low_high=(low, high),
            interpretation="likely_oversight",   # R16 default
            severity=it.severity_if_missing,
            advisory_note=advisory,
        ))
    # Canonical sort
    indicators.sort(key=lambda g: g.boq_id)
    return tuple(indicators)


# ============================================================
# § B — LUMP SUM INDICATORS
# ============================================================

def _build_lump_sum_indicators(
    *,
    quote_lines: Tuple[QuoteLineCanonical, ...],
    lump_sum_line_ids: Tuple[str, ...],
    quote_total_inr: float,
) -> Tuple[LumpSumIndicator, ...]:
    quote_by_id = {ql.line_id: ql for ql in quote_lines}
    indicators: List[LumpSumIndicator] = []
    for lid in lump_sum_line_ids:
        ql = quote_by_id[lid]
        pct_val = (
            (ql.total / quote_total_inr) * 100.0
            if quote_total_inr > 0
            else 0.0
        )
        quote_total_av = AttestedValue(
            value=float(ql.total),
            authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
            upstream_source=f"upstream_parser.line[{ql.line_id}].total",
        )
        pct_av = AttestedValue(
            value=pct_val,
            authority=AuthorityKind.LOCALLY_DERIVED,
            derivation_note=f"(line_total {ql.total} / quote_total {quote_total_inr}) × 100",
        )
        advisory = (
            f"Could you walk me through how you've priced "
            f"{ql.raw_label}? I'd like to understand what's included."
        )
        lint_advisory_text(advisory, field_name="LumpSumIndicator.advisory_note")
        indicators.append(LumpSumIndicator(
            line_id=ql.line_id,
            quote_label=ql.raw_label,
            quote_total=quote_total_av,
            pct_of_quote_total=pct_av,
            advisory_note=advisory,
        ))
    indicators.sort(key=lambda l: l.line_id)
    return tuple(indicators)


# ============================================================
# § C — UNMATCHED QUOTE LINES
# ============================================================

def _build_unmatched_quote_lines(
    *,
    quote_lines: Tuple[QuoteLineCanonical, ...],
    unmatched_line_ids: Tuple[str, ...],
) -> Tuple[UnmatchedQuoteLine, ...]:
    quote_by_id = {ql.line_id: ql for ql in quote_lines}
    out: List[UnmatchedQuoteLine] = []
    for lid in unmatched_line_ids:
        ql = quote_by_id[lid]
        qty_av = (
            AttestedValue(
                value=float(ql.quantity),
                authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
                upstream_source=f"upstream_parser.line[{ql.line_id}].quantity",
            )
            if ql.quantity is not None
            else None
        )
        rate_av = (
            AttestedValue(
                value=float(ql.rate),
                authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
                upstream_source=f"upstream_parser.line[{ql.line_id}].rate",
            )
            if ql.rate is not None
            else None
        )
        total_av = AttestedValue(
            value=float(ql.total),
            authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
            upstream_source=f"upstream_parser.line[{ql.line_id}].total",
        )
        advisory = (
            f"The line {ql.raw_label!r} doesn't appear to match an item "
            "in our reference BOQ. This may be a legitimate scope extra, "
            "or our reference may simply not cover it. It's worth asking "
            "the contractor what's included in this line."
        )
        lint_advisory_text(advisory, field_name="UnmatchedQuoteLine.advisory_note")
        out.append(UnmatchedQuoteLine(
            line_id=ql.line_id,
            quote_label=ql.raw_label,
            quote_quantity=qty_av,
            quote_unit=ql.unit_normalised,
            quote_rate=rate_av,
            quote_total=total_av,
            advisory_note=advisory,
        ))
    out.sort(key=lambda u: u.line_id)
    return tuple(out)


# ============================================================
# § D — ITEMIZATION INDICATORS (R13)
# ============================================================

def _build_itemization_indicators(
    *,
    matched_lines:        Tuple[MatchedLine, ...],
    gap_indicators:       Tuple[GapIndicator, ...],
    lump_sum_indicators:  Tuple[LumpSumIndicator, ...],
    boq_items:            Tuple[ProjectBOQItem, ...],
    quote_total_inr:      float,
    is_bundle_quote:      bool,
) -> ItemizationIndicators:
    """Per spec § 2.9 + R13 mandatory clause."""
    total_boq = len(boq_items)
    matched_count = len(matched_lines)
    completeness_pct = (
        (matched_count / total_boq) * 100.0 if total_boq else 0.0
    )

    completeness_av = AttestedValue(
        value=completeness_pct,
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note=(
            f"({matched_count} matched / {total_boq} total BOQ items) × 100"
        ),
    )

    lump_sum_count = len(lump_sum_indicators)
    lump_sum_total_value = sum(float(l.quote_total.value) for l in lump_sum_indicators)
    lump_sum_pct_val = (
        (lump_sum_total_value / quote_total_inr) * 100.0
        if quote_total_inr > 0
        else 0.0
    )
    lump_sum_pct_av = AttestedValue(
        value=lump_sum_pct_val,
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note=(
            f"(lump_sum_total_value {lump_sum_total_value} / "
            f"quote_total_inr {quote_total_inr}) × 100"
        ),
    )

    # Critical items present / gap
    critical_boq_ids = {it.boq_id for it in boq_items if it.severity_if_missing == "critical"}
    matched_boq_ids = {ml.matched_boq_id for ml in matched_lines}
    critical_present = sorted(
        next(it.label for it in boq_items if it.boq_id == bid)
        for bid in critical_boq_ids & matched_boq_ids
    )
    critical_gap = sorted(
        next(it.label for it in boq_items if it.boq_id == bid)
        for bid in critical_boq_ids - matched_boq_ids
    )

    # Margin transparency
    if is_bundle_quote:
        margin_transparency = "decomposition_does_not_apply"
    elif lump_sum_count == 0 and completeness_pct >= 75.0:
        margin_transparency = "embedded_in_rates"
    elif lump_sum_count >= total_boq * 0.5:
        margin_transparency = "not_detectable"
    else:
        margin_transparency = "embedded_in_rates"

    # Rate consistency — variance of rate_delta_pct across matched lines
    if matched_count >= 4:
        deltas = [
            float(m.rate_delta_pct.value)
            for m in matched_lines
            if m.signal is not None and m.signal != PriceSignal.INSUFFICIENT_DATA
        ]
        if len(deltas) >= 4:
            avg = sum(deltas) / len(deltas)
            var = sum((d - avg) ** 2 for d in deltas) / len(deltas)
            stdev = var ** 0.5
            if stdev < 10.0:
                rate_consistency = "consistent"
            elif stdev < 25.0:
                rate_consistency = "mixed"
            else:
                rate_consistency = "highly_variable"
        else:
            rate_consistency = "insufficient_matches"
    else:
        rate_consistency = "insufficient_matches"

    # R13 mandatory clause — MUST appear verbatim (substring) in advisory_note
    r13_clause = (
        "These indicators reflect how the quote was written, not the "
        "quality of work the contractor will deliver."
    )
    advisory = (
        f"This quote covers {completeness_pct:.0f}% of our reference "
        f"BOQ items with explicit line matches, includes {lump_sum_count} "
        f"lump-sum line(s) (~{lump_sum_pct_val:.0f}% of the quote total), "
        f"and shows {rate_consistency.replace('_', ' ')} rate alignment "
        "across matched items. "
        + r13_clause +
        " A well-itemized quote and a strong contractor are different "
        "things; both are worth considering separately."
    )
    lint_advisory_text(advisory, field_name="ItemizationIndicators.advisory_note")

    return ItemizationIndicators(
        itemization_completeness_pct=completeness_av,
        lump_sum_count=lump_sum_count,
        lump_sum_pct_of_total=lump_sum_pct_av,
        critical_items_present=tuple(critical_present),
        critical_items_gap=tuple(critical_gap),
        margin_transparency=margin_transparency,  # type: ignore[arg-type]
        rate_consistency=rate_consistency,         # type: ignore[arg-type]
        advisory_note=advisory,
    )


# ============================================================
# § E — REPORT CONFIDENCE (R17)
# ============================================================

def _build_report_confidence(
    *,
    matched_lines:         Tuple[MatchedLine, ...],
    unmatched_lines:       Tuple[UnmatchedQuoteLine, ...],
    total_quote_lines:     int,
    informal_signal_count: int,
    is_bundle_quote:       bool,
    quote_total_inr:       float,
    quote_lines:           Tuple[QuoteLineCanonical, ...],
    gamma_output:          PhaseGammaOutput,
) -> ReportConfidence:
    high_count = sum(1 for m in matched_lines if m.match_confidence_tier == "high")
    medium_count = sum(1 for m in matched_lines if m.match_confidence_tier == "medium")
    low_count = sum(1 for m in matched_lines if m.match_confidence_tier == "low")
    human_review_count = sum(
        1 for m in matched_lines
        if m.match_confidence_tier == "human_verification_recommended"
    )
    unmatched_count = len(unmatched_lines)

    # Pct calculations
    if total_quote_lines > 0:
        high_med_pct = (high_count + medium_count) / total_quote_lines * 100.0
        human_review_pct = human_review_count / total_quote_lines * 100.0
    else:
        high_med_pct = 0.0
        human_review_pct = 0.0

    # Bundle-value dominance
    bundle_value = sum(
        ql.total for ql in quote_lines
        if ql.line_id in gamma_output.lump_sum_line_ids
    )
    bundle_value_pct = (
        (bundle_value / quote_total_inr) * 100.0
        if quote_total_inr > 0
        else 0.0
    )

    # Tier decision (R17 priority order)
    overall: str
    if informal_signal_count >= 2:
        overall = "human_review_recommended"
    elif human_review_pct >= REPORT_TIER_HUMAN_REVIEW_PCT:
        overall = "human_review_recommended"
    elif is_bundle_quote and bundle_value_pct >= BUNDLE_PCT_DOMINANCE_THRESHOLD:
        # § 26.2 — cap at moderate_signal
        overall = "moderate_signal" if high_med_pct >= REPORT_TIER_MODERATE_SIGNAL_PCT else "high_ambiguity"
    elif high_med_pct >= REPORT_TIER_HIGH_SIGNAL_PCT:
        overall = "high_signal"
    elif high_med_pct >= REPORT_TIER_MODERATE_SIGNAL_PCT:
        overall = "moderate_signal"
    else:
        overall = "high_ambiguity"

    # advisory_note depends on the tier
    if overall == "high_signal":
        advisory = (
            "Most of the quote's lines aligned cleanly with our "
            "reference BOQ — the comparison signals below are well "
            "grounded."
        )
    elif overall == "moderate_signal":
        advisory = (
            "Around half of the quote's lines aligned cleanly with "
            "our reference BOQ. The comparison signals below are "
            "directional rather than precise; consider the patterns "
            "rather than individual figures."
        )
    elif overall == "high_ambiguity":
        advisory = (
            "Fewer than half of the quote's lines aligned cleanly "
            "with our reference BOQ. The comparison signals below "
            "should be treated as starting points for conversation, "
            "not conclusions."
        )
    else:  # human_review_recommended
        if informal_signal_count >= 2:
            advisory = (
                "This quote shows signals consistent with an informal "
                "or family-network construction arrangement (few line "
                "items, predominantly lump-sum pricing, limited brand "
                "specification). Our automated comparison is calibrated "
                "for formalised urban residential quotes and may not "
                "apply cleanly here. We'd suggest reviewing the "
                "comparison with someone you trust before drawing "
                "conclusions."
            )
        else:
            advisory = (
                "This quote has many handwritten or informally itemised "
                "lines. Our automatic comparison may not capture "
                "everything accurately. We'd suggest reviewing the "
                "comparison with someone you trust before drawing "
                "conclusions."
            )
    lint_advisory_text(advisory, field_name="ReportConfidence.advisory_note")

    return ReportConfidence(
        total_quote_lines=total_quote_lines,
        high_confidence_matches=high_count,
        medium_confidence_matches=medium_count,
        low_confidence_matches=low_count,
        human_verification_recommended=human_review_count,
        unmatched_quote_lines=unmatched_count,
        overall_report_tier=overall,  # type: ignore[arg-type]
        advisory_note=advisory,
    )


# ============================================================
# § F — ADVISORY FLAGS
# ============================================================

def _build_advisory_flags(
    *,
    beta_failures:         tuple,
    delta_failures:        tuple,
    informal_signal_count: int,
) -> Tuple[AdvisoryFlag, ...]:
    flags: List[AdvisoryFlag] = []

    if informal_signal_count >= 2:
        flags.append(AdvisoryFlag(
            source_component=f"c17_quote_comparison_engine.{C17_VERSION}",
            flag_id="informal_construction_arrangement_detected",
            message=(
                "Quote shows {n} informal-arrangement signals (spec § 1.4); "
                "report tier set to human_review_recommended."
            ).format(n=informal_signal_count),
        ))

    for fr in beta_failures:
        flags.append(AdvisoryFlag(
            source_component=f"c17_quote_comparison_engine.{C17_VERSION}",
            flag_id="beta_failure",
            message=f"Phase β WARN-mode failure on line[{fr.line_id}]: {fr.error_class}",
        ))
    for fr in delta_failures:
        flags.append(AdvisoryFlag(
            source_component=f"c17_quote_comparison_engine.{C17_VERSION}",
            flag_id="delta_failure",
            message=f"Phase δ WARN-mode failure on line[{fr.line_id}]: {fr.error_class}",
        ))
    return tuple(flags)
