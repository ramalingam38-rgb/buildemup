# BuildemUp Component 4 (Plot Analysis) — SPEC v0.3 PROPOSED

**Status:** **v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication** per Rule 8.

This is the result of the v0.2 round of corrections per Rule 7's **web-search-to-verify-external-claims** requirement (which I missed in v0.2 — Ramalingam's catch). v0.3 fixes 7 factually-wrong city climate assignments + 1 enum value + adds 5 self-critique items I should have caught independently. v0.2's other patches (15 items from the external critique walk) carry forward unchanged.

**Generated:** 2 May 2026, end of Session 28.
**Companion components:** outputs feed C5 (Topology Selector — CRITICAL), C6 (Orientation Priority Engine), C8 (Corridor), C14 (Unified Evaluation). C7 (already shipped) currently re-derives soil; retrofit is deferred per § 8 backlog candidate.
**Build position:** 4 of 17. Predecessor: C3a. Successor: C5.
**Scope discipline:** pure-function component — ResolvedBrief in, PlotAnalysis out. No state, scheduler, idempotency cache, or email hooks.

---

## § 0 — Pushback table (carries forward from v0.2 unchanged + 1 new entry)

| Objection (anticipated) | Pushback |
|---|---|
| "Why isn't C4 doing irregular-plot polygon analysis?" | Plot dataclass is rectangular-only upstream. Filed as B-066. |
| "Why solstice envelope, not per-month declination?" | C5/C6 use envelope for room-bias, not shading studies. Filed as B-067. |
| "Why memoize nothing?" | Pure no-I/O function called once per pipeline run. Caching adds invalidation complexity for zero observable speedup. |
| "Why is C7 still re-deriving soil?" | Pattern E mid-build. C7 retrofit is deferred (§ 8 candidate). |
| "Why is composite-zone treated as a single value when NBC composite contains internal variation (composite-dry vs composite-humid)?" *(NEW from v0.3 web research)* | NBC 2016 itself defines composite as a single zone (= "no single climatic condition predominates ≥6 months"). Recent academic literature (2023-2025) proposes refining into composite-dry / composite-humid sub-zones. C4 v1 follows NBC 2016 as canonical. **Filed as B-069**. |
| "Should this run before or after C3a?" | After. Linear pipeline. |

---

## § 1 — Purpose

Given a `ResolvedBrief`, produce a `PlotAnalysis` artifact for the layout pipeline (C5–C16). C4 is the **preferred single source of truth** for plot-derived properties; C5 onward MUST consume `PlotAnalysis` rather than re-compute. C7 (already shipped) currently re-derives soil — see § 8 backlog candidate. v0.2+ patches add a guardrail test catching accidental NEW direct `plot.*` access in C5+ code.

**Out of scope:** setbacks (C2), topology (C5), structural grid (C7), orientation priority (C6).

---

## § 2 — Input contract

C4 reads only from `ResolvedBrief.plot` and `ResolvedBrief.metadata`. Per critique #16, C4 normalizes `plot.city = plot.city.strip().lower()` on entry; the original is preserved on the passthrough field.

```python
ResolvedBrief.plot: domain.plot.Plot
    width_m: float            # street-facing dimension; INVARIANT: > 0
    depth_m: float            # perpendicular to street; INVARIANT: > 0
    facing: PlotOrientation   # 8-way enum (N/NE/E/SE/S/SW/W/NW)
    city: str                 # one of SUPPORTED_CITIES (lowercase)
    road_width_m: float
    plot_type: PlotType       # DETACHED / SEMI_DETACHED / ROW
    corner_plot: bool
    second_road_width_m: float | None
    shared_side: SharedSide | None
    soil_type_known: SoilType | None
```

Plot invariants are upstream (C1/Plot constructor); C4 adds defensive `assert` per § 6.

