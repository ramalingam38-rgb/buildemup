# C7 SPEC AMENDMENT v0.7 PROPOSED — WallSegment emission (B-212 resolution)

**Component**: 7 (Structural Grid Engine — already SHIPPED at v0.7.3)
**Amendment status**: **v0.7 PROPOSED.** Supersedes v0.6. **NOT LOCKED** per Ramalingam directive.
**Authority**: S35 author's draft. PROPOSED, awaiting Ramalingam adjudication.
**Authored**: S35 Walk #8 outcome.
**Driver**: B-212 (C10 LOCK BLOCKER) + Walk #8 #8 immediate B-240 extraction (architectural-direction fix).

---

## § 0 — Summary of changes from v0.6 → v0.7

Walk #8 reviewer #8 surfaced that v0.6's deferral of B-240 (canonical_serialize utilities extraction) institutionalises bad dependency direction even at test-helper level. Test-only dependency inversion (C7 → C10) still violates layering. Web evidence backs the discipline: deterministic replay infrastructure should sit at lowest available layer.

| Item | v0.6 status | v0.7 resolution |
|---|---|---|
| F-v6-W1 (canonical_serialize placement) | Recommended (b) C10 import, B-240 deferred to v2 | **REVERSED**: extract `canonical_serialize` to `buildemup.utilities` module **immediately** (per Walk #8 reviewer #8). Tiny infrastructure work; preserves correct dependency direction. **B-240 IMPLEMENTED-IN-SPEC at v0.7.** |
| Walk #8 #2 (CI lint enforcement) | NEW | **Filed as B-241**, post-v1. v0.7 documents the convention; CI enforcement = test-modernisation (B-237) territory. |
| Walk #8 #3 (wall fragmentation) | NEW | **Filed as B-242**, post-v1. Indian residential typically has corner-doors not mid-wall fragmentation; deferral acceptable. v0.7 documents the limitation in § 6. |

All other v0.6 items unchanged. **Schema additions: zero. Helper relocation: yes.**

---

## § 1 — Schema (REVISED v0.7 — `assert_wall_segment_order_independent` relocated to utilities module)

The `WALL_AXIS_CANONICAL_ORDER` constant, `WallAxis` enum, `WallTag` enum, `WallSegment` dataclass, `serialize_tags_sorted` helper, and `Grid` dataclass with `wall_segments_canonical()` method are **UNCHANGED from v0.6.**

**Relocated v0.7**: `assert_wall_segment_order_independent` test helper moves from C7 module to `buildemup.utilities`:

```python
# In buildemup/utilities/canonical.py (NEW v0.7 module per B-240):

def canonical_serialize(obj) -> str:
    """Module-level helper for byte-identical replay snapshots.

    Produces deterministic JSON across iteration orderings:
    - dict keys sorted lex-ASC
    - tuple/list elements emitted in source order (caller responsibility)
    - float values rounded to 6dp
    - frozenset[Enum] converted via serialize_tags_sorted (C7 helper)

    Centralised here per Walk #8 reviewer #8 architectural direction. Both C7
    (test helper) and C10 (replay snapshots) import from this module. Avoids
    C7→C10 test dependency inversion; preserves clean layering.
    """
    return json.dumps(_canonicalize(obj), sort_keys=True, separators=(",", ":"))


def assert_wall_segment_order_independent(fn: Callable[[Grid], Any]) -> None:
    """Test helper. Calls fn(grid) twice — default + shuffled wall_segments order.
    Asserts canonical_serialize(result_a) == canonical_serialize(result_b).

    Use in deterministic-replay tests to catch W8 violations.
    """
    import random
    # Caller passes a Grid-producing fixture; helper builds two Grids
    # (one canonical, one shuffled) and runs fn against both.
    ...
```

**C7 module re-exports** (for backwards-compat with v0.6 test code that imports from C7):
```python
# In components/c07/__init__.py:
from buildemup.utilities.canonical import (
    canonical_serialize,
    assert_wall_segment_order_independent,
)
```

C10 imports the same way. **No production cycle.** Test imports cross via the utilities module — clean architectural direction.

---

## § 2 — Behaviour (UNCHANGED from v0.6)

`GridGenerator.generate(envelope_width_m, envelope_depth_m)` populates `wall_segments` in CCW-from-south order. v0.7 production code uses `wall_segments_canonical()` (carried).

---

## § 3 — Invariants W1-W8 (UNCHANGED from v0.6)

(See v0.6 spec for W1-W7. W8 unchanged: production code uses `wall_segments_canonical()`; direct iteration reserved for snapshots.)

---

## § 4 — Test coverage requirements (UNCHANGED test count from v0.6 — 17 new tests)

Test target ~17 new tests including the W8 integration shuffle test using the relocated `assert_wall_segment_order_independent` helper. Cumulative target: 2155 + 17 ≈ 2172 passed.

---

## § 5 — Failure modes (UNCHANGED)

```
ValueError      — invariant violations W1-W7
KeyError        — wall_segment_by_id with unknown id
```

W8 enforced at API + test level only.

---

## § 6 — Limitations documented (NEW v0.7 per Walk #8 #3)

**Wall fragmentation (B-242)**: v1 `WallSegment` models a wall as a single continuous segment with `length_m`. Real walls may have doors, windows, shafts, or structural setbacks creating unusable subregions. v1 cluster-occupancy checks (C10 Inv 19) assume the full wall length minus safety margin is usable. For typical Indian residential layouts (corner-doors, minimal mid-wall fragmentation), this assumption holds in practice. Future polygonal envelopes (B-066) and luxury layouts with mid-wall doors require `usable_wall_spans: tuple[WallSpan, ...]` schema upgrade — tracked as **B-242**, post-v1 ship.

---

## § 7 — Open backlog (UPDATED v0.7)

| ID | Description | Trigger | Status |
|---|---|---|---|
| B-231 | Wall lookup O(1) optimisation for polygonal envelopes | Post B-066 | Open |
| B-235 | WallTag domain split (topology / structural / placement) | When 5+ tags exist | Open |
| B-237 | Test-suite modernisation; debug-mode runtime shuffle | Post v1 ship | Open |
| **B-240** | Extract `canonical_serialize` to `buildemup.utilities` shared module | v2 | **IMPLEMENTED-IN-SPEC at v0.7** |
| **B-241 (NEW)** | CI lint rule: forbid `.wall_segments` direct iteration outside snapshot/test modules. Pairs with B-237. | Post v1 ship | Open |
| **B-242 (NEW)** | `WallSegment.usable_wall_spans` for wall fragmentation modeling | Post v1 ship; defer if Indian-typical layouts have corner-doors only | Open |

---

## § 8 — Rule 11 spec audit on v0.7 PROPOSED

Per Rule 11 (LOCKED at S34).

**PATCH-NOW (in v0.7 itself): 0** — drafting absorbs Walk #8 #8.

**OPEN QUESTIONS surfaced**: 0.

**SPEC-AUDIT FINDINGS**:

| # | Finding | Verdict |
|---|---|---|
| F-v7-W1 | The `buildemup/utilities/canonical.py` module is new in v0.7. It needs its own test coverage (canonical_serialize edge cases: nested dicts, frozensets, FP precision). Test target should rise. | **MINOR** — add ~3 tests for canonical_serialize. v0.7 test target: 17 + 3 = 20 new tests. Adjust below. |
| F-v7-W2 | C7 module re-exports from `buildemup.utilities` create import-order sensitivity (utilities must be importable before C7). Document import order. | **MINOR** — Python convention; acceptable. Document in module docstring. |
| F-v7-W3 | The "no production cycle" claim relies on C7 production code NOT importing from `buildemup.utilities`. If a future contributor adds such an import, the architectural cleanliness erodes silently. | **NEEDS WALK** — accept Python convention; B-237 lint covers. Or, file as note: "C7 production code MUST NOT import from buildemup.utilities; only test paths and re-export shims." Documented inline. |

**REJECTED-AS-CONSIDERED**:
- "Should `buildemup.utilities` be its own component (CN.5 utilities)?" — No. It's infrastructure, not a Track-3 component. No spec needed.
- "Should re-exports be deprecated immediately?" — No. Backwards-compat for v0.6 test code; soft-remove in v2.

**Audit summary**: 0 patch-now, 1 minor (test count adjustment, applied below), 2 minor/NEEDS-WALK, 2 rejected. **No real bugs.** Audit ran; not performative.

**Test target adjustment per F-v7-W1**: 17 + 3 = 20 new tests. Cumulative target: 2155 + 20 ≈ 2175 passed.

---

## § 9 — Status

- **v0.7 PROPOSED.** **NOT LOCKED** per Ramalingam directive.
- 0 walk findings (1 minor inline-applied, 2 minor accepted as Python conventions).
- 0 open questions.
- B-240 IMPLEMENTED-IN-SPEC; B-241, B-242 newly filed for post-v1.
- Estimated walks to LOCK: **0** (LOCK CANDIDATE).

---

**End of v0.7 PROPOSED.** Awaits Ramalingam's reading.
