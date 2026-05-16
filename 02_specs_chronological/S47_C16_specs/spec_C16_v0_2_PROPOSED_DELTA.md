# Component 16 — Dual-Drawing Renderer — v0.2 PROPOSED-DELTA

**Spec version:** v0.2 PROPOSED-DELTA over v0.1 PROPOSED
**Status:** PROPOSED. PENDING Ramalingam LOCK adjudication.
**Authored:** S47 (this session, post-critique-walk)
**Critique source:** External review document, 13 substantive items + overall assessment
**Reading order:** This delta layers over `spec_C16_v0_1_PROPOSED.md`. To read the proposed v0.2 state, read v0.1 first then apply these amendments. Where the delta amends a section, the delta wins.

---

## What this delta changes vs v0.1

10 amendments (A1-A10), 4 new invariants (R19-R22), 1 enum added to schema, 1 architectural restructure (shared geometry core).

---

## A1 — SelectedLayout contract: concrete typestate

**Origin:** Reviewer item 1; converges with my own self-flagged Q1.

**Problem:** v0.1 § 10 treats `SelectedLayout` as opaque. The reviewer correctly notes this is the single largest architectural ambiguity. Without a defined contract: cache determinism fragile, provenance incomplete, replay can drift, downstream approvals ambiguous.

**Amendment:** Define `SelectionResult` typestate (replaces opaque `SelectedLayout` in v0.1 § 10):

```python
@dataclass(frozen=True)
class SelectionResult:
    """The contract C16 consumes from the (TBD) layout-selection step.
    
    Whoever produces the final selection (project-level adjudication
    per B-PROJECT-SELECTOR-COMPONENT-DEFINITION) MUST emit this shape.
    """
    selected_layout_signature: str          # the chosen candidate's stable signature
    selector_version: str                    # e.g. "human_v1" / "auto_v0.1" / "c17_aggregator_v1"
    selection_reason: SelectionReason       # enum: HUMAN_CHOICE | RANKER_TOP | TIEBREAK_DETERMINISTIC | DEFAULT_FIRST
    candidate_ranking_snapshot: tuple[CandidateRanking, ...]  # full ranked list, frozen at selection time
    human_override: Optional[HumanOverrideRecord]   # populated iff a human chose over a different ranked-top
    selection_timestamp_utc: str             # ISO 8601, stamped at selection time
    upstream_problem_reports: tuple[ProblemReport, ...]  # C15 outputs for ALL candidates (not just selected)
```

`SelectionReason` enum: `HUMAN_CHOICE`, `RANKER_TOP`, `TIEBREAK_DETERMINISTIC`, `DEFAULT_FIRST`, `UNKNOWN_LEGACY`.

C16 reads `selected_layout_signature` to identify which candidate to render. The other fields (ranking, override metadata) are passed through to provenance records — C16 doesn't decide based on them.

**Cache-relevant:** YES (input contract change → bump `C16_VERSION`).

**Backlog upgrades:**
- `B-C16-SELECTED-LAYOUT-CONTRACT-LOCK` → refined to specify these exact fields
- `B-PROJECT-SELECTOR-COMPONENT-DEFINITION` routed amendment hint retained — WHO produces SelectionResult is still project-level open

---

## A2 — Coordinate system formalized (right-handed Cartesian)

**Origin:** Reviewer item 11. Web-research verified against IFC + Revit + AutoCAD conventions.

**Problem:** v0.1 never specified origin point, axis orientation, handedness, floor elevation reference, or unit normalization. Major interoperability risk for future SVG/DXF/IFC/CAD exports.

**Amendment:** Add new § 1.0 "Coordinate system" at top of § 1:

> **C16 emits geometry in a right-handed Cartesian coordinate system** with these fixed conventions:
> - **Origin (0, 0, 0):** South-West corner of the site bounding box (the plot, not the building footprint). Floor elevation reference: ground floor finished floor level = z = 0.
> - **+X axis:** East (positive azimuth from origin).
> - **+Y axis:** North.
> - **+Z axis:** Up (right-hand rule per CAD/BIM standard).
> - **Units:** Millimeters (mm) for all linear measurements. Consistent with IS 962 and TNCDBR drawing conventions.
> - **Rotation convention:** Positive rotation = counter-clockwise about +Z (right-hand rule).
> - **Floating-point policy:** All coordinates emitted with banker's rounding to 1 mm precision (`round_half_even`). Sub-mm precision NEVER appears in output.
> - **Snapping tolerance:** 1 mm. Coordinates within 1 mm of grid intersection round to the grid.
> - **Bounding-box guard:** All coordinates MUST satisfy `0 ≤ x ≤ 200,000 mm AND 0 ≤ y ≤ 200,000 mm AND -5,000 ≤ z ≤ 50,000 mm`. Bounds chosen to safely cover Indian residential plots up to ~50,000 sqm with multi-storey heights; rejects pathological inputs early.

New Invariant **R19**: every coordinate in any DrawingModel obeys the system above. Violations raise `GeometryInconsistencyError` (per § 4 hierarchy).

**Cache-relevant:** NO (output convention only; coordinate system change post-LOCK would be a v2.x).

---

## A3 — Shared FloorGeometry core (deduplication architecture)

**Origin:** Reviewer item 7.

**Problem:** v0.1 has WorkingDrawingModel.floor_plans AND PermitDrawingModel.floor_plans as parallel structures. Over time geometry will drift: one model may lag, parity bugs will appear.

**Amendment:** Restructure schema so that geometry is computed ONCE and annotation layers reference it:

```python
@dataclass(frozen=True)
class FloorGeometry:
    """Source of truth for floor-level geometry. Shared by both
    WorkingDrawing and PermitDrawing via reference, not copy."""
    floor_level: int                        # 0 = ground, 1 = first, etc.
    floor_elevation_mm: int                  # absolute z of this floor's finished floor
    rooms: tuple[RoomGeometry, ...]          # boundaries, dimensions
    walls: tuple[WallSegment, ...]           # from C7 wall graph
    doors: tuple[DoorGeometry, ...]          # from C13
    windows: tuple[WindowGeometry, ...]      # from C9
    columns: tuple[ColumnGeometry, ...]      # from C7
    plumbing_stacks: tuple[PlumbingStack, ...]  # from C10
    
    # Stable opaque ID — same input → same ID (Inv R21)
    geometry_id: str                         # SHA-256 of canonical fields

@dataclass(frozen=True)
class WorkingDrawingFloor:
    """Working-drawing-specific overlay on a FloorGeometry."""
    geometry_ref: str                        # geometry_id of the shared FloorGeometry
    annotations: tuple[WorkingAnnotation, ...]  # joinery, finish, BOQ hooks
    door_schedule: tuple[DoorScheduleEntry, ...]
    window_schedule: tuple[WindowScheduleEntry, ...]
    finish_schedule: tuple[FinishScheduleEntry, ...]

@dataclass(frozen=True)
class PermitDrawingFloor:
    """Permit-drawing-specific overlay on the SAME FloorGeometry."""
    geometry_ref: str                        # MUST match a WorkingDrawingFloor.geometry_ref
    setback_annotations: tuple[SetbackAnnotation, ...]
    compliance_markers: tuple[ComplianceMarker, ...]
    # NO contractor-facing detail; compliance-focused only
```

`DualDrawingBundle` is restructured to carry the shared geometry tuple once:

```python
@dataclass(frozen=True)
class DualDrawingBundle:
    source_selection_signature: str
    floor_geometries: tuple[FloorGeometry, ...]  # ONE per floor — shared source of truth
    working_drawing_model: WorkingDrawingModel    # references floor_geometries by geometry_id
    permit_drawing_model: PermitDrawingModel      # references floor_geometries by geometry_id
    # ... (rest unchanged from v0.1)
```

New Invariant **R20** (geometry parity): for every floor, the geometry_ref in WorkingDrawingFloor and PermitDrawingFloor MUST match the geometry_id of the corresponding FloorGeometry. Working and permit drawings can NEVER hold divergent geometry.

**Cache-relevant:** YES (output schema change → bump `C16_VERSION`).

---

## A4 — SubmissionReadiness enum + UNSAFE flag

