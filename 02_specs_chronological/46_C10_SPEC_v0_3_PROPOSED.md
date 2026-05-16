# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v0.3 PROPOSED

**Component**: 10 (canonical Track 3 numbering)
**Status**: v0.3 PROPOSED. **NOT LOCKED.** Supersedes v0.2 PROPOSED.
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 Walk #2 outcome.
**Predecessors consumed**: C9 (Room Sizer) — `RoomSizedCandidate` (which embeds `corridor_designed_candidate.oriented_candidate` — the C5→C6→C8→C9 chain is preserved end-to-end); C7 (Grid) — `Grid` with `wall_segments` per C7 amendment v0.2; C4 — `PlotAnalysis`.
**Successors fed**: C11 (placement), C12 (vertical alignment), C14 (evaluation hard + soft).
**LOCK BLOCKED on**: C7 amendment v0.2 (B-212).

---

## § 0 — Why this exists (unchanged from v0.2)

Indian residential plumbing is the single largest hidden cost of a bad layout. C10 sits between C9 (sizes) and C11 (places) and answers: which wall does each wet room attach to, which other wet rooms group with it, how many vertical risers does that imply, and is the resulting plumbing geometry feasible per IPC/UPC trap-arm constraints? C10 emits *constraints, groupings, and engineering primitives*. C11 honours them during placement. C14 scores them during evaluation. C10 itself does not score.

---

## § 1 — Walk-resolved scope (Q1-Q5 from v0.1, Q6 from v0.2)

