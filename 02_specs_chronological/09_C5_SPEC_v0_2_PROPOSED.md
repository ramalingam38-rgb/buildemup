# BuildemUp Component 5 (Topology Selector) — SPEC v0.2 PROPOSED

**Status:** **v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication.** Per Rule 8, this version is not LOCKED until Ramalingam explicitly says "lock it" / "v0.2 LOCKED".

**Generated:** S29, immediately after C5 v0.1 DRAFT and DRAFT-Q adjudication.

**Adjudication received** (Ramalingam: "We will go as per your recommendation"):

| Q | Decision | Notes |
|---|---|---|
| 1 | `buildemup/domain/floor_brief.py` | FloorRoomBrief is a domain concept |
| 2 | DEFERRED — architecture-doc thresholds carried; B-090 filed if recalibration needed | Cannot recalibrate without empirical data |
| 3 | Metric internal; comments may mention ft for traceability | Consistent with C4 v1.0 sqm-canonical |
| 4 | Starting weights from § 4.2 table; tune via critique cycles | No pre-empirical calibration |
| 5 | One default zone-band assignment + B-091 (climate-variant bands) | Avoid Pattern E scope creep |
| 6 | Tie: Δ ≤ 0.10 → 2 candidates; Δ ≤ 0.15 → 3 | Defaults; critique-revisable |
| 7 | All-candidates-fail → hard `RuntimeError` | Consistent with C4 fail-fast |
| 8 | Pull `now` from `plot_analysis.provenance.derived_at` | Avoid duplicate state |

This v0.2 supersedes v0.1 DRAFT with all 8 adjudications applied. Web research and code-grep continue per Rule 7.

---

## § 0 — Pushback table (carried from v0.1 + critique-anticipation)

| Anticipated objection | Pushback |
|---|---|
| "Why generate-and-rank, not pure ML (House-GAN)?" | Rule-based generate-and-rank is interpretable, debuggable, no training data needed. ML is **B-085** (deferred). House-GAN literature confirms generate-and-rank is the correct paradigm at the topology level — the ML adds value at the room-mask level, not the bubble-diagram level. |
| "Why only 4 topologies?" | Architecture doc § C5 names exactly 4. Adding more before seeing real-plot output = premature. New topologies = **B-086** when a real plot fails to fit any of the 4. |
| "Why decision-table, not learned?" | Same as above + sample size: India residential corpus too small for ML at v1. |
| "Why does C5 only return candidates, not placed rooms?" | Separation of concerns. C5 = topology only. Pipeline: C5 → C6 (orientation) → C7 (already shipped) → C8 (corridor) → C9 (placement). |
| "Why pull `now` from PlotAnalysis.provenance.derived_at instead of accepting it?" | C4 already establishes the "compute time" for the pipeline run. C5 producing a different `now` would lie about the pipeline's logical clock. Pull, don't duplicate. |
| "Why metric internal when architecture doc speaks ft?" | Code-grep: C4 v1.0 made sqm canonical. C5 must agree. Comments may cite ft for architecture-doc traceability. |

---

## § 1 — Purpose

Given a `PlotAnalysis` (C4 output) and a `FloorRoomBrief`, return 1–3 ranked **topology candidates** for the floor — *before any room is placed*. Each candidate fully describes:

- Topology kind (Strip / Central Spine / L-shape / Courtyard)
- Zone-band assignments (compass direction → functional band)
- Corridor footprint sketch (position + nominal width; refined by C8)
- Score against the brief (suitability, with per-criterion breakdown)
- Provenance (links back to the PlotAnalysis trace_id)

C5 is the **first topology-aware component in the pipeline**. The architecture doc identifies C5 as ★ critical because past engine iterations placed rooms before deciding topology — producing wasted-corridor layouts. C5 fixes this by deciding topology first.

**Out of scope:** setbacks (C2 shipped), structural grid (C7 shipped), corridor full geometry (C8), room placement (C9), door placement (C10).

---

## § 2 — Input contract

```python
def select_topology(
    plot_analysis: PlotAnalysis,
    room_brief: FloorRoomBrief,
) -> tuple[TopologyCandidate, ...]:      # 1-3 candidates, score-ordered descending
    ...
```

### `PlotAnalysis` (already locked at C4 v1.0)

C5 reads the following fields. C5 MUST NOT re-derive any of them from raw `plot.*`:

- `tier: PlotTier`
- `aspect_ratio: float` — depth/width
- `plot.width_m`, `plot.depth_m` — for decision-table boundary checks (Q3: metric internal)
- `plot.facing: PlotOrientation`
- `plot.plot_type: PlotType`
- `plot.corner_plot: bool`
- `neighbour_context.open_sides: tuple[PlotOrientation, ...]`
- `neighbour_context.corner_assumption: str | None`
- `climate_zone: ClimateZone`
- `provenance.derived_at: float` — pulled into C5's TopologyProvenance per Q8

### `FloorRoomBrief` — domain dataclass per Q1 adjudication

Lives at `buildemup/domain/floor_brief.py` (NEW file).

```python
# buildemup/domain/floor_brief.py
@dataclass(frozen=True)
class FloorRoomBrief:
    """Per-floor room requirements. Multi-floor briefs construct one per floor.

    Domain concept (lives in domain/, not contracts/) — multiple components
    consume it: C5 (topology), C8 (corridor), C9 (placement).
    """
    bedroom_count: int
    bathroom_count: int
    has_kitchen: bool
    has_living: bool
    has_pooja: bool
    has_utility: bool
    other_rooms: tuple[str, ...] = ()        # e.g. ("study", "guest", "balcony")
    floor_label: str = "ground"

    def __post_init__(self) -> None:
        if self.bedroom_count < 0:
            raise ValueError(f"bedroom_count must be >= 0; got {self.bedroom_count}")
        if self.bathroom_count < 0:
            raise ValueError(f"bathroom_count must be >= 0; got {self.bathroom_count}")
```

Code-grep confirmed: no existing `FloorRoomBrief` anywhere upstream. This is a green-field addition.

---

## § 3 — Output contract

```python
@dataclass(frozen=True)
class TopologyCandidate:
    """One ranked topology candidate. Frozen, fully-described."""
    kind: TopologyKind
    score: float                                    # in [0.0, 1.0]; higher is better
    score_breakdown: Mapping[str, float]            # MappingProxyType
    zone_bands: Mapping[ZoneBand, PlotOrientation]  # MappingProxyType
    corridor_sketch: CorridorSketch
    justification: str                              # max 200 chars
    provenance: TopologyProvenance


class TopologyKind(str, Enum):
    STRIP = "strip"
    CENTRAL_SPINE = "central_spine"
    L_SHAPE = "l_shape"
    COURTYARD = "courtyard"


class ZoneBand(str, Enum):
    PUBLIC = "public"        # living, dining, foyer
    SERVICE = "service"      # kitchen, utility, pooja
    CIRCULATION = "circulation"
    PRIVATE = "private"      # bedrooms, attached baths


@dataclass(frozen=True)
class CorridorSketch:
    """Nominal corridor footprint. C8 (Corridor Designer) refines geometry."""
    position: CorridorPosition
    nominal_width_m: float
    runs_along: PlotOrientation


class CorridorPosition(str, Enum):
    NONE = "none"
    CENTRAL = "central"
    PERIMETER = "perimeter"
    L_BENT = "l_bent"


@dataclass(frozen=True)
class TopologyProvenance:
    """Per Q8: pulls derived_at from plot_analysis.provenance — single clock."""
    derived_at: float                            # = plot_analysis.provenance.derived_at
    plot_analysis_trace_id: str                  # = plot_analysis.trace_id
    candidate_decision_table_match: str          # which decision-table branch fired
```

---

## § 4 — Processing layers

### § 4.1 Decision-table candidate selection (per Q3 adjudication: metric internal)

Per architecture doc § C5, but expressed in metric. Threshold values mirror the doc's foot values via standard conversion (1 ft = 0.3048 m exactly; carried to 4 decimal places to avoid rounding drift):

```
# Architecture-doc thresholds expressed in metric (1 ft = 0.3048 m exact):
_WIDE_THRESHOLD_M     = 26 * 0.3048   # =  7.9248 m
_NARROW_THRESHOLD_M   = 22 * 0.3048   # =  6.7056 m
_LARGE_W_THRESHOLD_M  = 40 * 0.3048   # = 12.1920 m
_LARGE_D_THRESHOLD_M  = 60 * 0.3048   # = 18.2880 m

if plot.width_m >= _WIDE_THRESHOLD_M and bedroom_count <= 2:
    candidates = [STRIP]
    branch = "wide_few_bedrooms"
elif plot.width_m < _NARROW_THRESHOLD_M and bedroom_count >= 2:
    candidates = [CENTRAL_SPINE]
    branch = "narrow_many_bedrooms"
elif plot.corner_plot:
    candidates = [L_SHAPE, STRIP]
    branch = "corner"
elif plot.width_m >= _LARGE_W_THRESHOLD_M and plot.depth_m >= _LARGE_D_THRESHOLD_M:
    candidates = [COURTYARD, STRIP]
    branch = "large"
else:
    candidates = [STRIP, CENTRAL_SPINE]
    branch = "default_strip_or_central"
```

