"""
C17 — Orchestrator
====================

The single public entry point for C17. Wires phases α → β → γ → δ → ε → ζ
and produces a fully-signed QuoteComparisonReport.

Per spec § 3 phase pipeline + § 4 error handling.

Public API:
    run_c17(
        parsed_quote:          ParsedQuote,
        cost_lines:            Iterable[upstream cost line],
        rate_provider:         RateProvider,
        project_id:            str,
        jurisdiction_profile_id: str,
        declared_domain_scope: str,
        config:                C17RuntimeConfig | None = None,
    ) -> QuoteComparisonReport

Error contract (spec § 4):
    LocalQuoteError subtypes raise unconditionally — caller's
    responsibility. WARN mode does NOT swallow these.
    PerQuoteLineError subtypes raise in STRICT mode; WARN mode
    collects into FailedComparisonRecord-derived AdvisoryFlags.

Rule 11 self-analysis:
  1. Pre-flight validation: jurisdiction + domain_scope are checked
     at the ProjectBOQ boundary (phase β builds it). For caller
     ergonomics we also check up front to fail fast.
  2. signing is the LAST step — every other artifact is computed and
     wired in BEFORE cache_keys runs. R6 requires byte-equal replay
     so the signature must be over the FINAL canonical state.
  3. Determinism: every phase sorts its output canonically. Order
     of operations here is fixed; no per-run variance.
  4. We catch top-level Exception from cache_keys? NO — if the
     signature computation throws, that's a contract bug, not data
     corruption. Re-raise.
"""

from __future__ import annotations

from typing import Iterable, Optional

from buildemup.components.c17.cache_keys import (
    compute_canonical_replay_signature,
    compute_presentation_signature,
    compute_schema_descriptor_digest,
)
from buildemup.components.c17.config import C17RuntimeConfig
from buildemup.components.c17.contracts import ParsedQuote
from buildemup.components.c17.errors import JurisdictionNotSupportedError
from buildemup.components.c17.phases.alpha_canonicalize import run_phase_alpha
from buildemup.components.c17.phases.beta_boq_assembly import run_phase_beta
from buildemup.components.c17.phases.delta_verdicting import run_phase_delta
from buildemup.components.c17.phases.epsilon_totals import run_phase_epsilon
from buildemup.components.c17.phases.gamma_matching import run_phase_gamma
from buildemup.components.c17.phases.zeta_indicators import run_phase_zeta
from buildemup.components.c17.schema import QuoteComparisonReport
from buildemup.components.c17.versioning import (
    C17_REPORT_SCHEMA_VERSION,
    C17_VERSION,
    SUPPORTED_DOMAIN_SCOPES,
    SUPPORTED_JURISDICTIONS,
)
from buildemup.utils.rate_provider import RateProvider


