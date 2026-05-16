"""B-074 closure (S55): MEDIUM_ROCK is now a first-class kb.SoilClass.

Before this change, SoilType.MEDIUM_ROCK was approximated to
kb.SoilClass.SOFT_ROCK (660 kPa) with a provenance_note breadcrumb
naming B-074. After this change, kb.SoilClass.MEDIUM_ROCK exists with
IS 6403-aligned values (1000-1500 kPa range; typical 1250).
"""
from __future__ import annotations

import pytest

from buildemup.domain.plot import SoilType
from buildemup.kb.soil_classification import (
    SOIL_PROFILES as KB_SOIL_PROFILES,
    SoilClass,
)
from buildemup.kb.soil_city_defaults import (
    APPROXIMATION_NOTES_BY_SOIL_TYPE,
    BEARING_CAPACITY_BY_TYPE,
    KB_VERSION,
)


def test_kb_soil_class_has_medium_rock_entry():
    """kb.SoilClass.MEDIUM_ROCK now exists as a first-class enum value."""
    assert SoilClass.MEDIUM_ROCK.value == "medium_rock"


def test_kb_soil_profiles_has_medium_rock_with_is6403_range():
    """SOIL_PROFILES[MEDIUM_ROCK] uses the IS 6403 range 1000-1500 kPa
    typical 1250."""
    profile = KB_SOIL_PROFILES[SoilClass.MEDIUM_ROCK]
    assert profile.sbc_min_knm2 == 1000
    assert profile.sbc_max_knm2 == 1500
    assert profile.sbc_typical_knm2 == 1250
    assert profile.requires_pile is False
    assert profile.requires_soil_test is True
    assert "IS 6403" in profile.notes


def test_c4_bearing_capacity_by_type_uses_new_value():
    """C4's per-SoilType kPa table reflects the new 1250 kPa value."""
    assert BEARING_CAPACITY_BY_TYPE[SoilType.MEDIUM_ROCK] == 1250.0


def test_c4_bearing_capacity_no_longer_660_for_medium_rock():
    """Regression guard: MEDIUM_ROCK must NOT fall back to the old
    SOFT_ROCK 660 kPa approximation."""
    assert BEARING_CAPACITY_BY_TYPE[SoilType.MEDIUM_ROCK] != 660.0


def test_approximation_table_no_longer_lists_medium_rock():
    """B-074 contract: MEDIUM_ROCK was the table's only entry; with the
    fix in place, the table should be empty (export hook preserved per
    v0.8 contract)."""
    assert SoilType.MEDIUM_ROCK not in APPROXIMATION_NOTES_BY_SOIL_TYPE
    assert APPROXIMATION_NOTES_BY_SOIL_TYPE == {}


def test_kb_version_bumped_to_v1_1():
    """B-074 closure bumps the C4 soil-defaults KB version."""
    assert KB_VERSION == "v1.1"


@pytest.mark.parametrize(
    "soil_type,expected_kpa",
    [
        (SoilType.HARD_ROCK, 1620.0),
        (SoilType.MEDIUM_ROCK, 1250.0),
        (SoilType.DENSE_SAND, 350.0),
        (SoilType.STIFF_CLAY, 250.0),
    ],
)
def test_bearing_capacity_table_intact_for_other_types(soil_type, expected_kpa):
    """Sibling soil types are unaffected by the B-074 change."""
    assert BEARING_CAPACITY_BY_TYPE[soil_type] == expected_kpa
