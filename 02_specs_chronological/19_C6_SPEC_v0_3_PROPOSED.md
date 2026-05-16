# BuildemUp — C6 Orientation Priority — SPEC v0.3 PROPOSED

**Status**: PROPOSED. Not LOCKED. Awaits Ramalingam adjudication (continue critique → v0.4, or LOCK).
**Component**: C6 of canonical 17-component v3 list (Track 3).
**Position in pipeline**: Era 2 layout. Consumes C4 + C5 + brief.vastu_tier; produces input for C8 corridor designer.
**Predecessor**: v0.2 PROPOSED.
**Lineage delta from v0.2**: six amendments applied per S30 critique walk verdicts (items 1, 3, 7, 8, 9, 10).
**Pushbacks honored from v0.2 walk**: items 2 (adjacency = C9), 4 (search-space math), 12 (FULL hard-fail retained).

---

## § 1 — Purpose

(unchanged)

C5 selects a topology *kind* and assigns a *default* `zone_bands` mapping that rigidly follows `plot.facing`. C6 reads four signals — sun, wind, road (hard constraint only), Vastu (opt-in) — computes per-direction functional priorities, and refines each C5 candidate's `zone_bands` via global permutation search, preserving input cardinality.

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

## § 3 — Output schema — *v0.3 changes*

**v0.3 changes**: (i) `FunctionRole.DINING` REMOVED (revert v0.2 § 14.7 per § 14.12); (ii) `SignalBreakdown.road_score` retained for provenance but no longer contributes to `function_scores` formula (§ 14.14).

