"""
C16 — Orchestrator (public API)
==================================

Per v0.5 LOCKED spec § 4.

Public entry points:
    render_drawings(...)       → SuccessfulDrawingRender | FailedDrawingRender
    render_drawings_batch(...) → DrawingRenderBatchResult

Phase sequencing:
    Phase α (envelope)  →  Phase β (scheduling)  →  Phase γ (working)
                       →  Phase δ (permit)       →  Phase ε (attestation)
                       →  Phase ζ (bundle)

Error routing:
    LocalDrawingError       (UpstreamSchemaDriftError,
                             C16ConfigurationError,
                             JurisdictionNotSupportedError,
                             OrientationLockMismatchError)
            → always halts, regardless of strict_mode
    PerLayoutDrawingError   (MissingUpstreamDataError,
                             GeometryInconsistencyError,
                             ComplianceProvenanceError)
            → strict_mode=True  → raise
            → strict_mode=False → collect into FailedDrawingRender
"""
from __future__ import annotations

import time
from typing import Optional

from buildemup.components.c16.config import RenderingConfig
from buildemup.components.c16.contracts import (
    JurisdictionProfile,
    SelectionResult,
)
from buildemup.components.c16.errors import (
    LocalDrawingError,
    PerLayoutDrawingError,
)
from buildemup.components.c16.schema import (
    AdvisoryFlag,
    DrawingRenderBatchResult,
    DualDrawingBundle,
    FailedDrawingRender,
    FailureRecord,
    PhaseTimings,
    ReadabilityDiagnostics,
    SuccessfulDrawingRender,
)
from buildemup.components.c16.upstream_adapter import UpstreamInputBundle
from buildemup.components.c16.phases.alpha_envelope import execute_phase_alpha
from buildemup.components.c16.phases.beta_scheduling import execute_phase_beta
from buildemup.components.c16.phases.gamma_working import execute_phase_gamma
from buildemup.components.c16.phases.delta_permit import execute_phase_delta
from buildemup.components.c16.phases.epsilon_attestation import execute_phase_epsilon
from buildemup.components.c16.phases.zeta_bundle import execute_phase_zeta


def render_drawings(
    *,
    selection_result:        SelectionResult,
    upstream_inputs:         UpstreamInputBundle,
    jurisdiction_profile:    JurisdictionProfile,
    config:                  RenderingConfig,
    upstream_advisory_flags: tuple[AdvisoryFlag, ...] = (),
    strict_mode:             bool = True,
) -> SuccessfulDrawingRender | FailedDrawingRender:
    """Render one DualDrawingBundle from one SelectionResult.

    Per v0.5 LOCKED spec § 4.

    Returns:
        SuccessfulDrawingRender on success.
        FailedDrawingRender on PerLayoutDrawingError when strict=False.

    Raises:
        LocalDrawingError     — always halts (config / schema-drift /
                                jurisdiction / orientation-lock).
        PerLayoutDrawingError — when strict_mode=True and per-layout
                                failure occurs.
    """
    capture_timings = config.capture_phase_timings
    capture_diag    = config.capture_readability_diagnostics

    # Phase timings (observability — excluded from cache_keys per R7d)
    t_alpha = t_beta = t_gamma = t_delta = t_epsilon = t_zeta = 0
    t_start_total = time.perf_counter_ns()

    try:
        # ────────────── Phase α ──────────────
        t0 = time.perf_counter_ns() if capture_timings else 0
        envelope = execute_phase_alpha(
            selection_result=selection_result,
            upstream_inputs=upstream_inputs,
            jurisdiction_profile=jurisdiction_profile,
            config=config,
        )
        t_alpha = (time.perf_counter_ns() - t0) // 1000 if capture_timings else 0

        # ────────────── Phase β ──────────────
        t0 = time.perf_counter_ns() if capture_timings else 0
        scheduling = execute_phase_beta(envelope=envelope)
        t_beta = (time.perf_counter_ns() - t0) // 1000 if capture_timings else 0

        # ────────────── Phase γ ──────────────
        t0 = time.perf_counter_ns() if capture_timings else 0
        working_model = execute_phase_gamma(
            envelope=envelope,
            scheduling=scheduling,
            config=config,
        )
        t_gamma = (time.perf_counter_ns() - t0) // 1000 if capture_timings else 0

        # ────────────── Phase δ ──────────────
        t0 = time.perf_counter_ns() if capture_timings else 0
        permit_model_provisional = execute_phase_delta(
            envelope=envelope,
            upstream_inputs=upstream_inputs,
            jurisdiction_profile=jurisdiction_profile,
            config=config,
        )
        t_delta = (time.perf_counter_ns() - t0) // 1000 if capture_timings else 0

        # ────────────── Phase ε ──────────────
        t0 = time.perf_counter_ns() if capture_timings else 0
        permit_model = execute_phase_epsilon(
            envelope=envelope,
            permit_model=permit_model_provisional,
            upstream_inputs=upstream_inputs,
            jurisdiction_profile=jurisdiction_profile,
        )
        t_epsilon = (time.perf_counter_ns() - t0) // 1000 if capture_timings else 0

        # ────────────── Phase ζ ──────────────
        t0 = time.perf_counter_ns() if capture_timings else 0

        phase_timings: Optional[PhaseTimings] = None
        if capture_timings:
            phase_timings = PhaseTimings(
                alpha_envelope_assembly_ms=t_alpha // 1000,
                beta_scheduling_ms=t_beta // 1000,
                gamma_working_assembly_ms=t_gamma // 1000,
                delta_permit_assembly_ms=t_delta // 1000,
                epsilon_attestation_packaging_ms=t_epsilon // 1000,
                zeta_bundle_assembly_ms=0,  # filled below
                total_ms=(t_alpha + t_beta + t_gamma + t_delta + t_epsilon) // 1000,
            )

        readability: Optional[ReadabilityDiagnostics] = None
        if capture_diag:
            # v1 default — no congestion / no suppressions
            # (full heuristics: B-C16-READABILITY-FULL-HEURISTICS)
            readability = ReadabilityDiagnostics(
                collision_count=0,
                suppressed_annotations=(),
                viewport_congestion_score=0.0,
                readability_degraded=False,
            )

        bundle = execute_phase_zeta(
            envelope=envelope,
            working_model=working_model,
            permit_model=permit_model,
            selection_result=selection_result,
            jurisdiction_profile=jurisdiction_profile,
            config=config,
            upstream_cache_key=upstream_inputs.upstream_cache_key,
            upstream_advisory_flags=upstream_advisory_flags,
            phase_timings=phase_timings,
            readability_diagnostics=readability,
        )
        t_zeta = (time.perf_counter_ns() - t0) // 1000 if capture_timings else 0

        # If timings captured, rebuild bundle with finalized PhaseTimings.
        # (Bundle is frozen — but timings are observability-only and live
        # OUTSIDE the canonical signature; rebuilding only updates the
        # presentation_signature. For simplicity we omit the rebuild here
        # and accept zeta_micros=0 in the captured timings. Documented as
        # B-C16-ZETA-TIMING-SELF-INCLUSION.)
        _ = t_zeta

        return SuccessfulDrawingRender(bundle=bundle)

    except LocalDrawingError:
        # ALWAYS halts — re-raise regardless of strict_mode
        raise

    except PerLayoutDrawingError as exc:
        if strict_mode:
            raise
        return FailedDrawingRender(
            source_signature=(
                selection_result.replay_identity.selected_layout_signature
            ),
            failure_record=FailureRecord(
                phase=_phase_from_error(exc),
                error_invariant_id=getattr(exc, "invariant_id", "unspecified"),
                error_message=str(exc),
            ),
            partial_bundle=None,
        )


