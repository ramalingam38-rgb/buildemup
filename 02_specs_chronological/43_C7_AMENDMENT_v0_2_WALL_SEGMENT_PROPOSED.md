# C7 SPEC AMENDMENT v0.2 — WallSegment emission (B-212 resolution)

**Component**: 7 (Structural Grid Engine — already SHIPPED at v0.7.3)
**Amendment status**: v0.2 PROPOSED. **NOT LOCKED.**
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 Walk #1 outcome.
**Predecessor**: C7 SHIPPED v0.7.3 (Apr 22-23, Track 2 era).
**Driver**: B-212 (C10 LOCK BLOCKER per S35 critique walk).

---

## § 0 — Why this exists

C10 (Wet-Zone Stack Planner) needs a stable, canonical representation of "wall segments" — the surfaces of the buildable envelope that wet rooms attach to. Critique walk #1 verified by grep: **no `WallSegment` / `wall_id` exists anywhere in C7 or C8.** C10 cannot emit `wet_wall_assignment: dict[room_id, WallSegmentID]` without a stable upstream identifier.

Three options were considered:
- **(a) C7 emits walls** — walls are structural; the grid generates the perimeter as a side-effect of envelope geometry.
- (b) C8 emits walls — corridor envelopes carry edge geometry already.
- (c) C10 derives walls internally — doubles the work; C11/C12 would re-derive.

Ramalingam adjudicated **(a) C7**. Walls are structural primitives, the grid is structural, dependency direction is cleanest (C7 → C8 → C9 → C10 → C11 → C12).

---

## § 1 — Scope of this amendment

C7's existing contract is preserved. This amendment adds:

1. New `WallSegment` dataclass.
2. New `Grid.wall_segments: tuple[WallSegment, ...]` field.
3. New `Grid.wall_segment_by_id(wall_id: str) -> WallSegment` lookup.
4. Validation invariants on the wall-segment set.

**No changes** to existing fields (`columns`, `bay_x_m`, `bay_y_m`, `envelope_width_m`, `envelope_depth_m`). Backwards-compatible: every existing C7 call site continues to work; new field is additive.

---

## § 2 — Output schema (NEW)

```python
class WallAxis(str, Enum):
    NORTH = "north"   # y == envelope_depth_m
    SOUTH = "south"   # y == 0
    EAST  = "east"    # x == envelope_width_m
    WEST  = "west"    # x == 0


class WallTag(str, Enum):
    EXTERNAL      = "external"        # perimeter wall
    INTERNAL      = "internal"        # interior partition (not v1)
    LOAD_BEARING  = "load_bearing"    # carries vertical load (perimeter walls + columns)


@dataclass(frozen=True)
class WallSegment:
    """One wall segment of the buildable envelope.

    v1 (rectangular plot per B-066): exactly 4 wall segments, one per cardinal
    direction. Every segment is EXTERNAL and (for now) LOAD_BEARING.
    Future versions (post B-066) will emit polygonal wall sets and internal
    partition walls.
    """
    wall_id: str                # stable: "WALL_NORTH" / "WALL_SOUTH" / "WALL_EAST" / "WALL_WEST" in v1
    axis: WallAxis
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float
    length_m: float             # invariant: matches Euclidean(start, end)
    tags: frozenset[WallTag]

    def __post_init__(self):
        # Invariant W1: length_m matches geometry
        dx = self.end_x_m - self.start_x_m
        dy = self.end_y_m - self.start_y_m
        from math import hypot
        if abs(self.length_m - hypot(dx, dy)) > 1e-6:
            raise ValueError(
                f"WallSegment {self.wall_id}: length_m ({self.length_m}) "
                f"does not match geometry ({hypot(dx, dy)})"
            )
        # Invariant W2: every wall has at least one tag
        if not self.tags:
            raise ValueError(
                f"WallSegment {self.wall_id}: tags must be non-empty"
            )
        # Invariant W3: v1 walls are axis-aligned (orthogonal). Diagonal walls
        # come post B-066.
        if abs(dx) > 1e-6 and abs(dy) > 1e-6:
            raise ValueError(
                f"WallSegment {self.wall_id}: v1 walls must be axis-aligned "
                f"(orthogonal); got dx={dx}, dy={dy}"
            )
```

**Updated `Grid` dataclass** (additive change only):

```python
@dataclass(frozen=True)
class Grid:
    columns: list[ColumnPosition]
    bay_x_m: float
    bay_y_m: float
    columns_x_count: int
    columns_y_count: int
    envelope_width_m: float
    envelope_depth_m: float
    # NEW v0.2:
    wall_segments: tuple[WallSegment, ...] = ()

    def __post_init__(self):
        # Existing validations preserved.
        # NEW v0.2 validations:
        # Invariant W4: v1 must have exactly 4 wall segments (rectangular plot)
        # Invariant W5: every cardinal axis present exactly once
        # Invariant W6: wall_ids unique
        ...

    def wall_segment_by_id(self, wall_id: str) -> WallSegment:
        for w in self.wall_segments:
            if w.wall_id == wall_id:
                return w
        raise KeyError(f"Grid has no wall_segment with wall_id={wall_id!r}")
```

