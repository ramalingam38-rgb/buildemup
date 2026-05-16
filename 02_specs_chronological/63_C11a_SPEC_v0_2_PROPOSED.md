# C11a — Topology Mutation Layer — SPEC v0.2 PROPOSED

**Component**: 11a (canonical Track 3 numbering — paired with C11b NSGA-II)
**Status**: v0.2 PROPOSED. **NOT LOCKED.** Supersedes v0.1 PROPOSED.
**Authority**: S37 Walk #2 author's draft. PENDING Ramalingam adjudication.
**Authored**: S37 Walk #2, post external critique walk on v0.1.

---

## § 0 — Architectural notes (REVISED v0.2)

C11a sits between C10 (Wet-Zone Stack Planner) and C11b (NSGA-II Local
Refinement). Its job is **topology-level seed generation**: produce a
diverse, valid population of candidate seeds per input topology by
applying domain-specific mutation operators, validating each against
HARD constraints, and emitting valid seeds for C11b to refine.

**Pipeline position**:
```
C10 → C11a (THIS) → C11b → C12 → C13 → C14
```

### Two-tier mutation architecture (NEW v0.2 — resolves F-v1-1 + F-v1-2)

Per Walk #2 critique #1 + #2: shallow and deep operators have
fundamentally different cost profiles; collapsing them into one phase
collapsed architectural layering. v0.2 splits them explicitly.

**Tier A — Shallow topology transforms** (M1, M2, M3a/b/c, M4, M5,
M9a/b/c/d). Operator-local logic; targeted invariant subset re-validation;
fast path. Runtime per attempt: ~10ms (estimated).

**Tier B — Regenerative topology transforms** (M6, M7a/b, M8). Mutation
triggers `DeepMutationPipeline`: C7 grid regen (M7 only) → C9 size regen
→ C10 wet-zone re-plan. Validate via re-running the produced candidate's
own upstream invariants. Slow path; runtime ~100-500ms per attempt
(estimated; calibrate via B-219).

The pipeline is not C11a's invariant-checker; it is C11a's
**state-producer** for deep operators. C11a delegates re-validation
back to the upstream components that own those invariants (see Legality
Responsibility Matrix below).

### Mutation Legality Responsibility Matrix (NEW v0.2 — resolves critique #11)

| Layer | Owns | Authoritative for |
|---|---|---|
| C5 | Topology family taxonomy | Family classification (Central Spine / Courtyard / Strip) |
| C7 | Grid invariants W1–W8 | Structural feasibility |
| C9 | Room sizing invariants | Liveability minima per room category |
| C10 | Wet-zone invariants Inv 1–21 | Plumbing feasibility |
| **C11a (THIS)** | **Mutation transform application + family-transition policy** | **Mutation operator validity (does the operator produce a sane state?)** |

**Authority rules**:
- C11a **cannot override** upstream invariants. A mutation that produces
  state violating C7/C9/C10 invariants is REJECTED at C11a.
- C11a **can add** C11a-only invariants on the mutation transform itself
  (e.g., M2 vertical-flip privacy check) that don't exist upstream.
- C11a **delegates** re-validation of deep-mutation outputs to the layer
  that owns each invariant (C7/C9/C10 each verify their own).

### What C11a IS

