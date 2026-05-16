# BuildemUp — C6 Orientation Priority — SPEC v0.2 PROPOSED

**Status**: PROPOSED. Not LOCKED. Awaits Ramalingam adjudication (continue critique → v0.3, or LOCK).
**Component**: C6 of canonical 17-component v3 list (Track 3).
**Position in pipeline**: Era 2 layout. Consumes C4 + C5 + brief.vastu_tier; produces input for C8 corridor designer.
**Predecessor**: v0.1 DRAFT (S30, post-C5 v1.0 SHIP).
**Lineage delta from v0.1**: six amendments applied per S30 critique walk verdicts (items 3, 5, 6, 7, 9, 10).

---

## § 1 — Purpose

(unchanged from v0.1)

C5 selects a topology *kind* and assigns a *default* `zone_bands` mapping that rigidly follows `plot.facing`. That default is correct as a placeholder, but it ignores three signals that materially affect liveability:

1. **Sun path** — west exposure is hot, east is cool morning, north is calm light, south is heavy summer sun.
2. **Wind direction** — warm-humid wants windward openings for cross-ventilation; composite wants the opposite.
3. **Vastu** — culturally significant for a meaningful fraction of Indian buyers; opt-in via C1's locked `VastuTier.{OFF, PARTIAL, FULL}`.

A fourth signal — **road relationship** — is implicit in C5's default and continues to be honored *as a hard constraint for the entry-bearing band* (refined in v0.2 § 4.4 / § 4.6).

C6 reads these signals, computes a *per-direction functional priority*, and uses it to refine each C5 candidate's `zone_bands` via global permutation search while preserving the input cardinality.

**Out of scope for C6**: building massing rotation, room sizing, room placement, corridor geometry. C6 only refines *which compass direction gets which functional band*.

---

## § 2 — Input contract

(unchanged from v0.1)

```python
def prioritize_orientation(
    candidates: tuple[TopologyCandidate, ...],   # 1-3 from C5
    plot_analysis: PlotAnalysis,                  # from C4
    vastu_tier: VastuTier = VastuTier.OFF,        # from C1.brief
) -> tuple[OrientedCandidate, ...]:
```

Cardinality preserved (1-3 in → 1-3 out, position-paired).

---

## § 3 — Output schema

**v0.2 changes**: (i) added `FunctionRole.DINING`; (ii) dropped `composite_priority` from `DirectionPriorityScore`.

```python
class FunctionRole(str, Enum):
    LIVING       = "living"        # public-band default
    DINING       = "dining"        # NEW v0.2 — Indian dining is often distinct,
                                    # Vastu-preferred east/south. § 14.7
    BEDROOM      = "bedroom"        # private-band default
    KITCHEN      = "kitchen"        # service-band primary; Vastu-preferred SE
    POOJA        = "pooja"          # service-band, Vastu NE-preferred
    WET_AREA     = "wet_area"       # toilet/bath; Vastu avoids NE
    UTILITY      = "utility"        # service-band, low priority

class PlotDirection8(str, Enum):
    """v0.2 — 8-direction internal enum for Vastu computation only.
    NOT exposed in output; aggregated to 4-direction PlotOrientation
    via § 4.1.4 max-over-adjacent rule. § 14.4."""
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
    """Per-direction contribution from each of the four signals."""
    sun_score:    float        # [0, 1]
    wind_score:   float        # [0, 1]
    road_score:   float        # [0, 1]
    vastu_score:  float        # [0, 1]; == 0.0 iff vastu_tier == OFF (validator)

@dataclass(frozen=True)
class DirectionPriorityScore:
    """For one compass direction (4-direction output), per-function priority.

    Higher = better-suited for that function on this direction.
    NO composite_priority (dropped in v0.2 § 14.7 — see item 9 of v0.1 walk).
    Consumers compute their own weighted aggregate as needed.
    """
    function_scores:  Mapping[FunctionRole, float]   # each [0, 1]
    signal_breakdown: SignalBreakdown

@dataclass(frozen=True)
class OrientationProvenance:
    derived_at:               float
    plot_analysis_trace_id:   str
    vastu_tier:               VastuTier
    weights_applied:          Mapping[str, float]
    climate_profile:          str
    rule_trace:               tuple[str, ...]
    permutation_search_size:  int                       # NEW v0.2 — how many
                                                        # permutations were
                                                        # considered (§ 4.4)
    chosen_over_seed:         bool                      # NEW v0.2 — True if
                                                        # global optimum beat
                                                        # C5 seed by hysteresis;
                                                        # False if seed was kept

@dataclass(frozen=True)
class OrientationPriority:
    direction_priorities: Mapping[PlotOrientation, DirectionPriorityScore]
    refined_zone_bands:   Mapping[ZoneBand, PlotOrientation]
    priority_confidence:  float                          # 0..1
    score_margin:         float                          # gap to runner-up
                                                          # permutation overall
                                                          # (v0.2 redefinition —
                                                          # was per-band)
    provenance:           OrientationProvenance

@dataclass(frozen=True)
class OrientedCandidate:
    topology_candidate: TopologyCandidate
    orientation:        OrientationPriority
```

