# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v0.9 PROPOSED

**Component**: 10 (canonical Track 3 numbering)
**Status**: v0.9 PROPOSED. **NOT LOCKED** per Ramalingam directive. Supersedes v0.8.
**Authority**: S35 author's draft. PROPOSED, awaiting Ramalingam adjudication.
**Authored**: S35 Walk #8 outcome.
**LOCK BLOCKED on**: C7 amendment v0.7 LOCK declaration.

---

## § 0 — Architectural notes (UNCHANGED from v0.8)

(See v0.8 § 0 — C10 emits constraints/groupings/primitives; not consumer scores; not acoustics; not global optimisation; not hydraulic simulation; not MCS/MUS. Q19 product-onboarding contract; B-236 telemetry. Plumbing code framing per India UPC adoption; B-222 primary-source verification.)

---

## § 1 — Walk-resolved scope (cumulative — 8 walks)

All Q1-Q39 prior + Walk #8 resolutions:

| Q | Final | Walk |
|---|---|---|
| Q1-Q36 | (carried from v0.8) | walks 1-7 |
| Q37 | likely-bound 0.5 factor uniform at v1 | #6 |
| Q38 | fixture_capacity_weights from rough DFU correspondence | #6 |
| Q39 | mutually_exclusive_with exhaustive at v1 | #6 |
| **Q40** (NEW Walk #8) | F-v8-6 cluster-occupancy timing fix: split Phase 0.5 into 0.5a (pre-screen) + 2.5 (authoritative post-merge validation) | #8 |
| **Q41** (NEW Walk #8) | RemediationHint mutex DAG validation: acyclicity invariant + total ordering | #8 |
| **Q42** (NEW Walk #8) | symbolic_bend_estimate routing convention: horizontal-first, lex-ASC anchor wall_id tie-break | #8 |
| **Q43** (NEW Walk #8) | per-fixture likely-bound factors (WC=0.8, lavatory=0.5, shower=0.6, kitchen_sink=0.4) | #8 |
| **Q44** (NEW Walk #8) | Capacity vs scoring naming cleanup: extract `WetZoneCapacityWeights` from `WetZoneScoringWeights` | #8 |

---

## § 2 — Contract (REVISED v0.9 — schema changes for Q41, Q43, Q44)

```python
def plan_wet_zones(...) -> tuple[WetZonePlannedCandidate, ...]:
    """Contract unchanged from v0.8."""
```

### Schema (REVISED v0.9 — 3 schema changes from v0.8)

```python
@dataclass(frozen=True)
class TrapArmEstimate:
    """REVISED v0.9 (Q43): per-fixture likely-bound factors replace uniform 0.5."""
    upper_bound_m: float          # Manhattan worst-case-corner — fail-safe upper bound
    likely_bound_m: float         # Per-fixture factor × upper_bound_m; see Phase 4 below


@dataclass(frozen=True)
class RemediationHint:
    # ... carried from v0.8 ...
    kind: Literal["relax_config","increase_limit","alternative_routing","manual_review"]
    parameter: str
    current_value: Any
    suggested_value: Any
    severity: Literal["low","medium","high"]
    human_readable: str
    retry_priority: int
    mutually_exclusive_with: tuple[str, ...]
    expected_success_probability: float | None


@dataclass(frozen=True)
class WetZoneCapacityWeights:
    """NEW v0.9 (Q44 your call). Extracted from WetZoneScoringWeights.
    Capacity is a feasibility concern (Phase 3 Inv 17), not a scoring concern.
    Naming/placement cleanup per F-v8-2."""
    fixture_capacity_weights: dict[str, float] = field(default_factory=lambda: {
        "water_closet": 2.0, "shower": 1.5, "bathtub": 1.5,
        "lavatory": 1.0, "kitchen_sink": 1.0, "utility_sink": 1.0,
        "floor_drain": 0.5,
    })
    minimum_riser_spacing_m: float = 3.0
    wall_safety_margin_m: float = 0.0       # NEW v0.9: explicit override; defaults to 2 * minimum_riser_spacing_m at use


@dataclass(frozen=True)
class WetZoneScoringWeights:
    """REVISED v0.9 (Q44): capacity weights moved to WetZoneCapacityWeights.
    Scoring weights now strictly about wall ranking quality."""
    weight_engineering: float = 1.0
    weight_cultural: float = 1.0
    weight_adjacency: float = 1.0
    column_alignment_bonus: float = 0.2
    wall_length_sufficiency_bonus: float = 0.1
    wall_reuse_penalty: float = -0.5
    bathroom_axis_preferred: float = 1.0
    bathroom_axis_neutral: float = 0.5
    bathroom_axis_discouraged: float = 0.0
    pooja_axis_preferred: float = 1.0
    pooja_axis_neutral: float = 0.5
    pooja_axis_discouraged: float = 0.0


@dataclass(frozen=True)
class WetZonePlanConfig:
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    pooja_adjacency_mode: Literal["strict", "soft"] = "strict"
    max_risers: int | None = None
    adjacency_threshold_m: float = 0.0
    require_master_bath_adjacency: bool = True
    require_verified_plumbing: bool = False
    scoring_weights: WetZoneScoringWeights = field(default_factory=WetZoneScoringWeights)
    capacity_weights: WetZoneCapacityWeights = field(default_factory=WetZoneCapacityWeights)   # NEW v0.9
    scoring_profile: Literal["vastu_strict","vastu_soft","neutral"] = "neutral"
    max_backtrack_states: int = 100
    max_assignment_attempts: int = 50
    trap_arm_tolerance_m: float = 0.15
    performance_budgets: WetZonePerformanceBudgets = field(default_factory=WetZonePerformanceBudgets)
```

**Other schemas (carried unchanged from v0.8)**: `ForcedCultureOverride`, `WallScoreVector`, `RiserAnchor`, `RiserGroup`, `WetZoneRiskBreakdown`, `WetZonePerformanceBudgets`, `WetZonePlan`, `WetZonePlanProvenance`.

---

## § 3 — Behaviour (REVISED v0.9 — 4 phase revisions)

### Phase 0 — Compute `acceptable_wall_sets` (UNCHANGED from v0.8)

Production code uses `grid.wall_segments_canonical()` per C7 v0.7 W8 enforcement.

### Phase 0.5a — Rough pre-screen (REVISED v0.9 per Q40 / F-v8-6 real-bug fix)

**Was**: Phase 0.5 ran BOTH HARD-edge pairwise check AND cluster-occupancy check before Phase 2 merge — but cluster composition wasn't final yet, so occupancy validation was on intermediate state.

**Is**: Phase 0.5a runs ONLY the rough pre-screen — fast-fail on clearly-impossible HARD-edge incompatibility:

For each HARD-edge pair `(r1, r2)`:
1. Compute `intersection = acceptable_wall_sets[r1] ∩ acceptable_wall_sets[r2]` (memoised).
2. If empty: aggregate all infeasible pairs, raise `WetZoneInfeasibleError(failure_phase="pre_clustering")`.

**Cluster-occupancy check moves to Phase 2.5** (below).

### Phase 1a — Feasibility filter (UNCHANGED from v0.8)

### Phase 1b — Ranking (UNCHANGED from v0.8)

### Phase 2 — Wet-room clustering (UNCHANGED from v0.8)

Common-feasible-wall merge predicate; tie-break by cluster_id lex ASC; converges to final cluster composition.

### Phase 2.5 — Authoritative occupancy validation (NEW v0.9 per Q40 / F-v8-6 real-bug fix)

After Phase 2 merge converges, **before** Phase 3 assignment:

For each final cluster `C` (post-merge):
1. Compute `cluster_occupancy_m = Σ(room.liveability_min_width_m for room_id in C)`.
2. Compute `wall_safety_margin_m = config.capacity_weights.wall_safety_margin_m or 2 * config.capacity_weights.minimum_riser_spacing_m`.
3. For each candidate wall `w` in `intersection(acceptable_wall_sets of all members of C)`:
   - `usable_wall_length_m = w.length_m - wall_safety_margin_m`.
   - Wall is *spatially feasible* for cluster iff `cluster_occupancy_m <= usable_wall_length_m`.
4. If no spatially-feasible wall exists for cluster `C`: raise `WetZoneInfeasibleError(failure_phase="post_clustering_spatial")` with structured `RemediationHint`s.

**This is the F-v8-6 fix.** Occupancy validation now runs against final cluster composition, after merge convergence. The `failure_phase` value renames from `"pre_clustering_spatial"` (v0.8 wrong) to `"post_clustering_spatial"` (v0.9 correct semantic).

Inv 19 retained; semantic now references final cluster composition.

### Phase 3 — Wall assignment (REVISED v0.9 per Q44 — capacity_weights relocated)

```python
cluster_capacity_weight = sum(
    config.capacity_weights.fixture_capacity_weights[fixture_type]   # was: scoring_weights.fixture_capacity_weights
    for room_id in C.wet_room_ids
    for fixture_type in fixture_types_per_room[room_id]
)
wall_capacity = floor(w.length_m / config.capacity_weights.minimum_riser_spacing_m)   # was: scoring_weights.minimum_riser_spacing_m
fits = cluster_capacity_weight <= wall_capacity
```

Logic unchanged; field names relocated from `scoring_weights` to `capacity_weights`.

### Phase 4 — Trap-arm distance (REVISED v0.9 per Q42 + Q43)

**Per-fixture likely-bound factors (NEW v0.9 per Q43)**:

```python
LIKELY_BOUND_FACTORS_BY_FIXTURE: Final[dict[str, float]] = {
    "water_closet": 0.8,    # WCs typically far from anchor (corner placement)
    "lavatory":     0.5,    # Lavatories typically near door (mid-room)
    "shower":       0.6,    # Showers typically corner-placed but closer to anchor than WC
    "bathtub":      0.6,    # Similar to shower
    "kitchen_sink": 0.4,    # Kitchen sinks typically wall-aligned, close to riser
    "utility_sink": 0.4,    # Similar profile to kitchen
    "floor_drain":  0.7,    # Floor drains spread; conservative midpoint
}
```

For each `(room_id, fixture_type)`:
1. **Manhattan worst-case-corner distance** → `upper_bound_m`.
2. **Per-fixture likely bound** → `likely_bound_m = LIKELY_BOUND_FACTORS_BY_FIXTURE[fixture_type] * upper_bound_m`.
3. Validation per Inv 11 dual-bound logic (carried from v0.8).

**Symbolic bend estimate routing convention (NEW v0.9 per Q42)**:

For deterministic replay, v1 routing uses **horizontal-first** orthogonal path:
- From fixture corner `(fx, fy)`, route along x-axis first to `(anchor_x, fy)`, then along y-axis to `(anchor_x, anchor_y)`.
- Tie-break (when multiple anchors equidistant): **lex-ASC of anchor wall_id**.
- Bends counted: 0 if `(fx, fy)` is collinear with anchor on horizontal route; 1 if either `fx == anchor_x` or `fy == anchor_y` (single direction change); 2 in general case.

This makes `symbolic_bend_estimate` reproducible across implementations. Documented for B-233 future routing graph migration.

### Phase 5 — Provenance + risk breakdown (REVISED v0.9 per Q41 — mutex DAG validation)

**RemediationHint mutex graph validation (NEW v0.9 per Q41)**:

After hint generation, before serialisation into provenance:

```python
def validate_remediation_graph(hints: tuple[RemediationHint, ...]) -> None:
    """Validates RemediationHint mutex graph per Q41 + Walk #8 web evidence.

    Invariants:
    - Mutex relationships form a DAG (no cycles)
    - retry_priority + lex(parameter) form deterministic total ordering
    - Equal-priority hints break tie via lex-ASC of `parameter`

    Raises RemediationGraphError if invariants violated.
    """
    # 1. Build mutex graph: nodes = hint parameters, edges = mutually_exclusive_with
    parameters = {h.parameter for h in hints}
    edges = {(h.parameter, exc) for h in hints for exc in h.mutually_exclusive_with
             if exc in parameters}

    # 2. Cycle detection (DFS-based topological-sort failure)
    if has_cycle(parameters, edges):
        raise RemediationGraphError(
            "RemediationHint mutex graph contains cycles; orchestration undefined."
        )

    # 3. Verify deterministic ordering: (retry_priority ASC, parameter lex-ASC)
    sorted_hints = sorted(hints, key=lambda h: (h.retry_priority, h.parameter))
    # Same order every time = deterministic; verified by replay snapshots.
```

Mutex graph cycle detection enforces the invariant before hints reach the orchestrator. Web evidence backs the DAG-acyclicity discipline as standard for retry orchestration.

If validation fails → raise systemic `RemediationGraphError` (new error class). This is a Phase-5 internal-consistency check; if it fires, it's a C10 implementation bug, not a per-candidate input issue.

**Risk breakdown weighted-severity** (carried from v0.7 — 0.5/1.0/1.5 weights). **Performance budget warnings** (carried from v0.7). **`_observational_runtime_ms`** (carried from v0.7 — non-deterministic, observational).

---

## § 4 — Invariants (REVISED v0.9 — Inv 19 semantic update + Inv 21 NEW)

| # | Invariant | Mode |
|---|---|---|
| 1-18 | (carried from v0.8) | RAISE/WARN per mode |
| **19 (REVISED v0.9 per Q40)** | **For every FINAL cluster `C` (post-Phase-2 merge convergence) assigned to wall `w`: `Σ(room.liveability_min_width_m for room_id in C) <= w.length_m - wall_safety_margin_m`. Validated in Phase 2.5, not Phase 0.5.** | RAISE |
| 20 | `bend_estimation_mode` is a Literal[...] enum value matching the algorithm version | RAISE |
| **21 (NEW v0.9 per Q41)** | **`provenance.remediation_hints` mutex graph is a DAG (no cycles); `retry_priority` + parameter lex form a total ordering. Validated by `validate_remediation_graph()` in Phase 5.** | RAISE-as-RemediationGraphError |

(Inv 1-18 carried verbatim from v0.8.)

---

## § 5 — Failure modes (REVISED v0.9 — added RemediationGraphError + failure_phase rename)

```
WetZonePlanError [carries remediation_hints + failure_phase]
├── PerCandidateError
│   ├── WetZoneInfeasibleError (consolidated)
│   │   └── PreClusteringInfeasibleError
│   │       (failure_phase ∈ {"pre_clustering",
│   │                         "post_clustering_spatial",      # RENAMED v0.9 (was "pre_clustering_spatial" in v0.8)
│   │                         "assignment"})
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError
│   ├── WallCapacityExceededError
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow                             (systemic)
├── KBVersionMismatchError                               (startup-time)
└── RemediationGraphError                                (NEW v0.9 — systemic, Phase 5 mutex-graph cycle detection)
```

---

## § 6 — Test coverage requirements (REVISED v0.9)

Target ~175 tests (was 165 in v0.8; +10 for v0.9 features):

- ~36 schema tests (TrapArmEstimate per-fixture factors, RemediationHint with retry fields, WetZoneCapacityWeights extracted, WetZoneScoringWeights cleanup)
- ~42 invariant tests (Inv 1-21; Inv 19 semantic update + Inv 21 mutex DAG)
- ~46 phase-logic tests (Phase 0 with canonical accessor, Phase 0.5a fast-fail, Phase 2.5 post-merge occupancy, Phase 1a/1b, Phase 2 merge, Phase 3 backtracking + interim weighting + capacity_weights relocation, Phase 4 dual-bound + horizontal-first routing convention + per-fixture factors, Phase 5 mutex DAG validation)
- ~24 partial-batch tolerance tests
- ~10 STRICT-mode escalation tests
- ~12 deterministic-replay snapshot tests (uses canonical_serialize from buildemup.utilities; excludes _observational_runtime_ms)
- ~5 KB cross-validator tests

Cumulative baseline target at C10 ship: 2155 + 175 ≈ **2330 passed**.

---

## § 7 — Open questions surfaced at v0.9

**Q45 (NEW v0.9)**: `LIKELY_BOUND_FACTORS_BY_FIXTURE` lives as `Final[dict]` constant in C10 module. Should it move to `kb/plumbing_minimums.json` as a per-fixture field (`likely_bound_factor: float`)? Tighter co-location with trap-arm data; KB owns engineering parameters.
- **Recommendation**: move to KB in v1.0 / future calibration cycle. v0.9 keeps as module constant for proximity to Phase 4 logic. **File as B-246** if not addressed at LOCK.

**Q46 (NEW v0.9)**: `validate_remediation_graph()` runs once per Phase 5. Cost is small (typically 5-10 hints); cycle detection is O(N+E). But should validation also run on inputs (someone could construct a `WetZonePlanProvenance` with cyclic hints externally)?
- **Recommendation**: yes — validate in `WetZonePlanProvenance.__post_init__` too. Defensive depth. Bake into v0.9 schema implementation.

---

## § 8 — Backlog at v0.9 (UPDATED v0.9)

Carried open: B-212 (BLOCKER, expected to clear), B-213, B-214, B-215, B-216, B-217 (updated), B-219, B-220, B-222, B-223, B-224, B-225, B-226, B-227, B-228, B-229 (updated), B-230, B-231, B-232 (updated), B-233, B-234a/b, B-235, B-236, B-237, B-238.

**Newly filed at Walk #8 walk-triage**:
- **B-241**: CI lint rule for `.wall_segments` direct iteration (post v1)
- **B-242**: `WallSegment.usable_wall_spans` for fragmentation modeling (post v1)
- **B-243**: IMPLEMENTED-IN-SPEC at v0.9 (mutex DAG validation via `validate_remediation_graph()`)
- **B-244**: IMPLEMENTED-IN-SPEC at v0.9 (horizontal-first routing convention documented)
- **B-245**: Rule 11 maturity-weighted scoring extension (master_doc work, not spec)
- **B-246**: Move `LIKELY_BOUND_FACTORS_BY_FIXTURE` from C10 module constant to plumbing_minimums.json KB

**Resolved**:
- B-218: RESOLVED-AS-MISFRAMED at S35 Walk #2
- B-221: IMPLEMENTED in C10 v0.6
- B-239: IMPLEMENTED in C10 v0.8
- **B-240: IMPLEMENTED in C7 amendment v0.7** (canonical_serialize extracted to `buildemup.utilities`)
- **B-243: IMPLEMENTED in C10 v0.9** (mutex DAG validation)
- **B-244: IMPLEMENTED in C10 v0.9** (routing convention documented)

---

## § 9 — Rule 11 spec audit on v0.9 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.9 itself): 0** — drafting absorbs Walk #8.

**OPEN QUESTIONS surfaced**: Q45, Q46.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v9-1 | Phase 0.5a fast-fail HARD-edge check + Phase 2.5 spatial check are now both pre-Phase-3. The naming "Phase 0.5a" without a "Phase 0.5b" is confusing — is there an implicit second sub-phase? | **MINOR** — rename to "Phase 0.5" (single sub-phase) and "Phase 2.5". Updated below. |
| F-v9-2 | `LIKELY_BOUND_FACTORS_BY_FIXTURE` defaults: WC=0.8 is fairly high (WCs typically corner-placed, near anchor). Should be 0.6-0.7? Calibration ad-hoc per Q45. | **NEEDS WALK** — accept ad-hoc v0.9 values per Q45; tune via B-219 replay data. Not a blocker. |
| F-v9-3 | `validate_remediation_graph` is described in Phase 5 prose but its `RemediationGraphError` doesn't carry a `failure_phase` (because it's systemic, not per-candidate). Inconsistent with WetZoneInfeasibleError which does carry it. | **MINOR** — accept inconsistency: failure_phase is for per-candidate errors only. RemediationGraphError is systemic, doesn't need it. Document. |
| F-v9-4 | Test count target 175; rough math: 36+42+46+24+10+12+5 = 175. Math correct. | **PASS** |
| F-v9-5 | Inv 21 mode says "RAISE-as-RemediationGraphError" — unusual mode notation. Other invariants use plain "RAISE". | **MINOR** — normalize to "RAISE"; document that the raised type is RemediationGraphError. |
| F-v9-6 | Phase 4 horizontal-first routing convention. But what if anchor's `riser_anchor_xy` differs from the wall's centerline (e.g., anchor offset)? Routing from fixture to anchor crosses the wall, not parallel to it. The "horizontal-first" rule may not apply cleanly. | **NEEDS WALK** — accept v1 simplification: route from `room.bbox_corner` to `riser_anchor_xy` using horizontal-first; corner cases (anchor outside wall plane) are theoretical at v1 since `riser_anchor_xy` lies on the assigned wall by construction. Document inline. |

**REJECTED-AS-CONSIDERED**:
- "Should `validate_remediation_graph` use a graph library (networkx) or hand-roll DFS?" — Hand-roll. Lightweight; no dependency.
- "Should F-v9-2 calibrations be exposed as config?" — No. KB territory per Q45 / B-246.

**Audit summary**: 0 patch-now (1 minor inline rename), 5 minor walk findings (mostly pass), 2 rejected. **No real bugs.** Audit ran; not performative.

**PATCH-NOW APPLIED INLINE**: F-v9-1 — "Phase 0.5a" renamed to "Phase 0.5" throughout § 3 (no "0.5b" exists; suffix was confusing).

---

## § 10 — Status

- **v0.9 PROPOSED.** **NOT LOCKED** per Ramalingam directive.
- LOCK BLOCKED on:
  - C7 amendment v0.7 LOCK declaration
  - Q45, Q46 open questions (both have recommendations)
  - 5 minor walk findings (mostly pass / minor)
- **F-v8-6 real bug FIXED** in v0.9 (Phase 0.5 + 2.5 split).
- **5 amendments absorbed**: F-v8-6 fix, mutex DAG validation, routing convention, per-fixture factors, capacity-vs-scoring naming cleanup.
- **6 backlog items resolved or implemented-in-spec**: B-218, B-221, B-239, B-240, B-243, B-244.
- Estimated walks to LOCK: **0-1**. v0.9 is LOCK candidate after Q45/Q46 verdict + C7 v0.7 LOCK.

---

**End of v0.9 PROPOSED.** Awaits Ramalingam's reading. C7 amendment v0.7 must LOCK first per B-212.