def run_c17(
    *,
    parsed_quote:            ParsedQuote,
    cost_lines:              Iterable,
    rate_provider:           RateProvider,
    project_id:              str,
    jurisdiction_profile_id: str,
    declared_domain_scope:   str,
    locality_label:          str = "Chennai-wide",
    config:                  Optional[C17RuntimeConfig] = None,
) -> QuoteComparisonReport:
    """C17 single entry point. See module docstring for full contract."""
    if config is None:
        config = C17RuntimeConfig()

    # Pre-flight (fail fast — these checks also fire in ProjectBOQ
    # construction; doing them here keeps stack traces clean.)
    if jurisdiction_profile_id not in SUPPORTED_JURISDICTIONS:
        raise JurisdictionNotSupportedError(
            f"jurisdiction_profile_id {jurisdiction_profile_id!r} not "
            f"supported by C17 {C17_VERSION}.",
            requested_jurisdiction=jurisdiction_profile_id,
            supported=SUPPORTED_JURISDICTIONS,
        )
    if declared_domain_scope not in SUPPORTED_DOMAIN_SCOPES:
        raise JurisdictionNotSupportedError(
            f"declared_domain_scope {declared_domain_scope!r} not "
            f"supported by C17 {C17_VERSION}.",
            requested_jurisdiction=declared_domain_scope,
            supported=SUPPORTED_DOMAIN_SCOPES,
        )

    # ----- Phase α: canonicalise + classify decomposition
    alpha_out = run_phase_alpha(parsed_quote, config=config)

    # ----- Phase β: assemble ProjectBOQ
    beta_out = run_phase_beta(
        alpha_out,
        project_id=project_id,
        jurisdiction_profile_id=jurisdiction_profile_id,
        declared_domain_scope=declared_domain_scope,
        cost_lines=cost_lines,
        rate_provider=rate_provider,
        locality_label=locality_label,
        config=config,
    )

    # ----- Phase γ: 4-tier matching
    gamma_out = run_phase_gamma(alpha_out, beta_out)

    # ----- Phase δ: verdicting + R5 + bundle downgrade
    delta_out = run_phase_delta(alpha_out, beta_out, gamma_out, config=config)

    # ----- Phase ε: totals + DiscussionBaseline + RateStalenessDisclosure
    epsilon_out = run_phase_epsilon(
        alpha_out,
        beta_out,
        delta_out,
        rate_provider=rate_provider,
    )

    # ----- Phase ζ: GapIndicators + ItemizationIndicators + ReportConfidence
    zeta_out = run_phase_zeta(
        alpha_out,
        beta_out,
        gamma_out,
        delta_out,
        epsilon_out,
    )

    # ----- Signing (R6 / R7 / R8)
    canonical_sig = compute_canonical_replay_signature(
        source_quote_signature=alpha_out.verified_signature,
        source_boq_signature=beta_out.project_boq.boq_signature,
        strict_mode=config.strict_mode,
        matched_lines=delta_out.matched_lines,
        missing_from_quote=zeta_out.missing_from_quote,
        unmatched_quote_lines=zeta_out.unmatched_quote_lines,
        lump_sum_indicators=zeta_out.lump_sum_indicators,
        decomposition_acknowledgment=alpha_out.decomposition_ack,
        total_comparison=epsilon_out.total_comparison,
        discussion_baseline=epsilon_out.discussion_baseline,
        itemization_indicators=zeta_out.itemization_indicators,
        report_confidence=zeta_out.report_confidence,
        rate_staleness_disclosure=epsilon_out.rate_staleness_disclosure,
        jurisdiction_profile_id=jurisdiction_profile_id,
        declared_domain_scope=declared_domain_scope,
    )
    presentation_sig = compute_presentation_signature(
        canonical_replay_signature=canonical_sig,
    )
    schema_digest = compute_schema_descriptor_digest()

    # ----- Final assembly
    return QuoteComparisonReport(
        source_quote_signature=alpha_out.verified_signature,
        source_boq_signature=beta_out.project_boq.boq_signature,
        c17_version=C17_VERSION,
        c17_schema_version=C17_REPORT_SCHEMA_VERSION,
        jurisdiction_profile_id=jurisdiction_profile_id,
        declared_domain_scope=declared_domain_scope,
        rate_staleness_disclosure=epsilon_out.rate_staleness_disclosure,
        matched_lines=delta_out.matched_lines,
        missing_from_quote=zeta_out.missing_from_quote,
        unmatched_quote_lines=zeta_out.unmatched_quote_lines,
        lump_sum_indicators=zeta_out.lump_sum_indicators,
        decomposition_acknowledgment=alpha_out.decomposition_ack,
        total_comparison=epsilon_out.total_comparison,
        discussion_baseline=epsilon_out.discussion_baseline,
        itemization_indicators=zeta_out.itemization_indicators,
        report_confidence=zeta_out.report_confidence,
        advisory_flags=zeta_out.advisory_flags,
        upstream_check_provenance=zeta_out.upstream_check_provenance,
        canonical_replay_signature=canonical_sig,
        presentation_signature=presentation_sig,
        schema_descriptor_digest=schema_digest,
    )