`score_margin` redefinition (v0.2): now the gap between the chosen permutation's total score and the runner-up permutation's total score. Earlier v0.1 reading was per-band; the global-permutation reform makes a global margin more meaningful and simpler to reason about.

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

(HOT_DRY and COLD reserved per B-098.)

**§ 4.1.3 — Road-score**: `1.0` for `plot.facing` direction; `0.5` for the secondary road direction on corner plots; `0.0` otherwise. v0.2 — entry-on-road is now also a hard search-space constraint (§ 4.4); the score is used only for non-entry bands' soft preference (corner plots may want service-entry on the second road).

**§ 4.1.4 — Vastu computation (8-direction internal, 4-direction output)** — *v0.2 new*

Vastu rules are intrinsically 8-direction. Reducing them to 4 cardinals loses the most prescriptive content (NE pooja / SE kitchen / SW master bedroom). v0.2 computes Vastu in 8-direction internally and aggregates to 4-direction for the output schema.

**8-direction × 7-function Vastu table (PARTIAL tier baseline):**

| Direction | living | dining | bedroom | kitchen | pooja | wet_area | utility |
|-----------|--------|--------|---------|---------|-------|----------|---------|
| N         | 0.85   | 0.7    | 0.6     | 0.3     | 0.7   | 0.4      | 0.5     |
| NE        | 0.9    | 0.7    | 0.5     | 0.1     | **1.0** | **0.0**  | 0.3     |
| E         | 0.85   | 0.9    | 0.7     | 0.5     | 0.85  | 0.3      | 0.5     |
| SE        | 0.55   | 0.7    | 0.4     | **1.0** | 0.3   | 0.4      | 0.5     |
| S         | 0.5    | 0.6    | 0.4     | 0.7     | 0.2   | 0.5      | 0.6     |
| SW        | 0.4    | 0.4    | **1.0** | 0.4     | 0.2   | 0.5      | 0.7     |
| W         | 0.5    | 0.5    | 0.7     | 0.6     | 0.3   | 0.7      | 0.85    |
| NW        | 0.55   | 0.45   | 0.6     | 0.7     | 0.3   | 0.7      | 0.9     |

Bolded cells are the canonical Vastu prescriptions: NE pooja, SE kitchen, SW master bedroom, NE-avoid for wet areas. Values are PARTIAL-tier weights; FULL tier (post-B-099) replaces this table from `vastu_engine`.

**Aggregation rule (8-dir → 4-dir output)**:

For each cardinal direction `c ∈ {N, E, S, W}` and each function `f`:

```
vastu_score_4dir[c][f] = max(
    vastu_score_8dir[c][f],            # the cardinal itself
    vastu_score_8dir[ccw_adjacent][f], # the intercardinal CCW of c
    vastu_score_8dir[cw_adjacent][f],  # the intercardinal CW of c
)
```

Adjacency: `N → {NW, NE}`; `E → {NE, SE}`; `S → {SE, SW}`; `W → {SW, NW}`.

**Worked example**: kitchen on East = max(E.kitchen=0.5, NE.kitchen=0.1, SE.kitchen=1.0) = **1.0**. Kitchen on South = max(S.kitchen=0.7, SE.kitchen=1.0, SW.kitchen=0.4) = **1.0**. Both East and South pick up SE's full score — the optimizer then chooses between them on sun/wind/road signals. This is faithful to Vastu (SE is best, E and S are co-equal accommodations of SE).

