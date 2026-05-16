# C13 SPEC v0.5 PROPOSED — Door Placement (delta from v0.4)

**Status**: vN PROPOSED. **LOCK-CANDIDATE pending PROCESS-AMENDMENT
satisfaction (C14 v0.1 sketch).** PENDING Ramalingam LOCK adjudication
(Rule 8).

**Predecessor**: C13 v0.4 PROPOSED DELTA.
**Origin**: S44 critique walk #5 (external review of v0.4). 15 items
walked, **4 structural amendments** (D2, D6, D7, D11) + 1 DECISION
(D15) + 10 polish-deferred backlog items + 0 pushback.

**Walk yield trajectory**:

| Walk | Total items | Structural amendments | Net character |
|---|---|---|---|
| #2 | 17 | 10 | Foundation + amendments |
| #3 | 16 | 12 (3 reversals) | C13/C14 boundary correction |
| #4 | 15 | 11 | NBC vetoes + operational maturity |
| **#5** | **15** | **4** | **Polish-dominant; diminishing structural returns** |

**This walk is the diminishing-returns inflection**. By raw count items
are still high, but by *character* the remaining concerns are
governance/operational polish rather than correctness. Per Rule 11
vigorous self-analysis + Pattern E avoidance, v0.5 absorbs only the 4
structural items and defers the 10 polish items to backlog.

This is the discipline the reviewer themselves recommends in item 15:
> "The architecture is approaching the point where MORE amendments may
> start producing diminishing architectural returns while increasing
> complexity cost."

---

## Walk #5 STRUCTURAL amendments (LOCK-blocking)

### D2 — Narrow D11.3 to require alternate route existence

**Origin**: Reviewer item 2 + web-verified cultural reality.
**Problem**: v0.4 D11.3 said "no primary circulation routes THROUGH a
kitchen for non-kitchen access." Web search confirms studio apartments,
open-plan compact homes, and modern Indian residential layouts
legitimately blend kitchen into circulation. Blanket prohibition is
culturally over-broad.
**Amendment**: Narrow D11.3:

```
v0.4 D11.3 → v0.5 D11.3 (narrowed):

"No primary circulation routes THROUGH a kitchen for non-kitchen
access WHEN an alternate non-kitchen route to the same destination
exists in the door-induced graph."

This preserves the NBC-grounded concern (no forced kitchen-transit
for accessing private rooms) while permitting open-plan layouts
where the kitchen genuinely IS the circulation space by design.
```

Implementation: D11.3 check runs AFTER door selection. For each
non-kitchen room, compute door-induced shortest path. If path
traverses a kitchen, check whether an alternate path of equal or
shorter length exists that doesn't. If yes → violation. If no →
kitchen-transit is unavoidable, permitted.

Inv D11.3' (narrowed) is still STRICT/WARN-dispatched.

Cache-relevant: yes.

---

### D6 — Primary-reachability invariant for habitable rooms

**Origin**: Reviewer item 6.
**Problem**: v0.4 C9 secondary-door graph semantics said secondary
doors CAN satisfy Inv D13 alone. Reviewer correctly identifies that
this allows pathological "habitable room reachable only via utility
secondary door" layouts.
**Amendment**: Add **Inv D17 NEW** — primary-reachability for
habitable rooms:

```python
# In Phase F:
HABITABLE_ROOM_CATEGORIES: Final[frozenset[str]] = frozenset({
    "bedroom", "master_bedroom", "guest_bedroom",
    "living", "dining", "kitchen",
    "pooja", "study",
})

# Inv D17: Every habitable room is reachable from main_entry via the
# PRIMARY-DOOR-INDUCED graph (excluding secondary doors).
#
# Non-habitable rooms (bathroom, utility, store, servant, balcony) may
# be reachable via secondary doors only.

assert every habitable room has a primary-door path to main_entry
```

This preserves C9's secondary-door benefits for service spaces while
preventing the pathology of habitable spaces routed only through
service circulation.

Cache-relevant: yes.

---

### D7 — Cross-cache consistency: advisory→geometry hash reference

**Origin**: Reviewer item 7.
**Problem**: v0.4 C10 split cache into geometry/advisory/full keys.
But advisory replay at one geometry version is incoherent.
**Amendment**: Strengthen C10:

```python
@dataclass(frozen=True)
class C13CacheKeys:
    geometry_cache_key: str
    advisory_cache_key: str  # NOW: sha256 includes geometry_cache_key
    full_cache_key: str

# Implementation:
advisory_cache_key = sha256(
    geometry_cache_key  # ← NEW: pins advisories to specific geometry
    || advisory_schema_version
    || advisory_config_relevant_fields
)
```

**Inv D18 NEW**: advisory_cache_key always contains geometry_cache_key
as a prefix component. Replay of advisories against mismatched geometry
is impossible.

Provenance addition: `DoorPlacementProvenance.geometry_cache_key`
records which geometry version produced the advisories. C14 consumers
verify advisory + geometry coherence by matching this field.

Cache-relevant: yes.

---

### D11 — Minimum C14 v0.1 sketch scope checklist (PROCESS-AMENDMENT refinement)

**Origin**: Reviewer item 11.
**Problem**: v0.4 PROCESS-AMENDMENT made C13 LOCK depend on "C14 v0.1
sketch exists" but didn't define minimum sketch scope. Risk: C13 stays
perpetually almost-lockable while C14 expands.
**Amendment**: Define the MINIMUM C14 v0.1 sketch scope explicitly.
C13 LOCK requires C14 v0.1 sketch with these (and only these) items:

```
C14 v0.1 sketch — minimum acceptable scope:

1. § 0 — Purpose: explicit boundary statement (mirror of C13 § 0.5)

2. § 1 — Inputs:
   - Consumes: DoorPlacementResult (LOCKED C13 schema)
   - Consumes: AdvisoryFlag tuple (per ADVISORY_SCHEMA_VERSION)
   - Consumes: DoorPlacementProvenance (timing + geometry_cache_key)

3. § 2 — One concrete scoring output type sketched:
   - At minimum: layout_quality_band ∈ {GOOD, ACCEPTABLE, COMPROMISED}
     per backlog B-C14-LAYOUT-QUALITY-BAND
   - Demonstrates: how AdvisoryFlags → score → band

4. § 3 — One worked example flow:
   - C12 → C13 → C14 trace for a 4-room compact residential layout
   - Shows: advisory consumption, scoring computation, band assignment

NOT required at v0.1 sketch (deferred to C14 v0.1 full spec walks):
- Privacy gradient scoring details
- Sight-line optimization algorithms
- Multi-objective Pareto handling
- Mutation/improvement suggestion generation
- Cost integration
```

This is a STRICT minimum. C14 work beyond v0.1 sketch is NOT a C13
LOCK precondition. Reviewer's concern about scheduling coupling is
addressed by bounding the sketch scope tightly.

Cache-relevant: no (process spec).

---

### D15 — MVP-LOCK scope freeze (DECISION-amendment)

**Origin**: Reviewer item 15.
**Problem**: Spec is approaching architectural perfectionism. Continued
abstract refinement is diminishing returns; empirical work yields more.
**Decision**: Freeze MVP-LOCK scope as v0.5 + the 4 walk-#5 structural
amendments. Subsequent refinements ship as v1.x post-LOCK amendments
informed by production data, not pre-LOCK abstract walks.

```
MVP-LOCK scope for C13 v1.0:

Spec content frozen:
- v0.1 base
- v0.2 amendments A1-A10 (with reversals/refinements per v0.3)
- v0.3 amendments B1-B12 + C13/C14 boundary § 0.5
- v0.4 amendments C1-C11 + PROCESS-AMENDMENT
- v0.5 amendments D2, D6, D7, D11, D15 (this walk)

Deferred to v1.x post-LOCK backlog (this walk's items 1, 3, 4, 5, 8,
9, 10, 12, 13, 14): governance frameworks, telemetry tiers, contract
registry, taxonomy grouping, linting enforcement, polish-grade
improvements. See § 12 backlog additions below.

Walk #6 (recommended): operational validation walk AFTER C14 v0.1
sketch exists, focused ONLY on:
- Does the C13/C14 boundary hold operationally?
- Do AdvisoryFlags compose correctly into C14 scoring?
- Are there end-to-end gaps not visible from C13-only view?

NOT for: more abstract refinement of C13 spec.

LOCK criteria after walk #6:
- No structural concerns surface in walk #6
- C14 v0.1 sketch passes its own minimum-criteria check (D11)
- Test scaffold mockup demonstrates Inv D1-D18 implementable
```

