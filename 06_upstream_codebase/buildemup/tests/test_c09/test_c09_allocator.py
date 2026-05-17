"""C9 allocator tests.

Per C9 SPEC v0.7 LOCKED § 4.5 (Surplus allocation) + § 14.2.
"""
from __future__ import annotations

import pytest

from buildemup.components.c09 import AllocationStrategy
from buildemup.components.c09.allocator import (
    AllocationResult,
    distribute_surplus,
)
from buildemup.tests._c9_fixtures import make_room, make_regulatory


# Helper: build N rooms with controllable sizes
def _bedroom(idx: int, *, is_master: bool, prio: int,
             liv_min: float = 9.5, target: float = 10.2, max_m2: float = 16.32):
    return make_room(
        room_id=f"BEDROOM_{idx}",
        is_master=is_master,
        priority=prio,
        liveability_min_area_m2=liv_min,
        liveability_min_width_m=3.0,
        target_m2=target,
        max_m2=max_m2,
        regulatory=make_regulatory(area_m2=9.5, width_m=2.4),
    )


# ---------------------------------------------------------------------------
# Empty / trivial cases
# ---------------------------------------------------------------------------


def test_empty_rooms_all_unassigned():
    result = distribute_surplus(
        rooms=(),
        envelope_minus_corridor_m2=100.0,
        strategy=AllocationStrategy.PRIORITY_GREEDY,
    )
    assert result.unassigned_area_m2 == 100.0
    assert result.surplus_distributed_m2 == 0.0


def test_zero_surplus_all_at_min():
    """envelope == Σ liveability_min: nothing to distribute."""
    rooms = (
        _bedroom(1, is_master=True, prio=1, liv_min=10.0),
        _bedroom(2, is_master=False, prio=2, liv_min=10.0),
    )
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=20.0,
        strategy=AllocationStrategy.PRIORITY_GREEDY,
    )
    assert result.surplus_distributed_m2 == pytest.approx(0.0)
    assert result.unassigned_area_m2 == pytest.approx(0.0)
    assert set(result.rooms_at_min) == {"BEDROOM_1", "BEDROOM_2"}


def test_negative_surplus_raises():
    """Defensive: orchestrator should have raised RoomSizingInfeasibleError first."""
    rooms = (_bedroom(1, is_master=True, prio=1, liv_min=10.0),)
    with pytest.raises(ValueError, match="surplus"):
        distribute_surplus(
            rooms=rooms,
            envelope_minus_corridor_m2=5.0,
            strategy=AllocationStrategy.PRIORITY_GREEDY,
        )


# ---------------------------------------------------------------------------
# PRIORITY_GREEDY
# ---------------------------------------------------------------------------


def test_priority_greedy_high_priority_grows_first():
    """Surplus = 5; both rooms want 0.7 to reach target. P1 grows first."""
    rooms = (
        _bedroom(1, is_master=True, prio=1, liv_min=9.5, target=14.9, max_m2=23.84),
        _bedroom(2, is_master=False, prio=2, liv_min=9.5, target=10.2, max_m2=16.32),
    )
    # envelope = 25 → surplus = 25 - 19 = 6
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=25.0,
        strategy=AllocationStrategy.PRIORITY_GREEDY,
    )
    # Stage 1: BEDROOM_1 grows 9.5 → 14.9 (5.4 used). BEDROOM_2 grows 9.5 → 10.1 (0.6 left).
    # No leftover for stage 2.
    assert result.surplus_distributed_m2 == pytest.approx(6.0)
    assert result.unassigned_area_m2 == pytest.approx(0.0)
    assert result.assigned_per_room["BEDROOM_1"] == pytest.approx(14.9)
    assert result.assigned_per_room["BEDROOM_2"] == pytest.approx(10.1)


def test_priority_greedy_clamps_at_max():
    """Surplus large enough to push high-priority room to max."""
    rooms = (
        _bedroom(1, is_master=True, prio=1, liv_min=9.5, target=14.9, max_m2=23.84),
    )
    # envelope = 100 → surplus = 90.5
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=100.0,
        strategy=AllocationStrategy.PRIORITY_GREEDY,
    )
    # BR grows to max 23.84 (14.34 used); leftover = 76.16
    assert result.assigned_per_room["BEDROOM_1"] == pytest.approx(23.84)
    assert "BEDROOM_1" in result.rooms_clamped_at_max
    assert result.unassigned_area_m2 == pytest.approx(76.16)


def test_priority_greedy_stage_2_after_targets_met():
    """Surplus exceeds total-target; stage 2 grows toward max in priority order."""
    rooms = (
        _bedroom(1, is_master=True, prio=1, liv_min=9.5, target=14.9, max_m2=20.0),
        _bedroom(2, is_master=False, prio=2, liv_min=9.5, target=10.2, max_m2=15.0),
    )
    # surplus = 30 - 19 = 11
    # Stage 1: P1 takes 5.4 to reach target (5.6 left). P2 takes 0.7 (4.9 left).
    # Stage 2: P1 grows from 14.9 by 4.9 = 19.8 (max=20.0 not reached, no leftover).
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=30.0,
        strategy=AllocationStrategy.PRIORITY_GREEDY,
    )
    assert result.assigned_per_room["BEDROOM_1"] == pytest.approx(19.8)
    assert result.assigned_per_room["BEDROOM_2"] == pytest.approx(10.2)
    assert "BEDROOM_1" not in result.rooms_clamped_at_max
    assert result.unassigned_area_m2 == pytest.approx(0.0)


