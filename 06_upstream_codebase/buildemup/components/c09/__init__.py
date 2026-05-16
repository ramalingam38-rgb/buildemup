"""
BuildemUp† — Component 9 (Room Sizer) package init.

Per C9 SPEC v0.7 LOCKED § 5 (Invocation contract) + § 6 (Failure modes).

Public entry point: ``size_rooms(corridor_designed_candidates, floor_room_brief, grid, plot_analysis, *, config=None)``.

Public schema names (re-exported for downstream consumers C10/C11/C14):
  - Enums: RoomCategory, DwellingSizeTier, BathroomSubtype, NBCSourceConfidence,
           TierResolutionAccuracy, WidthFeasibilityVerdict, GridBayFeasibility,
           PlacementRiskLevel, AllocationStrategy, EnforcementMode
  - Dataclasses: RegulatoryMinimum, RoomSizeRequirement, RoomSizeTable,
                 RoomSizingProvenance, RoomSizedCandidate, RoomSizingConfig
  - Errors: RoomSizingError, PerCandidateError, RoomSizingInfeasibleError,
            WidthInfeasibleError, PackingInfeasibleError, WidthRiskyError,
            GridOversizeError, BatchSizingInfeasibleError, NBCConfidenceTooLow

†= placeholder name marker.
"""
from buildemup.components.c09.errors import (
    BatchSizingInfeasibleError,
    GridOversizeError,
    NBCConfidenceTooLow,
    PackingInfeasibleError,
    PerCandidateError,
    RoomSizingError,
    RoomSizingInfeasibleError,
    WidthInfeasibleError,
    WidthRiskyError,
)
from buildemup.components.c09.room_sizer import size_rooms
from buildemup.components.c09.schema import (
    DEFAULT_PACKING_EFFICIENCY,
    DEFAULT_WALL_THICKNESS_RATIO,
    DWELLING_TIER_THRESHOLD_M2,
    PER_CATEGORY_MAX_MULTIPLIER,
    AllocationStrategy,
    BathroomSubtype,
    DwellingSizeTier,
    EnforcementMode,
    GridBayFeasibility,
    NBCSourceConfidence,
    PlacementRiskLevel,
    RegulatoryMinimum,
    RoomCategory,
    RoomSizeRequirement,
    RoomSizeTable,
    RoomSizedCandidate,
    RoomSizingConfig,
    RoomSizingProvenance,
    TierResolutionAccuracy,
    WidthFeasibilityVerdict,
)


__all__ = [
    # Public entry point
    "size_rooms",
    # Errors
    "RoomSizingError",
    "PerCandidateError",
    "RoomSizingInfeasibleError",
    "WidthInfeasibleError",
    "PackingInfeasibleError",
    "WidthRiskyError",
    "GridOversizeError",
    "BatchSizingInfeasibleError",
    "NBCConfidenceTooLow",
    # Schema dataclasses
    "RoomSizingConfig",
    "RegulatoryMinimum",
    "RoomSizeRequirement",
    "RoomSizeTable",
    "RoomSizingProvenance",
    "RoomSizedCandidate",
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
]
