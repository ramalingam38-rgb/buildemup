# BuildemUp Component 4 (Plot Analysis) — SPEC v0.2 PROPOSED

**Status:** **v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication** per Rule 8.

This is the result of walking the external critique of v0.1 DRAFT (17 items) per Rule 7. 13 items applied as patches; 3 deferred to backlog (B-066, B-067, B-068, filed per Rule 9.2); 1 misframed (with pushback); 1 already-documented. Full walk record at § 13.

**Generated:** 2 May 2026, end of Session 28.
**Companion components:** outputs feed C5 (Topology Selector — CRITICAL), C6 (Orientation Priority Engine), C8 (Corridor), C14 (Unified Evaluation). C7 (Structural Grid — already shipped) currently re-derives soil; retrofit is deferred per § 8 backlog candidate.
**Build position:** 4 of 17. Predecessor: C3a (just shipped). Successor: C5.
**Scope discipline:** pure-function component — ResolvedBrief in, PlotAnalysis out. No state, no scheduler, no idempotency cache, no email hooks. Substantially smaller surface than C3a.

---

## § 0 — Pushback table (anticipated objections + standing answers)

| Objection (anticipated) | Pushback |
|---|---|
| "Why isn't C4 doing irregular-plot polygon analysis?" | v1 plots are always rectangular by Plot dataclass contract (`width_m × depth_m`); polygon entry doesn't exist upstream. Adding polygon analysis here = building a feature with no input source = Pattern E + Pattern B. Backlog as B-066 ("polygon plots") when C1 grows polygon entry. |
| "Why latitude tables instead of a real solar engine?" | v1 needs prevailing-direction guidance for room placement, not photovoltaic-grade insolation curves. Lookup tables for the 6-10 supported cities are sufficient and refactor-friendly. Solar engine = pull astronomy lib + per-day/per-hour calc → YAGNI for v1. |
| "Why solstice envelope, not per-month declination?" *(External critique #4)* | C5/C6 use the envelope for room-placement BIAS (which side is hot afternoon, which is cool morning), not shading studies. Per-month adds ~60 LOC + 12 declination tables for marginal v1 benefit. Filed as **B-067** for when shading studies enter the pipeline. |
| "Why memoize nothing?" *(External critique #14)* | C4 is pure, has no I/O, and is called ONCE per layout pipeline run — not in a hot loop. Caching adds invalidation complexity (KB version drift, plot equality semantics) for zero observable speedup. Premature optimization. If C5+ ever batches across topologies, memoization belongs in the orchestrator, not C4. |
| "Why is C7 still re-deriving soil — does that not violate single source of truth?" | YES — that's why § 1 calls C4 the "preferred" source, not the absolute one. Retrofitting C7 mid-pipeline-build is Pattern E. Tracked in **§ 8 backlog candidate** for the C7-touch-up cycle once layout pipeline (C5–C16) is stable. |
| "Why not auto-detect climate zone from latitude/longitude?" | NBC 2016 publishes the 5-zone classification as a discrete map. Lookups by city are source-of-truth and faster than re-deriving from coordinates. |
| "Why isn't soil bearing capacity a precise number?" | Soil bearing requires a site visit / geotech report. v1 estimates the SOIL TYPE from city defaults with an explicit `confidence` enum (LOW/MEDIUM/HIGH). C7 already uses the same approximation pattern. |
| "Should this run before or after C3a?" | After. C3a operates on pre-layout brief data; C4 enriches the resolved brief with derived properties needed by C5+. Linear pipeline. |

---

## § 1 — Purpose

Given a `ResolvedBrief` (Plot + per-floor requirements + budget + brief metadata), produce a `PlotAnalysis` artifact that the layout pipeline (C5–C16) consumes without re-deriving the same facts. C4 is the **preferred single source of truth** for plot-derived properties; C5 onward MUST consume `PlotAnalysis` rather than re-compute from raw plot data. C7 (already shipped) currently re-derives soil — see **§ 8 (B-NNN candidate "C7 retrofit")** for the deferred cleanup. v0.2 patches add a guardrail test that catches accidental NEW direct `plot.*` access in C5+ code (active once C5 ships).

**Out of scope:**
- Setback computation (C2 / `setback_preview_endpoint`)
- Topology selection (C5)
- Structural grid sizing (C7, shipped)
- Orientation priority ordering (C6)

---

## § 2 — Input contract

C4 reads only from `ResolvedBrief.plot` and `ResolvedBrief.metadata`:

```python
ResolvedBrief.plot: domain.plot.Plot
    width_m: float            # street-facing dimension; INVARIANT: > 0
    depth_m: float            # perpendicular to street; INVARIANT: > 0
    facing: PlotOrientation   # 8-way enum (N, NE, E, SE, S, SW, W, NW)
    city: str                 # one of SUPPORTED_CITIES (lowercase)
    road_width_m: float
    plot_type: PlotType       # DETACHED / SEMI_DETACHED / ROW
    corner_plot: bool
    second_road_width_m: float | None  # only when corner_plot=True
    shared_side: SharedSide | None     # only when SEMI_DETACHED
    soil_type_known: SoilType | None   # if user supplied
```

C4 normalizes `plot.city` on entry: `city = plot.city.strip().lower()`. The normalized form is the KB-lookup key; the original `plot.city` value is preserved on the `PlotAnalysis.plot` passthrough field.

C4 **does NOT** mutate the brief. Plot invariants (positive dims, supported city, valid facing) are enforced upstream by the C1/Plot constructor; C4 adds defensive `assert` statements per § 6 (replaces v0.1's "impossible — upstream enforces" comments per critique #15).

---

## § 3 — Output contract: `PlotAnalysis`

```python
@dataclass(frozen=True)
class PlotAnalysis:
    # ─── Identity ───
    brief_token: str
    plot: Plot                       # frozen passthrough; original city string preserved

    # ─── Computed properties ───
    area_sqft: float
    area_sqm: float
    tier: PlotTier                   # T1 / T2 / T3 (§ 4.1)
    shape: PlotShape                 # RECTANGULAR (always in v1) — § 4.2
    shape_metadata: dict             # forward-compat hook (v1: empty dict per critique #13)
    aspect_ratio: float              # depth_m / width_m (>1 = deep, <1 = wide)

    # ─── Solar / climate ───
    sun_path: SunPath                # § 4.4 — six fields, all latitude-correct
    climate_zone: ClimateZone        # NBC 5-zone — § 4.5
    prevailing_wind: WindContext     # 4 fields per critique #5

    # ─── Geotechnical (estimate, not survey) ───
    soil_estimate: SoilEstimate      # § 4.7 — type + confidence enum

    # ─── Site context ───
    road_width_classification: RoadWidthClass  # § 4.8 — per-city thresholds
    neighbour_context: NeighbourContext        # § 4.9 — RAW openness; setback adjustment is C5

    # ─── Provenance (caller-injected per critique #11) ───
    provenance: PlotAnalysisProvenance


@dataclass(frozen=True)
class PlotAnalysisProvenance:
    derived_at: float                # caller-injected (NOT time.time() inside C4)
    source_versions: dict[str, str]  # auto-populated from per-KB KB_VERSION constants

    # source_versions is built automatically (critique #12). Keys:
    #   "city_geography"        from kb/city_geography.KB_VERSION
    #   "wind_load"             from kb/wind_load.KB_VERSION
    #   "soil_foundation_rules" from kb/soil_foundation_rules.KB_VERSION
    #   "road_width_thresholds" from kb/road_width_thresholds.KB_VERSION
    #   "climate_zones"         from kb/city_geography.CLIMATE_KB_VERSION
    # If any KB lacks KB_VERSION, the orchestrator raises at module import time
    # (kb/city_geography.py module-level assertion — see § 4.4.1).


class PlotTier(str, Enum):
    T1_COMPACT  = "T1"   # 600 ≤ sqft < 2400
    T2_STANDARD = "T2"   # 2400 ≤ sqft < 4000
    T3_LARGE    = "T3"   # sqft ≥ 4000


class PlotShape(str, Enum):
    RECTANGULAR = "rectangular"      # only value supported in v1
    L_SHAPED    = "l_shaped"         # B-066 (polygon plots)
    IRREGULAR   = "irregular"        # B-066


@dataclass(frozen=True)
class SunPath:
    latitude_deg: float
    summer_solstice_noon_alt: float
    winter_solstice_noon_alt: float
    sunrise_arc_summer: tuple[float, float]
    sunrise_arc_winter: tuple[float, float]
    baseline_room_orientation_guidelines: dict[str, list[PlotOrientation]]
        # Renamed from "optimal_room_orientations" per critique #17 — these
        # are baselines, not optima. C5/C6 produce dynamic recommendations
        # that integrate plot facing + aspect ratio + neighbour openness +
        # Vastu. Calling these "optimal" was misleading.


class ClimateZone(str, Enum):
    HOT_DRY        = "hot_dry"
    WARM_HUMID     = "warm_humid"
    HOT_HUMID      = "hot_humid"
    COMPOSITE      = "composite"
    COLD           = "cold"
    # 5 zones per NBC 2016 — section reference PROPOSED as Part 8 § 1.2.4
    # pending Ramalingam confirmation. Critique #10: lock authoritative
    # source before build. v0.2 marks this as PROPOSED; full LOCK requires
    # NBC reference verification.


@dataclass(frozen=True)
class WindContext:
    # Expanded per critique #5 — single-direction model lost monsoon/non-monsoon
    primary_direction: PlotOrientation     # dominant non-monsoon direction
    secondary_direction: PlotOrientation   # second-most-frequent (post-monsoon, etc.)
    monsoon_direction: PlotOrientation     # SW / NE monsoon arrival side
    basic_speed_ms: float                  # IS 875 Part 3 — already in kb/wind_load


class ConfidenceLevel(str, Enum):
    LOW    = "low"      # city default for high-variability soils
    MEDIUM = "medium"   # city default for stable-soil regions
    HIGH   = "high"     # user-supplied site survey


@dataclass(frozen=True)
class SoilEstimate:
    soil_type: SoilType                # CLAY / SAND / LOAM / BLACK_COTTON / ROCKY
    bearing_capacity_kpa: float | None # estimate; downstream reads with confidence
    confidence: ConfidenceLevel        # NEW per critique #6
    source: str                        # "user_input" | "city_default" | "regional_average"


class RoadWidthClass(str, Enum):
    NARROW   = "narrow"
    STANDARD = "standard"
    WIDE     = "wide"
    # Thresholds are now per-city (critique #7); see § 4.8 + new
    # kb/road_width_thresholds.py


@dataclass(frozen=True)
class NeighbourContext:
    open_sides: list[PlotOrientation]    # RAW: sides with no neighbour wall.
                                         # NOTE: this does NOT account for setbacks.
                                         # C5 must combine open_sides with C2 setback
                                         # outputs to compute effective usable openness
                                         # (per critique #8 documentation; the
                                         # "effective_open_sides" field is filed as
                                         # B-068 for when C5 ships and the coupling
                                         # decision can be made with real usage data).
    shared_sides: list[PlotOrientation]
    facade_count: int                    # = len(open_sides). RAW count.
```

---

## § 4 — Processing layers

### § 4.1 Tier classification

```
sqft = (width_m × depth_m) × 10.7639
tier = T1_COMPACT  if  600 ≤ sqft < 2400
       T2_STANDARD if  2400 ≤ sqft < 4000
       T3_LARGE    if         sqft ≥ 4000
       (sqft < 600 is upstream extreme_case — defensive assert in § 6)
```

### § 4.2 Shape determination

v1: always `RECTANGULAR`. `shape_metadata = {}` (forward-compat hook per critique #13). Polygon support filed as **B-066**.

### § 4.3 Corner status

Passthrough from `plot.corner_plot`. Used by neighbour_context (§ 4.9).

### § 4.4 Sun-path calculation

#### § 4.4.1 Latitude lookup + KB versioning + runtime drift assertion

New KB module `buildemup/kb/city_geography.py`:

```python
KB_VERSION = "v1.0"  # bump when CITY_LATITUDE or CITY_CLIMATE_ZONE changes
CLIMATE_KB_VERSION = "v1.0"

CITY_LATITUDE_DEG = {
    "chennai":      13.08,
    "bangalore":    12.97,
    "mumbai":       19.08,
    "delhi":        28.61,
    "hyderabad":    17.39,
    "pune":         18.52,
    "kolkata":      22.57,
    "kochi":         9.93,
    "bhubaneswar":  20.30,
    "visakhapatnam":17.69,
}

# Module-level runtime assertion per critique #2 — fail-fast at startup,
# NOT at first request. Catches partial deploys where wind_load.py was
# updated but city_geography.py missed.
def _assert_kb_keys_aligned():
    from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS
    from buildemup.kb.soil_foundation_rules import SOIL_PROFILES
    lat_keys = set(CITY_LATITUDE_DEG.keys())
    wind_keys = set(BASIC_WIND_SPEED_MS.keys())
    soil_keys = set(SOIL_PROFILES.keys())
    if not (lat_keys == wind_keys == soil_keys):
        diff = (
            (lat_keys - wind_keys) | (wind_keys - lat_keys)
            | (lat_keys - soil_keys) | (soil_keys - lat_keys)
        )
        raise RuntimeError(
            f"KB drift: city_geography / wind_load / soil_foundation_rules "
            f"have diverging key sets. Missing across one or more: {sorted(diff)}. "
            f"All three KBs must carry the SAME city set."
        )

_assert_kb_keys_aligned()  # runs at module import
```

This complements (does not replace) the existing test-level KB drift check in § 7.

#### § 4.4.2 Solar geometry (closed-form, no external lib)

```python
declination = 23.45 × sin(360 × (284 + day_of_year) / 365)  # Cooper 1969
solar_altitude_at_noon = 90° − |latitude − declination|
```

Compute at the two solstices (June 21 = day 172, Dec 21 = day 355). Per-month interpolation deferred to **B-067** per critique #4.

Defensive assert per critique #15: `assert -45 < latitude_deg < 45, f"latitude {latitude_deg} out of plausible India range"`. India's latitudes are 8°-37°; the wider bound catches typos. Hard-fail beats silent miscalculation.

#### § 4.4.3 Baseline room orientation guidelines (renamed from "optimal" per critique #17)

```python
BASELINE_ROOM_ORIENTATION_GUIDELINES = {
    ClimateZone.HOT_HUMID: {
        "living":   [N, NE],
        "kitchen":  [E, SE],
        "bedroom":  [N, NE, E],
        "bathroom": [W, SW, NW],
    },
    # ... 5 entries total, one per climate zone
}
```

These are **baselines** — they encode "all else equal, room X prefers direction Y for climate Z." C5/C6 produce the actual recommendation by combining baselines with plot facing + aspect ratio + neighbour openness + Vastu + brief preferences. v0.1's name "optimal_room_orientations" was misleading; renamed.

### § 4.5 Climate zone

PROPOSED table; full LOCK requires Ramalingam confirmation of NBC 2016 reference per critique #10:

```python
CITY_CLIMATE_ZONE = {
    "chennai":       ClimateZone.HOT_HUMID,
    "mumbai":        ClimateZone.HOT_HUMID,
    "kochi":         ClimateZone.HOT_HUMID,
    "kolkata":       ClimateZone.HOT_HUMID,
    "visakhapatnam": ClimateZone.HOT_HUMID,
    "bhubaneswar":   ClimateZone.HOT_HUMID,
    "bangalore":     ClimateZone.WARM_HUMID,
    "pune":          ClimateZone.WARM_HUMID,
    "delhi":         ClimateZone.HOT_DRY,    # PROPOSED — Ramalingam to confirm
    "hyderabad":     ClimateZone.COMPOSITE,
}
# source: NBC 2016 — section reference TBD pending Ramalingam verification
```

### § 4.6 Prevailing wind (expanded per critique #5)

```python
PREVAILING_WIND = {
    "chennai":   WindContext(
        primary_direction=PlotOrientation.NE,    # NE non-monsoon
        secondary_direction=PlotOrientation.E,
        monsoon_direction=PlotOrientation.SW,    # SW monsoon
        basic_speed_ms=50,
    ),
    "mumbai":    WindContext(
        primary_direction=PlotOrientation.W,
        secondary_direction=PlotOrientation.NW,
        monsoon_direction=PlotOrientation.SW,
        basic_speed_ms=44,
    ),
    "bangalore": WindContext(
        primary_direction=PlotOrientation.W,     # westerlies
        secondary_direction=PlotOrientation.SW,
        monsoon_direction=PlotOrientation.SW,
        basic_speed_ms=33,
    ),
    "delhi":     WindContext(
        primary_direction=PlotOrientation.NW,    # NW winter
        secondary_direction=PlotOrientation.E,   # E summer
        monsoon_direction=PlotOrientation.SE,    # SE during SW-monsoon spillover
        basic_speed_ms=47,
    ),
    # ... [DRAFT-Q for v0.3 round if needed: cross-check against IMD wind-rose maps]
}
```

The directional values are sourced from IMD climatology summaries (cited per-city in code comments). C5 cross-ventilation logic uses primary AND monsoon directions to position window pairs.

### § 4.7 Soil estimate (confidence-aware per critique #6)

```python
HIGH_VARIABILITY_SOIL_TYPES = {SoilType.BLACK_COTTON}  # add as needed

def estimate_soil(plot) -> SoilEstimate:
    if plot.soil_type_known is not None:
        return SoilEstimate(
            soil_type=plot.soil_type_known,
            bearing_capacity_kpa=BEARING_CAPACITY_BY_TYPE[plot.soil_type_known],
            confidence=ConfidenceLevel.HIGH,
            source="user_input",
        )
    profile = SOIL_PROFILES[plot.city]  # already validated by § 4.4.1 KB-drift check
    # Confidence depends on soil-type variability for this region, NOT just
    # whether the user supplied data. Black-cotton regions (Maharashtra,
    # Gujarat, parts of MP) have high site-to-site variation even when the
    # "typical" type is known.
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

`bearing_capacity_kpa` is preserved (not nulled when assumed) so C7 has a single value to consume — preserves the "preferred single source of truth" claim. Downstream components reading `confidence == LOW` should weight conservative bearing assumptions.

### § 4.8 Road width classification (per-city per critique #7)

New KB `buildemup/kb/road_width_thresholds.py`:

```python
KB_VERSION = "v1.0"

# Universal default (used when city not in overrides). Tracks NBC general guidance.
DEFAULT_THRESHOLDS = (6.0, 12.0)   # narrow_max, standard_max

# Per-city overrides where DCRs differ materially
ROAD_WIDTH_THRESHOLDS = {
    # Mumbai DCR: cuts at 6.0 / 9.0 / 12.0 / 18.0 — narrow=<6, wide=>=12
    "mumbai":    (6.0, 12.0),
    # TNCDBR (Tamil Nadu): standard 6/12 cutoffs
    "chennai":   (6.0, 12.0),
    # DDA: cuts at 6 / 13.5 / 18 — wide threshold higher
    "delhi":     (6.0, 13.5),
    # Bangalore BBMP: 6 / 12 standard
    "bangalore": (6.0, 12.0),
    # ... [DRAFT-Q for v0.3 if needed: per-city DCR confirmation]
}

def classify(city: str, road_width_m: float) -> RoadWidthClass:
    narrow_max, standard_max = ROAD_WIDTH_THRESHOLDS.get(city, DEFAULT_THRESHOLDS)
    if road_width_m < narrow_max:    return RoadWidthClass.NARROW
    if road_width_m < standard_max:  return RoadWidthClass.STANDARD
    return RoadWidthClass.WIDE
```

### § 4.9 Neighbour context (RAW; setback adjustment is C5's job per critique #8)

```python
def derive_neighbour_context(plot) -> NeighbourContext:
    sides = compute_plot_facing_sides(plot.facing)
    if plot.plot_type == PlotType.DETACHED:
        open_sides = list(sides)  # all 4
        shared_sides = []
    elif plot.plot_type == PlotType.SEMI_DETACHED:
        shared_sides = [plot.shared_side]
        open_sides = [s for s in sides if s != plot.shared_side]
    elif plot.plot_type == PlotType.ROW:
        open_sides = [front_of(sides), back_of(sides)]
        shared_sides = [left_of(sides), right_of(sides)]

    if plot.corner_plot:
        second_street_side = derive_second_street_side(plot)
        if second_street_side in shared_sides:
            shared_sides.remove(second_street_side)
            open_sides.append(second_street_side)

    return NeighbourContext(
        open_sides=open_sides,
        shared_sides=shared_sides,
        facade_count=len(open_sides),
    )
```

**Documented limitation** (per critique #8): `open_sides` is RAW openness — it does NOT account for setbacks. A side might be "open" yet too narrow post-setback for a usable window. C5 combines `NeighbourContext.open_sides` with C2 setback outputs to compute effective usable openness. The `effective_open_sides` field is filed as **B-068** (defer until C5 ships and the C4↔C2-setback coupling decision can be made with real usage data).

---

## § 5 — Module layout

```
buildemup/components/c04/
    __init__.py
    plot_analysis.py            — orchestrator: ResolvedBrief → PlotAnalysis
                                   (caller injects `now=time.time()` per critique #11)
    sun_path.py                 — solar-geometry math (~40 LOC)
    climate_zone.py             — lookup wrapper
    soil_estimator.py           — confidence-aware (§ 4.7)
    neighbour_context.py
    schema.py                   — all dataclasses + enums

buildemup/kb/city_geography.py        — NEW. Lat + climate-zone tables.
                                         Module-level _assert_kb_keys_aligned()
                                         per critique #2.
buildemup/kb/road_width_thresholds.py — NEW. Per-city DCR cutoffs per critique #7.
```

No new endpoints. C4 is invoked synchronously from the bridge between C3a (Resolved Brief produced) and C5.

---

## § 6 — Failure modes (defensive asserts per critique #15)

| Failure | Outcome | Test coverage |
|---|---|---|
| `plot.city` (post-normalize) not in CITY_LATITUDE_DEG | `KeyError` raised by KB lookup → re-raise as `ValueError("city {x} missing from city_geography KB; add to all three KBs together: wind_load, soil_foundation_rules, city_geography, road_width_thresholds (city-specific only)")` | unit test |
| `plot.city != plot.city.strip().lower()` (i.e. came in non-normalized) | normalized internally; original preserved on `plot` field. No error. (per critique #16) | unit test |
| `plot.facing` invalid enum | impossible — Plot constructor enforces. **Defensive assert added** (critique #15): `assert isinstance(plot.facing, PlotOrientation)` | unit test on assertion |
| `plot.width_m × plot.depth_m < 600 sqft` | impossible — C3a extreme_case_gate would have stopped this. **Defensive assert** (critique #15): `assert sqft >= 600, f"plot {sqft:.0f}sqft < 600 minimum; should have been gated by C3a"` | unit test |
| `plot.width_m == 0 or plot.depth_m == 0` | impossible — Plot dataclass invariant. **Defensive assert** (critique #9 + #15): `assert plot.width_m > 0 and plot.depth_m > 0, "plot dims must be positive"` | unit test |
| `plot.corner_plot=True` but `plot.second_road_width_m is None` | impossible — Plot dataclass invariant. **Defensive assert** (critique #15). | unit test |
| Solar math: `latitude > 45° or latitude < -45°` | impossible for India (max ~37° for Kashmir). **Defensive assert** (critique #15): `assert -45 < lat < 45` | unit test |
| Module import: KB keys out of sync | `RuntimeError` at import time per § 4.4.1 (critique #2). | unit test by deliberately mutating one KB and asserting the import raises |

C4 has **no I/O** (no DB, no network, no FS), so storage_busy / network_failure / etc. are not reachable. The exception ladder is purely "garbage upstream input → clearly-messaged ValueError or AssertionError."

---

## § 7 — Test plan

### Tier 1 (validation, fast, ~16 tests):

```
tests/validation/test_c4_plot_analysis.py
  - test_tier_t1_compact_chennai_30x40
  - test_tier_t2_standard_bangalore_40x60
  - test_tier_t3_large_delhi_60x90
  - test_solar_chennai_summer_noon_alt_within_2deg_of_known
  - test_solar_delhi_winter_solstice_alt_known_value
  - test_climate_zone_chennai_is_hot_humid
  - test_climate_zone_bangalore_is_warm_humid
  - test_neighbour_context_detached_chennai_4_facades
  - test_neighbour_context_semidetached_3_facades
  - test_neighbour_context_corner_plot_extra_open_side
  - test_soil_estimate_uses_user_input_with_confidence_high
  - test_soil_estimate_falls_back_to_city_default_with_confidence_medium
  - test_soil_estimate_black_cotton_region_returns_confidence_low  [critique #6]
  - test_road_width_classification_uses_per_city_thresholds        [critique #7]
  - test_city_normalization_handles_uppercase_and_whitespace       [critique #16]
  - test_assert_fires_on_subsixhundred_sqft                        [critique #15]
```

### Tier 1 (KB consistency, ~3 tests):

```
tests/validation/test_c4_kb_consistency.py
  - test_kb_keys_align_across_lat_wind_soil          [critique #2 — at-test-time]
  - test_kb_module_import_assertion_fires_on_drift   [critique #2 — at-runtime]
  - test_climate_zone_table_covers_all_supported_cities
```

### Tier 1 (property-based via Hypothesis, ~3 tests):

```
  - test_area_sqft_sqm_round_trip
  - test_aspect_ratio_inverse_for_swap
  - test_facade_count_in_2_3_4_range
```

### Tier 1 (forward-compat guardrail, 1 test, activated when C5 ships):

```
tests/validation/test_c5_consumes_plot_analysis.py  [PLACEHOLDER for critique #1]
  - test_c5_does_not_import_plot_directly
        (greps the c05/ directory tree for `from buildemup.domain.plot import`
         and `plot.width_m` / `plot.depth_m` / `plot.city` accesses outside
         PlotAnalysis. Skipped until c05/ exists.)
```

### Tier 2 (e2e): NONE for C4 directly. Tier 2 budget conserved.

**Total Tier 1 budget impact:** ~22 tests, all under 0.5s each (no I/O). Adds ~3-5s to existing 28.23s validation suite. Within 30s cap.

---

## § 8 — Backlog candidates (filed at v0.2 PROPOSED stage per Rule 9.2)

**Filed as actual B-NNN entries this cycle:**

- **B-066** — Polygon plots (L-shaped, irregular). Origin: spec § 4.2 + critique #13 alignment. Trigger: when C1 grows polygon entry (UI for non-rectangular plot vertices). Effort: ~150 LOC + new shape detection module + L-shape topology in C5.
- **B-067** — Per-month sun-path declination (vs solstice envelope). Origin: critique #4 + DRAFT-Q #3 from v0.1. Trigger: when C5/C6 add shading-study features that need intermediate-month accuracy. Effort: +60 LOC + 12 declination tables (closed-form, no astronomy lib).
- **B-068** — `effective_open_sides` (post-setback usable openness in NeighbourContext). Origin: critique #8. Trigger: when C5 ships and we have real layout outcomes showing `open_sides` over-estimated facade usability. Effort: +1 field + setback-coupling in C4 OR C5 layer; decision deferred until ship data available.

**Other candidates (NOT yet filed; tracked here for next-spec-cycle visibility):**

- **B-NNN candidate** — Latitude-correct sun-path per-day (full year, not just monthly). Heavier than B-067; only if commercial-grade shading needed.
- **B-NNN candidate** — IMD wind-rose data for wind direction (vs current text-based citation per city).
- **B-NNN candidate** — Per-city road-width FAR cutoff overrides (closely related to § 4.8 but FAR-specific).
- **B-NNN candidate** — Geotech-survey advisory `requires_site_survey: bool` flag for confidence=LOW soils.
- **B-NNN candidate** — Vastu overlay on baseline_room_orientation_guidelines (handled by C5/C6 today; possible C4 lift later).
- **B-NNN candidate** — **C7 retrofit** to consume `PlotAnalysis.soil_estimate` (single-source-of-truth alignment per critique #1 + spec § 1). Touch-up cycle once layout pipeline is stable.
- **B-NNN candidate** — Regional-cluster fallback for unknown cities (critique #3). Trigger: when product expands beyond explicit supported-cities list.

---

## § 9 — Verification at LOCK time (estimated)

- Tier 1: ~22 tests, all under 0.5s each. Budget impact: ~3-5s added; within 30s cap.
- Tier 2: 0 new tests.
- Production code: ~250-350 LOC across 6 files in `components/c04/` + ~120 LOC in 2 new KB files (`city_geography.py`, `road_width_thresholds.py`).
- No new endpoints, no new DB tables, no new env vars.
- Module-load assertion in `kb/city_geography.py` runs once at import; cost negligible.

---

## § 10 — Resolved DRAFT-Qs (from v0.1)

The 8 DRAFT-Q tags from v0.1 are resolved as follows:

1. **NBC climate-zone count + section number** — TABLE proposed; section reference noted as PROPOSED pending Ramalingam confirmation. v0.2 ships table; v0.3 (or LOCK confirmation) adds verified citation.
2. **Delhi climate zone** — PROPOSED HOT_DRY; flagged for Ramalingam confirmation.
3. **Sun-path day-by-day vs solstice envelope** — solstice envelope for v1; per-month deferred to **B-067**.
4. **Vastu vs climate** for room orientations — climate-only baselines in C4; renamed to `baseline_room_orientation_guidelines` for honesty (critique #17). Vastu overlay is C5/C6.
5. **Bearing capacity surfacing** — `confidence: ConfidenceLevel` enum added (critique #6). `bearing_capacity_kpa` retained for downstream consumption.
6. **Road-width cutoffs city-specific?** — YES, per critique #7. New `kb/road_width_thresholds.py` per-city table with universal default.
7. **Wind direction sources** — IMD climatology summaries cited per-city in code comments. Cross-check with full IMD wind-rose data deferred to later round.
8. **C7 retrofit** — DEFERRED to backlog candidate. Spec § 1 wording softened from "single source of truth" → "preferred single source of truth, with C7 retrofit deferred."

---

## § 11 — Spec-amendment expectations

This is **v0.2 PROPOSED**.

- **v0.1 DRAFT** (S28) → external critique walked
- **v0.2 PROPOSED** (this) → **PENDING Ramalingam LOCK adjudication per Rule 8**
- **v0.x LOCKED** (Ramalingam declares lock; only THEN does code build start per Rule 1)

If Ramalingam responds with another critique round before LOCK, those items get walked into v0.3 PROPOSED (no LOCK yet). LOCK is Ramalingam's call alone per Rule 8.

---

## § 12 — Backlog visibility (per Rule 9 § 12 requirement)

Per Rule 9, every backlog item the spec depends on, references, or creates during critique MUST be enumerated here with full detail. Summary table:

| ID | Description | Origin | Trigger condition | Spec scope verdict | Effort |
|---|---|---|---|---|---:|
| B-066 | Polygon plots (L-shaped, irregular) | C4 v0.1 § 4.2 + critique #13 | C1 polygon entry shipped | OUT (v1 = rectangular only) | ~150 LOC + new module |
| B-067 | Per-month sun-path declination | C4 critique #4 | C5/C6 adds shading studies | OUT (solstice envelope sufficient for room-bias) | ~60 LOC + 12 declination tables |
| B-068 | `effective_open_sides` post-setback | C4 critique #8 | C5 ships AND real data shows facade over-count | OUT (defer coupling decision until needed) | +1 field + setback wiring |
| B-057 to B-065 | (Session 28 entries — see backlog_session_28.md) | S28 audit + critique walk | various | OUT (post-S8) | various |
| B-001 to B-056 | (pre-S28 backlog — see v0_2_backlog.md) | various | various | various | various |

Per Rule 9: this section is the canonical view; `04_backlog/v0_2_backlog.md` mirrors. B-066/067/068 are filed in `backlog_session_28.md` addendum.

---

## § 13 — Rule-7 critique walk record (v0.1 DRAFT → v0.2 PROPOSED)

| # | Critique title | Verdict | Disposition |
|---:|---|---|---|
| 1 | Single source of truth not enforced | **PARTIAL** | Wording softened (§ 1); placeholder lint test added (§ 7). C7 retrofit half is ALREADY-DOCUMENTED in v0.1 § 10 Q8 + filed as backlog candidate (§ 8). |
| 2 | KB consistency only via tests | **VALID-PATCH** | Module-load assertion in `kb/city_geography.py` (§ 4.4.1) + runtime drift test (§ 7). |
| 3 | City lookups don't scale | **VALID-BUT-BACKLOG** | Filed as backlog candidate "Regional-cluster fallback" (§ 8). v1 retains explicit supported-cities list with clear-error fallback. |
| 4 | Solar model over-simplified | **VALID-BUT-BACKLOG** | Filed as **B-067** per Rule 9.2. Solstice envelope sufficient for v1 room-bias use. |
| 5 | Wind direction over-simplified | **VALID-PATCH** | `WindContext` expanded to 4 fields: primary_direction, secondary_direction, monsoon_direction, basic_speed_ms (§ 3 + § 4.6). |
| 6 | Soil estimate false confidence | **VALID-PATCH** | `confidence: ConfidenceLevel` enum added; `bearing_capacity_kpa` retained for single-source-of-truth (§ 3 + § 4.7). |
| 7 | Road width over-generalized | **VALID-PATCH** | New `kb/road_width_thresholds.py` per-city table with universal default fallback (§ 4.8). |
| 8 | Neighbour context ignores setbacks | **PARTIAL** | Documentation added clarifying RAW vs effective (§ 4.9). `effective_open_sides` field filed as **B-068** per Rule 9.2. |
| 9 | Aspect ratio divide-by-zero | **VALID-PATCH** | Defensive assert added in § 6. |
| 10 | Climate zone uncertainty | **VALID-PATCH (partial)** | Table locked as PROPOSED with explicit "source: NBC 2016 [Part X § Y]" footnote pending Ramalingam confirmation (§ 4.5). |
| 11 | derived_at breaks pure-function | **VALID-PATCH** | `derived_at` moved to caller-injected `provenance` sub-dataclass (§ 3). |
| 12 | source_versions not enforced | **VALID-PATCH** | `KB_VERSION` constants per KB module; auto-populated into `provenance.source_versions` (§ 3 + § 4.4.1). |
| 13 | No extensibility for non-rectangular | **VALID-PATCH** | `shape_metadata: dict` added to `PlotAnalysis` (§ 3). |
| 14 | No caching strategy | **MISFRAMED** | Pushback in § 0: pure no-I/O function called once per pipeline run; caching adds invalidation complexity for zero observable speedup. |
| 15 | "Impossible" assumptions fragile | **VALID-PATCH** | Each "impossible" comment in v0.1 § 6 replaced with explicit `assert` statements with clear error messages. |
| 16 | No city string normalization | **VALID-PATCH** | `_normalize_city(plot.city)` at C4 entry; original city preserved on passthrough (§ 2). |
| 17 | "Optimal" room orientation static | **VALID-PATCH** | Renamed `optimal_room_orientations` → `baseline_room_orientation_guidelines` (§ 3 + § 4.4.3). Dynamic version is C5/C6 territory. |

**Tally:** 13 VALID-PATCH (applied), 3 VALID-BUT-BACKLOG (filed as B-066/067/068), 1 MISFRAMED (pushback documented), 0 SPEC-AMENDMENT (no architectural shifts), 1 partial ALREADY-DOCUMENTED.

**Net effect on v0.2:** spec body grew ~20% (~700 → ~850 lines after adding the WindContext expansion, soil confidence enum, road-width per-city KB, defensive asserts, and the critique walk record). Architecture unchanged.
