"""
BuildemUp — Component 11a: Topology Mutation Layer
====================================================

Public surface for C11a per SPEC v1.0 LOCKED.

Sub-session 1 ships:
  - schema (enums, frozen dataclasses, registries)
  - errors (full hierarchy with severity_tier ClassVars)
  - provenance + result types

Sub-session 2 (S39) ships:
  - operators/ (12 Tier A apply_* entry points)
  - operator_metadata.OPERATOR_METADATA (16-entry table)
  - registry.validate_operator_registry (Inv 26 + Inv 28)
  - predicate_registry (9 predicates: 3 callable + 6 stubs)
  - family_slot_allocator (per § 3 Phase 1)

Sub-session 3 will add Tier B operators (M6/M7/M8) +
DeepMutationPipeline. Sub-session 4 will add the
``mutate_topologies()`` orchestrator.
"""
from __future__ import annotations

# Schema re-exports
from buildemup.components.c11a.schema import (
    DeltaKey,
    EnforcementMode,
    FamilySlotAllocation,
    MutationApplicationResult,
    MutationDiagnostics,
    MutationLineageDepth,
    MutationOperator,
    MutationOperatorFamily,
    MutationOperatorMetadata,
    MutationTier,
    MutationViabilityPredicate,
    OperatorExpectedDeltaSchema,
    ProvenanceVerbosity,
    PurityAttestation,
    QuarantineFingerprint,
    RegistryValidationMode,
    TopologyFamilyTransitionPolicy,
    TopologyMutationConfig,
    UpstreamAmendmentWaiver,
    UPSTREAM_PURITY_REGISTRY,
    WAIVER_REGISTRY,
    _OPERATOR_FAMILY_POLICY,
)

# Provenance + result re-exports
from buildemup.components.c11a.provenance import (
    MutatedTopologyCandidate,
    TopologyMutationProvenance,
)

# Errors re-exports
from buildemup.components.c11a.errors import (
    BatchAllNonBaseFailedError,
    DeepMutationApplicationError,
    DeepMutationPurityContractError,
    InvariantViolationError,
    MutationApplicationError,
    OperatorRegistryError,
    PendingUpstreamPredicateError,
    PerCandidateError,
    SeverityClassificationAuditError,
    TopologyInvalidError,
    TopologyMutationError,
)

# Sub-session 2 — predicate registry + operator metadata + registry
# validation + family slot allocator + operator entry points.
from buildemup.components.c11a.operator_metadata import (
    OPERATOR_METADATA,
    get_operator_metadata,
    operators_by_family,
    operators_by_tier,
)
from buildemup.components.c11a.predicate_registry import (
    PREDICATE_REGISTRY,
    lookup_predicate,
    pending_upstream_predicate_count,
    predicate_ids_for,
    predicates_for,
)
from buildemup.components.c11a.registry import validate_operator_registry
from buildemup.components.c11a.family_slot_allocator import (
    FamilySlotAssignment,
    allocate_family_slots,
)
from buildemup.components.c11a.operators import (
    OperatorPreconditionError,
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
    apply_tier_b_operator,
    build_invalid_result,
    build_valid_result,
    derive_variant_id,
    dispatch_predicates,
)

# Sub-session 3 — Tier B pipeline + cache + lineage classification.
from buildemup.components.c11a.cache import (
    C11A_CACHE_KEY_VERSION,
    DeepMutationCacheKey,
    UpstreamVersionInfo,
    derive_cache_config_hash,
    derive_cache_key,
)
from buildemup.components.c11a.lineage import (
    LineageClassification,
    classify_lineage_depth,
)
from buildemup.components.c11a.deep_pipeline import (
    DeepMutationPipeline,
    DeepMutationPipelineResult,
    StubUpstreamRegenerator,
    TierBInputMutation,
    UpstreamRegenerator,
)

# Sub-session 4 — Phase 0 + orchestrator + real upstream adapter.
from buildemup.components.c11a.phase0 import (
    enforce_pending_predicate_sunset,
    run_phase_0_startup_validation,
    validate_severity_classification_audit,
    validate_upstream_purity_contract,
)
from buildemup.components.c11a.upstream_adapter import RealUpstreamRegenerator
from buildemup.components.c11a.orchestrator import mutate_topologies

# Sub-session 5 — B-NEW-V (strict candidate-context extractor) +
# B-NEW-X (WeakSet error registry) patches per S39 critique walk.
from buildemup.components.c11a.candidate_context import (
    CandidateContextSchemaError,
    extract_tier_a_context,
    extract_tier_a_context_from_candidate,
    extract_tier_a_context_lenient,
    extract_topology_kind,
    is_real_wet_zone_candidate,
)
from buildemup.components.c11a.errors import iter_registered_errors
from buildemup.components.c11a.source_signature import (
    derive_canonical_signature,
    derive_signature,
)


