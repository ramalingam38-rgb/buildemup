# Component 16 — Dual-Drawing Renderer

**Spec version:** v0.1 PROPOSED
**Status:** PROPOSED. PENDING Ramalingam LOCK adjudication.
**Authored:** S47 close (this session)
**Authored as:** SKETCH per the project's v0.6 C13-LOCK-gating convention reused at C14/C15.
**Author note:** Per Rule 8 — LOCK authority is Ramalingam's alone. This document is a draft for analysis.

---

## § 0.0 — IMPORTANT: C16 produces drawing DATA, not pixels

C16 is the Dual-Drawing Renderer. Its job is to consume the FINAL approved layout from upstream (C13 doors + C12 vertical alignment + C7 grid + C9 dimensions + supporting metadata) and emit TWO structured drawing models — one targeted at construction use, one at municipal permit submission. **C16 emits structured data.** Actual visual rendering (PDF generation, SVG paint, DXF conversion, web canvas) is a separate downstream concern.

C16 DOES NOT:
- Generate PDFs, SVGs, DXFs, or any binary/pixel format
- Sign drawings as a registered architect (per TNCDBR rule 19, signatures must be by a registered professional — that's a human step outside C16)
- Make compliance decisions (C2 / C4 / C10 already made them; C16 just packages those decisions into drawing-data form)
- Decide which of multiple candidate layouts to render (the "final layout" comes in pre-selected — selection logic lives upstream)
- Localize permit-drawing rules to states outside Tamil Nadu (v1 = TNCDBR 2019 + NBC 2016 only)

Two layouts with IDENTICAL pipeline outputs will produce BYTE-EQUAL DrawingModels (Inv R7).

**Why two drawings, not one?**

Per TNCDBR 2019 rule 8 + the Statutory Approval workflow in Tamil Nadu, working drawings and permit drawings serve fundamentally different audiences:

| Aspect | Working Drawing | Permit Drawing |
|---|---|---|
| Audience | Contractor / mason / supervisor | Municipal authority / DTCP / CMDA |
| Scale | 1:50 typical | 1:100 minimum per TNCDBR rule 8(1)(i) |
| Required dimensions | Wall thickness, joinery details, BOQ-linked annotations | Plot setbacks, FAR calc, plot coverage, building height |
| Required annotations | Material specs, finish schedules | Compliance attestations (FAR, NBC chapter references) |
| Required overlays | Plumbing stacks, structural columns visible | Rain water harvesting + sewage layout per rule 9 |
| Section views | Section A-A, B-B with construction details | Sectional details per rule 8(1) but compliance-focused |

Squeezing both into one drawing was the historical norm — and produces drawings that are bad at both jobs. C16 separates them at the data layer.

---

## § 0.1 — What C16 IS

A pure-function component that takes:

1. ONE final approved layout (`SelectedLayout` typestate — upstream-produced)
2. Upstream supporting data (wall graph from C7, doors from C13, room dimensions from C9, vertical alignment from C12, advisory flags from C13/C14, problem reports from C15 if available)
3. A `JurisdictionProfile` (v1: only `tn_cdbr_2019` shipped)
4. A `RenderingConfig` (scale targets, annotation density, multi-floor composition)

…and emits ONE `DualDrawingBundle` containing:

- `working_drawing_model: WorkingDrawingModel`
- `permit_drawing_model: PermitDrawingModel`
- `provenance: DrawingProvenance` (Inv R16 — version triple)
- `cache_keys: C16CacheKeys`

C16 is purely descriptive. No decisions. No optimizations. No mutations of upstream inputs.

---

## § 0.2 — What C16 IS NOT

- NOT a CAD tool. No editing surface; downstream UIs may layer one on top.
- NOT a 3D model generator. The output is plan-view + section-view (orthographic 2D).
- NOT a BOQ generator. BOQ is C17's domain (Quote Comparison). C16 emits annotation HOOKS that let a BOQ join in.
- NOT a compliance checker. C2/C4/C9/C10 already enforced compliance; C16 reads their outputs and PRESENTS them.
- NOT a signature workflow. Per TNCDBR, a registered architect must sign. C16 outputs an unsigned data envelope; signature flow is OUT-OF-SCOPE.
- NOT a multi-jurisdiction localization layer at v1. Only `tn_cdbr_2019` ships. Other states (Karnataka BBMP, Maharashtra MCGM, Delhi DDA, etc.) are post-v1 LOCK backlog.
- NOT user-facing styling. Drawing TEMPLATES (line weights, hatching styles, title block layout) are downstream of C16.

---

## § 1 — Schema

### 1.1 — Top-level output: DualDrawingBundle

```python
@dataclass(frozen=True)
class DualDrawingBundle:
    """The full output of one C16 invocation."""
    source_selected_layout_signature: str
    working_drawing_model: WorkingDrawingModel
    permit_drawing_model: PermitDrawingModel
    upstream_advisory_flags: tuple[AdvisoryFlag, ...]  # byte-identical passthrough, Inv R8
    c16_version: str
    c16_drawing_schema_version: int
    jurisdiction_profile_id: str   # e.g. "tn_cdbr_2019"
    cache_keys: C16CacheKeys
```

### 1.2 — WorkingDrawingModel (construction use)

```python
@dataclass(frozen=True)
class WorkingDrawingModel:
    floor_plans: tuple[FloorPlanWorking, ...]      # one per floor, sorted by floor_level ASC
    section_views: tuple[SectionView, ...]         # Section A-A, B-B per TNCDBR rule 8
    roof_plan: Optional[RoofPlan]                  # None if single-level no terrace
    door_schedule: tuple[DoorScheduleEntry, ...]   # one per Door from C13
    window_schedule: tuple[WindowScheduleEntry, ...]  # one per Window from C9
    finish_schedule: tuple[FinishScheduleEntry, ...]  # per-room finish/material annotations
    recommended_scale: Literal["1:50", "1:75"]
```

`FloorPlanWorking` carries:
- room boundaries with **exact dimensions** (mm precision per TNCDBR norms)
- wall thicknesses (from C7 wall graph)
- door positions (from C13) with clear_width annotations
- structural column positions (from C7)
- plumbing stack overlays (from C10)
- furniture footprint indicators (from C9 furniture-aware sizer if shipped)
- annotation hooks for BOQ join (`boq_anchor_id` field on every billable element)

### 1.3 — PermitDrawingModel (municipal submission)

```python
@dataclass(frozen=True)
class PermitDrawingModel:
    site_plan: SitePlan                            # mandatory per TNCDBR rule 8(1)
    floor_plans: tuple[FloorPlanPermit, ...]       # simplified vs working — compliance-focused
    elevations: tuple[Elevation, ...]              # min 1 (front); typically 2 (front + side)
    section_views: tuple[SectionView, ...]         # min 1 per rule 8(1)
    key_plan: KeyPlan                              # scale 1:10000 per rule 8(1)(i)
    compliance_attestation: ComplianceAttestation  # FAR / setbacks / coverage summary
    rwh_overlay: Optional[RainWaterHarvestingOverlay]  # mandatory per rule 9(a)
    sewage_layout: Optional[SewageLayoutOverlay]   # mandatory per rule 9(b)
    parking_provision: ParkingProvision            # mandatory per NBC + TNCDBR
    north_arrow_orientation_deg: float
    recommended_scale: Literal["1:100", "1:150", "1:200"]
```

`FloorPlanPermit` differs from `FloorPlanWorking`:
- Same geometry but with compliance-focused annotations (setback dimensions, height markers)
- NO contractor-facing detail (joinery, finish schedules, BOQ hooks)
- Carries `setback_dimensions: SetbackDimensions` (front/rear/L/R per TNCDBR jurisdiction)

`ComplianceAttestation` is the most important new schema element:

```python
@dataclass(frozen=True)
class ComplianceAttestation:
    """Packaging of upstream compliance decisions into drawing-ready form.
    
    Inv R15: every field below MUST trace to a specific upstream output.
    C16 NEVER originates compliance claims — it only re-formats them.
    """
    plot_area_sqm: float                # from C4 plot analysis
    built_up_area_sqm: float            # from C9 room sizer
    plot_coverage_pct: float            # derived: built_up / plot
    far_used: float                     # from C2 feasibility
    far_permitted: float                # from C4 + jurisdiction profile
    building_height_m: float            # from C12 vertical alignment
    height_limit_m: float               # from jurisdiction profile (18.3m for non-high-rise per TNCDBR)
    floors_count: int                   # from C12
    setback_compliance: SetbackComplianceReport   # all 4 sides
    parking_compliance: ParkingComplianceReport   # from C2 parking_width_feasibility CheckResult
    rwh_present: bool                   # mandatory per TNCDBR rule 9(a)
    sewage_treatment_present: bool      # mandatory per TNCDBR rule 9(b)
    
    # Provenance — Inv R15 enforcement
    upstream_check_provenance: tuple[CheckProvenance, ...]
```

### 1.4 — Supporting envelope types (sketch level)

- `FloorPlanWorking`, `FloorPlanPermit`, `SectionView`, `Elevation`, `RoofPlan`, `KeyPlan`, `SitePlan`
- `DoorScheduleEntry`, `WindowScheduleEntry`, `FinishScheduleEntry`
- `SetbackDimensions`, `SetbackComplianceReport`
- `ParkingProvision`, `ParkingComplianceReport`
- `RainWaterHarvestingOverlay`, `SewageLayoutOverlay`
- `CheckProvenance`
- `RenderingConfig`, `JurisdictionProfile`

Each carries its own frozen schema. **Detailed shape of each is SKETCH at v0.1; B-C16-ENVELOPE-SCHEMA-LOCK pins exact field lists at v1.0 LOCK.**

---

## § 2 — Invariants (prefix R for "Renderer")

| ID | Description |
|---|---|
| R1 | Every input `SelectedLayout` produces exactly one `DualDrawingBundle`. |
| R2 | `working_drawing_model.floor_plans` and `permit_drawing_model.floor_plans` cover the SAME set of floors (per C12 output). Order: floor_level ASC. |
| R3 | Every room in upstream layout appears in EVERY floor plan it belongs to — no rooms omitted, no rooms invented. |
| R4 | Door schedule = exactly the doors emitted by C13 (no additions, no omissions). Same for window schedule = C9 windows. |
| R5 | All node-level and floor-level annotations cover exactly the set in upstream — sorted lex-ASC on stable IDs. |
| R6 | `compliance_attestation.plot_coverage_pct` = `built_up_area / plot_area * 100`, computed to FP precision; cross-checks against upstream C2 FAR output (within 1e-6). |
| R7 | **Byte-equal replay determinism.** Same `SelectedLayout` + same `JurisdictionProfile` + same `RenderingConfig` → byte-identical `DualDrawingBundle`. |
| R8 | `upstream_advisory_flags == input.advisory_flags`. C16 NEVER mutates C13/C14/C15 output. |
| R9 | `c16_drawing_schema_version` is populated, ≥ 1. Adding new fields requires MINOR bump; removing/renaming requires MAJOR. |
| R10 | `recommended_scale` for working = 1:50 or 1:75. For permit = 1:100 / 1:150 / 1:200. Strict subsets per TNCDBR rule 8(1). |
| R11 | `north_arrow_orientation_deg ∈ [0, 360)`. Inherited from C4 plot orientation. |
| R12 | **Permit drawing setback dimensions trace to C2 feasibility.** Inv R6 + R15 jointly enforce traceability. |
| R13 | RWH and sewage overlays are EITHER both present (mandatory per TNCDBR rule 9) OR both absent (only valid if upstream JurisdictionProfile explicitly waives — e.g. plot below threshold per rule 5). |
| R14 | Read-only consumer. No mutation of any input. |
| R15 | **Compliance provenance.** Every compliance claim in PermitDrawingModel.compliance_attestation MUST carry a `CheckProvenance` entry pointing back to the upstream CheckResult that originated it. C16 NEVER originates compliance assertions. |
| R16 | **Provenance triple.** `(c16_version, c16_drawing_schema_version, jurisdiction_profile_id)` populated, non-empty/non-negative. |
| R17 | **Multi-floor consistency.** `working_drawing_model.section_views` cuts intersect at least 2 of the floors when `floors_count ≥ 2`. (No single-floor section cuts on multi-storey buildings.) |
| R18 | **Empty schedule safety.** Floor with zero doors emits an empty `DoorScheduleEntry` tuple, not None. Same for windows / finishes. |

---

## § 3 — Phases

C16 follows the same phase-mirror pattern as C13/C14: small number of pure passes, each producing one section of output. No mutation, no backtracking, no optimization.

### Phase α — Geometric envelope assembly
Read C7 wall graph + C12 floor list + C9 room dimensions. Produce a per-floor canonical `FloorEnvelope` (rooms + walls + thicknesses). Lex-ASC sorted. Pure.

### Phase β — Door & window scheduling
Read C13 doors + C9 windows. Cross-index against `FloorEnvelope`. Produce `DoorScheduleEntry` / `WindowScheduleEntry` tuples (Inv R4).

### Phase γ — Working drawing assembly
Compose `WorkingDrawingModel`:
- Floor plans with construction-grade annotations
- Section A-A and B-B placements (Inv R17 for multi-floor)
- Roof plan (if applicable)
- Door/window/finish schedules

### Phase δ — Permit drawing assembly
Compose `PermitDrawingModel`:
- Simplified floor plans (compliance-focused only)
- Elevations (front mandatory; side recommended)
- Site plan with setbacks marked
- Key plan at scale 1:10000 (TNCDBR rule 8(1)(i))
- RWH + sewage overlays (Inv R13)
- Parking provision

### Phase ε — Compliance attestation packaging
Read upstream C2/C4/C9/C12 outputs. Build `ComplianceAttestation` with full provenance (Inv R15). Cross-check Inv R6.

### Phase ζ — Bundle assembly
Compose `DualDrawingBundle`. Stamp provenance triple (Inv R16). Canonical-sort everything (Inv R2, R5).

---

## § 4 — Errors

C16 error hierarchy mirrors C13/C14 two-tier:

- `DrawingRenderError` — base
- `LocalDrawingError` — always halts (config errors, schema drift from upstream)
  - `UpstreamSchemaDriftError` — C13/C14/C15 output schema doesn't match expected
  - `C16ConfigurationError` — invalid RenderingConfig (bad scale, etc.)
  - `JurisdictionNotSupportedError` — JurisdictionProfile not in v1 supported set
- `PerLayoutDrawingError` — STRICT raises / WARN collects
  - `MissingUpstreamDataError` — required upstream field is None/empty
  - `GeometryInconsistencyError` — wall graph references unknown room ID
  - `ComplianceProvenanceError` — Inv R15 violation (claim without upstream trace)

No NBC-style vetoes at C16 — those live at C2/C4/C10. C16 only PACKAGES the results.

---

## § 5 — Failure modes (strict vs WARN)

Same pattern as C13/C14:

- `strict_mode=True` → `PerLayoutDrawingError` raises immediately, batch halts
- `strict_mode=False` (WARN) → error caught, packaged into `FailedDrawingRender(source_signature, failure_record, partial_bundle)`, batch continues

`LocalDrawingError` always halts regardless of mode.

Typestate output:
- `SuccessfulDrawingRender` — carries `DualDrawingBundle`
- `FailedDrawingRender` — carries `FailureRecord` + optional partial bundle

`DrawingRenderBatchResult` parallels C13's `DoorPlacementBatchResult` and C14's `CirculationAnalysisBatchResult`.

---

## § 6 — Performance budget

Per-layout: ≤ 1.5s wallclock for typical residential (≤ 4 floors, ≤ 25 rooms total). Drawing assembly is mostly tuple construction + canonical sorting — bound by the input size, no super-linear algorithms.

Per-batch (50 candidates): ≤ 60s. Mostly serial; parallelism deferred to post-LOCK as B-C16-BATCH-PARALLELIZATION.

---

## § 7 — Testing strategy

Mirroring C13/C14:

- **Foundational layer**: schema validation, frozen dataclass + invariants → target 50 tests
- **Phase-by-phase units**: envelope assembly / door scheduling / working composition / permit composition / compliance packaging → target 40 tests
- **Multi-floor integration**: section cut traversal, vertical alignment consistency → target 15 tests
- **Compliance provenance**: every attestation traces to upstream CheckResult → target 12 tests
- **PBT**: ≥ 15 property-based tests covering R1-R18 invariants. Adversarial generators: zero-rooms floor, multi-storey with floor-mismatched walls, malformed jurisdiction profile, empty schedules.
- **Adversarial corpus**: 5 known-problematic Indian residential layouts (corner plot, irregular plot, multi-courtyard, multi-stack plumbing, ceremonial-sequence)
- **Real-pipeline e2e**: pipe REAL C13→C14→C16 outputs through

**Target: ≥ 132 tests at v1.0 LOCK.**

PBT layer mandatory at v1.0 (closing the gap C14 currently has). **B-C16-PBT-LAYER-COVERAGE filed as v1.0-LOCK-MANDATORY.**

---

## § 8 — Cache keys

```python
@dataclass(frozen=True)
class C16CacheKeys:
    upstream_cache_key: str         # composed from C13 + C14 + C15 cache_keys
    drawing_cache_key: str          # SHA-256 of upstream + jurisdiction + rendering_config_sig
    full_cache_key: str             # drawing + c16_version + drawing_schema_version
```

Standard tier structure. Cache invalidation on:
- Any upstream output change
- Jurisdiction profile change
- RenderingConfig change (scale, annotation density)
- C16_VERSION / DRAWING_SCHEMA_VERSION bump

---

## § 9 — Versioning constants

```python
C16_VERSION: str = "v0.1"
C16_DRAWING_SCHEMA_VERSION: int = 1
EXPECTED_C13_VERSION: str = "v1.0"
EXPECTED_C14_VERSION: str = "v0.2"   # if C14 ships at v0.2; else v1.0
EXPECTED_C15_VERSION: str = "v0.2"
SUPPORTED_JURISDICTIONS: frozenset[str] = frozenset({"tn_cdbr_2019"})
```

---

## § 10 — Public API (binding intent for v0.1)

```python
def render_drawings(
    *,
    selected_layout: SelectedLayout,
    jurisdiction_profile: JurisdictionProfile,
    config: RenderingConfig | None = None,
    upstream_advisory_flags: tuple[AdvisoryFlag, ...] = (),
    strict_mode: bool = True,
) -> SuccessfulDrawingRender | FailedDrawingRender: ...

def render_drawings_batch(
    *,
    selected_layouts: tuple[SelectedLayout, ...],
    jurisdiction_profile: JurisdictionProfile,
    config: RenderingConfig | None = None,
    upstream_advisory_flags_by_signature: dict[str, tuple[AdvisoryFlag, ...]] = {},
    strict_mode: bool = True,
) -> DrawingRenderBatchResult: ...
```

`SelectedLayout` is the upstream type that bundles C13 doors + C12 vertical-aligned floor structure + supporting metadata. Exact shape TBD (B-C16-SELECTED-LAYOUT-CONTRACT-LOCK). For v0.1, treat `SelectedLayout` as opaque — the upstream "selector" (downstream of C14/C15) emits it.

---

## § 11 — Open questions surfaced at v0.1 PROPOSED

These are intentionally NOT resolved at v0.1 SKETCH:

1. **Q1 — `SelectedLayout` upstream contract.** WHO selects the final layout from candidate set? C15 is descriptive only (per its A1 amendment). C17 is Quote Comparison. The selector step might be human-in-the-loop, or a thin selection logic, or a new component. C16 needs the contract pinned. → backlog `B-C16-SELECTED-LAYOUT-CONTRACT-LOCK`.

2. **Q2 — Output is data, not pixels — confirmed?** I've architected this as a data emitter, not a PDF generator. Pros: deterministic, testable, replay-stable, downstream renderer flexibility. Cons: still need a renderer downstream before the user sees anything. Confirm architectural call?

3. **Q3 — TNCDBR-only v1 — confirmed?** Other state jurisdictions (Karnataka BBMP, Maharashtra MCGM, Delhi DDA) are NOT in v1 scope. Confirm or expand.

4. **Q4 — Section view selection.** TNCDBR rule 8(1) mandates "sectional details" but doesn't specify A-A vs B-B vs other cuts. C16 v0.1 SKETCH defaults to one cut along longest dimension + one perpendicular. Confirm or backlog rule.

5. **Q5 — BOQ hooks vs full BOQ.** Working drawing carries `boq_anchor_id` hooks for downstream BOQ generation (C17 territory). Is this the right architectural seam, or should C16 emit BOQ directly?

6. **Q6 — Furniture footprints in working drawing.** Some Indian working drawings show furniture footprints (for client review); others don't (contractor doesn't need them). Include by default? Configurable via RenderingConfig?

