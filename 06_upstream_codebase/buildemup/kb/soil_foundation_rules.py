"""
BuildemUp† — Soil & Foundation Rules
======================================

Knowledge module for soil bearing capacity assumptions and
foundation type selection. Sources:
  - IS 1080:1985 — Code of Practice for Design and Construction of
                   Shallow Foundations on Soils Other Than Raft
  - IS 1904:1986 — General Requirements for Design of Foundations
  - IS 6403:1981 — Code of Practice for Determination of Bearing
                   Capacity of Shallow Foundations
  - Local geotechnical surveys (Chennai, Bangalore typical)

For schematic design, we use city-typical assumptions. For final
design, ACTUAL soil testing is mandatory — this module flags that.

†= placeholder name marker.

KB_VERSION: "Soil_India_2026_v1"
"""
from __future__ import annotations
from dataclasses import dataclass


KB_VERSION = "Soil_India_2026_v1"


# ─────────────────────────────────────────────────────────────────────────────
# 1. SOIL BEARING CAPACITY DEFAULTS BY CITY
# ─────────────────────────────────────────────────────────────────────────────
# Safe Bearing Capacity (SBC) in tonnes per sqm.
# These are TYPICAL values for the urban areas of each city.
# Real soil testing can vary significantly — this is for early estimation.
@dataclass(frozen=True)
class SoilProfile:
    """Soil characteristics for a city/region."""
    city_name: str
    typical_soil: str               # "clay" | "sand" | "rock" | "filled_up"
    safe_bearing_capacity_t_sqm: float
    foundation_depth_m: float       # Typical embedment depth
    typical_water_table_m: float    # Depth to water table (m below GL)
    monsoon_water_table_m: float    # Water table during monsoon
    notes: str
    confidence_note: str            # What user should know about uncertainty
    area_specific_warnings: dict[str, str] = None  # Localised warnings

    def __post_init__(self):
        # Immutable default dict requires some dance
        if self.area_specific_warnings is None:
            object.__setattr__(self, 'area_specific_warnings', {})


CITY_SOIL_DEFAULTS = {
    "chennai": SoilProfile(
        city_name="Chennai",
        typical_soil="clay",
        safe_bearing_capacity_t_sqm=12.0,
        foundation_depth_m=1.5,
        typical_water_table_m=4.0,      # Inland areas
        monsoon_water_table_m=2.5,      # Rises during NE monsoon
        notes=(
            "Chennai has predominantly clay soil with SBC 10-15 T/sqm. "
            "Coastal areas (East Chennai near sea) may have lower bearing "
            "due to high water table. Velachery, Tambaram inland areas are "
            "typically firm clay."
        ),
        confidence_note=(
            "Soil testing recommended before final design. We've assumed "
            "12 T/sqm which is typical for inland Chennai. If your plot is "
            "coastal or near a water body, get a soil test (~₹15,000)."
        ),
        area_specific_warnings={
            "velachery": (
                "Velachery has historically been marshy. Water table can rise "
                "to within 1-2m of ground during NE monsoon (Oct-Dec). "
                "Consider waterproofing membrane below footing."
            ),
            "east_chennai": (
                "East Chennai (near sea) has low bearing capacity (8-10 T/sqm) "
                "and high water table. Pile foundations often needed for G+2+."
            ),
            "t_nagar": (
                "T. Nagar area has mixed fill. Soil testing strongly advised."
            ),
        },
    ),
    "bangalore": SoilProfile(
        city_name="Bangalore",
        typical_soil="rock_or_hard_clay",
        safe_bearing_capacity_t_sqm=20.0,
        foundation_depth_m=1.2,
        typical_water_table_m=8.0,
        monsoon_water_table_m=6.0,
        notes=(
            "Bangalore typically has shallow rock or hard murrum. "
            "SBC often 20-30 T/sqm. Foundation can be shallower."
        ),
        confidence_note="Typical Bangalore soil. Local variation possible.",
    ),
    "mumbai": SoilProfile(
        city_name="Mumbai",
        typical_soil="rock_or_filled_up",
        safe_bearing_capacity_t_sqm=15.0,
        foundation_depth_m=1.5,
        typical_water_table_m=3.0,
        monsoon_water_table_m=1.5,
        notes=(
            "Mumbai varies widely. Old reclaimed areas (South Mumbai, parts "
            "of Bandra) need pile foundations. Rocky areas (Powai, Goregaon) "
            "have good bearing 15-25 T/sqm. ASSUME pile if reclaimed."
        ),
        confidence_note=(
            "Mumbai soil is highly variable. SOIL TESTING IS MANDATORY "
            "before construction. Cost ₹20-30,000 well-spent."
        ),
    ),
    "delhi": SoilProfile(
        city_name="Delhi",
        typical_soil="silt_clay",
        safe_bearing_capacity_t_sqm=15.0,
        foundation_depth_m=1.5,
        typical_water_table_m=10.0,
        monsoon_water_table_m=8.0,
        notes="Delhi NCR has firm silty clay, SBC 12-18 T/sqm typical.",
        confidence_note="Typical Delhi soil. Yamuna floodplain areas are weaker.",
    ),
    "hyderabad": SoilProfile(
        city_name="Hyderabad",
        typical_soil="rock_or_murrum",
        safe_bearing_capacity_t_sqm=20.0,
        foundation_depth_m=1.2,
        typical_water_table_m=10.0,
        monsoon_water_table_m=8.0,
        notes="Hyderabad has hard murrum/rock similar to Bangalore.",
        confidence_note="Typical Hyderabad soil. Generally favorable.",
    ),
    "pune": SoilProfile(
        city_name="Pune",
        typical_soil="murrum",
        safe_bearing_capacity_t_sqm=18.0,
        foundation_depth_m=1.2,
        typical_water_table_m=8.0,
        monsoon_water_table_m=6.0,
        notes="Pune has firm murrum with SBC 15-20 T/sqm.",
        confidence_note="Typical Pune soil.",
    ),
    "kolkata": SoilProfile(
        city_name="Kolkata",
        typical_soil="alluvial_clay",
        safe_bearing_capacity_t_sqm=8.0,
        foundation_depth_m=2.0,
        typical_water_table_m=2.0,
        monsoon_water_table_m=0.5,
        notes=(
            "Kolkata has weak alluvial clay (Gangetic delta). SBC often "
            "5-10 T/sqm. Pile foundations common for >G+1."
        ),
        confidence_note=(
            "Weak soil. SOIL TESTING IS MANDATORY. Pile foundations may be "
            "required for G+1 or above."
        ),
    ),
}


