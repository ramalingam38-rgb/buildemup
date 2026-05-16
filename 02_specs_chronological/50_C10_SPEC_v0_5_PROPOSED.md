# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v0.5 PROPOSED

**Component**: 10 (canonical Track 3 numbering)
**Status**: v0.5 PROPOSED. **NOT LOCKED.** Supersedes v0.4 PROPOSED.
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 Walk #4 outcome.
**LOCK BLOCKED on**: C7 amendment v0.3 (B-212).

---

## § 0 — Architectural notes (REVISED v0.5)

C10 sits between C9 (room sizes) and C11 (geometric placement). It emits *constraints, groupings, and engineering primitives*. C11 honours them during placement. C14 scores them during evaluation.

**What C10 is NOT** (recurring walk-rejected scope expansions):
- **C10 does not produce *consumer-facing* scores.** It emits per-wall scoring vectors and severity-weighted risk breakdowns as *internal-decision metrics*; C14 owns the consumer plan-quality score. (Clarification per F-v4-9.)
- **C10 does not handle acoustics, privacy, sleeping-adjacency.** C14 territory. (Walk-#2 #15, Walk-#3 #14 — consistent rejection.)
- **C10 does not optimise globally.** C11a's 9 mutation operators (incl. wet-wall-rotation) handle exploration. C10 commits one plan as seed. (Walk-#2 #4, Walk-#3 #4-adjacent.)
- **C10 does not run hydraulic simulation.** v1 ships partial (trap-arm distance per IPC/UPC); full DFU/slope/vent goes to plumbing-engineer review (B-220).
- **C10 does not run MCS/MUS infeasibility diagnosis.** v1 ships rule-based remediation hints (B-221); full IIS isolation per CSP literature is B-230 (research-grade work for v3+).

**Pattern note**: this spec proposes a 2nd `require_verified_*` config gate (mirrors C9's `require_verified_nbc`). Building unified `RegulatoryConfidenceFramework` now would be premature abstraction (Pattern E variant). Filed as B-224; trigger = arrival of 3rd verification system.

---

## § 1 — Walk-resolved scope (cumulative)

| Q | Resolution | Walk |
|---|---|---|
| Q1 single-floor scope | Yes; multi-floor stack is C12. | #1 |
| Q2 wet-rooms include kitchen + utility | Yes; kitchen tracked separately. | #1 |
| Q3 hard verdict + grouping primitives, NO consumer scores | Yes. | #1 (clarified Walk #4) |
| Q4 one plan per candidate | Yes; C11a explores alternatives. | #1 |
| Q5 Pattern A fail-fast | Yes. | #1 |
| Q6 master-bath wall | `acceptable_wall_set`. | #2 |
| Q11 COMBINED-bath fixture mapping | Per-fixture distances `(room_id, fixture_type)`. | #3 |
| Q12 Vastu defaults | **REVISED Walk #4 #14**: see Q19 below. | #3 → #4 |
| Q13 column_id required | Optional; bonus, not requirement. | #3 |
| Q14 placement_risk in provenance | **REVISED Walk #4 #10**: replaced by `WetZoneRiskBreakdown` (3-axis). | #2 → #4 |
| Q-W3-1 Phase 2 merge criterion | `acceptable_wall_sets` overlap → strengthened to common-feasible-wall (Walk-#4 #2). | Walk-3 → #4 |
| Q-W3-2 quantisation level | **REVISED Walk #4 #16**: full-precision epsilon-aware comparison (`EPSILON=1e-9`); 6dp only for serialisation. | Walk-3 → #4 |
| Q-W3-3 score formula | Weighted sum + multi-axis breakdown emission. | Walk-3 |
| **Q19 (NEW Walk #4)**: Default scoring profile | **`neutral`** (flipped from `vastu_strict`). Product layer prompts user to select Vastu profile explicitly; no hidden default bias. | Walk #4 (your call) |
| **Q20 (NEW Walk #4)**: Runtime termination | **DROP** `max_runtime_ms` from config. Only `max_backtrack_states` + new `max_assignment_attempts`. Runtime is informational provenance, never control flow. | Walk #4 (your call) |
| **Q21 (NEW Walk #4)**: Infeasibility diagnosis | **Ship rule-based hints in v1**; full IIS isolation = B-230. | Walk #4 (your call) |

---

## § 2 — Contract (REVISED v0.5)

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

### Schema (REVISED v0.5)

```python
@dataclass(frozen=True)
class WallScoreVector:
    """Per-wall, per-category score breakdown emitted by Phase 1b.
    REVISED v0.5 per Walk #4 #6 + #7: total_score is derived; no storage redundancy.
    """
    wall_id: str
    category: str                       # "bathroom" / "kitchen" / "utility"
    engineering_score: float            # column alignment + length sufficiency
    cultural_score: float               # Vastu axis preference (zero if scoring_profile="neutral")
    adjacency_score: float              # proximity to required dry-room neighbours
    weight_engineering: float           # carried so total_score is reproducible from this record alone
    weight_cultural: float
    weight_adjacency: float

    @property
    def total_score(self) -> float:
        """Derived (Walk #4 #6 + my F-v4-3 fix). Never stored."""
        return (
            self.weight_engineering * self.engineering_score
            + self.weight_cultural * self.cultural_score
            + self.weight_adjacency * self.adjacency_score
        )


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
    """3-axis risk per Walk #4 #10. Replaces v0.4 single placement_risk_level.

    Each axis mirrors C9's PlacementRiskLevel semantics (LOW/MEDIUM/HIGH +
    severity-weighted score). Aggregation if needed happens at C14/UI layer.
    """
    optimization_risk: PlacementRiskLevel       # search truncation, low explored fraction
    optimization_score: int
    engineering_risk: PlacementRiskLevel        # WARN trap-arm, max_risers reached, capacity hits
    engineering_score: int
    cultural_risk: PlacementRiskLevel           # POOJA soft-mode violation, DISCOURAGED axis forced
    cultural_score: int


@dataclass(frozen=True)
class WetZonePlan:
    wet_wall_assignment: dict[str, str]
    riser_groups: tuple[RiserGroup, ...]
    kitchen_riser_group_id: str | None
    fixture_types_per_room: dict[str, tuple[str, ...]]      # populated from kb/plumbing_fixture_profiles.json (Walk #4 #12)
    trap_arm_distances: dict[tuple[str, str], float]        # (room_id, fixture_type) -> Manhattan distance
    total_wet_run_length_m: float
    bend_count: int                                          # formal definition Walk #4 #11 (see Phase 4)
    riser_count: int
    non_wet_room_buffer_zones: tuple[str, ...]
    acceptable_wall_sets: dict[str, tuple[str, ...]]

    @property
    def wall_segments_used(self) -> tuple[str, ...]:
        return tuple(sorted({rg.anchor.wall_id for rg in self.riser_groups}))


@dataclass(frozen=True)
class WetZoneScoringWeights:
    """Weighted-sum knobs. v0.5 changes (Walk #4 #14): defaults flipped to neutral profile."""
    weight_engineering: float = 1.0
    weight_cultural: float = 1.0
    weight_adjacency: float = 1.0
    column_alignment_bonus: float = 0.2
    wall_length_sufficiency_bonus: float = 0.1
    wall_reuse_penalty: float = -0.5
    minimum_riser_spacing_m: float = 3.0
    # Cultural-axis preferences (only consulted if scoring_profile != "neutral"):
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
    # Walk #4 Q19 (your call): default flipped to neutral
    scoring_profile: Literal["vastu_strict", "vastu_soft", "neutral"] = "neutral"
    # Walk #4 Q20 (your call): runtime as control-flow REMOVED
    max_backtrack_states: int = 100
    max_assignment_attempts: int = 50           # NEW v0.5
    # max_runtime_ms REMOVED in v0.5 per Walk #4 #5 + your call
    trap_arm_tolerance_m: float = 0.15


@dataclass(frozen=True)
class WetZonePlanProvenance:
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    plumbing_kb_version: str
    fixture_profiles_kb_version: str            # NEW v0.5 (Walk #4 #12)
    enforcement_mode: str
    pooja_adjacency_mode: str
    scoring_profile: str
    cluster_decisions: tuple[str, ...]
    wall_scoring_breakdown: tuple[WallScoreVector, ...]    # v0.5: tuple, not dict (multiple categories per wall)
    forced_culturally_discouraged: tuple[str, ...]         # NEW v0.5 (Walk #4 #7) — room_ids with culturally-DISCOURAGED but engineering-required wall
    unverified_plumbing_rows_used: tuple[str, ...]
    # Search-quality (Walk #4 #4 — categorical labels DROPPED):
    search_truncated: bool
    states_explored: int
    truncation_reason: Literal["max_states", "max_attempts", "completed", "infeasible_terminated"]
    runtime_ms_actual: int                       # informational only; never control flow
    # Risk breakdown (Walk #4 #10):
    risk_breakdown: WetZoneRiskBreakdown
    # Remediation hints (Walk #4 #18 + your Q21 call):
    remediation_hints: tuple[str, ...]
    rule_trace: tuple[str, ...]
```

---

## § 3 — Behaviour (REVISED v0.5 — full deterministic spec)

### Phase 0 — Compute `acceptable_wall_sets[room_id]` (REVISED v0.5 per Walk #4 #1)

**Recursive dependency removed.** Compute each room independently:

For every room in `RoomSizeTable.rooms`:
1. **Width feasibility** — `wall.length_m >= room.liveability_min_width_m`.
2. **Wall eligibility** — `WallTag.EXTERNAL in wall.tags`.
3. **Static exclusion rules** — POOJA excludes any wall whose axis matches a typically-wet axis (south/southeast/west); ONLY when `pooja_adjacency_mode="strict"`.
4. **No partner-reference**. Inter-room compatibility (master-BR/master-BA same-side, KITCHEN-LIVING adjacency) is enforced by Phase 2 clustering (HARD edges) + Phase 3 assignment validation (Inv 5/5b), not by Phase 0.

Output: `acceptable_wall_sets: dict[str, tuple[str, ...]]` — per-room independent.

### Phase 1a — Feasibility filter (NEW v0.5 per Walk #4 #7)

For each `WallSegment` in `Grid.wall_segments`:
1. Eligibility: `length_m >= 1.5m` AND `WallTag.EXTERNAL in tags`.
2. Output: `feasible_walls: set[str]` — engineering-feasible only.

### Phase 1b — Ranking (REVISED v0.5)

For each wall in `feasible_walls`, for each wet category:
1. Compute `engineering_score` (column-alignment-bonus + length-sufficiency-bonus).
2. Compute `cultural_score` — **zero** if `scoring_profile="neutral"` (Q19 your call). Otherwise per `WetZoneScoringWeights.{cat}_axis_*`.
3. Compute `adjacency_score` — bonus per HARD-edge dry-room partner whose acceptable side aligns with this wall.
4. Emit `WallScoreVector(...)` with explicit weight values.

**Determinism (Walk #4 #16 + your Q-W3-2 revision)**:
- Internal comparisons: full-precision FP with `EPSILON = 1e-9` epsilon-aware ordering. `score_a < score_b` becomes `(score_a + EPSILON) < score_b`.
- Tie-breaks: integer/lex rank keys (wall_id ASC, room_id ASC) — never raw FP.
- Serialisation (rule_trace, replay snapshots): `round(score, 6)`.

### Phase 2 — Wet-room clustering (REVISED v0.5 per Walk #4 #2)

**Stronger merge predicate**: replace v0.4's "overlap ≥ 1 wall" with "exists at least one wall in `intersection(acceptable_wall_sets)` of merged members AND that wall has remaining capacity AND merging satisfies all HARD edges of both clusters."

Implementation:
1. **Seed step** (unchanged): one cluster per HARD-edge anchor in seed-order. master_BR/master_BA pair → KITCHEN seed → typical_BAs in `(priority ASC, room_id_lex ASC)` order → UTILITY last.
2. **Merge step (REVISED v0.5)**: for each pair `(C_i, C_j)` in seed order:
   - Compute `common_walls = ∩(acceptable_wall_sets of all members of C_i ∪ C_j)`.
   - For each wall in `common_walls`, sort by Phase 1b total_score DESC; check capacity.
   - If at least one wall has capacity for `len(C_i) + len(C_j)` risers (per `minimum_riser_spacing_m`), AND merge does not violate HARD-anti edges, MERGE.
3. **Tie-break**: lower `cluster_id` wins (lex ASC).
4. **Termination**: no merge fires in a full pass OR `max_risers` reached.

This is genuinely deterministic and pre-placement-correct (no centroids needed).

### Phase 3 — Wall assignment with reuse + bounded backtracking (REVISED v0.5)

For each cluster in seed order:
1. **Score eligible walls** per Phase 1b for cluster's primary category. Apply `wall_reuse_penalty` for already-used walls. Capacity = `floor(wall.length_m / minimum_riser_spacing_m)`.
2. **Greedy pick** highest-score wall (post-penalty) where `wall ∈ all members' acceptable_wall_sets` AND capacity not exhausted.
3. **Backtrack** on Inv 4/5/5b/6 violation: undo, try next-best. Track `states_explored` AND `attempts_count`.
4. **Termination conditions** (Q20 your call — runtime not in control flow):
   - `states_explored > config.max_backtrack_states` → terminate. `truncation_reason="max_states"`.
   - `attempts_count > config.max_assignment_attempts` → terminate. `truncation_reason="max_attempts"`.
   - All clusters assigned → `truncation_reason="completed"`.
5. **If terminated with feasible best-found**: emit `search_truncated=True`. Record `states_explored`. **Categorical confidence label DROPPED** (Walk #4 #4); raw metrics let downstream calibrate.
6. **If no feasible state reached after termination**: raise `WetZoneInfeasibleError` with `remediation_hints` populated (Q21 your call).
7. **Forced-culture-override detection (Walk #4 #7)**: when chosen wall has `cultural_score=DISCOURAGED` for that cluster's category AND was selected because it was the only feasible choice, append `cluster.master_room_id` to `forced_culturally_discouraged`.
8. **Runtime measurement (informational only)**: record `time.monotonic()` start/end for `runtime_ms_actual`. Never compared against a threshold for control flow.

### Phase 4 — Trap-arm distance (REVISED v0.5)

For each wet room, expand fixtures by lookup in `kb/plumbing_fixture_profiles.json` (Walk #4 #12 — fixture mapping in KB):

```python
fixtures = lookup_fixtures(category=room.category, bathroom_subtype=room.bathroom_subtype)
# e.g. (BATHROOM, COMBINED) -> ("water_closet", "lavatory", "shower")
```

For each `(room_id, fixture_type)`:
1. **Manhattan worst-case-corner distance** (Walk #4 #3 from v0.4 Walk #3 #3): `|Δx| + |Δy|` from room's bounding-box corner farthest from anchor to anchor.
2. **Bend count formal definition (NEW v0.5 per Walk #4 #11)**:
   - 0 bends if fixture corner and anchor share an axis-line (collinear).
   - 1 bend if they share x or y coordinate.
   - 2 bends in general case (typical for v1 worst-case-corner).
3. **Validate** against `kb/plumbing_minimums.json[fixture_type].trap_arm_max_m`:
   - `distance <= max` → OK.
   - `max < distance <= max + tolerance` → WARN logged, no raise.
   - `distance > max + tolerance` → raise `TrapArmDistanceExceededError` (with `remediation_hints`).
4. Track unverified rows used.
5. Systemic gate `require_verified_plumbing=True` + unverified rows used → raise `PlumbingConfidenceTooLow`.

### Phase 5 — Provenance assembly + risk breakdown (REVISED v0.5 per Walk #4 #10)

Compute `WetZoneRiskBreakdown` (3-axis):

**Optimization risk** (search-quality):
- `search_truncated` → +1
- `states_explored < 10% of theoretical state space estimate` → +1
- `truncation_reason in ("max_states","max_attempts")` → +1

**Engineering risk** (plumbing/feasibility):
- `riser_count == effective_max_risers` → +1
- Any WARN-tier trap-arm distance (within tolerance, not raised) → +1
- Any wall at full capacity → +1

**Cultural risk** (cultural-rule compromise):
- `pooja_adjacency_mode == "soft"` AND POOJA placed adjacent to wet wall → +1
- `len(forced_culturally_discouraged) > 0` → +1
- Any cluster forced onto DISCOURAGED axis → +1

For each axis: score 0 → LOW; 1-2 → MEDIUM; 3+ → HIGH (mirrors C9 § 14.36).

**Remediation hints (NEW v0.5 per Q21)**: rule-based; populate when raising error or when risk axes show MEDIUM/HIGH:
- `riser_count == max_risers` → `"Try max_risers + 1 (currently {n})"`.
- POOJA infeasibility → `"Try pooja_adjacency_mode='soft'"`.
- Width infeasibility on master-BA → `"Try require_master_bath_adjacency=False"`.
- Trap-arm exceeded → `"Move riser closer to fixture (room_id={x}); current run = {d}m, max = {m}m"`.

These are simple rule-based hints. Full IIS/MCS = B-230 v3+ research.

---

## § 4 — Invariants (carried v0.4 — Inv 1-17, no changes; Inv 18 dropped at v0.4 audit)

| # | Invariant | Mode |
|---|---|---|
| 1 | Every BATHROOM in brief appears in `wet_wall_assignment` | RAISE |
| 2 | Every KITCHEN appears (if `has_kitchen`) | RAISE |
| 3 | UTILITY appears (if present) | RAISE |
| 4 | Every assigned wall_id exists AND meets Phase 1a feasibility | RAISE |
| 5 | Master BATHROOM's wall ∈ master BEDROOM's `acceptable_wall_set` | RAISE/WARN per config |
| 5b | KITCHEN's wall is adjacent to LIVING/service zone | RAISE |
| 6 | POOJA not on same wall as wet room AND not on same axis | RAISE/WARN per `pooja_adjacency_mode` |
| 7 | `riser_count >= 1` if ≥1 wet room | RAISE |
| 8 | `riser_count <= effective_max_risers` | RAISE/WARN per mode |
| 9 | Every `room_id` exists in `RoomSizeTable` | RAISE |
| 10 | `total_wet_run_length_m >= 0` AND finite | RAISE |
| 11 | `trap_arm_distances[(r,f)] <= MAX_TRAP_ARM_M[f] + trap_arm_tolerance_m` (within tolerance = WARN) | RAISE/WARN |
| 12 | `trap_arm_distances[(room_id, fixture_type)]` exists for every wet room × fixture | RAISE |
| 13 | Each `RiserGroup.wet_room_ids` non-empty | RAISE |
| 14 | `RiserGroup.anchor.wall_id` matches every member's `wet_wall_assignment` | RAISE |
| 15 | Every room's assigned wall ∈ `acceptable_wall_sets[room_id]` (non-empty) | RAISE |
| 16 | `fixture_types_per_room[room_id]` keys all exist in `kb/plumbing_minimums.json` AND in `kb/plumbing_fixture_profiles.json` | RAISE |
| 17 | `riser_count` consistent with wall capacity | RAISE |

---

## § 5 — Failure modes (REVISED v0.5 — added remediation_hints attribute)

```
WetZonePlanError (base) [carries remediation_hints: tuple[str, ...] = ()]
├── PerCandidateError
│   ├── WetZoneInfeasibleError
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError    (RAISE-tier — beyond tolerance)
│   ├── WallCapacityExceededError       (Inv 17)
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
└── PlumbingConfidenceTooLow            (systemic)
```

---

## § 6 — Test coverage requirements

Target ~140 tests (up from v0.4's 135 — Phase 1a/1b split + risk breakdown 3-axis tests + remediation hints + neutral-profile coverage):

- ~32 schema tests (RiserAnchor, RiserGroup, WallScoreVector incl. derived total_score, WetZoneRiskBreakdown, WetZoneScoringWeights profiles, config)
- ~38 invariant tests (Inv 1-17 across modes + boundary)
- ~32 phase-logic tests (Phase 0 independent computation, Phase 1a feasibility filter, Phase 1b ranking, Phase 2 stronger merge predicate, Phase 3 backtracking + reuse + truncation reasons, Phase 4 Manhattan + tolerance + bend-count)
- ~20 partial-batch tolerance tests
- ~10 STRICT-mode escalation tests
- ~8 deterministic-replay snapshot tests (Walk #3 #15 + Walk #4 #16 — full-precision compare, 6dp serialise)

Cumulative baseline target at C10 ship: 2155 + 140 ≈ **2295 passed**.

---

## § 7 — Open questions surfaced at v0.5

**Q22**: When `scoring_profile="neutral"`, `cultural_score` is zero. Does that make `forced_culturally_discouraged` always empty (since no wall is "DISCOURAGED" without cultural scoring)?
- **Recommendation**: yes, neutral profile → `forced_culturally_discouraged` always empty. Document in Phase 5.

**Q23**: `optimization_risk` axis uses `states_explored < 10% of theoretical state space estimate` — but the theoretical estimate is itself a heuristic. Is this calibration good enough?
- **Recommendation**: ad-hoc OK for v1. Refine via B-219 replay snapshots post-ship.

**Q24**: `kb/plumbing_fixture_profiles.json` — should v1 also encode pipe diameter per fixture in the profile, or rely on lookup-by-fixture-type into `kb/plumbing_minimums.json`?
- **Recommendation**: lookup-by-fixture-type. Keeps profiles KB minimal; engineering data lives in plumbing_minimums.

**Q25**: Inv 11 currently has 3 outcomes (OK / WARN / RAISE). Should the WARN also surface in `risk_breakdown.engineering_score` AND in `remediation_hints`, or just risk_breakdown?
- **Recommendation**: both. WARN is a degradation signal; user-visible hint helps actioning.

---

## § 8 — Backlog at v0.5

Carried open: B-212 (BLOCKER), B-213, B-214, B-215, B-216, B-217 (updated), B-219, B-220, B-221 (updated), B-222, B-223, B-224, B-225, B-226, B-227, B-228, B-229, B-230.
**B-218 RESOLVED-AS-MISFRAMED** at Walk #2.

No new B-NNN items at v0.5 — all Walk #4 reviewer items absorbed into amendments or routed to existing backlog.

---

## § 9 — Rule 11 spec audit on v0.5 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.5 itself): 0** — drafting is the patch round.

**OPEN QUESTIONS surfaced**: Q22-Q25 above.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v5-1 | `WetZoneRiskBreakdown` has 3 axes × 2 fields each = 6 fields. C14 will likely consume all 3 risk levels but compute its own aggregate. The spec doesn't say how C14 should aggregate — could lead to inconsistent UI/scoring downstream. | **NO ACTION at v0.5** — C14 spec problem. v0.5 emits the breakdown; aggregation is C14's call. |
| F-v5-2 | `optimization_score` and `engineering_score` and `cultural_score` are integers (mirroring C9 `placement_risk_score`). With 3+ contributing factors per axis at +1 each, scores up to ~5-6 are possible. Threshold `3+ → HIGH` is tight; rare events (e.g. 4 mild engineering issues) may overflow to HIGH inappropriately. | **NEEDS WALK** — calibrate or document expectation. Recommend leave at 3+ for v1; tune via B-219 replay data. |
| F-v5-3 | `forced_culturally_discouraged: tuple[str, ...]` — the type is just room_ids. Doesn't say WHICH wall was forced. Caller can't tell if forcing was master-BR's wall vs typical bathroom's. | **NEEDS WALK** — promote to `tuple[tuple[str, str], ...]` of `(room_id, wall_id)` pairs. Trivial fix; bake into v0.6. |
| F-v5-4 | `kb/plumbing_fixture_profiles.json` introduces a new KB-version-string field (`fixture_profiles_kb_version`) in provenance. No corresponding `require_verified_fixture_profiles` config — but the profile mapping is structural-not-regulatory, so probably doesn't need verification gate. Worth confirming. | **CLARIFICATION** — fixture mapping is operational data (which fixtures exist in which room types), not regulatory. No verification gate needed. Document in v0.6. |
| F-v5-5 | Phase 0 step 3 says POOJA excludes "any wall whose axis matches a typically-wet axis (south/southeast/west); ONLY when `pooja_adjacency_mode='strict'`". But "typically-wet axis" is informal — south/southeast/west is the Vastu *bathroom-preferred* axis set, which is exactly what we DON'T enforce when `scoring_profile="neutral"`. Inconsistency: with neutral profile + strict pooja mode, are POOJA exclusions cultural or structural? | **REAL BUG** — fix in v0.6. Recommendation: POOJA exclusion only triggers under `scoring_profile != "neutral"` OR via explicit per-pooja-axis-block config. With pure neutral profile, POOJA has no axis preference; only same-wall-as-wet-room is excluded. |
| F-v5-6 | `remediation_hints` are emitted as `tuple[str, ...]` — strings. Not machine-parseable for retry coordinator (B-NNN-A in C9 spec, B-221 here). | **NEEDS WALK** — promote to structured `tuple[RemediationHint, ...]` where `RemediationHint` is a frozen dataclass with `kind: str`, `parameter: str`, `current_value: Any`, `suggested_value: Any`. v0.6 fix. |
| F-v5-7 | `runtime_ms_actual` recorded but explicitly "never control flow". Tests asserting runtime would still be platform-dependent. Need to confirm: are there any tests on runtime? | **NO ACTION** — by Q20 design, no tests on runtime. Provenance field is observable but not constrained. |
| F-v5-8 | Test count target 140; previous walk amendments add ~5 tests each per amendment × 10 amendments = 50 new tests. 135 + 50 = 185, not 140. Math is off again. | **MINOR** — accept that test count is approximate; tune at build time. |
| F-v5-9 | `WallScoreVector.weight_*` fields are duplicated across all vectors emitted in one C10 call (every WallScoreVector carries the same weights, since they come from one config). Storage redundancy. | **NEEDS WALK** — accept as price of self-contained reproducibility, OR move weights to provenance once. v0.5 chose self-contained; this is a deliberate trade-off. Document in v0.6. |
| F-v5-10 | "Forced culturally discouraged" detection (Phase 3 step 7) only fires when ALL feasible walls are DISCOURAGED. But a wall might be DISCOURAGED *for one category* (bathroom on north) while PREFERRED for another (pooja on north). Detection logic over-triggers in mixed scenarios. | **NEEDS WALK** — refine detection to "all walls feasible-for-this-cluster's-primary-category have DISCOURAGED cultural_score". Bake into v0.6. |

**REJECTED-AS-CONSIDERED**:
- "Should `WetZoneRiskBreakdown` carry a derived `aggregate_risk: PlacementRiskLevel`?" — No. Walk #4 #10 explicitly split for non-aggregation. Adding it back loses the architectural win.
- "Should `WetZonePlanProvenance` track which Phase 0 / Phase 1a / Phase 1b / Phase 2 / Phase 3 caused which decision?" — Already in `cluster_decisions` and `rule_trace`. Fine-grained per-phase trace would explode trace size. Defer to B-219 replay.
- "Should we encode 'product layer must prompt for Vastu profile' in this spec?" — No. Product UX is out of spec scope. Document in C10 v1 product release notes.

**Audit summary**: 0 patch-now, 8 walk findings open (F-v5-1 to F-v5-10 excluding F-v5-1 NO-ACTION + F-v5-7 NO-ACTION), 3 rejected. F-v5-5 is a real spec bug that needs v0.6 fix.

**Self-coverage measurement**:
- Walk #4 reviewer found 18; my v0.4 audit caught 6 (33%).
- v0.5 audit catches 10 findings unprompted, including 1 real bug (F-v5-5).
- If next reviewer round finds <10, my coverage is improving.

---

## § 10 — Status

- **v0.5 PROPOSED**. **NOT LOCKED.**
- LOCK BLOCKED on:
  - C7 amendment v0.3 (B-212) reaching LOCK
  - F-v5-2, F-v5-3, F-v5-5 (real bug), F-v5-6, F-v5-9, F-v5-10 (6 walk findings) resolved
  - Q22-Q25 (4 open questions) adjudicated
  - F-v5-1, F-v5-4, F-v5-7, F-v5-8 NO-ACTION/CLARIFICATION-only
- Estimated walks to LOCK: **1 more** after v0.5 → v0.6 (the spec is converging; reviewer items are diminishing in architectural scope, increasing in detail-level).

---

**End of v0.5 PROPOSED.** Awaits Ramalingam's reading + walk #5 direction (parallel to C7 amendment walk #2).