| Q | Resolution |
|---|---|
| Q1 single-floor scope | Yes. Multi-floor stack alignment is C12. |
| Q2 wet-rooms include kitchen + utility | Yes. Kitchen tracked separately via `kitchen_riser_group_id`. |
| Q3 hard verdict + grouping primitives, NO scores | Yes. C14 single source of truth for scores. |
| Q4 one plan per candidate | Yes. C11a's wet-wall-rotation operator handles alternatives. |
| Q5 Pattern A fail-fast | Yes. No internal recovery loop. |
| Q6 master-bathroom expected wall | RESOLVED v0.3: emit `acceptable_wall_set: tuple[str, ...]` per room (Walk #2 reviewer #2). NOT a single "predicted side". |

---

## § 2 — Contract (REVISED v0.3)

```python
def plan_wet_zones(
    room_sized_candidates: tuple[RoomSizedCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    *,
    config: WetZonePlanConfig | None = None,
) -> tuple[WetZonePlannedCandidate, ...]:
    """C10 entry point. Per-candidate semantics mirror C9 § 14.40."""
```

**v0.3 change vs v0.2**: dropped the `oriented_candidates` parallel tuple. Verified by grep: the linkage chain is already complete — `RoomSizedCandidate.corridor_designed_candidate.oriented_candidate` traverses C9→C8→C6 directly. C10 walks the chain instead of taking parallel inputs. **(B-218 RESOLVED-AS-MISFRAMED at Walk #2 audit; no upstream amendment needed.)**

`WetZonePlannedCandidate` = `RoomSizedCandidate` + `wet_zone_plan: WetZonePlan` + `provenance: WetZonePlanProvenance`.

### `WetZonePlan` schema (v0.3 — primitives sharpened per Walk #2 reviewer #10, #11)

```python
@dataclass(frozen=True)
class RiserAnchor:
    """Geometric position of one riser on its wall. NEW v0.3 per reviewer #11."""
    wall_id: str                                    # which wall
    anchor_position_m: float                        # distance from wall.start along the wall
    riser_anchor_xy: tuple[float, float]            # absolute (x, y) on the envelope
    column_id: str | None                           # nearest C7 column grid_label, if within snap distance
    snap_distance_m: float | None                   # distance from anchor to that column (None if no nearby column)


@dataclass(frozen=True)
class RiserGroup:
    group_id: str
    anchor: RiserAnchor                             # NEW v0.3 — replaces wall_id+column_alignment
    wet_room_ids: tuple[str, ...]
    # invariant: all member rooms' wet_wall_assignment[room_id] == anchor.wall_id


@dataclass(frozen=True)
class WetZonePlan:
    wet_wall_assignment: dict[str, str]             # room_id -> wall_id
    riser_groups: tuple[RiserGroup, ...]
    kitchen_riser_group_id: str | None
    wall_segments_used: tuple[str, ...]
    # Geometric primitives (C14 consumes these to compute scores):
    total_wet_run_length_m: float
    bend_count: int                                 # 90° elbows in horizontal runs (descriptive, not constrained)
    trap_arm_distances: dict[str, float]            # room_id -> distance from fixture to riser
    fixture_types_per_room: dict[str, str]          # room_id -> fixture_type key into kb/plumbing_minimums.json
    riser_count: int
    non_wet_room_buffer_zones: tuple[str, ...]
    # Acceptable-wall sets (per reviewer #2 — replaces "expected wall side"):
    acceptable_wall_sets: dict[str, tuple[str, ...]]   # room_id -> tuple of wall_ids that satisfy adjacency invariants
```

### `WetZonePlanConfig` (v0.3)

```python
@dataclass(frozen=True)
class WetZonePlanConfig:
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    pooja_adjacency_mode: Literal["strict", "soft"] = "strict"
    max_risers: int | None = None
    adjacency_threshold_m: float = 0.0
    require_master_bath_adjacency: bool = True
    require_verified_plumbing: bool = False        # NEW v0.3 — mirrors C9 require_verified_nbc

    # NEW v0.3 — Vastu/orientation scoring (reviewer #6 + my F2)
    scoring_weights: WetZoneScoringWeights = ...   # see below

    # NEW v0.3 — backtracking complexity bound (reviewer #14 + my F7)
    max_backtrack_states: int = 100


@dataclass(frozen=True)
class WetZoneScoringWeights:
    """Numeric weights for Vastu/orientation wall-preference scoring.
    NEW v0.3 per reviewer #6.

    Defaults derived from web sources (multiple Vastu references) — flagged
    secondary_consensus until B-150-equivalent verification.
    """
    bathroom_axis_preferred: float = 1.0           # south, southeast, west — bathroom-friendly
    bathroom_axis_neutral: float = 0.5             # east — acceptable
    bathroom_axis_discouraged: float = 0.0         # north, northeast — strongly avoid (Pooja zone)
    pooja_axis_preferred: float = 1.0              # northeast, north, east
    pooja_axis_neutral: float = 0.5
    pooja_axis_discouraged: float = 0.0            # south, southwest
    column_alignment_bonus: float = 0.2            # bonus for risers anchored at a structural column
    shared_wall_adjacency_bonus: float = 0.3       # bonus when adjacency is via shared wall (vs distance threshold)
```

### `WetZonePlanProvenance` (v0.3 sketch)

```python
@dataclass(frozen=True)
class WetZonePlanProvenance:
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    plumbing_kb_version: str
    enforcement_mode: str
    pooja_adjacency_mode: str
    cluster_decisions: tuple[str, ...]              # rule_trace for each clustering decision
    wall_scoring_breakdown: dict[str, float]        # wall_id -> total score
    unverified_plumbing_rows_used: tuple[str, ...]  # room_ids whose fixture_type used SECONDARY_UNVERIFIED row
    search_truncated: bool                          # NEW v0.3 — True if max_backtrack_states hit
    states_explored: int                            # NEW v0.3 — actual count
    rule_trace: tuple[str, ...]
```

---

## § 3 — Behaviour (REVISED v0.3 — full deterministic spec)

### Phase 1 — Wet-wall candidate identification

For each `WallSegment` in `Grid.wall_segments`:
1. **Eligibility**:
   - `length_m >= 1.5` (v1 floor; refine via B-215)
   - `WallTag.EXTERNAL` in `tags` (v1; SERVICE_CORE pending B-217 update)
2. **Score per wet category** (BATHROOM, KITCHEN, UTILITY) using `config.scoring_weights`:
   - Map wall axis (NORTH/SOUTH/EAST/WEST) × oriented_candidate.facing → axis_class (PREFERRED / NEUTRAL / DISCOURAGED)
   - `score = scoring_weights.{cat}_axis_{class}` plus column_alignment_bonus if grid columns lie on the wall
3. Output: `wall_scores: dict[wall_id, dict[category, float]]`

### Phase 2 — Wet-room clustering (FULL DETERMINISTIC SPEC v0.3)

Build graph: nodes = wet rooms; edge weights:
- HARD edges (must cluster): master_BR↔master_BA, KITCHEN↔LIVING/DINING, UTILITY↔KITCHEN (preferred but not required).
- HARD anti-edges: POOJA↔any wet room (when `pooja_adjacency_mode="strict"`).
- SOFT edges: typical_BR↔typical_BA pairs; bath_only↔wc_only same-cluster preference.

**Deterministic greedy partition** (per reviewer #5, my F1):
1. **Seed step**: emit one cluster per HARD-edge anchor, in this order:
   - master_BR/master_BA pair (if both exist)
   - KITCHEN seed
   - For each remaining typical_BA, sort by `(priority ASC, room_id_lex ASC)` and seed its own cluster.
2. **Merge step**: pairwise compare clusters in seeded-order. Merge if cluster-centroid distance ≤ `adjacency_threshold_m` AND merge does not violate `max_risers`.
3. **Tie-break** (when scores equal): always lower `room_id` wins lex-ASC; if cluster IDs tie, lower `cluster_id` (= seed room_id) wins.
4. **Termination**: no more merges possible OR `max_risers` reached.

This is fully deterministic: same inputs → same output, byte-for-byte. Replay tests (B-219) verify.

### Phase 3 — Wall assignment (FULL DETERMINISTIC SPEC v0.3)

For each cluster (in seed order):
1. Score eligible walls per Phase 1 against the cluster's primary category.
2. Greedy pick highest-scoring wall not yet used by another cluster.
3. **Backtrack** (per reviewer #14): if assignment causes Inv 4/5/5b/6 violation, undo and try next-best wall. Track `states_explored: int`.
4. If `states_explored > config.max_backtrack_states`: terminate. If best-found is feasible, accept and emit `provenance.search_truncated=True`. If best-found infeasible, raise `WetZoneInfeasibleError`.

### Phase 4 — Trap-arm distance + provenance

For each wet room:
1. Determine `fixture_type` from category + bathroom_subtype mapping (BATHROOM with COMBINED subtype → "water_closet" + "lavatory" + "shower"; v0.3 uses worst-case = max trap arm, refined later).
2. Compute Euclidean distance from room centroid to assigned riser anchor → `trap_arm_distances[room_id]`.
3. Validate against `kb/plumbing_minimums.json`: `trap_arm_distances[room_id] <= MAX_TRAP_ARM_M[fixture_type]` (Inv 11 v0.3).
4. Record any UNVERIFIED rows used → `provenance.unverified_plumbing_rows_used`.
5. If `config.require_verified_plumbing=True` AND any unverified rows used → raise `PlumbingConfidenceTooLow` (mirrors C9 NBCConfidenceTooLow).

### Adjacency definition (carried forward unchanged from v0.2)

Two rooms `r1` and `r2` are **adjacent** iff:
- They share a wall segment of length ≥ 1.0m, OR
- Their bounding-box projections onto the same axis overlap AND distance ≤ `config.adjacency_threshold_m`.

For Inv 5 master-BA-to-master-BR (pre-placement): "assigned wet wall is in master bedroom's `acceptable_wall_set`" (per reviewer #2's revision).

---

## § 4 — Invariants (REVISED v0.3 — Inv 11 replaced per reviewer #7)

| # | Invariant | Mode |
|---|---|---|
| 1 | Every BATHROOM in brief appears in `wet_wall_assignment` | RAISE |
| 2 | Every KITCHEN appears (if `has_kitchen`) | RAISE |
| 3 | UTILITY appears (if present) | RAISE |
| 4 | Every assigned wall_id exists in `Grid.wall_segments` AND meets Phase 1 eligibility | RAISE |
| 5 | Master BATHROOM's wall ∈ master BEDROOM's `acceptable_wall_set` | RAISE if `require_master_bath_adjacency=True`; WARN otherwise |
| 5b | KITCHEN's wall is adjacent to LIVING/service zone | RAISE |
| 6 | POOJA not on same wall as any wet room AND not on a wall sharing the same axis | RAISE if `pooja_adjacency_mode="strict"`; WARN if `"soft"` |
| 7 | `riser_count >= 1` if ≥1 wet room | RAISE |
| 8 | `riser_count <= effective_max_risers` | RAISE if STRICT; WARN otherwise |
| 9 | Every `room_id` exists in `RoomSizeTable` | RAISE |
| 10 | `total_wet_run_length_m >= 0` AND finite | RAISE |
| **11 (REVISED v0.3)** | **For every wet room: `trap_arm_distances[room_id] <= MAX_TRAP_ARM_M[fixture_types_per_room[room_id]]`** (engineering invariant per IPC/UPC, replacing v0.2 heuristic) | **RAISE** |
| 12 | `trap_arm_distances[room_id]` exists for every wet room | RAISE |
| 13 | Each `RiserGroup.wet_room_ids` non-empty | RAISE |
| 14 | `RiserGroup.anchor.wall_id` matches every member's `wet_wall_assignment` (consistency) | RAISE |
| **15 (NEW v0.3)** | **Every room with a `wet_wall_assignment` has a non-empty `acceptable_wall_sets` entry, AND its assigned wall ∈ that set** | RAISE |
| **16 (NEW v0.3)** | **`fixture_types_per_room[room_id]` is a key in `kb/plumbing_minimums.json` for every wet room** | RAISE |

---

## § 5 — Failure modes (REVISED v0.3)

```
WetZonePlanError (base)
├── PerCandidateError (caught and aggregated)
│   ├── WetZoneInfeasibleError      — Inv 4/5/5b violation
│   ├── PoojaAdjacencyError         — Inv 6 strict
│   ├── RiserCountExceededError     — Inv 8 STRICT
│   ├── TrapArmDistanceExceededError — Inv 11 (NEW v0.3 — engineering hard fail)
│   └── ClusterIntegrityError       — Inv 13/14
├── BatchWetZoneInfeasibleError     — all candidates failed per-candidate
└── PlumbingConfidenceTooLow        — NEW v0.3, systemic; mirrors NBCConfidenceTooLow
```

---

## § 6 — Test coverage requirements

Target ~125 tests (up from v0.2's 115 — Inv 11 + Inv 15/16 + reviewer-driven cases):

- ~30 schema tests (RiserAnchor, RiserGroup, WetZonePlan, WetZoneScoringWeights, config invariants)
- ~32 invariant tests (Inv 1-16 across modes + boundary)
- ~22 phase-logic tests (Phase 1 eligibility + scoring; Phase 2 deterministic clustering with replay snapshots; Phase 3 backtracking + truncation)
- ~18 partial-batch tolerance tests
- ~10 STRICT-mode escalation tests
- ~13 orchestrator end-to-end tests (real C4→C5→C6→C7→C8→C9→C10 pipeline)

Cumulative baseline target at C10 ship: 2155 + 125 ≈ **2280 passed**.

---

## § 7 — Open questions surfaced at v0.3

**Q11**: BATHROOM with COMBINED subtype maps to multiple fixtures (WC + lavatory + shower). For Inv 11, do we (a) take max trap-arm distance across fixtures (worst case), (b) emit per-fixture distances, or (c) treat the bathroom as one entity with a representative fixture?
- **Recommendation**: (a) for v1 — worst-case max_trap_arm = WC distance (longest of the three at 1.83m). Refines later when C12 places fixtures within rooms. Document in Inv 11 commentary.

**Q12**: `WetZoneScoringWeights` defaults — the bathroom_axis values lean on Vastu literature. Web sources we cited say "south/southeast/west preferred for toilets". Is this enough authoritative grounding to ship as default, or should defaults be neutral (all 0.5) and users opt in via config?
- **Recommendation**: ship the Vastu-leaning defaults but flag them in `_origin` as secondary_consensus, mirroring B-204 pattern. Users in non-Vastu markets override via config.

**Q13**: Should `RiserAnchor.column_id` be required (forcing every riser to align to a column) or optional (allowing free-floating risers with snap_distance=None)?
- **Recommendation**: optional. Forcing alignment over-constrains; column_alignment is a *bonus*, not a *requirement*. C12 vertical alignment will validate stack feasibility downstream.

**Q14**: What happens when `Phase 3 backtracking truncates` AND the best-found-state is feasible? We accept it (per spec) but mark `search_truncated=True`. Should this also bump `placement_risk_level` (parallel to C9 PRL)?
- **Recommendation**: yes. Add `placement_risk_level: PlacementRiskLevel` to `WetZonePlanProvenance` for caller-visible degradation signal. Severity-weighted as C9: search_truncated=1, max_risers=1, soft mode active=1 → MEDIUM/HIGH thresholds.

---

## § 8 — Open backlog at v0.3

- **B-215**: Refine "minimum stack-fit length" (v1: 1.5m) — pending plumbing-engineer review.
- **B-216**: `adjacency_threshold_m` default tuning post-C11 placement data.
- **B-217 (UPDATED)**: Wall-tier classification (`EXTERNAL`/`SERVICE_CORE`/`INTERIOR`) — SERVICE_CORE in v2; INTERIOR post B-066.
- **B-219**: Deterministic-replay tests with hash snapshots for clustering+assignment.
- **B-220**: Full hydraulic primitives (DFU loading, slope feasibility, vent stack compatibility) — v0.3 ships partial (trap arm distance only); full pass at plumbing-engineer review.
- **B-221**: `WetZonePlanProvenance.remediation_hints` (parallel to B-207 for C9).
- **B-222 (NEW v0.3)**: Primary-source verification for `kb/plumbing_minimums.json` — analogous to B-150 for `nbc_room_minimums.json`. Trigger: pre-launch plumbing-engineer review.

**B-218 RESOLVED-AS-MISFRAMED** at Walk #2 audit: grep confirmed `RoomSizedCandidate.corridor_designed_candidate.oriented_candidate` chain already exists; no upstream amendment needed. Documented as a Rule-11 self-audit win — caught a 200-line phantom spec before authoring it.

---

## § 9 — Rule 11 spec audit on v0.3 PROPOSED

Per Rule 11 (LOCKED at S34), proactive audit before requesting LOCK.

**PATCH-NOW (in v0.3 itself): 1**

| Patch | Action |
|---|---|
| P1 | Phase 4 step 1 says "BATHROOM with COMBINED subtype → 'water_closet' + 'lavatory' + 'shower'; v0.3 uses worst-case = max trap arm". This is a v0.3 simplification but I didn't check whether the multi-fixture mapping is enumerable from existing C9 schema. Grep first. (Verified: `RoomSizeRequirement.bathroom_subtype` exists; Q11 captures the design choice. Patch = none needed; commentary already there.) |

**OPEN QUESTIONS surfaced**: Q11-Q14 above. Need walk attention.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v3-1 | Phase 2 "merge step" uses centroid distance — but rooms haven't been placed yet (C10 runs before C11). What centroid? | **BUG IN SPEC** — needs walk fix. Centroid-of-rooms doesn't exist pre-placement. The merge criterion should be over **acceptable_wall_sets overlap** or **eligible-wall co-occurrence**, not geometric distance. Fix in v0.4. |
| F-v3-2 | `acceptable_wall_sets[room_id]` is emitted but the spec doesn't say HOW to compute it. Logic is hand-waved. | **NEEDS WALK** — define computation. Likely: for master_BR, set = all walls of length ≥ master_BR.liveability_min_width_m AND tagged EXTERNAL (so the BR could plausibly attach there). |
| F-v3-3 | `WetZoneScoringWeights` has no weight for "row already used by another cluster". When assignment phase backtracks, score should *decrease* for already-used walls — but not encoded. | **NEEDS WALK** — add `wall_reuse_penalty: float = -0.5` or similar. |
| F-v3-4 | KB plumbing_minimums.json has fixture types not enumerable from C9's RoomCategory + BathroomSubtype directly. KITCHEN maps to "kitchen_sink"; BATHROOM/COMBINED maps to ??? (3 fixtures). Need explicit enum mapping. | **NEEDS WALK** — add `_fixture_types_per_room_category` mapping table to spec § 3 Phase 4. |
| F-v3-5 | Inv 11 raises `TrapArmDistanceExceededError` per-room; if a room's trap arm is over by 0.05m (wiggle-room), should it actually raise or downgrade to WARN? | **NEEDS WALK** — likely add `trap_arm_tolerance_m` to config (default 0.0 = strict; can be relaxed by user accepting plumbing-code violations). |
| F-v3-6 | `placement_risk_level` proposed in Q14 but not in v0.3 schema yet. If accepted, schema needs update. | **PENDING Q14 RESOLUTION** — once accepted, fold into `WetZonePlanProvenance` definition. |
| F-v3-7 | The walk-resolved scope table (§ 1) lists 6 Q's resolved, but new Q11-Q14 aren't in the table — table will get unwieldy across walks. | **COSMETIC** — consider moving "resolved" Q's to an appendix in v0.4. |
| F-v3-8 | Test count target says 125. v0.2 said 115. Each new invariant adds 4-6 tests typically. Inv 11 + 15 + 16 = 3 new invariants × ~5 = 15 new tests. 115 + 15 = 130, not 125. Math sanity. | **MINOR** — adjust target to 130 in v0.4 or document why 125 is the stable target. |

**REJECTED-AS-CONSIDERED**:
- "Should we ship `kb/plumbing_minimums.json` with all rows as `secondary_consensus` and require explicit verification before ship?" — No. v1 ships with the KB and a `require_verified_plumbing` config gate (default False). Production users who care opt in. Identical pattern to C9's `require_verified_nbc`.
- "Should we add a wall-thickness primitive for bathroom-vs-living interior walls (acoustic concern)?" — No. C11 placement decides interior wall thickness; C10 stays at envelope-wall scope.
- "Should `WetZoneScoringWeights` defaults be city-specific (Tamil Nadu ≠ Delhi)?" — No. v1 keeps a single default; B-205-style luxury/standard/compact-mode and city-specific weights are v2.

**Audit summary**: 1 patch-now (resolved as no-op via grep), 8 walk findings (F-v3-1 through F-v3-8), 3 rejected. Audit ran; not performative. **F-v3-1 is a real bug in the spec — Phase 2 merge step uses pre-placement centroid which doesn't exist.** Must fix in v0.4. This is exactly what Rule 11 is designed to catch.

---

## § 10 — Status

- **v0.3 PROPOSED**. **NOT LOCKED.**
- LOCK BLOCKED on:
  - C7 amendment v0.2 (B-212) reaching LOCK
  - 8 v0.3 walk findings F-v3-1 through F-v3-8 resolved
  - 4 open questions Q11-Q14 adjudicated
  - Real bug F-v3-1 fixed in v0.4
- Estimated walks to LOCK: 3-4 more (was 4-6; reducing because v0.3 absorbs ~9 amendments).

---

**End of v0.3 PROPOSED.** Awaits Ramalingam's reading + walk #3 direction.
