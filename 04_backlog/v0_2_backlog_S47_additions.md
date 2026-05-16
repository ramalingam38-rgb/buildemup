# v0_2_backlog_S47_additions.md

**Session:** S47
**Date:** 2026-05-14
**Authority:** Ramalingam directives at S47 close
**Components affected:** C14 (LOCKED this session), C16 (LOCKED at v0.5 this session)
**Predecessor file:** v0_2_backlog_S46_C14_C15_LOCKS.md

This file consolidates ALL backlog additions from S47. It does not retire prior backlog files — those remain canonical for their respective scopes.

---

## § 1 — Decomposition adjudication (recorded for posterity)

### B-C16-DECOMPOSITION-DECISION-LOCK

**Status at S46 close:** OPEN, LOCK-mandatory
**Status at S47 close:** **ADJUDICATED — DEFERRED to v2.x. Keep C16 unified at v1.0.**

**Adjudication authority:** Ramalingam, S47 directive ("Adjudicate decomposition and proceed with the handoff")

**Reasoning recorded in `02_specs_chronological/S47_C16_specs/spec_C16_v0_5_LOCKED.md` § Decomposition adjudication.**

### B-C16-DECOMPOSITION-DEFERRED-REVISIT-CONDITIONS (NEW at S47)

**Status:** OPEN, v2.x-conditional
**Description:** Triggers that would force re-opening the decomposition decision before v2.x:
- BuildemUp expands beyond residential to campus/infrastructure scale
- Third-party renderers want to consume C16 outputs independently
- C16 implementation reveals concrete seams that benefit from explicit separation
- Multi-jurisdiction expansion forces compliance layer separation
**Trigger:** any of the four conditions above
**Effort:** L (re-opens substantial architectural decision)

---

## § 2 — C14 critique walk additions (S47 build close)

External 11-item analysis on C14 v0.2 BUILD walked at S47 build close. Verdicts: 1 strong VALID, 4 VALID-BUT-BACKLOG, 3 DOCUMENTED, 4 MISFRAMED.

### LOCK-mandatory for C14 v1.0

| ID | Description | Effort |
|---|---|---|
| B-C14-PBT-LAYER-COVERAGE | Spec § 7 mandates ≥15 property-based tests; v0.2 BUILD shipped 0. Add PBT layer covering all invariants before C14 v1.0 LOCK. | M |

### VALID-but-backlog (post-LOCK / v1.x)

| ID | Description | Effort |
|---|---|---|
| B-C14-BATCH-PARALLELIZATION | Batch processing parallelism for multi-candidate analysis | M |
| B-C14-PROVENANCE-FOR-EVERY-FLAG | Add provenance trace to each emitted CirculationFlag | M |
| B-C14-PERFORMANCE-BENCHMARK-CORPUS | Adversarial corpus for performance budget verification | S |
| B-C14-SCHEMA-EVOLUTION-COMPATIBILITY | Forward-compatibility framework for schema migrations | M |

---

## § 3 — C16 critique walks 1-5 additions (S47 spec close)

5 critique walks producing 39 substantive item verdicts. Backlog additions consolidated below.

### v1.0-LOCK-BLOCKING items (2)

| ID | Origin | Effort |
|---|---|---|
| B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK | Walk #4 Item 12 → Walk #5 Item 4. Bind IS 962:1967 references (text heights, sheet sizes, pen weights, title block dims). Includes typography determinism (font metrics normalization, deterministic text layout). | L |
| ~~B-C16-DECOMPOSITION-DECISION-LOCK~~ | **CLOSED — adjudicated at S47, deferred to v2.x. See § 1.** | — |

### LOCK-mandatory non-blocking (17)

