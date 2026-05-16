# BuildemUp Component 4 (Plot Analysis) — SPEC v0.1 DRAFT

**Status:** DRAFT — first cut for Step 2 of D-066 (external critique). NOT LOCKED. Ramalingam takes this to the external critique source; Claude waits for the response, walks every item per Rule 7, produces v0.2 PROPOSED, awaits Ramalingam LOCK adjudication per Rule 8.

**Generated:** 2 May 2026, end of Session 28.
**Companion components:** outputs feed C5 (Topology Selector), C6 (Orientation Priority Engine), C7 (Structural Grid — already shipped, will consume some C4 outputs in a future revision), C8 (Corridor), C14 (Unified Evaluation).
**Build position:** 4 of 17. Predecessor: C3a (Pre-Layout Extreme-Case Gate, just shipped via S8). Successor: C5 (Topology Selector — CRITICAL).
**Scope discipline:** pure-function component — ResolvedBrief in, PlotAnalysis out. No state, no scheduler, no idempotency cache, no email hooks. Substantially smaller surface than C3a.

---

## § 0 — Pushback table (anticipated objections + standing answers)

| Objection (anticipated) | Pushback |
|---|---|
| "Why isn't C4 doing irregular-plot polygon analysis?" | v1 plots are always rectangular by Plot dataclass contract (`width_m × depth_m`); polygon entry doesn't exist upstream. Adding polygon analysis here = building a feature with no input source = Pattern E + Pattern B. Backlog as B-NNN ("polygon plots") when C1 grows polygon entry. |
| "Why latitude tables instead of a real solar engine?" | v1 needs prevailing-direction guidance for room placement, not photovoltaic-grade insolation curves. Lookup tables for the 6-10 supported cities are sufficient and refactor-friendly. Solar engine = pull astronomy lib + per-day/per-hour calc → YAGNI for v1. |
| "Why not auto-detect climate zone from latitude/longitude?" | NBC publishes the 5-zone classification as a discrete map; lookups by city are the source-of-truth and faster than re-deriving from coordinates. |
| "Why isn't soil bearing capacity a number?" | Soil bearing requires a site visit / geotech report; v1 estimates the SOIL TYPE (clay/sand/loam/black-cotton/rocky) from city defaults, with clear `assumed=true` flag. C7 already uses this same approximation pattern. |
| "Should this run before or after C3a?" | After. C3a operates on pre-layout brief data; C4 enriches the resolved brief with derived properties needed by C5+. Linear pipeline. |

---

## § 1 — Purpose

Given a `ResolvedBrief` (Plot + per-floor requirements + budget + brief metadata), produce a `PlotAnalysis` artifact that the layout pipeline (C5–C16) can consume without re-deriving the same facts. C4 is the **single source of truth** for plot-derived properties; downstream components MUST NOT re-compute these from raw plot data.

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
    width_m: float            # street-facing dimension
    depth_m: float            # perpendicular to street
    facing: PlotOrientation   # 8-way enum (N, NE, E, SE, S, SW, W, NW)
    city: str                 # one of SUPPORTED_CITIES
    road_width_m: float
    plot_type: PlotType       # DETACHED / SEMI_DETACHED / ROW
    corner_plot: bool
    second_road_width_m: float | None  # only when corner_plot=True
    shared_side: SharedSide | None     # only when SEMI_DETACHED
    soil_type_known: SoilType | None   # if user supplied
```

C4 **does NOT** mutate the brief. It also does NOT do further validation — `Plot` invariants (positive dims, supported city, valid facing) are already enforced by the C1/Plot constructor.

---

## § 3 — Output contract: `PlotAnalysis`

```python
@dataclass(frozen=True)
class PlotAnalysis:
    # ─── Identity ───
    brief_token: str            # passthrough, for trace correlation
    plot: Plot                  # original plot, frozen passthrough

    # ─── Computed properties (this component's value-add) ───
    area_sqft: float            # width_m × depth_m, converted
    area_sqm: float
    tier: PlotTier              # T1 / T2 / T3 (§ 4.1)
    shape: PlotShape            # RECTANGULAR (always in v1) — § 4.2
    aspect_ratio: float         # depth_m / width_m (>1 = deep, <1 = wide)

    # ─── Solar / climate ───
    sun_path: SunPath           # § 4.4 — six fields, all latitude-correct
    climate_zone: ClimateZone   # NBC 5-zone — § 4.5
    prevailing_wind: WindContext # direction + speed — § 4.6

    # ─── Geotechnical (estimate, not survey) ───
    soil_estimate: SoilEstimate # § 4.7 — type + assumed flag

    # ─── Site context ───
    road_width_classification: RoadWidthClass  # § 4.8 — narrow/standard/wide
    neighbour_context: NeighbourContext        # § 4.9 — open sides, shared sides

    # ─── Provenance ───
    derived_at: float           # unix timestamp (P29 propagation)
    source_versions: dict[str, str]  # {"climate_kb": "v1", ...}

