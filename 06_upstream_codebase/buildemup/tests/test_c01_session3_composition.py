"""
v0.1 Session 3 tests — Room Composer + Parking + Vastu.

Covers SPEC_v0.2 Section 13:
  - Section C (Room composition + NBC minimums + circulation + staircase)
  - Section E partial (parking feasibility messages)
  - Section F (Vastu integration)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────────
# C. Room composition, circulation, defaults, staircase
# ─────────────────────────────────────────────────────────────────────────

def test_default_g_only_has_ground_floor():
    from buildemup.components.c01.room_composer import (
        default_floors_for_storeys,
    )
    from buildemup.domain import FloorUse
    floors = default_floors_for_storeys(1)
    assert len(floors) == 1
    assert floors[0].floor_number == 0
    assert floors[0].floor_use == FloorUse.RESIDENTIAL
    assert len(floors[0].rooms) >= 3   # living, kitchen, bath at minimum
    print(f"PASS default G-only: 1 floor with {len(floors[0].rooms)} rooms")


def test_default_g1_template():
    from buildemup.components.c01.room_composer import (
        default_floors_for_storeys,
    )
    from buildemup.domain import RoomType
    floors = default_floors_for_storeys(2)
    assert len(floors) == 2
    # Floor 1 should have master bedroom
    room_types_floor1 = {r.room_type for r in floors[1].rooms}
    assert RoomType.BEDROOM_MASTER in room_types_floor1
    print(f"PASS default G+1: master bedroom on floor 1")


def test_default_g3_has_terrace_on_top():
    from buildemup.components.c01.room_composer import (
        default_floors_for_storeys,
    )
    from buildemup.domain import FloorUse
    floors = default_floors_for_storeys(4)
    assert len(floors) == 4
    # Top floor should be terrace
    assert floors[-1].floor_use == FloorUse.TERRACE_ACCESSIBLE
    print("PASS default G+3: terrace on top")


def test_default_floors_rejects_out_of_range():
    from buildemup.components.c01.room_composer import (
        default_floors_for_storeys,
    )
    for bad in [0, 5, -1]:
        try:
            default_floors_for_storeys(bad)
            assert False, f"Expected ValueError for {bad}"
        except ValueError:
            pass
    print("PASS default_floors rejects out-of-range (0, 5, -1)")


def test_circulation_factor_applied():
    """Floor area with circulation = sum(rooms) × factor (1.30/1.35/1.40).

    v0.9: factor is now size-aware per IS 3861-2002 research.
    """
    from buildemup.components.c01.room_composer import (
        estimate_floor_area_sqm,
    )
    from buildemup.domain import (
        FloorRequirement, FloorUse, RoomRequirement, RoomType,
    )
    floor = FloorRequirement(
        floor_number=0,
        floor_use=FloorUse.RESIDENTIAL,
        rooms=(
            RoomRequirement(RoomType.LIVING, 1, preferred_size_sqm=15.0),
            RoomRequirement(RoomType.KITCHEN, 1, preferred_size_sqm=8.0),
        ),
    )
    # Room area = 15 + 8 = 23 sqm (< 30 threshold, so "small" factor 1.40).
    # 23 × 1.40 = 32.2 sqm.
    est = estimate_floor_area_sqm(floor)
    assert abs(est - 32.2) < 0.1, f"Expected ~32.2, got {est}"
    print(f"PASS circulation factor applied: "
          f"23 sqm rooms → {est:.1f} sqm floor (×1.40 small-home)")


def test_stilt_floor_returns_zero_built_area():
    """STILT_PARKING is structure-only, not counted in built-up area."""
    from buildemup.components.c01.room_composer import (
        estimate_floor_area_sqm,
    )
    from buildemup.domain import FloorRequirement, FloorUse
    stilt = FloorRequirement(
        floor_number=0, floor_use=FloorUse.STILT_PARKING,
    )
    assert estimate_floor_area_sqm(stilt) == 0.0
    print("PASS stilt parking contributes 0 to built-up area")


def test_terrace_inaccessible_zero_built_area():
    from buildemup.components.c01.room_composer import (
        estimate_floor_area_sqm,
    )
    from buildemup.domain import FloorRequirement, FloorUse
    t = FloorRequirement(
        floor_number=2, floor_use=FloorUse.TERRACE_INACCESSIBLE,
    )
    assert estimate_floor_area_sqm(t) == 0.0
    print("PASS terrace_inaccessible → 0 built-up")


def test_auto_staircase_added_to_multi_floor():
    """If floors ≥ 2 and no staircase, add to ground with INFO message."""
    from buildemup.components.c01.room_composer import (
        default_floors_for_storeys, ensure_staircase_present,
    )
    from buildemup.domain import RoomType
    g1 = default_floors_for_storeys(2)
    # Verify no staircase in defaults
    assert not any(f.has_staircase for f in g1)

    updated, msgs = ensure_staircase_present(g1)
    assert len(msgs) == 1
    assert msgs[0].context == "auto_staircase"

    # Ground floor should now have staircase
    ground = updated[0]
    assert any(r.room_type == RoomType.STAIRCASE for r in ground.rooms)
    print(f"PASS auto-staircase added to ground floor with INFO message")


def test_auto_staircase_skipped_for_single_floor():
    """G-only home doesn't need staircase."""
    from buildemup.components.c01.room_composer import (
        default_floors_for_storeys, ensure_staircase_present,
    )
    g = default_floors_for_storeys(1)
    updated, msgs = ensure_staircase_present(g)
    assert len(msgs) == 0
    assert not any(f.has_staircase for f in updated)
    print("PASS single floor → no auto-staircase")


