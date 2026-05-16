# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v0.6 PROPOSED

**Component**: 10 (canonical Track 3 numbering)
**Status**: v0.6 PROPOSED. **NOT LOCKED.** Supersedes v0.5.
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 Walk #5 outcome.
**LOCK BLOCKED on**: C7 amendment v0.4 (B-212).

---

## § 0 — Architectural notes (REVISED v0.6)

C10 sits between C9 (room sizes) and C11 (geometric placement). It emits *constraints, groupings, and engineering primitives*. C11 honours them during placement. C14 scores them during evaluation.

**What C10 is NOT**:
- Does not produce *consumer-facing* scores (internal-decision metrics only; C14 owns plan quality).
- Does not handle acoustics, privacy, sleeping-adjacency conflicts (C14 territory).
- Does not optimise globally (C11a's 9 mutation operators do exploration).
- Does not run hydraulic simulation (B-220 plumbing-engineer review).
- Does not run MCS/MUS infeasibility diagnosis (v1 ships rule-based hints; B-230 = v3+ research).

**Pattern note**: 2nd `require_verified_*` config gate. Unified `RegulatoryConfidenceFramework` arrives at 3rd verification system (B-224).

**Q19 product-onboarding (NEW v0.6 per Walk #5 #12)**: C10's default `scoring_profile="neutral"` is the *safe-when-unset* value, not the *recommended Indian-residential* value. **Product layer MUST prompt the user to select `scoring_profile` at project setup**. Failure to prompt = product-layer Pattern E (silent default bias). C10 stays architecturally honest by emitting neutral by default; product UX drives explicit Vastu choice for the Indian-family target market. Documented as product-team contract.

---

## § 1 — Walk-resolved scope (cumulative across 5 walks)

| Q | Resolution | Walk |
|---|---|---|
| Q1 | Single-floor; multi-floor stack = C12 | #1 |
| Q2 | Wet-rooms include kitchen + utility; separate riser group | #1 |
| Q3 | Hard verdict + grouping primitives (no consumer scores) | #1 |
| Q4 | One plan per candidate; C11a explores | #1 |
| Q5 | Pattern A fail-fast | #1 |
| Q6 | `acceptable_wall_set` (set, not single) | #2 |
| Q11 | Per-fixture trap-arm distances `(room_id, fixture_type)` | #3 |
| Q12 → Q19 | scoring_profile defaults `neutral`; product onboarding prompts | #3 → #4 → #5 |
| Q13 | column_id optional; bonus, not requirement | #3 |
| Q14 | `WetZoneRiskBreakdown` 3-axis | #2 → #4 |
| Q-W3-1 | Phase 2 merge = common-feasible-wall | #3 → #4 |
| Q-W3-2 | Full-precision compare; 6dp serialise | #3 → #4 |
| Q-W3-3 | Weighted-sum + multi-axis breakdown | #3 |
| Q19 | Default `neutral` + product-onboarding spec (REVISED #5) | #4 → #5 |
| Q20 | `max_runtime_ms` DROPPED; states+attempts only | #4 |
| Q21 | Rule-based hints v1; B-230 IIS for v3+ | #4 |
| **Q22** (NEW #5) | PreClusteringInfeasibleError = PerCandidateError tier | #5 (your call) |
| **Q23** (NEW #5) | bend_count downgraded to informational | #5 (your call) |

---

## § 2 — Contract (REVISED v0.6)

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

### Schema (REVISED v0.6)

```python
@dataclass(frozen=True)
class RemediationHint:
    """Structured remediation hint per Walk #5 #2 (your call) + my F-v5-6.
    Replaces v0.5's plain string hints. Machine-parseable for retry orchestration.
    """
    kind: Literal[
        "relax_config",          # change a config value
        "increase_limit",        # raise a numeric limit
        "alternative_routing",   # try different riser placement
        "manual_review",         # human intervention required
    ]
    parameter: str               # e.g. "max_risers", "pooja_adjacency_mode"
    current_value: Any
    suggested_value: Any
    severity: Literal["low", "medium", "high"]    # low=safe, high=trade-off heavy
    human_readable: str          # rendered for UI/logs


@dataclass(frozen=True)
class ForcedCultureOverride:
    """Per Walk #5 #4 (your call) + my F-v5-3. Captures full context of any
    cluster forced onto a culturally-DISCOURAGED wall.
    """
    room_id: str
    wall_id: str
    category: str               # the cluster's primary category for which this wall is DISCOURAGED
    rejected_alternatives: tuple[str, ...]    # wall_ids tried but ruled out (reason in rule_trace)


@dataclass(frozen=True)
class WallScoreVector:
    """Per-wall, per-category score breakdown emitted by Phase 1b.
    REVISED v0.6 per Walk #5 #5: weights stored in provenance once, not per vector.
    """
    wall_id: str
    category: str
    engineering_score: float
    cultural_score: float
    adjacency_score: float
    scoring_profile_id: str     # references WetZonePlanProvenance.scoring_weights_snapshot

    # total_score still derived but requires looking up profile in provenance.
    # Removed @property; computed on-demand by callers using provenance.scoring_weights_snapshot.


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
    anchor: RiserAnchor
    wet_room_ids: tuple[str, ...]


@dataclass(frozen=True)
class WetZoneRiskBreakdown:
    """3-axis risk per Walk #4 #10. v0.6 (Walk #5 #3) adopts weighted-severity
    aggregation: not all degradations are equal.
    """
    optimization_risk: PlacementRiskLevel
    optimization_score: float       # weighted sum (was int in v0.5)
    engineering_risk: PlacementRiskLevel
    engineering_score: float
    cultural_risk: PlacementRiskLevel
    cultural_score: float


@dataclass(frozen=True)
class WetZonePlan:
    wet_wall_assignment: dict[str, str]
    riser_groups: tuple[RiserGroup, ...]
    kitchen_riser_group_id: str | None
    fixture_types_per_room: dict[str, tuple[str, ...]]
    trap_arm_distances: dict[tuple[str, str], float]
    total_wet_run_length_m: float
    bend_count: int               # NEW v0.6: downgraded to informational symbolic heuristic per Walk #5 #9 (your call)
    riser_count: int
    non_wet_room_buffer_zones: tuple[str, ...]
    acceptable_wall_sets: dict[str, tuple[str, ...]]

    @property
    def wall_segments_used(self) -> tuple[str, ...]:
        return tuple(sorted({rg.anchor.wall_id for rg in self.riser_groups}))


@dataclass(frozen=True)
class WetZoneScoringWeights:
    """Cultural + engineering scoring knobs. v0.6 unchanged from v0.5."""
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
    require_verified_plumbing: bool = False
    scoring_weights: WetZoneScoringWeights = field(default_factory=WetZoneScoringWeights)
    scoring_profile: Literal["vastu_strict", "vastu_soft", "neutral"] = "neutral"
    max_backtrack_states: int = 100
    max_assignment_attempts: int = 50
    trap_arm_tolerance_m: float = 0.15


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
    # Snapshot weights once (Walk #5 #5); WallScoreVector references this:
    scoring_weights_snapshot: WetZoneScoringWeights
    cluster_decisions: tuple[str, ...]
    wall_scoring_breakdown: tuple[WallScoreVector, ...]
    forced_culturally_discouraged: tuple[ForcedCultureOverride, ...]    # REVISED v0.6
    unverified_plumbing_rows_used: tuple[str, ...]
    search_truncated: bool
    states_explored: int
    truncation_reason: Literal["max_states", "max_attempts", "completed", "infeasible_terminated"]
    # NON-DETERMINISTIC, OBSERVATIONAL ONLY, EXCLUDED FROM REPLAY HASHES (Walk #5 #13):
    runtime_ms_observational: int
    risk_breakdown: WetZoneRiskBreakdown
    remediation_hints: tuple[RemediationHint, ...]    # REVISED v0.6
    rule_trace: tuple[str, ...]
```

---

## § 3 — Behaviour (REVISED v0.6)

### Phase 0 — Compute `acceptable_wall_sets` (REVISED v0.6 per F-v5-5)

For every room in `RoomSizeTable.rooms`:
1. **Width feasibility** — `wall.length_m >= room.liveability_min_width_m`.
2. **Wall eligibility** — `WallTag.EXTERNAL in wall.tags`.
3. **POOJA exclusion (REVISED v0.6 — F-v5-5 real bug fix)**:
   - **If `scoring_profile == "neutral"`**: NO axis-based exclusion. POOJA's acceptable set = all walls except those that will be assigned to wet rooms (post-Phase-3 enforcement via Inv 6 same-wall rule).
   - **If `scoring_profile != "neutral"` (vastu_strict, vastu_soft)**: exclude walls on bathroom-preferred axes (south/southeast/west) per Vastu literature, when `pooja_adjacency_mode="strict"`.

   This makes neutral genuinely neutral; only Inv 6's same-wall rule applies, no hidden cultural assumption.
4. **No partner-reference**. Inter-room compatibility enforced by Phase 0.5 + Phase 2.

Output: `acceptable_wall_sets: dict[str, tuple[str, ...]]` per-room independent.

### Phase 0.5 — Pre-clustering pairwise compatibility (NEW v0.6 per Walk #5 #11)

For each HARD-edge pair `(r1, r2)` (master_BR↔master_BA, KITCHEN↔LIVING, etc.):
1. Compute `intersection = acceptable_wall_sets[r1] ∩ acceptable_wall_sets[r2]`.
2. If empty: raise `PreClusteringInfeasibleError` (PerCandidateError tier per your Q22) with structured `RemediationHint`s populated.

Surfaces architectural impossibility before backtracking. O(HARD_edges × walls). Per Walk #5 #11.

### Phase 1a — Feasibility filter

For each `WallSegment`:
- Eligibility: `length_m >= 1.5m` AND `WallTag.EXTERNAL in tags`.
- Output: `feasible_walls: set[str]`.

### Phase 1b — Ranking

For each wall in `feasible_walls`, for each wet category:
- `engineering_score`: column-alignment-bonus + length-sufficiency-bonus.
- `cultural_score`: zero if `scoring_profile="neutral"`. Otherwise per `WetZoneScoringWeights.{cat}_axis_*`.
- `adjacency_score`: bonus per HARD-edge dry-room partner aligned.
- Emit `WallScoreVector` (with `scoring_profile_id` reference, not duplicated weights).

**Determinism**:
- Internal compares: full-precision FP, `EPSILON = 1e-9`.
- Tie-breaks: integer/lex rank keys (wall_id ASC, room_id ASC).
- Serialisation: `round(score, 6)`.

### Phase 2 — Wet-room clustering

Common-feasible-wall merge predicate (Walk #4 #2 strengthened):

1. **Seed step** (unchanged): one cluster per HARD-edge anchor, in seed order.
2. **Merge step**: for each pair `(C_i, C_j)`:
   - Compute `common_walls = ∩(acceptable_wall_sets of all members of C_i ∪ C_j)`.
   - For each wall in `common_walls`, score per Phase 1b; check capacity for `len(C_i) + len(C_j)` risers.
   - If at least one wall has capacity AND merge satisfies HARD-anti, MERGE.
3. **Tie-break**: lower `cluster_id` wins.

### Phase 3 — Wall assignment with reuse + bounded backtracking

(Largely unchanged from v0.5; refinements per Walk #5 #6.)

For each cluster:
1. Score eligible walls; apply `wall_reuse_penalty` for already-used. Capacity = `floor(wall.length_m / minimum_riser_spacing_m)`.
2. Greedy pick highest score where wall ∈ all members' `acceptable_wall_sets` AND capacity.
3. Backtrack on Inv 4/5/5b/6 violation; track `states_explored` and `attempts_count`.
4. Termination conditions:
   - `states_explored > config.max_backtrack_states` → `truncation_reason="max_states"`.
   - `attempts_count > config.max_assignment_attempts` → `truncation_reason="max_attempts"`.
   - All clusters assigned → `truncation_reason="completed"`.
5. **Forced-culture-override detection (REVISED v0.6 per Walk #5 #6 + my F-v5-10)**: per-cluster-primary-category evaluation. When ALL walls feasible-for-this-cluster's-primary-category have DISCOURAGED `cultural_score` for that category, AND a wall is selected, emit `ForcedCultureOverride(room_id, wall_id, category, rejected_alternatives)`.
6. Runtime measurement: `time.monotonic()` wraps the call; `runtime_ms_observational` recorded but NEVER used in control flow. Excluded from replay snapshot hashes.

### Phase 4 — Trap-arm distance

For each wet room, expand fixtures via `kb/plumbing_fixture_profiles.json` lookup. For each `(room_id, fixture_type)`:
1. Manhattan worst-case-corner distance.
2. **bend_count formal definition (REVISED v0.6 — Walk #5 #9 (your call) — DOWNGRADED to symbolic informational)**:
   - 0/1/2 bend symbolic count per same-axis-line/shared-coordinate/general case.
   - **No invariant constrains bend_count.** Documented in spec as: *"Symbolic heuristic. Not engineering-grade. C14 may use as rough cost proxy. Proper orthogonal routing graph deferred to C12 era per B-233."*
3. Validate against `kb/plumbing_minimums.json[fixture_type].trap_arm_max_m`:
   - `<= max` → OK.
   - `(max, max + tolerance]` → WARN logged.
   - `> max + tolerance` → raise `TrapArmDistanceExceededError` with structured `RemediationHint`s.
4. Track unverified rows; systemic gate `require_verified_plumbing=True` → raise `PlumbingConfidenceTooLow`.

### Phase 5 — Provenance + risk breakdown (REVISED v0.6 per Walk #5 #3)

Compute `WetZoneRiskBreakdown` with **weighted-severity aggregation** (per Walk #5 #3):

**Optimization risk** (search-quality):
- `search_truncated` → +1.0
- `truncation_reason in ("max_states","max_attempts")` → +0.5

**Engineering risk** (plumbing/feasibility):
- Any WARN-tier trap-arm (within tolerance) → +0.5
- `riser_count == effective_max_risers` → +1.0
- Any wall at full capacity → +0.5

**Cultural risk** (cultural-rule compromise):
- `pooja_adjacency_mode == "soft"` AND POOJA placed adjacent → +1.5
- `len(forced_culturally_discouraged) > 0` → +1.0 per override
- Any cluster forced onto DISCOURAGED axis → +0.5

For each axis: score 0 → LOW; 0 < score < 1.5 → MEDIUM; score >= 1.5 → HIGH (revised thresholds for fractional scoring; tune via B-219 replay data).

**`RemediationHint` population**: rule-based per current condition:
- `riser_count == max_risers` → `RemediationHint(kind="increase_limit", parameter="max_risers", current_value=N, suggested_value=N+1, severity="low", human_readable="Try max_risers + 1 (currently {N})")`.
- POOJA infeasibility → `RemediationHint(kind="relax_config", parameter="pooja_adjacency_mode", current_value="strict", suggested_value="soft", severity="medium", ...)`.
- Master-BA infeasibility → `RemediationHint(kind="relax_config", parameter="require_master_bath_adjacency", current_value=True, suggested_value=False, severity="high", ...)`.
- Trap-arm exceeded → `RemediationHint(kind="alternative_routing", parameter="riser_position", current_value=anchor_xy, suggested_value="closer to fixture", severity="medium", ...)`.

**Pre-clustering infeasibility hints** (NEW v0.6 per Phase 0.5):
- HARD-edge pair with empty intersection → `RemediationHint(kind="manual_review", parameter="acceptable_wall_sets", ..., severity="high", human_readable="No common wall for {r1} and {r2}; consider widening one room or relaxing HARD-edge.")`.

### Complexity note (NEW v0.6 per Walk #5 #18)

Worst-case complexity for Phase 3 backtracking: `O(C × W^R)` where C = clusters, W = feasible walls per cluster, R = rooms per cluster. v1 typical: C=2-3, W=2-4, R=1-3 → bounded states ~50-100. `max_backtrack_states=100` covers v1. Polygonal envelopes (B-066) may push W → 8+, requiring B-217 spatial partitioning. Instrument with B-219 replay.

### KB cross-validation startup hook (NEW v0.6 per Walk #5 #15)

Module-level function called at C10 import:

```python
def validate_plumbing_kbs_compatibility(profiles_kb, minimums_kb):
    referenced_types = {ft for row in profiles_kb["rows"] for ft in row["fixture_types"]}
    available_types = {row["fixture_type"] for row in minimums_kb["rows"]}
    orphans = referenced_types - available_types
    if orphans:
        raise KBVersionMismatchError(
            f"plumbing_fixture_profiles references missing types in plumbing_minimums: "
            f"{orphans}. Profiles KB version: {profiles_kb['_kb_version']}; "
            f"minimums KB version: {minimums_kb['_kb_version']}."
        )
```

Plus: `kb/plumbing_fixture_profiles.json` carries `_compatible_with_minimums_kb_version` field. **B-234 tracks full registry validator tooling for v2.**

---

## § 4 — Invariants (carried v0.5 — Inv 1-17, no new in v0.6)

| # | Invariant | Mode |
|---|---|---|
| 1 | Every BATHROOM in brief appears in `wet_wall_assignment` | RAISE |
| 2 | Every KITCHEN appears (if `has_kitchen`) | RAISE |
| 3 | UTILITY appears (if present) | RAISE |
| 4 | Every assigned wall_id exists AND meets Phase 1a feasibility | RAISE |
| 5 | Master BATHROOM's wall ∈ master BEDROOM's `acceptable_wall_set` | RAISE/WARN per config |
| 5b | KITCHEN's wall is adjacent to LIVING/service zone | RAISE |
| 6 | POOJA not on same wall as wet room AND not on same axis (axis check applies only when `scoring_profile != "neutral"`) | RAISE/WARN per `pooja_adjacency_mode` |
| 7 | `riser_count >= 1` if ≥1 wet room | RAISE |
| 8 | `riser_count <= effective_max_risers` | RAISE/WARN per mode |
| 9 | Every `room_id` exists in `RoomSizeTable` | RAISE |
| 10 | `total_wet_run_length_m >= 0` AND finite | RAISE |
| 11 | `trap_arm_distances[(r,f)] <= MAX_TRAP_ARM_M[f] + trap_arm_tolerance_m` | RAISE/WARN |
| 12 | `trap_arm_distances[(room_id, fixture_type)]` exists for every wet room × fixture | RAISE |
| 13 | Each `RiserGroup.wet_room_ids` non-empty | RAISE |
| 14 | `RiserGroup.anchor.wall_id` matches every member's `wet_wall_assignment` | RAISE |
| 15 | Every room's assigned wall ∈ `acceptable_wall_sets[room_id]` (non-empty) | RAISE |
| 16 | `fixture_types_per_room` keys all exist in BOTH plumbing_minimums AND plumbing_fixture_profiles KBs | RAISE |
| 17 | `riser_count` consistent with wall capacity | RAISE |

---

## § 5 — Failure modes (REVISED v0.6 — added PreClusteringInfeasibleError + KBVersionMismatchError)

```
WetZonePlanError (base) [carries remediation_hints: tuple[RemediationHint, ...] = ()]
├── PerCandidateError
│   ├── WetZoneInfeasibleError
│   ├── PreClusteringInfeasibleError    (NEW v0.6 — Phase 0.5 HARD-edge incompatibility)
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError
│   ├── WallCapacityExceededError
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow            (systemic)
└── KBVersionMismatchError              (NEW v0.6 — startup-time KB validation)
```

---

## § 6 — Test coverage requirements

Target ~145 tests (was 140; +5 for new features):

- ~32 schema tests (RemediationHint, ForcedCultureOverride, WallScoreVector w/profile_id, WetZoneRiskBreakdown w/weighted scores)
- ~38 invariant tests
- ~35 phase-logic tests (Phase 0 neutral-vs-vastu split, Phase 0.5 pairwise pre-clustering, Phase 1a/1b, Phase 2 stronger merge, Phase 3 backtracking + forced-override per-category, Phase 4 trap-arm + bend symbolic)
- ~20 partial-batch tolerance tests
- ~10 STRICT-mode escalation tests
- ~8 deterministic-replay snapshot tests (excludes runtime_ms_observational from hash)
- **~2 KB cross-validator tests** (NEW v0.6)

Cumulative baseline target at C10 ship: 2155 + 145 ≈ **2300 passed**.

---

## § 7 — Open questions surfaced at v0.6

**Q24 (NEW v0.6)**: Phase 5's risk-axis weighted-severity aggregation uses fractional scores (0.5, 1.0, 1.5). Threshold cutoffs `< 1.5 = MEDIUM`, `>= 1.5 = HIGH` may be calibrated wrong. v0.6 ships these; tune via B-219 post-ship.
- **Recommendation**: ad-hoc OK for v1. Replay data tunes thresholds.

**Q25 (NEW v0.6)**: `RemediationHint.severity` levels are 3-tier (low/medium/high). Should "manual_review" hints (e.g. PreClusteringInfeasibleError) auto-default to "high" or be configurable per hint?
- **Recommendation**: auto-default to "high" for manual_review kind; "low" for relax_config; "medium" for everything else. Document in Phase 5.

**Q26 (NEW v0.6)**: bend_count downgraded to informational — should it stay in `WetZonePlan` schema at all, or move to `WetZonePlanProvenance` since it's now informational?
- **Recommendation**: keep in `WetZonePlan` (it's an output primitive, not an audit trail). C14 may consume it as cost-estimation hint.

---

## § 8 — Backlog at v0.6

Carried open: B-212 (BLOCKER, expected to clear with C7 amendment v0.4 LOCK), B-213, B-214, B-215, B-216, B-217 (updated), B-219, B-220, B-221, B-222, B-223, B-224, B-225, B-226, B-227, B-228, B-229, B-230.
**Newly filed at v0.6** (Walk #5): B-231, B-232 (probable-fixture-zone), B-233 (orthogonal routing graph), B-234 (KB registry validator), B-235 (WallTag domain split).

**B-218 RESOLVED-AS-MISFRAMED** at Walk #2.

No new B-NNN items at v0.6 itself — all Walk #5 reviewer items absorbed.

---

## § 9 — Rule 11 spec audit on v0.6 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.6 itself): 0** — drafting is the patch round.

**OPEN QUESTIONS surfaced**: Q24-Q26 above.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v6-1 | Phase 0 step 3 with neutral profile says POOJA acceptable_set = "all walls except those assigned to wet rooms (post-Phase-3 enforcement)". But Phase 0 runs *before* Phase 3 — the exclusion is forward-referencing. Logically: Phase 0 emits POOJA's set as ALL walls; Inv 6 enforces same-wall exclusion at Phase 3 assignment time. Wording in Phase 0 should clarify the temporal split. | **PATCH-NOW v0.6 ITSELF** — wording fix. POOJA's Phase 0 set in neutral mode = all eligible walls; Inv 6 enforces same-wall exclusion at Phase 3. Inline-applied below. |
| F-v6-2 | `runtime_ms_observational` rename improves clarity but the JSON serialisation key is still in provenance dict. Anyone consuming provenance JSON might still try to use it. The "EXCLUDED FROM REPLAY HASHES" note is in code comment, not in user-facing schema doc. | **NEEDS WALK** — consider explicit `_observational_only` prefix in JSON key (`"_observational_runtime_ms"`) to make non-load-bearing nature visible at JSON inspection. v0.7 fix. |
| F-v6-3 | `RemediationHint.suggested_value: Any` — not type-safe. Could be int (max_risers), str (mode), bool (require_master_bath_adjacency), tuple (anchor_xy). Consumers can't type-check. | **NEEDS WALK** — accept `Any` with documented per-`kind` typing convention, OR introduce typed subclasses. Recommend `Any` with documentation for v1; subclass refactor when 3+ consumers exist. |
| F-v6-4 | Phase 5's weighted-severity aggregation can yield optimization_score=1.5 + engineering_score=2.0 + cultural_score=2.0 = aggregate 5.5. But there's no aggregate field. Caller computes if needed. Documented? | **MINOR** — already implicit in WetZoneRiskBreakdown 3-axis design. C14 aggregates per its own policy. Document briefly. |
| F-v6-5 | `validate_plumbing_kbs_compatibility` runs at module-import time. If KBs are loaded lazily or via dependency-injection, this hook may not fire. Need clarity on when this runs. | **NEEDS WALK** — specify: validator runs in C10's `__init__` or `plan_wet_zones` first call (lazy), not at module import. v0.7 clarification. |
| F-v6-6 | The Q19 product-onboarding § 0 note is a *product-team contract* but not enforceable from C10. If product team forgets to prompt, default neutral silently ships. Should we add a config-level `scoring_profile_explicitly_set: bool` flag for telemetry? | **NEEDS WALK** — consider as future enhancement (B-236). Out of v0.6 scope. |
| F-v6-7 | `ForcedCultureOverride.rejected_alternatives` is `tuple[str, ...]` of wall_ids. Doesn't include WHY each was rejected (which invariant fired). Loses debug context. | **NEEDS WALK** — promote to `tuple[tuple[str, str], ...]` of `(wall_id, rejection_reason)`. v0.7 fix. |
| F-v6-8 | Test count target says 145; rough math: 32+38+35+20+10+8+2 = 145. Math correct first time. | **PASS** |
| F-v6-9 | Phase 0.5 raises `PreClusteringInfeasibleError` for any HARD-edge pair with empty intersection. But what if the pair is r1↔r2 AND r1↔r3 — we raise on the first one. Does the error carry only that pair's info, or aggregate all infeasible pairs? Aggregating helps user fix root cause. | **NEEDS WALK** — aggregate all infeasible HARD-edge pairs in single error. v0.7 fix. |
| F-v6-10 | The architectural notes § 0 list 5 "what C10 is NOT" items. They're cumulative across walks but not deduplicated against each other. Cleanup recommended. | **MINOR** — minor cleanup, v0.7. |

**PATCH-NOW APPLIED INLINE TO v0.6**:

- **F-v6-1** PATCHED: Phase 0 step 3 wording for neutral profile updated above to clarify temporal split (Phase 0 emits all eligible walls; Phase 3 + Inv 6 enforce same-wall exclusion).

**REJECTED-AS-CONSIDERED**:
- "Should `WetZoneRiskBreakdown` carry `aggregate_risk: PlacementRiskLevel`?" — No. 3-axis split was a deliberate Walk #4 win.
- "Should `KBVersionMismatchError` extend `WetZonePlanError`?" — No. It's startup-time, not per-candidate; separate hierarchy correct.
- "Should `bend_count` carry a unit annotation `bend_count_symbolic: int`?" — No. Type system + docstring suffices.

**Audit summary**: 1 patch-now (F-v6-1, applied), 9 walk findings (F-v6-2 to F-v6-10), 3 rejected. Audit ran; not performative.

**Self-coverage measurement (Walk #5 round)**:
- Walk #5 reviewer found 30 items combined (18 C10 + 10 C7 + 2 KB).
- My v0.5 audit found 10 (C10) + 5 (C7) = 15. Combined overlap = 13. Combined coverage = 13/30 = **43%.**
- v0.6 audit catches 10 findings unprompted (1 patched inline).
- **Trend stabilising at ~33-43%.** External review remains valuable.

---

## § 10 — Status

- **v0.6 PROPOSED**. **NOT LOCKED.**
- LOCK BLOCKED on:
  - C7 amendment v0.4 reaching LOCK (expected next round)
  - F-v6-2, F-v6-3, F-v6-5, F-v6-6, F-v6-7, F-v6-9 (6 walk findings) resolved
  - Q24-Q26 (3 open questions) adjudicated
- F-v6-1 inline-resolved; F-v6-4, F-v6-8, F-v6-10 NO/MINOR.
- Estimated walks to LOCK: **1 more** after v0.6 → v0.7 likely refinement-only, then LOCK.

---

**End of v0.6 PROPOSED.** Awaits Ramalingam's reading + walk #6 direction.
