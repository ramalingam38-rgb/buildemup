"""
B-002 — line_type canonicalization on electric_line_clearance.

Bug: check_electric_line_clearance() stored line_type as lowercase or
the literal default "unknown". C3a's _classify_electric_line did
substring match on uppercase ("HT" / "HIGH"), which worked by accident
but value drift in details made tests/logs hard to chase. Fix: canonical
"HT" / "LT" / "UNKNOWN" everywhere.
"""
from __future__ import annotations

import pytest

from buildemup.components.c02.legal_only_checks import (
    check_electric_line_clearance,
)
from buildemup.domain import (
    Brief, Plot, PlotType, PlotOrientation,
    FloorRequirement, FloorUse, RoomRequirement, RoomType,
    BudgetRange, VastuTier, Setbacks,
)


def _make_brief() -> Brief:
    sb = Setbacks(
        front_m=1.5, rear_m=1.5,
        side_left_m=1.5, side_right_m=1.5,
    )
    return Brief(
        plot=Plot(
            width_m=12.0, depth_m=18.0,
            facing=PlotOrientation.NORTH,
            city="chennai", road_width_m=9.0,
            plot_type=PlotType.DETACHED,
        ),
        user_stated_setbacks=sb,
        nbc_compliant_setbacks=sb,
        floors=(
            FloorRequirement(
                floor_number=0, floor_use=FloorUse.RESIDENTIAL,
                rooms=(
                    RoomRequirement(room_type=RoomType.LIVING, count=1),
                    RoomRequirement(room_type=RoomType.KITCHEN, count=1),
                    RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=1),
                ),
                notes="",
            ),
        ),
        budget_range=BudgetRange(min_lakhs=30, max_lakhs=50),
        vastu_preference=VastuTier.OFF,
    )


@pytest.mark.parametrize("input_value,expected_canonical", [
    ("ht", "HT"),
    ("HT", "HT"),
    ("High", "HT"),
    ("high_tension", "HT"),
    ("lt", "LT"),
    ("LT", "LT"),
    ("Low", "LT"),
    ("low_tension", "LT"),
    ("unknown", "UNKNOWN"),
    ("", "UNKNOWN"),
    ("garbage", "UNKNOWN"),
])
def test_line_type_canonicalized_in_details(input_value, expected_canonical):
    """line_type stored in details must be canonical HT / LT / UNKNOWN."""
    brief = _make_brief()
    result = check_electric_line_clearance(
        brief,
        distance_from_electric_line_m=10.0,  # safely above min for either type
        line_type=input_value,
    )
    assert result.details["line_type"] == expected_canonical, (
        f"Input {input_value!r} should canonicalize to {expected_canonical!r}, "
        f"got {result.details['line_type']!r}"
    )


def test_details_line_type_present_when_distance_not_provided():
    """Even when distance is None, details['line_type'] must be populated."""
    brief = _make_brief()
    result = check_electric_line_clearance(
        brief, distance_from_electric_line_m=None,
    )
    assert "line_type" in result.details
    assert result.details["line_type"] == "UNKNOWN"


def test_c3a_detector_compatibility_HT():
    """When line_type='HT', C3a's _classify_electric_line should return LOW."""
    from buildemup.components.c03a.detector import _classify_electric_line
    from buildemup.domain.extreme_case import ResolutionProbability

    brief = _make_brief()
    result = check_electric_line_clearance(
        brief, distance_from_electric_line_m=1.0,  # below HT minimum
        line_type="ht",
    )
    assert _classify_electric_line(result) == ResolutionProbability.LOW


def test_c3a_detector_compatibility_LT():
    """When line_type='LT', C3a's _classify_electric_line should return MEDIUM."""
    from buildemup.components.c03a.detector import _classify_electric_line
    from buildemup.domain.extreme_case import ResolutionProbability

    brief = _make_brief()
    result = check_electric_line_clearance(
        brief, distance_from_electric_line_m=0.5,  # below LT minimum
        line_type="lt",
    )
    assert _classify_electric_line(result) == ResolutionProbability.MEDIUM