class PlotTier(str, Enum):
    T1_COMPACT  = "T1"   # 600 ≤ sqft < 2400 (§ 4.1)
    T2_STANDARD = "T2"   # 2400 ≤ sqft < 4000
    T3_LARGE    = "T3"   # sqft ≥ 4000

class PlotShape(str, Enum):
    RECTANGULAR = "rectangular"   # only value supported in v1
    L_SHAPED    = "l_shaped"      # backlog (B-066 candidate)
    IRREGULAR   = "irregular"     # backlog

@dataclass(frozen=True)
class SunPath:
    latitude_deg: float           # city latitude, source: CITY_LATITUDE_KB
    summer_solstice_noon_alt: float  # solar altitude angle, °
    winter_solstice_noon_alt: float
    sunrise_arc_summer: tuple[float, float]  # (azimuth_min, azimuth_max), °
    sunrise_arc_winter: tuple[float, float]
    optimal_room_orientations: dict[str, list[PlotOrientation]]
        # {"living": [N, NE], "kitchen": [SE, E], ...} — § 4.4.3

class ClimateZone(str, Enum):
    HOT_DRY        = "hot_dry"         # Delhi, Jaipur
    WARM_HUMID     = "warm_humid"      # Bangalore, Pune
    HOT_HUMID      = "hot_humid"       # Chennai, Mumbai, Kochi
    COMPOSITE      = "composite"       # Hyderabad, Bhopal
    COLD           = "cold"            # Shimla (out of v1 scope)
    # 5 zones per NBC 2016 Part 8 § 1.2.4 [DRAFT-Q: confirm zone count and names]

@dataclass(frozen=True)
class WindContext:
    prevailing_direction: PlotOrientation  # whence the wind comes from
    basic_speed_ms: float                  # IS 875 Part 3 — already in kb/wind_load
    monsoon_direction: PlotOrientation     # for ventilation planning

@dataclass(frozen=True)
class SoilEstimate:
    soil_type: SoilType        # CLAY / SAND / LOAM / BLACK_COTTON / ROCKY
    assumed: bool              # True if not supplied by user
    bearing_capacity_kpa: float | None  # estimate; None means "unknown, do site test"
    source: str                # "user_input" | "city_default" | "regional_average"

class RoadWidthClass(str, Enum):
    NARROW   = "narrow"     # < 6m  (often triggers FAR penalties)
    STANDARD = "standard"   # 6–12m
    WIDE     = "wide"       # ≥ 12m

@dataclass(frozen=True)
class NeighbourContext:
    open_sides: list[PlotOrientation]    # sides with no neighbour (street + setbacks)
    shared_sides: list[PlotOrientation]  # SEMI_DETACHED / ROW
    facade_count: int                    # how many sides we can put windows on
```

---

## § 4 — Processing layers (one section per derived property)

### § 4.1 Tier classification

```
sqft = area_sqft = (width_m × depth_m) × 10.7639
tier = T1_COMPACT  if  600   ≤ sqft < 2400
       T2_STANDARD if  2400  ≤ sqft < 4000
       T3_LARGE    if         sqft ≥ 4000
       (sqft < 600 = handled upstream by C3a as extreme_case)
