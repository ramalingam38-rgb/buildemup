# S38 Critique Walk — External Review of S38 Combined Amendments

**Walk number**: S38 Walk #1.
**Reviewer**: External (document provided by Ramalingam).
**Subject**: B-NEW-P, B-NEW-K, B-NEW-L, B-NEW-J as PROPOSED v0.1.
**Walked by**: Claude, S38.
**Method**: Rule 7 — verdict per finding (VALID / BACKLOG / MISFRAMED /
DOCUMENTED / SPEC-AMENDMENT). Web search mandatory: ≥1 search per round
to verify reviewer claims AND Claude's pushbacks. Code grep mandatory
on code claims. Push back when wrong.

---

## § 0 — Rule 7 gates surfaced at start

Reviewer makes verifiable factual claims in two places:
1. **B-NEW-P-1**: "severity_tier: ClassVar[str]" — values are weakly
   typed strings, vulnerable to typo / casing drift.
2. **B-NEW-K-impl**: implicit claim that 0.9m width / 0.9m landing
   are NBC residential minimums (this is my own claim — the reviewer
   didn't dispute it, but Rule 7 requires me to verify my own
   pushbacks too).

Code grep run: §1.1.
Web search run: §1.2 (NBC 2016 residential staircase minimums).

All other reviewer findings are design-philosophy / scope-discipline
claims, not externally verifiable; adjudicated on logical merit.

---

## § 1 — Verification

### § 1.1 Code grep — severity_tier typing

Reviewer claim: "string-based severity values remain weakly typed".

Actual code (verified):
```python
# components/c08/errors.py, c09/errors.py, c10/errors.py
_SeverityTier = Literal["per_candidate", "batch", "systemic"]

class WetZonePlanError(Exception):
    severity_tier: ClassVar[_SeverityTier] = "per_candidate"
```

`_SeverityTier` is a **typing.Literal closed-set type**, statically
checked by mypy / pyright / pyrefly. Assigning `"systemic"` ✓.
Assigning `"system"` ✗ (type error). Assigning `"SYSTEMIC"` ✗.
This is structurally identical to an Enum at the type-system level —
the closed-set property is preserved.

**Reviewer's "typo / casing / 'SYSTEMIC' vs 'system'" example is
factually wrong about the actual code**. Static type-checking
catches all three.

### § 1.2 Web search — NBC 2016 residential staircase minimums

Verified from multiple secondary sources (InfraLens, Sobha, Housivity,
houseyog) all consistent:

- **Residential staircase minimum width: 0.9 m** for buildings under
  3 stories. (InfraLens, Sobha NBC 1.13, houseyog summary.)
- **Landing depth: equal to staircase width** (not a fixed minimum).
  E.g., a 1.2 m wide stair requires a 1.2 m landing minimum.

My current code uses `MIN_STAIRCASE_WIDTH_M = 0.9` and
`MIN_STAIRCASE_LANDING_DEPTH_M = 0.9` as independent fixed minimums.
For the v1 minimum-width case (0.9m × 0.9m) this is correct. For
larger staircases (e.g., 1.0 m residential 3+ stories per NBC), the
landing should also scale to ≥ 1.0 m — but my current rule lets a
1.2 m wide stair pass with a 0.9 m landing.

**This is a finding the reviewer did NOT surface but is valid.** Adding
to backlog as B-NEW-K-landingscale.

---

## § 2 — Verdicts on reviewer findings

### B-NEW-P — Error severity classification

#### B-NEW-P-1 — String-based severity values weakly typed

**Verdict**: **MISFRAMED** (with partial concession).

Reviewer's premise — that values are bare strings — is wrong per § 1.1.
The Literal closed-set type provides the same closed-set guarantee an
Enum would. mypy/pyright reject typos and casing drift at type-check
time.

**Partial concession**: a `StrEnum` subclass would be marginally
better in two ways:
1. Static rejection of unknown values without needing mypy in CI
   (Literal is only enforced by static type-checkers, not at runtime).
2. Discoverability via `_SeverityTier.__members__`-style introspection.

But the trade-off:
- Enum requires importing the actual class everywhere it's used as a
  value, including in tests that compare to literal strings.
- The current design lets `severity_tier == "systemic"` work in test
  assertions; an Enum forces `severity_tier is _SeverityTier.SYSTEMIC`.
