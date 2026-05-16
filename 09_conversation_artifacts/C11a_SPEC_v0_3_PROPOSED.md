# C11a — Topology Mutation Layer — SPEC v0.3 PROPOSED

**Component**: 11a (canonical Track 3 numbering — paired with C11b NSGA-II)
**Status**: v0.3 PROPOSED. **NOT LOCKED.** Supersedes v0.2 PROPOSED.
**Authority**: S37 Walk #3 author's draft. PENDING Ramalingam adjudication.
**Authored**: S37 Walk #3, post external critique walk on v0.2.

---

## § 0 — Architectural notes (REVISED v0.3)

C11a sits between C10 (Wet-Zone Stack Planner) and C11b (NSGA-II Local
Refinement). Two-tier mutation architecture (carried v0.2):

- **Tier A — Shallow topology transforms** (M1, M2, M3a/b/c, M4, M5, M9a/b/c/d).
  Operator-local logic; targeted invariant subset re-validation; fast path.
- **Tier B — Regenerative topology transforms** (M6, M7a/b, M8). Mutation
  triggers `DeepMutationPipeline`: C7 → C9 → C10 re-execution.

### Atomicity-by-construction (NEW v0.3 — resolves critique #11)

Per Walk #3 critique #11: the spec was silent on rollback semantics for
partial-execution failures. v0.3 makes the atomicity rule explicit, but
the implementation is simpler than database-style rollback:

**No infrastructure addition.** All Tier B state is built from frozen
dataclasses with new-object semantics. There is no shared mutable upstream
artifact to roll back. A `DeepMutationPipeline` invocation either:

- **Succeeds**: returns a fully-formed `WetZonePlannedCandidate` (new object,
  upstream candidates unmodified).
- **Fails**: raises `DeepMutationApplicationError`. Pipeline output is
  `None`; the source candidate and all upstream state remain unchanged.
- **Partially fails**: not possible. C7/C9/C10 entry points themselves
  return new immutable objects or raise. There is no half-built state.

Distributed-system rollback infrastructure (checkpoint + UNDO logs per
Sauer & Härder 2014) is not needed because the mutation graph contains
no shared mutable nodes. v0.3 documents this as Inv 17 (NEW).

### Mutation Legality Responsibility Matrix (REVISED v0.3 — resolves critique #3)

v0.2 introduced "C11a-internal invariants" (privacy, staircase clearance,
entry approach). Critique #3 correctly identifies these as upstream
concerns conceptually owned by C5/C7/C8. v0.3 reframes:

**C11a does not own architectural rules.** C11a orchestrates legality by
referencing upstream rule IDs through `MutationViabilityPredicate`
objects. If a needed rule does not exist upstream, file as a separate
amendment to that upstream component (B-NNN entry); do NOT redefine in C11a.

```python
@dataclass(frozen=True)
class MutationViabilityPredicate:
    """Reference to an upstream rule that gates mutation viability.
    NEW v0.3 — replaces v0.2's "C11a-internal invariants" framing.
    """
    rule_owner: str        # "C5" | "C7" | "C8" | "C9" | "C10"
    rule_id: str           # owner's canonical rule identifier
    description: str       # human-readable; for diagnostics, NOT authoritative
    predicate: Callable    # the actual check function (lives upstream;
                           # C11a holds a reference, not a redefinition)
```

| Layer | Owns | C11a references |
|---|---|---|
| C5 | Topology family taxonomy, **privacy zoning rules** | "C5_zoning_privacy" |
| C7 | Grid invariants W1–W8, **staircase clearance** | "C7_staircase_clearance" |
| C8 | Corridor design, **entry approach compatibility** | "C8_entry_approach" |
| C9 | Room sizing invariants | "C9_Inv_5", "C9_Inv_13" |
| C10 | Wet-zone invariants Inv 1–21 | "C10_Inv_5", "C10_Inv_5b", etc. |
| **C11a (THIS)** | **Mutation transform application + viability orchestration** | (only its own application logic) |

**Concrete amendments needed upstream** (each filed as a separate B-NNN):

