"""
BuildemUp† — FloorRoomBrief domain dataclass.

Per C5 SPEC v0.9 LOCKED § 2 (input contract). DRAFT-Q 1 adjudicated to
domain placement (vs contracts/) because multiple components consume it:
C5 (topology), C8 (corridor), C9 (placement).

Amended per Spec #2 v0.11 LOCKED (C9 Amendment — `has_master_bedroom`
flag on FloorRoomBrief) — B-NEW-T3 enabler #2 of 4.

Amended per ``B-C9-ADJACENCY-HINTS`` v0.1 LOCKED via S43 directive
("Let's do the dependencies on c8&c9 and code that also") — adds
``adjacency_hints: tuple[AdjacencyHint, ...] = ()`` for C12 consumption.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from buildemup.domain.adjacency_hint import AdjacencyHint


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

    Per Spec #2 v0.11 LOCKED (C9 Amendment for B-NEW-T3): adds
    ``has_master_bedroom: bool = True`` orchestration-contextual flag.
    See the field docstring for the full normative semantics.

    Per ``B-C9-ADJACENCY-HINTS`` v0.1 LOCKED via S43 directive: adds
    ``adjacency_hints: tuple[AdjacencyHint, ...] = ()`` for C12
    placement consumption. Default empty tuple preserves byte-identical
    behaviour for every existing single-floor caller.
    """
    bedroom_count: int
    bathroom_count: int
    has_kitchen: bool
    has_living: bool
    has_pooja: bool
    has_utility: bool
    other_rooms: tuple[str, ...] = ()
    floor_label: str = "ground"
    has_master_bedroom: bool = True
    """Whether THIS floor hosts the master bedroom (and en-suite master bathroom).

    NATURE OF THIS FIELD (CRITICAL-1 from v0.8 critique walk):
    This is **orchestration-contextual metadata, not an intrinsic floor
    property.** A floor does not objectively "have a master bedroom" — that
    designation is a dwelling-level decision (which floor of an N-floor
    dwelling hosts the master bedroom). This field is the per-floor signal
    the C11a orchestrator passes to C9 so room sizing knows whether to
    designate bedroom #1 / bathroom #1 as master.

    The field LIVES on FloorRoomBrief because that's the cleanest signal at
    the C9 boundary, but its VALUE is set by orchestration upstream (Spec #4
    constructs per-floor briefs from a MultiFloorDwellingBrief, using
    ``iter_floors_with_master_flag()`` per Spec #1 § 3.3).

    DEFAULT (True): standalone FloorRoomBrief instances default to True
    because they conventionally represent single-floor dwellings, where
    the only floor IS the master floor by definition. This preserves
    v0.7 byte-identical behaviour for every existing single-floor caller.

    HASH PARTICIPATION (MINOR-2 from v0.8 critique walk): this field
    participates in dataclass equality and hash. Two FloorRoomBriefs
    identical except for has_master_bedroom are NOT equal and hash
    differently. This propagates upward into MultiFloorDwellingBrief's
    hash, which is why this amendment requires a C11A_CACHE_KEY_VERSION
    bump per Spec #1 § 3.6 normalization-versioning contract.

    CONTROLS BOTH BEDROOM AND BATHROOM MASTER DESIGNATION
    (see Spec #2 § 3.4 for the en-suite coupling rationale).
    """

    adjacency_hints: tuple[AdjacencyHint, ...] = ()
    """Per-floor adjacency hints consumed by C12 placement.

    Per ``B-C9-ADJACENCY-HINTS`` v0.1 LOCKED via S43 directive.

    Default empty tuple preserves byte-identical behaviour for every
    existing single-floor caller — no test regression.

    Canonical ordering invariant (enforced in __post_init__):
    sorted lex-ASC by ``(room_a_id, room_b_id)`` so the brief's hash
    is deterministic across ordering permutations of the same hint
    set. Same-pair duplicates raise ValueError.

    CACHE-KEY IMPACT: same hash-participation logic as
    has_master_bedroom — propagates into C11a cache keys. C11a SHOULD
    bump its cache-key version on adopting this amendment. Filed as
    ``B-C11A-CACHE-KEY-BUMP-ADJACENCY`` (cross-component note).
    """

    def __post_init__(self) -> None:
        if self.bedroom_count < 0:
            raise ValueError(
                f"bedroom_count must be >= 0; got {self.bedroom_count}"
            )
        if self.bathroom_count < 0:
            raise ValueError(
                f"bathroom_count must be >= 0; got {self.bathroom_count}"
            )
        # Inv E: adjacency_hints sorted lex-ASC by (room_a_id, room_b_id).
        keys = [(h.room_a_id, h.room_b_id) for h in self.adjacency_hints]
        if keys != sorted(keys):
            raise ValueError(
                f"FloorRoomBrief.adjacency_hints must be sorted lex-ASC "
                f"by (room_a_id, room_b_id); got order {keys}."
            )
        # Inv F: no duplicate (room_a_id, room_b_id) pairs.
        if len(set(keys)) != len(keys):
            raise ValueError(
                f"FloorRoomBrief.adjacency_hints contains duplicate "
                f"(room_a_id, room_b_id) pairs; got {keys}."
            )


__all__ = ["FloorRoomBrief"]
