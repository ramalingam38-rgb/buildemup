"""
BuildemUp† — Component 7 (Structural Grid) — package init.

Per C7 amendment v0.8 LOCKED. Re-exports WallSegment-related names so
that test code and downstream components can import from a single
canonical location. Also re-exports canonical_serialize and
assert_wall_segment_order_independent from buildemup.utilities for
backwards-compat with v0.6 test code that imported them via C7.

Production code in C7 must NOT import from buildemup.utilities; the
re-exports here are purely for test/import-shim convenience. See
B-241 for CI lint rule (post v1).
"""
from buildemup.components.c07.grid_generator import (
    ColumnPosition,
    Grid,
    GridGenerator,
)
from buildemup.components.c07.wall_segment import (
    WALL_AXIS_CANONICAL_ORDER,
    WALL_ORDER_CONVENTION,
    WallAxis,
    WallSegment,
    WallTag,
    serialize_tags_sorted,
)
from buildemup.utilities.canonical import (
    canonical_serialize,
    assert_wall_segment_order_independent,
)

__all__ = [
    "ColumnPosition",
    "Grid",
    "GridGenerator",
    "WALL_AXIS_CANONICAL_ORDER",
    "WALL_ORDER_CONVENTION",
    "WallAxis",
    "WallSegment",
    "WallTag",
    "serialize_tags_sorted",
    "canonical_serialize",
    "assert_wall_segment_order_independent",
]
