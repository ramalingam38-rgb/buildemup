# spec_C15_v0_2_LOCKED.md

**Component 15 — Layout Problem Finder**
**Status:** v0.2 LOCKED at S46.
**LOCK Authority:** Ramalingam, directive "Lock this and give me the handoff..." — S46.
**LOCK level:** SKETCH (per the project's v0.6 C13-LOCK-gating convention reused here).

---

## Reading order — the LOCKED v0.2 spec is COMPOSED FROM two files

The LOCKED state of C15 v0.2 is the union of:

1. **`spec_C15_v0_1_PROPOSED.md`** (760 lines) — the foundational v0.1 PROPOSED spec authored at S46
2. **`spec_C15_v0_2_PROPOSED_DELTA.md`** (485 lines) — 10 amendments (A1-A10) + 1 new B-NNN file layered over v0.1 from critique walk #1

These two files together constitute the LOCKED specification. The delta file is NOT a draft — its amendments are accepted into the LOCK.

**To read the locked spec correctly, read v0.1 first, then apply the v0.2 delta amendments mentally.** Where the delta amends a section, the delta wins.

---

## v0.2 LOCK summary — what is binding

### Public API contract (binding):
- `analyze_problems(...)` returns `ProblemAnalysisBatchResult` (typestate: SuccessfulProblemAnalysis / FailedProblemAnalysis)
- `analyze_problems_with_provenance(...)` returns batch + provenance
- **NO `analyze_with_ranker_hint()` entry — REMOVED per A1.** C17 reads `ProblemReport.checks` directly and computes its own aggregate. C15 is purely descriptive.
- `ProblemReport` schema per § 1.2 (v0.1) as amended by A1 (RankerHint removed), A5 (applicable_checks vs deferred_checks split), A6 (dimensions_not_evaluated), A7 (unconventional_pattern_hint), A10 (dimension_summary restructured)
- `ProblemCheck` schema per § 1.3 (v0.1) as amended by A2 (epistemic_kind field added)
- `cultural_profile` is REQUIRED parameter (no default) per A3

### Invariants (binding):
- P0-P16 (v0.1) as amended by:
  - A1: Inv P0 STRENGTHENED — C15 NEVER computes any single number representing layout quality, anywhere
  - A3: Inv P17 NEW — cultural_profile REQUIRED, no default
  - A4: Inv P18 NEW — every severity rule has severity_basis ≥ 20 characters
  - A6: Inv P19 NEW — dimensions_not_evaluated non-empty at every report

### 10 dimensions + check ID system (binding):
- Dimensions 1-10 per § 1.4 (v0.1)
- Check IDs follow `P{dimension}.{check_index}` per § 1.5 (v0.1)
- Each check carries `epistemic_kind` per A2: `regulatory` | `architectural_heuristic` | `cultural_preference`

### Data envelope (binding):
- 5/10 dimensions fully runnable with C12+C13+C14 data
- 3/10 partial (some checks runnable, others NA)
- 2/10 not runnable (Storage + Multi-functional both need furniture-fit data not in pipeline)
- Honest partial coverage at v1; future upstream extensions unlock remaining dimensions

### Moat preservation (binding):
- **No user-facing score, ever.**
- No internal aggregation in C15 (A1 enforces structurally; B-C15-MOAT-LINT enforces at CI)
- C17 owns aggregation; C15 stays descriptive
- B-C15-MOAT-AUDIT annual

### LOCK-mandatory backlog (must close before C15 v1.0 LOCK) — 7 items:
1. B-C15-SEVERITY-RULE-TABLE-LOCK
2. B-C15-CHECK-REGISTRY-LOCK
3. B-C15-CULTURAL-PROFILE-V1-LOCK (≥3 sub-variants per A3)
4. B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK
5. B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK
6. B-C15-MOAT-LINT
7. B-C15-CULTURAL-PROFILE-COVERAGE

### Cumulative backlog at LOCK: 26 items
- 7 LOCK-mandatory
- 4 data-dependency unlocks (route to upstream future components)
- 4 annual audits (B-C15-MOAT-AUDIT, B-C15-SEVERITY-AUDIT, B-C15-CHECK-ACCRETION-AUDIT, B-C15-CLASS-BIAS-AUDIT)
- 6 post-LOCK polish
- 3 project-scope (inherited from C14)
- 2 routed to other components

Per the C13 v1.0 LOCK precedent, v0.3+ amendments during implementation refine the SKETCH toward eventual v1.0 LOCK.

---

## What changed vs v0.1 (10 amendments)

| ID | Topic | Cache-relevant? |
|---|---|---|
| A1 | **Remove RankerHint from C15 entirely.** Inv P0 strengthens to "no aggregation anywhere in C15." | YES |
| A2 | Add `epistemic_kind` field to ProblemCheck (regulatory / architectural_heuristic / cultural_preference) | YES |
| A3 | Cultural profile REQUIRED, no default; ≥3 sub-variants at LOCK | YES |
| A4 | Severity rule table requires `severity_basis` citation per mapping | YES |
| A5 | ProblemReport default view: applicable_checks + deferred_checks split | YES |
| A6 | `dimensions_not_evaluated` enumeration surfaced in report | YES |
| A7 | `unconventional_pattern_hint` field + 5 v1 detection patterns | YES |
| A8 | Check-addition governance gate (§ 14.1 NEW; mirrors C14 A9) | NO |
| A9 | Explicit optimization-pressure disclosure in § 0.5 | NO |
| A10 | dimension_summary restructured: n_applicable separate from n_pass/warn/fail | YES |

Plus A11: 7 new B-NNN backlog items + 1 obsolete (B-C15-RANKER-HINT-ACCESS-CONTROL deleted per A1).

---

## Critique walks completed before LOCK

- Walk #1 (S46): produced v0.2 amendments above
- Walk #2 (S46): zero structural amendments (diminishing-returns signal); 1 new backlog item (B-C15-EVIDENCE-QUALITY-TAXONOMY); 1 scope amend (B-C15-CLASS-BIAS-AUDIT extended to cover data-availability bias)

26 cumulative backlog items after walk #2.

---

## Implementation pointers for next Claude (S47)

When implementing C15 v0.2 LOCKED spec:

1. **Inv P0 is structural.** Write the C15 module with ZERO functions returning numeric aggregates from check-contexts. B-C15-MOAT-LINT (LOCK-mandatory) should be implemented FIRST as a CI/grep check. Run it against your own code before declaring C15 done.
2. **Cultural profile API.** Implement at least 3 sub-variants (per B-C15-CULTURAL-PROFILE-COVERAGE LOCK-mandatory): `INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN`, `INDIAN_MIDDLE_CLASS_KERALA_COURTYARD`, `INDIAN_MIDDLE_CLASS_COMPACT_URBAN` (or similar). Each must produce MEASURABLY DIFFERENT outputs on the same input layout.
3. **Severity rule table.** Every entry needs `severity_basis ≥ 20 chars` citing NBC clause, Neufert page, design literature, or cultural source.
4. **Check registry.** ~35-41 checks per § 1.4 (v0.1). Each carries `epistemic_kind` (per A2). v1 implementation ships with ~20 RUNNABLE checks; ~15 emit NOT_APPLICABLE with structured `na_reason` pointing to data-dependency unlock backlog.
5. **ProblemReport schema** per A5/A6/A7/A10 — applicable_checks + deferred_checks split, dimensions_not_evaluated populated, unconventional_pattern_hint computed.
6. **Mirror C14's pattern**: typestate, WARN/STRICT, telemetry, provenance, cache key composability.
7. **C14 → C15 wiring.** C15 consumes the full CirculationGraphReport from C14. End-to-end tests should run C12 → C13 → C14 → C15 on the S45 corpus fixtures (be aware of B-C12-EDGE-DENSITY: C12 typically produces 0 shared edges in multi-room layouts; C15's data dependency on graph metrics will mostly emit NOT_APPLICABLE until C12 is fixed or fixtures use hub-and-spoke topology).

The 7 LOCK-mandatory backlog items are expected to surface during implementation. File v0.3+ PROPOSED_DELTAs as critique walks emerge.

---

**END OF v0.2 LOCKED REFERENCE.**
