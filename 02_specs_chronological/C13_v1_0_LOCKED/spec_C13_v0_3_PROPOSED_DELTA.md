# C13 SPEC v0.3 PROPOSED — Door Placement (delta from v0.2)

**Status**: vN PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor**: C13 v0.2 PROPOSED DELTA.
**Origin**: S44 critique walk #3 (external review of v0.2). 16 items
walked, 12 amendments (3 partial reversals + 9 new) + 2 pushback + 1
NEW boundary clarification section. Net architectural correction.

This document is the DELTA from v0.2. v0.1 base + v0.2 delta + v0.3
delta = full spec.

---

## Central narrative of this walk

Walk #3's reviewer identified that v0.2's amendments quietly crossed
the C13/C14 component boundary:

- A1 (weighted shortest-path) is circulation **optimization**, not
  placement feasibility
- D11 (no through-bedroom) is a circulation **quality** rule, not a
  placement invariant
- A8 (semantic priority table) is layout **preference**, not placement
  necessity

Web-verified mainstream pattern (ScienceDirect 2020 + 2024 papers):
floor-plan systems separate **feasibility (CP-style)** from
**optimization (GA-style/scoring)**. C13 should be the former; C14 is
the latter.

v0.3 corrects course: partial reversals on A1/D11/A8, explicit
§ 0.5 boundary statement, and several supporting amendments that
keep C13 in deterministic-feasibility territory.

---

## NEW § 0.5 — C13/C14 boundary (LOCKED at v1)

Insert after v0.1 § 0.4:

### 0.5.1 Two-stage architecture

C13 (this component) is responsible for: **deterministic feasible
door placement**. Outputs guarantee:

- Every room has ≥1 door
- Every door sits on a doorway-feasible shared edge (NBC compliant)
- No swing-arc conflicts
- Reachability preserved (door-induced graph stays connected)
- Byte-equal replay across runs

C14 (downstream) is responsible for: **circulation quality scoring +
optimization advisory**. C14 computes:

- Weighted-path quality metrics (through-bedroom penalty,
  corridor-bonus, etc.)
- Privacy gradient
- Sight-line analysis
- Daylight/ventilation interaction with door positions
- "Could this be better?" feedback

### 0.5.2 What C13 explicitly does NOT optimize

To prevent boundary creep, C13's v1 LOCKED scope excludes:

1. **Weighted circulation scoring** — Reverted from v0.2 A1. C13 uses
   feasibility-priority selection only (B1 below).
2. **Through-room quality enforcement** — Reverted from v0.2 D11.
   Through-bedroom routing is flagged as advisory data, not rejected
   at C13 (B2 below).
3. **Privacy gradient optimization** — Backlog `B-C13-PRIVACY-GRADIENT`
   routed to C14.
4. **Sight-line scoring** — Backlog `B-C13-SIGHT-LINE-OPTIMIZATION`
   routed to C14.
5. **Semantic room ranking** — Reverted from v0.2 A8. C13 uses
   structural priority only (entry > corridor-adjacent > lex-ASC) (B6
   below).

### 0.5.3 How C14 receives C13's output

C14 consumes:
- `DoorPlacementResult` (LOCKED schema)
- `DoorPlacementProvenance` (per A10 + B11 typestate)
- `AdvisoryFlags` (NEW per B2 below) — soft-signal annotations C13
  produces but does not act on

C14 may then layer weights, scoring, optimization on top. C14's
output may include "C14 suggests reverting this door" feedback —
that goes to C15 (user-facing) not back to C13.

### 0.5.4 Boundary enforcement at LOCK

Any future C13 amendment that:
- Introduces weighted scoring beyond binary feasibility
- Adds quality-based selection criteria
- Performs optimization (anything iterative for "better" vs "valid")

must first justify why it's NOT C14's responsibility. This is the
governance gate that prevents the boundary creep walk #3 identified.

---

## Walk #3 amendments

