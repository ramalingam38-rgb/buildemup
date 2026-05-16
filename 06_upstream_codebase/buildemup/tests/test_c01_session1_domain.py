"""
v0.1 Session 1 tests — Component 1 Domain Objects.

Covers SPEC_v0.2 Section 13-A (domain validation, ~10 tests).
Subsequent sessions add Sections B-J.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────────
# A. Domain object validation (~10 tests per SPEC_v0.2 Section 13)
# ─────────────────────────────────────────────────────────────────────────

def test_plot_accepts_valid_dimensions():
    from buildemup.domain import Plot, PlotOrientation, PlotType
    p = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0)
    assert p.width_m == 9.0
    assert p.area_sqm == 108.0
    assert p.plot_type == PlotType.DETACHED  # default
    print(f"PASS Plot accepts valid dimensions ({p.describe()[:40]}...)")


def test_plot_rejects_out_of_range_dimensions():
    from buildemup.domain import Plot, PlotOrientation
    # Width too narrow
    try:
        Plot(width_m=2.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0)
        assert False, "Expected ValueError for width=2"
    except ValueError as e:
        assert "out of range" in str(e)
    # Depth too deep
    try:
        Plot(width_m=9.0, depth_m=70.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0)
        assert False, "Expected ValueError for depth=70"
    except ValueError as e:
        assert "out of range" in str(e)
    # Road too narrow
    try:
        Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=1.0)
        assert False, "Expected ValueError for road=1m"
    except ValueError as e:
        assert "out of range" in str(e)
    print("PASS Plot rejects out-of-range width/depth/road")


def test_plot_rejects_unsupported_city():
    from buildemup.domain import Plot, PlotOrientation
    try:
        Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="atlantis", road_width_m=9.0)
        assert False, "Expected ValueError for unknown city"
    except ValueError as e:
        assert "not supported" in str(e)
    # Case insensitivity
    p = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="Chennai", road_width_m=9.0)
    assert p.city == "chennai"  # normalized
    print("PASS Plot rejects unsupported cities + normalizes case")


def test_plot_corner_requires_second_road():
    from buildemup.domain import Plot, PlotOrientation
    try:
        Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0, corner_plot=True)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "second_road_width_m" in str(e)
    # With second road width: works
    p = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0, corner_plot=True,
             second_road_width_m=6.0)
    assert p.wider_road_width_m == 9.0  # picks the wider
    print("PASS corner plot requires second_road_width, picks wider")


def test_plot_semi_detached_requires_shared_side():
    from buildemup.domain import Plot, PlotOrientation, PlotType, SharedSide
    # Missing shared_side
    try:
        Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0,
             plot_type=PlotType.SEMI_DETACHED)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "shared_side" in str(e)
    # With shared_side: works
    p = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0,
             plot_type=PlotType.SEMI_DETACHED, shared_side=SharedSide.LEFT)
    assert p.shared_side == SharedSide.LEFT
    # shared_side with DETACHED: rejected
    try:
        Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0,
             plot_type=PlotType.DETACHED, shared_side=SharedSide.LEFT)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "shared_side only meaningful" in str(e)
    print("PASS SEMI_DETACHED requires shared_side, DETACHED rejects it")


def test_setbacks_validates_and_compares():
    from buildemup.domain import Setbacks
    # Valid
    s = Setbacks(front_m=1.5, rear_m=1.5, side_left_m=1.5, side_right_m=1.5)
    assert s.total_width_reduction_m == 3.0
    assert s.total_depth_reduction_m == 3.0
    # Negative rejected
    try:
        Setbacks(front_m=-1, rear_m=1.5, side_left_m=1.5, side_right_m=1.5)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "cannot be negative" in str(e)
    # Unreasonably large rejected
    try:
        Setbacks(front_m=20, rear_m=1.5, side_left_m=1.5, side_right_m=1.5)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "exceeds 15m" in str(e)
    # is_at_least
    small = Setbacks(1.0, 1.0, 1.0, 1.0)
    big = Setbacks(1.5, 1.5, 1.5, 1.5)
    assert big.is_at_least(small) is True
    assert small.is_at_least(big) is False
    # difference_from returns signed diffs
    diff = small.difference_from(big)
    assert diff["front_m"] == -0.5
    assert diff["rear_m"] == -0.5
    print("PASS Setbacks validates + compares correctly")


def test_room_requirement_nbc_minimum_applied():
    from buildemup.domain import (
        RoomRequirement, RoomType, NBC_MINIMUM_ROOM_SIZES_SQM,
    )
    # No sizes specified → NBC default
    r = RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=1)
    assert r.effective_size_sqm == NBC_MINIMUM_ROOM_SIZES_SQM[RoomType.BEDROOM_MASTER]
    assert r.effective_size_sqm == 9.5
    # Preferred overrides
    r2 = RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=1,
                         preferred_size_sqm=12.0)
    assert r2.effective_size_sqm == 12.0
    # Below NBC rejected
    try:
        RoomRequirement(room_type=RoomType.KITCHEN, count=1,
                        preferred_size_sqm=3.0)  # NBC is 5.0
        assert False, "Expected ValueError for sub-NBC size"
    except ValueError as e:
        assert "below NBC minimum" in str(e)
    print(f"PASS RoomRequirement applies NBC minimums + overrides")


def test_floor_requirement_assembly():
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    floor = FloorRequirement(
        floor_number=0,
        floor_use=FloorUse.RESIDENTIAL,
        rooms=(
            RoomRequirement(RoomType.LIVING, 1),
            RoomRequirement(RoomType.KITCHEN, 1),
            RoomRequirement(RoomType.BEDROOM_MASTER, 1),
            RoomRequirement(RoomType.BATHROOM_ATTACHED, 1),
        ),
    )
    # Sum = 9.5 + 5.0 + 9.5 + 1.8 = 25.8
    assert abs(floor.total_room_area_sqm() - 25.8) < 0.01
    assert floor.has_staircase is False
    assert floor.is_load_bearing is True
    # Negative floor_number rejected
    try:
        FloorRequirement(floor_number=-1, floor_use=FloorUse.RESIDENTIAL)
        assert False
    except ValueError as e:
        assert "cannot be negative" in str(e)
    # floor > 3 rejected
    try:
        FloorRequirement(floor_number=4, floor_use=FloorUse.RESIDENTIAL)
        assert False
    except ValueError as e:
        assert "G+3" in str(e)
    print(f"PASS FloorRequirement assembly + validation")


def test_budget_range_validation():
    from buildemup.domain import BudgetRange
    # Valid
    b = BudgetRange(min_lakhs=15, max_lakhs=25)
    assert b.min_rupees == 1_500_000
    assert b.max_rupees == 2_500_000
    assert b.currency == "INR"
    # Max < Min rejected
    try:
        BudgetRange(min_lakhs=25, max_lakhs=15)
        assert False
    except ValueError as e:
        assert "< min_lakhs" in str(e)
    # Currency other than INR rejected in v0.1
    try:
        BudgetRange(min_lakhs=15, max_lakhs=25, currency="USD")
        assert False
    except ValueError as e:
        assert "INR only" in str(e)
    print(f"PASS BudgetRange validation (min<max, INR only)")


def test_brief_assembly_and_validation():
    from buildemup.domain import (
        Plot, PlotOrientation, Setbacks, FloorRequirement, RoomRequirement,
        FloorUse, RoomType, Brief, BudgetRange, VastuTier,
    )
    plot = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
                city="chennai", road_width_m=9.0)
    setbacks = Setbacks(1.5, 1.5, 1.5, 1.5)
    floor0 = FloorRequirement(
        floor_number=0, floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(RoomType.LIVING, 1),),
    )
    floor1 = FloorRequirement(
        floor_number=1, floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(RoomType.BEDROOM_MASTER, 1),),
    )

    brief = Brief(
        plot=plot,
        user_stated_setbacks=setbacks,
        nbc_compliant_setbacks=setbacks,
        floors=(floor0, floor1),
        budget_range=BudgetRange(min_lakhs=20, max_lakhs=30),
        vastu_preference=VastuTier.PARTIAL,
    )
    assert brief.total_floors_above_ground == 1  # floor 1
    assert brief.has_stilt_parking is False
    assert brief.vastu_preference == VastuTier.PARTIAL

    # Non-contiguous floor numbers rejected
    try:
        Brief(
            plot=plot,
            user_stated_setbacks=setbacks,
            nbc_compliant_setbacks=setbacks,
            floors=(floor0, FloorRequirement(floor_number=2, floor_use=FloorUse.RESIDENTIAL)),
            budget_range=BudgetRange(15, 25),
        )
        assert False, "Expected ValueError for non-contiguous floors"
    except ValueError as e:
        assert "contiguous" in str(e)

    # Stilt at floor > 0 rejected
    try:
        Brief(
            plot=plot,
            user_stated_setbacks=setbacks,
            nbc_compliant_setbacks=setbacks,
            floors=(
                floor0,
                FloorRequirement(floor_number=1, floor_use=FloorUse.STILT_PARKING),
            ),
            budget_range=BudgetRange(15, 25),
        )
        assert False, "Expected ValueError for stilt on floor 1"
    except ValueError as e:
        assert "STILT_PARKING must be ground floor" in str(e)

    print(f"PASS Brief assembly + contiguity + stilt placement rules")


def test_vastu_partial_items_visible():
    """Q5: user must see exactly what PARTIAL vastu includes."""
    from buildemup.domain import VASTU_PARTIAL_ITEMS, VastuTier
    assert len(VASTU_PARTIAL_ITEMS) == 7
    # Check the 7 specific items the user approved
    joined = " ".join(VASTU_PARTIAL_ITEMS).lower()
    assert "main door" in joined
    assert "kitchen" in joined
    assert "master bedroom" in joined
    assert "pooja" in joined
    assert "toilet" in joined or "bathroom" in joined
    assert "staircase" in joined
    assert "water tank" in joined
    # Default tier is OFF
    from dataclasses import fields
    # Just check VastuTier enum
    assert VastuTier.OFF.value == "off"
    assert VastuTier.PARTIAL.value == "partial"
    assert VastuTier.FULL.value == "full"
    print(f"PASS vastu partial list has the 7 user-approved items")


def test_plot_type_enum_values():
    from buildemup.domain import PlotType
    assert PlotType.DETACHED.value == "detached"
    assert PlotType.SEMI_DETACHED.value == "semi_detached"
    assert PlotType.CONTINUOUS.value == "continuous"
    # All three values accessible
    assert len(list(PlotType)) == 3
    print("PASS PlotType enum has 3 values (detached/semi/continuous)")


def test_domain_types_registered_for_enforcement():
    """v0.7.1: Component 1 types must be in _DOMAIN_TYPE_NAMES."""
    from buildemup.utils.component_contract import _DOMAIN_TYPE_NAMES
    # Component 1 types
    for type_name in [
        "Plot", "Setbacks", "Brief",
        "FloorRequirement", "RoomRequirement",
        "BudgetRange", "CostEstimate",
        "ComplianceSummary", "GuidanceMessage",
    ]:
        assert type_name in _DOMAIN_TYPE_NAMES, \
            f"{type_name} missing from domain enforcement registry"
    # Component 7 types still there (no regression)
    for type_name in ["Building", "Envelope", "Floor", "Column"]:
        assert type_name in _DOMAIN_TYPE_NAMES
    print(f"PASS {len(_DOMAIN_TYPE_NAMES)} types registered for domain enforcement")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.1 — Session 1 Tests: Domain Objects")
    print("=" * 70)
    print()
    print("--- A. Domain object validation ---")
    test_plot_accepts_valid_dimensions()
    test_plot_rejects_out_of_range_dimensions()
    test_plot_rejects_unsupported_city()
    test_plot_corner_requires_second_road()
    test_plot_semi_detached_requires_shared_side()
    test_setbacks_validates_and_compares()
    test_room_requirement_nbc_minimum_applied()
    test_floor_requirement_assembly()
    test_budget_range_validation()
    test_brief_assembly_and_validation()
    test_vastu_partial_items_visible()
    test_plot_type_enum_values()
    test_domain_types_registered_for_enforcement()
    print()
    print("=" * 70)
    print("ALL SESSION 1 TESTS PASSED")
    print("=" * 70)
