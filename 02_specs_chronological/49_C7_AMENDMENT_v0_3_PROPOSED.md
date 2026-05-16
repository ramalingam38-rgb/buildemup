# C7 SPEC AMENDMENT v0.3 — WallSegment emission (B-212 resolution)

**Component**: 7 (Structural Grid Engine — already SHIPPED at v0.7.3)
**Amendment status**: v0.3 PROPOSED. **NOT LOCKED.** Supersedes v0.2 PROPOSED.
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 Walk #1 outcome (this amendment had only 1 walk; running second walk in parallel with C10 v0.5 per Ramalingam direction).
**Driver**: B-212 (C10 LOCK BLOCKER per S35 critique walk).

---

## § 0 — Summary of changes from v0.2 → v0.3

Walk #1 (self-audit at v0.2 § 8) raised 3 questions and 4 findings. v0.3 resolves them per the recommendations in v0.2, with adjustments where new evidence emerged:

| Item | v0.2 status | v0.3 resolution |
|---|---|---|
| Q-W1 (default to `()` vs required field) | Pending | **Default to `()`** — backwards-compat first; populated by `GridGenerator.generate`. Existing test fixtures stay valid. |
| Q-W2 (internal partition walls v1) | Pending | **Externals only in v1**. Internal partitions = placement-time artifacts (C11 territory). Tag `INTERNAL` exists for forward-compat. |
| Q-W3 (column-segment cross-references) | Pending | **Not v1**. C12 (Vertical Alignment) needs this; defer until C12 spec exists. WallSegment carries no column-list field. |
| F-W1 (SHIPPED component amendment process) | Pending | **Treated as additive amendment.** Field is new + defaults to backwards-compat empty tuple. No deprecation cycle. Documented as the precedent for future SHIPPED-component amendments per Pattern A discipline (no band-aid fixes; modify at the source). |
| F-W2 (C8 corridor-vs-wall validation) | NO ACTION at v0.2 | **Confirmed NO ACTION at v0.3.** C8 sees `wall_segments` as opaque pass-through. Future C8 enhancement is separate work. |
| F-W3 (polygonal forward-compat) | NO ACTION at v0.2 | **Confirmed NO ACTION.** v1 schema accommodates polygons via `axis` enum extension or polygon-edge-index addition. Not locked into rectangular. |
| F-W4 (CCW from south vs CW from north convention) | Pending | **CCW from south retained** with explicit documentation. Web search confirmed no firm industry standard for cardinal-wall ordering in code; documentation matters more than direction. C9/C10 already treat the wall set as set-membership rather than ordered list, so the choice is internal-only. |

---

## § 1 — Output schema (REVISED v0.3)

```python
class WallAxis(str, Enum):
    """Cardinal wall axes for v1 rectangular envelope.
    Polygonal envelopes (post B-066) will extend or add polygon-edge-index.
    """
    NORTH = "north"   # y == envelope_depth_m
    SOUTH = "south"   # y == 0
    EAST  = "east"    # x == envelope_width_m
    WEST  = "west"    # x == 0


class WallTag(str, Enum):
    EXTERNAL      = "external"        # perimeter wall (v1 = all walls)
    INTERNAL      = "internal"        # interior partition (post-v1; tag exists for forward-compat)
    LOAD_BEARING  = "load_bearing"    # carries vertical load (v1 perimeter walls + columns)


@dataclass(frozen=True)
class WallSegment:
    """One wall segment of the buildable envelope.

    v1 (rectangular plot per B-066): exactly 4 wall segments, one per cardinal
    direction. Every segment is EXTERNAL and LOAD_BEARING.

    Forward-compatibility:
      - Polygonal envelopes (post B-066) extend WallAxis or add polygon edge index.
      - Internal partition walls populate when C11 placement emits them; v1 emits none.
    """
    wall_id: str                # stable v1: "WALL_NORTH" / "WALL_SOUTH" / "WALL_EAST" / "WALL_WEST"
    axis: WallAxis
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float
    length_m: float
    tags: frozenset[WallTag]

    def __post_init__(self):
        # Invariant W1: length_m matches Euclidean(start, end)
        from math import hypot
        dx = self.end_x_m - self.start_x_m
        dy = self.end_y_m - self.start_y_m
        if abs(self.length_m - hypot(dx, dy)) > 1e-6:
            raise ValueError(
                f"WallSegment {self.wall_id}: length_m ({self.length_m}) "
                f"does not match geometry ({hypot(dx, dy):.6f})"
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
                f"WallSegment {self.wall_id}: v1 walls must be axis-aligned; "
                f"got dx={dx:.6f}, dy={dy:.6f}"
            )
```