The aggregation rule is conservative — it never invents Vastu signal where none exists, and it never under-credits a cardinal that adjacency-touches a strong intercardinal.

### § 4.2 — Signal weighting

```
weights = {
    "sun":   1.0   if climate_zone in (COMPOSITE, TEMPERATE) else 0.7,
    "wind":  1.0   if climate_zone == WARM_HUMID            else 0.6,
    "road":  0.5,
    "vastu": {OFF: 0.0, PARTIAL: 0.4, FULL: 0.7}[vastu_tier],
}
weights = renormalize_to_sum_one(weights)
```

(unchanged from v0.1; renormalization ensures direct OFF/PARTIAL/FULL comparability.)

### § 4.3 — Per-direction per-function score computation

```
function_scores[f] = (
    sun_score(direction)   * sun_function_lookup(f)   * w_sun
  + wind_score(direction, climate)                    * w_wind
  + road_score(direction, plot.facing)                * w_road
  + vastu_score_4dir(direction, f, tier)              * w_vastu
)
```

`vastu_score_4dir` is the 8→4 aggregated value per § 4.1.4. Wind continues to NOT multiply by function lookup in v0.2 — open question for v0.3 (§ 15 Q1).

### § 4.4 — Refining zone_bands — *v0.2 reformed*

**v0.1 used pairwise greedy swap. v0.2 uses bounded global enumeration.**

**Step 1 — generate candidate permutations**:

For the topology's required-bands set (per C5 § 14.5 / C6 § 4.6), enumerate all assignments of bands → directions:

- Non-COURTYARD topologies (STRIP, CENTRAL_SPINE, L_SHAPE): distinct-direction constraint applies. Search space = `P(4, |required_bands|)` = at most `4! = 24` permutations.
- COURTYARD: distinct-direction constraint relaxed (CIRCULATION wraps the open core). Search space = `4^|required_bands|` = at most `4^4 = 256` assignments.

**Step 2 — prune by hard constraints** (entry-on-road):

For each candidate permutation, **drop it if** the entry-bearing band does not map to a road-facing direction:

```
entry_bearing_band = {
    STRIP:         ZoneBand.PUBLIC,
    CENTRAL_SPINE: ZoneBand.PUBLIC,
    L_SHAPE:       ZoneBand.PUBLIC,   # front arm
    COURTYARD:     ZoneBand.PUBLIC,
}[topology.kind]

valid_entry_directions = {plot.facing} ∪ ({secondary_road_direction} if corner_plot else ∅)
```

Permutations where `permutation[entry_bearing_band] ∉ valid_entry_directions` are dropped *before scoring*. This is what v0.1 § 4.6 validator caught post-hoc; v0.2 prunes pre-hoc (Pattern B avoidance — feasibility as search-space pruner, not post-hoc rejector).

**Step 3 — score every surviving permutation**:

```
total_score(perm) = Σ_band function_scores[band_to_function[band]][perm[band]]
```

`band_to_function`:
- PUBLIC      → LIVING   (per § 14.7: dining co-located with living in v1)
- SERVICE     → KITCHEN
- CIRCULATION → none (excluded from total_score; circulation has no functional preference)
- PRIVATE     → BEDROOM

**Step 4 — apply hysteresis vs. C5 seed**:

```
seed_perm = C5_default_zone_bands(topology, plot.facing)
seed_score = total_score(seed_perm)
best_perm  = argmax_total_score(surviving_perms)
best_score = total_score(best_perm)

if best_score - seed_score >= SWAP_HYSTERESIS_THRESHOLD (= 0.10):
    use best_perm
    chosen_over_seed = True
else:
    use seed_perm
    chosen_over_seed = False
```

This makes the hysteresis a **single global comparison**, not a per-band one. It also avoids flip-flopping on plots where the global optimum is a near-tie with C5's default.

**Step 5 — record `score_margin`**:

```
score_margin = best_score - second_best_score   # among surviving perms
```

(If only one permutation survives the pruning, `score_margin = best_score - 0.0`.)

### § 4.5 — Confidence

