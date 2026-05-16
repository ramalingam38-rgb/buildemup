"""
BuildemUp† — Component 10 (Wet-Zone Stack Planner) — Errors module.

Per C10 SPEC v1.0 LOCKED § 5 (Failure modes).

Exception hierarchy:

    WetZonePlanError [carries remediation_hints + failure_phase]
    ├── PerCandidateError
    │   ├── WetZoneInfeasibleError (consolidated)
    │   │   └── PreClusteringInfeasibleError
    │   │       (failure_phase ∈ {"pre_clustering",
    │   │                          "post_clustering_spatial",
    │   │                          "assignment"})
    │   ├── PoojaAdjacencyError
    │   ├── RiserCountExceededError
    │   ├── TrapArmDistanceExceededError
    │   ├── WallCapacityExceededError
    │   └── ClusterIntegrityError
    ├── BatchWetZoneInfeasibleError
    ├── PlumbingConfidenceTooLow                 (systemic)
    ├── KBVersionMismatchError                   (startup-time)
    └── RemediationGraphError                    (systemic Phase 5 mutex graph)

The PerCandidateError subclasses are aggregated by the orchestrator under the
partial-batch tolerance rule (mirrors C9 § 14.40). Systemic errors
(PlumbingConfidenceTooLow, KBVersionMismatchError, RemediationGraphError)
short-circuit the entire batch.

†= placeholder name marker.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal

if TYPE_CHECKING:
    from buildemup.components.c10.schema import RemediationHint


# B-NEW-P (S38) — error severity classification, required by C11a v1.0 § 2.7.
# Each error class declares its severity_tier ClassVar so C11a's
# DeepMutationPipeline can route exceptions via inversion-of-control rather
# than hardcoded type lists. Tiers:
#   "per_candidate" — candidate-scoped; aggregate via partial-batch tolerance
#   "batch"         — whole-batch failure
#   "systemic"      — halt; unrecoverable
# Inheritance carries the tier; subclasses override only when the semantic
# class differs from the parent.
_SeverityTier = Literal["per_candidate", "batch", "systemic"]


# =============================================================================
# Base
# =============================================================================


class WetZonePlanError(Exception):
    """Base class for all C10 errors. Never raised directly.

    Carries `remediation_hints` (tuple of RemediationHint) for orchestration
    and `failure_phase` (Literal value) when the error is per-candidate.
    Systemic errors don't carry `failure_phase` (per F-v9-3).
    """

    # B-NEW-P (S38): per-candidate is the conservative default for the base
    # class. Subclasses override to "batch" or "systemic" as appropriate.
    severity_tier: ClassVar[_SeverityTier] = "per_candidate"

    def __init__(
        self,
        message: str,
        *,
        remediation_hints: "tuple[RemediationHint, ...]" = (),
        failure_phase: str | None = None,
    ) -> None:
        super().__init__(message)
        self.remediation_hints = remediation_hints
        self.failure_phase = failure_phase


# =============================================================================
# Per-candidate errors (aggregated by orchestrator)
# =============================================================================


class PerCandidateError(WetZonePlanError):
    """Per-candidate failures; aggregated by orchestrator. Never raised
    directly — concrete subclasses below are the user-visible types."""


class WetZoneInfeasibleError(PerCandidateError):
    """Consolidated infeasibility error for pre-clustering, post-clustering
    spatial, and assignment phase failures.

    `failure_phase` distinguishes:
      - "pre_clustering"          — Phase 0.5 fast-fail HARD-edge incompat
      - "post_clustering_spatial" — Phase 2.5 cluster-occupancy infeasibility
      - "assignment"              — Phase 3 wall-assignment exhausted
    """


class PreClusteringInfeasibleError(WetZoneInfeasibleError):
    """Subclass for pre-clustering infeasibility. Carries failure_phase
    ∈ {"pre_clustering", "post_clustering_spatial"}. Distinct subclass
    so callers can catch this specifically while still matching the
    parent WetZoneInfeasibleError."""


class PoojaAdjacencyError(PerCandidateError):
    """POOJA placed adjacent to wet wall under strict mode (Inv 6)."""


class RiserCountExceededError(PerCandidateError):
    """Riser count > effective_max_risers (Inv 8 STRICT)."""


class TrapArmDistanceExceededError(PerCandidateError):
    """Trap-arm distance exceeded for a fixture (Inv 11 dual-bound RAISE)."""


class WallCapacityExceededError(PerCandidateError):
    """Cluster capacity weight > wall capacity (Inv 17 — Q36 interim DFU)."""


class ClusterIntegrityError(PerCandidateError):
    """Cluster invariants violated (Inv 13/14)."""


# =============================================================================
# Batch errors
# =============================================================================


class BatchWetZoneInfeasibleError(WetZonePlanError):
    """Raised when ALL candidates failed per-candidate. Carries the per-
    candidate errors as `.candidate_errors` for diagnosis."""

    severity_tier: ClassVar[_SeverityTier] = "batch"  # B-NEW-P (S38)

    def __init__(
        self,
        message: str,
        *,
        candidate_errors: "tuple[PerCandidateError, ...]" = (),
    ) -> None:
        super().__init__(message)
        self.candidate_errors = candidate_errors


# =============================================================================
# Systemic errors
# =============================================================================


class PlumbingConfidenceTooLow(WetZonePlanError):
    """Raised when require_verified_plumbing=True and at least one
    plan path used a plumbing KB row with secondary_unverified
    source_confidence."""

    severity_tier: ClassVar[_SeverityTier] = "systemic"  # B-NEW-P (S38)


class KBVersionMismatchError(WetZonePlanError):
    """Raised at startup when the plumbing minimums and fixture profiles
    KBs are incompatible (version drift, orphan fixture types, or semantic
    integrity violation)."""

    severity_tier: ClassVar[_SeverityTier] = "systemic"  # B-NEW-P (S38)


class RemediationGraphError(WetZonePlanError):
    """Raised in Phase 5 when the RemediationHint mutex graph contains
    cycles or other invariants of Inv 21 are violated. Systemic — indicates
    a C10 implementation bug, not a per-candidate input issue."""

    severity_tier: ClassVar[_SeverityTier] = "systemic"  # B-NEW-P (S38)


__all__ = [
    "WetZonePlanError",
    "PerCandidateError",
    "WetZoneInfeasibleError",
    "PreClusteringInfeasibleError",
    "PoojaAdjacencyError",
    "RiserCountExceededError",
    "TrapArmDistanceExceededError",
    "WallCapacityExceededError",
    "ClusterIntegrityError",
    "BatchWetZoneInfeasibleError",
    "PlumbingConfidenceTooLow",
    "KBVersionMismatchError",
    "RemediationGraphError",
]
