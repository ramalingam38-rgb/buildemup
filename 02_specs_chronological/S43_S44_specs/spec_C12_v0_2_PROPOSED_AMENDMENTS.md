# C12 — SPEC v0.2 PROPOSED — Walk #2 PATCH-NOW Amendments

**Component**: 12 (Multi-Floor Placement & Vertical Alignment Engine)

**Status**: v0.2 PROPOSED. **NOT LOCKED.** PENDING Ramalingam adjudication.

**Authority**: S43 Walk #2 author's draft incorporating external critique (20-item reviewer analysis) + corroborating own § 9 self-audit from v0.1.

**Scope**: PATCH-NOW amendment set against v0.1 PROPOSED. v0.2 does NOT rewrite v0.1; it applies focused amendments + adds backlog items + resolves several open questions. Full v0.2 spec = v0.1 + this amendment doc.

**Authored**: S43, post-external-critique walk.

---

## § 0.1 — Walk #2 verdict summary

| Item | Verdict | Section touched |
|------|---------|----------------|
| 1 (Tier A stub) | VALID-CRITICAL | § 3 Phase 0 + Inv 4 |
| 2 (MFRA under-spec) | VALID-HIGH | § 3 Phase 2 |
| 3 (slicing-tree bias) | PARTIAL — DOCUMENTED | § 3.1 |
| 4 (geometric ≠ architectural) | MISFRAMED | § 0 (clarification) |
| 5 (LENIENT_SHRINK) | VALID-HIGH | § 2.3 + Q-9 resolution |
| 6 (determinism fragile) | VALID-HIGH | New § 3.5 + Inv 7 |
| 7 (rectangular envelope) | DOCUMENTED | B-C12-IRREGULAR-ENVELOPES (no change) |
| 8 (adjacency too weak) | VALID | § 2.2 + Q-5 partial resolution |
| 9 (no circulation model) | VALID-CRITICAL | § 3 Phase 1 + new Inv 11 |
| 10 (VA over-simplified) | PARTIAL | § 3 Phase 3 + new backlog |
| 11 (backtrack complexity) | DOCUMENTED + new backlog | § 3.1 + B-C12-PLACEMENT-PRUNING |
| 12 (no post-placement opt) | MISFRAMED | § 0 (clarification) |
| 13 (shared edge fragility) | VALID | § 2.2 + new § 3.6 |
| 14 (zero-tolerance default) | VALID | § 2.3 + Q-2 resolution |
| 15 (no doorway feasibility) | VALID | § 2.2 + new Inv 12 |
| 16 (failure schema growth) | MISFRAMED — covered | (no change) |
| 17 (MF independence) | VALID-HIGH | § 3 Phase 2 + new backlog |
| 18 (empty-space metric) | MISFRAMED | § 0 (clarification) |
| 19 (env fingerprint) | DOCUMENTED | (no change) |
| 20 (C12 god-system) | VALID-but-YOURS | New backlog B-C12-COMPONENT-SPLIT-V2 |

**Distribution**: 9 v0.2 amendments / 5 new backlog / 5 MISFRAMED-pushback / 4 DOCUMENTED-already-filed.

---

## § 0.2 — MISFRAMED-scope pushback (explicit; not amendments)

Four reviewer items ask C12 to absorb work that belongs to other components. Spec § 0 (v0.1) already excludes these; v0.2 reinforces the boundaries:

