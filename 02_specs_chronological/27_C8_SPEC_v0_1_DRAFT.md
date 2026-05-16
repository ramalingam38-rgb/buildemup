# BuildemUp — C8 Corridor Designer — SPEC v0.1 DRAFT

**Status**: DRAFT. PENDING critique walks → LOCK adjudication. Greenfield first draft (no prior version). NOT build-ready until LOCKED.
**Component**: C8 of canonical 17-component v3 list (Track 3). Position 8 — first sub-component pending in build order after C7.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C5 (`TopologyCandidate.corridor_sketch`) + C6 (`OrientedCandidate.refined_zone_bands`) + C7 (`StructuralGrid`) + C4 (`PlotAnalysis`); produces input for C9 (Room Sizer) and downstream.
**Authoring session**: S31 (post C6 SHIP).
**Predecessor**: none — this is v0.1 DRAFT. C8 has been "not started" through every prior session.

---

## § 0 — Why this spec, why now

C5 produces a `CorridorSketch` (nominal width 1.2m, position, runs_along, approx_length_m, connectivity_type) — but it's a **sketch**, not a designed corridor. C5's own dataclass docstring states explicitly: *"C8 (Corridor Designer) refines geometry."* C6 produces refined zone_bands and direction priorities but does not touch corridor geometry. C7 produces the structural grid; corridor placement must respect grid lines for buildability. **No component currently produces actual corridor geometry** — the gap is architectural, not optional.

C8's job: given the upstream sketches/scores/grid, produce a `CorridorPath` that defines the corridor's polyline, width(s), and the entry-exit attachment points to functional bands. C8 does NOT place rooms (that's C9+). C8 does NOT generate doors (that's C13). C8 does NOT score corridor quality (that's C14's `CirculationAnalyzer`).

**Architecture-v2 provenance** (reproduced for traceability): C8 is described in `BuildemUp_Architecture_v2.md` lines 670–712 as "Corridor Design — given topology and grid, design the circulation corridor. Corridor is reserved before rooms are placed." Architecture v3 leaves C8 unchanged from v2 (no v3 delta touches C8). The CirculationAnalyzer added in architecture v3 § 6 belongs to C14, not C8.

---

## § 1 — Purpose

Given a C5/C6 oriented topology candidate, a C7 structural grid, and a C4 plot analysis, produce a **`CorridorPath`** — the geometry of the residential circulation corridor (polyline, widths, attachment points) — sized to satisfy the regulatory minimum + residential-comfort buffer, aligned to the structural grid, and respecting the topology kind (STRIP / CENTRAL_SPINE / L_SHAPE / COURTYARD).

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
    structural_grid: StructuralGrid,                       # from C7
    plot_analysis: PlotAnalysis,                           # from C4
    *,
    config: CorridorDesignConfig | None = None,            # tunables; default OK
) -> tuple[CorridorDesignedCandidate, ...]:
```

`CorridorDesignedCandidate` = `OrientedCandidate` + `corridor_path: CorridorPath` (extends position-paired chain).

`CorridorDesignConfig` carries per-call tunables: regulatory minimum width, comfort-target width, grid-snap tolerance, etc. Defaults baked into the dataclass mean callers can omit it entirely.

---

## § 3 — Output schema

```python
class CorridorSegmentKind(str, Enum):
    """A single straight corridor segment's role in the path."""
    PRIMARY    = "primary"      # Entry → main public spine
    BRANCH     = "branch"       # Off the primary (L-shape arm, T-junction)
    LOOP_ARM   = "loop_arm"     # One side of a courtyard loop
    ENTRY_STUB = "entry_stub"   # Short stub from entry door to primary spine

class CorridorEndpointKind(str, Enum):
    """What sits at a corridor segment's terminus."""
    ENTRY              = "entry"               # plot-facing entry door
    BAND_ATTACHMENT    = "band_attachment"     # connects to PUBLIC/SERVICE/PRIVATE band
    JUNCTION           = "junction"            # T or L join with another segment
    STAIR_ATTACHMENT   = "stair_attachment"    # vertical-circulation attachment (C12 will refine)
    DEAD_END           = "dead_end"            # terminates without door (rare; defensive)

