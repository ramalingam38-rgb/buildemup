"""
BuildemUp — Component 11a: Topology Mutation Layer
====================================================

Public surface for C11a per SPEC v1.0 LOCKED. Sub-session 1 ships:
- schema (enums, frozen dataclasses, registries)
- errors (full hierarchy with severity_tier ClassVars)
- provenance + result types

Sub-session 2 will add Tier A operator implementations and
`mutate_topologies()` orchestration.

The `mutate_topologies` entry point intentionally does NOT exist
yet — importing it before Sub-session 2 will ImportError, which is
the desired behavior.
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


__all__ = [
    # schema — operator enums
    "MutationOperator",
    "MutationTier",
    "MutationOperatorFamily",
    "TopologyFamilyTransitionPolicy",
    "_OPERATOR_FAMILY_POLICY",
    # schema — delta vocabulary
    "DeltaKey",
    "OperatorExpectedDeltaSchema",
    # schema — operator metadata
    "MutationOperatorMetadata",
    # schema — lineage classification
    "MutationLineageDepth",
    # schema — purity contract
    "PurityAttestation",
    "UPSTREAM_PURITY_REGISTRY",
    # schema — waiver
    "UpstreamAmendmentWaiver",
    "WAIVER_REGISTRY",
    # schema — predicate
    "MutationViabilityPredicate",
    # schema — quarantine
    "QuarantineFingerprint",
    # schema — config
    "TopologyMutationConfig",
    "EnforcementMode",
    "ProvenanceVerbosity",
    "RegistryValidationMode",
    "FamilySlotAllocation",
    # schema — diagnostics + per-op result
    "MutationDiagnostics",
    "MutationApplicationResult",
    # provenance + result
    "TopologyMutationProvenance",
    "MutatedTopologyCandidate",
    # errors
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
]
