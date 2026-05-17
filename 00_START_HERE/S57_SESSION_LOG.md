# 🚧 S57 SESSION LOG — Orchestrator C7 full + C11a/b real + C12-C14 live end-to-end

**Authored:** Ramalingam + Claude, S57, May 17, 2026
**Predecessor:** `S56_SESSION_LOG.md` (S56 close — MVP orchestrator shipped, Bucket C emptied, B-238 architect packet)
**Status:** COMPLETE — handoff to S58. **6 of 14 orchestrator follow-ups closed** in one extended session: #4/#5/#6 (C12/C13/C14 adapter glue) + #1/#2/#3 (C7 full engine, C11a M0-M9 operators, real C11b evaluator + brief shim). **C11b NSGA converges with the real evaluator** → C12 activates the documented primary RefinedCandidate adapter path. 4,386 tests passing.

---

## TL;DR

S57 was a two-part extended session.

**Part A (first batch):** close follow-ups #4 (C12 adapter), #5 (C13 adapter), #6 (C14 metadata builder). Goal: pipeline alive past C11b end-to-end. All three closed; 22 → 40 orchestrator tests; full sweep 4,350 → 4,368.

**Part B (extension, user direction "finish first three pending items in this session"):** close follow-ups #1 (C7 full StructuralGridEngine), #2 (C11a M0-M9 operators), #3 (real C11b EvaluatorProtocol + brief shim). Goal: orchestrator-side advancement of all items not gated on adapter glue. All three closed; 40 → 58 orchestrator tests; full sweep 4,368 → **4,386**.

**Combined outcome:** 6 of 14 orchestrator follow-ups closed in S57. Default smoke fixture now exercises full C7 (grid + structure + foundation + cost). Opt-in `use_real_c11b_evaluator=True` flips C11b from STUB to OK via a real `MultiObjectiveEvaluator` plus a brief shim that fixes C11b's pre-existing requirement-extraction gap; when on, C12's primary RefinedCandidate adapter path activates automatically. Zero regressions across the full sweep.

---

## Order of work

| Phase | Cluster | Status |
|---|---|---|
| Phase 1 | Item #4 C12 adapter (C11b RefinedCandidate + C11a fallback) | ✅ COMPLETE |
| Phase 2 | Item #5 C13 adapter (place_doors wiring) | ✅ COMPLETE |
| Phase 3 | Item #6 C14 metadata builder (room_metadata_by_signature) | ✅ COMPLETE |
| Phase 4 | Full sweep + handoff docs (intermediate) | ✅ COMPLETE |
| Phase 5 (extension) | Item #1 C7 full StructuralGridEngine wiring | ✅ COMPLETE |
| Phase 6 (extension) | Item #2 C11a M0-M9 operator config | ✅ COMPLETE |
| Phase 7 (extension) | Item #3 Real C11b EvaluatorProtocol + brief shim | ✅ COMPLETE |
| Phase 8 (extension) | Full sweep + handoff docs (final) | ✅ COMPLETE |

---

## Phase 1 — Item #4 C12 adapter

**The interesting design problem:** C11b currently ships STUB in the orchestrator (BatchAllTopologiesFailedError caught → payload=None). The follow-ups doc's stated adapter takes `RefinedCandidate`, but there's no `RefinedCandidate` to consume while #3 is deferred. Options:

- **(A) Strict — wait for #3.** Don't ship #4 until C11b is real. Defeats "flip STUB to OK in S57" goal.
- **(B) Pragmatic — add a fallback path.** Build adapter that consumes either `RefinedCandidate` (when C11b ships OK) or `MutatedTopologyCandidate` (C11a output, when C11b ships STUB). Orchestrator picks the right path based on C11b's status.

**Chosen B.** Rationale: end-to-end aliveness > optimization quality at S57. Fallback path drops C11b's NSGA refinement (room dimensions come from C9 sizing rather than C11b refinement) — acceptable trade. When #3 ships later, the primary `RefinedCandidate` path naturally takes over with no orchestrator code change.

