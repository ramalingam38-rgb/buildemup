# C12 v1.0 LOCKED — backlog additions from S44 external critique walk

**Origin**: External review of C12 v1.0 LOCKED code zip (S44).
**Walk verdict (Rule 7)**: 7 of 12 reviewer items MISFRAMED-FOR-C12
(correctly applicable to C3a / C14 / C15 / project-scope); 4 items
genuinely C12-scoped; 1 pushback. New backlog items below (Rule 9.2:
file VALID-BUT-BACKLOG immediately).

---

## New backlog items

### B-C12-CAUSAL-FAILURE-TRACEABILITY

**Origin**: S44 external review item 6 (Limited Explanatory Traceability)
**Verdict**: VALID
**Trigger condition**: When production failure investigation requires
constraint → affected room → propagated conflict chain reconstruction
that the current `FailureRecord(error_type, error_message, phase)`
schema can't provide.
**Scope**: Extend `FailureRecord` (post-LOCK schema amendment) or ship
a parallel `FailureTrace` structure (preferred — keeps v1.0 LOCKED
schema immutable) that captures:
  - Which invariant raised
  - Which room(s) participated
  - Which upstream constraint(s) triggered the cascade
  - Phase-by-phase state at failure point
**Effort estimate**: M (1-2 sessions). Requires deciding whether to
amend `FailureRecord` (LOCK-breaking) or ship parallel `FailureTrace`
returned via `place_and_align_with_provenance` (LOCK-preserving).
Preferred: parallel structure to preserve v1.0 LOCKED schema.
**Pre-conditions**: None — orthogonal to v1 functional surface.

---

### B-C12-MISALIGNMENT-SEVERITY-SCORING

**Origin**: S44 external review item 9 (Vertical Alignment Rigidity)
**Verdict**: PARTIALLY VALID (after pushback on "rigidity" framing —
VAV already uses tolerance-based soft acceptance; the genuine gap is
absence of a *severity score* for WARN-mode misaligned features)
**Trigger condition**: When downstream consumers (C14 scoring layer)
need to prioritize misaligned features by severity rather than a
binary aligned/not-aligned flag.
**Scope**: Add `severity_score: float` field to misaligned-feature
records in `VerticalAlignmentReport`. Score is a function of:
  - Distance from consensus centroid (ratio to tolerance)
  - Feature kind weight (staircase > wet-zone > structural column)
  - Number of floors involved
Range [0.0, 1.0] with 0.0=aligned within tolerance and 1.0=catastrophic.
**Effort estimate**: S (1 session). Score definition needs C14
coordination — premature without C14 scoring layer.
**Pre-conditions**: C14 (or successor scoring component) shipped.

---

### B-C12-LAYOUT-MEMORY-BANK

**Origin**: S44 external review item 12 (No Learning From Past Layouts)
**Verdict**: OUT-OF-SCOPE for v1 LOCK; VALID for v2+
**Trigger condition**: When production data accumulation reaches the
threshold where retrieval-assisted topology initialization would
demonstrably improve placement quality vs the deterministic
slicing-tree baseline.
**Scope**: Layout memory bank with:
  - Topology fingerprinting (hash of placed-room adjacency graph +
    envelope ratio + room categories)
  - Reinforcement scoring from accepted plans (post-C15 user-feedback
    signal)
  - Retrieval-assisted initialization: seed the slicing-tree with a
    permutation/cut-fraction order known to work for similar topologies
**Effort estimate**: L (3-4 sessions). Major architectural addition;
breaks v1's deterministic-by-construction guarantee unless retrieval
is itself deterministic (replay-safe).
**Pre-conditions**:
  - C15 user-feedback signal ingested
  - Min N=200 accepted plans in production
  - Replay-safety design for the retrieval lookup (Inv 7 must hold)

---

### B-PROJECT-SPEC-DRIFT-CI

**Origin**: S44 external review item 8 (Spec-Source Inconsistency)
**Verdict**: VALID, project-scope (not C12-scope)
**Trigger condition**: When LOCKED spec docs and their corresponding
production code drift apart without detection — e.g., a code change
silently invalidates a LOCKED invariant statement.
**Scope**: CI check that:
  - Parses LOCKED spec markdown for invariant statements (Inv 1, Inv
    2, ... format)
  - Matches each to a corresponding test or assertion in production
    code
  - Fails CI on uncovered invariants or removed-but-still-spec'd
    behaviors
