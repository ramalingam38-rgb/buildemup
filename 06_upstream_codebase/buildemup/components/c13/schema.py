"""
BuildemUp — Component 13 — schema (output + input dataclasses)
===============================================================

Per C13 SPEC v1.0 LOCKED. Composed from:
- v0.1 § 2 (Door, base output schema)
- v0.2 A3 (hinge_side, leaf_thickness)
- v0.2 A6 (D9' bathroom outswing semantics)
- v0.3 B2 (AdvisoryFlag dataclass)
- v0.3 B4 (geometric_fidelity tier)
- v0.3 B8 (RoomDoorPreference for secondary doors)
- v0.3 B11 (typestate API: SuccessfulDoorPlacement vs FailedDoorPlacement)
- v0.4 C1 (AdvisoryCategory enum + density / deduplication)
- v0.4 C4 (MAX_DOORS_PER_ROOM_V1 + secondary-door eligibility)
- v0.4 C6 (GeometricFidelity enum renaming Tier 1/2/3)
- v0.4 C9 (secondary-door graph semantics)
- v0.4 C10 (C13CacheKeys split into geometry / advisory / full)
- v0.5 D7 (advisory_cache_key contains geometry_cache_key prefix — Inv D18)
- v0.6 E1 (ConditionalLegalityViolation provenance — Inv D19)
- v0.6 E3 (AdvisoryFlag.causal_context reserved field)
- v0.7 F2 (CausalContext semantic intent docstring)

All dataclasses are frozen for hash-stability + replay determinism
(Inv D7). Canonical orderings are enforced in __post_init__ throughout
(per Inv D8 for door tuples, plus various sub-invariants).

Per v0.3 B11: C13 uses a typestate-discriminated union
(SuccessfulDoorPlacement vs FailedDoorPlacement) rather than C12's
mixed-result pattern. This is intentional architectural inconsistency
with C12 — the migration of older components to typestate is filed as
B-PROJECT-PIPELINE-CONVENTION-CONSOLIDATION (v2+).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Literal, Optional


# =============================================================================
# Habitable / secondary-door category sets (per v0.4 C4 + v0.5 D6)
# =============================================================================

HABITABLE_ROOM_CATEGORIES: Final[frozenset[str]] = frozenset({
    "bedroom",
    "master_bedroom",
    "guest_bedroom",
    "living",
    "dining",
    "kitchen",
    "pooja",
    "study",
})
"""Per v0.5 D6. Categories whose rooms must be reachable from main_entry
via the PRIMARY-door-induced graph (Inv D17). Non-habitable rooms
(bathroom, utility, store, servant, balcony) may be reachable via
secondary doors only."""


SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1: Final[frozenset[str]] = frozenset({
    "living",          # primary social + secondary to utility/balcony
    "kitchen",         # primary corridor + secondary to utility
    "utility",         # primary kitchen + secondary external
    "main_entrance",   # primary external + secondary internal (foyer)
})
"""Per v0.4 C4. Room categories eligible for secondary doors at v1.

