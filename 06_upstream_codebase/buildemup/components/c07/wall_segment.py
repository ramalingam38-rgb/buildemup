"""
BuildemUp† — Component 7 (Structural Grid) — wall_segment.py

Per C7 amendment v0.8 LOCKED (B-212 resolution).

Adds WallSegment emission to the Grid output without breaking any
existing C7 / C8 / C9 call sites. Backwards-compat: Grid's new
`wall_segments` field defaults to an empty tuple.

Public surface:
  Constants:
    - WALL_ORDER_CONVENTION = "CCW_FROM_SOUTH"
    - WALL_AXIS_CANONICAL_ORDER (SOUTH, EAST, NORTH, WEST)
  Enums:
    - WallAxis     (project-north +y; true-north handled by C6)
    - WallTag      (EXTERNAL / INTERNAL / LOAD_BEARING)
  Dataclass:
    - WallSegment  (frozen; W1-W3 invariants enforced in __post_init__)
  Helper:
    - serialize_tags_sorted(tags) -> tuple[str, ...]

Invariants W1-W7 are enforced at construction (W1-W3 in WallSegment;
W4-W7 in GridGenerator.generate). W8 is API/test-level only — production
code MUST use Grid.wall_segments_canonical() — see grid_generator.py.

†= placeholder name marker.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Final


# =============================================================================
# Module constants
# =============================================================================

WALL_ORDER_CONVENTION: Final[str] = "CCW_FROM_SOUTH"
"""Storage-order convention for v1 rectangular envelopes: walls listed
counter-clockwise starting from the SOUTH wall. Production code MUST NOT
rely on storage order — use Grid.wall_segments_canonical() instead.
This constant exists for documentation and audit-tool purposes."""


# =============================================================================
# Enums
# =============================================================================


class WallAxis(str, Enum):
    """Project-coordinate-system wall axes.

    NORTH = PROJECT-NORTH (+y of envelope coord system).
    True-north handled by C6 OrientedCandidate.
    """
    NORTH = "north"
    SOUTH = "south"
    EAST  = "east"
    WEST  = "west"


WALL_AXIS_CANONICAL_ORDER: Final[tuple[WallAxis, ...]] = (
    WallAxis.SOUTH, WallAxis.EAST, WallAxis.NORTH, WallAxis.WEST,
)
"""Canonical iteration order matching WALL_ORDER_CONVENTION.

Production code paths MUST use Grid.wall_segments_canonical() rather than
iterating over Grid.wall_segments directly. See § 3 W8 invariant in spec.
Direct iteration over Grid.wall_segments is reserved for canonical-
serialisation snapshots that explicitly want raw storage order."""


class WallTag(str, Enum):
    EXTERNAL      = "external"
    INTERNAL      = "internal"
    LOAD_BEARING  = "load_bearing"


# =============================================================================
# Helper
# =============================================================================


def serialize_tags_sorted(tags: frozenset[WallTag]) -> tuple[str, ...]:
    """Return tag values sorted lex-ASC as a tuple.

    Tuple chosen over frozenset for deterministic JSON serialisation order.
    Used by canonical_serialize machinery.
    """
    return tuple(sorted(t.value for t in tags))


# =============================================================================
# Dataclass
# =============================================================================


@dataclass(frozen=True)
class WallSegment:
    """A single perimeter wall of the envelope.

    Per C7 amendment v0.8 LOCKED. Frozen; W1-W3 invariants enforced in
    __post_init__:

      W1 — length_m matches Euclidean(start, end)  (tolerance 1e-6 m)
      W2 — every WallSegment carries at least one WallTag
      W3 — v1 walls axis-aligned (start_x == end_x OR start_y == end_y)
    """
    wall_id: str
    axis: WallAxis
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float
    length_m: float
    tags: frozenset[WallTag] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        # Type checks first so downstream comparisons are safe.
        if not isinstance(self.wall_id, str) or not self.wall_id:
            raise ValueError(
                f"WallSegment.wall_id must be a non-empty string; "
                f"got {self.wall_id!r}"
            )
        if not isinstance(self.axis, WallAxis):
            raise ValueError(
                f"WallSegment.axis must be WallAxis; got {type(self.axis).__name__}"
            )
        for fname in ("start_x_m", "start_y_m", "end_x_m", "end_y_m", "length_m"):
            v = getattr(self, fname)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(
                    f"WallSegment.{fname} must be float; got {type(v).__name__}"
                )
        if not isinstance(self.tags, frozenset):
            raise ValueError(
                f"WallSegment.tags must be frozenset[WallTag]; "
                f"got {type(self.tags).__name__}"
            )
        for t in self.tags:
            if not isinstance(t, WallTag):
                raise ValueError(
                    f"WallSegment.tags element must be WallTag; "
                    f"got {type(t).__name__}"
                )

        # W2: at least one tag.
        if len(self.tags) == 0:
            raise ValueError(
                f"WallSegment[{self.wall_id}] (W2): tags must contain "
                f"at least one WallTag"
            )

        # W3: v1 axis-aligned.
        if not (
            math.isclose(self.start_x_m, self.end_x_m, abs_tol=1e-6)
            or math.isclose(self.start_y_m, self.end_y_m, abs_tol=1e-6)
        ):
            raise ValueError(
                f"WallSegment[{self.wall_id}] (W3): v1 walls must be "
                f"axis-aligned; got start=({self.start_x_m},{self.start_y_m}) "
                f"end=({self.end_x_m},{self.end_y_m})"
            )

        # W1: length matches Euclidean distance.
        dx = self.end_x_m - self.start_x_m
        dy = self.end_y_m - self.start_y_m
        euclid = math.hypot(dx, dy)
        if not math.isclose(self.length_m, euclid, abs_tol=1e-6):
            raise ValueError(
                f"WallSegment[{self.wall_id}] (W1): length_m={self.length_m} "
                f"does not match Euclidean distance {euclid:.6f}"
            )


__all__ = [
    "WALL_ORDER_CONVENTION",
    "WALL_AXIS_CANONICAL_ORDER",
    "WallAxis",
    "WallTag",
    "WallSegment",
    "serialize_tags_sorted",
]
