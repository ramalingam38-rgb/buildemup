# C3a SPEC v0.2.1b AMENDMENT — Wording Corrections (LOCKED)

**Status:** LOCKED
**Authored:** S56, May 16, 2026, Ramalingam + Claude
**Parent spec:** `buildemup_C3a_SPEC_v0_2_1a_LOCKED.md` (same directory)
**Type:** Additive amendment — corrects three small wording / documentation drifts in the parent. **The parent's LOCKED text is NOT modified.** This amendment file is the new normative source for the items below.

---

## Scope

This amendment closes three Bucket C polish items filed against the parent C3a LOCKED spec:

| Backlog ID | What it is | Resolution in this amendment |
|---|---|---|
| **B-015** | Parent § 4.7 names third early-plot-hint classifier `_is_physical_tier_width(c)`; the actual S5 implementation is `_is_narrow_plot_width(c)` matching `EC_002_PLOT_WIDTH_INSUFFICIENT`. | § 4.7 reading is **corrected** here: the third classifier is `_is_narrow_plot_width(c)`. The implementation name is normative; the parent's name is a documentation drift. |
| **B-021** | Parent § 2.2 should document the tier → case_id mapping explicitly. (Currently it lives only as defensive contract tests `P4` in S5 v1.0.) | New § 2.2.E (this amendment) documents the canonical tier → case_id mapping. |
| **B-056** | Parent § 1.2 (ii) FORBIDDEN list intent is "no behavioural change to existing methods." S27 Flag A adjudication established that pure-additive read accessors on a FORBIDDEN-listed file ARE allowed. The parent doesn't carry that carve-out language. | New § 1.2 (ii.a) (this amendment) formalises the pure-additive-read-accessor carve-out. |

No code changes are induced by this amendment — the code is already correct (S5 implementation is authoritative for B-015; tests carry the mapping for B-021; the carve-out has been operationally applied since S27 for B-056). This amendment makes the documentation match the code.

---

## § 4.7 — Third early-plot-hint classifier (corrects parent § 4.7) — B-015

**Parent § 4.7 reads (cosmetic drift, do NOT use as normative):**

> [from parent] ... `_is_severe_envelope_shortfall(c)`, `_is_low_resolution_approval(c)`, `_is_physical_tier_width(c)` ...

**Corrected (normative):**

The third early-plot-hint classifier is **`_is_narrow_plot_width(c)`**, matching `EC_002_PLOT_WIDTH_INSUFFICIENT` in the C2 extreme-case enum. The S5 implementation in `06_upstream_codebase/buildemup/components/c03a/preflight.py` already uses this name; the parent spec's `_is_physical_tier_width` was a transcription error during the S2→S5 handoff.

**Rationale.** Physical-tier infeasibility is HARD_FAIL upstream and never produces an ExtremeCase that reaches C3a's preflight stage. The early-plot-hint exists to surface SEVERE-tier conditions to the user — and narrow plot width (`EC_002`) is the only severe-tier condition that affects the plot-shape framing. Naming the classifier after the case_id it matches (`_is_narrow_plot_width` → `EC_002_PLOT_WIDTH_INSUFFICIENT`) is correct; naming it after a tier the classifier never fires for is misleading.

**Test that locks this:** `test_c03a_session5_detector_contract.py::test_early_plot_hint_classifier_names` (already passing).

---

## § 2.2.E — Tier → case_id canonical mapping (new section) — B-021

**This is new normative content, additive to parent § 2.2.**

The C2 detector emits ExtremeCases tagged with a tier (`HARD_FAIL` / `SEVERE` / `MODERATE` / `MILD`) and a case_id. C3a's preflight builder maps each tier to a finite set of case_ids that it expects to see at that tier. Drift between these two sets is a contract violation.

The canonical mapping, as of v0.2.1b:

| Tier | Case IDs C3a expects to see | Notes |
|---|---|---|
| `HARD_FAIL` | (none reach C3a; HARD_FAIL terminates upstream) | C3a's preflight builder never receives these |
| `SEVERE` | `EC_001_PLOT_SETBACK_INSUFFICIENT`, `EC_002_PLOT_WIDTH_INSUFFICIENT`, `EC_003_PLOT_DEPTH_INSUFFICIENT`, `EC_004_SOIL_BEARING_INSUFFICIENT` | All SEVERE cases must be one of these four; new SEVERE case_ids require a parent amendment |
| `MODERATE` | `EC_010_BUDGET_ENVELOPE_TIGHT`, `EC_011_ROOM_COUNT_PER_FLOOR_AGGRESSIVE`, `EC_012_BUDGET_ENVELOPE_INSUFFICIENT` | |
| `MILD` | `EC_020_LOW_RESOLUTION_APPROVAL`, `EC_021_BUDGET_HINTED_HIGH_END_FINISH` | |

