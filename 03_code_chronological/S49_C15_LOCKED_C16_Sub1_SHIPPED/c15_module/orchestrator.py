"""
BuildemUp — Component 15 — Orchestrator
==========================================

Per C15 SPEC v0.2 LOCKED § 3 (Phases) + § 5.1 (strict/WARN dispatch).

Public API:
  analyze_problems(c12_candidate, c13_placement, c14_report, metadata, config)
    → SuccessfulProblemAnalysis | FailedProblemAnalysis

  analyze_problems_batch(triples, metadata_per_candidate, config)
    → ProblemAnalysisBatchResult

Phases:
  π (pi)     — Ingress + metadata resolution. Probe dependencies → CheckContext.
  ρ (rho)    — Check registry traversal (lex-ASC by check_id).
  σ (sigma)  — Severity assignment via severity_rule_table lookup.
  τ (tau)    — DimensionSummary aggregation per dimension 1..10.
  υ (upsilon)— Upstream advisory + structural + preference flag passthrough
               (Inv P10 byte-identical).
  φ (phi)    — Report assembly with provenance triple (Inv P16).
"""
from __future__ import annotations

import dataclasses
from typing import Sequence

from .config import ProblemFinderConfig
from .contracts import ProblemAnalysisMetadata
from .errors import (
    InconsistentInputError,
    LocalProblemError,
    PerCandidateProblemError,
)
from .protocol import CheckContext, probe_dependencies
from .registry import CheckRegistry, build_registry
from .pattern_detector import detect_unconventional_patterns
from .schema import (
    CheckStatus,
    DeferredCheck,
    DimensionSummary,
    FailedProblemAnalysis,
    FailureRecord,
    ProblemAnalysisBatchResult,
    ProblemCheck,
    ProblemReport,
    SuccessfulProblemAnalysis,
    UnconventionalPatternHint,
    _derive_coverage_quality,
    _derive_dim_maturity,
)
from .severity_rule_table import SEVERITY_RULE_TABLE_V1, lookup_severity
from .versioning import (
    C15_CHECK_REGISTRY_VERSION,
    C15_VERSION,
    DIMENSIONS_NOT_EVALUATED_V1,
    EXPECTED_ADVISORY_SCHEMA_VERSION,
)


def _empty_pattern_hint() -> UnconventionalPatternHint:
    return UnconventionalPatternHint(
        detected=False,
        suspected_patterns=(),
        confidence_caveat="",
        affected_check_ids=(),
    )


# =============================================================================
# Public single-candidate entrypoint
# =============================================================================

def analyze_problems(
    *,
    c12_candidate: object,
    c13_placement: object,
    c14_report: object,
    metadata: ProblemAnalysisMetadata,
    config: ProblemFinderConfig | None = None,
    registry: CheckRegistry | None = None,
) -> SuccessfulProblemAnalysis | FailedProblemAnalysis:
    """Analyze problems for ONE candidate (c12, c13, c14, metadata).

    Returns SuccessfulProblemAnalysis OR FailedProblemAnalysis based
    on strict/WARN dispatch. LocalProblemError always halts.
    """
    cfg = config or ProblemFinderConfig()
    reg = registry if registry is not None else build_registry()
    candidate_sig = _resolve_candidate_signature(c12_candidate)

    try:
        report = _run_phases(
            c12_candidate=c12_candidate,
            c13_placement=c13_placement,
            c14_report=c14_report,
            metadata=metadata,
            registry=reg,
            candidate_signature=candidate_sig,
        )
    except LocalProblemError:
        raise
    except PerCandidateProblemError as e:
        if cfg.strict_mode:
            raise
        return FailedProblemAnalysis(
            source_placed_candidate_signature=candidate_sig,
            failure_record=FailureRecord(
                candidate_signature=candidate_sig,
                error_type=type(e).__name__,
                error_message=str(e),
                phase=_phase_for_error(e),
            ),
            partial_report=None,
        )

    return SuccessfulProblemAnalysis(
        source_placed_candidate_signature=candidate_sig,
        report=report,
    )


# =============================================================================
# Phase π — Ingress + metadata resolution
# =============================================================================

def _resolve_candidate_signature(c12_candidate: object) -> str:
    sig = (
        getattr(c12_candidate, "source_refined_candidate_signature", None)
        or getattr(c12_candidate, "source_placed_candidate_signature", None)
        or getattr(c12_candidate, "candidate_signature", None)
    )
    if sig is None:
        sig = f"unknown-c12-candidate-{id(c12_candidate)}"
    return str(sig)


def _ingress_check_context(
    c12_candidate: object,
    c14_report: object,
    metadata: ProblemAnalysisMetadata,
) -> CheckContext:
    available = probe_dependencies(c12_candidate, c14_report, metadata)
    return CheckContext(
        placed_candidate=c12_candidate,
        circulation_report=c14_report,
        metadata=metadata,
        available_dependencies=available,
    )


