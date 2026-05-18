# S57 — Master Orchestrator Follow-Ups

**Authored:** S56, May 16, 2026, Ramalingam + Claude
**S57 update (May 17, 2026):** Items #4/#5/#6 ✅ CLOSED (C12 + C13 + C14 OK). Items #1/#2/#3 ✅ CLOSED (C7 full engine, C11a M1-M9, real C11b evaluator). **C11b now ships OK with the real MultiObjectiveEvaluator + brief shim — C12 activates the documented PRIMARY adapter path.** 8 follow-ups remain.
**S59 update (May 18, 2026):** **ALL 14 FOLLOW-UPS NOW CLOSED.** S59 shipped #7 (C15 triples), #8 (C16 drawings), #9 (C17 quote endpoint), #10 (C3a/C3b async-flags), #11 (free-form input), #12 (payload serialization), #13 (scenario corpus), #14 (UI). The master orchestrator runs C4→C16 as a fully wired chain; C17 runs via a separate `/api/quote/compare` flow; PIPELINE_PHASES grew from 17 → 18 (added `c03a_extreme_case_detection`). Static UI ships at `/orchestrator_run.html` + `/quote_compare.html`. **0 follow-ups remain — S60 is calendar-bound + component-bug territory only.** See `00_START_HERE/S59_SESSION_LOG.md` for the close-out record.

**Context:** S56 shipped the **MVP MasterOrchestrator** (`06_upstream_codebase/buildemup/orchestration/`) that walks all 17 components. S57 closed 6 follow-ups in one session: C7 runs the full StructuralGridEngine (grid + structure + foundation + cost); C11a supports the full M0-M9 operator suite; C11b uses a real EvaluatorProtocol (MultiObjectiveEvaluator + per-room brief shim) and now flips to OK; C12 activates the primary RefinedCandidate adapter path when C11b OK; C13/C14 ship OK. C15-C17 still STUB pending #7/#8/#9.

**This document is the explicit punch list.** Items are ordered by leverage. Each item lists exact file paths and contracts.

---

## Status of phases at S57 close

