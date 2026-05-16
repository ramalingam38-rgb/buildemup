"""S55 Batch 4 — C16 LOCK-mandatory closures.

Pins the 18 LOCK-mandatory items (1 LOCK-BLOCKING + 17 non-blocking)
filed at C16 v0.5 LOCK + S47 critique walks 1-5. Each item gets a
documented decision with S55-pinned breadcrumbs. Full C16 v1.0 LOCK
requires architect+drafting-standard reviewer sign-off on these
baselines.

  v1.0-BLOCKING (1):
    B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK

  LOCK-mandatory non-blocking (17):
    B-C16-ENVELOPE-SCHEMA-LOCK
    B-C16-SELECTED-LAYOUT-CONTRACT-LOCK
    B-C16-SECTION-CUT-RULES-LOCK
    B-C16-RWH-SEWAGE-OVERLAY-DETAIL-LOCK
    B-C16-COMPLIANCE-PROVENANCE-FORMAT-LOCK
    B-C16-PARKING-PROVISION-SCHEMA-LOCK
    B-C16-PBT-LAYER-COVERAGE
    B-C16-REGRESSION-SNAPSHOT-CORPUS
    B-C16-COORDINATE-CONVENTION-IFC-COMPATIBILITY-VERIFICATION
    B-C16-SHARED-GEOMETRY-PARITY-CI-CHECK
    B-C16-SECTION-CUT-FALLBACK-CORPUS
    B-C16-SEMANTIC-IDENTITY-STABILITY-CI
    B-C16-DUAL-FRAME-COORDINATE-CONVERSION-AUDIT
    B-PROJECT-SELECTOR-CANONICALIZATION-CONTRACT-LOCK
    B-C16-V0.3-TO-V0.4-MIGRATION-AUDIT
    B-C16-EPSILON-POLICY-CI-CHECK
    B-C16-OVERLAY-VALIDATION-RULES-LOCK
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Tuple


C16_LOCK_VERSION: Final[str] = "v0.5.LOCKED+S55-contracts-pinned"


# ─────────────────────────────────────────────────────────────────────
# B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK (v1.0 BLOCKING)
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RendererConformanceContract:
    """Binds C16 outputs to IS 962:1967 drafting standards.

    Pinned at S55 baseline. Architect review may revise specific
    typography metrics or pen-weight assignments at C16 v1.0 LOCK.
    """
    text_height_mm_titles: float = 5.0           # IS 962 § 8.2
    text_height_mm_labels: float = 3.5
    text_height_mm_dimensions: float = 2.5
    text_height_mm_notes: float = 2.0
    sheet_size_default: str = "A1_landscape"     # IS 962 § 4.1
    sheet_size_options: tuple[str, ...] = (
        "A4_portrait", "A3_landscape", "A2_landscape", "A1_landscape",
    )
    pen_weight_mm_thick: float = 0.7             # IS 962 § 8.4
    pen_weight_mm_medium: float = 0.5
    pen_weight_mm_thin: float = 0.35
    pen_weight_mm_construction: float = 0.18
    title_block_height_mm: float = 65.0          # IS 962 § 4.5
    title_block_width_mm: float = 185.0
    font_family_primary: str = "ISOCPEUR"        # IS-compliant monospace
    font_metrics_normalized: bool = True         # deterministic text layout
    citation: str = "IS 962:1967 Code of practice for architectural and building drawings"


RENDERER_CONFORMANCE_CONTRACT: Final[RendererConformanceContract] = (
    RendererConformanceContract()
)


# ─────────────────────────────────────────────────────────────────────
# B-C16-ENVELOPE-SCHEMA-LOCK
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EnvelopeSchemaField:
    field_name: str
    type_name: str
    required: bool
    description: str


# FloorPlanWorking, FloorPlanPermit, SectionView, Elevation envelope
# field manifests. Each list is the LOCK-pinned shape for v1.0.

FLOOR_PLAN_WORKING_SCHEMA: Final[Tuple[EnvelopeSchemaField, ...]] = (
    EnvelopeSchemaField("plan_id", "str", True, "stable identifier"),
    EnvelopeSchemaField("floor_number", "int", True, "0=ground, ..."),
    EnvelopeSchemaField("rooms", "tuple[Room, ...]", True, "placed rooms"),
    EnvelopeSchemaField("walls", "tuple[Wall, ...]", True, "exterior+interior"),
    EnvelopeSchemaField("doors", "tuple[Door, ...]", True, "from C13"),
    EnvelopeSchemaField("windows", "tuple[Window, ...]", True, "post-window-engine"),
    EnvelopeSchemaField("dimensions", "tuple[Dimension, ...]", True, "running"),
    EnvelopeSchemaField("annotations", "tuple[Annotation, ...]", False, "designer marks"),
    EnvelopeSchemaField("title_block", "TitleBlock", True, "per IS 962"),
    EnvelopeSchemaField("sheet_size", "str", True, "from RendererConformanceContract"),
    EnvelopeSchemaField("provenance_trace_id", "str", True, "for replay"),
)

FLOOR_PLAN_PERMIT_SCHEMA: Final[Tuple[EnvelopeSchemaField, ...]] = (
    EnvelopeSchemaField("plan_id", "str", True, "stable identifier"),
    EnvelopeSchemaField("floor_number", "int", True, ""),
    EnvelopeSchemaField("rooms", "tuple[Room, ...]", True, "placed rooms"),
    EnvelopeSchemaField("setback_overlay", "SetbackOverlay", True, "TNCDBR compliance"),
    EnvelopeSchemaField("far_overlay", "FarOverlay", True, "TNCDBR compliance"),
    EnvelopeSchemaField("rwh_overlay", "RwhOverlay", True, "TNCDBR rule 9"),
    EnvelopeSchemaField("parking_overlay", "ParkingOverlay", True, "NBC + TNCDBR"),
    EnvelopeSchemaField("compliance_attestation", "ComplianceAttestation", True, "signed"),
    EnvelopeSchemaField("title_block_permit", "TitleBlock", True, "permit-spec"),
    EnvelopeSchemaField("approval_signatures_block", "tuple[Signature, ...]", True, ""),
)

SECTION_VIEW_SCHEMA: Final[Tuple[EnvelopeSchemaField, ...]] = (
    EnvelopeSchemaField("section_id", "str", True, ""),
    EnvelopeSchemaField("cut_origin_point_m", "tuple[float, float]", True, ""),
    EnvelopeSchemaField("cut_direction_vector", "tuple[float, float]", True, ""),
    EnvelopeSchemaField("sectioned_elements", "tuple[Element, ...]", True, ""),
    EnvelopeSchemaField("elevation_reference_lines", "tuple[ReferenceLine, ...]", True, ""),
    EnvelopeSchemaField("height_dimensions", "tuple[Dimension, ...]", True, ""),
)

ELEVATION_SCHEMA: Final[Tuple[EnvelopeSchemaField, ...]] = (
    EnvelopeSchemaField("elevation_id", "str", True, "e.g. 'north_elevation'"),
    EnvelopeSchemaField("facade_direction", "PlotOrientation", True, ""),
    EnvelopeSchemaField("window_openings", "tuple[Opening, ...]", True, ""),
    EnvelopeSchemaField("door_openings", "tuple[Opening, ...]", True, ""),
    EnvelopeSchemaField("material_legend", "tuple[MaterialEntry, ...]", True, ""),
    EnvelopeSchemaField("solar_overlay", "Optional[SolarOverlay]", False, "v1.x B-C16-ELEVATION-VIEW-SOLAR-ANNOTATIONS"),
)


# ─────────────────────────────────────────────────────────────────────
# B-C16-SELECTED-LAYOUT-CONTRACT-LOCK
# ─────────────────────────────────────────────────────────────────────


class SelectionResultState(str, Enum):
    """Typestate progression per v0.2 A1 + v0.3 A1 refinement."""
    PROPOSED = "proposed"          # C17/C14/C15 emitted, awaits selector
    UNDER_REVIEW = "under_review"  # selector evaluating
    SELECTED = "selected"          # selector committed
    LOCKED = "locked"              # C16 has committed to this selection
    SUPERSEDED = "superseded"      # later selection invalidated this


@dataclass(frozen=True)
class SelectedLayoutContract:
    """v1.0-LOCK shape of SelectionResult."""
    selection_id: str
    placed_candidate_signature: str    # links to C12 PlacedCandidate
    state: SelectionResultState
    selected_at_iso: str               # ISO 8601 UTC
    selector_identity: str             # which component made the selection


# ─────────────────────────────────────────────────────────────────────
# B-C16-SECTION-CUT-RULES-LOCK + B-C16-SECTION-CUT-FALLBACK-CORPUS
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SectionCutRule:
    rule_id: str
    cut_through: str            # "main_entry" | "staircase" | "wet_zone_cluster"
    is_mandatory: bool
    fallback_strategy: str


SECTION_CUT_RULES: Final[Tuple[SectionCutRule, ...]] = (
    SectionCutRule(
        rule_id="CUT-ENTRY",
        cut_through="main_entry",
        is_mandatory=True,
        fallback_strategy="snap_to_nearest_door_axis",
    ),
    SectionCutRule(
        rule_id="CUT-STAIRCASE",
        cut_through="staircase",
        is_mandatory=True,
        fallback_strategy="skip_if_single_floor",
    ),
    SectionCutRule(
        rule_id="CUT-WET-ZONE",
        cut_through="wet_zone_cluster",
        is_mandatory=True,
        fallback_strategy="snap_to_largest_wet_zone_centroid",
    ),
)

# B-C16-SECTION-CUT-FALLBACK-CORPUS: 10 irregular plot geometries
SECTION_CUT_FALLBACK_CORPUS_CASE_IDS: Final[Tuple[str, ...]] = (
    "FALLBACK-001-L-shape",
    "FALLBACK-002-trapezoidal",
    "FALLBACK-003-narrow-strip",
    "FALLBACK-004-courtyard-interior",
    "FALLBACK-005-staircase-mid-envelope",
    "FALLBACK-006-multiple-wet-zones",
    "FALLBACK-007-zero-windows-on-cut-axis",
    "FALLBACK-008-double-height-region",
    "FALLBACK-009-stilt-floor-skip",
    "FALLBACK-010-terrace-cut",
)


# ─────────────────────────────────────────────────────────────────────
# B-C16-RWH-SEWAGE-OVERLAY-DETAIL-LOCK
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RwhOverlayDetail:
    catchment_min_area_sqm: float = 100.0    # TNCDBR rule 9.1
    tank_min_volume_liters: int = 5000        # TNCDBR rule 9.3
    percolation_pit_required: bool = True
    citation: str = "TNCDBR 2019 § 7 + NBC 2016 Part 9 § 11"


@dataclass(frozen=True)
class SewageOverlayDetail:
    septic_min_distance_from_well_m: float = 15.0    # TNCDBR rule 8.4
    septic_min_distance_from_property_line_m: float = 1.5
    soak_pit_required: bool = True
    citation: str = "TNCDBR 2019 § 8 + IS 2470:1985"


RWH_OVERLAY_DETAIL: Final[RwhOverlayDetail] = RwhOverlayDetail()
SEWAGE_OVERLAY_DETAIL: Final[SewageOverlayDetail] = SewageOverlayDetail()


# ─────────────────────────────────────────────────────────────────────
# B-C16-COMPLIANCE-PROVENANCE-FORMAT-LOCK
# ─────────────────────────────────────────────────────────────────────


class AuthorityKind(str, Enum):
    """Per v0.2 A5."""
    NATIONAL_CODE = "national_code"          # NBC
    STATE_REGULATION = "state_regulation"    # TNCDBR / DCPR
    CITY_BYLAW = "city_bylaw"
    INDIAN_STANDARD = "indian_standard"      # IS codes
    INTERNATIONAL_STANDARD = "international_standard"  # ASHRAE / IEC


@dataclass(frozen=True)
class ComplianceProvenance:
    """v1.0 LOCK shape."""
    check_id: str
    authority_kind: AuthorityKind
    authority_citation: str
    authority_clause: str
    verified_at_iso: str
    verifier_identity: str       # 'automated' | 'architect_review'


# ─────────────────────────────────────────────────────────────────────
# B-C16-PARKING-PROVISION-SCHEMA-LOCK
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ParkingProvision:
    units_required: int
    units_provided: int
    parking_kind: str            # 'open' | 'covered' | 'stilt' | 'basement'
    citation_authority: AuthorityKind
    citation_clause: str

    def is_compliant(self) -> bool:
        return self.units_provided >= self.units_required


# ─────────────────────────────────────────────────────────────────────
# B-C16-PBT-LAYER-COVERAGE
# ─────────────────────────────────────────────────────────────────────

C16_PBT_COVERAGE_MANIFEST: Final[Tuple[str, ...]] = (
    "pbt_floor_plan_working_schema_complete",
    "pbt_floor_plan_permit_schema_complete",
    "pbt_section_view_schema_complete",
    "pbt_elevation_schema_complete",
    "pbt_selection_typestate_monotonic",
    "pbt_section_cut_rules_cover_all_floors",
    "pbt_section_cut_fallback_corpus_all_succeed",
    "pbt_rwh_overlay_compliant_when_plot_area_above_threshold",
    "pbt_sewage_distances_canonical",
    "pbt_compliance_provenance_authority_kind_enum",
    "pbt_parking_compliant_when_units_provided_ge_required",
    "pbt_semantic_identity_stable_under_harmless_additions",
    "pbt_dual_frame_round_trip_within_1mm",
    "pbt_epsilon_policy_no_raw_float_comparisons",
    "pbt_renderer_text_height_matches_IS_962",
)


# ─────────────────────────────────────────────────────────────────────
# B-C16-REGRESSION-SNAPSHOT-CORPUS
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RegressionSnapshotEntry:
    case_id: str
    description: str
    expected_canonical_replay_signature: str   # populated as fixtures land


C16_REGRESSION_SNAPSHOT_CORPUS: Final[Tuple[RegressionSnapshotEntry, ...]] = (
    RegressionSnapshotEntry("SNAP-001-30x40-chennai-2bhk", "Standard 2BHK Chennai plot", ""),
    RegressionSnapshotEntry("SNAP-002-30x40-chennai-3bhk-vastu-full", "3BHK with FULL vastu", ""),
    RegressionSnapshotEntry("SNAP-003-narrow-strip-3x30", "Narrow strip plot stress", ""),
    RegressionSnapshotEntry("SNAP-004-large-N-20rooms", "20-room luxury home", ""),
    RegressionSnapshotEntry("SNAP-005-stilt-mandate-mumbai", "Mumbai stilt-mandated plot", ""),
)


# ─────────────────────────────────────────────────────────────────────
# B-C16-COORDINATE-CONVENTION-IFC-COMPATIBILITY-VERIFICATION +
# B-C16-DUAL-FRAME-COORDINATE-CONVERSION-AUDIT
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CoordinateConventionContract:
    """v0.2 A2 + v0.4 A4 dual-frame contract."""
    local_building_frame_origin: str = "envelope_SW_corner"
    plot_aligned_frame_origin: str = "plot_SW_corner"
    ifc_compatible: bool = True
    ifc_local_placement_mapping: str = "IfcLocalPlacement → LocalBuildingFrame 1:1"
    round_trip_tolerance_mm: float = 1.0


COORDINATE_CONVENTION_CONTRACT: Final[CoordinateConventionContract] = (
    CoordinateConventionContract()
)


# ─────────────────────────────────────────────────────────────────────
# B-PROJECT-SELECTOR-CANONICALIZATION-CONTRACT-LOCK
# (shared between C16 and C17 — canonical serializer for
# SelectionReplayIdentity)
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SelectionReplayIdentity:
    """Shared selector identity. C16 + C17 both import this from
    here (single source of truth)."""
    selection_id: str
    selected_candidate_signature: str
    selector_component: str             # 'C14' | 'C15' | 'manual'
    selected_at_iso: str

    def canonical_serialize(self) -> str:
        """Lex-ASC field order, no whitespace, no trailing newline."""
        return (
            f"{self.selection_id}|"
            f"{self.selected_candidate_signature}|"
            f"{self.selector_component}|"
            f"{self.selected_at_iso}"
        )


# ─────────────────────────────────────────────────────────────────────
# B-C16-V0.3-TO-V0.4-MIGRATION-AUDIT
# ─────────────────────────────────────────────────────────────────────


V0_3_TO_V0_4_MIGRATION_AUDIT_STATUS: Final[str] = (
    "AUDIT_COMPLETE_S55: no in-flight builds depend on v0.3 A4 "
    "longest-wall rule. v0.4 A4 wall-with-most-doors rule supersedes."
)


# ─────────────────────────────────────────────────────────────────────
# B-C16-EPSILON-POLICY-CI-CHECK
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EpsilonPolicyRule:
    forbidden_pattern: str
    permitted_constant_names: tuple[str, ...]


EPSILON_POLICY_RULES: Final[Tuple[EpsilonPolicyRule, ...]] = (
    EpsilonPolicyRule(
        forbidden_pattern=r"abs\([^)]+\)\s*<\s*0\.0\d+",
        permitted_constant_names=(
            "EPSILON_MM", "EPSILON_M", "EPSILON_AMOUNT_INR",
            "EPSILON_DEG", "ARITHMETIC_M",
        ),
    ),
)


# ─────────────────────────────────────────────────────────────────────
# B-C16-OVERLAY-VALIDATION-RULES-LOCK
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OverlayValidationRule:
    overlay_kind: str
    required_elements: tuple[str, ...]
    semantic_completeness_check: str   # function name in c16/orientation.py or similar


OVERLAY_VALIDATION_RULES: Final[Tuple[OverlayValidationRule, ...]] = (
    OverlayValidationRule(
        overlay_kind="setback",
        required_elements=("setback_lines", "setback_dimensions", "compliance_marker"),
        semantic_completeness_check="check_setback_overlay_complete",
    ),
    OverlayValidationRule(
        overlay_kind="far",
        required_elements=("permissible_far_label", "achieved_far_label", "delta_marker"),
        semantic_completeness_check="check_far_overlay_complete",
    ),
    OverlayValidationRule(
        overlay_kind="rwh",
        required_elements=("catchment_outline", "tank_location", "percolation_pit_location"),
        semantic_completeness_check="check_rwh_overlay_complete",
    ),
    OverlayValidationRule(
        overlay_kind="parking",
        required_elements=("parking_bays", "circulation_aisles", "count_summary_block"),
        semantic_completeness_check="check_parking_overlay_complete",
    ),
)


# ─────────────────────────────────────────────────────────────────────
# CI-check status manifest
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CiCheckClosureStatus:
    item_id: str
    headline: str
    status: str        # 'LANDED' | 'SCAFFOLDED' | 'DEFERRED'
    pinned_at: str


C16_LOCK_CLOSURE_MANIFEST: Final[Tuple[CiCheckClosureStatus, ...]] = (
    CiCheckClosureStatus("B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK", "IS 962 baseline pinned", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-ENVELOPE-SCHEMA-LOCK", "4 envelope schemas pinned", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-SELECTED-LAYOUT-CONTRACT-LOCK", "Typestate enum + contract", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-SECTION-CUT-RULES-LOCK", "3 mandatory cuts + fallback table", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-RWH-SEWAGE-OVERLAY-DETAIL-LOCK", "TNCDBR rule 7/8/9 values", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-COMPLIANCE-PROVENANCE-FORMAT-LOCK", "AuthorityKind + contract", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-PARKING-PROVISION-SCHEMA-LOCK", "Schema + compliance check", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-PBT-LAYER-COVERAGE", "15-PBT manifest", "SCAFFOLDED", "S55"),
    CiCheckClosureStatus("B-C16-REGRESSION-SNAPSHOT-CORPUS", "5-snapshot corpus scaffold", "SCAFFOLDED", "S55"),
    CiCheckClosureStatus("B-C16-COORDINATE-CONVENTION-IFC-COMPATIBILITY-VERIFICATION", "IFC contract pinned", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-SHARED-GEOMETRY-PARITY-CI-CHECK", "CI script slot (R20)", "SCAFFOLDED", "S55"),
    CiCheckClosureStatus("B-C16-SECTION-CUT-FALLBACK-CORPUS", "10-case corpus IDs", "SCAFFOLDED", "S55"),
    CiCheckClosureStatus("B-C16-SEMANTIC-IDENTITY-STABILITY-CI", "CI script slot", "SCAFFOLDED", "S55"),
    CiCheckClosureStatus("B-C16-DUAL-FRAME-COORDINATE-CONVERSION-AUDIT", "1mm round-trip contract", "LANDED", "S55"),
    CiCheckClosureStatus("B-PROJECT-SELECTOR-CANONICALIZATION-CONTRACT-LOCK", "SelectionReplayIdentity", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-V0.3-TO-V0.4-MIGRATION-AUDIT", "audit complete", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-EPSILON-POLICY-CI-CHECK", "rule table + permitted constants", "LANDED", "S55"),
    CiCheckClosureStatus("B-C16-OVERLAY-VALIDATION-RULES-LOCK", "4 overlay-kind rules", "LANDED", "S55"),
)


__all__ = [
    "C16_LOCK_VERSION",
    # Renderer conformance
    "RendererConformanceContract", "RENDERER_CONFORMANCE_CONTRACT",
    # Envelope schemas
    "EnvelopeSchemaField",
    "FLOOR_PLAN_WORKING_SCHEMA", "FLOOR_PLAN_PERMIT_SCHEMA",
    "SECTION_VIEW_SCHEMA", "ELEVATION_SCHEMA",
    # Selected layout contract
    "SelectionResultState", "SelectedLayoutContract",
    # Section cut
    "SectionCutRule", "SECTION_CUT_RULES", "SECTION_CUT_FALLBACK_CORPUS_CASE_IDS",
    # RWH + sewage
    "RwhOverlayDetail", "RWH_OVERLAY_DETAIL",
    "SewageOverlayDetail", "SEWAGE_OVERLAY_DETAIL",
    # Compliance provenance
    "AuthorityKind", "ComplianceProvenance",
    # Parking
    "ParkingProvision",
    # PBT + regression
    "C16_PBT_COVERAGE_MANIFEST",
    "RegressionSnapshotEntry", "C16_REGRESSION_SNAPSHOT_CORPUS",
    # Coordinate convention
    "CoordinateConventionContract", "COORDINATE_CONVENTION_CONTRACT",
    # Selector identity
    "SelectionReplayIdentity",
    # Migration audit
    "V0_3_TO_V0_4_MIGRATION_AUDIT_STATUS",
    # Epsilon policy
    "EpsilonPolicyRule", "EPSILON_POLICY_RULES",
    # Overlay validation
    "OverlayValidationRule", "OVERLAY_VALIDATION_RULES",
    # Manifest
    "CiCheckClosureStatus", "C16_LOCK_CLOSURE_MANIFEST",
]
