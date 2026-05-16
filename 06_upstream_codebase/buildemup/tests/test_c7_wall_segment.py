"""
BuildemUp† — Tests for C7 amendment v0.8 LOCKED (WallSegment emission).

Covers:
    - WallSegment construction (W1-W3 invariants)
    - GridGenerator emits 4 walls in CCW-from-south order
    - Module constants (WALL_ORDER_CONVENTION + WALL_AXIS_CANONICAL_ORDER)
    - serialize_tags_sorted helper
    - Grid.wall_segments_canonical() accessor
    - Grid.wall_segment_by_id() lookup
    - Backwards-compat: wall_segments=() default
    - W8 unit shuffle-order regression via assert_wall_segment_order_independent

Reference: NEXT_CLAUDE_HANDOFF.md (S35 -> S36) Step 1 build queue.

The W8 *integration* shuffle test (full C7 -> C9 -> C10 pipeline) is
deferred until C10 modules exist — see test_c10_replay.py for that one.
"""
from __future__ import annotations

import pytest

from buildemup.components.c07.grid_generator import Grid, GridGenerator
from buildemup.components.c07.wall_segment import (
    WALL_AXIS_CANONICAL_ORDER,
    WALL_ORDER_CONVENTION,
    WallAxis,
    WallSegment,
    WallTag,
    serialize_tags_sorted,
)
from buildemup.utilities.canonical import (
    assert_wall_segment_order_independent,
    canonical_serialize,
)


# ===========================================================================
# Module constants (1 test)
# ===========================================================================


def test_wall_order_convention_matches_canonical_order():
    """The string convention name and the enum-tuple canonical order
    must agree: 'CCW_FROM_SOUTH' implies (SOUTH, EAST, NORTH, WEST)."""
    assert WALL_ORDER_CONVENTION == "CCW_FROM_SOUTH"
    assert WALL_AXIS_CANONICAL_ORDER == (
        WallAxis.SOUTH, WallAxis.EAST, WallAxis.NORTH, WallAxis.WEST,
    )


# ===========================================================================
# WallSegment construction — W1, W2, W3 (4 tests; happy path + 3 invariants)
# ===========================================================================


def test_wall_segment_happy_path_constructs():
    """Valid WallSegment with all fields set; W1/W2/W3 satisfied."""
    w = WallSegment(
        wall_id="WALL_SOUTH",
        axis=WallAxis.SOUTH,
        start_x_m=0.0, start_y_m=0.0,
        end_x_m=10.0, end_y_m=0.0,
        length_m=10.0,
        tags=frozenset({WallTag.EXTERNAL, WallTag.LOAD_BEARING}),
    )
    assert w.wall_id == "WALL_SOUTH"
    assert w.axis == WallAxis.SOUTH
    assert w.length_m == 10.0
    assert WallTag.EXTERNAL in w.tags


def test_wall_segment_w1_violates_when_length_mismatched():
    """W1: declared length_m must equal Euclidean(start, end)."""
    with pytest.raises(ValueError, match=r"\(W1\):"):
        WallSegment(
            wall_id="WALL_BAD",
            axis=WallAxis.SOUTH,
            start_x_m=0.0, start_y_m=0.0,
            end_x_m=10.0, end_y_m=0.0,
            length_m=99.0,                       # wrong
            tags=frozenset({WallTag.EXTERNAL}),
        )


def test_wall_segment_w2_violates_with_empty_tags():
    """W2: every WallSegment must carry at least one WallTag."""
    with pytest.raises(ValueError, match=r"\(W2\):"):
        WallSegment(
            wall_id="WALL_NO_TAG",
            axis=WallAxis.SOUTH,
            start_x_m=0.0, start_y_m=0.0,
            end_x_m=10.0, end_y_m=0.0,
            length_m=10.0,
            tags=frozenset(),                    # empty -> W2 violation
        )


