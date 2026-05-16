# C7 SPEC AMENDMENT v0.8 LOCKED — WallSegment emission (B-212 resolution)

**Component**: 7 (Structural Grid Engine — already SHIPPED at v0.7.3)
**Amendment status**: **v0.8 LOCKED.** Supersedes v0.7 PROPOSED.
**Authority**: Ramalingam declaration at S35 Walk #9 close.
**Authored**: S35 Walk #9 outcome.
**Driver**: B-212 resolved at LOCK.

---

## § 0 — LOCK declaration

**Ramalingam directive at S35 Walk #9 close**: "lock both the spec docs."

Per Rule 8 (LOCK authority belongs to Ramalingam alone), this declaration constitutes the LOCK trigger. v0.7 contents promoted to v0.8 LOCKED with no schema changes; only the LOCK status updates.

**B-212 RESOLVED**: C10 LOCK BLOCKER cleared. C7 amendment is SHIPPED-AS-LOCKED (build delivers the schema).

---

## § 1 — Delta from v0.7 → v0.8

| Item | v0.7 status | v0.8 LOCKED resolution |
|---|---|---|
| Walk #9 #6 (replay determinism cross-runtime) | NEW | **Filed as part of B-237** (test-suite modernisation already covers cross-platform CI matrix). No spec change. |
| Walk #9 #8 (polygonal completeness) | Re-surface of B-217/226/231/235/242 | Already filed; no spec change. |
| Walk #9 reviewer overall | All other items already-filed-as-backlog | Confirmed. v0.8 LOCKS as-is. |

**Schema, behaviour, invariants W1-W8, test target (~20 new), failure modes, frozen-and-replace pattern, § 6 wall-fragmentation limitation: ALL UNCHANGED FROM v0.7.**

The full v0.7 spec content is hereby promoted to LOCKED state. See `58_C7_AMENDMENT_v0_7_PROPOSED.md` for the complete normative text — all sections § 1 through § 6 carry forward verbatim under v0.8 LOCKED status.

---

## § 2 — Open backlog (UNCHANGED from v0.7)

| ID | Description | Trigger | Status |
|---|---|---|---|
| B-231 | Wall lookup O(1) optimisation for polygonal envelopes | Post B-066 | Open |
| B-235 | WallTag domain split | When 5+ tags exist | Open |
| B-237 | Test-suite modernisation; debug-mode runtime shuffle; **cross-platform CI replay matrix per Walk #9 #6** | Post v1 ship | Open (scope expanded) |
| B-240 | Extract `canonical_serialize` to `buildemup.utilities` | IMPLEMENTED in v0.7 | Resolved |
| B-241 | CI lint rule for `.wall_segments` direct iteration | Post v1 ship | Open |
| B-242 | `WallSegment.usable_wall_spans` for fragmentation modeling | Post v1 ship | Open |

---

## § 3 — Build session readiness

**B-212 unblocks C10 LOCK + C10 build.** Build session can begin immediately upon C10 LOCK declaration (also at Walk #9 close per Ramalingam directive).

C7 amendment v0.8 build scope:
- 1 new module-level constant (`WALL_AXIS_CANONICAL_ORDER`)
- 2 new enums (`WallAxis`, `WallTag`)
- 1 new dataclass (`WallSegment` with W1-W3 `__post_init__` checks)
- 1 new module helper (`serialize_tags_sorted`)
- 1 new method on `Grid` (`wall_segments_canonical()`)
- 1 new field on `Grid` (`wall_segments: tuple[WallSegment, ...] = ()` backwards-compat default)
- 1 utilities module (`buildemup/utilities/canonical.py`) with `canonical_serialize()` + `assert_wall_segment_order_independent()`
- C7 module re-exports for backwards-compat
- 1 new W8 invariant (TEST-LEVEL enforcement; no runtime check)
- ~20 new tests; existing 174 C7 tests preserve

**Backwards-compatibility verified**: `wall_segments=()` default preserves all existing C9 / C8 / C2 / C1 call sites.

---

## § 4 — Status

- **v0.8 LOCKED.**
- **B-212 RESOLVED.**
- 0 open walk findings; 0 open questions.
- Build session: ready immediately.

---

**End of v0.8 LOCKED. Authority: Ramalingam declaration, S35 Walk #9 close.**