This is the disciplined finish reviewer item 15 advocates: stop
walking, start building.

Cache-relevant: no (process spec).

---

## Updated invariants table (v0.5)

| ID | Statement | Source |
|---|---|---|
| D1' | min_doors ≤ doors per room ≤ max_doors (≤ 2 at v1) | v0.3 B8 + v0.4 C4 |
| D2 | Every door sits on doorway_feasible SharedEdge | v0.1 |
| D3 | clear_width_m ≥ edge.min_required_clear_width_m | v0.1 |
| D4 | Door fits within edge | v0.1 |
| D5 | No two doors have overlapping swing arcs | v0.1 |
| D6 | Exactly one door has is_main_entry=True | v0.1 |
| D7 | Byte-equal replay across runs | v0.1 + A3 + A7 + B3 |
| D8 | doors tuple sorted lex-ASC | v0.1 |
| D9' | Bathroom outswing doesn't conflict with adjacent traversal | v0.2 A6 |
| D10 | clear_width_m ≤ 1.5m sanity bound | v0.1 |
| D11.1 | No door connects bathroom directly to kitchen (NBC) | v0.4 C2 |
| D11.2 | No primary circulation routes THROUGH bathroom (NBC) | v0.4 C2 |
| **D11.3'** | **No through-kitchen routing WHEN alternate route exists (narrowed)** | **v0.5 D2** |
| D11.4 | Master bedroom door doesn't open directly to kitchen/bathroom (NBC) | v0.4 C2 |
| D12' | Phase D loop-free + tie-break deterministic | v0.2 A4 + v0.3 B3 |
| D13 | All rooms reachable via door-induced graph | v0.2 A9 |
| D14 | geometric_fidelity enum, default APPROXIMATE | v0.3 B4 + v0.4 C6 |
| D15 | Secondary door's room has primary door first | v0.4 C9 |
| D16 | AdvisoryFlag density ≤ n_rooms × 1.5; deduplicated | v0.4 C1 |
| **D17 NEW** | **Habitable rooms reachable via PRIMARY-door graph (not secondary-only)** | **v0.5 D6** |
| **D18 NEW** | **advisory_cache_key always contains geometry_cache_key prefix** | **v0.5 D7** |

16 → 18 invariants. Per reviewer item 4 concern about invariant
fragmentation: the v1.x polish backlog includes formal grouping
(Geometry / Reachability / Legality / Determinism / Advisory hygiene)
as a presentation/organization improvement.

---

## v1.x polish backlog (from walk #5, deferred per D15)

These 10 items are filed as v1.x post-LOCK improvements. They are
operational polish, not LOCK-blocking correctness.

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-C13-INVARIANT-CLASSIFICATION-FRAMEWORK | LEGALITY / SAFETY / QUALITY classification for invariants + governance checklist for new amendments | Walk #5 item 1 | S (v1.x doc) |
| B-C13-CATEGORY-SPECIFIC-DENSITY-CAPS | Per-category advisory density caps (emergency never aggregated, etc.) instead of global n×1.5 | Walk #5 item 3 | S (v1.x) |
| B-C13-INVARIANT-TAXONOMY-GROUPING | Formal grouping of D1-D18 into 5 categories for documentation clarity | Walk #5 item 4 | S (v1.x doc) |
| B-C13-PHASE-D-DEBUG-PROVENANCE | Optional mutation-trail / rejected-states / rollback-reasons logging | Walk #5 item 5 | M (v1.x) |
| B-PROJECT-PIPELINE-RESULT-LINTING | Linting for new components to declare mixed-result OR typestate | Walk #5 item 8 | S (v1.x project) |
| B-C13-TELEMETRY-TIER-CLASSIFICATION | Tier minimal/debug/research split + sampling support | Walk #5 item 9 | M (v1.x) |
| B-C13-APPROXIMATE-EXPORT-RESTRICTIONS | Machine-readable fidelity metadata + export-format restrictions for APPROXIMATE outputs | Walk #5 item 10 | S (v1.x, mostly C15-side) |
| B-C13-LAYERED-PBT-STRATEGY | Shared generators/scaffolds + mutation testing for value density | Walk #5 item 12 | M (v1.x) |
| B-PROJECT-CONTRACT-REGISTRY | Centralized contract registry doc + dependency diagrams | Walk #5 item 13 | M (v1.x project) |
| B-C13-ADVISORY-CATEGORY-STRUCTURAL-RESTRICTION | Restrict advisories to "observable structural signals only" — PRIVACY/CIRCULATION/ERGONOMIC categories may need narrowing | Walk #5 item 14 | S (v1.x) |