- The amendment is contract-completion, not greenfield design — the
  Literal pattern follows existing buildemup conventions
  (TopologyKind/etc are Enums; numeric/string-literal-keyed maps stay
  Literal).

**Action**: no v1.0 amendment change. Filing **B-NEW-P-enum** as
backlog (post-launch consideration; trivial to switch later — just
change `_SeverityTier` from a Literal to a StrEnum subclass and
update `__post_init__` checks).

#### B-NEW-P-2 — C7 stdlib exceptions collapse to "systemic"

**Verdict**: **DOCUMENTED**.

This is exactly what § 1 of B-NEW-P spec already documents: "C7 has
no custom error classes…Per C11a § 2.7's defensive default, unknown
severity → systemic, which is the safe behaviour for C7's stdlib
raises." Reviewer's "may occasionally over-halt batches" is the
correct behaviour for an unknown error class.

**Partial concession**: the reviewer is right that some C7
ValueErrors *could* in principle be per-candidate. The fix isn't to
relax the default — it's to give C7 custom error classes, which is
B-NEW-P-c7classes (new backlog item).

**Action**: no v1.0 amendment change. Filing **B-NEW-P-c7classes**
as post-launch backlog: introduce `GridGenerationError` /
`SpanInfeasibleError` etc. for C7 to replace stdlib raises, with
proper `severity_tier` annotations.

---

### B-NEW-K — C7 staircase clearance

#### B-NEW-K-1 — Staircase is a purely geometric rectangle

**Verdict**: **VALID-BUT-BACKLOG** (already filed).

Reviewer is correct that the rectangle abstraction ignores stair
direction, riser geometry, U/L-shapes, etc. § 1 of the B-NEW-K spec
explicitly scopes this out: "Does NOT model the
egress-clearance-in-front-of-staircase check" and "Does NOT validate
vertical clearance / headroom".

**B-NEW-K-impl** is already filed for the GridGenerator integration;
**B-NEW-K-shape** is not. Adding it.

**Action**: no v1.0 amendment change. **Filing B-NEW-K-shape**:
extend Staircase model to carry `climb_direction: WallAxis`, `shape:
StairShape` enum (STRAIGHT/L/U/SPIRAL), `riser_height_m`,
`tread_depth_m`. Triggered post-launch + B-NEW-K-impl.

#### B-NEW-K-2 — Egress-clearance omission

**Verdict**: **DOCUMENTED**. Already filed as **B-NEW-K-egress** in
spec § 8. Reviewer's "MEDIUM-HIGH practical concern" priority noted
— but for v1 LOCK gate (Inv 24), the predicate's scope (mutation
viability) is correct. Egress is downstream concern.

**Action**: no v1.0 amendment change. B-NEW-K-egress already on
backlog.

#### B-NEW-K-3 — Anchor semantics under-specified

