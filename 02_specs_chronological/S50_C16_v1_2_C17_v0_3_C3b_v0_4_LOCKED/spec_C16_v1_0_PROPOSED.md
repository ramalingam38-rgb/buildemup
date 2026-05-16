# C16 — Dual-Drawing Renderer
## Spec v1.0 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v1.0 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Composed from:** v0.5 LOCKED + Sub-2 build surfacing + critique walk.
**Session:** S49.
**Predecessor LOCKED:** v0.5 LOCKED (S47).

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone. This document
> is PROPOSED only. Do not interpret as locked until Ramalingam
> explicitly states "v1.0 LOCKED".

---

## § 0 — Composition rationale

C16 v0.5 was LOCKED at S47 deliberately leaving sub-envelope field lists
as SKETCH (tracked by `B-C16-ENVELOPE-SCHEMA-LOCK`, LOCK-mandatory at
v1.0). The plan was: build the 6 phases against the SKETCH; let the
build surface what each phase actually needs from each sub-envelope;
pin the fields at v1.0 LOCK.

Sub-2 (S49) completed that build. This v1.0 PROPOSED spec:

1. **Adopts** v0.5 LOCKED verbatim for everything that was already pinned
   (R1–R34 invariants, AuthorityKind discipline, presentation/canonical
   signature separation, etc.).
2. **Pins** the sub-envelope field lists exactly as built and tested
   (§ 3 below).
3. **Records** the documented behaviors and stubs that ship under v1.0
   (§ 5 below — what we accept as v1.0-acceptable limits).
4. **Lists** the v1.0 backlog items closed and the ones explicitly
   deferred post-LOCK (§ 12 below — per Rule 9).

---

## § 1 — v0.5 LOCKED carried forward unchanged

All of the following remain LOCKED as in v0.5:

- **§ 1 Scope** — C16 produces a `DualDrawingBundle` per `SelectionResult`:
  one `WorkingDrawingModel` + one `PermitDrawingModel`, plus signatures.
- **§ 2 Phase set** — α envelope, β scheduling, γ working, δ permit,
  ε attestation, ζ bundle.
- **§ 4 Error tiers** — `LocalDrawingError` (always halts) and
  `PerLayoutDrawingError` (STRICT raises / WARN collects).
- **§ 5 Versioning** — `C16_VERSION = "v0.5.LOCKED"` for backwards
  binding-stability across the v0.5 → v1.0 transition. The product
  emits `"v0.5.LOCKED"` at runtime; v1.0 is the spec composition
  version, not the product version.
- **§ 6 Hard ceilings** — plot ±1km, building ±500m, local frame ±50m.
- **§ 8 R-invariants R1–R34** — all carried forward (with refined
  enforcement points documented in § 4 below).

---

## § 2 — Output contract (unchanged)

`render_drawings(...)` returns `SuccessfulDrawingRender | FailedDrawingRender`.

`render_drawings_batch(...)` returns `DrawingRenderBatchResult` with
`successes` and `failures` tuples (both sorted lex-ASC).

`DualDrawingBundle` carries:

- `source_selection_signature: str`
- `selection_audit_metadata: SelectionAuditMetadata`
- `c16_version: str`
- `c16_drawing_schema_version: int` (now 13 — see § 6)
- `jurisdiction_profile_id: str`
- `declared_domain_scope: str`
- `floor_geometries: tuple[FloorGeometry, ...]`
- `local_building_frame: LocalBuildingFrame`
- `geospatial_reference: GeospatialReference`
- `working_drawing_model: WorkingDrawingModel`
- `permit_drawing_model: PermitDrawingModel`
- `upstream_advisory_flags: tuple[AdvisoryFlag, ...]`
- `cache_keys: C16CacheKeys`
- `canonical_replay_signature: str` (R7 byte-equal)
- `presentation_signature: str` (R32a — canonical as prefix)
- `schema_descriptor_digest: str` (R26b)
- `phase_timings: PhaseTimings | None` (observability, excluded from cache)
- `readability_diagnostics: ReadabilityDiagnostics | None` (observability)

