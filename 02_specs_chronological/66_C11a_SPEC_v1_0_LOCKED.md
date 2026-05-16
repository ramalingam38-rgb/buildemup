<!-- ============================================================== -->
<!-- LOCKED at S37 by Ramalingam (Rule 8 LOCK authority).             -->
<!-- The body below is the v0.5/v0.3 PROPOSED spec content carried   -->
<!-- forward verbatim. LOCK was granted on this exact body.          -->
<!-- DO NOT MODIFY THIS FILE. Future amendments require new spec.    -->
<!-- ============================================================== -->

# C11a — Topology Mutation Layer — SPEC v0.5 PROPOSED

**Component**: 11a (canonical Track 3 numbering — paired with C11b NSGA-II)
**Status**: v0.5 PROPOSED. **NOT LOCKED.** **Freeze candidate**: proposing
v0.5 as the last walk before LOCK request, contingent on Ramalingam's
adjudication of items below + § 14 freeze rationale.
**Authority**: S37 Walk #5 author's draft. PENDING Ramalingam adjudication.
**Authored**: S37 Walk #5, post external critique walk on v0.4.

---

## § 0 — Architectural notes (REVISED v0.5)

Two-tier mutation architecture (carried). Atomicity-by-construction
(carried). Purity contract (carried v0.4). Pending-predicate sunset
(carried v0.4). v0.5 adds three governance refinements + freezes the
architectural surface.

### § 0.1 — DeepMutationPurityContract test discipline (REVISED v0.5 — resolves critique #1)

v0.4 introduced declarative `PurityAttestation`. Critique #1 correctly
identifies this as trust-based: a developer can wrongly mark a stateful
function as `pure`. Solution at v0.5: paired test-discipline
requirement, not a new subsystem.

**`PurityVerificationTestSuite`** is a test fixture pattern (not a new
runtime subsystem). For every `PurityAttestation` entry, the C11a test
suite includes:

1. **Deterministic replay test**: invoke entry point twice with identical
   inputs; assert byte-equal output (using existing `canonical_serialize`).
2. **Snapshot-diff test**: capture process global state before and after
   invocation; assert diff is empty (`pure`) or contained to declared
   cache region (`read_only_cache`, `lazy_init_once`).
3. **Repeated-invocation equivalence test**: invoke 100 times; assert
   first output equals last output.

Implementation is **test-only** — no runtime addition. Falsifies bad
attestations empirically. C11a build adds these as standard test
fixtures alongside per-operator tests. **Not a new v1 subsystem;
extends test discipline only.**

### § 0.2 — Compatibility window waiver (NEW v0.5 — resolves critique #2)

v0.4 sunset enforcement creates upstream-amendment deadlock risk:
delayed C5/C7/C8 amendment blocks C11a LOCK. Solution: explicit waiver
token with governance audit.

```python
@dataclass(frozen=True)
class UpstreamAmendmentWaiver:
    """NEW v0.5 — resolves critique #2.

    Allows C11a v1.0 LOCK to proceed despite a pending_upstream predicate,
    in exchange for an explicit, audit-logged grace window.
    """
    rule_owner: str
    rule_id: str
    waiver_reason: str                         # human-readable; written to provenance
    granted_by: str                            # name; for audit trail
    granted_at_iso: str                         # ISO 8601 timestamp
    grace_window_expires_at_version: str        # SemVer; hard ceiling
    inline_check_implementation: str           # docstring-style declaration of the temporary check
```

**Rules**:
- Waiver must be signed by Ramalingam (sole grant authority — Rule 8 alignment).
- Maximum **3 active waivers** at v1.0 LOCK time. More than 3 = LOCK
  refused regardless.
- Each waiver has a hard expiration ceiling: `current_version +
  PATCH+2`. Past ceiling = automatic LOCK invalidation at next release.
- All waivers logged to `WAIVER_REGISTRY` (source-constant); reviewable
  per release.

Inv 24 (LOCK gate) revised: `pending_upstream_predicate_count -
len(active_waivers) == 0` AND `len(active_waivers) ≤ 3`.

### § 0.3 — Concurrency execution contract (NEW v0.5 — resolves critique #9 / F-v4-8)

v1 explicit constraint:

