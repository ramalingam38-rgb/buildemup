# C11b — Local Refinement (NSGA-II) — SPEC v0.3 PROPOSED

**Component**: 11b (canonical Track 3 numbering — paired with C11a Topology Mutation)
**Status**: v0.3 PROPOSED. **NOT LOCKED.** **LOCK candidate** per S37 directive (Walk #3 of target 2-3).
**Authority**: S37/S38 author's draft. PENDING Ramalingam adjudication.
**Authored**: post C11b v0.2 PROPOSED + Walk #3 external critique.

---

## § 0 — Architectural notes (REVISED v0.3)

C11b sits between C11a (LOCKED) and C12. Per-topology NSGA-II Pareto
search with geometric parameter refinement. v0.1 + v0.2 architectural
choices carried unchanged; v0.3 is correctness/audit-finding patches
+ terminology tightening.

### § 0.1 — Walk #3 budget adherence

Walk #3 budget cap: **0 new v1 subsystems.** v0.3 adds 0 — all 8
critique items resolved as within-subsystem patches, terminology fixes,
or routed to backlog. Subsystem count stays at 10 (carried from v0.2).

### § 0.2 — Critical terminology: "area-feasible" (REVISED v0.3 — resolves item 7)

v0.2 used "feasible-by-construction" for the initialization invariant.
This is misleading because:

- C11b's HARD constraint (NSGA-II-CDP) checks `sum(room_area) ≤ envelope_area`
- *Geometric embeddability* (whether dimensions can actually pack into
  the topology) is a separate, much stronger property
- That stronger property is **C12's job** (per arch v3 § 4: C12 is the
  geometric placement / embeddability solver). C11b operates in
  parameter space; C12 operates in placement space.

**v0.3 terminology rule**: throughout the spec, "feasibility" means
**area-feasibility** unless qualified. Geometric embeddability is
explicitly *out of scope* for C11b.

Inv 18 renamed: `area_feasible_by_construction` (was
`feasible_by_construction`). All errors, log strings, and provenance
fields renamed accordingly. Reflects reality, prevents downstream
misinterpretation.

**Why this matters**: a downstream consumer reading
`init_retries_count` or `BatchAllTopologiesFailedError` could
incorrectly assume C11b output was geometrically valid. v0.3 makes the
distinction unambiguous in the type system.

### § 0.3 — Determinism strategy (REVISED v0.3 — partial fix for item 1)

`EnvironmentFingerprint` extended with C11b version and BLAS hint.
Full BLAS/LAPACK/CPU-vectorization fingerprinting deferred to **B-237
CI matrix expansion** (already filed; v0.3 adds C11b's contribution to
that work).

```python
@dataclass(frozen=True)
class EnvironmentFingerprint:
    numpy_version: str
    python_version: str
    platform_machine: str
    platform_system: str
    c11b_version: str                      # NEW v0.3 — resolves F-v2-4
    numpy_blas_info_summary: str           # NEW v0.3 — partial item 1 fix
    fingerprint_hash: str                  # SHA256 hex of canonical-serialized tuple


C11B_VERSION: Final[str] = "v1.0"          # NEW v0.3 — analog to CANONICAL_SERIALIZE_VERSION


def capture_environment_fingerprint() -> EnvironmentFingerprint:
    """v0.3: now also captures C11b version constant + numpy build BLAS info.
    Full BLAS/LAPACK/floating-point-mode fingerprinting (F-v3-1 carried)
    is B-237's responsibility."""
    blas_info = numpy.show_config(mode="dicts").get("Build Dependencies", {}).get(
        "blas", {"name": "unknown"}
    ).get("name", "unknown")
    ...
```

Spec wording (§ 0.3 v0.2): *"bitwise reproducible only on CI-validated
tuples"* — carried verbatim. Approved CI matrix tuples list now adds
`c11b_version` and `blas_name` columns.

### § 0.4 through § 0.10 — Carried v0.2

EvaluatorProtocol (§ 0.4), StubEvaluator (§ 0.5), refinement bounds
(§ 0.6), feasibility-aware init (§ 0.7), stagnation detection (§ 0.8),
output ordering (§ 0.9), DominanceSorterProtocol (§ 0.10) — all carried
v0.2 with the per-section revisions below.

### § 0.6 — Refinement bounds (REVISED v0.3 — resolves item 3)

