"""
BuildemUp — Component 12 — error / failure hierarchy
=====================================================

Per C12 SPEC v1.0 LOCKED § 4 — 11 failure types.

The hierarchy distinguishes:
- PerCandidatePlacementError: per-candidate failures (placement
  failed for this candidate; other candidates may succeed).
- LocalPlacementError: orchestrator-level errors that may halt
  the batch (e.g., schema drift, configuration invalid).

STRICT vs WARN mode behavior:
- Under STRICT: PerCandidatePlacementError raises immediately.
- Under WARN: PerCandidatePlacementError is recorded in
  PlacementBatchResult.failures and the candidate is skipped;
  the batch continues.

LocalPlacementError always raises regardless of mode.
"""
from __future__ import annotations


# =============================================================================
# Base classes
# =============================================================================

class PlacementError(Exception):
    """Base of all C12 errors."""


class LocalPlacementError(PlacementError):
    """Orchestrator-level errors that halt the batch.

    These represent issues with the configuration, the upstream
    contract, or the C12 runtime itself — not with individual
    candidates.
    """


class PerCandidatePlacementError(PlacementError):
    """Per-candidate placement failures.

    Under STRICT mode: raised immediately, halting the batch.
    Under WARN mode: caught by the orchestrator, recorded in
    PlacementBatchResult.failures, and the candidate is skipped.
    """


# =============================================================================
# Local (orchestrator-level) errors
# =============================================================================

class UpstreamSchemaDriftError(LocalPlacementError):
    """Per v0.4-A1: upstream component's schema version constant
    does not match what C12 was built against.

    Severity: systemic. Halts the batch immediately under any mode.
    Prevents silent cross-component contract drift.
    """


class C12ConfigurationError(LocalPlacementError):
    """Per § 2.3: PlacementConfig is malformed (negative tolerance,
    invalid retry budget, etc.). Validated at orchestrator entry."""


# =============================================================================
# Per-candidate errors
# =============================================================================

class GeometricInfeasibilityError(PerCandidatePlacementError):
    """The room set cannot fit inside the envelope per the
    placement algorithm. Raised by slicing-tree placement when
    no feasible partition exists."""


class CapabilityFlagInconsistencyError(PerCandidatePlacementError):
    """Per v0.2-A1: upstream RefinedCandidate has
    capability_mode == PREDICATE_ONLY (Tier A SHALLOW). C12 v1
    ships STRICT-MATERIALIZED-only; Tier A requires
    B-C12-TIER-A-RESOLVERS post-v1."""


class PlacementAlgorithmTimeoutError(PerCandidatePlacementError):
    """Per v0.3-A5: wallclock budget exceeded
    (per_candidate_wallclock_seconds default 10.0)."""


class CirculationInfeasibilityError(PerCandidatePlacementError):
    """Per v0.2-A6 Inv 11: reachability BFS over placed_rooms +
    corridor_zones determines one or more rooms cannot reach any
    entry point. Architecturally infeasible layout."""


class VerticalAlignmentError(PerCandidatePlacementError):
    """Per v0.2-A2: multi-floor alignment retries diverged
    (delta_n+1 >= delta_n: plateau or growth) OR exhausted the
    retry budget without convergence."""


class DoorwayFeasibilityError(PerCandidatePlacementError):
    """Per v0.2-A9 Inv 12: a HARD-adjacent room pair has no shared
    edge with doorway_feasible == True. Doorway-required adjacency
    is geometrically impossible."""


class AdjacencyConstraintViolationError(PerCandidatePlacementError):
    """Per v0.2-A5: a HARD adjacency hint cannot be satisfied by the
    placement (rooms not adjacent at all). Distinct from
    DoorwayFeasibilityError (adjacent but no fitting doorway)."""


# =============================================================================
# Public exports
# =============================================================================

__all__ = [
    # Bases
    "PlacementError",
    "LocalPlacementError",
    "PerCandidatePlacementError",
    # Local
    "UpstreamSchemaDriftError",
    "C12ConfigurationError",
    # Per-candidate
    "GeometricInfeasibilityError",
    "CapabilityFlagInconsistencyError",
    "PlacementAlgorithmTimeoutError",
    "CirculationInfeasibilityError",
    "VerticalAlignmentError",
    "DoorwayFeasibilityError",
    "AdjacencyConstraintViolationError",
]
