# ============================================================================
# BuildemUp C4 (Plot Analysis) — Consolidated Review Bundle (v0.7)
# ============================================================================
#
# SPEC: v0.7 LOCKED — patch delta on top of v0.6 LOCKED. Specs at:
#   /mnt/user-data/outputs/buildemup_C4_SPEC_v0_5_PROPOSED.md  (locked as v0.5)
#   /mnt/user-data/outputs/buildemup_C4_SPEC_v0_6_PROPOSED.md  (locked as v0.6)
#   /mnt/user-data/outputs/buildemup_C4_SPEC_v0_7_LOCKED.md    (this LOCK)
# Session: S29
# Status: code shipped, 1408 / 2 skipped / 0 failed in full project run
#         (was 1402/2/0 at v0.6 LOCK — net +6 from v0.7 patches)
#
# THIS FILE IS NOT EXECUTABLE.
# It is a single-file CONCATENATION for code review only. The actual
# source lives at the paths shown in each module-boundary header.
# Imports between modules look like cross-references after concat,
# not Python import resolution — do not try to run this file.
#
# WHAT CHANGED IN v0.7 (vs v0.6 bundle)
# -------------------------------------
# 4 SPEC-AMENDMENTS, 1 doc-only, 1 perf-test re-cap. All changes are
# internal refactors / field-shape changes — zero contract-breaking changes.
#
#  Walk #  Fix                                                  Files touched
#  ------  ---------------------------------------------------  --------------------
#    #1    Centralized normalize_city() helper                  climate_zone.py
#    #2    WindContext.basic_speed_ms: @property → stored field schema.py, wind_direction.py
#    #3    [BACKLOG only — B-079 KB_VERSION format policy]      (none)
#    #4    validate_city() helper; refactor 3 inline call sites climate_zone.py, plot_analysis.py
#    #5    [DOCUMENTED + PUSH-BACK] upstream invariants doc     plot_analysis.py docstring
#    #6    Perf cap 1ms → 3ms (CI-jitter headroom)              test_c4_performance.py
#
# 1 NEW BACKLOG ITEM filed at PROPOSED time (Rule 9.2):
#   B-079  System-wide KB_VERSION format policy. Codebase has 6+ co-existing
#          format styles (e.g., 'v1.0' vs 'Wind_IS875_2026_v1' vs
#          'SoilSBC_IS1904_v1_2026'). Cross-component sweep, not a C4-only fix.
#
# 2 PUSHBACKS HELD (no code change):
#   #1 framing — v0.6 fail-fast claim was already correct (verify_kb_consistency
#                catches case mismatches via set difference on lowercase keys).
#                The DRY refactor is still worth doing; framing was wrong.
#   #5 main   — Plot.__post_init__ enforces 3.0 ≤ width_m ≤ 60.0, dataclasses.replace
#                re-runs __post_init__. Width-zero is mechanically impossible through
#                any normal path. Adding redundant width_m > 0 in C4 = two-place
#                maintenance for one invariant. Push back stands.
#
# WHERE TO LOOK IF YOU ONLY HAVE 5 MINUTES
# ----------------------------------------
#   - components/c04/climate_zone.py: NEW normalize_city + validate_city helpers
#                                      (this is the core v0.7 refactor)
#   - components/c04/schema.py: WindContext now has basic_speed_ms as a field,
#                                no more @property
#   - kb/wind_direction.py: imports BASIC_WIND_SPEED_MS at top; populates each
#                            entry with basic_speed_ms eagerly
#   - components/c04/plot_analysis.py: derive() now calls validate_city(plot.city);
#                                       upstream-invariants doc note added
#
# BUNDLE ORDERING (dependency order, not alphabetical):
#   1. KB layer (soil_city_defaults — depends only on domain)
#   2. C4 schema (the type/enum vocabulary — read this before any logic)
#   3. KB layer that depends on C4 schema (wind_direction, city_geography)
#   4. C4 leaf modules (sun_path, climate_zone, soil_estimator, neighbour_context)
#   5. C4 orchestrator (plot_analysis)
#   6. C4 package init
#   7. Test fixtures
#   8. Tests (main → KB drift → immutability → solar → perf → property → guardrail)
#
# v0.6 → v0.7 SOURCE DELTA AT A GLANCE
#   schema.py:               -8 LOC  (removed @property block)
#   wind_direction.py:       +9 LOC  (top import + 6 basic_speed_ms kwargs)
#   climate_zone.py:         +29 LOC (normalize_city + validate_city helpers)
#   plot_analysis.py:        +9 LOC  (validate_city call + upstream-invariants doc;
#                                      net change from -5 inline + +14 doc)
#   test_c4_performance.py:  ±0 LOC  (cap 1→3ms; rationale rewritten)
#   test_c4_plot_analysis.py: +56 LOC (6 new tests at end)
#
# ============================================================================


# ============================================================================
# TABLE OF CONTENTS  (v0.7 bundle)
# ============================================================================
#
#   #  CATEGORY        PATH                                                     TOTAL   CODE
#
#   1  KB layer        kb/soil_city_defaults.py                                   156     76
#   2  C4 schema       components/c04/schema.py                                   365    257
#   3  KB layer        kb/wind_direction.py                                       100     64
#   4  KB layer        kb/city_geography.py                                       147    108
#   5  C4 logic        components/c04/sun_path.py                                 123     92
#   6  C4 logic        components/c04/climate_zone.py                              88     67
#   7  C4 logic        components/c04/soil_estimator.py                            89     60
#   8  C4 logic        components/c04/neighbour_context.py                        113     76
#   9  C4 logic        components/c04/plot_analysis.py                            253    184
#  10  C4 package      components/c04/__init__.py                                  50     44
#  11  Test fixtures   tests/validation/_c4_fixtures.py                            84     62
#  12  Tests           tests/validation/test_c4_plot_analysis.py                  529    396
#  13  Tests           tests/validation/test_c4_kb_consistency.py                  74     50
#  14  Tests           tests/validation/test_c4_immutability.py                    50     37
#  15  Tests           tests/validation/test_c4_solar.py                           69     52
#  16  Tests           tests/validation/test_c4_performance.py                     56     42
#  17  Tests           tests/validation/test_c4_property_based.py                  73     51
#  18  Tests           tests/validation/test_c5_consumes_plot_analysis.py          69     55
#
#       TOTALS          (18 files)                                                2488   1773
# ============================================================================



# ============================================================================
# FILE 1/18  ::  KB layer  ::  kb/soil_city_defaults.py
# LOC: 156 total, 76 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — typed soil projection adapter for C4 (NEW v0.5).

WHY THIS MODULE EXISTS
======================
C4 SPEC v0.5 § 4.7.1. Three upstream-facing problems caught by code-grep
round 2 (CG-6, CG-7, CG-8) at the start of Session 29:

  1. CG-6: kb/soil_foundation_rules.py exposes CITY_SOIL_DEFAULTS keyed
     by city — not "SOIL_PROFILES" as v0.4 spec assumed. C4 needs a
     city-keyed dict with a stable name.

  2. CG-7: kb/soil_foundation_rules.SoilProfile.typical_soil is an
     informal string (e.g. "rock_or_hard_clay", "silt_clay"), NOT
     convertible to domain.plot.SoilType. Its bearing field is in
     tonnes/sqm (`safe_bearing_capacity_t_sqm`), not kPa.

  3. CG-8: v0.4 spec referenced BEARING_CAPACITY_BY_TYPE without
     defining it. C4 needs a SoilType → kPa map for the user-input
     branch of estimate_soil().

This module is a typed projection adapter: it sources its values from
the two existing soil KBs and exposes the C4-shaped contract. Pattern
E safe — zero edits to shipped code.

  - Per-city kPa values: derived from
    kb/soil_foundation_rules.CITY_SOIL_DEFAULTS.safe_bearing_capacity_t_sqm
    via t/sqm × 9.81 m/s² ≈ kPa.

  - Per-SoilType kPa values: derived from
    kb/soil_classification.SOIL_PROFILES[SoilClass].sbc_typical_knm2
    via a SoilType (domain) → SoilClass (KB) mapping. SoilType.MEDIUM_ROCK
    has no exact SoilClass equivalent; mapped to SOFT_ROCK (closest,
    conservative).

  - typical_soil per city: closest matching SoilType enum value,
    chosen conservatively (e.g., Mumbai's "rock_or_filled_up" → FILLED_UP,
    triggering LOW confidence in line with the existing CITY_SOIL_DEFAULTS
    note "MANDATORY soil testing").

CONSUMER CONTRACT (per C4 spec § 3 SoilEstimate):
  bearing_capacity_kpa with confidence == LOW means downstream
  components MUST apply a structural safety factor.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.domain.plot import SoilType


KB_VERSION = "v1.0"


# ─────────────────────────────────────────────────────────────────────────────
# Per-city soil profile (typed projection of CITY_SOIL_DEFAULTS)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SoilCityProfile:
    """Typed soil default for a city. Used by C4's city-default branch."""
    typical_soil: SoilType
    typical_bearing_capacity_kpa: float


# 1 t/sqm ≈ 9.81 kPa (g = 9.81 m/s²). City kPa values below derived from
# kb/soil_foundation_rules.CITY_SOIL_DEFAULTS:
#
#   chennai     12.0 t/sqm × 9.81 = 117.7 kPa  (clay)
#   bangalore   20.0 t/sqm × 9.81 = 196.2 kPa  (rock_or_hard_clay)
#   mumbai      15.0 t/sqm × 9.81 = 147.1 kPa  (rock_or_filled_up — VARIABLE)
#   delhi       15.0 t/sqm × 9.81 = 147.1 kPa  (silt_clay)
#   hyderabad   20.0 t/sqm × 9.81 = 196.2 kPa  (rock_or_murrum)
#   pune        18.0 t/sqm × 9.81 = 176.6 kPa  (murrum)
#
# typical_soil mappings (informal city label → SoilType, conservative):
#   chennai     "clay"               → MEDIUM_CLAY
#   bangalore   "rock_or_hard_clay"  → MEDIUM_ROCK   (rocky-typical)
#   mumbai      "rock_or_filled_up"  → FILLED_UP     (CONSERVATIVE: triggers
#                                                      LOW confidence; matches
#                                                      Mumbai docs' "MANDATORY
#                                                      soil testing" note)
#   delhi       "silt_clay"          → MEDIUM_CLAY
#   hyderabad   "rock_or_murrum"     → MEDIUM_ROCK
#   pune        "murrum"             → STIFF_CLAY    (proxy for firm murrum)
SOIL_PROFILES: dict[str, SoilCityProfile] = {
    "chennai":   SoilCityProfile(SoilType.MEDIUM_CLAY, 117.7),
    "bangalore": SoilCityProfile(SoilType.MEDIUM_ROCK, 196.2),
    "mumbai":    SoilCityProfile(SoilType.FILLED_UP,   147.1),
    "delhi":     SoilCityProfile(SoilType.MEDIUM_CLAY, 147.1),
    "hyderabad": SoilCityProfile(SoilType.MEDIUM_ROCK, 196.2),
    "pune":      SoilCityProfile(SoilType.STIFF_CLAY,  176.6),
}


# ─────────────────────────────────────────────────────────────────────────────
# Per-SoilType bearing capacity (used by user-input branch of estimate_soil)
# ─────────────────────────────────────────────────────────────────────────────

# Sourced from kb.soil_classification.SOIL_PROFILES[SoilClass].sbc_typical_knm2
# via the SoilType (domain) → SoilClass (KB) mapping below. kN/m² == kPa.
#
#   domain.SoilType    → kb.SoilClass        sbc_typical_knm2
#     HARD_ROCK          HARD_ROCK             1620.0
#     MEDIUM_ROCK        SOFT_ROCK              660.0   (closest available)
#     DENSE_SAND         DENSE_SAND             350.0
#     MEDIUM_SAND        MEDIUM_SAND            200.0
#     LOOSE_SAND         LOOSE_SAND             125.0
#     STIFF_CLAY         STIFF_CLAY             250.0
#     MEDIUM_CLAY        MEDIUM_CLAY            125.0
#     SOFT_CLAY          SOFT_CLAY               90.0
#     FILLED_UP          RECLAIMED_FILL          50.0
#
# The mapping is intentionally one-way (no reverse needed): C4 reads
# SoilType from the user; SoilClass is internal to soil_classification.
BEARING_CAPACITY_BY_TYPE: dict[SoilType, float] = {
    SoilType.HARD_ROCK:    1620.0,
    SoilType.MEDIUM_ROCK:   660.0,   # mapped to kb.SoilClass.SOFT_ROCK
    SoilType.DENSE_SAND:    350.0,
    SoilType.MEDIUM_SAND:   200.0,
    SoilType.LOOSE_SAND:    125.0,
    SoilType.STIFF_CLAY:    250.0,
    SoilType.MEDIUM_CLAY:   125.0,
    SoilType.SOFT_CLAY:      90.0,
    SoilType.FILLED_UP:      50.0,   # mapped to kb.SoilClass.RECLAIMED_FILL
}


