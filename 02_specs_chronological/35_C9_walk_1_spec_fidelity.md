# C9 Spec Critique — Walk #1 (Self-critique on v0.1 DRAFT)

**Authoring session**: S33
**Subject**: `34_C9_SPEC_v0_1_DRAFT.md` (515 lines, drafted earlier this session)
**Walk type**: spec walk #1 of 3 (D-066 step 2; first round of critique)
**Walker**: Claude (self-critique on the DRAFT I wrote earlier this session)

This walk asks: **does the v0.1 DRAFT hold up against (a) actual upstream contracts, (b) the NBC 2016 numbers it cites, (c) project-wide architectural discipline?**

Per Rule 7, ≥1 web search performed (NBC 2016 room-size minimums; results inform Findings #4 and #5 below).
Per Rule 9.2, every VALID-BUT-BACKLOG item is filed at end of walk.

---

## Pre-touch inventory (Rule 10.6.1)

Pre-existing at walk-#1 open:
- C9 SPEC v0.1 DRAFT at `/home/claude/work/handoff_v10/02_specs_chronological/34_C9_SPEC_v0_1_DRAFT.md`
- C8 LOCKED v0.5 spec (in v9 bundle) — referenced for input contract
- `buildemup/components/c08/schema.py` — `CorridorDesignedCandidate` actual surface
- `buildemup/components/c07/grid_generator.py` — `Grid` actual class name
- `buildemup/domain/floor_brief.py` — `FloorRoomBrief` actual surface
- 9 backlog items listed inside the DRAFT (B-NNN-A through B-NNN-I)

This walk surfaces **new** findings. Pre-existing items are referenced when relevant but not re-counted.

---

## Summary of findings

| # | Finding | Verdict | Severity |
|---|---|---|---|
| 1 | Wrong type name `StructuralGrid`; actual class is `Grid` | VALID-DEFECT | LOW (typo-class) |
| 2 | `FloorRoomBrief.has_kitchen` / `has_living` are `bool` — DRAFT assumes always present | VALID-DEFECT | MEDIUM |
| 3 | `bathroom_count: int` may be 0; DRAFT § 3 collapses on this case | VALID-DEFECT | MEDIUM |
| 4 | NBC kitchen minimum I cited (5.0 m²) is wrong; correct is 4.5 m² (or 3.3 m² for dwellings ≤50 m²) | VALID-DEFECT | HIGH |
| 5 | NBC bathroom minimum I cited (1.8 m²) confuses Bathroom-only vs Combined-Bath-WC (2.8 m²) | VALID-DEFECT | HIGH |
| 6 | Q1 (FloorRoomBrief threading) — answer it now in walk #1 instead of deferring | VALID-RESOLVE-NOW | — |
| 7 | Q4 (master-vs-typical bedroom) — pattern is identical to a fundamental category-vs-instance question | VALID-RESOLVE-NOW | — |
| 8 | `RoomCategory` enum doesn't include MASTER_BEDROOM but § 4.2 distinguishes master from typical bedroom | DESIGN-INCONSISTENCY | MEDIUM |
| 9 | `consumption_band: ZoneBand` field on RoomSizeRequirement — C9 doesn't have band-assignment information; this belongs to C11 placement | VALID-DEFECT | MEDIUM |
| 10 | `floor_label` from FloorRoomBrief never propagated to RoomSizingProvenance — debug signal lost | VALID-BUT-BACKLOG | LOW |
| 11 | NBC width-minimum (Q2) — DRAFT defers this but it's a functional NBC compliance gap, not a quality bar | DESIGN-DEFICIENCY | MEDIUM |
| 12 | DRAFT cites InfraLens / Wadhwa as sources but I never named exact NBC clause numbers — provenance weakness | VALID-DEFECT | LOW |
| 13 | § 4.4 max_m2 = 1.6 × target heuristic conflicts with worked example | VALID-DEFECT | LOW |
| 14 | DRAFT § 4.6 infeasibility hard-fails but never specifies relationship to C2 retry contract | VALID-BUT-BACKLOG | MEDIUM |
| 15 | Test plan (§ 7) targets ~80–100 tests but DRAFT lists no specific invariant-coverage breakdown | VALID-DEFECT | LOW |

**Headline**: 12 VALID-DEFECTs (2 HIGH, 5 MEDIUM, 5 LOW) + 1 VALID-BUT-BACKLOG + 2 VALID-RESOLVE-NOW. Two HIGH-severity findings (#4 and #5) are **wrong NBC numbers** in the DRAFT — these would propagate into the KB if not corrected.

This is what walk #1 is for.

---

## Findings detail

### Finding #1 — Wrong type name `StructuralGrid`

**Verdict**: VALID-DEFECT.
**Severity**: LOW.
**Location**: § 2 input contract.
**Evidence**: my v0.1 DRAFT § 2 says `structural_grid: StructuralGrid` but C7 defines the class as `Grid` (in `buildemup.components.c07.grid_generator`). Confirmed by `dataclasses.fields(Grid)` returning `[columns, bay_x_m, bay_y_m, columns_x_count, columns_y_count, envelope_width_m, envelope_depth_m]`.
**Fix**: rename to `grid: Grid`. (Argument name `structural_grid` is fine for clarity; type annotation must be `Grid`.)

### Finding #2 — Brief optionality assumed away

**Verdict**: VALID-DEFECT.
**Severity**: MEDIUM.
**Location**: § 3 RoomCategory comments + § 4.2 / § 4.3 tables.
**Evidence**: `FloorRoomBrief.has_kitchen: bool` and `has_living: bool` are optional flags. DRAFT § 3 says `LIVING — Singular — at most one per floor in v1` and treats it as always present; DRAFT § 4.2 lists LIVING furniture-floor unconditionally (16.7 m²). Same for KITCHEN (7.9 m²).
**Why it matters**: a multi-floor brief might place LIVING on the ground floor only; the upper floor's `FloorRoomBrief.has_living=False` should yield no LIVING in the room table for that floor. DRAFT's invariant 1 (`rooms.count == FloorRoomBrief-derived total count`) breaks if the implementation doesn't honor the boolean flags.
**Fix**: § 3 RoomCategory comments say `LIVING — at most one per floor; present iff brief.has_living`. § 4.2 / § 4.3 tables include a "Conditional on" column. Invariant 2 (category counts match brief) needs to enforce this.

### Finding #3 — `bathroom_count == 0` collapses the master-attached convention

**Verdict**: VALID-DEFECT.
**Severity**: MEDIUM.
**Location**: § 3 RoomCategory comments (`BATHROOM_1 may be MASTER`) + § 4.2 / § 4.3 tables.
**Evidence**: `bathroom_count: int` may be 0 (e.g. a guest floor with bedrooms but shared baths elsewhere). DRAFT § 3 says `BATHROOM_1 conventionally master-attached`; this convention is meaningless when bathroom_count is 0, but the DRAFT doesn't mention this case.
**Fix**: explicitly handle bathroom_count = 0 — the table just contains zero bathrooms. The master-attached convention only applies when bathroom_count ≥ 1 AND bedroom_count ≥ 1. Add this to § 4.2 + invariant 2.

### Finding #4 — Wrong NBC kitchen minimum (HIGH)

**Verdict**: VALID-DEFECT.
**Severity**: HIGH.
**Location**: § 4.1 regulatory minimums table.
**Evidence**: DRAFT cites kitchen min = 5.0 m². Web research (slideshare NBC bye-laws table; Unit 2 Min Space Requirements doc) shows the actual NBC 2016 numbers are:
- Kitchen alone (separate dining), dwelling **up to 50 m²**: **3.3 m²** (width 1.8 m, height 2.75 m)
- Kitchen alone, dwelling **above 50 m²**: **4.5 m²** (width 1.8 m, height 2.75 m)
- Kitchen with separate store, above 50 m²: 4.5 m² (per slideshow Building Bye Laws)
- Kitchen-cum-dining, dwelling up to 50 m²: 7.5 m² (width 2.1 m)
- Kitchen-cum-dining, above 50 m²: 7.5 m² (width 2.1 m)
- Some older NBC sources (Unit 2 doc): 5.6 m² for separate-dining kitchen

**5.0 m² is not in the NBC 2016 table.** It's a number I half-remembered from an earlier research pass.

**Why it matters**: this is an NBC compliance number. Plans we generate using 5.0 m² as the kitchen floor would technically over-size by 0.5 m² for a 50+ m² dwelling separate-dining kitchen (4.5 m² actual NBC) — minor — but the DRAFT pattern of getting "approximately right" numbers from secondary sources is exactly the wrong pattern for a regulatory KB. Worse: if the dwelling is ≤50 m², our 5.0 m² floor is *15% over-sized*, eating into other rooms unnecessarily.

**Fix**: replace § 4.1 kitchen row with the actual two-tier NBC structure:
| Dwelling size | Kitchen min m² | Width min m | Source |
|---|---|---|---|
| ≤ 50 m² | 3.3 m² | 1.8 m | NBC 2016 Part 3 § 12.3 |
| > 50 m² | 4.5 m² | 1.8 m | same |

Plus the kitchen-with-dining variant (7.5 m²) gets a separate row.

This drives a follow-on finding: the regulatory table is **dwelling-size-tiered**, not flat — which means C9 needs to know the dwelling's total floor area (or at least its tier) to look up the right values.

### Finding #5 — Wrong NBC bathroom minimum (HIGH)

**Verdict**: VALID-DEFECT.
**Severity**: HIGH.
**Location**: § 4.1 regulatory minimums table.
**Evidence**: DRAFT cites Bathroom (with WC) = 1.8 m². The actual NBC 2016 table (per the bye-laws slideshow):
- Bathroom alone (no WC), ≤ 50 m² dwelling: 1.2 m² (width 1.0 m)
- Bathroom alone, > 50 m² dwelling: 1.8 m² (width 1.2 m)
- WC alone, ≤ 50 m²: 1.0 m² (width 0.9 m)
- WC alone, > 50 m²: 1.2 m² (width 0.9 m)
- **Combined Bath + WC, ≤ 50 m²: 1.8 m²** (width 1.0 m)
- **Combined Bath + WC, > 50 m²: 2.8 m²** (width 1.2 m)

My DRAFT confused "Bathroom alone (1.8 m² above-50 dwelling)" with "Combined Bath+WC". For Indian residential plans, **Combined Bath+WC is the typical interior bathroom configuration** — separate WC rooms are rare. So the DRAFT effectively under-specifies bathroom minimum by ~36% (1.8 vs 2.8 for typical above-50-m² dwellings).

**Why it matters**: this is the floor below which we'd reject a plan as non-compliant. Setting it 36% too low means we'd ship plans that violate NBC for typical Indian use. Real compliance failure.

**Fix**: replace § 4.1 bathroom row with the dwelling-tiered structure showing all three bathroom configurations (Bath alone, WC alone, Combined). Mark Combined Bath+WC as the v1 default since it's the typical Indian residential configuration.

### Finding #6 — Resolve Q1 (FloorRoomBrief threading) now

**Verdict**: VALID-RESOLVE-NOW.
**Location**: § 2.

**Decision recommendation**: **C9 takes `FloorRoomBrief` directly as a function parameter; do NOT thread onto `CorridorDesignedCandidate`.**

Reasoning:
- C8's `CorridorDesignedCandidate` is the corridor's geometric design. Adding a brief field is mixing concerns (corridor design vs brief composition).
- C5/C6/C7/C8 already get the brief implicitly via `topology_candidate` → `corridor_sketch`. The brief is not their direct concern.
- C9 is the first component that needs explicit brief consumption (which rooms exist? how many bedrooms?). Direct injection is correct.
- This matches how C4 takes `Plot` directly even though `Plot` is also implicit upstream.

**Resolution for v0.2**: drop Q1 from open questions; § 14 architectural decisions adds "C9 takes FloorRoomBrief directly. Cardinal pattern: each component explicitly receives the upstream artifacts it consumes; implicit threading is reserved for cross-component trace correlation, not data dependency."

### Finding #7 — Resolve Q4 (master-vs-typical bedroom) now; consequence for Finding #8

**Verdict**: VALID-RESOLVE-NOW.
**Location**: § 4.2 + § 3 RoomCategory.

**Decision recommendation**: **implicit (BEDROOM_1 is master); do NOT add MASTER_BEDROOM as a separate category.**

Reasoning:
- The category enum is for **kind of room**, not **role of room**. Adding MASTER_BEDROOM mixes those.
- The master-attached pattern is a **priority/role** convention, expressed via the `priority` field on `RoomSizeRequirement`. The room_id `BEDROOM_1` carries the master semantics; the priority value (1, highest) carries the "give it the master target_m2" semantics.
- For T2/T3 large-family briefs, `bedroom_count = 4` with `priority` overridable lets users designate any bedroom as master without changing the category enum.
- Adding MASTER_BEDROOM would also force C5/C6 upstream to track which TopologyCandidate is "for" the master bedroom — the spec layer ripple is too large for the benefit.

**Resolution for v0.2**: drop Q4. § 14: "Master/non-master is a `priority` distinction, not a category distinction. BEDROOM_1 conventionally master (priority=1, target_m2 = master target); BEDROOM_2..N typical (priority=2+, target_m2 = typical target)."

### Finding #8 — DESIGN-INCONSISTENCY: § 4.2 distinguishes master from typical without representing the distinction in the schema

**Verdict**: VALID-DEFECT (after Finding #7 resolution clarifies how to fix).
**Severity**: MEDIUM.
**Location**: § 3 RoomSizeRequirement vs § 4.2 furniture-floor table.

**Evidence**: § 4.2 table has separate rows for "BEDROOM (typical)" 9.3 m² and "BEDROOM (master, BEDROOM_1)" 13.0 m². But § 3 RoomSizeRequirement has only one `liveability_min_m2` field per room. How does the implementation know whether to apply 9.3 or 13.0?

**The implicit answer** (per Finding #7 resolution): based on `room_id` parsing — if the id matches `^BEDROOM_1$`, use master; else use typical. **This is fragile** — string-parsing for semantics is exactly the anti-pattern Pattern A discipline avoids.

**Fix options**:

**(a) Add a `is_master: bool` field on `RoomSizeRequirement`.** Most explicit. Master semantics live in the schema, not in id-parsing.

**(b) Add a `furniture_profile: str` field that selects which row of `kb/furniture_floor.json` to use.** More general — opens the door to non-master variants ("BEDROOM_with_balcony", "KITCHEN_with_pantry").

**(c) Compute `liveability_min_m2` *outside* the `RoomSizeRequirement` and store the *resolved* value, with the master decision encoded in `priority`.** Resolution happens at construction-time, schema stays minimal.

**Recommendation: (a) for v1.** `is_master: bool = False` on `RoomSizeRequirement`. Flag set only on BEDROOM_1 (and on BATHROOM_1 if convention applies). This propagates the master semantic into the schema where downstream consumers (C11 placement, C14 evaluation) can read it directly.

**Resolution for v0.2**: add `is_master: bool` field to `RoomSizeRequirement`; § 4.2 furniture-floor table becomes "look up by `(category, is_master)` tuple."

### Finding #9 — `consumption_band: ZoneBand` field is C11's job, not C9's

**Verdict**: VALID-DEFECT.
**Severity**: MEDIUM.
**Location**: § 3 RoomSizeRequirement.

**Evidence**: § 3 RoomSizeRequirement carries `consumption_band: ZoneBand` ("which band this room sits in"). But C9 doesn't *place* rooms — that's C11. Where does C9 get the band assignment?

If C9 derives it (e.g., master bedroom → PRIVATE, kitchen → SERVICE), it's encoding a **placement decision** without doing placement. If C9 leaves it None, the field is dead in v1.

**The architectural truth**: C9 produces sizes; C11 places rooms within bands. The band assignment is a **C11 output**, not a C9 output. The room→band assignment depends on plot topology + corridor geometry + adjacency rules — exactly C11's input set, not C9's.

**Fix**: drop `consumption_band` from `RoomSizeRequirement`. C9's output is purely sizing. C11 attaches band assignment when it places. (If a downstream consumer needs both size and band, they consume both C9 and C11 outputs.)

This also drops invariant 10 ("every consumption_band is a valid ZoneBand") since the field doesn't exist.

### Finding #10 — `floor_label` not propagated to provenance

**Verdict**: VALID-BUT-BACKLOG.
**Severity**: LOW.
**Location**: § 10 RoomSizingProvenance.

**Evidence**: `FloorRoomBrief.floor_label: str` ("Ground", "First", etc.) is on the input but never copied to provenance. For multi-floor plans, debugging a sizing issue requires knowing which floor.

**Fix**: add `floor_label: str` to `RoomSizingProvenance`. Cheap; small schema change.

### Finding #11 — NBC width-minimum is functional, not a quality bar

**Verdict**: DESIGN-DEFICIENCY.
**Severity**: MEDIUM.
**Location**: Q2 in DRAFT.

**Evidence**: NBC 2016 Part 3 mandates min width 2.4 m for habitable rooms (above-50 m² dwellings) or 2.1 m (≤50 m²). A 9.5 m² room at 1.5 m × 6.3 m fails NBC width while passing NBC area.

DRAFT defers this as B-NNN-G ("Width-minimum check"). But Q2 frames it as a **quality concern**. It's not — it's an **NBC compliance** concern. Plans that meet area but fail width are illegal, not "low quality."

**Fix**: width minimum belongs in the regulatory_min row, not deferred to backlog. Rename `regulatory_min_m2` to a richer struct:

```python
@dataclass(frozen=True)
class RegulatoryMinimum:
    area_m2: float
    width_m: float            # NBC also mandates min width
    height_m: float = 2.75    # NBC habitable; defaulted but should match
```

Or keep flat fields: `regulatory_min_area_m2`, `regulatory_min_width_m`, `regulatory_min_height_m`.

**Resolution**: width is part of the regulatory minimum, not a separate concern. v0.2 schema must include it.

This also cascades into the validator/placement contract: C11 placement must satisfy both area AND width constraints. C11 will need to read all three regulatory floors per room.

### Finding #12 — Provenance weakness: NBC clause numbers not cited

**Verdict**: VALID-DEFECT.
**Severity**: LOW.
**Location**: § 4.1.

**Evidence**: DRAFT § 4.1 says "NBC 2016 Part 3, § 4.5" but my walk's web research suggests it's actually NBC 2016 **Part 3 Clauses 12.1, 12.2, 12.3, 12.4** (per the slideshare bye-laws table that cites these clause numbers). The DRAFT's "§ 4.5" is wrong.

**Fix**: replace § 4.1 source attributions with verified NBC clause numbers:
- Habitable rooms: NBC 2016 Part 3 Clauses 12.1.1, 12.2.1, 12.2.2 (slideshare confirmed)
- Kitchen: NBC 2016 Part 3 Clauses 12.3.1, 12.3.2
- Bathroom/WC: NBC 2016 Part 3 Clause 12.4 (referenced, not exact number from web)
- Storeroom: NBC 2016 Part 3 (clause not cited in web sources I found)

Where I can't pin a clause, mark "v0.2 cites NBC 2016 Part 3 generally; v0.3 should pin exact clauses to a reviewed copy of the Code." This is honest.

### Finding #13 — § 4.4 max_m2 = 1.6 × target heuristic is unstable

**Verdict**: VALID-DEFECT.
**Severity**: LOW.
**Location**: § 4.4.

**Evidence**: § 4.4 says `max_m2 = 1.6 × target_m2`. The DRAFT's worked example calculation:
- BEDROOM target = 10.2 m²; max = 1.6 × 10.2 = **16.3 m²**
- LIVING target = 18.6 m²; max = 2.5 × 18.6 = **46.5 m²**
- BATHROOM target = 3.3 m²; max = 1.6 × 3.3 = **5.3 m²**

But § 4.4 also says "Bedrooms cap at ~26 m² (≈ 280 sqft)" — that contradicts 1.6 × 10.2 = 16.3 m². The 26 m² number assumes a *master* bedroom target ≈ 16 m², so 1.6 × 16 ≈ 26. So the 1.6 factor only matches the 26m² cap for **master bedrooms**, not typical ones.

The contradiction: § 4.4 mixes two different baseline assumptions (typical vs master) without flagging it.

**Fix**: § 4.4 separates per-category multipliers and states which target the multiplier applies to:
- BEDROOM (typical): max = 1.6 × typical_target = 16.3 m²
- BEDROOM (master): max = 1.6 × master_target = 23.8 m² (not 26 m²)
- LIVING: max = 2.5 × target = 46.5 m²
- BATHROOM: max = 1.6 × target = 5.3 m²
- KITCHEN: max = 1.6 × target = 14.9 m²

Drop the "26 m² bedroom cap" mention as inconsistent with the per-category multiplier.

### Finding #14 — Infeasibility hard-fail without C2 contract

**Verdict**: VALID-BUT-BACKLOG.
**Severity**: MEDIUM.
**Location**: § 4.6 + Q8.

**Evidence**: § 4.6 raises `RoomSizingInfeasibleError(B-NNN-A)` on infeasibility. Q8 asks "should C9 emit a (soft|hard) verdict that lets C2 retry with reduced room count?" The DRAFT defers this.

**My adjudication**: hard-fail is correct for v1 per Pattern A discipline (fail at boundary, surface to caller). The C2-retry-renegotiation contract is a real future need but cannot be designed without C2's full feasibility loop being defined first. C2 SHIPPED early in the project but its renegotiation API was minimal; expanding it to consume C9's infeasibility signal is C2's spec change, not C9's.

**Resolution for v0.2**: keep hard-fail; explicitly state in § 14 that C2's retry contract is undefined as of S33 and will require a coordinated C2+C9 spec amendment when soft-fail mode is needed. Move Q8 to § 12 backlog as "B-NNN-soft-fail" (not C9-only; cross-component spec dependency).

### Finding #15 — Test plan lacks invariant-coverage breakdown

**Verdict**: VALID-DEFECT.
**Severity**: LOW.
**Location**: § 7.

**Evidence**: § 7 says "~80–100 tests across modules" with rough per-module counts. But the DRAFT lists 10 invariants (§ 4.7) and the spec must demonstrably exercise each. The current test plan doesn't map tests to invariants.

For comparison: C8 test reconstruction (B-127, this session) explicitly mapped 275 tests to spec invariants. C5/C6/C7 specs did similar mapping at LOCK time.

**Fix**: § 7 v0.2 includes an invariant-coverage table:

| Invariant | Test count | Test file |
|---|---|---|
| Inv 1 (rooms count == brief total) | 4 | test_c9_schema.py |
| Inv 2 (category counts match brief) | 6 | test_c9_schema.py |
| Inv 3 (regulatory_min ≥ NBC) | 8 | test_c9_nbc_table.py |
| Inv 4 (liveability_min ≥ regulatory_min) | 4 | test_c9_schema.py |
| Inv 5 (target ≥ liveability_min) | 4 | test_c9_schema.py |
| Inv 6 (max ≥ target) | 4 | test_c9_schema.py |
| Inv 7 (Σ liveability_min ≤ envelope) | 6 | test_c9_orchestrator.py |
| Inv 8 (room_ids unique) | 3 | test_c9_schema.py |
| Inv 9 (priority contiguous 1..n) | 4 | test_c9_schema.py |
| ~~Inv 10 (consumption_band valid)~~ DROPPED per Finding #9 | — | — |

Expected total ≈ 43 invariant tests; plus orchestrator end-to-end (~20), allocator (~15), failure-modes (~20) → **~100 total**. Tightens the previous "~80-100" estimate.

---

## Backlog updates

Per Rule 9.2. Deltas to the DRAFT's § 12 backlog list:

**Filed during this walk** (immediate, before LOCK):
- Most findings are **spec edits** for v0.2 PROPOSED, not backlog entries. They get fixed in the spec, not deferred.
- Finding #14 → already was Q8 / B-NNN-A; reframed as "B-NNN-soft-fail-cross-component" to flag the C2 dependency.

**No new B-NNNs** at this walk's resolution — all findings are either spec-edits-now (Findings #1-#9, #11, #12, #13, #15) or DRAFT-already-listed-as-backlog (Findings #10, #14).

The DRAFT's existing 9 backlog items (B-NNN-A through B-NNN-I) carry forward, with B-NNN-A reframed and B-NNN-G (width minimum) **moved out of backlog and into v0.2 spec body** (per Finding #11).

Net backlog count for C9 at end of walk #1: **8** (was 9; one moved into spec body).

---

## Summary recommendations for v0.2 PROPOSED

The DRAFT needs the following edits before going to walk #2:

1. **Type fixes** (Finding #1): rename `StructuralGrid` → `Grid`.
2. **Brief optionality** (Findings #2, #3): handle `has_kitchen=False`, `has_living=False`, `bathroom_count=0` cases. Update invariant 2.
3. **NBC numbers** (Findings #4, #5, #12): replace § 4.1 with dwelling-tiered table; verify clause numbers; add bath+WC/WC-alone/combined distinction.
4. **Schema enrichment** (Findings #8, #11): add `is_master: bool` to RoomSizeRequirement; replace `regulatory_min_m2` with `(regulatory_min_area_m2, regulatory_min_width_m, regulatory_min_height_m)` triple.
5. **Drop band assignment** (Finding #9): remove `consumption_band` field from RoomSizeRequirement; remove invariant 10.
6. **Cap consistency** (Finding #13): make max_m2 multipliers per-category with separate typical/master rows.
7. **Q1, Q4 resolved** (Findings #6, #7): write decisions into § 14, drop from open questions.
8. **Provenance enrichment** (Finding #10): add `floor_label: str`.
9. **Test plan** (Finding #15): add invariant→test mapping table.
10. **Q8 reframed** (Finding #14): describe as cross-component dependency with C2 retry spec.

After these edits → C9 v0.2 PROPOSED, awaiting walk #2 (your reviewer round).

---

## End of Walk #1
