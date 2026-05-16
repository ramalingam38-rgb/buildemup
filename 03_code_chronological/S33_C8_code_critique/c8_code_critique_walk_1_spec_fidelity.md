# C8 Code Critique — Walk #1 (Spec Fidelity)

**Authoring session**: S33
**Subject**: `buildemup/components/c08/` (10 modules, 3,416 lines)
**Spec under review**: `26_C8_SPEC_v0_5_LOCKED.md` (the LOCKED spec at the time C8 SHIPPED at S32)
**Walk type**: code-critique walk #1 of 3 (D-066 step 7 retroactive — never run on C8 before)
**Test baseline at critique time**: 174 C8 tests passing within the 1988-test suite

This walk asks one question: **does the production code actually implement what the LOCKED spec says it does?** Walks #2 and #3 (code quality, test coverage adequacy) are deferred to subsequent rounds.

Format: each finding has a verdict (per Rule 7 vocabulary):
- **VALID-DEFECT** — code deviates from spec; needs code patch (or spec amendment if the spec is wrong)
- **VALID-BUT-BACKLOG** — deviation acknowledged; out-of-scope this build; file as B-NNN
- **MISFRAMED** — apparent deviation that's actually correct on closer reading
- **DOCUMENTED** — deviation matches what the spec already says is acceptable