| ID | Origin | Description | Effort |
|---|---|---|---|
| B-C16-ENVELOPE-SCHEMA-LOCK | v0.1 | Pin exact field lists for FloorPlanWorking/Permit/SectionView/Elevation | M |
| B-C16-SELECTED-LAYOUT-CONTRACT-LOCK | v0.1 | Define SelectionResult typestate (refined by v0.2 A1 + v0.3 A1) | M |
| B-C16-SECTION-CUT-RULES-LOCK | v0.1 → v0.2 A8 → walk #3 | Formalize mandatory cuts (entry + staircase + wet-zone) with irregular-geometry fallback | S |
| B-C16-RWH-SEWAGE-OVERLAY-DETAIL-LOCK | v0.1 | Pin RWH and sewage overlay shapes per TNCDBR rule 9 | M |
| B-C16-COMPLIANCE-PROVENANCE-FORMAT-LOCK | v0.1 | CheckProvenance shape (refined by v0.2 A5 AuthorityKind) | S |
| B-C16-PARKING-PROVISION-SCHEMA-LOCK | v0.1 | ParkingProvision schema per NBC + TNCDBR matrix | S |
| B-C16-PBT-LAYER-COVERAGE | v0.1 | ≥15 PBTs covering R1-R34 invariants. **Match C14's gap — do not repeat.** | M |
| B-C16-REGRESSION-SNAPSHOT-CORPUS | v0.1 | Pin reference outputs across 5-scenario adversarial corpus | S |
| B-C16-COORDINATE-CONVENTION-IFC-COMPATIBILITY-VERIFICATION | walk #1 | Verify A2 + A4 dual-frame maps cleanly to IFC IfcLocalPlacement | S |
| B-C16-SHARED-GEOMETRY-PARITY-CI-CHECK | walk #1 | CI test for working+permit geometry parity (R20) | S |
| B-C16-SECTION-CUT-FALLBACK-CORPUS | walk #1 | 10 irregular plot geometries stressing A8 fallback hierarchy | M |
| B-C16-SEMANTIC-IDENTITY-STABILITY-CI | walk #2 | CI test: harmless schema additions don't change semantic_identity_hash | S |
| B-C16-DUAL-FRAME-COORDINATE-CONVERSION-AUDIT | walk #2 | Round-trip test LocalBuildingFrame ↔ Plot-aligned within 1mm | S |
| B-PROJECT-SELECTOR-CANONICALIZATION-CONTRACT-LOCK | walk #3 | Shared canonical serializer for SelectionReplayIdentity (imported by C16 + C17) | M |
| B-C16-V0.3-TO-V0.4-MIGRATION-AUDIT | walk #3 | Verify no in-flight builds depend on v0.3 A4 longest-wall rule | S |
| B-C16-EPSILON-POLICY-CI-CHECK | walk #3 | Static analysis: every internal float comparison uses an EPSILON_ constant | S |
| B-C16-OVERLAY-VALIDATION-RULES-LOCK | walk #4 → walk #5 | Pin exact semantic_completeness_check rules per overlay_kind | M |

### Post-LOCK / v1.x (27)

