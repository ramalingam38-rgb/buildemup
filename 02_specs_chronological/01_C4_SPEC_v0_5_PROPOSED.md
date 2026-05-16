# BuildemUp Component 4 (Plot Analysis) — SPEC v0.5 PROPOSED

**Status:** **v0.5 PROPOSED. PENDING Ramalingam LOCK adjudication.** Per Rule 8, this version is not LOCKED until Ramalingam explicitly says "lock it" / "v0.5 LOCKED".

**Generated:** start of Session 29, 2 May 2026.

This v0.5 supersedes v0.4 LOCKED with **6 code-grep-round-2 fixes** found by the next Claude during the build-readiness walk. v0.4 was a clean LOCK at the time but did not run a pre-build code-grep against every name the spec referenced; v0.5 closes that gap. The 6 fixes are mechanical/structural — no architectural change. v0.4 stays in `02_specs_chronological/30_…` as the historical record; v0.5 is the build-target.

**Companion components:** outputs feed C5 (Topology Selector — CRITICAL), C6 (Orientation Priority Engine), C8 (Corridor), C14 (Unified Evaluation). C7 (Structural Grid — already shipped) currently re-derives soil; retrofit is **B-072**.

**Build position:** 4 of 17. Predecessor: C3a (just shipped). Successor: C5.

**Scope discipline:** pure-function component — `ResolvedBrief` in, `PlotAnalysis` out. No state, scheduler, idempotency cache, email hooks, or request-time I/O.

---

## § 0 — Pushback table (carried from v0.4)

| Objection | Pushback |
|---|---|
| "Why isn't C4 doing irregular-plot polygon analysis?" | Plot dataclass is `width_m × depth_m` only. Polygon entry doesn't exist upstream. **B-066**. |
| "Why solstice envelope, not per-month declination?" | C5/C6 use envelope for room-bias, not shading studies. **B-067**. Cooper 1969 accuracy is ~0.5–1° per web research. |
| "Why memoize nothing?" | Pure no-I/O function, called once per pipeline run. § 7 includes `test_derive_completes_under_10ms_for_typical_plot` to demonstrate the no-caching call holds. |
| "Why is C7 still re-deriving soil?" | Pattern E mid-build. C7 retrofit = **B-072**. |
| "Why universal 6/12m road thresholds when DCRs differ city-by-city?" | The road_width_classification is a COARSE classifier for layout heuristics. FSI-aware FAR computation is C2's job. |
| "Why 6 cities, not 10?" | `domain.plot.SUPPORTED_CITIES = {chennai, bangalore, hyderabad, mumbai, pune, delhi}`. Plot constructor enforces. |
| "Why not enforce single-source-of-truth via runtime `isinstance(input, PlotAnalysis)` everywhere?" | Type-checker (mypy) + a single import-pattern lint test catches accidental `from domain.plot import` in C5+ at CI time. Test guardrail (active when C5 ships) is the right mechanism. |
| "Why no climate × wind × sun cross-validation?" | Tautological: the tables ARE the source of truth; cross-checks reduce to "tests verify tables match tests' expectations." Pushback. |

---

## § 1 — Purpose

Given a `ResolvedBrief`, produce a `PlotAnalysis` artifact for the layout pipeline (C5–C16). C4 is the **preferred single source of truth** for plot-derived properties; C5 onward MUST consume `PlotAnalysis` rather than re-compute. C7 (already shipped) currently re-derives soil — see **B-072** for the deferred retrofit. v0.5 (and v0.4 before it) adds a guardrail test (active when C5 ships) that catches accidental NEW direct `plot.*` access in C5+ code.

**Out of scope:** setbacks (C2), topology (C5), structural grid (C7), orientation priority (C6), FSI/FAR computation (C2 / `setback_preview_endpoint`).

---

## § 2 — Input contract (v0.5 CORRECTED per CG-9)

C4 reads from a `ResolvedBrief` per the actual upstream shape (`buildemup.domain.extreme_case.ResolvedBrief`):

```python
ResolvedBrief.revised_brief: Brief                      # what goes to the layout pipeline
    .plot: domain.plot.Plot                             # ← C4 reads this
        width_m: float                # 3.0 ≤ width ≤ 60.0 (Plot constructor enforces)
        depth_m: float                # 3.0 ≤ depth ≤ 60.0
        facing: PlotOrientation       # member names: NORTH / NORTHEAST / EAST /
                                      # SOUTHEAST / SOUTH / SOUTHWEST / WEST /
                                      # NORTHWEST. Values are "N"/"NE"/etc. but
                                      # access is via full member names.
                                      # CORRECTED v0.5 (CG-5).
        city: str                     # one of SUPPORTED_CITIES (lowercase, 6 cities;
                                      # already normalized by Plot.__post_init__)
        road_width_m: float           # 1.5 ≤ road ≤ 30.0
        plot_type: PlotType           # DETACHED / SEMI_DETACHED / CONTINUOUS
        corner_plot: bool
        second_road_width_m: float | None    # required when corner_plot=True
        shared_side: SharedSide | None       # ENUM is {LEFT, RIGHT} relative to viewer
                                             # on the street facing the plot.
                                             # See § 4.9 for facing→compass translation.
        soil_type_known: SoilType | None     # 9 values per CORRECTED list below
    .trace_id: str                          # ← C4 reads this for trace correlation
                                            # CORRECTED v0.5 (CG-9): was assumed
                                            # "ResolvedBrief.metadata.brief_token"
                                            # in v0.1-v0.4 — that path doesn't exist.
                                            # Actual upstream path is
                                            # ResolvedBrief.revised_brief.trace_id.

# Actual upstream enum from buildemup/domain/plot.py:
class SoilType(str, Enum):
    HARD_ROCK     = "hard_rock"
    MEDIUM_ROCK   = "medium_rock"
    DENSE_SAND    = "dense_sand"
    MEDIUM_SAND   = "medium_sand"
    LOOSE_SAND    = "loose_sand"
    STIFF_CLAY    = "stiff_clay"
    MEDIUM_CLAY   = "medium_clay"
    SOFT_CLAY     = "soft_clay"
    FILLED_UP     = "filled_up"

SUPPORTED_CITIES = frozenset({
    "chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi",
})
```

