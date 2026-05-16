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

import dataclasses
import functools
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
    TopologyFamilyTransitionPolicy,
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

    Per Spec #4 v1.6 LOCKED (B-NEW-T3 enabler #4):
    when the source is a real MultiFloorWetZonePlannedCandidate (detected
    via the marker-attribute pattern of Spec #3), dispatch is routed to
    `_generate_seeds_multi_floor` which applies per-floor operators with
    bipartite operator+floor interleaving (Spec § 3.2) and M8 with cyclic
    target selection (§ 3.4). Single-floor briefs continue through the
    legacy single-floor path byte-identical.
    """
    # Spec #4 v1.6 § 3.10 — multi-floor branch detection.
    from buildemup.components.c11a.candidate_context import (
        is_real_multi_floor_candidate,
    )
    if is_real_multi_floor_candidate(source):
        return _generate_seeds_multi_floor(
            source=source,
            source_index=source_index,
            floor_room_brief=floor_room_brief,
            grid=grid,
            plot_analysis=plot_analysis,
            pipeline=pipeline,
            config=config,
            operator_attempts_log=operator_attempts_log,
            truncated_at_max_seeds=truncated_at_max_seeds,
        )

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
# Spec #4 v1.6 — Multi-floor seed generation (B-NEW-T3 enabler #4)
# =============================================================================


def _generate_seeds_multi_floor(
    *,
    source: Any,                            # MultiFloorWetZonePlannedCandidate
    source_index: int,
    floor_room_brief: Any,                  # MultiFloorDwellingBrief
    grid: Any,
    plot_analysis: Any,
    pipeline: DeepMutationPipeline,
    config: TopologyMutationConfig,
    operator_attempts_log: list[MutationApplicationResult],
    truncated_at_max_seeds: list[bool],
) -> tuple[list[MutationApplicationResult], int]:
    """Multi-floor variant of `_generate_seeds_for_one_source` per
    Spec #4 v1.6 LOCKED § 3.2 (per-floor Tier A bipartite dispatch),
    § 3.3 (per-floor Tier B M6/M7 dispatch), § 3.4 (M8 real impl with
    cyclic target selection), § 3.10 (single-floor backwards compat).

    Flow:
      1. Pre-flight: validate multi-floor protocol on brief + alignment
         between brief and source.
      2. Emit M0_BASE on the wrapper (valid by definition).
      3. For each enabled non-base operator, dispatch:
           - M8 (requires_multi_floor=True): cyclic target selection
             via `apply_m8_real`. One attempt per family-allocator slot.
           - Per-floor operators (M0-M7, M9 — requires_multi_floor=False):
             bipartite operator+floor interleaving via
             `_generate_per_floor_attempts`. Each (operator, floor_label)
             pair is one slot. Operator is applied to the per-floor WZPC
             at that label; the wrapper carries the per-floor lineage
             via `floor_label_affected` on the result.

    Single-floor briefs are NOT routed here; they continue through the
    legacy single-floor path in `_generate_seeds_for_one_source`.
    """
    from buildemup.components.c11a.m8_floor_swap_real import apply_m8_real

    # Pre-flight: validate brief + source multi-floor protocol + alignment.
    # These guards catch orchestration drift early — before any C9/C10
    # cascade work — and surface as OrchestrationError if they fail.
    #
    # Asymmetry note (self-review fix 7 at S41 close): unlike the
    # single-floor path (which returns per-candidate invalid results on
    # malformed inputs), these pre-flights RAISE rather than catching
    # per-candidate. This is intentional per Spec #4 v1.6 § 3.1: multi-
    # floor protocol/alignment violations are tagged severity_tier=
    # systemic, meaning "the layer above the per-candidate loop is mis-
    # wired." Recovering by skipping the candidate would mask a real
    # bug (e.g., paired wrong brief with wrong source). The whole batch
    # aborts; the OrchestrationError propagates to mutate_topologies'
    # caller for diagnosis.
    _validate_multi_floor_protocol(floor_room_brief)
    _validate_multi_floor_protocol(source)
    _validate_multi_floor_alignment(floor_room_brief, source)

    # Signature + family for the wrapper (Spec #4 § 3.5 + § 3.7).
    source_signature = _derive_source_signature(source, source_index)
    source_family_id = _derive_source_family_id(source)

    accepted: list[MutationApplicationResult] = []
    seen_variant_ids: set[str] = set()
    deduplicated = 0

    enabled_set = set(config.enabled_operators)

    # Step 1 — emit M0_BASE on the wrapper.
    if config.emit_base and MutationOperator.M0_BASE in enabled_set:
        # M0 is identity; it always passes for a valid wrapper.
        # Carry the source as output_candidate (Pattern B fix follow-up):
        # M0 represents "source as identity baseline", so consumers
        # scoring/comparing results expect output_candidate to be
        # readable for ALL valid results, with M0 returning the
        # unchanged source. Without this, the consumer must special-
        # case `if op==M0: use source else: use output_candidate`.
        m0_result = MutationApplicationResult(
            operator=MutationOperator.M0_BASE,
            valid=True,
            invalidity_reason=None,
            topology_variant_id=f"{source_signature}:m0",
            rejection_invariant_id=None,
            source_family_id=source_family_id,
            output_family_id=source_family_id,
            family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
            lineage_depth=MutationLineageDepth.SHALLOW_TRANSFORM,
            upstream_regeneration_delta=(),
            floor_label_affected=None,   # M0 is wrapper-wide
            output_candidate=source,
        )
        operator_attempts_log.append(m0_result)
        seen_variant_ids.add(m0_result.topology_variant_id or "")
        accepted.append(m0_result)

    # Step 2 — per-family slot allocation (multi-floor cap: each
    # family's slot ceiling is `enabled_ops * num_floors` to enable
    # bipartite (op × floor) coverage per Spec #4 v1.6 § 3.2).
    family_assignments = allocate_family_slots(
        enabled_operators=config.enabled_operators,
        family_slot_allocations=config.family_slot_allocations,
        max_seeds_per_input=config.max_seeds_per_input,
        floor_count_for_cap=len(source.floor_labels),
    )

    # Step 3 — iterate families lex-ASC.
    for assignment in family_assignments:
        if assignment.slot_count == 0:
            continue
        if assignment.family == MutationOperatorFamily.BASE:
            continue

        slots_remaining = assignment.slot_count

        # Partition operators in this family by requires_multi_floor.
        per_floor_ops: list[MutationOperator] = []
        m8_ops: list[MutationOperator] = []
        for op in assignment.enabled_operators_in_family:
            if OPERATOR_METADATA[op].requires_multi_floor:
                m8_ops.append(op)
            else:
                per_floor_ops.append(op)

        # M8 dispatch (cyclic real impl per Spec § 3.4).
        for op in m8_ops:
            if slots_remaining <= 0:
                break
            m8_result = _dispatch_m8_real(
                source=source,
                brief=floor_room_brief,
                operator=op,
                config=config,
                grid=grid,
                plot_analysis=plot_analysis,
                source_family_id=source_family_id,
            )
            operator_attempts_log.append(m8_result)
            if m8_result.valid:
                vid = m8_result.topology_variant_id or ""
                if config.deduplicate_by_signature and vid in seen_variant_ids:
                    deduplicated += 1
                    continue
                seen_variant_ids.add(vid)
                accepted.append(m8_result)
                slots_remaining -= 1

        # Per-floor operator dispatch with bipartite interleaving
        # (Spec § 3.2). Generate ALL (operator, floor_label) attempts
        # for this family, then truncate to slots_remaining.
        if per_floor_ops:
            attempts = _generate_per_floor_attempts(
                tuple(per_floor_ops), source.floor_labels,
            )
            for operator, floor_label in attempts:
                if slots_remaining <= 0:
                    break
                per_floor_result = _dispatch_per_floor_operator(
                    source=source,
                    floor_label=floor_label,
                    operator=operator,
                    floor_room_brief=floor_room_brief,
                    grid=grid,
                    plot_analysis=plot_analysis,
                    pipeline=pipeline,
                    config=config,
                    source_signature=source_signature,
                    source_family_id=source_family_id,
                )
                operator_attempts_log.append(per_floor_result)
                if per_floor_result.valid:
                    vid = per_floor_result.topology_variant_id or ""
                    if (
                        config.deduplicate_by_signature
                        and vid in seen_variant_ids
                    ):
                        deduplicated += 1
                        continue
                    seen_variant_ids.add(vid)
                    accepted.append(per_floor_result)
                    slots_remaining -= 1

    if any(
        a.slot_count > 0 and a.slot_count < len(a.enabled_operators_in_family)
        for a in family_assignments
    ):
        truncated_at_max_seeds[0] = True

    return accepted, deduplicated


def _dispatch_per_floor_operator(
    *,
    source: Any,                            # MultiFloorWetZonePlannedCandidate
    floor_label: str,
    operator: MutationOperator,
    floor_room_brief: Any,                  # MultiFloorDwellingBrief
    grid: Any,
    plot_analysis: Any,
    pipeline: DeepMutationPipeline,
    config: TopologyMutationConfig,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply a per-floor operator (M0-M7, M9 — NOT M8) against the
    per-floor WetZonePlannedCandidate at the given floor label.

    Per Spec #4 v1.6 § 3.2 + § 3.3: per-floor operators are dispatched
    by extracting the WZPC at `floor_label`, running the operator
    against it (Tier A predicate dispatch or Tier B regeneration), and
    annotating the result with `floor_label_affected=floor_label` for
    lineage causality.

    The wrapper itself is NOT reassembled at this layer — downstream
    consumers carry `source_candidate=<wrapper>` plus the result
    metadata identifying which floor was affected. Wrapper rebuilds
    happen in code that consumes the application result (variant
    materialization in C11b / downstream scoring).
    """
    try:
        per_floor_wzpc = source.get_floor(floor_label)
    except KeyError as e:
        return MutationApplicationResult(
            operator=operator,
            valid=False,
            invalidity_reason=f"per_floor_label_not_found: {e}",
            topology_variant_id=None,
            rejection_invariant_id=None,
            source_family_id=source_family_id,
            output_family_id=None,
            family_transition_policy=OPERATOR_METADATA[
                operator
            ].family_transition_policy,
            lineage_depth=MutationLineageDepth.SHALLOW_TRANSFORM,
            upstream_regeneration_delta=(),
            floor_label_affected=floor_label,
        )

    # Build per-floor Tier A context. The context binds to the per-floor
    # WZPC (the source of predicate evaluation), but uses the dwelling-
    # level grid + plot_analysis (which apply to all floors in v1; per-
    # floor grid is B-MFDB-C territory).
    tier_a_context = _build_tier_a_context(
        per_floor_wzpc,
        floor_room_brief.get_floor(floor_label),
        grid,
        plot_analysis,
    )

    # Dispatch via the existing single-floor _apply_one_attempt.
    base_result = _apply_one_attempt(
        operator=operator,
        source=per_floor_wzpc,
        tier_a_context=tier_a_context,
        pipeline=pipeline,
        config=config,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )

    # Re-stamp the result with floor_label_affected and a wrapper-scoped
    # topology_variant_id so dedup across floors works correctly.
    wrapper_vid = (
        f"{base_result.topology_variant_id}::floor={floor_label}"
        if base_result.topology_variant_id
        else None
    )
    return dataclasses.replace(
        base_result,
        topology_variant_id=wrapper_vid,
        floor_label_affected=floor_label,
    )


def _dispatch_m8_real(
    *,
    source: Any,                            # MultiFloorWetZonePlannedCandidate
    brief: Any,                             # MultiFloorDwellingBrief
    operator: MutationOperator,
    config: TopologyMutationConfig,
    grid: Any,
    plot_analysis: Any,
    source_family_id: str,
) -> MutationApplicationResult:
    """Dispatch M8 via the real cyclic-target-selection implementation
    in `m8_floor_swap_real.apply_m8_real`. Per Spec #4 v1.6 § 3.4.

    Builds a per-floor C9->C10 runner via the adapter and feeds it +
    the config's generation counter to apply_m8_real, which handles:
      - eligibility computation (Spec § 3.4 step 2),
      - cyclic target selection (§ 3.4 step 3),
      - per-floor C9->C10 cascade on the two affected floors (step 5),
      - wrapper reassembly with MFWZP invariant re-validation (step 6).

    Failure modes route into invalidity_reason per § 3.4 step 7
    taxonomy (no_viable_master_target / c9_generation_failed /
    c10_validation_failed / orchestration_state_drift:mfwzpN).
    """
    from buildemup.components.c11a.m8_floor_swap_real import apply_m8_real
    from buildemup.components.c11a.multi_floor_c9_c10_adapter import (
        make_per_floor_c9_runner,
    )

    # Build the per-floor C9->C10 runner. Per Spec #4 v1.6 § 3.4 + the
    # self-review fix at S41 close (Issue 3): runner now extracts each
    # floor's OWN CDC from that floor's ancestry inside the cascade,
    # rather than baking floors[0]'s CDC at factory time. This is
    # forward-compatible with heterogeneous multi-floor wrappers.
    runner = make_per_floor_c9_runner(
        grid=grid,
        plot_analysis=plot_analysis,
    )

    # Look up the operator's index in its family for cyclic determinism.
    operator_index = _operator_index_in_family(operator)

    base_result = apply_m8_real(
        source=source,
        brief=brief,
        generation=config.generation,
        operator_index=operator_index,
        run_c9_per_floor=runner,
        source_family_id=source_family_id,
    )

    # Stamp a wrapper-scoped variant_id when valid (apply_m8_real returns
    # variant_id=None — the orchestrator owns naming).
    if base_result.valid:
        # Variant id encodes the wrapper signature + the m8 family marker.
        # Generation participates so successive M8 mutations on the same
        # source produce distinct variant ids even when they happen to
        # pick different targets.
        wrapper_vid = (
            f"m8:gen={config.generation}:src_family={source_family_id}"
        )
        return dataclasses.replace(
            base_result,
            topology_variant_id=wrapper_vid,
            floor_label_affected=None,   # M8 is dwelling-wide (Spec § 3.8)
        )
    return base_result


@functools.lru_cache(maxsize=None)
def _operator_index_in_family(operator: MutationOperator) -> int:
    """Return the operator's index within its family's
    `enabled_operators_in_family` ordering, used by the M8 cyclic
    algorithm for cross-process determinism.

    For M8 specifically (the only multi-floor operator in v1), index
    is always 0 within the VERTICAL family — but if a future amendment
    adds sibling multi-floor operators, this helper extends naturally.

    Cached (self-review fix 6 at S41 close): result is invariant for
    a fixed OPERATOR_METADATA. Avoids re-sorting on every M8 dispatch.
    """
    metadata = OPERATOR_METADATA[operator]
    family = metadata.family
    siblings = sorted(
        (op for op, m in OPERATOR_METADATA.items() if m.family == family),
        key=lambda o: o.value,
    )
    return siblings.index(operator)


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


# =============================================================================
# Spec #4 v1.6 — Multi-floor orchestration helpers (B-NEW-T3 enabler #4)
# =============================================================================
#
# Per Spec #4 v1.6:
#   § 3.1 — _validate_multi_floor_protocol / _validate_multi_floor_alignment
#   § 3.2 — _generate_per_floor_attempts (bipartite round-major interleaving)
#   § 3.11 — affected_floor_set with split-kwarg API
#
# These helpers are intentionally factored as module-level functions so
# they are unit-testable independently of the larger mutate_topologies
# pipeline. The orchestrator's per-floor expansion logic (when input is
# a MultiFloorDwellingBrief) consumes them; Sub-4 will wire the full
# per-floor dispatch loop. v1.6 ships the helpers + M8 real impl; the
# `mutate_topologies` end-to-end multi-floor branch is filed for Sub-4
# integration work per the build plan.


def _validate_multi_floor_protocol(obj: Any) -> None:
    """Pre-flight: confirm ``obj`` conforms to the multi-floor protocol.

    Per Spec #4 v1.6 § 3.1: catches duck-type impostors that have some
    attributes but not all (or whose cardinality is mismatched). Real
    ``MultiFloorDwellingBrief`` instances (Spec #1) pass.

    Required:
      - ``is_multi_floor`` attribute exists AND is truthy.
      - ``floor_labels`` attribute exists AND is len()-measurable.
      - ``floors`` attribute exists AND is len()-measurable AND len >= 2.
      - len(floors) == len(floor_labels).

    Raises:
      OrchestrationProtocolError on any violation.
    """
    from buildemup.components.c11a.errors import OrchestrationProtocolError

    if not getattr(obj, "is_multi_floor", False):
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: is_multi_floor must be True; "
            f"got {getattr(obj, 'is_multi_floor', '<missing>')!r}"
        )
    if not hasattr(obj, "floor_labels"):
        raise OrchestrationProtocolError(
            "Multi-floor protocol violation: missing floor_labels attribute"
        )
    floors = getattr(obj, "floors", None)
    if floors is None:
        raise OrchestrationProtocolError(
            "Multi-floor protocol violation: missing floors attribute"
        )
    try:
        n = len(floors)
    except TypeError:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: floors not measurable; "
            f"got {type(floors).__name__}"
        )
    if n < 2:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: floors must have len >= 2; "
            f"got {n}"
        )
    try:
        labels_len = len(obj.floor_labels)
    except TypeError:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: floor_labels not measurable; "
            f"got {type(obj.floor_labels).__name__}"
        )
    if labels_len != n:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: floor_labels length "
            f"({labels_len}) != floors length ({n})"
        )


