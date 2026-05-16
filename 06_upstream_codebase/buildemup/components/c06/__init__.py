"""
BuildemUp† — Component 6 (Orientation Priority) package init.

Per C6 SPEC v0.6 LOCKED § 5.

Public entry point: ``prioritize_orientation(candidates, plot_analysis, vastu_tier)``.
Re-exports schema names that downstream components (C8+) will consume.

†= placeholder name marker.
"""
from buildemup.components.c06.schema import (
    # Constants
    CARDINAL_FACINGS,
    MAX_PERMUTATION_COUNT,
    MIN_DENOM,
    SIGNAL_DOMINANCE_THRESHOLD,
    SWAP_HYSTERESIS_THRESHOLD,
    # Enums
    FunctionRole,
    # Dataclasses
    DirectionPriorityScore,
    OrientationPriority,
    OrientationProvenance,
    OrientedCandidate,
    SignalBreakdown,
)
from buildemup.components.c06.select import prioritize_orientation

__all__ = [
    "prioritize_orientation",
    # Constants
    "CARDINAL_FACINGS",
    "MAX_PERMUTATION_COUNT",
    "MIN_DENOM",
    "SIGNAL_DOMINANCE_THRESHOLD",
    "SWAP_HYSTERESIS_THRESHOLD",
    # Enums
    "FunctionRole",
    # Dataclasses
    "DirectionPriorityScore",
    "OrientationPriority",
    "OrientationProvenance",
    "OrientedCandidate",
    "SignalBreakdown",
]

