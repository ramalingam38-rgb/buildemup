# 🚨 NEXT CLAUDE — START HERE — S57 OPEN

**Authored:** Ramalingam + Claude, S56 close, May 16, 2026
**Session state:** S56 was a **3-phase mega-session**: (1) B-238 architect engagement packet shipped (10 docs); (2) Bucket C fully emptied (13 items closed); (3) **MVP Master Orchestrator shipped** (`buildemup/orchestration/` + `/api/orchestrate` HTTP endpoint + 22 new tests passing). **Test sweep: 4,350 passed / 0 failed / 31 skipped.**

**Critical for S57:** **READ `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` FIRST.** That doc carries the explicit punch list for advancing the orchestrator from MVP → production-quality. 14 follow-up items totaling ~25-30 hours (6-8 sessions).

**Buckets state:** Bucket A has 2 calendar-bound items (B-220, B-238); Bucket B = 0; Bucket C = 0; Bucket D = 28 (intentionally v2-deferred). **The only open work is: B-238 architect outreach (calendar-bound), B-220 plumbing engineer (calendar-bound), the 14 orchestrator follow-ups, and the deferred v1+ roadmap (Option C).**

**Your task:** Read this file. Then read `S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md`. Then read `S56_SESSION_LOG.md`. Then await Ramalingam's S57 direction.

---

## 🎯 What S56 accomplished (three phases)

### Phase 1 — B-238 architect engagement packet (10 docs)
`04_backlog/B238_architect_engagement_packet_S56/` — sourcing channels, screening criteria, 5 outreach email templates, scope contract, ₹15-40K compensation structure, briefing pack, **30 structured review questions tied to S55 LOCK closures**, NDA template, 7-step feedback intake protocol. Ready for Ramalingam to drive outreach.

### Phase 2 — Bucket C emptied (13 items)
| # | Item | Resolution |
|---|---|---|
| 1 | B-S53-PROVISIONAL-CLEANUP | Deleted `c10/__init__.PROVISIONAL_S53.py` + README cleanup |
| 2 | B-060 | Docstring typo "7 files"→"8 files" in `tests/e2e/__init__.py` |
| 3 | B-099 | Vastu FULL tier hidden in `brief_form.html` w/ v1.1 restore breadcrumb |
| 4 | B-057 | Visible trace_id chip on `case.html` success render |
| 5 | B-059 | Dedicated `PER_CASE_LIMIT_REACHED` message in `done.js` |
| 6 | B-241 | New `scripts/wall_segments_lint_check.py` — UTF-8-safe, allowlisted, runs clean |
| 7 | B-S53-C7-LEGACY-DECISION | **KEEP** — c07_structural_grid.py IS the canonical orchestrator |
| 8 | B-S53-C2-SPEC-MOVE | Moved 2 C1 SPEC drafts from `docs/component1/` to `02_specs_chronological/` |
| 9 | B-015 + B-021 + B-056 | New `C3a_v0_2_1b_AMENDMENT_LOCKED.md` (additive amendment, parent untouched) |
| 10 | B-245 | New `01_master_doc/RULE_11_MATURITY_WEIGHTED_SCORING_S56.md` |
| 11 | B-S53-TEST-DIRS-MISSING | Deduplicated C10 (-140 wasted runs) + moved C9/C5/C8 stragglers to per-component dirs |
| 12 | B-S53-C1-CONSOLIDATE | **KEEP** — mirrors C7 layout (top-level orchestrator + sub-package) |

### Phase 3 — MVP Master Orchestrator + HTTP endpoint
New package `06_upstream_codebase/buildemup/orchestration/`:
- `MasterOrchestrator` class with `.run(...)` method walks all 17 phases
- `MasterOrchestratorConfig` (vastu_tier, max_topology_mutations, enable_c11b_refinement, halt_on_first_failure)
- `MasterOrchestratorResult` with `.phase(id)` lookup + `.summary()`
- `PhaseResult` + `PhaseStatus` (OK / ERROR / SKIPPED / STUB)
- `PIPELINE_PHASES` canonical 17-entry tuple

**Phase status at MVP:**

