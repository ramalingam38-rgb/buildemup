# spec_C16_v0_5_LOCKED.md

**Component 16 — Dual-Drawing Renderer**
**Status:** v0.5 LOCKED at S47.
**LOCK Authority:** Ramalingam, directive "Lock this and give me the handoff..." — S47, 2026-05-14.
**LOCK level:** SKETCH (per the project's v0.6 C13-LOCK-gating convention reused here, same as C14/C15 LOCKs).

---

## Reading order — the LOCKED v0.5 spec is COMPOSED FROM five files

The LOCKED state of C16 v0.5 is the union of:

1. **`spec_C16_v0_1_PROPOSED.md`** (476 lines) — foundational v0.1
2. **`spec_C16_v0_2_PROPOSED_DELTA.md`** (500 lines) — 10 amendments from critique walk #1
3. **`spec_C16_v0_3_PROPOSED_DELTA.md`** (448 lines) — 8 amendments from critique walk #2
4. **`spec_C16_v0_4_PROPOSED_DELTA.md`** (758 lines) — 12 amendments from critique walk #3 + Item 13 META routing
5. **`spec_C16_v0_5_PROPOSED_DELTA.md`** (439 lines) — 6 constrained amendments from critique walk #4

These five files together constitute the LOCKED specification. **To read the locked spec correctly, read in order v0.1 → v0.2 → v0.3 → v0.4 → v0.5.** Where any later delta amends a section, the later delta wins.

A composed canonical document (consolidating all 5 files into one) is NOT included in this LOCK by design. Per Rule 8 and the C13/C14/C15 LOCK convention, layered deltas are sufficient as the authoritative state at LOCK; composed canonical doc is a v1.x deliverable (per `B-C16-COMPOSED-CANONICAL-DOC` filed below).

---

## v0.5 LOCK summary — what is binding

### Public API contract (binding):
- `render_drawings(...)` returns `SuccessfulDrawingRender | FailedDrawingRender`
- `render_drawings_batch(...)` returns `DrawingRenderBatchResult`
- Output type: `DualDrawingBundle` with shared `FloorGeometry` core (v0.2 A3) referenced by both Working and Permit drawing models
- Dual-frame coordinates: `LocalBuildingFrame` (building-relative, right-handed Cartesian, +X via deterministic orientation hierarchy per v0.4 A4) + `GeospatialReference` metadata
- `SelectionResult` upstream contract (v0.3 A1 split into `SelectionReplayIdentity` + `SelectionAuditMetadata`)
- Jurisdiction profile: TNCDBR 2019 only at v1; `declared_domain_scope` enum constrained to residential_v1 / small_commercial_v1 / mixed_use_v1 (v0.5 A4)

### Invariants (binding):
- R1-R18 from v0.1 § 2
- R19-R34 from v0.2/v0.3/v0.4 (with sub-clauses)
- R26b (v0.5 A2 — schema descriptor digest)
- R28d (v0.5 A1 — 64-bit overflow detection)
- R29d (v0.5 A5 — orientation lock plausibility)
- R30d (v0.5 A6 — overlay validation contract)
- R31a/R31b (v0.5 A4 — hard ceilings + domain scope enforcement)
- R34e (v0.5 A3 — epsilon boundary inclusion semantics)

### Determinism (binding):
- Inv R7 byte-equal replay via canonical_replay_signature
- Separate presentation_signature for L1/L2 cache tier separation (v0.4 A9)
- semantic_identity_hash stable within same identity_generation (v0.4 A10)
- Canonical JSON serialization rules pinned (v0.4 A7 + v0.5 A2 schema digest)
- Epsilon policy (R34 + R34e) — coordinates 1mm, ratios 1e-4, angles 1e-6 deg

### Provenance discipline (binding):
- `AuthorityKind` enum: UPSTREAM_AUTHORITATIVE / LOCALLY_DERIVED / CROSS_CHECK_VERIFICATION (v0.2 A5)
- `legal_completeness` derives ONLY from UPSTREAM_AUTHORITATIVE values (v0.3 A5 — R25)
- `LegalCompleteness` ⊥ `ReadabilityStatus` split (v0.4 A5)
- Overlay validation contract surface (v0.5 A6) separates semantic completeness from visual visibility

### LOCK-mandatory backlog (must close before C16 v1.0 LOCK) — 19 items

**2 are v1.0-LOCK-BLOCKING:**
1. **B-C16-DECOMPOSITION-DECISION-LOCK** → **ADJUDICATED at S47**: DEFER to v2.x. Keep C16 unified at v1.0. (See B-C16-DECOMPOSITION-DEFERRED-REVISIT-CONDITIONS below for revisit triggers.)
2. **B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK** — bind IS 962:1967 references (text heights, sheet sizes, pen weights, title block dimensions). v1.0-LOCK-BLOCKING.

**17 LOCK-mandatory (non-blocking):**
3-19. See `04_backlog/v0_2_backlog_S47.md` § C16 for full list.

### Decomposition adjudication record

**Decision (S47, Ramalingam delegation): DEFER decomposition to v2.x. Keep C16 unified at v1.0.**

**Reasoning:**
- Industry precedent (Parasolid, ACIS, OpenCascade) is platform-grade; BuildemUp serves ONE pipeline for residential drawings — scope mismatch
- Internal seams already exist (FloorGeometry, AttestedValue, ElementIdentity, CanonicalTransform2D) — these ARE the decomposition, just inside one module
- C13/C14 LOCK precedent treats components as units; splitting C16 alone breaks pattern
- 19 → 22 component overhead significant for solo development
- Pattern E avoidance: decomposing pre-implementation is premature optimization

**Revisit conditions (filed as B-C16-DECOMPOSITION-DEFERRED-REVISIT-CONDITIONS):**
- BuildemUp expands beyond residential to campus/infrastructure scale
- Third-party renderers want to consume C16 outputs independently
- C16 implementation reveals concrete seams that benefit from explicit separation
- Multi-jurisdiction expansion forces compliance layer separation

### Cumulative backlog at LOCK: 49 items
- 19 LOCK-mandatory (2 BLOCKING for v1.0)
- 27 post-LOCK / v1.x
- 3 routed amendment hints

Per the C13 v1.0 LOCK precedent, v0.6+ amendments during implementation refine the SKETCH toward eventual v1.0 LOCK.

---

## Critique walks completed before LOCK — 5 walks

| Walk | Target | VALID-amendment | VALID-deferred | PARTIAL | MISFRAMED |
|---|---|---|---|---|---|
| #1 | v0.1 → v0.2 | 10 | 1 | 2 | 0 |
| #2 | v0.2 → v0.3 | 8 | 4 | 1 | 0 |
| #3 | v0.3 → v0.4 | 12 | 0 | 0 | 0 |
| #4 | v0.4 → v0.5 | 6 | 6 | 0 | 0 |
| #5 | v0.5 (final) | 0 | 10 | 0 | 0 |

The trajectory from walk #1 to walk #5 shows clear maturity progression — walks #4 and #5 confirmed remaining concerns are operational/governance, not architectural flaws. The reviewer at walk #5 Item 14 explicitly recommended stopping iteration and proceeding to implementation.

## 2 self-introduced determinism bugs (caught + fixed)

1. **v0.2 A1 timestamp in canonical signature** — fixed in v0.3 A1 via replay_identity/audit_metadata split
2. **v0.3 A4 "longest wall" orientation flip risk** — fixed in v0.4 A4 via deterministic hierarchy + lex-ASC tiebreak

Pattern noted for future Claudes: field-additions to canonical replay-identity warrant explicit determinism audit before submitting any delta.

## Implementation pointers for next Claude

**C16 build is NOT immediate next priority. C15 build is.** See `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` for build sequencing.

When C16 build does begin (likely S49 or later):
- Follow C13/C14/C15 multi-sub-session pattern
- Phases α-ζ map to the 6 spec phases (envelope / scheduling / working assembly / permit assembly / attestation packaging / bundle assembly)
- Mandatory PBT layer ≥ 15 tests per v0.1 § 7 (do NOT skip this as C14 did)
- Resolve `B-C16-DECOMPOSITION-DECISION-LOCK` as DEFERRED (already adjudicated at this S47 LOCK)
- Close `B-C16-RENDERER-CONFORMANCE-CONTRACT-LOCK` with IS 962:1967 binding values BEFORE v1.0 LOCK

---

## LOCK chain

v0.1 PROPOSED (S47) → v0.2 PROPOSED-DELTA (S47) → v0.3 PROPOSED-DELTA (S47) → v0.4 PROPOSED-DELTA (S47) → v0.5 PROPOSED-DELTA (S47) → **v0.5 LOCKED SKETCH (Ramalingam, S47)**

All five PROPOSED stages happened in a single session (S47) following spec-first discipline and 5 critique walks. Build will commence post-C15.
