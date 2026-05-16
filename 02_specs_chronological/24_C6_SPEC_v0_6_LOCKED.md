# BuildemUp — C6 Orientation Priority — SPEC v0.6 LOCKED

**Status**: LOCKED. Adjudicated by Ramalingam at S31 (mid-session, post-pre-code Q&A patch round). Proceed to D-066 Step 6 (code build).
**Component**: C6 of canonical 17-component v3 list (Track 3).
**Position in pipeline**: Era 2 layout. Consumes C4 + C5 + brief.vastu_tier; produces input for C8 corridor designer.
**Predecessor**: v0.5 LOCKED.
**Patch type**: Pre-code clarification round (S31, D-066 Step 6 prep). Not a critique walk — three discrete defects surfaced during pre-code spec/codebase cross-check, adjudicated by Ramalingam before any line of code was written.
**Rule 7 surface**: No external-standards factual claims in this patch round (mechanical enum drop, internal `NotImplementedError`, type-correctness wording clarification). No web research required; cleared at start of patch.

**Lineage delta from v0.5 LOCKED** (three discrete changes; all from S31 pre-code Q&A):

1. **Q1-A — Drop `PlotDirection8` enum** (§ 3, § 4.1.4, § 13). The existing `domain/envelope.py:PlotOrientation` is *already* 8-direction. `PlotDirection8` was a redundant duplicate introduced under a wrong premise about the upstream enum. Mechanical simplification, no behavior change. New AD § 14.19.
2. **Q1-B — Cardinal-only v1 facing** (§ 6, § 9, § 12). C5's `default_zone_bands(facing)` accepts intercardinal `PlotOrientation` values (e.g. `NORTHEAST`) and produces intercardinal zone_bands. C6's logic assumes 4-direction zone_bands; intercardinal would silently break Hamming distance and seed comparison. v0.6 adds explicit fail-fast at C6's input boundary; defers 8-dir external support to **B-107** (mirrors B-066 / B-098 pattern). New AD § 14.19.
3. **Q2 — `CIRCULATION` as private pseudo-function helper** (§ 4.4 step 3, § 13). v0.5 § 4.4 step 3 wrote `function_scores[CIRCULATION][...]` but `function_scores: Mapping[FunctionRole, float]` and `FunctionRole` does not include `CIRCULATION`. v0.6 clarifies: `CIRCULATION` is a `ZoneBand`, not a `FunctionRole`; its scoring is a private `_circulation_score(...)` helper inside `optimizer.py`, not a public `function_scores` key. No behavior change; type-correctness clarification only. New AD § 14.20.

---

## § 1 — Purpose

(unchanged)

C5 selects a topology *kind* and assigns a *default* `zone_bands` mapping that rigidly follows `plot.facing`. C6 reads three signals — sun, wind, Vastu (opt-in) — plus enforces the road-on-entry hard constraint, computes per-direction functional priorities, and refines each C5 candidate's `zone_bands` via global permutation search, preserving input cardinality.

**Out of scope for C6**: building massing rotation, room sizing, room placement, room-to-room adjacency, corridor geometry. C6 only refines *which compass direction gets which functional band*.

---

## § 2 — Input contract

(unchanged)

```python
def prioritize_orientation(
    candidates: tuple[TopologyCandidate, ...],   # 1-3 from C5
    plot_analysis: PlotAnalysis,                  # from C4
    vastu_tier: VastuTier = VastuTier.OFF,        # from C1.brief
) -> tuple[OrientedCandidate, ...]:
```

Cardinality preserved (1-3 in → 1-3 out, position-paired).

---

## § 3 — Output schema — *v0.6 changes*

**v0.6 changes**: `PlotDirection8` enum **REMOVED** (Q1-A — was a redundant duplicate of the existing 8-direction `PlotOrientation`). Internal Vastu computation now uses `PlotOrientation` directly. All other dataclasses unchanged from v0.5.

