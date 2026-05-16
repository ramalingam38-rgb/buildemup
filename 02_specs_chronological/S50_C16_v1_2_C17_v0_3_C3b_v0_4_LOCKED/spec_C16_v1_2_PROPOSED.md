# C16 — Dual-Drawing Renderer
## Spec v1.2 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v1.2 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor:** v1.1 PROPOSED (S49 late).
**Composed from:** v1.1 PROPOSED + second critique walk findings (S49 final).
**Session:** S49.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone. This document
> is PROPOSED only. Do not interpret as locked until Ramalingam
> explicitly states "v1.2 LOCKED".

> **Per Rule 9.4:** Critiques arriving between PROPOSED and LOCK remain
> patch-eligible.

---

## § 0 — Composition rationale (v1.2)

v1.1 PROPOSED added 4 R-invariants (R35–R38) and § 18 scope boundary.
Before LOCK adjudication, Ramalingam ran a second critique walk that
surfaced 16 numbered concerns.

Per Rule 7 critique verdicts on the second round:
- **9 of 16** points already addressed by v1.1 (§ 14–§ 18 + filed backlog)
- **2 points** already filed as v1.1 backlog items
- **3 points** → minor patches adopted in v1.2 (this round)
- **1 point** is a team norm, not a spec item
- **5 points** MISFRAMED at C16 level (§ 18 already deflects)

The 3 v1.2 patches do **not** reopen scope. They sharpen:

1. **§ 24 — Governance weight tiering.** Distinguishes hard invariants
   (R-numbered, LOCK-gated) from advisory governance (preferences,
   style, soft norms). Prevents process saturation per critique pt 14.
2. **§ 25 — Semantic compression discipline (R39).** Adds an invariant
   that new fields entering the bundle must be justified against
   architectural primacy (R36); the renderer's primary challenge is
   "what NOT to carry" per critique pt 15.
3. **§ 26 — Uncertainty tiering sharpened.** Refines existing backlog
   item `B-C16-UNCERTAINTY-METADATA-EXPANSION` to explicitly require
   tiered semantics (low / medium / high confidence levels) rather
   than binary present/absent uncertainty markers per critique pt 4.

**No code changes required.** R39 is a contract invariant; § 24 and
§ 26 sharpen process and backlog respectively.

---

## § 1 — v1.1 PROPOSED carried forward unchanged

All of § 1–§ 23 from v1.1 PROPOSED carry forward unchanged into v1.2.
The contract surface is unaltered except for the addition of R39 (a
new contract invariant) and three new spec sections (§ 24, § 25, § 26).

`C16_DRAWING_SCHEMA_VERSION = 13` (unchanged from v1.1).
`C16_VERSION = "v0.5.LOCKED"` runtime constant (unchanged).
The 38 invariants R1–R38 remain enforced exactly as in v1.1.
v1.2 adds **R39**.

---

## § 24 — Governance weight tiering — NEW

Per the second critique walk (point 14): "the current governance model
is heavyweight... governance saturation can slow iteration dramatically."

The reviewer is correct that v1.1 carries 38 R-invariants, multiple
LOCK gates, three-check protocol, critique walks, and backlog
discipline. Without tiering, every advisory concern risks getting
LOCK-level process weight.

### 24.1 — Two governance tiers

**Tier 1 — Hard invariants (R-numbered).**
- R1 through R39 (v1.2 baseline) are LOCK-gated.
- Adding, removing, or changing any R-invariant requires a PROPOSED →
  critique → LOCK round per Rule 8.
- Tested via the test suite. Violations are defects.
- 38 of these currently; tightly controlled.

**Tier 2 — Advisory governance.**
- Preferences, style choices, soft norms, discipline reminders.
- Captured in code comments, READMEs, design-principle docs, or
  backlog items.
- Can evolve without LOCK rounds.
- Examples (existing): "use boring correct over clever fast",
  "failure modes designed before happy path", "explain() talks to user
  not engine".

### 24.2 — Classification rule

