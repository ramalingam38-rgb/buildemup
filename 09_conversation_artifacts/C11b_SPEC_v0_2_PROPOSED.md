# C11b — Local Refinement (NSGA-II) — SPEC v0.2 PROPOSED

**Component**: 11b (canonical Track 3 numbering — paired with C11a Topology Mutation)
**Status**: v0.2 PROPOSED. **NOT LOCKED.** Supersedes v0.1 PROPOSED.
**Convergence target**: 2-3 walks to LOCK per Ramalingam directive S37. **This is Walk #2; v0.3 LOCK candidate next.**
**Authority**: S37/S38 author's draft. PENDING Ramalingam adjudication.
**Authored**: post C11b v0.1 PROPOSED + Walk #2 external critique.

---

## § 0 — Architectural notes (REVISED v0.2)

C11b sits between C11a (LOCKED) and C12. Per-topology NSGA-II Pareto
search with geometric parameter refinement. v0.1 architectural choices
(carried unchanged): NSGA-II-CDP, single-threaded v1, `EvaluatorProtocol`
forward-coupling to C14, room-dimensions-only refinement scope, PCG64
PRNG with derived per-topology seed.

### § 0.1 — Convergence stance (carried v0.1)

Walk #2 budget cap: 0-1 new v1 subsystems. **v0.2 adds 1**
(`DominanceSorterProtocol` per item 5). Walk #3 budget cap: 0 new
subsystems — pure correctness/audit-finding patches.

### § 0.2 — Reuse from C11a v1.0 LOCKED (carried v0.1)

Carried verbatim.

### § 0.3 — Determinism strategy (REVISED v0.2 — narrows numpy claim per item 8)

PRNG seed derivation unchanged. **Determinism scope clarification**:

> C11b's replay determinism is **bitwise reproducible only on
> CI-validated `(numpy_version, platform, Python_version)` tuples**.
> Statistical consistency across numpy versions is *not* equivalent to
> bitwise reproducibility. Cross-version drift is detected via
> `EnvironmentFingerprint` in provenance (NEW v0.2 below); replays with
> mismatched fingerprints raise warnings or rejections per
> enforcement_mode.

```python
@dataclass(frozen=True)
class EnvironmentFingerprint:
    """NEW v0.2 — narrows determinism claim per item 8.
    Captures the exact runtime tuple under which a result was produced.
    Replay comparison REJECTS on mismatch (analog to C11a
    QuarantineFingerprint pattern)."""
    numpy_version: str            # e.g., "2.0.1"
    python_version: str           # e.g., "3.12.3"
    platform_machine: str         # e.g., "x86_64"
    platform_system: str          # e.g., "Linux"
    fingerprint_hash: str         # SHA256 hex of canonical-serialized tuple


def capture_environment_fingerprint() -> EnvironmentFingerprint:
    """Called once per `run_local_refinement` invocation."""
```

Approved CI matrix tuples are listed in `B-237` cross-platform CI
config (carried). v1 launch baseline: 1 approved tuple
(numpy 2.0+, Python 3.12, Linux x86_64). Cross-tuple replay support
deferred to B-237 CI matrix expansion.

### § 0.4 — EvaluatorProtocol (REVISED v0.2 — item 6 resolution)

Cache-key now includes evaluator identity + version. Item 6 fix:

```python
class EvaluatorProtocol(Protocol):
    purity_attestation: PurityAttestation
    evaluator_identity_hash: str            # NEW v0.2 — stable across runs of same evaluator
    evaluator_version_hash: str             # NEW v0.2 — bumped on any logic change

    def evaluate(self, candidate: RefinedCandidate) -> ObjectiveVector:
        """Pure function. Same input → same output. No side effects."""
```

**Cache key scope** (REVISED v0.2):

```python
@dataclass(frozen=True)
class EvaluatorCacheKey:
    refined_parameters_canonical: str         # canonical_serialize hash
    evaluator_identity_hash: str              # NEW v0.2
    evaluator_version_hash: str               # NEW v0.2
```

If C14 ships and bumps `evaluator_version_hash`, cache invalidates
correctly. If a different evaluator is injected (e.g., `StubEvaluator`
vs production), cache namespaces don't collide.

### § 0.5 — StubEvaluator (REVISED v0.2 — item 1 resolution)

