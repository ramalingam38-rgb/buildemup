# BuildemUp S35 Walk #8 — Final Consolidated Bundle

**Status**: All artefacts PROPOSED. **Neither LOCKED** per Ramalingam directive.
**Authored**: S35 Walk #8 close.
**Bundle scope**: C7 amendment v0.7 + C10 v0.9 + 2 plumbing KBs + reclassified backlog + Rule 11 calibration (8 walks).

---

# Table of Contents

1. [Status & LOCK Path](#status--lock-path)
2. [What Changed in Walk #8](#what-changed-in-walk-8)
3. [C7 Amendment v0.7 PROPOSED](#c7-amendment-v07-proposed)
4. [C10 v0.9 PROPOSED](#c10-v09-proposed)
5. [Plumbing KBs](#plumbing-kbs)
6. [Reclassified Backlog (29 open / 6 resolved, 6 tiers)](#reclassified-backlog)
7. [Rule 11 Self-Coverage Calibration (8 walks)](#rule-11-self-coverage-calibration)
8. [Open at Session Close](#open-at-session-close)

---

# Status & LOCK Path

```
S35 Walk #8 close — LOCK PATH (final cycle)

      [C7 amendment v0.7 PROPOSED — NOT LOCKED per directive]
              ↓ (Ramalingam: `lock it` per Rule 8)
      [C7 amendment LOCKED]                               ←── unblocks B-212
              ↓
      [C10 v0.9 PROPOSED — NOT LOCKED]
              ↓ (Q45 + Q46 verdict; minor refinements)
      [C10 v1.0 PROPOSED → LOCKED]
              ↓
      [C10 build session: ~175 tests, ~2330 cumulative passing]
              ↓
      Pre-launch gates (B-220 + B-222 CORRECTNESS-CRITICAL)
              ↓
      Public ship
```

| Artefact | Version | Status | Walks until LOCK |
|---|---|---|---|
| C7 amendment | v0.7 | PROPOSED — LOCK CANDIDATE | 0 (Ramalingam declaration) |
| C10 | v0.9 | PROPOSED — near LOCK | 0-1 |
| kb/plumbing_minimums.json | v1 | DRAFT | locks with C10 |
| kb/plumbing_fixture_profiles.json | v2 | DRAFT | locks with C10 |

**Pre-launch gates (NOT pre-LOCK)**: B-220 (full hydraulics) + B-222 (KB primary-source verification).

---

# What Changed in Walk #8

5 amendments absorbed into v0.9; 1 architectural-direction fix into C7 v0.7.

## C7 Amendment v0.6 → v0.7 (1 amendment)

1. **B-240 IMPLEMENTED-IN-SPEC** (Walk #8 reviewer #8): `canonical_serialize` extracted to `buildemup.utilities` shared module. `assert_wall_segment_order_independent` test helper relocated. C7 module re-exports for backwards-compat. **Reverses v0.6's deferral** — preserves clean dependency direction. Test target 17 → 20 (audit added 3 utilities tests).

## C10 v0.8 → v0.9 (5 amendments)

2. **F-v8-6 REAL BUG FIXED (Q40)**: Phase 0.5 split into Phase 0.5 (HARD-edge fast-fail) + **Phase 2.5 NEW** (post-merge cluster-occupancy validation). Inv 19 semantic now references final cluster composition. `failure_phase="post_clustering_spatial"` (renamed from v0.8's "pre_clustering_spatial"). **Real bug eliminated.**

3. **Mutex DAG validation (Q41)**: `validate_remediation_graph()` Phase 5 hook + new `RemediationGraphError` systemic exception. Inv 21 NEW. Web-evidence backed: deterministic retry orchestration requires DAG-acyclicity + total-priority-ordering. **B-243 IMPLEMENTED-IN-SPEC.**

4. **Symbolic_bend_estimate routing convention (Q42)**: horizontal-first orthogonal path with lex-ASC anchor wall_id tie-break. Replay-deterministic across implementations. **B-244 IMPLEMENTED-IN-SPEC.**

5. **Per-fixture likely-bound factors (Q43)**: `LIKELY_BOUND_FACTORS_BY_FIXTURE` constant (WC=0.8, lavatory=0.5, shower=0.6, kitchen_sink=0.4, etc.). Replaces v0.8's uniform 0.5 factor. Q45 raises moving to KB; v0.9 keeps as module constant.

6. **Capacity vs scoring naming cleanup (Q44)**: `WetZoneCapacityWeights` extracted from `WetZoneScoringWeights`. Capacity is feasibility, not scoring. Field references updated in Phase 3.

## Backlog updates (Walk #8)

- **B-240 IMPLEMENTED** in C7 v0.7 (`canonical_serialize` extracted)
- **B-243 IMPLEMENTED** in C10 v0.9 (mutex DAG validation)
- **B-244 IMPLEMENTED** in C10 v0.9 (routing convention)
- **B-241 NEW**: CI lint rule for `.wall_segments` direct iteration (post v1)
- **B-242 NEW**: Wall fragmentation modeling — `WallSegment.usable_wall_spans` (post v1)
- **B-245 NEW**: Rule 11 maturity-weighted scoring extension (master_doc work)
- **B-246 NEW**: Move `LIKELY_BOUND_FACTORS_BY_FIXTURE` to plumbing_minimums.json KB

---

# C7 Amendment v0.7 PROPOSED

**LOCK CANDIDATE.** 0 walk findings; 0 open questions. F-v6-W1 resolved via immediate B-240 extraction.

## Key change: utilities module extraction

```python
# NEW v0.7: buildemup/utilities/canonical.py
def canonical_serialize(obj) -> str:
    """Module-level helper for byte-identical replay snapshots.
    Centralised here to avoid C7→C10 test dependency inversion.
    """
    return json.dumps(_canonicalize(obj), sort_keys=True, separators=(",", ":"))


def assert_wall_segment_order_independent(fn):
    """Test helper, relocated from C7 to utilities module."""
    ...


# C7 module re-exports for backwards-compat with v0.6 test code:
from buildemup.utilities.canonical import canonical_serialize, assert_wall_segment_order_independent
```

**No production cycle**: C7 production code does NOT import from `buildemup.utilities`. Only test helpers and C10 cross via the utilities module — clean architectural direction.

## Schema, behaviour, invariants W1-W8 (UNCHANGED from v0.6)

`WALL_AXIS_CANONICAL_ORDER` constant; `WallAxis` / `WallTag` enums; `WallSegment` dataclass with W1-W3 `__post_init__` checks; `Grid` with `wall_segments_canonical()` method; `serialize_tags_sorted()` helper. All carried.

## Test target: ~20 new tests (was 17 in v0.6; +3 for canonical_serialize utilities tests)

Cumulative target post-amendment: 2155 + 20 ≈ 2175 passed.

## § 6 Limitations documented

**Wall fragmentation (B-242)**: v1 models walls as continuous segments. Real walls may have doors/windows/shafts breaking usable span. For typical Indian residential (corner-doors), assumption holds. Future fragmentation support tracked as B-242, post-v1.

---

# C10 v0.9 PROPOSED

**Status**: PROPOSED. NOT LOCKED. **F-v8-6 real bug FIXED** via Phase 0.5/2.5 split.

## § 0 Architectural notes (carried from v0.8)

(See v0.8 — same 5 "what C10 is NOT" items; Q19 product-onboarding contract; plumbing code framing per India UPC adoption; pattern note for B-224 framework.)

## Schema (v0.9 changes)

```python
@dataclass(frozen=True)
class TrapArmEstimate:
    upper_bound_m: float
    likely_bound_m: float           # REVISED v0.9: per-fixture factor × upper (Q43)


@dataclass(frozen=True)
class WetZoneCapacityWeights:                                   # NEW v0.9 (Q44)
    fixture_capacity_weights: dict[str, float] = field(default_factory=lambda: {
        "water_closet": 2.0, "shower": 1.5, "bathtub": 1.5,
        "lavatory": 1.0, "kitchen_sink": 1.0, "utility_sink": 1.0,
        "floor_drain": 0.5,
    })
    minimum_riser_spacing_m: float = 3.0
    wall_safety_margin_m: float = 0.0       # 0 = use 2 * minimum_riser_spacing default


@dataclass(frozen=True)
class WetZoneScoringWeights:
    """REVISED v0.9 (Q44): capacity weights moved to WetZoneCapacityWeights."""
    weight_engineering: float = 1.0
    # ... ranking-only weights (carried) ...


@dataclass(frozen=True)
class WetZonePlanConfig:
    # ... existing ...
    capacity_weights: WetZoneCapacityWeights = field(default_factory=WetZoneCapacityWeights)   # NEW v0.9
    # ... rest carried ...


# NEW v0.9 (Q43) — module constant:
LIKELY_BOUND_FACTORS_BY_FIXTURE: Final[dict[str, float]] = {
    "water_closet": 0.8, "lavatory": 0.5, "shower": 0.6, "bathtub": 0.6,
    "kitchen_sink": 0.4, "utility_sink": 0.4, "floor_drain": 0.7,
}
```

## § 3 Behaviour (Phase changes)

| Phase | v0.9 change |
|---|---|
| 0 | UNCHANGED (uses `grid.wall_segments_canonical()` per C7 v0.7) |
| **0.5** | **REVISED — only HARD-edge fast-fail; cluster-occupancy moved to Phase 2.5** |
| 1a/1b | UNCHANGED |
| 2 | UNCHANGED (merge converges) |
| **2.5** | **NEW — authoritative cluster-occupancy validation against final composition (F-v8-6 fix)** |
| 3 | REVISED — capacity_weights field references relocated |
| 4 | REVISED — per-fixture likely-bound factors + horizontal-first routing convention |
| 5 | REVISED — `validate_remediation_graph()` mutex DAG validation |

## § 4 Invariants (21 total)

Inv 1-18 carried from v0.8. **Inv 19 REVISED** (semantic: post-merge final cluster composition). **Inv 20** carried (bend mode). **Inv 21 NEW**: RemediationHint mutex graph is acyclic; retry_priority + parameter lex form total ordering.

## § 5 Failure modes

```
WetZonePlanError [carries remediation_hints + failure_phase]
├── PerCandidateError
│   ├── WetZoneInfeasibleError (consolidated)
│   │   └── PreClusteringInfeasibleError
│   │       (failure_phase ∈ {"pre_clustering",
│   │                         "post_clustering_spatial",   # RENAMED from v0.8
│   │                         "assignment"})
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError
│   ├── WallCapacityExceededError
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow
├── KBVersionMismatchError
└── RemediationGraphError       (NEW v0.9 — systemic Phase 5 mutex-graph validation)
```

## § 6 Test target: ~175 tests; cumulative ~2330 passed.

## Open at v0.9

- **Q45**: move `LIKELY_BOUND_FACTORS_BY_FIXTURE` to KB (recommended for v1.0; B-246 if not)
- **Q46**: validate mutex graph in `WetZonePlanProvenance.__post_init__` defensively (recommended yes — bake into v0.9 implementation)
- 5 minor walk findings (F-v9-1 inline-fixed; F-v9-2 calibration ad-hoc; F-v9-3 RemediationGraphError no failure_phase; F-v9-5 mode notation; F-v9-6 routing edge cases)
- LOCK BLOCKER: C7 amendment v0.7 must LOCK first

---

# Plumbing KBs

(UNCHANGED from Walk #6/#7 bundles.)

**plumbing_minimums.json v1**: 7 fixture rows + global slope constants. UPC/IPC sourced. Secondary_consensus pending B-222 primary-source verification (NBC 2016 Part 9 + IS 1742).

**plumbing_fixture_profiles.json v2**: 5 mapping rows. `_compatible_with_minimums_kb_version: "Plumbing_v1_S35_DRAFT"`. Cross-KB validator at C10 startup.

---

# Reclassified Backlog (29 open / 6 resolved, 6 tiers)

## CORRECTNESS-CRITICAL — 2

| ID | Description |
|---|---|
| **B-220** | Full hydraulic primitives + plumbing-engineer review |
| **B-222** | Plumbing KB primary-source verification (NBC 2016 Part 9 + IS 1742 + state codes) |

## INFRASTRUCTURE — 8

| ID | Description |
|---|---|
| B-219 | Deterministic-replay tests with hash snapshots; calibrate Q24/Q31/Q37/Q45 |
| B-224 | RegulatoryConfidenceFramework |
| B-234a | KB registry validator tooling |
| B-234b | KB semantic-integrity validator depth |
| B-236 | `scoring_profile_explicitly_set` telemetry |
| B-237 | Test-suite modernisation (Hypothesis, scenario gen, snapshot compression, debug shuffle) |
| B-238 | Independent architect review |
| **B-241** | CI lint rule: forbid `.wall_segments` iteration outside snapshot/test |
| **B-245** | Rule 11 maturity-weighted scoring extension |

## OPTIMIZATION — 4

| ID | Description |
|---|---|
| B-213 | Adaptive `max_risers` formula |
| B-216 | `adjacency_threshold_m` default tuning |
| B-223 | Memoised score cache, complexity metrics |
| B-228 | Adaptive `wall_reuse_penalty` |

## FEATURE (v2+) — 5

| ID | Description |
|---|---|
| B-225 | Multi-anchor RiserGroup (schema forward-compat shipped; v2 removes invariant) |
| B-227 | Luxury fixture KB extension |
| B-229 | DFU-aware wall capacity (interim shipped at v0.8) |
| B-232 | Probable-fixture-zone heuristic (dual-bound + per-fixture factors shipped at v0.9; calibration future) |
| **B-246** | Move `LIKELY_BOUND_FACTORS_BY_FIXTURE` from C10 module to plumbing_minimums KB |

## POLYGONAL (B-066 era) — 5

| ID | Description |
|---|---|
| B-217 | Three-tier wall classes |
| B-226 | `acceptable_wall_sets` polygonal pruning |
| B-231 | Wall lookup O(1) optimisation |
| B-235 | WallTag domain split |
| **B-242** | `WallSegment.usable_wall_spans` for fragmentation |

## RESEARCH (v3+) — 2

| ID | Description |
|---|---|
| B-230 | Full MCS/MUS infeasibility diagnosis |
| B-233 | Proper orthogonal routing graph for `symbolic_bend_estimate` |

## DORMANT — 2

| B-214 (per-bathroom subtype, depends on B-208), B-215 (stack-fit length, rolls into B-220) |

## RESOLVED — 6

| ID | Resolution |
|---|---|
| B-218 | RESOLVED-AS-MISFRAMED at S35 Walk #2 |
| B-221 | IMPLEMENTED in C10 v0.6 (RemediationHint) |
| B-239 | IMPLEMENTED in C10 v0.8 (cluster-occupancy) |
| **B-240** | **IMPLEMENTED in C7 v0.7 (canonical_serialize utilities extraction)** |
| **B-243** | **IMPLEMENTED in C10 v0.9 (mutex DAG validation)** |
| **B-244** | **IMPLEMENTED in C10 v0.9 (routing convention documented)** |

---

# Rule 11 Self-Coverage Calibration (8 walks)

| Walk | My audit | Reviewer | Self-coverage | Maturity signal |
|---|---|---|---|---|
| 1 | 7 | 12 | 58% | DRAFT |
| 2 | 8 | 15 | 40% | Architecture forming |
| 3 | 8 | 16 | 31% | Architecture solidifying |
| 4 | 10 | 18 | 33% | Architecture stable |
| 5 | 15 | 30 | 43% | Refinement |
| 6 | 15 | 30 | 43% | Convergence |
| 7 | (none yet) | 10 | 60% | Strong convergence |
| **8** | **10 (v0.8 audit)** | **12** | **33% raw / 58% effective** | **LOCK readiness** |

**Walk #8 effective self-coverage**: 4 already-self-found + 3 already-resolved-in-newer-version = 7/12 = 58%. Stable.

**Pattern confirmed (8-walk dataset)**:
- Self-coverage stabilises at 30-60% for complex multi-phase specs depending on whether reviewer reads latest content.
- DRAFT-stage 58%, refinement plateau 30-43%, late-convergence 58-60%.
- 4 real bugs caught at audit across 8 walks (~10% of audit findings) — F-v4-4, F-v4-6, F-v6-1, F-v8-6. Rule 11 keeps earning its keep.
- External review consistently complementary, not redundant.

**Reviewer-feeding ergonomics finding (Walk #8)**: 25% of Walk #8 reviewer items were already-resolved-in-newer-version. **For future spec arcs: ensure reviewer is fed latest spec, not consolidated bundle pages of older versions.** B-245 maturity-weighted scoring would surface this distinction.

---

# Open at Session Close

## C7 amendment v0.7 (LOCK CANDIDATE)

- **Awaits**: Ramalingam declaration ("don't lock it yet" carried; awaiting reversal).
- 0 walk findings, 0 open questions.
- B-240 implemented; B-241/B-242 newly filed for post-v1.

## C10 v0.9

- **F-v8-6 REAL BUG FIXED**.
- **B-243 + B-244 implemented** (mutex DAG, routing convention).
- 5 minor walk findings (mostly pass; F-v9-1 inline-fixed).
- 2 open questions (Q45 LIKELY_BOUND_FACTORS to KB, Q46 defensive validation in __post_init__).
- LOCK BLOCKER: C7 amendment v0.7 must LOCK first.

## Spec arc final state

- **8 walks completed.**
- **6 backlog items resolved**: B-218, B-221, B-239, B-240, B-243, B-244.
- **23 backlog items open** (excluding 6 resolved); criticality-classified.
- **2 CORRECTNESS-CRITICAL pre-launch gates**: B-220 (hydraulics), B-222 (KB verification).
- **C7 amendment**: LOCK CANDIDATE. C10: 0-1 walks from LOCK.

## Path forward (next session)

1. Ramalingam reads bundle + Walk #8 review confirmation.
2. Adjudication on C7 v0.7 LOCK declaration.
3. Q45 / Q46 verdicts on C10 v0.9 → v1.0 LOCK candidate.
4. C10 v1.0 LOCKs.
5. C10 build session: ~175 tests, ~2330 cumulative passing.
6. Pre-launch: B-220 + B-222.
7. Public ship.

---

**End of bundle. S35 Walk #8 close.**

**Per Obligation 3 / Rule 10**: this was the final substantive cycle (already past Obligation 3 boundary per your directive). Handoff bundle assembly next per Rule 10.7:
1. You say "hand off"
2. I produce status block + three-check plan FIRST
3. You confirm/correct
4. I assemble v11 handoff bundle

**Session artefact map** (`/home/claude/work/buildemup/s35_outputs/`):
- `02_specs_chronological/`:
  - `54_C7_AMENDMENT_v0_5_PROPOSED_LOCK_CANDIDATE.md` (Walk #6)
  - `55_C10_SPEC_v0_7_PROPOSED.md` (Walk #6)
  - `56_C7_AMENDMENT_v0_6_PROPOSED.md` (Walk #7)
  - `57_C10_SPEC_v0_8_PROPOSED.md` (Walk #7)
  - `58_C7_AMENDMENT_v0_7_PROPOSED.md` (Walk #8 — LOCK CANDIDATE)
  - `59_C10_SPEC_v0_9_PROPOSED.md` (Walk #8 — F-v8-6 fixed)
- `04_backlog/buildemup_v2_backlog_S35_walk_6.md` (carry; needs Walk #8 update for B-240/241/242/243/244/245/246)
- `01_master_doc/`: bundles for Walks #5, #6, #7, #8 (this file)

**Earlier S34 outputs** in `/home/claude/work/buildemup/s34_outputs/` (files 42-50: full v0.1-v0.5 progression).

**Ready for handoff when you say so.**
