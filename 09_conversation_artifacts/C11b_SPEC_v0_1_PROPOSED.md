# C11b — Local Refinement (NSGA-II) — SPEC v0.1 PROPOSED

**Component**: 11b (canonical Track 3 numbering — paired with C11a Topology Mutation)
**Status**: v0.1 PROPOSED. **NOT LOCKED.**
**Convergence target**: 2-3 walks to LOCK per Ramalingam directive S37.
**Authority**: S37/S38 author's draft. PENDING Ramalingam adjudication.
**Authored**: post C11a v1.0 LOCKED (S37 Walk #5+#6).

---

## § 0 — Architectural notes

C11b sits between C11a and C12. Consumes `MutatedTopologyCandidate`
seeds from C11a; runs NSGA-II within each topology to refine geometric
parameters; outputs a Pareto front of refined candidates per topology.

**Pipeline position**:
```
C10 → C11a → C11b (THIS) → C12 → C13 → C14
```

### § 0.1 — Convergence stance

Per Ramalingam directive S37: **target 2-3 walks to LOCK** (vs. C11a's
5+1 walk arc). This forces v0.1 to make more decisions upfront. Five
disciplines apply:

1. **5-7 open questions max** (vs. C11a v0.1's 15) — pre-decide where
   reasonable.
2. **Reuse C11a v1.0 patterns wherever applicable** — don't re-litigate
   solved problems.
3. **Anticipate critique categories** — pre-empt the Walk #2 review
   surface area.
4. **Tight v1 subsystem count** — borrow from C11a's § 13 Complexity
   Budget; new subsystems must justify their cost in v0.1 not Walk #N.
5. **Honest forward-coupling to C14** — define the C14 evaluator
   contract narrowly via `EvaluatorProtocol` injection; do not redefine
   C14's authority.

### § 0.2 — What C11b IS

- NSGA-II Pareto search per topology (Deb et al. 2002 standard)
- Geometric **parameter refinement** (room dimensions only at v1)
- Multi-objective optimization via injected evaluator
- Deterministic via seeded PRNG (seed derived from C11a provenance)
- Per-topology independent (no cross-topology Pareto merging at v1)

### § 0.3 — What C11b is NOT

- **NOT topology mutation.** Topology is frozen by C11a's output.
- **NOT scoring authority.** Objectives are computed by injected
  `EvaluatorProtocol` (concrete C14 implementation, when shipped).
- **NOT placement geometry.** Per-room x/y/w/h finalization is C12.
- **NOT user-facing.** No rendering, no explanation strings beyond
  provenance trace. C16 is the renderer.
- **NOT cross-topology.** Each `MutatedTopologyCandidate` gets its own
  Pareto front. Cross-topology comparison is C14/C15's job.
- **NOT topology-violating.** v1 refinement scope: room widths/depths
  within liveability bounds. Wall positions, wet-wall assignment,
  family identity — all FROZEN by upstream.

### § 0.4 — Reuse from C11a v1.0 LOCKED

C11b inherits these architectural patterns directly:

| C11a pattern | C11b application |
|---|---|
| `canonical_serialize` (C7 amendment v0.8 utility) | Replay determinism |
| `severity_tier` ClassVar (post B-NEW-P) | Error classification |
| `UpstreamReplayVersionHashes` | Provenance replay-drift detection |
| `PurityAttestation` | EvaluatorProtocol purity contract |
| Atomicity-by-construction | Immutable candidate semantics |
| Single-threaded v1 contract (Inv 30) | Inherited verbatim |
| Provenance verbosity tiers | Inherited |
| Cache-relevant field annotation | Inherited |
| `validate_*_at_startup()` pattern | Validates evaluator + PRNG |

### § 0.5 — NSGA-II algorithm choice

**NSGA-II (Deb et al. 2002)** with constrained-domination principle
(NSGA-II-CDP for HARD constraint handling):

- Non-dominated sorting (O(MN²))
- Crowding distance for diversity
- Binary tournament selection
- **Crossover**: SBX (Simulated Binary Crossover), η_c=20
- **Mutation**: Polynomial mutation, η_m=20
- **Constraint handling**: CDP — feasible always dominates infeasible;
  infeasibles ranked by constraint-violation magnitude

Standard literature defaults; not domain-specific. Walk #2 may challenge
hyperparameters but alternative algorithms (NSGA-III, MOEA/D, Bayesian
multi-objective) are out of scope for v1.

### § 0.6 — Determinism strategy (NEW concern not in C11a)

NSGA-II is **stochastic** by design — population initialization,
crossover, mutation, tournament selection all consume random bits.
Replay determinism requires explicit PRNG management:

```python
def derive_prng_seed(
    topology_candidate: MutatedTopologyCandidate,
    config: LocalRefinementConfig,
) -> int:
    """Per-topology PRNG seed. Stable across runs given same upstream
    state."""
    seed_material = canonical_serialize({
        "variant_id": topology_candidate.topology_variant_id,
        "upstream_versions": topology_candidate.provenance.upstream_replay_versions,
        "config_cache_hash": derive_cache_config_hash(config),
    })
    return int(hashlib.sha256(seed_material.encode()).hexdigest()[:16], 16)


# PRNG: numpy.random.Generator with explicit seed
rng = numpy.random.default_rng(derive_prng_seed(...))
```

**Why numpy.random.Generator (vs. `random.Random`)**:
- Vector operations across population
- Consistent statistical properties across numpy versions (PCG64 backend)
- Standard NSGA-II implementations use numpy

**Per-topology PRNG isolation**: each topology's NSGA-II run gets its
own seeded `Generator`. No global state. Replay-safe by construction.

### § 0.7 — EvaluatorProtocol (forward-coupling to C14)

C11b receives an evaluator at function entry. The protocol is
**deliberately minimal** — single method, single attestation — so C14's
spec arc retains design freedom:

```python
class EvaluatorProtocol(Protocol):
    purity_attestation: PurityAttestation

    def evaluate(self, candidate: RefinedCandidate) -> ObjectiveVector:
        """Pure function. Same input → same output. No side effects."""


@dataclass(frozen=True)
class ObjectiveVector:
    """Multi-objective evaluation result. C14 declares what objectives
    it computes; C11b is objective-agnostic."""
    values: tuple[tuple[str, float], ...]      # (name, value), sorted lex-ASC by name
    constraint_violations: float = 0.0          # for NSGA-II-CDP
```

**Why this is acceptable forward-coupling**:
- C11b imposes minimal shape (objective_name → float; sorted lex-ASC)
- C14 chooses *which* objectives to compute (liveability, plumbing,
  vastu, structural, cost — per arch v3, but that's C14's catalog)
- v1 ships with a stub evaluator for testing (`StubEvaluator` returns
  deterministic synthetic objectives); production evaluator from C14

**Stub evaluator at v1**: `StubEvaluator` produces 3-objective
ObjectiveVector based on canonical_serialize hash. Lets C11b test infra
run before C14 exists. Replaced when C14 ships.

---

## § 1 — Walk-resolved scope

None at v0.1. First decisions land at Walk #2.

---

## § 2 — Contract

```python
def run_local_refinement(
    mutated_topology_candidates: tuple[MutatedTopologyCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    evaluator: EvaluatorProtocol,
    *,
    config: LocalRefinementConfig | None = None,
) -> tuple[RefinedCandidate, ...]:
    """C11b entry point. Per-topology NSGA-II refinement.

    Output ordering: input-order outer (per source topology), Pareto
    crowding-distance descending inner.

    Concurrency: single-threaded only at v1.0 (carries C11a Inv 30).
    """
```

### § 2.1 — Schema

```python
@dataclass(frozen=True)
class RefinedParameters:
    """v1 parameter scope: room dimensions only.
    Wall positions, wet-wall assignment, etc. all frozen from upstream."""
    room_dimensions: tuple[tuple[str, float, float], ...]
    # tuple of (room_id, width_m, depth_m), sorted lex-ASC by room_id


@dataclass(frozen=True)
class ObjectiveVector:
    values: tuple[tuple[str, float], ...]
    constraint_violations: float = 0.0


@dataclass(frozen=True)
class RefinedCandidate:
    source_topology_candidate: MutatedTopologyCandidate
    refined_parameters: RefinedParameters
    objective_vector: ObjectiveVector
    pareto_rank: int                            # 0 = non-dominated front
    crowding_distance: float
    provenance: LocalRefinementProvenance


@dataclass(frozen=True)
class GenerationSnapshot:
    """Per-generation telemetry. Diagnostic-only; not used for selection."""
    generation_index: int
    pareto_front_size: int
    pareto_front_signature_hash: str            # for stagnation detection
    feasible_count: int
    infeasible_count: int


@dataclass(frozen=True)
class LocalRefinementConfig:
    pop_size: int = field(default=50, metadata={"cache_relevant": True})
    max_generations: int = field(default=100, metadata={"cache_relevant": True})
    crossover_rate: float = field(default=0.9, metadata={"cache_relevant": True})
    mutation_rate: float = field(default=0.1, metadata={"cache_relevant": True})
    sbx_eta_c: float = field(default=20.0, metadata={"cache_relevant": True})
    polynomial_eta_m: float = field(default=20.0, metadata={"cache_relevant": True})
    pareto_output_size: int = field(default=20, metadata={"cache_relevant": True})
    convergence_stable_gens: int = field(default=5, metadata={"cache_relevant": True})
    enforcement_mode: EnforcementMode = field(
        default=EnforcementMode.WARN, metadata={"cache_relevant": False},
    )
    provenance_verbosity: ProvenanceVerbosity = field(
        default=ProvenanceVerbosity.PER_GEN, metadata={"cache_relevant": False},
    )
    evaluator_cache_enabled: bool = field(
        default=True, metadata={"cache_relevant": False},
    )


@dataclass(frozen=True)
class LocalRefinementProvenance:
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    source_variant_id: str
    prng_seed_used: int
    generations_run: int
    converged_at_generation: int | None
    convergence_reason: Literal[
        "max_generations", "stagnation_stable", "infeasible_terminated",
    ]
    generation_log: tuple[GenerationSnapshot, ...]
    final_pareto_front_size: int
    evaluator_call_count: int
    evaluator_cache_hit_count: int
    evaluator_cache_miss_count: int
    upstream_replay_versions: UpstreamReplayVersionHashes  # carried from C11a
    rule_trace: tuple[str, ...]
    _observational_runtime_ms: int                          # excluded from replay hashes
```

### § 2.2 — Refinement scope

**v1 scope: room widths and depths.** Constrained to:
- Lower bound: `liveability_min_width_m` and `liveability_min_depth_m`
  from C9
- Upper bound: `min_width * 1.5` and `min_depth * 1.5`
- Sum constraint: total floor area used ≤ envelope area (HARD constraint
  → constraint_violation if exceeded)

**Out of scope at v1** (filed as B-NEW-V):
- Wall offset adjustments (C7's job)
- Door positions (C13's job)
- Window positions (post-C13)
- Furniture refinement (C9 KB job)

---

## § 3 — Behaviour

### Phase 0 — Input + startup validation

1. Validate `evaluator.purity_attestation` present and valid
2. Verify each `MutatedTopologyCandidate` has expected provenance fields
3. Concurrency assertion: single-threaded execution context
4. Config validation (pop_size > 0, generations > 0, rates ∈ [0, 1])

### Phase 1 — Per-topology NSGA-II run

For each `MutatedTopologyCandidate` in input order:

1. **Seed derivation**: `seed = derive_prng_seed(candidate, config)`;
   instantiate `rng = numpy.random.default_rng(seed)`
2. **Initial population**: `pop_size` random parameter vectors uniformly
   sampled within liveability bounds via `rng`
3. **Initial evaluation**: call `evaluator.evaluate()` for each candidate
   (with cache); record `evaluator_call_count` and cache hit/miss
4. **Generation loop** for `g in [1, max_generations]`:
   - **Selection**: binary tournament (constrained domination
     comparator); produces parent pool of size `pop_size`
   - **Crossover**: SBX with rate `crossover_rate`, η=`sbx_eta_c`
   - **Mutation**: polynomial with rate `mutation_rate`, η=`polynomial_eta_m`
   - **Evaluation** of offspring (cache)
   - **Combine** parent + offspring → 2*pop_size population
   - **Non-dominated sort**: rank candidates into Pareto fronts
   - **Crowding distance** within each front
   - **Truncate** to pop_size (NSGA-II selection: lower rank first;
     within rank, larger crowding distance first)
   - **Snapshot** generation: `GenerationSnapshot(g, front_size,
     front_signature_hash, ...)`
   - **Convergence check**: if last `convergence_stable_gens` snapshots
     have identical `pareto_front_signature_hash`, terminate early
5. **Final extraction**: top `pareto_output_size` from rank-0 front,
   ordered by crowding distance descending

### Phase 2 — Output assembly

Concatenate per-topology Pareto fronts in input order. **No
cross-topology merging at v1** (per § 0.3 / Q2). Each topology's
RefinedCandidate batch maintains its own internal Pareto rank.

### Phase 3 — Provenance assembly

Per topology, build `LocalRefinementProvenance` with full generation
log (default `PER_GEN` verbosity), evaluator telemetry, PRNG seed used,
convergence reason, and `UpstreamReplayVersionHashes` propagated from
C11a.

### § 3.1 — Constraint handling (NSGA-II-CDP)

Constrained Domination Principle:
- Solution A dominates B if:
  - A is feasible and B is not, OR
  - Both feasible and A Pareto-dominates B, OR
  - Both infeasible and A has lower constraint_violation
- HARD constraint at v1: `sum(room_width × room_depth) ≤ envelope_area`
- Soft objectives are evaluator's responsibility

### § 3.2 — Pareto-front signature for stagnation detection

```python
def pareto_front_signature(front: tuple[RefinedCandidate, ...]) -> str:
    """Canonical hash of the Pareto front objective values, used for
    convergence-stagnation detection."""
    canonical = canonical_serialize(tuple(
        sorted(c.objective_vector.values for c in front)
    ))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
```

### § 3.3 — Evaluator caching

Per-batch `EvaluatorCacheKey` keyed on `canonical_serialize(refined_parameters)`.
Cache scope: single batch (`run_local_refinement` invocation). Discarded
at function return. Bounds size: pop_size × max_generations ≈ 5,000
entries max.

---

## § 4 — Invariants

| # | Invariant | Mode |
|---|---|---|
| 1 | Every output's `source_topology_candidate` exists in input tuple | RAISE |
| 2 | Output ordered: input-order outer, crowding-distance descending inner | RAISE |
| 3 | `RefinedParameters.room_dimensions` within liveability bounds (HARD) | RAISE |
| 4 | Pure function: same inputs (evaluator + config + candidates) → same outputs | RAISE (replay tier) |
| 5 | `ObjectiveVector.values` dimensions consistent across all candidates within a single batch | RAISE |
| 6 | `_observational_runtime_ms` not in any replay-hash computation | RAISE (replay tier) |
| 7 | Evaluator's `PurityAttestation` validated at startup | RAISE (startup) |
| 8 | `UpstreamReplayVersionHashes` propagated to every output's provenance | RAISE |
| 9 | Single-threaded execution contract (carry C11a Inv 30) | DOCUMENTED (contract) |
| 10 | `len(pareto_front) ≤ config.pareto_output_size` per topology | RAISE |
| 11 | `prng_seed_used` recorded in provenance and replay-reproducible | RAISE (replay tier) |
| 12 | NSGA-II-CDP constraint domination: feasible always dominates infeasible | RAISE |
| 13 | Pareto front signature hash excludes `_observational_runtime_ms` and timestamps | RAISE (replay tier) |
| 14 | Evaluator cache scope: single-batch only; discarded at function return | RAISE |
| 15 | Severity-tier classification on caught exceptions follows C11a Inv 27 pattern | RAISE |

15 invariants at v0.1. Comparable to C11a v0.1's 10 — slightly more because NSGA-II algorithmic correctness needs explicit invariants.

---

## § 5 — Failure modes

```
LocalRefinementError (base)
├── PerTopologyError
│   ├── NSGAConvergenceError              (no Pareto front formed; e.g., all-infeasible)
│   ├── InfeasiblePopulationError         (initial pop entirely violates HARD constraints)
│   └── EvaluatorContractError            (per-call evaluator failure)
├── BatchAllTopologiesFailedError         (all topologies failed)
├── EvaluatorPurityContractError          (startup; analog to C11a DeepMutationPurityContractError)
└── InvariantViolationError                (systemic)
```

---

## § 6 — Test coverage targets

Target ~150 tests at LOCK:

- ~25 schema (`RefinedCandidate`, `ObjectiveVector`,
  `LocalRefinementConfig`, `EvaluatorProtocol`, `PurityAttestation`
  reuse)
- ~30 NSGA-II core (non-dominated sort, crowding distance, tournament
  selection, SBX crossover, polynomial mutation)
- ~22 invariants (Inv 1-15 across modes)
- ~25 phase-logic (initialization, generation loop, convergence
  detection, final extraction)
- ~12 partial-batch / strict-mode (per-topology failure aggregation)
- ~12 replay determinism (PRNG seed reproducibility, cross-run
  byte-equality)
- ~12 evaluator contract (stub evaluator, PurityAttestation
  enforcement, cache hit/miss)
- ~12 edge cases (empty input, single-objective collapse,
  all-infeasible, convergence at gen 0)

Cumulative target at C11b ship: 2519 + 150 ≈ **2669 passed**.

---

## § 7 — Open questions (target 5-7 for aggressive convergence)

| Q | Question | v0.1 direction |
|---|---|---|
| Q1 | Constraint handling: NSGA-II-CDP vs. penalty-based? | **CDP at v1**. Penalty undermines determinism analysis and obscures feasibility. |
| Q2 | Cross-topology Pareto front aggregation? | **NO at v1**. Each topology = own front. C14 ranker does cross-topology if needed. |
| Q3 | Restart policy on stagnation? | **NO at v1**. Convergence-stable-gens early termination only. |
| Q4 | Refinement scope expansion beyond room dimensions at v1? | **NO**. Walls/doors/windows deferred to B-NEW-V (v2). |
| Q5 | Diversity metric: crowding distance only, or hypervolume too? | **Crowding distance only at v1**. Hypervolume is post-launch. |
| Q6 | PRNG: `numpy.random.Generator` vs. `random.Random`? | **`numpy.random.default_rng()` (PCG64 backend)** at v1. Verified across numpy versions via B-237. |
| Q7 | Output ordering — by crowding distance, by single objective, or interleaved? | **Crowding distance descending** (most diverse first). |

7 open questions. Walk #2 should challenge any of these; Walk #2 directions resolve them definitively for v0.2.

---

## § 8 — Backlog at v0.1

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-NEW-V | C11b refinement scope expansion (door/window/furniture refinement) | v0.1 Q4 | post-launch + measured under-coverage | M |
| B-NEW-W | C11b hypervolume-based diversity metric | v0.1 Q5 | post-launch | M |
| B-NEW-X | C11b adaptive operator hyperparameters (η_c, η_m, rates per generation) | future tuning needs | post-launch | M |
| B-NEW-Y | C11b cross-topology Pareto aggregation | v0.1 Q2 | C14 ranker observed insufficient | M |
| B-NEW-Z | C11b deterministic-parallel-NSGA-II (analog to C11a B-NEW-U) | scaling pressure | post-launch | L |

5 new items at v0.1. C11b is a fresh component — no pre-existing carry.

**Inherited triggers** affecting C11b:
- B-NEW-P (upstream `severity_tier` cluster) — required before C11b build (carry from C11a)
- B-237 (cross-platform replay CI) — required for Q6 verification

---

## § 9 — Rule 11 spec audit on v0.1 PROPOSED

**PATCH-NOW (in v0.1 itself): 0** — drafting is the patch round.

**OPEN QUESTIONS surfaced**: Q1-Q7 (7).

**SPEC-AUDIT FINDINGS (v0.1)**:

| # | Finding | Verdict |
|---|---|---|
| F-v1-1 | `EvaluatorProtocol` forward-couples to C14. If C14 spec emerges and the contract differs, C11b must amend. Mitigation: protocol intentionally minimal (1 method + attestation). | **DOCUMENTED** — accepted forward-coupling cost. |
| F-v1-2 | Pop_size=50 default is on the lower end for NSGA-II (literature: 100-300). Trade-off: smaller pop = faster runtime; might miss diverse Pareto. | **NEEDS WALK** — Walk #2 should benchmark. |
| F-v1-3 | Max_generations=100 default similarly low. | **NEEDS WALK** — Walk #2 confirm. |
| F-v1-4 | SBX η_c=20, polynomial η_m=20 are literature standard but Indian-residential layouts may need different tuning. No empirical data at v0.1. | **NEEDS WALK** — Walk #2 challenge; if no data, accept defaults; defer to B-NEW-X for tuning. |
| F-v1-5 | `StubEvaluator` for v1 testing is a real dependency — needs concrete spec for what it returns. Currently described as "3-objective ObjectiveVector based on canonical_serialize hash" but that's not a contract. | **PATCH-NOW** — define `StubEvaluator` deterministic synthetic-objective formula explicitly below. |
| F-v1-6 | `pareto_output_size=20` default is arbitrary. Why not 10? 50? Walk #2 should challenge. | **NEEDS WALK** — config default review. |
| F-v1-7 | Pareto front signature hash for stagnation detection (§ 3.2) uses sorted objective values. If two functionally distinct fronts produce same sorted values (unlikely but possible), false positive stagnation. | **NEEDS WALK** — stagnation-detection robustness. |
| F-v1-8 | Evaluator cache is per-batch with bounded size, but no LRU eviction policy specified. If pop_size × max_generations > some upper bound (e.g., 100 × 1000 = 100k), memory pressure. v1 defaults yield ~5000 entries — fine, but should be documented. | **PATCH-NOW** — document cache size bound; reject configs that would exceed 50k entries. |

**PATCH-NOW APPLIED INLINE TO v0.1**:

- **F-v1-5 — `StubEvaluator` formal contract**:
  ```python
  class StubEvaluator:
      """Test-only evaluator for v1 build. Replaced by C14 implementation
      when C14 ships. Deterministic synthetic objectives derived from
      canonical_serialize."""
      purity_attestation: PurityAttestation = PurityAttestation(
          component_id="C11b", entry_point="StubEvaluator.evaluate",
          purity_class="pure", attested_by="C11b",
          attested_at_kb_version="stub_v1.0",
      )

      def evaluate(self, candidate: RefinedCandidate) -> ObjectiveVector:
          payload = canonical_serialize(candidate.refined_parameters)
          h = hashlib.sha256(payload.encode()).digest()
          # 3 synthetic objectives in [0, 1]: deterministic, smooth across
          # parameter changes, uncorrelated.
          obj_a = (h[0] + h[1] * 256) / 65535.0      # "synthetic_liveability"
          obj_b = (h[2] + h[3] * 256) / 65535.0      # "synthetic_plumbing"
          obj_c = (h[4] + h[5] * 256) / 65535.0      # "synthetic_structural"
          return ObjectiveVector(
              values=(
                  ("synthetic_liveability", obj_a),
                  ("synthetic_plumbing",    obj_b),
                  ("synthetic_structural",  obj_c),
              ),
              constraint_violations=0.0,  # stub never violates
          )
  ```

- **F-v1-8 — Evaluator cache size bound**:
  Add `MAX_EVALUATOR_CACHE_ENTRIES: Final[int] = 50_000` constant.
  Phase 0 validation rejects configs where `pop_size × max_generations
  > MAX_EVALUATOR_CACHE_ENTRIES` (raises `LocalRefinementError`).

**SPEC-AUDIT FINDINGS count**: 8 — comparable to C11a v0.1's 10. Honest seed quality.

**REJECTED-AS-CONSIDERED**:
- "Should C11b run multi-objective Bayesian optimization instead of
  NSGA-II?" — Out of scope. NSGA-II is industry standard for
  multi-objective architectural search.
- "Should each generation be checkpointed for resumability?" —
  Operational concern, post-launch. C11b is single-batch deterministic;
  re-runs are cheap.
- "Should cross-topology objectives be normalized before merge?" — N/A
  at v1 (no cross-topology merging per Q2).
- "Should refinement bounds be dynamic per-topology?" — Adds complexity
  for unmeasured benefit. v1 uses fixed `[min, min × 1.5]`.

---

## § 10 — Status

- **v0.1 PROPOSED**. **NOT LOCKED.**
- LOCK NOT REQUESTED at v0.1.
- 7 open questions (target met for aggressive convergence).
- 8 audit findings (comparable to C11a v0.1).
- 5 backlog items.
- Estimated walks to LOCK: **2-3** per Ramalingam directive.
- Walk #2 should resolve at minimum: F-v1-2 (pop_size benchmark),
  F-v1-3 (max_generations), F-v1-7 (stagnation robustness), and
  Q1-Q7 directional confirmation.

---

## § 12 — Backlog enumeration (per Rule 9)

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-237 | Cross-platform replay CI matrix + Decimal geometry | S35 (carry; affects C11b PRNG verification) | M |
| B-NEW-P | Upstream `severity_tier` ClassVar amendment cluster | S37 W#4 (carry; required before C11b build) | XS |
| B-NEW-V | C11b refinement scope expansion | v0.1 Q4 | M |
| B-NEW-W | C11b hypervolume diversity metric | v0.1 Q5 | M |
| B-NEW-X | C11b adaptive NSGA-II hyperparameters | future tuning | M |
| B-NEW-Y | C11b cross-topology Pareto aggregation | v0.1 Q2 | M |
| B-NEW-Z | C11b deterministic-parallel-NSGA-II | scaling pressure | L |

**Backlog summary**: 7 items (2 carried + 5 new at v0.1).

---

## § 13 — Complexity Budget (NEW v0.1)

Adopting C11a's § 13 governance pattern from the start.

### v1 surface area: 9 subsystems

| # | Subsystem | Justified by |
|---|---|---|
| 1 | NSGA-II core algorithm (sort + crowding + selection + crossover + mutation) | Mission |
| 2 | EvaluatorProtocol + StubEvaluator | Mission (objectives via injection) |
| 3 | RefinedCandidate + ObjectiveVector schema | Mission |
| 4 | Per-topology PRNG seed derivation | Determinism |
| 5 | Evaluator cache (single-batch, size-bounded) | Runtime |
| 6 | Convergence detection (Pareto-front-stable-N-gens) | Mission |
| 7 | Constraint handling (NSGA-II-CDP) | Mission (HARD constraints) |
| 8 | Provenance + diagnostics + replay-version-hashes | Replay |
| 9 | Phase-0 validation (purity contract, single-thread, config sanity) | Startup safety |

**Borrow from C11a (no v1 surface cost)**:
- canonical_serialize utility
- severity_tier ClassVar pattern
- UpstreamReplayVersionHashes
- PurityAttestation pattern
- single-threaded contract
- cache_relevant field annotation discipline

### Walk #2+ governance rule

Per Ramalingam's 2-3 walk target: Walk #2 budget cap is **0-1 new v1
subsystems**. Walk #3 (if needed) caps at **0**. Anything else routes
to backlog or rejection.

---

**End of v0.1 PROPOSED.** Awaits Ramalingam reading + Walk #2 direction.