@dataclass(frozen=True)
class CorridorEndpoint:
    """One end of a corridor segment."""
    kind: CorridorEndpointKind
    point_m: tuple[float, float]               # (x, y) in plot-local coords
    attached_band: ZoneBand | None             # populated when kind == BAND_ATTACHMENT
    attached_direction: PlotOrientation | None # cardinal direction faced; for BAND_ATTACHMENT or ENTRY

@dataclass(frozen=True)
class CorridorSegment:
    """A single straight section of the corridor.

    All segments are axis-aligned (parallel to plot edges) in v1.
    Diagonal segments deferred to B-NNN (see § 9).
    """
    kind: CorridorSegmentKind
    start: CorridorEndpoint
    end: CorridorEndpoint
    width_m: float                             # may differ per segment (e.g., entry stub wider)
    length_m: float                            # derived from start/end; cached for consumers
    runs_along: PlotOrientation                # axis-aligned cardinal direction of travel

@dataclass(frozen=True)
class CorridorPath:
    """The complete corridor design for one candidate.

    Per SPEC v0.1 § 3.

    Invariants (§ 4.6):
      1. segments is non-empty (a degenerate single-segment "no corridor" form
         exists for tiny STRIP topologies; see § 4.3.1).
      2. Every segment.width_m >= config.regulatory_min_width_m.
      3. Every segment is axis-aligned to a cardinal direction.
      4. Total path is connected (every segment's endpoint is shared with
         at least one other segment, OR is an ENTRY / DEAD_END).
      5. Exactly one segment has an ENTRY endpoint (the entry stub or
         primary spine, depending on topology).
      6. Every functional ZoneBand in the candidate's refined_zone_bands
         (PUBLIC, SERVICE, PRIVATE) has at least one BAND_ATTACHMENT.
      7. CIRCULATION band's "attachment" is the corridor itself (validator
         skips this band; documented quirk).
      8. connectivity_type matches the upstream C5 ConnectivityType
         (LINEAR ↔ 1 PRIMARY segment + 0..N ENTRY_STUB; BRANCHED ↔ 1 PRIMARY +
         ≥ 1 BRANCH; LOOP ↔ ≥ 4 LOOP_ARM forming a closed loop).
      9. Total polyline length is within ±15% of C5's approx_length_m
         (loose tolerance — C5's estimate is sketch-grade).

    NOTE: The validator enforces 1–8 hard. Invariant 9 is a soft warning
    in `provenance.rule_trace`, not a hard fail (C5's approx_length_m can
    drift when C7 grid scaling perturbs cell sizes).
    """
    segments: tuple[CorridorSegment, ...]
    total_length_m: float                      # sum of segment.length_m
    connectivity_type: ConnectivityType        # mirrors C5; sanity-check
    grid_snap_offsets: Mapping[int, float]     # per-segment snap deltas (debug)

@dataclass(frozen=True)
class CorridorProvenance:
    derived_at: float
    oriented_candidate_trace_id: str           # ties back to OrientedCandidate
    structural_grid_trace_id: str              # ties back to C7
    config_snapshot: CorridorDesignConfig      # frozen copy of config used
    rule_trace: tuple[str, ...]                # human-readable decisions
    grid_alignment_score: float                # [0, 1] — how cleanly snapped to grid
    fallback_used: bool                        # True if topology-specific fallback fired

@dataclass(frozen=True)
class CorridorDesignedCandidate:
    """C6 candidate + C8's corridor design, position-paired."""
    oriented_candidate: OrientedCandidate
    corridor_path: CorridorPath
    provenance: CorridorProvenance

