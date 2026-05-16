"""
BuildemUp† — IS 456:2000 RCC Design Rules
==========================================

Knowledge module encoding Reinforced Cement Concrete design rules
for Indian residential buildings, primarily from:
  - IS 456:2000 — Plain & Reinforced Concrete Code of Practice
  - IS 875 (Part 1, 2, 3) — Design loads
  - IS 1893 (Part 1):2016 — Seismic design
  - Devdas Menon, "Structural Analysis" — practical span/depth ratios
  - Punmia, "Reinforced Concrete Structures" — column design

This module contains:
  - Preferred column grid bay sizes
  - Column sizing rules by floor count + seismic zone
  - Beam depth from span (Devdas Menon span/depth = 12)
  - Slab thickness from span (IS 456 cl. 23.2.1)
  - Concrete grade selection
  - Material quantity estimation factors

Every rule cites its source so users can verify.

†= placeholder name marker.

KB_VERSION: "RCC_India_IS456_2026_v1"
"""
from __future__ import annotations
from dataclasses import dataclass


KB_VERSION = "RCC_India_IS456_2026_v1"


# ─────────────────────────────────────────────────────────────────────────────
# 1. PREFERRED BAY SIZES (Devdas Menon + practical Indian residential)
# ─────────────────────────────────────────────────────────────────────────────
# Why these specific sizes:
#   - 2.7m: minimum for furniture-fit in habitable rooms
#   - 3.0m: most economical for G+1, smallest steel/concrete usage
#   - 3.3m, 3.6m: typical for medium Indian family homes
#   - 4.0m, 4.5m: larger rooms, requires deeper beams
#   - >5m: requires special design, not typical residential
PREFERRED_BAY_SIZES_M = [2.7, 3.0, 3.3, 3.6, 4.0, 4.5, 5.0]

# Maximum span for residential RCC without special design (IS 456 + practical)
MAX_RESIDENTIAL_SPAN_M = 5.0

# Minimum span (below this, the room can't fit furniture per Neufert)
MIN_RESIDENTIAL_SPAN_M = 2.7


# ─────────────────────────────────────────────────────────────────────────────
# 2. COLUMN SIZING RULES (IS 456 cl. 26.5.3.1 + practical Indian residential)
# ─────────────────────────────────────────────────────────────────────────────
# Source: IS 456:2000 cl. 26.5.3.1 — minimum column dimension 200mm.
# Practical: 230mm minimum (matches 9" brick wall — wall hides column).
# For multi-storey, column size grows with floor count due to higher loads.
@dataclass(frozen=True)
class ColumnSpec:
    """One column sizing rule for a given floor configuration."""
    floors_above_ground: int      # 0 = G only, 1 = G+1, etc.
    min_dim_mm: int               # IS 456 minimum (regulatory)
    typical_dim_mm: int           # Practical Indian residential
    typical_steel_pct: float      # Longitudinal steel as % of concrete area
    note: str
    source: str


COLUMN_RULES = [
    ColumnSpec(
        floors_above_ground=0,
        min_dim_mm=200,
        typical_dim_mm=230,
        typical_steel_pct=0.8,
        note="G only — 230x230 matches 9-inch wall, hides column in wall",
        source="IS 456:2000 cl. 26.5.3.1 + Punmia Ch. 13",
    ),
    ColumnSpec(
        floors_above_ground=1,
        min_dim_mm=230,
        typical_dim_mm=230,
        typical_steel_pct=1.0,
        note="G+1 — 230x230 sufficient for typical residential bay 3-3.6m",
        source="IS 456:2000 + Devdas Menon Ch. 11",
    ),
    ColumnSpec(
        floors_above_ground=2,
        min_dim_mm=230,
        typical_dim_mm=300,
        typical_steel_pct=1.2,
        note="G+2 — 300x300 standard. Some use 230x300 rectangular",
        source="IS 456:2000 + Punmia",
    ),
    ColumnSpec(
        floors_above_ground=3,
        min_dim_mm=300,
        typical_dim_mm=350,
        typical_steel_pct=1.5,
        note="G+3 — 350x350 or 300x450 rectangular",
        source="IS 456:2000",
    ),
    ColumnSpec(
        floors_above_ground=4,
        min_dim_mm=350,
        typical_dim_mm=450,
        typical_steel_pct=2.0,
        note="G+4 — 450x450, requires detailed seismic design",
        source="IS 456:2000 + IS 1893:2016",
    ),
]


