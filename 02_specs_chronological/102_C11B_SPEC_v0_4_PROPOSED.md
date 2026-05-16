# C11b — Local Refinement (NSGA-II) — SPEC v0.4 PROPOSED

**Component**: 11b (canonical Track 3 numbering — paired with C11a Topology Mutation)
**Status**: **v0.4 PROPOSED. NOT LOCKED.** PENDING Ramalingam adjudication per Rule 8.
**Authored**: S41 close, post Rule 11 self-analysis on v1.0 LOCKED spec.
**Supersedes**: v1.0 LOCKED at S37 (carried forward verbatim except where this amendment marks changes).
**Predecessors**: v0.1 PROPOSED (S35), v0.2 PROPOSED (S36), v0.3 PROPOSED → v1.0 LOCKED (S37).

---

## § 0 — Why v0.4 exists

C11b v1.0 was LOCKED at S37. Between S37 and S41 the codebase shifted in ways that affect C11b's input contract and constraint surface:

1. **C11a Spec #4 v1.6 LOCKED** (S40-continuation) — added multi-floor topology mutation. C11a now emits `MutatedTopologyCandidate` where `source_candidate` may be a real `MultiFloorWetZonePlannedCandidate`. v1.0 was written assuming single-floor topology only.
2. **C11a self-review fix at S41 close** — `MutationApplicationResult.output_candidate: Optional[Any]` field added so consumers receive the actual mutated artifact (Pattern B fix). C11b is the next consumer of this output.
3. **C9 amendment Spec #2 v0.12 LOCKED** (S41) — `FloorRoomBrief.has_master_bedroom` field gates Inv 13/14 cardinality. Multi-floor only; not relevant unless C11b accepts multi-floor inputs.

Rule 11 self-analysis on v1.0 LOCKED additionally surfaced four gaps the spec itself had not flagged:

4. **Per-topology timeout / circuit-breaker unspecified** — `init_max_retries=100` × `pop_size=100` is up to 10,000 area-feasibility checks per topology with no wall-clock cap.
5. **NSGA-II 3-objective Pareto pathology** — `StubEvaluator` returns 3 objectives. Doerr et al. 2022 proved NSGA-II cannot find the full Pareto front in sub-exponential time for ≥3 objectives; NSGA-III is the standard remedy. v1.0 spec implicitly accepts approximation; v0.4 makes this explicit and files a trigger.
6. **Evaluator failure isolation** — what happens when `evaluator.evaluate(candidate)` raises mid-generation? v1.0 has `EvaluatorContractError` but no semantics for whether one bad candidate halts the topology or just the candidate.
7. **PRNG seed composition** — spec says "per-topology rng seed" but doesn't specify how the seed is *derived* from `(LocalRefinementConfig.master_seed, topology_index)`. Without that rule, two builds with the same nominal config can produce different streams.

v0.4 addresses #1, #2, #3, #4, #5, #6, #7 above. It does NOT reopen any v1.0 design decision Ramalingam already adjudicated.

---

## § 0.1 — v1.0 → v0.4 delta summary

