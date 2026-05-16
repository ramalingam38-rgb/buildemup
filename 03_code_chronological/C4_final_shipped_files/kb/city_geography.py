"""
BuildemUp† — City Geography (NEW v0.5).

Per-city latitude + climate zone tables. Used by C4's solar geometry
and climate zone lookup. Hosts verify_kb_consistency() which checks
that all 4 KBs (this one, wind_load, wind_direction, soil_city_defaults)
cover every supported city.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.components.c04.schema import ClimateZone


KB_VERSION = "v1.0"


@dataclass(frozen=True)
class CityGeography:
    """Per-city geography for solar + climate calculation."""
    latitude_deg: float
    climate_zone: ClimateZone


# 6 cities matching domain.plot.SUPPORTED_CITIES exactly.
#
# Source: NBC 2016 Part 8 Section 1, §§ 2.2.21-2.2.24 + 3.2.2;
# cross-verified with ECBC 2017 climate-zone-finder.
#
# Adding a new city requires updating domain.plot.SUPPORTED_CITIES AND
# all 4 KBs (this one + wind_load + wind_direction + soil_city_defaults)
# in the same change. verify_kb_consistency() will fail-fast otherwise.
CITY_GEOGRAPHY: dict[str, CityGeography] = {
    "chennai":   CityGeography(13.08, ClimateZone.WARM_HUMID),
    "mumbai":    CityGeography(19.08, ClimateZone.WARM_HUMID),
    "bangalore": CityGeography(12.97, ClimateZone.TEMPERATE),
    "pune":      CityGeography(18.52, ClimateZone.TEMPERATE),
    "delhi":     CityGeography(28.61, ClimateZone.COMPOSITE),
    "hyderabad": CityGeography(17.39, ClimateZone.COMPOSITE),
}


def verify_kb_consistency() -> None:
    """Cross-KB invariant check.

    Every supported city must be present in EVERY KB. KBs may carry
    extras (forward-compat) but cannot be missing any supported city.

    v0.6 (walk #6): also runs LOOSE value-quality sanity checks. These
    are defensive against copy-paste / unit errors at code-edit time,
    NOT design bounds:
      - IS 875 Part 3:    India basic wind = 33-55 m/s, cyclonic up to ~70.
                          Sanity range: [30, 70].
      - India geography:  latitudes 8°-37° N. Sanity range with margin: [5, 40].
      - IS 6403 / IS 1904: typical residential SBC range. Sanity: [10, 2000].

    v0.8 (walk #5): also enforces every KB key equals normalize_city(key)
    at module load. Catches whitespace / casing drift even if it would
    pass a same-format-on-both-sides presence check.

    v1.0 (walks D4, D5): also type-checks PREVAILING_WIND directions
    (PlotOrientation enum) and range-checks BEARING_CAPACITY_BY_TYPE
    (per-SoilType kPa, parallel to the city-default range check).

    Called from components/c04/__init__.py at module import (fail-fast)
    AND as an explicit Tier-1 test.

    Raises:
        RuntimeError: if any KB has a non-string or non-normalized key,
                      OR is missing a supported city, OR has a value
                      out of plausible range, OR has wind directions
                      that are not PlotOrientation enums, OR has per-
                      SoilType kPa values out of plausible range.

    All KB_VERSION imports are explicit so any KB lacking the constant
    causes ImportError at this call (not later, deeper in C4).
    """
    # Local imports — defer to call time so module import order is robust.
    from buildemup.domain.plot              import SUPPORTED_CITIES
    from buildemup.kb.wind_load             import (
        BASIC_WIND_SPEED_MS, KB_VERSION as WL_VER,  # noqa: F401
    )
    from buildemup.kb.soil_city_defaults    import (
        SOIL_PROFILES, KB_VERSION as SC_VER,        # noqa: F401
    )
    from buildemup.kb.wind_direction        import (
        PREVAILING_WIND, KB_VERSION as WD_VER,      # noqa: F401
    )

    required = set(SUPPORTED_CITIES)

    # NEW v0.8 (walk #5): every KB key must be already-normalized.
    # Catches whitespace / casing errors at module load even if a
    # mismatched-but-internally-consistent format would slip past the
    # presence check (e.g., if SUPPORTED_CITIES itself ever drifts).
    # Local import to avoid a circular import: climate_zone imports from
    # this module, so we defer the import to call time.
    from buildemup.components.c04.climate_zone import normalize_city
    for kb_name, kb_keys in (
        ("city_geography",      list(CITY_GEOGRAPHY.keys())),
        ("wind_load",           list(BASIC_WIND_SPEED_MS.keys())),
        ("soil_city_defaults",  list(SOIL_PROFILES.keys())),
        ("wind_direction",      list(PREVAILING_WIND.keys())),
    ):
        for key in kb_keys:
            if not isinstance(key, str):
                raise RuntimeError(
                    f"KB drift: kb/{kb_name} has non-string city key "
                    f"{key!r} (type {type(key).__name__})."
                )
            normalized = normalize_city(key)
            if key != normalized:
                raise RuntimeError(
                    f"KB drift: kb/{kb_name} has non-normalized city key "
                    f"{key!r} (normalize_city → {normalized!r}). "
                    f"All KB keys must be lowercase, stripped."
                )

    # Coverage check: every supported city must be in every KB.
    for kb_name, kb_keys in (
        ("city_geography",      set(CITY_GEOGRAPHY.keys())),
        ("wind_load",           set(BASIC_WIND_SPEED_MS.keys())),
        ("soil_city_defaults",  set(SOIL_PROFILES.keys())),
        ("wind_direction",      set(PREVAILING_WIND.keys())),
    ):
        missing = required - kb_keys
        if missing:
            raise RuntimeError(
                f"KB drift: kb/{kb_name} missing required supported cities: "
                f"{sorted(missing)}. All 4 KBs must contain every city in "
                f"domain.plot.SUPPORTED_CITIES."
            )

    # NEW v0.6: value-quality sanity ranges (loose bounds for fail-fast).
    # Wind speed [30, 70] m/s per IS 875 Part 3 (India basic 33-55, cyclonic ~70).
    for city, speed in BASIC_WIND_SPEED_MS.items():
        if not (30.0 <= speed <= 70.0):
            raise RuntimeError(
                f"KB drift: kb/wind_load wind speed for '{city}' = {speed} m/s "
                f"out of plausible range [30, 70]. Per IS 875 Part 3 India "
                f"is 33-55 m/s with cyclonic peaks ~70."
            )
    # Latitude [5, 40] degrees (India is 8-37 N with margin).
    for city, geo in CITY_GEOGRAPHY.items():
        if not (5.0 <= geo.latitude_deg <= 40.0):
            raise RuntimeError(
                f"KB drift: kb/city_geography '{city}' latitude = "
                f"{geo.latitude_deg}° out of India range [5, 40]."
            )
    # Bearing capacity [10, 2000] kPa per IS 6403 / IS 1904 typical residential.
    for city, prof in SOIL_PROFILES.items():
        if not (10.0 <= prof.typical_bearing_capacity_kpa <= 2000.0):
            raise RuntimeError(
                f"KB drift: kb/soil_city_defaults '{city}' kPa = "
                f"{prof.typical_bearing_capacity_kpa} out of plausible "
                f"residential range [10, 2000]."
            )

    # NEW v1.0 (walk D5): per-SoilType kPa range check on BEARING_CAPACITY_BY_TYPE.
    # Parallel to the SOIL_PROFILES loop above. Catches accidental modification
    # of the per-soil-type table that the user_input branch of estimate_soil()
    # depends on. Same [10, 2000] kPa residential band per IS 6403 / IS 1904.
    from buildemup.kb.soil_city_defaults import BEARING_CAPACITY_BY_TYPE
    for soil_type, kpa in BEARING_CAPACITY_BY_TYPE.items():
        if not (10.0 <= kpa <= 2000.0):
            raise RuntimeError(
                f"KB drift: kb/soil_city_defaults BEARING_CAPACITY_BY_TYPE"
                f"[{soil_type.value}] = {kpa} kPa out of plausible "
                f"residential range [10, 2000]."
            )

    # NEW v1.0 (walk D4): PREVAILING_WIND direction type-check. Python doesn't
    # enforce dataclass type annotations at runtime; this catches KB corruption
    # that bypasses the WindContext type hints (e.g. someone setting
    # primary_direction="NE" string instead of PlotOrientation.NORTHEAST enum).
    from buildemup.domain.envelope import PlotOrientation as _PO
    for city, wc in PREVAILING_WIND.items():
        for field_name in ("primary_direction", "monsoon_direction"):
            value = getattr(wc, field_name)
            if not isinstance(value, _PO):
                raise RuntimeError(
                    f"KB drift: kb/wind_direction PREVAILING_WIND[{city!r}]."
                    f"{field_name} = {value!r} (type {type(value).__name__}); "
                    f"must be PlotOrientation enum."
                )


def kb_versions() -> dict[str, str]:
    """Snapshot of all 4 KB_VERSION constants used by C4.

    Used by PlotAnalysisProvenance.source_versions at construction time.
    """
    from buildemup.kb.wind_load          import KB_VERSION as WL_VER
    from buildemup.kb.soil_city_defaults import KB_VERSION as SC_VER
    from buildemup.kb.wind_direction     import KB_VERSION as WD_VER
    return {
        "city_geography":     KB_VERSION,
        "wind_load":          WL_VER,
        "soil_city_defaults": SC_VER,
        "wind_direction":     WD_VER,
    }


__all__ = [
    "KB_VERSION",
    "CityGeography",
    "CITY_GEOGRAPHY",
    "verify_kb_consistency",
    "kb_versions",
]