C4 normalizes `plot.city` defensively: `city = plot.city.strip().lower()`. The Plot constructor already does this normalization, so by the time C4 runs the city is guaranteed normalized. C4 still validates `city in CITY_GEOGRAPHY` as defense-in-depth in case CITY_GEOGRAPHY drifts from SUPPORTED_CITIES.

C4 **does NOT** mutate the brief. Plot invariants (dim bounds, road bounds, facing enum, city in SUPPORTED_CITIES) are enforced upstream by `Plot.__post_init__`; C4 adds production-safe validation per § 6 using explicit `raise ValueError` (NOT `assert`).

**Facing convention:** given `plot.facing`, "front" = facing direction; "back" = opposite; "right" = 90° clockwise from front (viewer standing on street looking at plot); "left" = 90° counter-clockwise. For compound facings (NORTHEAST, SOUTHEAST, SOUTHWEST, NORTHWEST), front/back are diagonal and right/left are the perpendicular diagonals. Implementation in `compute_plot_facing_sides(facing) -> dict[Literal["front","back","left","right"], PlotOrientation]`. All 8 input values tested.

---

## § 3 — Output contract: `PlotAnalysis` (CORRECTED v0.5 per CG-9)

```python
from types import MappingProxyType


@dataclass(frozen=True)
class PlotAnalysis:
    # ─── Identity ───
    trace_id: str                                        # CORRECTED v0.5 (CG-9):
                                                          # was "brief_token" in v0.1–v0.4.
                                                          # Renamed to mirror upstream
                                                          # Brief.trace_id.
    plot: Plot                                            # frozen passthrough

    # ─── Computed properties ───
    area_sqft: float
    area_sqm: float
    tier: PlotTier
    shape: PlotShape                                      # ALWAYS RECTANGULAR in v1
    shape_metadata: Mapping[str, object]                  # MappingProxyType
    aspect_ratio: float                                   # depth/width — see § 3 conv

    # ─── Solar ───
    sun_path: SunPath                                     # geometry only

    # ─── Climate (top-level) ───
    climate_zone: ClimateZone
    baseline_room_orientation_guidelines: Mapping[ClimateZone, Mapping[str, list[PlotOrientation]]]
                                                          # MappingProxyType wraps both
                                                          # outer + inner dicts

    # ─── Wind ───
    prevailing_wind: WindContext

    # ─── Geotechnical ───
    soil_estimate: SoilEstimate

    # ─── Site context ───
    road_width_classification: RoadWidthClass             # universal 6/12m
    neighbour_context: NeighbourContext

    # ─── Provenance ───
    provenance: PlotAnalysisProvenance


@dataclass(frozen=True)
class PlotAnalysisProvenance:
    derived_at: float                                     # caller-injected (> 0)
    source_versions: Mapping[str, str]                    # MappingProxyType
    # Auto-populated from per-KB KB_VERSION at construction:
    #   "city_geography"        from kb/city_geography.KB_VERSION
    #   "wind_load"             from kb/wind_load.KB_VERSION
    #   "soil_city_defaults"    from kb/soil_city_defaults.KB_VERSION
    #                            (NEW v0.5 per CG-6/7/8 — see § 4.7.1)
    #   "wind_direction"        from kb/wind_direction.KB_VERSION


class PlotTier(str, Enum):
    T1_COMPACT  = "T1"   # 600 ≤ sqft < 2400
    T2_STANDARD = "T2"   # 2400 ≤ sqft < 4000
    T3_LARGE    = "T3"   # sqft ≥ 4000


class PlotShape(str, Enum):
    RECTANGULAR = "rectangular"
    L_SHAPED    = "l_shaped"      # B-066 forward-compat
    IRREGULAR   = "irregular"     # B-066


@dataclass(frozen=True)
class SunPath:
    latitude_deg: float
    summer_solstice_noon_alt: float
    winter_solstice_noon_alt: float
    sunrise_arc_summer: tuple[float, float]
    sunrise_arc_winter: tuple[float, float]


class ClimateZone(str, Enum):
    HOT_DRY    = "hot_dry"
    WARM_HUMID = "warm_humid"
    TEMPERATE  = "temperate"
    COMPOSITE  = "composite"
    COLD       = "cold"
    # 5 zones per NBC 2016 Part 8 Section 1, §§ 2.2.21–2.2.24 + 3.2.2.


@dataclass(frozen=True)
class WindContext:
    primary_direction: PlotOrientation     # dominant non-monsoon
    monsoon_direction: PlotOrientation     # SW or NE monsoon arrival
    city: str                              # NEW v0.5 (cosmetic) — lookup key for property
    @property
    def basic_speed_ms(self) -> float:
        """Reads from kb/wind_load.BASIC_WIND_SPEED_MS (no duplication)."""
        from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS
        return float(BASIC_WIND_SPEED_MS[self.city])


class ConfidenceLevel(str, Enum):
    LOW    = "low"      # high-variability soil region; downstream MUST apply safety factor
    MEDIUM = "medium"   # city-default for stable-soil region
    HIGH   = "high"     # user-supplied site survey


@dataclass(frozen=True)
class SoilEstimate:
    soil_type: SoilType
    bearing_capacity_kpa: float | None
    confidence: ConfidenceLevel
    source: str                            # "user_input" | "city_default"

# CONSUMER CONTRACT: downstream components reading `confidence == LOW` MUST
# apply a structural safety factor to bearing_capacity_kpa. C7 currently uses
# its own conservative defaults (B-072 retrofit will align this).


class RoadWidthClass(str, Enum):
    NARROW   = "narrow"     # < 6m
    STANDARD = "standard"   # 6–12m
    WIDE     = "wide"       # ≥ 12m


@dataclass(frozen=True)
class NeighbourContext:
    open_sides: list[PlotOrientation]    # RAW openness (NOT setback-aware — see B-068)
    shared_sides: list[PlotOrientation]
    raw_facade_count: int                # = len(open_sides). B-068 will add
                                         # usable_facade_hint.

# Aspect ratio convention: aspect_ratio = depth / width.
# Values > 1 mean a deep plot (long axis perpendicular to street).
# Values < 1 mean a wide plot (long axis parallel to street).
# = 1 is square.
```

