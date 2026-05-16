"""
C16 — Dual-Drawing Renderer — upstream contract types
========================================================

This module pins the SHAPE of every type C16 receives from upstream
(SelectionResult, JurisdictionProfile, etc.) and the discriminated
enums used across C16's own outputs (AuthorityKind, LegalCompleteness,
ReadabilityStatus, ElementKind, SelectionReason).

Schema-defining dataclasses (DualDrawingBundle, FloorGeometry,
WorkingDrawingModel, PermitDrawingModel, ComplianceAttestation,
ElementIdentity) live in `schema.py`. This module deliberately holds
ONLY the upstream/enum surface so schema.py can build on it.

Per-amendment provenance (curated):

    v0.2 A1  → SelectionReason enum, CandidateRanking, HumanOverrideRecord
    v0.2 A5  → AuthorityKind, AttestedValue (with R22 validation)
    v0.2 A7  → ElementKind taxonomy
    v0.3 A1  → SelectionReplayIdentity / SelectionAuditMetadata / SelectionResult
    v0.3 A4  → LocalBuildingFrame (marker type), GeospatialReference
    v0.3 A5  → R25 (gate on UPSTREAM_AUTHORITATIVE) — enforced upstream
                of attestation packaging; not at this layer.
    v0.4 A5  → LegalCompleteness ⊥ ReadabilityStatus enums
    v0.4 A10 → identity_generation (referenced in schema.ElementIdentity)
    v0.5 A4  → JurisdictionProfile.declared_domain_scope
    v0.5 A5  → OrientationLock (optional metadata)

Rule 11 self-analysis (worst issues):
    1. C15 ProblemReport coupling. We import directly from
       buildemup.components.c15 (now LOCKED v1.0). Stable upstream.
    2. AttestedValue.value union enforced at __post_init__ (Python
       union types are erased at runtime).
    3. CandidateRanking and HumanOverrideRecord are under-specified
       in the spec. Defined here with the minimum the spec requires;
       downstream amendments can refine without breaking Sub-1 wiring.
    4. R31b: declared_domain_scope enum-check happens at construction.
    5. OrientationLock plausibility (R29d) needs CURRENT GEOMETRY to
       compare against — that check happens in Phase α, not here.
       At construction, OrientationLock validates its OWN fields only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Literal, Optional, Union

# Upstream from C15 (LOCKED v1.0 at S49 — stable surface)
from buildemup.components.c15.schema import ProblemReport  # noqa: F401

from buildemup.components.c16.errors import (
    C16ConfigurationError,
    ComplianceProvenanceError,
)
from buildemup.components.c16.versioning import (
    EPSILON_ANGLE_DEG,
    SUPPORTED_DOMAIN_SCOPES,
    SUPPORTED_JURISDICTIONS,
)


# ============================================================
# § 1 — SELECTION CONTRACT (v0.2 A1 + v0.3 A1)
# ============================================================
#
# v0.2 A1 introduced flat SelectionResult; v0.3 A1 REPLACED it with
# a split into replay-identity (cache-relevant) and audit-metadata
# (excluded from cache keys). The split is the LOCKED shape.

class SelectionReason(Enum):
    """Why a particular layout became 'selected'."""
    HUMAN_CHOICE             = "human_choice"
    RANKER_TOP               = "ranker_top"
    TIEBREAK_DETERMINISTIC   = "tiebreak_deterministic"
    DEFAULT_FIRST            = "default_first"
    UNKNOWN_LEGACY           = "unknown_legacy"


@dataclass(frozen=True)
class CandidateRanking:
    """One ranked candidate snapshot at selection time.

    Spec is light on shape; the minimal surface required is:
    the candidate's stable signature, its rank position, and a score.
    Downstream amendments may extend; Sub-1 holds the floor."""
    layout_signature: str
    rank_position: int           # 1-indexed; 1 == top
    score: float                 # ranker score, may be inf/-inf at fallback
    selection_marker: bool       # True iff this candidate was the chosen one

    def __post_init__(self) -> None:
        if self.rank_position < 1:
            raise C16ConfigurationError(
                f"CandidateRanking.rank_position must be ≥ 1, "
                f"got {self.rank_position}",
                offending_field="rank_position",
                offending_value=self.rank_position,
            )
        if not self.layout_signature:
            raise C16ConfigurationError(
                "CandidateRanking.layout_signature must be non-empty",
                offending_field="layout_signature",
                offending_value=self.layout_signature,
            )


@dataclass(frozen=True)
class HumanOverrideRecord:
    """Populated iff a human chose a layout other than the ranker's top.

    The selector emits this; C16 records it on audit_metadata so the
    full audit trail is preserved without polluting the canonical
    replay identity."""
    chosen_layout_signature:    str
    overridden_layout_signature: str
    override_reason:            str        # free text; spec deliberately loose
    overrider_actor_id:         Optional[str] = None

    def __post_init__(self) -> None:
        if self.chosen_layout_signature == self.overridden_layout_signature:
            raise C16ConfigurationError(
                "HumanOverrideRecord: chosen == overridden — that's not "
                "an override, that's agreement with the ranker.",
                offending_field="chosen_layout_signature",
                offending_value=self.chosen_layout_signature,
            )


@dataclass(frozen=True)
class SelectionReplayIdentity:
    """Fields that DO contribute to byte-equal replay (Inv R7).

    Per v0.3 A1: NO timestamps, NO env, NO human IDs here — those go
    into SelectionAuditMetadata so canonical_replay_signature stays
    drift-free across selector replays.
    """
    selected_layout_signature: str
    selector_version:          str
    selection_reason:          SelectionReason
    candidate_ranking_snapshot: tuple[CandidateRanking, ...]
    upstream_problem_reports:   tuple[ProblemReport, ...]

    def __post_init__(self) -> None:
        if not self.selected_layout_signature:
            raise C16ConfigurationError(
                "SelectionReplayIdentity.selected_layout_signature must be non-empty",
                offending_field="selected_layout_signature",
                offending_value=self.selected_layout_signature,
            )
        if not self.selector_version:
            raise C16ConfigurationError(
                "SelectionReplayIdentity.selector_version must be non-empty",
                offending_field="selector_version",
                offending_value=self.selector_version,
            )
        # The selected_layout_signature MUST appear in the ranking snapshot
        # with selection_marker=True (otherwise the selection record is
        # inconsistent with the ranking it claims to operate over).
        if self.candidate_ranking_snapshot:
            markers = [c for c in self.candidate_ranking_snapshot
                       if c.selection_marker]
            if len(markers) != 1:
                raise C16ConfigurationError(
                    f"SelectionReplayIdentity: ranking snapshot must contain "
                    f"exactly one entry with selection_marker=True, "
                    f"got {len(markers)}",
                    offending_field="candidate_ranking_snapshot",
                    offending_value=len(markers),
                )
            if markers[0].layout_signature != self.selected_layout_signature:
                raise C16ConfigurationError(
                    f"SelectionReplayIdentity: selected_layout_signature "
                    f"{self.selected_layout_signature!r} does not match "
                    f"marked candidate {markers[0].layout_signature!r}",
                    offending_field="selected_layout_signature",
                    offending_value=self.selected_layout_signature,
                )


@dataclass(frozen=True)
class SelectionAuditMetadata:
    """Fields that DO NOT contribute to byte-equal replay (Inv R7d).

    Timestamps, machine fingerprints, human override records — these
    are for traceability/forensics only. Excluded from
    canonical_replay_signature and cache keys.
    """
    selection_timestamp_utc:       str
    human_override:                Optional[HumanOverrideRecord] = None
    selector_instance_id:          Optional[str] = None
    selection_machine_fingerprint: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.selection_timestamp_utc:
            raise C16ConfigurationError(
                "SelectionAuditMetadata.selection_timestamp_utc must be non-empty "
                "(ISO 8601). Stamp at selection time, not at C16-render time.",
                offending_field="selection_timestamp_utc",
                offending_value=self.selection_timestamp_utc,
            )


@dataclass(frozen=True)
class SelectionResult:
    """Top-level upstream → C16 contract for what is being rendered.

    Per v0.3 A1: cache-relevant fields live on `replay_identity`;
    forensics live on `audit_metadata`. C16 derives cache keys ONLY
    from replay_identity.
    """
    replay_identity: SelectionReplayIdentity
    audit_metadata:  SelectionAuditMetadata


# ============================================================
# § 2 — AUTHORITY / PROVENANCE (v0.2 A5)
# ============================================================

class AuthorityKind(Enum):
    """Provenance discipline for ComplianceAttestation fields (R22).

    UPSTREAM_AUTHORITATIVE
        Value originated at an upstream component; C16 re-states it
        byte-identically. MUST carry non-empty upstream_source.
    LOCALLY_DERIVED
        Value computed in C16 from upstream inputs via pure arithmetic
        reformatting (e.g. ratio of two upstream values).
        NO independent compliance logic. MUST carry non-empty
        derivation_note and upstream_source=None.
    CROSS_CHECK_VERIFICATION
        Value computed locally AS A CHECK against an
        upstream-authoritative value of the same quantity. If they
        disagree beyond tolerance, raise ComplianceProvenanceError.
    """
    UPSTREAM_AUTHORITATIVE   = "upstream_authoritative"
    LOCALLY_DERIVED          = "locally_derived"
    CROSS_CHECK_VERIFICATION = "cross_check_verification"


# Value types acceptable in AttestedValue.value (R22 type guard).
_ATTESTED_VALUE_TYPES: Final[tuple[type, ...]] = (float, int, bool)


@dataclass(frozen=True)
class AttestedValue:
    """Every field of ComplianceAttestation is wrapped in one of these.

    Enforces R22 at __post_init__:
      - UPSTREAM_AUTHORITATIVE  → upstream_source non-empty,
                                  derivation_note is None
      - LOCALLY_DERIVED         → derivation_note non-empty,
                                  upstream_source is None
      - CROSS_CHECK_VERIFICATION→ BOTH non-empty (it's a comparison
                                  of a local derivation against an
                                  upstream-authoritative value)
    """
    value:           Union[float, int, bool]
    authority:       AuthorityKind
    upstream_source: Optional[str] = None
    derivation_note: Optional[str] = None

    def __post_init__(self) -> None:
        # Runtime type guard — Python erases unions at runtime.
        # NB: in Python, bool is a subclass of int, so isinstance(x, int)
        # is True for bools; that's fine here — we accept all three.
        if not isinstance(self.value, _ATTESTED_VALUE_TYPES):
            raise C16ConfigurationError(
                f"AttestedValue.value must be float | int | bool, "
                f"got {type(self.value).__name__}",
                offending_field="value",
                offending_value=self.value,
            )

        if self.authority is AuthorityKind.UPSTREAM_AUTHORITATIVE:
            if not self.upstream_source:
                raise ComplianceProvenanceError(
                    "AttestedValue UPSTREAM_AUTHORITATIVE requires non-empty "
                    "upstream_source",
                    invariant_id="R22",
                    authority_observed=self.authority.value,
                )
            if self.derivation_note is not None:
                raise ComplianceProvenanceError(
                    "AttestedValue UPSTREAM_AUTHORITATIVE must have "
                    "derivation_note=None (no local derivation involved)",
                    invariant_id="R22",
                    authority_observed=self.authority.value,
                )
        elif self.authority is AuthorityKind.LOCALLY_DERIVED:
            if not self.derivation_note:
                raise ComplianceProvenanceError(
                    "AttestedValue LOCALLY_DERIVED requires non-empty "
                    "derivation_note explaining the arithmetic",
                    invariant_id="R22",
                    authority_observed=self.authority.value,
                )
            if self.upstream_source is not None:
                raise ComplianceProvenanceError(
                    "AttestedValue LOCALLY_DERIVED must have "
                    "upstream_source=None (it's derived, not received)",
                    invariant_id="R22",
                    authority_observed=self.authority.value,
                )
        else:  # CROSS_CHECK_VERIFICATION
            if not self.upstream_source:
                raise ComplianceProvenanceError(
                    "AttestedValue CROSS_CHECK_VERIFICATION requires "
                    "non-empty upstream_source (the value being cross-checked)",
                    invariant_id="R22",
                    authority_observed=self.authority.value,
                )
            if not self.derivation_note:
                raise ComplianceProvenanceError(
                    "AttestedValue CROSS_CHECK_VERIFICATION requires "
                    "non-empty derivation_note (the local computation)",
                    invariant_id="R22",
                    authority_observed=self.authority.value,
                )


# ============================================================
# § 3 — COORDINATE FRAMES (v0.3 A4)
# ============================================================

@dataclass(frozen=True)
class LocalBuildingFrame:
    """Building-aligned orthogonal coordinate frame.

    Origin: SW corner of the BUILDING footprint (NOT the plot).
    +X axis: chosen per the deterministic hierarchy in v0.4 A4 / R29.
    +Y axis: perpendicular to +X, right-hand rule.
    +Z axis: Up.

    Marker type. The convention IS the type contract — instances of
    this class carry no fields; their presence in a bundle declares
    'this geometry follows the LocalBuildingFrame convention'.
    """
    # NOTE: deliberately empty — see docstring.
    # frozen=True + no fields = singleton-equivalent marker.


@dataclass(frozen=True)
class GeospatialReference:
    """Locates the LocalBuildingFrame in real-world geography.

    Per v0.3 A4 + v0.4 A4 (orientation hierarchy outcome).
    """
    local_origin_in_plot_mm:        tuple[int, int]
    """(east_offset, north_offset) from plot SW corner."""

    rotation_from_plot_north_deg:   float
    """CCW positive. 0 means LocalBuildingFrame +Y is aligned with plot North."""

    plot_north_arrow_orientation_deg: float
    """Plot's +Y axis vs true North (from C4)."""

    orientation_basis: Literal[
        "explicit_hint", "primary_entrance", "longest_wall", "lex_fallback"
    ]
    """Per R29b — WHICH hierarchy step fired. Always populated."""

    # Optional geospatial coordinates (WGS-84 datum assumed if present)
    geospatial_latitude:   Optional[float] = None
    geospatial_longitude:  Optional[float] = None
    geospatial_elevation_m: Optional[float] = None

    def __post_init__(self) -> None:
        # Range checks
        if not (0.0 <= self.rotation_from_plot_north_deg < 360.0):
            raise C16ConfigurationError(
                f"GeospatialReference.rotation_from_plot_north_deg must be "
                f"in [0, 360), got {self.rotation_from_plot_north_deg}",
                offending_field="rotation_from_plot_north_deg",
                offending_value=self.rotation_from_plot_north_deg,
            )
        if not (0.0 <= self.plot_north_arrow_orientation_deg < 360.0):
            raise C16ConfigurationError(
                f"GeospatialReference.plot_north_arrow_orientation_deg must "
                f"be in [0, 360), got {self.plot_north_arrow_orientation_deg}",
                offending_field="plot_north_arrow_orientation_deg",
                offending_value=self.plot_north_arrow_orientation_deg,
            )
        # Lat/Lng sanity if present (WGS-84 ranges)
        if self.geospatial_latitude is not None and not (
            -90.0 <= self.geospatial_latitude <= 90.0
        ):
            raise C16ConfigurationError(
                f"GeospatialReference.geospatial_latitude must be in "
                f"[-90, 90], got {self.geospatial_latitude}",
                offending_field="geospatial_latitude",
                offending_value=self.geospatial_latitude,
            )
        if self.geospatial_longitude is not None and not (
            -180.0 <= self.geospatial_longitude <= 180.0
        ):
            raise C16ConfigurationError(
                f"GeospatialReference.geospatial_longitude must be in "
                f"[-180, 180], got {self.geospatial_longitude}",
                offending_field="geospatial_longitude",
                offending_value=self.geospatial_longitude,
            )


