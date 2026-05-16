# C17 v0.3 LOCK RATIFICATION RECORD

**Component:** C17 — Quote Comparison Engine
**Spec version LOCKED:** v0.3
**LOCK authority:** Ramalingam (per Rule 8)
**LOCK ratification timestamp:** S50 close
**Spec file:** `spec_locks/spec_C17_v0_3_LOCKED.md`

---

## LOCK trajectory across S49–S50

| Spec version | Composed | Status |
|---|---|---|
| v0.1 PROPOSED | S49 close | Greenfield first-draft (636 lines, 12 R-invariants) |
| v0.2 PROPOSED | S50 mid | 12 SPEC-AMENDMENTs from v0.1 critique (757 lines, 18 R-invariants) |
| **v0.3 LOCKED** | **S50 close** | **4 surgical patches from v0.2 critique (522 lines, 18 R-invariants — R15 narrowed)** |

**Convergence:** v0.1 → v0.2 = 12 patches. v0.2 → v0.3 = 4 patches. v0.3 critique = **0 patches** (floor reached).

---

## Cumulative invariants at LOCK

**18 R-invariants total** (R1 through R18):
- R1–R12 inherited from v0.1
- R13–R18 added in v0.2 (itemization ⊥ competence, rate staleness, output ordering, generous-default missing-items, report-level escape valve, BOQ decomposition pluralism)
- R15 narrowed in v0.3 (from field-ordering psychology to no-headline-metadata)

---

## Test target at LOCK

- ~285 tests targeted at v1.0 implementation LOCK (per § 10)
- 0 C17 implementation code shipped yet — implementation begins now per § 9.1
- 683/683 existing tests pass (C15 + C16)

---

## Code state at LOCK

- 0 C17 source files (implementation begins now)
- v0.3 spec at `spec_locks/spec_C17_v0_3_LOCKED.md`
- Upstream contracts depended upon:
  - C7 v0.8 LOCKED (`StructuralCostEstimator`, `MaterialRate`, `RateProvider`)
  - C16 v1.2 LOCKED (`DualDrawingBundle`, `WorkingDrawingModel`, `compliance_attestation`)
  - `TransparencyTriple` (utility)
  - `AttestedValue` (from C16 contracts)
  - `AdvisoryFlag` (from C13/C14)

---

## Three-check verdict at LOCK

**GAP CHECK:** v0.3 § 0 — all 4 v0.2 critique patches delivered.
**AUDIT CHECK:** v0.3 §§ 7, 1.4, 26, 27.5 — every patch has a defined enforcement point (R15 narrowing tested via `test_c17_r15_narrowed.py`; § 1.4 tested via `test_c17_applicability_boundary.py`).
**INTEGRITY CHECK:** 683/683 existing tests green; spec file present at `spec_C17_v0_3_LOCKED.md` (522 lines).

---

## Backlog state at LOCK

| Category | Count |
|---|---|
| LOCK-mandatory (v0.1 set, must close at v1.0 implementation LOCK) | 5 |
| DEFERRED from v0.1 era | 8 |
| DEFERRED from v0.1 critique walk | 4 |
| DEFERRED from v0.2 critique walk | 8 |
| DEFERRED from v0.3 critique walk (post-LOCK addition — see § A) | 6 |
| **Total tracked** | **31** |

---

## § A — v0.3 critique walk backlog additions (post-LOCK)

Per Rule 9.2: filed at LOCK ratification time. The v0.3 critique walk
yielded 0 SPEC-AMENDMENTs and 6 backlog items, confirming convergence.

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| `B-C17-EPISTEMIC-ABSTENTION-PHILOSOPHY` | Define unified philosophy for system behavior under uncertainty. Currently fragmented across ReportConfidence, human_review_recommended, applicability boundaries, decomposition acknowledgments, advisory notes, bundle-level caveats. v1.x should consolidate into a single principle | v0.3 critique pt 1 | v1.x consolidation | M |
| `B-C17-BUNDLE-SEMANTIC-DISTINGUISHABILITY-DOWNSTREAM` | Bundle-level signals (per § 26.2) may be psychologically misread despite v0.3's 3× threshold inflation and tier downgrades. Downstream renderer should make bundle-level signals visibly distinct from line-item signals, not just numerically softer | v0.3 critique pt 3 | Renderer development | S |
| `B-C17-REGULATED-EXPLAINABILITY-MODE` | Prepare for eventual regulatory pressure on consumer-facing algorithmic judgments. § 27.5 establishes the opacity policy; this backlog covers the eventual "regulated mode" where specific thresholds become disclosed | v0.3 critique pt 4 | If/when Indian regulators address algorithmic consumer tools | M |
| `B-C17-HARD-ABSTENTION-THRESHOLDS` | Define conditions where C17 produces NO report at all (not even `human_review_recommended`). Currently the system always emits something; reviewer correctly identifies this as a structural bias toward partial-output optimism over abstention | v0.3 critique pt 5 | v1.x architectural | M |
| `B-C17-DOWNSTREAM-RENDERER-CONTRACT` | v0.3's R15 narrowing correctly moved visual hierarchy / uncertainty surfacing / graduated disclosure / caveat visibility downstream — but this means C17's philosophical safety now partly depends on renderer quality. Define minimum renderer obligations that a downstream implementation must honor | v0.3 critique pt 9 | Before first user-facing release | M |
| `B-C17-SUCCESS-METRICS-PHILOSOPHY` | Spec defines what NOT to do extensively. Does not define what success looks like. Examples: accurate comparisons? healthier conversations? fewer exploitative quotes? lower conflict? higher trust? Without explicit success philosophy, future optimization may drift | v0.3 critique pt 12 | Before post-launch optimization cycles | M |

---

## Critique walks executed (audit trail)

| Walk | Round | SPEC-AMENDMENTs | New backlog | Outcome |
|---|---|---|---|---|
| v0.1 critique | 1 | 12 (major restructure: removed `ContractorCredibility.score`, renamed enums, new mission framing, 6 new R-invariants) | 4 | → v0.2 PROPOSED |
| v0.2 critique | 2 | 4 (R15 narrowing, § 1.4 applicability, § 26 bundle scope, § 27.5 explainability) | 8 | → v0.3 PROPOSED |
| v0.3 critique | 3 | **0** | 6 | → **LOCK** |

**Standing precedent (per v0.3 § 29):** 0-amendment critique rounds are
the convergence floor. Subsequent components should aim for similar
trajectories.

---

## Next steps

**Track 3 canonical 17-component v3 status update:**

| Sub-component | Status |
|---|---|
| C1–C2, C3a, C4–C16 | ✅ SHIPPED |
| **C17** | ✅ **SPEC LOCKED at v0.3 (implementation begins)** |
| **C3b** | ⏸️ **Spec composition begins now per Ramalingam direction** |

**18 of 19 sub-components LOCKED.** C3b is the final remaining sub-component.

C17 implementation work proceeds in parallel with C3b spec composition
(both unblocked).
