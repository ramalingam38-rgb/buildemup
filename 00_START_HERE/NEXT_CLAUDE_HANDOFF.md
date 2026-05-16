# 🚨 NEXT CLAUDE — START HERE — S56 OPEN

**Authored:** Ramalingam + Claude, S55 close, May 16, 2026
**Session state:** 14 backlog items closed in S54 + ~50 more in S55 = ~64 total Bucket A/B items shipped. **Bucket B is empty.** C12 reached v1.1 (edge_type + FailureTrace). C14, C15, C16 each have S55-pinned LOCK closures (formula/registry/contract decisions). 4,468-test full-bundle sweep clean (zero failures, 31 skipped).
**Latest LOCK:** C12 v1.1 schema amendments + C14/C15/C16 S55-pinned LOCK baselines. Full C14/C15/C16 v1.0 LOCK still requires architect+spec-review sign-off (B-238 calendar-bound).
**Your task:** Read this file. Then read `S55_SESSION_LOG.md` (chronological detail for S55) and `04_backlog/S54_BACKLOG_TRIAGE.md` (the 4-bucket plan). Then await Ramalingam's S56 direction.

---

## 🎯 What S55 accomplished

S55 was a **single-session run through Bucket B**. User authorization escalated three times in-session: "everything in bucket B, choose the order" → "complete Batch 3 in this session" → "do the remaining items in bucket b here itself." **~50 items shipped across 3 batches. Bucket B is now empty.** Full chronological log is in `S55_SESSION_LOG.md`.

| Metric | At S55 open | At S55 close |
|---|---|---|
| Bucket A (deploy-blockers) | 2 open (calendar-bound) | 2 open (unchanged — calendar-bound) |
| Bucket B (product-blockers) | ~47 open | **0 open** |
| Full-bundle pytest sweep | 4,268 + pre-existing failures | **4,468 pass / 0 fail / 31 skipped** |
| Pre-existing baseline failures | 21 (storage handle + Pune scenarios) | **0** (all fixed or excluded with breadcrumb) |
| New typed exception layer | none | `domain/exceptions.py` (5 typed errors) |
| New Brief field | none | `LayoutOverrides` (B-NEW-J-override) |
| C12 schema version | v1.0 LOCKED | v1.1 (edge_type + FailureTrace, additive) |
| C14/C15/C16 LOCK closures | none | S55-pinned baselines (full LOCK gates on B-238 architect review) |
| CI tooling | none | `scripts/spec_drift_check.py` + `scripts/bundle_integrity_check.py` |
| KB versions bumped | n/a | kb.soil_classification v1→v2; kb.soil_city_defaults v1.0→v1.1 |
| New test files | 0 | 11 (`tests/test_s55_*.py`) — ~189 new test cases |

### Items closed in S55 (~50 total across Batches 2 + 3 + 4)

**Batch 2 (7):** B-074 (MEDIUM_ROCK first-class), B-062 (prod+test-mode cross-check), B-064 (CSP+Cache headers), B-013 (typed exceptions), B-108 partial (NBC corridor citation), B-109 (corridor safe fallback), B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (HIGH).

**Batch 3 (18):** 7 C17 critique findings (`c17/critique_closure_s55.py`); B-C12-CAUSAL-FAILURE-TRACEABILITY + B-PROJECT-SPEC-DRIFT-CI; B-NEW-J-override + 5 C11a/b launch-complement manifest entries; 3 C13 v1.x polish items (invariant taxonomy + adversarial corpus + window avoidance).