# =============================================================================
# Phase ρ — Registry traversal
# =============================================================================

def _phase_rho_traverse(
    registry: CheckRegistry, context: CheckContext,
) -> tuple[list[ProblemCheck], list[DeferredCheck]]:
    applicable: list[ProblemCheck] = []
    deferred: list[DeferredCheck] = []
    for check in registry:
        result = check.evaluate(context)
        if isinstance(result, ProblemCheck):
            applicable.append(result)
        elif isinstance(result, DeferredCheck):
            deferred.append(result)
        else:
            raise LocalProblemError(
                f"Check {check.check_id!r}.evaluate() returned {type(result).__name__}; "
                f"must return ProblemCheck or DeferredCheck."
            )
    return applicable, deferred


# =============================================================================
# Phase σ — Severity assignment (overwrite Check placeholder)
# =============================================================================

def _phase_sigma_assign_severity(
    applicable: list[ProblemCheck],
    metadata: ProblemAnalysisMetadata,
) -> list[ProblemCheck]:
    finalized: list[ProblemCheck] = []
    for pc in applicable:
        canonical = lookup_severity(
            SEVERITY_RULE_TABLE_V1,
            check_id=pc.check_id,
            status=pc.status,
            cultural_profile=metadata.cultural_profile,
        )
        if canonical == pc.severity:
            finalized.append(pc)
        else:
            finalized.append(dataclasses.replace(pc, severity=canonical))
    return finalized


# =============================================================================
# Phase τ — DimensionSummary aggregation
# =============================================================================

_DIMENSION_NAMES: tuple[str, ...] = (
    "No wasted space",                    # 1
    "Room sizes match function",          # 2
    "Logical flow",                       # 3
    "Natural light",                      # 4
    "Privacy",                            # 5
    "No bottlenecks",                     # 6
    "First-floor living",                 # 7
    "Outdoor connection",                 # 8
    "Storage",                            # 9
    "Multi-functional",                   # 10
)


def _phase_tau_dim_summaries(
    applicable: list[ProblemCheck],
    deferred: list[DeferredCheck],
) -> tuple[DimensionSummary, ...]:
    summaries: list[DimensionSummary] = []
    for dim in range(1, 11):
        n_pass = sum(1 for p in applicable if p.dimension_id == dim and p.status == CheckStatus.PASS)
        n_warn = sum(1 for p in applicable if p.dimension_id == dim and p.status == CheckStatus.WARN)
        n_fail = sum(1 for p in applicable if p.dimension_id == dim and p.status == CheckStatus.FAIL)
        n_app = n_pass + n_warn + n_fail
        n_def = sum(1 for d in deferred if d.dimension_id == dim)
        summaries.append(DimensionSummary(
            dimension_id=dim,
            dimension_name=_DIMENSION_NAMES[dim - 1],
            n_applicable=n_app,
            n_deferred=n_def,
            n_pass=n_pass, n_warn=n_warn, n_fail=n_fail,
            maturity=_derive_dim_maturity(n_app, n_def),
        ))
    return tuple(summaries)


# =============================================================================
# Phase υ — Upstream passthrough
# =============================================================================

def _phase_upsilon_passthrough(
    c13_placement: object, c14_report: object,
) -> tuple[tuple, tuple, tuple]:
    c13_advisory = tuple(getattr(c13_placement, "advisory_flags", ()) or ())
    c14_structural = tuple(getattr(c14_report, "structural_flags", ()) or ())
    c14_preference = tuple(getattr(c14_report, "preference_flags", ()) or ())
    return c13_advisory, c14_structural, c14_preference


# =============================================================================
# Phase φ — Report assembly
# =============================================================================

def _phase_phi_assemble_report(
    *,
    candidate_signature: str,
    applicable: list[ProblemCheck],
    deferred: list[DeferredCheck],
    dimension_summaries: tuple[DimensionSummary, ...],
    c13_advisory: tuple,
    c14_structural: tuple,
    c14_preference: tuple,
    metadata: ProblemAnalysisMetadata,
    upstream_cache_key: str,
    c12_candidate: object,
    c14_report: object,
) -> ProblemReport:
    applicable_sorted = tuple(sorted(applicable, key=lambda p: p.check_id))
    deferred_sorted = tuple(sorted(deferred, key=lambda d: d.check_id))
    # v0.3 A12: derive coverage signal from dimension_summaries.
    # NOT a quality score; a coverage-of-evaluation signal.
    coverage_quality, ratio_applicable = _derive_coverage_quality(
        dimension_summaries
    )
    # v1 LOCK B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK:
    # run 5 v1 pattern detectors. 2 implemented + 3 data-blocked
    # stubs (split_level_circulation, ritual_procession,
    # multigenerational_segregation).
    pattern_hint = detect_unconventional_patterns(c12_candidate, c14_report)
    return ProblemReport(
        source_placed_candidate_signature=candidate_signature,
        applicable_checks=applicable_sorted,
        deferred_checks=deferred_sorted,
        dimension_summary=dimension_summaries,
        dimensions_not_evaluated=DIMENSIONS_NOT_EVALUATED_V1,
        unconventional_pattern_hint=pattern_hint,
        cultural_profile_active=metadata.cultural_profile,
        c13_advisory_flags=c13_advisory,
        c14_structural_flags=c14_structural,
        c14_preference_flags=c14_preference,
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        upstream_cache_key=upstream_cache_key,
        coverage_quality=coverage_quality,
        ratio_applicable=ratio_applicable,
    )