# ============================================================
# § 4 — ORIENTATION LOCK (v0.5 A5)
# ============================================================

@dataclass(frozen=True)
class OrientationLock:
    """Optional persistence of LocalBuildingFrame orientation across
    architectural revisions (so semantic_identity_hashes don't break
    when someone moves the main door).

    Per R29d: when present, C16 honors this orientation AFTER a
    plausibility check against the four hierarchy candidates computed
    from CURRENT geometry. That plausibility check happens in Phase α
    (envelope assembly), NOT in this dataclass — at construction we
    only validate the lock's OWN fields are well-formed.
    """
    locked_at_first_publish:        bool
    locked_x_axis_orientation_deg:  float
    locked_origin_basis: Literal[
        "explicit_hint", "primary_entrance", "longest_wall", "lex_fallback"
    ]
    lock_provenance:                str

    def __post_init__(self) -> None:
        if not (0.0 <= self.locked_x_axis_orientation_deg < 360.0):
            raise C16ConfigurationError(
                f"OrientationLock.locked_x_axis_orientation_deg must be "
                f"in [0, 360), got {self.locked_x_axis_orientation_deg}",
                offending_field="locked_x_axis_orientation_deg",
                offending_value=self.locked_x_axis_orientation_deg,
            )
        if not self.lock_provenance:
            raise C16ConfigurationError(
                "OrientationLock.lock_provenance must be non-empty "
                "(free-text reason / project-stage identifier)",
                offending_field="lock_provenance",
                offending_value=self.lock_provenance,
            )


