"""
C11a Sub-session 5 — B-NEW-T1: M6 wet-rotate vertical slice tests.

Tests the post-process rotation against real C10 data structures
(WetZonePlan, RiserGroup, RiserAnchor) — proves the architecture
end-to-end without needing the full C5→C10 ancestry chain.

Coverage:
  - Rotation map: NORTH→EAST→SOUTH→WEST cycle is correct.
  - Room assignment rotates per acceptable_wall_sets.
  - M6NotViableError when no acceptable wall in rotated axis.
  - riser_groups rebuilt with rotated wall_ids.
  - Inv 14 preserved (every wall_id in groups appears in canonical walls).
  - DeltaKey diff: PLUMB_WET_WALL_ASSIGNMENT + PLUMB_RISER_GROUPS.
  - RealUpstreamRegenerator.regenerate(M6) dispatches to the slice.
"""
from __future__ import annotations

import pytest

from buildemup.components.c07.grid_generator import Grid, Staircase
from buildemup.components.c07.wall_segment import WallAxis, WallSegment, WallTag
from buildemup.components.c10.schema import (
    RiserAnchor,
    RiserGroup,
    WetZonePlan,
)
from buildemup.components.c11a import (
    DeltaKey,
    MutationOperator,
    RealUpstreamRegenerator,
    TierBInputMutation,
)
from buildemup.components.c11a.m6_wet_rotate_real import (
    M6NotViableError,
    _ROTATE_CW_90,
    _pick_rotated_wall,
    rotate_wet_wall_assignment,
)
from buildemup.components.c11a.upstream_adapter import _diff_m6_wet_rotate


# =============================================================================
# Synthetic but real-shape grid fixture
# =============================================================================


def _build_test_grid(width_m: float = 10.0, depth_m: float = 12.0) -> Grid:
    """Build a Grid with 4 perimeter walls (one per axis).

    The Grid class uses ``wall_segments_canonical()`` which the M6
    rotation reads — so we build a Grid that exposes 4 named walls,
    one per axis.
    """
    return Grid(
        columns=[],
        bay_x_m=3.0, bay_y_m=3.0,
        columns_x_count=0, columns_y_count=0,
        envelope_width_m=width_m, envelope_depth_m=depth_m,
        staircase=Staircase(
            origin_x_m=0.5, origin_y_m=0.5,
            width_m=1.0, landing_depth_m=1.2,
        ),
    )


def _build_test_walls(width_m: float = 10.0, depth_m: float = 12.0) -> tuple[WallSegment, ...]:
    """Construct 4 perimeter walls — one per WallAxis. Used to override
    Grid.wall_segments_canonical() in tests via monkeypatch.
    """
    return (
        WallSegment(
            wall_id="W_S",
            axis=WallAxis.SOUTH,
            start_x_m=0.0, start_y_m=0.0,
            end_x_m=width_m, end_y_m=0.0,
            length_m=width_m,
            tags=frozenset({WallTag.EXTERNAL}),
        ),
        WallSegment(
            wall_id="W_E",
            axis=WallAxis.EAST,
            start_x_m=width_m, start_y_m=0.0,
            end_x_m=width_m, end_y_m=depth_m,
            length_m=depth_m,
            tags=frozenset({WallTag.EXTERNAL}),
        ),
        WallSegment(
            wall_id="W_N",
            axis=WallAxis.NORTH,
            start_x_m=0.0, start_y_m=depth_m,
            end_x_m=width_m, end_y_m=depth_m,
            length_m=width_m,
            tags=frozenset({WallTag.EXTERNAL}),
        ),
        WallSegment(
            wall_id="W_W",
            axis=WallAxis.WEST,
            start_x_m=0.0, start_y_m=0.0,
            end_x_m=0.0, end_y_m=depth_m,
            length_m=depth_m,
            tags=frozenset({WallTag.EXTERNAL}),
        ),
    )


def _grid_with_canonical_walls(monkeypatch_obj) -> Grid:
    """Create a grid + override its wall_segments_canonical() to return
    our 4 test walls. Real Grid auto-generates walls but we want
    deterministic ones."""
    grid = _build_test_grid()
    walls = _build_test_walls()
    monkeypatch_obj.setattr(
        type(grid), "wall_segments_canonical",
        lambda self: walls, raising=False,
    )
    return grid


# =============================================================================
# Rotation map
# =============================================================================


def test_rotation_map_is_90_clockwise() -> None:
    """N→E→S→W→N cycle (project coord system 90° clockwise)."""
    assert _ROTATE_CW_90[WallAxis.NORTH] == WallAxis.EAST
    assert _ROTATE_CW_90[WallAxis.EAST]  == WallAxis.SOUTH
    assert _ROTATE_CW_90[WallAxis.SOUTH] == WallAxis.WEST
    assert _ROTATE_CW_90[WallAxis.WEST]  == WallAxis.NORTH


def test_rotation_map_total_over_walls() -> None:
    """Every WallAxis has a rotation entry (total function)."""
    for axis in WallAxis:
        assert axis in _ROTATE_CW_90


