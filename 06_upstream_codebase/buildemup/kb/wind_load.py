"""
BuildemUp† — IS 875 Part 3 Wind Load Rules
=============================================

Wind load calculation for residential buildings.

Most critical for:
  - Coastal cities (Mumbai, Chennai, Kolkata, Kochi)
  - Cyclone-prone regions (Odisha, Andhra coast)
  - Hill stations with strong winds

For G+2 residential, wind load typically governs only for:
  - Narrow elongated plans
  - Cantilever balconies
  - Large roof overhangs
  - Coastal locations

Source: IS 875 (Part 3):2015 — Wind Loads

†= placeholder name marker.

KB_VERSION: "Wind_IS875_2026_v1"
"""
from __future__ import annotations
from dataclasses import dataclass


KB_VERSION = "Wind_IS875_2026_v1"


# ─── 1. BASIC WIND SPEED BY CITY (IS 875 Part 3 Annex A Map) ─────────────
# Values in m/s at 10m height above ground for 50-year return period.
BASIC_WIND_SPEED_MS = {
    "chennai":    50,   # Coastal, Tamil Nadu
    "mumbai":     44,   # Coastal west, Maharashtra
    "bangalore":  33,   # Inland, moderate
    "hyderabad":  44,   # Telangana
    "pune":       39,   # Maharashtra
    "delhi":      47,   # Northern plains
    "kolkata":    50,   # Coastal east
    "kochi":      39,   # Kerala coast
    "bhubaneswar": 50,  # Cyclone zone
    "visakhapatnam": 50, # Cyclone zone
}


# ─── 2. TERRAIN CATEGORY (IS 875 Part 3 cl. 6.3.2) ───────────────────────
# Category 1: Open sea / coast (highest wind)
# Category 2: Open terrain with scattered obstructions
# Category 3: Terrain with numerous obstructions (urban)
# Category 4: Dense urban / tall buildings (lowest wind at low level)

TERRAIN_K2_FACTOR = {
    # For heights 10m or less (most residential)
    "coastal": 1.05,       # Category 1
    "open": 1.00,          # Category 2
    "urban": 0.91,         # Category 3 (most Indian cities)
    "dense_urban": 0.80,   # Category 4 (metros inner city)
}


# ─── 3. TOPOGRAPHY FACTOR K3 (IS 875 Part 3 cl. 6.3.3) ───────────────────
# 1.0 for flat ground, up to 1.36 for hill tops with steep slopes
TOPOGRAPHY_K3_FLAT = 1.0
TOPOGRAPHY_K3_GENTLE_HILL = 1.10
TOPOGRAPHY_K3_STEEP_HILL = 1.30


# ─── 4. IMPORTANCE FACTOR K4 (IS 875 Part 3 cl. 6.3.4) ───────────────────
# For residential = 1.0 (K4 applies only for essential services)
IMPORTANCE_K4_RESIDENTIAL = 1.0


# ─── 5. DESIGN WIND PRESSURE ─────────────────────────────────────────────
# Pz = 0.6 × Vz² (cl. 7.2)
# where Vz = Vb × k1 × k2 × k3 × k4
# k1 = risk coefficient, 1.0 for residential
K1_RESIDENTIAL = 1.0


@dataclass(frozen=True)
class WindLoadResult:
    """Wind load calculation result."""
    basic_wind_speed_ms: float
    design_wind_speed_ms: float
    design_pressure_pa: float           # Pascals (N/m²)
    design_pressure_knsqm: float        # kN/sqm (for load combinations)
    governing: bool                     # True if wind governs over seismic
    warnings: tuple[str, ...]
    notes: str


def calculate_wind_load(
    city: str,
    building_height_m: float,
    terrain_category: str = "urban",
    on_hill: bool = False,
) -> WindLoadResult:
    """Calculate wind load per IS 875 Part 3.

    Args:
        city: city name, used to look up basic wind speed.
        building_height_m: total building height above ground.
        terrain_category: 'coastal', 'open', 'urban', 'dense_urban'.
        on_hill: True if building is on a hill top.

    Returns:
        WindLoadResult with design pressure and warnings.
    """
    warnings: list[str] = []

    # Basic wind speed
    vb = BASIC_WIND_SPEED_MS.get(city.lower(), 44.0)  # 44 m/s conservative default

    # k1 (risk)
    k1 = K1_RESIDENTIAL

    # k2 (terrain)
    k2 = TERRAIN_K2_FACTOR.get(terrain_category, 0.91)

    # k3 (topography)
    k3 = TOPOGRAPHY_K3_GENTLE_HILL if on_hill else TOPOGRAPHY_K3_FLAT

    # k4 (importance)
    k4 = IMPORTANCE_K4_RESIDENTIAL

    # Design wind speed
    vz = vb * k1 * k2 * k3 * k4

    # Design pressure (Pa)
    pz = 0.6 * (vz ** 2)

    # Convert to kN/sqm
    pz_knsqm = pz / 1000.0

    # Warnings
    if vb >= 50:
        warnings.append(
            f"{city.title()} has high basic wind speed ({vb} m/s). "
            "Wind load is significant. Ensure roof elements are securely "
            "fastened. Overhangs/sunshades should be anchored properly."
        )

    if terrain_category == "coastal" or city.lower() in ("chennai", "mumbai", "kolkata", "kochi"):
        warnings.append(
            f"Coastal location: salt-air corrosion of steel reinforcement "
            f"is a concern. Use higher concrete cover (50mm min), consider "
            f"corrosion-resistant TMT (CRS) bars. Adds ~5% to steel cost."
        )

    if building_height_m > 12:  # G+3 or higher
        warnings.append(
            f"Building height {building_height_m}m: wind pressure increases "
            f"with height. Detailed structural analysis recommended."
        )

    # For G+2 residential, seismic usually governs in Zone III+
    # Wind may govern for Zone II coastal or tall G+4
    governing_note = (
        "For typical G+2 residential in Zone III+, seismic usually governs. "
        "For Zone II coastal or G+4+, wind may govern. Engineer will verify."
    )

    notes = (
        f"Vb={vb} m/s, Vz={vz:.1f} m/s, Pz={pz:.0f} Pa "
        f"({pz_knsqm:.2f} kN/sqm). {governing_note}"
    )

    return WindLoadResult(
        basic_wind_speed_ms=vb,
        design_wind_speed_ms=round(vz, 1),
        design_pressure_pa=round(pz, 0),
        design_pressure_knsqm=round(pz_knsqm, 2),
        governing=False,  # Simplified: assume seismic governs for residential
        warnings=tuple(warnings),
        notes=notes,
    )


