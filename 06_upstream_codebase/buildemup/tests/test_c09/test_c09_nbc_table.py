"""C9 NBC-table KB lookup tests.

Per C9 SPEC v0.7 LOCKED § 4.1, § 4.7 (Inv 3,4,5), § 7.
"""
from __future__ import annotations

import pytest

from buildemup.components.c09 import nbc_table
from buildemup.components.c09.schema import (
    BathroomSubtype,
    DwellingSizeTier,
    NBCSourceConfidence,
    RegulatoryMinimum,
    RoomCategory,
)


# ---------------------------------------------------------------------------
# SMALL tier
# ---------------------------------------------------------------------------


def test_small_master_bedroom():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL, category=RoomCategory.BEDROOM, is_master=True,
    )
    # SMALL master bedroom uses Clause 12.2.1 single-room dwelling: 9.5 / 2.4 / 2.75
    assert rm.area_m2 == pytest.approx(9.5)
    assert rm.width_m == pytest.approx(2.4)
    assert rm.height_m == pytest.approx(2.75)
    assert "12.2.1" in rm.nbc_clause


def test_small_typical_bedroom():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL, category=RoomCategory.BEDROOM, is_master=False,
    )
    # SMALL typical (smaller-of-2) — 12.2.2: 7.5 / 2.1 / 2.75
    assert rm.area_m2 == pytest.approx(7.5)
    assert rm.width_m == pytest.approx(2.1)
    assert "12.2.2" in rm.nbc_clause


def test_small_bathroom_combined():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL,
        category=RoomCategory.BATHROOM, is_master=False,
        bathroom_subtype=BathroomSubtype.COMBINED,
    )
    assert rm.area_m2 == pytest.approx(1.8)
    assert rm.width_m == pytest.approx(1.0)
    assert rm.height_m == pytest.approx(2.1)


def test_small_bathroom_bath_only():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL,
        category=RoomCategory.BATHROOM,
        bathroom_subtype=BathroomSubtype.BATH_ONLY,
    )
    assert rm.area_m2 == pytest.approx(1.2)


def test_small_bathroom_wc_only():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL,
        category=RoomCategory.BATHROOM,
        bathroom_subtype=BathroomSubtype.WC_ONLY,
    )
    assert rm.area_m2 == pytest.approx(1.0)
    assert rm.width_m == pytest.approx(0.9)


def test_small_kitchen():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL, category=RoomCategory.KITCHEN,
    )
    assert rm.area_m2 == pytest.approx(3.3)
    assert rm.width_m == pytest.approx(1.8)


def test_small_living():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL, category=RoomCategory.LIVING,
    )
    assert rm.area_m2 == pytest.approx(9.5)


def test_small_pooja_zero_area():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL, category=RoomCategory.POOJA,
    )
    assert rm.area_m2 == 0.0
    assert rm.width_m == 0.0


def test_small_utility_unverified_confidence():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL, category=RoomCategory.UTILITY,
    )
    assert rm.area_m2 == pytest.approx(3.2)
    assert rm.source_confidence == NBCSourceConfidence.SECONDARY_UNVERIFIED


# ---------------------------------------------------------------------------
# LARGE tier
# ---------------------------------------------------------------------------


def test_large_bedroom_master_and_typical_same():
    """LARGE tier: typical and master both use 12.1.1 (9.5 / 2.4 / 2.75)."""
    master = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.LARGE, category=RoomCategory.BEDROOM, is_master=True,
    )
    typical = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.LARGE, category=RoomCategory.BEDROOM, is_master=False,
    )
    assert master.area_m2 == typical.area_m2 == pytest.approx(9.5)


def test_large_kitchen_bigger_than_small():
    small = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.SMALL, category=RoomCategory.KITCHEN)
    large = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.LARGE, category=RoomCategory.KITCHEN)
    assert large.area_m2 > small.area_m2  # 4.5 > 3.3


def test_large_bathroom_combined_is_2_8():
    rm = nbc_table.lookup_nbc_minimum(
        tier=DwellingSizeTier.LARGE,
        category=RoomCategory.BATHROOM,
        bathroom_subtype=BathroomSubtype.COMBINED,
    )
    assert rm.area_m2 == pytest.approx(2.8)
    assert rm.width_m == pytest.approx(1.2)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_bathroom_without_subtype_raises():
    with pytest.raises(ValueError, match="BATHROOM requires"):
        nbc_table.lookup_nbc_minimum(
            tier=DwellingSizeTier.LARGE, category=RoomCategory.BATHROOM,
        )


def test_non_bathroom_with_subtype_raises():
    with pytest.raises(ValueError, match="non-BATHROOM"):
        nbc_table.lookup_nbc_minimum(
            tier=DwellingSizeTier.LARGE, category=RoomCategory.BEDROOM,
            bathroom_subtype=BathroomSubtype.COMBINED,
        )


def test_other_category_raises_keyerror():
    with pytest.raises(KeyError, match="OTHER"):
        nbc_table.lookup_nbc_minimum(
            tier=DwellingSizeTier.LARGE, category=RoomCategory.OTHER,
        )


def test_bad_tier_type_raises_typeerror():
    with pytest.raises(TypeError):
        nbc_table.lookup_nbc_minimum(
            tier="large", category=RoomCategory.BEDROOM)


def test_bad_category_type_raises_typeerror():
    with pytest.raises(TypeError):
        nbc_table.lookup_nbc_minimum(
            tier=DwellingSizeTier.LARGE, category="bedroom")


# ---------------------------------------------------------------------------
# KB integrity / metadata
# ---------------------------------------------------------------------------


def test_kb_version_is_set():
    assert "NBC" in nbc_table.KB_VERSION
    assert isinstance(nbc_table.KB_VERSION, str)


def test_all_rows_returns_regulatory_minimums():
    rows = nbc_table.all_rows()
    assert len(rows) > 0
    for r in rows:
        assert isinstance(r, RegulatoryMinimum)


def test_at_least_one_unverified_row_exists():
    """Storeroom (UTILITY) row is the documented SECONDARY_UNVERIFIED row."""
    rows = nbc_table.all_rows()
    unverified = [r for r in rows if r.source_confidence == NBCSourceConfidence.SECONDARY_UNVERIFIED]
    assert len(unverified) >= 1
