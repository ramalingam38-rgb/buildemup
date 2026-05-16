# BuildemUp — C6 Orientation Priority — SPEC v0.4 PROPOSED

**Status**: PROPOSED. Not LOCKED. Awaits Ramalingam adjudication (LOCK or continue critique → v0.5).
**Component**: C6 of canonical 17-component v3 list (Track 3).
**Position in pipeline**: Era 2 layout. Consumes C4 + C5 + brief.vastu_tier; produces input for C8 corridor designer.
**Predecessor**: v0.3 PROPOSED.
**Lineage delta from v0.3**: three amendments applied per S30 critique walk #3 verdicts (items 3, 10, 12). One new backlog item formalized (B-106).
**Pushbacks held from v0.3 walk**: items 1, 2 (already in calibration backlog), 4 (search-space math unchanged), 5, 6, 11 (third-round raises with no new evidence), 7 (bounded inertia), 8 (adjacency is C9).

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

## § 3 — Output schema — *v0.4 changes*

**v0.4 changes**: `OrientationProvenance` gains `weights_raw` (per § 14.16). All other dataclasses unchanged from v0.3.

```python
class FunctionRole(str, Enum):
    LIVING       = "living"        # public-band default; absorbs DINING bias (E-leaning)
    BEDROOM      = "bedroom"        # private-band default
    KITCHEN      = "kitchen"        # service-band primary; Vastu-preferred SE
    POOJA        = "pooja"          # service-band, Vastu NE-preferred
    WET_AREA     = "wet_area"       # toilet/bath; Vastu avoids NE
    UTILITY      = "utility"        # service-band, low priority

class PlotDirection8(str, Enum):
    """Internal 8-direction enum for Vastu computation only."""
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
    road_score retained for provenance/inspection (NOT in function_scores; § 14.14)."""
    sun_score:    float   # [0, 1] — contributes to function_scores
    wind_score:   float   # [0, 1] — contributes to function_scores
    road_score:   float   # [0, 1] — provenance only
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
    weights_applied:          Mapping[str, float]   # post-renormalization;
                                                     # 3 keys (sun, wind, vastu)
    weights_raw:              Mapping[str, float]   # NEW v0.4 — pre-normalization;
                                                     # 3 keys; preserves absolute
                                                     # signal strength info (§ 14.16)
    climate_profile:          str
    rule_trace:               tuple[str, ...]
    permutation_search_size:  int                    # post-prune count
    chosen_over_seed:         bool
    seed_distance:            int                    # Hamming distance from C5 seed

@dataclass(frozen=True)
class OrientationPriority:
    direction_priorities: Mapping[PlotOrientation, DirectionPriorityScore]
    refined_zone_bands:   Mapping[ZoneBand, PlotOrientation]
    priority_confidence:  float                       # v0.4 reformed — § 4.5
    score_margin:         float                       # gap to second-best perm
    provenance:           OrientationProvenance

@dataclass(frozen=True)
class OrientedCandidate:
    topology_candidate: TopologyCandidate
    orientation:        OrientationPriority
```

---

## § 4 — Behavior

### § 4.1 — Per-direction baselines

(unchanged from v0.3)

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

Computed and exposed in `SignalBreakdown` for inspection. **Does NOT contribute to `function_scores`** — entry-on-road enforced as hard constraint at § 4.4 step 2. Soft secondary-road preference for service entries is **B-106** (deferred until empirically triggered — see § 12).

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

Worked examples (kitchen, canonical SE; pooja, canonical NE):
- Kitchen: S=0.700 > W=0.575 > E=0.525 > N=0.225 — gradient preserved (S closest to SE)
- Pooja: E=0.750 > N=0.675 > W=0.275 > S=0.225 — gradient preserved (E and N adjacent to NE)

### § 4.2 — Signal weighting

```
weights_raw = {
    "sun":   1.0   if climate_zone in (COMPOSITE, TEMPERATE) else 0.7,
    "wind":  1.0   if climate_zone == WARM_HUMID            else 0.6,
    "vastu": {OFF: 0.0, PARTIAL: 0.4, FULL: 0.7}[vastu_tier],
}
weights_applied = renormalize_to_sum_one(weights_raw)
```

