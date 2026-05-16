# BuildemUp S35 Walk #6 — Final Consolidated Bundle

**Status**: All artefacts PROPOSED. **C7 amendment v0.5 = LOCK CANDIDATE.** **C10 v0.7 = 1 walk away from LOCK.** Awaiting Ramalingam adjudication for next session.
**Authored**: S35 Walk #6 close.
**Bundle scope**: C7 amendment v0.5 + C10 v0.7 + 2 plumbing KBs + reclassified backlog + Rule 11 calibration (6 walks).

---

# Table of Contents

1. [Status & LOCK Path](#status--lock-path)
2. [What Changed in Walk #6](#what-changed-in-walk-6)
3. [C7 Amendment v0.5 PROPOSED — LOCK CANDIDATE](#c7-amendment-v05-proposed--lock-candidate)
4. [C10 v0.7 PROPOSED](#c10-v07-proposed)
5. [KB: plumbing_minimums.json v1 DRAFT](#kb-plumbing_minimums-v1-draft)
6. [KB: plumbing_fixture_profiles.json v2 DRAFT](#kb-plumbing_fixture_profiles-v2-draft)
7. [Reclassified Backlog (26 items, 6 tiers)](#reclassified-backlog)
8. [Rule 11 Self-Coverage Calibration (6 walks)](#rule-11-self-coverage-calibration)
9. [Walk-Resolution Log](#walk-resolution-log)
10. [Open at Session Close](#open-at-session-close)

---

# Status & LOCK Path

```
S35 Walk #6 close — LOCK PATH

      [C7 amendment v0.5 PROPOSED — LOCK CANDIDATE]
              ↓ (Ramalingam: `lock it` per Rule 8)
      [C7 amendment LOCKED]                                ←── unblocks B-212
              ↓
      [C10 v0.7 PROPOSED]
              ↓ (1 walk: F-v7-2/3/5/7 + Q30/Q31)
      [C10 v0.8 PROPOSED → LOCKED]
              ↓
      [C10 build session: ~155 tests, ~2310 cumulative passing]
              ↓
      Pre-launch gates (B-220 + B-222 CORRECTNESS-CRITICAL)
              ↓
      Public ship
```

| Artefact | Version | Status | Walks until LOCK |
|---|---|---|---|
| C7 amendment | v0.5 | **LOCK CANDIDATE** | 0 (awaits Ramalingam) |
| C10 | v0.7 | PROPOSED | 1 |
| kb/plumbing_minimums.json | v1 | DRAFT | locks with C10 |
| kb/plumbing_fixture_profiles.json | v2 | DRAFT | locks with C10 |

**Pre-launch gates (NOT pre-LOCK per Q29)**: B-220 (full hydraulics) + B-222 (KB primary-source verification).

**Currently shipped (Track 3 canonical, 17-component architecture)**: 9 of 17 components. Test baseline at S34 close: 2155 passed / 3 skipped.

---

# What Changed in Walk #6

20 amendments absorbed into v0.7 (11 new from Walk #6 + 9 carried from prior batch-yes).

## C7 Amendment v0.4 → v0.5 (3 changes)

1. F-v4-W1 verdict: W8 stays test-level only; debug shuffle deferred to B-237.
2. NEW W8 strengthening: integration shuffle test spans full C7 → C9 → C10 chain (canonical-JSON comparison, not pickle — per audit fix F-v5-W1).
3. Test target: 13 → 14 (+1 integration test).

## C10 v0.6 → v0.7 (11 walk-#6 amendments)

1. **Phase 0.5 memoisation** — `acceptable_wall_sets` intersection cached; complexity bounded.
2. **`WallScoreVector.scoring_weights_hash`** — SHA256 hex for self-contained replay (Q27).
3. **Semantic-integrity KB validator** — extends version-drift check with plausible-range + unit consistency + orphan-minimum warnings.
4. **Error consolidation** — `PreClusteringInfeasibleError` becomes subclass of `WetZoneInfeasibleError`; `failure_phase` field distinguishes.
5. **Canonical serialisation discipline** — module-level `canonical_serialize()` + sort discipline per field.
6. **`anchors: tuple[RiserAnchor, ...]`** — forward-compat schema with v1 invariant `len==1` (Q28).
7. **`WetZonePerformanceBudgets`** — config dataclass with budgets; warning-tier on exceed (`performance_budget_warnings` provenance field).
8. **Backlog reclassification** — 6-tier criticality axis baked into § 8.
9. **Plumbing code framing** — § 0 paragraph documenting India's UPC-via-IPA adoption per Walk #6 web evidence.
10. **CORRECTNESS-CRITICAL pre-launch gates** — B-220 + B-222 flagged; v1 LOCK proceeds without them per Q29 Option B.
11. **`bend_count` informational note clarified** — not engineering-grade; B-233 covers proper routing.

## C10 v0.6 → v0.7 (9 amendments carried from prior batch-yes)

12. `_observational_runtime_ms` JSON underscore prefix (F-v6-2)
13. `RemediationHint.suggested_value: Any` documented per-kind (F-v6-3)
14. Lazy validator runs on first `plan_wet_zones` (F-v6-5)
15. B-236 filed for `scoring_profile_explicitly_set` telemetry (F-v6-6)
16. `rejected_alternatives: tuple[tuple[str, str], ...]` (wall_id, reason) (F-v6-7)
17. Aggregate all infeasible HARD-edge pairs in single error (F-v6-9)
18. Risk-axis thresholds ad-hoc; tune via B-219 (Q24)
19. RemediationHint severity defaults per kind (Q25)
20. bend_count stays in `WetZonePlan` (Q26)

## Backlog updates

- B-222: description amended — primary-source verification scope expanded (NBC 2016 Part 9 + IS 1742 + state codes); CORRECTNESS-CRITICAL flagged.
- B-225: schema forward-compat shipped at v0.7; effort reduced M → S.
- B-234: split into B-234a (registry validator tooling) + B-234b (semantic integrity validator).
- **B-237 NEW**: test-suite modernisation (Hypothesis, scenario gen, snapshot compression).
- **B-238 NEW**: independent architect review.

---

# C7 Amendment v0.5 PROPOSED — LOCK CANDIDATE

**Component 7 (Structural Grid Engine) — additive amendment for B-212**
**LOCK CANDIDATE**: 0 open questions, 0 walk findings. F-v5-W1 patched inline at audit.

## Schema

```python
WALL_ORDER_CONVENTION: Final[str] = "CCW_FROM_SOUTH"


class WallAxis(str, Enum):
    """`NORTH` = PROJECT-NORTH (+y of envelope coord system).
    True-north handled by C6 OrientedCandidate; C7 does not rotate.
    """
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
    """Tuple chosen over frozenset for deterministic ordering."""
    return tuple(sorted((t.value for t in tags)))


@dataclass(frozen=True)
class Grid:
    # ... existing fields ...
    wall_segments: tuple[WallSegment, ...] = ()    # backwards-compat default

    def wall_segment_by_id(self, wall_id: str) -> WallSegment: ...   # O(N), B-231 polygonal
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
| W8 | Downstream consumers MUST treat `wall_segments` as set-membership; algorithms MUST produce byte-identical output regardless of tuple iteration order. C7 → C9 → C10 integration shuffle-order regression test verifies (canonical-JSON comparison). | TEST-LEVEL |

## Test target: ~14 new tests; cumulative ~2169 passed.

**Awaits**: Ramalingam `lock it` declaration per Rule 8.

---

# C10 v0.7 PROPOSED

**Component 10 (Bathroom + Wet-Zone Stack Planner)**
**LOCK BLOCKED on**: C7 amendment v0.5 LOCK + 4 v0.7 walk findings + 2 open questions.

## § 0 Architectural notes

C10 emits **constraints, groupings, engineering primitives**. C11 places. C14 scores.

**What C10 is NOT**:
- Does not produce consumer-facing scores (C14 owns plan quality).
- Does not handle acoustics, privacy, sleeping-adjacency conflicts (C14).
- Does not optimise globally (C11a's 9 mutation operators).
- Does not run hydraulic simulation (B-220 plumbing-engineer review).
- Does not run MCS/MUS infeasibility diagnosis (B-230 = v3+ research).

**Q19 product-onboarding contract**: C10's default `scoring_profile="neutral"` is the safe-when-unset value. **Product layer MUST prompt user to select scoring_profile at project setup**. B-236 tracks compliance telemetry.

**Plumbing code framing**: India formally adopts UPC via IPA modification. v1 KB rows sourced to UPC/IPC valid for Indian deployments; B-222 (CORRECTNESS-CRITICAL pre-launch gate) verifies primary-source against NBC 2016 Part 9 + IS 1742 + state-specific codes.

## § 2 Schema (key elements)

```python
@dataclass(frozen=True)
class RemediationHint:
    kind: Literal["relax_config","increase_limit","alternative_routing","manual_review"]
    parameter: str
    current_value: Any
    suggested_value: Any
    severity: Literal["low","medium","high"]    # default: relax=low, manual=high, others=medium
    human_readable: str


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
    scoring_weights_hash: str          # NEW v0.7: SHA256 for self-contained replay


@dataclass(frozen=True)
class RiserGroup:
    group_id: str
    anchors: tuple[RiserAnchor, ...]   # NEW v0.7: forward-compat; v1 invariant len==1
    wet_room_ids: tuple[str, ...]


@dataclass(frozen=True)
class WetZonePerformanceBudgets:       # NEW v0.7
    max_wall_score_vectors: int = 100
    max_provenance_rule_trace_entries: int = 500
    max_remediation_hints: int = 20


@dataclass(frozen=True)
class WetZonePlanConfig:
    # ... carried from v0.6 ...
    scoring_profile: Literal["vastu_strict","vastu_soft","neutral"] = "neutral"
    max_backtrack_states: int = 100
    max_assignment_attempts: int = 50
    trap_arm_tolerance_m: float = 0.15
    performance_budgets: WetZonePerformanceBudgets = field(default_factory=...)   # NEW v0.7
```

## § 3 Behaviour summary (6 phases)

| Phase | Purpose | Key feature |
|---|---|---|
| 0 | Compute `acceptable_wall_sets[room_id]` | Neutral profile: no axis-based POOJA exclusion |
| 0.5 | Pairwise pre-clustering compatibility | Memoised; aggregates infeasible pairs in single error |
| 1a | Engineering feasibility filter | Length + EXTERNAL only |
| 1b | Cultural + adjacency ranking | `WallScoreVector` w/ `scoring_weights_hash` |
| 2 | Wet-room clustering | Common-feasible-wall merge |
| 3 | Wall assignment + backtracking | Forced-culture-override per-category; consolidated `WetZoneInfeasibleError(failure_phase=...)` |
| 4 | Trap-arm distance | Manhattan worst-case-corner; bend_count symbolic informational |
| 5 | Provenance + risk breakdown | 3-axis weighted-severity; `performance_budget_warnings` |

**FP discipline**: full-precision compare with `EPSILON=1e-9`; integer/lex tie-breaks; 6dp serialisation only.

**Canonical serialisation** (NEW v0.7): module-level `canonical_serialize()` + per-field sort discipline; byte-identical replay across iteration orderings.

**KB cross-validation** (REVISED v0.7): version drift + semantic integrity (plausible-range, unit consistency, orphan-minimum warnings).

## § 4 Invariants (18 — added Inv 18 for performance budget warnings)

Inv 1-17 carried from v0.6. **Inv 18 (NEW v0.7)**: `performance_budget_warnings` populated when budgets exceeded; descriptive only, no enforcement.

## § 5 Failure modes (REVISED v0.7 — error consolidation)

```
WetZonePlanError [carries remediation_hints + failure_phase]
├── PerCandidateError
│   ├── WetZoneInfeasibleError                          (consolidated)
│   │   └── PreClusteringInfeasibleError                (subclass: failure_phase="pre_clustering")
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError
│   ├── WallCapacityExceededError
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow                            (systemic)
└── KBVersionMismatchError                              (startup-time)
```

## Test target: ~155 tests; cumulative ~2310 passed.

## Open at v0.7

- 4 walk findings (F-v7-2 hash canonical-input, F-v7-3 plausible-range citations, F-v7-5 BudgetWarning structure, F-v7-7 subclass redundancy) — mostly v0.8 refinement
- 2 open questions (Q30 hash truncation, Q31 budget calibration)
- LOCK BLOCKER: C7 amendment v0.5 must LOCK first

---

# KB: plumbing_minimums v1 DRAFT

**7 fixture rows + global slope constants. UPC/IPC sourced (India adopts UPC via IPA per Walk #6 web evidence). All marked `secondary_consensus` or `secondary_unverified` pending B-222 primary-source verification.**

| fixture_type | trap_arm_max_m | min_pipe_diameter_mm | trap_seal_min_mm | source |
|---|---|---|---|---|
| water_closet | 1.83 | 100 | 50 | UPC §1002.2 (3" trap = 6 ft) |
| lavatory | 1.07 | 32 | 38 | IPC Table 909.1 (1-1/2" trap = 42 in) |
| shower | 1.52 | 50 | 50 | IPC Table 909.1 (2" trap = 60 in) |
| bathtub | 1.52 | 50 | 50 | IPC Table 909.1 |
| kitchen_sink | 1.07 | 38 | 50 | IPC Table 909.1 |
| utility_sink | 1.07 | 38 | 50 | IPC Table 909.1 |
| floor_drain | 1.52 | 50 | 50 | IPC Table 909.1 (secondary_unverified) |

**Global**: `min_slope_per_m = 0.0208` (1/4"/ft); `max_slope_per_m = 0.083` (one diameter/ft).

**B-222 verification scope**: NBC 2016 Part 9 + IS 1742 + state-specific Indian codes (Tamil Nadu CDBR, etc.). Replace all `secondary_*` flags with `primary_verified`.

---

# KB: plumbing_fixture_profiles v2 DRAFT

**5 mapping rows + cross-KB version pinning.**

| room_category | bathroom_subtype | fixture_types |
|---|---|---|
| bathroom | combined | (water_closet, lavatory, shower) |
| bathroom | bath_only | (lavatory, shower) |
| bathroom | wc_only | (water_closet,) |
| kitchen | null | (kitchen_sink,) |
| utility | null | (utility_sink,) |

**v2 metadata**: `_compatible_with_minimums_kb_version: "Plumbing_v1_S35_DRAFT"`. Cross-KB validator at C10 startup catches drift + semantic integrity issues (per v0.7 extension).

---

# Reclassified Backlog (26 open / 2 resolved, 6 tiers)

## CORRECTNESS-CRITICAL (pre-launch gates) — 2

| ID | Description |
|---|---|
| **B-220** | Full hydraulic primitives + plumbing-engineer review |
| **B-222** | Plumbing KB primary-source verification (NBC 2016 Part 9 + IS 1742 + state codes) |

Production default: `require_verified_plumbing=True` until both complete.

## INFRASTRUCTURE — 7

| ID | Description |
|---|---|
| B-219 | Deterministic-replay tests with hash snapshots; calibrate Q24/Q31 |
| B-224 | RegulatoryConfidenceFramework (when 3rd verification system arrives) |
| B-234a | KB registry validator tooling |
| B-234b | KB semantic-integrity validator depth |
| B-236 | `scoring_profile_explicitly_set` telemetry |
| B-237 | Test-suite modernisation (Hypothesis, scenario gen, snapshot compression, debug shuffle) |
| B-238 | Independent architect review |

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
| B-227 | Luxury fixture KB extension (bidet, dual sinks, dishwasher) |
| B-229 | DFU-aware wall capacity |
| B-232 | Probable-fixture-zone heuristic |

## POLYGONAL (B-066 era) — 4

| ID | Description |
|---|---|
| B-217 | Three-tier wall classes (EXTERNAL/SERVICE_CORE/INTERIOR) |
| B-226 | `acceptable_wall_sets` polygonal pruning |
| B-231 | Wall lookup O(1) optimisation |
| B-235 | WallTag domain split |

## RESEARCH (v3+) — 2

| ID | Description |
|---|---|
| B-230 | Full MCS/MUS infeasibility diagnosis |
| B-233 | Proper orthogonal routing graph for bend_count |

## DORMANT — 2

| ID | Description |
|---|---|
| B-214 | Per-bathroom subtype propagation (depends on B-208) |
| B-215 | Refine "minimum stack-fit length" (rolls into B-220) |

## RESOLVED — 2

| ID | Description | Resolution |
|---|---|---|
| B-218 | C8 oriented_candidate ref preservation | RESOLVED-AS-MISFRAMED at S35 Walk #2 (chain already exists) |
| B-221 | Structured RemediationHint | IMPLEMENTED in C10 v0.6 |

---

# Rule 11 Self-Coverage Calibration

| Walk | My audit | Reviewer | Overlap | Self-coverage | Maturity signal |
|---|---|---|---|---|---|
| 1 (C10 v0.1 DRAFT) | 7 | 12 | 7 | 58% | DRAFT (high — author's "unknowns" list) |
| 2 (C10 v0.2 PROPOSED) | 8 | 15 | 6 | 40% | Architecture forming |
| 3 (C10 v0.3 PROPOSED) | 8 | 16 | 5 | 31% | Architecture solidifying |
| 4 (C10 v0.4 PROPOSED) | 10 | 18 | 6 | 33% | Architecture stable |
| 5 (combined v0.5 + C7 v0.3) | 15 | 30 | 13 | 43% | Refinement |
| 6 (combined v0.6 + C7 v0.4) | 15 | 30 | 13 | 43% | **Convergence** (flat = signal) |

**Empirical patterns confirmed**:
- Self-coverage scales **inversely with spec complexity**. Small additive amendments (C7) hit 70%; complex multi-phase planners stabilise at 30-40%.
- DRAFT-stage audits hit higher coverage (58%) because author's "unknowns" list IS the audit.
- External review consistently finds 60-70% of new architectural issues my audit misses.
- **Walk #6 flat 43% alongside Walk #5 is the strongest convergence signal yet** — reviewer no longer finding architectural depth my audit misses; remaining gap is mostly meta-concerns + sharp incremental catches.

**Real-bug catch rate**: ~10% of audit findings are spec bugs vs walk-level concerns. Known catches:
- F-v4-4 (v0.4): wording fix
- F-v4-6 (v0.4): trivial Inv 18 dropped
- F-v6-1 (v0.6): Phase 0 temporal-split wording
- F-v5-W1 (C7 v0.5 audit): pickle → canonical-JSON for W8 integration test

**Future calibration (Walk #6 #26)**: severity-weighted scoring (critical/major/minor/cosmetic) instead of raw overlap counts. Documented for future Track 3 component spec arcs.

---

# Walk-Resolution Log

6 critique walks. Cumulative Q-resolutions:

| Q | Final | Walk |
|---|---|---|
| Q1 | Single-floor scope | #1 |
| Q2 | Wet-rooms include kitchen + utility (separate riser group) | #1 |
| Q3 | Hard verdict + grouping primitives, NO consumer scores | #1 |
| Q4 | One plan per candidate; C11a explores | #1 |
| Q5 | Pattern A fail-fast | #1 |
| Q6 | `acceptable_wall_set` (set, not predicted side) | #2 |
| Q11 | Per-fixture trap-arm `(room_id, fixture_type)` | #3 |
| Q12 → Q19 | Default `neutral` + product-onboarding contract | #3 → #4 → #5 |
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
| Q24 | Risk-axis thresholds ad-hoc; tune via B-219 | #5 |
| Q25 | RemediationHint severity defaults per kind | #5 |
| Q26 | bend_count stays in WetZonePlan schema | #5 |
| **Q27** | scoring_weights_hash on WallScoreVector | #6 |
| **Q28** | `anchors: tuple[...]` forward-compat (v1 invariant len==1) | #6 |
| **Q29** | v1 LOCK = architectural completeness; B-220/B-222 = pre-launch gates | #6 |

**C7 amendment Q-resolutions**:

| Q | Final | Walk |
|---|---|---|
| Q-W1 | Default `()` for backwards-compat | #2 |
| Q-W2 | Externals-only in v1 | #2 |
| Q-W3 | No column refs in WallSegment v1 | #2 |
| Q-W4 | NO wall_thickness in v1 | #2 (revisit at Walk #5) |
| Q-W5 | NO warn-on-empty | #2 (revisit at Walk #5) |
| Q-W6 | YES `WALL_ORDER_CONVENTION` constant | #2 |
| F-v4-W1 | W8 test-level only; debug shuffle = B-237 | #5 |

**Open at session close (v0.7 + C7 v0.5)**: Q30 (hash truncation), Q31 (budget calibration), F-v7-2/3/5/7.

---

# Open at Session Close

## C7 amendment v0.5 LOCK CANDIDATE

- **Awaits**: Ramalingam `lock it` declaration per Rule 8
- F-v5-W1 patched inline at audit (canonical-JSON for W8 integration test)
- 0 open questions, 0 walk findings
- Test target: ~14 new tests, no regressions on existing 174 C7 tests

## C10 v0.7 PROPOSED

- **LOCK BLOCKED on**: C7 amendment v0.5 LOCK + 4 walk findings + 2 open questions
- F-v7-2: `scoring_weights_hash` input is `canonical_serialize(weights)` — minor docs fix
- F-v7-3: plausible-range thresholds in KB validator need IPC/NBC citations — minor
- F-v7-5: `performance_budget_warnings: tuple[str, ...]` strings vs structured — defer to v2
- F-v7-7: `PreClusteringInfeasibleError` subclass + `failure_phase` field redundancy — keep subclass for `isinstance()` ergonomics
- Q30: hash truncation to 16-char prefix — recommend yes for v0.8
- Q31: performance budget calibration — ad-hoc v1, tune via B-219
- **Estimated walks to LOCK: 1** (v0.8 likely refinement-only)

## Path forward (next session)

**Recommended order**:
1. **Ramalingam declares `lock it` on C7 amendment v0.5** → C7 LOCKED, B-212 cleared
2. **One more walk on C10 v0.7** (or batch-yes-to-recommendations) → C10 v0.8 PROPOSED → LOCK
3. **C10 build session**: ~155 tests, target ~2310 cumulative passing
4. **Pre-launch**: B-220 + B-222 CORRECTNESS-CRITICAL gates complete
5. **Public ship**

---

**End of bundle. S35 Walk #6 close.**

**Session artefact map** (in `/home/claude/work/buildemup/s35_outputs/`):
- `02_specs_chronological/54_C7_AMENDMENT_v0_5_PROPOSED_LOCK_CANDIDATE.md` (261 lines)
- `02_specs_chronological/55_C10_SPEC_v0_7_PROPOSED.md` (~600 lines)
- `04_backlog/buildemup_v2_backlog_S35_walk_6.md` (reclassified, 26 open / 2 resolved)
- `01_master_doc/CONSOLIDATED_S35_WALK_6_BUNDLE.md` (this file)

Earlier session artefacts (in `/home/claude/work/buildemup/s34_outputs/02_specs_chronological/`):
- C10 spec evolution: v0.1 DRAFT (file 42) → v0.2 (44) → v0.3 (46) → v0.4 (47) → v0.5 (50)
- C7 amendment evolution: v0.2 (43) → v0.3 (49)
- KBs: plumbing_minimums v1 (45), plumbing_fixture_profiles v1 (48)
- Walk #5 bundle: `s35_outputs/01_master_doc/CONSOLIDATED_S35_WALK_5_BUNDLE.md`