```python
class FunctionRole(str, Enum):
    LIVING       = "living"
    BEDROOM      = "bedroom"
    KITCHEN      = "kitchen"
    POOJA        = "pooja"
    WET_AREA     = "wet_area"
    UTILITY      = "utility"

# (No PlotDirection8 — use domain.envelope.PlotOrientation throughout.)

@dataclass(frozen=True)
class SignalBreakdown:
    sun_score:    float   # [0, 1] — contributes to function_scores
    wind_score:   float   # [0, 1] — contributes to function_scores
    road_score:   float   # [0, 1] — provenance only (§ 14.14)
    vastu_score:  float   # [0, 1] — contributes; == 0.0 iff vastu_tier == OFF

@dataclass(frozen=True)
class DirectionPriorityScore:
    function_scores:  Mapping[FunctionRole, float]   # each [0, 1]
    signal_breakdown: SignalBreakdown

@dataclass(frozen=True)
class OrientationProvenance:
    derived_at:               float
    plot_analysis_trace_id:   str
    vastu_tier:               VastuTier
    weights_applied:          Mapping[str, float]   # post-renormalization
    weights_raw:              Mapping[str, float]   # pre-normalization (§ 14.16)
    signal_dominance:         float                  # v0.5 — max(weights_raw) / sum(weights_raw)
    dominant_signal:          str | None             # v0.5 — "sun" | "wind" | "vastu" | None
    climate_profile:          str
    rule_trace:               tuple[str, ...]
    permutation_search_size:  int
    chosen_over_seed:         bool
    seed_distance:            int

@dataclass(frozen=True)
class OrientationPriority:
    direction_priorities: Mapping[PlotOrientation, DirectionPriorityScore]
    refined_zone_bands:   Mapping[ZoneBand, PlotOrientation]
    priority_confidence:  float                       # margin-clamped (§ 4.5)
    score_margin:         float
    provenance:           OrientationProvenance

@dataclass(frozen=True)
class OrientedCandidate:
    topology_candidate: TopologyCandidate
    orientation:        OrientationPriority
```

**Contract clarification (v0.6 § 14.19)**: `direction_priorities` keys are exactly the four cardinal members of `PlotOrientation`: `NORTH`, `EAST`, `SOUTH`, `WEST`. `refined_zone_bands` values are also restricted to those four cardinals (per the v1 cardinal-only facing constraint — see § 6). Intercardinal `PlotOrientation` members exist in the enum but are unused in C6 v1 output.

---

## § 4 — Behavior

### § 4.1 — Per-direction baselines

(unchanged from v0.5 except § 4.1.4 wording per Q1-A)

**§ 4.1.1 — Sun-score table**:

| Direction | sun_score |
|-----------|-----------|
| North     | 0.95      |
| East      | 0.85      |
| South     | 0.55      |
| West      | 0.20      |

**§ 4.1.2 — Wind-score table** (climate-conditional):

| Direction | warm-humid | composite | temperate |
|-----------|------------|-----------|-----------|
| North     | 0.6        | 0.7       | 0.7       |
| East      | 0.7        | 0.6       | 0.7       |
| South     | 0.9        | 0.5       | 0.7       |
| West      | 0.85       | 0.5       | 0.7       |

**§ 4.1.3 — Road-score** (provenance only):

```
road_score(direction, plot) = (
    1.0  if direction == plot.facing
    0.5  if direction == secondary_road_direction (corner plots only)
    0.0  otherwise
)
```

Computed and exposed in `SignalBreakdown` for inspection. **Does NOT contribute to `function_scores`** — entry-on-road enforced as hard constraint at § 4.4 step 2.

**§ 4.1.4 — Vastu computation (8-direction internal, weighted-avg aggregation) — *v0.6 wording change***:

8-direction × 6-function Vastu table (PARTIAL tier baseline). Keyed by all 8 `PlotOrientation` members (no separate `PlotDirection8` enum — Q1-A):

| Direction | living | bedroom | kitchen | pooja | wet_area | utility |
|-----------|--------|---------|---------|-------|----------|---------|
| NORTH     | 0.85   | 0.6     | 0.3     | 0.7   | 0.4      | 0.5     |
| NORTHEAST | 0.9    | 0.5     | 0.1     | **1.0** | **0.0**  | 0.3     |
| EAST      | 0.85   | 0.7     | 0.5     | 0.85  | 0.3      | 0.5     |
| SOUTHEAST | 0.55   | 0.4     | **1.0** | 0.3   | 0.4      | 0.5     |
| SOUTH     | 0.5    | 0.4     | 0.7     | 0.2   | 0.5      | 0.6     |
| SOUTHWEST | 0.4    | **1.0** | 0.4     | 0.2   | 0.5      | 0.7     |
| WEST      | 0.5    | 0.7     | 0.6     | 0.3   | 0.7      | 0.85    |
| NORTHWEST | 0.55   | 0.6     | 0.7     | 0.3   | 0.7      | 0.9     |

**Weighted-average aggregation rule** (8-dir table → 4-dir cardinal score):

```
vastu_score_4dir(c, f) = (
    1.0 × VASTU_TABLE[c][f]                  # cardinal, full weight
  + 0.5 × VASTU_TABLE[ccw_adjacent(c)][f]    # CCW intercardinal, half weight
  + 0.5 × VASTU_TABLE[cw_adjacent(c)][f]     # CW intercardinal, half weight
) / 2.0
```

