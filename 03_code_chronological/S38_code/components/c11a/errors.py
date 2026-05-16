"""
BuildemUp — Component 11a: Topology Mutation Layer — errors
============================================================

Per SPEC § 5 + § 2.7 (v1.0 LOCKED).

Error hierarchy:

    TopologyMutationError (base)
    ├── PerCandidateError
    │   ├── TopologyInvalidError
    │   ├── MutationApplicationError
    │   └── DeepMutationApplicationError
    ├── BatchAllNonBaseFailedError
    ├── OperatorRegistryError
    ├── DeepMutationPurityContractError
    ├── PendingUpstreamPredicateError
    ├── SeverityClassificationAuditError       (NEW v0.5)
    └── InvariantViolationError                (systemic)

Each class declares a `severity_tier` ClassVar in
`{"per_candidate", "batch", "systemic"}` for inversion-of-control
catch routing per § 2.7. Pattern matches the upstream B-NEW-P
amendment shipped at S38.
"""
from __future__ import annotations

from typing import ClassVar, Literal, Optional, Sequence


_SeverityTier = Literal["per_candidate", "batch", "systemic"]


# =============================================================================
# Base hierarchy
# =============================================================================


class TopologyMutationError(Exception):
    """Base for all C11a errors. Per SPEC § 5.

    Default severity is per_candidate (conservative); subclasses
    override to batch / systemic where appropriate.
    """

    severity_tier: ClassVar[_SeverityTier] = "per_candidate"


# -----------------------------------------------------------------------------
# Per-candidate failures (aggregated by orchestrator)
# -----------------------------------------------------------------------------


class PerCandidateError(TopologyMutationError):
    """Marker base for errors that scope to a single
    `WetZonePlannedCandidate × MutationOperator` attempt and should
    aggregate via the partial-batch rule rather than halting."""

    severity_tier: ClassVar[_SeverityTier] = "per_candidate"


class TopologyInvalidError(PerCandidateError):
    """Raised when a per-candidate Tier A or Tier B mutation produces a
    geometrically or semantically invalid topology — for example, an
    operator output that violates an upstream invariant (W9, Inv 21,
    privacy_zoning, etc.).

    Carries `rejection_invariant_id` (owner-prefixed, e.g.,
    "C7_W9", "C8_Inv_21", "C5_privacy_zoning") so the caller can
    diagnose which upstream rule fired.
    """

    severity_tier: ClassVar[_SeverityTier] = "per_candidate"

    def __init__(
        self,
        message: str,
        *,
        rejection_invariant_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.rejection_invariant_id = rejection_invariant_id


class MutationApplicationError(PerCandidateError):
    """Raised when a Tier A (SHALLOW) operator's mutator function fails
    for reasons unrelated to upstream invariants — e.g., the operator's
    own pre-conditions are not met (no central spine to invert for M4
    on a non-applicable topology)."""

    severity_tier: ClassVar[_SeverityTier] = "per_candidate"


class DeepMutationApplicationError(PerCandidateError):
    """Wraps an upstream per-candidate exception caught during Tier B
    DeepMutationPipeline regeneration.

    Per § 2.7 catch logic: when Tier B re-runs C9/C10 (and possibly
    C7/C8 for grid scale), upstream errors with
    `severity_tier="per_candidate"` are caught here and the candidate
    is rejected (not aggregated as a batch failure). Errors with
    `severity_tier="systemic"` propagate uncaught; errors with
    `severity_tier="batch"` are also wrapped (batch-level is treated
    as a systemic failure of the per-candidate Tier B run).
    """

    severity_tier: ClassVar[_SeverityTier] = "per_candidate"

    def __init__(
        self,
        message: str,
        *,
        wrapped_exception: Optional[BaseException] = None,
        upstream_component: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.wrapped_exception = wrapped_exception
        self.upstream_component = upstream_component


# -----------------------------------------------------------------------------
# Batch-level failure
# -----------------------------------------------------------------------------


class BatchAllNonBaseFailedError(TopologyMutationError):
    """Raised when every non-base operator failed for every input
    candidate.

    The orchestrator emits at least M0_BASE (always valid) per
    `config.emit_base=True`, so this only fires when the batch
    successfully emitted M0_BASE outputs but ZERO non-base mutation
    candidates passed. Distinct from `BatchAllFailed` (no successful
    output at all) which would surface from upstream batch errors.
    """

    severity_tier: ClassVar[_SeverityTier] = "batch"

    def __init__(
        self,
        message: str,
        *,
        per_candidate_failures: Sequence[tuple[int, BaseException]] = (),
        input_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.per_candidate_failures = tuple(per_candidate_failures)
        self.input_count = input_count


# -----------------------------------------------------------------------------
# Systemic failures (halt the whole batch)
# -----------------------------------------------------------------------------


class OperatorRegistryError(TopologyMutationError):
    """Raised by `validate_operator_registry()` at startup when the
    operator metadata table is inconsistent with the operator enum
    (e.g., missing operator, conflicting tier, invalid family
    transition policy, DeltaKey enum violation per Inv 28, missing
    cache_relevant metadata per Inv 26).

    Systemic — the registry is global to all batches; a faulty
    registry cannot produce correct mutations for any input.
    """

    severity_tier: ClassVar[_SeverityTier] = "systemic"


class DeepMutationPurityContractError(TopologyMutationError):
    """Raised by `validate_upstream_purity_contract()` at startup when
    `UPSTREAM_PURITY_REGISTRY` is missing an attestation for an upstream
    entry point Tier B requires, or the attested KB version does not
    match the runtime upstream KB version.

    Per § 0.1 — upstream purity is a precondition for atomicity-by-
    construction. A purity contract violation makes Tier B unsafe.
    """

    severity_tier: ClassVar[_SeverityTier] = "systemic"


class PendingUpstreamPredicateError(TopologyMutationError):
    """Raised by Phase 0 startup validation when:

    1. A predicate has `pending_upstream=True` and `expires_at_version
       is None` (no sunset declared), OR
    2. The current C11a version >= predicate's `expires_at_version`
       AND the predicate is still marked pending (sunset hard-fail), OR
    3. The Inv 24 LOCK gate fails:
       `pending_upstream_count - len(active_waivers) != 0` OR
       `len(active_waivers) > 3`.

    Per § 0.2 — sunset enforcement preserves architectural integrity
    of the predicate ecosystem.
    """

    severity_tier: ClassVar[_SeverityTier] = "systemic"


class SeverityClassificationAuditError(TopologyMutationError):
    """NEW v0.5 (F-v4-5 / critique #6).

    Raised by `validate_severity_classification_audit()` at startup
    when an upstream exception type referenced by Tier B has no valid
    `severity_tier` ClassVar — i.e., the dependency graph contains an
    error class that would route to the defensive "unknown" → systemic
    fallback in § 2.7's catch logic.

    Fails closed: an unclassified error means C11a can't reason about
    its severity, and treating it as systemic is conservative but
    blocks startup so the missing classification is fixed at source.
    """

    severity_tier: ClassVar[_SeverityTier] = "systemic"


class InvariantViolationError(TopologyMutationError):
    """Raised when a numbered C11a invariant is violated at runtime —
    indicates a programmer error or upstream contract breach that bypassed
    the schema/registry validation.

    Systemic — invariant violations are unrecoverable; the batch
    cannot continue safely.
    """

    severity_tier: ClassVar[_SeverityTier] = "systemic"


__all__ = [
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
