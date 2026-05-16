# C13 v1.0 LOCKED — Full Component Bundle

**Status (end of S45, including continuation through Sub-6):** v1.0 implementation complete.
LOCK candidacy gated on governance items (C14 v0.1 sketch + end-to-end examples
+ walk #6.5), not on C13 code.

**Test posture:** 3489 passed / 3 skipped / 0 failed.
**C13 test count:** 195 tests across 7 files.

---

## Directory layout

```
c13_bundle/
├── README.md                         (this file)
├── components/
│   └── c13/                          (15 production modules + __init__)
│       ├── __init__.py
│       ├── versioning.py             constants (C13_VERSION, MAX_DOORS_PER_ROOM_V1,
│       │                              DEFAULT_LEAF_THICKNESS_M, ...)
│       ├── errors.py                 LocalPlacementError / PerCandidatePlacementError
│       │                              hierarchy + concrete subclasses
│       ├── contracts.py              C13ConsumesFromC12Edge Protocol +
│       │                              C12V10EdgeAdapter
│       ├── schema.py                 Door, AdvisoryFlag, SuccessfulDoorPlacement,
│       │                              FailedDoorPlacement, FailureRecord,
│       │                              DoorPlacementBatchResult, RoomDoorPreference,
│       │                              ConditionalLegalityViolation, ...
│       ├── config.py                 DoorPlacementConfig
│       ├── cache_keys.py             build_c13_cache_keys() + helpers
│       ├── telemetry.py              6 event types + C13TelemetrySink protocol +
│       │                              NullTelemetrySink + InMemoryTelemetrySink
│       ├── edge_selection.py         Phase A (3-tier structural priority,
│       │                              NBC vetoes D11.1/D11.4, secondary doors)
│       ├── swing_assignment.py       Phase B (main-entry + bathroom + smaller-room
│       │                              rules + outswing advisory emission)
│       ├── position_selection.py     Phase C (corner_offset + grid snap)
│       ├── conflict_resolution.py    Phase D (CSP-lite swing-arc conflict
│       │                              resolution with mandatory convergence
│       │                              telemetry)
│       ├── assembly.py               Phase E (DoorState → Door schema, exactly-one
│       │                              is_main_entry marker, Inv D8 sort)
│       ├── verification.py           Phase F PURE VERIFICATION (Inv D13/D17/D11.3')
│       ├── orchestrator.py           place_doors() top-level entry point
│       │                              (wires A→B→C→D→E→F with strict/WARN dispatch)
│       └── provenance.py             place_doors_with_provenance() +
│                                      DoorPlacementProvenance + CandidateProvenanceEntry
└── tests/
    └── test_c13/                     (7 test modules + __init__)
        ├── __init__.py
        ├── test_c13_foundational_layer.py            77 unit tests
        ├── test_c13_phase_a_b_telemetry.py           28 unit tests
        ├── test_c13_phase_c_d.py                     20 unit tests
        ├── test_c13_phase_e_f_orchestrator.py        30 unit tests
        ├── test_c13_provenance.py                    22 unit tests
        ├── test_c13_property_based.py                29 PBTs (Hypothesis)
        └── test_c13_adversarial_integration_corpus.py 11 integration tests
                                                       (uses real C12 outputs)
```

---

## Code volume

- **Production:** 16 files, **5,820** lines (incl. `__init__.py`)
- **Tests:** 8 files (incl. `__init__.py`), **6,214** lines
- **Total:** 24 files, **12,034** lines

---

## Spec authority chain

C13 SPEC v1.0 LOCKED was reached through:
- v0.1 PROPOSED (initial draft — 17 invariants D1–D17, 6 phases A–F)
- v0.2 PROPOSED_DELTA (hinge_side, leaf_thickness, A6 bathroom outswing rule)
- v0.3 PROPOSED_DELTA (3-tier structural priority B6, secondary doors B8, B11 typestate)
- v0.4 PROPOSED_DELTA (mandatory PhaseDConvergenceEvent C5, NBC vetoes C2,
                       secondary-door eligibility C4, ≥27 PBT floor C3)
- v0.5 PROPOSED_DELTA (D11.3' narrowing, D17 primary-reachability for habitable rooms)
- v0.6 PROPOSED_DELTA (constraint classification E1, composability validation E2,
                       fast-revision window E4, adversarial integration corpus
                       B-C13-ADVERSARIAL-INTEGRATION-CORPUS)
- v0.7 PROPOSED_DELTA (F1 Phase F PURE VERIFICATION discipline, Inv D22)
- v1.0 LOCKED (consolidated; 90-day fast-revision window active)

---

## Invariants enforced (D1–D22)

| Inv | Description | Enforced by |
|-----|-------------|-------------|
| D1' | Every room has ≥1 door (relaxed from D1 via RoomDoorPreference) | Phase A + orchestrator |
| D4  | Door fits within edge (position + width ≤ overlap_length) | Phase C |
| D5  | No overlapping swing arcs (APPROXIMATE predicate at v1) | Phase D |
| D6  | Exactly one is_main_entry door | Phase E + SuccessfulDoorPlacement |
| D7  | Byte-equal replay determinism | All phases (canonical sorts, lex BFS) |
| D8  | Doors sorted lex-ASC by (room_a, room_b) | Phase E |
| D9' | Bathroom outswing emits EMERGENCY advisory | Phase B |
| D10 | clear_width ≤ 1.5m sanity bound | Door __post_init__ |
| D11.1 | No bathroom-to-kitchen door | Phase A NBC veto |
| D11.2 | No bathroom-bedroom direct door (deferred to Phase F adjacency lookup) | (backlog: B-C13-D11_2-PBT) |
| D11.3' | Kitchen-transit conditional legality (alternate-route detection) | Phase F |
| D11.4 | Master bedroom primary not to kitchen/bathroom | Phase A NBC veto |
| D12 | Phase D iteration budget bound | Phase D |
| D13 | Full reachability via door-induced graph | Phase F |
| D14 | GeometricFidelity.APPROXIMATE at v1 | Phase E |
| D16 | Advisory density ≤ n_rooms × 1.5 | (default-enforced) |
| D17 | Primary-door-only reachability for habitable rooms | Phase F |
| D19 | ConditionalLegalityViolation provenance required | FailureRecord __post_init__ |
| D22 | Phase F side-effect-free | verify() contract |

---

## Public API surface

```python
from buildemup.components.c13 import (
    # Top-level entry points
    place_doors,                    # standard
    place_doors_with_provenance,    # with operational metadata

    # Config + sinks
    DoorPlacementConfig,
    C13TelemetrySink,
    NullTelemetrySink,
    InMemoryTelemetrySink,

    # Result schema
    DoorPlacementBatchResult,
    SuccessfulDoorPlacement,
    FailedDoorPlacement,
    Door,
    AdvisoryFlag,
    FailureRecord,
    ConditionalLegalityViolation,

    # Provenance
    DoorPlacementProvenance,
    CandidateProvenanceEntry,

    # Per-phase entry points (testable in isolation)
    select_edges,        # Phase A
    assign_swings,       # Phase B
    assign_positions,    # Phase C
    resolve_conflicts,   # Phase D
    assemble_doors,      # Phase E
    verify,              # Phase F

    # Constants
    C13_VERSION, C13_EDGE_PROTOCOL_VERSION, ADVISORY_SCHEMA_VERSION,
    MAX_DOORS_PER_ROOM_V1, HABITABLE_ROOM_CATEGORIES,
    DEFAULT_LEAF_THICKNESS_M, DEFAULT_CORNER_OFFSET_M, DEFAULT_GRID_SNAP_M,
)
```

---

## Filed backlog items surfaced during build

| ID | Description | Effort | Routed to |
|----|-------------|--------|-----------|
| B-C13-LEAF-THICKNESS-CONFIGURABLE | leaf_thickness_m configurable per DoorPlacementConfig | S | C13 v1.x |
| B-C13-PROVENANCE-SPLIT | Split provenance into Replay + Operational + Diagnostic | M | C13 v1.x |
| B-C13-D11_2-PBT | PBT for D11.2 (bathroom-bedroom direct door) | S | C13 v1.x |
| B-C13-D11_3-PBT | PBT for D11.3' (Hypothesis-friendly topology generator) | M | C13 v1.x |
| B-C13-D12-PBT-VALUE-ASSESSMENT | Decide if D12 needs Hypothesis PBT (covered by unit test) | S | C13 v1.x |
| B-C12-EDGE-DENSITY | C12 slicing-tree should optionally bias for shared-edge density | M | C12 maintainer (post-LOCK) |

---

## Bug fixed during integration corpus build

`orchestrator.py::_classify_error_phase()` was defaulting `DoorPositionInfeasibleError`
to `phaseC` regardless of origin. The corpus showed that C12's sparse-edge outputs
trigger Phase A's `DoorPositionInfeasibleError` ("entry room has no feasible shared
edge"), which was being mis-attributed to Phase C. Fixed by parsing the error message
prefix tag ("Phase A:" / "Phase C:") which both raise sites populate by convention.

---

## Files NOT in this bundle (but referenced by C13)

- `buildemup/components/c12/` — upstream C12 (SharedEdge, PlacedCandidate, PlacementConfig)
- `buildemup/components/c11b/` — further upstream
- Spec files: `spec_C13_v0_1_PROPOSED.md` through `spec_C13_v1_0_LOCKED.md` (in the
  handoff bundle's `02_specs_chronological/S44_continuation_C13_specs/`)

To run the test suite, this bundle needs to be merged back into a working tree
that also has C12 + the buildemup package layout.
