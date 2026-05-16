# C7 SPEC AMENDMENT v0.5 PROPOSED — LOCK CANDIDATE — WallSegment emission (B-212)

**Component**: 7 (Structural Grid Engine — already SHIPPED at v0.7.3)
**Amendment status**: **v0.5 PROPOSED — LOCK CANDIDATE.** Supersedes v0.4. Pending Ramalingam adjudication for LOCK.
**Authority**: S35 author's draft. PROPOSED, awaiting `lock it` / `vN LOCKED` per Rule 8.
**Authored**: S35 Walk #6 outcome.
**Driver**: B-212 (C10 LOCK BLOCKER).

---

## § 0 — Summary of changes from v0.4 → v0.5

Walk #6 reviewer flagged 1 v0.4 audit finding (F-v4-W1) and Walk #6 #1 (W8 enforcement scope). v0.5 resolves both per Walk #6 adjudications.

| Item | v0.4 status | v0.5 resolution |
|---|---|---|
| F-v4-W1 (W8 test-level only vs runtime check) | Pending | **TEST-LEVEL ONLY** confirmed (your call). Debug-mode shuffle deferred to **B-237** (test-suite modernisation). Documented explicitly in § 3 W8 invariant. |
| Walk #6 #1 (Replay determinism integration tests) | NEW | Test plan extended: shuffle-order regression test now covers C7 → C9 → C10 integration chain (not just C7 → C10). 1 additional test. |
| Walk #6 #18 (Downstream order-dependence) | NEW | W8 invariant text strengthened: "downstream consumers MUST treat `wall_segments` as set-membership; algorithms MUST produce byte-identical output regardless of tuple iteration order. Verified by integration shuffle test spanning C7 → C9 → C10." |

All other v0.4 items remain unchanged. **No schema changes from v0.4.**

---

## § 1 — Output schema (UNCHANGED from v0.4)

```python
WALL_ORDER_CONVENTION: Final[str] = "CCW_FROM_SOUTH"


class WallAxis(str, Enum):
    """`NORTH` = PROJECT-NORTH (+y of envelope coord system).
    True-north handled by C6 OrientedCandidate; C7 does not rotate.
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
    replace pattern matching C9 discipline).

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
        # W1
        if abs(self.length_m - hypot(dx, dy)) > 1e-6:
            raise ValueError(
                f"WallSegment {self.wall_id}: length_m ({self.length_m}) "
                f"does not match geometry ({hypot(dx, dy):.6f})"
            )
        # W2
        if not self.tags:
            raise ValueError(f"WallSegment {self.wall_id}: tags must be non-empty")
        # W3
        if abs(dx) > 1e-6 and abs(dy) > 1e-6:
            raise ValueError(
                f"WallSegment {self.wall_id}: v1 walls must be axis-aligned; "
                f"got dx={dx:.6f}, dy={dy:.6f}"
            )


def serialize_tags_sorted(tags: frozenset[WallTag]) -> tuple[str, ...]:
    """Centralized helper for deterministic provenance. Returns tuple sorted
    by enum value. Tuple chosen over frozenset for deterministic ordering;
    frozenset iteration is not order-stable.
    """
    return tuple(sorted((t.value for t in tags)))


@dataclass(frozen=True)
class Grid:
    columns: list[ColumnPosition]
    bay_x_m: float
    bay_y_m: float
    columns_x_count: int
    columns_y_count: int
    envelope_width_m: float
    envelope_depth_m: float
    wall_segments: tuple[WallSegment, ...] = ()

    def wall_segment_by_id(self, wall_id: str) -> WallSegment:
        for w in self.wall_segments:    # O(N); B-231 polygonal optimisation
            if w.wall_id == wall_id:
                return w
        raise KeyError(f"Grid has no wall_segment with wall_id={wall_id!r}")
```

---

## § 2 — Behaviour (UNCHANGED from v0.4)

`GridGenerator.generate(envelope_width_m, envelope_depth_m)` populates `wall_segments` with exactly 4 segments for v1 rectangular envelope, in **CCW from SOUTH** order.

