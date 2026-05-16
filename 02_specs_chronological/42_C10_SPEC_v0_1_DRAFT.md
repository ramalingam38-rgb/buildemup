# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v0.1 DRAFT

**Component**: 10 (canonical Track 3 numbering)
**Status**: v0.1 DRAFT — opens spec arc. **NOT LOCKED.**
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 entry.
**Predecessors**: consumes C9 (Room Sizer) — `RoomSizedCandidate` from S34.
**Successors**: feeds C11 (geometric placement), C12 (vertical alignment), C14 (evaluation hard constraints + soft objectives).

---

## § 0 — Why this exists

In Indian residential construction, **plumbing is the single largest hidden cost of a bad layout**. Bathrooms scattered on three different walls = three vertical risers, three sets of waterproofing, three points of ceiling damage risk. Bathrooms grouped on one wall = one riser, lower cost, fewer leak points. The architecture doc lists this as one of the six Indian-family optimisation objectives: *score_wet_zone_efficiency → ₹ plumbing cost*.

C9 produces a sized room set with no wall-attachment opinions. C11 does geometric placement (XY coordinates). C10 sits between them and answers: **which wall does each wet room attach to, and which other wet rooms does it group with, such that the eventual placement minimises plumbing run length and maximises stack alignment?**

C10 does NOT place rooms. It produces *constraints and groupings* that C11 honours during placement. This separation matches the Track 3 architecture and avoids Pattern B (building-without-wiring): C10 trusting C11 to handle geometry, C11 trusting C10 to handle wet-zone semantics.

---

## § 1 — Scope (open questions surfaced at v0.1)

**Q1 (CRITICAL — needs Ramalingam direction)**: Single-floor or multi-floor?
- C9 is single-floor (FloorRoomBrief is one floor). Wet-stack alignment ("kitchen above kitchen") is multi-floor by definition.
- Option A: C10 is single-floor only. It produces wet-zone groupings within ONE floor. C12 (Vertical Alignment) handles cross-floor stack alignment by consuming multiple C10 outputs (one per floor).
- Option B: C10 takes a tuple of floor-specific RoomSizedCandidates (one per floor) and plans wet-zones holistically across floors.
- **Recommendation**: Option A. Cleaner separation. C10 stays at C9's scope (one floor); stacking is C12's job per architecture v3 sequence ([10] Wet-Zone Stack Planner → [11a/b] Mutation/NSGA-II → [12] Vertical Alignment).
- The "stack" in the component name then refers to *plumbing stack* (riser column), not *floor stack* — i.e., grouping bathrooms so they share a riser within a single floor, with riser column position locked for downstream multi-floor alignment.

**Q2**: Is kitchen part of wet-zone planning, or only bathrooms?
- Kitchen has plumbing (sink) but lower water volume than bathrooms. NBC and contractor norms in India usually treat kitchen plumbing separately (different stack, often closer to the rear wall).
- Option A: C10 plans kitchen + bathrooms together as one wet-zone graph.
- Option B: C10 plans bathrooms only; kitchen handled implicitly via wall-adjacency rule.
- **Recommendation**: Option A — include kitchen, but allow it to belong to a separate riser group from bathrooms. Both are wet rooms; ignoring kitchen produces architecturally weak plans (kitchen across the house from bathrooms wastes pipe).
- Utility room (washing machine, sink) also has plumbing — also include.

**Q3**: Hard constraint vs soft objective scope?
- Architecture v3 puts "plumbing feasibility" in HARD constraints (C14 stage 1) and "wet-zone efficiency" in SOFT objectives (C14 stage 2).
- Option A: C10 produces BOTH outputs — a hard "is there any feasible wet-wall assignment for this layout?" verdict + a soft "groupings score" (₹ plumbing cost estimate or normalised efficiency score 0–10).
- Option B: C10 produces only hard verdict; C14 does the soft scoring later.
- **Recommendation**: Option A. The grouping decision IS the soft signal — making C10 emit only a binary verdict throws away the work it just did. C14 consumes C10's grouping output to compute its soft score.

**Q4**: Does C10 produce ONE wet-zone plan per candidate, or N alternatives?
- C9 produces tuple of 1–3 RoomSizedCandidate. C11 will mutate via topology operators. Does C10 also produce alternatives, or commit to one wet-zone plan per input candidate?
- **Recommendation**: One plan per input candidate. Alternatives come later via C11a topology mutation (one of the 9 operators is "wet-wall rotation"). C10 commits; C11a mutates.

**Q5**: What if there's no good wet-wall assignment (e.g., LIVING room is between two bathroom groups, blocking shared wall)?
- Pattern A (fail-fast) per C9 precedent: raise `WetZoneInfeasibleError` at the candidate level; orchestrator aggregates per-candidate errors as in C9's `BatchSizingInfeasibleError` pattern.
- Soft fallback (e.g., "best available even if subpar") undermines the C14 hard-constraint contract.
- **Recommendation**: Pattern A. Hard infeasibility raises; soft suboptimality scores low.

---

## § 2 — Contract (DRAFT)