@dataclass(frozen=True)
class CorridorDesignConfig:
    """Tunables for C8. All have safe defaults; callers can omit.

    NOTE on regulatory_min_width_m (Pattern C / Rule 7 surface):
      The architecture-v2 spec asserts 0.9m as "NBC: 0.9m interior
      residential" but the S31 web research did NOT independently surface
      this exact value from a primary NBC source (TNCDBR rule 42 was
      referenced but the text wasn't retrieved; NBC Part 4 surfaced 1.0m
      for staircase widths but not for corridors). The 0.9m default is
      therefore documented as **needs-primary-source-verification** and
      is exposed as a config parameter rather than a hardcoded constant
      so it can be overridden without recompilation. See B-NNN-A in § 12.
    """
    regulatory_min_width_m: float = 0.9        # NEEDS PRIMARY-SOURCE VERIFICATION
    comfort_target_width_m: float = 1.2        # matches C5's nominal_width_m default
    entry_stub_width_m: float = 1.0            # entry stub may be wider than primary
    grid_snap_tolerance_m: float = 0.15        # how far off-grid before forcing snap
    courtyard_loop_inner_clear_m: float = 1.0  # inner-clearance of courtyard loop
    allow_width_variation_per_segment: bool = True
```

---

## § 4 — Behavior

### § 4.1 — Topology dispatch

C8's algorithm is a topology-kind dispatch (matches C5 enum):

| Topology | Algorithm |
|---|---|
| `STRIP` (small T1: no corridor) | Single ENTRY-only "stub" path; no BAND_ATTACHMENTs (rooms abut directly). Triggers degenerate path (§ 4.3.1). |
| `STRIP` (T2/T3: linear) | Single PRIMARY segment along `corridor_sketch.runs_along`; ENTRY at facing end; BAND_ATTACHMENTs perpendicular. |
| `CENTRAL_SPINE` | Single PRIMARY segment along `corridor_sketch.runs_along`; ENTRY_STUB from facing edge to spine (if entry doesn't already meet spine); BAND_ATTACHMENTs both sides. |
| `L_SHAPE` | One PRIMARY arm + one BRANCH arm meeting at a JUNCTION; both axis-aligned. ENTRY on the longer arm by default. |
| `COURTYARD` | Four LOOP_ARM segments forming a closed loop around the central courtyard; ENTRY on the arm matching plot.facing. |

### § 4.2 — Grid snapping

C8 reads `structural_grid.column_lines_x` and `structural_grid.column_lines_y` (cardinal grid lines in plot-local coords) and snaps each corridor segment's centerline to the nearest grid line within `config.grid_snap_tolerance_m`. If no grid line is within tolerance, the segment goes off-grid and `provenance.grid_alignment_score` decreases proportionally.

Snap algorithm (per segment):
1. Compute segment centerline `c` from C5 sketch (`runs_along` axis + perpendicular position derived from band centroid).
2. Find nearest grid line `g` parallel to `runs_along`'s perpendicular axis.
3. If `|c - g| <= config.grid_snap_tolerance_m`, snap (set centerline to `g`); record offset in `grid_snap_offsets`.
4. Else leave at `c`; `grid_alignment_score *= 0.7` (penalty per off-grid segment).

### § 4.3 — Width assignment

Per segment:
- Default: `width_m = max(config.comfort_target_width_m, config.regulatory_min_width_m)` = 1.2m.
- ENTRY_STUB segments: `width_m = config.entry_stub_width_m` = 1.0m (slightly narrower; matches grand-entrance feel of architecture-v2's "1.0m double door").
- Constrained-plot override: if applying default width would push corridor past plot's buildable envelope, narrow toward `config.regulatory_min_width_m`. If even that fails, raise `CorridorTooNarrowError(B-NNN-B)`.

#### § 4.3.1 — Degenerate path (no-corridor STRIP)

For small T1 STRIP topologies where C5 set `corridor_sketch.position == NONE`, C8 produces a **degenerate** `CorridorPath`:
- Exactly one segment of kind `ENTRY_STUB`, length ~ 1.0m (matches entry door + threshold).
- `start.kind = ENTRY`, `end.kind = DEAD_END`.
- No BAND_ATTACHMENTs (validator invariant 6 is relaxed for this case via documented quirk).
- `total_length_m` ≈ 1.0m.

This represents "no real corridor; rooms open directly off the entry threshold" — the historic Indian small-house pattern.

### § 4.4 — Endpoint construction

For each topology, C8 constructs `CorridorEndpoint`s:
- **ENTRY**: located on plot.facing edge of buildable envelope; `attached_direction = plot.facing`.
- **BAND_ATTACHMENT**: located on the side of a corridor segment facing the band's direction (from `oriented_candidate.refined_zone_bands`); `attached_band` and `attached_direction` populated.
- **JUNCTION** (L_SHAPE only): at the L's bend; no `attached_band`.
- **STAIR_ATTACHMENT**: defensive only in v1 (single-floor); always None unless C12 vertical-alignment data is present in the future.
- **DEAD_END**: only for degenerate STRIP path.

### § 4.5 — Approx-length sanity check (soft)

After constructing all segments, sum their lengths and compare to C5's `corridor_sketch.approx_length_m`. If `|sum - approx| > 0.15 × approx`, append `"length_drift_>15%"` to `rule_trace`. Does NOT fail (per § 3 invariant 9 note).

### § 4.6 — Validator invariants

(per § 3 dataclass docstring; restated as a numbered list for the validator implementation)

1. `segments` non-empty.
2. Every `width_m >= regulatory_min_width_m` (modulo degenerate-path quirk).
3. All segments axis-aligned to cardinals.
4. Path connectivity: every endpoint shared with another segment, OR is ENTRY / DEAD_END.
5. Exactly one ENTRY endpoint across the full path.
6. PUBLIC, SERVICE, PRIVATE bands each have ≥ 1 BAND_ATTACHMENT (skipped for degenerate path).
7. CIRCULATION band attachment-skip is documented and validator allowed.
8. `connectivity_type` matches upstream C5 contract.
9. (soft) Total length within ±15% of C5 approx_length_m.

---

## § 5 — Invocation contract (public)

```python
designed = design_corridors(
    oriented_candidates=c6_output,
    structural_grid=c7_grid,
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
| `structural_grid` is not a `StructuralGrid` | `TypeError` |
| `plot_analysis` is not `PlotAnalysis` | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066 — same gate as C6) |
| Plot too small to fit `regulatory_min_width_m` corridor on the required topology axis | `CorridorTooNarrowError(B-NNN-B)` |
| Grid has no lines parallel to a needed corridor axis | `NotImplementedError(B-NNN-C)` (rotated grids deferred) |
| L_SHAPE topology but candidate's refined_zone_bands has < 2 distinct cardinal directions | Validator fail at output (defensive — shouldn't happen with valid C6 output) |

