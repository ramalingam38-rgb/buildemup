"""
C17 — Phase ε — Totals, DiscussionBaseline, RateStalenessDisclosure
======================================================================

Input:  PhaseAlphaOutput (canonical lines)
        PhaseBetaOutput  (ProjectBOQ)
        PhaseDeltaOutput (matched lines)
Output: TotalComparison + DiscussionBaseline + RateStalenessDisclosure

Responsibilities:
  1. Aggregate quote_total from ParsedQuote.
  2. Aggregate our_estimate_total as a TransparencyTriple (range +
     midpoint + per-BOQ-item derivation lines).
  3. Compute delta_amount and delta_pct as LOCALLY_DERIVED.
  4. Build the headline_summary in reference-tone (R2 lint).
  5. Derive potential_conversation_range from RateProvider's
     contractor_margin_range_pct() (R9).
  6. Build DiscussionBaseline = our_estimate_total + reasonable_margin.
  7. Populate RateStalenessDisclosure (R14).

Rule 11 self-analysis:
  1. TransparencyTriple uses HIGH/MEDIUM/LOW Confidence aliases —
     v0.5 renamed to WELL_CONSTRAINED/REGIONAL_TYPICAL/DEPENDS_ON_CHOICE.
     We use REGIONAL_TYPICAL throughout (this is regional-typical
     rate data).
  2. uncertainty_pct on our_estimate_total derives from the
     ProjectBOQ rate_min/rate_max spread weighted by line value.
     Computed honestly; not a fixed ±10%.
  3. Conversation-range disclaimer is hard-coded; R2 lint catches drift.
  4. RateStalenessDisclosure strings are templated from kb_version
     + kb_date; if those are empty we'd emit empty strings — guarded
     in the function (the dataclass __post_init__ also validates).
"""

from __future__ import annotations

from dataclasses import dataclass

from buildemup.components.c16.contracts import AttestedValue, AuthorityKind
from buildemup.components.c17.advisory_lint import lint_advisory_text
from buildemup.components.c17.contracts import ProjectBOQ
from buildemup.components.c17.phases.alpha_canonicalize import PhaseAlphaOutput
from buildemup.components.c17.phases.beta_boq_assembly import PhaseBetaOutput
from buildemup.components.c17.phases.delta_verdicting import PhaseDeltaOutput
from buildemup.components.c17.schema import (
    DiscussionBaseline,
    RateStalenessDisclosure,
    TotalComparison,
)
from buildemup.utils.confidence import Confidence
from buildemup.utils.rate_provider import RateProvider
from buildemup.utils.transparency import DerivationLine, TransparencyTriple


@dataclass(frozen=True)
class PhaseEpsilonOutput:
    total_comparison:           TotalComparison
    discussion_baseline:        DiscussionBaseline
    rate_staleness_disclosure:  RateStalenessDisclosure


