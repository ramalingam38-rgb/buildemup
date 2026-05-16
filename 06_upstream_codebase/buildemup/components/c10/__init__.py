"""
BuildemUp† — Component 10 (Wet-Zone Stack Planner) — package init.

Per C10 SPEC v1.0 LOCKED. Public entry point: ``plan_wet_zones(...)``.

Public schema, errors, and configuration types are re-exported here so that
downstream consumers (C11/C12/C14) and test fixtures import from a single
canonical location.

†= placeholder name marker.
"""
from buildemup.components.c10.errors import (
    BatchWetZoneInfeasibleError,
    ClusterIntegrityError,
    KBVersionMismatchError,
    PerCandidateError,
    PlumbingConfidenceTooLow,
    PoojaAdjacencyError,
    PreClusteringInfeasibleError,
    RemediationGraphError,
    RiserCountExceededError,
    TrapArmDistanceExceededError,
    WallCapacityExceededError,
    WetZoneInfeasibleError,
    WetZonePlanError,
)
from buildemup.components.c10.kb_validator import (
    get_fixture_types_for,
    get_plumbing_minimum_for,
    load_plumbing_fixture_profiles,
    load_plumbing_minimums,
    validate_plumbing_kbs_compatibility,
)
from buildemup.components.c10.provenance import (
    compute_risk_level,
    validate_remediation_graph,
)
from buildemup.components.c10.schema import (
    EPSILON,
    LIKELY_BOUND_FACTORS_BY_FIXTURE,
    SERIALIZATION_PRECISION,
    EnforcementMode,
    ForcedCultureOverride,
    PlacementRiskLevel,
    RemediationHint,
    RiserAnchor,
    RiserGroup,
    TrapArmEstimate,
    TruncationReason,
    WallScoreVector,
    WetZoneCapacityWeights,
    WetZonePerformanceBudgets,
    WetZonePlan,
    WetZonePlanConfig,
    WetZonePlanProvenance,
    WetZonePlannedCandidate,
    WetZoneRiskBreakdown,
    WetZoneScoringWeights,
    compute_scoring_weights_hash,
)
from buildemup.components.c10.wet_zone_planner import plan_wet_zones


__all__ = [
    # Public entry
    "plan_wet_zones",
    # Constants
    "EPSILON",
    "SERIALIZATION_PRECISION",
    "LIKELY_BOUND_FACTORS_BY_FIXTURE",
    # Enums
    "EnforcementMode",
    "PlacementRiskLevel",
    "TruncationReason",
    # Primitive dataclasses
    "TrapArmEstimate",
    "RemediationHint",
    "ForcedCultureOverride",
    "WallScoreVector",
    "RiserAnchor",
    "RiserGroup",
    "WetZoneRiskBreakdown",
    "WetZonePerformanceBudgets",
    # Weights / config
    "WetZoneCapacityWeights",
    "WetZoneScoringWeights",
    "WetZonePlanConfig",
    "compute_scoring_weights_hash",
    # Plan + provenance + envelope
    "WetZonePlan",
    "WetZonePlanProvenance",
    "WetZonePlannedCandidate",
    # Errors
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
    # KB validator
    "validate_plumbing_kbs_compatibility",
    "load_plumbing_minimums",
    "load_plumbing_fixture_profiles",
    "get_plumbing_minimum_for",
    "get_fixture_types_for",
    # Phase-5 helpers
    "validate_remediation_graph",
    "compute_risk_level",
]
