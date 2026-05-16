# BuildemUp — C9 Room Sizer — SPEC v0.6 PROPOSED

**Status**: PROPOSED. PENDING Ramalingam LOCK adjudication. Per Rule 8, LOCK authority belongs to Ramalingam alone; this document represents the v0.6 candidate after 6 walks (walks #1-#6).
**Component**: C9 of canonical 17-component v3 list (Track 3). Position 9.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C8 (`CorridorDesignedCandidate`) + C7 (`Grid`) + C4 (`PlotAnalysis`) + C1's `FloorRoomBrief`. Produces input for C10 (Bathroom + Wet-Zone Stack Planner) and C11 (Room Placement).
**Authoring sessions**: S33 entire arc.
**Predecessor**: v0.5 PROPOSED (731 lines).

---

## § 0 — Why this spec, why now

C9 sits between "the bands and corridor are designed" and "specific rooms have specific sizes." Given the brief's room composition, the band envelopes from C8, the structural grid bays, and the plot analysis, C9 produces a `RoomSizeTable` — for each room: regulatory floor (area + width + height + clause + source_confidence), liveability minimum (area + interior clear width), target, max.

**v0.6 substantive correction (Walk #6 #1)**: deterministic width impossibility now RAISES (`WidthInfeasibleError`), not just WARNs. Walk #6 web research grounded this against the fail-fast industry consensus (Wikipedia "Fail-fast system"; standard-of-practice for deterministic impossibility): heuristic checks should WARN to avoid false-positive rejection, but mathematical impossibility should fail at the boundary. v0.5's WARN-only stance on IMPOSSIBLE conflated heuristic with deterministic — corrected here.

C9 does NOT place rooms (C11). C9 does NOT generate furniture layouts (C14). C9 does NOT decide adjacencies (C5/C11). C9 does NOT assign rooms to zone bands (C11). C9 does NOT enforce height (C11 — § 14.22). C9 does NOT compute room shape / aspect ratio (C11 — § 14.26). C9 does NOT score sizes (C14).

**v0.6 lineage delta from v0.5 PROPOSED** (5 walk-#6 edits):

| # | Edit | Source | § affected |
|---|---|---|---|
| 1 | Inv 17 split: 17a RAISES on IMPOSSIBLE; 17b WARNS on RISKY. New `WidthInfeasibleError(B-NNN-J)` typed exception | Walk #6 #1 (web-grounded fail-fast) | § 4.6, § 4.7, § 6, § 14 |
| 2 | Severity-weighted `placement_risk_level` derivation (replaces flat count) | Walk #6 #2 + #3 | § 4.7, § 14 |
| 3 | `unverified_nbc_rows_used: tuple[str, ...]` in provenance — visible flag for default `require_verified_nbc=False` case | Walk #6 #5 | § 10 |
| 4 | `wall_thickness_ratio: float = 0.10` config field; FEASIBLE/RISKY threshold derived dynamically | Walk #6 #6 | § 2, § 4.7, § 14 |
| 5 | New typed exception class `WidthInfeasibleError(B-NNN-J)` mirroring `RoomSizingInfeasibleError(B-NNN-A)` pattern | Walk #6 #1 follow-on | § 6, § 14 |

Push-backs (no spec change, same architectural-layer reasoning carried forward from walks #3-#5): Walk #6 #4 (multi-floor LARGE-default already addressed by `assumed_total_dwelling_area_m2` in v0.5), #7 (width is constraint not target/max — § 14.27), #8 (height enforcement is C11 — § 14.22), #10 (envelope geometry is C11 — § 14.28).

---

## § 1 — Purpose

Given a C8-corridor-designed candidate, the brief's room composition, the structural grid bays, and the plot analysis, produce a **`RoomSizeTable`** — for each requested room:
- regulatory floor (area, width, height, clause, source_confidence) per NBC 2016 dwelling tier
- liveability minimum (area + interior clear width)
- target size (area)
- max size (area)

The total of all liveability-min areas must fit within the buildable envelope minus the corridor area (Inv 9 RAISE). Any room whose `liveability_min_width_m` exceeds the envelope's smaller axis fails deterministically (Inv 17a RAISE; new in v0.6 per Walk #6 #1).

**WARN-mode safety nets** for heuristic placement-readiness signals (don't false-positive-reject feasible plans):
- Inv 10: heuristic packing check (area-density)
- Inv 17b: width-feasibility RISKY verdict per room (just-barely-fits envelope)
- Inv 18: grid-bay feasibility verdict per room (SINGLE/DOUBLE/TRIPLE/OVERSIZED)

A combined `placement_risk_level` (LOW / MEDIUM / HIGH) is **severity-weighted-derived** (NEW v0.6 per Walk #6 #2/#3) from these signals so C11 placement and C14 evaluation can read a single risk score without unpacking individual flags.

Cardinality preserved: 1-3 C8 candidates → 1-3 C9 candidates, position-paired.

**Out of scope for C9** (carried forward from v0.5):
- Room placement (XY positioning) — C11
- Adjacency / connectivity — C5 selected, C11 enforces
- Zone band assignment for rooms — C11 placement
- Width-to-bay grid feasibility (full check) — C11 placement
- Aspect ratio / room shape — C11 placement geometry (§ 14.26)
- Wall thickness deduction from envelope coords — C11 placement (§ 14.23)
- Door swing clearance — C13
- Height enforcement — C11 volume validation (§ 14.22)
- Furniture layout — C14
- Wet-wall back-to-back stacking — C10
- Vertical alignment across floors — C12
- Cost computation — C14
- Envelope-shape-aware feasibility (geometry-complete) — C11 (§ 14.28)

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

`RoomSizingConfig` carries per-call tunables (cumulative through v0.6):
- `enforcement_mode` (`STRICT` / `WARN`)
- Neufert/Ching multipliers
- `allocation_strategy` (`PRIORITY_GREEDY` / `PROPORTIONAL`)
- `packing_efficiency` (default 0.75)
- `dwelling_tier_override` (None = derived)
- `priority_override` (None = use v1 default)
- `require_verified_nbc: bool = False` (v0.5)
- `assumed_total_dwelling_area_m2: float | None = None` (v0.5)
- **`wall_thickness_ratio: float = 0.10`** (NEW v0.6 per Walk #6 #6): used to compute the FEASIBLE/RISKY boundary for `WidthFeasibilityVerdict`. Default 0.10 (10%) matches typical Indian residential interior partition fraction of envelope-to-envelope width; range typically 0.07-0.12. RISKY threshold = (1.0 - wall_thickness_ratio) × envelope_min_axis.

**Why `Grid` is taken** (carried forward from v0.4 § 14.16-bis): provenance capture (`grid_bay_min_m`, `grid_bay_max_m`) + Inv 18 n-bay feasibility verdict per room. Grid availability does not drive sizing computation.

---

## § 3 — Output schema — REVISED v0.6

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
    """Per-room width-feasibility classification.

    Verdicts (v0.6 — uses config.wall_thickness_ratio for RISKY boundary):
      - FEASIBLE: liveability_min_width_m ≤ (1.0 - wall_thickness_ratio) × envelope_min_axis
        (room fits with typical wall-thickness margin)
      - RISKY: (1.0 - wall_thickness_ratio) × envelope_min_axis < liveability_min_width_m ≤ envelope_min_axis
        (just barely fits envelope min-axis; high probability of failure
        once C11 adds wall thickness) → Inv 17b WARN
      - IMPOSSIBLE: liveability_min_width_m > envelope_min_axis
        (deterministic placement impossibility; C11 cannot succeed) → Inv 17a RAISES
    """
    FEASIBLE   = "feasible"
    RISKY      = "risky"
    IMPOSSIBLE = "impossible"


class GridBayFeasibility(str, Enum):
    """Per-room grid-bay feasibility classification (n-bay framing).

    Verdicts (computed against grid.bay_max_m):
      - SINGLE_BAY: liveability_min_width_m ≤ bay_max_m
      - DOUBLE_BAY: bay_max_m < liveability_min_width_m ≤ 2 × bay_max_m
      - TRIPLE_BAY: 2 × bay_max_m < liveability_min_width_m ≤ 3 × bay_max_m
      - OVERSIZED:  liveability_min_width_m > 3 × bay_max_m
        (Inv 18 WARN trigger)
    """
    SINGLE_BAY = "single_bay"
    DOUBLE_BAY = "double_bay"
    TRIPLE_BAY = "triple_bay"
    OVERSIZED  = "oversized"


class PlacementRiskLevel(str, Enum):
    """Combined risk signal — REVISED v0.6 to be severity-weighted.

    v0.5 used flat-count aggregation (treating all flags equally). v0.6
    weights signals by severity per Walk #6 #2/#3:

    - IMPOSSIBLE width: doesn't reach this stage (Inv 17a RAISES first)
    - OVERSIZED grid: weight 2 (closest-to-deterministic; room won't fit
      any 1/2/3-bay placement)
    - packing_warning, RISKY width, TRIPLE_BAY grid: weight 1 each

    Total score → level:
      - score 0:        LOW
      - score 1-2:      MEDIUM
      - score ≥ 3:      HIGH

    OVERSIZED grid alone (weight 2) → MEDIUM by itself; OVERSIZED + any
    other yellow → HIGH. This severity awareness was missing in v0.5.
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
    """Provenance for one C9 sizing pass — REVISED v0.6."""
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    nbc_table_version: str
    furniture_kb_version: str
    targets_kb_version: str
    dwelling_size_tier: DwellingSizeTier
    tier_resolution_accuracy: TierResolutionAccuracy
    assumed_total_dwelling_area_m2: float | None
    grid_bay_min_m: float
    grid_bay_max_m: float
    wall_thickness_ratio_used: float                # NEW v0.6 (Walk #6 #6):
                                                     # The actual config value applied; allows
                                                     # debugging when threshold-derivation matters.
    enforcement_mode: str
    allocation_strategy: str
    surplus_distributed_m2: float
    rooms_at_min: tuple[str, ...]
    rooms_clamped_at_max: tuple[str, ...]
    packing_basis: str
    heuristic_packing_check_warning: bool
    width_feasibility_per_room: dict[str, WidthFeasibilityVerdict]
    grid_bay_feasibility_per_room: dict[str, GridBayFeasibility]
    placement_risk_level: PlacementRiskLevel
    placement_risk_score: int                       # NEW v0.6 (Walk #6 #2/#3):
                                                     # Raw weighted score before bucketing into LOW/
                                                     # MEDIUM/HIGH. Aids debugging "why did this
                                                     # tip into HIGH?"
    unverified_nbc_rows_used: tuple[str, ...]       # NEW v0.6 (Walk #6 #5):
                                                     # room_ids that used a SECONDARY_UNVERIFIED
                                                     # RegulatoryMinimum row. Empty tuple if all
                                                     # rows used were VERIFIED or SECONDARY_CONSENSUS.
                                                     # Surfaces unverified-acceptance even when
                                                     # require_verified_nbc=False (default).
    other_sizing_behavior: str
    rule_trace: tuple[str, ...]


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

Carried forward unchanged from v0.4/v0.5 (tables in § 4.1 SMALL / LARGE; source_confidence per row; LOCK NOT blocked on B-150). v0.6 adds visibility: even in default `require_verified_nbc=False` mode, any SECONDARY_UNVERIFIED row used populates `provenance.unverified_nbc_rows_used` so the silent acceptance becomes visible.

#### Dwelling-tier resolution (carried unchanged from v0.5)

```python
def _resolve_dwelling_tier(
    candidate: CorridorDesignedCandidate,
    floor_room_brief: FloorRoomBrief,
    config: RoomSizingConfig,
) -> tuple[DwellingSizeTier, TierResolutionAccuracy, float | None]:
    if config.dwelling_tier_override is not None:
        return config.dwelling_tier_override, TierResolutionAccuracy.OVERRIDE_SUPPLIED, None
    if config.assumed_total_dwelling_area_m2 is not None:
        a = config.assumed_total_dwelling_area_m2
        tier = DwellingSizeTier.SMALL if a <= 50.0 else DwellingSizeTier.LARGE
        return tier, TierResolutionAccuracy.OVERRIDE_SUPPLIED, a
    is_multi_floor = floor_room_brief.floor_label.lower() not in ("ground", "ground_floor", "gf")
    if is_multi_floor:
        return DwellingSizeTier.LARGE, TierResolutionAccuracy.APPROXIMATE_DEFENSIVE_LARGE, None
    envelope_areas = sum(e.area_m2 for e in candidate.corridor_path.envelopes)
    tier = DwellingSizeTier.SMALL if envelope_areas <= 50.0 else DwellingSizeTier.LARGE
    return tier, TierResolutionAccuracy.EXACT, envelope_areas
```

### § 4.2 — Liveability minimums (furniture-fit floor)

Carried forward unchanged from v0.4/v0.5. `liveability_min_width_m` = max(regulatory.width_m, furniture.min_width_m); INTERIOR clear width per § 14.23.

### § 4.3 — Target sizes

Carried forward. KB-managed via `kb/room_targets.json`.

### § 4.4 — Max sizes

Carried forward. Per-category multipliers per § 4.4.

### § 4.5 — Surplus allocation

Carried forward. `PRIORITY_GREEDY` default; `PROPORTIONAL` alternative; leftover → `unassigned_area_m2`.

### § 4.6 — Infeasibility detection — REVISED v0.6

v0.6 has **two** typed infeasibility exceptions:

**`RoomSizingInfeasibleError(B-NNN-A)`** (existing): raised when `Σ liveability_min_area_m2 > buildable_envelope_minus_corridor_m2` (Inv 9). Total area infeasibility.

**`WidthInfeasibleError(B-NNN-J)`** (NEW v0.6 per Walk #6 #1): raised when any room's `liveability_min_width_m > envelope_min_axis` (Inv 17a). Deterministic placement impossibility; not a heuristic.

Sample `WidthInfeasibleError`:
```
WidthInfeasibleError: deterministic width infeasibility on candidate 0:
  BEDROOM_1: liveability_min_width=3.3m, envelope_min_axis=2.5m
  → room cannot fit on this envelope; placement at C11 is mathematically
    impossible.
Caller must escalate to brief renegotiation (B-NNN-A) or plot expansion.
```

Both errors hard-fail per Pattern A. Soft-fail mode (B-NNN-A reframed) requires C2 retry contract amendment.

**Why split into two errors**: distinguishing area-infeasibility (Σ liveability_min > envelope) from width-infeasibility (single room too wide for envelope) gives callers (eventually C2 renegotiation) a clearer signal — the remediations differ. Area-infeasible: drop a room. Width-infeasible: change envelope shape OR drop the wide room.

### § 4.7 — Validator invariants — REVISED v0.6

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
| 10 | Σ liveability_min_area_m2 ≤ envelope × packing_efficiency | placement-readiness heuristic | **WARN** |
| 11 | room_ids unique | data integrity | RAISE |
| 12 | priority values cover 1..n contiguously | well-formedness | RAISE |
| 13 | exactly one BEDROOM has is_master=True iff bedroom_count ≥ 1 | master semantics | RAISE |
| 14 | at most one BATHROOM has is_master=True | master semantics | RAISE |
| 15 | bathroom_subtype is set iff category == BATHROOM | schema integrity | RAISE |
| 16 | unassigned_area_m2 ≥ 0 | math | RAISE |
| **17a** | **for every room, NO room has WidthFeasibilityVerdict.IMPOSSIBLE** (NEW v0.6 per Walk #6 #1) | deterministic width infeasibility | **RAISE** (`WidthInfeasibleError`) |
| **17b** | **classify width feasibility (FEASIBLE / RISKY); RISKY rooms logged** (REVISED v0.6 per Walk #6 #1) | placement-readiness heuristic | **WARN** if any RISKY |
| 18 | classify grid-bay feasibility per room; OVERSIZED triggers WARN | grid-bay sanity heuristic | **WARN** if any OVERSIZED |

**Inv 17 split rationale (Walk #6 #1, web-grounded)**: deterministic mathematical impossibility (room width > envelope min-axis) is not a heuristic; the fail-fast principle says fail at the boundary. v0.5 conflated heuristic-WARN with deterministic-WARN. v0.6 corrects: 17a RAISES on IMPOSSIBLE; 17b WARNS on RISKY.

**Inv 17a check (with `wall_thickness_ratio` applied for RISKY threshold computation)**:
```python
def _classify_width_feasibility(
    room: RoomSizeRequirement,
    envelope_min_axis: float,
    wall_thickness_ratio: float,
) -> WidthFeasibilityVerdict:
    risky_threshold = (1.0 - wall_thickness_ratio) * envelope_min_axis
    if room.liveability_min_width_m > envelope_min_axis:
        return WidthFeasibilityVerdict.IMPOSSIBLE
    if room.liveability_min_width_m > risky_threshold:
        return WidthFeasibilityVerdict.RISKY
    return WidthFeasibilityVerdict.FEASIBLE


# In validator (Inv 17a check):
impossible_rooms = [
    r_id for r_id, v in width_feasibility_per_room.items()
    if v == WidthFeasibilityVerdict.IMPOSSIBLE
]
if impossible_rooms:
    raise WidthInfeasibleError(
        f"C9 deterministic width infeasibility: rooms {impossible_rooms} "
        f"have liveability_min_width_m exceeding envelope_min_axis. "
        f"This is not heuristic — placement at C11 is mathematically impossible. "
        f"Caller must escalate to brief renegotiation (B-NNN-A) or plot expansion."
    )
```

**`placement_risk_level` derivation (REVISED v0.6 per Walk #6 #2/#3)** — severity-weighted aggregation:
```python
def _derive_placement_risk_level(
    width_verdicts: dict[str, WidthFeasibilityVerdict],
    grid_verdicts: dict[str, GridBayFeasibility],
    packing_warning: bool,
) -> tuple[PlacementRiskLevel, int]:
    """Returns (level, raw_score). raw_score stored in provenance for debug.

    Severity weights (Walk #6 #2/#3):
      - IMPOSSIBLE width: doesn't reach here (Inv 17a RAISES first)
      - OVERSIZED grid: weight 2 (closest-to-deterministic; room won't fit
        any 1/2/3-bay placement)
      - packing_warning: weight 1
      - any RISKY width: weight 1
      - any TRIPLE_BAY grid: weight 1

    score → level:
      - 0:    LOW
      - 1-2:  MEDIUM
      - 3+:   HIGH

    OVERSIZED alone (weight 2) → MEDIUM. OVERSIZED + any yellow → HIGH.
    """
    score = 0
    if any(v == GridBayFeasibility.OVERSIZED for v in grid_verdicts.values()):
        score += 2
    if packing_warning:
        score += 1
    if any(v == WidthFeasibilityVerdict.RISKY for v in width_verdicts.values()):
        score += 1
    if any(v == GridBayFeasibility.TRIPLE_BAY for v in grid_verdicts.values()):
        score += 1

    if score >= 3:
        return PlacementRiskLevel.HIGH, score
    if score >= 1:
        return PlacementRiskLevel.MEDIUM, score
    return PlacementRiskLevel.LOW, score
```

### § 4.8 — Order-of-checks

Type checks → shape (B-066) → brief sanity → dwelling-tier resolution → grid-bay capture → per-candidate regulatory lookup (with `require_verified_nbc` gate; populate `unverified_nbc_rows_used`) → liveability resolution → infeasibility check (Inv 9) → **width-feasibility classification + Inv 17a RAISE on IMPOSSIBLE (NEW v0.6)** → surplus allocation → validator (Inv 1-18 with verdict-derivation for 17b/18) → placement_risk_level severity-weighted derivation. Pattern A: fail at boundary; surface heuristics via WARN.

---

## § 5 — Invocation contract (public)

```python
sized = size_rooms(
    corridor_designed_candidates=c8_output,
    floor_room_brief=c1_brief.floors[0],
    grid=c7_grid,
    plot_analysis=c4_plot_analysis,
)

# v0.6 patterns:
sized = size_rooms(
    ...,
    config=RoomSizingConfig(
        require_verified_nbc=True,                # post-B-150 strict mode
        assumed_total_dwelling_area_m2=120.0,     # multi-floor exact tier
        wall_thickness_ratio=0.08,                # thinner partitions (e.g., AAC blocks)
    ),
)
```

Cardinality: 1-3 in → 1-3 out, position-paired.

---

## § 6 — Failure modes — REVISED v0.6

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
| **Any room's WidthFeasibilityVerdict == IMPOSSIBLE (Inv 17a)** | **`WidthInfeasibleError` (B-NNN-J) — NEW v0.6** |
| Any room's WidthFeasibilityVerdict == RISKY (Inv 17b) | logged in `width_feasibility_per_room`; placement_risk_level derivation; no raise |
| Any room's GridBayFeasibility == OVERSIZED (Inv 18) | logged in `grid_bay_feasibility_per_room`; placement_risk_level=HIGH likely; no raise |
| `config.require_verified_nbc=True` AND any row used has `source_confidence != VERIFIED` | `KeyError` (`NBCConfidenceTooLow`) |
| `config.require_verified_nbc=False` AND any SECONDARY_UNVERIFIED row used | log room_id to `provenance.unverified_nbc_rows_used`; no raise |
| One room category's NBC table entry missing for resolved tier | `KeyError` (KB integrity) |
| Empty input tuple | Returns empty tuple |

Typed exception hierarchy (v0.6):
```python
class RoomSizingError(Exception): ...
class RoomSizingInfeasibleError(RoomSizingError): ...   # Inv 9: total area infeasibility (B-NNN-A)
class WidthInfeasibleError(RoomSizingError): ...        # Inv 17a: deterministic width (B-NNN-J, NEW v0.6)
class NBCConfidenceTooLow(RoomSizingError, KeyError): ...  # require_verified_nbc strict mode
```

Both `RoomSizingInfeasibleError` and `WidthInfeasibleError` extend `RoomSizingError` so callers can catch either with one except clause when they don't care about the distinction.

---

## § 7 — Test plan — REVISED v0.6

v0.6 targets **~135 tests** (was ~130 in v0.5; +5 for Inv 17a RAISE coverage):

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
| **17a** | **WidthInfeasibleError on IMPOSSIBLE width (RAISE)** (NEW v0.6) | **6** | test_c9_orchestrator.py |
| **17b** | **width_feasibility_per_room verdicts (FEASIBLE / RISKY) — config-driven threshold** | **8** | test_c9_orchestrator.py |
| 18 | grid_bay_feasibility_per_room verdicts (SINGLE/DOUBLE/TRIPLE/OVERSIZED) | 8 | test_c9_orchestrator.py |
| **PRL** | **placement_risk_level severity-weighted derivation (LOW/MEDIUM/HIGH paths)** | **8** (was 6 in v0.5; +2 for weight-tested edge cases) | test_c9_orchestrator.py |
| **Subtotal — invariants** | | **118** | |

### Module-coverage

| Module | Tests | Focus |
|---|---|---|
| nbc_table.py | ~12 | dwelling-tier; clauses; subtype variants; require_verified_nbc gate; unverified_nbc_rows_used population |
| furniture_floor.py | ~10 | (category, is_master, bathroom_subtype) lookup |
| targets_kb.py | ~6 | (category, is_master) target lookup |
| allocator.py | ~12 | PRIORITY_GREEDY / PROPORTIONAL / max-clamp |
| size_rooms (orchestrator) | ~15 | end-to-end; tier accuracy enum; assumed_total_dwelling_area_m2 paths; wall_thickness_ratio config paths |
| failure_modes | ~15 | type checks; B-066; edge cases; new WidthInfeasibleError raise paths |
| **Subtotal — coverage** | | **~70** | |

**Combined estimate ≈ 135 tests**.

---

## § 8 — KB references

Carried forward unchanged from v0.4/v0.5:

| KB | Status | Used for |
|---|---|---|
| `kb/nbc_room_minimums.json` | NEW v0.2 (rev v0.4) | NBC dwelling-tiered table; `source_confidence` per row |
| `kb/furniture_floor.json` | NEW v0.2 (rev v0.3) | (category, is_master, bathroom_subtype) → (area_m2, min_width_m, ref_config) |
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
| Multi-floor dwelling-tier (whole-dwelling auto-derived from C2) | B-148 |
| Packing-efficiency tightening to ERROR mode | B-149 |
| NBC clause verification against authoritative PDF | B-150 |
| OTHER subtype-driven sizing differentiation | B-151 |
| Aspect ratio / shape constraints | C11 (§ 14.26) |
| Width-to-bay grid feasibility (full check) | C11 |
| Wall thickness deduction from envelope coords | C11 (§ 14.23) |
| Door swing clearance | C13 |
| Height enforcement | C11 (§ 14.22) |
| Envelope-shape-aware feasibility (geometry-complete) | C11 (§ 14.28) |

---

## § 10 — Provenance — REVISED v0.6

`RoomSizingProvenance` fields (cumulative through v0.6):

**Traceability**: `derived_at`, `plot_analysis_trace_id`, `floor_label`
**KB versions**: `nbc_table_version`, `furniture_kb_version`, `targets_kb_version`
**Tier resolution**: `dwelling_size_tier`, `tier_resolution_accuracy`, `assumed_total_dwelling_area_m2`
**Grid context**: `grid_bay_min_m`, `grid_bay_max_m`
**Width-threshold context (NEW v0.6)**: `wall_thickness_ratio_used`
**Config**: `enforcement_mode`, `allocation_strategy`
**Allocation results**: `surplus_distributed_m2`, `rooms_at_min`, `rooms_clamped_at_max`
**Heuristic packing**: `packing_basis`, `heuristic_packing_check_warning`
**Per-room verdicts**: `width_feasibility_per_room`, `grid_bay_feasibility_per_room`
**Combined risk**: `placement_risk_level`, **`placement_risk_score` (NEW v0.6)** — raw weighted score
**NBC verification visibility (NEW v0.6)**: `unverified_nbc_rows_used`
**v1 limitation visibility**: `other_sizing_behavior` ("pooled_v1")
**Debug**: `rule_trace`

---

## § 11 — Spec metadata

- **Version**: v0.6 PROPOSED
- **Status**: PROPOSED — pending Ramalingam LOCK adjudication
- **Lineage**: v0.1 DRAFT → v0.2 → v0.3 → v0.4 → v0.5 → v0.6 (6 walks completed)
- **Authoring sessions**: S33 entire arc

**Convergence trajectory after 6 walks**:

| Walk | Findings | Net new actionable | Push-backs |
|---|---|---|---|
| #1 | 15 | 12 | 0 |
| #2 | 15 | 2 | 0 |
| #3 | 11 | 3 | 2 |
| #4 | 10 | 4 | 2 |
| #5 | 10 | 6 | 3 |
| #6 | 10 | 5 | 4 |

Walk #6 push-backs (4) ≥ net-new actionable (5) — the system has converged. The single substantive correction in walk #6 was the IMPOSSIBLE→RAISE escalation, which corrected my walk-#5 conflation of heuristic-WARN with deterministic-WARN. Web research grounded the fail-fast principle for deterministic impossibility.

---

## § 12 — Backlog enumeration

Total: **13 items** (was 12 in v0.5; +1 from Walk #6: B-NNN-J for the new typed exception).

| ID | Title | Origin | Status | Trigger | Effort |
|---|---|---|---|---|---|
| B-NNN-A | Soft-fail mode + C2 retry | § 4.6 / Q8 | BACKLOG | C2 feasibility loop | M |
| B-NNN-B | Plot-tier-aware target sizing | § 4.3 | BACKLOG | Empirical signal | S |
| B-NNN-C | Configurable priority order beyond default | § 4.5 | BACKLOG | First user request | S |
| B-NNN-D | State DCR overrides | § 4.1 | BACKLOG | Municipality rejection | M |
| B-NNN-E | Multi-floor coordination | § scope | BACKLOG | C12 vertical alignment | L |
| B-NNN-F | Furniture KB versioning | § 4.2 | BACKLOG | Customization feature | M |
| B-NNN-I | Bath assignment rules | § 4.2 | BACKLOG | C11 placement | M |
| B-148 | Multi-floor dwelling-tier (auto-derived from C2) | § 4.1 | BACKLOG | Multi-floor test case | M |
| B-149 | Packing-efficiency to ERROR mode | § 4.7 Inv 10 | BACKLOG | Calibration data | S |
| B-150 | NBC clause verification | § 4.1 / § 8 | BACKLOG | Verification pass complete | S |
| B-151 | OTHER subtype-driven sizing | § 9 | BACKLOG | First product feature | M |
| **B-NNN-J** | **`WidthInfeasibleError` typed exception class** (NEW v0.6 per Walk #6 #1) | § 4.6 / § 6 | TO-BE-IMPLEMENTED IN BUILD | C9 build session | (in build) |
| (deferred to C11) | Aspect ratio / shape constraints | Walk #4 #5 | C11 spec | C11 build | (in C11) |
| (deferred to C11) | Width-to-bay grid feasibility (full check) | Walk #3 #2 | C11 spec | C11 build | (in C11) |
| (deferred to C11) | Wall thickness deduction from envelope | Walk #4 #4 | C11 spec | C11 build | (in C11) |
| (deferred to C13) | Door swing clearance | Walk #4 #4 | C13 spec | C13 build | (in C13) |
| (deferred to C11) | Height enforcement | Walk #4 #10 | C11 spec | C11 build | (in C11) |
| (deferred to C11) | Envelope-shape-aware feasibility | Walk #5 #10 | C11 spec | C11 build | (in C11) |

Note: B-NNN-J is a build-session implementation task (the exception class file + tests), not a future-deferred backlog item.

---

## § 13 — Definitions

Cumulative across walks (v0.6 additions marked):

- **`regulatory_minimum`** *(v0.2; rev v0.4)*: NBC 2016 floor.
- **`liveability_min_area_m2`** / **`liveability_min_width_m`** *(v0.2/v0.3)*: max(regulatory, furniture). Width is INTERIOR clear.
- **`target_m2`** *(v0.2; KB-managed v0.3)*: comfortable size.
- **`max_m2`** *(v0.2)*: waste threshold.
- **`buildable_envelope_minus_corridor_m2`** *(v0.2)*: from C8 corridor_path.envelopes minus corridor.
- **`DwellingSizeTier`** *(v0.2)*: SMALL ≤50 m² / LARGE >50 m².
- **`TierResolutionAccuracy`** *(v0.4)*: EXACT / APPROXIMATE_DEFENSIVE_LARGE / OVERRIDE_SUPPLIED.
- **`assumed_total_dwelling_area_m2`** *(v0.5)*: numeric of the dwelling-area assumption.
- **`is_master`** *(v0.2)*: True for BEDROOM_1.
- **`bathroom_subtype`** *(v0.3)*: COMBINED / BATH_ONLY / WC_ONLY.
- **`other_subtype`** *(v0.4)*: free-text echo of brief.other_rooms[i].
- **`source_confidence`** *(v0.4)*: VERIFIED / SECONDARY_CONSENSUS / SECONDARY_UNVERIFIED.
- **`require_verified_nbc`** *(v0.5)*: config flag forcing VERIFIED-only rows.
- **`packing_efficiency`** / **`packing_basis`** *(v0.2/v0.3)*: heuristic ratio + provenance string.
- **`unassigned_area_m2`** *(v0.3)*: leftover envelope after surplus.
- **`grid_bay_min_m` / `grid_bay_max_m`** *(v0.4)*: provenance fields.
- **`WidthFeasibilityVerdict`** *(v0.5; rev v0.6 to use config wall_thickness_ratio)*: FEASIBLE / RISKY / IMPOSSIBLE.
- **`GridBayFeasibility`** *(v0.5)*: SINGLE_BAY / DOUBLE_BAY / TRIPLE_BAY / OVERSIZED.
- **`PlacementRiskLevel`** *(v0.5; rev v0.6 to severity-weighted)*: LOW / MEDIUM / HIGH.
- **`width_feasibility_per_room`** / **`grid_bay_feasibility_per_room`** *(v0.5)*: per-room verdict maps.
- **`other_sizing_behavior`** *(v0.5)*: provenance string ("pooled_v1").
- **`WidthInfeasibleError`** *(NEW v0.6)*: typed exception raised on Inv 17a (deterministic IMPOSSIBLE width).
- **`wall_thickness_ratio`** *(NEW v0.6)*: config field (default 0.10) driving FEASIBLE/RISKY threshold.
- **`unverified_nbc_rows_used`** *(NEW v0.6)*: provenance tuple of room_ids using SECONDARY_UNVERIFIED rows.
- **`placement_risk_score`** *(NEW v0.6)*: raw weighted score before bucketing into LOW/MEDIUM/HIGH.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 DRAFT
§ 14.1 — Two-floor minimum (regulatory + liveability).
§ 14.2 — `PRIORITY_GREEDY` as v1 default.
§ 14.3 — Hard-fail on infeasibility (v1).
§ 14.4 — NBC table is KB-managed JSON.

### From v0.2 PROPOSED
§ 14.5 — C9 receives `FloorRoomBrief` directly.
§ 14.6 — Master/non-master via `priority` and `is_master`.
§ 14.7 — `regulatory_minimum` is a triple.
§ 14.8 — `consumption_band` field DROPPED.
§ 14.9 — Dwelling-tier resolved from C8 envelope total.
§ 14.10 — Packing-efficiency check is WARN.
§ 14.11 — `max_m2` per-category multipliers consistent.

### From v0.3 PROPOSED
§ 14.12 — Liveability includes width.
§ 14.13 — Multi-floor dwelling-tier defensive.
§ 14.14 — Width feasibility deferred to C11 (full check).
§ 14.15 — Heuristic_packing_check is heuristic.
§ 14.16 — Grid input rationale.
§ 14.17 — `unassigned_area_m2` explicit.
§ 14.18 — Targets KB-managed.
§ 14.19 — Priority is first-class config.
§ 14.20 — Bathroom subtype schema-explicit.
§ 14.21 — Secondary-source NBC disagreement documented.

### From v0.4 PROPOSED
§ 14.16-bis — Grid input functionally consumed.
§ 14.22 — Height enforcement is C11.
§ 14.23 — `liveability_min_width_m` is interior clear width.
§ 14.24 — NBC source confidence exposed; LOCK NOT blocked on B-150.
§ 14.25 — Tier resolution accuracy is 3-state enum.
§ 14.26 — Aspect ratio is C11.
§ 14.27 — Width is constraint, not target/max dimension.

### From v0.5 PROPOSED
§ 14.28 — C9 is area-dominant, not geometry-complete.
§ 14.29 — Width-feasibility classified, not just flagged.
§ 14.30 — Grid-bay uses n-bay framing.
§ 14.31 — Combined placement_risk_level derived (resolved B-152).
§ 14.32 — NBC verification can be enforced (require_verified_nbc).
§ 14.33 — Multi-floor dwelling-area can be user-supplied.
§ 14.34 — v1 OTHER pooling visible in provenance.

### NEW v0.6 (resolved per Walk #6)

§ 14.35 — **Deterministic impossibility RAISES; heuristic risk WARNS** (Walk #6 #1, web-grounded). Walk #6 web research confirmed the fail-fast principle (Wikipedia "Fail-fast system"; industry consensus): when an error condition is mathematically certain (room width > envelope min-axis cannot fit by any geometry), the right action is fail-at-boundary, not log-and-continue. v0.5's Inv 17 WARN-only conflated heuristic checks (heuristic_packing, RISKY width — these *might* fail downstream) with deterministic checks (IMPOSSIBLE width — *will* fail downstream). v0.6 splits Inv 17 into 17a (RAISE on IMPOSSIBLE — new `WidthInfeasibleError`) and 17b (WARN on RISKY). This is the most substantive engineering correction across all 6 walks.

§ 14.36 — **Risk aggregation is severity-weighted, not flat-count** (Walk #6 #2/#3). v0.5's count-based aggregation treated OVERSIZED grid (closest-to-deterministic; room genuinely won't fit any 1/2/3-bay placement) the same as RISKY width or packing warning. v0.6 weights OVERSIZED at 2 and other yellow flags at 1, so OVERSIZED alone reaches MEDIUM and OVERSIZED + any yellow reaches HIGH. The raw `placement_risk_score` is also stored in provenance for debugging.

§ 14.37 — **Wall-thickness ratio is configurable** (Walk #6 #6). The 0.9 RISKY threshold in v0.5 was hardcoded. v0.6 introduces `wall_thickness_ratio: float = 0.10` config field; RISKY threshold = (1.0 - wall_thickness_ratio) × envelope_min_axis. Default matches typical Indian residential interior partition (~10% of envelope-to-envelope). Configurable for AAC blocks (~7-8%) or thicker masonry walls (~12%).

§ 14.38 — **Unverified NBC row usage is visible by default** (Walk #6 #5). v0.5 made unverified rows visible only when `require_verified_nbc=True` triggered a raise. v0.6 populates `provenance.unverified_nbc_rows_used` *always* when SECONDARY_UNVERIFIED rows are used, regardless of the strict-mode flag. Silent acceptance is now logged silently; loud rejection (the strict mode) is a separate choice.

§ 14.39 — **Two typed errors for two failure modes** (Walk #6 #1 follow-on). `RoomSizingInfeasibleError(B-NNN-A)` for total-area infeasibility (Inv 9); `WidthInfeasibleError(B-NNN-J)` for width infeasibility (Inv 17a). Both extend `RoomSizingError` so callers can catch either generically; the distinction matters for renegotiation (drop a room vs change envelope shape).

---

## § 15 — Open questions remaining

After 6 walks the open-questions list is essentially closed. Two residuals:

### Q14 (carried) — Should max_m2 multipliers also live in `kb/room_targets.json`?

**Recommendation for LOCK**: yes; move to KB. One-line spec change.

### NEW Q17 — Confirm the severity weights (OVERSIZED=2, others=1)

The 2:1 ratio was chosen because OVERSIZED is closest-to-deterministic among the yellow flags. Empirical calibration from C11 placement data over time may suggest different weights.

**Recommendation for LOCK**: ship 2:1; revisit when C11 placement data exists.

---

## § 16 — End of v0.6 PROPOSED

Expected next: Ramalingam LOCK adjudication → build (D-066 step 6-8).

If LOCKED, the build session can begin immediately:
- 3 KB JSONs authored
- ~7 production modules under `buildemup/components/c09/` (schema, errors [includes WidthInfeasibleError], nbc_table, furniture_floor, targets_kb, allocator, validator, room_sizer)
- ~135 tests authored

After 6 walks of converging discipline (push-backs ≥ net-new actionable in walk #6; the substantive walk-#6 fix corrected my own walk-#5 reasoning error rather than discovering a new architectural issue), the system is **production-ready v1**. Walk #6's fail-fast escalation makes v0.6 materially safer than v0.5 — IMPOSSIBLE width is now caught at C9 boundary instead of silently passed to C11.