The `branch` string lands on `TopologyProvenance.candidate_decision_table_match` for traceability.

**Q2 deferred:** these threshold values come from the architecture doc (Apr 17 session). Empirical recalibration against current Indian-market data is **B-090** (filed below).

### § 4.2 Scoring (per Q4 adjudication: starting weights, tune via critique)

Each candidate is scored on 7 criteria. Final score = weighted sum, clamped to [0.0, 1.0].

| Criterion | Weight | What it measures |
|---|---:|---|
| width_fit | 0.25 | Does plot.width_m comfortably fit this topology's bands? |
| bedroom_fit | 0.20 | Bedroom count ↔ topology capacity (Strip ≤ 2, Central Spine 2-4, etc.) |
| open_side_count | 0.15 | More open sides → courtyard less critical; favours Strip on detached |
| climate_fit | 0.15 | Warm-humid → cross-ventilation → CENTRAL_SPINE / COURTYARD favored |
| corner_fit | 0.10 | corner_plot=True heavily favours L_SHAPE; 0 for non-corner |
| aspect_ratio_fit | 0.10 | aspect_ratio > 1.5 (deep plot) penalizes Strip |
| corridor_overhead | 0.05 | Courtyard has highest corridor cost; lighter topologies score higher |

**Drop threshold:** candidates scoring `< 0.30` are dropped before tie-checking.

**Each criterion maps `plot+brief` → [0.0, 1.0]** with deterministic, documented logic. Detailed scorer functions in `scorers.py`. Tests assert each criterion in [0,1].

### § 4.3 Zone-band assignment per topology (per Q5 adjudication: one default + B-091)