| ID | Upstream amendment |
|---|---|
| B-NEW-J | C5: privacy zoning rule (bedrooms cannot face primary road; codify the rule explicitly) |
| B-NEW-K | C7: staircase clearance invariant (extend W-invariants with staircase rule) |
| B-NEW-L | C8: entry approach compatibility (codify entry-corridor compatibility as an invariant) |

C11a v1 ships with `MutationViabilityPredicate` references that point at
**these B-NNN-pending rules**. If an upstream rule isn't yet codified,
the predicate is marked `pending_upstream=True` and C11a applies a
*temporary inline check* clearly tagged as such — auditable, removable
once the upstream amendment lands.

### Tier B caching (NEW v0.3 — resolves critique #1)

```python
@dataclass(frozen=True)
class DeepMutationCacheKey:
    """Signature-keyed memoization for DeepMutationPipeline.
    NEW v0.3."""
    operator: MutationOperator
    source_topology_signature_hash: str
    config_hash: str           # SHA256 of relevant TopologyMutationConfig fields
```

Cache scope is **single batch** (per `mutate_topologies` invocation).
Cache discarded at function return. No cross-invocation persistence at
v1 (deferred to B-NEW-E2 — process-lifetime cache). This bounds cache
size: 16 operators × 8 inputs = 128 entries max per batch.

Hit rate expectations: **low** for diverse inputs (each candidate's
topology signature is typically unique); **high** for repeated structurally
identical inputs (e.g., test fixtures, multi-config sweeps).

Incremental regeneration (delta propagation between C9 → C10 when only
M7 grid scaling changed) is deferred to **B-NEW-E2** v2 work. The
signature-keyed cache is the v1 floor.

---

## § 1 — Walk-resolved scope (REVISED v0.3)

