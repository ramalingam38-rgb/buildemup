"""
BuildemUp Component 16 — Dual-Drawing Renderer
================================================

Sub-1 (S49) shipped: foundational layer (6 files / ~1,950 LOC / 250+ tests).

Files:
    versioning.py   — pinned constants for the LOCK baseline
    errors.py       — two-tier error hierarchy
    contracts.py    — upstream contract types + enums
    config.py       — RenderingConfig + CoordinateBoundsPolicy (R31a)
    cache_keys.py   — canonical hashing + dual signatures (R7c, R32)
    schema.py       — DualDrawingBundle + R19–R34 enforcement

NOT YET SHIPPED (subsequent sub-sessions):
    Phase α — Geometric envelope assembly
    Phase β — Door & window scheduling
    Phase γ — Working drawing assembly
    Phase δ — Permit drawing assembly
    Phase ε — Compliance attestation packaging
    Phase ζ — Bundle assembly + signature stamping
    orchestrator.py — render_drawings + render_drawings_batch public API
    PBT layer ≥ 15 — per v0.1 § 7 (B-C16-PBT-LAYER-COVERAGE)
    5-scenario adversarial corpus — per v0.1 § 7
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
]
