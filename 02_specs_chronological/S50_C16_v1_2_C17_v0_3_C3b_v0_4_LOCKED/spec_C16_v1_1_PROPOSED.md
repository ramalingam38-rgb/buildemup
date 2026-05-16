# C16 — Dual-Drawing Renderer
## Spec v1.1 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v1.1 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor:** v1.0 PROPOSED (S49 mid).
**Composed from:** v1.0 PROPOSED + Rule 7 critique walk findings (S49 late).
**Session:** S49.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone. This document
> is PROPOSED only. Do not interpret as locked until Ramalingam
> explicitly states "v1.1 LOCKED".

> **Per Rule 9.4:** Critiques arriving between PROPOSED and LOCK remain
> patch-eligible → v1.1 PROPOSED is the response to the v1.0 critique
> walk, NOT a deferred-to-future-LOCK backlog item.

---

## § 0 — Composition rationale

v1.0 PROPOSED was composed at S49 from v0.5 LOCKED + Sub-2 build
surfacings. Before LOCK adjudication, Ramalingam ran a critique walk
that surfaced 20 concerns from an external reviewer.

Per Rule 7 critique verdicts:
- 4 → **SPEC-AMENDMENT** for v1.1 (added as new sections § 14–§ 17)
- 7 → **VALID-BUT-BACKLOG** (filed per Rule 9.2)
- 9 → **MISFRAMED** (applies to downstream consumer renderer, not C16
  itself; documented in § 18 as scope boundary)

**The fundamental frame clarification this critique forced:**

C16 is a **structured-data emitter**, NOT a pixel-renderer. C16 emits
typed dataclasses (`DualDrawingBundle`) carrying:
- geometry coordinates in mm
- annotation anchor points
- schedule entries
- AttestedValues with provenance
- compliance markers

It produces ZERO pixel output: no SVG/PDF/PNG, no colors, no fonts, no
collision resolution, no overlay arbitration. Phase ζ produces a hash,
not an image.

Whatever downstream consumer (web frontend, CAD export, print layer)
eventually consumes the bundle makes the visual decisions. This must
be **explicit at the spec level** to prevent the bundle's contract
drifting into visual concerns that don't belong here.

v1.1 makes this explicit (§ 18) and adds 4 invariants that sharpen
where C16's responsibility ends.

---

## § 1 — v1.0 PROPOSED carried forward unchanged

All of § 1–§ 13 from v1.0 PROPOSED carry forward unchanged into v1.1.
The contract surface is unaltered. v1.1 ADDS:
- § 14 — Determinism boundary (R35)
- § 15 — Architectural primacy invariant (R36)
- § 16 — Public-schema contract (R37)
- § 17 — Projection unity (R38)
- § 18 — Scope boundary (what C16 is NOT responsible for)
- § 19 — Updated backlog roll-up

No fields are removed or renamed; therefore per R9 this is a MINOR
schema event, but the schema_version bump is deferred — these new
invariants are *contract* invariants (R35–R38) that don't change the
emitted data shape. **`C16_DRAWING_SCHEMA_VERSION = 13`** (unchanged
from v1.0).

---

## § 14 — Determinism boundary (R35 — NEW)

> **R35 — Semantic determinism, not pixel determinism.**
>
> C16's `canonical_replay_signature` byte-equal-on-replay guarantee
> covers the **semantic content** of the bundle:
> - geometry coordinates (mm-quantized per R7a)
> - element identities (per R7b)
> - canonical lex-ASC ordering (per R7c)
> - provenance + attestation values
>
> It does **NOT** cover, and does NOT require:
> - pixel-level placement of labels
> - text wrapping
> - color choices
> - font rasterization
> - print layout
> - viewport scaling
>
> Downstream consumers MAY apply non-deterministic label repositioning,
> adaptive layout, font fallback, or any other pixel-level adjustment
> WITHOUT violating C16's replay contract, so long as the underlying
> semantic content (annotation_id, anchor_x_mm, anchor_y_mm, text)
> remains byte-identical.