`c ∈ {NORTH, EAST, SOUTH, WEST}` (cardinal only at the consumption point). Adjacency: `NORTH → {NORTHWEST, NORTHEAST}`; `EAST → {NORTHEAST, SOUTHEAST}`; `SOUTH → {SOUTHEAST, SOUTHWEST}`; `WEST → {SOUTHWEST, NORTHWEST}`.

`VASTU_TABLE` is the 8-key mapping above; lives in `vastu_kb.py` (PARTIAL tier baseline). FULL tier reads from the `vastu_engine` KB (B-099) and currently raises `NotImplementedError`.

### § 4.2 — Signal weighting + dominance derivation

(unchanged from v0.5)

```
weights_raw = {
    "sun":   1.0   if climate_zone in (COMPOSITE, TEMPERATE) else 0.7,
    "wind":  1.0   if climate_zone == WARM_HUMID            else 0.6,
    "vastu": {OFF: 0.0, PARTIAL: 0.4, FULL: 0.7}[vastu_tier],
}
weights_applied = renormalize_to_sum_one(weights_raw)
```

**Signal dominance derivation** (v0.5):

```
SIGNAL_DOMINANCE_THRESHOLD = 0.45

raw_total = sum(weights_raw.values())
if raw_total > 0:
    signal_dominance = max(weights_raw.values()) / raw_total
    if signal_dominance >= SIGNAL_DOMINANCE_THRESHOLD:
        dominant_signal = argmax_key(weights_raw)   # "sun" | "wind" | "vastu"
    else:
        dominant_signal = None                      # balanced — no signal dominates
else:
    # Edge case: all weights zero (e.g., OFF tier in climate that disables sun+wind?)
    # Should never happen in v1 valid inputs; defensive handling.
    signal_dominance = 0.0
    dominant_signal = None
```

**Interpretation guide for consumers**:

- `signal_dominance ≈ 0.33` (3 equal weights) → balanced; no single signal drives the orientation
- `signal_dominance ≈ 0.45-0.55` → moderate dominance; one signal carries more weight but others contribute meaningfully
- `signal_dominance ≈ 0.7+` → heavy dominance; one signal nearly determines the orientation
- `dominant_signal == "sun"` → sun path is the primary driver (composite/temperate climates with OFF tier)
- `dominant_signal == "wind"` → wind/cross-ventilation is the primary driver (warm-humid with OFF tier)
- `dominant_signal == "vastu"` → Vastu is the primary driver (FULL tier in mild climate zones)
- `dominant_signal == None` → balanced; the optimization integrates multiple signals roughly equally

### § 4.3 — Per-direction per-function score computation

(unchanged from v0.5)

```
function_scores[direction][f] = (
    sun_score(direction)         * sun_function_lookup(f)  * w_sun
  + wind_score(direction, clim)  * wind_function_lookup(f) * w_wind
  + vastu_score_4dir(direction, f, tier)                   * w_vastu
)
```

`sun_function_lookup`: LIVING=1.0, BEDROOM=0.7, KITCHEN=0.6, POOJA=0.8, WET_AREA=0.3, UTILITY=0.3
`wind_function_lookup`: LIVING=0.9, BEDROOM=1.0, KITCHEN=0.6, POOJA=0.5, WET_AREA=0.4, UTILITY=0.3

`function_scores` is `Mapping[FunctionRole, float]` — keyed only by the 6 `FunctionRole` members. `CIRCULATION` is a `ZoneBand`, not a `FunctionRole`, and is scored separately (§ 4.4 step 3).

### § 4.4 — Refining zone_bands — *v0.6 wording change in step 3*

(steps 1, 2, 4, 5 unchanged; step 3 wording clarified per Q2)

**Step 1**: enumerate all band → direction permutations (≤ 4! = 24 non-COURTYARD; ≤ 4^4 = 256 COURTYARD).

**Step 2**: prune by entry-on-road (PUBLIC must face plot.facing or secondary_road_direction on corner plots) + assert `len(surviving_perms) <= MAX_PERMUTATION_COUNT (= 256)` defense-in-depth.

**Step 3**: score every surviving permutation.

```
total_score(perm) = (
    Σ_(b ∈ functional_bands) function_scores[band_to_function[b]][perm[b]]
  + 0.5 × _circulation_score(perm[CIRCULATION])
)
```

`band_to_function`: `PUBLIC → LIVING`, `SERVICE → KITCHEN`, `PRIVATE → BEDROOM`. `CIRCULATION` is **not** mapped to a FunctionRole; it has its own private scoring helper (Q2 / § 14.20):

