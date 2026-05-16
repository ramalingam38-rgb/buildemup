"""
Tests for B-NEW-K (S38): C7 staircase clearance — W9 invariant.

Verifies:
  1. ``Staircase`` dataclass validation (frozen + per-field guards)
  2. ``Grid.__post_init__`` W9 enforcement when staircase is set
  3. ``validate_staircase_clearance(grid, staircase)`` predicate
  4. Backwards-compat: Grid with no staircase constructs cleanly
  5. NBC-grounded constants are at the documented minimums

Per C7 AMENDMENT v0.8 LOCKED + B-NEW-K v0.1 PROPOSED.
"""
from __future__ import annotations

import pytest

from buildemup.components.c07.grid_generator import (
    Grid,
    MIN_STAIRCASE_LANDING_DEPTH_M,
    MIN_STAIRCASE_WIDTH_M,
    Staircase,
    validate_staircase_clearance,
)
from buildemup.components.c07.wall_segment import WallAxis


# Reusable fixtures
def _envelope_grid(
    width_m: float = 9.0,
    depth_m: float = 12.0,
    *,
    staircase: Staircase | None = None,
) -> Grid:
    """Minimal Grid with no columns/walls; used to exercise W9 logic only."""
    return Grid(
        columns=[],
        bay_x_m=3.0,
        bay_y_m=3.0,
        columns_x_count=2,
        columns_y_count=2,
        envelope_width_m=width_m,
        envelope_depth_m=depth_m,
        wall_segments=(),
        staircase=staircase,
    )


# =============================================================================
# Staircase dataclass validation
# =============================================================================


def test_staircase_construction_happy() -> None:
    """A well-formed Staircase constructs without error."""
    s = Staircase(
        origin_x_m=0.0,
        origin_y_m=0.0,
        width_m=1.0,
        landing_depth_m=1.0,
        anchor=WallAxis.SOUTH,
    )
    assert s.width_m == 1.0
    assert s.landing_depth_m == 1.0
    assert s.anchor is WallAxis.SOUTH


def test_staircase_zero_width_rejected() -> None:
    """width_m must be > 0."""
    with pytest.raises(ValueError, match="width_m must be > 0"):
        Staircase(
            origin_x_m=0.0, origin_y_m=0.0,
            width_m=0.0, landing_depth_m=1.0,
        )


def test_staircase_negative_depth_rejected() -> None:
    """landing_depth_m must be > 0."""
    with pytest.raises(ValueError, match="landing_depth_m must be > 0"):
        Staircase(
            origin_x_m=0.0, origin_y_m=0.0,
            width_m=1.0, landing_depth_m=-0.5,
        )


def test_staircase_negative_origin_rejected() -> None:
    """Origin coordinates must be non-negative."""
    with pytest.raises(ValueError, match="origin must be non-negative"):
        Staircase(
            origin_x_m=-0.1, origin_y_m=0.0,
            width_m=1.0, landing_depth_m=1.0,
        )


def test_staircase_bad_anchor_type_rejected() -> None:
    """anchor must be WallAxis or None."""
    with pytest.raises(ValueError, match="anchor must be WallAxis or None"):
        Staircase(
            origin_x_m=0.0, origin_y_m=0.0,
            width_m=1.0, landing_depth_m=1.0,
            anchor="east",  # type: ignore[arg-type]
        )


def test_staircase_anchor_none_allowed() -> None:
    """Centre placements (anchor=None) are valid."""
    s = Staircase(
        origin_x_m=3.0, origin_y_m=4.0,
        width_m=1.0, landing_depth_m=1.0,
        anchor=None,
    )
    assert s.anchor is None


# =============================================================================
# Grid.__post_init__ W9 enforcement
# =============================================================================


def test_grid_with_no_staircase_constructs_cleanly() -> None:
    """Backwards-compat: Grid with default staircase=None always OK."""
    g = _envelope_grid(width_m=9.0, depth_m=12.0)
    assert g.staircase is None


def test_grid_with_valid_staircase_constructs() -> None:
    """A valid staircase passing W9 lets Grid construct."""
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=1.0, landing_depth_m=1.0,
        anchor=WallAxis.SOUTH,
    )
    g = _envelope_grid(width_m=9.0, depth_m=12.0, staircase=s)
    assert g.staircase is s


def test_grid_w9a_width_below_nbc_raises() -> None:
    """W9-a: width below NBC minimum rejects at Grid construction."""
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=0.5,  # below MIN_STAIRCASE_WIDTH_M
        landing_depth_m=1.0,
        anchor=WallAxis.SOUTH,
    )
    with pytest.raises(ValueError, match="W9-a: staircase width"):
        _envelope_grid(staircase=s)