**v0.4**: `weights_raw` (pre-normalization) is now retained alongside `weights_applied` (post-normalization) and exposed in `OrientationProvenance` for transparency. Renormalization preserves OFF/PARTIAL/FULL comparability in `weights_applied`; the raw weights show absolute strength of each signal before mixing (§ 14.16).

### § 4.3 — Per-direction per-function score computation

(unchanged from v0.3)

```
function_scores[direction][f] = (
    sun_score(direction)         * sun_function_lookup(f)  * w_sun
  + wind_score(direction, clim)  * wind_function_lookup(f) * w_wind
  + vastu_score_4dir(direction, f, tier)                   * w_vastu
)
```

Where `w_sun, w_wind, w_vastu` come from `weights_applied`.

**`sun_function_lookup(f)`**:

| f | multiplier |
|---|---|
| LIVING   | 1.0 |
| BEDROOM  | 0.7 |
| KITCHEN  | 0.6 |
| POOJA    | 0.8 |
| WET_AREA | 0.3 |
| UTILITY  | 0.3 |

**`wind_function_lookup(f)`**:

| f | multiplier |
|---|---|
| LIVING   | 0.9 |
| BEDROOM  | 1.0 |
| KITCHEN  | 0.6 |
| POOJA    | 0.5 |
| WET_AREA | 0.4 |
| UTILITY  | 0.3 |

### § 4.4 — Refining zone_bands — *v0.4 step 2 assertion added*

**Step 1 — generate candidate permutations** (unchanged):

For the topology's required-bands set, enumerate all band → direction assignments:

- Non-COURTYARD (STRIP, CENTRAL_SPINE, L_SHAPE): distinct-direction. ≤ `4! = 24`.
- COURTYARD: distinct relaxed. ≤ `4^4 = 256`.

**Step 2 — prune by hard constraints** + **v0.4 cap assertion**:

```
entry_bearing_band = ZoneBand.PUBLIC   # all four topology kinds
valid_entry_directions = (
    {plot.facing} ∪ ({secondary_road_direction} if corner_plot else ∅)
)

surviving_perms = [
    p for p in all_perms
    if p[entry_bearing_band] ∈ valid_entry_directions
]

# v0.4 NEW — defense-in-depth: catch implementation bugs that silently
# expand the search space
MAX_PERMUTATION_COUNT = 256
assert len(surviving_perms) <= MAX_PERMUTATION_COUNT, (
    f"permutation explosion: got {len(surviving_perms)}, "
    f"expected ≤ {MAX_PERMUTATION_COUNT} (analytic bound)"
)
```

Resolves v0.2 § 15 Q6 (§ 14.17).

**Step 3 — score every surviving permutation**:

```
total_score(perm) = (
    Σ_(b ∈ functional_bands) function_scores[band_to_function[b]][perm[b]]
  + 0.5 × function_scores[CIRCULATION][perm[CIRCULATION]]
)
```

`band_to_function`:
- PUBLIC      → LIVING
- SERVICE     → KITCHEN
- PRIVATE     → BEDROOM
- CIRCULATION → CIRCULATION (pseudo-function; light scoring)

`function_scores[CIRCULATION][direction] = 0.3×sun + 0.2×wind + 0.5` — light formulation that prefers no-west and mild airflow.

**Step 4 — apply hysteresis vs C5 seed + tie-break**:

```
seed_perm  = C5_default_zone_bands(topology, plot.facing)
seed_score = total_score(seed_perm)

ranked_perms = sort(surviving_perms, key=tie_break_key, descending=False)
best_perm    = ranked_perms[0]
best_score   = total_score(best_perm)

if best_score - seed_score >= SWAP_HYSTERESIS_THRESHOLD (= 0.10):
    chosen_perm = best_perm
    chosen_over_seed = True
else:
    chosen_perm = seed_perm
    chosen_over_seed = False
```

`tie_break_key(perm)` (5-tier):