```python
class FunctionRole(str, Enum):
    LIVING       = "living"        # public-band default; absorbs DINING bias (E-leaning)
    BEDROOM      = "bedroom"        # private-band default
    KITCHEN      = "kitchen"        # service-band primary; Vastu-preferred SE
    POOJA        = "pooja"          # service-band, Vastu NE-preferred
    WET_AREA     = "wet_area"       # toilet/bath; Vastu avoids NE
    UTILITY      = "utility"        # service-band, low priority
    # NOTE v0.3: DINING removed. Without its own band it added complexity
    # without decision power (§ 14.12). Tracked under B-095 for proper
    # band-level integration when FloorRoomBrief is enriched.

class PlotDirection8(str, Enum):
    """Internal 8-direction enum for Vastu computation only.
    Aggregated to 4-direction PlotOrientation via § 4.1.4 weighted-average rule."""
    N  = "n"
    NE = "ne"
    E  = "e"
    SE = "se"
    S  = "s"
    SW = "sw"
    W  = "w"
    NW = "nw"

@dataclass(frozen=True)
class SignalBreakdown:
    """Per-direction contribution from each signal.

    v0.3: road_score retained for provenance/inspection but does NOT
    contribute to function_scores formula (entry-on-road handled as hard
    constraint at § 4.4 step 2). § 14.14.
    """
    sun_score:    float   # [0, 1] — contributes to function_scores
    wind_score:   float   # [0, 1] — contributes to function_scores
    road_score:   float   # [0, 1] — provenance only; NOT in function_scores (v0.3)
    vastu_score:  float   # [0, 1] — contributes; == 0.0 iff vastu_tier == OFF

@dataclass(frozen=True)
class DirectionPriorityScore:
    """For one compass direction, per-function priority.

    No composite_priority (dropped in v0.2 § 14.7 per item 9 of v0.1 walk).
    """
    function_scores:  Mapping[FunctionRole, float]   # each [0, 1]
    signal_breakdown: SignalBreakdown

@dataclass(frozen=True)
class OrientationProvenance:
    derived_at:               float
    plot_analysis_trace_id:   str
    vastu_tier:               VastuTier
    weights_applied:          Mapping[str, float]   # post-renormalization;
                                                     # v0.3 has 3 keys (sun, wind,
                                                     # vastu) — no road
    climate_profile:          str
    rule_trace:               tuple[str, ...]
    permutation_search_size:  int
    chosen_over_seed:         bool
    seed_distance:            int                    # NEW v0.3 — Hamming distance
                                                     # of chosen permutation from
                                                     # C5 seed (tie-break diagnostic)

@dataclass(frozen=True)
class OrientationPriority:
    direction_priorities: Mapping[PlotOrientation, DirectionPriorityScore]
    refined_zone_bands:   Mapping[ZoneBand, PlotOrientation]
    priority_confidence:  float
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

**§ 4.1.1 — Sun-score table** (climate-conditional only via weight, not table):

| Direction | sun_score | comment                                               |
|-----------|-----------|-------------------------------------------------------|
| North     | 0.95      | Best — diffuse calm light, no harsh sun               |
| East      | 0.85      | Morning sun, cool by afternoon                        |
| South     | 0.55      | Strong summer sun, good winter sun                    |
| West      | 0.20      | Hot afternoon sun, hardest to shade                   |

**§ 4.1.2 — Wind-score table** (climate-zone-conditional):

| Direction | warm-humid | composite | temperate |
|-----------|------------|-----------|-----------|
| North     | 0.6        | 0.7       | 0.7       |
| East      | 0.7        | 0.6       | 0.7       |
| South     | 0.9        | 0.5       | 0.7       |
| West      | 0.85       | 0.5       | 0.7       |

**§ 4.1.3 — Road-score** *(v0.3 — provenance only)*:

```
road_score(direction, plot) = (
    1.0  if direction == plot.facing
    0.5  if direction == secondary_road_direction (corner plots only)
    0.0  otherwise
)
```

Computed and exposed in `SignalBreakdown` for inspection (so consumers can see "this direction is/isn't road-facing"). **Does NOT contribute to `function_scores`** — entry-on-road is enforced as hard constraint at § 4.4 step 2. Soft secondary-road preference for service entries on corner plots is deferred (would file B-106 if ever needed).

**§ 4.1.4 — Vastu computation (8-direction internal, 4-direction output)** — *v0.3 weighted-avg aggregation*

Vastu is computed in 8 directions internally and aggregated to 4-direction output via weighted average.

**8-direction × 6-function Vastu table (PARTIAL tier baseline)** — *v0.3 DINING column removed*:

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

LIVING column carries mild east-bias to absorb dining considerations (per § 14.12 — DINING-without-band reversal). E.living = 0.85 already reflects this; no further adjustment needed.

**Weighted-average aggregation rule (8-dir → 4-dir)** — *v0.3 replaces v0.2's max rule*:

For each cardinal direction `c ∈ {N, E, S, W}` and each function `f`:

```
vastu_score_4dir[c][f] = (
    1.0 × vastu_8dir[c][f]                # cardinal, full weight
  + 0.5 × vastu_8dir[ccw_adjacent(c)][f]  # CCW intercardinal, half weight
  + 0.5 × vastu_8dir[cw_adjacent(c)][f]   # CW intercardinal, half weight
) / 2.0                                    # weights sum to 2.0
```

Adjacency: `N → {NW, NE}`; `E → {NE, SE}`; `S → {SE, SW}`; `W → {SW, NW}`.

**Worked examples**:

*Kitchen (canonical SE)*:
- E_kitchen = (1.0×0.5 + 0.5×0.1 + 0.5×1.0) / 2.0 = **0.525**
- S_kitchen = (1.0×0.7 + 0.5×1.0 + 0.5×0.4) / 2.0 = **0.700**
- N_kitchen = (1.0×0.3 + 0.5×0.7 + 0.5×0.1) / 2.0 = **0.225**
- W_kitchen = (1.0×0.6 + 0.5×0.4 + 0.5×0.7) / 2.0 = **0.575**

S > W > E > N — faithful gradient: S is adjacency-closest to SE (the canonical kitchen direction), with E as second-best.

*Pooja (canonical NE)*:
- N_pooja = (1.0×0.7 + 0.5×0.3 + 0.5×1.0) / 2.0 = **0.675**
- E_pooja = (1.0×0.85 + 0.5×1.0 + 0.5×0.3) / 2.0 = **0.750**
- S_pooja = (1.0×0.2 + 0.5×0.3 + 0.5×0.2) / 2.0 = **0.225**
- W_pooja = (1.0×0.3 + 0.5×0.2 + 0.5×0.3) / 2.0 = **0.275**

E > N >> W > S — both E and N adjacency-touch NE; E wins because E.pooja_cardinal (0.85) > N.pooja_cardinal (0.7).

The weighted-avg rule preserves the 8-dir gradient while keeping output 4-direction-compatible. Replaces v0.2's max rule which produced ties whenever an intercardinal hit 1.0 (§ 14.9).

### § 4.2 — Signal weighting — *v0.3 changes*

**v0.3** — `road` weight removed; renormalize over 3 signals (sun, wind, vastu):

```
weights = {
    "sun":   1.0   if climate_zone in (COMPOSITE, TEMPERATE) else 0.7,
    "wind":  1.0   if climate_zone == WARM_HUMID            else 0.6,
    "vastu": {OFF: 0.0, PARTIAL: 0.4, FULL: 0.7}[vastu_tier],
}
weights = renormalize_to_sum_one(weights)
```

Renormalization preserves OFF/PARTIAL/FULL comparability.

### § 4.3 — Per-direction per-function score computation — *v0.3 changes*

**v0.3 changes**: (i) `road` term removed from formula; (ii) `wind_function_lookup` added symmetrically with `sun_function_lookup`.

```
function_scores[direction][f] = (
    sun_score(direction)         * sun_function_lookup(f)  * w_sun
  + wind_score(direction, clim)  * wind_function_lookup(f) * w_wind
  + vastu_score_4dir(direction, f, tier)                   * w_vastu
)
```

**`sun_function_lookup(f)`** — encodes which functions care about daylight:

| f | multiplier | rationale |
|---|---|---|
| LIVING   | 1.0 | wants natural daylight |
| BEDROOM  | 0.7 | wants morning sun, evening shade — moderate |
| KITCHEN  | 0.6 | some morning sun OK; mostly task lighting |
| POOJA    | 0.8 | auspicious east sun |
| WET_AREA | 0.3 | minimal; mostly task lighting |
| UTILITY  | 0.3 | minimal; mostly task lighting |

**`wind_function_lookup(f)`** — *v0.3 NEW* — encodes which functions benefit from natural cross-ventilation (web-supported; bedrooms and living are primary natural-ventilation beneficiaries; kitchens/wet-areas rely on mechanical exhaust):

| f | multiplier | rationale |
|---|---|---|
| LIVING   | 0.9 | comfort-priority natural ventilation |
| BEDROOM  | 1.0 | sleeping comfort, primary beneficiary |
| KITCHEN  | 0.6 | mechanical exhaust handles smoke/grease |
| POOJA    | 0.5 | gentle airflow OK |
| WET_AREA | 0.4 | exhaust fan is the real solution |
| UTILITY  | 0.3 | function-driven, not comfort-driven |

### § 4.4 — Refining zone_bands — *v0.3 step 3 + step 4 changes*

**Step 1 — generate candidate permutations** (unchanged from v0.2):

For the topology's required-bands set, enumerate all band → direction assignments:

- Non-COURTYARD (STRIP, CENTRAL_SPINE, L_SHAPE): distinct-direction constraint applies. Search space ≤ `4! = 24`.
- COURTYARD: distinct-direction relaxed. Search space ≤ `4^4 = 256`.

**Minimum search size** (verified analytically against entry-on-road prune): always ≥ 6 surviving permutations across all valid (topology, corner) combinations. The "no permutation survives" path (§ 6) covers the impossible edge as defense-in-depth.

**Step 2 — prune by hard constraints** (entry-on-road, unchanged from v0.2):

```
entry_bearing_band = ZoneBand.PUBLIC   # all four topology kinds
valid_entry_directions = (
    {plot.facing} ∪ ({secondary_road_direction} if corner_plot else ∅)
)
```

Drop permutations where `permutation[entry_bearing_band] ∉ valid_entry_directions`.

**Step 3 — score every surviving permutation** — *v0.3 includes CIRCULATION*:

```
total_score(perm) = (
    Σ_(b ∈ functional_bands) function_scores[band_to_function[b]][perm[b]]
  + 0.5 × function_scores[CIRCULATION][perm[CIRCULATION]]   # v0.3 NEW
)
```

`band_to_function`:
- PUBLIC      → LIVING
- SERVICE     → KITCHEN
- PRIVATE     → BEDROOM
- CIRCULATION → CIRCULATION (v0.3 NEW; treated as a pseudo-function)

`function_scores[CIRCULATION][direction]` — *v0.3 NEW* — light scoring that prefers no-west (heat avoidance) and mild airflow:

```
function_scores[CIRCULATION][direction] = (
    sun_score(direction)         * 0.3       # mild: avoid west heat
  + wind_score(direction, clim)  * 0.2       # mild: prefer some airflow
  + 0.5                                       # mild flat baseline
)
```

This contribution enters `total_score` with multiplier `× 0.5` to keep it secondary to the three functional bands. Net effect: when functional bands tie or are near-equal, CIRCULATION's preference for non-west tilts the choice. In typical cases the three functional bands dominate.

**Step 4 — apply hysteresis vs C5 seed + tie-break** — *v0.3 tie-break NEW*:

```
seed_perm  = C5_default_zone_bands(topology, plot.facing)
seed_score = total_score(seed_perm)

