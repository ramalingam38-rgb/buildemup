# spec_C14_v0_2_PROPOSED_DELTA.md

**Component 14 — Connection-Graph Quality Engine**
**Status:** v0.2 PROPOSED_DELTA. PENDING Ramalingam LOCK adjudication.
**Authored:** S46 (post-critique-walk-#1)
**Reads as a delta on top of:** spec_C14_v0_1_PROPOSED.md
**Origin:** Critique walk #1 on v0.1 PROPOSED, dated S46.

---

## Walk #1 summary

External reviewer + Claude self-analysis surfaced 12 patch-eligible items + 2 backlog-worthy items. Verdict distribution:

- 9 VALID-AS-PATCH (incorporated as A1-A11 amendments below)
- 2 VALID-BUT-BACKLOG (new B-NNN, see § 12)
- 5 DOCUMENTED (no amendment — either praise or already-filed)

Self-analysis surfaced 3 bugs in v0.1 that the reviewer either flagged obliquely or missed entirely:
- (a) Inv E11 mathematically false at small k → A1
- (b) Inv E3 EXTERNAL exclusion only checked one side → A2
- (c) v0.1 cited SSPT 2026 as grounding but SSPT trains on ≤7 rooms → A3

---

## A1 — Replace RA with RRA (Real Relative Asymmetry) per Hillier 1987

**Origin:** Reviewer item 3 + self-analysis (a).

**Problem:** v0.1 § 1.2 + Inv E11 specified `relative_asymmetry` with Hillier 1984's raw formula `RA = 2(MD - 1) / (k - 2)` and asserted RA ∈ [0, 1]. The assertion is mathematically false: for k=3, MD=2 → RA = 2.0. Raw RA stays in [0, 1] only for large graphs. Residential layouts are tiny (typically 2-12 nodes), so the v0.1 invariant is unenforceable.

Reviewer item 3 made the same observation operationally ("RA and integration become unstable/noisy at tiny node counts").

The well-established fix in space syntax practice is **Real Relative Asymmetry (RRA)** — Hillier, Hanson, and Graham 1987, "Ideas are in things: an application of the space syntax method to discovering house genotypes" (Environment and Planning B, 14(4), 363-385). RRA divides RA by a D-value derived from a reference graph of the same node count, keeping the result comparable across layouts of different sizes. Professional tooling (DepthmapX, QGIS Space Syntax plugin) emits both RA and RRA for exactly this reason.

**Amendment:**

Replace `relative_asymmetry: float` in `CirculationGraphReport` with:

```python
raw_relative_asymmetry: float          # Hillier 1984 formula, unbounded for small k
real_relative_asymmetry: float         # Hillier 1987 normalized, bounded [0, ~1] for k ≥ 4
integration: float                     # 1 / real_relative_asymmetry (small-k caveat applies)
```

Replace Inv E11 with:

> E11': `raw_relative_asymmetry ≥ 0` (no upper bound at small k).
> E11'': `real_relative_asymmetry ∈ [0, ~1.5]` for k ≥ 4. For k < 4, defined as `float('nan')` because the D-value reference graph is degenerate at those sizes. Downstream consumers MUST gate metric use on `len(nodes) ≥ 4`.
> E12': `integration = 1 / real_relative_asymmetry` when `real_relative_asymmetry > 0`; else `float('inf')`. Small-graph caveat: for `k < 4`, integration is `float('nan')`.

Add to § 2: **Inv E17 NEW** — small-graph caveat metric:

> E17: A new field `graph_size_category: Literal["tiny", "small", "normal"]` is emitted, where `tiny = k ∈ {1, 2}` (most metrics N/A), `small = k ∈ {3}` (RRA defined but high-noise), `normal = k ≥ 4`. Downstream consumers SHOULD check `graph_size_category` before consuming integration/RRA as authoritative signals.

**Cache-relevant:** YES (metric formulas changed → bump `C14_METRIC_VERSION` from 1 to 2 at LOCK).

---

## A2 — Fix Inv E3: EXTERNAL exclusion checks BOTH sides

**Origin:** Self-analysis (b).

**Problem:** v0.1 Inv E3 said edges exclude `room_b_id == "EXTERNAL"`. But C12's canonical lex-ASC edge ordering places `"EXTERNAL"` (capital E, 0x45) as `room_a` whenever the entry room id begins with a lowercase letter. Examples from the S45 corpus: `("EXTERNAL", "main_entry")` is lex-valid because `"EXTERNAL" < "main_entry"`. The v0.1 invariant would miss this exclusion and incorrectly include the EXTERNAL door as a graph edge, inflating `connectivity[main_entry]` by 1 and distorting all downstream metrics.

**Amendment:** Replace Inv E3 with:

> E3': `CirculationGraphReport.edges` = sorted `(d.room_a_id, d.room_b_id)` for d in doors, EXCLUDING edges where `room_a_id == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID` OR `room_b_id == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID` (both sides checked). The constant comes from C13's `contracts` module.

**Cache-relevant:** YES (excluded edges affect every metric → bump `C14_VERSION`).

---

## A3 — Disclose SSPT citation scope honestly

**Origin:** Self-analysis (c) + reviewer items 3, 6, 11 collectively.

**Problem:** v0.1 § 0 cited "verified against 2026 SSPT paper" as grounding for door-mediated adjacency at C14's residential scale. SSPT trains on ≤7-room plans and benchmarks at 8 rooms. That citation does NOT actually support the metric behavior at the 2-4 room counts that C12 typically produces (per S45 corpus B-C12-EDGE-DENSITY finding).

**Amendment:** Replace v0.1 § 0 "academic grounding" paragraph with:

> Academic grounding: Hillier & Hanson 1984 ("The Social Logic of Space") for the door-mediated adjacency graph and the depth/integration metric family. Hillier, Hanson & Graham 1987 ("Ideas are in things") for RRA — the size-normalized variant required for small graphs. The 2026 SSPT paper (Jiang & Zhang, arXiv 2602.22507) uses the SAME door-mediated adjacency construction at the 7-8 room benchmark, but does NOT validate metric behavior at residential-scale 2-4 rooms. Small-graph behavior is therefore handled defensively via Inv E17 (small-graph caveat) + A1 RRA normalization, NOT by appeal to academic validation we don't have. v1.0 LOCK should target empirical calibration via the adversarial integration corpus before claiming metric authority.

**Cache-relevant:** NO (documentation only).

---

## A4 — Split CirculationFlagKind into STRUCTURAL vs PREFERENCE

**Origin:** Reviewer items 1, 12.

**Problem:** v0.1's five `CirculationFlagKind` values mix two semantic categories. `TRANSIT_THROUGH_BEDROOM`, `PRIVACY_GRADIENT_VIOLATION`, `EXCESSIVE_DEPTH` are culturally-loaded preferences (a studio apartment doesn't have a privacy gradient; a ceremonial-sequence home may DESIRE high depth). `BOTTLENECK_CONCENTRATION` and `DEAD_END_ISOLATION` are closer to universal pathologies (any layout where one room is the only path to all others is a structural concern regardless of cultural context).