> **C11a v1.0 is single-threaded by contract.** `mutate_topologies()` is
> not safe to invoke concurrently from multiple threads against shared
> state (specifically: the per-batch `DeepMutationCacheKey` cache and
> the `_KB_VALIDATED` lazy-init globals downstream).

```python
def mutate_topologies(
    wet_zoned_candidates: tuple[WetZonePlannedCandidate, ...],
    ...
) -> tuple[MutatedTopologyCandidate, ...]:
    """...
    
    Concurrency:
        Single-threaded only at v1.0. Multi-process safe (no
        cross-process state). Multiple threads in the same process
        invoking this function concurrently is undefined behaviour.
        Async parallelization deferred to B-NEW-U.
    """
```

**B-NEW-U** files the eventual deterministic-parallel-semantics work
(post-launch).

### § 0.4 — Mutation Legality Responsibility Matrix (carried v0.3/v0.4)

Carried unchanged. C11a does not own architectural rules.

---

## § 1 — Walk-resolved scope (REVISED v0.5)

| Q / F | Resolution | Walk |
|---|---|---|
| (carried v0.2-v0.4) | … as prior | … |
| **F-v4-1 (W#5)** | **Delta-key canonical vocabulary: hierarchical-namespace `DeltaKey` enum (`geometry.room.area`, `plumbing.wet_wall.assignment`, etc.). Resolves critique #3 + F-v4-1.** | W#5 |
| **F-v4-2 (W#5)** | **`UPSTREAM_PURITY_REGISTRY` stays source-constant. Source-edit PR is the explicit review gate. Data-driven (KB-loaded) registry deferred to post-v1 (no B-NEW filed; would be over-engineering at v1).** | W#5 |
| **F-v4-5 (W#5)** | **`SeverityClassificationAudit` at C11a startup — analog to `validate_upstream_purity_contract`. Walks every referenced exception type; verifies `severity_tier` ClassVar present and not "unknown". Resolves critique #6.** | W#5 |
| **F-v4-6 (W#5)** | **Quarantine semantics: maintain runtime allow-list (not config mutation). Quarantine fingerprint added to provenance. Replay with mismatched quarantine state REJECTED. Resolves critique #5.** | W#5 |
| **F-v4-8 (W#5)** | **§ 0.3 above — single-threaded contract at v1.** | W#5 |
| **Q1 (W#5)** | **All 9 base operators (16 enum entries) ship at v1. Yield-skew remediation via B-NEW-D post-launch with measured data; trimming pre-launch is unfalsifiable speculation.** | W#5 |
| **Q11 (W#5)** | **M7 grid scales fixed at v1 (3.0/3.3/2.7 m). KB-driven set post-v1 via B-NEW-A.** | W#5 |
| **Q12 (W#5)** | **Multi-floor: building-wide. M8 confirmed.** | W#5 |
| **Q22 (W#5)** | **M4 corridor inversion is `TRANSFORMS_FAMILY` (not INVALIDATES). Concrete reasoning: corridor inversion converts central-spine to edge-strip but the room-graph is preserved. Carried as TRANSFORMS unless Walk #6+ surfaces a counter-example.** | W#5 |

**Resolved at Walk #5**: 5 deferred audit findings + 4 long-standing
open questions. **0 open questions remain at v0.5.**

---

## § 2 — Contract (REVISED v0.5)

### § 2.1 — Operator enum + tier + family (carried v0.4)

### § 2.2 — Operator metadata (REVISED v0.5 — uses DeltaKey)

```python
class DeltaKey(str, Enum):
    """NEW v0.5 — canonical vocabulary for upstream-regeneration deltas.
    Hierarchical namespace prevents semantic drift (resolves critique #3).
    """
    # geometry domain
    GEO_ROOM_AREA           = "geometry.room.area"
    GEO_ROOM_POSITION_X     = "geometry.room.position_x"
    GEO_ROOM_POSITION_Y     = "geometry.room.position_y"
    GEO_GRID_BAY_SIZE       = "geometry.grid.bay_size"
    GEO_STAIRCASE_POSITION  = "geometry.staircase.position"
    GEO_ENTRY_POSITION      = "geometry.entry.position"

    # adjacency domain
    ADJ_EDGES               = "adjacency.edges"
    ADJ_EDGES_ORIENTATION   = "adjacency.edges_orientation"

    # circulation domain
    CIRC_CORRIDOR_TOPOLOGY  = "circulation.corridor.topology"
    CIRC_PRIMARY_PATH       = "circulation.primary_path"
    CIRC_CORRIDOR_ROUTING   = "circulation.corridor.routing"

    # zoning domain
    ZONE_ASSIGNMENTS        = "zoning.assignments"
    ZONE_PRIVACY_PATTERN    = "zoning.privacy_pattern"

    # plumbing domain
    PLUMB_WET_WALL_ASSIGNMENT = "plumbing.wet_wall.assignment"
    PLUMB_TRAP_ARM_DISTANCES  = "plumbing.trap_arm.distances"
    PLUMB_RISER_GROUPS        = "plumbing.riser_groups"

    # multi-floor domain
    MULTI_MASTER_BR_FLOOR     = "multifloor.master_bedroom.floor"
    MULTI_FLOOR_ASSIGNMENT    = "multifloor.floor_assignment"

    # meta domain — these keys are NEVER produced as expected/allowed deltas
    # by any operator. They appear only in `forbidden_keys` sets to express
    # cross-operator invariants ("no operator may change room count" /
    # "no operator may change fixture-type set"). They live in the enum so
    # the canonical-vocabulary rule (Inv 28) catches misuse at startup;
    # absence from any operator's expected/allowed set is intentional.
    META_FIXTURE_TYPES        = "meta.fixture_types"
    META_ROOM_COUNT           = "meta.room_count"
```

**Per-operator delta schemas (REVISED v0.5 to use DeltaKey enum)**:

| Operator | Expected | Allowed secondary | Forbidden |
|---|---|---|---|
| M0_BASE | `{}` | — | — |
| M1 | `{GEO_ROOM_POSITION_X}` | `{ADJ_EDGES_ORIENTATION}` | `{GEO_ROOM_AREA, META_FIXTURE_TYPES}` |
| M2 | `{GEO_ROOM_POSITION_Y}` | `{ADJ_EDGES_ORIENTATION}` | `{GEO_ROOM_AREA}` |
| M3a/b/c | `{GEO_STAIRCASE_POSITION}` | `{CIRC_CORRIDOR_ROUTING}` | `{META_ROOM_COUNT, GEO_ROOM_AREA}` |
| M4 | `{CIRC_CORRIDOR_TOPOLOGY}` | `{ADJ_EDGES, ZONE_ASSIGNMENTS}` | `{META_ROOM_COUNT}` |
| M5 | `{ZONE_ASSIGNMENTS}` | `{ADJ_EDGES, ZONE_PRIVACY_PATTERN}` | `{META_ROOM_COUNT}` |
| M6 | `{PLUMB_WET_WALL_ASSIGNMENT}` | `{PLUMB_TRAP_ARM_DISTANCES, PLUMB_RISER_GROUPS}` | `{GEO_ROOM_AREA, GEO_ROOM_POSITION_X}` |
| M7a/b | `{GEO_GRID_BAY_SIZE, GEO_ROOM_AREA}` | `{PLUMB_WET_WALL_ASSIGNMENT, PLUMB_TRAP_ARM_DISTANCES, GEO_ROOM_POSITION_X, GEO_ROOM_POSITION_Y}` | `{META_ROOM_COUNT, META_FIXTURE_TYPES}` |
| M8 | `{MULTI_MASTER_BR_FLOOR, MULTI_FLOOR_ASSIGNMENT}` | `{ADJ_EDGES}` | `{META_ROOM_COUNT, GEO_ROOM_AREA}` |
| M9a-d | `{GEO_ENTRY_POSITION}` | `{CIRC_PRIMARY_PATH}` | `{META_ROOM_COUNT, GEO_ROOM_POSITION_X, GEO_ROOM_POSITION_Y}` |

**Critical Inv 28** (NEW v0.5): every key in any
`OperatorExpectedDeltaSchema` set must be a `DeltaKey` enum value.
String literals not in the enum raise `OperatorRegistryError` at startup.

### § 2.3 through § 2.7 — Schema (carried v0.4 with type-tightening)

`upstream_regeneration_delta: tuple[DeltaKey, ...]` (was `tuple[str, ...]`).

### § 2.8 — Operator registry validation (REVISED v0.5 — adds severity audit)

`validate_operator_registry()` extended to call:

```python
def validate_severity_classification_audit() -> None:
    """NEW v0.5 — resolves critique #6 / F-v4-5.
    Walks the dependency graph of upstream exception types referenced
    by DeepMutationPipeline. Verifies every type carries `severity_tier`
    ClassVar with a value in {'per_candidate', 'batch', 'systemic'}.

    Raises:
        SeverityClassificationAuditError on any missing/invalid tier.
    """
```

### § 2.9 — Quarantine fingerprint (NEW v0.5 — resolves critique #5)

```python
@dataclass(frozen=True)
class QuarantineFingerprint:
    """NEW v0.5 — captures the runtime-quarantined-operators set.
    Replays with mismatched fingerprints REJECTED."""
    quarantined_operators: tuple[MutationOperator, ...]   # sorted lex-ASC
    quarantine_reasons: tuple[tuple[str, str], ...]       # (operator_value, reason)
    fingerprint_hash: str                                  # SHA256 of canonical-serialize


# Added to TopologyMutationProvenance:
@dataclass(frozen=True)
class TopologyMutationProvenance:
    # ... carried fields ...
    quarantine_fingerprint: QuarantineFingerprint    # NEW v0.5
```

**Replay rule** (NEW v0.5 / Inv 29 below): when comparing two replay
provenances, if `quarantine_fingerprint.fingerprint_hash` differs, the
replay is REJECTED — the two runs effectively executed different mutation
systems. Removes the "two environments produce different effective
results" risk from critique #5.

---

## § 3 — Behaviour (REVISED v0.5)

### Phase 0 — Input + startup validation (REVISED v0.5)

1. `validate_operator_registry()` (carried; extended)
2. `validate_upstream_purity_contract()` (carried v0.4)
3. **`validate_severity_classification_audit()` (NEW v0.5)**
4. Sunset-enforcement scan + waiver registry check (REVISED v0.5)
5. Per-config validation (carried)
6. **Concurrency assertion: assert single-threaded execution context (NEW v0.5)**

### Phase 1 through Phase 3 — (carried v0.4)

### § 3.4 — Tier A predicate orchestration (carried v0.4)

### § 3.5 — Tier B `DeepMutationPipeline` (carried v0.4)

### § 3.6 — M5 invalidation case (carried v0.4)

### § 3.7 — Cache-relevant per-field independent-mutation test discipline (NEW v0.5 — resolves critique #8)

For every `TopologyMutationConfig` field carrying
`metadata["cache_relevant"]`, the test suite includes:

1. **Cache-relevant field flip**: change one cache-relevant field; assert
   `derive_cache_config_hash` produces different output; assert
   `mutate_topologies` on identical inputs produces different
   `topology_variant_id` set or different counts.
2. **Cache-irrelevant field flip**: change one cache-irrelevant field;
   assert `derive_cache_config_hash` produces *same* output; assert
   mutation results identical.

**Test discipline only — no runtime addition.** ~24 tests added (12
config fields × 2 directions). Counted in v0.5 § 6 below.

---

## § 4 — Invariants (REVISED v0.5)

| # | Invariant | Mode |
|---|---|---|
| 1-27 | (carried verbatim from v0.4) | as v0.4 |
| **24 REVISED** | **`pending_upstream_predicate_count - len(active_waivers) == 0` AND `len(active_waivers) ≤ 3`. Waivers logged to `WAIVER_REGISTRY` source-constant.** | RAISE (LOCK gate) |
| **28 (NEW v0.5)** | **`OperatorExpectedDeltaSchema` keys MUST be `DeltaKey` enum values; string literals raise `OperatorRegistryError` at startup. (resolves critique #3)** | RAISE (startup) |
| **29 (NEW v0.5)** | **`QuarantineFingerprint.fingerprint_hash` mismatch between two replays = replay REJECTED. Cross-environment replay safety. (resolves critique #5)** | RAISE (replay tier) |
| **30 (NEW v0.5)** | **`mutate_topologies()` is single-threaded; multi-thread invocation is undefined behaviour. (resolves critique #9)** | DOCUMENTED (contract) |

**Total invariants at v0.5 LOCK candidate**: 30 (revised 24 + new 28-30).
27 RAISE-tier; 1 DESCRIPTIVE (Inv 14); 2 DOCUMENTED-tier (Inv 22 startup; Inv 30 contract).

---

## § 5 — Failure modes (REVISED v0.5)

```
TopologyMutationError (base)
├── PerCandidateError
│   ├── TopologyInvalidError
│   ├── MutationApplicationError
│   └── DeepMutationApplicationError
├── BatchAllNonBaseFailedError
├── OperatorRegistryError
├── DeepMutationPurityContractError
├── PendingUpstreamPredicateError
├── SeverityClassificationAuditError       (NEW v0.5)
└── InvariantViolationError                (systemic)
```

---

## § 6 — Test coverage targets (REVISED v0.5)

Target ~205 tests at LOCK (up from v0.4's 175):

- ~32 schema (+ `DeltaKey` enum, `UpstreamAmendmentWaiver`,
  `QuarantineFingerprint`)
- ~32 per-operator
- ~30 invariants (Inv 1-30)
- ~25 phase-logic
- ~12 partial-batch / strict-mode
- ~10 replay snapshot
- ~10 diagnostics
- ~10 v0.3 carry (registry validation, lineage classification, atomicity)
- ~14 v0.4 carry (purity, sunset, marker drift, registry quarantine,
  severity)
- **~30 NEW v0.5** — purity test suite per attestation (~10), severity
  audit (~3), quarantine fingerprint replay reject (~4), DeltaKey
  enum enforcement (~3), per-field independent-mutation cache discipline
  (~10; scoped to 5 representative fields at v1 per F-v5-3:
  `enabled_operators`, `max_seeds_per_input`, `deduplicate_by_signature`,
  `enforcement_mode`, `provenance_verbosity`; full 12-field combinatorial
  coverage deferred post-launch)

Cumulative target at C11a ship: 2314 + 205 ≈ **2519 passed**.

---

## § 7 — Open questions at v0.5

**0 open questions remaining.** All Q1, Q11, Q12, Q22 resolved at
Walk #5.

This is a **freeze signal**: open-question count has gone 15 → 9 → 6 →
4 → 0 across v0.1 → v0.5. Diminishing-returns territory.

---

## § 8 — Backlog at v0.5

**New at v0.5** (Walk #5 critique outcomes):

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-NEW-R | C11a `ComplexityScore` rubric (runtime/schema/replay/operational/governance cost annotations per subsystem) | W#5 #4 | next major spec round (any component) | M |
| B-NEW-S | C5 amendment: explicit structural / semantic / circulation split in TopologyFamilyDefinition | W#5 #7 | post-launch + observed family-classification ambiguity | M |
| B-NEW-T | C11a `DeltaCauseDescriptor` (causal lineage extension: operator-driven / constraint-remediation / heuristic-repair / optimization-induced) | W#5 #10 | post-launch + measured emergent classification ambiguity | M |
| B-NEW-U | C11a deterministic-parallel-semantics for `mutate_topologies` | W#5 #9 | scaling pressure on batch runtime | L |

**Cumulative**: 26 backlog items (4 pre-existing + 3 v0.1 + 3 v0.2 + 7 v0.3 + 5 v0.4 + 4 v0.5).

---

## § 9 — Rule 11 spec audit on v0.5 PROPOSED

**PATCH-NOW (in v0.5 itself): 0**.

**OPEN QUESTIONS at v0.5**: 0.

**SPEC-AUDIT FINDINGS (v0.5)**:

| # | Finding | Verdict |
|---|---|---|
| F-v5-1 | `UpstreamAmendmentWaiver.granted_by` field is governance metadata; if Ramalingam grants 5+ waivers, ad-hoc auditing fails. Inv 24 caps active waivers at 3, but no spec field tracks rolling waiver-issuance rate. | **DOCUMENTED** — operational; covered by source-controlled WAIVER_REGISTRY review. |
| F-v5-2 | `DeltaKey` enum has 18 entries at v0.5 first cut. Some operators reference forbidden keys that don't exist in any expected/allowed set (e.g., `META_FIXTURE_TYPES` — only forbidden, never expected). Should `META_FIXTURE_TYPES` be in the enum if no operator produces it? | **PATCH-NOW** — `META_*` keys retained because they're forbidden cross-operator (negative space matters); documented. |
| F-v5-3 | Per-field independent-mutation test discipline (§ 3.7) generates ~24 tests for 12 config fields × 2 directions. With `enabled_operators` having 16 enum entries, full combinatorial coverage explodes. Need scoped sample. | **PATCH-NOW** — sample 5 representative fields (enabled_operators, max_seeds_per_input, deduplicate_by_signature, enforcement_mode, provenance_verbosity) at v1; full coverage post-launch. Adjusted test count from ~24 to ~10. |
| F-v5-4 | `QuarantineFingerprint.fingerprint_hash` collision risk: SHA256 with sorted-tuple inputs is fine; but if `quarantine_reasons` contains free-form strings, two semantically-identical quarantines from different code paths produce different hashes. | **NEEDS WALK** OR **DOCUMENTED** — practically: quarantine_reasons should be enum'd; deferred to b-NEW-Q (post-launch). For v1, stringly-typed is acceptable. |
| F-v5-5 | Freeze candidacy claim in § 14: 0 open questions, audit findings count is dropping (10 v0.1 audit → 10 v0.2 → 8 v0.3 → 8 v0.4 → 5 v0.5). Diminishing returns supported empirically. | **CONVERGENCE-SIGNAL CONFIRMED** — see § 14. |

**PATCH-NOW APPLIED INLINE TO v0.5**:
- **F-v5-2**: Documented why `META_*` keys are in the enum (forbidden cross-operator).
- **F-v5-3**: Per-field independent-mutation test discipline scoped to 5 representative fields at v1 (not all 12); ~10 tests not ~24. Updated § 6 above.

**REJECTED-AS-CONSIDERED**:
- "Should `WAIVER_REGISTRY` track *historical* expired waivers?" Source
  history is the audit trail; runtime tracking adds complexity for no value.
- "Should `QuarantineFingerprint` include the validation mode used?" Already
  implied by the quarantine state itself; no extra field needed.

---

## § 10 — Status

- **v0.5 PROPOSED**. **NOT LOCKED.**
- **Freeze candidate**: proposing v0.5 as final walk before LOCK request.
- 12 valid critique items resolved (5 amendments + 4 backlog + 1 longterm-doc + 1 convergence-signal + 1 already-routed). 0 MISFRAMED.
- **0 open questions remain.**
- 26 backlog items.
- Signals favour LOCK request: 0 open questions; 5 audit findings (down from 10/10/8/8); diminishing-returns pattern in critique value-add.
- Ramalingam adjudication path:
  - **(a) Approve LOCK request → C11a v1.0 LOCKED at Walk #5.**
  - **(b) Request Walk #6 → continue spec arc; identify what would reach LOCK.**

---

## § 12 — Backlog enumeration

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-217 / B-220 / B-237 / B-238 | (carried; pre-existing) | S35 | various |
| B-NEW-A through B-NEW-Q | (carried v0.1-v0.4; 17 items) | W#1-W#4 | various |
| **B-NEW-R** | **`ComplexityScore` rubric** | **W#5 #4** | **M** |
| **B-NEW-S** | **C5 amendment: TopologyFamilyDefinition split** | **W#5 #7** | **M** |
| **B-NEW-T** | **`DeltaCauseDescriptor` causal lineage** | **W#5 #10** | **M** |
| **B-NEW-U** | **C11a deterministic-parallel-semantics** | **W#5 #9** | **L** |

**Backlog summary**:

| Total | Pre-existing | v0.1 | v0.2 | v0.3 | v0.4 | v0.5 |
|---|---|---|---|---|---|---|
| **26** | 4 | 3 | 3 | 7 | 5 | 4 |

---

## § 13 — Complexity Budget (REVISED v0.5)

### v1 surface area: 18 subsystems

| # | Subsystem | Status |
|---|---|---|
| 1-16 | (carried v0.4 — 16 subsystems) | unchanged |
| **17 (NEW v0.5)** | **DeltaKey canonical enum** | enforces critique #3 fix |
| **18 (NEW v0.5)** | **QuarantineFingerprint** | enforces critique #5 fix |

### What v0.5 explicitly does NOT add to v1

| Considered | Routing |
|---|---|
| ComplexityScore rubric (item 4) | B-NEW-R (process tooling, not C11a runtime) |
| TopologyFamilyDefinition semantic split (item 7) | B-NEW-S (C5 amendment, not C11a) |
| DeltaCauseDescriptor (item 10) | B-NEW-T (post-launch causal extension) |
| Deterministic parallel mutation (item 9) | B-NEW-U (post-launch scale work) |
| Replay containers / migration (item 12) | B-NEW-N expansion (already filed) |
| PurityVerificationTestSuite as runtime subsystem (item 1) | Demoted to **test discipline** — no v1 subsystem cost |
| Per-field cache test discipline (item 8) | Demoted to **test discipline** — no v1 subsystem cost |

### Walk #5 budget adherence

- Walk #5 budget cap was 0-2 new v1 subsystems.
- **Walk #5 added: 2 (DeltaKey enum, QuarantineFingerprint)**. At cap.
- 5 critique items routed to backlog/longterm without v1 cost.
- 2 critique items addressed via test-discipline only (no runtime addition).
- Walk #5 within governance constraints.

### Recommendation: hard freeze post-Walk #5

Walks #6+ should accept ZERO new v1 subsystems. Only:
- Correctness fixes
- Replay integrity fixes
- Determinism fixes
- Critical bugs surfaced in implementation

Walk #5 critique #11 (architecture accretion) supports this freeze
boundary; § 14 below operationalizes it.

---

## § 14 — Freeze candidacy rationale (NEW v0.5)

This section makes the case for v0.5 → v1.0 LOCK at Walk #5.

### § 14.1 — Convergence signals (empirical)

| Walk | Audit findings | Open Qs | New v1 subsystems | Critique items resolved |
|---|---|---|---|---|
| v0.1 | 10 | 15 | 16 (initial) | (seed) |
| v0.2 | 10 | 9 | +0 (refinement) | 12 |
| v0.3 | 8 | 6 | +0 (refinement) | 12 |
| v0.4 | 8 | 4 | +0 (refinement) | 12 |
| v0.5 | 5 | **0** | **+2** | 12 |

**Pattern**: open questions strictly monotone-decreasing. Audit findings
strictly non-increasing. Critique resolution count steady (~12 per
walk = reviewer is finding things, but they're routing to
backlog / longterm now, not v1 amendments).

### § 14.2 — Industry standard (research-validated)

Spec freeze fires when subsequent iteration produces similar insights
rather than new discoveries; design lock when iteration yields
diminishing returns.

Walk #5 routes:
- 5 of 12 to backlog-with-trigger (post-launch w/ specific data condition)
- 1 of 12 to longterm-doc
- 1 of 12 IS the convergence signal itself (item 11)
- 1 of 12 already-routed
- 4 of 12 amendments — all governance refinement, no new architectural surface

The reviewer themselves write item 11: *"the system is no longer
struggling with basic architecture; it is now struggling with scaling
governance complexity."* Governance can scale post-LOCK via backlog;
correctness cannot. v0.5 has correctness covered.

### § 14.3 — Counter-arguments to LOCK now

1. **Upstream amendments not yet shipped (B-NEW-J/K/L/P)**. Real
   blocker. Mitigation: § 0.2 waiver mechanism handles edge cases;
   amendment cluster is XS-effort × 4 = 1-2 sessions.
2. **Implementation may surface new bugs**. True for every spec.
   Walks #6+ as patch rounds remain available; LOCK isn't permafrost.
3. **Tier B caching effectiveness unmeasured**. Empirical question;
   needs implementation. Cache disabling escape hatch in config.

None of these are *spec-arc-resolvable* concerns. They are
implementation concerns. Spec arc has done its job.

### § 14.4 — Proposed LOCK preconditions

For Ramalingam adjudication:

1. **Waiver mechanism activated** (§ 0.2): up to 3 active waivers
   permitted at v1.0 LOCK; sunset enforcement deferred to ceiling.
2. **Upstream amendments B-NEW-J/K/L/P**: scheduled as separate sessions
   before C11a build start (sequencing per Inv 24 LOCK gate). Not all
   blocking LOCK proposal — LOCK can be granted contingent on amendments
   landing within waiver window.
3. **B-237 cross-platform replay CI**: not blocking LOCK; blocking
   pre-launch (already gated).
4. **No spec changes beyond audit-finding patches** until C11a v1
   build complete.

### § 14.5 — Recommendation

**Request LOCK at Walk #5**. Decision is yours per Rule 8.

If LOCK denied: Walk #6 should focus on what *specifically* would
trigger LOCK, not on uncovering new architectural surface.

---

**End of v0.5 PROPOSED.** Awaits Ramalingam's adjudication: Walk #6 or
LOCK.
