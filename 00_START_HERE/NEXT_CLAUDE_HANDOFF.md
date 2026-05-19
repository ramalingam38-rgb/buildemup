# 🚨 NEXT CLAUDE — START HERE — S60 OPEN

**Authored:** Ramalingam + Claude, S59 close, May 18, 2026
**Session state:** S59 was a **single-session push** that closed the LAST 8 orchestrator follow-ups: **#7 (C15 triples) + #8 (C16 drawings) + #9 (C17 quote endpoint) + #10 (C3a/C3b async-flags) + #11 (free-form input) + #12 (payload serialization) + #13 (scenario corpus) + #14 (UI)**. **0 follow-ups remain.** The master orchestrator now runs end-to-end with C15+C16 OK, C17 routed to a separate endpoint, and a clickable browser UI that renders SVG floorplans.

**Critical for S60:** **READ `00_START_HERE/S59_SESSION_LOG.md` FIRST.** That's the complete S59 record + landmines + what was deferred.

**The only remaining open work is:**
- B-238 architect outreach (calendar-bound, Ramalingam-driven; packet ready since S56; UI now ready for click-through).
- B-220 plumbing engineer outreach (calendar-bound; packet not yet built).
- Component-level bugs surfaced by the S59 scenario corpus — **all now graceful-STUB-degraded at the orchestrator level (S59 extended).** Underlying component fixes (B-107 C6, B-C8, B-C9, B-C10, B-C12) remain open as architect-amendment work, but the pipeline never crashes on them.
- v1+ roadmap doc (deferred per user direction until B-238 feedback lands).

**S59 extended close (2026-05-19):** Test baseline grew to **4,422 passed / 0 failed / 31 skipped**. C11b flake fixed via `init_max_retries=500` in the orchestrator's real-evaluator path; the 5 scenario-corpus bugs now uniformly STUB-degrade at the orchestrator instead of ERROR-cascading.

**S59 extended pt 2 close (2026-05-19):** Spec-amendment pass.
- **C8 v1.1 AMENDMENT LOCKED** — COURTYARD arm corner-trim. **Genuine algorithm fix**; Delhi+large now ships C8 OK (no longer STUB).
- **C10 v1.1 AMENDMENT LOCKED** — Phase 3 relaxation pass (opt-in-default). Doesn't unblock Mumbai/Hyderabad (binding constraint is 3m riser spacing on small plot, plumbing-engineer territory) but unblocks future "tight-but-fixable" cases.
- **C9 stub_reason enrichment** — surfaces actual Inv 9 deficit ("brief exceeds plot by X m²") in the orchestrator response.
- **B-107 DEFERRAL MEMO** — vastu intercardinal extension needs vastu-expert review.
- **B-C12 DEFERRAL MEMO** — slicing-tree shared-edge density redesign needs architect review.
- Scenario suite went from 1 happy + 5 known-broken → 4 happy + 4 known-broken.

**Test sweep target: 4,422 passed.** (Verified post-amendment; no regression.)

**Your task:** Read this file. Then read `S59_SESSION_LOG.md`. Then await Ramalingam's S60 direction.

---

## 🎯 What S59 accomplished

Single-session orchestrator-advance push: close all 8 remaining follow-ups so an architect can click through the full pipeline before the B-238 engagement.

### New architecture surfaces
- **`POST /api/quote/compare`** — separate C17 endpoint. Accepts JSON parsed_quote + cost_lines; auto-computes the signature; returns matched lines / gaps / signals / signatures.
- **`POST /api/orchestrate` (extended)** — now accepts free-form `plot` + `brief` JSON (mirrors `/api/brief/capture` shape), supports `include_payloads=true` to serialize every phase payload, and full config knobs (`enable_full_structural_engine`, `enable_full_mutation_operators`, `use_real_c11b_evaluator`).
- **`GET /orchestrator_run.html`** — Tailwind-CDN form: pick fixture, run, see per-phase chips + C3a flags + inline SVG floorplans rendered from C16 bundle JSON + collapsible payload accordion.
- **`GET /quote_compare.html`** — Paste contractor quote JSON + cost lines → see verdict summary + signatures + optional full report.