def test_wall_segment_w3_violates_when_not_axis_aligned():
    """W3: v1 walls must be axis-aligned (start_x==end_x OR start_y==end_y)."""
    with pytest.raises(ValueError, match=r"\(W3\):"):
        WallSegment(
            wall_id="WALL_DIAG",
            axis=WallAxis.SOUTH,
            start_x_m=0.0, start_y_m=0.0,
            end_x_m=10.0, end_y_m=5.0,           # diagonal
            length_m=(10.0**2 + 5.0**2) ** 0.5,  # length is correct (W1 OK)
            tags=frozenset({WallTag.EXTERNAL}),
        )


# ===========================================================================
# Lookup methods on Grid (2 tests)
# ===========================================================================


def test_wall_segment_by_id_returns_matching_segment():
    """`wall_segment_by_id` finds the segment with the matching wall_id."""
    grid = GridGenerator().generate(
        envelope_width_m=10.0, envelope_depth_m=12.0,
    )
    south = grid.wall_segment_by_id("WALL_SOUTH")
    assert south.axis == WallAxis.SOUTH
    assert south.length_m == 10.0


def test_wall_segment_by_id_raises_key_error_on_unknown():
    """Unknown wall_id triggers KeyError with informative message."""
    grid = GridGenerator().generate(
        envelope_width_m=10.0, envelope_depth_m=12.0,
    )
    with pytest.raises(KeyError, match=r"WALL_DOES_NOT_EXIST"):
        grid.wall_segment_by_id("WALL_DOES_NOT_EXIST")


# ===========================================================================
# Backwards compatibility (1 test)
# ===========================================================================


def test_grid_constructed_without_wall_segments_is_backwards_compatible():
    """Construct a Grid the old way (no wall_segments arg). Default empty
    tuple preserves all existing C8/C9 fixtures and call sites."""
    grid = Grid(
        columns=[],
        bay_x_m=3.0, bay_y_m=3.0,
        columns_x_count=0, columns_y_count=0,
        envelope_width_m=9.0, envelope_depth_m=9.0,
    )
    assert grid.wall_segments == ()
    assert grid.wall_segments_canonical() == ()


# ===========================================================================
# Ordering — generate emits CCW-from-south for various envelopes (2 tests)
# ===========================================================================


def test_grid_generator_emits_walls_ccw_from_south_square():
    """Square envelope: 4 walls in (SOUTH, EAST, NORTH, WEST) storage order."""
    grid = GridGenerator().generate(
        envelope_width_m=9.0, envelope_depth_m=9.0,
    )
    axes = tuple(w.axis for w in grid.wall_segments)
    assert axes == (
        WallAxis.SOUTH, WallAxis.EAST, WallAxis.NORTH, WallAxis.WEST,
    )
    # W4: exactly 4 walls; W7: total length == perimeter.
    assert len(grid.wall_segments) == 4
    perim = 2 * grid.envelope_width_m + 2 * grid.envelope_depth_m
    assert sum(w.length_m for w in grid.wall_segments) == pytest.approx(perim)


def test_grid_generator_emits_walls_ccw_from_south_rectangular():
    """Rectangular envelope: storage order matches CCW-from-south, lengths
    match width/depth alternating."""
    grid = GridGenerator().generate(
        envelope_width_m=12.0, envelope_depth_m=8.0,
    )
    by_axis = {w.axis: w for w in grid.wall_segments}
    assert by_axis[WallAxis.SOUTH].length_m == 12.0
    assert by_axis[WallAxis.NORTH].length_m == 12.0
    assert by_axis[WallAxis.EAST].length_m == 8.0
    assert by_axis[WallAxis.WEST].length_m == 8.0
    # W6: wall_ids unique.
    ids = {w.wall_id for w in grid.wall_segments}
    assert len(ids) == 4
    # W5: every axis once.
    axes = {w.axis for w in grid.wall_segments}
    assert axes == set(WallAxis)


# ===========================================================================
# serialize_tags_sorted helper (1 test)
# ===========================================================================


def test_serialize_tags_sorted_returns_lex_ascending_tuple():
    """Helper returns a tuple sorted lex-ASC by tag .value, regardless
    of frozenset iteration order."""
    tags = frozenset({WallTag.LOAD_BEARING, WallTag.EXTERNAL})
    serialised = serialize_tags_sorted(tags)
    assert isinstance(serialised, tuple)
    assert serialised == ("external", "load_bearing")


