"""
B-003 — regression test for Mumbai + Pune stilt mandate thresholds.

Bug: STILT_MANDATE_BY_CITY in c02/legal_only_checks.py had only Delhi.
Mumbai and Pune briefs silently bypassed the HARD_FAIL check (returned
NOT_APPLICABLE) even though both cities' DCRs mandate stilt for
residential plots in the 300-2000 sqm range.

Fix (S54): Added Mumbai + Pune to the mandate dict with conservative
thresholds (300 sqm minimum). Source flagged for primary-PDF verification
under B-150 full.
"""
from __future__ import annotations

import pytest
from buildemup.components.c02.legal_only_checks import (
    check_stilt_mandate_compliance, STILT_MANDATE_BY_CITY,
)
from buildemup.domain import (
    Brief, Plot, PlotType, PlotOrientation,
    FloorRequirement, FloorUse, RoomRequirement, RoomType,
    BudgetRange, VastuTier, Setbacks,
)


def _make_brief(
    *, city: str, plot_width_m: float = 16.0, plot_depth_m: float = 25.0,
    has_stilt: bool = False,
) -> Brief:
    """Build a minimal Brief for a stilt mandate test."""
    floors_list = []
    if has_stilt:
        floors_list.append(FloorRequirement(
            floor_number=0,
            floor_use=FloorUse.STILT_PARKING,
            rooms=(),
            notes="",
        ))
    floors_list.append(FloorRequirement(
        floor_number=1 if has_stilt else 0,
        floor_use=FloorUse.RESIDENTIAL,
        rooms=(
            RoomRequirement(room_type=RoomType.LIVING, count=1),
            RoomRequirement(room_type=RoomType.KITCHEN, count=1),
            RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=1),
        ),
        notes="",
    ))
    plot = Plot(
        width_m=plot_width_m, depth_m=plot_depth_m,
        facing=PlotOrientation.NORTH,
        city=city, road_width_m=9.0,
        plot_type=PlotType.DETACHED,
    )
    sb = Setbacks(
        front_m=1.5, rear_m=1.5,
        side_left_m=1.5, side_right_m=1.5,
    )
    return Brief(
        plot=plot,
        user_stated_setbacks=sb,
        nbc_compliant_setbacks=sb,
        floors=tuple(floors_list),
        budget_range=BudgetRange(min_lakhs=30, max_lakhs=50),
        additional_requirements=(),
        vastu_preference=VastuTier.OFF,
    )


# ─── KB has the new cities ─────────────────────────────────────────────

def test_mumbai_in_stilt_mandate_dict():
    """Regression: mumbai must be in STILT_MANDATE_BY_CITY (was missing)."""
    assert "mumbai" in STILT_MANDATE_BY_CITY, (
        "B-003 regression: Mumbai stilt mandate threshold is missing"
    )
    entry = STILT_MANDATE_BY_CITY["mumbai"]
    assert entry["min_plot_sqm"] > 0
    assert entry["max_plot_sqm"] > entry["min_plot_sqm"]
    assert "DCPR" in entry["source"], (
        "Mumbai source citation should mention DCPR (Development Control "
        "and Promotion Regulations)"
    )


def test_pune_in_stilt_mandate_dict():
    """Regression: pune must be in STILT_MANDATE_BY_CITY (was missing)."""
    assert "pune" in STILT_MANDATE_BY_CITY, (
        "B-003 regression: Pune stilt mandate threshold is missing"
    )
    entry = STILT_MANDATE_BY_CITY["pune"]
    assert entry["min_plot_sqm"] > 0
    assert entry["max_plot_sqm"] > entry["min_plot_sqm"]
    assert "UDCPR" in entry["source"], (
        "Pune source citation should mention UDCPR (Unified DCR)"
    )


# ─── HARD_FAIL fires for in-range Mumbai/Pune briefs without stilt ─────

@pytest.mark.parametrize("city,width_m,depth_m,expect_in_range", [
    ("mumbai", 16.0, 25.0, True),    # 400 sqm — in mandate range
    ("pune",   16.0, 25.0, True),    # 400 sqm — in mandate range
    ("mumbai", 10.0, 12.0, False),   # 120 sqm — below 300 sqm minimum
    ("pune",   10.0, 12.0, False),   # 120 sqm — below 300 sqm minimum
])
def test_stilt_check_correctly_classifies_plot(
    city, width_m, depth_m, expect_in_range,
):
    """In-range plot WITHOUT stilt → HARD_FAIL. Out-of-range → NOT_APPLICABLE."""
    from buildemup.domain.feasibility import CheckSeverity
    brief = _make_brief(
        city=city, plot_width_m=width_m, plot_depth_m=depth_m,
        has_stilt=False,
    )
    result = check_stilt_mandate_compliance(brief)
    if expect_in_range:
        assert result.severity == CheckSeverity.HARD_FAIL, (
            f"{city} brief in mandate range without stilt should HARD_FAIL "
            f"per B-003 fix; got {result.severity}"
        )
    else:
        assert result.severity == CheckSeverity.NOT_APPLICABLE, (
            f"{city} brief out of mandate range should be NOT_APPLICABLE; "
            f"got {result.severity}"
        )


def test_stilt_check_passes_when_brief_has_stilt():
    """In-range plot WITH stilt → PASS, not HARD_FAIL."""
    from buildemup.domain.feasibility import CheckSeverity
    brief = _make_brief(
        city="mumbai", plot_width_m=16.0, plot_depth_m=25.0,
        has_stilt=True,
    )
    result = check_stilt_mandate_compliance(brief)
    assert result.severity == CheckSeverity.PASS, (
        f"Mumbai with stilt should PASS; got {result.severity}"
    )


# ─── Delhi behaviour unchanged (regression guard) ──────────────────────

def test_delhi_unchanged_in_range():
    """Delhi mandate kept at 100-1000 sqm — fix must not affect it."""
    from buildemup.domain.feasibility import CheckSeverity
    brief = _make_brief(
        city="delhi", plot_width_m=16.0, plot_depth_m=20.0,
        has_stilt=False,
    )
    result = check_stilt_mandate_compliance(brief)
    assert result.severity == CheckSeverity.HARD_FAIL