---

## § 7 — Test plan

Following C6's pattern. Targets ~120-150 tests across 6+ files:

- `test_c8_failure_modes.py` — all rows in § 6, ~20 tests
- `test_c8_topology_dispatch.py` — STRIP / CENTRAL_SPINE / L_SHAPE / COURTYARD path correctness, ~30 tests
- `test_c8_grid_snapping.py` — snap-on-tolerance, off-grid penalty, multi-segment snap, ~20 tests
- `test_c8_widths.py` — default / entry-stub / constrained-plot narrowing, ~15 tests
- `test_c8_validator.py` — all 9 invariants, ~20 tests
- `test_c8_select.py` — public API end-to-end + provenance + cardinality, ~20 tests
- `test_c8_immutability.py` — frozen dataclasses, ~10 tests

Worked examples (NE 30×40 plot per architecture v2 line 700–712):
- CENTRAL_SPINE: corridor runs N-S, width 1.2m, length ~10.97m, ENTRY at N edge.
- COURTYARD on 40×60: 4-arm loop, each arm width 1.2m, inner clear ~3m.
- STRIP small (15×40): degenerate path, 1.0m stub.

---

## § 8 — KB references

| KB | Status | Used for |
|---|---|---|
| NBC 2016 Part 4 (egress widths) | external; partially verified | regulatory_min_width_m default |
| TNCDBR 2019 rule 42 | referenced in TN rules; text not retrieved | regional override hook (B-NNN-D) |
| Neufert Architects' Data | external; widely-used reference | comfort_target_width_m default |
| Architecture v2 § 8 (BuildemUp internal) | yes | NE 30×40 worked example |