# ===========================================================================
# Canonical accessor (3 NEW v0.6/v0.7 tests)
# ===========================================================================


def test_wall_segments_canonical_returns_canonical_order_regardless_of_storage():
    """`wall_segments_canonical()` returns walls in (SOUTH, EAST, NORTH,
    WEST) order even if storage tuple is shuffled."""
    grid = GridGenerator().generate(
        envelope_width_m=10.0, envelope_depth_m=10.0,
    )
    # Build a Grid with the SAME walls but stored in reverse order.
    reversed_walls = tuple(reversed(grid.wall_segments))
    grid_reversed = Grid(
        columns=grid.columns,
        bay_x_m=grid.bay_x_m, bay_y_m=grid.bay_y_m,
        columns_x_count=grid.columns_x_count,
        columns_y_count=grid.columns_y_count,
        envelope_width_m=grid.envelope_width_m,
        envelope_depth_m=grid.envelope_depth_m,
        wall_segments=reversed_walls,
    )
    canon_axes = tuple(w.axis for w in grid_reversed.wall_segments_canonical())
    assert canon_axes == (
        WallAxis.SOUTH, WallAxis.EAST, WallAxis.NORTH, WallAxis.WEST,
    )


def test_wall_segments_canonical_silently_omits_missing_axes():
    """Forward-compat with non-rectangular envelopes (post B-066): if a
    Grid only has SOUTH and EAST walls, the canonical accessor returns
    only those two — silently omits NORTH and WEST."""
    south = WallSegment(
        wall_id="WS", axis=WallAxis.SOUTH,
        start_x_m=0.0, start_y_m=0.0, end_x_m=5.0, end_y_m=0.0,
        length_m=5.0, tags=frozenset({WallTag.EXTERNAL}),
    )
    east = WallSegment(
        wall_id="WE", axis=WallAxis.EAST,
        start_x_m=5.0, start_y_m=0.0, end_x_m=5.0, end_y_m=4.0,
        length_m=4.0, tags=frozenset({WallTag.EXTERNAL}),
    )
    grid = Grid(
        columns=[], bay_x_m=3.0, bay_y_m=3.0,
        columns_x_count=0, columns_y_count=0,
        envelope_width_m=5.0, envelope_depth_m=4.0,
        wall_segments=(south, east),
    )
    canon = grid.wall_segments_canonical()
    assert tuple(w.axis for w in canon) == (WallAxis.SOUTH, WallAxis.EAST)


def test_assert_wall_segment_order_independent_detects_violation_and_pass():
    """The `assert_wall_segment_order_independent` helper itself: passes
    on order-independent functions and raises AssertionError on
    ordering-dependent ones."""
    # Build factory: produces a Grid with the same envelope but lets
    # the caller specify the wall_segments tuple ordering explicitly.
    base = GridGenerator().generate(
        envelope_width_m=10.0, envelope_depth_m=8.0,
    )

    def factory(segments_override):
        # If override empty, return canonical Grid.
        if not segments_override:
            return base
        return Grid(
            columns=base.columns,
            bay_x_m=base.bay_x_m, bay_y_m=base.bay_y_m,
            columns_x_count=base.columns_x_count,
            columns_y_count=base.columns_y_count,
            envelope_width_m=base.envelope_width_m,
            envelope_depth_m=base.envelope_depth_m,
            wall_segments=segments_override,
        )

    # Order-INDEPENDENT function: uses canonical accessor -> passes.
    def good_fn(g):
        return tuple(w.axis.value for w in g.wall_segments_canonical())

    assert_wall_segment_order_independent(factory, good_fn)

    # Order-DEPENDENT function: uses raw .wall_segments -> fails.
    def bad_fn(g):
        return tuple(w.axis.value for w in g.wall_segments)

    with pytest.raises(AssertionError, match="W8 violation"):
        assert_wall_segment_order_independent(factory, bad_fn)