# ============================================================
# § 5 — JURISDICTION (v0.2 A1 baseline + v0.5 A4)
# ============================================================

@dataclass(frozen=True)
class JurisdictionProfile:
    """The jurisdiction-specific permit rules C16 reads.

    v1 ships ONLY 'tn_cdbr_2019'. The shape includes hooks for future
    multi-jurisdiction expansion (B-C16-MULTI-JURISDICTION-PROFILES).

    Per v0.5 A4 / R31b — declared_domain_scope is enum-enforced.
    """
    jurisdiction_id:          str
    declared_domain_scope:    Literal[
        "residential_v1", "small_commercial_v1", "mixed_use_v1"
    ] = "residential_v1"

    # Optional explicit hint for LocalBuildingFrame orientation (R29 step 1)
    local_x_axis_orientation_deg_hint: Optional[float] = None

    # Optional orientation lock (R29d / v0.5 A5)
    orientation_lock: Optional[OrientationLock] = None

    def __post_init__(self) -> None:
        if self.jurisdiction_id not in SUPPORTED_JURISDICTIONS:
            from buildemup.components.c16.errors import (
                JurisdictionNotSupportedError,
            )
            raise JurisdictionNotSupportedError(
                f"Jurisdiction {self.jurisdiction_id!r} is not in "
                f"SUPPORTED_JURISDICTIONS. v1 ships only TNCDBR.",
                requested_jurisdiction=self.jurisdiction_id,
                supported=SUPPORTED_JURISDICTIONS,
            )
        if self.declared_domain_scope not in SUPPORTED_DOMAIN_SCOPES:
            raise C16ConfigurationError(
                f"JurisdictionProfile.declared_domain_scope must be one of "
                f"{sorted(SUPPORTED_DOMAIN_SCOPES)}, "
                f"got {self.declared_domain_scope!r}. (R31b)",
                offending_field="declared_domain_scope",
                offending_value=self.declared_domain_scope,
            )
        if self.local_x_axis_orientation_deg_hint is not None:
            v = self.local_x_axis_orientation_deg_hint
            if not (0.0 <= v < 360.0):
                raise C16ConfigurationError(
                    f"JurisdictionProfile.local_x_axis_orientation_deg_hint "
                    f"must be in [0, 360) when present, got {v}",
                    offending_field="local_x_axis_orientation_deg_hint",
                    offending_value=v,
                )


