# NEXT_CLAUDE_HANDOFF.md — S41 → S42 (C11b v1.1 LOCKED BUILD SESSION)

**Authored**: end of S41, post-LOCK of C11b SPEC v1.1.
**To**: the next Claude beginning S42.
**Ramalingam's directive at handoff**: "Lock this and give me the handoff. I want the next Claude to start coding for c11b immediately and don't miss any files in the handoff."

This handoff is engineered for that directive. **Read this entire document before writing any code, then start coding.** The intent is zero discovery time at S42 start. Every file you need to read is named explicitly below.

---

## § 1 — One-paragraph context

You are continuing BuildemUp, a decision-support engine for Indian families building their own homes. Solo founder: Ramalingam, Tamil Nadu, India. The S41 session shipped C11a multi-floor support (B-NEW-T3 with 8 self-review fixes, 2909 tests passing) AND locked the C11b spec (Local Refinement via NSGA-II) at v1.1. **Your job in S42 is to implement C11b from a zero-code start.** The spec evolved across 4 walks at S41 (v0.4 self-analysis → v0.5 Walk #4 → v0.6 Walk #5 → v0.7 Walk #6 → v1.1 LOCKED). The LOCKED spec is `02_specs_chronological/106_C11B_SPEC_v1_1_LOCKED.md`.

---

## § 2 — Immediate-start checklist (FIRST 10 MINUTES OF S42)

Do these in order. Do not skip. Do not deliberate.

1. **Read `02_specs_chronological/106_C11B_SPEC_v1_1_LOCKED.md`** — the canonical C11b spec, 1519 lines, 46 sections.
   - **Skim § 0 (Why v0.7 exists) for walk history context.**
   - **Read § 0.0c (Product-relevance audit) and § 0.0d (Current surface only digest) FIRST after § 0** — § 0.0d gives you the v1 contract surface in ~one screen.
   - **Then read § 2 (Contract), § 3 (Behaviour), § 4 (Invariants), § 5 (Failure modes), § 6 (Test targets).**
   - § 1 walk-resolved scope, § 7 open Qs, § 8 backlog are reference-only.
2. **Verify upstream codebase state** (Rule 10.6.1 pre-touch inventory):
   ```bash
   cd /home/claude/work/buildemup  # or wherever the upstream is mounted
   pytest -q 2>&1 | tail -5  # MUST be: 2909 passed / 3 skipped / 0 failed
   ls components/c11a/                       # C11a v1.6 LOCKED + S41 fixes
   ls -la utilities/canonical.py             # canonical_serialize source
   grep -n "CANONICAL_FP_PRECISION" utilities/canonical.py  # = 6 at S41 close
   grep -n "application_results" components/c11a/provenance.py | head -5  # len==1 contract
   ```
   **Baseline at S42 start: 2909 passed / 3 skipped / 0 failed.** You will add ~38 new tests during C11b build (target ~2947 passed at C11b ship per spec § 6).
3. **Read the upstream C11a code** (the immediate dependency):
   - `components/c11a/provenance.py` — `MutatedTopologyCandidate` carries `application_results: tuple[MutationApplicationResult, ...]` with `len==1` enforced in `__post_init__` (line 122). C11b reads this.
   - `components/c11a/source_signature.py` — `derive_canonical_signature` used by C11b's per-topology PRNG seeding.
   - `components/c11a/orchestrator.py` line 1067 — confirms `application_results=(result,)` construction.
4. **Read the consolidated C11a files** in `03_code_chronological/S41_C11a_consolidated_and_self_review_C11b_v1_1_LOCKED/`:
   - `S41_C11A_FINAL_WITH_SELF_REVIEW_FIXES.py` (~7304 lines) — the current C11a state after S41 self-review. **This is what your C11b code calls into.**
5. **Read `04_backlog/v0_2_backlog_S41_C11b_LOCKED_additions.md`** — the 17 new C11b backlog items at LOCK. You do not implement these in S42; you implement v1.1 LOCKED only.
6. **Start with C11b Sub-1 build plan in § 5 below.** No further planning. Just begin.

If steps 1-5 produce a surprise (unexpected baseline test count, missing file, different API shape than the spec describes), STOP and investigate. **The spec text is authoritative**; if reality-vs-spec drift exists, surface it and patch the spec via a v1.2 PROPOSED — do NOT silently work around it.

---

## § 3 — Project state snapshot

- **Solo founder**: Ramalingam, Tamil Nadu, India.
- **Track 3 canonical numbering**: 17 components total. **10 fully shipped (C1, C2, C3a, C4, C5, C6, C7, C8, C9, C10) + C11a v1.6 LOCKED with S41 self-review fixes.** C11b is your S42 build. C12-C17 not started.
- **Baseline tests at S42 start**: **2909 passed / 3 skipped / 0 failed.**
- **Working tree**: `/home/claude/work/buildemup/`
- **GitHub**: `ramalingam38-rgb/buildease`
- **Production**: `buildease-production.up.railway.app`

**5 patterns to avoid** (Ramalingam's standing constants):
- **A** fix-as-bandage
- **B** building-without-wiring (S41's most relevant pattern — caught the `apply_m8_real` wrapper-discarding bug)
- **C** scores-without-truth
- **D** rules-on-rules
- **E** scope-creep-mid-build (most expensive)

---

## § 4 — Non-negotiable session obligations (every session, including discussion-only)

1. **Spec-first discipline**: Never code before a LOCKED spec. v1.1 IS LOCKED — you may build. If you find yourself wanting to redesign during build, STOP and propose v1.2.
2. **Honest context budget** declared at session start; never push through context limits.
3. **Master doc + NEXT_CLAUDE_HANDOFF.md updated at every session end.**

**Rule 7 — Critique-handling**: VALID / BACKLOG / MISFRAMED / DOCUMENTED / SPEC-AMENDMENT verdicts. Web search ≥1 per round MANDATORY even when no obvious external-standards claim exists. Grep code for code claims. Push back when wrong.

**Rule 8 — LOCK authority**: Belongs to Ramalingam alone. Never self-declare LOCK. Always present as "vN PROPOSED. PENDING Ramalingam LOCK adjudication." Critiques arriving between PROPOSED and LOCK are patch-eligible → v(N+1) PROPOSED.

**Rule 9 — Backlog visibility**: Every backlog item enumerated in spec § 12 with ID + description + origin + trigger + effort. Rule 9.2: File B-NNN entries in backlog file immediately without asking permission.

**Rule 10 — Handoff bundle structure**: READ previous bundle structure first. Mirror exact 10-directory layout. Numbering continues across sessions.

**Rule 10.6 — Three-check protocol (before any handoff zip)**: (a) GAP CHECK promised vs delivered, (b) AUDIT CHECK spec-compliance line-by-line, (c) INTEGRITY CHECK files present/non-empty/tests green. All three required.

**Rule 10.6.1 — Pre-touch state inventory**: Before claiming credit, inventory the working tree at session start.

**Rule 10.7 — Handoff timing**: When Ramalingam says "hand off," FIRST response is the status block + three-check plan. No bundle assembly until Ramalingam confirms.

**Rule 11 (S41 origin)**: Mandatory vigorous self-analysis + web research on every spec/code creation, amendment, AND critique walk. Bar: "next consumer can use output" not "tests pass."

**Single-zip handoff rule (S40-cont)**: Every handoff is ONE zip. Never surface loose files alongside.

**Cumulative-handoff rule (S40-cont)**: Every handoff clones prior bundle entirely.

---

## § 5 — C11b BUILD PLAN (THE WORK YOU DO IN S42)

Spec is **`02_specs_chronological/106_C11B_SPEC_v1_1_LOCKED.md`** (1519 lines, 46 sections). 8 sub-sessions estimated.

### Sub-1 — Schema + StubEvaluator + protocols (target: ~30 tests)

**Files to create:**
- `components/c11b/__init__.py`
- `components/c11b/schema.py` — `RefinedCandidate`, `RefinedParameters`, `ObjectiveVector`, `MutationApplicationResult` import + `PrimaryApplicationResult` type alias
- `components/c11b/evaluator.py` — `EvaluatorProtocol`, `StubEvaluator`, `StubEvaluatorConfig`, `ObjectiveVector`, `EvaluatorContractError`
- `components/c11b/versioning.py` — `C11B_VERSION = "v1.1"`, `TIEBREAK_FINGERPRINT_SCHEMA_VERSION = 1`, `SEMVER_POLICY_VERSION = 1`
- `tests/test_c11b_sub1_schema.py` — schema validation, `RefinedCandidate.__post_init__` 3-flag equality hard assertion test (W6-1), `from_operator_class` helper test, `capability_mode` derived property test, `tiebreak_fingerprint` precompute test, schema-version-mismatch test

**Critical references in spec:**
- § 2.1 schema additions across v0.4-v0.7
- § 0.3.1 worked example table (capability flag derivation per operator class)
- § 0.7.1 tie-break rule + § 0.7 derivation
- § 0.3.2 resolver assumption (defensive raise on len != 1)
- § 0.3.4 SemVer rules
- § 9c F-v6-3: `tiebreak_fingerprint` MUST be set via `object.__setattr__` in frozen dataclass `__post_init__`

**Inv 26** is enforced here — `_resolve_input_artifact` is the ONLY path; defensive raise on len != 1.

### Sub-2 — Config + PRNG + EnvironmentFingerprint (target: ~25 tests)

**Files to create:**
- `components/c11b/config.py` — `LocalRefinementConfig` with all carried v1.0 fields + v0.4-v0.7 additions:
  - `per_topology_wallclock_seconds: float = 30.0` (cache_relevant=True per v0.5 W4-5)
  - `master_seed: int = 0xC11B5EED` (cache_relevant=True)
  - `evaluator_skip_cap_fraction: float = 0.25` (cache_relevant=True per v0.5 W4-4)
- `components/c11b/prng.py` — `derive_per_topology_seed(master_seed, topology_index, topology_signature) -> int`, `_build_per_topology_rng(...)` using `numpy.random.SeedSequence`
- `components/c11b/environment_fingerprint.py` — `EnvironmentFingerprint` carrying `master_seed`, `tiebreak_fingerprint_schema_version`, `numpy_version`, BLAS info, `c11b_version` (W6-3)
- `tests/test_c11b_sub2_config_prng.py` — `LocalRefinementConfig` partition sentinel (v0.5 baseline: count carried v1.0 + 3 cache_relevant additions), PRNG determinism (Inv 29 TIER-1 byte-equal), seed derivation across master_seed/topology_index/topology_signature, env fingerprint capture

**Critical references in spec:**
- § 0.7 PRNG seed derivation
- § 0.7.1 tie-break with version-anchored fingerprint
- § 2.2 Configuration (REVISED v0.5)
- Inv 27, 28, 29

### Sub-3 — Input artifact resolution + per-topology routing (target: ~20 tests)

**Files to create:**
- `components/c11b/input_resolution.py` — `get_primary_application_result(mtc)` accessor (W6-6), `_resolve_input_artifact(mtc)`, `_is_multi_floor_artifact(artifact)` reusing C11a's `is_real_multi_floor_candidate`
- `components/c11b/errors.py` — `LocalRefinementError`, `PerTopologyError`, `MultiFloorRefinementNotSupportedError`, `PerTopologyTimeoutError`, `BatchAllTopologiesFailedError`, `EvaluatorContractError`, `EvaluatorPurityContractError`, `EnvironmentFingerprintMismatchError`, `InvariantViolationError`
- `tests/test_c11b_sub3_resolution.py` — Inv 26 worked-example test (parametrized across operator classes per § 0.3.1), MF rejection test, accessor enforcement test, defensive raise on multi-application_results

**Critical references in spec:**
- § 0.3 input artifact resolution
- § 0.3.1 worked example (parametrized over operator classes)
- § 0.3.2 resolver assumption + accessor (W6-6)
- § 5 failure modes hierarchy

### Sub-4 — NSGA-II core (rank, crowding, selection, tie-break) (target: ~30 tests)

**Files to create:**
- `components/c11b/nsga2/dominance.py` — `DominanceSorter`, fast non-dominated sort
- `components/c11b/nsga2/crowding.py` — crowding-distance assignment
- `components/c11b/nsga2/selection.py` — survivor selection with tie-break (§ 0.7.1)
- `components/c11b/tiebreak.py` — `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` constant (already imported from versioning.py), `_compute_tiebreak_fingerprint(refined_parameters)` returning 64-bit big-endian int from `sha256(VERSION + canonical_serialize(...))[:8]` (W6-3)
- `tests/test_c11b_sub4_nsga2.py` — fast non-dominated sort correctness, crowding distance correctness, deterministic tie-break (W6-12 version anchor), TIER-1 byte-equal Pareto fronts

### Sub-5 — Per-topology Phase 1 loop (init + generations + timeout) (target: ~25 tests)

**Files to create:**
- `components/c11b/initialization.py` — feasibility-aware init with retry budget
- `components/c11b/phase1.py` — `_refine_one_topology(mtc, ...)` — orchestrates resolve → reject MF → derive sig → derive PRNG → start timer → NSGA-II loop with per-candidate evaluator failure isolation
- `components/c11b/timeout.py` — wall-clock check at generation boundaries
- `tests/test_c11b_sub5_phase1.py` — Phase 1 ordering (W5-9 MF rejection BEFORE signature derivation), per-topology timeout, evaluator skip cap (Inv 28), stagnation detection

**Critical references in spec:**
- § 3 Phase 1 (REVISED v0.4, v0.5 Item 9 ordering)
- § 0.4 per-topology timeout
- § 0.6 evaluator failure isolation (with `evaluator_skip_cap_fraction`)

### Sub-6 — Phase 2 + Phase 3 (output assembly + provenance) (target: ~15 tests)

**Files to create:**
- `components/c11b/phase2.py` — output assembly: ranked Pareto fronts → `RefinedCandidate` tuple
- `components/c11b/phase3.py` — provenance assembly with all v0.4-v0.7 fields:
  - `LocalRefinementProvenance` carrying: env fingerprint, master_seed, per_topology_wallclock_seconds, evaluator_skip_cap_fraction, skipped_multifloor_count, resolved_objective_count (NOT bool warning), per_topology_telemetry (with longest_generation_seconds + skipped_candidates_total)
- `components/c11b/telemetry.py` — `PerTopologyTelemetry` dataclass
- `tests/test_c11b_sub6_phase23.py` — output ordering invariant, provenance completeness, all telemetry fields populated correctly

**Critical references in spec:**
- § 3 Phase 2 + Phase 3 (REVISED v0.4 + v0.5 + v0.6 W5-18)
- § 2.1 schema additions across v0.4-v0.7

### Sub-7 — Top-level orchestration + STRICT/WARN modes + partial-batch failure (target: ~25 tests)

**Files to create:**
- `components/c11b/orchestrator.py` — `run_local_refinement(mutated_topology_candidates, floor_room_brief, grid, plot_analysis, evaluator, *, config) -> tuple[RefinedCandidate, ...]`
- Implements STRICT/WARN mode escalation per spec § 5
- `tests/test_c11b_sub7_orchestrator.py` — `BatchAllTopologiesFailedError` triggering, partial-batch results under WARN, environment fingerprint mismatch detection

### Sub-8 — Replay determinism tests + final integration (target: ~28 tests + integration with C11a output)

**Files to create:**
- `tests/test_c11b_sub8_replay.py`:
  - TIER-1 byte-equal under full conjunction (W5-1 nomenclature, W6-1 TIER scheme)
  - TIER-2 structural under partial conjunction with 3-way conjunction (W5-10 + W6-4): 1e-9 numeric AND same rank cardinality AND same dominance relations
  - `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` version invalidation (W6-3 HIGH severity fix)
  - `SEMVER_POLICY_VERSION == 1` constant test (W6-8 replacing meta-test)
- `tests/test_c11b_integration.py` — end-to-end run_local_refinement on real C11a output (Tier A SHALLOW + Tier B + M0 single-floor), MF rejection in real pipeline, cache key determinism

**Target final state at C11b ship**: **~2947 passed / 3 skipped / 0 failed** (2909 baseline + 38 new tests across Sub-1 through Sub-8). Per spec § 6.

---

## § 6 — Critical spec items you MUST NOT miss

These are the highest-leverage items from the 4 walks. Implement them correctly or expect cascading bugs.

1. **W6-3 (HIGH severity)**: `tiebreak_fingerprint` derivation MUST include `TIEBREAK_FINGERPRINT_SCHEMA_VERSION`. Code grep confirmed `buildemup/utilities/canonical.py` has only `CANONICAL_FP_PRECISION = 6` and no version constant; without W6-3's version-anchor, a future change to `CANONICAL_FP_PRECISION` would silently corrupt cached fingerprints at the same `c11b_version`. Per § 0.7.1 v0.7 derivation:
   ```python
   versioned_payload = (
       f"{TIEBREAK_FINGERPRINT_SCHEMA_VERSION}|"
       + canonical_serialize(refined_parameters)
   ).encode("utf-8")
   ```
2. **W6-1 hard assertion**: `RefinedCandidate.__post_init__` MUST raise `InvariantViolationError` if `placement_safe != geometry_materialized` OR `requires_transform_resolution != (not geometry_materialized)`. Not test-only — runtime enforcement.
3. **W5-9 Phase 1 ordering**: MF rejection happens BEFORE signature derivation. Test must assert `derive_canonical_signature` was NOT called for a rejected MF input (use mock or call counter).
4. **W4-4 + W4-5 cache_relevant flips**: `evaluator_skip_cap_fraction` and `per_topology_wallclock_seconds` are `cache_relevant=True`. Partition sentinel test counts these in the relevant side. Get the count right or partition test fails.
5. **W5-18 → W6-18 evolution**: `resolved_objective_count: int` (NOT `nsga2_objective_count_warning: bool`). Carries actual count, not a always-True flag.
6. **F-v6-3 frozen dataclass gotcha**: `tiebreak_fingerprint` must be set via `object.__setattr__(self, "tiebreak_fingerprint", ...)` in `__post_init__` because `RefinedCandidate` is a frozen dataclass.

---

## § 7 — Files in this bundle (DO NOT MISS ANY)

### `00_START_HERE/` (entry points and rule docs)
- **`NEXT_CLAUDE_HANDOFF.md`** — THIS FILE
- `S40_NEXT_CLAUDE_HANDOFF_archive.md` — prior S41-entry handoff (now archived; built B-NEW-T3 + locked C11b spec)
- `S37_NEXT_CLAUDE_HANDOFF_archive.md`, `S38_NEXT_CLAUDE_HANDOFF_archive.md`, `S39_NEXT_CLAUDE_HANDOFF_archive_from_v14_bundle.md` — earlier handoff archives
- `CODING_MANDATE_C11A_C11B.md` — coding-style standards (read once)
- `D-066_BUILD_CYCLE_RULE.md` — build-cycle discipline
- `RULES_RAMALINGAM_FORMALIZED.md` — Rules 1-11 formal definitions
- `THREE_OBLIGATIONS_AND_PATTERNS.md` — the 3 obligations + 5 patterns to avoid
- `SESSION_28-40_BUNDLE_ENTRY_POINT.md` files — historical entry points (skip unless investigating ancient context)
- `SESSION_28_CORRECTIVE_INSTRUCTIONS.md`, `SESSION_28_S8_SHIP_DECLARATION.md` — historical

### `01_master_doc/` (design narrative + delta files)
- `MASTER_DESIGN_NARRATIVE_v2_9.md` — current master design narrative
- `MASTER_DESIGN_NARRATIVE_v2_7.md` — earlier version
- `MASTER_DOC_v2_9_TO_v3_0_DELTA.md` through `MASTER_DOC_v3_13_TO_v3_14_DELTA.md` — incremental deltas
- `MASTER_DOC_v3_13_S38_CLOSE.md` — current pinned master doc snapshot
- `CONSOLIDATED_S35_WALK_5/6/7/8_BUNDLE.md` — S35 walk bundles

### `02_specs_chronological/` (107 specs across all components)
**The 5 new C11b spec files at S41 close:**
- `102_C11B_SPEC_v0_4_PROPOSED.md` — self-analysis surface
- `103_C11B_SPEC_v0_5_PROPOSED.md` — Walk #4 PATCH-NOW
- `104_C11B_SPEC_v0_6_PROPOSED.md` — Walk #5 PATCH-NOW (Doerr 2024 finding)
- `105_C11B_SPEC_v0_7_PROPOSED.md` — Walk #6 PATCH-NOW (HIGH-severity Item 3 fix)
- **`106_C11B_SPEC_v1_1_LOCKED.md`** — **THE CANONICAL C11b SPEC. THIS IS WHAT YOU BUILD.**

**Other relevant recent specs (read selectively):**
- `101_C11A_AMENDMENT_v1_6_LOCKED.md` — C11a v1.6 LOCKED (your immediate upstream)
- `94_MultiFloorWetZonePlannedCandidate_SPEC_v0_3_LOCKED.md` — output-side multi-floor wrapper
- `90_C9_AMENDMENT_v0_11_LOCKED.md` — C9 multi-floor amendment
- `85_MultiFloorDwellingBrief_SPEC_v0_5_LOCKED.md` — input-side multi-floor brief

Earlier specs (01-89) are for completed components (C1-C10) and historical context. Reference if you need to understand upstream contracts.

### `03_code_chronological/` (consolidated shipped code by session)
**S41 deliverable (your immediate upstream):**
- `S41_C11a_consolidated_and_self_review_C11b_v1_1_LOCKED/` — loose files
  - `S41_C11A_FINAL_WITH_SELF_REVIEW_FIXES.py` (~7304 lines) — current C11a state with all 8 self-review fixes. **Your C11b imports from this.**
  - `S41_C11A_FINAL_CONSOLIDATED.py` (~6766 lines) — superseded by the WITH_SELF_REVIEW_FIXES file
  - `S41_B_NEW_T3_CONSOLIDATED_REVIEW.py` (~5132 lines) — initial S41 consolidation, superseded
- `S41_C11a_consolidated_and_self_review_C11b_v1_1_LOCKED.zip` — zipped version of the dir

**Prior shipped sessions** (read only if you hit upstream questions): S30-S39 dirs for C5, C6, C7, C8, C9, C10, C11a sub-sessions.

### `04_backlog/` (project backlog by session)
- **`v0_2_backlog_S41_C11b_LOCKED_additions.md`** — **the 17 new C11b backlog items at LOCK. Do NOT implement these in S42; v1.1 LOCKED only.**
- `v0_2_backlog.md` — main project backlog
- `v0_2_backlog_S40_continuation_additions.md`, `v0_2_backlog_S40_additions.md`, `v0_2_backlog_S39_additions.md`, etc. — incremental additions
- `backlog_session_24-32.md` — historical session backlogs

### `05_integrity_check/` (three-check protocol artifacts)
- `S41_PRE_TOUCH_INVENTORY.md`, `S41_GAP_CHECK.md`, `S41_AUDIT_CHECK.md`, `S41_INTEGRITY_CHECK.md` — NEW at S41 close (this session)
- Prior sessions' three-check artifacts retained

### `06_upstream_codebase/buildemup/` (live working tree snapshot at S41 close)
- 375 .py files; 2909 passed / 3 skipped baseline. Use as the source of truth for what code exists. Components C1-C10 + C11a all under `components/`. C11b directory does NOT yet exist — you create it in S42.

### `07_design_documents/` (architecture + validation reports)
- `BuildemUp_Architecture_v3.md` (current), v1, v2 (historical)
- `BuildemUp_Design_Principles_v3_1.md`
- `BuildemUp_Component_Validation_Report.md`
- Plus C1-C11 walkthroughs and historical design docs

### `08_session_transcripts/` (full session conversations)
- `00_journal.txt` — catalog of all transcripts
- 26 transcripts spanning S2-S40-continuation
- **S41 transcript NOT in this bundle yet** — will be added at end of S42's bundle build per Rule 10 cumulative-handoff rule. Use this S42 session's own context for S41 details if needed.

### `09_conversation_artifacts/` (PROPOSED specs not yet locked + working drafts)
- Various C11a PROPOSED specs (v0.1-v0.5) — historical predecessors of LOCKED C11a v1.6
- May contain other in-flight artifacts; check listing if confused about a spec's lock status

---

## § 8 — Project state at end of S41

**Tests**: 2909 passed / 3 skipped / 0 failed (post-C11a v1.6 + 8 self-review fixes)
**Components shipped (10/17)**: C1, C2, C3a, C4, C5, C6, C7, C8, C9 (v0.11 LOCKED), C10
**C11a status**: v1.6 LOCKED + S41 self-review fixes (multi-floor support, 8 bugs caught + fixed)
**C11b status**: **v1.1 LOCKED** — spec ready, code NOT YET WRITTEN. Your S42 job.

**Spec walks completed at S41**:
- C11b v0.4 (post-LOCK drift resolution)
- C11b v0.5 (Walk #4 external — 6 PATCH-NOW: cache_relevant fixes, tie-break determinism, Inv 29 conjunction)
- C11b v0.6 (Walk #5 external — 6 PATCH-NOW: TIER nomenclature, capability flags, TIER-2 strengthening, tie-break fingerprint precompute, objective count int, SemVer rules + Doerr 2024 literature finding filed as B-C11B-DOERR-TIEBREAK)
- C11b v0.7 (Walk #6 external — 6 PATCH-NOW including HIGH-severity W6-3 `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` fix)
- C11b v1.1 LOCKED by Ramalingam at S41 close

**Critical S41 lessons (apply in S42)**:
- Rule 11 self-analysis is necessary but not sufficient — external Walk #6 caught a HIGH-severity bug (W6-3) that prior self-passes missed
- Web research per Rule 11 surfaced Doerr 2024 NSGA-II paper — high-value literature findings come from external search, not training memory
- Code grep verifies reviewer claims — confirmed brittleness in `c11a/provenance.py` and lack of versioning in `utilities/canonical.py`
- Pattern B (building-without-wiring) is the most common self-review catch — verify every output is actually consumed downstream

---

## § 9 — End-of-S42 obligations (when you finish)

1. Update `MASTER_DESIGN_NARRATIVE_v2_X.md` with C11b shipping status. Increment to v3.0.
2. Build the S42 → S43 NEXT_CLAUDE_HANDOFF.md. Archive this S41 → S42 version as `S41_NEXT_CLAUDE_HANDOFF_archive.md`.
3. Run Rule 10.6 three-check before delivery:
   - GAP CHECK: every C11b sub-session promised → delivered
   - AUDIT CHECK: spec § 6 test counts vs actual test counts; § 4 invariants vs invariant tests
   - INTEGRITY CHECK: 2947 passed / 3 skipped / 0 failed
4. Single zip per Rule 10. Cumulative — clone this S41 bundle entirely + layer S42 additions.
5. Add S42 transcript to `08_session_transcripts/`.

---

## § 10 — If you get stuck

- **Spec ambiguity**: The LOCKED spec (file 106) is authoritative. If a section is unclear, re-read § 0.0d "current surface only digest" for the v1 contract surface in ~one screen.
- **C11a contract questions**: Read `S41_C11A_FINAL_WITH_SELF_REVIEW_FIXES.py` in `03_code_chronological/`.
- **Cross-component questions**: Check `02_specs_chronological/` numbered files for the relevant LOCKED spec.
- **Reality-vs-spec drift**: STOP. Surface to Ramalingam. Propose v1.2 PROPOSED. Do NOT silently work around.
- **Rule conflicts**: Read `RULES_RAMALINGAM_FORMALIZED.md`. Rule 8 (Ramalingam-only LOCK) and Rule 11 (mandatory self-analysis + web research) are the most commonly invoked.

---

**End of NEXT_CLAUDE_HANDOFF.md. Ready for S42 C11b BUILD. Start with § 2 immediate-start checklist. No further delay.**