Conflating them under one enum prevents downstream consumers from weighting them differently — and risks the C14 output reading as architectural ideology rather than circulation analysis.

**Amendment:** Replace `CirculationFlagKind` with two enums:

```python
class StructuralCirculationFlagKind(StrEnum):
    BOTTLENECK_CONCENTRATION = "bottleneck_concentration"
    DEAD_END_ISOLATION = "dead_end_isolation"

class PreferenceCirculationFlagKind(StrEnum):
    TRANSIT_THROUGH_BEDROOM = "transit_through_bedroom"
    PRIVACY_GRADIENT_VIOLATION = "privacy_gradient_violation"
    EXCESSIVE_DEPTH = "excessive_depth"
```

Replace `circulation_flags: tuple[CirculationFlag, ...]` in `CirculationGraphReport` with:

```python
structural_flags: tuple[CirculationFlag, ...]
preference_flags: tuple[CirculationFlag, ...]
```

Each flag's `flag_kind` field is typed as the union: `StructuralCirculationFlagKind | PreferenceCirculationFlagKind`.

Downstream consumers (C15 / C17) can weight structural and preference flags independently — and downstream UX can label preferences explicitly so users know it's a *preference*, not a *defect*.

**Cache-relevant:** YES (schema change → bump `C14_VERSION`).

