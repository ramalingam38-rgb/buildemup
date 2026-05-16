# 🚨 NEXT CLAUDE — START HERE — S54 OPEN

**Authored:** Ramalingam + Claude, S53 close, May 16, 2026
**Session state:** Track 3 canonical 17-component architecture **STRUCTURALLY COMPLETE**
**Latest LOCK:** C3b v0.7 (S52); no new LOCKs in S53 (reconciliation pass only)
**Your task:** Read this. Then read `COMPONENT_STATUS_S53.md` in this same directory. Then await Ramalingam's S54 direction.

---

## 🎯 The single most important thing to know

**All 17 components are LOCKED and physically present at canonical paths
in `06_upstream_codebase/buildemup/components/`.**

This was not true at S52 close. The S52 handoff said "all 17 components
are shipped," and at the session-level it was true — but the upstream
working tree had bundle drift: 5 components (C3a, C4, C10, C12, C13)
had stub `contracts.py` files at canonical paths but the real LOCKED
code was missing. C7 had a single 951-LOC pre-amendment monolith and a
stub folder.

S53 closed every gap. All real LOCKED code is now at canonical paths.
**Test count: 750 (S53 start) → 4,268 (S53 close).**

---

## 📊 What S53 actually did

Reconciliation pass — no new specs, no new LOCKs, no contract changes.

| # | Action | Source |
|---|---|---|
| 1 | Restored C3a (9 modules + 23 tests + 5 API + 11 UI files) | `buildemup_c3a_complete.zip` upload |
| 2 | Restored C4 (7 modules) | `03_code_chronological/C4_final_shipped_files/` |
| 3 | Restored C10 (11 modules + 5 KB JSONs + 7 tests) | `c10_c12_c13_c14_components.zip` upload |
| 4 | Restored C12 (17 modules + `slicing_kd_tree/` + 8 tests) | Same upload |
| 5 | Restored C13 (16 modules + 7 tests) | Same upload + `S45_C13_v1_0_SHIPPED.zip` |
| 6 | Restored C7 (8 LOCKED modules) | `c7_complete_bundle.zip` upload + S38 `grid_generator.py` |
| 7 | Codified stub-shim pattern across all 6 restored components | S52-introduced pattern |
| 8 | Installed `hypothesis` library | `pip install --break-system-packages` |
| 9 | Filed all S53 spec docs in `02_specs_chronological/` | Move from working tree |
| 10 | Wrote `COMPONENT_STATUS_S53.md` and `components/README.md` | New authoring |
| 11 | Wrote S53 GAP/AUDIT/INTEGRITY checks | Rule 10.6 |
| 12 | Wrote `MASTER_DOC_v3_16_TO_v3_17_DELTA.md` | This delta |

---

## ⚠️ Critical landmines for the next Claude

### Landmine 1 — Do NOT trust handoff doc claims of "shipped" without verification

This is exactly the trap S53 fell into. The S52 handoff said all 17
were shipped; the truth was 5 stubs + 1 monolith. If a future session
says "C19 is shipped," **verify it physically lives at the canonical
path** by running:

```bash
ls 06_upstream_codebase/buildemup/components/cNN/
```

Empty folder or just `contracts.py` + `__init__.py` = stub. The
**multiple-module count + non-trivial LOC + tests in `tests/test_cNN/`**
is the actual proof of presence.

### Landmine 2 — `grid_generator.py` has TWO LOCKED versions

The c7_complete_bundle.zip shipped `grid_generator.py` at 301 LOC
(S36 v0.8 LOCKED). The live LOCKED contract is **501 LOC** (S38 with
B-NEW-K W9 staircase amendment baked in). The 501-LOC version lives at
`03_code_chronological/S38_code/components/c07/grid_generator.py` and is
what's currently installed at `c07/grid_generator.py`.

**Do not "revert" to the bundle version** — the project has been using
the staircase amendment continuously since S38.

### Landmine 3 — Stub-shim pattern is real architecture, not legacy

