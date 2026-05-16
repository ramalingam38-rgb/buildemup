"""
BuildemUp — Component 11b — public surface
============================================

Per Ramalingam's S42 directive: the ``__init__.py`` re-exports the
public surface so consumers import from ``buildemup.components.c11b``
rather than from internal module paths. File granularity stays an
implementation detail; the v1.1 LOCKED contract is the surface.

Public surface (the *only* names consumers should import):

- ``run_local_refinement``, ``run_local_refinement_with_provenance``,
  ``RefinementBatchResult`` — top-level entry points.
- ``LocalRefinementConfig``, ``EnforcementMode``, ``ProvenanceVerbosity``,
  ``StagnationConfig``, ``DominanceSorterProtocol`` — config surface.
- ``StubEvaluator``, ``StubEvaluatorConfig``, ``EvaluatorProtocol`` —
  evaluator surface.
- ``RefinedCandidate``, ``RefinedParameters``, ``RoomDimension``,
  ``ObjectiveVector``, ``OperatorClass`` — schema surface.
- ``LocalRefinementProvenance``, ``PerTopologyTelemetry``,
  ``EnvironmentFingerprint``, ``capture_environment_fingerprint`` —
  provenance surface.
- Failure-mode types (full hierarchy from ``errors``).
- Version constants ``C11B_VERSION``, ``TIEBREAK_FINGERPRINT_SCHEMA_VERSION``,
  ``SEMVER_POLICY_VERSION``.
"""
from __future__ import annotations

from buildemup.components.c11b.config import (
    DominanceSorterProtocol,
    EnforcementMode,
    LocalRefinementConfig,
    ProvenanceVerbosity,
    StagnationConfig,
    cache_irrelevant_field_names,
    cache_relevant_field_names,
)
from buildemup.components.c11b.environment_fingerprint import (
    EnvironmentFingerprint,
    capture_environment_fingerprint,
)
from buildemup.components.c11b.errors import (
    AreaInfeasiblePopulationError,
    BatchAllTopologiesFailedError,
    EnvironmentFingerprintMismatchError,
    EvaluatorContractError,
    EvaluatorPurityContractError,
    InvariantViolationError,
    LocalRefinementError,
    MultiFloorRefinementNotSupportedError,
    NSGAConvergenceError,
    PerTopologyError,
    PerTopologyTimeoutError,
)
from buildemup.components.c11b.evaluator import (
    EvaluatorProtocol,
    StubEvaluator,
    StubEvaluatorConfig,
)
from buildemup.components.c11b.orchestrator import (
    RefinementBatchResult,
    run_local_refinement,
    run_local_refinement_with_provenance,
)
from buildemup.components.c11b.provenance import LocalRefinementProvenance
from buildemup.components.c11b.schema import (
    ObjectiveVector,
    OperatorClass,
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
)
from buildemup.components.c11b.telemetry import PerTopologyTelemetry
from buildemup.components.c11b.versioning import (
    C11B_VERSION,
    SEMVER_POLICY_VERSION,
    TIEBREAK_FINGERPRINT_SCHEMA_VERSION,
)


__all__ = [
    # Entry points
    "run_local_refinement",
    "run_local_refinement_with_provenance",
    "RefinementBatchResult",
    # Config
    "LocalRefinementConfig",
    "EnforcementMode",
    "ProvenanceVerbosity",
    "StagnationConfig",
    "DominanceSorterProtocol",
    "cache_relevant_field_names",
    "cache_irrelevant_field_names",
    # Evaluator
    "EvaluatorProtocol",
    "StubEvaluator",
    "StubEvaluatorConfig",
    # Schema
    "RefinedCandidate",
    "RefinedParameters",
    "RoomDimension",
    "ObjectiveVector",
    "OperatorClass",
    # Provenance
    "LocalRefinementProvenance",
    "PerTopologyTelemetry",
    "EnvironmentFingerprint",
    "capture_environment_fingerprint",
    # Errors
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
    # Version constants
    "C11B_VERSION",
    "TIEBREAK_FINGERPRINT_SCHEMA_VERSION",
    "SEMVER_POLICY_VERSION",
]