```
priority_confidence = (top_total - mean_total_of_others) / max(top_total, ε)
```

(unchanged math from v0.1, but now applied at *permutation level* rather than per-band — cleaner with the global-enumeration reform.)

When all surviving permutations score similarly (square plot, temperate climate, OFF tier), `priority_confidence` is low. Open question for v0.3: replace with entropy- or variance-based metric (B-104 territory).

### § 4.6 — Validator (defense-in-depth)

The construction-time validator stays as defense-in-depth even though § 4.4 step 2 prunes infeasibles. Validator checks:

1. `direction_priorities` covers exactly N, E, S, W (4 keys).
2. Every `function_scores` value in [0, 1].
3. `signal_breakdown.vastu_score == 0.0` iff `vastu_tier == OFF`.
4. Refined `zone_bands` keeps the C5-required band set for the topology kind.
5. For non-COURTYARD topologies, refined `zone_bands` has distinct directions.
6. **Entry-on-road**: the entry-bearing band maps to a road-facing direction. *(Same predicate as § 4.4 step 2; redundant by design. If § 4.4 enumeration is correct, this never fires; if a future refactor breaks the pruner, the validator catches it. Pattern A safeguard.)*

---

## § 5 — Invocation contract (public)

(unchanged from v0.1)

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

## § 6 — Failure modes — *v0.2 changes*

| Condition                                          | Behavior                                                   |
|----------------------------------------------------|------------------------------------------------------------|
| `candidates` is empty tuple                        | Returns empty tuple (no-op, no raise)                      |
| `candidates` is not a tuple                        | `TypeError`                                                |
| `vastu_tier` is not a VastuTier instance           | `TypeError`                                                |
| `plot_analysis.shape != RECTANGULAR`               | `NotImplementedError("v1 supports rectangular only; B-066")` |
| Climate zone is HOT_DRY or COLD                    | `NotImplementedError("climate zone reserved; B-098")`      |
| **`vastu_tier == FULL` and `vastu_engine` KB absent** | **`NotImplementedError("FULL tier requires vastu_engine KB; B-099. Use PARTIAL.")` *(v0.2 — was graceful degradation in v0.1; § 14.8)*** |
| All permutations pruned by entry-on-road           | Falls back to C5 seed (and `chosen_over_seed=False` in provenance); never raises |

**Why FULL is now hard-fail**: graceful degradation hid the gap between contract and behavior — users got PARTIAL with elevated weight while believing they had FULL semantics. v0.2 fails fast, which (a) is honest, (b) creates implementation pressure to actually populate the KB, (c) keeps the v1 surface clean.

---

## § 7 — Test plan — *v0.2 updates*

Following C5's pattern. v0.2 updates target ~100-120 tests (up from v0.1's ~80-100 because of new permutation enumeration + 8-dir Vastu + DINING coverage).

**Cardinality / ordering**: N candidates in → N OrientedCandidates out, same order.

**Per-tier Vastu behavior**:
- OFF → `vastu_score == 0.0` for every direction; identical output regardless of brief
- PARTIAL → 8-dir → 4-dir aggregation works correctly: kitchen on East and kitchen on South both get SE-aggregated score 1.0; pooja on North and East both get NE-aggregated score 1.0; SW master bedroom is reflected
- FULL → raises `NotImplementedError` until B-099 KB exists *(v0.2 contract test)*

**Permutation-search behavior** *(new in v0.2)*:
- Non-COURTYARD topologies enumerate ≤ 24 permutations
- COURTYARD enumerates ≤ 256 assignments
- All entry-on-road-violating permutations pruned before scoring (provenance.permutation_search_size reflects post-prune count)
- Hysteresis: global advantage < 0.10 → seed kept, `chosen_over_seed=False`
- Hysteresis: global advantage ≥ 0.10 → best applied, `chosen_over_seed=True`

**Climate behavior**:
- WARM_HUMID — wind weight dominates, south-southwest preferred for living
- COMPOSITE — sun weight dominates, north preferred for living

**DINING placement** *(new in v0.2)*: at PARTIAL Vastu tier, DINING gets East-preferred score (0.9 cardinal + adjacency). When LIVING is on North (winning sun), DINING co-locates per band_to_function (no separate band yet — see § 14.7).