```
1. -total_score(perm)                              # primary: highest score
2.  hamming_distance(perm, seed_perm)              # secondary: closest to seed
3. -function_scores[LIVING][perm[PUBLIC]]          # tertiary: best living
4. -function_scores[BEDROOM][perm[PRIVATE]]        # quaternary: best bedroom
5.  lex_band_direction(perm)                       # final: deterministic
```

**Step 5 — record `score_margin`**:

```
score_margin = best_score - second_best_score   # via tie_break_key ranking
```

If only one permutation survived, `score_margin = best_score - 0.0`.

### § 4.5 — Confidence — *v0.4 reform*

**v0.4** — replace `(top - mean_others) / top` (statistically weak; mean-based) with **margin-clamped formula** per § 14.15:

```
MIN_DENOM = 0.1
priority_confidence = clamp(
    (top_score - second_score) / max(top_score, MIN_DENOM),
    0.0, 1.0
)
```

**Behavior**:
- High `top_score` (≥ 0.1) with large gap to second: high confidence (close to 1.0)
- High `top_score` with tiny gap to second: low confidence
- Low `top_score` (< 0.1): denominator clamped at 0.1, preventing the small-denominator inflation the v0.3 walk flagged ("0.05 - 0.04 / 0.05 = 0.20" no longer looks confident)
- Single-permutation case: `second_score = 0.0`, denominator at least 0.1 → confidence = `top_score / 0.1` clamped to 1.0

**Why margin-clamped over entropy**: research literature establishes both margin- and entropy-based metrics outperform max-only / mean-based; margin is simpler to implement and reason about. Entropy upgrade is **B-104** (when real-world feedback shows margin-clamped misleads).

### § 4.6 — Validator (defense-in-depth)

(unchanged from v0.3)

Construction-time validator checks:
1. `direction_priorities` covers exactly N, E, S, W.
2. Every `function_scores` value in [0, 1].
3. `signal_breakdown.vastu_score == 0.0` iff `vastu_tier == OFF`.
4. Refined `zone_bands` keeps the C5-required band set for the topology kind.
5. For non-COURTYARD topologies, refined `zone_bands` has distinct directions.
6. Entry-on-road: entry-bearing band maps to a road-facing direction.
7. `seed_distance == hamming_distance(refined_zone_bands, seed_zone_bands)`.

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

(unchanged from v0.3 — FULL hard-fail retained per v0.2 § 14.8 and three rounds of pushback)

| Condition                                          | Behavior                                                   |
|----------------------------------------------------|------------------------------------------------------------|
| `candidates` is empty tuple                        | Returns empty tuple                                        |
| `candidates` is not a tuple                        | `TypeError`                                                |
| `vastu_tier` is not a VastuTier instance           | `TypeError`                                                |
| `plot_analysis.shape != RECTANGULAR`               | `NotImplementedError("v1 supports rectangular only; B-066")` |
| Climate zone is HOT_DRY or COLD                    | `NotImplementedError("climate zone reserved; B-098")`      |
| `vastu_tier == FULL` and `vastu_engine` KB absent  | `NotImplementedError("FULL tier requires vastu_engine KB; B-099. Use PARTIAL.")` |
| All permutations pruned by entry-on-road           | Falls back to C5 seed (`chosen_over_seed=False`); never raises |
| `len(surviving_perms) > 256`                       | **NEW v0.4** — `AssertionError` (defense-in-depth; catches implementation bugs) |

---

## § 7 — Test plan — *v0.4 updates*

Following C5's pattern. v0.4 targets ~115-135 tests (small growth from v0.3).

**Unchanged from v0.3**: cardinality, ordering, OFF tier zero-vastu invariant, FULL hard-fail, climate behavior, frozen/immutability, perturbation stability, weighted-avg aggregation, wind_function_lookup, CIRCULATION light scoring, tie-break determinism, Hamming distance recording, DINING removal, road in provenance.

**v0.4 additions**:

- **Margin-clamped confidence**:
  - `top=0.8, second=0.7` → confidence = `0.1/0.8 = 0.125`
  - `top=0.05, second=0.04` → confidence = `0.01/max(0.05, 0.1) = 0.01/0.1 = 0.1` (no longer inflated)
  - `top=0.9, second=0.0` → confidence = `0.9/0.9 = 1.0` (clamped to 1.0)
  - `top=0.0, second=0.0` → confidence = `0.0/0.1 = 0.0`
  - Single-perm case: `second=0.0` → confidence reflects only top_score
