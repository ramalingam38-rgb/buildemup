# C7 SPEC AMENDMENT v0.6 PROPOSED — WallSegment emission (B-212 resolution)

**Component**: 7 (Structural Grid Engine — already SHIPPED at v0.7.3)
**Amendment status**: **v0.6 PROPOSED.** Supersedes v0.5 LOCK CANDIDATE. **NOT LOCKED** per Ramalingam directive.
**Authority**: S35 author's draft. PROPOSED, awaiting Ramalingam adjudication.
**Authored**: S35 Walk #7 outcome.
**Driver**: B-212 (C10 LOCK BLOCKER) + Walk #7 #1 canonical accessor sharpening.

---

## § 0 — Summary of changes from v0.5 → v0.6

Walk #7 reviewer #1 surfaced a real architectural sharpening of W8: rather than enforcing W8 only at test level, expose a canonical-iteration API that production code can use unconditionally. This **moves W8 from "test discipline" to "architectural API enforcement"** — without runtime overhead.

| Item | v0.5 status | v0.6 resolution |
|---|---|---|
| W8 enforcement scope | Test-level only (per F-v4-W1 prior verdict) | **Canonical accessor** added (`Grid.iter_wall_segments_canonical()`); production code uses accessor; direct iteration over `wall_segments` reserved for canonical-serialisation snapshots. Test-level shuffle regression continues to verify the canonical-accessor path produces consistent output. |
| Walk #7 #1 (canonical accessor + assertion helper) | NEW | Both added to C7 module surface. |

All other v0.5 items remain unchanged. **No schema field changes from v0.5; only new method + helper.**

---

## § 1 — Output schema (REVISED v0.6 — additive method + module helper)

```python
WALL_ORDER_CONVENTION: Final[str] = "CCW_FROM_SOUTH"


class WallAxis(str, Enum):
    """`NORTH` = PROJECT-NORTH (+y of envelope coord system).
    True-north handled by C6 OrientedCandidate.
    """
    NORTH = "north"
    SOUTH = "south"
    EAST  = "east"
    WEST  = "west"


# NEW v0.6 (Walk #7 #1) — canonical iteration order for production code:
WALL_AXIS_CANONICAL_ORDER: Final[tuple[WallAxis, ...]] = (
    WallAxis.SOUTH, WallAxis.EAST, WallAxis.NORTH, WallAxis.WEST,
)
"""Canonical iteration order matching WALL_ORDER_CONVENTION='CCW_FROM_SOUTH'.
Production code paths MUST use Grid.iter_wall_segments_canonical() rather than
iterating over Grid.wall_segments directly. See § 3 W8 invariant."""


class WallTag(str, Enum):
    EXTERNAL      = "external"
    INTERNAL      = "internal"
    LOAD_BEARING  = "load_bearing"


@dataclass(frozen=True)
class WallSegment:
    wall_id: str
    axis: WallAxis
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float
    length_m: float
    tags: frozenset[WallTag]
    # __post_init__ enforces W1, W2, W3


def serialize_tags_sorted(tags: frozenset[WallTag]) -> tuple[str, ...]:
    """Tuple chosen over frozenset for deterministic ordering."""
    return tuple(sorted((t.value for t in tags)))


def assert_wall_segment_order_independent(fn: Callable[[Grid], Any]) -> None:
    """Test helper (NEW v0.6 per Walk #7 #1). Calls fn(grid) once with default
    wall_segments order, once with shuffled order. Asserts that
    canonical_serialize(result_a) == canonical_serialize(result_b).

    Use in deterministic-replay tests to catch W8 violations: any production
    code path that depends on wall_segments tuple ordering will produce
    different results across the two calls and fail this assertion.

    Note: requires `canonical_serialize` from C10 (or shared utility module —
    cross-component import). v1 ships with C10 dependency; v2 may extract to
    a shared utilities module.
    """
    import random
    # Caller passes a Grid-producing fixture; helper builds two Grids
    # (one canonical, one shuffled) and runs fn against both.
    ...


@dataclass(frozen=True)
class Grid:
    columns: list[ColumnPosition]
    bay_x_m: float
    bay_y_m: float
    columns_x_count: int
    columns_y_count: int
    envelope_width_m: float
    envelope_depth_m: float
    wall_segments: tuple[WallSegment, ...] = ()    # backwards-compat default

    def wall_segment_by_id(self, wall_id: str) -> WallSegment:
        for w in self.wall_segments:    # O(N); B-231 polygonal optimisation
            if w.wall_id == wall_id:
                return w
        raise KeyError(f"Grid has no wall_segment with wall_id={wall_id!r}")

    # NEW v0.6 (Walk #7 #1):
    def iter_wall_segments_canonical(self) -> tuple[WallSegment, ...]:
        """Returns wall_segments in canonical WallAxis order (SOUTH, EAST, NORTH, WEST).

        Production code paths MUST use this method instead of iterating over
        `wall_segments` directly. Guarantees byte-identical iteration regardless
        of the underlying tuple's storage ordering.

        Direct iteration over `wall_segments` is reserved for canonical-
        serialisation snapshots that explicitly want raw storage order for
        debugging/audit purposes.

        Returns walls present in the Grid; missing axes are silently omitted
        (non-rectangular envelopes post B-066 may have <4 walls per axis).
        """
        by_axis: dict[WallAxis, WallSegment] = {w.axis: w for w in self.wall_segments}
        return tuple(by_axis[a] for a in WALL_AXIS_CANONICAL_ORDER if a in by_axis)
```

