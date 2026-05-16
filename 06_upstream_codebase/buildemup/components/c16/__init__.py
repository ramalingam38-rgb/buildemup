"""
BuildemUp Component 16 — Dual-Drawing Renderer
================================================

Sub-1 (S49) shipped: foundational layer (6 files / ~1,950 LOC / 250+ tests).
Sub-2 (S49) shipped: full phase pipeline α → β → γ → δ → ε → ζ + orchestrator.

Foundational files:
    versioning.py   — pinned constants for the LOCK baseline
    errors.py       — two-tier error hierarchy
    contracts.py    — upstream contract types + enums
    config.py       — RenderingConfig + CoordinateBoundsPolicy (R31a)
    cache_keys.py   — canonical hashing + dual signatures (R7c, R32)
    schema.py       — DualDrawingBundle + R19–R34 enforcement
    upstream_adapter.py — UpstreamInputBundle + unit conversions (R7a)
    orientation.py  — R29 4-step hierarchy + R29d plausibility

Phase pipeline (phases/):
    alpha_envelope.py    — Phase α — geometric envelope assembly
    beta_scheduling.py   — Phase β — door / window / finish scheduling
    gamma_working.py     — Phase γ — working drawing + R23 section cuts
    delta_permit.py      — Phase δ — permit drawing + permit-critical overlays
    epsilon_attestation.py — Phase ε — ComplianceAttestation packaging (R25)
    zeta_bundle.py       — Phase ζ — bundle + signature stamping (R32a/R26b)

orchestrator.py — render_drawings + render_drawings_batch public API.
"""

from buildemup.components.c16.versioning import (
    C16_DRAWING_SCHEMA_VERSION,
    C16_IDENTITY_GENERATION,
    C16_VERSION,
    EPSILON_ANGLE_DEG,
    EPSILON_COORD_MM,
    EPSILON_RATIO,
    EXPECTED_C7_VERSION,
    EXPECTED_C9_VERSION,
    EXPECTED_C10_VERSION,
    EXPECTED_C12_VERSION,
    EXPECTED_C13_VERSION,
    EXPECTED_C14_VERSION,
    EXPECTED_C15_VERSION,
    HARD_CEILING_BUILDING_X_MM,
    HARD_CEILING_BUILDING_Y_MM,
    HARD_CEILING_BUILDING_Z_MAX_MM,
    HARD_CEILING_BUILDING_Z_MIN_MM,
    HARD_CEILING_LOCAL_FRAME_X_MAX_MM,
    HARD_CEILING_LOCAL_FRAME_X_MIN_MM,
    HARD_CEILING_LOCAL_FRAME_Y_MAX_MM,
    HARD_CEILING_LOCAL_FRAME_Y_MIN_MM,
    HARD_CEILING_PLOT_X_MM,
    HARD_CEILING_PLOT_Y_MM,
    ORIENTATION_BASIS_VALUES,
    SUPPORTED_DOMAIN_SCOPES,
    SUPPORTED_JURISDICTIONS,
    version_summary,
    version_triple,
)

from buildemup.components.c16.errors import (
    C16ConfigurationError,
    ComplianceProvenanceError,
    DrawingRenderError,
    GeometryInconsistencyError,
    JurisdictionNotSupportedError,
    LocalDrawingError,
    MissingUpstreamDataError,
    OrientationLockMismatchError,
    PerLayoutDrawingError,
    UpstreamSchemaDriftError,
)

from buildemup.components.c16.contracts import (
    AttestedValue,
    AuthorityKind,
    CandidateRanking,
    CheckProvenance,
    ElementKind,
    GeospatialReference,
    HumanOverrideRecord,
    JurisdictionProfile,
    LegalCompleteness,
    LocalBuildingFrame,
    OrientationLock,
    ReadabilityStatus,
    SelectionAuditMetadata,
    SelectionReason,
    SelectionReplayIdentity,
    SelectionResult,
)

from buildemup.components.c16.config import (
    CoordinateBoundsPolicy,
    RenderingConfig,
    effective_building_bounds,
    effective_plot_bounds,
)

from buildemup.components.c16.cache_keys import (
    C16CacheKeys,
    canonical_json,
    canonical_replay_signature,
    canonicalize_value,
    config_signature_for,
    derive_c16_cache_keys,
    presentation_signature,
    sha256_hex,
)

from buildemup.components.c16.schema import (
    INT64_MAX,
    INT64_MIN,
    PERMIT_CRITICAL_OVERLAY_NAMES,
    AdvisoryFlag,
    CanonicalTransform2D,
    ColumnGeometry,
    ComplianceAttestation,
    ComplianceMarker,
    DoorGeometry,
    DoorScheduleEntry,
    DrawingRenderBatchResult,
    DualDrawingBundle,
    Elevation,
    ElementIdentity,
    FailedDrawingRender,
    FailureRecord,
    FinishScheduleEntry,
    FloorGeometry,
    KeyPlan,
    ParkingComplianceReport,
    ParkingProvision,
    PermitDrawingFloor,
    PermitDrawingModel,
    PhaseTimings,
    PlumbingStack,
    RainWaterHarvestingOverlay,
    ReadabilityDiagnostics,
    RoofPlan,
    RoomGeometry,
    SchemaDescriptor,
    SectionView,
    SetbackAnnotation,
    SetbackComplianceReport,
    SetbackDimensions,
    SewageLayoutOverlay,
    SignaturePlaceholder,
    SitePlan,
    SuccessfulDrawingRender,
    SuppressedAnnotation,
    TransformOverflowError,
    WallSegment,
    WindowGeometry,
    WindowScheduleEntry,
    WorkingAnnotation,
    WorkingDrawingFloor,
    WorkingDrawingModel,
    compute_element_identity,
    compute_schema_descriptor_digest,
)
from buildemup.components.c16.upstream_adapter import (
    UpstreamInputBundle,
    m_to_mm,
    sorted_by_floor_label,
    floor_label_to_level,
)
from buildemup.components.c16.orientation import (
    OrientationDecision,
    WallCandidate,
    all_hierarchy_candidates,
    compute_orientation,
    validate_orientation_lock,
)
from buildemup.components.c16.phases.alpha_envelope import (
    EnvelopeAssembly,
    execute_phase_alpha,
)
from buildemup.components.c16.phases.beta_scheduling import (
    FloorSchedules,
    SchedulingResult,
    execute_phase_beta,
)
from buildemup.components.c16.phases.gamma_working import execute_phase_gamma
from buildemup.components.c16.phases.delta_permit import execute_phase_delta
from buildemup.components.c16.phases.epsilon_attestation import (
    execute_phase_epsilon,
)
from buildemup.components.c16.phases.zeta_bundle import execute_phase_zeta
from buildemup.components.c16.orchestrator import (
    render_drawings,
    render_drawings_batch,
)


