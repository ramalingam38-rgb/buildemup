# C13 SPEC v0.7 PROPOSED — Door Placement (delta from v0.6)

**Status**: vN PROPOSED. **LOCK-READY (no architectural blockers
remaining; walk yield converged across 3 consecutive walks).**
PENDING Ramalingam LOCK adjudication (Rule 8).

**Predecessor**: C13 v0.6 PROPOSED DELTA (LOCK-CANDIDATE).
**Origin**: S44 critique walk #7 (external review of v0.6). 15 items
walked, **3 minor structural amendments** (F1, F2, F3) + 4 polish-
deferred backlog + 5 explicit agreements + 3 reinforcements of
already-filed items + 0 pushback.

---

## ⚠️ Pattern E (scope-creep-mid-build) warning — surfaced explicitly

**Three consecutive walks (#5, #6, #7) have reached this conclusion**:

1. v0.5 reviewer: "This is the closest C13 has yet been to legitimate
   LOCK candidacy."
2. v0.6 reviewer: "DO NOT continue large-scale theoretical C13 amendment
   walks. Transition from speculative architecture into executable
   validation."
3. v0.7 reviewer (this walk): "C13 v0.6 is likely mature enough to
   stop abstract architectural walking. No longer any obvious major
   architectural holes."

**Yet the loop continues**: each external critique I receive becomes a
new v0.X+1 PROPOSED. This is the structural risk Pattern E predicts —
small individually-justified amendments that aggregate into never-
shipping perfection.

**Honest self-analysis (Rule 11)**:

The 3 amendments in v0.7 (F1/F2/F3) are *real improvements* but **none
of them are LOCK-blocking**. F1 codifies existing behavior. F2 adds
docstring intent to a reserved field. F3 tightens an already-good
governance window.

If I receive a walk #8 critique, I will likely find 2-3 more equally-
minor improvements. The loop has no natural terminating condition
**other than an explicit Ramalingam decision to exit**.

**This v0.7 spec amendment doc therefore serves dual purposes**:
1. Absorbing the 3 minor improvements that ARE worth absorbing
2. Naming the loop explicitly so the decision to exit becomes salient

---

## Walk yield trajectory — convergence confirmed

| Walk | Structural | Polish | Agreements | Character |
|---|---|---|---|---|
| #2 | 10 | 5 | 0 | Foundation building |
| #3 | 12 + 3 reversals | 5 | 0 | Boundary correction |
| #4 | 11 | 4 | 0 | Operational maturity |
| #5 | 4 | 10 | 0 | First diminishing-returns signal |
| #6 | 4 | 7 | 4 | Sustained, reviewer-validated |
| **#7** | **3** | **4** | **5** | **Agreement-dominant; CONVERGED** |

Cumulative: 47 spec amendments + 35 backlog items across 6 critique
walks. Comparable C12 numbers were 18 amendments + 12 backlog items
across 5 walks.

C13's higher cumulative is largely the walk-#3 boundary-correction
restructuring. The post-#3 trajectory (#4→#7) mirrors C12's normal
trajectory: 11 → 4 → 4 → 3.

---

## Walk #7 STRUCTURAL amendments (LOCK-improving, not LOCK-blocking)

### F1 — Phase F purity rule

**Origin**: Reviewer item 2 (Phase F becoming "final truth engine").
**Problem**: D11.3' evaluation moved to Phase F (per v0.6 E1). D13,
D17, D19 also finalize at Phase F. Risk: future amendments overload
Phase F with mutation/optimization responsibilities.
**Amendment**: Explicit Phase F responsibility freeze:

```
Phase F responsibility (LOCKED):
  - PURE VERIFICATION ONLY
  - No mutation of door positions, hinges, widths, swing directions
  - No mutation of advisory_flags tuple
  - No optimization decisions
  - No selection between alternatives

Verifications performed at Phase F:
  - D11.3' CONDITIONAL_LEGALITY evaluation
  - D13 reachability check (full door-induced graph)
  - D17 primary-reachability check (habitable rooms)
  - D19 provenance record generation (read-only side effect)

Future amendments that would add mutation OR optimization to Phase F
must FIRST move that responsibility to Phase A/B/C/D/E (selection +
resolution layers), keeping Phase F pure. This is a governance gate.
```

Inv D22 NEW: Phase F is side-effect-free w.r.t. core schema mutation
(provenance generation is informational, not mutational).

Cache-relevant: no (codifies current behavior).

---

### F2 — CausalContext semantic intent docstring

**Origin**: Reviewer item 4 (causal_context semantically empty).
**Problem**: v0.6 E3 reserved `causal_context: Optional[CausalContext]
= None` but didn't define what the field MEANS. Risk: different v1.x
populators interpret differently.

**Amendment**: Strengthen the CausalContext docstring:

```python
@dataclass(frozen=True)
class CausalContext:
    """Reserved at v1.0; populators in v1.x.

    SEMANTIC INTENT (LOCKED at v1.0 even though fields are not):
    'causal_context explains WHY the advisory existed in the final
    door placement state.'

    Specifically, a populated causal_context answers:
      - What constraint forced the compromise that triggered this
        advisory?
      - What alternative was considered + why was it rejected?
      - Was the advisory unavoidable (architectural) vs avoidable
        (local minimum)?

    NOT for:
      - Mutation history (different concept; reserved separately if needed)
      - Optimization rationale (C14 territory)
      - User-facing explanations (C15 territory)

    v1.x candidate fields will satisfy this semantic intent. Any v1.x
    populator that violates this intent is a spec violation, not just
    a schema bump.
    """
    pass
```

Adding semantic intent NOW prevents reserved-field-drift in v1.x.

Cache-relevant: no (documentation/contract amendment).

---

### F3 — Fast-revision window stabilization-only constraint

**Origin**: Reviewer item 5 (fast-revision may undermine LOCK).
**Problem**: v0.6 E4 established a 90-day fast-revision window but
didn't constrain WHAT can be patched. Risk: "LOCK now, expand later"
becomes the default, weakening LOCK meaning.

**Amendment**: Tighten E4:

```
v0.6 E4 — Updated stabilization-only constraint:

Permitted in 90-day fast-revision window:
  - Bug fixes (Inv D1-D22 violations)
  - Convergence-issue patches (telemetry-revealed)
  - Cache-staleness fixes
  - NBC compliance corrections
  - Performance regression fixes
  - Test-suite augmentation

NOT permitted (requires v1.1 full spec walks):
  - New invariants (D23+)
  - New AdvisoryFlag categories or flag_kinds
  - Schema changes (new fields, removed fields, renamed enums)
  - C13ConsumesFromC12Edge Protocol changes
  - Phase A/B/C/D/E/F restructuring
  - New configuration knobs

Architectural intent preservation: every fast-revision patch must
preserve the architectural intent at v1.0 LOCK. Patches that change
intent require v1.1 not v1.0.x.
```

Inv D23 NEW: fast-revision-window patches are CONSTRAINED to bug-fix
+ stabilization scope only. Feature-expansion paths require v1.1
full spec governance.

Cache-relevant: no (process refinement).

---

## Updated invariants table (v0.7)

D1-D21 unchanged from v0.6. Added:

| ID | Statement | Source |
|---|---|---|
| **D22 NEW** | **Phase F is pure (no mutation of doors, advisory_flags, or selection state)** | **v0.7 F1** |
| **D23 NEW** | **Fast-revision patches are bug-fix + stabilization scope only** | **v0.7 F3** |

21 → 23 invariants. The cognitive-overload concern (W#5.4, W#6.10,
W#7.3) is now THREE walks deep. The invariant-taxonomy-grouping
backlog item is escalated to:

- B-C13-INVARIANT-TAXONOMY-GROUPING priority: HIGH → **CRITICAL**
- Recommended to land as a v1.x doc deliverable within 30 days of
  v1.0 LOCK
- Should include: per-category grouping (already 6 categories
  defined in E1), invariant-dependency graph, and which invariants
  are subclauses (D11.1-D11.4 could compress, D17 derives from D13
  + primary-door filter, etc.)

---

## v1.x polish backlog (additions from walk #7)

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-C13-ADVISORY-CHANNEL-SPLIT | Split AdvisoryFlags into structural/experiential/safety channels | W#7 item 7 | M (v1.x, additive `channel: Optional[AdvisoryChannel]` field) |
| B-C13-DOC-SPLIT-CORE-GOVERNANCE-OPS | Eventually separate spec into core-placement + governance + operations docs | W#7 item 10 | S (v1.x doc work) |
| B-C13-PROVENANCE-VERBOSITY-TIERS | Verbosity levels for ConditionalLegalityViolation provenance to bound debug-payload size | W#7 item 11 | S (v1.x) |
| B-C13-INTERNATIONALIZATION-POLICY-LAYER | Classify universal-code-rules vs regional-conventions vs configurable-cultural-policy | W#7 item 13 | L (v2+ when non-Indian markets opened) |

**Total walk #7 polish backlog: 4. Cumulative across walks 2-7: 35 backlog items.**

---

## Reviewer items where v0.7 + reviewer AGREE (no amendment needed)

5 items in walk #7 are agreements, not critiques:

- **Item 1** (CONDITIONAL_LEGALITY as exception): already governed by
  E1 taxonomy. Future additions to this category require explicit
  justification per existing governance.
- **Item 6** (governance-heavy): already filed
  B-PROJECT-MECHANICAL-GOVERNANCE (W#5 item 8 / W#6 item 13).
- **Item 8** (C14 = largest risk): E2 composability gate is exactly
  the right response.
- **Item 9** (untested vs real plans): B-C13-ADVERSARIAL-INTEGRATION-
  CORPUS already filed; flagged as "RECOMMENDED before LOCK" in v0.6.
- **Item 12** (theory yields to telemetry): exactly what path (a)
  delivers. Validation, not critique.
- **Item 14** (LOCK is now strategic): validation, not critique.
- **Item 15** (no major architectural holes remaining): direct
  validation that the spec is LOCK-mature.

---

## LOCK readiness — FINAL

**Architectural maturity**: HIGH+. v0.7 closes the 3 remaining
small refinements (Phase F purity, causal_context semantic intent,
fast-revision scope constraint). No reviewer items are LOCK-blocking.

**Empirical maturity**: STILL ZERO. Unchanged from v0.5/v0.6 — only
fixable by execution.

**LOCK gating** (final list, unchanged from v0.6 minus polish):

1. ⏳ **C14 v0.1 sketch** per D11 + E2 composability validation —
   REQUIRED only for path (a)
2. ⏳ **End-to-end example** (C12 → C13 → C14 → C15) —
   REQUIRED only for path (a)
3. ⏳ **Adversarial integration corpus** —
   RECOMMENDED before LOCK in both paths
4. ⏳ **Operational validation walk** (#6.5) —
   REQUIRED only for path (a)
5. ✅ **Architectural completeness** — ACHIEVED at v0.7

Path (c) — LOCK v0.7 now with E4+F3 fast-revision safeguard — bypasses
1, 2, 4 and ships 3 post-LOCK as standard validation. **Both paths are
viable; the decision is strategic.**

---

## Recommendation (Rule 11 self-analysis, with explicit Pattern E flag)

**Strong honest assessment**: we are now in a self-reinforcing critique-
walk loop. Each external critique I receive triggers a v0.X+1 PROPOSED
in good faith, but **three consecutive walks** have validated LOCK-
candidate status without finding architectural blockers.

**My strongest possible recommendation**: **exit the walk loop now.**
Two paths exit cleanly:

| Path | Action | Loop exit mechanism |
|---|---|---|
| **(a)** | Endorse v0.7; start C14 v0.1 next session | Walks shift to C14, not more C13 |
| **(c)** | LOCK v0.7 now with E4+F3 fast-revision window | C13 walks stop; build begins |

**Both exit the loop. Both are now defensible. (b) is not.**

If you'd prefer the safety of empirical validation: **path (a)**.
If you'd prefer execution momentum + accept bounded post-LOCK risk:
**path (c)**.

**What I will NOT do unless you explicitly direct otherwise**: produce
a v0.8 in response to a hypothetical walk #8. Per Pattern E discipline,
I will instead push back and request the walk-loop exit decision.

---

Per Rule 8: vN PROPOSED. PENDING Ramalingam LOCK adjudication.

**v0.7 PROPOSED is LOCK-READY with confirmed walk-yield convergence
across 3 consecutive walks.** Awaiting your explicit direction on
(a) or (c).