---

## § 2 — Behaviour (UNCHANGED from v0.5)

`GridGenerator.generate(envelope_width_m, envelope_depth_m)` populates `wall_segments` with exactly 4 segments for v1 rectangular envelope, in **CCW from SOUTH** storage order:

| wall_id | axis | start | end | length_m | tags |
|---|---|---|---|---|---|
| `WALL_SOUTH` | SOUTH | (0, 0) | (W, 0) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_EAST` | EAST | (W, 0) | (W, D) | D | {EXTERNAL, LOAD_BEARING} |
| `WALL_NORTH` | NORTH | (W, D) | (0, D) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_WEST` | WEST | (0, D) | (0, 0) | D | {EXTERNAL, LOAD_BEARING} |

`NORTH` here is **project-north** (+y direction). True-north handled by C6 OrientedCandidate.

Storage order matches canonical order at v1 (since `GridGenerator.generate` produces them in CCW-from-south sequence). However, **production code MUST NOT rely on this coincidence**: future Grid construction paths (e.g., deserialisation, B-066 polygonal envelopes, hand-built test fixtures) may store walls in arbitrary order. Always use `iter_wall_segments_canonical()`.

---

## § 3 — Invariants (REVISED v0.6 — W8 strengthened)

| # | Invariant | Mode |
|---|---|---|
| W1 | `length_m` matches Euclidean(start, end) | RAISE |
| W2 | Every WallSegment has at least one WallTag | RAISE |
| W3 | v1 walls axis-aligned | RAISE |
| W4 | v1 Grid has exactly 4 wall_segments | RAISE |
| W5 | Each WallAxis appears exactly once | RAISE |
| W6 | wall_ids unique | RAISE |
| W7 | Total wall length == perimeter (`2W + 2D`) | RAISE |
| **W8 (REVISED v0.6)** | **All production code paths consuming Grid wall data MUST use `Grid.iter_wall_segments_canonical()`. Direct iteration over `Grid.wall_segments` is reserved for canonical-serialisation snapshots and explicit raw-storage inspection. Algorithms using the canonical accessor MUST produce byte-identical output regardless of `wall_segments` tuple storage order.** Verified by C7 → C9 → C10 integration shuffle-order regression test using `assert_wall_segment_order_independent` helper. Test-level enforcement; direct iteration of `wall_segments` is not runtime-blocked but flagged in code review. | API + TEST |

---

## § 4 — Test coverage requirements (REVISED v0.6 — added accessor + helper tests)

Per D-066 build cycle:
- 4 wall-segment construction tests (W1-W7 + happy path)
- 2 lookup tests (`wall_segment_by_id` happy + KeyError)
- 1 backwards-compat test (existing 174 C7 tests pass with new `wall_segments=()` default)
- 2 ordering tests (CCW-from-south for square + rectangular envelopes)
- 1 module constant test (`WALL_ORDER_CONVENTION == "CCW_FROM_SOUTH"`)
- 1 `serialize_tags_sorted` helper test
- 2 W8 unit shuffle-order regression tests (using `assert_wall_segment_order_independent`)
- 1 W8 integration shuffle-order regression test (full C7 → C9 → C10 pipeline; canonical-JSON comparison; per audit fix F-v5-W1)
- **3 NEW v0.6 tests for canonical accessor**:
  - `iter_wall_segments_canonical` returns walls in `(SOUTH, EAST, NORTH, WEST)` order regardless of storage order.
  - `iter_wall_segments_canonical` silently omits missing axes (forward-compat for non-rectangular envelopes).
  - `assert_wall_segment_order_independent` helper correctly detects an ordering-dependent function vs an order-independent function (positive + negative test cases).

**Target**: ~17 new tests (was 14 in v0.5). No regressions on existing 174 C7 tests. Cumulative target post-amendment ship: 2155 + 17 ≈ 2172 passed.

---

## § 5 — Failure modes (UNCHANGED)

```
ValueError      — invariant violations W1-W7
KeyError        — wall_segment_by_id with unknown id
```