---

## § 9 — Out of scope

| Item | Backlog ID |
|---|---|
| Diagonal corridor segments (axis-aligned only in v1) | **B-NNN-E** |
| Multi-floor vertical corridor coordination | **B-NNN-F** (defer until C12 ships) |
| Per-room door placement on the corridor | C13 (separate component) |
| Circulation-quality scoring (primary/secondary/service) | C14 CirculationAnalyzer |
| Furniture-fit checks for corridor (turning radii, accessibility) | C9 / accessibility backlog |
| Variable-width corridor along a single segment (e.g., bell-mouth at entry) | **B-NNN-G** |
| Stair sizing/integration | C12 |
| **Primary-source verification of NBC 0.9m corridor minimum** | **B-NNN-A** |
| **Hard "corridor too narrow" handling — graceful fallback vs. raise** | **B-NNN-B** |
| **Rotated structural grids** (non-axis-aligned to plot) | **B-NNN-C** |
| **TNCDBR rule 42 + city-specific overrides** | **B-NNN-D** |

(B-NNN placeholders to be assigned at LOCK time; current canonical max = B-107.)

---

## § 10 — Provenance

`CorridorProvenance` carries:
- `derived_at`, `oriented_candidate_trace_id`, `structural_grid_trace_id` — traceability
- `config_snapshot` — exact config used (frozen)
- `rule_trace` — sequence of decisions taken (snap-success-per-segment, length-drift-warning, fallback-fired, etc.)
- `grid_alignment_score` — quality measure for downstream consumers
- `fallback_used` — True if degenerate path or any topology-specific fallback fired

---

## § 11 — Spec metadata

- **Version**: v0.1 DRAFT
- **Status**: DRAFT. Pre-critique. Pending walks → LOCK adjudication.
- **Lineage**: v0.1 DRAFT (S31; S31 first draft post C6 SHIP)
- **Authoring session**: S31
- **Companion artifacts**: C5 SPEC v0.9 LOCKED (corridor_sketch contract); C6 SPEC v0.7 LOCKED (refined_zone_bands contract); C7 (StructuralGrid contract — assumed from upstream code, NOT freshly verified in S31)
- **Web research surface (Rule 7)**: NBC 2016 + TNCDBR 2019 + Neufert references searched; primary source for "0.9m residential corridor minimum" NOT independently verified — flagged in § 3 dataclass docstring + § 9 backlog (B-NNN-A). Pattern C avoidance: the 0.9m value is a configurable parameter, not a hardcoded constant.

---

## § 12 — Backlog enumeration (preliminary; B-NNNs assigned at LOCK)

Total: 7 items, all OUT-of-scope this build.

### B-NNN-A — Primary-source verification of NBC residential corridor minimum width

**Origin**: C8 v0.1 § 3 dataclass docstring + § 11 web-research surface.
**Status**: BACKLOG (Pattern C avoidance — surface uncertainty rather than ship a hardcoded unverified value).
**Description**: The architecture-v2 spec asserts "NBC: 0.9m interior residential" for corridor minimum width. S31 web research located NBC Part 4 references but did not retrieve the exact corridor-width clause for residential; TNCDBR rule 42 was referenced but its text not surfaced. Resolve by retrieving the actual NBC Part 4 + TNCDBR rule 42 text and confirming the 0.9m figure (or correcting the default).
**Trigger**: Before any v1 production deployment that depends on building-code compliance claims; OR before any user-facing copy that cites NBC corridor minimums.
**S31-scope verdict**: OUT — v1 ships with 0.9m as default + configurable override. Verification is a pre-prod task, not a build-blocker.
**Effort**: S (~1 hour: locate NBC Part 4 PDF, locate TNCDBR rule 42 text, update default value if needed).

