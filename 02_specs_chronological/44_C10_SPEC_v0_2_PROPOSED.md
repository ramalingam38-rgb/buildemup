# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v0.2 PROPOSED

**Component**: 10 (canonical Track 3 numbering)
**Status**: v0.2 PROPOSED. **NOT LOCKED.** Supersedes v0.1 DRAFT.
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 Walk #1 outcome.
**Predecessors consumed**: C9 (Room Sizer) — `RoomSizedCandidate`; C6 (Orientation) — `OrientedCandidate`; C7 (Grid) — `Grid` with `wall_segments` per C7 amendment v0.2; C4 — `PlotAnalysis`.
**Successors fed**: C11 (placement), C12 (vertical alignment), C14 (evaluation hard + soft).
**LOCK BLOCKED on**: B-212 (C7 amendment v0.2 must LOCK first).

---

## § 0 — Why this exists

Indian residential plumbing is the single largest hidden cost of a bad layout. Bathrooms scattered on three different walls = three vertical risers, three sets of waterproofing, three points of ceiling damage risk. Bathrooms grouped on one wall = one riser, lower cost, fewer leak points. Architecture v3 lists wet-zone efficiency as one of the six Indian-family optimisation objectives (`score_wet_zone_efficiency → ₹ plumbing cost`).

C9 produces a sized room set with no wall-attachment opinions. C11 does geometric placement. C10 sits between them and answers: **which wall does each wet room attach to, which other wet rooms does it group with, and how many vertical risers does that imply** — such that the eventual placement minimises plumbing run length and respects cultural/technical adjacency constraints.

C10 does NOT place rooms. It produces *constraints, groupings, and primitives* that C11 honours during placement and C14 scores during evaluation.

---

## § 1 — Scope (Walk #1 resolutions LOCKED IN)

**Q1 — Single-floor scope. RESOLVED: yes.** C10 plans wet-zones within ONE floor. C12 (Vertical Alignment) handles cross-floor stack alignment. The "stack" in the component name refers to *plumbing stack* (riser column), not *floor stack*.

**Q2 — Kitchen + utility inclusion. RESOLVED: yes, with separate riser group permitted.** Wet rooms = `BATHROOM`, `KITCHEN`, `UTILITY`. Kitchen tracked via separate `kitchen_riser_group_id` so it can occupy its own riser if geometry favours it.

**Q3 — Hard verdict + grouping primitives (NO scores). RESOLVED.** C10 emits both feasibility verdict (PerCandidateError on infeasibility, mirroring C9 Pattern A) AND grouping primitives (run length, bend count, riser count, wall segments used). **C10 does NOT compute scores.** C14 consumes primitives and computes all scores per single-source-of-truth principle.

**Q4 — One plan per candidate. RESOLVED: yes.** C11a's wet-wall-rotation operator (one of 9 topology mutations per Architecture v3) handles alternative-plan exploration. C10 commits one plan; C11a mutates.

**Q5 — Pattern A fail-fast on infeasibility. RESOLVED: yes.** No internal recovery loop in C10. Recovery via C11a mutation operators or upstream brief renegotiation.

---

## § 2 — Contract

```python
def plan_wet_zones(
    room_sized_candidates: tuple[RoomSizedCandidate, ...],
    oriented_candidates: tuple[OrientedCandidate, ...],   # NEW v0.2 per Walk #1
    floor_room_brief: FloorRoomBrief,
    grid: Grid,                                            # carries wall_segments per C7 amendment v0.2
    plot_analysis: PlotAnalysis,
    *,
    config: WetZonePlanConfig | None = None,
) -> tuple[WetZonePlannedCandidate, ...]:
    """C10 entry point. Per-candidate semantics mirror C9 § 14.40."""
```

`oriented_candidates` and `room_sized_candidates` must be parallel (same length, same candidate ordering) — caller-error layer asserts this.

`WetZonePlannedCandidate` = `RoomSizedCandidate` + `wet_zone_plan: WetZonePlan` + `provenance: WetZonePlanProvenance`.

### `WetZonePlan` schema (v0.2 — primitives only, scores stripped)

