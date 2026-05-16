# BuildemUp Component 4 (Plot Analysis) — SPEC v0.6 PROPOSED

**Status:** **v0.6 PROPOSED. PENDING Ramalingam LOCK adjudication.** Per Rule 8, this version is not LOCKED until Ramalingam explicitly says "lock it" / "v0.6 LOCKED". This document is the **patch delta** over v0.5 LOCKED — it does not restate the full v0.5 spec body. Reading order: read v0.5 first, then this delta.

**Generated:** S29 mid-session, after C4 SHIP and code-review critique round 1.
**Source critique:** 10-item document supplied by Ramalingam.
**Adjudication-window context:** v0.5 was locked and code shipped (1389/2 skipped/0 failed). This walk handles a post-SHIP critique round per D-066 Step 8 and Rule 7.

---

## § 13 — Rule-7 walk (v0.5 → v0.6)

### Verification gates run BEFORE this walk (Rule 7 prerequisites)

1. **Code-grep on existing codebase:**
   - `kb/soil_classification.py`: confirmed only `SOFT_ROCK (660 kPa)` and `HARD_ROCK (1620 kPa)` exist as rock classes. NO `MEDIUM_ROCK` in the source KB. Mapping is the only available downcast.
   - `domain/brief.py`: confirmed `trace_id: str = ""` with no format/uniqueness enforcement upstream. Generated nowhere; defaulted to empty string.
2. **Web-research on factual claims about external standards:**
   - IS 875 Part 3: India basic wind speeds = 33–55 m/s; cyclonic up to ~70 m/s. Source: scribd / civilengineeringweb / IIT-K GSDMA / studocu. Cross-confirmed.
   - IS 6403 / IS 1904: typical SBC for "weathered rock" 300–800 kPa; "medium weathered mudstone" 1500–2500 kPa; "foliated metamorphic" 1500–3000 kPa. Source: engineersviews / NCBI mudstone study / civilblog. Cross-confirmed.
3. **Performance measurement (1000 warmed calls of `derive()` on chennai_30x40):**
   - min: 0.009 ms · p50: 0.010 ms · p95: 0.015 ms · p99: 0.031 ms · max: 0.064 ms · mean: 0.011 ms.

These results inform the verdicts below.

### Critique walk