def test_auto_staircase_idempotent():
    """If user already added staircase, we don't duplicate."""
    from buildemup.components.c01.room_composer import (
        ensure_staircase_present,
    )
    from buildemup.domain import (
        FloorRequirement, FloorUse, RoomRequirement, RoomType,
    )
    floors = (
        FloorRequirement(
            floor_number=0,
            floor_use=FloorUse.RESIDENTIAL,
            rooms=(
                RoomRequirement(RoomType.LIVING, 1),
                RoomRequirement(RoomType.STAIRCASE, 1),
            ),
        ),
        FloorRequirement(
            floor_number=1, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.BEDROOM_MASTER, 1),),
        ),
    )
    updated, msgs = ensure_staircase_present(floors)
    assert len(msgs) == 0
    # Ground floor rooms unchanged
    assert len(updated[0].rooms) == 2
    print("PASS auto-staircase is idempotent")


def test_auto_staircase_on_first_floor_when_ground_is_stilt():
    """STILT ground → staircase goes to floor 1, not stilt."""
    from buildemup.components.c01.room_composer import (
        ensure_staircase_present,
    )
    from buildemup.domain import (
        FloorRequirement, FloorUse, RoomRequirement, RoomType,
    )
    floors = (
        FloorRequirement(floor_number=0, floor_use=FloorUse.STILT_PARKING),
        FloorRequirement(
            floor_number=1, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.LIVING, 1),),
        ),
    )
    updated, msgs = ensure_staircase_present(floors)
    # Floor 0 (stilt) stays empty
    assert len(updated[0].rooms) == 0
    # Floor 1 gets staircase
    assert any(r.room_type == RoomType.STAIRCASE for r in updated[1].rooms)
    # Message mentions first floor
    assert "first floor" in msgs[0].text
    print("PASS stilt at ground → staircase goes to first floor")


# ─────────────────────────────────────────────────────────────────────────
# E. Parking feasibility (Drawback 7)
# ─────────────────────────────────────────────────────────────────────────

def test_parking_ok_on_wide_plot():
    """Plot ≥ 8m + stilt → no guidance."""
    from buildemup.components.c01.parking_feasibility import (
        check_parking_feasibility,
    )
    msgs = check_parking_feasibility(
        plot_width_m=10.0, plot_depth_m=12.0,
        has_stilt_parking=True,
        side_left_setback_m=1.5, side_right_setback_m=1.5,
    )
    assert len(msgs) == 0
    print("PASS wide plot + stilt: no concern")


def test_parking_concern_on_narrow_plot():
    """Plot 6-8m + stilt → STRONG_CONCERN."""
    from buildemup.components.c01.parking_feasibility import (
        check_parking_feasibility,
    )
    from buildemup.domain import GuidanceSeverity
    msgs = check_parking_feasibility(
        plot_width_m=7.0, plot_depth_m=12.0,
        has_stilt_parking=True,
        side_left_setback_m=1.5, side_right_setback_m=1.5,
    )
    assert len(msgs) == 1
    assert msgs[0].severity == GuidanceSeverity.STRONG_CONCERN
    assert "tight" in msgs[0].text.lower()
    print(f"PASS narrow plot (7m) + stilt → STRONG_CONCERN")


