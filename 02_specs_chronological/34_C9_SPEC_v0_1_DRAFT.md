# BuildemUp — C9 Room Sizer — SPEC v0.1 DRAFT

**Status**: DRAFT. PENDING critique walks → LOCK adjudication. Greenfield first draft (no prior version). Per Rule 8, LOCK authority belongs to Ramalingam alone; this is the entry point of D-066's step-1 (draft → critique → critique → critique → LOCK).
**Component**: C9 of canonical 17-component v3 list (Track 3). Position 9. First sub-component pending in build order after C8 (which SHIPPED at S32).
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C8 (`CorridorDesignedCandidate`) + C7 (`StructuralGrid`) + C4 (`PlotAnalysis`) + C1's `FloorRoomBrief`. Produces input for C10 (Bathroom + Wet-Zone Stack Planner).
**Authoring session**: S33 (post C8 SHIP).
**Predecessor**: none — this is v0.1 DRAFT.

---

## § 0 — Why this spec, why now

After C8 SHIP at S32, the pipeline has produced: oriented topology candidates with refined zone bands (C6), structural grid (C7), and corridor geometry (C8). The downstream consumer (C10 wet-zone planner) needs *room footprints with sizes assigned* — not just band envelopes. C9 sits between "the bands and corridor are designed" and "specific rooms have specific min/target sizes."

C9's job: given the brief's room composition (`FloorRoomBrief.bedroom_count`, `bathroom_count`, `has_kitchen`, etc.), the band envelopes from C8's `ZoneBandEnvelope` (with the corridor area carved out), the structural grid bays, and the plot analysis (climate, tier, regulatory minimums), produce a `RoomSizeTable` — for each room, a `(min_m2, target_m2, max_m2)` triple that downstream placement components can satisfy.

C9 does NOT place rooms (that's C11 placement engine). C9 does NOT generate furniture layouts (that's C14 furniture-fit metric). C9 does NOT decide adjacencies (that's C5/C11). C9 does NOT score the resulting sizes (that's C14).

**The architectural distinction the project has been making**: NBC 2016 minimum is the **regulatory floor**; furniture-fit minimum is the **liveability floor**. v1 C9 produces both — `min_m2 = max(nbc_min, furniture_min)` — so downstream consumers can choose to enforce either. The "liveability gap" identified in the v3 architecture (NBC-compliant rooms can still be unlivable) is closed at this layer.

**Architecture-v2/v3 provenance** (reproduced for traceability):
- v2 § 5 / Component 9 (Room Sizer with furniture envelope): "Assign a minimum and target size to every room, based on NBC + actual furniture + clearance requirements."
- v3 leaves C9 unchanged from v2 (no v3 delta touches C9 directly).
- Component Validation Report § 9: "Use NBC 2016 as floor for rejection (Q6: refuse if below NBC), Neufert/Ching as preferred targets (warn if below preferred but above NBC)."

---

## § 1 — Purpose

Given a C8-corridor-designed candidate, the brief's room composition, the structural grid bays, and the plot analysis, produce a **`RoomSizeTable`** — for each requested room (bedroom × N, bathroom × M, kitchen, living, pooja, utility, plus brief-defined `other_rooms`), the regulatory-floor min size, the liveability min size, the target size, and the max size. The total of all `min_m2` must fit within the buildable envelope minus the corridor area; if it does not, raise a typed `RoomSizingInfeasibleError(B-NNN-A)` with the deficit named.

Cardinality preserved: 1-3 C8 candidates → 1-3 C9 candidates, position-paired.