# Seismic zone modifier per IS 1893:2016
# Seismic Zone V (highest) needs +50mm column dim, Zone IV +25mm.
SEISMIC_ZONE_MODIFIERS_MM = {
    "II": 0,    # Most of South India incl. Chennai — low seismic
    "III": 0,   # Mumbai, Delhi, Pune — moderate
    "IV": 25,   # Patna, Srinagar — high
    "V": 50,    # Bhuj, NE India — very high
}


def select_column_spec(floors_above_ground: int, seismic_zone: str = "II") -> ColumnSpec:
    """Pick the right column rule for the building.

    Args:
        floors_above_ground: 0 for G only, 1 for G+1, etc.
        seismic_zone: 'II', 'III', 'IV', 'V' per IS 1893.

    Returns:
        ColumnSpec with typical dimensions adjusted for seismic zone.

    Raises:
        ValueError if floor count out of supported range (>4).
    """
    if floors_above_ground < 0 or floors_above_ground > 4:
        raise ValueError(
            f"Floors above ground must be 0-4 (G to G+4). "
            f"Got {floors_above_ground}. "
            f"For taller buildings, custom structural design is required."
        )

    base = next(c for c in COLUMN_RULES if c.floors_above_ground == floors_above_ground)
    seismic_add = SEISMIC_ZONE_MODIFIERS_MM.get(seismic_zone, 0)

    if seismic_add == 0:
        return base

    # Return a new spec with seismic adjustment
    return ColumnSpec(
        floors_above_ground=base.floors_above_ground,
        min_dim_mm=base.min_dim_mm + seismic_add,
        typical_dim_mm=base.typical_dim_mm + seismic_add,
        typical_steel_pct=base.typical_steel_pct + 0.2,  # Higher confinement steel
        note=f"{base.note} (+{seismic_add}mm for Zone {seismic_zone})",
        source=f"{base.source} + IS 1893:2016",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. BEAM DEPTH FROM SPAN (Devdas Menon span/depth = 12)
# ─────────────────────────────────────────────────────────────────────────────
# Rule: depth = span / 12 (rounded up to nearest 50mm), with minimum 300mm.
# Width: typically same as column dimension (so beam fits flush).
# Source: Devdas Menon "Structural Analysis" + Punmia Ch. 14.

BEAM_SPAN_TO_DEPTH_RATIO = 12  # Conservative for residential simply-supported beams
BEAM_MIN_DEPTH_MM = 300        # Practical minimum to accommodate reinforcement
BEAM_MIN_WIDTH_MM = 230        # Matches 9" brick wall


def calculate_beam_depth_mm(span_m: float) -> int:
    """Calculate beam depth for a given span.

    Returns depth in mm, rounded up to nearest 50mm increment.
    Always at least BEAM_MIN_DEPTH_MM (300mm).
    """
    if span_m <= 0:
        raise ValueError(f"Span must be positive, got {span_m}m")
    if span_m > MAX_RESIDENTIAL_SPAN_M:
        raise ValueError(
            f"Span {span_m}m exceeds residential maximum {MAX_RESIDENTIAL_SPAN_M}m. "
            f"Custom structural design required."
        )

    raw_depth_mm = (span_m * 1000) / BEAM_SPAN_TO_DEPTH_RATIO
    # Round up to nearest 50mm
    rounded_depth_mm = int(((raw_depth_mm + 49) // 50) * 50)
    return max(rounded_depth_mm, BEAM_MIN_DEPTH_MM)


# ─────────────────────────────────────────────────────────────────────────────
# 4. SLAB THICKNESS FROM SPAN (IS 456 cl. 23.2.1)
# ─────────────────────────────────────────────────────────────────────────────
# IS 456 cl. 23.2.1: For simply supported one-way slab, span/depth ≤ 20.
# For two-way slab, span/depth ≤ 30 to 40.
# Practical Indian residential: 120mm minimum, 150mm typical.

SLAB_ONE_WAY_SPAN_TO_DEPTH = 20
SLAB_TWO_WAY_SPAN_TO_DEPTH = 32  # Conservative middle of 30-40 range
SLAB_MIN_THICKNESS_MM = 120


def calculate_slab_thickness_mm(longer_span_m: float, is_two_way: bool = True) -> int:
    """Calculate slab thickness based on the longer span of the panel.

    Args:
        longer_span_m: longer dimension of the slab panel (clear span).
        is_two_way: True if both directions span similar (common in residential).

    Returns thickness in mm, rounded up to nearest 25mm.
    """
    ratio = SLAB_TWO_WAY_SPAN_TO_DEPTH if is_two_way else SLAB_ONE_WAY_SPAN_TO_DEPTH
    raw_mm = (longer_span_m * 1000) / ratio
    # Round up to nearest 25mm
    rounded_mm = int(((raw_mm + 24) // 25) * 25)
    return max(rounded_mm, SLAB_MIN_THICKNESS_MM)


# ─────────────────────────────────────────────────────────────────────────────
# 5. CONCRETE GRADE SELECTION (IS 456 cl. 6.1)
# ─────────────────────────────────────────────────────────────────────────────
# IS 456 cl. 6.1.2: minimum grade for RCC = M20 (20 N/mm² characteristic strength).
# Higher floors / larger spans need stronger concrete.

def select_concrete_grade(floors_above_ground: int, seismic_zone: str = "II") -> str:
    """Pick concrete grade for the structure.

    Returns grade string like 'M20', 'M25', 'M30'.
    """
    if floors_above_ground <= 1:
        # G or G+1: M20 sufficient
        return "M25" if seismic_zone in ("IV", "V") else "M20"
    elif floors_above_ground <= 3:
        # G+2 or G+3: M25 standard
        return "M30" if seismic_zone in ("IV", "V") else "M25"
    else:
        # G+4: M30 minimum
        return "M30"


# ─────────────────────────────────────────────────────────────────────────────
# 6. MATERIAL QUANTITIES (industry rules of thumb, calibrated to practice)
# ─────────────────────────────────────────────────────────────────────────────
# These are rules of thumb for ESTIMATION at the schematic stage.
# Detailed structural design will produce more accurate quantities.

# Concrete volume per floor area (cum per sqm of built-up area)
# Source: Punmia + practical residential averages
CONCRETE_PER_SQM_FLOOR_AREA_CUM = {
    "G_only":    0.10,   # Just GF slab, beams, footings, columns
    "G+1":       0.13,   # Adds intermediate slab + larger columns
    "G+2":       0.15,
    "G+3":       0.17,
    "G+4":       0.19,
}

# Steel quantity per cubic metre of concrete (kg/cum)
# Source: Punmia Ch. 13, IS 456 average reinforcement levels
STEEL_KG_PER_CUM_CONCRETE = {
    "footings":  60,    # Light reinforcement
    "columns":   180,   # Heavy longitudinal + ties
    "beams":     150,   # Bottom + top + stirrups
    "slabs":     90,    # Two-layer mesh
    "average":   100,   # Weighted average for rough estimation
}

# Foundation volume as % of total concrete (typical for isolated footings on good soil)
FOUNDATION_CONCRETE_PCT_OF_TOTAL = 0.20


def estimate_concrete_volume_cum(floor_area_sqm: float, floors_above_ground: int) -> float:
    """Estimate total concrete volume for the structure.

    Includes footings, columns, beams, slabs across all floors.
    """
    floors_key = "G_only" if floors_above_ground == 0 else f"G+{floors_above_ground}"
    rate = CONCRETE_PER_SQM_FLOOR_AREA_CUM.get(floors_key, 0.13)
    total_floor_area = floor_area_sqm * (floors_above_ground + 1)
    return total_floor_area * rate


def estimate_steel_tonnes(concrete_volume_cum: float) -> float:
    """Estimate total steel quantity in tonnes."""
    avg_kg_per_cum = STEEL_KG_PER_CUM_CONCRETE["average"]
    total_kg = concrete_volume_cum * avg_kg_per_cum
    return total_kg / 1000.0


# ─────────────────────────────────────────────────────────────────────────────
# 7. CITATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────
# Used by component output to show users WHERE rules come from
CITATIONS = {
    "IS_456": "IS 456:2000 — Plain & Reinforced Concrete Code of Practice",
    "IS_875_1": "IS 875 (Part 1):1987 — Dead loads",
    "IS_875_2": "IS 875 (Part 2):1987 — Imposed loads",
    "IS_1893": "IS 1893 (Part 1):2016 — Criteria for Earthquake Resistant Design",
    "DEVDAS_MENON": "Devdas Menon — Structural Analysis (Narosa Publishing)",
    "PUNMIA": "B.C. Punmia — Reinforced Concrete Structures (Laxmi Publications)",
    "NBC_2016_PART_4": "NBC 2016 Part 4 — Fire and Life Safety",
    "NBC_2016_PART_6": "NBC 2016 Part 6 — Structural Design",
}