### B-NNN-B — CorridorTooNarrowError handling: graceful fallback vs raise

**Origin**: C8 v0.1 § 4.3 width-assignment fallback chain.
**Status**: BACKLOG (deferred design dialogue).
**Description**: When plot is too small to fit `regulatory_min_width_m` corridor on the required topology axis, v1 raises `CorridorTooNarrowError`. Real product behavior may need a graceful fallback (e.g., suggest a different topology, propose a no-corridor degenerate path, or flag for user manual override). Resolve via product-decision dialogue + downstream consumer needs.
**Trigger**: First user-reported case OR when C9 (Room Sizer) needs to know whether to expect a corridor or not.
**S31-scope verdict**: OUT — v1 raises; defer graceful handling to product-decision round.
**Effort**: M.

### B-NNN-C — Rotated structural grid support

**Origin**: C8 v0.1 § 4.2 grid-snapping algorithm assumes axis-aligned grid.
**Status**: BACKLOG.
**Description**: v1 assumes `structural_grid.column_lines_x` and `column_lines_y` are axis-aligned cardinal arrays. C7 may eventually produce grids rotated to plot-edge angles (e.g., for non-rectangular plots). C8 needs to support rotated snap geometry then.
**Trigger**: C7 produces a rotated grid (currently rectangular-only via B-066 chain).
**S31-scope verdict**: OUT — gated by B-066 / C7 capability.
**Effort**: M.

### B-NNN-D — TNCDBR rule 42 + city-specific corridor-width overrides

**Origin**: C8 v0.1 § 8 KB references (TNCDBR rule 42 referenced but text not retrieved).
**Status**: BACKLOG.
**Description**: Different cities/states may have stricter or looser corridor-width rules than NBC. v1 uses the NBC default everywhere. Future: per-city KB lookup keyed on `plot_analysis.plot.city`, with TN cities deferring to TNCDBR rule 42, etc.
**Trigger**: User reports plan-rejection due to local rule mismatch; OR product decision to claim regional regulatory accuracy.
**S31-scope verdict**: OUT — v1 single-default is acceptable for MVP.
**Effort**: M.

### B-NNN-E — Diagonal corridor segments

**Origin**: C8 v0.1 § 3 invariant 3 (axis-aligned only).
**Status**: BACKLOG.
**Description**: Some plot shapes / aesthetic preferences benefit from diagonal corridor runs (e.g., aligning with a diagonal sight line). v1 enforces axis-aligned for simplicity + grid-snap predictability.
**Trigger**: Architectural preference signal from users OR non-rectangular plot support (B-066) opens diagonal naturally.
**S31-scope verdict**: OUT.
**Effort**: L.

### B-NNN-F — Multi-floor vertical corridor coordination

**Origin**: C8 v0.1 § 9.
**Status**: BACKLOG.
**Description**: When C12 (Vertical Alignment) ships, multi-floor plans need their corridors stacked to align with stairs across floors. v1 is single-floor.
**Trigger**: C12 ships.
**S31-scope verdict**: OUT — gated by C12.
**Effort**: M.

### B-NNN-G — Variable-width corridor along a single segment

**Origin**: C8 v0.1 § 4.3 (width is per-segment, not per-position-along-segment).
**Status**: BACKLOG.
**Description**: Architectural pattern: bell-mouth widening at entry (1.5m at door, narrows to 1.2m). v1 only supports per-segment widths.
**Trigger**: Aesthetic / experience-quality signal.
**S31-scope verdict**: OUT.
**Effort**: M.

---

## § 13 — Definitions