| ID | Origin | Effort |
|---|---|---|
| B-C16-MULTI-JURISDICTION-PROFILES | v0.1 → walk #1 Item 6 | XL |
| B-C16-BATCH-PARALLELIZATION | v0.1 | M |
| B-C16-ELEVATION-VIEW-SOLAR-ANNOTATIONS | v0.1 | M |
| B-C16-3D-MODEL-EXPORT | v0.1 → walk #1 Item 13 | XL |
| B-C16-RENDERER-OUTPUT-FORMAT-INTEGRATIONS | v0.1 | L |
| B-C16-ANNOTATION-DENSITY-AUTO-TUNING | v0.1 | M |
| B-C16-ARCHITECT-SIGNATURE-WORKFLOW-INTEGRATION | v0.1 | L |
| B-C16-JURISDICTION-CAPABILITY-MATRIX | walk #1 | L |
| B-C16-RENDERING-CONFIG-CONFLICT-RESOLUTION-AUDIT | walk #1 | S |
| B-C16-PERFORMANCE-BUDGET-CALIBRATION-FROM-PROD-DATA | walk #1 | S |
| B-C16-BIM-IFC-EXPORT-PILOT | walk #1 | L |
| B-C16-SUBMISSION-READINESS-USER-EDUCATION | walk #1 | M |
| B-C16-MUNICIPAL-WORKFLOW-STATE-EXTENSION | walk #2 | M |
| B-C16-ADAPTIVE-SECTION-CUT-HEURISTICS | walk #2 | M |
| B-C16-OBSERVABILITY-SIGNATURE | walk #2 | S |
| B-C16-V1-TO-V2-MIGRATION-FRAMEWORK | walk #2 | XL |
| B-C16-EPSILON-BOUNDARY-CASES-CORPUS | walk #4 | S |
| B-C16-TRANSFORM-OVERFLOW-CORPUS | walk #4 | S |
| B-C16-LEGACY-SELECTOR-COMPATIBILITY-MIGRATION | walk #5 Item 1 | L |
| B-C16-RECURSIVE-HASH-DEPENDENCY-DOCS | walk #5 Item 2 | M |
| B-C16-INTEGRITY-HASH-COLLISION-INSTRUMENTATION | walk #5 Item 8 | M |
| B-C16-CACHE-LINEAGE-METADATA | walk #5 Item 9 | M |
| B-C16-IDENTITY-GENERATION-GOVERNANCE-RFC | walk #5 Item 10 | M |
| B-C16-ORIENTATION-LOCK-SETTER-CONTRACT | v0.5 A5 | S |
| B-C16-DECOMPOSITION-DEFERRED-REVISIT-CONDITIONS | S47 adjudication | L (if triggered) |
| B-C16-COMPOSED-CANONICAL-DOC | walk #5 Item 12 | M |
| B-CLAUDE-PRE-DELTA-DETERMINISM-AUDIT | self-discipline, walk #5 self-analysis | (project-meta) |

### Routed amendment hints (3)

| ID | Description | Routed to |
|---|---|---|
| B-C17-BOQ-FROM-C16-ANCHORS | C17 consumes C16's BOQ hooks | C17 maintainer |
| B-PROJECT-SELECTOR-COMPONENT-DEFINITION | Define WHO emits SelectionResult | project-level |
| B-C2-PARKING-FEASIBILITY-PROVENANCE-FOR-C16 | C2 expose provenance for C16's compliance_attestation | C2 maintainer |

---

## § 4 — Project-meta backlog item (NEW at S47)

### B-CLAUDE-PRE-DELTA-DETERMINISM-AUDIT

**Status:** OPEN, project-meta discipline
**Description:** Self-discipline checkpoint for future Claudes. Before submitting any spec delta that adds a field to a frozen dataclass that participates in canonical replay-identity, manually trace: (a) does the field's value source have deterministic resolution under small input perturbations? (b) does the field cross into replay_identity inappropriately (e.g. timestamps, env IDs, machine fingerprints)?

**Pattern observed:** S47 introduced 2 determinism bugs across 5 walks:
- Walk #2 caught v0.2 A1 timestamp-in-canonical-signature
- Walk #4 caught v0.3 A4 longest-wall-orientation-flip

**Both bugs were field-additions to types that flow into canonical replay-identity.** Adding this discipline prevents the third occurrence.

**Trigger:** every spec delta that adds a field to a frozen dataclass in C16/C13/C14/C15 lineage
**Effort:** O(minutes per delta) — manual trace, not tooling

---

## § 5 — Summary

**S47 backlog additions:** ~46 items across C14 critique walk + 5 C16 critique walks + decomposition adjudication + project-meta.

**At S47 close, C16 backlog state:**
- 1 ADJUDICATED (decomposition deferred)
- 1 v1.0-LOCK-BLOCKING open (renderer conformance)
- 17 LOCK-mandatory non-blocking
- 27 post-LOCK / v1.x
- 3 routed amendment hints

**C14 backlog state:**
- 1 LOCK-mandatory for C14 v1.0 (PBT layer)
- 4 post-LOCK / v1.x

**Project backlog max approx:** B-C16 series saturates; canonical numeric range B-NNN max needs separate consolidation in next session.

**File status:** This file is the consolidated S47 addition record. It supersedes nothing; prior files remain canonical for their respective scopes.