def _validate_multi_floor_alignment(brief: Any, source: Any) -> None:
    """Pre-flight: confirm source's per-floor labels match brief's
    per-floor labels exactly (identity + order + count).

    Per Spec #4 v1.6 § 3.1: guards against orchestration drift where
    the brief and source came from different construction paths.

    Required:
      - source.floor_labels == brief.floor_labels (exact tuple equality).
      - source.master_bedroom_floor_label == brief.master_bedroom_floor_label.

    Raises:
      OrchestrationAlignmentError if any condition fails.
    """
    from buildemup.components.c11a.errors import OrchestrationAlignmentError

    if source.floor_labels != brief.floor_labels:
        raise OrchestrationAlignmentError(
            f"Multi-floor alignment violation: source.floor_labels="
            f"{source.floor_labels!r} != brief.floor_labels="
            f"{brief.floor_labels!r}"
        )
    if source.master_bedroom_floor_label != brief.master_bedroom_floor_label:
        raise OrchestrationAlignmentError(
            f"Multi-floor alignment violation: "
            f"source.master_bedroom_floor_label="
            f"{source.master_bedroom_floor_label!r} != "
            f"brief.master_bedroom_floor_label="
            f"{brief.master_bedroom_floor_label!r}"
        )


def _generate_per_floor_attempts(
    operators_in_family: tuple[MutationOperator, ...],
    floor_labels: tuple[str, ...],
) -> tuple[tuple[MutationOperator, str], ...]:
    """Bipartite operator+floor interleaving per Spec #4 v1.6 § 3.2.

    Round-major outer loop: round 0 emits one (operator, floor) pair
    for each operator with a rotated floor; round 1 rotates again; etc.

    For n_operators=4, n_floors=4, the generated order is:
        round 0: (M0, F0), (M2, F1), (M3, F2), (M4, F3)
        round 1: (M0, F1), (M2, F2), (M3, F3), (M4, F0)
        round 2: (M0, F2), (M2, F3), (M3, F0), (M4, F1)
        round 3: (M0, F3), (M2, F0), (M3, F1), (M4, F2)

    Fairness property (Spec § 3.2): bounded imbalance <= 1 on both
    operator and floor axes under slot truncation, starvation-free
    for S >= max(n_ops, n_fl).

    Args:
        operators_in_family: tuple of operators to dispatch.
        floor_labels: tuple of floor labels (typically from
            wrapper.floor_labels).

    Returns:
        Tuple of (operator, floor_label) pairs in the bipartite
        round-major order.
    """
    attempts: list[tuple[MutationOperator, str]] = []
    n_floors = len(floor_labels)
    if n_floors == 0:
        return ()
    for round_idx in range(n_floors):
        for operator_index, operator in enumerate(operators_in_family):
            floor_index = (operator_index + round_idx) % n_floors
            attempts.append((operator, floor_labels[floor_index]))
    return tuple(attempts)


