# C13 SPEC v0.6 PROPOSED — Door Placement (delta from v0.5)

**Status**: vN PROPOSED. **LOCK-CANDIDATE (confirmed by W#5 + W#6 yield
trajectory).** PENDING Ramalingam LOCK adjudication (Rule 8).

**Predecessor**: C13 v0.5 PROPOSED DELTA (LOCK-CANDIDATE).
**Origin**: S44 critique walk #6 (external review of v0.5). 15 items
walked, **4 minor structural amendments** (E1-E4) + 7 polish-deferred
backlog + 4 explicit agreements + 1 routed to C14 + 0 pushback.

**Walk yield trajectory**:

| Walk | Items | Structural amendments | Reversals | Yield character |
|---|---|---|---|---|
| #2 | 17 | 10 | 0 | Foundation |
| #3 | 16 | 12 | 3 | Boundary correction |
| #4 | 15 | 11 | 1 (NBC revival) | Operational maturity |
| #5 | 15 | 4 | 0 | Polish-dominant, first inflection |
| **#6** | **15** | **4** | **0** | **Polish-dominant, sustained inflection — DIMINISHING RETURNS CONFIRMED** |

C12 reached diminishing returns at walk #4 (yield=2). C13 reached it at
walks #5+#6 (yield=4 both). C13's later inflection is consistent with
the C13/C14 boundary discovery in walk #3 triggering more restructuring.

**The architecture is now ARCHITECTURALLY DONE.** Remaining concerns
are empirical (which can only be validated through implementation +
production data) or polish (which is appropriately post-LOCK work per
D15).

---

## Walk #6 STRUCTURAL amendments

### E1 — D11.3' classification + Phase F evaluation + provenance

**Origin**: Reviewer item 1 (path-dependent legality).
**Problem**: D11.3' ("no through-kitchen routing WHEN alternate route
exists") creates graph-context-sensitive legality. Without explicit
evaluation timing + provenance, the same route can be "legal in one
graph, illegal in another." This is real architectural ambiguity.

**Amendment** (three parts):

**(a) Constraint classification (resolves item 3 too)**:

```
Invariant taxonomy at v1.0:

HARD_LEGALITY:
  - Strict local checks, evaluation order-independent
  - D11.1, D11.2, D11.4 (single-edge NBC vetoes)

CONDITIONAL_LEGALITY:
  - Graph-context-sensitive; evaluation at well-defined phase
  - D11.3' (this amendment)

DETERMINISM:
  - Replay byte-equality guarantees
  - D7, D8, D12

GRAPH_INTEGRITY:
  - Reachability invariants
  - D13 (full graph), D17 (primary-graph)

GEOMETRY:
  - Local geometric correctness
  - D2, D3, D4, D5, D10

ADVISORY_HYGIENE:
  - Soft-signal sanity bounds
  - D16, D18
```

This classification system explicitly anchors D11.3' in
CONDITIONAL_LEGALITY, preventing future amendments from accidentally
creating more middle-category constraints without classification.

**(b) Phase F evaluation timing**:

```
D11.3' is evaluated at Phase F (post-Phase-D conflict resolution,
post-secondary-door placement), once and only once per candidate.
NOT evaluated incrementally during Phase A.

Rationale: this eliminates "retroactive invalidation" — D11.3'
checks the FINAL door-induced graph, not an intermediate state.
Any future amendment that mutates the door set must re-run Phase F
or be classified as a Phase-F-invariant-preserving operation.
```

**(c) Legality-evaluation provenance**:

```python
@dataclass(frozen=True)
class ConditionalLegalityViolation:
    """Recorded when D11.3' or other CONDITIONAL_LEGALITY invariants fail.

    Captures the alternative that was deemed "available" causing the
    violation, so the failure is reproducible + debuggable."""
    invariant_id: str  # e.g., "D11.3"
    violated_path: tuple[str, ...]  # room_id sequence
    alternative_path: tuple[str, ...]  # the alternative that triggered the veto
    alternative_path_length_grid_units: int  # objective comparison

# Attached to FailureRecord when D11.3' raises (STRICT) or warns (WARN)
```