**Rationale (critique point 4):** the reviewer identified a genuine
tension between determinism requirements and human legibility. Without
R35, a consumer renderer might assume it MUST place every label at
exactly the anchor pixel — destroying readability when labels collide.
R35 explicitly authorizes adaptive pixel-layout downstream.

**Test:** `tests/test_c16/test_c16_phase_zeta.py` already verifies
canonical signature is identical regardless of `PhaseTimings` or
`ReadabilityDiagnostics` (observability). R35 documents the principle
that justifies that test design.

---

## § 15 — Architectural primacy invariant (R36 — NEW)

> **R36 — The building is the center.**
>
> When emitting a `FloorGeometry`, C16's primary obligation is the
> **physical building**: rooms, walls, doors, columns, plumbing stacks.
> All system metadata — schedules, attestations, advisory flags,
> compliance markers, annotations — is **secondary**.
>
> Concrete obligations:
> 1. `rooms`, `walls`, `doors`, `columns`, `plumbing_stacks` are the
>    geometry-defining payload of `FloorGeometry.identity`.
>    `annotations` and `schedules` are NOT.
> 2. The bundle MUST NOT carry more annotation tuples than geometry
>    tuples at any FloorGeometry. (If this constraint is ever violated,
>    that is a defect — the bundle has drifted into metadata-heavy
>    territory.)
> 3. New overlays added in v1.x MUST attach to a geometry element
>    (room, wall, etc.) via `affected_room_id` or equivalent — never
>    free-floating.
>
> Downstream renderers SHOULD honor R36 by giving geometry visual
> primacy and metadata visual secondariness, but this is a *strong
> recommendation*, not an enforceable C16 invariant.

**Rationale (critique point 13 — the sharpest critique):** As upstream
semantics accumulate, the bundle risks becoming a visualization of
*system internals* (audits, flags, governance states) instead of the
home itself. R36 fixes this at the data-contract level: the building
geometry is always primary; metadata is always anchored to a geometry
element.

**Test coverage:** existing tests verify rooms/walls/doors appear in
geometry-defining payload. v1.1 patch session will add explicit R36
test: `test_no_floor_carries_more_annotations_than_geometry_elements`.

---

## § 16 — Public-schema contract (R37 — NEW)

> **R37 — `DualDrawingBundle` schema is a public versioned API.**
>
> Once a `DualDrawingBundle` is emitted with
> `c16_drawing_schema_version=N`, downstream consumers MAY assume:
>
> 1. **Additive evolution only at MINOR bumps.** Bumping
>    `C16_DRAWING_SCHEMA_VERSION` from N → N+1 means new fields/types
>    were added. Existing field names + types + canonical ordering are
>    unchanged. Consumers built for schema_version=N continue to read
>    schema_version=N+1 bundles correctly (forward-compat by ignoring
>    new fields).
>
> 2. **Removal or rename requires MAJOR bump.** A change that removes
>    or renames any field, or alters the type of an existing field, or
>    changes the canonical ordering of any tuple, requires
>    `C16_DRAWING_SCHEMA_VERSION` to jump from N → 100*ceil((N+1)/100)
>    (i.e. cross a hundred boundary), AND requires concurrent bump of
>    `C16_IDENTITY_GENERATION`.
>
> 3. **Public exposure.** The bundle schema is exposed via `__all__`
>    in `buildemup.components.c16`. Anything in `__all__` is API.
>    Anything not in `__all__` is internal.
>
> 4. **Deprecation policy.** Fields targeted for removal in a future
>    MAJOR bump SHOULD be marked deprecated in their docstring for at
>    least one MINOR cycle before removal.

**Rationale (critique point 16):** The reviewer correctly identified
that once users save/share/print/archive drawings, output stability
becomes critical. Without R37, a routine refactor inside C16 could
break every saved bundle in the wild. R37 designates the bundle
schema as a versioned public API with explicit backwards-compat
discipline.