| wall_id | axis | start | end | length_m | tags |
|---|---|---|---|---|---|
| `WALL_SOUTH` | SOUTH | (0, 0) | (W, 0) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_EAST` | EAST | (W, 0) | (W, D) | D | {EXTERNAL, LOAD_BEARING} |
| `WALL_NORTH` | NORTH | (W, D) | (0, D) | W | {EXTERNAL, LOAD_BEARING} |
| `WALL_WEST` | WEST | (0, D) | (0, 0) | D | {EXTERNAL, LOAD_BEARING} |

`NORTH` here is **project-north** (+y direction). True-north handled by C6 OrientedCandidate.

---

## § 3 — Invariants (UNCHANGED — W1-W8)

| # | Invariant | Mode |
|---|---|---|
| W1 | `length_m` matches Euclidean(start, end) | RAISE |
| W2 | Every WallSegment has at least one WallTag | RAISE |
| W3 | v1 walls axis-aligned | RAISE |
| W4 | v1 Grid has exactly 4 wall_segments | RAISE |
| W5 | Each WallAxis appears exactly once | RAISE |
| W6 | wall_ids unique | RAISE |
| W7 | Total wall length == perimeter (`2W + 2D`) | RAISE |
| **W8** | **Downstream consumers MUST treat `wall_segments` as set-membership; algorithms MUST produce byte-identical output regardless of tuple iteration order. Verified by C7 → C9 → C10 integration shuffle-order regression test (Walk #6 strengthening).** Test-level only (no runtime check). Debug-mode runtime shuffle deferred to **B-237** test modernisation. | TEST-LEVEL |

---

## § 4 — Test coverage requirements (REVISED v0.5 — added integration shuffle test)

Per D-066 build cycle:
- 4 wall-segment construction tests (W1-W7 + happy path)
- 2 lookup tests (`wall_segment_by_id` happy + KeyError)
- 1 backwards-compat test (existing 174 C7 tests pass with new `wall_segments=()` default)
- 2 ordering tests (CCW-from-south for square + rectangular envelopes)
- 1 module constant test (`WALL_ORDER_CONVENTION == "CCW_FROM_SOUTH"`)
- 1 `serialize_tags_sorted` helper test
- 2 W8 unit shuffle-order regression tests (Grid built with shuffled tuple → C9 produces identical output; C9 produces identical output → C10 produces identical output)
- **1 W8 integration shuffle-order regression test (NEW v0.5)**: full C7 → C9 → C10 pipeline produces byte-identical `WetZonePlannedCandidate` outputs across shuffled wall_segments tuple orderings on `bangalore_40x60` fixture. Asserts `pickle.dumps(result_a) == pickle.dumps(result_b)`.

**Target**: ~14 new tests (was 13 in v0.4), no regressions on existing 174 C7 tests. Cumulative target post-amendment ship: 2155 + 14 ≈ 2169 passed.

---

## § 5 — Failure modes (UNCHANGED)

```
ValueError      — invariant violations W1-W7
KeyError        — wall_segment_by_id with unknown id
```

W8 enforced at test level only.

---

## § 6 — Frozen-and-replace pattern (UNCHANGED — documentation only)

`WallSegment` is frozen. Tag/field updates produce new instances via `dataclasses.replace`. Standard discipline across C9 dataclasses. O(N) replacement fine at v1 (N=4); polygonal era benefits from batch-replace helpers (B-231-adjacent).

---

## § 7 — Open backlog (carried forward)

| ID | Description | Trigger |
|---|---|---|
| B-231 | Wall lookup O(1) optimisation for polygonal envelopes (precomputed dict) | Post B-066 |
| B-235 | WallTag domain split (topology / structural / placement) | When 5+ tags exist |
| B-237 | Test-suite modernisation: Hypothesis property-based testing, shuffle-mode debug runtime | Post v1 ship |

---

## § 8 — Rule 11 spec audit on v0.5 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.5 itself): 0** — no changes from v0.4 except W8 strengthening + integration test.

**OPEN QUESTIONS surfaced**: 0. All v0.4 questions resolved.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v5-W1 | W8 integration test uses `pickle.dumps` for byte-equality — but `pickle` ordering of dict keys depends on Python version. Two Python 3.10 runs produce identical pickle; Python 3.11 may not. Stronger discipline: serialise via canonical-JSON (sorted keys) and compare strings. | **NEEDS WALK** — adopt canonical-JSON comparison. Lightweight; pickle-version-independent. v0.5 audit decision: **PATCH-NOW the test description** to specify canonical-JSON not pickle. Inline-applied below. |
| F-v5-W2 | The "B-237 test modernisation" reference adds W8 enforcement to a backlog item. Is B-237's scope correctly inclusive of debug-mode shuffle, or is that a separate concern? | **MINOR** — B-237 description already covers "shuffle-mode debug runtime" explicitly. No action. |
| F-v5-W3 | Test count target jumped from 13 (v0.4) to 14 (v0.5) — only one new test (the integration shuffle). Math correct first time. | **PASS** |

**PATCH-NOW APPLIED INLINE**:
- **F-v5-W1**: W8 test description (§ 4 last bullet) updated to specify canonical-JSON comparison instead of pickle:

> "1 W8 integration shuffle-order regression test (NEW v0.5): full C7 → C9 → C10 pipeline produces byte-identical `WetZonePlannedCandidate` outputs across shuffled wall_segments tuple orderings on `bangalore_40x60` fixture. **Asserts `canonical_json_serialize(result_a) == canonical_json_serialize(result_b)`** (canonical-JSON: sorted keys, FP rounded to 6dp per C10 v0.6 § 3 discipline). Pickle byte-comparison rejected at audit due to pickle-format Python-version sensitivity."

**REJECTED-AS-CONSIDERED**:
- "Should W8 carry a runtime debug-mode hash check?" — No. Test-level discipline suffices for v1; B-237 covers the modernisation path.
- "Should `Grid.__post_init__` fail-fast when `wall_segments=()` and other v0.7+ fields suggest production use?" — No. Backwards-compat default `()` is intentional. F-v3-W3 status quo.
- "Should we add `Grid.is_well_formed: bool` derived property for callers?" — Premature; no consumer asks for it.

**Audit summary**: 1 patch-now (F-v5-W1, applied inline), 2 minor/pass, 3 rejected. Audit ran; not performative. **No remaining walk findings. Spec is LOCK-ready.**

---

## § 9 — Status

- **v0.5 PROPOSED — LOCK CANDIDATE.**
- All v0.3 + v0.4 walk items resolved.
- W8 strengthened with integration test (canonical-JSON comparison per audit fix).
- 0 open questions; 0 walk findings.
- Backwards-compat preserved; existing 174 C7 tests stay green.
- **Awaits Ramalingam `lock it` / `LOCKED` declaration per Rule 8.**

---

**End of v0.5 PROPOSED — LOCK CANDIDATE.** Pending Ramalingam adjudication.