```python
@dataclass(frozen=True)
class WetZonePlan:
    wet_wall_assignment: dict[str, str]                  # room_id -> wall_id
    riser_groups: tuple[RiserGroup, ...]                 # connected wet-room groupings
    kitchen_riser_group_id: str | None                   # which group kitchen belongs to (None if kitchen absent)
    wall_segments_used: tuple[str, ...]                  # wall_ids carrying risers
    # Primitives for C14 (NEW in v0.2 — replaces deleted riser_efficiency_score):
    total_wet_run_length_m: float                        # sum of horizontal pipe runs to risers
    bend_count: int                                      # 90° elbows in horizontal runs
    trap_arm_distances: dict[str, float]                 # room_id -> distance from fixture to riser
    riser_count: int                                     # number of distinct vertical risers
    non_wet_room_buffer_zones: tuple[str, ...]           # room_ids that must NOT be adjacent to wet walls (POOJA + config-flagged BEDROOMs)


@dataclass(frozen=True)
class RiserGroup:
    group_id: str
    wall_id: str                                         # which wall this riser stack lives on
    wet_room_ids: tuple[str, ...]                        # wet rooms sharing this riser
    column_alignment: str | None                         # nearest C7 column grid_label, if applicable
```

### `WetZonePlanConfig`

```python
@dataclass(frozen=True)
class WetZonePlanConfig:
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    pooja_adjacency_mode: Literal["strict", "soft"] = "strict"   # NEW v0.2 — per Walk #1 #3 compromise
    max_risers: int | None = None                                # None = derived per tier (v1: SMALL=2, LARGE=3)
    adjacency_threshold_m: float = 0.0                           # 0 = shared-wall only; > 0 = within-distance counts as adjacent
    require_master_bath_adjacency: bool = True                   # Inv 5 — can be relaxed per design intent
```

---

## § 3 — Behaviour

### Phase 1 — Wet-wall candidate identification

Inputs: `Grid.wall_segments` (4 walls in v1) + `OrientedCandidate.facing` (Vastu / climate axis).

Eligibility per wall:
1. Length ≥ minimum stack-fit length (v1: 1.5m; B-215 to refine).
2. Tagged `EXTERNAL` (interior partition walls not allowed for risers in v1).
3. Vastu axis preference per `oriented_candidate.facing`: south/southeast generally preferred for bathroom location per Indian practice; north/northeast preferred for pooja. Walls scored by axis-fit, NOT eliminated.

### Phase 2 — Wet-room clustering

Build a graph: nodes = wet rooms; edges weighted by adjacency-need:
- Master BATHROOM ↔ master BEDROOM: HARD edge (Inv 5).
- KITCHEN ↔ DINING/SERVICE zone: HARD edge (Inv 5b).
- POOJA ↔ any wet room: HARD anti-edge (Inv 6).
- Typical bathrooms ↔ typical bedrooms: SOFT edge (preference).

Cluster via **deterministic greedy partitioning**:
1. Seed each cluster with a HARD-edge anchor (master-BR/master-BA pair, kitchen+service, etc.).
2. Merge clusters whose centroids are < `adjacency_threshold_m` apart.
3. Tie-break by `(cluster_size DESC, lowest_room_id_lex_ASC)` for determinism.

Output: 1–3 clusters per floor in v1.

### Phase 3 — Wall assignment

For each cluster, score eligible walls by:
- Vastu/orientation alignment (Phase 1 score).
- Total run length to nearest C7 column (riser anchored to column for vertical alignment).
- Adjacency to required dry rooms (master-BR for master-BA cluster).

Greedy assignment with backtracking on conflicts. Pattern A: if no eligible wall accommodates a HARD-required cluster, raise `WetZoneInfeasibleError`.

### Phase 4 — Provenance

Emit `WetZonePlanProvenance` with rule_trace covering: cluster membership decisions, wall scoring breakdown, any WARN-mode findings (e.g., master-BA forced onto a sub-optimal wall), unverified KB rows used.

### Adjacency definition (Inv 5 concrete — Walk #1 #2 baked in)

Two rooms `r1` and `r2` are **adjacent** iff:
- They share a wall segment of length ≥ 1.0m, OR
- Their bounding boxes are within `config.adjacency_threshold_m` AND share an axis (their projection onto either x or y axis overlaps).

For C10's purposes (Inv 5 master-BA-to-master-BR), since C10 runs *before* placement, "adjacent" means "assigned wet wall is on the same side of the envelope as the master bedroom's expected wet wall side". C11 placement enforces the actual geometric adjacency; C10 enforces the *side* prediction.

---

## § 4 — Invariants (expanded from v0.1's 10 to 14)

