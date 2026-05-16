# BuildemUp — C9 Room Sizer — SPEC v0.2 PROPOSED

**Status**: PROPOSED. PENDING walk #3 → LOCK adjudication. Per Rule 8, LOCK authority belongs to Ramalingam alone; this document represents the v0.2 candidate after walks #1 (Claude self-critique) and #2 (Ramalingam review).
**Component**: C9 of canonical 17-component v3 list (Track 3). Position 9. First sub-component pending in build order after C8.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C8 (`CorridorDesignedCandidate`) + C7 (`Grid`) + C4 (`PlotAnalysis`) + C1's `FloorRoomBrief`. Produces input for C10 (Bathroom + Wet-Zone Stack Planner) and C11 (Room Placement).
**Authoring sessions**: S33 v0.1 DRAFT + walk #1 + walk #2 + v0.2 PROPOSED.
**Predecessor**: v0.1 DRAFT (515 lines).

---

## § 0 — Why this spec, why now

After C8 SHIP at S32, the pipeline produces oriented topology candidates with refined zone bands (C6), structural grid (C7), and corridor geometry (C8). Downstream consumers (C10 wet-zone planner, C11 placement) need *room footprints with sizes assigned* — not just band envelopes. C9 sits between "the bands and corridor are designed" and "specific rooms have specific sizes."

C9's job: given the brief's room composition (`FloorRoomBrief.bedroom_count`, `bathroom_count`, `has_kitchen`, etc.), the band envelopes from C8's `CorridorPath.envelopes` (with the corridor area carved out), the structural grid bays, and the plot analysis, produce a `RoomSizeTable` — for each room, a `(regulatory_min, liveability_min, target, max)` quadruple **including width minima from NBC** that downstream placement components can satisfy.

