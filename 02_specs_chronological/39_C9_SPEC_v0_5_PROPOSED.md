# BuildemUp — C9 Room Sizer — SPEC v0.5 PROPOSED

**Status**: PROPOSED. PENDING Ramalingam LOCK adjudication. Per Rule 8, LOCK authority belongs to Ramalingam alone; this document represents the v0.5 candidate after 5 walks (walks #1, #2, #3, #4, #5).
**Component**: C9 of canonical 17-component v3 list (Track 3). Position 9.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C8 (`CorridorDesignedCandidate`) + C7 (`Grid`) + C4 (`PlotAnalysis`) + C1's `FloorRoomBrief`. Produces input for C10 (Bathroom + Wet-Zone Stack Planner) and C11 (Room Placement).
**Authoring sessions**: S33 entire arc.
**Predecessor**: v0.4 PROPOSED (710 lines).

---

## § 0 — Why this spec, why now

C9 sits between "the bands and corridor are designed" and "specific rooms have specific sizes." Given the brief's room composition, the band envelopes from C8, the structural grid bays, and the plot analysis, C9 produces a `RoomSizeTable` — for each room: regulatory floor (area + width + height + clause + source_confidence), liveability minimum (area + interior clear width), target, max.

C9 does NOT place rooms (C11). C9 does NOT generate furniture layouts (C14). C9 does NOT decide adjacencies (C5/C11). C9 does NOT assign rooms to zone bands (C11). C9 does NOT enforce height (C11 — § 14.22). C9 does NOT compute room shape / aspect ratio (C11 — § 14.26). C9 does NOT score sizes (C14).

**v0.5 lineage delta from v0.4 PROPOSED** (6 walk-#5 edits):

| # | Edit | Source | § affected |
|---|---|---|---|
| 1 | `WidthFeasibilityVerdict` enum (FEASIBLE / RISKY / IMPOSSIBLE); per-room provenance map | Walk #5 #1 | § 3, § 4.7, § 10 |
| 2 | `GridBayFeasibility` enum (SINGLE_BAY / DOUBLE_BAY / TRIPLE_BAY / OVERSIZED); replaces arbitrary 2× threshold | Walk #5 #2 | § 3, § 4.7, § 10, § 14 |
| 3 | `assumed_total_dwelling_area_m2: float | None` provenance field for explicit numeric signal | Walk #5 #3 | § 10 |
| 4 | `require_verified_nbc: bool = False` config flag | Walk #5 #4 | § 2, § 6 |
| 5 | `PlacementRiskLevel` enum (LOW / MEDIUM / HIGH); resolves B-152 into spec body | Walk #5 #7 | § 3, § 10, § 12 |
| 6 | Minor doc additions: `other_sizing_behavior` provenance field; § 14.28 area-dominant scope statement | Walk #5 #9, #10 | § 10, § 14 |

Push-backs (no spec change, same architectural-layer reasoning as walks #3-#4): Walk #5 #5 (wall thickness is C11's job per § 14.23), #6 (width is constraint not target/max — § 14.27), #8 (height enforcement is C11 per § 14.22).

---

## § 1 — Purpose

Given a C8-corridor-designed candidate, the brief's room composition, the structural grid bays, and the plot analysis, produce a **`RoomSizeTable`** — for each requested room:
- regulatory floor (area, width, height, clause, source_confidence) per NBC 2016 dwelling tier
- liveability minimum (area + interior clear width)
- target size (area)
- max size (area)

The total of all liveability-min areas must fit within the buildable envelope minus the corridor area (Inv 9). Three WARN-mode safety nets surface placement-readiness signals to downstream consumers without false-positive-rejecting feasible plans:
- Inv 10: heuristic packing check (area-density)
- Inv 17: width-feasibility verdict per room (FEASIBLE / RISKY / IMPOSSIBLE)
- Inv 18: grid-bay feasibility verdict per room (SINGLE_BAY / DOUBLE_BAY / TRIPLE_BAY / OVERSIZED)

A combined `placement_risk_level` (LOW / MEDIUM / HIGH) is derived from these signals so C11 placement and C14 evaluation can read a single risk score without unpacking individual flags.

Cardinality preserved: 1-3 C8 candidates → 1-3 C9 candidates, position-paired.

**Out of scope for C9**:
- Room placement (XY positioning) — C11
- Adjacency / connectivity — C5 selected, C11 enforces
- Zone band assignment for rooms — C11 placement
- Width-to-bay grid feasibility (full check) — C11 placement (C9 does WARN-only n-bay sanity per Inv 18)
- Aspect ratio / room shape — C11 placement geometry (Walk #4 #5 / § 14.26)
- Wall thickness deduction from envelope coords — C11 placement (Walk #4 #4 / § 14.23 / Walk #5 #5)
- Door swing clearance — C13 door placement
- Height enforcement — C11 volume validation (§ 14.22 / Walk #5 #8)
- Furniture layout — C14 furniture-fit metric
- Wet-wall back-to-back stacking — C10
- Vertical alignment across floors — C12
- Cost computation — C14
- Envelope-shape-aware feasibility (geometry-complete) — C11 (§ 14.28 / Walk #5 #10)

---

## § 2 — Input contract

```python
def size_rooms(
    corridor_designed_candidates: tuple[CorridorDesignedCandidate, ...],   # 1-3 from C8
    floor_room_brief: FloorRoomBrief,                                       # from C1
    grid: Grid,                                                              # from C7
    plot_analysis: PlotAnalysis,                                            # from C4
    *,
    config: RoomSizingConfig | None = None,                                 # tunables; default OK
) -> tuple[RoomSizedCandidate, ...]:
```

`RoomSizedCandidate` = `CorridorDesignedCandidate` + `room_size_table: RoomSizeTable` + `provenance: RoomSizingProvenance`.

`RoomSizingConfig` carries per-call tunables:
- `enforcement_mode` (`STRICT` / `WARN`)
- Neufert/Ching multipliers
- `allocation_strategy` (`PRIORITY_GREEDY` / `PROPORTIONAL`)
- `packing_efficiency` (default 0.75)
- `dwelling_tier_override` (None = derived)
- `priority_override` (None = use v1 default)
- **`require_verified_nbc: bool = False`** (NEW v0.5 per Walk #5 #4): when True, C9 raises `KeyError` if any RegulatoryMinimum row used carries `source_confidence != VERIFIED`. v1 default False (pre-B-150 most rows are SECONDARY_CONSENSUS); becomes useful after B-150 verifies rows against authoritative NBC PDF.
- **`assumed_total_dwelling_area_m2: float | None = None`** (NEW v0.5 per Walk #5 #3): when supplied, C9 uses this as the whole-dwelling area for tier resolution instead of per-floor proxy. None means derive per-floor (single-floor) or pick LARGE defensively (multi-floor).

**Why `Grid` is taken** (carried forward from v0.4 § 14.16-bis): provenance capture (`grid_bay_min_m`, `grid_bay_max_m`) + Inv 18 n-bay feasibility verdict per room. Grid availability does not drive sizing computation.

---

## § 3 — Output schema — REVISED v0.5

```python
class RoomCategory(str, Enum):
    BEDROOM    = "bedroom"
    BATHROOM   = "bathroom"
    LIVING     = "living"
    KITCHEN    = "kitchen"
    POOJA      = "pooja"
    UTILITY    = "utility"
    OTHER      = "other"


class DwellingSizeTier(str, Enum):
    SMALL = "small"   # dwelling ≤ 50 m²
    LARGE = "large"   # dwelling > 50 m²


class BathroomSubtype(str, Enum):
    COMBINED = "combined"
    BATH_ONLY = "bath_only"
    WC_ONLY = "wc_only"


class NBCSourceConfidence(str, Enum):
    VERIFIED            = "verified"
    SECONDARY_CONSENSUS = "secondary_consensus"
    SECONDARY_UNVERIFIED= "secondary_unverified"


class TierResolutionAccuracy(str, Enum):
    EXACT                       = "exact"
    APPROXIMATE_DEFENSIVE_LARGE = "approximate_defensive_large"
    OVERRIDE_SUPPLIED           = "override_supplied"


class WidthFeasibilityVerdict(str, Enum):
    """NEW v0.5 (Walk #5 #1) — per-room width-feasibility classification.

    Replaces v0.4's binary "Inv 17 fired or didn't" with a 3-state verdict:
      - FEASIBLE: liveability_min_width_m ≤ 0.9 × envelope_min_axis
        (room fits with typical wall-thickness margin)
      - RISKY: 0.9 × envelope_min_axis < liveability_min_width_m ≤ envelope_min_axis
        (just barely fits envelope min-axis; high probability of failure
        once C11 adds wall thickness)
      - IMPOSSIBLE: liveability_min_width_m > envelope_min_axis
        (deterministic placement impossibility; C11 cannot succeed)

    The 0.9 RISKY threshold is grounded in typical Indian residential
    interior wall thickness as fraction of room width: a 3.0m room has
    ~115mm interior partitions on each side, eating ~7-10% of envelope-to-
    envelope width. The 0.9 boundary is the inflection between "comfortable
    placement" and "wall-thickness-borderline".
    """
    FEASIBLE   = "feasible"
    RISKY      = "risky"
    IMPOSSIBLE = "impossible"


class GridBayFeasibility(str, Enum):
    """NEW v0.5 (Walk #5 #2) — per-room grid-bay feasibility classification.

    Replaces v0.4's arbitrary 2×grid.bay_max_m threshold with the
    architecturally-grounded n-bay framing (residential rooms typically
    span 1, 2, or 3 bays; Wikipedia "Bay (architecture)" + WoodWorks
    structural grid references confirm this is the natural classification).

    Verdicts (computed against grid.bay_max_m):
      - SINGLE_BAY: liveability_min_width_m ≤ bay_max_m (fits in 1 bay)
      - DOUBLE_BAY: bay_max_m < liveability_min_width_m ≤ 2 × bay_max_m
      - TRIPLE_BAY: 2 × bay_max_m < liveability_min_width_m ≤ 3 × bay_max_m
      - OVERSIZED:  liveability_min_width_m > 3 × bay_max_m
        (fundamentally won't fit any 1/2/3-bay placement; OVERSIZED is
        the WARN trigger — anything else is informational)
    """
    SINGLE_BAY = "single_bay"
    DOUBLE_BAY = "double_bay"
    TRIPLE_BAY = "triple_bay"
    OVERSIZED  = "oversized"


class PlacementRiskLevel(str, Enum):
    """NEW v0.5 (Walk #5 #7) — combined risk signal.

    Resolves B-152 by deriving a single risk score from the WARN flags:
      - LOW: no WARNs fired AND all rooms FEASIBLE width AND
        SINGLE_BAY/DOUBLE_BAY/TRIPLE_BAY grid (no OVERSIZED)
      - MEDIUM: heuristic_packing_check_warning OR any room RISKY width
        OR any room TRIPLE_BAY grid (1-2 yellow flags total)
      - HIGH: 3+ yellow flags total OR any IMPOSSIBLE width OR
        any OVERSIZED grid

    Computed at end of validation pass. Consumers (C11, C14) read a
    single risk score without unpacking individual flag fields.
    """
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


@dataclass(frozen=True)
class RegulatoryMinimum:
    """NBC 2016 floor (area + width + height + clause + source_confidence)."""
    area_m2: float
    width_m: float
    height_m: float
    nbc_clause: str
    source_confidence: NBCSourceConfidence


@dataclass(frozen=True)
class RoomSizeRequirement:
    """Per-room sizing requirement.

    Invariants (asserted at construction):
      - 0 < regulatory_minimum.area_m2 ≤ liveability_min_area_m2 ≤ target_m2 ≤ max_m2
      - regulatory_minimum.width_m ≤ liveability_min_width_m
      - is_master is True only on BEDROOM_1 (and BATHROOM_1 if convention applies)
      - bathroom_subtype is set iff category == BATHROOM
      - other_subtype is meaningful iff category == OTHER (echoes brief.other_rooms[i])
    """
    room_id: str
    category: RoomCategory
    regulatory_minimum: RegulatoryMinimum
    liveability_min_area_m2: float
    liveability_min_width_m: float                  # INTERIOR clear width (§ 14.23)
    target_m2: float
    max_m2: float
    priority: int
    is_master: bool = False
    bathroom_subtype: BathroomSubtype | None = None
    other_subtype: str = ""


@dataclass(frozen=True)
class RoomSizeTable:
    """The complete sizing for one C8 candidate's floor."""
    rooms: tuple[RoomSizeRequirement, ...]
    buildable_envelope_minus_corridor_m2: float
    dwelling_size_tier: DwellingSizeTier
    total_liveability_min_area_m2: float
    total_target_m2: float
    surplus_for_distribution_m2: float
    unassigned_area_m2: float
    packing_efficiency_used: float
    floor_label: str


@dataclass(frozen=True)
class RoomSizingProvenance:
    """Provenance for one C9 sizing pass — REVISED v0.5."""
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    nbc_table_version: str
    furniture_kb_version: str
    targets_kb_version: str
    dwelling_size_tier: DwellingSizeTier
    tier_resolution_accuracy: TierResolutionAccuracy
    assumed_total_dwelling_area_m2: float | None    # NEW v0.5 (Walk #5 #3):
                                                     # Set value when OVERRIDE_SUPPLIED OR
                                                     # config supplied. None when EXACT
                                                     # (per-floor known) OR DEFENSIVE_LARGE
                                                     # (genuinely unknown).
    grid_bay_min_m: float
    grid_bay_max_m: float
    enforcement_mode: str
    allocation_strategy: str
    surplus_distributed_m2: float
    rooms_at_min: tuple[str, ...]
    rooms_clamped_at_max: tuple[str, ...]
    packing_basis: str
    heuristic_packing_check_warning: bool
    width_feasibility_per_room: dict[str, WidthFeasibilityVerdict]   # NEW v0.5 (Walk #5 #1):
                                                     # room_id → verdict map. Replaces v0.4's
                                                     # opaque early_width_infeasibility_warnings list.
    grid_bay_feasibility_per_room: dict[str, GridBayFeasibility]     # NEW v0.5 (Walk #5 #2):
                                                     # room_id → n-bay verdict map. Replaces v0.4's
                                                     # opaque grid_bay_max_warnings list.
    placement_risk_level: PlacementRiskLevel        # NEW v0.5 (Walk #5 #7):
                                                     # Combined risk signal; resolves B-152.
    other_sizing_behavior: str                      # NEW v0.5 (Walk #5 #9):
                                                     # "pooled_v1" until B-151 lifts subtype-driven
                                                     # sizing differentiation. Explicit string makes
                                                     # the v1 limitation visible.
    rule_trace: tuple[str, ...]
    # REMOVED v0.5: early_width_infeasibility_warnings (replaced by per-room verdict map)
    # REMOVED v0.5: grid_bay_max_warnings (replaced by per-room verdict map)


@dataclass(frozen=True)
class RoomSizedCandidate:
    """One C8 CorridorDesignedCandidate + C9 sizing."""
    corridor_designed_candidate: CorridorDesignedCandidate
    room_size_table: RoomSizeTable
    provenance: RoomSizingProvenance
```

---

## § 4 — Behavior

### § 4.1 — Regulatory minimums (NBC 2016 KB)

NBC 2016 Part 3 numbers are dwelling-tiered. Carried forward unchanged from v0.4 (tables in § 4.1 SMALL / LARGE; source_confidence per row; LOCK NOT blocked on B-150 verification).

**v0.5 adds**: `RoomSizingConfig.require_verified_nbc: bool = False`. When True at runtime, C9 raises `KeyError` (specifically `NBCConfidenceTooLow`) if any RegulatoryMinimum row used has `source_confidence != VERIFIED`. v1 default False; flag becomes useful after B-150 lands.

#### Dwelling-tier resolution — REVISED v0.5

```python
def _resolve_dwelling_tier(
    candidate: CorridorDesignedCandidate,
    floor_room_brief: FloorRoomBrief,
    config: RoomSizingConfig,
) -> tuple[DwellingSizeTier, TierResolutionAccuracy, float | None]:
    """Returns (tier, accuracy_tag, assumed_total_dwelling_area_m2).

    Walk #5 #3 enrichment: caller can supply config.assumed_total_dwelling_area_m2
    to provide an exact whole-dwelling area; otherwise per-floor is used (with
    defensive LARGE-pick for multi-floor).

    The numeric is propagated to provenance so consumers see the actual
    dwelling-area assumption (or its absence).
    """
    if config.dwelling_tier_override is not None:
        return config.dwelling_tier_override, TierResolutionAccuracy.OVERRIDE_SUPPLIED, None

    if config.assumed_total_dwelling_area_m2 is not None:
        # User supplied whole-dwelling area; tier from that
        a = config.assumed_total_dwelling_area_m2
        tier = DwellingSizeTier.SMALL if a <= 50.0 else DwellingSizeTier.LARGE
        return tier, TierResolutionAccuracy.OVERRIDE_SUPPLIED, a

    is_multi_floor = floor_room_brief.floor_label.lower() not in ("ground", "ground_floor", "gf")
    if is_multi_floor:
        return DwellingSizeTier.LARGE, TierResolutionAccuracy.APPROXIMATE_DEFENSIVE_LARGE, None

    envelope_areas = sum(e.area_m2 for e in candidate.corridor_path.envelopes)
    tier = DwellingSizeTier.SMALL if envelope_areas <= 50.0 else DwellingSizeTier.LARGE
    return tier, TierResolutionAccuracy.EXACT, envelope_areas  # per-floor area is the assumption
```

### § 4.2 — Liveability minimums (furniture-fit floor)

Carried forward unchanged from v0.4. `liveability_min_width_m` = max(regulatory.width_m, furniture.min_width_m); INTERIOR clear width per § 14.23.

### § 4.3 — Target sizes

Carried forward unchanged from v0.3/v0.4. KB-managed via `kb/room_targets.json`.

### § 4.4 — Max sizes

Carried forward unchanged from v0.3/v0.4.

### § 4.5 — Surplus allocation

Carried forward unchanged from v0.3/v0.4. `PRIORITY_GREEDY` default; `PROPORTIONAL` alternative; leftover → `unassigned_area_m2`.

### § 4.6 — Infeasibility detection

Carried forward unchanged from v0.4. Hard-fail on Inv 9 area infeasibility.

### § 4.7 — Validator invariants — REVISED v0.5

| # | Invariant | Source | Mode |
|---|---|---|---|
| 1 | rooms.count == FloorRoomBrief total | brief consistency | RAISE |
| 2 | category counts match brief | brief consistency | RAISE |
| 3 | regulatory_minimum.area_m2 ≥ NBC table value | NBC compliance | RAISE |
| 4 | regulatory_minimum.width_m ≥ NBC table value | NBC compliance | RAISE |
| 5 | regulatory_minimum.height_m ≥ NBC table value | NBC compliance | RAISE |
| 6 | liveability_min_area_m2 ≥ regulatory_minimum.area_m2 | math | RAISE |
| 6b | liveability_min_width_m ≥ regulatory_minimum.width_m | math | RAISE |
| 7 | target_m2 ≥ liveability_min_area_m2 | math | RAISE |
| 8 | max_m2 ≥ target_m2 | math | RAISE |
| 9 | Σ liveability_min_area_m2 ≤ buildable_envelope_minus_corridor_m2 | feasibility | RAISE |
| 10 | Σ liveability_min_area_m2 ≤ envelope × packing_efficiency (heuristic_packing_check) | placement-readiness heuristic | **WARN** |
| 11 | room_ids unique | data integrity | RAISE |
| 12 | priority values cover 1..n contiguously | well-formedness | RAISE |
| 13 | exactly one BEDROOM has is_master=True iff bedroom_count ≥ 1 | master semantics | RAISE |
| 14 | at most one BATHROOM has is_master=True | master semantics | RAISE |
| 15 | bathroom_subtype is set iff category == BATHROOM | schema integrity | RAISE |
| 16 | unassigned_area_m2 ≥ 0 | math | RAISE |
| **17** | **for every room, classify width feasibility (FEASIBLE / RISKY / IMPOSSIBLE)** (REVISED v0.5 per Walk #5 #1) | early width infeasibility | **WARN** if any IMPOSSIBLE; informational otherwise |
| **18** | **for every room, classify grid-bay feasibility (SINGLE_BAY / DOUBLE_BAY / TRIPLE_BAY / OVERSIZED)** (REVISED v0.5 per Walk #5 #2) | grid-bay sanity heuristic | **WARN** if any OVERSIZED; informational otherwise |

**Inv 17 (REVISED v0.5)**: instead of binary "WARN if room width > envelope min-axis", v0.5 produces a per-room `WidthFeasibilityVerdict`. Provenance carries `width_feasibility_per_room: dict[room_id, verdict]` so consumers see the full classification, not just a flag. WARN fires only when any room is IMPOSSIBLE; RISKY rooms produce informational entries (not WARNs).

**Inv 18 (REVISED v0.5)**: instead of arbitrary `2 × grid.bay_max_m` threshold, v0.5 produces a per-room `GridBayFeasibility` verdict (SINGLE_BAY / DOUBLE_BAY / TRIPLE_BAY / OVERSIZED). The n-bay framing is grounded in residential architectural practice (rooms span 1, 2, or 3 bays naturally; Wikipedia "Bay (architecture)", structural grid references). WARN fires only when any room is OVERSIZED.

**`placement_risk_level` derivation (NEW v0.5 per Walk #5 #7)**:
```python
def _derive_placement_risk_level(
    width_verdicts: dict[str, WidthFeasibilityVerdict],
    grid_verdicts: dict[str, GridBayFeasibility],
    packing_warning: bool,
) -> PlacementRiskLevel:
    has_impossible = any(v == WidthFeasibilityVerdict.IMPOSSIBLE for v in width_verdicts.values())
    has_oversized = any(v == GridBayFeasibility.OVERSIZED for v in grid_verdicts.values())
    if has_impossible or has_oversized:
        return PlacementRiskLevel.HIGH

    yellow_flags = 0
    if packing_warning:
        yellow_flags += 1
    if any(v == WidthFeasibilityVerdict.RISKY for v in width_verdicts.values()):
        yellow_flags += 1
    if any(v == GridBayFeasibility.TRIPLE_BAY for v in grid_verdicts.values()):
        yellow_flags += 1

    if yellow_flags >= 3:
        return PlacementRiskLevel.HIGH
    if yellow_flags >= 1:
        return PlacementRiskLevel.MEDIUM
    return PlacementRiskLevel.LOW
```

Stored in `provenance.placement_risk_level`.

### § 4.8 — Order-of-checks

Type checks → shape (B-066) → brief sanity → dwelling-tier resolution (with accuracy + numeric) → grid-bay capture → per-candidate regulatory lookup (with require_verified_nbc gate) → liveability resolution → infeasibility check (Inv 9) → surplus allocation → validator (Invs 1-18 with verdict-derivation for 17/18) → placement_risk_level derivation. Pattern A: fail at boundary; surface via WARN where over-strict; classify-not-flag for richer downstream signals.

---

## § 5 — Invocation contract (public)

```python
sized = size_rooms(
    corridor_designed_candidates=c8_output,
    floor_room_brief=c1_brief.floors[0],
    grid=c7_grid,
    plot_analysis=c4_plot_analysis,
)

# Optional v0.5 patterns:
sized = size_rooms(
    ...,
    config=RoomSizingConfig(
        require_verified_nbc=True,                # post-B-150 strict mode
        assumed_total_dwelling_area_m2=120.0,     # multi-floor exact tier
    ),
)
```

Cardinality: 1-3 in → 1-3 out, position-paired.

---

## § 6 — Failure modes — REVISED v0.5

| Condition | Behavior |
|---|---|
| `corridor_designed_candidates` not a tuple | `TypeError` |
| `floor_room_brief` not FloorRoomBrief | `TypeError` |
| `grid` not Grid | `TypeError` |
| `plot_analysis` not PlotAnalysis | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066) |
| Brief specifies 0 bedrooms | `ValueError` |
| Brief specifies 0 bathrooms | passes through |
| Brief specifies has_living=False | passes through; LIVING absent |
| Brief specifies has_kitchen=False | passes through; KITCHEN absent |
| brief.floor_label != "Ground" AND no `assumed_total_dwelling_area_m2` | tier_resolution_accuracy=APPROXIMATE_DEFENSIVE_LARGE; assumed_total_dwelling_area_m2=None in provenance |
| Σ liveability_min_area > envelope (Inv 9) | `RoomSizingInfeasibleError` (B-NNN-A) |
| Σ liveability_min_area > envelope × packing_efficiency (Inv 10) | log to provenance; no raise |
| Any room's WidthFeasibilityVerdict == IMPOSSIBLE (Inv 17) | logged in `width_feasibility_per_room`; placement_risk_level=HIGH; no raise |
| Any room's GridBayFeasibility == OVERSIZED (Inv 18) | logged in `grid_bay_feasibility_per_room`; placement_risk_level=HIGH; no raise |
| `config.require_verified_nbc=True` AND any row used has `source_confidence != VERIFIED` | `KeyError` (`NBCConfidenceTooLow`) |
| One room category's NBC table entry missing for resolved tier | `KeyError` (KB integrity) |
| Empty input tuple | Returns empty tuple |

---

## § 7 — Test plan — REVISED v0.5

v0.5 targets **~130 tests** with explicit invariant→test mapping:

### Invariant coverage

| Inv # | Invariant | Test count | Test file |
|---|---|---|---|
| 1 | rooms.count == brief total | 6 | test_c9_schema.py |
| 2 | category counts match brief | 8 | test_c9_schema.py |
| 3 | regulatory.area ≥ NBC value | 10 | test_c9_nbc_table.py |
| 4 | regulatory.width ≥ NBC value | 8 | test_c9_nbc_table.py |
| 5 | regulatory.height ≥ NBC value | 6 | test_c9_nbc_table.py |
| 6 | liveability_area ≥ regulatory.area | 4 | test_c9_schema.py |
| 6b | liveability_width ≥ regulatory.width | 6 | test_c9_schema.py |
| 7 | target ≥ liveability_area | 4 | test_c9_schema.py |
| 8 | max ≥ target | 4 | test_c9_schema.py |
| 9 | Σ liveability_area ≤ envelope (RAISE) | 6 | test_c9_orchestrator.py |
| 10 | Σ liveability_area ≤ envelope × packing_efficiency (WARN) | 4 | test_c9_orchestrator.py |
| 11 | room_ids unique | 3 | test_c9_schema.py |
| 12 | priority contiguous | 4 | test_c9_schema.py |
| 13 | one BEDROOM is_master | 4 | test_c9_schema.py |
| 14 | at most one BATHROOM is_master | 4 | test_c9_schema.py |
| 15 | bathroom_subtype iff category=BATHROOM | 4 | test_c9_schema.py |
| 16 | unassigned_area_m2 ≥ 0 | 3 | test_c9_schema.py |
| **17** | **width_feasibility_per_room verdicts (FEASIBLE/RISKY/IMPOSSIBLE)** | 9 | test_c9_orchestrator.py |
| **18** | **grid_bay_feasibility_per_room verdicts (SINGLE/DOUBLE/TRIPLE/OVERSIZED)** | 8 | test_c9_orchestrator.py |
| **PRL** | **placement_risk_level derivation (LOW/MEDIUM/HIGH paths)** | 6 | test_c9_orchestrator.py |
| **Subtotal — invariants** | | **111** | |

### Module-coverage

| Module | Tests | Focus |
|---|---|---|
| nbc_table.py | ~12 | dwelling-tier; clauses; subtype variants; require_verified_nbc gate |
| furniture_floor.py | ~10 | (category, is_master, bathroom_subtype) lookup |
| targets_kb.py | ~6 | (category, is_master) target lookup |
| allocator.py | ~12 | PRIORITY_GREEDY / PROPORTIONAL / max-clamp |
| size_rooms (orchestrator) | ~15 | end-to-end; tier accuracy enum; assumed_total_dwelling_area_m2 paths |
| failure_modes | ~15 | type checks; B-066; edge cases |
| **Subtotal — coverage** | | **~70** | |

**Combined estimate ≈ 130 tests** (some invariant tests double as module-coverage tests).

---

## § 8 — KB references

Carried forward from v0.4:

| KB | Status | Used for |
|---|---|---|
| `kb/nbc_room_minimums.json` | NEW v0.2 (rev. v0.4) | NBC dwelling-tiered table; `source_confidence` per row |
| `kb/furniture_floor.json` | NEW v0.2 (rev. v0.3) | (category, is_master, bathroom_subtype) → (area_m2, min_width_m, ref_config) |
| `kb/room_targets.json` | NEW v0.3 | (category, is_master) → target_m2 |
| `kb/state_dcr_overrides.json` | stub; B-NNN-D | TNCDBR / Maharashtra / KMC overrides |

---

## § 9 — Out of scope

| Item | Backlog ID |
|---|---|
| State-DCR room-size overrides | B-NNN-D |
| Plot-tier-aware target sizing | B-NNN-B |
| Configurable priority order beyond default | B-NNN-C |
| Multi-floor sizing coordination | B-NNN-E |
| Furniture KB versioning + per-room customization | B-NNN-F |
| Soft-fail mode + C2 retry contract | B-NNN-A |
| BR/BA pooling rules | B-NNN-I |
| Multi-floor dwelling-tier (whole-dwelling, when not user-supplied) | B-148 |
| Packing-efficiency tightening to ERROR mode | B-149 |
| NBC clause verification against authoritative PDF | B-150 |
| OTHER subtype-driven sizing differentiation | B-151 |
| ~~Combined placement_risk_level~~ RESOLVED v0.5 in spec body | (B-152 closed) |
| Aspect ratio / shape constraints | C11 placement (§ 14.26) |
| Width-to-bay grid feasibility (full check) | C11 placement |
| Wall thickness deduction from envelope coords | C11 placement (§ 14.23) |
| Door swing clearance | C13 |
| Height enforcement | C11 (§ 14.22) |
| Envelope-shape-aware feasibility (geometry-complete) | C11 (§ 14.28) |

---

## § 10 — Provenance — REVISED v0.5

`RoomSizingProvenance` fields (cumulative):

**Traceability**: `derived_at`, `plot_analysis_trace_id`, `floor_label`
**KB versions**: `nbc_table_version`, `furniture_kb_version`, `targets_kb_version`
**Tier resolution**: `dwelling_size_tier`, `tier_resolution_accuracy`, `assumed_total_dwelling_area_m2` (NEW v0.5)
**Grid context**: `grid_bay_min_m`, `grid_bay_max_m`
**Config**: `enforcement_mode`, `allocation_strategy`
**Allocation results**: `surplus_distributed_m2`, `rooms_at_min`, `rooms_clamped_at_max`
**Heuristic packing**: `packing_basis`, `heuristic_packing_check_warning`
**Per-room verdicts (NEW v0.5)**: `width_feasibility_per_room: dict[str, WidthFeasibilityVerdict]`, `grid_bay_feasibility_per_room: dict[str, GridBayFeasibility]`
**Combined risk (NEW v0.5)**: `placement_risk_level: PlacementRiskLevel`
**v1 limitation visibility (NEW v0.5)**: `other_sizing_behavior: str = "pooled_v1"`
**Debug**: `rule_trace`

---

## § 11 — Spec metadata

- **Version**: v0.5 PROPOSED
- **Status**: PROPOSED — pending Ramalingam LOCK adjudication
- **Lineage**: v0.1 DRAFT → v0.2 → v0.3 → v0.4 → v0.5 (5 walks completed)
- **Authoring sessions**: S33 entire arc

**Convergence trajectory after 5 walks**:

| Walk | Findings | Net new actionable | Push-backs |
|---|---|---|---|
| #1 | 15 | 12 | 0 |
| #2 | 15 | 2 | 0 |
| #3 | 11 | 3 | 2 |
| #4 | 10 | 4 | 2 |
| #5 | 10 | 6 | 3 |

Walk #5 added more refinements than walks #3-#4 (6 net new) but the refinements were **classification + signal-richness improvements**, not architectural defects. No HIGH-severity findings since walk #1. Push-backs are stable at 2-3 per walk and consistent in their architectural-layer-separation reasoning. The system has converged to "production-ready v1 with classification richness."

---

## § 12 — Backlog enumeration

Total: **12 items** (was 13 in v0.4; -1 because B-152 resolved into v0.5 spec body).

| ID | Title | Origin | Status | Trigger | Effort |
|---|---|---|---|---|---|
| B-NNN-A | Soft-fail mode + C2 retry | § 4.6 / Q8 | BACKLOG | C2 feasibility loop | M |
| B-NNN-B | Plot-tier-aware target sizing | § 4.3 | BACKLOG | Empirical signal | S |
| B-NNN-C | Configurable priority order beyond default | § 4.5 | BACKLOG | First user request | S |
| B-NNN-D | State DCR overrides | § 4.1 | BACKLOG | Municipality rejection | M |
| B-NNN-E | Multi-floor coordination | § scope | BACKLOG | C12 vertical alignment | L |
| B-NNN-F | Furniture KB versioning | § 4.2 | BACKLOG | Customization feature | M |
| B-NNN-I | Bath assignment rules | § 4.2 | BACKLOG | C11 placement | M |
| B-148 | Multi-floor dwelling-tier (whole-dwelling auto-derived) | § 4.1 | BACKLOG | Multi-floor test case where user didn't supply assumed_total_dwelling_area_m2 | M |
| B-149 | Packing-efficiency to ERROR mode | § 4.7 Inv 10 | BACKLOG | Calibration data | S |
| B-150 | NBC clause verification | § 4.1 / § 8 | BACKLOG | Verification pass complete | S |
| B-151 | OTHER subtype-driven sizing | § 9 | BACKLOG | First product feature | M |
| ~~B-152~~ | ~~Combined placement_risk_level~~ RESOLVED v0.5 | § 12 | CLOSED | (resolved into spec body) | — |
| (deferred to C11) | Aspect ratio / shape constraints | Walk #4 #5 | C11 spec | C11 build | (in C11) |
| (deferred to C11) | Width-to-bay grid feasibility (full check) | Walk #3 #2 | C11 spec | C11 build | (in C11) |
| (deferred to C11) | Wall thickness deduction from envelope | Walk #4 #4 / Walk #5 #5 | C11 spec | C11 build | (in C11) |
| (deferred to C13) | Door swing clearance | Walk #4 #4 | C13 spec | C13 build | (in C13) |
| (deferred to C11) | Height enforcement | Walk #4 #10 / Walk #5 #8 | C11 spec | C11 build | (in C11) |
| (deferred to C11) | Envelope-shape-aware feasibility | Walk #5 #10 | C11 spec | C11 build | (in C11) |

---

## § 13 — Definitions

Cumulative across walks (most carried; v0.5 additions marked):

- **`regulatory_minimum`** *(v0.2; rev v0.4)*: NBC 2016 floor (area + width + height + clause + source_confidence).
- **`liveability_min_area_m2`** *(v0.2)*: max(regulatory.area_m2, furniture.area_m2).
- **`liveability_min_width_m`** *(v0.3; clarified v0.4)*: INTERIOR clear width; max(regulatory.width_m, furniture.min_width_m).
- **`target_m2`** *(v0.2; KB-managed v0.3)*: comfortable size from `kb/room_targets.json`.
- **`max_m2`** *(v0.2)*: waste threshold; per-category multipliers per § 4.4.
- **`buildable_envelope_minus_corridor_m2`** *(v0.2)*: from C8's corridor_path.envelopes total minus corridor area.
- **`DwellingSizeTier`** *(v0.2)*: SMALL ≤50 m² / LARGE >50 m².
- **`TierResolutionAccuracy`** *(v0.4)*: EXACT / APPROXIMATE_DEFENSIVE_LARGE / OVERRIDE_SUPPLIED.
- **`assumed_total_dwelling_area_m2`** *(NEW v0.5)*: numeric signal of the dwelling-area assumption (None when unknown).
- **`is_master`** *(v0.2)*: True for BEDROOM_1 (and BATHROOM_1 if convention applies).
- **`bathroom_subtype`** *(v0.3)*: COMBINED (default) / BATH_ONLY / WC_ONLY.
- **`other_subtype`** *(v0.4)*: free-text echo of brief.other_rooms[i].
- **`source_confidence`** *(v0.4)*: VERIFIED / SECONDARY_CONSENSUS / SECONDARY_UNVERIFIED.
- **`require_verified_nbc`** *(NEW v0.5)*: config flag; True forces VERIFIED-only rows.
- **`packing_efficiency`** *(v0.2)*: default 0.75; heuristic ratio for Inv 10.
- **`packing_basis`** *(v0.3)*: provenance string (`"heuristic_v1_static_0.75"`).
- **`unassigned_area_m2`** *(v0.3)*: explicit field for leftover envelope after surplus allocation.
- **`grid_bay_min_m` / `grid_bay_max_m`** *(v0.4)*: provenance fields capturing grid bay extremes.
- **`WidthFeasibilityVerdict`** *(NEW v0.5)*: FEASIBLE / RISKY / IMPOSSIBLE.
- **`GridBayFeasibility`** *(NEW v0.5)*: SINGLE_BAY / DOUBLE_BAY / TRIPLE_BAY / OVERSIZED.
- **`PlacementRiskLevel`** *(NEW v0.5)*: LOW / MEDIUM / HIGH (combined risk signal).
- **`width_feasibility_per_room`** *(NEW v0.5)*: provenance map of room_id → WidthFeasibilityVerdict.
- **`grid_bay_feasibility_per_room`** *(NEW v0.5)*: provenance map of room_id → GridBayFeasibility.
- **`other_sizing_behavior`** *(NEW v0.5)*: provenance string ("pooled_v1") making v1 OTHER limitation visible.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 DRAFT
§ 14.1 — Two-floor minimum (regulatory + liveability).
§ 14.2 — `PRIORITY_GREEDY` as v1 default.
§ 14.3 — Hard-fail on infeasibility (v1).
§ 14.4 — NBC table is KB-managed JSON.

### From v0.2 PROPOSED
§ 14.5 — C9 receives `FloorRoomBrief` directly.
§ 14.6 — Master/non-master via `priority` and `is_master`, not category.
§ 14.7 — `regulatory_minimum` is a triple (area + width + height).
§ 14.8 — `consumption_band` field DROPPED.
§ 14.9 — Dwelling-tier resolved from C8 envelope total per floor.
§ 14.10 — Packing-efficiency check is WARN, not RAISE.
§ 14.11 — `max_m2` per-category multipliers internally consistent.

### From v0.3 PROPOSED
§ 14.12 — Liveability includes width, not just area (CRITICAL).
§ 14.13 — Multi-floor dwelling-tier handled defensively.
§ 14.14 — Width feasibility deferred to C11 (full check).
§ 14.15 — Heuristic_packing_check is heuristic, not guarantee.
§ 14.16 — Grid input rationale: trace + future B-148 + config-flagged sizing.
§ 14.17 — `unassigned_area_m2` as explicit field.
§ 14.18 — Targets KB-managed.
§ 14.19 — Priority is first-class config.
§ 14.20 — Bathroom subtype is schema-explicit.
§ 14.21 — Secondary-source NBC disagreement documented.

### From v0.4 PROPOSED
§ 14.16-bis — Grid input is functionally consumed (provenance + Inv 18).
§ 14.22 — Height enforcement is C11's responsibility.
§ 14.23 — `liveability_min_width_m` is interior clear width; wall thickness is C11.
§ 14.24 — NBC source confidence is exposed, not hidden; LOCK NOT blocked on B-150.
§ 14.25 — Tier resolution accuracy is 3-state enum, not binary.
§ 14.26 — Aspect ratio is C11 placement geometry, not C9.
§ 14.27 — Width is constraint, not target/max dimension.

### NEW v0.5 (resolved per Walk #5)

§ 14.28 — **C9 is area-dominant, not geometry-complete** (Walk #5 #10). Long narrow envelope handling, room shape, aspect ratio, and depth/width geometric coupling are all C11 placement geometry. Inv 17 catches the trivial impossibility (room width > envelope min-axis) but does not validate full envelope-shape feasibility.

§ 14.29 — **Width-feasibility is classified, not just flagged** (Walk #5 #1). Walk #4's binary "Inv 17 fired or didn't" is enriched in v0.5 to a 3-state per-room verdict (FEASIBLE / RISKY / IMPOSSIBLE). Provenance carries the full `width_feasibility_per_room` map. The 0.9 RISKY threshold is grounded in typical Indian residential interior wall thickness (~7-10% of envelope-to-envelope width).

§ 14.30 — **Grid-bay feasibility uses n-bay framing, not arbitrary thresholds** (Walk #5 #2). Walk #4's `2 × grid.bay_max_m` was an arbitrary heuristic. v0.5 replaces it with n-bay classification (SINGLE_BAY / DOUBLE_BAY / TRIPLE_BAY / OVERSIZED) — grounded in actual residential architectural practice where rooms span 1, 2, or 3 bays naturally. WARN fires only when OVERSIZED.

§ 14.31 — **Combined placement_risk_level is derived, not separately computed** (Walk #5 #7 — resolves B-152). Instead of fragmenting risk signals across multiple WARN flags, v0.5 derives a single `PlacementRiskLevel` (LOW / MEDIUM / HIGH) from the existing flags. C11 placement and C14 evaluation can read a single risk score; debugging traces individual flags via provenance per-room verdict maps.

§ 14.32 — **NBC verification can be enforced when needed** (Walk #5 #4). `require_verified_nbc: bool = False` config flag lets callers (post-B-150) require all rows used to be VERIFIED. v1 default False since most rows are SECONDARY_CONSENSUS pre-B-150.

§ 14.33 — **Multi-floor dwelling-area can be user-supplied** (Walk #5 #3). `assumed_total_dwelling_area_m2: float | None` config field lets callers supply the whole-dwelling area when known (lifting the defensive-LARGE assumption for multi-floor briefs). The numeric is propagated to provenance for transparency. B-148 remains for the case when caller doesn't supply but C2 could automatically derive.

§ 14.34 — **v1 OTHER pooling is explicitly visible in provenance** (Walk #5 #9). `other_sizing_behavior: str = "pooled_v1"` makes the v1 limitation visible in provenance so consumers (and future code review) see the simplification rather than discovering it. Becomes "subtype_driven" when B-151 lifts.

---

## § 15 — Open questions remaining

After 5 walks the open-questions list is essentially closed. Only one residual question:

### Q14 — Should max_m2 multipliers also live in `kb/room_targets.json`?

**Recommendation for LOCK**: yes; move to KB. Then user briefs can override via `RoomSizingConfig.targets_kb_override`. Decide at LOCK; either way it's a one-line spec change.

### NEW Q16 — Confirm 0.9 width-feasibility RISKY threshold

The 0.9 boundary between FEASIBLE and RISKY in `WidthFeasibilityVerdict` is grounded in typical interior wall thickness. Confirm at LOCK or call walk #6 to refine.

**Recommendation**: ship 0.9 as v1; calibrate from C11 placement-failure data over time.

---

## § 16 — End of v0.5 PROPOSED

Expected next: Ramalingam LOCK adjudication → build (D-066 step 6-8).

If LOCKED, the build session can begin immediately:
- 3 KB JSONs authored (`nbc_room_minimums.json`, `furniture_floor.json`, `room_targets.json`)
- ~7 production modules under `buildemup/components/c09/` (schema, nbc_table, furniture_floor, targets_kb, allocator, validator, room_sizer)
- ~130 tests authored matching § 7 invariant→test mapping

After 5 walks of converging discipline (push-backs stable at 2-3 per walk; no HIGH-severity findings since walk #1; v0.5 refinements are all classification/richness improvements not architectural changes), the system is **production-ready v1**.
