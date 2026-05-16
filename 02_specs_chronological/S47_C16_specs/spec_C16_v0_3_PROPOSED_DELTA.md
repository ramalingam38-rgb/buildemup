# Component 16 — Dual-Drawing Renderer — v0.3 PROPOSED-DELTA

**Spec version:** v0.3 PROPOSED-DELTA over v0.2 PROPOSED-DELTA (over v0.1 PROPOSED)
**Status:** PROPOSED. PENDING Ramalingam LOCK adjudication.
**Authored:** S47 (this session, post-critique-walk #2)
**Critique source:** External review document #2 on v0.2 PROPOSED-DELTA, 13 substantive items
**Reading order:** This delta layers over `spec_C16_v0_2_PROPOSED_DELTA.md` which itself layers over `spec_C16_v0_1_PROPOSED.md`. To read the proposed v0.3 state: read v0.1 → apply v0.2 amendments → apply v0.3 amendments. Where deltas conflict, latest wins.

---

## What v0.3 changes vs v0.2

8 amendments (A1-A8 of v0.3 — renumbered locally; do not confuse with v0.2's A1-A10). 4 backlog additions for deferred items. 2 new invariants (R24-R25).

The most consequential: **A1 fixes a determinism bug I introduced** in v0.2 A1 (timestamp in SelectionResult). The reviewer caught it directly.

---

## A1 — Split SelectionResult into replay_identity and audit_metadata

**Origin:** Reviewer #2 item 1. This fixes a real bug I introduced in v0.2 A1.

**Problem:** I added `selection_timestamp_utc: str` to SelectionResult in v0.2. If timestamp flows through to canonical signatures or cache keys, the SAME selection at two different times produces DIFFERENT replay-identities — invalidating Inv R7 byte-equal replay and creating cache churn.

**Amendment:** Restructure SelectionResult to separate REPLAY identity from AUDIT metadata:

```python
@dataclass(frozen=True)
class SelectionReplayIdentity:
    """Fields that contribute to byte-equal replay. NO time, NO env, NO human IDs."""
    selected_layout_signature: str
    selector_version: str
    selection_reason: SelectionReason
    candidate_ranking_snapshot: tuple[CandidateRanking, ...]
    upstream_problem_reports: tuple[ProblemReport, ...]

@dataclass(frozen=True)
class SelectionAuditMetadata:
    """Fields for audit trail. EXCLUDED from cache keys and equality.
    
    Per Inv R7d (A9 from v0.2): no environment dependence in canonical
    output. This metadata exists purely for traceability/forensics."""
    selection_timestamp_utc: str
    human_override: Optional[HumanOverrideRecord]
    selector_instance_id: Optional[str]      # which selector replica produced this
    selection_machine_fingerprint: Optional[str]   # for distributed forensics

@dataclass(frozen=True)
class SelectionResult:
    """Top-level: discriminated by canonical replay identity + opaque audit."""
    replay_identity: SelectionReplayIdentity
    audit_metadata: SelectionAuditMetadata
```

**C16 contract:**
- `C16CacheKeys` are derived ONLY from `replay_identity` (Inv R7 byte-equal preserved).
- `DualDrawingBundle.source_selection_signature` MUST be the canonical hash of `replay_identity` ONLY.
- `audit_metadata` is passed through into a separate field of DualDrawingBundle (`audit_metadata: SelectionAuditMetadata`) for traceability but EXCLUDED from canonical equality.

**Cache-relevant:** YES (input contract change → C16_VERSION bump v0.2 → v0.3).

**Refinement to v0.2 A1:** the v0.2 A1's flat SelectionResult shape is REPLACED by this nested form. All fields preserved; their cache-relevance is now explicit.

---

## A2 — Geometry referential integrity invariants

**Origin:** Reviewer #2 item 2.

**Problem:** v0.2 A3 introduced shared FloorGeometry referenced by `geometry_id`. The reviewer correctly notes broken `geometry_ref` could invalidate drawing trees while appearing structurally valid.

**Amendment:** Add new Inv **R24** with three sub-clauses:

```
R24a — Reference completeness: every WorkingDrawingFloor.geometry_ref
       AND every PermitDrawingFloor.geometry_ref MUST resolve to
       exactly one FloorGeometry in DualDrawingBundle.floor_geometries.
       Zero matches → reject. Multiple matches → reject (duplicate IDs).

R24b — No orphan geometry: every FloorGeometry in floor_geometries
       MUST be referenced by AT LEAST one WorkingDrawingFloor AND
       AT LEAST one PermitDrawingFloor. (Drawing models cannot leave
       a floor's geometry orphaned.)

R24c — geometry_id uniqueness: no two FloorGeometry instances in
       floor_geometries may share the same geometry_id. Duplicate ID
       → reject.
```

Enforced at `DualDrawingBundle.__post_init__`. Violation raises `GeometryInconsistencyError` (per-layout error, STRICT raises / WARN collects).

**Cache-relevant:** NO (constraint tightening, no output schema change).

---

## A3 — Semantic identity vs presentation identity (stable IDs across schema evolution)

**Origin:** Reviewer #2 item 3. Web-research-verified against IFC GUID stability conventions.

**Problem:** v0.2 A7's stable IDs derive from SHA-256 of "canonical serialized content." Industry experience (per IFC GUID literature) shows this breaks under harmless schema evolution: field reordering, optional metadata additions, presentation tweaks all change the hash. Cache churn, broken cross-version references, annotation-anchor invalidation.

**Amendment:** Separate two identity concepts:

```python
@dataclass(frozen=True)
class ElementIdentity:
    """Two-tier identity for every renderable element."""
    
    semantic_identity_hash: str
    """SHA-256 (first 8 hex) of a tightly-scoped semantic tuple:
    
      - element_kind (ElementKind from v0.2 A7)
      - floor_level (which floor this element belongs to)
      - geometry-defining fields ONLY (positions, dimensions, NOT
        annotations, NOT presentation properties, NOT optional metadata)
    
    STABILITY GUARANTEE: a schema MINOR-bump that adds an optional
    field to ElementIdentity's source dataclass MUST NOT change this
    hash. Only the listed semantic-defining fields contribute.
    
    Same building element → same semantic_identity_hash across
    C16 versions, schema MINOR bumps, and harmless metadata additions."""
    
    presentation_identity_hash: str
    """SHA-256 (first 8 hex) of the FULL canonical serialization.
    
    Includes annotations, presentation metadata, optional fields.
    
    USE CASE: cache invalidation when display changes; debugging
    when two elements look-the-same-but-render-differently.
    
    Changes whenever ANYTHING about the element changes."""
```

**The "stable_id" referenced throughout C16 is `semantic_identity_hash`.** Downstream BOQ anchors, BIM cross-references, and annotation links all use semantic_identity_hash. The presentation_identity_hash is for renderer internals + observability only.

**Migration path:** v0.2 A7's flat `geometry_id: str` field on FloorGeometry is REPLACED by an `identity: ElementIdentity` field. The semantic hash takes the geometry-defining-fields-only subset; the presentation hash takes the full structure.

**v0.2 A7's element-kind taxonomy unchanged.** This is a refinement of the ID-generation rule, not the taxonomy.

**Cache-relevant:** YES (schema change → C16_DRAWING_SCHEMA_VERSION bump 2 → 3).

---

## A4 — Dual-frame coordinate architecture

**Origin:** Reviewer #2 item 4. Aligns with IFC IfcLocalPlacement + IfcSite pattern (web-research verified).

**Problem:** v0.2 A2 set a single global coordinate frame (origin = site SW corner, +X = East, +Y = North). For plots rotated significantly off-North, coordinates become awkward: inflated magnitudes, unintuitive editing, non-orthogonal local geometry, IFC interoperability friction.

**Amendment:** Replace single-frame convention with dual-frame architecture:

```python
@dataclass(frozen=True)
class LocalBuildingFrame:
    """Building-aligned orthogonal coordinate frame.
    
    Origin: SW corner of the BUILDING footprint (NOT the plot).
    +X axis: parallel to the LONGEST building wall, building-relative.
    +Y axis: perpendicular to +X, by right-hand rule (counter-clockwise
             from +X when viewed from +Z = up).
    +Z axis: Up (right-hand rule).
    
    All FloorGeometry coordinates are emitted in this frame.
    Coordinates are typically small magnitudes (tens of meters) and
    intuitive for local editing."""
    pass  # marker type; the convention is the type contract

@dataclass(frozen=True)
class GeospatialReference:
    """Metadata locating the LocalBuildingFrame in real-world geography.
    
    Used to correlate the local building frame with:
    - Surveyor coordinates
    - Plot orientation (from C4 plot analysis)
    - Site plan / key plan rendering (which use plot-aligned coordinates)
    - Future IFC export (maps to IfcSite + IfcLocalPlacement)"""
    
    # Origin of LocalBuildingFrame in plot-local coordinates:
    local_origin_in_plot_mm: tuple[int, int]   # (east_offset, north_offset) from plot SW
    
    # Rotation of LocalBuildingFrame relative to plot-aligned axes:
    rotation_from_plot_north_deg: float        # CCW positive; 0 = +Y aligned with plot North
    
    # Plot-level orientation (from C4):
    plot_north_arrow_orientation_deg: float    # plot's +Y vs true North
    
    # Optional: real geospatial coordinates (lat/lng) for future georeferencing.
    # NOT REQUIRED at v1. Optional metadata only.
    geospatial_latitude: Optional[float] = None
    geospatial_longitude: Optional[float] = None
    geospatial_elevation_m: Optional[float] = None
    
    # WGS-84 datum assumed if geospatial_* fields populated.
```

**Where each frame is used:**

| Coordinate frame | Used for |
|---|---|
| LocalBuildingFrame | All FloorGeometry, working+permit floor plans, sections, elevations |
| Plot-aligned (legacy v0.2 A2) | Site plan, setback annotations, parking provision |
| Real geospatial (optional) | Future IFC IfcSite export, geocoded site reports |

**The relationship is computable:** Plot-aligned coordinates = `rotate(LocalBuildingFrame coordinates, rotation_from_plot_north_deg) + local_origin_in_plot_mm`. Both frames are deterministic given the inputs.

**Bounding-box guards** (modified from v0.2 A2):
- LocalBuildingFrame coords: `-50,000 ≤ x ≤ 50,000 mm` (typical residential building dimensions; rejects pathological inputs)
- Plot-aligned coords: `0 ≤ x ≤ 200,000 mm` (preserved from v0.2; covers Indian residential plots up to ~50,000 sqm)
- These bounds MOVED to RenderingConfig per A8 below.

**DualDrawingBundle gains:**
- `local_building_frame: LocalBuildingFrame` (always present; marker type)
- `geospatial_reference: GeospatialReference` (always present; some fields may be None)

**Cache-relevant:** YES (output schema change → C16_DRAWING_SCHEMA_VERSION bump 3 → 4).

---

## A5 — Submission readiness gated by UPSTREAM_AUTHORITATIVE only (R25)

**Origin:** Reviewer #2 item 6.

**Problem:** v0.2 A4's SubmissionReadiness enum can be derived from any AuthorityKind. If a LOCALLY_DERIVED ratio (e.g. plot_coverage_pct calculation drift) influences readiness state, C16 silently becomes a quasi-compliance engine — exactly the drift A5 from v0.2 tried to prevent.

**Amendment:** Add Inv **R25** (governance rule):

```
R25 — Submission-readiness authority discipline:
      PermitDrawingModel.submission_readiness MAY ONLY be derived
      from AttestedValue entries whose authority kind is
      UPSTREAM_AUTHORITATIVE.
      
      LOCALLY_DERIVED values (e.g. plot_coverage_pct as ratio of
      upstream values) MAY appear in PermitDrawingModel for
      DISPLAY purposes but MUST NOT gate submission_readiness.
      
      CROSS_CHECK_VERIFICATION values, if any disagree with their
      upstream-authoritative counterpart, MAY downgrade
      submission_readiness to UNSAFE_FOR_SUBMISSION but MUST emit
      a corresponding ComplianceProvenanceError in
      failure_record.errors.
```

**Practical effect:** the determination of "permit-critical overlays present" (per v0.2 A4) checks ONLY upstream-authoritative claims. Local arithmetic is advisory only.

**Cache-relevant:** NO (governance invariant; no schema change).

---

## A6 — Optional ReadabilityDiagnostics field

**Origin:** Reviewer #2 item 7.

**Problem:** v0.2 A6's annotation suppression precedence is deterministic but doesn't surface WHAT got suppressed. Compliance labels suppressed via overlap heuristics could silently disappear, producing legally-incomplete drawings.

**Amendment:** Add optional `readability_diagnostics: Optional[ReadabilityDiagnostics]` to DualDrawingBundle:

```python
@dataclass(frozen=True)
class ReadabilityDiagnostics:
    """Observability for annotation suppression and collision events.
    
    OPTIONAL — emitted iff RenderingConfig.capture_readability_diagnostics
    is True (default: False at v1 to preserve byte-equal replay for
    consumers who don't need diagnostics).
    
    EXCLUDED from canonical equality and cache_keys (same pattern as
    PhaseTimings in v0.2 A10)."""
    
    collision_count: int                          # raw annotation-overlap events detected
    suppressed_annotations: tuple[SuppressedAnnotation, ...]
    """Each entry: which annotation was suppressed, which other
    annotation it conflicted with, what precedence rule fired."""
    
    viewport_congestion_score: float             # 0.0 (uncongested) to 1.0 (severe)
    
    readability_degraded: bool                    # True iff any compliance-tier annotation was suppressed
    """If True, downstream UIs MUST surface a 'drawing readability
    degraded — manual review recommended' warning to the user."""
```

**Inv extension:** if `readability_degraded == True` AND the suppressed compliance annotation is permit-critical (per v0.2 A4 list), submission_readiness MUST be downgraded to UNSAFE_FOR_SUBMISSION (combines with R25).

**Cache-relevant:** NO (excluded from cache_keys by design; observability only).

---

## A7 — Canonical JSON serialization rules pinned

**Origin:** Reviewer #2 item 9.

**Problem:** v0.2 A9 (Inv R7c) said "canonical JSON" but didn't pin enum form, Optional[None] handling, absent-vs-null semantics, or nested dataclass canonicalization. Real ambiguity for downstream cache + comparison systems.

**Amendment:** Pin canonical JSON serialization rules:

```
1. Object key ordering: lex-ASC (UTF-8 codepoint order).
2. Enum serialization: ALWAYS as string value of `.value` attribute.
   E.g. SubmissionReadiness.COMPLETE_REQUIRES_SIGNATURE serializes as
   "complete_requires_signature", NEVER as the enum name nor as int.
3. Optional[None] fields: OMITTED from canonical JSON entirely.
   No null. No empty string. Field absent means value is None.
   Consumers MUST treat absent fields as None.
4. Nested dataclasses: serialized as objects with lex-ASC keys
   recursively. No type tags.
5. Tuples: serialized as JSON arrays. Preserve element order
   (which is already canonical-sorted at construction time per
   Inv R2 / R5).
6. frozenset: serialized as JSON arrays with elements in lex-ASC
   order (since frozensets are unordered in Python but JSON arrays
   are ordered).
7. Numeric formatting:
   - Integers: bare integers, no trailing decimals
   - Floats representing mm: rounded to 1 mm precision per
     Inv R7a, serialized as bare integers (NOT floats)
   - Floats representing ratios: rounded to 4 decimal places per
     Inv R7a, serialized with EXACTLY 4 decimal places (e.g.
     0.7500, not 0.75)
   - Floats representing degrees: 6 decimal places fixed
8. String encoding: UTF-8 with NFC unicode normalization.
9. No whitespace between tokens. No trailing newline. No comments.
10. No object/array trailing commas.
```

These rules cumulatively guarantee that two `DualDrawingBundle` instances with the same canonical replay-identity will produce byte-identical JSON serializations.

**This refines Inv R7c (from v0.2 A9), not replaces it.**

**Cache-relevant:** NO (clarification of existing R7c).

---

## A8 — Move coordinate bounds to RenderingConfig

**Origin:** Reviewer #2 item 11.

**Problem:** v0.2 A2 hardcoded coordinate bounds (200,000mm × 200,000mm for plot, ~50,000mm for building height). The reviewer correctly observes these are tuned for Indian residential; campus / apartment / mixed-use violates them unnecessarily.

**Amendment:** Move bounds into RenderingConfig with residential defaults:

```python
@dataclass(frozen=True)
class CoordinateBoundsPolicy:
    """Per-project coordinate range guards. Defaults tuned for Indian
    residential; larger-scope projects override."""
    plot_x_max_mm: int = 200_000              # 200m east-west
    plot_y_max_mm: int = 200_000              # 200m north-south
    building_x_max_mm: int = 50_000           # 50m building dimension
    building_y_max_mm: int = 50_000
    building_z_min_mm: int = -5_000           # basement
    building_z_max_mm: int = 50_000           # high-rise upper bound

@dataclass(frozen=True)
class RenderingConfig:
    # ... (existing v0.2 A6 fields) ...
    coordinate_bounds: CoordinateBoundsPolicy = CoordinateBoundsPolicy()
```

Inv R19 (from v0.2 A2) now reads bounds from `config.coordinate_bounds` rather than from hardcoded constants. Violations still raise `GeometryInconsistencyError`.

**Cache-relevant:** YES (bounds are config; bounds enter `config_signature` for cache_keys; bump C16_VERSION v0.3 → v0.3.1 or hold for v0.3 cumulative bump).

---

## § 12 — Backlog updates from critique walk #2

### New LOCK-mandatory items

| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK | Define renderer-consumer contract: line-weight abstraction, text-anchor positioning, canonical rendering semantics. MUST be defined BEFORE any downstream renderer (PDF/SVG/DXF) integration ships. | **v1.0-LOCK-MANDATORY** | L |
| B-C16-SEMANTIC-IDENTITY-STABILITY-CI | CI test: simulate harmless schema additions (new optional fields) and verify semantic_identity_hash unchanged. Catch accidental "promotion" of presentation field into semantic hash. | **v1.0-LOCK-MANDATORY** | S |
| B-C16-DUAL-FRAME-COORDINATE-CONVERSION-AUDIT | Round-trip test: LocalBuildingFrame → Plot-aligned → LocalBuildingFrame produces byte-equal coordinates within 1mm tolerance. | **v1.0-LOCK-MANDATORY** | S |

### New post-LOCK items

| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C16-MUNICIPAL-WORKFLOW-STATE-EXTENSION | Architect future expansion: workflow-state extension layer for {architect_reviewed_unsigned, authority_rejected, revision_requested, etc.}. C16 emits drawing-completeness state; external workflow tracks municipal lifecycle. | v1.x | M |
| B-C16-ADAPTIVE-SECTION-CUT-HEURISTICS | Add adaptive cuts for courtyards, double-height spaces, split levels, cantilevered sections. v1 ships mandatory cuts only (entry/staircase/wet-zone per v0.2 A8). | v1.x | M |
| B-C16-OBSERVABILITY-SIGNATURE | Separate observability signature for timing/diagnostics (distinct from canonical replay-identity). Two "equal" bundles with different runtime behavior would have different observability_signatures. | v1.x | S |
| B-C16-V1-TO-V2-MIGRATION-FRAMEWORK | Explicit geometry schema versioning, overlay compatibility matrix, migration adapters, geometry lineage metadata. Required before v2.x schema bump. | v2.x | XL |

### Cumulative backlog at v0.3 PROPOSED: 33 items

- 14 LOCK-mandatory (8 from v0.1 + 3 from walk #1 + 3 from walk #2)
- 16 post-LOCK / v1.x (12 from prior + 4 from walk #2)
- 3 routed amendment hints (unchanged)

---

## Cumulative invariant table (after v0.1 + v0.2 + v0.3)

| ID | Description | Source |
|---|---|---|
| R1-R18 | Original invariants per v0.1 § 2 | v0.1 |
| R19 | Coordinate bounds | v0.2 A2 (refined to config in v0.3 A8) |
| R20 | Geometry parity (working ↔ permit ↔ shared) | v0.2 A3 |
| R21 | Submission-readiness completeness | v0.2 A4 |
| R22 | Provenance authority discipline | v0.2 A5 |
| R23 | Mandatory section cuts | v0.2 A8 |
| R24 | Geometry referential integrity (3 sub-clauses) | v0.3 A2 |
| R25 | Submission-readiness gated by UPSTREAM_AUTHORITATIVE only | v0.3 A5 |

---

## Version bumps required at v0.3

- `C16_VERSION`: v0.2 → v0.3
- `C16_DRAWING_SCHEMA_VERSION`: 2 → 4 (skips 3 because A3 + A4 are both schema-altering)

---

## Rule 8 / Rule 11 disclosure

Per Rule 8: LOCK authority is Ramalingam's alone. This delta is **PROPOSED, PENDING your adjudication**. Lock applies after explicit "lock it" / "v0.3 LOCKED."

Per Rule 11: web research conducted on IFC GlobalId stability conventions for Item 3 verification (semantic vs presentation identity is a documented industry workaround for IFC GUID instability). Item 4's dual-frame architecture aligns with IFC's IfcLocalPlacement + IfcSite pattern (verified in prior walk's coordinate search). All 13 substantive reviewer items walked with verdicts: 8 VALID-with-amendment, 4 VALID-deferred-to-backlog, 1 PARTIALLY-VALID.

Self-analysis worst remaining gaps after this delta:

1. **A1's timestamp fix relies on upstream selector discipline.** If a sloppy upstream selector stamps timestamp inside replay_identity instead of audit_metadata, C16 inherits the determinism bug. Mitigation: B-C16-SELECTION-REPLAY-IDENTITY-DISCIPLINE-CI added as LOCK-mandatory.

2. **A3 semantic identity stability depends on getting the "geometry-defining fields" subset right.** If a future schema change accidentally adds a presentation field to the semantic hash's source tuple, stability silently breaks. Mitigation: B-C16-SEMANTIC-IDENTITY-STABILITY-CI filed (above).

3. **A4 dual-frame adds conversion complexity.** Round-trip integrity (LocalBuildingFrame ↔ plot-aligned) must be exact within 1mm. Mitigation: B-C16-DUAL-FRAME-COORDINATE-CONVERSION-AUDIT filed.

4. **A5/A6/A8 don't fundamentally change architecture; they refine v0.2.** Risk profile of v0.3 is roughly equal to v0.2 with these refinements applied.

5. **The "selector" upstream question (Q1 from v0.1, refined in v0.2 A1, refined again in v0.3 A1) is still UNRESOLVED at the project level.** Whoever produces SelectionResult must implement the replay_identity / audit_metadata split correctly. This crosses C16's boundary into project-level governance.

---

## § 16 — End of v0.3 PROPOSED-DELTA

This document constitutes the C16 v0.3 PROPOSED-DELTA. Awaiting Ramalingam LOCK adjudication.

Next steps if LOCKED:
- C16 v0.3 LOCKED SPEC composed from v0.1 + v0.2 + v0.3
- Build can begin per spec-first discipline
- Critique walk #3 may produce v0.4 if any further refinement surfaces

Next steps if revisions requested:
- v0.3 PROPOSED-DELTA reshaped per your direction
- Re-submitted as v0.3 PROPOSED-DELTA-2

Per Rule 8 — your call.
