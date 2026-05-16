"""
BuildemUp† — Pile Foundation Rules
=====================================

Pile foundation sizing for weak soil conditions.

When isolated/raft is insufficient:
  - Mumbai reclaimed areas (Backbay, parts of Bandra, Nariman Point)
  - Kolkata Gangetic alluvium
  - Any coastal site with soft strata > 3m deep
  - Sites where SBC < 6 T/sqm

Pile types commonly used in India:
  - Bored cast-in-situ: most common for residential (₹3000-5000/rmt)
  - Driven precast: faster but vibration issues (rare in residential)
  - Under-reamed: for expansive soils, DFCC design (specific regions)

This module handles the most common: BORED CAST-IN-SITU RCC PILES.

Sources:
  - IS 2911 (Part 1, Sec 2):2010 — Bored cast-in-situ concrete piles
  - IS 2911 (Part 4):2013 — Load test on piles
  - Varghese, "Design of Reinforced Concrete Foundations"

†= placeholder name marker.

KB_VERSION: "Pile_Foundation_IS2911_2026_v1"
"""
from __future__ import annotations
from dataclasses import dataclass


KB_VERSION = "Pile_Foundation_IS2911_2026_v1"


# ─── 1. PILE CAPACITY RULES ──────────────────────────────────────────────
# For bored cast-in-situ piles in soft soil:
#   Ultimate load = skin friction + end bearing
# For preliminary design we use rule-of-thumb capacities per pile dia.
# Source: IS 2911 + Varghese Ch. 7

@dataclass(frozen=True)
class PileSpec:
    """One pile specification."""
    diameter_mm: int
    typical_length_m: float        # Embedment below scour level
    safe_working_load_kn: float    # Per single pile
    concrete_cum_per_pile: float
    steel_kg_per_pile: float
    note: str


# Typical single-pile safe loads for bored cast-in-situ piles in
# medium-to-soft alluvial soil (Mumbai/Kolkata typical)
PILE_CATALOG = {
    300: PileSpec(
        diameter_mm=300,
        typical_length_m=8.0,
        safe_working_load_kn=200,
        concrete_cum_per_pile=0.565,   # π × 0.15² × 8
        steel_kg_per_pile=50,
        note="Small pile — residential single-family, light loads",
    ),
    400: PileSpec(
        diameter_mm=400,
        typical_length_m=10.0,
        safe_working_load_kn=350,
        concrete_cum_per_pile=1.257,   # π × 0.20² × 10
        steel_kg_per_pile=90,
        note="Medium pile — typical G+2 residential on weak soil",
    ),
    500: PileSpec(
        diameter_mm=500,
        typical_length_m=12.0,
        safe_working_load_kn=550,
        concrete_cum_per_pile=2.356,   # π × 0.25² × 12
        steel_kg_per_pile=160,
        note="Larger pile — G+3 or heavy column loads",
    ),
    600: PileSpec(
        diameter_mm=600,
        typical_length_m=15.0,
        safe_working_load_kn=800,
        concrete_cum_per_pile=4.241,   # π × 0.30² × 15
        steel_kg_per_pile=230,
        note="Large pile — G+4 or very soft strata",
    ),
}


def select_pile_spec(column_load_kn: float, safety_factor: float = 1.1) -> PileSpec:
    """Select a pile specification that can carry the column load.

    Args:
        column_load_kn: factored column load
        safety_factor: extra margin on working load (default 1.1 = 10%)

    Returns:
        PileSpec that can safely carry the load.

    If load exceeds largest catalogued pile, returns the largest with note.
    """
    required_capacity = column_load_kn * safety_factor

    for dia in sorted(PILE_CATALOG.keys()):
        spec = PILE_CATALOG[dia]
        if spec.safe_working_load_kn >= required_capacity:
            return spec

    # Load exceeds our catalog — return largest + flag
    largest = PILE_CATALOG[max(PILE_CATALOG.keys())]
    return PileSpec(
        diameter_mm=largest.diameter_mm,
        typical_length_m=largest.typical_length_m * 1.2,  # Assume deeper
        safe_working_load_kn=largest.safe_working_load_kn,
        concrete_cum_per_pile=largest.concrete_cum_per_pile * 1.2,
        steel_kg_per_pile=largest.steel_kg_per_pile * 1.2,
        note=(
            f"Load exceeds typical residential pile capacity. "
            f"Detailed pile design required by geotechnical engineer."
        ),
    )