def get_soil_profile(city: str, area: str | None = None) -> SoilProfile:
    """Get soil profile for a city. Falls back to a conservative default.

    Args:
        city: the city name (e.g., 'chennai').
        area: optional area/locality name (e.g., 'velachery') for
              area-specific warnings.
    """
    city_key = city.lower().strip()
    if city_key in CITY_SOIL_DEFAULTS:
        return CITY_SOIL_DEFAULTS[city_key]
    # Conservative fallback for unknown cities
    return SoilProfile(
        city_name=city.title(),
        typical_soil="assumed_medium",
        safe_bearing_capacity_t_sqm=10.0,
        foundation_depth_m=1.5,
        typical_water_table_m=5.0,  # Conservative assumption
        monsoon_water_table_m=3.0,
        notes=f"No local data for {city}. Using conservative defaults.",
        confidence_note="SOIL TESTING IS STRONGLY RECOMMENDED for unknown locations.",
    )


def get_area_warning(city: str, area: str | None) -> str | None:
    """Return area-specific warning if we have one, else None.

    Example: get_area_warning('chennai', 'velachery') returns the
    marshy-area warning for Velachery.
    """
    if not area:
        return None
    city_key = city.lower().strip()
    if city_key not in CITY_SOIL_DEFAULTS:
        return None
    profile = CITY_SOIL_DEFAULTS[city_key]
    area_key = area.lower().replace(" ", "_").replace(".", "")
    return profile.area_specific_warnings.get(area_key)


def check_water_table_risk(soil: SoilProfile, foundation_depth_m: float) -> dict:
    """Check if foundation depth is affected by water table.

    Returns a dict with risk level and user-facing warning.
    """
    risk = {
        "level": "LOW",
        "foundation_below_monsoon_water_table": False,
        "warning": None,
    }

    if foundation_depth_m >= soil.monsoon_water_table_m:
        # Foundation will be BELOW monsoon water table
        risk["foundation_below_monsoon_water_table"] = True
        risk["level"] = "HIGH"
        risk["warning"] = (
            f"During monsoon the water table in {soil.city_name} rises to "
            f"{soil.monsoon_water_table_m}m. Your foundation at "
            f"{foundation_depth_m}m will be below this level. You'll need: "
            f"(1) below-footing waterproofing membrane (~₹10-15K extra), "
            f"(2) dewatering during construction in monsoon season (avoid "
            f"Oct-Dec casting), (3) anti-corrosion treatment for rebars."
        )
    elif foundation_depth_m >= soil.monsoon_water_table_m - 0.5:
        # Within 0.5m of monsoon water table
        risk["level"] = "MEDIUM"
        risk["warning"] = (
            f"Your foundation at {foundation_depth_m}m is close to the "
            f"monsoon water table ({soil.monsoon_water_table_m}m) in "
            f"{soil.city_name}. Consider waterproofing as a precaution."
        )

    return risk


