"""C9 validator tests.

Per C9 SPEC v0.7 LOCKED § 4.6 / § 4.7 / § 14.35-§ 14.42.

Covers:
  - check_total_area_feasibility (Inv 9 RAISE)
  - check_width_feasibility_inv_17a (Inv 17a RAISE + per-room verdict map)
  - _classify_width_feasibility (FEASIBLE / RISKY / IMPOSSIBLE)
  - _classify_grid_bay (SINGLE / DOUBLE / TRIPLE / OVERSIZED)
  - run_invariants (full Inv 1-18 sweep, WARN + STRICT escalations)
  - _derive_placement_risk_level (severity-weighted aggregation per § 14.36)
"""
from __future__ import annotations

import pytest

from buildemup.components.c09 import (
    BathroomSubtype,
    EnforcementMode,
    GridBayFeasibility,
    GridOversizeError,
    PackingInfeasibleError,
    PlacementRiskLevel,
    RoomCategory,
    RoomSizingInfeasibleError,
    WidthFeasibilityVerdict,
    WidthInfeasibleError,
    WidthRiskyError,
)
from buildemup.components.c09.validator import (
    _classify_grid_bay,
    _classify_width_feasibility,
    _derive_placement_risk_level,
    check_total_area_feasibility,
    check_width_feasibility_inv_17a,
    classify_grid_bay_feasibility,
    run_invariants,
)
from buildemup.tests._c9_fixtures import make_regulatory, make_room


# ---------------------------------------------------------------------------
# check_total_area_feasibility (Inv 9 RAISE)
# ---------------------------------------------------------------------------


def test_inv_9_pass_when_envelope_sufficient():
    rooms = (make_room(liveability_min_area_m2=13.0),)
    # No raise.
    check_total_area_feasibility(
        rooms=rooms, envelope_minus_corridor_m2=50.0, candidate_index=0,
    )


def test_inv_9_raise_when_total_min_exceeds_envelope():
    rooms = (
        make_room(room_id="BEDROOM_1", priority=1, liveability_min_area_m2=20.0,
                  target_m2=20.0, max_m2=32.0),
        make_room(room_id="BEDROOM_2", priority=2, liveability_min_area_m2=20.0,
                  is_master=False, target_m2=20.0, max_m2=32.0),
    )
    with pytest.raises(RoomSizingInfeasibleError, match="Inv 9"):
        check_total_area_feasibility(
            rooms=rooms, envelope_minus_corridor_m2=30.0, candidate_index=0,
        )


def test_inv_9_at_boundary_passes():
    """Σ liveability_min == envelope: no surplus but feasible."""
    rooms = (make_room(liveability_min_area_m2=13.0),)
    check_total_area_feasibility(
        rooms=rooms, envelope_minus_corridor_m2=13.0, candidate_index=0,
    )


def test_inv_9_error_carries_deficit_metadata():
    rooms = (make_room(liveability_min_area_m2=15.0, target_m2=15.0, max_m2=24.0),)
    try:
        check_total_area_feasibility(
            rooms=rooms, envelope_minus_corridor_m2=10.0, candidate_index=2,
        )
    except RoomSizingInfeasibleError as exc:
        assert exc.candidate_index == 2
        assert exc.deficit_m2 == pytest.approx(5.0)
        assert exc.envelope_minus_corridor_m2 == 10.0
    else:
        pytest.fail("expected RoomSizingInfeasibleError")


# ---------------------------------------------------------------------------
# _classify_width_feasibility
# ---------------------------------------------------------------------------


def test_classify_width_feasible_well_below_threshold():
    # threshold = (1 - 0.10) * 12.0 = 10.8; width 3.6 << 10.8 → FEASIBLE
    assert _classify_width_feasibility(3.6, 12.0, 0.10) == WidthFeasibilityVerdict.FEASIBLE


def test_classify_width_risky_just_above_threshold():
    # threshold = (1 - 0.10) * 4.0 = 3.6; width 3.7 > 3.6 but <= 4.0 → RISKY
    assert _classify_width_feasibility(3.7, 4.0, 0.10) == WidthFeasibilityVerdict.RISKY