**Frozen / immutability**: every dataclass frozen; every Mapping is MappingProxyType.

**Stability** (Hypothesis): perturbing direction by ±1 cardinal step (N→E) cycles direction priorities consistently.

**Failure modes**: each row of § 6 covered, including new FULL hard-fail path.

---

## § 8 — KB references

(unchanged from v0.1; FULL tier now blocked until KB exists.)

| KB                  | Status       | Used for                                        |
|---------------------|--------------|-------------------------------------------------|
| Climate strategies  | exists       | sun/wind score baselines per zone               |
| Sun path            | partial      | east-morning / west-afternoon priors            |
| `vastu_engine`      | **stub** — FULL tier blocked | FULL-tier 8-dir × N-function table; B-099 |

---

## § 9 — Out of scope

(updated for v0.2 — B-096 demoted to internal-adopted)

- ~~8-direction granularity~~ → **internally adopted in v0.2 § 4.1.4**; the public output surface remains 4-dir per `PlotOrientation`. **B-096 retained** for "expose 8-dir externally" if downstream consumers ever ask.
- Multi-floor per-floor orientation → **B-097**
- HOT_DRY and COLD climate zones → **B-098**
- `vastu_engine` KB population for FULL tier → **B-099** (now hard-blocking — v0.2 § 14.8)
- Empirical recalibration of weights → **B-090**
- Per-room finer-grain priorities → **B-095**
- Building massing rotation (Meaning A) → **B-100**
- Signal interaction terms (sun×wind etc.) → **B-101** *(new from S30 walk)*
- Location-aware wind & continuous climate scaling → **B-102** *(new)*
- Dynamic hysteresis threshold → **B-103** *(new)*
- Entropy-/variance-based confidence metric → **B-104** *(new)*
- C6 ↔ C8 layout-feasibility feedback loop → **B-105** *(new)*

---

## § 10 — Provenance — *v0.2 additions*

`OrientationProvenance` now carries:

- `derived_at` — pulled from `plot_analysis.provenance.derived_at`
- `plot_analysis_trace_id`
- `vastu_tier`
- `weights_applied` — final post-renormalization
- `climate_profile`
- `rule_trace`
- `permutation_search_size` — *v0.2 new*: how many permutations survived the entry-on-road prune (debug aid; verifies the search ran)
- `chosen_over_seed` — *v0.2 new*: True if global optimum beat C5 seed by hysteresis; False if seed kept

The two new fields make § 4.4's behavior introspectable without reading code.

---

## § 11 — Spec metadata

- **Version**: v0.2 PROPOSED
- **Status**: PROPOSED. Pending Ramalingam adjudication.
- **Lineage**: v0.1 DRAFT (S30) → v0.2 PROPOSED (S30 critique walk; six amendments)
- **Authoring session**: S30
- **Companion artifacts**: S30 critique-walk verdicts (chat); five new B-NNN backlog items filed (§ 12)

---

## § 12 — Backlog enumeration (per Rule 9 / Rule 9.2)

### Items spec depends on (existing — referenced not introduced)

| ID    | Description                                                |
|-------|------------------------------------------------------------|
| B-066 | non-rectangular plot guardrail                             |
| B-090 | empirical recalibration                                    |
| B-091 | climate-variant zone-band overrides                        |
| B-094 | orthogonalize width_fit vs aspect_ratio_fit                |
| B-095 | FloorRoomBrief enrichment                                  |
| B-096 | Externally expose 8-dir output (v0.2 demoted scope)        |

### Items NEW in C6 v0.1 (retained)

| ID    | Description                                                                              | Trigger                                                     | Effort |
|-------|------------------------------------------------------------------------------------------|-------------------------------------------------------------|--------|
| B-097 | Multi-floor per-floor orientation                                                        | When C9/C10 introduce multi-floor placement                 | L      |
| B-098 | HOT_DRY and COLD climate zones                                                           | When a v1 city maps to either                               | S      |
| B-099 | Populate `vastu_engine` KB for FULL tier                                                 | **NOW BLOCKING — FULL hard-fails until populated (§ 14.8)** | M      |
| B-100 | Building massing rotation engine                                                         | When non-rectangular plots arrive (also gated by B-066)     | L      |