7. **Q7 — Architect-signature workflow.** Per TNCDBR rule 8(1)(iii), the architect/engineer must sign drawings. This is HUMAN. Does C16 emit a "signature slot" placeholder in the model, or is that downstream?

These should each be adjudicated during the v0.2 critique walk + LOCK process.

---

## § 12 — Backlog at v0.1 PROPOSED

### LOCK-mandatory (must close before C16 v1.0 LOCK) — 8 items

| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C16-ENVELOPE-SCHEMA-LOCK | Pin exact field lists for FloorPlanWorking / FloorPlanPermit / SectionView / Elevation / etc. | v1.0 | M |
| B-C16-SELECTED-LAYOUT-CONTRACT-LOCK | Define the upstream `SelectedLayout` typestate. WHO emits it. | v1.0 | M |
| B-C16-SECTION-CUT-RULES-LOCK | Formalize which cuts are mandatory (A-A direction, B-B direction, special cases for irregular plots) | v1.0 | S |
| B-C16-RWH-SEWAGE-OVERLAY-DETAIL-LOCK | Pin exact field shapes for rain-water-harvesting and sewage overlays per TNCDBR rule 9 | v1.0 | M |
| B-C16-COMPLIANCE-PROVENANCE-FORMAT-LOCK | Pin `CheckProvenance` exact shape; ensure every upstream-component check is reachable | v1.0 | S |
| B-C16-PARKING-PROVISION-SCHEMA-LOCK | Pin `ParkingProvision` schema per NBC + TNCDBR matrix | v1.0 | S |
| B-C16-PBT-LAYER-COVERAGE | ≥15 PBTs covering R1-R18 invariants | v1.0 | M |
| B-C16-REGRESSION-SNAPSHOT-CORPUS | Pin reference outputs across the 5-scenario adversarial corpus | v1.0 | S |

