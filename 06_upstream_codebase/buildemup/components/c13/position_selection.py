"""
BuildemUp — Component 13 — Phase C (position along edge)
=========================================================

Per C13 SPEC v1.0 LOCKED:
- v0.1 § 3.3 (base position selection)
- v0.2 A2 (corner_offset_m default 0.15 m — Neufert ergonomic minimum)
- v0.2 A7 (grid_snap_m default 0.05 m — discrete increment)

Phase C responsibility:
  - For each door, choose `position_along_edge_m` (the offset along
    the SharedEdge where the door's hinge corner sits).
  - Default to corner_offset_m (canonical starting position; v0.2 A2
    avoided the degenerate position=0 that would put the door flush
    against the wall corner).
  - Ensure position + clear_width_m <= overlap_length_m (Inv D4: door
    fits within edge).
  - Snap to grid_snap_m (Inv D14: APPROXIMATE fidelity at v1).

Phase C does NOT detect or resolve swing-arc conflicts; it picks
the canonical initial position. Phase D iterates over Phase C's
output and shifts positions during conflict resolution.

Per v0.7 F1 purity discipline: Phase C is a pure function of its
inputs (no telemetry side effects on a per-position basis at v1 —
position shifts during Phase D will emit SwingArcConflictEvent).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

from .contracts import C13ConsumesFromC12Edge
from .edge_selection import EdgeAssignment, EdgeSelectionResult
from .errors import DoorPositionInfeasibleError


@dataclass(frozen=True)
class PositionAssignment:
    """One door's position decision. Output of Phase C per edge
    assignment.

    Fields:
      room_a_id, room_b_id: canonical edge identifier (matches the
          parent EdgeAssignment).
      position_along_edge_m: hinge corner offset along the edge,
          measured from overlap_start_m. Grid-snapped per Inv D14.
      clear_width_m: door clear width (config default at v1).
      is_secondary: True if this is a secondary door (mirrors
          EdgeAssignment.is_secondary for downstream Phase E
          assembly).
    """
    room_a_id: str
    room_b_id: str
    position_along_edge_m: float
    clear_width_m: float
    is_secondary: bool

    def __post_init__(self) -> None:
        if self.position_along_edge_m < 0.0:
            raise ValueError(
                f"PositionAssignment.position_along_edge_m must be "
                f">= 0.0; got {self.position_along_edge_m}."
            )
        if self.clear_width_m <= 0.0:
            raise ValueError(
                f"PositionAssignment.clear_width_m must be > 0.0; "
                f"got {self.clear_width_m}."
            )


@dataclass(frozen=True)
class PositionAssignmentResult:
    """Output of Phase C. Same ordering as input EdgeSelectionResult:
    canonical (room_a_id, room_b_id, is_secondary)."""
    assignments: tuple[PositionAssignment, ...]

    def __post_init__(self) -> None:
        keys = [
            (a.room_a_id, a.room_b_id, a.is_secondary)
            for a in self.assignments
        ]
        if keys != sorted(keys):
            raise ValueError(
                f"PositionAssignmentResult.assignments must be "
                f"sorted by (room_a_id, room_b_id, is_secondary); "
                f"got {keys}."
            )


# =============================================================================
# Helpers
# =============================================================================

def _snap_to_grid(value: float, grid_snap_m: float) -> float:
    """Snap a value to the nearest multiple of grid_snap_m.

    Uses round-half-away-from-zero (math.floor(x + 0.5*sign(x))) for
    deterministic behavior — Python's built-in round() uses banker's
    rounding which is fine for Inv D7 but harder to reason about.

    Per Inv D14 APPROXIMATE fidelity at v1: grid_snap_m default
    0.05 m (50 mm). Snapping introduces at most grid_snap_m/2 of
    geometric error vs theoretical optimum.
    """
    if grid_snap_m <= 0.0:
        return value
    n_units = math.floor(value / grid_snap_m + 0.5)
    return n_units * grid_snap_m


def _initial_position(
    edge: C13ConsumesFromC12Edge,
    clear_width_m: float,
    corner_offset_m: float,
    grid_snap_m: float,
) -> float:
    """Compute the canonical initial position along an edge.

    Per v0.2 A2: position_along_edge_m = corner_offset_m (so the
    door's hinge corner sits corner_offset_m in from the edge's
    overlap_start_m).

    Constraint (Inv D4): position + clear_width_m <= overlap_length_m.
    If corner_offset_m + clear_width_m > overlap_length_m, raise
    DoorPositionInfeasibleError (this should be rare since C12 already
    verifies min_required_clear_width_m at the edge level, but
    corner_offset reduces the effective placement window).
    """
    snapped_corner = _snap_to_grid(corner_offset_m, grid_snap_m)
    if snapped_corner + clear_width_m > edge.overlap_length_m:
        # Try to find ANY feasible position by reducing corner offset
        # toward zero. If even zero doesn't fit, the edge is genuinely
        # too narrow.
        if clear_width_m > edge.overlap_length_m:
            raise DoorPositionInfeasibleError(
                f"Phase C: door clear_width={clear_width_m:.3f}m "
                f"exceeds edge overlap_length={edge.overlap_length_m:.3f}m "
                f"on edge ({edge.room_a_id}, {edge.room_b_id})."
            )
        # corner_offset shrinks; door still fits at position=0 (or
        # an adjusted corner-offset that just fits).
        return 0.0
    return snapped_corner


# =============================================================================
# Phase C entry point
# =============================================================================

def assign_positions(
    *,
    edge_result: EdgeSelectionResult,
    default_clear_width_m: float,
    corner_offset_m: float,
    grid_snap_m: float,
) -> PositionAssignmentResult:
    """Phase C entry point.

    For each EdgeAssignment from Phase A, choose an initial
    position_along_edge_m. v1 uses corner_offset_m as the canonical
    starting position; Phase D may shift positions during conflict
    resolution.

    Per v0.4 C6 GeometricFidelity.APPROXIMATE default at v1:
    positions are grid-snapped (grid_snap_m default 0.05 m), so two
    runs with the same inputs produce byte-equal positions (Inv D7).

    Args:
      edge_result: Phase A output.
      default_clear_width_m: door clear width to use for all doors at
          v1. Per DoorPlacementConfig default 0.9 m (NBC 2016 internal
          door minimum).
      corner_offset_m: hinge-corner offset from edge start.
          Per DoorPlacementConfig default 0.15 m (Neufert minimum).
      grid_snap_m: positional grid quantization.
          Per DoorPlacementConfig default 0.05 m (50 mm).

    Returns:
      PositionAssignmentResult.

    Raises:
      DoorPositionInfeasibleError: a door's clear_width_m exceeds the
          edge's overlap_length_m (C12 should already have caught
          this via doorway_feasible=False, but defensive check).
    """
    positions: list[PositionAssignment] = []
    for a in edge_result.assignments:
        pos = _initial_position(
            a.edge,
            default_clear_width_m,
            corner_offset_m,
            grid_snap_m,
        )
        positions.append(PositionAssignment(
            room_a_id=a.edge.room_a_id,
            room_b_id=a.edge.room_b_id,
            position_along_edge_m=pos,
            clear_width_m=default_clear_width_m,
            is_secondary=a.is_secondary,
        ))

    positions.sort(key=lambda p: (p.room_a_id, p.room_b_id, p.is_secondary))
    return PositionAssignmentResult(assignments=tuple(positions))


__all__ = [
    "PositionAssignment",
    "PositionAssignmentResult",
    "assign_positions",
]
