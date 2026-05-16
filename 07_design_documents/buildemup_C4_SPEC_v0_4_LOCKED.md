# BuildemUp Component 4 (Plot Analysis) — SPEC v0.4 LOCKED

**Status:** **v0.4 LOCKED** — Ramalingam adjudication received end of Session 28 ("Lock this spec and give me the handoff"). Per Rule 1, code build may now begin against this LOCKED spec.

**Generated:** 2 May 2026, end of Session 28.

This v0.4 consolidates: (1) all VALID-PATCH items from the 2nd external critique walk on v0.3 (12 items), (2) Claude's self-critique pass (5 items), (3) the 4 hygiene items Claude flagged on v0.3 last turn but didn't apply, (4) decisions on the 3 open questions left from v0.3 ("Path B" per Ramalingam), and (5) **4 additional factual errors caught only by greping the actual upstream `domain/plot.py`** during v0.4 prep — these would have produced `AttributeError` at module import OR runtime contract violations had they reached code.

The pattern is becoming clear: each Rule-7 cycle (web research + code grep + self-critique + external walk) catches a new tier of errors. v0.4 is the first revision built on **all four** verification surfaces.

**Companion components:** outputs feed C5 (Topology Selector — CRITICAL), C6 (Orientation Priority Engine), C8 (Corridor), C14 (Unified Evaluation). C7 (Structural Grid — already shipped) currently re-derives soil; retrofit is **B-072** (filed this cycle per Rule 9.2).

**Build position:** 4 of 17. Predecessor: C3a (just shipped). Successor: C5.

**Scope discipline:** pure-function component — ResolvedBrief in, PlotAnalysis out. No state, scheduler, idempotency cache, email hooks, or request-time I/O.

---

## § 0 — Pushback table