### Post-LOCK / v1.x — 7 items

| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C16-MULTI-JURISDICTION-PROFILES | Add Karnataka BBMP, Maharashtra MCGM, Delhi DDA, others | v1.x | XL |
| B-C16-BATCH-PARALLELIZATION | Parallel batch rendering for 50+ candidates | v1.x | M |
| B-C16-ELEVATION-VIEW-SOLAR-ANNOTATIONS | Sun-path overlay on elevations | post-v1 | M |
| B-C16-3D-MODEL-EXPORT | Export to glTF or IFC for 3D visualization | post-v1 | XL |
| B-C16-RENDERER-OUTPUT-FORMAT-INTEGRATIONS | First downstream renderer integrations (PDF/SVG/DXF) | post-v1 | L |
| B-C16-ANNOTATION-DENSITY-AUTO-TUNING | Auto-collapse annotations when scale forces overlap | post-v1 | M |
| B-C16-ARCHITECT-SIGNATURE-WORKFLOW-INTEGRATION | Connect to digital signature flow (DSC / Aadhaar e-sign) | post-v1 | L |

### Routed amendment hints — 3 items

| ID | Description | Routed to |
|---|---|---|
| B-C17-BOQ-FROM-C16-ANCHORS | C17 consumes C16's BOQ hooks to generate BOQ document | C17 maintainer |
| B-PROJECT-SELECTOR-COMPONENT-DEFINITION | Define WHO selects the final layout (new component or extension of existing?) | Project-level decision |
| B-C2-PARKING-FEASIBILITY-PROVENANCE-FOR-C16 | C2's parking_width_feasibility CheckResult needs to expose provenance for C16's compliance_attestation | C2 maintainer |

