"""
BuildemUp — Component 11b — failure modes
===========================================

Per SPEC v1.1 LOCKED § 5 (Failure modes, REVISED v0.4):

::

    LocalRefinementError (base)
    ├── PerTopologyError
    │   ├── NSGAConvergenceError
    │   ├── AreaInfeasiblePopulationError
    │   ├── EvaluatorContractError
    │   ├── MultiFloorRefinementNotSupportedError    (NEW v0.4)
    │   └── PerTopologyTimeoutError                  (NEW v0.4)
    ├── BatchAllTopologiesFailedError
    ├── EvaluatorPurityContractError
    ├── EnvironmentFingerprintMismatchError
    └── InvariantViolationError                       (systemic)
"""
from __future__ import annotations

from typing import ClassVar, Literal


# =============================================================================
# Base — every C11b error is rooted here
# =============================================================================


class LocalRefinementError(Exception):
    """Base for all C11b runtime failures."""

    severity_tier: ClassVar[Literal["per_candidate", "per_topology", "systemic"]] = (
        "systemic"
    )


# =============================================================================
# Per-topology failure mode (one topology halts; batch may continue under WARN)
# =============================================================================


class PerTopologyError(LocalRefinementError):
    """A single topology failed; batch continues under WARN mode,
    halts under STRICT mode."""

    severity_tier: ClassVar[Literal["per_candidate", "per_topology", "systemic"]] = (
        "per_topology"
    )


class NSGAConvergenceError(PerTopologyError):
    """NSGA-II loop hit ``max_generations`` without stagnation
    detection firing (rare; usually indicates a degenerate evaluator
    or pathological initial population)."""


class AreaInfeasiblePopulationError(PerTopologyError):
    """Initialization could not produce a feasible population within
    ``init_max_retries * permutations_per_candidate`` attempts (per
    spec § 0.7).

    Renamed from v0.2 ``InfeasiblePopulationError`` per § 0.2
    terminology rule: 'area-feasible' is sum-of-areas, NOT geometric
    embeddability (which is C12's job)."""


class EvaluatorContractError(PerTopologyError):
    """The evaluator violated its contract. Two variants:

    1. **Per-candidate** (the evaluator raises this for one candidate
       — the candidate is malformed for the evaluator's contract).
       Caught and counted toward the skip cap (Inv 28); the
       candidate is dropped and the generation continues at reduced
       population.

    2. **Systemic** (skip cap exceeded OR the evaluator raised a
       non-contract exception type). Halts the topology with this
       error wrapping the cause.

    Per spec § 0.6 (D-EV-1, D-EV-2) + Inv 28 cap."""


class MultiFloorRefinementNotSupportedError(PerTopologyError):
    """**NEW v0.4 (D-MF-1).** Raised when a ``MutatedTopologyCandidate``
    resolves to a real ``MultiFloorWetZonePlannedCandidate`` artifact
    — v1 of C11b does not support multi-floor refinement.

    The reject occurs IMMEDIATELY after artifact resolution per spec
    § 3 Phase 1 step 2 (W5-9 ordering), BEFORE any signature
    derivation, PRNG setup, or evaluator work happens.

    Filed for future expansion: ``B-C11B-MF`` (multi-floor refinement
    scope expansion, deferred until C12 multi-floor placement OR C14
    multi-floor scoring lands)."""


class PerTopologyTimeoutError(PerTopologyError):
    """**NEW v0.4 (D-TO-2).** Raised at a generation boundary when
    wall-clock elapsed exceeds ``per_topology_wallclock_seconds``
    (default 30.0s, cache_relevant=True per v0.5 W4-5).

    Per Inv 27. Out of scope at v1: per-evaluation timeout,
    intra-generation watchdog. Filed as ``B-C11B-TIMEOUT-V2``."""


# =============================================================================
# Batch-level and systemic failures
# =============================================================================


class BatchAllTopologiesFailedError(LocalRefinementError):
    """Every topology in the batch failed (each by some
    ``PerTopologyError`` subtype). Under WARN mode this is the only
    batch-halt path; under STRICT mode any per-topology error halts
    the batch."""


class EvaluatorPurityContractError(LocalRefinementError):
    """The evaluator returned different ``ObjectiveVector``s for the
    same ``RefinedCandidate`` across calls. Pure-function contract
    violation; halts the batch (cannot trust the cache or sort)."""


class EnvironmentFingerprintMismatchError(LocalRefinementError):
    """At Phase 0, the captured ``EnvironmentFingerprint`` does not
    match an expected value passed in for replay. Halts immediately;
    indicates the runtime environment changed (numpy version, BLAS,
    ``c11b_version``, ``tiebreak_fingerprint_schema_version``).

    Per Inv 24 (carried v1.0) + Inv 29 (v0.4-v0.7 evolution)."""


class InvariantViolationError(LocalRefinementError):
    """A runtime invariant check failed. Always systemic — invariant
    violations indicate a programming bug, not user-data malformation.

    Notable callers:
    - ``RefinedCandidate.__post_init__`` per W6-1: 3-flag equality
      violated → raise this error (HARD assertion, not test-only).
    - ``_resolve_input_artifact`` for ``len(application_results) != 1``
      (Inv 26 audit-tier contract).
    """


__all__ = [
    "LocalRefinementError",
    "PerTopologyError",
    "NSGAConvergenceError",
    "AreaInfeasiblePopulationError",
    "EvaluatorContractError",
    "MultiFloorRefinementNotSupportedError",
    "PerTopologyTimeoutError",
    "BatchAllTopologiesFailedError",
    "EvaluatorPurityContractError",
    "EnvironmentFingerprintMismatchError",
    "InvariantViolationError",
]
