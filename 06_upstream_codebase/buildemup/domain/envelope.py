"""
BuildemUp† — Envelope domain object.

The buildable footprint of a building on a plot. Includes plot
orientation (compass direction the plot faces) and physical dimensions.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class PlotOrientation(str, Enum):
    """Compass direction the plot's main entrance faces.

    Used by:
      - Solar/Vastu logic (Component 5)
      - Wind direction (Component 7 wind load)
      - Setback rules (Component 6)
    """
    NORTH = "N"
    NORTHEAST = "NE"
    EAST = "E"
    SOUTHEAST = "SE"
    SOUTH = "S"
    SOUTHWEST = "SW"
    WEST = "W"
    NORTHWEST = "NW"


@dataclass(frozen=True)
class Envelope:
    """Buildable rectangular footprint after setbacks.

    All measurements in metres. Origin = south-west corner of envelope.

    For non-rectangular plots, this represents the bounding-box envelope.
    Re-entrant corners are tracked as separate fields (used by Component 7
    regularity checks).
    """
    width_m: float          # East-west extent (X axis)
    depth_m: float          # North-south extent (Y axis)
    facing: PlotOrientation = PlotOrientation.NORTH

    # Re-entrant corner depths (for L/U-shaped plans)
    re_entrant_x_m: float = 0.0
    re_entrant_y_m: float = 0.0

    # Property-line constraint flags
    is_property_line_north: bool = False
    is_property_line_south: bool = False
    is_property_line_east: bool = False
    is_property_line_west: bool = False

    def __post_init__(self):
        if self.width_m < 5.0 or self.depth_m < 5.0:
            raise ValueError(
                f"Envelope too small: {self.width_m}m × {self.depth_m}m. "
                f"Minimum 5×5m required for structural design."
            )
        if self.re_entrant_x_m < 0 or self.re_entrant_y_m < 0:
            raise ValueError(
                f"Re-entrant corner depths must be ≥ 0. "
                f"Got x={self.re_entrant_x_m}, y={self.re_entrant_y_m}"
            )

    @property
    def area_sqm(self) -> float:
        """Gross rectangular area, ignoring re-entrant corners."""
        return self.width_m * self.depth_m

    @property
    def net_area_sqm(self) -> float:
        """Net buildable area, accounting for re-entrant corners."""
        return self.area_sqm - (self.re_entrant_x_m * self.re_entrant_y_m)

    @property
    def aspect_ratio(self) -> float:
        """Long edge / short edge. Used for plan regularity check."""
        if self.width_m <= 0 or self.depth_m <= 0:
            return 1.0
        long_edge = max(self.width_m, self.depth_m)
        short_edge = min(self.width_m, self.depth_m)
        return long_edge / short_edge

    @property
    def has_re_entrant(self) -> bool:
        return self.re_entrant_x_m > 0 or self.re_entrant_y_m > 0

    @property
    def is_property_line_edge(self) -> bool:
        """True if any side is a property line (affects foundation type)."""
        return (self.is_property_line_north or self.is_property_line_south
                or self.is_property_line_east or self.is_property_line_west)