### Cumulative backlog at v0.1 PROPOSED: 18 items

---

## § 13 — Dependencies on locked upstream

C16 depends on:

| Upstream | Version | What C16 consumes |
|---|---|---|
| C2 Feasibility Engine | LOCKED | FAR, plot dimensions, parking_width_feasibility CheckResult |
| C4 Plot Analysis | LOCKED v1.1 | plot orientation, area, plot type, jurisdiction context |
| C7 Structural Grid | LOCKED v0.7.3+v0.8 | wall graph, column positions, beam network |
| C9 Room Sizer | LOCKED | room dimensions, windows, optionally furniture footprints |
| C10 Wet-Zone Stack | LOCKED v1.0 | plumbing stack vertical alignment |
| C12 Vertical Alignment Engine | LOCKED v1.0 | floor-by-floor structural alignment, height |
| C13 Door Placement | LOCKED v1.0 | door geometry, advisory flags |
| C14 Connection-Graph Quality | LOCKED v0.2 OR LOCKED v1.0 | (optional) advisory flags from circulation analysis |
| C15 Layout Problem Finder | LOCKED v0.2 | (optional) problem reports for permit-drawing annotation |

C14 + C15 inputs are OPTIONAL — C16 functions without them (in WARN mode if absent; STRICT requires explicit "no_circulation_analysis" flag).