---

## A5 — Sharpen TRANSIT_THROUGH_BEDROOM definition for v0.1 SKETCH

**Origin:** Reviewer item 5.

**Problem:** v0.1's spec text says "a bedroom is on the shortest path between main_entry and another room" but doesn't define which shortest path, all-pairs vs entry-pairs, or what to do with ties. The reviewer raises real cases (bedroom between balcony and living; family lounge through master bedroom culturally acceptable).

**Amendment:** v0.2 LOCKS the SKETCH-level definition:

> A bedroom room R is flagged TRANSIT_THROUGH_BEDROOM iff there exists a pair `(A, B)` where `A, B ∉ {bedroom_category_keywords}`, `A ≠ B ≠ R`, AND R appears in the INTERIOR (not endpoint) of the lex-ASC canonical BFS shortest path from A to B, AND no alternate equal-length path exists that avoids all bedroom-category rooms.

This v0.2 definition:
- Uses BFS lex-ASC tie-break (same as C13 Phase F replay determinism)
- Restricts to non-bedroom endpoints (so bedroom-to-bedroom doesn't trigger)
- Requires *no avoidable* alternate (so layouts where the bedroom-traversal is genuinely the only route get a free pass — analog of C13's D11.3' alternate-path narrowing)

This is the v0.2 PROPOSED definition. `B-C14-TRANSIT-BEDROOM-DEFINITION-LOCK` (already filed in v0.1 § 12) is retained for v1.0 LOCK refinement — specifically to settle questions the reviewer raised:
- Do we use ALL pairs `(A, B)` or only main_entry-anchored pairs?
- Should "bedroom" extend to other private-category rooms (study, pooja, master_bedroom)?
- How do we handle the family-lounge-through-master case (culturally acceptable)?

**Cache-relevant:** YES (flag emission semantics changed → bump `C14_METRIC_VERSION`).

---

## A6 — Truncation meta-flag when density cap triggers

**Origin:** Reviewer item 9.

**Problem:** v0.1 Inv E13 caps `circulation_flags` count at `k × 0.75`. Reviewer correctly observes that graph pathologies often cluster (a bad layout legitimately deserves many warnings) and the cap could hide secondary issues, biasing toward earlier checks in fixed-iteration order.

The elegant fix is to emit a meta-flag indicating truncation occurred.

**Amendment:**

Add to both `StructuralCirculationFlagKind` and `PreferenceCirculationFlagKind`:

```python
TRUNCATION_META = "truncation_meta"
```

(Same string in both; emission goes to whichever tuple was over-cap.)

Replace Inv E13 with:

> E13': `len(structural_flags) + len(preference_flags) ≤ len(nodes) × 0.75`, with the understanding that if more flags would have been emitted, a single `TRUNCATION_META` flag replaces the last slot of the over-cap tuple. The `TRUNCATION_META` flag's `explanation_template` MUST include the count of suppressed flags and a stable enumeration of suppressed flag kinds.

**Cache-relevant:** YES (output schema change → bump `C14_VERSION`).

---

## A7 — Graph-abstraction-not-reality disclaimer at § 0.0

**Origin:** Reviewer item 6.

**Problem:** v0.1 § 0.1-0.2 describes what C14 IS and IS NOT, but doesn't prominently warn that graph metrics are abstractions, not lived experience. Reviewer correctly notes "two layouts may have identical graphs but radically different lived experience" — and that downstream consumers may overinterpret.

**Amendment:** Add new § 0.0 at the top of the spec:

> ## § 0.0 — IMPORTANT: C14 is graph abstraction, not lived experience
>
> C14 computes Hillier-tradition Space Syntax metrics on the door-induced adjacency graph. Those metrics are abstractions. They DO NOT capture:
> - Room dimensions or proportions
> - Doorway clear widths or sight lines
> - Vertical perception (low ceilings, double-height)
> - Furniture placement or built-in storage
> - Acoustic separation
> - Material qualities (transparent vs opaque dividers)
> - Lighting (natural and artificial)
> - Outdoor connection (windows, balconies, courtyards)
> - Cultural/lifestyle preferences (open-plan vs ceremonial sequence, multigen)
>
> Two layouts may have IDENTICAL C14 reports but radically different lived experience. Downstream consumers (C15 in particular) own the bridge from graph topology to architectural quality, AND from architectural quality to lived experience. C14's job stops at the graph.
>
> Treat C14 metrics as **heuristic signals**, never as authoritative architectural judgments.

**Cache-relevant:** NO (documentation only).

---

## A8 — Category-coverage contract + routed C12 amendment hint

**Origin:** Reviewer item 10.

**Problem:** C14's flag emission rules depend critically on `room_categories` upstream. Misclassified rooms produce incorrect circulation judgments — and worse, the misclassification is INVISIBLE to C14 (no error, just bad output).

**Amendment:**

(a) Export the exact category keyword sets C14 consumes, as importable module-level constants:

```python
BEDROOM_CATEGORY_KEYWORDS: Final[frozenset[str]] = frozenset({
    "bedroom", "master_bedroom", "guest_bedroom", "kids_bedroom",
})

PUBLIC_CATEGORY_KEYWORDS: Final[frozenset[str]] = frozenset({
    "living", "dining", "family", "lounge", "kitchen",
})

PRIVATE_CATEGORY_KEYWORDS: Final[frozenset[str]] = frozenset({
    "bedroom", "master_bedroom", "guest_bedroom", "kids_bedroom",
    "bathroom", "study", "pooja",
})

CIRCULATION_CATEGORY_KEYWORDS: Final[frozenset[str]] = frozenset({
    "corridor", "foyer", "staircase",
})
```

(b) Add `category_coverage: float` field to `CirculationGraphReport`, defined as: fraction of input `placed_room_ids` whose `room_categories[room_id]` keyword appears in at least one of the four sets above. `category_coverage ∈ [0, 1]`.

(c) Add Inv E18 NEW: `category_coverage` populated. Low coverage (default threshold 0.5) emits a STRUCTURAL flag `category_coverage_low` indicating downstream consumers SHOULD verify upstream categorization quality.

(d) Routed amendment hint to C12: file `B-C12-CATEGORY-NORMALIZATION-GOVERNANCE` (post-LOCK, M) — C12 maintainer's call. C14 does NOT modify the keyword sets unilaterally; if C12's normalization conventions change, that's a coordinated amendment across both components.

**Cache-relevant:** YES (new schema field → bump `C14_VERSION`).

---

## A9 — Metric-addition governance gate

**Origin:** Reviewer items 2, 15.

**Problem:** v0.1 § 0.2 lists what C14 is NOT, but doesn't codify the GATE for adding new metrics post-v1.0. The reviewer's strongest forward-looking concern is metric accretion: every new metric will appear cheap and reasonable in isolation but bloats the subsystem cumulatively.

**Amendment:** Add new § 14.1 (under § 14 LOCK readiness) titled "Metric-addition governance gate":

> ## § 14.1 — Metric-addition governance gate (post-LOCK)
>
> After v1.0 LOCK, adding any new metric or flag kind to C14 requires passing a three-criterion gate. The proposal must demonstrate:
>
> 1. **Architectural justification.** Why this metric belongs at C14 and not C15 (Layout Problem Finder). C14 is the graph abstraction layer; if the metric requires room dimensions, geometry, NBC interpretation, or lived-quality reasoning, it routes to C15.
>
> 2. **Downstream usefulness evidence.** At least one downstream consumer (C15 / C17 / C18 / UX) must commit to consuming the new metric for a concrete decision. "Might be useful someday" fails this gate.
>
> 3. **Replay-stability proof.** The metric must be computable in O(V²) or better, deterministic under Inv E7 (lex-ASC neighbour ordering), and stable across the small-graph regime (E17). No formulas that diverge at small k unless an explicit `nan` fallback is specified.
>
> The gate is enforced at critique-walk time. Backlog item B-C14-METRIC-ACCRETION-AUDIT (filed below) commits to a periodic audit (annually) of all C14 metrics against these criteria.

**Cache-relevant:** NO (governance only).

---

## A10 — Interpretation-neutrality statement

**Origin:** Reviewer item 12.

**Problem:** v0.1 implicitly suggested that lower depth / higher integration is "better" — by labeling deviations as "violations" or "concerns." Reviewer correctly observes this encodes architectural ideology. A ceremonial sequence (entry → foyer → living → dining → master bedroom, all in a deliberate linear sequence) DESIRABLY produces higher depth. A multigenerational home may DESIRABLY produce lower integration (acoustic/visual separation).

**Amendment:** Add to § 0.0 (the disclaimer) one additional paragraph:

> **Interpretation neutrality.** Lower depth / higher integration is NOT inherently better. C14 reports values; interpretation belongs downstream. A ceremonial-sequence home, a multigenerational layout, or an acoustic-separation design may DESIRABLY produce higher depth + lower integration. C14 flags emit as `severity=info` by default unless the metric is clearly pathological (orphan room reachable only via secondary doors). Severity escalation belongs to C15.

Additionally: change the default severity of all preference flags from v0.1's `warning` to `info`. Severity bumping is a C15 decision based on full architectural context, not a C14 decision based on graph topology alone.

**Cache-relevant:** YES (default severity changed → bump `C14_METRIC_VERSION`).

---

## A11 — Multi-floor scope bump to fast-revision window

**Origin:** Reviewer item 8.

**Problem:** v0.1 deferred multi-floor cross-floor metrics to "post-v1.0" with effort L. Reviewer correctly observes this is more serious than v0.1 implied: many circulation-quality issues are fundamentally vertical (FF bedroom depth from GF entry, elder accessibility across floors, stair bottlenecks).

**Amendment:** Bump `B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS` priority:

- Was: post-v1.0, L effort, undated
- Now: **v1.x fast-revision window (90 days post-LOCK), L effort**

The bump means: C14 v1.0 LOCK proceeds with per-floor independent graphs (current v0.1 design), but C14 v1.1 (within 90-day window) MUST add cross-floor metrics. If the window closes without the addition, it converts to a post-LOCK breaking change requiring v2.0 governance.

**Cache-relevant:** NO (scope/governance only).

---

## A12 — New backlog items filed (reviewer items 7, 11)

**Origin:** Reviewer items 7, 11.

**Amendment:** File two new B-NNN items in § 12:

| ID | Description | Origin | Trigger | S{N}-scope | Effort |
|---|---|---|---|---|---|
| B-C14-PRIMARY-EDGE-SEMANTIC-FORMALIZATION | Formal definition of what architectural meaning "primary edge" encodes; currently provenance-dependent on C13's is_secondary | Reviewer #7 | v1.0-LOCK-MANDATORY | C14 v1.0 | S |
| B-PROJECT-METRIC-INTERPRETATION-GOVERNANCE | Project-wide governance for downstream metric-interpretation consistency (preventing C15/C17/UI from each deriving their own weighting) | Reviewer #11 | post-LOCK | v2.x project | L |
| B-C14-METRIC-ACCRETION-AUDIT | Periodic (annual) audit of all C14 metrics against the three-criterion gate (A9) | Walk #1 | post-LOCK | C14 v1.x | S |
| B-C12-CATEGORY-NORMALIZATION-GOVERNANCE | C12 maintainer concern — coordinated amendment process for room-category normalization changes that affect C13/C14/C15 | A8 | post-LOCK | C12 v1.x | M |

---

## § 12 — Backlog (full roll-up after v0.2)

Combining v0.1's 7 items + v0.2's 4 new items, the C14 backlog now stands at **11 items**:

### LOCK-mandatory (must close before v1.0 LOCK)

| ID | Description |
|---|---|
| B-C14-BETWEENNESS-FORMULA-LOCK | Pin exact betweenness formula |
| B-C14-PRIVACY-GRADIENT-FORMULA-LOCK | Pin exact privacy-gradient monotonicity formula |
| B-C14-TRANSIT-BEDROOM-DEFINITION-LOCK | Pin transit-bedroom definition (A5 ships SKETCH-level; full LOCK still required) |
| B-C14-PRIMARY-EDGE-SEMANTIC-FORMALIZATION | Pin primary-edge architectural semantics |

**Total LOCK-mandatory: 4.**

### Fast-revision window (90 days post-LOCK)

| ID | Description |
|---|---|
| B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS | Bumped from post-v1.0 to v1.x window per A11 |

**Total fast-revision: 1.**

### Post-LOCK polish (C14 v1.x)

| ID | Description |
|---|---|
| B-C14-CACHE-SPLIT-IF-DIVERGENT | Split full_cache_key into geometry/advisory only if divergent use case |
| B-C14-ISOVIST-SUPPORT | Sight-line / isovist analysis |
| B-C14-METRIC-ACCRETION-AUDIT | Annual audit per A9 gate |

**Total post-LOCK polish: 3.**

### Project-scope (v2.x)

| ID | Description |
|---|---|
| B-PROJECT-PIPELINE-METADATA-CONTRACT | Convention for "upstream metadata threaded as params" |
| B-PROJECT-ADVISORY-UNIFICATION | Unify C14 + C15 + C16 advisories under versioned registry |
| B-PROJECT-METRIC-INTERPRETATION-GOVERNANCE | Cross-component metric-interpretation consistency |

**Total project-scope: 3.**

### Routed to other components

| ID | Description | Routed to |
|---|---|---|
| B-C12-CATEGORY-NORMALIZATION-GOVERNANCE | Room-category normalization coordination | C12 maintainer |

**Total routed: 1.**

**Spec § 12 summary: 11 C14 items + 1 routed = 12 cumulative.**

---

## § 14.2 — LOCK readiness UPDATED after v0.2

**Architectural maturity at v0.2 PROPOSED:** SKETCH with one cycle of patches. Boundary discipline strengthened (A4, A7, A10), small-graph mathematics fixed (A1, A2), governance codified (A9), backlog enumerated (12 items, 4 LOCK-mandatory).

**Empirical maturity:** Still ZERO. C14 has not been built.

**Anticipated LOCK path:**

Path (a) — quick LOCK: Lock v0.2 as the SKETCH-level spec. The SKETCH addresses all of v0.6 C13-LOCK-gating's "C14 v0.1 sketch" requirement. Pre-implementation refinement (formulas, edge cases) happens via v0.3+ critique walks during the implementation phase, NOT as a blocker on LOCK.

Path (b) — continue walks: One more critique walk on v0.2 before LOCK. Risk: Pattern E (scope-creep-mid-build).

**Recommendation:** Path (a). The v0.6 C13-LOCK-gating requirement was for a SKETCH, not a fully-specified component. v0.2 PROPOSED is now a disciplined sketch with self-aware governance + a clear roadmap to implementation. Locking here unblocks C13 LOCK precondition immediately; pre-implementation refinement happens in walks #2+ during the build.

---

**END OF v0.2 PROPOSED_DELTA. PENDING Ramalingam LOCK adjudication.**
