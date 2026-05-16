"""
BuildemUp† — Component 8 (Corridor Designer) package init.

Per C8 SPEC v0.5 LOCKED § 5.

Public entry point: ``design_corridors(oriented_candidates, grid, plot_analysis)``.

Re-exports the public schema names that downstream components will consume.

†= placeholder name marker.
"""
from buildemup.components.c08.errors import (
    CorridorDispatchError,
    CorridorSelfIntersectionError,
    CorridorTooNarrowError,
)
from buildemup.components.c08.schema import (
    ALLOWED_JUNCTION_ANGLES_DEG,
    DEFAULT_BAND_PRIORITY_ORDER,
    DEFAULT_EPSILON_M,
    DEFAULT_UNDER_COMFORT_PENALTY_RATIO,
    GRID_FRACTION_CANDIDATES,
    ConsumptionBand,
    CorridorDesignConfig,
    CorridorDesignedCandidate,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorPath,
    CorridorProvenance,
    CorridorSegment,
    CorridorSegmentKind,
    GridAlignmentReport,
    NarrowPlotRecommendation,
    WidthPropagation,
    WidthQuantization,
    ZoneBandEnvelope,
)
from buildemup.components.c08.corridor_designer import (
    design_corridors,
    design_corridors_safe,
    design_one_corridor,
)


__all__ = [
    # Public entry point
    "design_corridors",
    "design_corridors_safe",
    "design_one_corridor",
    # Errors
    "CorridorTooNarrowError",
    "CorridorSelfIntersectionError",
    "CorridorDispatchError",
    # Schema
    "CorridorDesignConfig",
    "CorridorDesignedCandidate",
    "CorridorPath",
    "CorridorSegment",
    "CorridorEndpoint",
    "CorridorProvenance",
    "ZoneBandEnvelope",
    "GridAlignmentReport",
    "NarrowPlotRecommendation",
    # Enums
    "CorridorSegmentKind",
    "CorridorEndpointKind",
    "WidthQuantization",
    "WidthPropagation",
    "ConsumptionBand",
    # Constants
    "GRID_FRACTION_CANDIDATES",
    "ALLOWED_JUNCTION_ANGLES_DEG",
    "DEFAULT_EPSILON_M",
    "DEFAULT_BAND_PRIORITY_ORDER",
    "DEFAULT_UNDER_COMFORT_PENALTY_RATIO",
]
