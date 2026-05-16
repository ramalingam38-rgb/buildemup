# CODING MANDATE — C11a + C11b builds

**Authored at**: S37 close.
**For**: S38 Claude opening the C11a + C11b build sessions.
**Status**: explicit user directive S37 close.

---

## What you're building

Two LOCKED specs need code:

1. **C11a v1.0 LOCKED** — Topology Mutation Layer
   - Spec: `02_specs_chronological/66_C11a_SPEC_v1_0_LOCKED.md`
   - 16 mutation operators across 9 families
   - Two-tier execution (Tier A shallow / Tier B regenerative)
   - 30 invariants
   - ~205 test target

2. **C11b v1.0 LOCKED** — NSGA-II Local Refinement
   - Spec: `02_specs_chronological/69_C11b_SPEC_v1_0_LOCKED.md`
   - NSGA-II-CDP per-topology Pareto search
   - Geometric parameter refinement (room dims only at v1)
   - 25 invariants
   - ~190 test target

---

## Recommended build order

### Step 0 (BEFORE any C11a/b work) — Reconcile waiver cap

Per S37 close: Ramalingam granted 4 upstream amendment waivers
(B-NEW-J/K/L/P), but C11a § 0.2 caps active waivers at 3.

**Surface this to Ramalingam at S38 open. Two paths**:

(a) **Knock out 1 amendment first** — pick B-NEW-K (C7 staircase
clearance) OR B-NEW-L (C8 entry approach). Both XS effort (~30min).
Drops pending count to 3, respects the cap. Recommended path: keeps
C11a § 0.2 unchanged.