def test_classify_width_impossible_exceeds_envelope():
    # width 5.0 > 4.0 → IMPOSSIBLE
    assert _classify_width_feasibility(5.0, 4.0, 0.10) == WidthFeasibilityVerdict.IMPOSSIBLE


def test_classify_width_at_envelope_exactly_is_risky():
    # width == envelope (== 4.0) → RISKY (just above 3.6 threshold)
    assert _classify_width_feasibility(4.0, 4.0, 0.10) == WidthFeasibilityVerdict.RISKY


def test_classify_width_with_thicker_walls_more_conservative():
    # Higher wall_thickness_ratio → tighter risky_threshold → RISKY for narrower rooms
    # threshold(0.20) = 3.2; width 3.5 between 3.2 and 4.0 → RISKY
    assert _classify_width_feasibility(3.5, 4.0, 0.20) == WidthFeasibilityVerdict.RISKY
    # threshold(0.05) = 3.8; width 3.5 < 3.8 → FEASIBLE
    assert _classify_width_feasibility(3.5, 4.0, 0.05) == WidthFeasibilityVerdict.FEASIBLE


# ---------------------------------------------------------------------------
# check_width_feasibility_inv_17a
# ---------------------------------------------------------------------------


def test_inv_17a_pass_with_feasible_widths():
    rooms = (make_room(liveability_min_width_m=3.3),)
    verdicts = check_width_feasibility_inv_17a(
        rooms=rooms, envelope_min_axis_m=12.0, wall_thickness_ratio=0.10,
        candidate_index=0,
    )
    assert verdicts["BEDROOM_1"] == WidthFeasibilityVerdict.FEASIBLE


def test_inv_17a_raise_when_room_impossible():
    rooms = (
        make_room(room_id="LIVING_1", category=RoomCategory.LIVING, priority=1,
                  is_master=False, liveability_min_width_m=15.0,
                  liveability_min_area_m2=16.7, target_m2=18.6, max_m2=46.5),
    )
    with pytest.raises(WidthInfeasibleError, match="LIVING_1"):
        check_width_feasibility_inv_17a(
            rooms=rooms, envelope_min_axis_m=12.0, wall_thickness_ratio=0.10,
            candidate_index=0,
        )


def test_inv_17a_risky_room_does_not_raise_returns_verdict():
    rooms = (
        make_room(liveability_min_width_m=3.7),  # RISKY against 4.0 axis
    )
    verdicts = check_width_feasibility_inv_17a(
        rooms=rooms, envelope_min_axis_m=4.0, wall_thickness_ratio=0.10,
        candidate_index=0,
    )
    assert verdicts["BEDROOM_1"] == WidthFeasibilityVerdict.RISKY


# ---------------------------------------------------------------------------
# _classify_grid_bay
# ---------------------------------------------------------------------------


def test_classify_grid_bay_single():
    # width 3.0 <= bay_max 3.0 → SINGLE_BAY
    assert _classify_grid_bay(3.0, 3.0) == GridBayFeasibility.SINGLE_BAY


def test_classify_grid_bay_double():
    # width 5.0; bay 3.0 → 5 <= 6 (=2*3) but > 3 → DOUBLE_BAY
    assert _classify_grid_bay(5.0, 3.0) == GridBayFeasibility.DOUBLE_BAY


def test_classify_grid_bay_triple():
    # width 8.0; bay 3.0 → 6 < 8 <= 9 → TRIPLE_BAY
    assert _classify_grid_bay(8.0, 3.0) == GridBayFeasibility.TRIPLE_BAY


def test_classify_grid_bay_oversized():
    # width 10.0; bay 3.0 → > 9 → OVERSIZED
    assert _classify_grid_bay(10.0, 3.0) == GridBayFeasibility.OVERSIZED


