"""
BuildemUp† — FloorRequirement + RoomRequirement domain objects.

Per SPEC_v0.2 Section 2.1 — what the user wants on each floor.

RoomRequirement   : one type of room (bedroom, kitchen, etc.) + count
FloorRequirement  : a floor's use + list of room requirements + free-text notes
FloorUse          : what the floor does (residential / stilt / terrace)
RoomType          : the 12 supported room types

These feed into:
  - estimate_floor_area_sqm() which applies circulation_factor=1.30
    (per SPEC_v0.2 Section 4.3, Drawback 5 fix)
  - ensure_staircase_present() which auto-adds staircase if ≥2 floors
    and user didn't include one (Drawback 8 fix)
  - floors_above_ground calculation in Brief.to_structural_grid_input()
    which counts STILT + RESIDENTIAL + TERRACE as load-bearing
    (Drawback 3 clarification)

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from buildemup.domain.exceptions import (
    FloorNumberOutOfRangeError,
    RoomCountNegativeError,
    RoomSizeBelowNbcMinError,
)


class FloorUse(str, Enum):
    """What a floor is used for.

    For structural/load calculation purposes (Component 7), all four
    of these are LOAD-BEARING and count toward floors_above_ground.
    Per Drawback 3 documentation fix.
    """
    STILT_PARKING = "stilt_parking"
    RESIDENTIAL = "residential"
    TERRACE_ACCESSIBLE = "terrace_accessible"
    TERRACE_INACCESSIBLE = "terrace_inaccessible"


class RoomType(str, Enum):
    """The 12 supported room types for v0.1.

    Matches what Indian residential briefs typically contain.
    No 'study', 'gym', 'servant room' in v0.1 — user uses STORE or
    BEDROOM_REGULAR and describes in notes.
    """
    BEDROOM_MASTER = "bedroom_master"
    BEDROOM_REGULAR = "bedroom_regular"
    BATHROOM_ATTACHED = "bathroom_attached"
    BATHROOM_COMMON = "bathroom_common"
    KITCHEN = "kitchen"
    LIVING = "living"
    DINING = "dining"
    POOJA = "pooja"
    BALCONY = "balcony"
    UTILITY = "utility"
    STORE = "store"
    STAIRCASE = "staircase"


# NBC 2016 Part 3 minimum room sizes, in sqm
# (also duplicated in kb_rules/room_minimums.json per single-source pattern)
NBC_MINIMUM_ROOM_SIZES_SQM = {
    RoomType.BEDROOM_MASTER: 9.5,
    RoomType.BEDROOM_REGULAR: 7.5,
    RoomType.BATHROOM_ATTACHED: 1.8,
    RoomType.BATHROOM_COMMON: 2.8,
    RoomType.KITCHEN: 5.0,
    RoomType.LIVING: 9.5,
    RoomType.DINING: 6.0,
    RoomType.POOJA: 1.5,
    RoomType.BALCONY: 1.5,
    RoomType.UTILITY: 2.0,
    RoomType.STORE: 1.5,
    RoomType.STAIRCASE: 5.5,
}


@dataclass(frozen=True)
class RoomRequirement:
    """One type of room and how many the user wants.

    Size precedence (per SPEC_v0.2 Section 4.3):
      1. preferred_size_sqm if given
      2. min_size_sqm if given
      3. NBC_MINIMUM_ROOM_SIZES_SQM default

    Resolved via effective_size_sqm property.
    """
    room_type: RoomType
    count: int
    min_size_sqm: float | None = None
    preferred_size_sqm: float | None = None

    def __post_init__(self) -> None:
        if self.count < 0:
            raise RoomCountNegativeError(
                f"Room count cannot be negative: {self.count}"
            )
        if self.count > 10:
            raise ValueError(
                f"Room count of {self.count} for {self.room_type.value} "
                f"is implausible for residential. Check input."
            )

        # If preferred is given, it must be ≥ min (if min given) and ≥ NBC min
        nbc_min = NBC_MINIMUM_ROOM_SIZES_SQM[self.room_type]

        if self.min_size_sqm is not None:
            if self.min_size_sqm < nbc_min:
                raise RoomSizeBelowNbcMinError(
                    f"min_size_sqm {self.min_size_sqm} for "
                    f"{self.room_type.value} is below NBC minimum "
                    f"{nbc_min} sqm."
                )

        if self.preferred_size_sqm is not None:
            if self.preferred_size_sqm < nbc_min:
                raise RoomSizeBelowNbcMinError(
                    f"preferred_size_sqm {self.preferred_size_sqm} for "
                    f"{self.room_type.value} is below NBC minimum "
                    f"{nbc_min} sqm."
                )
            if (self.min_size_sqm is not None
                    and self.preferred_size_sqm < self.min_size_sqm):
                raise ValueError(
                    f"preferred_size_sqm {self.preferred_size_sqm} < "
                    f"min_size_sqm {self.min_size_sqm}."
                )

    @property
    def effective_size_sqm(self) -> float:
        """The size we actually use for area estimation.

        Precedence: preferred → min → NBC default.
        """
        if self.preferred_size_sqm is not None:
            return self.preferred_size_sqm
        if self.min_size_sqm is not None:
            return self.min_size_sqm
        return NBC_MINIMUM_ROOM_SIZES_SQM[self.room_type]

    @property
    def total_area_sqm(self) -> float:
        """Total area occupied by all rooms of this type."""
        return self.count * self.effective_size_sqm

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "room_type": self.room_type.value,
            "count": self.count,
            "min_size_sqm": self.min_size_sqm,
            "preferred_size_sqm": self.preferred_size_sqm,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "RoomRequirement":
        return cls(
            room_type=RoomType(payload["room_type"]),
            count=payload["count"],
            min_size_sqm=payload.get("min_size_sqm"),
            preferred_size_sqm=payload.get("preferred_size_sqm"),
        )


@dataclass(frozen=True)
class FloorRequirement:
    """What the user wants on one floor.

    For RESIDENTIAL floors, rooms describe the composition.
    For STILT_PARKING and TERRACE floors, rooms is typically empty or
    just ancillary (e.g., STORE on terrace).
    """
    floor_number: int                       # 0 = ground, 1 = first, etc.
    floor_use: FloorUse
    rooms: tuple[RoomRequirement, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if self.floor_number < 0:
            raise FloorNumberOutOfRangeError(
                f"floor_number {self.floor_number} cannot be negative."
            )
        if self.floor_number > 3:
            # G+3 is the max we support in v0.1 per Component 7 scope
            raise FloorNumberOutOfRangeError(
                f"floor_number {self.floor_number} exceeds v0.1 maximum "
                f"(G+3). Taller buildings require high-rise review "
                f"(NBC Part 4 fire safety) — out of scope."
            )

        # For non-residential floors, rooms should typically be empty
        if (self.floor_use == FloorUse.STILT_PARKING and len(self.rooms) > 0):
            # Allow but warn at engine level — don't crash
            pass
        if (self.floor_use == FloorUse.TERRACE_INACCESSIBLE
                and len(self.rooms) > 0):
            pass

    @property
    def is_load_bearing(self) -> bool:
        """All four FloorUse values are load-bearing per Drawback 3."""
        return True

    @property
    def has_staircase(self) -> bool:
        """True if user included a STAIRCASE room on this floor."""
        return any(r.room_type == RoomType.STAIRCASE for r in self.rooms)

    def total_room_area_sqm(self) -> float:
        """Sum of all room areas BEFORE circulation factor.

        Note: for total floor area including walls/passages, use
        estimate_floor_area_sqm() which applies circulation_factor=1.30.
        """
        return sum(r.total_area_sqm for r in self.rooms)

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "floor_number": self.floor_number,
            "floor_use": self.floor_use.value,
            "rooms": [r.to_dict() for r in self.rooms],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "FloorRequirement":
        return cls(
            floor_number=payload["floor_number"],
            floor_use=FloorUse(payload["floor_use"]),
            rooms=tuple(
                RoomRequirement.from_dict(r) for r in payload.get("rooms", [])
            ),
            notes=payload.get("notes", ""),
        )