**Verdict**: **VALID — partial**. § 1.1 of this walk verified that
my anchor field defines which envelope edge the footprint is flush
with, but does NOT specify climb direction or landing-side. For
mutation viability (the C11a Tier A predicate's purpose) this is
sufficient — the predicate scope is footprint-clearance only. But
for downstream consumers (B-NEW-K-impl), they'll need climb
direction.

**Action**: no v1.0 amendment change for the predicate purpose, but
documenting in B-NEW-K-shape (above) that `climb_direction` is part
of the post-launch enrichment.

---

#### B-NEW-K-4 (NEW — surfaced by Claude during this walk)

**Title**: Landing depth doesn't scale with stair width per NBC.

**Verdict**: **VALID — but spec-amendment scope-creep risk**.

NBC 2016 (verified per § 1.2) requires landing depth ≥ stair width,
not a fixed 0.9m minimum. My v1 code uses fixed minimums for both,
so a 1.2m wide stair can pass W9 with a 0.9m landing.

**Decision**: this is genuinely a v1 correctness bug, not a future
enhancement. Two options:
- **(a)** Patch B-NEW-K v0.1 → v0.2 PROPOSED to change W9-b from
  `landing_depth_m ≥ MIN_STAIRCASE_LANDING_DEPTH_M (= 0.9)` to
  `landing_depth_m ≥ width_m`.
- **(b)** File as **B-NEW-K-landingscale** for post-LOCK fix,
  preserving v0.1 as PROPOSED.

I lean toward **(a)** because it's a 2-line code change + 2 test
updates, and shipping v1.0 with a known under-specification is worse
than a small patch round. Surfacing for Ramalingam's call.

**Action**: surfaced for Ramalingam adjudication at end of walk.

---

### B-NEW-L — C8 entry approach Inv 21

#### B-NEW-L-1 — Edge-based entry semantics simplistic

**Verdict**: **DOCUMENTED**. Reviewer is correct that real entry
usability depends on setbacks, vehicle access, gate placement, etc.
But (a) those concerns belong at C2 (parking feasibility) and C6
(setback), not C8 (corridor design); (b) Inv 21's purpose is
mutation viability for M9a-d, not entry-usability validation. Edge
compatibility is the right v1 abstraction.

**Action**: no v1.0 amendment change. The concerns reviewer raises
are already covered by B-NEW-J-roomlevel (privacy/usability layer)
and existing C2/C6 components.

#### B-NEW-L-2 — Multi-entry semantics deferred

**Verdict**: **DOCUMENTED**. Already filed as **B-NEW-L-multi-entry**
in spec § 6. Reviewer's "LOW priority" assessment matches my
backlog priority.

**Action**: no v1.0 amendment change.

---

### B-NEW-J — C5 privacy zoning

#### B-NEW-J-1 — Zone-band privacy is coarse proxy

**Verdict**: **DOCUMENTED**. Already filed as **B-NEW-J-roomlevel**
in spec § 6. Reviewer's "MEDIUM-HIGH practical concern" matches.
Spec § 1 explicitly says: "Per-room 'bedroom on road wall' checks
at C9/C10 are a stricter follow-up captured as a backlog item."

**Action**: no v1.0 amendment change.

#### B-NEW-J-2 — Cultural assumptions hardcoded

**Verdict**: **MISFRAMED**.

Reviewer surfaces "urban premium frontage homes, sea-facing/
view-facing bedrooms" as legitimate exceptions. But:

1. **The rule is for mutation viability, not user override.** A user
   who genuinely wants a road-facing master bedroom can specify that
   intent in C1 (brief capture) and bypass the M2/M5 mutation entirely;
   B-NEW-J doesn't constrain user-stated preferences, only mutation
   suggestions.

2. **The "exceptions" the reviewer cites are themselves regional
   sub-typologies**, not universal exceptions. A sea-facing house in
   Mumbai's Bandra Bandstand is a luxury sub-typology — BuildemUp's
   target user is the mainstream solo Indian self-builder per
   project memory ("solo founder…decision-support engine for Indian
   families building their own homes"). The mainstream target is
   correctly served by the rule.

3. **The "intentional layout" objection conflates rule with
   recommendation.** Inv 21/J is a mutation-viability gate, not a
   recommendation engine. C11a's pre-Pareto NSGA-II will explore
   mutated layouts; rejecting "PRIVATE on road" mutations means
   C11a's *suggestions* respect privacy; the user can still
   manually reject any C11a output and specify their own preferences
   via C1 brief.

**Action**: no v1.0 amendment change. **Filing B-NEW-J-override**
as low-priority backlog: explicit user-brief field
`accept_road_facing_private_band: bool = False` to short-circuit
the rule for users with stated luxury / view preferences. This is
post-launch discovery work.

#### B-NEW-J-3 — Intercardinal forbidden-triple over-constrains

**Verdict**: **DOCUMENTED — design intent**.

Reviewer is correct that conservatism may reject layouts that would
work in practice on a corner plot. But this is exactly the **design
discipline** my spec § 1 articulates: "A PRIVATE band on any of
those three is exposed to the road. … Conservative privacy bias is
reasonable at topology stage." The reviewer's own conclusion agrees
("Conservative privacy bias is reasonable at topology stage").

**Action**: no v1.0 amendment change.

**Note**: the smoke test in `tests/test_c5_privacy_zoning.py`
(test #22) verifies that all 32 default zone_bands × facing
combinations from C5's existing `default_zone_bands(kind, facing)`
already pass the rule. Reviewer's "may over-constrain" concern
is empirically not realised against C5's own defaults — the rule
fits cleanly in the default design space.

---

### Cross-amendment systemic findings

#### Cross-1 — Predicate ecosystem governance load

**Verdict**: **VALID — but C11a-scoped, not S38-scoped**.

Reviewer is correct that a growing predicate registry creates
governance overhead. But this is exactly what C11a § 0.4 and § 3.4
explicitly model: "C11a does not own architectural rules; legality
predicates reference upstream rule IDs." The governance lives in
C11a's `MutationViabilityPredicate` registry with its `rule_owner`,
`rule_id`, `pending_upstream` audit fields. C11a's Inv 24 LOCK gate
itself is the formal governance instrument.

**Action**: no v1.0 amendment change. C11a's existing infrastructure
handles this.

#### Cross-2 — Topology-level proxies vs physical-validity

**Verdict**: **DOCUMENTED** — this is the deliberate layered
architecture per C11a § 0.4 and the spec discipline of each
amendment. Reviewer's own conclusion agrees: "earlier components
SHOULD operate at coarser abstraction levels."

**Action**: no v1.0 amendment change.

---

## § 3 — New backlog items filed (per Rule 9.2)

All new items added immediately to backlog without permission per
Rule 9.2. Filed as v0.2 PROPOSED amendments where they patch the
spec; filed as new B-IDs where they're follow-on work.

| ID | Origin | Trigger | Effort |
|---|---|---|---|
| **B-NEW-P-enum** | Walk #1 P-1 partial | post-launch Enum migration | XS |
| **B-NEW-P-c7classes** | Walk #1 P-2 | when C7 ValueErrors need per-candidate routing | S-M |
| **B-NEW-K-shape** | Walk #1 K-1 + K-3 | post-launch + B-NEW-K-impl | M-L |
| **B-NEW-K-landingscale** | Walk #1 K-4 (Claude-surfaced) | **v0.2 patch candidate (urgent)** | XS |
| **B-NEW-J-override** | Walk #1 J-2 | post-launch user-feedback | S |

---

## § 4 — Adjudication summary

| Reviewer finding | Verdict | v1.0 spec change? |
|---|---|---|
| B-NEW-P-1 (weak typing) | **MISFRAMED** (Literal IS closed-set) | No |
| B-NEW-P-2 (C7 stdlib) | **DOCUMENTED** | No |
| B-NEW-K-1 (rect model) | **VALID-BUT-BACKLOG** | No |
| B-NEW-K-2 (egress) | **DOCUMENTED** | No |
| B-NEW-K-3 (anchor) | **VALID — partial** | No |
| **B-NEW-K-4 (landing scale)** | **VALID** (Claude-surfaced) | **YES — patch candidate** |
| B-NEW-L-1 (edge simplistic) | **DOCUMENTED** | No |
| B-NEW-L-2 (multi-entry) | **DOCUMENTED** | No |
| B-NEW-J-1 (coarse proxy) | **DOCUMENTED** | No |
| B-NEW-J-2 (cultural) | **MISFRAMED** (mutation-viability ≠ recommendation) | No |
| B-NEW-J-3 (intercardinal) | **DOCUMENTED** | No |
| Cross-1 (governance) | **VALID — C11a-scoped** | No |
| Cross-2 (proxies) | **DOCUMENTED** | No |

**Walk-end status**:

- **3 amendments LOCK-ready as v0.1 PROPOSED**: B-NEW-P, B-NEW-L,
  B-NEW-J. No v1.0 changes from this walk.
- **B-NEW-K is patch-candidate**: my own Claude-surfaced finding (K-4
  landing-depth-scale) has spec-amendment implications. Surfacing
  for Ramalingam adjudication.

---

## § 5 — Decision needed from Ramalingam

For B-NEW-K only (P, L, J unaffected):

- [ ] **(a) Patch B-NEW-K to v0.2 PROPOSED** with corrected W9-b:
      `landing_depth_m >= width_m` (instead of fixed 0.9m floor).
      I produce v0.2 PROPOSED, update the predicate code, update tests
      (~2-line code change, ~3 tests adjusted, ~30 min effort).
- [ ] **(b) Keep B-NEW-K v0.1 as-is**, file the issue as
      **B-NEW-K-landingscale** for post-LOCK fix. Cleaner LOCK round
      but ships a known under-spec.
- [ ] **(c) other**: ____________________________________________

P, L, J — confirm LOCK as v1.0?
- [ ] LOCK B-NEW-P v0.1 → v1.0
- [ ] LOCK B-NEW-L v0.1 → v1.0
- [ ] LOCK B-NEW-J v0.1 → v1.0

---

**End of S38 Walk #1.**
