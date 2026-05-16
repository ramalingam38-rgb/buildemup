# BuildemUp — C8 Corridor Designer — SPEC v0.4 PROPOSED

**Status**: PROPOSED. PENDING critique walks → LOCK adjudication. Critique-walk-#3 patch over v0.3 PROPOSED. **Deliberately accepts substantial complexity per Ramalingam direction at walk #3 close** (full local-propagation of junction widths via taper zones, replacing v0.3's global-max-inheritance). Includes scored width selection (replaces v0.3 binary rule), configurable band priority, dispatch-error diagnostic enrichment, edge-snap envelope-symmetry secondary criterion.
**Component**: C8 of canonical 17-component v3 list (Track 3). Position 8 — first sub-component pending in build order after C7.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C5 (`TopologyCandidate.corridor_sketch`) + C6 (`OrientedCandidate.refined_zone_bands`) + C7 (`Grid` — *not* `StructuralGrid`; see § 14.9) + C4 (`PlotAnalysis`); produces input for C9 (Room Sizer) and downstream.
**Authoring session**: S31 (post C6 SHIP, post v0.3 critique walk #3).
**Predecessor**: v0.3 PROPOSED (S31; critique walk #2).

---

## § 0 — Lineage delta from v0.3 PROPOSED → v0.4 PROPOSED

**Drivers**: 7-item reviewer critique walk #3 + Ramalingam adjudication on Q1 (default 2.0 penalty ratio) + Q2 (full local-propagation accepted; not the simpler step-discontinuity compromise).

**Empirical work completed pre-draft (per Pattern C)**:
- Trapezoid sweep-line union algorithm verified via monte-carlo on 6 cases (4 v0.3 cases reproduce exact areas; new L-shape-with-taper = 7.23 m²; new COURTYARD-with-4-tapered-corners = 16.99 m²).
- Trapezoid decomposition (≤ 3 rect + ≤ 4 right-triangles per segment) verified analytically: a 1.0m → 1.5m taper over 1m decomposes to 1 inner rect (1.0 m²) + 2 right triangles (0.125 m² each) = 1.25 m² total, matches analytical trapezoid area exactly.
- Width-selection scored rule verified: produces 1.50/1.10/1.12 on 3.0m/3.3m/4.5m bays — meaningful improvement over both v0.2's bias-down and v0.3's bias-up.

| # | Source | Verdict | What changed |
|---|---|---|---|
| 1 | Walk #3 Drawback 1 | AFFIRMED (already backlogged) | No v0.4 action; B-NNN-K stands. |
| 2 | Walk #3 Drawback 2 | VALID — externally verified | Width selection: scored rule with `under_comfort_penalty_ratio = 2.0` (§ 4.3, § 14.19). Replaces v0.3 binary "smallest ≥ comfort" rule. Web research at S31 confirmed both over-design and under-design have real costs. |
| 3 | Walk #3 Drawback 3 | VALID | Junction-width propagation: `WidthPropagation.JUNCTION_LOCAL_ONLY` default with linear taper in junction-adjacent regions (§ 3 schema, § 4.3.1, § 4.10, § 14.20). **Substantial new architectural surface.** |
| 4 | Walk #3 Drawback 4 | PARTIAL — pushback hold | `consumption_band` stays advisory-only; trigger condition for promoting to constraint documented in § 14.24. C8 still does not act on it (Pattern E avoidance). |
| 5 | Walk #3 Drawback 5 | VALID | Edge-snap secondary criterion: prefer grid pairs whose midpoint is closest to envelope center (§ 4.2.1, § 14.21). Tunable via `envelope_symmetry_weight`. |
| 6 | Walk #3 Drawback 6 | PARTIAL + PUSHBACK | `CorridorDispatchError` enriched with diagnostic metadata (`candidate_index`, `topology_kind`, `failure_phase`, `suggested_alternative_topologies`); auto-skip explicitly NOT added per § 14.17 deliberate-raise rationale (§ 14.23). |
| 7 | Walk #3 Drawback 7 | VALID | Configurable band priority order: `config.band_priority_order = DEFAULT_BAND_PRIORITY_ORDER`; default preserves v0.3 PUBLIC > PRIVATE > SERVICE (§ 14.22). |

**Architectural decisions added in v0.4** (§ 14.19–§ 14.24, 6 ADs):
- § 14.19 — Scored width selection (replaces § 14.11 binary rule; `under_comfort_penalty_ratio = 2.0`)
- § 14.20 — Junction-width local-propagation via linear taper (replaces § 14.12 global-max-inheritance)
- § 14.21 — Edge-snap envelope-symmetry secondary criterion
- § 14.22 — Configurable band-priority order (Indian-default preserved)
- § 14.23 — `CorridorDispatchError` diagnostic enrichment (no auto-skip)
- § 14.24 — Consumption-band promotion trigger documented

**v0.3 ADs partially superseded**:
- § 14.11 (binary "smallest ≥ comfort" rule) → REPLACED by § 14.19 scored selection
- § 14.12 (global-max-inheritance for junction width) → REFINED by § 14.20 local-propagation; § 14.12's intent (eliminate step discontinuities) preserved but mechanism replaced

**New invariants** (5 added to existing 15; total 20):
- Invariant 16 — Taper zones must not exceed half segment length (`taper_zone_m ≤ segment_length / 2`); fallback per § 4.3.1.
- Invariant 17 — Tapered-edge geometric exclusion: edges within taper zones are NOT counted in `edges_aligned_count` and NOT subject to grid-snap.
- Invariant 18 — Junction-width-match-via-taper: at every JUNCTION endpoint, all adjoining segments have equal `width_m` AT THE JUNCTION POINT (i.e., `start_width_m` of one segment = `end_width_m` of its neighbor at the shared junction coordinate).
- Invariant 19 — Taper monotonicity: width interpolates linearly between `start_width_m` and `end_width_m`; no oscillation, no quadratic, no bezier (axis-aligned linear only in v1).
- Invariant 20 — Constant-width-region coverage: at least the middle 50% of each segment's length must have constant width (`constant_middle_length ≥ segment_length / 2`); ensures taper zones don't dominate the segment.

**Web research surface (Rule 7)**: Walk #3 Drawback 2 web research returned strong external evidence for both over-design and under-design costs in residential corridors (Quora architect: "12-18% as practical default"; Coohom: "wasted corridor space quietly steals value"; Constructive Laws: "Keep internal passages minimal to gain more usable space"). This refuted v0.3's framing that downward bias was the only systematic harm — the scored rule in § 14.19 reflects this correction.

Pre-draft taper-length default research (Rule 7) returned no external standards for residential corridor taper length. v0.4 commits to `min(bay_x, bay_y)` as a reasoned default (configurable; B-NNN-O for empirical calibration).

**Code-grep verification at S31**: monte-carlo verification on 6 cases (4 v0.3 reproduce; 2 new tapered cases in valid range). Decomposition arithmetic verified analytically.

**Backward-compat from v0.3**: substantial behavior changes. v0.3 was PROPOSED-not-LOCKED, no shipped consumers. No migration path needed.

---

## § 0.1 — Lineage delta from v0.2 PROPOSED → v0.3 PROPOSED (preserved; historical)

**Drivers**: 9-item reviewer critique walk #2 + empirical verification (Drawback 2 confirmed on 3 of 7 official C7 bay sizes; Drawback 6 confirmed theoretical for v0.2's exact-snap design but principle adopted).

| # | Source | Verdict | What changed |
|---|---|---|---|
| 1 | Walk #2 Drawback 1 | PARTIAL + PUSHBACK | v0.3 acknowledges strip-model simplification explicitly in § 14.16; refinement deferred to **B-NNN-K**. v1 keeps uniform strips. |
| 2 | Walk #2 Drawback 2 | VALID — empirical | Width selection rule changed from "closest to comfort_target" to "smallest ≥ comfort_target, fallback largest ≥ regulatory_min" (§ 4.3, § 14.11). Eliminates downward bias on bay sizes 3.0m / 3.3m / 4.5m. |
| 3 | Walk #2 Drawback 3 | PARTIAL + PUSHBACK | NEW invariant 14: every snap-line passes through ≥ 1 column (already true by construction in v0.2, now made explicit; § 14.13). |
| 4 | Walk #2 Drawback 4 | VALID — promote | Junction-width equality enforced by default; `equal_width_at_junctions: bool = True` (§ 4.3, § 14.12). Fillets/transitions deferred to **B-NNN-M**. |
| 5 | Walk #2 Drawback 5 | VALID — fix | Corner-overlap deterministic resolution: PUBLIC > PRIVATE > SERVICE priority (§ 4.0, § 14.10). |
| 6 | Walk #2 Drawback 6 | PARTIAL — empirical OK; principle adopted | NEW: `epsilon_m_for(stage)` centralized helper; default 1mm preserved (empirically sufficient; § 14.18). |
| 7 | Walk #2 Drawback 7 | VALID — fix | Area accounting uses sweep-line union of axis-aligned rectangles, not additive sum (§ 4.8, § 14.14). Algorithm verified on 4 cases (disjoint, overlap, L-shape, courtyard). |
| 8 | Walk #2 Drawback 8 | PARTIAL + PUSHBACK | NEW: `CorridorDispatchError` raised at session pre-validation (catches dispatch bugs at boundary, not deep). `CorridorSelfIntersectionError` retained as deliberate raise — soft fallback would mask Pattern A bugs (§ 14.17). |
| 9 | Walk #2 Drawback 9 | PARTIAL + PUSHBACK | NEW: `consumption_band: ConsumptionBand` enum on `CorridorPath` (LOW <12%, MED 12-20%, HIGH >20%); advisory metadata only — C8 takes no action; C14/C15 decide (§ 14.15). |

**Architectural decisions added in v0.3** (§ 14.10–§ 14.18, 9 ADs):
- § 14.10 — Corner-overlap deterministic resolution (PUBLIC > PRIVATE > SERVICE)
- § 14.11 — Width-selection rule: bias upward (smallest ≥ comfort)
- § 14.12 — Junction-width equality default
- § 14.13 — Column-line-only invariant for edge-snap
- § 14.14 — Area accounting: union, not sum
- § 14.15 — Consumption band metadata (advisory only)
- § 14.16 — Strip model is provisional v1
- § 14.17 — SelfIntersectionError is deliberate raise
- § 14.18 — Epsilon handling: centralized helper

**Web research surface (Rule 7)**: 1 external-standards-relevant claim (Drawback 3 — "grid columns ≠ wall-support guarantee"). VERIFIED: industry consensus says column lines ARE structural (Eng-Tips, Archisoup); the reviewer's underlying concern collapses to "are snap-lines column-supported?" — answer is yes by construction (v0.2 § 4.2 derives lines from `grid.columns`); v0.3 makes this an explicit invariant.

**Empirical verification at S31** (Rule 7 code-grep mandate):
- Drawback 2 bias confirmed on 3 of 7 PREFERRED_BAY_SIZES_M (3.0m → 1.0m, 3.3m → 1.1m, 4.5m → 1.12m — all sub-comfort)
- Drawback 6 FP-accumulation tested on v0.2 design: 0.0 error for axis-aligned grid-quantized values (1mm tolerance is empirically sufficient; principle still adopted via centralized helper)
- Union-area algorithm verified on 4 test cases (disjoint = 4.0, overlap = 7.0, L-shape = 7.0, courtyard ring = 16.0)

**Backward-compat from v0.2**: substantial behavior changes (width selection, area calculation, junction widths). v0.2 was PROPOSED-not-LOCKED, so no shipped consumers exist. No migration path needed.

---

## § 0.1 — Lineage delta from v0.1 DRAFT → v0.2 PROPOSED (preserved; historical)

**Drivers**: 7-item reviewer critique walk + 1 self-found defect from upstream-grep verification (Rule 7 code-grep mandate).

| # | Source | What changed |
|---|---|---|
| 1 | Reviewer Drawback 1 | NEW: spatial model — C8 derives `ZoneBandEnvelope` rectangles from `refined_zone_bands` + `Grid` envelope dims (§ 4.0, § 14.1). |
| 2 | Reviewer Drawback 2 | Width assignment: grid-quantized by default (§ 4.3, § 14.2). Edges align to grid lines, not centerlines. |
| 3 | Reviewer Drawback 3 | Connectivity: geometric (coordinate-coincident within EPSILON_M) + 0°/90° junction angles only (§ 4.6 inv 4 + 13). |
| 4 | Reviewer Drawback 4 | Length sanity check **removed**. C5 sketch is sketch-grade; C8's length is the truth. Drift moved to C5-side integration test (B-110). |
| 5 | Reviewer Drawback 5 | NEW spatial-feasibility invariants (10, 11, 12): envelope containment, no self-intersection, no segment overlap except at exact junctions (§ 4.6, § 4.7). |
| 6 | Reviewer Drawback 6 | Provenance reports envelope-area consumption; C9 reads downstream. C8 does NOT pre-fetch C9 needs (Pattern E avoidance, § 14.5). |
| 7 | Reviewer Drawback 7 | `CorridorPath.has_corridor: bool` flag; invariants split into ALL-PATHS vs HAS-CORRIDOR-ONLY tiers (§ 4.6). "Documented quirk" language removed. |
| V-A | Self-found (S31 grep) | v0.1 § 4.2 referenced phantom `column_lines_x`, `column_lines_y` fields. Actual C7 schema is `Grid.columns: list[ColumnPosition]` + `bay_x_m` + `bay_y_m`. Algorithm rewritten (§ 4.2, § 14.9). |

**Architectural decisions adopted in v0.2 (per § 14)**:
- § 14.1 — **Option A**: C8 owns the spatial model. C9 / C11a override question deliberately surfaced as known-unknown (not closed).
- § 14.2 — Default width quantization: `WidthQuantization.GRID_FRACTIONS` with `NEAREST_GRID_LINE` and `NONE_FREE_WIDTH` opt-outs.

**Web research surface (Rule 7)**: 1 external-standards claim verified — industry practice "gridlines align to wall centers / column edges" (Archlogbook, LinkedIn Construction Gridlines, USPTO patents on residential timber-grid). Strengthens Drawback 2's verdict to VALID-VERIFIED. All other items are internal-coherence claims; verified by code-grep against actual C4/C5/C6/C7 schemas at S31.

**Zero-behavior-from-v0.1**: not applicable. v0.1 was DRAFT (no shipped code); v0.2 is the pre-LOCK iteration. Behavior change is the *point* of this round.

---

## § 1 — Purpose

(unchanged from v0.1)

Given a C5/C6 oriented topology candidate, a C7 `Grid`, and a C4 plot analysis, produce a **`CorridorPath`** — the geometry of the residential circulation corridor (polyline, widths, attachment points to functional bands) — sized to the structural grid + regulatory minimum, aligned to grid lines, and respecting the topology kind.

Cardinality preserved (C5/C6 candidate → C8 candidate, position-paired, like C6).

**Out of scope for C8** (intentionally not addressed):
- Room placement, room sizing — C9 / C11
- Door placement, passage-door rules — C13
- Circulation-quality scoring (primary/secondary/service path classification) — C14's CirculationAnalyzer
- Stair geometry — C12 (vertical alignment)
- Furniture-fit checks — C9 (room sizer)
- Corridor lighting / mechanical — out of v1 scope entirely

---

## § 2 — Input contract

```python
def design_corridors(
    oriented_candidates: tuple[OrientedCandidate, ...],   # 1-3 from C6
    grid: Grid,                                            # from C7 (was "structural_grid" in v0.1)
    plot_analysis: PlotAnalysis,                           # from C4
    *,
    config: CorridorDesignConfig | None = None,            # tunables; default OK
) -> tuple[CorridorDesignedCandidate, ...]:
```

`Grid` is C7's existing dataclass (`buildemup.components.c07.grid_generator.Grid`). It exposes:
- `columns: list[ColumnPosition]` — actual column positions with x, y, label
- `bay_x_m: float`, `bay_y_m: float` — bay dimensions
- `envelope_width_m: float`, `envelope_depth_m: float` — buildable rectangle
- `columns_x_count: int`, `columns_y_count: int`

C8 derives column-line coordinates internally from `Grid.columns` rather than expecting pre-computed line tuples (per V-A fix, § 14.9).

---

## § 3 — Output schema

```python
class CorridorSegmentKind(str, Enum):
    PRIMARY    = "primary"
    BRANCH     = "branch"
    LOOP_ARM   = "loop_arm"
    ENTRY_STUB = "entry_stub"

class CorridorEndpointKind(str, Enum):
    ENTRY              = "entry"
    BAND_ATTACHMENT    = "band_attachment"
    JUNCTION           = "junction"
    STAIR_ATTACHMENT   = "stair_attachment"
    DEAD_END           = "dead_end"

class WidthQuantization(str, Enum):
    """How corridor width is chosen relative to grid bay.

    NEW v0.2 (§ 14.2). Default: GRID_FRACTIONS.
    """
    GRID_FRACTIONS    = "grid_fractions"     # width ∈ {1/4, 1/3, 1/2, 2/3, 3/4} × min(bay_x, bay_y)
    NEAREST_GRID_LINE = "nearest_grid_line"  # edges snap to grid lines; width derived
    NONE_FREE_WIDTH   = "none_free_width"    # original v0.1 behavior; logged loudly in provenance


# ─── NEW v0.2: spatial model (Reviewer Drawback 1, § 14.1) ──────────────────

@dataclass(frozen=True)
class ZoneBandEnvelope:
    """Bounding rectangle for one ZoneBand within the buildable envelope.

    NEW v0.2 (Reviewer Drawback 1; § 14.1 Option A).

    C8 derives these internally from `oriented_candidate.refined_zone_bands`
    + `grid.envelope_width_m/depth_m`. Each band gets a directional strip of
    the buildable rectangle, sized proportionally:

      - 4 distinct cardinal bands → 4 strips, each ~25% of envelope along its axis
      - 3 distinct cardinal bands → 3 strips (one band absent; e.g., L_SHAPE)
      - COURTYARD: 4 perimeter strips around a central open core

    The strip model is intentionally simple (Pattern A avoidance — the band
    geometry is the simplest possible spatial referent that resolves the
    abstraction gap). Real per-room geometry is C9's job.

    Coordinates: plot-local, origin = SW corner of buildable envelope.

    Invariants (asserted at construction):
      - x_min < x_max, y_min < y_max
      - all coords ∈ [0, envelope_width_m] × [0, envelope_depth_m]
      - direction is one of CARDINAL_FACINGS (per C6 invariant)
    """
    band: ZoneBand
    direction: PlotOrientation        # cardinal; mirrors refined_zone_bands
    x_min_m: float
    y_min_m: float
    x_max_m: float
    y_max_m: float

    @property
    def centroid_m(self) -> tuple[float, float]:
        return ((self.x_min_m + self.x_max_m) / 2.0,
                (self.y_min_m + self.y_max_m) / 2.0)


@dataclass(frozen=True)
class CorridorEndpoint:
    kind: CorridorEndpointKind
    point_m: tuple[float, float]              # (x, y) plot-local; coordinate-exact
    attached_band: ZoneBand | None
    attached_direction: PlotOrientation | None
    attached_envelope_id: int | None          # NEW v0.2: index into envelopes tuple


@dataclass(frozen=True)
class CorridorSegment:
    """A single straight axis-aligned section of the corridor.

    All segments are axis-aligned to a cardinal direction in v1.
    Diagonal deferred to B-NNN-E.

    NEW v0.4 (Walk #3 Drawback 3 / § 14.20): segments now have variable
    width via taper zones. Each segment has THREE width regions along
    its runs_along axis:
      - Taper-start zone:    [start, start + taper_zone_m]; width interpolates
                              linearly from `start_width_m` at segment start
                              to `constant_width_m` at end of zone
      - Constant middle:     [start + taper_zone_m, end - taper_zone_m];
                              width = `constant_width_m`
      - Taper-end zone:      [end - taper_zone_m, end]; width interpolates
                              linearly from `constant_width_m` to `end_width_m`

    `start_width_m`, `end_width_m`, and `constant_width_m` may all be equal
    (no taper anywhere, like v0.2/v0.3 uniform-width segments). When any
    differs, the corresponding taper zone activates.

    `taper_zone_m` defaults to `min(grid.bay_x_m, grid.bay_y_m)` per
    config; falls back to `segment_length_m / 2` when default exceeds half
    the segment length (per Invariant 16; logged as
    `"taper_truncated_at_segment_N"` in provenance.rule_trace).

    Invariants (asserted at construction):
      - start.point_m and end.point_m differ in exactly one coordinate
        (axis-aligned)
      - length_m == |end - start| in the differing coordinate
      - all three width values > 0
      - 2 × taper_zone_m ≤ length_m (Invariant 16)
      - constant_middle_length ≥ length_m / 2 (Invariant 20)
      - runs_along is the cardinal direction from start to end
    """
    kind: CorridorSegmentKind
    start: CorridorEndpoint
    end: CorridorEndpoint
    constant_width_m: float                   # NEW v0.4 (was `width_m` in v0.3)
    start_width_m: float                      # NEW v0.4
    end_width_m: float                        # NEW v0.4
    taper_zone_m: float                       # NEW v0.4
    length_m: float
    runs_along: PlotOrientation

    @property
    def has_taper(self) -> bool:
        """True if either end tapers (start_width != constant or end_width != constant)."""
        return (
            abs(self.start_width_m - self.constant_width_m) > 1e-9
            or abs(self.end_width_m - self.constant_width_m) > 1e-9
        )

    @property
    def constant_middle_length_m(self) -> float:
        """Length of the constant-width middle region."""
        return max(0.0, self.length_m - 2 * self.taper_zone_m)


@dataclass(frozen=True)
class CorridorPath:
    """The complete corridor design for one candidate.

    Per SPEC v0.3 § 3 + § 4.6.

    NEW v0.2 (Reviewer Drawback 7): `has_corridor: bool` flag. Invariants
    split into ALL-PATHS (apply unconditionally) and HAS-CORRIDOR-ONLY
    (apply only when has_corridor == True). Eliminates the "documented
    quirk" of v0.1 § 4.6 invariants 6 + 7.

    NEW v0.3 (Walk #2 Drawback 9): `consumption_band` advisory metadata.
    """
    has_corridor: bool                        # NEW v0.2
    segments: tuple[CorridorSegment, ...]
    envelopes: tuple[ZoneBandEnvelope, ...]   # NEW v0.2 (§ 14.1)
    total_length_m: float
    total_area_m2: float                      # NEW v0.2; in v0.3 = union area (§ 14.14)
    consumption_band: ConsumptionBand         # NEW v0.3 (§ 14.15); advisory only
    connectivity_type: ConnectivityType       # mirrors C5; sanity-check
    grid_alignment: GridAlignmentReport       # NEW v0.2 (replaces grid_snap_offsets)


class ConsumptionBand(str, Enum):
    """Qualitative classification of corridor area consumption.

    NEW v0.3 (§ 14.15 / Walk #2 Drawback 9). Advisory metadata only;
    C8 takes no action. C14/C15 decide what to do with this signal.

    Thresholds (12% / 20%) are defaults; configurable via
    CorridorDesignConfig.consumption_band_thresholds.
    """
    LOW    = "low"      # envelope_area_fraction < 0.12
    MEDIUM = "medium"   # 0.12 ≤ fraction < 0.20
    HIGH   = "high"     # fraction ≥ 0.20


@dataclass(frozen=True)
class GridAlignmentReport:
    """How well the corridor aligns to the C7 grid.

    NEW v0.2 (replaces v0.1's `grid_snap_offsets` raw mapping).

    NEW v0.4 (Walk #3 Drawback 5 / § 14.21): adds
    `envelope_symmetry_score` for secondary alignment criterion.
    NEW v0.4 (Walk #3 Drawback 3 / § 14.20): adds `tapered_edges_count`
    for taper-zone exclusion accounting.
    """
    quantization_used: WidthQuantization
    edges_aligned_count: int                  # number of constant-region edges on grid lines
    edges_total_count: int                    # total constant-region edges across all segments
    tapered_edges_count: int                  # NEW v0.4; edges in taper zones (geometrically excluded from snap accounting)
    grid_alignment_score: float               # [0, 1]; edges_aligned / edges_total
    chosen_width_fraction: float | None       # populated for GRID_FRACTIONS quantization
    chosen_bay_axis: str | None               # "x" or "y"; which bay was the quantization basis
    envelope_symmetry_score: float            # NEW v0.4 [0, 1]; 1.0 = pair midpoint at envelope center


class WidthPropagation(str, Enum):
    """How junction widths propagate across adjacent segments.

    NEW v0.4 (Walk #3 Drawback 3 / § 14.20). Default: JUNCTION_LOCAL_ONLY.
    """
    JUNCTION_LOCAL_ONLY    = "junction_local_only"   # Default v0.4: junction inherits max;
                                                      # adjoining segments taper from constant_width
                                                      # to junction width within taper_zone_m of
                                                      # the junction. Local containment.
    GLOBAL_MAX_INHERITANCE = "global_max"            # v0.3 behavior: entire segment width = max.
                                                      # Deprecated; use only for back-compat tests.
    INDEPENDENT_WIDTHS     = "independent"           # v0.2 behavior: mismatch at junction
                                                      # tolerated (logged in provenance).
                                                      # Use only for special architect-driven cases.


@dataclass(frozen=True)
class CorridorProvenance:
    derived_at: float
    oriented_candidate_trace_id: str
    grid_trace_id: str                        # was structural_grid_trace_id in v0.1
    config_snapshot: CorridorDesignConfig
    rule_trace: tuple[str, ...]
    fallback_used: bool
    envelope_area_consumed_m2: float          # NEW v0.2 (= union area in v0.3 per § 14.14)
    envelope_area_fraction: float             # NEW v0.2
    additive_sum_m2: float                    # NEW v0.3 (diagnostic; sum-without-union)
    overlap_area_m2: float                    # NEW v0.3 (diagnostic; additive_sum - union_area)


@dataclass(frozen=True)
class CorridorDesignedCandidate:
    oriented_candidate: OrientedCandidate
    corridor_path: CorridorPath
    provenance: CorridorProvenance


@dataclass(frozen=True)
class CorridorDesignConfig:
    """Tunables for C8. All have safe defaults; callers can omit.

    NEW v0.2 fields: width_quantization, junction_angle_tolerance_deg,
    epsilon_m. Renamed: grid_snap_tolerance_m → fallback_snap_tolerance_m
    (only used when quantization == NONE_FREE_WIDTH).

    NEW v0.3 fields: equal_width_at_junctions, consumption_band_thresholds.

    NEW v0.4 fields: width_propagation, taper_zone_m_default,
    under_comfort_penalty_ratio, envelope_symmetry_weight,
    band_priority_order. Removed v0.3 field: equal_width_at_junctions
    (subsumed by width_propagation).
    """
    regulatory_min_width_m: float = 0.9       # NEEDS PRIMARY-SOURCE VERIFICATION (B-NNN-A)
    comfort_target_width_m: float = 1.2
    entry_stub_width_m: float = 1.0
    width_quantization: WidthQuantization = WidthQuantization.GRID_FRACTIONS  # NEW v0.2
    fallback_snap_tolerance_m: float = 0.15   # only for NONE_FREE_WIDTH
    junction_angle_tolerance_deg: float = 0.0  # NEW v0.2; 0.0 = exact 0/90 only
    epsilon_m: float = 0.001                  # NEW v0.2; coordinate-coincidence tolerance
    courtyard_loop_inner_clear_m: float = 1.0
    consumption_band_thresholds: tuple[float, float] = (0.12, 0.20)  # NEW v0.3 (§ 14.15)

    # NEW v0.4 (Walk #3 Drawback 3 / § 14.20)
    width_propagation: WidthPropagation = WidthPropagation.JUNCTION_LOCAL_ONLY
    taper_zone_m_default: float | None = None  # None = use min(bay_x, bay_y) at runtime; B-NNN-O

    # NEW v0.4 (Walk #3 Drawback 2 / § 14.19)
    under_comfort_penalty_ratio: float = 2.0  # B-NNN-O for empirical calibration

    # NEW v0.4 (Walk #3 Drawback 5 / § 14.21)
    envelope_symmetry_weight: float = 0.3     # B-NNN-Q for empirical calibration

    # NEW v0.4 (Walk #3 Drawback 7 / § 14.22)
    band_priority_order: tuple[ZoneBand, ...] | None = None  # None = DEFAULT_BAND_PRIORITY_ORDER
```

**Constants** (in c08/schema.py):

```python
# v0.2 § 14.2 — quantization fraction set
GRID_FRACTION_CANDIDATES: tuple[float, ...] = (0.25, 1.0/3.0, 0.5, 2.0/3.0, 0.75)

# v0.2 § 4.6 inv 13 — junction angle constants
ALLOWED_JUNCTION_ANGLES_DEG: frozenset[float] = frozenset({0.0, 90.0, 180.0, 270.0})

# v0.2 § 3 — coordinate-coincidence tolerance default
DEFAULT_EPSILON_M: float = 0.001              # 1mm; sub-construction-tolerance

# v0.4 § 14.22 — default band priority order (Walk #3 Drawback 7)
# Indian residential vernacular default; configurable via config.band_priority_order
DEFAULT_BAND_PRIORITY_ORDER: tuple[ZoneBand, ...] = (
    ZoneBand.PUBLIC,    # 1st priority — entry-bearing, most foot traffic
    ZoneBand.PRIVATE,   # 2nd — privacy/quietness; corner window placement
    ZoneBand.SERVICE,   # 3rd — most spatially flexible
    # ZoneBand.CIRCULATION intentionally absent (it IS the corridor)
)

# v0.4 § 14.19 — width-selection penalty default
DEFAULT_UNDER_COMFORT_PENALTY_RATIO: float = 2.0  # B-NNN-O calibration
```

---

## § 4 — Behavior

### § 4.0 — Spatial model derivation (NEW v0.2; per § 14.1 Option A)

Before any topology dispatch, C8 derives the `ZoneBandEnvelope` set from the candidate's `refined_zone_bands` mapping + `grid.envelope_width_m/depth_m`. This is the spatial referent that all subsequent geometry resolves against.

**Algorithm** — directional-strip model:

For each `(band, direction)` in `oriented_candidate.refined_zone_bands`:
1. Determine strip thickness `t = envelope_dim_along_direction / N`, where `N` = count of distinct cardinal bands in the candidate (e.g., 4 for a 4-band CENTRAL_SPINE; 3 for typical L_SHAPE).
2. Place the strip at the edge of the buildable rectangle facing `direction`:
   - NORTH-band → `y_min = envelope_depth - t`, `y_max = envelope_depth`, full width
   - EAST-band → `x_min = envelope_width - t`, `x_max = envelope_width`, full depth
   - SOUTH-band → `y_min = 0`, `y_max = t`, full width
   - WEST-band → `x_min = 0`, `x_max = t`, full depth
3. **COURTYARD topology variant**: strips are perimeter only; central rectangle of size `(envelope_width - 2t) × (envelope_depth - 2t)` is the courtyard void (not a band; not occupied by any envelope).

**The CIRCULATION band intentionally does NOT get a `ZoneBandEnvelope`.** It IS the corridor (per v0.1 § 14.7 / v0.2 § 14.7). Validator skip remains documented.

**Strip overlap at corners — deterministic resolution (NEW v0.3; § 14.10)**: where two adjacent cardinal strips meet at a corner (e.g., NORTH-band + EAST-band in the NE corner), v0.3 resolves ownership deterministically by **band-priority order: PUBLIC > PRIVATE > SERVICE**. The overlap rectangle is assigned to whichever overlapping band has higher priority; the loser's envelope is clipped at the overlap boundary.

Rationale: PUBLIC is the entry-bearing band with most foot traffic (wins corner); PRIVATE has highest privacy/quietness needs (next); SERVICE is most spatially flexible (loses). This eliminates v0.2's centroid-projection ambiguity (Walk #2 Drawback 5) without requiring downstream resolution.

If both overlapping bands have the same priority class (rare; only possible if multiple bands of the same type exist, which v1 doesn't support per `refined_zone_bands` cardinality), tie-break is **lexicographic on band name**.

This model is intentionally the **simplest possible spatial resolution** of the band → direction abstraction. Per § 14.16 it is documented as **provisionally C8-owned and uniformly-thick** in v1; band-importance-weighted refinement is deferred to **B-NNN-K** (Walk #2 Drawback 1 partial-resolution).

### § 4.1 — Topology dispatch

(unchanged structure from v0.1, but each branch now operates on `ZoneBandEnvelope`s, not abstract bands)

| Topology | Algorithm |
|---|---|
| `STRIP` (small T1: no corridor) | Returns `CorridorPath(has_corridor=False, segments=(), envelopes=...)` — see § 4.3.1. |
| `STRIP` (T2/T3: linear) | Single PRIMARY segment between facing-edge envelope and opposite-edge envelope; ENTRY at facing end; BAND_ATTACHMENT endpoints into perpendicular envelopes. |
| `CENTRAL_SPINE` | Single PRIMARY segment along `corridor_sketch.runs_along` axis through envelope center; ENTRY_STUB from facing-edge to spine; BAND_ATTACHMENTs both sides. |
| `L_SHAPE` | One PRIMARY arm + one BRANCH arm meeting at a JUNCTION; both axis-aligned. ENTRY on the longer arm by default. |
| `COURTYARD` | Four LOOP_ARM segments forming a closed loop around the central open core (the `(envelope_width - 2t) × (envelope_depth - 2t)` rectangle from § 4.0); ENTRY on the arm matching plot.facing. |

### § 4.2 — Grid line derivation + edge alignment (NEW v0.2; replaces v0.1 § 4.2)

**v0.1 referenced phantom fields `column_lines_x` and `column_lines_y` on `StructuralGrid`. C7's actual `Grid` exposes `columns: list[ColumnPosition]` (each with `.x_m`, `.y_m`) + `bay_x_m`, `bay_y_m`. v0.2 derives line coordinates from columns** (per V-A self-found defect, § 14.9):

```python
def derive_grid_lines(grid: Grid) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Derive (x_lines, y_lines) from grid.columns. Sorted, deduplicated."""
    x_lines = tuple(sorted({c.x_m for c in grid.columns}))
    y_lines = tuple(sorted({c.y_m for c in grid.columns}))
    return (x_lines, y_lines)
```

**Edge alignment** (NEW v0.2; per Reviewer Drawback 2 + verified industry practice):

For each corridor segment, the segment's two **edges** (parallel to `runs_along`, offset by `±width_m/2` from centerline) are the alignment targets — NOT the centerline. The algorithm:

1. From `width_quantization` (§ 4.3 below), determine the segment's `width_m`.
2. From the segment's required centerline position (derived from envelope geometry of attached bands), compute candidate edge coordinates `e_low = c - width_m/2`, `e_high = c + width_m/2`.
3. For the perpendicular axis (lines perpendicular to `runs_along`), find the nearest grid lines `g_low ≤ e_low` and `g_high ≥ e_high`.
4. If `(g_high - g_low) within ±epsilon_m of width_m`: snap edges to `(g_low, g_high)`; centerline becomes `(g_low + g_high) / 2`. **Edges aligned**: contributes to `grid_alignment.edges_aligned_count`.
5. Else: leave edges at computed `(e_low, e_high)`. **Edges off-grid**: contributes to off-aligned count; algorithm logs `"segment_N_edges_off_grid"` in `provenance.rule_trace`.

**Per industry practice** (verified web research, S31): gridlines align to wall centers and column edges. The corridor's *walls* sit on grid lines; the corridor *void* is what's left between them. v0.1's centerline-snap was backwards; v0.2's edge-snap matches construction reality.

#### § 4.2.1 — Envelope-symmetry secondary criterion (NEW v0.4; per § 14.21 / Walk #3 Drawback 5)

When multiple grid-line pairs satisfy the edge-snap requirement (i.e., their separation matches the chosen `width_m` within `epsilon_m`), v0.4 ties-break with a secondary score that prefers pairs whose midpoint is closest to the envelope center.

```python
def edge_snap_choice_score(pair: tuple[float, float],
                          envelope_dim_m: float,
                          target_centerline: float,
                          config: CorridorDesignConfig) -> float:
    """Lower is better. Combines primary (target-centerline alignment) and
    secondary (envelope-symmetry) criteria.
    """
    g_low, g_high = pair
    pair_center = (g_low + g_high) / 2.0
    primary_dist = abs(pair_center - target_centerline)  # primary: hit the band
    envelope_center = envelope_dim_m / 2.0
    symmetry_dist = abs(pair_center - envelope_center) / envelope_dim_m  # secondary
    return primary_dist + config.envelope_symmetry_weight * symmetry_dist
```

`config.envelope_symmetry_weight` defaults to 0.3 (calibration → **B-NNN-Q**). The score is recorded in `GridAlignmentReport.envelope_symmetry_score = 1 - symmetry_dist` (so 1.0 = perfect symmetry).

**Why secondary**: the primary criterion (hitting the target centerline derived from band geometry) must dominate — corridor must reach its bands. The secondary criterion only matters when multiple grid pairs are equally good for the primary.

**Practical effect**: on plots where C7's grid is offset (envelope center doesn't sit on a grid line), v0.4 prefers grid pairs straddling the envelope center over pairs offset to one side. This stabilizes downstream `ZoneBandEnvelope` placement against minor grid-asymmetry artifacts.

### § 4.3 — Width assignment (NEW v0.2; quantization-driven)

Per `config.width_quantization`:

**`GRID_FRACTIONS`** (default) — *scored selection (NEW v0.4; per § 14.19 / Walk #3 Drawback 2)*:

v0.3 used "smallest ≥ comfort" which over-corrected v0.2's downward bias by introducing an upward bias (e.g., 1.65m corridor on a 3.3m bay where 1.10m would be acceptable). v0.4 uses asymmetric scoring:

```python
def width_selection_score(candidate_m: float, comfort_m: float, regulatory_m: float, ratio: float) -> float:
    """Lower is better. Asymmetric penalty: under-comfort × ratio (default 2.0),
    over-comfort × 1.0. Below regulatory minimum is disqualified.
    """
    if candidate_m < regulatory_m:
        return float('inf')
    diff = candidate_m - comfort_m
    if diff < 0:
        return abs(diff) * ratio  # default 2.0
    else:
        return diff * 1.0
```

1. `bay_min = min(grid.bay_x_m, grid.bay_y_m)`.
2. Candidate widths = `[f × bay_min for f in GRID_FRACTION_CANDIDATES]`.
3. Filter to candidates ≥ `regulatory_min_width_m`.
4. **Choose the candidate minimizing `width_selection_score`** (with `ratio = config.under_comfort_penalty_ratio`, default 2.0).
5. If filtered is empty: raise `CorridorTooNarrowError(B-NNN-B)`.
6. Record `(chosen_width_fraction, chosen_bay_axis)` in `GridAlignmentReport`.

**Worked examples** against actual C7 `PREFERRED_BAY_SIZES_M = [2.7, 3.0, 3.3, 3.6, 4.0, 4.5, 5.0]` with target=1.2, ratio=2.0:

| Bay (m) | v0.2 (closest) | v0.3 (≥ target) | **v0.4 (scored)** | v0.4 reasoning |
|---|---|---|---|---|
| 2.7 | 1.35 ✓ | 1.35 ✓ | **1.35** ✓ | only candidate ≥ comfort; uncontested |
| 3.0 | 1.00 ✗ | 1.50 ✓ (over) | **1.50** ✓ | 1.0m: 0.2 × 2 = 0.4 penalty; 1.5m: 0.3 × 1 = 0.3 penalty → 1.5m wins |
| 3.3 | 1.10 ✗ | 1.65 ✓ (over) | **1.10** | 1.1m: 0.1 × 2 = 0.2 penalty; 1.65m: 0.45 × 1 = 0.45 penalty → 1.1m wins (acceptable: 0.1m below comfort) |
| 3.6 | 1.20 ✓ | 1.20 ✓ | **1.20** ✓ | exact match; uncontested |
| 4.0 | 1.33 ✓ | 1.33 ✓ | **1.33** ✓ | smallest ≥ comfort; uncontested |
| 4.5 | 1.12 ✗ | 1.50 ✓ (over) | **1.12** | 1.12m: 0.075 × 2 = 0.15 penalty; 1.5m: 0.3 × 1 = 0.3 penalty → 1.12m wins (acceptable: 0.08m below comfort) |
| 5.0 | 1.25 ✓ | 1.25 ✓ | **1.25** ✓ | smallest ≥ comfort; uncontested |

**Web research grounding** (Rule 7, S31): Coohom's anti-pattern story (*"the corridor was so wide we were sacrificing two full kitchen cabinets in every unit"*) and Constructive Laws' guidance (*"Residential Homes: Keep internal passages minimal to gain more usable space"*) confirm that over-design has real cost, not just under-design. The asymmetric 2:1 ratio reflects that under-comfort is more occupant-visible than over-comfort, so still penalized harder — but not infinitely so.

**Empirical verification at S31**: scored rule produces the right answer on all 7 bay sizes — never extreme over-design (worst case 1.50m at 3.0m bay), never extreme under-design (worst case 1.10m at 3.3m bay).

**`NEAREST_GRID_LINE`**:
1. Compute desired `width_m = max(comfort_target_width_m, regulatory_min_width_m)`.
2. Find nearest pair of grid lines `(g_low, g_high)` straddling the corridor's required centerline with `g_high - g_low` ≥ `regulatory_min_width_m`.
3. Width derived as `g_high - g_low`. Edges aligned by construction.

**`NONE_FREE_WIDTH`** (escape hatch, logged loudly):
- Original v0.1 behavior: `width_m = max(comfort_target_width_m, regulatory_min_width_m)`.
- Edges may be off-grid; falls back to `fallback_snap_tolerance_m` for centerline snap.
- `provenance.rule_trace` includes `"WARNING: width_quantization=NONE_FREE_WIDTH; corridor edges may not align to structural grid"`.

**ENTRY_STUB segments**: separate width = `entry_stub_width_m` (default 1.0m). Quantization applied to entry stub independently.

#### § 4.3.1 — Taper zone length defaults + truncation fallback (NEW v0.4)

Per § 14.20, segments adjacent to a JUNCTION may need to taper their width across a `taper_zone_m` length to match the junction's inherited width. The taper-length default and fallback chain:

```python
def resolve_taper_zone_m(config: CorridorDesignConfig,
                         grid: Grid,
                         segment_length_m: float) -> float:
    """Resolve the taper-zone length for a single segment.

    Default: min(grid.bay_x_m, grid.bay_y_m) — bay-scale is the natural
    local unit; the taper should be perceptible relative to the bay.

    Fallback: when 2 × default > segment_length (i.e. the two end-tapers
    would overlap), truncate to segment_length / 2 per side. Logs
    "taper_truncated_at_segment_N" in provenance.rule_trace.

    Empirical calibration: B-NNN-O.
    """
    if config.taper_zone_m_default is not None:
        proposed = config.taper_zone_m_default
    else:
        proposed = min(grid.bay_x_m, grid.bay_y_m)

    max_allowed = segment_length_m / 2.0  # one taper per end
    if proposed > max_allowed:
        # Truncation: log and shrink
        return max_allowed
    return proposed
```

**Bay-range analysis** (per C7's `PREFERRED_BAY_SIZES_M = [2.7, ..., 5.0]`):
- Default taper zone: 2.7m (smallest bay) to 5.0m (largest bay).
- For a segment shorter than `2 × bay_min`, truncation fires: e.g., a 4m L_SHAPE branch with bay_min = 2.7m → taper truncated to 2.0m per side.

**Web research grounding (Rule 7)**: no industry-standards guidance found for residential corridor taper length. The default is a *reasoned default*, not standards-bound. Empirical calibration deferred to **B-NNN-O**.

**Constrained-plot override**: if the chosen quantized width pushes corridor outside the buildable envelope (envelope-overflow check at § 4.7 invariant 10), narrow to next-smaller GRID_FRACTION candidate. If even the smallest exceeds `regulatory_min_width_m`-violating, raise `CorridorTooNarrowError(B-NNN-B)`.

#### § 4.3.2 — Degenerate path (NEW v0.2 representation)

For small T1 STRIP topologies where C5 set `corridor_sketch.position == NONE`:

```python
CorridorPath(
    has_corridor=False,                       # ← KEY FLAG (NEW v0.2)
    segments=(),                               # empty, not a single dummy stub
    envelopes=<bands per § 4.0>,              # bands still derived
    total_length_m=0.0,
    total_area_m2=0.0,
    connectivity_type=<from C5; preserved>,
    grid_alignment=GridAlignmentReport(
        quantization_used=config.width_quantization,
        edges_aligned_count=0,
        edges_total_count=0,
        grid_alignment_score=1.0,             # vacuously aligned
        chosen_width_fraction=None,
        chosen_bay_axis=None,
    ),
)
```

**Validator behavior** (per § 4.6 split): when `has_corridor=False`, ALL-PATHS invariants 1, 3, 4, 5, 8, 10-12 still apply (most are vacuously satisfied on empty segments). HAS-CORRIDOR-ONLY invariants 2, 6, 7, 9 are skipped. This eliminates the v0.1 "documented quirk" framing — there's now a clean type-system signal.

### § 4.4 — Endpoint construction (NEW v0.2; envelope-anchored)

Per topology, C8 constructs endpoints **anchored to ZoneBandEnvelope rectangles** (resolves Reviewer Drawback 1):

- **ENTRY**: located on plot.facing edge of buildable envelope, snapped to nearest grid x-line or y-line (depending on facing axis). `attached_direction = plot.facing`.
- **BAND_ATTACHMENT**: located on the segment's edge facing the band's `ZoneBandEnvelope`, at the projection of `envelope.centroid_m` onto the segment. `attached_band` = band, `attached_direction` = direction, `attached_envelope_id` = index into the path's `envelopes` tuple.
- **JUNCTION** (L_SHAPE only): at the L's bend; coordinates exact (must be coordinate-coincident with two segment endpoints — see § 4.6 inv 4).
- **STAIR_ATTACHMENT**: defensive only in v1; always None.
- **DEAD_END**: not used in v0.2 (replaced by `has_corridor=False`).

**Endpoint coordinate-exactness** (NEW v0.2; per Reviewer Drawback 3): all endpoints carry exact `(x, y)` floats. Two endpoints are "coincident" iff `|x1 - x2| < EPSILON_M and |y1 - y2| < EPSILON_M`. The validator uses this for invariants 4 and 13.

### § 4.5 — Length tracking (NEW v0.2; v0.1 sanity-check removed)

**v0.1's approx-length-vs-C5 sanity check is REMOVED in v0.2** (Reviewer Drawback 4).

C8's `total_length_m` is the authoritative corridor length post-grid-quantization. C5's `corridor_sketch.approx_length_m` is sketch-grade and intended for C5-internal scoring only. Comparing the two at C8-time created false-warning noise (legitimately drift up to ~15% from grid quantization alone).

**Replacement**: optional integration test (NOT in C8) compares `c8_path.total_length_m` against `c5_sketch.approx_length_m` to detect *systemic* drift across many candidates. Filed as **B-110**: "C5 ↔ C8 length-drift integration test."

C8 still computes and exposes `total_length_m` (sum of segment lengths) for downstream consumers + provenance.

### § 4.6 — Validator invariants (NEW v0.2; tiered)

**ALL-PATHS** (apply regardless of `has_corridor`):

1. `segments` is a tuple (may be empty when `has_corridor=False`).
2. ~(moved to HAS-CORRIDOR-ONLY)~
3. Every segment is axis-aligned to a cardinal direction (vacuous when no segments).
4. **Geometric connectivity** (NEW v0.2; per Reviewer Drawback 3): for each segment, `start.point_m` and `end.point_m` differ in exactly one axis; for any two segments, their shared endpoint coordinates are equal within `EPSILON_M` (no "endpoint shared" set semantics; coordinate-coincident).
5. **At most one** ENTRY endpoint across the full path (zero is OK when `has_corridor=False`).
8. `connectivity_type` matches upstream C5 contract.
10. **NEW v0.2 — Envelope containment** (per Reviewer Drawback 5): every segment's bounding box (centerline ± width/2) lies entirely within `[0, envelope_width_m] × [0, envelope_depth_m]`.
11. **NEW v0.2 — No self-intersection** (per Reviewer Drawback 5): for any two non-adjacent segments, their bounding boxes do not overlap.
12. **NEW v0.2 — Junction-only overlap** (per Reviewer Drawback 5): for adjacent segments (sharing an endpoint), bounding-box overlap is permitted ONLY at the junction point itself, not along segment lengths.
13. **NEW v0.2 — Junction angle** (per Reviewer Drawback 3): at every JUNCTION endpoint, the angle between incoming and outgoing segment directions is in `ALLOWED_JUNCTION_ANGLES_DEG = {0.0, 90.0, 180.0, 270.0}` (within `config.junction_angle_tolerance_deg`, default 0.0).
14. **NEW v0.3 — Column-supported snap-lines** (per Walk #2 Drawback 3 / § 14.13): every grid line used for edge-snap must pass through ≥ 1 `ColumnPosition` in `grid.columns`. Invariant is satisfied by construction since `derive_grid_lines()` (§ 4.2) derives lines from `grid.columns`; the explicit invariant safeguards against future refactors that introduce non-column reference lines.
15. **NEW v0.3 — Junction-width equality** (per Walk #2 Drawback 4 / § 14.12; refined v0.4 / § 14.20): when `config.width_propagation == JUNCTION_LOCAL_ONLY` (default v0.4) or `GLOBAL_MAX_INHERITANCE`, all segments meeting at a JUNCTION endpoint have equal width AT THE JUNCTION POINT (i.e., adjacent segments' `start_width_m` or `end_width_m` matching the shared junction coordinate are equal within `EPSILON_M`). When `INDEPENDENT_WIDTHS`, the validator skips this check (mismatch logged in provenance instead).
16. **NEW v0.4 — Taper-zone length bound** (per § 14.20 / § 4.3.1): for every segment, `2 × taper_zone_m ≤ length_m`. Truncation per § 4.3.1 ensures this; validator confirms.
17. **NEW v0.4 — Tapered-edge geometric exclusion** (per § 14.20): edges within taper zones are NOT counted in `GridAlignmentReport.edges_aligned_count` and are NOT subject to grid-snap. Tapered edges go in `tapered_edges_count` instead. Tapered-zone edge-snap would contradict the linear-interpolation contract.
18. **NEW v0.4 — Junction-width-match-via-taper** (per § 14.20): at every JUNCTION endpoint, all adjoining segments have equal width at the junction point (start_width_m or end_width_m, whichever matches). The junction-adjacent taper zone bridges from this junction width back to the segment's `constant_width_m`. (Subsumes part of invariant 15 for `JUNCTION_LOCAL_ONLY`.)
19. **NEW v0.4 — Taper monotonicity** (per § 14.20): width within a taper zone interpolates *linearly* between `start_width_m` (or `constant_width_m`) and `constant_width_m` (or `end_width_m`). No oscillation, no quadratic, no bezier (axis-aligned linear only in v1).
20. **NEW v0.4 — Constant-width-region coverage** (per § 14.20): every segment's constant-width middle region is at least 50% of the segment's length: `constant_middle_length_m ≥ length_m / 2`. Ensures taper zones don't dominate the segment. Combined with invariant 16, this means `taper_zone_m ≤ length_m / 4` per side (assuming both ends taper).

**HAS-CORRIDOR-ONLY** (apply only when `has_corridor=True`):

2. Every segment's `constant_width_m`, `start_width_m`, and `end_width_m` are all `>= regulatory_min_width_m`. (Updated v0.4: applies to all three width fields, not a single `width_m`.)
6. PUBLIC, SERVICE, PRIVATE bands each have ≥ 1 BAND_ATTACHMENT in the segments tuple.
7. CIRCULATION band has no `ZoneBandEnvelope` (it IS the corridor; § 4.0 + § 14.7).
9. **EXISTS** at least one ENTRY endpoint (combined with inv 5: exactly one).

### § 4.7 — Spatial-feasibility checks (NEW v0.2; per Reviewer Drawback 5)

Performed during construction (not just at validator):

- **Envelope containment**: as each segment is constructed, assert its bounding box ⊆ envelope rectangle. If overflow, narrow width per § 4.3 fallback chain or raise.
- **Self-intersection**: as each segment is added to a building path, check against all prior segments via bounding-box-pair overlap test. If overlap detected outside junction tolerance, raise `CorridorSelfIntersectionError` (this is a programmer error in the topology dispatcher; should not happen with correct § 4.1 implementation).
- **Junction snap**: at every JUNCTION, after both adjoining segments are placed, force junction endpoint to exact coordinates `(min(start1.x, end2.x), min(start1.y, end2.y))` or equivalent — prevents EPSILON_M-scale drift from accumulating across multi-segment paths.

### § 4.8 — Area accounting (NEW v0.4; trapezoid-aware sweep-line union)

**v0.3's rectangle-only sweep-line is invalidated by v0.4 taper zones.** Tapered segments are no longer pure rectangles; they are *axis-aligned trapezoids* in the taper-zone regions. v0.4 extends the algorithm to handle this geometry.

**v0.4 algorithm** (per § 14.14 → § 14.20 refinement):

```python
def _polygon_union_area(segments: tuple[CorridorSegment, ...]) -> float:
    """Compute the true union area of axis-aligned segments-with-tapers
    using a sweep-line over decomposed primitives. NO external dependency.

    Algorithm (verified S31 on 6 test cases):
      1. For each segment, decompose into ≤ 3 axis-aligned rectangles
         + ≤ 4 axis-aligned right-triangles:
           - Constant middle region → 1 rectangle
           - Each taper zone → 1 inner rectangle (narrow-end width)
                              + 2 right-triangles (the widening wedges)
      2. Collect critical x-coordinates from all primitives, plus
         intersection x-coordinates where one primitive's y-bound crosses
         another's.
      3. Sweep over refined x-slabs. Within each slab:
         a. Active primitives have y-intervals that are linear in x
            (constant for rectangles; sloped for triangles).
         b. Merged-height as a function of x is piecewise linear.
         c. Integrate: each piecewise segment is a trapezoid; closed-form
            area calculation.
      4. Sum all sub-slab contributions.

    Time complexity: O(N³ log N) where N = primitives count. For C8's
    expected ≤ 8 segments per candidate (≤ 24 primitives after taper
    decomposition), this is ~80,000 operations. Well under 1ms per
    candidate.

    Decomposition arithmetic verified S31:
      Tapered segment 1.0m → 1.5m over 1m length decomposes to:
        1 inner rect (1.0 × 1.0 = 1.0 m²)
        + 2 right triangles (each 0.5 × 0.5 / 2 = 0.125 m²)
        = 1.25 m² total
      Matches analytical trapezoid area: (1.0 + 1.5) / 2 × 1.0 = 1.25 m². ✓
    """
```

**Verification cases** (passed at S31; monte-carlo with 400,000 samples):

| Case | Topology | Expected | Monte Carlo |
|---|---|---|---|
| Disjoint rectangles | trivial | 4.0 | 4.009 |
| Two overlapping rectangles | trivial | 7.0 | 7.034 |
| L-shape no taper (v0.3 case) | L_SHAPE | 7.0 | 7.032 |
| COURTYARD ring no taper (v0.3 case) | COURTYARD | 16.0 | 15.960 |
| **L-shape with taper at junction (NEW v0.4)** | L_SHAPE+taper | 6.0 ≤ x ≤ 8.5 | **7.226** |
| **COURTYARD with 4 tapered corners (NEW v0.4)** | COURTYARD+taper | 16.0 ≤ x ≤ 18.0 | **16.987** |

The 4 v0.3 cases reproduce within monte-carlo error (~0.05). The 2 new cases sit in expected ranges; corner taper widening adds 1.0 m² over the no-taper baseline (~5% increase as expected for 4 corner widenings on a 5×5 envelope).

**Why decomposition rather than direct trapezoid sweep**: decomposition reduces the implementation surface to "rectangles + axis-aligned right-triangles," both well-understood primitives. Direct trapezoid sweep would require new geometric primitive types and intersection logic. The decomposition approach is verifiable analytically (each segment's primitives sum to the analytical trapezoid area) and reuses the same sweep-line shape as v0.3.

**Provenance reporting** (unchanged interface from v0.3):

```python
total_area_m2 = _polygon_union_area(segments)             # truth (trapezoid union)
additive_sum_m2 = sum(_segment_trapezoid_area(s) for s in segments)  # diagnostic
overlap_area_m2 = additive_sum_m2 - total_area_m2         # diagnostic
```

`provenance.envelope_area_consumed_m2 = total_area_m2`
`provenance.additive_sum_m2`, `provenance.overlap_area_m2` — diagnostic.
`provenance.envelope_area_fraction = total_area_m2 / (grid.envelope_width_m * grid.envelope_depth_m)`

C9 reads `envelope_area_consumed_m2`. **C8 does NOT pre-fetch C9's needs** (Pattern E avoidance — § 14.5).

### § 4.9 — Consumption-band classification (NEW v0.3; advisory only)

After area accounting, C8 classifies the candidate's corridor area consumption into a qualitative band (per § 14.15 / Walk #2 Drawback 9):

```python
class ConsumptionBand(str, Enum):
    LOW    = "low"      # envelope_area_fraction < 0.12  — efficient circulation
    MEDIUM = "medium"   # 0.12 ≤ fraction < 0.20         — typical residential
    HIGH   = "high"     # fraction ≥ 0.20                — corridor-heavy plan
```

The thresholds (12% / 20%) are **advisory defaults**. Configurable via `CorridorDesignConfig.consumption_band_thresholds: tuple[float, float] = (0.12, 0.20)`. Empirical calibration deferred to **B-NNN-N** (real-plan data analysis).

**C8 takes no action on this classification.** It is metadata only — passed to downstream consumers (C14 evaluation, C15 ranking) which decide what to do with it. Pre-empting their decision logic at C8 would violate Pattern E.

`CorridorPath.consumption_band` exposes the classification.

---

### § 4.10 — Junction-width local propagation (NEW v0.4; replaces v0.3 § 4.3 global-max)

Per § 14.20 (Walk #3 Drawback 3), v0.3's "junction inherits max width from all adjoining segments, all segments inflate to max" was rejected as cascading — one wide segment globally inflated the entire corridor.

v0.4 algorithm (`width_propagation == JUNCTION_LOCAL_ONLY`, default):

```python
def propagate_junction_widths(segments: list[CorridorSegment],
                              config: CorridorDesignConfig,
                              grid: Grid) -> list[CorridorSegment]:
    """For each JUNCTION endpoint, compute the inherited width as the MAX
    of adjoining segments' constant_width_m. Each adjoining segment then
    tapers from that junction-max at the junction end, back to its own
    constant_width_m over the taper_zone_m length. The constant middle
    region keeps the segment's requested width.

    Localizes width inheritance: a wide PRIMARY segment no longer inflates
    the BRANCH; the BRANCH only widens in the taper zone adjacent to the
    junction.
    """
    # 1. Build a junction-coordinate → adjoining-segments map.
    junction_index: dict[tuple[float, float], list[int]] = ...
    
    # 2. For each junction, compute the inherited width.
    for junction_pt, seg_indices in junction_index.items():
        junction_width = max(segments[i].constant_width_m for i in seg_indices)
        
        # 3. For each segment touching this junction, set its
        #    start_width_m or end_width_m (whichever endpoint matches) to
        #    the junction width. Resolve the taper_zone_m via § 4.3.1.
        for i in seg_indices:
            seg = segments[i]
            taper_m = resolve_taper_zone_m(config, grid, seg.length_m)
            
            if seg.start.point_m == junction_pt:
                segments[i] = replace(seg,
                    start_width_m=junction_width,
                    taper_zone_m=taper_m,
                )
            else:  # end matches junction
                segments[i] = replace(seg,
                    end_width_m=junction_width,
                    taper_zone_m=taper_m,
                )
    
    return segments
```

**Worked example** (L_SHAPE, PRIMARY=1.65m, BRANCH=1.20m, bay_min=3.3m):

| Region | v0.3 width (global-max) | **v0.4 width (local)** |
|---|---|---|
| PRIMARY constant middle | 1.65m | 1.65m |
| PRIMARY taper into junction | (no taper; uniform 1.65m) | tapers from 1.65m → 1.65m (no change at junction; this end is already wide) |
| **JUNCTION POINT** | 1.65m | **1.65m** (inherited max) |
| BRANCH taper out of junction | (no taper; uniform 1.65m) | tapers from **1.65m** → 1.20m over `taper_zone_m = 3.3m` |
| BRANCH constant middle | 1.65m | **1.20m** (back to requested width) |
| BRANCH far-end taper | (none) | (none; far end is not a junction) |

**Net effect**: BRANCH constant middle is 1.20m as requested (not v0.3's inflated 1.65m). Wide-PRIMARY corridor area inflation is contained to the taper zone adjacent to the junction (one bay-min of length).

**Alternative configurations**:
- `width_propagation == GLOBAL_MAX_INHERITANCE`: v0.3 behavior. Entire BRANCH inflates to 1.65m. Use only for back-compat tests.
- `width_propagation == INDEPENDENT_WIDTHS`: v0.2 behavior. Junction has step discontinuity (1.65m abruptly drops to 1.20m). Logs `"junction_width_step_at_segment_N"` in provenance. Use only for explicit architect-driven step-down corridors (rare).

**Trade-off acknowledged**: local propagation requires segments to model *variable* width along their length (taper zones), which complicates area accounting (§ 4.8 → trapezoid union, not rectangle union) and introduces 5 new invariants (16-20). This complexity was deliberately accepted per Ramalingam direction at walk #3 close.

---

## § 5 — Invocation contract (public)

```python
designed = design_corridors(
    oriented_candidates=c6_output,
    grid=c7_grid,                              # Grid, not "structural_grid"
    plot_analysis=plot_analysis,
)  # config defaults are fine for v1
```

Cardinality: 1-3 in → 1-3 out, position-paired.

---

## § 6 — Failure modes

| Condition | Behavior |
|---|---|
| `oriented_candidates` is empty tuple | Returns empty tuple |
| `oriented_candidates` is not a tuple | `TypeError` |
| `grid` is not a `Grid` | `TypeError` |
| `plot_analysis` is not `PlotAnalysis` | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066) |
| Plot too small to fit smallest GRID_FRACTION ≥ `regulatory_min_width_m` | `CorridorTooNarrowError(B-NNN-B)` |
| Grid envelope < 5×5m (C7 minimum) | Should never reach C8 (C7 raises first); defensive `ValueError` |
| L_SHAPE topology but candidate's refined_zone_bands has < 2 distinct cardinal directions | Validator fail (defensive) |
| Self-intersection during construction | `CorridorSelfIntersectionError` (programmer error — see § 14.17) |
| Topology dispatch produces invalid geometry on dry-run | `CorridorDispatchError` with diagnostic metadata (NEW v0.3; enriched v0.4 / § 14.23) |
| Junction angle outside `{0°, 90°, 180°, 270°}` ± tolerance | Validator fail (NEW v0.2) |
| Junction-width mismatch when `width_propagation` ≠ `INDEPENDENT_WIDTHS` | Validator fail (refined v0.4) |
| Snap-line that passes through zero columns | Validator fail (NEW v0.3 invariant 14) |
| Taper zone exceeds half segment length | Truncated to `segment_length_m / 2` per § 4.3.1; logged in provenance |
| Constant-width middle region < segment_length / 2 | Validator fail (NEW v0.4 invariant 20) |
| Tapered edge subjected to grid-snap | Validator fail (NEW v0.4 invariant 17) |
| Segment overflows envelope after width assignment | Triggers § 4.3 narrowing fallback; if exhausted, `CorridorTooNarrowError` |

---

## § 7 — Test plan

NEW v0.2 test additions (~30 net):

- `test_c8_spatial_model.py` — NEW (Drawback 1): `ZoneBandEnvelope` derivation across 4-band, 3-band, COURTYARD; corner-strip overlap; CIRCULATION-skip. ~15 tests.
- `test_c8_grid_quantization.py` — NEW (Drawback 2): `GRID_FRACTIONS` selection across bay sizes; `NEAREST_GRID_LINE`; `NONE_FREE_WIDTH` warning; edge alignment vs centerline. ~20 tests.
- `test_c8_geometric_connectivity.py` — NEW (Drawback 3): coordinate-coincident vs near-coincident; junction-angle enforcement; ε-tolerance boundary. ~10 tests.
- `test_c8_spatial_feasibility.py` — NEW (Drawback 5): envelope containment; self-intersection detection; junction-only-overlap. ~15 tests.
- `test_c8_area_accounting.py` — NEW (Drawback 6): area consumed; envelope fraction; junction-overlap subtraction. ~5 tests.
- `test_c8_has_corridor_flag.py` — NEW (Drawback 7): degenerate path with `has_corridor=False`; validator tier split. ~10 tests.

Plus retained from v0.1 plan (~80 tests across topology dispatch, widths, validator, select, immutability, failure modes).

**Total target**: ~155 tests across 9 files.

---

## § 8 — KB references

(unchanged from v0.1 + 1 row added)

| KB | Status | Used for |
|---|---|---|
| NBC 2016 Part 4 | external; partially verified | regulatory_min_width_m default |
| TNCDBR 2019 rule 42 | referenced; text not retrieved | regional override hook (B-NNN-D) |
| Neufert Architects' Data | external; widely-used | comfort_target_width_m default |
| Architecture v2 § 8 | internal | NE 30×40 worked example |
| **Industry gridline practice** (Archlogbook, LinkedIn Construction Gridlines, USPTO grid patents) | **NEW v0.2; verified S31** | **Edge-snap, not centerline-snap** (§ 14.2) |

---

## § 9 — Out of scope

(v0.1 list + 3 rows added)

| Item | Backlog ID |
|---|---|
| Diagonal corridor segments | B-NNN-E |
| Multi-floor vertical corridor coordination | B-NNN-F |
| Per-room door placement on corridor | C13 |
| Circulation-quality scoring | C14 CirculationAnalyzer |
| Furniture-fit checks for corridor | C9 / accessibility backlog |
| Variable-width within single segment | B-NNN-G |
| Stair sizing / integration | C12 |
| **Primary-source verification of NBC 0.9m corridor minimum** | B-NNN-A |
| **Hard "corridor too narrow" graceful fallback** | B-NNN-B |
| **Rotated structural grids** | B-NNN-C |
| **TNCDBR rule 42 + city-specific corridor overrides** | B-NNN-D |
| **NEW v0.2: Per-room ZoneBandEnvelope refinement** (C9 / C11a override hook) | **B-NNN-H** |
| **NEW v0.2: Cross-segment width interaction model** (variable widths along path connectivity) | **B-NNN-I** |
| **NEW v0.2: Area-budget-aware corridor sizing** (full system loop where C8 width responds to C9 area pressure) | **B-NNN-J** |
| **NEW v0.2: C5 ↔ C8 length-drift integration test** (replaces removed § 4.5) | **B-110** |
| **NEW v0.3: Band-importance-weighted strip allocation** | **B-NNN-K** |
| **NEW v0.3: Polygon-union via shapely (if axis-aligned algorithm proves insufficient)** | **B-NNN-L** |
| **NEW v0.3: Junction transition segments / fillets** (B-NNN-E gated) | **B-NNN-M** |
| **NEW v0.3: Empirical thresholds for consumption_band** | **B-NNN-N** |
| **NEW v0.4: Width-selection scoring + taper-length empirical calibration** | **B-NNN-O** |
| **NEW v0.4: Width interpolation in junction-adjacent regions implementation** | **B-NNN-P** |
| **NEW v0.4: Envelope-symmetry secondary-criterion weight calibration** | **B-NNN-Q** |

(B-NNN placeholders to be assigned at LOCK time. B-110 reserved as the first concrete number after B-107 since it's narrowly-scoped and likely-to-implement-soon.)

---

## § 10 — Provenance

`CorridorProvenance` carries (NEW v0.2 fields marked):

- `derived_at`, `oriented_candidate_trace_id`, `grid_trace_id`
- `config_snapshot` (frozen)
- `rule_trace` — sequence of decisions (snap-success, fallback-fired, narrowing-applied, etc.)
- `fallback_used`
- **NEW v0.2: `envelope_area_consumed_m2`** (Drawback 6 — published for C9)
- **NEW v0.2: `envelope_area_fraction`** (Drawback 6)

Plus the `GridAlignmentReport` carried inside `CorridorPath` (replaces v0.1's raw `grid_snap_offsets` mapping).

---

## § 11 — Spec metadata

- **Version**: v0.4 PROPOSED
- **Status**: PROPOSED. PENDING Ramalingam LOCK adjudication; not yet build-ready.
- **Lineage**: v0.1 DRAFT (S31) → v0.2 PROPOSED (S31; walk #1 + V-A) → v0.3 PROPOSED (S31; walk #2 + 9 ADs) → **v0.4 PROPOSED (S31; walk #3 + 6 ADs § 14.19–§ 14.24 + 3 new B-NNNs)**
- **Authoring session**: S31
- **Companion artifacts**: C5 SPEC v0.9 LOCKED; C6 SPEC v0.7 LOCKED; C7 `Grid` schema (verified S31)
- **Web research surface (Rule 7)**: NBC + TNCDBR + Neufert + industry-gridline-practice (v0.2). v0.3 walk: column-line = structural-line consensus (§ 14.13). **v0.4 walk: residential corridor over-design and under-design BOTH have real costs (Quora, Coohom, Constructive Laws); refutes v0.3's framing that downward bias was the only systematic harm. Drives § 14.19 scored selection. No external standards found for residential taper-zone length; § 14.20 default is reasoned, not standards-bound (B-NNN-O for empirical).**
- **Empirical verification at S31** (Rule 7 mandate):
  - Width-selection scored rule verified: never extreme over-design (worst 1.50m at 3.0m bay), never extreme under-design (worst 1.10m at 3.3m bay) across 7 official C7 bay sizes.
  - Trapezoid sweep-line union verified via monte-carlo on 6 cases (4 v0.3 cases reproduce; new L-shape-with-taper = 7.23 m²; new COURTYARD-with-4-tapered-corners = 16.99 m²).
  - Trapezoid decomposition verified analytically: 1.0m → 1.5m taper over 1m = 1 inner rect (1.0 m²) + 2 right triangles (0.125 m² each) = 1.25 m² total (matches analytical trapezoid area exactly).

---

## § 12 — Backlog enumeration (preliminary; B-NNNs assigned at LOCK)

Total: **18 items** (v0.1: 7; v0.2: +4 = 11; v0.3: +4 = 15; v0.4: +3 = 18). All OUT-of-scope this build.

### B-NNN-A — Primary-source verification of NBC residential corridor minimum width
(unchanged from v0.1)

### B-NNN-B — CorridorTooNarrowError handling: graceful fallback vs raise
(unchanged from v0.1)

### B-NNN-C — Rotated structural grid support
(unchanged from v0.1)

### B-NNN-D — TNCDBR rule 42 + city-specific corridor-width overrides
(unchanged from v0.1)

### B-NNN-E — Diagonal corridor segments
(unchanged from v0.1)

### B-NNN-F — Multi-floor vertical corridor coordination
(unchanged from v0.1)

### B-NNN-G — Variable-width corridor along a single segment
(unchanged from v0.1)

### B-NNN-H — Per-room ZoneBandEnvelope refinement (C9 / C11a override hook) — NEW v0.2

**Origin**: C8 v0.2 § 14.1 known-unknown surface. The directional-strip spatial model in § 4.0 is intentionally simple. C9 (Room Sizer) or C11a (Topology Mutation) may need finer band rectangles than uniform envelope strips.
**Status**: BACKLOG (deferred design dialogue).
**Description**: When C9 ships, it may want to refine band extents based on actual furniture-fit calculations rather than accepting C8's uniform-strip model. Resolve via C8/C9 contract dialogue at C9-build time. Options at that point: (a) C8 accepts an optional `band_envelopes_override` parameter from C9; (b) C8 produces strips and C9 *replaces* them entirely in its own output dataclass; (c) the spatial-model decision moves out of C8 into a shared upstream component.
**Trigger**: C9 LOCK or first failing C9 test that reveals the strip model is too coarse.
**S31-scope verdict**: OUT — v1 ships with strip model.
**Effort**: M.

### B-NNN-I — Cross-segment width interaction model — NEW v0.2

**Origin**: C8 v0.2 § 4.3 — width is per-segment but no rule says adjacent segments at a junction must agree. v0.1's `allow_width_variation_per_segment: True` permits any width difference; in practice this creates awkward steps at junctions.
**Status**: BACKLOG.
**Description**: Define how adjacent segment widths interact at junctions (force-equal, allow-step-with-fillet, allow-arbitrary). v1 allows arbitrary (logged in provenance).
**Trigger**: Aesthetic / experience-quality signal OR first user complaint about "stepped corridor" rendering.
**S31-scope verdict**: OUT.
**Effort**: S.

### B-NNN-J — Area-budget-aware corridor sizing — NEW v0.2

**Origin**: C8 v0.2 critique walk Drawback 6.
**Status**: BACKLOG.
**Description**: Full system loop where C8's width responds to C9's room-sizing pressure (e.g., narrow corridor when C9 reports rooms are tight). v1 is one-way: C8 publishes area, C9 reads it. Bidirectional negotiation deferred.
**Trigger**: Empirical signal that v1 corridor area choices systematically push C9 over feasibility thresholds.
**S31-scope verdict**: OUT — v1's one-way contract is a deliberate Pattern E avoidance.
**Effort**: L.

### B-110 — C5 ↔ C8 length-drift integration test — NEW v0.2

**Origin**: C8 v0.2 § 4.5 (replaces removed v0.1 § 4.5 sanity check).
**Status**: BACKLOG (low effort; should land soon after C8 SHIP).
**Description**: Cross-component integration test that exercises real C5 candidates through real C8 and asserts `c5.approx_length_m` vs `c8.total_length_m` drift is within an empirically-derived envelope (likely ±20% based on grid-quantization range). Detects systemic divergence (C5 sketch heuristic out of sync with C8 reality) without false-alarming on legitimate per-candidate variation.
**Trigger**: C8 SHIPs.
**S31-scope verdict**: OUT of C8-build scope; in scope as a follow-up integration task.
**Effort**: S.

### B-NNN-K — Band-importance-weighted strip allocation — NEW v0.3

**Origin**: C8 v0.3 § 14.16 (Walk #2 Drawback 1 partial-resolution).
**Status**: BACKLOG (deferred design refinement).
**Description**: v1 ships uniform-thickness strips (each band gets `envelope_dim / N` thickness). Real residential plans have non-uniform proportions: PUBLIC typically larger than SERVICE; PRIVATE often fragmented across multiple regions. Refine via empirical weighting (e.g., `LIVING: 0.35, BEDROOM: 0.30, KITCHEN: 0.20, ...`) calibrated against C9 + C11a behavior data.
**Trigger**: (a) C9 reports systematic room-fit failures attributable to coarse band proportions, OR (b) C11a needs to mutate band proportions as part of its operators.
**S31-scope verdict**: OUT — v1 uniform model is intentionally simple; refinement needs empirical data not available yet.
**Effort**: M.

### B-NNN-L — Polygon-union via shapely if axis-aligned algorithm proves insufficient — NEW v0.3

**Origin**: C8 v0.3 § 14.14 (Walk #2 Drawback 7 fallback).
**Status**: BACKLOG (probabilistically low-need).
**Description**: v1 implements axis-aligned-rectangle union via sweep-line (~50 lines, no external dependency). If v2 introduces diagonal segments (B-NNN-E) or other non-axis-aligned geometry, the sweep-line algorithm becomes insufficient. Re-evaluate at that point: either extend the sweep-line to general polygons, or introduce shapely as a dependency.
**Trigger**: B-NNN-E ships OR diagonal/curved corridor segments enter v1.
**S31-scope verdict**: OUT — v1 axis-aligned-only by spec.
**Effort**: S (replace sweep-line with `shapely.ops.unary_union`).

### B-NNN-M — Junction transition segments / fillets — NEW v0.3

**Origin**: C8 v0.3 § 14.12 (Walk #2 Drawback 4 deferred refinement; supersedes v0.2's B-NNN-I framing).
**Status**: BACKLOG (aesthetic refinement).
**Description**: v1 enforces equal width at junctions (eliminates step discontinuities). Architecturally finer designs use fillets (curved transitions) or chamfered tapers at junctions for visual polish. Implementing requires non-axis-aligned geometry (currently forbidden by § 14.1.3) — the unblock is jointly with B-NNN-E (diagonal segments).
**Trigger**: B-NNN-E ships OR aesthetic-quality signal from real-plan reviews.
**S31-scope verdict**: OUT — v1 axis-aligned + equal-width junctions is the simplest correct design.
**Effort**: M.

### B-NNN-N — Empirical thresholds for consumption_band — NEW v0.3

**Origin**: C8 v0.3 § 14.15 (Walk #2 Drawback 9 follow-up).
**Status**: BACKLOG (calibration; pre-empirical).
**Description**: v1 ships LOW/MEDIUM/HIGH thresholds at 12% / 20% as educated-guess defaults. Calibrate against real Indian residential plans (target dataset: ResPlan or comparable; ~100+ plans across plot sizes and tier classifications) to validate or revise the thresholds. Likely outcome: bracket may shift slightly (e.g., 10% / 18%); category labels stable.
**Trigger**: C8 SHIPs + ≥ 50 v1-production plans with measured consumption fractions OR explicit calibration sprint.
**S31-scope verdict**: OUT — calibration without data.
**Effort**: S (one analyst-day with the data).

---

**Total v0.3 backlog**: **15 items** (was 11 in v0.2; +4 from this critique walk = K, L, M, N).

### B-NNN-O — Width-selection scoring + taper-length empirical calibration — NEW v0.4

**Origin**: C8 v0.4 § 14.19 (scoring weights) + § 14.20 / § 4.3.1 (taper-length default).
**Status**: BACKLOG (calibration; pre-empirical).
**Description**: Two related calibration questions: (a) `under_comfort_penalty_ratio = 2.0` default produces architecturally-sensible results across 7 C7 bay sizes per S31 verification, but the 2:1 ratio is an educated guess; validate against real-plan satisfaction surveys or downstream feasibility data. (b) Taper-zone length default `min(bay_x, bay_y)` is reasoned-not-standards-bound (no industry-standards guidance found at S31 web research); validate against real-plan rendering and architect feedback.
**Trigger**: C8 SHIPs + ≥ 50 v1 production plans with measured corridor-quality signals OR explicit calibration sprint.
**S31-scope verdict**: OUT — calibration without data.
**Effort**: S (one analyst-day with the data).

### B-NNN-P — Width interpolation in junction-adjacent regions implementation — NEW v0.4

**Origin**: C8 v0.4 § 14.20 implementation work.
**Status**: BACKLOG (build-time, not spec-time).
**Description**: The local-propagation algorithm (§ 14.20) requires `CorridorSegment` to model variable width via taper zones with linear interpolation. v0.4 spec defines the contract; implementation must translate to working code with attention to edge cases: very-short segments (taper truncation per § 4.3.1), segments with both ends as junctions (two tapers per segment), zero-width-difference junctions (no taper needed but contract still has `start_width_m == constant_width_m`).
**Trigger**: C8 build session.
**S31-scope verdict**: OUT — implementation work, not spec.
**Effort**: M (real architectural work; ~2-3 days).

### B-NNN-Q — Envelope-symmetry secondary-criterion weight calibration — NEW v0.4

**Origin**: C8 v0.4 § 14.21 (`envelope_symmetry_weight = 0.3` default).
**Status**: BACKLOG (calibration).
**Description**: The 0.3 weight is an educated guess balancing primary edge-snap criterion against secondary envelope-symmetry. Validate against real-plan rendering: does the secondary criterion meaningfully stabilize ZoneBandEnvelope placement, or is it noise? Tune weight if needed.
**Trigger**: C8 SHIPs + visual review of 20+ production plans with grid-offset envelopes.
**S31-scope verdict**: OUT.
**Effort**: S.

---

**Total v0.4 backlog**: **18 items** (v0.1: 7; v0.2: +4 = 11; v0.3: +4 = 15; v0.4: +3 = 18). All OUT-of-scope this build.

---

## § 13 — Definitions

(v0.1 retained + v0.2 additions)

- **CorridorPath** *(v0.1; v0.2 + has_corridor flag, envelopes tuple, total_area_m2, grid_alignment field)*
- **CorridorSegment**, **CorridorEndpoint** *(v0.1; v0.2 + coordinate-exactness contract)*
- **ZoneBandEnvelope** *(NEW v0.2; § 4.0)*: bounding rectangle for one ZoneBand; derived by C8 from `refined_zone_bands` + `Grid` envelope dims via the directional-strip model.
- **Directional-strip model** *(NEW v0.2; § 4.0)*: spatial-model algorithm assigning each cardinal band a strip of the buildable envelope along its facing direction.
- **GRID_FRACTIONS** *(NEW v0.2)*: width quantization mode where corridor widths are chosen from `{1/4, 1/3, 1/2, 2/3, 3/4} × min(bay_x, bay_y)`.
- **Edge-snap** *(NEW v0.2; § 4.2)*: alignment policy where corridor *edges* (not centerlines) align to grid lines. Matches industry practice.
- **EPSILON_M** *(NEW v0.2)*: coordinate-coincidence tolerance for geometric connectivity (default 0.001m = 1mm).
- **`has_corridor` flag** *(NEW v0.2; § 4.3.1)*: boolean on `CorridorPath` distinguishing real-corridor outputs from degenerate-path (small T1 STRIP) outputs. Replaces v0.1's "documented quirk" framing.
- **Length sanity check** *(REMOVED v0.2)*: was v0.1 § 4.5; deleted because C5 sketch length and C8 grid-quantized length are not comparable. Diagnostic moved to B-110 integration test.
- **Taper zone** *(NEW v0.4; § 4.3.1, § 14.20)*: a region within a CorridorSegment where width interpolates linearly between `start_width_m` (or `end_width_m`) and `constant_width_m`. Default length: `min(grid.bay_x_m, grid.bay_y_m)`; truncates to `segment_length_m / 2` when default exceeds.
- **Constant middle** *(NEW v0.4)*: the region of a CorridorSegment between its two taper zones, with uniform `constant_width_m`. By invariant 20, must be ≥ 50% of segment length.
- **Width propagation** *(NEW v0.4; § 14.20)*: how junction widths propagate to adjoining segments. Three modes: `JUNCTION_LOCAL_ONLY` (default; via taper zones), `GLOBAL_MAX_INHERITANCE` (v0.3 behavior; deprecated), `INDEPENDENT_WIDTHS` (v0.2 behavior; allows step discontinuity).
- **Scored width selection** *(NEW v0.4; § 14.19)*: width-selection rule using asymmetric penalty (`under_comfort_penalty_ratio = 2.0` default × under-comfort distance vs 1.0 × over-comfort distance). Replaces v0.3 binary "smallest ≥ comfort" rule.
- **Trapezoid decomposition** *(NEW v0.4; § 4.8 / § 14.20)*: a tapered CorridorSegment decomposes into ≤ 3 axis-aligned rectangles + ≤ 4 axis-aligned right-triangles for area-accounting purposes. Each tapered region = 1 inner rect + 2 right-triangles (the widening wedges).
- **Envelope-symmetry secondary criterion** *(NEW v0.4; § 14.21)*: edge-snap tiebreak preferring grid-line pairs whose midpoint is closest to envelope center. Weighted at `envelope_symmetry_weight = 0.3` default vs primary alignment criterion.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 (DRAFT)
§ 14.1–§ 14.8 — (preserved; v0.1 numbering shifts to v0.1.x slots below)

(v0.1 ADs renumbered as v0.1-era to avoid collision with v0.2 ADs):
- § 14.1.1 — C8's scope is geometry, not scoring (was v0.1 § 14.1)
- § 14.1.2 — Topology dispatch is the algorithm core (was v0.1 § 14.2)
- § 14.1.3 — Axis-aligned corridors only in v1 (was v0.1 § 14.3)
- § 14.1.4 — Cardinality preserved across C5 → C6 → C8 chain (was v0.1 § 14.4)
- § 14.1.5 — Regulatory width is a parameter, not constant (was v0.1 § 14.5)
- § 14.1.6 — *(v0.1 § 14.6 "Degenerate path is first-class output" — superseded by v0.2 § 14.7 has_corridor flag; preserved as historical)*
- § 14.1.7 — *(v0.1 § 14.7 "CIRCULATION skip is a quirk" — superseded by v0.2 § 14.7 explicit invariant tier; preserved as historical)*
- § 14.1.8 — *(v0.1 § 14.8 "Length-sanity check is soft" — REVERSED in v0.2 § 14.8; check removed entirely)*

### From v0.2 (PROPOSED — this round) — NEW

#### § 14.1 — Spatial model: C8 owns it (Reviewer Drawback 1; Option A)

**Decision**: C8 derives `ZoneBandEnvelope` rectangles internally from `refined_zone_bands` + `Grid.envelope_width_m/depth_m` via the directional-strip model (§ 4.0).

**Three options considered**:

| Option | Approach | Verdict |
|---|---|---|
| (A) C8 owns the spatial model | This option | **CHOSEN** — boundary aligns with information-availability + Pattern A avoidance |
| (B) Push to C5 or C6 | Modify shipped components | REJECTED — Pattern A risk on shipped specs; C5/C6 don't need spatial info for their own scoring |
| (C) Defer to a later component | Keep C8 sketch-only, push geometry deeper | REJECTED — leaves the same architectural gap, just deeper; creates inconsistency where 3 components are geometry-aware but C8 isn't |

**Rationale**: C5 and C6 model the design *decision*; C8 is the first component to model the design *artifact*. The spatial model belongs on the artifact side. Pushing it earlier pollutes scoring components with geometric info they don't need.

**Known unknown surfaced** (NOT closed by this AD): C9 (Room Sizer) and C11a (Topology Mutation Layer) may need to override or refine `ZoneBandEnvelope`s. v0.2 declares C8's ownership *provisional*. If C9/C11a need finer geometry, the resolution is via the B-NNN-H dialogue at that point — NOT by incrementally amending C8 (Pattern A avoidance). The directional-strip model is intentionally simple so it can be replaced wholesale rather than patched.

**Web research surface (Rule 7)**: not applicable to this AD. The decision is internal-architecture; no external-standards claim.

#### § 14.2 — Width quantization: GRID_FRACTIONS by default (Reviewer Drawback 2)

**Decision**: `CorridorDesignConfig.width_quantization` defaults to `WidthQuantization.GRID_FRACTIONS`. Edge-snap, not centerline-snap. Two opt-outs available (`NEAREST_GRID_LINE`, `NONE_FREE_WIDTH`).

**Rationale (3 reasons)**:

1. **External standards align**: industry practice consistently aligns gridlines to wall centers / column edges, not corridor voids. (Verified S31 web search: Archlogbook, LinkedIn Construction Gridlines, USPTO grid patents.) v0.1's centerline-snap was backwards.
2. **Buildability follows for free**: corridor walls on grid lines means structural beams above them have natural support; no awkward fractional spans.
3. **Algorithm simplification**: removes a class of edge cases (off-grid penalty, off-grid score, off-grid messaging). The grid-snap penalty in v0.1 was a calibration tax on a problem the design itself created.

**Why "with opt-out" rather than "always quantize"**: Indian residential construction has real cases where the architect wants a non-grid corridor (threading between fixed columns from an earlier layout, or aligning with a non-structural feature). The escape hatch is one config field; cost is negligible.

**`GRID_FRACTION_CANDIDATES` set choice** (`{1/4, 1/3, 1/2, 2/3, 3/4}`): chosen because architects subdivide bays at quarters and thirds in practice. Coarser sets (just halves and thirds) considered; rejected as over-restrictive given configurability already exists. Set is exposed as a module constant; can be tuned via B-090 calibration family if empirical data justifies.

**Web research surface (Rule 7)**: VERIFIED. Industry-standard "gridlines align to walls/columns" is the basis for the edge-snap choice. Cited in § 8 KB references.

#### § 14.3 — Geometric connectivity (Reviewer Drawback 3)

**Decision**: Connectivity invariant 4 requires coordinate-coincidence within `EPSILON_M` (default 0.001m / 1mm), not set-theoretic endpoint sharing. New invariant 13: junction angles in `{0°, 90°, 180°, 270°}`.

**Rationale**: v0.1's "endpoint shared" was set-theoretic, allowing a corridor path to be "connected" by symbolic name even if endpoints were geometrically distinct. v0.2 collapses the abstraction: connectivity means *same coordinates*. EPSILON_M = 1mm is below construction tolerance (~5–10mm) so two endpoints within EPSILON are physically the same point.

**Why explicit junction-angle invariant**: the 0°/90° constraint was implicit in v0.1 ("axis-aligned segments") but never stated as a *junction* invariant — two axis-aligned segments could meet at a junction with arbitrary orientation if construction was sloppy. v0.2 makes it explicit + defaults `junction_angle_tolerance_deg = 0.0` (exact).

#### § 14.4 — Length sanity check removed (Reviewer Drawback 4)

**Decision**: v0.1 § 4.5 length-vs-C5-approx-length check is REMOVED in v0.2. Replaced by external integration test (B-110).

**Rationale**: C5's `approx_length_m` is sketch-grade. C8's `total_length_m` is grid-quantized truth. The two are legitimately different (drift of 5–15% from grid quantization alone is normal). Comparing them at C8-time created false warnings without diagnostic value. Removing the check is honest; the integration-test alternative (B-110) preserves the systemic-drift signal at the right granularity.

#### § 14.5 — Provenance-only contract with C9 (Reviewer Drawback 6)

**Decision**: C8 publishes `envelope_area_consumed_m2` and `envelope_area_fraction` in provenance. C9 reads it. C8 does NOT pre-fetch C9's needs.

**Rationale**: Pattern E (scope-creep-mid-build) avoidance. The reviewer's diagnosis (corridor width affects C9 feasibility) is correct. The reviewer's solutions (compute max allowable corridor from area budget; feed width constraints from upstream) require C8 to know C9's room-sizing model — coupling that doesn't exist yet and shouldn't be invented at C8-build time.

The honest fix: publish what C8 knows; let C9 read it; defer bidirectional negotiation to B-NNN-J when empirical signal justifies it.

#### § 14.6 — `has_corridor` flag, not "documented quirk" (Reviewer Drawback 7)

**Decision**: Add `CorridorPath.has_corridor: bool`. Split validator invariants into ALL-PATHS and HAS-CORRIDOR-ONLY tiers (§ 4.6).

**Rationale**: v0.1's "documented quirk" (degenerate-STRIP path produces a special-case CorridorPath that the validator partially skips) was a smell. The `has_corridor` flag makes the distinction first-class in the type system: downstream code branches on the flag, not on undocumented validator-skip behavior. The invariant tier-split is the natural consequence — invariants that depend on segment existence move to HAS-CORRIDOR-ONLY.

#### § 14.7 — CIRCULATION band has no envelope (refines v0.1 § 14.7)

**Decision**: CIRCULATION band intentionally has NO `ZoneBandEnvelope` because it IS the corridor. Validator invariant 7 (HAS-CORRIDOR-ONLY tier) explicitly asserts this.

**Rationale**: Same logic as v0.1 § 14.7, but now formalized: rather than a "documented quirk," it's a typed invariant. Reviewers looking for missing envelope coverage are pointed to the invariant.

#### § 14.8 — Reverses v0.1 § 14.8 (length sanity reversal)

**Decision**: v0.1 § 14.8 ("Length-sanity check is soft, not hard") is REVERSED in v0.2. The check is REMOVED entirely (§ 14.4 above + § 4.5).

**Rationale**: v0.1 § 14.8 defended the check as a soft warning. The reviewer's Drawback 4 surfaced that even a soft warning is wrong because the baseline (C5 approx length) is incomparable to C8's grid-quantized truth. The check produced noise, not signal. Removing it is honest; the systemic-drift question moves to integration-test scope (B-110).

#### § 14.9 — V-A self-found defect: C7 contract correction

**Decision**: v0.1 § 4.2 referenced phantom fields `column_lines_x` and `column_lines_y` on a non-existent `StructuralGrid` dataclass. v0.2 corrects:
- Type: `Grid` (from `buildemup.components.c07.grid_generator`), not `StructuralGrid`.
- Field access: derive line coordinates from `Grid.columns: list[ColumnPosition]` via `derive_grid_lines()` helper; do not assume pre-computed line tuples.
- Envelope dims: `Grid.envelope_width_m`, `Grid.envelope_depth_m` (these exist).

**Rationale**: Rule 7's code-grep mandate caught this at S31 critique walk #1. v0.1 was authored without grepping C7's actual schema (an open question in v0.1 § 15 Q1, deferred to "first critique walk"). v0.2's spec-correctness depended on doing it now rather than later — without the fix, the spec described an algorithm that could not be implemented because its inputs don't exist.

**Lesson surfaced** (for future v0.1 drafts of other components): grep the upstream schema BEFORE drafting, not as a deferred-question. Filed mentally as a pre-draft checklist item, not a backlog entry (it's a process improvement, not deferred work).

### From v0.3 (PROPOSED — this round) — NEW

#### § 14.10 — Corner-overlap deterministic resolution (Walk #2 Drawback 5)

**Decision**: When two adjacent cardinal strips overlap at a corner of the buildable envelope, ownership is assigned by band-priority order: **PUBLIC > PRIVATE > SERVICE**. Overlap rectangle goes to the higher-priority band; the loser's envelope is clipped at the overlap boundary.

**Rationale**: PUBLIC (living, dining, foyer) is the entry-bearing band with most foot traffic — it earns corner real estate. PRIVATE (bedrooms) needs the corner less for traffic but more for window placement. SERVICE (kitchen, utility) is the most spatially flexible, lowest sensitivity to corner-vs-middle placement. This mirrors Indian residential vernacular: living rooms claim corner positions; bedrooms align along sides; service zones tuck into central or service-end positions.

**Tie-break** (rare; only possible if multiple bands of the same type exist, which v1 doesn't support per `refined_zone_bands` cardinality): lexicographic on band name.

**Web research surface (Rule 7)**: not applicable to this AD. The decision is internal-architecture; no external-standards claim.

#### § 14.11 — Width-selection rule: bias upward (Walk #2 Drawback 2)

**Decision**: GRID_FRACTIONS selection rule changed from "candidate closest to comfort_target" (v0.2) to "smallest candidate ≥ comfort_target; fallback largest candidate ≥ regulatory_min if none meet comfort" (v0.3).

**Rationale**: Empirically verified at S31 against actual C7 `PREFERRED_BAY_SIZES_M = [2.7, 3.0, 3.3, 3.6, 4.0, 4.5, 5.0]`. v0.2's "closest" rule produced sub-comfort widths on **3 of 7 bay sizes** (3.0m → 1.0m, 3.3m → 1.1m, 4.5m → 1.13m — all extremely common in Indian residential). The bias was systematic and silent — every project on those bay sizes shipped with corridors below the 1.2m comfort target.

v0.3's "smallest ≥ comfort" rule produces ≥ 1.2m on **all 7** official bay sizes:

| Bay (m) | v0.2 chosen | v0.3 chosen |
|---|---|---|
| 2.7 | 1.35m ✓ | 1.35m ✓ |
| **3.0** | **1.00m ✗** | **1.50m ✓** |
| **3.3** | **1.10m ✗** | **1.65m ✓** |
| 3.6 | 1.20m ✓ | 1.20m ✓ |
| 4.0 | 1.33m ✓ | 1.33m ✓ |
| **4.5** | **1.13m ✗** | **1.50m ✓** |
| 5.0 | 1.25m ✓ | 1.67m ✓ |

**Trade-off acknowledged**: v0.3 is more area-consuming. A 3.0m-bay 1.5m corridor uses 50% of the bay vs v0.2's 33%. This is a deliberate choice — the comfort target is the floor, not a ceiling to approach from below. Total corridor area impact is monitored via `consumption_band` (§ 14.15) and Pattern E flag in B-NNN-J if it becomes systemically problematic.

**Pushback alternative considered**: weighted-distance scoring with asymmetric penalty. Rejected as over-engineered for v1; the binary "above/below comfort" rule is honest and inspectable.

**Web research surface (Rule 7)**: not applicable. Internal rule choice based on empirical bay-size analysis.

#### § 14.12 — Junction-width equality default (Walk #2 Drawback 4)

**Decision**: New config field `equal_width_at_junctions: bool = True`. When True (default), all segments meeting at a JUNCTION endpoint must have equal width; junction inherits the maximum requested width across adjoining segments. Validator invariant 15 enforces.

**Rationale**: v0.2 declared "variable widths permitted (logged in provenance)" via B-NNN-I. The reviewer correctly identified this as a real geometric defect, not aesthetic — step discontinuities at L_SHAPE bends and COURTYARD corners produce physically awkward and structurally questionable junctions. Equal-width default eliminates the issue.

**Why "equal" not "fillet/taper"**: transition geometry (chamfered corners, curved fillets) introduces non-axis-aligned segments which v1 explicitly forbids (§ 14.1.3 axis-aligned only). Equal-width is the simplest fix that preserves axis-alignment. Fillets deferred to **B-NNN-M**.

**Why opt-out exists**: rare cases where the architect explicitly designs a step-down corridor (e.g., widening at a stair landing). One config flag costs nothing.

**Web research surface (Rule 7)**: not applicable.

#### § 14.13 — Column-supported snap-lines (Walk #2 Drawback 3)

**Decision**: NEW invariant 14 — every grid line used for edge-snap must pass through ≥ 1 `ColumnPosition` in `grid.columns`. Already true by construction in v0.2 (§ 4.2 derives lines from `grid.columns`); the explicit invariant safeguards against future refactors.

**Rationale**: Reviewer correctly identified the underlying concern — "are snap-lines actually structural?" Industry consensus from S31 web research (Eng-Tips, Archisoup): column lines ARE structural; they ARE where columns sit. In C7's `Grid.columns` model, every line passing through a `ColumnPosition` is column-supported by definition. The invariant locks this in.

**What if future C7 introduces non-column reference lines?** The invariant fails fast. The fix at that point: either filter snap-line candidates to column-supported only, or accept reference lines with a documented `non_column_support: bool` flag in `GridAlignmentReport`. v1 does neither — invariant 14 keeps the contract clean.

**Reviewer's framing pushback**: the reviewer wrote "grid columns ≠ wall-support guarantee," implying a distinction between "structural grid" and "reference grid." In C7's actual model, this distinction doesn't exist — `grid.columns` are the columns. The verified industry-standard framing is "column lines are structural columns."

**Web research surface (Rule 7)**: VERIFIED. Industry consensus per Eng-Tips engineer (*"They are column lines, columns are structural"*) and Archisoup (*"Grids play a vital role in determining the placement of primary structural components, such as columns, beams, and load-bearing walls"*).

#### § 14.14 — Area accounting: union, not sum (Walk #2 Drawback 7)

**Decision**: Replace v0.2's "additive sum minus junction overlap" with sweep-line union of axis-aligned rectangles. No external dependency (no shapely); algorithm fits in ~50 lines and handles all v1 topology cases.

**Rationale**: v0.2's incremental subtraction worked only at single-point junctions, missing corner-region overlaps in L_SHAPE (where one arm's full width overlaps the other arm's full width along the corner) and COURTYARD (where 4 corner regions each have width² overlap area). For a 1m corridor at a COURTYARD corner, the missed overlap is 1m² × 4 corners = 4m² (~5% of typical envelope). C9 receiving this incorrect area would systematically underestimate available room area.

**Algorithm choice**: sweep-line over x-coordinates with active y-intervals, merging overlapping intervals per slab. Verified at S31 on 4 cases (disjoint, two-rect overlap, L-shape, courtyard ring) — all correct.

**Why not shapely**: v1 is axis-aligned-only by spec (§ 14.1.3). Shapely's full polygon machinery is overkill; introducing it as a dependency adds install friction (C/Python binding, GEOS C library) for zero v1 benefit. If v2 introduces diagonal segments via B-NNN-E, re-evaluate then via **B-NNN-L**.

**Diagnostic exposure**: `additive_sum_m2` and `overlap_area_m2` exposed in provenance for debugging — they should always satisfy `additive_sum >= union >= envelope_area_consumed`. Drift signals algorithm bugs.

**Web research surface (Rule 7)**: not applicable. Internal algorithm choice.

#### § 14.15 — Consumption-band metadata (Walk #2 Drawback 9; advisory only)

**Decision**: New `CorridorPath.consumption_band: ConsumptionBand` enum (LOW < 12%, MEDIUM 12-20%, HIGH ≥ 20%). C8 takes no action on it; advisory only. Downstream (C14 evaluation, C15 ranking) decides what to do with the signal.

**Rationale**: Reviewer's diagnosis correct — bare `envelope_area_fraction` numbers are dead telemetry without thresholds. Reviewer's solutions overlap with Pattern E (defining thresholds at C8 pre-empts C14/C15 ranking logic). v0.3's compromise: classify the band qualitatively (which gives downstream a stable interface to pivot on), but take no action on it (which preserves C14/C15's authority to define what "too much corridor" means).

**Threshold defaults**: 12% / 20% are educated guesses based on Indian residential vernacular (typical efficient plans have 8-15% circulation; corridor-heavy designs hit 20-25%). Empirical calibration deferred to **B-NNN-N** with real-plan data.

**Configurable via `CorridorDesignConfig.consumption_band_thresholds`**: callers (typically test fixtures) can override.

**Web research surface (Rule 7)**: not applicable. Threshold values are educated guesses pending B-NNN-N calibration; no external-standards claim.

#### § 14.16 — Strip model is provisional v1 (Walk #2 Drawback 1)

**Decision**: The uniform-thickness directional-strip model (§ 4.0) is acknowledged as a v1 simplification. Real residential plans have non-uniform band proportions — PUBLIC typically larger than SERVICE; PRIVATE often fragmented across multiple non-adjacent regions. v1 ships uniform; refinement deferred to **B-NNN-K** (band-importance-weighted strip allocation).

**Rationale**: Reviewer correctly identified that uniform strips can distort downstream layouts. v0.2 acknowledged this implicitly via § 14.1's "provisional ownership" framing; v0.3 makes it explicit as its own AD. The acknowledgment closes the documentation gap without forcing the refinement at v1 build time.

**Why defer rather than fix**: the right band-proportion model depends on empirical data from C9 + C11a (room-fit signals; mutation operator behavior). Pre-empting that at C8-build would be Pattern A (fix-as-bandage based on reviewer intuition rather than data). The strip model is intentionally simple so it can be replaced wholesale rather than patched.

**Pushback acknowledged**: the reviewer's solutions (proportional weighting, non-uniform thickness, band-priority ordering) all have merit for v2. v1 keeps it simple.

**Web research surface (Rule 7)**: not applicable. Internal-architecture acknowledgment.

#### § 14.17 — SelfIntersectionError is deliberate raise (Walk #2 Drawback 8)

**Decision**: `CorridorSelfIntersectionError` retained as a deliberate raise (no soft fallback). NEW: pre-validation step in `design_corridors()` runs the topology-dispatch logic in dry-run mode at session boundary; if dry-run produces invalid geometry for valid inputs, that's caught with `CorridorDispatchError` carrying a backlog item ID — **before** any segment is constructed.

**Rationale**: Reviewer's "production code shouldn't crash" principle is sound generally, but in C8's specific case, self-intersection from valid inputs would mean the topology-dispatch logic itself is buggy. Soft fallback (e.g., "simplify path automatically") would mask Pattern A bugs — silently producing wrong geometry while suppressing the diagnostic signal that the dispatch logic needs fixing.

**The right fix is "fail fast with better diagnostic," not "fail soft with degraded output."** v0.3 splits the failure mode:
- `CorridorDispatchError` (NEW v0.3): raised at session pre-validation when dry-run dispatch produces invalid geometry. Carries a backlog item ID for the offending topology+input combination. Caller can route to alternative candidates.
- `CorridorSelfIntersectionError`: raised only if pre-validation passes but construction-time segment placement still produces overlap. This would indicate a dispatch-vs-construction logic mismatch — a deeper bug worth crashing on.

**Pushback against reviewer's "fragile pipeline" framing**: production pipelines that silently degrade on invalid inputs become impossible to debug. C8's correctness depends on dispatch logic being correct; obscuring failures there harms the product more than the crash does.

**Web research surface (Rule 7)**: not applicable.

#### § 14.18 — Epsilon handling: centralized helper (Walk #2 Drawback 6)

**Decision**: Keep `EPSILON_M = 0.001` (1mm) as default. Add module-level helper `epsilon_m_for(stage)` that returns stage-appropriate tolerances:

```python
def epsilon_m_for(stage: str, *, bay_min_m: float | None = None) -> float:
    """Stage-aware geometric tolerance. Centralized so v1 has one source of truth.

    Stages:
      - "connectivity"          → EPSILON_M (1mm; coordinate-coincident endpoints)
      - "junction_angle"        → config.junction_angle_tolerance_deg (default 0.0)
      - "envelope_containment"  → EPSILON_M * 10 (10mm; envelope dims have own FP)
      - "bay_scaled"            → 0.001 * bay_min_m (for callers wanting bay-relative)
      - "default"               → EPSILON_M
    """
```

**Rationale**: Reviewer's "1mm too strict for accumulated operations" was empirically tested at S31 and found *not* to be true for v0.2's exact-snap design (FP error = 0.0 across all tested cases). However, the reviewer's deeper principle — "centralize geometric tolerance handling" — is sound engineering independent of whether 1mm is currently sufficient. v0.3 adopts the principle without changing the empirically-correct default.

**Why not bay-scaled by default**: bay-scaled epsilons (e.g., `0.001 × bay`) would be 2.7mm at 2.7m bay and 5mm at 5m bay. Not wrong, but the variability invites bugs (a coordinate "coincident" at one bay isn't at another). Fixed 1mm is predictable. The bay-scaled option is exposed for callers who need it.

**Future-proofing**: when v2 introduces diagonal segments (B-NNN-E) or floating-point-heavy operations (e.g., trigonometric junction angles), the centralized helper lets us tune per-stage without scattering changes across the codebase.

**Web research surface (Rule 7)**: not applicable. Internal engineering principle.

### From v0.4 (PROPOSED — this round) — NEW

#### § 14.19 — Scored width selection (replaces v0.3 § 14.11 binary rule)

**Decision**: Width-selection rule changed from "smallest candidate ≥ comfort_target with fallback to largest ≥ regulatory_min" (v0.3) to **asymmetric scored selection** with `under_comfort_penalty_ratio = 2.0` default.

**Rationale**: Walk #3 reviewer + S31 web research both refuted v0.3's framing that downward bias was the only systematic harm. Web findings:
- Quora architect (multi-unit residential): *"12-18% as a practical default for typical multi-unit residential projects"*
- Coohom anti-pattern story: *"the corridor was so wide... we were sacrificing two full kitchen cabinets in every unit... wasted corridor space quietly steals value"*
- Constructive Laws guidance: *"Residential Homes: Keep internal passages minimal to gain more usable space"*

These confirm both over-design and under-design have real costs. v0.3's "smallest ≥ comfort" produced 1.65m corridors on 3.3m bays where 1.10m would be acceptable — exactly the over-design pattern Coohom warned against.

The 2:1 penalty ratio reflects empirical asymmetry: occupants notice under-comfort more readily than over-comfort, so under-penalty stays higher. Ratio is tunable (config + B-NNN-O calibration).

**Empirical outcome on actual C7 bay sizes** (verified S31):

| Bay (m) | v0.2 (closest) | v0.3 (≥ target) | **v0.4 (scored)** |
|---|---|---|---|
| 2.7 | 1.35 ✓ | 1.35 ✓ | 1.35 ✓ |
| 3.0 | 1.00 ✗ | 1.50 ✓ over | **1.50 ✓** |
| 3.3 | 1.10 ✗ | 1.65 over | **1.10** acceptable |
| 3.6 | 1.20 ✓ | 1.20 ✓ | 1.20 ✓ |
| 4.0 | 1.33 ✓ | 1.33 ✓ | 1.33 ✓ |
| 4.5 | 1.12 ✗ | 1.50 over | **1.12** acceptable |
| 5.0 | 1.25 ✓ | 1.25 ✓ | 1.25 ✓ |

v0.4 never extreme over-design (worst case 1.50m at 3.0m), never extreme under-design (worst case 1.10m at 3.3m).

**v0.3 § 14.11 status**: SUPERSEDED. v0.3's binary rule preserved as historical reference; v0.4's scored rule is the active selection mechanism.

**Web research surface (Rule 7)**: VERIFIED — multiple practitioner sources confirm both directions of bias have cost.

#### § 14.20 — Junction-width local-propagation via linear taper (replaces v0.3 § 14.12)

**Decision**: Junction-width handling changes from "global max inheritance — entire segment widens to junction-max" (v0.3 § 14.12) to **local taper-zone propagation** — junction inherits max width; adjoining segments taper from their `constant_width_m` to junction-width over `taper_zone_m`. Default propagation mode: `WidthPropagation.JUNCTION_LOCAL_ONLY`.

**Rationale**: Walk #3 reviewer correctly identified that v0.3's global-max inheritance cascades — one wide PRIMARY (1.65m) inflated all connected BRANCH segments to 1.65m even though the BRANCH only needed 1.20m. Local propagation contains the inflation to within `taper_zone_m` of the junction.

**Architectural surface introduced**:
- `CorridorSegment` gains `start_width_m`, `end_width_m`, `constant_width_m`, `taper_zone_m` (replaces v0.3's single `width_m` field).
- Area accounting (§ 4.8) extends from rectangle-only to trapezoid-aware sweep-line (§ 14.14 refinement).
- 5 new invariants (16-20): taper-zone bound, tapered-edge exclusion, junction-width-match-via-taper, taper monotonicity, constant-width coverage.
- Edge-snap (§ 4.2) applies only to constant-width regions; tapered edges geometrically distinct.

**Taper-zone length default**: `min(grid.bay_x_m, grid.bay_y_m)` — bay-scale is the natural local unit. Configurable; truncates to `segment_length_m / 2` when default exceeds (§ 4.3.1). Empirical calibration → **B-NNN-O**.

**Complexity acceptance**: This is substantially more architectural surface than the v0.3 compromise (independent widths with documented step discontinuity) would have required. Ramalingam explicitly directed at walk #3 close: "Accept the complexity; v0.4 implements full local-propagation properly." That direction is the authorization.

**v0.3 § 14.12 status**: REFINED. The v0.3 intent (eliminate step discontinuities at junctions) is preserved; the mechanism is replaced (local taper instead of global inflation).

**Web research surface (Rule 7)**: no industry-standards guidance for residential corridor taper length. Default is reasoned, not standards-bound.

#### § 14.21 — Edge-snap envelope-symmetry secondary criterion (Walk #3 Drawback 5)

**Decision**: When multiple grid-line pairs satisfy edge-snap requirement, secondary score prefers pairs whose midpoint is closest to envelope center. Configurable weight `envelope_symmetry_weight = 0.3` default.

**Rationale**: Reviewer correctly identified that grid-snap and envelope-boundary alignment are independent constraint systems. When the grid is offset relative to the envelope (common when C7 grid is column-driven and envelope is setback-driven), edge-snap can produce asymmetric `ZoneBandEnvelope` placement — the corridor sits closer to one side of the envelope than the other.

**Why secondary, not primary**: the primary criterion (hitting the target centerline derived from band geometry) must dominate — corridor must reach its bands. The secondary criterion only matters when multiple grid pairs are equally good for the primary. Weight 0.3 reflects this priority.

**Calibration → B-NNN-Q**.

**Web research surface (Rule 7)**: not applicable. Internal architectural choice.

#### § 14.22 — Configurable band-priority order (Walk #3 Drawback 7)

**Decision**: Move v0.3's hardcoded `PUBLIC > PRIVATE > SERVICE` corner-overlap priority to config: `config.band_priority_order = DEFAULT_BAND_PRIORITY_ORDER` (default preserves v0.3 ordering).

**Rationale**: Reviewer correctly noted the priority is culturally biased toward Indian residential vernacular. Indian designs reasonably favor PUBLIC corners for entry/foot-traffic, but other cultural styles (e.g., privacy-first traditions where bedrooms claim corners) may invert the order. Trivial to configure; expensive to leave hardcoded.

**Default preserved**: Indian residential vernacular (the v1 product target) keeps PUBLIC > PRIVATE > SERVICE. Override is opt-in.

**Validator**: `band_priority_order` must contain exactly the 3 functional bands (PUBLIC, PRIVATE, SERVICE) in some order. CIRCULATION must NOT appear (per invariant 7).

**Web research surface (Rule 7)**: not applicable. Default-justification is internal-vernacular reasoning.

#### § 14.23 — `CorridorDispatchError` diagnostic enrichment (Walk #3 Drawback 6; refines § 14.17)

**Decision**: `CorridorDispatchError` now carries diagnostic metadata: `candidate_index`, `topology_kind`, `failure_phase`, `suggested_alternative_topologies`. Auto-skip explicitly NOT added (Pattern A pushback per § 14.17 — soft fallback masks dispatch bugs).

**Rationale**: Reviewer correctly noted v0.3's bare error was unfriendly to callers. Reviewer's "auto-skip" suggestion was rejected: silently skipping invalid dispatch outputs degrades the diagnostic signal that the dispatch logic itself needs fixing (Pattern A risk).

**Honest middle path**: enrich the error with everything the caller needs to make an informed decision (which candidate, which topology, which phase failed, what alternatives might work for this plot+bands), but require the caller to decide. The caller (typically a higher-level pipeline orchestrator) chooses to (a) re-call C8 with an alternative oriented_candidate, (b) surface to user, (c) abort. C8 itself never silently degrades.

**Web research surface (Rule 7)**: not applicable.

#### § 14.24 — Consumption-band promotion trigger (Walk #3 Drawback 4; refines § 14.15)

**Decision**: `consumption_band` remains advisory-only in v0.4. The trigger condition for promoting it from advisory to active constraint is documented:

> When **C14 (Unified Evaluation) ships** and identifies `consumption_band == HIGH` candidates as systematically losing in ranking, OR when **B-NNN-N empirical calibration** completes and confirms the 12% / 20% thresholds are correct, C8 v(N+1) gains `config.max_consumption_band: ConsumptionBand | None = None` which when set raises `CorridorAreaBudgetExceededError` if exceeded.

**Rationale**: Reviewer correctly noted bare metric is dead telemetry. Reviewer's "soft constraint hook" suggestion (`max_allowed_consumption_band` config) was reasonable but pre-empts C14/C15 ranking authority (Pattern E). v0.4's compromise: document the path from passive metric to active constraint without prematurely committing to it. Filed as the trigger condition for B-NNN-N, not a separate backlog item.

**v0.3 § 14.15 status**: REFINED. Advisory-only behavior preserved; promotion path documented.

**Web research surface (Rule 7)**: not applicable. Threshold values pending B-NNN-N calibration.

### Pushback ledger (preempted critique items + new items handled)

| Item | Source | Reason for hold or how addressed |
|---|---|---|
| "Why doesn't C8 score corridor quality?" | Anticipated, v0.1 | Held — C14 CirculationAnalyzer is the documented home (§ 14.1.1) |
| "Diagonal corridors in v1 for non-rectilinear plots?" | Anticipated, v0.1 | Held — B-066 + B-NNN-E |
| "Why parameterize regulatory width instead of just looking up NBC?" | Anticipated, v0.1 | Held — Pattern C (§ 14.1.5); B-NNN-A is the verification task |
| "Per-floor corridor variation?" | Anticipated, v0.1 | Held — B-NNN-F |
| "Hardcoded 0.7 off-grid penalty?" | Anticipated, v0.1 | RESOLVED — v0.2 quantization eliminates off-grid penalty entirely |
| **Reviewer 1: Band attachment under-specified** | v0.2 critique walk | RESOLVED via § 14.1 + § 4.0 spatial model |
| **Reviewer 2: Centerline-snap ignores width** | v0.2 critique walk | RESOLVED via § 14.2 quantization + § 4.2 edge-snap |
| **Reviewer 3: Topological connectivity** | v0.2 critique walk | RESOLVED via § 14.3 + invariants 4 + 13 |
| **Reviewer 4: Length sanity ignores grid-snap** | v0.2 critique walk | RESOLVED via § 14.4 (check removed) + B-110 |
| **Reviewer 5: No spatial feasibility** | v0.2 critique walk | RESOLVED via § 4.7 + invariants 10–12 |
| **Reviewer 6: Corridor width local, not system-aware** | v0.2 critique walk | PARTIALLY RESOLVED via § 14.5 provenance contract; full system-aware sizing → B-NNN-J |
| **Reviewer 7: Degenerate STRIP breaks invariants** | v0.2 critique walk | RESOLVED via § 14.6 has_corridor flag + tiered invariants |
| **Self-found V-A: phantom C7 fields** | S31 grep | RESOLVED via § 14.9 |
| **Walk #2 Drawback 1: Strip model adjacency assumptions** | v0.3 critique walk | PARTIAL + PUSHBACK — § 14.16 acknowledges; B-NNN-K defers refinement |
| **Walk #2 Drawback 2: GRID_FRACTIONS bias downward** | v0.3 critique walk | RESOLVED via § 14.11 bias-upward rule (verified on 7 official C7 bay sizes) |
| **Walk #2 Drawback 3: Edge-align ≠ structural** | v0.3 critique walk | PARTIAL + PUSHBACK — § 14.13 invariant 14; reviewer's framing pushed back per industry consensus |
| **Walk #2 Drawback 4: Junction width mismatch** | v0.3 critique walk | RESOLVED via § 14.12 equal_width_at_junctions=True default |
| **Walk #2 Drawback 5: Corner-overlap ambiguity** | v0.3 critique walk | RESOLVED via § 14.10 PUBLIC > PRIVATE > SERVICE priority |
| **Walk #2 Drawback 6: EPSILON_M too strict** | v0.3 critique walk | PARTIAL — empirical concern unfounded (FP=0.0); § 14.18 centralized helper adopts the principle |
| **Walk #2 Drawback 7: Area accounting incomplete** | v0.3 critique walk | RESOLVED via § 14.14 sweep-line union (verified on 4 cases) |
| **Walk #2 Drawback 8: SelfIntersectionError unsafe** | v0.3 critique walk | PARTIAL + PUSHBACK — § 14.17 deliberate raise + new CorridorDispatchError pre-validation |
| **Walk #2 Drawback 9: Area fraction lacks thresholds** | v0.3 critique walk | PARTIAL + PUSHBACK — § 14.15 ConsumptionBand advisory; C14/C15 retain action authority |
| **Walk #3 Drawback 1: Strip model adjacency assumptions** | v0.4 critique walk | AFFIRMED — already backlogged as B-NNN-K (no v0.4 action needed) |
| **Walk #3 Drawback 2: Width over-correction (upward bias)** | v0.4 critique walk | RESOLVED via § 14.19 scored selection; web-verified; never extreme over- or under-design across 7 C7 bay sizes |
| **Walk #3 Drawback 3: Junction width propagation cascade** | v0.4 critique walk | RESOLVED via § 14.20 local-propagation with linear taper; substantial architectural surface accepted per Ramalingam direction |
| **Walk #3 Drawback 4: Consumption band passive** | v0.4 critique walk | PARTIAL — held per Pattern E; § 14.24 documents promotion trigger |
| **Walk #3 Drawback 5: Edge-snap envelope drift** | v0.4 critique walk | RESOLVED via § 14.21 secondary symmetry criterion |
| **Walk #3 Drawback 6: CorridorDispatchError no recovery** | v0.4 critique walk | PARTIAL + PUSHBACK — § 14.23 diagnostic enrichment; auto-skip rejected per Pattern A |
| **Walk #3 Drawback 7: Hardcoded band priority** | v0.4 critique walk | RESOLVED via § 14.22 configurable order; default preserved for Indian residential vernacular |

---

## § 15 — Open questions for next round (or LOCK)

(v0.1 list partially resolved; v0.2 carries forward + adds)

**Resolved by v0.2**:
- v0.1 Q1 (C7 contract) — RESOLVED via § 14.9 grep + § 4.2 rewrite
- v0.1 Q3 (degenerate path representation) — RESOLVED via § 14.6 has_corridor flag
- v0.1 Q4 (grid-snap penalty) — RESOLVED — quantization eliminates the penalty

**Carried forward from v0.1**:
- v0.1 Q2 (`CorridorDesignConfig` location): kept in function signature; minor.
- v0.1 Q5 (`CorridorDesignedCandidate` naming): clunky alternatives discussed; lean: keep current.
- v0.1 Q6 (`_c8_fixtures.py` pattern): defer to first build session; pattern matches C5/C6 fixtures.

**NEW v0.2 open questions**:

1. **`GRID_FRACTION_CANDIDATES` exact set**: I picked `{1/4, 1/3, 1/2, 2/3, 3/4}` per architect convention. Coarser sets viable. Calibration question — defer to B-090 family unless you want a different default before LOCK.

2. **`junction_angle_tolerance_deg = 0.0` default**: exact match means floating-point perfection. Should it be `0.001` (sub-degree tolerance) for FP safety? Lean: keep 0.0 since junctions are constructed at exact 90° in § 4.7; FP drift would indicate a bug worth surfacing.

3. **`ZoneBandEnvelope` corner-overlap resolution**: § 4.0 allows two adjacent strips to overlap at corners (e.g., NE corner = NORTH-band ∩ EAST-band). C9 will resolve via room-fit. Should C8 expose the overlap rectangles explicitly (extra dataclass) or leave them implicit? Lean: implicit; downstream computes if needed.

4. **`has_corridor=False` edge cases**: when no corridor exists (small T1 STRIP), should `envelopes` still be computed? Lean: yes — the bands exist regardless, even without a corridor connecting them. C9 still needs them.

5. **Should `ZoneBandEnvelope` be re-exported from C8's `__init__.py`?** It's a new public type. Lean: yes, since C9 will consume it.

---

## § 16 — End of v0.4 PROPOSED

**Spec round summary**:

```
Type           : v0.4 PROPOSED (critique walk #3 patch over v0.3 PROPOSED)
Driver         : 7-item reviewer critique walk #3 + Ramalingam adjudication
                 (Q1 default 2.0 penalty ratio; Q2 full local-propagation
                 accepted, not the simpler step-discontinuity compromise)
Authoring      : S31
Web research   : Walk #3 Drawback 2 web search refuted v0.3's framing —
                 over-design and under-design BOTH have real costs
                 (Quora, Coohom, Constructive Laws). Drove § 14.19 scored
                 selection. No external standard for residential taper
                 length found; § 14.20 default reasoned, not standards-bound.
Code-grep      : C7 PREFERRED_BAY_SIZES_M verified; v0.3 width-bias bug
                 confirmed empirically; trapezoid union verified on 6 cases.
Reviewer       : 4 fully RESOLVED (2, 3, 5, 7)
verdicts         2 PARTIAL + PUSHBACK (4, 6)
                 1 AFFIRMED-AS-BACKLOGGED (1)
Empirical fix  : v0.4 width-selection scored rule produces no extreme
                 over- or under-design across 7 C7 bay sizes
                 (worst over: 1.50m at 3.0m bay; worst under: 1.10m at 3.3m)
New ADs        : 6 (§ 14.19 through § 14.24)
v0.3 ADs       : 9 preserved (§ 14.10 through § 14.18); § 14.11 SUPERSEDED
                 by § 14.19; § 14.12 REFINED by § 14.20; § 14.15 REFINED
                 by § 14.24
v0.2 ADs       : 9 preserved (§ 14.1 through § 14.9)
v0.1 ADs       : 5 preserved (§ 14.1.1–14.1.5), 3 superseded
New B-NNNs     : 3 (B-NNN-O, B-NNN-P, B-NNN-Q)
Total backlog  : 18 items (was 15 in v0.3)
New invariants : 5 (16-20: taper bound, tapered-edge exclusion, junction-
                 width-match-via-taper, taper monotonicity, constant-width
                 coverage). Total invariants: 20.
Behavior change: SUBSTANTIAL — width selection (scored), junction handling
                 (local taper propagation), area accounting (trapezoid union),
                 secondary edge-snap criterion, configurable band priority,
                 enriched dispatch error. v0.3 was PROPOSED-not-LOCKED so no
                 backward-compat issues.
Status         : PROPOSED. PENDING Ramalingam LOCK adjudication.
```

**Convergence trajectory**:

```
                       reviewer items    new B-NNNs    self-found defects
v0.1 → v0.2                7 critiques       4              1 (V-A)
                           6 RESOLVED                          
                           1 PARTIAL                            
v0.2 → v0.3                9 critiques       4              0
                           4 RESOLVED                          
                           5 PARTIAL                            
v0.3 → v0.4                7 critiques       3              0
                           4 RESOLVED                          
                           2 PARTIAL                            
                           1 AFFIRMED-BACKLOGGED              
```

**Convergence reading**: walk #3 produced 7 items vs walk #2's 9, with 4 RESOLVED + 2 PARTIAL + 1 AFFIRMED. Diminishing-returns trajectory healthy. Walk #4 likely returns ≤ 5 items, mostly nits or items already deferred. v0.4 is plausibly LOCK-quality after one more confirmation walk.

Per Rule 8: **PROPOSED. PENDING Ramalingam LOCK adjudication.** Adjudication-window critique on v0.4 stays patch-eligible (would produce v0.5 PROPOSED) until you say "lock it."

**Awaiting**: critique walk #4 OR LOCK.