def test_priority_override_reorders():
    """Override flips priority — BEDROOM_2 (typical) grows before BEDROOM_1 (master)."""
    rooms = (
        _bedroom(1, is_master=True, prio=1, liv_min=9.5, target=14.9, max_m2=23.84),
        _bedroom(2, is_master=False, prio=2, liv_min=9.5, target=10.2, max_m2=16.32),
    )
    # surplus = 1.0; with override, BEDROOM_2 takes the 1.0 first
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=20.0,
        strategy=AllocationStrategy.PRIORITY_GREEDY,
        priority_override=("BEDROOM_2", "BEDROOM_1"),
    )
    assert result.assigned_per_room["BEDROOM_2"] == pytest.approx(10.2)  # took target
    assert result.assigned_per_room["BEDROOM_1"] == pytest.approx(9.8)   # leftover 0.3


# ---------------------------------------------------------------------------
# PROPORTIONAL
# ---------------------------------------------------------------------------


def test_proportional_equal_weights():
    """Two rooms with equal (target - liveability_min); surplus splits 50/50."""
    rooms = (
        _bedroom(1, is_master=False, prio=1, liv_min=9.5, target=10.5, max_m2=20.0),
        _bedroom(2, is_master=False, prio=2, liv_min=9.5, target=10.5, max_m2=20.0),
    )
    # surplus = 21 - 19 = 2.0; weight equal → each gets 1.0
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=21.0,
        strategy=AllocationStrategy.PROPORTIONAL,
    )
    assert result.assigned_per_room["BEDROOM_1"] == pytest.approx(10.5)
    assert result.assigned_per_room["BEDROOM_2"] == pytest.approx(10.5)


def test_proportional_clamps_redistributes():
    """Proportional with one room hitting cap; remainder redistributes."""
    rooms = (
        _bedroom(1, is_master=True, prio=1, liv_min=9.5, target=10.0, max_m2=10.0),  # tight cap
        _bedroom(2, is_master=False, prio=2, liv_min=9.5, target=20.0, max_m2=30.0),
    )
    # P1 max-cap = 10 - 9.5 = 0.5
    # P2 max-cap = 30 - 9.5 = 20.5
    # surplus = 50 - 19 = 31
    # weights P1=0.5, P2=10.5 (total 11)
    # P1 share = 31 * 0.5/11 = 1.41, capped at 0.5 → clip
    # remaining 30.5; P2 share = full = 30.5, capped at 20.5 → clip
    # leftover = 31 - 0.5 - 20.5 = 10.0
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=50.0,
        strategy=AllocationStrategy.PROPORTIONAL,
    )
    assert result.assigned_per_room["BEDROOM_1"] == pytest.approx(10.0)  # clamped at max
    assert result.assigned_per_room["BEDROOM_2"] == pytest.approx(30.0)  # clamped at max
    assert "BEDROOM_1" in result.rooms_clamped_at_max
    assert "BEDROOM_2" in result.rooms_clamped_at_max
    assert result.unassigned_area_m2 == pytest.approx(10.0)


def test_proportional_no_growth_room_skipped():
    """A room whose target == liveability_min has zero weight → no surplus to it."""
    rooms = (
        _bedroom(1, is_master=True, prio=1, liv_min=10.0, target=10.0, max_m2=15.0),  # zero weight
        _bedroom(2, is_master=False, prio=2, liv_min=9.5, target=12.0, max_m2=20.0),
    )
    # surplus = 30 - 19.5 = 10.5; weight P1=0, P2=2.5 → P2 takes 10.5 / 2.5 share, capped at 10.5
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=30.0,
        strategy=AllocationStrategy.PROPORTIONAL,
    )
    assert result.assigned_per_room["BEDROOM_1"] == pytest.approx(10.0)  # stays at min
    # P2 grows by 10.5 → 20.0 (clamped at max)
    assert result.assigned_per_room["BEDROOM_2"] == pytest.approx(20.0)
    assert "BEDROOM_1" in result.rooms_at_min


def test_unknown_strategy_raises():
    rooms = (_bedroom(1, is_master=True, prio=1),)
    with pytest.raises(ValueError, match="unknown strategy"):
        distribute_surplus(
            rooms=rooms,
            envelope_minus_corridor_m2=20.0,
            strategy="invalid",  # type: ignore[arg-type]
        )


def test_allocation_result_metadata():
    rooms = (_bedroom(1, is_master=True, prio=1, liv_min=9.5, target=14.9, max_m2=23.84),)
    result = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=12.0,
        strategy=AllocationStrategy.PRIORITY_GREEDY,
    )
    assert isinstance(result, AllocationResult)
    assert result.surplus_for_distribution_m2 == pytest.approx(2.5)
    assert result.surplus_distributed_m2 + result.unassigned_area_m2 == pytest.approx(2.5)