- **`weights_raw` exposed**: provenance carries pre-normalization weights; consumers can verify FULL has `vastu_raw=0.7` vs PARTIAL `vastu_raw=0.4` even when post-normalized values look proportionally similar
- **Permutation cap assertion**: deliberately injected mock that returns >256 permutations triggers `AssertionError`

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
| 8-dir external output | **B-096** | Internally adopted; external output deferred |
| Multi-floor per-floor orientation | **B-097** | OUT |
| HOT_DRY / COLD climate zones | **B-098** | OUT |
| `vastu_engine` KB for FULL | **B-099** | OUT (hard-blocking — § 14.8) |
| Empirical recalibration | **B-090** | OUT (existing) |
| Per-room finer priorities (incl. DINING band) | **B-095** | OUT |
| Building massing rotation | **B-100** | OUT |
| Signal interaction terms | **B-101** | OUT |
| Location-aware wind & continuous climate | **B-102** | OUT |
| Dynamic hysteresis threshold | **B-103** | OUT |
| Entropy-/variance-based confidence | **B-104** | OUT (margin-clamped is v0.4 default — § 14.15) |
| C6 ↔ C8 layout-feasibility feedback | **B-105** | OUT |
| **Secondary-road service-entry bonus (corner plots)** | **B-106** | **NEW v0.4 — formalized** (§ 12) |

---

## § 10 — Provenance — *v0.4 addition*

`OrientationProvenance` carries:

- `derived_at`, `plot_analysis_trace_id` — traceability
- `vastu_tier` — proves what tier was applied
- `weights_applied` — post-normalization weights (3 keys: sun, wind, vastu)
- **`weights_raw`** — *v0.4 NEW* — pre-normalization weights; preserves absolute signal-strength info that renormalization compresses (§ 14.16)
- `climate_profile`, `rule_trace` — debugging
- `permutation_search_size` — post-prune count
- `chosen_over_seed` — True if global optimum beat seed by hysteresis
- `seed_distance` — Hamming distance of chosen permutation from seed

---

## § 11 — Spec metadata