```python
def plan_wet_zones(
    room_sized_candidates: tuple[RoomSizedCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    *,
    config: WetZonePlanConfig | None = None,
) -> tuple[WetZonePlannedCandidate, ...]:
    """C10 entry point.

    Per-candidate semantics (mirrors C9 v0.7 § 14.40): each input candidate
    is planned independently. PerCandidateError subclasses are caught and
    aggregated; the batch raises BatchWetZoneInfeasibleError only if ALL
    candidates fail.
    """
```

`WetZonePlannedCandidate` = `RoomSizedCandidate` + `wet_zone_plan: WetZonePlan` + `provenance: WetZonePlanProvenance`.

`WetZonePlan` (v0.1 sketch — refined in walks):
- `wet_wall_assignment: dict[room_id, WetWallID]` — which wall each wet room attaches to. Wet rooms = BATHROOM, KITCHEN, UTILITY.
- `riser_groups: tuple[RiserGroup, ...]` — connected groups of wet rooms sharing a vertical plumbing stack.
- `kitchen_riser_group_id: str | None` — kitchen typically gets its own riser; tracked separately.
- `wet_wall_axis: tuple[WallSegmentID, ...]` — the wall segments that carry plumbing risers (anchors C12 vertical alignment downstream).
- `total_wet_run_length_m: float` — soft-objective input for C14.
- `riser_count: int` — count of distinct vertical risers.
- `non_wet_room_buffer_zones: tuple[room_id, ...]` — rooms (typically POOJA, certain BEDROOMs) that must NOT be adjacent to wet walls per cultural / waterproofing norms.

---

## § 3 — Behavioural sketch (deliberately under-specified at v0.1)

**Phase 1 — wet-wall candidate identification**: enumerate exterior + structural walls eligible to carry a riser. Eligibility rules drawn from NBC + Indian construction norms (TBD walk). Likely criteria: external wall preference for ventilation; wall must be ≥ X m long to fit a stack; wall must not face the entry façade (cultural aesthetic norm — verify in walk).

**Phase 2 — wet-room clustering**: graph-cluster bathrooms by adjacency need (e.g., master bathroom adjacent to master bedroom; common bathroom near sleeping zones; kitchen typically near service zone). Output: 1–3 clusters per floor.

**Phase 3 — wall assignment**: assign each cluster to a wet-wall candidate, minimising total run length subject to:
- Master bathroom on a wall adjacent to master bedroom (HARD).
- Kitchen on a wall adjacent to service/dining zone (HARD).
- POOJA never adjacent to wet wall (HARD — Vastu / cultural).
- Riser count ≤ config.max_risers (default: TBD; v1 likely 2 for Indian single-family).

**Phase 4 — provenance + verdicts**: emit WetZonePlanProvenance with rule_trace, plumbing_cost_estimate (₹), riser_efficiency_score (0–10), and any WARN-tier findings (e.g., master bathroom on opposite wall from master bedroom forced by geometry → soft penalty, not hard fail).

---

## § 4 — Invariants (v0.1 — to be expanded in walks)

| # | Invariant | Mode |
|---|---|---|
| 1 | Every BATHROOM in the brief appears in `wet_wall_assignment` | RAISE |
| 2 | Every KITCHEN in the brief appears in `wet_wall_assignment` (if has_kitchen) | RAISE |
| 3 | UTILITY (if present) appears in `wet_wall_assignment` | RAISE |
| 4 | Every assigned wall is eligible per Phase 1 rules | RAISE |
| 5 | Master BATHROOM's wall is adjacent to master BEDROOM's likely wall (TBD geometric def) | RAISE |
| 6 | POOJA is not adjacent to any wet wall | RAISE |
| 7 | `riser_count >= 1` (degenerate-zero impossible if ≥1 wet room exists) | RAISE |
| 8 | `riser_count <= config.max_risers` | RAISE / WARN (TBD per Q3) |
| 9 | All `room_id`s in `wet_wall_assignment` exist in the input `RoomSizeTable` | RAISE |
| 10 | `total_wet_run_length_m >= 0` | RAISE |

More invariants will surface during walks. v0.1's job is to anchor enough to evaluate the design, not bulletproof it.

---

## § 5 — Open backlog at v0.1 (file these per Rule 9.2 if walks confirm)

- **B-NNN-α**: define WallSegmentID upstream — does C7 / C8 emit a stable wall identifier? If not, C10 needs to derive one.
- **B-NNN-β**: kitchen-to-bathroom riser distance threshold below which they should share a riser vs above which they should not.
- **B-NNN-γ**: wet-wall eligibility — exterior preference, length minimum, façade avoidance — needs primary-source check (NBC clauses on plumbing + Indian construction practice).
- **B-NNN-δ**: cultural rules — POOJA-not-adjacent-to-wet-wall, master-bath-adjacent-to-master-bed — confirm scope and any user-overrideable knobs.

---

## § 6 — Failure modes (v0.1 — mirrors C9 § 6 typed hierarchy)

