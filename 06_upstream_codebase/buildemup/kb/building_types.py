"""
BuildemUp† — Building Type Registry
=====================================

The architecture that enables expansion beyond residential.

v0.4 implements: residential single-family.
v0.4 architecturally supports (registry entries declared, rules stubbed):
  - residential multi-family
  - commercial office
  - retail
  - mixed-use
  - educational (schools, colleges)
  - healthcare (clinics, hospitals)
  - hospitality (hotels, guesthouses)

Explicitly excluded from architecture (out of scope):
  - industrial
  - warehouse
  - airports / transportation hubs
  - power plants / industrial process

Why a registry instead of an enum:
  - Each building type has different importance factor (IS 1893)
  - Different live load (IS 875 Part 2)
  - Different max floor count for our v1 engine
  - Different finish quality tier
  - Different code applicability (NBC, ECBC for commercial)
  - The registry makes adding a new type a data change, not a code change

†= placeholder name marker.

KB_VERSION: "BuildingType_Registry_2026_v1"
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


KB_VERSION = "BuildingType_Registry_2026_v1"


class BuildingType(str, Enum):
    """All building types we recognize.

    Each value matches a registry entry below. The enum exists so that
    code can refer to types symbolically; the registry holds the actual
    parameters per type.
    """
    # Fully implemented in v0.4
    RESIDENTIAL_SINGLE_FAMILY = "residential_single_family"

    # Architecturally supported, rules stubbed for future implementation
    RESIDENTIAL_MULTI_FAMILY = "residential_multi_family"
    COMMERCIAL_OFFICE = "commercial_office"
    RETAIL = "retail"
    MIXED_USE = "mixed_use"
    EDUCATIONAL = "educational"
    HEALTHCARE = "healthcare"
    HOSPITALITY = "hospitality"


@dataclass(frozen=True)
class BuildingTypeSpec:
    """Specification for one building type.

    All parameters that vary by type live here. Engine logic reads from
    here rather than hardcoding residential values.
    """
    type_id: BuildingType
    display_name: str

    # IS 1893 importance factor (cl. 6.4.2)
    # Higher = more conservative seismic design
    importance_factor: float

    # IS 875 Part 2 typical live load (kN/sqm) for the dominant use floor
    typical_live_load_knsqm: float

    # Max floors our v1 engine supports for this building type
    max_floors_above_ground: int

    # Whether stilt parking is common/expected
    typically_has_stilt_parking: bool

    # Whether IS 13920 ductile detailing is mandatory regardless of zone
    # (true for "important" buildings — hospitals, schools)
    is13920_mandatory_all_zones: bool

    # NBC 2016 part(s) primarily applicable
    nbc_parts_applicable: tuple[str, ...]

    # Implementation status in our codebase
    implementation_status: str  # "FULLY_IMPLEMENTED" | "STUBBED" | "PLANNED"

    # User-facing notes about this type
    user_notes: str = ""


# ─────────────────────────────────────────────────────────────────────────
# REGISTRY — single source of truth for building type parameters
# ─────────────────────────────────────────────────────────────────────────
BUILDING_TYPE_REGISTRY: dict[BuildingType, BuildingTypeSpec] = {

    BuildingType.RESIDENTIAL_SINGLE_FAMILY: BuildingTypeSpec(
        type_id=BuildingType.RESIDENTIAL_SINGLE_FAMILY,
        display_name="Residential — single family home",
        importance_factor=1.0,           # IS 1893 cl. 6.4.2 default
        typical_live_load_knsqm=2.0,     # IS 875 Part 2 cl. 4.1
        max_floors_above_ground=4,       # G+4 max for our v1 engine
        typically_has_stilt_parking=True,
        is13920_mandatory_all_zones=False,
        nbc_parts_applicable=("NBC 2016 Part 4 (fire)",
                              "NBC 2016 Part 6 (structural)"),
        implementation_status="FULLY_IMPLEMENTED",
        user_notes="Standard single-family home. Most of our launch market.",
    ),

    BuildingType.RESIDENTIAL_MULTI_FAMILY: BuildingTypeSpec(
        type_id=BuildingType.RESIDENTIAL_MULTI_FAMILY,
        display_name="Residential — multi-family / apartment",
        importance_factor=1.0,
        typical_live_load_knsqm=2.0,
        max_floors_above_ground=4,       # Limited until lateral analysis added
        typically_has_stilt_parking=True,
        is13920_mandatory_all_zones=False,
        nbc_parts_applicable=("NBC 2016 Part 4", "NBC 2016 Part 6"),
        implementation_status="STUBBED",
        user_notes=(
            "Apartment buildings with multiple units. Architecturally "
            "supported but lateral analysis needed for >G+2 — currently "
            "limited to G+4 max with disclosure."
        ),
    ),

    BuildingType.COMMERCIAL_OFFICE: BuildingTypeSpec(
        type_id=BuildingType.COMMERCIAL_OFFICE,
        display_name="Commercial — office building",
        importance_factor=1.0,
        typical_live_load_knsqm=3.0,    # IS 875 Part 2 cl. 4.1 (office)
        max_floors_above_ground=4,       # Conservative until full validation
        typically_has_stilt_parking=True,
        is13920_mandatory_all_zones=False,
        nbc_parts_applicable=("NBC 2016 Part 4", "NBC 2016 Part 6",
                              "ECBC 2017 (energy)"),
        implementation_status="STUBBED",
        user_notes=(
            "Small to mid-sized office building. Commercial-grade finishes "
            "and electrical loads. ECBC applies. NOT YET FULLY IMPLEMENTED."
        ),
    ),

    BuildingType.RETAIL: BuildingTypeSpec(
        type_id=BuildingType.RETAIL,
        display_name="Retail — shop / showroom",
        importance_factor=1.0,
        typical_live_load_knsqm=4.0,    # Higher LL for shopping/storage
        max_floors_above_ground=3,
        typically_has_stilt_parking=True,
        is13920_mandatory_all_zones=False,
        nbc_parts_applicable=("NBC 2016 Part 4", "NBC 2016 Part 6"),
        implementation_status="STUBBED",
        user_notes=(
            "Retail space — shop, showroom, small commercial. Higher live "
            "load than residential. NOT YET FULLY IMPLEMENTED."
        ),
    ),

    BuildingType.MIXED_USE: BuildingTypeSpec(
        type_id=BuildingType.MIXED_USE,
        display_name="Mixed-use (commercial + residential)",
        importance_factor=1.0,
        typical_live_load_knsqm=3.0,    # Average across uses
        max_floors_above_ground=4,
        typically_has_stilt_parking=True,
        is13920_mandatory_all_zones=False,
        nbc_parts_applicable=("NBC 2016 Part 4", "NBC 2016 Part 6",
                              "ECBC 2017 if commercial >100 sqm"),
        implementation_status="STUBBED",
        user_notes=(
            "Commercial on lower floors + residential above (common Indian "
            "urban pattern). Per-floor load logic needed — NOT IMPLEMENTED."
        ),
    ),

    BuildingType.EDUCATIONAL: BuildingTypeSpec(
        type_id=BuildingType.EDUCATIONAL,
        display_name="Educational (school, college)",
        importance_factor=1.5,           # IS 1893 cl. 6.4.2 — important building
        typical_live_load_knsqm=4.0,    # Classrooms IS 875 Part 2
        max_floors_above_ground=3,
        typically_has_stilt_parking=False,
        is13920_mandatory_all_zones=True,  # Important building — always ductile
        nbc_parts_applicable=("NBC 2016 Part 4", "NBC 2016 Part 6",
                              "NBC 2016 Part 9 (educational specifics)"),
        implementation_status="STUBBED",
        user_notes=(
            "Schools/colleges are 'important buildings' per IS 1893 — "
            "importance factor 1.5×, ductile detailing always required, "
            "stricter fire safety. NOT YET FULLY IMPLEMENTED."
        ),
    ),

    BuildingType.HEALTHCARE: BuildingTypeSpec(
        type_id=BuildingType.HEALTHCARE,
        display_name="Healthcare (clinic, hospital)",
        importance_factor=1.5,           # Important building
        typical_live_load_knsqm=3.0,
        max_floors_above_ground=3,
        typically_has_stilt_parking=True,
        is13920_mandatory_all_zones=True,
        nbc_parts_applicable=("NBC 2016 Part 4", "NBC 2016 Part 6",
                              "NBC 2016 Part 9"),
        implementation_status="STUBBED",
        user_notes=(
            "Hospitals/clinics need uninterrupted operation post-earthquake. "
            "Importance factor 1.5×. Specialised MEP needs (medical gas, "
            "isolation rooms). NOT YET FULLY IMPLEMENTED."
        ),
    ),

    BuildingType.HOSPITALITY: BuildingTypeSpec(
        type_id=BuildingType.HOSPITALITY,
        display_name="Hospitality (hotel, guesthouse)",
        importance_factor=1.0,
        typical_live_load_knsqm=2.0,    # Hotel rooms similar to residential
        max_floors_above_ground=4,
        typically_has_stilt_parking=True,
        is13920_mandatory_all_zones=False,
        nbc_parts_applicable=("NBC 2016 Part 4 (stricter for hotels)",
                              "NBC 2016 Part 6"),
        implementation_status="STUBBED",
        user_notes=(
            "Hotel/guesthouse. Stricter fire code (NBC Part 4 hospitality). "
            "Specialised plumbing for guest rooms. NOT YET FULLY IMPLEMENTED."
        ),
    ),
}


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────
def get_spec(building_type: BuildingType) -> BuildingTypeSpec:
    """Get the spec for a building type. Raises if unknown."""
    if building_type not in BUILDING_TYPE_REGISTRY:
        raise KeyError(f"Unknown building type: {building_type}")
    return BUILDING_TYPE_REGISTRY[building_type]


def is_fully_implemented(building_type: BuildingType) -> bool:
    """Is this building type fully implemented in v0.4?"""
    return get_spec(building_type).implementation_status == "FULLY_IMPLEMENTED"


def supported_types() -> list[BuildingType]:
    """All types in the registry."""
    return list(BUILDING_TYPE_REGISTRY.keys())


def fully_implemented_types() -> list[BuildingType]:
    """Only the types we fully support today."""
    return [
        bt for bt, spec in BUILDING_TYPE_REGISTRY.items()
        if spec.implementation_status == "FULLY_IMPLEMENTED"
    ]


def stubbed_types() -> list[BuildingType]:
    """Types architecturally supported but with rules pending."""
    return [
        bt for bt, spec in BUILDING_TYPE_REGISTRY.items()
        if spec.implementation_status == "STUBBED"
    ]