**Facing convention** (NEW per self-critique #2): given `plot.facing`, the "front" side is the facing direction; "back" is opposite; "left" and "right" are clockwise-from-front rotations of 90° and 270°. For example: `facing=N` → `front=N, right=E, back=S, left=W`. The `compute_plot_facing_sides(plot.facing)` helper returns a `dict[Literal["front","back","left","right"], PlotOrientation]`. This is documented HERE in spec because the convention is shared by C5+; it also lives in code as the helper's docstring.

---

## § 3 — Output contract: `PlotAnalysis`

```python
@dataclass(frozen=True)
class PlotAnalysis:
    # ─── Identity ───
    brief_token: str
    plot: Plot                       # frozen passthrough; original city preserved

    # ─── Computed properties ───
    area_sqft: float
    area_sqm: float
    tier: PlotTier                   # T1 / T2 / T3 (§ 4.1)
    shape: PlotShape                 # RECTANGULAR (always v1) — § 4.2
    shape_metadata: dict             # forward-compat hook (v1: empty)
    aspect_ratio: float              # depth_m / width_m
                                     # >1 = deep plot (long perpendicular to street)
                                     # <1 = wide plot (long parallel to street)
                                     # Convention pinned per self-critique #3

    # ─── Solar / climate ───
    sun_path: SunPath                # § 4.4
    climate_zone: ClimateZone        # NBC 2016 5-zone — § 4.5
    prevailing_wind: WindContext     # § 4.6 (4 fields)

    # ─── Geotechnical ───
    soil_estimate: SoilEstimate      # § 4.7 — confidence-aware

    # ─── Site context ───
    road_width_classification: RoadWidthClass   # § 4.8 — per-city
    neighbour_context: NeighbourContext         # § 4.9 — RAW openness

    # ─── Provenance (caller-injected per critique #11) ───
    provenance: PlotAnalysisProvenance


@dataclass(frozen=True)
class PlotAnalysisProvenance:
    derived_at: float                # caller-injected (NOT time.time() inside C4).
                                     # Tests pass derived_at=0.0 by convention.
    source_versions: dict[str, str]  # auto-populated from KB_VERSION constants

    # source_versions auto-populated keys (per critique #12):
    #   "city_geography"   ← kb/city_geography.KB_VERSION
    #   "wind_load"        ← kb/wind_load.KB_VERSION
    #   "soil_foundation"  ← kb/soil_foundation_rules.KB_VERSION
    #   "road_thresholds"  ← kb/road_width_thresholds.KB_VERSION
    # Bump policy (NEW per self-critique #5):
    #   - Add/remove a city in any KB        → minor bump (v1.1)
    #   - Change an existing city's value    → minor bump
    #   - Change table semantics (new field) → major bump (v2.0)
    #   - Convention rename                  → major bump


class PlotTier(str, Enum):
    T1_COMPACT  = "T1"   # 600 ≤ sqft < 2400
    T2_STANDARD = "T2"   # 2400 ≤ sqft < 4000
    T3_LARGE    = "T3"   # sqft ≥ 4000


class PlotShape(str, Enum):
    RECTANGULAR = "rectangular"   # only value supported in v1
    L_SHAPED    = "l_shaped"      # B-066
    IRREGULAR   = "irregular"     # B-066


@dataclass(frozen=True)
class SunPath:
    latitude_deg: float
    summer_solstice_noon_alt: float
    winter_solstice_noon_alt: float
    sunrise_arc_summer: tuple[float, float]
    sunrise_arc_winter: tuple[float, float]
    baseline_room_orientation_guidelines: dict[str, list[PlotOrientation]]
        # Renamed from "optimal_room_orientations" per critique #17.
        # Climate-driven baselines; C5/C6 produce dynamic recommendations
        # integrating plot facing + aspect ratio + neighbour openness + Vastu.


# ═════════════════════════════════════════════════════════════════════
# CRITICAL FIX (v0.3) — NBC 2016 climate zones
# ═════════════════════════════════════════════════════════════════════
# Verified against NBC 2016 Part 8 Section 1 (Building Services —
# Lighting and Natural Ventilation), §§ 2.2.21–2.2.24 + 3.2.2.
#
# v0.2 had an INCORRECT enum: it listed HOT_HUMID, which does NOT exist
# in NBC 2016, and OMITTED TEMPERATE, which DOES exist. NBC 2016
# inherits the Bansal & Minke 1988 classification and modifies it by
# combining "cold and sunny" + "cold and cloudy" into a single COLD
# zone, giving exactly 5 zones.
class ClimateZone(str, Enum):
    HOT_DRY    = "hot_dry"      # Mean monthly max > 30°C, RH < 55%
    WARM_HUMID = "warm_humid"   # Mean monthly max > 30°C, RH > 55%
                                # (Includes coastal cities + NE India per NBC)
    TEMPERATE  = "temperate"    # Mean monthly max 25-30°C, RH < 75%
                                # (Renamed from "Moderate" in Bansal & Minke;
                                # called TEMPERATE in NBC 2016)
    COLD       = "cold"         # Mean monthly max < 25°C
    COMPOSITE  = "composite"    # No single zone dominates ≥ 6 months
                                # (Internal variation — composite-dry vs
                                # composite-humid — filed as B-069)


@dataclass(frozen=True)
class WindContext:
    # 4 fields per critique #5
    primary_direction: PlotOrientation     # dominant non-monsoon direction
    secondary_direction: PlotOrientation   # second-most-frequent
    monsoon_direction: PlotOrientation     # SW / NE monsoon arrival side
    basic_speed_ms: float                  # IS 875 Part 3


class ConfidenceLevel(str, Enum):
    LOW    = "low"      # city default, high-variability soil region
    MEDIUM = "medium"   # city default, stable-soil region
    HIGH   = "high"     # user-supplied site survey


@dataclass(frozen=True)
class SoilEstimate:
    soil_type: SoilType
    bearing_capacity_kpa: float | None
    confidence: ConfidenceLevel
    source: str  # "user_input" | "city_default" | "regional_average"


class RoadWidthClass(str, Enum):
    NARROW   = "narrow"
    STANDARD = "standard"
    WIDE     = "wide"


@dataclass(frozen=True)
class NeighbourContext:
    open_sides: list[PlotOrientation]    # RAW (pre-setback). C5 must combine
                                         # with C2 setback outputs to compute
                                         # effective usable openness. The
                                         # `effective_open_sides` field is
                                         # filed as B-068.
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
       (sqft < 600 → defensive assert; should be C3a-gated)
```

### § 4.2 Shape determination

v1: always `RECTANGULAR`. `shape_metadata = {}` forward-compat. Polygon support → B-066.

### § 4.3 Corner status

Passthrough from `plot.corner_plot`. Used by § 4.9.

### § 4.4 Sun-path calculation

#### § 4.4.1 KB structure (consolidated per self-critique #1)

`buildemup/kb/city_geography.py`:

```python
KB_VERSION = "v1.0"   # tracks lat + climate-zone tables together

@dataclass(frozen=True)
class CityGeography:
    latitude_deg: float
    climate_zone: ClimateZone
    # Per self-critique #1: latitude and climate zone are co-keyed on
    # the same city set. Single dict avoids drift between the two
    # tables — they MUST update together.

# ═════════════════════════════════════════════════════════════════════
# CRITICAL CORRECTIONS (v0.3) — verified against:
#   - NBC 2016 Part 8 Section 1 (representative cities)
#   - ECBC 2017 climate-zone-finder
#   - Multiple peer-reviewed sources (Sciencedirect, IEEE solar paper)
#
# v0.2 had 7 cities mis-assigned. Fixed inline below with citations.
# ═════════════════════════════════════════════════════════════════════
CITY_GEOGRAPHY = {
    "chennai":       CityGeography(13.08, ClimateZone.WARM_HUMID),
        # was HOT_HUMID (non-existent NBC zone) → corrected to WARM_HUMID
        # NBC 2016 representative city for the warm-humid zone (along with Mumbai).
    "mumbai":        CityGeography(19.08, ClimateZone.WARM_HUMID),
        # was HOT_HUMID → WARM_HUMID (NBC representative).
    "bangalore":     CityGeography(12.97, ClimateZone.TEMPERATE),
        # was WARM_HUMID → TEMPERATE. NBC 2016 representative city for
        # the temperate zone. Mean monthly max 25-30°C, RH < 75%.
    "delhi":         CityGeography(28.61, ClimateZone.COMPOSITE),
        # was HOT_DRY → COMPOSITE. NBC 2016 representative city for the
        # composite zone. Hot-dry summers, cold winters, monsoon — no
        # single regime dominates ≥ 6 months.
    "hyderabad":     CityGeography(17.39, ClimateZone.COMPOSITE),
        # COMPOSITE (unchanged from v0.2).
    "pune":          CityGeography(18.52, ClimateZone.TEMPERATE),
        # was WARM_HUMID → TEMPERATE. Plateau city (~560m elevation),
        # mild summers and winters. Listed alongside Bangalore in NBC
        # examples for the temperate zone.
    "kolkata":       CityGeography(22.57, ClimateZone.WARM_HUMID),
        # was HOT_HUMID → WARM_HUMID. Coastal east, similar profile to
        # Chennai.
    "kochi":         CityGeography(9.93,  ClimateZone.WARM_HUMID),
        # was HOT_HUMID → WARM_HUMID. Kerala coast.
    "bhubaneswar":   CityGeography(20.30, ClimateZone.WARM_HUMID),
        # was HOT_HUMID → WARM_HUMID. East coast.
    "visakhapatnam": CityGeography(17.69, ClimateZone.WARM_HUMID),
        # was HOT_HUMID → WARM_HUMID. East coast.
}


def _assert_kb_keys_aligned():
    """Module-load runtime drift check (per critique #2 + self-critique #6)."""
    from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS
    from buildemup.kb.soil_foundation_rules import SOIL_PROFILES
    geo_keys = set(CITY_GEOGRAPHY.keys())
    wind_keys = set(BASIC_WIND_SPEED_MS.keys())
    soil_keys = set(SOIL_PROFILES.keys())
    if not (geo_keys == wind_keys == soil_keys):
        diff = sorted(geo_keys ^ wind_keys ^ soil_keys)
        raise RuntimeError(
            f"KB drift: city_geography / wind_load / soil_foundation_rules "
            f"have divergent key sets. Symmetric difference: {diff}. "
            f"All three KBs must carry the same city set."
        )

    # Verify KB_VERSION presence on all three (per self-critique #6)
    import buildemup.kb.wind_load as w
    import buildemup.kb.soil_foundation_rules as s
    for mod, name in [(w, "wind_load"), (s, "soil_foundation_rules")]:
        if not hasattr(mod, "KB_VERSION"):
            raise RuntimeError(
                f"kb/{name}.py missing required KB_VERSION constant. "
                f"Add KB_VERSION = 'v1.0' or current value at module top."
            )

_assert_kb_keys_aligned()  # runs at module import
```

#### § 4.4.2 Solar geometry (closed-form, no external lib)

```python
declination = 23.45 × sin(360 × (284 + day_of_year) / 365)  # Cooper 1969
solar_altitude_at_noon = 90° − |latitude − declination|
```

Compute at solstices (June 21 = day 172, Dec 21 = day 355). Per-month → B-067.

Defensive assert: `assert -45 < latitude_deg < 45, ...` — India is 8°-37°N.

#### § 4.4.3 Baseline room orientation guidelines

**v0.3 correction**: v0.2 only sketched 2 of the 5 climate zones. v0.3 enumerates all 5:

```python
BASELINE_ROOM_ORIENTATION_GUIDELINES = {
    ClimateZone.HOT_DRY: {
        # Block intense W/SW summer sun; capture morning E sun.
        "living":   [N, NE],
        "kitchen":  [E, NE],
        "bedroom":  [N, NE, E],
        "bathroom": [W, SW],
    },
    ClimateZone.WARM_HUMID: {
        # Maximise NE/E ventilation paths; avoid afternoon W sun.
        "living":   [N, NE],
        "kitchen":  [E, SE],
        "bedroom":  [N, NE, E],
        "bathroom": [W, SW, NW],
    },
    ClimateZone.TEMPERATE: {
        # Balanced regime; orient social spaces to N for diffuse light,
        # bedrooms can use E for morning warmth.
        "living":   [N, NE, E],
        "kitchen":  [E, NE],
        "bedroom":  [E, NE, N, S],
        "bathroom": [W, NW],
    },
    ClimateZone.COMPOSITE: {
        # Hot-dry summer + cold winter → favour S/SE for winter solar
        # gain, screen W for summer.
        "living":   [N, NE, S],
        "kitchen":  [E, NE],
        "bedroom":  [N, NE, S],
        "bathroom": [W, SW, NW],
    },
    ClimateZone.COLD: {
        # Maximise S solar gain (winter), W sun also welcome.
        "living":   [S, SE],
        "kitchen":  [SE, S],
        "bedroom":  [S, SE, E],
        "bathroom": [N, NW],
    },
}
```

Naming reminder per critique #17: these are **baselines**. C5/C6 produce the actual recommendation by combining with plot facing, aspect ratio, neighbour openness, Vastu, brief preferences.

### § 4.5 Climate zone

`climate_zone = CITY_GEOGRAPHY[normalized_city].climate_zone`. v0.3 corrections inline in § 4.4.1.

**Source: NBC 2016 Part 8 Section 1 (Building Services — Lighting and Natural Ventilation), § 2.2.21–2.2.24 + § 3.2.2**, definitions Table 1 and climatic classification map (Fig. 2).

**Known limitation (B-069 candidate):** NBC 2016 composite zone groups climatically diverse locations. Recent literature (2023-2025 ScienceDirect publications) proposes splitting into composite-dry (Delhi-leaning) and composite-humid (Lucknow-leaning) sub-zones. v1 follows NBC 2016 verbatim; refinement deferred.

### § 4.6 Prevailing wind (4 fields per critique #5)

```python
PREVAILING_WIND = {
    "chennai":   WindContext(NE, E,  SW, 50),
    "mumbai":    WindContext(W,  NW, SW, 44),
    "bangalore": WindContext(W,  SW, SW, 33),
    "delhi":     WindContext(NW, E,  SE, 47),
    # ... [DRAFT-Q for v0.4 if needed: cross-check against IMD wind-rose maps]
}
```

Sources: IMD climatology summaries + India Meteorological Department wind atlases. Cross-check with full IMD wind-rose data → backlog for v2.

### § 4.7 Soil estimate (confidence-aware per critique #6)

Unchanged from v0.2:

```python
HIGH_VARIABILITY_SOIL_TYPES = {SoilType.BLACK_COTTON}

def estimate_soil(plot) -> SoilEstimate:
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

**v0.3 self-critique note (#7):** SoilType enum values must include BLACK_COTTON for the variability check to fire. Existing `domain.plot.SoilType` enum has the values per code review (line 52). LOCK-time check: confirm SoilType has BLACK_COTTON; if not, add as part of C4 build.

### § 4.8 Road width classification (per-city per critique #7)

`buildemup/kb/road_width_thresholds.py`:

```python
KB_VERSION = "v1.0"
DEFAULT_THRESHOLDS = (6.0, 12.0)

ROAD_WIDTH_THRESHOLDS = {
    "mumbai":    (6.0, 12.0),
    "chennai":   (6.0, 12.0),
    "delhi":     (6.0, 13.5),
    "bangalore": (6.0, 12.0),
    # ... [DRAFT-Q for v0.4 if needed]
}

def classify(city: str, road_width_m: float) -> RoadWidthClass:
    narrow_max, standard_max = ROAD_WIDTH_THRESHOLDS.get(city, DEFAULT_THRESHOLDS)
    if road_width_m < narrow_max:    return RoadWidthClass.NARROW
    if road_width_m < standard_max:  return RoadWidthClass.STANDARD
    return RoadWidthClass.WIDE
```

### § 4.9 Neighbour context (RAW; setback adjustment is C5)

Unchanged from v0.2. `open_sides` is RAW; C5 combines with C2 setbacks. Effective post-setback openness → B-068.

**v0.3 documentation (per self-critique #2):** the helper `compute_plot_facing_sides(facing)` returns a 4-key dict `{"front", "back", "left", "right"}` mapped to `PlotOrientation` values. Convention is clockwise-from-front rotation (front → right via 90° CW; front → back via 180°; front → left via 270°).

`plot.shared_side` for SEMI_DETACHED carries an absolute compass direction (`PlotOrientation`), not a relative side label. C4 trusts this.

---

## § 5 — Module layout (unchanged from v0.2)

```
buildemup/components/c04/
    __init__.py
    plot_analysis.py            — orchestrator
    sun_path.py                 — solar geometry (~40 LOC)
    climate_zone.py             — lookup wrapper
    soil_estimator.py           — confidence-aware
    neighbour_context.py
    schema.py                   — dataclasses + enums

buildemup/kb/city_geography.py        — NEW. Consolidated lat + climate per
                                         self-critique #1. Module-import
                                         assertion per critique #2.
buildemup/kb/road_width_thresholds.py — NEW. Per-city DCR cutoffs.
```

---

## § 6 — Failure modes (unchanged from v0.2; defensive asserts retained)

Same table as v0.2. Plus a v0.3 addition:

| Failure | Outcome |
|---|---|
| KB lacks `KB_VERSION` constant on import | `RuntimeError` at module-load (per self-critique #6). |
| `SoilType` enum missing required value (e.g. BLACK_COTTON) | impossible if Plot dataclass is up-to-date. **Defensive assert** on first reference. |

---

## § 7 — Test plan (unchanged; ~22 tests Tier 1)

Test list carries forward from v0.2 unchanged. NEW tests this round:

```
tests/validation/test_c4_kb_consistency.py
  - test_kb_module_import_asserts_kb_version_presence  [self-critique #6]
  - test_climate_zone_assignments_match_nbc_2016       [v0.3 web-research-verified table]
        # Locks the corrections from v0.2 → v0.3:
        # Bangalore=TEMPERATE, Pune=TEMPERATE,
        # Chennai/Mumbai/Kolkata/Kochi/Vizag/Bhubaneswar=WARM_HUMID,
        # Delhi=COMPOSITE, Hyderabad=COMPOSITE.
```

Total Tier 1 budget: still under 1.77s headroom of the 30s cap.

---

## § 8 — Backlog candidates (per Rule 9.2)

**Filed via this spec cycle (carried over from v0.2):**
- B-066 — Polygon plots (L-shaped, irregular)
- B-067 — Per-month sun-path declination
- B-068 — `effective_open_sides` post-setback

**NEW filed this round (v0.3):**
- **B-069** — NBC 2016 composite-zone internal sub-classification (composite-dry vs composite-humid). Origin: v0.3 web research surfaced 2023-2025 academic literature proposing this split. Trigger: when downstream layout outcomes differ materially between Delhi-style and Lucknow-style composite cities. Effort: enum extension + per-city sub-tag + downstream consumer changes (~30 LOC + spec amendment).
- **B-070** — IMD wind-rose data for prevailing wind (vs current single-source-citation per city). Origin: § 4.6 DRAFT-Q + v0.3 self-critique. Trigger: when ventilation-correctness incidents surface in production. Effort: ~20 LOC + 8-direction wind-rose tables per city.

**Other candidates (not filed; flagged for next-spec-cycle visibility):**
- C7 retrofit to consume `PlotAnalysis.soil_estimate`
- Geotech-survey advisory `requires_site_survey: bool` flag
- Vastu overlay on baseline_room_orientation_guidelines (C5/C6 today)
- Regional-cluster fallback for unknown cities
- Per-city road-width FAR cutoff overrides (related to § 4.8 but FAR-specific)
- Per-day sun-path (extends B-067)

---

## § 9 — Verification at LOCK time

- Tier 1: ~22 tests, ~3-5s added; under 30s cap.
- Tier 2: 0 new.
- Production code: ~250-350 LOC + ~150 LOC across 2 KB files.
- 1 module-load runtime assertion in `kb/city_geography.py`.

---

## § 10 — Resolved DRAFT-Qs (final)

| DRAFT-Q | Resolution |
|---|---|
| 1. NBC climate-zone count + section number | **CONFIRMED via web research:** 5 zones (HOT_DRY, WARM_HUMID, TEMPERATE, COLD, COMPOSITE). **NBC 2016 Part 8 Section 1**, §§ 2.2.21–2.2.24 + 3.2.2. (v0.2 had this PROPOSED pending Ramalingam; v0.3 verifies independently per Rule 7 web-search.) |
| 2. Delhi climate zone | **CORRECTED:** COMPOSITE (was HOT_DRY in v0.2). Delhi is the NBC representative city for COMPOSITE zone. |
| 3. Sun-path day-by-day vs solstice envelope | Solstice envelope for v1; per-month → B-067. |
| 4. Vastu vs climate for room orientations | Climate-only baselines in C4; renamed to `baseline_room_orientation_guidelines`. Vastu = C5/C6. |
| 5. Bearing capacity surfacing | `confidence` enum added; bearing_capacity_kpa retained. |
| 6. Road-width cutoffs city-specific | Yes — `kb/road_width_thresholds.py` per-city. |
| 7. Wind direction sources | IMD climatology in v1; full wind-rose → B-070. |
| 8. C7 retrofit | Deferred to backlog candidate. § 1 wording softened. |

---

## § 11 — Spec-amendment expectations

This is **v0.3 PROPOSED**. Lifecycle:

- v0.1 DRAFT (S28) → external critique
- v0.2 PROPOSED (S28) → factual-error catch by Ramalingam ("did you web-search?")
- **v0.3 PROPOSED** (this) → **PENDING Ramalingam LOCK adjudication per Rule 8**
- v0.x LOCKED → code build per Rule 1

If another critique round arrives, walk into v0.4 PROPOSED. LOCK is Ramalingam's call alone.

---

## § 12 — Backlog visibility (per Rule 9 § 12 requirement)

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-066 | Polygon plots (L-shaped, irregular) | C4 v0.1 § 4.2 + critique #13 | C1 polygon entry | OUT (v1 = rect) | ~150 LOC + spec |
| B-067 | Per-month sun-path declination | C4 critique #4 | C5/C6 shading studies | OUT | ~60 LOC |
| B-068 | `effective_open_sides` post-setback | C4 critique #8 | C5 ships + facade over-count seen | OUT | ~20 LOC |
| **B-069** | **Composite-zone internal sub-classification** | **C4 v0.3 web research** | **Layout outcomes diverge between composite cities** | **OUT (NBC 2016 = single COMPOSITE)** | **~30 LOC + spec** |
| **B-070** | **IMD wind-rose data per city** | **C4 v0.3 § 4.6 self-critique** | **Ventilation-correctness incidents** | **OUT (single-direction sufficient v1)** | **~20 LOC** |
| B-057 to B-065 | Session 28 — see backlog_session_28.md | various | various | OUT | various |
| B-001 to B-056 | Pre-S28 — see v0_2_backlog.md | various | various | various | various |

---

## § 13 — Rule-7 walk records

### v0.1 → v0.2 (external critique, 17 items)

13 VALID-PATCH applied · 3 VALID-BUT-BACKLOG (B-066/067/068) · 1 MISFRAMED (#14 caching, pushback) · 1 ALREADY-DOCUMENTED (#1 C7 retrofit half).

### v0.2 → v0.3 (Rule-7 web-search-required pass + self-critique)

**Background:** Rule 7 mandates "Web-search to verify external claims before accepting. Push back when wrong." I missed this in v0.2 round. Ramalingam caught it. v0.3 does the missed work + adds self-critique.

**v0.3 corrections from web research (NBC 2016 Part 8 Section 1 + ECBC 2017 + multiple peer-reviewed sources):**

| Item | v0.2 (wrong) | v0.3 (corrected) |
|---|---|---|
| ClimateZone enum | HOT_HUMID present (non-NBC), TEMPERATE absent | **TEMPERATE present, HOT_HUMID removed** |
| Bangalore zone | WARM_HUMID | **TEMPERATE** (NBC representative) |
| Pune zone | WARM_HUMID | **TEMPERATE** |
| Chennai zone | HOT_HUMID | **WARM_HUMID** (NBC representative) |
| Mumbai zone | HOT_HUMID | **WARM_HUMID** (NBC representative) |
| Kolkata, Kochi, Vizag, Bhubaneswar | HOT_HUMID (×4) | **WARM_HUMID** (×4) |
| Delhi zone | HOT_DRY | **COMPOSITE** (NBC representative) |
| Hyderabad | COMPOSITE | COMPOSITE (no change) |
| Section reference | "Part 8 § 1.2.4 [memory; Ramalingam to verify]" | **NBC 2016 Part 8 Section 1, §§ 2.2.21–2.2.24 + 3.2.2** (verified) |

**v0.3 self-critique additions (5 items I should have caught independently in v0.1/v0.2):**

| # | Item | Resolution in v0.3 |
|---|---|---|
| 1 | CITY_LATITUDE and CITY_CLIMATE_ZONE were duplicated metadata co-keyed on the same city set | Consolidated into single `CITY_GEOGRAPHY` dict-of-dataclass (§ 4.4.1). |
| 2 | "Front/back/left/right" mapping for `compute_plot_facing_sides(facing)` was buried in a helper docstring; convention not pinned in spec | Documented in § 2 explicitly. |
| 3 | `aspect_ratio` convention not pinned (depth/width vs long/short axis) | Documented in § 3 (`depth/width`; >1 = deep, <1 = wide). |
| 4 | `provenance.derived_at` test-time convention not stated | Documented in § 3 (tests pass `derived_at=0.0`). |
| 5 | KB_VERSION bump policy unwritten | Documented in § 3 (minor for value/key changes; major for semantic changes). |
| 6 | Module-load assertion verifies key alignment but not KB_VERSION presence | Extended to assert `KB_VERSION` attribute on all 3 KBs (§ 4.4.1). |

**v0.3 backlog items filed per Rule 9.2 (always-file directive):** B-069, B-070.

**Net effect on v0.3:** spec body shrunk slightly (consolidating CITY_LATITUDE + CITY_CLIMATE_ZONE) while adding correctness. Architecture unchanged. The 7 mis-assigned cities + the missing TEMPERATE enum value would have been a v1 release-blocker had they reached code; catching them at spec stage is the entire point of the DRAFT → critique → LOCK discipline.
