# S38 Walk #2 — Adjudication of Meta-Critique on Walk #1

**Walk number**: S38 Walk #2.
**Reviewer**: External (document provided by Ramalingam).
**Subject**: meta-critique of S38 Walk #1's adjudications.
**Walked by**: Claude, S38.
**Method**: Rule 7 — verdict per finding (VALID / BACKLOG / MISFRAMED /
DOCUMENTED / SPEC-AMENDMENT). Search/grep where reviewer makes
verifiable claims.

---

## § 0 — Rule 7 gates surfaced at start

**Verifiable claims to check:**
1. Finding 1: Python runtime accepts unrecognised string assignment to
   a Literal-typed ClassVar.
2. Finding 6: C11a/C1 architecture has no user-override mechanism that
   would let a user bypass B-NEW-J for road-facing-bedroom preferences.

Both verified in § 1. Other findings are governance/realism
meta-observations adjudicated on logical merit.

---

## § 1 — Verification

### § 1.1 Runtime Literal enforcement (Finding 1)

```python
from typing import ClassVar, Literal
_T = Literal['per_candidate', 'batch', 'systemic']
class E(Exception):
    severity_tier: ClassVar[_T] = 'per_candidate'
e = E()
e.severity_tier = 'SYSTEM'    # No runtime error.
print(e.severity_tier)         # → 'SYSTEM'
```

**Reviewer is technically correct.** Python accepts the bad
assignment at runtime. Static type-checkers (mypy/pyright/pyrefly)
catch it; the runtime does not.

My Walk #1 said "structurally identical to an Enum" without
qualification. That phrasing was too strong. The qualified version
("structurally identical at the type-system level") is accurate, but
the unqualified version overstates the equivalence — a `StrEnum`
provides runtime rejection of bad values; `Literal` does not.

### § 1.2 User-override mechanism (Finding 6)

Greppped C1 brief schema and C11a v1.0 LOCKED spec:
- `components/c01/*.py`: no `accept_road_facing_private_band`, no
  `override_privacy`, no `user_preference` flag for predicate
  bypass. Brief carries `plot.facing` but not user-stated layout
  preferences that would key off `B-NEW-J`'s predicate.
- C11a v1.0 LOCKED spec: no predicate-disable or user-override
  mechanism. `MutationViabilityPredicate` is keyed off `rule_owner`,
  `rule_id`, `pending_upstream` only.

**Reviewer is correct.** My Walk #1 claim — that "a user who
genuinely wants a road-facing master bedroom can specify that intent
in C1 (brief capture) and bypass the M2/M5 mutation entirely" —
**describes a path that doesn't exist in the current architecture.**
C1's brief has no such field, and C11a's predicate registry has no
override slot. B-NEW-J's predicate fires unconditionally on every M2/
M5 mutation, regardless of user preference.

This is a meaningful concession. My pushback on the original critique
was **partially MISFRAMED**: I correctly identified the conceptual
distinction between "mutation viability" and "user recommendation",
but I incorrectly claimed an operational override path that doesn't
exist.

---

## § 2 — Verdicts

### Finding 1 — Literal typing depends on static-analysis discipline

**Verdict**: **VALID — partial concession.**

Reviewer is correct that Python's runtime doesn't enforce Literal.
My Walk #1 overstated the Enum-equivalence. The actual position is:
- mypy/pyright/pyrefly catch typos and casing drift at static-check
  time.
- Python runtime accepts any string assignment.
- Tests passing without static type-check don't catch the issue.

Mitigations already in place:
- `tests/test_severity_tier_classification.py` Test #2 explicitly
  validates `severity_tier in VALID_TIERS = {"per_candidate",
  "batch", "systemic"}` for every error class. So a typo in the
  declaration would be caught at test time, not just static-check
  time.

This is meaningful coverage but doesn't catch a typo introduced by a
future contributor on a *new* error class that hasn't been added to
the test parametrization.

**Action**: no v1.0 change. **B-NEW-P-enum** already filed at Walk #1
captures the migration option. **Adding** runtime check at audit time
in C11a Sub-session 1's `audit_predicate_registry` (mentioned in
C11a § 0.5) — the audit would iterate registered predicates and
verify their declared `severity_tier` against the closed set. That
slots into existing C11a infrastructure rather than spawning new
governance.

**New backlog**: **B-NEW-P-runtime-audit** — extend C11a
predicate-registry audit to verify upstream error classes have
valid `severity_tier` ClassVars at C11a startup, not just static
type-check time. XS effort, post-launch consideration.