---

## § 4 — Processing layers

### § 4.1 Tier classification

```
sqft = (width_m × depth_m) × 10.7639
tier = T1_COMPACT  if  600 ≤ sqft < 2400
       T2_STANDARD if  2400 ≤ sqft < 4000
       T3_LARGE    if         sqft ≥ 4000
```

`sqft < 600` → `raise ValueError("plot < 600sqft minimum — should have been gated by C3a")`.

### § 4.2 Shape determination

v1: ALWAYS `RECTANGULAR`. `shape_metadata = MappingProxyType({})`.
Code paths consuming `shape_metadata` MUST guard:
```python
if shape != PlotShape.RECTANGULAR:
    raise NotImplementedError("v1 supports rectangular only; B-066")
```

### § 4.3 Corner status

Passthrough.

### § 4.4 Sun-path calculation

#### § 4.4.1 KB module — `kb/city_geography.py` (NEW)

```python
from buildemup.components.c04.schema import ClimateZone

KB_VERSION = "v1.0"

@dataclass(frozen=True)
class CityGeography:
    latitude_deg: float
    climate_zone: ClimateZone


CITY_GEOGRAPHY = {
    # 6 cities matching domain.plot.SUPPORTED_CITIES exactly.
    "chennai":   CityGeography(13.08, ClimateZone.WARM_HUMID),
    "mumbai":    CityGeography(19.08, ClimateZone.WARM_HUMID),
    "bangalore": CityGeography(12.97, ClimateZone.TEMPERATE),
    "pune":      CityGeography(18.52, ClimateZone.TEMPERATE),
    "delhi":     CityGeography(28.61, ClimateZone.COMPOSITE),
    "hyderabad": CityGeography(17.39, ClimateZone.COMPOSITE),
}
# Source: NBC 2016 Part 8 Section 1, §§ 2.2.21-2.2.24 + 3.2.2;
# cross-verified with ECBC 2017 climate-zone-finder.
```

#### § 4.4.2 KB drift verification (CORRECTED v0.5 per CG-6)

```python
def verify_kb_consistency() -> None:
    """Called from C4 module init AND as explicit Tier-1 test.

    INVARIANT: every supported city must be present in EVERY KB.
    KBs may carry extras (forward-compat) but cannot be missing any
    supported city.
    """
    from buildemup.domain.plot import SUPPORTED_CITIES
    from buildemup.kb.wind_load          import BASIC_WIND_SPEED_MS, KB_VERSION as WL_VER  # noqa: F401
    from buildemup.kb.soil_city_defaults import SOIL_PROFILES,      KB_VERSION as SC_VER  # noqa: F401
    from buildemup.kb.wind_direction     import PREVAILING_WIND,    KB_VERSION as WD_VER  # noqa: F401
    # ↑ CORRECTED v0.5 (CG-6): SOIL_PROFILES now lives in
    #   kb/soil_city_defaults.py (NEW per CG-6/7/8). The old import target
    #   kb/soil_foundation_rules.py exposes CITY_SOIL_DEFAULTS (different
    #   schema, different name) and is left untouched (Pattern E).

    required = set(SUPPORTED_CITIES)

    for kb_name, kb_keys in [
        ("city_geography",      set(CITY_GEOGRAPHY.keys())),
        ("wind_load",           set(BASIC_WIND_SPEED_MS.keys())),
        ("soil_city_defaults",  set(SOIL_PROFILES.keys())),
        ("wind_direction",      set(PREVAILING_WIND.keys())),
    ]:
        missing = required - kb_keys
        if missing:
            raise RuntimeError(
                f"KB drift: kb/{kb_name} missing required supported cities: "
                f"{sorted(missing)}. All 4 KBs must contain every city in "
                f"domain.plot.SUPPORTED_CITIES."
            )
```

**Removed v0.5 (per CG-10):** the prior NOTE about "adding `KB_VERSION = 'v1.0'` to existing `kb/wind_load.py` and `kb/soil_foundation_rules.py`" is **dropped**. Both files already carry `KB_VERSION` (`"Wind_IS875_2026_v1"` and `"Soil_India_2026_v1"` respectively). C4 build does **not** modify either file. The above `verify_kb_consistency()` only imports `KB_VERSION` for presence (any value works); no value-check is performed.

#### § 4.4.3 Solar geometry (closed-form)

Cooper 1969 declination, ~0.5–1° accuracy:

```
declination = 23.45 × sin(360 × (284 + day_of_year) / 365)
solar_altitude_at_noon = 90° − |latitude − declination|
```

Computed at solstices (June 21 = day 172, Dec 21 = day 355). Per-month → **B-067**.

Validation:
```python
if not (-45 < latitude_deg < 45):
    raise ValueError(f"latitude {latitude_deg}° out of plausible range")
```

#### § 4.4.4 Baseline room orientation guidelines (TOP-LEVEL on PlotAnalysis)

Top-level field on `PlotAnalysis`, NOT nested inside `SunPath`.

