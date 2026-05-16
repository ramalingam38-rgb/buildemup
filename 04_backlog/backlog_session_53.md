# Backlog Session 53 — Reconciliation Pass Additions

**Session:** S53
**Date:** May 16, 2026
**Source:** S53 reconciliation pass that restored C3a/C4/C7/C10/C12/C13 LOCKED code to canonical paths

---

## Closed in S53

### B-S53-C7-WALL-SEGMENT-RESTORE ✅ CLOSED
- **Description:** Restore `c07/wall_segment.py` and modular `c07/grid_generator.py` to canonical paths.
- **Origin:** Discovered at S53 mid-session when C10 LOCKED `__init__.py` imports failed.
- **Resolution:** Installed 8 LOCKED modules from `c7_complete_bundle.zip`; `grid_generator.py` sourced from `03_code_chronological/S38_code/` (501 LOC with W9 staircase amendment) rather than the bundle's S36 v0.8 version (301 LOC).
- **Impact:** Unblocked C10's full LOCKED contract + C11a staircase operators. Test count went from 750 to 4,268.

### B-S53-C10-INIT-RESTORE ✅ CLOSED
- **Description:** Once C7 gap closed, restore C10's LOCKED `__init__.py` (preserved as `__init__.LOCKED.py` during the gap window).
- **Resolution:** Rename complete; LOCKED `__init__.py` active; provisional preserved as `__init__.PROVISIONAL_S53.py` for audit trail.

---

## Opened in S53 (carry to S54)

### B-S53-C2-SPEC-MOVE (Cosmetic — Low priority)
- **Description:** Move C2 spec docs from `06_upstream_codebase/buildemup/docs/` to canonical `02_specs_chronological/`.
- **Origin:** Per Rule 10, working tree should not contain spec docs.
- **Effort:** Trivial (file move + verify no broken references).
- **Trigger:** S54 cleanup pass if Ramalingam chooses Option E.

### B-S53-C1-CONSOLIDATE (Cleanup — Low priority)
- **Description:** Fold `c01_brief_capture.py` (top-level legacy orchestrator) into `c01/` folder.
- **Origin:** Legacy hybrid layout from before component folders were standardized.
- **Effort:** S–M. Need to verify nothing imports from the top-level path.
- **Risk:** If anything in `api/` or `tests/` imports `c01_brief_capture` directly, those imports must be updated.

### B-S53-C7-LEGACY-DECISION (Decision needed — Medium priority)
- **Description:** Decide fate of `06_upstream_codebase/buildemup/components/c07_structural_grid.py` (951 LOC pre-amendment monolithic file).
- **Options:**
  - **(a) Delete** — fully superseded by modular `c07/` folder; no production code imports from it.
  - **(b) Move to `09_conversation_artifacts/`** — keep as historical reference.
  - **(c) Move to `03_code_chronological/legacy/`** — same idea, different folder.
- **Effort:** Trivial.
- **Trigger:** Ramalingam decision required.

### B-S53-PROVISIONAL-CLEANUP (S54 trivial)
- **Description:** Delete `06_upstream_codebase/buildemup/components/c10/__init__.PROVISIONAL_S53.py` audit-trail file after S54 rollback safety period.
- **Trigger:** S54 close if no rollback needed.

### B-S53-TEST-DIRS-MISSING (Style — Low priority)
- **Description:** Reorganize test files for C4/C5/C6/C8/C9 into per-component `tests/test_cNN/` directories. Currently they live as flat-file `test_cNN_*.py` files in `tests/`.
- **Origin:** Inconsistent test layout across the project (C3b, C10, C11a, C11b, C12, C13, C14 use per-component dirs; older components use flat layout).
- **Effort:** S–M.
- **Risk:** May break pytest collection if not done carefully.

---

## Pre-existing pre-launch hard gates (unchanged from prior sessions)

These remain open and are the recommended priority for S54+:

- **B-220 (hydraulics):** Plumbing engineering depth — extend C10 with real hydraulic calculation, not just chase routing.
- **B-237 (cross-platform CI):** Verify the project runs on Mac/Windows/Linux reliably.
- **B-238 (architect review):** Get a licensed Indian architect to review BuildEase output. Cannot be done by Claude alone.
- **B-150-equiv (NBC primary verification):** Verify code citations against actual NBC 2016 text.

---

## Pre-existing component backlogs (unchanged)

- **B-NEW-P-runtime-audit:** Post-launch audit of severity_tier classifier.
- **B-NEW-P-enum:** Post-launch — convert severity_tier from Literal to enum.
- **B-NEW-P-c7classes:** S–M effort — add severity_tier to C7 error classes.
- **B-NEW-J-override:** Launch-complement, must ship same release as C11a production.
- **B-NEW-J-roomlevel, B-NEW-J-acoustic:** Post-launch.
- **B-C12-EDGE-DENSITY:** C12 slicing-tree should optionally bias for shared-edge density.
- **B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT:** HIGH priority routed amendment to C12 v1.1.
- **B-C13-INVARIANT-TAXONOMY-GROUPING:** v1.x polish (3 walks deep).
- **B-C13-ADVERSARIAL-INTEGRATION-CORPUS:** Walk #6 item.
- **B-C14-LAYOUT-QUALITY-BAND:** Spec item.
- **B-C3B-EXPERIENTIAL-CONTINUITY-ISOVIST-COMPUTATION:** Awaiting Ramalingam input.
- **B-C3B-LATENCY-TELEMETRY-FIRST:** Round-2 backlog.
- **B-241:** CI lint rule preventing C7 production code from importing `buildemup.utilities` (post v1).

Full historical lineage in `04_backlog/backlog_session_*.md` and the v0_2_backlog files.
