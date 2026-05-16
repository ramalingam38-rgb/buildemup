"""
C10 — Wet-Zone Stack Planner — UPSTREAM STUB for C3b consumption
=================================================================

NOTE: STUB covering only the surface C3b consumes. The real C10
(LOCKED v1.0) provides full plumbing/drainage planning per IS 1172
+ stack-alignment heuristics.

C3b consumes:
  - RiserGroup               — for wet_zone_restage tweak context

Per spec § 3 Phase β step 4.2:
  'Wet-zone stack interaction → C10 RiserGroup output; tweak affects
   a room with a riser OR adjacent to one'

Stability: PINNED to C10 v1.0.LOCKED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, Tuple


@dataclass(frozen=True)
class Riser:
    """A single vertical plumbing riser shared across floors."""
    riser_id:        str
    riser_kind:      Literal["water_supply", "drain", "vent", "combined"]
    x_mm:            float
    y_mm:            float
    served_floors:   Tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.riser_id:
            raise ValueError("Riser.riser_id must be non-empty")
        if not self.served_floors:
            raise ValueError("Riser.served_floors must be non-empty")


@dataclass(frozen=True)
class RiserGroup:
    """A set of risers that share a wet-zone stack. C3b uses this
    to detect tweaks that would break stack alignment (which would
    trigger AUTO-PROMOTE-TO-HEAVY per R13 / R15 combined effect).

    Minimum fields per C10 v1.0 LOCKED for C3b consumption.
    """
    riser_group_id:        str
    risers:                Tuple[Riser, ...] = field(default_factory=tuple)
    served_room_ids:       Tuple[str, ...] = field(default_factory=tuple)
    """Room IDs (from C12 PlacedRoom) that draw from / drain into this
    riser group. Adjacent rooms may also be affected by tweaks here."""

    chase_width_mm:        float = 600.0
    """Vertical chase width. Standard 600-1200mm per IS 1172."""

    def __post_init__(self) -> None:
        if not self.riser_group_id:
            raise ValueError("RiserGroup.riser_group_id must be non-empty")
        if not self.risers:
            raise ValueError("RiserGroup.risers must contain at least 1 riser")
        if self.chase_width_mm <= 0:
            raise ValueError(
                f"RiserGroup.chase_width_mm must be positive; "
                f"got {self.chase_width_mm}"
            )


C10_STUB_VERSION: Final[str] = "v1.0.LOCKED.stub.S52"

__all__ = ["Riser", "RiserGroup", "C10_STUB_VERSION"]