**Out of scope for C9** (intentionally not addressed):
- Room placement (XY positioning) — C11
- Adjacency / connectivity — C5 selected, C11 enforces
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
    structural_grid: StructuralGrid,                                        # from C7
    plot_analysis: PlotAnalysis,                                            # from C4
    *,
    config: RoomSizingConfig | None = None,                                 # tunables; default OK
) -> tuple[RoomSizedCandidate, ...]:
```

`RoomSizedCandidate` = `CorridorDesignedCandidate` + `room_size_table: RoomSizeTable` + `provenance: RoomSizingProvenance` (extends position-paired chain).

`RoomSizingConfig` carries per-call tunables: enforcement mode (`STRICT` / `WARN`), Neufert/Ching multipliers, allocation strategy (`PRIORITY_GREEDY` / `PROPORTIONAL`), defaults baked into the dataclass mean callers can omit it entirely.

**Why `FloorRoomBrief` directly, not via a candidate field**: C5 already attaches the brief implicitly to its candidates via shared C4 trace_id, but the brief itself is not on the `OrientedCandidate` / `CorridorDesignedCandidate`. C9 needs the brief explicitly to enumerate bedrooms (count) and named other_rooms. **Open Q1 for critique**: should `FloorRoomBrief` be threaded onto `CorridorDesignedCandidate` upstream so C9's signature collapses, or is the explicit pass-through the cleaner contract? Q1 is a candidate for walk #1.

---

## § 3 — Output schema

```python
class RoomCategory(str, Enum):
    """The 6 v1 room categories. Mirrors C6's FunctionRole + introduces named
    instances for multi-room categories (BEDROOM_1, BEDROOM_2, ...).
    """
    BEDROOM    = "bedroom"      # Bedrooms enumerated by count → BEDROOM_1, BEDROOM_2, ...
    BATHROOM   = "bathroom"     # Likewise; BATHROOM_1 may be MASTER (priority-elevated)
    LIVING     = "living"       # Singular — at most one per floor in v1
    KITCHEN    = "kitchen"      # Singular
    POOJA      = "pooja"        # Optional (per FloorRoomBrief.has_pooja)
    UTILITY    = "utility"      # Optional (per FloorRoomBrief.has_utility)
    OTHER      = "other"        # FloorRoomBrief.other_rooms entries; pooled here in v1


@dataclass(frozen=True)
class RoomSizeRequirement:
    """Per-room sizing requirement.

    For each room R:
      - regulatory_min_m2: NBC 2016 floor; cannot be deducted from
      - liveability_min_m2: max(regulatory_min, furniture_floor)
      - target_m2: comfortable size for typical Indian use
      - max_m2: above which area is wasted (used to clamp surplus distribution)

    Invariants (asserted at construction):
      - 0 < regulatory_min_m2 <= liveability_min_m2 <= target_m2 <= max_m2
      - regulatory_min_m2 always uses NBC 2016 numbers (or KB-managed table)
    """
    room_id: str                                    # e.g. "BEDROOM_1", "BATHROOM_2", "KITCHEN"
    category: RoomCategory                          # enum
    regulatory_min_m2: float                        # NBC 2016 floor
    liveability_min_m2: float                       # max(reg_min, furniture_min)
    target_m2: float                                # Neufert/Ching comfortable
    max_m2: float                                   # waste threshold
    consumption_band: ZoneBand                      # which band this room sits in
    priority: int                                   # 1 = highest, used for surplus allocation


@dataclass(frozen=True)
class RoomSizeTable:
    """The complete sizing for one C8 candidate's floor.

    Rooms are enumerated by FloorRoomBrief: bedroom_count → BEDROOM_1...N,
    bathroom_count → BATHROOM_1...M (BATHROOM_1 conventionally master-attached
    in v1), plus living/kitchen/pooja/utility/other as flagged.

    Invariants (asserted at construction):
      - rooms is non-empty
      - room_ids unique
      - Σ liveability_min_m2 ≤ buildable_envelope_minus_corridor_m2
      - Σ target_m2 may exceed envelope (surplus-allocation absorbs slack)
      - every category counts match brief (count(BEDROOM) == brief.bedroom_count, etc.)
    """
    rooms: tuple[RoomSizeRequirement, ...]
    buildable_envelope_minus_corridor_m2: float     # available area
    total_liveability_min_m2: float                 # Σ liveability_min
    total_target_m2: float                          # Σ target
    surplus_for_distribution_m2: float              # envelope − Σ liveability_min