### B1 — Partial reversal of A1 (weighted shortest-path)

**Origin**: Reviewer item 1 + boundary clarification.
**Reversal**: v0.2 A1 (weighted multipliers 0.5/1.0/2.0/5.0/10.0) is
**REMOVED from C13**. Walk #2's pathology fix (avoid BFS bedroom →
bedroom → bedroom → bathroom routing) is preserved differently:

**Replacement** for v0.1 § 3.1 step 4:

```
For non-corridor-adjacent rooms:
  1. Use simple BFS step-depth (v0.1 original)
  2. ADDITIONALLY: emit an AdvisoryFlag if the chosen path traverses
     through bedroom/bathroom/pooja
  3. C14 consumes AdvisoryFlags + applies weighted scoring + may
     emit "reroute suggested" feedback
```

C13 still terminates on the shortest BFS path — that's a feasibility
question. C14 decides whether that path is GOOD.

**Inv D11 v0.2 → REMOVED**. Replaced by AdvisoryFlag emission (B2).

Cache-relevant: yes (changes door selection back to simpler form).

---

### B2 — D11 reversal: AdvisoryFlag pattern

**Origin**: Reviewer item 2 (ultra-compact homes) + boundary
clarification.
**Reversal**: v0.2 Inv D11 ("no door routes through bedroom/bathroom
unless HARD hint requires it") was an absolute invariant. Walk #3
reviewer correctly notes this over-constrains compact Indian
typologies (mezzanine/staircase routing through sleeping spaces is
legitimate in some cases).

**Replacement**: Introduce `AdvisoryFlag` dataclass:

```python
@dataclass(frozen=True)
class AdvisoryFlag:
    """Soft signal from C13 to C14. Not actioned at C13."""
    flag_kind: Literal[
        "through_private_routing",
        "through_bathroom_routing",
        "through_pooja_routing",
        "long_corridor_route",
        "minimal_clearance_door",
        "bathroom_outswing_emergency_clearance",
    ]
    affected_room_id: str
    severity: Literal["info", "warning", "concern"]
    explanation_template: str  # human-readable explanation key
```

C13 emits these into `DoorPlacementResult.advisory_flags`. C14
decides what to do with them.

**Inv D11 v0.3**: zero advisory flags is preferred but not required.

Cache-relevant: yes (advisory flags are part of result).

---

### B3 — A4 strengthening: visited-state hashing + total-order tie-break

**Origin**: Reviewer items 3 + 12 (combined).
**Problem**: v0.2 A4's conflict-resolution monotonic-conflict-count
heuristic can reduce conflicts while degrading geometry. Also,
multiple equally-valid repairs need explicit tie-breaking for replay.

**Amendment**: Strengthen A4 with two additions:

**(a) Visited-state hashing (loop prevention)**:

```python
# In Phase D bounded retry:
visited_states: set[str] = set()

for iteration in range(max_conflict_resolution_iterations):
    state_hash = hash_door_configuration(doors)
    if state_hash in visited_states:
        # Loop detected → stop retrying, raise STRICT or record WARN
        break
    visited_states.add(state_hash)
    # ... rest of v0.2 A4 logic ...
```

**(b) Total-order tie-break for equally-valid repairs**:

When multiple resolution strategies produce equally-feasible states
(same conflict count, same geometry quality), tie-break in this
canonical order:

1. Minimal positional displacement (sum of |Δposition_along_edge|)
2. Maximal width preservation (prefer no clear_width_m reduction)
3. Hinge-side preservation (prefer keeping original hinge_side)
4. Swing-direction preservation (prefer keeping original direction)
5. Lexicographic edge ordering on (room_a_id, room_b_id)

**Inv D12 v0.3 strengthened**:
- Loop-free (visited-state hashing)
- Tie-break deterministic (total-order specified)

Cache-relevant: no (deterministic given config).

---

### B4 — False-confidence disclaimer + arc-fidelity tier

**Origin**: Reviewer item 4.
**Problem**: Adding hinge_side + leaf_thickness in v0.2 A3 made the
swing model LOOK more rigorous, but real swing collision depends on
frame projection, handle clearance, wall reveal offsets, perpendicular-
wall truncation, door-stop hardware. v1 doesn't model any of these.
Risk: downstream consumers assume physical correctness beyond
guarantees.

**Amendment**: Add explicit § 0.4.1 "geometric fidelity tier"
classification:

| Tier | Models | Status |
|---|---|---|
| 1 (v1.0 LOCKED) | Simplified swept arc + hinge + leaf thickness | Shipped via A3 |
| 2 (post-v1) | + Frame projection + wall thickness reveal | `B-C13-FRAME-DEPTH-MODELING` |
| 3 (v2+) | + Handle clearance + door-stop + perpendicular truncation | `B-C13-FULL-3D-SWING-MODEL` |

Document mandate: Tier 1 outputs MUST be labeled as "feasibility
approximation" in any user-facing presentation. C15 (UX layer)
enforces this disclosure.

**Inv D14 added**: every DoorPlacementResult carries a
`geometric_fidelity_tier: int = 1` field at v1.

Cache-relevant: no (documentation amendment).

---

### B5 — Protocol abstraction for C12 coupling

**Origin**: Reviewer item 5 (A5 creates tight C12-C13 coupling).
**Problem**: v0.2 A5 routes a C12 v1.1 amendment to add
`SharedEdge.edge_type`. Reviewer correctly notes this creates
release-train coupling: C13 evolution speed now depends on C12
semver cadence. Circular amendment churn risk.

**Amendment**: Introduce a formal contract abstraction:

```python
class C13ConsumesFromC12Edge(Protocol):
    """The fields C13 reads from C12's SharedEdge.

    Frozen at C13 v1.0 LOCK. Future C12 SharedEdge additions don't
    break C13 unless they change THESE fields' semantics.
    """
    room_a_id: str
    room_b_id: str
    axis: Literal["vertical", "horizontal"]
    overlap_start_m: float
    overlap_end_m: float
    overlap_length_m: float
    min_required_clear_width_m: float
    doorway_feasible: bool
    edge_type: EdgeType  # added in C12 v1.1 per v0.2 A5
```

C13 binds against this Protocol, not the raw C12 dataclass. v0.2's
direct schema reference is replaced by structural typing.

A future C12 v1.2 amendment that adds, say, `acoustic_isolation_db`
to SharedEdge does NOT trigger a C13 amendment because that field
isn't in the Protocol.

**Trade-off acknowledged**: this adds an indirection layer. The
benefit (decoupled release trains) outweighs the cost
(Protocol-maintenance overhead) per reviewer's reasoning.

Cache-relevant: yes (the Protocol becomes part of C13's stable
schema contract).

---

### B6 — Partial reversal of A8 (room priority simplification)

**Origin**: Reviewer item 7 (typology bias).
**Reversal**: v0.2 A8's 9-tier priority table (entry > living >
kitchen > pooja > dining > master bedroom > bedrooms > bathrooms >
utility/store/servant/balcony) was residential-typology-specific.
Reviewer correctly notes this fails for non-residential occupancies.

