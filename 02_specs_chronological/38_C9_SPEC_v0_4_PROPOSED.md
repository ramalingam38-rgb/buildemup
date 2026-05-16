# BuildemUp — C9 Room Sizer — SPEC v0.4 PROPOSED

**Status**: PROPOSED. PENDING Ramalingam LOCK adjudication. Per Rule 8, LOCK authority belongs to Ramalingam alone; this document represents the v0.4 candidate after walks #1, #2, #3, and #4.
**Component**: C9 of canonical 17-component v3 list (Track 3). Position 9.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C8 (`CorridorDesignedCandidate`) + C7 (`Grid`) + C4 (`PlotAnalysis`) + C1's `FloorRoomBrief`. Produces input for C10 (Bathroom + Wet-Zone Stack Planner) and C11 (Room Placement).
**Authoring sessions**: S33 entire arc.
**Predecessor**: v0.3 PROPOSED (732 lines).

---

## § 0 — Why this spec, why now

C9 sits between "the bands and corridor are designed" and "specific rooms have specific sizes." Given the brief's room composition, the band envelopes from C8, the structural grid bays, and the plot analysis, C9 produces a `RoomSizeTable` — for each room: regulatory floor (area + width + height + clause + source_confidence), liveability minimum (area + width), target, max.

C9 does NOT place rooms (C11). C9 does NOT generate furniture layouts (C14). C9 does NOT decide adjacencies (C5/C11). C9 does NOT assign rooms to zone bands (C11). C9 does NOT enforce height (C11 — § 14.22). C9 does NOT score sizes (C14).