def test_classify_grid_bay_zero_bay_is_oversized():
    """Defensive: zero bay treats every room as OVERSIZED."""
    assert _classify_grid_bay(3.0, 0.0) == GridBayFeasibility.OVERSIZED


def test_classify_grid_bay_per_room_helper_returns_dict():
    rooms = (
        make_room(room_id="BR1", priority=1, liveability_min_width_m=3.0),
        make_room(room_id="BR2", priority=2, is_master=False,
                  liveability_min_width_m=8.0,
                  regulatory=make_regulatory(area_m2=9.5, width_m=2.4)),
    )
    verdicts = classify_grid_bay_feasibility(rooms=rooms, bay_max_m=3.0)
    assert verdicts["BR1"] == GridBayFeasibility.SINGLE_BAY
    assert verdicts["BR2"] == GridBayFeasibility.TRIPLE_BAY


# ---------------------------------------------------------------------------
# _derive_placement_risk_level (severity-weighted)
# ---------------------------------------------------------------------------


def test_prl_low_when_all_feasible():
    width_verdicts = {"r1": WidthFeasibilityVerdict.FEASIBLE}
    grid_verdicts = {"r1": GridBayFeasibility.SINGLE_BAY}
    level, score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning=False,
    )
    assert level == PlacementRiskLevel.LOW
    assert score == 0


def test_prl_medium_packing_only():
    width_verdicts = {"r1": WidthFeasibilityVerdict.FEASIBLE}
    grid_verdicts = {"r1": GridBayFeasibility.SINGLE_BAY}
    level, score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning=True,
    )
    assert level == PlacementRiskLevel.MEDIUM
    assert score == 1


def test_prl_medium_oversized_alone():
    """OVERSIZED grid alone (weight 2) = MEDIUM (score 2)."""
    width_verdicts = {"r1": WidthFeasibilityVerdict.FEASIBLE}
    grid_verdicts = {"r1": GridBayFeasibility.OVERSIZED}
    level, score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning=False,
    )
    assert level == PlacementRiskLevel.MEDIUM
    assert score == 2


def test_prl_high_oversized_plus_packing():
    """OVERSIZED (2) + packing (1) = score 3 → HIGH."""
    width_verdicts = {"r1": WidthFeasibilityVerdict.FEASIBLE}
    grid_verdicts = {"r1": GridBayFeasibility.OVERSIZED}
    level, score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning=True,
    )
    assert level == PlacementRiskLevel.HIGH
    assert score == 3


def test_prl_high_oversized_plus_risky():
    """OVERSIZED (2) + RISKY width (1) = score 3 → HIGH."""
    width_verdicts = {"r1": WidthFeasibilityVerdict.RISKY}
    grid_verdicts = {"r1": GridBayFeasibility.OVERSIZED}
    level, score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning=False,
    )
    assert level == PlacementRiskLevel.HIGH
    assert score == 3


def test_prl_medium_risky_alone():
    """RISKY width alone (1) = MEDIUM (score 1)."""
    width_verdicts = {"r1": WidthFeasibilityVerdict.RISKY}
    grid_verdicts = {"r1": GridBayFeasibility.SINGLE_BAY}
    level, score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning=False,
    )
    assert level == PlacementRiskLevel.MEDIUM
    assert score == 1


def test_prl_medium_triple_bay_alone():
    """TRIPLE_BAY alone (1) = MEDIUM."""
    width_verdicts = {"r1": WidthFeasibilityVerdict.FEASIBLE}
    grid_verdicts = {"r1": GridBayFeasibility.TRIPLE_BAY}
    level, score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning=False,
    )
    assert level == PlacementRiskLevel.MEDIUM
    assert score == 1


def test_prl_high_three_minor_yellows():
    """packing(1) + RISKY(1) + TRIPLE(1) = 3 → HIGH."""
    width_verdicts = {"r1": WidthFeasibilityVerdict.RISKY}
    grid_verdicts = {"r1": GridBayFeasibility.TRIPLE_BAY}
    level, score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning=True,
    )
    assert level == PlacementRiskLevel.HIGH
    assert score == 3