```python
# Private, internal to optimizer.py — NOT a key in DirectionPriorityScore.function_scores
def _circulation_score(direction: PlotOrientation) -> float:
    """Light circulation scoring per § 14.10 (CIRCULATION light scoring).

    Uses raw direction-baseline sun/wind scores (§ 4.1.1 / § 4.1.2),
    NOT the weighted blended function_scores.
    """
    return (
        0.3 * sun_score(direction)
      + 0.2 * wind_score(direction, climate_zone)
      + 0.5
    )
```

Intentionally lightweight: CIRCULATION's direction matters less than functional band placement. The 0.5 multiplier on the CIRCULATION term in `total_score` further damps its influence vs. functional bands. See § 14.10 (CIRCULATION light scoring) and § 14.20 (Q2 type-correctness clarification).

**Step 4**: apply hysteresis (`SWAP_HYSTERESIS_THRESHOLD = 0.10`) vs. C5 seed; tie-break with 5-tier `tie_break_key`:

1. -total_score
2. hamming_distance(perm, seed_perm)
3. -function_scores[LIVING][perm[PUBLIC]]
4. -function_scores[BEDROOM][perm[PRIVATE]]
5. lex_band_direction(perm)

**Step 5**: record `score_margin = best_score - second_best_score`.

### § 4.5 — Confidence (margin-clamped)

(unchanged from v0.5)

```
MIN_DENOM = 0.1
priority_confidence = clamp(
    (top_score - second_score) / max(top_score, MIN_DENOM),
    0.0, 1.0
)
```

### § 4.6 — Validator — *v0.6 adds invariant 9*

(invariants 1–8 unchanged from v0.5; invariant 9 new)

1. `direction_priorities` covers exactly NORTH, EAST, SOUTH, WEST (the four cardinal `PlotOrientation` members).
2. Every `function_scores` value in [0, 1].
3. `signal_breakdown.vastu_score == 0.0` iff `vastu_tier == OFF`.
4. Refined `zone_bands` keeps the C5-required band set.
5. For non-COURTYARD topologies, refined `zone_bands` has distinct directions.
6. Entry-on-road: entry-bearing band maps to a road-facing direction.
7. `seed_distance == hamming_distance(refined_zone_bands, seed_zone_bands)`.
8. `dominant_signal == None` iff `signal_dominance < SIGNAL_DOMINANCE_THRESHOLD`.
9. **NEW v0.6**: `refined_zone_bands` values are all in `{NORTH, EAST, SOUTH, WEST}` (no intercardinals; per the cardinal-only facing constraint of § 6).

---

## § 5 — Invocation contract (public)

(unchanged)

```python
oriented_candidates = prioritize_orientation(
    candidates=topology_candidates,
    plot_analysis=plot_analysis,
    vastu_tier=brief.vastu_preference.tier,
)
```

---

## § 6 — Failure modes — *v0.6 adds intercardinal-facing row*

| Condition | Behavior |
|---|---|
| `candidates` is empty tuple | Returns empty tuple |
| `candidates` is not a tuple | `TypeError` |
| `vastu_tier` is not a VastuTier instance | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066) |
| `plot_analysis.plot.facing not in {NORTH, EAST, SOUTH, WEST}` | **`NotImplementedError("intercardinal facing reserved; B-107. v1 supports cardinal facing only.")` — NEW v0.6 (Q1-B / § 14.19)** |
| Climate zone is HOT_DRY or COLD | `NotImplementedError` (B-098) |
| `vastu_tier == FULL` and `vastu_engine` KB absent | `NotImplementedError` (B-099) |
| All permutations pruned by entry-on-road | Falls back to C5 seed |
| `len(surviving_perms) > 256` | `AssertionError` (defense-in-depth) |