**New package:** `06_upstream_codebase/buildemup/orchestration/adapters/`
- `__init__.py` — re-exports.
- `c11b_to_c12.py` — three functions:
  - `adapt_refined_to_single_floor(refined, plot_analysis, *, room_categories_by_id)` — primary path. Builds `SingleFloorPlacementInput` from `RefinedCandidate`. Threads a category lookup because C11b's RefinedCandidate doesn't carry category data itself.
  - `adapt_mutated_to_single_floor(mutated, plot_analysis)` — fallback path. Walks `mutated.source_candidate.room_sized_candidate.room_size_table.rooms` to extract C9 sizing, then computes (width, depth) from target area + min-width via `_derive_dims_from_requirement`.
  - `build_single_floor_inputs_from_upstream(*, c11a_payload, c11b_payload, plot_analysis)` — orchestrator-facing dispatcher.

**Orchestrator change:** `master_orchestrator.py:`
- Replace `_stub_phase("c12_vertical_placement", ...)` with new `_run_c12_vertical_placement(c11a_payload, c11b_payload, plot_analysis)` method.
- Calls `place_and_align(single_floor_inputs=adapted, config=PlacementConfig(strict_mode=False), c11b_env_fingerprint_hash="orch:s57:c12_fallback")`.
- Returns OK when `PlacementBatchResult` is produced. Per-candidate failures captured in `batch.failures` are not phase-level failures (matches existing C11b STUB-catch pattern).

**Tests added:**
- `tests/test_orchestration/test_c12_adapter.py` — 7 tests: 2 for fallback path (uses real C4-C11a chain), 2 for primary path (synthetic RefinedCandidate), 3 for dispatcher routing.
- `tests/test_orchestration/test_master_orchestrator_smoke.py` — 1 new test (`test_c12_phase_flips_to_ok_via_fallback_adapter`).
- `tests/test_orchestration/test_orchestrate_endpoint.py` — 1 new test + existing stub-assertion narrowed.

**Effort actual:** ~2.5h (in the 2-3h estimate).

---

## Phase 2 — Item #5 C13 adapter

Simple compared to #4. C13's `place_doors` consumes C12's `placed_candidates` directly.

**Orchestrator change:** `_run_c13_doors(c12_payload)` calls:
```python
place_doors(
    placed_candidates=c12_payload.placed_candidates,
    config=DoorPlacementConfig(strict_mode=False),
    c12_cache_key=c12_payload.cache_key,
)
```
Mirrors the `_pipe_c12_to_c13` helper in C13's existing adversarial integration corpus exactly. WARN mode so per-candidate `DoorPositionInfeasibleError` failures (the documented sparse-edge problem — filed `B-C12-EDGE-DENSITY`) get captured inside `batch.failed` rather than halting the phase.

**Tests added:**
- 1 new smoke test (`test_c13_phase_flips_to_ok_via_place_doors`).
- Endpoint test updated to assert C13 OK.

**Effort actual:** ~30 min (under the 1h estimate — adapter is a 5-line function call).

---

## Phase 3 — Item #6 C14 metadata builder

C14's `analyze_circulation_batch` needs `room_metadata_by_signature: dict[str, tuple[RoomMetadata, ...]]` where:
- Key = `source_placed_candidate_signature` (C13's signature, traces back to C12's).
- Value = per-room RoomMetadata with category + `is_main_entry_room` flag.