@dataclass(frozen=True)
class RoomSizingProvenance:
    """Provenance for one C9 sizing pass."""
    derived_at: float
    plot_analysis_trace_id: str
    nbc_table_version: str                          # which NBC table snapshot
    furniture_kb_version: str                       # which Neufert/Ching snapshot
    enforcement_mode: str                           # STRICT | WARN
    allocation_strategy: str                        # PRIORITY_GREEDY | PROPORTIONAL
    surplus_distributed_m2: float                   # post-allocation
    rooms_at_min: tuple[str, ...]                   # IDs that got only liveability_min
    rooms_clamped_at_max: tuple[str, ...]           # IDs that hit max_m2
    rule_trace: tuple[str, ...]


@dataclass(frozen=True)
class RoomSizedCandidate:
    """One C8 CorridorDesignedCandidate + C9 sizing."""
    corridor_designed_candidate: CorridorDesignedCandidate
    room_size_table: RoomSizeTable
    provenance: RoomSizingProvenance
```

**Open Q2 for critique**: should `RoomSizeRequirement` carry a `(width_min_m, depth_min_m)` lower bound (not just area)? Industry practice cites NBC's "min width 2.4 m" rule for habitable rooms — a 9.5 m² room that's 1.5 m × 6.3 m is non-compliant on width even though it meets the area. Walk #1 candidate.

---

## § 4 — Behavior

### § 4.1 — Regulatory minimums (NBC 2016 KB)

Source-of-truth table for v1 (per Rule 7 web research, S33; consensus across InfraLens, Wadhwa, NBC 2016 Part 3):

| Category | NBC 2016 min area | NBC 2016 min width | Source |
|---|---|---|---|
| BEDROOM (habitable) | 9.5 m² (single-room dwellings) / 7.5 m² (multi-room dwellings; B-NNN-G to verify) | 2.4 m | NBC 2016 Part 3, § 4.5 |
| LIVING (habitable) | 9.5 m² | 2.4 m | same |
| KITCHEN | 5.0 m² | 1.8 m | NBC 2016 Part 3, § 4.5.1 |
| BATHROOM (with WC) | 1.8 m² | 1.0 m | NBC 2016 Part 3, § 4.5.3 |
| BATHROOM (WC only) | 1.1 m² | 0.9 m | same |
| POOJA | (not habitable; no NBC floor) | — | — |
| UTILITY | 3.2 m² (storeroom) | — | NBC 2016 Part 3, § 4.5.5 |

These values live in `kb/nbc_room_minimums.json` (matches existing C7 KB pattern). Versioned via `nbc_table_version`. **Open Q3 for critique**: at what granularity should the table support state-DCR overrides (TNCDBR Tamil Nadu, Maharashtra DCR, Karnataka KMC byelaws)? B-NNN-D candidate.

### § 4.2 — Liveability minimums (furniture-fit floor)

For each category, a furniture-floor area is computed from a reference furniture configuration. v1 uses static defaults (per architecture-v2 Component 9 worked example) cached in `kb/furniture_floor.json`:

| Category | Furniture-floor m² | Reference configuration |
|---|---|---|
| BEDROOM (typical) | 9.3 m² (~100 sqft) | Single bed 0.9 × 2.0 + study 1.2 × 0.6 + wardrobe 1.2 × 0.6 + 0.75 m clearance |
| BEDROOM (master, BEDROOM_1) | 13.0 m² (~140 sqft) | Queen 1.5 × 2.0 + 2 side tables + wardrobe + 0.9 m clearance |
| LIVING | 16.7 m² (~180 sqft) | 3-seat sofa + 2 chairs + coffee table + circulation |
| KITCHEN | 7.9 m² (~85 sqft) | L-counter 3.0 m run + fridge + 1.2 m work aisle |
| BATHROOM | 2.8 m² (~30 sqft) | Shower 0.9 × 0.9 + WC + sink + 0.6 m clearance |
| POOJA | 2.8 m² (~30 sqft) | Altar 0.6 × 0.9 + seated prayer + storage cabinet |
| UTILITY | 2.8 m² (~30 sqft) | Washing machine + sink + storage |

`liveability_min_m2 = max(regulatory_min_m2, furniture_floor_m2)`. For BEDROOM, this typically resolves to ~9.3 m² (regulatory and furniture nearly coincident). For master BEDROOM_1, 13.0 m² (furniture wins). For LIVING, 16.7 m² (furniture wins decisively over NBC's 9.5 m²).

**Open Q4 for critique**: should the master-vs-typical bedroom distinction be explicit (BEDROOM_MASTER as a separate category) or implicit (BEDROOM_1 always treated as master)? Walk #1 candidate.

### § 4.3 — Target sizes

Per architecture-v2 Component 9 worked example (NE 30×40 reference plan), `target_m2` per category:

| Category | Target m² (typical) | Target m² (master/luxury for BR_1) |
|---|---|---|
| BEDROOM | 10.2 (~110 sqft) | 14.9 (~160 sqft) |
| LIVING | 18.6 (~200 sqft) | — |
| KITCHEN | 9.3 (~100 sqft) | — |
| BATHROOM | 3.3 (~35 sqft) | 4.2 (~45 sqft for master-attached) |
| POOJA | 3.3 (~35 sqft) | — |
| UTILITY | 3.7 (~40 sqft) | — |

**Open Q5 for critique**: should target sizes scale with plot tier (T1 5–10 lakh-sqft / T2 / T3) rather than being fixed? A T3 plot at 5,400 sqft might warrant larger targets than a T1 1,200 sqft plot. B-NNN-B candidate; v1 holds them fixed.

### § 4.4 — Max sizes (waste threshold)

`max_m2 = 1.6 × target_m2` (per architecture-v2 implicit; the worked example bath2 at 30 sqft target 35 sqft suggests max ≈ 50 sqft = 4.6 m²; ratio 1.6 holds). Bedrooms cap at ~26 m² (≈ 280 sqft) — beyond which the room is "wasted" per the v3 design principle "give the surplus back to other rooms." Living can go higher (no cap); set max = 2.5 × target for LIVING specifically.

**Open Q6 for critique**: are these multipliers right? They're heuristics. Walk candidate.

### § 4.5 — Surplus allocation

After computing `liveability_min` for each room, `surplus_m2 = buildable_envelope_minus_corridor_m2 - Σ liveability_min`. Distribution algorithm:

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
1. BEDROOM_1 (master) — highest
2. BEDROOM_2..N (children, guest)
3. KITCHEN
4. LIVING
5. BATHROOM_1 (master attached)
6. BATHROOM_2..M (common, guest)
7. POOJA
8. UTILITY
9. OTHER (pooled)

**Open Q7 for critique**: priority order is from v1 architecture; is it still right? Master bedroom over kitchen makes sense for sleeping comfort but kitchen is the engine of daily life. A T2/T3 family-size brief might invert. B-NNN-C candidate; v1 holds the v1 order as default with priority overridable per-call via `RoomSizingConfig`.

### § 4.6 — Infeasibility detection

If `Σ liveability_min_m2 > buildable_envelope_minus_corridor_m2`, raise `RoomSizingInfeasibleError(B-NNN-A)` with deficit named:

```
RoomSizingInfeasibleError: this floor's liveability_min total (74.6 m²)
exceeds buildable envelope minus corridor (66.0 m²) by 8.6 m². Specific:
  BEDROOM_1: 13.0 m² (master)
  BEDROOM_2: 9.3 m²
  BEDROOM_3: 9.3 m²
  LIVING:    16.7 m²
  KITCHEN:    7.9 m²
  BATHROOM_1: 2.8 m²
  BATHROOM_2: 2.8 m²
  POOJA:      2.8 m²
  UTILITY:    2.8 m²
  Σ:         74.6 m²
