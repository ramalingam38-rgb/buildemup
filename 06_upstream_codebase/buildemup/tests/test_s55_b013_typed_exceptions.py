"""B-013 (S55): typed exception classes for Brief validation.

Before this change, S4's `_classify_error()` substring-matched the
text of `ValueError` messages raised by Brief / RoomRequirement /
BudgetRange / FloorRequirement. Wording changes silently regressed
classification to UNKNOWN.

After this change, each validator raises a typed `BriefDomainError`
subclass; `_classify_error` dispatches on type first and falls back
to the legacy substring path. All typed errors subclass `ValueError`
so existing `except ValueError` sites stay unchanged.
"""
from __future__ import annotations

import pytest

from buildemup.components.c03a.brief_change_apply import (
    CLS_BEDROOM,
    CLS_BUDGET,
    CLS_FLOOR_COUNT,
    CLS_ROOM_AREA,
    _classify_error,
)
from buildemup.domain.brief import BudgetRange
from buildemup.domain.exceptions import (
    BriefDomainError,
    BudgetValidationError,
    FloorCountTooLowError,
    FloorNumberOutOfRangeError,
    RoomCountNegativeError,
    RoomSizeBelowNbcMinError,
)
from buildemup.domain.extreme_case import BriefChange
from buildemup.domain.floor_requirement import (
    FloorRequirement,
    FloorUse,
    RoomRequirement,
    RoomType,
)


# ─────────────────────────────────────────────────────────────────────
# 1) Each typed error is raised by the right validator
# ─────────────────────────────────────────────────────────────────────

def test_budget_implausibly_low_raises_typed_error():
    with pytest.raises(BudgetValidationError) as ei:
        BudgetRange(min_lakhs=0, max_lakhs=50)
    assert "implausibly low" in str(ei.value)


def test_budget_max_less_than_min_raises_typed_error():
    with pytest.raises(BudgetValidationError) as ei:
        BudgetRange(min_lakhs=50, max_lakhs=30)
    assert "max_lakhs" in str(ei.value)


def test_room_count_negative_raises_typed_error():
    with pytest.raises(RoomCountNegativeError):
        RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=-1)


def test_room_size_below_nbc_min_raises_typed_error():
    with pytest.raises(RoomSizeBelowNbcMinError):
        RoomRequirement(
            room_type=RoomType.BEDROOM_MASTER,
            count=1,
            min_size_sqm=2.0,  # NBC min is far higher
        )


def test_floor_number_above_max_raises_typed_error():
    with pytest.raises(FloorNumberOutOfRangeError):
        FloorRequirement(floor_number=4, floor_use=FloorUse.RESIDENTIAL)


def test_floor_number_negative_raises_typed_error():
    with pytest.raises(FloorNumberOutOfRangeError):
        FloorRequirement(floor_number=-1, floor_use=FloorUse.RESIDENTIAL)


# ─────────────────────────────────────────────────────────────────────
# 2) Backwards compatibility — typed errors still ARE ValueErrors
# ─────────────────────────────────────────────────────────────────────

def test_typed_errors_subclass_value_error():
    """`except ValueError` sites must continue to work unchanged."""
    for cls in (
        BudgetValidationError,
        FloorCountTooLowError,
        FloorNumberOutOfRangeError,
        RoomCountNegativeError,
        RoomSizeBelowNbcMinError,
    ):
        assert issubclass(cls, ValueError)
        assert issubclass(cls, BriefDomainError)


def test_budget_typed_error_caught_by_value_error_clause():
    try:
        BudgetRange(min_lakhs=0, max_lakhs=50)
    except ValueError:
        return  # backwards compat preserved
    pytest.fail("BudgetValidationError did not satisfy except ValueError")


# ─────────────────────────────────────────────────────────────────────
# 3) Classifier dispatches on type, independent of message text
# ─────────────────────────────────────────────────────────────────────

def _fake_brief():
    """Build a minimal valid Brief for context-building tests."""
    from buildemup.domain.brief import Brief
    from buildemup.domain.plot import Plot, PlotOrientation
    from buildemup.domain.setbacks import Setbacks

    plot = Plot(
        width_m=12.0, depth_m=15.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
    )
    sb = Setbacks(front_m=1.5, rear_m=1.5, side_left_m=1.5, side_right_m=1.5)
    floor = FloorRequirement(
        floor_number=0,
        floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=2),),
    )
    return Brief(
        plot=plot,
        user_stated_setbacks=sb,
        nbc_compliant_setbacks=sb,
        floors=(floor,),
        budget_range=BudgetRange(min_lakhs=20, max_lakhs=50),
    )


def test_classify_budget_dispatches_by_type_even_with_unmatching_text():
    """A BudgetValidationError with totally unrelated wording must still
    classify as CLS_BUDGET via type dispatch."""
    brief = _fake_brief()
    change = BriefChange(
        field_path="budget.max_lakhs",
        operation="SET",
        new_value=10,
        description="reduce budget",
    )
    err = BudgetValidationError("totally unrelated wording about pancakes")
    cls, _ = _classify_error(err, brief, change)
    assert cls == CLS_BUDGET


def test_classify_room_size_dispatches_by_type():
    brief = _fake_brief()
    change = BriefChange(
        field_path="floors.0.rooms.bedroom_master.min_size_sqm",
        operation="SET",
        new_value=2.0,
        description="shrink bedroom",
    )
    err = RoomSizeBelowNbcMinError("wording without the magic substring")
    cls, _ = _classify_error(err, brief, change)
    assert cls == CLS_ROOM_AREA


def test_classify_bedroom_count_negative_dispatches_by_type():
    brief = _fake_brief()
    change = BriefChange(
        field_path="rooms.bedroom_master",
        operation="SET",
        new_value=-1,
        description="drop bedrooms",
    )
    err = RoomCountNegativeError("anything")
    cls, _ = _classify_error(err, brief, change)
    assert cls == CLS_BEDROOM


def test_classify_floor_count_dispatches_by_type():
    brief = _fake_brief()
    change = BriefChange(
        field_path="floors", operation="SET", new_value=(),
        description="drop all floors",
    )
    err = FloorCountTooLowError("wording without the magic substring")
    cls, _ = _classify_error(err, brief, change)
    assert cls == CLS_FLOOR_COUNT


# ─────────────────────────────────────────────────────────────────────
# 4) Substring fallback still works for plain ValueError
# ─────────────────────────────────────────────────────────────────────

def test_legacy_substring_fallback_still_classifies_plain_value_error():
    """A plain ValueError with the legacy wording must still classify
    correctly via the substring path."""
    brief = _fake_brief()
    change = BriefChange(
        field_path="floors", operation="SET", new_value=(),
        description="drop all floors",
    )
    err = ValueError("Brief requires at least one floor (ground floor).")
    cls, _ = _classify_error(err, brief, change)
    assert cls == CLS_FLOOR_COUNT
