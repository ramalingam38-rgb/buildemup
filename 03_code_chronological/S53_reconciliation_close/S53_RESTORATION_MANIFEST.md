# S53 Restoration Manifest

**Date:** May 16, 2026
**Session:** S53 (reconciliation pass)
**Purpose:** Record what S53 restored/installed to the upstream tree

---

## Component code installed at canonical paths

### C3a (from buildemup_c3a_complete.zip upload)
- `06_upstream_codebase/buildemup/components/c03a/` — 9 modules:
  brief_change_apply.py, counterfactual.py, detector.py, error_formatter.py,
  gate_state.py, gate_termination.py, option_generator.py, preflight.py,
  __init__.py
- `06_upstream_codebase/buildemup/components/c03a_extreme_case_gate.py`
- `06_upstream_codebase/buildemup/api/c3a_*.py` — 5 API endpoints
- `06_upstream_codebase/buildemup/static/c3a/` — 11 UI files
- `06_upstream_codebase/buildemup/tests/test_c03a_session*.py` — 23 test files

### C4 (from 03_code_chronological/C4_final_shipped_files/)
- `06_upstream_codebase/buildemup/components/c04/` — 7 modules:
  climate_zone.py, neighbour_context.py, plot_analysis.py, schema.py,
  soil_estimator.py, sun_path.py, __init__.py

### C7 (from c7_complete_bundle.zip + S38_code/)
- `06_upstream_codebase/buildemup/components/c07/` — 8 LOCKED modules:
  wall_segment.py (185 LOC, from bundle),
  grid_generator.py (501 LOC, from S38_code/ for W9 staircase amendment),
  frame_sanity.py (445 LOC, from bundle),
  foundation_engine.py (291 LOC, from bundle),
  structural_sizer.py (388 LOC, from bundle),
  load_combinations.py (207 LOC, from bundle),
  global_stability.py (474 LOC, from bundle),
  cost_estimator.py (184 LOC, from bundle),
  __init__.py (from bundle)

### C10 (from c10_c12_c13_c14_components.zip upload)
- `06_upstream_codebase/buildemup/components/c10/` — 11 modules:
  assignment.py, clustering.py, errors.py, kb_validator.py, occupancy.py,
  provenance.py, schema.py, scoring.py, trap_arm.py, wet_zone_planner.py,
  __init__.py
- `06_upstream_codebase/buildemup/kb/plumbing_minimums.json`
- `06_upstream_codebase/buildemup/kb/plumbing_minimums_v2.json`
- `06_upstream_codebase/buildemup/kb/plumbing_fixture_profiles.json`
- `06_upstream_codebase/buildemup/kb/plumbing_fixture_profiles_v2.json`
- `06_upstream_codebase/buildemup/tests/test_c10/` — 7 test files

### C12 (from c10_c12_c13_c14_components.zip upload)
- `06_upstream_codebase/buildemup/components/c12/` — 17 modules + slicing_kd_tree/ subpackage
- `06_upstream_codebase/buildemup/tests/test_c12/` — 8 test files

### C13 (from S45_C13_v1_0_SHIPPED.zip + bundle upload)
- `06_upstream_codebase/buildemup/components/c13/` — 16 modules
- `06_upstream_codebase/buildemup/tests/test_c13/` — 7 test files

---

## Stub-shim files preserved per S52 pattern

Each of these components has both the real LOCKED contract AND a `_c3b_shim.py`
preserving the simplified contract surface that C3b imports from:

- `c03a/_c3b_shim.py`
- `c04/_c3b_shim.py`
- `c07/_c3b_shim.py` (formerly `c07/contracts.py`)
- `c10/_c3b_shim.py`
- `c12/_c3b_shim.py`
- `c13/_c3b_shim.py`

---

## Audit-trail files

- `c10/__init__.PROVISIONAL_S53.py` — provisional `__init__.py` used briefly
  during S53 before C7's wall_segment.py arrived. Safe to delete at S54
  (B-S53-PROVISIONAL-CLEANUP).

---

## Documentation authored

- `00_START_HERE/COMPONENT_STATUS_S53.md`
- `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` (S54 entry-point)
- `01_master_doc/MASTER_DOC_v3_16_TO_v3_17_DELTA.md`
- `04_backlog/backlog_session_53.md`
- `05_integrity_check/S53_GAP_CHECK.md`
- `05_integrity_check/S53_AUDIT_CHECK.md`
- `05_integrity_check/S53_INTEGRITY_CHECK.md`
- `06_upstream_codebase/buildemup/components/README.md`
- `03_code_chronological/S53_reconciliation_close/S53_RESTORATION_MANIFEST.md` (this file)

---

## Spec docs filed (moved from working tree to canonical archive)

- `spec_C12_v0_1_PROPOSED.md` through `spec_C12_v1_0_LOCKED.md` (7 files) → `02_specs_chronological/C12_v1_0_LOCKED/`
- `spec_C13_v0_1_PROPOSED.md` through `spec_C13_v1_0_LOCKED.md` (8 files) → `02_specs_chronological/C13_v1_0_LOCKED/`
- `spec_C8_AMENDMENT_corridor_zones_v0_1.md` → `02_specs_chronological/C8_AMENDMENT_corridor_zones/`
- `spec_C9_AMENDMENT_adjacency_hints_v0_1.md` → `02_specs_chronological/C9_AMENDMENT_adjacency_hints/`
- `v0_2_backlog_S42_critique_walk_additions.md` → `04_backlog/`
- `v0_2_backlog_S44_C12_critique_walk_additions.md` → `04_backlog/`

C3a, C14 spec docs newly filed in `02_specs_chronological/C3a_v0_2_1a_LOCKED/`
and `02_specs_chronological/C14_v0_2_LOCKED/` respectively.

---

## Test posture

- Before S53: 464 passing (C3b only)
- After S53: 4,268 passing, 6 skipped, 0 failed, 4,274 collected

Test command:
```bash
cd 06_upstream_codebase/buildemup/tests
PYTHONPATH=/home/claude/work/06_upstream_codebase/buildemup:/home/claude/work/06_upstream_codebase \
  python3 -m pytest -q --no-header
```
