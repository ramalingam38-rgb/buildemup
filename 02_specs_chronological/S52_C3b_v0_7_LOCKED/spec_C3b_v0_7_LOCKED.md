# C3b v0.7 LOCKED — Spec amendment over v0.6
**Session:** S52 (same session as v0.4→v0.5→v0.6→v0.7)
**Predecessor:** v0.6 LOCKED (S52, delegated)
**Adjudication mode:** LOCK delegated to Claude by Ramalingam directive
  ("do the valid patches only and Lock it")
**Lock authority:** Rule 8 LOCK-by-explicit-delegation

---

## § 0 — Honest scoping note (Rule 11)

Round 3 produced 3 v1.x candidates. Of those, only 1 is genuinely
delegation-safe:

| Candidate | Effort | Risk | v0.7 status |
|---|---|---|---|
| B-C3B-COMPATIBILITY-CAUSAL-GRAPH | S | Low | **PATCHED in v0.7** |
| B-C3B-EXPERIENTIAL-CONTINUITY-ISOVIST-COMPUTATION | M-L | High | **DEFERRED** |
| B-C3B-GENERATIONAL-BOUNDARY-DESIGN | XL | High | **DEFERRED (v2)** |

**Why isovist is deferred:** Round 3 backlog notes the work needs a
"deterministic sampling strategy" + geometry library integration.
Doing this correctly requires Ramalingam's input on sample-point
selection (because the choice IS the R6 contract — different
sampling = different replay sigs). Doing it under delegation
risks subtly wrong determinism that the test suite wouldn't catch.

**Why generational boundary is deferred:** Round 3 backlog explicitly
marks this v2 with "operational criteria pending."

**Net v0.7 yield:** 1 patch (C1 below). Smaller than v0.6 but cleaner
than shipping risky work under delegation.

---

## § 1 — New v1.0 amendments (1 total)

### C1 — Compatibility causal graph
**Was:** B-C3B-COMPATIBILITY-CAUSAL-GRAPH (Round 3 Pt 34)

**Problem:** CompatibilityAssertion currently carries only a free-form
`advisory_note`. When a tweak conflicts with several other systems
(e.g., bathroom relocation affecting riser stack + beam routing +
parking headroom), the user sees "conflict detected" without an
intuitive understanding of WHICH systems propagate.

**Spec change:** Add to CompatibilityAssertion an Optional structured
propagation chain.

**New dataclass (in schema.py):**
```python
@dataclass(frozen=True)
class PropagationEdge:
    """One link in a causal propagation chain. Captures that a
    change to from_system propagates to to_system via a structural
    or systemic relationship.

    relationship_kind values (Literal, enforced):
      - "shares_wet_zone_chase"      (bathroom <-> bathroom)
      - "shares_structural_bay"      (any -> any)
      - "shares_riser_stack"         (kitchen <-> bathroom)
      - "shares_load_path"           (column-touching)
      - "shares_circulation_node"    (door-adjacent)
      - "shares_external_envelope"   (external wall change)
      - "shares_vertical_alignment"  (multi-floor)
    """
    from_system:        str
    to_system:          str
    relationship_kind:  Literal[...]    # 7 values above
    advisory_note:      str             # R2 lint-clean, ≤ 200 chars
```

**Spec change to CompatibilityAssertion:**
```python
@dataclass(frozen=True)
class CompatibilityAssertion:
    ...existing fields preserved verbatim...
    propagation_chain: Optional[tuple[PropagationEdge, ...]] = None
```

**Backward compatibility:** Optional, defaults None. All existing
callers that don't populate it get exact v0.6 behavior.

**Severity routing:** Unchanged. Propagation chain is informational
metadata; the conflict/compatible result is computed identically.

**R6 byte-equal replay:** Preserved. The chain is deterministic
output of the same severity-context computation. When populated,
included in canonical_replay_signature (this is genuine state, not
strategic advisory like R17).

**Invariant impact:** No new invariant. The existing R15
compatibility-assertion invariants apply unchanged.

---

## § 2 — New invariants

None. C1 is additive metadata without new invariants.

---

## § 3 — Backward compatibility statement

v0.6 → v0.7:
- CompatibilityAssertion gains 1 Optional field (propagation_chain)
- PropagationEdge is a new dataclass (no existing callers affected)

**C3B_SESSION_SCHEMA_VERSION bumps from 4 → 5.**
v0.6 sessions need migration (v0.6→v0.7 helper deferred to v1.x).

---

## § 4 — Test parity requirements

C1: 7 tests
  - PropagationEdge construction + relationship_kind enum validation
  - PropagationEdge advisory_note lint discipline (R2)
  - PropagationEdge advisory_note length ceiling
  - CompatibilityAssertion with chain=None (v0.6 behavior preserved)
  - CompatibilityAssertion with non-empty chain
  - Persistence roundtrip (chain survives save/load)
  - canonical_replay_signature includes chain when populated

Foundation: 2 tests (version + schema bump)

**Target additions:** ~9 new tests. Expected total: 450 + 9 ≈ 459.

---

## § 5 — What stays in backlog after v0.7

- B-C3B-EXPERIENTIAL-CONTINUITY-ISOVIST-COMPUTATION (v1.x — needs
  Ramalingam input on deterministic sampling strategy)
- B-C3B-GENERATIONAL-BOUNDARY-DESIGN (v2 — operational criteria
  pending)
- All other Round 1 / Round 2 / Round 3 deferred items unchanged
  from v0.6 state

---

## § 6 — LOCK declaration

**v0.7 LOCKED by Ramalingam directive S52** ("do the valid patches
only and Lock it"). Audit trail preserved.

Implementation: build C1 only, regenerate consolidated file as v0.7,
prepare handoff bundle on confirmation. Per Rule 10.7, first response
to "give me the handoff" is the status block + three-check plan, NOT
bundle assembly — confirmation gates bundle work.