| # | Critique summary | Verdict | Resolution |
|---|---|---|---|
| 1 | Float-based tier classification fragile at boundaries (2399.998 sqft) | **VALID — SPEC-AMENDMENT** | Compare in sqm space using exact conversion factor `1 sqft = 0.09290304 sqm`. |
| 2 | Hard-coded `MEDIUM_ROCK → SOFT_ROCK (660 kPa)` is silent domain loss | **PARTIALLY VALID — SPEC-AMENDMENT (provenance) + B-074 (kPa value fix)** | Add `provenance_note: str \| None` to `SoilEstimate`. File real-kPa fix as backlog. |
| 3 | Wind data marked PROPOSED but used as truth | **VALID — SPEC-AMENDMENT** | Add `confidence: ConfidenceLevel` to `WindContext`; all 6 cities = MEDIUM (single-station IMD) until B-070 promotes to HIGH. |
| 4 | No validation for extreme aspect ratios (3m × 60m → ratio=20) | **VALID-BUT-BACKLOG (B-075)** + light DOCUMENTED note | C3a is the proper input gate; aspect classification waits for a real downstream consumer (Pattern B). Add a docstring note on `aspect_ratio` field. |
| 5 | CONTINUOUS+corner always picks LEFT — arbitrary | **VALID — SPEC-AMENDMENT (surface assumption)** + B-076 (input contract fix) | Add `corner_assumption: str \| None` field to `NeighbourContext` exposing the inferred side; deeper fix (`Plot.corner_orientation` field) → B-076. |
| 6 | KB consistency check only validates presence | **VALID — SPEC-AMENDMENT** | Tighten `verify_kb_consistency()` with sanity ranges: wind ∈ [30, 70] m/s, latitude ∈ [5, 40]°, kPa ∈ [10, 2000]. |
| 7 | Soil confidence is too coarse (LOW/MEDIUM/HIGH) | **DUPLICATE of #2 (resolved by same `provenance_note`)** + B-077 (richer model deferred) | The same field added in #2 carries the reason; full multi-state model deferred. |
| 8 | Sun path ignores longitude (time offset) | **DOCUMENTED (push back partial)** | Longitude is mathematically irrelevant for solstice noon altitude (depends only on \|lat − decl\|). Add docstring note; no code change. B-067 already covers per-month declination. |
| 9 | trace_id not validated for uniqueness/format | **MISFRAMED — PUSH BACK** + B-078 (system-wide policy) | Upstream contract is `Brief.trace_id: str = ""` (empty default; no format/uniqueness enforcement at origin). C4 enforcing format would violate the upstream contract. File system-wide trace_id policy as B-078; not a C4 fix. |
| 10 | Performance test too loose (10ms p95) | **VALID — SPEC-AMENDMENT** | Tighten p95 cap to **1.0 ms** (~66× current measured p95 of 0.015 ms). 3ms (critique's suggestion) is still 200× current; 1ms balances regression detection vs CI-host jitter. |

**Tally:** 5 SPEC-AMENDMENTS (folded into v0.6). 4 new backlog items (B-074, B-075, B-076, B-077, B-078 — counted 5; #2 spawns 1, #4 spawns 1, #5 spawns 1, #7 spawns 1, #9 spawns 1). 1 DOCUMENTED-only (#8). 1 PUSH-BACK (#9 main claim, partially backlogged). 1 DUPLICATE (#7 → #2 same field).

---

## § 14 — v0.6 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — Tier classification in sqm space (item 1)

**Spec § 4.1 amended:**

```
# Exact conversion factor (NOT the rounded 10.7639):
SQM_PER_SQFT = 0.09290304  # 1 ft² = 0.3048² m² exactly (IEC convention)

# Thresholds expressed in sqm (the canonical computed unit):
_T1_MIN_SQM =  600.0 * SQM_PER_SQFT  #  55.74182400 sqm
_T2_MIN_SQM = 2400.0 * SQM_PER_SQFT  # 222.96729600 sqm
_T3_MIN_SQM = 4000.0 * SQM_PER_SQFT  # 371.61216000 sqm

# area_sqft remains a derived presentation field on PlotAnalysis for UX;
# tier comparison happens in sqm space (no second-order rounding).
```

**Why sqm not sqft:** the input is already in metres (`Plot.width_m × Plot.depth_m`), so `area_sqm` is the canonical computed value. Going via `area_sqft = sqm × 10.7639` introduces a second rounding step (the 10.7639 factor itself is rounded). Comparing in sqm eliminates that.

**Test addition:** `test_tier_boundary_at_2400_sqft_lands_in_t2` — explicit boundary case using 12.192×18.288 m (textbook 40×60 ft).

### § 14.2 — Soil estimate provenance note (items 2, 7)

**Spec § 3 `SoilEstimate` dataclass amended:**

```python
@dataclass(frozen=True)
class SoilEstimate:
    soil_type: SoilType
    bearing_capacity_kpa: float | None
    confidence: ConfidenceLevel
    source: str                          # "user_input" | "city_default"
    provenance_note: str | None = None   # NEW v0.6: surfaces approximation
                                         # decisions or high-variability reasons.
                                         # Examples below.
```

**Spec § 4.7 `estimate_soil()` amended to populate `provenance_note`:**

| Branch | Soil resolution | provenance_note |
|---|---|---|
| user_input | exact SoilType key in BEARING_CAPACITY_BY_TYPE | None |
| user_input | MEDIUM_ROCK (no exact KB equivalent) | `"medium_rock_approximated_to_soft_rock_660kpa_underestimate_b074"` |
| city_default | typical_soil ∈ HIGH_VARIABILITY_SOIL_TYPES | `f"{typical_soil.value}_high_variability_site_survey_required"` |
| city_default | else | None |

The `_b074` suffix on the MEDIUM_ROCK note acts as an in-source breadcrumb to the deferred fix (B-074).

**Test additions:** `test_soil_estimate_user_input_medium_rock_carries_provenance_note`, `test_soil_estimate_mumbai_carries_high_variability_note`, `test_soil_estimate_chennai_default_has_no_provenance_note`.

### § 14.3 — Wind data confidence (item 3)

**Spec § 3 `WindContext` dataclass amended:**

```python
@dataclass(frozen=True)
class WindContext:
    primary_direction: PlotOrientation
    monsoon_direction: PlotOrientation
    city: str
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM   # NEW v0.6
    # ConfidenceLevel mapping:
    #   MEDIUM = single-station IMD climatology (current state of all 6 cities).
    #   HIGH   = full per-city wind-rose verified (B-070 promotes when complete).
    #   LOW    = reserved for known-bad data; not currently used.

    @property
    def basic_speed_ms(self) -> float:
        from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS
        return float(BASIC_WIND_SPEED_MS[self.city])
```

**Spec § 4.6 `PREVAILING_WIND` table:** all 6 entries get `confidence=ConfidenceLevel.MEDIUM` explicitly (was implicit "PROPOSED" in v0.5).

**Consumer contract addendum to spec § 3:** "Components reading `WindContext.confidence == MEDIUM` MAY apply fallback heuristics (e.g., assume isotropic monsoon dominance) when ventilation logic depends on tight directional resolution. C5 ventilation logic SHOULD read this flag."

**Test addition:** `test_all_prevailing_wind_entries_carry_medium_confidence_until_b070`.

### § 14.4 — KB consistency value-quality checks (item 6)

**Spec § 4.4.2 `verify_kb_consistency()` amended:**

```python
def verify_kb_consistency() -> None:
    # ... existing presence checks unchanged ...

    # NEW v0.6: value-quality sanity ranges.
    # These are LOOSE bounds for fail-fast on copy-paste / unit errors,
    # NOT design bounds. Tight per-standard ranges:
    #   IS 875 Part 3:   India basic wind = 33–55 m/s, cyclonic up to ~70.
    #   India geography: latitudes 8°-37° N (with margin → 5°-40°).
    #   IS 6403 / IS 1904: typical residential SBC range 50–2000 kPa.
    for city, speed in BASIC_WIND_SPEED_MS.items():
        if not (30.0 <= speed <= 70.0):
            raise RuntimeError(
                f"KB drift: kb/wind_load wind speed for {city} = {speed} m/s "
                f"out of plausible range [30, 70]. Per IS 875 Part 3."
            )
    for city, geo in CITY_GEOGRAPHY.items():
        if not (5.0 <= geo.latitude_deg <= 40.0):
            raise RuntimeError(
                f"KB drift: kb/city_geography {city} latitude = {geo.latitude_deg}° "
                f"out of India range [5, 40]."
            )
    for city, prof in SOIL_PROFILES.items():
        if not (10.0 <= prof.typical_bearing_capacity_kpa <= 2000.0):
            raise RuntimeError(
                f"KB drift: kb/soil_city_defaults {city} kPa = "
                f"{prof.typical_bearing_capacity_kpa} out of plausible "
                f"residential range [10, 2000]."
            )
```

**Test addition:** `test_kb_drift_detected_for_out_of_range_wind_speed`, `test_kb_drift_detected_for_out_of_range_latitude`, `test_kb_drift_detected_for_out_of_range_kpa` (each via monkeypatch).

### § 14.5 — Corner-plot assumption surfacing (item 5)

**Spec § 3 `NeighbourContext` dataclass amended:**

```python
@dataclass(frozen=True)
class NeighbourContext:
    open_sides: tuple[PlotOrientation, ...]
    shared_sides: tuple[PlotOrientation, ...]
    raw_facade_count: int
    corner_assumption: str | None = None  # NEW v0.6: surfaces the v1
                                          # convention used to pick the
                                          # second-street side when the
                                          # input contract underspecifies it.
```

**Population rules:**
- Non-corner plot → `None`.
- Corner DETACHED → `None` (all sides already open; no assumption).
- Corner SEMI_DETACHED → `None` (deterministic from `shared_side`).
- Corner CONTINUOUS, no `Plot.corner_orientation` (v1 input has no such field) → `"second_street_assumed_LEFT_b076"` — breadcrumbs to B-076.

**Consumer contract addendum:** "Components reading `corner_assumption is not None` SHOULD treat downstream layout decisions affected by the second-street side as TENTATIVE pending B-076."

**Test addition:** `test_corner_continuous_carries_assumption_breadcrumb`, `test_corner_semidetached_carries_no_assumption`, `test_non_corner_carries_no_assumption`.

### § 14.6 — Sun path longitude doc note (item 8)

**Spec § 4.4.3 amended:**

```python
# NOTE: longitude is mathematically irrelevant for the solstice noon
# altitude formula `90° − |latitude − declination|`. Longitude only
# shifts the WALL-CLOCK time of solar noon, not its altitude or compass
# azimuth. C5/C6 use the envelope (altitude + azimuth at solstice), not
# the wall-clock time, so longitude is correctly omitted. This becomes
# relevant only for: hourly shading studies, daylight simulation, solar
# panel performance modeling — all out of scope for v1 (B-067 covers the
# adjacent per-month declination work).
```

No code change. Documentation only.

### § 14.7 — Performance cap tightening (item 10)

**Spec § 7 perf test amended:**

```python
def test_derive_completes_under_1ms_for_typical_plot():
    """1000-call P95 must beat 1.0 ms.

    Measured baseline (S29 codebase): p50 ≈ 0.010 ms, p95 ≈ 0.015 ms,
    max ≈ 0.064 ms (1000 warmed samples on dev host). The 1.0 ms cap is
    ~66× current p95 — comfortable headroom for slower CI hosts while
    catching any meaningful regression (e.g., accidental I/O at call time,
    or O(n²) loops added in future).
    """
    # ... 1000 calls, p95 < 1.0 ms ...
```

Sample size bumped 100 → 1000 for tighter p95 confidence. Cap 10ms → 1.0 ms.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — item #9 (trace_id format/uniqueness validation)

**Critique claim:** C4 should enforce length, format, or uniqueness on `trace_id`.

**Pushback:** C4 reads `trace_id` from the upstream `ResolvedBrief.revised_brief.trace_id`. Code-grep confirms the upstream contract:

```python
# buildemup/domain/brief.py line 253
trace_id: str = ""
```

The default is **empty string** with **no `__post_init__` validation, no UUID enforcement, no length check, nothing**. Adding format enforcement at the C4 read site would make C4 stricter than its own input contract — a Pattern A "fix as bandage" anti-pattern (see RULES_RAMALINGAM_FORMALIZED), and would break in production the moment any caller produces a Brief without setting trace_id explicitly (which is the documented default).

The right fix is system-wide: a trace_id lifecycle policy at the origin point (where Briefs are constructed). That's filed as **B-078**.

C4's current check (non-None str) is the appropriate read-site contract: defend against type errors, trust upstream for content shape.

### Pushback B — item #8 main claim (longitude affects sun path)

**Critique claim:** "Sun path model ignores longitudinal variation (time offset)" — implies a correctness gap.

**Pushback:** For the formulae C4 uses — `solar_altitude_at_noon = 90° − |latitude − declination|` and sunrise/sunset compass azimuth `cos(A) = sin(decl) / cos(lat)` — longitude is **mathematically absent**. Longitude only shifts the WALL-CLOCK time of solar noon, not its altitude or compass position. Since C5/C6 consume the angular envelope (altitude + compass azimuth), not local time, longitude omission is **not a correctness gap**. The critique's footnote ("Minor now, but becomes relevant if: shading, daylight simulation, solar panel optimization") is correct — those features would need full diurnal modeling, which is per-hour, not per-day. Filed under existing **B-067** (per-month declination → also per-hour modelling when promoted).

---

## § 16 — Backlog roll-up (Rule 9)

### New backlog items added in v0.6

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-074 | MEDIUM_ROCK proper kPa value (currently approximated to SOFT_ROCK 660 kPa, real ~1000–1500 kPa per IS 6403). Resolution requires either extending kb.SoilClass with a MEDIUM_ROCK class OR aligning C4's BEARING_CAPACITY_BY_TYPE with C7's foundation-design defaults. | v0.6 walk #2 | C7 retrofit B-072 active | OUT (v0.6) | ~30 LOC + KB review |
| B-075 | Aspect ratio classification (`AspectClass` enum) and extreme-plot detection (e.g., aspect_ratio > 5 → flag). | v0.6 walk #4 | C5 layout heuristic break observed in extreme test cases | OUT (v0.6) | ~20 LOC |
| B-076 | `Plot.corner_orientation: PlotOrientation \| None` input-contract field for corner plots, eliminating the v1 LEFT-default convention. Touches C1/C3a/C7. | v0.6 walk #5 | corner-plot ambiguity surfaces in C5 layouts | OUT (v0.6) | ~50 LOC + 3-component coordination |
| B-077 | Richer soil confidence model (multi-state, e.g., HIGH-survey / MEDIUM-stable / LOW-variable / LOW-liquefaction / LOW-fill). Currently captured as free-text `provenance_note` (v0.6 SPEC-AMENDMENT). | v0.6 walk #7 | C7 retrofit B-072 active OR insurer/code requirement surfaces | OUT (v0.6) | ~40 LOC |
| B-078 | System-wide trace_id lifecycle policy: format (e.g., UUID4), uniqueness scope, generation site (Brief constructor), and validation at all read sites. Touches every component reading trace_id. | v0.6 walk #9 | observability/debug session needs trace_id correlation across components | OUT (v0.6) | ~20 LOC + cross-component sweep |

### Pre-existing backlog (carried, no change)

| ID | Description | Status |
|---|---|---|
| B-066 | Polygon plots | Carried |
| B-067 | Per-month sun-path declination | Carried (v0.6 walk #8 references this) |
| B-068 | effective_open_sides (post-setback) | Carried |
| B-069 | Composite-zone sub-classification | Carried |
| B-070 | IMD wind-rose per city (promotes wind confidence MEDIUM → HIGH; v0.6 walk #3 references) | Carried |
| B-071 | Latitude-band city fallback | Carried |
| B-072 | C7 retrofit to consume PlotAnalysis.soil_estimate (v0.6 walks #2, #7 reference) | Carried |
| B-001 .. B-065 | Pre-S28 entries | Carried |

### Summary table of backlog items touching v0.6 walk

| Walk item | Backlog ref | New / pre-existing |
|---|---|---|
| #2 (mapping value) | B-074 | NEW |
| #2 / #7 (richer confidence) | B-077 | NEW |
| #3 (wind verification) | B-070 | pre-existing |
| #4 (aspect class) | B-075 | NEW |
| #5 (corner_orientation) | B-076 | NEW |
| #7 (richer soil model) | B-077 | NEW (same as above) |
| #8 (longitude/diurnal) | B-067 | pre-existing |
| #9 (trace_id policy) | B-078 | NEW |

**Total NEW backlog this walk:** 5 items (B-074, B-075, B-076, B-077, B-078). All filed at v0.6 PROPOSED time per Rule 9.2.

---

## § 17 — What v0.6 LOCKS

If Ramalingam locks v0.6 PROPOSED:

1. Five SPEC-AMENDMENTS land in code (sections § 14.1 through § 14.7 — note § 14.6 is doc-only, so 5 actual code sections + 1 doc).
2. Five new backlog items file (B-074..B-078).
3. Two pushbacks documented and held (items #9 and #8 main claim).
4. Estimated code delta: ~80 LOC schema/logic + ~120 LOC tests. Existing tests should remain passing (no contract-breaking changes — all field additions have safe defaults).
5. Re-run full project tests to confirm no regressions.

**Architecture: identical to v0.5.** No new modules. No removed fields. Only field additions with `None` defaults and one comparison-space change (sqft→sqm).

---

## § 18 — v0.6 verification at LOCK time (estimated)

- Tier 1: ~12 new tests (boundary, soil provenance ×3, wind confidence, KB-drift sanity ×3, corner assumption ×3, perf cap re-cap).
- Tier 2: 0 new.
- Production code: ~80 LOC across schema.py, plot_analysis.py, soil_estimator.py, neighbour_context.py, kb/wind_direction.py, kb/city_geography.py.
- Zero edits to shipped code outside v0.5's surface (C7, C2, C1 untouched).
- Existing 1389 tests re-run + 12 new = ~1401 expected passing.

---

## § 19 — Status

**v0.6 PROPOSED. PENDING Ramalingam LOCK adjudication.**

Adjudication-window critiques arriving between PROPOSED and LOCK remain PATCH-eligible per Rule 8 — additional critique items will produce v0.7 PROPOSED, NOT backlog entries, until Ramalingam locks.