# ============================================================
# § 6 — STATUS ENUMS (v0.4 A5 — orthogonal split)
# ============================================================

class LegalCompleteness(Enum):
    """Pure legal/governance status — independent of rendering quality.
    Per R30a: derives ONLY from UPSTREAM_AUTHORITATIVE values +
    permit-critical overlay presence."""
    LEGALLY_COMPLETE       = "legally_complete"
    LEGALLY_INCOMPLETE     = "legally_incomplete"
    UNSAFE_FOR_SUBMISSION  = "unsafe_for_submission"


class ReadabilityStatus(Enum):
    """Pure presentation-quality status — renderer/viewport dependent.
    Per R30b: derives from ReadabilityDiagnostics. Independent of
    legal status."""
    READABLE              = "readable"
    REVIEW_RECOMMENDED    = "review_recommended"
    READABILITY_DEGRADED  = "readability_degraded"


# ============================================================
# § 7 — ELEMENT TAXONOMY (v0.2 A7)
# ============================================================

class ElementKind(Enum):
    """Semantic taxonomy for every renderable element.
    BIM-forward: maps cleanly to IFC IfcWall / IfcDoor / IfcColumn /
    IfcCovering etc. when the export backlog item ships post-v1.

    Per R9: adding new kinds is a MINOR schema bump.
    Removing/renaming is MAJOR."""
    # Walls
    WALL_EXTERNAL                 = "wall_external"
    WALL_INTERNAL_LOAD_BEARING    = "wall_internal_load_bearing"
    WALL_INTERNAL_PARTITION       = "wall_internal_partition"
    WALL_PARAPET                  = "wall_parapet"

    # Openings
    DOOR_EXTERNAL                 = "door_external"
    DOOR_INTERNAL                 = "door_internal"
    WINDOW_EXTERNAL               = "window_external"
    WINDOW_VENTILATOR             = "window_ventilator"

    # Structural
    COLUMN                        = "column"
    BEAM                          = "beam"
    SLAB_FLOOR                    = "slab_floor"
    SLAB_ROOF                     = "slab_roof"

    # Plumbing
    PLUMBING_STACK_FRESH_WATER    = "plumbing_stack_fresh_water"
    PLUMBING_STACK_WASTE          = "plumbing_stack_waste"
    PLUMBING_STACK_RAIN_WATER     = "plumbing_stack_rain_water"

    # Compliance overlays
    SETBACK_MARKER                = "setback_marker"
    FAR_ANNOTATION                = "far_annotation"
    PARKING_BAY                   = "parking_bay"
    RWH_FACILITY                  = "rwh_facility"
    SEWAGE_FACILITY               = "sewage_facility"


# ============================================================
# § 8 — CHECK PROVENANCE (v0.1 § 1.3)
# ============================================================

@dataclass(frozen=True)
class CheckProvenance:
    """Trace from a ComplianceAttestation field back to the upstream
    CheckResult that originated it. Required by Inv R15 for every
    compliance claim on PermitDrawingModel."""
    upstream_component:  str          # e.g. "c2_feasibility"
    check_id:            str          # e.g. "parking_width_feasibility"
    upstream_version:    str          # e.g. "v1.0"
    attested_field_name: str          # the field on ComplianceAttestation

    def __post_init__(self) -> None:
        for fname, fval in (
            ("upstream_component",  self.upstream_component),
            ("check_id",            self.check_id),
            ("upstream_version",    self.upstream_version),
            ("attested_field_name", self.attested_field_name),
        ):
            if not fval:
                raise C16ConfigurationError(
                    f"CheckProvenance.{fname} must be non-empty",
                    offending_field=fname,
                    offending_value=fval,
                )
