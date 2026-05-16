# BuildemUp — C6 Orientation Priority — SPEC v0.5 PROPOSED

**Status**: PROPOSED. Not LOCKED. Awaits Ramalingam adjudication (LOCK or continue critique → v0.6).
**Component**: C6 of canonical 17-component v3 list (Track 3).
**Position in pipeline**: Era 2 layout. Consumes C4 + C5 + brief.vastu_tier; produces input for C8 corridor designer.
**Predecessor**: v0.4 PROPOSED.
**Lineage delta from v0.4**: one amendment applied per S30 critique walk #4 (item 9 — signal_dominance interpretability layer). Nine pushbacks held (items 1, 2, 3, 4, 5, 6, 7, 8, 10) — most are 3rd or 4th raises with no new evidence.

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

## § 3 — Output schema — *v0.5 changes*

**v0.5 changes**: `OrientationProvenance` gains two interpretability fields — `signal_dominance` (float) and `dominant_signal` (str | None) — per § 14.18.

```python
class FunctionRole(str, Enum):
    LIVING       = "living"
    BEDROOM      = "bedroom"
    KITCHEN      = "kitchen"
    POOJA        = "pooja"
    WET_AREA     = "wet_area"
    UTILITY      = "utility"

class PlotDirection8(str, Enum):
    """Internal 8-direction enum for Vastu computation only."""
    N  = "n"; NE = "ne"; E = "e"; SE = "se"
    S  = "s"; SW = "sw"; W = "w"; NW = "nw"

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
    signal_dominance:         float                  # NEW v0.5 — max(weights_raw) / sum(weights_raw);
                                                     # ≈ 0.33 = balanced; ≈ 1.0 = single signal dominates
    dominant_signal:          str | None             # NEW v0.5 — "sun" | "wind" | "vastu" | None
                                                     # None when signal_dominance < SIGNAL_DOMINANCE_THRESHOLD
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

---

## § 4 — Behavior

### § 4.1 — Per-direction baselines

(unchanged from v0.4)

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

**§ 4.1.4 — Vastu computation (8-direction internal, weighted-avg aggregation)**:

8-direction × 6-function Vastu table (PARTIAL tier baseline):

| Direction | living | bedroom | kitchen | pooja | wet_area | utility |
|-----------|--------|---------|---------|-------|----------|---------|
| N         | 0.85   | 0.6     | 0.3     | 0.7   | 0.4      | 0.5     |
| NE        | 0.9    | 0.5     | 0.1     | **1.0** | **0.0**  | 0.3     |
| E         | 0.85   | 0.7     | 0.5     | 0.85  | 0.3      | 0.5     |
| SE        | 0.55   | 0.4     | **1.0** | 0.3   | 0.4      | 0.5     |
| S         | 0.5    | 0.4     | 0.7     | 0.2   | 0.5      | 0.6     |
| SW        | 0.4    | **1.0** | 0.4     | 0.2   | 0.5      | 0.7     |
| W         | 0.5    | 0.7     | 0.6     | 0.3   | 0.7      | 0.85    |
| NW        | 0.55   | 0.6     | 0.7     | 0.3   | 0.7      | 0.9     |

**Weighted-average aggregation rule** (8-dir → 4-dir):

```
vastu_score_4dir[c][f] = (
    1.0 × vastu_8dir[c][f]                # cardinal, full weight
  + 0.5 × vastu_8dir[ccw_adjacent(c)][f]  # CCW intercardinal, half weight
  + 0.5 × vastu_8dir[cw_adjacent(c)][f]   # CW intercardinal, half weight
) / 2.0
```

Adjacency: `N → {NW, NE}`; `E → {NE, SE}`; `S → {SE, SW}`; `W → {SW, NW}`.

### § 4.2 — Signal weighting + dominance derivation

(weighting unchanged from v0.4 + dominance computation NEW)

```
weights_raw = {
    "sun":   1.0   if climate_zone in (COMPOSITE, TEMPERATE) else 0.7,
    "wind":  1.0   if climate_zone == WARM_HUMID            else 0.6,
    "vastu": {OFF: 0.0, PARTIAL: 0.4, FULL: 0.7}[vastu_tier],
}
weights_applied = renormalize_to_sum_one(weights_raw)
```

**v0.5 NEW — signal dominance derivation**:

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

(unchanged from v0.4)

```
function_scores[direction][f] = (
    sun_score(direction)         * sun_function_lookup(f)  * w_sun
  + wind_score(direction, clim)  * wind_function_lookup(f) * w_wind
  + vastu_score_4dir(direction, f, tier)                   * w_vastu
)
```

`sun_function_lookup`: LIVING=1.0, BEDROOM=0.7, KITCHEN=0.6, POOJA=0.8, WET_AREA=0.3, UTILITY=0.3
`wind_function_lookup`: LIVING=0.9, BEDROOM=1.0, KITCHEN=0.6, POOJA=0.5, WET_AREA=0.4, UTILITY=0.3

### § 4.4 — Refining zone_bands

(unchanged from v0.4)

**Step 1**: enumerate all band → direction permutations (≤ 4! = 24 non-COURTYARD; ≤ 4^4 = 256 COURTYARD).

**Step 2**: prune by entry-on-road (PUBLIC must face plot.facing or secondary_road_direction on corner plots) + assert `len(surviving_perms) <= MAX_PERMUTATION_COUNT (= 256)` defense-in-depth.

**Step 3**: score every surviving permutation.

```
total_score(perm) = (
    Σ_(b ∈ functional_bands) function_scores[band_to_function[b]][perm[b]]
  + 0.5 × function_scores[CIRCULATION][perm[CIRCULATION]]
)