| Objection | Pushback |
|---|---|
| "Why isn't C4 doing irregular-plot polygon analysis?" | Plot dataclass is `width_m × depth_m` only. Polygon entry doesn't exist upstream. **B-066**. |
| "Why solstice envelope, not per-month declination?" | C5/C6 use envelope for room-bias, not shading studies. **B-067**. Cooper 1969 accuracy is ~0.5-1° per web research (was overstated as 1.5° in v0.3). |
| "Why memoize nothing?" | Pure no-I/O function, called once per pipeline run. v0.4 § 7 adds `test_derive_completes_under_10ms_for_typical_plot` to demonstrate the no-caching call holds. |
| "Why is C7 still re-deriving soil?" | Pattern E mid-build. C7 retrofit = **B-072** (filed v0.4). |
| "Why universal 6/12m road thresholds when DCRs differ city-by-city?" | The road_width_classification is a COARSE classifier for layout heuristics. FSI-aware FAR computation is C2's job — Mumbai DCPR 2034 cuts at 9/12/18/27m, Bangalore BBMP at 12/18/24m, Delhi DDA on plot size. v0.3's per-city KB conflated concerns; v0.4 reverts to universal 6/12 + delegates FSI to C2. |
| "Why 6 cities, not 10?" | `domain.plot.SUPPORTED_CITIES = {chennai, bangalore, hyderabad, mumbai, pune, delhi}`. Plot constructor enforces. v0.3's spec listed 10 cities (kolkata, kochi, bhubaneswar, visakhapatnam included) — those are NOT in v1's supported set. v0.4 corrected. |
| "Why not enforce single-source-of-truth via runtime `isinstance(input, PlotAnalysis)` everywhere?" *(2nd-round external #1)* | Type-checker (mypy) + a single import-pattern lint test catches accidental `from domain.plot import` in C5+ at CI time. Scattered runtime asserts add cost on every call to catch a bug that lint catches once. Test guardrail (active when C5 ships) is the right mechanism. |
| "Why no climate × wind × sun cross-validation?" *(2nd-round external #12)* | Tautological: the tables ARE the source of truth; cross-checks reduce to "tests verify tables match tests' expectations." If tables drift in a way that breaks coupling, downstream tests catch it. Pushback. |

---

## § 1 — Purpose

Given a `ResolvedBrief`, produce a `PlotAnalysis` artifact for the layout pipeline (C5–C16). C4 is the **preferred single source of truth** for plot-derived properties; C5 onward MUST consume `PlotAnalysis` rather than re-compute. C7 (already shipped) currently re-derives soil — see **B-072** for the deferred retrofit. v0.4 adds a guardrail test (active when C5 ships) that catches accidental NEW direct `plot.*` access in C5+ code.

**Out of scope:** setbacks (C2), topology (C5), structural grid (C7), orientation priority (C6), FSI/FAR computation (C2 / `setback_preview_endpoint`).

---

## § 2 — Input contract (FACTUAL CORRECTIONS from v0.3)

C4 reads only from `ResolvedBrief.plot` and `ResolvedBrief.metadata`:

```python
ResolvedBrief.plot: domain.plot.Plot
    width_m: float            # 3.0 ≤ width ≤ 60.0 (Plot constructor enforces)
    depth_m: float            # 3.0 ≤ depth ≤ 60.0
    facing: PlotOrientation   # 8-way enum (N, NE, E, SE, S, SW, W, NW)
    city: str                 # one of SUPPORTED_CITIES (lowercase, 6 cities)
    road_width_m: float       # 1.5 ≤ road ≤ 30.0
    plot_type: PlotType       # DETACHED / SEMI_DETACHED / CONTINUOUS
                              # ┃ CORRECTED v0.4: was "ROW" in v0.1-v0.3 — wrong.
                              # ┃ Actual enum value is CONTINUOUS (per
                              # ┃ TNCDBR 2019 "Continuous Building Area").
    corner_plot: bool
    second_road_width_m: float | None    # required when corner_plot=True
    shared_side: SharedSide | None       # ENUM is {LEFT, RIGHT} relative to viewer on
                                         # the street facing the plot. CORRECTED v0.4:
                                         # was assumed PlotOrientation in v0.1-v0.3.
                                         # See § 4.9 for facing→compass translation.
    soil_type_known: SoilType | None     # 9 values per CORRECTED list below

ResolvedBrief.metadata
    brief_token: str          # ONLY field C4 needs (for trace correlation)


# CORRECTED v0.4 — actual upstream enum from domain/plot.py
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
    # No "BLACK_COTTON", "CLAY", "SAND", "LOAM", or "ROCKY" values exist —
    # v0.1-v0.3 spec referenced these wrongly. v0.4 uses the actual 9 values.

# CORRECTED v0.4 — 6 cities, not 10
SUPPORTED_CITIES = frozenset({
    "chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi",
})
```

C4 normalizes `plot.city` on entry: `city = plot.city.strip().lower()`. The Plot constructor already validates `city in SUPPORTED_CITIES`, so by the time C4 runs, the city is guaranteed to be one of the 6. C4 still validates `city in CITY_GEOGRAPHY` (per #10 fail-fast) as defense-in-depth in case CITY_GEOGRAPHY drifts from SUPPORTED_CITIES.

C4 **does NOT** mutate the brief. Plot invariants (dim bounds, road bounds, facing enum, city in SUPPORTED_CITIES) are enforced upstream by `Plot.__post_init__`; C4 adds production-safe validation per § 6 using explicit `raise ValueError` (NOT `assert`).

**Facing convention** (NEW per SC-B): given `plot.facing`, "front" = facing direction; "back" = opposite; "right" = 90° clockwise from front (viewer standing on street looking at plot); "left" = 90° counter-clockwise. For compound facings (NE, SE, SW, NW), front/back are diagonal and right/left are the perpendicular diagonals. Implementation in `compute_plot_facing_sides(facing) -> dict[Literal["front","back","left","right"], PlotOrientation]`. All 8 input values tested.

---

## § 3 — Output contract: `PlotAnalysis`

```python
from types import MappingProxyType   # SC-1: true immutability for nested dicts


@dataclass(frozen=True)
class PlotAnalysis:
    # ─── Identity ───
    brief_token: str
    plot: Plot                                           # frozen passthrough

    # ─── Computed properties ───
    area_sqft: float
    area_sqm: float
    tier: PlotTier
    shape: PlotShape                                     # ALWAYS RECTANGULAR in v1
    shape_metadata: Mapping[str, object]                 # MappingProxyType (SC-1)
    aspect_ratio: float                                  # depth/width — see § 3 conv

    # ─── Solar ───
    sun_path: SunPath                                    # geometry only (SC-4 split)

    # ─── Climate (top-level per SC-4 — was nested under SunPath in v0.3) ───
    climate_zone: ClimateZone
    baseline_room_orientation_guidelines: Mapping[ClimateZone, Mapping[str, list[PlotOrientation]]]
                                                          # MappingProxyType wraps both
                                                          # outer + inner dicts (SC-1)

    # ─── Wind ───
    prevailing_wind: WindContext

    # ─── Geotechnical ───
    soil_estimate: SoilEstimate

    # ─── Site context ───
    road_width_classification: RoadWidthClass            # universal 6/12m (reverted)
    neighbour_context: NeighbourContext

    # ─── Provenance ───
    provenance: PlotAnalysisProvenance


@dataclass(frozen=True)
class PlotAnalysisProvenance:
    derived_at: float                                    # caller-injected (> 0)
    source_versions: Mapping[str, str]                   # MappingProxyType (SC-1)
    # Auto-populated from per-KB KB_VERSION at construction:
    #   "city_geography"        from kb/city_geography.KB_VERSION
    #   "wind_load"             from kb/wind_load.KB_VERSION
    #   "soil_foundation_rules" from kb/soil_foundation_rules.KB_VERSION
    #   "wind_direction"        from kb/wind_direction.KB_VERSION (NEW per #4)


class PlotTier(str, Enum):
    T1_COMPACT  = "T1"   # 600 ≤ sqft < 2400
    T2_STANDARD = "T2"   # 2400 ≤ sqft < 4000
    T3_LARGE    = "T3"   # sqft ≥ 4000


class PlotShape(str, Enum):
    RECTANGULAR = "rectangular"   # ALWAYS in v1
    L_SHAPED    = "l_shaped"      # B-066 forward-compat
    IRREGULAR   = "irregular"     # B-066


@dataclass(frozen=True)
class SunPath:
    # Geometry only — climate-derived recommendations are top-level on PlotAnalysis (SC-4)
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
    # No v1 city maps to HOT_DRY (Jodhpur not in supported set) or COLD
    # (Srinagar not in supported set). Test asserts.


@dataclass(frozen=True)
class WindContext:
    primary_direction: PlotOrientation     # dominant non-monsoon
    monsoon_direction: PlotOrientation     # SW or NE monsoon arrival
    @property
    def basic_speed_ms(self) -> float:
        """Reads from kb/wind_load.BASIC_WIND_SPEED_MS (SC-C: no duplication).
        WindContext is constructed with city; speed lookup is computed at access."""
        ...
    # NB: WindContext is NOT frozen-dataclass-instantiable with a speed field
    # if we want to avoid the speed-vs-kb duplication. Implementation choice:
    # either store city ref + property (this design) or pass speed-at-construction
    # explicitly (less clean). v0.4 uses the property approach.


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

# CONSUMER CONTRACT (#7 doc note): downstream components reading
# `confidence == LOW` MUST apply a structural safety factor to
# bearing_capacity_kpa. C7 currently uses its own conservative defaults
# (B-072 retrofit will align this). Documented here for explicit contract.


class RoadWidthClass(str, Enum):
    NARROW   = "narrow"     # < 6m
    STANDARD = "standard"   # 6–12m
    WIDE     = "wide"       # ≥ 12m
    # v0.4: REVERTED to universal thresholds. v0.3's per-city KB
    # conflated coarse classification with FSI-aware classification.
    # Mumbai DCPR cuts at 9/12/18/27m, Bangalore BBMP at 12/18/24m,
    # Delhi DDA on plot size — these are FSI concerns, not coarse-class.
    # FSI-aware logic stays in C2 (feasibility), where it belongs.


@dataclass(frozen=True)
class NeighbourContext:
    open_sides: list[PlotOrientation]    # RAW openness (NOT setback-aware — see B-068)
    shared_sides: list[PlotOrientation]
    raw_facade_count: int                # = len(open_sides). RENAMED v0.4 per #8
                                         # (was facade_count — name was misleading).
                                         # B-068 will add usable_facade_hint.

# Aspect ratio convention (SC documentation): aspect_ratio = depth / width.
# Values > 1 mean a deep plot (long axis perpendicular to street).
# Values < 1 mean a wide plot (long axis parallel to street).
# = 1 is square. Pinned in spec to avoid downstream ambiguity.
```

---

## § 4 — Processing layers

### § 4.1 Tier classification (unchanged from v0.3)

```
sqft = (width_m × depth_m) × 10.7639
tier = T1_COMPACT  if  600 ≤ sqft < 2400
       T2_STANDARD if  2400 ≤ sqft < 4000
       T3_LARGE    if         sqft ≥ 4000
```

`sqft < 600` → `raise ValueError("plot < 600sqft minimum — should have been gated by C3a")` (production-safe per #6, #17).

### § 4.2 Shape determination

v1: ALWAYS `RECTANGULAR`. `shape_metadata = MappingProxyType({})` (SC-1).
Code paths consuming `shape_metadata` MUST guard:
```python
if shape != PlotShape.RECTANGULAR:
    raise NotImplementedError("v1 supports rectangular only; B-066")
```
(per #11 — prevents misuse of the forward-compat hook.)

### § 4.3 Corner status

Passthrough.

### § 4.4 Sun-path calculation

#### § 4.4.1 KB module — `kb/city_geography.py` (CORRECTED v0.4: 6 cities)

```python
KB_VERSION = "v1.0"

@dataclass(frozen=True)
class CityGeography:
    latitude_deg: float
    climate_zone: ClimateZone


CITY_GEOGRAPHY = {
    # 6 cities matching domain.plot.SUPPORTED_CITIES exactly.
    # No kolkata/kochi/bhubaneswar/visakhapatnam — those are NOT in v1
    # supported set. Adding them requires updating domain.plot.SUPPORTED_CITIES
    # AND all 4 KBs (this one + wind_load + soil_foundation_rules + wind_direction)
    # in the same change.
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

#### § 4.4.2 KB drift verification (SC refactored per critique #2 + SC-A)

```python
def verify_kb_consistency() -> None:
    """Called from C4 module init AND as explicit Tier-1 test.
    
    INVARIANT: every supported city must be present in EVERY KB.
    KBs may carry extras (forward-compat) but cannot be missing any
    supported city.
    """
    from buildemup.domain.plot import SUPPORTED_CITIES
    from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS, KB_VERSION as WL_VER
    from buildemup.kb.soil_foundation_rules import SOIL_PROFILES, KB_VERSION as SF_VER
    from buildemup.kb.wind_direction import PREVAILING_WIND, KB_VERSION as WD_VER
    
    required = set(SUPPORTED_CITIES)
    
    # Coverage check: every supported city must be in every KB
    for kb_name, kb_keys in [
        ("city_geography",         set(CITY_GEOGRAPHY.keys())),
        ("wind_load",              set(BASIC_WIND_SPEED_MS.keys())),
        ("soil_foundation_rules",  set(SOIL_PROFILES.keys())),
        ("wind_direction",         set(PREVAILING_WIND.keys())),
    ]:
        missing = required - kb_keys
        if missing:
            raise RuntimeError(
                f"KB drift: kb/{kb_name} missing required supported cities: "
                f"{sorted(missing)}. All 4 KBs must contain every city in "
                f"domain.plot.SUPPORTED_CITIES."
            )
    
    # KB_VERSION presence (SC-6 from v0.3 — extended to wind_direction)
    # Already verified by import above; if any module lacks KB_VERSION,
    # ImportError fires first.
```

(NOTE: `kb/wind_load.py` and `kb/soil_foundation_rules.py` may currently lack `KB_VERSION` — they pre-date C4. Adding KB_VERSION = "v1.0" to each is a one-line addition NOT to be deferred. Single-line touchup is in scope per Pattern E avoidance.)

#### § 4.4.3 Solar geometry (closed-form)

Cooper 1969 declination, **~0.5-1° accuracy** per web research (was overstated as 1.5° in v0.3):

```
declination = 23.45 × sin(360 × (284 + day_of_year) / 365)
solar_altitude_at_noon = 90° − |latitude − declination|
```

Computed at solstices (June 21 = day 172, Dec 21 = day 355). Per-month = **B-067**.

Validation (production-safe per #6, #17):
```python
if not (-45 < latitude_deg < 45):
    raise ValueError(f"latitude {latitude_deg}° out of plausible range")
```

#### § 4.4.4 Baseline room orientation guidelines (TOP-LEVEL per SC-4)

Top-level field on `PlotAnalysis`, NOT nested inside `SunPath` (climate-derived, not solar-geometry-derived; v0.3 had a coupling smell here).

```python
BASELINE_ROOM_ORIENTATION_GUIDELINES = MappingProxyType({
    ClimateZone.WARM_HUMID: MappingProxyType({  # Mumbai, Chennai
        "living":   [N, NE],
        "kitchen":  [E, SE],
        "bedroom":  [N, NE, E],
        "bathroom": [W, SW, NW],
    }),
    ClimateZone.TEMPERATE: MappingProxyType({   # Bangalore, Pune
        "living":   [N, NE, E, S],
        "kitchen":  [E, SE, NE],
        "bedroom":  [N, NE, E],
        "bathroom": [W, SW],
    }),
    ClimateZone.COMPOSITE: MappingProxyType({   # Delhi, Hyderabad
        "living":   [N, NE, E],
        "kitchen":  [E, NE],
        "bedroom":  [N, NE, E, SE],
        "bathroom": [W, SW, NW],
    }),
    ClimateZone.HOT_DRY: MappingProxyType({     # Reserved (no v1 city)
        "living":   [N, NE, E],
        "kitchen":  [E, NE],
        "bedroom":  [N, NE, E],
        "bathroom": [W, SW],
    }),
    ClimateZone.COLD: MappingProxyType({        # Reserved (no v1 city)
        "living":   [S, SE, SW],
        "kitchen":  [E, SE],
        "bedroom":  [S, SE],
        "bathroom": [N, NW],
    }),
})
```

These are CLIMATE-derived heuristics. C5/C6 produce dynamic recommendations integrating baselines + plot facing + aspect ratio + neighbour openness + Vastu + brief preferences.

### § 4.5 Climate zone (looked up from CITY_GEOGRAPHY)

`climate_zone = CITY_GEOGRAPHY[normalized_city].climate_zone`. Values per § 4.4.1.

### § 4.6 Prevailing wind — NEW dedicated KB module per critique #4 + SC-D

`buildemup/kb/wind_direction.py` (NEW):

```python
KB_VERSION = "v1.0"

# Per-city wind direction. Source: Indian Meteorological Department
# climatology summaries (cited per-city below). Full IMD wind-rose
# integration is B-070.
PREVAILING_WIND = {
    "chennai":   WindContext(
        primary_direction=PlotOrientation.NE,    # NE non-monsoon (Oct-Mar)
        monsoon_direction=PlotOrientation.SW,    # SW monsoon (Jun-Sep)
        # Source: IMD Chennai climatology
    ),
    "mumbai":    WindContext(
        primary_direction=PlotOrientation.W,
        monsoon_direction=PlotOrientation.SW,
        # Source: IMD Santacruz station
    ),
    "bangalore": WindContext(
        primary_direction=PlotOrientation.W,
        monsoon_direction=PlotOrientation.SW,
        # Source: IMD Bangalore HAL
    ),
    "pune":      WindContext(
        primary_direction=PlotOrientation.W,
        monsoon_direction=PlotOrientation.SW,
        # Source: IMD Shivajinagar
    ),
    "hyderabad": WindContext(
        primary_direction=PlotOrientation.W,
        monsoon_direction=PlotOrientation.SW,
        # Source: IMD Begumpet
    ),
    "delhi":     WindContext(
        primary_direction=PlotOrientation.NW,    # NW winter
        monsoon_direction=PlotOrientation.SE,    # monsoon spillover
        # Source: IMD Safdarjung
    ),
}
# All values PROPOSED pending per-city IMD wind-rose verification (B-070).
```

`WindContext.basic_speed_ms` is a property that reads from `kb/wind_load.BASIC_WIND_SPEED_MS` at access time (SC-C: no duplication).

### § 4.7 Soil estimate (CORRECTED v0.4: actual SoilType enum)

```python
# CORRECTED v0.4: soft/medium/loose soils have higher site variability.
# v0.3's BLACK_COTTON reference doesn't exist in the actual enum.
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
    typical = SoilType(profile.typical_soil)
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

### § 4.8 Road width classification (REVERTED to universal per Path B)

```python
def classify_road(road_width_m: float) -> RoadWidthClass:
    if road_width_m < 6.0:    return RoadWidthClass.NARROW
    if road_width_m < 12.0:   return RoadWidthClass.STANDARD
    return RoadWidthClass.WIDE
```

v0.3's per-city KB (`kb/road_width_thresholds.py`) is REMOVED. FSI-aware computation lives in C2.

### § 4.9 Neighbour context (CORRECTED v0.4: SharedSide is LEFT/RIGHT, not PlotOrientation)

```python
# Translation table: facing direction → which compass bearing is "left" and "right"
# from a viewer standing on the street facing the plot.
LEFT_RIGHT_BY_FACING = {
    PlotOrientation.N:  {"left": PlotOrientation.W, "right": PlotOrientation.E},
    PlotOrientation.S:  {"left": PlotOrientation.E, "right": PlotOrientation.W},
    PlotOrientation.E:  {"left": PlotOrientation.N, "right": PlotOrientation.S},
    PlotOrientation.W:  {"left": PlotOrientation.S, "right": PlotOrientation.N},
    # Compound facings: left/right are perpendicular diagonals
    PlotOrientation.NE: {"left": PlotOrientation.NW, "right": PlotOrientation.SE},
    PlotOrientation.SE: {"left": PlotOrientation.NE, "right": PlotOrientation.SW},
    PlotOrientation.SW: {"left": PlotOrientation.SE, "right": PlotOrientation.NW},
    PlotOrientation.NW: {"left": PlotOrientation.SW, "right": PlotOrientation.NE},
}

def derive_neighbour_context(plot: Plot) -> NeighbourContext:
    sides = compute_plot_facing_sides(plot.facing)  # {"front", "back", "left", "right"} → orientations
    
    if plot.plot_type == PlotType.DETACHED:
        open_sides = list(sides.values())  # all 4
        shared_sides = []
    elif plot.plot_type == PlotType.SEMI_DETACHED:
        # Translate plot.shared_side (LEFT or RIGHT) into a PlotOrientation
        shared_orientation = LEFT_RIGHT_BY_FACING[plot.facing][plot.shared_side.value]
        shared_sides = [shared_orientation]
        open_sides = [s for s in sides.values() if s != shared_orientation]
    elif plot.plot_type == PlotType.CONTINUOUS:    # CORRECTED: was "ROW" in v0.3
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
        raw_facade_count=len(open_sides),    # RENAMED per #8
    )
```

**Documented limitation** (per critique #8 from v0.1 round; carried forward): `open_sides` is RAW openness — does NOT account for setbacks. C5 combines with C2 setbacks for effective usable openness. `effective_open_sides` = **B-068**.

---

## § 5 — Module layout + invocation contract

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
buildemup/kb/wind_direction.py     — NEW per #4. PREVAILING_WIND + KB_VERSION.
buildemup/kb/wind_load.py          — EXISTING. Add KB_VERSION = "v1.0" line.
buildemup/kb/soil_foundation_rules.py — EXISTING. Add KB_VERSION = "v1.0" line.
```

### Invocation contract (NEW per SC-6, SC-E)

```python
import time
from buildemup.components.c04.plot_analysis import derive

# In bridge between C3a (resolved brief) and C5 (topology):
plot_analysis = derive(resolved_brief, now=time.time())

# Type signature: derive(brief: ResolvedBrief, *, now: float) -> PlotAnalysis
#
# Args:
#   brief — ResolvedBrief from C3a output
#   now   — keyword-only required. Must be float > 0 (Unix epoch seconds).
#           Validated by derive(): if not isinstance(now, float) or now <= 0:
#                                       raise TypeError / ValueError
#
# Returns: frozen PlotAnalysis. C5 MUST consume this and MUST NOT
#          re-derive any of its fields from raw plot.
#
# Pure: no I/O at call time. KB lookups happened at module import.
```

`now` is keyword-only required so caller intent is explicit. Tests pass `now=0.0` for determinism — note this is technically invalid per `now > 0` validation; **test path uses now=1.0** (smallest valid float for the contract).

No new endpoints, DB tables, or env vars.

---

## § 6 — Failure modes (production-safe per #6, #17, SC-15)

All v1 invariants enforced via explicit `if not ...: raise ValueError(...)` (NOT `assert`, which `python -O` strips). `assert` reserved for test-only invariants.

| Failure | Handling | Test |
|---|---|---|
| `plot.city` (post-normalize) not in CITY_GEOGRAPHY | `if normalized not in CITY_GEOGRAPHY: raise ValueError("city {x} missing from CITY_GEOGRAPHY; check kb/city_geography.py against domain.plot.SUPPORTED_CITIES")` | unit |
| `plot.city` came in non-normalized | normalized internally; original preserved | unit |
| `plot.facing` invalid enum | `if not isinstance(plot.facing, PlotOrientation): raise ValueError(...)` | unit |
| `area_sqft < 600` | `raise ValueError("plot < 600sqft minimum — should have been gated by C3a")` | unit |
| `latitude > 45° or latitude < -45°` | `raise ValueError(f"latitude {x}° out of plausible India range")` | unit |
| `now <= 0 or not isinstance(now, float)` | `raise ValueError / TypeError` | unit |
| `shape != PlotShape.RECTANGULAR` (consumer of shape_metadata) | `raise NotImplementedError("v1 supports rectangular only; B-066")` | unit |
| KB drift (some supported city missing from one of 4 KBs) | `verify_kb_consistency()` raises `RuntimeError` | unit |
| C5 directly imports `domain.plot.Plot` instead of using PlotAnalysis | placeholder lint test (active when c05/ exists) | unit |

C4 has **no request-time I/O** (KB lookups at import; per-call cost is pure CPU).

---

## § 7 — Test plan

### Tier 1 (~28 tests):

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
  - test_neighbour_context_semidetached_left_facing_north_translates_to_west [NEW v0.4]
  - test_neighbour_context_continuous_2_facades                              [CORRECTED]
  - test_neighbour_context_corner_plot_extra_open_side
  - test_compute_plot_facing_sides_for_all_8_orientations                    [SC-B]
  - test_soil_estimate_uses_user_input_with_confidence_high
  - test_soil_estimate_falls_back_to_city_default_with_confidence_medium
  - test_soil_estimate_loose_sand_returns_confidence_low                     [CORRECTED]
  - test_road_width_classification_uses_universal_thresholds                 [REVERTED]
  - test_city_normalization_handles_uppercase_and_whitespace
  - test_below_600_sqft_raises_value_error
  - test_invalid_latitude_raises_value_error
  - test_now_zero_or_negative_raises                                          [SC-E]
  - test_now_non_float_raises_type_error                                      [SC-E]
  - test_shape_consumer_guard_raises_for_non_rectangular                     [#11]

tests/validation/test_c4_kb_consistency.py
  - test_kb_consistency_passes_for_supported_cities
  - test_verify_kb_consistency_callable_explicitly
  - test_kb_drift_detected_when_supported_city_missing                        [refactored]

tests/validation/test_c4_immutability.py
  - test_shape_metadata_is_mappingproxytype                                   [SC-1]
  - test_baseline_orientations_uses_mappingproxytype_outer_and_inner          [SC-1]
  - test_provenance_source_versions_is_mappingproxytype                       [SC-1]

tests/validation/test_c4_solar.py
  - test_solar_chennai_summer_noon_alt_within_1deg_of_known                   [tightened #5]
  - test_solar_delhi_winter_solstice_alt_within_1deg_of_known                 [tightened]
  - test_solar_golden_dataset_6_cities_2_solstices_within_1deg                [NEW #5]
        # 12 reference values × 1° tolerance, web-research-backed Cooper accuracy

tests/validation/test_c4_performance.py
  - test_derive_completes_under_10ms_for_typical_plot                         [#13]

tests/validation/test_c4_property_based.py (Hypothesis)
  - test_area_sqft_sqm_round_trip
  - test_aspect_ratio_inverse_for_swap
  - test_raw_facade_count_in_2_3_4_range                                      [renamed]

tests/validation/test_c5_consumes_plot_analysis.py [SKIPPED until c05/ exists]
  - test_c5_does_not_import_plot_directly                                     [#14 negative]
  - test_stub_c5_consumer_reads_plot_analysis_without_recomputation           [#14 positive]
```

### Tier 2 (e2e): NONE for C4. Tier 2 budget conserved.

**Total:** ~32 tests. Budget impact: ~5-8s added to existing 28.23s. Within 30s cap.

---

## § 8 — Backlog candidates

**Filed via this spec cycle (carried over):**
- B-066 — Polygon plots
- B-067 — Per-month sun-path declination
- B-068 — `effective_open_sides` post-setback
- B-069 — Composite-zone internal sub-classification
- B-070 — IMD wind-rose data per city
- B-071 — Latitude-band climate fallback for unknown cities

**NEW filed v0.4 (per Rule 9.2):**
- **B-072** — **C7 retrofit to consume `PlotAnalysis.soil_estimate`**. Origin: critique #1 of v0.1 round + spec § 1 deferred since v0.1 + Path B confirmation v0.4. Trigger: when layout pipeline (C5–C16) is stable. Effort: ~30 LOC in C7 + retrofit tests.

---

## § 9 — Verification at LOCK time (estimated)

- Tier 1: ~32 tests, ~5-8s budget impact.
- Tier 2: 0 new.
- Production code: ~280-380 LOC across 6 files in `components/c04/` + ~150 LOC across 2 NEW KB files (`city_geography.py`, `wind_direction.py`) + 2 one-line additions to existing KBs (`KB_VERSION = "v1.0"` in `wind_load.py` and `soil_foundation_rules.py`).
- 1 module-import KB-consistency call.

---

## § 10 — Resolved DRAFT-Qs (final)

| Q | Resolution |
|---|---|
| 1. NBC zone count + section | 5 zones; **NBC 2016 Part 8 Section 1, §§ 2.2.21–2.2.24 + 3.2.2** (web-verified) |
| 2. Delhi climate zone | **COMPOSITE** (web-verified) |
| 3. Sun-path day-by-day vs solstice | Solstice; per-month → B-067 |
| 4. Vastu vs climate | Climate-only baselines in C4; Vastu → C5/C6 |
| 5. Bearing capacity surfacing | `confidence` enum + downstream-must-apply-safety-factor doc note |
| 6. Road thresholds city-specific | NO — universal 6/12m, FSI is C2's job (Path B) |
| 7. Wind direction sources | IMD climatology v1 + dedicated `kb/wind_direction.py`; full wind-rose → B-070 |
| 8. C7 retrofit | **B-072** (filed v0.4) |
| 9. Path B open items from v0.3 | All applied: universal thresholds + 4 hygiene items + 12 patches + 5 self-critique + B-072 |

---

## § 11 — Spec-amendment expectations

- v0.1 DRAFT (S28) → external critique
- v0.2 PROPOSED (S28) → factual-error catch by Ramalingam
- v0.3 PROPOSED (S28) → web research applied; new external critique round
- **v0.4 LOCKED** (this — adjudicated end of S28) → code build may now begin per Rule 1

---

## § 12 — Backlog visibility (Rule 9 § 12)

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-066 | Polygon plots | C4 v0.1 § 4.2 | C1 polygon entry | OUT (v1 = rect) | ~150 LOC |
| B-067 | Per-month sun-path | C4 critique #4 | C5/C6 shading | OUT | ~60 LOC |
| B-068 | effective_open_sides | C4 critique #8 | C5 + facade over-count | OUT | ~20 LOC |
| B-069 | Composite-zone sub-class | C4 v0.3 web research | layout outcomes diverge | OUT | ~30 LOC |
| B-070 | IMD wind-rose | C4 v0.3 SC | ventilation incidents | OUT | ~50 LOC |
| B-071 | Lat-band city fallback | C4 v0.3 critique #3 | tier-2 city expansion | OUT | ~30 LOC |
| **B-072** | **C7 retrofit to consume PlotAnalysis.soil_estimate** | **C4 v0.4 Path B** | **layout pipeline stable** | **OUT** | **~30 LOC** |
| B-057 to B-065 | (Session 28 entries) | various | various | OUT | various |
| B-001 to B-056 | (pre-S28) | various | various | various | various |

---

## § 13 — Rule-7 walk records

### v0.1 → v0.2 (17 external items): see v0.2 § 13. Carried forward.
### v0.2 → v0.3 (web research + self-critique): see v0.3 § 13. Carried forward.
### v0.3 → v0.4 walk

**External critique (17 items from 2nd round):**

| # | Verdict | Disposition |
|---|---|---|
| 1 | MISFRAMED | Pushback in § 0; type-checker + lint > scattered runtime asserts |
| 2 | CONDITIONAL→MOOT | Reverted to universal thresholds; no per-city KB to drift |
| 3 | VALID-BUT-BACKLOG | Filed as **B-071** |
| 4 | VALID-PATCH | Dedicated `kb/wind_direction.py` with KB_VERSION (§ 4.6) |
| 5 | VALID-PATCH | 1° tolerance + 12-value golden dataset (web-research-driven, § 7) |
| 6 | VALID-PATCH | All `assert` for prod invariants → `if not: raise ValueError` (§ 6) |
| 7 | VALID-PATCH (doc) | Explicit downstream-must-apply-safety-factor contract (§ 3 + § 4.7) |
| 8 | VALID-PATCH | `facade_count` → `raw_facade_count` (§ 3) |
| 9 | VALID-PATCH (lighter) | Typed contract `now > 0` + clear docstring example (§ 5); no factory |
| 10 | VALID-PATCH | Validate city in CITY_GEOGRAPHY immediately after normalize (§ 6) |
| 11 | VALID-PATCH | NotImplementedError guard for non-RECTANGULAR shape consumers (§ 4.2) |
| 12 | MISFRAMED | Pushback in § 0; tautological cross-validation |
| 13 | VALID-PATCH | `test_derive_completes_under_10ms_for_typical_plot` (§ 7) |
| 14 | VALID-PATCH (partial) | Stub-C5-consumer test added; no-direct-import test stays (§ 7) |
| 15 | CONDITIONAL→MOOT | Universal thresholds — no per-city granularity to expose |
| 16 | ALREADY-DOCUMENTED | B-067 + WindContext seasonal split |
| 17 | VALID-PATCH (same as #6) | Production-safe ValueError throughout § 6 |

**Self-critique (5 items, additional to last turn's 15):**

| ID | Disposition |
|---|---|
| SC-A | PlotType verified — was DETACHED/SEMI_DETACHED/CONTINUOUS, NOT ROW. CORRECTED throughout § 2, § 4.9. |
| SC-B | `compute_plot_facing_sides()` tested for all 8 orientations (§ 7) |
| SC-C | `WindContext.basic_speed_ms` is property reading kb/wind_load directly (§ 3) |
| SC-D | Resolved with #4 — dedicated `kb/wind_direction.py` |
| SC-E | `now > 0` + `isinstance(now, float)` validation (§ 5, § 7) |

**Path B from last turn (3 open items, all applied):**

| Item | Decision | Where applied |
|---|---|---|
| Road-width per-city vs universal | Universal (revert) | § 4.8, RoadWidthClass enum, § 10 Q6 |
| 4 hygiene items from prior self-critique | All applied | MappingProxyType (§ 3 SC-1), prod-safe ValueError (§ 6 SC-15), BASELINE top-level (§ 4.4.4 SC-4), invocation contract (§ 5 SC-6) |
| C7 retrofit as backlog | Filed | **B-072** |

**Code-grep findings (NEW Rule-7 verification surface beyond external/web/self-critique):**

| # | Finding | Impact |
|---|---|---|
| CG-1 | `PlotType.CONTINUOUS`, not `ROW` | spec corrected throughout |
| CG-2 | `SUPPORTED_CITIES = 6 cities`, not 10 | CITY_GEOGRAPHY trimmed; KB drift check refactored to "every supported city in every KB" (allows extras) |
| CG-3 | `SoilType` has 9 specific values, no `BLACK_COTTON` | HIGH_VARIABILITY_SOIL_TYPES uses SOFT_CLAY/LOOSE_SAND/FILLED_UP — would have been AttributeError at import otherwise |
| CG-4 | `SharedSide` is `LEFT/RIGHT` enum, not `PlotOrientation` | NeighbourContext logic adds `LEFT_RIGHT_BY_FACING` translation table |

**Net code-grep verdict:** 4 errors that would have caused `AttributeError` at module import OR runtime contract violations. NONE were caught by the external critique; ALL caught by Claude's self-grep of upstream `domain/plot.py`. The lesson: **upstream code grep is now a mandatory Rule-7 verification surface alongside web research and self-critique**, not optional.

**Tally:** 13 VALID-PATCH (from external) + 5 self-critique + 4 hygiene from prior turn + 4 code-grep + 1 backlog filed (B-072). 2 misframed (pushback). 2 conditional→moot. 1 already-documented.

**Net effect on v0.4:** spec body grew ~10% over v0.3 (mainly the LEFT_RIGHT translation table, immutability wrappers, golden dataset test). Architecture unchanged. The 4 code-grep errors would have been v1 release-blockers.