| # | Invariant | Mode |
|---|---|---|
| 1 | Every BATHROOM in brief appears in `wet_wall_assignment` | RAISE |
| 2 | Every KITCHEN in brief appears in `wet_wall_assignment` (if `has_kitchen`) | RAISE |
| 3 | UTILITY (if present) appears in `wet_wall_assignment` | RAISE |
| 4 | Every assigned wall_id exists in `Grid.wall_segments` AND meets Phase 1 eligibility | RAISE |
| 5 | Master BATHROOM's wall on same envelope side as master BEDROOM's expected side | RAISE if `config.require_master_bath_adjacency=True`; WARN otherwise |
| 5b | KITCHEN's wall is adjacent (per § 3 def) to LIVING / service zone | RAISE |
| 6 | POOJA not on same wall as any wet room AND not on a wall sharing the wet-wall axis (per Vastu sources) | RAISE if `config.pooja_adjacency_mode="strict"`; WARN if `"soft"` |
| 7 | `riser_count >= 1` (degenerate-zero impossible if ≥1 wet room) | RAISE |
| 8 | `riser_count <= effective_max_risers` (config or tier-derived) | RAISE if `enforcement_mode=STRICT`; WARN otherwise |
| 9 | Every `room_id` in `wet_wall_assignment` exists in `RoomSizeTable` | RAISE |
| 10 | `total_wet_run_length_m >= 0` AND finite | RAISE |
| 11 | `bend_count >= 0` AND `<= 4 * riser_count` (heuristic ceiling — anything more is implausible) | WARN |
| 12 | `trap_arm_distances[room_id]` exists for every wet room | RAISE |
| 13 | Each `RiserGroup.wet_room_ids` non-empty | RAISE |
| 14 | `RiserGroup.wall_id` matches the wall every member's `wet_wall_assignment` points to (consistency) | RAISE |

---

## § 5 — Failure modes (typed hierarchy)

```
WetZonePlanError (base)
├── PerCandidateError (caught and aggregated)
│   ├── WetZoneInfeasibleError   — Inv 4/5/5b violation; no eligible wall for required cluster
│   ├── PoojaAdjacencyError      — Inv 6 violation in strict mode
│   ├── RiserCountExceededError  — Inv 8 violation in STRICT mode
│   └── ClusterIntegrityError    — Inv 13/14 (internal consistency failure)
└── BatchWetZoneInfeasibleError  — all candidates failed per-candidate
```

Plus systemic: `TypeError`, `ValueError`, `NotImplementedError` (B-066 plot-shape gate).

---

## § 6 — Test coverage requirements

