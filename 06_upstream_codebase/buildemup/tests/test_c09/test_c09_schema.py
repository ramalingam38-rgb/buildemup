"""C9 schema invariant tests.

Per C9 SPEC v0.7 LOCKED § 7. Covers Inv 6, 6b, 7, 8, 11, 13, 14, 15, 16
at the dataclass-construction level (defensive checks duplicated by validator
where the whole-table view matters).
"""
from __future__ import annotations

import pytest

from buildemup.components.c09 import (
    BathroomSubtype,
    NBCSourceConfidence,
    RegulatoryMinimum,
    RoomCategory,
    RoomSizeRequirement,
    RoomSizeTable,
    DwellingSizeTier,
)
from buildemup.tests._c9_fixtures import make_regulatory, make_room


# ---------------------------------------------------------------------------
# RegulatoryMinimum
# ---------------------------------------------------------------------------


def test_regulatory_minimum_negative_area_raises():
    with pytest.raises(ValueError):
        RegulatoryMinimum(area_m2=-1.0, width_m=2.4, height_m=2.75,
                          nbc_clause="x", source_confidence=NBCSourceConfidence.SECONDARY_CONSENSUS)


def test_regulatory_minimum_negative_width_raises():
    with pytest.raises(ValueError):
        RegulatoryMinimum(area_m2=9.5, width_m=-0.1, height_m=2.75,
                          nbc_clause="x", source_confidence=NBCSourceConfidence.SECONDARY_CONSENSUS)


def test_regulatory_minimum_negative_height_raises():
    with pytest.raises(ValueError):
        RegulatoryMinimum(area_m2=9.5, width_m=2.4, height_m=-0.1,
                          nbc_clause="x", source_confidence=NBCSourceConfidence.SECONDARY_CONSENSUS)


def test_regulatory_minimum_zero_values_ok():
    """POOJA / UTILITY have zero NBC requirements in v1."""
    rm = RegulatoryMinimum(area_m2=0.0, width_m=0.0, height_m=2.1,
                           nbc_clause="(no NBC floor)",
                           source_confidence=NBCSourceConfidence.SECONDARY_CONSENSUS)
    assert rm.area_m2 == 0.0


def test_regulatory_minimum_bad_confidence_type_raises():
    with pytest.raises(TypeError):
        RegulatoryMinimum(area_m2=9.5, width_m=2.4, height_m=2.75,
                          nbc_clause="x", source_confidence="verified")


# ---------------------------------------------------------------------------
# RoomSizeRequirement — Inv 6/6b/7/8/15
# ---------------------------------------------------------------------------


def test_inv_6_liveability_area_below_regulatory_raises():
    """Inv 6: liveability_min_area_m2 >= regulatory_minimum.area_m2."""
    reg = make_regulatory(area_m2=10.0)
    with pytest.raises(ValueError, match="liveability_min_area_m2"):
        make_room(regulatory=reg, liveability_min_area_m2=8.0)


def test_inv_6b_liveability_width_below_regulatory_raises():
    """Inv 6b: liveability_min_width_m >= regulatory_minimum.width_m."""
    reg = make_regulatory(width_m=2.4)
    with pytest.raises(ValueError, match="liveability_min_width_m"):
        make_room(regulatory=reg, liveability_min_width_m=2.1)


def test_inv_7_target_below_liveability_raises():
    """Inv 7: target_m2 >= liveability_min_area_m2."""
    with pytest.raises(ValueError, match="target_m2"):
        make_room(liveability_min_area_m2=14.0, target_m2=13.0)


def test_inv_8_max_below_target_raises():
    """Inv 8: max_m2 >= target_m2."""
    with pytest.raises(ValueError, match="max_m2"):
        make_room(target_m2=14.9, max_m2=13.0)


def test_inv_15_bathroom_subtype_required_for_bathroom():
    with pytest.raises(ValueError, match="BATHROOM"):
        make_room(category=RoomCategory.BATHROOM, room_id="BATHROOM_1",
                  is_master=False, bathroom_subtype=None,
                  liveability_min_area_m2=2.8, liveability_min_width_m=1.2,
                  target_m2=3.3, max_m2=5.28,
                  regulatory=make_regulatory(area_m2=2.8, width_m=1.2, height_m=2.1))