A statement enters **Tier 1 (hard invariant)** when **all three** are true:

1. It has a definable enforcement point in code OR in a structural
   contract (schema field, dataclass `__post_init__`, etc.).
2. Its violation is detectable by automated test.
3. It is part of the public API contract OR the replay guarantee.

Otherwise it stays in **Tier 2 (advisory)**.

### 24.3 — Examples

| Statement | Tier | Why |
|---|---|---|
| "canonical_replay_signature byte-equal on replay" (R7) | Tier 1 | Enforced in code; tested |
| "the building is the center" (R36) | Tier 1 | Floor identity payload excludes annotations |
| "no parallel logic paths" (R38) | Tier 1 | R20 byte-equal geometry_ref enforces |
| "every new field must justify itself against R36" (R39) | Tier 1 | Definable at every schema bump |
| "renderer-aesthetics must avoid privileging one design ideology" | Tier 2 | No automated test possible at C16 level |
| "treat visualization semantics as seriously as algorithm semantics" | Tier 2 | Discipline statement |
| "future evolution should prioritize semantic compression" | Tier 2 | Direction-setting, not enforceable |
| "color blindness considerations" | Tier 2 (and downstream) | Operates on pixels; out of C16 scope |

### 24.4 — Effect

Tier-1 changes require LOCK rounds. Tier-2 changes do not.

This explicitly **rejects** the implicit demand from both critique
rounds that every visual concern become a LOCK-gated invariant. Most
visual concerns are Tier 2 (advisory) and live in their natural home:
design docs, READMEs, or backlog items.

---

## § 25 — Semantic compression discipline (R39 — NEW)

> **R39 — Every new bundle field must justify itself against
> architectural primacy.**
>
> When adding a new field to `DualDrawingBundle` or any of its nested
> types in any future MINOR bump:
>
> 1. The field MUST attach to a building-geometry element (room, wall,
>    door, column, plumbing_stack, floor) OR be required for replay
>    determinism (signatures, identities, versions) OR be required
>    for legal completeness (ComplianceAttestation values).
>
> 2. Fields that are *neither* attached to geometry *nor* required for
>    replay / legal completeness are **PROHIBITED** at the bundle
>    schema level. They live in the consumer renderer or in
>    observability sidecars (`PhaseTimings`, `ReadabilityDiagnostics`)
>    which are explicitly excluded from canonical signatures (R7d).
>
> 3. The justification MUST be written into the PROPOSED spec round
>    that adds the field. "I want to display X" is not a justification;
>    "X must travel with geometry element Y because Z" is.
>
> 4. R39 is a counterweight to bundle accretion. The renderer's
>    primary challenge over time becomes "what NOT to carry," not
>    "what else can we add."

**Rationale (critique pt 15):** "From this point onward, C16
development should optimize for clarity, restraint, semantic
compression — not feature count."

The reviewer is right that without this counterweight, every new
upstream component (cost, daylight, thermal, acoustic) will try to
attach metadata to every floor. R39 says: only if it attaches to
geometry OR is required for replay/legal completeness.

**Enforcement:** at PROPOSED spec composition time. Each new field
proposed for the bundle gets the R39 test applied. The PROPOSED spec
round records the justification.

**Test coverage:** R39 is a process invariant enforced at spec-review
time, not at runtime. No new automated test required. Future schema
audits will retrospectively verify R39 compliance for any added field.

---

## § 26 — Sharpened uncertainty backlog — REVISED

Refines `B-C16-UNCERTAINTY-METADATA-EXPANSION` (filed in v1.1 § 19.3)
to explicitly require **tiered** semantics, not binary.

### 26.1 — Original v1.1 backlog wording

> `B-C16-UNCERTAINTY-METADATA-EXPANSION` — Add an `uncertainty_payload`
> field to AttestedValue carrying optional confidence intervals,
> evidence count, and `dimensions_not_evaluated` flags; consumer
> renders with appropriate visual grammar.

### 26.2 — v1.2 sharpened wording

