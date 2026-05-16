# C11a v0.2 Backlog — S39 Additions (post-patches)

**Session**: S39 (C11a Sub-2 + Sub-3 + Sub-4 build, critique walk,
patches Tier 1 + Tier 2 + Tier 3 partial).
**Filed by**: Claude per Rule 9.2.
**Format**: Mirrors v0_2_backlog_S38_additions.md.

---

## § 1 — Items LANDED at S39 (Sub-5 patches)

The following items from the critique walk were filed AND landed in
the same session, with full test coverage and zero regressions:

### B-NEW-X — WeakSet error registry ✅ LANDED

- **Implementation**: `errors.py` — `__init_subclass__` on
  `TopologyMutationError` auto-populates a `weakref.WeakSet`.
  `iter_registered_errors()` returns sorted-by-qualname snapshot.
  `phase0.validate_severity_classification_audit()` walks the
  registry instead of `cls.__subclasses__()`.
- **Tests**: 9 new tests in
  `test_c11a_subsession5_error_registry.py`. Sub-4's existing audit
  tests simplified — try/finally cleanup replaced with `del + gc.collect()`
  per WeakSet semantics.
- **Origin**: S39 critique walk F8.
- **Outcome**: ~half-day estimated, landed in ~30 min. Confirmed
  WeakSet drops dynamically-created subclasses on GC.

### B-NEW-V — Strict candidate-context extractor ✅ LANDED

- **Implementation**: `candidate_context.py` — single canonical
  v1.0 ancestry chain `WetZonePlannedCandidate → room_sized_candidate
  → corridor_designed_candidate → oriented_candidate →
  topology_candidate`. `extract_tier_a_context_from_candidate` raises
  `CandidateContextSchemaError` (per_candidate severity) on missing
  attrs. Dispatcher `extract_tier_a_context` routes real
  `WetZonePlannedCandidate` to strict, synthetic to lenient.
  Lenient extractor preserved for Sub-4 test fixture compatibility.
- **Tests**: 18 new tests in
  `test_c11a_subsession5_candidate_context.py`.
- **Origin**: S39 critique walk F4.
- **Outcome**: Schema drift now fails LOUD on real candidates;
  test fixtures remain LOOSELY-typed.

### B-NEW-U — Canonical structural source signature ✅ LANDED

- **Implementation**: `source_signature.py` — `derive_signature`
  dispatcher. Real `WetZonePlannedCandidate` → walk v1.0 ancestry
  chain extracting structural-only fields (topology_kind, zone_bands,
  corridor segments, room sizes, wet-zone plan). Synthetic →
  repr+index fallback (Sub-4 path). Hash format unchanged
  (16-hex SHA256 prefix).
- **Tests**: 11 new tests in
  `test_c11a_subsession5_signature.py`. Verifies determinism,
  field-distinction, dict-order-independence, replay determinism.
- **Origin**: S39 critique walk F3.
- **Outcome**: Cache correctness now stable across structurally-equal
  inputs even when reprs vary.

### B-NEW-W partial — Cache versioning hooks ✅ LANDED

- **Implementation**: `cache.py` — added `C11A_CACHE_KEY_VERSION`
  constant (`"v1.0.0"`) folded into config hash. Added optional
  `UpstreamVersionInfo` parameter; when provided, KB-version strings
  fold into hash. Backwards-compatible: callers omitting
  `upstream_versions` get hash that includes only C11a version + config.
- **Tests**: 11 new tests in
  `test_c11a_subsession5_cache_versioning.py`.
- **Origin**: S39 critique walk F7.
- **Outcome**: v1 floor ready; full B-NEW-W (process-lifetime cache
  + cross-batch invalidation epochs) still gated on B-NEW-E2.

### B-NEW-Y partial — Long-horizon stress fuzz ✅ LANDED

- **Implementation**: `test_c11a_subsession5_stress_fuzz.py` —
  hypothesis-based dispatch fuzz (50 examples × random source ×
  random plot facing → orchestrator never crashes); 50-source batch
  no-state-leak; 10-run replay determinism for both Tier A and
  Tier B (with stub regenerator); perf regression sentinels (250ms
  single, 2.5s for 50-source batch); cache-replay-within-batch
  coverage.
- **Tests**: 8 new test cases in stress_fuzz file (the
  hypothesis-driven test counts as 1 test running 50 examples).
- **Origin**: S39 critique walk F10.
- **Outcome**: Architecture validated under randomized inputs.
  Long-horizon mutation chain tests deferred until B-NEW-T2/T3
  land (real Tier B needed for chain-stress to be meaningful).

### B-NEW-T1 — M6 wet-rotate vertical slice ✅ LANDED

- **Implementation**: `m6_wet_rotate_real.py` — post-process rotation
  approach. `rotate_wet_wall_assignment(plan, grid)` rotates each
  room's wet wall 90° clockwise (NORTH→EAST→SOUTH→WEST), respecting
  `acceptable_wall_sets`. Rebuilds `riser_groups` and recomputes
  `trap_arm_distances` + `total_wet_run_length_m` +
  `symbolic_bend_estimate` to preserve Inv 14.
  `RealUpstreamRegenerator.regenerate(M6_WET_ROTATE)` dispatches into
  this when source is a real `WetZonePlannedCandidate`. Real
  `compute_delta()` for M6 returns `PLUMB_WET_WALL_ASSIGNMENT` +
  `PLUMB_RISER_GROUPS` + `PLUMB_TRAP_ARM_DISTANCES`.
  `M6NotViableError` (per_candidate severity) when rotation is
  infeasible.