Per Rule 9.2, every VALID-BUT-BACKLOG item is filed at end of walk. Per Rule 7, ≥1 web search performed (architectural gridline-alignment convention; result documented in Finding #4).

---

## Pre-touch inventory (Rule 10.6.1)

Pre-existing at S33 walk #1 open:
- 10 C8 production modules (3,416 lines total) — read-only artifacts of the v0.5 LOCKED build at S32.
- C8 SPEC v0.5 LOCKED (1,712 lines) in v9 bundle 02_specs_chronological/.
- 174 C8 tests in `tests/validation/` — not modified during this walk.
- B-129 already filed (S32) and resolved-in-spec at C8 v0.6 PROPOSED (S33 earlier this session).
- B-130 already filed (S33 earlier) for sweep-line refactor.
- B-131 already filed (S33 earlier) for n_tapered_ends threading.

This walk surfaces **new** findings beyond B-129/B-130/B-131. Pre-existing items are referenced when relevant but not re-counted.

---

## Summary of findings

11 new findings surfaced in this walk:

| # | Finding | Verdict | Severity |
|---|---|---|---|
| 1 | `find_edge_snap_pair()` defined but never called from production | VALID-DEFECT | HIGH |
| 2 | `CorridorSelfIntersectionError` imported but never raised | VALID-DEFECT | MEDIUM |
| 3 | § 4.7 junction-snap step has no implementation | VALID-DEFECT | MEDIUM |
| 4 | `GridAlignmentReport` is fabricated, not measured | VALID-DEFECT | HIGH |
| 5 | `tapered_edges_count` always 0; Inv 17 vacuously satisfied | VALID-DEFECT | MEDIUM |
| 6 | Trace IDs synthesized at C8-time, not propagated from upstream | VALID-DEFECT | MEDIUM |
| 7 | § 4.3.1 constrained-plot override (envelope-overflow narrowing) absent | VALID-DEFECT | MEDIUM |
| 8 | BAND_ATTACHMENT endpoints never populated with `attached_band` | VALID-DEFECT | HIGH |
| 9 | `ENTRY_STUB`, `STAIR_ATTACHMENT`, `DEAD_END` enum members defined but never instantiated | VALID-BUT-BACKLOG | LOW |
| 10 | `entry_stub_width_m` config field defined but never read | VALID-BUT-BACKLOG | LOW |
| 11 | Validator skips Inv 14 (column-supported snap-lines) entirely | VALID-DEFECT | LOW |

Plus pre-existing findings already in backlog:
- B-129 (RESOLVED-IN-SPEC C8 v0.6 PROPOSED) — Inv 20 vs § 4.3.1 inconsistency.
- B-130 — sweep-line union vs 1cm rasterization shortcut.
- B-131 — `n_tapered_ends` not threaded through `resolve_taper_zone_m()` callers.

**Headline**: 8 new VALID-DEFECTs (3 HIGH, 4 MEDIUM, 1 LOW), 2 VALID-BUT-BACKLOG (LOW), 1 partially-MISFRAMED (Finding #4 — see analysis). The HIGH-severity defects mean three spec invariants (6, 14, the alignment reporting contract) are effectively unenforced in production; the corridor designer ships passing tests that don't cover the unenforced paths.

---

## Module-by-module review

### Module 1: `errors.py` (113 lines)

**Verdict**: SPEC-FIDELITY-MOSTLY-OK.

`CorridorTooNarrowError`, `CorridorSelfIntersectionError`, `CorridorDispatchError` defined per § 6 / § 14.17 / § 14.23. Diagnostic-metadata fields match § 14.23 enrichment (candidate_index, topology_kind, failure_phase, suggested_alternative_topologies).

**See Finding #2** below: `CorridorSelfIntersectionError` is *defined* correctly but never *raised* anywhere. The class itself is fine; the gap is at the raise site (which lives in topology_dispatch / corridor_designer), not in errors.py.

---

### Module 2: `schema.py` (709 lines)

**Verdict**: SPEC-FIDELITY-MOSTLY-OK; one DOCUMENTED-DEVIATION already covered by B-129/B-129's resolution at C8 v0.6 PROPOSED.

The schema dataclasses correctly model the spec § 3 contract:
- All 5 enums (CorridorSegmentKind, CorridorEndpointKind, WidthQuantization, WidthPropagation, ConsumptionBand) match § 3 / § 4.9.
- All 8 dataclasses (ZoneBandEnvelope, CorridorEndpoint, CorridorSegment, GridAlignmentReport, CorridorDesignConfig, CorridorProvenance, CorridorPath, CorridorDesignedCandidate) frozen + immutable per spec.
- `CorridorSegment.__post_init__` enforces all the per-segment invariants: axis-alignment (Inv 3), positive widths/length, Inv 16 (per-side taper bound), Inv 20 (constant_middle ≥ length/2 N-aware).
- `CorridorPath.__post_init__` enforces the has_corridor / segments-empty consistency.
- `CorridorProvenance.__post_init__` enforces the area_fraction range.

The only spec-vs-code deviation in schema is the **N-aware `constant_middle_length_m` formula** (lines 379-387) — code already counts only actual tapers, while spec § 3 / Inv 20 (v0.5 LOCKED) text says `length - 2 × taper_zone_m` always. This is the B-129 deviation, formally documented as deviation Δ.4 in master doc v3.7 at S32 close, and now resolved in spec at C8 v0.6 PROPOSED (drafted earlier this session). **Verdict: DOCUMENTED-AND-RESOLVED**.

Minor: schema Inv 16 enforcement at line 350 uses `length_m / 2.0 + eps` as the per-side bound (one-side limit). For N=2 segments this is a *looser* bound than necessary — Inv 20 will catch the tighter `length / 4` requirement at line 360-368. Both invariants are enforced; the per-side bound (Inv 16) is not the binding constraint for N=2 cases; Inv 20 is. This matches the spec semantics. **Verdict: MISFRAMED — code is correct.**

---

### Module 3: `spatial_model.py` (245 lines)

**Verdict**: SPEC-FIDELITY-PARTIAL.

`derive_zone_band_envelopes()` implements § 4.0 directional-strip model with corner-overlap resolution (§ 14.10) — strips are placed by direction, then overlaps are resolved by `band_priority_order`. The implementation is complete for the spec's algorithm.

The pairwise overlap-resolution loop (lines 131-207) is O(n²) with n ≤ 4 strips, which is fine for v1. Tie-break on equal priority falls back to lexicographic on band name (line 156), matching § 4.0 spec text.

Clipping logic for N/S strips clips along x; E/W strips clip along y (lines 166-207). This preserves each loser strip's intended axis. A defensive fallback (lines 175-184, 199-205) handles "interior overlap" — the comment correctly says "should not happen with cardinal strips" but the code keeps the path. This is acceptable defensive programming.

**No spec deviations found in this module.**

---

### Module 4: `grid_alignment.py` (111 lines)

**Verdict**: PARTIAL-DEFECT — see Finding #1.

`derive_grid_lines(grid)` correctly implements § 4.2 / § 14.9 — derives lines from columns; the v0.1 phantom `column_lines_x/y` issue is fixed. Sorted, deduplicated. Matches spec.

`edge_snap_choice_score()` and `find_edge_snap_pair()` correctly implement § 4.2.1 envelope-symmetry secondary criterion. Score function combines primary (target-centerline distance) + secondary (envelope-symmetry weighted by `envelope_symmetry_weight`).

**However**: see Finding #1 — these two functions are dead code. They're never called from `corridor_designer.py` or `topology_dispatch.py`. The `WidthQuantization.NEAREST_GRID_LINE` mode (handled in `width_selection.py:select_corridor_width()` line 134-139) returns target_width without snapping; the comment claims "caller (corridor_designer) must combine with edge-snap to derive the actual width" — but `corridor_designer.design_one_corridor()` takes the returned width as final and never invokes `find_edge_snap_pair()`. The whole edge-snap algorithm in § 4.2 is unreachable in production.

---

### Module 5: `width_selection.py` (185 lines)

**Verdict**: PARTIAL-DEFECT — see Finding #7.

`width_selection_score()` implements § 4.3 / § 14.19 asymmetric penalty correctly: under-comfort × 2.0, over-comfort × 1.0, regulatory-violating returns inf.

`select_grid_fraction_width()` correctly: picks bay_min, builds 5 GRID_FRACTION_CANDIDATES, filters to ≥ regulatory_min, scores, picks min. Raises `CorridorTooNarrowError` if no eligible candidate. Matches § 4.3 + § 14.19.

`resolve_taper_zone_m()` matches § 4.3.1 v0.5 spec text (`max_allowed = length / 2`). The N-aware fix is in B-131 / C8 v0.6 PROPOSED. **Verdict: DOCUMENTED — already in backlog as B-131.**

**However**: see Finding #7 — § 4.3.1 mandates "Constrained-plot override: if the chosen quantized width pushes corridor outside the buildable envelope (envelope-overflow check at § 4.7 invariant 10), narrow to next-smaller GRID_FRACTION candidate." No implementation. `select_grid_fraction_width()` picks the scored width once; no envelope-overflow recheck; no narrowing-on-overflow path. If the chosen width does cause an Inv 10 violation, the validator raises a generic `ValueError` with the Inv 10 message — but the typed retry/narrow-to-smaller path is missing.

---

### Module 6: `junction_propagation.py` (213 lines)

**Verdict**: SPEC-FIDELITY-MOSTLY-OK.

Three propagation modes implemented per § 4.10:
- `INDEPENDENT_WIDTHS`: no propagation; logs step discontinuity. Matches spec.
- `GLOBAL_MAX_INHERITANCE`: each adjoining segment inflates entirely to junction_max. Matches spec.
- `JUNCTION_LOCAL_ONLY` (default): junction-end gets junction_max; constant middle stays at constant_width_m. Matches spec.

The `_coord_key()` quantization at half-epsilon is a clean way to handle coordinate matching. Junction index is built once and reused.

The `taper_zone_m=max(seg.taper_zone_m, taper_m)` pattern at lines 193, 199 is a small defensive choice — preserves the larger of any pre-existing taper. Reasonable.

**However**: `resolve_taper_zone_m()` is called with the v0.5 single-arg signature (no `n_tapered_ends`). The pre-existing B-131 captures this; the resolution after C8 v0.6 LOCK will thread N through. **Verdict: DOCUMENTED — already in backlog as B-131.**

The propagation correctly handles the "segment width matches junction_max already" case (lines 168-180) — no taper needed, just set the junction-end width explicitly to satisfy Inv 18.

---

### Module 7: `area_accounting.py` (485 lines)

**Verdict**: SPEC-FIDELITY-PARTIAL — already covered by B-130 (sweep-line vs rasterization shortcut). New finding within this module:

The `decompose_segment()` function at lines 174-350 has a deeply concerning code section at lines 240-348 (the y-axis transpose path for N/S segments with right-triangles). The 100+ lines of inline comments explicitly admit:

> "we accept a small approximation here and will validate against the spec's 6 verification cases."
> "we use the simpler path: keep the primitive in its original abstraction (x-parametric), as if its world axes were already aligned."
> "for mixed-axis cases (junctions of perpendicular segments), the sweep-line falls back to a rasterization-based rectified union."

The downstream union-area function `polygon_union_area_m2()` doesn't *use* a sweep-line at all — it goes directly to `_rasterized_union_area()`. So the transpose-axis confusion in `decompose_segment()` is moot for the area calculation (rasterization tests every cell against every primitive's `_point_in_primitive()`, which handles the transpose correctly via `t = (x - p.x_min) / dx` linear interpolation regardless of axis).

But the *primitives returned* from `decompose_segment()` for N/S segments are geometrically wrong as standalone objects (the right-triangle's bounding box and y_lo/y_hi semantics don't survive the transpose cleanly). They happen to give the right answer through `_point_in_primitive()` because that function uses the *original* parametric semantics regardless of intended world axis — but if any other code consumes these primitives directly (e.g., a future sweep-line refactor), the transpose path is a landmine.

**Verdict: VALID-BUT-BACKLOG-OVERLAP** — partially overlaps B-130 (which mandates a sweep-line refactor that would need to fix this transpose path properly). Adding to the B-130 entry as a clarification rather than filing a new B-NNN. See "Backlog updates" section below.

---

### Module 8: `topology_dispatch.py` (528 lines)

**Verdict**: SPEC-FIDELITY-PARTIAL — see Findings #8, #9.

`dispatch_strip_no_corridor()`: returns empty tuple. Matches § 4.1 + § 4.3.2.

`dispatch_strip_linear()`: builds single PRIMARY segment between facing edge and opposite edge, ENTRY at facing end. Matches spec.

`dispatch_central_spine()`: builds single PRIMARY through envelope center; ENTRY at one end if `plot_facing == spine_axis_facing`, else BAND_ATTACHMENT. Matches partially — see Finding #9 (no ENTRY_STUB segment is created; spec § 4.1 mentions one).

`dispatch_l_shape()`: PRIMARY arm + BRANCH arm meeting at JUNCTION at envelope center. Matches spec geometry-wise. **However**: `branch_facing` is hardcoded (line 282 `PlotOrientation.NORTH` arbitrarily; line 288 `PlotOrientation.EAST` arbitrarily). The spec says "BRANCH runs perpendicular" — the choice between N/S (when PRIMARY runs E/W) is left to "arbitrary", which is a real implementation gap (the branch direction should be informed by which band's envelope it serves, not picked arbitrarily). **Verdict: VALID-BUT-BACKLOG (LOW; this is a refinement not a defect; v1 plans pass tests but second-band alignment is suboptimal).**

`dispatch_courtyard()`: 4 LOOP_ARM segments around envelope perimeter at width/2 inset. ENTRY assigned to the arm matching `plot_facing`. Matches spec § 4.1 + § 4.0 courtyard variant.

`dispatch_topology()`: dispatches on `TopologyKind` correctly; raises `CorridorDispatchError(B-126)` for L_SHAPE with insufficient cardinal directions in `refined_zone_bands`. The defensive `if len(directions) < 2` check at line 495 matches § 6 row.

**Critical Finding #8**: every `BAND_ATTACHMENT` endpoint in every dispatcher is constructed without `attached_band` or `attached_envelope_id`. Spec § 4.4 mandates: "BAND_ATTACHMENT: ... `attached_band` = band, `attached_direction` = direction, `attached_envelope_id` = index into the path's `envelopes` tuple." Code only sets `kind` and `point_m`. Validator Inv 6 (line 352-373) checks `bands_with_attachments` derived from `ep.attached_band` — silently passes because the set is always empty. So Inv 6 ("PUBLIC, SERVICE, PRIVATE bands each have ≥ 1 BAND_ATTACHMENT") is vacuously satisfied.

---

### Module 9: `validator.py` (394 lines)

**Verdict**: SPEC-FIDELITY-PARTIAL — see Findings #5, #11.

The validator implements 14 of the 20 invariants explicitly. Per spec § 4.6:
- ✓ Inv 1 (segments is tuple) — line 122
- ✓ Inv 3 (axis-aligned cardinal) — line 130
- ✓ Inv 4 (geometric connectivity) — line 153 (pairwise near-but-not-coincident check)
- ✓ Inv 5 (at most one ENTRY) — line 169
- ✓ Inv 8 (connectivity_type type) — line 183
- ✓ Inv 10 (envelope containment) — line 190 (raises generic ValueError; see Finding #7)
- ✓ Inv 11 (no self-intersection) — line 204 (raises generic ValueError; see Finding #2)
- ✓ Inv 12 (junction-only overlap) — same loop, line 211 (allows endpoint-sharing pairs)
- ✓ Inv 13 (junction angle) — line 226 (computes pairwise angles at each junction)
- ✗ Inv 14 (column-supported snap-lines) — line 281 explicitly skipped: "Satisfied by construction in derive_grid_lines() (§ 4.2). Defensive check skipped here — no separate snap-line registry to validate." **See Finding #11.**
- ✓ Inv 15+18 (junction-width equality) — line 287 (skipped when INDEPENDENT_WIDTHS)
- ✓ Inv 16 (per-side taper bound) — line 304 (also enforced in __post_init__)
- ⚠ Inv 17 (tapered-edge geometric exclusion) — line 313 effectively no-ops; `tapered_edges_count + edges_aligned_count > edges_total_count` check is guarded with `pass`. **See Finding #5.**
- (vacuous) Inv 19 (taper monotonicity) — line 326 vacuously satisfied because the model is linear by construction
- ✓ Inv 20 (constant_middle_length) — line 330 (also enforced in __post_init__)

HAS-CORRIDOR-ONLY:
- ✓ Inv 2 (widths ≥ regulatory) — line 339
- ⚠ Inv 6 (band attachments) — line 352, vacuously satisfied due to Finding #8
- ✓ Inv 7 (CIRCULATION has no envelope) — line 376
- ✓ Inv 9 (≥ 1 ENTRY when has_corridor) — line 384

**Inv 11 / Inv 12 raise `ValueError`, not `CorridorSelfIntersectionError`** — see Finding #2.

The pairwise-overlap test at line 208 uses `_bboxes_overlap()` with strict overlap (touching does not count); endpoint-sharing pairs are allowed to overlap (Inv 12). The comment at line 213-217 acknowledges that "rigorous junction-locality check at validator time is over-strict given taper zones; rely on construction-time correctness (§ 4.7 spatial-feasibility checks)" — but **§ 4.7 spatial-feasibility checks are not implemented anywhere** (see Finding #3). So junction-locality is *unenforced* in either path.

---

### Module 10: `corridor_designer.py` (361 lines)

**Verdict**: SPEC-FIDELITY-PARTIAL — see Findings #4, #6.

The orchestrator `design_one_corridor()` follows the 11-step sequence (envelopes → has_corridor decision → width → dispatch → propagate → area → consumption_band → grid_alignment_report → CorridorPath → validator → provenance). Step ordering matches § 5 + § 4.x.

`design_corridors()` does the right input-validation + position-paired iteration; raises `NotImplementedError(B-066)` for non-rectangular shape; passes `candidate_index` through for diagnostic context.

**Critical Finding #4** at lines 83-120 (`_build_grid_alignment_report`): the function fabricates `GridAlignmentReport` rather than measuring actual grid alignment. For `GRID_FRACTIONS`: edges_total = 2 × n_segments, edges_aligned = edges_total (always equal), grid_alignment_score = 1.0 (always). For `NEAREST_GRID_LINE`: 0.9 always. For `NONE_FREE_WIDTH`: 0.0 always. None of these inspect the actual segment positions vs grid lines. The report's value as a downstream signal is zero; downstream consumers reading `grid_alignment_score` get the same number for all candidates of the same quantization mode.

**Finding #6** at lines 74-76 (`_trace_id`): synthesizes trace IDs by milliseconds-since-epoch-mod-10^9. The spec § 10 (Provenance) says `oriented_candidate_trace_id` should reference the upstream — i.e. `oriented_candidate.orientation.provenance.plot_analysis_trace_id` — for cross-component correlation. Code's fake IDs break that correlation.

---

## Detailed findings

### Finding #1 — `find_edge_snap_pair()` defined but never called

**Verdict**: VALID-DEFECT.
**Severity**: HIGH (an entire spec algorithm — § 4.2 edge-snap with envelope-symmetry tie-break — is unreachable in production).
**Spec reference**: § 4.2 + § 4.2.1.
**Code locations**:
- `grid_alignment.py:60` — `find_edge_snap_pair()` defined.
- `width_selection.py:134-139` — `WidthQuantization.NEAREST_GRID_LINE` returns target width with comment "caller must combine with edge-snap" but no caller does.
- `corridor_designer.py:176-181` — `select_corridor_width()` is called; the returned width is treated as final.

**Evidence**:
```bash
$ grep -rn "find_edge_snap_pair\(" buildemup/components/c08/ | grep -v __pycache__
buildemup/components/c08/grid_alignment.py:9:  - ``find_edge_snap_pair(...)``
buildemup/components/c08/grid_alignment.py:60:def find_edge_snap_pair(
buildemup/components/c08/width_selection.py:11:  - NEAREST_GRID_LINE: caller-driven; uses grid_alignment.find_edge_snap_pair.
```
Definition + comment-only references. Zero call sites.

**Why it matters**: when `width_quantization == NEAREST_GRID_LINE`, the code returns a target width that's *not* snapped to any actual grid line. Callers using NEAREST_GRID_LINE think they're getting grid-snapped widths; they're getting un-snapped widths. The 1.0 default `grid_alignment_score` for GRID_FRACTIONS (Finding #4) means GRID_FRACTIONS doesn't snap either — the fractional widths happen to fall on grid lines because the algorithm uses `f × bay_min`, not because any snap was performed.

**Recommended fix**:
- (a) Wire `find_edge_snap_pair()` into the NEAREST_GRID_LINE path of `select_corridor_width()`.
- (b) Update `_build_grid_alignment_report()` to track per-segment edge-snap state and report real numbers.
- (c) Add tests that assert NEAREST_GRID_LINE actually snaps.

**Code patch effort**: M (~3-4 hours).

---

### Finding #2 — `CorridorSelfIntersectionError` imported but never raised

**Verdict**: VALID-DEFECT.
**Severity**: MEDIUM (typed exception path advertised in errors.py + corridor_designer.py docstring exists but is unreachable; raises happen as generic ValueError).
**Spec reference**: § 6 + § 14.17.
**Code locations**:
- `errors.py:50` — class defined.
- `corridor_designer.py:38` — imported.
- `corridor_designer.py:309` — listed in docstring as raisable.
- `validator.py:219` — Inv 11 violation raises `ValueError`, not the typed exception.

**Evidence**:
```bash
$ grep -rn "raise CorridorSelfIntersectionError\b" buildemup/ | grep -v __pycache__
(no output)
```
Class is imported into corridor_designer; never raised anywhere.

**Why it matters**: callers expecting the typed exception (per § 6 spec contract) will receive `ValueError` instead and won't be able to catch-and-recover specifically. The advertised exception type is part of the public API surface.

**Recommended fix**: replace the `ValueError` raise at validator.py:219 with `CorridorSelfIntersectionError` (carrying segment_a_index, segment_b_index, overlap_box per the class signature).

**Code patch effort**: S (~30 minutes).

---

### Finding #3 — § 4.7 junction-snap step has no implementation

**Verdict**: VALID-DEFECT.
**Severity**: MEDIUM (spec mandates an explicit construction-time normalization; code lacks it).
**Spec reference**: § 4.7 explicitly says: "Junction snap: at every JUNCTION, after both adjoining segments are placed, force junction endpoint to exact coordinates `(min(start1.x, end2.x), min(start1.y, end2.y))` or equivalent — prevents EPSILON_M-scale drift from accumulating across multi-segment paths."
**Code locations**: nothing in the C8 codebase implements this step. `topology_dispatch._dispatch_l_shape` constructs junction endpoints directly with the same `(junction_x, junction_y)` tuple for both segments (so they're already coincident by construction in this case), but the spec's normalization step would also handle paths constructed across multiple sub-functions or future modifications.

**Why it matters**: the current correctness depends on every dispatcher using exact-same-tuple construction. Any refactor that introduces independent endpoint construction would cause silent EPSILON_M drift accumulation. The spec's prescribed normalization is a safety net; it's missing.

**Recommended fix**: add a `_snap_junctions()` helper in `topology_dispatch.py` (or `corridor_designer.py`) that runs after dispatch and normalizes coincident junction endpoints to a single canonical coordinate tuple.

**Code patch effort**: S-M (~1-2 hours).

---

### Finding #4 — `GridAlignmentReport` is fabricated, not measured

**Verdict**: VALID-DEFECT (the partial-MISFRAMED case mentioned in the summary: code is *internally consistent* but the report is meaningless as a quality signal).
**Severity**: HIGH (downstream consumers think they're reading a measurement; they're reading a constant).
**Spec reference**: § 4.2 step 5 says off-grid segments contribute to off-aligned count and log to provenance. § 3 GridAlignmentReport schema says `edges_aligned_count` should be the count of edges that snapped to grid lines.
**Code locations**: `corridor_designer.py:83-120`.

**Evidence**:
```python
if config.width_quantization == WidthQuantization.GRID_FRACTIONS:
    edges_total = max(0, n_segments * 2)
    edges_aligned = edges_total          # ALWAYS = total
    score = 1.0                          # ALWAYS = 1.0
elif config.width_quantization == WidthQuantization.NEAREST_GRID_LINE:
    edges_total = max(0, n_segments * 2)
    edges_aligned = edges_total          # ALWAYS = total
    score = 0.9                          # ALWAYS = 0.9
else:  # NONE_FREE_WIDTH
    edges_total = max(0, n_segments * 2)
    edges_aligned = 0                    # ALWAYS = 0
    score = 0.0                          # ALWAYS = 0.0
```

Per-mode constants. No segment is inspected; no grid line is consulted; no actual snap is checked.

**Web research grounding (Rule 7)**: industry standard for gridline-to-element alignment uses *wall centerlines* and *column edges* (Archlogbook, LinkedIn-Construction Gridlines, Eng-Tips). The C8 v0.5 spec § 4.2 simplifies this to "corridor edges sit on grid lines" which is a reasonable v1 approximation. Either way, *some real measurement* should populate `edges_aligned_count`. Reporting all-aligned-or-none-aligned by mode is uninformative.

**Why it matters**: in the v3 architecture roadmap, `GridAlignmentReport` is supposed to feed C14 (evaluation engine) so that "buildable" plans rank above "off-grid" plans. With constant scores per mode, this ranking signal is degenerate.

**Recommended fix**: actually measure. For each segment:
- Compute its two wall-edge x-coords (or y-coords) at half-width offset from centerline.
- Look up the nearest grid line on each side; check if within `epsilon_m`.
- Count aligned vs misaligned.
- Score = aligned_count / max(total_count, 1).

**Code patch effort**: M (~2-3 hours including a few new tests).

---

### Finding #5 — `tapered_edges_count` always 0; Inv 17 vacuously satisfied

**Verdict**: VALID-DEFECT (Inv 17 effectively unenforced).
**Severity**: MEDIUM (taper-zone edges contribute to alignment-score noise; Inv 17 explicitly excludes them — but only if they're tracked).
**Spec reference**: Inv 17 says tapered-zone edges go in `tapered_edges_count`, NOT in `edges_aligned_count`, and are not subject to grid-snap.
**Code locations**: `corridor_designer.py:96, 115, 167` — `tapered_edges_count=0` hardcoded everywhere.

**Why it matters**: when junctions cause tapers (per § 4.10), each tapered segment has 2 tapered edges per taper zone. If a segment has both ends tapering (N=2 case), it has 4 tapered edges that should be excluded from grid-alignment scoring. Currently they're either incorrectly counted in `edges_aligned_count` (because Finding #4 hardcodes that = total) or not counted anywhere.

**Recommended fix**: as part of the Finding #4 fix, also count tapered edges and report them in `tapered_edges_count` separately.

**Code patch effort**: included in Finding #4's M effort.

---

### Finding #6 — Trace IDs synthesized at C8-time, not propagated from upstream

**Verdict**: VALID-DEFECT.
**Severity**: MEDIUM (correlation across components is broken).
**Spec reference**: § 10 — provenance is for traceability; trace IDs only have value if they correlate to upstream artifacts.
**Code locations**: `corridor_designer.py:74-76, 247-248, 269-270`.

**Evidence**:
```python
def _trace_id(prefix: str, ts: float) -> str:
    return f"{prefix}_{int(ts * 1000) % 10**9}"

# ...
oriented_candidate_trace_id=_trace_id("c6cand", started_at),  # synthesized; not from C6
grid_trace_id=_trace_id("c7grid", started_at),                # synthesized; not from C7
```

The `oriented_candidate.orientation.provenance.plot_analysis_trace_id` is available on the input but never read.

**Why it matters**: a debugging session that asks "what C6 candidate produced this C8 corridor?" can't be answered from the trace IDs because they don't reference each other. Each component generates its own millisecond-mod ID.

**Recommended fix**: populate `oriented_candidate_trace_id` from `oriented_candidate.orientation.provenance.plot_analysis_trace_id` (or whatever C6 trace field is canonical). Same for grid_trace_id (read from `grid.provenance.trace_id` or equivalent if C7's grid carries one; if not, file a B-NNN to add it).

**Code patch effort**: S (~30 minutes).

---

### Finding #7 — § 4.3.1 constrained-plot override (envelope-overflow narrowing) absent

**Verdict**: VALID-DEFECT.
**Severity**: MEDIUM (graceful-degradation path mandated by spec is missing; users hit hard-fail paths instead).
**Spec reference**: § 4.3.1 — "Constrained-plot override: if the chosen quantized width pushes corridor outside the buildable envelope (envelope-overflow check at § 4.7 invariant 10), narrow to next-smaller GRID_FRACTION candidate. If even the smallest exceeds `regulatory_min_width_m`-violating, raise `CorridorTooNarrowError(B-109)`."
**Code locations**: `width_selection.py:select_grid_fraction_width()` picks one width; never re-tries on overflow.

**Why it matters**: small/narrow plots can have a chosen GRID_FRACTION × bay_min width that, when placed at envelope-center, has its edges falling outside the envelope. The spec's prescribed behavior is to narrow to the next-smaller candidate. Current behavior: validator catches this at Inv 10 and raises `ValueError` rather than letting the design retry with a narrower candidate.

**Recommended fix**: refactor `select_grid_fraction_width()` to accept an `envelope_dim_m` parameter and check edge overflow against it; on overflow, retry with the next-smaller eligible candidate. Raise `CorridorTooNarrowError(B-109)` only if all candidates are exhausted.

**Code patch effort**: M (~2-3 hours).

---

### Finding #8 — BAND_ATTACHMENT endpoints never populated with `attached_band`

**Verdict**: VALID-DEFECT.
**Severity**: HIGH (spec Inv 6 is vacuously satisfied because the data it inspects is never populated).
**Spec reference**: § 4.4 — "BAND_ATTACHMENT: located on the segment's edge facing the band's `ZoneBandEnvelope`, at the projection of `envelope.centroid_m` onto the segment. `attached_band` = band, `attached_direction` = direction, `attached_envelope_id` = index into the path's `envelopes` tuple."
**Code locations**: every dispatcher in `topology_dispatch.py`. None set `attached_band`.

**Evidence**: `dispatch_strip_linear()` line 145-148 creates `far_end = CorridorEndpoint(kind=CorridorEndpointKind.BAND_ATTACHMENT, point_m=end_pt)` — no `attached_band`. Same pattern in dispatch_central_spine, dispatch_l_shape, dispatch_courtyard. Validator Inv 6 (line 352-373) only checks endpoints whose `attached_band is not None`; since none are tagged, `bands_with_attachments` is always empty, and the missing-bands check returns no missing bands. Inv 6 passes vacuously.

**Why it matters**: Inv 6 ("PUBLIC, SERVICE, PRIVATE bands each have ≥ 1 BAND_ATTACHMENT in the segments tuple") is supposed to assert that the corridor actually reaches every functional band. With this defect, a corridor that bypasses the SERVICE band entirely passes Inv 6 silently. Downstream components (C9 room sizer, etc.) might consume `attached_band` to know which corridor segment serves which band; they'll see all None.

**Recommended fix**: in each dispatcher, when constructing a BAND_ATTACHMENT endpoint, identify which envelope the endpoint sits on/near (via centroid projection per spec) and set `attached_band`, `attached_direction`, `attached_envelope_id`. Then the existing Inv 6 logic in validator.py will work.

**Code patch effort**: M (~2-4 hours; touches every dispatcher).

---

### Finding #9 — `ENTRY_STUB`, `STAIR_ATTACHMENT`, `DEAD_END` enum members defined but never instantiated

**Verdict**: VALID-BUT-BACKLOG.
**Severity**: LOW (dead surface; not a behavior bug).
**Spec reference**: § 3 (enum) + § 4.4 (STAIR_ATTACHMENT "defensive only in v1; always None" — already documented as deferred). § 4.1 mentions ENTRY_STUB for CENTRAL_SPINE — partially-deferred per dispatcher comment.
**Code locations**: `schema.py:78, 86-87`.

**Why it matters**: dead-code enum members suggest spec features that aren't shipped. Code intent is unclear: is ENTRY_STUB intentionally deferred (like STAIR_ATTACHMENT/DEAD_END are documented as) or accidentally not built? Reader has to dig to find out.

**Recommended fix**: file as B-NNN-J: "Build ENTRY_STUB segment construction for CENTRAL_SPINE (currently spec-described but not implemented; comment in topology_dispatch.py:220-223 acknowledges)."

**Code patch effort (deferred)**: M.

---

### Finding #10 — `entry_stub_width_m` config field defined but never read

**Verdict**: VALID-BUT-BACKLOG.
**Severity**: LOW (dead config; ties to Finding #9).
**Spec reference**: § 3 CorridorDesignConfig.
**Code locations**: `schema.py:450`. Validated in __post_init__ (line 477-481) but never consumed anywhere in the design flow.

**Recommended fix**: when ENTRY_STUB construction (Finding #9) lands, this field gets consumed. Until then, document the gap.

**Code patch effort (deferred)**: included in Finding #9's effort.

---

### Finding #11 — Validator skips Inv 14 (column-supported snap-lines) entirely

**Verdict**: VALID-DEFECT.
**Severity**: LOW (the spec rationale at validator.py:282-283 — "Satisfied by construction in derive_grid_lines()" — is correct *given current implementation*, but the invariant is supposed to be defense-in-depth).
**Spec reference**: § 4.6 Inv 14: "every grid line used for edge-snap must pass through ≥ 1 ColumnPosition in grid.columns. Invariant is satisfied by construction since derive_grid_lines() (§ 4.2) derives lines from grid.columns; the explicit invariant safeguards against future refactors that introduce non-column reference lines."
**Code locations**: `validator.py:281-283`.

**Why it matters**: defense-in-depth is the explicit purpose. By skipping the check, a future refactor that introduces a non-column-derived snap line will pass validation. The spec text says the invariant exists *for* the safeguard role.

**Recommended fix**: actually run the check — for each segment edge that's marked aligned, verify its coordinate is in `grid_x_lines` or `grid_y_lines`. (Currently moot because `edges_aligned_count` is fabricated per Finding #4; the real fix to Finding #4 should enable a real Inv 14 check too.)

**Code patch effort**: included in Finding #4's effort.

---

## Backlog updates

Per Rule 9.2 (always-file-backlog directive). New entries to file:

- **B-132** — Wire `find_edge_snap_pair()` into NEAREST_GRID_LINE path; populate real grid alignment metrics. (Findings #1 + #4 + #5 + #11.) [HIGH severity; M effort]
- **B-133** — Replace generic ValueError with typed `CorridorSelfIntersectionError` at validator.py:219. (Finding #2.) [MEDIUM severity; S effort]
- **B-134** — Implement § 4.7 junction-snap normalization. (Finding #3.) [MEDIUM severity; S-M effort]
- **B-135** — Propagate upstream trace IDs through CorridorProvenance instead of synthesizing. (Finding #6.) [MEDIUM severity; S effort]
- **B-136** — Implement § 4.3.1 constrained-plot override (envelope-overflow narrowing fallback chain). (Finding #7.) [MEDIUM severity; M effort]
- **B-137** — Populate `attached_band` / `attached_envelope_id` on BAND_ATTACHMENT endpoints in every dispatcher. (Finding #8.) [HIGH severity; M effort]
- **B-138** — Build ENTRY_STUB segment construction for CENTRAL_SPINE; consume `entry_stub_width_m` config field. (Findings #9 + #10.) [LOW severity; M effort]
- **B-139** — L_SHAPE branch direction is hardcoded as N or E arbitrarily; should be informed by which band's envelope it serves. (Module 8 review.) [LOW severity; M effort]

B-130 (already filed) gets an addendum noting the `decompose_segment` y-axis transpose path is part of the sweep-line refactor scope.

---

## Spec defects vs code defects — routing

Per the walk introduction, distinguishing where the fix belongs:

**Code-only defects** (spec is correct; code deviates):
- Findings #1, #2, #3, #4, #5, #6, #7, #8, #11 — fix in code.

**Spec-was-defective, already-resolved**:
- (none new in this walk; B-129 was the only one and v0.6 PROPOSED resolves it.)

**Spec deferments / acknowledged gaps**:
- Findings #9, #10 — spec text already acknowledges (e.g., STAIR_ATTACHMENT "defensive only in v1"). The remaining work is incremental implementation.

---

## Recommendation to Ramalingam

C8 ships passing 174 tests. None of those tests would catch the 11 findings in this walk because:
- Finding #1 (no edge-snap call) — no test sets `WidthQuantization.NEAREST_GRID_LINE`.
- Finding #2 (wrong exception) — no test asserts the typed exception is raised on self-intersection.
- Finding #3 (no junction-snap) — no test introduces sub-EPSILON drift across dispatchers.
- Finding #4 (fabricated alignment report) — no test inspects the report's correctness against actual grid positions.
- Finding #5 (tapered_edges always 0) — same.
- Finding #6 (fake trace IDs) — no test correlates upstream and downstream trace IDs.
- Finding #7 (no envelope-overflow narrowing) — no test creates a small-plot case where the chosen width overflows.
- Finding #8 (BAND_ATTACHMENT not tagged) — no test inspects `attached_band` on the resulting endpoints.
- Finding #11 (Inv 14 skipped) — same as #4.

This pattern — tests cover what's there, not what should be there — is a reminder that test coverage adequacy is the explicit subject of walk #3, not walk #1.

For walk #2 (code quality / architecture), I'd flag in advance: the area_accounting `decompose_segment` y-axis transpose path (lines 240-348) is the most concerning code section in the codebase. The 100+ lines of inline-comment debate about geometric semantics suggest unresolved confusion that survived the SHIP review. A clean rewrite is probably the right move.

Walk #2 and walk #3 wait on your direction.

---

## End of Walk #1