**v0.4 lineage delta from v0.3 PROPOSED** (8 walk-#4 edits):

| # | Edit | Source | § affected |
|---|---|---|---|
| 1 | Multi-floor tier accuracy: `tier_resolution_accuracy` provenance flag | Walk #4 #1 | § 10, § 14 |
| 2 | Early width infeasibility WARN (Inv 17) | Walk #4 #2 | § 4.7, § 10 |
| 3 | Grid usage: `grid_bay_min_m` / `grid_bay_max_m` in provenance + Inv 18 grid-bay cross-reference WARN | Walk #4 #3 | § 4.7, § 10, § 14 |
| 4 | Liveability width = interior clear width; document wall-thickness deferral | Walk #4 #4 | § 4.2, § 14 |
| 5 | NBC source confidence: `source_confidence` field on RegulatoryMinimum | Walk #4 #6 | § 3, § 4.1, § 8 |
| 6 | Optional `other_subtype` field on RoomSizeRequirement | Walk #4 #7 | § 3 |
| 7 | Height enforcement deferral documented (§ 14.22) | Walk #4 #10 | § 14 |
| 8 | New backlog B-152: placement_risk_level combined signal | Walk #4 #9 | § 12 |

Push-backs (no spec change): Walk #4 #5 (aspect ratio is C11 placement geometry), Walk #4 #8 (width is constraint, not target/max dimension).

---

## § 1 — Purpose

Given a C8-corridor-designed candidate, the brief's room composition, the structural grid bays, and the plot analysis, produce a **`RoomSizeTable`** — for each requested room (bedroom × N, bathroom × M, optional kitchen, optional living, optional pooja, optional utility, plus brief-defined `other_rooms`):
- regulatory floor (area, width, height, clause, source_confidence) per NBC 2016 dwelling tier
- liveability minimum (interior clear area AND interior clear width)
- target size (area)
- max size (area)

The total of all liveability-min areas must fit within the buildable envelope minus the corridor area (Inv 9). A *heuristic_packing_check* warning fires (Inv 10 WARN). v0.4 adds two more WARN-mode safety nets: Inv 17 catches "this room's required width exceeds the envelope's smaller axis" and Inv 18 catches "this room's required width exceeds twice the largest grid bay" — both early indicators of placement-infeasibility that C11 would otherwise discover.

Cardinality preserved: 1-3 C8 candidates → 1-3 C9 candidates, position-paired.

**Out of scope for C9**:
- Room placement (XY positioning) — C11
- Adjacency / connectivity — C5 selected, C11 enforces
- Zone band assignment for rooms — C11 placement
- Width-to-bay grid feasibility (full check) — C11 placement (C9 does WARN-only sanity per Inv 17/18)
- Aspect ratio / room shape — C11 placement geometry (Walk #4 #5 push-back)
- Wall thickness deduction from envelope coords — C11 placement (Walk #4 #4 push-back; § 14.23)
- Door swing clearance — C13 door placement
- Height enforcement — C11 volume validation (§ 14.22)
- Furniture layout — C14 furniture-fit metric
- Wet-wall back-to-back stacking — C10
- Vertical alignment across floors — C12
- Cost computation — C14

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

`RoomSizingConfig` carries per-call tunables: `enforcement_mode` (`STRICT` / `WARN`), Neufert/Ching multipliers, `allocation_strategy` (`PRIORITY_GREEDY` / `PROPORTIONAL`), `packing_efficiency` (default 0.75), `dwelling_tier_override` (None = derived), `priority_override` (None = use v1 default).

**Why `Grid` is taken** (REVISED v0.4 per Walk #4 #3): Grid is now functionally consumed in two ways:
1. **Provenance capture**: `grid_bay_min_m` and `grid_bay_max_m` are stored in `RoomSizingProvenance` for downstream debugging (when a C11 placement fails, the C9 sizing context includes the bay dimensions that constrained it).
2. **Inv 18 (WARN) cross-reference**: rooms whose `liveability_min_width_m > 2 × grid.bay_max_m` are flagged as "very wide rooms unlikely to fit any bay-aligned placement." Doesn't raise — that's C11's call — but surfaces the impossibility early.

Grid availability still does NOT drive sizing computation (sizes are determined by NBC + furniture floors). Grid is consumed as *context*, not as *constraint*. § 14.16 (v0.3) extended in § 14.16-bis (v0.4) to cover the provenance + Inv 18 use.

---

## § 3 — Output schema — REVISED v0.4

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
    """NEW v0.4 (Walk #4 #6) — explicit confidence tag for NBC values.

    Until B-150 verifies all rows against the authoritative NBC 2016 Part 3
    PDF, every regulatory_minimum carries a confidence tag so downstream
    consumers and users can see the provenance quality.
    """
    VERIFIED            = "verified"             # Pinned to authoritative NBC PDF
    SECONDARY_CONSENSUS = "secondary_consensus"  # Multiple secondary sources agree
    SECONDARY_UNVERIFIED= "secondary_unverified" # Single source or sources disagree


class TierResolutionAccuracy(str, Enum):
    """NEW v0.4 (Walk #4 #1) — explicit accuracy tag for dwelling-tier
    resolution.

    Multi-floor briefs cannot resolve tier from per-floor area alone (NBC's
    50 m² threshold is whole-dwelling). v1 picks LARGE defensively for
    multi-floor; the accuracy tag makes the assumption explicit instead
    of silently approximating.
    """
    EXACT                       = "exact"                       # single-floor brief; tier is exact
    APPROXIMATE_DEFENSIVE_LARGE = "approximate_defensive_large" # multi-floor; LARGE picked defensively
    OVERRIDE_SUPPLIED           = "override_supplied"           # config.dwelling_tier_override used


@dataclass(frozen=True)
class RegulatoryMinimum:
    """NBC 2016 floor (area + width + height + clause + source_confidence).

    REVISED v0.4 (Walk #4 #6): added source_confidence. Until B-150 lands,
    most rows are SECONDARY_CONSENSUS (multiple secondary sources agree on
    the value); the storeroom row (and any row where Walk #1/#2 web sources
    diverged) is SECONDARY_UNVERIFIED. After B-150 verifies against the
    authoritative NBC 2016 PDF, rows can be promoted to VERIFIED.
    """
    area_m2: float                  # NBC minimum floor area
    width_m: float                  # NBC minimum width (the shorter side)
    height_m: float                 # NBC minimum ceiling height
    nbc_clause: str                 # "NBC 2016 Part 3 Clause 12.2.1" etc.
    source_confidence: NBCSourceConfidence  # NEW v0.4


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
    room_id: str                                    # e.g. "BEDROOM_1", "BATHROOM_2", "OTHER_1"
    category: RoomCategory                          # enum
    regulatory_minimum: RegulatoryMinimum           # NBC quintuple
    liveability_min_area_m2: float                  # max(regulatory.area_m2, furniture.area_m2)
    liveability_min_width_m: float                  # max(regulatory.width_m, furniture.min_width_m)
                                                     # See § 14.23: this is INTERIOR CLEAR width.
    target_m2: float                                # Neufert/Ching comfortable
    max_m2: float                                   # waste threshold
    priority: int                                   # 1 = highest, used for surplus allocation
    is_master: bool = False                         # Drives (category, is_master) lookup
    bathroom_subtype: BathroomSubtype | None = None # Set iff category == BATHROOM
    other_subtype: str = ""                         # NEW v0.4 (Walk #4 #7):
                                                     # echoes brief.other_rooms[i] when category=OTHER;
                                                     # empty string for non-OTHER rooms.
                                                     # v1 does not drive sizing differentiation;
                                                     # B-151 lifts that.


@dataclass(frozen=True)
class RoomSizeTable:
    """The complete sizing for one C8 candidate's floor."""
    rooms: tuple[RoomSizeRequirement, ...]
    buildable_envelope_minus_corridor_m2: float     # available area
    dwelling_size_tier: DwellingSizeTier            # which NBC tier was used
    total_liveability_min_area_m2: float            # Σ liveability_min_area
    total_target_m2: float                          # Σ target
    surplus_for_distribution_m2: float              # envelope − Σ liveability_min
    unassigned_area_m2: float                       # leftover after surplus allocation
    packing_efficiency_used: float                  # which packing factor was applied
    floor_label: str                                # propagated from FloorRoomBrief


@dataclass(frozen=True)
class RoomSizingProvenance:
    """Provenance for one C9 sizing pass — REVISED v0.4."""
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str                                # propagated from FloorRoomBrief
    nbc_table_version: str
    furniture_kb_version: str
    targets_kb_version: str
    dwelling_size_tier: DwellingSizeTier            # tier that drove regulatory lookup
    tier_resolution_accuracy: TierResolutionAccuracy # NEW v0.4 (Walk #4 #1):
                                                     # EXACT / APPROXIMATE_DEFENSIVE_LARGE /
                                                     # OVERRIDE_SUPPLIED. Replaces v0.3's
                                                     # multi_floor_tier_warning bool with a
                                                     # 3-state enum that captures the actual
                                                     # accuracy semantic, not just a binary flag.
    grid_bay_min_m: float                           # NEW v0.4 (Walk #4 #3):
                                                     # min(grid.bay_x_m, grid.bay_y_m) at C9 entry.
                                                     # Captured for downstream debugging.
    grid_bay_max_m: float                           # NEW v0.4 (Walk #4 #3):
                                                     # max(grid.bay_x_m, grid.bay_y_m) at C9 entry.
    enforcement_mode: str                           # STRICT | WARN
    allocation_strategy: str                        # PRIORITY_GREEDY | PROPORTIONAL
    surplus_distributed_m2: float                   # post-allocation
    rooms_at_min: tuple[str, ...]
    rooms_clamped_at_max: tuple[str, ...]
    packing_basis: str                              # "heuristic_v1_static_0.75" until B-149
    heuristic_packing_check_warning: bool           # Inv 10 fired in WARN mode
    early_width_infeasibility_warnings: tuple[str, ...]  # NEW v0.4 (Walk #4 #2):
                                                     # room_ids that triggered Inv 17 (WARN).
                                                     # Empty tuple if no warnings.
    grid_bay_max_warnings: tuple[str, ...]          # NEW v0.4 (Walk #4 #3):
                                                     # room_ids that triggered Inv 18 (WARN).
                                                     # Empty tuple if no warnings.
    rule_trace: tuple[str, ...]
    # REMOVED v0.4: multi_floor_tier_warning (replaced by tier_resolution_accuracy enum)
    # REMOVED v0.4: nothing else; all v0.3 fields preserved


@dataclass(frozen=True)
class RoomSizedCandidate:
    """One C8 CorridorDesignedCandidate + C9 sizing."""
    corridor_designed_candidate: CorridorDesignedCandidate
    room_size_table: RoomSizeTable
    provenance: RoomSizingProvenance
```

---

## § 4 — Behavior

### § 4.1 — Regulatory minimums (NBC 2016 KB) — REVISED v0.4

**Important caveat (carried from v0.3, expanded v0.4)**: secondary sources for NBC 2016 numbers **disagree**. The slideshare bye-laws table (S33 walk #1 source) cites bedroom 7.5/9.5 m² (dwelling-tiered); InfraLens cites bedroom 6.5 m² flat. v1 ships the **slideshare bye-laws values** (multiple sources agree, dwelling-tiered, clause-attributed) but every row is now tagged with a `source_confidence`. Until **B-150** (authoritative NBC 2016 PDF verification) lands:
- Most rows: `SECONDARY_CONSENSUS` — multiple secondary sources agree
- Storeroom row + any row where sources diverged: `SECONDARY_UNVERIFIED`

After B-150, rows verified against the authoritative PDF are promoted to `VERIFIED`.

**LOCK is NOT blocked on B-150** (per S33 walk #4 adjudication): blocking would prevent C9 ship indefinitely until somebody completes a 2-3 day independent verification effort. Better to ship with the confidence flag exposed; downstream consumers (and end users) can see the provenance quality and choose their tolerance.

#### Dwelling tier: SMALL (dwelling ≤ 50 m²)

| Category | NBC area m² | NBC width m | NBC height m | NBC clause | source_confidence |
|---|---|---|---|---|---|
| BEDROOM (smaller-of-2) | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.2.2 | SECONDARY_CONSENSUS |
| BEDROOM (single-room) | 9.5 | 2.4 | 2.75 | NBC 2016 Part 3 Clause 12.2.1 | SECONDARY_CONSENSUS |
| LIVING | 7.5 / 9.5 | 2.1 / 2.4 | 2.75 | same as BEDROOM | SECONDARY_CONSENSUS |
| KITCHEN (separate) | 3.3 | 1.8 | 2.75 | NBC 2016 Part 3 Clause 12.3.1 | SECONDARY_CONSENSUS |
| KITCHEN-cum-DINING | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.3.2 | SECONDARY_CONSENSUS |
| BATHROOM, COMBINED ★ | 1.8 | 1.0 | 2.1 | NBC 2016 Part 3 Clause 12.4 | SECONDARY_CONSENSUS |
| BATHROOM, BATH_ONLY | 1.2 | 1.0 | 2.1 | NBC 2016 Part 3 Clause 12.4 | SECONDARY_CONSENSUS |
| BATHROOM, WC_ONLY | 1.0 | 0.9 | 2.1 | NBC 2016 Part 3 Clause 12.4 | SECONDARY_CONSENSUS |
| POOJA | (no NBC floor) | — | 2.1 | (none) | SECONDARY_CONSENSUS |
| UTILITY (storeroom) | 3.2 | (no width minimum cited) | 2.2 | NBC 2016 Part 3 (clause v0.4 unverified) | SECONDARY_UNVERIFIED |

★ = v1 default for "BATHROOM" category.

#### Dwelling tier: LARGE (dwelling > 50 m²)

| Category | NBC area m² | NBC width m | NBC height m | NBC clause | source_confidence |
|---|---|---|---|---|---|
| BEDROOM | 9.5 | 2.4 | 2.75 | NBC 2016 Part 3 Clause 12.1.1 | SECONDARY_CONSENSUS |
| LIVING | 9.5 | 2.4 | 2.75 | same as BEDROOM | SECONDARY_CONSENSUS |
| KITCHEN (separate) | 4.5 | 1.8 | 2.75 | NBC 2016 Part 3 Clause 12.3.1 | SECONDARY_CONSENSUS |
| KITCHEN-cum-DINING | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.3.2 | SECONDARY_CONSENSUS |
| BATHROOM, COMBINED ★ | 2.8 | 1.2 | 2.1 | NBC 2016 Part 3 Clause 12.4 | SECONDARY_CONSENSUS |
| BATHROOM, BATH_ONLY | 1.8 | 1.2 | 2.1 | NBC 2016 Part 3 Clause 12.4 | SECONDARY_CONSENSUS |
| BATHROOM, WC_ONLY | 1.2 | 0.9 | 2.1 | NBC 2016 Part 3 Clause 12.4 | SECONDARY_CONSENSUS |
| POOJA | (no NBC floor) | — | 2.1 | (none) | SECONDARY_CONSENSUS |
| UTILITY (storeroom) | 3.2 | (no width minimum cited) | 2.2 | NBC 2016 Part 3 (clause v0.4 unverified) | SECONDARY_UNVERIFIED |

★ = v1 default for "BATHROOM" category.

#### Dwelling-tier resolution (REVISED v0.4 per Walk #4 #1)

```python
def _resolve_dwelling_tier(
    candidate: CorridorDesignedCandidate,
    floor_room_brief: FloorRoomBrief,
    config: RoomSizingConfig,
) -> tuple[DwellingSizeTier, TierResolutionAccuracy]:
    """Returns (tier, accuracy_tag).

    v1 explicitly assumes single-floor briefs. For multi-floor (where
    brief.floor_label != "Ground"), v1 picks LARGE defensively and tags
    the result APPROXIMATE_DEFENSIVE_LARGE so consumers/users see that
    the assumption was made.

    B-148 lifts the approximation when C2 threads total_dwelling_area_m2.
    """
    if config.dwelling_tier_override is not None:
        return config.dwelling_tier_override, TierResolutionAccuracy.OVERRIDE_SUPPLIED

    is_multi_floor = floor_room_brief.floor_label.lower() not in ("ground", "ground_floor", "gf")
    if is_multi_floor:
        return DwellingSizeTier.LARGE, TierResolutionAccuracy.APPROXIMATE_DEFENSIVE_LARGE

    envelope_areas = sum(e.area_m2 for e in candidate.corridor_path.envelopes)
    tier = DwellingSizeTier.SMALL if envelope_areas <= 50.0 else DwellingSizeTier.LARGE
    return tier, TierResolutionAccuracy.EXACT
```

These values live in `kb/nbc_room_minimums.json`. Versioned via `nbc_table_version`.

### § 4.2 — Liveability minimums (furniture-fit floor) — REVISED v0.4

**Walk #4 #4 clarification**: `liveability_min_width_m` is **interior clear width** — what the room occupant experiences as walkable / furniture-placeable width. Wall thickness (typical Indian residential interior partition: 100-115mm) is added by C11 when laying out room footprints from envelope-to-envelope coordinates. C9 produces the inside-the-room number; C11 produces the wall-to-wall placement. This separation matches the area treatment (carpet area at C9 → built-up area at C11 + wall thickness).

For each `(category, is_master, bathroom_subtype)` tuple, the furniture KB carries `(area_m2, min_width_m, reference_config)`:

| Category | is_master | Subtype | Furniture area m² | Furniture min_width_m | Reference configuration |
|---|---|---|---|---|---|
| BEDROOM | False | — | 9.3 | 3.0 | Single bed 0.9 × 2.0 + study 1.2 × 0.6 + wardrobe 1.2 × 0.6 + 0.75 m clearance |
| BEDROOM | True | — | 13.0 | 3.3 | Queen 1.5 × 2.0 + 2 side tables + wardrobe + 0.9 m clearance |
| LIVING | False | — | 16.7 | 3.6 | 3-seat sofa + 2 chairs + coffee table + circulation |
| KITCHEN | False | — | 7.9 | 2.4 | L-counter 3.0 m run + fridge + 1.2 m work aisle |
| BATHROOM | False | COMBINED | 2.8 | 1.2 | Shower 0.9 × 0.9 + WC + sink + 0.6 m clearance |
| BATHROOM | True | COMBINED | 4.0 | 1.5 | + tub-or-larger-shower + double sink |
| BATHROOM | False | BATH_ONLY | 2.0 | 1.0 | Shower 0.9 × 0.9 + sink + 0.4 m clearance |
| BATHROOM | False | WC_ONLY | 1.5 | 0.9 | WC + small sink + 0.5 m clearance |
| POOJA | False | — | 2.8 | 1.2 | Altar 0.6 × 0.9 + seated prayer + storage cabinet |
| UTILITY | False | — | 2.8 | 1.2 | Washing machine + sink + storage |

```python
liveability_min_area_m2  = max(regulatory.area_m2,  furniture.area_m2)
liveability_min_width_m  = max(regulatory.width_m,  furniture.min_width_m)
```

These values live in `kb/furniture_floor.json`. Versioned via `furniture_kb_version`.

### § 4.3 — Target sizes

KB-managed via `kb/room_targets.json`. Per architecture-v2 Component 9 worked example. Values unchanged from v0.3.

| Category | is_master | Target m² |
|---|---|---|
| BEDROOM | False | 10.2 |
| BEDROOM | True | 14.9 |
| LIVING | False | 18.6 |
| KITCHEN | False | 9.3 |
| BATHROOM (COMBINED) | False | 3.3 |
| BATHROOM (COMBINED) | True | 4.2 |
| POOJA | False | 3.3 |
| UTILITY | False | 3.7 |

### § 4.4 — Max sizes (waste threshold)

Per-category multipliers (unchanged from v0.3):

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

### § 4.5 — Surplus allocation

Priority is first-class config (v0.3 § 14.19). v1 default ordering:
1. BEDROOM_1 (is_master=True)
2. BEDROOM_2..N
3. KITCHEN (if present)
4. LIVING (if present)
5. BATHROOM_1 (master-attached if applicable)
6. BATHROOM_2..M
7. POOJA (if present)
8. UTILITY (if present)
9. OTHER (pooled)

Algorithm (`PRIORITY_GREEDY` default; `PROPORTIONAL` alternative): see v0.3 § 4.5. Leftover surplus → `unassigned_area_m2` field on RoomSizeTable.

### § 4.6 — Infeasibility detection

Unchanged from v0.3. If `Σ liveability_min_area_m2 > buildable_envelope_minus_corridor_m2`, raise `RoomSizingInfeasibleError(B-NNN-A)` with deficit named.

### § 4.7 — Validator invariants — REVISED v0.4

| # | Invariant | Source | Mode |
|---|---|---|---|
| 1 | rooms.count == FloorRoomBrief-derived total count (with conditional inclusion) | Walk #1 #2 / Walk #2 #3 | RAISE |
| 2 | category counts match brief | brief consistency | RAISE |
| 3 | every regulatory_minimum.area_m2 ≥ NBC table value for resolved tier | NBC compliance | RAISE |
| 4 | every regulatory_minimum.width_m ≥ NBC table value | NBC compliance | RAISE |
| 5 | every regulatory_minimum.height_m ≥ NBC table value | NBC compliance | RAISE |
| 6 | every liveability_min_area_m2 ≥ regulatory_minimum.area_m2 | math | RAISE |
| 6b | every liveability_min_width_m ≥ regulatory_minimum.width_m | math | RAISE |
| 7 | every target_m2 ≥ liveability_min_area_m2 | math | RAISE |
| 8 | every max_m2 ≥ target_m2 | math | RAISE |
| 9 | Σ liveability_min_area_m2 ≤ buildable_envelope_minus_corridor_m2 | feasibility | RAISE |
| 10 | Σ liveability_min_area_m2 ≤ envelope × packing_efficiency (heuristic_packing_check) | placement-readiness heuristic | **WARN** |
| 11 | room_ids are unique | data integrity | RAISE |
| 12 | priority values cover 1..n contiguously | well-formedness | RAISE |
| 13 | exactly one BEDROOM has is_master=True iff bedroom_count ≥ 1 | master semantics | RAISE |
| 14 | at most one BATHROOM has is_master=True | master semantics | RAISE |
| 15 | bathroom_subtype is set iff category == BATHROOM | schema integrity | RAISE |
| 16 | unassigned_area_m2 ≥ 0 | math | RAISE |
| **17** | **for every room, liveability_min_width_m ≤ min(envelope_width, envelope_depth)** (NEW v0.4 per Walk #4 #2) | early width infeasibility | **WARN** |
| **18** | **for every room, liveability_min_width_m ≤ 2 × grid.bay_max_m** (NEW v0.4 per Walk #4 #3) | grid-bay sanity | **WARN** |

**Inv 17 rationale**: catches the trivial impossibility where a room's required width exceeds the envelope's smaller axis dimension (e.g., 3.0 m bedroom in 2.5 m × 8 m envelope-minus-corridor). C11 placement would discover this; Inv 17 surfaces it at C9 boundary instead. WARN mode (not RAISE) because the envelope might still be a valid C8 candidate for *other* sizing scenarios (different brief mix); raising would be too strict.

**Inv 18 rationale**: catches rooms whose required width exceeds twice the largest grid bay (impossible to fit even spanning two bays without extreme overhang). WARN mode because some grid-misaligned placements are valid; this is the obvious-impossibility heuristic.

Both Inv 17 and Inv 18 violations are logged per-room into `provenance.early_width_infeasibility_warnings` and `provenance.grid_bay_max_warnings` respectively.

### § 4.8 — Order-of-checks

Type checks → shape (B-066) → brief sanity → dwelling-tier resolution (with accuracy tag) → grid-bay capture → per-candidate regulatory lookup → liveability resolution (area + width) → infeasibility check (Inv 9) → surplus allocation → validator (full invariant sweep, including Inv 17/18 WARN). Pattern A: fail at boundary; surface via WARN where over-strict.

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

## § 6 — Failure modes — REVISED v0.4

| Condition | Behavior |
|---|---|
| `corridor_designed_candidates` not a tuple | `TypeError` |
| `floor_room_brief` not FloorRoomBrief | `TypeError` |
| `grid` not Grid | `TypeError` |
| `plot_analysis` not PlotAnalysis | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066) |
| `plot_analysis.climate_zone` is HOT_DRY or COLD | passes through; v1 has no climate-dependent sizing |
| Brief specifies 0 bedrooms | `ValueError` |
| Brief specifies 0 bathrooms | passes through; resulting table has 0 bathrooms |
| Brief specifies has_living=False | passes through; LIVING absent from table |
| Brief specifies has_kitchen=False | passes through; KITCHEN absent from table |
| brief.floor_label != "Ground" (multi-floor context) | passes through; tier_resolution_accuracy=APPROXIMATE_DEFENSIVE_LARGE |
| Σ liveability_min_area > envelope (Inv 9) | `RoomSizingInfeasibleError` (B-NNN-A) |
| Σ liveability_min_area > envelope × packing_efficiency (Inv 10) | log to provenance; no raise |
| Any room's liveability_min_width_m > min(envelope_width, envelope_depth) (Inv 17) | log room_id to provenance.early_width_infeasibility_warnings; no raise |
| Any room's liveability_min_width_m > 2 × grid.bay_max_m (Inv 18) | log room_id to provenance.grid_bay_max_warnings; no raise |
| One room category's NBC table entry missing for resolved tier | `KeyError` (KB integrity issue) |
| Empty input tuple | Returns empty tuple |

---

## § 7 — Test plan — REVISED v0.4

v0.4 targets **~120 tests** with explicit invariant→test mapping:

### Invariant coverage

| Inv # | Invariant | Test count | Test file |
|---|---|---|---|
| 1 | rooms.count == brief total (with conditionals) | 6 | test_c9_schema.py |
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
| 12 | priority contiguous after conditionals | 4 | test_c9_schema.py |
| 13 | exactly one BEDROOM is_master if bed_count ≥ 1 | 4 | test_c9_schema.py |
| 14 | at most one BATHROOM is_master | 4 | test_c9_schema.py |
| 15 | bathroom_subtype iff category=BATHROOM | 4 | test_c9_schema.py |
| 16 | unassigned_area_m2 ≥ 0 | 3 | test_c9_schema.py |
| **17** | **liveability_min_width ≤ envelope min-axis (WARN)** (NEW v0.4) | 5 | test_c9_orchestrator.py |
| **18** | **liveability_min_width ≤ 2 × grid.bay_max_m (WARN)** (NEW v0.4) | 4 | test_c9_orchestrator.py |
| **Subtotal — invariants** | | **97** | |

### Module-coverage

| Module | Tests | Focus |
|---|---|---|
| nbc_table.py | ~12 | dwelling-tier; clause coverage; subtype variants; source_confidence |
| furniture_floor.py | ~10 | (category, is_master, bathroom_subtype) lookup; area + min_width |
| targets_kb.py | ~6 | (category, is_master) target lookup |
| allocator.py | ~12 | PRIORITY_GREEDY / PROPORTIONAL / max-clamp / unassigned_area populated |
| size_rooms (orchestrator) | ~15 | end-to-end; tier_resolution_accuracy enum coverage; multi-floor cases; grid-bay capture |
| failure_modes | ~15 | type checks; B-066; edge cases |
| **Subtotal — coverage** | | **~70** | |

**Combined estimate ≈ 120 tests**.

---

## § 8 — KB references

| KB | Status | Used for |
|---|---|---|
| `kb/nbc_room_minimums.json` | NEW v0.2 (rev. v0.4) | NBC 2016 dwelling-tiered table; rows include `source_confidence` per Walk #4 #6 |
| `kb/furniture_floor.json` | NEW v0.2 (rev. v0.3) | (category, is_master, bathroom_subtype) → (area_m2, min_width_m, reference_config) |
| `kb/room_targets.json` | NEW v0.3 | (category, is_master) → target_m2 |
| `kb/state_dcr_overrides.json` | stub; B-NNN-D | TNCDBR / Maharashtra DCR / KMC overrides |

**NBC clause provenance**: every row of `kb/nbc_room_minimums.json` carries `clause` and `source_confidence`. v1 ships with most rows at `SECONDARY_CONSENSUS` and one row (storeroom) at `SECONDARY_UNVERIFIED`. **B-150** (authoritative-PDF verification) lifts confidence to `VERIFIED` row-by-row when complete; LOCK is NOT blocked on B-150 per Walk #4 adjudication.

---

## § 9 — Out of scope

| Item | Backlog ID |
|---|---|
| State-DCR room-size overrides | B-NNN-D |
| Plot-tier-aware target sizing | B-NNN-B |
| Configurable priority order beyond v1 default | B-NNN-C |
| Multi-floor sizing coordination | B-NNN-E |
| Furniture KB versioning + per-room customization | B-NNN-F |
| Soft-fail mode + C2 retry contract | B-NNN-A |
| BR/BA pooling rules | B-NNN-I |
| Multi-floor dwelling-tier (whole-dwelling) | B-148 |
| Packing-efficiency tightening to ERROR mode | B-149 |
| NBC clause verification against authoritative PDF | B-150 |
| OTHER category subtype-driven sizing differentiation | B-151 |
| **Combined placement_risk_level signal** | **B-152 (NEW v0.4 per Walk #4 #9)** |
| Aspect ratio / shape constraints | C11 placement (Walk #4 #5 push-back) |
| Width-to-bay grid feasibility (full check) | C11 placement (Walk #3 #2 + Walk #4 #2 push-back) |
| Wall thickness deduction from envelope coords | C11 placement (Walk #4 #4 push-back) |
| Door swing clearance | C13 (Walk #4 #4 — door swings don't affect liveability_width) |
| Height enforcement | C11 (§ 14.22 / Walk #4 #10) |

---

## § 10 — Provenance — REVISED v0.4

`RoomSizingProvenance` carries:
- `derived_at`, `plot_analysis_trace_id`, `floor_label` — traceability
- `nbc_table_version`, `furniture_kb_version`, `targets_kb_version` — KB snapshots
- `dwelling_size_tier` + `tier_resolution_accuracy` (NEW v0.4) — tier determined; how exactly
- `grid_bay_min_m`, `grid_bay_max_m` (NEW v0.4) — grid-bay context for downstream debug
- `enforcement_mode`, `allocation_strategy`
- `surplus_distributed_m2`, `rooms_at_min`, `rooms_clamped_at_max`
- `packing_basis` — `"heuristic_v1_static_0.75"` until B-149
- `heuristic_packing_check_warning` — Inv 10 fired
- `early_width_infeasibility_warnings` (NEW v0.4) — room_ids that triggered Inv 17
- `grid_bay_max_warnings` (NEW v0.4) — room_ids that triggered Inv 18
- `rule_trace`

---

## § 11 — Spec metadata

- **Version**: v0.4 PROPOSED
- **Status**: PROPOSED — pending Ramalingam LOCK adjudication
- **Lineage**: v0.1 DRAFT → v0.2 PROPOSED → v0.3 PROPOSED → v0.4 PROPOSED (4 walks completed)
- **Authoring sessions**: S33 entire arc
- **Convergence signal**: walk #1 had 12 actionable; walk #2 had 13 overlap + 2 net-new; walk #3 had 4 overlap + 3 net-new + 2 push-backs; walk #4 had 3 overlap + 4 net-new + 2 push-backs + 1 backlog. New findings are decreasing in critical-severity; push-backs are increasing as architectural-layer separations are challenged. The 4-walk arc matches C8's spec discipline.

---

## § 12 — Backlog enumeration (preliminary; B-NNNs assigned at LOCK)

Total: **13 items** (was 12 in v0.3; +1 from Walk #4: B-152).

| ID | Title | Origin | Status | Trigger | S33-scope | Effort |
|---|---|---|---|---|---|---|
| B-NNN-A | Soft-fail mode + C2 retry | § 4.6 / Q8 | BACKLOG | C2 feasibility loop | OUT | M |
| B-NNN-B | Plot-tier-aware target sizing | § 4.3 | BACKLOG | Empirical signal | OUT | S |
| B-NNN-C | Configurable priority order | § 4.5 | BACKLOG | First user request | OUT | S |
| B-NNN-D | State DCR overrides | § 4.1 | BACKLOG | Municipality rejection | OUT | M |
| B-NNN-E | Multi-floor coordination | § scope | BACKLOG | C12 vertical alignment | OUT | L |
| B-NNN-F | Furniture KB versioning | § 4.2 | BACKLOG | Customization feature | OUT | M |
| B-NNN-I | Bath assignment rules | § 4.2 | BACKLOG | C11 placement | OUT | M |
| B-148 | Multi-floor dwelling-tier (whole-dwelling) | § 4.1 | BACKLOG | Multi-floor test case | OUT | M |
| B-149 | Packing-efficiency to ERROR | § 4.7 Inv 10 | BACKLOG | Calibration data | OUT | S |
| B-150 | NBC clause verification | § 4.1 / § 8 | BACKLOG | Verification pass complete | OUT | S |
| B-151 | OTHER subtype-driven sizing | § 9 / Walk #3 #9 | BACKLOG | First product feature | OUT | M |
| **B-152** | **Combined placement_risk_level signal** (NEW v0.4 per Walk #4 #9) | § 12 / Walk #4 | BACKLOG | C11/C14 want a derived risk metric beyond the individual WARN flags | OUT | S |
| (deferred to C11) | Aspect ratio / shape constraints | Walk #4 #5 | C11 spec | C11 build | OUT (out of C9 scope) | (in C11) |
| (deferred to C11) | Width-to-bay grid feasibility (full check) | Walk #3 #2 / Walk #4 #2 | C11 spec | C11 build | OUT (out of C9 scope) | (in C11) |
| (deferred to C11) | Wall thickness deduction from envelope | Walk #4 #4 | C11 spec | C11 build | OUT (out of C9 scope) | (in C11) |
| (deferred to C13) | Door swing clearance | Walk #4 #4 | C13 spec | C13 build | OUT (out of C9 scope) | (in C13) |
| (deferred to C11) | Height enforcement | Walk #4 #10 / § 14.22 | C11 spec | C11 build | OUT (out of C9 scope) | (in C11) |

---

## § 13 — Definitions

- **`regulatory_minimum`** *(v0.2; rev v0.4)*: NBC 2016 floor (area + width + height + clause + source_confidence). All three of area/width/height are NBC-mandated; source_confidence is a v0.4 honesty tag for the secondary-source provenance gap.
- **`liveability_min_area_m2`** *(v0.2)*: `max(regulatory.area_m2, furniture.area_m2)`.
- **`liveability_min_width_m`** *(v0.3; clarified v0.4)*: `max(regulatory.width_m, furniture.min_width_m)`. **Interior clear width** — wall thickness is added at C11 placement (§ 14.23).
- **`target_m2`** *(v0.2; KB-managed v0.3)*: comfortable size; from `kb/room_targets.json`.
- **`max_m2`** *(v0.2)*: waste threshold; per-category multipliers per § 4.4.
- **`buildable_envelope_minus_corridor_m2`** *(v0.2)*: from C8's `corridor_path.envelopes` total minus corridor area.
- **`DwellingSizeTier`** *(v0.2)*: NBC tier enum (SMALL ≤50 m² / LARGE >50 m²).
- **`TierResolutionAccuracy`** *(NEW v0.4)*: 3-state enum tagging how the tier was resolved (EXACT / APPROXIMATE_DEFENSIVE_LARGE / OVERRIDE_SUPPLIED). Replaces v0.3's binary `multi_floor_tier_warning`.
- **`is_master`** *(v0.2)*: True for BEDROOM_1 (and BATHROOM_1 if convention applies); drives `(category, is_master)` lookup.
- **`bathroom_subtype`** *(v0.3)*: COMBINED (default) / BATH_ONLY / WC_ONLY.
- **`other_subtype`** *(NEW v0.4)*: free-text echo of brief.other_rooms[i] for OTHER category. v1 does not differentiate sizing on this; B-151 lifts that.
- **`source_confidence`** *(NEW v0.4)*: enum tagging NBC value provenance quality (VERIFIED / SECONDARY_CONSENSUS / SECONDARY_UNVERIFIED).
- **`packing_efficiency`** *(v0.2)*: default 0.75. Heuristic ratio for Inv 10 WARN.
- **`packing_basis`** *(v0.3)*: provenance string. v1: `"heuristic_v1_static_0.75"`.
- **`unassigned_area_m2`** *(v0.3)*: explicit field for leftover envelope area after surplus allocation.
- **`grid_bay_min_m` / `grid_bay_max_m`** *(NEW v0.4)*: provenance fields capturing grid bay extremes at C9 entry.
- **`early_width_infeasibility_warnings`** *(NEW v0.4)*: tuple of room_ids that triggered Inv 17 (room width > envelope min-axis).
- **`grid_bay_max_warnings`** *(NEW v0.4)*: tuple of room_ids that triggered Inv 18 (room width > 2 × bay_max).
- **`PRIORITY_GREEDY` / `PROPORTIONAL`** *(v0.2)*: surplus-allocation strategies.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 DRAFT (carried)

§ 14.1 — Two-floor minimum (regulatory + liveability).
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

### From v0.3 PROPOSED

§ 14.12 — Liveability includes width, not just area (CRITICAL).
§ 14.13 — Multi-floor dwelling-tier handled defensively.
§ 14.14 — Width feasibility deferred to C11.
§ 14.15 — Heuristic_packing_check is a heuristic, not a guarantee.
§ 14.16 — Grid input rationale (v0.3): trace correlation + future B-148 + config-flagged grid-aware sizing.
§ 14.17 — `unassigned_area_m2` as explicit field.
§ 14.18 — Targets KB-managed.
§ 14.19 — Priority is first-class config.
§ 14.20 — Bathroom subtype is schema-explicit.
§ 14.21 — Secondary-source NBC disagreement is documented.

### NEW v0.4 (resolved per Walk #4)

§ 14.16-bis — **Grid input is now functionally consumed** (Walk #4 #3). Beyond the v0.3 trace-correlation rationale, v0.4 captures `grid_bay_min_m` and `grid_bay_max_m` in provenance and runs Inv 18 (WARN) — `liveability_min_width_m ≤ 2 × grid.bay_max_m` — as a sanity heuristic. Grid is no longer a "dummy input"; it earns its place in the input contract.

§ 14.22 — **Height enforcement is C11's responsibility** (Walk #4 #10). C9 stores `regulatory_minimum.height_m` (e.g., 2.75m for habitable rooms, 2.1m for bathrooms) but does NOT enforce. C11 placement enforces during volume validation. This matches the area/width pattern: C9 produces minimums, C11 satisfies them.

§ 14.23 — **`liveability_min_width_m` is interior clear width, not envelope-to-envelope** (Walk #4 #4). Walk #4 surfaced that wall thickness genuinely eats envelope-to-envelope width (typical 100-115mm Indian residential interior partitions). The decision is to keep C9 producing **interior clear width** and have C11 add wall thickness when laying out from envelope coordinates. This matches the area treatment (C9 produces carpet-area equivalents; C11 adds walls). Door swing clearance is irrelevant to room width (it's a floor-arc inside the room) and belongs to C13.

§ 14.24 — **NBC source confidence is exposed, not hidden** (Walk #4 #6). Until B-150 verifies all NBC values against the authoritative NBC 2016 PDF, every `RegulatoryMinimum` carries a `source_confidence` enum tag. Most rows are `SECONDARY_CONSENSUS` (multiple secondary sources agree); the storeroom row is `SECONDARY_UNVERIFIED`. LOCK is NOT blocked on B-150 — the alternative is indefinite C9 hold, which is worse than ship-with-honesty. Downstream consumers and end users can read the confidence flag and choose their tolerance.

§ 14.25 — **Tier resolution accuracy is a 3-state enum, not a binary flag** (Walk #4 #1). `TierResolutionAccuracy` (`EXACT` / `APPROXIMATE_DEFENSIVE_LARGE` / `OVERRIDE_SUPPLIED`) replaces v0.3's `multi_floor_tier_warning: bool`. The enum captures the actual semantic — including the case where the user explicitly supplied `dwelling_tier_override`, which v0.3 conflated with EXACT.

§ 14.26 — **Aspect ratio is C11 placement geometry, not C9 sizing** (Walk #4 #5 push-back). C9 produces area + min-width; depth and shape are placement decisions belonging to C11. Adding aspect-ratio constraints at C9 would make sizing depend on geometric placement, violating the C9-vs-C11 layer separation.

§ 14.27 — **Width is a constraint, not a target/max dimension** (Walk #4 #8 push-back). `target_m2` and `max_m2` are area-only because width is a *minimum* required for furniture-fit and NBC compliance, not a *quality optimization target*. A bedroom that exceeds liveability_min_width by 0.5m has placement flexibility but no quality benefit. Adding `target_width_m` would conflate constraint-satisfaction with quality, muddying the schema.

---

## § 15 — Open questions remaining

After 4 walks, the open-questions list has compressed substantially. v0.4's residual questions:

### Q13 (carried from v0.3) — Should `liveability_min_width_m` be required to be ≤ envelope's smaller axis?

**Resolution in v0.4**: Inv 17 (WARN) handles this. Not a hard check (v0.3 §14.14 deferred to C11), but a WARN-mode safety net. v0.4 closes this open question.

### Q14 (carried from v0.3) — Should max_m2 multipliers also live in `kb/room_targets.json`?

**Recommendation for LOCK**: yes; move to KB. Then user briefs can override via `RoomSizingConfig.targets_kb_override`. Decide at LOCK.

### NEW Q15 — At what trigger should B-150 (NBC clause verification) be elevated from optional to blocking?

If a regulator/inspector challenges a generated plan citing a specific clause C9 used, that's the event that forces verification. Until then, ship with confidence flag exposed.

**Recommendation for LOCK**: confirm "regulator challenge" as the trigger; B-150 effort is S; one-time verification pass.

---

## § 16 — End of v0.4 PROPOSED

Expected next: Ramalingam LOCK adjudication → build (D-066 step 6-8).

If LOCKED, the build session can begin immediately:
- 3 KB JSONs authored (`nbc_room_minimums.json`, `furniture_floor.json`, `room_targets.json`)
- ~7 production modules under `buildemup/components/c09/` (schema, nbc_table, furniture_floor, targets_kb, allocator, validator, room_sizer)
- ~120 tests authored matching § 7 invariant→test mapping

If walk #5 needed, walk happens on v0.4 PROPOSED. After 4 walks of converging discipline (3 → 4 → 3 → 3 actionable items per walk; 0 → 1 → 2 → 2 push-backs; no new HIGH-severity findings since walk #1), the next walk is likely cosmetic.