# =============================================================================
# Orchestration glue
# =============================================================================

def _run_phases(
    *,
    c12_candidate: object, c13_placement: object, c14_report: object,
    metadata: ProblemAnalysisMetadata,
    registry: CheckRegistry,
    candidate_signature: str,
) -> ProblemReport:
    context = _ingress_check_context(c12_candidate, c14_report, metadata)

    # π consistency: placed_rooms ids must match metadata.placed_room_ids.
    pr_attr = getattr(c12_candidate, "placed_rooms", None)
    if pr_attr is not None:
        pr_ids = tuple(sorted(getattr(r, "room_id", "") for r in pr_attr))
        if pr_ids != tuple(metadata.placed_room_ids):
            raise InconsistentInputError(
                f"C12 placed_rooms ids {pr_ids} disagree with metadata.placed_room_ids "
                f"{tuple(metadata.placed_room_ids)}."
            )

    applicable, deferred = _phase_rho_traverse(registry, context)
    applicable = _phase_sigma_assign_severity(applicable, metadata)
    dim_summaries = _phase_tau_dim_summaries(applicable, deferred)
    c13_adv, c14_struct, c14_pref = _phase_upsilon_passthrough(c13_placement, c14_report)
    upstream_key = _extract_upstream_cache_key(c14_report)
    return _phase_phi_assemble_report(
        candidate_signature=candidate_signature,
        applicable=applicable, deferred=deferred,
        dimension_summaries=dim_summaries,
        c13_advisory=c13_adv,
        c14_structural=c14_struct, c14_preference=c14_pref,
        metadata=metadata, upstream_cache_key=upstream_key,
        c12_candidate=c12_candidate, c14_report=c14_report,
    )


def _extract_upstream_cache_key(c14_report: object) -> str:
    """Per Inv P14: upstream_cache_key == c14_input.cache_keys.full_cache_key.

    If C14 doesn't surface a cache_keys attribute (test contexts /
    synthesized inputs), fall back to a deterministic placeholder
    derived from the report's identity hash so byte-equal replay
    still holds for the same input."""
    ck = getattr(c14_report, "cache_keys", None)
    if ck is not None:
        full = getattr(ck, "full_cache_key", None) or getattr(ck, "full", None) or ""
        if full:
            return str(full)
    # Fallback: stable, non-empty marker — annotated so consumers
    # know the upstream did not produce a real cache key.
    return f"c15-synthesized-upstream-key-no-c14-cache-{id(c14_report):x}"


def _phase_for_error(e: PerCandidateProblemError) -> str:
    name = type(e).__name__
    if name in ("MissingMetadataError", "InconsistentInputError"):
        return "pi"
    return "rho"


# =============================================================================
# Batch entry
# =============================================================================

def analyze_problems_batch(
    *,
    triples: Sequence[tuple[object, object, object]],
    metadata_per_candidate: Sequence[ProblemAnalysisMetadata],
    config: ProblemFinderConfig | None = None,
    registry: CheckRegistry | None = None,
) -> ProblemAnalysisBatchResult:
    if len(triples) != len(metadata_per_candidate):
        raise LocalProblemError(
            f"triples len {len(triples)} disagrees with metadata len {len(metadata_per_candidate)}."
        )
    cfg = config or ProblemFinderConfig()
    reg = registry if registry is not None else build_registry()

    successes: list[SuccessfulProblemAnalysis] = []
    failures: list[FailedProblemAnalysis] = []
    for (c12, c13, c14), md in zip(triples, metadata_per_candidate):
        r = analyze_problems(
            c12_candidate=c12, c13_placement=c13, c14_report=c14,
            metadata=md, config=cfg, registry=reg,
        )
        if isinstance(r, SuccessfulProblemAnalysis):
            successes.append(r)
        else:
            failures.append(r)

    successes_sorted = tuple(sorted(
        successes, key=lambda s: s.source_placed_candidate_signature
    ))
    failures_sorted = tuple(sorted(
        failures, key=lambda f: f.source_placed_candidate_signature
    ))
    return ProblemAnalysisBatchResult(
        successful=successes_sorted, failed=failures_sorted,
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
    )


__all__ = ["analyze_problems", "analyze_problems_batch"]
