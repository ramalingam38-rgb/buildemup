# C10 SPEC v1.1 AMENDMENT — Phase 3 Relaxation Pass (LOCKED)

**Parent spec:** `02_specs_chronological/61_C10_SPEC_v1_0_LOCKED.md` (immutable; do not edit)
**Amendment authored:** S59 extended, 2026-05-19, Ramalingam + Claude
**Status:** LOCKED
**Closes:** `B-NEW-C10-PHASE3-CLUSTER-EXHAUSTION` (partial — see "What this does NOT fix")
**Bumps:** `C10_VERSION` minor → behavior may change for callers that previously caught `WetZoneInfeasibleError` on Phase-3 exhaustion.

## Why this amendment exists

The S59 scenario corpus surfaced two combos where C10 Phase 3 wall-assignment exhausted the strict-greedy search budget on small plots:

- `mumbai_30x40 + small_brief` — 1 candidate, 2 clusters (bathroom + kitchen), `states_explored=4` before exhaustion.
- `hyderabad_30x40 + small_brief` — same shape, same exhaustion.

Root cause: on small plots (30×40 ft → ~9 × 12 m), the wall segments produced by C7 are short, and the per-cluster `acceptable_wall_sets` (intersection of each member room's vastu/orientation/category-preferred walls) ends up with only 1–2 entries per cluster. When two clusters compete for the same one or two acceptable walls, the strict greedy can't satisfy both even with full backtracking.

The v1.0 LOCKED contract raised `WetZoneInfeasibleError` in this case, halting the wet-zone phase. v1.1 adds an OPT-IN-DEFAULT fallback: when the strict pass exhausts, retry once over the FULL grid-wall set (capacity remains a hard gate), emitting one `ForcedCultureOverride` per relaxed assignment so the consumer sees the trade.

## What changed

### Schema (`schema.py`)

- `WetZonePlanConfig.enable_relaxation_pass: bool = True` (NEW). Default True; v1.0 behavior recoverable by setting False.

### Algorithm (`assignment.py`)

`assign_clusters_to_walls` adds a third optional parameter `enable_relaxation_pass: bool = True`. When the strict greedy returns False:

1. **(If `enable_relaxation_pass=False`)** — raise `WetZoneInfeasibleError` as in v1.0. Error message gets a `(strict-only mode — set enable_relaxation_pass=True for AMENDMENT v1.1 fallback)` suffix.

2. **(If `enable_relaxation_pass=True`, the new default)** — retry the assignment over the FULL set of wall_ids in the grid. The relaxation pass:
   - Uses the same `_wall_score` ordering (best-scored wall first).
   - Uses the same `_wall_capacity_ok` capacity gate (capacity is a hard plumbing-engineering constraint, never relaxed).
   - Drops the `cluster_acceptable_walls` filter (the relaxation surface).
   - Honors a 4× generous state budget (`max_states * 4`) since the search space is much wider.
   - On success: for every cluster whose assigned wall falls OUTSIDE the strict acceptable set, append a `ForcedCultureOverride(room_id, wall_id, category, rejected_alternatives=(strict_set_members, "strict_acceptable_set_infeasible"))`. Downstream consumers (C16 renderer, C15 problem-finder) read `forced_culturally_discouraged` and can surface a "we placed your bathroom on a non-ideal wall because no better option fit" flag in the UI.
   - On failure: raise `WetZoneInfeasibleError` as before, with `(relaxation pass also failed)` suffix.

### Wiring (`wet_zone_planner.py`)

`plan_wet_zones` now passes `enable_relaxation_pass=config.enable_relaxation_pass` through to the assignment call. No other call sites change.

### Orchestrator (`orchestration/master_orchestrator.py`)

No change required — the orchestrator's existing `BatchWetZoneInfeasibleError` graceful-downgrade still fires when even the relaxation pass fails. On Mumbai/Hyderabad 30×40 + small_brief, the relaxation does NOT succeed (the binding constraint is 3m minimum riser spacing per NBC vs ~3m wall lengths, not the acceptable-set filter) — the orchestrator still STUB-degrades but the error message is now more informative.

## What this does NOT fix

The Mumbai 30×40 + small_brief case still fails C10 because **minimum riser spacing is 3.0 m and the wall segments are also ~3 m**, leaving wall_capacity = 1 riser. A bathroom cluster with WC + basin + shower needs capacity ≥ 3. Capacity is a hard NBC plumbing-engineering constant, NOT a wall-scoring or vastu-preference issue. Three options exist for that case, all of which require domain input outside this amendment:

1. **Reduce `minimum_riser_spacing_m`** from 3.0 to (e.g.) 1.5 — requires plumbing-engineer (B-220) review. May violate NBC 2016 § 9.2.
2. **Allow inter-cluster wall sharing** with explicit pipe-routing — requires plumbing layout algorithm work.
3. **Reject the brief at C2 feasibility** when the plot is too small for the wet-room program — clean UX, requires C2 spec extension.

This amendment unblocks the "tight on acceptable walls but otherwise fine" case (which is the common one on larger small plots); the "tight on capacity" case remains as `B-C10-CAPACITY-CONSTRAINT-TIGHTNESS` for B-220 follow-up.

## Test surface

- `tests/test_c10/test_wet_zone_amendment_relaxation.py` (NEW) — see `tests/test_orchestration/test_master_orchestrator_scenarios.py` for the orchestrator-level coverage that already exists.
- All pre-amendment C10 tests pass unchanged because the relaxation only fires on strict failure (no behavior change for cases that previously succeeded).

## Invariants

- **Inv 17 (capacity)** unchanged — capacity is a hard gate in both passes.
- **NEW Inv 21**: If `enable_relaxation_pass=True` AND strict pass succeeds, output IS byte-identical to v1.0. (The relaxation is dead code on the happy path.)
- **NEW Inv 22**: If the relaxation pass succeeds, `forced_culturally_discouraged` contains AT LEAST one entry whose `rejected_alternatives` carries the marker `"strict_acceptable_set_infeasible"`. Downstream consumers can detect "relaxation was used" via this marker without needing a new field on `AssignmentResult`.

## Replay determinism

The relaxation pass is deterministic: walls are sorted by `(-score, wall_id)` (same key as the strict pass), explored depth-first with backtracking, and the success path is the lex-first feasible assignment over the full wall set. Same inputs → same output.

## Cache key impact

`WetZonePlanConfig.enable_relaxation_pass` participates in the C10 cache key (cache_relevant=True implicitly via the dataclass field). Callers running with `enable_relaxation_pass=True` get a different cache namespace than `=False`, so prior-cache replays remain byte-stable.

---

**End of C10 v1.1 AMENDMENT.**