R20 / R24a / R24b / R24c / R33b enforced at `__post_init__`.

---

## § 3 — Sub-envelope field PINNING (B-C16-ENVELOPE-SCHEMA-LOCK closure)

This section closes the LOCK-mandatory item from v0.5 by pinning every
sub-envelope field list. ADDITIVE bump per R9 → schema_version = 13.

### 3.1 — Geometry types (in `LocalBuildingFrame` mm coords)

**`RoomGeometry`** (one room placed)
```
identity:    ElementIdentity   # R7b two-tier (semantic = geom-only)
room_id:     str
category:    str               # canonical category string from C12
x_mm:        int               # LocalBuildingFrame SW-origin
y_mm:        int
width_mm:    int
depth_mm:    int
```

**`WallSegment`** (perimeter from C7, internal from C12 SharedEdge)
```
identity:     ElementIdentity
wall_id:      str
element_kind: ElementKind      # WALL_EXTERNAL / WALL_INTERNAL_PARTITION /
                                # WALL_INTERNAL_LOAD_BEARING
start_x_mm:   int
start_y_mm:   int
end_x_mm:     int
end_y_mm:     int
```

**`DoorGeometry`** (from C13 Door + matching C12 SharedEdge)
```
identity:           ElementIdentity
door_id:            str
room_a_id:          str
room_b_id:          str
axis:               Literal["vertical", "horizontal"]
anchor_x_mm:        int        # door anchor in LocalBuildingFrame
anchor_y_mm:        int
clear_width_mm:     int
swing_direction:    Literal["into_room_a", "into_room_b"]
hinge_side:         Literal["start", "end"]
leaf_thickness_mm:  int
is_main_entry:      bool       # R29 hierarchy step 2 input
element_kind:       ElementKind  # DOOR_INTERNAL or DOOR_EXTERNAL
```

**`WindowGeometry`** (v1: empty — `B-C16-WINDOW-UPSTREAM-CONTRACT`)
```
identity:       ElementIdentity
window_id:      str
wall_id:        str
center_x_mm:    int
center_y_mm:    int
width_mm:       int
sill_height_mm: int
head_height_mm: int
element_kind:   ElementKind     # WINDOW_EXTERNAL
```

**`ColumnGeometry`** (from C7 ColumnPosition)
```
identity:     ElementIdentity
column_id:    str               # C7's grid_label (e.g. "A1")
x_mm:         int
y_mm:         int
width_mm:     int               # cross-section width
depth_mm:     int               # cross-section depth
on_perimeter: bool
```

Cross-section default 230×230 mm at v1.0 (Indian RCC G+0 standard).

**`PlumbingStack`** (from C10 RiserGroup + RiserAnchor)
```
identity:        ElementIdentity
stack_id:        str             # C10 RiserGroup.group_id
element_kind:    ElementKind     # PLUMBING_STACK_FRESH_WATER (v1 default)
x_mm:            int
y_mm:            int
wall_id:         str             # wall the stack is anchored to
serves_room_ids: tuple[str, ...] # C10 wet_room_ids, lex-ASC sorted
```

### 3.2 — Working-drawing primitives

**`SectionView`** (R23 cut)
```
identity:         ElementIdentity
section_id:       str
cut_type:         Literal["entry", "staircase", "wet_zone"]
floors_traversed: tuple[int, ...]
axis:             Literal["vertical", "horizontal"]
cut_position_mm:  int             # absolute LocalBuildingFrame coord
offset_mm:        int = 0         # R23 v0.2 A8 fallback magnitude
```

**`Elevation`**
```
identity:     ElementIdentity
elevation_id: str
facade_axis:  Literal["north", "south", "east", "west"]
width_mm:     int
height_mm:    int
```

**`RoofPlan`**
```
identity:           ElementIdentity
outline_x_mm:       int
outline_y_mm:       int
outline_width_mm:   int
outline_depth_mm:   int
drainage_slope_pct: float = 1.0   # NBC ≥ 1% for flat roofs
```

