# C8 S33 patch summary

12 patches landed; all 1988 tests pass.

## Per-patch what/where/result

### B-142 — Centralize tolerance policy
**Files**: NEW `tolerances.py` (99 lines); imports added in `spatial_model.py`, `area_accounting.py`, `junction_propagation.py`, `width_selection.py`, `schema.py`.
**Change**: Three named tiers replace scattered magic numbers — `STRUCTURAL_M=1e-3` (coordinate matching), `GEOMETRIC_M=1e-6` (ratios/scores), `ARITHMETIC_M=1e-12` (FP round-off). Plus `epsilon_m_for(stage)` helper.
**Replaced**: 12 sites of bare `1e-9`/`1e-12`/`1e-6` literals.
**Tests**: 782/782 validation pass.

### B-131 — N-aware `resolve_taper_zone_m()`
**Files**: `width_selection.py` (signature change, default `n_tapered_ends=1` preserves v0.5 length/2 semantics for bare callers).
**Change**: `max_allowed = length / (2 × max(1, n_tapered_ends))`. Implements C8 SPEC v0.6 PROPOSED math.
**Replaced**: previous `max_allowed = length / 2` (which under-bounded N=2 cases by 50%).
**Tests**: 4 taper tests at 782/782.

### B-141 — Cap junction propagation taper accumulation
**Files**: `junction_propagation.py`.
**Change**: pre-pass counts tapered ends per segment; `taper_zone_m = min(max(seg.taper_zone_m, taper_m), length / (2 × max(1, n_tapered)))`.
**Replaced**: unbounded `taper_zone_m = max(seg.taper_zone_m, taper_m)`.
**Side benefit**: rule_trace records `_n=N`, `_truncated`, `_capped` markers for debugging.
**Tests**: 782/782.

### B-133 — Typed `CorridorSelfIntersectionError` on Inv 11
**Files**: `validator.py` (raise site), `tests/validation/test_c8_validator.py` (1 test updated), `tests/validation/test_c8_spatial_feasibility.py` (1 test updated).
**Change**: replace generic `ValueError` with typed `CorridorSelfIntersectionError(message, segment_a_index, segment_b_index, overlap_box)`.
**Tests**: 782/782 (2 tests updated to expect typed exception per S33 marker).

### B-135 — Propagate upstream trace IDs
**Files**: `corridor_designer.py` (new `_upstream_trace_ids()` helper; 2 call sites updated for has-corridor / no-corridor branches).
**Change**: read `oriented_candidate.orientation.provenance.plot_analysis_trace_id` instead of synthesizing fake `_trace_id("c6cand", started_at)`.
**Followup**: C7 Grid carries no trace_id field today; synthesized fallback used for grid_trace_id (filed as B-NNN-grid-trace).
**Tests**: 782/782.

### B-137 — Tag BAND_ATTACHMENT endpoints
**Files**: `topology_dispatch.py` (new `_resolve_band_attachment()` + `_band_attachment_endpoint()` helpers; 4 dispatchers updated: strip_linear, central_spine [2 endpoints], l_shape branch).
**Change**: every BAND_ATTACHMENT endpoint now carries `(attached_band, attached_direction, attached_envelope_id)` derived by centroid-distance projection onto envelope tuple.
**Replaced**: bare `CorridorEndpoint(kind=BAND_ATTACHMENT, point_m=…)` with all metadata-fields=None.
**Surfaced**: B-144 (Inv 6 was vacuously passing pre-B-137).

### B-144 — Inv 6 semantic correction (surfaced by B-137)
**Files**: `validator.py` (Inv 6 check rewritten).
**Change**: Inv 6 now uses bay-proximity adjacency: each present required band (PUBLIC/SERVICE/PRIVATE) must have ≥1 corridor segment within `max(bay_x_m, bay_y_m)` of its envelope. Replaces "≥1 BAND_ATTACHMENT endpoint per band" which was structurally incompatible with through-pass topologies (a 1-segment linear corridor cannot have 3 endpoints).
**Why**: corridor segments run *between* zone bands, not *through* them. Strict endpoint-tagging vacuously passed pre-B-137 and spuriously fired post-B-137; bay-proximity is the architecturally correct semantic.
**Tests**: 782/782.

### B-134 — § 4.7 junction-snap normalization
**Files**: `topology_dispatch.py` (new `snap_junctions()` function), `corridor_designer.py` (step 4.5 inserted between dispatch and propagation).
**Change**: idempotent canonical-coord enforcement at every JUNCTION endpoint. Pass 1: bucket JUNCTION endpoints by quantized key, store first-seen as canonical. Pass 2: replace every JUNCTION coord with canonical, leaving non-JUNCTIONs alone.
**Why**: prevents EPSILON_M-scale drift from accumulating across multi-segment paths. No-op for v1 dispatchers (which already use coincident tuples), but defense-in-depth for future composite paths.
**Tests**: 782/782 (rule_trace now records `junctions_snapped`).