- **Scope honesty**: this is a **post-process rotation**, not a full
  C10 re-run with a rotation hint. The vertical slice validates the
  pipeline architecture end-to-end against real C10 data structures
  but does not let C10 search for a better assignment under the hint.
  See B-NEW-T1.5 below.
- **Tests**: 17 new tests in
  `test_c11a_subsession5_m6_vertical_slice.py`. Covers rotation
  map, wall picking, plan rebuild (Inv 14 preservation), riser-group
  reconstruction, M6NotViable failure path, DeltaKey diff,
  RealUpstreamRegenerator dispatch.
- **Origin**: S39 critique walk F5.
- **Outcome**: First Tier B operator wired against real upstream.
  DeepMutationPipeline architecture validated end-to-end with
  real `WetZonePlan` data.

---

## § 2 — Items still pending

### B-NEW-T1.5 — Promote M6 rotation to a real C10 re-run

- **Description**: Add `WetWallRotationHint` parameter to
  `WetZonePlanConfig`. C10 receives the hint and weights the rotated
  axis in its scoring during search. Lets M6 propose better wet-wall
  assignments than the post-process rotation can.
- **Why deferred**: requires C10 amendment review (cross-component
  change). The S39 vertical slice (B-NEW-T1 LANDED) proves the
  architecture works against real C10 data without changing C10's API.
- **Trigger**: post-S39, in a session focused on C10 amendment.
- **Effort**: M (~2 days; new C10 config knob + scoring weight).

### B-NEW-T2 — Tier B M7a/M7b grid scale upstream wiring

- **Description**: Wire M7a/b against real C7+C8+C9+C10 cascade.
  Construct new `Grid` via `c07.grid_generator.GridGenerator().generate`
  with target bay sizes; cascade through corridor design + room sizing
  + wet-zone plan.
- **Why deferred**: largest Tier B wiring effort (full pipeline
  cascade); needs its own session per CODING_MANDATE vertical-slice
  policy.
- **Trigger**: Sub-5+ priority 1 (after B-NEW-T1 confirms architecture).
- **Effort**: L (~3-4 days).

### B-NEW-T3 — Tier B M8 master-floor swap upstream wiring

- **Description**: Rebuild `floor_room_brief` with master bedroom
  relocated to alternate floor; re-run `c09.room_sizer.size_rooms` +
  `c10.wet_zone_planner.plan_wet_zones` per floor. M8 only fires
  when `floor_room_brief.is_multi_floor`.
- **Why deferred**: narrowest applicability (multi-floor only); least
  urgent for v1 commercial path.
- **Trigger**: Sub-5+ priority 2 (after B-NEW-T2).
- **Effort**: M (~2 days).

### B-NEW-Y full — Long-horizon C11a stress fuzz

- **Description**: Mutation chain accumulation tests (apply M1 → M3a
  → M5 → M9b on real candidates), topology corruption stress (
  malformed sources), perf regression benchmarks
  (`cost_per_valid_candidate`), mutation replay debugging
  (record/replay sessions).
- **Why partial at S39**: meaningful chain-stress requires real
  Tier B operators. The Sub-5 partial covers single-shot dispatch
  fuzz and many-source batch stress — both Tier A only.
- **Trigger**: After B-NEW-T2 lands (real Tier B needed).
- **Effort**: M (~2-3 days remaining).

### B-NEW-W full — Cross-batch cache invalidation

- **Description**: Process-lifetime cache (B-NEW-E2) + cross-batch
  invalidation epochs + runtime KB-version drift detection. Builds
  on the B-NEW-W partial landed at S39.
- **Why deferred**: gated on B-NEW-E2 design (process-lifetime cache).
- **Trigger**: When B-NEW-E2 is filed.
- **Effort**: M (~1-2 days remaining).

---

## § 3 — Critique walk dispositions (informational)

The following findings from S39 critique walk were classified
**not actionable**:

- **F1** stub predicates → MISFRAMED (stubs encode structural
  properties, not unimplemented checks; documented in
  predicate_registry.py module docstring + § 0.3 spec)
- **F2** symbolic-only operators → MISFRAMED (deliberate Q2 design
  per S39; deep mutation is C11b's job, not C11a's)
- **F6** lineage classification too simple → SPEC-AMENDMENT for
  post-v1 (covered by existing B-NEW-F continuation; categorical
  classification is required by NSGA-II downstream consumer at v1)
- **F9** evolutionary diversity collapse → MISFRAMED (C11b territory,
  not C11a — C11a is per-batch seed generation, no multi-generation
  loop to converge)
- **F11** complexity guardrails → MISFRAMED (C11a is bounded —
  ≤max_seeds_per_input × inputs; cache cap 128 entries; complexity
  concerns belong to C11b NSGA-II)
- **F12** human-usability ≠ constraint validity → MISFRAMED (entire-
  system scope; covered by C12-C17 in pipeline architecture)

---

## § 4 — Summary

| Category | Count |
|---|---|
| Items LANDED at S39 critique-patch session | **6** (B-NEW-X, V, U, W partial, Y partial, T1) |
| Items still pending | **5** (B-NEW-T1.5, T2, T3, Y full, W full) |
| Total tests added in critique-patch session | **74** (Sub-5: 9 + 18 + 11 + 11 + 8 + 17) |
| Full project test count post-patches | **2731 passed / 2 skipped** |
| C11a test count | **306** |

---

**End of S39 Additions.**
