# BuildemUp — C6 Orientation Priority — SPEC v0.1 DRAFT

**Status**: PROPOSED (DRAFT). Not LOCKED. Awaits Ramalingam critique → iterate → LOCK.
**Component**: C6 of canonical 17-component v3 list (Track 3).
**Position in pipeline**: Era 2 layout. Consumes C4 + C5 + brief.vastu_tier; produces input for C8 corridor designer.
**Predecessor in spec lineage**: none (greenfield).
**Author session**: S30 (post-C5 v1.0 SHIP).

---

## § 1 — Purpose

C5 selects a topology *kind* for the plot (STRIP, CENTRAL_SPINE, L_SHAPE, COURTYARD) and assigns a *default* `zone_bands` mapping that rigidly follows `plot.facing` (PUBLIC=front, PRIVATE=back, SERVICE=left, CIRCULATION=right). That default is correct as a placeholder, but it ignores three signals that materially affect liveability:

1. **Sun path** — west exposure is hot, east is cool morning, north is calm light, south is heavy summer sun.
2. **Wind direction** — warm-humid climate (Chennai, Mumbai) wants windward openings for cross-ventilation; composite (Delhi) wants the opposite.
3. **Vastu** — culturally significant for a meaningful fraction of Indian buyers; opt-in via C1's locked `VastuTier.{OFF, PARTIAL, FULL}`.

A fourth signal — **road relationship** — is implicit in C5's default (entry has to face the road) and continues to be honored.

C6 reads these signals, computes a *per-direction functional priority* (which compass direction is best for living vs bedroom vs kitchen vs pooja vs wet-area vs utility), and uses that priority to refine each C5 candidate's `zone_bands` while preserving the input cardinality.

**Out of scope for C6**: building massing rotation, room sizing, room placement, corridor geometry. C6 only refines *which compass direction gets which functional band*.

---

## § 2 — Input contract

```python
def prioritize_orientation(
    candidates: tuple[TopologyCandidate, ...],   # 1-3 from C5
    plot_analysis: PlotAnalysis,                  # from C4
    vastu_tier: VastuTier = VastuTier.OFF,        # from C1.brief
) -> tuple[OrientedCandidate, ...]:
```

**Why pass `vastu_tier` and not the full brief**: C6 only needs the tier; coupling to the rest of the brief would force test fixtures to construct a full Brief just to test orientation logic. Cleaner contract.

**Why pass `plot_analysis` instead of just `plot.facing`**: C6 reads `climate_zone`, `aspect_ratio`, `neighbour_context.open_sides`, and `plot.facing`. PlotAnalysis already aggregates these — no reason to deconstruct.

**Cardinality**: 1-3 candidates in → 1-3 OrientedCandidate out, position-paired (Q3 design).

---

## § 3 — Output schema

```python
class FunctionRole(str, Enum):
    LIVING   = "living"          # public-band default
    BEDROOM  = "bedroom"          # private-band default
    KITCHEN  = "kitchen"          # service-band primary
    POOJA    = "pooja"            # service-band, Vastu-sensitive
    WET_AREA = "wet_area"         # toilet/bath; Vastu has avoid-NE rule
    UTILITY  = "utility"          # service-band, low priority

@dataclass(frozen=True)
class SignalBreakdown:
    """Per-direction contribution from each of the four signals (each in [0,1])."""
    sun_score:    float
    wind_score:   float
    road_score:   float
    vastu_score:  float           # 0.0 when vastu_tier == OFF

@dataclass(frozen=True)
class DirectionPriorityScore:
    """For one compass direction, the per-function priority (each in [0,1]).

    Higher = better-suited for that function on this direction.
    """
    function_scores: Mapping[FunctionRole, float]
    signal_breakdown: SignalBreakdown
    composite_priority: float     # weighted sum across functions; for sorting

@dataclass(frozen=True)
class OrientationProvenance:
    derived_at: float                                          # from plot_analysis
    plot_analysis_trace_id: str
    vastu_tier: VastuTier
    weights_applied: Mapping[str, float]                       # sun/wind/road/vastu post-norm
    climate_profile: ClimateProfile                            # which climate-strategy was selected
    rule_trace: tuple[str, ...]                                # ordered list of rules fired

@dataclass(frozen=True)
class OrientationPriority:
    """The C6 output for one C5 candidate."""
    direction_priorities: Mapping[PlotOrientation, DirectionPriorityScore]
    refined_zone_bands:   Mapping[ZoneBand, PlotOrientation]   # may differ from C5's default
    priority_confidence:  float                                # 0..1
    score_margin:         float                                # gap to runner-up direction per band
    provenance:           OrientationProvenance

@dataclass(frozen=True)
class OrientedCandidate:
    """C5 TopologyCandidate augmented with C6 orientation priority."""
    topology_candidate: TopologyCandidate
    orientation:        OrientationPriority
```