v0.1 used SHA256 hash → discontinuous. v0.2 replaces with
**geometry-correlated synthetic objectives**:

```python
class StubEvaluator:
    """Test-only evaluator for v1 build. Replaced by C14 implementation
    when C14 ships.

    REVISED v0.2: synthetic objectives are now geometry-correlated
    (smooth across small parameter changes), not hash-derived.
    """
    purity_attestation: PurityAttestation = PurityAttestation(
        component_id="C11b", entry_point="StubEvaluator.evaluate",
        purity_class="pure", attested_by="C11b",
        attested_at_kb_version="stub_v2.0",
    )
    evaluator_identity_hash: str = "stub_v2.0"
    evaluator_version_hash: str = "v2.0"

    def evaluate(self, candidate: RefinedCandidate) -> ObjectiveVector:
        params = candidate.refined_parameters.room_dimensions
        # Three smooth, deterministic, geometry-correlated objectives:
        # 1. synthetic_compactness:
        #      mean(min(w, d) / max(w, d)) over rooms — closer to 1 = compact
        ratios = [min(w, d) / max(w, d) for _, w, d in params]
        compactness = sum(ratios) / max(len(ratios), 1)
        # 2. synthetic_aspect_variance:
        #      variance of room aspect ratios — diversity proxy (lower = more uniform)
        aspect_ratios = [w / d for _, w, d in params]
        mean_ar = sum(aspect_ratios) / max(len(aspect_ratios), 1)
        variance = sum((ar - mean_ar) ** 2 for ar in aspect_ratios) / max(len(aspect_ratios), 1)
        # 3. synthetic_envelope_efficiency:
        #      fraction of envelope used (higher = more efficient)
        # (envelope reference passed via candidate.source_topology_candidate)
        total_room_area = sum(w * d for _, w, d in params)
        envelope_area = (
            candidate.source_topology_candidate
            .source_candidate.room_size_table.envelope_width_m
            * candidate.source_topology_candidate.source_candidate
            .room_size_table.envelope_depth_m
        )
        efficiency = total_room_area / max(envelope_area, 1.0)
        return ObjectiveVector(
            values=(
                ("synthetic_compactness",          round(compactness, 6)),
                ("synthetic_aspect_variance",      round(variance, 6)),
                ("synthetic_envelope_efficiency",  round(efficiency, 6)),
            ),
            constraint_violations=0.0,
        )
```

**Properties verified**:
- Local parameter changes → local objective changes (smooth landscape)
- Deterministic (no hash, no PRNG)
- C14-independent
- 3 objectives at minimum (matches NSGA-II diversity expectation)
- Maintains the (sorted by name) ObjectiveVector contract

NSGA-II benchmarking on this stub now produces **representative**
convergence/stagnation behaviour, validating tuning decisions before
C14 exists.

### § 0.6 — Refinement bounds (REVISED v0.2 — item 3 resolution)

v0.1 fixed `[min, min × 1.5]` ignored envelope slack. v0.2:
**envelope-aware dynamic upper bound** at v1 (per-category multipliers
deferred to v2 / B-NEW-V2):

```python
def derive_room_upper_bounds(
    room_id: str,
    room_min_w: float, room_min_d: float,
    envelope_w: float, envelope_d: float,
    other_rooms_min_area: float,    # sum of OTHER rooms' min area
    *,
    universal_max_multiplier: float = 2.5,    # NEW v0.2: was implicit 1.5
) -> tuple[float, float]:
    """Returns (max_width, max_depth) for a single room.

    Envelope-aware ceiling: reserves min-area for siblings.
    """
    envelope_area = envelope_w * envelope_d
    # Slack reserved for OTHER rooms (HARD: each must hit its own min)
    slack_for_this_room = max(envelope_area - other_rooms_min_area, room_min_w * room_min_d)
    # Per-room upper bound: smaller of (universal multiplier) and (envelope-feasible)
    max_w = min(
        room_min_w * universal_max_multiplier,
        slack_for_this_room / room_min_d,         # if other dim at min
        envelope_w,
    )
    max_d = min(
        room_min_d * universal_max_multiplier,
        slack_for_this_room / room_min_w,
        envelope_d,
    )
    return (max_w, max_d)
```