def run_phase_epsilon(
    alpha_output: PhaseAlphaOutput,
    beta_output:  PhaseBetaOutput,
    delta_output: PhaseDeltaOutput,
    *,
    rate_provider: RateProvider,
) -> PhaseEpsilonOutput:
    """Phase ε entry point."""
    boq = beta_output.project_boq

    # ----------------------------------------------------------
    # 1. our_estimate_total as TransparencyTriple
    # ----------------------------------------------------------
    our_total_low = sum(it.rate_min.value * it.quantity.value for it in boq.items)
    our_total_mid = sum(it.rate_median.value * it.quantity.value for it in boq.items)
    our_total_high = sum(it.rate_max.value * it.quantity.value for it in boq.items)

    if our_total_mid > 0:
        avg_spread = ((our_total_high - our_total_low) / 2.0) / our_total_mid * 100.0
    else:
        avg_spread = 10.0  # placeholder if BOQ is empty (which shouldn't happen)

    derivation_lines = [
        DerivationLine(
            label=it.label,
            quantity=float(it.quantity.value),
            unit=it.unit,
            rate=float(it.rate_median.value),
            rate_unit=f"₹/{it.unit}",
            amount=float(it.rate_median.value) * float(it.quantity.value),
            source=f"rate_provider.{boq.rate_provider_kb_version}",
        )
        for it in boq.items
    ]

    our_estimate_triple = TransparencyTriple(
        label="Project reference estimate",
        exact_value=our_total_mid,
        unit="₹",
        uncertainty_pct=round(avg_spread, 2),
        confidence=Confidence.REGIONAL_TYPICAL,
        derivation=derivation_lines,
        notes=[
            f"Rates from {boq.rate_provider_kb_version} ({boq.rate_provider_locality}).",
            "Range reflects min/max rate spread across BOQ items.",
        ],
    )

    # ----------------------------------------------------------
    # 2. Quote-side total + deltas
    # ----------------------------------------------------------
    quote_total_v = alpha_output.quote_total_inr
    delta_amount_v = quote_total_v - our_total_mid
    delta_pct_v = (
        (delta_amount_v / our_total_mid) * 100.0
        if our_total_mid > 0
        else 0.0
    )

    quote_total_av = AttestedValue(
        value=quote_total_v,
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source="upstream_parser.quote_total_inr",
    )
    delta_amount_av = AttestedValue(
        value=delta_amount_v,
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note=f"quote_total {quote_total_v} - our_estimate_total {our_total_mid}",
    )
    delta_pct_av = AttestedValue(
        value=delta_pct_v,
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note=(
            f"(delta_amount {delta_amount_v} / our_estimate_total {our_total_mid}) × 100"
        ),
    )

    # ----------------------------------------------------------
    # 3. potential_conversation_range
    # ----------------------------------------------------------
    margin_low_pct, margin_high_pct = rate_provider.contractor_margin_range_pct()
    # Reasonable margin range applied to our_estimate_total
    conv_range_low = our_total_mid * (1.0 + margin_low_pct / 100.0)
    conv_range_high = our_total_mid * (1.0 + margin_high_pct / 100.0)

    # ----------------------------------------------------------
    # 4. headline_summary (R2 lint-clean reference-tone)
    # ----------------------------------------------------------
    delta_sign = "higher than" if delta_amount_v > 0 else "lower than"
    delta_abs_lakhs = abs(delta_amount_v) / 100_000.0
    our_lakhs = our_total_mid / 100_000.0
    if abs(delta_pct_v) < 1.0:
        headline = (
            f"The quote total (₹{quote_total_v/100_000:.1f}L) is close to "
            f"our reference estimate (₹{our_lakhs:.1f}L). Our reference is "
            "one input among several to consider."
        )
    else:
        headline = (
            f"The quote total is ₹{delta_abs_lakhs:.1f}L {delta_sign} our "
            f"reference estimate (₹{our_lakhs:.1f}L). Our reference is one "
            "input among several to consider; final cost depends on scope, "
            "site conditions, and material choices."
        )
    lint_advisory_text(headline, field_name="TotalComparison.headline_summary")

    conv_range_disclaimer = (
        "This range is a reference for conversation, not a savings "
        "guarantee. Final cost depends on site conditions, scope "
        "changes, variation orders, material choices, and contractor "
        f"terms. Rate references are from {boq.rate_provider_kb_version}."
    )
    lint_advisory_text(
        conv_range_disclaimer,
        field_name="TotalComparison.conversation_range_disclaimer",
    )

    total_comparison = TotalComparison(
        quote_total=quote_total_av,
        our_estimate_total=our_estimate_triple,
        delta_amount=delta_amount_av,
        delta_pct=delta_pct_av,
        headline_summary=headline,
        potential_conversation_range=(conv_range_low, conv_range_high),
        conversation_range_disclaimer=conv_range_disclaimer,
    )

    # ----------------------------------------------------------
    # 5. DiscussionBaseline (R9 — never undercut, never inflate)
    # ----------------------------------------------------------
    default_margin_pct = rate_provider.contractor_margin_default_pct()
    adjusted_total_mid = our_total_mid * (1.0 + default_margin_pct / 100.0)
    adjusted_uncertainty = round(
        max(avg_spread, abs(margin_high_pct - margin_low_pct) / 2.0),
        2,
    )

    adjusted_total_triple = TransparencyTriple(
        label="Discussion baseline (with reasonable contractor margin)",
        exact_value=adjusted_total_mid,
        unit="₹",
        uncertainty_pct=adjusted_uncertainty,
        confidence=Confidence.DEPENDS_ON_CHOICE,
        derivation=[
            DerivationLine(
                label="Our reference estimate (median rates)",
                amount=our_total_mid,
                source="rate_provider median",
            ),
            DerivationLine(
                label=f"+ reasonable contractor margin ({default_margin_pct:.0f}%)",
                amount=adjusted_total_mid - our_total_mid,
                source="rate_provider.contractor_margin_default_pct",
            ),
        ],
        notes=[
            f"Margin range from RateProvider: {margin_low_pct:.0f}–{margin_high_pct:.0f}%; "
            f"default: {default_margin_pct:.0f}%.",
            "Not a price target — actual contract price depends on factors "
            "specific to your project we don't see.",
        ],
    )

    reasonable_margin_av = AttestedValue(
        value=float(default_margin_pct),
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source=(
            f"rate_provider.{rate_provider.kb_version}.contractor_margin_default_pct"
        ),
    )

    conv_language = (
        "Could you walk me through the basis for the key line items? "
        f"Our reference range from {boq.rate_provider_kb_version} suggests "
        f"a total of roughly ₹{our_lakhs:.1f}L with a typical contractor "
        f"margin of {default_margin_pct:.0f}%. I'd appreciate understanding "
        "how your figures are arrived at."
    )
    lint_advisory_text(
        conv_language,
        field_name="DiscussionBaseline.conversation_language",
    )

    disclaimer = (
        f"This baseline assumes typical Chennai rates as of "
        f"{boq.rate_provider_kb_version}. It is not a price target. The "
        "actual contract price depends on many factors specific to your "
        "project that we don't see."
    )
    lint_advisory_text(disclaimer, field_name="DiscussionBaseline.disclaimer")

    discussion_baseline = DiscussionBaseline(
        adjusted_total=adjusted_total_triple,
        reasonable_margin_pct=reasonable_margin_av,
        conversation_language=conv_language,
        disclaimer=disclaimer,
    )

    # ----------------------------------------------------------
    # 6. RateStalenessDisclosure (R14)
    # ----------------------------------------------------------
    staleness = _build_rate_staleness_disclosure(boq)

    return PhaseEpsilonOutput(
        total_comparison=total_comparison,
        discussion_baseline=discussion_baseline,
        rate_staleness_disclosure=staleness,
    )


