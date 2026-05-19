# C8 SPEC v1.1 AMENDMENT — COURTYARD arm corner-trim (LOCKED)

**Parent spec:** `02_specs_chronological/33_C8_SPEC_v0_6_LOCKED.md` (immutable; do not edit)
**Amendment authored:** S59 extended, 2026-05-19, Ramalingam + Claude
**Status:** LOCKED
**Closes:** `B-C8-LARGE-PLOT-COVERAGE`
**Bumps:** `C8_VERSION` minor — COURTYARD output geometry changes (arms ~w shorter), but all downstream consumers either accept the new geometry transparently or were previously broken on COURTYARD.

## Why this amendment exists

The S59 scenario corpus surfaced `delhi_60x90 + large_brief` (and any other COURTYARD-topology combo) consistently producing `CorridorSelfIntersectionError` (Inv 11). Root cause: each of COURTYARD's 4 LOOP_ARM segments was constructed to span the FULL envelope dimension (e.g. `south` arm: x ∈ [0, ew], y at south centerline ± w/2), and adjacent arms therefore overlapped at each of the 4 corners by a `w × w` square.

The parent spec's `dispatch_courtyard` carried this comment:

> For simplicity, each arm spans the full envelope dimension; junction overlap is handled at area-accounting time.

But Inv 11 validation runs BEFORE area accounting, and the validator's `_segments_share_endpoint` check returns False because the corner overlap point (e.g. `(east_centerline_x, south_centerline_y)`) is **not** an endpoint of either the south arm (which ends at `(ew, south_centerline_y)`) nor the east arm (which starts at `(east_centerline_x, 0)`). So the validator correctly rejects the overlap as a self-intersection, and EVERY COURTYARD-topology candidate fails Phase 3 validation.

## What changed

### `dispatch_courtyard` in `components/c08/topology_dispatch.py`

Each arm is now trimmed to meet the orthogonal arms' centerlines at the corners:

```
south arm:  (west_centerline_x, south_centerline_y) → (east_centerline_x, south_centerline_y)
east  arm:  (east_centerline_x, south_centerline_y) → (east_centerline_x, north_centerline_y)
north arm:  (east_centerline_x, north_centerline_y) → (west_centerline_x, north_centerline_y)
west  arm:  (west_centerline_x, north_centerline_y) → (west_centerline_x, south_centerline_y)
```

Adjacent arms now share endpoints exactly at the four corners:
- south.end == east.start at SE corner `(ew - w/2, w/2)`
- east.end == north.start at NE corner `(ew - w/2, ed - w/2)`
- north.end == west.start at NW corner `(w/2, ed - w/2)`
- west.end == south.start at SW corner `(w/2, w/2)`

Arm lengths drop by `w` (the corridor width):
- horizontal arms: `ew - w` (was `ew`)
- vertical arms: `ed - w` (was `ed`)

### What does NOT change

- L_SHAPE topology: already correct (primary and branch share the JUNCTION endpoint at `(junction_x, junction_y)` exactly).
- STRIP, T_SHAPE, MULTI_BRANCH, COURTYARD-with-no-corridor: no change required.
- Validator: unchanged — Inv 11 + Inv 12 logic was already correct; the dispatcher was producing geometrically invalid output that the validator was right to reject.
- Area accounting: arm-length reduction propagates naturally through C8 area calculations. The "saved" area (4 × w × w at corners) is correctly NOT double-counted now.

## Test surface

- All 228 C8 tests continue to pass with no modification (the previous strict-only COURTYARD validation already caught the bug; no test was asserting the broken-overlap output).
- `tests/test_orchestration/test_master_orchestrator_scenarios.py::test_scenario_pipeline_runs_end_to_end[delhi_60x90_large]` previously expected C8 phase to STUB-degrade via the orchestrator's `CorridorSelfIntersectionError` catch. With this amendment, C8 ships OK on Delhi+large. The scenario row should be flipped from `"c08_corridor"` → `None` (happy-path) to reflect the new behavior.

## Invariants

- **Inv 10 (envelope containment)** — unchanged. New arm bboxes are tighter, still inside envelope.
- **Inv 11 (no self-intersection)** — now satisfied. Adjacent arms share endpoints; non-adjacent arms (e.g. south + north) don't overlap because their centerlines are separated by `ed - w`.
- **Inv 12 (junction-only overlap)** — still allowed at the 4 shared corner endpoints.
- **Inv 13 (junction angles 0/90/180/270)** — corner junctions are 90° by construction.

## Cache key impact

C8 cache keys derived from corridor segment geometry will change for COURTYARD-topology candidates. v1.0 caches for COURTYARD were necessarily empty (every COURTYARD output raised before reaching cache), so there's no cache-replay break — but callers should not assume `c8_cache_key_v1.0(COURTYARD_input) == c8_cache_key_v1.1(COURTYARD_input)`.

## Replay determinism

Deterministic. Same input → same output. Arm centerline calculation is pure arithmetic on grid dimensions.

---

**End of C8 v1.1 AMENDMENT.**
