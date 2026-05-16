# Reviewer Critique Walk: C11A Amendment v1.4 PROPOSED → drove v1.5 PROPOSED

**Source**: external reviewer feedback received during S40-continuation, post-v1.4 PROPOSED.
**Action taken**: Claude's analysis of these 15 items produced v1.5 PROPOSED (file 99 in 02_specs_chronological/).
**Reviewer verdict at end**: "REAL PRE-LOCK ISSUES REMAINING: 1. `affected_floor_set()` semantic overload. 2. fairness wording overstated. Everything else is plausibly backlog-grade. Convergence assessment: VERY HIGH. Most likely trajectory: v1.5 PROPOSED, then LOCK."

---

# C11A Amendment v1.4 PROPOSED — Genuine Drawbacks + Concrete Solutions

--------------------------------------------------
DRAWBACK 1 — `affected_floor_set()` API SEMANTIC OVERLOAD
--------------------------------------------------

Problem:
`target_floor_label` means two different things:
- per-floor operators → directly-mutated floor
- M8 → destination master floor

This creates semantic ambiguity and future orchestration risk.

Failure modes:
- passing old-master instead of new-master
- assuming target_floor_label == only directly-mutated floor
- accidental misuse in future operators

Why it matters:
This is not naming polish.
It is a contract ambiguity in a foundational orchestration abstraction.

Solution:
Split semantics explicitly.

Recommended patch:

def affected_floor_set(
    operator,
    source,
    *,
    direct_floor_label: str | None = None,
    new_master_floor_label: str | None = None,
) -> frozenset[FloorImpact]:

Alternative:
- specialize M8 handling into a separate helper entirely

Best long-term option:
Separate dwelling-wide operators from per-floor operators at the type-contract level.

Severity:
PRE-LOCK

--------------------------------------------------
DRAWBACK 2 — FAIRNESS CLAIMS ARE MATHEMATICALLY OVERSTATED
--------------------------------------------------

Problem:
Spec says:
"both axes uniform under truncation"

But actual property is:
- imbalance bounded by ≤ 1
- not true uniformity

Example:
5 operators
3 floors
slot_count = 7

Distribution becomes:
Operators:
2,2,1,1,1

Floors:
2,3,2

No starvation exists anymore,
but truncation still advantages early partial-round entries.

Why it matters:
The algorithm is good.
The proof wording is inaccurate.

Solution:
Replace wording:

BAD:
- "uniform under truncation"

GOOD:
- "bounded imbalance ≤ 1 under truncation"
- "starvation-free"
- "asymptotically uniform"

Add explicit fairness theorem wording.

Severity:
Minor but real correctness-documentation issue.

--------------------------------------------------
DRAWBACK 3 — PARTIAL-ROUND POSITIONAL ADVANTAGE STILL EXISTS
--------------------------------------------------

Problem:
Even after bipartite interleaving,
earlier operators still gain slight exposure advantage
inside incomplete final rounds.

Not starvation.
Not severe bias.
But deterministic ordering still leaks priority.

Why it matters:
Large evolutionary runs may subtly over-explore early-round combinations.

Solution Options:

OPTION A (Recommended for v1.x):
Accept bounded imbalance as sufficient.
Document explicitly.

OPTION B (Future):
Stable-shuffle rounds using source_signature.

OPTION C (Future):
Round-start offset rotates by generation.

Example:

round_offset = generation % num_operators

Then rotate operator iteration start.

Filed naturally under:
- B-C11A-13
- future exploration-policy work

Severity:
Not pre-LOCK.

--------------------------------------------------
DRAWBACK 4 — FAMILY-ID SEMANTICS DIVERGE FROM WRAPPER SEMANTICS
--------------------------------------------------

Problem:
Wrapper/signature semantics preserve tuple order.
Family aggregation intentionally canonicalizes tuple order away.

This creates semantic divergence.

Example:
- signatures distinguish tuple-order ancestry
- family IDs intentionally collapse tuple-order variance

Future maintainers may incorrectly assume:
family identity == structural identity

It does not.

Why it matters:
Potential future cache/family/equality confusion.

Solution:
Add explicit semantic distinction section:

"Family-ID canonicalization intentionally discards tuple order.
Wrapper identity and canonical signatures do NOT.
These systems serve different purposes."

Also:
rename "family identity" internally to:
- "slot-allocation family"
or
- "exploration family"

to reduce identity confusion.

Severity:
Minor but important conceptual clarification.