### Items NEW in C6 v0.2 (from critique walk; per Rule 9.2 — filed without permission)

| ID    | Description                                                                              | Trigger                                                     | S30-scope verdict | Effort |
|-------|------------------------------------------------------------------------------------------|-------------------------------------------------------------|--------------------|--------|
| B-101 | Signal interaction terms (sun×wind, vastu×road) replacing pure linear blend              | When B-090 yields ≥ 50 datapoints; check fit residuals      | OUT (empirical)    | M      |
| B-102 | Location-aware wind & continuous climate scaling — extend C4 PlotAnalysis                | When B-090 reveals city-level variance > zone-level         | OUT (C4 territory) | L      |
| B-103 | Dynamic hysteresis threshold = f(confidence, aspect_ratio, climate_strength)             | Post-B-090; same gate as B-101                              | OUT (empirical)    | S      |
| B-104 | Entropy- or variance-based confidence metric                                             | When real-world feedback shows current metric misleads      | OUT (v1.x)         | S      |
| B-105 | C6 ↔ C8 layout-feasibility feedback loop                                                 | After C8 ships and is stable                                | OUT (post-C8)      | L      |

### Summary table

| Total backlog items referenced | 6 (existing) + 4 (C6 v0.1) + 5 (C6 v0.2) = **15** |
| In scope this build            | 0                                                  |
| Out of scope this build        | 15                                                 |

---

## § 13 — Definitions

(v0.1 definitions retained; v0.2 additions below.)

- **PlotDirection8**: internal 8-direction enum used only for Vastu computation. Aggregated to 4-direction `PlotOrientation` for output.
- **8→4 Vastu aggregation rule**: cardinal direction's Vastu score for function F = max over (cardinal + 2 adjacent intercardinals) of their 8-dir Vastu score for F.
- **Permutation search size**: count of (band → direction) permutations that survived the entry-on-road prune in § 4.4 step 2; recorded in provenance.
- **`chosen_over_seed`**: provenance boolean; True iff the global-permutation argmax beat C5's seed by `SWAP_HYSTERESIS_THRESHOLD` (= 0.10).

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 (S30 design — Q1/Q2/Q3)

#### § 14.1 — Q1 (S30): Meaning B (functional priority per direction)

C6 is the "what each compass direction is best for" engine. Building massing (Meaning A) is implicit in plot dimensions + C5's topology choice. **B-100** captures massing-rotation work for when non-rectangular plots arrive.

#### § 14.2 — Q2 (S30): Vastu honors C1's three-tier contract

`VastuTier.{OFF, PARTIAL, FULL}` is the authoritative input. OFF default; OFF means `vastu_score == 0.0` (verified by validator). PARTIAL covers C1's locked 7-core-items list. **(See § 14.4 for v0.2's 8-dir refinement and § 14.8 for FULL hard-fail.)**

#### § 14.3 — Q3 (S30): Cardinality preservation

C6 returns one `OrientedCandidate` per input `TopologyCandidate`. No fan-out. Trade-off visibility comes from `signal_breakdown` per direction — not from enumerated alternative orientations.

### From v0.2 (S30 critique walk — items 3, 5, 6, 7, 9, 10)

#### § 14.4 — v0.2: 8-direction internal Vastu computation (item 3)

Vastu's most prescriptive content lives at intercardinal directions (NE pooja, SE kitchen, SW master bedroom, NW guest). Web research on Vastu Shastra confirmed: 8-dir is the minimum for the system to function meaningfully, and modern consultancies use 16-dir frameworks. Reducing to 4-dir cardinal output loses the canonical signal.

v0.2 adopts internal 8-dir computation (`PlotDirection8` enum) with an aggregation rule that takes the max over a cardinal + its two adjacent intercardinals. This faithfully preserves Vastu signal in the 4-dir output without changing C4/C5's `PlotOrientation` enum (no breaking change downstream).

**B-096 demoted from "out-of-scope deferred work" to "internal-adopted, output-only deferral"**: 8-dir is now active; the public output surface stays 4-dir until consumers ask for 8-dir externally.

#### § 14.5 — v0.2: Global permutation enumeration replaces greedy swap (item 5)

