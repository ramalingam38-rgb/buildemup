# spec_C14_v0_1_PROPOSED.md

**Component 14 — Connection-Graph Quality Engine**
**Status:** v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication.
**Authored:** S46 (post-C13 v1.0 LOCK)
**Authority chain:** v0.1 PROPOSED → critique walks → v1.0 LOCK
**Lineage:**
- BuildemUp_Component_Validation_Report.md (April 2026): C14 = "Connection-Graph Quick Check" (Locked Decision #1)
- C13 SPEC v1.0 LOCKED v0.6 LOCK-gating requirement: "C14 v0.1 sketch drafted showing AdvisoryFlag consumption + scoring contract surface"
- Academic grounding: Hillier & Hanson 1984 "The Social Logic of Space"; SSPT 2026 (arXiv 2602.22507)

---

## § 0 — Meta + scope boundary

### 0.1 What C14 IS

C14 ingests one batch of `DoorPlacementBatchResult` from C13 (specifically the `successful: tuple[SuccessfulDoorPlacement, ...]` field) and produces, per candidate, a `CirculationGraphReport` carrying:

- **Adjacency graph** — `(rooms = nodes, doors = edges)` per Hillier convention
- **Graph quality metrics** — step-depth, mean depth, relative asymmetry, integration, connectivity, betweenness (per Space Syntax 1984)
- **Quality flags** — transit-through-bedroom, privacy-gradient violation, dead-end isolation (excess depth), bottleneck concentration
- **Aggregated AdvisoryFlag passthrough** — C13's per-door advisories carried forward + augmented with C14's circulation-graph advisories

C14 is **per-candidate** (not per-batch-aggregate). One `CirculationGraphReport` per `SuccessfulDoorPlacement` consumed.

### 0.2 What C14 IS NOT

Tight boundary. C14 does NOT:
- Compute scores (no single number — explicit per Locked Decision #1)
- Rank candidates against each other (that's C17 ranker)
- Apply deep architectural quality checks (that's C15 Layout Problem Finder)
- Modify the underlying layout (read-only consumer)
- Re-verify Inv D13/D17/D11.3' from C13 (those are HARD invariants enforced at C13 Phase F; C14 trusts the prior verification)
- Compute construction cost, room-area adequacy, furniture fit, ventilation, daylight (all C15/C16 territory)
- Optimize or backtrack (purely analytical pass)

If a future change tries to add scoring/optimization/deep-quality to C14, the spec walk must FIRST route the responsibility to C15/C16/C17. C14 stays a fast quick-check that other components consume.

### 0.3 Why "quick check"

Per BuildemUp_Component_Validation_Report.md: "This runs as a quick first filter before the expensive Layout Problem Finder. Layouts that fail basic connectivity are killed early."

C13 already enforces basic connectivity (Inv D13). So what does C14 add as a quick filter? **Quality discriminators on REACHABLE layouts.** Two layouts both pass C13 Phase F, but one has 7-step paths to bedrooms while the other has 3-step paths. C14 surfaces that distinction.

### 0.4 Dependency direction

```
C12 → C13 → C14 → C15 → C17 (ranker) → C18 (renderer)
                  ↘
                  C16 (space auditor, parallel to C15)
```

C14 depends on C13's `SuccessfulDoorPlacement` schema (LOCKED at C13 v1.0). C14 emits a NEW schema (`CirculationGraphReport`) consumed by C15.

C14 has NO read access to C12 internals; everything it needs about geometry comes through C13's Door tuple. C14 has NO read access to C11/below.

### 0.5 Cache scope

C14 cache key composes:
- `c13_cache_key` (input cache key — full key, not split)
- `C14_VERSION`
- `C14_METRIC_VERSION` (bump when metric formulas change semantically even if their NAMES are stable — analog of C13's `C13_EDGE_PROTOCOL_VERSION`)

Per the v0.4-C7 cross-component pipeline convention (mixed-result for pre-v2.0, typestate for v2.0+), C14 is NEW at v2.0 → ships with typestate (`SuccessfulCirculationAnalysis` / `FailedCirculationAnalysis`).

---

## § 1 — Schema (consumed + produced)

### 1.1 Input — what C14 reads from C13

C14 consumes:

```python
# From C13:
SuccessfulDoorPlacement:
  - source_placed_candidate_signature: str
  - doors: tuple[Door, ...]              # primary + secondary
  - advisory_flags: tuple[AdvisoryFlag, ...]
  - geometric_fidelity: GeometricFidelity # APPROXIMATE at v1
  - cache_keys: C13CacheKeys

# Door (per door):
  - room_a_id: str
  - room_b_id: str
  - is_main_entry: bool                  # exactly one per placement
  - is_secondary: bool                   # inferred via Phase A provenance
                                          # — exposed at C14 boundary via
                                          # primary_door_ids frozenset
                                          # threaded by orchestrator
  - ... (axis, position, swing, etc. — ignored by C14 at v0.1)

# Plus (threaded externally — not in Door, but C14 needs it):
  - placed_room_ids: tuple[str, ...]     # canonical room list from C12
  - room_categories: dict[str, str]      # room_id → category
  - main_entry_room_id: str              # which room owns is_main_entry
  - primary_door_ids: frozenset[tuple[str, str]]
                                          # which doors are primaries
                                          # (secondary inferred = NOT in this set)
```

The last block (`placed_room_ids`, `room_categories`, `main_entry_room_id`, `primary_door_ids`) is **upstream metadata** not encoded in the LOCKED C13 schema. C14's orchestrator must accept these as separate parameters — mirroring how C13's Phase F accepts them.

**Backlog item filed**: `B-PROJECT-PIPELINE-METADATA-CONTRACT` (post-LOCK, M) — the recurring pattern of "upstream metadata threaded as separate params" is now visible at C13/C14 and will recur at C15. Worth a project-scope convention.

### 1.2 Output — `CirculationGraphReport`

```python
@dataclass(frozen=True)
class CirculationGraphReport:
    """Per-candidate circulation-graph analysis. Frozen for replay.

    Threaded between C14 and downstream consumers (C15 / C17).
    """
    source_placed_candidate_signature: str

    # ── Graph topology (Hillier permeability graph) ─────────────
    nodes: tuple[str, ...]                          # room_ids, lex-ASC
    edges: tuple[tuple[str, str], ...]              # (room_a, room_b), lex-ASC
    primary_edges: tuple[tuple[str, str], ...]      # subset of edges
                                                     # — for primary-only metrics

    # ── Node-level metrics (per Hillier 1984) ───────────────────
    step_depth_from_entry: tuple[tuple[str, int], ...]
        # (room_id, BFS step-depth from main_entry_room_id), lex-ASC by room_id
    connectivity: tuple[tuple[str, int], ...]
        # (room_id, degree in adjacency graph), lex-ASC by room_id
    betweenness_rank: tuple[tuple[str, int], ...]
        # (room_id, rank 1..n where 1 = most-bottleneck) — see § 2 E5

    # ── Layout-level metrics ───────────────────────────────────
    mean_depth: float                                # average step-depth across rooms
    max_depth: int                                   # deepest room's depth
    relative_asymmetry: float                        # normalized to [0, 1]
    integration: float                               # 1 / RA

    # ── Quality flags emitted by C14 ───────────────────────────
    circulation_flags: tuple[CirculationFlag, ...]   # see § 1.3

    # ── AdvisoryFlag passthrough + augmentation ────────────────
    upstream_advisory_flags: tuple[AdvisoryFlag, ...]
        # exactly C13's tuple, copied unchanged (Inv E8)
    c14_advisory_flags: tuple[AdvisoryFlag, ...]
        # NEW advisories emitted by C14, in the same AdvisoryFlag
        # schema (ADVISORY_SCHEMA_VERSION compatible per Inv E9)

    # ── Provenance ─────────────────────────────────────────────
    c14_version: str
    c14_metric_version: int
    advisory_schema_version: int                    # passed through from C13
```

### 1.3 `CirculationFlag` schema

```python
class CirculationFlagKind(StrEnum):
    TRANSIT_THROUGH_BEDROOM = "transit_through_bedroom"
        # A bedroom is on the shortest path between main_entry and
        # another room — implies family members traverse a private
        # space to reach somewhere else.
    PRIVACY_GRADIENT_VIOLATION = "privacy_gradient_violation"
        # A habitable room (bedroom/master) is SHALLOWER (smaller
        # step-depth) than a public room (living/dining). Violates
        # public→private monotonicity.
    EXCESSIVE_DEPTH = "excessive_depth"
        # A room's step-depth exceeds the configurable threshold
        # (default 5 at v1). Implies overly circuitous access.
    BOTTLENECK_CONCENTRATION = "bottleneck_concentration"
        # A single non-corridor room concentrates betweenness above
        # threshold (default 0.7 normalized at v1). Implies
        # over-reliance on one room as crossing point.
    DEAD_END_ISOLATION = "dead_end_isolation"
        # A room is reachable only via a single non-corridor
        # neighbor (degree-1 path) AND it's habitable.

@dataclass(frozen=True)
class CirculationFlag:
    flag_kind: CirculationFlagKind
    affected_room_id: str
    severity: AdvisorySeverity                     # info/warning/concern
    explanation_template: str                      # consumer-readable
    deduplication_key: str                         # for cap enforcement
    # NOTE: no `category` field at v0.1 — C14 flags are circulation-only.
    # If C14 flags ever need cross-category dispatch, the schema bumps.
```

### 1.4 Why a separate `CirculationFlag` (not reuse C13's `AdvisoryFlag`)?

Considered both. Decision: **separate** at v0.1, with **structural compatibility** for future merging.

Reasoning:
- C13's `AdvisoryFlag.flag_kind` is a `Literal[...]` over 6 LOCKED kinds. Extending it would require an `ADVISORY_SCHEMA_VERSION` bump at C13 — breaking the v1.0 LOCK.
- C14's flag kinds are categorically different (circulation/graph) from C13's (geometric/safety).
- Keeping them separate at v0.1 preserves the C13 LOCK and lets C14 evolve independently.
- The `c14_advisory_flags` field in `CirculationGraphReport` is *typed as `AdvisoryFlag`* (C13's type) — the C14 advisories are CirculationFlag *converted into* AdvisoryFlag at emission. This gives downstream consumers (C15) a uniform `tuple[AdvisoryFlag, ...]` to consume without knowing whether a flag came from C13 or C14.

Backlog filed: `B-PROJECT-ADVISORY-UNIFICATION` (post-LOCK, L) — eventually fold C14 + C15 + C16 advisories into a single registry with versioned categories.

---

## § 2 — Invariants

C14 invariants use prefix **E** (for "Evaluation/Edge-graph") to distinguish from C13's D.

| ID | Description |
|---|---|
| E1 | Every input `SuccessfulDoorPlacement` produces exactly one `CirculationGraphReport`. |
| E2 | `CirculationGraphReport.nodes` = sorted `placed_room_ids`. No additions, no omissions. |
| E3 | `CirculationGraphReport.edges` = sorted `(d.room_a_id, d.room_b_id)` for d in doors, EXCLUDING edges where `room_b_id == "EXTERNAL"` (external envelope doors are NOT graph edges — they're entry points, not internal connections). |
| E4 | `primary_edges ⊆ edges`. |
| E5 | All node-level metric tuples (`step_depth_from_entry`, `connectivity`, `betweenness_rank`) cover exactly `placed_room_ids` (no extra, no missing). Sort lex-ASC by room_id. |
| E6 | `step_depth_from_entry[main_entry_room_id] == 0`. |
| E7 | **Byte-equal replay determinism.** Same `SuccessfulDoorPlacement` + same metadata → identical `CirculationGraphReport`. BFS uses lex-ASC neighbour ordering (same convention as C13 Phase F). Same Inv as C13 D7. |
| E8 | `upstream_advisory_flags == input.advisory_flags` (byte-identical tuple — C14 does NOT mutate C13's output). |
| E9 | All emitted `c14_advisory_flags` conform to the current `ADVISORY_SCHEMA_VERSION` from C13. C14 does NOT bump this version. |
| E10 | `mean_depth ≤ max_depth ≤ len(nodes) - 1`. Sanity bound. |
| E11 | `relative_asymmetry ∈ [0, 1]`. Per Hillier formula `RA = 2(MD - 1) / (k - 2)`, normalized. |
| E12 | `integration ∈ [1, ∞)` (= 1/RA when RA > 0; defined as `∞` symbolically as `float("inf")` when RA == 0 — single-node degenerate). |
| E13 | **Circulation flag density bounded.** `len(circulation_flags) ≤ len(nodes) × C14_FLAG_DENSITY_FACTOR`. Default factor 0.75 at v1. |
| E14 | **Read-only consumer.** No field of any input object mutated. Equivalent to C13 Inv D22 for Phase F. |
| E15 | **Graph-correctness invariant.** If `len(nodes) > 1`, every node has at least one edge (follows from C13 Inv D13 which C14 trusts). |
| E16 | **Provenance triple stability.** `(c14_version, c14_metric_version, advisory_schema_version)` populated, non-empty/non-negative, advisory_schema_version equals input C13 version. |

---

## § 3 — Phases

C14's algorithmic structure mirrors C13 Phase F's pattern: a small number of pure passes, each producing one section of the result. No mutation, no backtracking, no optimization.

### Phase α — Graph construction
- From `doors`, build node set (placed_room_ids), edge set (excluding EXTERNAL), primary edge subset.
- Pure. Returns `(nodes, edges, primary_edges)`.

### Phase β — Node-level metrics
- BFS from `main_entry_room_id` → `step_depth_from_entry`
- Count each node's neighbors → `connectivity`
- Betweenness (lightweight v1 formula — see § 3.5) → `betweenness_rank`

### Phase γ — Layout-level metrics
- `mean_depth = sum(step_depths) / (k - 1)` where k = len(nodes)
- `max_depth = max(step_depths)`
- `relative_asymmetry = 2(mean_depth - 1) / (k - 2)` for k > 2, else 0.0
- `integration = 1 / RA` (or `inf` if RA == 0)

### Phase δ — Quality-flag emission
- Iterate `CirculationFlagKind` checks in fixed order (replay-deterministic).
- Each emits zero or more `CirculationFlag` records.
- Density bounded per Inv E13.

### Phase ε — Advisory passthrough + conversion
- Copy `upstream_advisory_flags` byte-identically (Inv E8).
- Convert C14's `CirculationFlag` records to `AdvisoryFlag` (per Inv E9 schema-compatible).
- Stamp final `c14_advisory_flags` tuple.

### Phase ζ — Report assembly
- Build `CirculationGraphReport` with canonical sorts (Inv E2, E3, E5).
- Stamp provenance triple (Inv E16).

### § 3.5 — Betweenness formula at v0.1

Full Brandes-style betweenness is O(VE) — borderline at large room counts but tractable for residential (n ≤ 15 typical). For v0.1, propose:

```
betweenness_rank(R) = (# of shortest paths between distinct (A, B) pairs
                        that pass through R) / (total shortest paths)
```

Computed via running Brandes from each node, summing through-counts. v0.1 commits to the RANK (1..k) being deterministic and lex-stable on ties, not to the exact value formula. v0.2 critique walk should refine the formula.

Backlog filed: `B-C14-BETWEENNESS-FORMULA-LOCK` (v1.0-LOCK-MANDATORY, S effort).

---

## § 4 — Errors

C14 error hierarchy mirrors C13's two-tier:

- `CirculationAnalysisError` — base
- `LocalCirculationError` — always halts (config errors, schema drift from C13)
  - `UpstreamSchemaDriftError` — C13 output doesn't match expected schema
  - `C14ConfigurationError` — bad config (negative threshold etc.)
- `PerCandidateCirculationError` — strict-mode raise OR WARN-mode collect
  - `EntryRoomNotFoundError` — main_entry_room_id not in placed_room_ids (defensive — C13 already validates this)
  - `GraphInconsistencyError` — derived graph violates basic structural invariant (e.g., edge references unknown room_id) — defensive against C13 contract drift

No NBC-style vetoes at C14 — those live at C13.

---

## § 5 — Failure modes (strict vs WARN)

Same pattern as C13:

- `strict_mode=True` → `PerCandidateCirculationError` raises immediately, batch halts.
- `strict_mode=False` (WARN) → error caught, packaged into `FailedCirculationAnalysis(source_signature, failure_record, partial_report)`, batch continues.

`LocalCirculationError` always halts regardless of mode.

Typestate output:
- `SuccessfulCirculationAnalysis` — carries `CirculationGraphReport`
- `FailedCirculationAnalysis` — carries `FailureRecord` + optional partial report

`CirculationAnalysisBatchResult` parallels `DoorPlacementBatchResult`.

---

## § 6 — Performance budget

Per-candidate: ≤ 0.5s for n ≤ 15 rooms. BFS is O(V+E) = O(n²) worst case for dense graphs but residential graphs are sparse (typical 1-3 edges per room). Brandes betweenness is O(VE) ≈ O(n³); for n ≤ 15 this is < 4000 ops.

Per-batch (50 candidates): ≤ 5s wallclock total.

Configurable budget via `CirculationConfig.per_candidate_wallclock_seconds`.

---

## § 7 — Testing strategy

Mirroring the C13 pattern that LOCKED in v1.0:

- **Foundational layer**: dataclass validation, schema canonical sorts, frozen/hashable. Target: 40 tests.
- **Phase-by-phase units**: graph construction / node metrics / layout metrics / flag emission / advisory passthrough. Target: 30 tests.
- **Orchestrator + provenance**: end-to-end + WARN/STRICT dispatch + version threading. Target: 20 tests.
- **PBT**: ≥15 PBTs covering E1-E16 invariants + adversarial generators (sparse-edge, dense-edge, single-room degenerate).
- **Adversarial integration corpus**: pipe REAL C13 outputs through REAL C14 for the 7 scenarios already in C13's corpus. Target: 11 tests mirroring C13's corpus pattern.

Total target: **≥ 116 tests** at v1.0 LOCK.

---

## § 8 — Cache keys

```python
@dataclass(frozen=True)
class C14CacheKeys:
    c13_cache_key: str                # passthrough
    metric_cache_key: str             # hash(c13_cache_key + C14_VERSION
                                      #       + C14_METRIC_VERSION
                                      #       + config-relevant fields)
    full_cache_key: str               # same as metric_cache_key at v0.1
                                      #  — split deferred to v2.0 if/when
                                      #    C14 produces non-metric outputs
```

Per Inv D18-analog (C14 version): geometry-cache invalidation in C13 propagates to C14 via `c13_cache_key` change. Advisory-cache change in C13 ALSO propagates (because at C14, advisory + geometry are bundled — `full_cache_key` only).

Backlog: `B-C14-CACHE-SPLIT-IF-DIVERGENT` (post-LOCK, M) — split into geometry/advisory only if a real use case for divergent invalidation emerges.

---

## § 9 — Telemetry

Light at v1. Three event types proposed:

```python
@dataclass(frozen=True)
class GraphConstructionEvent:
    candidate_signature: str
    n_nodes: int
    n_edges: int
    n_primary_edges: int

@dataclass(frozen=True)
class CirculationFlagEmittedEvent:
    candidate_signature: str
    flag_kind: CirculationFlagKind
    affected_room_id: str
    severity: AdvisorySeverity

@dataclass(frozen=True)
class CirculationAnalysisCompleteEvent:
    candidate_signature: str
    success: bool
    n_flags_total: int                 # upstream + c14 combined
    wallclock_seconds: float
    mean_depth: float
    max_depth: int
```

`C14TelemetrySink` Protocol + `NullTelemetrySink` + `InMemoryTelemetrySink` — mirror C13's pattern.

No mandatory day-1 event analogous to `PhaseDConvergenceEvent` — C14 has no convergence/optimization. If C15 needs operational signals from C14 later, those can be added without bumping `C14_VERSION` (telemetry is cache-irrelevant per C13 precedent).

---

## § 10 — Provenance

Same pattern as C13 `place_doors_with_provenance`:

```python
def analyze_circulation_with_provenance(
    *,
    batch: DoorPlacementBatchResult,
    placed_room_metadata: dict[str, RoomMetadata],   # threaded
    config: CirculationConfig,
) -> tuple[CirculationAnalysisBatchResult, CirculationAnalysisProvenance]:
    ...
```

Provenance carries: per-candidate wallclock, phase reached, success/failure outcome, flag counts. Inv: wallclock not replay-deterministic; structural fields are.

---

## § 11 — Public API

```python
def analyze_circulation(
    *,
    batch: DoorPlacementBatchResult,
    placed_room_metadata: dict[str, RoomMetadata],
    config: CirculationConfig,
) -> CirculationAnalysisBatchResult:
    """Standard entry. Returns batch result with successful + failed tuples."""
    ...

def analyze_circulation_with_provenance(...) -> tuple[...]:
    """Entry with provenance."""
    ...
```

`RoomMetadata` is a simple struct carrying `(room_id, category, is_main_entry_room, is_primary_door_set)` per room — the "upstream metadata" pattern from § 1.1.

---

## § 12 — Backlog (existing + new from this spec)

### New backlog items C14 v0.1 creates

| ID | Description | Trigger | S{N}-scope | Effort |
|---|---|---|---|---|
| B-PROJECT-PIPELINE-METADATA-CONTRACT | Project-scope convention for "upstream metadata threaded as params" (recurs at C13, C14, C15) | post-LOCK | v2.x project | M |
| B-PROJECT-ADVISORY-UNIFICATION | Fold C14 + C15 + C16 advisories into single versioned registry | post-LOCK | v2.x project | L |
| B-C14-BETWEENNESS-FORMULA-LOCK | Pin exact betweenness formula at v1.0 LOCK | v1.0-LOCK-MANDATORY | C14 v1.0 | S |
| B-C14-CACHE-SPLIT-IF-DIVERGENT | Split full_cache_key into geometry/advisory only if divergent invalidation use case emerges | post-LOCK | C14 v1.x | M |
| B-C14-ISOVIST-SUPPORT | Add sight-line / isovist analysis (currently out of scope at v0.1) | when C15/C18 needs sight-line data | C14 v1.x | M |
| B-C14-PRIVACY-GRADIENT-FORMULA-LOCK | Pin exact privacy-gradient monotonicity formula at v1.0 LOCK | v1.0-LOCK-MANDATORY | C14 v1.0 | S |
| B-C14-TRANSIT-BEDROOM-DEFINITION-LOCK | Pin the "bedroom is transit" formal definition (BFS shortest path? betweenness threshold?) | v1.0-LOCK-MANDATORY | C14 v1.0 | S |

### Routed amendments needed

| ID | Description | Routes to |
|---|---|---|
| (none at v0.1) | — | — |

C13's LOCKED schema is sufficient for C14 input; no C13 amendment needed. If a future C14 critique walk surfaces that some C13 field is needed but missing (e.g., `axis` for sight-line direction), it would route through B-C13-FUTURE-AMENDMENT during C13's 90-day fast-revision window.

### Spec § 12 summary

**Total new backlog: 7. 0 amendments routed. 3 LOCK-mandatory.**

---

## § 13 — End-to-end examples (LOCK precondition per v0.6)

Per v0.6 LOCK gating for C13: "End-to-end example flows documented (C12 → C13 → C14 → C15) for at least 3 representative layouts."

### Example 1 — Compact 2-room (entry + bedroom)

**C12 output**: 1 PlacedCandidate, 2 rooms, 1 shared edge (entry-bedroom).

**C13 output**: SuccessfulDoorPlacement with 1 door (entry-bedroom, is_main_entry=True).

**C14 input**: 1 successful placement; metadata: main_entry_room_id="AAA_entry", primary_door_ids={("AAA_entry", "bedroom_01")}, placed_room_ids=("AAA_entry", "bedroom_01"), room_categories={"AAA_entry": "main_entrance", "bedroom_01": "bedroom"}.

**C14 output (proposed shape)**:
```
CirculationGraphReport:
  nodes = ("AAA_entry", "bedroom_01")
  edges = (("AAA_entry", "bedroom_01"),)
  primary_edges = (("AAA_entry", "bedroom_01"),)
  step_depth_from_entry = (("AAA_entry", 0), ("bedroom_01", 1))
  connectivity = (("AAA_entry", 1), ("bedroom_01", 1))
  betweenness_rank = (("AAA_entry", 1), ("bedroom_01", 2))
  mean_depth = 1.0
  max_depth = 1
  relative_asymmetry = 0.0   # degenerate k=2 case → 0
  integration = inf          # symbolic, RA == 0
  circulation_flags = ()     # no flags — too small for any rule to fire
  upstream_advisory_flags = ()       # C13 had none
  c14_advisory_flags = ()
```

**C15 input** (sketched, since C15 doesn't exist): consumes the full report, runs 30+ deep architectural checks (e.g., "bedroom on external wall?", "bathroom near bedroom?"). For 2-room, most checks N/A.

### Example 2 — Standard 4-room (entry + living + kitchen + bedroom)

**C12 output**: 1 PlacedCandidate, 4 rooms. INTEGRATION CONSTRAINT noted in C13 corpus: real C12 currently produces 0 shared edges at this size — that's a C12-side issue (B-C12-EDGE-DENSITY filed). For the spec example, ASSUME C12 produces a hub-and-spoke layout with entry-living + living-kitchen + living-bedroom (3 edges, living is the hub).

**C13 output**: SuccessfulDoorPlacement with 3 doors; entry-living is is_main_entry.

**C14 input metadata**: 4 rooms, 3 primary doors, entry=AAA_entry.

**C14 output (proposed)**:
```
nodes = ("AAA_entry", "bedroom_01", "kitchen_01", "living_01")
edges = ( ("AAA_entry","living_01"), ("bedroom_01","living_01"),
          ("kitchen_01","living_01") )
step_depth_from_entry = (
    ("AAA_entry", 0),
    ("bedroom_01", 2),    # entry → living → bedroom
    ("kitchen_01", 2),
    ("living_01", 1),
)
connectivity = (("AAA_entry", 1), ("bedroom_01", 1),
                ("kitchen_01", 1), ("living_01", 3))
betweenness_rank = (("living_01", 1), ...)  # living = bottleneck
mean_depth = (0+2+2+1)/3 = 1.67
max_depth = 2
relative_asymmetry = 2(1.67-1)/(4-2) = 0.67
integration = 1/0.67 = 1.49
circulation_flags = ( ... maybe BOTTLENECK_CONCENTRATION on living_01
                          if betweenness > 0.7 threshold ... )
```

**C15 input**: receives the report. Runs deeper analysis — e.g., "is the living-as-hub topology appropriate for family size?" — using the betweenness signal C14 surfaced.

### Example 3 — Multi-floor with shared vertical stack

**C12 output**: MultiFloorPlacementBatchResult with GF + FF candidates, shared bathroom stack at vertical core.

**C13 output**: TWO SuccessfulDoorPlacements (one per floor). Each floor's main_entry differs — GF has the building entry; FF has stair-landing as floor-entry.

**C14 input**: orchestrator processes each floor's SuccessfulDoorPlacement independently. C14 v0.1 does NOT do cross-floor circulation analysis (each floor's graph is independent at v0.1).

**C14 output**: TWO CirculationGraphReports. The GF report includes the staircase as a node (connectivity 2: living + landing). The FF report uses the landing as its main_entry_room_id.

**Backlog filed**: `B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS` (post-v1.0, L) — eventually compute vertical-circulation metrics (e.g., "step-depth from building entry to FF master bedroom INCLUDING the stair traversal"). Out of scope at v0.1.

**C15 input**: Receives both reports. Can compute multi-floor problems (e.g., "is FF master bedroom too far from GF main entry?") by combining the two graphs externally.

---

## § 14 — LOCK readiness

**Architectural maturity at v0.1 PROPOSED**: SKETCH. Sufficient to validate the C13/C14 boundary for the C13 LOCK precondition. NOT sufficient for C14 LOCK — that requires:

1. ⏳ Critique walks #1-N to refine metrics (formulas, thresholds, flag definitions)
2. ⏳ Betweenness / privacy-gradient / transit-bedroom formula LOCK (3 B-NNN items above)
3. ⏳ C14 LOCK gating analog to C13's v0.6 — likely "C15 v0.1 sketch + C14↔C15 boundary validation walk"
4. ⏳ Adversarial integration corpus C14-specific

**Empirical maturity**: ZERO. C14 has not been built. (Same starting position as C13 at its v0.1 PROPOSED.)

**Recommendation**: present v0.1 PROPOSED for Ramalingam adjudication. Anticipated path:
- (a) Lock v0.1 sketch quickly to unblock C13 LOCK precondition (the v0.6 gating only requires "sketch", not "fully spec'd")
- (b) OR continue walks before any LOCK — but this risks Pattern E (scope-creep-mid-build)

Suggest path (a) with a clear understanding that v0.1 LOCK = "the SKETCH is locked", not "the full spec is locked". v0.2+ then refines under the same fast-revision window pattern C13 used.

---

**END OF v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication.**
