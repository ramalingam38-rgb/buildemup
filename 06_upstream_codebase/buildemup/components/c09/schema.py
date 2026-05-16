"""
BuildemUp† — Component 9 (Room Sizer) — Schema module.

Per C9 SPEC v0.7 LOCKED § 3 (Output schema).

Defines:
  - Enums: RoomCategory, DwellingSizeTier, BathroomSubtype, NBCSourceConfidence,
           TierResolutionAccuracy, WidthFeasibilityVerdict, GridBayFeasibility,
           PlacementRiskLevel, AllocationStrategy, EnforcementMode
  - Dataclasses: RegulatoryMinimum, RoomSizeRequirement, RoomSizeTable,
                 RoomSizingProvenance, RoomSizedCandidate, RoomSizingConfig

All output dataclasses are frozen (immutable). RoomSizingConfig is also frozen
to keep the call signature stable across components.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from buildemup.components.c08.schema import CorridorDesignedCandidate


# =============================================================================
# Enums
# =============================================================================


class RoomCategory(str, Enum):
    """v1 room category set. Per § 3."""
    BEDROOM  = "bedroom"
    BATHROOM = "bathroom"
    LIVING   = "living"
    KITCHEN  = "kitchen"
    POOJA    = "pooja"
    UTILITY  = "utility"
    OTHER    = "other"


class DwellingSizeTier(str, Enum):
    """NBC dwelling tier. Per § 3.

    SMALL = dwelling <= 50 m^2 (NBC clause 12.2.x — smaller min-areas)
    LARGE = dwelling > 50 m^2 (NBC clause 12.1.x — larger min-areas)
    """
    SMALL = "small"
    LARGE = "large"


class BathroomSubtype(str, Enum):
    """v1 bathroom subtype enum. Per § 3.

    COMBINED  = WC + shower + sink (Indian residential default)
    BATH_ONLY = shower + sink, no WC
    WC_ONLY   = WC + small sink, no shower
    """
    COMBINED  = "combined"
    BATH_ONLY = "bath_only"
    WC_ONLY   = "wc_only"


class NBCSourceConfidence(str, Enum):
    """Per-row source confidence. Per § 3 / § 14.24.

    VERIFIED            = independently verified against the NBC 2016 PDF
    SECONDARY_CONSENSUS = multiple secondary sources agree (v1 default)
    SECONDARY_UNVERIFIED= row used in v1 but with disagreement / missing citation;
                          B-150 verification pass will resolve.
    """
    VERIFIED             = "verified"
    SECONDARY_CONSENSUS  = "secondary_consensus"
    SECONDARY_UNVERIFIED = "secondary_unverified"


class TierResolutionAccuracy(str, Enum):
    """Per § 14.25 — captures how the dwelling tier was resolved.

    EXACT                       = derived from candidate envelopes (single floor)
    APPROXIMATE_DEFENSIVE_LARGE = multi-floor brief with no explicit area; LARGE picked defensively
    OVERRIDE_SUPPLIED           = config supplied either dwelling_tier_override or assumed_total_dwelling_area_m2
    """
    EXACT                       = "exact"
    APPROXIMATE_DEFENSIVE_LARGE = "approximate_defensive_large"
    OVERRIDE_SUPPLIED           = "override_supplied"


class WidthFeasibilityVerdict(str, Enum):
    """Per-room width-feasibility classification. Per § 14.29 / § 14.37.

    Verdicts (v0.7 — uses config.wall_thickness_ratio for RISKY boundary):
      - FEASIBLE: liveability_min_width_m <= (1.0 - wall_thickness_ratio) * envelope_min_axis
      - RISKY:    (1.0 - wall_thickness_ratio) * envelope_min_axis < liveability_min_width_m <= envelope_min_axis
                  (just barely fits envelope; high probability of failure once C11 adds
                   wall thickness) -> Inv 17b WARN (or RAISE in STRICT mode)
      - IMPOSSIBLE: liveability_min_width_m > envelope_min_axis
                  (deterministic placement impossibility) -> Inv 17a RAISE
                  (always; not heuristic)
    """
    FEASIBLE   = "feasible"
    RISKY      = "risky"
    IMPOSSIBLE = "impossible"


class GridBayFeasibility(str, Enum):
    """Per-room grid-bay feasibility (n-bay framing). Per § 14.30.

    Verdicts (computed against grid.bay_max_m):
      - SINGLE_BAY: liveability_min_width_m <= bay_max_m
      - DOUBLE_BAY: bay_max_m < liveability_min_width_m <= 2 * bay_max_m
      - TRIPLE_BAY: 2 * bay_max_m < liveability_min_width_m <= 3 * bay_max_m
      - OVERSIZED:  liveability_min_width_m > 3 * bay_max_m (Inv 18 WARN trigger;
                    RAISE in STRICT mode per § 14.42).
    """
    SINGLE_BAY = "single_bay"
    DOUBLE_BAY = "double_bay"
    TRIPLE_BAY = "triple_bay"
    OVERSIZED  = "oversized"


class PlacementRiskLevel(str, Enum):
    """Combined risk signal — severity-weighted (§ 14.36).

    Score derivation per ``validator._derive_placement_risk_level``:
      - score 0:    LOW
      - score 1-2:  MEDIUM
      - score >= 3: HIGH

    OVERSIZED grid alone (weight 2) -> MEDIUM by itself.
    OVERSIZED + any other yellow -> HIGH.
    """
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class AllocationStrategy(str, Enum):
    """Surplus allocation strategy. Per § 4.5 / § 14.2.

    PRIORITY_GREEDY = v1 default; assign surplus to high-priority rooms first
                      (clamped at max_m2) before falling through to lower priority.
    PROPORTIONAL    = pro-rata distribution by liveability_min_area_m2.
    """
    PRIORITY_GREEDY = "priority_greedy"
    PROPORTIONAL    = "proportional"


class EnforcementMode(str, Enum):
    """Enforcement mode for heuristic invariants. Per § 14.41.

    WARN   = default; heuristic invariants (Inv 10 packing, Inv 17b RISKY,
             Inv 18 OVERSIZED) log to provenance and let the candidate through.
    STRICT = NEW v0.7; heuristic invariants escalate to per-candidate RAISE
             (PackingInfeasibleError / WidthRiskyError / GridOversizeError);
             failed candidates drop from the result tuple per § 14.40.
    """
    WARN   = "WARN"
    STRICT = "STRICT"


# =============================================================================
# Constants
# =============================================================================

# Per § 4.4 — max_m2 multiplier per category. Q14 in spec § 15 may eventually
# move these into kb/room_targets.json; v0.7 keeps them in code per the strict
# spec reading. Lookup key is RoomCategory; LIVING uses the larger 2.5x
# multiplier to allow generous living-room sizing.
PER_CATEGORY_MAX_MULTIPLIER: Mapping[RoomCategory, float] = MappingProxyType({
    RoomCategory.BEDROOM:  1.6,
    RoomCategory.LIVING:   2.5,
    RoomCategory.KITCHEN:  1.6,
    RoomCategory.BATHROOM: 1.6,
    RoomCategory.POOJA:    1.6,
    RoomCategory.UTILITY:  1.6,
    RoomCategory.OTHER:    1.6,
})


# Per § 14.41 — default packing efficiency. Tunable via config.
DEFAULT_PACKING_EFFICIENCY: float = 0.75

# Per § 14.37 — default wall-thickness ratio. Indian residential 100-115mm interior
# partitions ~ 10% of envelope-to-envelope width.
DEFAULT_WALL_THICKNESS_RATIO: float = 0.10

# SMALL/LARGE dwelling tier threshold. Per § 4.1.
DWELLING_TIER_THRESHOLD_M2: float = 50.0


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class RoomSizingConfig:
    """Per-call tunables for ``size_rooms``. Per § 2.

    All fields have defensive defaults — passing ``RoomSizingConfig()`` with no
    overrides reproduces the v1 default behavior.
    """

    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    """v0.7-activated. WARN preserves v0.6 default behaviour. STRICT
    escalates Inv 10/17b/18 to per-candidate RAISE."""

    allocation_strategy: AllocationStrategy = AllocationStrategy.PRIORITY_GREEDY
    """Surplus allocation strategy. PRIORITY_GREEDY default per § 4.5."""

    packing_efficiency: float = DEFAULT_PACKING_EFFICIENCY
    """Inv 10 heuristic ratio. WARN trigger when Sum(liveability_min) > envelope * this."""

    dwelling_tier_override: DwellingSizeTier | None = None
    """If supplied, bypass envelope-area-based tier resolution. Used by tests
    and explicit-mode callers."""

    priority_override: tuple[str, ...] | None = None
    """If supplied, override the v1 default priority order. Tuple of room_ids
    in priority order. Validated against rooms produced by the orchestrator."""

    require_verified_nbc: bool = False
    """v0.5. When True, raise NBCConfidenceTooLow if any used NBC row is not
    VERIFIED. Default False keeps v1 ship-as-secondary-consensus behaviour."""

    assumed_total_dwelling_area_m2: float | None = None
    """v0.5. If supplied, used to resolve dwelling tier in multi-floor briefs
    where the candidate envelope is just one floor of the dwelling. Tags
    tier_resolution_accuracy = OVERRIDE_SUPPLIED."""

    wall_thickness_ratio: float = DEFAULT_WALL_THICKNESS_RATIO
    """v0.6. Drives the FEASIBLE/RISKY threshold:
    risky_threshold = (1.0 - wall_thickness_ratio) * envelope_min_axis."""

    def __post_init__(self) -> None:
        if not isinstance(self.enforcement_mode, EnforcementMode):
            raise TypeError(
                f"RoomSizingConfig.enforcement_mode must be EnforcementMode; "
                f"got {type(self.enforcement_mode).__name__}"
            )
        if not isinstance(self.allocation_strategy, AllocationStrategy):
            raise TypeError(
                f"RoomSizingConfig.allocation_strategy must be AllocationStrategy; "
                f"got {type(self.allocation_strategy).__name__}"
            )
        if not (0.0 < self.packing_efficiency <= 1.0):
            raise ValueError(
                f"RoomSizingConfig.packing_efficiency must be in (0, 1]; "
                f"got {self.packing_efficiency}"
            )
        if self.dwelling_tier_override is not None and not isinstance(
            self.dwelling_tier_override, DwellingSizeTier
        ):
            raise TypeError(
                f"RoomSizingConfig.dwelling_tier_override must be "
                f"DwellingSizeTier or None; "
                f"got {type(self.dwelling_tier_override).__name__}"
            )
        if (
            self.assumed_total_dwelling_area_m2 is not None
            and self.assumed_total_dwelling_area_m2 <= 0.0
        ):
            raise ValueError(
                f"RoomSizingConfig.assumed_total_dwelling_area_m2 must be > 0 "
                f"when supplied; got {self.assumed_total_dwelling_area_m2}"
            )
        if not (0.0 <= self.wall_thickness_ratio < 1.0):
            raise ValueError(
                f"RoomSizingConfig.wall_thickness_ratio must be in [0, 1); "
                f"got {self.wall_thickness_ratio}"
            )


# =============================================================================
# Dataclasses — per-room sizing
# =============================================================================


@dataclass(frozen=True)
class RegulatoryMinimum:
    """NBC 2016 floor for one room. Per § 3 / § 14.7.

    Triple of (area, width, height) plus the source clause + confidence.
    Width / height fields can be 0.0 when NBC has no requirement (e.g.
    UTILITY width, POOJA area).
    """
    area_m2: float
    width_m: float
    height_m: float
    nbc_clause: str
    source_confidence: NBCSourceConfidence

    def __post_init__(self) -> None:
        if self.area_m2 < 0.0:
            raise ValueError(
                f"RegulatoryMinimum.area_m2 must be >= 0; got {self.area_m2}"
            )
        if self.width_m < 0.0:
            raise ValueError(
                f"RegulatoryMinimum.width_m must be >= 0; got {self.width_m}"
            )
        if self.height_m < 0.0:
            raise ValueError(
                f"RegulatoryMinimum.height_m must be >= 0; got {self.height_m}"
            )
        if not isinstance(self.source_confidence, NBCSourceConfidence):
            raise TypeError(
                f"RegulatoryMinimum.source_confidence must be NBCSourceConfidence; "
                f"got {type(self.source_confidence).__name__}"
            )


@dataclass(frozen=True)
class RoomSizeRequirement:
    """Per-room sizing requirement. Per § 3.

    Construction-time invariants (asserted in __post_init__):
      Inv 6:  liveability_min_area_m2 >= regulatory_minimum.area_m2
      Inv 6b: liveability_min_width_m >= regulatory_minimum.width_m
      Inv 7:  target_m2 >= liveability_min_area_m2
      Inv 8:  max_m2 >= target_m2
      Inv 13/14: is_master semantics (deferred to validator; needs whole-table view)
      Inv 15: bathroom_subtype set iff category == BATHROOM
    """
    room_id: str
    category: RoomCategory
    regulatory_minimum: RegulatoryMinimum
    liveability_min_area_m2: float
    liveability_min_width_m: float
    target_m2: float
    max_m2: float
    priority: int
    is_master: bool = False
    bathroom_subtype: BathroomSubtype | None = None
    other_subtype: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.room_id, str) or not self.room_id:
            raise ValueError(
                f"RoomSizeRequirement.room_id must be a non-empty string; "
                f"got {self.room_id!r}"
            )
        if not isinstance(self.category, RoomCategory):
            raise TypeError(
                f"RoomSizeRequirement.category must be RoomCategory; "
                f"got {type(self.category).__name__}"
            )
        if not isinstance(self.regulatory_minimum, RegulatoryMinimum):
            raise TypeError(
                f"RoomSizeRequirement.regulatory_minimum must be RegulatoryMinimum; "
                f"got {type(self.regulatory_minimum).__name__}"
            )
        # Inv 6 (per-room area)
        if self.liveability_min_area_m2 < self.regulatory_minimum.area_m2:
            raise ValueError(
                f"RoomSizeRequirement[{self.room_id}]: "
                f"liveability_min_area_m2 ({self.liveability_min_area_m2}) "
                f"< regulatory_minimum.area_m2 ({self.regulatory_minimum.area_m2})"
            )
        # Inv 6b (per-room width)
        if self.liveability_min_width_m < self.regulatory_minimum.width_m:
            raise ValueError(
                f"RoomSizeRequirement[{self.room_id}]: "
                f"liveability_min_width_m ({self.liveability_min_width_m}) "
                f"< regulatory_minimum.width_m ({self.regulatory_minimum.width_m})"
            )
        # Inv 7 (target above liveability)
        if self.target_m2 < self.liveability_min_area_m2:
            raise ValueError(
                f"RoomSizeRequirement[{self.room_id}]: "
                f"target_m2 ({self.target_m2}) "
                f"< liveability_min_area_m2 ({self.liveability_min_area_m2})"
            )
        # Inv 8 (max above target)
        if self.max_m2 < self.target_m2:
            raise ValueError(
                f"RoomSizeRequirement[{self.room_id}]: "
                f"max_m2 ({self.max_m2}) < target_m2 ({self.target_m2})"
            )
        if self.priority < 1:
            raise ValueError(
                f"RoomSizeRequirement[{self.room_id}]: "
                f"priority must be >= 1; got {self.priority}"
            )
        # Inv 15 (bathroom_subtype iff BATHROOM)
        if self.category == RoomCategory.BATHROOM:
            if not isinstance(self.bathroom_subtype, BathroomSubtype):
                raise ValueError(
                    f"RoomSizeRequirement[{self.room_id}]: BATHROOM rooms must "
                    f"have a BathroomSubtype; got {self.bathroom_subtype!r}"
                )
        else:
            if self.bathroom_subtype is not None:
                raise ValueError(
                    f"RoomSizeRequirement[{self.room_id}]: non-BATHROOM rooms "
                    f"must have bathroom_subtype is None; "
                    f"got {self.bathroom_subtype!r}"
                )
        # is_master is meaningful on BEDROOM (Inv 13) and BATHROOM (Inv 14)
        if self.is_master and self.category not in (
            RoomCategory.BEDROOM, RoomCategory.BATHROOM
        ):
            raise ValueError(
                f"RoomSizeRequirement[{self.room_id}]: is_master=True only "
                f"valid for BEDROOM or BATHROOM; got category={self.category.value}"
            )
        if self.other_subtype and self.category != RoomCategory.OTHER:
            raise ValueError(
                f"RoomSizeRequirement[{self.room_id}]: other_subtype is only "
                f"meaningful for OTHER category; got category={self.category.value}"
            )


@dataclass(frozen=True)
class RoomSizeTable:
    """Sizing for one C8 candidate's floor. Per § 3.

    Per-table invariants (asserted post-init):
      - rooms is a non-empty tuple of RoomSizeRequirement
      - room_ids unique (Inv 11)
      - total_liveability_min_area_m2 == sum of room liveability_min_area_m2 (within tolerance)
      - unassigned_area_m2 >= 0 (Inv 16)
    The harder cross-room invariants (Inv 1-2 brief consistency, Inv 9 envelope feasibility,
    Inv 12 priority contiguity, Inv 13/14 master uniqueness) are checked in
    validator.run_invariants because they need brief / envelope context.
    """
    rooms: tuple[RoomSizeRequirement, ...]
    buildable_envelope_minus_corridor_m2: float
    dwelling_size_tier: DwellingSizeTier
    total_liveability_min_area_m2: float
    total_target_m2: float
    surplus_for_distribution_m2: float
    unassigned_area_m2: float
    packing_efficiency_used: float
    floor_label: str

    def __post_init__(self) -> None:
        if not isinstance(self.rooms, tuple):
            raise TypeError(
                f"RoomSizeTable.rooms must be a tuple; "
                f"got {type(self.rooms).__name__}"
            )
        if len(self.rooms) == 0:
            raise ValueError("RoomSizeTable.rooms must be non-empty")
        for i, r in enumerate(self.rooms):
            if not isinstance(r, RoomSizeRequirement):
                raise TypeError(
                    f"RoomSizeTable.rooms[{i}] must be RoomSizeRequirement; "
                    f"got {type(r).__name__}"
                )
        # Inv 11 (room_ids unique)
        ids = [r.room_id for r in self.rooms]
        if len(set(ids)) != len(ids):
            raise ValueError(
                f"RoomSizeTable.rooms have duplicate room_id: {ids}"
            )
        if not isinstance(self.dwelling_size_tier, DwellingSizeTier):
            raise TypeError(
                f"RoomSizeTable.dwelling_size_tier must be DwellingSizeTier; "
                f"got {type(self.dwelling_size_tier).__name__}"
            )
        if self.buildable_envelope_minus_corridor_m2 < 0.0:
            raise ValueError(
                f"RoomSizeTable.buildable_envelope_minus_corridor_m2 must be >= 0; "
                f"got {self.buildable_envelope_minus_corridor_m2}"
            )
        # Inv 16 (unassigned area non-negative)
        if self.unassigned_area_m2 < -1e-6:  # tolerate float fuzz
            raise ValueError(
                f"RoomSizeTable.unassigned_area_m2 must be >= 0; "
                f"got {self.unassigned_area_m2}"
            )


@dataclass(frozen=True)
class RoomSizingProvenance:
    """Provenance for one C9 sizing pass. Per § 3 / § 10.

    Each successful output candidate carries its own provenance instance.
    The "which input candidates failed" info lives in BatchSizingInfeasibleError
    when raised — there is no aggregate batch provenance object (§ 10).
    """
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    nbc_table_version: str
    furniture_kb_version: str
    targets_kb_version: str
    dwelling_size_tier: DwellingSizeTier
    tier_resolution_accuracy: TierResolutionAccuracy
    assumed_total_dwelling_area_m2: float | None
    grid_bay_min_m: float
    grid_bay_max_m: float
    wall_thickness_ratio_used: float
    enforcement_mode: str
    allocation_strategy: str
    surplus_distributed_m2: float
    rooms_at_min: tuple[str, ...]
    rooms_clamped_at_max: tuple[str, ...]
    packing_basis: str
    heuristic_packing_check_warning: bool
    width_feasibility_per_room: Mapping[str, WidthFeasibilityVerdict]
    grid_bay_feasibility_per_room: Mapping[str, GridBayFeasibility]
    placement_risk_level: PlacementRiskLevel
    placement_risk_score: int
    unverified_nbc_rows_used: tuple[str, ...]
    other_sizing_behavior: str
    rule_trace: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.derived_at <= 0.0:
            raise ValueError(
                f"RoomSizingProvenance.derived_at must be > 0 (Unix epoch); "
                f"got {self.derived_at}"
            )
        if not isinstance(self.dwelling_size_tier, DwellingSizeTier):
            raise TypeError(
                "RoomSizingProvenance.dwelling_size_tier must be DwellingSizeTier"
            )
        if not isinstance(
            self.tier_resolution_accuracy, TierResolutionAccuracy
        ):
            raise TypeError(
                "RoomSizingProvenance.tier_resolution_accuracy must be "
                "TierResolutionAccuracy"
            )
        if not isinstance(self.placement_risk_level, PlacementRiskLevel):
            raise TypeError(
                "RoomSizingProvenance.placement_risk_level must be "
                "PlacementRiskLevel"
            )
        if self.placement_risk_score < 0:
            raise ValueError(
                f"RoomSizingProvenance.placement_risk_score must be >= 0; "
                f"got {self.placement_risk_score}"
            )
        # Wrap mappings in MappingProxyType so consumers can't mutate
        # (mimics the C04 / C08 pattern).
        if not isinstance(self.width_feasibility_per_room, MappingProxyType):
            object.__setattr__(
                self,
                "width_feasibility_per_room",
                MappingProxyType(dict(self.width_feasibility_per_room)),
            )
        if not isinstance(self.grid_bay_feasibility_per_room, MappingProxyType):
            object.__setattr__(
                self,
                "grid_bay_feasibility_per_room",
                MappingProxyType(dict(self.grid_bay_feasibility_per_room)),
            )


@dataclass(frozen=True)
class RoomSizedCandidate:
    """One C8 CorridorDesignedCandidate paired with its C9 sizing. Per § 3.

    The embedded ``corridor_designed_candidate`` reference allows callers to
    correlate a C9 output back to its input position in the partial-batch
    pattern (§ 14.40).
    """
    corridor_designed_candidate: CorridorDesignedCandidate
    room_size_table: RoomSizeTable
    provenance: RoomSizingProvenance

    def __post_init__(self) -> None:
        if not isinstance(
            self.corridor_designed_candidate, CorridorDesignedCandidate
        ):
            raise TypeError(
                "RoomSizedCandidate.corridor_designed_candidate must be "
                "CorridorDesignedCandidate"
            )
        if not isinstance(self.room_size_table, RoomSizeTable):
            raise TypeError(
                "RoomSizedCandidate.room_size_table must be RoomSizeTable"
            )
        if not isinstance(self.provenance, RoomSizingProvenance):
            raise TypeError(
                "RoomSizedCandidate.provenance must be RoomSizingProvenance"
            )


__all__ = [
    # Enums
    "RoomCategory",
    "DwellingSizeTier",
    "BathroomSubtype",
    "NBCSourceConfidence",
    "TierResolutionAccuracy",
    "WidthFeasibilityVerdict",
    "GridBayFeasibility",
    "PlacementRiskLevel",
    "AllocationStrategy",
    "EnforcementMode",
    # Constants
    "PER_CATEGORY_MAX_MULTIPLIER",
    "DEFAULT_PACKING_EFFICIENCY",
    "DEFAULT_WALL_THICKNESS_RATIO",
    "DWELLING_TIER_THRESHOLD_M2",
    # Dataclasses
    "RoomSizingConfig",
    "RegulatoryMinimum",
    "RoomSizeRequirement",
    "RoomSizeTable",
    "RoomSizingProvenance",
    "RoomSizedCandidate",
]