# ─────────────────────────────────────────────────────────────────────────────
# 2. FOUNDATION TYPE SELECTION (IS 1904)
# ─────────────────────────────────────────────────────────────────────────────
# Decision matrix: column load × bearing capacity → foundation type
@dataclass(frozen=True)
class FoundationSpec:
    """Specification for a foundation footing."""
    type: str                  # "isolated" | "combined" | "raft" | "pile"
    size_m: tuple[float, float]   # (width, length) for isolated
    depth_m: float
    concrete_volume_cum: float
    steel_kg: float
    description: str
    source: str


def calculate_isolated_footing_size(
    column_load_kn: float,
    safe_bearing_capacity_t_sqm: float,
    safety_factor: float = 1.1,
) -> tuple[float, float]:
    """Size a square isolated footing for a given column load.

    Args:
        column_load_kn: total axial load on the column (kN).
        safe_bearing_capacity_t_sqm: SBC of soil in T/sqm.
        safety_factor: additional safety on bearing area.

    Returns:
        (width, length) in metres. Square footing for residential.

    Source: IS 1080:1985 + Punmia Ch. 16
    """
    if column_load_kn <= 0:
        raise ValueError(f"Column load must be positive, got {column_load_kn}")
    if safe_bearing_capacity_t_sqm <= 0:
        raise ValueError(f"SBC must be positive, got {safe_bearing_capacity_t_sqm}")

    # Convert kN to tonnes (1 kN ≈ 0.102 tonnes-force)
    load_tonnes = column_load_kn * 0.102

    # Required area = load / SBC, with safety factor
    required_area_sqm = (load_tonnes * safety_factor) / safe_bearing_capacity_t_sqm

    # Square footing side
    side_m = required_area_sqm ** 0.5

    # Round up to nearest 0.1m for practicality
    side_m = round(side_m + 0.05, 1)

    # Minimum practical footing size (so you can actually pour concrete)
    side_m = max(side_m, 1.0)

    return (side_m, side_m)


def estimate_column_load_kn(
    tributary_area_sqm: float,
    floors_above: int,
    load_per_floor_knsqm: float = 12.0,
) -> float:
    """Rough estimate of axial load on a column.

    load_per_floor includes:
      - Self weight of slab + beams + finishes (~6 kN/sqm)
      - Live load (residential per IS 875: 2 kN/sqm)
      - Wall load tributary to column (~4 kN/sqm)
      Total ≈ 12 kN/sqm per floor (conservative for residential)

    Source: IS 875 + practical residential dead+live load.
    """
    floors_supported = floors_above + 1  # +1 for the floor above this column
    total_load_kn = tributary_area_sqm * load_per_floor_knsqm * floors_supported
    return total_load_kn


def select_foundation_type(
    column_load_kn: float,
    soil: SoilProfile,
    column_spacing_m: float,
) -> str:
    """Pick foundation type based on load, soil, and column spacing.

    Logic:
      - If footing size > 60% of column spacing → use combined or raft
      - If soil is weak (SBC < 6) → recommend pile/raft
      - Otherwise → isolated footing
    """
    # Weak soil check
    if soil.safe_bearing_capacity_t_sqm < 6.0:
        return "pile"

    # Calculate required footing size
    fw, _ = calculate_isolated_footing_size(
        column_load_kn, soil.safe_bearing_capacity_t_sqm
    )

    # If footings would overlap or nearly so, use combined or raft
    if fw > column_spacing_m * 0.6:
        return "raft"
    elif fw > column_spacing_m * 0.45:
        return "combined"
    else:
        return "isolated"


def estimate_footing_quantities(
    footing_size_m: tuple[float, float],
    depth_m: float = 0.35,
) -> tuple[float, float]:
    """Estimate concrete and steel for one isolated footing.

    Returns (concrete_cum, steel_kg).
    Source: IS 456 + Punmia.
    """
    width, length = footing_size_m
    concrete_cum = width * length * depth_m

    # Steel ~ 60 kg/cum for footings (light reinforcement)
    steel_kg = concrete_cum * 60.0

    return (concrete_cum, steel_kg)