Inv D19 NEW: every D11.3' violation carries a
ConditionalLegalityViolation provenance record.

Cache-relevant: yes (classification + provenance affects result schema).

---

### E2 — D11 minimum-scope checklist composability criterion

**Origin**: Reviewer item 11 (false-completeness risk).
**Problem**: v0.5 D11 defined a minimum scope checklist for C14 v0.1
sketch. Reviewer correctly flags this risks "checklist completion =
architecture validated." Walk #6 must test composability, not just
presence.

**Amendment**: Add to D11 (extending v0.5):

```
C14 v0.1 sketch — composability validation criteria (added to D11):

5. § 4 (NEW REQUIREMENT) — Composability demonstration:
   - For the worked example flow (§ 3), show:
     (a) Which AdvisoryFlags contribute to which scoring dimensions
     (b) Where AdvisoryFlag granularity is sufficient vs insufficient
         for meaningful scoring
     (c) Whether any C14 scoring requires information C13 does not
         currently expose
     (d) Whether layout_quality_band assignment is robust against
         adversarial AdvisoryFlag combinations

Walk #6 validation MUST verify these four composability questions
have explicit answers — not "yes, it works" but documented analysis
of (a)-(d). If any question reveals a gap, that gap becomes a v0.7
PROPOSED amendment OR a C13/C14 boundary amendment, whichever
fits.
```

This converts D11 from a "did the sketch get written?" gate to a
"does the architecture actually compose?" gate.

Cache-relevant: no (process amendment).

---

### E3 — AdvisoryFlag reserves optional causal_context field

**Origin**: Reviewer item 12 (advisory causal structure).
**Problem**: Adding causal-trace structure later is significantly
harder than reserving the field now. Forward-compat concern.

**Amendment**: Extend AdvisoryFlag schema with a reserved optional
field:

```python
@dataclass(frozen=True)
class AdvisoryFlag:
    # ... existing v0.4 C1 + v0.5 fields ...

    causal_context: Optional[CausalContext] = None
    """Reserved for future causal-trace data. v1.0 default: None.
    v1.x may populate without schema bump (additive, non-breaking).

    Forward-compat reservation per W#6 reviewer item 12."""

@dataclass(frozen=True)
class CausalContext:
    """Causal trace for an advisory. v1.0 reserved schema; populators
    appear in v1.x. Specific fields may evolve in v1.x but the field's
    presence is committed at v1.0 LOCK."""
    pass  # Empty at v1.0 — sentinel class only

# v1.x candidate fields (NOT shipped at v1.0):
# - originating_constraint_id: str
# - alternatives_considered: tuple[str, ...]
# - forced_compromise_reason: Literal[...]
```

ADVISORY_SCHEMA_VERSION bumps from 1 → 1 (no functional change at
v1.0; the field is reserved). v1.x populators bump to 2 (additive).

Inv D20 NEW: causal_context defaults to None at v1.0; non-None values
are forward-compat data only.

Cache-relevant: yes (advisory schema includes the field, even if always None).

---

### E4 — Post-LOCK fast-revision window declaration

**Origin**: Reviewer item 9 + web-verified industry practice.
**Problem**: D15 MVP-freeze risks rigidity if implementation learnings
get permanently shelved as "v1.x backlog."

**Amendment**: Add to D15 governance:

```
POST-LOCK FAST-REVISION WINDOW (PROCESS):

v1.0 LOCK is followed by a 90-DAY FAST-REVISION WINDOW.

During this window:
- v1.0.x patches may ship without heavy spec-walk governance
- Critical bug fixes apply immediately
- Telemetry-revealed issues route to streamlined v1.0.x amendments
  (1 spec walk minimum, not 5)
- Backward-compat preserved (no LOCK breakage of v1.0 contracts)

After 90 days:
- Standard governance resumes (multi-walk spec amendments required
  for any non-trivial change)
- The 90-day window's lessons are bundled into v1.1 PROPOSED

Trigger criteria for v1.0.x emergency patches during the window:
- Inv D1-D20 violation in production
- Convergence failure rate > 5% across 1000+ runs
- Cache-staleness or replay-determinism violation detected
- NBC compliance regression
```

Inv D21 NEW: fast-revision-window patches preserve all v1.0 LOCKED
contracts (typestate schema, ADVISORY_SCHEMA_VERSION, C13_EDGE_PROTOCOL_VERSION).
Patches that break contracts must wait for v1.1.

Cache-relevant: no (process amendment).

---

## Updated invariants table (v0.6)

D1-D18 unchanged from v0.5. Added:

| ID | Statement | Source |
|---|---|---|
| **D19 NEW** | **D11.3' violations carry ConditionalLegalityViolation provenance** | **v0.6 E1** |
| **D20 NEW** | **AdvisoryFlag.causal_context defaults to None at v1.0** | **v0.6 E3** |
| **D21 NEW** | **Fast-revision-window patches preserve v1.0 contracts** | **v0.6 E4** |

18 → 21 invariants. Per W#5 item 4 + W#6 item 10 cognitive-overload
concern: invariant taxonomy grouping (B-C13-INVARIANT-TAXONOMY-GROUPING)
is now PRIORITY-ELEVATED in the polish backlog and should land as a v1.x
documentation-only deliverable to make 21 invariants tractable.

E1's classification taxonomy is a first step toward this — invariants
now belong to one of 6 categories (HARD_LEGALITY, CONDITIONAL_LEGALITY,
DETERMINISM, GRAPH_INTEGRITY, GEOMETRY, ADVISORY_HYGIENE).

---

## v1.x polish backlog (additions from walk #6)