__all__ = [
    # versioning
    "C16_VERSION", "C16_DRAWING_SCHEMA_VERSION", "C16_IDENTITY_GENERATION",
    "EPSILON_ANGLE_DEG", "EPSILON_COORD_MM", "EPSILON_RATIO",
    "EXPECTED_C7_VERSION", "EXPECTED_C9_VERSION", "EXPECTED_C10_VERSION",
    "EXPECTED_C12_VERSION", "EXPECTED_C13_VERSION", "EXPECTED_C14_VERSION",
    "EXPECTED_C15_VERSION",
    "HARD_CEILING_BUILDING_X_MM", "HARD_CEILING_BUILDING_Y_MM",
    "HARD_CEILING_BUILDING_Z_MAX_MM", "HARD_CEILING_BUILDING_Z_MIN_MM",
    "HARD_CEILING_LOCAL_FRAME_X_MAX_MM", "HARD_CEILING_LOCAL_FRAME_X_MIN_MM",
    "HARD_CEILING_LOCAL_FRAME_Y_MAX_MM", "HARD_CEILING_LOCAL_FRAME_Y_MIN_MM",
    "HARD_CEILING_PLOT_X_MM", "HARD_CEILING_PLOT_Y_MM",
    "ORIENTATION_BASIS_VALUES", "SUPPORTED_DOMAIN_SCOPES",
    "SUPPORTED_JURISDICTIONS", "version_summary", "version_triple",
    # errors
    "C16ConfigurationError", "ComplianceProvenanceError", "DrawingRenderError",
    "GeometryInconsistencyError", "JurisdictionNotSupportedError",
    "LocalDrawingError", "MissingUpstreamDataError",
    "OrientationLockMismatchError", "PerLayoutDrawingError",
    "UpstreamSchemaDriftError", "TransformOverflowError",
    # contracts
    "AttestedValue", "AuthorityKind", "CandidateRanking", "CheckProvenance",
    "ElementKind", "GeospatialReference", "HumanOverrideRecord",
    "JurisdictionProfile", "LegalCompleteness", "LocalBuildingFrame",
    "OrientationLock", "ReadabilityStatus", "SelectionAuditMetadata",
    "SelectionReason", "SelectionReplayIdentity", "SelectionResult",
    # config
    "CoordinateBoundsPolicy", "RenderingConfig",
    "effective_building_bounds", "effective_plot_bounds",
    # cache_keys
    "C16CacheKeys", "canonical_json", "canonical_replay_signature",
    "canonicalize_value", "config_signature_for", "derive_c16_cache_keys",
    "presentation_signature", "sha256_hex",
    # schema
    "INT64_MAX", "INT64_MIN", "PERMIT_CRITICAL_OVERLAY_NAMES",
    "AdvisoryFlag", "CanonicalTransform2D", "ColumnGeometry",
    "ComplianceAttestation", "ComplianceMarker", "DoorGeometry",
    "DoorScheduleEntry", "DrawingRenderBatchResult", "DualDrawingBundle",
    "Elevation", "ElementIdentity", "FailedDrawingRender", "FailureRecord",
    "FinishScheduleEntry", "FloorGeometry", "KeyPlan",
    "ParkingComplianceReport", "ParkingProvision", "PermitDrawingFloor",
    "PermitDrawingModel", "PhaseTimings", "PlumbingStack",
    "RainWaterHarvestingOverlay", "ReadabilityDiagnostics", "RoofPlan",
    "RoomGeometry", "SchemaDescriptor", "SectionView", "SetbackAnnotation",
    "SetbackComplianceReport", "SetbackDimensions", "SewageLayoutOverlay",
    "SignaturePlaceholder", "SitePlan", "SuccessfulDrawingRender",
    "SuppressedAnnotation", "WallSegment", "WindowGeometry",
    "WindowScheduleEntry", "WorkingAnnotation", "WorkingDrawingFloor",
    "WorkingDrawingModel", "compute_element_identity",
    "compute_schema_descriptor_digest",
    # upstream_adapter
    "UpstreamInputBundle", "m_to_mm", "sorted_by_floor_label",
    "floor_label_to_level",
    # orientation
    "OrientationDecision", "WallCandidate", "all_hierarchy_candidates",
    "compute_orientation", "validate_orientation_lock",
    # phases
    "EnvelopeAssembly", "execute_phase_alpha",
    "FloorSchedules", "SchedulingResult", "execute_phase_beta",
    "execute_phase_gamma", "execute_phase_delta",
    "execute_phase_epsilon", "execute_phase_zeta",
    # orchestrator (public API)
    "render_drawings", "render_drawings_batch",
]
