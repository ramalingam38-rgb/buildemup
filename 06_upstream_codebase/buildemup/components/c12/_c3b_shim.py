"""
C12 — Vertical Alignment & Placement — UPSTREAM STUB for C3b consumption
=========================================================================

NOTE: STUB covering only the surface C3b consumes. The real C12
(LOCKED v1.0) does full inter-floor coherence, stack alignment,
column continuity, and final room placement.

C3b consumes:
  - PlacedRoom               — for affected_room_ids references

Per spec § 2.3:
  'affected_room_ids: tuple[str, ...] — Room IDs from C12's PlacedRoom
   outputs that this tweak modifies'

Also per spec § 7 R3 (Layout grounding):
  'every TweakOption.affected_room_ids and affected_grid_cells MUST
   reference valid IDs in the upstream SelectionResult'

Stability: PINNED to C12 v1.0.LOCKED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, Optional, Tuple


RoomFunction = Literal[
    "living", "dining", "kitchen", "kitchen_utility",
    "bedroom_master", "bedroom_secondary", "bedroom_guest",
    "bath_full", "bath_powder", "bath_attached",
    "pooja", "study", "balcony", "lobby", "corridor",
    "stair", "lift_lobby", "store", "utility", "laundry",
    "parking", "entry_foyer",
]


@dataclass(frozen=True)
class RoomGeometry:
    """A room's footprint geometry. C3b uses this for space_impact
    deltas and bounding-box checks against structural grid cells."""
    x_mm:         float
    y_mm:         float
    width_mm:     float
    depth_mm:     float
    """(width, depth) interior dimensions; excludes wall thickness."""

    def __post_init__(self) -> None:
        if self.width_mm <= 0 or self.depth_mm <= 0:
            raise ValueError(
                f"RoomGeometry dimensions must be positive; "
                f"got width={self.width_mm}, depth={self.depth_mm}"
            )

    @property
    def area_sqft(self) -> float:
        return (self.width_mm / 304.8) * (self.depth_mm / 304.8)


@dataclass(frozen=True)
class PlacedRoom:
    """A room placed on the floor plan by C12.

    Minimum fields per C12 v1.0 LOCKED for C3b consumption:
      - room_id: stable identifier
      - room_function: function tag (drives orientation tweaks)
      - geometry: footprint
      - floor: which floor
      - structural_bay_ids: which C7 cells this room sits in
      - adjacent_room_ids: spatial-adjacency graph (for circulation
        and privacy reasoning)
    """
    room_id:                  str
    room_function:            RoomFunction
    floor:                    int
    geometry:                 RoomGeometry
    structural_bay_ids:       Tuple[str, ...] = field(default_factory=tuple)
    """C7 cell_ids this room covers — usually 1, sometimes 2 if room
    straddles a bay boundary (which is itself a heuristic signal for
    severity)."""

    adjacent_room_ids:        Tuple[str, ...] = field(default_factory=tuple)
    has_external_wall:        bool = False
    """True if any side of the room is on the building envelope.
    Window resize / balcony tweaks require this."""

    cardinal_orientation:     Optional[Literal["N", "S", "E", "W"]] = None
    """If the room's primary frontage faces a cardinal direction
    (e.g., a master bedroom with windows on the south side), set
    here. Used by C3b for orientation-mismatch detection."""

    def __post_init__(self) -> None:
        if not self.room_id:
            raise ValueError("PlacedRoom.room_id must be non-empty")
        if self.floor < 0:
            raise ValueError(
                f"PlacedRoom.floor must be >= 0; got {self.floor}"
            )


C12_STUB_VERSION: Final[str] = "v1.0.LOCKED.stub.S52"

__all__ = [
    "RoomFunction",
    "RoomGeometry",
    "PlacedRoom",
    "C12_STUB_VERSION",
]
