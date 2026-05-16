"""Tier-1 unit tests for C4 KB drift detection.

Per SPEC v0.5 LOCKED § 7.
"""
from __future__ import annotations

import pytest

from buildemup.kb.city_geography import CITY_GEOGRAPHY, verify_kb_consistency
from buildemup.domain.plot import SUPPORTED_CITIES


def test_kb_consistency_passes_for_supported_cities():
    """All 4 KBs cover every SUPPORTED_CITIES — no exception raised."""
    verify_kb_consistency()  # raises RuntimeError if drift


def test_verify_kb_consistency_callable_explicitly():
    """The function is callable as a free function (not just at module init)."""
    # We call it twice — must be idempotent.
    verify_kb_consistency()
    verify_kb_consistency()


def test_kb_drift_detected_when_supported_city_missing(monkeypatch):
    """Removing a city from one KB makes verify_kb_consistency raise."""
    from buildemup.kb import wind_load

    # Monkeypatch BASIC_WIND_SPEED_MS to drop "chennai".
    original = wind_load.BASIC_WIND_SPEED_MS
    pruned = {k: v for k, v in original.items() if k != "chennai"}
    monkeypatch.setattr(wind_load, "BASIC_WIND_SPEED_MS", pruned)

    with pytest.raises(RuntimeError, match=r"KB drift.*wind_load.*chennai"):
        verify_kb_consistency()


# ─── v0.6 § 14.4: KB sanity-range drift checks (walk #6) ─────────────────

def test_kb_drift_detected_for_out_of_range_wind_speed(monkeypatch):
    """Wind speed outside [30, 70] m/s (per IS 875 Part 3) raises RuntimeError."""
    from buildemup.kb import wind_load
    rigged = dict(wind_load.BASIC_WIND_SPEED_MS)
    rigged["chennai"] = 999.0   # impossible
    monkeypatch.setattr(wind_load, "BASIC_WIND_SPEED_MS", rigged)

    with pytest.raises(RuntimeError, match=r"wind_load.*chennai.*999"):
        verify_kb_consistency()


def test_kb_drift_detected_for_out_of_range_latitude(monkeypatch):
    """Latitude outside India range [5, 40] raises RuntimeError."""
    from buildemup.kb import city_geography
    from buildemup.kb.city_geography import CityGeography
    from buildemup.components.c04.schema import ClimateZone
    rigged = dict(city_geography.CITY_GEOGRAPHY)
    rigged["delhi"] = CityGeography(89.0, ClimateZone.COMPOSITE)   # impossible
    monkeypatch.setattr(city_geography, "CITY_GEOGRAPHY", rigged)

    with pytest.raises(RuntimeError, match=r"city_geography.*delhi.*89"):
        verify_kb_consistency()


def test_kb_drift_detected_for_out_of_range_kpa(monkeypatch):
    """Bearing capacity outside [10, 2000] kPa raises RuntimeError."""
    from buildemup.kb import soil_city_defaults
    from buildemup.kb.soil_city_defaults import SoilCityProfile
    from buildemup.domain.plot import SoilType
    rigged = dict(soil_city_defaults.SOIL_PROFILES)
    rigged["mumbai"] = SoilCityProfile(SoilType.FILLED_UP, 9999.0)   # impossible
    monkeypatch.setattr(soil_city_defaults, "SOIL_PROFILES", rigged)

    with pytest.raises(RuntimeError, match=r"soil_city_defaults.*mumbai.*9999"):
        verify_kb_consistency()


# ─── v0.8 § 14.1: KB key normalization enforcement (walk #5) ─────────────

def test_kb_drift_detected_for_non_normalized_key(monkeypatch):
    """v0.8: a non-normalized KB key (uppercase / whitespace) raises."""
    from buildemup.kb import wind_load
    rigged = dict(wind_load.BASIC_WIND_SPEED_MS)
    # Inject an uppercase key while preserving membership of the lowercase one
    rigged["Chennai"] = rigged["chennai"]
    monkeypatch.setattr(wind_load, "BASIC_WIND_SPEED_MS", rigged)

    with pytest.raises(RuntimeError, match=r"non-normalized.*Chennai"):
        verify_kb_consistency()