```python
from buildemup.domain.envelope import PlotOrientation as PO    # CORRECTED v0.5 (CG-5):
                                                                 # use full member names.

BASELINE_ROOM_ORIENTATION_GUIDELINES = MappingProxyType({
    ClimateZone.WARM_HUMID: MappingProxyType({  # Mumbai, Chennai
        "living":   [PO.NORTH, PO.NORTHEAST],
        "kitchen":  [PO.EAST,  PO.SOUTHEAST],
        "bedroom":  [PO.NORTH, PO.NORTHEAST, PO.EAST],
        "bathroom": [PO.WEST,  PO.SOUTHWEST, PO.NORTHWEST],
    }),
    ClimateZone.TEMPERATE: MappingProxyType({   # Bangalore, Pune
        "living":   [PO.NORTH, PO.NORTHEAST, PO.EAST, PO.SOUTH],
        "kitchen":  [PO.EAST,  PO.SOUTHEAST, PO.NORTHEAST],
        "bedroom":  [PO.NORTH, PO.NORTHEAST, PO.EAST],
        "bathroom": [PO.WEST,  PO.SOUTHWEST],
    }),
    ClimateZone.COMPOSITE: MappingProxyType({   # Delhi, Hyderabad
        "living":   [PO.NORTH, PO.NORTHEAST, PO.EAST],
        "kitchen":  [PO.EAST,  PO.NORTHEAST],
        "bedroom":  [PO.NORTH, PO.NORTHEAST, PO.EAST, PO.SOUTHEAST],
        "bathroom": [PO.WEST,  PO.SOUTHWEST,  PO.NORTHWEST],
    }),
    ClimateZone.HOT_DRY: MappingProxyType({     # Reserved (no v1 city)
        "living":   [PO.NORTH, PO.NORTHEAST, PO.EAST],
        "kitchen":  [PO.EAST,  PO.NORTHEAST],
        "bedroom":  [PO.NORTH, PO.NORTHEAST, PO.EAST],
        "bathroom": [PO.WEST,  PO.SOUTHWEST],
    }),
    ClimateZone.COLD: MappingProxyType({        # Reserved (no v1 city)
        "living":   [PO.SOUTH, PO.SOUTHEAST, PO.SOUTHWEST],
        "kitchen":  [PO.EAST,  PO.SOUTHEAST],
        "bedroom":  [PO.SOUTH, PO.SOUTHEAST],
        "bathroom": [PO.NORTH, PO.NORTHWEST],
    }),
})
```

These are CLIMATE-derived heuristics. C5/C6 produce dynamic recommendations integrating baselines + plot facing + aspect ratio + neighbour openness + Vastu + brief preferences.

### § 4.5 Climate zone

`climate_zone = CITY_GEOGRAPHY[normalized_city].climate_zone`.

### § 4.6 Prevailing wind — `kb/wind_direction.py` (NEW, CORRECTED v0.5 per CG-5)

```python
from buildemup.domain.envelope import PlotOrientation as PO

KB_VERSION = "v1.0"

# Per-city wind direction. Source: Indian Meteorological Department
# climatology summaries (cited per-city below). Full IMD wind-rose
# integration is B-070.
PREVAILING_WIND = {
    "chennai":   WindContext(
        primary_direction=PO.NORTHEAST,    # NE non-monsoon (Oct–Mar)
        monsoon_direction=PO.SOUTHWEST,    # SW monsoon (Jun–Sep)
        city="chennai",                     # NEW v0.5 — for basic_speed_ms property
        # Source: IMD Chennai climatology
    ),
    "mumbai":    WindContext(
        primary_direction=PO.WEST,
        monsoon_direction=PO.SOUTHWEST,
        city="mumbai",
        # Source: IMD Santacruz station
    ),
    "bangalore": WindContext(
        primary_direction=PO.WEST,
        monsoon_direction=PO.SOUTHWEST,
        city="bangalore",
        # Source: IMD Bangalore HAL
    ),
    "pune":      WindContext(
        primary_direction=PO.WEST,
        monsoon_direction=PO.SOUTHWEST,
        city="pune",
        # Source: IMD Shivajinagar
    ),
    "hyderabad": WindContext(
        primary_direction=PO.WEST,
        monsoon_direction=PO.SOUTHWEST,
        city="hyderabad",
        # Source: IMD Begumpet
    ),
    "delhi":     WindContext(
        primary_direction=PO.NORTHWEST,    # NW winter
        monsoon_direction=PO.SOUTHEAST,    # monsoon spillover
        city="delhi",
        # Source: IMD Safdarjung
    ),
}
# All values PROPOSED pending per-city IMD wind-rose verification (B-070).
```

`WindContext.basic_speed_ms` is a property that reads from `kb/wind_load.BASIC_WIND_SPEED_MS` at access time — no duplication.

### § 4.7 Soil estimate (CORRECTED v0.5 per CG-6/7/8 — Option A typed-projection adapter)

#### § 4.7.1 New module `kb/soil_city_defaults.py` (NEW v0.5)

This module is the **typed projection adapter** between two existing soil KBs and the C4 contract. It introduces zero changes to shipped code (Pattern E safe). Both source KBs continue to be used by C7 unchanged.

