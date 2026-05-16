# C13 SPEC v0.2 PROPOSED — Door Placement (delta from v0.1)

**Status**: vN PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor**: C13 v0.1 PROPOSED.
**Origin**: S44 critique walk #2 (external review), 17 items walked,
10 amendments + 5 new backlog items.

This document is the DELTA from v0.1. For unchanged sections refer to
`spec_C13_v0_1_PROPOSED.md`. Amendments listed below by ID (A1-A10).

---

## Walk #2 amendments

### A1 — Replace local BFS step-depth with weighted-shortest-path

**Origin**: Reviewer item 2.
**Problem**: § 3.1 step 4 used raw BFS step-depth — local heuristic that
can produce pathological circulation (e.g., bedroom → bedroom →
bedroom → bathroom).
**Amendment**: Replace § 3.1 step 4 with weighted shortest-path using
semantic edge weights:

```
edge_weight = base_weight × semantic_multiplier
```

Where `semantic_multiplier` is:

| Path-through context | Multiplier |
|---|---|
| Corridor edge | 0.5 (bonus — preferred) |
| Living / dining (public) | 1.0 (neutral) |
| Kitchen | 2.0 (penalty — utility space) |
| Bedroom (private) | 5.0 (heavy penalty — through-bedroom routing is anti-pattern) |
| Bathroom | 10.0 (catastrophic — never route through) |
| Pooja (cultural-private) | 8.0 (heavy penalty per cultural norms) |

Cache-relevant: yes (changes door selection).
**Inv D11 added**: no door routes through a bedroom or bathroom unless
explicitly required by upstream HARD adjacency hint.

---

### A2 — Configurable corner offset (replace 0.0 default)

**Origin**: Reviewer item 3.
**Problem**: § 3.3 step 1 defaulted `position_along_edge_m = 0.0`,
producing high swing-conflict frequency at corners where columns,
chases, switches, and wardrobes live.
**Amendment**: Replace § 3.3 step 1 with:

```
position_along_edge_m = max(corner_offset_m, ...)
```

Default `corner_offset_m = 0.15` (150mm — Neufert ergonomic minimum).
Configurable. Snapped to C12 grid via A7 below.

Cache-relevant: yes (changes door geometry).

---

### A3 — Add hinge_side + leaf_thickness to Door schema

**Origin**: Reviewer items 4 + 6.
**Problem**: Door swing direction alone is ambiguous. Two doors with
`swing_direction="into_room_a"` can hinge on opposite ends of the
shared edge, producing different arc geometry. This breaks Inv D7
(byte-equal replay) because implementations could diverge.
**Amendment**: Extend Door schema:

```python
@dataclass(frozen=True)
class Door:
    # ... v0.1 fields ...
    hinge_side: Literal["start", "end"]
    """'start' = hinge at overlap_start_m end of the edge.
    'end' = hinge at overlap_start_m + overlap_length_m end.
    Combined with swing_direction, fully determines arc geometry."""

    leaf_thickness_m: float = 0.04
    """Door leaf thickness. Default 40mm (Indian standard residential).
    Affects swept-volume conflict detection."""
```

`frame_depth_m` deferred to v1.x per `B-C13-FRAME-DEPTH-MODELING`
(needs C7 grid integration for column-aligned frame depths).

Inv D7 strengthened: hinge_side selection is canonical = "start" by
default unless swing direction + room geometry mandate "end" for arc
clearance.

Cache-relevant: yes (full geometry).

---

### A4 — Bounded conflict resolution with state snapshot

**Origin**: Reviewer item 5.
**Problem**: § 3.4 used strict greedy lex-ASC iteration which can trap
the solution space (D1 shift resolves pair (D1,D2) but creates new
conflict with D3).
**Amendment**: Replace § 3.4 conflict resolution with bounded retry:

```
max_conflict_resolution_iterations = 5  (default, configurable)

For each conflict round:
  1. Snapshot current door state
  2. Apply resolution strategies (a-f from v0.1) in canonical order
  3. Re-scan all pairs for new conflicts created by resolution
  4. If conflict count strictly decreased: continue
  5. If conflict count plateaued or increased: ROLLBACK to snapshot,
     try next resolution strategy
  6. If all strategies exhausted at this round: raise
     SwingArcConflictError (STRICT) or record failure (WARN)
```

Inherits the monotonic-δ abort pattern from C12 MFRA (v0.2-A2).

Cache-relevant: no (deterministic given config; resolution order is
canonical).

**Inv D12 added**: conflict_resolution_iterations_used ≤
max_conflict_resolution_iterations.

---

### A5 — C12 v1.1 amendment for SharedEdge.edge_type

**Origin**: Reviewer item 7 + my Rule 11 self-analysis (carried from
v0.1 Section 13 Q1).
**Problem**: § 3.1 step 2 used `room_b_id == "EXTERNAL"` string sentinel
for main-entry edge detection. C12 SharedEdge schema has no concept of
external-boundary edges (grep-verified). Sentinel-string approach is
architecturally fragile per reviewer.
**Amendment**: Route a SPEC-AMENDMENT to C12 v1.1:

**Routed amendment to C12**: Extend `SharedEdge` schema with
`edge_type: EdgeType` enum:

```python
class EdgeType(Enum):
    INTERNAL = "internal"
    EXTERNAL_ENVELOPE = "external_envelope"
    SERVICE = "service"  # service entry, utility access
    BALCONY = "balcony"  # semi-external (balcony/verandah)
```

For v1.0 SharedEdges currently in production, default = INTERNAL.
External edges are derived from envelope-boundary geometry (room's
edge touches envelope perimeter) at C12 ingress.

**Routed via B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT** (HIGH-priority,
LOCK-blocking for C13 LOCK):

- Effort: M (2-3 days). Touches C12 schema (semver MINOR bump to
  v1.1.0 since it's an additive field with backward-compatible
  default).
- Pre-condition for C13 LOCK: this amendment LOCKED first.

Within C13 spec: § 3.1 step 2 rewrites to use `edge.edge_type ==
EXTERNAL_ENVELOPE` instead of string sentinel.

Cache-relevant: yes.

---

### A6 — Bathroom swing preferred-inward, not mandatory

**Origin**: Reviewer item 9 (web-verified).
**Problem**: § 3.2 step 2 said "doors to bathrooms ALWAYS swing INTO
the bathroom." Web search confirmed this is overgeneralized — small
bathrooms commonly outswing (safety + fixture clearance + accessibility).
**Amendment**: Replace § 3.2 step 2 with:

```
Bathroom doors: preferred swing INTO the bathroom UNLESS:
  (a) Inward arc would conflict with bathroom fixtures (after
      reasonable fixture-zone reservations). v1 uses a simple
      proxy: bathroom area < 4 m² (40 sqft).
  (b) Accessibility hint flagged on the bathroom (future v1.x).
  (c) Bathroom is a powder room (no shower/tub) — preferred outward
      for fixture clearance.
```

For v1: rule (a) is the only hard branch; (b) and (c) require
upstream input flags not present at v1.0, filed as backlog.

Inv D9 weakened (no longer absolute "ALWAYS inward"); replaced by:
**Inv D9'**: bathroom doors that swing outward must NOT conflict
with adjacent corridor / room traversal (verified in Phase D).

Cache-relevant: yes.

---

### A7 — Explicit grid-snap on position_along_edge_m

**Origin**: Reviewer item 10.
**Problem**: § 3.3 mentioned "discrete increments" but didn't
mandate grid-snap on the INITIAL door position. FP drift across
Python/platform versions could break Inv D7 byte-equal replay.
**Amendment**: Add explicit snap to § 3.3:

```python
# In Phase C (position selection):
position_along_edge_m = snap_to_grid(
    raw_position,
    grid_m=DEFAULT_GRID_SNAP_M,  # 50mm, inherited from C12
)
```

