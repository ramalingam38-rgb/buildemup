"""
BuildemUp† — Grid domain object.

Shared grid abstraction. Wraps the existing c07 Grid for backwards
compatibility while providing a clean import path for non-Component-7
consumers (Component 4 layout, Component 9 services, etc.).

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from buildemup.domain.column import Column


@dataclass(frozen=True)
class DomainGrid:
    """Column grid for a building.

    n_cols × n_rows columns, with bay sizes between them.
    bay_x_m and bay_y_m are arrays of length (n_cols-1) and (n_rows-1)
    respectively, giving the spacing between consecutive column lines.

    For a uniform grid:
      bay_x_m = [4.0, 4.0]    # 3 columns: 0, 4, 8
      bay_y_m = [3.6, 3.6]    # 3 rows
    """
    n_cols: int                       # Columns in X direction (1-indexed)
    n_rows: int                       # Rows in Y direction
    bay_x_m: tuple[float, ...]        # Bay widths (length = n_cols-1)
    bay_y_m: tuple[float, ...]        # Bay depths (length = n_rows-1)
    columns: tuple[Column, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.n_cols < 2 or self.n_rows < 2:
            raise ValueError(
                f"Grid needs at least 2×2 columns. Got {self.n_cols}×{self.n_rows}."
            )
        if len(self.bay_x_m) != self.n_cols - 1:
            raise ValueError(
                f"bay_x_m length must be n_cols-1 = {self.n_cols-1}. "
                f"Got {len(self.bay_x_m)}."
            )
        if len(self.bay_y_m) != self.n_rows - 1:
            raise ValueError(
                f"bay_y_m length must be n_rows-1 = {self.n_rows-1}. "
                f"Got {len(self.bay_y_m)}."
            )

    @property
    def total_columns(self) -> int:
        return self.n_cols * self.n_rows

    @property
    def longest_bay_m(self) -> float:
        """Longest single bay span — drives beam sizing + sensitivity."""
        all_bays = list(self.bay_x_m) + list(self.bay_y_m)
        return max(all_bays) if all_bays else 0.0

    @property
    def total_width_m(self) -> float:
        return sum(self.bay_x_m)

    @property
    def total_depth_m(self) -> float:
        return sum(self.bay_y_m)