---

## § 14 — LOCK readiness

For v1.0 LOCK, C16 needs:

1. All 8 LOCK-mandatory backlog items closed
2. ≥132 tests passing including ≥15 PBTs
3. 5-scenario adversarial corpus integration-tested
4. Compliance provenance traced for every TNCDBR rule referenced in this spec
5. Performance budget verified at residential scale + 50-candidate batch
6. Multi-floor section cut validation across 3-floor and 4-floor cases
7. Ramalingam LOCK adjudication per Rule 8

v0.2 PROPOSED-DELTA expected from first critique walk. v0.3+ during implementation refines toward v1.0 LOCK.

---

## § 15 — Rule 8 / Rule 11 disclosure

Per Rule 8: LOCK authority is Ramalingam's alone. This v0.1 is PROPOSED, awaiting your adjudication.

Per Rule 11: web research conducted on TNCDBR 2019 rules 8/9, scale requirements (1:100 min for detailed plans; 1:10000 for key plans), and the Tamil Nadu permit-submission workflow. Source: Chennai Corporation, CMDA, and DTCP published TNCDBR 2019 documentation. Findings encoded into § 0.0, § 1.3, § 1.4, § 2 R10/R12/R13, and § 12 backlog items related to rule 8/9 overlays.

Self-analysis worst issues:

