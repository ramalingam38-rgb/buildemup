# 🚨 NEXT CLAUDE — START HERE — S55 OPEN

**Authored:** Ramalingam + Claude, S54 close, May 16, 2026
**Session state:** 14 backlog items closed in S54; project pushed to private GitHub repo `ramalingam38-rgb/buildemup`; CI matrix active.
**Latest LOCK:** No new LOCKs in S54 (Bucket A + B fixes only — no contract changes).
**Your task:** Read this file. Then read `S54_SESSION_LOG.md` (chronological detail) and `04_backlog/S54_BACKLOG_TRIAGE.md` (the 4-bucket plan). Then await Ramalingam's S55 direction.

---

## 🎯 What S54 accomplished

S54 was a **single-day execution session** that closed 14 backlog items, set up CI, and pushed the project to GitHub for the first time. The full chronological log is in `S54_SESSION_LOG.md`. Headline numbers:

| Metric | At S54 open | At S54 close |
|---|---|---|
| Bucket A (deploy-blockers) | 8 open | 2 open (B-220, B-238 — calendar-bound, need humans) |
| Bucket B (product-blockers) | ~55 open | ~47 open |
| Tests passing | 4,268 | 4,312 (+44 new test cases) |
| GitHub state | not a repo | private repo `ramalingam38-rgb/buildemup` + 2 commits + CI active |
| Live verification | C1 brief surface only | C1 + C2 + C3a chain working live + verified twice by user |
| Memory files | none | 3 files at `~/.claude/projects/.../memory/` |

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

**Smoke test (~3 sec):**
```powershell
cd "C:\Buildemup Full 17 components complete\06_upstream_codebase"
.\venv\Scripts\Activate.ps1
python -m pytest buildemup\tests\test_s54_brief_chain.py buildemup\tests\test_s54_006_budget_suppression.py -q
```
Expected: 10 passed.

**Full suite (~90 sec):** runs ~4,312 tests; see `04_backlog/S54_BACKLOG_TRIAGE.md` Phase 17 for the canonical invocation pattern.

**Live server:**
```powershell
python -m buildemup.api.server
```
Visit `http://localhost:8000/brief_form.html` and submit a brief. Output should include C1 sections + `FEASIBILITY CHECK — Component 2` section + (if applicable) `⚠ EXTREME CASE(S) DETECTED` section.

---

## 🛣️ Recommended directions for S55

Pick one based on Ramalingam's signal:

### Option A — Continue Bucket B (still ~47 items)
Biggest sub-cluster: **C14/C15/C16 LOCK-mandatory items (~28 items)**. These were filed at component v1.0 LOCK time as v1-launch-blockers. Each one is hours of work — reading specs, locking formulas, writing tests.

Other Bucket B groupings:
- C17 critique findings (7 items — semantic-match, arithmetic-mismatch, rate-sanity OCR, etc.)
- C13 v1.x polish top 3 (invariant taxonomy, adversarial corpus, window avoidance)
- C11a/b launch-complement (6 items, B-NEW-J-override must ship with C11a v1)
- C12 critique-walk findings (3 items; B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT is HIGH priority)
- C6 trust gap (2 items: reconstruct missing C6 production tests; bundle integrity check)
- B-066 (polygon plots — promoted to B in S54 per user; Large effort)

### Option B — Address calendar-bound Bucket A items
- **B-238 architect review:** Find a licensed Indian architect, ideally Chennai-based (TNCDBR familiarity), and brief them. Budget ₹15-40K for 6-10 hours. This is the single highest-leverage pre-launch action — they will surface 5-15 new items you can't catch yourself.
- **B-220 hydraulics:** Find a plumbing engineer to pair with on C10's hydraulic depth.

### Option C — User-requested deferred deliverable (DETAILED V1+ ROADMAP)
**REMEMBER THIS.** Saved in memory at `project_buildease_state_and_deferred_tasks.md`:
> User wants a detailed v1+ project plan covering: (a) what's completed, (b) what's still to be completed, (c) what improvements are needed, (d) what additional design modules are needed to make the project soul-complete (3D, interior design, full CAD pack for construction, municipal-approval submission, construction-phase help, engineer-fee + labour-cost breakout, etc.).
>
> User flagged this explicitly: "I want you to keep in mind about this." Do NOT begin this plan until the user signals that backlogs + deploy are complete.

If user says "let's do the roadmap now," this is the deliverable.

### Option D — Deploy with all 17 components
User's standing decision: when we deploy publicly, all 17 components must be live, not the current C1+C2+C3a-only surface. This requires the **master orchestrator** (wires C1 → C2 → C3a/C3b → C4 → ... → C17 as one pipeline) + HTTP routes for C4-C17 + UI for drawings (C16) and quote upload (C17). Multi-session work.

### Option E — Cosmetic Bucket C (14 items)
Quick wins; ~1 session for all 14. Includes B-099 (hide Vastu FULL from UI per user decision), B-S53-PROVISIONAL-CLEANUP, B-S53-C1-CONSOLIDATE, B-S53-C2-SPEC-MOVE, etc.

**My recommendation:** A or B. B is calendar-bound so start it early. A is the gate to "v1 done."

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

## 🧠 Memory state at S54 close

Three memory files exist; new Claude reads them automatically:

1. `user_ramalingam.md` — who Ramalingam is, working style, origin story
2. `project_buildease_state_and_deferred_tasks.md` — S54 state + deferred v1+ roadmap task
3. `feedback_session_handoff_log.md` — preference: maintain session log + finalize as handoff at end

If memory shows different content than this handoff, **trust the handoff** (it's more recent) and update memory with `update`.

---

## 🎓 Project context (one paragraph for fresh sessions)

BuildemUp† (placeholder name; future "BuildEase") is a decision-support engine for Indian families building their own home. The product exists to close information asymmetry between homeowners and contractors/architects/engineers, in particular making material cost, engineer fees, labour, contractor margin, and timeline all visible separately (the user built his own home and was given a single bundled cost with no breakdown — that experience is the origin story). 17 components: C1 brief → C2 feasibility → C3a/C3b negotiation → C4 plot analysis → C5 topology → C6 orientation → C7 structural grid → C8 corridor → C9 room sizer → C10 wet zones → C11a/b topology mutation + NSGA-II → C12 vertical alignment → C13 doors → C14 connection graph → C15 problem finder → C16 dual drawings → C17 quote comparison. Soul-complete v1 requires master orchestrator, 3D, interior design, full CAD pack for construction, municipal submission, construction-phase help — NONE of which exist yet. Current deploy surface is C1+C2+C3a only.

†= placeholder name marker. Final product name TBD ("BuildEase" preferred; "Archimind" is taken).

**Welcome to S55. Read `S54_SESSION_LOG.md` next for chronological detail, then `S54_BACKLOG_TRIAGE.md` for the work plan.**