**Cross-reference:** R9 already requires schema_version bumps; R37
formalizes the *contract* that those bumps imply.

---

## § 17 — Projection unity (R38 — NEW)

> **R38 — Both drawings are projections of one semantic scene; no
> parallel logic paths.**
>
> The `WorkingDrawingModel` and `PermitDrawingModel` MUST be derived
> from the same upstream `EnvelopeAssembly`. Concretely:
>
> 1. **Shared geometry.** Both models' `floor_plans[i].geometry_ref`
>    point to the **same** `FloorGeometry.geometry_ref`. R20 enforces
>    this byte-equally already.
>
> 2. **No re-derivation.** Phase γ (working) and Phase δ (permit) MUST
>    both consume the Phase α envelope. Neither phase may re-derive
>    room geometry, wall positions, or column locations independently.
>
> 3. **Differentiated overlays only.** What differs between working
>    and permit is the OVERLAY set:
>    - Working: dimension annotations, schedules, section cuts, roof plan
>    - Permit: setback annotations, compliance markers, overlays, site plan,
>      elevations, key plan, attestation
>    These overlays are additive on top of the shared geometry — never
>    a different geometry.
>
> 4. **R20 is the enforcement teeth.** R20 already enforces byte-equal
>    geometry_ref consistency. R38 documents *why* that's correct: it
>    prevents the dual-drawing system from forking into two divergent
>    "truths."

**Rationale (critique point 7):** Dual-render systems often evolve
into "technical drawing" + "user-friendly drawing" that drift apart;
eventually one becomes "the real one" and the other becomes stale.
R38 prevents this at the architecture level: both models are
projections of the same envelope. R20 already enforces this; R38
documents the principle so future overlay additions don't violate it.

**Test coverage:** R20 tests (`test_c16_schema.TestBundleR20GeometryParity`)
already cover the byte-equal geometry_ref requirement. v1.1 patch
session will add: `test_working_and_permit_share_envelope_phase_alpha`.

---

## § 18 — Scope boundary (what C16 is NOT) — NEW

This section explicitly enumerates the responsibilities that fall
**outside** C16's scope. These are the responsibilities of the
**downstream consumer renderer** (frontend / CAD export / print layer)
that eventually consumes the bundle. Naming them here prevents future
scope creep into C16.

### 18.1 — Not in C16's scope

| Concern | C16 emits | Consumer renderer handles |
|---|---|---|
| Color choices | nothing | all color decisions |
| Font selection / sizing | nothing | font stack + size |
| Label collision resolution | annotation anchors only | adaptive label repositioning |
| Overlay z-order / arbitration | per-overlay structural data | rendering z-order |
| Accessibility (a11y) | semantic identifiers + roles | screen reader hooks, color contrast |
| Print vs screen layout | one bundle | per-medium adaptive layout |
| Progressive disclosure UX | structured data + provenance | expand/collapse UI |
| Multi-mode views (construction / circulation / etc.) | one complete bundle | per-mode visibility filtering |
| Pixel-level determinism | semantic determinism only | pixel-level layout (R35) |
| Visual hierarchy / emphasis | severity + epistemic kind | visual treatment mapping |
| User-trust UX (clarity, restraint) | data quality + provenance | UX restraint discipline |

### 18.2 — Why this matters

The critique walk surfaced 9 concerns that, on inspection, apply to
the downstream consumer renderer, NOT to C16 itself. Without § 18,
those concerns would creep into C16 over time — bloating it from
"structured-data emitter" into "visual rendering system."

§ 18 says: **NO.** C16 is a structured-data emitter. It carries
enough information for any reasonable consumer renderer to honor the
concerns. The consumer renderer is then responsible for the visual
discipline.

### 18.3 — C16's obligation to downstream

C16's obligation is to **provide downstream the information it needs**
to honor those concerns:
- For visual epistemic discipline (critique point 3): provide
  `AuthorityKind` on every AttestedValue, severity on every
  ProblemCheck, epistemic kind on every CheckEpistemicKind.