def affected_floor_set(
    operator: MutationOperator,
    source: Any,
    *,
    direct_floor_label: Optional[str] = None,
    new_master_floor_label: Optional[str] = None,
) -> frozenset:
    """Return the set of FloorImpact entries describing how the given
    operator's application affects each floor.

    Per Spec #4 v1.6 § 3.11 — split-kwarg API (v1.5, item 1 from v1.4
    critique walk).

      - Per-floor operators (M0-M7, M9): caller passes
        ``direct_floor_label=L``. Returns
        ``{FloorImpact(L, "direct", cascade=True, validation_only=False)}``.
        ``new_master_floor_label`` MUST be None.

      - M8 (dwelling-wide): caller passes ``new_master_floor_label=L``.
        Returns two FloorImpact entries — the old master floor + the
        new master floor — both with ``kind="direct"``,
        ``requires_cascade=True``. ``direct_floor_label`` MUST be None.

    Validation rule: exactly one of ``direct_floor_label`` and
    ``new_master_floor_label`` must be provided. Which one is
    determined by the operator's class:
      - operator.requires_multi_floor=False → direct_floor_label
      - operator.requires_multi_floor=True  → new_master_floor_label

    Convention: ``requires_cascade XOR requires_validation_only`` —
    a floor either gets full regeneration or just constraint re-check,
    never both, never neither. Direct kinds default to cascade=True;
    indirect kinds (future B-C11A-7) will default to validation_only=True.

    Raises OrchestrationProtocolError if both kwargs are None or
    both are set, or if the wrong one is set for the operator's class.
    """
    from buildemup.components.c11a.errors import OrchestrationProtocolError
    from buildemup.components.c11a.operator_metadata import OPERATOR_METADATA
    from buildemup.components.c11a.schema import FloorImpact

    metadata = OPERATOR_METADATA[operator]

    if metadata.requires_multi_floor:
        if new_master_floor_label is None:
            raise OrchestrationProtocolError(
                f"affected_floor_set: new_master_floor_label required "
                f"for multi-floor operator {operator}"
            )
        if direct_floor_label is not None:
            raise OrchestrationProtocolError(
                f"affected_floor_set: direct_floor_label MUST be None "
                f"for multi-floor operator {operator}; got "
                f"{direct_floor_label!r}"
            )
        # M8 today; future multi-floor operators extend here.
        return frozenset({
            FloorImpact(
                label=source.master_bedroom_floor_label,
                kind="direct",
                requires_cascade=True,
                requires_validation_only=False,
            ),
            FloorImpact(
                label=new_master_floor_label,
                kind="direct",
                requires_cascade=True,
                requires_validation_only=False,
            ),
        })
    else:
        if direct_floor_label is None:
            raise OrchestrationProtocolError(
                f"affected_floor_set: direct_floor_label required for "
                f"per-floor operator {operator}"
            )
        if new_master_floor_label is not None:
            raise OrchestrationProtocolError(
                f"affected_floor_set: new_master_floor_label MUST be "
                f"None for per-floor operator {operator}; got "
                f"{new_master_floor_label!r}"
            )
        return frozenset({
            FloorImpact(
                label=direct_floor_label,
                kind="direct",
                requires_cascade=True,
                requires_validation_only=False,
            ),
        })


__all__ = [
    "mutate_topologies",
    # Spec #4 v1.6: multi-floor orchestration helpers
    "_validate_multi_floor_protocol",
    "_validate_multi_floor_alignment",
    "_generate_per_floor_attempts",
    "affected_floor_set",
]
