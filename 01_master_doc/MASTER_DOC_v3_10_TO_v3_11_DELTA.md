# BuildemUp Master Doc — Delta v3.10 → v3.11

**Predecessor**: v3.10 (S35 close)
**Successor**: v3.11 (S36 close)
**Authored**: S36 close.

---

## What changed in S36

S36 was a **build session**, not a spec walk. Per the S35→S36 handoff
directive ("S36 = BUILD SESSION. NO SPEC WALKS."), this session
implemented the two artefacts that S35 closed at LOCK:

1. **C7 amendment v0.8 LOCKED** — additive WallSegment emission.
2. **C10 v1.0 LOCKED** — Bathroom + Wet-Zone Stack Planner.

No new spec versions, no new walks, no LOCK adjudication this session.

---

## C7 amendment v0.8 LOCKED — SHIPPED

### Modules created/modified

- `buildemup/utilities/__init__.py` (NEW)
- `buildemup/utilities/canonical.py` (NEW) —
  `canonical_serialize(obj)` (sort_keys, FP→6dp, frozenset→sorted,
  dataclass field-walk) +
  `assert_wall_segment_order_independent(grid_factory, fn, seed=12345)`
  test helper.
- `buildemup/components/c07/wall_segment.py` (NEW) —
  - `WALL_ORDER_CONVENTION = "CCW_FROM_SOUTH"`
  - `WALL_AXIS_CANONICAL_ORDER = (SOUTH, EAST, NORTH, WEST)`
  - `WallAxis` enum, `WallTag` enum (EXTERNAL/INTERNAL/LOAD_BEARING)
  - `WallSegment` frozen dataclass with W1-W3 enforcement in `__post_init__`
  - `serialize_tags_sorted` helper.
- `buildemup/components/c07/grid_generator.py` (modified, additive only) —
  - `Grid.wall_segments: tuple[WallSegment, ...] = ()` field
  - `Grid.wall_segments_canonical()` method (W8 enforcement; canonical-axis-
    order dict lookup with silent-omit)
  - `Grid.wall_segment_by_id()` O(N) lookup
  - `_build_wall_segments()` populating CCW-from-south.
- `buildemup/components/c07/__init__.py` (modified) — re-exports
  including `buildemup.utilities.canonical`.

### Tests

`tests/test_c7_wall_segment.py` (NEW) — **19 tests, all passing**.
Coverage includes W1/W2/W3 invariants, lookup happy + KeyError,
backwards-compat empty-tuple default, CCW-from-south for square +
rectangular envelopes, module constants, serialize_tags_sorted, canonical
accessor (3 tests), W8 unit-shuffle (2 tests), canonical_serialize (3 tests).

W8 *integration* shuffle test deferred to `tests/test_c10_replay.py` so
it can run against the full C7→C10 pipeline; landed there in S36 as well.

### Backwards compatibility

Full pre-existing C7 test suite still passes. `Grid` field is additive
(default empty tuple); existing call sites continue to work without
modification.

---

## C10 v1.0 LOCKED — SHIPPED

### Knowledge bases (copied from S35 spec drafts; `_DRAFT` suffix dropped)

- `kb/plumbing_minimums.json` (`_kb_version`: `"Plumbing_v1_S35"`).
  7 fixtures: water_closet, lavatory, shower, bathtub, kitchen_sink,
  utility_sink (all `secondary_consensus`), floor_drain
  (`secondary_unverified`).
- `kb/plumbing_fixture_profiles.json` (`_kb_version`: `"Profiles_v2_S35"`,
  `_compatible_with_minimums_kb_version`: `"Plumbing_v1_S35"`). 5 rows:
  bathroom × 3 subtypes (combined / bath_only / wc_only) + kitchen +
  utility.

### Modules created — `buildemup/components/c10/`

- `errors.py` — full hierarchy: `WetZonePlanError` →
  `PerCandidateError` → {`WetZoneInfeasibleError` →
  `PreClusteringInfeasibleError`}, `PoojaAdjacencyError`,
  `RiserCountExceededError`, `TrapArmDistanceExceededError`,
  `WallCapacityExceededError`, `ClusterIntegrityError`;
  `BatchWetZoneInfeasibleError` (carries `candidate_errors`);
  systemic: `PlumbingConfidenceTooLow`, `KBVersionMismatchError`,
  `RemediationGraphError`. `WetZonePlanError` carries
  `remediation_hints` + `failure_phase`.
