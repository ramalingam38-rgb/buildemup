# Rule 11 Maturity-Weighted Scoring Extension (S56)

**Authored:** S56, May 16, 2026, Ramalingam + Claude
**Closes:** B-245 (Rule 11 maturity-weighted scoring extension)
**Status:** Master_doc tooling, not spec — informational, applies to project meta-process going forward.

---

## What Rule 11 is today

Rule 11 (introduced in S35, calibrated across 8 walks) is the project's self-coverage check: at each critique walk, count my own audit findings vs. the reviewer's findings, compute the overlap as a self-coverage percentage, log it. The S35 Walk #8 calibration data (in `CONSOLIDATED_S35_WALK_8_BUNDLE.md` § "Rule 11 Self-Coverage Calibration") established the pattern:

- DRAFT stage: ~58% self-coverage
- Refinement plateau: 30-43%
- Late convergence: 58-60%
- Stable ceiling around 60% for complex multi-phase specs

The single percentage is informative but coarse. It conflates findings of very different importance (a typo-class issue and a correctness-critical invariant violation count equally).

---

## What B-245 asks for

Extend Rule 11 with **maturity dimensions** — dimensions of spec/component quality that, when measured per finding, allow the self-coverage score to carry signal about WHICH parts of the work are mature vs. unstable. The original backlog filing names four dimensions:

1. **Architectural ambiguity** — questions still open or framings still debatable.
2. **Correctness-critical-unresolved** — findings that affect the validity of output (vs. cosmetic).
3. **Invariant instability** — invariants that have been amended after the initial LOCK.
4. **Replay nondeterminism** — tests that are flaky, environment-sensitive, or snapshot-dependent in undocumented ways.

---

## The extension

For each critique walk, classify EACH finding into ONE of 4 weight bands. The maturity-weighted self-coverage score is then the sum of weights of overlap-found findings divided by the sum of weights of all findings.

### Weight bands

| Band | Weight | Definition |
|---|---|---|
| **W₁ — Cosmetic / typo** | 0.25 | Wording, formatting, naming consistency. Catching it earlier or later doesn't affect output correctness. |
| **W₂ — Architectural ambiguity** | 0.50 | A framing question, a design decision that is not WRONG per se but where the choice is not motivated. Catching this matters because un-motivated decisions tend to drift. |
| **W₃ — Invariant instability** | 1.0 | An invariant that has been amended after its initial LOCK, OR an invariant whose enforcement code does not match its spec text. Catching this is critical because spec/code drift compounds. |
| **W₄ — Correctness-critical-unresolved / replay nondeterminism** | 2.0 | A finding that affects whether the system's output can be trusted (compliance miscall, calculation error, soil/setback drift, etc.) OR a test/replay that fails to be deterministic. These are the findings most worth weighting heavily because they are the ones the user actually pays the cost of. |

### Score formulas

**Maturity-weighted self-coverage (MWSC):**

```
MWSC = Σ(weight_i × overlap_i) / Σ(weight_i)
```

Where:
- `weight_i` is the weight band of finding i (one of 0.25, 0.50, 1.0, 2.0).
- `overlap_i` is 1 if the finding was caught by self-audit (independent of whether reviewer also caught it); 0 otherwise.

**Maturity-weighted reviewer-unique rate (MWRUR):**

```
MWRUR = Σ(weight_i × reviewer_unique_i) / Σ(weight_i)
```

Where:
- `reviewer_unique_i` is 1 if reviewer caught it AND self-audit did NOT; 0 otherwise.

**Interpretation rule:**

- High MWSC (>0.70) AND low MWRUR (<0.20) → self-audit is reliable; the work is converging.
- High MWSC AND high MWRUR → self-audit is reliable for cosmetic items but blind to high-weight items the reviewer keeps surfacing — recalibrate the audit checklist toward W₃/W₄ dimensions.
- Low MWSC AND low MWRUR → both self-audit and reviewer are missing things; need a third pass (architect-validation or external testing).
- Low MWSC AND high MWRUR → reviewer is doing most of the work; self-audit needs reframing or more time.

---

## Retroactive application — Walk #8 example

Re-classifying the Walk #8 findings using the maturity-weighted bands:

| Walk #8 finding | Band | Weight | Self-found? |
|---|---|---|---|
| F-v8-1: minor wording on plumbing minimums | W₁ | 0.25 | yes |
| F-v8-2: NBC citation breadcrumb missing | W₁ | 0.25 | yes |
| F-v8-3: C10 phase-7 ordering convention | W₂ | 0.50 | yes |
| F-v8-4: C7 amendment scope clarity | W₂ | 0.50 | yes |
| F-v8-5: Backlog reclassification triage | W₂ | 0.50 | no |
| **F-v8-6: REAL BUG** in C10 occupancy resolution | W₄ | 2.0 | no (reviewer-unique) |
| F-v8-7: invariant W12 amended post-LOCK | W₃ | 1.0 | yes |
| F-v8-8: replay flakiness in test_c10_strict_mode | W₄ | 2.0 | yes |
| F-v8-9–12: cosmetic spec wording fixes | W₁ (×4) | 0.25 × 4 = 1.0 | yes (3), no (1) |

Numerator (self-found, weighted):
`(0.25 + 0.25 + 0.50 + 0.50 + 0 + 0 + 1.0 + 2.0 + 0.75) = 5.25`

Denominator (all findings, weighted):
`(0.25 + 0.25 + 0.50 + 0.50 + 0.50 + 2.0 + 1.0 + 2.0 + 1.0) = 8.0`

**MWSC (Walk #8) = 5.25 / 8.0 = 65.6%**

Reviewer-unique weighted:
`(0.50 + 2.0 + 0.25) = 2.75` → MWRUR = 2.75 / 8.0 = 34.4%

**Interpretation:** Walk #8 self-audit was reliable on W₁/W₂ (cosmetic + architectural ambiguity) but missed F-v8-6 (the W₄ real bug). Recalibration suggested: the audit checklist for future walks should explicitly enumerate W₄ probes (replay determinism check, correctness-critical-against-expected-output check) so the next walk's self-audit is more likely to surface them. This matches the original Walk #8 observation that 4 real bugs in 8 walks (~10% of findings) is the audit's failure mode — maturity weighting makes that failure mode quantifiable rather than qualitative.

Compare to the raw Walk #8 score: 7/12 = 58% (or "33% raw / 58% effective" per the original calibration). The maturity-weighted score (65.6%) is slightly higher because the W₃ + W₄ items the self-audit DID find (F-v8-7 invariant amendment, F-v8-8 replay flakiness) carry heavy weight and dominate the calculation. This is the desired behavior: catching the heavy items matters more than catching the cosmetic ones.

---

## When to apply this

**Apply at every formal critique walk going forward.** Specifically:

1. **At each LOCK ratification** (e.g., C14, C15, C16 LOCK ratifications when they happen post-B-238).
2. **At any session that closes ≥ 5 backlog items.** Bands are quick to assign retroactively from the closing log.
3. **At session-handoff time** — the maturity-weighted score becomes a vector into the handoff doc, not just a single percentage.

**Don't apply at every Bucket C polish item** — the overhead exceeds the value when findings are all W₁. Reserve for non-trivial walks.

---

## What this does NOT change

- Rule 11 raw self-coverage % is still computed and logged at every walk; this extension is additive.
- The spec/component LOCK criteria are unchanged. MWSC is a meta-quality signal, not a gate.
- No code changes induced. This is pure master_doc tooling.

---

## Forward integration

When the B-238 architect feedback lands (see `04_backlog/B238_architect_engagement_packet_S56/09_feedback_intake_protocol.md`), apply maturity-weighted scoring during the post-deliverable intake. Each architect finding gets classified into a W-band per the table above, and the MWSC/MWRUR of the architect-engagement is computed against the Claude+Ramalingam pre-architect self-audit baseline. This will produce the project's first external-validated MWSC value, which becomes a yardstick for future calibrations.

If the architect surfaces ≥ 3 W₃/W₄ findings that the self-audit baseline did NOT catch, the project should pause for a self-audit-process review (recalibrate the audit checklist) before proceeding to v1 release. If the architect surfaces only W₁/W₂ findings, the self-audit baseline is validated and v1 release can proceed with the standard backlog-processing flow.

---

## Closure record

| Backlog ID | Status |
|---|---|
| B-245 | ✅ CLOSED S56 (this document) |