**`KeyPlan`**
```
identity:        ElementIdentity
floor_count:     int
site_outline_mm: tuple[int, int, int, int]
```

**`SitePlan`**
```
identity:                ElementIdentity
plot_x_mm:               int
plot_y_mm:               int
plot_width_mm:           int
plot_depth_mm:           int
building_footprint_xywh: tuple[int, int, int, int]
```

### 3.3 — Schedules

**`DoorScheduleEntry`** — door_identity, schedule_id, door_number,
width_mm, height_mm (default 2100), material (default "wood").

**`WindowScheduleEntry`** — window_identity, schedule_id, window_number,
width_mm, height_mm, material (default "aluminium"). v1 empty per
B-C16-WINDOW-UPSTREAM-CONTRACT.

**`FinishScheduleEntry`** — room_identity, schedule_id, floor_finish,
wall_finish, ceiling_finish. Per-category defaults per § 5.4.

### 3.4 — Permit-critical overlays

**`SetbackDimensions`** — front_mm, rear_mm, left_mm, right_mm.

**`SetbackComplianceReport`** — setback_dimensions +
{front,rear,left,right}_min_required_mm + all_compliant.

**`ParkingProvision`** — provided_count, required_count, bay_size_mm
(default 2500×5000 mm).

**`ParkingComplianceReport`** — compliant, provided_count, required_count.

**`RainWaterHarvestingOverlay`** — overlay_id, pit_count (≥1),
pit_location_xy_mm (default SE corner of plot).

**`SewageLayoutOverlay`** — overlay_id, septic_tank_location_xy_mm,
sewage_treatment_capacity_l (default 1500).

**`WorkingAnnotation`** — annotation_id, text, anchor_x/y_mm,
annotation_kind ∈ {dimension, room_label, note, elevation}.

**`SetbackAnnotation`** — annotation_id, side, value_mm, anchor_x/y_mm.

**`ComplianceMarker`** — marker_id, marker_kind ∈ {rwh_pit, parking_bay,
septic_tank, fire_path, north_arrow}, anchor_x/y_mm.

---

## § 4 — R-invariant enforcement points (definitive list)

Closing the v0.5 LOCKED open question of *where* each R-invariant is
enforced in code. This table is the v1.0 contract:

| Invariant | Enforced at | Test coverage |
|---|---|---|
| R7a (mm conversion) | `upstream_adapter.m_to_mm` | `test_c16_upstream_adapter.TestMToMm` |
| R7b (stable IDs) | `schema.compute_element_identity` | `test_c16_phase_alpha.TestR7bStableIdentities` |
| R7c (canonical lex-ASC) | per-phase tuple construction | every phase test |
| R7d (no time/env in canonical) | `cache_keys.canonical_replay_signature` | `test_c16_phase_zeta.TestCanonicalReplaySignature.test_phase_timings_do_not_affect_canonical_signature` |
| R8 (advisory passthrough) | `zeta_bundle.execute_phase_zeta` | `test_c16_phase_zeta.TestAdvisoryFlagsPassthrough` |
| R9 (schema MINOR vs MAJOR) | `versioning.C16_DRAWING_SCHEMA_VERSION = 13` | `test_c16_versioning` |
| R15 (compliance provenance) | `epsilon_attestation.execute_phase_epsilon` | `test_c16_phase_epsilon.TestR15Provenance` |
| R19 (coord bounds) | `alpha_envelope._check_bounds` | `test_c16_phase_alpha` (indirect) |
| R20 (geometry parity) | `schema.DualDrawingBundle.__post_init__` | `test_c16_schema.TestBundleR20GeometryParity` |
| R21 (legal_completeness gating) | `delta_permit.execute_phase_delta` | `test_c16_phase_delta.TestLegalCompletenessIncompleteBeforeEpsilon` |
| R22 (authority discipline) | `contracts.AttestedValue.__post_init__` | `test_c16_phase_epsilon.TestR22AuthorityDiscipline` |
| R23 (mandatory section cuts) | `gamma_working._compute_section_view` | `test_c16_phase_gamma.TestSectionViewsR23` |
| R24a (reference resolution) | `schema.DualDrawingBundle.__post_init__` | `test_c16_schema.TestBundleR24aReferenceResolution` |
| R24b (no orphan geometry) | `schema.DualDrawingBundle.__post_init__` | `test_c16_schema.TestBundleR24bOrphanGeometry` |
| R24c (geometry_id uniqueness) | `schema.DualDrawingBundle.__post_init__` | `test_c16_schema.TestBundleR24cUniqueness` |
| R25 (UPSTREAM_AUTHORITATIVE gating) | `epsilon_attestation` legally_counted set | `test_c16_phase_epsilon.TestR25LegalCompleteness` |
| R26b (schema descriptor digest) | `schema.compute_schema_descriptor_digest` | `test_c16_phase_zeta.TestR26bSchemaDescriptorDigest` |
| R29 (orientation hierarchy 4 steps) | `orientation.compute_orientation` | `test_c16_orientation.TestStep{1..4}` |
| R29b (orientation_basis recorded) | `alpha_envelope` → `GeospatialReference` | `test_c16_phase_alpha.TestGeospatialReference` |
| R29c (lex-ASC semantic tiebreak) | `orientation.compute_orientation` | `test_c16_orientation.TestStep3.test_tied_longest_tiebreak_lex_min` |
| R29d (lock plausibility) | `orientation.validate_orientation_lock` | `test_c16_adversarial_corpus.TestScenario5` |
| R30 (legal ⊥ readability) | `schema.PermitDrawingModel.__post_init__` | `test_c16_schema.TestPermitDrawingModelLegalCompleteness` |
| R32a (canonical as prefix) | `cache_keys.presentation_signature` | `test_c16_phase_zeta.TestR32aPresentationSignature` |
| R33b (uniform identity_generation) | `schema.DualDrawingBundle.__post_init__` | `test_c16_schema.TestBundleR33bMixedGeneration` |

---

## § 5 — v1.0-acceptable documented limits

These are NOT defects; these are the spec's deliberate v1.0 scope.
Backlog items track future expansion.

### 5.1 — No upstream window source
`B-C16-WINDOW-UPSTREAM-CONTRACT` — no upstream component currently
emits windows. v1.0 ships with empty `windows` tuples on every
`FloorGeometry`. `WindowGeometry` schema is pinned and ready for future
upstream integration.

### 5.2 — All plumbing stacks default to FRESH_WATER
`B-C16-STACK-KIND-FROM-C10` — C10 doesn't tag stack kind in the
consumed surface. All `PlumbingStack.element_kind` set to
`PLUMBING_STACK_FRESH_WATER` at v1.0.

### 5.3 — Default column cross-section 230×230 mm
Indian RCC G+0 standard. Multi-storey size derivation is future work
(B-C16-COLUMN-CROSSSECTION-FROM-C7).

### 5.4 — Default per-category finishes
Hardcoded by category. Brief-driven choice is `B-C16-FINISH-DEFAULTS-FROM-BRIEF`.

Defaults:
- BEDROOM, LIVING → vitrified_tile floor, emulsion_paint walls
- KITCHEN → ceramic_tile floor, ceramic_tile walls (wet)
- BATHROOM → anti_skid_ceramic_tile floor, ceramic_tile walls
- STAIRCASE → granite floor

### 5.5 — Staircase section-cut uses midroom heuristic
`B-C16-STAIRCASE-CUT-FROM-C7-STAIRCASE` — C7's optional `Staircase`
field is not yet consumed; the staircase cut uses the top floor's
lex-min room midpoint as a stand-in. Test coverage confirms cut is
emitted when multi-floor.

### 5.6 — Default 1 parking bay
TNCDBR allows 1 covered bay for typical residential. Brief-driven
override is `B-C16-PARKING-FROM-BRIEF`.

### 5.7 — ReadabilityDiagnostics minimal
`B-C16-READABILITY-FULL-HEURISTICS` — `viewport_congestion_score`
defaults 0.0, `suppressed_annotations` defaults empty,
`readability_degraded` defaults False. R30 contract honored
(legal_completeness ⊥ readability_status); full heuristics post-v1.0.

