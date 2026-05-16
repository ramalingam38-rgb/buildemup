"""
BuildemUp† — C4 climate zone lookup + city validation utilities.

Per spec § 4.5 + v0.7 § 14.1.

Hosts:
  - normalize_city() — canonical lowercase/strip helper
  - validate_city()  — normalize + verify membership in CITY_GEOGRAPHY
  - lookup_climate_zone(city) -> ClimateZone
  - lookup_latitude(city)     -> float

v0.7 (walks #1, #4): the city-validation pattern — `if city not in
CITY_GEOGRAPHY: raise ValueError(...)` — was duplicated across 3 sites
in v0.6 (plot_analysis.py:178, climate_zone:lookup_climate_zone,
climate_zone:lookup_latitude). v0.7 centralizes it as `validate_city()`
and refactors all 3 call sites to use it.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c04.schema import ClimateZone
from buildemup.kb.city_geography import CITY_GEOGRAPHY


def normalize_city(city: str) -> str:
    """Canonical city normalization. Single source of truth.

    Returns a stripped, lowercase city name. Used at all C4 read sites
    (defense in depth — Plot.__post_init__ already does this for the
    Plot.city field, but the helper makes the contract explicit and
    available to call sites that may receive non-Plot inputs).

    Raises:
        TypeError: if city is not a str.
    """
    if not isinstance(city, str):
        raise TypeError(f"city must be str; got {type(city).__name__}")
    return city.strip().lower()


def validate_city(city: str) -> str:
    """Normalize city and verify membership in CITY_GEOGRAPHY.

    Returns the normalized city name. Single source of truth for the
    city-validation pattern that v0.6 repeated across 3 sites
    (plot_analysis.py, climate_zone:lookup_climate_zone,
    climate_zone:lookup_latitude).

    Raises:
        TypeError: if city is not a str (propagated from normalize_city).
        ValueError: if the normalized name is not a supported city.
    """
    normalized = normalize_city(city)
    if normalized not in CITY_GEOGRAPHY:
        raise ValueError(
            f"city '{normalized}' missing from CITY_GEOGRAPHY; check "
            f"kb/city_geography.py against domain.plot.SUPPORTED_CITIES"
        )
    return normalized


def lookup_climate_zone(city: str) -> ClimateZone:
    """Look up climate zone for a city.

    v0.7 (walk #4): uses the centralized validate_city() helper rather
    than inlining the membership check. Behavior unchanged.
    """
    normalized = validate_city(city)
    return CITY_GEOGRAPHY[normalized].climate_zone


def lookup_latitude(city: str) -> float:
    """Look up latitude (degrees) for a city.

    v0.7 (walk #4): uses the centralized validate_city() helper rather
    than inlining the membership check. Behavior unchanged.
    """
    normalized = validate_city(city)
    return CITY_GEOGRAPHY[normalized].latitude_deg


__all__ = [
    "normalize_city",
    "validate_city",
    "lookup_climate_zone",
    "lookup_latitude",
]
