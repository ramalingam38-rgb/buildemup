"""
C7 — Structural Grid Engine — UPSTREAM STUB for C3b consumption
=================================================================

NOTE: STUB covering only the surface C3b consumes. The real C7
(LOCKED v0.8) provides full column sizing, beam sizing, IS 456
verification, foundation type selection, and cost estimation.

C3b consumes:
  - StructuralGridCell       — for affected_grid_cells references
                                + load-bearing wall context

Per spec § 3 Phase β step 4.2:
  'Load-bearing wall involvement → C7 structural grid; tweak affects
   a wall marked load-bearing OR within 300mm of a column'

Stability: PINNED to C7 v0.8.LOCKED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, Tuple


@dataclass(frozen=True)
class GridColumn:
    """A single structural column at a grid intersection. C3b uses
    column positions for the load-bearing-proximity check
    (LOAD_BEARING_PROXIMITY_MM)."""
    column_id:     str
    x_mm:          float
    y_mm:          float
    floor:         int
    size_mm:       Tuple[int, int]
    """(width, depth) in mm. e.g. (230, 230) for G+0 standard."""

    def __post_init__(self) -> None:
        if not self.column_id:
            raise ValueError("GridColumn.column_id must be non-empty")


@dataclass(frozen=True)
class StructuralGridCell:
    """One bay of the structural grid — a rectangular region bounded
    by 4 columns.

    Minimum fields per C7 v0.8 LOCKED for C3b consumption:
      - cell_id: stable identifier
      - bounding columns: which 4 columns form the corners
      - bay_dimensions_m: width × depth in meters
      - is_load_bearing_perimeter: walls on this bay's edge are
        load-bearing if they sit on a column line
    """
    cell_id:                       str
    floor:                         int
    corner_column_ids:             Tuple[str, str, str, str]
    """(NW, NE, SE, SW) column IDs."""

    bay_dimensions_m:              Tuple[float, float]
    """(width, depth) in meters."""

    is_load_bearing_perimeter:     bool = True
    """C3b uses this to detect tweaks affecting load-bearing walls."""

    contains_riser_chase:          bool = False
    """C3b uses this for wet-zone restage tweak context."""

    def __post_init__(self) -> None:
        if not self.cell_id:
            raise ValueError("StructuralGridCell.cell_id must be non-empty")
        if len(self.corner_column_ids) != 4:
            raise ValueError(
                f"StructuralGridCell.corner_column_ids must be 4 IDs; "
                f"got {len(self.corner_column_ids)}"
            )
        w, d = self.bay_dimensions_m
        if w <= 0 or d <= 0:
            raise ValueError(
                f"StructuralGridCell.bay_dimensions_m must both be positive; "
                f"got {self.bay_dimensions_m!r}"
            )


@dataclass(frozen=True)
class StructuralGrid:
    """The whole structural grid for one or more floors.
    C3b uses this for the per-instance severity context vector."""
    grid_id:        str
    floor_count:    int
    columns:        Tuple[GridColumn, ...] = field(default_factory=tuple)
    cells:          Tuple[StructuralGridCell, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.grid_id:
            raise ValueError("StructuralGrid.grid_id must be non-empty")
        if self.floor_count < 1:
            raise ValueError(
                f"StructuralGrid.floor_count must be >= 1; "
                f"got {self.floor_count}"
            )


C7_STUB_VERSION: Final[str] = "v0.8.LOCKED.stub.S52"

__all__ = [
    "GridColumn", "StructuralGridCell", "StructuralGrid",
    "C7_STUB_VERSION",
]