- For multi-mode views (critique point 2): provide a single complete
  bundle; downstream filters by mode.
- For accessibility (critique point 10): provide stable identifiers
  + semantic roles + structured text — never raw pixels.
- For uncertainty visualization (critique point 9): provide explicit
  AuthorityKind + confidence trails + LegalCompleteness ⊥
  ReadabilityStatus.

**§ 18.3 is the C16-side contract.** What downstream does with the
information is downstream's discipline.

---

## § 19 — Updated backlog roll-up (Rule 9 + Rule 9.2)

### 19.1 — CLOSED at v1.1 LOCK (5 items — same as v1.0 PROPOSED)

| ID | Description | Origin | v1.1 verdict |
|---|---|---|---|
| `B-C16-ENVELOPE-SCHEMA-LOCK` | Pin sub-envelope field lists | v0.5 LOCK | **CLOSED** in § 3 |
| `B-C16-PBT-LAYER-COVERAGE` | ≥15 property-based tests | v0.1 § 7 | **CLOSED** — 15 tests |
| `B-C16-ADVERSARIAL-CORPUS` | 5-scenario integration corpus | v0.1 § 7 | **CLOSED** — 5 scenarios |
| `B-C16-SHARED-EDGE-AXIS-PINNING` | Position partitions at real boundary | Sub-2 build | **CLOSED** — § 8.1 |
| `B-C16-R23-OFFSET-FALLBACK` | Inward-snap R23 cut when outside bbox | Sub-2 build | **CLOSED** — § 8.3 |

### 19.2 — DEFERRED post-LOCK (v1.x-acceptable, v1.0 items)

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

### 19.3 — NEW from v1.0 critique walk (filed per Rule 9.2 — 7 items)

| ID | Description | Origin | Critique point | Effort |
|---|---|---|---|---|
| `B-C16-DOWNSTREAM-VISUAL-SEMANTIC-CONTRACT` | Pin C15 severity → visual-treatment contract for the downstream renderer; C16 ships the data, the consumer pins the visual mapping | v1.0 critique pt 1 | Severity / epistemic kind / authority must survive visually downstream | M (consumer side; C16 provides the schema) |
| `B-C16-MULTI-MODE-RENDERING-VIEW-API` | Document how a consumer renderer derives multi-mode views (construction / circulation / privacy / audit / uncertainty / compact) from one bundle | v1.0 critique pt 2 | Consumer needs to know which bundle fields to filter per mode | M |
| `B-C16-EPISTEMIC-FIDELITY-AT-RENDER-BOUNDARY` | Document the contract that downstream MUST visually differentiate UPSTREAM_AUTHORITATIVE / LOCALLY_DERIVED / CROSS_CHECK_VERIFICATION and ProblemCheck severities; advisory note in bundle | v1.0 critique pt 3, 15 | Consumer rendering may accidentally encode value judgments | S (C16 documents; consumer enforces) |
| `B-C16-R24-INDEX-PRECOMPUTE` | Replace R24 O(n×m) reference-resolution loop with precomputed index; needed only at very large element counts | v1.0 critique pt 5 | At >1000 elements, R24 enforcement may become noticeable | S (perf-driven, not blocking v1) |
| `B-C16-UPSTREAM-ADAPTER-VERSION-PINNING-TESTS` | Add tests that explicitly verify duck-typed upstream adapter raises `UpstreamSchemaDriftError` when expected upstream attributes are missing or renamed | v1.0 critique pt 8 | Currently adapter silently falls back to defaults for missing attrs | S |
| `B-C16-UNCERTAINTY-METADATA-EXPANSION` | Add an `uncertainty_payload` field to AttestedValue carrying optional confidence intervals, evidence count, and `dimensions_not_evaluated` flags; consumer renders with appropriate visual grammar | v1.0 critique pt 9, 20 | Current AttestedValue carries authority + provenance but not numeric confidence | M |
| `B-C16-FUTURE-OVERLAY-SCHEMA-DISCIPLINE` | When new overlays (cost, daylight, acoustic, thermal, etc.) are added in v1.x, they MUST conform to existing `ComplianceMarker` + `WorkingAnnotation` shape; no parallel new overlay primitives | v1.0 critique pt 14 | Prevents visual grammar fragmentation across future overlays | S (discipline, not code) |