- **Version**: v0.4 PROPOSED
- **Status**: PROPOSED. Pending Ramalingam adjudication (LOCK or → v0.5).
- **Lineage**: v0.1 DRAFT → v0.2 PROPOSED (walk #1) → v0.3 PROPOSED (walk #2) → v0.4 PROPOSED (walk #3)
- **Authoring session**: S30
- **Companion artifacts**: 3 critique-walk verdicts; 1 new B-NNN (B-106) formalized

---

## § 12 — Backlog enumeration

### Existing (referenced)

| ID | Description |
|---|---|
| B-066 | non-rectangular plot guardrail |
| B-090 | empirical recalibration |
| B-091 | climate-variant zone-band overrides |
| B-094 | orthogonalize width_fit vs aspect_ratio_fit |
| B-095 | FloorRoomBrief enrichment (also gates DINING band reintro) |
| B-096 | Externally expose 8-dir output |

### From C6 v0.1

| ID | Description | Trigger |
|---|---|---|
| B-097 | Multi-floor per-floor orientation | When C9/C10 introduce multi-floor placement |
| B-098 | HOT_DRY and COLD climate zones | When a v1 city maps to either |
| B-099 | Populate `vastu_engine` KB | NOW BLOCKING — FULL hard-fails until populated |
| B-100 | Building massing rotation | When non-rectangular plots arrive |

### From C6 v0.2 walk

| ID | Description | Trigger |
|---|---|---|
| B-101 | Signal interaction terms | When B-090 yields ≥ 50 datapoints |
| B-102 | Location-aware wind & continuous climate | When B-090 reveals city-level variance > zone-level |
| B-103 | Dynamic hysteresis threshold | Post-B-090 |
| B-104 | Entropy-/variance-based confidence | When real-world feedback shows margin-clamped misleads (v0.4 § 14.15 baseline) |
| B-105 | C6 ↔ C8 layout-feasibility feedback | After C8 ships |

### From C6 v0.3 walk

(none filed)

### From C6 v0.4 walk

| ID | Description | Trigger | S30-scope verdict | Effort |
|---|---|---|---|---|
| **B-106** | SERVICE-band-only secondary-road bonus on corner plots — soft preference for service entry on the secondary road of corner plots; v0.3 § 14.14 cleaned up road handling, but corner-plot service-entry optimization is a real architectural pattern that v1's hard-only road treatment doesn't capture | (a) corner-plot share of v1 production usage exceeds 25%, OR (b) ≥ 5 user complaints about service entry placement on corner plots | OUT (deferred until empirically triggered; v0.3 just consolidated road handling — Pattern A risk in re-amending) | S |

### Summary

| Total backlog items referenced | 6 + 4 + 5 + 0 + 1 = **16** |
| In scope this build            | 0 |
| Out of scope this build        | 16 |

---

## § 13 — Definitions

(v0.1/v0.2/v0.3 definitions retained; v0.4 additions below)

- **Margin-clamped confidence** *(v0.4)*: `clamp((top - second) / max(top, MIN_DENOM), 0, 1)` with `MIN_DENOM = 0.1`. Replaces v0.3's mean-based formula (statistically weak per literature; § 14.15).
- **`weights_raw`** *(v0.4)*: pre-normalization signal weights (sun, wind, vastu) exposed in `OrientationProvenance` alongside `weights_applied`. Preserves absolute-strength information that renormalization compresses.
- **MAX_PERMUTATION_COUNT** *(v0.4)*: constant `= 256`. Used in § 4.4 step 2 assertion as defense-in-depth against implementation bugs that could silently expand the search space.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 (S30 design)

#### § 14.1 — Q1: Meaning B (functional priority per direction)
#### § 14.2 — Q2: Vastu honors C1's three-tier contract
#### § 14.3 — Q3: Cardinality preservation

### From v0.2 (S30 critique walk #1)

#### § 14.4 — 8-direction internal Vastu computation (refined in v0.3 § 14.9)
#### § 14.5 — Global permutation enumeration replaces greedy swap
#### § 14.6 — Entry-on-road as search-space pruner + validator (refined in v0.3 § 14.14)
#### § 14.7 — DINING split + composite_priority drop (DINING reversed in v0.3 § 14.12)
#### § 14.8 — FULL Vastu tier hard-fails until B-099 (reaffirmed three times)

### From v0.3 (S30 critique walk #2)

#### § 14.9 — Weighted-avg 8→4 aggregation replaces max
#### § 14.10 — CIRCULATION light scoring
#### § 14.11 — wind_function_lookup added
#### § 14.12 — DINING REVERSAL (drops `FunctionRole.DINING`)
#### § 14.13 — Tie-break hierarchy defined (5-tier)
#### § 14.14 — road_score moved to provenance-only

### From v0.4 (S30 critique walk #3)

#### § 14.15 — Margin-clamped confidence replaces mean-based (item 3)

v0.3's `(top - mean_others) / top` was the third raise of the same critique (v0.1 walk item 8 → backlog; v0.2 walk item 6 → backlog; v0.3 walk item 3 → amend). Web research established that mean-based and max-only confidence are statistically weak for ranking systems; margin-based or entropy-based is the established practice.

v0.4 adopts **margin-clamped** formula: `clamp((top - second) / max(top, 0.1), 0, 1)`. Simpler than entropy, addresses the small-denominator inflation the v0.3 walk flagged (`top=0.05, second=0.04` no longer reads as confidence ≈ 0.20). Entropy-based remains in B-104 for when real-world feedback shows margin-clamped misleads.

#### § 14.16 — `weights_raw` exposure for absolute-strength transparency (item 10)

v0.3 exposed `weights_applied` (post-renormalization) only. The reviewer noted renormalization compresses absolute differences (FULL-tier `vastu_raw=0.7` after renormalization can look proportionally similar to PARTIAL `vastu_raw=0.4`). v0.4 retains `weights_raw` (pre-normalization) alongside `weights_applied` in `OrientationProvenance`. No scoring change; pure transparency add. Lets users verify "this run had FULL-tier raw weight 0.7" without re-deriving from the scoring formula.

#### § 14.17 — Permutation cap assertion (item 12)

Resolves v0.2 § 15 Q6. v0.4 adds explicit `assert len(surviving_perms) <= MAX_PERMUTATION_COUNT (= 256)` after § 4.4 step 2 pruning. Catches implementation bugs that silently expand the search space. Zero runtime cost in valid cases. Defense-in-depth alongside the analytic bound.

### Pushback ledger (items the spec deliberately does NOT address)

Across three critique walks, eight items have been raised that v0.4 deliberately holds against:

| Item | Round(s) raised | Reason for hold |
|---|---|---|
| Adjacency between bands | walk #1 (item 2), walk #2 (item 8) | Adjacency is C9's job; band-level "minimal coupling" has no clean v1 formulation |
| Search-space < threshold fallback | walk #1 (item 4), walk #2 (item 4) | Math: minimum 6 permutations across all valid (topology, corner) combinations; trigger never fires |
| FULL graceful degradation | walk #1 (item 12), walk #2 (item 11), walk #3 (item 11) | Original v0.1 walk asked for hard-fail; reversing now would re-open the contract gap |
| Signal interaction terms | walk #1 (item 1), walk #2 (item 5), walk #3 (item 5) | Pre-empirical; B-101 covers it |
| Dynamic hysteresis | walk #1 (item 4), walk #2 (item 5), walk #3 (item 6) | Pre-empirical; B-103 covers it |
| Tie-break "design inertia" | walk #2 (item 7) | Bias is bounded by hysteresis; intentional and explicit (§ 14.13) |
| Continuous climate weights | walk #1 (item 12), walk #2 (item 11) | C4 enrichment territory; B-102 |
| Aggregation distortion (post weighted-avg) | walk #2 (item 1) | v0.3 § 14.9 fix produces real gradient; remaining tuning is calibration (B-090) |

Each of these has been considered and a deliberate decision made. Future spec rounds should bring **new evidence** if reopening any of them.

---

## § 15 — Open questions for v0.5 critique round (or LOCK)

**Resolved by v0.4**: confidence formula (§ 14.15), provenance transparency (§ 14.16), permutation cap (§ 14.17).

**Carried forward**:

1. **`OrientedCandidate` naming** — sets the pattern for C7+. Alternatives: `LayoutCandidate`, `Stage2Candidate`. Worth resolving before LOCK because rename gets expensive once C7 spec references this type. **Recommendation**: keep `OrientedCandidate` — descriptive, accurate, no namespace collision.
2. **Weighted-avg intercardinal weight** — 0.5 vs 0.7. Calibration; B-090 territory.
3. **CIRCULATION scoring multiplier** — 0.5 in total, 0.3×sun + 0.2×wind + 0.5 baseline. Calibration; B-090 territory.
4. **`wind_function_lookup` values** — heuristic; B-090 will tune.
5. **Hamming distance normalization for L_SHAPE** — currently raw integer (0-3 for L_SHAPE, 0-4 for others). Cross-topology comparison isn't a real scenario in v1, so normalization may be over-engineering. **Recommendation**: leave raw integer; document this in § 4.4 step 4.
6. **MIN_DENOM choice** *(new v0.4)* — `0.1` is heuristic. Could be `0.05` (less aggressive clamping) or `0.2` (more aggressive). Calibration; B-090 territory once confidence-related feedback arrives.

All carried-forward items are calibration questions or naming preferences. **None are structural.**

---

## § 16 — End of v0.4 PROPOSED

**Convergence trajectory** (cumulative):

```
                  amendments  new B-NNNs  misframed/pushback
v0.1 → v0.2          6           5           3
v0.2 → v0.3          6           0           3
v0.3 → v0.4          3           1           8 (5 first-time + 3 third-raise)
                     ▼           ▼           ▲
              halved each round           pushbacks now cycling
```

3 amendments. 1 new B-NNN. Cycling pushbacks signal the design has stabilized. § 15 carries 6 open questions, all calibration or naming — none structural. Spec is LOCK-ready pending Ramalingam adjudication.
