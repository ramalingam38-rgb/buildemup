"""
BuildemUp — Component 11a — mutate_topologies orchestrator (Sub-session 4)
=============================================================================

Per spec § 2 / § 3: the C11a entry point. Per-candidate semantics
mirror C9/C10 § 14.40.

Phases:

  Phase 0 — input + startup validation (purity, sunset, severity audit)
  Phase 1 — per-candidate seed generation
  Phase 2 — output assembly + diagnostics
  Phase 3 — provenance assembly

Determinism guarantees (Inv 30 + replay tests):
  * Family iteration order: lex-ASC of family.value
  * Operator iteration within family: lex-ASC of operator.value
  * Output order: per-candidate accept buffer order, candidates in
    input order
  * variant_id: deterministic SHA256-prefix from operator + source sig
  * derived_at and elapsed_seconds are observational; they are
    excluded from canonical-serialize replay hashes via
    ``_observational_runtime_ms``
"""
from __future__ import annotations

import hashlib
import math
import time
from typing import Any, Callable, Mapping, Optional

from buildemup.components.c11a.candidate_context import (
    CandidateContextSchemaError,
    extract_tier_a_context,
    extract_topology_kind,
)
from buildemup.components.c11a.source_signature import derive_signature
from buildemup.components.c11a.deep_pipeline import (
    DeepMutationPipeline,
)
from buildemup.components.c11a.errors import (
    BatchAllNonBaseFailedError,
    TopologyMutationError,
)
from buildemup.components.c11a.family_slot_allocator import (
    allocate_family_slots,
)
from buildemup.components.c11a.operator_metadata import OPERATOR_METADATA
from buildemup.components.c11a.operators import (
    TierAOperatorContext,
    apply_m0_base,
    apply_m1_horiz_flip,
    apply_m2_vert_flip,
    apply_m3a_stair_east,
    apply_m3b_stair_west,
    apply_m3c_stair_ne,
    apply_m4_corridor_inv,
    apply_m5_zone_swap,
    apply_m6_wet_rotate,
    apply_m7a_grid_3_3,
    apply_m7b_grid_2_7,
    apply_m8_vert_rearr,
    apply_m9a_entry_ne_center,
    apply_m9b_entry_ne_corner_w,
    apply_m9c_entry_ne_corner_e,
    apply_m9d_entry_offset_ne,
)
from buildemup.components.c11a.phase0 import run_phase_0_startup_validation
from buildemup.components.c11a.provenance import (
    MutatedTopologyCandidate,
    TopologyMutationProvenance,
)
from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationDiagnostics,
    MutationLineageDepth,
    MutationOperator,
    MutationOperatorFamily,
    MutationTier,
    ProvenanceVerbosity,
    QuarantineFingerprint,
    TopologyMutationConfig,
)
from buildemup.components.c11a.upstream_adapter import RealUpstreamRegenerator


# =============================================================================
# Tier-specific dispatch tables
# =============================================================================


_TIER_A_DISPATCH: Mapping[
    MutationOperator,
    Callable[..., MutationApplicationResult],
] = {
    MutationOperator.M0_BASE:         apply_m0_base,
    MutationOperator.M1_HORIZ_FLIP:   apply_m1_horiz_flip,
    MutationOperator.M2_VERT_FLIP:    apply_m2_vert_flip,
    MutationOperator.M3A_STAIR_EAST:  apply_m3a_stair_east,
    MutationOperator.M3B_STAIR_WEST:  apply_m3b_stair_west,
    MutationOperator.M3C_STAIR_NE:    apply_m3c_stair_ne,
    MutationOperator.M4_CORRIDOR_INV: apply_m4_corridor_inv,
    MutationOperator.M5_ZONE_SWAP:    apply_m5_zone_swap,
    MutationOperator.M9A_ENTRY_CTR:   apply_m9a_entry_ne_center,
    MutationOperator.M9B_ENTRY_W:     apply_m9b_entry_ne_corner_w,
    MutationOperator.M9C_ENTRY_E:     apply_m9c_entry_ne_corner_e,
    MutationOperator.M9D_ENTRY_OFF:   apply_m9d_entry_offset_ne,
}

