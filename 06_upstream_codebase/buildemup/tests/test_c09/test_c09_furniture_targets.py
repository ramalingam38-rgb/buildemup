"""C9 furniture-floor + targets KB lookup tests.

Per C9 SPEC v0.7 LOCKED § 4.2 / § 4.3 / § 4.4 / § 14.34.
"""
from __future__ import annotations

import pytest

from buildemup.components.c09 import furniture_floor as ff_mod
from buildemup.components.c09 import targets_kb as tg_mod
from buildemup.components.c09.schema import (
    BathroomSubtype,
    PER_CATEGORY_MAX_MULTIPLIER,
    RoomCategory,
)


# ---------------------------------------------------------------------------
# Furniture floor
# ---------------------------------------------------------------------------


def test_furniture_master_bedroom():
    ff = ff_mod.lookup_furniture_floor(
        category=RoomCategory.BEDROOM, is_master=True,
    )
    assert ff.area_m2 == pytest.approx(13.0)
    assert ff.min_width_m == pytest.approx(3.3)


def test_furniture_typical_bedroom():
    ff = ff_mod.lookup_furniture_floor(
        category=RoomCategory.BEDROOM, is_master=False,
    )
    assert ff.area_m2 == pytest.approx(9.3)
    assert ff.min_width_m == pytest.approx(3.0)


def test_furniture_living_room():
    ff = ff_mod.lookup_furniture_floor(category=RoomCategory.LIVING)
    assert ff.area_m2 == pytest.approx(16.7)
    assert ff.min_width_m == pytest.approx(3.6)


def test_furniture_kitchen():
    ff = ff_mod.lookup_furniture_floor(category=RoomCategory.KITCHEN)
    assert ff.area_m2 == pytest.approx(7.9)


def test_furniture_master_bathroom_combined():
    ff = ff_mod.lookup_furniture_floor(
        category=RoomCategory.BATHROOM, is_master=True,
        bathroom_subtype=BathroomSubtype.COMBINED,
    )
    assert ff.area_m2 == pytest.approx(4.0)
    assert ff.min_width_m == pytest.approx(1.5)


def test_furniture_typical_bathroom_combined():
    ff = ff_mod.lookup_furniture_floor(
        category=RoomCategory.BATHROOM, is_master=False,
        bathroom_subtype=BathroomSubtype.COMBINED,
    )
    assert ff.area_m2 == pytest.approx(2.8)


def test_furniture_bath_only_smaller_than_combined():
    combined = ff_mod.lookup_furniture_floor(
        category=RoomCategory.BATHROOM,
        bathroom_subtype=BathroomSubtype.COMBINED,
    )
    bath_only = ff_mod.lookup_furniture_floor(
        category=RoomCategory.BATHROOM,
        bathroom_subtype=BathroomSubtype.BATH_ONLY,
    )
    assert bath_only.area_m2 < combined.area_m2


def test_furniture_other_category_falls_through():
    """OTHER pooled v1 default per § 14.34."""
    ff = ff_mod.lookup_furniture_floor(category=RoomCategory.OTHER)
    assert ff.area_m2 > 0


def test_furniture_bathroom_without_subtype_raises():
    with pytest.raises(ValueError):
        ff_mod.lookup_furniture_floor(category=RoomCategory.BATHROOM)


def test_furniture_non_bathroom_with_subtype_raises():
    with pytest.raises(ValueError):
        ff_mod.lookup_furniture_floor(
            category=RoomCategory.LIVING,
            bathroom_subtype=BathroomSubtype.COMBINED,
        )


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


def test_target_master_bedroom():
    assert tg_mod.lookup_target_m2(
        category=RoomCategory.BEDROOM, is_master=True
    ) == pytest.approx(14.9)


def test_target_typical_bedroom():
    assert tg_mod.lookup_target_m2(
        category=RoomCategory.BEDROOM, is_master=False
    ) == pytest.approx(10.2)


def test_target_living():
    assert tg_mod.lookup_target_m2(category=RoomCategory.LIVING) == pytest.approx(18.6)


def test_target_master_bathroom_bigger_than_typical():
    master = tg_mod.lookup_target_m2(
        category=RoomCategory.BATHROOM, is_master=True)
    typical = tg_mod.lookup_target_m2(
        category=RoomCategory.BATHROOM, is_master=False)
    assert master > typical  # 4.2 > 3.3


def test_target_other_falls_through():
    assert tg_mod.lookup_target_m2(category=RoomCategory.OTHER) > 0


def test_target_living_master_falls_back_to_typical():
    """LIVING is never master; lookup with is_master=True should fall back."""
    typical = tg_mod.lookup_target_m2(category=RoomCategory.LIVING, is_master=False)
    master = tg_mod.lookup_target_m2(category=RoomCategory.LIVING, is_master=True)
    assert master == typical


# ---------------------------------------------------------------------------
# Max sizes (target × multiplier)
# ---------------------------------------------------------------------------


def test_max_master_bedroom():
    """Master bedroom: target 14.9 × 1.6 = 23.84."""
    assert tg_mod.lookup_max_m2(
        category=RoomCategory.BEDROOM, is_master=True
    ) == pytest.approx(23.84)


def test_max_living_uses_2_5_multiplier():
    """LIVING gets 2.5× per § 4.4 (more generous waste threshold)."""
    target = tg_mod.lookup_target_m2(category=RoomCategory.LIVING)
    max_m2 = tg_mod.lookup_max_m2(category=RoomCategory.LIVING)
    assert max_m2 == pytest.approx(target * 2.5)


def test_max_other_categories_use_1_6_multiplier():
    for cat in [RoomCategory.BEDROOM, RoomCategory.KITCHEN,
                RoomCategory.BATHROOM, RoomCategory.POOJA, RoomCategory.UTILITY]:
        # check the multiplier table
        assert PER_CATEGORY_MAX_MULTIPLIER[cat] == pytest.approx(1.6)


def test_max_always_geq_target():
    """Max-multiplier is always >= 1.0 so max >= target."""
    for cat in RoomCategory:
        if cat == RoomCategory.OTHER:
            target = tg_mod.lookup_target_m2(category=cat)
            max_m2 = tg_mod.lookup_max_m2(category=cat)
            assert max_m2 >= target


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_furniture_kb_version_is_set():
    assert isinstance(ff_mod.KB_VERSION, str) and ff_mod.KB_VERSION


def test_targets_kb_version_is_set():
    assert isinstance(tg_mod.KB_VERSION, str) and tg_mod.KB_VERSION