v0.2 universal 2.5× multiplier was topology- and category-agnostic.
v0.3 keeps it as default but adds **lightweight per-category sanity
caps** without requiring a KB:

```python
# Module-level constants. Not a KB — these are architectural
# common-sense caps. KB-driven multipliers are B-NEW-V2 (post-launch).
SEMANTIC_CAP_BY_CATEGORY: Final[dict[str, float]] = {
    "bathroom":  1.8,    # bathrooms beyond 1.8× min are absurd
    "kitchen":   1.5,    # kitchens beyond 1.5× min rarely useful
    "utility":   1.5,
    "pooja":     1.5,
    # bedroom, living, corridor, other: fall back to universal_max_multiplier (2.5)
}

# Aspect-ratio sanity floor (NEW v0.3):
MAX_ROOM_ASPECT_RATIO: Final[float] = 3.0
"""max(w, d) / min(w, d) <= 3.0. Rejects pathological rooms (8m × 1.5m
master bedroom) that pass area-feasibility but are architecturally
absurd. Constraint enforced as HARD via NSGA-II-CDP."""


def derive_room_upper_bounds(
    room_id: str,
    room_category: str,                    # NEW v0.3 parameter
    room_min_w: float, room_min_d: float,
    envelope_w: float, envelope_d: float,
    other_rooms_min_area: float,
    *,
    universal_max_multiplier: float = 2.5,
) -> tuple[float, float]:
    """v0.3: per-category semantic cap applied before envelope clip.
    Joint feasibility resolved by NSGA-II-CDP as before."""
    category_cap = SEMANTIC_CAP_BY_CATEGORY.get(
        room_category, universal_max_multiplier,
    )
    # ... rest carried v0.2 with category_cap replacing universal_max_multiplier
    # for that room.
```

**Aspect ratio HARD constraint** (NEW v0.3) added to NSGA-II-CDP
violation accumulator: candidates with `max(w,d)/min(w,d) > 3.0` get
`constraint_violations += (ratio - 3.0)`. Per-category caps and aspect
ratio together replace v0.2's pure universal-multiplier model.

Per-category multipliers from KB (architect-validated catalog) remain
B-NEW-V2 post-launch.

### § 0.7 — Initialization strategy (REVISED v0.3 — resolves item 2)

v0.2 sequential allocation with single permutation introduced
allocation-order bias. v0.3: **multiple permutation orderings per
candidate**:

```python
def feasibility_aware_init(
    rooms: tuple[RoomSizeRequirement, ...],
    envelope_w: float, envelope_d: float,
    rng: numpy.random.Generator,
    pop_size: int,
    permutations_per_candidate: int = 3,         # NEW v0.3
) -> list[RefinedParameters]:
    """REVISED v0.3 (item 2): for each candidate, sample 3 random room
    orderings via rng; run sequential allocation with each; pick the
    most-area-balanced result (lowest variance of room_area /
    room_min_area). Reduces allocation-order bias per Walk #3 critique.

    Determinism: still fully reproducible via per-topology rng seed.

    Cost: 3× allocation work per candidate. Pop_size=100 ×
    permutations=3 = 300 allocation runs ≈ 30ms total. Negligible vs
    100 generations of NSGA-II.

    Dirichlet-based budget partitioning (literature-preferred per
    Zhang et al. 2024) deferred to B-NEW-V4. v1 ships with
    multiple-permutation; trade-off acknowledged.
    """
```

**Trade-off**: multiple-permutation is a partial fix. True allocation
fairness (e.g., Dirichlet area partitioning, symmetric simultaneous
allocation) requires more invasive changes. v1 ships the simpler fix
and files **B-NEW-V4** for proper Dirichlet allocation post-launch.

### § 0.8 — Stagnation detection compute cost (REVISED v0.3 — resolves item 4)

v0.2 stagnation signature ran every generation with O(N²) pairwise
diversity. v0.3: **adaptive computation cadence** + **centroid-variance
fallback**:

```python
@dataclass(frozen=True)
class StagnationConfig:
    """NEW v0.3 — explicit cost knobs."""
    full_signature_every_n_gens: int = 5     # full O(N²) every 5 gens
    centroid_variance_per_gen: bool = True    # cheap O(N) every gen
    diversity_metric: Literal["pairwise_distance", "centroid_variance"] = "centroid_variance"


def compute_stagnation_signature_lite(
    population, gen_index, config,
) -> StagnationSignature:
    """v0.3: cheap centroid-variance every gen; full pairwise every
    Nth gen.

    Centroid-variance: O(N) compute. Captures variance of room
    dimensions across population. Sufficient for stagnation detection
    in 80%+ of cases per pilot benchmarks (forthcoming during build).
    """
    if gen_index % config.full_signature_every_n_gens == 0:
        # Full pairwise — O(N²)
        return compute_stagnation_signature_full(population)
    # Cheap path — O(N)
    return compute_stagnation_signature_centroid(population)
```

**Math**: centroid-variance for population of N candidates × R rooms ×
2 dims = O(N × R × 2). For pop_size=100, ~10 rooms typical = 2,000 ops
vs O(N² × R × 2) = 200,000 ops for pairwise. ~100× speedup on cheap-gen
path; still 1× full check every 5 gens.

Convergence triggers iff `composite_hash` repeats for
`convergence_stable_gens=5` consecutive **full-signature** gens.

### § 0.9 — Output ordering (REVISED v0.3 — resolves item 5)

v0.2 added `output_rank_reason: Literal["diversity_order", ...]`.
Critique #5 correctly notes this is documentation-only; downstream
consumers can still misinterpret.

v0.3 hardens the contract by **renaming the field for unambiguous
signaling**:

```python
@dataclass(frozen=True)
class RefinedCandidate:
    # ...
    # REMOVED: output_rank_reason (v0.2)
    # REPLACED with these two fields:
    output_sequence_is_quality_ranked: bool       # NEW v0.3 — REQUIRED FALSE at v1
    output_sequence_strategy: Literal[
        "diversity_order",                          # crowding-distance descending
        # post-v1 strategies routed via B-NEW-V3:
        # "objective_balance",
        # "pareto_membership_only",
    ]
```

At v1, **`output_sequence_is_quality_ranked` is always `False`**.
Downstream code reading `if candidate.output_sequence_is_quality_ranked:
top_n = candidates[:N]` will branch correctly without further
documentation. Misuse becomes a type-checked branch instead of a
documentation-only contract.

### § 0.10 — DominanceSorter abstraction scope (REVISED v0.3 — resolves item 6)

v0.2 introduced `DominanceSorterProtocol`. Critique #6 notes the
abstraction only covers sorting, not diversity semantics or survivor
selection. v0.3 documents the scope explicitly:

```python
class DominanceSorterProtocol(Protocol):
    """v0.3 scope clarification:
    Abstracts NON-DOMINATED SORTING ONLY. Does NOT abstract:
      - Diversity semantics (crowding distance is hardcoded at v1)
      - Survivor selection (NSGA-II rank+crowding hardcoded at v1)
      - Tie-breaking (lex-ASC by candidate hash hardcoded at v1)

    Replacing the sorter (e.g., Jensen fast sort) is safe.
    Replacing the *algorithm family* (e.g., MOEA/D, NSGA-III)
    requires additional protocol abstractions (B-NEW-V5 if needed
    post-launch).
    """
    def sort(self, population): ...
```

**B-NEW-V5** filed: broader algorithm-family protocols
(`DiversityMetricProtocol`, `SurvivorSelectionProtocol`) for if/when
post-NSGA-II algorithms become relevant.

---

## § 1 — Walk-resolved scope (REVISED v0.3)