def test_parking_critical_concern_below_6m():
    """Plot < 6m + stilt → STRONG_CONCERN (critical wording)."""
    from buildemup.components.c01.parking_feasibility import (
        check_parking_feasibility,
    )
    from buildemup.domain import GuidanceSeverity
    msgs = check_parking_feasibility(
        plot_width_m=5.0, plot_depth_m=12.0,
        has_stilt_parking=True,
        side_left_setback_m=1.0, side_right_setback_m=1.0,
    )
    assert len(msgs) == 1
    assert msgs[0].severity == GuidanceSeverity.STRONG_CONCERN
    # Critical variant mentions 'very tight'
    assert "very tight" in msgs[0].text.lower()
    print(f"PASS critical narrow plot (5m) + stilt → strongest wording")


def test_parking_no_check_without_stilt():
    """If no stilt parking, we don't check."""
    from buildemup.components.c01.parking_feasibility import (
        check_parking_feasibility,
    )
    msgs = check_parking_feasibility(
        plot_width_m=5.0, plot_depth_m=12.0,
        has_stilt_parking=False,
        side_left_setback_m=1.0, side_right_setback_m=1.0,
    )
    assert len(msgs) == 0
    print("PASS no stilt → no parking check")


def test_stilt_car_capacity_estimate():
    """Car capacity estimator returns expected integer counts."""
    from buildemup.components.c01.parking_feasibility import (
        estimate_stilt_car_capacity,
    )
    # 10m plot, 1.5m each side = 7m internal, 7/3 = 2 cars
    assert estimate_stilt_car_capacity(10.0, 1.5, 1.5) == 2
    # 13m plot, 1.5 each = 10m internal, 10/3 = 3 cars
    assert estimate_stilt_car_capacity(13.0, 1.5, 1.5) == 3
    # Too narrow: 5m plot, 1m each = 3m internal = 1 car
    assert estimate_stilt_car_capacity(5.0, 1.0, 1.0) == 1
    # Zero cars on extremely narrow
    assert estimate_stilt_car_capacity(4.0, 1.5, 1.5) == 0
    print("PASS stilt car capacity estimator")


# ─────────────────────────────────────────────────────────────────────────
# F. Vastu integration
# ─────────────────────────────────────────────────────────────────────────

def test_vastu_off_produces_no_messages():
    from buildemup.components.c01.vastu_filter import generate_vastu_guidance
    from buildemup.domain import Plot, PlotOrientation, VastuTier
    p = Plot(width_m=9, depth_m=12, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9)
    msgs = generate_vastu_guidance(p, VastuTier.OFF)
    assert len(msgs) == 0
    print("PASS VastuTier.OFF → no messages")


def test_vastu_partial_has_exactly_7_items():
    """PARTIAL must produce exactly 7 messages — per user approval."""
    from buildemup.components.c01.vastu_filter import generate_vastu_guidance
    from buildemup.domain import Plot, PlotOrientation, VastuTier
    p = Plot(width_m=9, depth_m=12, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9)
    msgs = generate_vastu_guidance(p, VastuTier.PARTIAL)
    assert len(msgs) == 7
    # Check context tags cover the 7 items
    contexts = {m.context for m in msgs}
    expected = {
        "vastu_main_door", "vastu_kitchen", "vastu_master_bedroom",
        "vastu_pooja", "vastu_toilet", "vastu_staircase",
        "vastu_water_tank",
    }
    assert contexts == expected
    print(f"PASS PARTIAL produces exactly 7 messages with expected contexts")


def test_vastu_full_extends_partial():
    """FULL = 7 PARTIAL + additional items."""
    from buildemup.components.c01.vastu_filter import generate_vastu_guidance
    from buildemup.domain import Plot, PlotOrientation, VastuTier
    p = Plot(width_m=9, depth_m=12, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9)
    msgs_partial = generate_vastu_guidance(p, VastuTier.PARTIAL)
    msgs_full = generate_vastu_guidance(p, VastuTier.FULL)
    # First 7 of FULL == PARTIAL (same instances)
    assert msgs_full[:7] == msgs_partial
    # FULL has more
    assert len(msgs_full) > len(msgs_partial)
    print(f"PASS FULL = PARTIAL 7 + {len(msgs_full) - 7} additional items")