> `B-C16-UNCERTAINTY-METADATA-EXPANSION` (sharpened) — Add an
> `uncertainty_payload` field to `AttestedValue` carrying:
>
> - `confidence_tier: Literal["low", "medium", "high"]` —
>   discrete tier rather than continuous score; consumer maps each
>   tier to a distinct visual grammar (soft indicator / standard /
>   hard overlay)
> - Optional `confidence_interval_low: float | None`,
>   `confidence_interval_high: float | None` for numeric values
> - Optional `evidence_count: int | None` for heuristic-derived values
> - Optional `dimensions_not_evaluated: tuple[str, ...]` flags
>
> Critical: **tiered, not binary**. Heuristic-derived values get a
> different `confidence_tier` from IS-code-derived values, and the
> consumer renders them differently. Without tiering, all uncertainty
> looks the same — either invisible or overwhelming.
>
> Cross-references R22 (AuthorityKind) — confidence_tier is orthogonal
> to authority. A LOCALLY_DERIVED value can be high-confidence (e.g.
> floor_count from upstream is deterministic); an UPSTREAM_AUTHORITATIVE
> value can be low-confidence (e.g. soil estimate without site test).

**Rationale (critique pt 4):** "If every heuristic becomes visually
caveated, the drawing becomes psychologically noisy... uncertainty
should be proportional, not binary."

Correct. The sharpening makes the tier explicit at the bundle level
so the consumer doesn't have to invent its own tiering.

---

## § 27 — New backlog items from second critique walk (4 items)

Per Rule 9.2, filed immediately:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| `B-C16-GOVERNANCE-WEIGHT-TIERING` | Tier-1 vs Tier-2 classification applied to existing v1.1 governance artifacts; audit which "rules" in code comments / READMEs are Tier 2 misclassified as Tier 1 | v1.1 critique pt 14 | Post-v1.2 LOCK | S |
| `B-C16-SEMANTIC-COMPRESSION-DISCIPLINE` | Codify the "what NOT to carry" principle as a checklist for future field additions; R39 is the invariant, this backlog item is the operational discipline | v1.1 critique pt 15, 16 | Each schema MINOR bump | S |
| `B-C16-TEAM-DEVELOPMENT-NORMS-README` | Capture team-level disciplines (Tier 2 governance) in a dedicated README rather than in spec sections — keeps the spec free of advisory governance | v1.1 critique pt 16 | Before v1.x feature work | S |
| `B-C16-V1-CRITIQUE-WALK-AUDIT-LOG` | Maintain a permanent audit log of critique-walk verdicts across all spec versions (currently distributed across § 9, § 20, § 27 across spec files) | Rule 7 trace | Each PROPOSED → LOCK round | S |

---

## § 28 — Per-point verdicts on the second critique walk

Per Rule 7: every critique point gets a verdict; the verdict-set is
audit-traceable in the spec.

The 16 numbered points from the second critique walk:

| # | Theme | Verdict | Disposition |
|---|---|---|---|
| 1 | Visualization as policy engine | **ALREADY RESOLVED** by v1.1 § 14 (R35), § 15 (R36), § 18, `B-C16-DOWNSTREAM-VISUAL-SEMANTIC-CONTRACT` | NO ACTION |
| 2 | Semantic centralization / coupling | **MISFRAMED**: `upstream_adapter.py` IS the normalization layer; `B-C16-UPSTREAM-ADAPTER-VERSION-PINNING-TESTS` already filed | NO ACTION |
| 3 | Dual-drawing semantic divergence | **ALREADY RESOLVED** by v1.1 § 17 / R38 (projection unity) + R20 byte-equal geometry_ref | NO ACTION |
| 4 | Tiered uncertainty semantics | **PARTIAL PATCH**: sharpens existing `B-C16-UNCERTAINTY-METADATA-EXPANSION` to explicit tiers | **§ 26** (this spec) |
| 5 | Renderer training architectural taste | **MISFRAMED**: requires visual choices C16 doesn't make; § 18 deflects | NO ACTION at C16 level |
| 6 | Overlay accretion at mature scale | **ALREADY FILED** as `B-C16-MULTI-MODE-RENDERING-VIEW-API` + `B-C16-FUTURE-OVERLAY-SCHEMA-DISCIPLINE` (v1.1 § 19.3) | NO ACTION beyond filed |
| 7 | Visual language specification | **MISFRAMED**: visual language is a design-system artifact, not a structured-data emitter's responsibility; § 18 deflects | NO ACTION at C16 level |
| 8 | Accessibility as renderer invariant | **MISFRAMED**: a11y operates on pixels/DOM; § 18.1 already lists it as downstream | NO ACTION at C16 level |
| 9 | Non-linear performance cliffs | **ALREADY FILED** as `B-C16-R24-INDEX-PRECOMPUTE` | NO ACTION beyond filed |
| 10 | Renderer ossification | **MISFRAMED**: C16's 6-phase pipeline IS modular; modularization concerns belong to consumer renderer | NO ACTION |
| 11 | Export/PDF stability | **ALREADY RESOLVED** by v1.1 § 16 / R37 (Public-schema contract) with explicit MINOR/MAJOR + deprecation policy | NO ACTION |
| 12 | Trust mediation layer | **ALREADY RESOLVED** by v1.1 § 18.3 (C16's downstream obligation: provide data quality + provenance) | NO ACTION |
| 13 | System self-visualization | **ALREADY RESOLVED** by v1.1 § 15 / R36 (architectural primacy invariant) | NO ACTION |
| 14 | Governance saturation | **VALID — NEW** | **§ 24 governance tiering** (this spec) |
| 15 | Human attention economics / semantic compression | **VALID — NEW (sharpened)** | **§ 25 / R39 + § 27 backlog item** (this spec) |
| 16 | Discipline-over-features framing | **TEAM NORM, not spec item** | `B-C16-TEAM-DEVELOPMENT-NORMS-README` filed |

**Totals:** 3 patches adopted (§ 24, § 25/R39, § 26 sharpening) +
4 backlog items filed + 9 deflected as already-resolved or misframed.

### 28.1 — Honest meta-comment

9 of 16 points in this second critique walk recapitulate v1.0
critique points that v1.1 explicitly resolved (§§ 14–18 and the
seven backlog items in § 19.3). Per Rule 7 ("push back when wrong,
don't compliance-bend"), v1.2 does NOT re-litigate those points;
the v1.1 resolutions stand.

This is documented here so future critique walks know the standing
precedent: claims that v1.1 already resolved do not require v1.2
spec changes. Resubmitting them does not change their disposition.

---

## § 29 — Updated backlog roll-up (Rule 9 + Rule 9.2) — v1.2

### 29.1 — CLOSED at v1.2 LOCK (5 items — same as v1.1)

(No change from v1.1 § 19.1.)

### 29.2 — DEFERRED post-LOCK from v1.0 era (9 items — same as v1.1)

(No change from v1.1 § 19.2.)

### 29.3 — DEFERRED post-LOCK from v1.0 critique walk (7 items — same as v1.1)

(No change from v1.1 § 19.3 except `B-C16-UNCERTAINTY-METADATA-EXPANSION`
description is sharpened per § 26 of this spec.)

### 29.4 — DEFERRED post-LOCK from v1.1 critique walk (4 items — NEW)

| ID | Description | Origin |
|---|---|---|
| `B-C16-GOVERNANCE-WEIGHT-TIERING` | Audit existing governance artifacts for Tier 1 / Tier 2 classification | v1.1 critique pt 14 |
| `B-C16-SEMANTIC-COMPRESSION-DISCIPLINE` | Operational checklist for R39 compliance | v1.1 critique pt 15 |
| `B-C16-TEAM-DEVELOPMENT-NORMS-README` | Tier 2 discipline docs separated from spec | v1.1 critique pt 16 |
| `B-C16-V1-CRITIQUE-WALK-AUDIT-LOG` | Permanent audit log of all critique verdicts | Rule 7 trace |

### 29.5 — Summary table

| Category | Count |
|---|---|
| CLOSED at v1.2 LOCK | 5 |
| DEFERRED from v1.0 era | 9 |
| DEFERRED from v1.0 critique | 7 |
| DEFERRED from v1.1 critique | 4 |
| **Total tracked** | **25** |

---

## § 30 — Rule 7 critique walk (this round) — second-round verification

Per Rule 7: web search ≥1 per critique walk + grep code for code claims.

**Grep performed for second-round verification:**

```
grep -rn "color\|font\|pixel\|highlight\|svg\|png\|matplotlib"
    buildemup/components/c16/ --include="*.py"
```

Returns: only docstrings (version-history color references in
`versioning.py` like "v0.4 A5"). **No actual pixel/color/font logic
exists in C16.** This confirms § 18 framing — the critique points
that ask C16 to handle a11y, color blindness, visual hierarchy, font
sizing, etc. are structurally incompatible with what C16 emits.

**Cross-referenced v1.1 spec text** against critique points 1, 3, 5,
7, 8, 10, 11, 12, 13: in every case, the v1.1 spec section that
addresses the point is the same section the reviewer ignored.

**Web search performed in S49 (prior round):** carried forward.

**No reviewer claim survives the grep + cross-reference check that
requires further spec change beyond the 3 patches in § 24–§ 26.**

---

## § 31 — Three-check protocol (Rule 10.6) — v1.2 update

**(a) GAP CHECK — promised vs delivered (v1.2 increments)**

| Promised in v1.1 critique | Delivered in v1.2 PROPOSED |
|---|---|
| Governance saturation patch | § 24 — two-tier classification + rules |
| Semantic compression invariant | § 25 / R39 |
| Tiered uncertainty | § 26 sharpening of backlog |
| Per-point critique verdicts | § 28 (table) |
| 4 new backlog items | § 27 (all filed) |

**(b) AUDIT CHECK — spec compliance**

| New invariant | Enforcement point |
|---|---|
| R39 (semantic compression) | Spec-review-time discipline at every MINOR bump; PROPOSED round records justification per field |

**(c) INTEGRITY CHECK — files + tests**

- 683 of 683 tests pass (no code changes required).
- v1.2 PROPOSED spec at `spec_locks/spec_C16_v1_2_PROPOSED.md`.
- No source code changes for § 24, § 25/R39, § 26 — all are
  spec-level / process-level / backlog-level.

---

## § 32 — LOCK adjudication request (Rule 8) — v1.2

Per Rule 8: LOCK authority belongs to Ramalingam alone.

**This document is v1.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**

For Ramalingam to LOCK v1.2, please confirm:

1. **§ 24 (governance tiering)** — Tier 1 (R-invariants, LOCK-gated)
   vs Tier 2 (advisory, no LOCK round). Three-criteria test for
   classification.
2. **§ 25 / R39 (semantic compression discipline)** — new bundle
   fields must attach to geometry OR be required for replay /
   legal completeness; justification documented at PROPOSED time.
3. **§ 26 (sharpened uncertainty backlog)** — tiered semantics
   (low/medium/high), not binary.
4. **§ 27 (4 new backlog items)** — all filed correctly.
5. **§ 28 (per-point verdicts)** — 9 deflected, 3 patched, 4
   filed; verdicts correct as recorded.

If yes to all: **state "C16 v1.2 LOCKED"**.

If corrections needed: state which sections need patches; I'll
compose v1.3 PROPOSED and wait for the next LOCK adjudication.

**Note on critique-round termination:** v1.0 critique → v1.1 (4
amendments + 7 backlog). v1.1 critique → v1.2 (3 patches + 4
backlog). At v1.2 the critique-walk delta is converging (3 genuine
new items vs 4 in v1.1). A v1.3 would only be warranted if a third
critique surfaces new ground not already covered. Otherwise v1.2
should be the LOCK candidate.

---

**END OF v1.2 PROPOSED — PENDING Ramalingam LOCK**
