# S45_C13_v1_0_SHIPPED — README

**Session:** S45 (BuildemUp, this iteration)
**Status:** C13 v1.0 IMPLEMENTATION LOCKED by Ramalingam at S45 close (per `"Lock this build and let's move on to c14 spec doc"`).
**Date:** S45 close, immediately preceding S46.

---

## What was shipped

C13 v1.0 implementation — full code following the spec LOCKED at S44 (path c).

### Production code (16 modules)
Location: `06_upstream_codebase/buildemup/components/c13/`

| Module | Purpose |
|---|---|
| `__init__.py` | Public exports |
| `assembly.py` | Phase E: DoorState → Door, is_main_entry marker, Inv D8 sort |
| `cache_keys.py` | Cache key composition (geometry + advisory + full) |
| `config.py` | DoorPlacementConfig dataclass + validation |
| `conflict_resolution.py` | Phase D: door conflict resolution with telemetry |
| `contracts.py` | C13ConsumesFromC12Edge Protocol + EXTERNAL placeholder |
| `edge_selection.py` | Phase A: shared-edge → candidate door selection |
| `errors.py` | Two-tier error hierarchy (Local / PerCandidate) |
| `orchestrator.py` | Top-level `place_doors()` + batch result assembly |
| `position_selection.py` | Phase B: door position on selected edge |
| `provenance.py` | `place_doors_with_provenance()` + DoorPlacementProvenance |
| `schema.py` | Door + SuccessfulDoorPlacement + FailedDoorPlacement |
| `swing_assignment.py` | Phase C: door swing direction |
| `telemetry.py` | Event types + Sink Protocol + Null/InMemory impls |
| `verification.py` | Phase F: PURE VERIFICATION (Inv D13 + D17 + D11.3') |
| `versioning.py` | Version constants + DEFAULT_LEAF_THICKNESS_M |

Total production: ~5,820 lines.

### Tests (7 modules)
Location: `06_upstream_codebase/buildemup/tests/test_c13/`

| Test module | Coverage | Test count |
|---|---|---|
| `test_c13_foundational_layer.py` | Schema, errors, contracts, versioning | 77 |
| `test_c13_phase_a_b_telemetry.py` | Edge selection + position + telemetry | 28 |
| `test_c13_phase_c_d.py` | Swing assignment + conflict resolution | 20 |
| `test_c13_phase_e_f_orchestrator.py` | Phase E + F + orchestrator | 30 |
| `test_c13_provenance.py` | Provenance + replay determinism | 22 |
| `test_c13_property_based.py` | Hypothesis PBT, 29 tests | 29 |
| `test_c13_adversarial_integration_corpus.py` | REAL C12 → C13 pipeline | 11 |

**Total C13 tests: 217.**

### Test posture at S45 close

- **3489 passed / 3 skipped / 0 failed** (baseline 3272 at S44 close; +217 contributed by C13)
- Full pytest run: ~85 seconds

### LOCK invariants (per the LOCKED v1.0 spec)

23 invariants D1-D23 organized in 6 categories:
- HARD_LEGALITY (D1-D5, D11.1)
- CONDITIONAL_LEGALITY (D11.2, D11.3')
- DETERMINISM (D7, D9, D10, D16, D22)
- GRAPH_INTEGRITY (D6, D8, D13, D17)
- GEOMETRY (D12, D14, D15)
- ADVISORY_HYGIENE (D18-D23)

Phase F is PURE VERIFICATION per Inv D22.

### Adversarial corpus findings (filed as backlog)

- **B-C12-EDGE-DENSITY** — Routed to C12 maintainer: C12's slicing_kd_tree typically produces ZERO shared edges in multi-room layouts (rooms placed at non-contiguous corner anchors). C13 surfaces this cleanly as DoorPositionInfeasibleError. Does NOT block C13 LOCK. **This affects downstream C14 + C15 integration testing.**
- **B-C13-STRUCTURAL-PHASE-TAGGING** — `_classify_error_phase()` uses message-prefix introspection; should be structurally tagged in v1.x.

---

## How to consume this in S47 (C14 + C15 implementation)

The C13 module is importable as-is. Public API:

```python
from buildemup.components.c13 import (
    place_doors,
    place_doors_with_provenance,
    DoorPlacementBatchResult,
    SuccessfulDoorPlacement,
    FailedDoorPlacement,
    Door,
    DoorPlacementConfig,
)
```

C14 will consume `DoorPlacementBatchResult.successful: tuple[SuccessfulDoorPlacement, ...]` per the C14 v0.2 LOCKED spec.

When C12 → C13 corpus testing surfaces the B-C12-EDGE-DENSITY issue, the C14/C15 integration tests should use either:
- Hub-and-spoke fixture topology (assumes C12 emits shared edges, which it currently doesn't for multi-room) — OR
- Synthesized SuccessfulDoorPlacement directly, bypassing real C12 → C13 for the first integration pass

---

## Files in this directory

- `c13_v1_0_bundle_s45.zip` (120 KB) — packaged deliverable from S45 close. Contains a copy of all C13 production + test files for traceability. **The authoritative source is `06_upstream_codebase/buildemup/components/c13/` and `06_upstream_codebase/buildemup/tests/test_c13/`.**
- `C13_README_from_bundle.md` — the README that shipped with the bundle.
- `README.md` — this file.

---

## Critique walks completed

The C13 v1.0 spec went through walks #1-#8 across S43-S44. C13 v1.0 implementation went through walk #1 (post-build, at S45 close) which produced 11 backlog items (already in `04_backlog/`) but **0 VALID-AS-PATCH structural amendments** — the post-implementation review concluded "architecturally coherent, internally disciplined, strongly tested, governance-aware, implementation-ready" and recommended path (a) "stop abstract refinement, begin integration."

Ramalingam locked at this point.