```

Rationale: tiers drive layout-engine assumptions (T1 favors no-corridor or central-spine topologies; T3 unlocks courtyard).

### § 4.2 Shape determination

v1: always `RECTANGULAR`. Plot dataclass only carries width × depth. L_SHAPED / IRREGULAR are backlog.

### § 4.3 Corner status

Passthrough from `plot.corner_plot`. C4 does NOT re-derive. Used as input to neighbour_context (§ 4.9) — corner plots have one extra "open side" (the second street).

### § 4.4 Sun-path calculation

#### § 4.4.1 Latitude lookup

New KB module `buildemup/kb/city_geography.py`:
```python
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
# Same key set as kb/wind_load.BASIC_WIND_SPEED_MS — must stay in sync.
```

#### § 4.4.2 Solar geometry (closed-form, no external lib)

```python
declination = 23.45 × sin(360 × (284 + day_of_year) / 365)  # Cooper 1969
solar_altitude_at_noon = 90° − |latitude − declination|
```

For v1, compute altitude at the two solstices (June 21 = day 172, Dec 21 = day 355) — that's the envelope every other day fits inside. Sunrise/sunset azimuths use the standard formula:

```python
cos(azimuth) = (sin(declination) − sin(latitude) × sin(altitude)) / (cos(latitude) × cos(altitude))
```

Implementation cost: ~40 LOC of pure math, no astronomy lib. Tested with reference values for Chennai / Delhi / Mumbai.

#### § 4.4.3 Optimal room orientations

Lookup table by climate zone × room type:

```python
OPTIMAL_ROOM_ORIENTATIONS = {
    ClimateZone.HOT_HUMID: {
        "living":   [N, NE],          # avoid afternoon W sun
        "kitchen":  [E, SE],          # morning sun, away from cooking heat going W
        "bedroom":  [N, NE, E],
        "bathroom": [W, SW, NW],      # least-used directions
    },
    ClimateZone.HOT_DRY: {
        "living":   [N, NE, E],
        "kitchen":  [E, NE],
        "bedroom":  [N, NE, E],
        "bathroom": [W, SW],
    },
    # ... 5 entries total, one per climate zone
}
```

[DRAFT-Q: should optimal-orientations also factor Vastu? C5/C6 will surface Vastu separately. C4 stays climate-driven; Vastu is a downstream layer.]

### § 4.5 Climate zone

Lookup by city. NBC 2016 Part 8 § 1.2.4 [DRAFT-Q: verify section number; spec author memory may be wrong] defines 5 zones. Mapping table:

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
    "delhi":         ClimateZone.HOT_DRY,    # [DRAFT-Q: HOT_DRY or COMPOSITE?]
    "hyderabad":     ClimateZone.COMPOSITE,
}
```

### § 4.6 Prevailing wind

Existing `kb/wind_load.BASIC_WIND_SPEED_MS` provides speed. C4 adds DIRECTION via new lookup:

```python
PREVAILING_WIND_DIRECTION = {
    "chennai":   PlotOrientation.SE,    # SE monsoon
    "mumbai":    PlotOrientation.SW,    # SW monsoon dominant
    "bangalore": PlotOrientation.W,     # westerlies
    "delhi":     PlotOrientation.NW,    # NW winter, E summer; pick dominant
    # ... [DRAFT-Q: India Meteorological Department sources to vet]
}
```

Reasoning: ventilation planning in C5/C9 needs WHICH SIDE wind arrives from to position cross-ventilation pairs.

### § 4.7 Soil estimate

```python
def estimate_soil(plot) -> SoilEstimate:
    if plot.soil_type_known is not None:
        return SoilEstimate(
            soil_type=plot.soil_type_known,
            assumed=False,
            bearing_capacity_kpa=BEARING_CAPACITY_BY_TYPE[plot.soil_type_known],
            source="user_input",
        )
    # Fallback to city default from existing kb/soil_foundation_rules.SOIL_PROFILES
    profile = SOIL_PROFILES[plot.city]
    return SoilEstimate(
        soil_type=SoilType(profile.typical_soil),
        assumed=True,
        bearing_capacity_kpa=profile.typical_bearing_capacity_kpa,
        source="city_default",
    )
```

[DRAFT-Q: Black-cotton soil is highly site-variable in Maharashtra/Gujarat — should we surface a `requires_geotech_survey: bool` advisory flag? C7 already conservatively assumes worst-case for unknowns; pushing this back to user is double-asking.]

### § 4.8 Road width classification