```python
"""
BuildemUp — typed soil projection for C4.

Reasons (v0.5 / CG-6, CG-7, CG-8):
  - kb/soil_foundation_rules.py exposes CITY_SOIL_DEFAULTS keyed by city,
    but with `typical_soil: str` (informal labels like "rock_or_hard_clay")
    and `safe_bearing_capacity_t_sqm` (tonnes/sqm — not kPa).
  - kb/soil_classification.py exposes SOIL_PROFILES keyed by SoilClass enum
    (12 values), with sbc_typical_knm2 (kPa). Different enum from
    domain.plot.SoilType (9 values).
  - C4's contract (PlotAnalysis.soil_estimate) wants:
      * city → (SoilType, kPa)         for the city-default branch
      * SoilType → kPa                 for the user-input branch
This module provides both, sourced from the two existing KBs above with
explicit conversions and mappings. No shipped code is modified.
"""
from __future__ import annotations
from dataclasses import dataclass

from buildemup.domain.plot import SoilType


KB_VERSION = "v1.0"


@dataclass(frozen=True)
class SoilCityProfile:
    typical_soil: SoilType
    typical_bearing_capacity_kpa: float


# 1 t/sqm ≈ 9.81 kPa (g = 9.81 m/s²). City kPa values below are derived
# from kb/soil_foundation_rules.CITY_SOIL_DEFAULTS.safe_bearing_capacity_t_sqm
# multiplied by 9.81 and rounded to one decimal.
#
# typical_soil mappings (informal label → SoilType enum, conservative):
#   chennai   "clay"               → MEDIUM_CLAY
#   bangalore "rock_or_hard_clay"  → MEDIUM_ROCK   (rocky-typical)
#   mumbai    "rock_or_filled_up"  → FILLED_UP     (CONSERVATIVE: triggers
#                                                    LOW confidence — Mumbai
#                                                    docs say "MANDATORY soil
#                                                    testing")
#   delhi     "silt_clay"          → MEDIUM_CLAY
#   hyderabad "rock_or_murrum"     → MEDIUM_ROCK
#   pune      "murrum"             → STIFF_CLAY    (proxy for firm murrum)
SOIL_PROFILES: dict[str, SoilCityProfile] = {
    "chennai":   SoilCityProfile(SoilType.MEDIUM_CLAY, 117.7),   # 12.0 t/sqm
    "bangalore": SoilCityProfile(SoilType.MEDIUM_ROCK, 196.2),   # 20.0 t/sqm
    "mumbai":    SoilCityProfile(SoilType.FILLED_UP,   147.1),   # 15.0 t/sqm
    "delhi":     SoilCityProfile(SoilType.MEDIUM_CLAY, 147.1),   # 15.0 t/sqm
    "hyderabad": SoilCityProfile(SoilType.MEDIUM_ROCK, 196.2),   # 20.0 t/sqm
    "pune":      SoilCityProfile(SoilType.STIFF_CLAY,  176.6),   # 18.0 t/sqm
}


# Per-SoilType bearing capacity (typical, kPa). Values sourced from
# kb/soil_classification.SOIL_PROFILES.sbc_typical_knm2 via the
# SoilType (domain) → SoilClass (KB) mapping below. SoilType.MEDIUM_ROCK
# has no exact SoilClass equivalent; mapped to SOFT_ROCK (the closest,
# more conservative, available class).
#
# domain.SoilType   → kb.SoilClass        kb sbc_typical_knm2
#   HARD_ROCK         HARD_ROCK             1620.0
#   MEDIUM_ROCK       SOFT_ROCK              660.0   (closest available)
#   DENSE_SAND        DENSE_SAND             350.0
#   MEDIUM_SAND       MEDIUM_SAND            200.0
#   LOOSE_SAND        LOOSE_SAND             125.0
#   STIFF_CLAY        STIFF_CLAY             250.0
#   MEDIUM_CLAY       MEDIUM_CLAY            125.0
#   SOFT_CLAY         SOFT_CLAY               90.0
#   FILLED_UP         RECLAIMED_FILL          50.0
BEARING_CAPACITY_BY_TYPE: dict[SoilType, float] = {
    SoilType.HARD_ROCK:    1620.0,
    SoilType.MEDIUM_ROCK:   660.0,
    SoilType.DENSE_SAND:    350.0,
    SoilType.MEDIUM_SAND:   200.0,
    SoilType.LOOSE_SAND:    125.0,
    SoilType.STIFF_CLAY:    250.0,
    SoilType.MEDIUM_CLAY:   125.0,
    SoilType.SOFT_CLAY:      90.0,
    SoilType.FILLED_UP:      50.0,
}
```

#### § 4.7.2 estimate_soil()

```python
HIGH_VARIABILITY_SOIL_TYPES = frozenset({
    SoilType.SOFT_CLAY,    # Highly variable; site survey strongly recommended
    SoilType.LOOSE_SAND,   # Liquefaction risk; varies with water table
    SoilType.FILLED_UP,    # Made-up ground — always low-confidence
})

def estimate_soil(plot: Plot) -> SoilEstimate:
    if plot.soil_type_known is not None:
        return SoilEstimate(
            soil_type=plot.soil_type_known,
            bearing_capacity_kpa=BEARING_CAPACITY_BY_TYPE[plot.soil_type_known],
            confidence=ConfidenceLevel.HIGH,
            source="user_input",
        )
    profile = SOIL_PROFILES[plot.city]
    typical = profile.typical_soil
    confidence = (
        ConfidenceLevel.LOW if typical in HIGH_VARIABILITY_SOIL_TYPES
        else ConfidenceLevel.MEDIUM
    )
    return SoilEstimate(
        soil_type=typical,
        bearing_capacity_kpa=profile.typical_bearing_capacity_kpa,
        confidence=confidence,
        source="city_default",
    )
```

Net effect by city (city-default branch):

| City     | typical_soil  | kPa   | confidence |
|----------|---------------|-------|------------|
| chennai  | MEDIUM_CLAY   | 117.7 | MEDIUM     |
| bangalore| MEDIUM_ROCK   | 196.2 | MEDIUM     |
| mumbai   | FILLED_UP     | 147.1 | **LOW**    |
| delhi    | MEDIUM_CLAY   | 147.1 | MEDIUM     |
| hyderabad| MEDIUM_ROCK   | 196.2 | MEDIUM     |
| pune     | STIFF_CLAY    | 176.6 | MEDIUM     |

(Mumbai LOW reflects the "MANDATORY soil testing" guidance in the existing CITY_SOIL_DEFAULTS notes — the conservative `typical_soil = FILLED_UP` triggers LOW confidence; downstream applies safety factor per § 3 consumer contract.)

### § 4.8 Road width classification

```python
def classify_road(road_width_m: float) -> RoadWidthClass:
    if road_width_m < 6.0:    return RoadWidthClass.NARROW
    if road_width_m < 12.0:   return RoadWidthClass.STANDARD
    return RoadWidthClass.WIDE
```

Universal thresholds (Path B). FSI-aware computation lives in C2.

### § 4.9 Neighbour context (CORRECTED v0.5 per CG-5)