def test_vastu_all_messages_are_info_only():
    """CRITICAL: vastu NEVER produces STRONG_CONCERN or CONCERN."""
    from buildemup.components.c01.vastu_filter import generate_vastu_guidance
    from buildemup.domain import (
        Plot, PlotOrientation, VastuTier, GuidanceSeverity,
    )
    # Test with multiple plot facings
    for facing in [PlotOrientation.NORTH, PlotOrientation.SOUTH,
                   PlotOrientation.EAST, PlotOrientation.WEST]:
        p = Plot(width_m=9, depth_m=12, facing=facing,
                 city="chennai", road_width_m=9)
        for tier in [VastuTier.PARTIAL, VastuTier.FULL]:
            msgs = generate_vastu_guidance(p, tier)
            for m in msgs:
                assert m.severity == GuidanceSeverity.INFO, (
                    f"{facing.value} {tier.value}: "
                    f"found non-INFO severity {m.severity}"
                )
    print(f"PASS vastu messages are INFO-only across all facings and tiers")


def test_vastu_south_facing_plot_main_door_warning():
    """South-facing plot gets 'traditionally avoided' text for main door."""
    from buildemup.components.c01.vastu_filter import generate_vastu_guidance
    from buildemup.domain import Plot, PlotOrientation, VastuTier
    p = Plot(width_m=9, depth_m=12, facing=PlotOrientation.SOUTH,
             city="chennai", road_width_m=9)
    msgs = generate_vastu_guidance(p, VastuTier.PARTIAL)
    main_door = next(m for m in msgs if m.context == "vastu_main_door")
    assert "traditionally avoided" in main_door.text.lower()
    # Still INFO severity
    from buildemup.domain import GuidanceSeverity
    assert main_door.severity == GuidanceSeverity.INFO
    print("PASS south-facing plot: main door flagged but still INFO")


def test_vastu_partial_items_match_user_approved_list():
    """The 7 items user approved must match VASTU_PARTIAL_ITEMS."""
    from buildemup.domain import VASTU_PARTIAL_ITEMS
    from buildemup.components.c01.vastu_filter import (
        list_partial_items_for_form_display,
    )
    # Both sources must return the same 7 items
    assert list_partial_items_for_form_display() == VASTU_PARTIAL_ITEMS
    assert len(VASTU_PARTIAL_ITEMS) == 7
    # Verify specific items user approved
    joined = " ".join(VASTU_PARTIAL_ITEMS).lower()
    assert "main door" in joined
    assert "kitchen" in joined
    assert "master bedroom" in joined
    assert "pooja" in joined
    assert "toilet" in joined or "bathroom" in joined
    assert "staircase" in joined
    assert "water tank" in joined
    print(f"PASS 7 PARTIAL items match user-approved list")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.1 — Session 3 Tests: Room Composer + Parking + Vastu")
    print("=" * 70)
    print()
    print("--- C. Room composition + circulation + staircase ---")
    test_default_g_only_has_ground_floor()
    test_default_g1_template()
    test_default_g3_has_terrace_on_top()
    test_default_floors_rejects_out_of_range()
    test_circulation_factor_applied()
    test_stilt_floor_returns_zero_built_area()
    test_terrace_inaccessible_zero_built_area()
    test_auto_staircase_added_to_multi_floor()
    test_auto_staircase_skipped_for_single_floor()
    test_auto_staircase_idempotent()
    test_auto_staircase_on_first_floor_when_ground_is_stilt()
    print()
    print("--- E. Parking feasibility ---")
    test_parking_ok_on_wide_plot()
    test_parking_concern_on_narrow_plot()
    test_parking_critical_concern_below_6m()
    test_parking_no_check_without_stilt()
    test_stilt_car_capacity_estimate()
    print()
    print("--- F. Vastu integration ---")
    test_vastu_off_produces_no_messages()
    test_vastu_partial_has_exactly_7_items()
    test_vastu_full_extends_partial()
    test_vastu_all_messages_are_info_only()
    test_vastu_south_facing_plot_main_door_warning()
    test_vastu_partial_items_match_user_approved_list()
    print()
    print("=" * 70)
    print("ALL SESSION 3 TESTS PASSED")
    print("=" * 70)
