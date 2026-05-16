# spec_C14_v0_2_LOCKED.md

**Component 14 — Connection-Graph Quality Engine**
**Status:** v0.2 LOCKED at S46.
**LOCK Authority:** Ramalingam, directive "Lock this and let's move on to c15 spec doc" — S46.
**LOCK level:** SKETCH (per the project's v0.6 C13-LOCK-gating convention reused here).

---

## Reading order — the LOCKED v0.2 spec is COMPOSED FROM two files

The LOCKED state of C14 v0.2 is the union of:

1. **`spec_C14_v0_1_PROPOSED.md`** (553 lines) — the foundational v0.1 PROPOSED spec authored at S46
2. **`spec_C14_v0_2_PROPOSED_DELTA.md`** (385 lines) — 12 amendments (A1-A12) layered over v0.1 from critique walk #1

These two files together constitute the LOCKED specification. The delta file is NOT a draft — its amendments are accepted into the LOCK.

**To read the locked spec correctly, read v0.1 first, then apply the v0.2 delta amendments mentally.** Where the delta amends a section, the delta wins.

---

## v0.2 LOCK summary — what is binding

### Public API contract (binding):
- `analyze_circulation(...)` returns `CirculationAnalysisBatchResult` (typestate: SuccessfulCirculationAnalysis / FailedCirculationAnalysis)
- `analyze_circulation_with_provenance(...)` returns batch + provenance
- `CirculationGraphReport` schema per § 1.2 (v0.1) as amended by A1 (raw + real RA + integration + graph_size_category), A4 (structural_flags + preference_flags), A6 (truncation_meta), A8 (category_coverage)

### Invariants (binding):
- E1-E16 (v0.1) as amended by:
  - A1: E11 → E11' (raw RA unbounded) + E11'' (RRA bounded for k≥4) + E12' (integration); E17 NEW (graph_size_category)
  - A2: E3 → E3' (EXTERNAL exclusion both sides)
  - A6: E13 → E13' (truncation meta-flag accommodation)
  - A8: E18 NEW (category_coverage populated)
- Inv E0 implicit: `CirculationFlagKind` is split into Structural + Preference

### LOCK-mandatory backlog (must close before C14 v1.0 LOCK):
1. B-C14-BETWEENNESS-FORMULA-LOCK
2. B-C14-PRIVACY-GRADIENT-FORMULA-LOCK
3. B-C14-TRANSIT-BEDROOM-DEFINITION-LOCK
4. B-C14-PRIMARY-EDGE-SEMANTIC-FORMALIZATION

### Fast-revision window (90 days post-LOCK):
- B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS

Per the C13 v1.0 LOCK precedent, v0.3+ amendments during implementation refine the SKETCH toward eventual v1.0 LOCK. v0.2 LOCK does NOT preclude further amendment; it stabilizes the contract surface enough to begin implementation.

---

## What changed vs v0.1 (12 amendments)

| ID | Topic | Cache-relevant? |
|---|---|---|
| A1 | RA → RRA (Hillier 1987) + small-graph caveat (graph_size_category) | YES |
| A2 | Inv E3 EXTERNAL exclusion fixed (both sides) | YES |
| A3 | SSPT citation scope honestly disclosed | NO |
| A4 | CirculationFlagKind split: Structural vs Preference | YES |
| A5 | TRANSIT_THROUGH_BEDROOM definition sharpened (BFS shortest, no avoidable alternate) | YES |
| A6 | Truncation meta-flag when density cap fires | YES |
| A7 | § 0.0 disclaimer: graph abstraction not lived experience | NO |
| A8 | Category-coverage contract + B-C12-CATEGORY-NORMALIZATION-GOVERNANCE routed | YES |
| A9 | Metric-addition governance gate (§ 14.1 NEW) | NO |
| A10 | Interpretation-neutrality statement; preference-flag defaults to `info` | YES |
| A11 | B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS bumped to fast-revision window | NO |
| A12 | New B-NNN: PRIMARY-EDGE-SEMANTIC, PROJECT-METRIC-INTERPRETATION-GOV, METRIC-ACCRETION-AUDIT, C12-CATEGORY-NORMALIZATION | NO |

12 cumulative backlog items, 4 LOCK-mandatory.

---

## Critique walks completed before LOCK

- Walk #1 (S46): produced v0.2 amendments above
- Walk #2 (S46): zero structural amendments (diminishing-returns signal); 1 new backlog item (B-C14-CONFIDENCE-BANDS-METRIC-RELIABILITY)

13 cumulative backlog items after walk #2.

---

## Implementation pointers for next Claude (S47)

When implementing C14 v0.2 LOCKED spec:

1. Inv E11' / E11'' / E17 — implement BOTH raw_RA and RRA; gate downstream consumption on graph_size_category
2. Inv E3' — EXTERNAL exclusion on BOTH sides of the edge tuple
3. CirculationFlagKind — TWO enums, NOT one
4. Per A5: TRANSIT detection uses lex-ASC canonical BFS shortest path; check for avoidable alternates (analog of C13's D11.3')
5. Per A6: when emitting flags, sort by deterministic order; truncate at `len(nodes) × 0.75 - 1` normal flags + 1 truncation_meta when over
6. Per A8: emit `category_coverage` + emit `category_coverage_low` STRUCTURAL flag below 0.5 threshold
7. Per A10: preference-flag default severity = `info`
8. Mirror C13's pattern: typestate, WARN/STRICT, telemetry, provenance, cache key composability

The LOCK-mandatory backlog items (4) are expected to surface during implementation. File v0.3+ PROPOSED_DELTAs as critique walks emerge.

---

**END OF v0.2 LOCKED REFERENCE.**
