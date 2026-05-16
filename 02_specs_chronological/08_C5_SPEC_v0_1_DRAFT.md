# BuildemUp Component 5 (Topology Selector) — SPEC v0.1 DRAFT

**Status:** **v0.1 DRAFT. PENDING Ramalingam review and adjudication of DRAFT-Qs in § 10. NOT a LOCK.**

Per Rule 8: Claude does not self-LOCK. This v0.1 surfaces the design space, web-research findings, code-grep findings, and questions Ramalingam needs to answer before v0.2 PROPOSED.

**Generated:** S29 mid-session, immediately after C4 v1.1 LOCK and C5 transition.

**Source materials:**
- `/mnt/project/BuildemUp_Architecture_v1.md` § "Component 5 — Topology Selector ★ critical" (lines 393–457)
- C4 v1.0 LOCKED — `PlotAnalysis` is the input contract C5 reads from
- Web research: House-GAN++, House-GAN, Finch3D — bubble-diagram + generate-and-rank literature

**Build position:** 6 of 17. Predecessor: C4 (just shipped). Successor: C6 (Orientation Priority Engine).

**Critical-path note from architecture doc:** *"This is the component whose absence caused most of your past frustration. Before any room is placed, the engine decides: what topology should this floor have?"* C5 is marked ★ critical because previous engine iterations placed rooms before deciding topology, producing wasted-corridor layouts. C5 fixes this.

---

## § 0 — Pushback table (anticipated)

| Anticipated objection | Pushback |
|---|---|
| "Why generate-and-rank, not pure ML (House-GAN)?" | Rule-based generate-and-rank is interpretable, debuggable, no training data needed. ML is B-085 (deferred). House-GAN literature confirms the generate-and-rank paradigm is correct. |
| "Why only 4 topologies — not Hall-centric, U-shape, T-shape, etc.?" | Architecture doc § C5 names exactly 4 (Strip / Central Spine / L-shape / Courtyard). Adding more without seeing C5 layout output = premature. New topologies = backlog when a real plot doesn't fit the 4. |
| "Why decision-table, not learned?" | Same answer as above + sample-size: India residential corpus is too small for ML at v1. |
| "Why does C5 only return candidates and not the placed rooms?" | Separation of concerns. C5 picks topology only. Placement = C9. C5 → C6 (orientation) → C7 (already shipped: structural grid) → C8 (corridor) → C9 (placement). |

---

## § 1 — Purpose

Given a `PlotAnalysis` (C4 output) and a list of room requirements, return 1–3 ranked candidate **topologies** for the floor — *before any room is placed*. Each candidate fully describes:
- Topology kind (Strip / Central Spine / L-shape / Courtyard)
- Zone-band assignments (which compass direction holds which functional band)
- Corridor footprint sketch (position + nominal width)
- Score against the brief (suitability, justified)

C5 is the **first topology-aware component in the pipeline**. C6 onward consume ranked candidates and may pass two through if scores tie.

**Out of scope** (deferred to later components or backlog):
- Setbacks (C2, already shipped)
- Structural grid (C7, already shipped)
- Corridor design — full geometry (C8)
- Room placement (C9)
- Door placement (C10)
- Adjacency-graph optimization (C11+)

---

## § 2 — Input contract

C5 reads two inputs:

```python
def select_topology(
    plot_analysis: PlotAnalysis,         # frozen output from C4 v1.0
    room_brief: FloorRoomBrief,          # NEW dataclass to be defined this spec
) -> tuple[TopologyCandidate, ...]:      # 1-3 candidates, score-ordered
```

### `PlotAnalysis` (already locked at C4 v1.0)

C5 reads (does not re-derive):
- `tier: PlotTier` — T1_COMPACT / T2_STANDARD / T3_LARGE
- `aspect_ratio: float` — depth / width
- `plot.width_m`, `plot.depth_m` (defensive read for direct comparison; C5 prefers tier + aspect_ratio)
- `plot.facing: PlotOrientation` — front-of-plot direction
- `plot.plot_type: PlotType` — DETACHED / SEMI_DETACHED / CONTINUOUS
- `plot.corner_plot: bool` — needed for L-shape candidate eligibility
- `neighbour_context.open_sides: tuple[PlotOrientation, ...]` — façade openness
- `neighbour_context.corner_assumption: str | None` — surfaces v1 LEFT default
- `climate_zone: ClimateZone` — drives orientation preferences in C6, but C5 still reads for topology bias (e.g., warm-humid prefers cross-ventilation → courtyard or central spine)
- `sun_path` — already present; C6 owns the orientation logic but C5 may use latitude band as a tie-breaker

### `FloorRoomBrief` — DRAFT shape (DRAFT-Q 1)

