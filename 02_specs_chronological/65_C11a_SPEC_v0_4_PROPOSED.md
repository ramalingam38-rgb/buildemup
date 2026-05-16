# C11a — Topology Mutation Layer — SPEC v0.4 PROPOSED

**Component**: 11a (canonical Track 3 numbering — paired with C11b NSGA-II)
**Status**: v0.4 PROPOSED. **NOT LOCKED.** Supersedes v0.3 PROPOSED.
**Authority**: S37 Walk #4 author's draft. PENDING Ramalingam adjudication.
**Authored**: S37 Walk #4, post external critique walk on v0.3.

---

## § 0 — Architectural notes (REVISED v0.4)

Two-tier mutation architecture (carried v0.2). Tier A shallow / Tier B
regenerative via `DeepMutationPipeline`. Atomicity-by-construction
(carried v0.3). v0.4 adds two cross-cutting governance mechanisms:
**purity contract** (resolves critique #1) and **pending-predicate
sunset** (resolves critique #2).

### § 0.1 — DeepMutationPurityContract (NEW v0.4 — resolves critique #1)

Atomicity-by-construction relies on upstream entry points being
side-effect free. v0.3 noted the C10 `_KB_VALIDATED` global as a
mutable cache; the reviewer correctly generalized this to "every
future upstream addition could silently violate atomicity."

Solution: **explicit purity attestation** registered at module load.

```python
@dataclass(frozen=True)
class PurityAttestation:
    """A declaration that an upstream entry point is side-effect free
    for the purposes of C11a Tier B regeneration."""
    component_id: str               # "C7" | "C9" | "C10"
    entry_point: str                # e.g., "GridGenerator.generate"
    purity_class: Literal[
        "pure",                     # no observable side effects on inputs or globals
        "read_only_cache",          # reads from process-global cache; never writes during call
        "lazy_init_once",           # first call may set a process-global; subsequent calls pure
    ]
    attested_by: str                # owner component name; identifies signer
    attested_at_kb_version: str     # binds attestation to a specific upstream version


# Module-level registry. C11a startup validates expected entries exist.
UPSTREAM_PURITY_REGISTRY: Final[tuple[PurityAttestation, ...]] = (
    PurityAttestation("C7", "GridGenerator.generate", "pure", "C7", "v0.7.3+amend_v0.8"),
    PurityAttestation("C9", "size_rooms", "pure", "C9", "v0.1+S34"),
    PurityAttestation("C10", "plan_wet_zones", "lazy_init_once", "C10", "v1.0_S36"),
    # C10's _KB_VALIDATED global qualifies as lazy_init_once; documented but not blocking.
)


def validate_upstream_purity_contract() -> None:
    """Startup hook. Validates all required upstream entry points have
    a registered PurityAttestation and the attested KB version matches
    runtime KB version. Run once during C11a import.

    Raises:
        DeepMutationPurityContractError on missing/mismatched attestations.
    """
```

**Test discipline** (Inv 25 below): the C11a test suite includes
*stateful upstream mock injection* tests — fixtures that intentionally
mock C9/C10 with side-effect-bearing implementations to verify
`DeepMutationPipeline` either (a) detects the violation via the
contract or (b) demonstrates the failure mode visibly. This makes the
purity assumption empirically falsifiable rather than implicit.

### § 0.2 — Pending-upstream predicate sunset (NEW v0.4 — resolves critique #2)

v0.3 introduced `pending_upstream=True` for predicates whose upstream
amendment (B-NEW-J/K/L) hasn't landed. Critique #2 correctly identifies
this as legality duplication risk.

```python
@dataclass(frozen=True)
class MutationViabilityPredicate:
    rule_owner: str
    rule_id: str
    description: str
    _predicate_fn: Callable                    # runtime; underscore = excluded from serialization
    pending_upstream: bool = False              # carried v0.3
    expires_at_version: str | None = None       # NEW v0.4 — required if pending_upstream=True
```

**Sunset enforcement**:
1. If `pending_upstream=True` and `expires_at_version is None` → startup raises.
2. If current C11a version >= `expires_at_version` AND predicate still
   marked pending → startup escalating warning (WARN at v < target+1, RAISE at +2).
3. **LOCK gate**: 0 predicates with `pending_upstream=True` allowed at
   C11a v1.0 LOCK (Inv 24 below). All upstream amendments
   (B-NEW-J/K/L/P) must land before C11a v1.0 LOCK can be granted.

Governance metric exposed: `pending_upstream_predicate_count` —
visible at startup; baseline expectation is **0 at v1.0 LOCK**.

### § 0.3 — Mutation Legality Responsibility Matrix (carried v0.3)

C11a does not own architectural rules. Legality predicates reference
upstream rule IDs. Concrete amendments still required:

| ID | Upstream amendment |
|---|---|
| B-NEW-J | C5: privacy zoning rule |
| B-NEW-K | C7: staircase clearance invariant |
| B-NEW-L | C8: entry approach invariant |
| **B-NEW-P (NEW v0.4)** | **C10/C9/C7: error severity classification — `severity_tier` class attribute on every error class (resolves critique #10)** |

---

## § 1 — Walk-resolved scope (REVISED v0.4)

| Q / F | Resolution | Walk |
|---|---|---|
| (carried v0.2/v0.3) | … as prior | … |
| **F-v3-2 (W#4)** | **Upstream amendments B-NEW-J/K/L/P land BEFORE C11a v1 build (no temporary inline checks). Sequencing: 1 sub-session per amendment (XS effort each, ~4 amendment sessions total = ~1-2 calendar sessions).** | W#4 |
| **F-v3-3 / Q21 (W#4)** | **`OperatorExpectedDeltaSchema`: per-operator declared upstream-delta scope. Implementation in § 2.5 below.** | W#4 |
| **F-v2-3 carried (W#4)** | **M5 zone-swap concrete invalidation fixture: a Courtyard topology where private rooms surround the central court, and zone-swap (M5) places service rooms (kitchen/utility) around the court → no longer a recognizable Courtyard topology family. Fixture documented in test plan; INVALIDATES_FAMILY survives in enum.** | W#4 |
| **F-v3-7 (W#4)** | **Per-operator test plan: variants share invalidation fixtures. M3a/b/c → 3 happy + 1 invalidation; M7a/b → 2 happy + 1 invalidation; M9a/b/c/d → 4 happy + 1 invalidation. Total: 21 happy + 11 invalidation = 32 per-operator tests (matches v0.3 target).** | W#4 |
| **F-v3-8 (W#4)** | **`upstream_regeneration_delta` keys drawn from a controlled vocabulary defined in `OperatorExpectedDeltaSchema` per operator.** | W#4 |

---

## § 2 — Contract (REVISED v0.4)

### § 2.1 — Operator enum + tier + family + transition policy

Carried verbatim from v0.3 (16 operators across 9 families).

### § 2.2 — Operator metadata (REVISED v0.4 — declarative cache + delta schema)

```python
@dataclass(frozen=True)
class MutationOperatorMetadata:
    operator: MutationOperator
    tier: MutationTier
    family: MutationOperatorFamily
    family_transition_policy: TopologyFamilyTransitionPolicy
    requires_multi_floor: bool
    requires_grid_regen: bool
    expected_delta_schema: OperatorExpectedDeltaSchema   # NEW v0.4 (Q21/F-v3-3)
    cache_relevant_config_fields: tuple[str, ...]        # NEW v0.4 (critique #4)


@dataclass(frozen=True)
class OperatorExpectedDeltaSchema:
    """NEW v0.4 — resolves Q21/F-v3-3.

    Declares the upstream-delta vocabulary for an operator. The actual
    delta produced by Tier B regeneration is compared against this set;
    deltas outside the declared scope mark the result as
    EMERGENT_REGENERATION.
    """
    expected_delta_keys: frozenset[str]    # whitelist — exact match
    allowed_secondary_keys: frozenset[str]  # tolerated but flagged
    forbidden_keys: frozenset[str] = frozenset()  # if any of these appear, REJECT mutation
```

**Per-operator delta schemas (Walk #4 first cut)**:

| Operator | Expected delta keys | Allowed secondary | Forbidden |
|---|---|---|---|
| M0_BASE | `{}` (no delta) | — | — |
| M1_HORIZ_FLIP | `{room_x_coords}` | `{adjacency_edges_orientation}` | `{room_areas, fixture_types}` |
| M2_VERT_FLIP | `{room_y_coords}` | `{adjacency_edges_orientation}` | `{room_areas}` |
| M3a/b/c | `{staircase_position}` | `{corridor_routing}` | `{room_count, room_areas}` |
| M4 | `{corridor_topology}` | `{adjacency_edges, zone_assignments}` | `{room_count}` |
| M5 | `{zone_assignments}` | `{adjacency_edges}` | `{room_count}` |
| M6 | `{wet_wall_assignment}` | `{trap_arm_distances, riser_groups}` | `{room_areas, room_x_coords}` |
| M7a/b | `{grid_bay_size, room_areas}` | `{wet_wall_assignment, trap_arm_distances, room_x_coords, room_y_coords}` | `{room_count, fixture_types}` |
| M8 | `{master_bedroom_floor, floor_room_assignment}` | `{adjacency_edges}` | `{room_count, room_areas}` |
| M9a-d | `{entry_position}` | `{primary_circulation_path}` | `{room_count, room_x_coords, room_y_coords}` |

Walk #5 confirms or refines this matrix per concrete fixture testing.

### § 2.3 — Application result + candidate (carried v0.3)

`MutationApplicationResult` carries `lineage_depth` and
`upstream_regeneration_delta`. Lineage classifier (NEW v0.4):

```python
def classify_lineage_depth(
    operator: MutationOperator,
    actual_delta_keys: frozenset[str],
) -> MutationLineageDepth:
    """Resolves Q21/F-v3-3 — precise classifier."""
    if OPERATOR_METADATA[operator].tier == MutationTier.SHALLOW:
        return MutationLineageDepth.SHALLOW_TRANSFORM

    schema = OPERATOR_METADATA[operator].expected_delta_schema
    if actual_delta_keys & schema.forbidden_keys:
        # Mutation invariant violated; will be REJECTED upstream of this call.
        # Defensive: classify but the result will not be emitted.
        return MutationLineageDepth.EMERGENT_REGENERATION
    if actual_delta_keys <= (schema.expected_delta_keys | schema.allowed_secondary_keys):
        return MutationLineageDepth.REGENERATIVE_TRANSFORM
    return MutationLineageDepth.EMERGENT_REGENERATION
```

### § 2.4 — Diagnostics + signature (carried v0.3)

Carried v0.3.

### § 2.5 — Cache-relevant field annotation (NEW v0.4 — resolves critique #4)

Replace v0.3's manually curated `config_hash` subset with a declarative
mechanism:

```python
def _is_cache_relevant(field_metadata: dict) -> bool:
    """Helper: read dataclass field metadata for cache_relevant marker."""
    return field_metadata.get("cache_relevant", False)


@dataclass(frozen=True)
class TopologyMutationConfig:
    enabled_operators: tuple[MutationOperator, ...] = field(
        default_factory=..., metadata={"cache_relevant": True},
    )
    max_seeds_per_input: int = field(
        default=8, metadata={"cache_relevant": True},
    )
    family_slot_allocations: tuple[FamilySlotAllocation, ...] = field(
        default_factory=..., metadata={"cache_relevant": True},
    )
    deterministic_order: bool = field(
        default=True, metadata={"cache_relevant": True},
    )
    emit_base: bool = field(
        default=True, metadata={"cache_relevant": True},
    )
    deduplicate_by_signature: bool = field(
        default=True, metadata={"cache_relevant": True},
    )
    # cache-irrelevant (don't affect mutation result):
    enforcement_mode: EnforcementMode = field(
        default=EnforcementMode.WARN, metadata={"cache_relevant": False},
    )
    provenance_verbosity: ProvenanceVerbosity = field(
        default=ProvenanceVerbosity.PER_OP, metadata={"cache_relevant": False},
    )
    deep_mutation_cache_enabled: bool = field(
        default=True, metadata={"cache_relevant": False},
    )
    skip_pending_upstream_predicates: bool = field(
        default=False, metadata={"cache_relevant": False},
    )


def derive_cache_config_hash(config: TopologyMutationConfig) -> str:
    """Auto-derives the hash from all cache-relevant fields. New fields
    added without `metadata={"cache_relevant": ...}` raise at startup
    via `validate_operator_registry()` extension."""
```

**Inv 26 (NEW v0.4)**: every `TopologyMutationConfig` field MUST carry
`metadata["cache_relevant"]`. Missing markers caught at startup;
drift-prevention mechanism for critique #4.

### § 2.6 — Registry validation modes (NEW v0.4 — resolves critique #5)

```python
class RegistryValidationMode(str, Enum):
    """NEW v0.4 — operational fragility mitigation (critique #5)."""
    STRICT = "strict"     # default; raises on any inconsistency at startup
    WARN   = "warn"       # logs warning; disables affected operators; continues startup


@dataclass(frozen=True)
class TopologyMutationConfig:
    # ... carried fields ...
    registry_validation_mode: RegistryValidationMode = field(
        default=RegistryValidationMode.STRICT,
        metadata={"cache_relevant": False},
    )
```

**Behaviour**:
- `STRICT` (default, recommended for production): startup raises
  `OperatorRegistryError` on any registry inconsistency. No degraded mode.
- `WARN` (development / CI debugging): startup logs a structured warning
  per inconsistency, marks affected operators as "quarantined", proceeds.
  Quarantined operators automatically excluded from `enabled_operators`
  for that process lifetime.

**Per-operator quarantine telemetry / lifecycle observability** is
deferred to **B-NEW-Q** (post-launch operational concern).

### § 2.7 — Error severity classification (NEW v0.4 — resolves critique #10)

Hardcoded exception lists (v0.3 § 3.5 systemic-error-propagation rule)
become brittle as upstream errors evolve. v0.4 inverts the dependency:
each upstream error class declares its own severity tier.

```python
# Pattern (added at upstream components via B-NEW-P amendment):
class WetZonePlanError(Exception):
    severity_tier: ClassVar[Literal[
        "per_candidate",   # candidate-scoped; aggregate
        "batch",            # whole-batch failure
        "systemic",         # halt; unrecoverable
    ]] = "per_candidate"

class KBVersionMismatchError(WetZonePlanError):
    severity_tier: ClassVar[str] = "systemic"

class BatchWetZoneInfeasibleError(WetZonePlanError):
    severity_tier: ClassVar[str] = "batch"

class PlumbingConfidenceTooLow(WetZonePlanError):
    severity_tier: ClassVar[str] = "systemic"
```

**C11a's catch logic in `DeepMutationPipeline`**:

```python
try:
    new_candidate = c10.plan_wet_zones(...)
except Exception as e:
    severity = getattr(type(e), "severity_tier", "unknown")
    if severity == "systemic":
        raise                                # propagate uncaught
    if severity == "batch":
        raise DeepMutationApplicationError(e)  # wrap; reject mutation
    if severity == "per_candidate":
        raise DeepMutationApplicationError(e)  # wrap; reject mutation
    # severity == "unknown": defensive — treat as systemic
    raise
```

**B-NEW-P** files the upstream amendment pattern. Required before C11a
build.

---

## § 3 — Behaviour (REVISED v0.4)

### Phase 0 — Input + startup validation

1. `validate_operator_registry()` (carried v0.3, extended for cache-relevant
   field markers and `OperatorExpectedDeltaSchema` presence).
2. `validate_upstream_purity_contract()` (NEW v0.4).
3. Sunset-enforcement scan: count `pending_upstream` predicates;
   raise/warn per § 0.2 rules.
4. Per-config validation (carried).

### Phase 1 — Per-candidate seed generation

Carried v0.3 with one addition: post-mutation, call
`classify_lineage_depth(operator, actual_delta_keys)` to label each
result.

### Phase 2 — Output assembly + diagnostics

Carried v0.3.

### Phase 3 — Provenance assembly

Carried v0.3.

### § 3.4 — Tier A predicate orchestration

Walk #4 deferred-but-shipped per-operator predicate matrix (using
post-amendment upstream rule IDs from B-NEW-J/K/L):

| Operator | Predicates (rule_owner.rule_id) |
|---|---|
| M0_BASE | (none — pass-through) |
| M1 | C9.Inv_5, C9.Inv_13, C10.Inv_4, C10.Inv_5 |
| M2 | C5.privacy_zoning, C9.Inv_5, C9.Inv_13, C10.Inv_5 |
| M3a/b/c | C7.staircase_clearance, C9.Inv_4 |
| M4 | C9.Inv_4, C10.Inv_5 |
| M5 | C5.privacy_zoning, C10.Inv_5b |
| M9a-d | C8.entry_approach |

Per-predicate `expires_at_version` set to v1.0 (LOCK gate; B-NEW-J/K/L
must land first).

### § 3.5 — Tier B `DeepMutationPipeline` (REVISED v0.4)

Carried v0.3 plus:
- Step 5b: post-regeneration, compute `actual_delta_keys` and call
  `classify_lineage_depth()`. If forbidden_keys hit: REJECT.
- Step 5c (catch): if upstream error raised, route via § 2.7
  severity-tier rule.

### § 3.6 — M5 invalidation case (NEW v0.4 — F-v2-3 carried)

Concrete fixture demonstrating M5_ZONE_SWAP producing
`INVALIDATES_FAMILY`:

```
Source: Courtyard topology, 30×30 plot
  Bedrooms (private) ring the central court on N, E, W.
  Living/Dining (public) is on S, opening into court.
  Kitchen is on SE corner, accessing both court and dining.
  Pooja is on NE corner, oriented toward court.

Apply M5_ZONE_SWAP:
  Private (bedrooms) → S
  Public (living/dining) → N, E, W ringing court
  Kitchen → NW corner
  Pooja → SW corner

Result: court is now ringed by service + public zones. Bedrooms cluster
on the south face. The "court is the private retreat" semantic that
defines Courtyard family is gone. Result is more accurately classified
as "South-strip with vestigial court" — no longer a Courtyard.

Classification: INVALIDATES_FAMILY (output_family_id = "STRIP_VESTIGIAL_COURT"
or rejected entirely depending on enforcement_mode).
```

This fixture justifies preserving the `INVALIDATES_FAMILY` enum value.
Walk #5 may add additional invalidation cases (M4 in some plot shapes
is a candidate).

---

## § 4 — Invariants (REVISED v0.4)

| # | Invariant | Mode |
|---|---|---|
| 1-22 | (carried verbatim from v0.3) | as v0.3 |
| **23 (NEW v0.4)** | **`MutationLineageDepth` classification follows `OperatorExpectedDeltaSchema`: SHALLOW for Tier A; REGENERATIVE for Tier B with delta ⊆ (expected ∪ allowed_secondary); EMERGENT for Tier B with delta exceeding that set; REJECT if any forbidden_key present** | RAISE |
| **24 (NEW v0.4)** | **At C11a v1.0 LOCK, `pending_upstream_predicate_count == 0`. Sunset enforcement (§ 0.2) escalates from WARN at version+1 to RAISE at version+2.** | RAISE (LOCK gate) |
| **25 (NEW v0.4)** | **`UPSTREAM_PURITY_REGISTRY` covers every C7/C9/C10 entry point invoked by `DeepMutationPipeline`. Stateful upstream mock injection tests verify atomicity assumption is empirically falsifiable.** | RAISE (startup + test) |
| **26 (NEW v0.4)** | **Every `TopologyMutationConfig` field carries `metadata["cache_relevant"]` boolean. Missing markers raise `OperatorRegistryError` at startup. (resolves critique #4 drift)** | RAISE (startup) |
| **27 (NEW v0.4)** | **Upstream errors classified via `severity_tier` ClassVar — not hardcoded type lists. Unknown severity defaults to `systemic` (defensive). (resolves critique #10)** | RAISE (severity inversion of control) |

---

## § 5 — Failure modes (REVISED v0.4)

Carried v0.3 plus:

```
TopologyMutationError (base)
├── PerCandidateError
│   ├── TopologyInvalidError
│   ├── MutationApplicationError
│   └── DeepMutationApplicationError
├── BatchAllNonBaseFailedError
├── OperatorRegistryError
├── DeepMutationPurityContractError       (NEW v0.4 — startup)
├── PendingUpstreamPredicateError         (NEW v0.4 — startup; sunset breach)
└── InvariantViolationError               (systemic)
```

---

## § 6 — Test coverage targets (REVISED v0.4)

Target ~175 tests at LOCK (up from v0.3's 155):

- ~32 schema (carried; +`OperatorExpectedDeltaSchema`,
  `PurityAttestation`, `RegistryValidationMode`)
- ~32 per-operator (Walk #4 plan: 21 happy + 11 invalidation)
- ~30 invariants (Inv 1-27)
- ~25 phase-logic
- ~12 partial-batch / strict-mode
- ~10 replay snapshot
- ~10 diagnostics
- ~10 NEW v0.3 (registry validation, lineage classification, atomicity
  kill-step)
- **~14 NEW v0.4** — purity contract violations (5), pending sunset
  enforcement (3), cache-relevant field marker enforcement (2),
  registry mode quarantine (2), severity-tier inversion (2)

Cumulative target at C11a ship: 2314 + 175 ≈ **2489 passed**.

---

## § 7 — Open questions surfaced at v0.4 (down from 6 to 4)

| Q | Question | v0.4 direction |
|---|---|---|
| Q1 | Catalog completeness — all 9 base operators at v1? | Carried open. Walk #5 review per-operator yield expectations. |
| Q11 | M7 grid-scale set fixed or KB-driven? | KB-driven post-v1 (B-NEW-A); fixed at v1. |
| Q12 | Multi-floor briefs — per-floor or building-wide? | Building-wide. |
| Q22 (NEW) | M4 corridor inversion as additional INVALIDATES_FAMILY case? | Walk #5 to test. |

**Resolved at Walk #4**: Q13 (cross-platform via B-237 + version
hashes), Q16 (TopologyFamily as strings), Q17 (slot tie-break lex-ASC),
Q21 (lineage classification via OperatorExpectedDeltaSchema),
F-v2-3 (M5 fixture documented).

---

## § 8 — Backlog at v0.4

**New at v0.4** (Walk #4 critique outcomes):

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-NEW-M | C11a quantitative lineage extension (regeneration magnitude, normalized topology delta score) | W#4 #6 | post-launch + measured emergent rate | M |
| B-NEW-N | C11a replay compatibility infrastructure (frozen invariant snapshots, KB version pinning, replay migration adapters) | W#4 #8 | post-launch + first replay-snapshot incompat case | L |
| B-NEW-O | C11a `InvariantCapabilityRegistry` (capability abstraction over raw rule_id references) | W#4 #9 | invariant reference count exceeds 30 | L |
| **B-NEW-P** | **Upstream amendments: `severity_tier` ClassVar on every error class in C7/C9/C10** | W#4 #10 | required before C11a v1 build | XS |
| B-NEW-Q | C11a per-operator quarantine telemetry + lifecycle observability | W#4 #5 partial | post-launch operational | S |

**Scope confirmations on existing items** (no new IDs):
- B-NEW-G (signature spatial expansion) explicitly covers circulation
  graph depth, public/private traversal depth, corridor branching factor,
  room visibility hierarchy per W#4 #7.
- B-NEW-O has explicit trigger condition: invariant reference count > 30.
  At v1 we have ~12 references; capability abstraction doesn't earn its
  complexity tax yet.

---

## § 9 — Rule 11 spec audit on v0.4 PROPOSED

**PATCH-NOW (in v0.4 itself): 0** — drafting is the patch round.

**OPEN QUESTIONS at v0.4**: Q1, Q11, Q12, Q22 (4; down from 6).

**SPEC-AUDIT FINDINGS (v0.4)**:

| # | Finding | Verdict |
|---|---|---|
| F-v4-1 | `OperatorExpectedDeltaSchema` per-operator delta keys are free-form strings ("room_x_coords", "wet_wall_assignment", etc.) — no canonical vocabulary registry. Two operators may use different strings for the same concept. | **NEEDS WALK** — Walk #5 should formalize delta vocabulary as an enum. |
| F-v4-2 | `UPSTREAM_PURITY_REGISTRY` is a tuple constant — adding entries requires source edit. If C11 grows new upstream dependencies (e.g., post-v1 KB lookups), the registry update becomes another sequence point. | **NEEDS WALK** — registry as data-driven (KB-loaded) vs source-constant; lean toward source-constant for explicit review gate. |
| F-v4-3 | `expires_at_version` strings are unstructured — "v1.0" vs "v1.0.0" vs "v1.0_S37" — no canonical form. Comparison against current version is ambiguous. | **PATCH-NOW** — adopt SemVer-like canonical form: `vMAJOR.MINOR[.PATCH]`. |
| F-v4-4 | M5 Courtyard fixture says "kitchen → NW corner" but the source description has "kitchen at SE corner". After zone swap, kitchen would migrate based on its zone classification. Need to clarify whether kitchen is service-zone (private-pattern) or public-zone in this case. | **PATCH-NOW** — clarify kitchen as service-zone; SE→NW is correct. |
| F-v4-5 | `severity_tier` defaults to `"systemic"` for unknown — defensive. But if upstream forgets to set it, every per-candidate error becomes a batch-halting systemic error. Strict default is safer for correctness but creates operational fragility. | **NEEDS WALK** — default trade-off; could add a startup check that all referenced exception classes carry a `severity_tier` ClassVar (similar to `validate_upstream_purity_contract`). |
| F-v4-6 | `RegistryValidationMode.WARN` quarantines affected operators by removing them from `enabled_operators`. If `enabled_operators` is a frozen tuple in `TopologyMutationConfig`, runtime quarantine requires creating a new config — mutation problem in itself. | **NEEDS WALK** — quarantine semantics: alter config or maintain separate runtime allow-list. |
| F-v4-7 | The Walk #4 critique meta-item #12 (Complexity Budget) deserves its own § in the spec. Currently surfaced in this audit but not as a permanent governance section. | **PATCH-NOW** — add § 13 Complexity Budget. |
| F-v4-8 | `UpstreamPurityContract` v0.4 distinguishes `pure` / `read_only_cache` / `lazy_init_once`. But `lazy_init_once` admits race conditions in multi-threaded execution (two threads triggering first-call simultaneously). C11a is currently single-threaded but no spec constraint enforces this. | **NEEDS WALK** — concurrency contract; lean toward single-threaded constraint at v1. |

**PATCH-NOW APPLIED INLINE TO v0.4**:
- **F-v4-3**: `expires_at_version` follows `vMAJOR.MINOR[.PATCH]`. C11a v1.0 LOCK gate compares against `v1.0`.
- **F-v4-4**: M5 fixture clarification — kitchen treated as service-zone (private-pattern); zone-swap migrates SE → NW.
- **F-v4-7**: § 13 Complexity Budget added below.

**REJECTED-AS-CONSIDERED**:
- "Should we serialize the `PurityAttestation` registry as JSON for review?"
  Source-constant tuple is deliberate; review gate is the source-edit PR.
- "Should `expected_delta_keys` allow regex patterns?" Adds complexity for
  no measured need; explicit enums cleaner.

---

## § 10 — Status

- **v0.4 PROPOSED**. **NOT LOCKED.**
- LOCK NOT REQUESTED at v0.4.
- 12 valid critique items resolved (5 amendments + 2 partial + 4 backlog
  + 1 documented + 1 meta-amendment). 0 fully MISFRAMED; 1 push-back (item 9).
- 4 open questions remaining.
- 22 backlog items total (see § 12).
- Estimated walks to LOCK: **1-3** more.
- Walk #5 priorities: F-v4-1 (delta vocabulary canonical form),
  F-v4-5 (severity_tier startup check), F-v4-6 (quarantine semantics),
  F-v4-8 (concurrency contract), Q1 (catalog completeness review with
  yield expectations), Q22 (M4 invalidation case).

---

## § 12 — Backlog enumeration

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-217 / B-220 / B-237 / B-238 | (carried; 4 pre-existing) | S35 | various |
| B-NEW-A through B-NEW-L | (carried v0.1-v0.3; 10 items) | W#1-#3 | various |
| **B-NEW-M** | **Quantitative lineage extension** | **W#4 #6** | **M** |
| **B-NEW-N** | **Replay compatibility infra** | **W#4 #8** | **L** |
| **B-NEW-O** | **InvariantCapabilityRegistry (trigger: refs > 30)** | **W#4 #9** | **L** |
| **B-NEW-P** | **Upstream `severity_tier` amendment cluster** | **W#4 #10** | **XS** |
| **B-NEW-Q** | **Per-operator quarantine telemetry** | **W#4 #5 partial** | **S** |

**Backlog summary**:

| Total | Pre-existing | v0.1 | v0.2 | v0.3 | v0.4 |
|---|---|---|---|---|---|
| **22** | 4 | 3 | 3 | 7 | 5 |

---

## § 13 — Complexity Budget (NEW v0.4 — meta-amendment per critique #12)

Reviewer correctly observes backlog growth (10 → 17 → 22) signals
surface-area expansion. Each spec walk adds 3-7 backlog items. After 9
walks (matching C10's arc), 35-50 items would be unreasonable.

### v1 surface area declared

C11a v1 ships these v1-essential subsystems:

| # | Subsystem | Justified by |
|---|---|---|
| 1 | 16 mutation operators + metadata | Mission (the topology mutation set) |
| 2 | Tier A / Tier B execution | Critique W#2 #1, #2 (cost separation) |
| 3 | Per-family slot allocation | Critique W#2 #8 (truncation bias) |
| 4 | Topology signature canonical | Critique W#2 #5 (deduplication needs canonical surface) |
| 5 | Provenance + diagnostics | Mission (replay + observability) |
| 6 | KB validators + registry validation | Mission (startup safety) |
| 7 | MutationLineageDepth + classifier | Critique W#3 #6 (Tier B traceability) |
| 8 | UpstreamReplayVersionHashes | Critique W#3 #10 (replay drift detection) |
| 9 | DeepMutationCacheKey memoization | Critique W#3 #1 (Tier B cost) |
| 10 | MutationViabilityPredicate orchestration | Critique W#3 #3 (invariant ownership) |
| 11 | DeepMutationPurityContract | Critique W#4 #1 (atomicity assumption) |
| 12 | Pending-predicate sunset | Critique W#4 #2 (legality duplication) |
| 13 | OperatorExpectedDeltaSchema | Critique W#4 #3 (lineage classifier) |
| 14 | cache_relevant field annotation | Critique W#4 #4 (cache-key drift) |
| 15 | RegistryValidationMode | Critique W#4 #5 (startup fragility) |
| 16 | severity_tier inversion | Critique W#4 #10 (error classification) |

**16 subsystems for v1.** Each has a documented critique-walk
justification trigger. None speculative.

### What v0.4 explicitly does NOT add

| Considered | Rejected as |
|---|---|
| Capability registry (item 9) | Premature for ~12 invariant references; trigger > 30 |
| Quantitative lineage (item 6) | Categorical sufficient at v1; metric design needs measured data |
| Circulation signature deep fields (item 7) | Replay-surface overfitting risk; defer to v2 |
| Replay compatibility migration (item 8) | Detection sufficient at v1; migration after first incompat |
| Per-operator quarantine telemetry (item 5 partial) | Operational concern post-launch |

### Walk #5+ governance rule

Each future walk's audit must explicitly count net surface-area changes:
- Items added → counted toward v1 budget
- Items routed to backlog → no v1 cost, but add to operational debt
- Items rejected-as-considered → preferred over backlog when not clearly future-needed

**Walk #5 budget cap**: 0-2 new v1 subsystems. Beyond that, walk
findings must route to backlog or rejection.

---

**End of v0.4 PROPOSED.** Awaits Ramalingam's reading + Walk #5 direction.
