"""
BuildemUp† — Component 4 (Plot Analysis) package init.

Per spec § 5: calls verify_kb_consistency() at import (fail-fast on
KB drift). Re-exports the public entry point `derive` and the public
schema names that downstream components (C5+) consume.

†= placeholder name marker.
"""
from buildemup.components.c04.plot_analysis import derive
from buildemup.components.c04.schema import (
    BASELINE_ROOM_ORIENTATION_GUIDELINES,
    LEFT_RIGHT_BY_FACING,
    ClimateZone,
    ConfidenceLevel,
    NeighbourContext,
    PlotAnalysis,
    PlotAnalysisProvenance,
    PlotShape,
    PlotTier,
    RoadWidthClass,
    SoilEstimate,
    SunPath,
    WindContext,
    compute_plot_facing_sides,
)

# Fail-fast KB drift check — raises RuntimeError if any supported city
# is missing from any of the 4 KBs. Runs once per process at import.
from buildemup.kb.city_geography import verify_kb_consistency as _verify_kb
_verify_kb()
del _verify_kb

__all__ = [
    "derive",
    "PlotAnalysis",
    "PlotAnalysisProvenance",
    "PlotTier",
    "PlotShape",
    "ClimateZone",
    "ConfidenceLevel",
    "RoadWidthClass",
    "SunPath",
    "WindContext",
    "SoilEstimate",
    "NeighbourContext",
    "BASELINE_ROOM_ORIENTATION_GUIDELINES",
    "LEFT_RIGHT_BY_FACING",
    "compute_plot_facing_sides",
]