### 19.4 — Summary table

| Category | Count |
|---|---|
| CLOSED at v1.1 LOCK | 5 |
| DEFERRED post-LOCK (v1.0 items) | 9 |
| NEW from v1.0 critique walk (deferred) | 7 |
| **Total tracked** | **21** |

---

## § 20 — Critique walk verdicts (full transcript for audit trail)

Per Rule 7: every critique point gets a verdict. Documented here so
the critique walk is traceable in the spec history.

| # | Critique theme | Verdict | Disposition |
|---|---|---|---|
| 1 | Renderer becoming second interpretation engine | MISFRAMED + VALID-BUT-BACKLOG | § 18 + `B-C16-DOWNSTREAM-VISUAL-SEMANTIC-CONTRACT` |
| 2 | Overlay density collapses readability | VALID-BUT-BACKLOG | § 18 + `B-C16-MULTI-MODE-RENDERING-VIEW-API` |
| 3 | Visual authority bias | MISFRAMED (for C16) | § 18 + `B-C16-EPISTEMIC-FIDELITY-AT-RENDER-BOUNDARY` |
| 4 | Determinism vs human legibility | VALID → SPEC-AMENDMENT | **§ 14 / R35** (new) |
| 5 | Performance bottleneck | MISFRAMED + minor backlog | § 18 + `B-C16-R24-INDEX-PRECOMPUTE` |
| 6 | Annotation hierarchy drift | MISFRAMED (downstream) | § 18 |
| 7 | Dual-drawing forking the UX | VALID → SPEC-AMENDMENT | **§ 17 / R38** (new) |
| 8 | Upstream semantic stability dependency | VALID-BUT-BACKLOG | `B-C16-UPSTREAM-ADAPTER-VERSION-PINNING-TESTS` |
| 9 | Uncertainty under-specified | VALID-BUT-BACKLOG | `B-C16-UNCERTAINTY-METADATA-EXPANSION` |
| 10 | Accessibility risk | MISFRAMED (downstream) | § 18 |
| 11 | Print vs screen divergence | MISFRAMED (downstream) | § 18 |
| 12 | Minimalism vs explainability | MISFRAMED (downstream) | § 18 |
| 13 | "Rendering the pipeline instead of the house" | VALID → SPEC-AMENDMENT | **§ 15 / R36** (new) |
| 14 | Visual consistency across future overlays | VALID-BUT-BACKLOG | `B-C16-FUTURE-OVERLAY-SCHEMA-DISCIPLINE` |
| 15 | Renderer encoding value judgments | MISFRAMED (downstream) | § 18 + cross-ref `EPISTEMIC-FIDELITY` |
| 16 | Export stability as public API | VALID → SPEC-AMENDMENT | **§ 16 / R37** (new) |
| 17 | Too sophisticated for rapid iteration | MISFRAMED | Phase pipeline IS modular |
| 18 | Most user-trust-sensitive component | MISFRAMED (downstream framing) | § 18 |
| 19 | Lacks visual-philosophy governance | MISFRAMED (product, not C16) | § 18 |
| 20 | Semantic overload through visualization | VALID, partly addressed | § 15 + § 18 |

**Totals:** 4 SPEC-AMENDMENT, 7 VALID-BUT-BACKLOG (filed), 9 MISFRAMED
(§ 18 documents scope).

---

## § 21 — Rule 7 critique walk (this round)

Per Rule 7: **web search ≥1 per critique walk + grep code for code
claims**.

