"""
BuildemUp — Component 14 — contracts (upstream-metadata + category sets)
========================================================================

Per C14 SPEC v0.2 LOCKED (v0.1 § 1.1 + § 11 + v0.2 A8).

This module provides:

1. `RoomMetadata` — the per-room upstream metadata struct threaded into
   C14's orchestrator entry points (per v0.1 § 11). The metadata bundle
   is NOT encoded in C13's LOCKED schema; the orchestrator accepts it
   as a separate `placed_room_metadata` parameter (mirroring C13 Phase
   F's pattern). B-PROJECT-PIPELINE-METADATA-CONTRACT (v0.1 § 12) is
   filed against the recurrence of this pattern.

2. Category keyword sets (per v0.2 A8) — exposed as importable
   module-level constants so downstream consumers know exactly which
   room-category strings C14 treats as "bedroom" / "public" / "private"
   / "circulation". Misclassified rooms produce incorrect circulation
   judgments, and worse, the misclassification is invisible — hence
   A8's category_coverage contract.

3. `EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID` re-export — per v0.2 A2,
   Inv E3' excludes edges where EITHER `room_a_id` OR `room_b_id`
   equals this constant from C13's contracts module.

The category keyword sets are FROZEN at v0.2 LOCK. Modifications go
through B-C12-CATEGORY-NORMALIZATION-GOVERNANCE (v0.2 A8 routed) so
C12 / C13 / C14 stay coordinated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Re-export the EXTERNAL placeholder from C13's contracts.
# Per v0.2 A2 Inv E3', BOTH sides of the edge tuple are checked.
from buildemup.components.c13.contracts import (
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
)


# =============================================================================
# Category keyword sets (per v0.2 A8)
# =============================================================================

BEDROOM_CATEGORY_KEYWORDS: Final[frozenset[str]] = frozenset({
    "bedroom",
    "master_bedroom",
    "guest_bedroom",
    "kids_bedroom",
})
"""Per v0.2 A8.

Room-category strings that C14 treats as "bedroom" for flag emission
(notably TRANSIT_THROUGH_BEDROOM per v0.2 A5 and PRIVACY_GRADIENT_VIOLATION
per v0.1 § 1.3).

Cache-relevant: yes (changes which flags surface).

B-C14-TRANSIT-BEDROOM-DEFINITION-LOCK (LOCK-mandatory) will pin the
exact bedroom-category boundary at v1.0 — specifically whether to
extend to study/pooja/master_bedroom (currently included for master,
not for study/pooja).
"""

PUBLIC_CATEGORY_KEYWORDS: Final[frozenset[str]] = frozenset({
    "living",
    "dining",
    "family",
    "lounge",
    "kitchen",
})
"""Per v0.2 A8.

Room-category strings that C14 treats as "public" for PRIVACY_GRADIENT_VIOLATION
detection. The privacy-gradient invariant says: bedrooms (private) should
NOT be shallower (smaller step_depth) than public rooms.

B-C14-PRIVACY-GRADIENT-FORMULA-LOCK (LOCK-mandatory) will pin the exact
monotonicity formula at v1.0.
"""

PRIVATE_CATEGORY_KEYWORDS: Final[frozenset[str]] = frozenset({
    "bedroom",
    "master_bedroom",
    "guest_bedroom",
    "kids_bedroom",
    "bathroom",
    "study",
    "pooja",
})
"""Per v0.2 A8.

Room-category strings that C14 treats as "private" — a superset of
BEDROOM_CATEGORY_KEYWORDS plus bathroom/study/pooja.
"""

CIRCULATION_CATEGORY_KEYWORDS: Final[frozenset[str]] = frozenset({
    "corridor",
    "foyer",
    "staircase",
})
"""Per v0.2 A8.

Room-category strings that C14 treats as pure circulation. These rooms
are exempt from BOTTLENECK_CONCENTRATION (corridors are SUPPOSED to be
high-betweenness — that's their architectural purpose).
"""


# Union of all category sets (used for category_coverage calculation).
ALL_RECOGNIZED_CATEGORY_KEYWORDS: Final[frozenset[str]] = (
    BEDROOM_CATEGORY_KEYWORDS
    | PUBLIC_CATEGORY_KEYWORDS
    | PRIVATE_CATEGORY_KEYWORDS
    | CIRCULATION_CATEGORY_KEYWORDS
    | frozenset({"main_entrance"})
)
"""Union of all categories C14 recognizes for `category_coverage`
computation per v0.2 A8 Inv E18.

`main_entrance` is included because C13's main_entry_room_id typically
carries that category. It's not flag-relevant in itself, but counts
toward category coverage."""


# =============================================================================
# RoomMetadata (per v0.1 § 1.1 / § 11)
# =============================================================================

@dataclass(frozen=True)
class RoomMetadata:
    """Per-room upstream metadata threaded into C14's orchestrator entry.

    Per v0.1 § 11 + § 1.1, this struct carries the upstream data that
    C13's LOCKED schema does NOT encode but C14 nonetheless needs:

    - `category`: the room-category string (e.g., "bedroom", "living").
      Cross-referenced against the category keyword sets above for
      flag emission.
    - `is_main_entry_room`: True iff this room owns C13's
      `is_main_entry=True` door. Exactly one room per
      SuccessfulDoorPlacement should be True.
    - `is_secondary_door_owner`: Reserved for future use. At v0.2,
      C14 reads primary-edge membership from `primary_door_ids`
      threaded directly into the orchestrator (per v0.1 § 1.1).
      Filed as B-PROJECT-PIPELINE-METADATA-CONTRACT.

    Frozen for hash-stability + replay determinism (Inv E7).
    """
    room_id: str
    category: str
    is_main_entry_room: bool
    is_secondary_door_owner: bool = False

    def __post_init__(self) -> None:
        # Defensive: room_id must be non-empty for canonical sorts to work.
        if not self.room_id:
            raise ValueError(
                "RoomMetadata.room_id must be a non-empty string"
            )
        # Defensive: category must be a string (may be empty if unknown,
        # but unknown categories contribute to low category_coverage per
        # v0.2 A8 Inv E18).
        if not isinstance(self.category, str):
            raise TypeError(
                f"RoomMetadata.category must be str; got {type(self.category)}"
            )


__all__ = [
    "EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID",
    "BEDROOM_CATEGORY_KEYWORDS",
    "PUBLIC_CATEGORY_KEYWORDS",
    "PRIVATE_CATEGORY_KEYWORDS",
    "CIRCULATION_CATEGORY_KEYWORDS",
    "ALL_RECOGNIZED_CATEGORY_KEYWORDS",
    "RoomMetadata",
]