# ─────────────────────────────────────────────────────────────────────────────
# High-variability marker (drives LOW confidence in city-default branch)
# ─────────────────────────────────────────────────────────────────────────────

# When a city's typical_soil falls in this set, estimate_soil() returns
# ConfidenceLevel.LOW for the city-default branch. Per spec § 4.7.
HIGH_VARIABILITY_SOIL_TYPES: frozenset[SoilType] = frozenset({
    SoilType.SOFT_CLAY,    # highly variable; site survey strongly recommended
    SoilType.LOOSE_SAND,   # liquefaction risk; varies with water table
    SoilType.FILLED_UP,    # made-up ground — always low-confidence
})


# Coverage invariants checked by tests:
#   - Every domain.plot.SoilType value is a key in BEARING_CAPACITY_BY_TYPE.
#   - SOIL_PROFILES covers every city in domain.plot.SUPPORTED_CITIES.
# The KB-drift check (verify_kb_consistency in kb.city_geography) handles
# the latter as part of the cross-KB invariant.

__all__ = [
    "KB_VERSION",
    "SoilCityProfile",
    "SOIL_PROFILES",
    "BEARING_CAPACITY_BY_TYPE",
    "HIGH_VARIABILITY_SOIL_TYPES",
]


# ============================================================================
# FILE 2/18  ::  C4 schema  ::  components/c04/schema.py
# LOC: 365 total, 257 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — Component 4 (Plot Analysis) schema.

All dataclasses + enums for C4. Per SPEC v0.5 LOCKED § 3.

Pure types only — no logic, no I/O. Importable independently of the
rest of c04 to break circular import risk between
`kb/city_geography.py` and `components/c04/__init__.py`.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot, SoilType


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class PlotTier(str, Enum):
    """Plot-size tier — drives layout topology bias in C5."""
    T1_COMPACT = "T1"     # 600 ≤ sqft < 2400
    T2_STANDARD = "T2"    # 2400 ≤ sqft < 4000
    T3_LARGE = "T3"       # sqft ≥ 4000


class PlotShape(str, Enum):
    """Plot shape. v1 always RECTANGULAR; L_SHAPED / IRREGULAR = B-066."""
    RECTANGULAR = "rectangular"
    L_SHAPED = "l_shaped"
    IRREGULAR = "irregular"


class ClimateZone(str, Enum):
    """5 climate zones per NBC 2016 Part 8 Section 1, §§ 2.2.21–2.2.24 + 3.2.2.

    No v1 city maps to HOT_DRY (Jodhpur not in supported set) or COLD
    (Srinagar not in supported set). Reserved for future expansion.
    """
    HOT_DRY = "hot_dry"
    WARM_HUMID = "warm_humid"
    TEMPERATE = "temperate"
    COMPOSITE = "composite"
    COLD = "cold"


class ConfidenceLevel(str, Enum):
    """Confidence tag on derived properties (currently soil_estimate).

    Consumer contract: components reading `confidence == LOW` MUST apply
    a structural safety factor to bearing_capacity_kpa. C7 currently
    uses its own conservative defaults (B-072 retrofit will align this).
    """
    LOW = "low"        # high-variability soil region; downstream MUST apply safety factor
    MEDIUM = "medium"  # city-default for stable-soil region
    HIGH = "high"      # user-supplied site survey


class RoadWidthClass(str, Enum):
    """Coarse classifier for layout heuristics. FSI-aware logic lives in C2."""
    NARROW = "narrow"        # < 6m
    STANDARD = "standard"    # 6–12m
    WIDE = "wide"            # ≥ 12m


# ─────────────────────────────────────────────────────────────────────────────
# Geometry / climate / wind / soil dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SunPath:
    """Solar geometry at solstices. Closed-form Cooper 1969.

    Per-month declination = B-067.
    """
    latitude_deg: float
    summer_solstice_noon_alt: float
    winter_solstice_noon_alt: float
    sunrise_arc_summer: tuple[float, float]
    sunrise_arc_winter: tuple[float, float]


@dataclass(frozen=True)
class WindContext:
    """City wind characterisation.

    `basic_speed_ms` is the IS-875 Part 3 basic wind speed for the city,
    in m/s. `city` is documentary metadata (which city these values
    refer to).

    v0.5 (CG-5): `primary_direction` and `monsoon_direction` use
    full PlotOrientation member names (NORTH, NORTHEAST, ...), not
    short value-string aliases.

    v0.6 (walk #3): `confidence` field exposes the data-quality status
    of the per-city direction values. All v1 cities are MEDIUM (single-
    station IMD climatology). HIGH requires per-city wind-rose
    verification (B-070).

    v0.7 (walk #2): `basic_speed_ms` is a STORED field, not a lazy
    property. The IS-875 wind speed is resolved once at PREVAILING_WIND
    construction (module load) and frozen on the dataclass, eliminating
    the runtime hidden import. Single-source-of-truth for wind speeds is
    preserved (kb.wind_load is still the canonical KB; it's just
    consulted at module load instead of at every property access).

    CONSUMER CONTRACT: components reading `confidence == MEDIUM` MAY
    apply fallback heuristics (e.g., assume isotropic monsoon dominance)
    when ventilation logic depends on tight directional resolution.
    """
    primary_direction: PlotOrientation     # dominant non-monsoon
    monsoon_direction: PlotOrientation     # SW or NE monsoon arrival
    city: str                              # documentary metadata
    basic_speed_ms: float                  # NEW v0.7 (walk #2): stored field
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass(frozen=True)
class SoilEstimate:
    """Soil + bearing capacity estimate with confidence tag.

    Consumer contract: confidence == LOW → downstream MUST apply
    safety factor on bearing_capacity_kpa.

    v0.6 (walks #2, #7): `provenance_note` surfaces approximation
    decisions or high-variability reasons that the LOW/MEDIUM/HIGH
    confidence enum is too coarse to express. Examples:
      - None for clean user_input or stable city defaults.
      - "medium_rock_approximated_to_soft_rock_660kpa_underestimate_b074"
        when MEDIUM_ROCK is requested (kb has no MEDIUM_ROCK class;
        downcast to SOFT_ROCK is a documented underestimate per IS 6403).
      - "filled_up_high_variability_site_survey_required" for Mumbai
        city default (matches CITY_SOIL_DEFAULTS' "MANDATORY soil
        testing" guidance).

    The `_b074` / `_b076` suffixes act as in-source breadcrumbs to the
    deferred backlog items.
    """
    soil_type: SoilType
    bearing_capacity_kpa: float | None
    confidence: ConfidenceLevel
    source: str                              # "user_input" | "city_default"
    provenance_note: str | None = None       # NEW v0.6 (walks #2, #7)


@dataclass(frozen=True)
class NeighbourContext:
    """Raw plot openness — does NOT account for setbacks.

    `effective_open_sides` (post-setback) = B-068.

    v0.6 (walk #5): `corner_assumption` surfaces the v1 convention used
    when the input contract underspecifies which side the second street
    is on (currently only CONTINUOUS+corner without an explicit
    `Plot.corner_orientation`). Populated as
    `"second_street_assumed_LEFT_b076"` for that case; None otherwise.

    CONSUMER CONTRACT: components reading `corner_assumption is not None`
    SHOULD treat downstream layout decisions affected by the second-
    street side as TENTATIVE pending B-076.
    """
    open_sides: tuple[PlotOrientation, ...]
    shared_sides: tuple[PlotOrientation, ...]
    raw_facade_count: int                    # = len(open_sides)
    corner_assumption: str | None = None     # NEW v0.6 (walk #5)


@dataclass(frozen=True)
class PlotAnalysisProvenance:
    """Tracking metadata: when this analysis was derived + KB versions.

    `derived_at` is caller-injected (Unix epoch seconds, > 0). KB
    versions auto-populated from KB_VERSION constants at construction.
    """
    derived_at: float                    # Unix epoch seconds (> 0)
    source_versions: Mapping[str, str]   # MappingProxyType


# ─────────────────────────────────────────────────────────────────────────────
# Top-level output: PlotAnalysis
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlotAnalysis:
    """C4's output. Single source of truth for plot-derived properties.

    C5 onward MUST consume this rather than re-deriving from raw `plot`.
    C7 currently re-derives soil — see B-072 for the deferred retrofit.

    v0.5 (CG-9): `trace_id` (was `brief_token` in v0.1–v0.4) — renamed
    to mirror upstream Brief.trace_id.
    """
    # ── Identity ──
    trace_id: str
    plot: Plot                                            # frozen passthrough

    # ── Computed properties ──
    area_sqft: float
    area_sqm: float
    tier: PlotTier
    shape: PlotShape                                      # ALWAYS RECTANGULAR in v1
    shape_metadata: Mapping[str, object]                  # MappingProxyType
    aspect_ratio: float                                   # depth / width

    # ── Solar geometry ──
    sun_path: SunPath

    # ── Climate (top-level — climate-derived, not solar-geometry-derived) ──
    climate_zone: ClimateZone
    baseline_room_orientation_guidelines: Mapping[
        ClimateZone, Mapping[str, tuple[PlotOrientation, ...]]
    ]                                                      # MappingProxyType (outer + inner)

    # ── Wind ──
    prevailing_wind: WindContext

    # ── Geotechnical ──
    soil_estimate: SoilEstimate

    # ── Site context ──
    road_width_classification: RoadWidthClass
    neighbour_context: NeighbourContext

    # ── Provenance ──
    provenance: PlotAnalysisProvenance


# ─────────────────────────────────────────────────────────────────────────────
# Constants (climate-keyed baselines + facing translation)
# ─────────────────────────────────────────────────────────────────────────────

# Baseline room orientation guidelines per climate zone (v0.5 CG-5: full
# PlotOrientation member names). MappingProxyType wraps both outer + inner
# dicts so consumers cannot mutate (SC-1).
#
# These are CLIMATE-derived heuristics. C5/C6 produce dynamic recommendations
# integrating baselines + plot facing + aspect ratio + neighbour openness +
# Vastu + brief preferences.
#
# Values for HOT_DRY and COLD are reserved (no v1 city maps to them); the
# tables are populated for forward-compat but no v1 test path exercises them
# beyond presence checks.
_PO = PlotOrientation  # local alias to keep the table compact