```python
@dataclass(frozen=True)
class FloorRoomBrief:
    """Per-floor room requirements. Multi-floor briefs construct one per floor."""
    bedroom_count: int
    bathroom_count: int
    has_kitchen: bool                              # ground floor only typically
    has_living: bool                               # ground floor only typically
    has_pooja: bool                                # cultural — common in Indian residential
    has_utility: bool                              # ground floor service area
    other_rooms: tuple[str, ...] = ()              # e.g. ("study", "guest", "balcony")
    floor_label: str = "ground"                    # for multi-floor disambiguation
```

This dataclass does NOT exist upstream (code-grep confirmed: no `FloorRoomBrief` anywhere in `domain/` or `contracts/`). DRAFT-Q 1 covers where it lands.

---

## § 3 — Output contract

```python
@dataclass(frozen=True)
class TopologyCandidate:
    """One ranked topology candidate. Frozen, fully-described."""
    kind: TopologyKind                              # enum: STRIP / CENTRAL_SPINE / L_SHAPE / COURTYARD
    score: float                                    # higher is better; in [0.0, 1.0]
    score_breakdown: Mapping[str, float]            # MappingProxyType — per-criterion scores
    zone_bands: Mapping[ZoneBand, PlotOrientation]  # MappingProxyType — which compass direction holds which functional band
    corridor_sketch: CorridorSketch                 # nominal corridor footprint, refined by C8
    justification: str                              # human-readable why-this-rank, max 200 chars
    provenance: TopologyProvenance


class TopologyKind(str, Enum):
    STRIP = "strip"                # Public band → service → circulation → private, perpendicular to street
    CENTRAL_SPINE = "central_spine" # Corridor down the middle, rooms flank both sides
    L_SHAPE = "l_shape"             # Rooms wrap an L-shaped corridor (corner plots)
    COURTYARD = "courtyard"         # Rooms surround a central open space (large plots)


class ZoneBand(str, Enum):
    PUBLIC = "public"      # living, dining, foyer
    SERVICE = "service"    # kitchen, utility, pooja
    CIRCULATION = "circulation"
    PRIVATE = "private"    # bedrooms, attached baths


@dataclass(frozen=True)
class CorridorSketch:
    """Nominal corridor footprint. C8 (Corridor Designer) refines geometry."""
    position: CorridorPosition
    nominal_width_m: float
    runs_along: PlotOrientation       # corridor's long axis (orientation it runs N→S, E→W, etc.)


class CorridorPosition(str, Enum):
    NONE = "none"                # Strip topologies on small T1 plots; rooms accessed directly
    CENTRAL = "central"          # Down the middle (Central Spine)
    PERIMETER = "perimeter"      # Wraps the inside of the building shell (L, Courtyard)
    L_BENT = "l_bent"            # L-shape only


@dataclass(frozen=True)
class TopologyProvenance:
    derived_at: float
    plot_analysis_trace_id: str   # mirrors C4's trace_id for cross-component correlation
    candidate_decision_table_match: str   # which decision-table branch fired
```

---

## § 4 — Processing layers

### § 4.1 Decision-table candidate selection

Per architecture doc § C5, the v1 selector uses a small decision table. DRAFT v0.1 lists the rules from the architecture doc unchanged — DRAFT-Q 2 covers thresholds.

```
plot_w_ft = plot.width_m * 3.28084   # m → ft (we work in metric internally; ft for the rule comments to match the architecture-doc language)

if plot_w_ft >= 26 and bedroom_count <= 2:
    candidates = [STRIP]
elif plot_w_ft < 22 and bedroom_count >= 2:
    candidates = [CENTRAL_SPINE]
elif corner_plot:
    candidates = [L_SHAPE, STRIP]
elif plot_w_ft >= 40 and plot_d_ft >= 60:
    candidates = [COURTYARD, STRIP]
else:
    candidates = [STRIP, CENTRAL_SPINE]   # try both, score, pick winner
```

**DRAFT-Q 3:** confirm the architecture-doc thresholds in feet vs metric. The architecture doc was written when the codebase was sqft-native; C4 v1.0 made sqm canonical. Spec v0.2 should resolve to one or the other consistently.

### § 4.2 Scoring

Each candidate is scored on multiple criteria (DRAFT — actual weights need adjudication):

| Criterion | Weight | What it measures |
|---|---:|---|
| width-fit | 0.25 | Does plot.width_m comfortably fit this topology's bands? |
| bedroom-fit | 0.20 | Does the bedroom count fit one row (Strip), two flanks (Central Spine), or wrap an L? |
| open-side count | 0.15 | More open sides → courtyard becomes less critical; favours Strip on detached plots |
| climate-fit | 0.15 | Warm-humid favours cross-ventilation → Central Spine / Courtyard; Composite zones favour Strip |
| corner-fit | 0.10 | corner_plot=True heavily favours L-shape |
| aspect-ratio-fit | 0.10 | aspect_ratio > 1.5 (deep plot) penalizes Strip |
| corridor-overhead | 0.05 | Courtyard has highest corridor cost (perimeter) |