**Defensive contract test.** `S5 v1.0 P4` in `test_c03a_session5_detector_contract.py` enforces this mapping by walking every emitted ExtremeCase and asserting `case.tier in EXPECTED_TIERS_BY_CASE_ID[case.case_id]`. Future case_ids must be added to that mapping in the same commit that adds the case_id; otherwise contract tests fail.

**Tier → early-plot-hint coverage.** The three classifiers in § 4.7 (per B-015 correction) cover the SEVERE-tier cases that should produce early-plot-hint framing for the user:

- `_is_severe_envelope_shortfall(c)` → matches `EC_001` (setback) and `EC_004` (soil-bearing)
- `_is_low_resolution_approval(c)` → matches MILD `EC_020`
- `_is_narrow_plot_width(c)` → matches SEVERE `EC_002` (plot width)

`EC_003_PLOT_DEPTH_INSUFFICIENT` (SEVERE plot depth) intentionally does NOT have an early-plot-hint classifier. The reason: plot depth is more commonly negotiable (rear-setback tightening, building-line adjustment) than plot width, so the user gets the standard ExtremeCase resolution flow, not a plot-shape framing pre-flag. If a future amendment establishes that plot depth also warrants early-plot-hint framing, add `_is_short_plot_depth(c)` per the same pattern.

---

## § 1.2 (ii.a) — Pure-additive-read-accessor carve-out (new sub-section) — B-056

**This is new normative content, additive to parent § 1.2 (ii).**

The parent § 1.2 (ii) FORBIDDEN list names files that must not be modified in ordinary C3a work. The intent of the FORBIDDEN designation is **"no behavioural change to existing methods on these files."**

**Carve-out (v0.2.1b, ratified by Flag A adjudication S27, May 2 2026):**

It IS permissible to add new methods to a FORBIDDEN-listed file when ALL of the following conditions hold:

1. **Pure-additive read access only.** The new method must be a read accessor — it computes or returns information derived from existing state, with no mutation of object state, no I/O, no side effects.
2. **No existing-method modification.** The new method must be added alongside existing methods, not by modifying them. Existing public API surface, signatures, return values, and side effects MUST remain bit-identical.
3. **No new external dependency.** The new method must not introduce a new import, library, or KB reference.
4. **Documented as carve-out.** The PR adding the new method must reference § 1.2 (ii.a) and B-056 in its commit message + the new method's docstring.

**Example of permitted carve-out:** `GateStateStorage.load_status_row(token)` was added in S27 Phase 1 to support C3a's § 5a.4 implementation outline, which needs `row.is_terminal` + `row.saved_at` access. The existing `save_row` and `resume_row` methods were not modified. Pure-additive. Read-only. No new external dependency. PR cited Flag A approval + this carve-out. Permitted.

**Example of NOT permitted carve-out:** Modifying `GateStateStorage.save_row` to also store a derived field — this is not pure-additive (it changes existing-method behavior). Requires a full parent-spec amendment, not the carve-out.

**Rationale.** The FORBIDDEN list exists to prevent silent behavioural drift in storage / API / serialization layers that other components depend on. Pure-additive read accessors do not cause drift because they cannot change the existing observable behavior of any caller. Forbidding them too strictly was found in S27 to slow down legitimate work (forcing trivial structural changes through the heavyweight spec-amendment cycle). The carve-out preserves the spirit of FORBIDDEN (behavioural stability) while permitting the letter (additive surface) where it is unambiguously safe.

---

## What this amendment does NOT change

- All existing LOCKED contract tests continue to pass without modification.
- All existing public API surface, return values, and side-effect contracts are unchanged.
- The parent `buildemup_C3a_SPEC_v0_2_1a_LOCKED.md` text remains the LOCKED reference for everything outside the three sections corrected above. **For sections corrected here (§ 4.7, § 2.2, § 1.2 (ii.a)), THIS amendment is normative; the parent is informational/historical.**

---

## Versioning

Parent: v0.2.1a LOCKED (2026, multiple sessions).
This amendment: **v0.2.1b LOCKED (S56, May 16, 2026)**.

Backwards compatibility: full. No code changes required.

Successor: any further C3a wording or behavioral amendments should ship as `v0_2_1c_AMENDMENT_LOCKED.md`, `v0_2_2_AMENDMENT_LOCKED.md`, etc., bundling architect-feedback findings from B-238 where applicable.

---

## Closure record

| Backlog ID | Status |
|---|---|
| B-015 | ✅ CLOSED S56 (this amendment, § 4.7) |
| B-021 | ✅ CLOSED S56 (this amendment, § 2.2.E) |
| B-056 | ✅ CLOSED S56 (this amendment, § 1.2 (ii.a)) |