ranked_perms = sort(surviving_perms, key=tie_break_key, descending=True)
best_perm    = ranked_perms[0]
best_score   = total_score(best_perm)

if best_score - seed_score >= SWAP_HYSTERESIS_THRESHOLD (= 0.10):
    chosen_perm = best_perm
    chosen_over_seed = True
else:
    chosen_perm = seed_perm
    chosen_over_seed = False
```

**`tie_break_key(perm)` — v0.3 deterministic ordering**:

```
1. -total_score(perm)                              # primary: highest score
2.  hamming_distance(perm, seed_perm)              # secondary: closest to seed
3. -function_scores[LIVING][perm[PUBLIC]]          # tertiary: best living
4. -function_scores[BEDROOM][perm[PRIVATE]]        # quaternary: best bedroom
5.  lex_band_direction(perm)                       # final: deterministic
```

**`hamming_distance(perm_a, perm_b)`**: count of bands assigned to a different direction across the two permutations. Range: `0` (identical) to `|required_bands|` (all different). For L_SHAPE (3 bands), 0–3; for the other three topologies (4 bands), 0–4.

**`lex_band_direction(perm)`**: tuple of `(direction.value)` ordered by `ZoneBand` enum order, lexicographically compared. Pure deterministic fallback for full-tie cases (vanishingly rare in practice).

The chosen permutation's `seed_distance` is recorded in provenance.

**Step 5 — record `score_margin`**:

```
score_margin = best_score - second_best_score   # via tie_break_key ranking
```

If only one permutation survived pruning, `score_margin = best_score - 0.0`.

### § 4.5 — Confidence

(unchanged formula; applied at permutation level)

```
priority_confidence = (top_total - mean_total_of_others) / max(top_total, ε)
```

Open question for v0.4 (B-104): replace with entropy-based metric.

### § 4.6 — Validator (defense-in-depth)

(unchanged from v0.2 + one addition)

Construction-time validator checks:
1. `direction_priorities` covers exactly N, E, S, W.
2. Every `function_scores` value in [0, 1].
3. `signal_breakdown.vastu_score == 0.0` iff `vastu_tier == OFF`.
4. Refined `zone_bands` keeps the C5-required band set for the topology kind.
5. For non-COURTYARD topologies, refined `zone_bands` has distinct directions.
6. **Entry-on-road**: entry-bearing band maps to a road-facing direction (same predicate as § 4.4 step 2).
7. **NEW v0.3**: `seed_distance == hamming_distance(refined_zone_bands, seed_zone_bands)`. Sanity check that the recorded distance matches reality.

---

## § 5 — Invocation contract (public)

(unchanged)

```python
from buildemup.components.c06 import prioritize_orientation, VastuTier