def test_inv_15_bathroom_subtype_forbidden_for_non_bathroom():
    with pytest.raises(ValueError, match="non-BATHROOM"):
        make_room(category=RoomCategory.LIVING, room_id="LIVING_1",
                  is_master=False,
                  bathroom_subtype=BathroomSubtype.COMBINED,
                  liveability_min_area_m2=16.7, liveability_min_width_m=3.6,
                  target_m2=18.6, max_m2=46.5)


def test_is_master_only_on_bedroom_or_bathroom():
    """is_master is only valid for BEDROOM or BATHROOM (Inv 13/14 prep)."""
    with pytest.raises(ValueError, match="is_master"):
        make_room(category=RoomCategory.LIVING, room_id="LIVING_1",
                  is_master=True,
                  liveability_min_area_m2=16.7, liveability_min_width_m=3.6,
                  target_m2=18.6, max_m2=46.5)


def test_other_subtype_only_on_other_category():
    with pytest.raises(ValueError, match="other_subtype"):
        make_room(category=RoomCategory.BEDROOM, other_subtype="study")


def test_priority_must_be_positive():
    with pytest.raises(ValueError, match="priority"):
        make_room(priority=0)


def test_room_id_must_be_non_empty():
    with pytest.raises(ValueError, match="room_id"):
        make_room(room_id="")


def test_master_bedroom_construction_succeeds():
    """Sanity: default fixture builds a valid master bedroom."""
    r = make_room()
    assert r.is_master is True
    assert r.category == RoomCategory.BEDROOM
    assert r.priority == 1


# ---------------------------------------------------------------------------
# RoomSizeTable — Inv 11, 16
# ---------------------------------------------------------------------------


def test_inv_11_duplicate_room_ids_in_table_raise():
    r1 = make_room(room_id="BEDROOM_1", priority=1)
    r2 = make_room(room_id="BEDROOM_1", priority=2)
    with pytest.raises(ValueError, match="duplicate room_id"):
        RoomSizeTable(
            rooms=(r1, r2),
            buildable_envelope_minus_corridor_m2=100.0,
            dwelling_size_tier=DwellingSizeTier.LARGE,
            total_liveability_min_area_m2=26.0,
            total_target_m2=29.8,
            surplus_for_distribution_m2=70.2,
            unassigned_area_m2=70.2,
            packing_efficiency_used=0.75,
            floor_label="ground",
        )


def test_inv_16_negative_unassigned_raises():
    r = make_room()
    with pytest.raises(ValueError, match="unassigned"):
        RoomSizeTable(
            rooms=(r,),
            buildable_envelope_minus_corridor_m2=100.0,
            dwelling_size_tier=DwellingSizeTier.LARGE,
            total_liveability_min_area_m2=13.0,
            total_target_m2=14.9,
            surplus_for_distribution_m2=87.0,
            unassigned_area_m2=-5.0,
            packing_efficiency_used=0.75,
            floor_label="ground",
        )


def test_table_must_have_at_least_one_room():
    with pytest.raises(ValueError, match="non-empty"):
        RoomSizeTable(
            rooms=(),
            buildable_envelope_minus_corridor_m2=100.0,
            dwelling_size_tier=DwellingSizeTier.LARGE,
            total_liveability_min_area_m2=0.0,
            total_target_m2=0.0,
            surplus_for_distribution_m2=100.0,
            unassigned_area_m2=100.0,
            packing_efficiency_used=0.75,
            floor_label="ground",
        )


def test_negative_envelope_minus_corridor_raises():
    r = make_room()
    with pytest.raises(ValueError, match="buildable_envelope_minus_corridor_m2"):
        RoomSizeTable(
            rooms=(r,),
            buildable_envelope_minus_corridor_m2=-1.0,
            dwelling_size_tier=DwellingSizeTier.LARGE,
            total_liveability_min_area_m2=13.0,
            total_target_m2=14.9,
            surplus_for_distribution_m2=0.0,
            unassigned_area_m2=0.0,
            packing_efficiency_used=0.75,
            floor_label="ground",
        )