def render_drawings_batch(
    *,
    selection_results:       tuple[SelectionResult, ...],
    upstream_inputs_per:     tuple[UpstreamInputBundle, ...],
    jurisdiction_profile:    JurisdictionProfile,
    config:                  RenderingConfig,
    upstream_advisory_flags_per: tuple[tuple[AdvisoryFlag, ...], ...] = (),
    strict_mode:             bool = False,
) -> DrawingRenderBatchResult:
    """Batch entry point — renders each SelectionResult and aggregates
    successes/failures. STRICT mode halts on first per-layout failure;
    WARN mode collects all.

    Pre: len(selection_results) == len(upstream_inputs_per).
    """
    if len(selection_results) != len(upstream_inputs_per):
        raise ValueError(
            f"render_drawings_batch: selection_results "
            f"({len(selection_results)}) != upstream_inputs_per "
            f"({len(upstream_inputs_per)})."
        )

    if upstream_advisory_flags_per and (
        len(upstream_advisory_flags_per) != len(selection_results)
    ):
        raise ValueError(
            f"render_drawings_batch: upstream_advisory_flags_per length "
            f"mismatch ({len(upstream_advisory_flags_per)} vs "
            f"{len(selection_results)})."
        )

    successes: list[SuccessfulDrawingRender] = []
    failures:  list[FailedDrawingRender] = []

    for i, (sr, ub) in enumerate(zip(selection_results, upstream_inputs_per)):
        flags = (
            upstream_advisory_flags_per[i] if upstream_advisory_flags_per else ()
        )
        result = render_drawings(
            selection_result=sr,
            upstream_inputs=ub,
            jurisdiction_profile=jurisdiction_profile,
            config=config,
            upstream_advisory_flags=flags,
            strict_mode=strict_mode,
        )
        if isinstance(result, SuccessfulDrawingRender):
            successes.append(result)
        else:
            failures.append(result)

    # Canonical lex-ASC ordering by signature (R7c)
    successes_sorted = tuple(sorted(
        successes,
        key=lambda s: s.bundle.source_selection_signature,
    ))
    failures_sorted = tuple(sorted(
        failures, key=lambda f: f.source_signature,
    ))

    return DrawingRenderBatchResult(
        successes=successes_sorted,
        failures=failures_sorted,
    )


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _phase_from_error(exc: PerLayoutDrawingError) -> str:
    """Best-effort phase tagging for FailureRecord. Per the v0.5 spec,
    the failure record carries a Literal["alpha","beta","gamma","delta",
    "epsilon","zeta"]. For PerLayoutDrawingError the originating phase
    is best inferred from the error class:

        MissingUpstreamDataError    → alpha (envelope assembly)
        GeometryInconsistencyError  → alpha (also possible γ — degenerate)
        ComplianceProvenanceError   → epsilon (attestation)
    """
    from buildemup.components.c16.errors import (
        ComplianceProvenanceError,
        GeometryInconsistencyError,
        MissingUpstreamDataError,
    )
    if isinstance(exc, ComplianceProvenanceError):
        return "epsilon"
    if isinstance(exc, (MissingUpstreamDataError, GeometryInconsistencyError)):
        return "alpha"
    return "alpha"