```python
def classify_road(road_width_m: float) -> RoadWidthClass:
    if road_width_m < 6.0:  return NARROW
    if road_width_m < 12.0: return STANDARD
    return WIDE
```

The actual road_width_m passes through unchanged; this enum is a layout-pipeline convenience (FAR rules in DCRs typically have step-functions at 6m / 9m / 12m / 18m thresholds). [DRAFT-Q: 6/12 cutoffs are common but city-specific — should the cutoffs themselves be city-keyed?]

### § 4.9 Neighbour context

```python
def derive_neighbour_context(plot) -> NeighbourContext:
    sides = compute_plot_facing_sides(plot.facing)  # 4 sides given facing
    if plot.plot_type == PlotType.DETACHED:
        open_sides = [front, left, right, back]
        shared_sides = []
    elif plot.plot_type == PlotType.SEMI_DETACHED:
        # plot.shared_side tells us WHICH side is shared
        shared_sides = [plot.shared_side]
        open_sides = [s for s in sides if s != plot.shared_side]
    elif plot.plot_type == PlotType.ROW:
        # Both side neighbours present; only front and back open
        open_sides = [front, back]
        shared_sides = [left, right]

    if plot.corner_plot:
        # corner adds the second-street side as open if it was shared
        open_sides = list(set(open_sides) | {derive_second_street_side(plot)})

    return NeighbourContext(
        open_sides=open_sides,
        shared_sides=shared_sides,
        facade_count=len(open_sides),
    )
```

`facade_count` is the actionable number for C5/C9: it's how many sides we can put windows on. Range: 2 (row plot, mid-block) to 4 (detached).

---

## § 5 — Module layout

```
buildemup/components/c04/
    __init__.py
    plot_analysis.py            — orchestrator: ResolvedBrief → PlotAnalysis
    sun_path.py                 — solar-geometry math (~40 LOC)
    climate_zone.py             — lookup wrapper
    soil_estimator.py           — wraps kb/soil_foundation_rules
    neighbour_context.py
    schema.py                   — all dataclasses + enums

buildemup/kb/city_geography.py  — NEW. Lat/long + climate-zone tables.
                                  Co-keyed with kb/wind_load and
                                  kb/soil_foundation_rules.
```

No new endpoints. C4 is invoked synchronously from the bridge between C3a (Resolved Brief produced) and C5 (Topology Selector).

---

## § 6 — Failure modes

| Failure | Outcome | Test coverage |
|---|---|---|
| `plot.city` not in CITY_LATITUDE_KB | `ValueError("city {x} missing from city_geography KB; add to all 3 KBs together: wind_load, soil_foundation_rules, city_geography")` | unit test |
| `plot.facing` invalid enum | impossible — C1 enforces. C4 trusts the contract. | n/a |
| `plot.width_m × plot.depth_m < 600 sqft` | impossible — C3a extreme_case_gate would have stopped this. C4 trusts. Defensive: assert and raise; do not silently produce a tier-T0 unknown. | unit test on assertion |
| `plot.corner_plot=True` but `plot.second_road_width_m is None` | impossible — Plot dataclass invariant. | covered upstream |
| Solar math: `latitude > 66.5°` | impossible for India (max ~35° for Kashmir). Defensive: assert. | unit test |

C4 has **no I/O** (no DB, no network, no FS), so storage_busy / network_failure / etc. are not reachable. The exception ladder is purely "garbage upstream input → ValueError". No 503 path, no idempotency cache, no email hook.

---

## § 7 — Test plan

### Tier 1 (validation, fast, ~12 tests):

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
  - test_soil_estimate_uses_user_input_when_supplied
  - test_soil_estimate_falls_back_to_city_default_with_assumed_true
```

### Property-based (Hypothesis, ~3 tests):

```
  - test_area_sqft_sqm_round_trip       (sqft / 10.7639 ≈ sqm)
  - test_aspect_ratio_inverse_for_swap  (swap width<->depth → 1/r)
  - test_facade_count_in_2_3_4_range