# ─── 2. PILE GROUP CONFIGURATION ─────────────────────────────────────────
# For each column, typically 1 pile if load < 400 kN, else multiple
# Pile spacing in group: 3 × diameter (IS 2911 cl. 6.3.4)

def pile_group_size(column_load_kn: float, single_pile_capacity_kn: float) -> int:
    """How many piles per column?

    Residential G+2 typically needs 1-2 piles per column.
    """
    import math
    count = math.ceil(column_load_kn / single_pile_capacity_kn)
    return max(count, 1)


# ─── 3. PILE CAP ─────────────────────────────────────────────────────────
# A pile cap sits over the pile group, tying piles to column.
# Size: 3D overhang from edge piles per IS 2911 cl. 6.3.4

def pile_cap_size_m(pile_count: int, pile_dia_mm: int) -> tuple[float, float]:
    """Pile cap dimensions for a group."""
    d = pile_dia_mm / 1000.0  # m
    if pile_count == 1:
        # Single pile: cap is just a pedestal ~1.2m × 1.2m
        return (1.2, 1.2)
    elif pile_count == 2:
        # 2 piles in a line: 3D center-to-center + 1.5D overhang each side
        length = 3 * d + 2 * (1.5 * d)
        width = 1.5 * d + 2 * (1.5 * d)
        return (round(width, 2), round(length, 2))
    elif pile_count <= 4:
        # 2×2 square group
        side = 3 * d + 2 * (1.5 * d)
        return (round(side, 2), round(side, 2))
    else:
        # 3×3 or bigger — approximate
        side = 2 * (3 * d) + 2 * (1.5 * d)
        return (round(side, 2), round(side, 2))


def pile_cap_concrete_cum(
    cap_size_m: tuple[float, float], thickness_m: float = 0.6
) -> float:
    """Concrete volume for pile cap."""
    return cap_size_m[0] * cap_size_m[1] * thickness_m


# ─── 4. COST MULTIPLIERS ─────────────────────────────────────────────────
# Pile driving/boring is more expensive than isolated footings.
# Mumbai premium: pile contractors charge 20-30% more than Chennai
# due to demand and soil conditions.
PILE_COST_MULTIPLIER_BY_CITY = {
    "mumbai": 1.25,        # Premium — high demand, reclaimed soil
    "kolkata": 1.15,       # Weak alluvial, many contractors
    "chennai": 1.10,       # Only when needed (coastal areas)
    "default": 1.20,
}


def estimate_pile_cost_multiplier(city: str) -> float:
    """Multiplier for pile cost vs flat material rate."""
    return PILE_COST_MULTIPLIER_BY_CITY.get(
        city.lower().strip(), PILE_COST_MULTIPLIER_BY_CITY["default"]
    )


# ─── 5. WARNINGS ─────────────────────────────────────────────────────────
def pile_foundation_warnings(city: str) -> list[str]:
    """Generate warnings specific to pile foundation projects."""
    warnings = [
        "PILE FOUNDATION: Adds significant cost (typically ₹2-5L extra "
        "vs isolated footings for residential).",
        "SOIL TESTING IS MANDATORY before proceeding. Budget ₹25-40K for "
        "Standard Penetration Test (SPT) with boreholes.",
        "Pile load test recommended on first pile (IS 2911 Part 4). "
        "Budget ~₹35-50K for one test.",
        "Expect 15-25 days of pile construction before superstructure. "
        "Affects overall timeline.",
        "Vibration during boring: neighbours may object if within 5m.",
    ]
    if city.lower() == "mumbai":
        warnings.append(
            "Mumbai pile driving/boring requires BMC notification. "
            "Permit process: 2-3 weeks. Budget ₹5-10K for permits."
        )
    return warnings


# ─── 6. CITATIONS ────────────────────────────────────────────────────────
CITATIONS = {
    "IS_2911_1": "IS 2911 (Part 1, Sec 2):2010 — Bored cast-in-situ piles",
    "IS_2911_4": "IS 2911 (Part 4):2013 — Pile load test",
    "VARGHESE": "P.C. Varghese — Design of Reinforced Concrete Foundations",
}