### B-132 — Real grid-alignment measurement
**Files**: `corridor_designer.py` (new `_measure_grid_alignment()` function, `_build_grid_alignment_report()` rewritten; signature now takes `segments + grid` instead of `n_segments`).
**Change**: per segment, compute the two wall-edge perpendicular coords (centerline ± width/2) and check against actual grid lines from `derive_grid_lines(grid)`. Track tapered_edges separately per Inv 17.
**Replaced**: hardcoded `1.0`/`0.9`/`0.0` per quantization mode regardless of actual snap state.
**Surfaced**: real measurement reveals 0/N edges align in canonical test pipeline (confirms walk #1 Finding #4 with concrete numbers; previously hidden behind constants).
**Side note**: filing **B-145** as followup — the spec's GRID_FRACTIONS quantization controls *width*, not *placement*; achieving real grid-alignment requires placement-aware dispatch, which the current envelope-center placement does not provide.
**Tests**: 782/782 (existing tests asserted score-bounds [0, 1], not exact-1.0, so they still pass with real measurement).

### B-136 — § 4.3.1 envelope-overflow narrowing
**Files**: `width_selection.py` (`select_grid_fraction_width()` and `select_corridor_width()` both gain `envelope_dim_m` parameter), `corridor_designer.py` (step 3 passes `envelope_dim_m=min(envelope_width_m, envelope_depth_m)`).
**Change**: when scored width would overflow envelope, narrow to next-smaller eligible GRID_FRACTION. Raise `CorridorTooNarrowError(B-109)` only when even smallest exceeds envelope.
**Replaced**: scored width was final regardless of envelope-fit; validator caught Inv 10 violations after the fact with generic ValueError.
**Tests**: 782/782.

### B-138 — ENTRY_STUB construction for CENTRAL_SPINE
**Files**: `topology_dispatch.py` (`dispatch_central_spine()` rewritten with case-(a)/case-(b) branches).
**Change**: when `plot.facing` is perpendicular to `spine_axis_facing`, build a 3-segment path: ENTRY_STUB (from facing-edge to spine, perpendicular to spine, width = `config.entry_stub_width_m`) + SPINE_A (from spine_start to junction) + SPINE_B (from junction to spine_end). When `plot.facing` aligns with spine axis, retain v0.5 single-spine ENTRY behavior.
**Replaced**: v0.5's "v1 ships as just the spine (no entry stub yet)" no-op for case (b).
**Tests**: 782/782 (existing tests use case-(a)-aligned configurations).

### B-143 — Convert "assumed-by-construction" Inv 14 to explicit check
**Files**: `validator.py`.
**Change**: every grid line returned by `derive_grid_lines(grid)` must have a supporting column at the same coordinate within `epsilon_m`. Defense-in-depth against future refactors that introduce non-column reference lines.
**Replaced**: `# Satisfied by construction in derive_grid_lines() (§ 4.2). Defensive check skipped here`.
**Tests**: 782/782.

## Code-size delta

| Module | Pre-S33 | Post-S33 | Δ |
|---|---|---|---|
| `__init__.py` | 72 | 72 | 0 |
| `errors.py` | 113 | 113 | 0 |
| `tolerances.py` | — | 99 | NEW |
| `schema.py` | 709 | 710 | +1 |
| `spatial_model.py` | 245 | 250 | +5 |
| `grid_alignment.py` | 111 | 111 | 0 |
| `width_selection.py` | 185 | 281 | +96 |
| `junction_propagation.py` | 213 | 244 | +31 |
| `area_accounting.py` | 485 | 490 | +5 |
| `topology_dispatch.py` | 528 | 816 | +288 |
| `validator.py` | 394 | 464 | +70 |
| `corridor_designer.py` | 361 | 498 | +137 |
| **TOTAL** | **3,416** | **4,148** | **+732 (+21%)** |

## New backlog from this session

- **B-145** (NEW): GRID_FRACTIONS quantizes width but does not guarantee placement-on-grid-line; corridor centerline is at envelope-center which has no grid-alignment relationship. Spec amendment candidate; B-132 measurement revealed this.
- **B-NNN-grid-trace** (NEW): C7 Grid lacks a `trace_id` field; B-135 falls back to synthesized for grid_trace_id. Add `Grid.provenance.trace_id` in C7 next refactor.

## Tests updated for typed-exception transition

Two tests updated for B-133 typed exception (these are not regressions — the previous `ValueError`-catching tests asserted the *unintended* generic behavior):
- `tests/validation/test_c8_validator.py::test_inv_11_self_intersection`
- `tests/validation/test_c8_spatial_feasibility.py::test_overlapping_non_adjacent_segments_caught_by_validator`

Both now expect `CorridorSelfIntersectionError` per § 6 / § 14.17 spec contract.

Plus 3 taper tests fixed automatically when default `n_tapered_ends=1` was chosen (preserved v0.5 `length/2` for bare callers).

## Final test result

```
1988 passed, 1 skipped, 1415 warnings, 52 subtests passed in 55.73s
```