--------------------------------------------------
DRAWBACK 5 — CYCLIC COVERAGE TEST HAS OFF-BY-ONE REASONING
--------------------------------------------------

Problem:
Spec incorrectly says:
- "3 generations" for a 3-floor dwelling

But:
eligible target count = total floors - current master

For:
3 floors
1 current master

Coverage cycle size = 2, not 3.

Why it matters:
Test spec currently mismatches actual algorithm.

Solution:
Correct wording:

"Apply M8 across N distinct generations,
where N = eligible target count."

Add explicit formula:

N = len(eligible_targets)

Severity:
Minor test-spec issue.

--------------------------------------------------
DRAWBACK 6 — ROOT-CAUSE PRECISION IS PARTIALLY OVERSTATED
--------------------------------------------------

Problem:
`orchestration_state_drift:mfwzpN`
improves taxonomy,
but invariant-level failures still collapse many root causes together.

Example:
mfwzp5 may originate from:
- C9 ignoring master flag
- stale wrapper reuse
- duplicate floor replacement
- cascade corruption
- bad floor mutation

Spec wording occasionally implies stronger diagnosability than system actually provides.

Why it matters:
Future telemetry/debugging expectations may become unrealistic.

Solution:
Clarify taxonomy semantics:

"Invariant-specific drift variants narrow failure class
but do NOT uniquely identify root cause."

Future improvements:
- generation provenance
- operator provenance
- floor ancestry tracing
- mutation-chain metadata

Already overlaps:
- B-C11A-8
- B-C11A-14

Severity:
Minor.

--------------------------------------------------
DRAWBACK 7 — CYCLIC M8 TARGET SELECTION HAS EVOLUTIONARY PERIODICITY
--------------------------------------------------

Problem:
Algorithm:

(generation + operator_index) % N

creates deterministic cycles.

Generations:
g, g+N, g+2N
all hit same target.

Why it matters:
Future NSGA-II orchestration may synchronize exploration patterns across population members.

Potential outcome:
- phase-locked search behaviour
- synchronized topology exploration
- reduced diversity

Solution:
Stable-shuffle eligible targets per candidate.

Recommended future algorithm:

permutation = stable_shuffle(targets, source_signature)
index = generation % N

Benefits:
- preserves determinism
- preserves coverage
- breaks resonance synchronization

Already correctly filed as:
B-C11A-13

Severity:
Future-scale issue only.

--------------------------------------------------
DRAWBACK 8 — M8 STILL ASSUMES ONLY DIRECT MASTER-FLIP EFFECTS
--------------------------------------------------

Problem:
M8 currently assumes:
only old-master and new-master floors require regeneration.

Future cross-floor constraints break this assumption.

Examples:
- vertical plumbing stacks
- circulation coupling
- structural column alignment
- stair adjacency
- acoustic constraints

Indirect invalidation becomes real.

Why it matters:
Future architectural constraints may silently invalidate untouched floors.

Solution:
v1.4 already partially solved this correctly via `FloorImpact`.

Remaining work:
populate indirect impacts.

Example future extension:

FloorImpact(
    label="second",
    kind="indirect",
    requires_cascade=False,
    requires_validation_only=True,
)

This is one of v1.4's strongest architectural choices.

Remaining work belongs to:
B-C11A-7

Severity:
Future architectural-scale issue.

--------------------------------------------------
DRAWBACK 9 — PROPERTY TESTS STILL CANNOT PROVE EVOLUTIONARY STABILITY
--------------------------------------------------

Problem:
100-example property tests + one 50-step chain
are still small relative to combinatorial state space.

Rare failures may survive CI.

Examples:
- lineage drift accumulation
- stale floor reuse
- cache aliasing edge cases
- reconstruction divergence
- long-cycle exploration anomalies

Why it matters:
Multi-floor orchestration is combinatorially explosive.

Solution:
Nightly stress fuzzing.

Recommended:
- 1000+ examples
- 100+ step chains
- randomized operator schedules
- replay-seed persistence

Already correctly filed as:
B-C11A-12

Severity:
Not pre-LOCK.

--------------------------------------------------
DRAWBACK 10 — SIGNATURE RECURSION COST SCALES WITH FLOOR COUNT
--------------------------------------------------

Problem:
Multi-floor signatures recurse into all per-floor signatures repeatedly.

Complexity:
O(num_floors × signature_depth)

This impacts:
- cache identity
- lineage
- orchestration
- repeated comparisons

