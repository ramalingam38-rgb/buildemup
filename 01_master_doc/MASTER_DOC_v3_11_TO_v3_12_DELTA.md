# BuildemUp Master Doc — Delta v3.11 → v3.12

**Predecessor**: v3.11 (S36 close)
**Successor**: v3.12 (S37 close)
**Authored**: S37 close.

---

## What changed in S37

S37 was a **spec-arc session**. No new code shipped beyond the item-7
patch on C10. Two LOCKs granted (Rule 8) and a small code patch.

1. **C11a v1.0 LOCKED** — Topology Mutation Layer. 5+1 walks (W#1
   through W#5 LOCK candidate, plus W#6 reviewer-confirmation walk).
2. **C11b v1.0 LOCKED** — NSGA-II Local Refinement. 3+1 walks
   (W#1, W#2, W#3 LOCK candidate, plus W#4 reviewer-confirmation walk).
   Faster convergence per Ramalingam's S37 directive (target 2-3 walks).
3. **Item 7 patch** — C10 `_build_fixture_types_per_room` strict-fallback
   removal (raises `KBVersionMismatchError` instead of silent default).
   Address W#5 critique #7 from S36 close. +2 tests (2312 → 2314).

---

## C11a v1.0 LOCKED — summary

**Mission**: per-topology mutation operator catalog (16 enum entries
across 9 families: BASE, FLIP, STAIRCASE, CORRIDOR, ZONE, WET_WALL,
GRID, VERTICAL, ENTRY).

**Architecture highlights**:
- Two-tier execution: Tier A shallow operators (M1/M2/M3/M4/M5/M9) +
  Tier B regenerative operators (M6/M7/M8) via `DeepMutationPipeline`
- 30 invariants
- `MutationLegalityResponsibilityMatrix` — C11a does NOT own
  architectural rules; predicates reference upstream rule IDs
- `DeepMutationPurityContract` (atomicity-by-construction)
- `UpstreamAmendmentWaiver` mechanism (max 3 active at LOCK, granted
  by Ramalingam alone)
- `DeltaKey` canonical enum (hierarchical namespace, 18 entries across
  geometry/adjacency/circulation/zoning/plumbing/multifloor/meta domains)
- `QuarantineFingerprint` + replay rejection
- `severity_tier` ClassVar inversion (requires upstream B-NEW-P amendment)
- Single-threaded contract at v1
- 16 v1 subsystems declared
- ~205 test target

**Spec arc**: v0.1 (15 open Qs) → v0.2 (9) → v0.3 (6) → v0.4 (4) →
v0.5 (0). Walk #6 reviewer-confirmation walk endorsed v0.5 as
freeze-ready; LOCKED.

**Cumulative test target after C11a build**: 2314 + 205 ≈ **2519 passed**.

**Build prerequisites** (Inv 24 LOCK gate):
- B-NEW-J (C5 privacy zoning amendment) — XS
- B-NEW-K (C7 staircase clearance amendment) — XS
- B-NEW-L (C8 entry approach amendment) — XS
- B-NEW-P (upstream `severity_tier` cluster on C7/C9/C10) — XS

Per Ramalingam S37: waiver tokens GRANTED for all 4. Note 4 > § 0.2
cap of 3; see § 8 of v3.12 delta below for reconciliation.

---

## C11b v1.0 LOCKED — summary

**Mission**: per-topology NSGA-II Pareto search; geometric parameter
refinement (room dimensions only at v1).

**Architecture highlights**:
- NSGA-II-CDP (Constrained Domination Principle); SBX η_c=20 crossover,
  polynomial η_m=20 mutation
- 25 invariants
- `EvaluatorProtocol` forward-coupling to C14 (deliberately minimal:
  1 method + PurityAttestation + identity + version hash)
- `StubEvaluator` for v1 build-time testing (geometry-correlated
  synthetic objectives — compactness, aspect variance, envelope
  efficiency)
- Feasibility-aware sequential area allocation init (3 permutations
  per candidate to reduce sampling bias)
- `StagnationConfig` adaptive cadence: O(N) centroid variance every
  gen, full O(N²) check every 5 gens
- `DominanceSorterProtocol` abstraction (sort algorithm replaceable;
  diversity/survivor semantics hardcoded NSGA-II)
- `EnvironmentFingerprint` with `c11b_version` + `numpy_blas_info_summary`
- `output_sequence_is_quality_ranked: bool` always False at v1 (hard
  contract signal)
- `MAX_ROOM_ASPECT_RATIO=3.0` HARD constraint via NSGA-II-CDP
- `SEMANTIC_CAP_BY_CATEGORY`: bathroom 1.8×, kitchen 1.5×, etc.
  (universal default 2.5×)
- 10 v1 subsystems declared
- ~190 test target

**Spec arc**: v0.1 (7 open Qs) → v0.2 (2) → v0.3 (0). Walk #4
reviewer-confirmation walk endorsed v0.3 as freeze-ready; LOCKED.

**Cumulative test target after C11b build** (post-C11a): 2519 + 190 ≈
**2709 passed**.

**Build prerequisites**: inherits C11a's via shared upstream
amendments. C11a must ship before C11b (C11b consumes
`MutatedTopologyCandidate` from C11a).

---

## Item 7 patch on C10

**Where**: `components/c10/wet_zone_planner.py`,
`_build_fixture_types_per_room` function.

**Before**: silent fallback to default fixture tuples on KB lookup
failure (e.g., `("water_closet", "lavatory", "shower")` for missing
bathroom subtype).

**After**: raises `KBVersionMismatchError` with chained `KeyError`
preserving original lookup error context. Inv 16 violations now
surface immediately.

**Tests**: 2 added in `tests/test_c10_kb_validator.py` (`TestStrictFallbackRemoval`).

**Test count**: 2312 → **2314 passed** / 3 skipped.

---

## Backlog at S37 close

| Bucket | Count |
|---|---|
| Pre-existing (carried) | 23 |
| New at S37 (C11a) | 18 (4 upstream amendments waived) |
| New at S37 (C11b) | 10 |
| **Total at S37 close** | **51** |

Documented in `04_backlog/v0_2_backlog_S37_C11a_C11b_additions.md` and
`04_backlog/v0_2_backlog_S36_additions.md` (carried).

---

## Status at S37 close

- 9 of 17 canonical components SHIPPED in code
- C11a v1.0 LOCKED in spec — code build pending (S38)
- C11b v1.0 LOCKED in spec — code build pending after C11a (S38+)
- Test suite: **2314 passed, 3 skipped**
- Backlog: 51 items
- Pre-launch hard gates: B-220 (hydraulics), B-222 (plumbing KB primary
  verification), B-150-equiv (NBC primary verification), B-237
  (cross-platform replay CI), B-NEW-J/K/L/P (upstream amendments)
- Master doc v3.12 delta complete

---

## Three-check protocol (Rule 10.6)

S37 hand-off protocol invoked at session close. All three checks run;
results in `05_integrity_check/` directory.

---

**End of v3.11 → v3.12 delta. S37 closed.**