---

## § 3 — Behaviour

`GridGenerator.generate(envelope_width_m, envelope_depth_m)` populates `wall_segments` with exactly 4 segments for v1 rectangular envelope:

| wall_id | axis | start | end | length_m | tags |
|---|---|---|---|---|---|
| `WALL_SOUTH` | SOUTH | (0, 0) | (W, 0) | W | EXTERNAL, LOAD_BEARING |
| `WALL_EAST` | EAST | (W, 0) | (W, D) | D | EXTERNAL, LOAD_BEARING |
| `WALL_NORTH` | NORTH | (W, D) | (0, D) | W | EXTERNAL, LOAD_BEARING |
| `WALL_WEST` | WEST | (0, D) | (0, 0) | D | EXTERNAL, LOAD_BEARING |

W = `envelope_width_m`, D = `envelope_depth_m`. Counter-clockwise ordering (south → east → north → west) for orientation consistency with downstream consumers.

---

## § 4 — Invariants

| # | Invariant | Mode |
|---|---|---|
| W1 | `length_m` matches Euclidean distance between start and end | RAISE |
| W2 | Every WallSegment has at least one WallTag | RAISE |
| W3 | v1 walls are axis-aligned (orthogonal) | RAISE |
| W4 | v1 Grid has exactly 4 wall_segments | RAISE |
| W5 | Each WallAxis (N/S/E/W) appears exactly once | RAISE |
| W6 | wall_ids unique within Grid | RAISE |
| W7 | Total wall length == envelope perimeter (`2W + 2D`) | RAISE |

---

## § 5 — Test coverage requirements

Per D-066 build cycle:

- 4 wall-segment tests covering invariants W1-W7
- 2 lookup tests (`wall_segment_by_id` happy + KeyError)
- 1 backward-compat test confirming all existing 174 C7 tests still pass

**Target**: ~7 new tests, no regressions on existing 174 C7 tests.

---

## § 6 — Failure modes

```
ValueError      — invariant violations W1-W7
KeyError        — wall_segment_by_id with unknown id
```

No new exception classes; uses existing C7 error hierarchy.

---

## § 7 — Open questions for walks

**Q-W1**: Should `Grid.wall_segments` default to `()` for backwards-compat, or be required (forcing every call site to update)?
- **Recommendation**: default to `()`, populate in `GridGenerator.generate`. Existing test fixtures that build Grid by hand stay valid; production path always populates.

**Q-W2**: Do internal partition walls also belong here (interior wall between two rooms), or are those generated by C11 placement?
- **Recommendation**: v1 = external only. Internal partitions are placement-time artifacts (C11). Tag exists for forward-compat.

**Q-W3**: Should walls carry references to which structural columns they pass over?
- **Recommendation**: not v1. C12 (Vertical Alignment) will need this; defer until C12 spec.

---

## § 8 — Rule 11 spec audit on this amendment

PATCH-NOW (in this DRAFT itself): 0.

OPEN QUESTIONS surfaced:
- Q-W1, Q-W2, Q-W3 above.

SPEC-AUDIT FINDINGS:

| # | Finding | Verdict |
|---|---|---|
| F-W1 | C7 SHIPPED is in Track 2 (the original v0.7.3 build), pre-dating Track 3 disciplines (D-066 build cycle, Rule 11). Adding fields to a SHIPPED component is unusual — does this require a deprecation cycle? | **NEEDS WALK** — recommend treating as additive amendment (no deprecation needed since field is new + defaults to backwards-compat empty tuple). |
| F-W2 | C8 (Corridor Designer) consumes Grid but doesn't currently use wall geometry. Adding `wall_segments` to Grid doesn't break C8's contract, but C8 might want to validate corridor envelopes against walls eventually. | **NO ACTION at v0.2** — C8 enhancement is separate work. C8 sees new field as opaque pass-through. |
| F-W3 | Future polygonal envelopes (post B-066) will need more than 4 walls. The `WallSegment` schema accommodates this (via `axis` extending to a Polygon-edge enum, or via leaving `axis` only for cardinal v1 and adding edge-index for polygons). v1 schema doesn't lock anything bad. | **NO ACTION at v0.2** — design is forward-compatible. |
| F-W4 | "Counter-clockwise from SOUTH" is a convention; what if downstream expects clockwise from NORTH (common architectural convention)? | **NEEDS WALK** — pick one and document. |

REJECTED-AS-CONSIDERED:
- "Should walls have a thickness parameter?" — No. Wall thickness is a placement-time decision; C9 already has `wall_thickness_ratio` config for envelope-axis sizing. Wall geometry here is centerline.

**Audit summary**: 0 patch-now, 4 walk findings, 1 rejected. Audit ran; not performative.

---

## § 9 — Status

- v0.2 PROPOSED. **NOT LOCKED.**
- Awaits Ramalingam's first reading.
- Walks needed before LOCK (estimate 2-3, simpler than C9's 7-walk arc since this is additive).
- C10 LOCK is BLOCKED on this LOCK landing.

---

**End of v0.2 PROPOSED.** Awaits adjudication on Q-W1, Q-W2, Q-W3, F-W1, F-W4.
