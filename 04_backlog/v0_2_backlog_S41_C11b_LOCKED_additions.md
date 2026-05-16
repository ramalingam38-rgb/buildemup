# v0.2 Backlog — S41 C11b v1.1 LOCKED Additions

**Date**: S41 close (May 12, 2026)
**Origin**: C11b spec evolution across v0.4-v0.7 (4 walks: self-analysis + Walks #4, #5, #6 external critiques) → v1.1 LOCKED

## Cumulative C11b backlog at LOCK: 17 NEW items (v0.4 + v0.5 + v0.6 + v0.7)

Existing pre-v0.4 C11b backlog (12 items) carried unchanged: B-237, B-NEW-P, B-NEW-V, B-NEW-W, B-NEW-X, B-NEW-Y, B-NEW-Z, B-NEW-V2, B-NEW-V3, B-NEW-V4, B-NEW-V5 (WIDENED at v0.4), B-NEW-V6.

### v0.4 additions (2 items)

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-C11B-MF** | Multi-floor topology refinement for C11b | When product needs end-to-end MF refinement (likely with C12 MF placement OR C14 MF scoring) | L |
| **B-C11B-TIMEOUT-V2** | Per-evaluation timeout + generation-level resumability after wall-clock breach. v0.7 W6-10 amendment: scope extended to intra-generation watchdog hooks (candidate-evaluation checkpoints, evaluator soft deadlines, heartbeat timestamps) | When measured tail-latency on production evaluator becomes a quality concern | M |

### v0.5 additions (6 items)

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-C11B-EVALUATOR-RESILIENCE** | Replenish skipped candidates immediately with regenerated offspring instead of shrinking population mid-generation | When measured Pareto-front quality degrades correlated with high skip-counts on production evaluator | M |
| **B-C11B-RESOLVER-V2** | `primary_application_result: MutationApplicationResult` singleton field on `MutatedTopologyCandidate` (cleanup of v1 cardinality brittleness) | When (if) C11a introduces multi-application MTCs | M |
| **B-C11B-TIMEOUT-COMPLEXITY** | Complexity-aware timeout budget: `timeout = base + k * room_count` or similar | When measured timeout-failures cluster on complex briefs | S-M |
| **B-C11B-INV-TIERING** | Formal CORE / REPLAY / DIAGNOSTIC tiering of the 29 invariants; allow non-core relaxation in development mode | When contributor onboarding signals 29 invariants is a cognitive blocker | S |
| **B-C11B-STRICT-TIERS** | STRICT_PER_TOPOLOGY vs STRICT_GLOBAL distinction; configurable systemic-failure thresholds; partial batch salvage mode | When production runs see frequent batch-halts from single pathological topologies | M |
| **B-C12-MATERIALIZATION-CONTRACT** (ROUTED TO C12) | C12 placement layer MUST assert capability-flag consistency (`placement_safe`, `geometry_materialized`, `requires_transform_resolution`) before consuming refined parameters as final geometry | When C12 spec arc begins | S |

### v0.6 additions (8 items)

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-C11B-DOERR-TIEBREAK** | Adopt Doerr/Ivan/Krejca 2024 frequency-based NSGA-II tie-break (AAAI; arxiv 2412.11931). Proves NSGA-II can optimize benchmarks efficiently for ≥3 objectives via "number of individuals with the same objective value" as the third tie-break criterion (before random tail). Simultaneously addresses Walk #5 Items 2 (tie-break bias) and 15 (NSGA-II 3-objective limitation). **v0.7 W6-5 caveat**: assumes discrete-valued objectives; continuous floats reduce frequency-counting to ~all-1 buckets. Adoption requires continuous-objective adaptation research (epsilon-clustering or density estimation) + empirical validation BEFORE replacing v1 tie-break. | Before C14 production evaluator ships OR when first 3-objective hypervolume regression is observed | M |
| **B-C11B-CACHE-TIERS** | Cache-relevance tiering: OUTPUT_CRITICAL / REPLAY_CRITICAL / DIAGNOSTIC, replacing the binary `cache_relevant: bool`. **v0.7 W6-9 trigger tightened**: "when cache hit rate drops below 50% in experimentation runs" | When cache hit rate < 50% in experimentation | M |
| **B-C11B-PROVENANCE-SPLIT** | Split `LocalRefinementProvenance` into three independently-versioned dataclasses: `ReplayProvenance` (master_seed, env tuple, c11b_version), `OperationalTelemetry` (timeouts, skips, durations), `DiagnosticWarnings` (resolved_objective_count, skipped_multifloor_count). **v0.7 W6-11 PROMOTED to HIGH priority**: trigger tightened to "any change requiring c11b_version MINOR or MAJOR bump" | Any c11b_version MINOR/MAJOR bump | M |
| **B-C11A-MTC-SINGLETON** (ROUTED TO C11a) | C11a v1.6 amendment to expose `primary_application_result: MutationApplicationResult` as a type-honest singleton field, with `extra_application_results: tuple[...] = ()` for future batch expansion. Eliminates the v1 tuple-vs-singleton schema dishonesty | Whenever C11a v1.6 LOCKED takes a non-trivial amendment for any other reason | S |
| **B-C11B-COMPLEXITY-BUDGET-V2** | Weighted complexity metric (invariants×1, cache×2, replay×3, telemetry×0.5) alongside subsystem count. **v0.7 W6-7 PROMOTED to MANDATORY**: every future walk reports the weighted complexity metric in § 14.1 convergence table | Mandatory ongoing | S |
| **B-C11B-SPEC-SPLIT-V2** | Documentation modularization: split spec into `C11b-Core-Optimization` + `C11b-Replay` + `C11b-Provenance` + `C11b-Failure-Policy`. **v0.7 W6-14 PROMOTED to HIGH priority**: § 0.0d "current surface only" digest is interim mitigation; full split remains backlog | When spec length exceeds ~1500 lines (currently 1519) OR when contributor explicitly requests modular reading | S |
| **B-PIPELINE-CAPABILITY-NEGOTIATION** (ROUTED TO ORCHESTRATOR) | Orchestrator-level capability flag (`supports_multifloor_refinement: bool`) consulted by upstream components before generating multi-floor candidates. Prevents wasted MF generation when C11b is configured to reject MF | When measured MF-rejection cost crosses orchestrator-observable thresholds | M |
| **B-C11B-HYPERVOLUME-WARN** | Hypervolume-regression-based warning replacing the dropped `nsga2_objective_count_warning` bool. **v0.7 W6-13 amendment**: backlog item now explicitly requires freeze of normalization policy + benchmark corpus BEFORE the warning fires in production | After B-NEW-W ships hypervolume metric | S |

### v0.7 additions (1 item)

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-C11B-TIER2-SCALING** | Replace O(N²) pairwise dominance checks in TIER-2 replay validation with hashing/indexing structures (ND-trees, front-adjacency signatures, Pareto layer DAG fingerprints). Literature reference: Bashir 2025 arxiv 2508.20689 ND-trees for ≥3 objectives | When CI TIER-2 wall-clock > 5min per replay batch OR when population sizes exceed 500 | M |

### v1.0 backlog updates carried at LOCK

- **B-NEW-V5** (WIDENED at v0.4 D-NSGA-2): Broader EA protocols + **NSGA-III migration**. Widened trigger: (a) C14 ≥3 obj AND (b) hypervolume regression 2+ cycles, OR (c) architect blocking feedback

## Cumulative backlog summary at C11b v1.1 LOCKED

| Total | Pre-existing | v0.1 | v0.2 | v0.3 | v0.4 | v0.5 | v0.6 | v0.7 |
|---|---|---|---|---|---|---|---|---|
| **29** | 2 | 5 | 2 | 3 | 2 | 6 | 8 | 1 |

(12 pre-v0.4 carried + 17 added across v0.4-v0.7 = 29 cumulative)

## Cross-component routings

These backlog items live in C11b's spec but address other components:
- B-C12-MATERIALIZATION-CONTRACT → C12 placement layer
- B-C11A-MTC-SINGLETON → C11a v1.6 amendment
- B-PIPELINE-CAPABILITY-NEGOTIATION → orchestrator layer

