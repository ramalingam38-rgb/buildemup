# Component 16 — Dual-Drawing Renderer — v0.4 PROPOSED-DELTA

**Spec version:** v0.4 PROPOSED-DELTA over v0.3 PROPOSED-DELTA (over v0.2, over v0.1)
**Status:** PROPOSED. PENDING Ramalingam LOCK adjudication.
**Authored:** S47 (this session, post-critique-walk #3)
**Critique source:** External review document #3 on v0.3 PROPOSED-DELTA, 13 substantive items
**Reading order:** v0.1 → v0.2 → v0.3 → v0.4. Where deltas conflict, latest wins.

---

## What v0.4 changes vs v0.3

12 amendments (A1-A12 of v0.4 — local numbering), 1 meta-concern routed to LOCK-mandatory backlog (Item 13), 8 new invariants (R26-R33). Fixes 1 real bug I introduced in v0.3 A4 (Item 4 below). All 13 reviewer items resolved.

---

## A1 — Upstream canonicalization contract for SelectionResult

**Origin:** Reviewer #3 item 1.

**Problem:** v0.3 A1 separated replay_identity from audit_metadata but didn't define HOW upstream selectors must canonicalize the fields inside replay_identity. Two logically-identical selections could still produce different replay-identities if upstream ordering drifts.

**Amendment:** Define explicit canonicalization contract for `SelectionReplayIdentity` fields, binding on the upstream selector producer:

```python
@dataclass(frozen=True)
class SelectionReplayIdentity:
    """All fields MUST be canonicalized per the rules below.
    
    Canonicalization is the SELECTOR'S responsibility — C16 trusts
    inputs to be canonical. C16's __post_init__ verifies and rejects
    non-canonical inputs (per new Inv R26)."""
    
    selected_layout_signature: str
    """MUST be the stable signature emitted by the upstream layout
    pipeline (C11a/C11b/C12 chain). MUST be lex-ASC of layout candidates'
    canonical signatures."""
    
    selector_version: str
    """MUST be of the form '{selector_name}_v{semver}', e.g.
    'human_v1.0.0' or 'auto_aggregator_v0.3.2'. Normalized to lowercase."""
    
    selection_reason: SelectionReason
    """Enum value, normalized via .value attribute access."""
    
    candidate_ranking_snapshot: tuple[CandidateRanking, ...]
    """MUST be sorted lex-ASC by (final_rank: int, layout_signature: str).
    final_rank ties broken by layout_signature ASC. NO timestamps.
    NO selector-internal scores beyond the final rank (those go in
    audit_metadata if needed)."""
    
    upstream_problem_reports: tuple[ProblemReport, ...]
    """MUST be sorted lex-ASC by (source_layout_signature, problem_report_id).
    No timestamps. ProblemReport.checks within each report sorted per
    C15's canonical convention (lex-ASC by check_id)."""
```

**New Inv R26 (canonical replay-identity serializer):**
```
R26 — On __post_init__, C16 validates the SelectionReplayIdentity for:
  (a) candidate_ranking_snapshot is sorted by (final_rank, layout_signature)
  (b) upstream_problem_reports sorted by (source_layout_signature, problem_report_id)
  (c) selector_version matches the regex pattern
  (d) selection_reason is a valid enum value
Validation failure raises UpstreamSchemaDriftError (LocalDrawingError —
always halts; never collected in WARN mode).
```

**Routed amendment hint:** `B-PROJECT-SELECTOR-CANONICALIZATION-CONTRACT-LOCK` — the SELECTOR component (whoever produces SelectionResult) MUST publish a canonical serializer that BOTH C16 AND C17 import. Shared library, not duplicated.

**Cache-relevant:** NO (invariant tightening; same cache_keys produced).

---

## A2 — Per-ElementKind semantic field inclusion matrix

**Origin:** Reviewer #3 item 2.

**Problem:** v0.3 A3 said semantic_identity_hash uses "geometry-defining fields ONLY" but didn't enumerate which fields qualify per ElementKind. Different developers would hash different subsets while believing they obeyed the spec.

**Amendment:** Pin per-ElementKind inclusion matrix at SKETCH level:

**WALL kinds (WALL_EXTERNAL, WALL_INTERNAL_LOAD_BEARING, WALL_INTERNAL_PARTITION, WALL_PARAPET):**

| Field | In semantic_identity_hash? |
|---|---|
| start_x_mm (rounded per R7a) | ✓ |
| start_y_mm (rounded per R7a) | ✓ |
| end_x_mm (rounded per R7a) | ✓ |
| end_y_mm (rounded per R7a) | ✓ |
| thickness_mm (rounded per R7a) | ✓ |
| wall_kind (ElementKind.value) | ✓ |
| room_a_semantic_id (recursive) | ✓ |
| room_b_semantic_id (recursive) | ✓ |
| hatching_style | ✗ presentation |
| label_text | ✗ annotation |
| dimension_offset_mm | ✗ annotation |

**DOOR kinds (DOOR_EXTERNAL, DOOR_INTERNAL):**

| Field | In semantic_identity_hash? |
|---|---|
| wall_semantic_id (recursive) | ✓ |
| position_along_edge_mm (rounded) | ✓ |
| clear_width_mm (rounded) | ✓ |
| swing_direction | ✓ |
| hinge_side | ✓ |
| door_kind (ElementKind.value) | ✓ |
| is_main_entry | ✓ |
| door_number_label | ✗ annotation |
| schedule_anchor_id | ✗ presentation |
| finish_specification | ✗ annotation |

**WINDOW kinds (WINDOW_EXTERNAL, WINDOW_VENTILATOR):**

| Field | In semantic_identity_hash? |
|---|---|
| wall_semantic_id (recursive) | ✓ |
| position_along_edge_mm (rounded) | ✓ |
| width_mm, height_mm, sill_height_mm | ✓ |
| window_kind (ElementKind.value) | ✓ |
| label_text | ✗ annotation |
| schedule_anchor_id | ✗ presentation |

**STRUCTURAL kinds (COLUMN, BEAM, SLAB_FLOOR, SLAB_ROOF):**

| Field | In semantic_identity_hash? |
|---|---|
| Geometric position fields (rounded) | ✓ |
| structural_kind (ElementKind.value) | ✓ |
| Cross-section class (e.g. "rectangular_300x300") | ✓ |
| Material class enum (e.g. "rcc_m25") | ✓ |
| Exact material specification text | ✗ annotation |
| Steel reinforcement detail | ✗ annotation (separate structural detailing concern) |

**PLUMBING kinds (PLUMBING_STACK_FRESH_WATER, PLUMBING_STACK_WASTE, PLUMBING_STACK_RAIN_WATER):**

| Field | In semantic_identity_hash? |
|---|---|
| stack_kind (ElementKind.value) | ✓ |
| floor_level | ✓ |
| vertical_column_position_mm (rounded) | ✓ |
| stack_diameter_class enum | ✓ |
| Exact diameter mm | ✗ presentation |
| Pipe material text | ✗ annotation |

**COMPLIANCE OVERLAY kinds:** Per A10 below — these get their own identity_generation and follow a different stability policy.

**Pre-hash normalization procedure (Inv R27 NEW):**
1. Apply Inv R7a rounding (mm to integer, ratios to 4dp, degrees to 6dp)
2. Apply Inv R7c canonical JSON serialization
3. Recursively resolve `*_semantic_id` references to their own semantic_identity_hash values
4. Serialize as canonical JSON per Inv R7c
5. SHA-256 the resulting bytes
6. Take first 8 hex chars as semantic_identity_hash

Order of operations is fixed; different orderings produce different hashes.

**Cache-relevant:** YES (matrix change → C16_DRAWING_SCHEMA_VERSION bump 4 → 5; semantic_identity_hash values change).

---

## A3 — Canonical transform matrix conventions

**Origin:** Reviewer #3 item 3.

**Problem:** v0.3 A4 introduced dual-frame architecture but didn't specify the transform representation. Repeated transforms (LocalBuildingFrame → Plot → Geospatial) accumulate rounding drift.

**Amendment:** Define canonical transform representation:

```python
@dataclass(frozen=True)
class CanonicalTransform2D:
    """2D affine transform in row-major 3x3 matrix form.
    
    Composition: transform_chain = T_n @ ... @ T_2 @ T_1 applied to
    homogeneous column vector [x, y, 1]^T.
    
    Inv R28 — All 9 elements stored as int with FIXED precision
    multiplier (1e6 for rotation, 1 for translation in mm). NO float
    storage to prevent rounding drift on composition."""
    
    # Row 0: [cos*1e6, -sin*1e6, tx_mm]
    a00_micro: int  # cos(theta) * 1,000,000
    a01_micro: int  # -sin(theta) * 1,000,000
    a02_mm: int     # tx (translation X in mm, integer)
    # Row 1: [sin*1e6, cos*1e6, ty_mm]
    a10_micro: int
    a11_micro: int
    a12_mm: int
    # Row 2: [0, 0, 1] — implicit, not stored

@dataclass(frozen=True)
class TransformProvenance:
    """Immutable record of transform composition history."""
    source_frame: str       # e.g. "LocalBuildingFrame"
    target_frame: str       # e.g. "PlotAligned"
    composition_steps: tuple[str, ...]   # e.g. ("rotation", "translation")
    composed_at_phase: Literal["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]
```

**Inv R28 (transform composition precision):**
```
R28a — Round-trip precision: for any geometry point P,
       |T_inverse(T(P)) - P| ≤ 1mm (Manhattan distance).
R28b — Composition chain precision: for a chain of ≤ 5 transforms,
       cumulative precision drift ≤ 1mm.
R28c — All transforms in a DualDrawingBundle's geometry pipeline
       carry TransformProvenance records. NO anonymous transforms.
```

Frames in C16 v0.4: `LocalBuildingFrame`, `PlotAligned`, `Geospatial` (optional). Allowed transforms: `LocalBuildingFrame → PlotAligned` (via rotation + translation per v0.3 A4), `PlotAligned → Geospatial` (via reference if geospatial fields populated, otherwise identity).

**Cache-relevant:** NO (internal computation discipline; output unchanged).

---

## A4 — Deterministic LocalBuildingFrame orientation hierarchy (BUG FIX)

**Origin:** Reviewer #3 item 4. **This fixes a real bug I introduced in v0.3 A4.**

**Problem:** v0.3 A4 set LocalBuildingFrame +X = "parallel to the LONGEST building wall." This breaks determinism:
- Ties between equal-length walls
- Tiny geometry edits flipping the chosen wall
- L-shaped or U-shaped buildings with ambiguous dominant orientation
- Small harmless edits could rotate the local frame by 90° and invalidate downstream stable IDs

**Amendment:** Replace v0.3 A4's orientation rule with a deterministic hierarchy:

```
LocalBuildingFrame +X axis orientation, chosen by first applicable rule:

1. EXPLICIT HINT from upstream:
   If JurisdictionProfile or C4 PlotAnalysis carries an explicit
   `local_x_axis_orientation_deg`, use it. (For TNCDBR jurisdictions,
   typically aligned to plot's longest edge to match permit conventions.)

2. PRIMARY ENTRANCE WALL AXIS:
   The wall that the main entry door (is_main_entry=True from C13)
   sits on. +X axis = parallel to that wall, oriented such that the
   door's "outside" side is to the LEFT of +X (CCW from +X = inside
   of building).

3. LONGEST EXTERNAL WALL with tie-break:
   Among all walls with ElementKind == WALL_EXTERNAL, choose the one
   with the longest geometric length. Length ties (within Inv R7a
   1mm precision) broken by lex-ASC comparison of the wall's
   semantic_identity_hash. The chosen wall defines +X.

4. LEX-ASC fallback (defensive — should be unreachable):
   If no WALL_EXTERNAL elements exist (degenerate single-room
   "structure"), origin at any wall's geometric centroid; +X = lex-ASC
   first wall's start→end direction.
```

**Inv R29 (orientation determinism):**
```
R29a — Same FloorGeometry → same LocalBuildingFrame orientation
       (within Inv R7a precision).
R29b — The hierarchy step that fired is recorded in
       DualDrawingBundle.geospatial_reference.orientation_basis: 
       Literal["explicit_hint", "primary_entrance", "longest_wall", 
               "lex_fallback"]. Always populated.
R29c — Tiebreaks at any level use semantic_identity_hash (which is
       itself stable per A2 + R27), never raw geometric values that
       could drift.
```

**Migration from v0.3:** existing v0.3 builds (if any) used rule (3) without the tiebreak. Re-renders with v0.4 will produce identical orientations IF no ties exist; tied cases now resolve deterministically. `B-C16-V0.3-TO-V0.4-MIGRATION-AUDIT` filed to verify no in-flight builds are affected.

**Cache-relevant:** YES (orientation_basis field added → C16_DRAWING_SCHEMA_VERSION bump 5 → 6).

---

## A5 — Split legal completeness from readability quality

**Origin:** Reviewer #3 item 5.

**Problem:** v0.3's combined `submission_readiness` enum mixed governance (legal completeness) with readability (renderer-dependent, viewport-dependent). Viewport congestion suppressing a non-critical annotation could downgrade legal status — wrong coupling.

**Amendment:** Split into two orthogonal status fields:

```python
class LegalCompleteness(Enum):
    """Pure legal/governance status — independent of rendering."""
    LEGALLY_COMPLETE = "legally_complete"  # all permit-critical overlays present + upstream-authoritative
    LEGALLY_INCOMPLETE = "legally_incomplete"  # some permit-critical overlay absent
    UNSAFE_FOR_SUBMISSION = "unsafe_for_submission"  # validation failures detected

class ReadabilityStatus(Enum):
    """Pure presentation-quality status — renderer/viewport dependent."""
    READABLE = "readable"                              # all annotations fit without suppression
    REVIEW_RECOMMENDED = "review_recommended"          # non-critical annotation suppressed
    READABILITY_DEGRADED = "readability_degraded"      # critical annotation suppressed

@dataclass(frozen=True)
class PermitDrawingModel:
    # Replaces v0.2 A4's single submission_readiness:
    legal_completeness: LegalCompleteness    # governance
    readability_status: ReadabilityStatus    # presentation
    requires_professional_signature: bool = True   # always True (preserved from v0.2)
    missing_overlays: tuple[str, ...] = ()
    signature_placeholder: Optional[SignaturePlaceholder] = None
```

**Inv R30 (status orthogonality):**
```
R30a — legal_completeness derives ONLY from UPSTREAM_AUTHORITATIVE
       AttestedValue presence + permit-critical overlay presence.
       NEVER influenced by readability or renderer state.
R30b — readability_status derives from ReadabilityDiagnostics
       (from v0.3 A6 / now A9 below). Independent of legal status.
R30c — A drawing can be LEGALLY_COMPLETE + READABILITY_DEGRADED
       (legally fine but hard to read). A drawing can be
       LEGALLY_INCOMPLETE + READABLE (clean rendering of incomplete
       content). Both are valid; neither orthogonal status implies
       the other.
```

**Downstream UI guidance:**
- `LEGALLY_COMPLETE + READABLE`: ready for architect signature
- `LEGALLY_COMPLETE + REVIEW_RECOMMENDED`: ready for architect signature; user warned about overlap
- `LEGALLY_COMPLETE + READABILITY_DEGRADED`: ready for signature legally, but visual review strongly recommended before submission
- `LEGALLY_INCOMPLETE`: NOT ready regardless of readability
- `UNSAFE_FOR_SUBMISSION`: hard block regardless of readability

**Cache-relevant:** YES (schema change → C16_DRAWING_SCHEMA_VERSION bump 6 → 7).

---

## A6 — Schema-version-aware optional field handling

**Origin:** Reviewer #3 item 6.

**Problem:** v0.3 A7 rule #3 said "Optional[None] fields OMITTED from canonical JSON entirely." Reviewer correctly notes this conflates:
- field absent because schema version doesn't have it
- field absent because value is None
- field intentionally omitted
Hurts forward-compatibility for future schema migrations.

**Amendment:** Preserve omission rule for canonical replay (it's right for determinism), but add a separate **schema descriptor** companion:

```python
@dataclass(frozen=True)
class SchemaDescriptor:
    """Companion metadata for forward-compatible deserialization.
    
    EXCLUDED from canonical replay-identity (per Inv R7). EMITTED as
    a separate JSON sibling, not embedded in DrawingModel.
    
    Carries the optional-field registry: which fields exist in this
    schema version, even if they're None / absent. Consumers reading
    older bundles use the older schema_descriptor to disambiguate
    'absent-because-old-schema' from 'absent-because-None'."""
    
    schema_version: int
    optional_field_registry: tuple[OptionalFieldEntry, ...]
    
@dataclass(frozen=True)
class OptionalFieldEntry:
    field_path: str           # e.g. "PermitDrawingModel.signature_placeholder"
    introduced_at_schema_version: int
    deprecated_at_schema_version: Optional[int] = None
```

**Canonical JSON rule (refines v0.3 A7 rule #3):**
- Field absent: value is None AND field exists in current schema → semantically equivalent to None
- Field deserialization: consumer checks against schema_descriptor; if field not in registry for the bundle's schema_version, treat as "field didn't exist yet" (different from "field exists and is None")

**Cache-relevant:** NO (canonical replay rules unchanged; schema_descriptor is a sibling artifact, not part of replay-identity).

---

## A7 — Hard global safety caps overriding RenderingConfig

**Origin:** Reviewer #3 item 7.

**Problem:** v0.3 A8 moved coordinate bounds to RenderingConfig for scalability. But arbitrary user configs could disable protections (set bounds to infinity), allow pathological coordinates, create memory/performance explosions.

**Amendment:** Add **HARD CEILING** constants that override any RenderingConfig:

```python
# Module-level constants (cannot be overridden):
HARD_CEILING_PLOT_X_MM: Final[int] = 1_000_000        # 1 km — covers township scale
HARD_CEILING_PLOT_Y_MM: Final[int] = 1_000_000
HARD_CEILING_BUILDING_X_MM: Final[int] = 500_000      # 500m — covers largest commercial complex
HARD_CEILING_BUILDING_Y_MM: Final[int] = 500_000
HARD_CEILING_BUILDING_Z_MAX_MM: Final[int] = 500_000  # 500m — taller than typical skyscraper limit
HARD_CEILING_BUILDING_Z_MIN_MM: Final[int] = -50_000  # 50m basement depth
```

**Inv R31 (hard safety cap precedence):**
```
R31 — Effective coordinate bounds = MIN(
        RenderingConfig.coordinate_bounds.{plot|building}_{x|y|z}_{max|min}_mm,
        HARD_CEILING_{PLOT|BUILDING}_{X|Y|Z}_{MAX|MIN}_MM
      )
      
      Config bounds NEVER exceed hard ceilings. A config that tries
      to declare bounds beyond hard ceiling raises C14ConfigurationError
      at config construction time (LocalDrawingError — always halts).
```

These hard ceilings are loose enough to cover any imaginable BuildemUp use case (1km × 1km plot, 500m building) but tight enough to reject pathological inputs (negative dimensions, infinite ranges, etc.).

**Cache-relevant:** NO (defensive constant; same valid bundles produced).

---

## A8 — O(n) referential integrity via hash-map indexing

**Origin:** Reviewer #3 item 8.

**Problem:** v0.3 A2's R24 referential integrity checks are clean for residential ≤25 rooms but naïve implementation is O(n²) for n geometry references. Apartment complexes / campus scale violates the per-batch performance budget.

**Amendment:** Specify O(n) validation algorithm in the v0.4 SKETCH:

```python
def _validate_referential_integrity(bundle: DualDrawingBundle) -> None:
    """O(n) implementation of Inv R24a/b/c."""
    
    # Build geometry_id → FloorGeometry index (O(n_floors))
    geometry_index: dict[str, FloorGeometry] = {}
    for fg in bundle.floor_geometries:
        if fg.geometry_id in geometry_index:
            raise GeometryInconsistencyError(
                f"R24c violation: duplicate geometry_id {fg.geometry_id!r}"
            )
        geometry_index[fg.geometry_id] = fg
    
    # R24a: every geometry_ref resolves exactly once (O(n_floors))
    working_refs: set[str] = set()
    for wfp in bundle.working_drawing_model.floor_plans:
        if wfp.geometry_ref not in geometry_index:
            raise GeometryInconsistencyError(
                f"R24a violation: working geometry_ref {wfp.geometry_ref!r} not found"
            )
        working_refs.add(wfp.geometry_ref)
    permit_refs: set[str] = set()
    for pfp in bundle.permit_drawing_model.floor_plans:
        if pfp.geometry_ref not in geometry_index:
            raise GeometryInconsistencyError(
                f"R24a violation: permit geometry_ref {pfp.geometry_ref!r} not found"
            )
        permit_refs.add(pfp.geometry_ref)
    
    # R24b: every FloorGeometry is referenced (O(n_floors))
    all_geometry_ids = set(geometry_index.keys())
    orphan_in_working = all_geometry_ids - working_refs
    orphan_in_permit = all_geometry_ids - permit_refs
    if orphan_in_working or orphan_in_permit:
        raise GeometryInconsistencyError(
            f"R24b violation: orphan geometry_ids in "
            f"working={sorted(orphan_in_working)!r}, permit={sorted(orphan_in_permit)!r}"
        )
```

**Performance contract:** O(n) where n = number of FloorGeometry instances. Hash-map lookup is amortized O(1). Total: O(n_floors × hash_cost) ≈ linear in floor count.

**Additionally:** uniqueness enforcement is done DURING construction (not at __post_init__ end), so duplicate IDs are caught before any other invariant runs. Mirrors C13's "fail fast" pattern.

**Cache-relevant:** NO (algorithm specification; same outputs).

---

## A9 — Separate presentation-quality signature

**Origin:** Reviewer #3 item 9.

**Problem:** v0.3 A6 excluded ReadabilityDiagnostics from canonical equality. Two bundles can now be canonically "equal" while one suppressed critical annotations and the other didn't — operationally not equivalent.

**Amendment:** Add a separate `presentation_signature` to DualDrawingBundle:

```python
@dataclass(frozen=True)
class DualDrawingBundle:
    # ... existing fields ...
    
    canonical_replay_signature: str
    """SHA-256 of canonical replay-identity (per Inv R7). EXCLUDES
    timings, diagnostics, audit metadata."""
    
    presentation_signature: str
    """SHA-256 INCLUDING:
    - canonical_replay_signature
    - readability_diagnostics (if present)
    - phase_timings (if present)
    - schema_descriptor digest
    
    Two bundles with same canonical_replay_signature but different
    presentation_signature mean: same logical drawing, different
    presentation state. Useful for cache tier separation."""
```

**Inv R32 (signature relationship):**
```
R32a — canonical_replay_signature is computed first, then included
       as a prefix in the input to presentation_signature.
R32b — Two bundles with identical canonical_replay_signature MAY
       have different presentation_signature (different diagnostics,
       different timings).
R32c — Two bundles with identical presentation_signature MUST have
       identical canonical_replay_signature.
```

**Cache tier separation:**
- L1 cache (cheap, hot): keyed by presentation_signature
- L2 cache (warm): keyed by canonical_replay_signature — can serve "same logical drawing" hits across different presentation states

**Cache-relevant:** YES (new field → C16_DRAWING_SCHEMA_VERSION bump 7 → 8).

---

## A10 — Identity generation + breaking-change protocol

**Origin:** Reviewer #3 item 10.

**Problem:** v0.3 A3's stability guarantee for semantic_identity_hash conflicts with intentional future migrations. Coordinate system shifts, geometry-normalization fixes, wall-topology corrections SHOULD change semantic identity — but current wording strongly biases toward stability.

**Amendment:** Add `identity_generation` field to ElementIdentity:

```python
@dataclass(frozen=True)
class ElementIdentity:
    """Two-tier identity, generation-scoped."""
    
    identity_generation: int          # NEW in v0.4
    """Identity stability scope. Same generation → semantic_identity_hash
    is stable. Different generation → all bets off; consumers must
    re-resolve by other means.
    
    Generation BUMPS happen on:
    - Coordinate system migrations (e.g. v0.4 → v1.0 LocalBuildingFrame
      changes)
    - Geometry normalization fixes (e.g. wall-topology bug fixes)
    - Element-kind taxonomy MAJOR changes (e.g. WALL split into 5 sub-kinds)
    
    Generation does NOT bump on:
    - Adding new optional metadata fields
    - Adding new ElementKind values (additive)
    - Changing presentation fields
    - Schema MINOR bumps"""
    
    semantic_identity_hash: str
    """STABLE WITHIN GENERATION. Computed per A2 + R27. Cross-generation
    comparison is undefined."""
    
    presentation_identity_hash: str
    """Changes with any content change. See v0.3 A3."""
```

**Inv R33 (identity generation discipline):**
```
R33a — identity_generation is a module-level constant
       (C16_IDENTITY_GENERATION). Incrementing requires MAJOR
       version bump of C16_DRAWING_SCHEMA_VERSION and is documented
       in the v(N).x release notes as a "breaking change."
R33b — All ElementIdentity instances in a single DualDrawingBundle
       share the SAME identity_generation. Mixed-generation bundles
       are invalid (validated at __post_init__).
R33c — Migrations bump identity_generation. Consumers cache-busting
       on generation change MUST re-resolve cross-references.
```

C16 v0.4 starts at `C16_IDENTITY_GENERATION = 1`. The v0.3 A4 → v0.4 A4 orientation hierarchy fix doesn't bump generation (it's a bug fix, not a coordinate system change — semantic_identity_hash for non-tied geometries is unchanged).

**Cache-relevant:** YES (new field → C16_DRAWING_SCHEMA_VERSION bump 8 → 9).

---

## A11 — Canonical epsilon policy

**Origin:** Reviewer #3 item 11.

**Problem:** v0.3 A9 defined output rounding (R7a) but not internal comparison tolerances. Risk: byte-equal outputs but internal computation divergence.

**Amendment:** Pin epsilon policy:

```python
# Module-level constants:
EPSILON_COORDINATE_MM: Final[int] = 1                  # coordinate equality / Manhattan distance
EPSILON_RATIO: Final[float] = 1e-4                     # ratio equality (e.g. plot_coverage_pct)
EPSILON_ANGLE_DEG: Final[float] = 1e-6                 # angle equality
EPSILON_TRANSFORM_CHAIN_MM: Final[int] = 1             # cumulative drift over ≤5-step transform chain
EPSILON_AREA_SQM: Final[float] = 0.01                  # area equality (0.01 sqm = 100 sq cm)
```

**Inv R34 (epsilon discipline):**
```
R34a — All internal comparisons use the appropriate epsilon constant.
       No bare `==` on floats.
R34b — Transform composition guarantees cumulative drift ≤
       EPSILON_TRANSFORM_CHAIN_MM (Manhattan) over ≤5-step chains.
R34c — Cross-frame tolerance reconciliation: when comparing
       coordinates that traversed different frames, use 2 ×
       EPSILON_COORDINATE_MM (accounts for round-trip accumulation).
R34d — These constants are NOT user-configurable. Per Item 7
       discipline (no unsafe runtime flexibility for safety-critical
       constants).
```

**Cache-relevant:** NO (internal discipline; same outputs).

---

## A12 — Promote renderer conformance contract to architectural appendix

**Origin:** Reviewer #3 item 12.

**Problem:** v0.3 left B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK as a LOCK-mandatory backlog item. Reviewer correctly observes it's architecture-critical, not auxiliary: PDF/SVG/DXF renderers may diverge on line semantics, annotation placement, scaling — affecting legal interpretation.

**Amendment:** Add new **§ 17 (Renderer Conformance Contract Appendix)** to the spec, SKETCH-level at v0.4. Promoted out of backlog into the main specification body.

```
§ 17 — Renderer Conformance Contract (SKETCH at v0.4)

A "C16-Conformant Renderer" is any downstream component that
consumes a DualDrawingBundle and produces visual output (PDF/SVG/DXF/
canvas/etc.). To claim conformance, a renderer MUST:

§ 17.1 — Geometry interpretation:
  - Coordinates emitted in LocalBuildingFrame, units mm, right-handed
    Cartesian (per A4 of v0.3 + v0.4)
  - Element identity stable across renders for same input
    (presentation_identity_hash equivalent)
  - Transforms applied per CanonicalTransform2D representation (A3)

§ 17.2 — Line semantics:
  - WALL_EXTERNAL: solid line, weight class "heavy"
  - WALL_INTERNAL_LOAD_BEARING: solid line, weight class "medium"
  - WALL_INTERNAL_PARTITION: solid line, weight class "light"
  - WALL_PARAPET: dashed line, weight class "medium"
  - HIDDEN lines (e.g. items above cut plane): dashed, weight class "light"
  - SECTION CUT line: dashed-dotted, weight class "heavy"
  Weight class mapping to absolute pen width is renderer-dependent
  but MUST preserve relative ordering: heavy > medium > light.

§ 17.3 — Text anchor positioning:
  - All text annotations carry anchor_point (x, y in mm) and
    anchor_alignment enum (top-left, top-center, ..., bottom-right)
  - Renderer MUST honor anchor + alignment without re-flow
  - Text overflow handling: renderer MAY truncate but MUST emit
    a warning into ReadabilityDiagnostics

§ 17.4 — Scale fidelity:
  - DualDrawingBundle.working_drawing_model.recommended_scale and
    permit_drawing_model.recommended_scale are AUTHORITATIVE
  - Renderer at differing scale MUST emit a scale-mismatch warning

§ 17.5 — Determinism:
  - Same DualDrawingBundle + same renderer version + same target
    format → byte-equal output (when possible per format)
  - Non-deterministic rendering (e.g. PDF date stamps) MUST be
    suppressed for conformance

§ 17.6 — Conformance attestation:
  - Renderer publishes a renderer_version + renderer_conformance_attestation_id
  - Downstream consumers can verify the attestation against a public
    registry (LOCK-mandatory: B-C16-RENDERER-CONFORMANCE-REGISTRY-LOCK)
```

At v0.4 this is **SKETCH-level Appendix only**. v1.0 LOCK requires the appendix matured into binding contract.

**Cache-relevant:** NO (renderer-side contract; doesn't affect C16's output schema).

---

## § 12 — Backlog updates from critique walk #3

### New LOCK-mandatory items (added to v0.3's 14 → 17 total)

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-C16-DECOMPOSITION-DECISION-LOCK** | **(META — from Item 13)** Adjudicate before v1.0 LOCK: (a) keep C16 unified, (b) decompose into C16a Geometry + C16b Compliance + C16c Drawing + C16d Serialization, (c) defer decomposition to v2.x. Industry precedent (Parasolid, ACIS, OpenCascade) favors decomposition; BuildemUp's residential scope may justify staying unified. | **v1.0-LOCK-MANDATORY** | L (the decision itself); XL (if decomposition chosen) |
| B-PROJECT-SELECTOR-CANONICALIZATION-CONTRACT-LOCK | Shared canonical serializer for SelectionReplayIdentity, imported by both C16 and C17 (avoid duplicated implementations) | v1.0 (project-level) | M |
| B-C16-V0.3-TO-V0.4-MIGRATION-AUDIT | Verify no in-flight builds depend on the v0.3 A4 "longest wall" rule before v0.4 A4 lands | v1.0 | S |
| B-C16-RENDERER-CONFORMANCE-REGISTRY-LOCK | Public registry of conformant renderer attestations per § 17.6 | v1.0 | M |
| B-C16-EPSILON-POLICY-CI-CHECK | CI test: every internal float comparison uses an EPSILON_ constant, not bare ==. Static analysis pass. | v1.0 | S |

### New post-LOCK items

| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C16-SCHEMA-MIGRATION-FRAMEWORK | Implement SchemaDescriptor + optional-field registry deserialization framework | v1.x | L |
| B-C16-TRANSFORM-PROVENANCE-AUDIT-CORPUS | Adversarial corpus exercising 5-step transform chains for R28 verification | v1.x | M |

### Cumulative backlog at v0.4 PROPOSED: 40 items

- 17 LOCK-mandatory (was 14 at v0.3 → +3 from walk #3 + B-C16-DECOMPOSITION-DECISION-LOCK as meta-item)
- 20 post-LOCK / v1.x (was 16 + 2 new + 2 from compositional planning)
- 3 routed amendment hints (unchanged)

---

## Cumulative invariant table (after v0.1 + v0.2 + v0.3 + v0.4)

| ID | Description | Source |
|---|---|---|
| R1-R18 | Original v0.1 invariants | v0.1 |
| R19 | Coordinate bounds (config-driven per v0.3 A8 + hard ceilings per v0.4 A7) | v0.2 A2 |
| R20 | Geometry parity | v0.2 A3 |
| R21 | Submission-readiness completeness (now split into legal vs readability — see R30) | v0.2 A4 |
| R22 | Provenance authority discipline | v0.2 A5 |
| R23 | Mandatory section cuts | v0.2 A8 |
| R24 | Geometry referential integrity (O(n) per v0.4 A8) | v0.3 A2 |
| R25 | Submission-readiness gated by UPSTREAM_AUTHORITATIVE only | v0.3 A5 |
| **R26** | Canonical replay-identity serializer validation | **v0.4 A1** |
| **R27** | Per-ElementKind semantic field inclusion matrix | **v0.4 A2** |
| **R28** | Transform composition precision (a/b/c) | **v0.4 A3** |
| **R29** | LocalBuildingFrame orientation determinism (a/b/c) | **v0.4 A4** |
| **R30** | Legal completeness ⊥ readability status (a/b/c) | **v0.4 A5** |
| **R31** | Hard safety cap precedence | **v0.4 A7** |
| **R32** | Replay vs presentation signature relationship (a/b/c) | **v0.4 A9** |
| **R33** | Identity generation discipline (a/b/c) | **v0.4 A10** |
| **R34** | Canonical epsilon policy (a/b/c/d) | **v0.4 A11** |

Total invariants: 34 (was 25 at v0.3 close).

---

## Version bumps required at v0.4

- `C16_VERSION`: v0.3 → v0.4
- `C16_DRAWING_SCHEMA_VERSION`: 4 → 9 (large jump: A2, A4, A5, A9, A10 all schema-altering)
- `C16_IDENTITY_GENERATION`: NEW = 1 (introduced in A10)

---

## Rule 8 / Rule 11 disclosure

Per Rule 8: LOCK authority is Ramalingam's alone. This delta is **PROPOSED, PENDING your adjudication**. Lock applies after explicit "lock it" / "v0.4 LOCKED."

Per Rule 11: web research conducted for walk #3 on industry component decomposition patterns. Findings: mature CAD/BIM systems consistently separate geometry kernel (Parasolid/ACIS/OpenCascade) from CAD application, rendering engine, and compliance layers. This validates Item 13's "spec breadth explosion" concern as a real architectural pattern. Recorded as B-C16-DECOMPOSITION-DECISION-LOCK (v1.0-LOCK-MANDATORY).

Self-analysis worst remaining gaps after this delta:

1. **A4 orientation hierarchy fix is the most consequential change in v0.4** — it eliminates the determinism bug I introduced in v0.3 A4. Same accountability pattern as v0.2's timestamp bug (caught at walk #2). I'm flagging that I've now introduced 2 determinism bugs across 3 critique walks; reviewers caught both. The pattern suggests I should run **internal determinism review** before submitting each delta — adding to my own session discipline checklist.

2. **A10 identity_generation introduces a forward-compatibility lever I haven't tested.** Bumping generation invalidates all prior cache entries — that's by design but operationally significant. v1.0 should land with `C16_IDENTITY_GENERATION = 1` and the bump protocol exercised at least once in CI before real generation bumps.

3. **B-C16-DECOMPOSITION-DECISION-LOCK is the most strategic open question** at v0.4. The decomposition decision affects not just C16 but the project's overall component count. If decomposed: 17 → 20 components (Track 3 grows). If unified: C16 stays as-is but bloated.

4. **§ 17 Renderer Conformance Appendix is SKETCH-only.** A binding renderer contract is genuinely architecture-critical; promoting from backlog into the appendix is right, but the appendix itself is incomplete. v1.0 LOCK should mature it into a binding sub-specification.

5. **Diminishing returns concern from walk #3 stands.** This delta closes 12 of 13 items rigorously. Walk #4 (if you choose it) will likely find smaller items still. At some point the project's standard convention applies: SKETCH-level LOCK at v0.4, refine during implementation toward v1.0.

---

## § 16 — End of v0.4 PROPOSED-DELTA

This document constitutes the C16 v0.4 PROPOSED-DELTA. Awaiting Ramalingam LOCK adjudication.

Three forward paths:
- **`lock it` / `v0.4 LOCKED`** → composed v0.4 LOCKED SPEC across v0.1+v0.2+v0.3+v0.4; build can begin per spec-first discipline
- **Critique walk #4** → I produce v0.5 PROPOSED-DELTA if walk reveals further issues
- **Revisions** → reshape v0.4 PROPOSED-DELTA-2 per your direction

Per Rule 8 — your call.