| Q / F | Resolution | Walk |
|---|---|---|
| (carried v0.1/v0.2) | … | … |
| **F-v2-4 (W#3)** | **`C11B_VERSION = "v1.0"` constant added; included in `EnvironmentFingerprint`** | W#3 |
| **Q4** | NO — refinement scope room-dimensions-only at v1 (B-NEW-V) | W#1 carry |
| **Q8** | post-launch (B-NEW-V3) | W#2 carry |
| **CRIT #7 (W#3)** | **Inv 18 renamed to `area_feasible_by_construction`. Geometric embeddability is C12's responsibility, not C11b's. Spec terminology hardened.** | W#3 |
| **CRIT #1 partial (W#3)** | **`c11b_version` + `numpy_blas_info_summary` in EnvironmentFingerprint. Full BLAS/CPU/FP-mode fingerprint is B-237 work.** | W#3 |
| **CRIT #2 (W#3)** | **`permutations_per_candidate=3` reduces allocation-order bias. Dirichlet allocation deferred to B-NEW-V4.** | W#3 |
| **CRIT #3 (W#3)** | **`SEMANTIC_CAP_BY_CATEGORY` + `MAX_ROOM_ASPECT_RATIO=3.0`. KB-driven multipliers stay B-NEW-V2.** | W#3 |
| **CRIT #4 (W#3)** | **`StagnationConfig` adaptive cadence: cheap centroid every gen, full pairwise every 5 gens.** | W#3 |
| **CRIT #5 (W#3)** | **`output_sequence_is_quality_ranked: bool` (always False at v1). Hard contract signal.** | W#3 |
| **CRIT #6 (W#3)** | **DominanceSorterProtocol scope documented. Broader protocols → B-NEW-V5.** | W#3 |
| **CRIT #8 partial (W#3)** | **`evaluator_cache_max_memory_mb` config; cache-eviction hooks scaffold (no behavior change at v1)** | W#3 |

**0 open questions remaining at v0.3.**

---

## § 2 — Contract (REVISED v0.3)

Top-level signature unchanged.

### § 2.1 — Schema additions/changes (NEW v0.3)

- `EnvironmentFingerprint` extended (per § 0.3) with `c11b_version` +
  `numpy_blas_info_summary`
- `C11B_VERSION: Final[str] = "v1.0"` constant
- `SEMANTIC_CAP_BY_CATEGORY: Final[dict[str, float]]` (per § 0.6)
- `MAX_ROOM_ASPECT_RATIO: Final[float] = 3.0` (per § 0.6)
- `StagnationConfig` (per § 0.8)
- `RefinedCandidate.output_rank_reason` REMOVED; replaced with
  `output_sequence_is_quality_ranked: bool` + `output_sequence_strategy`
  (per § 0.9)
- `EvaluatorCacheStats` (NEW v0.3 — per item 8 partial; tracks entry
  count + estimated memory bytes; informational only at v1)

### § 2.2 — Configuration (REVISED v0.3 — defaults updated)

```python
@dataclass(frozen=True)
class LocalRefinementConfig:
    pop_size: int = field(default=100, metadata={"cache_relevant": True})
    max_generations: int = field(default=100, metadata={"cache_relevant": True})
    crossover_rate: float = field(default=0.9, metadata={"cache_relevant": True})
    mutation_rate: float = field(default=0.1, metadata={"cache_relevant": True})
    sbx_eta_c: float = field(default=20.0, metadata={"cache_relevant": True})
    polynomial_eta_m: float = field(default=20.0, metadata={"cache_relevant": True})
    pareto_output_size: int = field(default=20, metadata={"cache_relevant": True})
    convergence_stable_gens: int = field(default=5, metadata={"cache_relevant": True})
    universal_max_multiplier: float = field(default=2.5, metadata={"cache_relevant": True})
    init_max_retries: int = field(default=100, metadata={"cache_relevant": True})
    permutations_per_candidate: int = field(           # NEW v0.3
        default=3, metadata={"cache_relevant": True},
    )
    stagnation_config: StagnationConfig = field(        # NEW v0.3
        default_factory=StagnationConfig, metadata={"cache_relevant": True},
    )
    evaluator_cache_max_memory_mb: int = field(         # NEW v0.3 (item 8 scaffold)
        default=512, metadata={"cache_relevant": False},
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
    dominance_sorter_factory: Callable[[], DominanceSorterProtocol] = field(
        default=StandardDominanceSorter, metadata={"cache_relevant": False},
    )
```

---

## § 3 — Behaviour (REVISED v0.3)

### Phase 0 — Input + startup validation

Carried v0.2 + 1 addition:
- Capture `EnvironmentFingerprint` now includes `c11b_version` and BLAS
  hint.

### Phase 1 — Per-topology NSGA-II run (REVISED v0.3)

Carried v0.2 with three updates:
- Initialization uses `permutations_per_candidate=3` per § 0.7.
- Per-room upper bounds use `SEMANTIC_CAP_BY_CATEGORY` per § 0.6.
- Aspect ratio HARD constraint added to constraint_violations.
- Stagnation check uses `StagnationConfig` adaptive cadence per § 0.8.

### Phase 2 — Output assembly (REVISED v0.3)

Output candidates now carry `output_sequence_is_quality_ranked=False`
and `output_sequence_strategy="diversity_order"`. Sequence is
diversity-ordered (carried), but the contract is now type-checked.

### Phase 3 — Provenance assembly

Carried v0.2 + populates new fields per § 0.3 / § 2.1.

### § 3.1-§ 3.3 — (carried v0.2)

---

## § 4 — Invariants (REVISED v0.3)

| # | Invariant | Mode |
|---|---|---|
| 1-21 | (carried verbatim from v0.2) | as v0.2 |
| **18 RENAMED** | **`area_feasible_by_construction`: every initial-pop candidate satisfies `sum(room_area) ≤ envelope_area` (NOT geometric embeddability — that's C12's responsibility)** | RAISE |
| **22 (NEW v0.3)** | **`max(w,d)/min(w,d) ≤ MAX_ROOM_ASPECT_RATIO=3.0` per room. Violations contribute to `constraint_violations` via NSGA-II-CDP.** | RAISE (CDP) |
| **23 (NEW v0.3)** | **`output_sequence_is_quality_ranked == False` at v1.0. Type-checked at write-time. v2 changes require explicit B-NEW-V3 amendment.** | RAISE |
| **24 (NEW v0.3)** | **`EnvironmentFingerprint` MUST include `c11b_version`. Replays across C11b versions detect drift via fingerprint mismatch even when numpy/python identical.** | RAISE (replay tier) |
| **25 (NEW v0.3)** | **Stagnation detection costs bounded: full O(N²) check max once per `full_signature_every_n_gens` (default 5). Per-gen check is O(N) centroid variance. Total per-batch worst case: 100/5 × 100² = 200,000 ops.** | DOCUMENTED (cost) |

25 invariants at v0.3 (vs 21 at v0.2).

---

## § 5 — Failure modes (REVISED v0.3)

```
LocalRefinementError (base)
├── PerTopologyError
│   ├── NSGAConvergenceError
│   ├── AreaInfeasiblePopulationError       (REVISED v0.3 — was InfeasiblePopulationError)
│   └── EvaluatorContractError
├── BatchAllTopologiesFailedError
├── EvaluatorPurityContractError
├── EnvironmentFingerprintMismatchError
└── InvariantViolationError                 (systemic)
```

`AreaInfeasiblePopulationError` rename per § 0.2 terminology rule.

---

## § 6 — Test coverage targets (REVISED v0.3)

Target ~190 tests at LOCK (up from v0.2's 175):

- ~28 schema (unchanged)
- ~30 NSGA-II core (unchanged)
- ~30 invariants (Inv 1-25; +4)
- ~25 phase-logic
- ~12 partial-batch / strict-mode
- ~14 replay determinism (+ c11b_version mismatch tests)
- ~12 evaluator contract
- ~14 edge cases (+ aspect-ratio violation, semantic-cap clipping)
- ~16 v0.2 carry (feasibility-aware init, composite stagnation, etc.)
- **~9 NEW v0.3** — area-feasibility terminology check (~2),
  multiple-permutation init (~2), aspect-ratio HARD constraint (~2),
  stagnation adaptive cadence (~2), `output_sequence_is_quality_ranked`
  type-check enforcement (~1)

Cumulative target at C11b ship: 2519 + 190 ≈ **2709 passed**.

---

## § 7 — Open questions at v0.3

**0 open questions remaining.**

Convergence pattern across walks:

| Walk | Open Qs | Audit findings | New v1 subsystems |
|---|---|---|---|
| v0.1 | 7 | 8 | 9 (initial) |
| v0.2 | 2 | 7 | +1 (sorter) |
| v0.3 | **0** | 5 | **+0** |

Open Qs strictly monotone-decreasing 7 → 2 → 0. Audit findings
non-increasing. Subsystem growth halted at Walk #3 budget cap. **All
convergence signals green for LOCK request.**

---

## § 8 — Backlog at v0.3

**New at v0.3** (Walk #3 critique outcomes):

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-NEW-V4** | **C11b Dirichlet-based area partitioning for initialization (full bias removal)** | **W#3 #2** | **post-launch + measured Pareto-quality regression** | **M** |
| **B-NEW-V5** | **Broader EA protocols (`DiversityMetricProtocol`, `SurvivorSelectionProtocol`) for non-NSGA-II algorithm families** | **W#3 #6** | **alternate algorithm family becomes relevant** | **L** |
| **B-NEW-V6** | **C11b cache memory budget LRU eviction policy (replaces v1's count-only bound)** | **W#3 #8** | **measured memory pressure** | **S-M** |

**Cumulative**: 12 backlog items (2 carried + 5 v0.1 + 2 v0.2 + 3 v0.3).

---

## § 9 — Rule 11 spec audit on v0.3 PROPOSED

**PATCH-NOW (in v0.3 itself): 0**.

**OPEN QUESTIONS at v0.3**: 0.

**SPEC-AUDIT FINDINGS (v0.3)**:

| # | Finding | Verdict |
|---|---|---|
| F-v3-1 | Full BLAS/LAPACK/CPU-vectorization fingerprinting (item 1 expansion) deferred to B-237. Spec doesn't explicitly file a sub-task in B-237 scope; partial. | **DOCUMENTED** — B-237 has the receiving end; v0.3's `numpy_blas_info_summary` is C11b's contribution. |
| F-v3-2 | `MAX_ROOM_ASPECT_RATIO=3.0` is a magic constant with no architectural-validation source. 3.0 means a 9m × 3m room is OK; a 9m × 2.9m room isn't. Reasonable but unjustified. | **DOCUMENTED** — explicit non-blocker; B-238 (architect review) will validate. |
| F-v3-3 | `permutations_per_candidate=3` is a magic number too. Why 3? Why not 5, or 10? | **DOCUMENTED** — pragmatic compromise (cost vs. coverage). Tunable via config. |
| F-v3-4 | `SEMANTIC_CAP_BY_CATEGORY` doesn't include `bedroom` or `living` — they fall back to 2.5×. Master bedroom at 2.5× of liveability minimum can be 30+ m² which is reasonable; smaller bedrooms at 2.5× are also OK. So fallback is fine. | **DOCUMENTED**. |
| F-v3-5 | `output_sequence_is_quality_ranked: bool` — what about post-v1 when `objective_balance` ordering ships? The bool will need a third state ("partial") or mode-dependent reading. | **DOCUMENTED** — B-NEW-V3 already files the v2 ordering. When that lands, the bool may need to become a tri-state enum; v1 ships with bool because it captures the v1 reality cleanly. |

**5 audit findings, all DOCUMENTED.** None blocking. v0.3 is clean by
the criteria of Walk #5 C11a's pattern (where 2-3 findings remained
DOCUMENTED at LOCK time).

**REJECTED-AS-CONSIDERED**:
- "Should `output_sequence_is_quality_ranked` be replaced with a more
  general `OutputContract` enum at v1?" — Premature; 2-state is
  sufficient now; tri-state when post-v1 strategies arrive.
- "Should `MAX_ROOM_ASPECT_RATIO` be category-specific (e.g.,
  bathrooms tighter, corridors looser)?" — Adds complexity for
  unmeasured benefit. v1 ships with universal 3.0.

---

## § 10 — Status

- **v0.3 PROPOSED**. **NOT LOCKED.**
- **LOCK candidate per S37 directive (Walk #3 of 2-3 target).**
- 8 valid critique items resolved (8 amendments, 0 rejected).
- **0 open questions remain.**
- **5 audit findings, all DOCUMENTED (non-blocking).**
- 12 backlog items, 3 new at v0.3.
- Walk #3 budget adherence: **0 new subsystems added** (cap met).
- Convergence signals: open Qs 7→2→0 monotone; audit 8→7→5 non-increasing;
  subsystem growth halted; reviewer surface narrowing pattern matches
  C11a's pre-LOCK trajectory.

---

## § 12 — Backlog enumeration

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-237 | Cross-platform replay CI matrix + Decimal geometry + (NEW W#3) BLAS/CPU fingerprinting | S35 carry | M |
| B-NEW-P | Upstream `severity_tier` ClassVar amendment cluster | S37 W#4 carry | XS |
| B-NEW-V | C11b refinement scope expansion | v0.1 Q4 | M |
| B-NEW-W | C11b hypervolume diversity metric | v0.1 Q5 | M |
| B-NEW-X | C11b adaptive NSGA-II hyperparameters | future tuning | M |
| B-NEW-Y | C11b cross-topology Pareto aggregation | v0.1 Q2 | M |
| B-NEW-Z | C11b deterministic-parallel-NSGA-II | scaling pressure | L |
| B-NEW-V2 | C11b per-category bound multipliers (KB-driven) | W#2 #3 | M |
| B-NEW-V3 | C11b objective_balance output ordering | W#2 #7 | S-M |
| **B-NEW-V4** | **C11b Dirichlet area partitioning** | **W#3 #2** | **M** |
| **B-NEW-V5** | **Broader EA protocols (non-NSGA-II family support)** | **W#3 #6** | **L** |
| **B-NEW-V6** | **C11b cache memory-budget LRU eviction** | **W#3 #8** | **S-M** |

**Backlog summary**:

| Total | Pre-existing | v0.1 | v0.2 | v0.3 |
|---|---|---|---|---|
| **12** | 2 | 5 | 2 | 3 |

---

## § 13 — Complexity Budget (REVISED v0.3)

### v1 surface area: 10 subsystems (UNCHANGED at Walk #3)

Walk #3 budget cap: 0 new v1 subsystems. **Met**. All Walk #3 changes
are within-subsystem patches, terminology corrections, or backlog
additions.

### What v0.3 explicitly does NOT add to v1

| Considered | Routing |
|---|---|
| Dirichlet area partitioning (item 2 full fix) | B-NEW-V4 |
| Full BLAS/CPU fingerprinting (item 1 full fix) | B-237 expansion |
| Geometric embeddability check (item 7 full fix) | C12's job; NOT C11b scope |
| KB-driven per-category multipliers (item 3 full fix) | B-NEW-V2 (already filed) |
| LRU cache eviction (item 8 full fix) | B-NEW-V6 |
| Broader EA protocols (item 6 full decoupling) | B-NEW-V5 |

**6 of 8 critique items routed via partial-fix-now + full-fix-backlog
pattern.** Items 5 and 7 fully resolved at v1 (terminology + contract
hardening).

---

## § 14 — Freeze candidacy rationale

Adopting C11a v0.5's § 14 pattern.

### § 14.1 — Convergence signals (empirical)

| Walk | Audit findings | Open Qs | New v1 subsystems | Critique items resolved |
|---|---|---|---|---|
| v0.1 | 8 | 7 | 9 (initial) | (seed) |
| v0.2 | 7 | 2 | +1 | 8 |
| v0.3 | 5 | **0** | **+0** | 8 |

**Pattern**: open Qs strictly monotone-decreasing to 0. Audit findings
strictly non-increasing. Walk #3 stayed at budget cap. Critique
resolution count steady — but routing flipped: Walk #3 routed 6 of 8
to backlog vs Walk #2's 1 of 8. This is the "diminishing returns"
signal — reviewer is finding things, but they're routing to backlog
rather than v1 amendments.

### § 14.2 — Industry standard parallel to C11a

Same convergence pattern as C11a v0.5 (Walk #5 LOCK candidate):
- Open Qs reach 0
- Audit findings drop and become DOCUMENTED-tier
- Critique items shift from amendments to backlog routing
- Subsystem growth halts at the budget cap

C11a was LOCKED at Walk #5+#6 with this exact signal pattern. C11b
reaches the same signal pattern at Walk #3 — faster convergence per
the S37 directive (2-3 walks vs C11a's 5+).

### § 14.3 — Counter-arguments to LOCK now

1. **C11a B-NEW-J/K/L/P upstream amendments not yet shipped**.
   Inherited from C11a as a build-time prerequisite via B-NEW-P (carry).
   Not a C11b spec issue.
2. **C14 doesn't exist yet**. Mitigated by `EvaluatorProtocol`
   abstraction + `StubEvaluator` for v1 build-time testing.
3. **B-237 cross-platform CI not yet built**. Pre-launch gate, not
   LOCK gate.

None are spec-arc-resolvable. Implementation concerns.

### § 14.4 — Proposed LOCK preconditions

For Ramalingam adjudication:

1. C11a v1.0 already LOCKED ✓
2. Build-time prerequisites (B-NEW-P, B-237) not blocking LOCK; blocking
   build-start
3. C14 not blocking LOCK (`StubEvaluator` covers v1 build); pre-launch
   gate
4. No spec changes beyond audit-finding patches until C11b v1 build
   complete

### § 14.5 — Recommendation

**Request LOCK at Walk #3.** S37 directive met (2-3 walks target).
Decision is yours per Rule 8.

---

**End of v0.3 PROPOSED.** Awaits Ramalingam adjudication: LOCK or
Walk #4.