The flag is the interesting bit. Derived from the C13 door with `is_main_entry=True`: its non-EXTERNAL endpoint is the entry room. Handles the degenerate "both endpoints internal" case via lex-ASC tiebreak (matches C14's own `_derive_main_entry_room_id`).

**New module:** `orchestration/adapters/c12_c13_to_c14.py` exports `build_room_metadata_by_signature(*, c12_payload, c13_payload)`. Indexes C12 placed candidates by signature for O(1) lookup; for each C13 success, finds the corresponding C12 placement and builds the metadata tuple.

**Orchestrator change:** `_run_c14_connection_graph(c12_payload, c13_payload)` calls `analyze_circulation_batch(batch=c13_payload, room_metadata_by_signature=metadata, config=CirculationConfig(), strict_mode=False)`.

**Tests added:**
- `tests/test_orchestration/test_c14_metadata_builder.py` — 8 unit tests covering main-entry derivation edge cases + builder routing (uses synthetic fakes, no full chain).
- 1 new smoke test (`test_c14_phase_flips_to_ok_via_circulation_batch`).
- Endpoint test updated.

**Effort actual:** ~1h (in the 1-1.5h estimate).

---

## Phase 4 — Verification

| Run | Result | Notes |
|---|---|---|
| `tests/test_orchestration` (smoke + adapters + metadata) | 40 passed | was 22 at S56 close; +18 in S57 |
| Full sweep `tests` | **4,368 passed / 0 failed / 31 skipped** | was 4,350; +18 matches the new orchestrator tests |

Zero regressions. All existing tests unaffected by the C12/C13/C14 wiring.

---

## Phase 5 (extension) — Item #1 C7 full StructuralGridEngine wiring

S57 Part A's #4-#6 left items #1, #2, #3 deferred to S58. User direction during the session: "finish the first three pending items in this session itself." All three closed below.

**Discovery:** The follow-up doc referenced `StructuralGridEngine().execute()` but the C7 subpackage (`components/c07/`) only exposes the building blocks (`GridGenerator`, `StructuralSizer`, `FoundationEngine`, `StructuralCostEstimator`). The real composed engine lives at the top-level module `buildemup/components/c07_structural_grid.py` — a coordinator that pulls in all four sub-components. That's what S57 wires.

**Orchestrator change:**
- New config field `MasterOrchestratorConfig.enable_full_structural_engine: bool = True` (default ON).
- `_run_c07_structural_grid` checks the flag: full path calls `StructuralGridEngine().execute(StructuralGridInput(...))` → `StructuralGridOutput` (grid + structure + foundation + cost + sensitivity). MVP path keeps `GridGenerator().generate()` for back-compat.
- New helper `_extract_grid(c07_result)` reads `.grid` from either payload shape. Downstream C8/C9/C10/C11a unchanged.

**Defaults used in StructuralGridInput:** `floors_above_ground=2`, `seismic_zone="II"`, `building_type=RESIDENTIAL_SINGLE_FAMILY`. City auto-detected from `plot_analysis.plot.city` with "chennai" fallback.

**Fix note:** Initially used `output.cost.exact` in notes string — the field is actually `exact_value`. Fixed.

**Tests added:**
- `test_c7_full_engine_payload_carries_structure_and_cost` — asserts grid + structure + foundation + cost fields populate.
- `test_c7_mvp_compat_path_returns_grid_directly` — asserts the back-compat path still works.

**Effort actual:** ~45 min.

---

## Phase 6 (extension) — Item #2 C11a M0-M9 operator suite

Simple config-only change as expected.

**Orchestrator change:**
- New config field `MasterOrchestratorConfig.enable_full_mutation_operators: bool = False` (default OFF — smoke test stays small).
- `_run_c11a_topology_mutation` branches on the flag. When True, enables the full 16-operator suite (M0_BASE + M1_HORIZ_FLIP + M2_VERT_FLIP + M3A/M3B/M3C + M4_CORRIDOR_INV + M5_ZONE_SWAP + M6_WET_ROTATE + M7A/M7B + M8_VERT_REARR + M9A/M9B/M9C/M9D).
- Notes line records which mode ran ("full M0-M9" vs "M0_BASE only") and the variant count.

**Doc-vs-reality fix:** The follow-up doc listed M9 operators as `M9A_ENTRY_NE_CENTER` etc. The actual enum names per `c11a/schema.py` are `M9A_ENTRY_CTR` / `M9B_ENTRY_W` / `M9C_ENTRY_E` / `M9D_ENTRY_OFF`. Used the real names.

**Test added:** `test_c11a_full_operator_suite_produces_more_variants` — runs default vs. full configs and asserts full ≥ default variant count.

**Effort actual:** ~20 min.

---

## Phase 7 (extension) — Item #3 Real C11b EvaluatorProtocol + brief shim

Hardest of the three. Required diagnosing a pre-existing C11b extraction gap before the real evaluator could land.

**New module:** `06_upstream_codebase/buildemup/orchestration/evaluators.py`.

### Part 1 — Real EvaluatorProtocol

`MultiObjectiveEvaluator` implements `EvaluatorProtocol` with three NSGA-friendly objectives derived from upstream context + candidate dimensions:

1. **`area_undersizing`** — `sum(max(0, target_m2 - actual_m2)²)` across rooms. Quadratic penalty on under-sized rooms only (C12 handles envelope fit, so oversize isn't penalized here). Zero at C9 target.
2. **`aspect_penalty`** — `sum((aspect_ratio - 1)²)` where aspect = max(w,d)/min(w,d). Zero for perfect squares.
3. **`envelope_waste`** — `max(0, envelope_area - total_room_area)`. Zero when fully utilizing the plot.

All three are "lower is better" per NSGA-II convention, smooth, and have well-defined gradients.

`build_real_evaluator_from_upstream(*, c11a_payload, plot_analysis)` constructor walks C11a → C10 → C9 to pull per-room context (target areas + min widths).

### Part 2 — The brief-shim discovery

Initial test run: real evaluator wired, but C11b still shipped STUB (BatchAllTopologiesFailedError). Diagnosis: C11b's internal `_extract_requirements_and_envelope(floor_room_brief, grid, plot_analysis)` looks for per-room `min_width_m` / `min_depth_m` on `floor_room_brief.room_requirements`. The canonical `FloorRoomBrief` (used by C5/C8/C9) carries only high-level counts (`bedroom_count`, `has_kitchen`, etc.) — no per-room dimension data. Result: zero requirements extracted → NSGA produced zero candidates regardless of evaluator quality.

The per-room data already exists upstream in C9's `RoomSizeTable`. So the fix: build a shim brief carrying the C9 data in the shape C11b expects, pass IT (instead of the canonical FloorRoomBrief) to C11b.

`C11bBriefShim` + `build_c11b_brief_shim_from_upstream(c11a_payload)` ship this. After wiring, NSGA converges on the smoke fixture: 60 RefinedCandidates produced.

### Cascade effect on C12

When C11b ships OK with refined candidates, the C12 dispatcher (from S57 #4) auto-routes from the C11a fallback path to the documented PRIMARY `adapt_refined_to_single_floor` path. **No orchestrator code change needed** — the dispatcher's conditional already handles this. The S57 #4 design (fallback for now, primary for later) paid off here.

Also fixed: the dispatcher's `_extract_refined_candidates` now handles both `RefinementBatchResult` (with `.refined_candidates`) and raw `tuple[RefinedCandidate, ...]` (what `run_local_refinement` actually returns).

### Orchestrator wiring

- New config field `MasterOrchestratorConfig.use_real_c11b_evaluator: bool = False` (default OFF — preserves StubEvaluator + STUB path for deterministic smoke tests).
- `_run_c11b_refinement` branches on the flag. When True: builds the real evaluator + brief shim, passes both to `run_local_refinement`. Notes record evaluator kind + refined-candidate count.

### Tests added

`tests/test_orchestration/test_c11b_real_evaluator.py` — 13 tests:
- 7 evaluator-behavior tests with synthetic RefinedCandidates (zero-at-target, quadratic-undersize-grow, oversize-not-penalized, square-zero-aspect, elongated-grows, envelope-zero-at-full, envelope-positive-when-under-utilized)
- 3 signature-stability tests
- 1 builder edge case (empty C11a payload)
- 1 constructor guard (non-positive envelope area)
- 1 orchestrator integration (C11b flips to OK)
- 1 cascade test (C12 primary path activates)

**Effort actual:** ~3h (in the 4-6h estimate; brief-shim diagnosis ate ~1h).

---

## What S57 deliberately did NOT touch

After the S57 extended session, the following still-pending items remain:

- **#7 C15 triples** — easy win now that C12+C13+C14 ship OK; logical next session.
- **#8 C16 UpstreamInputBundle** — biggest near-term architect-visibility value (produces drawings).
- **#9 C17 separate flow** — depends on quote-upload UI.
- **#10 C3a/C3b integration** — design decision needed.
- **#11 free-form HTTP input** — currently fixture-only.
- **#12 phase-payload serialization** — endpoint returns status + metadata only.
- **#13 scenario corpus** — single smoke fixture today.
- **#14 UI surface** — no UI for orchestrator results.
- **B-220 (plumbing engineer outreach)** — calendar-bound, not Claude work.
- **B-238 (architect outreach)** — calendar-bound, in progress on Ramalingam's side.

---

## File map of S57 changes

| File | Change |
|---|---|
| `06_upstream_codebase/buildemup/orchestration/adapters/__init__.py` | NEW — adapter package marker + re-exports |
| `06_upstream_codebase/buildemup/orchestration/adapters/c11b_to_c12.py` | NEW — RefinedCandidate + MutatedTopologyCandidate adapters + dispatcher |
| `06_upstream_codebase/buildemup/orchestration/adapters/c12_c13_to_c14.py` | NEW — room_metadata_by_signature builder |
| `06_upstream_codebase/buildemup/orchestration/master_orchestrator.py` | MODIFIED — added `_run_c12_vertical_placement`, `_run_c13_doors`, `_run_c14_connection_graph`; removed corresponding `_stub_phase` calls |
| `06_upstream_codebase/buildemup/tests/test_orchestration/test_c12_adapter.py` | NEW — 7 adapter unit tests |
| `06_upstream_codebase/buildemup/tests/test_orchestration/test_c14_metadata_builder.py` | NEW — 8 metadata-builder unit tests |
| `06_upstream_codebase/buildemup/tests/test_orchestration/test_master_orchestrator_smoke.py` | MODIFIED — added C12/C13/C14 OK assertions; renamed stub-assertion test from `test_c12_through_c17_phases_marked_stub` to `test_c15_through_c17_phases_marked_stub` |
| `06_upstream_codebase/buildemup/tests/test_orchestration/test_orchestrate_endpoint.py` | MODIFIED — same shift; added `test_endpoint_reports_c12_c13_c14_ok_via_adapters` |
| `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` | MODIFIED — marked #1/#2/#3/#4/#5/#6 ✅ CLOSED; updated phase-status table; updated S58 priority guidance |
| `00_START_HERE/S57_SESSION_LOG.md` | NEW — this file |
| `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` | MODIFIED — S58 entry, new baseline (4,386), new orchestrator status |
| **Phase 5/6/7 (extension) additions:** | |
| `06_upstream_codebase/buildemup/orchestration/evaluators.py` | NEW — MultiObjectiveEvaluator + RoomEvaluationContext + C11bBriefShim + builders (S57 #3) |
| `06_upstream_codebase/buildemup/orchestration/master_orchestrator.py` | MODIFIED — full StructuralGridEngine wiring (#1), M0-M9 operator config (#2), real-evaluator + brief-shim wiring (#3) |
| `06_upstream_codebase/buildemup/orchestration/adapters/c11b_to_c12.py` | MODIFIED — `_extract_refined_candidates` now handles both RefinementBatchResult AND raw tuple shape |
| `06_upstream_codebase/buildemup/tests/test_orchestration/test_master_orchestrator_smoke.py` | MODIFIED — 3 new tests (C7 full engine payload, C7 MVP-compat, C11a full operator suite) |
| `06_upstream_codebase/buildemup/tests/test_orchestration/test_c11b_real_evaluator.py` | NEW — 13 evaluator unit tests + 2 integration tests |

---

## Critical landmines for the next Claude (delta from S56)

### Landmine 1 (UPDATED) — 4,368 is the new test count
- S55 → S56 phase 2 dropped by 140 (removed wasted C10 duplicates) → 4,328
- S56 phase 2 → S56 phase 3 added 22 (orchestration tests) → 4,350
- **S56 → S57 added 18 (adapter + metadata + flipped existing tests) → 4,368**

### Landmine 2 (UPDATED) — C11b is still STUB in the orchestrator
The C12 adapter's PRIMARY path (`adapt_refined_to_single_floor`) is wired but unused at S57 because C11b doesn't ship a `RefinementBatchResult`. The FALLBACK path (`adapt_mutated_to_single_floor`) is what's actually active. When follow-up #3 ships a real `EvaluatorProtocol`, C11b will flip to OK and the primary path takes over automatically — no orchestrator code change needed.

### Landmine 3 (UPDATED) — C15-C17 still STUB
C12-C14 flipped to OK in S57. C15 (#7), C16 (#8), C17 (#9) still STUB. C15 is the easiest next-step now that all three upstream phases are OK.

### Landmine 4 (UPDATED) — Adapter category lookup
The PRIMARY-path adapter (`adapt_refined_to_single_floor`) requires a `room_categories_by_id` dict because RefinedCandidate doesn't carry categories. The dispatcher (`build_single_floor_inputs_from_upstream`) builds this lookup from C11a's upstream wet-zoned candidates. If #3 lands and C11b ships RefinedCandidate output, this lookup must still be threaded — make sure that path stays correct.

### Landmine 5 — C12 sparse-edge problem
C12's slicing-tree typically produces 0 shared edges for multi-room layouts in the smoke fixture (per the C13 adversarial integration corpus). C13 then produces 0 successful placements. C14 then has empty metadata. **This is all working as designed** — filed as `B-C12-EDGE-DENSITY` post-LOCK. Phases ship OK regardless because the orchestrator's "OK = call succeeded" semantics match the architecture's intentional decoupling. Do not try to "fix" this in the orchestrator; the fix is in C12's placement algorithm and tracked separately.

### Inherited from S56 (still applies)
- Landmine 6 — LOCKED specs immutable; amend, don't edit
- Landmine 7 — Run pytest from `06_upstream_codebase/buildemup/` (worktree path now `distracted-newton-d8ec13`)
- Landmine 8 — Frontend changes need server restart
- Landmine 9 — Inherited landmines (C1/C7 layouts, GitHub repo PRIVATE, non-engineer user, Vastu FULL hidden)

---

## Numbers

- Tests at S56 close: 4,350
- Tests at S57 Part A: 4,368 (+18)
- Tests at S57 extended close: **4,386** (+18, total +36)
- Orchestrator tests: 22 → 40 (Part A) → **58** (extended)
- Files added: 6 (3 adapters + evaluators.py + 3 test files)
- Files modified: 5 (orchestrator + 3 existing tests/docs + adapter dispatcher)
- Items closed at S57: **#1, #2, #3, #4, #5, #6** (6 of 14, ~50%)
- Items deferred to S58+: #7, #8, #9, #10, #11, #12, #13, #14 (8 remaining)
- B-238 architect outreach: Ramalingam-driven; calendar-bound, no Claude work
- B-220 plumbing engineer outreach: Ramalingam-driven; calendar-bound, no Claude work

---

**Handoff to S58:** Read `00_START_HERE/NEXT_CLAUDE_HANDOFF.md`. The 8 remaining follow-ups are documented in `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` with #1/#2/#3/#4/#5/#6 marked ✅ CLOSED. Recommended next focus: #8 (C16 drawings — highest architect-visibility) or #7 (C15 triples — easy win).