**Replacement**: Simplify v1 to **3-tier structural priority**:

1. Main entry room (must succeed first)
2. Corridor-adjacent rooms (lex-ASC, structural priority — corridor is
   the typology-agnostic circulation backbone)
3. All other rooms (lex-ASC)

The "living before kitchen before pooja" semantic ranking is REMOVED
from C13. C14 can advise on door-selection quality (e.g., "this living
room's door is poorly placed for entry sight-lines") but doesn't
require typology-specific iteration order at C13.

Full semantic priority for residential = `B-C13-SEMANTIC-PRIORITY-RESIDENTIAL`
(v1.x backlog, routed to C14).

Cache-relevant: yes.

---

### B7 — Phase F scope clarification (pushback documentation)

**Origin**: Reviewer item 8 + boundary clarification.
**Problem**: Reviewer wants Phase F to validate graph QUALITY, not
just connectivity. **PUSH BACK** per § 0.5 boundary.

**Amendment**: Strengthen § 3 Phase F documentation:

> Phase F validates STRUCTURAL CONNECTIVITY ONLY. Specifically:
> - Every PlacedRoom is reachable from main entry via the door-induced
>   graph (Inv D13).
>
> Phase F explicitly DOES NOT validate:
> - Path quality (long traversals, through-private routing)
> - Circulation efficiency
> - Sight-line quality
> - Privacy gradient
>
> These are C14's responsibility per § 0.5. C13 emits AdvisoryFlags
> (per B2) that C14 consumes for quality analysis.

Cache-relevant: no (documentation).

---

### B8 — Optional secondary door support

**Origin**: Reviewer item 10 (single-door pushback escalation).
**Problem**: With weighted-pathfinding demoted in B1, the single-door
limitation becomes less severe. But for living rooms, kitchens with
utility exits, and some service spaces, a secondary door is
genuinely useful.

**Amendment**: Add **caller-specified optional secondary door** at the
Room input level:

```python
@dataclass(frozen=True)
class RoomDoorPreference:
    """Per-room door cardinality hints. Caller-specified, never
    heuristically derived at v1.0."""
    room_id: str
    min_doors: int = 1
    max_doors: int = 1
    secondary_door_preference: Literal[
        "none",  # default
        "corridor",  # prefer corridor edge for secondary
        "utility",  # prefer utility-room edge for secondary
        "external",  # prefer envelope-boundary edge for secondary
    ] = "none"
```

The room-preference tuple is part of `DoorPlacementInput`. If a room
has `min_doors=2`, Phase A selects two edges (primary by B6
structural priority, secondary by preference). Phase D conflict
resolution treats secondary doors as equal priority to primary.

**Inv D1 strengthened**: every PlacedRoom has ≥ min_doors doors,
≤ max_doors doors.

Full heuristic-driven multi-door (no caller input required) =
`B-C13-AUTO-MULTI-DOOR` (v1.x or v2+, depending on signal).

Cache-relevant: yes.

---

### B9 — Reframe Phase D as bounded CSP-lite

**Origin**: Reviewer item 11 (excellent meta-observation).
**Problem**: Phase D now has retries + rollback + snapshots + visited-
state hashing + multi-state evaluation = bounded constraint search.
The spec still calls it "procedural repair logic" which understates
its complexity.

**Amendment**: Add new § 3.4.1 "Phase D as bounded CSP-lite":

> Phase D is formally a **bounded local search with deterministic
> backtracking**, not pure procedural repair.
>
> **State space**: Door configurations (combinations of position +
> hinge_side + swing_direction + clear_width per door).
>
> **Search guarantee**: Bounded by `max_conflict_resolution_iterations`
> (default 5). Termination: visited-state hashing prevents infinite
> loops.
>
> **Convergence assumption**: For n ≤ 15 rooms and ≤ 30 edges (v1
> scope), termination within the bound is empirically observed.
> Beyond n > 15, no convergence guarantee (filed under
> `B-C13-SPATIAL-INDEXING-PHASE-D` + `B-C13-LARGE-N-CSP-CONVERGENCE`).
>
> **Admissible mutations**: position shift (1 grid unit),
> swing-direction flip, clear-width reduction (to NBC minimum),
> hinge-side flip.
>
> **Inadmissible**: position jumps > 1 grid unit, width reduction
> below NBC minimum, edge migration (changing which SharedEdge a
> door uses — that's Phase A territory).

**Telemetry** (already in C13 spec § 9): add
`PhaseDSearchEvent(iterations_used, conflicts_at_start, conflicts_at_end, branching_factor)`.

Cache-relevant: no (documentation amendment + telemetry).

---

### B10 — § 0.5 explicit C13/C14 boundary (the central walk #3 amendment)

**Origin**: Reviewer item 13.
**Action**: NEW § 0.5 inserted into spec (see top of this document).

The boundary clarification governs:
- Which optimization-related amendments stay in C13 (none — they're
  all C14 territory)
- Which amendments get partial-reversed (A1 → B1, D11 → B2, A8 → B6)
- Which future amendments are blocked from C13 (per § 0.5.4
  governance gate)

This is the single most important architectural amendment of the
walk. Cache-relevant: yes (boundary affects what's in DoorPlacementResult
schema vs what's routed to C14).

---

### B11 — Typestate API: SuccessfulDoorPlacement vs FailedDoorPlacement

**Origin**: Reviewer item 15.
**Problem**: WARN mode collects failures into the batch result, but
downstream consumers can accidentally consume invalid candidates.
Reviewer suggests typestate discrimination.

**Amendment**: Replace generic `DoorPlacementResult` with a tagged
union:

```python
@dataclass(frozen=True)
class SuccessfulDoorPlacement:
    """v1 ships ONLY this from successful candidates."""
    source_placed_candidate_signature: str
    doors: tuple[Door, ...]
    advisory_flags: tuple[AdvisoryFlag, ...]
    geometric_fidelity_tier: int
    # ... other v0.2 fields ...

@dataclass(frozen=True)
class FailedDoorPlacement:
    """For WARN mode collection. CANNOT be misused as a successful result."""
    source_placed_candidate_signature: str
    failure_record: FailureRecord
    partial_doors: tuple[Door, ...]  # for debug only
    partial_advisory_flags: tuple[AdvisoryFlag, ...]

DoorPlacementOutcome = Union[SuccessfulDoorPlacement, FailedDoorPlacement]

@dataclass(frozen=True)
class DoorPlacementBatchResult:
    successful: tuple[SuccessfulDoorPlacement, ...]
    failed: tuple[FailedDoorPlacement, ...]
    # NO general "results" field that mixes them
    c13_version: str
    cache_key: str
```

Downstream consumers MUST explicitly pattern-match on the discriminated
union. Type checkers (mypy) reject access to `.doors` on a
`FailedDoorPlacement`.

Cache-relevant: yes (schema change).

---

### B12 — Adversarial-stacking PBT category

**Origin**: Reviewer item 16 (heuristic stacking).
**Problem**: v0.2 spec has 21 PBT floor (per v0.2 walk update) but
doesn't explicitly mandate adversarial integration testing for
heuristic-stacking pathologies.

**Amendment**: Add to § 8 test mandate:

> **Adversarial-stacking PBT category** (≥3 tests, mandatory at v1):
>
> Generate random compact layouts (n=3-8 rooms, envelope tightly
> fitting). Run full C13 pipeline. Assert:
>
> 1. Phase D iterations_used ≤ max_conflict_resolution_iterations
> 2. No oscillation (visited-state hashing prevents loops, but
>    PBT verifies)
> 3. No "regression" — re-running on identical input produces
>    identical output (Inv D7 byte-equal)
> 4. AdvisoryFlag counts are bounded (sanity check: ≤ n_rooms × 2)
> 5. Termination within budget for all generated inputs (no hangs)

PBT floor revised: **24** (was 21 in v0.2): 13 invariants + 3 failure
triggers + 5 adversarial + 3 adversarial-stacking.

Cache-relevant: no (test mandate).

---

## Updated invariants table (v0.3)

| ID | Statement | Source |
|---|---|---|
| D1 | Every PlacedRoom has ≥ min_doors doors, ≤ max_doors doors | v0.1, strengthened by B8 |
| D2 | Every door sits on a doorway_feasible SharedEdge | v0.1 |
| D3 | clear_width_m ≥ edge.min_required_clear_width_m | v0.1 |
| D4 | Door fits within edge | v0.1 |
| D5 | No two doors have overlapping swing arcs | v0.1 |
| D6 | Exactly one door has is_main_entry=True | v0.1 |
| D7 | Byte-equal replay across runs | v0.1, strengthened by A3 + A7 + B3 total-order tie-break |
| D8 | doors tuple sorted lex-ASC | v0.1 |
| D9' | Bathroom doors that swing outward don't conflict with adjacent traversal | v0.2 A6 |
| D10 | clear_width_m ≤ 1.5m (sanity bound) | v0.1 |
| **D11 REMOVED** | (was "no through-bedroom unless HARD hint" — replaced by AdvisoryFlag in B2) | v0.3 reversal |
| D12' | conflict_resolution_iterations_used ≤ max; loop-free; tie-break deterministic | v0.2 A4 + v0.3 B3 |
| D13 | Every PlacedRoom reachable from main entry via door-induced graph | v0.2 A9 |
| **D14 NEW** | geometric_fidelity_tier ∈ {1, 2, 3}, default 1 at v1 | v0.3 B4 |

13 → 12 invariants (D11 removed; D14 added; net -1).

---

## Updated § 12 backlog

### New backlog items from walk #3

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-C13-SEMANTIC-PRIORITY-RESIDENTIAL | Full living>kitchen>pooja>dining semantic ranking (reverted from v0.2 A8) | B6 partial reversal | When C14 ships AND production data shows production-quality complaints | M (v1.x or C14-side) |
| B-C13-PRIVACY-GRADIENT | Privacy-aware door selection | § 0.5.2 routing | When C14 privacy-gradient scoring lands | M (v1.x, C14-routed) |
| B-C13-AUTO-MULTI-DOOR | Heuristic-driven multi-door (no caller input needed) | B8 v1-scope | When production usage shows pattern of always-2-doors for specific room kinds | S-M (v1.x) |
| B-C13-LARGE-N-CSP-CONVERGENCE | Convergence guarantee for n > 15 rooms | B9 v1-scope-limit | When luxury/commercial scaling demands n>15 | L (v2+) |
| B-C13-FULL-3D-SWING-MODEL | Tier 3 fidelity: handle, door-stop, perpendicular truncation | B4 deferred | When user-facing 3D rendering needs accurate swing visualization | L (v2+) |

### Items reclassified from walk #2

| ID | v0.2 status | v0.3 status |
|---|---|---|
| B-C13-OCCUPANCY-TYPE-ABSTRACTION | v2+ | v2+ unchanged; v1 already-typology-agnostic via B6 |
| B-C13-FRAME-DEPTH-MODELING | v1.x | v1.x → upgraded to Tier 2 in B4 fidelity classification |
| B-C13-DOOR-CARDINALITY | v1.x | v0.3 SUPERSEDED by B8 (caller-specified) + B-C13-AUTO-MULTI-DOOR (heuristic) |

### Backlog summary table

**Total new items: 5. Net change (including supersession): +4 items.**

---

## Pushback items (NOT amended in v0.3)

**Walk #3 item 8 (Phase F should validate quality)**: PUSH BACK. Quality
scoring is C14's job per new § 0.5 boundary. Phase F explicitly stays
connectivity-only. Documented via B7.

**Walk #3 item 9 (cache key maintenance-heavy)**: PUSH BACK. Explicit
version constants are intentional. Trade-off: aggressive
invalidation > silent staleness. The reviewer's "semantic capability
hashes" is interesting but adds another abstraction layer. Documented
as a v0.3 § 6 addition:

> Cache key versioning is INTENTIONALLY explicit per amendment A10
> (v0.2). The trade-off accepts increased cache invalidation
> frequency in exchange for guaranteed staleness detection. A future
> "semantic capability hash" optimization is filed as
> `B-C13-SEMANTIC-CAPABILITY-CACHE` (v2+, low priority).

---

## Walk yield analysis

| Walk | Amendments | New backlog | Reversals | Notes |
|---|---|---|---|---|
| #2 | 10 | 5 | 0 | First external review of v0.1 |
| #3 | 12 | 5 | 3 (A1, D11, A8) | Boundary clarification surfaced |

Walk #3 is NOT diminishing-returns territory — it surfaced the C13/C14
boundary that walk #2 missed. This is a sign that **at least one more
external walk is recommended before LOCK candidacy**. C12 trajectory
was 10→8→2→2→1 across 5 walks; C13 is at 10→12, suggesting walks #4-5
will likely yield more (matching v0.2 self-analysis recommendation).

---

## Open questions resolved + new (v0.3)

**v0.2 Question 6 (C13 LOCK blocked on C12 v1.1?)**: PARTIALLY
RESOLVED via B5. C13 LOCKs against the C13ConsumesFromC12Edge Protocol,
not the raw C12 dataclass. C12 v1.1 amendment still needed, but C13
LOCK doesn't have to wait — C13 can ship with a Protocol-typed
adapter that initially uses the v1.0 schema fields + a stub for
edge_type that defaults to INTERNAL until C12 v1.1 ships the real
enum. **Recommend C13 LOCK can proceed in parallel with C12 v1.1
amendment.**

**NEW v0.3 Question 7**: § 0.5 explicit boundary means several
amendments effectively shift complexity to C14. C14 spec doesn't
exist yet. Should we draft C14 v0.1 BEFORE LOCKing C13 to validate
the boundary works? My recommendation: yes — a thin C14 v0.1 sketch
showing how AdvisoryFlags + weighted scoring fit on the C14 side
would prove the boundary holds. Otherwise C13 LOCK risks future
discovery that C14 can't actually receive what C13 emits.

**NEW v0.3 Question 8**: B8 introduces RoomDoorPreference as caller-
specified. Who is the "caller" in production? C11b? C12? Upstream
config? The v1 contract assumes caller-supplied; this should be
specified before LOCK.

**NEW v0.3 Question 9**: B11 typestate API breaks C12's pattern
(which uses a single PlacementBatchResult with separate
placed_candidates + failures fields). Should C12 be retroactively
amended to match B11's typestate pattern, or do we accept the
inconsistency? **My recommendation**: accept the inconsistency at
v1.0 (don't break LOCKED C12), but consider C12 v2.0 alignment in
the future.

---

## Self-analysis (Rule 11) for walk #3

Three concerns about THIS walk:

1. **B1/B2/B6 partial reversals admit walk #2 was over-amended.** This
   is intellectually honest but somewhat embarrassing for spec
   discipline. The lesson: external critiques BEFORE proposing
   amendments catches scope creep early. Walk #2 amendments were
   produced internally; walk #3 was the first external check on those
   amendments. Future C13 walks should ideally interleave external
   review more aggressively.

2. **B10 (§ 0.5 boundary statement) defers significant complexity to
   C14 which doesn't exist yet.** This is a technical-debt admission.
   Per v0.3 Question 7, recommend drafting C14 v0.1 sketch before
   C13 LOCK to validate the boundary works end-to-end.

3. **B11 typestate API is more aggressive than C12's pattern.** This
   creates an architectural inconsistency between C12 (mixed result
   schema) and C13 (typestate-discriminated schema). Could be
   intentional (we learned, we improved) or could indicate C12 needs
   retroactive alignment. Question 9 above.

---

Per Rule 8: vN PROPOSED. PENDING Ramalingam LOCK adjudication.

**Recommendation for next steps**:
- (a) Ramalingam direct feedback on B1-B12 amendments + § 0.5 boundary
- (b) Walk #4 (another external review of v0.3) BEFORE LOCK candidacy
- (c) Draft C14 v0.1 sketch to validate the § 0.5 boundary
- (d) Schedule C12 v1.1 amendment spec walk in parallel

My recommendation: (c) first (validate boundary), then (b) (one more
external walk), THEN consider LOCK. C13 LOCK in this session is
unlikely realistic given walk yields.
