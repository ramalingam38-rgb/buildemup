"""
BuildemUp† — Load Estimation Rules (IS 875 Parts 1, 2, 3)
==========================================================

Realistic load estimation for residential column design.

Previously: single 12 kN/sqm per floor (oversimplified).
Now: differentiated by floor type, with concentrated loads for
     water tanks, staircases, and balconies.

Sources:
  - IS 875 (Part 1):1987 — Dead loads
  - IS 875 (Part 2):1987 — Imposed loads
  - IS 875 (Part 3):2015 — Wind loads
  - Punmia, Ch. 2 — Design loads

†= placeholder name marker.

KB_VERSION: "Loads_India_2026_v1"
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


KB_VERSION = "Loads_India_2026_v1"


class FloorType(str, Enum):
    """What kind of floor a column supports."""
    STILT_PARKING = "stilt_parking"    # Parking floor (light live load)
    RESIDENTIAL = "residential"         # Normal living floor
    TERRACE_ACCESSIBLE = "terrace_accessible"  # Gym/garden on terrace
    TERRACE_INACCESSIBLE = "terrace_inaccessible"  # Just roof slab
    BALCONY = "balcony"                 # Cantilever balcony
    STAIRCASE = "staircase"             # Staircase landing


# v0.7.1: single-source rules — load from JSON at import time.
from buildemup.utils.kb_rules_loader import load_rules as _load_rules
_LOADS = _load_rules("load_rules")


# ─────────────────────────────────────────────────────────────────────────────
# 1. DEAD LOADS (IS 875 Part 1) — loaded from kb_rules/load_rules.json
# ─────────────────────────────────────────────────────────────────────────────
SLAB_WEIGHT_KN_PER_SQM_PER_MM = float(
    _LOADS["dead_load"]["values"]["slab_weight_kn_per_sqm_per_mm"]
)
FINISHES_KN_PER_SQM = float(
    _LOADS["dead_load"]["values"]["finishes_kn_per_sqm"]
)

# Internal partition wall allowance — loaded from JSON
PARTITION_WALL_KN_PER_SQM = float(
    _LOADS["dead_load"]["values"]["partition_wall_kn_per_sqm"]
)


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIVE LOADS (IS 875 Part 2) — kN/sqm — loaded from JSON
# ─────────────────────────────────────────────────────────────────────────────
# JSON keys are enum names (uppercase) — remap to FloorType keys for
# back-compat with existing callers.
LIVE_LOAD_KN_PER_SQM = {
    FloorType.STILT_PARKING: float(
        _LOADS["live_loads_by_floor_type"]["values"]["STILT_PARKING"]
    ),
    FloorType.RESIDENTIAL: float(
        _LOADS["live_loads_by_floor_type"]["values"]["RESIDENTIAL"]
    ),
    FloorType.TERRACE_ACCESSIBLE: float(
        _LOADS["live_loads_by_floor_type"]["values"]["TERRACE_ACCESSIBLE"]
    ),
    FloorType.TERRACE_INACCESSIBLE: float(
        _LOADS["live_loads_by_floor_type"]["values"]["TERRACE_INACCESSIBLE"]
    ),
    FloorType.BALCONY: float(
        _LOADS["live_loads_by_floor_type"]["values"]["BALCONY"]
    ),
    FloorType.STAIRCASE: float(
        _LOADS["live_loads_by_floor_type"]["values"]["STAIRCASE"]
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. CONCENTRATED LOADS — loaded from JSON
# ─────────────────────────────────────────────────────────────────────────────
OVERHEAD_WATER_TANK_LOAD_KN = float(
    _LOADS["concentrated_loads"]["overhead_water_tank"]["total_load_kn"]
)
OVERHEAD_WATER_TANK_AREA_SQM = float(
    _LOADS["concentrated_loads"]["overhead_water_tank"]["footprint_sqm"]
)
OVERHEAD_WATER_TANK_DISTRIBUTED_KN_PER_SQM = float(
    _LOADS["concentrated_loads"]["overhead_water_tank"]["distributed_kn_per_sqm"]
)


# ─────────────────────────────────────────────────────────────────────────────
# 4. WALL LOADS (IS 875 Part 1) — loaded from JSON
# ─────────────────────────────────────────────────────────────────────────────
WALL_LOAD_230MM_KN_PER_M = float(
    _LOADS["wall_loads"]["values"]["brick_230mm_3m_height_kn_per_m"]
)
WALL_LOAD_115MM_KN_PER_M = float(
    _LOADS["wall_loads"]["values"]["brick_115mm_3m_height_kn_per_m"]
)


# ─────────────────────────────────────────────────────────────────────────────
# 5. PARTIAL SAFETY FACTORS (IS 456 cl. 36.4) — loaded from JSON
# ─────────────────────────────────────────────────────────────────────────────
SAFETY_FACTORS = {
    k: float(v) for k, v in _LOADS["partial_safety_factors"]["values"].items()
}


# ─────────────────────────────────────────────────────────────────────────────
# 6. FLOOR LOAD CALCULATION
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class FloorLoad:
    """Load breakdown for one floor type."""
    floor_type: FloorType
    slab_thickness_mm: int
    dead_load_kn_per_sqm: float
    live_load_kn_per_sqm: float
    partition_load_kn_per_sqm: float
    total_unfactored_kn_per_sqm: float
    total_factored_kn_per_sqm: float     # With safety factors applied
    has_concentrated_load: bool = False
    concentrated_load_note: str = ""


def calculate_floor_load(
    floor_type: FloorType,
    slab_thickness_mm: int = 125,
    has_water_tank: bool = False,
) -> FloorLoad:
    """Calculate total design load per sqm for a floor type.

    Args:
        floor_type: What this floor is used for.
        slab_thickness_mm: Actual slab thickness (affects dead load).
        has_water_tank: True if this floor supports an overhead water tank.

    Returns:
        FloorLoad with unfactored (service) and factored (ultimate) loads.
    """
    # Dead load components
    slab_dead = SLAB_WEIGHT_KN_PER_SQM_PER_MM * slab_thickness_mm
    finishes = FINISHES_KN_PER_SQM

    # Partition walls (only on residential floors, not terrace/balcony)
    if floor_type == FloorType.RESIDENTIAL:
        partition = PARTITION_WALL_KN_PER_SQM
    else:
        partition = 0.0

    total_dead = slab_dead + finishes + partition

    # Live load from IS 875 Part 2
    live = LIVE_LOAD_KN_PER_SQM[floor_type]

    # Concentrated load addition (water tank on accessible terrace)
    concentrated_note = ""
    has_concentrated = False
    if has_water_tank and floor_type in (
        FloorType.TERRACE_ACCESSIBLE, FloorType.TERRACE_INACCESSIBLE
    ):
        has_concentrated = True
        concentrated_note = (
            f"Water tank: {OVERHEAD_WATER_TANK_LOAD_KN:.0f} kN concentrated "
            f"over {OVERHEAD_WATER_TANK_AREA_SQM:.1f} sqm. Columns directly "
            f"below tank carry extra load."
        )

    # Factored load per IS 456 cl. 36.4 (Limit State Design)
    factored = (
        SAFETY_FACTORS["dead_load"] * total_dead +
        SAFETY_FACTORS["live_load"] * live
    )

    return FloorLoad(
        floor_type=floor_type,
        slab_thickness_mm=slab_thickness_mm,
        dead_load_kn_per_sqm=round(total_dead, 2),
        live_load_kn_per_sqm=live,
        partition_load_kn_per_sqm=partition,
        total_unfactored_kn_per_sqm=round(total_dead + live, 2),
        total_factored_kn_per_sqm=round(factored, 2),
        has_concentrated_load=has_concentrated,
        concentrated_load_note=concentrated_note,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. COLUMN LOAD FROM STACKED FLOORS
# ─────────────────────────────────────────────────────────────────────────────
def calculate_column_axial_load_kn(
    tributary_area_sqm: float,
    floor_stack: list[FloorType],
    slab_thickness_mm: int = 125,
    has_water_tank_above: bool = False,
    is_water_tank_column: bool = False,
) -> dict:
    """Calculate axial load on a column from all floors above it.

    Args:
        tributary_area_sqm: bay_x × bay_y for an interior column.
        floor_stack: list of floor types supported by this column, from
                     top to bottom. E.g., for a column at stilt level in
                     a stilt+G+1+terrace building: [TERRACE, FF, GF, STILT].
        slab_thickness_mm: slab thickness (affects dead load).
        has_water_tank_above: is there a water tank on any floor above?
        is_water_tank_column: is THIS column directly below the tank?
                              (If yes, add concentrated load contribution.)

    Returns:
        dict with unfactored load, factored load, per-floor breakdown,
        and concentrated load contribution.
    """
    per_floor_loads_kn = []
    total_unfactored = 0.0
    total_factored = 0.0

    for floor_type in floor_stack:
        floor_load = calculate_floor_load(
            floor_type,
            slab_thickness_mm,
            has_water_tank=has_water_tank_above and floor_type in (
                FloorType.TERRACE_ACCESSIBLE, FloorType.TERRACE_INACCESSIBLE
            ),
        )
        floor_contribution_unfactored = (
            floor_load.total_unfactored_kn_per_sqm * tributary_area_sqm
        )
        floor_contribution_factored = (
            floor_load.total_factored_kn_per_sqm * tributary_area_sqm
        )
        total_unfactored += floor_contribution_unfactored
        total_factored += floor_contribution_factored
        per_floor_loads_kn.append({
            "floor_type": floor_type.value,
            "load_kn": round(floor_contribution_unfactored, 1),
            "factored_kn": round(floor_contribution_factored, 1),
        })

    # Water tank concentration (if this is the tank-supporting column)
    concentrated_contribution_kn = 0.0
    if is_water_tank_column:
        concentrated_contribution_kn = OVERHEAD_WATER_TANK_LOAD_KN
        total_unfactored += concentrated_contribution_kn
        total_factored += (
            SAFETY_FACTORS["dead_load"] * concentrated_contribution_kn
        )

    return {
        "total_unfactored_kn": round(total_unfactored, 1),
        "total_factored_kn": round(total_factored, 1),
        "per_floor_loads": per_floor_loads_kn,
        "concentrated_contribution_kn": concentrated_contribution_kn,
        "tributary_area_sqm": tributary_area_sqm,
        "safety_factors_applied": {
            "dead_load": SAFETY_FACTORS["dead_load"],
            "live_load": SAFETY_FACTORS["live_load"],
        },
    }
