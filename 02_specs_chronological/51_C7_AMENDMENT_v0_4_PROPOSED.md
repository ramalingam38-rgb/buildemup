# C7 SPEC AMENDMENT v0.4 PROPOSED — WallSegment emission (B-212 resolution)

**Component**: 7 (Structural Grid Engine — already SHIPPED at v0.7.3)
**Amendment status**: v0.4 PROPOSED. **NOT LOCKED.** Supersedes v0.3 PROPOSED. **Likely LOCK candidate.**
**Authority**: S35 author's draft. PROPOSED, pending Ramalingam adjudication.
**Authored**: S35 Walk #5 outcome.
**Driver**: B-212 (C10 LOCK BLOCKER).

---

## § 0 — Summary of changes from v0.3 → v0.4

Walk #2 (v0.3 self-audit + reviewer items 19-28) raised 3 questions and 5 findings plus 2 new genuine catches. v0.4 resolves all per recommendations adopted in Walk #5:

| Item | v0.3 status | v0.4 resolution |
|---|---|---|
| Q-W4 (wall_thickness in WallSegment) | Pending | **NO**. Defer to C12 / C16 rendering. Centerline geometry only at v1. |
| Q-W5 (warn on empty wall_segments) | Pending | **NO**. Hand-built fixtures legitimately use `()`. C10 will surface the issue with a clear error message. |
| Q-W6 (`WALL_ORDER_CONVENTION` constant) | Pending | **YES**. Module-level constant exposed. |
| F-v3-W1 (linear lookup scaling) | NEEDS WALK | **NO ACTION at v1** — premature optimization for 4-element lookup. **B-231** files for B-066 polygonal era. |
| F-v3-W2 (frozen WallSegment for tag updates) | NEEDS WALK | **Frozen-and-replace** pattern adopted; matches C9 dataclass discipline. Documented in § 6. |
| F-v3-W3 (empty default hides upstream failures) | NEEDS WALK | **Status quo retained**; document expected error path: empty `wall_segments` → C10 surfaces `WetZoneInfeasibleError("Grid has no wall_segments — was Grid.generate() bypassed?")`. |
| F-v3-W4 (frozenset serialisation) | MINOR | **`serialize_tags_sorted()` helper** centralized in C7 module — sorts by enum value before tuple-conversion for deterministic provenance. |
| F-v3-W5 (project-north vs true-north) | NEEDS WALK | **`WallAxis.NORTH` = project-north**. True-north handled by C6 OrientedCandidate. Documented in § 2. |
| **NEW Walk #5 #27 (WallTag domain split)** | — | **B-235** filed for v2 when 5+ tags exist. v1's 3-tag flat frozenset is acceptable. |
| **NEW Walk #5 #28 (downstream order-dependence)** | — | **NEW Invariant W8**: downstream consumers must treat wall_segments as set-membership; ordering is for canonical serialisation only. Test plan adds shuffle-order regression test. |

---

## § 1 — Output schema (REVISED v0.4 — minor additions)

```python
WALL_ORDER_CONVENTION: Final[str] = "CCW_FROM_SOUTH"
"""Module constant per Q-W6. Wall ordering convention exposed for downstream
inspection and replay-test assertion. Counter-clockwise starting from SOUTH.
No firm industry standard exists per S35 web research; documentation matters
more than direction.
"""


class WallAxis(str, Enum):
    """Cardinal wall axes for v1 rectangular envelope.

    `NORTH` here means PROJECT-NORTH — the +y direction of the envelope
    coordinate system as defined by C7's GridGenerator. TRUE-NORTH (the actual
    geographic compass direction) is handled by C6 OrientedCandidate; C7 does
    not perform any project-to-true rotation. (Per F-v3-W5 resolution.)

    Polygonal envelopes (post B-066) extend or supersede this enum.
    """
    NORTH = "north"
    SOUTH = "south"
    EAST  = "east"
    WEST  = "west"


class WallTag(str, Enum):
    """v1 tags. Domain split (topology / structural / placement) deferred to
    v2 per B-235 when 5+ tags arrive (e.g. FIRE_RATED, ACOUSTIC_SEAL).
    """
    EXTERNAL      = "external"
    INTERNAL      = "internal"
    LOAD_BEARING  = "load_bearing"


@dataclass(frozen=True)
class WallSegment:
    """One wall segment of the buildable envelope.

    v1: rectangular plot per B-066 → exactly 4 wall segments, all EXTERNAL +
    LOAD_BEARING. Frozen — all updates produce a new instance (frozen-and-
    replace pattern matching C9 discipline; reviewer Walk #5 #20).

    Forward-compat:
      - Polygonal envelopes (B-066) add WallAxis values or polygon edge index.
      - Internal partition walls (B-217) emit when C11 placement creates them.
    """
    wall_id: str
    axis: WallAxis
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float
    length_m: float
    tags: frozenset[WallTag]

    def __post_init__(self):
        from math import hypot
        dx = self.end_x_m - self.start_x_m
        dy = self.end_y_m - self.start_y_m
        # Invariant W1
        if abs(self.length_m - hypot(dx, dy)) > 1e-6:
            raise ValueError(
                f"WallSegment {self.wall_id}: length_m ({self.length_m}) "
                f"does not match geometry ({hypot(dx, dy):.6f})"
            )
        # Invariant W2
        if not self.tags:
            raise ValueError(f"WallSegment {self.wall_id}: tags must be non-empty")
        # Invariant W3 (v1 axis-aligned)
        if abs(dx) > 1e-6 and abs(dy) > 1e-6:
            raise ValueError(
                f"WallSegment {self.wall_id}: v1 walls must be axis-aligned; "
                f"got dx={dx:.6f}, dy={dy:.6f}"
            )


def serialize_tags_sorted(tags: frozenset[WallTag]) -> tuple[str, ...]:
    """Centralized tag serialisation per F-v3-W4. Returns tuple sorted by enum
    value for deterministic provenance and replay snapshots. Use this in any
    rule_trace string or snapshot output instead of iterating frozenset directly.
    """
    return tuple(sorted((t.value for t in tags)))
```