```

### Tier 2 (e2e): NONE for C4 directly. C4 is a pure function used by the C5+ pipeline; e2e tests at C5 level will exercise C4 transitively. Do not create C4-only e2e tests — they would be redundant and would inflate Tier 2 budget for no coverage gain.

### KB drift checks:

```
tests/validation/test_c4_kb_consistency.py
  - test_city_keys_align_across_three_kbs
        (CITY_LATITUDE_KB.keys() == BASIC_WIND_SPEED_MS.keys() == SOIL_PROFILES.keys())
  - test_climate_zone_table_covers_all_supported_cities
```

This is the GUARDRAIL Pattern that prevented the C3a P43 trace_id desync — KB drift is loud at test-collect time, not silent at runtime.

---

## § 8 — Backlog (filed at C4 v0.1 LOCK time, per Rule 9.2)

These are out of v0.1 scope and will be filed as B-NNN entries at LOCK-time, NOT now (since the spec is still DRAFT and the items might shift):

- **B-066 candidate** — L-shaped & irregular plot polygons (depends on C1 polygon entry)
- **B-067 candidate** — Latitude-correct sun-path per-day (vs. solstice envelope) for shading studies
- **B-068 candidate** — Wind-tunnel-grade vs. lookup wind direction (depends on volume of T3 plots)
- **B-069 candidate** — Per-city road-width FAR cutoff overrides
- **B-070 candidate** — Geotech survey advisory flag for black-cotton-soil regions
- **B-071 candidate** — Vastu overlay on optimal_room_orientations (handled by C5/C6 today)

[DRAFT-Q: any of these worth pulling INTO v0.1 because C5 needs them? Best guess: no — C5 can layer on top of v0.1.]

---

## § 9 — Verification at LOCK time (estimated)

- Tier 1: ~12 tests, all under 1 second each (no I/O, no fixtures beyond plain dataclass instantiation). Budget impact: under 2s added to the existing 28.23s validation Tier 1 budget. Comfortably within the 30s cap.
- Tier 2: 0 new tests (deliberately — see § 7).
- Production code: ~250-350 LOC across 6 files in `components/c04/` + ~100 LOC in `kb/city_geography.py`.
- No new endpoints, no new DB tables, no new env vars.

---

## § 10 — Open questions for external critique

These are explicit DRAFT-Q tags inviting the external critic to push:

1. **NBC climate-zone count + section number** — spec author cited "Part 8 § 1.2.4 / 5 zones" from memory. Verify against canonical NBC 2016.
2. **Delhi climate zone** — HOT_DRY or COMPOSITE? Different references put it differently.
3. **Sun-path day-by-day vs solstice envelope** — solstice envelope = ~40 LOC math; per-day = +100 LOC and possibly external lib. Does C5/C6 need per-day?
4. **Vastu vs climate** for optimal_room_orientations — does C4 stay climate-only (cleaner) or merge in Vastu (one-pass for the layout pipeline)?
5. **Bearing capacity surfacing** — should C4 emit `requires_geotech_survey: bool` for high-variability soils, or is that a C7 concern?
6. **Road-width cutoffs city-specific?** — DCR variations are real (Mumbai DCR vs TNCDBR vs DDA cut differently). Does v1 keep universal 6/12m thresholds?
7. **Wind direction sources** — IMD wind-rose maps, Köppen climatology, or NBC tables? Need a citation per city.
8. **C7 retrofit** — C7 (already shipped) currently re-derives soil estimate from `kb/soil_foundation_rules` directly. Should we retrofit C7 to consume `PlotAnalysis.soil_estimate` for single-source-of-truth, or leave C7 alone and accept the duplication for v1? (Pattern E concern — touching C7 mid-build to enforce architectural purity.)

---

## § 11 — Spec-amendment expectations

This is **v0.1 DRAFT**. Expected lifecycle:
- **v0.1 DRAFT** (this) → external critique
- **v0.2 PROPOSED** (Claude after critique walk per Rule 7; PENDING Ramalingam LOCK adjudication per Rule 8)
- **v0.x LOCKED** (Ramalingam declares lock; only THEN does code build start per Rule 1)

No code is written until LOCK. No backlog entries are filed until LOCK (per Rule 9 visibility — items must enumerate in spec § 8 with full detail BEFORE being entered into project backlog file). The only inputs Claude takes between DRAFT and LOCK are: (a) Ramalingam adjudications, (b) external critique walked per Rule 7.