C9 does NOT place rooms (that's C11). C9 does NOT generate furniture layouts (that's C14 furniture-fit metric). C9 does NOT decide adjacencies (that's C5/C11). C9 does NOT assign rooms to zone bands (that's C11 placement; v0.1 DRAFT incorrectly carried `consumption_band` per Walk #1 Finding #9 / Walk #2 Finding #6 — removed in v0.2). C9 does NOT score the resulting sizes (that's C14).

**The architectural distinction the project has been making**: NBC 2016 minimum is the **regulatory floor**; furniture-fit minimum is the **liveability floor**. v1 C9 produces both — `liveability_min = max(regulatory_min, furniture_floor)` — so downstream consumers can choose to enforce either. The "liveability gap" identified in the v3 architecture (NBC-compliant rooms can still be unlivable) is closed at this layer.

**v0.2 lineage delta from v0.1 DRAFT** (12 spec edits per walks #1 + #2):

| # | Edit | Source | § affected |
|---|---|---|---|
| 1 | Type fix: `StructuralGrid` → `Grid` | Walk #1 #1 | § 2 |
| 2 | Optional rooms (LIVING/KITCHEN/BATHROOM=0) handled | Walk #1 #2 + #3 / Walk #2 #3 + #14 | § 3, § 4.7 |
| 3 | NBC numbers corrected (kitchen, bathroom) | Walk #1 #4 + #5 / Walk #2 #1 | § 4.1 |
| 4 | Schema enriched: `is_master`, regulatory triple | Walk #1 #8 + #11 / Walk #2 #4 + #5 + #2 | § 3 |
| 5 | `consumption_band` field DROPPED | Walk #1 #9 / Walk #2 #6 | § 3, § 4.7 |
| 6 | `max_m2` per-category multipliers consistent | Walk #1 #13 / Walk #2 #9 | § 4.4 |
| 7 | Q1 + Q4 resolved (FloorRoomBrief direct, is_master implicit) | Walk #1 #6 + #7 / Walk #2 #5 + #12 | § 14 |
| 8 | `floor_label` propagated to provenance | Walk #1 #10 / Walk #2 #10 | § 10 |
| 9 | Test plan: invariant→test mapping table | Walk #1 #15 / Walk #2 #11 | § 7 |
| 10 | NBC clauses pinned or marked uncertain | Walk #1 #12 / Walk #2 #13 | § 4.1, § 8 |
| 11 | Dwelling-tier resolution from C8 envelopes | Walk #2 #7 (NEW; sharpened walk #1 NBC tier finding) | § 4.1, § 14 |
| 12 | Packing-efficiency invariant added (WARN mode) | Walk #2 #15 (NEW) | § 4.7 invariant 7b, § 14 |

---

## § 1 — Purpose

Given a C8-corridor-designed candidate, the brief's room composition, the structural grid bays, and the plot analysis, produce a **`RoomSizeTable`** — for each requested room (bedroom × N, bathroom × M, optional kitchen, optional living, optional pooja, optional utility, plus brief-defined `other_rooms`):
- regulatory floor (area, width, height) per NBC 2016 dwelling tier
- liveability minimum size
- target size
- max size

The total of all liveability-min sizes must fit within the buildable envelope minus the corridor area (Inv 7); a *packing-efficiency* warning fires if the total approaches the envelope without typical wall/clearance slack (Inv 7b WARN mode). If it does not fit, raise a typed `RoomSizingInfeasibleError(B-NNN-A)` with the deficit named.

Cardinality preserved: 1-3 C8 candidates → 1-3 C9 candidates, position-paired.

**Out of scope for C9** (intentionally not addressed):
- Room placement (XY positioning) — C11
- Adjacency / connectivity — C5 selected, C11 enforces
- Zone band assignment for rooms — C11 placement
- Furniture layout — C14 furniture-fit metric (consumes C9's sizes as input, not the reverse)
- Door placement, swing direction — C13
- Wet-wall back-to-back stacking — C10
- Vertical alignment across floors — C12
- Cost computation — C14 cost metric
- Surfaces, finishes, MEP — out of v1 entirely

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

`RoomSizingConfig` carries per-call tunables: enforcement mode (`STRICT` / `WARN`), Neufert/Ching multipliers, allocation strategy (`PRIORITY_GREEDY` / `PROPORTIONAL`), `packing_efficiency` (default 0.75), `dwelling_tier_override` (None = derived from C8). Defaults baked into the dataclass mean callers can omit it entirely.

**FloorRoomBrief is passed directly, not threaded onto `CorridorDesignedCandidate`** (resolved Walk #1 Q1 / Walk #2 #12). Rationale: C8's `CorridorDesignedCandidate` is corridor geometry; threading the brief onto it would mix concerns. C9 is the first component that explicitly consumes the brief's room composition. Direct injection mirrors C4's `Plot` parameter pattern.

---

## § 3 — Output schema

```python
class RoomCategory(str, Enum):
    """The 6 v1 room categories. Mirrors C6's FunctionRole values.

    Master-vs-typical bedroom is NOT a separate category (resolved Walk #1
    Q4 / Walk #2 #5). The role is expressed via the `is_master: bool` flag
    on RoomSizeRequirement; category enum stays clean.
    """
    BEDROOM    = "bedroom"      # Bedrooms enumerated by count → BEDROOM_1, BEDROOM_2, ...
    BATHROOM   = "bathroom"     # Likewise; BATHROOM_1 may be MASTER (if is_master=True)
    LIVING     = "living"       # Singular — at most one per floor; present iff brief.has_living
    KITCHEN    = "kitchen"      # Singular — at most one per floor; present iff brief.has_kitchen
    POOJA      = "pooja"        # Optional (per FloorRoomBrief.has_pooja)
    UTILITY    = "utility"      # Optional (per FloorRoomBrief.has_utility)
    OTHER      = "other"        # FloorRoomBrief.other_rooms entries; pooled here in v1


class DwellingSizeTier(str, Enum):
    """NBC 2016 dwelling-size tiers per Part 3 Clauses 12.1-12.4.

    NBC numbers vary by dwelling-unit total floor area:
    - SMALL: dwelling ≤ 50 m² → smaller habitable floors, smaller kitchen,
      narrower habitable widths
    - LARGE: dwelling > 50 m² → standard habitable floors

    Tier resolved from C8 envelopes per § 4.1 (sum of band envelope areas
    on this floor), unless config.dwelling_tier_override is supplied.

    For multi-floor briefs (G+1 / G+2), v1 uses the per-floor area as proxy
    for the whole-dwelling tier; threading the actual whole-dwelling area
    is filed as B-148.
    """
    SMALL = "small"   # dwelling ≤ 50 m²
    LARGE = "large"   # dwelling > 50 m²


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
                                     # Or "v0.2 unverified clause" when source is uncertain


@dataclass(frozen=True)
class RoomSizeRequirement:
    """Per-room sizing requirement.

    For each room R:
      - regulatory_minimum: NBC 2016 floor; cannot be deducted from
      - liveability_min_m2: max(regulatory.area_m2, furniture_floor_m2)
      - target_m2: comfortable size for typical Indian use
      - max_m2: above which area is wasted (used to clamp surplus distribution)

    Invariants (asserted at construction):
      - 0 < regulatory_minimum.area_m2 ≤ liveability_min_m2 ≤ target_m2 ≤ max_m2
      - regulatory_minimum carries area + width + height (all NBC)
      - is_master is True only on BEDROOM_1 (and BATHROOM_1 if convention applies)
    """
    room_id: str                                    # e.g. "BEDROOM_1", "BATHROOM_2", "KITCHEN"
    category: RoomCategory                          # enum
    regulatory_minimum: RegulatoryMinimum           # NBC triple (area + width + height)
    liveability_min_m2: float                       # max(reg_min.area, furniture_min)
    target_m2: float                                # Neufert/Ching comfortable
    max_m2: float                                   # waste threshold
    priority: int                                   # 1 = highest, used for surplus allocation
    is_master: bool = False                         # NEW v0.2 (Walk #1 #8 / Walk #2 #4):
                                                     # True for BEDROOM_1 (and BATHROOM_1 by
                                                     # convention when bath_count ≥ 1 AND bed_count ≥ 1).
                                                     # Drives furniture lookup: (category, is_master)
                                                     # selects the right row of kb/furniture_floor.json.
    # NB: consumption_band field DROPPED in v0.2 (Walk #1 #9 / Walk #2 #6) —
    # band assignment is C11 placement's job, not C9's.


@dataclass(frozen=True)
class RoomSizeTable:
    """The complete sizing for one C8 candidate's floor.

    Rooms are enumerated by FloorRoomBrief: bedroom_count → BEDROOM_1...N,
    bathroom_count → BATHROOM_1...M (BATHROOM_1 conventionally master-attached
    if bedroom_count ≥ 1; BATHROOM_1.is_master = True iff master-attached
    convention applies). Conditional inclusion: LIVING iff has_living=True;
    KITCHEN iff has_kitchen=True; POOJA iff has_pooja=True; UTILITY iff has_utility=True.

    Invariants (asserted at construction):
      - rooms is non-empty
      - room_ids unique
      - Σ liveability_min_m2 ≤ buildable_envelope_minus_corridor_m2 (Inv 7)
      - Σ liveability_min_m2 ≤ envelope × packing_efficiency (Inv 7b WARN; not raise)
      - Σ target_m2 may exceed envelope (surplus-allocation absorbs slack)
      - every category counts match brief (count(BEDROOM)==brief.bedroom_count;
        count(LIVING)==1 iff brief.has_living else 0; etc.)
      - exactly one BEDROOM has is_master=True iff bedroom_count ≥ 1
    """
    rooms: tuple[RoomSizeRequirement, ...]
    buildable_envelope_minus_corridor_m2: float     # available area
    dwelling_size_tier: DwellingSizeTier            # NEW v0.2: which NBC tier was used
    total_liveability_min_m2: float                 # Σ liveability_min
    total_target_m2: float                          # Σ target
    surplus_for_distribution_m2: float              # envelope − Σ liveability_min
    packing_efficiency_used: float                  # NEW v0.2: which packing factor was applied


@dataclass(frozen=True)
class RoomSizingProvenance:
    """Provenance for one C9 sizing pass."""
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str                                # NEW v0.2 (Walk #1 #10 / Walk #2 #10):
                                                     # propagated from FloorRoomBrief.floor_label
                                                     # so multi-floor debugging can identify which
                                                     # floor a sizing decision came from.
    nbc_table_version: str                          # which NBC table snapshot
    furniture_kb_version: str                       # which Neufert/Ching snapshot
    dwelling_size_tier: DwellingSizeTier            # tier that drove regulatory lookup
    enforcement_mode: str                           # STRICT | WARN
    allocation_strategy: str                        # PRIORITY_GREEDY | PROPORTIONAL
    surplus_distributed_m2: float                   # post-allocation
    rooms_at_min: tuple[str, ...]                   # IDs that got only liveability_min
    rooms_clamped_at_max: tuple[str, ...]           # IDs that hit max_m2
    packing_efficiency_warning: bool                # NEW v0.2: True if Inv 7b WARN fired
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

### § 4.1 — Regulatory minimums (NBC 2016 KB) — REVISED v0.2

NBC 2016 Part 3 numbers are **dwelling-tiered**: smaller dwellings have looser numerics for habitable rooms; larger dwellings get the standard floor. This was Walk #2 Finding #7 (sharpening Walk #1 Findings #4 + #5).

**Source-of-truth table for v1** (per Walk #1 + Walk #2 web research, S33; consensus across NBC 2016 Part 3 Clauses 12.1-12.4 as cited in the slideshare bye-laws table, the InfraLens NBC reference, and the Wadhwa NBC summary):

#### Dwelling tier: SMALL (dwelling ≤ 50 m²)

| Category | NBC area m² | NBC width m | NBC height m | NBC clause |
|---|---|---|---|---|
| BEDROOM (habitable, 1 of 2 in dwelling) | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.2.2 |
| BEDROOM (habitable, single-room dwelling) | 9.5 | 2.4 | 2.75 | NBC 2016 Part 3 Clause 12.2.1 |
| LIVING (habitable) | 7.5 (smaller-of-2) / 9.5 (single-room) | 2.1 / 2.4 | 2.75 | same |
| KITCHEN (separate) | 3.3 | 1.8 | 2.75 | NBC 2016 Part 3 Clause 12.3.1 |
| KITCHEN-cum-DINING | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.3.2 |
| BATHROOM (no WC) | 1.2 | 1.0 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| WC (no bath) | 1.0 | 0.9 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| BATHROOM + WC (combined) ★ | 1.8 | 1.0 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| POOJA | (not habitable; no NBC floor) | — | 2.1 | (none) |
| UTILITY (storeroom) | 3.2 | (no width minimum cited) | 2.2 | NBC 2016 Part 3 (clause v0.2 unverified; see § 8) |

★ = v1 default for "BATHROOM" room category, since combined Bath+WC is the typical Indian residential interior bathroom configuration.

#### Dwelling tier: LARGE (dwelling > 50 m²)

| Category | NBC area m² | NBC width m | NBC height m | NBC clause |
|---|---|---|---|---|
| BEDROOM (habitable) | 9.5 | 2.4 | 2.75 | NBC 2016 Part 3 Clause 12.1.1 |
| LIVING (habitable) | 9.5 | 2.4 | 2.75 | same |
| KITCHEN (separate) | 4.5 | 1.8 | 2.75 | NBC 2016 Part 3 Clause 12.3.1 |
| KITCHEN-cum-DINING | 7.5 | 2.1 | 2.75 | NBC 2016 Part 3 Clause 12.3.2 |
| BATHROOM (no WC) | 1.8 | 1.2 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| WC (no bath) | 1.2 | 0.9 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| BATHROOM + WC (combined) ★ | 2.8 | 1.2 | 2.1 | NBC 2016 Part 3 Clause 12.4 |
| POOJA | (not habitable; no NBC floor) | — | 2.1 | (none) |
| UTILITY (storeroom) | 3.2 | (no width minimum cited) | 2.2 | NBC 2016 Part 3 (clause v0.2 unverified; see § 8) |

★ = v1 default for "BATHROOM" room category.

#### Dwelling-tier resolution (Walk #2 Finding #7)

C9 derives the dwelling tier from the C8 envelope total per floor:

```python
def _resolve_dwelling_tier(
    candidate: CorridorDesignedCandidate,
    config: RoomSizingConfig,
) -> DwellingSizeTier:
    if config.dwelling_tier_override is not None:
        return config.dwelling_tier_override
    envelope_areas = sum(e.area_m2 for e in candidate.corridor_path.envelopes)
    return DwellingSizeTier.SMALL if envelope_areas <= 50.0 else DwellingSizeTier.LARGE
```

**Multi-floor caveat**: NBC's dwelling-size threshold (50 m²) refers to the *whole dwelling unit* across all floors. v1 uses per-floor area as proxy. For multi-floor briefs (G+1, G+2), this *under-tiers* the rooms (a 60-m² total dwelling split as 30+30 reads as SMALL on each floor instead of LARGE for the whole). Filed as **B-148** for cross-component fix when multi-floor briefs become common.

These values live in `kb/nbc_room_minimums.json` (matches existing C7 KB pattern). Versioned via `nbc_table_version`.

**State-DCR overrides** (B-NNN-D, deferred): TNCDBR (Tamil Nadu), MH-DCR (Maharashtra), KMC (Karnataka) byelaws override NBC defaults. v1 ignores these; first DCR-mismatch trigger filing.

### § 4.2 — Liveability minimums (furniture-fit floor)

For each `(category, is_master)` tuple, a furniture-floor area is computed from a reference furniture configuration. v1 uses static defaults (per architecture-v2 Component 9 worked example) cached in `kb/furniture_floor.json`:

| Category | is_master | Furniture-floor m² | Reference configuration |
|---|---|---|---|
| BEDROOM | False | 9.3 m² (~100 sqft) | Single bed 0.9 × 2.0 + study 1.2 × 0.6 + wardrobe 1.2 × 0.6 + 0.75 m clearance |
| BEDROOM | True (BEDROOM_1) | 13.0 m² (~140 sqft) | Queen 1.5 × 2.0 + 2 side tables + wardrobe + 0.9 m clearance |
| LIVING | False | 16.7 m² (~180 sqft) | 3-seat sofa + 2 chairs + coffee table + circulation |
| KITCHEN | False | 7.9 m² (~85 sqft) | L-counter 3.0 m run + fridge + 1.2 m work aisle |
| BATHROOM | False | 2.8 m² (~30 sqft) | Shower 0.9 × 0.9 + WC + sink + 0.6 m clearance |
| BATHROOM | True (BATHROOM_1 if master-attached) | 4.0 m² (~43 sqft) | + tub-or-larger-shower + double sink |
| POOJA | False | 2.8 m² (~30 sqft) | Altar 0.6 × 0.9 + seated prayer + storage cabinet |
| UTILITY | False | 2.8 m² (~30 sqft) | Washing machine + sink + storage |

`liveability_min_m2 = max(regulatory_minimum.area_m2, furniture_floor_m2)`. For BEDROOM (LARGE tier, typical), this resolves to max(9.5, 9.3) = 9.5 m² (regulatory wins by 0.2). For master BEDROOM_1 (LARGE tier), max(9.5, 13.0) = 13.0 m² (furniture wins). For LIVING (LARGE tier), max(9.5, 16.7) = 16.7 m² (furniture wins decisively). For BATHROOM (LARGE tier, combined Bath+WC), max(2.8, 2.8) = 2.8 m² (regulatory and furniture coincident).

### § 4.3 — Target sizes

Per architecture-v2 Component 9 worked example (NE 30×40 reference plan), `target_m2` per `(category, is_master)`:

| Category | is_master | Target m² | Source |
|---|---|---|---|
| BEDROOM | False | 10.2 (~110 sqft) | architecture-v2 § 5 |
| BEDROOM | True | 14.9 (~160 sqft) | architecture-v2 § 5 |
| LIVING | False | 18.6 (~200 sqft) | architecture-v2 § 5 |
| KITCHEN | False | 9.3 (~100 sqft) | architecture-v2 § 5 |
| BATHROOM | False | 3.3 (~35 sqft) | architecture-v2 § 5 |
| BATHROOM | True | 4.2 (~45 sqft for master-attached) | architecture-v2 § 5 |
| POOJA | False | 3.3 (~35 sqft) | architecture-v2 § 5 |
| UTILITY | False | 3.7 (~40 sqft) | architecture-v2 § 5 |

**Plot-tier-aware target sizing** (B-NNN-B, deferred): T1/T2/T3 plot tiers may warrant scaled targets; v1 holds them fixed.

### § 4.4 — Max sizes (waste threshold) — REVISED v0.2

Per-category multipliers (consistency fix per Walk #1 #13 / Walk #2 #9; the previous "1.6 × target with 26 m² bedroom cap" mention had self-contradictory baselines):

| Category | is_master | max_m2 multiplier | Resulting cap | Rationale |
|---|---|---|---|---|
| BEDROOM | False | 1.6 × target | 1.6 × 10.2 = 16.3 m² | "1.6× target" v3 design principle |
| BEDROOM | True | 1.6 × target | 1.6 × 14.9 = 23.8 m² | same — master cap is the *master target × 1.6*, not a separate 26m² |
| LIVING | False | 2.5 × target | 2.5 × 18.6 = 46.5 m² | living rooms benefit from generosity; relaxed cap |
| KITCHEN | False | 1.6 × target | 1.6 × 9.3 = 14.9 m² | |
| BATHROOM | False | 1.6 × target | 1.6 × 3.3 = 5.3 m² | |
| BATHROOM | True | 1.6 × target | 1.6 × 4.2 = 6.7 m² | master-attached cap |
| POOJA | False | 1.6 × target | 1.6 × 3.3 = 5.3 m² | |
| UTILITY | False | 1.6 × target | 1.6 × 3.7 = 5.9 m² | |

The previous DRAFT's "Bedrooms cap at ~26 m²" mention is dropped — that was a typical-bedroom-target × 1.6 ≈ 26 misconception. The corrected per-category multipliers above are internally consistent.

### § 4.5 — Surplus allocation

After computing `liveability_min` for each room, `surplus_m2 = buildable_envelope_minus_corridor_m2 - Σ liveability_min`. Distribution algorithm (unchanged from v0.1 DRAFT):

```python
def distribute_surplus(rooms, surplus_m2, strategy):
    """Allocate surplus_m2 among rooms, capped at max_m2.

    Strategy PRIORITY_GREEDY (default v1; per architecture-v1's "splitter
    always protects the more important room first"):
      1. Sort rooms by priority ascending (1 = highest).
      2. For each room in order, give it as much as possible up to target_m2.
      3. After all rooms reach target, distribute remaining surplus capped at max_m2.
      4. Any leftover surplus stays unassigned (will be treated as "slack" by
         downstream placement; could become balcony, courtyard expansion, etc.).

    Strategy PROPORTIONAL (alternative for walk consideration):
      Allocate proportionally to priority weights. Less surgical but smoother
      transitions across plot sizes.

    Returns: per-room target_m2 (each capped at max_m2).
    """
```

Default priority order (v1):
1. BEDROOM_1 (is_master=True) — highest
2. BEDROOM_2..N (is_master=False)
3. KITCHEN (if present)
4. LIVING (if present)
5. BATHROOM_1 (master-attached if applicable)
6. BATHROOM_2..M
7. POOJA (if present)
8. UTILITY (if present)
9. OTHER (pooled)

Conditional inclusion (per Walk #1 #2 + #3 / Walk #2 #3 + #14): the priority list compacts gracefully when optional rooms are absent. If `brief.has_living=False`, LIVING is skipped from the list (no priority gap). If `brief.bathroom_count == 0`, the BATHROOM rows drop out and BATHROOM_1.is_master semantics never apply.

### § 4.6 — Infeasibility detection

If `Σ liveability_min_m2 > buildable_envelope_minus_corridor_m2`, raise `RoomSizingInfeasibleError(B-NNN-A)` with deficit named (unchanged from v0.1 DRAFT).

```
RoomSizingInfeasibleError: this floor's liveability_min total (74.6 m²)
exceeds buildable envelope minus corridor (66.0 m²) by 8.6 m². Specific:
  BEDROOM_1: 13.0 m² (master)
  BEDROOM_2: 9.5 m²
  BEDROOM_3: 9.5 m²
  LIVING:    16.7 m²
  KITCHEN:    7.9 m²
  BATHROOM_1: 4.0 m² (master)
  BATHROOM_2: 2.8 m²
  POOJA:      2.8 m²
  UTILITY:    2.8 m²
  Σ:         77.0 m²
Deficit: 11.0 m² (from 66.0 m² envelope-minus-corridor). Options:
  (a) Drop BEDROOM_3 (saves 9.5 m²) — but brief specified 3 bedrooms.
  (b) Reduce BEDROOM_1 to non-master spec (saves 3.5 m²) — partial.
  (c) Split across two floors (request a multi-floor brief).
  (d) Increase plot size or relax setbacks.

Caller must escalate to C2 feasibility renegotiation or surface to user.
```

Hard-fail is deliberate per Pattern A (resolved Walk #1 #14 / Walk #2 #8). C2 retry contract is undefined as of S33 and would require coordinated C2+C9 spec amendment when soft-fail mode is needed (filed as B-NNN-A reframed: "B-NNN-soft-fail-cross-component").

### § 4.7 — Validator invariants — REVISED v0.2

| # | Invariant | Source | Mode |
|---|---|---|---|
| 1 | rooms.count == FloorRoomBrief-derived total count (with conditional inclusion) | Walk #1 #2 / Walk #2 #3 | RAISE |
| 2 | category counts match brief (BEDROOM count == brief.bedroom_count; LIVING count == 1 iff brief.has_living else 0; etc.) | brief consistency | RAISE |
| 3 | every regulatory_minimum.area_m2 ≥ NBC 2016 table value for resolved tier | NBC compliance | RAISE |
| 4 | every regulatory_minimum.width_m ≥ NBC 2016 table value (NEW v0.2 per Walk #1 #11 / Walk #2 #2) | NBC compliance | RAISE |
| 5 | every regulatory_minimum.height_m ≥ NBC 2016 table value (NEW v0.2 per Walk #1 #11 / Walk #2 #2) | NBC compliance | RAISE |
| 6 | every liveability_min_m2 ≥ regulatory_minimum.area_m2 | math | RAISE |
| 7 | every target_m2 ≥ liveability_min_m2 | math | RAISE |
| 8 | every max_m2 ≥ target_m2 | math | RAISE |
| 9 | Σ liveability_min_m2 ≤ buildable_envelope_minus_corridor_m2 | feasibility | RAISE |
| 10 | Σ liveability_min_m2 ≤ envelope × packing_efficiency (default 0.75) (NEW v0.2 per Walk #2 #15) | placement-readiness | **WARN** (logged to provenance; not raised) |
| 11 | room_ids are unique | data integrity | RAISE |
| 12 | priority values cover 1..n contiguously (no gaps after conditional skipping) | well-formedness | RAISE |
| 13 | exactly one BEDROOM has is_master=True iff bedroom_count ≥ 1 (NEW v0.2 per Walk #1 #8 / Walk #2 #4) | master semantics | RAISE |
| 14 | at most one BATHROOM has is_master=True | master semantics | RAISE |

**Inv 10 (packing-efficiency) — WARN MODE rationale**: Pattern A discipline says fail at the boundary, not silently degrade. But over-strict packing-efficiency check would false-positive-reject feasible plans where downstream C11 placement could succeed. Solution: log a `packing_efficiency_warning=True` to provenance + add `tight_packing` to `rule_trace`, but don't raise. C11 will catch the truly-unplaceable cases at its placement-geometry validator. Calibration data over time will inform whether to tighten Inv 10 to RAISE (filed as **B-149**).

**Inv 4 + Inv 5 — width/height enforcement**: a 9.5 m² room at 1.5 m × 6.3 m fails NBC width even though it meets NBC area. v1 enforces all three (area, width, height) at C9. C11 placement consumes all three (C11 must produce a layout where the resulting room geometry meets all three minimums).

**~~Inv 10 of v0.1 DRAFT (consumption_band valid enum)~~**: DROPPED in v0.2 (Walk #1 #9 / Walk #2 #6) since `consumption_band` field was removed from RoomSizeRequirement.

### § 4.8 — Order-of-checks

Type checks first → shape check (B-066 non-rectangular plot) → brief sanity (bedroom_count ≥ 1, bathroom_count ≥ 0, has_kitchen | has_living etc.) → dwelling-tier resolution → per-candidate regulatory lookup → liveability resolution → infeasibility check → surplus allocation → validator (full invariant sweep). Pattern A: fail at boundary, not deep in sizing.

---

## § 5 — Invocation contract (public)

```python
sized = size_rooms(
    corridor_designed_candidates=c8_output,
    floor_room_brief=c1_brief.floors[0],   # for ground floor; multi-floor briefs loop
    grid=c7_grid,                           # v0.2: type is Grid (was StructuralGrid)
    plot_analysis=c4_plot_analysis,
)  # config defaults are fine for v1
```

Cardinality: 1-3 in → 1-3 out, position-paired (matches C6/C8 pattern).

---

## § 6 — Failure modes — REVISED v0.2

| Condition | Behavior |
|---|---|
| `corridor_designed_candidates` not a tuple | `TypeError` |
| `floor_room_brief` not FloorRoomBrief | `TypeError` |
| `grid` not Grid (v0.2 fix) | `TypeError` |
| `plot_analysis` not PlotAnalysis | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066, mirrors C6) |
| `plot_analysis.climate_zone` is HOT_DRY or COLD | passes through; v1 has no climate-dependent sizing |
| Brief specifies 0 bedrooms | `ValueError` (caller bug; brief should always specify ≥ 1 bedroom) |
| Brief specifies 0 bathrooms (NEW v0.2 — Walk #1 #3 / Walk #2 #14) | passes through; resulting table has 0 bathrooms; BATHROOM_1.is_master semantics never apply |
| Brief specifies has_living=False | passes through; LIVING absent from table |
| Brief specifies has_kitchen=False | passes through; KITCHEN absent from table |
| Σ liveability_min > envelope (Inv 9) | `RoomSizingInfeasibleError` (B-NNN-A) |
| Σ liveability_min > envelope × packing_efficiency (Inv 10) | log to provenance; no raise |
| One room category's NBC table entry missing for resolved tier | `KeyError` (caller-side KB integrity issue) |
| Empty input tuple | Returns empty tuple |

**Order-of-checks**: type checks → shape → brief sanity → dwelling-tier → regulatory → liveability → infeasibility → surplus → validator.

---

## § 7 — Test plan — REVISED v0.2

Following C5/C6/C8 pattern. v0.2 targets ~100 tests with explicit invariant→test mapping (Walk #1 #15 / Walk #2 #11):

### Invariant coverage

| Inv # | Invariant | Test count | Test file |
|---|---|---|---|
| 1 | rooms.count == brief total (with conditionals) | 6 | test_c9_schema.py |
| 2 | category counts match brief | 8 | test_c9_schema.py |
| 3 | regulatory.area ≥ NBC value (per tier) | 10 | test_c9_nbc_table.py |
| 4 | regulatory.width ≥ NBC value | 8 | test_c9_nbc_table.py |
| 5 | regulatory.height ≥ NBC value | 6 | test_c9_nbc_table.py |
| 6 | liveability_min ≥ regulatory.area | 4 | test_c9_schema.py |
| 7 | target ≥ liveability_min | 4 | test_c9_schema.py |
| 8 | max ≥ target | 4 | test_c9_schema.py |
| 9 | Σ liveability_min ≤ envelope (RAISE) | 6 | test_c9_orchestrator.py |
| 10 | Σ liveability_min ≤ envelope × packing_efficiency (WARN) | 4 | test_c9_orchestrator.py |
| 11 | room_ids unique | 3 | test_c9_schema.py |
| 12 | priority contiguous after conditionals | 4 | test_c9_schema.py |
| 13 | exactly one BEDROOM is_master if bed_count ≥ 1 | 4 | test_c9_schema.py |
| 14 | at most one BATHROOM is_master | 4 | test_c9_schema.py |
| **Subtotal — invariants** | | **75** | |

### Module-coverage

| Module | Tests | Focus |
|---|---|---|
| nbc_table.py | ~12 (above 10+8+6=24 covers some) | dwelling-tier resolution; clause coverage |
| furniture_floor.py | ~8 | (category, is_master) tuple lookup |
| allocator.py | ~12 | PRIORITY_GREEDY / PROPORTIONAL / max-clamp / leftover surplus |
| size_rooms (orchestrator) | ~15 | end-to-end on bangalore_40x60 / chennai-30x40 / delhi_60x90 |
| failure_modes | ~15 | type checks; B-066; bathroom_count=0; has_living=False; infeasibility |
| **Subtotal — coverage tests** | | **~62** | |

**Combined estimate ≈ 100 tests** (some invariant tests double as module-coverage tests; deduplication brings the unique count to ~100).

---

## § 8 — KB references

| KB | Status | Used for |
|---|---|---|
| `kb/nbc_room_minimums.json` | **NEW v0.2** | NBC 2016 dwelling-tiered table (SMALL/LARGE) with area + width + height + clause |
| `kb/furniture_floor.json` | **NEW v0.2** | (category, is_master) → furniture-floor m² + reference configuration |
| `kb/state_dcr_overrides.json` | **stub; B-NNN-D** | TNCDBR / Maharashtra DCR / KMC overrides on NBC defaults |

**NBC clause provenance** (Walk #1 #12 / Walk #2 #13): each row of `kb/nbc_room_minimums.json` carries a `clause` field. Verified clauses (12.1.1, 12.2.1, 12.2.2, 12.3.1, 12.3.2, 12.4) are tagged "verified-via-bye-laws-table-S33". Unverified clauses (storeroom in NBC Part 3 — clause number not found in Walk #1/#2 web sources) are tagged "v0.2 unverified clause" and filed as **B-150** for direct verification against a reviewed copy of NBC 2016 Part 3.

---

## § 9 — Out of scope

| Item | Backlog ID |
|---|---|
| State-DCR room-size overrides (TNCDBR, MH-DCR, KMC) | B-NNN-D |
| Plot-tier-aware target sizing (T1/T2/T3 differential) | B-NNN-B |
| Configurable priority order beyond v1 default | B-NNN-C |
| ~~Width-minimum check (NBC's 2.4 m habitable-room width)~~ MOVED into spec body per Walk #1 #11 | (removed from backlog) |
| Multi-floor sizing coordination (master on FF, kids on GF, etc.) | B-NNN-E |
| Furniture KB versioning + per-room user customization | B-NNN-F |
| Soft-fail mode (return reduced count + warning instead of raise) — cross-component dependency on C2 | B-NNN-A (was-Q8) |
| BR/BA pooling rules (master-attached vs common bath assignment) | B-NNN-I |
| Multi-floor dwelling-tier resolution (whole-dwelling vs per-floor) | **B-148** (NEW v0.2) |
| Packing-efficiency tightening to ERROR mode after calibration | **B-149** (NEW v0.2) |
| NBC clause verification (storeroom, etc., for clauses not pinned in S33 web research) | **B-150** (NEW v0.2) |

---

## § 10 — Provenance

`RoomSizingProvenance` carries:
- `derived_at`, `plot_analysis_trace_id` — traceability
- `floor_label` (NEW v0.2) — which floor of multi-floor brief produced this
- `nbc_table_version`, `furniture_kb_version` — KB-snapshot identification
- `dwelling_size_tier` (NEW v0.2) — which tier drove regulatory lookup
- `enforcement_mode` (`STRICT` / `WARN`) — gate behavior
- `allocation_strategy` (`PRIORITY_GREEDY` / `PROPORTIONAL`) — algorithm choice
- `surplus_distributed_m2` — total redistribution
- `rooms_at_min` — IDs that got only liveability_min (no surplus)
- `rooms_clamped_at_max` — IDs that hit max_m2 cap
- `packing_efficiency_warning` (NEW v0.2) — True if Inv 10 fired in WARN mode
- `rule_trace` — debugging

---

## § 11 — Spec metadata

- **Version**: v0.2 PROPOSED
- **Status**: PROPOSED — pending walk #3 → LOCK adjudication. Per Rule 8, LOCK belongs to Ramalingam.
- **Lineage**: v0.1 DRAFT → v0.2 PROPOSED (12 spec edits per Walks #1 + #2)
- **Authoring sessions**: S33 (DRAFT + walks + PROPOSED)
- **Companion artifacts**: Walk #1 critique (`35_C9_walk_1_spec_fidelity.md`), Walk #2 reviewer round (chat-delivered S33), web research grounding for NBC clauses + carpet-area efficiency.

---

## § 12 — Backlog enumeration (preliminary; B-NNNs assigned at LOCK)

Total: **11 items** (was 9 in v0.1 DRAFT; +2 new from Walk #2 + 1 new from clause-verification need; -1 moved into spec body).

### B-NNN-A — Soft-fail mode + C2 retry dialogue (REFRAMED v0.2)
**Origin**: § 4.6 / Q8. Reframed as cross-component dependency: requires C2 spec amendment to consume C9's infeasibility verdict and renegotiate the brief.
**Status**: BACKLOG (deferred design dialogue with C2).
**Trigger**: C2's feasibility loop needs to consume C9's verdict.
**Effort**: M (interface change; depends on C2 contract).

### B-NNN-B — Plot-tier-aware target sizing
**Origin**: § 4.3. Target sizes are fixed in v1; T3 plots could comfortably support larger rooms.
**Status**: BACKLOG.
**Trigger**: Empirical signal (≥ 5 user reports of "rooms feel too small on big plots").
**Effort**: S.

### B-NNN-C — Configurable priority order
**Origin**: § 4.5. v1 default is master-bedroom-first.
**Status**: BACKLOG (RoomSizingConfig already accepts override; tests cover only default).
**Trigger**: First user request for non-default ordering.
**Effort**: S.

### B-NNN-D — State DCR overrides
**Origin**: § 4.1. NBC defaults work everywhere but cities have stricter rules.
**Status**: BACKLOG.
**Trigger**: First plan rejected at municipality for room-size violation traceable to state DCR.
**Effort**: M.

### B-NNN-E — Multi-floor sizing coordination
**Origin**: outside § scope. v1 sizes one floor at a time.
**Status**: BACKLOG.
**Trigger**: C12 vertical alignment work.
**Effort**: L.

### B-NNN-F — Furniture KB versioning + per-room customization
**Origin**: § 4.2. v1 furniture floor is static defaults.
**Status**: BACKLOG.
**Trigger**: Architectural-customization product feature.
**Effort**: M.

### B-NNN-I — Master-attached vs common bath assignment rules
**Origin**: § 4.2 / § 4.5. v1 conventions BATHROOM_1 = master-attached.
**Status**: BACKLOG.
**Trigger**: C11 placement work.
**Effort**: M.

### B-148 — Multi-floor dwelling-tier resolution (NEW v0.2 per Walk #2 #7)
**Origin**: § 4.1. v1 uses per-floor area as proxy for whole-dwelling NBC tier; multi-floor briefs (G+1 / G+2) need `total_dwelling_area_m2` threaded from C2.
**Status**: BACKLOG.
**Trigger**: First multi-floor brief test case where per-floor and whole-dwelling tiers diverge.
**Effort**: M (cross-component: C2 must compute and thread total dwelling area).

### B-149 — Packing-efficiency tightening to ERROR mode (NEW v0.2 per Walk #2 #15)
**Origin**: § 4.7 Inv 10. v1 logs Inv 10 as WARN to avoid false-positive rejection; production calibration data should drive a stricter default.
**Status**: BACKLOG.
**Trigger**: 50+ shipped plans where C11 placement geometry fails despite C9 passing Inv 9 but warning Inv 10.
**Effort**: S (config flag + invariant tier toggle).

### B-150 — NBC clause verification against reviewed copy of NBC 2016 Part 3 (NEW v0.2)
**Origin**: § 4.1 + § 8. Walk #1/#2 web research pinned clauses 12.1.1, 12.2.1, 12.2.2, 12.3.1, 12.3.2, 12.4 from a slideshare bye-laws table; storeroom (3.2 m²) clause not found in web sources. Direct verification against an authoritative NBC 2016 Part 3 PDF needed.
**Status**: BACKLOG.
**Trigger**: First time a regulator/inspector challenges a generated plan citing a specific clause.
**Effort**: S (one-time verification pass; KB updates).

### v0.2 backlog summary table

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

---

## § 13 — Definitions

- **`regulatory_minimum`** *(v0.2)*: NBC 2016 floor for the room category at the resolved dwelling tier. Carries area + width + height + clause-citation. Below any of area/width/height the room is non-compliant with the National Building Code.
- **`liveability_min_m2`** *(v0.2)*: `max(regulatory_minimum.area_m2, furniture_floor_m2)`. Below this value the room is technically compliant but cannot accommodate standard furniture with adequate clearance.
- **`target_m2`** *(v0.2)*: The comfortable size for typical Indian residential use, derived from architecture-v2 worked example. Target is what surplus allocation aims to reach.
- **`max_m2`** *(v0.2)*: Above this size the area is considered "wasted" and surplus is redirected to other rooms. Per-category multipliers per § 4.4.
- **`buildable_envelope_minus_corridor_m2`** *(v0.2)*: From C8's `CorridorPath.total_area_m2` and the plot's setback envelope: `(plot.area - setbacks - corridor)`. Computed at C9 entry.
- **`DwellingSizeTier`** *(NEW v0.2)*: NBC 2016 dwelling-size-tier enum. SMALL (≤50 m²) / LARGE (>50 m²). Resolves which row of `kb/nbc_room_minimums.json` to use.
- **`is_master`** *(NEW v0.2)*: Boolean flag on RoomSizeRequirement. True for BEDROOM_1 (and BATHROOM_1 if master-attached convention applies). Drives `(category, is_master)` lookup into furniture floor and target tables.
- **`packing_efficiency`** *(NEW v0.2)*: Default 0.75. Ratio used for Inv 10 WARN check: `Σ liveability_min ≤ envelope × packing_efficiency` warns when room area approaches envelope without typical wall + clearance slack.
- **`PRIORITY_GREEDY`** *(v0.2)*: Surplus-allocation strategy that gives the highest-priority room target_m2 first.
- **`PROPORTIONAL`** *(v0.2)*: Alternative strategy that distributes surplus proportionally to priority weights.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 DRAFT (carried forward)

§ 14.1 — **Two-floor minimum (regulatory + liveability)**: keep BOTH floors. NBC compliance is a hard legal requirement; furniture-fit is a quality bar.

§ 14.2 — **`PRIORITY_GREEDY` as v1 default**: simple, surgical, predictable.

§ 14.3 — **Hard-fail on infeasibility (v1)**: `RoomSizingInfeasibleError` raises. Soft-fail mode (B-NNN-A) deferred until C2 dialogue.

§ 14.4 — **NBC table is KB-managed JSON, not hardcoded constants**: matches C7 / C4 pattern.

### NEW v0.2 (resolved per Walks #1 + #2)

§ 14.5 — **C9 receives `FloorRoomBrief` directly, not via candidate** (Walk #1 Q1 / Walk #2 #12). Cardinal pattern: each component explicitly receives the upstream artifacts it consumes; implicit threading is reserved for cross-component trace correlation, not data dependency. C9 is the first component that needs explicit brief consumption.

§ 14.6 — **Master/non-master is a `priority` and `is_master` distinction, not a category distinction** (Walk #1 Q4 / Walk #2 #5). BEDROOM_1 conventionally master (`is_master=True`, priority=1, target_m2=master target); BEDROOM_2..N typical. Adding MASTER_BEDROOM enum was rejected to keep `RoomCategory` clean and avoid forcing C5/C6 upstream to track which TopologyCandidate is "for" the master.

§ 14.7 — **Schema enrichment: `regulatory_minimum` is a triple, not a scalar** (Walk #1 #11 / Walk #2 #2). NBC 2016 mandates area, width, AND height; the schema must carry all three so C11 placement satisfies all of them.

§ 14.8 — **`consumption_band` field DROPPED from RoomSizeRequirement** (Walk #1 #9 / Walk #2 #6). Band assignment is C11 placement's job. C9 produces sizes, not placement metadata.

§ 14.9 — **Dwelling-tier resolved from C8 envelope total** (Walk #2 #7). C9 doesn't need an explicit `dwelling_area_m2` parameter; it derives the tier from `Σ corridor_path.envelopes[].area_m2`. Multi-floor caveat filed as B-148.

§ 14.10 — **Packing-efficiency check is WARN, not RAISE** (Walk #2 #15). Pattern A discipline says fail at boundary, but over-strict packing check would false-positive-reject feasible plans. WARN logs to provenance; C11 placement geometry validator catches the truly unplaceable cases. Tightening filed as B-149.

§ 14.11 — **`max_m2` per-category multipliers are internally consistent**. The previous DRAFT's "1.6× target with 26m² bedroom cap" had self-contradictory baselines. v0.2 §4.4 has one multiplier per (category, is_master) tuple; the 26 m² cap mention is dropped.

---

## § 15 — Open questions for next round (or LOCK)

Most v0.1 open questions resolved during walks #1 + #2:
- ~~Q1~~: Resolved (§ 14.5).
- **Q2 (was)**: Should `RoomSizeRequirement` carry width? **Resolved YES** in § 3 + § 4.7 Inv 4 + § 14.7. Width is now part of regulatory_minimum triple.
- ~~Q3~~ State-DCR overrides: deferred (B-NNN-D); v0.2 doesn't try to handle.
- ~~Q4~~: Resolved (§ 14.6).
- **Q5 (was)**: Should target sizes scale with plot tier? Deferred (B-NNN-B); v0.2 holds fixed.
- **Q6 (was)**: Are max-multipliers right? § 4.4 v0.2 makes them per-category-consistent; v1 holds the values, monitoring data drives future re-calibration.
- **Q7 (was)**: Is v1 default priority order right? Deferred (B-NNN-C); v0.2 holds the v1 order with override path.
- ~~Q8~~: Resolved (§ 14.3 + B-NNN-A reframed).
- **Q9 (was)**: Should v0.1 carry width × depth shape constraints? **Resolved**: width is enough for v1 (NBC's mandate is on width specifically, not depth). C11 placement decides depth from area + width during layout.
- **Q10 (was)**: Climate effect on priority order? Deferred (B-091 territory); v0.2 doesn't address.

### NEW Q11 — Bathroom default: combined Bath+WC vs separate?

v0.2 § 4.1 marks **Combined Bath+WC** as the v1 default for "BATHROOM" room category since it's the typical Indian residential interior bathroom configuration. But some user briefs may want separate bath + WC rooms. Should the schema admit a `bathroom_subtype: BathroomSubtype` enum (`COMBINED` / `BATH_ONLY` / `WC_ONLY`) for v1, or defer until briefs explicitly request it?

**Recommendation for walk #3**: defer (the brief's `bathroom_count` is sufficient for v1; subtype = COMBINED hardcoded). File as **B-NNN-bathroom-subtype** if not actioned at walk #3.

### NEW Q12 — Should `floor_label` be propagated to RoomSizeTable too, not just provenance?

v0.2 § 10 puts `floor_label` only in provenance. But for multi-floor briefs the consuming code may need to know which floor a `RoomSizeTable` represents *without* unpacking provenance.

**Recommendation for walk #3**: add `floor_label: str` to RoomSizeTable too (cheap; resolves the inconvenience for callers who don't want to unpack provenance just for floor identification). Decide at LOCK.

---

## § 16 — End of v0.2 PROPOSED

Expected next: walk #3 (Ramalingam reviewer round) → LOCK adjudication → build (D-066 step 6-8).