# =============================================================================
# Wall picking
# =============================================================================


def test_pick_rotated_wall_finds_compatible() -> None:
    """Room assigned to W_N (NORTH) rotates → look for EAST wall in
    acceptable_wall_ids. Returns W_E."""
    walls = _build_test_walls()
    walls_by_id = {w.wall_id: w for w in walls}
    axis_to_walls = {a: tuple(w for w in walls if w.axis == a) for a in WallAxis}

    new_wid = _pick_rotated_wall(
        current_wall_id="W_N",
        walls_by_id=walls_by_id,
        axis_to_walls=axis_to_walls,
        acceptable_wall_ids=("W_S", "W_E", "W_W"),  # E is acceptable
    )
    assert new_wid == "W_E"


def test_pick_rotated_wall_returns_none_when_not_acceptable() -> None:
    walls = _build_test_walls()
    walls_by_id = {w.wall_id: w for w in walls}
    axis_to_walls = {a: tuple(w for w in walls if w.axis == a) for a in WallAxis}

    # Room currently on W_N → rotated axis is EAST. But acceptable
    # excludes W_E.
    new_wid = _pick_rotated_wall(
        current_wall_id="W_N",
        walls_by_id=walls_by_id,
        axis_to_walls=axis_to_walls,
        acceptable_wall_ids=("W_S", "W_W"),  # no EAST wall acceptable
    )
    assert new_wid is None


def test_pick_rotated_wall_unknown_current_wall_returns_none() -> None:
    walls = _build_test_walls()
    walls_by_id = {w.wall_id: w for w in walls}
    axis_to_walls = {a: tuple(w for w in walls if w.axis == a) for a in WallAxis}

    new_wid = _pick_rotated_wall(
        current_wall_id="W_DOES_NOT_EXIST",
        walls_by_id=walls_by_id,
        axis_to_walls=axis_to_walls,
        acceptable_wall_ids=("W_E",),
    )
    assert new_wid is None


# =============================================================================
# Plan rotation — happy path
# =============================================================================


def _build_test_plan() -> WetZonePlan:
    """Construct a minimal-valid WetZonePlan with 2 rooms on W_N."""
    return WetZonePlan(
        wet_wall_assignment={"kitchen": "W_N", "bathroom_1": "W_N"},
        riser_groups=(
            RiserGroup(
                group_id="rg_0",
                anchors=(RiserAnchor(
                    wall_id="W_N",
                    anchor_position_m=5.0,
                    riser_anchor_xy=(5.0, 12.0),
                    column_id=None,
                    snap_distance_m=None,
                ),),
                wet_room_ids=("bathroom_1", "kitchen"),
            ),
        ),
        kitchen_riser_group_id="rg_0",
        fixture_types_per_room={"kitchen": (), "bathroom_1": ()},
        trap_arm_distances={},
        total_wet_run_length_m=0.0,
        symbolic_bend_estimate=0,
        bend_estimation_mode="symbolic_v1",
        riser_count=1,
        non_wet_room_buffer_zones=(),
        acceptable_wall_sets={
            "kitchen": ("W_N", "W_E"),       # E is acceptable for rotation
            "bathroom_1": ("W_N", "W_E"),
        },
    )


def test_rotate_assignment_north_to_east(monkeypatch) -> None:
    """Rooms on W_N (NORTH) rotate → W_E (EAST)."""
    grid = _grid_with_canonical_walls(monkeypatch)
    plan = _build_test_plan()
    new_plan = rotate_wet_wall_assignment(plan, grid)

    assert new_plan.wet_wall_assignment == {
        "kitchen": "W_E",
        "bathroom_1": "W_E",
    }


def test_rotate_assignment_preserves_inv_14_walls_used(monkeypatch) -> None:
    """Inv 14: every wall_id in riser_groups.anchor.wall_id appears
    in plan.wall_segments_used (the property)."""
    grid = _grid_with_canonical_walls(monkeypatch)
    plan = _build_test_plan()
    new_plan = rotate_wet_wall_assignment(plan, grid)

    walls_in_groups = {
        rg.anchors[0].wall_id for rg in new_plan.riser_groups
    }
    walls_used = set(new_plan.wall_segments_used)
    assert walls_in_groups == walls_used


def test_rotate_assignment_riser_groups_rebuilt(monkeypatch) -> None:
    """Riser groups rebuilt with new wall_ids; group_ids prefixed
    'rg_rotated_'."""
    grid = _grid_with_canonical_walls(monkeypatch)
    plan = _build_test_plan()
    new_plan = rotate_wet_wall_assignment(plan, grid)

    assert len(new_plan.riser_groups) == 1
    assert new_plan.riser_groups[0].anchors[0].wall_id == "W_E"
    assert new_plan.riser_groups[0].group_id == "rg_rotated_W_E"


def test_rotate_assignment_clusters_by_rotated_wall(monkeypatch) -> None:
    """Two rooms assigned to W_N share a cluster; after rotation, both
    map to W_E and stay clustered."""
    grid = _grid_with_canonical_walls(monkeypatch)
    plan = _build_test_plan()
    new_plan = rotate_wet_wall_assignment(plan, grid)

    rg = new_plan.riser_groups[0]
    assert set(rg.wet_room_ids) == {"kitchen", "bathroom_1"}


