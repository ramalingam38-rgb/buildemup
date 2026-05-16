# C3b — Post-Layout Trade-off Negotiation
## Spec v0.4 LOCKED — Ratified at S50 close

**Status:** v0.4 LOCKED. LOCKED by Ramalingam at S50 close (Rule 8).
**Predecessor:** v0.3 PROPOSED (S50).
**Composed from:** v0.3 PROPOSED + third critique walk findings (S50 close).
**Session:** S50 close.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone.

---

## § 0 — Composition rationale (v0.4)

v0.3 PROPOSED was a surgical patch over v0.2 (1 small SPEC-AMENDMENT
+ 6 backlog items, 0 new R-invariants). The third critique walk
identified **one remaining LOCK-boundary ambiguity**: whether § 0.2
Negotiation Philosophy Hierarchy is **descriptive** or **normative**.

The reviewer's framing was unambiguous LOCK signal: *"v0.3 is very
likely the LOCK candidate. The architecture has stabilized."* and
*"I would NOT request a major v0.4 restructure."*

**v0.4 contains a single micro-patch:**

1. **§ 0.2 explicitly clarified as DESCRIPTIVE.** Hierarchy is a map
   of existing enforcement (R13, R14, R15, R16, Principle 4, iteration
   cap), not its own governance authority. Future drifts are bugs in
   the enforcing invariants, not § 0.2 violations. Consistent with
   v0.3's restraint discipline; honors v0.2 critique pt 11's
   meta-warning against governance accretion.

Plus 4 new BACKLOG items from the v0.3 critique walk.

**No new R-invariants.** R1–R16 stand. Schema unchanged.

| Round | SPEC-AMENDMENTs | New R-invariants | Backlog | Note |
|---|---|---|---|---|
| v0.1 → v0.2 | 6 (4 major + 2 small) | 4 (R13–R16) | 8 | Major patches |
| v0.2 → v0.3 | 1 small | 0 | 6 | Philosophy section |
| **v0.3 → v0.4 (this)** | **1 micro (sentence-level)** | **0** | **4** | **Convergence floor** |

**v0.4 is the LOCK candidate.** A v0.5 round is not anticipated.

---

## § 0.1 — Mission framing — carried forward unchanged from v0.3

---

## § 0.2 — Negotiation Philosophy Hierarchy (CLARIFIED v0.4)

**§ 0.2 is EXPLICITLY DESCRIPTIVE, not normative.**

This section maps how existing enforcement mechanisms (R13, R14, R15,
R16 + Principle 4 + iteration cap + advisory tone lint) are layered
in authority. It is **a map of existing governance**, not its own
governance authority.

**Consequences of "descriptive":**

- Future code paths that violate the hierarchy are **bugs in the
  enforcing invariants** (e.g., R13 failed to block a topology-altering
  tweak), NOT violations of § 0.2 itself.
- § 0.2 has no enforcement mechanism of its own — no separate tests,
  no separate lint, no separate drift detection.
- Adding new invariants in future versions does NOT require
  cross-referencing § 0.2; the hierarchy is updated to describe the
  new state, not the other way around.
- "Tier 1 wins" means *because R13 + NBC + structural feasibility
  enforce it mechanically*, NOT because § 0.2 mandates it normatively.

**Why descriptive, not normative:**

v0.3 was composed under explicit restraint discipline per the v0.2
critique pt 11 meta-warning. Making § 0.2 normative would add a new
layer of governance machinery — the exact failure mode that meta-
warning identified. § 0.2 stays descriptive to honor the restraint.

### The hierarchy (highest → lowest authority — DESCRIPTIVE MAP)

**Tier 1 — Architectural integrity** (non-negotiable in practice
because the enforcing invariants are non-negotiable).
- Encoded by: **R13 Topology Invariance**, **NBC compliance**
  (upstream C7/C9/C15), **structural feasibility** (C7+C12), **hard
  constraints in C15's ProblemReport**.
- *"Tier 1 wins" because these enforcing invariants block at apply
  time. Violating Tier 1 means R13/NBC/etc. failed.*

**Tier 2 — Honest visibility** (non-circumventable in practice because
the enforcing invariants always surface).
- Encoded by: **R14 Regression Detection**, **R15 Multi-Tweak
  Compatibility**, **Q3 Level B logging** (chosen-from-presented
  invariant), **R16 Version Authority**.
- *"Tier 2 overrides Tier 3 in surfacing" because R14/R15/R16 surface
  outcomes before any user choice. Violating Tier 2 means a regression
  or conflict went unsurfaced — a bug in R14/R15.*

**Tier 3 — User agency** (Principle 4 always-final-choice within
Tier 1+2 constraints).
- Encoded by: **Design Principles v3.1 Principle 4**, **Phase ε
  branching logic**, **always-available undo** (R14 revert tweak, R15
  revert option, manual rejection).