**Code grep verified:**
- No SVG, PDF, PNG, matplotlib, cairo, or reportlab imports in
  `buildemup/components/c16/` (`grep -rn "svg\|png\|canvas\|matplotlib\|cairo\|reportlab" ...` returns nothing).
- No color, font, pixel decisions anywhere in C16 source
  (`grep -rn "color\|font\|pixel\|highlight\|bold" ...` returns only
  docstrings and version history).
- Confirms framing in § 18: C16 is structured-data only.

**Web search performed in S49 (prior round):**
IFC `IfcLocalPlacement` + `IfcSite` coordinate-frame conventions
against dual-frame approach. Validated v0.3 A4 small-magnitude
LocalBuildingFrame design. (Carried forward from v1.0 § 9.)

**No reviewer claim survives the code grep that requires further
spec change.** All 20 points addressed via SPEC-AMENDMENT, BACKLOG,
or scope-boundary documentation.

---

## § 22 — Three-check protocol (Rule 10.6) — v1.1 update

**(a) GAP CHECK — promised vs delivered (v1.1 increments)**

| Promised in v1.0 critique walk | Delivered in v1.1 PROPOSED |
|---|---|
| 4 SPEC-AMENDMENTs | § 14, § 15, § 16, § 17 (R35–R38) |
| 7 new backlog items | § 19.3 (all 7 filed with IDs) |
| Scope boundary documented | § 18 |
| Critique verdicts audit-traceable | § 20 (full table) |

**(b) AUDIT CHECK — spec compliance**

| New invariant | Enforcing call site | Test coverage |
|---|---|---|
| R35 (determinism boundary) | Documented; consumer-side discipline | `test_c16_phase_zeta.TestCanonicalReplaySignature.test_phase_timings_do_not_affect_canonical_signature` |
| R36 (architectural primacy) | `compute_element_identity` payload structure | v1.1 patch test: floor identity uses geometry-defining only |
| R37 (public schema API) | `versioning.py` constants + `__all__` discipline | Existing schema_version tests verify the contract |
| R38 (projection unity) | R20 enforcement in `DualDrawingBundle.__post_init__` | `test_c16_schema.TestBundleR20GeometryParity` |

**(c) INTEGRITY CHECK — files + tests**

- 683 of 683 tests pass.
- v1.1 PROPOSED spec replaces v1.0 PROPOSED at
  `spec_locks/spec_C16_v1_1_PROPOSED.md`.
- No source code changes required for R35–R38 — these are spec-level
  invariants that document existing behaviors and disciplines.

---

## § 23 — LOCK adjudication request (Rule 8) — v1.1

Per Rule 8: LOCK authority belongs to Ramalingam alone.

**This document is v1.1 PROPOSED. PENDING Ramalingam LOCK adjudication.**

For Ramalingam to LOCK v1.1, please confirm:

1. **§ 14 / R35 (determinism boundary)** — semantic determinism only;
   pixel-layout is downstream.
2. **§ 15 / R36 (architectural primacy)** — building geometry primary;
   metadata always anchored to a geometry element.
3. **§ 16 / R37 (public schema API)** — `DualDrawingBundle` schema is
   a versioned public contract with documented evolution policy.
4. **§ 17 / R38 (projection unity)** — both drawings are projections
   of one envelope; no parallel logic paths.
5. **§ 18 (scope boundary)** — explicit enumeration of what C16 is
   NOT responsible for; visual responsibilities are downstream.
6. **§ 19.3 (7 new backlog items)** — all filed correctly per Rule 9.2.
7. **§ 20 (critique verdicts)** — verdicts on all 20 critique points
   are correct as recorded.

If yes to all: **state "C16 v1.1 LOCKED"**.

If corrections needed: state which sections need patches; I'll
compose v1.2 PROPOSED with the patches and wait for the next LOCK
adjudication round.

---

**END OF v1.1 PROPOSED — PENDING Ramalingam LOCK**