**Origin:** Reviewer items 10 + 12 (merged — same operational concern).

**Problem:** v0.1 WARN mode lets partial PermitDrawingModels through. Downstream may treat them as submission-ready. Plus, even COMPLETE permit drawings require an architect signature (per TNCDBR rule 8(1)(iii)) — but v0.1 doesn't flag this prominently.

**Amendment:** Add `SubmissionReadiness` enum to `PermitDrawingModel`:

```python
class SubmissionReadiness(Enum):
    """Per TNCDBR rule 8(1)(iii) — permit drawings emitted by C16 are
    NEVER submission-ready in the legal sense. They require:
    
    1. Registered architect / engineer signature (HUMAN, outside C16)
    2. Authority-specific scrutiny stamp (outside system entirely)
    
    Even a COMPLETE bundle is COMPLETE_REQUIRES_SIGNATURE — never DONE."""
    
    COMPLETE_REQUIRES_SIGNATURE = "complete_requires_signature"  # all overlays present
    INCOMPLETE_DRAFT = "incomplete_draft"        # some non-critical overlay missing; safe to share with architect but NOT to submit
    UNSAFE_FOR_SUBMISSION = "unsafe_for_submission"  # permit-critical overlay missing — DO NOT submit

@dataclass(frozen=True)
class PermitDrawingModel:
    # ... (existing fields) ...
    submission_readiness: SubmissionReadiness          # ALWAYS populated
    requires_professional_signature: bool = True       # ALWAYS True (TNCDBR rule 8(1)(iii))
    missing_overlays: tuple[str, ...] = ()             # names of permit-critical overlays absent
    signature_placeholder: Optional[SignaturePlaceholder] = None  # downstream signature flow hooks here
```

**Permit-critical overlays** (whose absence forces `UNSAFE_FOR_SUBMISSION`):
- Rain water harvesting overlay (TNCDBR rule 9(a))
- Sewage layout overlay (TNCDBR rule 9(b))
- Setback dimensions on all 4 sides
- FAR + plot coverage compliance attestation
- Parking provision

If ANY are missing, `submission_readiness = UNSAFE_FOR_SUBMISSION` and `missing_overlays` enumerates which.

New Invariant **R21**: PermitDrawingModel with `submission_readiness == COMPLETE_REQUIRES_SIGNATURE` MUST have all 5 permit-critical overlays present. PermitDrawingModel with `UNSAFE_FOR_SUBMISSION` MUST have non-empty `missing_overlays`. Validated at `__post_init__`.