```python
from buildemup.domain.envelope import PlotOrientation as PO

# Translation table: facing direction → which compass bearing is "left" and "right"
# from a viewer standing on the street facing the plot.
LEFT_RIGHT_BY_FACING = {
    PO.NORTH:     {"left": PO.WEST,      "right": PO.EAST},
    PO.SOUTH:     {"left": PO.EAST,      "right": PO.WEST},
    PO.EAST:      {"left": PO.NORTH,     "right": PO.SOUTH},
    PO.WEST:      {"left": PO.SOUTH,     "right": PO.NORTH},
    # Compound facings: left/right are perpendicular diagonals
    PO.NORTHEAST: {"left": PO.NORTHWEST, "right": PO.SOUTHEAST},
    PO.SOUTHEAST: {"left": PO.NORTHEAST, "right": PO.SOUTHWEST},
    PO.SOUTHWEST: {"left": PO.SOUTHEAST, "right": PO.NORTHWEST},
    PO.NORTHWEST: {"left": PO.SOUTHWEST, "right": PO.NORTHEAST},
}

def derive_neighbour_context(plot: Plot) -> NeighbourContext:
    sides = compute_plot_facing_sides(plot.facing)  # {"front","back","left","right"} → orientations

    if plot.plot_type == PlotType.DETACHED:
        open_sides = list(sides.values())  # all 4
        shared_sides = []
    elif plot.plot_type == PlotType.SEMI_DETACHED:
        # plot.shared_side is SharedSide.{LEFT, RIGHT}; .value is "left"/"right"
        shared_orientation = LEFT_RIGHT_BY_FACING[plot.facing][plot.shared_side.value]
        shared_sides = [shared_orientation]
        open_sides = [s for s in sides.values() if s != shared_orientation]
    elif plot.plot_type == PlotType.CONTINUOUS:
        # Continuous building area (TNCDBR 2019): shares both side walls
        open_sides = [sides["front"], sides["back"]]
        shared_sides = [sides["left"], sides["right"]]

    if plot.corner_plot:
        # Second street is on one of the shared sides; promote it to open
        second_street_side = derive_second_street_side(plot)
        if second_street_side in shared_sides:
            shared_sides.remove(second_street_side)
            open_sides.append(second_street_side)

    return NeighbourContext(
        open_sides=open_sides,
        shared_sides=shared_sides,
        raw_facade_count=len(open_sides),
    )
```

**Documented limitation:** `open_sides` is RAW openness — does NOT account for setbacks. C5 combines with C2 setbacks for effective usable openness. `effective_open_sides` = **B-068**.

---

## § 5 — Module layout + invocation contract (CORRECTED v0.5)

```
buildemup/components/c04/
    __init__.py                 — calls verify_kb_consistency() at import
    plot_analysis.py            — orchestrator: derive(brief, *, now) → PlotAnalysis
    sun_path.py                 — Cooper 1969 math (~40 LOC)
    climate_zone.py             — lookup wrapper
    soil_estimator.py           — confidence-aware
    neighbour_context.py        — LEFT/RIGHT translation included
    schema.py                   — all dataclasses + enums

buildemup/kb/city_geography.py     — NEW. 6-city Lat + climate-zone tables.
                                      verify_kb_consistency() lives here.
buildemup/kb/wind_direction.py     — NEW. PREVAILING_WIND + KB_VERSION.
buildemup/kb/soil_city_defaults.py — NEW v0.5 (CG-6/7/8). SoilCityProfile
                                      + SOIL_PROFILES + BEARING_CAPACITY_BY_TYPE
                                      + KB_VERSION. Typed projection adapter
                                      between existing KBs (no shipped code touched).

buildemup/kb/wind_load.py              — EXISTING, untouched (already has KB_VERSION).
buildemup/kb/soil_foundation_rules.py  — EXISTING, untouched (already has KB_VERSION).
buildemup/kb/soil_classification.py    — EXISTING, untouched (already has KB_VERSION).
                                          Used as the source for kPa values in
                                          soil_city_defaults.BEARING_CAPACITY_BY_TYPE.
```

### Invocation contract

```python
import time
from buildemup.components.c04.plot_analysis import derive

# In bridge between C3a (resolved brief) and C5 (topology):
plot_analysis = derive(resolved_brief, now=time.time())

# Type signature: derive(brief: ResolvedBrief, *, now: float) -> PlotAnalysis
#
# Args:
#   brief — ResolvedBrief from C3a output. derive() reads:
#             brief.revised_brief.plot
#             brief.revised_brief.trace_id
#           (CORRECTED v0.5 per CG-9 — was assumed brief.plot / brief.metadata.brief_token)
#   now   — keyword-only required. Must be float > 0 (Unix epoch seconds).
#           Validated by derive(): non-float → TypeError; ≤ 0 → ValueError.
#
# Returns: frozen PlotAnalysis. C5 MUST consume this and MUST NOT
#          re-derive any of its fields from raw plot.
#
# Pure: no I/O at call time. KB lookups happened at module import.
```

`now` is keyword-only required so caller intent is explicit. Tests pass `now=1.0` (smallest valid float for the contract).

No new endpoints, DB tables, or env vars.

---

## § 6 — Failure modes (CORRECTED v0.5 per CG-9)

All v1 invariants enforced via explicit `if not ...: raise ValueError(...)` (NOT `assert`).