- *"Tier 3 overrides Tier 4/5" because Principle 4 says so — the user
  is not coerced. Violating Tier 3 means UI imposed a choice the user
  didn't make.*

**Tier 4 — System guidance** (non-binding by R2 advisory tone lint).
- Encoded by: **MutationEnvelope** (§ 2.8), **R2 advisory-tone lint**,
  **`recommendation_flag`** (structural marker, not authoritative
  ranking), **TransparencyTriple impacts**.
- *"Tier 4 is never override-binding" because R2's banned-phrase list
  excludes imperative language. Violating Tier 4 means R2 lint missed
  a phrase that imposes rather than informs.*

**Tier 5 — Convergence support** (soft, user-wellbeing focused).
- Encoded by: **Iteration cap** (default 5, ceiling 7),
  **MAX_REPRESENT_COUNT = 2**, **MAX_TWEAKS_PER_LAYOUT = 6**.
- *Tier 5 is the softest layer — protects user from fatigue without
  constraining correctness or agency.*

### Conflict resolution

When invariants suggest conflicting actions, the standard interpretation
is to consult the tier of each enforcing invariant. **The hierarchy
documents which mechanism wins; it is not itself the deciding mechanism.**

Examples (descriptive of v0.3 behavior, not new rules):

- User accepts a tweak that violates R13 → R13 enforcement blocks the
  apply. Tier 1 "wins" because R13 enforced.
- User accepts a tweak that triggers R14 regression → R14 surfaces the
  regression in advisory; user MAY proceed. Tier 3 honored over Tier 2's
  surfacing because R14 surfaces before user choice, not after.
- User hits iteration cap → iteration cap routes to forced finalization
  with `MutationEnvelope` advisory. Tier 3 respected (user not forced
  past their will), Tier 5 protects wellbeing.

### What v0.4 does NOT add

- No `philosophy_hierarchy_check` invariant
- No tests verifying § 0.2 is "respected"
- No drift detection on tier ordering
- No new enforcement machinery whatsoever

§ 0.2 remains **legibility documentation**. Its value is in giving
future contributors a clear map; the enforcement still lives in the
R-invariants and Principle 4 and iteration cap mechanisms.

---

## §§ 1 – 10 — Carried forward unchanged from v0.2/v0.3

(All scope, output contract, phase pipeline, errors, versioning,
ceilings, R-invariants R1–R16, upstream dependencies, backlog § 9.1
+ § 9.2 + § 9.3, and test plan content carries forward unchanged.)

**Schema unchanged:** `C3B_SESSION_SCHEMA_VERSION` stays at `2`.

```python
C3B_VERSION = "v0.4.PROPOSED"
C3B_SESSION_SCHEMA_VERSION = 2     # UNCHANGED
C3B_IDENTITY_GENERATION = 1
```

---

## § 9.4 — Backlog additions from v0.3 critique walk (NEW — 4 items)

Per Rule 9.2, filed immediately:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| `B-C3B-NEGOTIATION-SUCCESS-ONTOLOGY` | C3b currently defines mechanical correctness (integrity / visibility / agency / guidance / convergence) but no explicit notion of *negotiation success*. Future analytics may optimize the wrong thing (speed-over-quality, finalization-over-satisfaction) without explicit success criteria. v1.x: define ontology — finalized quickly? explored deeply? few regressions? high confidence? stable archetype? low undo? emotional satisfaction? | v0.3 critique pt 4 | v1.x before analytics rollout | M |
| `B-C3B-BACKLOG-TAXONOMY-CLASSIFICATION` | C3b backlog reached 29 items by v0.3 (33 with v0.4 additions). The reviewer correctly notes this is becoming "shadow architecture" — future intended state may diverge from v1.0. Periodically classify items into (a) foundational future architecture, (b) optional enhancements. Prevents present design from under-investing in robustness because backlog assumed inevitable | v0.3 critique pt 5 | Quarterly backlog review | S (per review) |
| `B-C3B-POSITIVE-INTERACTION-DESIGN` | v0.3 excels at preventing bad outcomes (silent regressions, topology drift, hidden conflicts, coercive language, ambiguity, invalid reruns). It is less good at *enabling great user experience*. Risk: C3b becomes safe / auditable / correct but emotionally flat. v1.x: explicit positive interaction design philosophy + research, not only protective governance | v0.3 critique pt 7 | v1.x UX research | L |
| `B-C3B-HUMAN-STATE-MODELING` | R16 (Version Authority) tracks layout state lineage but not human-state evolution within a session — user confidence, preference certainty, fatigue, trust, attachment to prior versions. Especially important if C3b becomes the primary user interaction layer per v0.2 critique pt 13. v1.x: model human-state evolution as first-class signal | v0.3 critique pt 8 | v1.x | L |

---

## § 9.5 — Updated backlog summary (v0.4)

