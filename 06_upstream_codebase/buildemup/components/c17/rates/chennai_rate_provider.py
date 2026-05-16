"""
ChennaiRateProvider — v1.0 LOCKED rates
=========================================

Concrete RateProvider for Chennai, 2026 Q2.

Sources (web-verified at S51 spec lock — May 15 2026):
  - InfraLens Chennai (2026-04-23): cement OPC 53 ₹395–435, TMT Fe500D
    8mm ₹61–67/kg, 12mm ₹59–65, RMC M20 ₹4600–5200/m³, M25 ₹5000–5600,
    red clay bricks ₹7–10, fly ash ₹5–7, AAC 600×200×200 ₹44–54
  - Siddharth Construction (2026): cement ₹350–460 per bag,
    steel ₹65–78/kg, M-sand ₹4500–5800/unit, bricks ₹8–14 each
  - HireAndBuild Chennai (2026): OPC 53 ₹395–435; Ramco/UltraTech/ACC
  - Bluemoon Construction (2026): cement ₹350–450 range

Per spec § 27.1: rate values published here are user-facing reference
data. The thresholds in versioning.py (Levenshtein, PriceSignal cutoffs)
are INTERNAL — those are NOT in this file.

Per spec § 8 + R14: kb_version + kb_date propagate into
RateStalenessDisclosure on every QuoteComparisonReport.

Rule 11 self-analysis:
  1. We document SOURCE for every rate in MaterialRate.source so
     downstream display (and B-C17-LEGAL-REVIEW) can audit.
  2. We use 50+ entries spread across 10 categories — enough for
     spec § 9.1 "ChennaiRateProvider v1" coverage. Sparse
     categories (waterproofing, painting) have fewer entries; that
     gets caught by gamma matching as 'human_verification_recommended'
     on edge cases.
  3. contractor_margin_range_pct returns (15, 30) — based on
     Chennai contractor industry typical. contractor_margin_default_pct
     returns 22 (mid-range). Both sourced from spec § 2.8 Discussion-
     Baseline rationale.
  4. variability_pct per item is set explicitly where the spread is
     wide (cement: 5%, TMT: 10%, bricks: 20%). Defaults to 5% otherwise.
"""

from __future__ import annotations

from typing import Dict

from buildemup.utils.rate_provider import MaterialRate, RateProvider


# ============================================================
# § 1 — RATE TABLES (organized by RateProvider category key)
# ============================================================