# ===========================================================================
# W8 unit shuffle-order regression (2 tests)
# ===========================================================================


def test_w8_serializing_canonical_walls_is_shuffle_invariant():
    """Canonicalising the OUTPUT of `wall_segments_canonical()` produces
    byte-identical JSON regardless of underlying wall_segments storage
    order. This is the W8 invariant in test form."""
    base = GridGenerator().generate(
        envelope_width_m=11.0, envelope_depth_m=7.0,
    )

    def factory(segments_override):
        if not segments_override:
            return base
        return Grid(
            columns=base.columns,
            bay_x_m=base.bay_x_m, bay_y_m=base.bay_y_m,
            columns_x_count=base.columns_x_count,
            columns_y_count=base.columns_y_count,
            envelope_width_m=base.envelope_width_m,
            envelope_depth_m=base.envelope_depth_m,
            wall_segments=segments_override,
        )

    def fn(g):
        # Emit a per-wall summary using the canonical accessor only.
        return [
            {
                "wall_id": w.wall_id,
                "axis": w.axis.value,
                "length_m": w.length_m,
                "tags": serialize_tags_sorted(w.tags),
            }
            for w in g.wall_segments_canonical()
        ]

    assert_wall_segment_order_independent(factory, fn)


def test_w8_summed_wall_length_invariant_under_shuffle():
    """Order-independent aggregations (sum, set membership) survive
    a wall_segments shuffle. This is a positive control on the helper."""
    base = GridGenerator().generate(
        envelope_width_m=9.0, envelope_depth_m=6.0,
    )

    def factory(segments_override):
        if not segments_override:
            return base
        return Grid(
            columns=base.columns,
            bay_x_m=base.bay_x_m, bay_y_m=base.bay_y_m,
            columns_x_count=base.columns_x_count,
            columns_y_count=base.columns_y_count,
            envelope_width_m=base.envelope_width_m,
            envelope_depth_m=base.envelope_depth_m,
            wall_segments=segments_override,
        )

    def fn(g):
        return {
            "perimeter": sum(w.length_m for w in g.wall_segments_canonical()),
            "axes_present": sorted(
                w.axis.value for w in g.wall_segments_canonical()
            ),
        }

    assert_wall_segment_order_independent(factory, fn)


# ===========================================================================
# canonical_serialize utility tests (3 tests)
# ===========================================================================


def test_canonical_serialize_sorts_dict_keys_lex_ascending():
    """Same dict in different insertion order serialises identically."""
    d1 = {"b": 1, "a": 2, "c": 3}
    d2 = {"c": 3, "a": 2, "b": 1}
    assert canonical_serialize(d1) == canonical_serialize(d2)
    assert canonical_serialize(d1) == '{"a":2,"b":1,"c":3}'


def test_canonical_serialize_handles_frozenset_of_enum_deterministically():
    """frozenset of WallTag values converted to sorted list of .value
    strings — independent of iteration order."""
    tags_a = frozenset({WallTag.EXTERNAL, WallTag.LOAD_BEARING})
    tags_b = frozenset({WallTag.LOAD_BEARING, WallTag.EXTERNAL})
    assert canonical_serialize(tags_a) == canonical_serialize(tags_b)
    assert canonical_serialize(tags_a) == '["external","load_bearing"]'


def test_canonical_serialize_rounds_floats_to_six_decimals():
    """FP precision normalised: 0.123456789 rounds to 0.123457."""
    out = canonical_serialize({"x": 0.1234567891234})
    assert "0.123457" in out
    # Nested in dataclass is also rounded.
    grid = Grid(
        columns=[], bay_x_m=3.000000123, bay_y_m=3.0,
        columns_x_count=0, columns_y_count=0,
        envelope_width_m=9.0, envelope_depth_m=9.0,
    )
    out2 = canonical_serialize(grid)
    # bay_x_m rounds to 3.0 (six decimals truncated to integer-equivalent).
    assert '"bay_x_m":3.0' in out2 or '"bay_x_m":3.000000' in out2
