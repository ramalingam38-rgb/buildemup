# S41 AUDIT CHECK (Rule 10.6 (b))

**Date**: S41 close (May 12, 2026)
**Purpose**: Spec-compliance audit of the v1.1 LOCKED spec against the C11a S41 code that immediately precedes C11b build.

## C11b spec v1.1 LOCKED — readiness audit

### § 2 Contract surface — verified present in spec

- `run_local_refinement(...)` signature with positional + keyword-only args ✅
- All schema types referenced: `RefinedCandidate`, `RefinedParameters`, `ObjectiveVector`, `MutationApplicationResult`, `LocalRefinementConfig`, `StubEvaluatorConfig`, `StubEvaluator`, `EvaluatorProtocol`, `LocalRefinementProvenance`, `EnvironmentFingerprint`, `PerTopologyTelemetry`, `PrimaryApplicationResult` ✅
- Failure mode hierarchy: `LocalRefinementError` → `PerTopologyError` → 5 subclasses; plus `BatchAllTopologiesFailedError`, `EvaluatorPurityContractError`, `EnvironmentFingerprintMismatchError`, `InvariantViolationError` ✅
- Module-level constants: `C11B_VERSION = "v1.1"`, `TIEBREAK_FINGERPRINT_SCHEMA_VERSION = 1`, `SEMVER_POLICY_VERSION = 1` ✅

### § 3 Behaviour — verified ordering

Phase 1 step ordering (per W5-9 Item 9 PATCH-NOW): resolve → reject MF → derive sig → derive PRNG → start timer → NSGA-II loop → telemetry capture. ✅ Specified precisely. Item 9 test: `derive_canonical_signature` NOT called for rejected MF input.

### § 4 Invariants 1-29 — present in spec

- Inv 1-25 carried verbatim from v1.0 LOCKED ✅
- Inv 26 (input artifact resolver): RAISE ✅
- Inv 27 (per-topology wallclock breach): RAISE ✅
- Inv 28 (evaluator skip cap): RAISE ✅ (cap = max(1, int(pop_size * config.evaluator_skip_cap_fraction)))
- Inv 29 (PRNG determinism + TIER-1/2/3 replay): RAISE (replay tier) ✅

Inv 29 v0.6 + v0.7 wording verified: 3-way conjunction for TIER-2 (numeric 1e-9 AND rank cardinality AND dominance relations); TIER-3 minimum semantics frozen in § 0.7.2.

### § 5 Failure modes — hierarchy verified

```
LocalRefinementError (base)
├── PerTopologyError
│   ├── NSGAConvergenceError
│   ├── AreaInfeasiblePopulationError
│   ├── EvaluatorContractError
│   ├── MultiFloorRefinementNotSupportedError    (NEW v0.4)
│   └── PerTopologyTimeoutError                  (NEW v0.4)
├── BatchAllTopologiesFailedError
├── EvaluatorPurityContractError
├── EnvironmentFingerprintMismatchError
└── InvariantViolationError                       (systemic)
```
✅ Specified.

### § 6 Test coverage — 38 new tests targeted

| Cluster | Count |
|---|---|
| v0.2 carry | ~16 |
| v0.3 carry | ~9 |
| v0.4 new (Sub-3 input resolution + Sub-2 PRNG + Sub-5 timeout) | ~12 |
| v0.5 new (Sub-1 capability flag, Sub-2 partition sentinel, Sub-4 tie-break, Sub-5 Phase 1 ordering) | ~12 |
| v0.6 new (Sub-1 capability flags, Sub-4 tie-break fingerprint, Sub-6 resolved_objective_count) | ~6 |
| v0.7 new (Sub-1 W6-1 hard assertion, Sub-4 W6-3 version anchor, Sub-3 W6-6 accessor, Sub-1 W6-8 SemVer constant, Sub-8 W6-4 TIER-3 minimum semantics) | ~8 |
| Schema general | ~28 |
| NSGA-II core | ~30 |
| Invariant coverage | ~34 |
| Phase logic | ~25 |
| Partial-batch / strict-mode | ~12 |
| Replay determinism | ~14 |
| Evaluator contract | ~12 |
| Edge cases | ~14 |

Net: 38 cluster-specific + ~190 from the carried test plan = ~228 C11b-only tests. Cumulative target: **~2947 passed at C11b ship** (2909 baseline + 38 new).

### Compliance audit against upstream C11a code

**Verified via grep on `06_upstream_codebase/buildemup/`:**
- `components/c11a/provenance.py:122` raises if `len(application_results) != 1` ✅ — C11b's defensive raise in Inv 26 aligned with C11a's `__post_init__` enforcement
- `components/c11a/source_signature.py` exports `derive_canonical_signature(input_artifact)` ✅ — C11b's PRNG seed derivation uses this
- `components/c11a/orchestrator.py:1067` constructs MTC with `application_results=(result,)` ✅ — singleton at construction
- `utilities/canonical.py` has `CANONICAL_FP_PRECISION = 6` with NO `SERIALIZATION_VERSION` constant ✅ — confirms W6-3 HIGH-severity finding; C11b's `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` cleanly anchors against this

### Decisions surfaced during audit

| # | Decision | Resolution at LOCK |
|---|---|---|
| D-1 | Should `C11B_VERSION` bump from "v1.0" to "v1.1" or to "v2.0" given mutation_semantics removal? | LOCKED at "v1.1" — v0.5/v0.6 was PROPOSED not LOCKED, so the schema change is theoretical; future post-LOCK MAJOR changes will require v2.0 |
| D-2 | Should `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` and `c11b_version` be unified? | LOCKED as TWO separate constants — tiebreak version covers fingerprint derivation, c11b version covers full surface; F-v7-1 documented; build-time commit-message discipline |
| D-3 | Should TIER-3 be implemented at v1 or deferred? | DEFERRED to B-NEW-W; § 0.7.2 freezes minimum semantics so future TIER-3 cannot fragment |
| D-4 | Should B-C11A-MTC-SINGLETON ship in v1 or backlog? | BACKLOG — touches LOCKED C11a v1.6; Ramalingam authority required for C11a amendment |

### Compliance with Rule 11 self-analysis

- v0.4 self-analysis: 7 findings, 1 PATCH-NOW folded, 1 RESOLVED via config field, 5 DOCUMENTED ✅
- v0.5 self-analysis (§ 9a): 7 findings, 1 PATCH-NOW folded, 6 DOCUMENTED ✅
- v0.6 self-analysis (§ 9b): 7 findings, 0 PATCH-NOW, 7 DOCUMENTED ✅ (but missed W6-3 HIGH-severity — externally caught at Walk #6)
- v0.7 self-analysis (§ 9c): 6 findings, 0 PATCH-NOW, 6 DOCUMENTED ✅

**Self-analysis lesson recorded**: Rule 11 self-pass is necessary but insufficient. The W6-3 HIGH-severity bug (silent fingerprint drift via canonical_serialize evolution) was visible from a Pattern B / cross-component dependency lens, but each individual self-pass focused on within-component concerns. **Future Rule 11 passes should explicitly enumerate cross-component dependencies and audit each for silent-drift risk.**

## Verdict

**SPEC v1.1 LOCKED is READY FOR BUILD.** All upstream C11a surface verified compatible. All invariants specified. All test targets enumerated. C11b Sub-1 through Sub-8 build plan in NEXT_CLAUDE_HANDOFF.md § 5 directly maps to spec sections.