**Updated `Grid` dataclass** (additive change only — backwards compatible per Q-W1):

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
    # NEW v0.3 (formerly v0.2):
    wall_segments: tuple[WallSegment, ...] = ()

    def wall_segment_by_id(self, wall_id: str) -> WallSegment:
        for w in self.wall_segments:
            if w.wall_id == wall_id:
                return w
        raise KeyError(f"Grid has no wall_segment with wall_id={wall_id!r}")
```

---

## § 2 — Behaviour

`GridGenerator.generate(envelope_width_m, envelope_depth_m)` populates `wall_segments` with exactly 4 segments for v1 rectangular envelope.

**Wall ordering: counter-clockwise starting from SOUTH** (documented choice per F-W4 resolution; no firm industry convention exists per web search):

| wall_id | axis | start | end | length_m | tags |
|---|---|---|---|---|---|
| `WALL_SOUTH` | SOUTH | (0, 0) | (W, 0) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_EAST` | EAST | (W, 0) | (W, D) | D | {EXTERNAL, LOAD_BEARING} |
| `WALL_NORTH` | NORTH | (W, D) | (0, D) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_WEST` | WEST | (0, D) | (0, 0) | D | {EXTERNAL, LOAD_BEARING} |

W = `envelope_width_m`, D = `envelope_depth_m`. All wall_ids treated as set members downstream (C9/C10 don't depend on order).

---

## § 3 — Invariants (unchanged from v0.2 — W1-W7)

| # | Invariant | Mode |
|---|---|---|
| W1 | `length_m` matches Euclidean(start, end) | RAISE |
| W2 | Every WallSegment has at least one WallTag | RAISE |
| W3 | v1 walls are axis-aligned | RAISE |
| W4 | v1 Grid has exactly 4 wall_segments | RAISE |
| W5 | Each WallAxis (N/S/E/W) appears exactly once | RAISE |
| W6 | wall_ids unique within Grid | RAISE |
| W7 | Total wall length == envelope perimeter (`2W + 2D`) | RAISE |

---

## § 4 — Test coverage requirements

Per D-066 build cycle:
- 4 wall-segment construction tests (W1-W7 invariants + happy path)
- 2 lookup tests (`wall_segment_by_id` happy + KeyError)
- 1 backwards-compat test confirming all existing 174 C7 tests still pass
- 2 ordering tests (CCW-from-south convention verified for both square + rectangular envelopes)

**Target**: ~9 new tests, no regressions on existing 174 C7 tests. Cumulative target post-amendment ship: 2155 + 9 ≈ 2164 passed. (C10 v0.5 build adds ~135 more later.)

---

## § 5 — Failure modes (unchanged from v0.2)

```
ValueError      — invariant violations W1-W7
KeyError        — wall_segment_by_id with unknown id
```

No new exception classes; uses existing C7 error hierarchy.

---

## § 6 — Open questions surfaced at v0.3 (NEW second walk)

**Q-W4**: Should `WallSegment` carry a `wall_thickness_m: float | None` field for forward-compat with C12 vertical alignment / future-rendering? C9 already has `wall_thickness_ratio` config; that's a property of the *envelope*, not the wall.
- **Recommendation**: NO. Wall thickness is C11/C12/C16 placement-and-rendering territory. Centerline geometry only at v1.

**Q-W5**: When `Grid.wall_segments` is the default empty tuple `()` (e.g. in a hand-built test fixture), should `Grid.__post_init__` warn? C9 v1 already silently uses uniform-bay assumption per D3 fix. Warn-on-empty would help catch consumers that forget to populate it.
- **Recommendation**: NO warn at v0.3. Hand-built fixtures intentionally use `()`. Production path always populates via `GridGenerator.generate`. Adding a warn would create noise in C9's existing 1988+ tests.

**Q-W6**: Should the wall-ordering convention (CCW from south) be exposed via class-level docstring AND a module-level constant `WALL_ORDER_CONVENTION = "CCW_FROM_SOUTH"` for downstream consumers to reference?
- **Recommendation**: YES. Document as constant. Cheap; protects against drift.

---

## § 7 — Rule 11 spec audit on v0.3 PROPOSED

Per Rule 11 (LOCKED at S34), proactive audit before requesting LOCK.

**PATCH-NOW (in v0.3 itself): 0** — drafting is the patch round.

**OPEN QUESTIONS surfaced**: Q-W4, Q-W5, Q-W6 above.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v3-W1 | The `wall_segment_by_id` method is O(N) linear search. With v1's 4 walls this is irrelevant; with B-066 polygonal envelopes (10s of walls) it could become hot in C10's per-room iteration. | **NO ACTION at v1** — premature optimization for 4-element lookup. File as B-231 for B-066 era. |
| F-v3-W2 | The schema mixes "geometry" (start/end XY, length) with "semantic tags" (WallTag set) in one frozen dataclass. C11 placement may want to update tags (e.g., reclassify a wall as LOAD_BEARING after structural analysis) but the dataclass is frozen. | **NEEDS WALK** — either accept frozen-and-replace pattern (caller constructs new WallSegment with updated tags) or split into geometry+semantics. Recommend frozen-and-replace; matches C9 dataclass discipline. |
| F-v3-W3 | Backwards-compat default `wall_segments: tuple[...] = ()` means a Grid built without GridGenerator (e.g. in an old test) silently has no walls. C10 receives empty tuple, falls through to "no eligible walls" → infeasibility. The error surfaces at C10 not at C7. | **NEEDS WALK** — accept (mirrors how C9 handles uniform-bay assumption silently) OR add Grid validation. Recommend status quo for backwards-compat; C10 will surface the issue with a clear error message ("Grid has no wall_segments — was Grid.generate() bypassed?"). |
| F-v3-W4 | The `tags: frozenset[WallTag]` is `frozenset` not `tuple`. Frozenset is correct for set-semantics but doesn't preserve insertion order — affects deterministic provenance trace ordering. | **MINOR** — when serialising tags to provenance, sort by enum value: `tuple(sorted(tags, key=lambda t: t.value))`. Document in v0.4. |
| F-v3-W5 | The amendment doesn't specify how `WALL_ORDER_CONVENTION` interacts with project-north vs true-north (per architectural drawing conventions). If project-north differs from true-north, "WALL_NORTH" might be the wall facing project-north or true-north. | **NEEDS WALK** — pick one. Web evidence suggests project-north is typical for floor plan conventions. Recommend: `WallAxis.NORTH` = project-north (consistent with how the Grid envelope is defined). True-north for Vastu/orientation handled by C6 OrientedCandidate. Document in § 2. |

**REJECTED-AS-CONSIDERED**:
- "Add a `wall_corner_id` separate from `wall_id` for the 4 corners?" — No. Corners are derivable as `(wall.start_x_m, wall.start_y_m)` intersections. Not needed.
- "Emit `Grid.perimeter_m` as a derived property?" — Not blocked, can add as `@property` if any downstream consumer asks. Not in v0.3 scope.
- "Add an `EXTERIOR_FACADE` tag distinct from `EXTERNAL` for entry-side walls?" — Out of scope. Entry-side semantics live in C2/C4 plot analysis.

**Audit summary**: 0 patch-now, 5 walk findings, 3 rejected. Audit ran; not performative.

---

## § 8 — Status

- **v0.3 PROPOSED**. **NOT LOCKED.**
- 3 v0.3 walk-2 questions Q-W4, Q-W5, Q-W6 to adjudicate.
- 5 spec-audit findings F-v3-W1 through F-v3-W5 to resolve.
- Estimated walks to LOCK: **1 more.** This amendment is small enough that v0.4 should be lockable.

---

**End of v0.3 PROPOSED.** Awaits Ramalingam's reading.
