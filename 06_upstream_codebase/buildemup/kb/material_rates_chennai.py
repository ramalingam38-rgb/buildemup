"""
BuildemUp† — Chennai 2026 Material Rates
==========================================

Real material and labour rates for Chennai construction in 2026.
Each rate has:
  - The price
  - The unit
  - The source (where we got it)
  - A typical variability range

Sources:
  - JSW/TATA steel published rates (Q1 2026)
  - Ramco/Ultratech cement dealer prices (Chennai region)
  - Local trade publications (Builder Magazine, India Construction Review)
  - Chennai contractor surveys (ranges across builders)

These rates are deliberately conservative-realistic. They will be
updated quarterly via a manual review (later: scraper).

Every cost output the engine produces traces back to a rate in this file.

†= placeholder name marker.

KB_VERSION: "Chennai_2026_Q2_v1"
"""
from __future__ import annotations

from buildemup.utils.rate_provider import RateProvider, MaterialRate


KB_VERSION = "Chennai_2026_Q2_v1"


# ─────────────────────────────────────────────────────────────────────────────
# 1. STRUCTURAL MATERIALS (RCC frame)
# ─────────────────────────────────────────────────────────────────────────────
RCC_MATERIALS = {
    "concrete_M20": MaterialRate(
        name="Ready-mix concrete",
        rate=6_800,
        unit="cum",
        source="Chennai RMC suppliers Q1 2026 (UltraTech, Lafarge)",
        variability_pct=4.0,
        grade="M20",
        is_code="IS 456",
        supplier_type="RMC plant",
    ),
    "concrete_M25": MaterialRate(
        name="Ready-mix concrete",
        rate=7_500,
        unit="cum",
        source="Chennai RMC suppliers Q1 2026",
        variability_pct=4.0,
        grade="M25",
        is_code="IS 456",
        supplier_type="RMC plant",
    ),
    "concrete_M30": MaterialRate(
        name="Ready-mix concrete",
        rate=8_400,
        unit="cum",
        source="Chennai RMC suppliers Q1 2026",
        variability_pct=4.0,
        grade="M30",
        is_code="IS 456",
        supplier_type="RMC plant",
    ),
    "steel_TMT_Fe500": MaterialRate(
        name="TMT bars",
        rate=72_000,
        unit="tonne",
        source="JSW/TATA Chennai dealer Q1 2026",
        variability_pct=8.0,
        notes="Steel rate fluctuates with international iron ore prices",
        brand="JSW or TATA Tiscon",
        grade="Fe500D",
        is_code="IS 1786",
        supplier_type="dealer",
    ),
    "shuttering_labour": MaterialRate(
        name="Shuttering + form labour",
        rate=420,
        unit="sqm",
        source="Chennai contractor average 2026",
        variability_pct=10.0,
        supplier_type="contractor",
    ),
    "structural_labour": MaterialRate(
        name="RCC casting labour (per cum)",
        rate=2_800,
        unit="cum",
        source="Chennai contractor average 2026",
        variability_pct=12.0,
        supplier_type="contractor",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. MASONRY
# ─────────────────────────────────────────────────────────────────────────────
MASONRY_MATERIALS = {
    "brick_red_clay": MaterialRate(
        name="Red clay bricks",
        rate=8.5,
        unit="brick",
        source="Chennai brick kilns 2026",
        variability_pct=10.0,
        is_code="IS 1077",
        supplier_type="dealer",
    ),
    "cement_OPC53": MaterialRate(
        name="Cement",
        rate=395,
        unit="bag",
        source="Chennai dealer Q1 2026",
        variability_pct=6.0,
        brand="Ramco or Ultratech",
        grade="OPC 53",
        is_code="IS 12269",
        supplier_type="dealer",
    ),
    "sand_river": MaterialRate(
        name="River sand (Manimuktha or similar)",
        rate=2_400,
        unit="cum",
        source="Chennai sand suppliers 2026",
        variability_pct=15.0,
        notes="Sand prices vary highly with monsoon, government regulation",
    ),
    "masonry_labour": MaterialRate(
        name="Brick masonry labour (incl. plastering)",
        rate=380,
        unit="sqm",  # of wall area
        source="Chennai contractor average",
        variability_pct=12.0,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. PLUMBING
# ─────────────────────────────────────────────────────────────────────────────
PLUMBING_MATERIALS = {
    "cpvc_pipe_15mm": MaterialRate(
        name="CPVC pipe 15mm (Astral/Supreme)",
        rate=145,
        unit="rmt",  # running metre
        source="Chennai plumbing dealer 2026",
    ),
    "cpvc_pipe_20mm": MaterialRate(
        name="CPVC pipe 20mm",
        rate=210,
        unit="rmt",
        source="Chennai plumbing dealer 2026",
    ),
    "pvc_drain_110mm": MaterialRate(
        name="PVC drain 110mm (4-inch main stack)",
        rate=320,
        unit="rmt",
        source="Chennai plumbing dealer 2026",
    ),
    "bathroom_set_jaquar_continental": MaterialRate(
        name="Bathroom set Jaquar Continental (full)",
        rate=30_000,
        unit="bathroom",
        source="Jaquar Continental Prime line 2026",
        variability_pct=15.0,
        notes="Includes basin, taps, shower, WC, accessories",
    ),
    "kitchen_sink_set": MaterialRate(
        name="Kitchen sink + tap (mid-tier stainless)",
        rate=8_500,
        unit="set",
        source="Hindware/Jaquar mid-tier 2026",
    ),
    "plumbing_labour": MaterialRate(
        name="Plumbing labour (per fixture point)",
        rate=850,
        unit="point",
        source="Chennai contractor average 2026",
        variability_pct=10.0,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# 4. ELECTRICAL
# ─────────────────────────────────────────────────────────────────────────────
ELECTRICAL_MATERIALS = {
    "wiring_per_point_basic": MaterialRate(
        name="Electrical point basic (light/switch/socket)",
        rate=750,
        unit="point",
        source="Chennai contractor 2026, Polycab/Havells wires",
        variability_pct=12.0,
    ),
    "wiring_per_point_AC": MaterialRate(
        name="AC point with 16A socket (heavy duty)",
        rate=2_200,
        unit="point",
        source="Chennai contractor 2026",
    ),
    "MCB_distribution_board": MaterialRate(
        name="MCB distribution board (8-way Havells)",
        rate=4_500,
        unit="board",
        source="Havells dealer 2026",
    ),
    "electrical_labour": MaterialRate(
        name="Electrical wiring labour",
        rate=85,
        unit="sqft",  # of built-up area
        source="Chennai contractor average 2026",
        variability_pct=10.0,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# 5. FINISHES
# ─────────────────────────────────────────────────────────────────────────────
FINISH_MATERIALS = {
    "vitrified_tile_mid": MaterialRate(
        name="Vitrified tile mid-tier (₹85 + laying)",
        rate=140,  # Material + laying
        unit="sqft",
        source="Chennai tile dealer + laying 2026",
        variability_pct=20.0,
        notes="Tile choice has biggest variability. Range ₹60-300/sqft.",
    ),
    "wall_paint_emulsion": MaterialRate(
        name="Emulsion paint (Asian Paints Premium)",
        rate=22,
        unit="sqft",  # incl. labour, primer, 2 coats
        source="Asian Paints + Chennai labour 2026",
    ),
    "door_flush_main": MaterialRate(
        name="Main door flush + frame (teakwood veneer)",
        rate=45_000,
        unit="door",
        source="Chennai carpentry 2026",
        variability_pct=20.0,
    ),
    "door_flush_internal": MaterialRate(
        name="Internal flush door + frame",
        rate=12_000,
        unit="door",
        source="Chennai carpentry 2026",
    ),
    "window_aluminium": MaterialRate(
        name="Aluminium sliding window (powder-coated)",
        rate=850,
        unit="sqft",
        source="Chennai aluminium fabricator 2026",
        variability_pct=15.0,
    ),
    "waterproofing_bath": MaterialRate(
        name="Bathroom waterproofing (Dr. Fixit)",
        rate=180,
        unit="sqft",
        source="Pidilite Chennai 2026",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# 6. CONTRACTOR MARGIN GUIDANCE
# ─────────────────────────────────────────────────────────────────────────────
CONTRACTOR_MARGIN_GUIDANCE = {
    "typical_low_pct": 8,
    "typical_avg_pct": 12,
    "typical_high_pct": 18,
    "premium_high_pct": 22,  # Branded contractors, smaller projects
    "default_for_estimate": 12,  # What we use for our cost estimates
    "notes": (
        "Contractor margin in Chennai residential typically ranges 8-18%. "
        "Smaller projects often see 12-18%. Larger projects 8-12%. "
        "Branded design-build firms charge 18-25%."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# 7. RATE PROVIDER (public API — use this, not get_rate directly)
# ─────────────────────────────────────────────────────────────────────────────
_CATALOG = {
    "rcc": RCC_MATERIALS,
    "masonry": MASONRY_MATERIALS,
    "plumbing": PLUMBING_MATERIALS,
    "electrical": ELECTRICAL_MATERIALS,
    "finish": FINISH_MATERIALS,
}


class ChennaiRateProvider(RateProvider):
    """Rate provider for Chennai. Implements RateProvider interface."""

    @property
    def city_name(self) -> str:
        return "Chennai"

    @property
    def kb_version(self) -> str:
        return KB_VERSION

    def get_rate(self, category: str, key: str) -> MaterialRate:
        if category not in _CATALOG:
            raise KeyError(
                f"Unknown material category: {category}. "
                f"Valid: {list(_CATALOG.keys())}"
            )
        if key not in _CATALOG[category]:
            raise KeyError(
                f"Unknown material key: '{key}' in category '{category}'. "
                f"Valid keys: {list(_CATALOG[category].keys())}"
            )
        return _CATALOG[category][key]

    def contractor_margin_range_pct(self) -> tuple[float, float]:
        return (
            CONTRACTOR_MARGIN_GUIDANCE["typical_low_pct"],
            CONTRACTOR_MARGIN_GUIDANCE["typical_high_pct"],
        )

    def contractor_margin_default_pct(self) -> float:
        return CONTRACTOR_MARGIN_GUIDANCE["default_for_estimate"]


# Backwards compatibility: keep the free function for tests
def get_rate(category: str, key: str) -> MaterialRate:
    """Look up a material rate by category and key (legacy helper)."""
    provider = ChennaiRateProvider()
    return provider.get_rate(category, key)
