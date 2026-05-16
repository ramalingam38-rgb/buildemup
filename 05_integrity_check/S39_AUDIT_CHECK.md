# S39 AUDIT CHECK (Rule 10.6.b)

**Session**: S39 — C11a Sub-2 + Sub-3 + Sub-4 build + critique-walk patches.
**Spec basis**: C11a SPEC v1.0 LOCKED at S38. Spec amendments LOCKED at
S38: B-NEW-J, B-NEW-K (incl K-4 patch), B-NEW-L, B-NEW-P.
**Purpose**: line-by-line spec compliance check for what shipped at S39.

---

## Sub-2 — Tier A operators

### § 2.2 v0.5 OPERATOR_METADATA (16-entry table)
✅ All 16 operators present in `operator_metadata.py`:
M0_BASE, M1_HORIZ_FLIP, M2_VERT_FLIP, M3A/B/C_STAIR_*, M4_CORRIDOR_INV,
M5_ZONE_SWAP, M6_WET_ROTATE, M7A/B_GRID_*, M8_VERT_REARR, M9A/B/C/D_ENTRY_*

### § 0.3 PREDICATE_REGISTRY (9 entries)
✅ All 9 predicates registered, ordered C5→C7→C8→C9→C10:
- C5.privacy_zoning (callable)
- C7.staircase_clearance (callable)
- C8.corridor_grid_alignment (callable)
- C9.Inv_4 / Inv_5 / Inv_13 (stubs; pending_upstream=False per Q1)
- C10.Inv_4 / Inv_5 / Inv_5b (stubs; pending_upstream=False per Q1)

**Q1 design decision recorded**: stubs encode structural properties
(operator metadata's expected/forbidden delta sets enforce the
invariants by-construction); not "unimplemented checks." Documented
in module docstring + critique walk F1 disposition.

### § 12 Inv 26 + Inv 28 registry validation
✅ `registry.validate_operator_registry()` enforces:
- Inv 26: every metadata-declared family ↔ operator pair is consistent
- Inv 28: family transitions are valid per FamilyTransitionPolicy enum

### § 3 Phase 1 family slot allocator
✅ `family_slot_allocator.allocate_family_slots()`:
- Reserves slots per family per `FamilySlotAllocation`
- Spillover allocation when max_seeds budget has surplus
- Lex-ASC iteration (deterministic per Inv 30)