| Change ID | Section | Scope | Type |
|---|---|---|---|
| **D-MF-1** | § 2 (Contract) | Add explicit rejection of multi-floor inputs at v1. `MultiFloorWetZonePlannedCandidate` as `source_candidate` raises `MultiFloorRefinementNotSupportedError`. | Spec-text addition |
| **D-MF-2** | § 8 (Backlog) | File **B-C11B-MF**: multi-floor refinement scope expansion. | Backlog addition |
| **D-OC-1** | § 2.1 (Schema) + § 3 (Behaviour) | Document that C11b reads `MutationApplicationResult.output_candidate` as the input artifact when present; for Tier A SHALLOW results with `output_candidate=None`, C11b refines the `source_candidate` directly (predicate-only operators don't materialize new geometry; C11b operates on the unchanged source). | Spec-text clarification |
| **D-OC-2** | § 4 (Invariants) | Add **Inv 26**: C11b's input-artifact resolution rule is deterministic per the v0.4 § 3.0 algorithm. | RAISE |
| **D-TO-1** | § 2.2 (Config) | Add `per_topology_wallclock_seconds: float = 30.0` (cache_relevant=False — affects diagnostics only). | Spec-text addition |
| **D-TO-2** | § 5 (Failure modes) | Add `PerTopologyTimeoutError(PerTopologyError)`. | Spec-text addition |
| **D-TO-3** | § 4 (Invariants) | Add **Inv 27**: per-topology wall-clock breach raises `PerTopologyTimeoutError` and contributes to `BatchAllTopologiesFailedError` accounting. | RAISE |
| **D-NSGA-1** | § 0.5 (StubEvaluator) | Add `StubEvaluatorConfig` with `objectives: Literal[2, 3] = 3` (default carries v0.3 3-objective behavior; 2-objective mode added as a config knob for testing inside NSGA-II's proven regime). | Spec-text addition |
| **D-NSGA-2** | § 8 (Backlog) | **Widen B-NEW-V5** trigger: explicit measurable criterion for NSGA-III migration (when production evaluator returns ≥3 objectives AND empirical hypervolume regression is observed across 2+ release cycles). | Backlog widening |
| **D-EV-1** | § 3 (Behaviour) | Specify evaluator failure isolation: a single `evaluator.evaluate()` raising `EvaluatorContractError` is per-candidate (skip that candidate, continue the generation); a systemic exception type (non-EvaluatorContractError) halts the topology with `EvaluatorContractError` wrapping. | Spec-text addition |
| **D-EV-2** | § 4 (Invariants) | Add **Inv 28**: per-generation evaluator failure cap = `max(1, int(pop_size * config.evaluator_skip_cap_fraction))` (default fraction 0.25). Exceeding the cap upgrades to systemic. | RAISE |
| **D-EV-3** | § 2.2 (Config) | Add `evaluator_skip_cap_fraction: float = 0.25` (cache_relevant=False — diagnostic budget knob). Makes Inv 28's cap configurable. | Spec-text addition |
| **D-PR-1** | § 2.2 (Config) + § 3 Phase 0 | Specify `master_seed: int = 0xC11B5EED` (cache_relevant=True). Per-topology seed = `hash_to_int(master_seed, topology_index, topology_signature) % 2**32`. | Spec-text addition |
| **D-PR-2** | § 4 (Invariants) | Add **Inv 29**: PRNG seed derivation is pure-deterministic; two runs with the same master_seed + same topology_signature MUST produce byte-equal PRNG streams. | RAISE (replay tier) |

**Net: 29 invariants at v0.4 (was 25 at v1.0). 4 new invariants (26, 27, 28, 29). 3 new config fields (`per_topology_wallclock_seconds`, `master_seed`, `evaluator_skip_cap_fraction`), 1 new failure type (`PerTopologyTimeoutError`), 1 new error type (`MultiFloorRefinementNotSupportedError`). 1 spec-text expansion of `StubEvaluator` (`objectives: Literal[2,3]=3`, default carries v0.3). 1 widened backlog item trigger (B-NEW-V5). 2 new backlog items (B-C11B-MF, B-C11B-TIMEOUT-V2).**

---

## § 0.2 — Multi-floor input rejection at v1 (D-MF-1, D-MF-2)

**Rationale**: C11a as of S41 emits both single-floor `WetZonePlannedCandidate` and multi-floor `MultiFloorWetZonePlannedCandidate` outputs. C11b v1.0 was specced before multi-floor existed. Refining a multi-floor wrapper as one parameter vector is a meaningfully different design problem (rooms span floors, area constraints are per-floor not global, NSGA-II population size implicitly multiplies by floor count). v1 scopes to single-floor; multi-floor is post-v1.

**Behavior**: Per-topology routing in Phase 1:

```python
def _refine_one_topology(
    mtc: MutatedTopologyCandidate,
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    evaluator: EvaluatorProtocol,
    config: LocalRefinementConfig,
    topology_index: int,
) -> tuple[RefinedCandidate, ...]:
    """Per-topology entry. v0.4: rejects multi-floor source candidates."""
    input_artifact = _resolve_input_artifact(mtc)  # See § 3.0

    # D-MF-1: explicit multi-floor rejection at v1.
    if _is_multi_floor_artifact(input_artifact):
        raise MultiFloorRefinementNotSupportedError(
            f"C11b v1.0 does not support multi-floor topology refinement. "
            f"topology_index={topology_index}, "
            f"source_type={type(input_artifact).__name__}. "
            f"Multi-floor refinement is post-v1 scope (B-C11B-MF)."
        )
    ...
```

`MultiFloorRefinementNotSupportedError` is a `PerTopologyError` subclass, so under WARN mode the topology fails and is reported in `BatchAllTopologiesFailedError`'s telemetry; under STRICT mode the batch halts. This matches v1.0's failure-mode discipline for other per-topology errors.

**Backlog**:

```
B-C11B-MF (NEW v0.4): Multi-floor refinement scope expansion for C11b.
  Origin: v0.4 § 0.2 (D-MF-1) — C11a now emits multi-floor wrappers; C11b v1 rejects them.
  Trigger: when product needs end-to-end multi-floor refinement (likely
    coincides with C12 multi-floor placement landing or C14 multi-floor
    scoring landing — whichever comes first).
  Effort estimate: L (5-10 sessions). Likely architectural decisions:
    (a) refine each floor's WZPC independently and recombine via Spec #3
        wrapper assembly;
    (b) refine the wrapper as one parameter vector with per-floor area
        sub-budgets;
    (c) hybrid: per-floor refinement with cross-floor structural
        constraint enforcement.
```

---

## § 0.3 — Input artifact resolution (D-OC-1, D-OC-2)

**Rationale**: C11a's S41 self-review added `MutationApplicationResult.output_candidate: Optional[Any]` so consumers receive the actual mutated artifact for Tier B and M8 operators. For Tier A SHALLOW operators (M1-M5, M9 predicate-only), `output_candidate` stays None — the operator returned a verdict, not new geometry. C11b must handle both cases consistently.

**v0.4 algorithm (§ 3.0 NEW)**:

```python
def _resolve_input_artifact(
    mtc: MutatedTopologyCandidate,
) -> Any:
    """Per Inv 26: deterministic resolution of the topology artifact
    C11b refines from a MutatedTopologyCandidate.

    Convention (carried from C11a Sub-4): each MutatedTopologyCandidate
    carries exactly ONE MutationApplicationResult — one accepted
    operator application per MTC. This v0.4 resolver enforces that
    convention defensively: empty application_results or multi-element
    application_results raise `EvaluatorContractError` per Inv 26's
    audit-tier contract. v0.4 does not assume future MTCs will carry
    multiple results; if that convention changes, the resolver must
    be updated alongside (programming-bug discipline).

    Rule:
      - If mtc.application_results is empty or has >1 element:
        raise `EvaluatorContractError` (Inv 26 audit).
      - Let result = mtc.application_results[0].
      - If result.output_candidate is not None:
        use it (Tier B regenerative ops: M6, M7; multi-floor M8;
        single-floor M0; multi-floor M0).
      - Else: use mtc.source_candidate (Tier A SHALLOW predicate-only
        ops: M1-M5, M9 — these emit verdicts on the source without
        constructing new geometry; v1 of C11b refines the unchanged
        source).
    """
    if len(mtc.application_results) != 1:
        raise EvaluatorContractError(
            f"C11b Inv 26: MutatedTopologyCandidate must carry exactly "
            f"one application result; got {len(mtc.application_results)}. "
            f"This violates C11a Sub-4 convention; programming bug or "
            f"upstream contract drift."
        )
    result = mtc.application_results[0]
    if result.output_candidate is not None:
        return result.output_candidate
    return mtc.source_candidate
```

**Invariant 26 (NEW v0.4)**: The above resolver is the ONLY way C11b's per-topology refinement reads the input artifact. Direct access to `mtc.source_candidate` outside the resolver is a programming bug (Inv 26 audit during build).

**Consequence**: C11b treats Tier A SHALLOW M1-M5, M9 candidates as "no-op mutations" for parameter refinement purposes. The operator's contribution to C11a's output is the *verdict* (the candidate is a valid topology under that mutation), and C11b refines its room dimensions accordingly. Materialization of Tier A geometry (e.g., actually computing the M1 horizontal-flipped coordinates) is downstream of C11b — likely C12 placement.

**Test discipline**: Inv 26 has at least 1 dedicated test per case (Tier B, M8, Tier A) — 3 tests minimum.

### § 0.3.1 — Worked example: resolution by operator class (NEW v0.4 close)

| Operator | Tier | C11a `output_candidate` populated? | C11b reads | Notes |
|---|---|---|---|---|
| M0_BASE (single-floor) | SHALLOW | Yes (source itself, per S41 fix) | `result.output_candidate` (= source) | Identity mutation; refines unchanged source |
| M0_BASE (multi-floor) | SHALLOW | Yes (wrapper itself) | `result.output_candidate` (= wrapper) | **Rejected at v1 via D-MF-1** |
| M1_HORIZ_FLIP, M2_VERT_FLIP | SHALLOW | None (Tier A predicate-only) | `mtc.source_candidate` | Refine the unflipped source; flip materialization is C12's job |
| M3a-c (staircase), M4 (corridor), M5 (zone) | SHALLOW | None | `mtc.source_candidate` | Same as M1/M2 |
| M9a-d (entry) | SHALLOW | None | `mtc.source_candidate` | Same as M1/M2 |
| M6_WET_ROTATE | REGENERATIVE | Yes (rotated WZPC from deep pipeline) | `result.output_candidate` | Tier B; new geometry materialized |
| M7A_GRID_3_3, M7B_GRID_2_7 | REGENERATIVE | Yes (regridded WZPC from deep pipeline) | `result.output_candidate` | Tier B; new geometry materialized |
| M8_VERT_REARR (multi-floor only) | REGENERATIVE | Yes (rewrapped MFWZPC after C9+C10 cascade) | `result.output_candidate` | **Rejected at v1 via D-MF-1** |

**Reading the table**: For Tier A SHALLOW ops M1-M5, M9 — which are the bulk of C11a output — C11b refines `source_candidate` directly. This is correct because Tier A operators *don't actually mutate geometry*; they emit verdicts that the source is valid under that operator's transformation. C11b's job is to refine room dimensions of the validated topology, and the topology is the source.

For Tier B and M0, `output_candidate` is the artifact to refine — for M6/M7 the regenerated WZPC, for M0 the source itself.

---

## § 0.4 — Per-topology timeout / circuit-breaker (D-TO-1, D-TO-2, D-TO-3)

**Rationale**: v1.0 `init_max_retries=100` × `pop_size=100` = up to 10,000 area-feasibility checks per topology with no wall-clock cap. If a topology has very tight area constraints (FAR <0.95, packed rooms), the init loop could spin without finding a feasible candidate. Worst case: single bad topology stalls an entire batch indefinitely.

**v0.4 mechanism**:

```python
@dataclass(frozen=True)
class LocalRefinementConfig:
    ...  # carried v1.0
    per_topology_wallclock_seconds: float = field(   # NEW v0.4
        default=30.0,
        metadata={"cache_relevant": False},  # diagnostic, not output-determining
    )
```

**Behavior** (Phase 1 per-topology):

```python
def _refine_one_topology(...):
    start_perf = time.perf_counter()
    ...
    # Per-generation loop:
    for gen in range(config.max_generations):
        elapsed = time.perf_counter() - start_perf
        if elapsed > config.per_topology_wallclock_seconds:
            raise PerTopologyTimeoutError(
                f"C11b: topology_index={topology_index} exceeded wallclock "
                f"budget {config.per_topology_wallclock_seconds:.1f}s "
                f"at generation {gen}/{config.max_generations}; "
                f"elapsed {elapsed:.1f}s."
            )
        ...  # generation body
```

The check is at generation boundaries, not inside individual operations. This means a single very long generation (e.g., a pathological evaluator) can still overrun the budget, but the topology will exit at the next generation boundary. v2 may add per-evaluation timeouts.

**Invariant 27 (NEW v0.4)**: Per-topology wall-clock breach raises `PerTopologyTimeoutError`. Under WARN mode the topology fails; under STRICT mode the batch halts via `BatchAllTopologiesFailedError`. The error is per-topology, not systemic.

**Default rationale**: 30s per topology, with `max_generations=100` and `pop_size=100`, gives ~300ms per generation. Even a slow stub evaluator (≤1ms per candidate) fits in ~100ms; production evaluators with C14 may need more headroom, configurable via this field.

**Out of scope at v0.4**: per-evaluation timeout, generation-level resumability after timeout. Filed as **B-C11B-TIMEOUT-V2** for post-launch tuning.

---

## § 0.5 — NSGA-II 3-objective Pareto pathology (D-NSGA-1, D-NSGA-2)

**Rationale**: Recent runtime analysis (Doerr et al. 2022) proves NSGA-II cannot compute the full Pareto front in sub-exponential time once the objective count reaches 3. v1.0's `StubEvaluator` returns 3 objectives. This is mathematically suboptimal but operationally acceptable for v1 because:

1. The 3 stub objectives are correlated (compactness, aspect-variance, envelope-efficiency all reflect room geometry), so the practical Pareto front is well-approximated by NSGA-II even where the full theoretical front is unreachable.
2. NSGA-III with reference points is the standard remedy but requires additional infrastructure (reference-point sampling, perpendicular-distance crowding) that's a separate spec arc.
3. C14 production evaluator has not yet committed to an objective count; v1 should not predict it.

**v0.4 change**:

```python
@dataclass(frozen=True)
class StubEvaluatorConfig:                          # NEW v0.4
    """Config knob for the stub-only objective count.

    Default is 3 (v0.3 carried behavior). Setting to 2 stays inside
    NSGA-II's mathematically proven regime (no 3-objective Pareto-front
    pathology), useful when the production evaluator is also 2-objective
    or when isolating algorithm correctness from objective-count effects.
    """
    objectives: Literal[2, 3] = 3                   # NEW v0.4 — keeps v0.3 default

class StubEvaluator:
    """v0.4: objectives count is now configurable. Default stays at 3
    to preserve v1.0 LOCKED behavior. Set objectives=2 in config to
    use 2-objective mode (stays inside NSGA-II's proven regime per
    Doerr et al. 2022).
    """
    def __init__(self, config: StubEvaluatorConfig | None = None) -> None:
        self._config = config or StubEvaluatorConfig()

    def evaluate(self, candidate: RefinedCandidate) -> ObjectiveVector:
        # Compute all 3 candidate objectives, return first N.
        compactness, variance, efficiency = _compute_three_stub_objectives(candidate)
        if self._config.objectives == 2:
            return ObjectiveVector(
                values=(
                    ("synthetic_compactness", round(compactness, 6)),
                    ("synthetic_envelope_efficiency", round(efficiency, 6)),
                ),
                constraint_violations=0.0,
            )
        return ObjectiveVector(  # 3-objective mode (v0.3 default behavior)
            values=(
                ("synthetic_compactness", round(compactness, 6)),
                ("synthetic_aspect_variance", round(variance, 6)),
                ("synthetic_envelope_efficiency", round(efficiency, 6)),
            ),
            constraint_violations=0.0,
        )
```

**Backlog widening (D-NSGA-2)** — Update **B-NEW-V5** trigger description:

```
B-NEW-V5 (WIDENED v0.4): Broader EA protocols + NSGA-III migration.
  Original (v0.3): "alternate algorithm family becomes relevant."
  Widened (v0.4) trigger: ANY of:
    (a) Production evaluator (C14) commits to returning ≥3 objectives, AND
    (b) Empirical hypervolume regression observed across 2 release cycles
        on standard benchmark briefs, OR
    (c) Architect feedback indicates Pareto-front coverage is product-
        quality blocking.
  Effort estimate: L (carried). Implementation likely Deb-Jain NSGA-III
  with reference-point sampling.
```

**Invariant: none added**. The 3-objective regime is a known limitation, not an invariant violation. Spec text in § 0.5 documents the trade-off.

---

## § 0.6 — Evaluator failure isolation (D-EV-1, D-EV-2)

**Rationale**: v1.0 has `EvaluatorContractError` but doesn't specify behavior when `evaluator.evaluate(candidate)` raises mid-generation. Three cases need disambiguation:

1. **Per-candidate failure** (evaluator raises `EvaluatorContractError`): the candidate is malformed for the evaluator's contract (e.g., room dimensions outside its trained range). Skip that one candidate; continue the generation.
2. **Systemic failure** (evaluator raises any other exception type): the evaluator itself is broken (e.g., C14 KB lookup failed, model file missing). Halt the topology, raise `EvaluatorContractError` wrapping the underlying cause.
3. **Per-candidate flood** (>25% of population fails per-candidate in one generation): treat as systemic regardless of declared error type. Indicates the evaluator's contract is mismatched with C11b's population, not isolated bad candidates.

**v0.4 mechanism** (Phase 1 per-generation):

```python
def _evaluate_population(
    population: tuple[RefinedCandidate, ...],
    evaluator: EvaluatorProtocol,
    config: LocalRefinementConfig,
) -> tuple[tuple[RefinedCandidate, ...], int]:
    """Returns (evaluated_population, skipped_count).

    Per Inv 28: skip count cap is
    ``max(1, int(pop_size * config.evaluator_skip_cap_fraction))``
    (default 0.25 → 25 of 100). Exceeding the cap upgrades the failure
    to systemic (raises EvaluatorContractError).

    v0.4: cap is configurable via `evaluator_skip_cap_fraction` for
    consistency with `per_topology_wallclock_seconds` (Inv 27) — both
    are operationally tunable budgets, neither should be hardcoded.
    """
    evaluated: list[RefinedCandidate] = []
    skipped = 0
    skip_cap = max(1, int(len(population) * config.evaluator_skip_cap_fraction))
    for candidate in population:
        try:
            objective_vector = evaluator.evaluate(candidate)
        except EvaluatorContractError:
            skipped += 1
            if skipped > skip_cap:
                raise EvaluatorContractError(
                    f"C11b: per-candidate evaluator failure cap exceeded "
                    f"({skipped} > {skip_cap} of {len(population)}, "
                    f"fraction={config.evaluator_skip_cap_fraction:.2f}); "
                    f"upgrading to systemic per Inv 28."
                )
            continue  # skip this candidate; population shrinks by 1
        except Exception as exc:
            raise EvaluatorContractError(
                f"C11b: systemic evaluator failure (non-contract exception): "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        evaluated.append(_attach_objective_vector(candidate, objective_vector))
    return tuple(evaluated), skipped
```

**Invariant 28 (NEW v0.4, REVISED v0.4 close)**: Per-generation evaluator failure cap = `max(1, int(pop_size * config.evaluator_skip_cap_fraction))` (default fraction 0.25 → 25 of 100). Exceeding the cap raises `EvaluatorContractError` (systemic per the WARN/STRICT escalation).

**Consequence**: A generation that loses up to 25% of its population to per-candidate evaluator failure continues at reduced population; the next generation's reproduction step refills via selection pressure. >25% failures fail the topology. This is a deliberate tradeoff: tolerate edge-case evaluator brittleness, hard-fail systemic mis-wiring.

---

## § 0.7 — PRNG seed derivation (D-PR-1, D-PR-2)

**Rationale**: v1.0 spec mentions "per-topology rng seed" but doesn't specify derivation. Standard practice: set seeds across all RNGs (Python's random, NumPy's RandomState/Generator, any backend like PyTorch) from a single master seed via a deterministic mixing function. Without specification, two runs of the same nominal config could produce different streams if NumPy's RNG defaults change.

**v0.4 mechanism**:

```python
@dataclass(frozen=True)
class LocalRefinementConfig:
    ...  # carried v1.0
    master_seed: int = field(                     # NEW v0.4
        default=0xC11B5EED,                       # deliberately recognizable
        metadata={"cache_relevant": True},        # affects output; cached separately
    )

def derive_per_topology_seed(
    master_seed: int,
    topology_index: int,
    topology_signature: str,
) -> int:
    """Pure deterministic derivation per Inv 29.

    Uses SHA256 over the canonical concatenation. Truncated to 32 bits
    so NumPy's SeedSequence accepts it (any int up to 2^32 is fine;
    larger ints would also work but 32 bits keeps logs readable).
    """
    payload = f"{master_seed}|{topology_index}|{topology_signature}"
    h = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(h[:4], byteorder="big")

def _build_per_topology_rng(
    config: LocalRefinementConfig,
    topology_index: int,
    topology_signature: str,
) -> numpy.random.Generator:
    """Build per-topology PRNG via explicit SeedSequence for NumPy
    version stability.

    Rationale: numpy.random.default_rng(int) semantics have been stable
    since NumPy 1.17, but NumPy's recommended practice is to construct
    via SeedSequence explicitly to make the intent unambiguous and to
    enable reproducible spawning in future parallel implementations
    (B-NEW-Z deterministic-parallel-NSGA-II).
    """
    seed = derive_per_topology_seed(
        config.master_seed, topology_index, topology_signature,
    )
    seed_seq = numpy.random.SeedSequence(seed)
    return numpy.random.default_rng(seed_seq)
```

**Invariant 29 (NEW v0.4)**: PRNG seed derivation is pure-deterministic; two runs with the same (`master_seed`, `topology_index`, `topology_signature`) MUST produce byte-equal PRNG streams. This is RAISE-tier replay invariant — replay tests assert byte-equality.

**`topology_signature`**: Reuse C11a's `derive_canonical_signature(input_artifact)` output (16-hex SHA256 prefix). For multi-floor wrappers this would aggregate per-floor signatures; v1 doesn't see multi-floor inputs (per D-MF-1), so the signature is the single-floor structural hash.

**Per-replay assertion**: Phase 0 captures `master_seed` into `EnvironmentFingerprint`. Replay-tier tests assert that two runs with the same fingerprint produce byte-equal Pareto fronts.

---

## § 0.8 — Carried v1.0 sections (no v0.4 changes)

All of v1.0 § 0.6 (refinement bounds), § 0.7 (feasibility-aware init), § 0.8 (stagnation detection), § 0.9 (output ordering), § 0.10 (DominanceSorter scope), § 1 (Walk-resolved scope), § 13 (Complexity budget), § 14 (Freeze candidacy) carry forward verbatim. v0.4 does not amend them.

---

## § 1 — Walk-resolved scope (v0.4 additions)

| Q / F / G | Resolution | Walk |
|---|---|---|
| (carried v0.1-v1.0) | … | … |
| **G-S41-1 (D-MF-1)** | Multi-floor inputs rejected at v1 with `MultiFloorRefinementNotSupportedError`; B-C11B-MF files post-v1 work | v0.4 self-analysis |
| **G-S41-2 (D-OC-1)** | C11b reads `MutationApplicationResult.output_candidate` when present; falls back to `source_candidate` for Tier A SHALLOW | v0.4 self-analysis |
| **G-S41-3 (D-TO-1)** | `per_topology_wallclock_seconds=30.0` default; `PerTopologyTimeoutError` per-topology | v0.4 self-analysis |
| **G-S41-4 (D-NSGA-1)** | `StubEvaluator.objectives` defaults to 2; B-NEW-V5 widened with NSGA-III migration trigger | v0.4 self-analysis + web research (Doerr 2022) |
| **G-S41-5 (D-EV-1)** | Per-candidate evaluator failures skip-and-continue up to `pop_size // 4`; beyond that upgrade to systemic | v0.4 self-analysis |
| **G-S41-6 (D-PR-1)** | `master_seed=0xC11B5EED`; per-topology seed = SHA256(master_seed, index, signature)[:4] | v0.4 self-analysis |

**Open Qs at v0.4: 0.** All gaps surfaced by Rule 11 self-analysis are resolved either in-spec or by deferred-backlog with explicit trigger.

---

## § 2 — Contract (REVISED v0.4)

Top-level signature unchanged from v1.0:

```python
def run_local_refinement(
    mutated_topology_candidates: tuple[MutatedTopologyCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    evaluator: EvaluatorProtocol,
    *,
    config: LocalRefinementConfig | None = None,
) -> tuple[RefinedCandidate, ...]: ...
```

### § 2.1 — Schema additions (v0.4 over v1.0)

- `MultiFloorRefinementNotSupportedError(PerTopologyError)` — NEW v0.4
- `PerTopologyTimeoutError(PerTopologyError)` — NEW v0.4
- `StubEvaluatorConfig` dataclass + `objectives: Literal[2, 3] = 2` field — NEW v0.4
- `derive_per_topology_seed(master_seed, topology_index, topology_signature) -> int` — NEW v0.4

### § 2.2 — Configuration (additions over v1.0)

```python
@dataclass(frozen=True)
class LocalRefinementConfig:
    # ... all v1.0 fields carried ...
    per_topology_wallclock_seconds: float = field(   # NEW v0.4
        default=30.0,
        metadata={"cache_relevant": False},
    )
    master_seed: int = field(                          # NEW v0.4
        default=0xC11B5EED,
        metadata={"cache_relevant": True},
    )
    evaluator_skip_cap_fraction: float = field(        # NEW v0.4 — Inv 28 knob
        default=0.25,
        metadata={"cache_relevant": False},  # diagnostic; doesn't affect output identity
    )
```

**Partition sentinel impact (v0.4 → tests)**: C11b inherits C11a's cache-relevant-field partition-sentinel test pattern (analogue to C11a's `test_config_cache_relevant_partition_six_six`). v0.4 changes the partition: `master_seed` (cache_relevant=True) adds 1 to the relevant count; `per_topology_wallclock_seconds` and `evaluator_skip_cap_fraction` (cache_relevant=False) add 2 to the irrelevant count. The partition-sentinel test for C11b's `LocalRefinementConfig` is part of the ~28 schema tests (§ 6) and must be authored against the v0.4 counts (v1.0 baseline counts + the v0.4 additions enumerated above).

---

## § 3 — Behaviour (REVISED v0.4)

### Phase 0 — Input + startup validation

Carried v1.0 + 1 addition:
- Capture `master_seed` into `EnvironmentFingerprint.master_seed: int` (NEW v0.4 field). Replay-tier tests can detect master-seed changes via fingerprint mismatch.

### § 3.0 — Per-topology input artifact resolution (NEW v0.4)

Per § 0.3: `_resolve_input_artifact(mtc)` returns `mtc.application_results[0].output_candidate` when non-None, else `mtc.source_candidate`. This is the ONLY path for reading the input artifact in Phase 1 (Inv 26).

### Phase 1 — Per-topology NSGA-II run (REVISED v0.4)

Carried v1.0 with v0.4 additions:

1. **Resolve input artifact** via § 3.0.
2. **Reject multi-floor** (D-MF-1): `MultiFloorRefinementNotSupportedError` if `_is_multi_floor_artifact(input_artifact)`.
3. **Derive per-topology PRNG** via § 0.7.
4. **Start wall-clock timer**; raise `PerTopologyTimeoutError` if exceeded at any generation boundary.
5. **Evaluator failure isolation** per § 0.6: per-candidate skip up to `pop_size // 4`; beyond that, raise systemic.
6. All other Phase 1 logic unchanged from v1.0.

### Phase 2 — Output assembly

Unchanged from v1.0.

### Phase 3 — Provenance assembly

Carried v1.0 + populates:
- `master_seed` into provenance
- `per_topology_wallclock_seconds` into provenance
- Per-topology timeout / skip-count counters into per-topology telemetry block

---

## § 4 — Invariants (REVISED v0.4)

v1.0 invariants 1-25 carried unchanged. v0.4 adds Inv 26-29:

| # | Invariant | Mode |
|---|---|---|
| 1-25 | (carried verbatim from v1.0) | as v1.0 |
| **26 (NEW v0.4)** | **Input-artifact resolver: `_resolve_input_artifact(mtc)` is the only path for reading mtc's artifact in Phase 1. Empty or multi-element `application_results` raises `EvaluatorContractError`. Direct `mtc.source_candidate` access elsewhere in Phase 1 is a programming bug (caught in code review).** | RAISE |
| **27 (NEW v0.4)** | **Per-topology wall-clock breach raises `PerTopologyTimeoutError`. Default `per_topology_wallclock_seconds=30.0`. Check at generation boundaries.** | RAISE |
| **28 (NEW v0.4)** | **Per-generation evaluator failure cap = `max(1, int(pop_size * config.evaluator_skip_cap_fraction))` (default fraction 0.25). Exceeding the cap upgrades to `EvaluatorContractError` systemic.** | RAISE |
| **29 (NEW v0.4)** | **PRNG seed derivation is pure-deterministic: same (`master_seed`, `topology_index`, `topology_signature`) → byte-equal stream. Asserted in replay tests.** | RAISE (replay tier) |

29 invariants at v0.4 (was 25 at v1.0).

---

## § 5 — Failure modes (REVISED v0.4)

```
LocalRefinementError (base)
├── PerTopologyError
│   ├── NSGAConvergenceError
│   ├── AreaInfeasiblePopulationError
│   ├── EvaluatorContractError
│   ├── MultiFloorRefinementNotSupportedError    (NEW v0.4)
│   └── PerTopologyTimeoutError                  (NEW v0.4)
├── BatchAllTopologiesFailedError
├── EvaluatorPurityContractError
├── EnvironmentFingerprintMismatchError
└── InvariantViolationError                       (systemic)
```

---

## § 6 — Test coverage targets (REVISED v0.4)

Target **~205 tests at LOCK** (up from v1.0's 190):

- ~28 schema (unchanged)
- ~30 NSGA-II core (unchanged)
- ~34 invariants (Inv 1-29; +4)
- ~25 phase-logic (unchanged)
- ~12 partial-batch / strict-mode (unchanged)
- ~14 replay determinism (+ master_seed mismatch tests; carried v1.0)
- ~12 evaluator contract (+ per-candidate skip cap, systemic-upgrade tests)
- ~14 edge cases (unchanged)
- ~16 v0.2 carry (unchanged)
- ~9 v0.3 carry (unchanged)
- **~12 NEW v0.4** (was 11 at v0.4 open; +1 at v0.4 close for partition-sentinel coverage):
  - 3× input-artifact resolver (Tier B output_candidate, M8 output_candidate, Tier A None fallback)
  - 1× input-artifact resolver defensive contract (empty application_results, multi-element application_results raise EvaluatorContractError per Inv 26)
  - 1× multi-floor rejection (raises MultiFloorRefinementNotSupportedError)
  - 2× per-topology timeout (within budget, exceeds budget)
  - 2× evaluator failure isolation (within skip cap, above skip cap — now config-driven)
  - 2× PRNG seed derivation (determinism within same seed, divergence across seeds)
  - 1× stub-evaluator objectives count config (2 vs 3 objectives produce different Pareto fronts)

Cumulative target update note: v1.0 LOCKED projected ~2709 passed at C11b ship from a baseline of ~2519 (post-C11a v1.0). Actual baseline at v0.4 authorship is **2909 passed / 3 skipped** (S41 close, post-C11a v1.6 + self-review fixes). C11b ship target is therefore **2909 + 12 ≈ 2921 passed** at v0.4 spec ship-out — the +12 is v0.4-specific tests; the ~190 from v1.0's projection is the *total* C11b test addition, and 12 of those land specifically from v0.4 amendments.

---

## § 7 — Open questions at v0.4

**0 open questions remaining.**

---

## § 8 — Backlog at v0.4

**New / widened at v0.4**:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C11B-MF** (NEW) | Multi-floor topology refinement for C11b | v0.4 D-MF-1 | When product needs end-to-end MF refinement (likely with C12 MF placement OR C14 MF scoring) | L |
| **B-C11B-TIMEOUT-V2** (NEW) | Per-evaluation timeout + generation-level resumability after wall-clock breach | v0.4 D-TO-3 | When measured tail-latency on production evaluator becomes a quality concern | M |
| **B-NEW-V5** (WIDENED) | Broader EA protocols + **NSGA-III migration** | v0.3 carry + v0.4 D-NSGA-2 widening | (a) C14 ≥3 obj AND (b) hypervolume regression 2+ cycles, OR (c) architect blocking feedback | L |

Existing v1.0 backlog items (B-237, B-NEW-P, B-NEW-V, B-NEW-W, B-NEW-X, B-NEW-Y, B-NEW-Z, B-NEW-V2, B-NEW-V3, B-NEW-V4, B-NEW-V6) carried unchanged.

**Cumulative at v0.4: 14 backlog items** (12 carried + 2 new at v0.4).

---

## § 9 — Rule 11 self-analysis pass on v0.4 PROPOSED

Applied Rule 11 to v0.4 itself before submitting. Findings:

| # | Finding | Verdict |
|---|---|---|
| F-v4-1 | `per_topology_wallclock_seconds=30.0` is a magic constant. Why 30s, not 10s or 120s? | **DOCUMENTED** — pragmatic compromise based on ~300ms/generation × 100 generations target. Tunable via config. B-238 (architect review) can validate post-launch. |
| F-v4-2 | `master_seed=0xC11B5EED` is decorative. A real default could be 0 or 42. | **DOCUMENTED** — decorative seed signals "C11b SEED" in hex; clearer in stack traces than `0`. No functional difference. |
| F-v4-3 | The 25% per-candidate evaluator-skip cap default. Why 25% and not 10% or 50%? | **RESOLVED at v0.4 close** — Fix (e) made the cap a config field (`evaluator_skip_cap_fraction`, default 0.25). 0.25 is the default heuristic (10% too tight for some evaluator edge cases; 50% too loose, masks systemic mis-wiring); tunable per workload via the new config field. |
| F-v4-4 | `_is_multi_floor_artifact` helper not specified in detail. v0.4 leans on `is_real_multi_floor_candidate` from C11a's `candidate_context` module. | **DOCUMENTED** — reuse of existing C11a primitive; no new code needed in C11b for the detection itself. |
| F-v4-5 | Inv 26 says the resolver is the "only path" but this is enforced by code review, not by type system. A future contributor could bypass it. | **DOCUMENTED** — same enforcement style as C11a Inv 26 (cache-relevant metadata) and C11a Inv 18 (novelty estimator). Build discipline via test coverage + code review. |
| F-v4-6 | `EnvironmentFingerprint.master_seed: int` field addition is a schema change but v0.4 doesn't bump `c11b_version` from "v1.0" → "v1.1". | **PATCH NOW in v0.4** — bump `C11B_VERSION` constant from "v1.0" to "v1.1" to match the schema growth. Replay-tier tests then detect v1.0 → v1.1 cache invalidation correctly. |
| F-v4-7 | Backlog ID format inconsistency: existing project uses `B-NEW-T3`, `B-C11A-19`, `B-C9-H`, `B-NEW-V5`. v0.4 introduces `B-C11B-MF` (suffix-letters style) and `B-C11B-TIMEOUT-V2` (suffix-versioned style). The styles already coexist in the project (e.g., `B-C9-H` matches the suffix-letters style), so v0.4's choice is consistent with the precedent set by recent C9 backlog. No action needed but worth noting for future-Claude. | **DOCUMENTED** — no action; styles already coexist. |

Patch applied: `C11B_VERSION: Final[str] = "v1.1"` (NEW in v0.4, was "v1.0" at v1.0 LOCKED).

**Audit findings summary**: 8 findings surfaced during v0.4 authorship; final disposition: 5 DOCUMENTED (F-v4-1, F-v4-2, F-v4-4, F-v4-5, F-v4-7), 1 PATCH-NOW folded into v0.4 body (F-v4-6 → C11B_VERSION bump), 1 RESOLVED via config field (F-v4-3 → fix (e)). No blockers.

---

## § 10 — Status

- **v0.4 PROPOSED. NOT LOCKED.**
- Authored at S41 close to address post-LOCK drift + Rule 11 self-analysis findings.
- 8 critique items resolved (7 spec amendments + 1 new backlog + 1 widened backlog; D-EV-3 added during self-review pass).
- 0 open questions remain.
- 8 audit findings: 5 DOCUMENTED, 1 PATCH-NOW folded in, 1 RESOLVED via config field, 1 DOCUMENTED at close (F-v4-7 backlog naming).
- 14 backlog items (12 carried + 2 new at v0.4).
- 29 invariants (was 25 at v1.0); 4 new (Inv 26-29).

**Awaits Ramalingam adjudication per Rule 8.**

---

## § 12 — Backlog enumeration

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-237 | Cross-platform replay CI matrix + Decimal geometry + BLAS/CPU fingerprinting | S35 carry | M |
| B-NEW-P | Upstream `severity_tier` ClassVar amendment cluster | S37 W#4 carry | XS |
| B-NEW-V | C11b refinement scope expansion | v0.1 Q4 | M |
| B-NEW-W | C11b hypervolume diversity metric | v0.1 Q5 | M |
| B-NEW-X | C11b adaptive NSGA-II hyperparameters | future tuning | M |
| B-NEW-Y | C11b cross-topology Pareto aggregation | v0.1 Q2 | M |
| B-NEW-Z | C11b deterministic-parallel-NSGA-II | scaling pressure | L |
| B-NEW-V2 | C11b per-category bound multipliers (KB-driven) | W#2 #3 | M |
| B-NEW-V3 | C11b objective_balance output ordering | W#2 #7 | S-M |
| B-NEW-V4 | C11b Dirichlet area partitioning | W#3 #2 | M |
| **B-NEW-V5** | **Broader EA protocols + NSGA-III migration (WIDENED v0.4)** | W#3 #6 + v0.4 D-NSGA-2 | L |
| B-NEW-V6 | C11b cache memory-budget LRU eviction | W#3 #8 | S-M |
| **B-C11B-MF** (NEW v0.4) | **Multi-floor topology refinement** | v0.4 D-MF-1 | L |
| **B-C11B-TIMEOUT-V2** (NEW v0.4) | **Per-evaluation timeout + generation-level resumability** | v0.4 D-TO-3 | M |

**Backlog summary**:

| Total | Pre-existing | v0.1 | v0.2 | v0.3 | v0.4 |
|---|---|---|---|---|---|
| **14** | 2 | 5 | 2 | 3 | **2** |

---

## § 13 — Complexity Budget (REVISED v0.4)

### v1 surface area: 10 subsystems (UNCHANGED at v0.4)

v0.4 adds 0 new subsystems. All changes are within-subsystem:

- D-MF-1: within Phase 1 routing (existing subsystem)
- D-OC-1: within Phase 1 input handling (existing subsystem)
- D-TO-1: within Phase 1 generation loop (existing subsystem)
- D-NSGA-1: within StubEvaluator (existing subsystem)
- D-EV-1: within Phase 1 evaluator-orchestration (existing subsystem)
- D-PR-1: within Phase 0 + Phase 1 PRNG-setup (existing subsystem)

Subsystem count cap met. No architectural growth from this amendment.

---

## § 14 — Freeze candidacy rationale (REVISED v0.4)

### § 14.1 — Convergence signals

| Walk | Open Qs | Audit findings | New v1 subsystems |
|---|---|---|---|
| v0.1 | 7 | 8 | 9 (initial) |
| v0.2 | 2 | 7 | +1 |
| v0.3 | 0 | 5 | +0 |
| v1.0 LOCKED | 0 | 5 (carried) | +0 |
| **v0.4** | **0** | **6** | **+0** |

v0.4 added 1 audit finding (F-v4-6, PATCH-NOW), kept all else. Convergence pattern stable. Walk #4 stayed at budget cap.

### § 14.2 — Why v0.4 isn't a full re-walk

v0.4 is **drift-resolution + Rule 11 sanity pass**, not a redesign:
- 6 critique items, all from post-LOCK reality changes or Rule 11 hunt (not external reviewer)
- 0 design-space decisions reopened
- 0 new subsystems
- 4 new invariants (incremental, not foundational)
- 2 new backlog items (post-v1 work, not v1 expansion)

If LOCKED, v0.4 is the spec C11b builds against. If not LOCKED (e.g., you want a Walk #4 external critique cycle first), v0.4 stays PROPOSED until that walk runs.

### § 14.3 — Recommendation

**Request LOCK on v0.4.** This addresses the spec-vs-reality drift the prior LOCK didn't anticipate. Decision is yours per Rule 8.

---

**End of v0.4 PROPOSED.** Awaits Ramalingam adjudication: LOCK or Walk #N.