One default mapping per topology — climate-variant overrides deferred to **B-091**. Defaults assume a north-facing plot (the architecture doc's "north to south" baseline); the assignment rotates with `plot.facing` so the relative band positions stay consistent regardless of which side faces the street.

| Topology | Default zone-band assignment (relative to plot.facing) |
|---|---|
| STRIP | front_band=PUBLIC, second=SERVICE, third=CIRCULATION, back=PRIVATE |
| CENTRAL_SPINE | one_flank=(PUBLIC + SERVICE), other_flank=PRIVATE, central_corridor=CIRCULATION |
| L_SHAPE | front_arm=PUBLIC, side_arm=PRIVATE, junction=CIRCULATION |
| COURTYARD | front=PUBLIC, sides=SERVICE+PRIVATE, courtyard=CIRCULATION (open) |

The `compute_plot_facing_sides()` helper (already in C4 schema) translates these relative positions to absolute compass directions per the plot's facing.

### § 4.4 Tie-breaking and 1-3 candidates returned (per Q6 adjudication)

After dropping `score < 0.30`:

1. Sort surviving candidates score-descending.
2. Top candidate always returned.
3. Second candidate returned if `top.score - second.score ≤ 0.10`.
4. Third candidate returned if 2nd was returned AND `top.score - third.score ≤ 0.15`.

If decision-table produced only 1 candidate (e.g., `wide_few_bedrooms` → [STRIP]), exactly 1 is returned. Single-candidate branches don't enter tie-breaking.

### § 4.5 Failure handling (per Q7 adjudication: hard fail)

If all candidates score `< 0.30` after § 4.4 culling:

```python
raise RuntimeError(
    f"no topology fits — likely upstream bug. Plot: {plot.width_m}×{plot.depth_m}m, "
    f"facing={plot.facing.name}, bedrooms={room_brief.bedroom_count}, "
    f"trace_id={plot_analysis.trace_id}. All scores: {dropped_scores}"
)
```

This is consistent with C4's fail-fast philosophy. Fallback to a "Strip with warnings" candidate would silently produce wrong layouts — same anti-pattern v0.9 walk #1 rejected.

---

## § 5 — Module layout

```
buildemup/components/c05/
    __init__.py            # re-exports + (no verify_kb_consistency for C5 yet)
    select.py              # orchestrator: select_topology()
    decision_table.py      # § 4.1 rule-based candidate-set picker
    scorers.py             # § 4.2 per-criterion scoring functions
    zone_bands.py          # § 4.3 default zone-band assignments
    schema.py              # TopologyKind, TopologyCandidate, etc.

buildemup/domain/floor_brief.py     # NEW per Q1 — FloorRoomBrief

buildemup/tests/validation/
    test_c5_select_topology.py
    test_c5_decision_table.py
    test_c5_scorers.py
    test_c5_zone_bands.py
    test_c5_immutability.py
    test_c5_consumes_plot_analysis.py    # already a placeholder; activates when c05/ exists
    test_c5_failure_modes.py
```

Code-grep confirmed: `tests/validation/test_c5_consumes_plot_analysis.py` already exists as a v0.5 module-skipped placeholder. When `c05/__init__.py` lands, it auto-activates.

### Invocation contract

```python
from buildemup.components.c05 import select_topology

# In bridge between C4 (PlotAnalysis) and C6 (Orientation Priority):
candidates = select_topology(plot_analysis, room_brief)
# candidates is a tuple of 1-3 TopologyCandidate objects, score-ordered.
# C6 reads candidates[0]; if len > 1, may also evaluate candidates[1+].
```

No new endpoints, DB tables, or env vars.

---

## § 6 — Failure modes

| Failure | Handling |
|---|---|
| `room_brief.bedroom_count < 0` | `FloorRoomBrief.__post_init__` raises `ValueError` |
| `room_brief.bathroom_count < 0` | `FloorRoomBrief.__post_init__` raises `ValueError` |
| `plot_analysis.shape != PlotShape.RECTANGULAR` | `raise NotImplementedError("v1 supports rectangular only; B-066")` |
| Plot too small (sqft < 600) | Already gated by C3a/C4; C5 trusts upstream |
| All candidates score < 0.30 | `raise RuntimeError(...)` per § 4.5 (Q7) |
| corner_plot with `corner_assumption` non-None | C5 still proceeds; surfaces in justification: "second-street side assumed (B-076)" |
| `plot_analysis.provenance.derived_at <= 0` | Cannot happen — C4 v1.0 validates; defensive type-check only |

---

## § 7 — Test plan (~32 tests)

### Tier 1

```
tests/validation/test_c5_select_topology.py
  - test_strip_chosen_for_wide_plot_with_few_bedrooms
  - test_central_spine_chosen_for_narrow_plot_with_many_bedrooms
  - test_l_shape_offered_for_corner_plot
  - test_courtyard_offered_for_large_plot
  - test_default_branch_yields_strip_and_central_spine
  - test_returns_at_least_one_candidate
  - test_returns_at_most_three_candidates
  - test_candidates_score_ordered_descending
  - test_candidates_are_frozen_immutable
  - test_strip_dropped_for_extreme_aspect_ratio
  - test_warm_humid_climate_favours_cross_ventilation
  - test_provenance_carries_plot_analysis_trace_id
  - test_provenance_derived_at_pulled_from_plot_analysis        [Q8]
  - test_zone_bands_present_for_every_candidate

tests/validation/test_c5_decision_table.py
  - test_wide_plot_few_bedrooms_yields_strip
  - test_narrow_plot_many_bedrooms_yields_central_spine
  - test_corner_yields_l_shape_and_strip
  - test_large_yields_courtyard_and_strip
  - test_ambiguous_yields_strip_and_central_spine
  - test_thresholds_match_architecture_doc                      [Q2]
  - test_branch_string_lands_on_provenance

tests/validation/test_c5_scorers.py
  - test_each_criterion_in_zero_to_one_range
  - test_corner_fit_zero_for_non_corner
  - test_corner_fit_high_for_l_shape_on_corner
  - test_climate_fit_warm_humid_favours_courtyard
  - test_aspect_ratio_fit_penalizes_strip_on_deep_plot

tests/validation/test_c5_zone_bands.py
  - test_strip_default_assignment_relative_to_facing
  - test_central_spine_flanks
  - test_l_shape_assigns_corridor_at_bend
  - test_courtyard_perimeter_assignment

tests/validation/test_c5_immutability.py
  - test_topology_candidate_is_frozen
  - test_score_breakdown_is_mappingproxytype
  - test_zone_bands_is_mappingproxytype

tests/validation/test_c5_failure_modes.py
  - test_all_candidates_below_threshold_raises_runtime_error    [Q7]
  - test_floor_brief_negative_bedrooms_rejected
  - test_floor_brief_negative_bathrooms_rejected

tests/validation/test_c5_consumes_plot_analysis.py (already present; activates)
  - test_c5_does_not_import_plot_directly
  - test_stub_c5_consumer_reads_plot_analysis_without_recomputation
```

### Tier 2: 0 new (C5 is mid-pipeline; no end-to-end flow targets C5 alone).

**Total:** ~32 tests, ~5–8s budget impact.

---

## § 8 — Backlog (filed at v0.2 PROPOSED time per Rule 9.2)

| ID | Description | Trigger |
|---|---|---|
| B-085 | ML-trained scoring (House-GAN-style bubble-diagram refinement) | Corpus of ≥2000 Indian residential plans labelled with topology choice |
| B-086 | Hall-centric, U-shape, T-shape topologies | Real plot fails to fit any of the 4 v1 topologies |
| B-087 | Multi-floor coordination (ground-floor topology constrains first-floor) | 2-floor brief support added |
| B-088 | Vastu integration in zone-band assignment | Customer demand from Tier-2 cities |
| B-089 | User-supplied topology preference (override candidate selection) | Architect-pro tier launch |
| B-090 | Recalibrate decision-table thresholds (currently from Apr-17 session) | Empirical Indian-market data available, OR a real plot fails decision-table mid-design |
| B-091 | Climate-variant zone-band assignments per topology | Layout outcomes diverge across climate zones in user feedback |

7 NEW backlog items filed in C5 lineage.

---

## § 9 — Verification at LOCK time (estimated)

- Tier 1: ~32 tests, ~5–8s budget impact. Within 30s cap.
- Tier 2: 0 new.
- Production code: ~280–380 LOC across 6 files in `components/c05/` + ~25 LOC in `domain/floor_brief.py`.
- Zero edits to shipped code (C1, C2, C3a, C4, C7).

---

## § 10 — Resolved DRAFT-Qs

All 8 DRAFT-Qs from v0.1 adjudicated per Ramalingam recommendation-acceptance:

1. ✓ FloorRoomBrief in `domain/floor_brief.py`
2. ✓ Architecture-doc thresholds carried; B-090 filed
3. ✓ Metric internal
4. ✓ Starting weights from § 4.2; tune via critique
5. ✓ One default zone-band per topology; B-091 filed
6. ✓ Δ ≤ 0.10 / Δ ≤ 0.15 tie thresholds
7. ✓ Hard `RuntimeError` on all-fail
8. ✓ `now` pulled from PlotAnalysis.provenance

---

## § 11 — Spec-amendment expectations

- v0.1 DRAFT (S29 mid-session) → adjudication of DRAFT-Qs
- **v0.2 PROPOSED** (this — S29) — pending Ramalingam LOCK adjudication

Per Rule 8: adjudication-window critiques arriving between PROPOSED and LOCK remain PATCH-eligible — additional concerns produce v0.3 PROPOSED, NOT backlog entries, until Ramalingam locks.

---

## § 12 — Backlog visibility (Rule 9 — full enumeration)

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-085 | ML-trained topology scoring | C5 v0.2 | corpus ≥ 2k labelled plans | OUT (v1) | high |
| B-086 | More topology kinds (U/T/Hall) | C5 v0.2 | real plot fails 4-topology fit | OUT (v1) | medium |
| B-087 | Multi-floor coordination | C5 v0.2 | 2-floor brief support | OUT (v1) | medium |
| B-088 | Vastu zone-band integration | C5 v0.2 | Tier-2 customer demand | OUT (v1) | medium |
| B-089 | User-override topology preference | C5 v0.2 | architect-pro tier | OUT (v1) | low |
| B-090 | Recalibrate decision-table thresholds | C5 v0.2 / Q2 deferred | empirical market data, OR real-plot decision-table failure | OUT (v0.2) | low + data |
| B-091 | Climate-variant zone-band overrides | C5 v0.2 / Q5 deferred | climate-divergent layout outcomes | OUT (v0.2) | medium |

Pre-existing C4 backlog (B-066..B-084) carried unchanged.

---

## § 13 — Status

**v0.2 PROPOSED.** Architecture doc design folded in. All 8 DRAFT-Qs adjudicated. 7 backlog items filed. No code yet (Obligation 1: spec-first).

**Awaiting:** Ramalingam `lock it` → critique round → PATCH cycle → eventual LOCK → code build per D-066.
