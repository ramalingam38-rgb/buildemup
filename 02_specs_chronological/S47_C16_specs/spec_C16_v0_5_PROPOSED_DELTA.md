# Component 16 — Dual-Drawing Renderer — v0.5 PROPOSED-DELTA

**Spec version:** v0.5 PROPOSED-DELTA over v0.4 (over v0.3, v0.2, v0.1)
**Status:** PROPOSED. PENDING Ramalingam LOCK adjudication.
**Authored:** S47 (this session, post-critique-walk #4)
**Critique source:** External review document #4 on v0.4 PROPOSED-DELTA, 13 substantive items
**Reading order:** v0.1 → v0.2 → v0.3 → v0.4 → v0.5. Latest wins.

---

## Authoring note — why v0.5 is CONSTRAINED

This delta is deliberately small (6 amendments vs walk #4's 13 items). Reasons:

1. Reviewer Item 13 explicitly identifies spec breadth as the dominant remaining risk: "C16 is now approaching platform-layer complexity."
2. Reviewer Item 14 affirms architecture trajectory is strong and the next gate is decomposition decision, not more amendments.
3. Pattern E avoidance: mechanically producing a fat v0.5 worsens the spec-breadth concern the reviewer just elevated.

Six items get concrete amendments (tightenings only — no new field families). Six items route to backlog (operational/governance concerns, appropriate for v1.x). One item (Renderer conformance) elevates from § 17 SKETCH to LOCK-mandatory binding-contract. One item (Decomposition) elevates urgency for v1.0 LOCK adjudication.

---

## A1 (v0.5) — Explicit 64-bit signed integer requirement for CanonicalTransform2D

**Origin:** Reviewer #4 item 3.

**Problem:** v0.4 A3 used integer fixed-point representation but didn't specify storage width. At township scale (1km coordinates × 1e6 rotation multiplier = ~1e9), 32-bit signed (~2.1e9 limit) cuts close. Long transform chains could overflow silently.

**Amendment:** Pin storage requirement:

```python
@dataclass(frozen=True)
class CanonicalTransform2D:
    """All 6 stored elements MUST be 64-bit signed integers.
    
    Python int has arbitrary precision so this is automatic;
    however, downstream C16-conformant renderers MUST use int64
    (NOT int32) when porting to typed languages.
    
    Rationale: at township scale (1km plot, 1e6 rotation multiplier),
    composed transform elements reach 1e9-1e12 range. int32 max is
    ~2.1e9. int64 max is ~9.2e18 — safe margin of ~6 orders of magnitude."""
    
    a00_micro: int  # 64-bit signed
    a01_micro: int
    a02_mm: int
    a10_micro: int
    a11_micro: int
    a12_mm: int
```

**Inv R28 strengthened (NEW R28d):**
```
R28d — Overflow detection: every transform composition MUST check
       that no intermediate element exceeds 64-bit signed range
       (±9,223,372,036,854,775,807). On overflow, raise
       TransformOverflowError (LocalDrawingError subclass — always
       halts). NEVER silently truncate.
```

**Saturation policy:** none. Overflow is a hard error, not a clamp. Reason: silent clamp would corrupt geometry.

**Cache-relevant:** NO (constraint tightening; same values in valid range produce same outputs).

---

## A2 (v0.5) — schema_descriptor_digest embedded in DualDrawingBundle

**Origin:** Reviewer #4 item 6.

**Problem:** v0.4 A6 emitted SchemaDescriptor as a sibling artifact. Risk: bundle/descriptor desynchronization, detached metadata, archive corruption.

**Amendment:** Embed an integrity digest inside the bundle while keeping the descriptor itself as a sibling:

```python
@dataclass(frozen=True)
class DualDrawingBundle:
    # ... existing fields ...
    schema_descriptor_digest: str
    """SHA-256 hex digest of the companion SchemaDescriptor's
    canonical JSON serialization. Allows consumers to verify
    bundle↔descriptor pairing without trusting filesystem layout
    or transmission integrity.
    
    On deserialization, consumer MUST recompute descriptor digest
    and verify match. Mismatch raises SchemaDescriptorMismatchError
    (LocalDrawingError — always halts)."""
```

**Inv R26b NEW (extends R26):**
```
R26b — Every DualDrawingBundle.schema_descriptor_digest MUST equal
       SHA-256 of the canonical-serialized SchemaDescriptor that
       accompanies it. Validated at deserialization time.
```

The digest is INCLUDED in `canonical_replay_signature` (per v0.4 A9 R32) so descriptor changes invalidate bundle caches correctly.

**Cache-relevant:** YES (new field → C16_DRAWING_SCHEMA_VERSION bump 9 → 10).

---

## A3 (v0.5) — Epsilon inclusive/exclusive boundary semantics

**Origin:** Reviewer #4 item 11.

**Problem:** v0.4 A11 defined epsilon constants but didn't specify boundary semantics. "Difference ≤ EPSILON" vs "< EPSILON"; behavior at exactly EPSILON drift; rounding order post-transform.

**Amendment:** Pin boundary semantics:

```
Epsilon comparison semantics — definitive:

EQUALITY:  |a - b| ≤ EPSILON                  (inclusive)
LESS:      a < b - EPSILON                    (exclusive of band)
GREATER:   a > b + EPSILON                    (exclusive of band)

At EXACTLY EPSILON drift (|a - b| == EPSILON), values compare EQUAL.
This is deliberately inclusive — it favors stability over discrimination.

Post-transform normalization order:
1. Apply transform (raw float arithmetic, no rounding)
2. Round result to mm grid (banker's rounding per R7a)
3. Apply Inv R19 bounds check
4. THEN compare via epsilon for equality decisions

NEVER round before transform; NEVER compare before rounding.
Order is fixed. Different orders produce different boundary behavior.
```

**Inv R34e NEW:**
```
R34e — Boundary tie-resolution at exactly EPSILON: comparison
       returns EQUAL. Implementations that round at the boundary
       MUST follow the normalization order above. Tested in CI per
       B-C16-EPSILON-BOUNDARY-CASES-CORPUS.
```

**Cache-relevant:** NO (clarification of existing R34).

---

## A4 (v0.5) — Hard ceiling domain scope annotation

**Origin:** Reviewer #4 item 7.

**Problem:** v0.4 A7's hard ceilings (1km plot, 500m building) are residential/commercial assumptions. Future infrastructure corridors, industrial campuses, GIS-linked megaprojects could legitimately exceed.

**Amendment:** Annotate scope explicitly + add escape hatch:

```python
# Module-level constants (cannot be overridden via RenderingConfig):
#
# SCOPE: BuildemUp residential and small-commercial v1.
# Plot ≤ 1km × 1km; building ≤ 500m × 500m × 500m height.
# 
# For larger domains (township, campus, infrastructure corridor):
# (a) Use a DIFFERENT jurisdiction profile that declares its scope,
# (b) Bump C16_VERSION to a domain-specific variant (e.g. C16-CAMPUS),
# (c) DO NOT override these ceilings within current jurisdiction.
HARD_CEILING_PLOT_X_MM: Final[int] = 1_000_000
HARD_CEILING_PLOT_Y_MM: Final[int] = 1_000_000
HARD_CEILING_BUILDING_X_MM: Final[int] = 500_000
HARD_CEILING_BUILDING_Y_MM: Final[int] = 500_000
HARD_CEILING_BUILDING_Z_MAX_MM: Final[int] = 500_000
HARD_CEILING_BUILDING_Z_MIN_MM: Final[int] = -50_000

# JurisdictionProfile NEW field:
@dataclass(frozen=True)
class JurisdictionProfile:
    # ... existing fields ...
    declared_domain_scope: Literal[
        "residential_v1",
        "small_commercial_v1",
        "mixed_use_v1",
    ] = "residential_v1"
```

**Inv R31 refined:**
```
R31a — Effective ceiling = HARD_CEILING_* constants (no longer
       subject to RenderingConfig override).
R31b — JurisdictionProfile.declared_domain_scope MUST be one of
       the supported v1 values. Larger-scope domains require a
       different C16 variant; v1 rejects them at JurisdictionProfile
       construction.
```

This is **annotation + ENUM enforcement** — no functional change in residential/commercial, but explicit boundary makes future extension paths clear.

**Cache-relevant:** YES (new field on JurisdictionProfile → cache_keys include declared_domain_scope; C16_DRAWING_SCHEMA_VERSION bump 10 → 11).

---

## A5 (v0.5) — Optional orientation_lock metadata

**Origin:** Reviewer #4 item 4.

**Problem:** v0.4 A4's orientation hierarchy is deterministic for a given FloorGeometry, but small architectural revisions (moving main door, adding ceremonial entrance) can rotate the LocalBuildingFrame by 90°. Stable semantic IDs across the project lifecycle then break.

**Amendment:** Add OPTIONAL `orientation_lock` metadata that, when present, freezes orientation across revisions:

```python
@dataclass(frozen=True)
class OrientationLock:
    """Optional persistence record for LocalBuildingFrame orientation.
    
    When present in upstream JurisdictionProfile or SelectionResult:
    C16 uses this orientation regardless of what A4 hierarchy would
    otherwise compute. Hierarchy still validates the lock is plausible
    (within EPSILON_ANGLE_DEG of one of the 4 hierarchy candidates)
    but otherwise honors it."""
    
    locked_at_first_publish: bool
    """If True: orientation was frozen at first published bundle for
    this project. Subsequent renders preserve it even if architectural
    revisions would otherwise re-derive."""
    
    locked_x_axis_orientation_deg: float
    """The frozen +X axis orientation. Compared against A4's hierarchy
    candidates with EPSILON_ANGLE_DEG tolerance."""
    
    locked_origin_basis: Literal[
        "explicit_hint", "primary_entrance", 
        "longest_wall", "lex_fallback"
    ]
    """Which A4 hierarchy step the lock corresponds to. Useful for
    auditing why this orientation was originally chosen."""
    
    lock_provenance: str
    """Free-text reason, e.g. 'first_published_2026_03_15'."""
```

**Inv R29 strengthened (NEW R29d):**
```
R29d — When OrientationLock is present, C16 honors it after a
       PLAUSIBILITY CHECK: locked_x_axis_orientation_deg MUST be
       within EPSILON_ANGLE_DEG of one of the 4 hierarchy
       candidates from R29 (explicit_hint / primary_entrance /
       longest_wall / lex_fallback) computed from CURRENT geometry.
       
       Implausible lock raises OrientationLockMismatchError
       (LocalDrawingError — always halts). A mismatch means the
       building geometry has changed so radically that the lock
       no longer makes sense; manual review required.
```

**When to lock:** at first published bundle for a project. Mechanism for setting the lock is OUT OF SCOPE for C16 — that's an upstream project-management decision (file as B-C16-ORIENTATION-LOCK-SETTER-CONTRACT).

**Cache-relevant:** YES (new optional field → C16_DRAWING_SCHEMA_VERSION bump 11 → 12).

---

## A6 (v0.5) — Overlay completeness validation contract

**Origin:** Reviewer #4 item 5.

**Problem:** v0.4 A5's LegalCompleteness depends on "permit-critical overlay present" but doesn't define "present" — partially clipped overlay? truncated annotation? zero-area parking bay? Different developers would judge differently.

**Amendment:** Define `OverlayValidationContract` — separate validation surface from rendering visibility:

```python
@dataclass(frozen=True)
class OverlayValidationContract:
    """Per-overlay-kind validation rules. SKETCH at v0.5.
    Each overlay declares its own validation function via this contract."""
    
    overlay_kind: Literal[
        "rwh_overlay", "sewage_layout", "setback_dimensions",
        "compliance_attestation", "parking_provision"
    ]
    
    semantic_completeness_check: str
    """Reference to a named validation rule. Examples:
    - 'rwh_has_nonzero_capacity_and_drainage_path'
    - 'sewage_has_treatment_node_and_outlet_path'
    - 'setback_has_4_sides_with_dimensions_above_zero'
    - 'parking_provision_has_required_count_and_nonzero_bay_area'
    - 'compliance_attestation_has_all_5_authoritative_values'
    
    LOCK-mandatory: B-C16-OVERLAY-VALIDATION-RULES-LOCK pins the
    exact rule definitions at v1.0."""
    
    visual_visibility_required: bool
    """Separate concern from semantic completeness. An overlay can
    be semantically complete (all data present) but visually
    suppressed by RenderingConfig — that's REVIEW_RECOMMENDED
    territory (per A5 R30), NOT LEGALLY_INCOMPLETE."""
```

**Inv R30d NEW (extends R30):**
```
R30d — LegalCompleteness determination uses ONLY
       semantic_completeness_check results. Visual visibility,
       annotation overlap, viewport congestion are READABILITY
       concerns and feed ReadabilityStatus, never LegalCompleteness.
       
       Concrete: a parking bay with valid dimensional area >0 and
       valid bay_count >0 is LEGALLY_COMPLETE even if its annotation
       label was suppressed for overlap. The label suppression
       feeds READABILITY_DEGRADED.
```

The exact rule semantics (e.g. what "nonzero capacity" means for RWH) is pinned by `B-C16-OVERLAY-VALIDATION-RULES-LOCK` (LOCK-mandatory; added to backlog below).

**Cache-relevant:** NO (validation contract; outputs unchanged).

---

## § 17 — Renderer Conformance Contract elevation

**Origin:** Reviewer #4 item 12 (ELEVATED, not amendment).

**Change at v0.5:** v0.4's § 17 appendix WAS SKETCH-level "heavy/medium/light" abstraction. Walk #4 correctly notes this is too abstract for legal workflows. Indian municipal submissions reference IS 962:1967.

**Action:** § 17 is **ELEVATED from SKETCH-level appendix to v1.0-LOCK-MANDATORY architectural sub-specification**. v0.5 doesn't expand the appendix content (Pattern E avoidance), but the backlog item is upgraded:

```
B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK refined to require, at
v1.0 LOCK, binding specifications referencing IS 962:1967:

  - Minimum plotted text height: 2.5mm (per industry CAD standard)
  - Title block: 150mm × 100mm for A1 sheets (per IS 962)
  - Text size hierarchy:
    * Title block headings: 5-7mm
    * Drawing labels: 3.5-5mm  
    * General notes/dimensions: 2.5-3.5mm
  - Sheet sizes supported (per ISO 216): A0, A1, A2, A3
  - Pen weight ranges: heavy 0.5-0.7mm, medium 0.25-0.35mm, 
    light 0.13-0.18mm (per IS 962 + standard CAD practice)
  - Monochrome compatibility required (municipal printers often
    monochrome)
  - Graphic scale bar mandatory on every sheet (paper expansion
    safety per industry standard)
  - Margins per ISO 5457 (drawing border margins)
```

The actual binding values for v1.0 LOCK will be pinned at that time. v0.5 establishes the requirement that they MUST be pinned.

---

## § 12 — Backlog updates from walk #4

### Items ROUTED to backlog (no v0.5 amendment)

| ID | Origin (walk #4 item) | Trigger | Effort |
|---|---|---|---|
| B-C16-LEGACY-SELECTOR-COMPATIBILITY-MIGRATION | Item 1 — version negotiation, compat adapters, legacy import mode | v1.x | L |
| B-C16-RECURSIVE-HASH-DEPENDENCY-DOCS | Item 2 — dependency-scope documentation, graph-diff tooling | v1.x | M |
| B-C16-INTEGRITY-HASH-COLLISION-INSTRUMENTATION | Item 8 — collision telemetry, distribution analysis, benchmark corpus | v1.x | M |
| B-C16-CACHE-LINEAGE-METADATA | Item 9 — signature ancestry graph, replay↔presentation reconciliation tooling | v1.x | M |
| B-C16-IDENTITY-GENERATION-GOVERNANCE-RFC | Item 10 — formal RFC process, migration review checklist, compatibility report | v1.x process | M |
| B-C16-ORIENTATION-LOCK-SETTER-CONTRACT | A5 routed — define WHO/WHERE sets OrientationLock (project-management upstream concern) | v1.0 | S |

### Items ELEVATED in priority

| ID | Change | Why |
|---|---|---|
| **B-C16-DECOMPOSITION-DECISION-LOCK** | ELEVATED to **v1.0-LOCK-BLOCKING**: must adjudicate BEFORE v1.0 LOCK (not just "before v1.0 LOCK as background"). | Reviewer #4 item 13/14 explicitly: "decomposition decision before v1.0 LOCK is now genuinely important." |
| **B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK** | ELEVATED to v1.0-LOCK-BLOCKING with binding IS 962:1967 references. | Reviewer #4 item 12 — abstract semantics insufficient for legal workflows. |

### Items NEW from v0.5 amendments

| ID | Description | Trigger | Effort |
|---|---|---|---|
| B-C16-EPSILON-BOUNDARY-CASES-CORPUS | Adversarial corpus for boundary cases at exactly EPSILON drift, multi-step normalization. | v1.0 | S |
| B-C16-OVERLAY-VALIDATION-RULES-LOCK | Pin exact `semantic_completeness_check` rules per overlay_kind. | **v1.0-LOCK-MANDATORY** | M |
| B-C16-TRANSFORM-OVERFLOW-CORPUS | CI test for 64-bit overflow detection in 5-step transform chains at township scale. | v1.0 | S |

### Cumulative backlog at v0.5 PROPOSED: 49 items

- 19 LOCK-mandatory (was 17 at v0.4 + 3 new from walk #4 - 1 absorbed into existing item)
- 27 post-LOCK / v1.x (was 20 at v0.4 + 7 routed/new)
- 3 routed amendment hints

**Of the 19 LOCK-mandatory, 2 are now v1.0-LOCK-BLOCKING** (decomposition decision + renderer conformance binding). The remaining 17 are LOCK-required but can be closed in parallel during implementation.

---

## Cumulative invariant table at v0.5

| ID | Description | Source |
|---|---|---|
| R1-R23 | Original v0.1 invariants + v0.2/v0.3 additions | prior |
| R24 | Geometry referential integrity (O(n) per v0.4 A8) | v0.3 A2 |
| R25 | Submission-readiness gated by UPSTREAM_AUTHORITATIVE only | v0.3 A5 |
| R26 (+R26b) | Canonical replay-identity validation + descriptor digest | v0.4 A1 + v0.5 A2 |
| R27 | Per-ElementKind semantic field inclusion matrix | v0.4 A2 |
| R28 (+R28d) | Transform composition precision + 64-bit overflow detection | v0.4 A3 + v0.5 A1 |
| R29 (+R29d) | LocalBuildingFrame orientation + optional lock plausibility | v0.4 A4 + v0.5 A5 |
| R30 (+R30d) | Legal completeness ⊥ readability + overlay validation surface | v0.4 A5 + v0.5 A6 |
| R31 (refined) | Hard safety cap + domain scope enforcement | v0.4 A7 + v0.5 A4 |
| R32 | Replay vs presentation signature relationship | v0.4 A9 |
| R33 | Identity generation discipline | v0.4 A10 |
| R34 (+R34e) | Canonical epsilon policy + boundary inclusion semantics | v0.4 A11 + v0.5 A3 |

Total invariants: 34 main + 6 sub-clauses added at v0.5.

---

## Version bumps required at v0.5

- `C16_VERSION`: v0.4 → v0.5
- `C16_DRAWING_SCHEMA_VERSION`: 9 → 12 (A2, A4, A5 are schema-altering)
- `C16_IDENTITY_GENERATION`: unchanged at 1

---

## Rule 8 / Rule 11 disclosure

Per Rule 8: LOCK authority is Ramalingam's alone. This delta is **PROPOSED, PENDING your adjudication.**

Per Rule 11: web research conducted for Item 12 verification. Findings: India's canonical drawing standard is IS 962:1967 (Indian Standard Code of Practice for Architectural and Building Drawings). Industry-standard minimum plotted text height: 2.5mm. Title block 150×100mm for A1 sheets. These concrete values are now referenced in `B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK` (elevated to v1.0-LOCK-BLOCKING).

Self-analysis worst remaining concerns after this delta:

1. **The decomposition decision (Item 13) is now the dominant unresolved question.** v0.5 explicitly does NOT add new scope to C16. But locking C16 at v1.0 without first adjudicating decomposition risks committing to a unified C16 that mature CAD/BIM systems would split. Recommend: adjudicate decomposition BEFORE v0.6 (if there is one) or before v0.5 LOCK.

2. **Walk #4 is the first walk where deferred-to-backlog items outnumbered VALID-with-amendment items** (6 vs 6 vs. walk #3's 12 vs 0). This is the diminishing-returns trajectory becoming visible in numbers.

3. **§ 17 renderer conformance is now BLOCKING but still SKETCH.** Closing it requires real specification work (IS 962 references, sheet sizes, pen weights). That's a meaningful chunk of LOCK-blocking work.

4. **Two bugs I introduced across four walks** (v0.2 A1 timestamp determinism, v0.3 A4 orientation-via-longest-wall). Both caught by reviewers, both fixed in successive deltas. The pattern is: I introduce subtle determinism bugs in field additions. **I should add a self-discipline checkpoint: before submitting any delta that adds a field, manually trace whether the field can cross into replay_identity inappropriately, and whether its value source has deterministic resolution under small input perturbations.** Filed as personal-discipline B-CLAUDE-PRE-DELTA-DETERMINISM-AUDIT (project-meta).

---

## § 16 — End of v0.5 PROPOSED-DELTA

Three forward paths:

1. **`lock v0.5`** → composed v0.5 LOCKED SPEC across v0.1+v0.2+v0.3+v0.4+v0.5. Two v1.0-LOCK-BLOCKING items remain open (decomposition decision + renderer conformance binding) — those gate v1.0 LOCK, not v0.5 LOCK. Build can begin at v0.5 LOCKED SKETCH per project convention.

2. **Adjudicate decomposition NOW** → answer `B-C16-DECOMPOSITION-DECISION-LOCK` first (keep unified / decompose into C16a-d / defer to v2.x). The answer reshapes everything downstream.

3. **Walk #5** → another critique round. **Honest forecast: walk #5 will find walk #4-style items (operational/governance), not architectural flaws.** v0.5 closed 6 concrete items; v0.6 would close maybe 4-6 more; v0.7 maybe 2-4. Diminishing returns continue. The architecture-meaningful gates are decomposition + renderer conformance, not more deltas.

Per Rule 8 — your call.

Per Rule 1 (honest context budget): producing v0.5 fits comfortably; v0.6 would fit but tighten further; a handoff cut from here closes cleanly. **My recommendation: path 1 OR path 2 over path 3.**