| Phase | Status | What's needed to upgrade to OK |
|---|---|---|
| `c01_brief` | SKIPPED (no full Brief provided) or OK (if Brief passed) | None — works as designed; SKIP is correct default |
| `c02_feasibility` | SKIPPED or OK | None — works as designed |
| `c04_plot_analysis` | OK | None |
| `c05_topology` | OK | None |
| `c06_orientation` | OK | None |
| `c07_structural_grid` | **OK with full engine (S57)** | ✅ #1 closed. `enable_full_structural_engine=True` (default) runs StructuralGridEngine → StructuralGridOutput. MVP-compat path still available |
| `c08_corridor` | OK | None |
| `c09_room_sizer` | OK | None |
| `c10_wet_zones` | OK | None |
| `c11a_topology_mutation` | **OK with M0-M9 (S57, opt-in)** | ✅ #2 closed. `enable_full_mutation_operators=True` enables M0 + M1-M9 |
| `c11b_nsga_refinement` | **OK with real evaluator (S57, opt-in)** | ✅ #3 closed. `use_real_c11b_evaluator=True` flips to OK via MultiObjectiveEvaluator + brief shim. Default `False` preserves StubEvaluator → STUB path for deterministic smoke tests |
| `c12_vertical_placement` | **OK (S57)** | ✅ #4 closed. Primary RefinedCandidate adapter activates when C11b OK; C11a fallback used when C11b STUB |
| `c13_doors` | **OK (S57)** | ✅ #5 closed. C12 PlacedCandidates → place_doors with WARN-mode config |
| `c14_connection_graph` | **OK (S57)** | ✅ #6 closed. room_metadata_by_signature builder ships in `orchestration/adapters/c12_c13_to_c14.py` |
| `c15_problem_finder` | STUB | (C12,C13,C14) triples + ProblemAnalysisMetadata (see Follow-up #7) |
| `c16_dual_drawings` | STUB | UpstreamInputBundle assembly (see Follow-up #8) |
| `c17_quote_comparison` | STUB | Separate user-uploaded-quote flow (see Follow-up #9) |

---

## Follow-up #1 — C7 full StructuralGridEngine wiring ✅ CLOSED (S57)

**Closed:** S57 (2026-05-17). `_run_c07_structural_grid` switched from `GridGenerator().generate(...)` to `StructuralGridEngine().execute(StructuralGridInput(...))` (in `06_upstream_codebase/buildemup/components/c07_structural_grid.py`). Payload is now `StructuralGridOutput` with `grid + structure + foundation + cost + sensitivity` populated.

**Orchestrator change:** new `_extract_grid(c07_result)` helper pulls the Grid object out of either the full-engine StructuralGridOutput (default) or the MVP-compat Grid payload (when `enable_full_structural_engine=False`). Downstream C8/C9/C10/C11a are unchanged.

**MVP-compat path:** `MasterOrchestratorConfig(enable_full_structural_engine=False)` reverts to S56-MVP behavior (Grid-only payload) for tests that pin that shape.

**Defaults used:** `floors_above_ground=2`, `seismic_zone="II"`, `building_type=RESIDENTIAL_SINGLE_FAMILY`. City is auto-detected from `plot_analysis.plot.city` (falls back to "chennai" for unsupported cities — the cost estimator handles this gracefully).

**Tests added:** 2 smoke tests (full-engine payload shape + MVP-compat path).

**Effort actual:** ~45 min (under the 1-2h estimate; mostly debugging field names).

---

## Follow-up #2 — C11a enable M1-M9 mutation operators ✅ CLOSED (S57)

**Closed:** S57 (2026-05-17). `MasterOrchestratorConfig.enable_full_mutation_operators: bool = False` added; when True, `_run_c11a_topology_mutation` enables M0_BASE + M1-M9 (full 16-operator suite). Default False keeps the smoke-test surface small.

**Doc-vs-reality note:** Follow-up doc listed `M9A_ENTRY_NE_CENTER` / `M9B_ENTRY_NE_CORNER_W` etc. but the actual enum names are `M9A_ENTRY_CTR` / `M9B_ENTRY_W` / `M9C_ENTRY_E` / `M9D_ENTRY_OFF` (per `c11a/schema.py`). The implementation uses the real names.

**Tests added:** 1 smoke test (`test_c11a_full_operator_suite_produces_more_variants`) — asserts full suite produces ≥ default-suite variant count and that notes record the active mode.

**Effort actual:** ~20 min (under the 30 min estimate).

---

## Follow-up #3 — Real EvaluatorProtocol for C11b ✅ CLOSED (S57)

**Closed:** S57 (2026-05-17). New module `06_upstream_codebase/buildemup/orchestration/evaluators.py` ships:

- `MultiObjectiveEvaluator` (implements `EvaluatorProtocol`) with three NSGA-friendly objectives derived from upstream context + candidate dimensions:
  1. `area_undersizing` — quadratic penalty on (target_area - actual_area) when room is under-sized
  2. `aspect_penalty` — sum of (aspect_ratio - 1)² across rooms
  3. `envelope_waste` — under-utilization of the plot envelope
- `build_real_evaluator_from_upstream(*, c11a_payload, plot_analysis)` — constructor helper that walks C11a → C10 → C9 to extract per-room context.
- `C11bBriefShim` + `build_c11b_brief_shim_from_upstream(c11a_payload)` — required because C11b's `_extract_requirements_and_envelope` looks for per-room `min_width_m` / `min_depth_m` attributes that the canonical `FloorRoomBrief` doesn't carry. The shim re-packages C9's `RoomSizeTable` rows in the shape C11b expects.

**Orchestrator wiring:** `MasterOrchestratorConfig.use_real_c11b_evaluator: bool = False`. When True, `_run_c11b_refinement` builds the real evaluator + brief shim from upstream and passes BOTH to `run_local_refinement`. NSGA converges on the smoke fixture (~60 RefinedCandidates produced; verified). C11b ships OK.

**Cascade effect:** When C11b ships OK with refined candidates, the C12 dispatcher (`build_single_floor_inputs_from_upstream`) auto-routes to the PRIMARY `adapt_refined_to_single_floor` path instead of the C11a fallback. The S57 #4 primary path activates without any orchestrator code change.

**Critical fix beyond the doc's spec:** The follow-up doc described an evaluator-only change, but C11b's brief-extraction logic was broken on the canonical `FloorRoomBrief` (zero requirements extracted → NSGA produced zero candidates regardless of evaluator). The shim bridges this. Without the shim, the real evaluator alone doesn't flip C11b to OK.

**Tests added:** `tests/test_orchestration/test_c11b_real_evaluator.py` (13 tests covering evaluator behavior, signature stability, construction guards) + 2 new smoke tests (C11b OK assertion + C12 primary-path activation).

**Effort actual:** ~3h (within the 4-6h estimate; the brief-shim diagnosis ate ~1h).

---

## Follow-up #4 — C12 adapter: C11b RefinedCandidate → SingleFloorPlacementInput ✅ CLOSED (S57)

**Closed:** S57 (2026-05-17). New package `06_upstream_codebase/buildemup/orchestration/adapters/` ships two adapter functions:

- `adapt_refined_to_single_floor(refined, plot_analysis, *, room_categories_by_id)` — the documented primary path. Builds `SingleFloorPlacementInput` from `RefinedCandidate` + a category lookup (C11b RefinedCandidate doesn't carry categories itself). Activates once #3 ships a real EvaluatorProtocol; until then this path is exercised only by unit tests.
- `adapt_mutated_to_single_floor(mutated, plot_analysis)` — the STUB-fallback. Sources room dimensions from the C9 `RoomSizeTable` embedded in the C10 wet-zoned candidate via `mutated.source_candidate.room_sized_candidate.room_size_table.rooms`. Used by the master orchestrator while C11b ships STUB. Drops C11b's optimization (acceptable trade for end-to-end aliveness at S57).
- `build_single_floor_inputs_from_upstream(*, c11a_payload, c11b_payload, plot_analysis)` — orchestrator-facing dispatcher. Prefers `RefinedCandidate` path if C11b shipped OK; falls back to the C11a path otherwise; returns empty tuple if both upstream payloads are missing.

**Orchestrator wiring:** `_run_c12_vertical_placement` calls `place_and_align(single_floor_inputs=..., config=PlacementConfig(strict_mode=False), c11b_env_fingerprint_hash="orch:s57:c12_fallback")`. Phase ships OK when the call returns a `PlacementBatchResult` — per-candidate failures captured inside the batch are not phase-level failures.

**Tests added:** `tests/test_orchestration/test_c12_adapter.py` (7 tests covering both adapter paths + dispatcher routing) + 2 new smoke tests in `test_master_orchestrator_smoke.py` and `test_orchestrate_endpoint.py`.

**Effort actual:** ~2.5h (within the 2-3h estimate). Counts toward the orchestrator-advance hour budget.

---

## Follow-up #5 — C13 adapter: C12 PlacedCandidate → place_doors batch ✅ CLOSED (S57)

**Closed:** S57 (2026-05-17). `_run_c13_doors(c12_payload)` in `master_orchestrator.py` calls:
```python
place_doors(
    placed_candidates=c12_payload.placed_candidates,
    config=DoorPlacementConfig(strict_mode=False),
    c12_cache_key=c12_payload.cache_key,
)
```
Pattern matches `_pipe_c12_to_c13` in the C13 adversarial integration corpus exactly.

Phase ships OK when call returns a `DoorPlacementBatchResult`. Per-candidate `DoorPositionInfeasibleError` failures (the documented sparse-edge problem from C13's adversarial corpus — filed as B-C12-EDGE-DENSITY) are captured inside `batch.failed` and are working-as-designed, not phase-level failures.

**Tests added:** 2 new tests (`test_c13_phase_flips_to_ok_via_place_doors` in smoke + endpoint OK assertion update).

**Effort actual:** ~30 min (came in under the 1h estimate because adapter is trivial — just a function call).

---

## Follow-up #6 — C14 room_metadata_by_signature builder ✅ CLOSED (S57)

**Closed:** S57 (2026-05-17). New module `orchestration/adapters/c12_c13_to_c14.py` ships `build_room_metadata_by_signature(*, c12_payload, c13_payload)`:

- Indexes C12 placed candidates by `source_refined_candidate_signature` for O(1) lookup.
- For each C13 `SuccessfulDoorPlacement`, derives the main-entry room from the door with `is_main_entry=True` (handles `EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID` on either endpoint; falls back to `room_a` for degenerate internal-to-internal main entries per Inv E7 deterministic tiebreak).
- Builds `RoomMetadata(room_id, category, is_main_entry_room)` per placed room, sourcing categories from `PlacedRoom.category` (which passes through from C12's category-passthrough of C9 sizing).
- Skips C13 signatures missing from C12 — C14 then surfaces those as `GraphInconsistencyError` under STRICT (intentional error surface).

**Orchestrator wiring:** `_run_c14_connection_graph(c12_payload, c13_payload)` calls `analyze_circulation_batch(batch=c13_payload, room_metadata_by_signature=metadata, config=CirculationConfig(), strict_mode=False)`. Phase ships OK when the call returns a `CirculationAnalysisBatchResult`.

**Tests added:** `tests/test_orchestration/test_c14_metadata_builder.py` (8 unit tests covering main-entry derivation edge cases + builder routing) + 2 new smoke tests.

**Effort actual:** ~1h (within the 1-1.5h estimate).

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

**Priority order for S58+ (recommendation):**
1. #8 C16 UpstreamInputBundle (3-4h) — produces actual drawings the architect can review. Highest visibility, gates B-238 feedback loop.
2. #7 C15 (C12, C13, C14) triples (1-1.5h) — easy win now that all three upstream phases ship OK.
3. #9 C17 separate flow (3-4h) — depends on UI work for quote upload.
4. #10 C3a/C3b integration (2-3h) — design decision needed.
5. #11 / #12 / #13 / #14 — input contract + serialization + corpus + UI work.

**Critical path:** B-238 architect feedback may reshape priorities — the architect may want to see drawings (#8) before refinement quality (#3). Defer prioritization decisions until architect feedback lands.

---

## Closing record

| Item | Status |
|---|---|
| MVP orchestrator shipped | ✅ S56 |
| 22 orchestration tests passing | ✅ S56 |
| Full test sweep: 4,350 / 0 / 31 | ✅ S56 |
| Follow-ups doc | ✅ S56 (this file) |
| **#4 C12 adapter (C11b RefinedCandidate + C11a fallback)** | **✅ S57 (2026-05-17)** |
| **#5 C13 adapter (place_doors wiring)** | **✅ S57 (2026-05-17)** |
| **#6 C14 metadata builder (room_metadata_by_signature)** | **✅ S57 (2026-05-17)** |
| **#1 C7 full StructuralGridEngine wiring** | **✅ S57 (2026-05-17, extended)** |
| **#2 C11a M0-M9 full operator suite (opt-in)** | **✅ S57 (2026-05-17, extended)** |
| **#3 Real C11b EvaluatorProtocol + brief shim (opt-in)** | **✅ S57 (2026-05-17, extended)** |
| **Full test sweep: 4,386 / 0 / 31** | **✅ S57 extended** |
| **#7 C15 (C12,C13,C14) triples + ProblemAnalysisMetadata** | **✅ S59 (2026-05-18)** |
| **#8 C16 UpstreamInputBundle assembly + render_drawings_batch** | **✅ S59 (2026-05-18)** |
| **#9 C17 separate `/api/quote/compare` flow** | **✅ S59 (2026-05-18)** |
| **#10 C3a/C3b integration (async-flags mode)** | **✅ S59 (2026-05-18)** |
| **#11 Free-form Plot + FloorRoomBrief input contract** | **✅ S59 (2026-05-18)** |
| **#12 Phase-payload JSON serialization** | **✅ S59 (2026-05-18)** |
| **#13 Comprehensive fixture corpus** | **✅ S59 (2026-05-18)** |
| **#14 UI: `/orchestrator_run.html` + `/quote_compare.html`** | **✅ S59 (2026-05-18)** |
| **ALL 14 follow-ups closed; PIPELINE_PHASES now 18 with c03a** | **✅ S59 (2026-05-18)** |