**DRAFT-Q 4:** weights and any missing criteria.

Final score is the weighted sum, clamped to [0.0, 1.0]. Candidates with score < 0.30 are dropped (an L-shape on a non-corner plot scores 0 on corner-fit and quickly falls below threshold).

### § 4.3 Zone-band assignment per topology

Once a topology is chosen, its bands are assigned to compass directions. The default mapping per the architecture doc is *"Public band → service → circulation → private, north to south"* — but this is climate- and culture-specific. C5 makes a **first-pass** assignment that C6 (Orientation Priority Engine) refines.

DRAFT defaults (subject to DRAFT-Q 5):

| Topology | Default zone-band assignment |
|---|---|
| Strip | front=PUBLIC, second_row=SERVICE, third_row=CIRCULATION, back=PRIVATE |
| Central Spine | flanking E=PUBLIC + SERVICE, flanking W=PRIVATE |
| L-shape | front=PUBLIC, side=PRIVATE, junction=CIRCULATION |
| Courtyard | N+S=PRIVATE, E+W=PUBLIC+SERVICE, courtyard=CIRCULATION |

### § 4.4 1–3 candidates returned

Per architecture doc: *"When two candidates score similarly, both are passed downstream and we end up with two of the three layouts BuildemUp shows the user."* C5 returns 1, 2, or 3 candidates depending on the decision-table branch and the scoring outcome.

Tie criterion (DRAFT-Q 6): scores within 0.10 of the top → both returned. Three returned only if all three are within 0.15 of the top.

---

## § 5 — Module layout (proposed)

```
buildemup/components/c05/
    __init__.py            # re-exports + verify_kb_consistency call (none for C5 yet)
    select.py              # orchestrator: select_topology(plot_analysis, room_brief)
    decision_table.py      # rule-based candidate-set picker (§ 4.1)
    scorers.py             # per-criterion scoring functions (§ 4.2)
    zone_bands.py          # default zone-band assignments (§ 4.3)
    schema.py              # TopologyKind, TopologyCandidate, CorridorSketch, etc.

buildemup/contracts/floor_room_brief.py   # NEW (or domain/ — DRAFT-Q 1)
    FloorRoomBrief dataclass

buildemup/tests/validation/
    test_c5_select_topology.py
    test_c5_decision_table.py
    test_c5_scorers.py
    test_c5_zone_bands.py
    test_c5_immutability.py
    test_c5_consumes_plot_analysis.py    # already a placeholder from C4 v0.5; activates when c05/ exists
```

**Code-grep confirmed:** `tests/validation/test_c5_consumes_plot_analysis.py` already exists as a v0.5 module-skipped placeholder. When `c05/__init__.py` lands, the placeholder unblocks and runs.

---

## § 6 — Failure modes

| Failure | Handling |
|---|---|
| `room_brief.bedroom_count < 0` | `raise ValueError("bedroom_count must be ≥ 0")` |
| `plot_analysis.shape != PlotShape.RECTANGULAR` | `raise NotImplementedError("v1 supports rectangular only; B-066")` |
| Plot too small for any topology (sqft < 600) | Already gated by C3a/C4 — C5 trusts C4's pre-validation |
| All candidates score < 0.30 | `raise RuntimeError("no topology fits — likely upstream bug; report plot details")` (DRAFT-Q 7: hard fail or fallback?) |
| corner_plot with `neighbour_context.corner_assumption` non-None | C5 still proceeds; surfaces in TopologyCandidate.justification that "second-street side is assumed (B-076)" |

---

## § 7 — Test plan (estimated ~30 tests)