_TIER_B_DISPATCH: Mapping[
    MutationOperator,
    Callable[..., MutationApplicationResult],
] = {
    MutationOperator.M6_WET_ROTATE:   apply_m6_wet_rotate,
    MutationOperator.M7A_GRID_3_3:    apply_m7a_grid_3_3,
    MutationOperator.M7B_GRID_2_7:    apply_m7b_grid_2_7,
    MutationOperator.M8_VERT_REARR:   apply_m8_vert_rearr,
}


# =============================================================================
# Identity-derivation helpers
# =============================================================================


def _derive_source_signature(source: Any, source_index: int) -> str:
    """Per B-NEW-U: deterministic identity hash via canonical structural
    serialise (real WetZonePlannedCandidate) or repr+index fallback
    (synthetic test fixtures). See source_signature.derive_signature
    for the full design rationale.

    Real candidates with structurally-equal state produce equal
    signatures — making the Tier B cache hit deterministically across
    invocations on equivalent inputs.
    """
    return derive_signature(source, source_index)


def _derive_source_family_id(source: Any) -> str:
    """Best-effort topology family id extraction. Falls back to
    ``"unknown"`` — operationally fine at v1.

    Per B-NEW-V: dispatches between strict (real WetZonePlannedCandidate,
    canonical ancestry path) and lenient (synthetic test fixtures,
    multi-fallback walks).
    """
    return extract_topology_kind(source)


def _build_tier_a_context(
    source: Any,
    floor_room_brief: Any,
    grid: Any,
    plot_analysis: Any,
) -> TierAOperatorContext:
    """Extract TierAOperatorContext fields per B-NEW-V dispatcher.

    For real ``WetZonePlannedCandidate`` inputs, walks the v1.0
    canonical ancestry chain strictly — schema drift raises
    ``CandidateContextSchemaError`` so the orchestrator can surface
    affected candidates per-candidate.

    For synthetic test fixtures (Sub-4 ``_FakeWetZoneCandidate``),
    falls back to lenient duck-type walks. floor_room_brief is unused
    here (extractors only read source + grid + plot_analysis).
    """
    return extract_tier_a_context(source, grid, plot_analysis)


def _is_multi_floor(floor_room_brief: Any) -> bool:
    if hasattr(floor_room_brief, "is_multi_floor"):
        return bool(floor_room_brief.is_multi_floor)
    floors = getattr(floor_room_brief, "floors", None)
    if floors is not None:
        try:
            return len(floors) > 1
        except TypeError:
            return False
    return False


# =============================================================================
# Per-operator dispatch
# =============================================================================