# ---------------------------------------------------------------------------
# run_invariants — full sweep, WARN + STRICT
# ---------------------------------------------------------------------------


def _make_three_rooms():
    """Build a minimal 3-bedroom set (1 master + 2 typical) for invariant tests."""
    return (
        make_room(room_id="BEDROOM_1", priority=1, is_master=True),
        make_room(room_id="BEDROOM_2", priority=2, is_master=False,
                  liveability_min_area_m2=9.5, liveability_min_width_m=3.0,
                  target_m2=10.2, max_m2=16.32,
                  regulatory=make_regulatory(area_m2=9.5, width_m=2.4)),
        make_room(room_id="BEDROOM_3", priority=3, is_master=False,
                  liveability_min_area_m2=9.5, liveability_min_width_m=3.0,
                  target_m2=10.2, max_m2=16.32,
                  regulatory=make_regulatory(area_m2=9.5, width_m=2.4)),
    )


def test_run_invariants_passes_simple_3br():
    rooms = _make_three_rooms()
    width_verdicts = {r.room_id: WidthFeasibilityVerdict.FEASIBLE for r in rooms}
    out = run_invariants(
        rooms=rooms, bedroom_count=3, bathroom_count=0,
        has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
        other_rooms_count=0,
        width_verdicts=width_verdicts,
        bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
        packing_efficiency=0.75,
        enforcement_mode=EnforcementMode.WARN,
        candidate_index=0,
    )
    assert out.placement_risk_level == PlacementRiskLevel.LOW
    assert out.heuristic_packing_check_warning is False


def test_inv_1_count_mismatch_raises():
    rooms = _make_three_rooms()
    width_verdicts = {r.room_id: WidthFeasibilityVerdict.FEASIBLE for r in rooms}
    with pytest.raises(ValueError, match="Inv 1"):
        run_invariants(
            rooms=rooms, bedroom_count=2, bathroom_count=0,  # claims 2 BRs but rooms has 3
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.WARN,
            candidate_index=0,
        )


def test_inv_12_priority_gap_raises():
    """Priorities 1,2,4 leave gap → Inv 12 fail."""
    rooms = (
        make_room(room_id="A", priority=1),
        make_room(room_id="B", priority=2, is_master=False,
                  liveability_min_area_m2=9.5, liveability_min_width_m=3.0,
                  target_m2=10.2, max_m2=16.32,
                  regulatory=make_regulatory(area_m2=9.5, width_m=2.4)),
        make_room(room_id="C", priority=4, is_master=False,
                  liveability_min_area_m2=9.5, liveability_min_width_m=3.0,
                  target_m2=10.2, max_m2=16.32,
                  regulatory=make_regulatory(area_m2=9.5, width_m=2.4)),
    )
    width_verdicts = {r.room_id: WidthFeasibilityVerdict.FEASIBLE for r in rooms}
    with pytest.raises(ValueError, match="Inv 12"):
        run_invariants(
            rooms=rooms, bedroom_count=3, bathroom_count=0,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.WARN,
            candidate_index=0,
        )


def test_inv_13_two_masters_raises():
    rooms = (
        make_room(room_id="A", priority=1, is_master=True),
        make_room(room_id="B", priority=2, is_master=True,
                  liveability_min_area_m2=13.0, liveability_min_width_m=3.3,
                  target_m2=14.9, max_m2=23.84),
    )
    width_verdicts = {r.room_id: WidthFeasibilityVerdict.FEASIBLE for r in rooms}
    with pytest.raises(ValueError, match="Inv 13"):
        run_invariants(
            rooms=rooms, bedroom_count=2, bathroom_count=0,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.WARN,
            candidate_index=0,
        )


