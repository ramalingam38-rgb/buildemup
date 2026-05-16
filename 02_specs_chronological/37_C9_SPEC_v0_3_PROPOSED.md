# BuildemUp — C9 Room Sizer — SPEC v0.3 PROPOSED

**Status**: PROPOSED. PENDING Ramalingam LOCK adjudication. Per Rule 8, LOCK authority belongs to Ramalingam alone; this document represents the v0.3 candidate after walks #1 (Claude self-critique), #2 (Ramalingam review on v0.1), and #3 (Ramalingam review on v0.2).
**Component**: C9 of canonical 17-component v3 list (Track 3). Position 9.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C8 (`CorridorDesignedCandidate`) + C7 (`Grid`) + C4 (`PlotAnalysis`) + C1's `FloorRoomBrief`. Produces input for C10 (Bathroom + Wet-Zone Stack Planner) and C11 (Room Placement).
**Authoring sessions**: S33 v0.1 DRAFT + walks #1, #2, #3 + v0.3 PROPOSED.
**Predecessor**: v0.2 PROPOSED (729 lines).

---

## § 0 — Why this spec, why now

After C8 SHIP at S32, the pipeline produces oriented topology candidates with refined zone bands (C6), structural grid (C7), and corridor geometry (C8). Downstream consumers (C10 wet-zone planner, C11 placement) need *room footprints with sizes assigned* — not just band envelopes. C9 sits between "the bands and corridor are designed" and "specific rooms have specific sizes."

C9's job: given the brief's room composition (`FloorRoomBrief.bedroom_count`, `bathroom_count`, `has_kitchen`, etc.), the band envelopes from C8's `CorridorPath.envelopes` (with the corridor area carved out), the structural grid bays, and the plot analysis, produce a `RoomSizeTable` — for each room, **(regulatory floor for area + width + height, liveability floor for area + width, target, max)** that downstream placement components can satisfy.