oriented_candidates = prioritize_orientation(
    candidates=topology_candidates,
    plot_analysis=plot_analysis,
    vastu_tier=brief.vastu_preference.tier,
)
```

Returns `tuple[OrientedCandidate, ...]` of same length as `candidates`. Order preserved.

---

## § 6 — Failure modes

(unchanged from v0.2 — FULL hard-fail retained per v0.2 § 14.8 and v0.2-walk item 12 pushback)

| Condition                                          | Behavior                                                   |
|----------------------------------------------------|------------------------------------------------------------|
| `candidates` is empty tuple                        | Returns empty tuple                                        |
| `candidates` is not a tuple                        | `TypeError`                                                |
| `vastu_tier` is not a VastuTier instance           | `TypeError`                                                |
| `plot_analysis.shape != RECTANGULAR`               | `NotImplementedError("v1 supports rectangular only; B-066")` |
| Climate zone is HOT_DRY or COLD                    | `NotImplementedError("climate zone reserved; B-098")`      |
| `vastu_tier == FULL` and `vastu_engine` KB absent  | `NotImplementedError("FULL tier requires vastu_engine KB; B-099. Use PARTIAL.")` |
| All permutations pruned by entry-on-road           | Falls back to C5 seed (`chosen_over_seed=False`); never raises |

---

## § 7 — Test plan — *v0.3 updates*

Following C5's pattern. v0.3 targets ~110-130 tests (modest growth from v0.2).

**Unchanged from v0.2**: cardinality, ordering, OFF tier zero-vastu invariant, FULL hard-fail, climate behavior, frozen/immutability, perturbation stability.

**v0.3 additions**:

- **Weighted-avg aggregation** — Worked examples from § 4.1.4 codified as test cases. Kitchen scores: S=0.700 > W=0.575 > E=0.525 > N=0.225. Pooja scores: E=0.750 > N=0.675 > W=0.275 > S=0.225. Direct table assertions.
- **wind_function_lookup** — bedroom-on-windward-direction outscores utility-on-same-direction; kitchen scores moderately; explicit lookup-value table assertion.
- **CIRCULATION light scoring** — circulation never lands on West when other directions are available with comparable functional-band totals.
- **Tie-break determinism** — Hypothesis test: any two runs of `prioritize_orientation` on identical inputs produce identical outputs (no random tie-break flips).
- **Hamming distance recorded correctly** — `seed_distance` matches actual position-by-position difference.
- **DINING removal** — `FunctionRole.DINING` no longer exists; LIVING column carries dining bias (E.living = 0.85 > N.living = 0.7).
- **road_score in provenance, not in scoring** — verify SignalBreakdown.road_score is set; verify changing road_score (via mock) doesn't change function_scores.

---

## § 8 — KB references

(unchanged)

| KB                  | Status                              | Used for                                |
|---------------------|-------------------------------------|-----------------------------------------|
| Climate strategies  | exists                              | sun/wind score baselines                |
| Sun path            | partial                             | east-morning / west-afternoon priors    |
| `vastu_engine`      | **stub** — FULL tier blocked        | FULL-tier 8-dir × N-function table; B-099 |

---

## § 9 — Out of scope

| Item | Backlog ID | Status |
|---|---|---|
| 8-dir external output | **B-096** | Internally adopted (§ 4.1.4); external output deferred |
| Multi-floor per-floor orientation | **B-097** | OUT |
| HOT_DRY / COLD climate zones | **B-098** | OUT |
| `vastu_engine` KB for FULL | **B-099** | OUT (now hard-blocking — § 14.8) |
| Empirical recalibration | **B-090** | OUT (existing) |
| Per-room finer priorities | **B-095** | OUT (now also gates DINING band reintro per § 14.12) |
| Building massing rotation | **B-100** | OUT |
| Signal interaction terms | **B-101** | OUT (existing) |
| Location-aware wind & continuous climate | **B-102** | OUT (existing) |
| Dynamic hysteresis threshold | **B-103** | OUT (existing) |
| Entropy-/variance-based confidence | **B-104** | OUT (existing) |
| C6 ↔ C8 layout-feasibility feedback | **B-105** | OUT (existing) |

**No new B-NNN items filed in v0.3 walk** (items 5/6/11 already covered; items 2/4/12 misframed; item 8 reversal touches existing B-095).

---

## § 10 — Provenance

`OrientationProvenance` carries:

- `derived_at`, `plot_analysis_trace_id` — traceability
- `vastu_tier` — proves what tier was applied
- `weights_applied` — *v0.3* — three keys (sun, wind, vastu); no road
- `climate_profile`, `rule_trace` — debugging
- `permutation_search_size` — how many permutations survived pruning
- `chosen_over_seed` — True if global optimum beat C5 seed by hysteresis
- `seed_distance` — *v0.3 NEW* — Hamming distance of chosen permutation from seed (tie-break diagnostic)

---

## § 11 — Spec metadata

- **Version**: v0.3 PROPOSED
- **Status**: PROPOSED. Pending Ramalingam adjudication.
- **Lineage**: v0.1 DRAFT (S30) → v0.2 PROPOSED (S30 critique walk #1) → v0.3 PROPOSED (S30 critique walk #2)
- **Authoring session**: S30
- **Companion artifacts**: S30 critique-walk #2 verdicts; no new B-NNN items filed

---

## § 12 — Backlog enumeration

### Existing (referenced)

| ID | Description |
|---|---|
| B-066 | non-rectangular plot guardrail |
| B-090 | empirical recalibration |
| B-091 | climate-variant zone-band overrides |
| B-094 | orthogonalize width_fit vs aspect_ratio_fit |
| B-095 | FloorRoomBrief enrichment (now also gates DINING band reintro) |
| B-096 | Externally expose 8-dir output |

### From C6 v0.1

| ID | Description | Trigger |
|---|---|---|
| B-097 | Multi-floor per-floor orientation | When C9/C10 introduce multi-floor placement |
| B-098 | HOT_DRY and COLD climate zones | When a v1 city maps to either |
| B-099 | Populate `vastu_engine` KB | **NOW BLOCKING — FULL hard-fails until populated** |
| B-100 | Building massing rotation | When non-rectangular plots arrive |

### From C6 v0.2 walk

| ID | Description | Trigger |
|---|---|---|
| B-101 | Signal interaction terms (sun×wind etc.) | When B-090 yields ≥ 50 datapoints |
| B-102 | Location-aware wind & continuous climate | When B-090 reveals city-level variance > zone-level |
| B-103 | Dynamic hysteresis threshold | Post-B-090 |
| B-104 | Entropy-/variance-based confidence | When real-world feedback shows current metric misleads |
| B-105 | C6 ↔ C8 layout-feasibility feedback | After C8 ships |

### From C6 v0.3 walk

**None filed**. Items 2 and 4 misframed; items 5, 6, 11 already covered; item 12 pushback retained.

### Summary

| Total backlog items referenced | 6 + 4 + 5 + 0 = **15** |
| In scope this build            | 0 |
| Out of scope this build        | 15 |

---

## § 13 — Definitions

(v0.1/v0.2 definitions retained; v0.3 additions/changes below)

- **Weighted-avg 8→4 aggregation** *(v0.3)*: `vastu_score_4dir[c][f] = (1.0×c + 0.5×ccw_adj + 0.5×cw_adj) / 2.0`. Replaces v0.2's max rule. Preserves 8-dir gradient.
- **`sun_function_lookup`** / **`wind_function_lookup`** *(v0.3 wind new)*: per-function multipliers encoding which roles benefit from sun / wind (e.g., bedroom benefits more from cross-ventilation than utility).
- **CIRCULATION light scoring** *(v0.3)*: `function_scores[CIRCULATION][direction]` = `0.3×sun + 0.2×wind + 0.5`. Contributes to `total_score` with `× 0.5` weight (secondary to functional bands).
- **Hamming distance** *(v0.3)*: count of bands assigned to a different direction across two permutations; `0` (identical) to `|required_bands|`.
- **`tie_break_key`** *(v0.3)*: 5-tier deterministic ordering — total_score, then min Hamming distance to seed, then LIVING score, then BEDROOM score, then lexicographic.
- **`seed_distance`** *(v0.3)*: Hamming distance of the chosen permutation from C5 seed; recorded in provenance.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 (S30 design)

#### § 14.1 — Q1: Meaning B (functional priority per direction)
C6 = "what each compass direction is best for" engine. Building massing (Meaning A) → B-100.

#### § 14.2 — Q2: Vastu honors C1's three-tier contract
`VastuTier.{OFF, PARTIAL, FULL}`. OFF default. (See § 14.4 for 8-dir refinement, § 14.8 for FULL hard-fail.)

#### § 14.3 — Q3: Cardinality preservation
One `OrientedCandidate` per input `TopologyCandidate`. No fan-out.

### From v0.2 (S30 critique walk #1)

#### § 14.4 — 8-direction internal Vastu computation
Vastu's prescriptive content lives at intercardinals (NE pooja, SE kitchen, SW master bedroom). v0.2 adopts internal 8-dir; **v0.3 § 14.9 refines aggregation to weighted-avg**.

#### § 14.5 — Global permutation enumeration replaces greedy swap
≤ 24 permutations (non-COURTYARD), ≤ 256 (COURTYARD). Argmax with hysteresis vs C5 seed at global level.

#### § 14.6 — Entry-on-road as search-space pruner + validator
Pruned in § 4.4 step 2; validator (§ 4.6) defense-in-depth. **v0.3 § 14.14 makes road purely hard-constraint** (not in scoring formula).

#### § 14.7 — DINING split + composite_priority drop
**REVERSED in v0.3 § 14.12 (DINING)**; composite_priority drop retained.

#### § 14.8 — FULL Vastu tier hard-fails until B-099
Cleaner contract than graceful degradation. Mechanical pressure on B-099. **Reaffirmed in v0.3** against v0.2-walk item 12 pushback (no reversal).

### From v0.3 (S30 critique walk #2)

#### § 14.9 — Weighted-avg 8→4 aggregation replaces max (item 1)

v0.2's max rule produced ties whenever an intercardinal hit 1.0 (E_kitchen = S_kitchen = 1.0 when SE = 1.0), losing the cardinal-level gradient (S is closer to SE in the 8-dir table than E is). Weighted-avg with cardinal weight 1.0 and intercardinal weight 0.5 each preserves the gradient: S_kitchen = 0.700 > E_kitchen = 0.525. Faithful to Vastu, faithful to 8-dir signal, faithful to 4-dir output. Intercardinal weight 0.5 is starting heuristic — alternatives (0.7) deferred to empirical recalibration (B-090).

#### § 14.10 — CIRCULATION light scoring (item 3)

v0.2 had CIRCULATION getting "whatever's left" after the three functional bands grabbed the best directions, with no scoring contribution. Result: corridor could land in west heat zone — bad usability. v0.3 gives CIRCULATION a small scoring contribution (`0.3×sun + 0.2×wind + 0.5`) entering `total_score` with `× 0.5` weight. Functional bands still dominate; CIRCULATION's preference for non-west tilts the tie cases.

#### § 14.11 — wind_function_lookup added (item 7)

Web research (cross-ventilation literature) confirms bedrooms and living rooms are primary natural-ventilation beneficiaries; kitchens and wet-areas rely on mechanical exhaust. v0.3 adds `wind_function_lookup` symmetric with the existing `sun_function_lookup`. Resolves v0.2 § 15 Q2.

#### § 14.12 — DINING REVERSAL (item 8)

v0.2 § 14.7 added `FunctionRole.DINING` based on Indian residential context. Without its own band, DINING didn't contribute distinct decision power — it just modified LIVING's effective scores. v0.3 reverses: DINING removed from FunctionRole; LIVING column values absorb mild east bias (E.living = 0.85 already reflects this). True DINING separation tracked under existing **B-095** (FloorRoomBrief enrichment) — when bands grow to support a separate DINING band, reintroduce. This is a reversal of a v0.2 amendment; honest about that — Rule 7 walks are about getting the spec right, not protecting prior decisions.

#### § 14.13 — Tie-break hierarchy defined (item 9)

v0.2 § 15 Q5 left tie-break undefined → non-deterministic outputs possible. v0.3 defines 5-tier `tie_break_key`: (1) total_score, (2) min Hamming distance to seed, (3) max LIVING score, (4) max BEDROOM score, (5) lexicographic. Hamming-distance-from-seed as secondary key keeps small score differences close to C5's default — fewer surprises for users.

#### § 14.14 — road_score moved to provenance-only (item 10)

v0.2 had road simultaneously enforced as hard constraint (§ 4.4 step 2) and computed as soft signal (§ 4.3 formula) — dual-purpose confusion. v0.3 removes road from the scoring formula entirely; hard entry-on-road constraint remains. road_score still computed and exposed in `SignalBreakdown` for provenance/inspection. Soft service-entry-on-secondary-road preference deferred (would file B-106 if needed).

---

## § 15 — Open questions for v0.4 critique round

**Resolved by v0.3**: Q1 (8→4 aggregation), Q2 (wind function-independence), Q4 (DINING band — by removal), Q5 (permutation tie-break).

**Carried forward from v0.2**:

1. **`OrientedCandidate` naming** — sets the pattern for C7+. Alternatives: `LayoutCandidate`, `Stage2Candidate`. Worth resolving before LOCK because rename gets expensive once C7 spec references this type.

2. **Permutation search-size invariant** — should the spec mandate `assert len(surviving_perms) <= 256` as an explicit defense-in-depth check? Current: analytic bound is the limit; explicit assertion would catch implementation bugs.

**New from v0.3**:

3. **Weighted-avg intercardinal weight** — v0.3 uses `0.5` for both adjacent intercardinals. Alternative `0.7` would amplify intercardinal signal more (less differentiation between cardinals; more signal preservation). Calibrated empirically post-B-090.

4. **CIRCULATION scoring multiplier** — v0.3 uses `× 0.5` in `total_score` and a `0.3×sun + 0.2×wind + 0.5` baseline. Multiplier choice (0.3 / 0.5 / 0.7) determines how much CIRCULATION pushes against functional bands. Calibrated empirically.

5. **`wind_function_lookup` values** — exact multipliers (LIVING 0.9, BEDROOM 1.0, KITCHEN 0.6, …) are heuristic. B-090 will tune.

6. **Hamming distance variant for L_SHAPE** — L_SHAPE has 3 required bands, max distance 3. Other topologies have 4 bands, max distance 4. Should we normalize Hamming distance to [0,1] (divide by max) for cross-topology consistency? Currently raw integer; aware that tie-break across topologies isn't a real scenario (each candidate is processed independently) so normalization may be over-engineering.

---

## § 16 — End of v0.3 PROPOSED

Convergence signal: 6 amendments, 0 new B-NNN items, 1 reversal (DINING). All "critical before LOCK" items from v0.2 walk addressed. Ready for v0.4 critique round or LOCK.