| Failure | Handling | Test |
|---|---|---|
| `brief.revised_brief.plot` access fails (None or missing attr) | `raise ValueError("ResolvedBrief.revised_brief.plot is required")` | unit |
| `plot.city` (post-normalize) not in CITY_GEOGRAPHY | `raise ValueError("city {x} missing from CITY_GEOGRAPHY; check kb/city_geography.py against domain.plot.SUPPORTED_CITIES")` | unit |
| `plot.city` came in non-normalized | normalized internally; original preserved | unit |
| `plot.facing` invalid enum | `raise ValueError(f"plot.facing must be PlotOrientation; got {type(...)}")` | unit |
| `area_sqft < 600` | `raise ValueError("plot < 600sqft minimum — should have been gated by C3a")` | unit |
| `latitude > 45° or latitude < -45°` | `raise ValueError(f"latitude {x}° out of plausible India range")` | unit |
| `now <= 0` | `raise ValueError(...)` | unit |
| `now` not a float | `raise TypeError(...)` | unit |
| `shape != PlotShape.RECTANGULAR` (consumer of shape_metadata) | `raise NotImplementedError("v1 supports rectangular only; B-066")` | unit |
| KB drift (some supported city missing from one of 4 KBs) | `verify_kb_consistency()` raises `RuntimeError` | unit |
| C5 directly imports `domain.plot.Plot` instead of using PlotAnalysis | placeholder lint test (active when c05/ exists) | unit |

C4 has **no request-time I/O** (KB lookups at import; per-call cost is pure CPU).

---

## § 7 — Test plan (~32 tests)

### Tier 1:

```
tests/validation/test_c4_plot_analysis.py
  - test_tier_t1_compact_chennai_30x40
  - test_tier_t2_standard_bangalore_40x60
  - test_tier_t3_large_delhi_60x90
  - test_climate_zone_chennai_is_warm_humid
  - test_climate_zone_bangalore_is_temperate
  - test_climate_zone_pune_is_temperate
  - test_climate_zone_delhi_is_composite
  - test_climate_zone_hyderabad_is_composite
  - test_climate_zone_no_v1_city_is_cold_or_hot_dry
  - test_baseline_orientations_cover_all_5_zones
  - test_neighbour_context_detached_4_facades
  - test_neighbour_context_semidetached_left_facing_north_translates_to_west
  - test_neighbour_context_continuous_2_facades
  - test_neighbour_context_corner_plot_extra_open_side
  - test_compute_plot_facing_sides_for_all_8_orientations
  - test_soil_estimate_uses_user_input_with_confidence_high
  - test_soil_estimate_falls_back_to_city_default_with_confidence_medium
  - test_soil_estimate_mumbai_city_default_returns_confidence_low      [v0.5]
  - test_road_width_classification_uses_universal_thresholds
  - test_city_normalization_handles_uppercase_and_whitespace
  - test_below_600_sqft_raises_value_error
  - test_invalid_latitude_raises_value_error
  - test_now_zero_or_negative_raises_value_error
  - test_now_non_float_raises_type_error
  - test_shape_consumer_guard_raises_for_non_rectangular
  - test_derive_reads_plot_from_revised_brief                          [v0.5/CG-9]
  - test_derive_reads_trace_id_from_revised_brief                      [v0.5/CG-9]

tests/validation/test_c4_kb_consistency.py
  - test_kb_consistency_passes_for_supported_cities
  - test_verify_kb_consistency_callable_explicitly
  - test_kb_drift_detected_when_supported_city_missing

tests/validation/test_c4_immutability.py
  - test_shape_metadata_is_mappingproxytype
  - test_baseline_orientations_uses_mappingproxytype_outer_and_inner
  - test_provenance_source_versions_is_mappingproxytype

tests/validation/test_c4_solar.py
  - test_solar_chennai_summer_noon_alt_within_1deg_of_known
  - test_solar_delhi_winter_solstice_alt_within_1deg_of_known
  - test_solar_golden_dataset_6_cities_2_solstices_within_1deg

tests/validation/test_c4_performance.py
  - test_derive_completes_under_10ms_for_typical_plot

tests/validation/test_c4_property_based.py (Hypothesis)
  - test_area_sqft_sqm_round_trip
  - test_aspect_ratio_inverse_for_swap
  - test_raw_facade_count_in_2_3_4_range

tests/validation/test_c5_consumes_plot_analysis.py [SKIPPED until c05/ exists]
  - test_c5_does_not_import_plot_directly
  - test_stub_c5_consumer_reads_plot_analysis_without_recomputation
```

### Tier 2 (e2e): NONE for C4. Tier 2 budget conserved.

**Total:** ~33 tests (was ~32 in v0.4; +1 Mumbai LOW-confidence test, +2 ResolvedBrief access tests, −1 user-input-with-loose-sand-low (rolled into MEDIUM city-default test naming)).

Budget impact: ~5–8s added to existing 28.23s. Within 30s cap.

---

## § 8 — Backlog candidates (carried)

- B-066 — Polygon plots
- B-067 — Per-month sun-path declination
- B-068 — `effective_open_sides` post-setback
- B-069 — Composite-zone internal sub-classification
- B-070 — IMD wind-rose data per city
- B-071 — Latitude-band climate fallback for unknown cities
- B-072 — C7 retrofit to consume `PlotAnalysis.soil_estimate`

**No new backlog items in v0.5.** The 6 fixes are SPEC-AMENDMENT (mechanical/structural correctness), not deferred work.

---

## § 9 — Verification at LOCK time (estimated)

- Tier 1: ~33 tests, ~5–8s budget impact.
- Tier 2: 0 new.
- Production code: ~280–380 LOC across 6 files in `components/c04/` + ~200 LOC across 3 NEW KB files (`city_geography.py`, `wind_direction.py`, `soil_city_defaults.py`).
- Zero edits to existing shipped code (Pattern E safe).
- 1 module-import KB-consistency call.

---

## § 10 — Resolved DRAFT-Qs (carried; v0.5 adds none)

| Q | Resolution |
|---|---|
| 1. NBC zone count + section | 5 zones; NBC 2016 Part 8 Section 1, §§ 2.2.21–2.2.24 + 3.2.2 |
| 2. Delhi climate zone | COMPOSITE |
| 3. Sun-path day-by-day vs solstice | Solstice; per-month → B-067 |
| 4. Vastu vs climate | Climate-only baselines in C4; Vastu → C5/C6 |
| 5. Bearing capacity surfacing | `confidence` enum + downstream-must-apply-safety-factor doc note |
| 6. Road thresholds city-specific | NO — universal 6/12m, FSI is C2's job |
| 7. Wind direction sources | IMD climatology v1 + dedicated `kb/wind_direction.py`; full wind-rose → B-070 |
| 8. C7 retrofit | B-072 |
| 9. Path B open items from v0.3 | All applied in v0.4 |
| 10. v0.5 — soil-layer adapter | Option A typed-projection adapter via new `kb/soil_city_defaults.py` (NEW Q this round) |