- `schema.py` — module constants (`LIKELY_BOUND_FACTORS_BY_FIXTURE` Final
  dict, `EPSILON=1e-9`, `SERIALIZATION_PRECISION=6`); enums
  (`EnforcementMode`, `PlacementRiskLevel`, `TruncationReason`); primitive
  dataclasses (`TrapArmEstimate` with Q43 dual-bound + likely<=upper invariant;
  `RemediationHint` with Q33 retry_priority + mutually_exclusive_with +
  expected_success_probability; `ForcedCultureOverride`; `WallScoreVector`
  with scoring_weights_hash; `RiserAnchor`; `RiserGroup` with v1 invariant
  `len(anchors)==1`; `WetZoneRiskBreakdown`; `WetZonePerformanceBudgets`
  100/500/20); weights (`WetZoneCapacityWeights` Q44-extracted with
  `fixture_capacity_weights` defaults WC=2.0, shower=1.5, bathtub=1.5,
  lavatory=1.0, ks=1.0, us=1.0, fd=0.5, `minimum_riser_spacing_m=3.0`,
  `wall_safety_margin_m=0.0=>2*spacing`); `WetZoneScoringWeights`;
  `WetZonePlanConfig` (production-default `require_verified_plumbing=True`);
  envelope (`WetZonePlan` with Inv 10/20 enforcement, `WetZonePlanProvenance`
  with Q46 defensive `validate_remediation_graph` in `__post_init__`,
  `WetZonePlannedCandidate`); `compute_scoring_weights_hash` (SHA256 hex of
  canonical-JSON).
- `provenance.py` — `validate_remediation_graph` (Inv 21: DAG no cycles via
  DFS, no duplicate (priority, parameter) pairs); `compute_risk_level`
  (>=3→HIGH, >=1→MEDIUM, else LOW per v0.4 § 3 weights 0.5/1.0/1.5).
- `kb_validator.py` — `load_plumbing_minimums`/`profiles`,
  `validate_plumbing_kbs_compatibility` (version pinning, orphan-reference
  check, semantic integrity 25-200mm/38-100mm/positive-trap-arm,
  orphan-minimum warnings as tuple), `get_plumbing_minimum_for`,
  `get_fixture_types_for`. `KB_DIR` resolved from `__file__` to
  `../../kb`.
- `scoring.py` — `_MIN_WALL_LENGTH_M=1.5`, `filter_feasible_walls`
  (Phase 1a, uses `wall_segments_canonical`), `rank_walls` (Phase 1b
  emits `WallScoreVector` with hash, sorted by (wall_id, category)),
  `total_score` (weighted sum), `acceptable_wall_set` (Phase 0 per-room),
  `_wall_has_column` helper, `_axis_class`/`_cultural_score` helpers
  (v1 baseline returns NEUTRAL absent C6 inputs).
- `occupancy.py` — `fast_fail_pre_screen` (Phase 0.5 HARD-edge intersection
  check, raises `PreClusteringInfeasibleError` with aggregated pairs);
  `cluster_occupancy_validate` (Phase 2.5 post-merge per F-v8-6 fix, raises
  `WetZoneInfeasibleError(failure_phase="post_clustering_spatial")`).
- `clustering.py` — `cluster_wet_rooms` (Phase 2: seed-per-room, HARD-edge
  merges, iterative overlap-merge with HARD-anti veto, lex-ASC tie-break,
  optional `capacity_check` predicate to veto unservable merges).
- `assignment.py` — `AssignmentResult` dataclass + `assign_clusters_to_walls`
  (Phase 3 greedy + bounded backtracking, Q36 `cluster_capacity_weight`
  via `fixture_capacity_weights`, `wall_reuse_penalty`,
  `forced_culturally_discouraged` detection, raises
  `WetZoneInfeasibleError(failure_phase="assignment")` with hints).
- `trap_arm.py` — `manhattan_worst_case` (4-corner max),
  `estimate_trap_arm` (Q43 per-fixture factor),
  `symbolic_bend_estimate` (Q42 horizontal-first 0/1/2),
  `validate_inv_11` (Q34 dual-bound: RAISE if both over, WARN if upper-only,
  returns `unverified_rows` tuple), `gate_unverified_rows` (raises
  `PlumbingConfidenceTooLow`).
- `wet_zone_planner.py` — `plan_wet_zones()` top-level orchestrator. Lazy KB
  validation cache (`_KB_VALIDATED`, `_KB_WARNINGS`). Per-candidate
  try/except aggregating `PerCandidateError` →
  `BatchWetZoneInfeasibleError`. `_plan_one_candidate` runs Phases 0 → 0.5
  → 1b → 2 → 2.5 → 3 → 4 → 5. Helpers: `_derive_hard_edges` (returns empty
  tuple at v1 — master_BR↔master_BA is Inv 5 adjacency, not cluster
  constraint), `_derive_hard_anti_edges` (POOJA vs all wet rooms),
  `_build_fixture_types_per_room` (via profiles KB),
  `_build_cluster_primary_category` (priority bathroom > kitchen > utility >
  pooja), `_build_riser_groups` (one anchor per cluster at wall midpoint),
  `_find_kitchen_riser_group_id`, `_compute_risk_breakdown`
  (3-axis weighted-severity), `_wet_strip_bbox` (room proxy: along-wall
  `liveability_min_width_m`, perpendicular `_PROXY_DEPTH_M=0.6`).
