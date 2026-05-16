# C12 — Multi-Floor Placement & Vertical Alignment Engine — SPEC v0.1 PROPOSED

**Component**: 12 (canonical Track 3 numbering — consumes C11b RefinedCandidates and C10 MultiFloorWetZonePlannedCandidates; feeds C13 Door Placement)

**Status**: v0.1 PROPOSED. **NOT LOCKED.** Walk #1 seed.

**Authority**: S43 Walk #1 author's draft. PENDING Ramalingam adjudication.

**Scope decision (locked at S42 close)**: **C12-Wide** — vertical alignment + single-floor geometric placement + multi-floor refinement absorption.

**Authored**: S43 Walk #1, post-C11b v1.1 LOCKED.

---

## § 0 — Architectural notes

C12 sits between C11b (Local NSGA-II Refinement) and C13 (Door Placement). Its job is **geometric realization**: take refined parameter vectors (room dimensions from C11b) or rejected multi-floor candidates (from C10 via C11b's MF-rejection path) and produce fully placed geometry — every room with absolute `(x, y, width, depth)` coordinates inside the envelope, every floor verified for embeddability, and multi-floor outputs verified for vertical alignment (columns, wet-stacks, staircases) across floors.

**Pipeline position**:

```
C10 → C11a → C11b ──single-floor──> C12 → C13 → C14
                │
                └──multi-floor rejection────┘
                                            (C12 absorbs at v1)
```

**What C12 IS (the C12-Wide scope adopted at S42 close)**:

- **Single-floor placement (SFP)**: turn each `RefinedCandidate.refined_parameters.room_dimensions` (room IDs + width/depth pairs) into placed rectangles inside the envelope. Verify geometric embeddability (no overlap, fully contained, adjacency hints from C8 honoured to the extent feasible).
- **Vertical alignment verification (VAV)**: for multi-floor candidates, verify that structural columns, wet-zone stacks, and staircase landings/runs align across floors within tolerance. Emit per-floor placed geometry plus alignment metadata.
- **Multi-floor refinement absorption (MFRA)**: gateway for `MultiFloorWetZonePlannedCandidate` inputs that C11b rejected via `MultiFloorRefinementNotSupportedError`. Per-floor SFP + VAV iteration loop, bounded retries.
- **Capability-flag enforcement at consume time**: per B-C12-MATERIALIZATION-CONTRACT (filed during C11b walks), assert `placement_safe == True AND geometry_materialized == True` on every input `RefinedCandidate` before placement. Tier A SHALLOW candidates (PREDICATE_ONLY) MUST resolve their pending transforms before reaching C12 — that resolver step is C12's first action on Tier A input.

**What C12 is NOT** (recurring scope-creep risks; surfaced now to anticipate Walk #2 critique):

- **NOT scoring or evaluation.** C12 produces placed geometry; C14 scores it. A placement that is geometrically valid but architecturally poor (e.g., dark interior bedroom) is still emitted; quality judgement is C14's job.
- **NOT door / window placement.** Once rooms are placed, C13 picks door positions on shared walls. C12 emits placed rectangles + shared-edge adjacency graph; that's all C13 needs.
- **NOT NSGA-II.** C11b already ran multi-objective optimization on parameter vectors. C12's job is to *realize* the chosen parameters as geometry, not to re-search. If SFP can't place a given parameter vector, the candidate is rejected (or repaired under lenient mode per Q-9 below); no Pareto search re-runs.
- **NOT a renderer.** Coordinates are produced; visual output is C16.
- **NOT a structural engineer.** Column-alignment verification is geometric (do columns at floor N and floor N+1 share `(x, y)` within tolerance?). Load-path analysis is post-v1.
- **NOT user-facing.** No explanation strings beyond provenance trace. Human-language reports are C14/C16.

**Architectural divergence from VLSI literature** (raised at Walk #1, expect critique):

VLSI floorplanning (sequence-pair, Q-sequence, simulated annealing per Tang & Wong 2001) is the canonical placement-algorithm literature. Those techniques assume *flexible* module shapes (sized rectangles with adjustable aspect ratios) and optimize for wirelength + area; they're solving a different problem.

C12 takes the opposite assumption: room dimensions are **already fixed** by C11b's NSGA-II refinement. C12's job is not to optimize layout area — it's to *verify* whether the chosen dimensions admit a valid placement at all, and to produce one if so. This means C12's "placement algorithm" is much closer to a *feasibility checker with backtracking* than a continuous optimizer. The trade-off is reduced placement quality vs the literature, but tight coupling to C11b's chosen parameter vector (which is the point — C11b is where multi-objective trade-offs are made). **Q-1 surfaces the algorithm choice for Walk #2.**

---

## § 1 — Walk-resolved scope

| Q | Resolution | Walk |
|---|---|---|
| (none) | v0.1 has no walk-resolved scope. First scope decisions land at Walk #2. | — |

---

## § 2 — Contract

### § 2.1 — Top-level signature

```python
def place_and_align(
    *,
    single_floor_inputs: tuple[RefinedCandidate, ...] = (),
    multi_floor_inputs: tuple[MultiFloorWetZonePlannedCandidate, ...] = (),
    grid: Grid,
    plot_analysis: PlotAnalysis,
    floor_room_brief: FloorRoomBrief,
    config: PlacementConfig | None = None,
    expected_environment_fingerprint: EnvironmentFingerprint | None = None,
) -> PlacementBatchResult:
    """
    C12 entry point. Accepts BOTH single-floor and multi-floor inputs;
    routes each through the appropriate sub-engine (SFP / MFRA).

    Returns PlacementBatchResult with:
      - placed_candidates: tuple of single-floor placed outputs
      - multi_floor_placed_candidates: tuple of MF placed outputs
      - provenance: PlacementProvenance (env fingerprint + counters
                   + per-input telemetry, mirroring C11b § 2.1 shape)
      - failure_summaries: structured records, NOT strings
                          (per B-C11B-FAILURE-SCHEMA-V2 from S42
                           critique — C12 adopts the structured form
                           from day one rather than carrying C11b's
                           string-based debt forward)
    """
```

### § 2.2 — Schema additions

```python
@dataclass(frozen=True)
class PlacedRoom:
    """One room placed at absolute coordinates inside the envelope."""
    room_id: str
    x_m: float          # bottom-left corner, x coordinate (metres)
    y_m: float          # bottom-left corner, y coordinate (metres)
    width_m: float      # x-extent
    depth_m: float      # y-extent
    floor_index: int    # 0 = ground floor; 1 = first floor; etc.


@dataclass(frozen=True)
class SharedEdge:
    """Adjacency between two PlacedRoom instances; consumed by C13."""
    room_a_id: str
    room_b_id: str
    axis: Literal["vertical", "horizontal"]   # of the shared edge
    overlap_start_m: float                     # along the shared axis
    overlap_end_m: float
    overlap_length_m: float                    # convenience: end - start


@dataclass(frozen=True)
class PlacedCandidate:
    """One single-floor placed candidate. Inv 18+ from C11b's
    'area-feasible by construction' is upgraded here to
    'geometry-realized by construction'."""
    placed_rooms: tuple[PlacedRoom, ...]
    shared_edges: tuple[SharedEdge, ...]
    source_refined_candidate_signature: str    # provenance back to C11b
    floor_index: int                            # 0 at v1 single-floor
    envelope_width_m: float
    envelope_depth_m: float
    placement_algorithm_used: Literal["slicing_kd_tree", "csp_fallback"]
    # geometry-materialized flag from upstream RefinedCandidate; MUST be True.
    geometry_materialized: bool = True


@dataclass(frozen=True)
class VerticalAlignmentReport:
    """Per-multi-floor candidate alignment audit."""
    columns_aligned: bool
    wet_stacks_aligned: bool
    staircases_aligned: bool
    misalignment_deltas_m: tuple[tuple[str, float], ...]
    # ^ list of (feature_id, x-or-y delta in metres) for failures


@dataclass(frozen=True)
class MultiFloorPlacedCandidate:
    """Multi-floor placed candidate after VAV passes."""
    per_floor: tuple[PlacedCandidate, ...]
    alignment_report: VerticalAlignmentReport
    source_multifloor_candidate_signature: str


@dataclass(frozen=True)
class PlacementBatchResult:
    placed_candidates: tuple[PlacedCandidate, ...]
    multi_floor_placed_candidates: tuple[MultiFloorPlacedCandidate, ...]
    provenance: PlacementProvenance
    failure_records: tuple[FailureRecord, ...]
    # ^ structured per B-C11B-FAILURE-SCHEMA-V2 pattern
```

### § 2.3 — Configuration

```python
@dataclass(frozen=True)
class PlacementConfig:
    # ── algorithm selection ─────────────────────────────────
    placement_algorithm: Literal[
        "slicing_kd_tree",     # v1 default; fast, deterministic
        "csp_backtrack",       # fallback when slicing fails
    ] = "slicing_kd_tree"
    use_csp_fallback_on_slicing_failure: bool = True

    # ── single-floor placement budgets ───────────────────────
    placement_max_retries: int = 50
    per_candidate_wallclock_seconds: float = 10.0

    # ── multi-floor alignment ────────────────────────────────
    vertical_alignment_tolerance_m: float = 0.0      # Q-2 default
    multi_floor_max_realign_iterations: int = 3      # Q-3 default

    # ── enforcement ──────────────────────────────────────────
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    # ^ same shape as C11b (carried for consistency)

    repair_mode: Literal["strict", "lenient_shrink"] = "strict"
    # ^ Q-9: what if C11b's chosen dims don't fit? STRICT rejects;
    #   LENIENT_SHRINK tries to shrink dims by ≤5% before rejecting.

    # ── determinism ──────────────────────────────────────────
    master_seed: int = 0xC12_5EED
    # ^ slicing-tree has tie-break rng for room ordering when scores tie

    # ── replay ───────────────────────────────────────────────
    expected_environment_fingerprint_strict: bool = True
```

---

## § 3 — Behaviour

### Phase 0 — Input + startup validation

1. Capture `EnvironmentFingerprint` (reusing C11b's pattern; C12 adds its own version anchor `C12_VERSION: Final[str] = "v0.1"`).
2. If `expected_environment_fingerprint` is provided and doesn't match, raise `EnvironmentFingerprintMismatchError`.
3. For each single-floor input: assert `geometry_materialized is True AND placement_safe is True` per B-C12-MATERIALIZATION-CONTRACT. If `requires_transform_resolution is True` (Tier A SHALLOW input), invoke the **transform resolver** sub-step first (§ 3.0a below) to materialize the pending geometry; then re-assert flags.

### Phase 0a — Transform resolver (Tier A SHALLOW inputs)

A C11b output with `capability_mode == "PREDICATE_ONLY"` carries a refined parameter vector but no materialized geometry. The transform resolver is the bridge: it takes the predicate verdict (which mutation operator the candidate represents) plus the refined dimensions and produces a candidate with `geometry_materialized = True`.

**At v0.1, the resolver is a stub** that simply marks the candidate as materialized without doing real geometric transformation. Real per-operator resolvers are filed as `B-C12-TIER-A-RESOLVERS` (per-operator implementations for M1–M5, M9a–d). This stub is sufficient for v1 ship if all SFP inputs are Tier B or M0 (already materialized).

### Phase 1 — Single-floor placement (SFP) per candidate

For each `RefinedCandidate` in `single_floor_inputs`:

1. Resolve transforms if needed (Phase 0a).
2. Build the room-list from `refined_parameters.room_dimensions`.
3. Pull adjacency hints from `floor_room_brief` (e.g., kitchen-adjacent-to-dining).
4. Invoke `placement_algorithm` (default: slicing-tree partition; see § 3.1).
5. On algorithm success: emit `PlacedCandidate` with placed rooms + computed `shared_edges`.
6. On algorithm failure under `enforcement_mode=STRICT`: raise `GeometricInfeasibilityError`.
7. On failure under `WARN`: record a `FailureRecord` and continue.

### Phase 2 — Multi-floor refinement absorption (MFRA)

For each `MultiFloorWetZonePlannedCandidate` in `multi_floor_inputs`:

1. Decompose into per-floor sub-candidates.
2. Run Phase 1 (SFP) on each floor independently.
3. Run Phase 3 (VAV) on the resulting tuple of `PlacedCandidate`s.
4. If VAV fails AND iteration count < `multi_floor_max_realign_iterations`: feed alignment-delta back as constraint hints, retry SFP on misaligned floors with column-position constraints, re-run VAV.
5. On convergence: emit `MultiFloorPlacedCandidate`.
6. On exhaustion: raise `VerticalAlignmentError` (STRICT) or record (WARN).

### Phase 3 — Vertical alignment verification (VAV)

Given a tuple of `PlacedCandidate`s, one per floor:

1. Identify alignment-relevant features per floor:
   - Structural columns (from C7 Grid)
   - Wet-zone stack centroids (from C10 wet-zone metadata)
   - Staircase landing/run rectangles (currently from FloorRoomBrief; long-term backlog: dedicated stair planner)
2. For each feature, compute the per-floor `(x_m, y_m)` position.
3. For each adjacent floor pair `(N, N+1)`: compute deltas; flag any feature whose delta exceeds `vertical_alignment_tolerance_m`.
4. Build `VerticalAlignmentReport`. If all three alignment categories pass, emit success; else record deltas for the MFRA retry loop.

### Phase 4 — Provenance assembly

Mirrors C11b § 3 Phase 3:

- Capture env fingerprint + master_seed + algorithm used per candidate
- Per-candidate telemetry: wallclock time, retry count, algorithm path
- Structured failure records (B-C11B-FAILURE-SCHEMA-V2 form — adopted from day one in C12)

---

## § 3.1 — Slicing k-d-tree placement algorithm (v1 default)

Per Knecht & König 2010, the slicing-tree approach to residential floor plans:

1. Sort rooms by area, descending.
2. Recursively bisect the envelope along the longer dimension.
3. At each cut, place the largest remaining room aligned to the cut, with shorter-dim against the envelope wall.
4. If the room doesn't fit the bisected region, backtrack to a different cut orientation.
5. Repeat until all rooms placed or backtrack limit exhausted.

This is O(n log n) typical and O(n!) worst-case (full backtrack). For n ≤ 15 rooms (typical Indian residential) the worst case is tractable. Adjacency hints from C8 promote/demote candidate placements but don't override the area-first heuristic at v1.

**Algorithm correctness at v1**: deterministic given `master_seed` (used only for tie-break on equal-area rooms), produces a valid placement OR fails cleanly. Does NOT guarantee optimality.

---

## § 4 — Invariants (v0.1 — will grow during walks)

| # | Invariant | Mode |
|---|---|---|
| 1 | Every `PlacedRoom` is fully contained within `(0, 0)` to `(envelope_width_m, envelope_depth_m)`. | RAISE |
| 2 | No two `PlacedRoom`s on the same floor have overlapping interiors (shared edges allowed). | RAISE |
| 3 | `PlacedRoom.width_m == RefinedParameters.room_dimensions[i].width_m` for the corresponding room_id (geometry preserves refinement). Tolerance: `0.0` at v1 in `strict` mode; ≤5% deviation allowed under `lenient_shrink`. | RAISE (STRICT) |
| 4 | Capability-flag consistency at input: `geometry_materialized AND placement_safe` MUST be True (per B-C12-MATERIALIZATION-CONTRACT). | RAISE |
| 5 | For multi-floor outputs: every alignment-relevant feature aligns within `vertical_alignment_tolerance_m` across adjacent floors. | RAISE |
| 6 | `floor_index` is monotonically non-decreasing across the `per_floor` tuple in a `MultiFloorPlacedCandidate`. | RAISE |
| 7 | Deterministic output: same input + same config + same env fingerprint → byte-equal `PlacedCandidate` tuple. | RAISE (replay tier) |
| 8 | Every `PlacedCandidate.source_refined_candidate_signature` matches the input `RefinedCandidate.source_topology_candidate_signature` (one-to-one provenance trace). | RAISE |
| 9 | `placement_algorithm_used` field is populated and matches one of the literal values in `PlacementConfig.placement_algorithm`. | RAISE |
| 10 | `shared_edges` is computed deterministically from `placed_rooms` (function of geometry, not algorithm state). | RAISE |

---

## § 5 — Failure modes (v0.1 — will grow)

```
PlacementError (base)
├── PerCandidatePlacementError
│   ├── GeometricInfeasibilityError    (no valid placement; STRICT mode)
│   ├── CapabilityFlagInconsistencyError  (Inv 4 violation)
│   ├── PlacementAlgorithmTimeoutError (per-candidate budget exceeded)
│   └── TransformResolverError         (Tier A stub failure)
├── PerMultiFloorPlacementError
│   ├── VerticalAlignmentError         (VAV failed; MFRA retries exhausted)
│   └── MultiFloorDecompositionError   (per-floor input malformed)
├── BatchAllPlacementsFailedError      (WARN mode: every input failed)
├── EnvironmentFingerprintMismatchError (replay tier)
└── InvariantViolationError            (systemic)
```

---

## § 6 — Test coverage targets (v0.1)

- ~30 SFP-only tests: small-envelope placement, large-envelope placement, adjacency-hint honoring, backtrack-on-infeasible, area-sort tie-break determinism, lenient_shrink mode.
- ~20 VAV tests: column-aligned passing, column-misaligned failing, wet-stack alignment, staircase alignment, mixed-feature alignment.
- ~25 MFRA tests: 2-floor convergence after 1 retry, 2-floor exhaustion after max-retries, 3-floor cascade, repair-mode behaviour.
- ~15 orchestrator tests: STRICT/WARN escalation, env fingerprint replay, batch-all-failed, structured failure records.
- ~10 invariant tests: Inv 1-10 each with positive and negative cases.

Target ~100 tests at v1 LOCK (mirrors C11a v0.1 scope before its walks expanded coverage).

---

## § 7 — Open questions at v0.1 (resolve during Walks #2-#N)

- **Q-1 (HIGH)**: Placement algorithm choice. Slicing k-d-tree (v1 default) is fast but suboptimal. Should v1 ship with CSP-backtrack fallback enabled by default, or only as opt-in? Literature suggests CSP (Regateiro et al. 2012) handles non-rectangular envelopes better.
- **Q-2 (MEDIUM)**: Vertical alignment tolerance default. `0.0` is strict; `0.05 m` (50mm) is forgiving. Indian construction tolerances are typically ±10mm at the slab level. Reviewer-likely critique: 0.0 is unachievable in practice; 0.05 is the right v1 default.
- **Q-3 (MEDIUM)**: Multi-floor refinement loop bound. `3` retries is a starting point. Should this scale with floor count, or stay flat?
- **Q-4 (LOW)**: Determinism via `master_seed`. Slicing tree is deterministic without rng; only tie-break uses it. Is `master_seed` needed at v1 or can we defer it to a parallel-execution Q?
- **Q-5 (HIGH)**: Adjacency hints from C8. At v1 they're soft (promote/demote candidate placements). Should they ever be HARD? E.g., bathroom-must-be-adjacent-to-bedroom is a hard architectural constraint in some cultures. **Q-5 risks scope-creep into KB rules — guard against.**
- **Q-6 (MEDIUM)**: Non-rectangular envelopes (L-shaped plots, corner plots). At v0.1 we assume rectangular; real Indian residential plots are often irregular. Probably backlog for v2.
- **Q-7 (LOW)**: Handoff contract to C13. `shared_edges` should be sufficient; verify with C13 spec stub.
- **Q-8 (MEDIUM)**: Performance budget. `10s per single-floor candidate` is generous; `30s for multi-floor with retries` is conservative. Verify against Indian residential pop sizes (typical: 10-15 rooms per floor).
- **Q-9 (HIGH)**: Repair mode under input infeasibility. STRICT vs LENIENT_SHRINK. The LENIENT mode is dangerous — it silently changes C11b's refined output, breaking the C11b → C12 contract that "C11b chooses dims; C12 places them." If we offer it, must we also emit a `repair_delta` provenance field?
- **Q-10 (MEDIUM)**: Cache key. Does C12 have its own cache (extending C11b's env tuple), or does C12 piggyback C11b's cache by treating placement as deterministic given the input candidate signature?
- **Q-11 (LOW)**: Multi-floor refinement re-running C11b. Should MFRA re-invoke C11b NSGA-II per floor (the v1.1 LOCKED `B-C11B-MF` deferral path), or just run SFP-per-floor with no re-refinement? v0.1 assumes the latter (simpler); reviewer may push for the former.
- **Q-12 (LOW)**: Capability-flag handling for `M8_MULTI_FLOOR` operator class. At C11b v1.1, M8 is rejected. If C12 absorbs MF inputs that came from M8 mutations, do we re-classify them as `M0_BASE` for downstream consumers, or keep the M8 lineage in provenance?

**12 open questions at v0.1.** All resolvable through Walks #2-#N before LOCK.

---

## § 8 — Backlog at v0.1 (Rule 9 enumeration — to be expanded each walk)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C12-TIER-A-RESOLVERS** | Per-operator transform resolvers for M1–M5, M9a–d that turn predicate-only Tier A SHALLOW C11b outputs into materialized geometry. Currently § 3.0a is a stub. | C12 v0.1 § 3.0a | Before C13 ships; OR when first non-Tier-B candidate reaches C12 | M |
| **B-C12-CSP-PLACEMENT** | Full CSP-backtrack placement algorithm per Regateiro et al. 2012 block-algebra + O(n²) incremental path-consistency. Currently a fallback stub; should be production-grade for non-rectangular envelopes (Q-6). | C12 v0.1 Q-1 | When slicing-tree fails on >10% of production candidates OR when L-shaped plots enter production | M-L |
| **B-C12-IRREGULAR-ENVELOPES** | Support L-shaped, T-shaped, and corner-cut plot envelopes. v0.1 assumes rectangular. | C12 v0.1 Q-6 | When real Indian-residential plot data shows >20% non-rectangular OR when first user complaint surfaces | M |
| **B-C12-ADAPTIVE-RETRY-BUDGET** | Scale `multi_floor_max_realign_iterations` with floor count and alignment-feature count instead of constant. | C12 v0.1 Q-3 | When 3-retry budget exhausts on >5% of multi-floor inputs | S |
| **B-C12-REPAIR-PROVENANCE** | If `repair_mode=lenient_shrink` ships in v1, mandate `repair_delta` provenance field on `PlacedCandidate` recording the delta from C11b's refined dims. Otherwise downstream debugging is impossible. | C12 v0.1 Q-9 | If Q-9 resolves to LENIENT_SHRINK | S |
| **B-C12-CACHE-KEY-EXTENSION** | Formal cache key inheritance from C11b: `c12_cache_key = sha256(c11b_env_fingerprint, c12_config)`. Mirrors C11b's cache pattern. | C12 v0.1 Q-10 | When cache becomes operationally relevant (post-launch) | S |
| **B-C12-MFRA-NSGA-RE-INVOKE** | If MFRA needs per-floor re-refinement (not just SFP-per-floor), the spec must define how C11b is re-invoked: cache key handling, fingerprint propagation, recursion bound. | C12 v0.1 Q-11 | If Q-11 resolves to re-invocation | M |
| **B-C12-DAYLIGHT-AWARE-PLACEMENT** | Daylight-orientation hints: bedrooms preferentially placed on cool-facing walls (climate-zone aware per C6). At v0.1 placement is pure geometric. | New v0.1 | When climate-aware scoring (C14) shows daylight-correlated regression | M |
| **B-C12-STAIR-PLANNER** | Dedicated stair planner sub-component. v0.1 reads stair rectangles from FloorRoomBrief; future spec separates stair design (run, landings, headroom) from placement. | New v0.1 | Before multi-storey residential gains share in production | M-L |
| **B-C12-FAILURE-SCHEMA-V2-PARITY** | Ensure C12's structured `FailureRecord` schema matches the one B-C11B-FAILURE-SCHEMA-V2 will introduce, so cross-component telemetry aggregates cleanly. | New v0.1, paired with S42 critique walk #16 | Same trigger as B-C11B-FAILURE-SCHEMA-V2 | S |
| **B-C12-CONSTRAINT-PROPAGATION** | Surface adjacency-hint enforcement as a configurable HARD/SOFT toggle per hint (Q-5). | C12 v0.1 Q-5 | When Q-5 resolves; OR when KB-rule integration begins | M |

**Summary table (11 items at v0.1).**

---

## § 9 — Rule 11 spec audit on v0.1 PROPOSED

Mandatory per Rule 11 (vigorous self-analysis on every spec creation).

**Worst issues first:**

1. **§ 3.0a transform resolver is a stub.** This is the single biggest hole. If any Tier A SHALLOW C11b output reaches v1 C12, the stub will mark it materialized without doing real geometric transformation — downstream (C13, C14) will see invalid geometry attributed to a "materialized" flag. Mitigation: backlog item `B-C12-TIER-A-RESOLVERS` filed; v1 should ship with a HARD assertion that input `capability_mode == "MATERIALIZED"` (Tier B + M0 only) and fail-fast on Tier A until the resolvers are built. Documented as Q-1-alt for Walk #2.

2. **§ 3 Phase 2 (MFRA) iteration loop is hand-wavy.** "Feed alignment-delta back as constraint hints" — the actual mechanism for translating a 50mm misalignment delta into a constrained re-placement is not specified. Risk: at LOCK we discover the loop never converges in practice. Mitigation: Walk #2 must specify the constraint-injection mechanism formally.

3. **Inv 7 (deterministic output) is asserted but the proof is thin.** Slicing-tree is deterministic given input ordering; tie-break uses `master_seed`. But adjacency-hint scoring (Phase 1 step 3) may pull from `floor_room_brief` in an order-dependent way. Walk #2 must verify the hint-lookup is canonical.

4. **No interaction with B-C11B-PROVENANCE-SPLIT yet.** C11b's `LocalRefinementProvenance` is about to split into three dataclasses. C12's `PlacementProvenance` should anticipate the same shape (replay / operational / diagnostic separation) rather than carry a monolithic block forward.

5. **Capability-flag check timing.** § 3 Phase 0 step 3 asserts flags before placement. Good. But what about RefinedCandidates that successfully passed C11b's `__post_init__` W6-1 hard check yet were tampered with in-flight? At v1 we trust the singleton path; at v2 we may need a re-check at C12 ingress.

**Self-analysis: no functional bugs.** The spec is internally consistent for v0.1 PROPOSED scope. Issues #1-#5 are walk-resolvable, not LOCK-blockers.

**Web research verification:**

- Searched "architectural floor plan placement algorithm 2D rectangle packing" — confirmed Knecht & König 2010 slicing-tree approach + Regateiro et al. 2012 CSP block-algebra. Both filed.
- Floor-planning NP-hardness confirmed per Klawitter et al. 2021 (arxiv 2107.05036). v1's algorithm choice (heuristic slicing + backtrack) is the standard pragmatic compromise.

---

## § 10 — Status

**v0.1 PROPOSED.** PENDING Ramalingam LOCK adjudication.

**Open items**: 12 Q-questions in § 7 + 5 self-audit concerns in § 9.

**Walks remaining**: at least 2-3 before LOCK candidacy (analogous to C11a's path from v0.1 → v1.0 over 4 walks).

**Next session (S44+)** action item: Walk #2 review of v0.1 PROPOSED, focused on Q-1, Q-5, Q-9 (the three HIGH-priority open questions) plus self-audit issue #1 (Tier A resolver stub).

---

## § 11 — Glossary deltas (terminology adopted from C11b)

- **`EnvironmentFingerprint`**: same shape as C11b's (env tuple + version anchors). C12 adds `c12_version: str` field. Re-uses C11b's `master_seed` capture pattern.
- **`capability_mode`**: read from `RefinedCandidate` per C11b § 0.3.1. "MATERIALIZED" is required at C12 ingress.
- **WARN / STRICT enforcement**: same semantics as C11b § 0.4.

---

## § 12 — Backlog visibility inside spec (Rule 9 summary table)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-C12-TIER-A-RESOLVERS | Per-operator transform resolvers (M1–M5, M9a–d) | C12 v0.1 § 3.0a | Before C13 ships OR first Tier A input | M |
| B-C12-CSP-PLACEMENT | CSP-backtrack production grade | C12 v0.1 Q-1 | >10% slicing failures OR L-plots enter prod | M-L |
| B-C12-IRREGULAR-ENVELOPES | L-shaped / T-shaped / corner-cut plots | C12 v0.1 Q-6 | >20% non-rect plot data OR user complaint | M |
| B-C12-ADAPTIVE-RETRY-BUDGET | Scale retry count with floor/feature count | C12 v0.1 Q-3 | >5% 3-retry exhaustion | S |
| B-C12-REPAIR-PROVENANCE | repair_delta field if lenient_shrink ships | C12 v0.1 Q-9 | Q-9 → LENIENT_SHRINK | S |
| B-C12-CACHE-KEY-EXTENSION | Formal cache key inheriting C11b env | C12 v0.1 Q-10 | Cache becomes operationally relevant | S |
| B-C12-MFRA-NSGA-RE-INVOKE | Define re-invocation of C11b for MFRA | C12 v0.1 Q-11 | Q-11 → re-invocation | M |
| B-C12-DAYLIGHT-AWARE-PLACEMENT | Climate-zone-aware bedroom orientation | New v0.1 | Daylight regression in C14 | M |
| B-C12-STAIR-PLANNER | Dedicated stair sub-component | New v0.1 | Multi-storey gains prod share | M-L |
| B-C12-FAILURE-SCHEMA-V2-PARITY | Match B-C11B-FAILURE-SCHEMA-V2 shape | New v0.1 | Same trigger as parent | S |
| B-C12-CONSTRAINT-PROPAGATION | HARD/SOFT toggle per adjacency hint | C12 v0.1 Q-5 | Q-5 resolves OR KB-rules begin | M |

**11 items at v0.1.** Expect 3-5 more per walk.

---

## § 13 — Complexity Budget (v0.1 baseline)

| Subsystem | Count |
|---|---|
| Public types | 6 (PlacedRoom, SharedEdge, PlacedCandidate, VerticalAlignmentReport, MultiFloorPlacedCandidate, PlacementBatchResult) |
| Failure types | 9 |
| Configuration fields | 10 |
| Invariants | 10 |
| Sub-phases | 5 (Phase 0, 0a, 1, 2, 3, plus provenance assembly) |
| Open questions | 12 |
| Backlog items | 11 |

**Weighted complexity (per B-C11B-COMPLEXITY-BUDGET-V2 metric)**:
- Invariants × 1 = 10
- Failure types × 2 = 18 (treat as cache-relevant for now)
- Replay × 3 = 3 (env fingerprint)
- Telemetry × 0.5 = 5

**Total weighted: 36**. Comfortable for v0.1. C11b at v1.1 LOCKED weighed ~75-80; we have headroom.

---

## § 14 — Freeze candidacy rationale

**v0.1 is NOT a freeze candidate.** Filed for completeness; explicit non-candidacy:

- 12 open questions; HIGH-priority ones (Q-1, Q-5, Q-9) all have material design impact.
- Transform resolver stub (§ 3.0a) is a known correctness hole for Tier A inputs.
- MFRA constraint-injection mechanism (§ 3 Phase 2) is hand-wavy.

**Earliest LOCK candidacy**: v0.4 or v0.5, depending on critique-walk velocity. Mirrors C11a (4 walks v0.1 → v1.0) and C11b (3 walks v0.4 → v1.1).

---

**End of C12 SPEC v0.1 PROPOSED.**

**Status reminder**: PENDING Ramalingam LOCK adjudication per Rule 8. No code before LOCK.
