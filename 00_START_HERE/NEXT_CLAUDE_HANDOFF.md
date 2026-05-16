# 🚨 NEXT CLAUDE — START HERE — S56 OPEN

**Authored:** Ramalingam + Claude, S55 close, May 16, 2026
**Session state:** 14 backlog items closed in S54 + 25 more in S55 = 39 total Bucket A/B items shipped. C12 reached v1.1 via EXTERNAL-EDGE-TYPE-AMENDMENT (HIGH priority); also added FailureTrace v1.1 (B-C12-CAUSAL-FAILURE-TRACEABILITY). 4,356-test sweep clean (21 pre-existing baseline failures separately tracked).
**Latest LOCK:** C12 v1.1 schema amendments (additive defaults; no contract breaks). All other S55 changes are non-LOCK-touching fixes.
**Your task:** Read this file. Then read `S55_SESSION_LOG.md` (chronological detail for S55) and `04_backlog/S54_BACKLOG_TRIAGE.md` (the 4-bucket plan). Then await Ramalingam's S56 direction.

---

## 🎯 What S55 accomplished

S55 was a **single-session continuation of Bucket B**. The user authorized "everything in bucket B" with Claude choosing the order, then asked to complete Batch 3 in-session as well. **25 items shipped** across 2 batches. Full chronological log is in `S55_SESSION_LOG.md`. Headline numbers:

| Metric | At S55 open | At S55 close |
|---|---|---|
| Bucket A (deploy-blockers) | 2 open (calendar-bound) | 2 open (unchanged — calendar-bound) |
| Bucket B (product-blockers) | ~47 open | ~22 open |
| Tests passing (S54+S55-touched surface) | n/a | 4,356 of 4,356 (+107 new test cases) |
| New typed exception layer | none | `domain/exceptions.py` with 5 typed errors |
| New Brief field | none | `LayoutOverrides` (B-NEW-J-override) |
| C12 schema version | v1.0 LOCKED | v1.1 (additive: edge_type + FailureTrace) |
| C13 polish layer | n/a | `c13/v1x_polish_s55.py` (invariant taxonomy + adversarial corpus + window avoidance) |
| C17 critique closures | none | 7 items via `c17/critique_closure_s55.py` + α/δ edits |
| CI tooling | none | `scripts/spec_drift_check.py` (B-PROJECT-SPEC-DRIFT-CI) |
| KB versions bumped | n/a | kb.soil_classification v1→v2; kb.soil_city_defaults v1.0→v1.1 |

### Specific items closed in S55 (25 total)

**Batch 2 — code-only, all DONE (7):**
1. **B-074** — MEDIUM_ROCK as first-class kb.SoilClass with IS 6403 typical 1250 kPa
2. **B-062** — Startup cross-check: BUILDEMUP_ENV=prod + C3A_TEST_MODE=1 → sys.exit(1)
3. **B-064** — CSP + Cache-Control + nosniff headers on static assets
4. **B-013** — Typed exception migration: BriefDomainError + 5 subclasses
5. **B-108 partial** — NBC corridor minimum citation breadcrumb + verification report
6. **B-109** — `design_corridors_safe()` + `NarrowPlotRecommendation` graceful fallback
7. **B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT** (HIGH) — C12 v1.1 SharedEdge.edge_type

**Batch 3 — closures, all DONE (18):**

C17 critique findings (7):
- 8. **B-C17-LEGITIMATE-PREMIUM-DISCLAIMER** — principle-aligned premium sentence in δ
- 9. **B-C17-ARITHMETIC-MISMATCH-INDICATOR** — severity bands on QuoteLineCanonical
- 10. **B-C17-RATE-SANITY-DETECTOR** — 10×/0.1× envelope outlier detector
- 11. **B-C17-MATCH-BASIS-EXPANSION** — `ExpandedMatchBasis` discoverable fields
- 12. **B-C17-SEMANTIC-MATCH-LAYER** — `BoqDomain` ontology + classifier + compat check
- 13. **B-C17-CONTRACTOR-RESPONSE-SECTION** — `ContractorResponse` dataclass
- 14. **B-C17-ALTERNATE-MARKET-REFERENCES** — `AlternateMarketReference` dataclass

C12 leftovers (2):
- 15. **B-C12-CAUSAL-FAILURE-TRACEABILITY** — parallel `FailureTrace` dataclass (LOCKED FailureRecord preserved)
- 16. **B-PROJECT-SPEC-DRIFT-CI** — `scripts/spec_drift_check.py` runner with `--strict`

C11a/b launch-complement (6):
- 17. **B-NEW-J-override** (must ship with C11a v1) — `LayoutOverrides` + consultation hook
- 18-20. **B-NEW-T1.5/T3/Y-full** — manifest entries (DEFERRED_BUILD / DEFERRED_GATED)
- 21. **B-C11B-PURITY-SPOTCHECK** — `c11b_purity_spotcheck()` helper
- 22. **B-C11B-CANONICAL-GOLDEN-TESTS** — `C11bGoldenFixture` + scaffold

C13 v1.x polish (3):
- 23. **B-C13-INVARIANT-TAXONOMY-GROUPING** (CRITICAL) — `InvariantClass` + taxonomy covering all 13 v1.0 invariants
- 24. **B-C13-ADVERSARIAL-INTEGRATION-CORPUS** — 5 named adversarial test recipes
- 25. **B-C13-WINDOW-AVOIDANCE** — `WindowAvoidanceAdvisory` dataclass

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

**Welcome to S56. Read `S55_SESSION_LOG.md` next for S55 chronological detail (then `S54_SESSION_LOG.md` for earlier context), then `S54_BACKLOG_TRIAGE.md` for the work plan.**

---

## 🛣️ Recommended Batch 4 directions for S56

Batches 2 + 3 closed everything in Bucket B *except* the LOCK-mandatory pile and the two large items. S56 should pick from:

- **C14 LOCK-mandatory** (4 items) — lock betweenness/privacy/transit/edge formulas before C14 v1.0 ships. Each item is hours of focused spec work; recommended start.
- **C15 LOCK-mandatory** (7 items) — severity-rule-table, check-registry, cultural-profile, measurement-formulas, moat-lint.
- **C16 LOCK-mandatory** (~17 items) — envelope schema, section-cut rules, RWH overlay, compliance provenance, parking schema, PBT coverage, regression snapshots, dual-frame coordinate audit.
- **B-066 polygon plots** (1 item, large) — promoted from v2-deferred to product-blocker by user decision; touches C5/C7/C8.
- **C6 trust gap** (2 items) — B-127 reconstruct 186 missing tests; B-128 bundle integrity check.

**My recommendation:** start with C14 LOCK-mandatory because each subsequent component depends on C14's locked formulas. Then C15 → C16 → B-066 → C6 trust gap.

Also worth picking up: the **21 pre-existing failures** that the S55 sweep surfaced (`test_c01_v09_session_b.py` Windows storage-handle races + `test_c02_session_j/k/l.py` Pune downgrade) — file as new Bucket B items in Batch 4 and fix early; they're likely small once root cause is found.

## 🚩 Pre-existing failures filed in S55 (file as Bucket B in Batch 3)

21 pre-existing failures observed during S55's full-bundle sweep, verified by stash-and-rerun to predate S55 work:
- 17 failures in `test_c01_v09_session_b.py` — Windows file-handle race on storage tests
- 2 failures in `test_c02_session_j.py` — Pune downgrade rule scenario (S17)
- 1 each in `test_c02_session_k.py` + `test_c02_session_l.py` — inherit session_j validation

File these as new Bucket B items when Batch 3 starts; they're likely small fixes once root cause is found.