Per D-066 (mirror C9's structure):

- ~25 schema/contract tests (`WetZonePlan`, `RiserGroup`, `WetZonePlanConfig` invariants)
- ~30 invariant tests (Inv 1-14 across modes + boundary cases)
- ~20 phase-logic tests (Phase 1 eligibility, Phase 2 clustering, Phase 3 assignment)
- ~15 partial-batch tolerance tests (per § 14.40 pattern from C9)
- ~10 STRICT-mode escalation tests
- ~15 orchestrator end-to-end tests (uses real C4→C5→C6→C7→C8→C9→C10 pipeline on bangalore_40x60 fixture + variants)

**Target**: ~115 tests. Cumulative baseline at C10 ship: 2155 + 115 ≈ **2270 passed**.

---

## § 7 — Open questions surfaced at v0.2

These need walk attention BEFORE LOCK:

**Q6**: Master-bathroom wall prediction — when master-BR could go on multiple walls (geometrically valid for any of N walls), how does C10 pick the "expected side"? Three options: (a) use C6 OrientedCandidate's facing-derived heuristic; (b) emit a tuple of acceptable wall sides; (c) defer to C11 placement and only flag inconsistency post-hoc.
- **Recommendation**: (b) — emit `RoomSizedCandidate.expected_wet_walls: tuple[str, ...]` from C9 (small C9 amendment) OR derive in C10 from C6's facing. Cleaner is C10-derived.

**Q7**: When kitchen and bathroom clusters are far apart and force 2 risers, does C10 attempt a single-riser fallback by relaxing the kitchen-DINING adjacency edge? Pattern A says no (raise + let C11a mutate). Pattern A leaning confirmed; flagging for explicit walk decision.

**Q8**: `pooja_adjacency_mode` defaulting to `"strict"` — is this the right product default for the Indian market? Web evidence is unanimous (6+ sources) but the user-population question is "what fraction of users want strict Vastu". Without data, conservative-strict is the right default per the moat-feature framing in Architecture v3.

**Q9**: How does C10 handle the case where C9 emits 3 candidates but C6 emits 1 OrientedCandidate (because orientation is plot-level, not candidate-level)?
- **Likely answer**: C6 emits one OrientedCandidate; C10 broadcasts it across all C9 candidates. Verify by grepping C6 contract.

**Q10**: Is `column_alignment: str | None` enough, or does C10 need to emit the full `(x, y)` riser column position?
- **Recommendation**: column_label is sufficient; C12 looks up Grid.columns by label.

---

## § 8 — Open backlog at v0.2

Per Rule 9.2:

- **B-215**: Refine "minimum stack-fit length" (v1: 1.5m). Should depend on pipe diameter + structural detailing. Trigger: when plumbing engineer reviews v1 output.
- **B-216**: `adjacency_threshold_m` default — currently 0.0 (shared-wall-only). v2 may want > 0 for "within 0.5m counts as adjacent" semantics. Trigger: when C11 placement results show too many false-infeasibilities.
- **B-217**: Internal partition walls as wet-wall candidates (currently EXTERNAL-only). Trigger: post B-066 polygonal envelope work.

---

## § 9 — Rule 11 spec audit on v0.2 PROPOSED

Per Rule 11 (LOCKED at S34), proactive audit before requesting LOCK.

**PATCH-NOW (in this PROPOSED itself): 0** — PROPOSED is the patch; further sharpening goes to walks.

**OPEN QUESTIONS surfaced**: Q6-Q10 above. All five need walk attention.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F1 | Phase 2 clustering says "deterministic greedy partitioning" but the tie-break rule is stated only as one line. C9 spent significant text on similar deterministic-tie-break rules in allocator. C10 should match that rigor. | **NEEDS WALK** — bake fuller deterministic spec into v0.3. |
| F2 | "Vastu axis preference" in Phase 1 is described qualitatively but not given a scoring formula. Score weights need to be in spec, not in code. | **NEEDS WALK** — define numeric weights per axis or mark as `WetZoneScoringWeights` config. |
| F3 | Inv 6 "POOJA not on same wall AND not on a wall sharing the wet-wall axis" — the second clause is stronger than what web sources strictly require. Sources say "not adjacent" / "not share a wall" — the axis-sharing extension is mine. | **NEEDS WALK** — defensible (Vastu prohibits sharing wall with any wet area; same-axis on opposite ends still avoids that), but the spec should cite the source for the strengthening. |
| F4 | The contract takes `oriented_candidates` as a parallel tuple to `room_sized_candidates`, but caller-error layer just asserts "same length". What if they're same-length but candidate[0] in each refers to different things? | **NEEDS WALK** — likely fix: encode the linkage in `RoomSizedCandidate` itself (already carries `corridor_designed_candidate`; should also carry the upstream `OrientedCandidate` reference). Possible C9 amendment. |
| F5 | "C10 does NOT compute scores" is asserted, but `total_wet_run_length_m` is itself a derived metric. Where's the line? | **CLARIFICATION NEEDED** — distinction is "primitive geometric measurement" (C10) vs "weighted/normalized cost or quality score" (C14). Document this in v0.3 § 0. |
| F6 | C10 invokes "C7 column grid_label" for `RiserGroup.column_alignment` but not all risers will align to a grid column (geometry permitting). Need to define behaviour when no column is within snap distance. | **NEEDS WALK** — either `column_alignment: str | None` (current) means "None when no nearby column" or we add `column_snap_distance_m` config. Specify in v0.3. |
| F7 | C10's Phase 3 "greedy assignment with backtracking" is hand-waved. C9 would have specified the algorithm. | **NEEDS WALK** — either spec the algorithm or commit to "TBD in v0.3". |
| F8 | Tests target 115; v0.1 had 10 invariants and v0.2 has 14. Test count grows ~2x faster than invariants. Sanity check the math in v0.3. | **NEEDS WALK** — likely fine (each invariant has multiple test cases); confirm with test inventory. |

**REJECTED-AS-CONSIDERED**:
- "Should C10 emit a candidate-level confidence score?" — No. Confidence is a soft signal; C14 derives it from primitives.
- "Should C10 know about plot soil type for trap-arm slope?" — No. Slope is a placement-time / engineering concern; C12 or C14.
- "Should C10 have a 'fast path' that skips Vastu rules entirely?" — Yes, via `pooja_adjacency_mode="soft"` config; no need for separate fast-path.

**Audit summary**: 0 patch-now, 8 walk findings, 3 rejected-as-considered. Audit ran; not performative. **v0.3 is needed before LOCK** (this is normal — C9 took 7 walks).

---

## § 10 — Status

- **v0.2 PROPOSED**. **NOT LOCKED.**
- LOCK BLOCKED on:
  - C7 amendment v0.2 (B-212) reaching LOCK
  - 8 walk findings F1-F8 resolved or backlogged
  - 5 open questions Q6-Q10 adjudicated
- Estimated walks to LOCK: 4-6 (smaller than C9's 7-walk arc since architectural shape is clearer).

---

**End of v0.2 PROPOSED.** Awaits Ramalingam's reading + walk #2 direction.