---

### Finding 2 — NBC grounding relies on secondary-source interpretation

**Verdict**: **DOCUMENTED.**

Reviewer is correct. My Walk #1 search hit InfraLens / Sobha /
Housivity / houseyog — secondary sources. Primary source is BIS NBC
2016 Part 4 itself, which is paywalled / requires BIS license.

Already handled by B-150-equiv pre-launch hard gate ("Primary-source
verification of NBC residential staircase minimums"). Not a v1
correctness blocker; it's a pre-launch-only hard gate. Spec § 0
flags constants as "needs-verification".

**Action**: no v1.0 change. B-150-equiv handles this.

---

### Finding 3 — B-NEW-K-4 landing-depth-scale (HIGH priority)

**Verdict**: **VALID — Walk #1 already surfaced this.** Reviewer
**corroborates** Walk #1's recommendation to patch before LOCK.

Two independent reviewers (the meta-critique reviewer + my own Walk
#1 self-surfacing) now agree this is the only finding that rises
to "v1 correctness flaw" rather than backlog-deferrable. The signal
strength is unambiguous.

**Action**: still pending Ramalingam decision — see § 5.

---

### Finding 4 — Backlog growth becoming hidden complexity layer

**Verdict**: **VALID — meta-governance concern.**

Reviewer correctly observes that B-NEW-K-{shape, egress, landingscale,
impl} + B-NEW-J-{roomlevel, override} + B-NEW-L-{multi-entry,
rotated} are fragments of future semantic systems that may overlap
heavily.

But this is also exactly what backlog discipline is *for*. The
alternative — building all the realism layers into v1 — is the
"fix-as-bandage / scope-creep-mid-build" antipattern explicitly
called out in project memory.

**Mitigation**: a **backlog roadmap consolidation** exercise post-LOCK,
where the K-* and J-* clusters are reviewed as a group for shared
abstractions before any one of them is built. This isn't a v1 task.

**Action**: no v1.0 change. **New backlog**: **B-meta-backlog-roadmap**
— periodic backlog-cluster review to detect overlapping future
semantic systems. M-LONGTERM. File only if the cluster grows beyond
3 items per parent (already the case for K-*, watch J-* and L-*).

---

### Finding 5 — "Mutation viability" abstraction shield

**Verdict**: **VALID — partial concession on pattern, not on
individual usages.**

I used "mutation viability, not full realism" framing in 4
adjudications across Walk #1 (B-NEW-K-1, B-NEW-K-2 partially,
B-NEW-L-1, B-NEW-J-2). Each individual usage was correct in its
specific context — the predicate scope IS mutation viability per
C11a § 0.4 ("C11a does not own architectural rules; legality
predicates reference upstream rule IDs"). But the **pattern of
repeated reliance** on this distinction is a real risk: it can
become the dismissal mechanism the reviewer warns about.

The genuine risk this points to is: **upstream coarse predicates
that are weak predictors of downstream success will inflate the
rejection rate at later layers, wasting C11a's NSGA-II search
effort.** That's a real, measurable concern that becomes visible
at integration time, not before.

**Action**: no v1.0 change. **New process note**:
**B-meta-predicate-fidelity-monitoring** — at C11a integration time,
measure downstream rejection rate per Tier A predicate. If a
predicate's false-positive rate (passes mutation viability but fails
at C9/C10) exceeds some threshold (TBD), file the predicate for
realism enrichment. M-LONGTERM. This is exactly what Pareto
optimization metrics would surface naturally if they exist.

---

### Finding 6 — Cultural-rule rebuttal overstates user override

**Verdict**: **VALID — concession.** § 1.2 above verified the
user-override path I described in Walk #1 doesn't exist in the
current architecture.

The substance of my Walk #1 verdict (B-NEW-J-2 = MISFRAMED) was
**partially correct**: the reviewer's "universal cultural bias"
framing did conflate mutation viability with recommendation. But my
specific defense — "a user can specify intent in C1 brief" — was
factually wrong, because C1 has no such field today.

**Adjusted verdict on original B-NEW-J-2**: **VALID-IN-PART**.

The implication: **B-NEW-J-override is not a low-priority
post-launch backlog item; it's the operational complement to
B-NEW-J's enforcement.** Without an override mechanism, C11a's M2/M5
mutation engine will always avoid road-facing PRIVATE bands, biasing
the search-space against legitimate luxury/view typologies even when
the user wants them.

**Action**: no v1.0 spec change to B-NEW-J itself (the rule is
correct), but **escalating B-NEW-J-override priority** from
"low-priority post-launch" to "complement-of-launch" — i.e., it
should ship in the same release window as B-NEW-J's actual
enforcement (whenever C11a v1 ships in production), not deferred
indefinitely.

The override mechanism design: a `brief.layout_overrides:
LayoutOverrides` field carrying named-rule bypass tokens (e.g.,
`accept_road_facing_private_band: bool = False`). C11a's predicate
registry consults overrides before firing the predicate. Effort:
S-M, owned by C1 (brief schema) + C11a (registry consultation).

---

### Finding 7 — Predicate governance manually coordinated

**Verdict**: **VALID — meta-governance, longterm.**

Reviewer is correct that there's no centralized invariant graph,
predicate conflict detector, or semantic-coupling mapper. C11a's
predicate registry is a flat list of `(rule_owner, rule_id,
description, _predicate_fn)` tuples; growth could lead to
duplication or contradictory rules without automated detection.

But this is exactly the governance C11a § 0.5 (`audit_predicate_
registry`) is positioned to handle — it just hasn't been extended
to do conflict detection yet.

**Action**: no v1.0 change. **New backlog**:
**B-meta-predicate-conflict-detector** — extend C11a's audit to:
(a) detect duplicate `(rule_owner, rule_id)` pairs, (b) detect
predicates with overlapping rule_ids across different owners, (c)
visualize the predicate graph by rule_owner cluster. M effort,
post-launch.

---

### Finding 8 — Convergence narrative slightly optimistic

**Verdict**: **VALID — partial concession, MINOR.**

Reviewer's distinction between "structurally mature" vs "semantically
mature" is fair. My Walk #1's "3 amendments LOCK-ready" is accurate
about the LOCK gate (Inv 24) but doesn't speak to semantic richness.

This is more a tone calibration than a finding requiring action.
Conceding the framing without action.

**Action**: no v1.0 change. No backlog item.

---

### Finding 9 — Partial-fix-now + backlog-later pattern hides tech debt

**Verdict**: **VALID — but inherent to phased-delivery discipline.**

Reviewer is right that repeated use of the "minimal v1, defer
realism to backlog" pattern can ossify simplifications. But this is
also the alternative to the "scope-creep-mid-build" antipattern
explicitly called out in project memory ("most expensive of the 5
patterns to avoid"). The fix isn't to stop doing phased delivery; it's
to plan migration paths upfront.

**Action**: no v1.0 change. Already mitigated by spec-discipline:
each amendment's § 1 ("Scope discipline") explicitly enumerates what
v1 does NOT do, with named backlog items for the deferred work. This
makes future migration legible.

---

### Finding 10 — Invariants accumulating semantic weight beyond original layer

**Verdict**: **VALID — design observation, no action needed.**

Reviewer is right that B-NEW-J starts as "topology-stage privacy
filter" and gradually becomes a de facto architectural-realism rule.
But that's not necessarily a flaw — it reflects the reality that an
invariant good enough to filter mutations is also good enough to
inform downstream architectural intent.

The hidden-rigidity risk the reviewer raises is real but addressable
by the same B-NEW-J-override mechanism (Finding 6). If an override
exists, semantic weight is not rigidity — it's a default that can
be relaxed.

**Action**: subsumed under B-NEW-J-override (now escalated).

---

### Finding 11 — Cross-layer realism gaps may accumulate optimization waste

**Verdict**: **VALID — empirically observable post-integration.**

Reviewer is right that coarse upstream + permissive filters →
wasted NSGA-II search effort. Pareto pollution is a real risk that
becomes visible only at integration time.

**Action**: subsumed under B-meta-predicate-fidelity-monitoring
(Finding 5). The fix is measurement, not pre-launch architectural
change.

---

### Finding 12 — Review rigor depends on reviewer quality

**Verdict**: **MISFRAMED — meta-process observation, not a system
finding.**

This is true of any architecture review. It's not actionable as a
system change. The walk's defense against superficial reviewers IS
Rule 7 — verify factual claims, push back on MISFRAMED findings,
file legitimate VALID-BUT-BACKLOG items, end with backlog roll-up.

**Action**: no change. Standing process discipline already in place.

---

## § 3 — Walk #2 corrections to Walk #1

| Walk #1 verdict | Walk #2 correction |
|---|---|
| B-NEW-P-1 = MISFRAMED | **VALID — partial.** Literal is static-only at runtime; my "Enum-equivalent" was overclaim. Mitigation: existing test #2 + new B-NEW-P-runtime-audit. |
| B-NEW-J-2 = MISFRAMED | **VALID-IN-PART.** The "user-override" path I cited doesn't exist in current architecture. Action: escalate B-NEW-J-override from low-priority to launch-complement. |

These are the only two Walk #1 verdicts that need adjustment. The
other 11 stand.

---

## § 4 — New backlog filed (per Rule 9.2)

| ID | Origin | Trigger | Effort |
|---|---|---|---|
| **B-NEW-P-runtime-audit** | Walk #2 F1 | post-launch C11a audit extension | XS |
| **B-meta-backlog-roadmap** | Walk #2 F4 | when K-/J-/L- backlog clusters need consolidation review | M-LT |
| **B-meta-predicate-fidelity-monitoring** | Walk #2 F5 + F11 | C11a integration-time downstream rejection-rate measurement | M-LT |
| **B-meta-predicate-conflict-detector** | Walk #2 F7 | post-launch C11a audit extension | M |

**Plus escalation** (not new): **B-NEW-J-override** moves from
"post-launch user-feedback" to "complement-of-launch — must ship
when B-NEW-J's enforcement ships in production". S-M effort, owned
by C1 + C11a.

---

## § 5 — Adjudication summary

| Walk #2 finding | Verdict | v1.0 change? |
|---|---|---|
| F1 (Literal runtime) | **VALID — partial concession** | No (B-NEW-P-runtime-audit filed) |
| F2 (NBC secondary) | **DOCUMENTED** (B-150-equiv) | No |
| F3 (K-4 landing scale) | **VALID — corroborates Walk #1** | **YES — patch candidate** |
| F4 (backlog growth) | **VALID — governance** | No |
| F5 (mutation-viability shield) | **VALID — pattern concern** | No |
| F6 (user-override neutrality) | **VALID — concession** | No (B-NEW-J-override escalated) |
| F7 (predicate governance) | **VALID — longterm** | No |
| F8 (convergence optimism) | **VALID — minor** | No |
| F9 (partial-fix tech debt) | **VALID — inherent** | No |
| F10 (semantic accumulation) | **VALID — subsumed** | No |
| F11 (cross-layer waste) | **VALID — subsumed** | No |
| F12 (reviewer quality) | **MISFRAMED — meta-process** | No |

**11 valid / 1 misframed.** The two genuine corrections to Walk #1
adjusted (F1, F6 partial). All other findings either DOCUMENTED in
existing backlog, subsumed under filed items, or governance-monitoring
without v1 action.

**The B-NEW-K-4 patch is the only material v1 decision still
pending.** Twice corroborated now (Walk #1 self-surfaced + Walk #2
reviewer agreement).

---

## § 6 — Decision needed from Ramalingam

Same as Walk #1 § 5, restated cleanly:

### B-NEW-K v0.1 → patch or accept?

- [ ] **(a) Patch B-NEW-K to v0.2 PROPOSED**: change W9-b from
      `landing_depth_m >= MIN_STAIRCASE_LANDING_DEPTH_M (= 0.9m)`
      to `landing_depth_m >= max(width_m, MIN_STAIRCASE_LANDING_DEPTH_M)`.
      ~30 min: 2-line code change, 3 test adjustments, surface as
      patch round, you LOCK v0.2 → v1.0.
- [ ] **(b) Keep v0.1 as-is**, file as **B-NEW-K-landingscale** for
      post-LOCK fix. Faster LOCK round but ships a known
      under-specification.
- [ ] **(c) other**

**My recommendation: still (a).** Twice corroborated; trivial fix;
shipping v1.0 with a known under-specification is worse than the
small patch round.

### LOCK confirmation for the other three?

- [ ] LOCK B-NEW-P v0.1 → v1.0 (Walk #2 F1 mitigation via
      B-NEW-P-runtime-audit backlog, not blocking)
- [ ] LOCK B-NEW-L v0.1 → v1.0
- [ ] LOCK B-NEW-J v0.1 → v1.0 **with** explicit acknowledgment that
      B-NEW-J-override is escalated to launch-complement (not deferred
      indefinitely)

---

**End of S38 Walk #2.**