Deficit: 8.6 m². Options:
  (a) Drop BEDROOM_3 (saves 9.3 m²) — but brief specified 3 bedrooms.
  (b) Reduce BEDROOM_1 to non-master spec (saves 3.7 m²) — partial.
  (c) Split across two floors (request a multi-floor brief).
  (d) Increase plot size or relax setbacks.

Caller must escalate to C2 feasibility renegotiation or surface to user.
```

**Open Q8 for critique**: should C9 emit a `(soft|hard)` verdict that lets C2 retry with reduced room count, or always hard-fail? Walk candidate; v1 hard-fails.

### § 4.7 — Validator invariants

| # | Invariant | Source |
|---|---|---|
| 1 | rooms.count == FloorRoomBrief-derived total count | brief consistency |
| 2 | category counts match brief | brief consistency |
| 3 | every regulatory_min_m2 ≥ NBC 2016 table value | NBC compliance |
| 4 | every liveability_min_m2 ≥ regulatory_min_m2 | math |
| 5 | every target_m2 ≥ liveability_min_m2 | math |
| 6 | every max_m2 ≥ target_m2 | math |
| 7 | Σ liveability_min_m2 ≤ buildable_envelope_minus_corridor_m2 | feasibility |
| 8 | room_ids are unique | data integrity |
| 9 | priority values cover 1..n contiguously (no gaps) | well-formedness |
| 10 | every consumption_band is a valid ZoneBand | enum |

---

## § 5 — Invocation contract (public)

```python
sized = size_rooms(
    corridor_designed_candidates=c8_output,
    floor_room_brief=c1_brief.floors[0],   # for ground floor; multi-floor briefs loop
    structural_grid=c7_grid,
    plot_analysis=c4_plot_analysis,
)  # config defaults are fine for v1
```

Cardinality: 1-3 in → 1-3 out, position-paired (matches C6/C8 pattern).

---

## § 6 — Failure modes

| Condition | Behavior |
|---|---|
| `corridor_designed_candidates` not a tuple | `TypeError` |
| `floor_room_brief` not FloorRoomBrief | `TypeError` |
| `structural_grid` not StructuralGrid | `TypeError` |
| `plot_analysis` not PlotAnalysis | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066, mirrors C6) |
| `plot_analysis.climate_zone` is HOT_DRY or COLD | passes through; v1 has no climate-dependent sizing |
| Brief specifies 0 bedrooms | `ValueError` (caller bug; brief should always specify ≥ 1 bedroom) |
| Σ liveability_min > envelope | `RoomSizingInfeasibleError` (B-NNN-A) |
| One room category's NBC table entry missing | `KeyError` (caller-side KB integrity issue) |
| Empty input tuple | Returns empty tuple |

**Order-of-checks**: type checks first, shape check next, brief sanity, then per-candidate infeasibility. (Pattern A avoidance — fail at boundary, not deep in sizing.)

---

## § 7 — Test plan

Following C5/C6/C8's pattern. v0.1 targets ~80-100 tests across modules:

- **schema.py**: ~25 tests — RoomSizeRequirement / RoomSizeTable / RoomSizedCandidate __post_init__ invariants, range checks, frozen-ness, enum coverage.
- **nbc_table.py**: ~10 tests — table coverage (every category present), value-spot-checks against NBC 2016 numbers, version-string presence.
- **furniture_floor.py**: ~10 tests — table coverage, master-vs-typical distinction.
- **allocator.py**: ~15 tests — PRIORITY_GREEDY happy path, infeasibility raise, max_m2 clamp, target reached then overflow, leftover-surplus handling, PROPORTIONAL strategy parity.
- **size_rooms (orchestrator)**: ~20 tests — end-to-end on bangalore_40x60 / chennai-equivalent / delhi_60x90, cardinality preservation, position pairing, all 4 cardinal facings (via C8 inputs), provenance correctness.
- **failure_modes**: ~15 tests — every row in § 6 table.

---

## § 8 — KB references

| KB | Status | Used for |
|---|---|---|
| `kb/nbc_room_minimums.json` | **NEW v0.1** | NBC 2016 area + width minimums per category |
| `kb/furniture_floor.json` | **NEW v0.1** | Neufert/Ching reference furniture configurations → floor m² |
| `kb/state_dcr_overrides.json` | **stub; B-NNN-D** | TNCDBR / Maharashtra DCR / KMC overrides on NBC defaults |

---

## § 9 — Out of scope

| Item | Backlog ID |
|---|---|
| State-DCR room-size overrides (TNCDBR, MH-DCR, KMC) | B-NNN-D |
| Plot-tier-aware target sizing (T1/T2/T3 differential) | B-NNN-B |
| Configurable priority order beyond v1 default | B-NNN-C |
| Width-minimum check (NBC's 2.4 m habitable-room width) | B-NNN-G |
| Multi-floor sizing coordination (master on FF, kids on GF, etc.) | B-NNN-E |
| Furniture KB versioning + per-room user customization | B-NNN-F |
| Soft-fail mode (return reduced count + warning instead of raise) | B-NNN-H |
| BR/BA pooling rules (master-attached vs common bath assignment) | B-NNN-I |

---

## § 10 — Provenance

`RoomSizingProvenance` carries:
- `derived_at`, `plot_analysis_trace_id` — traceability
- `nbc_table_version`, `furniture_kb_version` — KB-snapshot identification
- `enforcement_mode` (`STRICT` / `WARN`) — gate behavior
- `allocation_strategy` (`PRIORITY_GREEDY` / `PROPORTIONAL`) — algorithm choice
- `surplus_distributed_m2` — total redistribution
- `rooms_at_min` — IDs that got only liveability_min (no surplus)
- `rooms_clamped_at_max` — IDs that hit max_m2 cap
- `rule_trace` — debugging

---

## § 11 — Spec metadata

- **Version**: v0.1 DRAFT
- **Status**: DRAFT — first round; PENDING walks #1–#3 critique → LOCK
- **Lineage**: v0.1 DRAFT (greenfield)
- **Authoring session**: S33
- **Companion artifacts**: NBC 2016 web research (Rule 7) — InfraLens / Wadhwa / Sobha; architecture v2 § 5 Component 9; architecture v3 (no delta).

---

## § 12 — Backlog enumeration (preliminary; B-NNNs assigned at LOCK)

Total: **9 items** (all OUT-of-scope this build).

### B-NNN-A — RoomSizingInfeasibleError + soft-fail mode dialogue
**Origin**: § 4.6 — when liveability_min total exceeds envelope, v1 hard-raises. A soft-fail mode that returns a reduced-count brief + warning would let C2 retry without crashing the pipeline.
**Status**: BACKLOG (deferred design dialogue with C2 at C2-build time).
**Trigger**: C2's feasibility loop needs to consume C9's verdict and renegotiate.
**Effort**: M (interface change; depends on C2 contract).

### B-NNN-B — Plot-tier-aware target sizing
**Origin**: § 4.3 — target sizes are fixed in v1; T3 plots could comfortably support larger rooms, T1 plots may not afford v1 targets.
**Status**: BACKLOG.
**Trigger**: Empirical signal (≥ 5 user reports of "rooms feel too small on big plots" or "infeasibility on small plots even though brief is reasonable").
**Effort**: S (table refactor; multiplier per tier).

### B-NNN-C — Configurable priority order
**Origin**: § 4.5 — v1 default is master-bedroom-first; some users may prefer kitchen-first or living-first.
**Status**: BACKLOG (RoomSizingConfig already accepts override; tests cover only default).
**Trigger**: First user request for non-default ordering.
**Effort**: S.

### B-NNN-D — State DCR overrides
**Origin**: § 4.1 — NBC defaults work everywhere but cities have stricter rules (TNCDBR for Tamil Nadu, MH-DCR for Maharashtra, KMC for Bangalore). v1 ignores these.
**Status**: BACKLOG.
**Trigger**: First plan rejected at municipality for room-size violation traceable to state DCR.
**Effort**: M (KB layer + city → DCR lookup).
**Related**: mirrors B-076 (corner plot secondary-road convention) and B-098 (climate zone) — same pattern of state-specific overrides on national defaults.

### B-NNN-E — Multi-floor sizing coordination
**Origin**: outside § scope — v1 sizes one floor at a time; multi-floor briefs (G+1, G+2) need master/kids distribution across floors.
**Status**: BACKLOG.
**Trigger**: C12 vertical alignment work.
**Effort**: L.

### B-NNN-F — Furniture KB versioning + per-room customization
**Origin**: § 4.2 — v1 furniture floor is static defaults; users may want "I have a king bed, not a queen" or "no walk-in, just a wardrobe."
**Status**: BACKLOG.
**Trigger**: Architectural-customization product feature.
**Effort**: M.

### B-NNN-G — Width-minimum (NBC 2.4 m habitable-room width) check
**Origin**: § 4.1 — NBC mandates min 2.4 m width on habitable rooms; v1 only checks area. A 9.5 m² room at 1.5 m × 6.3 m fails NBC width but passes area.
**Status**: BACKLOG (architecturally simple; deferred because C9's job is sizing, and width check belongs to C11 placement).
**Trigger**: C11 placement build round.
**Effort**: S (~1 hour).

### B-NNN-H — Soft-fail mode (return reduced brief + warning)
**Origin**: § 6 / Q8 — v1 hard-raises on infeasibility; product UX may want to surface "Brief reduced: 3 bedrooms became 2" warnings instead.
**Status**: BACKLOG.
**Trigger**: B-NNN-A dialogue.
**Effort**: S.

### B-NNN-I — Master-attached vs common bath assignment rules
**Origin**: § 4.2 / § 4.5 — v1 conventions BATHROOM_1 = master-attached, BATHROOM_2+ = common. But brief-driven scenarios (4 bedrooms but only 2 baths) need explicit rules for which BR shares which bath.
**Status**: BACKLOG.
**Trigger**: C11 placement work; placement may surface adjacency conflicts.
**Effort**: M.

### v0.1 backlog summary table

| ID | Title | Origin | Status | Trigger | S33-scope | Effort |
|---|---|---|---|---|---|---|
| B-NNN-A | Soft-fail mode + C2 dialogue | § 4.6 / Q8 | BACKLOG | C2 feasibility loop | OUT | M |
| B-NNN-B | Plot-tier-aware target sizing | § 4.3 / Q5 | BACKLOG | Empirical signal | OUT | S |
| B-NNN-C | Configurable priority order | § 4.5 / Q7 | BACKLOG | First user request | OUT | S |
| B-NNN-D | State DCR overrides | § 4.1 / Q3 | BACKLOG | Municipality rejection | OUT | M |
| B-NNN-E | Multi-floor coordination | § scope | BACKLOG | C12 vertical alignment | OUT | L |
| B-NNN-F | Furniture KB versioning | § 4.2 | BACKLOG | Customization feature | OUT | M |
| B-NNN-G | Width-minimum check | § 4.1 / Q2 | BACKLOG | C11 placement | OUT | S |
| B-NNN-H | Soft-fail return mode | § 6 / Q8 | BACKLOG | B-NNN-A | OUT | S |
| B-NNN-I | Bath assignment rules | § 4.2 | BACKLOG | C11 placement | OUT | M |

---

## § 13 — Definitions

- **`regulatory_min_m2`** *(v0.1)*: NBC 2016 floor area for the room category. Below this value the room is non-compliant with the National Building Code.
- **`liveability_min_m2`** *(v0.1)*: `max(regulatory_min_m2, furniture_floor_m2)`. Below this value the room is technically compliant but cannot accommodate standard furniture with adequate clearance.
- **`target_m2`** *(v0.1)*: The comfortable size for typical Indian residential use, derived from architecture-v2 worked example. Target is what surplus allocation aims to reach.
- **`max_m2`** *(v0.1)*: Above this size the area is considered "wasted" and surplus is redirected to other rooms. v1 uses 1.6 × target for most categories, 2.5 × target for LIVING.
- **`buildable_envelope_minus_corridor_m2`** *(v0.1)*: From C8's `CorridorPath.total_area_m2` and the plot's setback envelope: `(plot.area - setbacks - corridor)`. Computed at C9 entry.
- **`PRIORITY_GREEDY`** *(v0.1)*: Surplus-allocation strategy that gives the highest-priority room target_m2 first, then the next, etc.
- **`PROPORTIONAL`** *(v0.1)*: Alternative strategy that distributes surplus proportionally to priority weights (smoother but less surgical).

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 (this draft)

§ 14.1 — **Two-floor minimum (regulatory + liveability)**: keep BOTH floors, do not collapse to one. Downstream consumers need to distinguish "we'd reject for code violation" from "we'd warn but allow." Rationale: NBC compliance is a hard legal requirement; furniture-fit is a quality bar.

§ 14.2 — **`PRIORITY_GREEDY` as v1 default**: simple, surgical, predictable. Matches architecture-v1's "splitter always protects the more important room first." `PROPORTIONAL` is documented but not the v1 default.

§ 14.3 — **Hard-fail on infeasibility (v1)**: `RoomSizingInfeasibleError` raises rather than soft-degrading. Soft-fail mode (B-NNN-H) deferred until C2 dialogue. Rationale: pattern A avoidance — surface the problem at the boundary, don't silently truncate the brief.

§ 14.4 — **NBC table is KB-managed JSON, not hardcoded constants**: matches C7 / C4 pattern. Lets the table version-bump without code changes.

§ 14.5 — **C9 receives `FloorRoomBrief` directly, not via candidate**: explicit pass-through over hidden field. Q1 to be revisited at walk #1.

§ 14.6 — **`max_m2 = 1.6 × target_m2` heuristic (2.5 for LIVING)**: drawn from architecture-v2 implicit; calibration deferred to user signal.

§ 14.7 — **`liveability_min_m2 = max(regulatory_min_m2, furniture_floor_m2)`**: per architecture-v2 Component Validation Report § 9 — "use NBC 2016 as floor for rejection, Neufert/Ching as preferred targets."

---

## § 15 — Open questions for next round (or LOCK)

1. **Q1**: Should `FloorRoomBrief` be threaded onto `CorridorDesignedCandidate` upstream so C9's signature collapses, or is the explicit pass-through cleaner? (§ 2)
2. **Q2**: Should `RoomSizeRequirement` carry `(width_min_m, depth_min_m)` not just area, to enforce NBC's 2.4 m habitable-room width? (§ 3 / B-NNN-G)
3. **Q3**: At what granularity should the regulatory table support state-DCR overrides? (§ 4.1 / B-NNN-D)
4. **Q4**: Should master-vs-typical bedroom distinction be explicit (BEDROOM_MASTER as separate category) or implicit (BEDROOM_1 always treated as master)? (§ 4.2)
5. **Q5**: Should target sizes scale with plot tier (T1/T2/T3)? (§ 4.3 / B-NNN-B)
6. **Q6**: Are the max-multipliers (1.6 for most, 2.5 for living) right? (§ 4.4)
7. **Q7**: Is the v1 default priority order (master-bedroom-first) right? (§ 4.5 / B-NNN-C)
8. **Q8**: Should infeasibility hard-fail (v1) or soft-degrade (B-NNN-H)? (§ 4.6 / § 6)
9. **Q9**: Should v0.1 carry `width_m × depth_m` shape constraints alongside area? (§ 3 — distinct from Q2 width-minimum)
10. **Q10**: How does C9 interact with B-091 (climate-variant zone-band assignment)? Does climate affect priority order? (§ 4.5)

---

## § 16 — End of v0.1 DRAFT

Expected next: critique walks (D-066 step 2-4), then v0.2 PROPOSED → ... → v0.N LOCKED → build (D-066 step 6-8).