Why it matters:
Large evolutionary runs may repeatedly recompute identical signatures.

Solution:
Memoized immutable signatures.

Recommended:
- lazy cached per-floor signature
- Merkle-style aggregation
- structural sharing

Example:

cached_signature: str | None

computed once per immutable wrapper.

Already correctly filed as:
B-C11A-15

Severity:
Performance issue only.

--------------------------------------------------
DRAWBACK 11 — WRAPPER REBUILDING MAY CREATE ALLOCATION CHURN
--------------------------------------------------

Problem:
Repeated:

with_floor_replaced()

causes repeated immutable wrapper reconstruction.

Long runs may allocate heavily.

Why it matters:
Potential performance bottleneck under large populations.

Solution:
Future optimization options:
- batched replacement
- builder-style assembly
- persistent immutable structures
- structural sharing

Already filed as:
B-C11A-9

Severity:
Performance issue only.

--------------------------------------------------
DRAWBACK 12 — ORCHESTRATION POLICIES ARE STILL HARD-WIRED
--------------------------------------------------

Problem:
Policies currently embedded directly inside orchestrator:
- floor scheduling
- M8 targeting
- truncation policy

Not strategy-based.

Why it matters:
Future experimentation becomes harder:
- weighted exploration
- adaptive exploration
- NSGA-II coordination
- A/B policy testing

Solution:
Extract strategy interfaces:

FloorSelectionPolicy
M8TargetPolicy
AttemptBudgetPolicy

Current inline approach is acceptable for v1,
but future coordination complexity will grow.

Already correctly filed as:
B-C11A-11

Severity:
Architecture-evolution concern only.

--------------------------------------------------
DRAWBACK 13 — GENERATION SEMANTICS ARE NOW CRITICAL GLOBAL STATE
--------------------------------------------------

Problem:
Generation now influences:
- M8 target selection
- scheduling determinism
- exploration trajectory

But generation ownership/lifecycle is only lightly specified.

Why it matters:
Incorrect generation advancement policy may create:
- replay mismatch
- exploration duplication
- cache confusion
- synchronization artefacts

Solution:
Formalize generation contract.

Add:
- generation lifecycle ownership
- monotonicity guarantees
- replay semantics
- reset semantics

Potential future lineage metadata:

generation: int
operator_index: int

Already overlaps:
- B-C11A-14

Severity:
Medium future-governance issue.

--------------------------------------------------
DRAWBACK 14 — MULTI-FLOOR ORCHESTRATION GREATLY INCREASES STATE-SPACE SIZE
--------------------------------------------------

Problem:
Search space exploded from:
- operators
to:
- operators × floors × generations × cascade states

Why it matters:
Potential:
- slower convergence
- more invalid branches
- evolutionary dilution

v1.4 improves fairness,
but fairness also increases exploration breadth.

Solution:
Future:
- adaptive quotas
- exploration weighting
- invalidity-aware throttling
- score-guided scheduling

Already overlaps:
- B-C11A-5
- B-C11A-10
- C11b future work

Severity:
Expected evolutionary-system tradeoff.

--------------------------------------------------
DRAWBACK 15 — DETECTION SYSTEMS ARE NOW MIXED (MARKER + NAME-BASED)
--------------------------------------------------

Problem:
Multi-floor uses marker-attribute detection.
Single-floor still partially uses name-based detection.

This creates inconsistent detection philosophy.

Why it matters:
Future maintainers may accidentally mix:
- marker semantics
- type-name semantics
- Protocol semantics

leading to inconsistent orchestration behaviour.

Solution:
Project-wide detection unification.

Preferred long-term:
- Protocol/ABC approach
OR
- universal marker-based detection

Already partially addressed via:
B-C11A-6

Severity:
Minor architecture consistency issue.

--------------------------------------------------
OVERALL ASSESSMENT
--------------------------------------------------

v1.4 is dramatically stronger than:
- v1.1
- v1.2
- v1.3

Most severe algorithmic defects are now genuinely solved.

The remaining drawbacks are mostly:
- contract precision
- scalability
- evolutionary-governance
- future extensibility
- performance optimization
- deterministic exploration nuance

REAL PRE-LOCK ISSUES REMAINING:
1. `affected_floor_set()` semantic overload
2. fairness wording overstated

Everything else is plausibly backlog-grade.

Convergence assessment:
VERY HIGH.

Most likely trajectory:
- v1.5 PROPOSED
- then LOCK.