---

## § 11 — Spec-amendment expectations

- v0.1 DRAFT (S28) → external critique
- v0.2 PROPOSED (S28) → factual-error catch by Ramalingam
- v0.3 PROPOSED (S28) → web research applied; new external critique round
- v0.4 LOCKED (S28) → adjudicated end of S28
- **v0.5 PROPOSED** (this — S29 start) — pending Ramalingam LOCK adjudication

---

## § 12 — Backlog visibility (Rule 9)

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-066 | Polygon plots | C4 v0.1 § 4.2 | C1 polygon entry | OUT (v1 = rect) | ~150 LOC |
| B-067 | Per-month sun-path | C4 critique #4 | C5/C6 shading | OUT | ~60 LOC |
| B-068 | effective_open_sides | C4 critique #8 | C5 + facade over-count | OUT | ~20 LOC |
| B-069 | Composite-zone sub-class | C4 v0.3 web research | layout outcomes diverge | OUT | ~30 LOC |
| B-070 | IMD wind-rose | C4 v0.3 SC | ventilation incidents | OUT | ~50 LOC |
| B-071 | Lat-band city fallback | C4 v0.3 critique #3 | tier-2 city expansion | OUT | ~30 LOC |
| B-072 | C7 retrofit to consume PlotAnalysis.soil_estimate | C4 v0.4 Path B | layout pipeline stable | OUT | ~30 LOC |
| B-057..B-065 | (Session 28 entries) | various | various | OUT | various |
| B-001..B-056 | (pre-S28) | various | various | various | various |

No new backlog items in v0.5.

---

## § 13 — Rule-7 walk records

### v0.1 → v0.2 (17 external items): see v0.2 § 13. Carried.
### v0.2 → v0.3 (web research + self-critique): see v0.3 § 13. Carried.
### v0.3 → v0.4 walk: see v0.4 § 13. Carried.

### v0.4 → v0.5 walk (code-grep round 2)

External critique: NONE this round (no external critique source between v0.4 LOCK and v0.5).
Self-critique / web research: NONE this round.

**Code-grep findings (the entire v0.4→v0.5 delta):**

| # | Finding | Spec location | Resolution |
|---|---|---|---|
| CG-5 | `PlotOrientation` member names are `NORTH/NORTHEAST/...`, not `N/NE/...`. v0.4 used the value-string shorthand throughout. | § 3 (BASELINE), § 4.6 PREVAILING_WIND, § 4.9 LEFT_RIGHT_BY_FACING (~20 occurrences) | Mechanical rename to full member names. |
| CG-6 | `from kb.soil_foundation_rules import SOIL_PROFILES` — that symbol does not exist there. The actual variable is `CITY_SOIL_DEFAULTS`. | § 4.4.2 verify_kb_consistency, § 4.7 estimate_soil | New module `kb/soil_city_defaults.py` (Pattern E safe). Existing `soil_foundation_rules.py` left untouched (still used by C7). |
| CG-7 | `SoilProfile.typical_soil` returns informal strings like "rock_or_hard_clay" (NOT SoilType-convertible). `safe_bearing_capacity_t_sqm` is in tonnes/sqm, not kPa, and is named differently. | § 4.7 estimate_soil | New `SoilCityProfile` dataclass in `soil_city_defaults.py` with `typical_soil: SoilType` + `typical_bearing_capacity_kpa: float` (derived via t/sqm × 9.81). |
| CG-8 | `BEARING_CAPACITY_BY_TYPE` referenced but defined nowhere. | § 4.7 estimate_soil (user-input branch) | Defined in new `soil_city_defaults.py`, sourced from `kb.soil_classification.SOIL_PROFILES.sbc_typical_knm2` via SoilType→SoilClass mapping (documented in module). |
| CG-9 | `ResolvedBrief.plot` and `ResolvedBrief.metadata.brief_token` — neither attribute exists on actual `ResolvedBrief`. Plot path is `revised_brief.plot`; trace correlation is `revised_brief.trace_id`. | § 2 input contract, § 3 PlotAnalysis output | Read via `brief.revised_brief.plot` and `brief.revised_brief.trace_id`. PlotAnalysis output field renamed `brief_token` → `trace_id` for parity with upstream. |
| CG-10 | "Add KB_VERSION = 'v1.0'" instruction for `wind_load.py` and `soil_foundation_rules.py` — but both already carry KB_VERSION values. | § 4.4.2 NOTE, § 5 layout | Removed instruction. C4 build does not modify either file. `verify_kb_consistency` only asserts presence (any value). Pattern E safe. |

**Net code-grep verdict (round 2):** 6 errors that would have caused `AttributeError` / `ImportError` / `KeyError` at module import or first-call time. NONE were caught by external critique (no round between v0.4 LOCK and v0.5). ALL caught by build-readiness code-grep at start of S29 against the upstream tree.

**Lesson reinforced:** code-grep is mandatory at the **start of code build**, not only at spec time. v0.4's § 13 already named code-grep as "now mandatory Rule-7 surface" but the v0.4 spec itself only ran 4 code-grep checks (PlotType, SoilType, SUPPORTED_CITIES, SharedSide). It missed the soil-layer schema, the ResolvedBrief access path, and the PlotOrientation member names. v0.5 closes those.

**Tally:** 6 SPEC-AMENDMENT (CG-5 through CG-10). 0 backlog. 0 architectural change. Net spec body grows ~12% over v0.4 (added: soil_city_defaults adapter section, Mumbai LOW-confidence row in city table, 2 new tests, walk record). Architecture identical to v0.4.