- **Item 4 examples** (inaccessible rooms, windowless bedrooms, trapped kitchens) → C14 scoring layer. C12 emits geometry; C14 judges livability. Doorway feasibility (#15) is the genuine C12-overlap; the rest is downstream.
- **Item 12** (post-placement optimization / nudging) → asks C12 to re-do C11b's NSGA-II optimization. C11b is where multi-objective trade-offs are made. C12 realizes the chosen vector; it doesn't re-search.
- **Item 16** (define failure taxonomy globally) → already covered by B-C12-FAILURE-SCHEMA-V2-PARITY paired with B-C11B-FAILURE-SCHEMA-V2 (S42 critique walk addition). Cross-component schema convergence happens at that pair's resolution.
- **Item 18** (empty-space / residual-space quality) → C14 scoring metric. A geometrically-valid placement with thin residual strips is a quality concern, not a validity concern.

Half-MISFRAMED on Items 3 and 10:

- **Item 3 (architectural diversity)**: NSGA-II in C11b is the diversity-generating mechanism (parameter-space exploration with crowding distance). C12 places what C11b chose. The slicing-tree's structural bias is real but applies to *layout style for a given parameter vector*, not to *output set diversity across vectors*. v0.2 documents the bias explicitly in § 3.1.
- **Item 10 (structural alignment)**: feature-volume alignment is a real upgrade path (filed as B-C12-VOLUMETRIC-ALIGNMENT below). Beam conflicts / shaft continuity / load paths require structural engineering that is post-v1 scope.

---

## § 0.3 — PATCH-NOW amendments (the v0.2 deltas to v0.1)

### Amendment v0.2-A1 — Tier A HARD-fail-fast at ingress (Item 1)

**Replaces**: § 3 Phase 0 step 3 (capability flag assertion) + § 3.0a (resolver stub).

**New text**:

```
Phase 0 step 3: For each single-floor input, assert:
  - geometry_materialized is True
  - placement_safe is True
  - capability_mode == "MATERIALIZED"

Tier A SHALLOW inputs (capability_mode == "PREDICATE_ONLY") are
REJECTED at ingress with a per-candidate
CapabilityFlagInconsistencyError (under STRICT) or recorded
failure (under WARN).

Phase 0a (Transform resolver) is REMOVED from v1 entirely. Re-added
post-v1 when B-C12-TIER-A-RESOLVERS ships per-operator resolvers.

Rationale: a stub resolver that marks geometry materialized without
actually materializing it is an integrity breach. The reviewer
correctly identified this as LOCK-blocking. v1 ships strict-MATERIALIZED-only;
Tier A inputs require either upstream resolution by a future C11b
extension or the dedicated resolver layer in B-C12-TIER-A-RESOLVERS.
```

**Affected invariants**: Inv 4 strengthens to RAISE always (no LENIENT
escape hatch).

**Affected failure modes**: TransformResolverError REMOVED from the
v1 hierarchy (no resolver to fail).

---

### Amendment v0.2-A2 — MFRA constraint-injection formalization (Item 2)

**Replaces**: § 3 Phase 2 step 4 (the "feed alignment delta back as constraint hints" hand-wave).

**New text**:

```
Phase 2 step 4 — MFRA retry mechanism, formal definition:

Let R_n = set of features misaligned at iteration n (per VAV output).
Let δ_n = max(absolute deltas across features in R_n).

For each misaligned feature f ∈ R_n with delta (dx, dy):
  - Identify the floor F whose feature position deviates most from
    the consensus position across all floors.
  - Inject a HARD position constraint into F's SFP retry:
    f.target_position = mean(positions of f across non-deviant floors)
    with ε-tolerance = (alignment_tolerance / 2).
  - Re-run SFP on F with the constraint added.

Convergence criterion (monotonic-delta):
  - If δ_{n+1} < δ_n × 0.5: continue iteration (good progress).
  - If δ_n × 0.5 ≤ δ_{n+1} < δ_n: continue iteration (slow progress).
  - If δ_{n+1} >= δ_n: ABORT with VerticalAlignmentError (divergence
    or plateau; further retries would be wasted).

Bound: max iterations = config.multi_floor_max_realign_iterations
(default 3 per v0.1). Combined with monotonic-delta abort, worst-case
work is bounded above by (3 × SFP cost + 3 × VAV cost).

Records: every retry's δ_n is captured in
MultiFloorPlacedCandidate.alignment_report.delta_progression: tuple[float, ...]
for post-hoc convergence debugging.
```

**Affected schema**: `VerticalAlignmentReport` gains a `delta_progression: tuple[float, ...]` field.

**Affected invariants**: new Inv 13 — `len(alignment_report.delta_progression) ≤ multi_floor_max_realign_iterations + 1`.

---

### Amendment v0.2-A3 — STRICT-only at v1 (Item 5)

**Replaces**: § 2.3 `PlacementConfig.repair_mode` field.

**New text**:

```python
# REMOVED at v1:
# repair_mode: Literal["strict", "lenient_shrink"] = "strict"

# v0.2 ships STRICT-only. Lenient repair → B-C12-LENIENT-REPAIR-V2.
# Rationale (per Walk #2 Item 5): silently changing C11b-refined
# dimensions inside C12 breaks the C11b→C12 contract that "C11b
# chooses dims; C12 places them." If lenient mode is ever needed,
# it requires (a) explicit repair_delta provenance field, (b) v1.X
# version bump on c12_version, (c) downstream consumer notification
# protocol — all out of scope for v1 LOCK.
```

**Open question Q-9** resolved: STRICT-only at v1.

---

### Amendment v0.2-A4 — Canonicalization rules for determinism (Item 6)

**Adds**: new § 3.5 (determinism contract).

**New text**:

```
§ 3.5 — Determinism contract

Inv 7 requires byte-equal placement output given same input + config +
env fingerprint. To uphold this against reviewer-identified ordering
fragility, the following canonicalization rules apply:

1. Room iteration order: ALWAYS sort by lex-ASC room_id before any
   placement iteration. Even if input arrives unsorted (defensive).
2. Adjacency hint iteration: sort by lex-ASC (room_a_id, room_b_id)
   tuple before hint application.
3. Floating-point comparisons: ALL geometric comparisons use
   CANONICAL_FP_PRECISION (= 6 decimal places, inherited from
   utilities/canonical.py — same value C11b uses).
4. Coordinate snapping: room positions are snapped to the C7-Grid
   resolution (typically 50mm) before emission.
5. No unordered collections at any pipeline boundary: dicts at
   pipeline edges are converted to tuple[tuple[K, V], ...] sorted by K.
6. Backtrack search order: when slicing-tree backtracks, alternative
   cuts are tried in fixed (vertical-then-horizontal) order.
7. PRNG: only used for tie-break on equal-score placements; seeded
   from config.master_seed; replay-tested per Inv 7.

Replay regression suite: ≥10 byte-equal replay tests across
permuted-input scenarios. Filed under test coverage targets § 6.
```

**Affected invariants**: Inv 7 wording strengthens to enumerate the
six canonicalization rules.

---

### Amendment v0.2-A5 — HARD/SOFT adjacency typing (Item 8)

**Replaces**: § 2.2 implicit "soft only" adjacency hint handling.

**New text** (in § 2.2 schema):

```python
class AdjacencyConstraintKind(str, enum.Enum):
    HARD = "hard"  # violation → reject placement
    SOFT = "soft"  # violation → score penalty in C14, not C12

@dataclass(frozen=True)
class AdjacencyHint:
    room_a_id: str
    room_b_id: str
    kind: AdjacencyConstraintKind
    weight: float = 1.0  # for SOFT only; ignored when HARD

# Adjacency hints are now consumed from FloorRoomBrief.adjacency_hints
# (an upstream contract the C9 spec must add — filed as
# B-C9-ADJACENCY-HINTS for cross-component dependency tracking).
```

**Rationale**: reviewer's 4-level enum (HARD/SOFT/PREFERRED/AVOID) is
over-engineered for v1. HARD = "must" and SOFT = "should" cover the
two genuine architectural concerns: critical functional adjacencies
(kitchen↔dining, staircase continuity) get HARD; optional
preferences (study↔library) get SOFT.

**Open question Q-5** partially resolved: typing scheme adopted;
which specific adjacencies get HARD vs SOFT is a Walk #3 question
(domain-specific catalog).

---

### Amendment v0.2-A6 — Circulation reservation contract (Item 9)

**Adds**: new § 3 Phase 0b (corridor zone reservation) + new Inv 11.

**New text**:

```
§ 3 Phase 0b — Corridor zone reservation

The FloorRoomBrief input contains a corridor_zones field (output of
C8 Corridor Design). Each corridor zone is a rectangle in envelope
coordinates representing a reserved circulation path.

Before Phase 1 SFP begins, C12:
1. Marks each corridor zone rectangle as occupied (cannot be
   placed-into).
2. Runs a reachability BFS over the planned room positions + corridor
   zones to verify that every room is reachable from at least one
   building entry point.
3. If reachability fails: emit CirculationInfeasibilityError under
   STRICT, or record under WARN.

Cross-component contract: C8 spec MUST expose corridor_zones in
FloorRoomBrief output. Filed as B-C8-CORRIDOR-ZONE-CONTRACT (an
upstream amendment that needs C8 cooperation).

Inv 11 (NEW): every PlacedRoom in a PlacedCandidate is reachable
via the corridor_zones graph from the FloorRoomBrief.entry_points
set. RAISE if violated.

Failure mode (NEW):
  - CirculationInfeasibilityError (PerCandidatePlacementError subtype)
```

**Affected failure hierarchy**:

```
PerCandidatePlacementError
├── GeometricInfeasibilityError
├── CapabilityFlagInconsistencyError
├── PlacementAlgorithmTimeoutError
└── CirculationInfeasibilityError (NEW v0.2)
```

---

### Amendment v0.2-A7 — Epsilon-aware shared_edges + grid snapping (Item 13)

**Replaces**: § 2.2 SharedEdge field definitions; adds § 3.6.

**New text**:

```python
# In § 2.2 schema:
@dataclass(frozen=True)
class SharedEdge:
    room_a_id: str
    room_b_id: str
    axis: Literal["vertical", "horizontal"]
    overlap_start_m: float    # snapped to C7-Grid resolution
    overlap_end_m: float      # snapped to C7-Grid resolution
    overlap_length_m: float

    # NEW v0.2: doorway feasibility (Item 15 amendment below)
    min_required_clear_width_m: float
    doorway_feasible: bool

§ 3.6 — Shared edge derivation (NEW v0.2)

shared_edges are computed deterministically from placed_rooms as
follows:

1. For each pair (R_a, R_b) of placed rooms in canonical order:
   a. Compute the geometric overlap on each axis using ε-tolerance
      (ε = 0.001 m = 1mm).
   b. If overlap length > ε on exactly one axis: shared edge candidate.
   c. Snap overlap_start_m and overlap_end_m to C7-Grid resolution
      (typically 0.05 m = 50mm) by rounding.
   d. Reject if snapped overlap length < min(NBC 2016 door minima)
      = 0.75 m (no possible doorway → not architecturally usable).

This eliminates the floating-point fragility the reviewer identified:
sliver overlaps and near-miss adjacencies are deterministically
filtered out before SharedEdge construction.
```

---

### Amendment v0.2-A8 — Realistic alignment tolerance default (Item 14)

**Replaces**: § 2.3 `vertical_alignment_tolerance_m` default.

**New text**:

```python
# v0.1:
# vertical_alignment_tolerance_m: float = 0.0

# v0.2:
vertical_alignment_tolerance_m: float = 0.02  # 20mm
# Rationale: IS 456 (concrete) slab pour tolerance is ±10mm. Geometric
# placement tolerance must accommodate construction reality plus
# floating-point/snapping headroom. 20mm = 2× construction tolerance,
# a conservative production default. Strict-zero (v0.1) was unrealistic
# per reviewer Item 14.
```

**Open question Q-2** resolved: 20mm default. Configurable per batch.

---

### Amendment v0.2-A9 — Doorway feasibility per NBC 2016 (Item 15)

**Adds**: § 2.2 SharedEdge fields + new Inv 12.

**New text** (already partly in A7 above; consolidated here):

```python
# In SharedEdge (per A7):
min_required_clear_width_m: float
doorway_feasible: bool

# Derivation rule (in § 3.6 step 1d expansion):
#
# Per NBC 2016 Part 3 (verified via web search, S43 Walk #2):
#   - Main entrance:       1.00 m minimum
#   - Bedroom door:        0.90 m minimum
#   - Bathroom door:       0.75 m minimum
#   - General/other:       0.75 m minimum
#
# min_required_clear_width_m is derived from the room categories of
# the two rooms sharing the edge:
#   - If either room is "main entrance" or any room category implying
#     entry: 1.00 m.
#   - Else if either room is "bedroom": 0.90 m.
#   - Else if either room is "bathroom" / "wc" / "toilet": 0.75 m.
#   - Else: 0.75 m (general fallback).
#
# doorway_feasible = (overlap_length_m >= min_required_clear_width_m).

Inv 12 (NEW): every PlacedCandidate has at least one
doorway_feasible == True SharedEdge per pair of rooms that
floor_room_brief.adjacency_hints declares as HARD-adjacent.
RAISE under STRICT.
```

---

### Amendment v0.2-A10 — Vertical core reservation pre-step (Item 17)

**Adds**: § 3 Phase 1b (vertical core reservation for MF inputs).

**New text**:

```
§ 3 Phase 1b — Vertical core reservation (MF inputs only)

For multi-floor inputs, BEFORE per-floor SFP runs, C12 identifies
the alignment-relevant "vertical cores":

1. Staircase rectangle (from FloorRoomBrief.stair_zone).
2. Wet-zone column centroid(s) (from MultiFloorWetZonePlannedCandidate
   metadata).
3. Structural column grid (from C7 Grid; columns aligned across
   floors by definition).

Each vertical core is reserved at the SAME (x, y) position on every
floor before any per-floor SFP runs. This prevents the iteration
oscillation pattern the reviewer correctly identified: per-floor SFP
placing a staircase at different (x, y) on each floor, then VAV
failing, then retry trying to "pull" the misaligned floor — wasted
work that could have been prevented by reservation.

Full coupled-multi-floor placement (joint optimization across all
floors simultaneously) remains B-C12-COUPLED-MF-PLACEMENT backlog.
The reservation pre-step is a v1-tractable middle ground.

Affected Phase 2 step 2: per-floor SFP now runs against the
reserved-cores constraint.
```

---

## § 0.4 — New backlog items (5; Rule 9.2 immediate filing)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C12-PLACEMENT-PRUNING** | Branch-and-bound + dead-space prediction + memoized partial placements for slicing-tree backtrack search. v1 ships textbook backtrack at O(n!) worst-case (tractable for n≤15). Pruning becomes necessary at higher room counts. | Walk #2 Item 11 | When placement wallclock exceeds budget on >5% of production candidates OR when room_count > 20 enters production | M |
| **B-C12-LENIENT-REPAIR-V2** | LENIENT_SHRINK repair mode (silently shrink C11b-refined dims by ≤5% if STRICT placement fails). Requires `repair_delta` provenance field, c12_version MINOR bump, and downstream consumer notification protocol. NOT a v1 ship per Walk #2 Item 5 verdict. | Walk #2 Item 5 | When STRICT-only rejection rate exceeds 30% in production OR when user feedback signals over-rejection | S-M |
| **B-C12-COUPLED-MF-PLACEMENT** | Joint multi-floor placement: optimize all floors simultaneously with shared vertical constraint graph instead of per-floor SFP + VAV retry loop. v1 ships the reservation-based middle ground (amendment A10); full coupled placement is the long-form fix. | Walk #2 Item 17 | When MFRA retry exhaustion exceeds 10% of multi-floor inputs OR when 3+ floor production share rises | M-L |
| **B-C12-VOLUMETRIC-ALIGNMENT** | Feature-volume alignment (vs v1 point-based). Staircases get 3D trajectory checks (run + landing + headroom); wet-stacks get volumetric tolerance; structural columns get grid-occupancy checks per C7. | Walk #2 Item 10 | When multi-storey construction begins OR when first staircase-geometry production complaint surfaces | M |
| **B-C12-COMPONENT-SPLIT-V2** | Split C12-Wide into C12a (SFP) / C12b (VAV) / C12c (MFRA orchestration) when complexity warrants. Mirrors B-C11B-PROVENANCE-SPLIT pattern. Ramalingam explicitly chose C12-Wide at S42 close; this item only fires if the wide form becomes untenable. | Walk #2 Item 20 | When § 13 weighted complexity score > 100 OR when contributor onboarding signals C12 is too large to grasp | M-L |

Plus 1 cross-component upstream amendment dependency:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C8-CORRIDOR-ZONE-CONTRACT** (ROUTED TO C8) | C8 Corridor Design must expose `corridor_zones: tuple[Rectangle, ...]` on its output for C12 reservation consumption. Currently C8 emits corridor geometry implicitly; v0.2 makes the consumption contract explicit. | C12 v0.2 Amendment A6 | Before C12 v1 LOCK | S |

Plus another:

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C9-ADJACENCY-HINTS** (ROUTED TO C9) | C9 Room Sizer / FloorRoomBrief must expose `adjacency_hints: tuple[AdjacencyHint, ...]` with HARD/SOFT typing. Currently adjacency is implicit; v0.2 makes the consumption contract explicit. | C12 v0.2 Amendment A5 | Before C12 v1 LOCK | S |

**Total new items: 7 (5 C12-local + 2 ROUTED to C8/C9).**

---

## § 0.5 — Open question status after v0.2

| Q | Status | Resolution |
|---|--------|-----------|
| Q-1 (placement algo) | OPEN | Walk #3: decide whether CSP-backtrack is opt-in or default fallback. Slicing-tree stays v1 default. |
| Q-2 (alignment tolerance) | **RESOLVED** | 0.02 m (20mm) per A8 |
| Q-3 (MFRA retry bound) | OPEN | Walk #3: scale with floor count or stay constant 3? |
| Q-4 (PRNG determinism) | **RESOLVED via A4** | master_seed used only for tie-break; canonicalization rules cover the rest |
| Q-5 (adjacency HARD/SOFT) | **PARTIAL — typing resolved via A5** | Walk #3: domain-specific catalog of which adjacencies get HARD |
| Q-6 (non-rectangular envelopes) | OPEN | Backlog only (B-C12-IRREGULAR-ENVELOPES) |
| Q-7 (handoff to C13) | OPEN | Walk #3: verify SharedEdge surface against C13 stub |
| Q-8 (performance budget) | OPEN | Walk #3: empirical validation against typical brief sizes |
| Q-9 (repair mode) | **RESOLVED** | STRICT-only at v1 per A3 |
| Q-10 (cache key) | OPEN | Walk #3: own cache vs C11b-inherited |
| Q-11 (MFRA NSGA re-invoke) | **RESOLVED via A10** | No re-invocation at v1; reservation-based middle ground |
| Q-12 (M8 capability re-classify) | OPEN | Walk #3: low priority |

**Resolved at v0.2: 4 of 12** (Q-2, Q-4, Q-9, Q-11). **Partial: 1** (Q-5). **Remaining: 7.**

---

## § 0.6 — Self-audit on v0.2 (Rule 11)

Worst issues first:

1. **Cross-component dependencies introduced (B-C8-CORRIDOR-ZONE-CONTRACT, B-C9-ADJACENCY-HINTS)**. These are real architectural-coupling additions. v0.2 LOCK candidacy depends on those amendments landing in C8 and C9 — neither is in our hands. Mitigation: file both as routed backlog items; verify with you whether to gate v1 LOCK on those OR ship C12 v1 with conservative defaults (empty corridor_zones, empty adjacency_hints) and let later C8/C9 amendments enable them.

2. **Circulation reachability BFS (A6 Phase 0b step 2)** depends on an "entry points" notion that isn't yet specified upstream. Walk #3 must clarify whether entry_points comes from C8, C9, or PlotAnalysis.

3. **Doorway feasibility (A9 Inv 12)** uses an `is_main_entrance` predicate on room category that doesn't yet have a stable enum value across C1-C10. Walk #3 must canonicalize.

4. **Determinism canonicalization (A4)** introduces a CANONICAL_FP_PRECISION dependency on utilities/canonical.py. C11b spec § 0.7.1 W6-3 already flagged that constant as a shared-state risk. Same concern applies here; mitigation is the same TIEBREAK_FINGERPRINT_SCHEMA_VERSION pattern — but C12 doesn't need its own version constant yet at v0.2 (no fingerprinting layer in C12). Surface for Walk #3 as a "do we need C12_PLACEMENT_SCHEMA_VERSION" question.

5. **Component-split deferral (B-C12-COMPONENT-SPLIT-V2)** keeps C12-Wide intact per your S42 directive. v0.2 weighted complexity grew (~36 → ~52 after amendments) but still well under the 100 trigger. No immediate action.

No functional bugs in the amendment set. All 5 self-audit concerns are walk-resolvable, not LOCK-blockers.

---

## § 0.7 — Status

**v0.2 PROPOSED.** PENDING Ramalingam LOCK adjudication per Rule 8.

**Distance from v1 LOCK candidacy**: 1-2 more walks. v0.2 substantially closed the LOCK-blocking gaps (Items 1, 2, 9 all addressed). Walk #3 should focus on Q-1 (CSP fallback), Q-5 (adjacency catalog), Q-7 (C13 handoff verification), plus the 5 self-audit cross-component-dependency questions.

**Test coverage targets** unchanged at ~100 tests at v1 LOCK; v0.2 adds ~10 tests covering circulation BFS, doorway feasibility, monotonic-delta convergence, and Tier-A-rejection-at-ingress.

**Weighted complexity** (per B-C11B-COMPLEXITY-BUDGET-V2 metric):
- Invariants: 13 × 1 = 13
- Failure types: 10 × 2 = 20
- Replay: 1 × 3 = 3 (env fingerprint, no own version constant yet)
- Telemetry: 5 × 0.5 = 2.5

**Total: 38.5.** Up from v0.1's 36; well under the 100 split-trigger.

---

**End of C12 SPEC v0.2 PROPOSED — Walk #2 amendment doc.**

**Status reminder**: PENDING Ramalingam LOCK adjudication. No code anywhere; v1 LOCK still 1-2 walks away.