1. **Q1 — SelectedLayout upstream is the biggest unknown.** I've architected C16 as a pure renderer that takes a pre-selected layout. But the project doesn't yet have a definitive "selector" component. C15 is descriptive, C17 is Quote Comparison. Who selects which candidate becomes the FINAL? This needs project-level adjudication BEFORE C16 LOCK.

2. **§ 1 schema breadth is large.** WorkingDrawingModel + PermitDrawingModel + ComplianceAttestation + 12 supporting envelope types is a lot to lock at v1.0. Risk: SKETCH-level schema commitments that reviewers reject during critique walks. Mitigation: keep envelope shapes at SKETCH; pin during implementation.

3. **TNCDBR-only at v1 narrows market.** If BuildemUp ships to non-Tamil Nadu users, permit drawings won't work. Multi-jurisdiction (B-C16-MULTI-JURISDICTION-PROFILES) is post-v1 but should be on the near-horizon roadmap.

4. **Architect signature workflow is OUT-OF-SCOPE.** This is correct architecturally but may surprise the user. Drawings emitted by C16 are NOT submittable as-is — they need an architect's signature, which is human + downstream.

5. **No 3D model output.** Plan view + section view only. For C17 (Quote Comparison) or user-facing previews, 3D is filed as post-v1 backlog. If the product needs 3D walkthroughs at MVP, this becomes a critical gap.

---

## § 16 — End of v0.1 PROPOSED

This document constitutes C16 v0.1 PROPOSED. Awaiting Ramalingam LOCK adjudication or revision request.

Critique walks expected before LOCK. v0.2 PROPOSED-DELTA will incorporate adjudications.