C9 does NOT place rooms (that's C11). C9 does NOT generate furniture layouts (that's C14 furniture-fit metric). C9 does NOT decide adjacencies (that's C5/C11). C9 does NOT assign rooms to zone bands (that's C11 placement). C9 does NOT score the resulting sizes (that's C14).

**The architectural distinction the project has been making**: NBC 2016 minimum is the **regulatory floor**; furniture-fit minimum is the **liveability floor**. v1 C9 produces both — including width, not just area, after Walk #3 surfaced that area-only liveability checking was a critical gap (a 2.4m-wide bedroom passes NBC area but cannot fit standard bed + clearance furniture).

**v0.3 lineage delta from v0.2 PROPOSED** (11 spec edits per Walk #3):

| # | Edit | Source | § affected |
|---|---|---|---|
| 1 | Dwelling-tier multi-floor: explicit single-floor assumption + warning + defensive LARGE-pick | Walk #3 #1 | § 4.1, § 14 |
| 2 | Width feasibility: explicit deferral to C11 with documented rationale | Walk #3 #2 | § 4.7, § 14 |
| 3 | Packing efficiency renamed "heuristic_packing_check"; provenance carries `packing_basis` tag | Walk #3 #3 | § 4.7, § 10 |
| 4 | **Liveability width tracking** — new schema field, new invariant (CRITICAL) | Walk #3 #4 | § 3, § 4.2, § 4.7 |
| 5 | Grid-availability rationale documented; sizing/placement separation explicit | Walk #3 #5 | § 14 |
| 6 | `bathroom_subtype: BathroomSubtype` added to schema (default COMBINED) | Walk #3 #6 | § 3 |
| 7 | `unassigned_area_m2` field on RoomSizeTable | Walk #3 #7 | § 3 |
| 8 | Strengthen § 4.5 priority-as-config wording | Walk #3 #8 | § 4.5 |
| 9 | OTHER subtyping filed as B-151; v1 documents the pooling | Walk #3 #9 | § 9, § 12 |
| 10 | Targets moved to `kb/room_targets.json` | Walk #3 #11 | § 4.3, § 8 |
| 11 | Document secondary-source NBC disagreement; strengthens B-150 | Walk #3 web research | § 4.1, § 8 |

---

## § 1 — Purpose

Given a C8-corridor-designed candidate, the brief's room composition, the structural grid bays, and the plot analysis, produce a **`RoomSizeTable`** — for each requested room (bedroom × N, bathroom × M, optional kitchen, optional living, optional pooja, optional utility, plus brief-defined `other_rooms`):
- regulatory floor (area, width, height) per NBC 2016 dwelling tier
- liveability minimum (**area AND width**, per Walk #3 #4)
- target size
- max size

The total of all liveability-min areas must fit within the buildable envelope minus the corridor area (Inv 9). A *heuristic_packing_check* warning fires if the total approaches the envelope without typical wall + clearance slack (Inv 10 WARN, per Walk #3 #3). If the area infeasibility test fails, raise a typed `RoomSizingInfeasibleError(B-NNN-A)`.

Cardinality preserved: 1-3 C8 candidates → 1-3 C9 candidates, position-paired.

**Out of scope for C9** (intentionally not addressed):
- Room placement (XY positioning) — C11
- Adjacency / connectivity — C5 selected, C11 enforces
- Zone band assignment for rooms — C11 placement
- Width-to-bay grid feasibility — C11 placement (per Walk #3 #2)
- Furniture layout — C14 furniture-fit metric (consumes C9's sizes as input)
- Door placement, swing direction — C13
- Wet-wall back-to-back stacking — C10
- Vertical alignment across floors — C12
- Cost computation — C14 cost metric

---

## § 2 — Input contract

```python
def size_rooms(
    corridor_designed_candidates: tuple[CorridorDesignedCandidate, ...],   # 1-3 from C8
    floor_room_brief: FloorRoomBrief,                                       # from C1
    grid: Grid,                                                              # from C7  (v0.2 fix: was StructuralGrid)
    plot_analysis: PlotAnalysis,                                            # from C4
    *,
    config: RoomSizingConfig | None = None,                                 # tunables; default OK
) -> tuple[RoomSizedCandidate, ...]:
```

`RoomSizedCandidate` = `CorridorDesignedCandidate` + `room_size_table: RoomSizeTable` + `provenance: RoomSizingProvenance` (extends position-paired chain).

`RoomSizingConfig` carries per-call tunables: enforcement mode (`STRICT` / `WARN`), Neufert/Ching multipliers, allocation strategy (`PRIORITY_GREEDY` / `PROPORTIONAL`), `packing_efficiency` (default 0.75), `dwelling_tier_override` (None = derived from C8), **`priority_override: tuple[RoomCategory, ...] | None = None`** (per Walk #3 #8 — first-class config rather than buried option). Defaults baked into the dataclass mean callers can omit it entirely.

**FloorRoomBrief is passed directly, not threaded onto `CorridorDesignedCandidate`** (resolved Walk #1 Q1 / Walk #2 #12). Cardinal pattern: each component explicitly receives the upstream artifacts it consumes.

**Why `Grid` is taken even though sizing doesn't directly use it** (Walk #3 #5 / § 14.12): Grid is consumed for (a) eventual dwelling-tier resolution refinement (B-148), (b) trace correlation in provenance (when C7 grid_trace_id lands per `B-NNN-grid-trace`), and (c) future grid-aware sizing options behind config flags. Sizing-as-a-function-of-grid-bays is intentionally NOT v1 behavior; that's placement-shape decision territory and belongs to C11.

---

## § 3 — Output schema — REVISED v0.3

```python
class RoomCategory(str, Enum):
    """The 6 v1 room categories. Mirrors C6's FunctionRole values."""
    BEDROOM    = "bedroom"
    BATHROOM   = "bathroom"
    LIVING     = "living"
    KITCHEN    = "kitchen"
    POOJA      = "pooja"
    UTILITY    = "utility"
    OTHER      = "other"


class DwellingSizeTier(str, Enum):
    """NBC 2016 dwelling-size tiers per Part 3 Clauses 12.1-12.4."""
    SMALL = "small"   # dwelling ≤ 50 m²
    LARGE = "large"   # dwelling > 50 m²


class BathroomSubtype(str, Enum):
    """NEW v0.3 (Walk #3 #6) — bathroom configuration variants.

    Indian residential default is COMBINED (bath+WC in one room).
    Some briefs (luxury or traditional) want separate bath and WC.

    Field is on RoomSizeRequirement when category=BATHROOM. Drives
    NBC table lookup via (category, subtype, dwelling_tier).
    """
    COMBINED = "combined"  # bath + WC together (v1 default; typical Indian residential)
    BATH_ONLY = "bath_only"  # bath without WC
    WC_ONLY = "wc_only"      # WC without bath


@dataclass(frozen=True)
class RegulatoryMinimum:
    """The regulatory floor for a single room (NBC 2016, dwelling-tiered).

    Per Walk #1 Finding #11 / Walk #2 Finding #2: NBC 2016 mandates ALL
    THREE of area, width, and height. Plans meeting area but failing width
    are non-compliant. Schema must carry all three.
    """
    area_m2: float                  # NBC minimum floor area
    width_m: float                  # NBC minimum width (the shorter side)
    height_m: float                 # NBC minimum ceiling height
    nbc_clause: str                 # "NBC 2016 Part 3 Clause 12.2.1" etc.
                                     # Or "v0.3 unverified clause" when source is uncertain


@dataclass(frozen=True)
class RoomSizeRequirement:
    """Per-room sizing requirement.

    For each room R:
      - regulatory_minimum: NBC 2016 floor (area + width + height)
      - liveability_min_area_m2 + liveability_min_width_m: NEW v0.3 — both
        derived as max(regulatory, furniture); v0.2's scalar was incomplete
        per Walk #3 Finding #4
      - target_m2: comfortable size for typical Indian use
      - max_m2: above which area is wasted

    Invariants (asserted at construction):
      - 0 < regulatory_minimum.area_m2 ≤ liveability_min_area_m2 ≤ target_m2 ≤ max_m2
      - regulatory_minimum.width_m ≤ liveability_min_width_m
      - is_master is True only on BEDROOM_1 (and BATHROOM_1 if convention applies)
    """
    room_id: str                                    # e.g. "BEDROOM_1", "BATHROOM_2", "KITCHEN"
    category: RoomCategory                          # enum
    regulatory_minimum: RegulatoryMinimum           # NBC triple (area + width + height)
    liveability_min_area_m2: float                  # max(regulatory.area_m2, furniture.area_m2)
    liveability_min_width_m: float                  # NEW v0.3 (Walk #3 #4 CRITICAL):
                                                     # max(regulatory.width_m, furniture.min_width_m)
                                                     # Closes the "9.5 m² @ 2.4m wide passes area
                                                     # but can't fit furniture" gap.
    target_m2: float                                # Neufert/Ching comfortable
    max_m2: float                                   # waste threshold
    priority: int                                   # 1 = highest, used for surplus allocation
    is_master: bool = False                         # NEW v0.2 (Walk #1 #8 / Walk #2 #4)
    bathroom_subtype: BathroomSubtype | None = None # NEW v0.3 (Walk #3 #6):
                                                     # only set when category == BATHROOM.
                                                     # Default COMBINED for category=BATHROOM;
                                                     # None for non-bathroom rooms.


@dataclass(frozen=True)
class RoomSizeTable:
    """The complete sizing for one C8 candidate's floor.

    Invariants (asserted at construction):
      - rooms is non-empty
      - room_ids unique
      - Σ liveability_min_area_m2 ≤ buildable_envelope_minus_corridor_m2 (Inv 9)
      - Σ liveability_min_area_m2 ≤ envelope × packing_efficiency (Inv 10 WARN)
      - Σ target_m2 may exceed envelope (surplus-allocation absorbs slack)
      - every category counts match brief
      - exactly one BEDROOM has is_master=True iff bedroom_count ≥ 1
    """
    rooms: tuple[RoomSizeRequirement, ...]
    buildable_envelope_minus_corridor_m2: float     # available area
    dwelling_size_tier: DwellingSizeTier            # which NBC tier was used
    total_liveability_min_area_m2: float            # Σ liveability_min_area
    total_target_m2: float                          # Σ target
    surplus_for_distribution_m2: float              # envelope − Σ liveability_min
    unassigned_area_m2: float                       # NEW v0.3 (Walk #3 #7):
                                                     # leftover envelope after surplus allocation —
                                                     # explicit field replaces v0.2's narrative
                                                     # "stays unassigned". Downstream consumers
                                                     # (C11) can decide if it becomes balcony,
                                                     # courtyard expansion, or void.
    packing_efficiency_used: float                  # which packing factor was applied
    floor_label: str                                # NEW v0.3 (Q12 from v0.2):
                                                     # propagated from FloorRoomBrief. Multi-floor
                                                     # consumers can identify which floor without
                                                     # unpacking provenance.


@dataclass(frozen=True)
class RoomSizingProvenance:
    """Provenance for one C9 sizing pass."""
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str                                # propagated from FloorRoomBrief
    nbc_table_version: str
    furniture_kb_version: str
    targets_kb_version: str                         # NEW v0.3 (Walk #3 #11):
                                                     # kb/room_targets.json now KB-managed
    dwelling_size_tier: DwellingSizeTier            # tier that drove regulatory lookup
    multi_floor_tier_warning: bool                  # NEW v0.3 (Walk #3 #1):
                                                     # True if C9 ran with brief.floor_label != "Ground"
                                                     # AND no whole-dwelling-area threading available
                                                     # (defensive LARGE-pick happened)
    enforcement_mode: str                           # STRICT | WARN
    allocation_strategy: str                        # PRIORITY_GREEDY | PROPORTIONAL
    surplus_distributed_m2: float                   # post-allocation
    rooms_at_min: tuple[str, ...]
    rooms_clamped_at_max: tuple[str, ...]
    packing_basis: str                              # NEW v0.3 (Walk #3 #3):
                                                     # "heuristic_v1_static_0.75" until B-149 lifts
                                                     # to calibrated. Makes clear this is a heuristic,
                                                     # not a geometric guarantee.
    heuristic_packing_check_warning: bool           # RENAMED v0.3 from packing_efficiency_warning
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

### § 4.1 — Regulatory minimums (NBC 2016 KB) — REVISED v0.3

**Important caveat (Walk #3 web research)**: secondary sources for NBC 2016 numbers **disagree among themselves**. The slideshare bye-laws table (S33 walk #1 source) cites bedroom 7.5/9.5 m² (dwelling-tiered); InfraLens cites bedroom 6.5 m² flat. v1 ships the **slideshare bye-laws table values** because they are tier-aware (matching NBC 2016 Part 3 Clauses 12.1-12.4 structure) and consistent with the Wadhwa NBC summary. v0.3 § 8 documents this disagreement; **B-150 is the authoritative-NBC-PDF verification pass that resolves it**.

NBC 2016 Part 3 numbers are **dwelling-tiered**: smaller dwellings have looser numerics for habitable rooms.

#### Dwelling tier: SMALL (dwelling ≤ 50 m²)

| Category | NBC area m² | NBC width m | NBC height m | NBC clause |
|---|---|---|---|---|
| BEDROOM (habitable, smaller-of-2) | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.2.2 |
| BEDROOM (habitable, single-room dwelling) | 9.5 | 2.4 | 2.75 | NBC 2016 Part 3 Clause 12.2.1 |
| LIVING (habitable) | 7.5 / 9.5 | 2.1 / 2.4 | 2.75 | same |
| KITCHEN (separate) | 3.3 | 1.8 | 2.75 | NBC 2016 Part 3 Clause 12.3.1 |
| KITCHEN-cum-DINING | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.3.2 |
| BATHROOM, COMBINED Bath+WC ★ | 1.8 | 1.0 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| BATHROOM, BATH_ONLY | 1.2 | 1.0 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| BATHROOM, WC_ONLY | 1.0 | 0.9 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| POOJA | (not habitable; no NBC floor) | — | 2.1 | (none) |
| UTILITY (storeroom) | 3.2 | (no width minimum cited) | 2.2 | NBC 2016 Part 3 (clause v0.3 unverified; B-150) |

★ = v1 default for "BATHROOM" category.

#### Dwelling tier: LARGE (dwelling > 50 m²)

| Category | NBC area m² | NBC width m | NBC height m | NBC clause |
|---|---|---|---|---|
| BEDROOM (habitable) | 9.5 | 2.4 | 2.75 | NBC 2016 Part 3 Clause 12.1.1 |
| LIVING (habitable) | 9.5 | 2.4 | 2.75 | same |
| KITCHEN (separate) | 4.5 | 1.8 | 2.75 | NBC 2016 Part 3 Clause 12.3.1 |
| KITCHEN-cum-DINING | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.3.2 |
| BATHROOM, COMBINED Bath+WC ★ | 2.8 | 1.2 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| BATHROOM, BATH_ONLY | 1.8 | 1.2 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| BATHROOM, WC_ONLY | 1.2 | 0.9 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| POOJA | (not habitable; no NBC floor) | — | 2.1 | (none) |
| UTILITY (storeroom) | 3.2 | (no width minimum cited) | 2.2 | NBC 2016 Part 3 (clause v0.3 unverified; B-150) |

★ = v1 default for "BATHROOM" category.

#### Dwelling-tier resolution (REVISED v0.3 per Walk #3 #1)

C9 derives the dwelling tier defensively:

```python
def _resolve_dwelling_tier(
    candidate: CorridorDesignedCandidate,
    floor_room_brief: FloorRoomBrief,
    config: RoomSizingConfig,
) -> tuple[DwellingSizeTier, bool]:
    """Returns (tier, multi_floor_warning).

    v1 explicitly assumes single-floor briefs (per-floor area = whole-dwelling
    area, so tier resolution is exact).

    For multi-floor briefs (where brief.floor_label is not "Ground" or where
    the orchestrator has indicated multi-floor context):
      - C9 picks LARGE defensively (higher tier; over-spec on regulatory
        minimum is harmless; under-spec = NBC violation)
      - sets multi_floor_tier_warning=True in provenance
      - logs a warning to rule_trace

    B-148 lifts this when C2 threads `total_dwelling_area_m2`.
    """
    if config.dwelling_tier_override is not None:
        return config.dwelling_tier_override, False

    # Detect multi-floor context (heuristic for v1)
    is_multi_floor = floor_room_brief.floor_label.lower() not in ("ground", "ground_floor", "gf")

    if is_multi_floor:
        # Defensive LARGE-pick to avoid under-spec
        return DwellingSizeTier.LARGE, True

    envelope_areas = sum(e.area_m2 for e in candidate.corridor_path.envelopes)
    tier = DwellingSizeTier.SMALL if envelope_areas <= 50.0 else DwellingSizeTier.LARGE
    return tier, False
```

**Rationale (Walk #3 #1)**: NBC's 50 m² threshold refers to the *whole dwelling unit* across all floors. v0.2 used per-floor-area as silent proxy; v0.3 makes the assumption explicit and *defensive*: when in doubt (multi-floor context), pick LARGE so we never under-spec. This honors Pattern A (surface the assumption rather than hide it) while preserving Pattern E avoidance (don't add complexity to fix what should be threaded from upstream).

These values live in `kb/nbc_room_minimums.json`. Versioned via `nbc_table_version`.

### § 4.2 — Liveability minimums (furniture-fit floor) — REVISED v0.3 CRITICAL

**Walk #3 Finding #4 was the strongest finding of the walk**: v0.2 area-only liveability check missed that NBC-area-passing rooms can fail to fit furniture due to width.

For each `(category, is_master)` tuple, the furniture KB now carries **both area and minimum width**:

| Category | is_master | Furniture area m² | Furniture min_width_m | Reference configuration |
|---|---|---|---|---|
| BEDROOM | False | 9.3 (~100 sqft) | 3.0 | Single bed 0.9 × 2.0 + study 1.2 × 0.6 + wardrobe 1.2 × 0.6 + 0.75 m clearance |
| BEDROOM | True (BEDROOM_1) | 13.0 (~140 sqft) | 3.3 | Queen 1.5 × 2.0 + 2 side tables + wardrobe + 0.9 m clearance |
| LIVING | False | 16.7 (~180 sqft) | 3.6 | 3-seat sofa + 2 chairs + coffee table + circulation |
| KITCHEN | False | 7.9 (~85 sqft) | 2.4 | L-counter 3.0 m run + fridge + 1.2 m work aisle |
| BATHROOM, COMBINED | False | 2.8 (~30 sqft) | 1.2 | Shower 0.9 × 0.9 + WC + sink + 0.6 m clearance |
| BATHROOM, COMBINED | True (BATHROOM_1) | 4.0 (~43 sqft) | 1.5 | + tub-or-larger-shower + double sink |
| BATHROOM, BATH_ONLY | False | 2.0 (~22 sqft) | 1.0 | Shower 0.9 × 0.9 + sink + 0.4 m clearance |
| BATHROOM, WC_ONLY | False | 1.5 (~16 sqft) | 0.9 | WC + small sink + 0.5 m clearance |
| POOJA | False | 2.8 (~30 sqft) | 1.2 | Altar 0.6 × 0.9 + seated prayer + storage cabinet |
| UTILITY | False | 2.8 (~30 sqft) | 1.2 | Washing machine + sink + storage |

```python
liveability_min_area_m2 = max(regulatory.area_m2, furniture.area_m2)
liveability_min_width_m = max(regulatory.width_m, furniture.min_width_m)
```

**Worked examples (LARGE tier)**:
- BEDROOM (typical): liveability area = max(9.5, 9.3) = 9.5; liveability width = max(2.4, 3.0) = **3.0** (furniture wins)
- BEDROOM (master): liveability area = max(9.5, 13.0) = 13.0; liveability width = max(2.4, 3.3) = **3.3** (furniture wins)
- LIVING: liveability area = max(9.5, 16.7) = 16.7; liveability width = max(2.4, 3.6) = **3.6** (furniture wins)
- BATHROOM (combined, typical): area = max(2.8, 2.8) = 2.8; width = max(1.2, 1.2) = 1.2 (coincident)

**Why width matters concretely**: a 9.5 m² bedroom at 2.4m × 4.0m passes both NBC area (9.5≥9.5) and NBC width (2.4≥2.4). But at 2.4m wide it cannot fit `bed (1.5m) + side-table (0.5m) + clearance (0.6m) = 2.6m`. The furniture min_width = 3.0m forces the room to ≥3.0m wide, making it actually livable.

These values live in `kb/furniture_floor.json`. Versioned via `furniture_kb_version`.

### § 4.3 — Target sizes — REVISED v0.3

Targets now KB-managed via `kb/room_targets.json` (Walk #3 #11). Per architecture-v2 Component 9 worked example:

| Category | is_master | Target m² | Source |
|---|---|---|---|
| BEDROOM | False | 10.2 (~110 sqft) | architecture-v2 § 5 |
| BEDROOM | True | 14.9 (~160 sqft) | architecture-v2 § 5 |
| LIVING | False | 18.6 (~200 sqft) | architecture-v2 § 5 |
| KITCHEN | False | 9.3 (~100 sqft) | architecture-v2 § 5 |
| BATHROOM (COMBINED) | False | 3.3 (~35 sqft) | architecture-v2 § 5 |
| BATHROOM (COMBINED) | True | 4.2 (~45 sqft for master-attached) | architecture-v2 § 5 |
| POOJA | False | 3.3 (~35 sqft) | architecture-v2 § 5 |
| UTILITY | False | 3.7 (~40 sqft) | architecture-v2 § 5 |

Versioned via `targets_kb_version` in provenance. Plot-tier-aware target sizing (B-NNN-B) deferred.

### § 4.4 — Max sizes (waste threshold)

Per-category multipliers (consistency fix per Walk #1 #13 / Walk #2 #9):

| Category | is_master | max_m2 multiplier | Resulting cap |
|---|---|---|---|
| BEDROOM | False | 1.6 × target | 16.3 m² |
| BEDROOM | True | 1.6 × target | 23.8 m² |
| LIVING | False | 2.5 × target | 46.5 m² |
| KITCHEN | False | 1.6 × target | 14.9 m² |
| BATHROOM | False | 1.6 × target | 5.3 m² |
| BATHROOM | True | 1.6 × target | 6.7 m² |
| POOJA | False | 1.6 × target | 5.3 m² |
| UTILITY | False | 1.6 × target | 5.9 m² |

### § 4.5 — Surplus allocation — REVISED v0.3 wording

Priority is **first-class config** (Walk #3 #8). The default v1 ordering is documented but the override path is explicit:

```python
@dataclass(frozen=True)
class RoomSizingConfig:
    # ... other fields ...
    priority_override: tuple[RoomCategory, ...] | None = None
    """If supplied, replaces the v1 default ordering. v1 default is:
    (BEDROOM_master, BEDROOM_typical, KITCHEN, LIVING, BATHROOM_master,
     BATHROOM_typical, POOJA, UTILITY, OTHER).

    Empty tuple is invalid; None means use default.
    """
```

After computing `liveability_min_area` for each room, `surplus_m2 = buildable_envelope_minus_corridor_m2 - Σ liveability_min_area`. Distribution algorithm (unchanged from v0.2):

```python
def distribute_surplus(rooms, surplus_m2, strategy):
    """Allocate surplus_m2 among rooms, capped at max_m2.

    PRIORITY_GREEDY (default): give highest-priority room target first.
    PROPORTIONAL (alternative): distribute proportionally to priority weights.

    Leftover surplus → unassigned_area_m2 (Walk #3 #7), explicit field
    on RoomSizeTable. Downstream (C11) decides if this becomes balcony,
    courtyard expansion, or void.
    """
```

Default v1 priority order:
1. BEDROOM_1 (is_master=True)
2. BEDROOM_2..N
3. KITCHEN (if present)
4. LIVING (if present)
5. BATHROOM_1 (master-attached if applicable)
6. BATHROOM_2..M
7. POOJA (if present)
8. UTILITY (if present)
9. OTHER (pooled)

Conditional inclusion: skipped categories don't create gaps in the priority sequence.

### § 4.6 — Infeasibility detection

Unchanged from v0.2. If `Σ liveability_min_area_m2 > buildable_envelope_minus_corridor_m2`, raise `RoomSizingInfeasibleError(B-NNN-A)` with deficit named.

Hard-fail is deliberate per Pattern A. Soft-fail mode (B-NNN-A reframed) requires C2 retry contract amendment.

### § 4.7 — Validator invariants — REVISED v0.3

| # | Invariant | Source | Mode |
|---|---|---|---|
| 1 | rooms.count == FloorRoomBrief-derived total count (with conditional inclusion) | Walk #1 #2 / Walk #2 #3 | RAISE |
| 2 | category counts match brief | brief consistency | RAISE |
| 3 | every regulatory_minimum.area_m2 ≥ NBC table value for resolved tier | NBC compliance | RAISE |
| 4 | every regulatory_minimum.width_m ≥ NBC table value | NBC compliance | RAISE |
| 5 | every regulatory_minimum.height_m ≥ NBC table value | NBC compliance | RAISE |
| 6 | every liveability_min_area_m2 ≥ regulatory_minimum.area_m2 | math | RAISE |
| **6b** | **every liveability_min_width_m ≥ regulatory_minimum.width_m** (NEW v0.3 per Walk #3 #4) | math | RAISE |
| 7 | every target_m2 ≥ liveability_min_area_m2 | math | RAISE |
| 8 | every max_m2 ≥ target_m2 | math | RAISE |
| 9 | Σ liveability_min_area_m2 ≤ buildable_envelope_minus_corridor_m2 | feasibility | RAISE |
| 10 | Σ liveability_min_area_m2 ≤ envelope × packing_efficiency (heuristic_packing_check) | placement-readiness heuristic | **WARN** (logged; not raised) |
| 11 | room_ids are unique | data integrity | RAISE |
| 12 | priority values cover 1..n contiguously | well-formedness | RAISE |
| 13 | exactly one BEDROOM has is_master=True iff bedroom_count ≥ 1 | master semantics | RAISE |
| 14 | at most one BATHROOM has is_master=True | master semantics | RAISE |
| **15** | **bathroom_subtype is set iff category == BATHROOM** (NEW v0.3 per Walk #3 #6) | schema integrity | RAISE |
| **16** | **unassigned_area_m2 ≥ 0** (NEW v0.3 per Walk #3 #7) | math | RAISE |

**Inv 10 framing (REVISED v0.3 per Walk #3 #3)**: this is a **heuristic_packing_check**, NOT a geometric guarantee. Provenance carries `packing_basis = "heuristic_v1_static_0.75"` to make this explicit. Real geometric placement-feasibility is C11 placement's job.

**Width feasibility deferral (Walk #3 #2)**: C9 enforces NBC width minimum (Inv 4) and liveability width (Inv 6b). C9 does NOT enforce **bay-grid feasibility** (whether `liveability_min_width_m` can be realized within available grid bays at the placement stage). That's C11 placement's job. v1 callers should not interpret a passing C9 result as guaranteed-placeable.

### § 4.8 — Order-of-checks

Type checks → shape (B-066) → brief sanity (bedroom_count ≥ 1; has_kitchen | has_living etc.) → dwelling-tier resolution (with multi-floor warning) → per-candidate regulatory lookup → liveability resolution (area + width) → infeasibility check → surplus allocation → validator (full invariant sweep). Pattern A: fail at boundary.

---

## § 5 — Invocation contract (public)

```python
sized = size_rooms(
    corridor_designed_candidates=c8_output,
    floor_room_brief=c1_brief.floors[0],
    grid=c7_grid,
    plot_analysis=c4_plot_analysis,
)
```

Cardinality: 1-3 in → 1-3 out, position-paired.

---

## § 6 — Failure modes — REVISED v0.3

| Condition | Behavior |
|---|---|
| `corridor_designed_candidates` not a tuple | `TypeError` |
| `floor_room_brief` not FloorRoomBrief | `TypeError` |
| `grid` not Grid | `TypeError` |
| `plot_analysis` not PlotAnalysis | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066, mirrors C6) |
| `plot_analysis.climate_zone` is HOT_DRY or COLD | passes through; v1 has no climate-dependent sizing |
| Brief specifies 0 bedrooms | `ValueError` |
| Brief specifies 0 bathrooms | passes through; resulting table has 0 bathrooms |
| Brief specifies has_living=False | passes through; LIVING absent from table |
| Brief specifies has_kitchen=False | passes through; KITCHEN absent from table |
| brief.floor_label != "Ground" (multi-floor context) | passes through; multi_floor_tier_warning=True; defensive LARGE-pick |
| Σ liveability_min_area > envelope (Inv 9) | `RoomSizingInfeasibleError` (B-NNN-A) |
| Σ liveability_min_area > envelope × packing_efficiency (Inv 10) | log to provenance; no raise |
| One room category's NBC table entry missing for resolved tier | `KeyError` (KB integrity issue) |
| Empty input tuple | Returns empty tuple |

---

## § 7 — Test plan — REVISED v0.3

Following C5/C6/C8 pattern. v0.3 targets ~110 tests with explicit invariant→test mapping (Walk #1 #15 / Walk #2 #11):

### Invariant coverage

| Inv # | Invariant | Test count | Test file |
|---|---|---|---|
| 1 | rooms.count == brief total (with conditionals) | 6 | test_c9_schema.py |
| 2 | category counts match brief | 8 | test_c9_schema.py |
| 3 | regulatory.area ≥ NBC value (per tier) | 10 | test_c9_nbc_table.py |
| 4 | regulatory.width ≥ NBC value | 8 | test_c9_nbc_table.py |
| 5 | regulatory.height ≥ NBC value | 6 | test_c9_nbc_table.py |
| 6 | liveability_area ≥ regulatory.area | 4 | test_c9_schema.py |
| **6b** | **liveability_width ≥ regulatory.width (NEW v0.3)** | 6 | test_c9_schema.py |
| 7 | target ≥ liveability_area | 4 | test_c9_schema.py |
| 8 | max ≥ target | 4 | test_c9_schema.py |
| 9 | Σ liveability_area ≤ envelope (RAISE) | 6 | test_c9_orchestrator.py |
| 10 | Σ liveability_area ≤ envelope × packing_efficiency (WARN) | 4 | test_c9_orchestrator.py |
| 11 | room_ids unique | 3 | test_c9_schema.py |
| 12 | priority contiguous after conditionals | 4 | test_c9_schema.py |
| 13 | exactly one BEDROOM is_master if bed_count ≥ 1 | 4 | test_c9_schema.py |
| 14 | at most one BATHROOM is_master | 4 | test_c9_schema.py |
| **15** | **bathroom_subtype iff category=BATHROOM (NEW v0.3)** | 4 | test_c9_schema.py |
| **16** | **unassigned_area_m2 ≥ 0 (NEW v0.3)** | 3 | test_c9_schema.py |
| **Subtotal — invariants** | | **88** | |

### Module-coverage

| Module | Tests | Focus |
|---|---|---|
| nbc_table.py | ~12 | dwelling-tier resolution; clause coverage; all subtype variants (COMBINED/BATH_ONLY/WC_ONLY) |
| furniture_floor.py | ~10 | (category, is_master) lookup with both area + min_width fields |
| targets_kb.py | ~6 | (category, is_master) target lookup |
| allocator.py | ~12 | PRIORITY_GREEDY / PROPORTIONAL / max-clamp / leftover surplus / unassigned_area populated |
| size_rooms (orchestrator) | ~15 | end-to-end on bangalore_40x60 / chennai-30x40 / delhi_60x90 |
| failure_modes | ~15 | type checks; B-066; edge cases; multi-floor warning; infeasibility |
| **Subtotal — coverage** | | **~70** | |

**Combined estimate ≈ 110 tests** (some invariant tests double as module-coverage tests; deduplication brings the unique count to ~110).

---

## § 8 — KB references — REVISED v0.3

| KB | Status | Used for |
|---|---|---|
| `kb/nbc_room_minimums.json` | NEW v0.2 | NBC 2016 dwelling-tiered table (SMALL/LARGE) with area + width + height + clause |
| `kb/furniture_floor.json` | REVISED v0.3 | (category, is_master, bathroom_subtype) → (area, min_width_m, reference_config) |
| `kb/room_targets.json` | NEW v0.3 (Walk #3 #11) | (category, is_master) → target_m2; matches existing KB pattern |
| `kb/state_dcr_overrides.json` | stub; B-NNN-D | TNCDBR / Maharashtra DCR / KMC overrides on NBC defaults |

**NBC clause provenance — REVISED v0.3 per Walk #3 web research**:

Each row of `kb/nbc_room_minimums.json` carries a `clause` field. **Secondary sources disagree on NBC numbers**: the slideshare bye-laws table (which v1 ships) cites bedroom=7.5/9.5 m² (dwelling-tiered) referencing clauses 12.1.1/12.2.1/12.2.2; InfraLens cites bedroom=6.5 m² (flat) without clause attribution; Wadhwa/Sobha consensus aligns with slideshare bye-laws.

v1 ships the slideshare bye-laws values because:
- They are dwelling-tiered (matching NBC 2016 Part 3 § 12 structure)
- Multiple consensus sources agree
- Clause attributions are pinned to the table

**B-150 is the authoritative-NBC-PDF verification pass** that resolves the source disagreement. Until B-150 lands:
- Verified clauses (12.1.1, 12.2.1, 12.2.2, 12.3.1, 12.3.2, 12.4): tagged "verified-via-bye-laws-table-S33"
- Unverified clauses (storeroom in NBC Part 3): tagged "v0.3 unverified clause"

---

## § 9 — Out of scope

| Item | Backlog ID |
|---|---|
| State-DCR room-size overrides (TNCDBR, MH-DCR, KMC) | B-NNN-D |
| Plot-tier-aware target sizing (T1/T2/T3 differential) | B-NNN-B |
| Configurable priority order beyond v1 default | B-NNN-C |
| Multi-floor sizing coordination (master on FF, kids on GF, etc.) | B-NNN-E |
| Furniture KB versioning + per-room user customization | B-NNN-F |
| Soft-fail mode + C2 retry contract | B-NNN-A |
| BR/BA pooling rules (master-attached vs common) | B-NNN-I |
| Multi-floor dwelling-tier resolution | B-148 |
| Packing-efficiency tightening to ERROR mode | B-149 |
| NBC clause verification against authoritative PDF | B-150 |
| **OTHER category subtyping (study/office/guest)** | **B-151 (NEW v0.3 per Walk #3 #9)** |
| Width-to-bay grid feasibility | C11 placement (deferred to C11 spec, not C9 backlog) |

---

## § 10 — Provenance

`RoomSizingProvenance` carries:
- `derived_at`, `plot_analysis_trace_id` — traceability
- `floor_label` — which floor produced this
- `nbc_table_version`, `furniture_kb_version`, `targets_kb_version` (NEW v0.3) — KB snapshots
- `dwelling_size_tier` — which tier drove regulatory lookup
- `multi_floor_tier_warning` (NEW v0.3) — defensive LARGE-pick fired
- `enforcement_mode`, `allocation_strategy`
- `surplus_distributed_m2`, `rooms_at_min`, `rooms_clamped_at_max`
- `packing_basis` (NEW v0.3) — `"heuristic_v1_static_0.75"` until B-149 calibrated
- `heuristic_packing_check_warning` (RENAMED v0.3) — Inv 10 fired in WARN mode
- `rule_trace`

---

## § 11 — Spec metadata

- **Version**: v0.3 PROPOSED
- **Status**: PROPOSED — pending Ramalingam LOCK adjudication. Per Rule 8, LOCK belongs to Ramalingam alone.
- **Lineage**: v0.1 DRAFT → v0.2 PROPOSED → v0.3 PROPOSED (3 walks completed)
- **Authoring sessions**: S33 entire arc
- **Companion artifacts**: Walk #1 critique (`35_C9_walk_1_spec_fidelity.md`), Walk #2 + Walk #3 reviewer rounds (chat-delivered S33), web research grounding NBC clauses + secondary-source disagreement.

---

## § 12 — Backlog enumeration (preliminary; B-NNNs assigned at LOCK)

Total: **12 items** (was 11 in v0.2; +1 new from Walk #3).

| ID | Title | Origin | Status | Trigger | S33-scope | Effort |
|---|---|---|---|---|---|---|
| B-NNN-A | Soft-fail mode + C2 retry | § 4.6 / Q8 | BACKLOG | C2 feasibility loop | OUT | M |
| B-NNN-B | Plot-tier-aware target sizing | § 4.3 | BACKLOG | Empirical signal | OUT | S |
| B-NNN-C | Configurable priority order | § 4.5 | BACKLOG | First user request | OUT | S |
| B-NNN-D | State DCR overrides | § 4.1 | BACKLOG | Municipality rejection | OUT | M |
| B-NNN-E | Multi-floor coordination | § scope | BACKLOG | C12 vertical alignment | OUT | L |
| B-NNN-F | Furniture KB versioning | § 4.2 | BACKLOG | Customization feature | OUT | M |
| B-NNN-I | Bath assignment rules | § 4.2 | BACKLOG | C11 placement | OUT | M |
| B-148 | Multi-floor dwelling-tier | § 4.1 | BACKLOG | Multi-floor test case | OUT | M |
| B-149 | Packing-efficiency to ERROR | § 4.7 Inv 10 | BACKLOG | Calibration data | OUT | S |
| B-150 | NBC clause verification | § 4.1 / § 8 | BACKLOG | Regulator challenge | OUT | S |
| **B-151** | **OTHER category subtyping** (NEW v0.3 per Walk #3 #9) | § 9 | BACKLOG | First product feature wanting per-other-room sizing differentiation | OUT | M |
| (C11 deferred) | Width-to-bay grid feasibility | Walk #3 #2 | C11 spec, not C9 backlog | C11 build | OUT (out of C9 scope) | (in C11) |

---

## § 13 — Definitions

- **`regulatory_minimum`** *(v0.2)*: NBC 2016 floor (area + width + height + clause). All three are NBC-mandated.
- **`liveability_min_area_m2`** *(v0.2)*: `max(regulatory.area_m2, furniture.area_m2)`.
- **`liveability_min_width_m`** *(NEW v0.3)*: `max(regulatory.width_m, furniture.min_width_m)`. Closes the area-only gap from Walk #3 #4.
- **`target_m2`** *(v0.2)*: comfortable size; KB-managed in v0.3.
- **`max_m2`** *(v0.2)*: waste threshold; per-category multipliers per § 4.4.
- **`buildable_envelope_minus_corridor_m2`** *(v0.2)*: from C8's `corridor_path.envelopes` total minus corridor area.
- **`DwellingSizeTier`** *(v0.2)*: NBC tier enum (SMALL ≤50 m² / LARGE >50 m²).
- **`is_master`** *(v0.2)*: True for BEDROOM_1; drives `(category, is_master)` furniture/target lookup.
- **`bathroom_subtype`** *(NEW v0.3)*: COMBINED (default) / BATH_ONLY / WC_ONLY. Drives NBC + furniture lookup for bathroom rooms.
- **`packing_efficiency`** *(v0.2)*: default 0.75. Heuristic ratio for Inv 10 WARN.
- **`packing_basis`** *(NEW v0.3)*: provenance string identifying the basis of the packing-efficiency heuristic. v1: `"heuristic_v1_static_0.75"`.
- **`unassigned_area_m2`** *(NEW v0.3)*: explicit field for leftover envelope area after surplus allocation. Replaces v0.2's narrative.
- **`PRIORITY_GREEDY` / `PROPORTIONAL`** *(v0.2)*: surplus-allocation strategies.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 DRAFT (carried)

§ 14.1 — Two-floor minimum (regulatory + liveability) — NBC compliance is hard; furniture-fit is quality.
§ 14.2 — `PRIORITY_GREEDY` as v1 default.
§ 14.3 — Hard-fail on infeasibility (v1).
§ 14.4 — NBC table is KB-managed JSON.

### From v0.2 PROPOSED

§ 14.5 — C9 receives `FloorRoomBrief` directly.
§ 14.6 — Master/non-master is a `priority` and `is_master` distinction, not a category.
§ 14.7 — Schema enrichment: `regulatory_minimum` is a triple (area + width + height).
§ 14.8 — `consumption_band` field DROPPED from RoomSizeRequirement.
§ 14.9 — Dwelling-tier resolved from C8 envelope total per floor (with multi-floor caveat).
§ 14.10 — Packing-efficiency check is WARN, not RAISE.
§ 14.11 — `max_m2` per-category multipliers are internally consistent.

### NEW v0.3 (resolved per Walk #3)

§ 14.12 — **Liveability includes width, not just area** (Walk #3 #4 CRITICAL). v0.2's area-only liveability check missed that NBC-area-passing rooms can fail furniture-fit due to width. v0.3 furniture KB carries `(area_m2, min_width_m)` per `(category, is_master, bathroom_subtype)`; both `liveability_min_area_m2` and `liveability_min_width_m` flow through to RoomSizeRequirement.

§ 14.13 — **Multi-floor dwelling-tier handled defensively** (Walk #3 #1). When brief.floor_label indicates multi-floor context, C9 picks LARGE tier defensively (over-spec is harmless; under-spec = NBC violation) and sets `multi_floor_tier_warning=True` in provenance. B-148 lifts this when C2 threads `total_dwelling_area_m2`.

§ 14.14 — **Width feasibility deferred to C11** (Walk #3 #2). C9 enforces NBC width and liveability width minimums, but does NOT check whether the width can be realized within available grid bays. That's C11 placement's job. Documented to prevent silent over-rejection.

§ 14.15 — **Heuristic_packing_check is a heuristic, not a guarantee** (Walk #3 #3). Provenance carries `packing_basis = "heuristic_v1_static_0.75"`. Real geometric placement-feasibility is C11.

§ 14.16 — **Grid input rationale documented** (Walk #3 #5). Grid is consumed for trace correlation, future B-148 multi-floor dwelling-tier resolution, and config-flagged grid-aware sizing. v1 sizing is intentionally grid-blind to preserve C9-vs-C11 layer separation. Grid availability ≠ Grid usage.

§ 14.17 — **`unassigned_area_m2` as explicit field** (Walk #3 #7). Replaces v0.2's narrative "stays unassigned"; downstream consumers (C11) read this directly.

§ 14.18 — **Targets KB-managed** (Walk #3 #11). `kb/room_targets.json` matches the pattern of `kb/nbc_room_minimums.json` and `kb/furniture_floor.json`. Versioned via `targets_kb_version`.

§ 14.19 — **Priority is first-class config** (Walk #3 #8). `RoomSizingConfig.priority_override` is documented as the canonical override path; v1 default ordering exists but the override is not buried.

§ 14.20 — **Bathroom subtype is schema-explicit, not assumption** (Walk #3 #6). v1 default for BATHROOM category is `BathroomSubtype.COMBINED`; explicit field preserves backward compatibility when separate bath/WC variants ship later.

§ 14.21 — **Secondary-source NBC disagreement is documented** (Walk #3 web research). Multiple authoritative-looking sources cite different bedroom/kitchen minimums. v1 ships the slideshare bye-laws values (consensus of multiple sources, dwelling-tiered, clause-attributed). B-150 is the authoritative-PDF verification pass.

---

## § 15 — Open questions remaining

After 3 walks, the open-questions list has compressed substantially. v0.3's residual questions:

### NEW Q13 — Should `liveability_min_width_m` be required to be ≤ envelope's smaller axis?

If a brief has a 2.5m × 6m envelope-minus-corridor (effective width = 2.5m), and a room's liveability_min_width = 3.0m, the room is infeasible by width alone — even before area sums up. Currently no explicit check.

**Recommendation for LOCK**: defer to C11 placement (which does the actual envelope-fit-check). C9 doesn't have envelope geometry beyond total area.

### NEW Q14 — `kb/room_targets.json` format: include max_m2 multipliers too, or keep them in schema constants?

§ 4.4 max multipliers (1.6× / 2.5×) are currently in spec text. Should they live in the KB?

**Recommendation for LOCK**: yes; move to KB. Then user briefs can override via `RoomSizingConfig.targets_kb_override`. Add to v0.3 → LOCK.

---

## § 16 — End of v0.3 PROPOSED

Expected next: Ramalingam LOCK adjudication → build (D-066 step 6-8).

If LOCKED, the build session can begin immediately:
- `kb/nbc_room_minimums.json` + `kb/furniture_floor.json` + `kb/room_targets.json` authored
- 11 modules under `buildemup/components/c09/` (schema, nbc_table, furniture_floor, targets_kb, allocator, validator, room_sizer)
- Tests authored matching § 7 invariant→test mapping (~110 tests)

If walk #4 needed, walk happens on v0.3 PROPOSED.