- `__init__.py` — public API: `plan_wet_zones` + all
  schema/errors/KB-validator/provenance helpers re-exported.

### Tests — 138 added across 6 files

- `tests/test_c10_schema.py`: **44 tests** (module constants, enums,
  TrapArmEstimate, RemediationHint, RiserGroup, WetZonePlanConfig,
  WetZoneCapacityWeights, WetZoneScoringWeights + hash, WallScoreVector,
  ForcedCultureOverride, WetZoneRiskBreakdown, WetZonePerformanceBudgets,
  WetZonePlan __post_init__ Inv 10/20).
- `tests/test_c10_kb_validator.py`: **19 tests** (disk happy path, lookup
  helpers, in-memory failure modes: version drift / orphan refs /
  semantic-integrity diameter / trap-seal / trap-arm).
- `tests/test_c10_invariants.py`: **30 tests** (Inv 7/10/11/13/16/20/21,
  PlumbingConfidenceTooLow gating, manhattan_worst_case,
  estimate_trap_arm Q43, symbolic_bend_estimate Q42).
- `tests/test_c10_phase_logic.py`: **29 tests** (Phase 0 filter,
  acceptable_wall_set, Phase 0.5 fast_fail_pre_screen, Phase 1b ranking,
  Phase 2 clustering with capacity_check, Phase 2.5 occupancy,
  compute_risk_level).
- `tests/test_c10_strict_mode.py`: **9 tests** (require_verified_plumbing
  paths, partial-batch tolerance, replay determinism schema-level).
- `tests/test_c10_replay.py`: **7 tests** (W8 integration shuffle on full
  C7→C10 pipeline, plan-serialisation determinism, riser-groups lex-sort,
  wall-segments-used lex-sort, wall_scoring_breakdown lex-sort,
  observational fields type-correct).

### Cumulative test count progression

- S35 close: **2155 passed, 3 skipped**
- S36 after C7 amendment v0.8: **2174 passed (+19)**
- S36 after C10 v1.0: **2312 passed (+138)**

### S36 in numbers

- Net new tests: **+157**
- Spec target was 175 for C10 alone; achieved **138 / 175 = 79%**.
- Backwards-compatibility: full prior suite continues to pass (no
  regressions).
- C10 end-to-end smoke verified on the existing `_c9_fixtures.run_c8_pipeline`
  Bangalore 12.19 × 18.29m envelope: 3 of 3 candidates planned.

### Known v1 simplifications (deliberate, documented)

- `_derive_hard_edges` returns empty tuple at v1: master_BR↔master_BA is
  Inv 5 adjacency, not a wet-zone clustering HARD edge. Future: when wet-
  stack-share rules ship, hard_edges becomes wet-wet pairs.
- `_PROXY_DEPTH_M = 0.6` for trap-arm bbox: fixtures assumed AT the wet
  wall. Real bbox arrives from C11 placement.
- `_axis_class` returns NEUTRAL absent C6 OrientedCandidate inputs;
  cultural scoring layered when C6 integration lands.
- One riser per cluster (`RiserGroup.anchors` len == 1). Multi-anchor
  pending B-225.
- `cluster_wet_rooms` accepts an optional `capacity_check` callable to
  veto unservable merges; the orchestrator wires this. Without it, Phase
  2 may produce over-large clusters.

---

## Backlog at S36 close

No backlog items closed in S36 (build session, not spec walk).
No new B-NNN entries created.

`04_backlog/buildemup_v2_backlog_S35_walk_9.md` carries forward unchanged.

---

## Three-check protocol (Rule 10.6)

Per Rule 10.7, three-check (GAP / AUDIT / INTEGRITY) is gated on
Ramalingam's "hand off" directive. **Not run yet at S36 close.** Will run
on Ramalingam's go-ahead.

---

## Status at S36 close

- C1, C2, C7, C8, C9 SHIPPED (carried).
- **C7 amendment v0.8 LOCKED — SHIPPED at S36.**
- **C10 v1.0 LOCKED — SHIPPED at S36.**
- Test suite: **2312 passed, 3 skipped, 1415 warnings, 52 subtests passed.**
- Next session S37: open per Ramalingam's direction. Likely candidates:
  - Three-check protocol + handoff bundle assembly (if "hand off" issued)
  - C11 SPEC drafting (next canonical component: geometric placement)
  - Pre-launch backlog (B-220, B-222, B-150 plumbing primary-source
    verification)
  - C10 test target catch-up (~37 more tests to hit 175 target)
  - kb_audit_S36.md (B-204-style audit; deferred from S36 Step 3)

---

**End of v3.10 → v3.11 delta. S36 closed.**