**Why a separate wrapper `OrientedCandidate` instead of mutating `TopologyCandidate`**: TopologyCandidate is C5's frozen contract; modifying it would couple C5 to C6. The wrapper preserves loose coupling and lets future spec rounds add fields to OrientationPriority without disturbing C5.

**Why expose `signal_breakdown` per direction**: Q2's promise — Vastu trade-offs are visible (`vastu_score` is always present, == 0 at OFF tier so consumers can prove non-influence). Same applies for climate: a city designer wants to see *why* north was chosen for living.

---

## § 4 — Behavior

### § 4.1 — Per-direction baseline tables (climate-conditional)

For each `(climate_zone, direction)` pair, compute the four signal raw scores. Then per-function priority is a weighted aggregation of those signals.

**Sun-score table** (warm-humid + composite + temperate; same for v0.1, refined empirically per B-090):

| Direction | sun_score | comment                                               |
|-----------|-----------|-------------------------------------------------------|
| North     | 0.95      | Best — diffuse calm light, no harsh sun               |
| East      | 0.85      | Morning sun, cool by afternoon                        |
| South     | 0.55      | Strong summer sun, good winter sun (composite/cold)   |
| West      | 0.20      | Hot afternoon sun, hardest to shade                   |

(Hot-dry and cold zones reserved — no v1 city maps to them; B-098.)

**Wind-score table** (climate-zone-conditional):

| Direction | warm-humid | composite | temperate |
|-----------|------------|-----------|-----------|
| North     | 0.6        | 0.7       | 0.7       |
| East      | 0.7        | 0.6       | 0.7       |
| South     | 0.9        | 0.5       | 0.7       |
| West      | 0.85       | 0.5       | 0.7       |

(Warm-humid: south-southwest monsoon winds prevail — those become the cross-ventilation source. Composite: less dominant prevailing-wind story; flatter curve. Temperate: low wind sensitivity overall.)