- **CorridorPath** *(v0.1)*: full corridor design output for one candidate; tuple of `CorridorSegment`s + `total_length_m` + `connectivity_type` mirror.
- **CorridorSegment** *(v0.1)*: one straight axis-aligned section; carries kind, start/end endpoints, width, length, runs_along.
- **CorridorEndpoint** *(v0.1)*: one end of a segment; carries kind (ENTRY/BAND_ATTACHMENT/JUNCTION/STAIR_ATTACHMENT/DEAD_END), point coords, optional band+direction.
- **Degenerate path** *(v0.1 § 4.3.1)*: single ENTRY_STUB segment with no BAND_ATTACHMENTs; represents "no real corridor" small-T1 STRIP case.
- **Grid alignment score** *(v0.1)*: [0, 1] derived metric; 1.0 if every segment snapped cleanly, decreased by 0.7× per off-grid segment.
- **Regulatory min width** *(v0.1)*: configurable parameter; default 0.9m (architecture-v2 asserted; primary-source verification = B-NNN-A).
- **Comfort target width** *(v0.1)*: configurable parameter; default 1.2m (matches C5 sketch nominal_width_m + Neufert residential guidance).
- **Entry stub** *(v0.1)*: short corridor segment from entry door to primary spine; used in CENTRAL_SPINE and COURTYARD topologies where the entry isn't already on the spine.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 (this draft)

#### § 14.1 — C8's scope is geometry, not scoring

C8 produces the corridor's polyline + widths + endpoints. Scoring corridor *quality* (primary/secondary/service path classification, cross-traffic detection) is C14's `CirculationAnalyzer` per architecture v3 § 6. Conflating the two would couple geometry to evaluation prematurely (Pattern E risk).

#### § 14.2 — Topology dispatch is the algorithm core

Five topology kinds → five distinct geometry generators. This mirrors C6's per-topology approach and C5's per-topology decision table. Alternatives considered:
- Generic graph-based corridor generator (RTREE / shortest-path) — REJECTED as overengineering for v1; the topology-kind enum already constrains the design space tightly.
- Single parameterized algorithm with topology as input — REJECTED because the four kinds have genuinely different geometric structures (linear vs. branched vs. loop), not different parameters.

#### § 14.3 — Axis-aligned corridors only in v1

Diagonal corridors deferred to B-NNN-E. Rationale: axis-aligned makes grid snapping deterministic; matches Indian residential vernacular (rectangular rooms in rectangular grids); simplifies C13 door placement downstream. Rejecting diagonal in v1 is a YAGNI call backed by the building-typology survey in architecture v2.

#### § 14.4 — Cardinality preserved across the C5 → C6 → C8 chain

C8 produces one `CorridorDesignedCandidate` per `OrientedCandidate` in, position-paired. Same convention as C6. C8 does NOT prune candidates (that's C14 → C15's job at the evaluation/ranking stages). C8 is a pure transform.

#### § 14.5 — Regulatory width is a parameter, not a constant (Pattern C surface)

The 0.9m default is exposed as `CorridorDesignConfig.regulatory_min_width_m` rather than hardcoded. This converts "we acted on an unverified architecture-v2 claim" into "we surfaced uncertainty as a configuration knob with a documented backlog entry (B-NNN-A)." Prevents Pattern C's "scores-without-truth" trap at the source.

#### § 14.6 — Degenerate path is a first-class output, not an error

For tiny T1 STRIP topologies where C5 sets `corridor_sketch.position == NONE`, C8 returns a documented degenerate `CorridorPath` rather than raising. Rationale: "no corridor" is a valid Indian vernacular pattern (small house, rooms off entry threshold), not a failure case. Treating it as an error would force callers to handle a conditional surface that doesn't reflect the underlying reality.

#### § 14.7 — CIRCULATION band has no BAND_ATTACHMENT (skip in invariant 6)

The CIRCULATION band's "attachment" to the corridor is *the corridor itself*. Treating it as needing a BAND_ATTACHMENT endpoint would create a recursive definitional loop. Validator invariant 6 explicitly skips CIRCULATION band; documented as a quirk so reviewers don't flag it as a missing check.

#### § 14.8 — Length-sanity check is soft, not hard (invariant 9)

