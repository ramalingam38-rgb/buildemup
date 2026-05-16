"""
C13 — Door Placement — UPSTREAM STUB for C3b consumption
=========================================================

NOTE: STUB covering only the surface C3b consumes. The real C13
(LOCKED v1.0) does full door placement, swing-clearance checks, and
egress validation.

C3b consumes:
  - DoorPlacement            — for door_relocate tweak grounding

Per spec § 2.3 (door_relocate tweak):
  'move door to different wall'

C13 door IDs are referenced in TweakOption.affected_grid_cells when
the tweak is door_relocate (per spec § 7 R3 layout grounding).

Stability: PINNED to C13 v1.0.LOCKED.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal


DoorKind = Literal[
    "interior_room",        # bedroom door, bath door, etc.
    "interior_circulation", # living-to-corridor, etc.
    "entry_main",           # main front door
    "entry_secondary",      # service entrance, back door
    "balcony",              # interior-to-balcony
    "utility",              # to utility / laundry
]


SwingDirection = Literal[
    "into_room_a",   # swings into room_a_id
    "into_room_b",   # swings into room_b_id
    "sliding",       # no swing
    "bifold",        # folds back
]


@dataclass(frozen=True)
class DoorPlacement:
    """A single door connecting two rooms (or a room to the outside).

    Minimum fields per C13 v1.0 LOCKED for C3b consumption:
      - door_id: stable identifier
      - door_kind: drives tweak generation rules
      - between_rooms: (room_a_id, room_b_id); one can be 'EXTERIOR'
      - wall_id: which wall (links to C7 grid)
      - width_mm, height_mm: standard 900×2100 typical
      - swing: direction
    """
    door_id:        str
    door_kind:      DoorKind
    room_a_id:      str
    """Origin room. May be 'EXTERIOR' for entry doors."""

    room_b_id:      str
    """Destination room."""

    wall_id:        str
    """Identifier of the wall this door pierces."""

    width_mm:       int = 900
    height_mm:      int = 2100
    swing:          SwingDirection = "into_room_a"

    def __post_init__(self) -> None:
        if not self.door_id:
            raise ValueError("DoorPlacement.door_id must be non-empty")
        if not self.room_a_id or not self.room_b_id:
            raise ValueError(
                "DoorPlacement.room_a_id/room_b_id must both be non-empty "
                "(use 'EXTERIOR' for outside)"
            )
        if self.width_mm < 600 or self.height_mm < 1800:
            raise ValueError(
                f"DoorPlacement dimensions implausibly small "
                f"(width={self.width_mm}, height={self.height_mm}); "
                f"NBC minimums are ~750mm × 2000mm"
            )


C13_STUB_VERSION: Final[str] = "v1.0.LOCKED.stub.S52"

__all__ = [
    "DoorKind", "SwingDirection",
    "DoorPlacement",
    "C13_STUB_VERSION",
]