**Order-of-checks note**: intercardinal-facing check fires *before* climate / Vastu / permutation checks (it's an input-shape precondition; Pattern A avoidance — fail at the boundary, not deep in the pipeline).

---

## § 7 — Test plan

(unchanged from v0.5 + v0.6 additions for new failure mode)

Following C5's pattern. v0.6 targets ~125-145 tests (small growth from v0.5 for the 3 new tests below).

**Unchanged from v0.5** (signal_dominance, margin-clamped confidence, weights_raw, permutation cap assertion, etc.).

**v0.6 additions** (small):

- **Intercardinal facing rejection** (Q1-B / § 14.19): test that each of NORTHEAST, SOUTHEAST, SOUTHWEST, NORTHWEST as `plot.facing` raises `NotImplementedError` with the B-107 message. (~1 parametrized test, 4 cases.)
- **Cardinal facing happy path coverage**: confirm all four cardinals (NORTH, EAST, SOUTH, WEST) work end-to-end. (~1 parametrized test, 4 cases.)
- **Validator invariant 9**: refined_zone_bands values are all cardinal. (~1 test.)

`_circulation_score` private helper is exercised indirectly via every `total_score`-based test (no separate test target — it's an implementation detail).

---

## § 8 — KB references

(unchanged)

| KB | Status | Used for |
|---|---|---|
| Climate strategies | exists | sun/wind score baselines |
| Sun path | partial | east-morning / west-afternoon priors |
| `vastu_engine` | **stub** | FULL-tier 8-dir × N-function table; B-099 |

---

## § 9 — Out of scope — *v0.6 adds B-107 row*

| Item | Backlog ID |
|---|---|
| 8-dir external output | B-096 |
| Multi-floor per-floor orientation | B-097 |
| HOT_DRY / COLD climate zones | B-098 |
| `vastu_engine` KB for FULL | B-099 |
| Empirical recalibration | B-090 |
| Per-room finer priorities | B-095 |
| Building massing rotation | B-100 |
| Signal interaction terms | B-101 |
| Location-aware wind & continuous climate | B-102 |
| Dynamic hysteresis threshold | B-103 |
| Entropy-/variance-based confidence | B-104 |
| C6 ↔ C8 layout-feasibility feedback | B-105 |
| Secondary-road service-entry bonus (corner plots) | B-106 |
| **Intercardinal `plot.facing` support (extend C6 scoring to 8-dir externally) — NEW v0.6** | **B-107** |

---

## § 10 — Provenance

(unchanged from v0.5)

`OrientationProvenance` carries:

- `derived_at`, `plot_analysis_trace_id` — traceability
- `vastu_tier` — proves what tier was applied
- `weights_applied` — post-normalization
- `weights_raw` — pre-normalization (v0.4 § 14.16)
- `signal_dominance` — v0.5 — `max(weights_raw) / sum(weights_raw)`
- `dominant_signal` — v0.5 — string identifier of the dominant signal, or None when balanced
- `climate_profile`, `rule_trace` — debugging
- `permutation_search_size` — post-prune count
- `chosen_over_seed` — True if global optimum beat seed by hysteresis
- `seed_distance` — Hamming distance from seed

---

## § 11 — Spec metadata

- **Version**: v0.6 LOCKED
- **Status**: LOCKED at S31 (Ramalingam adjudication, mid-session). Pre-code patch round; not a critique walk. Build-ready — D-066 Step 6 in progress.
- **Lineage**: v0.1 DRAFT → v0.2 PROPOSED (walk #1) → v0.3 PROPOSED (walk #2) → v0.4 PROPOSED (walk #3) → v0.5 PROPOSED (walk #4) → v0.5 LOCKED (Ramalingam, S30 close) → v0.6 PROPOSED (S31 pre-code patch round) → **v0.6 LOCKED (Ramalingam, S31)**
- **Authoring session**: S31
- **Companion artifacts**: pre-code Q&A discussion (S31); recommendations document adjudicated by Ramalingam; one new B-NNN (B-107 in v0.6)

---

## § 12 — Backlog enumeration — *v0.6 adds B-107*

### Total: 17 items, all OUT-of-scope this build

| Source | Count | Items |
|---|---|---|
| Existing references | 6 | B-066, B-090, B-091, B-094, B-095, B-096 |
| C6 v0.1 | 4 | B-097, B-098, B-099, B-100 |
| C6 v0.2 walk | 5 | B-101, B-102, B-103, B-104, B-105 |
| C6 v0.3 walk | 0 | — |
| C6 v0.4 walk | 1 | B-106 |
| C6 v0.5 walk | 0 | — |
| **C6 v0.6 patch round (S31, pre-code)** | **1** | **B-107** |

### B-107 — full detail (per Rule 9 spec self-containment)

**ID**: B-107
**Description**: Intercardinal `plot.facing` support — extend C6 scoring to 8-direction externally.
**Origin**: C6 v0.6 § 14.19 (S31 pre-code Q&A round, Q1-B). Surfaced when pre-code spec/codebase cross-check found `domain/envelope.py:PlotOrientation` is 8-direction (not 4-direction as the v0.5 spec assumed) and C5's `default_zone_bands(facing)` produces intercardinal zone_bands when `plot.facing` is intercardinal.
**Status**: BACKLOG (deferred-but-non-blocking for v1).
**Trigger**: (a) ≥ 1 v1 production input has intercardinal `plot.facing`, OR (b) ≥ 5 user requests for diagonal-plot orientation support.
**S31-scope verdict**: OUT — v1 supports cardinal facing only. Intercardinal `plot.facing` raises `NotImplementedError` at C6's input boundary (§ 6). Mirrors B-066 (non-RECTANGULAR shape) and B-098 (HOT_DRY / COLD climate) pattern: defer-with-explicit-fail, not silent-coerce.
**Effort**: M (touches sun/wind score tables to add NE/SE/SW/NW rows, weighted-avg aggregation rule, Hamming distance over 8-dir keyspace, validator invariant 9, ~10-15 new tests, plus design dialogue on whether scoring tables interpolate or use independent intercardinal values).
**Related**: B-066 (non-RECTANGULAR shape — same defer-with-fail pattern), B-098 (HOT_DRY/COLD climate — same pattern), B-096 (8-dir external output — adjacent concern; C6's external output is currently 4-dir per v0.5 § 9).

---

## § 13 — Definitions — *v0.6 additions / removals*

(v0.1–v0.5 retained; v0.6 additions and one removal)

- **`signal_dominance`** *(v0.5)*: `max(weights_raw) / sum(weights_raw)`. Range `[0.33, 1.0]` with 3 signals. Indicates how much one signal drives the orientation choice.
- **`dominant_signal`** *(v0.5)*: string identifier (`"sun"`, `"wind"`, or `"vastu"`) of the heaviest raw weight when `signal_dominance >= SIGNAL_DOMINANCE_THRESHOLD`; otherwise `None`.
- **SIGNAL_DOMINANCE_THRESHOLD** *(v0.5)*: constant `= 0.45`. Below this, no signal is considered dominant.
- **`_circulation_score(direction)`** *(v0.6 NEW — Q2)*: private helper inside `optimizer.py`; returns `0.3 × sun_score(direction) + 0.2 × wind_score(direction, climate) + 0.5`. NOT a key in `DirectionPriorityScore.function_scores`. Naming convention (leading underscore) marks it as module-private; it is exercised indirectly through `total_score`.
- **`PlotDirection8`** *(REMOVED v0.6 — Q1-A)*: previously defined in v0.2–v0.5 § 3 as a duplicate 8-direction enum. Removed because `domain.envelope.PlotOrientation` already provides 8-direction values; the duplicate served no purpose.
- **Cardinal facings** *(v0.6 implicit)*: `{PlotOrientation.NORTH, PlotOrientation.EAST, PlotOrientation.SOUTH, PlotOrientation.WEST}`. C6 v1 supports only cardinal `plot.facing`; intercardinal raises NotImplementedError (B-107).

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 (S30 design)
§ 14.1 — Q1: Meaning B (functional priority per direction)
§ 14.2 — Q2: Vastu honors C1's three-tier contract
§ 14.3 — Q3: Cardinality preservation

### From v0.2 (walk #1)
§ 14.4 — 8-direction internal Vastu (refined v0.3 § 14.9; further refined v0.6 § 14.19)
§ 14.5 — Global permutation enumeration
§ 14.6 — Entry-on-road as pruner + validator (refined v0.3 § 14.14)
§ 14.7 — DINING split + composite_priority drop (DINING reversed v0.3 § 14.12)
§ 14.8 — FULL Vastu tier hard-fails (reaffirmed four times)

### From v0.3 (walk #2)
§ 14.9 — Weighted-avg 8→4 aggregation
§ 14.10 — CIRCULATION light scoring (formalized v0.6 § 14.20)
§ 14.11 — wind_function_lookup added
§ 14.12 — DINING REVERSAL
§ 14.13 — Tie-break hierarchy defined (5-tier)
§ 14.14 — road_score moved to provenance-only

### From v0.4 (walk #3)
§ 14.15 — Margin-clamped confidence
§ 14.16 — `weights_raw` exposure
§ 14.17 — Permutation cap assertion

### From v0.5 (walk #4)
§ 14.18 — `signal_dominance` + `dominant_signal` interpretability layer

### From v0.6 (S31 pre-code patch round — NEW)

#### § 14.19 — Drop `PlotDirection8` + cardinal-only v1 facing (Q1-A and Q1-B)

**Two related decisions resolved together since both stem from the same upstream observation**: `domain/envelope.py:PlotOrientation` is already 8-direction. The v0.5 spec was authored under a wrong premise that `PlotOrientation` was 4-direction (cardinal-only) and that an additional `PlotDirection8` enum was needed for internal Vastu computation. Pre-code grep at S31 start revealed the premise is false:

- `PlotOrientation` enum (`domain/envelope.py:14`) defines all 8 directions: NORTH, NORTHEAST, EAST, SOUTHEAST, SOUTH, SOUTHWEST, WEST, NORTHWEST.
- C1's `vastu_filter.py:49-51` uses `PlotOrientation.NORTHEAST` and `PlotOrientation.SOUTHWEST` in production logic.
- C1's `c01_brief_capture.py:915-918` maps all 8 string codes to enum members.
- C4's `compute_plot_facing_sides()` is "tested for all 8 PlotOrientation values" (`components/c04/schema.py:328`).
- C4 fixture `_c4_fixtures.py:36` uses `facing=PlotOrientation.NORTHEAST`.
- C5's `default_zone_bands(facing)` therefore produces intercardinal zone_bands when `plot.facing` is intercardinal (e.g., `{PUBLIC: NORTHEAST, SERVICE: SOUTHWEST, ...}`).

**Decision Q1-A — drop `PlotDirection8`**: pure mechanical simplification. `VASTU_TABLE` becomes `Mapping[PlotOrientation, Mapping[FunctionRole, float]]` keyed by all 8 PlotOrientation members. No conversion shim, no parallel enum. Zero behavior change.

**Decision Q1-B — cardinal-only v1 facing with explicit fail**: C6's scoring tables (§ 4.1.1 sun, § 4.1.2 wind), 4-dir Hamming distance, and the validator invariant "direction_priorities covers exactly N/E/S/W" all assume cardinal facings. Three resolution paths considered:

| Path | Action | Verdict |
|---|---|---|
| (a) | Cardinal-only v1; `NotImplementedError` on intercardinal facing; file B-107 | **CHOSEN** — minimal blast radius; matches B-066/B-098 pattern |
| (b) | Coerce intercardinal facing to nearest cardinal at C6 boundary | REJECTED — Pattern A (fix-as-bandage hides modeling gap); requires undocumented tiebreak rule |
| (c) | Extend C6 sun/wind/scoring tables to 8-dir externally | REJECTED — substantial design change; bigger than a patch round; deferred to B-107 |

Path (a) chosen for explicit fail-fast at the input boundary. The intercardinal facing case is a real product concern (some Indian plots are diagonal to the cardinal grid), but extending scoring to 8-dir is a design dialogue, not a patch — defers to B-107.

**Web research surface (Rule 7)**: not applicable to this AD. Both Q1-A and Q1-B are claims about *this codebase's existing types*, verified by code-grep, not external standards. No factual claim about Vastu, sun paths, or wind patterns is being made or revised.

#### § 14.20 — `CIRCULATION` as private pseudo-function helper (Q2)

v0.5 § 4.4 step 3 wrote `function_scores[CIRCULATION][direction] = 0.3×sun + 0.2×wind + 0.5`, treating `CIRCULATION` as if it were a `FunctionRole` key in `function_scores`. But `function_scores: Mapping[FunctionRole, float]` and `FunctionRole` (§ 3) does not include CIRCULATION — `CIRCULATION` is a `ZoneBand`, not a `FunctionRole`. The bracket notation was a type error in spec wording.

**Decision**: `CIRCULATION` scoring is a **private helper `_circulation_score(direction)`** inside `optimizer.py`, called only from the `total_score` formula. Public `DirectionPriorityScore.function_scores` stays clean, keyed exclusively by the 6 `FunctionRole` members.

**Why a private helper rather than synthetic enum extension**:

- CIRCULATION is conceptually a band, not a function; promoting it to FunctionRole would pollute the public contract.
- The scoring formula (`0.3 × raw_sun + 0.2 × raw_wind + 0.5`) is structurally different from the per-function blend (sun_function_lookup, wind_function_lookup, vastu) — it uses RAW direction baselines, not the per-function weighted blend. Forcing it into the same shape would obscure that.
- CIRCULATION scoring is consumed at exactly one call site (the `total_score` formula in step 3) — module-private scope is correct.

**No behavior change** from v0.5: the same numeric result is computed, just at a syntactically valid location. Tests that verified `total_score` in v0.5 remain valid; no test changes required.

**Web research surface (Rule 7)**: not applicable. Q2 is a type-correctness clarification about *this spec's own dataclasses*, not an external claim. The CIRCULATION light-scoring formula itself (0.3×sun + 0.2×wind + 0.5) is unchanged from v0.3 § 14.10; v0.6 only fixes the wording about *where* it lives in the type system.

### Pushback ledger (items the spec deliberately does NOT address)

(unchanged from v0.5; v0.6 patch round did not raise any pushback-eligible items)

| Item | Rounds raised | Reason for hold |
|---|---|---|
| Adjacency between bands | walks 1, 2, 4 | Adjacency is C9's job; band-level "minimal coupling" has no clean v1 formulation |
| Search-space < threshold fallback | walks 1, 2 | Math: minimum 6 permutations across all valid (topology, corner) combinations; trigger never fires |
| FULL graceful degradation | walks 1, 2, 3, 4 | Original walk asked for hard-fail; reversing now would re-open the contract gap |
| Signal interaction terms | walks 1, 2, 3, 4 | Pre-empirical; B-101 covers it |
| Dynamic hysteresis | walks 1, 2, 3, 4 | Pre-empirical; B-103 covers it |
| Tie-break "design inertia" | walks 2, 4 | Bias is bounded by hysteresis; intentional and explicit (§ 14.13) |
| Continuous climate weights | walks 1, 2 | C4 enrichment territory; B-102 |
| Aggregation distortion (post weighted-avg) | walks 2, 4 | v0.3 § 14.9 fix produces real gradient; remaining tuning is calibration (B-090) |
| CIRCULATION scoring constants | walks 3, 4 | Heuristic constants pre-empirical; calibration covered by B-090 family |
| Confidence distribution-awareness | walks 1, 2, 3, 4 | v0.4 § 14.15 fixed mean-based metric; entropy upgrade is B-104 |

---

## § 15 — Open questions for next round (or LOCK)

**Resolved by v0.6**: PlotDirection8 redundancy (§ 14.19); intercardinal-facing handling gap (§ 14.19, B-107); CIRCULATION type-correctness (§ 14.20).

**Carried forward (unchanged from v0.5)**:

1. **`OrientedCandidate` naming** — recommendation: keep
2. **Weighted-avg intercardinal weight** (0.5 vs 0.7) — calibration; B-090
3. **CIRCULATION scoring multiplier** — calibration; B-090
4. **`wind_function_lookup` values** — calibration; B-090
5. **Hamming distance normalization for L_SHAPE** — recommendation: leave raw integer
6. **`MIN_DENOM` choice** for confidence — calibration; B-090
7. **`SIGNAL_DOMINANCE_THRESHOLD`** *(0.45 default)* — calibration; B-090

All seven open questions are calibration values or naming preferences. **None are structural.** v0.6 closed three structural items (the only structural items remaining at v0.5 LOCK) in a single patch round.

---

## § 16 — End of v0.6 LOCKED

**Patch round summary**:

```
Type           : pre-code clarification (not a critique walk)
Driver         : pre-code spec/codebase cross-check at S31 start
Ramalingam Q&A : Q1-A, Q1-B, Q2 — all adjudicated before any line of code
Changes        : 3 discrete clarifications (Q1-A drop enum; Q1-B fail-fast +
                 B-107; Q2 CIRCULATION type fix)
New B-NNNs     : 1 (B-107)
New ADs        : 2 (§ 14.19, § 14.20)
Tests added    : ~3 (intercardinal rejection × 4; cardinal happy path × 4;
                 invariant 9 × 1 → ~9 cases across ~3 test functions)
Behavior change: zero (mechanical/type-correctness only; no scoring change)
Web research   : not required (no external-standards claims; Rule 7 surfaced
                 and cleared at start of patch round)
Status         : LOCKED (Ramalingam, S31).
```

**Convergence trajectory** (cumulative through v0.6):

```
                       amendments  new B-NNNs  pushback streak
v0.1 → v0.2               6           5           start
v0.2 → v0.3               6           0           still structural
v0.3 → v0.4               3           1           cycling begins (8 pushbacks)
v0.4 → v0.5               1           0           cycling deep (9 pushbacks;
                                                  5 items at 4-round raise)
v0.5 LOCKED (S30 close)
v0.5 → v0.6 (patch)       3           1           pre-code Q&A — no walk
```

The v0.6 patch round is procedurally distinct from v0.1–v0.5: it was driven by Claude's pre-code spec/codebase cross-check at the start of D-066 Step 6, not by an external critique reviewer. Three discrete defects surfaced; all three resolved with Ramalingam's adjudication; no design-space ambiguity in any of the three resolutions.

**Awaiting**: Ramalingam LOCK adjudication on v0.6. Upon LOCK → D-066 Step 6 (code build) per the 5-file split agreed in Q3 (`schema.py`, `signals.py`, `vastu_kb.py`, `optimizer.py`, `select.py` + `__init__.py`) with real-upstream test fixtures per Q4.
