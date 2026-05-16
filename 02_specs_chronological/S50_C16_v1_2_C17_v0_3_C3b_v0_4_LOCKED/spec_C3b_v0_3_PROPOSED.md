# C3b — Post-Layout Trade-off Negotiation
## Spec v0.3 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor:** v0.2 PROPOSED (S50 close).
**Composed from:** v0.2 PROPOSED + second critique walk findings (S50 → S51).
**Session:** S50 close.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone.

> **Per Rule 9.4:** Critiques arriving between PROPOSED and LOCK remain
> patch-eligible.

---

## § 0 — Composition rationale (v0.3)

v0.2 PROPOSED was a moderate restructure (6 SPEC-AMENDMENTs from v0.1
critique, including 4 new R-invariants R13–R16). The second critique
walk on v0.2 yielded 13 numbered concerns. Verdict tally:

- **1 SPEC-AMENDMENT** adopted in v0.3 (small — organizes existing
  implicit priorities; NO new invariants)
- **0 new R-invariants** — deliberate restraint per critique pt 11
  meta-warning
- **6 new BACKLOG items** filed per Rule 9.2
- **6 NO ACTION** (1 meta-warning honored, 2 already-filed, 1
  unresolvable, 2 praise)

**The critique's most important point was its meta-warning** (pt 11):
*"v0.3 should probably emphasize architectural restraint, not maximal
patching. Not every surfaced tension should become a new invariant."*

v0.3 honors this. The single SPEC-AMENDMENT (**§ 0.2 Negotiation
Philosophy Hierarchy**) is not a new constraint — it is an explicit
organization of priorities R13–R16 + iteration cap + MutationEnvelope
+ Principle 4 already encode implicitly. It clarifies governing
hierarchy without adding governance machinery.

This pattern mirrors C17 v0.2 → v0.3 (which produced 4 surgical
patches and was followed by 0-patch LOCK round). C3b's trajectory:

| Round | SPEC-AMENDMENTs | New R-invariants | Backlog |
|---|---|---|---|
| v0.1 critique → v0.2 | 6 (4 major + 2 small) | 4 (R13–R16) | 8 |
| **v0.2 critique → v0.3 (this)** | **1 small** | **0** | **6** |

The 6 → 1 SPEC-AMENDMENT drop and 4 → 0 new-invariant drop is the
convergence signal. v0.3 is positioned as the LOCK candidate.

---

## § 0.1 — Mission framing — carried forward unchanged from v0.2

