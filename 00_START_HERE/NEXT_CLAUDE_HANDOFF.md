# 🚨 NEXT CLAUDE — START HERE — S58 OPEN

**Authored:** Ramalingam + Claude, S57 close, May 17, 2026
**Session state:** S57 was an **extended two-part session** that closed SIX orchestrator follow-ups: **#4 (C12 adapter)**, **#5 (C13 adapter)**, **#6 (C14 metadata builder)** [Part A]; then **#1 (C7 full StructuralGridEngine)**, **#2 (C11a M0-M9 operators)**, **#3 (real C11b EvaluatorProtocol + brief shim)** [extension per user direction "finish first three pending items"]. **Test sweep: 4,386 passed / 0 failed / 31 skipped** (up from 4,350 at S56 close; +36 new tests). C11b now ships OK with the real evaluator → C12 activates the documented primary RefinedCandidate adapter path.

**Critical for S58:** **READ `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` FIRST.** That doc carries the explicit punch list. **8 follow-ups remain** (was 14 at S57 open; #1/#2/#3/#4/#5/#6 ✅ CLOSED). Next-priority recommendations are in the doc's revised priority section.

**Buckets state:** Bucket A has 2 calendar-bound items (B-220, B-238); Bucket B = 0; Bucket C = 0; Bucket D = 28 (intentionally v2-deferred). **The only open work is: B-238 architect outreach (calendar-bound), B-220 plumbing engineer (calendar-bound), the 11 remaining orchestrator follow-ups, and the deferred v1+ roadmap (Option C).**

**Your task:** Read this file. Then read `S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md`. Then read `S57_SESSION_LOG.md`. Then await Ramalingam's S58 direction.

---

## 🎯 What S57 accomplished

S57 was a single-session orchestrator-advance: close follow-ups #4, #5, #6 so the master orchestrator runs C4 → C14 as a real chain end-to-end.

### New package: `06_upstream_codebase/buildemup/orchestration/adapters/`
- `__init__.py` — re-exports
- `c11b_to_c12.py` — C11b RefinedCandidate (primary) + C11a MutatedTopologyCandidate (fallback) adapters + dispatcher
- `c12_c13_to_c14.py` — `build_room_metadata_by_signature` builder

### Orchestrator changes
- `_run_c12_vertical_placement` replaces the C12 stub. Uses RefinedCandidate path if C11b ships OK, else falls back to C11a path.
- `_run_c13_doors` replaces the C13 stub. Calls `place_doors(placed_candidates=c12_payload.placed_candidates, config=DoorPlacementConfig(strict_mode=False), c12_cache_key=c12_payload.cache_key)`.
- `_run_c14_connection_graph` replaces the C14 stub. Builds metadata via the new adapter; calls `analyze_circulation_batch`.

### Tests
- New: `test_c12_adapter.py` (7 tests), `test_c14_metadata_builder.py` (8 tests)
- Modified: smoke + endpoint tests narrowed (stub-assertion now covers c15-c17 only)
- 22 → 40 orchestrator tests
- Full sweep: 4,350 → **4,368**

**Phase status at S57 close:**

| Phase | Default status | Notes |
|---|---|---|
| `c01_brief` / `c02_feasibility` | SKIPPED or OK | Same as S56 |
| `c04_plot_analysis` → `c06_orientation` | OK | Same as S56 |
| **`c07_structural_grid`** | **OK (full engine, S57)** | Default `enable_full_structural_engine=True` runs StructuralGridEngine → grid + structure + foundation + cost. Toggle False for MVP-compat |
| `c08_corridor` → `c10_wet_zones` | OK | Same as S56 |
| **`c11a_topology_mutation`** | **OK (S57)** | Default M0_BASE only; opt-in `enable_full_mutation_operators=True` adds M1-M9 |
| **`c11b_nsga_refinement`** | **STUB by default; OK opt-in (S57)** | Default uses StubEvaluator → STUB. Set `use_real_c11b_evaluator=True` to use MultiObjectiveEvaluator + brief shim → C11b ships OK, NSGA produces ~60 RefinedCandidates |
| **`c12_vertical_placement`** | **OK (S57)** | Real `place_and_align`. Primary RefinedCandidate path activates when C11b OK; C11a fallback when C11b STUB |
| **`c13_doors`** | **OK (S57)** | Real `place_doors` call piping C12 placements |
| **`c14_connection_graph`** | **OK (S57)** | Real `analyze_circulation_batch` call |
| `c15_problem_finder` → `c17_quote_comparison` | STUB | Awaits follow-ups #7 / #8 / #9 |

---

## 📌 S58 must-do list — do NOT lose any of these

Per user direction "keep record of what you are doing and what should be done in later sessions ok. i dont want to miss anything":

### Calendar-bound (Ramalingam-driven; Claude cannot do alone)
1. **B-238 architect outreach** — packet ready at `04_backlog/B238_architect_engagement_packet_S56/`. Ramalingam builds longlist (3-4h), sends outreach emails (1 day), awaits replies (1-2 weeks).
2. **B-220 plumbing engineer outreach** — separate engagement. Packet not yet built; clone B-238 structure when ready.

### Orchestrator advancement (8 remaining items — see `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md`)
Revised priority order:
- **#8 C16 UpstreamInputBundle** (~3-4h) — produces actual drawings the architect can review. Highest visibility, gates B-238 feedback loop.
- **#7 C15 (C12, C13, C14) triples** (~1-1.5h) — easy win now that all three upstream phases ship OK.
- **#9 C17 separate flow** (~3-4h) — depends on UI work
- **#10 C3a/C3b integration** (~2-3h) — design decision needed
- **#11 Free-form input contract** (~3-4h)
- **#12 Phase-payload JSON serialization** (~2h)
- **#13 Scenario fixture corpus** (~session)
- **#14 UI to surface orchestrator results** (~session)

### Documentation deliverable (user-deferred since S54)
- **Detailed v1+ roadmap (Option C)** — completed / remaining / improvements / missing soul-modules (3D, interior, full CAD pack, municipal submission, construction-phase help, engineer-fee breakout). Best authored after B-238 feedback lands so "what's missing" reflects architect-validated reality.

### Pre-existing back-pocket
- **B-NEW-PUNE-SOIL-SCENARIO-REFRESH** — Pune soil S05/S17 scenarios currently excluded with breadcrumb (KB has STIFF_CLAY, scenarios expect BLACK_COTTON). Either re-author scenarios OR refresh KB after B-238.
- **Trivial finding S56 (still open):** `api/brief_endpoint.py:664` uses `datetime.utcfromtimestamp()` (Python 3.14+ deprecation). 1,421 warnings/sweep. Trivial inline fix.

---

## ⚠️ Critical landmines for the next Claude

### Landmine 1 — `4,386` is the new expected test count (was 4,350 at S56)
- S55 → S56 phase 2 dropped by 140 (removed wasted C10 duplicates) → 4,328
- S56 phase 2 → S56 phase 3 added 22 (orchestration tests) → 4,350
- S56 → S57 Part A added 18 (C12/C13/C14 adapter tests) → 4,368
- **S57 Part A → S57 extended added 18 (C7 full + C11a opt-in + C11b real evaluator tests) → 4,386**
- Don't think the changes are regressions; they're tracked.

### Landmine 2 — C11b is STUB BY DEFAULT but OK is now reachable
S57 #3 closed: setting `MasterOrchestratorConfig(use_real_c11b_evaluator=True)` flips C11b to OK. **Default stays False** (StubEvaluator → STUB) so the deterministic smoke tests don't change. When True, C12 auto-routes to the documented primary `adapt_refined_to_single_floor` path via the dispatcher — no orchestrator code change needed.

**Critical context for #3:** The follow-up doc only described an evaluator change, but C11b's pre-existing `_extract_requirements_and_envelope` was broken on the canonical FloorRoomBrief (zero requirements extracted → NSGA produced zero candidates). S57 also ships `C11bBriefShim` + `build_c11b_brief_shim_from_upstream` in `orchestration/evaluators.py` to bridge the contract gap. Without the shim, the real evaluator alone doesn't flip C11b to OK.

### Landmine 3 — C15-C17 are STILL STUB
S57 closed #1/#2/#3/#4/#5/#6. C15 (#7), C16 (#8), C17 (#9) remain STUB. **#7 is the easiest next-step** now that C12+C13+C14 all ship OK — just builds (C12, C13, C14) triples and threads through `analyze_problems_batch`.

### Landmine 4 — C12 sparse-edge problem (working as designed)
C12's slicing-tree often produces 0 shared edges for multi-room layouts in the smoke fixture (per the C13 adversarial integration corpus comments — filed `B-C12-EDGE-DENSITY` post-LOCK). C13 then produces 0 successful placements; C14 then has empty metadata. **This is all working as designed.** Phases ship OK regardless because the orchestrator's "OK = call succeeded" semantics match the architecture's intentional decoupling. **Do not** try to "fix" this in the orchestrator; the fix is in C12's placement algorithm tracked separately.

### Landmine 5 — Orchestrator endpoint still uses FIXTURE inputs, not free-form
`POST /api/orchestrate` only accepts `{plot_fixture: "bangalore_40x60", ...}` — named test fixtures. Production callers need free-form Plot + Brief input (follow-up #11). This is still MVP scope.

### Landmine 6 — Phase payloads still NOT serialized in HTTP response
The endpoint returns per-phase status + metadata only. The actual phase outputs (PlotAnalysis dataclass, candidate tuples, PlacementBatchResult, etc.) are NOT in the JSON. Follow-up #12 still pending.

### Landmine 7 — LOCKED specs remain immutable
S56 set the precedent: closed B-015/B-021/B-056 by authoring a NEW `C3a_v0_2_1b_AMENDMENT_LOCKED.md` next to the parent. Same pattern applies for future B-238 architect findings: don't edit `_v0_2_1a_LOCKED.md` in place.

### Landmine 8 — Run pytest from `06_upstream_codebase/buildemup/` (inside the package)
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\distracted-newton-d8ec13\06_upstream_codebase\buildemup"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" -m pytest tests -q
```
The worktree path will differ in S58; substitute the active worktree name.

### Landmine 9 — Frontend changes need server restart
brief_form.html / case.js / done.js cache as static. Hard refresh isn't enough.

### Landmine 10 — Inherited landmines (still apply)
`c01_brief_capture.py` + `c01/` are complementary (not duplicates), same for C7. `rendered_explain` vs `combined_rendered_explain`. GitHub repo is PRIVATE. User is non-engineer. Vastu FULL is hidden (B-099), not removed.

---

## ✅ How to verify project state on your own machine

**Smoke test the orchestrator (~3-4 min — slow because real-evaluator tests run actual NSGA):**
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\distracted-newton-d8ec13\06_upstream_codebase\buildemup"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" -m pytest tests/test_orchestration -q
```
Expected: **58 passed**.

**B-241 lint:**
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\distracted-newton-d8ec13"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" scripts\wall_segments_lint_check.py
```
Expected: PASS.

**Full sweep (~5-6 min — slower than S56 because of real-NSGA tests):** **4,386 passed / 0 failed / 31 skipped.**
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\distracted-newton-d8ec13\06_upstream_codebase\buildemup"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" -m pytest tests -q
```

**Live server with orchestrator endpoint:**
```powershell
cd "C:\Buildemup Full 17 components complete\06_upstream_codebase"
.\venv\Scripts\Activate.ps1
python -m buildemup.api.server
```
Then `curl -X POST -d '{}' http://localhost:8000/api/orchestrate` returns 17-phase JSON status; c12/c13/c14 should now show "status": "ok".

---

## 🛣️ Recommended directions for S58

### Option A (RECOMMENDED) — Close #8 (C16 drawings) so architect has something visual to review
The B-238 packet is in Ramalingam's hands; outreach is calendar-bound. Architect's first ask will likely be "show me drawings." Follow-up #8 (UpstreamInputBundle assembly + render_drawings_batch wiring) produces those. ~3-4 hours; high visibility value. After #8 lands, C15 (#7) is trivial to add on top.

### Option B — Close #7 (C15 triples) first, then #8
C15 is the easiest follow-up to add now that C12+C13+C14 all ship OK. ~1.5h. After C15, all five chained phases (C12-C16) become trivial to wire end-to-end.

### Option C — Real C11b evaluator (#3, ~4-6h)
Flips C12's primary path on. Higher refinement quality, but the architect doesn't see this directly — it's behind-the-scenes optimization. Lower B-238 visibility than #8 or #7.

### Option D — Detailed v1+ roadmap (Option C from S55)
Still deferred per user direction; best done AFTER B-238 feedback lands.

### Option E — Pure architect-feedback wait
Pause Claude work; focus on outreach. Return when feedback lands. Lowest churn.

**My recommendation:** Option A. Drawings are what architects evaluate first; everything else is internal-to-the-engine.

---

## 📁 Where everything is

| What | Where |
|---|---|
| This document | `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` (you're reading) |
| **S57 orchestrator follow-ups (READ FIRST; #4/#5/#6 closed)** | `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` |
| S57 session log | `00_START_HERE/S57_SESSION_LOG.md` |
| S56 session log | `00_START_HERE/S56_SESSION_LOG.md` |
| B-238 architect packet | `04_backlog/B238_architect_engagement_packet_S56/00_README.md` |
| Master Orchestrator package | `06_upstream_codebase/buildemup/orchestration/` |
| **Orchestrator adapter glue (S57)** | `06_upstream_codebase/buildemup/orchestration/adapters/` |
| **Orchestrator evaluators (S57 #3)** | `06_upstream_codebase/buildemup/orchestration/evaluators.py` |
| Orchestrator HTTP endpoint | `06_upstream_codebase/buildemup/api/orchestrate_endpoint.py` |
| Orchestrator tests | `06_upstream_codebase/buildemup/tests/test_orchestration/` |
| C3a amendment (S56) | `02_specs_chronological/C3a_v0_2_1a_LOCKED/buildemup_C3a_SPEC_v0_2_1b_AMENDMENT_LOCKED.md` |
| Rule 11 maturity scoring (S56) | `01_master_doc/RULE_11_MATURITY_WEIGHTED_SCORING_S56.md` |
| Backlog triage with 4 buckets | `04_backlog/S54_BACKLOG_TRIAGE.md` (B and C empty) |
| Master doc latest | `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md` |
| GitHub remote | `https://github.com/ramalingam38-rgb/buildemup` (PRIVATE) |
| Memory (auto-loaded) | `~\.claude\projects\C--Buildemup-Full-17-components-complete\memory\` |

---

## 🧠 Memory state at S57 close

Memory file `project_buildease_state_and_deferred_tasks.md` updated at S57 close to reflect: orchestrator now runs C4 → C14 end-to-end with full C7 engine + opt-in real C11b evaluator; 8 follow-ups remain; test baseline 4,386.

If memory shows different content than this handoff, **trust the handoff** (it's more recent).

---

## 🎓 Project context (one paragraph for fresh sessions)

BuildemUp† (placeholder name; future "BuildEase") is a decision-support engine for Indian families building their own home. The product exists to close information asymmetry between homeowners and contractors/architects/engineers — particularly making material cost, engineer fees, labour, contractor margin, and timeline all visible separately. 17 components: C1 brief → C2 feasibility → C3a/C3b negotiation → C4 plot analysis → C5 topology → C6 orientation → C7 structural grid → C8 corridor → C9 room sizer → C10 wet zones → C11a/b topology mutation + NSGA-II → C12 vertical alignment → C13 doors → C14 connection graph → C15 problem finder → C16 dual drawings → C17 quote comparison. **At S57 close, the master orchestrator runs C4 → C14 as a real chain end-to-end with full C7 structural sizing + foundation + cost** (C11b STUB by default, OK opt-in via real evaluator + brief shim; C12 auto-routes to primary RefinedCandidate path when C11b OK; C15-C17 STUB with explicit S58+ follow-ups). Soul-complete v1 also requires 3D, interior design, full CAD pack for construction, municipal submission, construction-phase help — none of which exist yet.

†= placeholder name marker. Final product name TBD ("BuildEase" preferred; "Archimind" is taken).

**Welcome to S58. Read `S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` first, then this file, then `S57_SESSION_LOG.md`. Then await Ramalingam's direction.**
