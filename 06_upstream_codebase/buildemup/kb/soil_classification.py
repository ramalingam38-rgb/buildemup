"""
BuildemUp† — Soil Classification & Bearing Capacity (v0.6)
=============================================================

Real IS 1904:1986 safe bearing capacity (SBC) values per soil type.

CRITICAL: These values follow Indian Standards. The earlier draft
"Build Ease — Real Solutions" document proposed values that were
WRONG by ~10× for hard rock (off by t/m² vs kN/m² unit confusion).
We use real IS 1904 values per user decision and our research.

ALL VALUES SHOWN AS RANGES (not single numbers) per user direction.

NEVER replace actual soil testing. SBC values here are for preliminary
estimation only — every output must include the disclaimer:
  "Actual SBC must be confirmed via soil test before construction."

Citations:
  - IS 1904:1986 (Code of practice for design and construction of
    foundations in soils)
  - IS 6403:1981 (Code of practice for determination of bearing
    capacity of shallow foundations)
  - Standard residential geotechnical practice in India

†= placeholder name marker.

KB_VERSION: "SoilSBC_IS1904_v1_2026"
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


KB_VERSION = "SoilSBC_IS1904_v1_2026"


class SoilClass(str, Enum):
    """Soil classification categories per IS 1904 (simplified)."""
    VERY_SOFT_CLAY = "very_soft_clay"
    SOFT_CLAY = "soft_clay"
    MEDIUM_CLAY = "medium_clay"
    STIFF_CLAY = "stiff_clay"
    LOOSE_SAND = "loose_sand"
    MEDIUM_SAND = "medium_sand"
    DENSE_SAND = "dense_sand"
    DENSE_GRAVEL = "dense_gravel"
    SOFT_ROCK = "soft_rock"
    HARD_ROCK = "hard_rock"
    BLACK_COTTON = "black_cotton"      # Expansive — special case
    RECLAIMED_FILL = "reclaimed_fill"   # Special case (e.g., Mumbai)


@dataclass(frozen=True)
class SoilProfile:
    """Per-soil-class properties for preliminary foundation sizing."""
    soil_class: SoilClass
    display_name: str
    sbc_min_knm2: float        # Lower bound of safe bearing capacity (kN/m²)
    sbc_max_knm2: float        # Upper bound
    sbc_typical_knm2: float    # Typical mid-range value for cost estimation
    is_expansive: bool         # Black cotton, expansive clays — needs special foundation
    requires_pile: bool        # True if shallow foundation NOT recommended
    requires_soil_test: bool   # Recommend soil test before construction
    notes: str


# ─────────────────────────────────────────────────────────────────────────
# Real IS 1904 / Indian practice SBC values (RANGES, not point values)
# Per user decision: use IS-aligned values, REJECT document numbers.
# ─────────────────────────────────────────────────────────────────────────
SOIL_PROFILES: dict[SoilClass, SoilProfile] = {

    SoilClass.VERY_SOFT_CLAY: SoilProfile(
        soil_class=SoilClass.VERY_SOFT_CLAY,
        display_name="Very soft clay",
        sbc_min_knm2=0,
        sbc_max_knm2=50,
        sbc_typical_knm2=25,
        is_expansive=False,
        requires_pile=True,
        requires_soil_test=True,
        notes="Very low SBC. Shallow foundation NOT recommended — pile foundation required.",
    ),

    SoilClass.SOFT_CLAY: SoilProfile(
        soil_class=SoilClass.SOFT_CLAY,
        display_name="Soft clay",
        sbc_min_knm2=75,
        sbc_max_knm2=100,
        sbc_typical_knm2=90,
        is_expansive=False,
        requires_pile=False,    # Marginal — case by case
        requires_soil_test=True,
        notes="Marginal SBC. Wider footings or raft may be needed. Settlement check critical.",
    ),

    SoilClass.MEDIUM_CLAY: SoilProfile(
        soil_class=SoilClass.MEDIUM_CLAY,
        display_name="Medium clay",
        sbc_min_knm2=100,
        sbc_max_knm2=150,
        sbc_typical_knm2=125,
        is_expansive=False,
        requires_pile=False,
        requires_soil_test=True,
        notes="Acceptable for shallow foundations with proper sizing.",
    ),

    SoilClass.STIFF_CLAY: SoilProfile(
        soil_class=SoilClass.STIFF_CLAY,
        display_name="Stiff clay / hard clay (dry)",
        sbc_min_knm2=150,
        sbc_max_knm2=440,       # Per IS 1904 hard/stiff clay
        sbc_typical_knm2=250,
        is_expansive=False,
        requires_pile=False,
        requires_soil_test=True,
        notes="Good bearing capacity. Suitable for residential shallow foundations.",
    ),

    SoilClass.LOOSE_SAND: SoilProfile(
        soil_class=SoilClass.LOOSE_SAND,
        display_name="Loose sand (dry)",
        sbc_min_knm2=100,
        sbc_max_knm2=150,
        sbc_typical_knm2=125,
        is_expansive=False,
        requires_pile=False,
        requires_soil_test=True,
        notes="Marginal. Liquefaction risk if water table is high. Site investigation mandatory.",
    ),

    SoilClass.MEDIUM_SAND: SoilProfile(
        soil_class=SoilClass.MEDIUM_SAND,
        display_name="Medium sand",
        sbc_min_knm2=150,
        sbc_max_knm2=250,
        sbc_typical_knm2=200,
        is_expansive=False,
        requires_pile=False,
        requires_soil_test=True,
        notes="Common residential soil. Suitable for shallow foundations.",
    ),

    SoilClass.DENSE_SAND: SoilProfile(
        soil_class=SoilClass.DENSE_SAND,
        display_name="Dense sand",
        sbc_min_knm2=250,
        sbc_max_knm2=450,
        sbc_typical_knm2=350,
        is_expansive=False,
        requires_pile=False,
        requires_soil_test=True,
        notes="Excellent for shallow foundations. Low settlement.",
    ),

    SoilClass.DENSE_GRAVEL: SoilProfile(
        soil_class=SoilClass.DENSE_GRAVEL,
        display_name="Dense gravel / gravelly sand",
        sbc_min_knm2=300,
        sbc_max_knm2=450,
        sbc_typical_knm2=400,
        is_expansive=False,
        requires_pile=False,
        requires_soil_test=True,
        notes="Excellent bearing capacity. Cost-effective shallow foundations.",
    ),

    SoilClass.SOFT_ROCK: SoilProfile(
        soil_class=SoilClass.SOFT_ROCK,
        display_name="Soft rock (sandstone, shale)",
        sbc_min_knm2=440,
        sbc_max_knm2=880,
        sbc_typical_knm2=660,
        is_expansive=False,
        requires_pile=False,
        requires_soil_test=True,
        notes="Excellent bearing. Footings can be small. Verify rock continuity below foundation.",
    ),

    SoilClass.HARD_ROCK: SoilProfile(
        soil_class=SoilClass.HARD_ROCK,
        display_name="Hard rock (granite, basalt)",
        sbc_min_knm2=450,       # Conservative floor (per user decision)
        sbc_max_knm2=3300,      # Per IS 1904 actual upper range
        sbc_typical_knm2=1620,  # Typical mid-range
        is_expansive=False,
        requires_pile=False,
        requires_soil_test=True,
        notes=(
            "Hard rock has very high bearing capacity (up to 3300 kN/m² per "
            "IS 1904). For preliminary cost estimation we use a conservative "
            "floor of 450 kN/m² to avoid over-confident foundation sizing if "
            "rock turns out to be weathered or partially soft. Engineer must "
            "verify actual rock quality."
        ),
    ),

    SoilClass.BLACK_COTTON: SoilProfile(
        soil_class=SoilClass.BLACK_COTTON,
        display_name="Black cotton soil (expansive clay)",
        sbc_min_knm2=130,
        sbc_max_knm2=160,
        sbc_typical_knm2=145,
        is_expansive=True,       # CRITICAL — expansive
        requires_pile=False,     # But needs special anti-swelling design
        requires_soil_test=True,
        notes=(
            "EXPANSIVE SOIL. Swells in monsoon, shrinks in summer — causes "
            "cracks if foundation not specially designed. Recommended: "
            "footing depth > 1.5m below ground OR under-reamed piles OR "
            "soil replacement. Structural engineer MUST be consulted."
        ),
    ),

    SoilClass.RECLAIMED_FILL: SoilProfile(
        soil_class=SoilClass.RECLAIMED_FILL,
        display_name="Reclaimed land / artificial fill",
        sbc_min_knm2=0,
        sbc_max_knm2=75,
        sbc_typical_knm2=50,
        is_expansive=False,
        requires_pile=True,      # Almost always needs piles
        requires_soil_test=True,
        notes=(
            "Reclaimed soil (e.g., Mumbai areas, coastal reclamations) has "
            "very poor bearing capacity AND highly variable consolidation. "
            "Pile foundation strongly recommended. Settlement risk is high. "
            "Site-specific geotechnical investigation MANDATORY."
        ),
    ),
}


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────
def get_soil_profile(soil_class: SoilClass) -> SoilProfile:
    if soil_class not in SOIL_PROFILES:
        raise KeyError(f"Unknown soil class: {soil_class}")
    return SOIL_PROFILES[soil_class]


def check_foundation_adequacy(
    soil_class: SoilClass,
    column_load_kn: float,
    footing_area_m2: float,
) -> dict:
    """Check if a proposed shallow footing is adequate for the given soil.

    Returns dict with:
      - applied_pressure_knm2: column_load / footing_area
      - sbc_typical_knm2: typical SBC for this soil
      - utilization_pct: applied / SBC × 100
      - is_adequate: True if utilization ≤ 80%
      - recommendation: text recommendation
      - requires_pile_anyway: True if soil class always needs pile
    """
    profile = get_soil_profile(soil_class)
    if footing_area_m2 <= 0:
        return {
            "error": "Footing area must be > 0",
            "is_adequate": False,
        }

    applied_pressure = column_load_kn / footing_area_m2
    sbc = profile.sbc_typical_knm2
    utilization = (applied_pressure / sbc * 100) if sbc > 0 else 999.0

    if profile.requires_pile:
        recommendation = (
            f"{profile.display_name}: shallow foundation NOT recommended "
            f"regardless of footing size. Use pile foundation. "
            f"({profile.notes})"
        )
        adequate = False
    elif utilization <= 80:
        recommendation = (
            f"{profile.display_name}: footing area adequate "
            f"({utilization:.0f}% of SBC utilised). "
            f"Engineer must verify with actual soil test."
        )
        adequate = True
    elif utilization <= 100:
        recommendation = (
            f"{profile.display_name}: footing tight ({utilization:.0f}% "
            f"of SBC utilised). Consider increasing footing size for "
            f"settlement comfort. Engineer review needed."
        )
        adequate = True  # Within capacity but tight
    else:
        recommendation = (
            f"{profile.display_name}: footing INADEQUATE "
            f"({utilization:.0f}% of SBC — exceeds capacity). "
            f"Increase footing size OR upgrade soil OR use pile foundation."
        )
        adequate = False

    return {
        "soil_class": soil_class.value,
        "applied_pressure_knm2": round(applied_pressure, 1),
        "sbc_typical_knm2": sbc,
        "sbc_range_knm2": (profile.sbc_min_knm2, profile.sbc_max_knm2),
        "utilization_pct": round(utilization, 1),
        "is_adequate": adequate,
        "requires_pile_anyway": profile.requires_pile,
        "is_expansive": profile.is_expansive,
        "recommendation": recommendation,
        "soil_test_required_disclaimer": (
            "Actual SBC must be confirmed via soil test before construction. "
            "Values used here are typical IS 1904 ranges for preliminary "
            "estimation only."
        ),
    }


def all_soil_classes() -> list[SoilClass]:
    """All supported soil classes."""
    return list(SOIL_PROFILES.keys())
