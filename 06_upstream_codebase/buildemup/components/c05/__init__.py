"""
BuildemUp† — Component 5 (Topology Selector) package init.

Per C5 SPEC v0.9 LOCKED § 5.

Public entry point: ``select_topology(plot_analysis, room_brief)``.
Re-exports schema names that downstream components (C6+) will consume.

No KB consistency check (no KB at C5).

†= placeholder name marker.
"""
from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    CorridorSketch,
    ScoreBreakdownEntry,
    TopologyCandidate,
    TopologyKind,
    TopologyPriors,
    TopologyProvenance,
    ZoneBand,
)
from buildemup.components.c05.select import (
    LOW_CONFIDENCE_THRESHOLD,
    MIN_CANDIDATE_ADMISSION_THRESHOLD,
    select_topology,
)


__all__ = [
    "select_topology",
    "LOW_CONFIDENCE_THRESHOLD",
    "MIN_CANDIDATE_ADMISSION_THRESHOLD",
    "TopologyKind",
    "ZoneBand",
    "CorridorPosition",
    "ConnectivityType",
    "CorridorSketch",
    "ScoreBreakdownEntry",
    "TopologyProvenance",
    "TopologyCandidate",
    "TopologyPriors",
]