BASELINE_ROOM_ORIENTATION_GUIDELINES: Mapping[
    ClimateZone, Mapping[str, tuple[PlotOrientation, ...]]
] = MappingProxyType({
    ClimateZone.WARM_HUMID: MappingProxyType({   # Mumbai, Chennai
        "living":   (_PO.NORTH, _PO.NORTHEAST),
        "kitchen":  (_PO.EAST, _PO.SOUTHEAST),
        "bedroom":  (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "bathroom": (_PO.WEST, _PO.SOUTHWEST, _PO.NORTHWEST),
    }),
    ClimateZone.TEMPERATE: MappingProxyType({    # Bangalore, Pune
        "living":   (_PO.NORTH, _PO.NORTHEAST, _PO.EAST, _PO.SOUTH),
        "kitchen":  (_PO.EAST, _PO.SOUTHEAST, _PO.NORTHEAST),
        "bedroom":  (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "bathroom": (_PO.WEST, _PO.SOUTHWEST),
    }),
    ClimateZone.COMPOSITE: MappingProxyType({    # Delhi, Hyderabad
        "living":   (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "kitchen":  (_PO.EAST, _PO.NORTHEAST),
        "bedroom":  (_PO.NORTH, _PO.NORTHEAST, _PO.EAST, _PO.SOUTHEAST),
        "bathroom": (_PO.WEST, _PO.SOUTHWEST, _PO.NORTHWEST),
    }),
    ClimateZone.HOT_DRY: MappingProxyType({       # Reserved (no v1 city)
        "living":   (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "kitchen":  (_PO.EAST, _PO.NORTHEAST),
        "bedroom":  (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "bathroom": (_PO.WEST, _PO.SOUTHWEST),
    }),
    ClimateZone.COLD: MappingProxyType({          # Reserved (no v1 city)
        "living":   (_PO.SOUTH, _PO.SOUTHEAST, _PO.SOUTHWEST),
        "kitchen":  (_PO.EAST, _PO.SOUTHEAST),
        "bedroom":  (_PO.SOUTH, _PO.SOUTHEAST),
        "bathroom": (_PO.NORTH, _PO.NORTHWEST),
    }),
})


# Facing → which compass direction is "left" / "right" from a viewer
# standing on the street facing the plot. Used by neighbour_context for
# SharedSide (LEFT/RIGHT) → PlotOrientation translation.
#
# Convention: "left" = 90° counter-clockwise from front; "right" = 90°
# clockwise. Compound facings (NORTHEAST, SOUTHEAST, SOUTHWEST, NORTHWEST)
# get perpendicular diagonals.
LEFT_RIGHT_BY_FACING: Mapping[
    PlotOrientation, Mapping[str, PlotOrientation]
] = MappingProxyType({
    _PO.NORTH:     MappingProxyType({"left": _PO.WEST,      "right": _PO.EAST}),
    _PO.SOUTH:     MappingProxyType({"left": _PO.EAST,      "right": _PO.WEST}),
    _PO.EAST:      MappingProxyType({"left": _PO.NORTH,     "right": _PO.SOUTH}),
    _PO.WEST:      MappingProxyType({"left": _PO.SOUTH,     "right": _PO.NORTH}),
    _PO.NORTHEAST: MappingProxyType({"left": _PO.NORTHWEST, "right": _PO.SOUTHEAST}),
    _PO.SOUTHEAST: MappingProxyType({"left": _PO.NORTHEAST, "right": _PO.SOUTHWEST}),
    _PO.SOUTHWEST: MappingProxyType({"left": _PO.SOUTHEAST, "right": _PO.NORTHWEST}),
    _PO.NORTHWEST: MappingProxyType({"left": _PO.SOUTHWEST, "right": _PO.NORTHEAST}),
})


# Facing → opposite (used for back-of-plot computation).
_OPPOSITE_FACING: Mapping[PlotOrientation, PlotOrientation] = MappingProxyType({
    _PO.NORTH:     _PO.SOUTH,
    _PO.SOUTH:     _PO.NORTH,
    _PO.EAST:      _PO.WEST,
    _PO.WEST:      _PO.EAST,
    _PO.NORTHEAST: _PO.SOUTHWEST,
    _PO.SOUTHWEST: _PO.NORTHEAST,
    _PO.SOUTHEAST: _PO.NORTHWEST,
    _PO.NORTHWEST: _PO.SOUTHEAST,
})


def compute_plot_facing_sides(
    facing: PlotOrientation,
) -> Mapping[str, PlotOrientation]:
    """Map plot.facing to the four cardinal "sides" of the plot.

    Returns a frozen mapping with keys "front", "back", "left", "right".

    "front" = facing direction (street side)
    "back"  = opposite of front
    "left"  = 90° counter-clockwise from front (viewer on street facing plot)
    "right" = 90° clockwise from front

    Tested for all 8 PlotOrientation values.
    """
    if not isinstance(facing, PlotOrientation):
        raise ValueError(
            f"compute_plot_facing_sides requires PlotOrientation; got "
            f"{type(facing).__name__}"
        )
    lr = LEFT_RIGHT_BY_FACING[facing]
    return MappingProxyType({
        "front": facing,
        "back":  _OPPOSITE_FACING[facing],
        "left":  lr["left"],
        "right": lr["right"],
    })


__all__ = [
    "PlotTier",
    "PlotShape",
    "ClimateZone",
    "ConfidenceLevel",
    "RoadWidthClass",
    "SunPath",
    "WindContext",
    "SoilEstimate",
    "NeighbourContext",
    "PlotAnalysisProvenance",
    "PlotAnalysis",
    "BASELINE_ROOM_ORIENTATION_GUIDELINES",
    "LEFT_RIGHT_BY_FACING",
    "compute_plot_facing_sides",
]


# ============================================================================
# FILE 3/18  ::  KB layer  ::  kb/wind_direction.py
# LOC: 100 total, 64 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — IMD Prevailing Wind Direction (NEW v0.5).

Per-city prevailing wind direction sourced from Indian Meteorological
Department climatology summaries. Used by C4 (Plot Analysis) for
ventilation orientation hints to the layout pipeline (C5/C6).

NOT a wind-rose. NOT for structural design. Wind speed (basic_speed_ms)
is read from kb/wind_load — this module carries direction only.

CALIBRATION CAVEAT (per C4 spec § 4.6): all 6 city values are PROPOSED
pending per-city IMD wind-rose verification (B-070).

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c04.schema import ConfidenceLevel, WindContext
from buildemup.domain.envelope import PlotOrientation as _PO
# v0.7 (walk #2): import wind speeds at module load so each WindContext
# can carry basic_speed_ms as a stored field instead of resolving via
# lazy property at access time. Module-load coupling between two
# mandatory KBs is intentional and acceptable.
from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS as _BASIC_WIND_SPEED_MS


KB_VERSION = "v1.0"


# Per-city wind direction. Source: IMD climatology summaries (cited per-city
# below). Full IMD wind-rose integration is B-070.
#
# NOTE: WindContext was extended in v0.5 with `city: str` so the
# basic_speed_ms property can do a wind_load lookup at access time.
# v0.7 (walk #2): `basic_speed_ms` is now a stored field; resolved here
# at module load. The `city` field is retained as documentary metadata.
#
# v0.6 (walk #3): every entry carries `confidence=ConfidenceLevel.MEDIUM`
# explicitly. MEDIUM = "single-station IMD climatology" — sufficient for
# v1 layout heuristics but not authoritative for ventilation engineering.
# B-070 will promote to HIGH when full per-city wind-rose data is
# integrated. C5 ventilation logic SHOULD read this flag and apply
# isotropic-monsoon fallback heuristics where directional resolution
# matters.
PREVAILING_WIND: dict[str, WindContext] = {
    "chennai":   WindContext(
        primary_direction=_PO.NORTHEAST,    # NE non-monsoon (Oct–Mar)
        monsoon_direction=_PO.SOUTHWEST,    # SW monsoon (Jun–Sep)
        city="chennai",
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["chennai"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Chennai (Nungambakkam) climatology
    ),
    "mumbai":    WindContext(
        primary_direction=_PO.WEST,
        monsoon_direction=_PO.SOUTHWEST,
        city="mumbai",
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["mumbai"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Santacruz station
    ),
    "bangalore": WindContext(
        primary_direction=_PO.WEST,
        monsoon_direction=_PO.SOUTHWEST,
        city="bangalore",
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["bangalore"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Bangalore HAL
    ),
    "pune":      WindContext(
        primary_direction=_PO.WEST,
        monsoon_direction=_PO.SOUTHWEST,
        city="pune",
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["pune"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Shivajinagar
    ),
    "hyderabad": WindContext(
        primary_direction=_PO.WEST,
        monsoon_direction=_PO.SOUTHWEST,
        city="hyderabad",
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["hyderabad"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Begumpet
    ),
    "delhi":     WindContext(
        primary_direction=_PO.NORTHWEST,    # NW winter
        monsoon_direction=_PO.SOUTHEAST,    # monsoon spillover
        city="delhi",
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["delhi"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Safdarjung
    ),
}


__all__ = [
    "KB_VERSION",
    "PREVAILING_WIND",
]


# ============================================================================
# FILE 4/18  ::  KB layer  ::  kb/city_geography.py
# LOC: 147 total, 108 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — City Geography (NEW v0.5).

Per-city latitude + climate zone tables. Used by C4's solar geometry
and climate zone lookup. Hosts verify_kb_consistency() which checks
that all 4 KBs (this one, wind_load, wind_direction, soil_city_defaults)
cover every supported city.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.components.c04.schema import ClimateZone


KB_VERSION = "v1.0"


@dataclass(frozen=True)
class CityGeography:
    """Per-city geography for solar + climate calculation."""
    latitude_deg: float
    climate_zone: ClimateZone


# 6 cities matching domain.plot.SUPPORTED_CITIES exactly.
#
# Source: NBC 2016 Part 8 Section 1, §§ 2.2.21-2.2.24 + 3.2.2;
# cross-verified with ECBC 2017 climate-zone-finder.
#
# Adding a new city requires updating domain.plot.SUPPORTED_CITIES AND
# all 4 KBs (this one + wind_load + wind_direction + soil_city_defaults)
# in the same change. verify_kb_consistency() will fail-fast otherwise.
CITY_GEOGRAPHY: dict[str, CityGeography] = {
    "chennai":   CityGeography(13.08, ClimateZone.WARM_HUMID),
    "mumbai":    CityGeography(19.08, ClimateZone.WARM_HUMID),
    "bangalore": CityGeography(12.97, ClimateZone.TEMPERATE),
    "pune":      CityGeography(18.52, ClimateZone.TEMPERATE),
    "delhi":     CityGeography(28.61, ClimateZone.COMPOSITE),
    "hyderabad": CityGeography(17.39, ClimateZone.COMPOSITE),
}


def verify_kb_consistency() -> None:
    """Cross-KB invariant check.

    Every supported city must be present in EVERY KB. KBs may carry
    extras (forward-compat) but cannot be missing any supported city.

    v0.6 (walk #6): also runs LOOSE value-quality sanity checks. These
    are defensive against copy-paste / unit errors at code-edit time,
    NOT design bounds:
      - IS 875 Part 3:    India basic wind = 33-55 m/s, cyclonic up to ~70.
                          Sanity range: [30, 70].
      - India geography:  latitudes 8°-37° N. Sanity range with margin: [5, 40].
      - IS 6403 / IS 1904: typical residential SBC range. Sanity: [10, 2000].

    Called from components/c04/__init__.py at module import (fail-fast)
    AND as an explicit Tier-1 test.

    Raises:
        RuntimeError: if any KB is missing a supported city OR any KB
                      value is out of plausible range.

    All KB_VERSION imports are explicit so any KB lacking the constant
    causes ImportError at this call (not later, deeper in C4).
    """
    # Local imports — defer to call time so module import order is robust.
    from buildemup.domain.plot              import SUPPORTED_CITIES
    from buildemup.kb.wind_load             import (
        BASIC_WIND_SPEED_MS, KB_VERSION as WL_VER,  # noqa: F401
    )
    from buildemup.kb.soil_city_defaults    import (
        SOIL_PROFILES, KB_VERSION as SC_VER,        # noqa: F401
    )
    from buildemup.kb.wind_direction        import (
        PREVAILING_WIND, KB_VERSION as WD_VER,      # noqa: F401
    )

    required = set(SUPPORTED_CITIES)

    # Coverage check: every supported city must be in every KB.
    for kb_name, kb_keys in (
        ("city_geography",      set(CITY_GEOGRAPHY.keys())),
        ("wind_load",           set(BASIC_WIND_SPEED_MS.keys())),
        ("soil_city_defaults",  set(SOIL_PROFILES.keys())),
        ("wind_direction",      set(PREVAILING_WIND.keys())),
    ):
        missing = required - kb_keys
        if missing:
            raise RuntimeError(
                f"KB drift: kb/{kb_name} missing required supported cities: "
                f"{sorted(missing)}. All 4 KBs must contain every city in "
                f"domain.plot.SUPPORTED_CITIES."
            )

    # NEW v0.6: value-quality sanity ranges (loose bounds for fail-fast).
    # Wind speed [30, 70] m/s per IS 875 Part 3 (India basic 33-55, cyclonic ~70).
    for city, speed in BASIC_WIND_SPEED_MS.items():
        if not (30.0 <= speed <= 70.0):
            raise RuntimeError(
                f"KB drift: kb/wind_load wind speed for '{city}' = {speed} m/s "
                f"out of plausible range [30, 70]. Per IS 875 Part 3 India "
                f"is 33-55 m/s with cyclonic peaks ~70."
            )
    # Latitude [5, 40] degrees (India is 8-37 N with margin).
    for city, geo in CITY_GEOGRAPHY.items():
        if not (5.0 <= geo.latitude_deg <= 40.0):
            raise RuntimeError(
                f"KB drift: kb/city_geography '{city}' latitude = "
                f"{geo.latitude_deg}° out of India range [5, 40]."
            )
    # Bearing capacity [10, 2000] kPa per IS 6403 / IS 1904 typical residential.
    for city, prof in SOIL_PROFILES.items():
        if not (10.0 <= prof.typical_bearing_capacity_kpa <= 2000.0):
            raise RuntimeError(
                f"KB drift: kb/soil_city_defaults '{city}' kPa = "
                f"{prof.typical_bearing_capacity_kpa} out of plausible "
                f"residential range [10, 2000]."
            )


def kb_versions() -> dict[str, str]:
    """Snapshot of all 4 KB_VERSION constants used by C4.

    Used by PlotAnalysisProvenance.source_versions at construction time.
    """
    from buildemup.kb.wind_load          import KB_VERSION as WL_VER
    from buildemup.kb.soil_city_defaults import KB_VERSION as SC_VER
    from buildemup.kb.wind_direction     import KB_VERSION as WD_VER
    return {
        "city_geography":     KB_VERSION,
        "wind_load":          WL_VER,
        "soil_city_defaults": SC_VER,
        "wind_direction":     WD_VER,
    }


__all__ = [
    "KB_VERSION",
    "CityGeography",
    "CITY_GEOGRAPHY",
    "verify_kb_consistency",
    "kb_versions",
]


# ============================================================================
# FILE 5/18  ::  C4 logic  ::  components/c04/sun_path.py
# LOC: 123 total, 92 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — C4 sun-path geometry (Cooper 1969, closed-form).

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


# ============================================================================
# FILE 6/18  ::  C4 logic  ::  components/c04/climate_zone.py
# LOC: 88 total, 67 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — C4 climate zone lookup + city validation utilities.

Per spec § 4.5 + v0.7 § 14.1.

Hosts:
  - normalize_city() — canonical lowercase/strip helper
  - validate_city()  — normalize + verify membership in CITY_GEOGRAPHY
  - lookup_climate_zone(city) -> ClimateZone
  - lookup_latitude(city)     -> float

v0.7 (walks #1, #4): the city-validation pattern — `if city not in
CITY_GEOGRAPHY: raise ValueError(...)` — was duplicated across 3 sites
in v0.6 (plot_analysis.py:178, climate_zone:lookup_climate_zone,
climate_zone:lookup_latitude). v0.7 centralizes it as `validate_city()`
and refactors all 3 call sites to use it.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c04.schema import ClimateZone
from buildemup.kb.city_geography import CITY_GEOGRAPHY


def normalize_city(city: str) -> str:
    """Canonical city normalization. Single source of truth.

    Returns a stripped, lowercase city name. Used at all C4 read sites
    (defense in depth — Plot.__post_init__ already does this for the
    Plot.city field, but the helper makes the contract explicit and
    available to call sites that may receive non-Plot inputs).

    Raises:
        TypeError: if city is not a str.
    """
    if not isinstance(city, str):
        raise TypeError(f"city must be str; got {type(city).__name__}")
    return city.strip().lower()


def validate_city(city: str) -> str:
    """Normalize city and verify membership in CITY_GEOGRAPHY.

    Returns the normalized city name. Single source of truth for the
    city-validation pattern that v0.6 repeated across 3 sites
    (plot_analysis.py, climate_zone:lookup_climate_zone,
    climate_zone:lookup_latitude).

    Raises:
        TypeError: if city is not a str (propagated from normalize_city).
        ValueError: if the normalized name is not a supported city.
    """
    normalized = normalize_city(city)
    if normalized not in CITY_GEOGRAPHY:
        raise ValueError(
            f"city '{normalized}' missing from CITY_GEOGRAPHY; check "
            f"kb/city_geography.py against domain.plot.SUPPORTED_CITIES"
        )
    return normalized


def lookup_climate_zone(city: str) -> ClimateZone:
    """Look up climate zone for a city.

    v0.7 (walk #4): uses the centralized validate_city() helper rather
    than inlining the membership check. Behavior unchanged.
    """
    normalized = validate_city(city)
    return CITY_GEOGRAPHY[normalized].climate_zone


def lookup_latitude(city: str) -> float:
    """Look up latitude (degrees) for a city.

    v0.7 (walk #4): uses the centralized validate_city() helper rather
    than inlining the membership check. Behavior unchanged.
    """
    normalized = validate_city(city)
    return CITY_GEOGRAPHY[normalized].latitude_deg


__all__ = [
    "normalize_city",
    "validate_city",
    "lookup_climate_zone",
    "lookup_latitude",
]


# ============================================================================
# FILE 7/18  ::  C4 logic  ::  components/c04/soil_estimator.py
# LOC: 89 total, 60 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — C4 soil estimator.

Per spec § 4.7. Returns SoilEstimate with confidence tag.

Two branches:
  - user_input:  plot.soil_type_known is provided → HIGH confidence,
                 bearing capacity from BEARING_CAPACITY_BY_TYPE.
  - city_default: not provided → city's typical_soil/kPa from
                  SOIL_PROFILES; LOW confidence if typical_soil is in
                  HIGH_VARIABILITY_SOIL_TYPES, else MEDIUM.

CONSUMER CONTRACT (per spec § 3): components reading
`confidence == LOW` MUST apply a structural safety factor.

v0.6 (walks #2, #7): populates `provenance_note` to surface
approximation decisions or high-variability reasons that the
LOW/MEDIUM/HIGH enum is too coarse to express.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c04.schema import ConfidenceLevel, SoilEstimate
from buildemup.domain.plot import Plot, SoilType
from buildemup.kb.soil_city_defaults import (
    BEARING_CAPACITY_BY_TYPE,
    HIGH_VARIABILITY_SOIL_TYPES,
    SOIL_PROFILES,
)


# v0.6 (walk #2): SoilType values that the underlying kb.soil_classification
# does NOT carry as a first-class class. C4's BEARING_CAPACITY_BY_TYPE has
# to approximate them downward to the closest available class. The note
# below explains the approximation explicitly so downstream consumers can
# see provenance instead of silently inheriting a substantially
# underestimated kPa value.
#
#   SoilType.MEDIUM_ROCK is mapped to kb.SoilClass.SOFT_ROCK (660 kPa).
#   Real medium rock per IS 6403 / IS 1904 typical values is ~1000-1500
#   kPa (foliated metamorphic 1500-3000; weathered rock 300-800; medium
#   weathered mudstone 1500-2500). 660 kPa is therefore a 40-55%
#   underestimate. Direction is conservative (over-designs foundations
#   = safe but costly). Proper fix is B-074.
_APPROXIMATED_USER_INPUT_NOTES: dict[SoilType, str] = {
    SoilType.MEDIUM_ROCK: (
        "medium_rock_approximated_to_soft_rock_660kpa_underestimate_b074"
    ),
}


def estimate_soil(plot: Plot) -> SoilEstimate:
    """Derive a soil estimate from the plot. See module docstring."""
    if plot.soil_type_known is not None:
        return SoilEstimate(
            soil_type=plot.soil_type_known,
            bearing_capacity_kpa=BEARING_CAPACITY_BY_TYPE[plot.soil_type_known],
            confidence=ConfidenceLevel.HIGH,
            source="user_input",
            provenance_note=_APPROXIMATED_USER_INPUT_NOTES.get(plot.soil_type_known),
        )

    # City-default branch. Plot.__post_init__ already guaranteed
    # plot.city ∈ SUPPORTED_CITIES, and verify_kb_consistency()
    # guaranteed SUPPORTED_CITIES ⊆ SOIL_PROFILES, so no KeyError here.
    profile = SOIL_PROFILES[plot.city]
    typical = profile.typical_soil
    is_high_variability = typical in HIGH_VARIABILITY_SOIL_TYPES
    confidence = (
        ConfidenceLevel.LOW
        if is_high_variability
        else ConfidenceLevel.MEDIUM
    )
    provenance_note = (
        f"{typical.value}_high_variability_site_survey_required"
        if is_high_variability
        else None
    )
    return SoilEstimate(
        soil_type=typical,
        bearing_capacity_kpa=profile.typical_bearing_capacity_kpa,
        confidence=confidence,
        source="city_default",
        provenance_note=provenance_note,
    )


__all__ = ["estimate_soil"]


# ============================================================================
# FILE 8/18  ::  C4 logic  ::  components/c04/neighbour_context.py
# LOC: 113 total, 76 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — C4 neighbour context derivation.

Per spec § 4.9. Computes which sides of the plot are open vs shared
with neighbours, accounting for plot_type (DETACHED / SEMI_DETACHED /
CONTINUOUS) and corner_plot.

Returns RAW openness — does NOT account for setbacks. C5 combines
with C2 setbacks for `effective_open_sides` (B-068).

CONVENTIONS:
  - SEMI_DETACHED: shared_side is LEFT or RIGHT relative to a viewer
    standing on the street facing the plot. Translated to a compass
    bearing via LEFT_RIGHT_BY_FACING.
  - CONTINUOUS: both side walls (left + right) are shared (TNCDBR 2019
    "Continuous Building Area"); only front + back are open.
  - corner_plot=True: a second street replaces one shared side wall
    with an open side. v1 conventions for which side (see
    derive_second_street_side below).

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c04.schema import (
    LEFT_RIGHT_BY_FACING,
    NeighbourContext,
    compute_plot_facing_sides,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot, PlotType, SharedSide


def derive_second_street_side(plot: Plot) -> PlotOrientation:
    """Compass direction of the second street for corner plots.

    Conventions (v1):
      - SEMI_DETACHED corner: second street is on the side WALL opposite
        to plot.shared_side. (If shared=LEFT, second street is on RIGHT.)
      - CONTINUOUS corner: second street is on the LEFT side wall (v1
        convention; arbitrary, can be refined when input contract supports
        specifying which corner).
      - DETACHED corner: all sides already open; this function should
        not be called for DETACHED. Defensive return = left side.

    Pre: plot.corner_plot == True (validation responsibility of caller).
    """
    if plot.plot_type == PlotType.SEMI_DETACHED:
        # shared_side is required to be set for SEMI_DETACHED (Plot
        # __post_init__ enforces). The opposite side is the corner road.
        shared_lr = plot.shared_side.value  # "left" | "right"
        opposite = "right" if shared_lr == "left" else "left"
        return LEFT_RIGHT_BY_FACING[plot.facing][opposite]

    if plot.plot_type == PlotType.CONTINUOUS:
        # v1 convention: second street on the LEFT side wall. See module
        # docstring for the future-refinement note.
        return LEFT_RIGHT_BY_FACING[plot.facing]["left"]

    # DETACHED — defensive return; caller short-circuits before this.
    return LEFT_RIGHT_BY_FACING[plot.facing]["left"]


def derive_neighbour_context(plot: Plot) -> NeighbourContext:
    """See module docstring."""
    sides = compute_plot_facing_sides(plot.facing)  # front/back/left/right

    if plot.plot_type == PlotType.DETACHED:
        open_sides: list[PlotOrientation] = list(sides.values())
        shared_sides: list[PlotOrientation] = []

    elif plot.plot_type == PlotType.SEMI_DETACHED:
        # shared_side is guaranteed non-None by Plot.__post_init__.
        assert plot.shared_side is not None  # type narrowing for mypy
        shared_orientation = LEFT_RIGHT_BY_FACING[plot.facing][plot.shared_side.value]
        shared_sides = [shared_orientation]
        open_sides = [s for s in sides.values() if s != shared_orientation]

    elif plot.plot_type == PlotType.CONTINUOUS:
        # Continuous building area (TNCDBR 2019): shares both side walls.
        open_sides = [sides["front"], sides["back"]]
        shared_sides = [sides["left"], sides["right"]]

    else:  # pragma: no cover — exhaustive over PlotType, but guard for future extensions.
        raise ValueError(f"unknown plot_type: {plot.plot_type}")

    # v0.6 (walk #5): track whether we used a v1 convention to pick the
    # second-street side, so downstream consumers can see when their
    # decisions are based on an inferred default.
    corner_assumption: str | None = None

    # Corner plot: a second street replaces one shared side with an open one.
    # No-op for DETACHED (no shared sides to remove from).
    if plot.corner_plot and shared_sides:
        second_street_side = derive_second_street_side(plot)
        if second_street_side in shared_sides:
            shared_sides.remove(second_street_side)
            open_sides.append(second_street_side)
        # Only CONTINUOUS+corner uses the v1 LEFT default convention. For
        # SEMI_DETACHED the second street is deterministic (opposite of
        # plot.shared_side, see derive_second_street_side); no assumption.
        if plot.plot_type == PlotType.CONTINUOUS:
            corner_assumption = "second_street_assumed_LEFT_b076"

    return NeighbourContext(
        open_sides=tuple(open_sides),
        shared_sides=tuple(shared_sides),
        raw_facade_count=len(open_sides),
        corner_assumption=corner_assumption,
    )


__all__ = ["derive_neighbour_context", "derive_second_street_side"]


# ============================================================================
# FILE 9/18  ::  C4 logic  ::  components/c04/plot_analysis.py
# LOC: 253 total, 184 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — Component 4 (Plot Analysis) orchestrator.

Per spec § 5 invocation contract.

Public entry point: `derive(brief: ResolvedBrief, *, now: float) -> PlotAnalysis`

Reads (CG-9):
  brief.revised_brief.plot         (the actual upstream path)
  brief.revised_brief.trace_id

Writes: a frozen PlotAnalysis. C5 onward MUST consume this rather than
re-deriving from raw plot.

Pure: no I/O at call time. KB lookups happened at module import.

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType

from buildemup.components.c04.climate_zone import (
    lookup_climate_zone,
    lookup_latitude,
    validate_city,
)
from buildemup.components.c04.neighbour_context import derive_neighbour_context
from buildemup.components.c04.schema           import (
    BASELINE_ROOM_ORIENTATION_GUIDELINES,
    PlotAnalysis,
    PlotAnalysisProvenance,
    PlotShape,
    PlotTier,
    RoadWidthClass,
)
from buildemup.components.c04.soil_estimator   import estimate_soil
from buildemup.components.c04.sun_path         import compute_sun_path
from buildemup.domain.envelope                 import PlotOrientation
from buildemup.domain.plot                     import Plot
from buildemup.kb.city_geography               import kb_versions
from buildemup.kb.wind_direction               import PREVAILING_WIND


# ─── Tier thresholds (per spec § 4.1) ───────────────────────────────────
# v0.6 (walk #1): tier classification compares in sqm space using the
# EXACT IEC conversion factor 1 sqft = 0.3048² m² = 0.09290304 sqm.
# This eliminates the second-rounding step (sqm × 10.7639) that made
# 40×60 ft (textbook 2400 sqft) land at 2399.998 sqft and misclassify
# as T1. The 10.7639 factor stays for area_sqft display only.
SQM_PER_SQFT = 0.09290304   # exact: 0.3048² (foot defined as 0.3048 m exactly)

_T1_MIN_SQFT = 600.0
_T2_MIN_SQFT = 2400.0
_T3_MIN_SQFT = 4000.0

_T1_MIN_SQM =  _T1_MIN_SQFT * SQM_PER_SQFT   #  55.74182400 sqm
_T2_MIN_SQM = _T2_MIN_SQFT * SQM_PER_SQFT    # 222.96729600 sqm
_T3_MIN_SQM = _T3_MIN_SQFT * SQM_PER_SQFT    # 371.61216000 sqm

_SQM_PER_SQFT_INV = 10.7639   # display-only: sqm × 10.7639 ≈ sqft

# ─── Road width class thresholds (per spec § 4.8) ───────────────────────
_NARROW_BELOW_M = 6.0
_STANDARD_BELOW_M = 12.0


def _classify_tier(area_sqm: float) -> PlotTier:
    """Classify plot tier from area in sqm (canonical comparison space).

    v0.6 (walk #1): comparison happens in sqm (the directly-computed
    unit) to avoid float misclassification at sqft boundaries — e.g.,
    40×60 ft = 12.192×18.288 m exactly, area_sqm = 222.967296 sqm,
    matches _T2_MIN_SQM = 2400 × 0.09290304 = 222.967296 sqm to ulp.
    """
    if area_sqm < _T1_MIN_SQM:
        # Display the failing area in sqft for the user-facing message.
        sqft = area_sqm * _SQM_PER_SQFT_INV
        raise ValueError(
            f"plot < {_T1_MIN_SQFT:.0f}sqft minimum (got {sqft:.1f}sqft) — "
            f"should have been gated by C3a"
        )
    if area_sqm < _T2_MIN_SQM:
        return PlotTier.T1_COMPACT
    if area_sqm < _T3_MIN_SQM:
        return PlotTier.T2_STANDARD
    return PlotTier.T3_LARGE


def _classify_road(road_width_m: float) -> RoadWidthClass:
    if road_width_m < _NARROW_BELOW_M:
        return RoadWidthClass.NARROW
    if road_width_m < _STANDARD_BELOW_M:
        return RoadWidthClass.STANDARD
    return RoadWidthClass.WIDE


def _validate_now(now: float) -> None:
    """Validate the keyword-only `now` parameter per spec § 5 invocation contract.

    bool is a subclass of int in Python; we explicitly reject it so a caller
    passing `now=True` doesn't sneak through `isinstance(now, float)` after
    the int promotion.
    """
    if isinstance(now, bool) or not isinstance(now, (int, float)):
        raise TypeError(
            f"`now` must be a float (Unix epoch seconds); got "
            f"{type(now).__name__}"
        )
    if now <= 0:
        raise ValueError(f"`now` must be > 0; got {now}")


def _extract_brief_inputs(brief: object) -> tuple[Plot, str]:
    """Pull (plot, trace_id) from a ResolvedBrief (CG-9 contract).

    Reads the actual upstream path:
      brief.revised_brief.plot
      brief.revised_brief.trace_id

    Defensive about each step so a malformed brief raises ValueError
    rather than AttributeError, per spec § 6.
    """
    revised = getattr(brief, "revised_brief", None)
    if revised is None:
        raise ValueError(
            "ResolvedBrief.revised_brief is required (got None or missing)"
        )
    plot = getattr(revised, "plot", None)
    if plot is None:
        raise ValueError(
            "ResolvedBrief.revised_brief.plot is required (got None or missing)"
        )
    if not isinstance(plot, Plot):
        raise ValueError(
            f"ResolvedBrief.revised_brief.plot must be domain.plot.Plot; got "
            f"{type(plot).__name__}"
        )
    trace_id = getattr(revised, "trace_id", None)
    if trace_id is None or not isinstance(trace_id, str):
        raise ValueError(
            "ResolvedBrief.revised_brief.trace_id must be a non-None str; "
            f"got {type(trace_id).__name__}"
        )
    return plot, trace_id


def derive(brief: object, *, now: float) -> PlotAnalysis:
    """Derive a PlotAnalysis from a ResolvedBrief.

    Args:
        brief: ResolvedBrief from C3a output. Reads
               `brief.revised_brief.plot` and `brief.revised_brief.trace_id`.
        now:   keyword-only required. Must be float > 0 (Unix epoch seconds).
               Tests pass `now=1.0` (smallest valid).

    Returns:
        Frozen PlotAnalysis. C5 onward MUST consume this; MUST NOT
        re-derive any of its fields from raw plot.

    Raises:
        TypeError: `now` not a float.
        ValueError: any of the input contract / domain validations fail
                    (city not in CITY_GEOGRAPHY; plot < 600sqft; latitude
                    out of range; bad facing enum; bad ResolvedBrief shape;
                    `now` ≤ 0).

    UPSTREAM INVARIANTS C4 RELIES ON (per domain/plot.py Plot.__post_init__):
        - 3.0 ≤ plot.width_m ≤ 60.0      (width-zero mechanically impossible)
        - 3.0 ≤ plot.depth_m ≤ 60.0
        - 1.5 ≤ plot.road_width_m ≤ 30.0
        - plot.city normalized + ∈ SUPPORTED_CITIES
        - plot.facing is a PlotOrientation enum

    These are NOT re-validated in C4 (single source of truth for plot
    invariants is the Plot constructor). dataclasses.replace() re-runs
    __post_init__, so post-construction modification via that path is also
    covered. The only true bypass is object.__new__ + object.__setattr__,
    which defeats any layer of validation equally — so re-validating in C4
    would not help.

    v0.7 (walk #5): documented above; pushback on a redundant defensive
    width_m > 0 check stands.
    """
    _validate_now(now)
    plot, trace_id = _extract_brief_inputs(brief)

    # Defensive: facing must be the enum (Plot.__post_init__ doesn't enforce
    # this, only the dim/road/city bounds — see domain/plot.py).
    if not isinstance(plot.facing, PlotOrientation):
        raise ValueError(
            f"plot.facing must be PlotOrientation; got "
            f"{type(plot.facing).__name__}"
        )

    # v0.7 (walks #1, #4): centralized validate_city helper replaces the
    # inline normalize+check. Plot.__post_init__ already guarantees
    # plot.city is a normalized supported city; this call is belt-and-
    # braces in case future callers bypass __post_init__.
    city = validate_city(plot.city)

    # ── Tier + shape + dimensions ──────────────────────────────────────
    area_sqm = plot.width_m * plot.depth_m
    area_sqft = area_sqm * _SQM_PER_SQFT_INV
    tier = _classify_tier(area_sqm)              # v0.6: compare in sqm space
    aspect_ratio = plot.depth_m / plot.width_m   # > 1 = deep; < 1 = wide

    # ── Solar geometry ─────────────────────────────────────────────────
    latitude_deg = lookup_latitude(city)
    sun_path = compute_sun_path(latitude_deg)

    # ── Climate ────────────────────────────────────────────────────────
    climate_zone = lookup_climate_zone(city)

    # ── Wind ───────────────────────────────────────────────────────────
    # PREVAILING_WIND is keyed by city; verify_kb_consistency() guarantees
    # presence for every supported city.
    prevailing_wind = PREVAILING_WIND[city]

    # ── Soil ───────────────────────────────────────────────────────────
    soil_estimate = estimate_soil(plot)

    # ── Site context ───────────────────────────────────────────────────
    road_width_classification = _classify_road(plot.road_width_m)
    neighbour_context = derive_neighbour_context(plot)

    # ── Provenance ─────────────────────────────────────────────────────
    provenance = PlotAnalysisProvenance(
        derived_at=float(now),
        source_versions=MappingProxyType(kb_versions()),
    )

    return PlotAnalysis(
        trace_id=trace_id,
        plot=plot,
        area_sqft=area_sqft,
        area_sqm=area_sqm,
        tier=tier,
        shape=PlotShape.RECTANGULAR,           # v1: always rectangular
        shape_metadata=MappingProxyType({}),   # SC-1: true immutability
        aspect_ratio=aspect_ratio,
        sun_path=sun_path,
        climate_zone=climate_zone,
        baseline_room_orientation_guidelines=BASELINE_ROOM_ORIENTATION_GUIDELINES,
        prevailing_wind=prevailing_wind,
        soil_estimate=soil_estimate,
        road_width_classification=road_width_classification,
        neighbour_context=neighbour_context,
        provenance=provenance,
    )


__all__ = ["derive"]


# ============================================================================
# FILE 10/18  ::  C4 package  ::  components/c04/__init__.py
# LOC: 50 total, 44 non-blank/non-comment
# ============================================================================

"""
BuildemUp† — Component 4 (Plot Analysis) package init.

Per spec § 5: calls verify_kb_consistency() at import (fail-fast on
KB drift). Re-exports the public entry point `derive` and the public
schema names that downstream components (C5+) consume.

†= placeholder name marker.
"""
from buildemup.components.c04.plot_analysis import derive
from buildemup.components.c04.schema import (
    BASELINE_ROOM_ORIENTATION_GUIDELINES,
    LEFT_RIGHT_BY_FACING,
    ClimateZone,
    ConfidenceLevel,
    NeighbourContext,
    PlotAnalysis,
    PlotAnalysisProvenance,
    PlotShape,
    PlotTier,
    RoadWidthClass,
    SoilEstimate,
    SunPath,
    WindContext,
    compute_plot_facing_sides,
)

# Fail-fast KB drift check — raises RuntimeError if any supported city
# is missing from any of the 4 KBs. Runs once per process at import.
from buildemup.kb.city_geography import verify_kb_consistency as _verify_kb
_verify_kb()
del _verify_kb

__all__ = [
    "derive",
    "PlotAnalysis",
    "PlotAnalysisProvenance",
    "PlotTier",
    "PlotShape",
    "ClimateZone",
    "ConfidenceLevel",
    "RoadWidthClass",
    "SunPath",
    "WindContext",
    "SoilEstimate",
    "NeighbourContext",
    "BASELINE_ROOM_ORIENTATION_GUIDELINES",
    "LEFT_RIGHT_BY_FACING",
    "compute_plot_facing_sides",
]


# ============================================================================
# FILE 11/18  ::  Test fixtures  ::  tests/validation/_c4_fixtures.py
# LOC: 84 total, 62 non-blank/non-comment
# ============================================================================

"""C4 test helpers — minimal stubs for the ResolvedBrief contract.

C4 only reads `brief.revised_brief.plot` and `brief.revised_brief.trace_id`.
Building a full ResolvedBrief in unit tests is needlessly heavy (and
couples C4 unit tests to C3a domain code). We use lightweight namespace
stubs with the two attributes C4 actually consumes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from buildemup.domain.plot import Plot, PlotType, SharedSide, SoilType
from buildemup.domain.envelope import PlotOrientation


@dataclass(frozen=True)
class _RevisedStub:
    plot: Plot
    trace_id: str


@dataclass(frozen=True)
class _BriefStub:
    revised_brief: _RevisedStub


def make_brief(plot: Plot, *, trace_id: str = "trace-test-001") -> _BriefStub:
    """Return a minimal stub satisfying C4's ResolvedBrief contract."""
    return _BriefStub(revised_brief=_RevisedStub(plot=plot, trace_id=trace_id))


def chennai_30x40() -> Plot:
    """30×40 ft Chennai plot (≈ 9.144 × 12.192 m, ~1200 sqft = T1)."""
    return Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTHEAST,
        city="chennai", road_width_m=9.0,
    )


def bangalore_40x60() -> Plot:
    """40×60 ft Bangalore plot (12.192 × 18.288 m exactly = textbook 2400 sqft → T2).

    v0.5 needed a nudge to 12.20 × 18.30 because tier was classified in
    sqft space and 12.192 × 18.288 × 10.7639 = 2399.998 (one ulp short
    of the boundary). v0.6 (walk #1) compares in sqm using the exact
    factor 0.09290304 — 12.192 × 18.288 = 222.967296 sqm matches
    _T2_MIN_SQM = 2400 × 0.09290304 = 222.967296 sqm exactly. Fixture
    restored to the textbook 40×60 ft to also serve as the boundary
    test case.
    """
    return Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.EAST,
        city="bangalore", road_width_m=12.0,
    )


def delhi_60x90() -> Plot:
    """60×90 ft Delhi plot (≈ 18.288 × 27.432 m, ~5400 sqft = T3)."""
    return Plot(
        width_m=18.288, depth_m=27.432, facing=PlotOrientation.SOUTH,
        city="delhi", road_width_m=15.0,
    )


def mumbai_30x40() -> Plot:
    return Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.WEST,
        city="mumbai", road_width_m=9.0,
    )


def pune_30x40() -> Plot:
    return Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTH,
        city="pune", road_width_m=8.0,
    )


def hyderabad_30x40() -> Plot:
    return Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTH,
        city="hyderabad", road_width_m=9.0,
    )


# ============================================================================
# FILE 12/18  ::  Tests  ::  tests/validation/test_c4_plot_analysis.py
# LOC: 529 total, 396 non-blank/non-comment
# ============================================================================

"""Tier-1 unit tests for C4 (Plot Analysis) — main behavioural surface.

Per SPEC v0.5 LOCKED § 7.
"""
from __future__ import annotations

import time

import pytest

from buildemup.components.c04 import derive
from buildemup.components.c04.schema import (
    BASELINE_ROOM_ORIENTATION_GUIDELINES,
    ClimateZone,
    ConfidenceLevel,
    PlotShape,
    PlotTier,
    RoadWidthClass,
    compute_plot_facing_sides,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot, PlotType, SharedSide, SoilType

from buildemup.tests.validation._c4_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    hyderabad_30x40,
    make_brief,
    mumbai_30x40,
    pune_30x40,
)


# ─── Tier classification ─────────────────────────────────────────────────

def test_tier_t1_compact_chennai_30x40():
    """30×40ft (≈1200 sqft) is T1_COMPACT."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.tier == PlotTier.T1_COMPACT
    assert 1190.0 < pa.area_sqft < 1210.0


def test_tier_t2_standard_bangalore_40x60():
    """Textbook 40×60 ft (exactly 2400 sqft via sqm-space comparison) is T2_STANDARD."""
    pa = derive(make_brief(bangalore_40x60()), now=1.0)
    assert pa.tier == PlotTier.T2_STANDARD
    # Display sqft will read ~2399.998 (from 10.7639 conversion); tier is correct.
    assert 2399.0 < pa.area_sqft < 2401.0


def test_tier_boundary_at_2400_sqft_lands_in_t2():
    """v0.6 (walk #1): 40×60 ft = 12.192×18.288 m exactly maps to 2400 sqft.

    Sqm-space comparison must classify this as T2, not T1. v0.5 sqft-space
    comparison misclassified due to the 10.7639 rounding factor.
    """
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.EAST,
        city="chennai", road_width_m=9.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.tier == PlotTier.T2_STANDARD, (
        f"40×60 ft (textbook 2400 sqft) must be T2; got {pa.tier}. "
        f"area_sqm={pa.area_sqm}, area_sqft_display={pa.area_sqft}"
    )


def test_tier_t3_large_delhi_60x90():
    """60×90ft (≈5400 sqft) is T3_LARGE."""
    pa = derive(make_brief(delhi_60x90()), now=1.0)
    assert pa.tier == PlotTier.T3_LARGE
    assert 5390.0 < pa.area_sqft < 5410.0


# ─── Climate zones (5 covered, 2 unmapped in v1) ─────────────────────────

def test_climate_zone_chennai_is_warm_humid():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.climate_zone == ClimateZone.WARM_HUMID


def test_climate_zone_bangalore_is_temperate():
    pa = derive(make_brief(bangalore_40x60()), now=1.0)
    assert pa.climate_zone == ClimateZone.TEMPERATE


def test_climate_zone_pune_is_temperate():
    pa = derive(make_brief(pune_30x40()), now=1.0)
    assert pa.climate_zone == ClimateZone.TEMPERATE


def test_climate_zone_delhi_is_composite():
    pa = derive(make_brief(delhi_60x90()), now=1.0)
    assert pa.climate_zone == ClimateZone.COMPOSITE


def test_climate_zone_hyderabad_is_composite():
    pa = derive(make_brief(hyderabad_30x40()), now=1.0)
    assert pa.climate_zone == ClimateZone.COMPOSITE


def test_climate_zone_no_v1_city_is_cold_or_hot_dry():
    """No v1 city should map to HOT_DRY or COLD (per spec § 4.4.1)."""
    from buildemup.kb.city_geography import CITY_GEOGRAPHY
    forbidden = {ClimateZone.HOT_DRY, ClimateZone.COLD}
    for city, geo in CITY_GEOGRAPHY.items():
        assert geo.climate_zone not in forbidden, (
            f"{city} maps to {geo.climate_zone} — no v1 city should be HOT_DRY/COLD"
        )


def test_baseline_orientations_cover_all_5_zones():
    """All 5 climate zones must have a guidelines entry (incl. reserved)."""
    assert set(BASELINE_ROOM_ORIENTATION_GUIDELINES.keys()) == set(ClimateZone)
    for zone, rooms in BASELINE_ROOM_ORIENTATION_GUIDELINES.items():
        assert {"living", "kitchen", "bedroom", "bathroom"} <= set(rooms.keys())
        for room, orientations in rooms.items():
            assert len(orientations) >= 1, f"{zone}.{room} has no orientations"
            for o in orientations:
                assert isinstance(o, PlotOrientation)


# ─── Neighbour context (DETACHED / SEMI_DETACHED / CONTINUOUS / corner) ──

def test_neighbour_context_detached_4_facades():
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.EAST,
        city="chennai", road_width_m=9.0, plot_type=PlotType.DETACHED,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.raw_facade_count == 4
    assert len(pa.neighbour_context.shared_sides) == 0
    assert len(pa.neighbour_context.open_sides) == 4


def test_neighbour_context_semidetached_left_facing_north_translates_to_west():
    """N-facing plot, shared_side=LEFT translates to compass WEST."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.SEMI_DETACHED, shared_side=SharedSide.LEFT,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.shared_sides == (PlotOrientation.WEST,)
    assert pa.neighbour_context.raw_facade_count == 3
    # The 3 open sides are front (N), back (S), right (E)
    assert set(pa.neighbour_context.open_sides) == {
        PlotOrientation.NORTH, PlotOrientation.SOUTH, PlotOrientation.EAST
    }


def test_neighbour_context_continuous_2_facades():
    """CONTINUOUS plots share both side walls — only front + back open."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0, plot_type=PlotType.CONTINUOUS,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.raw_facade_count == 2
    assert set(pa.neighbour_context.open_sides) == {
        PlotOrientation.NORTH, PlotOrientation.SOUTH
    }
    assert set(pa.neighbour_context.shared_sides) == {
        PlotOrientation.WEST, PlotOrientation.EAST
    }


def test_neighbour_context_corner_plot_extra_open_side():
    """Corner CONTINUOUS plot: one shared side gets promoted to open."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.CONTINUOUS,
        corner_plot=True, second_road_width_m=6.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    # 3 open sides (1 promoted from shared), 1 shared side remaining
    assert pa.neighbour_context.raw_facade_count == 3
    assert len(pa.neighbour_context.shared_sides) == 1


def test_compute_plot_facing_sides_for_all_8_orientations():
    """compute_plot_facing_sides returns front/back/left/right for all 8 facings."""
    expected = {
        PlotOrientation.NORTH: ("N", "S", "W", "E"),
        PlotOrientation.SOUTH: ("S", "N", "E", "W"),
        PlotOrientation.EAST:  ("E", "W", "N", "S"),
        PlotOrientation.WEST:  ("W", "E", "S", "N"),
        PlotOrientation.NORTHEAST: ("NE", "SW", "NW", "SE"),
        PlotOrientation.SOUTHEAST: ("SE", "NW", "NE", "SW"),
        PlotOrientation.SOUTHWEST: ("SW", "NE", "SE", "NW"),
        PlotOrientation.NORTHWEST: ("NW", "SE", "SW", "NE"),
    }
    for facing, (f, b, l, r) in expected.items():
        sides = compute_plot_facing_sides(facing)
        assert sides["front"].value == f, f"{facing}.front"
        assert sides["back"].value  == b, f"{facing}.back"
        assert sides["left"].value  == l, f"{facing}.left"
        assert sides["right"].value == r, f"{facing}.right"


# ─── Soil estimate ───────────────────────────────────────────────────────

def test_soil_estimate_uses_user_input_with_confidence_high():
    """If plot.soil_type_known is set, use it with HIGH confidence."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        soil_type_known=SoilType.HARD_ROCK,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.soil_estimate.soil_type == SoilType.HARD_ROCK
    assert pa.soil_estimate.confidence == ConfidenceLevel.HIGH
    assert pa.soil_estimate.source == "user_input"
    assert pa.soil_estimate.bearing_capacity_kpa == 1620.0


def test_soil_estimate_falls_back_to_city_default_with_confidence_medium():
    """Chennai default → MEDIUM_CLAY, MEDIUM confidence (not high-variability)."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.soil_estimate.soil_type == SoilType.MEDIUM_CLAY
    assert pa.soil_estimate.confidence == ConfidenceLevel.MEDIUM
    assert pa.soil_estimate.source == "city_default"
    assert pa.soil_estimate.bearing_capacity_kpa == pytest.approx(117.7)


def test_soil_estimate_mumbai_city_default_returns_confidence_low():
    """Mumbai default → FILLED_UP (high-variability) → LOW confidence (CG-7)."""
    pa = derive(make_brief(mumbai_30x40()), now=1.0)
    assert pa.soil_estimate.soil_type == SoilType.FILLED_UP
    assert pa.soil_estimate.confidence == ConfidenceLevel.LOW
    assert pa.soil_estimate.source == "city_default"


# ─── Road width classification (universal 6/12m, per Path B) ─────────────

def test_road_width_classification_uses_universal_thresholds():
    cases = [
        (1.5, RoadWidthClass.NARROW),
        (5.99, RoadWidthClass.NARROW),
        (6.0, RoadWidthClass.STANDARD),
        (9.0, RoadWidthClass.STANDARD),
        (11.99, RoadWidthClass.STANDARD),
        (12.0, RoadWidthClass.WIDE),
        (24.0, RoadWidthClass.WIDE),
    ]
    for road_m, expected in cases:
        plot = Plot(
            width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
            city="chennai", road_width_m=road_m,
        )
        pa = derive(make_brief(plot), now=1.0)
        assert pa.road_width_classification == expected, (
            f"road {road_m}m → {pa.road_width_classification}, expected {expected}"
        )


# ─── City normalization ──────────────────────────────────────────────────

def test_city_normalization_handles_uppercase_and_whitespace():
    """Plot.__post_init__ does the normalization; C4 still tolerates it."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="  Chennai  ", road_width_m=9.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.plot.city == "chennai"
    assert pa.climate_zone == ClimateZone.WARM_HUMID


# ─── Failure modes ───────────────────────────────────────────────────────

def test_below_600_sqft_raises_value_error():
    """A 3×3m plot is ~97 sqft — should fail tier classification."""
    # Plot constructor enforces ≥ 3.0m bounds, so 3×3m is the smallest.
    plot = Plot(
        width_m=3.0, depth_m=3.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=3.0,
    )
    with pytest.raises(ValueError, match="600sqft"):
        derive(make_brief(plot), now=1.0)


def test_invalid_latitude_raises_value_error():
    """sun_path computation rejects implausible lat (defense in depth)."""
    from buildemup.components.c04.sun_path import compute_sun_path
    with pytest.raises(ValueError, match="latitude"):
        compute_sun_path(60.0)
    with pytest.raises(ValueError, match="latitude"):
        compute_sun_path(-50.0)


def test_now_zero_or_negative_raises_value_error():
    plot = chennai_30x40()
    with pytest.raises(ValueError, match=r"now"):
        derive(make_brief(plot), now=0.0)
    with pytest.raises(ValueError, match=r"now"):
        derive(make_brief(plot), now=-5.0)


def test_now_non_float_raises_type_error():
    plot = chennai_30x40()
    with pytest.raises(TypeError, match=r"now"):
        derive(make_brief(plot), now="not-a-float")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"now"):
        derive(make_brief(plot), now=None)           # type: ignore[arg-type]
    # bool is a numeric subclass in Python; we explicitly reject it.
    with pytest.raises(TypeError, match=r"now"):
        derive(make_brief(plot), now=True)           # type: ignore[arg-type]


def test_shape_consumer_guard_raises_for_non_rectangular():
    """Per spec § 4.2: any consumer of shape_metadata that sees a non-RECTANGULAR
    shape MUST raise NotImplementedError. v1 always returns RECTANGULAR; this
    test simulates the future consumer guard."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.shape == PlotShape.RECTANGULAR

    # Simulate a future consumer pattern that would touch shape_metadata
    # only for non-rectangular shapes — guard must raise.
    def consumer(shape: PlotShape) -> None:
        if shape != PlotShape.RECTANGULAR:
            raise NotImplementedError("v1 supports rectangular only; B-066")
    with pytest.raises(NotImplementedError, match="B-066"):
        consumer(PlotShape.L_SHAPED)
    with pytest.raises(NotImplementedError, match="B-066"):
        consumer(PlotShape.IRREGULAR)


# ─── ResolvedBrief input contract (CG-9) ─────────────────────────────────

def test_derive_reads_plot_from_revised_brief():
    """C4 reads brief.revised_brief.plot, NOT brief.plot."""
    plot = chennai_30x40()
    brief = make_brief(plot, trace_id="trace-A")
    pa = derive(brief, now=1.0)
    # Round-trip: the same Plot object must come back on the output.
    assert pa.plot is plot

    # And a malformed brief (missing revised_brief) must raise ValueError,
    # not AttributeError.
    class _NoRevised:
        pass
    with pytest.raises(ValueError, match="revised_brief"):
        derive(_NoRevised(), now=1.0)


def test_derive_reads_trace_id_from_revised_brief():
    """C4 reads brief.revised_brief.trace_id and surfaces it on PlotAnalysis."""
    plot = chennai_30x40()
    brief = make_brief(plot, trace_id="trace-XYZ-123")
    pa = derive(brief, now=1.0)
    assert pa.trace_id == "trace-XYZ-123"

    # Missing trace_id raises ValueError, not AttributeError.
    from types import SimpleNamespace
    no_trace = SimpleNamespace(plot=plot)        # no trace_id attribute
    wrap = SimpleNamespace(revised_brief=no_trace)
    with pytest.raises(ValueError, match="trace_id"):
        derive(wrap, now=1.0)


# ─── v0.6 SPEC-AMENDMENT tests ─────────────────────────────────────────────

# § 14.2 Soil provenance_note (walks #2, #7)
def test_soil_estimate_chennai_default_has_no_provenance_note():
    """Stable city defaults carry no provenance_note (None)."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.soil_estimate.provenance_note is None


def test_soil_estimate_mumbai_carries_high_variability_note():
    """Mumbai default → FILLED_UP → provenance_note breadcrumbs the variability."""
    pa = derive(make_brief(mumbai_30x40()), now=1.0)
    note = pa.soil_estimate.provenance_note
    assert note is not None
    assert "filled_up" in note
    assert "high_variability" in note
    assert "site_survey_required" in note


def test_soil_estimate_user_input_medium_rock_carries_b074_breadcrumb():
    """User-input MEDIUM_ROCK is approximated to SOFT_ROCK 660 kPa; note must say so."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        soil_type_known=SoilType.MEDIUM_ROCK,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.soil_estimate.confidence == ConfidenceLevel.HIGH
    assert pa.soil_estimate.bearing_capacity_kpa == 660.0
    note = pa.soil_estimate.provenance_note
    assert note is not None
    assert "medium_rock" in note
    assert "soft_rock" in note
    assert "underestimate" in note
    assert "b074" in note


def test_soil_estimate_user_input_hard_rock_has_no_provenance_note():
    """Cleanly-mapped user inputs (no approximation) carry no note."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        soil_type_known=SoilType.HARD_ROCK,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.soil_estimate.provenance_note is None


# § 14.3 Wind confidence (walk #3)
def test_all_prevailing_wind_entries_carry_medium_confidence_until_b070():
    """Every per-city WindContext currently carries MEDIUM (single-station IMD)."""
    from buildemup.kb.wind_direction import PREVAILING_WIND
    for city, wc in PREVAILING_WIND.items():
        assert wc.confidence == ConfidenceLevel.MEDIUM, (
            f"{city} wind confidence is {wc.confidence}; v0.6 spec requires "
            f"MEDIUM until B-070 promotes per-city wind-rose to HIGH"
        )


def test_plot_analysis_surfaces_wind_confidence():
    """PlotAnalysis.prevailing_wind exposes the .confidence field."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.prevailing_wind.confidence == ConfidenceLevel.MEDIUM


# § 14.5 Corner assumption surfacing (walk #5)
def test_non_corner_carries_no_assumption():
    """Non-corner plots have corner_assumption = None."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.CONTINUOUS,
        corner_plot=False,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.corner_assumption is None


def test_corner_continuous_carries_b076_assumption_breadcrumb():
    """CONTINUOUS+corner uses the v1 LEFT default → assumption surfaced."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.CONTINUOUS,
        corner_plot=True, second_road_width_m=6.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    note = pa.neighbour_context.corner_assumption
    assert note is not None
    assert "second_street" in note
    assert "LEFT" in note
    assert "b076" in note


def test_corner_semidetached_carries_no_assumption():
    """SEMI_DETACHED+corner is deterministic from shared_side → no assumption."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.SEMI_DETACHED, shared_side=SharedSide.LEFT,
        corner_plot=True, second_road_width_m=6.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.corner_assumption is None


# ─── v0.7 SPEC-AMENDMENT tests ──────────────────────────────────────────────

# § 14.1: centralized normalize_city + validate_city (walks #1, #4)
def test_normalize_city_handles_uppercase_and_whitespace():
    """normalize_city is the canonical lowercase/strip helper."""
    from buildemup.components.c04.climate_zone import normalize_city
    assert normalize_city("  Chennai  ") == "chennai"
    assert normalize_city("DELHI") == "delhi"
    assert normalize_city("bangalore") == "bangalore"


def test_normalize_city_rejects_non_str():
    """Type contract: city must be str."""
    from buildemup.components.c04.climate_zone import normalize_city
    with pytest.raises(TypeError, match="city must be str"):
        normalize_city(123)              # type: ignore[arg-type]
    with pytest.raises(TypeError, match="city must be str"):
        normalize_city(None)             # type: ignore[arg-type]


def test_validate_city_returns_normalized_name_for_supported():
    """validate_city normalizes and verifies membership."""
    from buildemup.components.c04.climate_zone import validate_city
    assert validate_city("Chennai") == "chennai"
    assert validate_city("  DELHI  ") == "delhi"


def test_validate_city_raises_for_unsupported():
    """Unsupported city raises ValueError with helpful message."""
    from buildemup.components.c04.climate_zone import validate_city
    with pytest.raises(ValueError, match=r"missing from CITY_GEOGRAPHY"):
        validate_city("kolkata")
    with pytest.raises(ValueError, match=r"missing from CITY_GEOGRAPHY"):
        validate_city("not-a-city")


# § 14.2: WindContext.basic_speed_ms is now a stored field (walk #2)
def test_wind_context_basic_speed_ms_is_stored_field_not_property():
    """v0.7: basic_speed_ms is a dataclass field, not a @property descriptor."""
    import inspect
    from buildemup.components.c04.schema import WindContext
    # Property descriptor would show up via getattr_static on the CLASS.
    descriptor = inspect.getattr_static(WindContext, "basic_speed_ms", None)
    assert not isinstance(descriptor, property), (
        "basic_speed_ms should be a stored dataclass field per v0.7 §14.2, "
        "not a @property descriptor."
    )
    # And it must show up in __dataclass_fields__.
    assert "basic_speed_ms" in WindContext.__dataclass_fields__


def test_wind_context_basic_speed_ms_value_matches_wind_load_kb():
    """Eager-resolved basic_speed_ms equals kb.wind_load value at module load."""
    from buildemup.kb.wind_direction import PREVAILING_WIND
    from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS
    for city, wc in PREVAILING_WIND.items():
        assert wc.basic_speed_ms == float(BASIC_WIND_SPEED_MS[city]), (
            f"{city}: basic_speed_ms ({wc.basic_speed_ms}) != "
            f"wind_load value ({BASIC_WIND_SPEED_MS[city]})"
        )


# ============================================================================
# FILE 13/18  ::  Tests  ::  tests/validation/test_c4_kb_consistency.py
# LOC: 74 total, 50 non-blank/non-comment
# ============================================================================

"""Tier-1 unit tests for C4 KB drift detection.

Per SPEC v0.5 LOCKED § 7.
"""
from __future__ import annotations

import pytest

from buildemup.kb.city_geography import CITY_GEOGRAPHY, verify_kb_consistency
from buildemup.domain.plot import SUPPORTED_CITIES


def test_kb_consistency_passes_for_supported_cities():
    """All 4 KBs cover every SUPPORTED_CITIES — no exception raised."""
    verify_kb_consistency()  # raises RuntimeError if drift


def test_verify_kb_consistency_callable_explicitly():
    """The function is callable as a free function (not just at module init)."""
    # We call it twice — must be idempotent.
    verify_kb_consistency()
    verify_kb_consistency()


def test_kb_drift_detected_when_supported_city_missing(monkeypatch):
    """Removing a city from one KB makes verify_kb_consistency raise."""
    from buildemup.kb import wind_load

    # Monkeypatch BASIC_WIND_SPEED_MS to drop "chennai".
    original = wind_load.BASIC_WIND_SPEED_MS
    pruned = {k: v for k, v in original.items() if k != "chennai"}
    monkeypatch.setattr(wind_load, "BASIC_WIND_SPEED_MS", pruned)

    with pytest.raises(RuntimeError, match=r"KB drift.*wind_load.*chennai"):
        verify_kb_consistency()


# ─── v0.6 § 14.4: KB sanity-range drift checks (walk #6) ─────────────────

def test_kb_drift_detected_for_out_of_range_wind_speed(monkeypatch):
    """Wind speed outside [30, 70] m/s (per IS 875 Part 3) raises RuntimeError."""
    from buildemup.kb import wind_load
    rigged = dict(wind_load.BASIC_WIND_SPEED_MS)
    rigged["chennai"] = 999.0   # impossible
    monkeypatch.setattr(wind_load, "BASIC_WIND_SPEED_MS", rigged)

    with pytest.raises(RuntimeError, match=r"wind_load.*chennai.*999"):
        verify_kb_consistency()


def test_kb_drift_detected_for_out_of_range_latitude(monkeypatch):
    """Latitude outside India range [5, 40] raises RuntimeError."""
    from buildemup.kb import city_geography
    from buildemup.kb.city_geography import CityGeography
    from buildemup.components.c04.schema import ClimateZone
    rigged = dict(city_geography.CITY_GEOGRAPHY)
    rigged["delhi"] = CityGeography(89.0, ClimateZone.COMPOSITE)   # impossible
    monkeypatch.setattr(city_geography, "CITY_GEOGRAPHY", rigged)

    with pytest.raises(RuntimeError, match=r"city_geography.*delhi.*89"):
        verify_kb_consistency()


def test_kb_drift_detected_for_out_of_range_kpa(monkeypatch):
    """Bearing capacity outside [10, 2000] kPa raises RuntimeError."""
    from buildemup.kb import soil_city_defaults
    from buildemup.kb.soil_city_defaults import SoilCityProfile
    from buildemup.domain.plot import SoilType
    rigged = dict(soil_city_defaults.SOIL_PROFILES)
    rigged["mumbai"] = SoilCityProfile(SoilType.FILLED_UP, 9999.0)   # impossible
    monkeypatch.setattr(soil_city_defaults, "SOIL_PROFILES", rigged)

    with pytest.raises(RuntimeError, match=r"soil_city_defaults.*mumbai.*9999"):
        verify_kb_consistency()


# ============================================================================
# FILE 14/18  ::  Tests  ::  tests/validation/test_c4_immutability.py
# LOC: 50 total, 37 non-blank/non-comment
# ============================================================================

"""Tier-1 unit tests for C4 output immutability (SC-1).

Per SPEC v0.5 LOCKED § 7. MappingProxyType wraps shape_metadata,
baseline_room_orientation_guidelines (outer + inner), and
provenance.source_versions.
"""
from __future__ import annotations

from types import MappingProxyType

import pytest

from buildemup.components.c04 import derive
from buildemup.tests.validation._c4_fixtures import chennai_30x40, make_brief


def test_shape_metadata_is_mappingproxytype():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert isinstance(pa.shape_metadata, MappingProxyType)
    with pytest.raises(TypeError):
        pa.shape_metadata["new_key"] = "value"  # type: ignore[index]


def test_baseline_orientations_uses_mappingproxytype_outer_and_inner():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    outer = pa.baseline_room_orientation_guidelines
    assert isinstance(outer, MappingProxyType)
    # Outer mutation forbidden — item assign + del both raise TypeError.
    from buildemup.components.c04.schema import ClimateZone
    sample_zone = next(iter(outer.keys()))
    with pytest.raises(TypeError):
        outer[ClimateZone.HOT_DRY] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        del outer[sample_zone]           # type: ignore[attr-defined]
    # Inner mutation forbidden too
    for zone, inner in outer.items():
        assert isinstance(inner, MappingProxyType), f"{zone} inner not MappingProxyType"
        with pytest.raises(TypeError):
            inner["new_room"] = ()       # type: ignore[index]


def test_provenance_source_versions_is_mappingproxytype():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert isinstance(pa.provenance.source_versions, MappingProxyType)
    # The 4 KBs must each have a version entry
    assert {"city_geography", "wind_load", "soil_city_defaults", "wind_direction"} <= set(
        pa.provenance.source_versions.keys()
    )
    with pytest.raises(TypeError):
        pa.provenance.source_versions["spoof"] = "v0"  # type: ignore[index]


# ============================================================================
# FILE 15/18  ::  Tests  ::  tests/validation/test_c4_solar.py
# LOC: 69 total, 52 non-blank/non-comment
# ============================================================================

"""Tier-1 unit tests for C4 solar geometry (Cooper 1969).

Per SPEC v0.5 LOCKED § 7. 1° tolerance per Cooper-1969 published
accuracy of ~0.5–1° at solstices for closed-form declination.

Golden dataset: 6 cities × 2 solstices = 12 reference values.
"""
from __future__ import annotations

import pytest

from buildemup.components.c04 import derive
from buildemup.components.c04.sun_path import compute_sun_path
from buildemup.kb.city_geography import CITY_GEOGRAPHY
from buildemup.tests.validation._c4_fixtures import (
    chennai_30x40,
    delhi_60x90,
    make_brief,
)


# ─── 12-value golden dataset (computed via 90 - |lat - decl|) ──────────────
# decl_summer = +23.45°, decl_winter = -23.45° (Cooper 1969 at solstice DOY).
# Tolerance: 1° per published Cooper-1969 accuracy.
_TOLERANCE_DEG = 1.0

GOLDEN_NOON_ALTITUDES = {
    # city: (summer_solstice_alt, winter_solstice_alt)
    "chennai":   (79.63, 53.47),
    "mumbai":    (85.63, 47.47),
    "bangalore": (79.52, 53.58),
    "pune":      (85.07, 48.03),
    "delhi":     (84.84, 37.94),
    "hyderabad": (83.94, 49.16),
}


def test_solar_chennai_summer_noon_alt_within_1deg_of_known():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    expected_summer, _ = GOLDEN_NOON_ALTITUDES["chennai"]
    assert pa.sun_path.summer_solstice_noon_alt == pytest.approx(
        expected_summer, abs=_TOLERANCE_DEG
    )


def test_solar_delhi_winter_solstice_alt_within_1deg_of_known():
    pa = derive(make_brief(delhi_60x90()), now=1.0)
    _, expected_winter = GOLDEN_NOON_ALTITUDES["delhi"]
    assert pa.sun_path.winter_solstice_noon_alt == pytest.approx(
        expected_winter, abs=_TOLERANCE_DEG
    )


def test_solar_golden_dataset_6_cities_2_solstices_within_1deg():
    """Full 12-value golden dataset — every supported city × both solstices."""
    failures: list[str] = []
    for city, (expected_summer, expected_winter) in GOLDEN_NOON_ALTITUDES.items():
        sun_path = compute_sun_path(CITY_GEOGRAPHY[city].latitude_deg)
        if abs(sun_path.summer_solstice_noon_alt - expected_summer) > _TOLERANCE_DEG:
            failures.append(
                f"{city} summer: got {sun_path.summer_solstice_noon_alt:.2f}°, "
                f"expected {expected_summer:.2f}°"
            )
        if abs(sun_path.winter_solstice_noon_alt - expected_winter) > _TOLERANCE_DEG:
            failures.append(
                f"{city} winter: got {sun_path.winter_solstice_noon_alt:.2f}°, "
                f"expected {expected_winter:.2f}°"
            )
    assert not failures, "Solar golden-dataset mismatches:\n" + "\n".join(failures)


# ============================================================================
# FILE 16/18  ::  Tests  ::  tests/validation/test_c4_performance.py
# LOC: 56 total, 42 non-blank/non-comment
# ============================================================================

"""Tier-1 perf test for C4: derive() under 3ms typical (v0.7 walk #6).

Per SPEC v0.7 LOCKED § 14.4. Relaxed from v0.6's 1ms cap to absorb CI
runner variability while still catching meaningful regressions.

Cap evolution:
  v0.5: 10  ms (very loose; ~666× current p95)
  v0.6:  1  ms (tight;       ~66× current p95)
  v0.7:  3  ms (balanced;   ~200× current p95)

S29 measured baseline (1000 warmed calls on dev host):
  min:   0.009ms     p50:   0.010ms     p95:   0.015ms
  p99:   0.031ms     max:   0.064ms     mean:  0.011ms

Why 3 ms (not 1 ms):
  - Typical CI runners are 5-15× slower than a dev host. p95 on a slow
    CI runner could push to ~0.15-0.25ms — still well under 3 ms.
  - 1 ms cap creates flake risk if a CI runner has competing load.
  - 3 ms still catches a 200× regression — i.e., any change that adds
    accidental I/O, network calls, or O(n²) loops will trip the test.
  - Configurable-per-environment is over-engineering for current scale
    (single-developer project, no CI yet).
"""
from __future__ import annotations

import time

from buildemup.components.c04 import derive
from buildemup.tests.validation._c4_fixtures import chennai_30x40, make_brief


def test_derive_completes_under_3ms_for_typical_plot():
    """1000-call P95 must beat 3.0 ms.

    Sample size is 1000 (was 100 in v0.5) for tighter p95 confidence.
    """
    brief = make_brief(chennai_30x40())

    # Warm up — avoid first-call import / JIT effects skewing the sample.
    for _ in range(50):
        derive(brief, now=1.0)

    samples_ms: list[float] = []
    for _ in range(1000):
        t0 = time.perf_counter()
        derive(brief, now=1.0)
        samples_ms.append((time.perf_counter() - t0) * 1000.0)

    samples_ms.sort()
    p95 = samples_ms[949]   # 95th percentile of 1000 samples (index 949)

    assert p95 < 3.0, (
        f"p95 derive() time = {p95:.3f}ms — exceeds 3.0ms cap. "
        f"min={samples_ms[0]:.3f}ms, p50={samples_ms[499]:.3f}ms, "
        f"p99={samples_ms[989]:.3f}ms, max={samples_ms[-1]:.3f}ms"
    )


# ============================================================================
# FILE 17/18  ::  Tests  ::  tests/validation/test_c4_property_based.py
# LOC: 73 total, 51 non-blank/non-comment
# ============================================================================

"""Tier-1 property-based tests for C4 (Hypothesis).

Per SPEC v0.5 LOCKED § 7.
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st

from buildemup.components.c04 import derive
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot, PlotType, SUPPORTED_CITIES
from buildemup.tests.validation._c4_fixtures import make_brief


# Plot dim bounds per Plot.__post_init__: 3.0 ≤ width/depth ≤ 60.0.
# Use a narrowed range to avoid sub-600sqft (which raises by spec).
# 8m × 8m ≈ 689 sqft, just over the floor.
_DIM_MIN = 8.0
_DIM_MAX = 60.0
# Road bounds: 1.5 ≤ road ≤ 30.0
_ROAD_MIN = 1.5
_ROAD_MAX = 30.0


@st.composite
def _detached_plots(draw) -> Plot:
    """Strategy: a valid DETACHED Plot anywhere in the supported set."""
    width = draw(st.floats(min_value=_DIM_MIN, max_value=_DIM_MAX, allow_nan=False))
    depth = draw(st.floats(min_value=_DIM_MIN, max_value=_DIM_MAX, allow_nan=False))
    facing = draw(st.sampled_from(list(PlotOrientation)))
    city = draw(st.sampled_from(sorted(SUPPORTED_CITIES)))
    road = draw(st.floats(min_value=_ROAD_MIN, max_value=_ROAD_MAX, allow_nan=False))
    return Plot(
        width_m=width, depth_m=depth, facing=facing,
        city=city, road_width_m=round(road, 3),
        plot_type=PlotType.DETACHED,
    )


@given(_detached_plots())
@settings(max_examples=50, deadline=None)   # deadline=None → don't fail on slow CI
def test_area_sqft_sqm_round_trip(plot):
    """area_sqft / 10.7639 should round-trip area_sqm."""
    pa = derive(make_brief(plot), now=1.0)
    # Tight tolerance — pure float math, no cancellation.
    assert abs(pa.area_sqft / 10.7639 - pa.area_sqm) < 1e-6


@given(_detached_plots())
@settings(max_examples=50, deadline=None)
def test_aspect_ratio_inverse_for_swap(plot):
    """Swapping width and depth inverts aspect_ratio."""
    pa = derive(make_brief(plot), now=1.0)
    swapped = Plot(
        width_m=plot.depth_m, depth_m=plot.width_m,
        facing=plot.facing, city=plot.city,
        road_width_m=plot.road_width_m, plot_type=plot.plot_type,
    )
    pa_swapped = derive(make_brief(swapped), now=1.0)
    # aspect_ratio = depth/width; swap → 1/original ratio.
    assert abs(pa.aspect_ratio * pa_swapped.aspect_ratio - 1.0) < 1e-9


@given(_detached_plots())
@settings(max_examples=50, deadline=None)
def test_raw_facade_count_in_2_3_4_range(plot):
    """For any plot type + corner combo the raw_facade_count ∈ {2, 3, 4}."""
    pa = derive(make_brief(plot), now=1.0)
    # DETACHED → 4, CONTINUOUS → 2 (or 3 with corner_plot),
    # SEMI_DETACHED → 3 (or 4 with corner_plot).
    assert pa.neighbour_context.raw_facade_count in (2, 3, 4)
    # The raw_facade_count equals len(open_sides) by definition.
    assert pa.neighbour_context.raw_facade_count == len(pa.neighbour_context.open_sides)


# ============================================================================
# FILE 18/18  ::  Tests  ::  tests/validation/test_c5_consumes_plot_analysis.py
# LOC: 69 total, 55 non-blank/non-comment
# ============================================================================

"""Tier-1 guardrail tests for C5+ usage of PlotAnalysis.

Per SPEC v0.5 LOCKED § 7. SKIPPED at module level until c05/ exists,
to avoid building features without consumers (Pattern B). Activated
automatically when c05/ ships.

These tests enforce that C5 onward consumes PlotAnalysis rather than
re-deriving from raw plot — the "single source of truth" invariant
that motivates C4.
"""
from __future__ import annotations

import importlib.util

import pytest

# Module-level skip: no point running these until C5 is built.
if importlib.util.find_spec("buildemup.components.c05") is None:
    pytest.skip(
        "C5 not yet implemented — guardrail tests deferred. "
        "Activates automatically when buildemup/components/c05/ exists.",
        allow_module_level=True,
    )


def test_c5_does_not_import_plot_directly():
    """C5 source files MUST NOT import domain.plot.Plot directly.

    Negative-import test: C5 must consume PlotAnalysis (C4's output),
    not raw Plot.
    """
    import pkgutil
    import buildemup.components.c05 as c05_pkg
    forbidden = {"from buildemup.domain.plot import", "from buildemup.domain import plot"}
    offenders: list[str] = []
    for mod_info in pkgutil.walk_packages(c05_pkg.__path__, prefix="buildemup.components.c05."):
        spec = importlib.util.find_spec(mod_info.name)
        if spec is None or spec.origin is None:
            continue
        with open(spec.origin) as f:
            src = f.read()
        for pat in forbidden:
            if pat in src:
                offenders.append(f"{mod_info.name} contains '{pat}'")
    assert not offenders, "C5 must not import Plot directly:\n" + "\n".join(offenders)


def test_stub_c5_consumer_reads_plot_analysis_without_recomputation():
    """Smoke-test: a C5-shaped consumer can read everything it needs from
    PlotAnalysis without touching plot.* directly."""
    import time
    from buildemup.components.c04 import derive
    from buildemup.tests.validation._c4_fixtures import chennai_30x40, make_brief

    pa = derive(make_brief(chennai_30x40()), now=time.time())

    # A stub C5 consumer pattern: reads only PlotAnalysis fields.
    def stub_c5(plot_analysis) -> dict:
        return {
            "tier": plot_analysis.tier.value,
            "climate": plot_analysis.climate_zone.value,
            "open_facades": plot_analysis.neighbour_context.raw_facade_count,
            "soil_kpa": plot_analysis.soil_estimate.bearing_capacity_kpa,
            "summer_alt": plot_analysis.sun_path.summer_solstice_noon_alt,
        }
    bundle = stub_c5(pa)
    assert bundle["tier"] == "T1"
    assert bundle["climate"] == "warm_humid"
    assert bundle["open_facades"] == 4

