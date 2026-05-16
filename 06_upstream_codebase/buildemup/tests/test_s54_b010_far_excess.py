"""
B-010 — far_compliance HARD_FAIL must populate excess_sqft / excess_sqm.

Bug: check_far_compliance HARD_FAIL details lacked excess_sqft. C3a S3
option_generator for EC-004 fell back to threshold default, silently
disabling option B ("reduce built area by X sqft"). Fix: populate
excess_sqft + excess_sqm + excess_pct on every HARD_FAIL outcome.
"""
from __future__ import annotations

from buildemup.components.c02.legal_only_checks import check_far_compliance
from buildemup.domain import (
    Brief, Plot, PlotType, PlotOrientation,
    FloorRequirement, FloorUse, RoomRequirement, RoomType,
    BudgetRange, VastuTier, Setbacks,
)
from buildemup.domain.feasibility import CheckSeverity


def _make_overbuilt_brief() -> Brief:
    """Small plot + many floors → FAR exceeded → HARD_FAIL on far_compliance."""
    sb = Setbacks(
        front_m=0.5, rear_m=0.5,
        side_left_m=0.5, side_right_m=0.5,
    )
    # 600 sqft Chennai plot, G+3 with many rooms — guaranteed FAR > 2.0
    floors = tuple(
        FloorRequirement(
            floor_number=i, floor_use=FloorUse.RESIDENTIAL,
            rooms=(
                RoomRequirement(room_type=RoomType.LIVING, count=1),
                RoomRequirement(room_type=RoomType.KITCHEN, count=1),
                RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=2),
                RoomRequirement(room_type=RoomType.BEDROOM_REGULAR, count=2),
                RoomRequirement(room_type=RoomType.BATHROOM_ATTACHED, count=2),
            ),
            notes="",
        )
        for i in range(3)
    )
    return Brief(
        plot=Plot(
            width_m=6.096, depth_m=9.144,  # 20x30 ft
            facing=PlotOrientation.NORTH,
            city="chennai", road_width_m=9.0,
            plot_type=PlotType.DETACHED,
        ),
        user_stated_setbacks=sb,
        nbc_compliant_setbacks=sb,
        floors=floors,
        budget_range=BudgetRange(min_lakhs=20, max_lakhs=40),
        vastu_preference=VastuTier.OFF,
    )


def test_hard_fail_populates_excess_sqft():
    """B-010 regression: HARD_FAIL must include excess_sqft in details."""
    brief = _make_overbuilt_brief()
    result = check_far_compliance(brief)
    assert result.severity == CheckSeverity.HARD_FAIL, (
        f"Test setup error: brief should HARD_FAIL on FAR, got "
        f"{result.severity}"
    )
    assert "excess_sqft" in result.details, (
        "B-010 violation: HARD_FAIL did not populate excess_sqft. "
        "C3a EC-004 option_generator falls back to threshold default, "
        "silently disabling 'reduce built area' recommendation."
    )
    assert result.details["excess_sqft"] > 0


def test_hard_fail_populates_excess_sqm_and_pct():
    """Companion fields excess_sqm and excess_pct also populated."""
    brief = _make_overbuilt_brief()
    result = check_far_compliance(brief)
    assert "excess_sqm" in result.details
    assert "excess_pct" in result.details
    assert result.details["excess_sqm"] > 0
    assert result.details["excess_pct"] > 0


def test_hard_fail_message_includes_excess_sqft():
    """User-facing message should mention the concrete sqft excess."""
    brief = _make_overbuilt_brief()
    result = check_far_compliance(brief)
    assert "sqft over" in result.message, (
        "Message should mention 'sqft over' to be actionable for the user"
    )