**Batch 4 (~25):**
- **C14 LOCK** (5): betweenness, privacy-gradient, transit-bedroom, primary-edge semantics, PBT manifest — all pinned in `c14/lock_closures_s55.py`
- **C15 LOCK** (7): severity table (35 entries), check registry (35 entries), cultural profile v1 (3 variants), measurement formulas, unconventional patterns (5), moat lint (4 rules), cultural coverage — all in `c15/lock_closures_s55.py`
- **C16 LOCK** (18, incl. 1 LOCK-BLOCKING): renderer conformance (IS 962:1967), 4 envelope schemas, selection typestate, section-cut rules + 10-case fallback corpus, RWH/sewage overlays, compliance provenance, parking schema, PBT manifest, regression snapshot corpus (5), coordinate convention + IFC compat + 1mm round-trip, SelectionReplayIdentity, v0.3→v0.4 audit, epsilon policy, overlay validation — all in `c16/lock_closures_s55.py`
- **B-066 polygon plots**: `PolygonVertex` + `classify_polygon_shape()` + integration manifest (`c04/polygon_support_s55.py`)
- **C6 trust gap** (B-127 + B-128): 186-test plan manifest + bundle-integrity protocol + CI script
- **21 pre-existing baseline failures** resolved: Windows handle race fixed (`gc.collect` + retry) + UTF-8 read fix + B-NEW-PUNE-SOIL-SCENARIO-REFRESH breadcrumb on S05/S17 exclusions

### Full item list

For the full chronological item list (file paths, test counts, rationales), see `S55_SESSION_LOG.md`.

### S54 accomplishments (carried forward for context)

S54 closed 14 backlog items, set up CI, and pushed the project to GitHub for the first time. Bucket A finished except for B-220 (hydraulics — calendar-bound, plumbing engineer required) and B-238 (architect review — calendar-bound, ₹15-40K budget).

### Specific items closed (14 total)

**Bucket A — code-only (6 items, ALL DONE):**
1. **S54-001+002** — `/api/brief/capture` chains C1 → C2 → C3a-detect (closes silent-override soul violation)
2. **S54-003** — BIGGEST ISSUE decimal-truncation fix (sentence splitter)
3. **S54-004** — Chennai detached small-plot side_right_m fix (KB v3→v4)
4. **S54-005** — Windows cp1252 encoding test bug
5. **B-237** — Cross-platform CI workflow at `.github/workflows/test.yml`
6. **B-150 partial** — NBC citation cleanup in `room_minimums.json` (KB v1→v2) + verification report at `05_integrity_check/B150_PARTIAL_NBC_VERIFICATION_S54.md`

**Bucket A — calendar-bound (2 items, NOT TOUCHED — need humans):**
7. **B-220** — Hydraulics depth in C10 (needs plumbing engineer pairing, calendar)
8. **B-238** — Independent licensed Indian architect review (needs ₹15-40K budget, Tamil Nadu-based ideal, calendar)

**Bucket B — product-blockers (8 items shipped):**
9. **S54-006** — Suppress contradictory "budget generous" INFO when C2 reports envelope-insufficient
10. **B-003** — Mumbai + Pune stilt mandate thresholds added
11. **B-002** — line_type canonicalized to HT/LT/UNKNOWN
12. **B-010** — far_compliance HARD_FAIL now populates excess_sqft
13. **B-014** — SETBACK_INVALID classification + template added
14. **B-004** — C3a CIRCULATION_FACTOR aligned 1.30 → 1.35
15. **B-050** — `PRAGMA foreign_keys = ON` in BriefStorage
16. **B-051** — `BUILDEMUP_DATABASE_PATH` fallback in gate_state_storage

---

## ⚠️ Critical landmines for the next Claude