Bedrooms / bathrooms / pooja are EXCLUDED (privacy concern). Luxury
master suite multi-door is B-C13-MULTI-DOOR-BEDROOM-OVERRIDE (v1.x)."""


# =============================================================================
# AdvisoryCategory enum (per v0.4 C1)
# =============================================================================

class AdvisoryCategory(Enum):
    """Per C13 v0.4 C1. Coarse categorization of AdvisoryFlag concerns
    for density-bound enforcement (Inv D16) and downstream C14
    consumption.

    Values:
      ERGONOMIC: corner-too-close, narrow-clearance, swing-blocks-furniture
      PRIVACY: sight-line concerns (sub-C14 hints)
      CIRCULATION: through-private, long-corridor, through-kitchen-when-avoidable
      EMERGENCY: outswing-blocks-egress, narrow-emergency-clearance
      NBC_BORDERLINE: door width within 5% of NBC minimum (advisory floor)

    Per v0.4 C1 deduplication rule: ≤ 1 flag per (room_id, category)
    tuple. Future v1.x category-specific density caps filed as
    B-C13-CATEGORY-SPECIFIC-DENSITY-CAPS.
    """
    ERGONOMIC = "ergonomic"
    PRIVACY = "privacy"
    CIRCULATION = "circulation"
    EMERGENCY = "emergency"
    NBC_BORDERLINE = "nbc_borderline"


# =============================================================================
# GeometricFidelity enum (per v0.4 C6, renames v0.3 B4 Tier 1/2/3)
# =============================================================================

class GeometricFidelity(Enum):
    """Per C13 v0.4 C6 (renames v0.3 B4 numeric tiers semantically).

    Three fidelity tiers:

    APPROXIMATE (v1.0 LOCKED): simplified swept arc + hinge + leaf
        thickness. Does NOT model frame projection, handle clearance,
        door-stop hardware, perpendicular-wall truncation. Per v0.4 C6
        mandatory disclosure rule: any user-facing presentation MUST
        display "approximate placement — final dimensions require
        architect verification" (or equivalent) — C15 UX layer
        enforces this disclosure.

    ARCHITECTURAL (v1.x via B-C13-FRAME-DEPTH-MODELING): adds frame
        projection + wall-thickness reveal. Activated when C7 grid
        integration provides column-aligned frame depths.

    HIGH_FIDELITY (v2+ via B-C13-FULL-3D-SWING-MODEL): adds handle
        clearance, door-stop, perpendicular truncation. Activated
        when user-facing 3D rendering needs accurate swing
        visualization.

    Inv D14: every Door carries geometric_fidelity. v1.0 default:
    APPROXIMATE.
    """
    APPROXIMATE = "approximate"
    ARCHITECTURAL = "architectural"
    HIGH_FIDELITY = "high_fidelity"


# =============================================================================
# AdvisoryFlag flag_kind literal set (per v0.3 B2 + v0.4 C8)
# =============================================================================

# Per v0.3 B2: explicit Literal vocabulary of advisory kinds emitted by
# C13. Per v0.4 C8 ADVISORY_SCHEMA_VERSION: this set is FROZEN at v1.0
# LOCK. Adding values requires MINOR bump; renaming/removing requires
# MAJOR. v1.0 ships 6 flag kinds.
AdvisoryFlagKind = Literal[
    "through_private_routing",
    "through_bathroom_routing",
    "through_pooja_routing",
    "long_corridor_route",
    "minimal_clearance_door",
    "bathroom_outswing_emergency_clearance",
]


_ADVISORY_FLAG_KIND_VALUES: Final[frozenset[str]] = frozenset({
    "through_private_routing",
    "through_bathroom_routing",
    "through_pooja_routing",
    "long_corridor_route",
    "minimal_clearance_door",
    "bathroom_outswing_emergency_clearance",
})
"""Runtime-checkable mirror of AdvisoryFlagKind. The runtime check is
necessary because typing.Literal isn't introspectable on all Python
versions. Locked at v1.0; changes require ADVISORY_SCHEMA_VERSION bump."""


AdvisorySeverity = Literal["info", "warning", "concern"]
"""Per v0.4 C1 severity calibration:
- info:    ergonomic preference unmet (e.g., corner offset = 0)
- warning: noticeable quality concern (e.g., long-corridor routing)
- concern: significant deviation requiring C14 attention (e.g.,
           bathroom emergency-clearance compromise)
