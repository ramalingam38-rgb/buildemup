# C10 — Bathroom + Wet-Zone Stack Planner — SPEC v1.0 LOCKED

**Component**: 10 (canonical Track 3 numbering)
**Status**: **v1.0 LOCKED.** Supersedes v0.9 PROPOSED.
**Authority**: Ramalingam declaration at S35 Walk #9 close.
**Authored**: S35 Walk #9 outcome.
**LOCK BLOCKER cleared**: C7 amendment v0.8 LOCKED (B-212 resolved).

---

## § 0 — LOCK declaration

**Ramalingam directive at S35 Walk #9 close**: "lock both the spec docs."

Per Rule 8, this declaration constitutes the LOCK trigger. v0.9 contents promoted to v1.0 LOCKED with one minor schema delta (B-247 backlog reference) and Q45/Q46 verdicts applied. No real-bug fixes (none open at v0.9).

**B-247 patch applied** (only genuinely new finding from Walk #9): semantic conflict validation in retry coordinator filed as future post-v1 work.

---

## § 1 — Delta from v0.9 → v1.0

| Item | v0.9 status | v1.0 LOCKED resolution |
|---|---|---|
| **Q45** (likely-bound factors KB migration) | Open | **DEFERRED to B-246 post-v1**. v1.0 ships factors as `LIKELY_BOUND_FACTORS_BY_FIXTURE` Final[dict] module constant per v0.9. KB migration is post-ship. |
| **Q46** (defensive validation in `WetZonePlanProvenance.__post_init__`) | Open | **YES**. `validate_remediation_graph()` invoked from `WetZonePlanProvenance.__post_init__` for defensive depth. Bake into build implementation. |
| **Walk #9 #7** (semantic conflict beyond mutex acyclicity) | NEW finding | **FILED as B-247**. Acyclicity-only validation acknowledged as v1 limitation; full transactional retry-orchestration is C2 retry-coordinator work (post-v1). v1.0 § 8 backlog updated. |
| Walk #9 #1, #2, #3, #4, #5, #6, #8, #9, #10 | All already-filed | Confirmed; no spec change. |

**Schema, contract, behaviour (Phases 0-5), invariants 1-21, failure modes, test target (~175 tests), KB cross-validation, canonical serialisation, complexity notes: ALL UNCHANGED FROM v0.9.**

The full v0.9 spec content is hereby promoted to LOCKED state. See `59_C10_SPEC_v0_9_PROPOSED.md` for the complete normative text — all sections § 0 through § 9 carry forward verbatim under v1.0 LOCKED status, with the two delta items above applied.

---

## § 2 — Open questions resolved at LOCK

- **Q45 → DEFERRED**: B-246 covers post-v1 KB migration.
- **Q46 → YES**: defensive `__post_init__` validation in `WetZonePlanProvenance`.

All other Q1-Q44 carried from earlier walks remain resolved as documented.

---

## § 3 — Failure modes (UNCHANGED from v0.9)

```
WetZonePlanError [carries remediation_hints + failure_phase]
├── PerCandidateError
│   ├── WetZoneInfeasibleError (consolidated)
│   │   └── PreClusteringInfeasibleError
│   │       (failure_phase ∈ {"pre_clustering", "post_clustering_spatial", "assignment"})
│   ├── PoojaAdjacencyError
│   ├── RiserCountExceededError
│   ├── TrapArmDistanceExceededError
│   ├── WallCapacityExceededError
│   └── ClusterIntegrityError
├── BatchWetZoneInfeasibleError
├── PlumbingConfidenceTooLow                             (systemic)
├── KBVersionMismatchError                               (startup-time)
└── RemediationGraphError                                (systemic Phase 5 mutex-graph validation)
```

---

## § 4 — Open backlog (UPDATED v1.0)

**CORRECTNESS-CRITICAL (pre-launch, not pre-LOCK)**:
- B-220: Full hydraulic primitives + plumbing-engineer review
- B-222: Plumbing KB primary-source verification (NBC 2016 Part 9 + IS 1742 + state codes)

**INFRASTRUCTURE**:
- B-219, B-224, B-234a/b, B-236, B-237, B-238, B-241, B-245

**OPTIMIZATION**:
- B-213, B-216, B-223, B-228

**FEATURE (v2+)**:
- B-225, B-227, B-229, B-232, B-246 (KB migration of LIKELY_BOUND_FACTORS — Q45 deferral)

**POLYGONAL (B-066 era)**:
- B-217, B-226, B-231, B-235, B-242

**RESEARCH (v3+)**:
- B-230, B-233

**NEW v1.0**:
- **B-247** (NEW): Semantic conflict validation for `RemediationHint` retry orchestration. Beyond v1.0's mutex-DAG-acyclicity check, ensure jointly-applied hints don't create downstream infeasibility. Transactional simulation + rollback-safe plans. Trigger: when retry coordinator becomes a real production system. Post-v1. Effort: M.

**RESOLVED across spec arc**:
- B-218 (RESOLVED-AS-MISFRAMED at S35 Walk #2)
- B-221 (IMPLEMENTED in v0.6)
- B-239 (IMPLEMENTED in v0.8)
- B-240 (IMPLEMENTED in C7 v0.7)
- B-243 (IMPLEMENTED in v0.9)
- B-244 (IMPLEMENTED in v0.9)
- **B-212 RESOLVED** at LOCK (C7 amendment v0.8 LOCKED)

**DORMANT**: B-214, B-215.

---

## § 5 — Build session readiness

**Both LOCKs achieved at S35 Walk #9 close (Ramalingam directive). Build session begins immediately.**

C10 v1.0 build scope:
- 9 new modules under `components/c10/`: errors.py, schema.py, scoring.py, occupancy.py, clustering.py, assignment.py, trap_arm.py, provenance.py, wet_zone_planner.py, __init__.py
- 2 KB JSONs: `kb/plumbing_minimums.json` (v1), `kb/plumbing_fixture_profiles.json` (v2)
- ~175 tests across 7 test files: schema, invariants, phase-logic, partial-batch tolerance, STRICT-mode escalation, deterministic-replay snapshots, KB cross-validator
- Cumulative target: 2155 + 175 ≈ **2330 passed**
- Production-default config: `require_verified_plumbing=True` (until B-220 + B-222 land)

**Backwards-compatibility verified**: C9 SHIPPED + C7 v0.8 amendment additive only. No regressions on existing 2155-test baseline.

**Pre-launch gates remain**: B-220 (full hydraulics) + B-222 (KB primary-source verification). LAUNCH ≠ LOCK; v1 LAUNCHes only after both correctness-critical items complete.

---

## § 6 — Status

- **v1.0 LOCKED.** Authority: Ramalingam declaration, S35 Walk #9 close.
- **B-212 RESOLVED** (C7 amendment v0.8 LOCKED).
- B-247 newly filed; all other Walk #9 items already-filed-as-backlog.
- 0 open walk findings; 0 open questions.
- 9-walk spec arc complete (Walks #1 through #9 of S35).
- **Build session begins next session per Ramalingam directive.**

---

**End of v1.0 LOCKED. Authority: Ramalingam declaration, S35 Walk #9 close.**