C5's `approx_length_m` is sketch-grade; C7 grid scaling can perturb actual geometry by 5-15% legitimately. A hard fail on > 15% drift would create false alarms. Soft warning in `rule_trace` preserves the diagnostic signal without blocking valid output.

### Pushback ledger (preempted critique items)

| Item | Why anticipated | Why this spec doesn't address it |
|---|---|---|
| "Why doesn't C8 score corridor quality?" | Likely critique-walk pushback | C14's CirculationAnalyzer is the documented home; scope split is intentional (§ 14.1) |
| "Diagonal corridors in v1 for Indian non-rectilinear plots?" | Likely critique-walk pushback | B-066 gates non-rectangular plots; B-NNN-E captures diagonal when that ships |
| "Why parameterize regulatory width instead of just looking up NBC?" | Likely critique-walk pushback | Pattern C avoidance (§ 14.5); B-NNN-A is the verification task |
| "Per-floor corridor variation?" | Likely critique-walk pushback | v1 single-floor; B-NNN-F when C12 ships |
| "Hardcoded 0.7 off-grid penalty in grid_alignment_score?" | Likely calibration nit | Pre-empirical; calibration B-090 family |

---

## § 15 — Open questions for next round (or LOCK)

1. **C7 contract** — this draft assumes `structural_grid.column_lines_x: tuple[float, ...]` and `column_lines_y: tuple[float, ...]` plus a `trace_id`. Did NOT freshly verify against C7's actual schema. **Q for Ramalingam: should I grep C7's schema before drafting v0.2, or defer to first critique walk?**

2. **`CorridorDesignConfig` in input vs. session-level constant** — current draft puts it in the function signature. Alternatives: module-level constants (less testable) or per-call kwargs (more verbose). Lean: keep as dataclass in signature; defaults make it optional.

3. **Should C8 emit a degenerate path silently, or surface a flag in provenance?** Current: `provenance.fallback_used = True`. Alternative: separate output type. Lean: flag-on-provenance keeps the type system flat.

4. **Grid-snap penalty value (0.7×)** — pre-empirical placeholder. Calibration B-090 family.

5. **Naming** — is `CorridorDesignedCandidate` clunky? Alternatives: `CorridorBoundCandidate`, `CorridorEnrichedCandidate`. Lean: `CorridorDesignedCandidate` is clearest about what changed.

6. **Test fixture pattern** — should `_c8_fixtures.py` re-export C7's grid fixtures (assumes C7 has them) or build inline? Q for Ramalingam: what does C7's existing test infrastructure look like?

---

## § 16 — End of v0.1 DRAFT

**Spec round summary**:

```
Type           : v0.1 DRAFT (greenfield; no predecessor)
Driver         : Component 8 has been "not started" since project inception;
                 architecture v2 § 8 + v3 (unchanged) is the sole prior signal.
                 C5 (CorridorSketch) and C6 (refined_zone_bands) ship and
                 unblock C8 build.
Authoring      : S31 (post C6 v0.7 LOCKED + SHIP)
Web research   : NBC 2016 + TNCDBR 2019 + Neufert searched (Rule 7).
                 0.9m residential corridor minimum NOT independently verified;
                 surfaced as B-NNN-A + parameterized in CorridorDesignConfig
                 (Pattern C avoidance per § 14.5).
Pushback       : 5 anticipated critique items pre-empted in § 14 ledger
                 (scope-vs-scoring, diagonals, parameterization, multi-floor,
                 grid-snap calibration)
Backlog        : 7 items (B-NNN-A through B-NNN-G); placeholder IDs.
                 B-NNNs assigned at LOCK time; current canonical max = B-107
                 → B-NNN-A would become B-108, etc.
Open questions : 6 items in § 15 — most resolvable in critique walks
Status         : DRAFT. PENDING critique walks → LOCK adjudication.
```

**Awaiting**: critique walk #1 to drive v0.1 → v0.2. Per project Rule 8: LOCK adjudication is Ramalingam's alone. Per project Rule 1: no code touches disk until v0.X LOCKED.
