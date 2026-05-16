# C13 SPEC v0.1 PROPOSED — Door Placement

**Status**: vN PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor**: C12 v1.0 LOCKED.
**Origin**: S44 session, after C12 v1.0 build complete.

---

## § 0 — Purpose & v1 guarantee boundary

### 0.1 What C13 does

For every PlacedRoom in a PlacedCandidate, C13 decides:
- Which wall (which SharedEdge) the door sits on
- Where along that wall the door is positioned
- Which direction the door swings (into-room vs into-corridor)
- The door's clear width (default = wall's NBC minimum from C12)

**Output**: tuple of Door records attached to (or returned alongside)
the PlacedCandidate.

### 0.2 What C13 does NOT do (v1 boundary)

- Does NOT modify room positions (C12's geometry is immutable input)
- Does NOT modify shared-edge geometry (C12's edges are immutable input)
- Does NOT score door quality (that's C14's Connection-Graph Quick Check)
- Does NOT compute door-cost (that's C14/C15 cost layer)
- Does NOT do multi-floor door alignment (orthogonal — each floor has its own doors)

### 0.3 C13's relationship to C12

**Key design insight**: C12 already shipped:
- `SharedEdge.doorway_feasible` (NBC 2016 minima check)
- `SharedEdge.min_required_clear_width_m`
- `SharedEdge.overlap_length_m` / `overlap_start_m` / `overlap_end_m`
- Inv 12: HARD-adjacent pairs have doorway-feasible shared edges

C13 inherits this. It does NOT re-derive NBC minima or re-check feasibility.
It selects which feasible edges become realized doors.

### 0.4 v1 guarantee boundary (per C12 v0.5-A2 precedent)

v1 guarantees:
1. Every PlacedRoom has at least one door (Inv D1)
2. Every door is on a `doorway_feasible=True` SharedEdge (Inv D2)
3. Swing-arc conflicts between adjacent doors are detected + resolved (Inv D5)
4. Deterministic byte-equal replay given same input (Inv D7)
5. Door clear width ≥ NBC 2016 minimum per category-pair (Inv D3)

v1 does NOT guarantee:
- Globally optimal door positioning (step-depth minimization is best-effort)
- Aesthetic concerns (sight-lines, "first thing you see when entering")
- Window-blocking avoidance (no window data in v1 inputs — backlog)
- Cultural placement rules (e.g., pooja-room door orientation per vastu)

These deferred concerns are explicitly filed at § 12 backlog.

---

## § 1 — Inputs

### 1.1 Required inputs

```python
@dataclass(frozen=True)
class DoorPlacementInput:
    placed_candidate: PlacedCandidate     # from C12 output
    entry_room_id: str                    # which room is the main entry
    config: DoorPlacementConfig
```

### 1.2 Upstream contract assumptions

- `placed_candidate.shared_edges` is canonically sorted (C12 Inv 8)
- `placed_candidate.shared_edges` contains only NBC-feasible edges (C12 § 3.6)
- `placed_candidate.placed_rooms` sorted lex-ASC by room_id (C12 Inv 8)
- Reachability already verified upstream (C12 Inv 11 — Phase 0b BFS passed)

### 1.3 Schema version probe (per C12 v0.4-A1 precedent)

C13 will probe `C12_VERSION` at ingress. If C12 ships a MAJOR/MINOR bump
that changes SharedEdge schema, C13 raises `UpstreamSchemaDriftError`.
v1 binds against `C12_VERSION = "v1.0"`.

---

## § 2 — Output schema (LOCKED at v1)

### 2.1 Door dataclass

```python
@dataclass(frozen=True)
class Door:
    """One door realized on a shared edge.

    Fields:
      - room_a_id, room_b_id: canonical lex-ASC, matches the SharedEdge
        this door sits on
      - axis: "vertical" or "horizontal" (matches SharedEdge.axis)
      - position_along_edge_m: distance from edge start (overlap_start_m)
        along the edge axis. Range [0, overlap_length_m - clear_width_m].
      - clear_width_m: door's unobstructed opening width. Must be
        >= edge.min_required_clear_width_m.
      - swing_direction: "into_room_a" or "into_room_b" — which room
        the door arc swings INTO when opened.
      - is_main_entry: True iff this door is the building's main entrance.
    """
    room_a_id: str
    room_b_id: str
    axis: Literal["vertical", "horizontal"]
    position_along_edge_m: float
    clear_width_m: float
    swing_direction: Literal["into_room_a", "into_room_b"]
    is_main_entry: bool
```

### 2.2 DoorPlacementResult

```python
@dataclass(frozen=True)
class DoorPlacementResult:
    source_placed_candidate_signature: str
    doors: tuple[Door, ...]  # canonical lex-ASC by (room_a_id, room_b_id)
    c13_version: str
    cache_key: str
```

---

## § 3 — Algorithm

### 3.1 Phase A — Per-room door selection

For each room R (iterated in lex-ASC order by room_id):
1. Find all SharedEdges touching R (already filtered to feasible).
2. If R is the entry room → main entrance door:
   - Prefer edges marked as connecting to external envelope (v1: any
     edge with `room_b_id == "EXTERNAL"`; future: explicit boundary
     detection)
   - clear_width_m = 1.0m (NBC main entrance minimum)
   - is_main_entry = True
3. Else if R has corridor adjacency:
   - Pick the corridor edge with maximum overlap_length_m (most placement
     flexibility). Tie-break: lex-ASC corridor room_id.
   - clear_width_m = max(NBC minimum, configurable default)
4. Else (room only adjacent to other rooms):
   - Pick the edge minimising step-depth from main entry (BFS over
     existing assigned doors).
   - clear_width_m = NBC minimum for the category pair.

### 3.2 Phase B — Swing direction assignment

For each selected door:
1. Default rule: swing INTO the smaller-area room (so the door arc
   doesn't block circulation in the larger room).
2. Exception: doors to bathrooms ALWAYS swing INTO the bathroom (privacy
   + corridor clearance — NBC convention).
3. Exception: main entry ALWAYS swings INTO the building (away from
   external space).
4. Exception: kitchens MAY swing OUT if the kitchen is small and the
   adjacent space is corridor or dining (utility convention).
5. Canonical encoding: swing_direction is "into_room_a" or "into_room_b"
   resolved against the lex-ASC (room_a, room_b) ordering.

### 3.3 Phase C — Position along edge

For each door:
1. Default position: corner-aligned (`position_along_edge_m = 0.0`).
   Corner alignment preserves wall surface for furniture placement
   (per Neufert ergonomic convention).
2. If corner placement creates a swing-arc conflict with an adjacent
   wall's door (Phase D), shift position toward the edge midpoint by
   discrete increments (per v0.2-A4 grid-snap convention from C12).
3. If no conflict-free position exists, raise `DoorPositionInfeasible`
   (per-candidate error, STRICT/WARN dispatch as C12).

### 3.4 Phase D — Swing-arc conflict detection

For each pair of doors (D1, D2) where D1.room_a or D1.room_b shares
a room with D2:
1. Compute D1's 90° swing arc (quarter-circle of radius =
   D1.clear_width_m, anchored at hinge corner).
2. Compute D2's swing arc.
3. If arcs overlap geometrically → conflict.
4. Conflict resolution priority:
   a. Shift D1 along its edge by one grid unit
   b. Shift D2 along its edge by one grid unit
   c. Flip D1.swing_direction (if exception rules permit)
   d. Flip D2.swing_direction
   e. Reduce clear_width_m to NBC minimum (if greater)
   f. Raise `SwingArcConflictError` (per-candidate, STRICT/WARN)

Iteration order is canonical: lex-ASC door pairs.

### 3.5 Phase E — Canonical output assembly

1. Sort doors lex-ASC by (room_a_id, room_b_id).
2. Compute cache_key as
   `sha256(C13_VERSION || C12 cache_key || doors canonical-serialized)`.
3. Return DoorPlacementResult.

---

## § 4 — Invariants

| ID | Statement | Where enforced |
|---|---|---|
| D1 | Every PlacedRoom has ≥1 door | Phase A |
| D2 | Every door sits on a doorway_feasible SharedEdge | Phase A filter |
| D3 | clear_width_m ≥ edge.min_required_clear_width_m | Phase A |
| D4 | Door fits within edge: position + width ≤ overlap_length_m | Phase C |
| D5 | No two doors have overlapping swing arcs | Phase D |
| D6 | Exactly one door has is_main_entry=True (per candidate) | Phase A |
| D7 | Byte-equal replay across runs | Canonical ordering throughout |
| D8 | doors tuple sorted lex-ASC | Phase E |
| D9 | Swing direction respects exception rules (bathroom-in / entry-in) | Phase B |
| D10 | No door's clear width exceeds 1.5m at v1 (sanity bound) | Phase A |

---

## § 5 — STRICT vs WARN dispatch (per C12 precedent)

- `UpstreamSchemaDriftError`, `C13ConfigurationError`: ALWAYS halt
- `DoorPositionInfeasible`, `SwingArcConflictError`,
  `EntryRoomNotFoundError`: per-candidate errors
  - STRICT → raise immediately
  - WARN → collect into `failures: tuple[FailureRecord, ...]`

---

## § 6 — Cache key + replay (per C12 precedent)

C13 builds its own cache key inheriting C12's:
```python
c13_cache_key = sha256(
  C13_VERSION ||
  c12_cache_key ||
  config_cache_relevant_fields
)
```

Cache-relevant config fields:
- `strict_mode`
- `default_clear_width_m` (if greater than NBC minimum)
- `corner_alignment_preference`

Cache-IRrelevant config fields:
- `per_candidate_wallclock_seconds`
- `telemetry_sink`

---

## § 7 — Performance budget

- Per single-floor PlacedCandidate: ≤2 seconds (n ≤ 15 rooms ≤ 20 edges)
- Per 3-floor batch: ≤6 seconds
- These are SOFT budgets — exceeding raises a backlog signal, not an error.

---

## § 8 — Test mandate (per C12 v0.6-A1 precedent)

PBT floor: ≥1 PBT per invariant D1-D10 (10 minimum) + ≥1 PBT per
failure-mode trigger (3 minimum) + ≥1 adversarial generator (5 minimum)
= **18 PBT floor**.

Integration test mandate: composition with C12 SharedEdge surface
(B-C13-INTEGRATION-C12-COVERAGE).

---

## § 9 — Telemetry (per C12 precedent)

Five event types reusing the C12 sink pattern:
- `DoorPlacementEvent` (per door: room pair, axis, clear_width)
- `SwingArcConflictEvent` (when conflict detected + resolution applied)
- `EntryRoomResolutionEvent` (per candidate: which room chosen as entry)
- `DoorPerformanceEvent` (wallclock + door count)
- `EdgeSelectionDiversityEvent` (which edge picked per room, for
  diversity analysis)

---

## § 10 — Provenance (per C12 precedent)

`place_doors_with_provenance()` returns
`(DoorPlacementResult, DoorPlacementProvenance)`. Standard
`place_doors()` returns just the result.

---

## § 11 — Public API

```python
def place_doors(
    *,
    placed_candidates: tuple[PlacedCandidate, ...],
    config: DoorPlacementConfig,
    c12_cache_key: str,
) -> DoorPlacementBatchResult:
    ...

def place_doors_with_provenance(...) -> tuple[DoorPlacementBatchResult, DoorPlacementProvenance]:
    ...
```

---

## § 12 — Backlog (existing + new from this spec)

### Backlog items C13 spec depends on / creates

| ID | Description | Origin | Trigger | S{N}-scope | Effort |
|---|---|---|---|---|---|
| B-C13-WINDOW-AVOIDANCE | Door selection avoids blocking windows | v1 boundary | When window data is in upstream inputs | post-v1 | M |
| B-C13-SIGHT-LINE-OPTIMIZATION | Choose door angle for entry sight-line quality | v1 boundary | When C14 sight-line scoring lands | post-v1 | L |
| B-C13-EXTERNAL-EDGE-DETECTION | Detect envelope-boundary edges for entry-door placement (v1 uses "EXTERNAL" placeholder) | § 3.1 step 2 | v1 build | v1-MANDATORY | S |
| B-C13-VASTU-PLACEMENT | Cultural placement rules (pooja door orientation, NE entry preference) | v1 boundary | When C5 vastu-rules layer lands | post-v1 | M |
| B-C13-FURNITURE-CLEARANCE | Door swing doesn't conflict with furniture layout | v1 boundary | When C9 furniture-fit data is available | post-v1 | M |
| B-C13-DOUBLE-DOOR-PAIRS | Some entries need 2-leaf doors (luxury/wide openings) | v1 boundary | When upstream specifies leaf count | post-v1 | S |
| B-C13-POCKET-DOORS | Pocket / sliding door variants | v1 boundary | When upstream specifies door type | post-v1 | M |

### Routed amendments needed

| ID | Description | Routes to |
|---|---|---|
| B-C12-EXTERNAL-EDGE-MARKER | C12 SharedEdge needs a way to mark envelope-boundary edges (for entry-door logic) | C12 v1.1 amendment OR C13 adapter |

### Spec § 12 summary table

**Total new backlog items: 7 (6 post-v1, 1 v1-MANDATORY, 1 routed-amendment-required).**

---

## § 13 — Open questions for Ramalingam adjudication

1. **External-edge marker**: should C13's "EXTERNAL" placeholder become
   a proper C12 v1.1 amendment to SharedEdge, or stay as a C13-local
   adapter convention? (Affects B-C12-EXTERNAL-EDGE-MARKER routing.)

2. **Entry room source**: should C13 receive `entry_room_id` as input
   (caller specifies), or derive it from a heuristic? v1 spec assumes
   caller-specified; if heuristic-derive is wanted, that's a separate
   responsibility.

3. **Multi-door rooms**: living rooms / kitchens often have multiple
   doors. Spec § 3.1 says "≥1 door per room" (Inv D1). Should v1 allow
   multiple doors per room when upstream signals indicate? v0.1 says
   single-door minimum + caller-specified extras allowed.

4. **STRICT-only at v1?**: C12 went STRICT-MATERIALIZED-only at v1.
   Should C13 follow that pattern (no Tier A resolvers)?

5. **PBT floor**: 18 minimum is a guess scaled from C12's 25. Acceptable?

---

**End of v0.1 PROPOSED spec.**

Per Rule 8: vN PROPOSED. PENDING Ramalingam LOCK adjudication.
Ready for next-session critique walks (target: same 5-walk discipline
as C12) before LOCK.
