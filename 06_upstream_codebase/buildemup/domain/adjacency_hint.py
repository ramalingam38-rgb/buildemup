"""
BuildemUp — AdjacencyHint domain dataclass.

Per ``B-C9-ADJACENCY-HINTS`` amendment v0.1 LOCKED via S43 directive
("Let's do the dependencies on c8&c9 and code that also").

Adjacency knowledge is naturally an INPUT to layout (cultural /
functional / brief-derived), not an output. The cleanest home is
``FloorRoomBrief`` — already shared across C5 / C8 / C9 / C12, already
per-floor. This module defines the value types; FloorRoomBrief gains
an ``adjacency_hints: tuple[AdjacencyHint, ...] = ()`` field.

Per C12 v0.2 Amendment A5:
- HARD = critical functional/cultural adjacency; violation → C12
         rejects the placement.
- SOFT = preference; violation → C14 scores down, C12 doesn't reject.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Final


# B-C9-SCHEMA-VERSION-CONSTANT v0.1 LOCKED via S43 directive
# ("Lock it and start coding"). Consumed by C12 v0.4-A1 schema-version
# probe at ingress to catch semantic-incompatible upstream evolution.
ADJACENCY_HINT_SCHEMA_VERSION: Final[int] = 1


class AdjacencyConstraintKind(str, enum.Enum):
    """v1 two-level typing per C12 v0.2 Amendment A5.

    The reviewer-suggested four-level enum (HARD/SOFT/PREFERRED/AVOID)
    is over-engineered for v1; two levels cover the genuine
    architectural distinction. PREFERRED/AVOID can be added in a
    future amendment without breaking v1 (additive enum extension —
    Python ``str`` enums accept new members).
    """
    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class AdjacencyHint:
    """One pairwise adjacency hint between two rooms on the same floor.

    Canonical form requires ``room_a_id < room_b_id`` lex-ASC. This
    canonicalization makes two briefs with the same hint set in
    different orders hash identically — important for C11a cache-key
    determinism.

    Construction example:
        AdjacencyHint(
            room_a_id="bedroom_1",
            room_b_id="bathroom_1",
            kind=AdjacencyConstraintKind.HARD,
        )

    The ``weight`` field is meaningful only for ``SOFT`` adjacencies;
    C14 scoring multiplies the violation cost by ``weight``. For
    ``HARD`` adjacencies the field is ignored (the violation is a
    hard rejection, not a weighted penalty).
    """
    room_a_id: str
    room_b_id: str
    kind: AdjacencyConstraintKind
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.room_a_id or not self.room_b_id:
            raise ValueError("AdjacencyHint requires non-empty room ids.")
        if self.room_a_id == self.room_b_id:
            raise ValueError(
                f"AdjacencyHint requires distinct rooms; "
                f"got {self.room_a_id!r} twice."
            )
        if self.room_a_id > self.room_b_id:
            raise ValueError(
                f"AdjacencyHint requires canonical order "
                f"room_a_id < room_b_id; got {self.room_a_id!r} > "
                f"{self.room_b_id!r}. Construct as "
                f"AdjacencyHint(room_a_id={self.room_b_id!r}, "
                f"room_b_id={self.room_a_id!r}, ...)"
            )
        if self.weight < 0.0:
            raise ValueError(
                f"AdjacencyHint.weight must be >= 0; got {self.weight}."
            )


__all__ = [
    "ADJACENCY_HINT_SCHEMA_VERSION",
    "AdjacencyConstraintKind",
    "AdjacencyHint",
]
