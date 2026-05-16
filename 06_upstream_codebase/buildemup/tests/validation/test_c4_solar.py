"""Tier-1 unit tests for C4 solar geometry (Cooper 1969).

Per SPEC v0.5 LOCKED § 7. 1° tolerance per Cooper-1969 published
accuracy of ~0.5–1° at solstices for closed-form declination.

Golden dataset: 6 cities × 2 solstices = 12 reference values.
"""
from __future__ import annotations

import pytest

from buildemup.components.c04 import derive
from buildemup.components.c04.sun_path import compute_sun_path
from buildemup.kb.city_geography import CITY_GEOGRAPHY
from buildemup.tests.validation._c4_fixtures import (
    chennai_30x40,
    delhi_60x90,
    make_brief,
)


# ─── 12-value golden dataset (computed via 90 - |lat - decl|) ──────────────
# decl_summer = +23.45°, decl_winter = -23.45° (Cooper 1969 at solstice DOY).
# Tolerance: 1° per published Cooper-1969 accuracy.
_TOLERANCE_DEG = 1.0

GOLDEN_NOON_ALTITUDES = {
    # city: (summer_solstice_alt, winter_solstice_alt)
    "chennai":   (79.63, 53.47),
    "mumbai":    (85.63, 47.47),
    "bangalore": (79.52, 53.58),
    "pune":      (85.07, 48.03),
    "delhi":     (84.84, 37.94),
    "hyderabad": (83.94, 49.16),
}


def test_solar_chennai_summer_noon_alt_within_1deg_of_known():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    expected_summer, _ = GOLDEN_NOON_ALTITUDES["chennai"]
    assert pa.sun_path.summer_solstice_noon_alt == pytest.approx(
        expected_summer, abs=_TOLERANCE_DEG
    )


def test_solar_delhi_winter_solstice_alt_within_1deg_of_known():
    pa = derive(make_brief(delhi_60x90()), now=1.0)
    _, expected_winter = GOLDEN_NOON_ALTITUDES["delhi"]
    assert pa.sun_path.winter_solstice_noon_alt == pytest.approx(
        expected_winter, abs=_TOLERANCE_DEG
    )


def test_solar_golden_dataset_6_cities_2_solstices_within_1deg():
    """Full 12-value golden dataset — every supported city × both solstices."""
    failures: list[str] = []
    for city, (expected_summer, expected_winter) in GOLDEN_NOON_ALTITUDES.items():
        sun_path = compute_sun_path(CITY_GEOGRAPHY[city].latitude_deg)
        if abs(sun_path.summer_solstice_noon_alt - expected_summer) > _TOLERANCE_DEG:
            failures.append(
                f"{city} summer: got {sun_path.summer_solstice_noon_alt:.2f}°, "
                f"expected {expected_summer:.2f}°"
            )
        if abs(sun_path.winter_solstice_noon_alt - expected_winter) > _TOLERANCE_DEG:
            failures.append(
                f"{city} winter: got {sun_path.winter_solstice_noon_alt:.2f}°, "
                f"expected {expected_winter:.2f}°"
            )
    assert not failures, "Solar golden-dataset mismatches:\n" + "\n".join(failures)