WARN-mode `FailedDrawingRender` with partial bundle: `submission_readiness` always forced to `UNSAFE_FOR_SUBMISSION` regardless of whether overlays appear present (because the render failed mid-stream and per-overlay completeness can't be trusted).

**Cache-relevant:** YES (output schema change → bump `C16_DRAWING_SCHEMA_VERSION`).

---

## A5 — AuthorityKind enum + provenance discipline

**Origin:** Reviewer item 5.

**Problem:** v0.1 ComplianceAttestation mixes "values originated upstream" (plot_area_sqm from C4) and "values derived here from upstream inputs" (plot_coverage_pct = built_up / plot). The reviewer correctly flags this as a drift risk — C16 could unintentionally become a shadow compliance engine.

**Amendment:** Add `AuthorityKind` enum and tag every field:

```python
class AuthorityKind(Enum):
    """Provenance discipline for ComplianceAttestation fields.
    
    UPSTREAM_AUTHORITATIVE: value originated at an upstream component;
        C16 re-states it byte-identically.
    LOCALLY_DERIVED: value computed in C16 from upstream inputs.
        ONLY arithmetic reformatting is permitted (e.g. ratio of two
        upstream values). NO independent compliance logic.
    CROSS_CHECK_VERIFICATION: value computed locally AS A CHECK against
        an upstream-authoritative value of the same quantity, raising
        ComplianceProvenanceError if they disagree beyond tolerance.
    """
    UPSTREAM_AUTHORITATIVE = "upstream_authoritative"
    LOCALLY_DERIVED = "locally_derived"
    CROSS_CHECK_VERIFICATION = "cross_check_verification"

@dataclass(frozen=True)
class AttestedValue:
    """Wrapper for every ComplianceAttestation field."""
    value: float | int | bool
    authority: AuthorityKind
    upstream_source: Optional[str]   # e.g. "c2_feasibility:far_used"; None iff LOCALLY_DERIVED
    derivation_note: Optional[str]    # e.g. "built_up_area / plot_area * 100"; required for LOCALLY_DERIVED
```

ComplianceAttestation field types change:

```python
@dataclass(frozen=True)
class ComplianceAttestation:
    plot_area_sqm: AttestedValue                  # UPSTREAM_AUTHORITATIVE (C4)
    built_up_area_sqm: AttestedValue              # UPSTREAM_AUTHORITATIVE (C9)
    plot_coverage_pct: AttestedValue              # LOCALLY_DERIVED — note: "built_up/plot*100"
    far_used: AttestedValue                       # UPSTREAM_AUTHORITATIVE (C2)
    far_permitted: AttestedValue                  # UPSTREAM_AUTHORITATIVE (C4 + jurisdiction)
    building_height_m: AttestedValue              # UPSTREAM_AUTHORITATIVE (C12)
    # ... etc
```

**Rule:** C16 NEVER originates compliance assertions. The ONLY locally-computed values are: (a) arithmetic ratios from upstream values (e.g. plot_coverage_pct), (b) cross-check verifications that flag if they disagree with upstream.

New Invariant **R22**: every `LOCALLY_DERIVED` AttestedValue MUST have a non-empty `derivation_note` and `upstream_source = None`. Every `UPSTREAM_AUTHORITATIVE` MUST have non-empty `upstream_source` and `derivation_note = None`. Enforced at `__post_init__`.

**Cache-relevant:** YES (schema change → bump `C16_DRAWING_SCHEMA_VERSION`).

---

## A6 — RenderingConfig schema fleshed out

**Origin:** Reviewer item 9.

**Problem:** v0.1 RenderingConfig was opaque. Lacks deterministic semantics for conflict resolution, annotation suppression, scale fallback.

**Amendment:** Define `RenderingConfig` shape:

```python
@dataclass(frozen=True)
class RenderingConfig:
    # Scale targets (per TNCDBR rule 8)
    working_drawing_scale: Literal["1:50", "1:75"] = "1:50"
    permit_drawing_scale: Literal["1:100", "1:150", "1:200"] = "1:100"
    
    # Annotation density (controls suppression heuristics)
    annotation_density: Literal["full", "medium", "sparse"] = "full"
    
    # Multi-floor composition
    multi_floor_composition: Literal["per_floor_separate", "stacked_layout"] = "per_floor_separate"
    
    # Furniture display
    include_furniture_footprints_in_working: bool = True
    include_furniture_footprints_in_permit: bool = False  # NEVER True for permits
    
    # Section view configuration
    mandatory_section_cuts: frozenset[Literal["entry", "staircase", "wet_zone"]] = (
        frozenset({"entry", "staircase", "wet_zone"})
    )
    
    # Suppression precedence (when annotations would overlap)
    suppression_precedence: tuple[str, ...] = (
        "decorative",       # suppressed first
        "secondary_dim",
        "primary_dim",
        "structural",
        "compliance",       # suppressed LAST (never if possible)
    )
    
    # Conflict resolution (deterministic)
    annotation_conflict_policy: Literal["lex_asc_id_wins", "suppress_both"] = "lex_asc_id_wins"
```

**Precedence order** for resolution when fields conflict with internal C16 defaults:
1. Explicit `RenderingConfig` field (highest)
2. `JurisdictionProfile` recommended default
3. C16 hard-coded fallback (lowest)

Permit-mode safety: regardless of `RenderingConfig.include_furniture_footprints_in_permit`, furniture footprints NEVER appear in permit drawings. The flag exists for symmetry but is force-overridden.

**Cache-relevant:** YES (config affects output → cache_keys include config_signature; bump `C16_VERSION`).

---

## A7 — Stable element IDs + BIM-forward semantic taxonomy

**Origin:** Reviewer item 13.

**Problem:** v0.1 doesn't specify ID generation. UUIDs would break Inv R7 (replay determinism). Plus, future BIM/IFC export needs semantically-typed elements.

**Amendment:** Add ID generation rule + element taxonomy:

**ID generation rule:** every renderable element gets a stable opaque ID of the form `{element_kind}:{stable_hash_8}`, where `stable_hash_8` is the first 8 hex chars of SHA-256 of the element's canonical-serialized content. **No UUIDs.** Same input → same ID, guaranteed.

**Element taxonomy** (semantic categories for BIM-forward design):

```python
class ElementKind(Enum):
    # Walls
    WALL_EXTERNAL = "wall_external"
    WALL_INTERNAL_LOAD_BEARING = "wall_internal_load_bearing"
    WALL_INTERNAL_PARTITION = "wall_internal_partition"
    WALL_PARAPET = "wall_parapet"
    
    # Openings
    DOOR_EXTERNAL = "door_external"
    DOOR_INTERNAL = "door_internal"
    WINDOW_EXTERNAL = "window_external"
    WINDOW_VENTILATOR = "window_ventilator"
    
    # Structural
    COLUMN = "column"
    BEAM = "beam"
    SLAB_FLOOR = "slab_floor"
    SLAB_ROOF = "slab_roof"
    
    # Plumbing
    PLUMBING_STACK_FRESH_WATER = "plumbing_stack_fresh_water"
    PLUMBING_STACK_WASTE = "plumbing_stack_waste"
    PLUMBING_STACK_RAIN_WATER = "plumbing_stack_rain_water"
    
    # Compliance overlays
    SETBACK_MARKER = "setback_marker"
    FAR_ANNOTATION = "far_annotation"
    PARKING_BAY = "parking_bay"
    RWH_FACILITY = "rwh_facility"
    SEWAGE_FACILITY = "sewage_facility"
```

This taxonomy is **additive** — adding new kinds is a MINOR `C16_DRAWING_SCHEMA_VERSION` bump. Removing/renaming is MAJOR.

When future BIM/IFC export ships (post-v1 backlog), the taxonomy maps cleanly to IFC's `IfcWall`, `IfcDoor`, `IfcColumn`, etc.

**Cache-relevant:** YES (IDs in output → bump `C16_DRAWING_SCHEMA_VERSION`).

---

## A8 — Section-view generation rules formalized

**Origin:** Reviewer item 4; converges with my own self-flagged Q4.

**Problem:** v0.1 § 3 Phase γ used heuristic "longest dimension + perpendicular." Reviewer correctly notes irregular plots produce useless cuts; staircases may not appear; plumbing stacks may be hidden; split-level homes break.

**Amendment:** Mandatory section cuts (per `RenderingConfig.mandatory_section_cuts`):

**Cut 1 — Entry section:** passes through the main entrance (from C13) horizontally, oriented perpendicular to the entry door wall. Always required.

**Cut 2 — Staircase section:** passes through the staircase (from C12) on multi-floor buildings. SKIPPED for single-floor. Cut orientation chosen to maximize stair visibility (parallel to stair run direction).

**Cut 3 — Wet-zone section:** passes through the highest-stack-count plumbing column (from C10). Cut orientation chosen to maximize stack visibility. Used to show multi-floor wet-zone alignment.

**Fallback hierarchy for irregular geometries:**
1. If a mandatory cut would pass outside the building envelope (e.g. L-shaped plot, courtyard), the cut is offset by the minimum distance needed to stay inside, snapped to a structural grid line.
2. If multiple offset positions are valid, the lex-smallest stable_id-ordered choice wins (Inv R7 determinism).
3. If no valid offset exists (degenerate geometry), emit a `GeometryInconsistencyError` — STRICT raises, WARN collects.

New Invariant **R23**: WorkingDrawingModel.section_views contains exactly the section cuts listed in `RenderingConfig.mandatory_section_cuts`, in the order they appear in the enum. For multi-floor buildings, every section cut traverses ≥2 floors (Inv R17 already covers this).

**Cache-relevant:** NO (algorithm change, not output schema change; existing C16_VERSION sufficient).

---

## A9 — Determinism sub-invariants (R7 strengthened)

**Origin:** Reviewer item 3.

**Problem:** v0.1 R7 says "byte-equal replay" but doesn't address FP rounding, ID generation, or serialization stability — three real determinism vectors.

**Amendment:** Decompose R7 into sub-invariants:

- **R7a — Floating-point rounding policy:** all coordinates emitted with banker's rounding to 1 mm (already stated in A2). All ratios (e.g. plot_coverage_pct) banker's-rounded to 4 decimal places. No raw FP residue in output.
- **R7b — Stable ID generation:** element IDs derived deterministically via SHA-256 of canonical content (A7 specifies). NO UUIDs, NO timestamps, NO random sources.
- **R7c — Canonical JSON serialization:** when DrawingModel is serialized for caching or comparison, keys are emitted in lex-ASC order; numeric formatting uses fixed precision (mm: integer; ratios: 4 decimal places); strings encoded UTF-8 NFC-normalized; arrays preserve their canonical-sort order (no reordering).
- **R7d — No environment dependence:** no system time, no locale, no environment-variable lookups in C16's emission path.

These are tightenings of R7, not replacements. R7 remains the base invariant.

**Cache-relevant:** NO (clarification of existing R7; same byte-equal outputs guaranteed).

---

## A10 — Phase timing instrumentation (observability)

**Origin:** Reviewer item 8.

**Problem:** v0.1 performance budget (1.5s/layout) may underestimate annotation-heavy multi-floor villas. Reviewer's suggestion: phase timing instrumentation, geometry indexing, lazy section generation.

**Amendment:** Add optional `phase_timings: Optional[PhaseTimings]` field to DualDrawingBundle:

```python
@dataclass(frozen=True)
class PhaseTimings:
    """Optional observability. Same DualDrawingBundle output regardless
    of whether timings are captured (timings excluded from cache_keys)."""
    alpha_envelope_assembly_ms: int
    beta_scheduling_ms: int
    gamma_working_assembly_ms: int
    delta_permit_assembly_ms: int
    epsilon_attestation_packaging_ms: int
    zeta_bundle_assembly_ms: int
    total_ms: int
```

When `RenderingConfig.capture_phase_timings = True` (default: False), timings are stamped. **Timings are EXCLUDED from cache_keys and DrawingModel equality** — they're observability only, not part of the canonical output.

The v0.1 1.5s budget remains. If real-world data shows it's wrong, post-LOCK calibration is a v1.x amendment (B-C16-PERFORMANCE-BUDGET-CALIBRATION-FROM-PROD-DATA).

**Cache-relevant:** NO (timings excluded from cache_keys by design).

---

## § 12 — Backlog updates from critique walk

### New LOCK-mandatory items (added to v0.1's 8 → 11 total)

| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C16-COORDINATE-CONVENTION-IFC-COMPATIBILITY-VERIFICATION | Verify the A2 coordinate convention maps cleanly to IFC's `IfcLocalPlacement` when IFC export ships | v1.0 | S |
| B-C16-SHARED-GEOMETRY-PARITY-CI-CHECK | CI test that working+permit floor geometries reference identical `geometry_id` for every floor | v1.0 | S |
| B-C16-SECTION-CUT-FALLBACK-CORPUS | Adversarial corpus: 10 irregular plot geometries that stress the section-cut fallback hierarchy in A8 | v1.0 | M |

### New post-LOCK items

| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C16-JURISDICTION-CAPABILITY-MATRIX | Refactor JurisdictionProfile into a capability matrix as reviewer suggested in item 6 | v1.x | L |
| B-C16-RENDERING-CONFIG-CONFLICT-RESOLUTION-AUDIT | Annual audit of config precedence behavior against actual user-config patterns from prod | post-LOCK | S |
| B-C16-PERFORMANCE-BUDGET-CALIBRATION-FROM-PROD-DATA | Calibrate v1.0 1.5s/layout budget against real residential-villa production data | v1.x | S |
| B-C16-BIM-IFC-EXPORT-PILOT | First pilot of IFC export using A2 coordinate convention + A7 element taxonomy | post-v1 | L |
| B-C16-SUBMISSION-READINESS-USER-EDUCATION | Downstream UI must surface SubmissionReadiness clearly to users (e.g. prominent "REQUIRES ARCHITECT SIGNATURE" banner) | post-v1 | M |

### Routed amendment hint (unchanged from v0.1)
- B-PROJECT-SELECTOR-COMPONENT-DEFINITION still open — A1 sharpens the contract but doesn't resolve WHO produces SelectionResult

### Cumulative backlog at v0.2 PROPOSED: 26 items
- 11 LOCK-mandatory (8 from v0.1 + 3 from this walk)
- 12 post-LOCK / v1.x
- 3 routed amendment hints

---

## Summary of structural changes

**New types added:** `SelectionResult`, `SelectionReason`, `CandidateRanking`, `HumanOverrideRecord`, `FloorGeometry`, `WorkingDrawingFloor`, `PermitDrawingFloor`, `SubmissionReadiness`, `SignaturePlaceholder`, `AuthorityKind`, `AttestedValue`, `RenderingConfig` (full shape), `ElementKind`, `PhaseTimings`.

**New invariants:** R19 (coordinate bounds), R20 (geometry parity), R21 (submission-readiness completeness), R22 (provenance authority discipline), R23 (mandatory section cuts).

**Architectural shifts:** geometry deduplication (A3) is the biggest. ComplianceAttestation provenance discipline (A5) is the most semantically important.

**Cache-relevant amendments (require bump):** A1, A3, A4, A5, A6, A7 → bump `C16_DRAWING_SCHEMA_VERSION` from 1 → 2. `C16_VERSION` v0.1 → v0.2.

**Non-cache-relevant:** A2, A8, A9, A10.

---

## Rule 8 / Rule 11 disclosure

Per Rule 8: LOCK authority is Ramalingam's alone. This delta is **PROPOSED, PENDING your adjudication**. Lock applies after explicit "lock it" / "v0.2 LOCKED."

Per Rule 11: web research verified A2 coordinate convention against IFC + Revit + AutoCAD industry standards (right-handed Cartesian + origin-based local reference is universal). All 13 substantive reviewer items walked with verdicts; 11 VALID, 2 PARTIALLY-VALID, 0 MISFRAMED. The reviewer caught 2 gaps I missed in self-analysis (coordinate standard, permit/working geometry duplication).

Self-analysis worst remaining gaps after this delta:

1. **A1 SelectionResult contract still depends on B-PROJECT-SELECTOR-COMPONENT-DEFINITION resolution.** I refined the SHAPE but not the OWNER of SelectionResult. Project-level adjudication still needed.

2. **A2 coordinate convention assumes plot is roughly axis-aligned to true North.** For plots rotated significantly off-North, the SW-corner origin convention works but produces non-intuitive coordinates. Acceptable v1 limitation; B-C16-NON-AXIS-ALIGNED-PLOT-HANDLING for post-v1.

3. **A3 shared geometry is good but adds indirection.** Downstream consumers must dereference `geometry_ref` to get geometry. v1 tooling overhead is one extra lookup; trivial.

4. **A4 SubmissionReadiness "UNSAFE_FOR_SUBMISSION" depends on permit-critical overlay correctness.** If A6 RenderingConfig is misconfigured (e.g. mandatory_section_cuts incorrectly suppresses one), SubmissionReadiness may falsely report COMPLETE_REQUIRES_SIGNATURE. Mitigation: B-C16-PERMIT-CRITICAL-OVERLAY-AUDIT (post-LOCK).

---

## § 16 — End of v0.2 PROPOSED-DELTA

This document constitutes the C16 v0.2 PROPOSED-DELTA. Awaiting Ramalingam LOCK adjudication.

Next steps if LOCKED:
- C16 build can begin per spec-first discipline
- v0.3+ refinements during implementation toward v1.0 LOCK
- Project-level B-PROJECT-SELECTOR-COMPONENT-DEFINITION should resolve BEFORE C16 v1.0 LOCK (otherwise C16 ships against an opaque contract)

Next steps if revisions requested:
- v0.2 PROPOSED-DELTA reshaped per your direction
- Re-submitted as v0.2 PROPOSED-DELTA-2

Per Rule 8 — your call.