```
test_c5_select_topology.py
  - test_strip_chosen_for_wide_plot_with_few_bedrooms
  - test_central_spine_chosen_for_narrow_plot_with_many_bedrooms
  - test_l_shape_offered_for_corner_plot
  - test_courtyard_offered_for_large_plot
  - test_returns_at_least_one_candidate
  - test_returns_at_most_three_candidates
  - test_candidates_are_score_ordered_descending
  - test_candidates_are_frozen_immutable
  - test_strip_dropped_for_extreme_aspect_ratio
  - test_warm_humid_climate_favours_cross_ventilation_topology
  - test_provenance_carries_plot_analysis_trace_id
  - test_zone_bands_present_for_every_candidate

test_c5_decision_table.py
  - test_wide_plot_few_bedrooms_yields_strip
  - test_narrow_plot_many_bedrooms_yields_central_spine
  - test_corner_yields_l_shape_and_strip
  - test_large_yields_courtyard_and_strip
  - test_ambiguous_yields_strip_and_central_spine
  - test_thresholds_match_architecture_doc

test_c5_scorers.py
  - test_each_criterion_in_zero_to_one_range
  - test_corner_fit_zero_for_non_corner
  - test_corner_fit_high_for_l_shape_on_corner
  - test_climate_fit_warm_humid_favours_courtyard

test_c5_zone_bands.py
  - test_strip_default_north_to_south
  - test_central_spine_flanks_e_w
  - test_l_shape_assigns_corridor_at_bend
  - test_courtyard_perimeter_assignment

test_c5_immutability.py
  - test_topology_candidate_is_frozen
  - test_score_breakdown_is_mappingproxytype
  - test_zone_bands_is_mappingproxytype

test_c5_consumes_plot_analysis.py (already present as placeholder; activates)
  - test_c5_does_not_import_plot_directly
  - test_stub_c5_consumer_reads_plot_analysis_without_recomputation
```

---

## § 8 — Backlog candidates (anticipated)

- **B-085** — ML-trained scoring (House-GAN-style bubble-diagram refinement). Trigger: corpus of ≥2000 Indian residential plans labelled with topology choice.
- **B-086** — Hall-centric, U-shape, T-shape topologies. Trigger: a real plot fails to fit any of the 4 v1 topologies.
- **B-087** — Multi-floor coordination (a 2-storey plot's ground-floor topology constrains first-floor topology). Trigger: 2-floor brief support added.
- **B-088** — Vastu integration in zone-band assignment. Trigger: customer demand from Tier 2 cities.
- **B-089** — User-supplied topology preference (override candidate selection). Trigger: architect-pro tier launch.

---

## § 9 — Verification at LOCK time (estimated)

- Tier 1: ~30 tests, ~5–10s budget impact.
- Tier 2: 0 new (no end-to-end flows that hit C5 alone — C5 is mid-pipeline).
- Production code: ~250–350 LOC across 6 files in `components/c05/` + ~30 LOC for `FloorRoomBrief`.
- Zero edits to shipped code (C1, C2, C3a, C7, C4).

---

## § 10 — DRAFT-Qs for Ramalingam adjudication (BEFORE v0.2 PROPOSED)

These need answering before v0.2 PROPOSED can ship.

**DRAFT-Q 1:** Where does `FloorRoomBrief` live?
- (a) `buildemup/contracts/floor_room_brief.py` — alongside other contracts
- (b) `buildemup/domain/floor_brief.py` — alongside `Plot`, `Brief`
- (c) `buildemup/components/c05/schema.py` — local to C5 (then re-exported by C6+)

Recommendation: (b) — it's a domain concept, multiple components consume it. But this is a project-wide convention call.

**DRAFT-Q 2:** Are the architecture-doc decision-table thresholds (26 ft, 22 ft, 40×60 ft) correct, or do they need recalibration against current Indian-market data?

These are from the Apr 17 session in the architecture doc. C4 v1.0 added climate, soil, wind data. C5 v1 should at minimum confirm the thresholds aren't superseded.

**DRAFT-Q 3:** Metric or imperial in code internals?
- Architecture doc speaks in feet (26 ft, 22 ft, 40×60 ft).
- C4 v1.0 made `sqm` canonical (sqft is display-only).
- C5 v1 should pick one for internal comparison; recommend metric (consistent with C4).

**DRAFT-Q 4:** Scoring weights (the `0.25 / 0.20 / 0.15 / 0.15 / 0.10 / 0.10 / 0.05` table in § 4.2). These are draft starting values. Should v0.1 → v0.2 do empirical calibration, or start with these and tune via critique cycles?

**DRAFT-Q 5:** Default zone-band → compass mappings per topology (§ 4.3). The architecture doc says *"north to south"* but that's climate-zone-specific. Should v0.1 include 5 climate-zone variants, or one default + climate-zone overrides as a B-XXX backlog?

**DRAFT-Q 6:** Tie-breaking thresholds. Two candidates within score Δ ≤ 0.10 → both returned. Three within Δ ≤ 0.15 → all three returned. Are these sensible?

**DRAFT-Q 7:** Failure mode when all candidates score < 0.30 — hard `RuntimeError` or fallback to a generic "Strip with warnings" candidate?

**DRAFT-Q 8:** Should `select_topology` accept a `now: float` parameter the way C4's `derive` does (for provenance)? Or pull from `plot_analysis.provenance.derived_at`?

---

## § 11 — Status

**v0.1 DRAFT.** Awaiting Ramalingam adjudication on DRAFT-Qs 1–8 before v0.2 PROPOSED.

Per Rule 8, Claude does not self-LOCK. Per Obligation 1, no C5 code is being written.
