"""
BuildemUp† — C4 sun-path geometry (Cooper 1969, closed-form).

# ───────────────────── DEFERRED BACKLOG (REVIEW MARKER) ─────────────────────
# Critique reviewers: filed in spec § 16. Please do NOT re-flag.
# (Strippable review aid.)
#
#   B-067  Per-month sun-path declination (current model uses solstice-only
#          envelope, ~0.5-1° accuracy via Cooper 1969). Required for hourly
#          shading studies, daylight simulation, solar-panel performance
#          modeling. Out of v1 scope (C5/C6 use the envelope, not per-hour).
# ─────────────────────────────────────────────────────────────────────────────

Per spec § 4.4.3. ~0.5–1° accuracy, sufficient for solstice-envelope
room-orientation hints (C5/C6 use envelope, not shading studies). Per-month
declination = B-067.

Formulae:
  declination = 23.45° × sin(360° × (284 + N) / 365°)         (Cooper 1969)
  solar_altitude_at_noon = 90° − |latitude − declination|     (zenith for
                                                              θ = lat − decl)

Sunrise/sunset hour angle (sun on horizon, altitude = 0):
  cos(h) = − tan(lat) × tan(decl)

Sunrise/sunset compass azimuth (measured from N, clockwise):
  cos(A) = sin(decl) / cos(lat)                               (at altitude 0)
  A_sunrise ∈ [0°, 180°];  A_sunset = 360° − A_sunrise

For India (latitudes 12.97°–28.61°) at solstices (decl = ±23.45°),
|tan(lat) × tan(decl)| ≤ 0.24, so sunrise/sunset is always defined.

LONGITUDE OMISSION (v0.6 walk #8 — DOCUMENTED):
  Longitude is mathematically absent from all formulae above. The
  solstice noon altitude depends only on |lat − decl|; the sunrise/
  sunset compass azimuth depends only on (lat, decl). Longitude only
  shifts the WALL-CLOCK time of solar noon (e.g., Chennai's solar
  noon is ~13 minutes earlier than Mumbai's), NOT its altitude or
  compass position. Since C5/C6 consume the angular envelope (altitude
  + azimuth), not local time, longitude omission is correct, not a gap.
  Hourly shading studies, daylight simulation, and solar panel
  performance modeling would all need full diurnal models — out of
  scope for v1; covered by adjacent backlog item B-067.

†= placeholder name marker.
"""
from __future__ import annotations

from math import acos, cos, degrees, fabs, radians, sin

from buildemup.components.c04.schema import SunPath


# Solstice day-of-year (per spec § 4.4.3)
SUMMER_SOLSTICE_DOY = 172   # June 21
WINTER_SOLSTICE_DOY = 355   # December 21


def declination_deg(day_of_year: int) -> float:
    """Cooper 1969 solar declination, in degrees."""
    return 23.45 * sin(radians(360.0 * (284 + day_of_year) / 365.0))


def solar_altitude_at_noon_deg(latitude_deg: float, declination_deg_: float) -> float:
    """Solar altitude at solar noon for a given lat/declination."""
    return 90.0 - fabs(latitude_deg - declination_deg_)


def sunrise_sunset_azimuth_deg(
    latitude_deg: float, declination_deg_: float
) -> tuple[float, float]:
    """Compass azimuth of sunrise and sunset, in degrees from N (clockwise).

    Returns (sunrise_azimuth, sunset_azimuth). Both in [0°, 360°).
    Sunrise in eastern half-circle (0° ≤ A < 180°); sunset by symmetry
    around the meridian (sunset = 360° − sunrise).
    """
    lat_r = radians(latitude_deg)
    dec_r = radians(declination_deg_)
    cos_a = sin(dec_r) / cos(lat_r)
    # Defensive clamp for floating-point edge cases (won't actually hit
    # |cos_a| > 1 within India lat × ±23.45° decl, but keep robust).
    if cos_a > 1.0:
        cos_a = 1.0
    elif cos_a < -1.0:
        cos_a = -1.0
    sunrise = degrees(acos(cos_a))      # in [0°, 180°]
    sunset = 360.0 - sunrise            # mirror across meridian
    return (sunrise, sunset)


def compute_sun_path(latitude_deg: float) -> SunPath:
    """Closed-form sun-path geometry at solstices for a given latitude.

    Validation (per spec § 4.4.3): latitude must be in (-45°, 45°). For v1
    this is overkill (India is 8°–37°N), but the bound documents the
    closed-form's domain of plausibility.

    Raises:
        ValueError: latitude out of plausible range.
    """
    if not (-45.0 < latitude_deg < 45.0):
        raise ValueError(
            f"latitude {latitude_deg}° out of plausible India range "
            f"(expected -45° < lat < 45°)"
        )

    summer_decl = declination_deg(SUMMER_SOLSTICE_DOY)
    winter_decl = declination_deg(WINTER_SOLSTICE_DOY)

    summer_alt = solar_altitude_at_noon_deg(latitude_deg, summer_decl)
    winter_alt = solar_altitude_at_noon_deg(latitude_deg, winter_decl)

    summer_arc = sunrise_sunset_azimuth_deg(latitude_deg, summer_decl)
    winter_arc = sunrise_sunset_azimuth_deg(latitude_deg, winter_decl)

    return SunPath(
        latitude_deg=latitude_deg,
        summer_solstice_noon_alt=summer_alt,
        winter_solstice_noon_alt=winter_alt,
        sunrise_arc_summer=summer_arc,
        sunrise_arc_winter=winter_arc,
    )


__all__ = [
    "SUMMER_SOLSTICE_DOY",
    "WINTER_SOLSTICE_DOY",
    "declination_deg",
    "solar_altitude_at_noon_deg",
    "sunrise_sunset_azimuth_deg",
    "compute_sun_path",
]