def test_grid_w9b_landing_below_nbc_raises() -> None:
    """W9-b: landing depth below NBC minimum rejects at Grid construction."""
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=1.0,
        landing_depth_m=0.5,  # below MIN_STAIRCASE_LANDING_DEPTH_M
        anchor=WallAxis.SOUTH,
    )
    with pytest.raises(ValueError, match="W9-b: landing depth"):
        _envelope_grid(staircase=s)


def test_grid_w9c_overflow_east_raises() -> None:
    """W9-c: footprint extending beyond envelope width rejects."""
    s = Staircase(
        origin_x_m=8.5,
        origin_y_m=0.0,
        width_m=1.0,             # 8.5 + 1.0 = 9.5 > envelope 9.0
        landing_depth_m=1.0,
        anchor=None,
    )
    with pytest.raises(ValueError, match="W9-c: staircase east edge"):
        _envelope_grid(width_m=9.0, depth_m=12.0, staircase=s)


def test_grid_w9c_overflow_north_raises() -> None:
    """W9-c: footprint extending beyond envelope depth rejects."""
    s = Staircase(
        origin_x_m=0.0, origin_y_m=11.5,
        width_m=1.0,
        landing_depth_m=1.0,    # 11.5 + 1.0 = 12.5 > envelope 12.0
        anchor=None,
    )
    with pytest.raises(ValueError, match="W9-c: staircase north edge"):
        _envelope_grid(width_m=9.0, depth_m=12.0, staircase=s)


def test_grid_w9d_anchor_east_misaligned_raises() -> None:
    """W9-d: anchor=EAST requires footprint flush with east edge."""
    s = Staircase(
        origin_x_m=3.0,         # far_x = 3 + 1 = 4, envelope width 9 -> not flush
        origin_y_m=0.0,
        width_m=1.0,
        landing_depth_m=1.0,
        anchor=WallAxis.EAST,
    )
    with pytest.raises(ValueError, match="W9-d: anchor=EAST"):
        _envelope_grid(width_m=9.0, depth_m=12.0, staircase=s)


def test_grid_w9d_anchor_west_misaligned_raises() -> None:
    """W9-d: anchor=WEST requires origin_x_m=0."""
    s = Staircase(
        origin_x_m=2.0,         # not flush against west
        origin_y_m=0.0,
        width_m=1.0,
        landing_depth_m=1.0,
        anchor=WallAxis.WEST,
    )
    with pytest.raises(ValueError, match="W9-d: anchor=WEST"):
        _envelope_grid(staircase=s)


def test_grid_w9d_anchor_east_aligned_ok() -> None:
    """W9-d: anchor=EAST with footprint flush against east edge passes."""
    s = Staircase(
        origin_x_m=8.0,         # 8 + 1 = 9 = envelope width
        origin_y_m=0.0,
        width_m=1.0,
        landing_depth_m=1.0,
        anchor=WallAxis.EAST,
    )
    g = _envelope_grid(width_m=9.0, depth_m=12.0, staircase=s)
    assert g.staircase.anchor is WallAxis.EAST


def test_grid_w9d_anchor_north_aligned_ok() -> None:
    """W9-d: anchor=NORTH with footprint flush against north edge passes."""
    s = Staircase(
        origin_x_m=0.0,
        origin_y_m=11.0,        # 11 + 1 = 12 = envelope depth
        width_m=1.0,
        landing_depth_m=1.0,
        anchor=WallAxis.NORTH,
    )
    g = _envelope_grid(width_m=9.0, depth_m=12.0, staircase=s)
    assert g.staircase.anchor is WallAxis.NORTH


# =============================================================================
# validate_staircase_clearance() predicate (the C11a Tier A entry point)
# =============================================================================


def test_predicate_valid_returns_true_none() -> None:
    """A clean candidate Staircase + Grid returns (True, None)."""
    g = _envelope_grid(width_m=9.0, depth_m=12.0)
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=1.0, landing_depth_m=1.0,
        anchor=WallAxis.SOUTH,
    )
    ok, reason = validate_staircase_clearance(g, s)
    assert ok is True
    assert reason is None


def test_predicate_too_narrow_returns_false() -> None:
    """Width < NBC minimum returns (False, reason mentioning W9-a)."""
    g = _envelope_grid(width_m=9.0, depth_m=12.0)
    # We can't build the Staircase via __post_init__ if values are negative,
    # but we can with width = MIN-epsilon as a distinct test.
    # MIN_STAIRCASE_WIDTH_M = 0.9, use 0.85 (positive but below NBC).
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=0.85, landing_depth_m=1.0,
    )
    ok, reason = validate_staircase_clearance(g, s)
    assert ok is False
    assert reason is not None
    assert "W9-a" in reason