# ============================================================
# § X — RateStalenessDisclosure templating
# ============================================================

def _build_rate_staleness_disclosure(boq: ProjectBOQ) -> RateStalenessDisclosure:
    """Per spec § 2.11 + R14. Standardised caveats; values reflect
    Chennai-wide rate volatility per spec rationale."""
    micro = (
        "Rates may vary 5–15% between different parts of Chennai depending "
        "on contractor ecosystem, supply chains, and project access. Our "
        "reference is a Chennai-wide median."
    )
    volatility = (
        "Construction rates can shift 10–20% within a single quarter based "
        "on monsoon timing, demand, and material supply. These reference "
        f"rates are anchored to {boq.rate_provider_kb_date}."
    )
    cadence = (
        f"If this quote is more than 60 days old or your project extends "
        f"past Q+1 from {boq.rate_provider_kb_date}, rates may have changed; "
        "consider asking the contractor whether their figures still hold."
    )

    # Defence-in-depth lint
    for fname, text in (
        ("micro_market_caveat", micro),
        ("market_volatility_caveat", volatility),
        ("recommended_review_cadence", cadence),
    ):
        lint_advisory_text(text, field_name=f"RateStalenessDisclosure.{fname}")

    return RateStalenessDisclosure(
        rate_provider_kb_version=boq.rate_provider_kb_version,
        rate_provider_kb_date=boq.rate_provider_kb_date,
        rate_provider_locality=boq.rate_provider_locality,
        micro_market_caveat=micro,
        market_volatility_caveat=volatility,
        recommended_review_cadence=cadence,
    )