### 5.8 — Floor label normalization heuristic
`B-C16-FLOOR-LABEL-NORMALIZATION` — accepts F0/F1/F2/G/GF/FF/SF/TF
labels. Upstream contract pinning of canonical label space is
post-v1.0.

### 5.9 — PhaseTimings zeta_bundle_assembly_ms = 0
`B-C16-ZETA-TIMING-SELF-INCLUSION` — chicken-and-egg with bundle
construction. Documented; doesn't affect canonical signature (R7d).

---

## § 6 — Schema version

`C16_DRAWING_SCHEMA_VERSION = 13`.

Bump from v0.5 LOCKED's 12 → 13 reflects the additive sub-envelope
field expansion in § 3. ADDITIVE only per R9; downstream consumers
holding v0.5 schema_version=12 bundles remain readable.

---

## § 7 — Test coverage at v1.0 PROPOSED

| Module | Test count | All passing |
|---|---|---|
| `test_c16_versioning.py` | 8 | ✓ |
| `test_c16_errors.py` | 19 | ✓ |
| `test_c16_contracts.py` | 47 | ✓ |
| `test_c16_config.py` | 26 | ✓ |
| `test_c16_cache_keys.py` | 67 | ✓ |
| `test_c16_schema.py` | 88 | ✓ |
| `test_c16_upstream_adapter.py` | 24 | ✓ |
| `test_c16_orientation.py` | 12 | ✓ |
| `test_c16_phase_alpha.py` | 23 | ✓ |
| `test_c16_phase_beta.py` | 9 | ✓ |
| `test_c16_phase_gamma.py` | 14 | ✓ |
| `test_c16_phase_delta.py` | 15 | ✓ |
| `test_c16_phase_epsilon.py` | 15 | ✓ |
| `test_c16_phase_zeta.py` | 15 | ✓ |
| `test_c16_orchestrator.py` | 14 | ✓ |
| `test_c16_pbt.py` (PBT layer) | 15 | ✓ (≥15 LOCK-mandatory ✓) |
| `test_c16_adversarial_corpus.py` (5-scenarios) | 8 | ✓ (all 5 scenarios covered) |
| **Total C16** | **419** | **✓** |
| **Project total (C15 + C16)** | **683** | **✓** |

### PBT layer ≥ 15 ✓
Coverage: m_to_mm idempotency (4), canonical_json determinism (3),
sorted_by_floor_label (1), orientation invariance (2), pipeline
determinism (5). `B-C16-PBT-LAYER-COVERAGE` CLOSED.

### 5-scenario adversarial corpus ✓
1. Corner-touch geometry → 1 test ✓
2. Zero-overlap edges → 1 test ✓
3. Max-bounds plot → 1 test ✓
4. Multi-floor stacked layout → 2 tests ✓
5. Orientation-lock conflict → 3 tests ✓

---

## § 8 — Sub-2 build corrections to v0.5 PROPOSED behavior

These are bug fixes shipped in Sub-2 that v0.5 LOCKED had left
implicit. v1.0 PROPOSED makes them explicit contract:

### 8.1 — Shared-edge axis pinning at actual room boundary
Previously: internal partition walls placed at coord 0 perpendicular.
v1.0: partition wall is positioned at the actual `PlacedRoom`
boundary (room_a's max-X or max-Y face touching room_b). If rooms
aren't actually adjacent, falls back to room_a's max-face and
documents the heuristic.

### 8.2 — Door anchor against real boundary
Same fix for doors: anchor coordinate uses the resolved boundary,
not coord 0.

### 8.3 — R23 section-cut fallback offset
Per v0.2 A8: when cut_position would fall outside building bbox,
offset inward to nearest valid coord (with 50mm margin). Offset
magnitude recorded on `SectionView.offset_mm`. Was always 0 in v0.5
build; now correctly computed.

### 8.4 — Empty-walls degenerate case for R29d
When no walls exist (no Grid wall_segments), the orientation
hierarchy returns lex_fallback @ 0°. `all_hierarchy_candidates()`
mirrors this so R29d plausibility accepts a lock at 0° in that
degenerate case.

---

## § 9 — Rule 7 critique walk

Per Rule 7: web search ≥1 per critique walk; grep code for code
claims; push back when wrong.

**Web search performed:** Session S49 prior round verified IFC
`IfcLocalPlacement` + `IfcSite` coordinate-frame conventions against
the dual-frame approach. Verified: large-magnitude CRS coordinates
break Revit-interop downstream; v0.3 A4 small-magnitude
LocalBuildingFrame design choice validated.

**Code grep verified:**
- Every R-invariant in § 4 has an enforcing call site in code.
- Every test file lists in § 7 exists on disk.
- All 419 C16 tests pass under pytest as of S49 close.

**No reviewer claim** stands at this PROPOSED moment that requires
further pushback or research.

---

## § 10 — Three-check protocol (Rule 10.6)

Per Rule 10.6:

**(a) GAP CHECK — promised vs delivered**

| Promised in v0.5 LOCKED + Rule 9 backlog | Delivered in v1.0 PROPOSED |
|---|---|
| Sub-envelope fields pinned at v1.0 LOCK | § 3 above — fully pinned |
| PBT layer ≥ 15 | 15 tests in test_c16_pbt.py |
| 5-scenario adversarial corpus | 5 scenarios in test_c16_adversarial_corpus.py |
| 6 phase modules complete | All 6 phases pass tests |
| Orchestrator with STRICT/WARN routing | render_drawings + batch shipped |
| 8 backlog items (5.1–5.8 above) | All v1.0-acceptable + documented |

**(b) AUDIT CHECK — spec compliance line-by-line**

Each R-invariant in § 4 maps to an enforcing call site and ≥1 test.
No spec section unimplemented.

**(c) INTEGRITY CHECK — files present, non-empty, tests green**

- All source files in `buildemup/components/c16/` and
  `buildemup/components/c16/phases/` are non-empty.
- 683 of 683 tests pass.
- `python3 -c "import buildemup.components.c16"` succeeds with all
  expected symbols exported.

---

## § 11 — Pre-touch state inventory (Rule 10.6.1)

Per Rule 10.6.1: distinguish session-created from session-modified.

**Pre-existing at S49 start (from S48 handoff bundle):**
- `c15/` module — UNTOUCHED, all 264 C15 tests still pass.
- `spec_locks/C15_v1_0_LOCK_RATIFICATION.md` — UNTOUCHED.
- `tools/moat_lint.py`, `tools/cultural_profile_parity_audit.py` —
  UNTOUCHED.

**Created in S49 this session (originally Sub-1):**
- `c16/versioning.py`, `errors.py`, `contracts.py`, `config.py`,
  `cache_keys.py`, `schema.py`, `__init__.py`
- 6 Sub-1 test files (255 tests)

**Created in S49 this session (Sub-2 — full build):**
- `c16/upstream_adapter.py`
- `c16/orientation.py`
- `c16/orchestrator.py`
- `c16/phases/__init__.py`, `alpha_envelope.py`, `beta_scheduling.py`,
  `gamma_working.py`, `delta_permit.py`, `epsilon_attestation.py`,
  `zeta_bundle.py`
- 11 new test files (164 tests)
- 1 spec composition: `spec_C16_v1_0_PROPOSED.md` (this document)

**Modified in S49 this session:**
- `c16/__init__.py` — added Sub-2 exports
- `c16/versioning.py` — schema_version 12 → 13
- `c16/schema.py` — sub-envelope fields expanded (ADDITIVE, R9)
- `c16/phases/alpha_envelope.py` — shared-edge + door boundary fix
- `c16/phases/gamma_working.py` — R23 offset fallback
- `c16/orientation.py` — empty-walls degenerate fallback for R29d
- `c16/orchestrator.py` — PhaseTimings/ReadabilityDiagnostics field
  names corrected
- `tests/test_c16/test_c16_schema.py` — fixture update for new SitePlan signature
- `tests/test_c16/test_c16_versioning.py` — schema_version = 13 baseline

---

## § 12 — Backlog roll-up (Rule 9 + Rule 9.2)

Per Rule 9: every backlog item the spec depends on, references, or
creates must be enumerated here with ID, description, origin,
trigger, S{N}-scope verdict, effort.

### 12.1 — CLOSED at v1.0 LOCK

| ID | Description | Origin | S49 verdict |
|---|---|---|---|
| `B-C16-ENVELOPE-SCHEMA-LOCK` | Pin sub-envelope field lists | v0.5 LOCK | **CLOSED** in § 3 |
| `B-C16-PBT-LAYER-COVERAGE` | ≥15 property-based tests | v0.1 § 7 | **CLOSED** — 15 in `test_c16_pbt.py` |
| `B-C16-ADVERSARIAL-CORPUS` | 5-scenario integration corpus | v0.1 § 7 | **CLOSED** — 5 scenarios in `test_c16_adversarial_corpus.py` |
| `B-C16-SHARED-EDGE-AXIS-PINNING` | Position partitions at real boundary | Sub-2 build | **CLOSED** — § 8.1 |
| `B-C16-R23-OFFSET-FALLBACK` | Inward-snap R23 cut when outside bbox | Sub-2 build | **CLOSED** — § 8.3 |

### 12.2 — DEFERRED post-LOCK (v1.0-acceptable)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| `B-C16-WINDOW-UPSTREAM-CONTRACT` | Source windows from upstream | Sub-2 build | When upstream emits | M |
| `B-C16-STACK-KIND-FROM-C10` | C10 tags stack kind | Sub-2 build | C10 v1.x | S |
| `B-C16-COLUMN-CROSSSECTION-FROM-C7` | Column size from floor count | Sub-2 build | Multi-storey workload | S |
| `B-C16-FINISH-DEFAULTS-FROM-BRIEF` | Brief-driven finishes | Sub-2 build | Brief integration | M |
| `B-C16-STAIRCASE-CUT-FROM-C7-STAIRCASE` | Real staircase cut from C7 | Sub-2 build | C7 staircase consumption | S |
| `B-C16-PARKING-FROM-BRIEF` | Brief-driven parking count | Sub-2 build | Brief integration | S |
| `B-C16-READABILITY-FULL-HEURISTICS` | Collision detection + congestion | v0.4 A9 | UX-driven | L |
| `B-C16-FLOOR-LABEL-NORMALIZATION` | Pin canonical label space | Sub-2 build | Upstream contract round | S |
| `B-C16-ZETA-TIMING-SELF-INCLUSION` | Capture zeta_micros in PhaseTimings | Sub-2 build | Two-pass orchestrator design | S |

### 12.3 — Summary table

| Category | Count |
|---|---|
| CLOSED at v1.0 LOCK | 5 |
| DEFERRED post-LOCK | 9 |
| **Total tracked** | **14** |

---

## § 13 — LOCK adjudication request (Rule 8)

Per Rule 8: LOCK authority belongs to Ramalingam alone.

**This document is v1.0 PROPOSED. PENDING Ramalingam LOCK adjudication.**

For Ramalingam to LOCK, please confirm:

1. **Sub-envelope field PINNING** in § 3 captures what you want C16's
   v1.0 contract to be.
2. **R-invariant enforcement points** in § 4 are correct.
3. **v1.0-acceptable limits** in § 5 are acceptable as documented
   v1.0 ship-with limits (NOT defects).
4. **Schema version 13** is correct bump per R9.
5. **Sub-2 build corrections** in § 8 are correct fixes.
6. **Backlog roll-up** in § 12 captures the right work.

If yes to all: **state "C16 v1.0 LOCKED"**.

If corrections needed: state which sections need patches; I'll
compose v1.1 PROPOSED with the patches and wait for the next LOCK
adjudication round.

---

**END OF v1.0 PROPOSED — PENDING Ramalingam LOCK**
