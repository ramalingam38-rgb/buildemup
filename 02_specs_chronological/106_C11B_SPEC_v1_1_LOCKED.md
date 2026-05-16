# C11b — Local Refinement (NSGA-II) — SPEC v1.1 LOCKED

**Component**: 11b (canonical Track 3 numbering — paired with C11a Topology Mutation)
**Status**: **v1.1 LOCKED at S41 close by Ramalingam authority per Rule 8.**
**LOCKED ON**: S41 (May 12, 2026), from v0.7 PROPOSED.
**Authored**: S41 — 6 walks of evolution (v0.4 self-analysis → v0.5 Walk #4 → v0.6 Walk #5 → v0.7 Walk #6 → LOCK).
**Supersedes**: v1.0 LOCKED at S37 (SUPERSEDED — v1.0 cache invalidates via `c11b_version="v1.0"` → "v1.1" fingerprint mismatch).
**Predecessors**: v0.1 PROPOSED (S35), v0.2 PROPOSED (S36), v0.3 PROPOSED → v1.0 LOCKED (S37, SUPERSEDED), v0.4-v0.7 PROPOSED (S41).

**C11B_VERSION constant**: `Final[str] = "v1.1"` — the LOCKED version string referenced throughout the spec.

---

## § 0 — Why v0.7 exists

v0.6 PROPOSED received Walk #6 external critique (15 items). Verdicts after Rule 7 walk + Rule 11 self-analysis + 2 web searches (dominance hash structures, replay fingerprint versioning) + code grep on `buildemup/utilities/canonical.py`:

- **6 PATCH-NOW items** (correctness + cognitive-cost improvements) — folded into v0.7 body
- **4 PATCH-NOW backlog-text amendments** (tighten existing backlog wording without new items)
- **1 NEW BACKLOG item** (B-C11B-TIER2-SCALING)
- **4 ALREADY-DOCUMENTED items** carried with PROMOTION to high-priority (existing backlog items unchanged in substance, raised in priority)

The 6 PATCH-NOW correctness/UX fixes:

1. **Item 1** — Capability-flag triple cognitive cost. v0.6 ships 3 booleans that collapse to 2 effective states at v1 via the equality invariant. Future contributors may construct invalid state combinations not caught by tests. v0.7 adds:
   - `RefinedCandidate.__post_init__` HARD assertion of the 3-flag equality invariant (was test-only at v0.6)
   - `RefinedCandidate.from_operator_class(operator, ...)` helper constructor; direct flag construction discouraged
   - Derived read-only property `capability_mode: Literal["PREDICATE_ONLY", "MATERIALIZED"]` for logging/readability
2. **Item 3 (HIGH severity)** — `tiebreak_fingerprint` derivation depended on `canonical_serialize(refined_parameters)` without explicit version anchor. Code grep on `buildemup/utilities/canonical.py` confirmed: no `SERIALIZATION_VERSION` constant; only `CANONICAL_FP_PRECISION = 6` exists, which is a single bare module-level constant. If C7 or any other component changes float precision in a future amendment, every cached `tiebreak_fingerprint` silently drifts without cache-key invalidation. v0.7 adds:
   - `TIEBREAK_FINGERPRINT_SCHEMA_VERSION: Final[int] = 1` constant in C11b's tie-break module
   - Fingerprint derivation explicitly includes this version: `sha256(f"{TIEBREAK_FINGERPRINT_SCHEMA_VERSION}|" + canonical_serialize(...))`
   - `EnvironmentFingerprint.tiebreak_fingerprint_schema_version: int` field added so cache keys observe this version directly
   - Bump rule: any change to canonical_serialize semantics that affects tie-break OR any deliberate change to fingerprint derivation increments this version
3. **Item 4** — TIER-3 underspecification (currently "deferred to B-NEW-W" with no minimum semantics). v0.7 freezes minimum TIER-3 semantics in § 0.7.2 (NEW): paired Wilcoxon signed-rank test, 30 paired benchmark runs minimum, two-tailed p > 0.05, hypervolume normalized via reference-point = max+1 in each objective, benchmark corpus version-anchored.
4. **Item 6** — Resolver type safety. v0.7 introduces `get_primary_application_result(mtc: MutatedTopologyCandidate) -> MutationApplicationResult` accessor + `PrimaryApplicationResult` type alias. Direct `mtc.application_results[0]` access in C11b code becomes a code-review violation (lint-checkable pattern).
5. **Item 8** — Meta-test fragility. v0.7 replaces the "SemVer table exists in § 0.3.4" doc-presence test with `SEMVER_POLICY_VERSION: Final[int] = 1` constant. The test asserts the constant exists at the documented value; spec text can move without breaking tests.
6. **Item 15** — Replay/optimization balance declaration. v0.7 adds § 0.0c "Product-relevance audit of replay guarantees" declaring which replay tiers are product-critical (TIER-1 byte-equal for cache correctness, TIER-2 structural for CI regression detection) versus research/debug (TIER-3 statistical, deferred). Operators can selectively relax tiers via existing verbosity knob.

The 4 PATCH-NOW backlog-text amendments (no new items, sharper triggers/scope):

- **B-C11B-DOERR-TIEBREAK** (W6-5): Append continuous-objective-incompatibility caveat. Doerr 2024's proof assumes discrete-valued objectives; continuous floats reduce frequency-counting to ~all-1 buckets. Production C14 evaluator will likely emit continuous values, so the backlog item requires empirical validation + epsilon-clustering/density-estimation research before adoption.
- **B-C11B-HYPERVOLUME-WARN** (W6-13): Append freeze-normalization-first requirement. Hypervolume is sensitive to reference-point choice; the backlog item must freeze normalization policy + benchmark corpus BEFORE the warning fires in production.
- **B-C11B-TIMEOUT-V2** (W6-10): Append intra-generation watchdog hooks to the scope (candidate-evaluation checkpoints, evaluator soft deadlines, heartbeat timestamps).
- **B-C11B-CACHE-TIERS** (W6-9): Trigger criterion tightened — "when cache hit rate drops below 50% in experimentation runs" instead of vague "when measured cache hit rates collapse."

The 1 new backlog item:

- **B-C11B-TIER2-SCALING** (W6-2): O(N²) dominance check in TIER-2 replay validation becomes a CI bottleneck at large populations (N≥1000). Backlog covers: hash normalized dominance matrices, compare front-adjacency signatures, Pareto layer DAG fingerprints. Standard literature treatment via ND-trees (Bashir 2025 arxiv 2508.20689) for ≥3 objectives.

4 ALREADY-DOCUMENTED-AND-PROMOTED items:

- **Item 7** (subsystem count under-measures complexity): B-C11B-COMPLEXITY-BUDGET-V2 already exists; promoted to mandatory next-walk surface — every future walk MUST report the weighted complexity metric in § 14.1.
- **Item 11** (provenance god-object): B-C11B-PROVENANCE-SPLIT promoted to HIGH priority — trigger criterion tightened to "any change requiring a c11b_version bump."
- **Item 12** (candidate_index parallel-unsafe): B-NEW-Z (deterministic-parallel-NSGA-II) cross-referenced explicitly in § 0.7.1.
- **Item 14** (spec length usability): B-C11B-SPEC-SPLIT-V2 promoted; v0.7 adds § 0.0d "Current surface only" digest pointing to the v1 contract surface in 1 screen.

v0.7 introduces 0 new subsystems. Subsystem cap stays at 10 (held across 6 walks now). The weighted complexity metric (B-C11B-COMPLEXITY-BUDGET-V2 preview) puts the v0.7 actual complexity at:
- Invariants × 1 = 29
- Cache-affecting fields × 2 = 3 × 2 = 6
- Replay tiers × 3 = 3 × 3 = 9
- Telemetry fields × 0.5 = 8 × 0.5 = 4
- **Weighted total = 48** (vs subsystem count = 10)

This makes Item 7's diagnosis concrete: the spec-text complexity has grown 4.8× the subsystem count.

---

## § 0.0a — Why v0.6 existed (preserved context)

v0.5 PROPOSED received Walk #5 external critique (20 items). Verdicts after Rule 7 walk + Rule 11 self-analysis + 2 web searches (NSGA-II tie-breaking literature; cache fragmentation patterns) + code grep on `c11a/provenance.py`:

- **6 PATCH-NOW items** (correctness or contract tightening) — folded into v0.6 body
- **6 BACKLOG verdicts** — filed against post-v1 work (including one notable literature finding); plus 2 derived items (one OUT-OF-SCOPE → routed via cross-component backlog; one PATCH-NOW follow-on) for **8 total new backlog entries**
- **4 ALREADY-DOCUMENTED items** — existing v0.4/v0.5 text covers
- **2 OUT-OF-SCOPE items** — cross-component concerns routed elsewhere
- **2 items already accounted for** in v0.4/v0.5 backlog (B-C11B-EVALUATOR-RESILIENCE, B-C11B-STRICT-TIERS, B-C11B-TIMEOUT-COMPLEXITY)

The 6 PATCH-NOW items:
1. **Item 1** — Replay determinism nomenclature gap. v0.5 Inv 29 carried a 3-way conjunction (seed + env tuple + tie-break) and a "1e-9 structural" tolerance, but didn't formalize the tiers. v0.6 adds explicit TIER-1 / TIER-2 / TIER-3 nomenclature: TIER-1 byte-equal under full conjunction; TIER-2 structurally-equivalent under partial conjunction; TIER-3 statistically-equivalent for cross-environment checks.
2. **Item 5** — `mutation_semantics: Literal["PREDICATE_ONLY", "MATERIALIZED"]` enum has limited extensibility for downstream consumers. Replaced with three boolean capability flags: `geometry_materialized: bool`, `placement_safe: bool`, `requires_transform_resolution: bool`. Same information, cleaner extension surface.
3. **Item 10** — Inv 29's TIER-2 tolerance was numeric-only (`1e-9` absolute), which can hide cumulative drift over many generations. Strengthened to a conjunction: same numeric tolerance AND same Pareto rank cardinality per front AND same dominance relations across the front. Prevents replay regressions from being masked as "structurally equivalent."
4. **Item 12** — Tie-break uses `canonical_serialize(refined_parameters)` hashing. At NSGA-II sort time this is O(N²) hash calls. v0.6 precomputes a compact `tiebreak_fingerprint: int` on `RefinedCandidate.__post_init__` (one hash per candidate) and reuses it during sort.
5. **Item 18** — `nsga2_objective_count_warning: bool` is always True at v1 (default `objectives=3` always triggers the flag), defeating the warning's purpose. Replaced with `resolved_objective_count: int` carrying the actual count. Operators read the number, not a boolean. Hypervolume-regression-based warning (the operationally correct semantics) is filed as backlog `B-C11B-HYPERVOLUME-WARN`.
6. **Item 19** — v0.5 § 0.3.3 documented v1.0 → v1.1 migration but didn't define `C11B_VERSION` SemVer rules. v0.6 adds § 0.3.4 with explicit MAJOR/MINOR/PATCH semantics for cache-breaking, telemetry, replay, and invariant changes.

The 6 new backlog items (notable: Item 2 surfaces a recent peer-reviewed paper):

- **B-C11B-DOERR-TIEBREAK** (Item 2 + Item 15) — Adopt Doerr et al. 2024 NSGA-II frequency-based tie-break ("Speeding Up the NSGA-II With a Simple Tie-Breaking Rule"). Proves NSGA-II can optimize benchmarks efficiently for many objectives. Addresses both v0.5 Items 2 + 15 (tie-break bias + 3-objective limitation) with a single proven literature remedy.
- **B-C11B-CACHE-TIERS** (Item 4) — Cache-relevance tiering (OUTPUT_CRITICAL / REPLAY_CRITICAL / DIAGNOSTIC) instead of binary `cache_relevant: bool`.
- **B-C11B-PROVENANCE-SPLIT** (Item 11) — Split `LocalRefinementProvenance` into ReplayProvenance + OperationalTelemetry + DiagnosticWarnings.
- **B-C11A-MTC-SINGLETON** (Item 13) — C11a v1.6 amendment to expose `primary_application_result` as a singleton field; eliminates tuple-vs-singleton schema dishonesty.
- **B-C11B-COMPLEXITY-BUDGET-V2** (Item 14) — Weighted complexity metric (invariants + cache-affecting fields + replay constraints + telemetry fields) alongside subsystem count.
- **B-C11B-SPEC-SPLIT-V2** (Item 20) — Documentation split: C11b-Core-Optimization / C11b-Replay / C11b-Provenance / C11b-Failure-Policy.
- **B-PIPELINE-CAPABILITY-NEGOTIATION** (Item 7, ROUTED TO ORCHESTRATOR) — Upstream capability flag so MF-incapable downstreams suppress MF generation. Cross-component; not C11b's surface.
- **B-C11B-HYPERVOLUME-WARN** (Item 18 follow-on) — Hypervolume-regression detection as the actually-useful warning signal. Requires implementing hypervolume computation first.

Items routed as ALREADY-DOCUMENTED: Items 3 (candidate_index → carry to B-NEW-Z parallel-NSGA-II), 6 (telemetry growth → existing verbosity knob), 8 (evaluator resilience → existing B-C11B-EVALUATOR-RESILIENCE), 9 (timeout complexity → existing B-C11B-TIMEOUT-COMPLEXITY), 16 (STRICT brittleness → existing B-C11B-STRICT-TIERS).

Items routed as OUT-OF-SCOPE: Item 17 (replay CI → B-237 cross-platform CI matrix).

v0.6 introduces no new subsystems. Subsystem cap stays at 10 (held across all walks).

---

## § 0.0aa — Why v0.5 existed (preserved context)

v0.4 PROPOSED received Walk #4 external critique (20 items). Verdicts after Rule 7 walk + Rule 11 self-analysis + web research:

- **6 PATCH-NOW items** (correctness or consistency bugs) — folded into v0.5 body.
- **4 small documentation/telemetry additions** — folded into v0.5 body.
- **6 BACKLOG items** — filed against post-v1 work.
- **4 ALREADY-DOCUMENTED items** — existing v0.4 text covers; tightened where helpful.

The PATCH-NOW set:
1. **Item 16** — Internal default inconsistency for `StubEvaluatorConfig.objectives` (§ 1 + § 2.1 said default 2; § 0.5 said default 3). Resolved to default 3 (carries v0.3 LOCKED behavior).
2. **Item 4** — `evaluator_skip_cap_fraction` was `cache_relevant=False`; this is wrong because changing the cap can produce divergent Pareto fronts (different population sizes → different selection dynamics). Flipped to `cache_relevant=True`.
3. **Item 5** — `per_topology_wallclock_seconds` was `cache_relevant=False`; same logic (timeout-truncated outputs ≠ full-completion outputs). Flipped to `cache_relevant=True`.
4. **Item 6** — PRNG tie-break determinism unspecified. Added explicit lex-ASC tie-break on `(topology_signature, candidate_index)` for NSGA-II crowding-distance ties and Pareto-rank ties.
5. **Item 11** — Inv 29's "byte-equal Pareto fronts" claim required tightening: byte-equality holds only under the conjunction (same master_seed AND same CI-validated environment tuple AND deterministic tie-break). Wording corrected.
6. **(implicit, from Item 16)** — Partition sentinel counts re-derived: 2 fields flipped from cache_irrelevant to cache_relevant changes the partition baseline.

The additions:
- **Item 1 small fix** — `skipped_multifloor_count` telemetry field on `LocalRefinementProvenance`.
- **Item 2 small fix** — `mutation_semantics: Literal["PREDICATE_ONLY", "MATERIALIZED"]` documentation field on `RefinedCandidate`.
- **Item 3 small fix** — `longest_generation_seconds` telemetry field on per-topology provenance.
- **Item 10 small fix** — `nsga2_objective_count_warning: bool` flag in `LocalRefinementProvenance` when `objectives >= 3`.

The backlog set:
- **B-C11B-EVALUATOR-RESILIENCE** (item 7) — replenish-skipped-candidates strategy
- **B-C11B-RESOLVER-V2** (item 8) — `primary_application_result` singleton field if multi-result MTCs land
- **B-C11B-TIMEOUT-COMPLEXITY** (item 12) — complexity-aware timeout budget
- **B-C11B-INV-TIERING** (item 14) — CORE/REPLAY/DIAGNOSTIC invariant categorization
- **B-C11B-STRICT-TIERS** (item 17) — STRICT_PER_TOPOLOGY vs STRICT_GLOBAL distinction
- **B-C12-MATERIALIZATION-CONTRACT** (item 2 downstream) — C12 must assert geometry materialization before placement

v0.5 introduces no new subsystems. Subsystem cap stays at 10 (carried from v1.0). 1 audit finding (F-v4-7 from v0.4 close) carried forward unchanged.

---

## § 0.0b — Why v0.4 existed (preserved context)

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

## § 0.0c — Product-relevance audit of replay guarantees (NEW v0.7 W6-15)

Walk #6 Item 15 raised the architectural concern that v0.6's replay infrastructure was approaching dominance over the optimization core itself. v0.7 responds with an explicit audit, declaring product-criticality per replay surface:

| Surface | Product-criticality | Rationale | If product priorities shift |
|---|---|---|---|
| **TIER-1 byte-equal Pareto fronts** | **PRODUCT-CRITICAL** | Cache correctness depends on it: the same `EnvironmentFingerprint` MUST produce the same outputs, otherwise cache returns stale data. Without TIER-1, the cache becomes a correctness liability rather than an optimization | Removal would require redesigning the cache contract; deferred-evaluation pattern instead |
| **TIER-2 structurally-equivalent (1e-9 + dominance + cardinality)** | **PRODUCT-CRITICAL** | Used in CI regression detection across BLAS/platform drift. Without TIER-2, a single CI tuple change forces full pipeline re-validation manually | Replaced with snapshot-comparison CI; lower confidence in cross-platform drift detection |
| **TIER-3 statistically-equivalent (paired Wilcoxon hypervolume)** | **RESEARCH/DEBUG** | Only used when CI tuples themselves change (NumPy major version, new BLAS variant). Deferred to B-NEW-W. Operator-facing usefulness limited until hypervolume tooling exists | Drop entirely; cross-CI-tuple changes get explicit operator review instead |
| **Deterministic tie-break (§ 0.7.1)** | **PRODUCT-CRITICAL** | Required by TIER-1; without it, byte-equal Pareto fronts are impossible | (Removing would remove TIER-1 with it) |
| **`master_seed` config field** | **PRODUCT-CRITICAL** | Reproducibility starting point; operator-controllable | (Cannot remove without removing replay) |
| **`tiebreak_fingerprint` precompute** | **PRODUCT-CRITICAL** | Performance: avoids O(N²) hash work per generation | (Could revert to per-sort hashing, accept perf cost) |
| **`per_topology_telemetry`, `longest_generation_seconds`, `skipped_*` counters** | **OPERATIONAL** | Diagnostic value for production tuning; not correctness | Verbosity knob already gates these |
| **`resolved_objective_count`, `nsga2_objective_count_warning`** | **OPERATIONAL** | Signals NSGA-II 3-objective limitation; informs B-NEW-V5 migration | Drop if NSGA-III lands first |

**Net product surface**: 6 PRODUCT-CRITICAL, 2 OPERATIONAL, 1 RESEARCH/DEBUG. v1 ships all surfaces; operators can selectively quiet OPERATIONAL via verbosity. RESEARCH/DEBUG TIER-3 is deferred — landing it post-v1 is fine.

The reviewer's Item 15 concern was that replay infrastructure was overshadowing optimization. The audit shows: of 9 listed replay surfaces, 6 are genuinely product-critical (cache correctness depends on them), 2 are operational, 1 is research/debug. The infrastructure-vs-optimization split is roughly 6:3 toward infrastructure, which is justified for an optimization component that ships a deterministic cache.

---

## § 0.0d — Current surface only digest (NEW v0.7 W6-14)

For contributors who only need to know what C11b actually does at v1 LOCK (not the walk-history), this digest reproduces the v1 contract surface in ~one screen:

**Top-level function:**
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

**Per-topology Phase 1 order**:
1. Resolve input artifact via `get_primary_application_result(mtc)` (v0.7 W6-6 accessor) + `_resolve_input_artifact`
2. Reject multi-floor (`MultiFloorRefinementNotSupportedError`)
3. Derive `topology_signature` via C11a's `derive_canonical_signature`
4. Build per-topology PRNG via `derive_per_topology_seed(master_seed, topology_index, topology_signature)` → `np.random.SeedSequence`
5. Start wall-clock timer (raise `PerTopologyTimeoutError` at gen boundaries)
6. NSGA-II loop: evaluate (skip per-candidate up to `evaluator_skip_cap_fraction × pop_size`), sort by rank + crowding + tie-break (§ 0.7.1: `(topology_signature, tiebreak_fingerprint, candidate_index)`), select survivors
7. Emit `RefinedCandidate`s carrying 3 capability flags + tiebreak_fingerprint + source_topology_candidate_signature

**Key invariants for builders**:
- Inv 26: `_resolve_input_artifact` is the only path
- Inv 27: Per-topology wall-clock breach raises
- Inv 28: Skip cap = `max(1, int(pop_size * config.evaluator_skip_cap_fraction))`
- Inv 29: PRNG determinism + TIER-1/2/3 replay equivalence (§ 0.7 + § 0.7.2)
- Plus carried v1.0 Inv 1-25 (in main v0.4 spec carry section)

**v1 capability flag equality** (§ 0.3.1): `placement_safe == geometry_materialized AND requires_transform_resolution == NOT geometry_materialized`. Constructed via `RefinedCandidate.from_operator_class(operator, ...)` helper.

**v1 PRODUCT-CRITICAL surfaces** (§ 0.0c): TIER-1 byte-equal, TIER-2 structural, deterministic tie-break, master_seed, tiebreak_fingerprint precompute, capability flags.

If anything above is unclear, the full spec body is the source of truth; the digest is a navigation aid for builders who need the v1 contract surface without walking through the 6-walk delta history.

---

## § 0.1 — v1.0 → v0.4 delta summary

| Change ID | Section | Scope | Type |
|---|---|---|---|
| **D-MF-1** | § 2 (Contract) | Add explicit rejection of multi-floor inputs at v1. `MultiFloorWetZonePlannedCandidate` as `source_candidate` raises `MultiFloorRefinementNotSupportedError`. | Spec-text addition |
| **D-MF-2** | § 8 (Backlog) | File **B-C11B-MF**: multi-floor refinement scope expansion. | Backlog addition |
| **D-OC-1** | § 2.1 (Schema) + § 3 (Behaviour) | Document that C11b reads `MutationApplicationResult.output_candidate` as the input artifact when present; for Tier A SHALLOW results with `output_candidate=None`, C11b refines the `source_candidate` directly (predicate-only operators don't materialize new geometry; C11b operates on the unchanged source). | Spec-text clarification |
| **D-OC-2** | § 4 (Invariants) | Add **Inv 26**: C11b's input-artifact resolution rule is deterministic per the v0.4 § 3.0 algorithm. | RAISE |
| **D-TO-1** | § 2.2 (Config) | Add `per_topology_wallclock_seconds: float = 30.0` **(cache_relevant=True per v0.5 Item 5 PATCH-NOW — see § 0.1a; v0.4 incorrectly marked False)**. | Spec-text addition |
| **D-TO-2** | § 5 (Failure modes) | Add `PerTopologyTimeoutError(PerTopologyError)`. | Spec-text addition |
| **D-TO-3** | § 4 (Invariants) | Add **Inv 27**: per-topology wall-clock breach raises `PerTopologyTimeoutError` and contributes to `BatchAllTopologiesFailedError` accounting. | RAISE |
| **D-NSGA-1** | § 0.5 (StubEvaluator) | Add `StubEvaluatorConfig` with `objectives: Literal[2, 3] = 3` (default carries v0.3 3-objective behavior; 2-objective mode added as a config knob for testing inside NSGA-II's proven regime). | Spec-text addition |
| **D-NSGA-2** | § 8 (Backlog) | **Widen B-NEW-V5** trigger: explicit measurable criterion for NSGA-III migration (when production evaluator returns ≥3 objectives AND empirical hypervolume regression is observed across 2+ release cycles). | Backlog widening |
| **D-EV-1** | § 3 (Behaviour) | Specify evaluator failure isolation: a single `evaluator.evaluate()` raising `EvaluatorContractError` is per-candidate (skip that candidate, continue the generation); a systemic exception type (non-EvaluatorContractError) halts the topology with `EvaluatorContractError` wrapping. | Spec-text addition |
| **D-EV-2** | § 4 (Invariants) | Add **Inv 28**: per-generation evaluator failure cap = `max(1, int(pop_size * config.evaluator_skip_cap_fraction))` (default fraction 0.25). Exceeding the cap upgrades to systemic. | RAISE |
| **D-EV-3** | § 2.2 (Config) | Add `evaluator_skip_cap_fraction: float = 0.25` **(cache_relevant=True per v0.5 Item 4 PATCH-NOW — see § 0.1a)**. Makes Inv 28's cap configurable. | Spec-text addition |
| **D-PR-1** | § 2.2 (Config) + § 3 Phase 0 | Specify `master_seed: int = 0xC11B5EED` (cache_relevant=True). Per-topology seed = `hash_to_int(master_seed, topology_index, topology_signature) % 2**32`. | Spec-text addition |
| **D-PR-2** | § 4 (Invariants) | Add **Inv 29**: PRNG seed derivation is pure-deterministic; two runs with the same master_seed + same topology_signature MUST produce byte-equal PRNG streams (**v0.5 tightened — see § 0.1a Item 11**). | RAISE (replay tier) |

**Net at v0.4: 29 invariants (was 25 at v1.0). 4 new invariants (26, 27, 28, 29). 3 new config fields (`per_topology_wallclock_seconds`, `master_seed`, `evaluator_skip_cap_fraction`), 1 new failure type (`PerTopologyTimeoutError`), 1 new error type (`MultiFloorRefinementNotSupportedError`). 1 spec-text expansion of `StubEvaluator` (`objectives: Literal[2,3]=3`, default carries v0.3). 1 widened backlog item trigger (B-NEW-V5). 2 new backlog items (B-C11B-MF, B-C11B-TIMEOUT-V2).**

---

## § 0.1a — v0.4 → v0.5 delta summary (Walk #4 PATCH-NOW)

| Change ID | Section | Scope | Type |
|---|---|---|---|
| **W4-1 (Item 16)** | § 1, § 2.1 | Internal default consistency: `StubEvaluatorConfig.objectives = 3` everywhere (was "defaults to 2" in stale § 1 row and § 2.1 line — inherited drift from earlier draft). | Spec-text correction |
| **W4-4 (Item 4)** | § 2.2 (Config), § 0.6 | `evaluator_skip_cap_fraction.cache_relevant`: False → True. The skip cap CAN alter outputs (different surviving populations → different Pareto fronts), so it must be in the cache key. | Spec-text correction |
| **W4-5 (Item 5)** | § 2.2 (Config), § 0.4 | `per_topology_wallclock_seconds.cache_relevant`: False → True. A timeout-truncated run ≠ a normally-completed run; must be in the cache key. | Spec-text correction |
| **W4-6 (Item 6)** | § 0.7, § 4 (Inv 29) | Specify deterministic tie-break for NSGA-II: when two candidates tie on Pareto rank AND crowding distance, lex-ASC by `(topology_signature, candidate_index)`. Without this rule, byte-equal Pareto fronts can drift across runs. | Spec-text addition |
| **W4-11 (Item 11)** | § 0.7 (Inv 29 wording) | Tighten "byte-equal Pareto fronts" claim: byte-equality holds AS A CONJUNCTION of (same master_seed) AND (same CI-validated environment tuple per `EnvironmentFingerprint`) AND (deterministic tie-break per W4-6). | Spec-text tightening |
| **W4-1-tel (Item 1)** | § 2.1 (Schema) | Add `skipped_multifloor_count: int` field to `LocalRefinementProvenance`. Counts inputs that were filtered as multi-floor. Diagnostic only. | Spec-text addition |
| **W4-2-tel (Item 2)** | § 2.1 (Schema) | Add `mutation_semantics: Literal["PREDICATE_ONLY", "MATERIALIZED"]` field on `RefinedCandidate`. Documents whether the source mutation has been geometrically materialized; downstream consumers (C12) read this. Tier A SHALLOW → "PREDICATE_ONLY"; Tier B + M8 → "MATERIALIZED"; M0 single/multi-floor → "MATERIALIZED" (identity counts as materialized). | Spec-text addition |
| **W4-3-tel (Item 3)** | § 2.1 (Schema) | Add `longest_generation_seconds: float` field to per-topology provenance. Surfaces the within-topology stragglers that approached but didn't breach `per_topology_wallclock_seconds`. | Spec-text addition |
| **W4-10-tel (Item 10)** | § 2.1 (Schema) | Add `nsga2_objective_count_warning: bool` field to `LocalRefinementProvenance`. Set to True when `len(objective_vector.values) >= 3` to surface NSGA-II's documented many-objective limitation (Doerr 2022). | Spec-text addition |
| **W4-8-doc (Item 8)** | § 0.3 | Explicit documentation that v1's `_resolve_input_artifact` assumes `len(application_results) == 1` per C11a's v1 convention. Brittleness is acknowledged; v0.5 takes no behavior change. Filed as B-C11B-RESOLVER-V2. | Spec-text clarification |
| **W4-9-doc (Item 9)** | § 3 Phase 1 | Tighten step ordering: MF rejection occurs IMMEDIATELY after input-artifact resolution and BEFORE signature derivation, PRNG construction, evaluator init, or any other work. | Spec-text tightening |
| **W4-20-doc (Item 20)** | § 0.3 (NEW v0.5 subsection) | Explicit v1.0 → v1.1 migration semantics: old caches deserialize-miss via `C11B_VERSION` bump (already in v0.4 F-v4-6 PATCH-NOW); no in-place migration needed. | Spec-text clarification |

**Net at v0.5**: 29 invariants (unchanged from v0.4 — W4 fixes refine existing invariants 26-29, no new invariants). 0 new config fields (existing fields' `cache_relevant` flipped). 4 new provenance/result fields. 0 new failure types. 0 new spec subsystems. 6 new backlog items.

**Partition sentinel update (v0.5)**: The two cache_relevant flips (W4-4, W4-5) mean two fields moved from the irrelevant side to the relevant side. The partition sentinel test for `LocalRefinementConfig` must be re-derived against this v0.5 baseline:
- v0.4 baseline (now stale): N_relevant + 1 (master_seed); 2 added to irrelevant (timeout, skip_cap_fraction)
- v0.5 baseline: N_relevant + 3 (master_seed, timeout, skip_cap_fraction); 0 added to irrelevant

The test authoring per § 6 must use the v0.5 counts.

---

## § 0.1b — v0.5 → v0.6 delta summary (Walk #5 PATCH-NOW)

| Change ID | Section | Scope | Type |
|---|---|---|---|
| **W5-1 (Item 1)** | § 0.7, § 4 (Inv 29) | Replay TIER-1 / TIER-2 / TIER-3 nomenclature added. TIER-1 = byte-equal under full conjunction (same seed + same env tuple + same tie-break). TIER-2 = structurally-equivalent under partial conjunction (1e-9 numeric + same dominance + same rank cardinality per front). TIER-3 = statistically-equivalent for cross-environment checks (paired Wilcoxon hypervolume comparison, deferred to B-NEW-W hypervolume metric). | Spec-text addition |
| **W5-5 (Item 5)** | § 2.1 (Schema), § 0.3.1 (Worked example) | `RefinedCandidate.mutation_semantics: Literal[...]` replaced with three booleans: `geometry_materialized: bool`, `placement_safe: bool`, `requires_transform_resolution: bool`. Same information; cleaner extension. Worked-example table re-derived. | Spec-text correction |
| **W5-10 (Item 10)** | § 0.7, § 4 (Inv 29) | TIER-2 strengthened from numeric-only `1e-9` to a CONJUNCTION: (1e-9 absolute on numeric values) AND (same Pareto rank cardinality per front) AND (same dominance relations across all pairs in the front). Prevents cumulative drift from masquerading as "structurally equivalent." | Spec-text tightening |
| **W5-12 (Item 12)** | § 2.1 (Schema), § 0.7.1 (Tie-break rule) | Add `RefinedCandidate.tiebreak_fingerprint: int` computed once at `__post_init__`. Tie-break sort reads this 64-bit int instead of recomputing `canonical_serialize` hash. Reduces tie-break overhead from O(N²) hash work to O(N) precompute + O(N²) integer comparisons. | Spec-text optimization |
| **W5-18 (Item 18)** | § 2.1 (Schema), § 3 Phase 3 | `LocalRefinementProvenance.nsga2_objective_count_warning: bool` replaced with `resolved_objective_count: int`. Carries the actual count (1, 2, 3, or higher per future C14). Operators read the value; "always-True at v1" alert fatigue eliminated. | Spec-text correction |
| **W5-19 (Item 19)** | § 0.3.4 (NEW v0.6 subsection) | Explicit SemVer rules for `C11B_VERSION`: MAJOR for invariant-removal/contract-break, MINOR for invariant-addition or new failure-mode taxonomy, PATCH for telemetry-only additions or DOCUMENTED-tier wording fixes. Cache-key changes always trigger at least MINOR. | Spec-text addition |

**Net at v0.6**: 29 invariants (unchanged from v0.5; Inv 29 TIER-2 wording tightened in place, no new invariants). 1 schema replacement (`mutation_semantics` enum → 3 booleans). 1 schema field addition (`tiebreak_fingerprint: int`). 1 schema field replacement (`nsga2_objective_count_warning: bool` → `resolved_objective_count: int`). 8 new backlog items (1 cross-component, 1 C11a-side, 5 C11b-side, 1 follow-on; B-C11B-DOERR-TIEBREAK is the notable literature finding). 0 new subsystems (cap held at 10 across all walks).

**Partition sentinel update (v0.6)**: NO new config fields at v0.6. Partition sentinel baseline UNCHANGED from v0.5. (`tiebreak_fingerprint` is on `RefinedCandidate`, not `LocalRefinementConfig`.)

---

## § 0.1c — v0.6 → v0.7 delta summary (Walk #6 PATCH-NOW)

| Change ID | Section | Scope | Type |
|---|---|---|---|
| **W6-1 (Item 1)** | § 2.1 (Schema), § 0.3.1 | `RefinedCandidate.__post_init__` HARD-asserts the 3-flag equality invariant (was test-only at v0.6). Helper constructor `RefinedCandidate.from_operator_class(operator, refined_parameters, ...)` is the documented construction path. New read-only property `capability_mode: Literal["PREDICATE_ONLY", "MATERIALIZED"]` derived from the flags for logging/readability. | Spec-text addition + behavior tightening |
| **W6-3 (Item 3, HIGH severity)** | § 2.1, § 0.7.1, § 2.2 (Config) | `TIEBREAK_FINGERPRINT_SCHEMA_VERSION: Final[int] = 1` constant added. `tiebreak_fingerprint` derivation explicitly includes this version. `EnvironmentFingerprint.tiebreak_fingerprint_schema_version: int` field added (cache_relevant=True via fingerprint composition). Version-bump rule documented (any change to canonical_serialize semantics that affects tie-break OR deliberate fingerprint-derivation change increments this version). | Spec-text addition (correctness; closes a high-severity replay drift hole) |
| **W6-4 (Item 4)** | § 0.7.2 (NEW v0.7) | TIER-3 minimum semantics frozen: paired Wilcoxon signed-rank, ≥30 paired benchmark runs, two-tailed p > 0.05, hypervolume normalized via reference-point = max+1 per objective, benchmark corpus version-anchored. Implementation still deferred to B-NEW-W; semantics no longer free to drift. | Spec-text addition |
| **W6-6 (Item 6)** | § 0.3 (Input artifact resolution) | `get_primary_application_result(mtc: MutatedTopologyCandidate) -> MutationApplicationResult` accessor + `PrimaryApplicationResult: TypeAlias = MutationApplicationResult`. C11b code uses the accessor; direct `mtc.application_results[0]` becomes code-review violation pattern. | Spec-text addition |
| **W6-8 (Item 8)** | § 6 (Tests), § 0.3.4 | Replaced doc-presence meta-test for SemVer table with `SEMVER_POLICY_VERSION: Final[int] = 1` constant assertion. Test checks the constant; spec text can refactor without breaking. | Spec-text correction |
| **W6-15 (Item 15)** | § 0.0c (NEW v0.7) | Explicit product-relevance audit of replay guarantees, declaring 6 PRODUCT-CRITICAL + 2 OPERATIONAL + 1 RESEARCH/DEBUG surface. Resolves the "replay infrastructure dominates optimization" architectural concern with a documented framework. | Spec-text addition |

**v0.7 backlog-text amendments (no new items, sharper triggers/scope):**

| Item | Backlog ID | Amendment |
|---|---|---|
| W6-5 | B-C11B-DOERR-TIEBREAK | Append: Doerr 2024 frequency-counting assumes discrete-valued objectives; continuous floats reduce frequency-counting to ~all-1 buckets. Adoption requires continuous-objective adaptation research (epsilon-clustering or density estimation) + empirical validation BEFORE replacing v1 tie-break |
| W6-13 | B-C11B-HYPERVOLUME-WARN | Append: Hypervolume is sensitive to reference-point + normalization + objective scaling. Backlog item must freeze normalization policy + benchmark corpus BEFORE warning fires in production |
| W6-10 | B-C11B-TIMEOUT-V2 | Append: scope extended to include intra-generation watchdog hooks (candidate-evaluation checkpoints, evaluator soft deadlines, heartbeat timestamps) |
| W6-9 | B-C11B-CACHE-TIERS | Trigger tightened: "when cache hit rate drops below 50% in experimentation runs" (was vague "when measured cache hit rates collapse") |

**v0.7 new backlog item:**

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-C11B-TIER2-SCALING** (NEW v0.7) | O(N²) dominance check in TIER-2 replay validation becomes a CI bottleneck at large populations (N≥1000). Scope: hash normalized dominance matrices, compare front-adjacency signatures, Pareto layer DAG fingerprints. Literature reference: Bashir 2025 arxiv 2508.20689 ND-trees for ≥3 objectives | When CI TIER-2 wall-clock > 5min per replay batch OR when population sizes exceed 500 | M |

**v0.7 promotion list (already-documented items, now priority-elevated):**

- **B-C11B-COMPLEXITY-BUDGET-V2** (W6-7) → MANDATORY: every future walk reports weighted complexity metric in § 14.1 convergence table
- **B-C11B-PROVENANCE-SPLIT** (W6-11) → HIGH priority: trigger criterion tightened to "any change requiring c11b_version bump"
- **B-NEW-Z** (W6-12, deterministic-parallel-NSGA-II) → cross-referenced explicitly in § 0.7.1 as the candidate_index parallel-replacement path
- **B-C11B-SPEC-SPLIT-V2** (W6-14) → HIGH priority: § 0.0d "current surface only" digest is the interim mitigation

**Net at v0.7**: 29 invariants (unchanged; Inv 29 wording carries from v0.6 + new § 0.7.2 freezing TIER-3 minimum semantics). 1 new schema field (`EnvironmentFingerprint.tiebreak_fingerprint_schema_version: int`). 1 new module-level constant (`TIEBREAK_FINGERPRINT_SCHEMA_VERSION: Final[int] = 1`). 1 new accessor function (`get_primary_application_result`). 1 new type alias (`PrimaryApplicationResult`). 1 new helper constructor (`RefinedCandidate.from_operator_class`). 1 new derived property (`capability_mode`). 1 new SemVer constant (`SEMVER_POLICY_VERSION: Final[int] = 1`). 1 new backlog item (`B-C11B-TIER2-SCALING`). 4 backlog text amendments. 4 backlog priority promotions. 0 new subsystems (cap held at 10 across 6 walks).

**Partition sentinel update (v0.7)**: NO new `LocalRefinementConfig` fields at v0.7. Partition sentinel baseline UNCHANGED from v0.5/v0.6. (`tiebreak_fingerprint_schema_version` is on `EnvironmentFingerprint`, not `LocalRefinementConfig`.)

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

### § 0.3.1 — Worked example: resolution by operator class (REVISED v0.6 for capability flags)

The table now carries the v0.6 capability flags (W5-5) replacing the v0.5 `mutation_semantics` enum. `gm` = `geometry_materialized`, `ps` = `placement_safe`, `rtr` = `requires_transform_resolution`.

| Operator | Tier | C11a `output_candidate` populated? | C11b reads | gm | ps | rtr | Notes |
|---|---|---|---|---|---|---|---|
| M0_BASE (single-floor) | SHALLOW | Yes (source itself, per S41 fix) | `result.output_candidate` (= source) | True | True | False | Identity mutation; refines unchanged source |
| M0_BASE (multi-floor) | SHALLOW | Yes (wrapper itself) | `result.output_candidate` (= wrapper) | True | True | False | **Rejected at v1 via D-MF-1** |
| M1_HORIZ_FLIP, M2_VERT_FLIP | SHALLOW | None (Tier A predicate-only) | `mtc.source_candidate` | False | False | True | Refine the unflipped source; flip materialization is C12's job |
| M3a-c (staircase), M4 (corridor), M5 (zone) | SHALLOW | None | `mtc.source_candidate` | False | False | True | Same as M1/M2 |
| M9a-d (entry) | SHALLOW | None | `mtc.source_candidate` | False | False | True | Same as M1/M2 |
| M6_WET_ROTATE | REGENERATIVE | Yes (rotated WZPC from deep pipeline) | `result.output_candidate` | True | True | False | Tier B; new geometry materialized |
| M7A_GRID_3_3, M7B_GRID_2_7 | REGENERATIVE | Yes (regridded WZPC from deep pipeline) | `result.output_candidate` | True | True | False | Tier B; new geometry materialized |
| M8_VERT_REARR (multi-floor only) | REGENERATIVE | Yes (rewrapped MFWZPC after C9+C10 cascade) | `result.output_candidate` | True | True | False | **Rejected at v1 via D-MF-1** |

**Three-flag invariant at v1 (REVISED v0.7 W6-1 to HARD assertion)**: `placement_safe == geometry_materialized` AND `requires_transform_resolution == NOT geometry_materialized`. At v0.6 this was test-only; **v0.7 W6-1 enforces it via `RefinedCandidate.__post_init__` raising `InvariantViolationError`** if the equality is violated. The three booleans encode 2 effective states (Tier A vs Tier B/M0) at v1; the hard assertion prevents future contributors from manually constructing invalid combinations.

**Helper constructor (NEW v0.7 W6-1)**: `RefinedCandidate.from_operator_class(operator_class: OperatorClass, refined_parameters: RefinedParameters, ...)` is the documented construction path. The helper derives the capability flags from the operator class via the worked-example table above; direct construction of the flags is technically allowed but discouraged (and `__post_init__` will catch invalid combos).

**Derived property (NEW v0.7 W6-1)**: `RefinedCandidate.capability_mode -> Literal["PREDICATE_ONLY", "MATERIALIZED"]` is a read-only property derived from the flags (returns "PREDICATE_ONLY" iff NOT `geometry_materialized`). Provided for logging, debug output, and downstream consumers who want a compact label. Not stored in the dataclass (just a `@property` method).

**Future evolution path**: When future operators break the v1 equality (e.g., a placement-aware Tier A operator with `placement_safe=True AND geometry_materialized=False`), the `__post_init__` assertion AND the `capability_mode` property AND the `from_operator_class` helper all must be revised together. This is part of the schema-evolution discipline: invariants migrate as a unit.

**Reading the table**: For Tier A SHALLOW ops M1-M5, M9 — which are the bulk of C11a output — C11b refines `source_candidate` directly. This is correct because Tier A operators *don't actually mutate geometry*; they emit verdicts that the source is valid under that operator's transformation. C11b's job is to refine room dimensions of the validated topology, and the topology is the source.

For Tier B and M0, `output_candidate` is the artifact to refine — for M6/M7 the regenerated WZPC, for M0 the source itself.

### § 0.3.2 — Resolver assumes `len(application_results) == 1` (NEW v0.5 Item 8 doc, TIGHTENED v0.6 W5-13/Item 13)

The v0.4 resolver `_resolve_input_artifact` raises `EvaluatorContractError` if `len(mtc.application_results) != 1`. This enforces a C11a v1 convention but the underlying type signature remains misleading.

**Architectural debt explicitly acknowledged (v0.6 tightened with code-grep verification)**:

- `application_results: tuple[MutationApplicationResult, ...]` is typed as a tuple (plural cardinality).
- C11a's `MutatedTopologyCandidate.__post_init__` enforces `len == 1` at construction time (verified via grep on `buildemup/components/c11a/provenance.py` line 122 — raises if violated). So the runtime contract is solid; the **type signature alone** is dishonest.
- A future C11a amendment introducing batched/composite mutations would break the v1 resolver at runtime AND require C11a's `__post_init__` rule to relax. Both changes ship together or neither ships.

**v0.6 takes no behavior change** — the defensive raise is correct for v1. Two backlog items address the cleanup:

> **B-C11B-RESOLVER-V2** (v0.5 carry): C11b-side resolver cleanup. When (if) C11a introduces multi-application MTCs, replace `application_results: tuple[...]` with `primary_application_result: MutationApplicationResult` (singleton) + `secondary_results: tuple[...]` (optional batch). C11b reads `primary_application_result` unambiguously. Trigger: C11a multi-result mutation feature lands. Effort: M.

> **B-C11A-MTC-SINGLETON** (NEW v0.6 W5-13): C11a-side schema fix. Amend `MutatedTopologyCandidate` to expose `primary_application_result: MutationApplicationResult` as a singleton field (the type-honest version of the v1 contract), with `extra_application_results: tuple[MutationApplicationResult, ...] = ()` as the optional batch-expansion surface. This makes the v1 "one application result" contract type-safe instead of comment-enforced. Trigger: any time C11a v1.6 LOCKED takes a non-trivial amendment (e.g., for performance, new operators, or batching). Effort: S. Risk: TOUCHES C11a v1.6 LOCKED — requires explicit Ramalingam LOCK adjudication for the C11a amendment.

**Why v0.6 doesn't force the fix now**: B-C11A-MTC-SINGLETON would amend a LOCKED upstream spec. Per Rule 8, that's Ramalingam's call to authorize. v0.6 stays within C11b boundaries and files the C11a-side cleanup as a paired backlog item for future scheduling.

**v0.7 W6-6 mitigation — typed accessor before C11a amendment lands**: v0.7 adds a typed accessor at the C11b boundary that wraps the brittle tuple access:

```python
# In c11b/input_resolution.py (NEW v0.7 W6-6):
from typing import TypeAlias
from buildemup.components.c11a.provenance import MutationApplicationResult

PrimaryApplicationResult: TypeAlias = MutationApplicationResult
"""Type alias documenting that v1 MTC carries exactly one
application result (per C11a __post_init__ assertion).
Once B-C11A-MTC-SINGLETON ships, this alias points to the
type-honest singleton field."""

def get_primary_application_result(
    mtc: MutatedTopologyCandidate,
) -> PrimaryApplicationResult:
    """Typed accessor for the single application result on an MTC at
    v1. Wraps the tuple-indexing brittleness that B-C11A-MTC-SINGLETON
    will eventually eliminate.

    Raises EvaluatorContractError if the MTC violates the singleton
    contract (defensive — mirrors C11a's __post_init__ enforcement).
    """
    if len(mtc.application_results) != 1:
        raise EvaluatorContractError(
            f"C11b: MutatedTopologyCandidate must carry exactly one "
            f"application result at v1; got "
            f"{len(mtc.application_results)}. See B-C11A-MTC-SINGLETON."
        )
    return mtc.application_results[0]
```

**Discipline (NEW v0.7 W6-6)**: All C11b code accessing the application result MUST use `get_primary_application_result(mtc)` rather than `mtc.application_results[0]`. Direct indexing becomes a code-review violation pattern (lint rule candidate). Existing v0.6 `_resolve_input_artifact` is refactored to call the accessor.

### § 0.3.3 — v1.0 → v1.1 migration semantics (NEW v0.5 Item 20)

v0.4 bumped `C11B_VERSION` from "v1.0" to "v1.1" (F-v4-6 PATCH-NOW) to reflect schema growth. v0.5 carries this unchanged but documents the migration semantics explicitly:

- **Caches keyed by `EnvironmentFingerprint`**: any cached refinement output captured under `c11b_version="v1.0"` deserializes-miss under "v1.1" (cache key mismatch). No in-place migration is attempted; old cache entries become unreachable and are GC'd by normal eviction.
- **No persistent state requires migration tools**: C11b's outputs are read by C12 placement layer at runtime; they are not stored as a long-term durable artifact at v1. If a future component (C13 archive? C16 portfolio?) starts persisting C11b outputs across versions, that component owns the migration logic.
- **Provenance compatibility**: `LocalRefinementProvenance` v1.1 carries strictly more fields than v1.0 (the v0.4 + v0.5 additions). Code reading old provenance from logs should default missing fields to None/empty (lenient read), not raise.

### § 0.3.4 — `C11B_VERSION` SemVer rules (NEW v0.6 W5-19 / Item 19)

v0.5 documented v1.0 → v1.1 migration but didn't define when to bump which part of `C11B_VERSION`. v0.6 closes this:

| Change kind | Version bump | Rationale |
|---|---|---|
| Removing or renaming an invariant; removing a public type / field | **MAJOR** (v1.1 → v2.0) | Breaks downstream consumers that asserted the removed surface |
| Adding a new invariant; adding a public failure-mode type; renaming a config field's `cache_relevant` from True to False (loosens cache discipline) | **MINOR** (v1.1 → v1.2) | Backwards-compatible expansion; cache continues to validate older inputs since stricter keys still match |
| Renaming a config field's `cache_relevant` from False to True (tightens cache discipline); changing a default value that affects output identity; adding a new `cache_relevant=True` config field | **MINOR** (v1.1 → v1.2) | Backwards-compatible from contract perspective, but invalidates older caches via fingerprint mismatch |
| Adding telemetry / provenance fields; adding new value to a Literal[...] enum on a non-cache-relevant field; clarifying invariant wording without changing semantics | **PATCH** (v1.1 → v1.1.1) | Cache continues to validate; no consumer breaks |
| Bug-fix that changes output identity for the same input (e.g., the v0.5 W4-4/W4-5 cache_relevant correctness fixes) | **MINOR** (v1.1 → v1.2) | Old caches were producing wrong-keyed entries; new version intentionally invalidates them |

**v0.6 specifically**: v0.6 introduces no MAJOR changes. The capability-flag replacement (W5-5) is a schema CHANGE (removing `mutation_semantics`), which under the table above is MAJOR. **However**, v0.5 was PROPOSED, not LOCKED, when v0.6 supersedes it; therefore no actual cache or consumer exists yet, and the "MAJOR" bump is theoretical. v0.6 keeps `C11B_VERSION = "v1.1"` (carried from v0.4 PATCH-NOW). If v0.6 LOCKS, the *first* LOCK after v1.0 LOCKED (S37, SUSPENDED) becomes v1.1.

**Future bump policy**: After v0.6 LOCK (if granted), apply this table going forward. Any schema-removing change post-LOCK requires MAJOR bump. Any cache-key-affecting change requires at least MINOR.

**v0.7 W6-8 — machine-readable policy version**: To replace the v0.6 meta-test ("SemVer table exists in § 0.3.4"), v0.7 adds:

```python
# In c11b/versioning.py (NEW v0.7 W6-8):
SEMVER_POLICY_VERSION: Final[int] = 1
"""Version of the SemVer policy documented in spec § 0.3.4.
Increment when the bump-criteria table itself changes meaning.
Test assertion: `SEMVER_POLICY_VERSION >= 1` and matches the
spec-referenced value.

v0.7 W6-8 motivation: replace fragile doc-presence test
('SemVer table exists in §0.3.4') with constant-presence test.
Documentation can refactor without breaking CI."""
```

Test discipline (NEW v0.7 W6-8): the v0.6 test "SemVer table exists in § 0.3.4" is removed and replaced with `assert versioning.SEMVER_POLICY_VERSION == 1`. The constant value is the contract; documentation prose is documentation.

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
        metadata={"cache_relevant": True},   # v0.5 PATCH-NOW (Item 5):
                                              # timeout CAN truncate output mid-run;
                                              # truncated outputs differ from full
                                              # outputs, so cache key must include
                                              # this. v0.4 had False; corrected.
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

**Invariant 29 (NEW v0.4, REVISED v0.5 Item 11, REVISED v0.6 W5-1 + W5-10)**: PRNG seed derivation is pure-deterministic. Replay equivalence is specified as three explicit tiers (NEW v0.6 W5-1 nomenclature):

**TIER-1 — Byte-equal Pareto fronts**. Holds as a CONJUNCTION of:
  - same `master_seed`, `topology_index`, `topology_signature`
  - same CI-validated environment tuple (numpy_version, BLAS, platform_machine, platform_system, `c11b_version`) per `EnvironmentFingerprint`
  - deterministic tie-break rule applied (per § 0.7.1 below)

Replay tests asserting TIER-1 require all three conditions; missing any one drops to TIER-2.

**TIER-2 — Structurally-equivalent Pareto fronts**. Holds when the seed/env/tie-break conjunction is partial (e.g., different BLAS but same algorithm + seed). Asserted as a CONJUNCTION of three conditions (v0.6 W5-10 strengthening — previously v0.5 was numeric-only):
  - **Same Pareto rank cardinality per front**: `len(front_k_runA) == len(front_k_runB)` for each rank `k`
  - **Same dominance relations across the front**: for every pair `(a, b)` in the union of both runs' candidates, `a dominates b in run A iff a dominates b in run B`
  - **Numeric tolerance**: `1e-9` absolute on objective values; same objective-vector mapping (same keys, same ordering)

The conjunction prevents cumulative floating-point drift over many generations from being silently masked as "structurally equivalent" while the actual dominance topology has shifted (v0.5 numeric-only tolerance had this hole).

**TIER-3 — Statistically-equivalent Pareto fronts**. Holds across CI-incompatible environments (cross-platform, different NumPy major version). Asserted via paired hypervolume comparison (Wilcoxon signed-rank, p > 0.05) over a benchmark population. **Deferred to B-NEW-W (C11b hypervolume diversity metric)** — requires hypervolume computation infrastructure not present at v1. TIER-3 tests will land alongside B-NEW-W.

`topology_signature`: Reuse C11a's `derive_canonical_signature(input_artifact)` output (16-hex SHA256 prefix). For multi-floor wrappers this would aggregate per-floor signatures; v1 doesn't see multi-floor inputs (per D-MF-1), so the signature is the single-floor structural hash.

**Per-replay assertion**: Phase 0 captures `master_seed` into `EnvironmentFingerprint`. TIER-1 tests assert byte-equality. TIER-2 tests assert the three-condition conjunction. TIER-3 tests are deferred per B-NEW-W trigger.

### § 0.7.1 — Deterministic tie-break rule (NEW v0.5 Item 6, REVISED v0.6 W5-12)

NSGA-II's survival selection picks individuals first by Pareto rank, then by crowding distance descending. When candidates tie on BOTH (e.g., extreme points get `crowding_distance = +inf` and there are multiple), the algorithm's behavior depends on implementation. v0.5 specified the rule explicitly; v0.6 W5-12 optimizes layer 2 from per-sort `canonical_serialize` to a precomputed integer fingerprint.

**Rule**: Within an equivalence class of (rank, crowding_distance) ties, candidates are ordered by lex-ASC composite key:
```python
def _tiebreak_key(candidate: RefinedCandidate, candidate_index: int) -> tuple:
    """Lex-ASC tie-break for NSGA-II survivor selection per Inv 29.

    Composite key:
      1. topology_signature (deterministic from source artifact)
      2. tiebreak_fingerprint (precomputed 64-bit int per v0.6 W5-12;
         was canonical_serialize hash per v0.5, now precomputed once
         at RefinedCandidate.__post_init__ to avoid O(N²) hash work)
      3. candidate_index (insertion order in the current population)

    Layer 1 isolates ties to within-topology cases (most common at v1
    since C11b is per-topology). Layer 2 disambiguates near-identical
    candidates with different parameter vectors via the precomputed
    fingerprint. Layer 3 is the final fallback when even parameters
    tie (e.g., M0 identity copies).

    v0.6 performance note: layer 2 reads `candidate.tiebreak_fingerprint`
    (int compare, O(1) per pair) instead of computing
    `hashlib.sha256(canonical_serialize(...))` at sort time
    (O(serialization + hashing) per pair). For N=100 population this
    saves ~9,900 redundant hash operations per generation.
    """
    return (
        candidate.source_topology_candidate_signature,  # exposed via § 2.1
        candidate.tiebreak_fingerprint,                  # precomputed v0.6 W5-12
        candidate_index,
    )
```

**`tiebreak_fingerprint` derivation** (REVISED v0.7 W6-3 for version safety; computed once at `RefinedCandidate.__post_init__`):

```python
# Module-level constant in c11b/tiebreak.py (NEW v0.7 W6-3):
TIEBREAK_FINGERPRINT_SCHEMA_VERSION: Final[int] = 1
"""Bump rule (must be documented in commit message):
  - Increment when canonical_serialize semantics change in a way that
    affects RefinedParameters serialization (float precision change,
    field ordering change, normalization rule change, etc.).
  - Increment when the derivation function below changes (different
    hash, different byte count, different mixing).
  - Do NOT increment for non-affecting changes elsewhere in the codebase.

The version is captured into `EnvironmentFingerprint.tiebreak_fingerprint_schema_version: int`
so cache keys observe it directly. A cache entry computed under
version=1 deserializes-miss under version=2.
"""

def _compute_tiebreak_fingerprint(refined_parameters: RefinedParameters) -> int:
    """64-bit big-endian int from first 8 bytes of
    sha256(VERSION + canonical_serialize(refined_parameters)).

    v0.7 W6-3 change: the schema version is prepended to the payload
    before hashing. This makes the fingerprint explicitly dependent on
    the version, so changing canonical_serialize semantics WITHOUT
    bumping the version produces detectably different fingerprints
    (which then cache-miss correctly via EnvironmentFingerprint).

    Without this version-anchor (v0.6 behavior), a silent
    canonical_serialize change in any upstream component (e.g., C7
    changing float precision) would produce different fingerprints
    AT THE SAME c11b_version, silently corrupting cache integrity.
    """
    versioned_payload = (
        f"{TIEBREAK_FINGERPRINT_SCHEMA_VERSION}|"
        + canonical_serialize(refined_parameters)
    ).encode("utf-8")
    return int.from_bytes(
        hashlib.sha256(versioned_payload).digest()[:8],
        byteorder="big",
    )
```

**Cache-key composition (NEW v0.7 W6-3)**: `EnvironmentFingerprint` gains a new field `tiebreak_fingerprint_schema_version: int` that captures `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` at run time. Cache lookup uses the full fingerprint including this field; runs under version=1 cannot collide with runs under version=2 even if everything else (master_seed, c11b_version, NumPy version) is identical.

**Why this is high severity (despite the small spec change)**: at v0.6 a contributor amending C7 or C11a to change `CANONICAL_FP_PRECISION` (currently 6, in `buildemup/utilities/canonical.py`) for a legitimate reason would NOT bump `c11b_version` (because C11b code didn't change). All existing C11b cache entries would silently produce different `tiebreak_fingerprint` values, leading to wrong-keyed cache entries (same key, different content). This is a stealth correctness bug that the v0.6 spec hadn't surfaced. The W6-3 patch is the minimum-cost fix.

**Applied at**: NSGA-II survivor selection (after crowding-distance assignment) and Pareto-front membership assignment when multiple candidates have identical objective vectors.

**Test discipline**: 1 dedicated test asserts that two populations with intentionally tied candidates produce identical survivor sets across runs (TIER-1 byte-equal). 1 dedicated test asserts that swapping `candidate_index` (i.e., feeding the population in a different order) produces a DIFFERENT survivor set when ties exist — this proves the tie-break is reachable and order-sensitive, not silently disambiguated by upstream operations. 1 NEW v0.6 test asserts that `tiebreak_fingerprint` is deterministic across runs (same refined_parameters → same int) and that the sort uses the precomputed value rather than recomputing. 1 NEW v0.7 test asserts `tiebreak_fingerprint` includes `TIEBREAK_FINGERPRINT_SCHEMA_VERSION`: bumping the version while keeping `refined_parameters` identical produces a DIFFERENT fingerprint.

**Cross-reference to B-NEW-Z (W6-12, candidate_index parallel-unsafety)**: layer 3 (`candidate_index`) is insertion-order-sensitive by design at v1. Single-threaded NSGA-II at v1 has stable insertion order; future parallel-NSGA-II (B-NEW-Z) must replace `candidate_index` with a deterministic order-invariant fallback (candidate UUID, structural hash, or ancestry lineage id). v0.7 does not change layer 3 at v1.

### § 0.7.2 — TIER-3 minimum semantics (NEW v0.7 W6-4)

v0.6 deferred TIER-3 (statistically-equivalent Pareto fronts) to B-NEW-W, with "paired Wilcoxon hypervolume comparison" as the only specified mechanism. v0.7 W6-4 freezes additional minimum semantics now so that future TIER-3 implementations cannot fragment:

**Frozen at v0.7**:

| Aspect | Frozen value | Rationale |
|---|---|---|
| Statistical test | Paired Wilcoxon signed-rank, two-tailed | Non-parametric, paired-sample appropriate for hypervolume comparison; standard in EA literature |
| Minimum paired benchmark runs | 30 | Standard sample size for non-parametric tests; gives reasonable statistical power |
| Significance threshold | p > 0.05 (i.e., NOT rejecting null = "statistically equivalent") | TIER-3 asserts EQUIVALENCE, not difference; failing to reject null is the equivalence claim |
| Hypervolume normalization | Reference-point = (max observed in each objective across both compared runs) + 1.0 absolute offset | Reference-point sensitivity is a known hypervolume hazard; freezing the rule prevents drift across TIER-3 implementations |
| Benchmark corpus version-anchor | `TIER3_BENCHMARK_CORPUS_VERSION: Final[int]` constant (to be defined in v1 release notes) | Different corpora produce different results; version-anchor required |
| Confidence interval reporting | 95% CI on the median hypervolume difference, alongside p-value | Single p-value is fragile; CI shows effect size |

**Deferred to B-NEW-W**:

| Aspect | When defined |
|---|---|
| Hypervolume computation implementation | B-NEW-W spec arc |
| Benchmark corpus contents | B-NEW-W spec arc |
| TIER-3 test integration with CI matrix | B-237 + B-NEW-W intersection |

**Why freeze minimum semantics without implementing**: v0.7 prevents the scenario where Walk #N+1 implements TIER-3 in one way, then Walk #N+2 reimplements it differently because the spec left too much room. Freezing what CAN be frozen now reduces future spec fragmentation risk.

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
| **G-S41-4 (D-NSGA-1)** | `StubEvaluator.objectives` defaults to 3 (carries v0.3 LOCKED behavior); 2-objective mode added as configurable knob. B-NEW-V5 widened with NSGA-III migration trigger | v0.4 self-analysis + web research (Doerr 2022) |
| **G-S41-5 (D-EV-1)** | Per-candidate evaluator failures skip-and-continue up to `pop_size * config.evaluator_skip_cap_fraction` (default 0.25); beyond that upgrade to systemic. v0.5 PATCH-NOW: skip cap field is `cache_relevant=True` (Item 4). | v0.4 self-analysis + v0.5 W4 |
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

### § 2.1 — Schema additions (v0.4 over v1.0; v0.5 additions appended)

**v0.4 additions:**

- `MultiFloorRefinementNotSupportedError(PerTopologyError)` — NEW v0.4
- `PerTopologyTimeoutError(PerTopologyError)` — NEW v0.4
- `StubEvaluatorConfig` dataclass + `objectives: Literal[2, 3] = 3` field — NEW v0.4 (default 3 carries v0.3 LOCKED behavior; v0.5 W4-1 corrects stale draft inconsistency)
- `derive_per_topology_seed(master_seed, topology_index, topology_signature) -> int` — NEW v0.4

**v0.5 additions (Walk #4 telemetry/doc patches):**

```python
@dataclass(frozen=True)
class RefinedCandidate:
    # ... all v1.0 + v0.4 fields carried ...

    # v0.6 W5-5 (Item 5) replacement: mutation_semantics enum dropped;
    # three capability flags carry the same information with cleaner
    # extension surface. Future capabilities (e.g., partial materialization)
    # become a 4th flag, not a tri-state enum that breaks consumers.
    geometry_materialized: bool                        # NEW v0.6 (W5-5)
    """True iff the refinement input artifact carries geometrically
    materialized rooms (not just a predicate verdict). Derived from
    C11a operator metadata at refinement time:
      - Tier A SHALLOW (M1-M5, M9) -> False (predicate only)
      - Tier B REGENERATIVE (M6, M7) -> True
      - M8 multi-floor (rejected at v1) -> N/A
      - M0_BASE single-floor or multi-floor -> True (identity counts
        as materialized — output_candidate IS the source geometry).
    """
    placement_safe: bool                                # NEW v0.6 (W5-5)
    """True iff downstream placement (C12) may consume the refined
    parameters as final positions without further transform
    resolution. At v1, True iff `geometry_materialized` is True;
    future placement-aware operators may decouple these.
    """
    requires_transform_resolution: bool                 # NEW v0.6 (W5-5)
    """True iff a downstream consumer must apply the source
    operator's geometric transform (e.g., M1 horizontal flip)
    before treating the parameters as final geometry. At v1,
    True iff `geometry_materialized` is False (Tier A SHALLOW
    operators imply a pending transform; Tier B + M0 carry
    materialized geometry directly).
    """

    # v0.6 W5-12 (Item 12) addition: precomputed tie-break fingerprint
    # for O(N) precompute + O(N²) integer compares vs the v0.5
    # O(N²) canonical_serialize hash work. Computed in __post_init__
    # using the same content as the v0.5 tie-break layer 2 hash, but
    # truncated to a 64-bit int for fast comparison.
    tiebreak_fingerprint: int                           # NEW v0.6 (W5-12)
    """64-bit integer fingerprint over canonical_serialize(refined_parameters),
    precomputed once at RefinedCandidate construction. Used by NSGA-II
    survivor selection's tie-break (§ 0.7.1 layer 2) to avoid repeated
    serialization+hashing per comparison. Derivation:
        sha256(canonical_serialize(refined_parameters))[:8] as big-endian int.
    Stable across runs that produce identical refined_parameters.
    """

    source_topology_candidate_signature: str           # NEW v0.5 (Item 6 support)
    """16-hex SHA256 prefix from C11a's
    derive_canonical_signature(input_artifact). Exposed at this level
    so the tie-break rule in § 0.7.1 can read it without reaching
    into the upstream MTC."""


@dataclass(frozen=True)
class PerTopologyTelemetry:                            # NEW v0.5
    """Per-topology diagnostic block in LocalRefinementProvenance."""
    topology_index: int
    completed_generations: int
    longest_generation_seconds: float                  # NEW v0.5 (Item 3)
    """Wall-clock duration of the slowest generation within this
    topology. Surfaces tail-latency stragglers that approached but
    didn't breach per_topology_wallclock_seconds."""
    skipped_candidates_total: int
    """Sum of per-generation skip counts (Inv 28) for this topology."""


@dataclass(frozen=True)
class LocalRefinementProvenance:
    # ... all v1.0 + v0.4 fields carried ...
    skipped_multifloor_count: int                      # NEW v0.5 (Item 1)
    """Number of input MutatedTopologyCandidates rejected as
    multi-floor at v1. Diagnostic-only; downstream code may treat a
    non-zero value as a signal that multi-floor refinement (B-C11B-MF)
    should be prioritized."""
    resolved_objective_count: int                      # NEW v0.6 (W5-18, was v0.5 bool)
    """The objective count actually used by the configured evaluator
    during this batch (StubEvaluator at v1 returns 2 or 3 depending
    on `StubEvaluatorConfig.objectives`; future production C14 may
    return arbitrary count).

    v0.6 supersedes v0.5's `nsga2_objective_count_warning: bool` which
    was always True at v1 (default StubEvaluator objectives=3 → flag
    always set), creating alert fatigue. Operators now read the
    actual count and apply their own NSGA-II 3-objective gating
    logic.

    NSGA-II's documented many-objective limitation (Doerr 2022)
    applies at count >= 3. The hypervolume-regression-based warning
    (operationally correct semantics) is filed as
    B-C11B-HYPERVOLUME-WARN — requires hypervolume computation
    infrastructure not present at v1.
    """
    per_topology_telemetry: tuple[PerTopologyTelemetry, ...]  # NEW v0.5
    """One entry per input topology, in input order. Populated at
    `ProvenanceVerbosity.PER_GEN` or higher (matches v1.0 carried
    verbosity tiers); empty tuple at lower verbosity. F-v5-6 PATCH-NOW
    corrected naming: v0.5 draft initially said PER_TOPOLOGY (which
    isn't a v1.0 enum member)."""
```

### § 2.2 — Configuration (additions over v1.0; REVISED v0.5)

```python
@dataclass(frozen=True)
class LocalRefinementConfig:
    # ... all v1.0 fields carried ...
    per_topology_wallclock_seconds: float = field(   # NEW v0.4
        default=30.0,
        metadata={"cache_relevant": True},   # v0.5 PATCH-NOW (Item 5):
                                              # timeout-truncated outputs differ
                                              # from completed; must be in cache key.
    )
    master_seed: int = field(                          # NEW v0.4
        default=0xC11B5EED,
        metadata={"cache_relevant": True},
    )
    evaluator_skip_cap_fraction: float = field(        # NEW v0.4 — Inv 28 knob
        default=0.25,
        metadata={"cache_relevant": True},   # v0.5 PATCH-NOW (Item 4):
                                              # different caps -> different surviving
                                              # populations -> different Pareto
                                              # fronts; must be in cache key.
    )
```

**Partition sentinel impact (v0.5 — REVISED Item 4 + Item 5)**: C11b inherits C11a's cache-relevant-field partition-sentinel test pattern (analogue to C11a's `test_config_cache_relevant_partition_six_six`). v0.5 changes the partition versus v0.4:

| v1.0 baseline | v0.4 added | v0.5 (PATCH-NOW from v0.4) |
|---|---|---|
| (carried from v1.0; N relevant + M irrelevant) | +1 relevant (master_seed); +2 irrelevant (wallclock, skip_cap_fraction) | +3 relevant (master_seed, wallclock, skip_cap_fraction); +0 irrelevant |

The partition-sentinel test for C11b's `LocalRefinementConfig` must be authored against the v0.5 counts. The v0.4 → v0.5 flip (W4-4 + W4-5) shifts 2 fields from irrelevant to relevant.

---

## § 3 — Behaviour (REVISED v0.4)

### Phase 0 — Input + startup validation

Carried v1.0 + 2 additions:
- Capture `master_seed` into `EnvironmentFingerprint.master_seed: int` (NEW v0.4 field). Replay-tier tests can detect master-seed changes via fingerprint mismatch.
- Capture `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` into `EnvironmentFingerprint.tiebreak_fingerprint_schema_version: int` (NEW v0.7 W6-3 field). Cache lookup includes this field; runs under version=1 cannot collide with runs under version=2 even if everything else matches. Closes the v0.6 stealth-drift hole where a canonical_serialize semantics change in any upstream component would silently corrupt cache integrity at the same `c11b_version`.

### § 3.0 — Per-topology input artifact resolution (NEW v0.4)

Per § 0.3: `_resolve_input_artifact(mtc)` returns `mtc.application_results[0].output_candidate` when non-None, else `mtc.source_candidate`. This is the ONLY path for reading the input artifact in Phase 1 (Inv 26).

### Phase 1 — Per-topology NSGA-II run (REVISED v0.4, REVISED v0.5 Item 9)

Carried v1.0 with v0.4 + v0.5 additions. **The step ordering is significant** (Item 9 PATCH-NOW v0.5): cheap rejection happens before expensive setup, so a batch with many multi-floor inputs doesn't burn signature-derivation work before getting filtered:

1. **Resolve input artifact** via § 3.0. Cheap; reads from `mtc.application_results[0]` or `mtc.source_candidate`.
2. **Reject multi-floor IMMEDIATELY** (D-MF-1): `MultiFloorRefinementNotSupportedError` if `_is_multi_floor_artifact(input_artifact)`. **NO signature derivation, NO PRNG construction, NO evaluator init has happened yet.** Increment `LocalRefinementProvenance.skipped_multifloor_count`.
3. **Derive `topology_signature`** via C11a's `derive_canonical_signature(input_artifact)`. Cached as `RefinedCandidate.source_topology_candidate_signature` for tie-break in § 0.7.1.
4. **Derive per-topology PRNG** via § 0.7. Uses signature from step 3.
5. **Start wall-clock timer**; raise `PerTopologyTimeoutError` if exceeded at any generation boundary.
6. **Evaluator failure isolation** per § 0.6: per-candidate skip up to `max(1, int(pop_size * config.evaluator_skip_cap_fraction))` (default fraction 0.25); beyond that, raise systemic. Track `skipped_candidates_total` for telemetry.
7. **Per-generation telemetry**: measure wall-clock duration; update `longest_generation_seconds` if new max.
8. **Resolved objective count tracking** (v0.6 W5-18): after the first generation's evaluation, set `LocalRefinementProvenance.resolved_objective_count = len(objective_vector.values)`. Operators consult the value; the v0.5 bool warning is removed (was always-True at v1, see § 0 narrative).
9. **NSGA-II survivor selection**: when Pareto rank + crowding distance ties exist, apply tie-break per § 0.7.1.
10. All other Phase 1 logic unchanged from v1.0.

### Phase 2 — Output assembly

Carried v1.0 + v0.5 + v0.6: each `RefinedCandidate` carries three capability flags `(geometry_materialized, placement_safe, requires_transform_resolution)` derived from C11a operator metadata per the worked-example table in § 0.3.1. v0.5's `mutation_semantics` enum was replaced at v0.6 (W5-5); the v0.5 single-state enum became three booleans for extension cleanliness.

### Phase 3 — Provenance assembly

Carried v1.0 + v0.4 + v0.5 populates:
- `master_seed` into provenance (v0.4)
- `per_topology_wallclock_seconds` into provenance (v0.4)
- `evaluator_skip_cap_fraction` into provenance (v0.5; was v0.4 but cache_relevant flipped)
- Per-topology timeout / skip-count counters into per-topology telemetry block (v0.4 + v0.5)
- `skipped_multifloor_count`, `resolved_objective_count` (v0.6 W5-18 supersedes v0.5 bool warning), `per_topology_telemetry` (v0.5 W4 additions, v0.6 refinement)

---

## § 4 — Invariants (REVISED v0.4)

v1.0 invariants 1-25 carried unchanged. v0.4 adds Inv 26-29:

| # | Invariant | Mode |
|---|---|---|
| 1-25 | (carried verbatim from v1.0) | as v1.0 |
| **26 (NEW v0.4)** | **Input-artifact resolver: `_resolve_input_artifact(mtc)` is the only path for reading mtc's artifact in Phase 1. Empty or multi-element `application_results` raises `EvaluatorContractError`. Direct `mtc.source_candidate` access elsewhere in Phase 1 is a programming bug (caught in code review).** | RAISE |
| **27 (NEW v0.4)** | **Per-topology wall-clock breach raises `PerTopologyTimeoutError`. Default `per_topology_wallclock_seconds=30.0`. Check at generation boundaries.** | RAISE |
| **28 (NEW v0.4)** | **Per-generation evaluator failure cap = `max(1, int(pop_size * config.evaluator_skip_cap_fraction))` (default fraction 0.25). Exceeding the cap upgrades to `EvaluatorContractError` systemic.** | RAISE |
| **29 (NEW v0.4, REVISED v0.5 Items 6 + 11, REVISED v0.6 W5-1 + W5-10)** | **PRNG seed derivation is pure-deterministic. Replay equivalence is tiered: TIER-1 byte-equal under full conjunction (seed + env tuple + tie-break). TIER-2 structurally-equivalent under partial conjunction, asserted as a 3-way conjunction (`1e-9` numeric tolerance AND same rank cardinality per front AND same dominance relations across all pairs). TIER-3 statistically-equivalent (paired-Wilcoxon hypervolume) deferred to B-NEW-W. Tie-break via precomputed `tiebreak_fingerprint` per § 0.7.1 (v0.6 W5-12 optimization).** | RAISE (replay tier) |

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

## § 6 — Test coverage targets (REVISED v0.4, REVISED v0.5, REVISED v0.6, REVISED v0.7)

Target **~230 tests at LOCK** (up from v0.6's 223; v0.7 adds 8 net minus 1 v0.6 meta-test removed and 1 absorbed = +6 net adjustments):

- ~28 schema (unchanged)
- ~30 NSGA-II core (unchanged)
- ~34 invariants (Inv 1-29; +4 at v0.4, no new at v0.5 or v0.6 — Inv 29 wording revised in place at both walks)
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
- **~12 NEW v0.5** (W4 patches):
  - 2× tie-break rule (Item 6): within-tie ordering deterministic across runs; swapping candidate_index changes survivor set when ties exist
  - 1× Inv 29 conjunction (Item 11): byte-equal only under full env-tuple match; structurally-equivalent tolerance fires on partial match
  - 2× cache_relevant flips (Items 4, 5): partition sentinel reflects new counts; different cache keys for different `evaluator_skip_cap_fraction` values; different cache keys for different `per_topology_wallclock_seconds` values
  - 1× partition sentinel re-asserted at v0.5 baseline
  - 1× `skipped_multifloor_count` telemetry populated when MF inputs rejected (Item 1 small fix)
  - 1× `mutation_semantics` field tagging (now REVISED at v0.6 — see capability flag tests below) (Item 2 small fix)
  - 1× `longest_generation_seconds` telemetry tracks slowest generation (Item 3 small fix)
  - 1× `nsga2_objective_count_warning` flag (now REVISED at v0.6 — see resolved_objective_count tests below) (Item 10 small fix)
  - 1× Phase 1 ordering: MF rejection happens BEFORE signature derivation (Item 9 — assertion that derive_canonical_signature was not called for a rejected MF input)
  - 1× StubEvaluatorConfig default consistency (Item 16): `StubEvaluatorConfig().objectives == 3` (catches the v0.4 stale-draft inconsistency)
- **~6 NEW v0.6** (W5 patches):
  - 1× capability flag derivation (W5-5): for each operator class in § 0.3.1's table, the correct `(geometry_materialized, placement_safe, requires_transform_resolution)` tuple is computed (parametrized test across operators)
  - 1× capability flag v1 equality invariant (W5-5): `placement_safe == geometry_materialized AND requires_transform_resolution == NOT geometry_materialized` holds for every emitted RefinedCandidate (NOTE: at v0.7, this becomes a hard `__post_init__` assertion test, not a separate equality check; see W6-1 below)
  - 1× TIER nomenclature (W5-1): TIER-1 test asserts byte-equal under full conjunction; TIER-2 test asserts structurally-equivalent under partial conjunction (different BLAS simulated via objective-value perturbation within 1e-9); TIER-3 is deferred to B-NEW-W
  - 1× Inv 29 TIER-2 conjunction (W5-10): TIER-2 test REJECTS replay equivalence when same numeric tolerance holds but a dominance relation flipped (proves the 3-way conjunction catches what numeric-only tolerance misses)
  - 1× `tiebreak_fingerprint` precompute determinism (W5-12): same `refined_parameters` → same fingerprint across runs; tie-break sort reads the precomputed field rather than recomputing
  - 1× `resolved_objective_count: int` populated correctly (W5-18): equals `len(objective_vector.values)` from the configured StubEvaluator; replaces v0.5's always-True bool warning
  - 1× ~~SemVer rule documentation existence (W5-19): test that the SemVer table is documented in § 0.3.4 (light meta-test)~~ **REMOVED at v0.7 W6-8 — replaced by `SEMVER_POLICY_VERSION` constant test below**
- **~8 NEW v0.7** (W6 patches):
  - 1× `RefinedCandidate.__post_init__` hard-asserts 3-flag equality (W6-1): manual construction of invalid flag combinations raises `InvariantViolationError`
  - 1× `RefinedCandidate.from_operator_class(...)` helper constructor (W6-1): correct flags emitted per operator class; matches the § 0.3.1 worked-example table
  - 1× `capability_mode` derived property (W6-1): returns "PREDICATE_ONLY" iff `not geometry_materialized`
  - 1× `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` versioning (W6-3): same `refined_parameters` but different version constant → different fingerprint; cache key mismatch correctly fires
  - 1× `EnvironmentFingerprint.tiebreak_fingerprint_schema_version` field populated (W6-3): captured at run time; cache invalidates across version changes
  - 1× `get_primary_application_result` accessor (W6-6): correctly extracts single result; raises `EvaluatorContractError` on malformed multi-result MTC
  - 1× `SEMVER_POLICY_VERSION == 1` constant assertion (W6-8): replaces v0.6 doc-presence meta-test
  - 1× § 0.7.2 TIER-3 minimum semantics frozen (W6-4): light schema-presence test asserting the values declared in § 0.7.2 are documented in code constants (see B-NEW-W backlog when implementing); not a meta-test, an actual contract check

**Net v0.4 + v0.5 + v0.6 + v0.7 = 12 + 12 + 6 + 8 = 38 new tests** vs v1.0 LOCKED baseline (one v0.6 test removed by v0.7 W6-8; one v0.6 test absorbed into v0.7 W6-1 hard-assertion test).

Cumulative target: baseline at v0.7 authorship is **2909 passed / 3 skipped** (S41 close, post-C11a v1.6 + self-review fixes). C11b ship target is therefore **2909 + 38 ≈ 2947 passed** at v0.7 spec ship-out. The ~190 from v1.0's projection is the *total* C11b test addition that includes ~152 from v0.1/v0.2/v0.3 + 38 from v0.4/v0.5/v0.6/v0.7.

---

## § 7 — Open questions at v0.7

**0 open questions remaining.** Walk #6 (v0.6 → v0.7) resolved all 15 critique items via the PATCH-NOW / BACKLOG / ALREADY-DOCUMENTED routing matrix.

---

## § 8 — Backlog at v0.4 + v0.5 + v0.6 + v0.7

**New / widened at v0.4**:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C11B-MF** (NEW) | Multi-floor topology refinement for C11b | v0.4 D-MF-1 | When product needs end-to-end MF refinement (likely with C12 MF placement OR C14 MF scoring) | L |
| **B-C11B-TIMEOUT-V2** (NEW) | Per-evaluation timeout + generation-level resumability after wall-clock breach | v0.4 D-TO-3 | When measured tail-latency on production evaluator becomes a quality concern | M |
| **B-NEW-V5** (WIDENED) | Broader EA protocols + **NSGA-III migration** | v0.3 carry + v0.4 D-NSGA-2 widening | (a) C14 ≥3 obj AND (b) hypervolume regression 2+ cycles, OR (c) architect blocking feedback | L |

**New at v0.5 (Walk #4 critique outcomes)**:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C11B-EVALUATOR-RESILIENCE** (NEW) | Replenish skipped candidates immediately with regenerated offspring instead of shrinking population mid-generation | v0.5 W4-7 (Item 7) | When measured Pareto-front quality degrades correlated with high skip-counts on production evaluator | M |
| **B-C11B-RESOLVER-V2** (NEW) | `primary_application_result: MutationApplicationResult` singleton field on `MutatedTopologyCandidate` (cleanup of v1 cardinality brittleness) | v0.5 W4-8 (Item 8) | When (if) C11a introduces multi-application MTCs | M |
| **B-C11B-TIMEOUT-COMPLEXITY** (NEW) | Complexity-aware timeout budget: `timeout = base + k * room_count` or similar | v0.5 W4-12 (Item 12) | When measured timeout-failures cluster on complex briefs | S-M |
| **B-C11B-INV-TIERING** (NEW) | Formal CORE / REPLAY / DIAGNOSTIC tiering of the 29 invariants; allow non-core relaxation in development mode | v0.5 W4-14 (Item 14) | When contributor onboarding signals 29 invariants is a cognitive blocker | S |
| **B-C11B-STRICT-TIERS** (NEW) | STRICT_PER_TOPOLOGY vs STRICT_GLOBAL distinction; configurable systemic-failure thresholds; partial batch salvage mode | v0.5 W4-17 (Item 17) | When production runs see frequent batch-halts from single pathological topologies | M |
| **B-C12-MATERIALIZATION-CONTRACT** (NEW, ROUTED TO C12) | C12 placement layer MUST assert all three v0.6 capability flags are consistent before consuming refined parameters as final geometry. Routed downstream — not C11b's responsibility | v0.5 W4-2 + v0.6 W5-5 (Item 2 downstream, REVISED for capability flags) | When C12 spec arc begins | S (spec invariant addition) |

**New at v0.6 (Walk #5 critique outcomes)**:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C11B-DOERR-TIEBREAK** (NEW) | Adopt Doerr/Ivan/Krejca 2024 frequency-based NSGA-II tie-break (AAAI; arxiv 2412.11931). Proves NSGA-II can optimize benchmarks efficiently for ≥3 objectives via "number of individuals with the same objective value" as the third tie-break criterion (before random tail). Simultaneously addresses Walk #5 Items 2 (deterministic tie-break bias) and 15 (NSGA-II 3-objective limitation). | v0.6 W5-2 + W5-15 (Items 2 + 15) | Before C14 production evaluator ships OR when first 3-objective evaluator hypervolume regression is observed. **High priority** — has peer-reviewed proof and addresses two known v1 limitations with one mechanism. | M (implement frequency counting per objective; integrate with existing tie-break sort) |
| **B-C11B-CACHE-TIERS** (NEW) | Cache-relevance tiering: OUTPUT_CRITICAL / REPLAY_CRITICAL / DIAGNOSTIC, replacing the binary `cache_relevant: bool`. Reduces cache fragmentation under operational tuning by allowing operational knobs to bypass cache invalidation when only diagnostics change | v0.6 W5-4 (Item 4) | When measured cache hit rates collapse during experimentation OR when storage costs from over-invalidation become an operational concern | M |
| **B-C11B-PROVENANCE-SPLIT** (NEW) | Split `LocalRefinementProvenance` into three independently-versioned dataclasses: `ReplayProvenance` (master_seed, env tuple, c11b_version), `OperationalTelemetry` (timeouts, skips, durations), `DiagnosticWarnings` (resolved_objective_count, skipped_multifloor_count). Enables safer version increments | v0.6 W5-11 (Item 11) | When provenance schema growth blocks safe version increment OR when consumers want partial provenance reads | M |
| **B-C11A-MTC-SINGLETON** (NEW, ROUTED TO C11a) | C11a v1.6 amendment to expose `primary_application_result: MutationApplicationResult` as a type-honest singleton field, with `extra_application_results: tuple[...] = ()` for future batch expansion. Eliminates the v1 tuple-vs-singleton schema dishonesty | v0.6 W5-13 (Item 13) | Whenever C11a v1.6 LOCKED takes a non-trivial amendment for any other reason | S |
| **B-C11B-COMPLEXITY-BUDGET-V2** (NEW) | Define a weighted complexity metric alongside subsystem count: weight invariants × 1, cache-affecting fields × 2, replay constraints × 3, telemetry fields × 0.5. Track over walks to detect "subsystem-count steady but real complexity climbing" pattern | v0.6 W5-14 (Item 14) | When walk N+1's apparent stability hides complexity climb visible only via the weighted metric | S |
| **B-C11B-SPEC-SPLIT-V2** (NEW) | Documentation modularization: split this spec into `C11b-Core-Optimization` + `C11b-Replay` + `C11b-Provenance` + `C11b-Failure-Policy`. Code stays unified; docs split | v0.6 W5-20 (Item 20) | When spec length exceeds ~1500 lines (currently ~1100) OR when a contributor explicitly requests modular reading | S |
| **B-PIPELINE-CAPABILITY-NEGOTIATION** (NEW, ROUTED TO ORCHESTRATOR) | Orchestrator-level capability flag (`supports_multifloor_refinement: bool`) consulted by upstream components before generating multi-floor candidates. Prevents wasted MF generation when C11b is configured to reject MF | v0.6 W5-7 (Item 7, cross-component) | When measured MF-rejection cost crosses orchestrator-observable thresholds | M |
| **B-C11B-HYPERVOLUME-WARN** (NEW, follow-on to W5-18) | Hypervolume-regression-based warning replacing the dropped `nsga2_objective_count_warning` bool. Triggers when current-run hypervolume falls below historical baseline by configurable threshold. Requires hypervolume computation infrastructure (B-NEW-W). **v0.7 W6-13 amendment**: backlog item now explicitly requires freeze of normalization policy + benchmark corpus BEFORE the warning fires in production | v0.6 W5-18 + v0.7 W6-13 | After B-NEW-W ships hypervolume metric | S (once B-NEW-W lands) |

**New at v0.7 (Walk #6 critique outcomes)**:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C11B-TIER2-SCALING** (NEW v0.7) | Replace O(N²) pairwise dominance checks in TIER-2 replay validation with hashing/indexing structures (ND-trees, front-adjacency signatures, Pareto layer DAG fingerprints). Standard literature treatment (Bashir 2025 arxiv 2508.20689) | v0.7 W6-2 (Item 2) | When CI TIER-2 wall-clock > 5min per replay batch OR when population sizes exceed 500 | M |

**v0.7 backlog amendments (no new items, sharpened existing entries)**:

| Existing ID | v0.7 Amendment |
|---|---|
| B-C11B-DOERR-TIEBREAK | Doerr 2024 assumes discrete objectives; continuous floats reduce frequency-counting to ~all-1 buckets. Adoption requires continuous-objective adaptation research (epsilon-clustering or density estimation) + empirical validation BEFORE replacing v1 tie-break. (W6-5) |
| B-C11B-TIMEOUT-V2 | Scope extended to include intra-generation watchdog hooks: candidate-evaluation checkpoints, evaluator soft deadlines, heartbeat timestamps. (W6-10) |
| B-C11B-CACHE-TIERS | Trigger tightened: "when cache hit rate drops below 50% in experimentation runs" (was vague "when measured cache hit rates collapse"). (W6-9) |

**v0.7 backlog priority promotions (already-documented items, elevated)**:

- **B-C11B-COMPLEXITY-BUDGET-V2** → MANDATORY surface: every future walk MUST report the weighted complexity metric in § 14.1 convergence table. v0.7 sets the precedent by including the metric in § 0 narrative and § 14.1.
- **B-C11B-PROVENANCE-SPLIT** → HIGH priority: trigger criterion tightened to "any change requiring c11b_version MINOR or MAJOR bump."
- **B-NEW-Z** (deterministic-parallel-NSGA-II) → cross-referenced explicitly in § 0.7.1 as the candidate_index parallel-replacement path.
- **B-C11B-SPEC-SPLIT-V2** → HIGH priority: § 0.0d "current surface only" digest is the interim mitigation; spec split itself remains backlog.

Existing v1.0 backlog items (B-237, B-NEW-P, B-NEW-V, B-NEW-W, B-NEW-X, B-NEW-Y, B-NEW-Z, B-NEW-V2, B-NEW-V3, B-NEW-V4, B-NEW-V6) carried unchanged.

**Cumulative at v0.7: 29 backlog items** (12 carried + 2 new at v0.4 + 6 new at v0.5 + 8 new at v0.6 + 1 new at v0.7).

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

## § 9a — Rule 11 self-analysis pass on v0.5 PROPOSED

Applied Rule 11 to v0.5 itself before submitting (the patches AND the new spec text), looking for what could still be wrong:

| # | Finding | Verdict |
|---|---|---|
| F-v5-1 | The cache_relevant flips (W4-4, W4-5) invalidate any existing v0.4 caches. No v0.4 caches exist yet (no C11b code shipped), so this is theoretical; documenting for completeness. | **DOCUMENTED** — no live caches; v0.5 is pre-build. |
| F-v5-2 | The tie-break rule in § 0.7.1 uses `canonical_serialize(candidate.refined_parameters)` for layer 2. If `canonical_serialize` doesn't exist yet for `RefinedParameters` (it's a C7 amendment v0.8 utility for upstream types), C11b build needs to register `RefinedParameters` with the serializer. | **DOCUMENTED** — flagged as a build-time dependency; not a spec defect. |
| F-v5-3 | `source_topology_candidate_signature: str` on `RefinedCandidate` duplicates information already reachable via `source_topology_candidate.application_results[0]....` — but the duplication is intentional (exposing it at the `RefinedCandidate` level decouples tie-break from upstream traversal). | **DOCUMENTED** — intentional denormalization. |
| F-v5-4 | The structurally-equivalent tolerance (`1e-9` absolute) in Inv 29 is a magic number. Why 1e-9 and not 1e-6 or 1e-12? | **DOCUMENTED** — `1e-9` matches IEEE 754 double-precision relative error for typical room-dimension magnitudes (~10⁰-10¹ meters). Tighter than 1e-12 (would catch nondeterminism noise as false failure); looser than 1e-6 (would mask real algorithmic divergence). Tunable if production CI signals otherwise. |
| F-v5-5 | `mutation_semantics` enum has exactly 2 states (`PREDICATE_ONLY`, `MATERIALIZED`). If C12 introduces a partial-materialization concept, it'll need a 3rd state. | **DOCUMENTED** — sufficient for v1; v2 extension would be `PARTIALLY_MATERIALIZED` if needed. Routed downstream via B-C12-MATERIALIZATION-CONTRACT. |
| F-v5-6 | `per_topology_telemetry: tuple[PerTopologyTelemetry, ...]` lives on `LocalRefinementProvenance` and is "empty when verbosity < PER_TOPOLOGY". The verbosity threshold is named `PER_TOPOLOGY` but the v1.0 carried enum has `PER_GEN`. Naming mismatch. | **PATCH-NOW in v0.5** — use the carried v1.0 `PER_GEN` verbosity threshold consistently. |
| F-v5-7 | The `_resolve_input_artifact` defensive raise on `len(application_results) != 1` is now also Inv 26 enforcement. If a future C11b test wants to test the defensive path with a multi-result MTC, it needs a way to construct one — but C11a doesn't currently support multi-result construction. | **DOCUMENTED** — test uses `dataclasses.replace(mtc, application_results=(r1, r2))` to manually construct a malformed MTC. Acceptable test technique; doesn't require C11a changes. |

7 findings, 1 PATCH-NOW (F-v5-6 → fix below). Rest documented. No new audit findings vs. v0.4 baseline.

**Patch applied** (F-v5-6): in § 2.1, the `per_topology_telemetry` field doc references the v1.0 carried `ProvenanceVerbosity` enum's `PER_GEN` value (not the non-existent `PER_TOPOLOGY`).

---

## § 10 — Status

- **v1.1 LOCKED at S41 close by Ramalingam authority per Rule 8.**
- 6 walks of evolution: v0.4 (post-v1.0 drift) → v0.5 (Walk #4 external) → v0.6 (Walk #5 external) → v0.7 (Walk #6 external) → LOCK.
- 0 open questions at LOCK.
- 1 audit finding carried (F-v4-7 backlog ID convention; DOCUMENTED, no action).
- 29 backlog items at LOCK (12 carried + 17 added across v0.4-v0.7).
- 29 invariants (was 25 at v1.0 LOCKED S37; +4 at v0.4; 0 new at v0.5-v0.7 with wording revisions).
- Subsystem count = 10 (cap held across 6 walks).
- Weighted complexity = 48 (vs subsystem count 10 — visibility added per Walk #6 W6-7 promotion).
- 38 new tests target relative to v1.0 LOCKED baseline (cumulative ~2947 passed at C11b ship).

**This is the canonical C11b spec. C11b build starts immediately per the build plan in NEXT_CLAUDE_HANDOFF.md.**

---

## § 9c — Rule 11 self-analysis pass on v0.7 PROPOSED

Applied Rule 11 to v0.7 itself, including a particularly close look since v0.7's Item 3 fix patched a HIGH-severity hole that prior Rule 11 passes missed:

| # | Finding | Verdict |
|---|---|---|
| F-v7-1 | The Item 3 fix (W6-3) adds `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` as a separate constant from `c11b_version`. Two version numbers to track. A future contributor amending `_compute_tiebreak_fingerprint` could increment one but not the other. | **DOCUMENTED** — § 0.3.4 SemVer table now covers tiebreak_fingerprint_schema_version: incrementing it is a MINOR bump on `c11b_version`. The two versions are not redundant: tiebreak version covers fingerprint derivation specifically; c11b version covers all C11b surface. Build discipline + commit message convention. |
| F-v7-2 | `RefinedCandidate.from_operator_class` helper requires importing `OperatorClass` from C11a's enum. If C11a renames or reorganizes that enum, the helper signature breaks. Cross-component coupling. | **DOCUMENTED** — same as the existing C11a-C11b coupling for `MutatedTopologyCandidate`. Already covered by C11a versioning discipline. |
| F-v7-3 | § 0.7.2 freezes TIER-3 minimum semantics (paired Wilcoxon, p>0.05, etc.) but B-NEW-W is the actual implementation arc. If B-NEW-W's spec arrives and chooses different semantics, § 0.7.2 must be amended OR B-NEW-W must accept the constraints. Which? | **DOCUMENTED** — v0.7's intent is that § 0.7.2 IS the contract; B-NEW-W must respect it. If B-NEW-W has good reasons to deviate, that requires a v0.X PATCH amendment of § 0.7.2, not a unilateral B-NEW-W deviation. |
| F-v7-4 | The product-relevance audit (§ 0.0c) lists TIER-2 as PRODUCT-CRITICAL but the v0.6/v0.7 spec actually relies on TIER-2 only in CI replay tests. CI is "product" insofar as it gates releases, but operators don't see TIER-2 results directly. Is the labeling overstated? | **DOCUMENTED** — debatable. v0.7 keeps PRODUCT-CRITICAL because CI gating IS a product surface (a broken CI gate ships broken code). Reviewers may push back; the audit is a starting point, not a final word. |
| F-v7-5 | The 4 backlog promotions (Items 7, 11, 12, 14) don't actually CHANGE the spec's near-term path — the items remain backlog, just "higher priority backlog." Is the promotion meaningful, or symbolic? | **DOCUMENTED** — meaningful: it commits Claude (and future-Claude) to surfacing these items in every walk's § 14.1 convergence table going forward. That's a discipline change, not just a label change. |
| F-v7-6 | § 0.0d "current surface only" digest is a documentation artifact, not a contract. It can drift from the actual spec body without breaking any test. | **DOCUMENTED** — true and accepted. The digest is a navigation aid. A consistency-check test ("digest field declarations match dataclass definitions") would be over-engineering. If it drifts, future walks catch it. |

6 audit findings, 0 PATCH-NOW (all DOCUMENTED). No blockers.

---

## § 9b — Rule 11 self-analysis pass on v0.6 PROPOSED

Applied Rule 11 to v0.6 itself before submitting (the patches AND the new spec text), looking for what could still be wrong:

| # | Finding | Verdict |
|---|---|---|
| F-v6-1 | The three v0.6 capability flags (`geometry_materialized`, `placement_safe`, `requires_transform_resolution`) at v1 collapse to 2 effective states (Tier A vs Tier B/M0) via the equality `placement_safe == geometry_materialized AND requires_transform_resolution == NOT geometry_materialized`. So v1 has the same expressive power as v0.5's enum but uses 3 fields. Is this over-engineering for v1? | **DOCUMENTED** — the redundancy is intentional. The v1 invariant constrains the 3 flags to 2 states; later operators (e.g., placement-aware Tier A) can break the equality without an enum migration. Cost (3 bool fields vs 1 enum) is small; future-proofing benefit is real. |
| F-v6-2 | TIER-3 (statistically-equivalent) is deferred to B-NEW-W but referenced in Inv 29's wording. Reader of v0.6 alone sees "TIER-3 deferred" with no concrete semantics. Risk: future-Claude implements ad-hoc TIER-3 semantics inconsistent with B-NEW-W's eventual spec. | **DOCUMENTED** — § 0.7 explicitly says "deferred to B-NEW-W" and "TIER-3 tests will land alongside B-NEW-W." v1 ships without TIER-3 tests at all. No ad-hoc implementation risk because no TIER-3 invariant fires in v1 code. |
| F-v6-3 | `tiebreak_fingerprint: int` is precomputed in `RefinedCandidate.__post_init__`, but `RefinedCandidate` is a frozen dataclass — `__post_init__` must use `object.__setattr__` to set the field. This is a build-time gotcha not surfaced in the spec. | **DOCUMENTED** — common Python idiom; builders know it. Build-time note can be added if it bites. |
| F-v6-4 | The SemVer table in § 0.3.4 says "v0.6 specifically keeps `C11B_VERSION = v1.1`" — but the v0.6 schema replacement of `mutation_semantics` (a MAJOR change per the same table) is technically a contract-break. The "v0.5 was PROPOSED not LOCKED so no consumers exist" exception is correct but worth surfacing more clearly. | **DOCUMENTED** — explicit text in § 0.3.4 calls out the exception. Future amendments after a LOCK must follow the table strictly. |
| F-v6-5 | B-C11B-DOERR-TIEBREAK requires implementing "count of individuals having each objective value" as a third tie-break criterion. If the production evaluator uses continuous objectives (e.g., float compactness scores), exact-equality counting is nearly useless. Adapting Doerr 2024 for continuous-valued objectives requires binning or epsilon-clustering — not addressed in the cited paper. | **DOCUMENTED** — backlog item description should mention this adaptation work. Triggering it before C14 ships means the adaptation can be done with full knowledge of C14's objective semantics. |
| F-v6-6 | The v0.6 test counts (§ 6) include "1× SemVer rule documentation existence (W5-19)" which is a meta-test (asserts spec text exists). Meta-tests are unusual; reviewer could call them low-value. | **DOCUMENTED** — meta-tests guard against accidental spec-section removal during amendment churn. Light but worth keeping. |
| F-v6-7 | § 0 narrative claims "0 new subsystems at v0.6" but adding TIER-1/2/3 nomenclature, capability flags, tiebreak_fingerprint precompute, SemVer rules, and 8 backlog items DOES expand cognitive surface area even without new code subsystems. The reviewer's Item 14 concern (subsystem-count understates complexity) is itself the right diagnosis; v0.6 files B-C11B-COMPLEXITY-BUDGET-V2 against it. | **DOCUMENTED** — backlog item exists precisely because of this concern; no PATCH-NOW action. |

7 audit findings, 0 PATCH-NOW (all DOCUMENTED). No blockers.

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
| **B-C11B-EVALUATOR-RESILIENCE** (NEW v0.5) | **Replenish-skipped-candidates strategy (vs population shrinkage)** | v0.5 W4-7 | M |
| **B-C11B-RESOLVER-V2** (NEW v0.5) | **`primary_application_result` singleton field for cardinality safety** | v0.5 W4-8 | M |
| **B-C11B-TIMEOUT-COMPLEXITY** (NEW v0.5) | **Complexity-aware timeout budget scaling** | v0.5 W4-12 | S-M |
| **B-C11B-INV-TIERING** (NEW v0.5) | **CORE/REPLAY/DIAGNOSTIC invariant categorization** | v0.5 W4-14 | S |
| **B-C11B-STRICT-TIERS** (NEW v0.5) | **STRICT_PER_TOPOLOGY vs STRICT_GLOBAL distinction + partial batch salvage** | v0.5 W4-17 | M |
| **B-C12-MATERIALIZATION-CONTRACT** (NEW v0.5, ROUTED TO C12, REVISED v0.6) | **C12 must assert capability-flag consistency before consuming refined parameters** (v0.6 W5-5 changed surface from enum to 3 booleans) | v0.5 W4-2 + v0.6 W5-5 | S |
| **B-C11B-DOERR-TIEBREAK** (NEW v0.6) | **Doerr/Ivan/Krejca 2024 frequency-based NSGA-II tie-break (AAAI; arxiv 2412.11931); peer-reviewed proof; addresses items 2 + 15 simultaneously** | v0.6 W5-2 + W5-15 | M |
| **B-C11B-CACHE-TIERS** (NEW v0.6) | **Cache-relevance tiering (OUTPUT_CRITICAL / REPLAY_CRITICAL / DIAGNOSTIC)** | v0.6 W5-4 | M |
| **B-C11B-PROVENANCE-SPLIT** (NEW v0.6) | **Split LocalRefinementProvenance into ReplayProvenance + OperationalTelemetry + DiagnosticWarnings** | v0.6 W5-11 | M |
| **B-C11A-MTC-SINGLETON** (NEW v0.6, ROUTED TO C11a) | **C11a v1.6 amendment exposing `primary_application_result` as type-honest singleton** | v0.6 W5-13 | S |
| **B-C11B-COMPLEXITY-BUDGET-V2** (NEW v0.6) | **Weighted complexity metric (invariants×1, cache×2, replay×3, telemetry×0.5)** | v0.6 W5-14 | S |
| **B-C11B-SPEC-SPLIT-V2** (NEW v0.6) | **Documentation split: Core / Replay / Provenance / Failure-Policy** | v0.6 W5-20 | S |
| **B-PIPELINE-CAPABILITY-NEGOTIATION** (NEW v0.6, ROUTED TO ORCHESTRATOR) | **Upstream `supports_multifloor_refinement: bool` flag** | v0.6 W5-7 cross-component | M |
| **B-C11B-HYPERVOLUME-WARN** (NEW v0.6, follow-on) | **Hypervolume-regression-based warning (after B-NEW-W lands)** | v0.6 W5-18 follow-on | S |
| **B-C11B-TIER2-SCALING** (NEW v0.7) | **O(N²) dominance check → hash/ND-tree fingerprinting at scale (Bashir 2025)** | v0.7 W6-2 | M |

**Backlog summary**:

| Total | Pre-existing | v0.1 | v0.2 | v0.3 | v0.4 | v0.5 | v0.6 | v0.7 |
|---|---|---|---|---|---|---|---|---|
| **29** | 2 | 5 | 2 | 3 | 2 | 6 | 8 | **1** |

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

## § 14 — Freeze candidacy rationale (REVISED v0.7)

### § 14.1 — Convergence signals (NOW WITH WEIGHTED COMPLEXITY METRIC per W6-7 promotion)

| Walk | Open Qs | Audit findings | New v1 subsystems | Critique items | Weighted complexity |
|---|---|---|---|---|---|
| v0.1 | 7 | 8 | 9 (initial) | (seed) | ~25 (estimated) |
| v0.2 | 2 | 7 | +1 | 8 | ~30 |
| v0.3 | 0 | 5 | +0 | 8 | ~35 |
| v1.0 LOCKED | 0 | 5 (carried) | +0 | (lock) | ~35 |
| v0.4 | 0 | 6 (1 PATCH-NOW + 1 RESOLVED + rest DOC) | +0 | 7 (self-analysis) | ~40 |
| v0.5 | 0 | 7 (1 carried + 1 PATCH-NOW via F-v5-6 + 5 DOC) | +0 | 20 (Walk #4 external) | ~44 |
| v0.6 | 0 | 8 (1 carried + 7 self-pass; 0 PATCH-NOW) | +0 | 20 (Walk #5 external) | ~46 |
| **v0.7** | **0** | **7 (1 carried + 6 v0.7 self-pass; 0 PATCH-NOW; all DOC)** | **+0** | **15 (Walk #6 external)** | **~48** |

**Weighted complexity formula** (per B-C11B-COMPLEXITY-BUDGET-V2, MANDATORY surface at v0.7 onward):
```
weighted_complexity = (invariants × 1)
                    + (cache-affecting config fields × 2)
                    + (replay tiers × 3)
                    + (telemetry fields × 0.5)
```

v0.7 breakdown: `29×1 + 3×2 + 3×3 + 8×0.5 = 29 + 6 + 9 + 4 = 48` (vs subsystem count = 10).

**What the table shows**: Subsystem count has been flat at 10 since v0.2. Weighted complexity has grown from ~25 to ~48 — nearly doubling across 7 walks. This validates Walk #6 Item 7's concern: subsystem count alone hides the actual complexity climb. Future walks must continue reporting this column.

### § 14.2 — Why v0.7 is the third external-critique resolution

v0.7 continues the pattern established by v0.5 and v0.6: external critique → Rule 7 walk → web research + code grep → PATCH-NOW + BACKLOG + DOCUMENTED routing.

- **15 critique items from external reviewer** (the document supplied as "Genuine drawbacks / risks in C11b v0.6 PROPOSED")
- Routing matrix verified via Rule 7 walk + 2 web searches (dominance hash structures + replay fingerprint versioning) + code grep on `buildemup/utilities/canonical.py` (verifying Item 3)
- 6 items were correctness/UX PATCH-NOW
- 4 items were backlog-text amendments (sharpen existing entries)
- 1 item was a new backlog (B-C11B-TIER2-SCALING)
- 4 items were already documented, promoted to higher priority

**HIGH severity finding (Item 3)**: `tiebreak_fingerprint` was vulnerable to silent drift via canonical_serialize evolution without c11b_version bump. This is a stealth correctness bug that prior Rule 11 passes (v0.6 § 9b) did not catch. v0.7 W6-3 closes the hole with explicit `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` + cache-key composition. The fact that Rule 11 missed this in v0.6 is itself documented as F-v7 audit context — a reason to maintain external-critique discipline rather than relying solely on self-analysis.

**Architectural declaration (Item 15)**: Walk #6 raised the meta-concern that replay infrastructure was overshadowing optimization. v0.7 § 0.0c "Product-relevance audit" responds with an explicit framework: 6 PRODUCT-CRITICAL surfaces, 2 OPERATIONAL, 1 RESEARCH/DEBUG. This is the kind of architectural anchor that prevents future replay-feature creep.

### § 14.3 — Counter-arguments to LOCK now

1. **1 new backlog item + 4 sharpened backlog items + 4 promotions** — all post-v1 scope; none block v1 build.
2. **Weighted complexity = 48** (4.8× subsystem count). Real, but the bulk is replay infrastructure that is now explicitly product-justified in § 0.0c.
3. **F-v7-1 two version numbers** — TIEBREAK_FINGERPRINT_SCHEMA_VERSION + c11b_version. Build discipline + commit conventions handle it.
4. **F-v7-4 PRODUCT-CRITICAL labeling debatable** — yes, but the audit is a starting point; reviewers may disagree on individual labels without invalidating the framework.

None block LOCK.

### § 14.4 — Recommendation

**Request LOCK on v0.7.** This spec addresses the post-LOCK drift (v0.4) + Walk #4 (v0.5) + Walk #5 (v0.6) + Walk #6 (v0.7) external critiques. 6 walks of refinement (4 of them externally critiqued); convergence stable; 0 new v1 subsystems across all walks; weighted complexity 48 (visible and justified); 0 open questions.

The HIGH-severity Item 3 fix (W6-3) is the single most important correctness improvement across all 6 walks — without it, v0.6 would have shipped with a stealth replay-drift hole. That alone justifies v0.7 over v0.6.

If you want a Walk #7 instead, v0.7 stays PROPOSED until that walk runs.

---

**End of v1.1 LOCKED.** This is the canonical C11b spec. C11b Sub-1 build can begin per the build plan in `00_START_HERE/NEXT_CLAUDE_HANDOFF.md`.