(b) **Amend C11a § 0.2** to raise cap from 3 to 4. Small spec edit
(small walk, not full Walk #N).

Once reconciled, proceed.

### Step 1 — Upstream amendments (XS each; or partial via path (a) above)

Per C11a Inv 24 LOCK gate, all 4 must EVENTUALLY land. Order:

| Order | ID | Component | Description | Effort |
|---|---|---|---|---|
| 1 | B-NEW-P | C7+C9+C10 | Add `severity_tier: ClassVar[Literal[...]]` to every error class | XS |
| 2 | B-NEW-K | C7 | Add staircase clearance W-numbered invariant | XS |
| 3 | B-NEW-L | C8 | Add entry-approach compatibility invariant | XS |
| 4 | B-NEW-J | C5 | Add privacy zoning rule (bedrooms not on road-facing wall) | XS |

If pursuing path (a) above: do amendments 1-3 BEFORE C11a build; defer
amendment 4 (B-NEW-J) using its waiver. Or invert: do all 4 if S38
budget allows; remove waivers entirely.

### Step 2 — C11a v1.0 build

Estimated: 3-4 sub-sessions for full ~205 tests + integration.

Recommended decomposition:
- Sub-session 1: schema + errors + provenance modules (no logic yet)
- Sub-session 2: Tier A operators (M0/M1/M2/M3/M4/M5/M9 — shallow, no
  upstream re-run); per-family slot allocation; basic test coverage
- Sub-session 3: Tier B operators (M6/M7/M8) + DeepMutationPipeline;
  caching; lineage classification
- Sub-session 4: full integration; replay tests; quarantine fingerprint;
  purity contract test discipline; final test count target met

### Step 3 — C11b v1.0 build

Estimated: 2-3 sub-sessions for full ~190 tests + integration with C11a.

Recommended decomposition:
- Sub-session 1: schema + StubEvaluator + EvaluatorProtocol + PRNG
  determinism + initialization (feasibility-aware)
- Sub-session 2: NSGA-II core (sort + crowding + selection + crossover +
  mutation) + stagnation detection
- Sub-session 3: integration with C11a; full pipeline test (C5→C11b
  end-to-end); replay tests; environment fingerprint

### Step 4 — Integration verification

End-to-end smoke test from a synthetic 12×18m brief, walking the full
pipeline:
```
Brief → C5 → C6 → C7 → C8 → C9 → C10 → C11a → C11b → (output)
```

If the smoke test passes (no errors, deterministic), call it shipped
and request LOCK confirmation from Ramalingam (Rule 8 ship-declaration
analog to S28).

---

## Spec pointer map

When implementing each phase/feature, the relevant spec section:

### C11a

| Implementation focus | Spec section |
|---|---|
| Operator enum | § 2.1 |
| Operator metadata + family + tier | § 2.2 |
| Family transition policy table | § 2.2 (`_OPERATOR_FAMILY_POLICY`) |
| Per-operator delta schemas | § 2.5 (DeltaKey enum + `OperatorExpectedDeltaSchema`) |
| Two-tier execution architecture | § 0 (intro), § 3.4 (Tier A), § 3.5 (Tier B) |
| Atomicity-by-construction | § 0.1 (purity contract) |
| Tier B caching | § 0.3 (`DeepMutationCacheKey`) |
| Mutation Legality Responsibility Matrix | § 0.4 |
| Pending-predicate sunset + waivers | § 0.2 (`UpstreamAmendmentWaiver`) |
| `MutationLineageDepth` classifier | § 2.3 (`classify_lineage_depth`) |
| `QuarantineFingerprint` + replay rule | § 2.9 (Inv 29) |
| `severity_tier` ClassVar inversion | § 2.7 |
| Phase 0 startup validation | § 3 Phase 0 |
| M5 invalidation case fixture | § 3.6 (Courtyard scenario) |
| Single-threaded contract | § 0.3 (Inv 30) |
| `validate_operator_registry()` | § 2.8 |
| Cache-relevant field annotations | § 2.5 (Inv 26) |
| Waiver registry | § 0.2 |
| Test discipline (purity, fingerprint, etc.) | § 6 + § 0.1 |

### C11b

| Implementation focus | Spec section |
|---|---|
| NSGA-II algorithm + CDP | § 0.5 (algorithm choice) |
| Determinism strategy + PRNG | § 0.6 + § 0.3 (revised) |
| EvaluatorProtocol + StubEvaluator | § 0.7 + § 0.5 (revised) |
| Refinement bounds (envelope-aware + semantic caps) | § 0.6 (revised) |
| Feasibility-aware init | § 0.7 (revised) |
| Stagnation detection (composite signature) | § 0.8 (revised) |
| Output ordering contract | § 0.9 (revised) |
| `DominanceSorterProtocol` | § 0.10 |
| `EnvironmentFingerprint` | § 0.3 (revised) |
| Phase 0 startup | § 3 Phase 0 |
| Per-topology NSGA-II run | § 3 Phase 1 |
| Output assembly | § 3 Phase 2 |
| Provenance assembly | § 3 Phase 3 |
| 25 invariants | § 4 |
| Failure modes | § 5 |
| Test target breakdown (~190) | § 6 |

---

## Test target progression

| State | Test count |
|---|---|
| S37 close | 2314 passed / 3 skipped |
| Mid-C11a build (after sub-session 1) | ~2350 |
| End of C11a build | ~2519 (target: +205) |
| Mid-C11b build (after sub-session 1) | ~2550 |
| End of C11b build | ~2709 (target: +190) |
| End of integration | ~2715-2730 (smoke + integration tests) |

Honest tolerances: +/- 10 from target acceptable; under by more than
20 is a red flag.

---

## Build verification gates per sub-session

Each sub-session MUST end with:

1. **Full test suite passes** — `pytest buildemup/tests/ -q` shows 0 failures
2. **Test count progression on track** — within tolerance of expected
3. **No new linting/import errors** — `python -c 'from buildemup.components.c11a import *'` (etc.) succeeds
4. **Master doc delta updated** — even mid-build, log incremental progress
5. **`NEXT_CLAUDE_HANDOFF.md` updated** — even within S38, capture state for next sub-session

---

## Five Patterns — C11a/C11b-specific risks

### Pattern A (fix-as-bandage)
**C11a/b risk**: spec calls for `OperatorExpectedDeltaSchema` per
operator. If during build the delta vocabulary doesn't fit reality,
DO NOT silently expand `forbidden_keys` or skip schema enforcement.
Surface as spec amendment.

### Pattern B (no-wiring)
**C11a/b risk**: C11a output (`MutatedTopologyCandidate`) is C11b's
input. Don't ship C11a build complete without verifying C11b can
consume the actual output struct. Wire end-to-end at first integration
test.

### Pattern C (scores-without-truth)
**C11b risk**: `MutationDiagnostics.novelty_estimator_fidelity = "low"`
flag. DO NOT consume novelty estimator in operational decisions. Inv 18
of C11a forbids this; same discipline applies in C11b.

### Pattern D (rules-on-rules)
**C11a risk**: 30 invariants is a lot. If a new invariant emerges
during build, ask: does it overlap an existing one? Don't double-cover.

### Pattern E (scope-creep mid-build)
**C11b risk**: `EvaluatorProtocol` forward-coupling to C14.
**Resist** the temptation to "design C14 a little" while in C11b
build. C14 is a separate component with its own future spec arc.
C11b's StubEvaluator + EvaluatorProtocol contract are sufficient.

---

## Knowledge of S37 patches that matter

The C10 item-7 patch (S37) means `_build_fixture_types_per_room` now
raises `KBVersionMismatchError` instead of silent fallback. C11a's
Tier B regeneration calls C10 in `DeepMutationPipeline`. If your test
fixtures use bathroom subtypes not in `kb/plumbing_fixture_profiles.json`,
the test will fail with a clear error rather than silent default.
This is by design.

---

## Output files expected at C11a+C11b build complete

```
buildemup/components/c11a/
├── __init__.py
├── errors.py
├── schema.py
├── provenance.py
├── operator_registry.py    (validate_operator_registry, OPERATOR_METADATA)
├── operators_tier_a.py     (M0-M5, M9 shallow operators)
├── operators_tier_b.py     (M6-M8 deep operators)
├── deep_pipeline.py        (DeepMutationPipeline)
├── viability_predicates.py (predicate orchestration)
├── purity_contract.py      (UPSTREAM_PURITY_REGISTRY, validate_*)
├── waivers.py              (UpstreamAmendmentWaiver, WAIVER_REGISTRY)
└── topology_mutator.py     (mutate_topologies entry point)

buildemup/components/c11b/
├── __init__.py
├── errors.py
├── schema.py
├── provenance.py
├── evaluator_protocol.py
├── stub_evaluator.py
├── nsga2_core.py           (sort, crowding, selection)
├── operators.py            (SBX, polynomial mutation)
├── initialization.py       (feasibility-aware seq alloc)
├── stagnation.py           (StagnationConfig + adaptive cadence)
├── bounds.py               (derive_room_upper_bounds, semantic caps)
├── dominance_sorter.py     (StandardDominanceSorter)
├── environment.py          (EnvironmentFingerprint)
└── refinement.py           (run_local_refinement entry point)

buildemup/tests/
├── _c11a_fixtures.py
├── _c11b_fixtures.py
├── test_c11a_schema.py
├── test_c11a_operators_tier_a.py
├── test_c11a_operators_tier_b.py
├── test_c11a_deep_pipeline.py
├── test_c11a_invariants.py
├── test_c11a_replay.py
├── test_c11a_purity_contract.py
├── test_c11a_waivers.py
├── test_c11b_schema.py
├── test_c11b_nsga2_core.py
├── test_c11b_evaluator.py
├── test_c11b_initialization.py
├── test_c11b_stagnation.py
├── test_c11b_bounds.py
├── test_c11b_invariants.py
├── test_c11b_replay.py
└── test_c11ab_integration.py
```

These are RECOMMENDED structures; the spec doesn't mandate exact file
naming. Use what makes sense — but match approximate granularity for
test-finding ease.

---

## Inheritance from earlier components

C11a and C11b reuse extensively from prior LOCKED components:

| What's reused | From | How |
|---|---|---|
| `canonical_serialize` | C7 amendment v0.8 | Replay determinism |
| `severity_tier` ClassVar | All upstream (post B-NEW-P) | Error classification |
| `UpstreamReplayVersionHashes` | C10 | Replay drift detection |
| `PurityAttestation` pattern | C7/C10 | Atomicity contract |
| Atomicity-by-construction (frozen dataclasses) | All upstream | Inherited |
| Single-threaded contract | C10 (Inv 30) | Inherited verbatim |
| Provenance verbosity tiers | C10 | Inherited |
| Cache-relevant field annotation | (NEW pattern, originated C11a) | Establishes pattern |

---

## End-of-build ship verification

At C11a+C11b build complete, before requesting Ramalingam ship-confirm:

- [ ] Full test suite: ~2700+ passed, no failures
- [ ] All invariants tested: C11a Inv 1-30, C11b Inv 1-25
- [ ] Replay determinism: 2 runs of same input produce byte-equal output
- [ ] End-to-end smoke (12×18m brief through full pipeline) succeeds
- [ ] No silent fallbacks in C11a's `DeepMutationPipeline` or C11b's
      initialization
- [ ] All 4 upstream amendments shipped OR waivers documented in
      provenance per spec
- [ ] Master doc v3.13 delta authored
- [ ] `NEXT_CLAUDE_HANDOFF.md` updated for next session
- [ ] Three-check protocol run (GAP/AUDIT/INTEGRITY) documented

Then request Ramalingam ship-confirm. Mirror S28 SHIP_DECLARATION.md
format.

---

**End of CODING_MANDATE. S38 awaits Ramalingam's go-ahead at session start.**
