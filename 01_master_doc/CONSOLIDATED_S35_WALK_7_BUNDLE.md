# BuildemUp S35 Walk #7 — Updated Consolidated Bundle

**Status**: All artefacts PROPOSED. **Neither LOCKED** per Ramalingam directive.
**Authored**: S35 Walk #7 close.
**Bundle scope**: C7 amendment v0.6 + C10 v0.8 + 2 plumbing KBs + reclassified backlog + Rule 11 calibration (7 walks).

---

# Table of Contents

1. [Status & LOCK Path](#status--lock-path)
2. [What Changed in Walk #7](#what-changed-in-walk-7)
3. [C7 Amendment v0.6 PROPOSED](#c7-amendment-v06-proposed)
4. [C10 v0.8 PROPOSED](#c10-v08-proposed)
5. [KB: plumbing_minimums.json v1 DRAFT](#kb-plumbing_minimums-v1-draft)
6. [KB: plumbing_fixture_profiles.json v2 DRAFT](#kb-plumbing_fixture_profiles-v2-draft)
7. [Reclassified Backlog (28 items, 6 tiers)](#reclassified-backlog)
8. [Rule 11 Self-Coverage Calibration (7 walks)](#rule-11-self-coverage-calibration)
9. [Open at Session Close](#open-at-session-close)

---

# Status & LOCK Path

```
S35 Walk #7 close — LOCK PATH

      [C7 amendment v0.6 PROPOSED — NOT LOCKED per directive]
              ↓ (Ramalingam: `lock it` per Rule 8)
              ↓ + F-v6-W1 dependency placement decision
      [C7 amendment LOCKED]                                ←── unblocks B-212
              ↓
      [C10 v0.8 PROPOSED]
              ↓ (1 walk: F-v8-6 real bug + 5 minor + Q37/Q38/Q39)
      [C10 v0.9 PROPOSED → LOCKED]
              ↓
      [C10 build session: ~165 tests, ~2320 cumulative passing]
              ↓
      Pre-launch gates (B-220 + B-222 CORRECTNESS-CRITICAL)
              ↓
      Public ship
```

| Artefact | Version | Status | Walks until LOCK |
|---|---|---|---|
| C7 amendment | v0.6 | PROPOSED | 0-1 (F-v6-W1 + Ramalingam declaration) |
| C10 | v0.8 | PROPOSED | 1 (F-v8-6 fix in v0.9) |
| kb/plumbing_minimums.json | v1 | DRAFT | locks with C10 |
| kb/plumbing_fixture_profiles.json | v2 | DRAFT | locks with C10 |

**Pre-launch gates (NOT pre-LOCK per Q29)**: B-220 + B-222.

---

# What Changed in Walk #7

6 amendments absorbed: 1 in C7, 5 in C10. **3 architectural wins** + **3 sharper formulations**.

## C7 Amendment v0.5 → v0.6 (1 amendment)

1. **Canonical accessor** — `Grid.wall_segments_canonical()` method (renamed at audit from `iter_wall_segments_canonical` per F-v6-W3) + `assert_wall_segment_order_independent()` test helper. Moves W8 from "test discipline" to "API enforcement" without runtime overhead. **3 new tests** (target 14 → 17).

## C10 v0.7 → v0.8 (5 amendments)

2. **Cluster spatial-occupancy check (Q32 / Walk #7 #2)** — Phase 0.5 augmented with `Σ liveability_min_width_m <= usable_wall_length_m` per cluster. Uses C9's existing `RoomSizeRequirement.liveability_min_width_m` field — **zero C9 amendment cost** (verified by S35 grep). Surfaces late spatial-infeasibility early. New invariant Inv 19. New failure_phase value `"pre_clustering_spatial"`.

3. **Retry-orchestration RemediationHint (Q33 / Walk #7 #9)** — added `retry_priority: int`, `mutually_exclusive_with: tuple[str, ...]`, `expected_success_probability: float | None`. Defaults per kind documented. Phase 5 detects mutually-exclusive hints. Web-evidence backed: deterministic retry priority is a real engineering pattern.

4. **Dual-bound trap-arm (Q34 / Walk #7 #3)** — `trap_arm_distances` value type promoted from `float` to `TrapArmEstimate(upper_bound_m, likely_bound_m)`. Inv 11 RAISE iff BOTH bounds exceed; WARN if only upper exceeds. Likely_bound = 0.5 × upper at v1 (refined post-ship via B-232). **Reduces false-rejection on narrow Indian bathrooms.**

5. **Bend rename + mode (Q35 / Walk #7 #4)** — `bend_count` renamed to `symbolic_bend_estimate`; new `bend_estimation_mode: Literal["symbolic_v1"]` field. Field name now self-documents non-engineering-grade nature. New Inv 20.

6. **Interim wall capacity weighting (Q36 / Walk #7 #7)** — `WetZoneScoringWeights.fixture_capacity_weights` (WC=2.0, shower=1.5, lavatory/sink=1.0, floor_drain=0.5). Phase 3 capacity check uses cluster-weight sum vs wall-capacity, not room count. Fixes "3 WC bathrooms = 3 utility sinks" false-equivalence. Interim until B-220 + B-229 full DFU values.

## Backlog updates

- **B-239 IMPLEMENTED-IN-SPEC**: cluster-occupancy check shipped at v0.8 (zero C9 cost). Mark RESOLVED at LOCK.
- **B-229 effort reduced**: interim weighting shipped; full DFU = post-launch with B-220.
- **B-232 effort reduced**: dual-bound shipped; calibration = post-ship.
- **B-240 NEW**: extract `canonical_serialize` to `buildemup.utilities` shared module. Resolves F-v6-W1 (C7 amendment v0.6 audit). v2.

---

# C7 Amendment v0.6 PROPOSED

**Component 7 (Structural Grid Engine) — additive amendment for B-212**
**Status**: PROPOSED. NOT LOCKED per Ramalingam directive. 1 walk finding open (F-v6-W1).

## Schema

```python
WALL_ORDER_CONVENTION: Final[str] = "CCW_FROM_SOUTH"
WALL_AXIS_CANONICAL_ORDER: Final[tuple[WallAxis, ...]] = (
    WallAxis.SOUTH, WallAxis.EAST, WallAxis.NORTH, WallAxis.WEST,
)


class WallAxis(str, Enum):
    NORTH = "north"; SOUTH = "south"; EAST = "east"; WEST = "west"


class WallTag(str, Enum):
    EXTERNAL = "external"; INTERNAL = "internal"; LOAD_BEARING = "load_bearing"


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


def serialize_tags_sorted(tags: frozenset[WallTag]) -> tuple[str, ...]:
    return tuple(sorted((t.value for t in tags)))


def assert_wall_segment_order_independent(fn):    # NEW v0.6 — test helper
    """Calls fn(grid) twice — default + shuffled wall_segments order.
    Asserts canonical_serialize(result_a) == canonical_serialize(result_b).
    """
    ...


@dataclass(frozen=True)
class Grid:
    # ... existing fields ...
    wall_segments: tuple[WallSegment, ...] = ()

    def wall_segment_by_id(self, wall_id: str) -> WallSegment: ...

    # NEW v0.6 (Walk #7 #1):
    def wall_segments_canonical(self) -> tuple[WallSegment, ...]:
        """Production code MUST use this. Returns walls in (SOUTH, EAST, NORTH, WEST) order."""
        by_axis = {w.axis: w for w in self.wall_segments}
        return tuple(by_axis[a] for a in WALL_AXIS_CANONICAL_ORDER if a in by_axis)
```

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
| **W8 (REVISED v0.6)** | **All production code paths consuming Grid wall data MUST use `Grid.wall_segments_canonical()`.** Direct iteration over `Grid.wall_segments` reserved for canonical-serialisation snapshots. Algorithms using canonical accessor MUST produce byte-identical output regardless of `wall_segments` storage order. Verified by C7 → C9 → C10 integration shuffle test. | API + TEST |

## Test target: ~17 new tests; cumulative ~2172 passed.

## Open

- **F-v6-W1**: `assert_wall_segment_order_independent` needs `canonical_serialize` from C10 (or shared utility). Two paths: (a) extract to `buildemup.utilities` (B-240 file), (b) test-helper imports from C10. Recommendation (b) for v1; B-240 for v2.

---

# C10 v0.8 PROPOSED

**Component 10 (Bathroom + Wet-Zone Stack Planner)**
**Status**: PROPOSED. NOT LOCKED. **F-v8-6 real bug** to fix in v0.9.

## § 0 Architectural notes (carried from v0.7)

- C10 emits constraints, groupings, engineering primitives. C11 places. C14 scores.
- What C10 is NOT: consumer scores, acoustic/privacy, global optimisation, hydraulic simulation, MCS/MUS.
- Q19 product-onboarding contract; B-236 telemetry.
- Plumbing code framing: India adopts UPC via IPA; B-222 verifies primary-source.

## Schema (v0.8 additions)

```python
@dataclass(frozen=True)
class TrapArmEstimate:                                    # NEW v0.8 (Q34)
    upper_bound_m: float                                   # Manhattan worst-case-corner
    likely_bound_m: float                                  # 0.5 × upper at v1; refined via B-232


@dataclass(frozen=True)
class RemediationHint:                                    # REVISED v0.8 (Q33)
    kind: Literal["relax_config","increase_limit","alternative_routing","manual_review"]
    parameter: str
    current_value: Any
    suggested_value: Any
    severity: Literal["low","medium","high"]
    human_readable: str
    retry_priority: int                                    # NEW v0.8
    mutually_exclusive_with: tuple[str, ...]               # NEW v0.8
    expected_success_probability: float | None             # NEW v0.8 (None at v1)


@dataclass(frozen=True)
class WetZoneScoringWeights:
    # ... carried v0.7 ...
    fixture_capacity_weights: dict[str, float] = field(default_factory=lambda: {
        "water_closet": 2.0, "shower": 1.5, "bathtub": 1.5,
        "lavatory": 1.0, "kitchen_sink": 1.0, "utility_sink": 1.0,
        "floor_drain": 0.5,
    })                                                     # NEW v0.8 (Q36)


@dataclass(frozen=True)
class WetZonePlan:
    # ... carried v0.7, with these revisions ...
    trap_arm_distances: dict[tuple[str, str], TrapArmEstimate]    # REVISED v0.8: TrapArmEstimate replaces float
    symbolic_bend_estimate: int                                   # RENAMED from bend_count (Q35)
    bend_estimation_mode: Literal["symbolic_v1"]                  # NEW v0.8 (Q35)
    # ... rest carried ...
```

## § 3 Behaviour summary (Phase changes)

| Phase | v0.8 change |
|---|---|
| 0 | Production code uses `grid.wall_segments_canonical()` (C7 v0.6 W8 enforcement) |
| 0.5 | + cluster spatial-occupancy check (Inv 19); HARD-edge pairs aggregated |
| 1a/1b | UNCHANGED |
| 2 | UNCHANGED |
| 3 | Capacity uses `cluster_capacity_weight` via `fixture_capacity_weights` |
| 4 | Dual-bound trap-arm; symbolic_bend_estimate + mode |
| 5 | RemediationHint retry-priority + mutually-exclusive detection |

## § 4 Invariants (20 total — added Inv 19 cluster occupancy + Inv 20 bend mode)

Inv 1-10, 13-16 carried from v0.7. Inv 11 revised for dual-bound. Inv 17 revised for cluster_capacity_weight. Inv 18 carried. Inv 19/20 new.

## § 5 Failure modes

```
WetZonePlanError [carries remediation_hints + failure_phase]
├── PerCandidateError
│   ├── WetZoneInfeasibleError (consolidated)
│   │   └── PreClusteringInfeasibleError
│   │       (failure_phase ∈ {"pre_clustering", "pre_clustering_spatial", "assignment"})
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError
│   ├── WallCapacityExceededError
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow
└── KBVersionMismatchError
```

`failure_phase="pre_clustering_spatial"` is the new v0.8 value for cluster-occupancy infeasibility.

## Test target: ~165 tests; cumulative ~2320 passed.

## Open at v0.8

- **F-v8-6 (REAL BUG)**: cluster-occupancy check timing — should run after Phase 2 merge (final cluster composition), not before. v0.9 fix.
- F-v8-1, F-v8-2, F-v8-3, F-v8-7, F-v8-10 walk findings (mostly minor)
- Q37 (likely-bound 0.5 factor), Q38 (capacity weight source), Q39 (mutually-exclusive exhaustive)
- LOCK BLOCKER: C7 amendment v0.6 must LOCK first

---

# KB: plumbing_minimums.json v1 DRAFT

(UNCHANGED from v0.7 bundle. 7 fixture rows + global slope constants.)

| fixture_type | trap_arm_max_m | source |
|---|---|---|
| water_closet | 1.83 | UPC §1002.2 |
| lavatory | 1.07 | IPC Table 909.1 |
| shower | 1.52 | IPC Table 909.1 |
| bathtub | 1.52 | IPC Table 909.1 |
| kitchen_sink | 1.07 | IPC Table 909.1 |
| utility_sink | 1.07 | IPC Table 909.1 |
| floor_drain | 1.52 | IPC Table 909.1 (secondary_unverified) |

`min_slope_per_m=0.0208`, `max_slope_per_m=0.083`.

**B-222 verification scope**: NBC 2016 Part 9 + IS 1742 + state codes.

---

# KB: plumbing_fixture_profiles.json v2 DRAFT

(UNCHANGED from v0.7 bundle.)

| room_category | bathroom_subtype | fixture_types |
|---|---|---|
| bathroom | combined | (water_closet, lavatory, shower) |
| bathroom | bath_only | (lavatory, shower) |
| bathroom | wc_only | (water_closet,) |
| kitchen | null | (kitchen_sink,) |
| utility | null | (utility_sink,) |

`_compatible_with_minimums_kb_version: "Plumbing_v1_S35_DRAFT"`.

---

# Reclassified Backlog (28 open / 3 resolved, 6 tiers)

## CORRECTNESS-CRITICAL (pre-launch gates) — 2

| ID | Description |
|---|---|
| **B-220** | Full hydraulic primitives + plumbing-engineer review |
| **B-222** | Plumbing KB primary-source verification (NBC 2016 Part 9 + IS 1742 + state codes) |

## INFRASTRUCTURE — 8

| ID | Description |
|---|---|
| B-219 | Deterministic-replay tests with hash snapshots; calibrate Q24/Q31/Q37 |
| B-224 | RegulatoryConfidenceFramework |
| B-234a | KB registry validator tooling |
| B-234b | KB semantic-integrity validator depth |
| B-236 | `scoring_profile_explicitly_set` telemetry |
| B-237 | Test-suite modernisation (Hypothesis, scenario gen, snapshot compression, debug shuffle) |
| B-238 | Independent architect review |
| **B-240 (NEW)** | Extract `canonical_serialize` to `buildemup.utilities` shared module — resolves C7→C10 test-helper dependency |

## OPTIMIZATION — 4

| ID | Description |
|---|---|
| B-213 | Adaptive `max_risers` formula |
| B-216 | `adjacency_threshold_m` default tuning |
| B-223 | Memoised score cache, complexity metrics |
| B-228 | Adaptive `wall_reuse_penalty` |

## FEATURE (v2+) — 4

| ID | Description |
|---|---|
| B-225 | Multi-anchor RiserGroup (schema forward-compat shipped; v2 removes invariant) |
| B-227 | Luxury fixture KB extension |
| B-229 | DFU-aware wall capacity (interim shipped at v0.8; full DFU = v2 with B-220) |
| B-232 | Probable-fixture-zone heuristic (dual-bound shipped at v0.8; calibration future) |

## POLYGONAL (B-066 era) — 4

| ID | Description |
|---|---|
| B-217 | Three-tier wall classes |
| B-226 | `acceptable_wall_sets` polygonal pruning |
| B-231 | Wall lookup O(1) optimisation |
| B-235 | WallTag domain split |

## RESEARCH (v3+) — 2

| ID | Description |
|---|---|
| B-230 | Full MCS/MUS infeasibility diagnosis |
| B-233 | Proper orthogonal routing graph for `symbolic_bend_estimate` |

## DORMANT — 2

| ID | Description |
|---|---|
| B-214 | Per-bathroom subtype propagation (depends on B-208) |
| B-215 | Refine "minimum stack-fit length" (rolls into B-220) |

## RESOLVED — 3

| ID | Description | Resolution |
|---|---|---|
| B-218 | C8 oriented_candidate ref preservation | RESOLVED-AS-MISFRAMED at S35 Walk #2 |
| B-221 | Structured RemediationHint | IMPLEMENTED in C10 v0.6 |
| **B-239** | Cluster spatial-occupancy check | IMPLEMENTED in C10 v0.8 (zero C9 cost via existing `liveability_min_width_m`); confirms RESOLVED at LOCK |

---

# Rule 11 Self-Coverage Calibration (7 walks)

| Walk | My audit | Reviewer | Self-coverage | Maturity signal |
|---|---|---|---|---|
| 1 (C10 v0.1 DRAFT) | 7 | 12 | 58% | DRAFT |
| 2 (C10 v0.2 PROPOSED) | 8 | 15 | 40% | Architecture forming |
| 3 (C10 v0.3 PROPOSED) | 8 | 16 | 31% | Architecture solidifying |
| 4 (C10 v0.4 PROPOSED) | 10 | 18 | 33% | Architecture stable |
| 5 (combined v0.5 + C7 v0.3) | 15 | 30 | 43% | Refinement |
| 6 (combined v0.6 + C7 v0.4) | 15 | 30 | 43% | Convergence |
| **7 (combined v0.7 + C7 v0.5)** | **(no v0.8 audit yet at review time)** | **10** | **60%** | **Strong convergence** |

**Walk #7 signals**:
- Reviewer count dropped 67% (30 → 10).
- Self-coverage jumped 43% → 60%.
- Reviewer's overall-assessment confirms LOCK-readiness convergence.
- 6 of 10 reviewer items already-self-found; 3 genuinely new sharp catches; 1 already-resolved.

**Architectural pattern confirmed**: complex multi-phase specs converge in 5-7 walks. Self-coverage rises as architecture stabilises.

---

# Open at Session Close

## C7 amendment v0.6

- **Awaits**: Ramalingam adjudication (no LOCK declaration assumed per directive).
- F-v6-W1: `canonical_serialize` placement — recommend (b) C10 import for v1; B-240 for v2.
- F-v6-W3 patched inline at audit (method renamed `iter_wall_segments_canonical` → `wall_segments_canonical`).

## C10 v0.8

- **F-v8-6 real bug**: cluster-occupancy check should run *after* Phase 2 merge against final composition — currently spec says "after seed step but before merge". v0.9 fix mandatory.
- 5 minor walk findings (F-v8-1 dual-bound per-fixture refinement, F-v8-2 capacity-vs-scoring naming, F-v8-3 mutex parameter validation, F-v8-7 runtime measurement scope, F-v8-10 dead-weight expected_success_probability)
- 3 open questions Q37-Q39
- **LOCK BLOCKER**: C7 amendment v0.6 must LOCK first

## Path forward (next session)

1. Ramalingam reads bundle + Walk #7 review
2. Adjudication on C7 v0.6 (LOCK or one more pass)
3. v0.9 walk fixing F-v8-6 + minor findings
4. C10 v0.9 LOCKs after that walk
5. C10 build session (~165 tests, ~2320 cumulative passing)
6. Pre-launch: B-220 + B-222
7. Public ship

---

**End of bundle. S35 Walk #7 close.**

**Session artefact map** (in `/home/claude/work/buildemup/s35_outputs/`):
- `02_specs_chronological/56_C7_AMENDMENT_v0_6_PROPOSED.md` (~290 lines)
- `02_specs_chronological/57_C10_SPEC_v0_8_PROPOSED.md` (~620 lines)
- `04_backlog/buildemup_v2_backlog_S35_walk_6.md` (carried; B-239 RESOLVED at v0.8 + B-240 added)
- `01_master_doc/CONSOLIDATED_S35_WALK_7_BUNDLE.md` (this file)

**Earlier session artefacts** (in `/home/claude/work/buildemup/s34_outputs/`):
- C10 spec evolution: v0.1 DRAFT → v0.2 → v0.3 → v0.4 → v0.5 → v0.6 → v0.7 → v0.8
- C7 amendment evolution: v0.2 → v0.3 → v0.4 → v0.5 → v0.6
- KBs: plumbing_minimums v1, plumbing_fixture_profiles v2
- Walk #5 bundle, Walk #6 bundle, Walk #7 bundle

---

**Per Obligation 3 / Rule 10**: at session-end, master doc + NEXT_CLAUDE_HANDOFF.md update needed before handoff bundle assembly. Per Rule 10.7, "hand off" → status-block + three-check plan FIRST, then bundle assembly only after Ramalingam confirms.