v0.1 § 4.4 used pairwise greedy swap, which can miss globally optimal assignments. With at most `4! = 24` permutations (non-COURTYARD) or `4^4 = 256` (COURTYARD), brute-force enumeration is trivial.

v0.2 enumerates all permutations, prunes by hard constraints, scores each, picks argmax, and applies hysteresis vs. C5 seed at the global level (not pairwise). Eliminates greedy-local pathologies.

#### § 14.6 — v0.2: Entry-on-road as search-space pruner + validator (item 6)

v0.1 had entry-on-road only as a post-hoc validator — the optimizer could waste cycles building infeasible candidates. v0.2 prunes entry-on-road-violating permutations *before* scoring them (§ 4.4 step 2). The validator (§ 4.6) stays as defense-in-depth — the same predicate, applied redundantly so a future refactor of the pruner can't silently break feasibility.

The 0.5 score for non-entry bands' road preference is retained as a soft preference (corner plots may want a service entry on the second road).

#### § 14.7 — v0.2: DINING split + composite_priority drop (items 7, 9)

**DINING split**: `FunctionRole.DINING` added per Indian residential context (dining is often a distinct space, Vastu-preferred E/SE). The 8-dir Vastu table includes a DINING column. *In v1, DINING co-locates with LIVING under the PUBLIC band (no separate band).* Future B-095 (FloorRoomBrief enrichment) may introduce per-room granularity; until then, DINING contributes to the PUBLIC band's score by being a co-considered function in the per-direction priority but doesn't get its own direction assignment.

**`composite_priority` drop**: equal-weighted mean across functions treats LIVING and UTILITY as equivalent — misleading. v0.2 drops the field. Sorting / tie-break uses the four signal-breakdown values directly. Consumers needing a single number compute their own weighted aggregate.

#### § 14.8 — v0.2: FULL Vastu tier hard-fails until B-099 KB exists (item 10)

v0.1 had FULL gracefully degrade to PARTIAL semantics with elevated weight + a `rule_trace` warning. This is honest in implementation but creates a contract gap — users got PARTIAL behavior while believing they had FULL.

v0.2 raises `NotImplementedError("FULL tier requires vastu_engine KB; B-099. Use PARTIAL.")` until the KB is populated. Cleaner contract, mechanical pressure on B-099 to actually land. OFF and PARTIAL remain fully functional.

---

## § 15 — Open questions for v0.3 critique round

(v0.1 questions either resolved by v0.2 or refreshed below.)

**Resolved by v0.2**: Q1 (DINING) — done. Q3 (hysteresis as guess) — backlog (B-103). Q4 (FULL gradual vs hard-fail) — done (hard-fail).

**Still open**:

1. **8→4 aggregation rule** — v0.2 uses `max(cardinal + 2 adjacent)`. Alternative: weighted average where the cardinal contributes 1.0 and the two intercardinals 0.5 each. Max is more conservative (preserves intercardinal signal); average is smoother. Calibrated empirically post-B-090.

2. **Wind function-independence** — v0.2 still doesn't multiply wind by `function_lookup`. But bedrooms benefit more from cross-ventilation than utility rooms. Should we differentiate?

3. **`OrientedCandidate` naming** — wraps `topology_candidate` + `orientation`. Sets pattern for C7+. Is this the right name? Alternatives: `LayoutCandidate`, `Stage2Candidate`.

4. **DINING band assignment** — v0.2 keeps DINING co-located with LIVING under PUBLIC. But Indian dining is often physically separate from living (especially in larger plots). Should DINING get its own band when topology has bandwidth? This intersects B-095.

5. **Permutation tie-break** — when two permutations score equally (e.g., 0.842 and 0.842), v0.2 doesn't specify the tie-break key. Possible: prefer the one closer to C5 seed (smaller permutation distance). Possible: lexicographic over `function_scores[LIVING]` then `function_scores[BEDROOM]`. v0.3 should pick.

6. **Permutation search-size invariant** — should the spec mandate a maximum search size (e.g., assert `len(surviving_perms) <= 256` to catch implementation bugs)? Currently the analytic bound is the limit; an explicit assertion would be defense-in-depth.

---

## § 16 — End of v0.2 PROPOSED

Ready for v0.3 critique round or LOCK. Six amendments applied; 5 new backlog items filed.
