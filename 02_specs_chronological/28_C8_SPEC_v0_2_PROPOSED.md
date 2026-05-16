# BuildemUp — C8 Corridor Designer — SPEC v0.2 PROPOSED

**Status**: PROPOSED. PENDING critique walks → LOCK adjudication. Critique-walk-#1 patch over v0.1 DRAFT applying 7 reviewer drawbacks + 1 self-found C7-contract defect (V-A) + 2 architectural decisions (Option A spatial model, grid-quantized widths).
**Component**: C8 of canonical 17-component v3 list (Track 3). Position 8 — first sub-component pending in build order after C7.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C5 (`TopologyCandidate.corridor_sketch`) + C6 (`OrientedCandidate.refined_zone_bands`) + C7 (`Grid` — *not* `StructuralGrid`; see § 14.9) + C4 (`PlotAnalysis`); produces input for C9 (Room Sizer) and downstream.
**Authoring session**: S31 (post C6 SHIP, post v0.1 critique walk).
**Predecessor**: v0.1 DRAFT (S31).

---

## § 0 — Lineage delta from v0.1 DRAFT → v0.2 PROPOSED

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

    Invariants (asserted at construction):
      - start.point_m and end.point_m differ in exactly one coordinate
        (either x or y — axis-aligned)
      - length_m == |end - start| in the differing coordinate
      - width_m > 0
      - runs_along is the cardinal direction from start to end
    """
    kind: CorridorSegmentKind
    start: CorridorEndpoint
    end: CorridorEndpoint
    width_m: float
    length_m: float
    runs_along: PlotOrientation


@dataclass(frozen=True)
class CorridorPath:
    """The complete corridor design for one candidate.

    Per SPEC v0.2 § 3 + § 4.6.

    NEW v0.2 (Reviewer Drawback 7): `has_corridor: bool` flag. Invariants
    split into ALL-PATHS (apply unconditionally) and HAS-CORRIDOR-ONLY
    (apply only when has_corridor == True). Eliminates the "documented
    quirk" of v0.1 § 4.6 invariants 6 + 7.
    """
    has_corridor: bool                        # NEW v0.2
    segments: tuple[CorridorSegment, ...]
    envelopes: tuple[ZoneBandEnvelope, ...]   # NEW v0.2 (§ 14.1)
    total_length_m: float
    total_area_m2: float                      # NEW v0.2 (Drawback 6)
    connectivity_type: ConnectivityType       # mirrors C5; sanity-check
    grid_alignment: GridAlignmentReport       # NEW v0.2 (replaces grid_snap_offsets)


@dataclass(frozen=True)
class GridAlignmentReport:
    """How well the corridor aligns to the C7 grid.

    NEW v0.2 (replaces v0.1's `grid_snap_offsets` raw mapping).
    """
    quantization_used: WidthQuantization
    edges_aligned_count: int                  # number of segment edges on grid lines
    edges_total_count: int                    # total edges across all segments
    grid_alignment_score: float               # [0, 1]; edges_aligned / edges_total
    chosen_width_fraction: float | None       # populated for GRID_FRACTIONS quantization
    chosen_bay_axis: str | None               # "x" or "y"; which bay was the quantization basis


@dataclass(frozen=True)
class CorridorProvenance:
    derived_at: float
    oriented_candidate_trace_id: str
    grid_trace_id: str                        # was structural_grid_trace_id in v0.1
    config_snapshot: CorridorDesignConfig
    rule_trace: tuple[str, ...]
    fallback_used: bool
    envelope_area_consumed_m2: float          # NEW v0.2 (Drawback 6); = total_area_m2
    envelope_area_fraction: float             # NEW v0.2; ratio vs Grid envelope area


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
    """
    regulatory_min_width_m: float = 0.9       # NEEDS PRIMARY-SOURCE VERIFICATION (B-NNN-A)
    comfort_target_width_m: float = 1.2
    entry_stub_width_m: float = 1.0
    width_quantization: WidthQuantization = WidthQuantization.GRID_FRACTIONS  # NEW v0.2
    fallback_snap_tolerance_m: float = 0.15   # only for NONE_FREE_WIDTH
    junction_angle_tolerance_deg: float = 0.0  # NEW v0.2; 0.0 = exact 0/90 only
    epsilon_m: float = 0.001                  # NEW v0.2; coordinate-coincidence tolerance
    courtyard_loop_inner_clear_m: float = 1.0
    allow_width_variation_per_segment: bool = True
```

**Constants** (in c08/schema.py):

```python
# v0.2 § 14.2 — quantization fraction set
GRID_FRACTION_CANDIDATES: tuple[float, ...] = (0.25, 1.0/3.0, 0.5, 2.0/3.0, 0.75)

# v0.2 § 4.6 inv 13 — junction angle constants
ALLOWED_JUNCTION_ANGLES_DEG: frozenset[float] = frozenset({0.0, 90.0, 180.0, 270.0})

# v0.2 § 3 — coordinate-coincidence tolerance default
DEFAULT_EPSILON_M: float = 0.001              # 1mm; sub-construction-tolerance
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

**Strip overlap at corners**: where two adjacent cardinal strips meet at a corner (e.g., NORTH-band + EAST-band in the NE corner), the v0.2 model allows them to overlap. C9 will resolve corner ownership via room-fit. This is NOT a buildability issue (it's a sketch-level simplification, like C5's nominal width).

This model is intentionally the **simplest possible spatial resolution** of the band → direction abstraction. Per § 14.1 it is documented as **provisionally C8-owned**; if C9 or C11a need finer band geometry later, the model is replaced rather than incrementally patched (Pattern A avoidance).

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

### § 4.3 — Width assignment (NEW v0.2; quantization-driven)

Per `config.width_quantization`:

**`GRID_FRACTIONS`** (default):
1. `bay_min = min(grid.bay_x_m, grid.bay_y_m)`.
2. Candidate widths = `[f × bay_min for f in GRID_FRACTION_CANDIDATES]` = `[0.25, 1/3, 0.5, 2/3, 0.75] × bay_min`.
3. Filter to those `≥ regulatory_min_width_m`.
4. Choose the candidate **closest to** `comfort_target_width_m`.
5. If filtered list is empty (every fraction below regulatory min): raise `CorridorTooNarrowError(B-NNN-B)`.
6. Record `(chosen_width_fraction, chosen_bay_axis)` in `GridAlignmentReport`.

Worked example (3.0m bay, 0.9m regulatory min, 1.2m comfort target):
- Candidates: 0.75, 1.0, 1.5, 2.0, 2.25 m.
- Filter ≥ 0.9: 1.0, 1.5, 2.0, 2.25.
- Closest to 1.2: **1.0m** (|1.0 - 1.2| = 0.2 < |1.5 - 1.2| = 0.3).

**`NEAREST_GRID_LINE`**:
1. Compute desired `width_m = max(comfort_target_width_m, regulatory_min_width_m)`.
2. Find nearest pair of grid lines `(g_low, g_high)` straddling the corridor's required centerline with `g_high - g_low` ≥ `regulatory_min_width_m`.
3. Width derived as `g_high - g_low`. Edges aligned by construction.

**`NONE_FREE_WIDTH`** (escape hatch, logged loudly):
- Original v0.1 behavior: `width_m = max(comfort_target_width_m, regulatory_min_width_m)`.
- Edges may be off-grid; falls back to `fallback_snap_tolerance_m` for centerline snap.
- `provenance.rule_trace` includes `"WARNING: width_quantization=NONE_FREE_WIDTH; corridor edges may not align to structural grid"`.

**ENTRY_STUB segments**: separate width = `entry_stub_width_m` (default 1.0m). Quantization applied to entry stub independently.

**Constrained-plot override**: if the chosen quantized width pushes corridor outside the buildable envelope (envelope-overflow check at § 4.7 invariant 10), narrow to next-smaller GRID_FRACTION candidate. If even the smallest exceeds `regulatory_min_width_m`-violating, raise `CorridorTooNarrowError(B-NNN-B)`.

#### § 4.3.1 — Degenerate path (NEW v0.2 representation)

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

**HAS-CORRIDOR-ONLY** (apply only when `has_corridor=True`):

2. Every `width_m >= regulatory_min_width_m`.
6. PUBLIC, SERVICE, PRIVATE bands each have ≥ 1 BAND_ATTACHMENT in the segments tuple.
7. CIRCULATION band has no `ZoneBandEnvelope` (it IS the corridor; § 4.0 + § 14.7).
9. **EXISTS** at least one ENTRY endpoint (combined with inv 5: exactly one).

### § 4.7 — Spatial-feasibility checks (NEW v0.2; per Reviewer Drawback 5)

Performed during construction (not just at validator):

- **Envelope containment**: as each segment is constructed, assert its bounding box ⊆ envelope rectangle. If overflow, narrow width per § 4.3 fallback chain or raise.
- **Self-intersection**: as each segment is added to a building path, check against all prior segments via bounding-box-pair overlap test. If overlap detected outside junction tolerance, raise `CorridorSelfIntersectionError` (this is a programmer error in the topology dispatcher; should not happen with correct § 4.1 implementation).
- **Junction snap**: at every JUNCTION, after both adjoining segments are placed, force junction endpoint to exact coordinates `(min(start1.x, end2.x), min(start1.y, end2.y))` or equivalent — prevents EPSILON_M-scale drift from accumulating across multi-segment paths.

### § 4.8 — Area accounting (NEW v0.2; per Reviewer Drawback 6)

After all segments are constructed:

```python
total_area_m2 = sum(segment.length_m * segment.width_m for segment in segments)
# For overlapping segments at junctions, subtract overlap area (small; ≤ width^2 per junction)
```

`provenance.envelope_area_consumed_m2 = total_area_m2`
`provenance.envelope_area_fraction = total_area_m2 / (grid.envelope_width_m * grid.envelope_depth_m)`

C9 (Room Sizer) reads `envelope_area_consumed_m2` to compute remaining area for rooms. **C8 does NOT pre-fetch C9's needs** (Pattern E avoidance — § 14.5). C8 just publishes; C9 subscribes.

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
| Self-intersection during construction | `CorridorSelfIntersectionError` (programmer error) |
| Junction angle outside `{0°, 90°, 180°, 270°}` ± tolerance | Validator fail (NEW v0.2) |
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

- **Version**: v0.2 PROPOSED
- **Status**: PROPOSED. PENDING Ramalingam LOCK adjudication; not yet build-ready.
- **Lineage**: v0.1 DRAFT (S31) → **v0.2 PROPOSED (S31; critique walk #1 + V-A self-found defect + 2 ADs)**
- **Authoring session**: S31
- **Companion artifacts**: C5 SPEC v0.9 LOCKED; C6 SPEC v0.7 LOCKED; C7 `Grid` schema (verified by S31 grep)
- **Web research surface (Rule 7)**: NBC + TNCDBR + Neufert + industry-gridline-practice. NEW S31 verification: edge-snap-not-centerline-snap is industry standard (§ 14.2).
- **Code-grep verification (Rule 7 mandate, S31)**: C7's `Grid` schema confirmed; v0.1 phantom field references caught and corrected (V-A).

---

## § 12 — Backlog enumeration (preliminary; B-NNNs assigned at LOCK)

Total: **11 items** (was 7 in v0.1; +4 from this critique walk = B-NNN-H, B-NNN-I, B-NNN-J, B-110).

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

## § 16 — End of v0.2 PROPOSED

**Spec round summary**:

```
Type           : v0.2 PROPOSED (critique walk #1 patch over v0.1 DRAFT)
Driver         : 7-item reviewer critique + 1 self-found C7-contract defect (V-A)
                 + 2 architectural decisions (Option A spatial model,
                 grid-quantized widths)
Authoring      : S31
Web research   : 1 external-standards claim verified (industry edge-snap
                 practice — § 14.2). No primary-source revision needed.
Code-grep      : C7 Grid schema verified; v0.1 phantom field references
                 corrected (V-A / § 14.9).
Reviewer       : 6 RESOLVED, 1 PARTIALLY RESOLVED + B-NNN-J
verdicts         (Drawback 6 — full system-aware sizing deferred)
New ADs        : 9 (§ 14.1 through § 14.9)
v0.1 ADs       : 5 preserved (renumbered § 14.1.x), 3 superseded/reversed
                 (§ 14.1.6, § 14.1.7, § 14.1.8)
New B-NNNs     : 4 (B-NNN-H, B-NNN-I, B-NNN-J, B-110)
Total backlog  : 11 items (was 7 in v0.1)
Behavior change: substantial — v0.1 was DRAFT; v0.2 is the substantively-
                 revised pre-LOCK version. Spatial model is new. Width
                 quantization is new. Validator tier-split is new.
                 Phantom C7 fields removed.
Status         : PROPOSED. PENDING Ramalingam LOCK adjudication.
```

**Convergence trajectory**:

```
                       reviewer items    new B-NNNs    self-found defects
v0.1 → v0.2                7 critiques       4              1 (V-A)
                           6 RESOLVED
                           1 PARTIAL
```

Per Rule 8: **PROPOSED. PENDING Ramalingam LOCK adjudication.** Adjudication-window critique on v0.2 stays patch-eligible (would produce v0.3 PROPOSED) until you say "lock it."

**Awaiting**: critique walk #2 OR LOCK.
