# B-NEW-K — C7 staircase clearance W9 invariant — v1.0 **LOCKED**

**Status**: **v1.0 LOCKED** by Ramalingam at S38, 09 May 2026.
**Includes K-4 patch** (landing depth scales with width per NBC 2016).
**Predecessor**: v0.1 PROPOSED → v0.2 PROPOSED (K-4 patch round) → v1.0 LOCKED.
**Required by**: C11a v1.0 LOCKED § 3.4 — Tier A predicate matrix
`C7.staircase_clearance` for M3a/b/c operators.

---

## § 0 — What this amendment adds

C7 lacked any concept of a staircase. C11a's M3a/b/c mutation
operators move the staircase to designated positions; they need a
real, callable C7 predicate.

This amendment:

1. Adds `Staircase` frozen dataclass — axis-aligned rectangular
   footprint with optional WallAxis anchor.
2. Adds `Grid.staircase: Optional[Staircase] = None` field
   (backwards-compat default).
3. Adds NBC-2016-grounded clearance constants
   (`MIN_STAIRCASE_WIDTH_M = 0.9`, `MIN_STAIRCASE_LANDING_DEPTH_M = 0.9`)
   gated behind B-150-equiv primary-source verification.
4. Adds the **W9 numbered invariant** with **four sub-conditions**
   (a-d), enforced eagerly in `Grid.__post_init__` when staircase
   is set.
5. Exposes `validate_staircase_clearance(grid, staircase)` predicate
   that C11a Tier A registers as `C7.staircase_clearance`.

---

## § 1 — Scope discipline

What this amendment does **NOT** do at v1:

- Does NOT modify `GridGenerator.generate(...)` to construct
  staircases — `Grid.staircase` is data-model wiring only at v1.
- Does NOT model egress-clearance / room-layout interactions
  (filed as B-NEW-K-egress).
- Does NOT model climb direction, riser geometry, U/L-shape, or
  vertical clearance / headroom (filed as B-NEW-K-shape).
- Does NOT plumb staircase position through upstream
  `TopologyCandidate` or `WetZonePlannedCandidate` (filed as
  B-NEW-K-impl).

---

## § 2 — Schema

```python
MIN_STAIRCASE_WIDTH_M: Final[float] = 0.9
MIN_STAIRCASE_LANDING_DEPTH_M: Final[float] = 0.9

@dataclass(frozen=True)
class Staircase:
    origin_x_m: float
    origin_y_m: float
    width_m: float
    landing_depth_m: float
    anchor: Optional[WallAxis] = None

@dataclass(frozen=True)
class Grid:
    # ...existing fields...
    staircase: Optional[Staircase] = None  # NEW B-NEW-K
```

---

## § 3 — W9 invariant (with K-4 patch)

| # | Invariant | Mode |
|---|---|---|
| W1-W8 | (carried verbatim from C7 amendment v0.8 LOCKED) | as v0.8 |
| **W9** | **If `Grid.staircase` is set, the staircase satisfies four sub-conditions: (a) `width_m ≥ MIN_STAIRCASE_WIDTH_M`; (b) `landing_depth_m ≥ max(width_m, MIN_STAIRCASE_LANDING_DEPTH_M)` — landing must be at least the staircase width AND at least the NBC floor [K-4 patch]; (c) footprint lies entirely within envelope; (d) if `anchor` is set, footprint is flush with the corresponding envelope edge (within 1e-6 m).** | RAISE (Grid `__post_init__`) |

### K-4 patch rationale

NBC 2016 Part 4 requires landing depth ≥ staircase width (verified
S38 Walk #1 against InfraLens, Sobha, Housivity, houseyog
secondary sources; primary-source verification deferred to
B-150-equiv). v0.1 used a fixed 0.9m floor for both width and
landing — a 1.2m wide stair could pass W9 with a 0.9m landing,
which NBC would reject. v0.2 corrects this by requiring
`landing_depth_m ≥ max(width_m, 0.9)`.

---

## § 4 — Predicate contract

`validate_staircase_clearance(grid: Grid, staircase: Staircase)
-> tuple[bool, str | None]`

C11a Tier A registers this as `MutationViabilityPredicate(
rule_owner="C7", rule_id="staircase_clearance",
description="W9 four-sub-condition clearance check",
_predicate_fn=validate_staircase_clearance, pending_upstream=False)`.

---

## § 5 — Tests

`tests/test_c7_staircase_w9.py` — **27 tests, all passing**.
Includes 5 K-4-specific tests (`test_w9b_v0_2_*`):
- Wider stair with insufficient landing → fails W9-b
- Wider stair with proportional landing → passes
- Failure reason cites required value
- Minimum-width 0.9m stair with 0.9m landing → passes (floor case)
- Below-floor landing on minimum-width stair → fails

---

## § 6 — Backlog filed

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-NEW-K-impl** | Plumb staircase position through `GridGenerator.generate()` so C7 emits Grids with concrete staircase footprints | post-launch + C11a M3a/b/c stable | M |
| **B-NEW-K-shape** | Extend Staircase model with `climb_direction`, `shape: StairShape`, `riser_height_m`, `tread_depth_m` for U/L/spiral support | post-launch + B-NEW-K-impl | M-L |
| **B-NEW-K-egress** | Egress-clearance-in-front-of-staircase check (C9/C10 integration) | post-launch + B-238 architect review | M-L |

---

## § 7 — LOCK authority

**LOCKED v1.0 by Ramalingam at S38, 09 May 2026.**

---

**End of B-NEW-K v1.0 LOCKED.**