**Road-score** (= 1.0 for the direction matching `plot.facing`, 0.5 otherwise — soft preference, not hard, because the plot's secondary side could host a service entry on corner plots).

**Vastu-score** at PARTIAL tier — derived from C1's locked 7 core items, simplified to the 4 cardinal directions (NE → split half between N and E, etc.):

| Direction | living | bedroom | kitchen | pooja | wet_area | utility |
|-----------|--------|---------|---------|-------|----------|---------|
| North     | 0.9    | 0.6     | 0.4     | 0.85  | 0.3      | 0.5     |
| East      | 0.85   | 0.7     | 0.5     | 1.0   | 0.3      | 0.5     |
| South     | 0.5    | 0.4     | 0.7     | 0.3   | 0.5      | 0.6     |
| West      | 0.4    | 0.5     | 0.6     | 0.2   | 0.7      | 0.9     |

(Items 1-7 from C1 spec collapsed to this table at draft time. Faithful reading: NE pooja preferred, SE kitchen, SW master bedroom, NE wet-area avoid. v0.1 preserves these as priorities, not blocks. The full 8-direction grain is B-096.)

**Vastu-score at FULL tier** — larger weight (0.7) and additional 5+ items from `vastu_engine` KB (KB does not yet exist; B-099 stub). v0.1 implements PARTIAL fully and FULL == PARTIAL behavior with elevated weight, until KB lands.

### § 4.2 — Signal weighting

```
weights = {
    "sun":   1.0   if climate_zone in (COMPOSITE, TEMPERATE) else 0.7,
    "wind":  1.0   if climate_zone == WARM_HUMID            else 0.6,
    "road":  0.5,  # always; entry constraint is soft
    "vastu": {OFF: 0.0, PARTIAL: 0.4, FULL: 0.7}[vastu_tier],
}
weights = renormalize_to_sum_one(weights)
```

Renormalization ensures total weight is 1.0 regardless of tier — so OFF-tier and FULL-tier candidates are directly comparable on `composite_priority`.

### § 4.3 — Per-direction per-function score computation

For each direction `d ∈ {N, E, S, W}` and each function `f ∈ FunctionRole`:

```
function_scores[f] = (
    sun_score(d)   * sun_function_lookup(f)   * w_sun
  + wind_score(d, climate)                    * w_wind
  + road_score(d, plot.facing)                * w_road
  + vastu_score(d, f, tier)                   * w_vastu
)
```

Where `sun_function_lookup(f)` accounts for which functions actually care about sun (living=high, wet_area=low). Wind score doesn't multiply by function weight — wind benefits everywhere.

`composite_priority` per direction = mean across functions; used only for sorting / tie-break.

### § 4.4 — Refining `zone_bands`

Default (C5) zone-band mapping is the starting point. C6 considers swaps:

```
For each pair of (band, direction) in C5's default:
    if there exists another direction d' such that
       function_scores[band_to_function[band]] is meaningfully higher at d'
       AND swapping doesn't violate consistency (entry on road, no-duplicate-direction
       except for COURTYARD):
    then swap.
```

"Meaningfully higher" = score difference > `SWAP_HYSTERESIS_THRESHOLD = 0.10`. This is *deliberate hysteresis* — C5's default is the seed, C6 only overrides on significant signal. Avoids flip-flopping for plots where multiple directions are nearly equivalent.

`band_to_function`:
- PUBLIC      → LIVING
- SERVICE     → KITCHEN (primary; wet_area secondary)
- CIRCULATION → none (gets the leftover direction)
- PRIVATE     → BEDROOM

### § 4.5 — Confidence and margin

`priority_confidence` per OrientationPriority:

```
priority_confidence = mean over bands of (top_score - second_score) / top_score
```

When all directions score similarly (square plot, temperate climate, OFF tier), confidence is low — telling the user that the choice is weakly determined.

`score_margin`: the smallest band-level gap to the runner-up direction. Surfaces the closest-call band so a UI can highlight it.

### § 4.6 — Validators / consistency

A `_validate_orientation_priority(c)` runs at construction:

1. `direction_priorities` covers exactly N, E, S, W (4 keys).
2. Every `function_scores` value in [0, 1].
3. `signal_breakdown.vastu_score == 0.0` iff `vastu_tier == OFF`.
4. Refined `zone_bands` keeps the C5-required band set for the topology kind (i.e., we don't *delete* any band).
5. For non-COURTYARD topologies, refined `zone_bands` has distinct directions.
6. Entry-on-road preserved: the band hosting the main entry (PUBLIC for STRIP/CENTRAL_SPINE/COURTYARD; the front arm of L_SHAPE) maps to a road-facing direction (`plot.facing` or, on corner plots, the secondary road-facing direction).

---

## § 5 — Invocation contract (public)

```python
from buildemup.components.c06 import prioritize_orientation, VastuTier

oriented_candidates = prioritize_orientation(
    candidates=topology_candidates,
    plot_analysis=plot_analysis,
    vastu_tier=brief.vastu_preference.tier,
)
```

Returns `tuple[OrientedCandidate, ...]` of the same length as `candidates`. Order is preserved (no re-ranking — C5 already did that).

---

## § 6 — Failure modes

| Condition                                          | Behavior                                                   |
|----------------------------------------------------|------------------------------------------------------------|
| `candidates` is empty tuple                        | Returns empty tuple (no-op, no raise)                      |
| `candidates` is not a tuple                        | `TypeError`                                                |
| `vastu_tier` is not a VastuTier instance           | `TypeError`                                                |
| `plot_analysis.shape != RECTANGULAR`               | `NotImplementedError("v1 supports rectangular only; B-066")` |
| Climate zone is HOT_DRY or COLD (reserved in v1)  | `NotImplementedError("climate zone reserved; B-098")`      |
| Vastu KB requested at FULL but KB not present      | Falls back to PARTIAL semantics with elevated weight; emits warning to provenance.rule_trace |

No internal `RuntimeError` paths in v0.1 (all-fail scenarios produce low confidence, not exceptions — analogous to C5's Q7 reversal).

---

## § 7 — Test plan (sketch — fleshed out at code-build time)

Following C5's pattern (which gave 120 tests / 1539 total passing):

- **Cardinality / ordering**: N candidates in → N OrientedCandidates out, same order
- **Per-tier Vastu behavior**:
  - OFF → `vastu_score == 0.0` for every direction; identical output regardless of brief content
  - PARTIAL → 7-core-item Vastu signal honored; pooja best at NE, SW best for bedroom
  - FULL → larger weight than PARTIAL; structurally similar output
- **Climate behavior**:
  - WARM_HUMID — wind weight dominates, south-southwest preferred
  - COMPOSITE — sun weight dominates, north preferred for living
- **Refinement hysteresis**: small signal differences (< 0.10) preserve C5's default; large differences trigger swap
- **Entry-on-road preserved**: across all 4 facings × 4 topology kinds × 2 corner/non-corner configurations
- **Confidence behavior**: square plot in temperate, OFF tier → confidence < 0.3; rectangular plot warm-humid PARTIAL → confidence > 0.6
- **Frozen / immutability**: every dataclass frozen; every Mapping is MappingProxyType
- **Stability** (Hypothesis): perturbing brief.vastu_tier OFF → PARTIAL → FULL produces monotonic increases in vastu_score; perturbing direction by ±1 cardinal step (N→E) cycles direction priorities consistently
- **Failure modes**: each row of § 6 covered

Target: ~80-100 new tests; full suite stays green.

---

## § 8 — KB references

| KB                  | Status   | Used for                                        |
|---------------------|----------|-------------------------------------------------|
| Climate strategies  | exists   | sun/wind score baselines per zone               |
| Sun path            | partial  | east-morning / west-afternoon priors            |
| `vastu_engine`      | **stub** | FULL-tier extra items; B-099 to populate        |

C6 v1.0 does not require `vastu_engine` to be fully populated — PARTIAL tier covers the C1 contract. FULL tier degrades gracefully to PARTIAL until B-099 lands.

---

## § 9 — Out of scope (deferred to backlog § 12)

- 8-direction granularity (NE, NW, SE, SW) → **B-096**
- Multi-floor per-floor orientation (each floor independently oriented) → **B-097**
- HOT_DRY and COLD climate zones → **B-098**
- `vastu_engine` KB population for FULL tier → **B-099**
- Empirical recalibration of weights against real plans → **B-090** (existing)
- Per-room (master vs guest bedroom) finer-grain priorities → **B-095** (existing)
- Building massing rotation (Meaning A from S30 design discussion) → **B-100**

---

## § 10 — Provenance

`OrientationProvenance` carries:
- `derived_at` — pulled from `plot_analysis.provenance.derived_at` (single pipeline clock, per C5 Q8 precedent)
- `plot_analysis_trace_id` — for cross-component tracing
- `vastu_tier` — what tier was applied (provable)
- `weights_applied` — final post-renormalization weights for sun/wind/road/vastu
- `climate_profile` — which climate-strategy was selected (e.g., "warm_humid_wind_dominant")
- `rule_trace` — ordered list of rules that fired (e.g., `("c5_default_seed", "vastu_pooja_NE", "swap_living_to_north")`) — debugging aid

---

## § 11 — Spec metadata

- **Version**: v0.1 DRAFT
- **Status**: PROPOSED. Not LOCKED. Awaits Ramalingam adjudication.
- **Authoring session**: S30
- **Lineage**: greenfield (no predecessor versions)
- **Companion artifacts**: none yet (no critique rounds applied)

---

## § 12 — Backlog enumeration (per Rule 9)

Following the structure locked in C5 v0.9 § 12.

### Items spec depends on (existing — referenced not introduced)

| ID    | Description                                                | Origin |
|-------|------------------------------------------------------------|--------|
| B-066 | non-rectangular plot guardrail                             | C5 v0.4 |
| B-090 | empirical recalibration of weights against real plans      | C4/C5 |
| B-091 | climate-variant zone-band overrides                        | C5 v0.5 |
| B-094 | orthogonalize width_fit vs aspect_ratio_fit                | S30 walk |
| B-095 | FloorRoomBrief enrichment for downstream components        | S30 walk |

### Items NEW in this spec

| ID    | Description                                                                              | Trigger                                                  | S{N}-scope verdict | Effort |
|-------|------------------------------------------------------------------------------------------|----------------------------------------------------------|---------------------|--------|
| B-096 | 8-direction granularity (NE, NW, SE, SW)                                                 | When real plans show NE/SW Vastu rules need precision    | OUT (v1 = 4-dir)    | M      |
| B-097 | Multi-floor per-floor orientation                                                        | When C9/C10 introduce multi-floor placement              | OUT (v1 = 1 floor)  | L      |
| B-098 | HOT_DRY and COLD climate zones                                                           | When a v1 city maps to either (none currently)           | OUT (no city)       | S      |
| B-099 | Populate `vastu_engine` KB for FULL tier                                                 | When ≥ 1 FULL-tier user requests are observed in pilots  | OUT (PARTIAL covers contract) | M |
| B-100 | Building massing rotation engine (Meaning A from S30 discussion)                         | When non-rectangular plots arrive (B-066 also gates this)| OUT (no use case yet)| L      |

### Summary table (rolled up — C5 § 12 pattern)

| Total backlog items referenced | 5 (existing) + 5 (new) = 10 |
| In scope this build            | 0 |
| Out of scope this build         | 10 |

---

## § 13 — Definitions

- **Direction priority**: a per-(direction, function) score in [0,1] indicating how well-suited that compass direction is for that function on this specific plot.
- **Composite priority**: per-direction summary score, used for sorting (mean across functions).
- **Refinement hysteresis**: minimum signal advantage (0.10) needed to override C5's default zone-band assignment.
- **Vastu tier**: opt-in level (OFF / PARTIAL / FULL) honoring C1's locked contract. Default OFF.
- **Climate profile**: a derived label naming which climate-strategy was selected (e.g., "warm_humid_wind_dominant", "composite_sun_dominant"). Provenance only; not used for control flow.
- **Entry-on-road**: invariant that the band hosting the main entry must map to a road-facing direction.

---

## § 14 — Architectural decisions

(This section grows in v0.2+ as critique rounds resolve specific design choices. v0.1 records the three S30 design decisions only.)

### § 14.1 — Q1 framing (S30): Meaning B (functional priority per direction)

C6 is the "what each compass direction is best for" engine. Building massing (Meaning A) is implicit in plot dimensions + C5's topology choice and is not C6's concern. **B-100** captures the massing-rotation work for when non-rectangular plots arrive.

### § 14.2 — Q2 (S30): Vastu honors C1's three-tier contract

`VastuTier.{OFF, PARTIAL, FULL}` is the authoritative input. OFF default; OFF means `vastu_score == 0.0` for every direction (verified by validator). PARTIAL covers C1's locked 7-core-items list. FULL elevates weight to 0.7 and (when B-099 lands) consults full `vastu_engine` KB. **Vastu never blocks** — it only re-weights priorities.

### § 14.3 — Q3 (S30): Cardinality preservation

C6 returns one `OrientedCandidate` per input `TopologyCandidate`. No fan-out. Trade-off visibility comes from `signal_breakdown` per direction (sun/wind/road/vastu shown separately) — not from enumerated alternative orientations. If users later request orientation alternatives, that's a v1.x feature behind a separate `select_orientation_variant()` entry, not a v1 cardinality multiplier.

---

## § 15 — Open questions for v0.2 critique round

(Authored by Claude — Ramalingam may keep, drop, or replace.)

1. **Function-list scope** — the FunctionRole enum has 6 members (LIVING, BEDROOM, KITCHEN, POOJA, WET_AREA, UTILITY). Should DINING be separate from LIVING, or folded in? Indian context: dining is often a distinct space.

2. **Climate-zone dispatch granularity** — v0.1 has one wind table per (warm-humid, composite, temperate). Should we extend to per-city (Chennai-specific monsoon direction vs Mumbai's)? Tracks B-090 and the climate-refinement research thread; v0.1 keeps the NBC-matching coarseness.

3. **Hysteresis threshold** — `SWAP_HYSTERESIS_THRESHOLD = 0.10` is a guess. Is this too sticky? Too loose? Calibrated empirically post-B-090.

4. **Vastu PARTIAL → FULL behavior delta** — v0.1 makes FULL behave structurally like PARTIAL but with elevated weight (0.7 vs 0.4) until B-099 lands. Is that gradual-degradation reasonable, or should FULL hard-fail when KB is missing?

5. **Wind-score function-independence** — v0.1 doesn't multiply wind by `function_lookup` because "wind benefits everywhere." But bedrooms specifically benefit MORE from cross-ventilation than utility rooms (humans sleep there). Should we differentiate?

6. **Output field naming** — `OrientedCandidate` wraps `topology_candidate` + `orientation`. Is this the right name? Alternative: `LayoutCandidate`, `OrientedTopologyCandidate`, `Stage2Candidate`. Naming sets expectations for C7+.

---

## § 16 — End of v0.1 DRAFT

Ready for critique. Awaits PROPOSED → LOCKED transition by Ramalingam adjudication.
