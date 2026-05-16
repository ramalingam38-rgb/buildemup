# BuildemUp S35 Walk #5 — Consolidated Spec Bundle

**Status**: All artefacts PROPOSED. NONE LOCKED. Awaiting Ramalingam adjudication.
**Authored**: S35 Walk #5 outcome.
**Bundle contents**: C7 amendment v0.4 + C10 v0.6 + 2 plumbing KBs + status + backlog + Rule 11 calibration.

---

# Table of Contents

1. [Status & LOCK Path](#status--lock-path)
2. [C7 Amendment v0.4 PROPOSED — LOCK candidate](#c7-amendment-v04-proposed)
3. [C10 v0.6 PROPOSED](#c10-v06-proposed)
4. [KB: plumbing_minimums.json v1 DRAFT](#kb-plumbing_minimumsjson-v1-draft)
5. [KB: plumbing_fixture_profiles.json v2 DRAFT](#kb-plumbing_fixture_profilesjson-v2-draft)
6. [Active Backlog](#active-backlog)
7. [Rule 11 Self-Coverage Calibration](#rule-11-self-coverage-calibration)
8. [Walk-Resolution Log (5 walks)](#walk-resolution-log)

---

# Status & LOCK Path

```
S35 Walk #5 close — LOCK PATH

      [C7 amendment v0.4 PROPOSED]
              ↓ (1 walk away from LOCK; F-v4-W1 verdict needed)
      [C7 amendment LOCKED]                                ←── unblocks B-212
              ↓
      [C10 v0.6 PROPOSED]
              ↓ (1-2 walks; F-v6-2/3/5/6/7/9 + Q24-Q26)
      [C10 v0.7 PROPOSED]
              ↓
      [C10 LOCKED]                                          ←── ready for build
              ↓
      [C10 build session: ~145 tests, ~2300 cumulative passing]
```

| Artefact | Version | Status | Walks until LOCK |
|---|---|---|---|
| C7 amendment | v0.4 | PROPOSED | 0-1 (F-v4-W1 verdict only) |
| C10 | v0.6 | PROPOSED | 1-2 |
| kb/plumbing_minimums.json | v1 | DRAFT | locks with C10 |
| kb/plumbing_fixture_profiles.json | v2 | DRAFT | locks with C10 |

**Currently shipped (Track 3 canonical, 17-component architecture)**: 9 of 17 components shipped. Components SHIPPED at S34 close: C1, C2, C3a (S1 of 8 sub-shipped), C4, C5, C6, C7, C8, C9. Test baseline: 2155 passed / 3 skipped.

---

# C7 Amendment v0.4 PROPOSED

**Component 7 (Structural Grid Engine) — additive amendment for B-212**
**LOCK candidate**: 1 walk finding open (F-v4-W1: test-level discipline for Inv W8). All v0.3 walk items resolved.

## Schema additions

```python
WALL_ORDER_CONVENTION: Final[str] = "CCW_FROM_SOUTH"   # exposed module constant


class WallAxis(str, Enum):
    """`NORTH` = PROJECT-NORTH (+y of envelope coord system).
    True-north handled by C6 OrientedCandidate; C7 does not rotate."""
    NORTH = "north"
    SOUTH = "south"
    EAST  = "east"
    WEST  = "west"


class WallTag(str, Enum):
    EXTERNAL      = "external"
    INTERNAL      = "internal"
    LOAD_BEARING  = "load_bearing"


@dataclass(frozen=True)
class WallSegment:
    wall_id: str
    axis: WallAxis
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float
    length_m: float
    tags: frozenset[WallTag]
    # __post_init__ enforces W1, W2, W3


def serialize_tags_sorted(tags: frozenset[WallTag]) -> tuple[str, ...]:
    """Centralized helper for deterministic provenance and replay snapshots."""
    return tuple(sorted((t.value for t in tags)))


# Grid dataclass: additive change
@dataclass(frozen=True)
class Grid:
    # ... existing fields ...
    wall_segments: tuple[WallSegment, ...] = ()    # default for backwards-compat

    def wall_segment_by_id(self, wall_id: str) -> WallSegment: ...   # O(N), B-231 tracks polygonal opt
```

## v1 emitted walls (rectangular envelope, CCW from south)

| wall_id | axis | start | end | length_m | tags |
|---|---|---|---|---|---|
| `WALL_SOUTH` | SOUTH | (0, 0) | (W, 0) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_EAST` | EAST | (W, 0) | (W, D) | D | {EXTERNAL, LOAD_BEARING} |
| `WALL_NORTH` | NORTH | (W, D) | (0, D) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_WEST` | WEST | (0, D) | (0, 0) | D | {EXTERNAL, LOAD_BEARING} |

## Invariants W1-W8

| # | Invariant | Mode |
|---|---|---|
| W1 | `length_m` matches Euclidean(start, end) | RAISE |
| W2 | Every WallSegment has at least one WallTag | RAISE |
| W3 | v1 walls axis-aligned | RAISE |
| W4 | v1 Grid has exactly 4 wall_segments | RAISE |
| W5 | Each WallAxis appears exactly once | RAISE |
| W6 | wall_ids unique | RAISE |
| W7 | Total wall length == perimeter (`2W + 2D`) | RAISE |
| **W8** | Downstream consumers must treat `wall_segments` as set-membership; algorithms produce identical output regardless of tuple iteration order | TEST-LEVEL (shuffle-order regression test) |

## Test target: ~13 new tests; cumulative ~2168 passed.

## Open walk question

**F-v4-W1**: W8 enforced at test-level only (no runtime check). Recommend status quo; debug-mode shuffle is over-engineering. Awaits your verdict.

---

# C10 v0.6 PROPOSED

**Component 10 (Bathroom + Wet-Zone Stack Planner)**
**LOCK BLOCKED** on C7 amendment v0.4 LOCK + 6 v0.6 walk findings + 3 open questions.

## § 0 Architectural notes

C10 emits **constraints, groupings, engineering primitives**. C11 places. C14 scores.

**What C10 is NOT**:
- Does not produce consumer-facing scores (C14 owns plan quality).
- Does not handle acoustics, privacy, sleeping-adjacency conflicts (C14).
- Does not optimise globally (C11a's 9 mutation operators).
- Does not run hydraulic simulation (B-220 plumbing-engineer review).
- Does not run MCS/MUS infeasibility diagnosis (B-230 = v3+ research).

**Q19 product-onboarding contract (NEW v0.6)**: C10's default `scoring_profile="neutral"` is the *safe-when-unset* value. **Product layer MUST prompt user to select scoring_profile at project setup.** C10 stays architecturally honest by default; product UX drives explicit Vastu choice for Indian-family target market.

## § 2 Contract

```python
def plan_wet_zones(
    room_sized_candidates: tuple[RoomSizedCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,                                            # carries wall_segments per C7 amendment
    plot_analysis: PlotAnalysis,
    *,
    config: WetZonePlanConfig | None = None,
) -> tuple[WetZonePlannedCandidate, ...]
```

`WetZonePlannedCandidate` = `RoomSizedCandidate` + `wet_zone_plan: WetZonePlan` + `provenance: WetZonePlanProvenance`.

## Schema (key elements)

```python
@dataclass(frozen=True)
class RemediationHint:
    kind: Literal["relax_config","increase_limit","alternative_routing","manual_review"]
    parameter: str
    current_value: Any
    suggested_value: Any
    severity: Literal["low","medium","high"]
    human_readable: str


@dataclass(frozen=True)
class ForcedCultureOverride:
    room_id: str
    wall_id: str
    category: str
    rejected_alternatives: tuple[str, ...]


@dataclass(frozen=True)
class WallScoreVector:
    wall_id: str
    category: str
    engineering_score: float
    cultural_score: float
    adjacency_score: float
    scoring_profile_id: str        # references provenance.scoring_weights_snapshot


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
    optimization_risk: PlacementRiskLevel
    optimization_score: float
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
    bend_count: int                            # informational symbolic heuristic; not engineering-grade
    riser_count: int
    non_wet_room_buffer_zones: tuple[str, ...]
    acceptable_wall_sets: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class WetZonePlanConfig:
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    pooja_adjacency_mode: Literal["strict", "soft"] = "strict"
    max_risers: int | None = None
    adjacency_threshold_m: float = 0.0
    require_master_bath_adjacency: bool = True
    require_verified_plumbing: bool = False
    scoring_weights: WetZoneScoringWeights = field(default_factory=WetZoneScoringWeights)
    scoring_profile: Literal["vastu_strict","vastu_soft","neutral"] = "neutral"   # Q19
    max_backtrack_states: int = 100
    max_assignment_attempts: int = 50
    trap_arm_tolerance_m: float = 0.15
```

## § 3 Behaviour summary (6 phases)

| Phase | Purpose | Key feature |
|---|---|---|
| 0 | Compute `acceptable_wall_sets[room_id]` | F-v5-5 fix: neutral profile = no axis-based POOJA exclusion |
| 0.5 | Pairwise pre-clustering compatibility | NEW v0.6 — surfaces HARD-edge infeasibility before backtracking |
| 1a | Engineering feasibility filter | Per Walk #4 #7: feasibility before ranking |
| 1b | Cultural + adjacency ranking | `WallScoreVector` per wall × category; `scoring_profile_id` reference |
| 2 | Wet-room clustering | Common-feasible-wall merge predicate |
| 3 | Wall assignment with reuse + bounded backtracking | `forced_culturally_discouraged` per-category detection |
| 4 | Trap-arm distance | Manhattan worst-case-corner; bend_count symbolic informational |
| 5 | Provenance + risk breakdown | 3-axis weighted-severity (0.5 / 1.0 / 1.5 weights) |

**FP discipline**: full-precision compare with `EPSILON = 1e-9`; integer/lex tie-breaks; 6dp serialisation only.

**KB cross-validation**: `validate_plumbing_kbs_compatibility()` startup hook raises `KBVersionMismatchError` on version drift between profiles + minimums KBs.

## § 4 Invariants (17)

| # | Description |
|---|---|
| 1-3 | All wet rooms (BATHROOM, KITCHEN, UTILITY) appear in `wet_wall_assignment` |
| 4 | Assigned walls exist in Grid + meet Phase 1a feasibility |
| 5 | Master BA wall ∈ master BR `acceptable_wall_set` |
| 5b | KITCHEN wall adjacent to LIVING/service zone |
| 6 | POOJA same-wall + same-axis exclusion (axis check only when scoring_profile != neutral) |
| 7 | `riser_count >= 1` if wet rooms exist |
| 8 | `riser_count <= effective_max_risers` |
| 9 | room_ids exist in RoomSizeTable |
| 10 | `total_wet_run_length_m >= 0` finite |
| 11 | `trap_arm_distances[(r,f)] <= MAX[f] + tolerance` (RAISE/WARN tiers) |
| 12 | trap_arm_distances populated for every wet room × fixture |
| 13 | RiserGroup.wet_room_ids non-empty |
| 14 | RiserGroup.anchor.wall_id matches member wet_wall_assignment |
| 15 | Assigned wall ∈ acceptable_wall_sets[room_id] |
| 16 | `fixture_types_per_room` keys exist in BOTH plumbing KBs |
| 17 | `riser_count` consistent with wall capacity |

## § 5 Failure modes

```
WetZonePlanError [carries remediation_hints]
├── PerCandidateError
│   ├── WetZoneInfeasibleError
│   ├── PreClusteringInfeasibleError    (NEW v0.6)
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError
│   ├── WallCapacityExceededError
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow            (systemic)
└── KBVersionMismatchError              (NEW v0.6 startup)
```

## Test target: ~145 tests; cumulative ~2300 passed.

## Open at v0.6

- 6 walk findings (F-v6-2 thru F-v6-10 minus inline-fixed F-v6-1, minus minor F-v6-4/F-v6-8/F-v6-10)
- 3 open questions (Q24-Q26)
- LOCK BLOCKER: C7 amendment v0.4 must LOCK first

---

# KB: plumbing_minimums.json v1 DRAFT

**7 fixture rows + global slope constants. IPC/UPC sourced. All marked secondary_consensus or secondary_unverified pending B-222 primary-source verification.**

| fixture_type | trap_arm_max_m | min_pipe_diameter_mm | trap_seal_min_mm | source |
|---|---|---|---|---|
| water_closet | 1.83 | 100 | 50 | UPC §1002.2 / IPC §909.1 (3-inch trap = 6 ft) |
| lavatory | 1.07 | 32 | 38 | IPC Table 909.1 (1-1/2" trap = 42 in) |
| shower | 1.52 | 50 | 50 | IPC Table 909.1 (2" trap = 60 in) |
| bathtub | 1.52 | 50 | 50 | IPC Table 909.1 (2" trap = 60 in) |
| kitchen_sink | 1.07 | 38 | 50 | IPC Table 909.1 (1-1/2" trap = 42 in) |
| utility_sink | 1.07 | 38 | 50 | IPC Table 909.1 (1-1/2" trap = 42 in) |
| floor_drain | 1.52 | 50 | 50 | IPC Table 909.1 (secondary_unverified) |

**Global**: min_slope_per_m = 0.0208 (1/4"/ft); max_slope_per_m = 0.083 (one diameter/ft).

**B-222 verification path**: primary-source pass against NBC 2016 Part 9 + IS 1742 + state-specific Indian codes.

---

# KB: plumbing_fixture_profiles.json v2 DRAFT

**5 mapping rows + cross-KB version pinning per Walk #5 #15.**

| room_category | bathroom_subtype | fixture_types |
|---|---|---|
| bathroom | combined | (water_closet, lavatory, shower) |
| bathroom | bath_only | (lavatory, shower) |
| bathroom | wc_only | (water_closet,) |
| kitchen | null | (kitchen_sink,) |
| utility | null | (utility_sink,) |

**v2 change from v1**: added `_compatible_with_minimums_kb_version: "Plumbing_v1_S35_DRAFT"`. Cross-KB validator at C10 startup catches drift.

**Forward-compat (B-227 luxury fixtures)**: bidet, dual_kitchen_sink, dishwasher_drain, washing_machine_drain, water_purifier_drain — each adds row to plumbing_minimums first, then references here.

---

# Active Backlog

**OPEN at S35 Walk #5 close** (24 items):

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-212** | C7 WallSegment emission — **BLOCKER for C10 LOCK** | S35 Walk #1 | C7 v0.4 LOCK | M (in progress) |
| B-213 | Adaptive `max_risers` formula based on envelope width + wet-room count | S35 Walk #1 | post-ship tuning | S |
| B-214 | Per-bathroom subtype propagation | S35 Walk #1 | depends on B-208 | XS |
| B-215 | Refine "minimum stack-fit length" (v1: 1.5m heuristic) | S35 Walk #2 | plumbing-engineer review | S |
| B-216 | `adjacency_threshold_m` default tuning post-C11 placement | S35 Walk #2 | post C11 ship | XS |
| B-217 | Three-tier wall classification (EXTERNAL/SERVICE_CORE/INTERIOR) | S35 Walk #2 | post B-066 polygonal | M |
| B-219 | Deterministic-replay tests with hash snapshots | S35 Walk #2 | post C10 ship | XS |
| B-220 | Full hydraulic primitives (DFU, slope, vent stack) | S35 Walk #2 | plumbing-engineer review | L |
| B-221 | Structured `RemediationHint` (resolved by Walk #5 #2 — implemented in v0.6) | S35 Walk #2 | implemented | done |
| B-222 | Plumbing KB primary-source verification (IS/NBC) | S35 Walk #2 | pre-launch | M |
| B-223 | Performance hardening (memoised score cache, complexity metrics) | S35 Walk #3 | post-ship if slow | M |
| B-224 | `RegulatoryConfidenceFramework` unified verification | S35 Walk #3 | when 3rd verification system | L |
| B-225 | Multi-anchor RiserGroup support | S35 Walk #3 | v2 luxury-tier | M |
| B-226 | `acceptable_wall_sets` polygonal pruning | S35 Walk #3 | post B-066 | S |
| B-227 | Luxury fixture KB extension (bidet, dual sinks, dishwasher) | S35 Walk #4 | post v1 + market signal | XS |
| B-228 | Adaptive `wall_reuse_penalty` | S35 Walk #4 | post-ship tuning | S |
| B-229 | DFU-aware wall capacity | S35 Walk #4 | resolves with B-220 | M |
| B-230 | MCS/MUS full IIS infeasibility diagnosis (research-grade) | S35 Walk #4 | v3+ research | XL |
| B-231 | Wall lookup O(1) optimisation | S35 Walk #5 | post B-066 | XS |
| B-232 | Probable-fixture-zone heuristic | S35 Walk #5 | post v1 + empirical tuning | M |
| B-233 | Proper orthogonal routing graph for bend_count | S35 Walk #5 | when C12 spec exists | L |
| B-234 | Plumbing-KB registry validator tooling | S35 Walk #5 | post v1 ship | S |
| B-235 | WallTag domain split | S35 Walk #5 | when 5+ tags exist | S |

**RESOLVED at S35**: B-218 (RESOLVED-AS-MISFRAMED at Walk #2 audit); B-221 (implemented in C10 v0.6).

---

# Rule 11 Self-Coverage Calibration

| Walk | My audit found | Reviewer found | Overlap | Self-coverage |
|---|---|---|---|---|
| 1 (C10 v0.1 DRAFT) | 7 | 12 | 7 | 58% |
| 2 (C10 v0.2 PROPOSED) | 8 | 15 | 6 | 40% |
| 3 (C10 v0.3 PROPOSED) | 8 | 16 | 5 | 31% |
| 4 (C10 v0.4 PROPOSED) | 10 | 18 | 6 | 33% |
| 5 (C10 v0.5 PROPOSED) | 10 | 18 (C10) | 6 | 33% |
| 5 (C7 v0.3 PROPOSED) | 5 | 10 | 7 | 70% |
| 5 (combined) | 15 | 30 | 13 | **43%** |

**Empirical patterns**:
- Self-coverage scales **inversely with spec complexity**. Small additive amendments (C7) hit 70%; complex multi-phase planners (C10) stabilise at 30-40%.
- DRAFT-stage audits hit higher coverage (58%) because the spec author's "what I don't know" list IS the audit. PROPOSED audits drop because the author has more committed claims to defend.
- External review consistently finds 60-70% of new architectural issues my audit misses. **Rule 7 + Rule 11 are correctly complementary**, not redundant.
- Real-bug catch rate at audit: 1 inline-fix per 10 audit findings (F-v4-4 v0.4, F-v6-1 v0.6). ~10% of findings are spec bugs vs walk-level concerns.

---

# Walk-Resolution Log

5 critique walks completed at C10. Cumulative resolutions:

**Q-resolutions** (architectural decisions):

| Q | Final | Walk |
|---|---|---|
| Q1 | Single-floor scope | #1 |
| Q2 | Wet-rooms include kitchen + utility (separate riser group) | #1 |
| Q3 | Hard verdict + grouping primitives, NO consumer scores | #1 |
| Q4 | One plan per candidate; C11a explores | #1 |
| Q5 | Pattern A fail-fast | #1 |
| Q6 | `acceptable_wall_set` (set, not predicted side) | #2 |
| Q11 | Per-fixture trap-arm `(room_id, fixture_type)` | #3 |
| Q12 → Q19 | Default `neutral` + product-onboarding spec | #3 → #4 → #5 |
| Q13 | column_id optional bonus | #3 |
| Q14 | `WetZoneRiskBreakdown` 3-axis | #2 → #4 |
| Q-W3-1 | Phase 2 merge = common-feasible-wall | #3 → #4 |
| Q-W3-2 | Full-precision compare; 6dp serialise | #3 → #4 |
| Q-W3-3 | Weighted-sum + multi-axis breakdown | #3 |
| Q19 (revised) | Default neutral + product-layer prompts explicit choice | #4 → #5 |
| Q20 | `max_runtime_ms` DROPPED | #4 |
| Q21 | Rule-based hints v1; B-230 IIS for v3+ | #4 |
| Q22 | PreClusteringInfeasibleError = PerCandidateError tier | #5 |
| Q23 | bend_count downgraded to informational | #5 |

**Open at v0.6**: Q24 (risk threshold tuning), Q25 (severity defaults per RemediationHint kind), Q26 (bend_count schema location).

**Open at C7 v0.4**: F-v4-W1 (W8 test-level vs runtime).

---

**Bundle assembled at S35 Walk #5 close. All artefacts PROPOSED. Ramalingam adjudication next round.**