- Deterministic application of a fixed mutation operator catalog
- HARD-constraint validation per produced seed
- Per-input-candidate seed multiplication (1 input → ≤ N valid seeds)
- Diagnostic telemetry on mutation yield + topology diversity (NEW v0.2 critique #3, #6, #12)
- Forward-compat schema for future operator composition (NEW v0.2 critique #7)

### What C11a is NOT

- **NOT NSGA-II Pareto search.** C11b owns multi-objective optimization.
- **NOT room placement geometry.** Per-room x/y/w/h finalization is C12.
- **NOT scoring or evaluation.** No seed gets a quality score in C11a.
  *Diagnostic telemetry is not scoring* — it tracks operational health,
  doesn't rank seeds (per critique #12 reviewer's own framing).
- **NOT user-facing.** No rendering. C16 is the renderer.
- **NOT crossover.** Composing two seeds is C11b's job (NSGA-II crossover).
- **NOT learning from prior runs.** Operator selection is config-driven.

### Architectural divergence acknowledgment (carried v0.1)

EvoArch (Wong & Chan, 2009) uses abstract adjacency-matrix mutations.
C11a takes the opposite approach: a fixed catalog of 9 domain-specific
operators drawn from Indian residential typology patterns. This sacrifices
generality for semantic validity. **B-NEW-C** tracks introducing optional
abstract graph mutations as secondary operators post-launch.

---

## § 1 — Walk-resolved scope (REVISED v0.2)

| Q | Resolution | Walk |
|---|---|---|
| Q4 | HARD constraint validation: hybrid Tier A (operator-local + curated invariant subset) / Tier B (re-run upstream regen pipeline + invariant re-validation by owner). | Walk #2 (critique #1) |
| Q3 | Single-operator only at v1. **Schema future-proofs composition**: `applied_operators: tuple[MutationOperator, ...]` (always len==1 at v1). | Walk #2 (critique #7) |
| Q5 | Deterministic order: per-family slot allocation with lex-ASC fallback for spillover. **NOT pure lex-ASC truncate** (critique #8). | Walk #2 (critique #8) |
| Q7 | No filtering at C11a output. C11b is the sole search authority. | Walk #2 carry |
| Q8 | `topology_variant_id` = SHA256-12char-prefix of `canonical_serialize(TopologySignature)`. Signature surface defined explicitly (§ 2.5). | Walk #2 (critique #5) |
| Q9 | Invalid mutations: surface in `provenance.operator_application_log` with `valid=False` + `invalidity_reason` + `rejection_invariant_id`. NOT emitted as outputs. | Walk #2 carry |
| Q14 | v1 stays domain-specific. Diversity diagnostics (entropy, family-spread, yield) added at v0.2 to detect under-exploration. | Walk #2 (critique #3, #12) |
| Q15 | M0_BASE does NOT count against `max_seeds_per_input`. Bound applies to mutated seeds only. | Walk #2 carry |

---

## § 2 — Contract (REVISED v0.2)

```python
def mutate_topologies(
    wet_zoned_candidates: tuple[WetZonePlannedCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    *,
    config: TopologyMutationConfig | None = None,
) -> tuple[MutatedTopologyCandidate, ...]:
    """C11a entry point. Per-candidate semantics mirror C9/C10 § 14.40."""
```

### § 2.1 — Operator enum (carried v0.1)

```python
class MutationOperator(str, Enum):
    M0_BASE         = "m0_base"
    M1_HORIZ_FLIP   = "m1_horiz_flip"
    M2_VERT_FLIP    = "m2_vert_flip"
    M3A_STAIR_EAST  = "m3a_stair_east"
    M3B_STAIR_WEST  = "m3b_stair_west"
    M3C_STAIR_NE    = "m3c_stair_ne_corner"
    M4_CORRIDOR_INV = "m4_corridor_inv"
    M5_ZONE_SWAP    = "m5_public_private_swap"
    M6_WET_ROTATE   = "m6_wet_wall_rotate"
    M7A_GRID_3_3    = "m7a_grid_scale_3_3"
    M7B_GRID_2_7    = "m7b_grid_scale_2_7"
    M8_VERT_REARR   = "m8_master_floor_swap"
    M9A_ENTRY_CTR   = "m9a_entry_ne_center"
    M9B_ENTRY_W     = "m9b_entry_ne_corner_w"
    M9C_ENTRY_E     = "m9c_entry_ne_corner_e"
    M9D_ENTRY_OFF   = "m9d_entry_offset_ne"


class MutationTier(str, Enum):
    """NEW v0.2 — Tier A / Tier B split (critique #1, #2)."""
    SHALLOW       = "shallow"        # operator-local, fast
    REGENERATIVE  = "regenerative"   # triggers DeepMutationPipeline


class MutationOperatorFamily(str, Enum):
    """NEW v0.2 — for slot allocation (critique #8)."""
    BASE      = "base"           # M0
    FLIP      = "flip"           # M1, M2
    STAIRCASE = "staircase"      # M3a, M3b, M3c
    CORRIDOR  = "corridor"       # M4
    ZONE      = "zone"           # M5
    WET_WALL  = "wet_wall"       # M6
    GRID      = "grid"           # M7a, M7b
    VERTICAL  = "vertical"       # M8
    ENTRY     = "entry"          # M9a-d
```

**Operator metadata** (registered as a Final dict module constant):

```python
@dataclass(frozen=True)
class MutationOperatorMetadata:
    operator: MutationOperator
    tier: MutationTier
    family: MutationOperatorFamily
    family_transition_policy: TopologyFamilyTransitionPolicy
    requires_multi_floor: bool        # M8 only
    requires_grid_regen: bool         # M7 only
```

### § 2.2 — Topology family transition policy (NEW v0.2 — critique #4)

```python
class TopologyFamilyTransitionPolicy(str, Enum):
    PRESERVES_FAMILY    = "preserves_family"
    TRANSFORMS_FAMILY   = "transforms_family"
    INVALIDATES_FAMILY  = "invalidates_family"


# Per-operator family-transition table (Walk #2 first pass; revisit at #3-#4):
_OPERATOR_FAMILY_POLICY: Final[dict[MutationOperator, TopologyFamilyTransitionPolicy]] = {
    MutationOperator.M0_BASE:         TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M1_HORIZ_FLIP:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M2_VERT_FLIP:    TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M3A_STAIR_EAST:  TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M3B_STAIR_WEST:  TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M3C_STAIR_NE:    TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M4_CORRIDOR_INV: TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY,  # spine→strip
    MutationOperator.M5_ZONE_SWAP:    TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY,
    MutationOperator.M6_WET_ROTATE:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M7A_GRID_3_3:    TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M7B_GRID_2_7:    TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M8_VERT_REARR:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M9A_ENTRY_CTR:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M9B_ENTRY_W:     TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M9C_ENTRY_E:     TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M9D_ENTRY_OFF:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
}
```

### § 2.3 — Application result + candidate dataclasses (REVISED v0.2)

```python
@dataclass(frozen=True)
class MutationApplicationResult:
    operator: MutationOperator
    valid: bool
    invalidity_reason: str | None
    topology_variant_id: str | None
    rejection_invariant_id: str | None        # owner-prefixed (e.g. "C7_W1", "C10_Inv_5")
    source_family_id: str
    output_family_id: str | None              # may differ for TRANSFORMS_FAMILY operators
    family_transition_policy: TopologyFamilyTransitionPolicy


@dataclass(frozen=True)
class MutatedTopologyCandidate:
    """Output unit — REVISED v0.2 with composition-future-proof tuple."""
    source_candidate: WetZonePlannedCandidate
    applied_operators: tuple[MutationOperator, ...]   # v1 invariant: len==1
    topology_variant_id: str
    application_results: tuple[MutationApplicationResult, ...]   # v1: len==1
    provenance: TopologyMutationProvenance

    def __post_init__(self) -> None:
        if len(self.applied_operators) != 1:
            raise ValueError(
                f"v1 requires exactly 1 operator per output; "
                f"got {len(self.applied_operators)}. Multi-operator "
                f"composition deferred to B-NEW-B."
            )
```

### § 2.4 — Diagnostic telemetry (NEW v0.2 — critique #3, #6, #12)

```python
@dataclass(frozen=True)
class MutationDiagnostics:
    """Diagnostic-only metrics. NOT used for scoring or selection.
    Tracks operational health of the mutation layer.
    """
    per_operator_yield: dict[MutationOperator, float]    # accepted / total
    per_family_yield:   dict[MutationOperatorFamily, float]
    family_spread_entropy: float                          # Shannon over output families
    duplicate_ratio: float                                # deduped / accepted
    novelty_deficit_estimator: float                      # 1 - avg signature distance among emitted seeds
    deep_mutation_runtime_ms: int                         # observational; NOT in replay hashes
```

### § 2.5 — Canonical topology signature (NEW v0.2 — critique #5)

```python
@dataclass(frozen=True)
class TopologySignature:
    """Canonical signature surface for deduplication + variant-id derivation.
    Excludes runtime/observational fields by construction.
    """
    topology_family_id: str
    room_adjacency_edges: tuple[tuple[str, str], ...]    # sorted lex-ASC of canonical pair
    room_to_zone_mapping: tuple[tuple[str, str], ...]    # sorted by room_id
    wet_wall_assignment_canonical: tuple[tuple[str, str], ...]  # sorted by room_id
    entry_position: str                                   # enum value as string
    staircase_position: str
    master_bedroom_floor_label: str
    grid_bay_size_signature: str                          # rounded to 1dp via canonical_serialize
```

`topology_variant_id = SHA256(canonical_serialize(signature))[:12]`. Per
critique #5 reviewer's recommendation; integrates with C7 amendment v0.8
`canonical_serialize` utility.

### § 2.6 — Configuration + Provenance (REVISED v0.2)

```python
class ProvenanceVerbosity(str, Enum):
    """NEW v0.2 — tiered provenance modes (critique #9)."""
    SUMMARY = "summary"      # accepted/rejected/dedup counts only
    PER_OP  = "per_op"       # per-operator counts + reasons (default)
    FULL    = "full"         # every attempt logged with full state


@dataclass(frozen=True)
class FamilySlotAllocation:
    """NEW v0.2 — per-family slot reservation (critique #8)."""
    family: MutationOperatorFamily
    reserved_slots: int = 1


@dataclass(frozen=True)
class TopologyMutationConfig:
    enabled_operators: tuple[MutationOperator, ...] = field(
        default_factory=lambda: tuple(op for op in MutationOperator)
    )
    max_seeds_per_input: int = 8
    family_slot_allocations: tuple[FamilySlotAllocation, ...] = field(
        default_factory=lambda: (
            FamilySlotAllocation(MutationOperatorFamily.BASE,      1),
            FamilySlotAllocation(MutationOperatorFamily.FLIP,      1),
            FamilySlotAllocation(MutationOperatorFamily.STAIRCASE, 1),
            FamilySlotAllocation(MutationOperatorFamily.CORRIDOR,  1),
            FamilySlotAllocation(MutationOperatorFamily.ZONE,      1),
            FamilySlotAllocation(MutationOperatorFamily.WET_WALL,  1),
            FamilySlotAllocation(MutationOperatorFamily.GRID,      1),
            FamilySlotAllocation(MutationOperatorFamily.VERTICAL,  1),
            FamilySlotAllocation(MutationOperatorFamily.ENTRY,     1),
        )
    )
    deterministic_order: bool = True
    emit_base: bool = True
    deduplicate_by_signature: bool = True
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    provenance_verbosity: ProvenanceVerbosity = ProvenanceVerbosity.PER_OP


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
    rule_trace: tuple[str, ...]
    _observational_runtime_ms: int            # excluded from replay hashes
```

---

## § 3 — Behaviour (REVISED v0.2)

### Phase 0 — Input validation

Verify input non-empty (or return empty tuple if input empty), config sane,
slot allocations sum ≤ `max_seeds_per_input`.

### Phase 1 — Per-candidate seed generation (REVISED v0.2)

For each `WetZonePlannedCandidate`:

1. If `config.emit_base`: emit `M0_BASE` (always valid; uses BASE family slot).

2. **Per-family slot allocation** (NEW v0.2 — critique #8):
   - For each family in lex-ASC of family name (deterministic):
     - Identify enabled operators in this family in lex-ASC of operator name
     - Apply each in order; first `reserved_slots[family]` valid mutations fill the family's quota
     - If a family produces fewer valid mutations than its slot count: surplus slots return to a global "spillover" pool
   - **Spillover allocation**: surplus slots assigned to next family in lex-ASC family order with surplus production

3. **Per-mutation application**:
   - Determine `tier = OPERATOR_METADATA[op].tier`
   - **Tier A (SHALLOW)**: apply operator-local transform; validate via curated invariant subset (§ 3.4)
   - **Tier B (REGENERATIVE)**: invoke `DeepMutationPipeline` (§ 3.5); validate via re-running upstream invariants
   - If valid: compute `topology_variant_id` per § 2.5; check dedup; accept or skip
   - If invalid: log to `operator_application_log` with `rejection_invariant_id` (e.g., `"C9_Inv_6"`)

### Phase 2 — Output assembly + diagnostics

Concatenate per-candidate accept buffers in input order. Compute
`MutationDiagnostics`:

- `per_operator_yield[op] = accepted[op] / total_attempts[op]`
- `per_family_yield[fam] = sum_accepted[fam] / sum_total[fam]`
- `family_spread_entropy = -Σ p_fam * log2(p_fam)` over output families
- `duplicate_ratio = deduplicated / accepted`
- `novelty_deficit_estimator`: 1 - avg pairwise normalized signature
  Hamming distance among emitted seeds (closer to 0 = more diverse)

### Phase 3 — Provenance assembly

Per `config.provenance_verbosity`:

- `SUMMARY`: only counts in `operator_application_log` (drop reasons + state)
- `PER_OP`: counts + invalidity reasons (default)
- `FULL`: every attempt with full state snapshot

### § 3.4 — Tier A constraint set (REVISED v0.2)

Curated invariant subset per operator (Walk #3 pins exact predicates per
operator; Walk #2 establishes the ownership):

| Operator | Invariants checked (owners) |
|---|---|
| M0_BASE | none — pass-through |
| M1 horiz flip | C7 W1-W3; C9 Inv 5/13; C10 Inv 1/4 |
| M2 vert flip | privacy check (C11a-internal); C7; C9; C10 |
| M3a/b/c | staircase clearance (C11a-internal + C7); C9 Inv 4 |
| M4 corridor inv | C9 Inv 4 + adjacency; C10 Inv 5 |
| M5 zone swap | privacy + adjacency (C11a-internal); C10 Inv 5b |
| M9a-d | entry approach (C11a-internal); C8 corridor entry compatibility |

**C11a-internal invariants** (new at v0.2): privacy (bedrooms not on
road-facing wall), staircase clearance, entry approach compatibility.
Walk #3 enumerates these as numbered invariants.

### § 3.5 — Tier B `DeepMutationPipeline` (NEW v0.2 — critique #2)

```
DeepMutationPipeline(source_candidate, operator) -> WetZonePlannedCandidate | None
  Step 1: Construct mutated brief / grid / placement state per operator
  Step 2: For M7 — re-run C7 grid generation with new bay size
  Step 3: Re-run C9 size_rooms() against the new state
  Step 4: Re-run C10 plan_wet_zones() against the new room sizes
  Step 5: Validate output has no upstream invariant violations
  Step 6: Return regenerated WetZonePlannedCandidate or None
```

If any step raises an upstream error (`KBVersionMismatchError`,
`PlumbingConfidenceTooLow`, `BatchWetZoneInfeasibleError`): catch as
`DeepMutationApplicationError`; log; treat as rejected mutation.

---

## § 4 — Invariants (REVISED v0.2)

| # | Invariant | Mode |
|---|---|---|
| 1 | Every output's `source_candidate` exists in input tuple | RAISE |
| 2 | Every applied operator ∈ `config.enabled_operators` (or M0_BASE if `emit_base=True`) | RAISE |
| 3 | Per source: accepted count ≤ `config.max_seeds_per_input` (excluding M0_BASE) | RAISE |
| 4 | Output ordered: input-order outer, family lex-ASC then operator lex-ASC inner | RAISE |
| 5 | `topology_variant_id` unique within a single source's accepts | RAISE |
| 6 | If `emit_base=True`, M0_BASE always present per source candidate | RAISE |
| 7 | Mutation pure function: replay-reproducible | RAISE (replay tier) |
| 8 | HARD-constraint validation passes for every output | RAISE |
| 9 | Provenance: accepted + rejected + deduplicated = total attempts | RAISE |
| 10 | `_observational_runtime_ms` not in any replay-hash computation | RAISE (replay tier) |
| **11 (NEW v0.2)** | **`applied_operators` tuple length == 1 at v1 (composition is v2 / B-NEW-B)** | RAISE |
| **12 (NEW v0.2)** | **For each `MutationApplicationResult`: `family_transition_policy` matches `_OPERATOR_FAMILY_POLICY[operator]`** | RAISE |
| **13 (NEW v0.2)** | **TopologySignature canonical surface excludes `_observational_runtime_ms`, `derived_at`, and any provenance trace strings** | RAISE (replay tier) |
| **14 (NEW v0.2)** | **`MutationDiagnostics` is descriptive only — no field of it is read by selection or output-truncation logic** | DESCRIPTIVE |
| **15 (NEW v0.2)** | **Tier B output's upstream invariants (C7 / C9 / C10) all pass; if any fails the mutation is REJECTED with `rejection_invariant_id` set** | RAISE |
| **16 (NEW v0.2)** | **Slot allocations sum ≤ `max_seeds_per_input`; surplus from underfilled families spills deterministically** | RAISE |

---

## § 5 — Failure modes (REVISED v0.2)

```
TopologyMutationError (base)
├── PerCandidateError
│   ├── TopologyInvalidError              (no operator produced a valid seed)
│   ├── MutationApplicationError          (operator function raised internally)
│   └── DeepMutationApplicationError      (Tier B pipeline raised — NEW v0.2)
├── BatchAllNonBaseFailedError            (REVISED v0.2 — all batch produced only M0_BASE)
└── InvariantViolationError               (systemic — Inv 7/13 violated)
```

**Critique #10 resolution**: `BatchMutationFailedError` was unreachable
because M0_BASE always emits. Renamed to `BatchAllNonBaseFailedError`
and redefined: triggers when across all input candidates, **zero** non-base
mutations succeeded. Indicates C11a effectively did no useful seed
multiplication for this batch — informative rather than fatal — and may
be downgraded to a warning under `EnforcementMode.WARN`.

---

## § 6 — Test coverage targets (REVISED v0.2)

Target ~140 tests at LOCK (revised up from v0.1's hand-wavy 100):

- ~30 schema tests (operator enum, dataclasses, config validation,
  signature schema, family policy table)
- ~30 per-operator tests (one happy + one invalidating fixture per
  operator × 16 operators ≈ 30; deep operators get extra pipeline-failure
  paths)
- ~25 invariant tests (Inv 1-16 across modes)
- ~25 phase-logic tests (Phase 0 input validation, Phase 1 slot allocation
  + spillover, Phase 2 diagnostics computation, Phase 3 provenance tiers)
- ~12 partial-batch / strict-mode escalation
- ~8 deterministic-replay snapshot tests (signature stability across
  iteration order; Tier B regen reproducibility)
- ~10 diagnostic telemetry tests (Shannon entropy, novelty deficit, yield)

Cumulative target at C11a ship: 2314 + 140 ≈ **2454 passed**.

---

## § 7 — Open questions surfaced at v0.2 (down from 15 to 9)

| Q | Question | v0.2 direction |
|---|---|---|
| Q1 | Catalog completeness — keep all 9 base operators at v1? | Carried open. Walk #3 should review per-operator yield expectations. |
| Q11 | M7 grid-scale set fixed (3.0/3.3/2.7) or KB-driven? | KB-driven post-v1 (B-NEW-A); fixed at v1. |
| Q12 | Multi-floor briefs — per-floor or building-wide? | Building-wide. M8 master-floor-swap is meaningless per-floor. |
| Q13 | Determinism across Python versions / OSes? | Yes; reuses C7 amendment v0.8 utility + B-237 cross-platform CI. |
| **Q16 (NEW)** | TopologyFamily IDs — string enum or dataclass with metadata? | v0.2 ships strings; dataclass at C5 LOCK time if richer info emerges. |
| **Q17 (NEW)** | Slot allocation tie-break when two families produce equal surplus? | Lex-ASC family name. Walk #3 confirm. |
| **Q18 (NEW)** | C11a-internal invariants (privacy, staircase clearance, entry approach) — own numbering scheme or piggyback on C5/C8? | Walk #3 decide; lean toward C11a-internal numbering (`C11a_Inv_N`). |
| **Q19 (NEW)** | `DeepMutationPipeline` as a method on C11a, or a separate component? | Walk #3 decide; lean toward C11a-internal helper for cohesion. |
| **Q20 (NEW)** | `novelty_deficit_estimator` — Hamming on adjacency edges, or graph edit distance? | Hamming for v1 (cheap); graph edit distance is post-v1. |

**Resolved at Walk #2**: Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q14, Q15.

---

## § 8 — Backlog at v0.2

**Existing items affecting C11a** (carried v0.1):

| ID | Description |
|---|---|
| B-217 | Polygonal envelopes spatial partitioning |
| B-220 | Hydraulic primitives + plumbing-engineer review |
| B-237 | Cross-platform replay CI matrix + Decimal/fixed-point geometry |
| B-238 | Independent architect review |

**Proposed at v0.1 (file pending Ramalingam direction)**:

| ID | Description |
|---|---|
| B-NEW-A | C11a M7 grid-scale KB-driven set |
| B-NEW-B | C11a cross-operator composition (v2 schema-ready at v0.2) |
| B-NEW-C | C11a abstract graph mutation operators (EvoArch-style) |

**New at v0.2** (Walk #2 critique outcomes):

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-NEW-D | C11a adaptive operator scheduling (probabilistic / weighted by acceptance rate) | Critique #6 | post-launch + measured yield-skew | M |
| B-NEW-E | C11a provenance compaction for `FULL` verbosity (v2 — replay snapshot bloat fix) | Critique #9 | replay-snapshot size empirical pressure | S |
| B-NEW-F | C11a Quality-Diversity (QD) algorithm extension for novelty-driven seed generation | Critique #3 + #12 (research-validated) | post-launch + B-238 architect review | L |

---

## § 9 — Rule 11 spec audit on v0.2 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.2 itself): 0** — drafting is the patch round.

**OPEN QUESTIONS surfaced at v0.2**: Q1, Q11-Q13, Q16-Q20 (9 total; down from v0.1's 15).

**SPEC-AUDIT FINDINGS (v0.2)**:

| # | Finding | Verdict |
|---|---|---|
| F-v2-1 | `DeepMutationPipeline` reuses C7/C9/C10 entry points but doesn't define caching strategy. Re-running C9.size_rooms across 4 deep operators × 8 input candidates = 32 invocations per batch. Without memoisation this is slow. | **NEEDS WALK** — Q19-adjacent; cache strategy at Walk #3. |
| F-v2-2 | Slot allocation default = 1 per family × 9 families = 9 slots, but `max_seeds_per_input = 8`. Off-by-one: BASE consumes a slot, leaving 8 for the 8 mutated families. Either raise default to 9 or document BASE as zero-slot. | **PATCH-NOW v0.2 ITSELF** — see fix below. |
| F-v2-3 | `family_transition_policy` declared per operator but only INVALIDATES_FAMILY isn't represented in the table — every operator is PRESERVES or TRANSFORMS. If INVALIDATES never fires, it's dead enum. Either find an operator that invalidates, or drop the enum value. | **NEEDS WALK** — likely M5 zone swap can produce family-invalidation in some plot shapes; Walk #3 confirm. |
| F-v2-4 | `TopologySignature.room_adjacency_edges` is a tuple of (str, str) pairs but adjacency is symmetric — `(A, B)` == `(B, A)`. Need canonical pair ordering rule (lex-ASC of pair members). | **PATCH-NOW v0.2 ITSELF** — clarify. |
| F-v2-5 | `MutationDiagnostics.novelty_deficit_estimator` defined as Hamming distance, but Hamming distance only meaningful for fixed-length vectors. Adjacency edge sets are variable-length. Need symmetric difference / Jaccard distance instead. | **PATCH-NOW v0.2 ITSELF** — change to Jaccard. |
| F-v2-6 | The Legality Responsibility Matrix says "C11a can add C11a-only invariants on the mutation transform itself", but examples (privacy, staircase clearance) sound like upstream concerns. Privacy is conceptually a C5 topology concern; staircase is a C7 grid concern. Pulling them into C11a-internal duplicates ownership. | **NEEDS WALK** — should these invariants migrate upstream? |
| F-v2-7 | `DeepMutationApplicationError` catches upstream errors broadly. If C10 raises `KBVersionMismatchError` (systemic), should that be caught and wrapped, or re-raised? Spec is silent. | **NEEDS WALK** — systemic error propagation rule. |
| F-v2-8 | M8 (master-floor-swap) requires multi-floor briefs but `requires_multi_floor` flag is in metadata only. Phase 1 logic should skip M8 when `floor_room_brief` is single-floor. | **PATCH-NOW v0.2 ITSELF** — note the skip path. |
| F-v2-9 | `MutationDiagnostics.deep_mutation_runtime_ms` is observational but lives inside the diagnostics dataclass. Should it move to provenance's `_observational_runtime_ms` for consistency, or stay in diagnostics? | **NEEDS WALK** — schema-shape question. |
| F-v2-10 | Tier A invariant table (§ 3.4) is sparse — only some operators listed. Walk #3 should produce the full per-operator invariant matrix. | **NEEDS WALK** — Walk #3 deliverable. |

**PATCH-NOW APPLIED INLINE TO v0.2**:
- **F-v2-2**: Default `max_seeds_per_input` raised to **9** (or document as 8 mutated + 1 BASE).
  Resolution: M0_BASE consumes the BASE family slot but does NOT count toward
  `max_seeds_per_input`. Phase 0 validates: sum(non-BASE family slots) ≤
  `max_seeds_per_input`. Default slot allocations sum: 8 non-BASE + 1 BASE = 9 total slots emitted.
- **F-v2-4**: Adjacency pair canonicalization: `(A, B)` represented with `tuple(sorted([A, B]))` always.
- **F-v2-5**: `novelty_deficit_estimator` = `1 - avg_pairwise_jaccard_distance(signature_edge_sets)`.
- **F-v2-8**: Phase 1 skip path — when `not floor_room_brief.is_multi_floor`, skip M8 deterministically; record as `valid=False, invalidity_reason="single_floor_brief"`.

**REJECTED-AS-CONSIDERED**:
- "Should `TopologySignature` include the corridor type explicitly?" — Implicit in
  `room_adjacency_edges` already (corridor adjacency is captured as edges).
- "Should diagnostics include per-operator runtime?" — Adds noise; provenance
  log already carries per-operator state if `FULL` verbosity.

---

## § 10 — Status

- **v0.2 PROPOSED**. **NOT LOCKED.**
- LOCK NOT REQUESTED at v0.2.
- 12 valid critique items resolved (10 specs + 2 partial). 0 rejected.
- 9 open questions remaining (down from 15 at v0.1).
- 6 backlog items listed (4 existing + 3 v0.1 + 3 v0.2 = 10 total in § 12).
- Estimated walks to LOCK: **3-5** more.
- Walk #3 should prioritize: per-operator invariant matrix (F-v2-10), Tier B
  caching strategy (F-v2-1), F-v2-3/F-v2-6/F-v2-7 architectural questions.

---

## § 12 — Backlog enumeration (per Rule 9)

| ID | Description | Origin | S{N}-scope verdict | Effort |
|---|---|---|---|---|
| B-217 | Polygonal envelopes spatial partitioning | S35 | Affects M9/M1/M2 on non-rectangular plots; v2 | L |
| B-220 | Hydraulic primitives + plumbing-engineer review | S35 | Pre-launch hard gate; affects M6 acceptance standard | L |
| B-237 | Cross-platform replay CI matrix + Decimal geometry | S35 #6+#9 | Inv 7/13 dependency | M |
| B-238 | Independent architect review | S35 | Direct review target for 9-operator catalog + family-transition policy | M |
| B-NEW-A | C11a M7 grid-scale KB-driven set | S37 W#1 Q11 | post-launch | XS |
| B-NEW-B | C11a cross-operator composition v2 | S37 W#1 Q3 | C11b stable + measured under-coverage | M |
| B-NEW-C | C11a abstract graph mutation operators (EvoArch-style) | S37 W#1 Q14 | post-launch + B-238 review | L |
| **B-NEW-D** | **C11a adaptive operator scheduling** | **S37 W#2 #6** | **post-launch + measured yield-skew** | **M** |
| **B-NEW-E** | **C11a provenance compaction for FULL verbosity** | **S37 W#2 #9** | **replay-snapshot size pressure** | **S** |
| **B-NEW-F** | **C11a QD-algorithm extension for novelty-driven generation** | **S37 W#2 #3+#12** | **post-launch + B-238 review** | **L** |

**Backlog summary**:

| Total | Pre-existing | New at v0.1 | New at v0.2 |
|---|---|---|---|
| 10 | 4 | 3 | 3 |

---

**End of v0.2 PROPOSED.** Awaits Ramalingam's reading + Walk #3 direction.
