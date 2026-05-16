"""
BuildemUp† — FloorRoomBrief domain dataclass.

Per C5 SPEC v0.9 LOCKED § 2 (input contract). DRAFT-Q 1 adjudicated to
domain placement (vs contracts/) because multiple components consume it:
C5 (topology), C8 (corridor), C9 (placement).

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FloorRoomBrief:
    """Per-floor room requirements. Multi-floor briefs construct one per floor.

    Domain concept (lives in domain/, not contracts/) — multiple components
    consume it. v1 covers the typical Indian residential floor: bedrooms,
    bathrooms, optional kitchen / living / pooja / utility, plus an open-ended
    `other_rooms` tuple for less-common rooms (study, guest, balcony).

    Per C5 SPEC v0.2 PROPOSED § 2:
      - bedroom_count >= 0 (validated in __post_init__)
      - bathroom_count >= 0 (validated in __post_init__)
      - other_rooms is a tuple to keep the dataclass hashable / frozen-friendly
    """
    bedroom_count: int
    bathroom_count: int
    has_kitchen: bool
    has_living: bool
    has_pooja: bool
    has_utility: bool
    other_rooms: tuple[str, ...] = ()
    floor_label: str = "ground"

    def __post_init__(self) -> None:
        if self.bedroom_count < 0:
            raise ValueError(
                f"bedroom_count must be >= 0; got {self.bedroom_count}"
            )
        if self.bathroom_count < 0:
            raise ValueError(
                f"bathroom_count must be >= 0; got {self.bathroom_count}"
            )


__all__ = ["FloorRoomBrief"]
