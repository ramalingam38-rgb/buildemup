"""
BuildemUp† — Floor domain object.

One storey of a building. Used by every component that needs per-floor
information: live load, occupancy, finishes, vertical service routing.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class FloorType(str, Enum):
    """Per-floor functional type. Drives live load + use-case logic."""
    STILT_PARKING = "stilt_parking"      # Open at ground, columns visible
    GROUND = "ground"                     # Living/dining/kitchen typical
    FIRST = "first"                       # Bedrooms typical
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    TERRACE = "terrace"                   # Roof access only, light loads
    WATER_TANK_ROOF = "water_tank_roof"   # Top of overhead tank


# Map floor types to default live loads per IS 875 Part 2 (kN/m²)
DEFAULT_LIVE_LOAD_KNSQM = {
    FloorType.STILT_PARKING:    4.0,    # IS 875 Part 2 cl. 4.1 — passenger car
    FloorType.GROUND:           2.0,    # Residential dwelling
    FloorType.FIRST:            2.0,
    FloorType.SECOND:           2.0,
    FloorType.THIRD:            2.0,
    FloorType.FOURTH:           2.0,
    FloorType.TERRACE:          1.5,    # Roof — accessible
    FloorType.WATER_TANK_ROOF:  0.75,   # Roof — light access only
}


@dataclass(frozen=True)
class Floor:
    """One storey of a building.

    Floor numbering convention:
      - Stilt parking: floor_number = 0, type = STILT_PARKING
      - Ground floor (no stilt): floor_number = 0, type = GROUND
      - With stilt: ground floor = 1, type = GROUND
      - Upper floors: 2, 3, 4...
    """
    floor_number: int
    floor_type: FloorType
    floor_height_m: float = 3.0     # Standard residential
    live_load_knsqm: float = 0.0    # Override; 0 means use default for type
    has_water_tank: bool = False

    def __post_init__(self):
        if self.floor_height_m < 2.4 or self.floor_height_m > 5.0:
            raise ValueError(
                f"Floor height {self.floor_height_m}m unusual for "
                f"residential. Expected 2.4-5.0m."
            )

    @property
    def effective_live_load_knsqm(self) -> float:
        """Live load to use, with default fallback per IS 875 Part 2."""
        if self.live_load_knsqm > 0:
            return self.live_load_knsqm
        return DEFAULT_LIVE_LOAD_KNSQM.get(self.floor_type, 2.0)

    @property
    def is_typical_residential_floor(self) -> bool:
        """True for floors with standard residential live load."""
        return self.floor_type in (
            FloorType.GROUND, FloorType.FIRST, FloorType.SECOND,
            FloorType.THIRD, FloorType.FOURTH,
        )