"""


# =============================================================================
# CausalContext (per v0.6 E3 reserved field + v0.7 F2 semantic intent)
# =============================================================================

@dataclass(frozen=True)
class CausalContext:
    """Reserved at v1.0; populators in v1.x.

    SEMANTIC INTENT (LOCKED at v1.0 per v0.7 F2, even though fields
    are not):

    'causal_context explains WHY the advisory existed in the final
    door placement state.'

    Specifically, a populated causal_context answers:
      - What constraint forced the compromise that triggered this
        advisory?
      - What alternative was considered + why was it rejected?
      - Was the advisory unavoidable (architectural) vs avoidable
        (local minimum)?

    NOT for:
      - Mutation history (different concept; reserved separately if
        ever needed)
      - Optimization rationale (C14 territory)
      - User-facing explanations (C15 territory)

    v1.x candidate fields (NOT shipped at v1.0):
      - originating_constraint_id: str
      - alternatives_considered: tuple[str, ...]
      - forced_compromise_reason: Literal[...]

    Any v1.x populator that violates this semantic intent is a spec
    violation, not just a schema bump.

    Inv D20: causal_context defaults to None at v1.0; non-None values
    are forward-compat data only. Per v0.6 E3 forward-compat
    reservation.
    """
    # Empty sentinel body at v1.0. Frozen dataclass with no fields is
    # legal in Python 3.10+ and provides a stable hash + equality.


# =============================================================================
# AdvisoryFlag (per v0.3 B2 + v0.4 C1 + v0.6 E3)
# =============================================================================

@dataclass(frozen=True)
class AdvisoryFlag:
    """Per C13 v0.3 B2 (initial) + v0.4 C1 (category, severity,
    deduplication, density bounds) + v0.6 E3 (causal_context reserved).

    Soft signal from C13 to C14. Not actioned at C13 — C13 emits these
    annotations into DoorPlacementResult.advisory_flags; C14 decides
    whether to weight them in circulation scoring, sight-line analysis,
    privacy gradient, etc.

    Per v0.3 B2 boundary: AdvisoryFlags REPLACE v0.2's hard D11 invariant
    ("no door routes through bedroom/bathroom"). They preserve the
    pathology-detection without over-constraining compact Indian
    typologies (mezzanine/staircase through sleeping spaces is
    legitimate in some cases).

    Fields:
      flag_kind: one of the 6 LOCKED kinds (Literal). New kinds
          require ADVISORY_SCHEMA_VERSION MINOR bump (additive).
      affected_room_id: room_id this advisory pertains to.
      category: coarse classification for density-bound enforcement
          (Inv D16).
      severity: info | warning | concern (per v0.4 C1 calibration).
      explanation_template: human-readable explanation key — C15 UX
          layer interpolates with affected_room_id + other context.
      deduplication_key: (room_id, category) pair as a string key.
          Per Inv D16: at most one flag per (room_id, category) tuple.
      causal_context: Optional[CausalContext] (per v0.6 E3 reserved).
          v1.0 default: None. v1.x populators forward-compat per
          v0.7 F2 semantic intent docstring.

    Per Inv D16: AdvisoryFlag density bound ≤ n_rooms × 1.5;
    deduplicated per (room, category). Enforced by orchestrator at
    Phase E assembly (not at this dataclass level — multiple flags
    can be constructed validly; assembly verifies bounds).
    """
    flag_kind: AdvisoryFlagKind
    affected_room_id: str
    category: AdvisoryCategory
    severity: AdvisorySeverity
    explanation_template: str
    deduplication_key: str
    causal_context: Optional[CausalContext] = None

    def __post_init__(self) -> None:
        # Runtime check of flag_kind (Literal isn't enforced at runtime).
        if self.flag_kind not in _ADVISORY_FLAG_KIND_VALUES:
            raise ValueError(
                f"AdvisoryFlag.flag_kind must be one of "
                f"{sorted(_ADVISORY_FLAG_KIND_VALUES)!r}; "
                f"got {self.flag_kind!r}."
            )
        if not self.affected_room_id:
            raise ValueError("AdvisoryFlag.affected_room_id must be non-empty.")
        if self.severity not in ("info", "warning", "concern"):
            raise ValueError(
                f"AdvisoryFlag.severity must be 'info' / 'warning' / "
                f"'concern'; got {self.severity!r}."
            )
        if not self.explanation_template:
            raise ValueError(
                "AdvisoryFlag.explanation_template must be non-empty."
            )
        if not self.deduplication_key:
            raise ValueError(
                "AdvisoryFlag.deduplication_key must be non-empty."
            )


# =============================================================================
# Door (per v0.1 § 2.1 + v0.2 A3 + v0.4 C6)
# =============================================================================

@dataclass(frozen=True)
class Door:
    """One door realized on a shared edge.

    Per C13 SPEC v1.0 § 2 (composed):
    - v0.1 § 2.1 base: room ids, axis, position, clear_width,
      swing_direction, is_main_entry
    - v0.2 A3: hinge_side + leaf_thickness_m (resolves swing-arc
      geometry ambiguity per Inv D7)
    - v0.4 C6: geometric_fidelity enum (renames v0.3 B4 numeric tier)

    Canonical ordering: (room_a_id, room_b_id) lex-ASC. The room ids
    match the SharedEdge this door sits on (which is itself
    canonically room_a_id < room_b_id per C12 invariant).

    Per Inv D7 (byte-equal replay): hinge_side + swing_direction
    together fully determine the swing-arc geometry. position +
    clear_width + leaf_thickness complete the planar door
    representation.

    Per Inv D14 (geometric_fidelity): every Door carries the fidelity
    tier — v1.0 always APPROXIMATE; v1.x may ship ARCHITECTURAL via
    B-C13-FRAME-DEPTH-MODELING.

    Inv enforcement (D4 / D10 in __post_init__):
    - Inv D4: position + clear_width must fit within edge (enforced at
      assembly time when edge length is known; not at dataclass level).
    - Inv D10: clear_width_m ≤ 1.5m sanity bound (enforced here).
    - Inv D3: clear_width_m ≥ edge.min_required_clear_width_m
      (enforced at assembly with edge context).
    - Positivity: position ≥ 0, clear_width > 0, leaf_thickness > 0.
    """
    room_a_id: str
    room_b_id: str
    axis: Literal["vertical", "horizontal"]
    position_along_edge_m: float
    clear_width_m: float
    swing_direction: Literal["into_room_a", "into_room_b"]
    hinge_side: Literal["start", "end"]
    leaf_thickness_m: float
    is_main_entry: bool
    geometric_fidelity: GeometricFidelity

    def __post_init__(self) -> None:
        if not self.room_a_id or not self.room_b_id:
            raise ValueError(
                "Door requires non-empty room_a_id and room_b_id."
            )
        if self.room_a_id >= self.room_b_id:
            raise ValueError(
                f"Door requires canonical order room_a_id < room_b_id; "
                f"got {self.room_a_id!r} vs {self.room_b_id!r}."
            )
        if self.axis not in ("vertical", "horizontal"):
            raise ValueError(
                f"Door.axis must be 'vertical' or 'horizontal'; "
                f"got {self.axis!r}."
            )
        if self.swing_direction not in ("into_room_a", "into_room_b"):
            raise ValueError(
                f"Door.swing_direction must be 'into_room_a' or "
                f"'into_room_b'; got {self.swing_direction!r}."
            )
        if self.hinge_side not in ("start", "end"):
            raise ValueError(
                f"Door.hinge_side must be 'start' or 'end'; "
                f"got {self.hinge_side!r}."
            )
        if self.position_along_edge_m < 0.0:
            raise ValueError(
                f"Door.position_along_edge_m must be >= 0; "
                f"got {self.position_along_edge_m}."
            )
        if self.clear_width_m <= 0.0:
            raise ValueError(
                f"Door.clear_width_m must be positive; "
                f"got {self.clear_width_m}."
            )
        # Inv D10 — sanity bound at v1.
        if self.clear_width_m > 1.5:
            raise ValueError(
                f"Door.clear_width_m violates Inv D10 sanity bound "
                f"(<= 1.5m at v1); got {self.clear_width_m}."
            )
        if self.leaf_thickness_m <= 0.0:
            raise ValueError(
                f"Door.leaf_thickness_m must be positive; "
                f"got {self.leaf_thickness_m}."
            )


# =============================================================================
# RoomDoorPreference (per v0.3 B8 + v0.4 C4)
# =============================================================================

SecondaryDoorPreferenceKind = Literal["none", "corridor", "utility", "external"]


@dataclass(frozen=True)
class RoomDoorPreference:
    """Per-room door cardinality hints. Caller-specified, never
    heuristically derived at v1.0.

    Per v0.3 B8 + v0.4 C4. Heuristic-driven multi-door (no caller input
    required) is filed as B-C13-AUTO-MULTI-DOOR (v1.x or v2+).

    Fields:
      room_id: which room this preference applies to.
      min_doors: minimum doors required for this room (default 1).
      max_doors: maximum doors permitted (default 1; HARD cap of
          MAX_DOORS_PER_ROOM_V1 = 2 at v1).
      secondary_door_preference: hint for secondary door edge
          selection. 'none' = no preference; default.

    Per Inv D1' (v0.3 B8 + v0.4 C4 strengthened): each room has
    min_doors ≤ doors ≤ max_doors, where max_doors ≤ MAX_DOORS_PER_ROOM_V1
    at v1.

    Per v0.4 C4 prohibitions at v1:
    - max_doors > 2 → C13ConfigurationError
    - secondary doors on bedrooms/bathrooms/pooja → not enforced at
      this dataclass level (Phase A enforces against
      SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1)
    """
    room_id: str
    min_doors: int = 1
    max_doors: int = 1
    secondary_door_preference: SecondaryDoorPreferenceKind = "none"

    def __post_init__(self) -> None:
        if not self.room_id:
            raise ValueError("RoomDoorPreference.room_id must be non-empty.")
        if self.min_doors < 1:
            raise ValueError(
                f"RoomDoorPreference.min_doors must be >= 1; "
                f"got {self.min_doors}."
            )
        if self.max_doors < self.min_doors:
            raise ValueError(
                f"RoomDoorPreference.max_doors ({self.max_doors}) must be "
                f">= min_doors ({self.min_doors})."
            )
        # Inv D1' v1 hard cap.
        if self.max_doors > 2:  # MAX_DOORS_PER_ROOM_V1 inlined to avoid cycle
            raise ValueError(
                f"RoomDoorPreference.max_doors violates v1 hard cap "
                f"(MAX_DOORS_PER_ROOM_V1 = 2); got {self.max_doors}. "
                f"Luxury multi-door bedrooms: file under "
                f"B-C13-MULTI-DOOR-BEDROOM-OVERRIDE."
            )
        if self.secondary_door_preference not in (
            "none", "corridor", "utility", "external",
        ):
            raise ValueError(
                f"RoomDoorPreference.secondary_door_preference invalid; "
                f"got {self.secondary_door_preference!r}."
            )


# =============================================================================
# C13CacheKeys (per v0.4 C10 + v0.5 D7 — Inv D18 prefix rule)
# =============================================================================

# Per v0.5 D7: advisory_cache_key is constructed as
#   geometry_cache_key + SEPARATOR + advisory_payload_hash
# so the prefix relationship is literally testable via startswith().
# Per v0.5 D7 commentary: "Replay of advisories against mismatched
# geometry is impossible."
#
# The separator value is owned by `cache_keys.py` (the sole module that
# constructs cache keys). The C13CacheKeys dataclass only validates the
# prefix relationship via `startswith()`, which is separator-agnostic.


@dataclass(frozen=True)
class C13CacheKeys:
    """Per C13 v0.4 C10 (cache domain split) + v0.5 D7 (D18 prefix rule).

    Three cache keys derived from C13 inputs:

    - geometry_cache_key: hash of door positions, hinges, swings, widths.
      Stable across advisory recalibrations.
    - advisory_cache_key: hash of advisory flags. CONSTRAINED by Inv D18
      to contain geometry_cache_key as a prefix: a future advisory
      severity recalibration invalidates advisory_cache_key but
      preserves geometry_cache_key.
    - full_cache_key: hash of both — for full result replay.

    Per Inv D18 (LOCKED at v0.5 D7):
        advisory_cache_key.startswith(geometry_cache_key) MUST hold.

    Downstream (C14) consumers can optionally request "geometry-only
    replay" via the geometry key when only positioning is relevant.

    Cache-domain partitioning of config fields (per v0.4 C10):
    - Geometry domain: strict_mode, default_clear_width_m,
      corner_offset_m, max_conflict_resolution_iterations,
      secondary-door config.
    - Advisory domain: severity calibration, density bounds,
      category map.
    """
    geometry_cache_key: str
    advisory_cache_key: str
    full_cache_key: str

    def __post_init__(self) -> None:
        if not self.geometry_cache_key:
            raise ValueError("C13CacheKeys.geometry_cache_key must be non-empty.")
        if not self.advisory_cache_key:
            raise ValueError("C13CacheKeys.advisory_cache_key must be non-empty.")
        if not self.full_cache_key:
            raise ValueError("C13CacheKeys.full_cache_key must be non-empty.")
        # Inv D18: advisory_cache_key contains geometry_cache_key as prefix.
        if not self.advisory_cache_key.startswith(self.geometry_cache_key):
            raise ValueError(
                f"C13CacheKeys violates Inv D18: advisory_cache_key "
                f"must start with geometry_cache_key. "
                f"advisory_cache_key={self.advisory_cache_key!r}, "
                f"geometry_cache_key={self.geometry_cache_key!r}."
            )


# =============================================================================
# ConditionalLegalityViolation (per v0.6 E1 — Inv D19 provenance)
# =============================================================================

@dataclass(frozen=True)
class ConditionalLegalityViolation:
    """Per C13 v0.6 E1. Provenance attached to FailureRecord when a
    CONDITIONAL_LEGALITY invariant (D11.3' at v1) fires.

    Captures the alternative that was deemed "available" causing the
    violation, so the failure is reproducible + debuggable.

    Fields:
      invariant_id: which CONDITIONAL_LEGALITY invariant fired
          (e.g., "D11.3"). v1 ships only D11.3'; v1.x may add others.
      violated_path: room_id sequence describing the violating
          circulation path (e.g., for through-kitchen routing).
      alternative_path: room_id sequence describing the alternative
          path that triggered the veto (the path that made the
          violation conditional).
      alternative_path_length_grid_units: integer length of the
          alternative path in grid units, allowing objective
          comparison with the violated path's length.

    Inv D19: every D11.3' violation carries a ConditionalLegalityViolation
    provenance record. Stronger than C12's bare FailureRecord pattern.
    """
    invariant_id: str
    violated_path: tuple[str, ...]
    alternative_path: tuple[str, ...]
    alternative_path_length_grid_units: int

    def __post_init__(self) -> None:
        if not self.invariant_id:
            raise ValueError(
                "ConditionalLegalityViolation.invariant_id must be non-empty."
            )
        if len(self.violated_path) < 2:
            raise ValueError(
                f"ConditionalLegalityViolation.violated_path must contain "
                f">= 2 room_ids; got {self.violated_path!r}."
            )
        if len(self.alternative_path) < 2:
            raise ValueError(
                f"ConditionalLegalityViolation.alternative_path must "
                f"contain >= 2 room_ids; got {self.alternative_path!r}."
            )
        if self.alternative_path_length_grid_units <= 0:
            raise ValueError(
                f"ConditionalLegalityViolation."
                f"alternative_path_length_grid_units must be positive; "
                f"got {self.alternative_path_length_grid_units}."
            )


# =============================================================================
# FailureRecord (mirrors C12 pattern with C13-specific phase enum)
# =============================================================================

# Per C13 v0.7 F1: 6 algorithmic phases A-F. Phase F is PURE
# verification (per Inv D22). Phase A-E are selection / resolution
# layers. "phase0" denotes ingress (Phase 0 startup validation).
C13Phase = Literal[
    "phase0",   # ingress: schema-version probes, config validation
    "phaseA",   # per-room primary door selection
    "phaseB",   # swing direction assignment
    "phaseC",   # position-along-edge selection
    "phaseD",   # bounded CSP-lite conflict resolution
    "phaseE",   # canonical assembly + cache key generation
    "phaseF",   # pure verification (D11.3', D13, D17, D19)
]


@dataclass(frozen=True)
class FailureRecord:
    """Per-candidate failure under WARN mode. Mirrors C12.FailureRecord
    pattern but with C13-specific phase enum + optional
    ConditionalLegalityViolation provenance.

    Per v0.3 B11 typestate: FailureRecord is wrapped inside
    FailedDoorPlacement (not exposed in the successes tuple), which
    prevents downstream consumers from accidentally consuming
    invalid candidates as successful.

    Fields:
      candidate_signature: provenance back to the source PlacedCandidate.
      error_type: class name of the PerCandidatePlacementError that
          caused the failure (e.g., "SwingArcConflictError").
      error_message: the str() of the underlying exception.
      phase: which phase produced the failure (per C13Phase enum).
      conditional_legality_violation: per Inv D19 (v0.6 E1). Present
          ONLY when error_type == "ConditionalLegalityViolationError";
          None otherwise.
    """
    candidate_signature: str
    error_type: str
    error_message: str
    phase: C13Phase
    conditional_legality_violation: Optional[ConditionalLegalityViolation] = None

    def __post_init__(self) -> None:
        if not self.candidate_signature:
            raise ValueError(
                "FailureRecord.candidate_signature must be non-empty."
            )
        if not self.error_type:
            raise ValueError("FailureRecord.error_type must be non-empty.")
        # Inv D19 enforcement: provenance present iff error is
        # ConditionalLegalityViolationError.
        is_cond_legality = self.error_type == "ConditionalLegalityViolationError"
        has_provenance = self.conditional_legality_violation is not None
        if is_cond_legality and not has_provenance:
            raise ValueError(
                "FailureRecord violates Inv D19: "
                "ConditionalLegalityViolationError requires a "
                "conditional_legality_violation provenance record."
            )
        if has_provenance and not is_cond_legality:
            raise ValueError(
                f"FailureRecord: conditional_legality_violation provenance "
                f"present but error_type is {self.error_type!r}, not "
                f"'ConditionalLegalityViolationError'. Per Inv D19 the "
                f"provenance is reserved for CONDITIONAL_LEGALITY failures."
            )


# =============================================================================
# Typestate variants: SuccessfulDoorPlacement vs FailedDoorPlacement
# (per v0.3 B11)
# =============================================================================

@dataclass(frozen=True)
class SuccessfulDoorPlacement:
    """Per v0.3 B11 typestate API. v1 ships ONLY this from successful
    candidates.

    Downstream consumers MUST pattern-match on
    SuccessfulDoorPlacement vs FailedDoorPlacement — mypy rejects
    access to .doors on a FailedDoorPlacement. This enforces filtering
    at the type layer, preventing WARN-mode-failed candidates from
    accidentally consuming as successful.

    Fields:
      source_placed_candidate_signature: provenance back to C12 input.
      doors: canonical lex-ASC tuple of Door (Inv D8). Includes both
          primary (per Inv D1') and secondary (per v0.4 C9 graph
          semantics) doors.
      advisory_flags: tuple of AdvisoryFlag (Inv D16-deduplicated,
          density-bounded ≤ n_rooms × 1.5).
      geometric_fidelity: result-level summary (v1.0: APPROXIMATE per
          v0.4 C6 default; matches every Door's per-door tier).
      cache_keys: C13CacheKeys (geometry / advisory / full per Inv D18).
    """
    source_placed_candidate_signature: str
    doors: tuple[Door, ...]
    advisory_flags: tuple[AdvisoryFlag, ...]
    geometric_fidelity: GeometricFidelity
    cache_keys: C13CacheKeys

    def __post_init__(self) -> None:
        if not self.source_placed_candidate_signature:
            raise ValueError(
                "SuccessfulDoorPlacement.source_placed_candidate_signature "
                "must be non-empty."
            )
        # Inv D8: doors tuple sorted lex-ASC by (room_a_id, room_b_id).
        # Secondary doors at the same edge appear after primary at that
        # edge — within an edge, lex tie-break maintains determinism;
        # since at most one door per (room_a, room_b) edge is selected
        # at v1, simple key sort is sufficient.
        door_keys = [(d.room_a_id, d.room_b_id) for d in self.doors]
        if door_keys != sorted(door_keys):
            raise ValueError(
                f"SuccessfulDoorPlacement violates Inv D8 — doors must "
                f"be sorted lex-ASC by (room_a_id, room_b_id); got {door_keys}."
            )
        # Inv D6: exactly one door has is_main_entry=True
        # (verified only when ≥1 door exists; an empty doors tuple
        # would itself be a different invariant failure caught at
        # assembly time, not here).
        if self.doors:
            main_entries = sum(1 for d in self.doors if d.is_main_entry)
            if main_entries != 1:
                raise ValueError(
                    f"SuccessfulDoorPlacement violates Inv D6 — exactly "
                    f"one door must have is_main_entry=True; got "
                    f"{main_entries} main-entry doors."
                )


@dataclass(frozen=True)
class FailedDoorPlacement:
    """Per v0.3 B11 typestate API. For WARN-mode collection — CANNOT
    be misused as a successful result because the typestate
    discrimination is enforced at the schema level.

    Fields:
      source_placed_candidate_signature: provenance back to C12 input.
      failure_record: the FailureRecord including phase + error_type +
          optional ConditionalLegalityViolation provenance.
      partial_doors: doors placed before failure occurred. For DEBUG
          ONLY; consumers MUST NOT treat these as final placements.
      partial_advisory_flags: advisory flags emitted before failure.
          DEBUG only.
    """
    source_placed_candidate_signature: str
    failure_record: FailureRecord
    partial_doors: tuple[Door, ...] = field(default_factory=tuple)
    partial_advisory_flags: tuple[AdvisoryFlag, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.source_placed_candidate_signature:
            raise ValueError(
                "FailedDoorPlacement.source_placed_candidate_signature "
                "must be non-empty."
            )
        # partial_doors NOT required to satisfy Inv D8 sort — they
        # represent intermediate state for debugging. We DO require
        # them to be a tuple (frozen dataclass enforces this).


# =============================================================================
# DoorPlacementBatchResult (per v0.3 B11)
# =============================================================================

@dataclass(frozen=True)
class DoorPlacementBatchResult:
    """Per v0.3 B11. Top-level result of the door placement pipeline.

    Typestate-discriminated: separate tuples for successful + failed
    placements. NO general "results" field mixing them — that's the
    architectural improvement over C12's mixed-result pattern.

    Fields:
      successful: tuple of SuccessfulDoorPlacement (sorted lex-ASC
          by source_placed_candidate_signature for determinism).
      failed: tuple of FailedDoorPlacement (sorted same way).
      c13_version: captured C13_VERSION at result time.
      c13_edge_protocol_version: captured C13_EDGE_PROTOCOL_VERSION.
      advisory_schema_version: captured ADVISORY_SCHEMA_VERSION.
      cache_key: the batch-level full_cache_key (sha256 of
          per-candidate keys + version constants per v0.2 A10).
    """
    successful: tuple[SuccessfulDoorPlacement, ...]
    failed: tuple[FailedDoorPlacement, ...]
    c13_version: str
    c13_edge_protocol_version: int
    advisory_schema_version: int
    cache_key: str

    def __post_init__(self) -> None:
        if not self.c13_version:
            raise ValueError(
                "DoorPlacementBatchResult.c13_version must be non-empty."
            )
        if self.c13_edge_protocol_version < 1:
            raise ValueError(
                f"DoorPlacementBatchResult.c13_edge_protocol_version "
                f"must be >= 1; got {self.c13_edge_protocol_version}."
            )
        if self.advisory_schema_version < 1:
            raise ValueError(
                f"DoorPlacementBatchResult.advisory_schema_version "
                f"must be >= 1; got {self.advisory_schema_version}."
            )
        if not self.cache_key:
            raise ValueError(
                "DoorPlacementBatchResult.cache_key must be non-empty."
            )
        # Successful + failed should be sorted by signature for
        # deterministic ordering (Inv D7 byte-equal replay analog).
        success_keys = [
            s.source_placed_candidate_signature for s in self.successful
        ]
        if success_keys != sorted(success_keys):
            raise ValueError(
                f"DoorPlacementBatchResult.successful must be sorted "
                f"lex-ASC by source_placed_candidate_signature; got "
                f"{success_keys}."
            )
        failed_keys = [
            f.source_placed_candidate_signature for f in self.failed
        ]
        if failed_keys != sorted(failed_keys):
            raise ValueError(
                f"DoorPlacementBatchResult.failed must be sorted "
                f"lex-ASC by source_placed_candidate_signature; got "
                f"{failed_keys}."
            )


# =============================================================================
# Public exports
# =============================================================================

__all__ = [
    # Enums + literal-vocabulary mirrors
    "AdvisoryCategory",
    "GeometricFidelity",
    "AdvisoryFlagKind",
    "AdvisorySeverity",
    "SecondaryDoorPreferenceKind",
    "C13Phase",
    # Reserved sentinel
    "CausalContext",
    # Per-element schemas
    "AdvisoryFlag",
    "Door",
    "RoomDoorPreference",
    "C13CacheKeys",
    "ConditionalLegalityViolation",
    "FailureRecord",
    # Typestate result variants
    "SuccessfulDoorPlacement",
    "FailedDoorPlacement",
    "DoorPlacementBatchResult",
    # Category sets
    "HABITABLE_ROOM_CATEGORIES",
    "SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1",
]
