"""
BuildemUp — Component 12 — slicing-tree room spec
==================================================

Per C12 SPEC v1.0 LOCKED § 3.1 / § 3.2.

The slicing-tree placement algorithm consumes a RoomSpec per room:
the minimum information needed to place + canonicalize. The full
upstream RefinedCandidate carries more (operator lineage, optimizer
fields, etc.) — those flow through but don't drive placement.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoomSpec:
    """Per-room placement input.

    The slicing-tree algorithm receives a tuple of RoomSpecs (sorted
    canonically by room_id per v0.2-A4 rule #1) and emits PlacedRoom
    instances with realized (x, y, w, d) geometry.

    Fields:
      - room_id: stable identifier (canonicalization key).
      - category: canonical category string (post-normalization).
      - target_width_m / target_depth_m: dimensions chosen by C11b
        (NOT mutated in STRICT mode per v0.2-A3).
      - operator_class_lineage: passed through to PlacedRoom for
        provenance (per v0.3-A7).
    """
    room_id: str
    category: str
    target_width_m: float
    target_depth_m: float
    operator_class_lineage: str = ""

    def __post_init__(self) -> None:
        if not self.room_id:
            raise ValueError("RoomSpec.room_id must be non-empty.")
        if not self.category:
            raise ValueError("RoomSpec.category must be non-empty.")
        if self.target_width_m <= 0.0 or self.target_depth_m <= 0.0:
            raise ValueError(
                f"RoomSpec target dims must be positive; got "
                f"width={self.target_width_m}, depth={self.target_depth_m}."
            )

    @property
    def area_m2(self) -> float:
        return self.target_width_m * self.target_depth_m


__all__ = ["RoomSpec"]
