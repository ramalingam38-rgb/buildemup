# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v0.8 PROPOSED

**Component**: 10 (canonical Track 3 numbering)
**Status**: v0.8 PROPOSED. **NOT LOCKED** per Ramalingam directive. Supersedes v0.7.
**Authority**: S35 author's draft. PROPOSED, awaiting Ramalingam adjudication.
**Authored**: S35 Walk #7 outcome.
**LOCK BLOCKED on**: C7 amendment v0.6 LOCK declaration.

---

## § 0 — Architectural notes (UNCHANGED from v0.7)

C10 sits between C9 and C11. Emits constraints, groupings, engineering primitives. C11 places. C14 scores.

**What C10 is NOT**: consumer scores, acoustic/privacy concerns, global optimisation, hydraulic simulation, MCS/MUS infeasibility diagnosis. (See v0.7 for details.)

**Q19 product-onboarding contract**: default `scoring_profile="neutral"`; product layer prompts user to select. B-236 telemetry.

**Plumbing code framing**: India adopts UPC via IPA. v1 KB rows valid for Indian deployments; B-222 verifies primary-source.

---

## § 1 — Walk-resolved scope (cumulative — 7 walks)

All Q1-Q31 prior + Walk #7 resolutions:

| Q | Final | Walk |
|---|---|---|
| Q1-Q26 | (carried from v0.7) | walks 1-5 |
| Q27 | scoring_weights_hash on WallScoreVector | #6 |
| Q28 | `anchors: tuple[...]` forward-compat (v1 invariant len==1) | #6 |
| Q29 | v1 LOCK = architectural completeness; B-220/B-222 = pre-launch gates | #6 |
| Q30 | hash truncation to 16-char prefix — v0.8 candidate | #6 (recommended; not yet adjudicated) |
| Q31 | performance budget calibration ad-hoc; tune via B-219 | #6 |
| **Q32** (NEW Walk #7) | `estimated_wall_span_m` cluster-occupancy check | #7 (your call yes — B-239 baked into v0.8 since C9 zero-cost) |
| **Q33** (NEW Walk #7) | RemediationHint retry-orchestration fields | #7 (your call yes) |
| **Q34** (NEW Walk #7) | Trap-arm dual-bound (upper + likely) | #7 (your call yes) |
| **Q35** (NEW Walk #7) | bend_count rename + estimation_mode | #7 (your call yes) |
| **Q36** (NEW Walk #7) | Interim wall-capacity weighting (WC=2.0, shower=1.5, others=1.0) | #7 (your call yes) |

---

## § 2 — Contract (REVISED v0.8 — schema changes for 5 of 6 amendments)

```python
def plan_wet_zones(
    room_sized_candidates: tuple[RoomSizedCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    *,
    config: WetZonePlanConfig | None = None,
) -> tuple[WetZonePlannedCandidate, ...]:
    """C10 entry point. Per-candidate semantics mirror C9 § 14.40."""
```

`WetZonePlannedCandidate` = `RoomSizedCandidate` + `wet_zone_plan: WetZonePlan` + `provenance: WetZonePlanProvenance`.

### Schema (REVISED v0.8 — 5 schema changes from v0.7)

```python
@dataclass(frozen=True)
class TrapArmEstimate:
    """NEW v0.8 (Q34 your call). Dual-bound trap-arm distance. Replaces v0.7's
    plain float in trap_arm_distances. Reduces false-rejection on narrow
    Indian bathrooms (Walk #7 #3 + my F-v4-1)."""
    upper_bound_m: float          # Manhattan worst-case-corner — fail-safe upper bound
    likely_bound_m: float         # 0.5 * upper_bound — v1 heuristic; refined via B-232 post-ship


@dataclass(frozen=True)
class RemediationHint:
    """REVISED v0.8 (Q33 your call). Adds retry-orchestration fields per
    Walk #7 #9 + web evidence on deterministic retry priority."""
    kind: Literal["relax_config","increase_limit","alternative_routing","manual_review"]
    parameter: str
    current_value: Any
    suggested_value: Any
    severity: Literal["low","medium","high"]
    human_readable: str
    # NEW v0.8:
    retry_priority: int                                # orchestrator-ordering hint; lower = try first
    mutually_exclusive_with: tuple[str, ...]           # parameter names of conflicting hints
    expected_success_probability: float | None        # None at v1; calibrated post-B-219


@dataclass(frozen=True)
class ForcedCultureOverride:
    room_id: str
    wall_id: str
    category: str
    rejected_alternatives: tuple[tuple[str, str], ...]    # (wall_id, rejection_reason)


@dataclass(frozen=True)
class WallScoreVector:
    wall_id: str
    category: str
    engineering_score: float
    cultural_score: float
    adjacency_score: float
    scoring_profile_id: str
    scoring_weights_hash: str          # SHA256 hex; full 64 chars at v0.8 (Q30 truncation = post-LOCK refinement)


@dataclass(frozen=True)
class RiserAnchor:
    wall_id: str
    anchor_position_m: float
    riser_anchor_xy: tuple[float, float]
    column_id: str | None
    snap_distance_m: float | None


@dataclass(frozen=True)
class RiserGroup:
    group_id: str
    anchors: tuple[RiserAnchor, ...]   # forward-compat; v1 invariant len==1
    wet_room_ids: tuple[str, ...]


@dataclass(frozen=True)
class WetZoneRiskBreakdown:
    optimization_risk: PlacementRiskLevel
    optimization_score: float
    engineering_risk: PlacementRiskLevel
    engineering_score: float
    cultural_risk: PlacementRiskLevel
    cultural_score: float


@dataclass(frozen=True)
class WetZonePerformanceBudgets:
    max_wall_score_vectors: int = 100
    max_provenance_rule_trace_entries: int = 500
    max_remediation_hints: int = 20


@dataclass(frozen=True)
class WetZonePlan:
    wet_wall_assignment: dict[str, str]
    riser_groups: tuple[RiserGroup, ...]
    kitchen_riser_group_id: str | None
    fixture_types_per_room: dict[str, tuple[str, ...]]
    # REVISED v0.8 (Q34): TrapArmEstimate replaces float
    trap_arm_distances: dict[tuple[str, str], TrapArmEstimate]
    total_wet_run_length_m: float
    # RENAMED v0.8 (Q35 your call): was bend_count
    symbolic_bend_estimate: int                            # NOT engineering-grade; use bend_estimation_mode for context
    bend_estimation_mode: Literal["symbolic_v1"]           # forward-compat for B-233 ("orthogonal_routing_v1" etc)
    riser_count: int
    non_wet_room_buffer_zones: tuple[str, ...]
    acceptable_wall_sets: dict[str, tuple[str, ...]]

    @property
    def wall_segments_used(self) -> tuple[str, ...]:
        return tuple(sorted({rg.anchors[0].wall_id for rg in self.riser_groups}))


@dataclass(frozen=True)
class WetZoneScoringWeights:
    weight_engineering: float = 1.0
    weight_cultural: float = 1.0
    weight_adjacency: float = 1.0
    column_alignment_bonus: float = 0.2
    wall_length_sufficiency_bonus: float = 0.1
    wall_reuse_penalty: float = -0.5
    minimum_riser_spacing_m: float = 3.0
    bathroom_axis_preferred: float = 1.0
    bathroom_axis_neutral: float = 0.5
    bathroom_axis_discouraged: float = 0.0
    pooja_axis_preferred: float = 1.0
    pooja_axis_neutral: float = 0.5
    pooja_axis_discouraged: float = 0.0
    # NEW v0.8 (Q36 your call): interim DFU-aware capacity weights
    fixture_capacity_weights: dict[str, float] = field(default_factory=lambda: {
        "water_closet": 2.0,
        "shower": 1.5,
        "bathtub": 1.5,
        "lavatory": 1.0,
        "kitchen_sink": 1.0,
        "utility_sink": 1.0,
        "floor_drain": 0.5,
    })


@dataclass(frozen=True)
class WetZonePlanConfig:
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    pooja_adjacency_mode: Literal["strict", "soft"] = "strict"
    max_risers: int | None = None
    adjacency_threshold_m: float = 0.0
    require_master_bath_adjacency: bool = True
    require_verified_plumbing: bool = False
    scoring_weights: WetZoneScoringWeights = field(default_factory=WetZoneScoringWeights)
    scoring_profile: Literal["vastu_strict","vastu_soft","neutral"] = "neutral"
    max_backtrack_states: int = 100
    max_assignment_attempts: int = 50
    trap_arm_tolerance_m: float = 0.15
    performance_budgets: WetZonePerformanceBudgets = field(default_factory=WetZonePerformanceBudgets)


@dataclass(frozen=True)
class WetZonePlanProvenance:
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    plumbing_kb_version: str
    fixture_profiles_kb_version: str
    enforcement_mode: str
    pooja_adjacency_mode: str
    scoring_profile: str
    scoring_weights_snapshot: WetZoneScoringWeights
    cluster_decisions: tuple[str, ...]
    wall_scoring_breakdown: tuple[WallScoreVector, ...]
    forced_culturally_discouraged: tuple[ForcedCultureOverride, ...]
    unverified_plumbing_rows_used: tuple[str, ...]
    search_truncated: bool
    states_explored: int
    truncation_reason: Literal["max_states", "max_attempts", "completed", "infeasible_terminated"]
    _observational_runtime_ms: int
    risk_breakdown: WetZoneRiskBreakdown
    remediation_hints: tuple[RemediationHint, ...]
    performance_budget_warnings: tuple[str, ...]
    rule_trace: tuple[str, ...]
```

---

## § 3 — Behaviour (REVISED v0.8 — 6 phases with amendments)

### Phase 0 — Compute `acceptable_wall_sets` (UNCHANGED from v0.7)

For every room: width feasibility + WallTag.EXTERNAL + POOJA exclusion (conditional on scoring_profile).

**v0.8 production code change**: replace direct iteration `for wall in grid.wall_segments` with `for wall in grid.wall_segments_canonical()` (per C7 v0.6 W8 enforcement). Applies throughout C10 phases 0-5.

### Phase 0.5 — Pre-clustering pairwise compatibility (REVISED v0.8 per Q32 — Walk #7 #2)

**B-239 cluster-occupancy check (NEW v0.8)**:

For each cluster `C` (after Phase 2 seed step but before merge step):
1. Compute `cluster_occupancy_m = Σ(room.liveability_min_width_m for room_id in C)`. Uses C9's existing `RoomSizeRequirement.liveability_min_width_m` field — zero C9 amendment cost (verified by S35 grep).
2. For each candidate wall `w` in cluster's `acceptable_wall_sets`:
   - `usable_wall_length_m = w.length_m - 2 * minimum_riser_spacing_m` (safety margin: half a riser-spacing at each end).
   - Wall is *spatially feasible* for cluster iff `cluster_occupancy_m <= usable_wall_length_m`.
3. If no spatially-feasible wall exists for cluster `C`: emit `RemediationHint(kind="manual_review", parameter="cluster_size", ...)` and surface as `WetZoneInfeasibleError(failure_phase="pre_clustering_spatial")` — new failure_phase value distinct from "pre_clustering" (HARD-edge incompatibility).

**HARD-edge pairwise check (carried from v0.7)**: for each HARD-edge pair `(r1, r2)`, intersection of `acceptable_wall_sets` non-empty. Aggregated across all infeasible pairs in single error.

Both checks run in Phase 0.5; both raise `WetZoneInfeasibleError` (consolidated tree) with distinguishing `failure_phase` values.

Complexity: O(clusters × walls) for spatial check; O(HARD_edges × walls) for pairwise. v1 typical bounded.

### Phase 1a — Feasibility filter (UNCHANGED)

### Phase 1b — Ranking (UNCHANGED — uses canonical wall iteration per C7 v0.6)

### Phase 2 — Wet-room clustering (UNCHANGED — common-feasible-wall predicate; tie-break by cluster_id lex ASC)

### Phase 3 — Wall assignment (REVISED v0.8 per Q36 — Walk #7 #7)

**Capacity check uses interim DFU-aware weighting (NEW v0.8)**:

For each cluster `C` and candidate wall `w`:
```python
cluster_capacity_weight = sum(
    config.scoring_weights.fixture_capacity_weights[fixture_type]
    for room_id in C.wet_room_ids
    for fixture_type in fixture_types_per_room[room_id]
)
wall_capacity = floor(w.length_m / config.scoring_weights.minimum_riser_spacing_m)
# Cluster fits iff:
fits = cluster_capacity_weight <= wall_capacity
```

Replaces v0.7's flat `len(C.wet_room_ids) <= floor(w.length / spacing)`. Three WC-heavy bathrooms (capacity weight 6.0) on a 12m wall (capacity 4) now correctly fail; three utility sinks (capacity weight 3.0) on the same wall correctly pass.

This is interim. Full DFU-aware capacity per IPC Table 709.1 (B-220 + B-229) ships post-launch with plumbing-engineer review.

Other Phase 3 logic carries from v0.7: greedy + backtracking, `wall_reuse_penalty`, forced-culture-override per-category detection, truncation reasons.

### Phase 4 — Trap-arm distance (REVISED v0.8 per Q34 + Q35 — Walk #7 #3, #4)

For each `(room_id, fixture_type)`:

1. **Manhattan worst-case-corner distance** (carried v0.6) — `upper_bound_m`.
2. **Likely bound (NEW v0.8 per Q34)** — `likely_bound_m = 0.5 * upper_bound_m` for v1 heuristic. v1 assumes fixtures cluster in one half of the room; refined post-ship via B-232 empirical data on actual fixture-position distributions.
3. **Symbolic bend estimate (RENAMED v0.8 per Q35)** — was `bend_count`, now `symbolic_bend_estimate`. Same formal definition (0/1/2 bends per same-axis-line/shared-coordinate/general). Mode field `bend_estimation_mode = "symbolic_v1"` makes its provisional nature explicit.
4. **Validate against `kb/plumbing_minimums.json[fixture_type].trap_arm_max_m`** (REVISED v0.8 per Q34):
   - If `likely_bound_m <= MAX + tolerance_m`: OK.
   - If `likely_bound_m > MAX + tolerance_m` but `upper_bound_m <= MAX + tolerance_m`: WARN logged (likely passes, upper-bound borderline; rare case).
   - If both `likely_bound_m > MAX + tolerance_m` AND `upper_bound_m > MAX + tolerance_m`: raise `TrapArmDistanceExceededError`.
   - If `likely_bound_m <= MAX + tolerance_m` but `upper_bound_m > MAX + tolerance_m`: WARN (this is the **dual-bound win** — narrow Indian bathrooms where likely fixture position is fine but worst-case-corner is alarming. v0.7 would have raised; v0.8 warns).

Net effect: false-rejection rate drops on elongated bathrooms; fail-safe behaviour preserved when both bounds exceed.

5. Track unverified rows; systemic gate `require_verified_plumbing=True` → raise `PlumbingConfidenceTooLow`.

### Phase 5 — Provenance + risk breakdown (REVISED v0.8 — RemediationHint retry fields per Q33 — Walk #7 #9)

**RemediationHint default values (UPDATED v0.8)**:

| kind | severity default | retry_priority default | mutually_exclusive_with default |
|---|---|---|---|
| `relax_config` | low | 1 | (computed contextually; e.g. relax_pooja conflicts with no others) |
| `increase_limit` | medium | 2 | (e.g. "increase max_risers" conflicts with "decrease cluster size") |
| `alternative_routing` | medium | 3 | empty by default |
| `manual_review` | high | 99 | empty (terminal — orchestrator escalates) |

Web evidence on deterministic retry orchestration confirms this is real engineering:
- Inventory routing literature: explicit priority + fallback rules + deterministic outputs.
- Constraint feasibility relaxation literature: principled relaxation with priority ordering.

`expected_success_probability` defaults to `None` at v1; calibrated post-ship via B-219 replay data.

**Mutually-exclusive detection (NEW v0.8)**: Phase 5 inspects emitted hints; if two hints would relax conflicting constraints (e.g. "increase max_risers" + "decrease cluster size"), populate each hint's `mutually_exclusive_with` with the other's `parameter`. Orchestrator then knows to apply ONE, not both.

**Risk breakdown** (carried v0.6/v0.7 weighted-severity 0.5/1.0/1.5; tune via B-219).

**Performance budget warnings** (carried v0.7).

### Canonical serialisation (UNCHANGED from v0.7)

`canonical_serialize()` module-level helper. Per-field sort discipline. **F-v6-W1 from C7 v0.6 audit flagged dependency placement** — `canonical_serialize` is currently in C10 but C7's `assert_wall_segment_order_independent` test helper needs it. Two options:

- **(a)** Extract to `buildemup.utilities` shared module — clean long-term; small refactor.
- **(b)** Keep in C10; C7 test helper imports from C10 (introduces C7→C10 test dependency, but no production cycle since C7 production code doesn't import C10).

**Recommendation**: (b) for v1 (minimal disruption); file extraction as **B-240** for v2 utilities consolidation. Production code paths have no cycle (C7 production → no C10); only test helper crosses.

### KB cross-validation startup hook (UNCHANGED from v0.7)

Version drift + semantic integrity (plausible-range, unit consistency, orphan-minimum warnings).

---

## § 4 — Invariants (REVISED v0.8 — Inv 11 dual-bound semantics)

| # | Invariant | Mode |
|---|---|---|
| 1-10 | (carried from v0.7 — see prior spec) | RAISE |
| **11 (REVISED v0.8 per Q34)** | **For every `(room_id, fixture_type)`: RAISE iff `trap_arm_distances[(r,f)].likely_bound_m > MAX_TRAP_ARM_M[f] + trap_arm_tolerance_m` AND `trap_arm_distances[(r,f)].upper_bound_m > MAX_TRAP_ARM_M[f] + trap_arm_tolerance_m`. WARN iff only `upper_bound_m > MAX + tolerance` (likely bound passes; conservative upper-bound caution).** | RAISE/WARN |
| 12 | `trap_arm_distances[(room_id, fixture_type)]` exists for every wet room × fixture | RAISE |
| 13-16 | (carried from v0.7) | RAISE |
| 17 | `riser_count` consistent with wall capacity — **REVISED v0.8 per Q36**: capacity check uses cluster_capacity_weight (interim DFU-aware) | RAISE |
| 18 | `performance_budget_warnings` populated when budgets exceeded; descriptive only | DESCRIPTIVE |
| **19 (NEW v0.8 per Q32)** | **For every cluster `C` assigned to wall `w`: `Σ(room.liveability_min_width_m for room_id in C) <= w.length_m - 2 * minimum_riser_spacing_m`** (cluster spatial occupancy check) | RAISE |
| **20 (NEW v0.8 per Q35)** | **`bend_estimation_mode` is a Literal[...] enum value matching the algorithm version that produced `symbolic_bend_estimate`** | RAISE |

(Inv 1-10, 13-16 carried verbatim from v0.7.)

---

## § 5 — Failure modes (REVISED v0.8 — added pre_clustering_spatial failure_phase)

```
WetZonePlanError [carries remediation_hints + failure_phase]
├── PerCandidateError
│   ├── WetZoneInfeasibleError                          (consolidated)
│   │   └── PreClusteringInfeasibleError                (subclass: failure_phase ∈ {"pre_clustering", "pre_clustering_spatial"})
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError                    (RAISE-tier; per Inv 11 dual-bound logic)
│   ├── WallCapacityExceededError                       (per Inv 17 cluster-weight; carried v0.7)
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow                            (systemic)
└── KBVersionMismatchError                              (startup-time)
```

`WetZoneInfeasibleError.failure_phase` values: `"pre_clustering"` (HARD-edge), `"pre_clustering_spatial"` (NEW v0.8 — cluster occupancy), `"assignment"` (Phase 3).

---

## § 6 — Test coverage requirements (REVISED v0.8)

Target ~165 tests (was 155 in v0.7; +10 for v0.8 features):

- ~34 schema tests (TrapArmEstimate, RemediationHint with retry fields, WetZoneScoringWeights with fixture_capacity_weights, RiserGroup w/anchors-tuple, fixture_capacity_weights default)
- ~40 invariant tests (Inv 1-20; new Inv 19 cluster-occupancy + Inv 20 bend-mode)
- ~42 phase-logic tests (Phase 0 with canonical accessor, Phase 0.5 spatial check + HARD-edge aggregation, Phase 1a/1b, Phase 2 merge, Phase 3 backtracking + interim weighting + per-category override, Phase 4 dual-bound trap-arm + symbolic_bend_estimate)
- ~22 partial-batch tolerance tests
- ~10 STRICT-mode escalation tests
- ~12 deterministic-replay snapshot tests (canonical_serialize discipline; excludes `_observational_runtime_ms`; uses canonical accessor)
- ~5 KB cross-validator tests

Cumulative baseline target at C10 ship: 2155 + 165 ≈ **2320 passed**.

---

## § 7 — Open questions surfaced at v0.8

**Q37 (NEW v0.8)**: `TrapArmEstimate.likely_bound_m = 0.5 * upper_bound_m` is a v1 heuristic. Is 0.5 right, or should it be 0.6 / 0.4? B-232 calibrates post-ship.
- **Recommendation**: 0.5 for v1; tune via B-219 replay data.

**Q38 (NEW v0.8)**: `fixture_capacity_weights` defaults (WC=2.0, shower=1.5, lavatory=1.0, etc.) are interim per Walk #7 #7. Source?
- **Recommendation**: derived from rough DFU correspondence (WC has highest DFU; lavatory and kitchen sink similar). Document in spec § 0; primary source = NBC 2016 Part 9 + IPC Table 709.1 (B-220 review verifies).

**Q39 (NEW v0.8)**: `mutually_exclusive_with` detection in Phase 5 — should this be exhaustive (all conflicting pairs) or only the most-likely conflict pair?
- **Recommendation**: exhaustive at v1 (small N of hints; computation cheap). Orchestrator can ignore extras.

---

## § 8 — Backlog at v0.8

Carried open from v0.7: B-212 (BLOCKER), B-213, B-214, B-215, B-216, B-217 (updated), B-219, B-220, B-222, B-223, B-224, B-225, B-226, B-227, B-228, B-229 (updated v0.8 — interim shipped), B-230, B-231, B-232 (updated v0.8 — dual-bound shipped, calibration future), B-233, B-234a/b, B-235, B-236, B-237, B-238.

**Newly filed at v0.8** (Walk #7):
- **B-239**: Cluster spatial-occupancy check via `liveability_min_width_m` — **IMPLEMENTED in v0.8** (zero C9 amendment cost; can mark RESOLVED at v0.8 LOCK).
- **B-240**: Extract `canonical_serialize` to `buildemup.utilities` shared module to resolve C7→C10 test-helper dependency cleanly. Trigger: v2 utilities consolidation. Effort: S.

**Resolved**:
- B-218: RESOLVED-AS-MISFRAMED at S35 Walk #2
- B-221: IMPLEMENTED in C10 v0.6
- **B-239**: IMPLEMENTED in C10 v0.8 (provisional — confirms at LOCK)

---

## § 9 — Rule 11 spec audit on v0.8 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.8 itself): 0** — drafting absorbs Walk #7.

**OPEN QUESTIONS surfaced**: Q37, Q38, Q39 above.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v8-1 | `TrapArmEstimate.likely_bound_m = 0.5 * upper_bound_m` is a uniform heuristic across fixture types. WCs typically far from anchor (corner-of-room placement); lavatories typically nearer (door-side). The 0.5 factor may be too coarse. | **NEEDS WALK** — accept uniform 0.5 for v1; per-fixture refinement via B-232. Recommend per-fixture calibration table when probable-fixture-zone data accumulates. v0.9 candidate. |
| F-v8-2 | `fixture_capacity_weights` is in `WetZoneScoringWeights` — but it's a *capacity* concern, not a *scoring* concern. Naming/placement mismatch. | **NEEDS WALK** — extract to a new `WetZoneCapacityWeights` dataclass, OR rename `WetZoneScoringWeights` to encompass both. v0.9 cleanup; not v0.8 critical. |
| F-v8-3 | `mutually_exclusive_with: tuple[str, ...]` — `str` references parameter names. Two hints with `parameter="max_risers"` AND opposing suggested directions are conflicting. But the schema doesn't enforce that the parameter referenced in `mutually_exclusive_with` actually exists in another hint — could be dangling. | **NEEDS WALK** — Phase 5 detection ensures consistency; document that orchestrator should validate cross-references. Future structured retry-graph (B-NNN-graph) lifts this concern. |
| F-v8-4 | Inv 19 says cluster_occupancy ≤ usable_wall_length where usable = wall.length - 2*minimum_riser_spacing. The 2× safety margin is hard-coded. Should be configurable. | **MINOR** — accept for v0.8; expose `wall_safety_margin_m: float = 2.0 * minimum_riser_spacing_m` in WetZonePlanConfig if a customer asks. Defer. |
| F-v8-5 | The renamed `symbolic_bend_estimate` schema field — anyone reading raw JSON output sees `"symbolic_bend_estimate": 2` and intuits "this is symbolic, fine." But anyone reading dict-access code (`plan.symbolic_bend_estimate`) might still misuse. | **MINOR** — Python convention; can't fully prevent. F-v6-W2-equivalent for C10. B-237 covers linting. |
| F-v8-6 | Phase 0.5 cluster-occupancy check runs *before* Phase 2 merge. But cluster composition isn't final until Phase 2 merge completes. This means we may check occupancy on a cluster that subsequently gets merged into a larger one — the check on the smaller cluster is wasted. | **REAL ISSUE** — cluster-occupancy check should run **after** Phase 2 merge, against final cluster composition. Currently spec says "after seed step but before merge" — that's wrong. Fix in v0.9. |
| F-v8-7 | `_observational_runtime_ms` field — v0.8 still measures via `time.monotonic()` per Phase 3. But Phase 0.5 cluster-occupancy check (NEW v0.8) adds work — should runtime measurement wrap *all* phases or just Phase 3? | **NEEDS WALK** — wrap all phases for consistency. Document in v0.9. |
| F-v8-8 | Test count target 165; rough math: 34+40+42+22+10+12+5 = 165. Math correct. | **PASS** |
| F-v8-9 | The `failure_phase` enum now has 3 values: "pre_clustering", "pre_clustering_spatial", "assignment". Will need extension as more Phase-X failure modes emerge. Should be a Literal or a real enum? | **MINOR** — Literal is sufficient at v0.8; promote to enum if 5+ values emerge. |
| F-v8-10 | `RemediationHint.expected_success_probability: float | None` — at v1, all are None. Shipping a field that's always None is dead weight. | **NEEDS WALK** — accept dead weight as forward-compat for B-219; OR remove field, add later when calibration data exists. Recommend keep field (forward-compat win exceeds dead-weight cost). |

**REJECTED-AS-CONSIDERED**:
- "Should `TrapArmEstimate` carry both bounds AND the formula used?" — No. Formula is per-spec-version implicit.
- "Should `fixture_capacity_weights` be loaded from the plumbing KB instead of defaults?" — Premature. Once B-220 ships DFU values, the plumbing KB can carry capacity weights too.
- "Should `mutually_exclusive_with` be a `tuple[Literal[...]]` for type safety?" — No. Parameter set is open; `tuple[str, ...]` is right.

**Audit summary**: 0 patch-now (no inline fixes), 7 walk findings (1 real issue F-v8-6, 6 minor), 3 rejected. **F-v8-6 is a real spec bug** — cluster-occupancy check timing; v0.9 must fix.

**Self-coverage on this audit**: 10 findings unprompted. If reviewer Walk #8 (if you choose to run one) finds <10, my coverage is improving past the 60% Walk #7 mark.

---

## § 10 — Status

- **v0.8 PROPOSED. NOT LOCKED** per Ramalingam directive.
- LOCK BLOCKED on:
  - C7 amendment v0.6 LOCK declaration
  - F-v8-6 real bug (cluster-occupancy timing) — fix in v0.9
  - F-v8-1, F-v8-2, F-v8-3, F-v8-7, F-v8-10 walk findings — mostly v0.9 refinement
  - Q37, Q38, Q39 open questions
- **6 amendments absorbed**: canonical accessor (via C7 v0.6 + Phase 0-5 production code use), dual-bound trap-arm, bend rename + mode, interim wall capacity weighting, retry-orchestration RemediationHint, cluster-occupancy check.
- **B-239 IMPLEMENTED-IN-SPEC** (zero C9 cost via existing `liveability_min_width_m`).
- **B-240 NEW**: utilities module extraction for canonical_serialize (resolves F-v6-W1 from C7 v0.6 audit).
- **5 amendments updated existing backlog** (B-229, B-232 effort reduced — interim shipped).
- Estimated walks to LOCK: **1 more** after F-v8-6 fix in v0.9.

---

**End of v0.8 PROPOSED.** Awaits Ramalingam's reading. C7 amendment v0.6 must LOCK first per B-212.