__all__ = [
    # ── Sub-session 1: schema ─────────────────────────────────────
    "MutationOperator",
    "MutationTier",
    "MutationOperatorFamily",
    "TopologyFamilyTransitionPolicy",
    "_OPERATOR_FAMILY_POLICY",
    "DeltaKey",
    "OperatorExpectedDeltaSchema",
    "MutationOperatorMetadata",
    "MutationLineageDepth",
    "PurityAttestation",
    "UPSTREAM_PURITY_REGISTRY",
    "UpstreamAmendmentWaiver",
    "WAIVER_REGISTRY",
    "MutationViabilityPredicate",
    "QuarantineFingerprint",
    "TopologyMutationConfig",
    "EnforcementMode",
    "ProvenanceVerbosity",
    "RegistryValidationMode",
    "FamilySlotAllocation",
    "MutationDiagnostics",
    "MutationApplicationResult",
    # ── Sub-session 1: provenance + result ────────────────────────
    "TopologyMutationProvenance",
    "MutatedTopologyCandidate",
    # ── Sub-session 1: errors ─────────────────────────────────────
    "TopologyMutationError",
    "PerCandidateError",
    "TopologyInvalidError",
    "MutationApplicationError",
    "DeepMutationApplicationError",
    "BatchAllNonBaseFailedError",
    "OperatorRegistryError",
    "DeepMutationPurityContractError",
    "PendingUpstreamPredicateError",
    "SeverityClassificationAuditError",
    "InvariantViolationError",
    # ── Sub-session 2: predicate registry ─────────────────────────
    "PREDICATE_REGISTRY",
    "lookup_predicate",
    "predicate_ids_for",
    "predicates_for",
    "pending_upstream_predicate_count",
    # ── Sub-session 2: operator metadata + registry validation ────
    "OPERATOR_METADATA",
    "get_operator_metadata",
    "operators_by_tier",
    "operators_by_family",
    "validate_operator_registry",
    # ── Sub-session 2: family slot allocator ──────────────────────
    "FamilySlotAssignment",
    "allocate_family_slots",
    # ── Sub-session 2: operator implementations ───────────────────
    "OperatorPreconditionError",
    "TierAOperatorContext",
    "apply_m0_base",
    "apply_m1_horiz_flip",
    "apply_m2_vert_flip",
    "apply_m3a_stair_east",
    "apply_m3b_stair_west",
    "apply_m3c_stair_ne",
    "apply_m4_corridor_inv",
    "apply_m5_zone_swap",
    "apply_m9a_entry_ne_center",
    "apply_m9b_entry_ne_corner_w",
    "apply_m9c_entry_ne_corner_e",
    "apply_m9d_entry_offset_ne",
    "build_invalid_result",
    "build_valid_result",
    "derive_variant_id",
    "dispatch_predicates",
    # ── Sub-session 3: Tier B operators ────────────────────────────
    "apply_m6_wet_rotate",
    "apply_m7a_grid_3_3",
    "apply_m7b_grid_2_7",
    "apply_m8_vert_rearr",
    "apply_tier_b_operator",
    # ── Sub-session 3: cache ──────────────────────────────────────
    "DeepMutationCacheKey",
    "derive_cache_config_hash",
    "derive_cache_key",
    # ── Sub-session 3: lineage ────────────────────────────────────
    "LineageClassification",
    "classify_lineage_depth",
    # ── Sub-session 3: deep pipeline ──────────────────────────────
    "DeepMutationPipeline",
    "DeepMutationPipelineResult",
    "StubUpstreamRegenerator",
    "TierBInputMutation",
    "UpstreamRegenerator",
    # ── Sub-session 4: phase 0 + orchestrator + real adapter ──────
    "enforce_pending_predicate_sunset",
    "run_phase_0_startup_validation",
    "validate_severity_classification_audit",
    "validate_upstream_purity_contract",
    "RealUpstreamRegenerator",
    "mutate_topologies",
    # ── Sub-session 5 (S39 critique walk patches) ─────────────────
    "CandidateContextSchemaError",
    "extract_tier_a_context",
    "extract_tier_a_context_from_candidate",
    "extract_tier_a_context_lenient",
    "extract_topology_kind",
    "is_real_wet_zone_candidate",
    "iter_registered_errors",
    "derive_canonical_signature",
    "derive_signature",
    "C11A_CACHE_KEY_VERSION",
    "UpstreamVersionInfo",
]
