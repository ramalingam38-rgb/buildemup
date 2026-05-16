# Reviewer Critique Walk: C11A Amendment v1.5 PROPOSED → drove v1.6 PROPOSED → LOCKED

**Source**: external reviewer feedback received during S40-continuation, post-v1.5 PROPOSED.
**Action taken**: Claude's analysis of these 12 items produced v1.6 PROPOSED (file 100 in 02_specs_chronological/), which Ramalingam then LOCKED at file 101.
**Reviewer verdict at end**: "PRETTY CLOSE TO LOCK-WORTHY for v1 operational scope. But: not yet 'future-proof at NSGA-II scale'."

---

GENUINE DRAWBACKS / RISKS / FAILURE MODES + CONCRETE SOLUTIONS
C11A SPEC AMENDMENT v1.5 PROPOSED — Multi-floor pipeline rework
(B-NEW-T3 enabler #4 of 4)

========================================================
1. FAIRNESS GUARANTEE IS STILL NOT TRUE GLOBAL FAIRNESS
========================================================

Problem:
v1.5 correctly weakens the wording from "uniform under truncation"
to "bounded imbalance ≤ 1", but the implementation still has a real
deterministic positional advantage:

    earlier operators in round-major iteration order
    receive the ceiling-share during partial rounds.

Example:
    n_ops=5, S=7
    operator distribution:
        {2,2,1,1,1}

So although starvation is solved, the exploration pressure is still
systematically skewed toward lower-order operators whenever:
    S mod n_ops != 0

Why this matters:
In long-running evolutionary systems, even a +1 deterministic advantage
per generation compounds heavily over thousands of generations.
Earlier operators can dominate mutation lineage ancestry and indirectly
shape topology-family diversity.

Current spec issue:
The spec acknowledges the issue but understates long-term cumulative bias.
"Bounded imbalance ≤ 1" is mathematically true locally per generation,
but does NOT imply long-term fairness unless:
    - operator ordering rotates
    OR
    - slot offsets rotate
    OR
    - stable shuffle exists

Solution:
Promote one of the backlog fairness breakers into v1.x before scaling:
    Option A:
        rotate operator start index by generation

            start = generation % n_ops

    Option B:
        stable-shuffle operators using source_signature

    Option C:
        per-generation cyclic operator offset

This preserves determinism while removing perpetual privilege for
low-index operators.

Severity:
MEDIUM-HIGH
Not a correctness bug.
Potential long-term search-diversity degradation bug.


========================================================
2. CYCLIC M8 TARGETING CAN CAUSE EVOLUTIONARY RESONANCE
========================================================

Problem:
The deterministic cyclic selection:

    sorted_targets[(generation + operator_index) % N]

guarantees coverage, but creates strict periodicity.

For any candidate:
    generation g
    generation g+N
    generation g+2N

all select identical targets.

Why this matters:
Once NSGA-II or population-based evolution lands,
many candidates sharing generation counters can synchronize.

This creates:
    - phase-locking
    - synchronized topology pressure
    - exploration resonance
    - correlated search trajectories

This is a real evolutionary-search pathology.

The spec acknowledges it but defers to B-C11A-13.

Why this is risky:
This issue is not hypothetical.
Deterministic cyclic policies are known to create population coupling
in evolutionary systems.

Coverage != diversity.

Solution:
Replace deterministic cycle with:
    stable_shuffle(targets, source_signature)
    then generation % N

This preserves:
    - determinism
    - coverage guarantees
    - replay reproducibility

while breaking:
    - population synchronization
    - target periodicity resonance

Severity:
HIGH once NSGA-II lands.
LOW-MEDIUM before population search exists.


========================================================
3. GENERATION CONTRACT IS UNDER-ENFORCED
========================================================

Problem:
v1.5 formalizes generation semantics but explicitly does NOT enforce:
    - monotonicity
    - uniqueness
    - lineage consistency
    - replay correctness

This creates dangerous hidden assumptions:
    - callers can reuse generations accidentally
    - sharded search can collide
    - replay debugging can silently diverge
    - lineage determinism can drift

Current state:
C11a behavior correctness partially depends on external caller discipline.

Why this matters:
Generation is no longer cosmetic.
It directly affects:
    - M8 target selection
    - attempt scheduling
    - exploration trajectory

Therefore generation is effectively part of orchestration state.

Solution:
Add optional validation mode:

    validate_generation_contract=True

with:
    - monotonicity checks
    - duplicate-generation detection
    - lineage-generation assertions
    - replay trace verification hooks

OR

embed generation provenance directly into lineage metadata earlier.

Severity:
HIGH for debugging/reproducibility.
MEDIUM for production behavior.


========================================================
4. CACHE IDENTITY VS EXPLORATION IDENTITY IS STILL FRAGILE
========================================================

Problem:
The spec carefully separates:
    Tier 1 structural determinism
    Tier 2 scheduling determinism
    Tier 3 exploration determinism

But cache identity still only binds to structural identity.

This creates a subtle risk:
different exploration trajectories can collapse onto identical cache slots.

Why this matters:
If future orchestration layers accidentally assume:
    "cache hit means already explored"

the search can stagnate.

Current spec weakness:
The tier-table explains semantics but does not create hard architectural
boundaries preventing misuse.

Solution:
Future-proof now with:
    explicit cache metadata fields:
        cache_identity_kind="structural"

and:
    exploration lineage IDs distinct from structural signatures.

Potentially:
    exploration_hash != structural_hash

Severity:
MEDIUM-HIGH
Architectural correctness risk.
Especially dangerous in future optimization layers.


========================================================
5. MULTI-FLOOR WRAPPER REBUILDING CAN BECOME A MAJOR PERF BOTTLENECK
========================================================

Problem:
Every mutation rebuilds immutable wrappers repeatedly through:
    with_floor_replaced()
    with_master_on()

Long mutation chains produce:
    - repeated allocations
    - repeated tuple reconstruction
    - repeated recursive signature derivation
    - repeated wrapper validation

This can become extremely expensive in:
    - large populations
    - deep mutation chains
    - 4+ floor dwellings
    - NSGA-II workloads

Current mitigation:
Only backlog items exist.

Why this matters:
This is not micro-optimization.
Evolutionary systems amplify allocation overhead dramatically.

Solution:
Move earlier toward:
    - structural sharing
    - persistent immutable trees
    - batched floor replacement
    - Merkle-style signatures
    - lazy signature memoization

Potentially:
    persistent DAG-style wrapper storage.

Severity:
MEDIUM now.
HIGH at scale.


========================================================
6. FLOOR LABELS ARE STILL OVERLOADED AS IDENTITY PRIMITIVES
========================================================

Problem:
Multiple systems rely on floor labels:
    - ordering
    - family aggregation
    - deterministic sorting
    - signature derivation
    - orchestration targeting

But labels are semantic strings, not canonical structural IDs.

This causes fragility:
    "Ground"
    "ground"
    "GROUND"
    "g"
    "GF"

can all represent identical architectural semantics but generate:
    - different signatures
    - different family IDs
    - different cache identities

The spec assumes normalization upstream,
but architectural correctness depends on it heavily.

Solution:
Introduce explicit:
    floor_uid
or:
    canonical_floor_index

independent from display labels.

Labels become presentation metadata only.

Severity:
MEDIUM-HIGH
Identity correctness issue.


========================================================
7. PROPERTY TESTS STILL DO NOT MODEL TRUE SEARCH DYNAMICS
========================================================

Problem:
The property tests validate:
    - invariants
    - coverage
    - determinism
    - chain stability

But they still operate mostly on:
    - short chains
    - isolated candidates
    - non-population dynamics

Missing:
    - correlated population evolution
    - cache pressure
    - family-slot competition
    - replay drift
    - concurrent orchestration

Why this matters:
Many evolutionary failures only emerge from:
    population interaction + long horizons.

Solution:
Add simulation-level tests:
    - 10k generation replay
    - population diversity entropy
    - cache collision stress
    - operator-frequency convergence
    - phase-lock detection

Severity:
MEDIUM


========================================================
8. THE ORCHESTRATOR IS BECOMING A GOD-OBJECT
========================================================

Problem:
C11a orchestrator now owns:
    - dispatch
    - scheduling
    - fairness
    - generation semantics
    - lineage integration
    - cross-floor coordination
    - cache semantics
    - failure classification
    - operator policy

This is architectural concentration.

Why this matters:
Future changes become:
    high-risk
    tightly coupled
    regression-prone

The spec already acknowledges this via B-C11A-11.

But the issue is now substantial.

Solution:
Eventually split into:
    - SchedulingPolicy
    - MutationPlanner
    - FloorImpactResolver
    - ExplorationCoordinator
    - DeterminismController
    - MutationExecutor

Severity:
HIGH long-term maintainability risk.


========================================================
9. M8 ASSUMES MASTER RELOCATION IS LOCALLY SUFFICIENT
========================================================

Problem:
M8 only regenerates:
    old master floor
    new master floor

But future cross-floor constraints may require:
    - circulation updates
    - staircase relationships
    - vertical plumbing changes
    - stack continuity
    - adjacency balancing

The abstraction layer exists,
but the current implementation logic still psychologically anchors
future maintainers toward "2-floor impact".

Why this matters:
The implementation assumption may fossilize into future logic.

Solution:
Even before B-C11A-7 lands:
    document explicitly:
        "2-floor impact is an optimization assumption,
         NOT an architectural invariant."

Potentially rename:
    direct_impacts
instead of:
    affected_floor_set

Severity:
MEDIUM


========================================================
10. LINEAGE MODEL IS STILL TOO SHALLOW FOR TRUE REPRODUCIBILITY
========================================================

Problem:
Lineage currently captures:
    - floor_label_affected
    - wrapper transitions
    - family transitions

But NOT:
    - generation
    - operator ordering
    - scheduling offsets
    - slot truncation state
    - cache-hit ancestry
    - orchestration context

This means:
full replay reconstruction is impossible.

Why this matters:
As the search grows more sophisticated,
debugging unexplained topology drift becomes extremely difficult.

Solution:
Eventually lineage needs:
    - generation
    - operator_index
    - scheduling seed
    - slot allocator state
    - exploration path hash
    - parent lineage references

Essentially:
    event-sourced evolutionary provenance.

Severity:
HIGH for future debugging/explainability.


========================================================
11. CROSS-SPEC COUPLING IS EXTREMELY HIGH
========================================================

Problem:
This amendment tightly couples:
    Spec #1
    Spec #2
    Spec #3
    C9
    C10
    C11a
    future C11b

A small semantic drift in any component can cascade globally.

Example:
Changing:
    floor normalization
or:
    master-bedroom semantics

can silently break:
    signatures
    family IDs
    orchestration
    lineage
    cache identity

Why this matters:
The architecture is now entering "ecosystem coupling" territory.

Solution:
Introduce explicit:
    cross-spec invariant contracts
    compatibility matrices
    semantic version compatibility assertions

Potentially:
    automated contract tests between specs.

Severity:
HIGH architectural evolution risk.


========================================================
12. SPEC COMPLEXITY ITSELF IS BECOMING A RISK
========================================================

Problem:
The amendment is now extremely large and highly interdependent.

Risks:
    - maintainers misunderstand subtle contracts
    - partial implementations violate assumptions
    - future contributors patch locally but break global invariants
    - onboarding cost rises sharply

This is now systems-architecture scale,
not component-scale.

Why this matters:
Complexity itself becomes a source of defects.

Solution:
Post-LOCK:
    split into:
        - normative contracts
        - rationale appendix
        - algorithm appendix
        - invariants appendix
        - orchestration semantics appendix

Also add:
    architecture diagrams
    execution-flow diagrams
    identity-system maps

Severity:
HIGH maintainability/documentation risk.


========================================================
OVERALL ASSESSMENT
========================================================

The spec is now architecturally strong and internally coherent.
Most remaining issues are no longer:
    "correctness defects"

but instead:
    "evolutionary-system scaling risks"
    "architectural complexity risks"
    "future-search-dynamics risks"

The biggest remaining genuine concerns are:

    1. deterministic fairness bias accumulation
    2. cyclic exploration resonance
    3. orchestration centralization
    4. shallow lineage provenance
    5. high cross-spec coupling

The v1.5 round successfully resolves the reviewer's named pre-LOCK blockers,
but several backlog items are actually strategically important for
long-term scalability and evolutionary-search quality.

Current maturity assessment:
    PRETTY CLOSE TO LOCK-WORTHY
    for v1 operational scope.

But:
    not yet "future-proof at NSGA-II scale".