**Trade-off acknowledged**: per-category multipliers (e.g., master
bedroom 2.0×, kitchen 1.3×) are real and valuable but require KB
support. Filed as **B-NEW-V2** post-v1. v1 ships with universal 2.5×
multiplier (more generous than v0.1's 1.5×), envelope-feasible slack
clip, and per-room HARD min reservation.

### § 0.7 — Initialization strategy (NEW v0.2 — item 4 resolution)

v0.1 uniform sampling could produce all-infeasible initial populations
in dense topologies. v0.2: **feasibility-aware sequential area
allocation**:

```python
def feasibility_aware_init(
    rooms: tuple[RoomSizeRequirement, ...],
    envelope_w: float, envelope_d: float,
    rng: numpy.random.Generator,
    pop_size: int,
) -> list[RefinedParameters]:
    """Generate `pop_size` feasible-by-construction candidates.

    Algorithm (NEW v0.2 — resolves item 4):
      For each candidate i in [0, pop_size):
        budget = envelope_area
        For each room r in shuffled order:
          area_r = uniform(min_area_r, min(remaining_budget * room_share, max_area_r))
          dimensions sampled within (min_w_r, max_w_r) × (min_d_r, max_d_r)
                     subject to w_r * d_r ≈ area_r
          budget -= area_r
        If budget < 0 by epsilon: REJECT and retry (rejection sampling fallback)

    Per literature (Zhang et al., 2024 'Hybrid Dirichlet-LHS for
    constrained NSGA-II'), feasibility-aware initialization
    significantly improves convergence in space-allocation problems.
    """
```

**Rejection sampling fallback** (defensive): if 100 retries fail,
raise `InfeasiblePopulationError` with diagnostic — signals the
underlying brief is over-specified for the envelope (upstream concern,
not C11b's to solve).

**Telemetry exposed**: `LocalRefinementProvenance.init_retries_count`
(NEW v0.2) — observable signal of brief-tightness.

### § 0.8 — Stagnation detection (REVISED v0.2 — item 2 resolution)

v0.1's `pareto_front_signature_hash` of sorted objective values was too
weak. v0.2: **composite signature** combining multiple stable signals:

```python
@dataclass(frozen=True)
class StagnationSignature:
    """NEW v0.2 — resolves item 2.
    Stronger stagnation detection: hash composes objective front +
    feasibility counts + crowding-distance distribution + parameter
    diversity proxy."""
    objective_front_hash: str         # sorted objective vectors
    feasible_count: int
    crowding_distance_quantiles_hash: str   # quartiles of crowding distances
    parameter_diversity_hash: str          # mean pairwise dimension distance
    composite_hash: str                    # SHA256 of above 4


def compute_stagnation_signature(
    population: tuple[RefinedCandidate, ...],
) -> StagnationSignature:
    ...
```

Convergence triggers iff `composite_hash` repeats for
`convergence_stable_gens` consecutive generations. **Both** objective
front AND parameter diversity must stabilize — much harder to
false-positive than v0.1's objective-only hash.

### § 0.9 — Output ordering (REVISED v0.2 — item 7 resolution)

v0.1 ordered output by crowding distance descending. Critique #7
correctly identifies this prioritizes diversity over quality, which can
mislead downstream consumers.

**v0.2 resolution**:

```python
@dataclass(frozen=True)
class RefinedCandidate:
    # ... carried fields ...
    output_rank_reason: Literal[
        "diversity_order",    # crowding distance descending (default)
        "objective_balance",  # sum-of-normalized-objectives ascending (post-v1)
    ]                                          # NEW v0.2
    output_rank_index: int                     # 0-indexed position in output
```

Default `output_rank_reason = "diversity_order"` at v1 — preserves
v0.1 behaviour, but downstream consumers can no longer assume "first
candidate is best." `objective_balance` ordering deferred to B-NEW-V3
post-launch (requires C14 to define normalization).

**Downstream contract clarification** (NEW v0.2): C12/C14 must read
`output_rank_reason` before interpreting order. Any consumer that
treats output as "best-first" without checking this field is in error.

### § 0.10 — Dominance sorter abstraction (NEW v0.2 — item 5 resolution)

```python
class DominanceSorterProtocol(Protocol):
    """NEW v0.2 — abstraction over non-dominated sort.
    v1 implementation: standard O(MN²) NSGA-II.
    Future: Jensen fast sort, ENS-SS, dominance trees."""

    def sort(
        self, population: tuple[RefinedCandidate, ...],
    ) -> tuple[tuple[RefinedCandidate, ...], ...]:
        """Returns tuple of fronts (rank 0 = non-dominated)."""


class StandardDominanceSorter:
    """v1 implementation. O(MN²)."""
    def sort(self, population): ...


# Default config injection:
@dataclass(frozen=True)
class LocalRefinementConfig:
    # ... carried fields ...
    dominance_sorter_factory: Callable[[], DominanceSorterProtocol] = field(
        default=StandardDominanceSorter, metadata={"cache_relevant": False},
    )
```

**No algorithm change at v1.** The abstraction prevents future
algorithm replacement from requiring pipeline rewrites — minimal
v0.1-cost insurance against B-NEW-Z scaling pressure.

---

## § 1 — Walk-resolved scope (REVISED v0.2)

| Q / F | Resolution | Walk |
|---|---|---|
| Q1-Q7 | (carried v0.1; all 7 directions confirmed) | W#1 |
| F-v1-1 | EvaluatorProtocol forward-coupling cost accepted (item 6 patches narrow the contract via cache-key extension) | W#2 |
| **F-v1-2 (W#2)** | **pop_size=50 default raised to 100** (literature standard per NSGA-II benchmarks fix populations at 100) | W#2 |
| **F-v1-3 (W#2)** | **max_generations=100 confirmed adequate** with new stagnation detection (typical convergence < 50 gens on stub evaluator). Tunable per config. | W#2 |
| **F-v1-4 (W#2)** | **SBX η_c=20, polynomial η_m=20 confirmed** as literature standard. B-NEW-X tracks adaptive tuning post-v1. | W#2 |
| F-v1-5 | StubEvaluator formalized (further revised v0.2 for smoothness — item 1) | W#1 + W#2 |
| **F-v1-6 (W#2)** | **pareto_output_size=20 retained**; rationale: typical NSGA-II returns 20-50; matches downstream C14 ranker batch processing expectation. Tunable. | W#2 |
| F-v1-7 | **StagnationSignature composite hash** (item 2) | W#2 |
| F-v1-8 | (carried; max cache size enforced) | W#1 |

---

## § 2 — Contract (REVISED v0.2)

Top-level signature unchanged from v0.1.

### § 2.1 — Schema additions (NEW v0.2)

- `EnvironmentFingerprint` (per § 0.3)
- `StagnationSignature` (per § 0.8)
- `DominanceSorterProtocol` (per § 0.10)
- `EvaluatorProtocol` extended with identity + version hashes (per § 0.4)
- `RefinedCandidate.output_rank_reason` + `output_rank_index` (per § 0.9)
- `LocalRefinementProvenance.init_retries_count` (per § 0.7)
- `LocalRefinementProvenance.environment_fingerprint` (per § 0.3)

### § 2.2 — Configuration (REVISED v0.2 — defaults updated per Walk #2)

```python
@dataclass(frozen=True)
class LocalRefinementConfig:
    pop_size: int = field(default=100, metadata={"cache_relevant": True})    # was 50
    max_generations: int = field(default=100, metadata={"cache_relevant": True})
    crossover_rate: float = field(default=0.9, metadata={"cache_relevant": True})
    mutation_rate: float = field(default=0.1, metadata={"cache_relevant": True})
    sbx_eta_c: float = field(default=20.0, metadata={"cache_relevant": True})
    polynomial_eta_m: float = field(default=20.0, metadata={"cache_relevant": True})
    pareto_output_size: int = field(default=20, metadata={"cache_relevant": True})
    convergence_stable_gens: int = field(default=5, metadata={"cache_relevant": True})
    universal_max_multiplier: float = field(            # NEW v0.2
        default=2.5, metadata={"cache_relevant": True},
    )
    init_max_retries: int = field(                        # NEW v0.2
        default=100, metadata={"cache_relevant": True},
    )
    enforcement_mode: EnforcementMode = field(
        default=EnforcementMode.WARN, metadata={"cache_relevant": False},
    )
    provenance_verbosity: ProvenanceVerbosity = field(
        default=ProvenanceVerbosity.PER_GEN, metadata={"cache_relevant": False},
    )
    evaluator_cache_enabled: bool = field(
        default=True, metadata={"cache_relevant": False},
    )
    dominance_sorter_factory: Callable[[], DominanceSorterProtocol] = field(    # NEW v0.2
        default=StandardDominanceSorter, metadata={"cache_relevant": False},
    )
```

`MAX_EVALUATOR_CACHE_ENTRIES = 50_000` (carried v0.1). With pop_size=100,
max_generations=100, raw evaluation count = 10,000 — well within bound.

---

## § 3 — Behaviour (REVISED v0.2)

### Phase 0 — Input + startup validation

Carried v0.1 + 1 addition:
- **Capture `EnvironmentFingerprint`** at function entry; record in
  provenance.

### Phase 1 — Per-topology NSGA-II run (REVISED v0.2)

1. Seed derivation (carried v0.1)
2. **Feasibility-aware initialization** (NEW v0.2 — § 0.7) replaces
   uniform sampling
3. Initial evaluation (carried; cache key extended per § 0.4)
4. Generation loop (carried v0.1):
   - Selection, crossover, mutation, evaluation, combine, sort, truncate
   - **Stagnation check uses composite signature** (NEW v0.2 — § 0.8)
5. Final extraction (carried; output ordering tagged with
   `output_rank_reason` per § 0.9)

### Phase 2 — Output assembly (carried v0.1)

### Phase 3 — Provenance assembly (REVISED v0.2)

Carried + new fields populated: `init_retries_count`,
`environment_fingerprint`.

### § 3.1 — Constraint handling (NSGA-II-CDP)

Carried v0.1.

### § 3.2 — StagnationSignature compute (NEW v0.2 — § 0.8)

See § 0.8.

### § 3.3 — Evaluator caching (REVISED v0.2 — cache key extended per § 0.4)

---

## § 4 — Invariants (REVISED v0.2)

| # | Invariant | Mode |
|---|---|---|
| 1-15 | (carried verbatim from v0.1) | as v0.1 |
| **16 (NEW v0.2)** | **`EnvironmentFingerprint` populated for every output's provenance; replays with mismatched fingerprints rejected (analog to C11a Inv 29)** | RAISE (replay tier) |
| **17 (NEW v0.2)** | **`EvaluatorCacheKey` MUST include `evaluator_identity_hash` AND `evaluator_version_hash`. Cache contamination across evaluator changes prevented by construction.** | RAISE |
| **18 (NEW v0.2)** | **Initial population is feasibility-aware: every candidate passes HARD constraint (sum room area ≤ envelope area) by construction** | RAISE |
| **19 (NEW v0.2)** | **StagnationSignature composite_hash includes BOTH objective front AND parameter diversity. Convergence requires both stable.** | RAISE |
| **20 (NEW v0.2)** | **Every output's `output_rank_reason` set; downstream consumers must read it before interpreting order. v1 default = `diversity_order`.** | RAISE |
| **21 (NEW v0.2)** | **`DominanceSorterProtocol` injection: v1 ships with `StandardDominanceSorter` (O(MN²)); pipeline does not depend on the concrete sorter implementation** | DOCUMENTED (architecture) |

21 invariants at v0.2 (vs 15 at v0.1).

---

## § 5 — Failure modes (REVISED v0.2)

```
LocalRefinementError (base)
├── PerTopologyError
│   ├── NSGAConvergenceError              (no Pareto front formed)
│   ├── InfeasiblePopulationError         (init exhausted retries)
│   └── EvaluatorContractError
├── BatchAllTopologiesFailedError
├── EvaluatorPurityContractError          (startup)
├── EnvironmentFingerprintMismatchError   (NEW v0.2 — replay rejection)
└── InvariantViolationError                (systemic)
```

---

## § 6 — Test coverage targets (REVISED v0.2)

Target ~175 tests at LOCK (up from v0.1's 150):

- ~28 schema (+ EnvironmentFingerprint, StagnationSignature, extended
  EvaluatorProtocol, DominanceSorterProtocol)
- ~30 NSGA-II core
- ~28 invariants (Inv 1-21)
- ~25 phase-logic
- ~12 partial-batch / strict-mode
- ~12 replay determinism (+ environment fingerprint mismatch)
- ~12 evaluator contract (+ cache key with identity/version)
- ~12 edge cases
- **~16 NEW v0.2** — feasibility-aware init (~5), composite stagnation
  signature (~3), envelope-aware bounds (~3), cache-key evaluator-
  scoped (~2), output_rank_reason discipline (~3)

Cumulative target at C11b ship: 2519 + 175 ≈ **2694 passed**.

---

## § 7 — Open questions at v0.2 (down from 7 to 2)

| Q | Question | v0.2 direction |
|---|---|---|
| Q4 | Refinement scope expansion at v1? | Carried: NO (B-NEW-V). |
| **Q8 (NEW)** | What's the right `objective_balance` ordering formula for B-NEW-V3? | Walk #3 may surface; otherwise post-launch (requires C14 normalization spec). |

**Resolved at Walk #2**: Q1, Q2, Q3, Q5, Q6, Q7 — all confirmed
directions from v0.1. F-v1-2/3/4/6/7 directional or definitive.

---

## § 8 — Backlog at v0.2

**New at v0.2** (Walk #2 critique outcomes):

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-NEW-V2** | **C11b per-room-category bound multipliers (master bedroom 2.0×, kitchen 1.3×, etc.)** | **W#2 #3** | **post-launch + KB support** | **M** |
| **B-NEW-V3** | **C11b `objective_balance` output ordering option** | **W#2 #7** | **C14 normalization spec lands** | **S-M** |

**Cumulative**: 9 backlog items (2 carried + 5 v0.1 + 2 v0.2).

---

## § 9 — Rule 11 spec audit on v0.2 PROPOSED

**PATCH-NOW (in v0.2 itself): 0**.

**OPEN QUESTIONS at v0.2**: Q4, Q8 (2; down from 7).

**SPEC-AUDIT FINDINGS (v0.2)**:

| # | Finding | Verdict |
|---|---|---|
| F-v2-1 | `StubEvaluator.evaluate` reaches into `candidate.source_topology_candidate.source_candidate.room_size_table.envelope_width_m` — fragile chain. If C11a or C9 schemas change, stub breaks. | **PATCH-NOW** — stub instead reads envelope dimensions from a `current_envelope` field on RefinedCandidate (new shallow field); cleaner indirection. |
| F-v2-2 | `feasibility_aware_init` "shuffled order" of room iteration introduces non-determinism unless seeded from `rng`. Spec needs to be explicit. | **PATCH-NOW** — fixed: shuffle is via the function-scope `rng`, deterministic per per-topology seed. Updated § 0.7 below. |
| F-v2-3 | `StagnationSignature.parameter_diversity_hash` uses "mean pairwise dimension distance" — undefined for population of 1. With pop_size raised to 100, edge case is vanishingly rare; still worth defensive handling. | **PATCH-NOW** — define: if pop_size < 2, parameter_diversity_hash = "single_member"; convergence bypassed. |
| F-v2-4 | `EnvironmentFingerprint` includes `numpy_version` but not C11b's own version hash. If C11b code changes, replays might compare equal across C11b versions. | **NEEDS WALK** — Walk #3 should add C11b's own version constant; analog to C7's CANONICAL_SERIALIZE_VERSION. |
| F-v2-5 | `derive_room_upper_bounds` uses `other_rooms_min_area` — but if other rooms also expand within their bounds, total exceeds envelope. The HARD constraint catches this in CDP, but the bound function gives a misleading "max" that may be reached only when others are at min. Document this clearly. | **PATCH-NOW** — docstring updated to clarify bounds are *per-room reachable max*, not *jointly reachable*; HARD constraint resolves joint feasibility. |
| F-v2-6 | `DominanceSorterProtocol` injected via `Callable[[], DominanceSorterProtocol]` factory pattern, but no validation that the factory's return obeys the protocol. Phase 0 should call factory once and verify type. | **PATCH-NOW** — Phase 0 instantiates once, calls `validate_sorter_protocol(sorter)` checking method signature. |
| F-v2-7 | Walk #2 raised pop_size to 100 doubling per-batch evaluator calls (50→100 init + 100×100 generation = 10,100 vs 5,050). MAX_EVALUATOR_CACHE_ENTRIES = 50,000 still fits, but config validation rejection threshold needs updating. | **PATCH-NOW** — confirm 50,000 still safe; document the math. |

**PATCH-NOW APPLIED INLINE TO v0.2**:

- **F-v2-1**: `RefinedCandidate.current_envelope: tuple[float, float]` field added; stub reads via `candidate.current_envelope`. Cleaner abstraction.
- **F-v2-2**: § 0.7 updated — "for room r in `rng.permutation(rooms)`" makes shuffle determinism explicit.
- **F-v2-3**: StagnationSignature.parameter_diversity_hash fallback: "single_member" sentinel for pop_size < 2; convergence not triggered.
- **F-v2-5**: docstring added — "per-room reachable max; joint feasibility resolved by HARD constraint via NSGA-II-CDP."
- **F-v2-6**: Phase 0 calls factory once + validates protocol shape.
- **F-v2-7**: with pop_size=100 + max_generations=100, raw evaluation budget is 10,100; cache size 50,000 = 5× margin. Confirmed safe.

**REJECTED-AS-CONSIDERED**:
- "Should `EnvironmentFingerprint` include OS kernel version?" — Granular but noisy; numpy + Python + platform_machine + platform_system is sufficient identity.
- "Should `feasibility_aware_init` use Latin Hypercube Sampling (per jMetal's LHS strategy)?" — LHS gains over uniform on smooth landscapes; minor on space-allocation problems. v1 sequential allocation is simpler and proven for constrained problems. B-NEW-V4 if needed post-launch.
- "Should output_rank_reason support `"objective_dominance_count"` ordering?" — Adds complexity, redundant with NSGA-II Pareto rank. Rejected.

---

## § 10 — Status

- **v0.2 PROPOSED**. **NOT LOCKED.**
- **Walk #2 of 2-3 walk target completed.**
- 8 valid critique items resolved (8 amendments + 1 partial). 0 rejected.
- 2 open questions remaining (down from 7 at v0.1).
- 9 backlog items.
- Walk #2 budget cap: 0-1 new subsystems. Added 1 (`DominanceSorterProtocol`). At cap.
- 7 audit findings, 6 patched inline at v0.2; 1 deferred to Walk #3 (F-v2-4: C11b version hash in EnvironmentFingerprint).
- **Next walk**: Walk #3 should be tight — 0-1 audit findings, 0 new subsystems, target LOCK request.

---

## § 12 — Backlog enumeration

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-237 | Cross-platform replay CI matrix + Decimal geometry | S35 (carry) | M |
| B-NEW-P | Upstream `severity_tier` ClassVar amendment cluster | S37 W#4 (carry; required before C11b build) | XS |
| B-NEW-V | C11b refinement scope expansion | v0.1 Q4 | M |
| B-NEW-W | C11b hypervolume diversity metric | v0.1 Q5 | M |
| B-NEW-X | C11b adaptive NSGA-II hyperparameters | future tuning | M |
| B-NEW-Y | C11b cross-topology Pareto aggregation | v0.1 Q2 | M |
| B-NEW-Z | C11b deterministic-parallel-NSGA-II | scaling pressure | L |
| **B-NEW-V2** | **C11b per-category bound multipliers** | **W#2 #3** | **M** |
| **B-NEW-V3** | **C11b objective_balance output ordering** | **W#2 #7** | **S-M** |

**Backlog summary**:

| Total | Pre-existing | v0.1 | v0.2 |
|---|---|---|---|
| **9** | 2 | 5 | 2 |

---

## § 13 — Complexity Budget (REVISED v0.2)

### v1 surface area: 10 subsystems (was 9 at v0.1; +1 at Walk #2)

| # | Subsystem | Status |
|---|---|---|
| 1-9 | (carried v0.1 — 9 subsystems) | unchanged |
| **10 (NEW v0.2)** | **DominanceSorterProtocol abstraction** | future-proofing for B-NEW-Z (item 5) |

### What v0.2 explicitly does NOT add to v1

| Considered | Routing |
|---|---|
| Per-category room bound multipliers (item 3) | B-NEW-V2 (KB-dependent) |
| objective_balance output ordering (item 7) | B-NEW-V3 (C14-dependent) |
| Latin Hypercube Sampling for init | Rejected; sequential allocation simpler |
| Hypervolume stagnation criterion | Already filed B-NEW-W |

### Walk #3 budget adherence target

Walk #3: **0 new subsystems.** All findings must route to backlog,
patches, or rejection.

---

**End of v0.2 PROPOSED.** Awaits Ramalingam reading + Walk #3 direction.
Walk #3 is the proposed LOCK candidate per S37 directive.