Same `snap_to_grid` function as C12 (grep-confirmed available at
`buildemup.components.c12.bounds`). Re-export from C13 to avoid
direct C12-internal dependency.

Inv D7 strengthened: byte-equal replay guaranteed via grid-snapped
coordinates (same mechanism as C12 v0.2-A7).

Cache-relevant: no (changes precision representation only).

---

### A8 — Room-importance-DESC iteration order

**Origin**: Reviewer item 11.
**Problem**: § 3.1 iterated rooms lex-ASC, meaning "BATH_01" could
consume best corridor adjacency before "LIVING" got to pick.
**Amendment**: Replace § 3.1 iteration order. Process rooms in this
order (priority DESC, lex-ASC on ties):

1. Main entry room (highest priority — must succeed)
2. Living room
3. Kitchen
4. Pooja room
5. Dining
6. Master bedroom
7. Other bedrooms (lex-ASC)
8. Bathrooms (lex-ASC)
9. Utility / store / servant / balcony (lex-ASC)

Priority order is hard-coded for v1 (cache-relevant). Future
customization via configurable priority table is filed as
`B-C13-CONFIGURABLE-PRIORITY` (v1.x).

Full bipartite optimization (process all rooms simultaneously)
filed as `B-C13-GLOBAL-DOOR-ASSIGNMENT` (v2+).

Cache-relevant: yes.

---

### A9 — Phase F post-resolution reachability re-check

**Origin**: Reviewer item 12.
**Problem**: Phase D's conflict resolution can shift / flip / shrink
doors. The resulting door graph might violate Inv 11 (reachability)
that C12 already established for the underlying placement.
**Amendment**: Add Phase F to § 3:

```
Phase F — Post-resolution graph integrity verification

After Phase D + Phase E:
  1. Build the door-induced reachability graph:
     - Nodes: rooms
     - Edges: room pairs connected by a Door
  2. BFS from main-entry room
  3. Every room must be reachable
  4. If not: raise PostResolutionUnreachabilityError (STRICT) or
     record failure (WARN)
```

The graph is door-induced (not edge-induced) because some shared
edges may have no door — only those with doors count as paths.

**Inv D13 added**: every PlacedRoom is reachable from main entry
via the door-induced graph.

Cache-relevant: no (verification only, not generative).

---

### A10 — Cache key includes upstream schema version probes

**Origin**: Reviewer item 15.
**Problem**: § 6 derived cache key from `C12 cache_key` but didn't
explicitly include the C12 schema version constants. If C12 ships
v1.x with edge-semantics changes that DON'T bump cache_key
generation, C13 replay could become silently stale.
**Amendment**: Strengthen § 6 cache key derivation:

```python
c13_cache_key = sha256(
    C13_VERSION ||
    C12_VERSION ||                              # NEW
    EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION || # NEW
    EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION ||# NEW
    EDGE_TYPE_SCHEMA_VERSION ||                 # NEW per A5
    c12_cache_key ||
    config_cache_relevant_fields
)
```

Combined with C13's own schema version probes at ingress (mirror
of C12 v0.4-A1 pattern), this catches BOTH version bumps AND
silent semantic drift.

Cache-relevant: yes (this IS the cache key).

---

## Updated invariants table

Building on v0.1 § 4:

| ID | Statement | Source |
|---|---|---|
| D1 | Every PlacedRoom has ≥1 door | v0.1 |
| D2 | Every door sits on a doorway_feasible SharedEdge | v0.1 |
| D3 | clear_width_m ≥ edge.min_required_clear_width_m | v0.1 |
| D4 | Door fits within edge: position + width ≤ overlap_length_m | v0.1 |
| D5 | No two doors have overlapping swing arcs | v0.1 |
| D6 | Exactly one door has is_main_entry=True | v0.1 |
| D7 | Byte-equal replay across runs | v0.1, strengthened by A3 + A7 |
| D8 | doors tuple sorted lex-ASC | v0.1 |
| D9' | Bathroom doors that swing outward don't conflict with adjacent traversal | A6 (replaces v0.1 Inv D9) |
| D10 | No door's clear width exceeds 1.5m at v1 (sanity bound) | v0.1 |
| **D11** | No door routes through a bedroom or bathroom unless HARD adjacency hint requires it | **A1 NEW** |
| **D12** | conflict_resolution_iterations_used ≤ max_conflict_resolution_iterations | **A4 NEW** |
| **D13** | Every PlacedRoom reachable from main entry via door-induced graph | **A9 NEW** |

13 → 13 invariants (one replaced, three added, total still 13 due to D9 replacement).

---

## Updated § 12 backlog (additions from this walk)

### New backlog items

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-C13-DOOR-CARDINALITY | Multi-door support per room (living, kitchen with utility exit, master suite) | Walk #2 item 1 | When upstream room metadata exposes `min_doors_required` / `preferred_door_count` | M (v1.x) |
| B-C13-FRAME-DEPTH-MODELING | Door frame depth for accurate swept-volume conflict detection | A3 deferred | When C7 grid integration provides column-aligned frame depths | M (v1.x) |
| B-C13-COMPACT-BATHROOM-OUTSWING | Bathroom outward swing for compact + accessibility cases | A6 (b)(c) deferred | When upstream provides accessibility hints OR bathroom typology metadata | S (v1.x) |
| B-C13-CONFIGURABLE-PRIORITY | Customizable room-priority table for A8 iteration order | A8 hardcoded | When non-residential occupancy types ship | S (v1.x) |
| B-C13-GLOBAL-DOOR-ASSIGNMENT | Full bipartite door-edge assignment optimization | A8 deferred | When n>20 rooms OR door-selection quality becomes a production complaint | L (v2+) |
| B-C13-SPATIAL-INDEXING-PHASE-D | Sweep-line / interval-tree pruning for Phase D O(n²) | Walk #2 item 13 | When n>50 rooms (luxury/commercial) | M (v2+) |
| B-C13-OCCUPANCY-TYPE-ABSTRACTION | Residential / commercial / hospitality typology routing | Walk #2 item 17 | When BuildemUp scales beyond Indian residential | L (v2+) |

### Routed elsewhere (not C13-scope)

| Reviewer item | Route to |
|---|---|
| #8 (fire-egress model) | `B-C14-FIRE-EGRESS-MODEL` — Connection-Graph Quick Check territory |
| #14 escalation (window data priority) | Already filed `B-C13-WINDOW-AVOIDANCE`; escalate annotation from "post-v1" → "v1.x post-LOCK fast-follow" |

### Escalated existing items

| ID | v0.1 status | v0.2 status | Reason |
|---|---|---|---|
| B-C13-WINDOW-AVOIDANCE | post-v1 | v1.x post-LOCK fast-follow | Reviewer item 14: "practical impact larger than the spec currently frames" |
| B-C13-EXTERNAL-EDGE-DETECTION | v1-MANDATORY | SUPERSEDED by A5 (now routed to C12 v1.1 as `B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT`) | Cleaner architecture per reviewer #7 |

### Backlog summary table

**Total new backlog items: 7. Total in spec § 12: 12 + 1 routed C12 amendment.**

Walk #2 trajectory: **10 amendments + 5 new C13 backlog items + 1 routed
C12 amendment + 2 pushback + 2 routed elsewhere**. Significant churn
for a v0.2 walk — comparable to C12 v0.2 (10 amendments).

---

## Pushback items (NOT amended)

**Walk #2 item 1 (single-door assumption)**: v1 retains single-door
minimum per Inv D1. Multi-door is a real need but adding to v1 schema
adds significant complexity without clear v1 use case. Filed as
`B-C13-DOOR-CARDINALITY` for v1.x. The reviewer's example cases
(living, kitchen with utility) DO often share corridor adjacency,
which gives a natural single-corridor-edge door that suffices for
v1. **PUSH BACK on amending v1 schema.**

