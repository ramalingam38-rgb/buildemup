"""
BuildemUp† — Column domain object.

One column in a building's grid. Used by:
  - Component 7 (structural sizing, foundation design)
  - Component 4 (layout — columns constrain wall placement)
  - Component 9 (services — column locations affect plumbing routing)

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ColumnLocation(str, Enum):
    """Column position in the grid. Affects load calculation + foundation type."""
    INTERIOR = "interior"             # Tributary area = full bay × full bay
    EDGE = "edge"                     # Tributary area = half bay × full bay
    CORNER = "corner"                 # Tributary area = half bay × half bay
    PROPERTY_LINE = "property_line"   # Edge column on property boundary


@dataclass(frozen=True)
class Column:
    """One column in the grid.

    Position is in metres from south-west corner of envelope.
    Cross-section assumed square in v0.6 (rectangular = future).
    """
    column_id: str                    # e.g., "C1", "C2", ...
    x_m: float                        # East offset from origin
    y_m: float                        # North offset from origin
    location: ColumnLocation = ColumnLocation.INTERIOR
    cross_section_mm: int = 230       # Square section side
    concrete_grade: str = "M25"       # IS 456 grade
    steel_grade: str = "Fe500"        # IS 1786 grade
    steel_pct: float = 1.0            # Longitudinal steel %

    def __post_init__(self):
        if self.cross_section_mm < 230:
            raise ValueError(
                f"Column section {self.cross_section_mm}mm < 230mm minimum "
                f"(IS 456 cl. 26.5.3.1)."
            )
        if self.steel_pct < 0.8 or self.steel_pct > 4.0:
            raise ValueError(
                f"Steel % {self.steel_pct} outside IS 456 range (0.8-4.0)."
            )

    @property
    def gross_area_mm2(self) -> float:
        """Cross-section area in mm²."""
        return self.cross_section_mm * self.cross_section_mm

    @property
    def steel_area_mm2(self) -> float:
        """Longitudinal steel area in mm²."""
        return self.gross_area_mm2 * self.steel_pct / 100.0