**Total v1.x polish backlog from walk #5: 10 items.**

---

## Cumulative walk yield summary

| Walk | Items | Structural | Polish/Backlog | Reversals | Yield character |
|---|---|---|---|---|---|
| #2 | 17 | 10 amendments | 5 new backlog | 0 | Architecture-building |
| #3 | 16 | 12 amendments | 5 new backlog | 3 (boundary correction) | Boundary clarification |
| #4 | 15 | 11 amendments | 4 new backlog | 1 (NBC revival) | Operational maturity |
| **#5** | **15** | **4 amendments** | **10 polish backlog** | **0** | **Diminishing structural returns** |

Total: 37 spec amendments + 24 backlog items across 4 walks.

C12 comparison: walks 1-5 → 18 amendments + 12 backlog items.
C13 trajectory has been heavier because the C13/C14 boundary was a
late discovery (walk #3) that triggered restructuring.

Walk #5's structural-amendment rate (4/15 = 27%) vs walks #2-#4
(10-12/15-17 = ~70%) is the clearest signal of diminishing structural
returns. Polish-rate (10/15 = 67%) is the inverse signal.

---

## LOCK readiness assessment

**Architectural maturity**: HIGH. The spec has:
- Clear C12/C13/C14/C15 boundary (§ 0.5)
- 18 invariants covering correctness, safety, determinism, advisory hygiene
- Typestate API for failure-mode safety
- Cache-domain split with cross-domain consistency (D7/D18)
- Protocol abstraction for upstream coupling (B5)
- Process-level LOCK precondition discipline (D11/D15)

**Empirical maturity**: ZERO. No code shipped, no telemetry collected,
no end-to-end flow demonstrated.

**LOCK gating**:

1. ⏳ **C14 v0.1 sketch** per D11 minimum scope checklist — REQUIRED
2. ⏳ **End-to-end example** (C12 → C13 → C14 → C15 for one 4-room
   layout) — REQUIRED for boundary validation
3. ⏳ **Walk #6** focused on operational validation (not abstract
   refinement) — REQUIRED
4. ✅ **Architectural completeness** — ACHIEVED at v0.5

Once 1-3 complete, C13 LOCK candidacy can be assessed.

---

## Recommendation (Rule 11 self-analysis)

**Honest framing**: walks #2-#4 generated 33 amendments across
fundamental design issues. Walk #5 generated only 4 structural
amendments — the rest are operational polish. This is the
inflection point where further abstract refinement becomes more
expensive than empirical validation.

**Pattern E warning surfaced**: continued C13-only spec walks risk
scope-creep-mid-build. Reviewer item 15 + my own assessment converge:
the next productive work is **drafting C14 v0.1 sketch**, not walking
v0.5 abstractly.

**Three paths for your adjudication**:

1. **(a) Endorse v0.5 + START C14 v0.1 SKETCH** (my strong recommendation).
   v0.5 becomes the LOCK-candidate baseline. C14 v0.1 sketch validates
   the boundary operationally. Walk #6 of v0.5 happens after C14 v0.1
   to confirm boundary holds. Then LOCK.

2. **(b) Continue C13 walks #6, #7 first**, deferring C14 sketch.
   Risk: walk #6 yields more polish; LOCK keeps slipping; Pattern E
   gradually materializes.

3. **(c) LOCK C13 v0.5 NOW without C14 sketch**, accepting boundary
   risk. Risk: discover during C13 build or C14 integration that
   AdvisoryFlag contracts need amendment, requiring C13 v1.1 quickly.

I recommend **(a)**. The reviewer themselves endorses this path in
their final assessment.

---

Per Rule 8: vN PROPOSED. PENDING Ramalingam LOCK adjudication.

**v0.5 PROPOSED is a LOCK-CANDIDATE** (first version to reach this
status) pending only:
- C14 v0.1 sketch (per D11 minimum scope)
- One operational-validation walk after C14 v0.1 lands

This is the cleanest exit ramp from the spec walk loop. Awaiting
your direction on path (a)/(b)/(c).