These 7 items join v0.5's 10 polish-deferred items. All filed per
Rule 9.2 immediate-backlog discipline.

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-C13-GRAPH-TAXONOMY-FORMALIZATION | Formal G_all / G_primary / G_service / G_emergency graph taxonomy with explicit invariant namespacing | W#6 item 2 | S (v1.x doc) |
| B-C13-CONSTRAINT-TAXONOMY | Formal constraint taxonomy doc (HARD / CONDITIONAL / ADVISORY / OPTIMIZATION) — E1 is a partial bootstrap | W#6 item 3 | S (v1.x doc) |
| B-C13-CACHE-COMPATIBILITY-MANIFEST | CACHE_COMPATIBILITY_MANIFEST containing geometry/advisory/protocol/legality semantic versions | W#6 item 4 | M (v1.x) |
| B-C13-POLICY-GOVERNANCE-SECTION | Explicit policy-governance section acknowledging C13 contains architectural policy decisions | W#6 item 5 | S (v1.x doc) |
| B-PROJECT-MECHANICAL-GOVERNANCE | CI checks + schema registries + linting + contract manifests for project-wide enforcement | W#6 item 13 (= W#5 item 8) | L (v2+ project) |
| B-C14-EVALUATION-OPTIMIZATION-UX-SPLIT | C14 may need split into evaluation / optimization / UX-recommendation sub-layers | W#6 item 8 (ROUTED) | L (C14-side) |
| B-C13-ADVERSARIAL-INTEGRATION-CORPUS | Adversarial integration corpus immediately after C14 sketch (per W#6 item 6 + D15 path) | W#6 item 6 | M (pre-LOCK validation) |

**Total walk #6 polish backlog: 7. Cumulative across walks 2-6: 31 backlog items.**

Note: B-C13-ADVERSARIAL-INTEGRATION-CORPUS is technically pre-LOCK
work, not post-LOCK polish. It's filed in the backlog tracker but
scheduled to run during the path-(a) execution window (after C14 v0.1
sketch, before walk #6.5/LOCK).

---

## Items where reviewer + v0.5 spec ALREADY agree (no amendment)

These 4 items are validation, not critique:

- **Item 6** (LOCK may hide emergent interactions) — already addressed
  by D15 path (a): build adversarial corpus after C14 sketch.
- **Item 7** (diminishing returns ONLY for abstract walks) — agreement.
  v1.1 amendments expected post-LOCK via E4's fast-revision window.
- **Item 14** (empirical maturity zero) — agreement. Implementation
  is the highest-value next activity, exactly what path (a) delivers.
- **Item 15** (biggest risk = C13↔C14 interface) — agreement. Validates
  the v0.5 + v0.6 recommendation to draft C14 v0.1 next.

---

## LOCK readiness — UPDATED

**Architectural maturity**: HIGH+. v0.6 adds explicit constraint
classification (E1), composability validation criterion (E2), causal-
trace forward-compat (E3), and post-LOCK fast-revision window (E4).
These close the four remaining structural concerns.

**Empirical maturity**: STILL ZERO. (Unchanged from v0.5 — only fixable
by execution.)

**LOCK gating** (updated from v0.5):

1. ⏳ **C14 v0.1 sketch** per D11 minimum scope checklist + E2
   composability validation — REQUIRED
2. ⏳ **End-to-end example** (C12 → C13 → C14 → C15 for one 4-room
   compact residential) — REQUIRED
3. ⏳ **Adversarial integration corpus** per B-C13-ADVERSARIAL-INTEGRATION-CORPUS
   — RECOMMENDED before LOCK (not strictly required, but reviewer
   item 6 makes a strong case)
4. ⏳ **Final operational-validation walk** (#6.5 — different from
   this abstract walk; focused on composability per E2) — REQUIRED
5. ✅ **Architectural completeness** — ACHIEVED at v0.6

Once 1-4 complete, C13 LOCK candidacy is fully gated.

---

## Recommendation (Rule 11 self-analysis)

Walk #6 is the SECOND consecutive walk with ≤4 structural amendments
and majority polish/agreement items. This is the formal diminishing-
returns signal — same pattern C12 hit at walk #4.

**The reviewer's final assessment explicitly endorses path (a)**:

> "DO NOT continue large-scale theoretical C13 amendment walks before:
> drafting C14 v0.1 sketch, implementing prototype scaffolding,
> building telemetry, running adversarial layouts, and testing
> end-to-end flows."

I fully agree. v0.6 absorbs the 4 minor structural items reviewer
raised and defers everything else.

**Three paths for your adjudication** (updated from v0.5):

1. **(a) my STRONG recommendation**: endorse v0.6; draft C14 v0.1
   sketch next session (per D11 + E2 composability criteria); run
   adversarial integration corpus; then final walk #6.5 + LOCK.

2. **(b)** Continue C13 abstract walks #7+. Strong evidence against
   this: 2 consecutive walks show diminishing returns; reviewer
   explicitly advises against; Pattern E risk.

3. **(c)** LOCK C13 v0.6 NOW without C14 v0.1 sketch. Slight risk:
   AdvisoryFlag composability gap surfaces during C14 build and
   requires C13 v1.1 amendment. With E4's fast-revision window in
   place, this risk is now bounded — v1.0.x patches can ship in 90
   days without heavy governance. **(c) is actually viable post-E4.**

**My ranking now**: (a) > (c) > (b). v0.6 + E4 fast-revision window
makes (c) plausible without committing to one more round of abstract
walking.

---

Per Rule 8: vN PROPOSED. PENDING Ramalingam LOCK adjudication.

**v0.6 PROPOSED is the LOCK-CANDIDATE with confirmed diminishing-
returns signal.** Awaiting your direction on (a)/(b)/(c).