| Phase | Status | What runs |
|---|---|---|
| `c01_brief` / `c02_feasibility` | SKIPPED (no full Brief) or OK | Real call to `run_feasibility` if full_brief passed |
| `c04_plot_analysis` through `c11a_topology_mutation` | OK | Real chained calls via existing component entry points |
| `c11b_nsga_refinement` | STUB | Real call to `run_local_refinement` with `StubEvaluator`; `BatchAllTopologiesFailedError` caught + converted to STUB |
| `c12_vertical_placement` through `c17_quote_comparison` | STUB | Stub-status with explicit `stub_reason` + breadcrumb to follow-ups doc |

**HTTP endpoint:** `POST /api/orchestrate` — accepts `{plot_fixture, brief_fixture, config}`, returns per-phase status JSON (payloads not yet serialized — see follow-up #12).

**Tests:** 22 new (14 smoke + 8 endpoint), all passing. Full sweep: **4,350 / 0 / 31**.

---

## 📌 S57 must-do list — do NOT lose any of these

Per user direction "keep record of what you are doing and what should be done in later sessions ok. i dont want to miss anything":

### Calendar-bound (Ramalingam-driven; Claude cannot do alone)
1. **B-238 architect outreach** — packet ready at `04_backlog/B238_architect_engagement_packet_S56/`. Ramalingam builds longlist (3-4h), sends outreach emails (1 day), awaits replies (1-2 weeks).
2. **B-220 plumbing engineer outreach** — separate engagement. Packet not yet built; clone B-238 structure when ready.

### Orchestrator advancement (14 explicit items — see `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md`)
Priority order if budget is one session:
- **#5 C13 adapter** (~1h) — `_run_c13_doors` real implementation
- **#6 C14 metadata builder** (~1.5h) — `room_metadata_by_signature` construction
- **#4 C12 adapter** (~2-3h) — C11b → SingleFloorPlacementInput; gates #5/#6/#7/#8
- **#3 Real C11b EvaluatorProtocol** (~4-6h) — biggest single piece; can be deferred if downstream chain (#4-#8) is the priority
- **#8 C16 UpstreamInputBundle** (~3-4h) — produces actual drawings; high architect-visibility value
- **#9 C17 separate quote flow** (~3-4h) — separate endpoint, not strictly downstream
- **#1 C7 full StructuralGridEngine** (~1-2h)
- **#2 C11a M1-M9 operators** (~30min)
- **#7 C15 triples** (~1-1.5h)
- **#10 C3a/C3b integration** (~2-3h) — design decision needed
- **#11 Free-form input contract** (~3-4h)
- **#12 Phase-payload JSON serialization** (~2h)
- **#13 Scenario fixture corpus** (~session)
- **#14 UI to surface orchestrator results** (~session)

### Documentation deliverable (user-deferred since S54)
- **Detailed v1+ roadmap (Option C)** — completed / remaining / improvements / missing soul-modules (3D, interior, full CAD pack, municipal submission, construction-phase help, engineer-fee breakout). Best authored after B-238 feedback lands so "what's missing" reflects architect-validated reality.

### Pre-existing back-pocket
- **B-NEW-PUNE-SOIL-SCENARIO-REFRESH** — Pune soil S05/S17 scenarios currently excluded with breadcrumb (KB has STIFF_CLAY, scenarios expect BLACK_COTTON). Either re-author scenarios OR refresh KB after B-238.
- **Trivial new finding S56:** `api/brief_endpoint.py:664` uses `datetime.utcfromtimestamp()` (Python 3.14+ deprecation). 1,421 warnings/sweep. Trivial inline fix.

---

## ⚠️ Critical landmines for the next Claude

### Landmine 1 — `4,350` is the NEW expected test count (was 4,328 after S56 phase 2, was 4,468 at S55 close)
- S55 → S56 phase 2 dropped by 140 (removed wasted C10 duplicates) → 4,328
- S56 phase 2 → S56 phase 3 added 22 (orchestration tests) → 4,350
- Don't think the changes are regressions; they're tracked.

### Landmine 2 — C11b in orchestrator is STUB, not OK
The orchestrator calls C11b's real `run_local_refinement()` with the built-in `StubEvaluator`. NSGA convergence fails (BatchAllTopologiesFailedError), which is caught and converted to STUB status. **To flip C11b to OK, follow-up #3 ships a real `EvaluatorProtocol` implementation** (`buildemup/orchestration/evaluators.py`). Do NOT try to "fix" the StubEvaluator — it's working as designed.

### Landmine 3 — C12-C17 are NOT yet real chained calls
They appear in `PIPELINE_PHASES` and produce `PhaseResult` entries, but `_stub_phase()` is called instead of real component functions. **Each requires upstream-adapter glue** (see follow-ups #4 through #9). The contracts are typed but non-trivial.

### Landmine 4 — Orchestrator endpoint uses FIXTURE inputs, not free-form
`POST /api/orchestrate` only accepts `{plot_fixture: "bangalore_40x60", ...}` — named test fixtures. Production callers need free-form Plot + Brief input (follow-up #11). This is intentional MVP scope.

### Landmine 5 — Phase payloads NOT serialized in HTTP response
The endpoint returns per-phase status + metadata only. The actual phase outputs (PlotAnalysis dataclass, candidate tuples, etc.) are NOT in the JSON. Follow-up #12 handles this.

### Landmine 6 — LOCKED specs remain immutable
S56 closed B-015/B-021/B-056 by authoring a NEW `C3a_v0_2_1b_AMENDMENT_LOCKED.md` next to the parent. The parent's LOCKED text is unchanged. **Do the same for future B-238 architect findings**: don't edit `_v0_2_1a_LOCKED.md` in place.

### Landmine 7 — Run pytest from `06_upstream_codebase/buildemup/` (inside the package)
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\modest-yonath-ebe465\06_upstream_codebase\buildemup"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" -m pytest tests -q
```
Running from `06_upstream_codebase/` triggers `ModuleNotFoundError: No module named 'tests'`.

### Landmine 8 — Frontend changes need server restart
brief_form.html / case.js / done.js cache as static. Hard refresh isn't enough.

### Landmine 9 — Inherited landmines (still apply)
`c01_brief_capture.py` + `c01/` are complementary (not duplicates), same for C7. `rendered_explain` vs `combined_rendered_explain`. GitHub repo is PRIVATE. User is non-engineer. Vastu FULL is hidden (B-099), not removed.

---

## ✅ How to verify project state on your own machine

**Smoke test the orchestrator (~5 sec):**
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\modest-yonath-ebe465\06_upstream_codebase\buildemup"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" -m pytest tests/test_orchestration -q
```
Expected: 22 passed.

**B-241 lint:**
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\modest-yonath-ebe465"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" scripts\wall_segments_lint_check.py
```
Expected: PASS.

**Full sweep (~2 min):** **4,350 passed / 0 failed / 31 skipped.**
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\modest-yonath-ebe465\06_upstream_codebase\buildemup"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" -m pytest tests -q
```

**Live server with orchestrator endpoint:**
```powershell
cd "C:\Buildemup Full 17 components complete\06_upstream_codebase"
.\venv\Scripts\Activate.ps1
python -m buildemup.api.server
```
Then `curl -X POST -d '{}' http://localhost:8000/api/orchestrate` returns 17-phase JSON status.

---

## 🛣️ Recommended directions for S57

### Option A (RECOMMENDED) — Launch B-238 outreach + orchestrator follow-ups in parallel

The B-238 packet is ready and the orchestrator is shipped. Ramalingam should launch outreach this week (calendar-bound). Claude can work the orchestrator follow-ups in parallel:
- **S57 session:** close follow-ups #5 (C13 adapter, 1h) + #6 (C14 metadata, 1.5h) + #4 (C12 adapter, 2-3h) = ~5h of focused work. Result: C12+C13+C14 all flip from STUB → OK.
- **S58:** follow-up #8 (C16 UpstreamInputBundle, 3-4h) — produces actual drawings. High architect-visibility.
- **S59+:** real C11b evaluator + remaining follow-ups + scenario corpus + UI.

### Option B — Detailed v1+ roadmap (Option C from S55)
With the MVP orchestrator now demonstrating end-to-end pipeline, the v1+ roadmap can be authored with concrete reference points (vs. theoretical). User-flagged for memory. Best done after B-238 feedback lands, but can start now with "subject to architect refinement" markers.

### Option C — Pure architect-feedback wait
Pause Claude work; focus on outreach. Return when feedback lands. Lowest churn.

### Option D — B-220 plumbing engineer engagement
Clone B-238 packet structure for B-220. Calendar-bound. Same 3-5 week timeline.

**My recommendation:** Option A. Three follow-ups in one S57 session advance the orchestrator significantly while Ramalingam runs B-238 outreach. By the time B-238 feedback lands (~3 weeks), the orchestrator will likely have C12-C16 all flipped to OK, and the architect can see real drawings.

---

## 📁 Where everything is

| What | Where |
|---|---|
| This document | `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` (you're reading) |
| **S57 orchestrator follow-ups (READ FIRST)** | `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` |
| S56 session log | `00_START_HERE/S56_SESSION_LOG.md` |
| B-238 architect packet | `04_backlog/B238_architect_engagement_packet_S56/00_README.md` |
| Bucket C deferral rationale (historical; items now closed) | `04_backlog/S56_BUCKET_C_DEFERRALS.md` |
| Master Orchestrator package | `06_upstream_codebase/buildemup/orchestration/` |
| Orchestrator HTTP endpoint | `06_upstream_codebase/buildemup/api/orchestrate_endpoint.py` |
| Orchestrator tests | `06_upstream_codebase/buildemup/tests/test_orchestration/` |
| New C3a amendment (S56) | `02_specs_chronological/C3a_v0_2_1a_LOCKED/buildemup_C3a_SPEC_v0_2_1b_AMENDMENT_LOCKED.md` |
| Rule 11 maturity scoring (S56) | `01_master_doc/RULE_11_MATURITY_WEIGHTED_SCORING_S56.md` |
| Backlog triage with 4 buckets | `04_backlog/S54_BACKLOG_TRIAGE.md` (B and C now empty) |
| Master doc latest | `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md` |
| GitHub remote | `https://github.com/ramalingam38-rgb/buildemup` (PRIVATE) |
| Memory (auto-loaded) | `~\.claude\projects\C--Buildemup-Full-17-components-complete\memory\` |

---

## 🧠 Memory state at S56 close

Three memory files exist; new Claude reads them automatically:

1. `user_ramalingam.md` — who Ramalingam is, working style, origin story
2. `project_buildease_state_and_deferred_tasks.md` — **needs update at S57 open** to reflect orchestrator-shipped state and 14 follow-up items
3. `feedback_session_handoff_log.md` — preference: maintain session log + finalize as handoff

If memory shows different content than this handoff, **trust the handoff** (it's more recent).

---

## 🎓 Project context (one paragraph for fresh sessions)

BuildemUp† (placeholder name; future "BuildEase") is a decision-support engine for Indian families building their own home. The product exists to close information asymmetry between homeowners and contractors/architects/engineers — particularly making material cost, engineer fees, labour, contractor margin, and timeline all visible separately. 17 components: C1 brief → C2 feasibility → C3a/C3b negotiation → C4 plot analysis → C5 topology → C6 orientation → C7 structural grid → C8 corridor → C9 room sizer → C10 wet zones → C11a/b topology mutation + NSGA-II → C12 vertical alignment → C13 doors → C14 connection graph → C15 problem finder → C16 dual drawings → C17 quote comparison. **At S56 close, the MVP master orchestrator wires all 17 phases end-to-end** (C4-C11a real chain, C11b STUB on StubEvaluator, C12-C17 STUB with explicit S57 follow-ups). Soul-complete v1 also requires 3D, interior design, full CAD pack for construction, municipal submission, construction-phase help — none of which exist yet.

†= placeholder name marker. Final product name TBD ("BuildEase" preferred; "Archimind" is taken).

**Welcome to S57. Read `S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` first, then this file, then `S56_SESSION_LOG.md`. Then await Ramalingam's direction.**