**Walk #2 item 16 (STRICT/WARN silent bad architecture)**: PUSH BACK.
The reviewer suggests "WARN may exist only for telemetry/debug,
never for final candidate materialization." Architecture already
separates successes from failures (per C12 precedent —
`DoorPlacementBatchResult.doors` is success-only; failures are in
a separate tuple). Downstream consumers MUST filter, but the
contract is explicit. Removing WARN entirely would break batch
processing's per-candidate isolation. **No amendment.**

---

## Open questions resolved + new

**v0.1 Question 1 (external-edge marker)**: RESOLVED via A5 — C12 v1.1
amendment, not C13-local hack. Cleaner architecture, matches reviewer
#7 conclusion.

**v0.1 Question 2 (entry-room source)**: Standing. v0.1 spec says
caller-specified; this seems right per spec discipline (C13 doesn't
do its own heuristics).

**v0.1 Question 3 (multi-door rooms)**: RESOLVED — v1 single-door
minimum + `B-C13-DOOR-CARDINALITY` for v1.x.

**v0.1 Question 4 (STRICT-only at v1)**: Standing. After walk #2
pushback item 16, leaning AGAINST STRICT-only (WARN is useful for
batch isolation).

**v0.1 Question 5 (PBT floor of 18)**: Standing. With 3 new invariants
(D11/D12/D13) the PBT floor should rise to **21** (1 per invariant
floor of 13 + failure-trigger floor of 3 + adversarial floor of 5).

**NEW v0.2 Question 6**: Should C13 LOCK be blocked on C12 v1.1
shipping (per A5), or can C13 LOCK first with the EXTERNAL-string
adapter and C12 v1.1 land as a fast-follow? My recommendation: block
C13 LOCK on C12 v1.1. The adapter introduces architectural debt that
the reviewer correctly identifies as fragile.

---

## Self-analysis (Rule 11)

Three concerns about THIS walk that I want flagged:

1. **A5 is LOCK-blocking and itself needs a critique walk on the C12
   side.** Routing an amendment to a LOCKED component (C12 v1.0) is a
   non-trivial governance action. Recommend treating
   `B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT` as a C12 v1.1 spec walk in its
   own right (matching C12 v0.2-style discipline).

2. **A1 weighted-shortest-path multipliers (bathroom=10, bedroom=5,
   etc.) are hand-tuned heuristics with no empirical basis at v1.**
   These should ideally be calibrated against accepted plans (when
   that data exists). Filed implicitly under `B-C13-LAYOUT-MEMORY-BANK`
   precedent.

3. **A6 bathroom-area threshold of 4 m² is hand-picked.** Web search
   didn't surface a clear cutoff. NBC 2016 has bathroom area minima
   (1.8 m² separate, 2.8 m² combined per Part 3) but no inswing/outswing
   threshold. Recommend marking this as v1-conservative-best-effort.

---

## Closing

v0.2 PROPOSED is substantially LARGER than v0.1 because of A5 (routed
C12 amendment) and A1 (semantic edge weights). Walk yield: 10
amendments suggests v0.3 walk is likely to reveal more issues — C12
walk yields were 10 → 8 → 2 → 2 → 1 (diminishing returns over 5
walks). Recommend at least 2-3 more walks before LOCK candidacy.

Per Rule 8: vN PROPOSED. PENDING Ramalingam LOCK adjudication.

Ready for either:
- (a) Ramalingam direct feedback on amendments,
- (b) Walk #3 (self-critique against this v0.2),
- (c) Defer further C13 walks until C12 v1.1 amendment lands.

My recommendation: (c) — pause C13 walks until the routed C12 v1.1
amendment is itself spec-walked and LOCKED, since A5 depends on its
final shape. Then resume C13 walks #3+ with finalized A5 form.