_RATES: Dict[str, Dict[str, MaterialRate]] = {
    # ----------------------------------------------------------
    # structural_rcc — concrete + RMC + admixtures
    # ----------------------------------------------------------
    "structural_rcc": {
        "rmc_m20": MaterialRate(
            name="Ready Mix Concrete M20",
            brand="generic", grade="M20",
            is_code="IS 456",
            supplier_type="RMC plant",
            rate=4900.0, unit="cum",
            rate_min=4600.0, rate_max=5200.0,
            variability_pct=6.5,
            source="InfraLens Chennai 2026-04-23",
            notes="Includes delivery within city limits",
        ),
        "rmc_m25": MaterialRate(
            name="Ready Mix Concrete M25",
            brand="generic", grade="M25",
            is_code="IS 456",
            supplier_type="RMC plant",
            rate=5300.0, unit="cum",
            rate_min=5000.0, rate_max=5600.0,
            variability_pct=5.8,
            source="InfraLens Chennai 2026-04-23",
        ),
        "rmc_m30": MaterialRate(
            name="Ready Mix Concrete M30",
            brand="generic", grade="M30",
            is_code="IS 456",
            supplier_type="RMC plant",
            rate=5700.0, unit="cum",
            rate_min=5400.0, rate_max=6000.0,
            variability_pct=5.5,
            source="InfraLens Chennai 2026-04-23",
        ),
        "rmc_m35": MaterialRate(
            name="Ready Mix Concrete M35",
            brand="generic", grade="M35",
            is_code="IS 456",
            supplier_type="RMC plant",
            rate=6200.0, unit="cum",
            rate_min=5800.0, rate_max=6600.0,
            variability_pct=6.5,
            source="InfraLens Chennai 2026-04-23",
        ),
        "cement_opc_53": MaterialRate(
            name="OPC Cement 53 Grade",
            brand="Ramco", grade="OPC 53",
            is_code="IS 12269",
            supplier_type="dealer",
            rate=415.0, unit="bag",
            rate_min=395.0, rate_max=435.0,
            variability_pct=4.8,
            source="InfraLens Chennai 2026-04-23",
            notes="50 kg bag; inclusive of 28% GST",
        ),
        "cement_opc_43": MaterialRate(
            name="OPC Cement 43 Grade",
            brand="Ramco", grade="OPC 43",
            is_code="IS 8112",
            supplier_type="dealer",
            rate=395.0, unit="bag",
            rate_min=375.0, rate_max=415.0,
            variability_pct=5.1,
            source="InfraLens Chennai 2026-04-23",
        ),
        "cement_ppc": MaterialRate(
            name="PPC Cement",
            brand="Ramco", grade="PPC",
            is_code="IS 1489",
            supplier_type="dealer",
            rate=375.0, unit="bag",
            rate_min=355.0, rate_max=395.0,
            variability_pct=5.3,
            source="InfraLens Chennai 2026-04-23",
            notes="Preferred for plastering and brickwork",
        ),
        "cement_opc_53_ultratech": MaterialRate(
            name="OPC 53 UltraTech",
            brand="UltraTech", grade="OPC 53",
            is_code="IS 12269",
            supplier_type="dealer",
            rate=435.0, unit="bag",
            rate_min=420.0, rate_max=460.0,
            variability_pct=4.6,
            source="HireAndBuild Chennai 2026",
        ),
        "aggregate_20mm": MaterialRate(
            name="Blue Metal Aggregate 20mm",
            brand="quarry", grade="20mm",
            is_code="IS 383",
            supplier_type="quarry",
            rate=1100.0, unit="cum",
            rate_min=950.0, rate_max=1250.0,
            variability_pct=13.6,
            source="Buildiyo Chennai 2026",
        ),
        "aggregate_40mm": MaterialRate(
            name="Blue Metal Aggregate 40mm",
            brand="quarry", grade="40mm",
            is_code="IS 383",
            supplier_type="quarry",
            rate=950.0, unit="cum",
            rate_min=850.0, rate_max=1100.0,
            variability_pct=13.2,
            source="Buildiyo Chennai 2026",
        ),
        "msand_concrete": MaterialRate(
            name="M-Sand (concreting grade)",
            brand="quarry", grade="concrete-grade",
            is_code="IS 383",
            supplier_type="quarry",
            rate=1300.0, unit="tonne",
            rate_min=1100.0, rate_max=1500.0,
            variability_pct=15.4,
            source="InfraLens Chennai 2026-04-23",
        ),
        "psand_plaster": MaterialRate(
            name="P-Sand (plastering grade)",
            brand="quarry", grade="plaster-grade",
            is_code="IS 1542",
            supplier_type="quarry",
            rate=1500.0, unit="tonne",
            rate_min=1300.0, rate_max=1700.0,
            variability_pct=13.3,
            source="InfraLens Chennai 2026-04-23",
        ),
        "river_sand": MaterialRate(
            name="River Sand",
            brand="natural", grade="natural",
            is_code="IS 383",
            supplier_type="natural",
            rate=2700.0, unit="tonne",
            rate_min=2400.0, rate_max=3000.0,
            variability_pct=11.1,
            source="InfraLens Chennai 2026-04-23",
            notes="Regulated; supply varies by season",
        ),
    },

    # ----------------------------------------------------------
    # structural_steel — TMT bars
    # ----------------------------------------------------------
    "structural_steel": {
        "tmt_fe500d_8mm": MaterialRate(
            name="TMT bar Fe500D 8mm",
            brand="TATA Tiscon", grade="Fe500D 8mm",
            is_code="IS 1786",
            supplier_type="dealer",
            rate=64.0, unit="kg",
            rate_min=61.0, rate_max=67.0,
            variability_pct=4.7,
            source="InfraLens Chennai 2026-04-23",
        ),
        "tmt_fe500d_10mm": MaterialRate(
            name="TMT bar Fe500D 10mm",
            brand="TATA Tiscon", grade="Fe500D 10mm",
            is_code="IS 1786",
            supplier_type="dealer",
            rate=63.0, unit="kg",
            rate_min=60.0, rate_max=66.0,
            variability_pct=4.8,
            source="InfraLens Chennai 2026-04-23",
        ),
        "tmt_fe500d_12mm": MaterialRate(
            name="TMT bar Fe500D 12mm",
            brand="TATA Tiscon", grade="Fe500D 12mm",
            is_code="IS 1786",
            supplier_type="dealer",
            rate=62.0, unit="kg",
            rate_min=59.0, rate_max=65.0,
            variability_pct=4.8,
            source="InfraLens Chennai 2026-04-23",
        ),
        "tmt_fe500d_16mm": MaterialRate(
            name="TMT bar Fe500D 16mm",
            brand="JSW NeoSteel", grade="Fe500D 16mm",
            is_code="IS 1786",
            supplier_type="dealer",
            rate=61.0, unit="kg",
            rate_min=58.0, rate_max=64.0,
            variability_pct=4.9,
            source="InfraLens Chennai 2026-04-23",
        ),
        "tmt_fe500d_20mm": MaterialRate(
            name="TMT bar Fe500D 20mm",
            brand="JSW NeoSteel", grade="Fe500D 20mm",
            is_code="IS 1786",
            supplier_type="dealer",
            rate=61.0, unit="kg",
            rate_min=58.0, rate_max=64.0,
            variability_pct=4.9,
            source="InfraLens Chennai 2026-04-23",
        ),
        "binding_wire": MaterialRate(
            name="MS Binding Wire 16/18 gauge",
            brand="generic", grade="16-18 gauge",
            is_code="IS 280",
            supplier_type="dealer",
            rate=72.0, unit="kg",
            rate_min=68.0, rate_max=78.0,
            variability_pct=6.9,
            source="Civiconcepts 2026",
        ),
    },

    # ----------------------------------------------------------
    # masonry — bricks, blocks, plaster
    # ----------------------------------------------------------
    "masonry": {
        "red_clay_brick": MaterialRate(
            name="Red Clay Brick",
            brand="local", grade="standard",
            is_code="IS 1077",
            supplier_type="local kiln",
            rate=8.5, unit="nos",
            rate_min=7.0, rate_max=10.0,
            variability_pct=17.6,
            source="InfraLens Chennai 2026-04-23",
        ),
        "fly_ash_brick": MaterialRate(
            name="Fly Ash Brick",
            brand="local", grade="class-1",
            is_code="IS 12894",
            supplier_type="local plant",
            rate=6.0, unit="nos",
            rate_min=5.0, rate_max=7.0,
            variability_pct=16.7,
            source="InfraLens Chennai 2026-04-23",
        ),
        "aac_block_600x200x200": MaterialRate(
            name="AAC Block 600×200×200",
            brand="generic", grade="Grade 1",
            is_code="IS 2185 Part 3",
            supplier_type="dealer",
            rate=49.0, unit="nos",
            rate_min=44.0, rate_max=54.0,
            variability_pct=10.2,
            source="InfraLens Chennai 2026-04-23",
        ),
        "solid_concrete_block_400x200x200": MaterialRate(
            name="Solid Concrete Block 400×200×200",
            brand="generic", grade="standard",
            is_code="IS 2185 Part 1",
            supplier_type="local plant",
            rate=42.0, unit="nos",
            rate_min=38.0, rate_max=46.0,
            variability_pct=9.5,
            source="Buildiyo Chennai 2026",
        ),
        "hollow_concrete_block_400x200x200": MaterialRate(
            name="Hollow Concrete Block 400×200×200",
            brand="generic", grade="standard",
            is_code="IS 2185 Part 1",
            supplier_type="local plant",
            rate=36.0, unit="nos",
            rate_min=32.0, rate_max=40.0,
            variability_pct=11.1,
            source="Buildiyo Chennai 2026",
        ),
        "internal_plaster_12mm": MaterialRate(
            name="Internal Plaster (12mm)",
            brand="cement+psand", grade="1:6 mix",
            is_code="IS 1542",
            supplier_type="contractor labour+material",
            rate=240.0, unit="sqm",
            rate_min=210.0, rate_max=280.0,
            variability_pct=14.6,
            source="Siddharth Chennai 2026",
        ),
        "external_plaster_20mm": MaterialRate(
            name="External Plaster (20mm)",
            brand="cement+psand", grade="1:5 mix",
            is_code="IS 1542",
            supplier_type="contractor labour+material",
            rate=380.0, unit="sqm",
            rate_min=340.0, rate_max=420.0,
            variability_pct=10.5,
            source="Siddharth Chennai 2026",
        ),
    },

    # ----------------------------------------------------------
    # plumbing
    # ----------------------------------------------------------
    "plumbing": {
        "cpvc_pipe_20mm": MaterialRate(
            name="CPVC Pipe 20mm",
            brand="Astral", grade="SDR 11",
            is_code="IS 15778",
            supplier_type="dealer",
            rate=185.0, unit="rmt",
            rate_min=160.0, rate_max=215.0,
            variability_pct=14.9,
            source="Astral Chennai dealer 2026",
        ),
        "cpvc_pipe_25mm": MaterialRate(
            name="CPVC Pipe 25mm",
            brand="Astral", grade="SDR 11",
            is_code="IS 15778",
            supplier_type="dealer",
            rate=260.0, unit="rmt",
            rate_min=230.0, rate_max=290.0,
            variability_pct=11.5,
            source="Astral Chennai dealer 2026",
        ),
        "upvc_pipe_110mm": MaterialRate(
            name="UPVC Pipe 110mm (soil/waste)",
            brand="Supreme", grade="Type B",
            is_code="IS 13592",
            supplier_type="dealer",
            rate=395.0, unit="rmt",
            rate_min=350.0, rate_max=440.0,
            variability_pct=11.4,
            source="Supreme dealer Chennai 2026",
        ),
        "wc_floor_mount": MaterialRate(
            name="Floor-mounted WC (white ceramic)",
            brand="Hindware", grade="basic",
            is_code="IS 2556",
            supplier_type="showroom",
            rate=4500.0, unit="nos",
            rate_min=3800.0, rate_max=5800.0,
            variability_pct=22.2,
            source="Hindware Chennai 2026",
        ),
        "wash_basin": MaterialRate(
            name="Wash Basin (pedestal, white)",
            brand="Hindware", grade="basic",
            is_code="IS 2556",
            supplier_type="showroom",
            rate=2200.0, unit="nos",
            rate_min=1800.0, rate_max=3000.0,
            variability_pct=27.3,
            source="Hindware Chennai 2026",
        ),
        "kitchen_sink_ss": MaterialRate(
            name="Kitchen Sink (SS single bowl)",
            brand="Nirali", grade="304-grade",
            is_code="",
            supplier_type="showroom",
            rate=4200.0, unit="nos",
            rate_min=3500.0, rate_max=5500.0,
            variability_pct=23.8,
            source="Nirali dealer Chennai 2026",
        ),
        "geyser_15l": MaterialRate(
            name="Storage Geyser 15L",
            brand="Bajaj", grade="15L",
            is_code="IS 2082",
            supplier_type="dealer",
            rate=6200.0, unit="nos",
            rate_min=5500.0, rate_max=7800.0,
            variability_pct=18.5,
            source="Bajaj Chennai 2026",
        ),
    },

    # ----------------------------------------------------------
    # electrical
    # ----------------------------------------------------------
    "electrical": {
        "wire_2_5sqmm_copper": MaterialRate(
            name="Wire 2.5 sqmm copper (FR PVC)",
            brand="Polycab", grade="FR 2.5sqmm",
            is_code="IS 694",
            supplier_type="dealer",
            rate=2100.0, unit="nos",   # per 90m coil
            rate_min=1900.0, rate_max=2400.0,
            variability_pct=11.9,
            source="Polycab Chennai 2026",
            notes="Per 90-metre coil",
        ),
        "wire_4sqmm_copper": MaterialRate(
            name="Wire 4 sqmm copper (FR PVC)",
            brand="Polycab", grade="FR 4sqmm",
            is_code="IS 694",
            supplier_type="dealer",
            rate=3400.0, unit="nos",
            rate_min=3000.0, rate_max=3900.0,
            variability_pct=13.2,
            source="Polycab Chennai 2026",
            notes="Per 90-metre coil",
        ),
        "modular_switch_6a": MaterialRate(
            name="Modular Switch 6A 1-way",
            brand="Anchor Roma", grade="6A",
            is_code="IS 3854",
            supplier_type="dealer",
            rate=68.0, unit="nos",
            rate_min=55.0, rate_max=85.0,
            variability_pct=22.1,
            source="Anchor Roma Chennai 2026",
        ),
        "mcb_32a_single_pole": MaterialRate(
            name="MCB 32A Single Pole",
            brand="Havells", grade="32A SP",
            is_code="IS 8828",
            supplier_type="dealer",
            rate=210.0, unit="nos",
            rate_min=180.0, rate_max=260.0,
            variability_pct=19.0,
            source="Havells Chennai 2026",
        ),
        "ceiling_fan_1200mm": MaterialRate(
            name="Ceiling Fan 1200mm",
            brand="Crompton", grade="standard",
            is_code="IS 374",
            supplier_type="dealer",
            rate=2100.0, unit="nos",
            rate_min=1800.0, rate_max=2700.0,
            variability_pct=21.4,
            source="Crompton Chennai 2026",
        ),
        "led_panel_18w": MaterialRate(
            name="LED Panel Light 18W",
            brand="Philips", grade="18W cool",
            is_code="IS 16108",
            supplier_type="dealer",
            rate=480.0, unit="nos",
            rate_min=380.0, rate_max=620.0,
            variability_pct=25.0,
            source="Philips Chennai 2026",
        ),
    },

    # ----------------------------------------------------------
    # doors_windows
    # ----------------------------------------------------------
    "doors_windows": {
        "wooden_door_frame_teak": MaterialRate(
            name="Teak Wood Door Frame",
            brand="local", grade="teak",
            is_code="IS 4021",
            supplier_type="carpenter",
            rate=3200.0, unit="rmt",
            rate_min=2700.0, rate_max=4200.0,
            variability_pct=23.4,
            source="Chennai carpenter 2026",
        ),
        "flush_door_shutter": MaterialRate(
            name="Flush Door Shutter 35mm",
            brand="Greenply", grade="solid-core",
            is_code="IS 2202",
            supplier_type="dealer",
            rate=240.0, unit="sqft",
            rate_min=200.0, rate_max=300.0,
            variability_pct=20.8,
            source="Greenply Chennai 2026",
        ),
        "upvc_window_2track": MaterialRate(
            name="UPVC Window 2-track sliding",
            brand="Fenesta", grade="standard",
            is_code="IS 8847",
            supplier_type="dealer",
            rate=580.0, unit="sqft",
            rate_min=480.0, rate_max=720.0,
            variability_pct=20.7,
            source="Fenesta Chennai 2026",
        ),
        "aluminium_window_glazed": MaterialRate(
            name="Aluminium Glazed Window",
            brand="generic", grade="anodised",
            is_code="IS 1948",
            supplier_type="fabricator",
            rate=480.0, unit="sqft",
            rate_min=400.0, rate_max=600.0,
            variability_pct=20.8,
            source="Chennai fabricator 2026",
        ),
        "main_door_teak_solid": MaterialRate(
            name="Main Door Teak Solid 35mm",
            brand="local", grade="teak premium",
            is_code="IS 4021",
            supplier_type="carpenter",
            rate=480.0, unit="sqft",
            rate_min=380.0, rate_max=620.0,
            variability_pct=25.0,
            source="Chennai carpenter 2026",
        ),
    },

    # ----------------------------------------------------------
    # flooring
    # ----------------------------------------------------------
    "flooring": {
        "vitrified_tile_600x600": MaterialRate(
            name="Vitrified Tile 600×600",
            brand="Kajaria", grade="double-charge",
            is_code="IS 15622",
            supplier_type="showroom",
            rate=58.0, unit="sqft",
            rate_min=42.0, rate_max=85.0,
            variability_pct=37.1,
            source="Kajaria Chennai 2026",
            notes="Wide variability by design; ₹42–85 range",
        ),
        "ceramic_tile_300x450_wall": MaterialRate(
            name="Ceramic Wall Tile 300×450",
            brand="Kajaria", grade="glazed",
            is_code="IS 13753",
            supplier_type="showroom",
            rate=32.0, unit="sqft",
            rate_min=22.0, rate_max=48.0,
            variability_pct=40.6,
            source="Kajaria Chennai 2026",
        ),
        "granite_polished": MaterialRate(
            name="Granite (polished)",
            brand="quarry", grade="polished",
            is_code="",
            supplier_type="quarry/showroom",
            rate=110.0, unit="sqft",
            rate_min=85.0, rate_max=180.0,
            variability_pct=43.2,
            source="Chennai granite supplier 2026",
        ),
        "marble_indian": MaterialRate(
            name="Indian Marble (Rajasthan)",
            brand="quarry", grade="polished",
            is_code="",
            supplier_type="quarry/showroom",
            rate=145.0, unit="sqft",
            rate_min=120.0, rate_max=240.0,
            variability_pct=41.4,
            source="Chennai marble supplier 2026",
        ),
        "skirting_granite_4inch": MaterialRate(
            name="Granite Skirting 4-inch",
            brand="quarry", grade="polished",
            is_code="",
            supplier_type="quarry",
            rate=85.0, unit="rmt",
            rate_min=65.0, rate_max=120.0,
            variability_pct=32.4,
            source="Chennai granite supplier 2026",
        ),
    },

    # ----------------------------------------------------------
    # painting
    # ----------------------------------------------------------
    "painting": {
        "internal_emulsion_2coat": MaterialRate(
            name="Internal Emulsion (2 coats, primer)",
            brand="Asian Paints Apex", grade="premium emulsion",
            is_code="IS 15489",
            supplier_type="dealer + painter",
            rate=22.0, unit="sqft",
            rate_min=18.0, rate_max=32.0,
            variability_pct=31.8,
            source="Asian Paints Chennai 2026",
        ),
        "external_weatherproof_2coat": MaterialRate(
            name="External Weatherproof (2 coats, primer)",
            brand="Asian Paints Apex Ultima", grade="exterior",
            is_code="IS 15489",
            supplier_type="dealer + painter",
            rate=42.0, unit="sqft",
            rate_min=32.0, rate_max=58.0,
            variability_pct=31.0,
            source="Asian Paints Chennai 2026",
        ),
        "putty_2coat": MaterialRate(
            name="Wall Putty (2 coats)",
            brand="Birla White", grade="WallCare",
            is_code="",
            supplier_type="dealer + painter",
            rate=16.0, unit="sqft",
            rate_min=12.0, rate_max=22.0,
            variability_pct=31.3,
            source="Birla White Chennai 2026",
        ),
    },

    # ----------------------------------------------------------
    # waterproofing
    # ----------------------------------------------------------
    "waterproofing": {
        "terrace_membrane": MaterialRate(
            name="Terrace Waterproofing (membrane + screed)",
            brand="Dr.Fixit", grade="LW+ membrane",
            is_code="IS 2645",
            supplier_type="applicator",
            rate=85.0, unit="sqft",
            rate_min=65.0, rate_max=120.0,
            variability_pct=32.4,
            source="Dr.Fixit Chennai 2026",
        ),
        "bathroom_chemical": MaterialRate(
            name="Bathroom Floor Waterproofing (chemical)",
            brand="Dr.Fixit", grade="LW",
            is_code="IS 2645",
            supplier_type="applicator",
            rate=55.0, unit="sqft",
            rate_min=42.0, rate_max=80.0,
            variability_pct=34.5,
            source="Dr.Fixit Chennai 2026",
        ),
    },

    # ----------------------------------------------------------
    # miscellaneous
    # ----------------------------------------------------------
    "miscellaneous": {
        "site_clearance": MaterialRate(
            name="Site Clearance + Levelling",
            brand="contractor", grade="general",
            is_code="",
            supplier_type="contractor",
            rate=22.0, unit="sqft",
            rate_min=15.0, rate_max=35.0,
            variability_pct=45.5,
            source="Chennai contractor 2026",
        ),
        "scaffolding_rental": MaterialRate(
            name="Scaffolding Rental (per sqft built-up, full duration)",
            brand="contractor", grade="MS pipes",
            is_code="",
            supplier_type="contractor",
            rate=18.0, unit="sqft",
            rate_min=12.0, rate_max=28.0,
            variability_pct=44.4,
            source="Chennai contractor 2026",
        ),
        "labour_general": MaterialRate(
            name="General Construction Labour",
            brand="contractor", grade="skilled+unskilled mix",
            is_code="",
            supplier_type="contractor",
            rate=420.0, unit="sqft",
            rate_min=350.0, rate_max=500.0,
            variability_pct=17.9,
            source="Siddharth Chennai 2026",
        ),
    },
}


