# C12 — SPEC v1.0 LOCKED

**Component**: 12 (Multi-Floor Placement & Vertical Alignment Engine)

**Status**: **v1.0 LOCKED** by Ramalingam directive S43: *"Lock it and start coding"* (post Walk #6).

**Lock authority**: Ramalingam alone, per Rule 8. Citation: explicit "Lock it" signal received S43 after 5 critique walks (Walks #2-#6) converged on LOCK candidacy.

**Composition**: v1.0 = v0.1 PROPOSED + v0.2 amendments + v0.3 amendments + v0.4 amendments + v0.5 amendments + v0.6 amendments. The amendment docs (`spec_C12_v0_{1..6}*.md`) are the authoritative composed normative document. This LOCKED marker is the immutability seal; no further amendments to v1.0 — future changes require v1.1 PROPOSED → v1.1 LOCKED cycle.

---

## Lock summary

| Property | Value |
|---|---|
| Public types | 6 |
| Failure types | 11 |
| Configuration fields | 9 |
| Invariants | 13 (Inv 1-13) |
| Sub-phases | 6 (Phase 0, 0b, 1, 1b, 2, 3) |
| Open questions | 1 (Q-6, backlog-only) |
| Backlog items | 41 |
| Weighted complexity | 43.5 / 100 |
| Test surface mandate | ~150 (120 example + 25-30 PBT, invariant-grounded) |

---

## Cross-component dependencies (LOCKED + coded at S43)

- **B-C8-CORRIDOR-ZONE-CONTRACT** v0.1 LOCKED + coded + 11 tests passing
- **B-C9-ADJACENCY-HINTS** v0.1 LOCKED + coded + 15 tests passing
- **B-C8-SCHEMA-VERSION-CONSTANT** (routed thin amendment, coded at S43)
- **B-C9-SCHEMA-VERSION-CONSTANT** (routed thin amendment, coded at S43)

---

## Build plan (S44+)

1. Code routed amendments (C8 + C9 schema version constants) — trivial, this session.
2. Code C12 v1 implementation — ~25 production files mirroring C11b structure.
3. Test surface: ≥25 PBT (invariant-grounded) + ~120 example-based + ~10 integration = ~150 tests.
4. Target: 3059 baseline → ~3211 (3059 + 4 amendment tests + ~150 C12 tests).

---

## Backlog reservoir (41 items)

Filed across 5 critique walks with explicit triggers. NOT v1 LOCK blockers; ship with v1 and fire on trigger conditions. See individual `spec_C12_v0_*_PROPOSED_AMENDMENTS.md` § 0.4 sections for full IDs, descriptions, origins, triggers, and effort estimates.

Highlights: B-C12-CSP-PLACEMENT (HIGH priority, irregular envelopes), B-C12-COUPLED-MF-PLACEMENT (HIGH, joint multi-floor solving), B-C12-IRREGULAR-ENVELOPES (HIGH commercial), B-C12-COMPONENT-SPLIT-V2 (architectural debt), B-C12-PROPERTY-FUZZING (PROMOTED to v1 build via v0.5-A1, refined v0.6-A1).

---

**End of v1.0 LOCKED marker.** Build session begins.