```
WetZonePlanError (base)
├── PerCandidateError (caught and aggregated by orchestrator)
│   ├── WetZoneInfeasibleError   — Inv 4/5 violation; no eligible wall for a needed cluster
│   ├── PoojaAdjacencyError      — Inv 6; POOJA forced adjacent to wet wall by geometry
│   └── RiserCountExceededError  — Inv 8 RAISE branch
└── BatchWetZoneInfeasibleError  — all candidates failed per-candidate
```

Plus systemic errors (TypeError, ValueError on caller-error checks; NotImplementedError for non-rectangular plot per B-066).

---

## § 7 — Rule 11 spec audit at v0.1 DRAFT

Per Rule 11 (LOCKED at S34), this DRAFT runs through a proactive audit before opening to reviewer walks. Findings:

**PATCH-NOW (in this DRAFT itself)**: 0 — DRAFT is the patch; everything below the line is a finding to surface.

**OPEN QUESTIONS surfaced** (these go to walks for adjudication):
- Q1 single-floor scope (recommendation given; needs Ramalingam confirm)
- Q2 kitchen inclusion (recommendation given; needs walk)
- Q3 hard/soft split (recommendation given; needs walk)
- Q4 alternatives count (recommendation given; needs walk)
- Q5 fail-fast vs soft fallback (recommendation given; needs walk)

**SPEC-AUDIT FINDINGS** (things I'm uncertain about even after drafting):

| # | Finding | Verdict |
|---|---|---|
| F1 | "Wet wall" is not formally defined upstream. C7 emits Grid columns; C8 emits CorridorPath envelopes. Neither emits "wall segments" as a typed entity. C10 will need to derive walls from envelope geometry, which is non-trivial. | **NEEDS WALK** — possibly amend C7 or C8 to emit walls explicitly. |
| F2 | The architecture doc lists "wet-wall rotation" as one of the 9 topology mutation operators (C11a). If C11a can rotate the wet wall after C10 commits, what's the point of C10 committing? | **NEEDS WALK** — likely answer: C10 commits a *valid* assignment; C11a mutates to find *better* assignments; C14 scores. C10's commit is the seed, not the final. |
| F3 | Indian cultural rules (Vastu) are domain-specific and partially contested. POOJA-not-near-wet-wall is well-established but other Vastu prescriptions vary by tradition. C10 should encode minimal cultural rules behind config flags, not bake them in. | **NEEDS WALK** — define which rules are HARD vs config-toggleable. |
| F4 | Plumbing cost estimation (₹) requires city-specific rates. C10 might just emit `total_wet_run_length_m` and let C14's cost engine convert to ₹ using its city KB. | **NEEDS WALK** — separation of concerns suggests yes. |
| F5 | This DRAFT does not specify how C10 interacts with `OrientedCandidate` from C6. Wet-wall preference (e.g., "south wall has more sun, less ideal for bathrooms") may depend on orientation. | **NEEDS WALK** — does C10 take OrientedCandidate as a separate input, or implicitly via the candidate chain? |
| F6 | "Wet zone efficiency" appears as a soft objective in C14. C10 outputs `riser_efficiency_score`. Are these the same number, or does C14 compute its own from C10's primitives? | **NEEDS WALK** — likely the latter (separation of concerns). |
| F7 | The C9 spec has 18 invariants; C10 v0.1 has 10. v0.1 is deliberately under-specified, but the gap suggests I'm not done thinking. | **EXPECTED — v0.1 is by design under-specified.** Walks will surface more. |

**REJECTED-AS-CONSIDERED** (looked at, not real issues at this draft stage):
- "Should C10 handle dry rooms (BEDROOM, LIVING) at all?" — No. C10 is wet-room scoped. Dry rooms appear only as adjacency constraints (POOJA-not-adjacent, master-BR-adjacent-to-master-BA).
- "Should C10 produce alternative plans for the same input?" — Covered in Q4. Recommendation: no (C11a mutates).
- "Should C10 use the C7 grid for stack column placement?" — Yes, implicitly. Risers should align with structural columns where possible. Walks will detail.

---

## § 8 — What this DRAFT is NOT

- NOT LOCKED. Per Rule 8, only Ramalingam locks. v0.1 is the *opening* of the spec arc, not the result.
- NOT comprehensive. § 4 lists 10 invariants; final LOCKED version will have more. Walks will surface gaps.
- NOT yet verified against primary sources. NBC clauses on plumbing, Indian wet-zone construction practice, and Vastu rules need web-search verification per Rule 7 / Rule 11 discipline. **No claim in this DRAFT cites a primary source yet.** First walk should attack this.
- NOT yet ready for code. Per Obligation 1, no C10 code work begins until C10 is LOCKED.

---

## § 9 — Recommended first walk

**Walk #1 focus**: Q1 (single-floor scope) and F1 (wall-segment representation upstream). These are the two most foundational decisions; everything else depends on them.

**Walk #1 method**: per Rule 7, web-search the NBC clauses + Indian-construction wet-zone practice; grep C7/C8 codebase for any wall-segment emission. Rule 11 audit the result.

---

**End of v0.1 DRAFT.** Awaits Ramalingam's first reading and direction on the open questions.