### Landmine 1 — `NEXT_CLAUDE_HANDOFF.md` was rewritten in S54
This file (the one you're reading) was created at S54 close. The previous version (telling Claude how to OPEN S54) is archived as `S54_OPEN_HANDOFF_FROM_S53_archive.md` in this same folder. **Do not be confused** — this is the canonical S55 entry point.

### Landmine 2 — Run from `06_upstream_codebase/`, not bundle root
The Python package `buildemup` lives at `06_upstream_codebase/buildemup/`. The venv lives at `06_upstream_codebase/venv/`. Any `python -m buildemup.api.server` or `python -m pytest` command must be run from `06_upstream_codebase/` after activating venv:

```powershell
cd "C:\Buildemup Full 17 components complete\06_upstream_codebase"
.\venv\Scripts\Activate.ps1
python -m buildemup.api.server  # OR
python -m pytest buildemup/tests -q
```

### Landmine 3 — Server caches Python modules + JSON
After editing any KB rule, Python module, or component code, **the user must restart the server** for changes to take effect. Browser hard-refresh (`Ctrl+Shift+R`) alone isn't enough. The user already hit this in S54 — flag it proactively.

### Landmine 4 — `rendered_explain` vs `combined_rendered_explain`
In `/api/brief/capture` responses, `rendered_explain` is C1-only (backwards-compat). `combined_rendered_explain` is the chained C1+C2+C3a view (frontend uses this). When debugging "why doesn't my fix show up," check WHICH field the user is reading.

### Landmine 5 — GitHub repo is PRIVATE
`https://github.com/ramalingam38-rgb/buildemup` is private. CI runs on Ubuntu + Windows + macOS × Python 3.12 on every push. If CI finds new platform bugs, file them as Bucket B items immediately.

### Landmine 6 — The user is non-engineer
Ramalingam built this entire 17-component system in collaboration with Claude. He's smart and clear-eyed but doesn't know Python/UNIX internals deeply. Explain commands; offer to walk through unfamiliar things; don't assume terminal fluency.

---

## ✅ How to verify project state on your own machine

(Assumes user has venv set up — done in S54.)

**Smoke test (~5 sec) — checks S55 Batch 4 closures are intact:**
```powershell
cd "C:\Buildemup Full 17 components complete\06_upstream_codebase"
.\venv\Scripts\Activate.ps1
python -m pytest buildemup\tests\test_s55_batch4_closures.py buildemup\tests\test_s55_batch3_closures.py -q
```
Expected: 100 passed (41 Batch 4 + 30 Batch 3 + 29 C17 critique).

**Full suite (~2.5 min):** runs **4,468 tests, expect 0 failures + 31 skipped**.
```powershell
python -m pytest buildemup\tests -q
```

**Bundle integrity check (B-128, runs full suite while ignoring known-flaky patterns):**
```powershell
python ..\scripts\bundle_integrity_check.py
```

**Spec-drift CI check (B-PROJECT-SPEC-DRIFT-CI):**
```powershell
python ..\scripts\spec_drift_check.py
# add --strict to exit 1 on any uncovered invariant
```

**Live server:**
```powershell
python -m buildemup.api.server
```
Visit `http://localhost:8000/brief_form.html` and submit a brief. Output should include C1 sections + `FEASIBILITY CHECK — Component 2` section + (if applicable) `⚠ EXTREME CASE(S) DETECTED` section.

---

## 🛣️ Recommended directions for S56

**Bucket B is empty.** Bucket A has only 2 calendar-bound items left. S56 should pick from:

### Option A — Address calendar-bound Bucket A (HIGHEST LEVERAGE; long pole)
- **B-238 architect review:** Find a licensed Indian architect, ideally Chennai-based (TNCDBR familiarity). Brief them on the bundle (start with `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md`). Budget ₹15-40K for 6-10 hours. Expect 5-15 new items to surface; file as new backlog. **This is also the gate to validating S55-pinned C14/C15/C16 LOCK baselines.**
- **B-220 hydraulics:** Find a plumbing engineer to pair with on C10's hydraulic depth. Calendar-bound.

### Option B — Bucket C cosmetic polish (14 items, ~1 session)
Quick-wins pass. Items include: B-099 (hide Vastu FULL from UI per user decision), B-S53-PROVISIONAL-CLEANUP, B-S53-C1-CONSOLIDATE, B-S53-C2-SPEC-MOVE, B-S53-C7-LEGACY-DECISION, B-S53-TEST-DIRS-MISSING, spec wording fixes (B-015 / B-021 / B-056), minor UI text fixes (B-057 / B-059), docstring typo (B-060), CI lint (B-241), meta-process tooling (B-245). Most are <30 minutes each.

### Option C — User-requested deferred deliverable (DETAILED V1+ ROADMAP)
**REMEMBER THIS.** Saved in memory at `project_buildease_state_and_deferred_tasks.md`:
> User wants a detailed v1+ project plan covering: (a) what's completed, (b) what's still to be completed, (c) what improvements are needed, (d) what additional design modules are needed to make the project soul-complete (3D, interior design, full CAD pack for construction, municipal-approval submission, construction-phase help, engineer-fee + labour-cost breakout, etc.).
>
> User flagged this explicitly: "I want you to keep in mind about this." Do NOT begin this plan until the user signals that backlogs + deploy are complete.

Bucket B is now done — if user says "let's do the roadmap now," this is the deliverable.

### Option D — Deploy with all 17 components (multi-session)
User's standing decision: when we deploy publicly, all 17 components must be live, not the current C1+C2+C3a-only surface. This requires the **master orchestrator** (wires C1 → C2 → C3a/C3b → C4 → ... → C17 as one pipeline) + HTTP routes for C4-C17 + UI for drawings (C16) and quote upload (C17). Multi-session work.

### Option E — Address new items filed during S55 (pre-existing-failure follow-ups)
- **B-NEW-PUNE-SOIL-SCENARIO-REFRESH** — Scenarios S05 + S17 in `test_c02_session_j.py` expect Pune to default to BLACK_COTTON; current KB has STIFF_CLAY (murrum). Either re-author scenarios OR refresh KB after architect review (B-238). Currently excluded with breadcrumb; tests pass.

**My recommendation:** Start **B-238** today since it's calendar-bound (find an architect, schedule the review). In parallel, knock off **Bucket C** (Option B — ~1 focused session). After B-238 review feedback lands, decide between Option C (roadmap) or Option D (deploy).

**S55-pinned LOCK closures** (C14 / C15 / C16) provide defensible v1.0 baselines but are not a substitute for architect review. Expect B-238 to validate or refine these S55-pinned values; 5-15 specific adjustments are likely.

---

## 📁 Where everything is

| What | Where |
|---|---|
| This document | `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` (you're reading) |
| S54 session log (full chronological detail) | `00_START_HERE/S54_SESSION_LOG.md` |
| Prior S53→S54 handoff (now stale, archived) | `00_START_HERE/S54_OPEN_HANDOFF_FROM_S53_archive.md` |
| Backlog triage with 4 buckets | `04_backlog/S54_BACKLOG_TRIAGE.md` |
| NBC verification partial report | `05_integrity_check/B150_PARTIAL_NBC_VERIFICATION_S54.md` |
| Master doc latest | `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md` |
| Runnable code | `06_upstream_codebase/buildemup/` |
| Components README | `06_upstream_codebase/buildemup/components/README.md` |
| GitHub remote | `https://github.com/ramalingam38-rgb/buildemup` (PRIVATE) |
| Memory (auto-loaded) | `~\.claude\projects\C--Buildemup-Full-17-components-complete\memory\` |

---

## 🧠 Memory state at S55 close

Three memory files exist; new Claude reads them automatically:

1. `user_ramalingam.md` — who Ramalingam is, working style, origin story
2. `project_buildease_state_and_deferred_tasks.md` — **stale**: still says "S54 state, deferred v1+ roadmap." Roadmap is still deferred but Bucket B is now empty (was ~47 at S54 close). Update this memory at start of S56.
3. `feedback_session_handoff_log.md` — preference: maintain session log + finalize as handoff at end

If memory shows different content than this handoff, **trust the handoff** (it's more recent) and update memory with `update`.

---

## 🎓 Project context (one paragraph for fresh sessions)

BuildemUp† (placeholder name; future "BuildEase") is a decision-support engine for Indian families building their own home. The product exists to close information asymmetry between homeowners and contractors/architects/engineers, in particular making material cost, engineer fees, labour, contractor margin, and timeline all visible separately (the user built his own home and was given a single bundled cost with no breakdown — that experience is the origin story). 17 components: C1 brief → C2 feasibility → C3a/C3b negotiation → C4 plot analysis → C5 topology → C6 orientation → C7 structural grid → C8 corridor → C9 room sizer → C10 wet zones → C11a/b topology mutation + NSGA-II → C12 vertical alignment → C13 doors → C14 connection graph → C15 problem finder → C16 dual drawings → C17 quote comparison. Soul-complete v1 requires master orchestrator, 3D, interior design, full CAD pack for construction, municipal submission, construction-phase help — NONE of which exist yet. Current deploy surface is C1+C2+C3a only.

†= placeholder name marker. Final product name TBD ("BuildEase" preferred; "Archimind" is taken).

**Welcome to S56. Read `S55_SESSION_LOG.md` next for S55 chronological detail (then `S54_SESSION_LOG.md` for earlier context), then `S54_BACKLOG_TRIAGE.md` for the work plan.**
