"""
C16 — Dual-Drawing Renderer — schema (top-level bindings)
============================================================

Sub-1 scope: this module pins the BINDING top-level types (Inv R1–R34
enforced) and SKETCH-level sub-envelopes (RoomGeometry, WallSegment,
WindowGeometry, etc.) deferred to B-C16-ENVELOPE-SCHEMA-LOCK at C16
v1.0 LOCK.

What is FULLY locked at Sub-1:
    - DualDrawingBundle top-level + R24 referential integrity (R24a/b/c)
    - FloorGeometry + ElementIdentity (semantic + presentation hashes
      with identity_generation per v0.4 A10 / R33)
    - WorkingDrawingModel + PermitDrawingModel shells with R20 parity
    - PermitDrawingModel: legal_completeness + readability_status split
      per v0.4 A5 (R30 orthogonality)
    - ComplianceAttestation with AttestedValue + CheckProvenance
      (R15 + R22 + R25 partial)
    - CanonicalTransform2D (v0.5 A1 — R28d 64-bit overflow detection)
    - AdvisoryFlag (R8 passthrough)
    - SchemaDescriptor + schema_descriptor_digest verification (R26b)
    - PhaseTimings (v0.2 A10) — excluded from cache
    - ReadabilityDiagnostics + SuppressedAnnotation (v0.3 A6) — excluded
    - SignaturePlaceholder (v0.2 A4 — signature flow hook)

What is SKETCH at Sub-1 (B-C16-ENVELOPE-SCHEMA-LOCK):
    - RoomGeometry, WallSegment, DoorGeometry, WindowGeometry,
      ColumnGeometry, PlumbingStack — minimal placeholder fields,
      each carries `identity: ElementIdentity` so referential integrity
      works end-to-end at Sub-1, but their feature-rich payloads
      remain to be pinned at v1.0 LOCK.
    - SectionView, Elevation, RoofPlan, KeyPlan, SitePlan — same.
    - DoorScheduleEntry, WindowScheduleEntry, FinishScheduleEntry —
      same.
    - SetbackDimensions, SetbackComplianceReport, ParkingProvision,
      ParkingComplianceReport — same.
    - RainWaterHarvestingOverlay, SewageLayoutOverlay — same.

Rule 11 self-analysis worst issues:
    1. SKETCH sub-envelope strategy: per v0.1 § 1.4 + § 14 LOCK
       readiness item #1 (B-C16-ENVELOPE-SCHEMA-LOCK), full field
       pinning is deliberately a v1.0 deliverable, NOT Sub-1.
       Resisting Pattern E (scope creep).
    2. R24b "no orphan geometry" — per v0.3 A2, EVERY FloorGeometry
       must be referenced by AT LEAST one WorkingDrawingFloor AND
       AT LEAST one PermitDrawingFloor. Enforced here. Edge case:
       single-floor bundles. Tested explicitly.
    3. R28d transform overflow — Python int is arbitrary-precision,
       so overflow won't happen at runtime in Python. The spec
       requires the CHECK to fire for downstream int64-typed
       renderers. We implement the check as an explicit range guard.
    4. R33b mixed-generation rejection — every ElementIdentity in
       a bundle MUST share the same identity_generation. Enforced.
    5. SchemaDescriptor digest comparison (R26b) — Sub-1 implements
       the helper. Actual deserialization-time verification is a
       Phase ζ concern (bundle assembly), beyond Sub-1.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Final, Literal, Optional

from buildemup.components.c16.cache_keys import (
    C16CacheKeys,
    canonical_json,
    sha256_hex,
)
from buildemup.components.c16.contracts import (
    AttestedValue,
    AuthorityKind,
    CheckProvenance,
    ElementKind,
    GeospatialReference,
    LegalCompleteness,
    LocalBuildingFrame,
    ReadabilityStatus,
    SelectionAuditMetadata,
)
from buildemup.components.c16.errors import (
    C16ConfigurationError,
    ComplianceProvenanceError,
    GeometryInconsistencyError,
)
from buildemup.components.c16.versioning import (
    C16_IDENTITY_GENERATION,
)


# ============================================================
# § 1 — Int64 overflow (v0.5 A1 — R28d)
# ============================================================

INT64_MAX: Final[int] =  9_223_372_036_854_775_807
INT64_MIN: Final[int] = -9_223_372_036_854_775_808


class TransformOverflowError(GeometryInconsistencyError):
    """v0.5 A1 / R28d. Treated as a GeometryInconsistencyError subtype
    because it indicates the geometry transform pipeline cannot honor
    the coordinate range. Per spec: LocalDrawingError-style halt — we
    inherit the per-layout shape but it semantically halts."""


def _check_int64(value: int, *, field_name: str) -> None:
    """R28d — overflow detection. Python ints are arbitrary-precision,
    so this is a guard for downstream typed renderers (C/C++/Rust)."""
    if not (INT64_MIN <= value <= INT64_MAX):
        raise TransformOverflowError(
            f"R28d: {field_name}={value} outside int64 range "
            f"[{INT64_MIN}, {INT64_MAX}]. Silent truncation forbidden.",
            invariant_id="R28d",
            offending_ids=(field_name,),
        )


@dataclass(frozen=True)
class CanonicalTransform2D:
    """6-element 2D affine transform (v0.4 A3 + v0.5 A1).

    All 6 elements MUST be 64-bit signed integers. Python int is
    arbitrary-precision so this is a downstream-renderer contract
    enforced here as a value-range guard.
    """
    a00_micro: int
    a01_micro: int
    a02_mm:    int
    a10_micro: int
    a11_micro: int
    a12_mm:    int

    def __post_init__(self) -> None:
        for fname, fval in (
            ("a00_micro", self.a00_micro),
            ("a01_micro", self.a01_micro),
            ("a02_mm",    self.a02_mm),
            ("a10_micro", self.a10_micro),
            ("a11_micro", self.a11_micro),
            ("a12_mm",    self.a12_mm),
        ):
            if not isinstance(fval, int) or isinstance(fval, bool):
                raise C16ConfigurationError(
                    f"CanonicalTransform2D.{fname} must be int "
                    f"(NOT bool, NOT float), got {type(fval).__name__}",
                    offending_field=fname,
                    offending_value=fval,
                )
            _check_int64(fval, field_name=f"CanonicalTransform2D.{fname}")


# ============================================================
# § 2 — ElementIdentity (v0.3 A3 + v0.4 A10 — R27, R33)
# ============================================================

@dataclass(frozen=True)
class ElementIdentity:
    """Two-tier identity per v0.3 A3 + generation-scoped per v0.4 A10.

    semantic_identity_hash: STABLE within identity_generation.
                            Computed from geometry-defining fields
                            only (NOT annotations, presentation, etc.).
    presentation_identity_hash: changes with any content change.
                                Includes everything.
    identity_generation:  per R33a, BUMPS only on coord-system migrations,
                          geometry normalization fixes, or taxonomy MAJOR.

    Hashes are 8-char hex (first 8 of SHA-256) per v0.2 A7.
    """
    identity_generation:       int
    semantic_identity_hash:    str  # 8 hex chars
    presentation_identity_hash: str  # 8 hex chars

    def __post_init__(self) -> None:
        if self.identity_generation < 1:
            raise C16ConfigurationError(
                f"ElementIdentity.identity_generation must be ≥ 1, "
                f"got {self.identity_generation}",
                offending_field="identity_generation",
                offending_value=self.identity_generation,
            )
        for fname, fval in (
            ("semantic_identity_hash",     self.semantic_identity_hash),
            ("presentation_identity_hash", self.presentation_identity_hash),
        ):
            if not isinstance(fval, str) or len(fval) != 8:
                raise C16ConfigurationError(
                    f"ElementIdentity.{fname} must be 8 hex chars "
                    f"(first 8 of SHA-256), got {fval!r}",
                    offending_field=fname,
                    offending_value=fval,
                )
            if not all(c in "0123456789abcdef" for c in fval):
                raise C16ConfigurationError(
                    f"ElementIdentity.{fname} must be lowercase hex.",
                    offending_field=fname,
                    offending_value=fval,
                )


def compute_element_identity(
    *,
    element_kind: ElementKind,
    floor_level: int,
    geometry_defining_payload: dict,
    full_payload: dict,
) -> ElementIdentity:
    """Compute the dual-hash identity per v0.3 A3 + v0.4 A10.

    semantic = SHA-256(canonical(kind + floor_level + geometry-only))[:8]
    presentation = SHA-256(canonical(full_payload))[:8]
    """
    semantic_source = {
        "element_kind":  element_kind.value,
        "floor_level":   floor_level,
        "geometry":      geometry_defining_payload,
    }
    semantic_full = sha256_hex(canonical_json(semantic_source))
    presentation_full = sha256_hex(canonical_json(full_payload))
    return ElementIdentity(
        identity_generation=C16_IDENTITY_GENERATION,
        semantic_identity_hash=semantic_full[:8],
        presentation_identity_hash=presentation_full[:8],
    )


# ============================================================
# § 3 — SKETCH sub-envelopes (B-C16-ENVELOPE-SCHEMA-LOCK)
# ============================================================
#
# Each carries the bare minimum needed for Sub-1's referential
# integrity wiring. Full schemas land at C16 v1.0 LOCK.

@dataclass(frozen=True)
class RoomGeometry:
    """One room placed in LocalBuildingFrame coordinates.

    Source: C12.PlacedRoom (x_m, y_m, width_m, depth_m, room_id,
    category). C16 converts metres → millimetres (Inv R7a — int mm)
    and re-anchors from envelope-SW to LocalBuildingFrame-SW.
    """
    identity:    ElementIdentity
    room_id:     str
    category:    str        # canonical category string from C12
    x_mm:        int        # LocalBuildingFrame SW-origin
    y_mm:        int
    width_mm:    int
    depth_mm:    int


@dataclass(frozen=True)
class WallSegment:
    """One wall — perimeter (from C7) or internal partition (from C12
    SharedEdge). All coords in LocalBuildingFrame mm."""
    identity:     ElementIdentity
    wall_id:      str
    element_kind: ElementKind   # WALL_EXTERNAL / WALL_INTERNAL_PARTITION etc.
    start_x_mm:   int
    start_y_mm:   int
    end_x_mm:     int
    end_y_mm:     int


@dataclass(frozen=True)
class DoorGeometry:
    """One door on a shared edge (from C13).

    Source: C13.Door + C12.SharedEdge geometry.
    position_mm = absolute coord of door anchor; computed from
    SharedEdge.overlap_start_m + Door.position_along_edge_m at α.
    """
    identity:        ElementIdentity
    door_id:         str
    room_a_id:       str
    room_b_id:       str
    axis:            Literal["vertical", "horizontal"]
    anchor_x_mm:     int        # door anchor in LocalBuildingFrame
    anchor_y_mm:     int
    clear_width_mm:  int
    swing_direction: Literal["into_room_a", "into_room_b"]
    hinge_side:      Literal["start", "end"]
    leaf_thickness_mm: int
    is_main_entry:   bool = False    # used by R29 hierarchy step 2
    element_kind:    ElementKind = ElementKind.DOOR_INTERNAL


@dataclass(frozen=True)
class WindowGeometry:
    """One window. v1: no upstream component emits windows — Phase α
    optionally generates defaults from external walls. Documented as
    `B-C16-WINDOW-UPSTREAM-CONTRACT` in backlog. v1.0 default: empty."""
    identity:       ElementIdentity
    window_id:      str
    wall_id:        str       # the WallSegment this window sits on
    center_x_mm:    int
    center_y_mm:    int
    width_mm:       int
    sill_height_mm: int
    head_height_mm: int
    element_kind:   ElementKind = ElementKind.WINDOW_EXTERNAL


@dataclass(frozen=True)
class ColumnGeometry:
    """One structural column. Source: C7.ColumnPosition."""
    identity:     ElementIdentity
    column_id:    str            # C7's grid_label, e.g. "A1"
    x_mm:         int
    y_mm:         int
    width_mm:     int            # column cross-section
    depth_mm:     int
    on_perimeter: bool


@dataclass(frozen=True)
class PlumbingStack:
    """One vertical plumbing riser. Source: C10.RiserGroup +
    RiserAnchor.riser_anchor_xy."""
    identity:        ElementIdentity
    stack_id:        str          # C10 RiserGroup.group_id
    element_kind:    ElementKind   # PLUMBING_STACK_*
    x_mm:            int
    y_mm:            int
    wall_id:         str          # wall the stack is anchored to
    serves_room_ids: tuple[str, ...]   # C10 wet_room_ids


@dataclass(frozen=True)
class SectionView:
    """One section cut through the building.

    R23: cut_type ∈ RenderingConfig.mandatory_section_cuts.
    Per v0.2 A8 fallback: section cut may be offset to stay inside
    the building envelope; offset_mm records the magnitude.
    """
    identity:         ElementIdentity
    section_id:       str
    cut_type:         Literal["entry", "staircase", "wet_zone"]
    floors_traversed: tuple[int, ...]
    axis:             Literal["vertical", "horizontal"]
    cut_position_mm:  int           # absolute LocalBuildingFrame coord
    offset_mm:        int = 0       # magnitude of fallback offset (R23)


@dataclass(frozen=True)
class Elevation:
    """One building elevation (cardinal facade view)."""
    identity:     ElementIdentity
    elevation_id: str
    facade_axis:  Literal["north", "south", "east", "west"]
    width_mm:     int
    height_mm:    int


@dataclass(frozen=True)
class RoofPlan:
    """Roof outline + drainage direction."""
    identity:           ElementIdentity
    outline_x_mm:       int
    outline_y_mm:       int
    outline_width_mm:   int
    outline_depth_mm:   int
    drainage_slope_pct: float = 1.0   # NBC ≥ 1% for flat roofs


@dataclass(frozen=True)
class KeyPlan:
    """Small reference plan placed in corner of permit sheet."""
    identity:        ElementIdentity
    floor_count:     int
    site_outline_mm: tuple[int, int, int, int]   # (x, y, w, d) plot bbox


@dataclass(frozen=True)
class SitePlan:
    """Plot-level site plan with setback markings."""
    identity:                ElementIdentity
    plot_x_mm:               int
    plot_y_mm:               int
    plot_width_mm:           int
    plot_depth_mm:           int
    building_footprint_xywh: tuple[int, int, int, int]   # (x, y, w, d)


@dataclass(frozen=True)
class DoorScheduleEntry:
    """Working-drawing door schedule entry. Per Indian construction
    convention: number, location, size (width × height), material."""
    door_identity:   ElementIdentity
    schedule_id:     str
    door_number:     str
    width_mm:        int
    height_mm:       int = 2100    # standard door height
    material:        str = "wood"


@dataclass(frozen=True)
class WindowScheduleEntry:
    """Window schedule entry."""
    window_identity: ElementIdentity
    schedule_id:     str
    window_number:   str
    width_mm:        int
    height_mm:       int
    material:        str = "aluminium"


@dataclass(frozen=True)
class FinishScheduleEntry:
    """Per-room finish (floor / wall / ceiling) per Indian residential
    convention."""
    room_identity:   ElementIdentity
    schedule_id:     str
    floor_finish:    str = "vitrified_tile"
    wall_finish:     str = "emulsion_paint"
    ceiling_finish:  str = "emulsion_paint"


@dataclass(frozen=True)
class SetbackDimensions:
    """Setback values from plot boundary to building, in mm."""
    front_mm: int = 0
    rear_mm:  int = 0
    left_mm:  int = 0
    right_mm: int = 0


@dataclass(frozen=True)
class SetbackComplianceReport:
    """Per-side setback compliance against jurisdiction minimums."""
    setback_dimensions: SetbackDimensions
    front_min_required_mm: int = 0
    rear_min_required_mm:  int = 0
    left_min_required_mm:  int = 0
    right_min_required_mm: int = 0
    all_compliant:         bool = True


@dataclass(frozen=True)
class ParkingProvision:
    """Parking provision marking."""
    provided_count: int = 0
    required_count: int = 0
    bay_size_mm:    tuple[int, int] = (2500, 5000)   # standard car bay


@dataclass(frozen=True)
class ParkingComplianceReport:
    """Parking compliance against jurisdiction requirements."""
    compliant:        bool = False
    provided_count:   int = 0
    required_count:   int = 0


@dataclass(frozen=True)
class RainWaterHarvestingOverlay:
    """RWH overlay per TNCDBR rule 9(a)."""
    overlay_id:           str
    pit_count:            int = 1
    pit_location_xy_mm:   tuple[int, int] = (0, 0)


@dataclass(frozen=True)
class SewageLayoutOverlay:
    """Sewage layout overlay per TNCDBR rule 9(b)."""
    overlay_id:                  str
    septic_tank_location_xy_mm:  tuple[int, int] = (0, 0)
    sewage_treatment_capacity_l: int = 1500


@dataclass(frozen=True)
class WorkingAnnotation:
    """One annotation on a working drawing — dimensions, labels, notes."""
    annotation_id:  str
    text:           str = ""
    anchor_x_mm:    int = 0
    anchor_y_mm:    int = 0
    annotation_kind: Literal["dimension", "room_label", "note", "elevation"] = "note"


@dataclass(frozen=True)
class SetbackAnnotation:
    """One setback dimension callout on permit drawing."""
    annotation_id:  str
    side:           Literal["front", "rear", "left", "right"]
    value_mm:       int
    anchor_x_mm:    int = 0
    anchor_y_mm:    int = 0


@dataclass(frozen=True)
class ComplianceMarker:
    """One compliance marker (RWH symbol, parking grid, etc.)."""
    marker_id:   str
    marker_kind: Literal[
        "rwh_pit", "parking_bay", "septic_tank",
        "fire_path", "north_arrow",
    ] = "north_arrow"
    anchor_x_mm: int = 0
    anchor_y_mm: int = 0


@dataclass(frozen=True)
class SignaturePlaceholder:
    """v0.2 A4 — hook for downstream architect signature flow.
    OUT OF SCOPE for C16 to fill; this is the data envelope."""
    placeholder_id: str


# ============================================================
# § 4 — Provenance + advisory (R8 / R16)
# ============================================================

@dataclass(frozen=True)
class AdvisoryFlag:
    """R8 passthrough from C13/C14/C15. C16 NEVER mutates these."""
    source_component: str
    flag_id:          str
    message:          str


# ============================================================
# § 5 — FloorGeometry (v0.2 A3 + v0.3 A3)
# ============================================================

@dataclass(frozen=True)
class FloorGeometry:
    """Source-of-truth geometry per floor. Shared by Working and Permit
    drawings via geometry_ref → identity.semantic_identity_hash.

    Per v0.2 A3 + v0.3 A3: the geometry_id flat field was REPLACED
    by an `identity` ElementIdentity field.
    """
    floor_level:        int
    floor_elevation_mm: int
    identity:           ElementIdentity

    rooms:           tuple[RoomGeometry, ...]    = ()
    walls:           tuple[WallSegment, ...]      = ()
    doors:           tuple[DoorGeometry, ...]     = ()
    windows:         tuple[WindowGeometry, ...]   = ()
    columns:         tuple[ColumnGeometry, ...]   = ()
    plumbing_stacks: tuple[PlumbingStack, ...]    = ()

    @property
    def geometry_ref(self) -> str:
        """The opaque reference downstream overlays use. Per v0.3 A3
        this is the semantic_identity_hash (NOT presentation)."""
        return self.identity.semantic_identity_hash


# ============================================================
# § 6 — Working + Permit drawing overlay floors (R20)
# ============================================================

@dataclass(frozen=True)
class WorkingDrawingFloor:
    geometry_ref: str
    annotations:        tuple[WorkingAnnotation, ...]   = ()
    door_schedule:      tuple[DoorScheduleEntry, ...]   = ()
    window_schedule:    tuple[WindowScheduleEntry, ...] = ()
    finish_schedule:    tuple[FinishScheduleEntry, ...] = ()


@dataclass(frozen=True)
class PermitDrawingFloor:
    geometry_ref: str
    setback_annotations:  tuple[SetbackAnnotation, ...]   = ()
    compliance_markers:   tuple[ComplianceMarker, ...]     = ()


# ============================================================
# § 7 — Compliance attestation (v0.2 A5 — R15, R22)
# ============================================================

@dataclass(frozen=True)
class ComplianceAttestation:
    """Packaging of upstream compliance decisions.

    Per R15: every claim MUST trace to a CheckProvenance entry.
    Per R22: AttestedValue enforces authority discipline (in contracts.py).
    Per R25: submission_readiness / legal_completeness MAY ONLY derive
             from UPSTREAM_AUTHORITATIVE entries — enforced at the
             PermitDrawingModel level since that's where readiness lives.
    """
    plot_area_sqm:           AttestedValue
    built_up_area_sqm:       AttestedValue
    plot_coverage_pct:       AttestedValue
    far_used:                AttestedValue
    far_permitted:           AttestedValue
    building_height_m:       AttestedValue
    height_limit_m:          AttestedValue
    floors_count:            AttestedValue

    setback_compliance:      SetbackComplianceReport
    parking_compliance:      ParkingComplianceReport
    rwh_present:             AttestedValue
    sewage_treatment_present: AttestedValue

    upstream_check_provenance: tuple[CheckProvenance, ...] = ()

    def __post_init__(self) -> None:
        # R15: provenance non-empty for every UPSTREAM_AUTHORITATIVE field
        # (other authority kinds carry their own derivation, but every
        # value family should still have at least one provenance entry
        # so consumers can trace back to the originating check).
        if not self.upstream_check_provenance:
            raise ComplianceProvenanceError(
                "ComplianceAttestation.upstream_check_provenance must be "
                "non-empty. R15 requires every compliance claim trace to "
                "an upstream CheckResult.",
                invariant_id="R15",
            )


# ============================================================
# § 8 — Permit-critical overlay enumeration (v0.2 A4 / R21 / R30)
# ============================================================

PERMIT_CRITICAL_OVERLAY_NAMES: Final[frozenset[str]] = frozenset({
    "rain_water_harvesting",        # TNCDBR rule 9(a)
    "sewage_layout",                # TNCDBR rule 9(b)
    "setback_dimensions",
    "far_and_coverage_attestation",
    "parking_provision",
})


# ============================================================
# § 9 — WorkingDrawingModel
# ============================================================

@dataclass(frozen=True)
class WorkingDrawingModel:
    floor_plans:        tuple[WorkingDrawingFloor, ...]
    section_views:      tuple[SectionView, ...]      = ()
    roof_plan:          Optional[RoofPlan]            = None
    door_schedule:      tuple[DoorScheduleEntry, ...] = ()
    window_schedule:    tuple[WindowScheduleEntry, ...] = ()
    finish_schedule:    tuple[FinishScheduleEntry, ...] = ()
    recommended_scale:  Literal["1:50", "1:75"]       = "1:50"


# ============================================================
# § 10 — PermitDrawingModel (v0.4 A5 — R30 orthogonality)
# ============================================================

@dataclass(frozen=True)
class PermitDrawingModel:
    site_plan:          SitePlan
    floor_plans:        tuple[PermitDrawingFloor, ...]
    elevations:         tuple[Elevation, ...]         = ()
    section_views:      tuple[SectionView, ...]       = ()
    key_plan:           Optional[KeyPlan]              = None
    compliance_attestation: Optional[ComplianceAttestation] = None
    rwh_overlay:        Optional[RainWaterHarvestingOverlay] = None
    sewage_layout:      Optional[SewageLayoutOverlay]  = None
    parking_provision:  Optional[ParkingProvision]     = None

    north_arrow_orientation_deg: float = 0.0
    recommended_scale:  Literal["1:100", "1:150", "1:200"] = "1:100"

    # v0.4 A5 — orthogonal split (R30)
    legal_completeness:    LegalCompleteness = LegalCompleteness.UNSAFE_FOR_SUBMISSION
    readability_status:    ReadabilityStatus = ReadabilityStatus.READABLE
    requires_professional_signature: bool = True   # ALWAYS True (TNCDBR rule 8(1)(iii))
    missing_overlays:      tuple[str, ...] = ()
    signature_placeholder: Optional[SignaturePlaceholder] = None

    def __post_init__(self) -> None:
        # R21: LEGALLY_COMPLETE requires all permit-critical overlays present
        if self.legal_completeness == LegalCompleteness.LEGALLY_COMPLETE:
            present_overlays = self._enumerate_present_overlays()
            missing = PERMIT_CRITICAL_OVERLAY_NAMES - present_overlays
            if missing:
                raise C16ConfigurationError(
                    f"R21: PermitDrawingModel marked LEGALLY_COMPLETE but "
                    f"missing permit-critical overlays {sorted(missing)}.",
                    offending_field="legal_completeness",
                    offending_value=self.legal_completeness.value,
                )

        # R21 paired with v0.2 A4 inverse: UNSAFE_FOR_SUBMISSION + LEGALLY_INCOMPLETE
        # MUST have non-empty missing_overlays (else why is it unsafe?)
        if self.legal_completeness != LegalCompleteness.LEGALLY_COMPLETE:
            if not self.missing_overlays:
                # Allow this when explicitly UNSAFE_FOR_SUBMISSION due to
                # other failures (validation errors), but LEGALLY_INCOMPLETE
                # specifically means an overlay-class problem.
                if self.legal_completeness == LegalCompleteness.LEGALLY_INCOMPLETE:
                    raise C16ConfigurationError(
                        "R21: PermitDrawingModel LEGALLY_INCOMPLETE must list "
                        "missing_overlays (which permit-critical overlay is absent?).",
                        offending_field="missing_overlays",
                        offending_value=self.missing_overlays,
                    )

        # north_arrow in [0, 360)
        if not (0.0 <= self.north_arrow_orientation_deg < 360.0):
            raise C16ConfigurationError(
                f"PermitDrawingModel.north_arrow_orientation_deg must be "
                f"in [0, 360), got {self.north_arrow_orientation_deg}.",
                offending_field="north_arrow_orientation_deg",
                offending_value=self.north_arrow_orientation_deg,
            )

    def _enumerate_present_overlays(self) -> frozenset[str]:
        """Which permit-critical overlay names this model carries."""
        present: set[str] = set()
        if self.rwh_overlay is not None:
            present.add("rain_water_harvesting")
        if self.sewage_layout is not None:
            present.add("sewage_layout")
        if self.compliance_attestation is not None:
            # FAR + coverage attestation
            present.add("far_and_coverage_attestation")
            # setbacks live inside compliance_attestation.setback_compliance
            if self.compliance_attestation.setback_compliance is not None:
                present.add("setback_dimensions")
        if self.parking_provision is not None:
            present.add("parking_provision")
        return frozenset(present)


# ============================================================
# § 11 — Observability (excluded from cache)
# ============================================================

@dataclass(frozen=True)
class PhaseTimings:
    """v0.2 A10 — observability only. EXCLUDED from cache_keys."""
    alpha_envelope_assembly_ms:    int
    beta_scheduling_ms:            int
    gamma_working_assembly_ms:     int
    delta_permit_assembly_ms:      int
    epsilon_attestation_packaging_ms: int
    zeta_bundle_assembly_ms:       int
    total_ms:                      int

    def __post_init__(self) -> None:
        for fname in (
            "alpha_envelope_assembly_ms", "beta_scheduling_ms",
            "gamma_working_assembly_ms", "delta_permit_assembly_ms",
            "epsilon_attestation_packaging_ms", "zeta_bundle_assembly_ms",
            "total_ms",
        ):
            v = getattr(self, fname)
            if v < 0:
                raise C16ConfigurationError(
                    f"PhaseTimings.{fname} must be ≥ 0, got {v}",
                    offending_field=fname,
                    offending_value=v,
                )


@dataclass(frozen=True)
class SuppressedAnnotation:
    """v0.3 A6 — one annotation suppression event."""
    annotation_id:        str
    conflicting_annotation_id: str
    precedence_rule_fired: str


@dataclass(frozen=True)
class ReadabilityDiagnostics:
    """v0.3 A6 — observability. EXCLUDED from cache_keys."""
    collision_count:            int
    suppressed_annotations:     tuple[SuppressedAnnotation, ...]
    viewport_congestion_score:  float          # 0.0 .. 1.0
    readability_degraded:       bool

    def __post_init__(self) -> None:
        if self.collision_count < 0:
            raise C16ConfigurationError(
                "ReadabilityDiagnostics.collision_count must be ≥ 0.",
                offending_field="collision_count",
                offending_value=self.collision_count,
            )
        if not (0.0 <= self.viewport_congestion_score <= 1.0):
            raise C16ConfigurationError(
                f"ReadabilityDiagnostics.viewport_congestion_score must be "
                f"in [0, 1], got {self.viewport_congestion_score}.",
                offending_field="viewport_congestion_score",
                offending_value=self.viewport_congestion_score,
            )


# ============================================================
# § 12 — SchemaDescriptor + R26b digest (v0.5 A2)
# ============================================================

@dataclass(frozen=True)
class SchemaDescriptor:
    """v0.5 A2 — companion artifact describing the bundle's schema
    shape. C16 emits this alongside DualDrawingBundle; consumers
    verify pairing via schema_descriptor_digest."""
    c16_version:                str
    c16_drawing_schema_version: int
    c16_identity_generation:    int
    jurisdiction_id:            str
    declared_domain_scope:      str


def compute_schema_descriptor_digest(descriptor: SchemaDescriptor) -> str:
    """SHA-256 of canonical-JSON-ized SchemaDescriptor (R26b)."""
    return sha256_hex(canonical_json(descriptor))


# ============================================================
# § 13 — DualDrawingBundle (top-level — R1, R7, R8, R16, R20, R24, R26b, R32, R33)
# ============================================================

@dataclass(frozen=True)
class DualDrawingBundle:
    """The full output of one C16 invocation.

    Top-level invariants enforced at __post_init__:
        R8   — upstream_advisory_flags byte-identical passthrough
        R16  — version triple non-empty
        R20  — geometry parity: every working geometry_ref matches a
               permit geometry_ref AND vice versa
        R24a — every geometry_ref resolves to exactly one FloorGeometry
        R24b — every FloorGeometry referenced by ≥1 Working AND ≥1 Permit
        R24c — geometry_id uniqueness across FloorGeometry tuple
        R26b — schema_descriptor_digest validation hook
        R32a — canonical_replay_signature ⊥ presentation_signature
               (different fields populated independently)
        R32c — presentation_signature ≡ implies canonical_replay_signature ≡
               (verified externally; we just store both)
        R33b — every ElementIdentity in the bundle shares identity_generation
    """
    # Provenance
    source_selection_signature:   str
    selection_audit_metadata:     SelectionAuditMetadata
    c16_version:                  str
    c16_drawing_schema_version:   int
    jurisdiction_profile_id:      str
    declared_domain_scope:        str

    # Geometry (single source of truth)
    floor_geometries:             tuple[FloorGeometry, ...]
    local_building_frame:         LocalBuildingFrame
    geospatial_reference:         GeospatialReference

    # Drawing overlays
    working_drawing_model:        WorkingDrawingModel
    permit_drawing_model:         PermitDrawingModel

    # Advisory + cache
    upstream_advisory_flags:      tuple[AdvisoryFlag, ...]
    cache_keys:                   C16CacheKeys

    # Identity / signatures (v0.4 A9 + v0.5 A2)
    canonical_replay_signature:   str
    presentation_signature:       str
    schema_descriptor_digest:     str

    # Observability (OPTIONAL — excluded from cache_keys)
    phase_timings:                Optional[PhaseTimings]         = None
    readability_diagnostics:      Optional[ReadabilityDiagnostics] = None

    def __post_init__(self) -> None:
        # R16 — version triple sanity
        if not self.c16_version:
            raise C16ConfigurationError(
                "DualDrawingBundle.c16_version must be non-empty (R16).",
                offending_field="c16_version",
                offending_value=self.c16_version,
            )
        if self.c16_drawing_schema_version < 1:
            raise C16ConfigurationError(
                f"DualDrawingBundle.c16_drawing_schema_version must be ≥ 1, "
                f"got {self.c16_drawing_schema_version}",
                offending_field="c16_drawing_schema_version",
                offending_value=self.c16_drawing_schema_version,
            )
        if not self.jurisdiction_profile_id:
            raise C16ConfigurationError(
                "DualDrawingBundle.jurisdiction_profile_id must be non-empty.",
                offending_field="jurisdiction_profile_id",
                offending_value=self.jurisdiction_profile_id,
            )

        # Signatures sanity (64-hex SHA-256)
        for fname in (
            "canonical_replay_signature",
            "presentation_signature",
            "schema_descriptor_digest",
        ):
            v = getattr(self, fname)
            if not isinstance(v, str) or len(v) != 64 or not all(
                c in "0123456789abcdef" for c in v
            ):
                raise C16ConfigurationError(
                    f"DualDrawingBundle.{fname} must be 64-char lowercase "
                    f"SHA-256 hex digest.",
                    offending_field=fname,
                    offending_value=v,
                )

        # R24c — uniqueness of geometry_id
        seen: dict[str, FloorGeometry] = {}
        for fg in self.floor_geometries:
            gid = fg.geometry_ref
            if gid in seen:
                raise GeometryInconsistencyError(
                    f"R24c: duplicate geometry_ref {gid!r} "
                    f"(floors {seen[gid].floor_level} and {fg.floor_level}).",
                    invariant_id="R24c",
                    offending_ids=(gid,),
                )
            seen[gid] = fg

        # R24a — every working/permit geometry_ref resolves
        working_refs: set[str] = set()
        for wfp in self.working_drawing_model.floor_plans:
            if wfp.geometry_ref not in seen:
                raise GeometryInconsistencyError(
                    f"R24a: working geometry_ref {wfp.geometry_ref!r} "
                    f"does not resolve to any FloorGeometry.",
                    invariant_id="R24a",
                    offending_ids=(wfp.geometry_ref,),
                )
            working_refs.add(wfp.geometry_ref)

        permit_refs: set[str] = set()
        for pfp in self.permit_drawing_model.floor_plans:
            if pfp.geometry_ref not in seen:
                raise GeometryInconsistencyError(
                    f"R24a: permit geometry_ref {pfp.geometry_ref!r} "
                    f"does not resolve to any FloorGeometry.",
                    invariant_id="R24a",
                    offending_ids=(pfp.geometry_ref,),
                )
            permit_refs.add(pfp.geometry_ref)

        # R24b — no orphan FloorGeometry
        all_geometry_ids = set(seen.keys())
        orphan_w = all_geometry_ids - working_refs
        orphan_p = all_geometry_ids - permit_refs
        if orphan_w or orphan_p:
            raise GeometryInconsistencyError(
                f"R24b: orphan FloorGeometry — orphan_in_working="
                f"{sorted(orphan_w)!r}, orphan_in_permit={sorted(orphan_p)!r}.",
                invariant_id="R24b",
                offending_ids=tuple(sorted(orphan_w | orphan_p)),
            )

        # R20 — geometry parity: working refs ≡ permit refs
        if working_refs != permit_refs:
            only_w = working_refs - permit_refs
            only_p = permit_refs - working_refs
            raise GeometryInconsistencyError(
                f"R20: geometry-parity violation — only-in-working="
                f"{sorted(only_w)!r}, only-in-permit={sorted(only_p)!r}.",
                invariant_id="R20",
                offending_ids=tuple(sorted(only_w | only_p)),
            )

        # R33b — every ElementIdentity in this bundle shares identity_generation
        generations: set[int] = set()
        for fg in self.floor_geometries:
            generations.add(fg.identity.identity_generation)
            for collection in (
                fg.rooms, fg.walls, fg.doors, fg.windows,
                fg.columns, fg.plumbing_stacks,
            ):
                for elem in collection:
                    generations.add(elem.identity.identity_generation)
        if len(generations) > 1:
            raise C16ConfigurationError(
                f"R33b: mixed-generation bundle — found "
                f"identity_generations {sorted(generations)!r}.",
                offending_field="identity_generation",
                offending_value=sorted(generations),
            )


# ============================================================
# § 14 — Successful + Failed render typestate (v0.1 § 5)
# ============================================================

@dataclass(frozen=True)
class SuccessfulDrawingRender:
    bundle: DualDrawingBundle


@dataclass(frozen=True)
class FailureRecord:
    error_invariant_id: str
    error_message:      str
    phase:              Literal[
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta",
    ]


@dataclass(frozen=True)
class FailedDrawingRender:
    source_signature:  str
    failure_record:    FailureRecord
    partial_bundle:    Optional[DualDrawingBundle] = None


@dataclass(frozen=True)
class DrawingRenderBatchResult:
    successes:   tuple[SuccessfulDrawingRender, ...]
    failures:    tuple[FailedDrawingRender, ...]
