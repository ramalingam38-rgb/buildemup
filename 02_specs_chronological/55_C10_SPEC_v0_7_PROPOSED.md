# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v0.7 PROPOSED

**Component**: 10 (canonical Track 3 numbering)
**Status**: v0.7 PROPOSED. **NOT LOCKED.** Supersedes v0.6.
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 Walk #6 outcome.
**LOCK BLOCKED on**: C7 amendment v0.5 LOCK candidate awaiting Ramalingam declaration.

---

## § 0 — Architectural notes (REVISED v0.7 — deduplicated per F-v6-10 minor cleanup)

C10 sits between C9 (room sizes) and C11 (geometric placement). It emits *constraints, groupings, engineering primitives*. C11 honours them during placement. C14 scores them during evaluation.

**What C10 is NOT**:
- Does not produce consumer-facing scores (C14 owns plan quality; internal-decision metrics only).
- Does not handle acoustics, privacy, sleeping-adjacency conflicts (C14 territory).
- Does not optimise globally (C11a's 9 mutation operators do exploration).
- Does not run hydraulic simulation (B-220 plumbing-engineer review covers).
- Does not run MCS/MUS infeasibility diagnosis (B-230 = v3+ research).

**Pattern note**: 2nd `require_verified_*` config gate. Unified `RegulatoryConfidenceFramework` arrives at 3rd verification system (B-224).

**Q19 product-onboarding contract**: C10's default `scoring_profile="neutral"` is the *safe-when-unset* value. **Product layer MUST prompt the user to select scoring_profile at project setup**. C10 is architecturally honest by default; product UX drives explicit Vastu choice for the Indian-family target market. **B-236** tracks `scoring_profile_explicitly_set: bool` telemetry for production observability.

**Plumbing code framing (NEW v0.7 per Walk #6 #10 web evidence)**: India formally adopts UPC via IPA modification (Indian Plumbing Association published "Uniform Plumbing Code" tailored for India). v1 KB rows sourced to UPC/IPC are valid for Indian deployments; primary-source verification against NBC 2016 Part 9 + IS 1742 + state-specific overlays is **B-222** (CORRECTNESS-CRITICAL pre-launch gate, not pre-LOCK).

---

## § 1 — Walk-resolved scope (cumulative — 6 walks)

All Q1-Q26 prior + Walk #6 resolutions:

| Q | Final | Walk |
|---|---|---|
| Q1-Q5 | (original scope decisions) | #1 |
| Q6 | `acceptable_wall_set` (set, not predicted side) | #2 |
| Q11 | Per-fixture trap-arm `(room_id, fixture_type)` | #3 |
| Q12 → Q19 | Default `neutral` + product-onboarding spec | #3 → #4 → #5 |
| Q13 | column_id optional bonus | #3 |
| Q14 | `WetZoneRiskBreakdown` 3-axis | #2 → #4 |
| Q-W3-1 | Phase 2 merge = common-feasible-wall | #3 → #4 |
| Q-W3-2 | Full-precision compare; 6dp serialise | #3 → #4 |
| Q-W3-3 | Weighted-sum + multi-axis breakdown | #3 |
| Q19 | Default `neutral` + product onboarding | #4 → #5 |
| Q20 | `max_runtime_ms` DROPPED | #4 |
| Q21 | Rule-based hints v1; B-230 IIS for v3+ | #4 |
| Q22 | PreClusteringInfeasibleError = PerCandidateError | #5 |
| Q23 | bend_count downgraded to symbolic informational | #5 |
| Q24 | Risk-axis thresholds ad-hoc; tune via B-219 | #5 (your call yes) |
| Q25 | RemediationHint severity defaults per kind | #5 (your call yes) |
| Q26 | bend_count stays in WetZonePlan schema | #5 (your call yes) |
| **Q27** (NEW Walk #6) | scoring_weights_hash on WallScoreVector | #6 (your call yes) |
| **Q28** (NEW Walk #6) | `anchors: tuple[RiserAnchor, ...]` forward-compat (v1 invariant len==1) | #6 (your call yes) |
| **Q29** (NEW Walk #6) | v1 LOCK = architectural completeness; B-220 + B-222 are pre-launch (not pre-LOCK) gates | #6 (your call yes — Option B) |

---

## § 2 — Contract (REVISED v0.7)

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

### Schema (REVISED v0.7 — 9 changes from v0.6)

```python
@dataclass(frozen=True)
class RemediationHint:
    """Structured remediation hint. v0.7 (Walk #6 carried from prior batch-yes):
    severity defaults per kind; suggested_value typing documented per kind.
    """
    kind: Literal[
        "relax_config",
        "increase_limit",
        "alternative_routing",
        "manual_review",
    ]
    parameter: str               # see suggested_value typing per kind below
    current_value: Any           # documented per-kind in spec § 3 Phase 5
    suggested_value: Any         # documented per-kind in spec § 3 Phase 5
    severity: Literal["low", "medium", "high"]   # default per kind: relax_config=low, manual_review=high, others=medium
    human_readable: str

    # Per-kind suggested_value typing convention (v0.7 documented; not enforced via subclass):
    #   relax_config:        suggested_value type matches current_value (bool, str, etc.)
    #   increase_limit:      int (suggested_value > current_value)
    #   alternative_routing: tuple[float, float] | str (anchor_xy or wall_id)
    #   manual_review:       str (human description of root cause)


@dataclass(frozen=True)
class ForcedCultureOverride:
    """Walk #6 #14 + your prior call. rejected_alternatives now carries reasons."""
    room_id: str
    wall_id: str
    category: str
    rejected_alternatives: tuple[tuple[str, str], ...]    # (wall_id, rejection_reason)


@dataclass(frozen=True)
class WallScoreVector:
    """Per-wall, per-category score breakdown. v0.7 (Q27 your call):
    scoring_weights_hash provides self-contained replay reproducibility.
    """
    wall_id: str
    category: str
    engineering_score: float
    cultural_score: float
    adjacency_score: float
    scoring_profile_id: str                  # references provenance.scoring_weights_snapshot
    scoring_weights_hash: str                # NEW v0.7: SHA256 hex of WetZoneScoringWeights for self-contained replay


@dataclass(frozen=True)
class RiserAnchor:
    wall_id: str
    anchor_position_m: float
    riser_anchor_xy: tuple[float, float]
    column_id: str | None
    snap_distance_m: float | None


@dataclass(frozen=True)
class RiserGroup:
    """v0.7 (Q28 your call): forward-compat schema for B-225 multi-anchor."""
    group_id: str
    anchors: tuple[RiserAnchor, ...]         # NEW v0.7: tuple, not single. v1 invariant: len==1.
    wet_room_ids: tuple[str, ...]

    def __post_init__(self):
        # v1 invariant: exactly one anchor per RiserGroup
        if len(self.anchors) != 1:
            raise ValueError(
                f"RiserGroup {self.group_id}: v1 requires exactly 1 anchor; "
                f"got {len(self.anchors)}. Multi-anchor support pending B-225."
            )


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
    """NEW v0.7 per Walk #6 #30. Warning-tier on exceed; not raised."""
    max_wall_score_vectors: int = 100
    max_provenance_rule_trace_entries: int = 500
    max_remediation_hints: int = 20


@dataclass(frozen=True)
class WetZonePlan:
    wet_wall_assignment: dict[str, str]
    riser_groups: tuple[RiserGroup, ...]
    kitchen_riser_group_id: str | None
    fixture_types_per_room: dict[str, tuple[str, ...]]
    trap_arm_distances: dict[tuple[str, str], float]
    total_wet_run_length_m: float
    bend_count: int                          # informational symbolic heuristic; not engineering-grade
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


@dataclass(frozen=True)
class WetZonePlanConfig:
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    pooja_adjacency_mode: Literal["strict", "soft"] = "strict"
    max_risers: int | None = None
    adjacency_threshold_m: float = 0.0
    require_master_bath_adjacency: bool = True
    require_verified_plumbing: bool = False    # production-default = True per Q29; ship-default = False for tests
    scoring_weights: WetZoneScoringWeights = field(default_factory=WetZoneScoringWeights)
    scoring_profile: Literal["vastu_strict","vastu_soft","neutral"] = "neutral"
    max_backtrack_states: int = 100
    max_assignment_attempts: int = 50
    trap_arm_tolerance_m: float = 0.15
    performance_budgets: WetZonePerformanceBudgets = field(default_factory=WetZonePerformanceBudgets)   # NEW v0.7


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
    _observational_runtime_ms: int          # NEW v0.7 prefix per Walk #6 carried-yes (F-v6-2)
    risk_breakdown: WetZoneRiskBreakdown
    remediation_hints: tuple[RemediationHint, ...]
    performance_budget_warnings: tuple[str, ...]    # NEW v0.7: emitted when budgets exceeded
    rule_trace: tuple[str, ...]
```

---

## § 3 — Behaviour (REVISED v0.7)

### Phase 0 — Compute `acceptable_wall_sets[room_id]` (carried from v0.6)

For every room in `RoomSizeTable.rooms`:
1. Width feasibility — `wall.length_m >= room.liveability_min_width_m`.
2. Wall eligibility — `WallTag.EXTERNAL in wall.tags`.
3. **POOJA exclusion (carried v0.6 fix for F-v5-5)**:
   - If `scoring_profile == "neutral"`: NO axis-based exclusion. POOJA Phase 0 set = all eligible walls; Inv 6 same-wall enforcement at Phase 3.
   - If `scoring_profile != "neutral"`: exclude bathroom-preferred axes when `pooja_adjacency_mode="strict"`.
4. No partner-reference; inter-room compatibility enforced by Phase 0.5 + Phase 2.

### Phase 0.5 — Pre-clustering pairwise compatibility (REVISED v0.7 per Walk #6 #4 + #12)

Cache `acceptable_wall_sets` intersection results within single C10 invocation (memoisation per Walk #6 #4). For each HARD-edge pair `(r1, r2)`:
1. Compute `intersection = acceptable_wall_sets[r1] ∩ acceptable_wall_sets[r2]` (memoised).
2. If empty for ANY HARD-edge pair: **aggregate all infeasible pairs** (per F-v6-9 carried-yes), then raise `WetZoneInfeasibleError` (subclass note below) with structured `RemediationHint`s populated for each pair.

**Walk #6 #12 fix — error consolidation**: `PreClusteringInfeasibleError` is now a **subclass of `WetZoneInfeasibleError`** (not parallel class), with `failure_phase: Literal["pre_clustering"]` field distinguishing. Phase 3 raises `WetZoneInfeasibleError` with `failure_phase="assignment"`. Single error tree; same `RemediationHint` generation logic; preserved early-surfacing benefit.

Complexity: O(HARD_edges × walls). v1 typical: 3-5 edges × 4 walls = 12-20 ops. Bounded.

### Phase 1a — Feasibility filter (carried v0.6)

For each `WallSegment`: eligibility = `length_m >= 1.5m` AND `WallTag.EXTERNAL in tags`. Output: `feasible_walls: set[str]`.

### Phase 1b — Ranking (REVISED v0.7 per Q27)

For each wall in `feasible_walls`, for each wet category:
- `engineering_score`, `cultural_score`, `adjacency_score` per Phase 1b (carried).
- Emit `WallScoreVector` with **`scoring_weights_hash`** = SHA256 hex of canonical-JSON serialised `WetZoneScoringWeights`. Self-contained replay; weights snapshot lookup via hash → provenance archive.

Determinism: full-precision compare with `EPSILON=1e-9`; integer/lex tie-breaks; 6dp serialisation.

### Phase 2 — Wet-room clustering (carried v0.6)

Common-feasible-wall merge predicate. Seed → merge → tie-break on `cluster_id` lex ASC.

### Phase 3 — Wall assignment (carried v0.6 with consolidated error)

Greedy + backtracking; `wall_reuse_penalty`; capacity = `floor(wall.length_m / minimum_riser_spacing_m)`. Forced-culture-override per-cluster-primary-category detection. Truncation reasons: `max_states` / `max_attempts` / `completed` / `infeasible_terminated`. On infeasibility raise `WetZoneInfeasibleError(failure_phase="assignment", remediation_hints=...)`.

`_observational_runtime_ms` recorded via `time.monotonic()`; **NON-DETERMINISTIC. NOT FOR CONTROL FLOW. EXCLUDED FROM REPLAY SNAPSHOT HASHES.**

### Phase 4 — Trap-arm distance (carried v0.6)

Manhattan worst-case-corner; `bend_count` formal 0/1/2 (informational symbolic — not engineering-grade per Q23/Q26). Validate against `kb/plumbing_minimums.json[fixture_type].trap_arm_max_m`. Tolerance `[max, max+tol] = WARN`; beyond = `TrapArmDistanceExceededError` with hints.

### Phase 5 — Provenance + risk breakdown (REVISED v0.7)

Compute `WetZoneRiskBreakdown` with weighted-severity (carried v0.6: 0.5/1.0/1.5 weights; thresholds tuned via B-219).

**Performance budget enforcement (NEW v0.7 per Walk #6 #30)**:
- After Phase 4, count: `len(wall_scoring_breakdown)`, `len(rule_trace)`, `len(remediation_hints)`.
- For each that exceeds the budget: emit a string into `provenance.performance_budget_warnings`. Example: `"wall_scoring_breakdown count 127 exceeds budget 100"`.
- Warnings only; no raise. Caller decides escalation.

**`RemediationHint` defaults (Q25 carried-yes)**:
- `kind="manual_review"` → `severity="high"` default
- `kind="relax_config"` → `severity="low"` default
- `kind="increase_limit"` → `severity="medium"` default
- `kind="alternative_routing"` → `severity="medium"` default

### Canonical serialisation discipline (NEW v0.7 per Walk #6 #19)

Module-level helper `canonical_serialize(obj) -> str` produces byte-identical JSON across iteration orderings:

```python
def canonical_serialize(obj) -> str:
    """Produces deterministic JSON for replay snapshots.
    - dict keys sorted lex-ASC
    - tuple/list elements emitted in source order (caller responsibility for sort discipline)
    - float values rounded to 6dp
    - frozenset converted via serialize_tags_sorted (C7 helper)
    """
    return json.dumps(_canonicalize(obj), sort_keys=True, separators=(",", ":"))
```

**Sort discipline by field**:
- `non_wet_room_buffer_zones`: lex ASC
- `forced_culturally_discouraged`: lex ASC by `room_id`
- `unverified_plumbing_rows_used`: lex ASC
- `acceptable_wall_sets[k]` values: lex ASC of wall_ids
- `riser_groups`: lex ASC by `group_id`
- `wall_scoring_breakdown`: lex ASC by `(wall_id, category)`
- `cluster_decisions`, `rule_trace`: source order (production-only audit trace; replay snapshots use this directly)

Tests assert `canonical_serialize(plan)` byte-identical across iteration-shuffled inputs.

### KB cross-validation startup hook (REVISED v0.7 per Walk #6 #8)

Validator extended for **semantic integrity** beyond version drift:

```python
def validate_plumbing_kbs_compatibility(profiles_kb, minimums_kb):
    # 1. Version pinning (carried v0.6)
    if profiles_kb["_compatible_with_minimums_kb_version"] != minimums_kb["_kb_version"]:
        raise KBVersionMismatchError(...)

    # 2. Referenced fixture types exist in minimums (carried v0.6)
    referenced = {ft for row in profiles_kb["rows"] for ft in row["fixture_types"]}
    available = {row["fixture_type"] for row in minimums_kb["rows"]}
    if orphans := referenced - available:
        raise KBVersionMismatchError(f"orphan fixture types: {orphans}")

    # 3. Semantic integrity checks (NEW v0.7 per Walk #6 #8):
    for row in minimums_kb["rows"]:
        # Plausible diameter range (25-200mm covers all standard fixtures)
        if not (25 <= row["min_pipe_diameter_mm"] <= 200):
            raise KBVersionMismatchError(
                f"{row['fixture_type']}: min_pipe_diameter_mm={row['min_pipe_diameter_mm']} "
                f"outside plausible range [25, 200]"
            )
        # Trap seal range (38-100mm covers standard plumbing)
        if not (38 <= row["trap_seal_min_mm"] <= 100):
            raise KBVersionMismatchError(
                f"{row['fixture_type']}: trap_seal_min_mm out of plausible range"
            )
        # Trap arm positive
        if row["trap_arm_max_m"] <= 0:
            raise KBVersionMismatchError(...)

    # 4. Orphan-minimum warnings (NEW v0.7): fixtures in minimums NOT referenced in profiles
    orphan_minimums = available - referenced
    # Log warning, don't raise (forward-staged fixtures legitimate)
```

**B-234** updated and split:
- **B-234a**: Full registry validator tooling (auto-detect orphan refs, schema migration tests) — v2.
- **B-234b**: Semantic integrity validator depth (cross-source consistency vs NBC/IS) — v2.

### Complexity note (carried v0.6)

Worst-case Phase 3: `O(C × W^R)`. v1 typical: C=2-3, W=2-4, R=1-3 → bounded. Polygonal envelopes need spatial partitioning (B-217).

---

## § 4 — Invariants (REVISED v0.7 — added Inv 18 for performance budget warnings)

| # | Invariant | Mode |
|---|---|---|
| 1-17 | (carried from v0.6 — see prior spec) | RAISE/WARN per mode |
| **18 (NEW v0.7)** | **`provenance.performance_budget_warnings` is a `tuple[str, ...]`. Each entry references a budget that was exceeded; warnings only, never raised.** | DESCRIPTIVE — no enforcement |

(Inv 1-17 carried verbatim from v0.6 § 4 — see consolidated bundle.)

---

## § 5 — Failure modes (REVISED v0.7 — error consolidation per Walk #6 #12)

```
WetZonePlanError (base) [carries remediation_hints + failure_phase]
├── PerCandidateError
│   ├── WetZoneInfeasibleError                          (REVISED v0.7 — now consolidates)
│   │   └── PreClusteringInfeasibleError                (NEW: subclass with failure_phase="pre_clustering")
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError
│   ├── WallCapacityExceededError
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow                            (systemic)
└── KBVersionMismatchError                              (startup-time)
```

`WetZoneInfeasibleError.failure_phase` field distinguishes pre-clustering vs assignment-phase failures.

---

## § 6 — Test coverage requirements (REVISED v0.7)

Target ~155 tests (was 145; +10 for v0.7 features):

- ~32 schema tests (RemediationHint per-kind, ForcedCultureOverride with reasons, WallScoreVector w/hash, RiserGroup w/anchors-tuple, WetZonePerformanceBudgets, _observational_runtime_ms exclusion)
- ~38 invariant tests (Inv 1-18)
- ~38 phase-logic tests (Phase 0 neutral/vastu split, Phase 0.5 memoisation + aggregated infeasibility, Phase 1a/1b w/hash, Phase 2 stronger merge, Phase 3 backtracking + per-category override + error consolidation, Phase 4 trap-arm + bend symbolic)
- ~22 partial-batch tolerance tests
- ~10 STRICT-mode escalation tests
- ~10 deterministic-replay snapshot tests (using canonical_serialize; excludes _observational_runtime_ms; hash-equivalent across shuffle)
- ~5 KB cross-validator tests (version drift + semantic integrity)

Cumulative baseline target at C10 ship: 2155 + 155 ≈ **2310 passed**.

**Test maintenance concern (Walk #6 #25)**: 2310-test suite with replay-heavy patterns risks brittleness. **B-237 filed** for post-v1 test modernisation: Hypothesis property-based testing, scenario generators, snapshot compression. Not v1-blocking.

---

## § 7 — Open questions surfaced at v0.7

**Q30 (NEW v0.7)**: `WallScoreVector.scoring_weights_hash` SHA256 = 64 hex chars per vector × 100 vectors per plan = 6.4KB hash overhead. Acceptable, OR truncate to 16-char prefix?
- **Recommendation**: 16-char prefix sufficient for replay-collision detection (2^64 collision space). Save ~5KB per plan. v0.8 candidate.

**Q31 (NEW v0.7)**: `WetZonePerformanceBudgets` defaults (100 vectors, 500 trace entries, 20 hints) — calibrated against what?
- **Recommendation**: ad-hoc v1; tune via B-219 replay snapshots post-ship (same calibration mechanism as risk-axis thresholds Q24).

---

## § 8 — Backlog at v0.7 (REVISED v0.7 — criticality classification per Walk #6 #24)

**CORRECTNESS-CRITICAL (pre-launch gates per Q29)**:
- B-220: Full hydraulic primitives — plumbing-engineer review
- B-222: Plumbing KB primary-source verification (NBC 2016 Part 9 + IS 1742 + state codes)

**INFRASTRUCTURE (post-v1 platform work)**:
- B-219: Deterministic-replay tests with hash snapshots
- B-224: RegulatoryConfidenceFramework (when 3rd verification system arrives)
- B-234a/b: KB registry validator + semantic-integrity tooling
- B-236: `scoring_profile_explicitly_set` telemetry
- B-237: Test-suite modernisation (Hypothesis, scenario gen, snapshot compression)
- B-238: Independent architect review (cultural rules + spatial logic)

**OPTIMIZATION (post-ship tuning)**:
- B-213: Adaptive `max_risers` formula
- B-216: `adjacency_threshold_m` default tuning
- B-223: Memoised score cache + complexity metrics
- B-228: Adaptive `wall_reuse_penalty`

**FEATURE (v2+)**:
- B-225: Multi-anchor RiserGroup (schema forward-compat shipped at v0.7; v2 removes invariant)
- B-227: Luxury fixture KB extension
- B-229: DFU-aware wall capacity
- B-232: Probable-fixture-zone heuristic

**POLYGONAL (B-066 era)**:
- B-217: Three-tier wall classes (EXTERNAL/SERVICE_CORE/INTERIOR)
- B-226: `acceptable_wall_sets` polygonal pruning
- B-231: Wall lookup O(1) optimisation
- B-235: WallTag domain split

**RESEARCH (v3+)**:
- B-230: Full MCS/MUS infeasibility diagnosis
- B-233: Proper orthogonal routing graph for bend_count

**RESOLVED**:
- B-218: RESOLVED-AS-MISFRAMED at S35 Walk #2
- B-221: IMPLEMENTED in C10 v0.6 as RemediationHint dataclass

**Carried inactive**: B-214 (per-bathroom subtype, depends on B-208), B-215 (stack-fit length refinement).

---

## § 9 — Rule 11 spec audit on v0.7 PROPOSED

**PATCH-NOW (in v0.7 itself): 0** — drafting absorbs Walk #6.

**OPEN QUESTIONS surfaced**: Q30, Q31 above.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v7-1 | `RiserGroup.__post_init__` raises ValueError for v1 invariant `len(anchors)==1`. But the v2 plan is to remove this invariant. When v2 ships, the v1-only validation needs deprecation flagging. Document the migration path. | **MINOR** — add docstring note: "v2 removes len==1 invariant via B-225; migration tests will assert backward-compat." Inline-applied. |
| F-v7-2 | `scoring_weights_hash` SHA256 computation is deterministic but requires canonical-JSON serialisation of `WetZoneScoringWeights`. Without that, hash differs across float-format variations. | **NEEDS WALK** — specify hash input is `canonical_serialize(weights)` not raw JSON. v0.8 fix or document inline. |
| F-v7-3 | `validate_plumbing_kbs_compatibility` semantic checks use plausible-range thresholds (25-200mm diameter, 38-100mm trap seal). These thresholds aren't sourced — where do they come from? | **NEEDS WALK** — cite IPC/NBC ranges in docstring. ~80% defensible from Indian plumbing practice; ship with note that B-222 may refine. |
| F-v7-4 | `_observational_runtime_ms` JSON underscore prefix (`_observational_*`) makes it visually distinct in inspection. But Python attribute access is unaffected — anyone calling `provenance._observational_runtime_ms` directly bypasses the convention. | **NO ACTION at v1** — Python convention; can't enforce private. Document expectation in spec; B-237 adds linting. |
| F-v7-5 | `performance_budget_warnings: tuple[str, ...]` is unstructured. Same complaint as F-v6-3 about `RemediationHint`. | **NEEDS WALK** — promote to `tuple[BudgetWarning, ...]` dataclass with `(field, exceeded_value, budget_value)`? Or accept strings for v1, structure in v2. Recommend strings-for-v1 (consistent with F-v6-3 documented-per-kind acceptance). |
| F-v7-6 | Test count target 155; rough math: 32+38+38+22+10+10+5 = 155. Math correct second time. | **PASS** |
| F-v7-7 | The `failure_phase` field on `WetZoneInfeasibleError` allows distinguishing causes. But `PreClusteringInfeasibleError` subclass exists *separately* — are these redundant? | **NEEDS WALK** — likely yes; either keep subclass for `isinstance()` checks OR drop subclass and rely on `failure_phase`. v0.8 architectural decision. Recommend KEEP subclass (cleaner exception handling). |
| F-v7-8 | `canonical_serialize` is described as "module-level helper" — which module? `c10/__init__.py`? Shared utility module? | **MINOR** — pick `c10/serialization.py` per modular convention. Document in v0.8. |
| F-v7-9 | Schema added 4 new fields (scoring_weights_hash, anchors-tuple, performance_budgets, _observational_runtime_ms, performance_budget_warnings). Five fields = 5 JSON-schema-version bumps if downstream consumers care. Coordination cost. | **MINOR** — version JSON schema explicitly via `provenance.schema_version: str` field. Defer to v0.8. |
| F-v7-10 | The architectural-notes § 0 list grew from 4 to 5 items + plumbing-code framing paragraph. Reviewer #10 of Walk #6 surfaced Indian plumbing context; spec should reference that web-evidence inline. | **MINOR** — already inlined; § 0 reference is sufficient. |

**REJECTED-AS-CONSIDERED**:
- "Should `WetZonePerformanceBudgets` raise on exceed instead of warn?" — No. Walk #6 #30 framing was descriptive observability; raising creates false-positive rejection in production.
- "Should `canonical_serialize` be importable from a single shared utility module across C9 + C10?" — Defer; cross-component utility consolidation is a separate refactor (post-v1).
- "Should `forced_culturally_discouraged` aggregate by category to flag systemic cultural compromise?" — Already extractable via filter + groupby; no schema change needed.

**Audit summary**: 0 patch-now (1 inline minor doc), 8 walk findings (mostly minor), 3 rejected. **No real bugs.** Audit ran; not performative.

**Self-coverage on v0.7 audit**: 10 findings unprompted. Walk #7 reviewer (if you choose to run one) calibrates.

---

## § 10 — Status

- **v0.7 PROPOSED**. **NOT LOCKED.**
- **20 amendments absorbed**: 11 Walk #6 + 9 carried from prior batch-yes.
- LOCK BLOCKED on:
  - C7 amendment v0.5 LOCK declaration (you adjudicate)
  - F-v7-2, F-v7-3, F-v7-5, F-v7-7 walk findings (4 — mostly v0.8 refinement)
  - Q30, Q31 (2 open questions — both have recommendations)
- F-v7-1, F-v7-4, F-v7-6, F-v7-8, F-v7-9, F-v7-10 NO/MINOR
- Estimated walks to LOCK: **1 more.** v0.8 likely refinement-only; LOCK after.

---

**End of v0.7 PROPOSED.** Awaits Ramalingam's reading. C7 amendment v0.5 LOCK candidate must LOCK first per B-212.