W8 enforced at API + test level only.

---

## § 6 — Frozen-and-replace pattern (UNCHANGED)

`WallSegment` is frozen. Tag/field updates produce new instances via `dataclasses.replace`. Standard discipline across C9 dataclasses.

---

## § 7 — Open backlog (carried forward, unchanged)

| ID | Description | Trigger |
|---|---|---|
| B-231 | Wall lookup O(1) optimisation for polygonal envelopes (precomputed dict) | Post B-066 |
| B-235 | WallTag domain split (topology / structural / placement) | When 5+ tags exist |
| B-237 | Test-suite modernisation: Hypothesis property-based testing, debug-mode runtime shuffle | Post v1 ship |

---

## § 8 — Rule 11 spec audit on v0.6 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.6 itself): 0** — drafting absorbs Walk #7 #1.

**OPEN QUESTIONS surfaced**: 0.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v6-W1 | `assert_wall_segment_order_independent` requires `canonical_serialize` from C10 (or a shared utilities module). C7 currently has no dependency on C10 — introducing one creates a dependency cycle (C7 → C10 → C7). | **NEEDS WALK** — either (a) extract `canonical_serialize` to a `buildemup.utilities` module that both C7 and C10 import, or (b) keep helper in C10 (not C7) but document its existence in C7 spec. Recommend (a); cleaner long-term. v0.7 fix or session-deferred. |
| F-v6-W2 | `iter_wall_segments_canonical` returns a `tuple[WallSegment, ...]` — same type as `wall_segments`. A future contributor might still use `grid.wall_segments` by reflex. The canonical accessor is "MUST USE" but the language can't enforce it. | **MINOR** — Python convention; can't enforce. Document in spec § 3 W8; B-237 covers linting/type-narrow approaches. |
| F-v6-W3 | The accessor is named `iter_*` but returns a tuple, not an iterator. Naming is misleading. | **PATCH-NOW v0.6 ITSELF** — rename to `wall_segments_canonical()` (no `iter_` prefix). Inline-applied below. |
| F-v6-W4 | Test count target says 17 new tests; rough math: 4+2+1+2+1+1+2+1+3 = 17. Math correct. | **PASS** |
| F-v6-W5 | The canonical accessor handles missing axes silently for forward-compat with polygonal envelopes (post B-066). But v1 invariant W4 requires exactly 4 walls — so silent-omission can never trigger at v1. The forward-compat code is currently unreachable. | **MINOR** — accept as forward-compat documentation; no v1 cost. Document in accessor docstring. |

**PATCH-NOW APPLIED INLINE**:
- **F-v6-W3** PATCHED: method rename `iter_wall_segments_canonical` → `wall_segments_canonical`. The `iter_` prefix conventionally denotes an iterator; this method returns a tuple. Updating § 1 schema, § 2 behaviour text, § 3 W8 invariant, § 4 test descriptions to use the corrected name. Re-rendering relevant sections:

> § 1 schema:
> ```python
>     def wall_segments_canonical(self) -> tuple[WallSegment, ...]:
>         """Returns wall_segments in canonical WallAxis order ..."""
> ```
>
> § 2 production code text: "Always use `wall_segments_canonical()`."
>
> § 3 W8 invariant: "All production code paths ... MUST use `Grid.wall_segments_canonical()`. Direct iteration over `Grid.wall_segments` ..."
>
> § 4 tests: "`wall_segments_canonical` returns walls in `(SOUTH, EAST, NORTH, WEST)` order ..."

**REJECTED-AS-CONSIDERED**:
- "Add `Grid.canonical_iteration_marker: bool` flag for runtime self-test?" — No. Architectural noise; canonical accessor is the API.
- "Should the helper raise on detection rather than assert?" — No. `assert_*` naming convention follows pytest discipline.
- "Should W8 deprecate `wall_segments` direct access entirely?" — No. Snapshot/audit code legitimately needs raw storage order.

**Audit summary**: 1 patch-now (F-v6-W3 method rename, applied inline), 1 needs-walk (F-v6-W1 dependency placement), 3 minor/pass, 3 rejected. **No real bugs.** Audit ran; not performative.

---

## § 9 — Status

- **v0.6 PROPOSED.** **NOT LOCKED** per Ramalingam directive.
- 1 walk finding open (F-v6-W1 — `canonical_serialize` placement; v0.7 or session-deferred fix).
- Method rename applied inline at audit (F-v6-W3): `wall_segments_canonical()` (no `iter_` prefix).
- All v0.5 items + Walk #7 #1 absorbed.
- Estimated walks to LOCK: **0-1.** F-v6-W1 may resolve via session-deferred utilities-module extraction.

---

**End of v0.6 PROPOSED.** Awaits Ramalingam's reading.