# ─── 6. CITATIONS ────────────────────────────────────────────────────────
CITATIONS = {
    "IS_875_3": "IS 875 (Part 3):2015 — Design Loads (Wind) for Buildings",
}


# ─── 7. LOAD COMBINATIONS (IS 875 + IS 1893) ─────────────────────────────
# IS 875 Part 5 cl. 3.5 + IS 1893:2016 cl. 6.3
# For limit state design, primary combinations to check:
#   1.5 (DL + LL)              — gravity only (no lateral)
#   1.2 (DL + LL ± WL)         — gravity + wind
#   1.5 (DL ± WL)              — wind dominant (no live load)
#   1.2 (DL + LL ± EL)         — gravity + earthquake
#   1.5 (DL ± EL)              — earthquake dominant
#
# For our preliminary check we compare the two LATERAL cases:
#   wind: 1.2(DL+LL+WL)
#   seismic: 1.2(DL+LL+EL)
# and report which governs.


# Seismic base shear coefficient (IS 1893:2016 cl. 7.5.3)
# Vb / W = (Z × I × Sa/g) / (2 × R)
# For preliminary residential we use representative values:
#   Z = zone factor (from SEISMIC_ZONE_FACTORS in seismic_detailing)
#   I = 1.0 residential
#   Sa/g = 2.5 (medium soil, short period)
#   R = 5.0 with IS 13920 / 3.0 without
def estimate_base_shear_coefficient(seismic_zone: str, has_is13920: bool) -> float:
    """Estimate seismic base shear coefficient Vb/W.

    Returns the ratio of base shear to total weight — i.e., what fraction
    of the building's weight acts laterally during the design earthquake.
    """
    from buildemup.kb.seismic_detailing import SEISMIC_ZONE_FACTORS
    z = SEISMIC_ZONE_FACTORS.get(seismic_zone, 0.16)
    importance = 1.0  # residential
    sa_g = 2.5
    response_reduction = 5.0 if has_is13920 else 3.0
    return round((z * importance * sa_g) / (2 * response_reduction), 3)


def compare_lateral_loads(
    wind_pressure_knsqm: float,
    building_face_area_sqm: float,
    seismic_base_shear_coefficient: float,
    building_weight_kn: float,
) -> dict:
    """Compare wind force vs seismic base shear; return which governs.

    For preliminary design we compute total lateral force from each source
    and pick the larger as the "governing" lateral load case.
    """
    wind_force_kn = wind_pressure_knsqm * building_face_area_sqm
    seismic_force_kn = seismic_base_shear_coefficient * building_weight_kn

    if wind_force_kn > seismic_force_kn:
        governing = "wind"
        ratio = wind_force_kn / seismic_force_kn if seismic_force_kn > 0 else float("inf")
        message = (
            f"Wind governs: {wind_force_kn:.0f} kN vs seismic {seismic_force_kn:.0f} kN "
            f"({ratio:.2f}× larger). For G+2 residential this is unusual — "
            f"often indicates coastal/cyclone exposure or tall-narrow plan."
        )
    else:
        governing = "seismic"
        ratio = seismic_force_kn / wind_force_kn if wind_force_kn > 0 else float("inf")
        message = (
            f"Seismic governs: {seismic_force_kn:.0f} kN vs wind {wind_force_kn:.0f} kN "
            f"({ratio:.2f}× larger). Typical for G+2 residential in Zone III+."
        )

    return {
        "wind_force_kn": round(wind_force_kn, 0),
        "seismic_force_kn": round(seismic_force_kn, 0),
        "governing_load": governing,
        "ratio": round(ratio, 2),
        "message": message,
        "disclaimer": (
            "Preliminary lateral force comparison only. Real load "
            "combinations per IS 875 Part 5 + IS 1893 must be checked by "
            "structural engineer at detailed design stage."
        ),
    }