(v0.1's § 0.1 framing: *"C3b's purpose: once user has seen the three
ranked layouts, surface specific layout-grounded tweaks; user-driven
mutation negotiation, NOT a layout regenerator; bigger scope than
C3a because operating on geometry"* — preserved.)

---

## § 0.2 — Negotiation Philosophy Hierarchy (NEW v0.3 — critique pt 9)

Per critique pt 9: v0.2 encoded 5 implicit governing priorities
without making their hierarchy explicit. v0.3 surfaces the hierarchy
so future evolution + future critique rounds know what wins when
priorities conflict.

**The hierarchy (highest → lowest authority):**

### Tier 1 — Architectural integrity (NON-NEGOTIABLE)

System blocks, no user override. Encoded by:
- **R13 Topology Invariance** — MEDIUM tweaks must preserve C5 topology
- **NBC compliance** (inherited from upstream C7, C9, C15)
- **Structural feasibility** (inherited from C7 + C12)
- **Hard constraints** in C15's ProblemReport

If a tweak would violate Tier 1, C3b refuses. The user cannot accept
their way past an NBC minimum bath area or a structural-grid violation.
The `MutationEnvelope` (§ 2.8) communicates the block and routes the
user to the appropriate upstream layer (C3a brief change, etc.).

### Tier 2 — Honest visibility (NON-CIRCUMVENTABLE BY DEFAULT)

System surfaces what changed, never hides. Encoded by:
- **R14 Regression Detection** — increase in critical-tier checks surfaces
- **R15 Multi-Tweak Compatibility** — conflicts surface with resolution options
- **Q3 Level B logging** — full option set always logged
- **R16 Version Authority** — current layout state is always identifiable

The user can override Tier 2 outcomes (e.g., accept a regression),
but only after being explicitly shown the outcome. C3b never silently
suppresses a regression to make the user happier.

### Tier 3 — User agency (PRINCIPLE 4)

Within Tier 1 + Tier 2 constraints, the user has the final choice.
Encoded by:
- **Principle 4 user intervention checkpoints** (Design Principles v3.1)
- **Phase ε branching logic** (accept / reject / no_action / finalize /
  kickback / abandon)
- **Always-available undo** (R14's surfaced revert tweak, R15's revert
  option, manual rejection of any tweak)

The user is not coerced into any specific tweak path. C3b proposes
options; the user decides.

### Tier 4 — System guidance (NON-BINDING, ADVISORY)

System helps user reason about choices without imposing them. Encoded by:
- **MutationEnvelope** (§ 2.8) — structured pathway suggestions
- **R2 advisory tone** — banned-phrase lint on all user-facing text
- **`recommendation_flag`** — structural marker (suggested / optional /
  alternative), NOT authoritative ranking
- **TransparencyTriple impacts** — cost / space / comfort with derivation

The user can ignore guidance entirely. C3b never says "you should."

### Tier 5 — Convergence support (USER WELLBEING)

System protects user from fatigue / decision paralysis / runaway
exploration. Encoded by:
- **Iteration cap** (default 5, hard ceiling 7)
- **MAX_REPRESENT_COUNT = 2** (don't re-suggest same rejected tweak)
- **MAX_TWEAKS_PER_LAYOUT = 6** (choice-paralysis threshold)
- **Future** `B-C3B-GRADUATED-FINALIZATION-NUDGES` (v1.x graduated
  encouragement)

Tier 5 protects the user's cognitive load; it does not constrain
correctness or agency.

### Resolution rules when tiers conflict

- **Tier 1 always wins** — no exceptions. A tweak that violates topology
  invariance or NBC is blocked even if every higher-tier consideration
  argues for it.
- **Tier 2 overrides Tier 3** in surfacing, not in execution — i.e.,
  the regression IS shown to the user, but the user MAY still proceed
  after seeing it.
- **Tier 3 overrides Tier 4 and Tier 5** — if the user explicitly
  declines guidance, system respects that. If user explicitly requests
  to push past iteration cap, system surfaces a `MutationEnvelope`
  routing to step-back-to-brief but does not force the user out.
- **Tier 4 is never override-binding** — guidance is informational only.

**Rationale:** v0.2 implicitly had this hierarchy embedded in R13/R14/
R15/R16 + iteration cap + advisory tone + MutationEnvelope, but
nowhere stated. Future critique rounds and future contributors will
need this hierarchy to resolve conflicts between competing concerns
without re-litigating the original design decisions. § 0.2 is
documentation of existing design choice, not a new constraint.

**No new R-invariants** — Tier 1's R13 + Tier 2's R14/R15 + Tier 3's
Principle 4 already enforce the hierarchy mechanically. § 0.2 just
makes the layering legible.

---

## §§ 1 – 10 — Carried forward unchanged from v0.2

All of v0.2 § 1 (scope + § 1.4 applicability boundary), § 2 (output
contract — `TradeoffSession` / `TweakOptionSet` / `TweakOption` /
formalized `SubsetRerunRequest` / `TopologyInvarianceResult` /
`CompatibilityAssertion` / `MutationEnvelope` / `ResolvedSelection`),
§ 3 (6-phase pipeline with reworked Phase β step 4), § 4 (error tiers),
§ 5 (versioning), § 6 (hard ceilings), § 7 (R-invariants R1–R16),
§ 8 (upstream dependencies), § 9 (backlog § 9.1 + § 9.2), and § 10
(test plan) carry forward unchanged into v0.3.

**One small versioning note:** `C3B_SESSION_SCHEMA_VERSION` stays at
`2` (same as v0.2). v0.3 adds NO dataclass schema changes (§ 0.2 is
documentation-level, not contract-level).

```python
C3B_VERSION = "v0.3.PROPOSED"
C3B_SESSION_SCHEMA_VERSION = 2     # UNCHANGED from v0.2
C3B_IDENTITY_GENERATION = 1
```

---

## § 9.3 — Backlog additions from v0.2 critique walk (NEW — 6 items)

Per Rule 9.2, filed immediately:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| `B-C3B-EXPERIENTIAL-LAYOUT-INVARIANCE` | R13 (topology invariance) is correct but coarse. C5 topology equality doesn't imply architectural identity preservation — within "central_spine" a layout can preserve topology while radically changing circulation quality, room hierarchy, privacy zoning, daylight behavior, furniture usability, experiential flow. v1.x: distinguish topology invariance from *experiential* invariance. Likely defines per-archetype experiential signatures and detects drift independently of R13 | v0.2 critique pt 1 | v1.x | L |
| `B-C3B-IMPACT-DRIFT-DETECTION` | `SubsetRerunRequest.downstream_impact_set` (§ 2.4.1) declares impacts upfront, but real systems contain emergent dependencies. Orchestrator should record contract drift when downstream observes unexpected changes outside the declared set. Protects against "declarative overconfidence" | v0.2 critique pt 3 | Orchestrator development | M |
| `B-C3B-MULTIDIMENSIONAL-REGRESSION-METRIC` | R14 currently fires only on increase in critical-tier ProblemReport checks. Layout degradation is more dimensional — a tweak can reduce critical issues while worsening comfort, circulation, privacy, experiential coherence. v1.x: extend regression detection to multi-dimensional degradation tracking | v0.2 critique pt 4 | Post-launch + metric calibration | L |
| `B-C3B-FULL-SESSION-VALIDATION-PASS` | R15 does pairwise compatibility checks but can miss emergent N-way conflicts (A+B fine, B+C fine, A+C fine, A+B+C impossible). Before the formal dependency graph (`B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH`), implement periodic full-session validation passes after N≥3 accepted tweaks. Pragmatic intermediate step | v0.2 critique pt 5 | v1.x | M |
| `B-C3B-GOVERNANCE-LAYERED-DOCS` | C3b state machine is becoming complex (tweak generation + severity computation + rerun orchestration + compatibility validation + regression detection + negotiation history + mutation lineage + undo semantics + user agency + advisory language + topology preservation). Eventually split into layered subsystems: (a) negotiation logic, (b) mutation validation, (c) rerun orchestration contracts, (d) user-facing advisory policy. Mirrors C17 v0.3 backlog | v0.2 critique pts 8, 11 | v1.x reorganization | M |
| `B-C3B-ARCHETYPE-DRIFT-DETECTION` | After N tweaks, layout may technically preserve topology + pass all invariants + avoid critical regression, yet no longer resemble the original archetype the user selected (Cost Efficient / Everyday Living / Premium Design). R13 prevents topology drift; this backlog item adds *archetype* drift detection — compares current layout signature against original archetype's defining characteristics, flags excessive drift | v0.2 critique pt 10 | v1.x | M |

---

## § 9.4 — Updated backlog summary (v0.3)

| Category | Count |
|---|---|
| LOCK-mandatory (v0.1 set) | 7 |
| DEFERRED from v0.1 era | 8 |
| DEFERRED from v0.1 critique walk | 8 |
| DEFERRED from v0.2 critique walk (NEW v0.3) | 6 |
| **Total tracked** | **29** |

---

## § 11 — v0.1 critique walk verdicts — carried forward from v0.2 § 11

(All 13 v0.1 verdicts as recorded in v0.2 § 11 stand.)

---

## § 12 — v0.2 critique walk verdicts (NEW v0.3 — audit trail per Rule 7)

The 13 numbered points from the v0.2 critique walk:

| # | Theme | Verdict | Disposition in v0.3 |
|---|---|---|---|
| 1 | R13 topology invariance too coarse | **BACKLOG** | `B-C3B-EXPERIENTIAL-LAYOUT-INVARIANCE` filed § 9.3. v1.x distinguishes topology from experiential invariance. |
| 2 | Severity heuristically fragile | **NO ACTION (already filed)** | `B-C3B-FORMAL-MUTATION-ENVELOPE-GRAPH` (v0.2 § 9.2) already covers — reviewer confirms it's the solution. |
| 3 | SubsetRerunRequest declarative overconfidence | **BACKLOG** | `B-C3B-IMPACT-DRIFT-DETECTION` filed § 9.3 — orchestrator records contract drift. |
| 4 | R14 metric too narrow (only critical-count) | **BACKLOG** | `B-C3B-MULTIDIMENSIONAL-REGRESSION-METRIC` filed § 9.3 — v1.x extends regression to comfort/circulation/privacy dimensions. |
| 5 | R15 pairwise misses emergent N-way conflicts | **BACKLOG (pragmatic intermediate)** | `B-C3B-FULL-SESSION-VALIDATION-PASS` filed § 9.3 — full-session re-validation at N≥3 accepted tweaks, before formal graph. |
| 6 | MutationEnvelope creates expectation pressure | **NO ACTION — unresolvable** | Reviewer says "not solvable fully." Captured by § 0.1 mission framing. |
| 7 | Linear version authority feels artificial | **NO ACTION (already filed)** | `B-C3B-MUTATION-LINEAGE-AND-BRANCHING` (v0.2 § 9.2) already covers. |
| 8 | C3b becoming complex state machine | **BACKLOG** | `B-C3B-GOVERNANCE-LAYERED-DOCS` filed § 9.3 — mirrors C17 v0.3 precedent. |
| **9** | **No formal negotiation philosophy hierarchy** | **SPEC-AMENDMENT (small) — the only patch** | **§ 0.2 Negotiation Philosophy Hierarchy** (NEW) — organizes 5 implicit priorities (architectural integrity / honest visibility / user agency / system guidance / convergence support) into explicit Tier 1–5 hierarchy with conflict-resolution rules. NO new invariants. |
| 10 | Session-wide identity / archetype drift | **BACKLOG** | `B-C3B-ARCHETYPE-DRIFT-DETECTION` filed § 9.3 — v1.x detects when layout no longer resembles chosen archetype. |
| 11 | Governance density increasing fast | **NO ACTION — meta-warning honored** | This IS the meta-instruction. Honored by NOT adding R17–R20 even though tensions surfaced. v0.3 added 0 invariants. |
| 12 | Praise: controlled, auditable, reversible event | **NO ACTION** | Strongest endorsement of v0.2 |
| 13 | Praise: human-AI co-design protocol | **NO ACTION (long-term observation)** | Captured by § 0.1 mission framing |

**Totals:** 1 SPEC-AMENDMENT + 6 backlog items + 6 NO ACTION = 13 of 13
verdicted.

### 12.1 — Honest meta-comment

The v0.2 critique surfaced **mostly governance-density tensions**,
not architectural defects. The reviewer themselves explicitly warned
against compliance-patching every tension. v0.3 honors that:

- **6 → 1 SPEC-AMENDMENT** drop (vs v0.2's 6) — sharper convergence than C17.
- **4 → 0 new R-invariants** drop — deliberate restraint.
- **No restructure.** v0.3 is mostly v0.2 with § 0.2 added and audit trail.

The reviewer's deepest insight: *"C3b is the first formal human-AI
negotiation layer inside BuildemUp."* This framing is now embedded
in § 0.2's hierarchy — Tier 3 (User Agency) explicitly authoritative
within Tier 1+2 constraints, Tier 4 (System Guidance) explicitly
non-binding. The component's role is **structured co-design**, not
authoritative architecture decisions on behalf of the user.

§ 0.2 is the most important v0.3 addition not because it constrains
new behavior, but because it makes the *governing logic* of all
existing constraints legible. Future contributors can resolve
conflicts using the Tier 1–5 hierarchy without re-litigating the
original design decisions.

---

## § 13 — Test plan additions (v0.3 — minimal)

v0.2's ~300-test target stands. v0.3 adds **one small test file**
verifying § 0.2 hierarchy is correctly enforced by existing
invariants (no new code, just documentation-level validation):

| New test file | Count | Purpose |
|---|---|---|
| `test_c3b_negotiation_philosophy_hierarchy.py` | ~8 (NEW v0.3) | Verify that when priorities conflict in test scenarios, the documented Tier 1–5 resolution rules are honored by existing R13/R14/R15/R16 + iteration cap + advisory tone code paths. No new logic — confirms § 0.2 is descriptive, not prescriptive |

**Revised v1.0 LOCK test target: ~308 tests.**

---

## § 14 — Three-check protocol (Rule 10.6) — at LOCK time

(To be filled at LOCK time per the C15/C16/C17 pattern.)

---

## § 15 — Convergence assessment

The C3b spec sequence convergence:

| Round | SPEC-AMENDMENTs | New R-invariants | Backlog | Note |
|---|---|---|---|---|
| v0.1 critique → v0.2 | 6 (4 major + 2 small) | 4 (R13–R16) | 8 | Major architectural strengthening |
| **v0.2 critique → v0.3** | **1 small** | **0** | **6** | Philosophy organization, no new structure |
| v0.3 critique (predicted) | 0 | 0 | ≤ 3 | Convergence floor |

C3b is converging faster than C17 (which took 3 rounds: 12 → 4 → 0).
C3b has hit **6 → 1 → predicted 0** across two rounds.

**A v0.4 round is warranted only if a third critique surfaces a
genuinely actionable spec change** — not just sociotechnical tensions
(v0.2's critique already established that surfaced tensions are not
patches). Otherwise **v0.3 should LOCK.**

---

## § 16 — LOCK adjudication request (Rule 8)

**This document is C3b v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication.**

For Ramalingam to LOCK v0.3, please confirm:

1. **§ 0.2 Negotiation Philosophy Hierarchy** (NEW) — 5-tier hierarchy
   organizing existing implicit priorities (architectural integrity /
   honest visibility / user agency / system guidance / convergence
   support) with explicit conflict-resolution rules. NO new
   invariants. Documentation-level clarification.
2. **§ 9.3 6 new backlog items** — all filed.
3. **§ 12 13/13 v0.2-critique verdicts** — audit trail complete.
4. **No new R-invariants** — deliberately restrained per critique pt 11
   meta-warning.
5. **Schema unchanged** — `C3B_SESSION_SCHEMA_VERSION` stays at 2.

If yes to all: **state "C3b v0.3 LOCKED"** — implementation begins per
§ 9.1 LOCK-mandatory backlog (phase implementations + ~308 tests +
subset-rerun orchestrator contract + advisory-tone lint + tweak-
generation coverage calibration + SQLite WAL persistence + Q3 Level B
audit replay tests).

If corrections needed: state which sections need patches; I'll
compose v0.4 PROPOSED.

**My recommendation: LOCK v0.3.**

Reasoning:
- The v0.2 critique was largely endorsement-with-tensions-surfaced
  rather than fix-this. Only 1 of 13 points became a genuine spec
  amendment.
- The reviewer's meta-warning (pt 11) explicitly cautions against
  more patching.
- Convergence delta is 6 → 1 amendments — strongest possible LOCK
  signal short of zero.
- Following the C17 trajectory (12 → 4 → 0), C3b is currently at the
  1-patch round, which is the convergence floor.
- All 6 v0.3-critique tensions are genuinely future-work (filed as
  backlog), not present-defects.

If a v0.3 critique walk happens, expect 0 SPEC-AMENDMENTs + a few
backlog items + LOCK (mirroring C17 v0.3's pattern).

---

**END OF C3b v0.3 PROPOSED — PENDING Ramalingam LOCK**