### New orchestrator phase
- **`c03a_extreme_case_detection`** — runs between C2 and C4 in async-flags mode. Skipped without a full Brief; otherwise surfaces detected extreme-case IDs/categories. PIPELINE_PHASES grew from 17 → 18.

### New modules
- `orchestration/phase_payloads.py` — JSON serializer for dataclass phase payloads.
- `orchestration/freeform_inputs.py` — Plot + FloorRoomBrief JSON builders.
- `orchestration/adapters/c12_c13_c14_to_c15.py` — C15 triples + ProblemAnalysisMetadata.
- `orchestration/adapters/c12_to_c16.py` — C16 UpstreamInputBundle + SelectionResult assembly.
- `api/quote_endpoint.py` — C17 endpoint.
- `static/orchestrator_run.{html,css,js}` + `static/quote_compare.{html,js}` — the UI.

### Tests
- New: `test_s59_followups.py` (27 tests) + `test_master_orchestrator_scenarios.py` (8 tests).
- Updated assertions: `test_master_orchestrator_smoke.py` + `test_orchestrate_endpoint.py` (18-phase count + new C15/C16/C17 status expectations).
- Total orchestration suite: 92 tests passing (1 skipped, 1 known-flaky deselected).

**Phase status at S59 close:**

| Phase | Default status | Notes |
|---|---|---|
| `c01_brief` / `c02_feasibility` | SKIPPED or OK | Same as S57 |
| **`c03a_extreme_case_detection`** | **SKIPPED or OK (S59 #10)** | Async-flags: detection-only, never halts |
| `c04_plot_analysis` → `c11a_topology_mutation` | OK | Same as S57 |
| `c11b_nsga_refinement` | STUB by default; OK opt-in | Same as S57 |
| `c12_vertical_placement` → `c14_connection_graph` | OK | Same as S57 |
| **`c15_problem_finder`** | **OK (S59 #7)** | Triples adapter ships analyze_problems_batch |
| **`c16_dual_drawings`** | **OK or STUB (S59 #8)** | OK when bundles render; STUB when C13 sparse-edge → 0 candidates |
| **`c17_quote_comparison`** | **SKIPPED in master pipeline (S59 #9)** | Runs via separate `/api/quote/compare` endpoint |

---

## 📌 S60 must-do list

### Calendar-bound (Ramalingam-driven; Claude cannot do alone)
1. **B-238 architect outreach** — packet ready at `04_backlog/B238_architect_engagement_packet_S56/`. UI is NOW ready for architect click-through. Send the outreach emails.
2. **B-220 plumbing engineer outreach** — packet not yet built; clone B-238 structure when ready.

### Component-level fixes surfaced by S59 scenario corpus
Each one is a self-contained component bug that breaks a specific (city, brief) combo. Listed by leverage:
- **B-107 C6 intercardinal facing** — NE/SE/SW/NW facings rejected; blocks chennai_30x40 fixture.
- **B-C8-LARGE-PLOT-COVERAGE** — corridor self-intersection on delhi_60x90 + large brief.
- **B-NEW-C9-SIZING-EXHAUSTION** — Pune 30x40 + medium brief exhausts C9 search budget.
- **B-NEW-C10-PHASE3-CLUSTER-EXHAUSTION** — Mumbai + Hyderabad 30x40 + small brief exhausts wet-zone wall assignment.
- **B-C12-EDGE-DENSITY** (already filed) — C12 slicing-tree produces 0 shared edges on smoke fixture; causes the C16 STUB landing.

### Architectural improvements (post-B-238)
- **Per-candidate C10 wet-zone re-planning** — `c12_to_c16` adapter currently reuses the first C10 plan for every drawable candidate. Acceptable while C12 usually emits 1 placement; needs proper join post-B-238.
- **C11b NSGA flake** — `test_orchestrator_flips_c11b_to_ok_with_real_evaluator` fails in isolated runs (passes in full sweep). Either deselect or fix root cause.

### Documentation deliverable (user-deferred since S54)
- **Detailed v1+ roadmap (Option C)** — best authored AFTER B-238 feedback lands so "what's missing" reflects architect-validated reality.

### Pre-existing back-pocket
- **B-NEW-PUNE-SOIL-SCENARIO-REFRESH** — Pune soil S05/S17 scenarios currently excluded with breadcrumb (KB has STIFF_CLAY, scenarios expect BLACK_COTTON).
- **Trivial fix** — `api/brief_endpoint.py:664` `datetime.utcfromtimestamp` deprecation (1,421 warnings/sweep).

---

## ⚠️ Critical landmines for the next Claude

### Landmine 1 — Test baseline grew ~4,386 → ~4,420 (S59 +35 tests)

S59 added 27 follow-up tests + 8 scenario tests. Don't think existing tests broke.

### Landmine 2 — `test_orchestrator_flips_c11b_to_ok_with_real_evaluator` is flaky

Failed in isolated subset runs during S59; passes in the full sweep. **Not new — already flaky at S57 close.** NSGA non-determinism. Consider deselecting in CI or fixing the seed.

### Landmine 3 — PIPELINE_PHASES is now 18, NOT 17

S59 #10 added `c03a_extreme_case_detection`. Tests that hardcoded 17 were updated. Use `len(PIPELINE_PHASES)` not the literal.

### Landmine 4 — c17/__init__.py is EMPTY

`from buildemup.components.c17 import run_c17` fails. Import from `buildemup.components.c17.orchestrator` directly. The S59 quote endpoint does this correctly; other future C17 callers should too.

### Landmine 5 — C16 ships OK *or* STUB depending on C13 join

The bangalore smoke fixture hits the C12 sparse-edge case → 0 C13 successes → 0 drawable candidates → C16 STUB. Other fixtures may flip C16 to OK. **Both are valid.** The scenario corpus + S59 tests assert `in (OK, STUB)`.

### Landmine 6 — Quote endpoint auto-computes signature

The endpoint always overwrites caller-supplied `parsed_quote_signature` with the canonical SHA-256 derived from line items. Callers don't need to implement C17's canonicalisation.

### Landmine 7 — Scenario corpus deliberately records known-broken combos

5 of 6 fixture combos in `test_master_orchestrator_scenarios.py` are tagged with their expected failing phase. The test asserts "this combo fails AT this phase" — when the underlying component bug is fixed, flip the row's expected_failing_phase to None.

### Landmine 8 — Tailwind via CDN

`<script src="https://cdn.tailwindcss.com">` in the HTML head. No build step. Don't try to compile.

### Landmine 9 — Static file allowlist in server.py

Adding new static files = update the path tuple in `do_GET` near `/brief_form.html`. Forget = 404.

### Landmine 10 — Inherited landmines (still apply)
`c01_brief_capture.py` + `c01/` are complementary (not duplicates); same for C7. `rendered_explain` vs `combined_rendered_explain`. GitHub repo is PRIVATE. User is non-engineer. Vastu FULL is hidden (B-099), not removed.

---

## ✅ How to verify project state on your own machine

**Smoke test the orchestrator (~4 min):**
```powershell
cd "C:\Buildemup Full 17 components complete\.claude\worktrees\wonderful-agnesi-b41550\06_upstream_codebase\buildemup"
"C:\Buildemup Full 17 components complete\06_upstream_codebase\venv\Scripts\python.exe" -m pytest tests/test_orchestration -q --deselect tests/test_orchestration/test_c11b_real_evaluator.py::test_orchestrator_flips_c11b_to_ok_with_real_evaluator
```
Expected: **92 passed, 1 skipped, 1 deselected**.

**Live server with the new UI:**
```powershell
cd "C:\Buildemup Full 17 components complete\06_upstream_codebase"
.\venv\Scripts\Activate.ps1
python -m buildemup.api.server
```
Then browse:
- `http://localhost:8000/orchestrator_run.html` — run pipeline + see drawings
- `http://localhost:8000/quote_compare.html` — paste a quote → see verdict

**Full sweep (~6 min):** ~4,420 passed (vs 4,386 at S57 close).

---

## 🛣️ Recommended directions for S60

### Option A (RECOMMENDED) — Pure architect-feedback wait
S59 closed every Claude-actionable orchestrator item. Pause work; focus on B-238 outreach. Return when feedback lands. The architect's findings should drive what we fix next.

### Option B — Fix scenario-corpus known-broken combos
Each (B-107, B-C8, B-C9, B-C10) is a tractable component bug. ~2-4h each. Useful but lower B-238 leverage than (A).

### Option C — v1+ roadmap doc
Still deferred per user direction; do AFTER B-238 feedback.

### Option D — Polish the UI surface
Add CSV/PDF download for the C17 report; nicer drawing visualisation; mobile responsiveness. Useful if architect demos happen on a phone.

**My recommendation:** Option A. The orchestrator is now demo-ready. The next move belongs to the architect, not the codebase.

---

## 📁 Where everything is

| What | Where |
|---|---|
| This document | `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` (you're reading) |
| **S59 session log (READ FIRST)** | `00_START_HERE/S59_SESSION_LOG.md` |
| S57 session log | `00_START_HERE/S57_SESSION_LOG.md` |
| S56 session log | `00_START_HERE/S56_SESSION_LOG.md` |
| **S57 follow-ups (all 14 now closed)** | `04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md` |
| B-238 architect packet | `04_backlog/B238_architect_engagement_packet_S56/00_README.md` |
| **Orchestrator UI (S59 #14)** | `06_upstream_codebase/buildemup/static/orchestrator_run.html` |
| **Quote-compare UI (S59 #14)** | `06_upstream_codebase/buildemup/static/quote_compare.html` |
| **Quote endpoint (S59 #9)** | `06_upstream_codebase/buildemup/api/quote_endpoint.py` |
| Master Orchestrator | `06_upstream_codebase/buildemup/orchestration/master_orchestrator.py` |
| Orchestrator adapters | `06_upstream_codebase/buildemup/orchestration/adapters/` |
| Free-form input contract (S59 #11) | `06_upstream_codebase/buildemup/orchestration/freeform_inputs.py` |
| Payload serializer (S59 #12) | `06_upstream_codebase/buildemup/orchestration/phase_payloads.py` |
| Backlog triage | `04_backlog/S54_BACKLOG_TRIAGE.md` |
| Memory (auto-loaded) | `~\.claude\projects\C--Buildemup-Full-17-components-complete\memory\` |

---

## 🧠 Memory state at S59 close

Memory file `project_buildease_state_and_deferred_tasks.md` updated to reflect: all 14 S57 orchestrator follow-ups closed; pipeline now produces drawable, comparable artifacts; only calendar-bound + component-level bugs remain.

Memory file `feedback_proceed_without_asking.md` updated with the S59 reinforcement: blanket approval for tests + code changes inside the worktree.

If memory shows different content than this handoff, **trust the handoff** (it's more recent).

---

## 🎓 Project context (one paragraph for fresh sessions)

BuildemUp† (placeholder name; future "BuildEase") is a decision-support engine for Indian families building their own home. The product exists to close information asymmetry between homeowners and contractors/architects/engineers — particularly making material cost, engineer fees, labour, contractor margin, and timeline all visible separately. 17 components: C1 brief → C2 feasibility → C3a/C3b negotiation → C4 plot analysis → C5 topology → C6 orientation → C7 structural grid → C8 corridor → C9 room sizer → C10 wet zones → C11a/b topology mutation + NSGA-II → C12 vertical alignment → C13 doors → C14 connection graph → C15 problem finder → C16 dual drawings → C17 quote comparison. **At S59 close, the master orchestrator runs C4 → C16 as a real chain with C15 + C16 OK and an end-to-end browser UI; C17 runs as a separate /api/quote/compare flow; PIPELINE_PHASES carries 18 entries (the canonical 17 + c03a_extreme_case_detection async-flags phase).** Soul-complete v1 also requires 3D, interior design, full CAD pack for construction, municipal submission, construction-phase help — none of which exist yet.

†= placeholder name marker. Final product name TBD ("BuildEase" preferred; "Archimind" is taken).

**Welcome to S60. Read `S59_SESSION_LOG.md` first, then this file. Then await Ramalingam's direction.**