# =============================================================================
# Plan rotation — invalid path
# =============================================================================


def test_rotate_raises_when_no_acceptable_in_rotated_axis(monkeypatch) -> None:
    """Room with no E-axis wall in acceptable_wall_sets → M6NotViable."""
    grid = _grid_with_canonical_walls(monkeypatch)
    plan = WetZonePlan(
        wet_wall_assignment={"kitchen": "W_N"},
        riser_groups=(
            RiserGroup(
                group_id="rg_0",
                anchors=(RiserAnchor(
                    wall_id="W_N", anchor_position_m=5.0,
                    riser_anchor_xy=(5.0, 12.0),
                    column_id=None, snap_distance_m=None,
                ),),
                wet_room_ids=("kitchen",),
            ),
        ),
        kitchen_riser_group_id="rg_0",
        fixture_types_per_room={"kitchen": ()},
        trap_arm_distances={},
        total_wet_run_length_m=0.0,
        symbolic_bend_estimate=0,
        bend_estimation_mode="symbolic_v1",
        riser_count=1,
        non_wet_room_buffer_zones=(),
        # acceptable_wall_sets EXCLUDES E (the rotated axis)
        acceptable_wall_sets={"kitchen": ("W_N", "W_W")},
    )

    with pytest.raises(M6NotViableError, match="acceptable wall in the rotated axis"):
        rotate_wet_wall_assignment(plan, grid)


def test_m6_not_viable_severity_per_candidate() -> None:
    """M6NotViableError carries severity_tier='per_candidate' so the
    pipeline catches it as a per-candidate failure (batch continues)."""
    assert M6NotViableError.severity_tier == "per_candidate"


# =============================================================================
# DeltaKey diff
# =============================================================================


def test_diff_m6_returns_assignment_and_riser_keys(monkeypatch) -> None:
    """After rotation: wet_wall_assignment + riser_groups both differ
    → diff returns both keys."""
    grid = _grid_with_canonical_walls(monkeypatch)
    plan = _build_test_plan()
    new_plan = rotate_wet_wall_assignment(plan, grid)

    # Wrap in candidate-shaped objects (just need .wet_zone_plan).
    class _Holder:
        def __init__(self, plan): self.wet_zone_plan = plan

    delta = _diff_m6_wet_rotate(_Holder(plan), _Holder(new_plan))
    assert DeltaKey.PLUMB_WET_WALL_ASSIGNMENT in delta
    assert DeltaKey.PLUMB_RISER_GROUPS in delta


def test_diff_m6_returns_sorted(monkeypatch) -> None:
    """DeltaKey output is sorted by .value for replay determinism."""
    grid = _grid_with_canonical_walls(monkeypatch)
    plan = _build_test_plan()
    new_plan = rotate_wet_wall_assignment(plan, grid)

    class _Holder:
        def __init__(self, plan): self.wet_zone_plan = plan

    delta = _diff_m6_wet_rotate(_Holder(plan), _Holder(new_plan))
    values = [k.value for k in delta]
    assert values == sorted(values)


def test_diff_m6_empty_when_plans_identical() -> None:
    """No diff when source and regenerated have identical plans."""
    plan = _build_test_plan()
    class _Holder:
        def __init__(self, plan): self.wet_zone_plan = plan
    delta = _diff_m6_wet_rotate(_Holder(plan), _Holder(plan))
    assert delta == ()


# =============================================================================
# RealUpstreamRegenerator dispatch
# =============================================================================


def test_real_regenerator_m6_rejects_synthetic_source() -> None:
    """RealUpstreamRegenerator.regenerate(M6) requires a real
    WetZonePlannedCandidate — synthetic dict-shaped source raises
    NotImplementedError."""
    regen = RealUpstreamRegenerator()
    mut = TierBInputMutation(operator=MutationOperator.M6_WET_ROTATE)
    with pytest.raises(NotImplementedError, match="real WetZonePlannedCandidate"):
        regen.regenerate("not-a-real-candidate", mut, MutationOperator.M6_WET_ROTATE)


def test_real_regenerator_m7_still_unimplemented() -> None:
    """B-NEW-T2 not landed yet — M7a/M7b still raise NotImplementedError."""
    regen = RealUpstreamRegenerator()
    mut = TierBInputMutation(operator=MutationOperator.M7A_GRID_3_3)
    with pytest.raises(NotImplementedError, match="B-NEW-T2"):
        regen.regenerate("anything", mut, MutationOperator.M7A_GRID_3_3)


def test_real_regenerator_m8_still_unimplemented() -> None:
    """B-NEW-T3 not landed — M8 raises NotImplementedError."""
    regen = RealUpstreamRegenerator()
    mut = TierBInputMutation(operator=MutationOperator.M8_VERT_REARR)
    with pytest.raises(NotImplementedError, match="B-NEW-T3"):
        regen.regenerate("anything", mut, MutationOperator.M8_VERT_REARR)