def _apply_one_attempt(
    *,
    operator: MutationOperator,
    source: Any,
    tier_a_context: TierAOperatorContext,
    pipeline: DeepMutationPipeline,
    config: TopologyMutationConfig,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """One operator dispatch — Tier A direct, Tier B via pipeline.

    Tier B's NotImplementedError (B-NEW-T) is caught here and surfaced
    as per-candidate invalid (rather than batch-halt).
    """
    metadata = OPERATOR_METADATA[operator]
    if metadata.tier == MutationTier.SHALLOW:
        apply_fn = _TIER_A_DISPATCH[operator]
        return apply_fn(
            source, tier_a_context,
            source_signature=source_signature,
            source_family_id=source_family_id,
        )

    apply_fn = _TIER_B_DISPATCH[operator]
    try:
        return apply_fn(
            source, pipeline,
            config=config,
            source_signature=source_signature,
            source_family_id=source_family_id,
        )
    except NotImplementedError as exc:
        # B-NEW-T pending: surface as per-candidate invalid.
        return MutationApplicationResult(
            operator=operator,
            valid=False,
            invalidity_reason=(
                f"Tier B regenerator not wired for operator "
                f"{operator.value} (B-NEW-T pending). Pass "
                f"upstream_regenerator= to mutate_topologies(). "
                f"Underlying: {str(exc)[:160]}"
            ),
            topology_variant_id=None,
            rejection_invariant_id=None,
            source_family_id=source_family_id,
            output_family_id=None,
            family_transition_policy=metadata.family_transition_policy,
            lineage_depth=MutationLineageDepth.REGENERATIVE_TRANSFORM,
            upstream_regeneration_delta=(),
        )


# =============================================================================
# Phase 1 — per-candidate seed generation
# =============================================================================


def _generate_seeds_for_one_source(
    *,
    source: Any,
    source_index: int,
    floor_room_brief: Any,
    grid: Any,
    plot_analysis: Any,
    pipeline: DeepMutationPipeline,
    config: TopologyMutationConfig,
    operator_attempts_log: list[MutationApplicationResult],
    truncated_at_max_seeds: list[bool],
) -> tuple[
    list[MutationApplicationResult],   # accepted application results
    int,                                # deduplicated count
]:
    """Phase 1 per-source. Returns (accepted_results, deduplicated_count).

    Caller wraps each accepted result into a MutatedTopologyCandidate
    after Phase 2 builds the shared provenance.
    """
    source_signature = _derive_source_signature(source, source_index)
    source_family_id = _derive_source_family_id(source)
    tier_a_context = _build_tier_a_context(
        source, floor_room_brief, grid, plot_analysis,
    )

    accepted: list[MutationApplicationResult] = []
    seen_variant_ids: set[str] = set()
    deduplicated = 0

    enabled_set = set(config.enabled_operators)

    # Step 1 — emit M0_BASE (only counts if enabled and emit_base).
    if config.emit_base and MutationOperator.M0_BASE in enabled_set:
        result = _apply_one_attempt(
            operator=MutationOperator.M0_BASE,
            source=source, tier_a_context=tier_a_context,
            pipeline=pipeline, config=config,
            source_signature=source_signature,
            source_family_id=source_family_id,
        )
        operator_attempts_log.append(result)
        if result.valid:
            seen_variant_ids.add(result.topology_variant_id or "")
            accepted.append(result)

    # Step 2 — per-family slot allocation.
    family_assignments = allocate_family_slots(
        enabled_operators=config.enabled_operators,
        family_slot_allocations=config.family_slot_allocations,
        max_seeds_per_input=config.max_seeds_per_input,
    )

    # Step 3 — iterate families lex-ASC; first slot_count valid fill quota.
    for assignment in family_assignments:
        if assignment.slot_count == 0:
            continue
        if assignment.family == MutationOperatorFamily.BASE:
            # Already handled above.
            continue

        slots_remaining = assignment.slot_count
        for operator in assignment.enabled_operators_in_family:
            if slots_remaining <= 0:
                break

            # Skip M8 on single-floor briefs per F-v2-8.
            metadata = OPERATOR_METADATA[operator]
            if metadata.requires_multi_floor and not _is_multi_floor(floor_room_brief):
                operator_attempts_log.append(
                    MutationApplicationResult(
                        operator=operator,
                        valid=False,
                        invalidity_reason="single_floor_brief",
                        topology_variant_id=None,
                        rejection_invariant_id=None,
                        source_family_id=source_family_id,
                        output_family_id=None,
                        family_transition_policy=metadata.family_transition_policy,
                        lineage_depth=MutationLineageDepth.SHALLOW_TRANSFORM,
                        upstream_regeneration_delta=(),
                    )
                )
                continue

            result = _apply_one_attempt(
                operator=operator,
                source=source, tier_a_context=tier_a_context,
                pipeline=pipeline, config=config,
                source_signature=source_signature,
                source_family_id=source_family_id,
            )
            operator_attempts_log.append(result)

            if result.valid:
                vid = result.topology_variant_id or ""
                if config.deduplicate_by_signature and vid in seen_variant_ids:
                    deduplicated += 1
                    continue
                seen_variant_ids.add(vid)
                accepted.append(result)
                slots_remaining -= 1

    # Truncation flag — Sub-4 simplification: True if any family hit
    # its slot_count cap (i.e., had more enabled ops than slots).
    if any(
        a.slot_count > 0 and a.slot_count < len(a.enabled_operators_in_family)
        for a in family_assignments
    ):
        truncated_at_max_seeds[0] = True

    return accepted, deduplicated


# =============================================================================
# Phase 2 — diagnostics
# =============================================================================


def _compute_diagnostics(
    *,
    operator_attempts_log: list[MutationApplicationResult],
    accepted_results: list[MutationApplicationResult],
    pipeline: DeepMutationPipeline,
    elapsed_seconds: float,
) -> MutationDiagnostics:
    """Phase 2 diagnostics. Per § 2.4."""
    per_op_attempted: dict[MutationOperator, int] = {}
    per_op_accepted: dict[MutationOperator, int] = {}

    for r in operator_attempts_log:
        per_op_attempted[r.operator] = per_op_attempted.get(r.operator, 0) + 1
        if r.valid:
            per_op_accepted[r.operator] = per_op_accepted.get(r.operator, 0) + 1

    per_family_attempted: dict[MutationOperatorFamily, int] = {}
    per_family_accepted: dict[MutationOperatorFamily, int] = {}
    for op, count in per_op_attempted.items():
        family = OPERATOR_METADATA[op].family
        per_family_attempted[family] = per_family_attempted.get(family, 0) + count
    for op, count in per_op_accepted.items():
        family = OPERATOR_METADATA[op].family
        per_family_accepted[family] = per_family_accepted.get(family, 0) + count

    # Per-operator yield (accepted / attempted).
    per_operator_yield: dict[MutationOperator, float] = {
        op: per_op_accepted.get(op, 0) / count
        for op, count in per_op_attempted.items()
    }
    per_family_yield: dict[MutationOperatorFamily, float] = {
        f: per_family_accepted.get(f, 0) / count
        for f, count in per_family_attempted.items()
    }

    # Family spread entropy over accepted candidates.
    family_counts: dict[MutationOperatorFamily, int] = {}
    for r in accepted_results:
        family = OPERATOR_METADATA[r.operator].family
        family_counts[family] = family_counts.get(family, 0) + 1
    family_spread_entropy = _shannon_entropy(family_counts.values())

    # Duplicate ratio over accepted (Sub-4 placeholder — real dedup
    # count from Phase 1 is per-source, summed at orchestrator level).
    duplicate_ratio = 0.0
    if accepted_results:
        duplicate_ratio = 0.0   # populated by orchestrator wrapper

    deep_runtime_ms = int(elapsed_seconds * 1000)

    return MutationDiagnostics(
        per_operator_yield=per_operator_yield,
        per_family_yield=per_family_yield,
        family_spread_entropy=family_spread_entropy,
        duplicate_ratio=duplicate_ratio,
        novelty_deficit_estimator=0.0,
        novelty_estimator_fidelity="low",
        deep_mutation_runtime_ms=deep_runtime_ms,
    )


def _shannon_entropy(counts) -> float:
    counts = list(counts)
    total = sum(counts)
    if total == 0:
        return 0.0
    entropy = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


# =============================================================================
# Quarantine fingerprint (§ 2.9 — Sub-4 implementation)
# =============================================================================


def _compute_quarantine_fingerprint(
    quarantined_operators: tuple[MutationOperator, ...] = (),
    quarantine_reasons: tuple[tuple[str, str], ...] = (),
) -> QuarantineFingerprint:
    """SPEC § 2.9 — fingerprint hash of (quarantined_operators,
    quarantine_reasons).

    At v1.0 LOCK with RegistryValidationMode.STRICT the typical case
    is empty — the orchestrator's call to validate_operator_registry()
    raised on any registry violation, so no operators reach the
    quarantine state. WARN mode would populate these tuples.
    """
    sorted_ops = tuple(
        sorted(quarantined_operators, key=lambda op: op.value)
    )
    sorted_reasons = tuple(sorted(quarantine_reasons, key=lambda kv: kv[0]))

    h = hashlib.sha256()
    h.update("|".join(op.value for op in sorted_ops).encode("utf-8"))
    h.update(b"\x1f")
    h.update("|".join(f"{k}={v}" for k, v in sorted_reasons).encode("utf-8"))
    fingerprint_hash = h.hexdigest()

    return QuarantineFingerprint(
        quarantined_operators=sorted_ops,
        quarantine_reasons=sorted_reasons,
        fingerprint_hash=fingerprint_hash,
    )


# =============================================================================
# Phase 3 — provenance assembly
# =============================================================================


def _assemble_provenance(
    *,
    config: TopologyMutationConfig,
    operator_attempts_log: list[MutationApplicationResult],
    diagnostics: MutationDiagnostics,
    accepted_count: int,
    rejected_count: int,
    deduplicated_count: int,
    truncated_at_max_seeds: bool,
    plot_analysis: Any,
    floor_room_brief: Any,
    derived_at: float,
    elapsed_ms: int,
) -> TopologyMutationProvenance:
    """Phase 3 — provenance assembly per config.provenance_verbosity."""
    if config.provenance_verbosity == ProvenanceVerbosity.SUMMARY:
        attempts_log: tuple[MutationApplicationResult, ...] = ()
    else:
        attempts_log = tuple(operator_attempts_log)

    plot_trace_id = getattr(plot_analysis, "trace_id", None) or "unknown"
    floor_label = _derive_floor_label(floor_room_brief)

    rule_trace = (
        f"phase0:passed",
        f"phase1:attempts={len(operator_attempts_log)},accepted={accepted_count}",
        f"phase2:cache_hits={diagnostics.deep_mutation_runtime_ms}ms_runtime",
        f"phase3:verbosity={config.provenance_verbosity.value}",
    )

    quarantine_fp = _compute_quarantine_fingerprint()

    return TopologyMutationProvenance(
        derived_at=derived_at,
        plot_analysis_trace_id=plot_trace_id,
        floor_label=floor_label,
        enabled_operators_snapshot=tuple(
            op.value for op in config.enabled_operators
        ),
        operator_application_log=attempts_log,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        deduplicated_count=deduplicated_count,
        truncated_at_max_seeds=truncated_at_max_seeds,
        diagnostics=diagnostics,
        rule_trace=rule_trace,
        quarantine_fingerprint=quarantine_fp,
        _observational_runtime_ms=elapsed_ms,
    )


def _derive_floor_label(floor_room_brief: Any) -> str:
    """Best-effort floor label extraction."""
    label = getattr(floor_room_brief, "floor_label", None)
    if label:
        return str(label)
    return "ground"


# =============================================================================
# Top-level orchestrator
# =============================================================================


def mutate_topologies(
    wet_zoned_candidates: tuple[Any, ...],
    floor_room_brief: Any,
    grid: Any,
    plot_analysis: Any,
    *,
    config: Optional[TopologyMutationConfig] = None,
    upstream_regenerator: Any = None,
) -> tuple[MutatedTopologyCandidate, ...]:
    """C11a entry point. Per-candidate semantics mirror C9/C10 § 14.40.

    Args:
        wet_zoned_candidates: input WetZonePlannedCandidates.
        floor_room_brief: brief — used for M8 multi-floor check.
        grid: C7 Grid — carries envelope dims + staircase.
        plot_analysis: C4 PlotAnalysis — provides plot_facing.
        config: optional config; defaults to factory.
        upstream_regenerator: optional Tier B regenerator. None →
            RealUpstreamRegenerator (B-NEW-T pending so Tier B ops
            surface as per-candidate invalid).

    Returns:
        Tuple of MutatedTopologyCandidates in input order; per source
        in (M0_BASE → family lex-ASC → operator lex-ASC) order.
    """
    config = config or TopologyMutationConfig()
    derived_at = time.time()
    start_perf = time.perf_counter()

    # ── Phase 0 ────────────────────────────────────────────────────────
    run_phase_0_startup_validation()

    if not wet_zoned_candidates:
        return ()

    # Build per-batch pipeline.
    if upstream_regenerator is None:
        upstream_regenerator = RealUpstreamRegenerator(
            floor_room_brief=floor_room_brief,
            grid=grid,
            plot_analysis=plot_analysis,
        )
    pipeline = DeepMutationPipeline(
        upstream=upstream_regenerator,
        cache_enabled=config.deep_mutation_cache_enabled,
    )

    # ── Phase 1 ────────────────────────────────────────────────────────
    operator_attempts_log: list[MutationApplicationResult] = []
    all_accepted_results: list[MutationApplicationResult] = []
    all_accepted_sources: list[Any] = []   # parallel to all_accepted_results
    truncated_flag = [False]
    total_deduplicated = 0

    for source_index, source in enumerate(wet_zoned_candidates):
        per_source_results, dedup_count = _generate_seeds_for_one_source(
            source=source,
            source_index=source_index,
            floor_room_brief=floor_room_brief,
            grid=grid,
            plot_analysis=plot_analysis,
            pipeline=pipeline,
            config=config,
            operator_attempts_log=operator_attempts_log,
            truncated_at_max_seeds=truncated_flag,
        )
        for r in per_source_results:
            all_accepted_results.append(r)
            all_accepted_sources.append(source)
        total_deduplicated += dedup_count

    elapsed = time.perf_counter() - start_perf
    elapsed_ms = int(elapsed * 1000)

    # ── Phase 2 ────────────────────────────────────────────────────────
    diagnostics = _compute_diagnostics(
        operator_attempts_log=operator_attempts_log,
        accepted_results=all_accepted_results,
        pipeline=pipeline,
        elapsed_seconds=elapsed,
    )

    # Compute duplicate_ratio against actual deduplicated count.
    # MutationDiagnostics is frozen — rebuild via dataclasses.replace.
    from dataclasses import replace
    if all_accepted_results:
        duplicate_ratio = total_deduplicated / max(1, len(all_accepted_results) + total_deduplicated)
        diagnostics = replace(diagnostics, duplicate_ratio=duplicate_ratio)

    # ── Phase 3 ────────────────────────────────────────────────────────
    rejected_count = sum(1 for r in operator_attempts_log if not r.valid)
    accepted_count = len(all_accepted_results)
    provenance = _assemble_provenance(
        config=config,
        operator_attempts_log=operator_attempts_log,
        diagnostics=diagnostics,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        deduplicated_count=total_deduplicated,
        truncated_at_max_seeds=truncated_flag[0],
        plot_analysis=plot_analysis,
        floor_room_brief=floor_room_brief,
        derived_at=derived_at,
        elapsed_ms=elapsed_ms,
    )

    # Optional batch-level sanity check.
    non_base_attempts = [
        r for r in operator_attempts_log
        if r.operator != MutationOperator.M0_BASE
    ]
    non_base_accepted = [r for r in non_base_attempts if r.valid]
    if (
        non_base_attempts
        and not non_base_accepted
        and getattr(config, "fail_on_all_non_base_failure", False)
    ):
        raise BatchAllNonBaseFailedError(
            f"All {len(non_base_attempts)} non-base operator attempts "
            f"failed across {len(wet_zoned_candidates)} input "
            f"candidate(s)."
        )

    # Wrap accepted results into MutatedTopologyCandidates with shared provenance.
    decorated: list[MutatedTopologyCandidate] = []
    for source, result in zip(all_accepted_sources, all_accepted_results):
        decorated.append(
            MutatedTopologyCandidate(
                source_candidate=source,
                applied_operators=(result.operator,),
                topology_variant_id=result.topology_variant_id or "",
                application_results=(result,),
                provenance=provenance,
            )
        )

    return tuple(decorated)


__all__ = ["mutate_topologies"]