### Operator implementation pattern
✅ All 12 Tier A operators (M0-M5, M9 family) follow
`apply_<op>(source, ctx, *, source_signature, source_family_id) →
MutationApplicationResult` per Q2 design (operators return result-only;
deep mutation is C11b's job).

---

## Sub-3 — Tier B pipeline

### § 0.3 cache scope (Inv 30 single-batch)
✅ `cache.py` `DeepMutationCacheKey` + `derive_cache_config_hash`
respects single-batch scope. Cap 128 entries (16 ops × 8 input candidates worst case).

### § 3.5 DeepMutationPipeline contract
✅ `deep_pipeline.py`:
- `UpstreamRegenerator` Protocol (runtime_checkable per § 3.5)
- `StubUpstreamRegenerator` for unit tests
- `TierBInputMutation` per § 2.5 v0.5
- Pipeline catches per-candidate severity exceptions, surfaces as invalid result
- Severity routing via `getattr(type(exc), "severity_tier", None)`
  with 'systemic' default per F-v4-5

### § 2.5 lineage classification
✅ `lineage.classify_lineage_depth()`:
- REGEN: source_family_id preserved + delta_keys ⊆ expected
- EMERGENT: TRANSFORMS_FAMILY policy + new family_id matches transformed prefix
- REJECT: forbidden delta_keys appear

### § 2.5 v0.5 DeltaKey vocabulary
✅ All 20 categories present: GEO_*, ADJ_*, CIRC_*, ZONE_*, PLUMB_*,
MULTIFLOOR_*, META_*

### Tier B operator wrappers
✅ M6/M7a/M7b/M8 each call pipeline.execute() via shared
`_tier_b_base.apply_tier_b_operator` wrapper.

---

## Sub-4 — Phase 0 + orchestrator

### § 3 Phase 0 startup validation
✅ `phase0.run_phase_0_startup_validation()` runs all four:
1. `validate_operator_registry` (Sub-2; Inv 22, 26, 28)
2. `validate_upstream_purity_contract` (Inv 25)
3. `enforce_pending_predicate_sunset` (Inv 24 LOCK gate)
4. `validate_severity_classification_audit` (Inv 27 / F-v4-5)

### Inv 24 LOCK gate clauses
✅ Both clauses enforced in `enforce_pending_predicate_sunset`:
- Clause 1: `pending - waivers == 0`
- Clause 2: `len(waivers) ≤ 3`

### F-v4-5 severity classification audit (Sub-5 patched)
✅ At Sub-4 used `__subclasses__()` walk (spec gap surfaced in critique
walk F8). At Sub-5 replaced with `iter_registered_errors()` walking
WeakSet registry (B-NEW-X). Sorted-by-qualname for replay determinism.

### § 3 Phase 1/2/3 orchestrator
✅ `orchestrator.mutate_topologies()`:
- Phase 0: startup validators
- Phase 1: per-candidate seed generation (M0_BASE → family lex-ASC → operator lex-ASC)
- Phase 2: diagnostics (per_operator_yield, per_family_yield, family_spread_entropy, duplicate_ratio, runtime_ms)
- Phase 3: provenance assembly per ProvenanceVerbosity

### F-v2-8 single-floor M8 skip
✅ M8 attempts on single-floor briefs marked `valid=False,
invalidity_reason="single_floor_brief"` deterministically.

### § 2.9 quarantine fingerprint
✅ Empty `quarantined_operators=()` at v1.0 STRICT mode; deterministic
SHA256 hash.

### § 5 error hierarchy
✅ 12 typed exceptions with severity_tier ClassVars; all route through
WeakSet registry post-Sub-5.

### Inv 30 replay determinism
✅ Verified by `test_replay_determinism_*` tests (2-run + 10-run).

---

## Sub-5 — Critique-walk patches

### B-NEW-X — WeakSet error registry
✅ `errors.py` adds `__init_subclass__` populating
`weakref.WeakSet`; `iter_registered_errors()` returns sorted snapshot;
`phase0.py` walks registry instead of `__subclasses__()`.
**Spec gap closed**: F-v4-5 specified "audit" without specifying
mechanism. WeakSet design is deterministic + GC-collectable.

### B-NEW-V — Strict candidate-context extractor
✅ `candidate_context.py` ships:
- `CandidateContextSchemaError` (per_candidate severity, registered)
- Strict path walking v1.0 ancestry chain:
  `WetZonePlannedCandidate.room_sized_candidate.corridor_designed_candidate.oriented_candidate.topology_candidate.zone_bands` etc.
- Lenient duck-type fallback for synthetic test fixtures
- Dispatcher `extract_tier_a_context()` routes by `is_real_wet_zone_candidate()`

### B-NEW-U — Canonical structural source signature
✅ `source_signature.py` ships:
- `derive_canonical_signature()` walks structural fields: kind / zone_bands / corridor / room_size_table / wet_zone_plan / orientation
- `derive_signature()` dispatcher: real → canonical, synthetic → repr+index
- 16-hex SHA256 prefix format consistent with `derive_variant_id`

### B-NEW-W partial — Cache versioning hooks
✅ `cache.py`:
- `C11A_CACHE_KEY_VERSION = "v1.0.0"` constant folded into config hash
- `UpstreamVersionInfo` frozen dataclass with optional fold
- Backwards-compatible (Sub-3 callers omit `upstream_versions`)

### B-NEW-Y partial — Tier A stress fuzz
✅ `test_c11a_subsession5_stress_fuzz.py`:
- Hypothesis-based dispatch fuzz (50 examples)
- 50-source batch no-state-leak
- 10-run replay determinism (Tier A + Tier B with stub regen)
- Perf regression sentinels (250ms single, 2.5s 50-source)
- Cache replay-within-batch coverage

### B-NEW-T1 — M6 vertical slice
✅ `m6_wet_rotate_real.py`:
- Post-process rotation NORTH→EAST→SOUTH→WEST per project coords
- Respects `acceptable_wall_sets` per room
- Rebuilds `riser_groups` (group_id prefix `rg_rotated_`)
- Recomputes `trap_arm_distances` + `total_wet_run_length_m` + `symbolic_bend_estimate`
- Preserves Inv 14 (verified by test)
- `M6NotViableError` (per_candidate severity) on infeasible rotation
- `RealUpstreamRegenerator.regenerate(M6)` dispatches; `compute_delta(M6)` returns real DeltaKey diff (PLUMB_WET_WALL_ASSIGNMENT, PLUMB_RISER_GROUPS, PLUMB_TRAP_ARM_DISTANCES)

**Honest scope flag**: post-process rotation, NOT full C10 re-run with
rotation hint. Promotion to real C10 re-run is filed as B-NEW-T1.5
(needs C10 amendment review).

---

## Decisions surfaced (per Rule 10.6.b)

1. **Q1 (Sub-2)**: 6 stubs + 3 callables in predicate registry. Stubs
   encode structural properties; pending_upstream=False so Inv 24 LOCK
   gate stays at 0.

2. **Q2 (Sub-2)**: operators return MutationApplicationResult only; no
   deep mutation. Defers deep mutation to C11b.

3. **B-NEW-T deferral (Sub-4)**: shipped scaffold + per-operator
   NotImplementedError with implementation hints. Orchestrator catches
   NotImplementedError and surfaces as per-candidate invalid.

4. **B-NEW-T retired into T1/T2/T3 (Sub-5 critique walk)**: vertical
   slicing per F5 critique. T1 landed; T2/T3 still pending.

5. **B-NEW-T1 scope decision (Sub-5 Tier 3)**: post-process rotation
   instead of full C10 re-run. Honest scoped vertical slice; B-NEW-T1.5
   filed for the promotion.

6. **B-NEW-W partial vs full**: full B-NEW-W (cross-batch invalidation)
   gated on B-NEW-E2; partial shipped to set up the design cleanly.

7. **B-NEW-Y partial vs full**: full B-NEW-Y (mutation chain accumulation)
   gated on B-NEW-T2; partial shipped for single-shot dispatch fuzz +
   batch stress.

8. **Round-2 critique disposition (Sub-5)**: reviewed described a
   workflow/session/email system that doesn't exist in C11a. Discarded
   by Ramalingam after Claude pushed back per Rule 7 with grep evidence.

---

## AUDIT CHECK OUTCOME: ✅ SPEC-COMPLIANT WITH HONEST SCOPE FLAGS

All shipped code aligns with C11a SPEC v1.0 LOCKED + S38 amendments.
Two scope flags carry forward: B-NEW-T1 is honest-scoped slice (not
full re-run); B-NEW-W and B-NEW-Y are explicit partials with named
gating items.

**End of AUDIT CHECK.**