function_scores[CIRCULATION][direction] = 0.3×sun + 0.2×wind + 0.5
```

**Step 4**: apply hysteresis (`SWAP_HYSTERESIS_THRESHOLD = 0.10`) vs. C5 seed; tie-break with 5-tier `tie_break_key`:

1. -total_score
2. hamming_distance(perm, seed_perm)
3. -function_scores[LIVING][perm[PUBLIC]]
4. -function_scores[BEDROOM][perm[PRIVATE]]
5. lex_band_direction(perm)

**Step 5**: record `score_margin = best_score - second_best_score`.

### § 4.5 — Confidence (margin-clamped)

(unchanged from v0.4)

```
MIN_DENOM = 0.1
priority_confidence = clamp(
    (top_score - second_score) / max(top_score, MIN_DENOM),
    0.0, 1.0
)
```

### § 4.6 — Validator

(unchanged from v0.4 + one v0.5 invariant)

1. `direction_priorities` covers exactly N, E, S, W.
2. Every `function_scores` value in [0, 1].
3. `signal_breakdown.vastu_score == 0.0` iff `vastu_tier == OFF`.
4. Refined `zone_bands` keeps the C5-required band set.
5. For non-COURTYARD topologies, refined `zone_bands` has distinct directions.
6. Entry-on-road: entry-bearing band maps to a road-facing direction.
7. `seed_distance == hamming_distance(refined_zone_bands, seed_zone_bands)`.
8. **NEW v0.5**: `dominant_signal == None` iff `signal_dominance < SIGNAL_DOMINANCE_THRESHOLD`. Sanity check on the derivation.

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

## § 6 — Failure modes

(unchanged from v0.4)

| Condition | Behavior |
|---|---|
| `candidates` is empty tuple | Returns empty tuple |
| `candidates` is not a tuple | `TypeError` |
| `vastu_tier` is not a VastuTier instance | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066) |
| Climate zone is HOT_DRY or COLD | `NotImplementedError` (B-098) |
| `vastu_tier == FULL` and `vastu_engine` KB absent | `NotImplementedError` (B-099) |
| All permutations pruned by entry-on-road | Falls back to C5 seed |
| `len(surviving_perms) > 256` | `AssertionError` (defense-in-depth) |

---

## § 7 — Test plan — *v0.5 updates*

Following C5's pattern. v0.5 targets ~120-140 tests (small growth from v0.4).

**Unchanged from v0.4** (margin-clamped confidence, weights_raw, permutation cap assertion, etc.).

**v0.5 additions**:

- **`signal_dominance` computation**:
  - OFF tier in COMPOSITE climate: `weights_raw = {sun: 1.0, wind: 0.6, vastu: 0.0}` → dominance = 1.0/1.6 = 0.625; `dominant_signal = "sun"`
  - OFF tier in WARM_HUMID: `weights_raw = {sun: 0.7, wind: 1.0, vastu: 0.0}` → dominance = 1.0/1.7 = 0.588; `dominant_signal = "wind"`
  - PARTIAL tier in TEMPERATE: `weights_raw = {sun: 1.0, wind: 0.6, vastu: 0.4}` → dominance = 1.0/2.0 = 0.500; `dominant_signal = "sun"`
  - FULL tier in WARM_HUMID: `weights_raw = {sun: 0.7, wind: 1.0, vastu: 0.7}` → dominance = 1.0/2.4 = 0.417; `dominant_signal = None` (balanced — below threshold 0.45)
- **`dominant_signal == None` invariant**: when no signal exceeds threshold, dominant is None (validator check 8)
- **Edge case zero weights**: defensive code path (all weights zero) returns `signal_dominance=0.0, dominant_signal=None` without raising

---

## § 8 — KB references

(unchanged)

| KB | Status | Used for |
|---|---|---|
| Climate strategies | exists | sun/wind score baselines |
| Sun path | partial | east-morning / west-afternoon priors |
| `vastu_engine` | **stub** | FULL-tier 8-dir × N-function table; B-099 |

---

## § 9 — Out of scope

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

---

## § 10 — Provenance — *v0.5 additions*

`OrientationProvenance` carries:

- `derived_at`, `plot_analysis_trace_id` — traceability
- `vastu_tier` — proves what tier was applied
- `weights_applied` — post-normalization
- `weights_raw` — pre-normalization (v0.4 § 14.16)
- **`signal_dominance`** — *v0.5 NEW* — `max(weights_raw) / sum(weights_raw)`; quantifies how much one signal drives the orientation
- **`dominant_signal`** — *v0.5 NEW* — string identifier of the dominant signal, or None when balanced
- `climate_profile`, `rule_trace` — debugging
- `permutation_search_size` — post-prune count
- `chosen_over_seed` — True if global optimum beat seed by hysteresis
- `seed_distance` — Hamming distance from seed

---

## § 11 — Spec metadata

- **Version**: v0.5 PROPOSED
- **Status**: PROPOSED. Pending Ramalingam adjudication (LOCK or → v0.6).
- **Lineage**: v0.1 DRAFT → v0.2 PROPOSED (walk #1) → v0.3 PROPOSED (walk #2) → v0.4 PROPOSED (walk #3) → v0.5 PROPOSED (walk #4)
- **Authoring session**: S30
- **Companion artifacts**: 4 critique-walk verdicts; 1 new B-NNN (B-106 in v0.4); zero new B-NNNs in v0.5

---

## § 12 — Backlog enumeration

(unchanged from v0.4 — no new B-NNNs filed in walk #4)

### Total: 16 items, all OUT-of-scope this build

| Source | Count | Items |
|---|---|---|
| Existing references | 6 | B-066, B-090, B-091, B-094, B-095, B-096 |
| C6 v0.1 | 4 | B-097, B-098, B-099, B-100 |
| C6 v0.2 walk | 5 | B-101, B-102, B-103, B-104, B-105 |
| C6 v0.3 walk | 0 | — |
| C6 v0.4 walk | 1 | B-106 |
| C6 v0.5 walk | 0 | — |

---

## § 13 — Definitions

(v0.1–v0.4 retained; v0.5 additions)

- **`signal_dominance`** *(v0.5)*: `max(weights_raw) / sum(weights_raw)`. Range `[0.33, 1.0]` with 3 signals. Indicates how much one signal drives the orientation choice.
- **`dominant_signal`** *(v0.5)*: string identifier (`"sun"`, `"wind"`, or `"vastu"`) of the heaviest raw weight when `signal_dominance >= SIGNAL_DOMINANCE_THRESHOLD`; otherwise `None`.
- **SIGNAL_DOMINANCE_THRESHOLD** *(v0.5)*: constant `= 0.45`. Below this, no signal is considered dominant (orientation is balanced across signals).

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 (S30 design)
§ 14.1 — Q1: Meaning B (functional priority per direction)
§ 14.2 — Q2: Vastu honors C1's three-tier contract
§ 14.3 — Q3: Cardinality preservation

### From v0.2 (walk #1)
§ 14.4 — 8-direction internal Vastu (refined v0.3 § 14.9)
§ 14.5 — Global permutation enumeration
§ 14.6 — Entry-on-road as pruner + validator (refined v0.3 § 14.14)
§ 14.7 — DINING split + composite_priority drop (DINING reversed v0.3 § 14.12)
§ 14.8 — FULL Vastu tier hard-fails (reaffirmed four times)

### From v0.3 (walk #2)
§ 14.9 — Weighted-avg 8→4 aggregation
§ 14.10 — CIRCULATION light scoring
§ 14.11 — wind_function_lookup added
§ 14.12 — DINING REVERSAL
§ 14.13 — Tie-break hierarchy defined (5-tier)
§ 14.14 — road_score moved to provenance-only

### From v0.4 (walk #3)
§ 14.15 — Margin-clamped confidence
§ 14.16 — `weights_raw` exposure
§ 14.17 — Permutation cap assertion

### From v0.5 (walk #4)

#### § 14.18 — `signal_dominance` + `dominant_signal` interpretability layer (item 9)

v0.4 exposed `weights_raw` (§ 14.16) for transparency, but the v0.4 walk reviewer correctly noted that raw values without a derived interpretation metric leave consumers needing to compute "which signal is driving this orientation?" themselves. v0.5 adds two derived fields to `OrientationProvenance`:

- `signal_dominance` — quantitative measure (`max(weights_raw) / sum(weights_raw)`)
- `dominant_signal` — qualitative label (`"sun"`, `"wind"`, `"vastu"`, or `None` when balanced)

Threshold `SIGNAL_DOMINANCE_THRESHOLD = 0.45` is chosen above the equal-weight baseline (0.33 for 3 signals) by a margin that requires meaningful imbalance before declaring a "dominant" signal. Below threshold, `dominant_signal == None` signals balanced orientation — useful for downstream consumers (UI, C8 corridor designer) reasoning about how to present or refine the result.

Pure additive change: no scoring modification, no behavioral impact, no contract change to the public function. Web research (MCDA literature) supports interpretability layers on raw weights as standard practice.

### Pushback ledger (items the spec deliberately does NOT address)

Updated through walk #4. Each held position has a documented rationale; reopening any of these requires **new evidence**, not restatement of the original objection.

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

Items raised 4 times across walks: **adjacency, FULL hard-fail, signal interactions, dynamic hysteresis, confidence distribution-awareness**. These are now strongly-held positions — further critique on these specific items without new evidence will continue to be held.

---

## § 15 — Open questions for v0.6 critique round (or LOCK)

**Resolved by v0.5**: signal interpretability (§ 14.18 — adds dominance metric).

**Carried forward (unchanged from v0.4)**:

1. **`OrientedCandidate` naming** — recommendation: keep
2. **Weighted-avg intercardinal weight** (0.5 vs 0.7) — calibration; B-090
3. **CIRCULATION scoring multiplier** — calibration; B-090
4. **`wind_function_lookup` values** — calibration; B-090
5. **Hamming distance normalization for L_SHAPE** — recommendation: leave raw integer
6. **`MIN_DENOM` choice** for confidence — calibration; B-090

**New from v0.5**:

7. **`SIGNAL_DOMINANCE_THRESHOLD`** *(0.45 default)* — calibration. Should it be lower (0.40, more sensitive to imbalance) or higher (0.50, more conservative about declaring dominance)? B-090 territory.

All seven open questions are calibration values or naming preferences. **None are structural.**

---

## § 16 — End of v0.5 PROPOSED

**Convergence trajectory** (cumulative):

```
                  amendments  new B-NNNs  pushback streak
v0.1 → v0.2          6           5           start
v0.2 → v0.3          6           0           still structural
v0.3 → v0.4          3           1           cycling begins (8 pushbacks)
v0.4 → v0.5          1           0           cycling deep (9 pushbacks; 5 items
                                              now at 4-round raise count)
                     ▼           ▼           ▲
              ↓ each round                  ↑
```

1 amendment. 0 new B-NNNs. Five items at 4-round raise count. 16 backlog items stable. 7 open questions, all calibration or naming.

The spec is at LOCK readiness pending Ramalingam adjudication. If walk #5 produces 0 amendments and continued cycling, that's the unambiguous LOCK signal. If walk #5 produces 1+ first-time amendments, those merit consideration.
