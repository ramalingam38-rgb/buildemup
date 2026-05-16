"""
BuildemUp — Component 13 — Phase E (canonical output assembly)
==============================================================

Per C13 SPEC v1.0 LOCKED:
- v0.1 § 3.5 (canonical output assembly)
- v0.2 A3 (hinge_side + leaf_thickness_m fields)
- v0.4 C6 (GeometricFidelity enum, APPROXIMATE at v1)
- v0.7 F1 (Phase F is pure verification — Phase E does ALL the
  structural assembly; nothing structural happens in Phase F)

Phase E responsibility:
  - Convert each DoorState (from Phase D) into a Door schema object.
  - Mark EXACTLY ONE door as is_main_entry=True (per Inv D6). That
    door is the one whose edge was Tier-1-picked for
    main_entry_room_id by Phase A.
  - Sort the Door tuple lex-ASC by (room_a_id, room_b_id)
    (per Inv D8).
  - Populate leaf_thickness_m + geometric_fidelity from canonical
    defaults (per v0.2 A3 + v0.4 C6).
  - Carry through axis from the underlying SharedEdge (each Door
    references the edge it sits on).

Phase E does NOT:
  - Verify reachability (Phase F).
  - Verify NBC route constraints D11.2/D11.3' (Phase F).
  - Emit advisories (Phase B emits; Phase E only forwards).
  - Mutate door positions/swings/widths (Phase D was the last mutation).

Per Inv D6 enforcement: SuccessfulDoorPlacement __post_init__ verifies
exactly one is_main_entry=True. Phase E guarantees this by:
  1. Identifying the main entry edge via edge_result.assignments
     (the (room_id=main_entry_room_id, is_secondary=False) entry).
  2. Setting is_main_entry=True only on the Door whose
     (room_a_id, room_b_id) matches that edge.

Per Inv D7 byte-equal replay: Phase E is deterministic — it only
joins, sorts, and stamps flags. No randomness, no time-dependent
state.
"""
from __future__ import annotations

from typing import Optional

from .conflict_resolution import ConflictResolutionResult, DoorState
from .edge_selection import EdgeSelectionResult
from .schema import (
    AdvisoryFlag,
    Door,
    GeometricFidelity,
)
from .versioning import DEFAULT_LEAF_THICKNESS_M


# =============================================================================
# Helpers
# =============================================================================

def _find_main_entry_edge_id(
    edge_result: EdgeSelectionResult,
) -> tuple[str, str]:
    """Identify which edge bears the main entry door.

    Rule (per v0.1 § 3.1 step 2 + v0.4 C9 secondary semantics):
      The main entry door sits on the PRIMARY (is_secondary=False)
      edge picked for main_entry_room_id. Phase A's door-centric
      model guarantees at most one primary edge per room.

    Returns:
      (room_a_id, room_b_id) of the main entry edge.

    Raises:
      ValueError: defensive — if edge_result has no primary
      assignment for main_entry_room_id (would indicate a Phase A
      contract violation).
    """
    main_room = edge_result.main_entry_room_id
    primary_assignments = [
        a for a in edge_result.assignments
        if a.room_id == main_room and not a.is_secondary
    ]
    if not primary_assignments:
        raise ValueError(
            f"Phase E: edge_result has no primary assignment for "
            f"main_entry_room_id={main_room!r}. Phase A contract "
            f"violation."
        )
    if len(primary_assignments) > 1:
        # Defensive — door-centric model picks at most one primary
        # per room.
        raise ValueError(
            f"Phase E: edge_result has {len(primary_assignments)} "
            f"primary assignments for main_entry_room_id={main_room!r}; "
            f"expected exactly 1. Phase A contract violation."
        )
    edge = primary_assignments[0].edge
    return (edge.room_a_id, edge.room_b_id)


def _edge_axis_lookup(
    edge_result: EdgeSelectionResult,
) -> dict[tuple[str, str], str]:
    """Build (room_a_id, room_b_id) → axis lookup from the edge result.

    The DoorState carries position + swing + hinge but not axis (axis
    is a property of the underlying SharedEdge, not the door). Phase E
    uses this lookup to populate Door.axis.
    """
    return {
        (a.edge.room_a_id, a.edge.room_b_id): a.edge.axis
        for a in edge_result.assignments
    }


# =============================================================================
# Phase E entry point
# =============================================================================

def assemble_doors(
    *,
    conflict_result: ConflictResolutionResult,
    edge_result: EdgeSelectionResult,
    leaf_thickness_m: float = DEFAULT_LEAF_THICKNESS_M,
    geometric_fidelity: GeometricFidelity = GeometricFidelity.APPROXIMATE,
) -> tuple[Door, ...]:
    """Phase E entry point.

    For each DoorState in conflict_result.door_states, construct a
    Door schema object. Mark exactly one as is_main_entry=True (per
    Inv D6). Return a tuple sorted lex-ASC by (room_a_id, room_b_id)
    (per Inv D8).

    Args:
      conflict_result: Phase D output carrying resolved door states.
      edge_result: Phase A output used to identify main entry edge
          + look up edge axis.
      leaf_thickness_m: door leaf thickness in metres. Per v0.2 A3
          + DEFAULT_LEAF_THICKNESS_M = 0.04 (Indian standard
          residential 40mm).
      geometric_fidelity: per v0.4 C6 + Inv D14. Default
          APPROXIMATE at v1.

    Returns:
      Tuple of Door objects, sorted lex-ASC, with exactly one
      is_main_entry=True.

    Raises:
      ValueError: if Phase A's edge_result is malformed (no primary
          for main entry, or duplicate primary).
    """
    main_entry_edge_id = _find_main_entry_edge_id(edge_result)
    axis_lookup = _edge_axis_lookup(edge_result)

    doors: list[Door] = []
    for state in conflict_result.door_states:
        edge_id = (state.room_a_id, state.room_b_id)
        if edge_id not in axis_lookup:
            # Defensive: every door must trace back to a Phase A edge.
            raise ValueError(
                f"Phase E: DoorState edge ({state.room_a_id}, "
                f"{state.room_b_id}) has no matching Phase A "
                f"assignment. Phase D/A integrity violation."
            )
        axis = axis_lookup[edge_id]
        # Main entry marker. Only the (room_id=main_entry_room_id,
        # is_secondary=False) door gets is_main_entry=True. Other
        # doors — including any secondary doors on the entry room —
        # are not main-entry.
        is_main_entry = (
            edge_id == main_entry_edge_id and not state.is_secondary
        )
        doors.append(Door(
            room_a_id=state.room_a_id,
            room_b_id=state.room_b_id,
            axis=axis,
            position_along_edge_m=state.position_along_edge_m,
            clear_width_m=state.clear_width_m,
            swing_direction=state.swing_direction,
            hinge_side=state.hinge_side,
            leaf_thickness_m=leaf_thickness_m,
            is_main_entry=is_main_entry,
            geometric_fidelity=geometric_fidelity,
        ))

    # Canonical sort per Inv D8.
    doors.sort(key=lambda d: (d.room_a_id, d.room_b_id))
    return tuple(doors)


__all__ = [
    "assemble_doors",
]
