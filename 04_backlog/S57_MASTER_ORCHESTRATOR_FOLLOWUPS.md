# S57 — Master Orchestrator Follow-Ups (MUST do next session)

**Authored:** S56, May 16, 2026, Ramalingam + Claude
**Context:** S56 shipped the **MVP MasterOrchestrator** (`06_upstream_codebase/buildemup/orchestration/`) that walks all 17 components. C4-C11a run as a real chain; C11b runs the real orchestrator but uses C11b's built-in `StubEvaluator` (BatchAllTopologiesFailedError is caught and converted to STUB status). C12-C17 ship as STUB-status phases pending adapter glue.

**This document is the explicit punch list of what S57 must close so the orchestrator advances from MVP → production-quality.** Items are ordered by leverage. Each item lists exact file paths and contracts.

---

## Status of phases at S56 close

| Phase | S56 status | What's needed to upgrade to OK |
|---|---|---|
| `c01_brief` | SKIPPED (no full Brief provided) or OK (if Brief passed) | None — works as designed; SKIP is correct default |
| `c02_feasibility` | SKIPPED or OK | None — works as designed |
| `c04_plot_analysis` | OK | None |
| `c05_topology` | OK | None |
| `c06_orientation` | OK | None |
| `c07_structural_grid` | OK (GridGenerator only) | Upgrade to full `StructuralGridEngine().execute()` for sizing + foundation + cost (see Follow-up #1) |
| `c08_corridor` | OK | None |
| `c09_room_sizer` | OK | None |
| `c10_wet_zones` | OK | None |
| `c11a_topology_mutation` | OK (M0_BASE only) | Enable M1-M9 operators (see Follow-up #2) |
| `c11b_nsga_refinement` | STUB | Real EvaluatorProtocol implementation (see Follow-up #3) |
| `c12_vertical_placement` | STUB | C11b→C12 adapter (see Follow-up #4) |
| `c13_doors` | STUB | C12→C13 adapter + DoorPlacementConfig (see Follow-up #5) |
| `c14_connection_graph` | STUB | room_metadata_by_signature builder (see Follow-up #6) |
| `c15_problem_finder` | STUB | (C12,C13,C14) triples + ProblemAnalysisMetadata (see Follow-up #7) |
| `c16_dual_drawings` | STUB | UpstreamInputBundle assembly (see Follow-up #8) |
| `c17_quote_comparison` | STUB | Separate user-uploaded-quote flow (see Follow-up #9) |

---

## Follow-up #1 — C7 full StructuralGridEngine wiring

**Current state:** `_run_c07_structural_grid` calls only `GridGenerator().generate(...)` which produces column positions. The full `StructuralGridEngine().execute(...)` adds structural sizing (beams, slabs, columns dimensions), foundation engineering, and cost estimation.

**Effort:** ~1-2 hours.

**Action:**
1. Construct a `StructuralGridInput` from upstream `PlotAnalysis` + `FloorRoomBrief`. Fields:
   - `envelope_width_m` / `envelope_depth_m` (from plot analysis)
   - `floors_above_ground` (from floor_brief or default 2)
   - `city`, `seismic_zone`, `has_stilt_parking`, `has_terrace_access`, `has_water_tank`, `plot_facing` (defaults or from plot/brief)
   - `building_type=BuildingType.RESIDENTIAL_SINGLE_FAMILY`
2. Call `StructuralGridEngine().execute(input)` → `SizedStructure` + `FoundationDesign` + cost estimate
3. Update `_run_c07_structural_grid` payload to include both grid + structure + foundation + cost
4. Update smoke test to verify the upgraded payload

**File:** `06_upstream_codebase/buildemup/orchestration/master_orchestrator.py` — `_run_c07_structural_grid` method
**Test:** `06_upstream_codebase/buildemup/tests/test_orchestration/test_master_orchestrator_smoke.py` — `test_c4_c11a_phases_produce_real_outputs`

---

## Follow-up #2 — C11a enable M1-M9 mutation operators

**Current state:** MVP uses `enabled_operators=(MutationOperator.M0_BASE,)` for fast smoke tests. Production wants the full operator suite.

**Effort:** ~30 min (config-only change + adjusted test expectations).

**Action:**
1. In `MasterOrchestratorConfig`, add `enable_full_mutation_operators: bool = False` field.
2. In `_run_c11a_topology_mutation`, if `enable_full_mutation_operators=True`, use:
   ```python
   enabled_operators=(
       MutationOperator.M0_BASE,
       MutationOperator.M1_HORIZ_FLIP,
       MutationOperator.M2_VERT_FLIP,
       MutationOperator.M3A_STAIR_EAST,
       MutationOperator.M3B_STAIR_WEST,
       MutationOperator.M3C_STAIR_NE,
       MutationOperator.M4_CORRIDOR_INV,
       MutationOperator.M5_ZONE_SWAP,
       MutationOperator.M6_WET_ROTATE,
       MutationOperator.M7A_GRID_3_3,
       MutationOperator.M7B_GRID_2_7,
       MutationOperator.M8_VERT_REARR,
       MutationOperator.M9A_ENTRY_NE_CENTER,
       MutationOperator.M9B_ENTRY_NE_CORNER_W,
       MutationOperator.M9C_ENTRY_NE_CORNER_E,
       MutationOperator.M9D_ENTRY_OFFSET_NE,
   )
   ```
3. Add a new smoke test that runs with `enable_full_mutation_operators=True` and verifies multiple variants are produced.

**File:** `master_orchestrator.py` — `MasterOrchestratorConfig` + `_run_c11a_topology_mutation`
**Test:** new `test_c11a_full_operator_suite_produces_multiple_variants` in `test_master_orchestrator_smoke.py`

---

## Follow-up #3 — Real EvaluatorProtocol for C11b

**Current state:** C11b uses `StubEvaluator(StubEvaluatorConfig())`. The stub's heuristic scoring doesn't satisfy NSGA convergence — every batch fails under WARN mode and we catch the `BatchAllTopologiesFailedError` to convert to STUB status.

**Effort:** ~half-session to one full session. This is the largest follow-up.

**Action:**
1. Define what "real" evaluator means: NSGA-II requires objective vectors per candidate. Objectives likely include:
   - `accessibility_score` (from C14 graph metrics)
   - `wet_zone_economy` (from C10 risk)
   - `corridor_efficiency` (from C8 area accounting)
   - `programmatic_match` (from C9 room sizing satisfaction)
2. Build `MultiObjectiveEvaluator(EvaluatorProtocol)` in `buildemup/orchestration/evaluators.py` (new file).
3. Wire `_run_c11b_refinement` to use the new evaluator when `config.use_real_evaluator=True`.
4. Add tests asserting C11b phase produces OK status with real evaluator.

**File:** new `06_upstream_codebase/buildemup/orchestration/evaluators.py` + update `_run_c11b_refinement`
**Test:** new `test_c11b_with_real_evaluator_produces_refined_candidates`

**Reference:** `06_upstream_codebase/buildemup/components/c11b/evaluator.py` — see `EvaluatorProtocol` shape + `StubEvaluator` for what the contract requires.

---

## Follow-up #4 — C12 adapter: C11b RefinedCandidate → SingleFloorPlacementInput

**Current state:** STUB. C12's `place_and_align` requires `single_floor_inputs: tuple[SingleFloorPlacementInput, ...]` with specific fields: `candidate_signature`, `capability_mode`, `placement_safe`, `geometry_materialized`, `rooms: tuple[RoomSpec, ...]`, `envelope_width_m`, `envelope_depth_m`, `adjacency_hints`.

**Effort:** ~2-3 hours. The adapter is the bulk of C12 integration.

**Action:**
1. Add `adapters/c11b_to_c12.py` in `buildemup/orchestration/`:
   ```python
   def adapt_refined_to_single_floor(
       refined: RefinedCandidate,
       plot_analysis: PlotAnalysis,
   ) -> SingleFloorPlacementInput:
       # Build RoomSpec tuple from refined.rooms (RefinedParameters)
       # Compute candidate_signature, set placement_safe=True, etc.
       ...
   ```
2. Compute `c11b_env_fingerprint_hash` via `capture_environment_fingerprint(...)`.
3. Build `PlacementConfig()` with MVP defaults.
4. Update `_run_c12_vertical_placement` (currently `_stub_phase`) to call `place_and_align(single_floor_inputs=adapted, config=config, c11b_env_fingerprint_hash=fp)`.
5. Replace STUB status with OK status when adapter succeeds.

**File:** new `06_upstream_codebase/buildemup/orchestration/adapters/__init__.py` + `adapters/c11b_to_c12.py` + update `master_orchestrator.py`
**Test:** new `test_c12_vertical_placement_runs_with_c11b_adapter`

---

## Follow-up #5 — C13 adapter: C12 PlacedCandidate → place_doors batch

**Current state:** STUB. C13's `place_doors` requires `placed_candidates: Iterable` (the successful_placements from C12's PlacementBatchResult) + `config: DoorPlacementConfig` + `c12_cache_key: str`.

**Effort:** ~1 hour. Much simpler than #4 since C12's output is closer to C13's input.

**Action:**
1. In `_run_c13_doors` (currently stub), iterate `c12_result.payload.successful_placements`.
2. Construct `DoorPlacementConfig()` with v1 defaults.
3. Compute `c12_cache_key` (likely from `c12_result.payload.cache_key` field or via `derive_c12_cache_keys`).
4. Call `place_doors(placed_candidates=placements, config=config, c12_cache_key=cache_key)` → `DoorPlacementBatchResult`.
5. Mark status OK; thread payload to C14.

**File:** `master_orchestrator.py` — replace `_stub_phase("c13_doors", ...)` with real method
**Test:** new `test_c13_doors_runs_after_c12`

---

## Follow-up #6 — C14 room_metadata_by_signature builder

**Current state:** STUB. C14's `analyze_circulation_batch` requires `room_metadata_by_signature: dict[str, tuple[RoomMetadata, ...]]`. RoomMetadata holds room category, function, etc. — built from upstream room data.

**Effort:** ~1-1.5 hours.

**Action:**
1. Build `_build_room_metadata_by_signature(c12_placement_batch)` helper.
2. For each `PlacedCandidate`, extract room categories from `c10_result.payload` + `c12_result.payload`, build a `RoomMetadata` tuple, key by `candidate_signature`.
3. Call `analyze_circulation_batch(batch=c13_result.payload, room_metadata_by_signature=metadata)`.

**File:** `master_orchestrator.py` — replace `_stub_phase("c14_connection_graph", ...)` with real method
**Test:** new `test_c14_connection_graph_runs_after_c13`

---

## Follow-up #7 — C15 (C12,C13,C14) triples + ProblemAnalysisMetadata

**Current state:** STUB. C15's `analyze_problems_batch` requires `triples: Sequence[tuple[object, object, object]]` (one per candidate: C12 placement, C13 doors, C14 circulation report) + `metadata_per_candidate: Sequence[ProblemAnalysisMetadata]`.

**Effort:** ~1-1.5 hours.

**Action:**
1. Build triples by zipping `c12_result.payload.successful_placements` × `c13_result.payload.successful_door_placements` × `c14_result.payload.successful_analyses`.
2. Build `ProblemAnalysisMetadata` per candidate (cultural_profile_active from config.vastu_tier).
3. Call `analyze_problems_batch(triples=triples, metadata_per_candidate=metadata, config=ProblemFinderConfig())`.

**File:** `master_orchestrator.py` — replace `_stub_phase("c15_problem_finder", ...)`
**Test:** new `test_c15_problem_finder_runs_with_full_chain`

---

## Follow-up #8 — C16 UpstreamInputBundle assembly

**Current state:** STUB. C16's `render_drawings_batch` requires `upstream_inputs_per: tuple[UpstreamInputBundle, ...]`. UpstreamInputBundle is the heaviest adapter — assembles data from C7 (grid), C9 (rooms), C10 (wet zones), C12 (placement), C13 (doors).

**Effort:** ~3-4 hours. This is the second-largest follow-up after C11b.

**Action:**
1. Build `adapters/upstream_input_bundle_builder.py`:
   ```python
   def build_upstream_input_bundle(
       *, grid, room_sized, wet_zoned, placed, doors, plot_analysis,
   ) -> UpstreamInputBundle:
       # See c16/upstream_adapter.py for the dataclass structure
       ...
   ```
2. Construct `JurisdictionProfile` (TamilNadu / Chennai for MVP).
3. Construct `RenderingConfig()` with default IS 962:1967 conformance.
4. Construct `SelectionResult` tuple from C12 output (selected candidates).
5. Call `render_drawings_batch(selection_results=sel, upstream_inputs_per=bundles, jurisdiction_profile=jp, config=rc)`.

**File:** new `06_upstream_codebase/buildemup/orchestration/adapters/upstream_input_bundle_builder.py` + update `master_orchestrator.py`
**Test:** new `test_c16_drawings_render_with_full_chain`

**Reference:** `06_upstream_codebase/buildemup/components/c16/upstream_adapter.py` — `UpstreamInputBundle` dataclass shape.

---

## Follow-up #9 — C17 user-uploaded-quote flow

**Current state:** STUB. C17 (`run_c17`) requires `parsed_quote: ParsedQuote` (typically from user-uploaded PDF/Excel) + `cost_lines: tuple[CostLine, ...]` (from C7) + `rate_provider` + `project_id`. C17 is NOT strictly downstream of the layout pipeline — it's a separate flow where the user uploads a contractor quote and the system compares.

**Effort:** ~3-4 hours, mostly UX work outside the orchestrator.

**Action:**
1. Decide UX: should C17 be invoked as a SEPARATE endpoint (`/api/quote/compare`) rather than via the master orchestrator? Probably yes.
2. Build separate `api/quote_endpoint.py` accepting a parsed_quote payload + project_id, running `run_c17`, returning the QuoteComparisonReport.
3. Optionally add a follow-up `/api/orchestrate-with-quote` that wires the full pipeline + C17 in one call (project_id linking).
4. Build minimal UI for upload (out of scope for orchestrator; tracked separately).

**File:** new `06_upstream_codebase/buildemup/api/quote_endpoint.py` + new `06_upstream_codebase/buildemup/static/quote_upload.html`
**Test:** new `tests/test_orchestration/test_quote_endpoint.py`

---

## Follow-up #10 — C3a/C3b integration with master orchestrator

**Current state:** SKIPPED entirely. C3a (extreme-case detection) is session-stateful; C3b (negotiation) too. Both are already HTTP-accessible via `/api/c3a/*`.

**Effort:** ~2-3 hours. Design problem more than implementation problem.

**Action:**
1. Decide flow: when a brief enters the orchestrator, should C3a be invoked synchronously to detect extreme cases, then halt to allow user-facing negotiation (via C3b) before continuing C4-C16? Or run the full pipeline regardless and surface C3a flags in the result?
2. If synchronous-with-halt: orchestrator needs a "RESUMED_FROM_C3B" entry mode.
3. If async-with-flags: c3a detection runs as a pure step; flags surface in the result; pipeline continues.

**Recommendation:** async-with-flags. Halt-mode is too disruptive for an MVP pipeline.

**File:** `master_orchestrator.py` — add `_run_c3a_detection` between C2 and C4 phases; flag mode in config
**Test:** new `test_c3a_detection_surfaces_flags_without_halting`

---

## Follow-up #11 — Free-form Plot + FloorRoomBrief input contract

**Current state:** The `/api/orchestrate` HTTP endpoint accepts only NAMED FIXTURE inputs (`plot_fixture: bangalore_40x60`, `brief_fixture: medium_brief`). Production users will need free-form inputs.

**Effort:** ~3-4 hours (input validation surface is the work).

**Action:**
1. Define the JSON shape that maps to `Plot` + `FloorRoomBrief` + `Brief`. Closely mirror what `/api/brief/capture` already accepts.
2. Build `_parse_orchestrate_request(payload) -> tuple[Plot, Brief, FloorRoomBrief]` in `orchestrate_endpoint.py`.
3. Reuse C1's existing input-validation surface where possible (typed exceptions from `domain/exceptions.py` per B-013).
4. Add validation tests.

**File:** `06_upstream_codebase/buildemup/api/orchestrate_endpoint.py`
**Test:** add to `tests/test_orchestration/test_orchestrate_endpoint.py`

---

## Follow-up #12 — Phase-payload JSON serialization

**Current state:** Phase payloads (PlotAnalysis dataclass, candidate tuples, etc.) are NOT serialized in the HTTP response. Response carries only per-phase status + metadata.

**Effort:** ~2 hours.

**Action:**
1. For each phase, define a `_serialize_phase_payload(phase_id, payload) -> dict` helper.
2. Most dataclasses have safe `__repr__` or asdict shapes. Frozen dataclasses serialize cleanly via `dataclasses.asdict`.
3. Add `include_payloads: bool = False` config field to `MasterOrchestratorConfig`. When True, response includes serialized payloads.
4. Test response size with full payload inclusion.

**File:** `orchestrate_endpoint.py` + `master_orchestrator.py`
**Test:** new endpoint tests with `include_payloads=True`

---

## Follow-up #13 — Comprehensive fixture corpus for orchestrator scenarios

**Current state:** Single smoke-test fixture (`bangalore_40x60` + `medium_brief`). MVP doesn't exercise edge cases.

**Effort:** ~1 session, deeply parallelizable.

**Action:**
1. Build orchestrator-scenario fixtures: Chennai narrow plot, Pune BLACK_COTTON soil (after B-NEW-PUNE-SOIL-SCENARIO-REFRESH), Mumbai stilt parking, Bangalore G+2, Delhi corner plot.
2. For each, verify orchestrator produces sensible results.
3. This becomes the v1 acceptance suite for the orchestrator.

**File:** new `tests/test_orchestration/test_master_orchestrator_scenarios.py`
**Test:** ~10-15 new tests covering edge cases

---

## Follow-up #14 — UI to surface orchestrator results

**Current state:** No UI. `/api/orchestrate` returns JSON only.

**Effort:** ~1 session (frontend).

**Action:**
1. Build `static/orchestrator_run.html` — form to choose plot + brief fixture, run, display per-phase status with color-coded chips.
2. Link from `brief_form.html` ("Run full pipeline →").
3. Drawing surface (C16 output) — image rendering once Follow-up #8 produces drawings.

**File:** new `06_upstream_codebase/buildemup/static/orchestrator_run.html` + `orchestrator_run.js`
**Test:** Playwright e2e in `tests/e2e/test_orchestrator_run_ui.py`

---

## Effort summary (rough)

| Follow-up | Hours |
|---|---|
| #1 C7 full StructuralGridEngine | 1-2 |
| #2 C11a M1-M9 operators | 0.5 |
| #3 Real C11b EvaluatorProtocol | 4-6 |
| #4 C12 adapter | 2-3 |
| #5 C13 adapter | 1 |
| #6 C14 metadata | 1-1.5 |
| #7 C15 triples | 1-1.5 |
| #8 C16 UpstreamInputBundle | 3-4 |
| #9 C17 separate flow | 3-4 |
| #10 C3a/C3b integration | 2-3 |
| #11 Free-form inputs | 3-4 |
| #12 Payload serialization | 2 |
| #13 Fixture corpus | session |
| #14 UI | session |

**Total: ~25-30 hours, or 6-8 focused sessions.** This is the path from MVP → production-quality orchestrator.

**Priority order for S57 (if budget is one session):**
1. #5 C13 adapter (1h — easy win, demonstrates C12+C13 chained)
2. #6 C14 metadata (1.5h — easy win, demonstrates graph metrics)
3. #4 C12 adapter (2-3h — unblocks #5 + #6)
4. Skip #3 real evaluator until #4-#7 are wired (the chain works with StubEvaluator → STUB downstream; that's fine).

**Critical path:** B-238 architect feedback may reshape priorities — the architect may want to see drawings (Follow-up #8) before refinement quality (#3). Defer prioritization decisions until architect feedback lands.

---

## Closing record

| Item | Status |
|---|---|
| MVP orchestrator shipped | ✅ S56 |
| 22 orchestration tests passing | ✅ S56 |
| Full test sweep: 4,350 / 0 / 31 | ✅ S56 |
| Follow-ups doc | ✅ S56 (this file) |
| Real C11b evaluator | ⏸ S57+ |
| C12-C17 adapter glue | ⏸ S57+ |
| C3a/C3b integration | ⏸ S57+ |
| Free-form input contract | ⏸ S57+ |
| Phase-payload serialization | ⏸ S57+ |
| Scenario corpus | ⏸ S57+ |
| UI surface | ⏸ S57+ |
