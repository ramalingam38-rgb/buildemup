# C11a — Topology Mutation Layer — SPEC v0.1 PROPOSED

**Component**: 11a (canonical Track 3 numbering — paired with C11b NSGA-II)
**Status**: v0.1 PROPOSED. **NOT LOCKED.** Walk #1 seed.
**Authority**: S37 Walk #1 author's draft. PENDING Ramalingam adjudication.
**Authored**: S37 Walk #1, post-C10 v1.0 LOCKED.

---

## § 0 — Architectural notes

C11a sits between C10 (Wet-Zone Stack Planner) and C11b (NSGA-II Local Refinement). Its job is **topology-level** generation: produce 6-8 distinct candidate seeds per input topology by applying domain-specific mutation operators, validating each against HARD constraints, and emitting valid seeds. C11b then runs NSGA-II Pareto search on these seeds for *geometric* refinement.

**Pipeline position**:
```
C10 → C11a (THIS) → C11b → C12 → C13 → C14
```

**What C11a IS**:
- Deterministic application of a fixed mutation operator catalog
- HARD-constraint validation per produced seed (reject infeasible mutations early)
- Per-input-candidate seed multiplication (1 input → ≤ N valid seeds)

**What C11a is NOT** (recurring scope-creep risks; surfaced now to anticipate Walk #2 critique):
- **NOT NSGA-II Pareto search.** Multi-objective optimization is C11b. (Anticipated reviewer push: "why not score the seeds during mutation?" — declined; that's C14's job, scored by C11b.)
- **NOT room placement geometry.** Per-room x/y/w/h finalization is C12. C11a operates on topology variants, not realized geometry.
- **NOT scoring or evaluation.** No seed gets a quality score in C11a. Score is C14.
- **NOT user-facing.** No rendering, no explanation strings beyond provenance trace. C16 is the renderer.
- **NOT crossover.** Composing two seeds into a hybrid is NSGA-II's job (C11b). v1 of C11a applies single operators only — no operator stacking.
- **NOT learning from prior runs.** Mutation operator selection is config-driven, not adaptive. Adaptive operator selection per Wong & Chan (EvoArch) is post-v1.

**Architectural divergence from research literature** (raised at Walk #1, expect critique):

EvoArch (Wong & Chan, 2009) uses abstract adjacency-matrix mutations — Number-of-Node, Number-of-Edge, Node-Label, Swap-Node. This is domain-agnostic but loses semantic meaning (a "Swap-Node" mutation could place the kitchen between two bedrooms, which never makes sense in Indian residential).

C11a takes the opposite approach: a **fixed catalog of 9 domain-specific operators** drawn from Indian residential typology patterns (per `BuildemUp_Walkthrough_NE_30x40.md` § 5). This sacrifices generality for semantic validity — every mutation produces something an Indian builder would recognize as a plausible alternative. The trade-off is reduced operator novelty; we may miss layouts that abstract mutation would surface. **Q14 surfaces this for Walk #2.**

---

## § 1 — Walk-resolved scope

| Q | Resolution | Walk |
|---|---|---|
| (none) | v0.1 has no walk-resolved scope. First scope decisions land at Walk #2. | — |

---

## § 2 — Contract

```python
def mutate_topologies(
    wet_zoned_candidates: tuple[WetZonePlannedCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    *,
    config: TopologyMutationConfig | None = None,
) -> tuple[MutatedTopologyCandidate, ...]:
    """C11a entry point. Per-candidate semantics mirror C9/C10 § 14.40
    partial-batch tolerance: failures aggregate; output tuple may be
    shorter than (input_count × seeds_per_input) bound."""
```

`MutatedTopologyCandidate` carries the source `WetZonePlannedCandidate`, the applied operator, the resulting topology variant id, and a provenance trail.

### Schema (v0.1 — heavy on placeholders, expect Walk #2 sharpening)

```python
class MutationOperator(str, Enum):
    """The 9 base operators + their variants. v0.1 catalog mirrors
    Walkthrough § 5; subject to Walk #2 review (Q1)."""
    M0_BASE         = "m0_base"          # the unmutated input — always emitted
    M1_HORIZ_FLIP   = "m1_horiz_flip"    # E ↔ W
    M2_VERT_FLIP    = "m2_vert_flip"     # N ↔ S
    M3A_STAIR_EAST  = "m3a_stair_east"
    M3B_STAIR_WEST  = "m3b_stair_west"
    M3C_STAIR_NE    = "m3c_stair_ne_corner"
    M4_CORRIDOR_INV = "m4_corridor_inv"  # central → edge
    M5_ZONE_SWAP    = "m5_public_private_swap"
    M6_WET_ROTATE   = "m6_wet_wall_rotate"
    M7A_GRID_3_3    = "m7a_grid_scale_3_3"
    M7B_GRID_2_7    = "m7b_grid_scale_2_7"
    M8_VERT_REARR   = "m8_master_floor_swap"
    M9A_ENTRY_CTR   = "m9a_entry_ne_center"
    M9B_ENTRY_W     = "m9b_entry_ne_corner_w"
    M9C_ENTRY_E     = "m9c_entry_ne_corner_e"
    M9D_ENTRY_OFF   = "m9d_entry_offset_ne"


@dataclass(frozen=True)
class MutationApplicationResult:
    """Per-attempt outcome. Tracked in provenance regardless of valid/invalid
    so the seed-generation funnel is auditable."""
    operator: MutationOperator
    valid: bool
    invalidity_reason: str | None     # populated iff valid=False
    topology_variant_id: str | None   # populated iff valid=True
    rejection_invariant_id: str | None  # which Inv N+component caused reject


@dataclass(frozen=True)
class MutatedTopologyCandidate:
    """Output unit. One per (source candidate × valid mutation)."""
    source_candidate: WetZonePlannedCandidate
    applied_operator: MutationOperator
    topology_variant_id: str          # SHA256-prefix or deterministic name
    application_result: MutationApplicationResult
    provenance: TopologyMutationProvenance


@dataclass(frozen=True)
class TopologyMutationConfig:
    enabled_operators: tuple[MutationOperator, ...] = field(
        default_factory=lambda: tuple(op for op in MutationOperator)
    )
    max_seeds_per_input: int = 8
    deterministic_order: bool = True
    emit_base: bool = True            # always include M0_BASE in output
    deduplicate_by_signature: bool = True   # see Q2
    enforcement_mode: EnforcementMode = EnforcementMode.WARN


@dataclass(frozen=True)
class TopologyMutationProvenance:
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    enabled_operators_snapshot: tuple[str, ...]
    operator_application_log: tuple[MutationApplicationResult, ...]
    accepted_count: int
    rejected_count: int
    deduplicated_count: int           # collapsed by signature
    truncated_at_max_seeds: bool
    rule_trace: tuple[str, ...]
    _observational_runtime_ms: int    # excluded from replay hashes
```

---

## § 3 — Behaviour

### Phase 0 — Input validation

Verify input tuple non-empty (or return empty tuple if input empty), config sane (`max_seeds_per_input ≥ 1`, `enabled_operators` non-empty if `emit_base=False`).

### Phase 1 — Per-candidate seed generation

For each `WetZonePlannedCandidate` in input, in input order:

1. If `config.emit_base`: emit `M0_BASE` as seed 0 (always valid by definition).
2. For each operator in `config.enabled_operators`, in lex-ASC of operator name (determinism, Q5):
   - Apply operator (operator-specific mutation logic — see § 3.5).
   - Validate against HARD constraint set (§ 3.4).
   - If valid: compute `topology_variant_id = signature_hash(mutated_state)`.
   - If `config.deduplicate_by_signature` AND signature already seen: skip; record as deduplicated.
   - Otherwise: append to per-input accept buffer.
3. If accept-buffer exceeds `max_seeds_per_input`: truncate (keep first N — deterministic by enumeration order); emit `truncated_at_max_seeds=True`.

### Phase 2 — Output assembly

Concatenate per-candidate accept buffers in input order. Emit `MutatedTopologyCandidate` tuple.

### Phase 3 — Provenance

Per source candidate, build `TopologyMutationProvenance` with full operator-application log (accepted, rejected, deduplicated). Aggregate runtime via `time.monotonic()`; tag as observational only.

### § 3.4 — HARD constraint set (v0.1 placeholder)

A mutation is REJECTED if applying it produces:
- Wet-zone wall assignment violation (collapses to C10 Inv 4/5/5b/6 already-validated state)
- Privacy / acoustic violation (e.g., M2 vertical-flip placing bedrooms on the road-facing side)
- Furniture-fit violation (e.g., M7b 2.7m grid producing rooms below `liveability_min_width_m`)
- Vastu HARD violation (Vastu is INFO-only per project Inv 7 — but bedroom-on-toilet stack is HARD; needs Walk #2 to enumerate)
- Master-bath adjacency loss (per C9 Inv 13)

**Q4 surfaces**: enumerate the full HARD set explicitly per operator, or check via re-running C5–C10 invariants on the mutated state? Re-running is expensive but rigorous; per-operator enumeration is fast but error-prone.

### § 3.5 — Per-operator mutation logic (v0.1 placeholder, all 9 operators)

Each operator gets a small mutation function. Sketches at v0.1:

| Operator | Mutation summary |
|---|---|
| M0_BASE | identity — emit unchanged |
| M1_HORIZ_FLIP | reflect all room x-coords across grid centerline |
| M2_VERT_FLIP | reflect all room y-coords (flagged: privacy check often fails) |
| M3A/B/C | move staircase to designated wall position |
| M4_CORRIDOR_INV | move corridor from central spine to edge wall |
| M5_ZONE_SWAP | swap public-zone and private-zone rooms across the corridor |
| M6_WET_ROTATE | rotate wet-zone wall assignment 90° (C10's wet_wall_assignment regenerated) |
| M7A/B | scale grid bay size; re-run C7 grid generation; re-derive C9 sizing |
| M8 | swap master-bedroom floor (GF↔FF in multi-floor briefs) |
| M9A/B/C/D | relocate entry door |

Operators M6, M7, M8 require **upstream re-run** (C7 or C9 regeneration). v0.1 places this in a "deep mutation" tier; Q6 questions whether deep mutations belong in v1 or should defer to v2.

---

## § 4 — Invariants (v0.1, expect expansion)

| # | Invariant | Mode |
|---|---|---|
| 1 | Every `MutatedTopologyCandidate.source_candidate` exists in input tuple | RAISE |
| 2 | Every `applied_operator ∈ config.enabled_operators` (or `M0_BASE` if `emit_base=True`) | RAISE |
| 3 | Per source candidate, accepted count ≤ `config.max_seeds_per_input` | RAISE |
| 4 | Output ordered: input-order outer, operator lex-ASC inner | RAISE |
| 5 | `topology_variant_id` unique within a single source candidate's accepts | RAISE |
| 6 | If `emit_base=True`, M0_BASE always present per source candidate | RAISE |
| 7 | Mutation pure function: `(source, operator, config) → result` is reproducible | RAISE (replay tier) |
| 8 | HARD-constraint validation passes for every output (no "approved but infeasible") | RAISE |
| 9 | Provenance log entries sum: accepted + rejected + deduplicated = total attempts | RAISE |
| 10 | `_observational_runtime_ms` not in any replay-hash computation | RAISE (replay discipline) |

---

## § 5 — Failure modes

```
TopologyMutationError (base)
├── PerCandidateError
│   ├── TopologyInvalidError          (no operator produced a valid seed)
│   ├── MutationApplicationError      (operator function raised internally)
│   └── DeepMutationRerunError        (M6/M7/M8 upstream re-run failed)
├── BatchMutationFailedError          (all input candidates failed)
└── InvariantViolationError           (systemic — Inv 7 reproducibility violated)
```

Per-candidate errors aggregate (mirrors C9/C10 partial-batch). Systemic errors short-circuit the batch.

---

## § 6 — Test coverage targets

Target ~100 tests at LOCK (estimated; revise per walk arc):
- ~25 schema tests (operator enum, dataclasses, config validation)
- ~30 per-operator tests (one happy + one invalidating fixture per operator × 15 operators ≈ 30)
- ~20 invariant tests (Inv 1-10 across modes)
- ~15 phase-logic tests (Phase 0 input validation, Phase 1 dedup, Phase 2 assembly, Phase 3 provenance)
- ~10 partial-batch / strict-mode escalation
- ~5 deterministic-replay snapshot tests

Cumulative target at C11a ship: 2314 + 100 ≈ **2414 passed**.

---

## § 7 — Open questions surfaced at v0.1

| Q | Question | Walk #1 proposed direction |
|---|---|---|
| Q1 | Is the 9-operator catalog complete, or should v1 ship with fewer (e.g., M2/M5 are high-rejection operators)? | Ship all 9 at v1; let HARD-rejection rate tell us; trim post-launch. |
| Q2 | Deduplication: signature-hash on what state? Adjacency matrix only, or full geometric snapshot? | v1: adjacency matrix + room-to-zone mapping (cheaper); full geo at C11b. |
| Q3 | Operator composition (apply M1 then M3a)? | NO at v1 — single-operator only. Composition is C11b NSGA-II crossover. |
| Q4 | HARD constraint set — explicit enumeration vs re-run upstream invariants? | Hybrid: enumerate for shallow ops (M1/M2/M3/M4/M5/M9); re-run for deep ops (M6/M7/M8). |
| Q5 | Deterministic order — operator lex-ASC, or operator-priority? | Lex-ASC. Priority is a scoring concept; doesn't belong here. |
| Q6 | Deep mutations (M6/M7/M8) — v1 or v2? | v1 includes them (skipping reduces seed diversity); pay the runtime cost. |
| Q7 | Filter Pareto-dominated seeds at C11a output, or pass everything to C11b? | NO filtering at C11a. C11b is the sole search authority. |
| Q8 | `topology_variant_id` derivation — hash, sequence, or human-readable? | SHA256-12char-prefix of canonical state JSON; deterministic, brief. |
| Q9 | Invalid-mutation logging — silent drop, log-only, or surface in output? | Surface in provenance log; do NOT emit as outputs (would pollute downstream). |
| Q10 | Per-operator config knobs (e.g., M3 staircase locations beyond a/b/c)? | None at v1. Operator catalog is fixed. Knobs invite scope creep. |
| Q11 | M7 grid scale set (3.0, 3.3, 2.7) — fixed, or KB-driven? | KB-driven post-v1 (B-NEW); fixed at v1 mirroring Walkthrough. |
| Q12 | Multi-floor briefs — does C11a mutate per-floor or building-wide? | Building-wide (M8 master-floor-swap is meaningless per-floor). |
| Q13 | Determinism across Python versions / OSes — handled by canonical_serialize? | Yes; reuses C7 amendment v0.8 utility. |
| Q14 | Domain-specific catalog vs abstract graph mutations (research divergence) | Stay domain-specific at v1; semantic validity > novelty for Indian residential. |
| Q15 | Should `m0_base` count against `max_seeds_per_input` or be free? | Free (it's the unchanged input). Bound applies to mutated seeds. |

---

## § 8 — Backlog at v0.1

**Existing items that affect C11a**:

| ID | Description | Affects C11a |
|---|---|---|
| B-217 | Polygonal envelopes / spatial partitioning | Affects M9 entry mutations on non-rectangular plots; M1/M2 flip semantics on non-axis-aligned plots |
| B-220 | Hydraulic primitives + plumbing-engineer review | Indirect: M6 wet-wall rotation may produce hydraulically-questionable layouts that pass C10's partial-hydraulics check |
| B-238 | Independent architect review | Direct: 9-operator catalog is exactly the kind of cultural/spatial logic an architect should review |
| B-237 | Cross-platform replay CI matrix | Direct: C11a determinism depends on it |

**New items proposed at v0.1**:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-NEW-A | C11a M7 grid-scale KB (replace fixed 3.0/3.3/2.7 with KB-driven set) | S37 Walk #1 Q11 | post-launch | XS |
| B-NEW-B | C11a cross-operator composition (M1 ∘ M3a etc.) for v2 | S37 Walk #1 Q3 | C11b stable + measured under-coverage | M |
| B-NEW-C | C11a abstract graph mutation operators (EvoArch-style) for layout novelty | S37 Walk #1 Q14 | post-launch + B-238 architect review | L |

---

## § 9 — Rule 11 spec audit on v0.1 PROPOSED

Per Rule 11 (LOCKED at S34), proactive audit before requesting LOCK. **Note**: not requesting LOCK at v0.1; this is the seed. Audit findings inform Walk #2 direction.

**PATCH-NOW (in v0.1 itself): 0** — drafting itself is the patch round.

**OPEN QUESTIONS surfaced**: Q1-Q15 above.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v1-1 | The HARD constraint set in § 3.4 is a placeholder (re-run upstream vs explicit enumerate). Without resolving Q4, "validity" is ambiguous and tests cannot assert specific reject reasons. | **NEEDS WALK** — Q4 must resolve before LOCK. |
| F-v1-2 | M6/M7/M8 require upstream re-run (C7/C9 regeneration). This collapses the C7→...→C10 chain re-execution into C11a, which is a heavy coupling. Should deep operators be a separate phase? Or should C11a only consume re-executed candidates from a deep-mutation pre-pass? | **NEEDS WALK** — architectural separation question. |
| F-v1-3 | `topology_variant_id` derivation (Q8) — hash of what canonical state? If it includes `_observational_runtime_ms` accidentally, replay snapshots break. Need explicit field-exclusion list. | **NEEDS WALK** — defines the canonical-state surface. |
| F-v1-4 | Per-operator mutation logic (§ 3.5) is sketched in a one-line table. Each operator deserves a fully specified algorithm with input invariants and output guarantees. | **NEEDS WALK** — Walk #3-#4 should pin down per-operator algorithms. |
| F-v1-5 | The `MutationOperator` enum couples base operators (M1, M4, M5, M6, M8) and variants (M3a/b/c, M7a/b, M9a/b/c/d) flatly. A two-level structure (operator family + variant) would be more accurate but adds enum complexity. | **NEEDS WALK** — schema-shape discussion. |
| F-v1-6 | `enabled_operators` config defaults to all-on, but M2 and M5 have very high HARD-rejection rates per the Walkthrough. A "default-on minus M2/M5" config might be more honest about real-world acceptance. | **NEEDS WALK** — config defaults debate. |
| F-v1-7 | No explicit notion of "topology family" — Central Spine / Courtyard / Strip per arch v3 § 2. C5 emits these; C11a mutations may or may not preserve family. Spec is silent on whether topology family changes are valid. | **NEEDS WALK** — relate to C5 output. |
| F-v1-8 | No replay-snapshot test target listed in § 6. C7 amendment v0.8 W8 invariant says canonical accessor is mandatory in production code; C11a needs the equivalent. | **NEEDS WALK** — replay discipline borrowed from C7. |
| F-v1-9 | `BatchMutationFailedError` triggers when "all input candidates failed", but if every input candidate emits at least M0_BASE (which is always valid), this error is unreachable in practice. Either drop it from the hierarchy or define it more carefully. | **NEEDS WALK** — failure-mode reality check. |
| F-v1-10 | Test target ~100 is hand-wavy. C9 shipped 250+, C10 shipped 138 against a 175 target. Need a more grounded estimate after Walk #2 sharpens the per-operator algorithms. | **NEEDS WALK** — re-estimate post-#3. |

**Self-coverage measurement**: 10 findings caught in v0.1 audit — comparable to C10 v0.4 audit which surfaced 10 findings. The honest expectation is that Walk #2 reviewer will surface ~12-15 additional items (specs at v0.1 are inevitably underspecified).

**REJECTED-AS-CONSIDERED**:
- "Should C11a maintain a topology genealogy tree showing which seed derived from which input?" — Too much state; provenance log already records source_candidate + operator. Sufficient for replay.
- "Should C11a measure topology diversity (Hamming distance between seeds)?" — That's an evaluation concept; belongs to C14 or C11b's NSGA-II crowding distance.
- "Should each MutatedTopologyCandidate carry a regenerated WetZonePlannedCandidate (after re-running C10)?" — For shallow operators no. For deep operators (M6/M7/M8) yes — but that's part of F-v1-2's resolution.

---

## § 10 — Status

- **v0.1 PROPOSED**. **NOT LOCKED.**
- LOCK NOT REQUESTED at v0.1; standard practice from C10 / C7-amendment arcs is multi-walk convergence.
- Estimated walks to LOCK: **5-9** (matching C10's arc; C7 amendment took 8 walks).
- Walk #2 should resolve at minimum: F-v1-1 (HARD constraint set), F-v1-2 (deep operator re-run architecture), Q4 (validity check strategy), Q8 (variant_id derivation surface).
- 0 backlog items closed; 3 new B-NEW items proposed (filing on Ramalingam direction per Rule 9.2).

---

## § 12 — Backlog enumeration (per Rule 9)

Spec-relevant backlog items, enumerated for visibility:

| ID | Description | Origin | S{N}-scope verdict | Effort |
|---|---|---|---|---|
| B-217 | Polygonal envelopes spatial partitioning | S35 | Affects C11a M9/M1/M2 on non-rectangular plots; v2 work | L |
| B-220 | Hydraulic primitives + plumbing-engineer review | S35 | Pre-launch hard gate; affects C11a M6 acceptability standard | L |
| B-237 | Cross-platform replay CI matrix | S35 Walk #6+#9 | Affects C11a determinism (Inv 7) | M |
| B-238 | Independent architect review | S35 Walk #6 | Direct review target for the 9-operator catalog | M |
| B-NEW-A | C11a M7 grid-scale KB-driven set | S37 Walk #1 Q11 | post-launch trim | XS |
| B-NEW-B | C11a cross-operator composition for v2 | S37 Walk #1 Q3 | C11b stable + measured coverage | M |
| B-NEW-C | C11a abstract graph mutation operators (EvoArch-style) | S37 Walk #1 Q14 | post-launch + B-238 review | L |

**Backlog summary table**:

| Total | Pre-existing | New at v0.1 |
|---|---|---|
| 7 | 4 | 3 |

---

**End of v0.1 PROPOSED.** Awaits Ramalingam's reading + Walk #2 direction.