| Category | Count |
|---|---|
| LOCK-mandatory (v0.1 set) | 7 |
| DEFERRED from v0.1 era | 8 |
| DEFERRED from v0.1 critique walk | 8 |
| DEFERRED from v0.2 critique walk | 6 |
| DEFERRED from v0.3 critique walk (NEW v0.4) | 4 |
| **Total tracked** | **33** |

---

## § 11 — v0.1 critique walk verdicts — carried forward from v0.2/v0.3

---

## § 12 — v0.2 critique walk verdicts — carried forward from v0.3 § 12

---

## § 13 — v0.3 critique walk verdicts (NEW v0.4 — audit trail per Rule 7)

The 11 numbered points from the v0.3 critique walk:

| # | Theme | Verdict | Disposition in v0.4 |
|---|---|---|---|
| 1 | § 0.2 still descriptive, not operational | **SPEC-AMENDMENT (consolidates with pt 11)** | § 0.2 EXPLICITLY clarified as descriptive (this spec). |
| 2 | Tier 3 vs Tier 5 may conflict harder | **NO ACTION** | Reviewer says "unavoidable in v1.0." Captured by existing `B-C3B-GRADUATED-FINALIZATION-NUDGES`. |
| 3 | R13 protects structure not experience | **NO ACTION (already filed)** | `B-C3B-EXPERIENTIAL-LAYOUT-INVARIANCE` (v0.3 § 9.3) already covers. |
| 4 | No notion of negotiation success | **BACKLOG** | `B-C3B-NEGOTIATION-SUCCESS-ONTOLOGY` filed § 9.4. |
| 5 | Backlog growth large enough to be architectural signal | **BACKLOG (meta-discipline)** | `B-C3B-BACKLOG-TAXONOMY-CLASSIFICATION` filed § 9.4. |
| 6 | C3b is strategic not pipeline component | **NO ACTION — organizational observation** | Not a spec change. Carry as resourcing awareness. |
| 7 | Spec protective, not great-UX-enabling | **BACKLOG** | `B-C3B-POSITIVE-INTERACTION-DESIGN` filed § 9.4. |
| 8 | Hidden temporal complexity / human-state evolution | **BACKLOG** | `B-C3B-HUMAN-STATE-MODELING` filed § 9.4. |
| 9 | Converging to "constrained co-design OS" | **NO ACTION — framing observation** | Captured by § 0.1 mission framing. |
| 10 | Praise: resisted over-engineering | **NO ACTION** | Strongest endorsement of restraint discipline. |
| **11** | **§ 0.2 descriptive vs normative ambiguity** | **SPEC-AMENDMENT — micro (THE patch)** | **§ 0.2 explicitly clarified as descriptive** (this spec). Hierarchy is a map of existing enforcement, not its own authority. |

**Totals:** 1 SPEC-AMENDMENT (micro, consolidates pts 1+11) + 4 backlog
+ 6 NO ACTION = 11 of 11 verdicted.

### 13.1 — Honest meta-comment

The v0.3 critique was **endorsement-with-one-clarification**. The
reviewer explicitly said: *"This is the first C3b version that
genuinely feels: LOCK-ready"* and identified ONLY pt 11 (§ 0.2
ambiguity) as a genuine LOCK-boundary item. v0.4 surgically addresses
that one ambiguity and files the other tensions as backlog.

**Trajectory:**
- v0.1 critique → v0.2: 6 SPEC-AMENDMENTs + 4 R-invariants
- v0.2 critique → v0.3: 1 SPEC-AMENDMENT + 0 R-invariants
- v0.3 critique → **v0.4: 1 micro-patch + 0 R-invariants** ← convergence floor

C3b reached the convergence floor in **3 critique rounds** — same as C17.
Both shipped with substantive structural-then-clarifying-then-LOCK
trajectories.

---

## § 14 — Three-check protocol (Rule 10.6) — at LOCK time

(To be filled at LOCK ratification.)

---

## § 15 — LOCK adjudication request (Rule 8)

**This document is C3b v0.4 LOCKED. LOCKED by Ramalingam at S50 close.**

For Ramalingam to LOCK v0.4, please confirm:

1. **§ 0.2 explicitly DESCRIPTIVE** (this spec) — hierarchy maps
   existing enforcement, not its own governance authority. No new
   tests, no new enforcement, no new invariants.
2. **§ 9.4 4 new backlog items** filed.
3. **§ 13 11/11 v0.3-critique verdicts** — audit trail complete.
4. **No new R-invariants** — R1–R16 stand.
5. **Schema unchanged** — `C3B_SESSION_SCHEMA_VERSION` stays at 2.

If yes: **state "C3b v0.4 LOCKED"** and the C3b spec sequence is
complete. Track 3 canonical reaches **19 of 19 sub-components LOCKED**.

---

**END OF C3b v0.4 LOCKED — PENDING Ramalingam LOCK**