`_c3b_shim.py` files in c03a, c04, c07, c10, c12, c13 are **canonical**
per the stub-shim pattern established at S52. They are not leftover
stubs to be deleted. C3b imports from them. Renaming or removing them
will break C3b's 464-test suite.

The pattern is documented in `06_upstream_codebase/buildemup/components/README.md`.

### Landmine 4 — `c10/__init__.PROVISIONAL_S53.py` is audit trail, not active code

S53 briefly used a provisional `__init__.py` for C10 while waiting for
C7's `wall_segment.py`. Once C7 arrived, the LOCKED `__init__.py` was
restored. The provisional is preserved at `__init__.PROVISIONAL_S53.py`
for the audit trail and can be deleted at S54 (B-S53-PROVISIONAL-CLEANUP).

### Landmine 5 — `c07_structural_grid.py` at top level is the LEGACY pre-amendment version

The 951-LOC monolithic `components/c07_structural_grid.py` is the
pre-S36 monolithic version. The canonical post-amendment version lives
in `components/c07/` as 8 modular files. **No production code imports
from the top-level file.** Disposition decision pending
(B-S53-C7-LEGACY-DECISION).

---

## ✅ How to verify the project state yourself

Run this from the bundle root after unzipping:

```bash
cd 06_upstream_codebase/buildemup/tests
PYTHONPATH=$(pwd)/..:$(pwd)/../.. python3 -m pytest -q --no-header --tb=no
```

Expected: **4,268 passed, 6 skipped, 0 failed** in ~90 seconds.

If you see anything different, **stop**. Either:
- The Python version is wrong (use 3.12+)
- `hypothesis` isn't installed (run `pip install hypothesis --break-system-packages`)
- Bundle was modified after S53 close

Quick smoke (~2 seconds):
```bash
python3 -m pytest test_c03b/ test_c03a_*.py -q --no-header
# Expected: 750 passed, 3 skipped
```

---

## 🛣️ Recommended directions for S54

Ramalingam has not directed S54 yet. These are options ranked by my read:

### Option A — Pre-launch hard gates (recommended, blocks deployment)
Four backlog items have been marked as pre-launch hard gates:
- **B-220 (hydraulics):** Plumbing engineering depth — extend C10 with real hydraulic calculation, not just chase routing.
- **B-237 (cross-platform CI):** Verify the project runs on Mac/Windows/Linux reliably (currently Linux only).
- **B-238 (architect review):** Get a licensed Indian architect to review BuildEase output against real residential design practice. Cannot be done by Claude alone.
- **B-150-equiv (NBC primary verification):** Verify code citations against actual NBC 2016 text, not paraphrased KB modules.

### Option B — End-to-end orchestrator wiring
The 17 components each pass their tests individually, but there's no single
runnable pipeline `brief → feasibility → topology → grid → rooms → drawings → quote`.
This is integration work, not new design. ~2-4 sessions.

### Option C — User-facing surface
Design Principles v3.1 (locked, in `07_design_documents/`) spells out the
UX — Transparency Triple, advisory tone, confidence indicators, emotional
reassurance. The principles exist; the screens don't. ~3-6 sessions.

### Option D — Routed amendments
- **B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (HIGH priority)** routes to C12 v1.1.
- **B-NEW-J-override** must ship same release as C11a production.
- These are real LOCKED-spec amendment work, not new components.

### Option E — Cosmetic cleanup
- **B-S53-C1-CONSOLIDATE:** Fold `c01_brief_capture.py` into `c01/`.
- **B-S53-C2-SPEC-MOVE:** Move C2 spec from `docs/` to canonical archive.
- **B-S53-C7-LEGACY-DECISION:** Disposition of `c07_structural_grid.py`.
- **B-S53-PROVISIONAL-CLEANUP:** Delete `c10/__init__.PROVISIONAL_S53.py`.

My recommendation: **Option A or B**. The structural reconciliation is
done; the project needs ground-truth contact with real users (Option A
via architect review especially) and end-to-end runnability (Option B).

---

## 📁 Where everything is