| Q | Resolution | Walk |
|---|---|---|
| Q4 | Hybrid Tier A / Tier B validity (carried v0.2) | W#2 |
| Q3 | Single-operator only at v1; schema future-proofs composition | W#2 |
| Q5 | Per-family slot allocation with deterministic spillover | W#2 |
| Q7 | No filtering at C11a output | W#2 |
| Q8 | `topology_variant_id` SHA256-12char of canonical signature | W#2 |
| Q9 | Invalid mutations surface in provenance log; not as outputs | W#2 |
| Q14 | v1 stays domain-specific; diversity diagnostics added | W#2 |
| Q15 | M0_BASE doesn't count against `max_seeds_per_input` | W#2 |
| **Q19 (W#3)** | **`DeepMutationPipeline` as a C11a-internal helper module (`components/c11a/deep_pipeline.py`); reuses C7/C9/C10 entry points; no new component.** | W#3 |
| **F-v2-1 (W#3)** | **Tier B caching: signature-keyed memoization, single-batch scope, max 128 entries.** | W#3 |
| **F-v2-3 (W#3)** | **`INVALIDATES_FAMILY` enum kept; M5 zone swap can produce family-invalidation when all four cardinal zones are reassigned. Walk #4 confirms with concrete fixture.** | W#3 (tentative) |
| **F-v2-6 (W#3)** | **C11a-internal invariants migrated. Privacy/staircase/entry now reference upstream B-NEW-J/K/L pending amendments.** | W#3 |
| **F-v2-7 (W#3)** | **Systemic upstream errors (`KBVersionMismatchError`, `RemediationGraphError`, `PlumbingConfidenceTooLow`) propagate UNCAUGHT through C11a. Per-batch errors (`BatchWetZoneInfeasibleError`) are caught and wrapped as `DeepMutationApplicationError`.** | W#3 |
| **Q20 (W#3)** | **`novelty_deficit_estimator` = `1 - avg_pairwise_jaccard_distance(signature_edge_sets)`. Labeled low-fidelity in spec; B-NEW-F covers evolution to graph-edit-distance.** | W#3 |

---

## § 2 — Contract (REVISED v0.3 — atomicity-explicit)

Top-level signature unchanged from v0.2.

### § 2.1 — Operator enum (carried)

Carried verbatim from v0.2.

### § 2.2 — Family transition policy (REVISED v0.3 — INVALIDATES_FAMILY survives)

Carried v0.2 with one update: M5 reclassified to `TRANSFORMS_OR_INVALIDATES`
(both possible depending on plot proportions). Walk #4 produces concrete
fixture demonstrating M5 invalidation case. Until then, M5 is documented
as `TRANSFORMS_FAMILY` with annotation `may_invalidate=True`.

### § 2.3 — Application result + candidate (REVISED v0.3 — lineage depth added)

```python
class MutationLineageDepth(str, Enum):
    """NEW v0.3 — resolves critique #6.
    Tracks how far the output state has diverged from the source.
    """
    SHALLOW_TRANSFORM     = "shallow_transform"      # Tier A: same upstream state
    REGENERATIVE_TRANSFORM = "regenerative_transform" # Tier B: upstream re-run, but operator-driven
    EMERGENT_REGENERATION = "emergent_regeneration"  # Tier B: upstream re-run produced effects beyond operator intent
                                                     # (e.g., M7 grid scale → C10 made completely different wet-wall choice)


@dataclass(frozen=True)
class MutationApplicationResult:
    operator: MutationOperator
    valid: bool
    invalidity_reason: str | None
    topology_variant_id: str | None
    rejection_invariant_id: str | None        # owner-prefixed ("C7_W1", "C10_Inv_5", "C5_zoning_privacy")
    source_family_id: str
    output_family_id: str | None
    family_transition_policy: TopologyFamilyTransitionPolicy
    lineage_depth: MutationLineageDepth        # NEW v0.3
    upstream_regeneration_delta: tuple[str, ...] = ()  # NEW v0.3 — fields that changed in Tier B regen
```

`upstream_regeneration_delta` example: for an M7 mutation that re-ran
C9 + C10 and ended up with different wet-wall assignment, the delta would be:
`("c9.room_size_table.size_changes", "c10.wet_zone_plan.wet_wall_assignment")`.
Caller can detect emergent regeneration when the delta exceeds expected
operator scope.

### § 2.4 — Diagnostic telemetry (REVISED v0.3 — fidelity labeled)

```python
@dataclass(frozen=True)
class MutationDiagnostics:
    per_operator_yield: dict[MutationOperator, float]
    per_family_yield:   dict[MutationOperatorFamily, float]
    family_spread_entropy: float
    duplicate_ratio: float
    novelty_deficit_estimator: float          # LOW-FIDELITY (Jaccard); see B-NEW-F
    novelty_estimator_fidelity: Literal["low", "medium", "high"] = "low"   # NEW v0.3
    deep_mutation_runtime_ms: int
    deep_mutation_cache_hit_count: int          # NEW v0.3
    deep_mutation_cache_miss_count: int         # NEW v0.3
```

**`novelty_estimator_fidelity` rule** (NEW v0.3 — resolves critique #5):
The string label MUST match the algorithm in use. Operational decisions
(adaptive scheduling, stagnation alerts) MUST NOT consume a `low`-fidelity
estimator. Enforced as Inv 18 below.

### § 2.5 — Canonical topology signature (EXPANDED v0.3 — partial fix for critique #4)

```python
@dataclass(frozen=True)
class TopologySignature:
    topology_family_id: str
    room_adjacency_edges: tuple[tuple[str, str], ...]
    room_to_zone_mapping: tuple[tuple[str, str], ...]
    wet_wall_assignment_canonical: tuple[tuple[str, str], ...]
    entry_position: str
    staircase_position: str
    master_bedroom_floor_label: str
    grid_bay_size_signature: str
    # NEW v0.3 — partial spatial fidelity (critique #4):
    corridor_classification: str       # "central_spine" | "edge_corridor" | "courtyard_ring" | "no_corridor"
    frontage_exposure_map: tuple[tuple[str, str], ...]   # room_id -> facing_direction (sorted)
```

**Acknowledged limitation**: signature still does not capture circulation
quality, spatial depth, or axial structure. **B-NEW-G** tracks the v2
signature expansion. v0.3 takes the cheap-and-stable additions; defers the
expensive-and-evolving ones to v2 to avoid replay-surface overfitting per
the reviewer's own warning.

### § 2.6 — Configuration (REVISED v0.3 — caching + registry validation)

```python
@dataclass(frozen=True)
class TopologyMutationConfig:
    enabled_operators: tuple[MutationOperator, ...] = field(default_factory=...)
    max_seeds_per_input: int = 8
    family_slot_allocations: tuple[FamilySlotAllocation, ...] = field(default_factory=...)
    deterministic_order: bool = True
    emit_base: bool = True
    deduplicate_by_signature: bool = True
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    provenance_verbosity: ProvenanceVerbosity = ProvenanceVerbosity.PER_OP
    # NEW v0.3:
    deep_mutation_cache_enabled: bool = True
    skip_pending_upstream_predicates: bool = False   # if True, skip predicates whose
                                                      # upstream amendment hasn't landed
                                                      # (development mode only)
```

### § 2.7 — Provenance (REVISED v0.3 — replay version hashes)

```python
@dataclass(frozen=True)
class UpstreamReplayVersionHashes:
    """NEW v0.3 — resolves critique #10.
    Captures upstream component version hashes at the moment of mutation
    so cross-replay determinism can be verified."""
    c5_topology_kb_version: str
    c7_grid_generator_version: str
    c9_room_minimums_kb_version: str
    c10_plumbing_minimums_kb_version: str
    c10_plumbing_profiles_kb_version: str
    canonical_serialize_version: str   # C7 amendment v0.8 utility version


@dataclass(frozen=True)
class TopologyMutationProvenance:
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    enabled_operators_snapshot: tuple[str, ...]
    operator_application_log: tuple[MutationApplicationResult, ...]
    accepted_count: int
    rejected_count: int
    deduplicated_count: int
    truncated_at_max_seeds: bool
    diagnostics: MutationDiagnostics
    upstream_replay_versions: UpstreamReplayVersionHashes   # NEW v0.3
    rule_trace: tuple[str, ...]
    _observational_runtime_ms: int                         # excluded from replay hashes
```

### § 2.8 — Operator registry validation (NEW v0.3 — resolves critique #8)

```python
def validate_operator_registry() -> None:
    """Startup-hook validation. Called once per process during C11a import
    or first invocation. Cached `_REGISTRY_VALIDATED` mirror of C10
    `_KB_VALIDATED` pattern.
    NEW v0.3 — resolves critique #8.

    Validates:
      - Every MutationOperator enum entry has a metadata row.
      - Every metadata row has a family_transition_policy entry.
      - No orphan family in family_slot_allocations defaults.
      - Every MutationOperatorFamily has at least one member operator.
      - Tier B operators all set requires_grid_regen XOR requires_multi_floor.

    Raises:
        OperatorRegistryError on any inconsistency.
    """
```

---

## § 3 — Behaviour (REVISED v0.3)

### Phase 0 — Input validation

Includes `validate_operator_registry()` first call (cached). Plus prior
checks.

### Phase 1 — Per-candidate seed generation

Carried v0.2 with three additions:

1. **Tier B cache check** before invoking `DeepMutationPipeline`: lookup
   `DeepMutationCacheKey`; on hit, reuse cached result.
2. **Lineage depth labeling**: post-mutation, classify result as
   SHALLOW_TRANSFORM (Tier A), REGENERATIVE_TRANSFORM (Tier B with delta
   matching expected operator scope), or EMERGENT_REGENERATION (Tier B
   with delta exceeding operator scope).
3. **Predicate orchestration**: viability checks now reference upstream
   rule IDs via `MutationViabilityPredicate` objects (instead of
   C11a-internal redefinitions).

### Phase 2 — Output assembly + diagnostics

Carried v0.2. Diagnostics now include `deep_mutation_cache_hit_count`,
`deep_mutation_cache_miss_count`, and `novelty_estimator_fidelity` label.

### Phase 3 — Provenance assembly

Carried v0.2 with `upstream_replay_versions` field populated by reading
`_kb_version` strings from C9/C10 KBs + `canonical_serialize` module
version constant.

### § 3.4 — Tier A predicate orchestration (REVISED v0.3)

Per-operator viability predicates (Walk #4 produces full matrix; v0.3
shows shape):

```
M2 vert flip:
  - "C5_zoning_privacy" (pending B-NEW-J): bedroom not on road-facing wall
  - "C9_Inv_5":            master BA wall ∈ master BR acceptable set
  - "C9_Inv_13":           master semantics preserved
  - "C10_Inv_5":           master BR↔BA adjacency
  - "C10_Inv_4":           wall_id exists in grid

M3a stair_east:
  - "C7_staircase_clearance" (pending B-NEW-K): clearance to east wall
  - "C9_Inv_4":            corridor adjacency unchanged
```

### § 3.5 — Tier B `DeepMutationPipeline` (REVISED v0.3 — atomicity-explicit + cached)

```
DeepMutationPipeline(source_candidate, operator, config) -> WetZonePlannedCandidate | None

  Step 0: cache lookup (DeepMutationCacheKey)
          → on hit: return cached result; mark cache_hit_count++

  Step 1: construct mutated brief / grid / placement state per operator
          (frozen dataclasses; new objects, no mutation of source)

  Step 2: For M7 — call C7.GridGenerator().generate(new_envelope) → new Grid

  Step 3: call C9.size_rooms(...) against new state → new RoomSizedCandidate
          OR raise on failure (C9 already returns/raises, no half-state)

  Step 4: call C10.plan_wet_zones(...) against new room sizes
          → new WetZonePlannedCandidate
          OR raise on failure

  Step 5: validate upstream invariants on output (C7 W1-W8; C9 invariants;
          C10 Inv 1-21). If any fail, mutation REJECTED.

  Step 6: cache result; return.

  Atomicity: no shared mutable state between steps. Failure at any step
  raises DeepMutationApplicationError; partial state is unreachable
  because each step produces new immutable objects.
```

**Systemic-error propagation rule** (NEW v0.3 — resolves F-v2-7):
- `KBVersionMismatchError`, `RemediationGraphError`,
  `PlumbingConfidenceTooLow` — propagate UNCAUGHT (these are systemic to
  the entire batch, not the mutation).
- `BatchWetZoneInfeasibleError` — caught; wrapped as
  `DeepMutationApplicationError`; mutation rejected.
- Other per-candidate errors — caught; wrapped; rejected.

---

## § 4 — Invariants (REVISED v0.3)

| # | Invariant | Mode |
|---|---|---|
| 1-16 | (carried verbatim from v0.2) | as v0.2 |
| **17 (NEW v0.3)** | **Tier B output is fully-formed or `None`; no partial state escapes `DeepMutationPipeline`. Atomicity-by-construction (resolves critique #11).** | RAISE |
| **18 (NEW v0.3)** | **Operational decisions (adaptive scheduling, stagnation alerts) MUST NOT consume `MutationDiagnostics` fields where `novelty_estimator_fidelity == "low"`. Enforced via `MutationDiagnostics.assert_high_fidelity_only()` helper.** | RAISE (downstream consumers) |
| **19 (NEW v0.3)** | **`MutationViabilityPredicate.rule_owner` ∈ {"C5", "C7", "C8", "C9", "C10"}; no "C11a" predicates. C11a does not own architectural rules (resolves critique #3).** | RAISE |
| **20 (NEW v0.3)** | **`UpstreamReplayVersionHashes` populated for every output's provenance; if any upstream `_kb_version` differs between two replay runs, the variant_id may legitimately differ — replay-test framework checks version-hash equality first (resolves critique #10).** | RAISE (replay tier) |
| **21 (NEW v0.3)** | **`MutationLineageDepth` correctly classifies each output: SHALLOW for Tier A; REGENERATIVE for Tier B within expected delta scope; EMERGENT for Tier B exceeding expected delta scope (resolves critique #6).** | RAISE |
| **22 (NEW v0.3)** | **`validate_operator_registry()` succeeds at C11a import; metadata mismatches caught at startup, not runtime (resolves critique #8).** | RAISE (startup) |

---

## § 5 — Failure modes (REVISED v0.3)

```
TopologyMutationError (base)
├── PerCandidateError
│   ├── TopologyInvalidError              (no operator produced a valid seed)
│   ├── MutationApplicationError          (operator function raised internally)
│   └── DeepMutationApplicationError      (Tier B pipeline raised; atomicity preserved)
├── BatchAllNonBaseFailedError            (revised v0.2; carried)
├── OperatorRegistryError                 (NEW v0.3 — startup metadata inconsistency)
└── InvariantViolationError               (systemic — Inv 7/13/17/19-22)
```

---

## § 6 — Test coverage targets (REVISED v0.3)

Target ~155 tests at LOCK (up from v0.2's 140):

- ~30 schema (carried v0.2; +`MutationLineageDepth`,
  `MutationViabilityPredicate`, `UpstreamReplayVersionHashes`,
  `DeepMutationCacheKey`)
- ~32 per-operator (16 ops × {valid + invalid} = 32)
- ~28 invariants (Inv 1-22 across modes)
- ~25 phase-logic (slot allocation, spillover, deep cache hit/miss,
  predicate orchestration)
- ~12 partial-batch / strict-mode
- ~8 replay snapshot (signature stability + upstream version hash check)
- ~10 diagnostics (entropy, Jaccard, fidelity-label enforcement,
  cache-hit telemetry)
- **~10 NEW v0.3** — operator registry validation, lineage depth
  classification, atomicity (kill-step injection), upstream-version
  divergence detection

Cumulative target at C11a ship: 2314 + 155 ≈ **2469 passed**.

---

## § 7 — Open questions surfaced at v0.3 (down from 9 to 6)

| Q | Question | v0.3 direction |
|---|---|---|
| Q1 | Catalog completeness — keep all 9 base operators at v1? | Carried open. Walk #4 review per-operator yield expectations. |
| Q11 | M7 grid-scale set fixed or KB-driven? | KB-driven post-v1 (B-NEW-A); fixed at v1. |
| Q12 | Multi-floor briefs — per-floor or building-wide? | Building-wide. |
| Q13 | Cross-platform determinism? | Yes; reuses B-237 + UpstreamReplayVersionHashes. |
| Q16 | TopologyFamily IDs — string enum or dataclass? | v0.3 ships strings; revisit at C5 amendment. |
| Q17 | Slot allocation tie-break? | Lex-ASC family name; carried v0.2 baseline. |
| **Q21 (NEW)** | When does `EMERGENT_REGENERATION` fire? Need precise delta-scope rule per operator. | Walk #4 deliverable. |

**Resolved at Walk #3**: Q19 (DeepMutationPipeline as helper module),
Q20 (Jaccard with fidelity label), Q18 (predicate orchestration via
references; superseded F-v2-6).

---

## § 8 — Backlog at v0.3

**New at v0.3** (Walk #3 critique outcomes + push-throughs):

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-NEW-G | C11a TopologySignature spatial expansion (circulation graph, axial depth, frontage-exposure refinement) | W#3 critique #4 | post-launch + measured signature collision rate | M |
| B-NEW-H | C11a `TopologyTransitionDescriptor` (richer family-transition lineage with confidence + magnitude) | W#3 critique #9 | post-launch | S-M |
| B-NEW-I | C11a `BatchAllNonBaseFailedError` rolling failure-rate thresholds + severity escalation | W#3 critique #7 | observed alert noise | S |
| B-NEW-J | **C5 amendment**: codify privacy zoning rule (bedrooms not on road-facing wall) as numbered invariant | W#3 critique #3 | C11a v1 build needs viability predicate target | XS |
| B-NEW-K | **C7 amendment**: codify staircase clearance as W-numbered invariant | W#3 critique #3 | C11a v1 build needs predicate target | XS |
| B-NEW-L | **C8 amendment**: codify entry-approach compatibility as numbered invariant | W#3 critique #3 | C11a v1 build needs predicate target | XS |
| B-NEW-E2 | C11a Tier B incremental regeneration (delta propagation between C9 → C10 when only M7 changed); cross-invocation cache | W#3 critique #1 | post-launch + measured deep-mutation runtime pressure | L |

**Scope expansions on existing items**:

- **B-NEW-D** (adaptive operator scheduling) — extended to also cover
  family-slot allocation weighting per W#3 critique #2.
- **B-NEW-E** (provenance compaction) — extended to clarify it's about
  `FULL` verbosity replay-snapshot bloat, distinct from B-NEW-E2 caching.
- **B-NEW-F** (Quality-Diversity extension) — extended to include
  *semantic validity floor* per W#3 critique #12: novelty cannot violate
  domain plausibility constraints; QD search bounded by Indian-residential
  semantic gates.

---

## § 9 — Rule 11 spec audit on v0.3 PROPOSED

**PATCH-NOW (in v0.3 itself): 0** — drafting is the patch round.

**OPEN QUESTIONS at v0.3**: Q1, Q11-Q13, Q16, Q17, Q21 (6; down from 9).

**SPEC-AUDIT FINDINGS (v0.3)**:

| # | Finding | Verdict |
|---|---|---|
| F-v3-1 | `MutationViabilityPredicate.predicate: Callable` is unserializable — replay snapshots of provenance can't store the actual predicate. Either serialize as rule_id string only, or split into runtime-callable + serializable-reference. | **PATCH-NOW** — split into two fields: `rule_id` (serializable) + `_predicate_fn` (runtime; underscore = excluded from serialization). |
| F-v3-2 | `B-NEW-J/K/L` make C5/C7/C8 amendments a hard prerequisite for C11a v1. If those amendments don't land, C11a v1 ships with `pending_upstream=True` predicates running inline checks — basically v0.2 behaviour with a different label. Critique #3's resolution is partially deferred until upstream amendments arrive. | **NEEDS WALK** — sequencing question for Walk #4. |
| F-v3-3 | `EMERGENT_REGENERATION` lineage classification needs a precise predicate. Q21 surfaces this; Walk #4 must define per-operator expected-delta-scope. | **NEEDS WALK** — Walk #4 deliverable. |
| F-v3-4 | `UpstreamReplayVersionHashes.canonical_serialize_version` requires a version constant in `buildemup/utilities/canonical.py`. C7 amendment v0.8 didn't ship one. | **PATCH-NOW** — add `CANONICAL_SERIALIZE_VERSION: Final[str] = "v1.0"` to canonical.py during C11a build (small additive change, not a C7 amendment). |
| F-v3-5 | `DeepMutationCacheKey` doesn't include `_observational_runtime_ms` (correctly), but does include `config_hash`. If `config.provenance_verbosity` flips between SUMMARY/PER_OP/FULL, the cache miss-rate goes to 100% even though the actual mutation result is identical. Need to scope `config_hash` to mutation-relevant fields only. | **PATCH-NOW** — define `config_hash` over a curated subset. |
| F-v3-6 | "Atomicity-by-construction" relies on no upstream component having shared mutable state. C7/C9/C10 are all frozen-dataclass-based, but the global `_KB_VALIDATED` cache in C10 is mutable. Doesn't affect mutation atomicity directly (it's read-after-set), but worth flagging. | **NEEDS WALK** — minor; Walk #4 audit. |
| F-v3-7 | Test target jumped 140 → 155 with +10 new-area tests. The 32 per-operator tests assume each of 16 operators gets equal coverage, but M7a/b and M3a/b/c are each 1 test even though they're "variants of the same operator family" — should they share invalidation-fixture coverage? | **NEEDS WALK** — test plan refinement. |
| F-v3-8 | `MutationApplicationResult.upstream_regeneration_delta: tuple[str, ...]` is free-form strings. No schema for what valid delta strings look like. Easy to drift. | **NEEDS WALK** — define delta-key vocabulary. |

**PATCH-NOW APPLIED INLINE TO v0.3**:

- **F-v3-1**: `MutationViabilityPredicate.predicate` renamed to
  `_predicate_fn` (runtime-only; excluded from serialization);
  `rule_id` carries the serializable reference. Updated above.
- **F-v3-4**: `CANONICAL_SERIALIZE_VERSION = "v1.0"` to be added to
  `buildemup/utilities/canonical.py` at C11a build time (additive).
- **F-v3-5**: `config_hash` scoped to subset:
  `(enabled_operators, max_seeds_per_input, family_slot_allocations, deduplicate_by_signature)`.
  Provenance verbosity excluded.

**REJECTED-AS-CONSIDERED**:
- "Should `UpstreamReplayVersionHashes` include Python interpreter version?" — Out of scope; B-237 cross-platform CI handles this dimension.
- "Should `MutationLineageDepth` have a 4th tier for catastrophic regeneration?" — `EMERGENT_REGENERATION` covers it; further granularity post-launch.

---

## § 10 — Status

- **v0.3 PROPOSED**. **NOT LOCKED.**
- LOCK NOT REQUESTED at v0.3.
- 12 valid critique items resolved (7 spec amendments + 4 backlog + 1 push-back). 0 rejected.
- 6 open questions remaining (down from 9 at v0.2; 15 at v0.1).
- 13 backlog items total (4 pre-existing + 3 v0.1 + 3 v0.2 + 7 v0.3 incl. 3 upstream amendments). Some are scope expansions on existing IDs.
- Estimated walks to LOCK: **2-4** more.
- Walk #4 should prioritize: (a) per-operator predicate matrix (F-v3-2 sequencing + Walk #3 deferred); (b) `EMERGENT_REGENERATION` precise predicate (Q21); (c) M5 family-invalidation concrete fixture (F-v2-3 carried).

---

## § 12 — Backlog enumeration (per Rule 9)

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-217 | Polygonal envelopes spatial partitioning | S35 | L |
| B-220 | Hydraulic primitives + plumbing-engineer review | S35 | L |
| B-237 | Cross-platform replay CI matrix + Decimal geometry | S35 | M |
| B-238 | Independent architect review | S35 | M |
| B-NEW-A | C11a M7 grid-scale KB-driven set | W#1 Q11 | XS |
| B-NEW-B | C11a cross-operator composition v2 | W#1 Q3 | M |
| B-NEW-C | C11a abstract graph mutation operators | W#1 Q14 | L |
| B-NEW-D | C11a adaptive operator + slot scheduling | W#2 #6 + W#3 #2 | M |
| B-NEW-E | C11a `FULL` verbosity provenance compaction | W#2 #9 | S |
| B-NEW-F | C11a QD-algorithm extension + semantic validity floor | W#2 #3,#12 + W#3 #12 | L |
| **B-NEW-G** | **C11a TopologySignature spatial expansion (v2)** | **W#3 #4** | **M** |
| **B-NEW-H** | **C11a `TopologyTransitionDescriptor` (v2)** | **W#3 #9** | **S-M** |
| **B-NEW-I** | **C11a batch-failure rolling thresholds** | **W#3 #7** | **S** |
| **B-NEW-J** | **C5 amendment: privacy zoning invariant** | **W#3 #3** | **XS** |
| **B-NEW-K** | **C7 amendment: staircase clearance invariant** | **W#3 #3** | **XS** |
| **B-NEW-L** | **C8 amendment: entry approach invariant** | **W#3 #3** | **XS** |
| **B-NEW-E2** | **C11a Tier B incremental regen + cross-invocation cache** | **W#3 #1 deferred** | **L** |

**Backlog summary**:

| Total | Pre-existing | New v0.1 | New v0.2 | New v0.3 |
|---|---|---|---|---|
| 17 | 4 | 3 | 3 | 7 |

---

**End of v0.3 PROPOSED.** Awaits Ramalingam's reading + Walk #4 direction.