**Effort estimate**: M (1-2 sessions). Cross-cuts all 17 canonical
components; needs project-level coordination.
**Pre-conditions**: All canonical components shipped (so the parsing
scope is bounded).
**Routing note**: NOT a C12 item — project-scope. Filing here for
visibility; should eventually migrate to a project-level backlog
when the dedicated project-scope backlog file is created
(B-PROJECT-BACKLOG-CONSOLIDATION).

---

## Existing items the critique re-discovered (no action — already filed)

| Critique item | Existing backlog item / location | Notes |
|---|---|---|
| 2 (constraint-solver gap) | B-C12-CSP-PLACEMENT | Web search confirmed CP-SAT for floor planning is academic mainstream (ScienceDirect 2020 + arxiv 2025); priority validated |
| 3 (combinatorial explosion, slicing-tree) | B-C12-PLACEMENT-PRUNING | Already filed S43 |
| 3 (combinatorial explosion, MFRA retry) | DOCUMENTED in v0.2-A2 + v0.3-A2 (bounded retries + monotonic-δ abort) | Spec acknowledges + mitigates |
| 3 (staged solving suggestion) | DOCUMENTED — Phase 1b → Phase 2 → Phase 1 is exactly what's shipped | Pushback |
| 7 (preview mode misinterpretation) | C3a SPEC v0.2.1 LOCKED already implements mandatory checkbox + room-internal watermarks @ 30% opacity + dimension-ranges-only | Cross-component; C3a handles this |
| 11 (schema versioning suggestion) | DOCUMENTED — already implemented at v0.4-A1 (UpstreamSchemaDriftError) | Pushback: already shipped |

---

## Misframed items — explicit pushback

These reviewer items are NOT C12-scoped (verified by code grep):

**Item 1 (Hard-coded thresholds, EC_001):** Grep confirms
`EC_001_DROP_ROOM_THRESHOLD` lives in `c03a/option_generator.py`,
NOT C12. C12's only hardcoded constants are NBC 2016 doorway minima
(federal floor — state DCRs only add stricter requirements per web-
verified NBC governance), ε=1mm, grid=50mm, version strings.
**Route to C3a backlog if reviewer wants city-policy-pack layer
for C3a thresholds.**

**Item 4 (Test fixture over-dependence):** Grep + file inspection:
C12 test suite includes `test_c12_property_based.py` (26 PBT tests
per v0.6-A1 invariant-grounded floor) with Hypothesis-based
adversarial generators covering exact-fit, tiny-residual, alias-
normalization, high-density-adjacency, staircase-conflict, env-hash
permutation. Reviewer's "over-dependence on fixtures" was either
looking at older C11a stress fixtures or didn't see the PBT layer.
**Pushback: PBT layer already addresses this.**

**Item 5 ("Different plot" escape hatch):** Grep: no
`different_plot` / "find another plot" pathway in C12. That's
C3a/C14 option-generation territory. **Route to C3a.**

**Item 10 (Cost models heuristic):** Grep: no cost models in C12.
C14/C15 territory. **Route to C14/C15.**

**Item 11 (Invariant heaviness — separate hard/soft):** C12's 13
invariants are all structural-correctness (containment, non-overlap,
determinism, canonical ordering, replay byte-equality). These cannot
be "soft" without breaking the algorithm's correctness contract.
Reviewer's hard/soft separation is fine for qualitative-judgment
layers (C3a thresholds, C5 zone bands, C14 scoring) but not for
C12. **Pushback: structural invariants are necessarily hard.**

---

## Summary table

| New B-NNN | Verdict | Effort | Pre-condition |
|---|---|---|---|
| B-C12-CAUSAL-FAILURE-TRACEABILITY | VALID, C12-scope | M | None |
| B-C12-MISALIGNMENT-SEVERITY-SCORING | PARTIALLY VALID, C12-scope | S | C14 shipped |
| B-C12-LAYOUT-MEMORY-BANK | OUT-OF-SCOPE v1, v2+ | L | C15 + N=200 accepted plans + replay-safe retrieval design |
| B-PROJECT-SPEC-DRIFT-CI | VALID, project-scope | M | All 17 components shipped |

**Total new items filed: 4 (3 C12-scoped, 1 project-scoped)**

Walk closes per Rule 7. Per Ramalingam directive S44: "Lock it and
file the backlogs and let's move on to next component."