def test_predicate_overflow_returns_false() -> None:
    """Footprint extending past envelope returns (False, reason mentioning W9-c)."""
    g = _envelope_grid(width_m=9.0, depth_m=12.0)
    s = Staircase(
        origin_x_m=9.0, origin_y_m=0.0,
        width_m=1.0, landing_depth_m=1.0,
        anchor=None,
    )
    ok, reason = validate_staircase_clearance(g, s)
    assert ok is False
    assert reason is not None
    assert "W9-c" in reason


def test_predicate_pure_does_not_mutate_grid() -> None:
    """Predicate is pure — does not mutate input Grid."""
    g = _envelope_grid(width_m=9.0, depth_m=12.0)
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=1.0, landing_depth_m=1.0,
    )
    initial_staircase = g.staircase
    validate_staircase_clearance(g, s)
    # Grid is frozen so attribute mutation would error; this just confirms
    # the predicate doesn't try to assign.
    assert g.staircase is initial_staircase


# =============================================================================
# NBC-grounded constants sanity
# =============================================================================


def test_nbc_constants_at_documented_minimums() -> None:
    """NBC 2016 Part 4 Table 3.1.4-G — residential staircase minimums.
    These values await primary-source verification per B-150-equiv;
    this test pins the v1 documented values so an inadvertent edit
    surfaces in code review."""
    assert MIN_STAIRCASE_WIDTH_M == 0.9
    assert MIN_STAIRCASE_LANDING_DEPTH_M == 0.9


def test_nbc_constants_are_floats() -> None:
    """Constants are floats (not ints) — consistency with WallSegment
    field convention."""
    assert isinstance(MIN_STAIRCASE_WIDTH_M, float)
    assert isinstance(MIN_STAIRCASE_LANDING_DEPTH_M, float)


# =============================================================================
# B-NEW-K v0.2 (S38 K-4 patch) — landing-depth-scales-with-width tests
# =============================================================================
#
# NBC 2016 Part 4: landing depth must be at least the staircase width
# (not just a fixed 0.9m floor). v0.1 used a fixed-floor rule which
# under-specified W9 for stairs wider than 0.9m. v0.2 corrects to
# `landing_depth_m >= max(width_m, MIN_STAIRCASE_LANDING_DEPTH_M)`.


def test_w9b_v0_2_wider_stair_requires_proportional_landing() -> None:
    """K-4 patch: a 1.2m wide stair with a 0.9m landing must FAIL W9-b
    under v0.2 (would have passed under v0.1's fixed-floor rule)."""
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=1.2,
        landing_depth_m=0.9,   # = MIN floor, but < width_m
    )
    with pytest.raises(ValueError, match="W9-b: landing depth"):
        _envelope_grid(width_m=10.0, depth_m=12.0, staircase=s)


def test_w9b_v0_2_wider_stair_with_matching_landing_passes() -> None:
    """K-4 patch: a 1.2m wide stair with a 1.2m landing passes."""
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=1.2, landing_depth_m=1.2,
    )
    g = _envelope_grid(width_m=10.0, depth_m=12.0, staircase=s)
    assert g.staircase is s


def test_w9b_v0_2_predicate_returns_actionable_reason() -> None:
    """K-4 patch: failure reason cites the 'required' value (max of
    width and NBC floor) so callers can correct."""
    g = _envelope_grid(width_m=10.0, depth_m=12.0)
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=1.5, landing_depth_m=1.0,
    )
    ok, reason = validate_staircase_clearance(g, s)
    assert ok is False
    assert reason is not None
    assert "W9-b" in reason
    # Reason includes the required value (max of width and floor)
    assert "1.5" in reason


def test_w9b_v0_2_minimum_width_landing_floor_still_applies() -> None:
    """K-4 patch: for the minimum 0.9m wide stair, the NBC floor still
    applies (max(0.9, 0.9) = 0.9) — backwards-compat with v0.1's case."""
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=0.9, landing_depth_m=0.9,
    )
    g = _envelope_grid(width_m=10.0, depth_m=12.0, staircase=s)
    assert g.staircase is s


def test_w9b_v0_2_landing_below_floor_for_narrow_stair() -> None:
    """K-4 patch: even if width were below floor (which Staircase
    rejects via width_m=0.9 minimum check), the floor still applies.
    This test uses width=0.9 + landing=0.85 to exercise the floor
    branch where width < floor would otherwise let it slip."""
    # width = 0.9 (= floor), landing = 0.85 (< floor)
    s = Staircase(
        origin_x_m=0.0, origin_y_m=0.0,
        width_m=0.9, landing_depth_m=0.85,
    )
    with pytest.raises(ValueError, match="W9-b: landing depth"):
        _envelope_grid(width_m=10.0, depth_m=12.0, staircase=s)
