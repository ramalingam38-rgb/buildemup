"""
B-014 — SETBACK_INVALID classification for negative / >15m setbacks.

Bug: brief_change_apply's setback handlers let Setbacks.__post_init__
ValueError bubble out, triggering UNKNOWN classification and a generic
"try a different option" message. Fix: catch validation errors, classify
as SETBACK_INVALID, surface the side + result value in context, and
provide a template that names the actual problem.
"""
from __future__ import annotations

import pytest

from buildemup.components.c03a.brief_change_apply import (
    _handle_setbacks_front, _handle_setbacks_rear,
    _handle_setbacks_side_left, _handle_setbacks_side_right,
    CLS_SETBACK_INVALID,
)
from buildemup.components.c03a.error_formatter import (
    format_validation_error_for_user, _TEMPLATES,
)
from buildemup.domain import (
    Brief, Plot, PlotType, PlotOrientation,
    FloorRequirement, FloorUse, RoomRequirement, RoomType,
    BudgetRange, VastuTier, Setbacks,
)
from buildemup.domain.extreme_case import (
    BriefChangeIntegrityError, BriefChange, ResolutionOption,
)


def _make_brief_with_setbacks(front: float = 1.5) -> Brief:
    sb = Setbacks(
        front_m=front, rear_m=1.5,
        side_left_m=1.5, side_right_m=1.5,
    )
    return Brief(
        plot=Plot(
            width_m=12.0, depth_m=15.0,
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
                ),
                notes="",
            ),
        ),
        budget_range=BudgetRange(min_lakhs=30, max_lakhs=50),
        vastu_preference=VastuTier.OFF,
    )


# ─── Template + constant present ─────────────────────────────────────

def test_setback_invalid_template_present():
    """error_formatter must have a SETBACK_INVALID template."""
    assert "SETBACK_INVALID" in _TEMPLATES, (
        "B-014 regression: SETBACK_INVALID template missing"
    )


def test_setback_invalid_constant_exists():
    """brief_change_apply must export CLS_SETBACK_INVALID."""
    assert CLS_SETBACK_INVALID == "SETBACK_INVALID"


# ─── Negative setback delta → classified, not UNKNOWN ────────────────

def test_negative_resulting_setback_classifies_as_setback_invalid():
    """A delta that drives front_m negative must raise SETBACK_INVALID,
    not a raw ValueError or UNKNOWN-classified error."""
    brief = _make_brief_with_setbacks(front=1.5)
    change = BriefChange(
        field_path="setbacks.front_m",
        operation="INCREMENT",
        new_value=-5.0,  # 1.5 + (-5.0) = -3.5, invalid
        description="reduce front setback by 5m",
    )
    with pytest.raises(BriefChangeIntegrityError) as exc_info:
        _handle_setbacks_front(brief, change)
    err = exc_info.value
    assert err.classify() == CLS_SETBACK_INVALID, (
        f"Expected SETBACK_INVALID, got {err.classify()}"
    )
    assert err.context["side"] == "front_m"
    assert err.context["result_m"] == -3.5


def test_oversize_resulting_setback_classifies_as_setback_invalid():
    """A delta that drives front_m > 15m must raise SETBACK_INVALID."""
    brief = _make_brief_with_setbacks(front=1.5)
    change = BriefChange(
        field_path="setbacks.front_m",
        operation="INCREMENT",
        new_value=20.0,  # 1.5 + 20 = 21.5, invalid
        description="add 20m to front setback",
    )
    with pytest.raises(BriefChangeIntegrityError) as exc_info:
        _handle_setbacks_front(brief, change)
    assert exc_info.value.classify() == CLS_SETBACK_INVALID


# ─── Formatter renders a useful message, not "try another" ─────────────

def test_formatter_renders_setback_invalid_specifically():
    """The user-facing reason must name the side + value, NOT fall back
    to the generic 'try another option' UNKNOWN message.
    """
    err = BriefChangeIntegrityError(
        "setbacks.front_m would become -3.50m",
        classification=CLS_SETBACK_INVALID,
        context={
            "side": "front_m",
            "delta_m": -5.0,
            "result_m": -3.5,
            "current_m": 1.5,
        },
    )
    option = ResolutionOption(
        option_id="opt_A",
        description="reduce front setback by 5m",
        impact_summary="frees 5m × plot_width of buildable area",
        cost_impact=None,
        space_impact_sqft=200,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=False,
    )
    msg = format_validation_error_for_user(err, option)
    assert "front_m" in msg
    assert "-3.5" in msg
    assert "0–15m" in msg
    # The generic UNKNOWN fallback must NOT appear
    assert "doesn't work for your brief" not in msg


# ─── Valid setback adjustments still work (no regression) ─────────────

def test_valid_setback_increment_still_works():
    """A reasonable delta still applies cleanly — no false positives."""
    brief = _make_brief_with_setbacks(front=1.5)
    change = BriefChange(
        field_path="setbacks.front_m",
        operation="INCREMENT",
        new_value=0.5,  # 1.5 + 0.5 = 2.0, valid
        description="increase front setback by 0.5m",
    )
    new_brief = _handle_setbacks_front(brief, change)
    assert new_brief.user_stated_setbacks.front_m == 2.0