**Updated `Grid` dataclass** (additive, backwards-compatible):

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
    wall_segments: tuple[WallSegment, ...] = ()    # v0.2 addition

    def wall_segment_by_id(self, wall_id: str) -> WallSegment:
        for w in self.wall_segments:    # O(N); B-231 tracks polygonal optimisation
            if w.wall_id == wall_id:
                return w
        raise KeyError(f"Grid has no wall_segment with wall_id={wall_id!r}")
```

---

## § 2 — Behaviour

`GridGenerator.generate(envelope_width_m, envelope_depth_m)` populates `wall_segments` with exactly 4 segments for v1 rectangular envelope.

**Wall ordering: counter-clockwise from SOUTH** (`WALL_ORDER_CONVENTION = "CCW_FROM_SOUTH"` exposed as module constant). Choice is project-internal; downstream consumers MUST treat as set-membership per Inv W8.

| wall_id | axis | start | end | length_m | tags |
|---|---|---|---|---|---|
| `WALL_SOUTH` | SOUTH | (0, 0) | (W, 0) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_EAST` | EAST | (W, 0) | (W, D) | D | {EXTERNAL, LOAD_BEARING} |
| `WALL_NORTH` | NORTH | (W, D) | (0, D) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_WEST` | WEST | (0, D) | (0, 0) | D | {EXTERNAL, LOAD_BEARING} |

`NORTH` here is **project-north** = +y direction of the envelope coordinate system. True-north (geographic compass) lives in C6 OrientedCandidate; C7 does not rotate. Critical for Vastu and orientation-aware logic downstream.

---

## § 3 — Invariants (REVISED v0.4 — added W8)

| # | Invariant | Mode |
|---|---|---|
| W1 | `length_m` matches Euclidean(start, end) | RAISE |
| W2 | Every WallSegment has at least one WallTag | RAISE |
| W3 | v1 walls are axis-aligned | RAISE |
| W4 | v1 Grid has exactly 4 wall_segments | RAISE |
| W5 | Each WallAxis (N/S/E/W) appears exactly once | RAISE |
| W6 | wall_ids unique within Grid | RAISE |
| W7 | Total wall length == envelope perimeter (`2W + 2D`) | RAISE |
| **W8 (NEW v0.4)** | **Downstream consumers must treat `wall_segments` as set-membership; algorithms must produce identical output regardless of tuple iteration order.** Verified by **shuffle-order regression test**: same Grid with `wall_segments` in different tuple orders produces byte-identical downstream output. | TEST-LEVEL (no runtime check; enforced via test discipline) |

---

## § 4 — Test coverage requirements

Per D-066 build cycle:
- 4 wall-segment construction tests (W1-W7 + happy path)
- 2 lookup tests (`wall_segment_by_id` happy + KeyError)
- 1 backwards-compat test (existing 174 C7 tests pass with new `wall_segments=()` default)
- 2 ordering tests (CCW-from-south convention verified for square + rectangular envelopes)
- 1 module constant test (`WALL_ORDER_CONVENTION == "CCW_FROM_SOUTH"`)
- 1 `serialize_tags_sorted` helper test
- 2 W8 shuffle-order regression tests (Grid built with shuffled tuple → C9 + C10 produce identical output)

**Target**: ~13 new tests, no regressions on existing 174 C7 tests. Cumulative target post-amendment ship: 2155 + 13 ≈ 2168 passed.

---

## § 5 — Failure modes (unchanged)

```
ValueError      — invariant violations W1-W7
KeyError        — wall_segment_by_id with unknown id
```

W8 enforced at test level only; no runtime check.

---

## § 6 — Frozen-and-replace pattern (NEW v0.4 documentation)

Per F-v3-W2 + reviewer Walk #5 #20: `WallSegment` is frozen. To update tags or any field, callers construct a new `WallSegment` with the desired values rather than mutating in place. This is the standard discipline across all C9 dataclasses.

Example:
```python
# Adding ACOUSTIC_SEAL tag (post-v2):
old_wall = grid.wall_segment_by_id("WALL_NORTH")
new_wall = dataclasses.replace(old_wall, tags=old_wall.tags | {WallTag.ACOUSTIC_SEAL})
new_grid = dataclasses.replace(grid, wall_segments=tuple(
    new_wall if w.wall_id == "WALL_NORTH" else w for w in grid.wall_segments
))
```

Tradeoff: O(N) replacement is fine at v1 (N=4). Polygonal envelopes (post-B-066) with many walls may benefit from batch-replace helpers — track via B-231.

---

## § 7 — Open backlog

| ID | Description | Trigger |
|---|---|---|
| B-231 | Wall lookup O(1) optimisation for polygonal envelopes (precomputed dict) | Post B-066 |
| B-235 | WallTag domain split (topology / structural / placement) | When 5+ tags exist |

---

## § 8 — Rule 11 spec audit on v0.4 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.4 itself): 0** — drafting is the patch round.

**OPEN QUESTIONS surfaced**: 0. All v0.3 questions resolved.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v4-W1 | W8 is "TEST-LEVEL" only — no runtime check. If a future C-component subtly depends on order (e.g. iterating `for w in grid.wall_segments[:2]` for "first two walls"), the test catches the regression but only at integration level. | **NEEDS WALK** — accept the test-level discipline (matches Python convention for design constraints) OR add a debug-mode runtime check that shuffles every Nth call. Recommend test-level only; debug shuffle is over-engineering for v1. |
| F-v4-W2 | `serialize_tags_sorted` returns `tuple[str, ...]`. Why not return `frozenset[str]` for true set-semantics? Because frozenset iteration is not ordered. Tuple is right; document why. | **MINOR** — add docstring note explaining tuple choice for deterministic ordering. |
| F-v4-W3 | The `dataclasses.replace` example in § 6 uses an inline tuple comprehension — clean Python but shifts the burden to every caller. Worth a `Grid.update_wall(wall_id, **fields)` convenience method? | **NO at v1** — over-engineering. Document the pattern; if 3+ call sites need it, refactor then. |
| F-v4-W4 | Test count target says 13 new tests. Counting: 4 + 2 + 1 + 2 + 1 + 1 + 2 = 13. Math correct. | **PASS** — first time v0.x test math has actually checked out. |
| F-v4-W5 | The `WALL_ORDER_CONVENTION = "CCW_FROM_SOUTH"` constant is a string. Should it be an enum value (`WallOrderConvention.CCW_FROM_SOUTH`) for type-safety? | **NO at v1** — single value, no other conventions in v1. Refactor to enum if v2 introduces alternate orderings. |

**REJECTED-AS-CONSIDERED**:
- "Add `wall_corners: tuple[tuple[float, float], ...]` for explicit corner geometry?" — No. Derivable from `(start_x_m, start_y_m)` of consecutive walls.
- "Add `Grid.perimeter_m` derived property?" — Not blocked; add as `@property` only when downstream consumer needs it.
- "Add `is_convex_envelope: bool` flag for forward-compat polygonal?" — Premature. v1 is rectangular; B-066 era will introduce shape classification.

**Audit summary**: 0 patch-now, 5 walk findings (4 NO/MINOR, 1 needs walk decision), 3 rejected. **F-v4-W1 is the only one needing your call.** Recommendation: test-level only (status quo). Audit ran; not performative.

---

## § 9 — Status

- **v0.4 PROPOSED**. **NOT LOCKED.** **Likely LOCK candidate after F-v4-W1 adjudication.**
- 1 walk finding open (F-v4-W1 — recommend test-level only).
- 0 open questions.
- All v0.3 walk items + Walk #5 reviewer items resolved.
- Estimated walks to LOCK: **0-1**. v0.5 likely just absorbs F-v4-W1 verdict and locks.

---

**End of v0.4 PROPOSED.** Awaits Ramalingam's reading + F-v4-W1 verdict for LOCK.