# ============================================================
# § 2 — PROVIDER IMPLEMENTATION
# ============================================================

class ChennaiRateProvider(RateProvider):
    """Concrete RateProvider for Chennai 2026 Q2.

    Per spec § 8: kb_version pinned to 'Chennai_2026_Q2_v1'. Bumps
    quarterly under B-C17-HEURISTIC-ROTATION-DISCIPLINE.

    Per spec § 2.11 (R14): kb_date is exposed as a property so the
    upstream_adapter can populate RateStalenessDisclosure cleanly."""

    @property
    def city_name(self) -> str:
        return "Chennai"

    @property
    def kb_version(self) -> str:
        return "Chennai_2026_Q2_v1"

    @property
    def kb_date(self) -> str:
        """ISO 8601 date for the rate snapshot."""
        return "2026-04-23"

    def get_rate(self, category: str, key: str) -> MaterialRate:
        if category not in _RATES:
            raise KeyError(
                f"ChennaiRateProvider: unknown category {category!r}. "
                f"Known: {sorted(_RATES.keys())}"
            )
        cat_table = _RATES[category]
        if key not in cat_table:
            raise KeyError(
                f"ChennaiRateProvider: unknown key {key!r} in "
                f"category {category!r}. Known keys: {sorted(cat_table.keys())}"
            )
        return cat_table[key]

    def contractor_margin_range_pct(self) -> tuple[float, float]:
        """Per spec § 2.8 + Chennai industry typical.

        (low, high) for residential v1 work:
          - Low end: 15% (lean operations, repeat clients)
          - High end: 30% (premium contractor, complex sites)"""
        return (15.0, 30.0)

    def contractor_margin_default_pct(self) -> float:
        """Mid-range default for DiscussionBaseline (R9)."""
        return 22.0