| What | Where |
|---|---|
| This document | `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` (you're reading it) |
| Comprehensive component index | `00_START_HERE/COMPONENT_STATUS_S53.md` (read it second) |
| Project rules | `00_START_HERE/RULES_RAMALINGAM_FORMALIZED.md` |
| Three obligations + 5 anti-patterns | `00_START_HERE/THREE_OBLIGATIONS_AND_PATTERNS.md` |
| Master doc latest delta | `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md` |
| All spec docs | `02_specs_chronological/` (flat numbered + per-component folders + per-session folders) |
| Code archive per session | `03_code_chronological/` |
| Backlog | `04_backlog/` (most recent: `S48_critique_walk_backlog_delta.md` + S53 entries in COMPONENT_STATUS) |
| S53 three-checks | `05_integrity_check/S53_GAP_CHECK.md`, `S53_AUDIT_CHECK.md`, `S53_INTEGRITY_CHECK.md` |
| Runnable code | `06_upstream_codebase/buildemup/` |
| Components README | `06_upstream_codebase/buildemup/components/README.md` |
| C1 spec + design docs | `07_design_documents/` (includes Design Principles v3.1) |
| Raw session transcripts | `08_session_transcripts/` |
| Conversation artifacts | `09_conversation_artifacts/` |

---

## ✅ Prerequisites for S54

All carryforward from S50/S52, plus S53 reinforcement:

1. **Rule 7** (critique handling): web search mandatory on every critique walk.
2. **Rule 8** (LOCK authority = Ramalingam alone): never self-declare LOCK; always present as PROPOSED, await explicit "lock it."
3. **Rule 9.2** (always-file-backlog): when critique surfaces VALID-BUT-BACKLOG items, file them as B-NNN entries in `04_backlog/v0_2_backlog.md` immediately, no permission needed.
4. **Rule 10** (handoff bundle structure): 10-directory canonical layout; never invent new top-level directories.
5. **Rule 10.6** (three-check protocol): GAP + AUDIT + INTEGRITY checks mandatory before every handoff.
6. **Rule 10.6.1** (pre-touch inventory): before claiming credit for created/modified files, inventory the working tree at session start.
7. **Rule 10.7** (handoff timing): "hand off" → first response is status block + three-check **plan**; NO bundle assembly until Ramalingam confirms/corrects.
8. **Single-zip rule:** Every handoff is one zip file. No loose files alongside.
9. **Cumulative-handoff rule:** Every handoff is cumulative, not delta. Clone prior session's bundle, then layer this session's additions.
10. **Rule 11** (vigorous self-analysis + web research): on every spec/code creation, amendment, and critique walk.

---

## 🎓 Project context (for fresh sessions)

BuildEase† (placeholder name) is a decision-support engine for Indian
families building their own home. Mission: close information asymmetry
between homeowners and contractors in the Indian residential construction
market.

- **Solo founder:** Ramalingam, Tamil Nadu, India.
- **Live deployment:** buildease-production.up.railway.app
- **GitHub:** ramalingam38-rgb/buildease
- **17-component canonical architecture** (Track 3) is definitive.
- **Domain depth:** NBC 2016, IS 456/962/11268/13920, TNCDBR, city DCRs
  (Tamil Nadu, Mumbai, Delhi, Bangalore, Maharashtra, Hyderabad), BHK
  conventions, FAR, stilt mandates, plot rules, CBA verification, Vastu
  (excluded from logic but understood for users), BOQ, IFC.

The four phases of the pipeline:

1. **Understanding (C1–C4):** Brief capture, feasibility check, trade-off
   negotiation if infeasible, plot analysis.
2. **Generation (C5–C13):** Topology, orientation, structural grid,
   corridor, room size, wet zones, placement, vertical alignment, doors.
3. **Evaluation (C14–C16):** Connection graph, problem finder, dual drawings.
4. **Cost Transparency (C17):** Quote comparison.

C11a (Topology Mutation) and C11b (NSGA-II Refinement) sit between
generation and evaluation as iteration layers.

---

†= placeholder name marker. Final product name to be set later
("BuildEase" is the working name; "Archimind" is taken).

**Welcome to S54. Read `COMPONENT_STATUS_S53.md` next.**