def test_kb_drift_detected_for_whitespace_in_key(monkeypatch):
    """Whitespace in a KB key also caught by normalization check."""
    from buildemup.kb import wind_load
    rigged = dict(wind_load.BASIC_WIND_SPEED_MS)
    rigged[" delhi"] = rigged["delhi"]
    monkeypatch.setattr(wind_load, "BASIC_WIND_SPEED_MS", rigged)

    with pytest.raises(RuntimeError, match=r"non-normalized"):
        verify_kb_consistency()


# ─── v1.0 § 14.2: PREVAILING_WIND direction type check (walk D4) ─────────

def test_kb_drift_detected_for_non_plotorientation_wind_direction(monkeypatch):
    """v1.0 walk D4: a non-PlotOrientation value in PREVAILING_WIND raises."""
    from buildemup.kb import wind_direction
    from buildemup.components.c04.schema import ConfidenceLevel, WindContext
    from buildemup.domain.envelope import PlotOrientation
    rigged = dict(wind_direction.PREVAILING_WIND)
    # Replace chennai entry with an invalid primary_direction (string instead of enum).
    rigged["chennai"] = WindContext(
        primary_direction="NE",                         # type: ignore[arg-type]
        monsoon_direction=PlotOrientation.SOUTHWEST,
        basic_speed_ms=50.0,
        confidence=ConfidenceLevel.MEDIUM,
    )
    monkeypatch.setattr(wind_direction, "PREVAILING_WIND", rigged)

    with pytest.raises(RuntimeError, match=r"chennai.*primary_direction.*must be PlotOrientation"):
        verify_kb_consistency()


def test_kb_drift_detected_for_non_plotorientation_monsoon_direction(monkeypatch):
    """v1.0 walk D4: monsoon_direction also type-checked."""
    from buildemup.kb import wind_direction
    from buildemup.components.c04.schema import ConfidenceLevel, WindContext
    from buildemup.domain.envelope import PlotOrientation
    rigged = dict(wind_direction.PREVAILING_WIND)
    rigged["delhi"] = WindContext(
        primary_direction=PlotOrientation.NORTHWEST,
        monsoon_direction=42,                            # type: ignore[arg-type]
        basic_speed_ms=47.0,
        confidence=ConfidenceLevel.MEDIUM,
    )
    monkeypatch.setattr(wind_direction, "PREVAILING_WIND", rigged)

    with pytest.raises(RuntimeError, match=r"delhi.*monsoon_direction.*must be PlotOrientation"):
        verify_kb_consistency()


# ─── v1.0 § 14.3: per-SoilType kPa range check (walk D5) ─────────────────

def test_kb_drift_detected_for_out_of_range_per_soil_type_kpa(monkeypatch):
    """v1.0 walk D5: BEARING_CAPACITY_BY_TYPE values outside [10, 2000] kPa raise.

    Parallel to the v0.6 SOIL_PROFILES range check (which covers city defaults);
    this covers the per-SoilType table that the user_input branch consumes.
    """
    from buildemup.kb import soil_city_defaults
    from buildemup.domain.plot import SoilType
    rigged = dict(soil_city_defaults.BEARING_CAPACITY_BY_TYPE)
    rigged[SoilType.HARD_ROCK] = 9999.0  # impossible
    monkeypatch.setattr(soil_city_defaults, "BEARING_CAPACITY_BY_TYPE", rigged)

    with pytest.raises(RuntimeError, match=r"BEARING_CAPACITY_BY_TYPE.*hard_rock.*9999"):
        verify_kb_consistency()


def test_kb_drift_detected_for_below_range_per_soil_type_kpa(monkeypatch):
    """Below-range kPa also caught."""
    from buildemup.kb import soil_city_defaults
    from buildemup.domain.plot import SoilType
    rigged = dict(soil_city_defaults.BEARING_CAPACITY_BY_TYPE)
    rigged[SoilType.SOFT_CLAY] = 5.0   # below 10 kPa floor
    monkeypatch.setattr(soil_city_defaults, "BEARING_CAPACITY_BY_TYPE", rigged)

    with pytest.raises(RuntimeError, match=r"BEARING_CAPACITY_BY_TYPE.*soft_clay.*5"):
        verify_kb_consistency()