def test_inv_14_two_master_bathrooms_raises():
    rooms = (
        make_room(room_id="BR", priority=1, is_master=True),
        make_room(room_id="BA1", category=RoomCategory.BATHROOM, priority=2, is_master=True,
                  bathroom_subtype=BathroomSubtype.COMBINED,
                  liveability_min_area_m2=4.0, liveability_min_width_m=1.5,
                  target_m2=4.2, max_m2=6.72,
                  regulatory=make_regulatory(area_m2=2.8, width_m=1.2, height_m=2.1)),
        make_room(room_id="BA2", category=RoomCategory.BATHROOM, priority=3, is_master=True,
                  bathroom_subtype=BathroomSubtype.COMBINED,
                  liveability_min_area_m2=4.0, liveability_min_width_m=1.5,
                  target_m2=4.2, max_m2=6.72,
                  regulatory=make_regulatory(area_m2=2.8, width_m=1.2, height_m=2.1)),
    )
    width_verdicts = {r.room_id: WidthFeasibilityVerdict.FEASIBLE for r in rooms}
    with pytest.raises(ValueError, match="Inv 14"):
        run_invariants(
            rooms=rooms, bedroom_count=1, bathroom_count=2,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.WARN,
            candidate_index=0,
        )


def test_inv_10_packing_warning_no_strict():
    """Packing warn under WARN mode: surfaces in outcome but does NOT raise."""
    rooms = _make_three_rooms()  # Σ liv_min = 13 + 9.5 + 9.5 = 32
    width_verdicts = {r.room_id: WidthFeasibilityVerdict.FEASIBLE for r in rooms}
    # envelope * 0.75 = 30; total liv min = 32 → > 30 → packing warn
    out = run_invariants(
        rooms=rooms, bedroom_count=3, bathroom_count=0,
        has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
        other_rooms_count=0, width_verdicts=width_verdicts,
        bay_max_m=3.0, envelope_minus_corridor_m2=40.0,
        packing_efficiency=0.75, enforcement_mode=EnforcementMode.WARN,
        candidate_index=0,
    )
    assert out.heuristic_packing_check_warning is True
    assert out.placement_risk_level == PlacementRiskLevel.MEDIUM


def test_inv_10_strict_raises_packing_infeasible():
    """STRICT + packing warn → PackingInfeasibleError."""
    rooms = _make_three_rooms()
    width_verdicts = {r.room_id: WidthFeasibilityVerdict.FEASIBLE for r in rooms}
    with pytest.raises(PackingInfeasibleError, match="Inv 10"):
        run_invariants(
            rooms=rooms, bedroom_count=3, bathroom_count=0,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=40.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=0,
        )


def test_inv_17b_strict_raises_width_risky():
    """RISKY width + STRICT → WidthRiskyError."""
    rooms = _make_three_rooms()
    width_verdicts = {
        "BEDROOM_1": WidthFeasibilityVerdict.RISKY,
        "BEDROOM_2": WidthFeasibilityVerdict.FEASIBLE,
        "BEDROOM_3": WidthFeasibilityVerdict.FEASIBLE,
    }
    with pytest.raises(WidthRiskyError, match="Inv 17b"):
        run_invariants(
            rooms=rooms, bedroom_count=3, bathroom_count=0,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=0,
        )


def test_inv_18_strict_raises_grid_oversize():
    """OVERSIZED grid + STRICT → GridOversizeError."""
    rooms = (
        make_room(room_id="LIVING_1", category=RoomCategory.LIVING, priority=1,
                  is_master=False, liveability_min_area_m2=16.7,
                  liveability_min_width_m=10.0,  # too wide for 3.0m bays (>9.0)
                  target_m2=18.6, max_m2=46.5,
                  regulatory=make_regulatory(area_m2=9.5, width_m=3.6)),
    )
    width_verdicts = {"LIVING_1": WidthFeasibilityVerdict.FEASIBLE}
    with pytest.raises(GridOversizeError, match="Inv 18"):
        run_invariants(
            rooms=rooms, bedroom_count=0, bathroom_count=0,
            has_kitchen=False, has_living=True, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0,
            envelope_minus_corridor_m2=200.0,  # accommodate width
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=0,
        )
