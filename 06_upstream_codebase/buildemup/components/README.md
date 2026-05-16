# `components/` — BuildemUp 17-Component Architecture (Track 3 Canonical)

This directory contains every component of the 17-component canonical architecture.
Each component has its own folder (`c01/` through `c17/`, with C3 split into `c03a/`+`c03b/`
and C11 split into `c11a/`+`c11b/` — 19 folders for 17 architectural components).

**State at S53 close:** All 17 components have their LOCKED code present at the
canonical path. The full test suite runs end-to-end (4,268 passing).

---

## How to read each component folder

Real LOCKED contracts live at the canonical path: `cNN/contracts.py` (or
exposed via `cNN/__init__.py`, depending on the component's structure).

Some folders also contain `_c3b_shim.py` — these are **simplified contract shims**
written during S52 to give C3b a minimum import surface without requiring the
full upstream component to be loaded. C3b imports from `_c3b_shim`, no other
component does. This isolation is intentional and version-pinned
(`{COMPONENT}_STUB_VERSION = "vX.Y.LOCKED.stub.S52"`).

When a downstream component needs the real LOCKED contract, it imports from
`cNN.contracts` (or the package's public `__init__`) directly. C3b is the only
consumer that uses the shim.

---

## Component status (S53 close)

| # | Folder | LOCKED at | Real code | Shim | Notes |
|---|---|---|---|---|---|
| C1 | `c01/` + `c01_brief_capture.py` | v0.9.3 | ✅ | — | Legacy hybrid layout |
| C2 | `c02/` | v0.1 | ✅ | — | |
| C3a | `c03a/` + `c03a_extreme_case_gate.py` | v0.2.1a | ✅ (9 modules) | ✅ | Restored S53 |
| C3b | `c03b/` | v0.7 (S52) | ✅ | — | Freshest LOCK; 464-test suite |
| C4 | `c04/` | v1.0 | ✅ (7 modules) | ✅ | Restored S53 |
| C5 | `c05/` | v0.9 | ✅ | — | |
| C6 | `c06/` | v0.6 | ✅ | — | |
| C7 | `c07/` + `c07_structural_grid.py` | v0.8 | ✅ (8 modules) | ✅ | Restored S53 from `c7_complete_bundle.zip` |
| C8 | `c08/` | v0.5 | ✅ | — | |
| C9 | `c09/` | v0.7 | ✅ | — | |
| C10 | `c10/` | v1.0 (S36) | ✅ (11 modules) | ✅ | LOCKED `__init__.py` active |
| C11a | `c11a/` | v1.0 | ✅ | — | |
| C11b | `c11b/` | v1.1 | ✅ | — | |
| C12 | `c12/` | v1.0 (S44) | ✅ (17 modules + slicing_kd_tree/) | ✅ | Restored S53 |
| C13 | `c13/` | v1.0 (S45) | ✅ (16 modules) | ✅ | Restored S53 |
| C14 | `c14/` | v0.2 (S47) | ✅ (14 modules) | — | Specs added S53 |
| C15 | `c15/` | v1.0 | ✅ | — | |
| C16 | `c16/` | v1.2 | ✅ | — | |
| C17 | `c17/` | v0.3 | ✅ | — | |

---

## C7 modular structure (post-S36 amendment)

The C7 folder contains 8 modules + `__init__.py`:

| Module | LOC | Purpose |
|---|---|---|
| `wall_segment.py` | 185 | `WallAxis`, `WallTag`, `WallSegment`, `WALL_AXIS_CANONICAL_ORDER`, `WALL_ORDER_CONVENTION`, `serialize_tags_sorted` |
| `grid_generator.py` | 501 | `Grid`, `ColumnPosition`, `GridGenerator`, `Staircase`, `validate_staircase_clearance`, `MIN_STAIRCASE_LANDING_DEPTH_M` (W9 amendment from S38) |
| `frame_sanity.py` | 445 | Frame-level structural sanity checks |
| `foundation_engine.py` | 291 | Foundation type selection (5 types) + IS 2911 pile sizing |
| `structural_sizer.py` | 388 | Column/beam/slab sizing per IS 456 |
| `load_combinations.py` | 207 | IS 875 + IS 1893 load combinations |
| `global_stability.py` | 474 | Global stability + irregularity classification |
| `cost_estimator.py` | 184 | Per-element cost rolled up from KB rates |
| `__init__.py` | — | Re-exports per C7 v0.8 LOCKED spec |

The top-level `components/c07_structural_grid.py` (951 LOC) is the legacy
pre-amendment monolithic file. Retained for backwards reference; no production
code imports from it. Cleanup decision pending (B-S53-C7-LEGACY-DECISION).

---

## Stub-shim pattern (canonical, S52+)

The `_c3b_shim.py` pattern was introduced at S52 to let C3b build against
minimal contract types while the upstream tree was being assembled. Pattern
rules:

- The shim file is named `_c3b_shim.py` (underscore prefix = internal/non-public).
- The real contracts live at the canonical `contracts.py` path (or are exposed
  via the package's public `__init__`, depending on the component).
- C3b imports from `_c3b_shim`, no other component does.
- The shim's exported types may DIFFER from the real contracts in surface
  (the shim is a simplified view; the real contract is per the LOCKED spec).
- Shim files self-identify with a version constant:
  `{COMPONENT}_STUB_VERSION: Final[str] = "vX.Y.LOCKED.stub.S52"`.

If you find yourself wanting to delete a `_c3b_shim.py`, you also need to
update C3b's import surface (`c03b/contracts.py` and `tests/test_c03b/fixtures.py`)
to import from the real `contracts.py` or `__init__.py` instead. This is a
non-trivial change because the shim types are simplified — see C13's case
where the shim has `DoorPlacement` but the real spec has
`SuccessfulDoorPlacement`/`FailedDoorPlacement`.

---

## Audit-trail files (S53 reconciliation provisional)

- `c10/__init__.PROVISIONAL_S53.py` — provisional `__init__.py` used while
  C7's `wall_segment.py` was missing. The current `c10/__init__.py` is the
  LOCKED version. Safe to delete at S54 after rollback period (B-S53-PROVISIONAL-CLEANUP).

---

## Where the LOCKED specs live

All LOCKED + PROPOSED spec docs for the architectural components are in
`02_specs_chronological/` at the bundle root. See `00_START_HERE/COMPONENT_STATUS_S53.md`
for a canonical-order index of every component's spec doc paths and code paths.

---

*Authored S53 by Claude after the reconciliation pass that restored C3a, C4,
C7, C10, C12, C13 to canonical paths. C7 gap closed by `c7_complete_bundle.zip`
upload; tests went from 750 passing to 4,268 passing.*
