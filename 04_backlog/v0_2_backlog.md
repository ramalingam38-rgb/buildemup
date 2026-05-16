# v0.2 Backlog — Component 3a

Items surfaced during the C3a build that are **not** blocking, but should be addressed before C3a v0.2 (or carried into a maintenance pass). Per the spec-first discipline: these were intentionally deferred to keep S2 and later builds against the locked SPEC v0.2.1 spec, not patched mid-build (Pattern E).

---

## Origin: Session 18 (S2 — Detection logic, 30 April 2026)

### B-001 — Add `BudgetRange.midpoint_inr()` helper

**Source:** S2 build, EC-008 detection.
**Issue:** EC-008 fires when `cost_estimate.exact_value > brief.budget_range.max_rupees * 1.5`. The spec wording uses "budget.target" loosely; the resolved-Q&A interpretation maps "target" to `max_rupees`. A `midpoint_inr()` helper would document the right thing to compare against and reduce ambiguity for future readers.
**Proposed change:** add `@property midpoint_inr` (or `target_inr`) on `BudgetRange` returning `(min_lakhs + max_lakhs) / 2 * 100_000`, with a docstring stating the EC-008 detector uses `max_rupees`, not midpoint.
**Risk:** none — pure additive helper.
**Effort:** ~5 LOC + 1 test.

### B-002 — Add `line_type` field to `electric_line_clearance` CheckResult

**Source:** S2 build, EC-010 HT/LT classification.
**Issue:** Detector reads `cr.details.get("line_type", "")` to distinguish HT (LOW resolution probability) from LT (MEDIUM). C2's `legal_only_checks.check_electric_line_clearance` does not currently populate `line_type` consistently. Detector defaults to MEDIUM when absent — safe but loses fidelity for HT cases.
**Proposed change:** in `components/c02/legal_only_checks.py`, ensure every `electric_line_clearance` CheckResult sets `details["line_type"]` to either `"HT"` or `"LT"` based on the underlying check input.
**Risk:** medium — touches C2 source. Need a regression test that pre-existing checks still pass.
**Effort:** ~10 LOC + 2 tests.

### B-003 — Mumbai and Pune stilt thresholds for EC-007

**Source:** S2 build plan, flagged item 2.
**Issue:** SPEC EC-007 says "Mumbai, Delhi, Pune" trigger the stilt mandate. C2's `legal_only_checks.STILT_MANDATE_BY_CITY` only models Delhi. Mumbai and Pune cases will currently not fire the underlying `stilt_mandate_compliance` HARD_FAIL, so EC-007 silently never fires for those two cities.
**Proposed change:** research and add Mumbai (DCPR 2034 stilt rules) + Pune (UDCPR stilt rules) thresholds to `STILT_MANDATE_BY_CITY` in `components/c02/legal_only_checks.py`. Cross-reference `kb_rules/coverage_rules.json` if appropriate.
**Risk:** low — additive city coverage.
**Effort:** ~30 LOC + 4 tests (2 cities × positive/negative).

### B-004 — Reconcile circulation factor (1.30 vs 1.35)

**Source:** S2 build, EC-001 detection comment.
**Issue:** SPEC EC-001 says circulation factor is 1.30 (per C1's `floor_requirement.estimate_floor_area_sqm`). C2's envelope check uses 1.35. Detector follows the spec (1.30); C2 is more conservative. This is currently a documentation-only discrepancy because EC-001 is a separate signal from the C2 `envelope_sufficiency` HARD_FAIL.
**Proposed change:** decide which factor is correct (probably 1.30 per C1, since it's the user-input-derived assumption) and align C2's envelope check. Or, if both should remain, document the reason explicitly in both source files and the spec.
**Risk:** low — slightly tightens or relaxes one C2 check.
**Effort:** ~5 LOC source + audit existing C2 tests.

---

## Origin: Session 19 (S3 — Option generation, 30 April 2026)

### B-005 — BriefChange `field_path` vocabulary may need refinement

**Source:** S3 build resolved-question Q2; pre-flagged in S3 orientation file 02.
**Issue:** S3 emits paths like `rooms.all.size`, `coverage.reduce_footprint`, `floors.add_stilt`, `parking.has_covered`. S4 (BriefChange application) is the layer that interprets these and mutates the Brief. Some semantics are provisional — particularly `rooms.lowest_priority` (currently never emitted by S3 but listed in the original Q2 table) and the two paths that have no Brief schema field yet (`parking.has_covered`, `coverage.reduce_footprint`). When S4 ships, vocabulary may need refinement based on what's natural to apply.
**Proposed change:** revisit the field_path vocabulary table after S4 v0.1 ships. Consolidate any paths that turned out to be ambiguous; document the canonical form.
**Risk:** medium — coordinated change across S3 + S4.
**Effort:** ~30 LOC source + ~5 tests.

### B-006 — Cut priority order should move to a configurable rule

**Source:** S3 build, ROOM_CUT_PRIORITY constant in `option_generator.py`.
**Issue:** The cut priority order (BALCONY < STORE < UTILITY < POOJA < DINING < LIVING < KITCHEN < BEDROOM_REGULAR < BEDROOM_MASTER) is currently a hardcoded constant in `option_generator.py`. Per D-006 (Era 1 locked decision) the order is fixed for now, but if user-configurable priorities are introduced (e.g., "I'd rather lose a bedroom than a balcony"), this should move to a configurable rule loaded from KB.
**Proposed change:** move ROOM_CUT_PRIORITY into a structured rule file (`kb_rules/cut_priority.json`) and load via `kb_rules_loader`. Allow per-user override at C1 capture time.
**Risk:** low — additive.
**Effort:** ~20 LOC + 3 tests.

### B-007 — Brief should capture BHK flexibility signal in C1

**Source:** S3 build resolved-question Q8.
**Issue:** SPEC EC-002 option 1 ("Reduce BHK count") says "RECOMMENDED if user expressed flexibility on BHK in C1". Brief currently has no `bhk_flexibility` field. S3 uses an interim heuristic (`bhk >= 3`) — works for most cases but loses fidelity. Same for EC-001 option B which uses shortfall thresholds.
**Proposed change:** add `bhk_flexibility: bool | None = None` (or a tier enum) to Brief; capture via a new C1 question. Update S3's recommendation logic to use the captured signal.
**Risk:** medium — touches C1 schema, brief_form.html, brief storage migration.
**Effort:** ~50 LOC + form changes + 4 tests.

### B-008 — METRO_CITIES list should move to KB rules

**Source:** S3 build, EC-003 recommendation logic.
**Issue:** Currently `METRO_CITIES = frozenset({"mumbai", "delhi", "bangalore"})` is hardcoded in `option_generator.py`. Used to flip EC-003 recommendation between "drop covered parking" (tier-2/3) and "convert to stilt" (metros). This list will need updating as cities urbanize.
**Proposed change:** add a `city_tier` field to `kb_rules/city_feasibility_defaults.json` or introduce a new `kb_rules/city_tiers.json`. Load via `kb_rules_loader`.
**Risk:** low.
**Effort:** ~15 LOC + 2 tests.

### B-009 — EC-005 permitted_coverage_pct default should read from KB

**Source:** S3 build, EC-005 option B.
**Issue:** When the `ground_coverage_compliance` CheckResult does not populate `details["permitted_coverage_pct"]`, S3 falls back to a hardcoded 60% default (typical Chennai DCR). Should read the per-city limit from `kb_rules/coverage_rules.json` instead.
**Proposed change:** in `_ec005_permitted_coverage_pct()`, read from coverage_rules.json keyed by `brief.plot.city` if CheckResult details miss it. Fall back to 60% only if both sources lack data.
**Risk:** low — additive fallback chain.
**Effort:** ~10 LOC + 3 tests.

### B-010 — EC-004 `excess_sqft` default should be reliably populated by C2

**Source:** S3 build, EC-004 option B recommendation logic.
**Issue:** When the `far_compliance` CheckResult does not populate `details["excess_sqft"]`, S3 falls back to a value above the threshold (so option B is NOT recommended). C2's `far_compliance` check should reliably set this so the recommendation logic works correctly.
**Proposed change:** in `components/c02/legal_only_checks.py`'s `check_far_compliance`, ensure `details["excess_sqft"]` is set on every HARD_FAIL outcome.
**Risk:** medium — touches C2 source.
**Effort:** ~10 LOC + 2 tests.

### B-011 — Brief schema lacks `parking` and `coverage` structured fields

**Source:** S3 build, EC-003 option A and EC-005 option B; relevant to S4.
**Issue:** S3 emits BriefChanges with `field_path = "parking.has_covered"` and `"coverage.reduce_footprint"` but Brief has no `parking` or `coverage` field. S4 v0.1 will store these acceptances in `additional_requirements` as audit-trail strings. When the schema gains structured fields, S4's two corresponding handlers should mutate those fields directly, and the strings should be removed.
**Proposed change:** add `parking: ParkingPolicy | None` and `coverage_acceptance: CoverageAcceptance | None` to Brief. Refactor S4 handlers. Migrate any `additional_requirements` strings.
**Risk:** medium — schema migration; S4 handler refactor.
**Effort:** ~60 LOC + 6 tests.

### B-012 — `FAR_EXCEEDED_BY_CHANGE` classification reserved but not produced

**Source:** S4 spec design, error classification table.
**Issue:** S4 v0.1 reserves the `FAR_EXCEEDED_BY_CHANGE` classification (templates exist in error_formatter) but the applier never proactively detects FAR violations. Today FAR is caught by C2's re-run after the change is applied. This works but means the user sees the FAR error one round-trip later than they could.
**Proposed change:** add a lightweight FAR-headroom check inside `apply_brief_change` for `floors.add` operations, classifying preemptively to `FAR_EXCEEDED_BY_CHANGE` when the new floor would exceed the city limit.
**Risk:** low — additive, optional fast path.
**Effort:** ~25 LOC + 2 tests.

### B-013 — Classification logic relies on substring-matching error messages

**Source:** S4 spec design, classification logic shape.
**Issue:** S4 v0.1's `_classify_error()` inspects `Brief.__post_init__`'s `ValueError` message text via substring matching ("count cannot be negative", "below NBC minimum", etc.). If those messages change wording, classification will silently regress to UNKNOWN. Robustness concern.
**Proposed change:** introduce typed exception classes in the Brief / RoomRequirement / FloorRequirement layer (e.g., `BedroomCountBelowMinError`, `NbcMinError`). S4 catches by type, not text. Existing `ValueError` callers stay backward-compatible by having the new types subclass `ValueError`.
**Risk:** medium — touches multiple domain files; needs careful regression coverage.
**Effort:** ~80 LOC + audit existing tests.

### B-014 — Setbacks negative/oversize errors classify as UNKNOWN

**Source:** Surfaced during S4 build (Session 20). The locked S4 spec Q7 stated that `Setbacks` has no `__post_init__` validation and so negative-result setbacks would silently succeed. **The actual `setbacks.py` code refutes this** — `Setbacks.__post_init__` raises `ValueError` for any side `< 0.0` or `> 15.0`. So a malformed `setbacks.X_m INCREMENT` (e.g., a `-2.0` delta on a `1.5m` setback) raises a `ValueError` with text `"Setback front_m=-0.5m cannot be negative."`. The S4 classifier's substring matchers don't match this text, so it falls through to `UNKNOWN`.
**Issue:** UNKNOWN gives the user a generic "this option doesn't work — try another" message instead of the specific reason. Acceptable for v0.1 (S3 only emits ±0.3 deltas, so this rarely fires in practice), but not ideal.
**Proposed change:** add a `SETBACK_INVALID` classification (with template "Setback {side} would become {result_m:.1f}m, which is outside the allowed 0–15m range.") and matching substring rules for "setback" + "cannot be negative" / "exceeds 15m".
**Risk:** low — additive only.
**Effort:** ~20 LOC + 2 tests.

---

## Origin: Session 21 (S5 — Counterfactual + Preflight builders, 30 April 2026)

### B-015 — Parent C3a spec § 4.7 wording: `_is_physical_tier_width` mismatch

**Source:** S5 spec drafting (Q1).
**Issue:** parent spec § 4.7 names third early-plot-hint classifier `_is_physical_tier_width(c)`. Per S2's detector, physical tier is HARD_FAIL upstream and never produces an ExtremeCase. S5 implements as `_is_narrow_plot_width(c)` matching `EC_002_PLOT_WIDTH_INSUFFICIENT` (severe tier — the only tier the detector ever fires for).
**Proposed change:** patch parent spec § 4.7 wording in next revision.
**Risk:** none — cosmetic.
**Effort:** ~5 LOC parent spec.

### B-016 — Composite weighted ranking for counterfactual alternatives

**Source:** S5 critique round 1 Drawback 1.
**Issue:** counterfactual ranking uses recommended-flag + space-distance only. Doesn't factor in cost delta, regulatory feasibility, user priorities. Critique proposed `score = w1*recommended + w2*space_delta + w3*cost_delta + w4*probability` weighted scoring.
**Deferral rationale:** parent spec § 4.6 explicitly mandates current ranking. Adding weighted scoring without empirical weights = magic numbers; needs real user data to tune.
**Trigger:** when first user feedback indicates surprising counterfactual ordering.
**Effort:** ~30 LOC + parent spec § 4.6 revision.

### B-017 — Optional `counterfactual_summary` override on ResolutionOption

**Source:** S5 critique round 1 Drawback 2.
**Issue:** Even with v1.0 P1's casing fix, `f"would have {summary}"` can produce stilted phrasing. Proper fix is letting S3 hand-craft a counterfactual sentence per option.
**Deferral rationale:** requires modifying ResolutionOption (S1 dataclass) AND re-shipping S3 to populate the new field for every option.
**Trigger:** v0.2 product polish pass before public launch.
**Effort:** ~80 LOC across S1 + S3.

### B-018 — Confidence indicator on counterfactual alternatives

**Source:** S5 critique round 1 Drawback 3.
**Issue:** alternatives tuple is (option_id, description, would_have). No confidence/feasibility signal.
**Proposed change:** extend to (option_id, description, would_have, confidence_level: CostConfidence | None).
**Deferral rationale:** requires modifying CounterfactualSummary's `__post_init__`. S1 dataclass change.
**Trigger:** when user research surfaces "I picked the wrong alternative."
**Effort:** ~25 LOC across S1 + S5.

### B-019 — Cap of 2 alternatives — known tension (DECISION DEFERRED)

**Source:** S5 critique round 1 Drawback 4.
**Status:** REJECTED for v0.2 (per D-065). Locked by parent spec v0.2.1 critique #5 round.
**Logged here** for revisit only if real users complain.
**Trigger:** ≥3 user reports of "I wished I'd seen the third option."

### B-020 — `severity_breakdown` field on PreflightSummary

**Source:** S5 critique round 1 Drawback 5.
**Issue:** PreflightSummary should carry structured `severity_breakdown = {critical: X, moderate: Y}`.
**Deferral rationale:** S1 dataclass change. v1.0 P3 patch delivers user value within S5 by embedding severity in summary_message text.
**Trigger:** when S7 (API) is built and frontend wants colored severity badges.
**Effort:** ~30 LOC across S1 + S5 + S7.

### B-021 — Detector → S5 contract documentation in parent spec

**Source:** S5 critique round 1 Drawback 8.
**Issue:** parent spec § 2.2 should document the tier→case_id mapping explicitly (S5 v1.0 has these as defensive contract tests P4).
**Trigger:** next parent-spec revision (alongside B-015).
**Effort:** ~10 LOC parent spec.

### B-022 — Aggregated counterfactual across all decisions

**Source:** S5 critique round 1 Drawback 10.
**Issue:** counterfactual is per-decision only. Users can't see cumulative effect.
**Deferral rationale:** S6's responsibility (decision log). New domain type likely needed.
**Trigger:** S6 design phase.
**Effort:** ~120 LOC if built into S6.

### B-023 — Message-key system / centralized copy registry

**Source:** S5 critique round 1 Drawback 11; partial pre-work in S5 v1.1 D2 fix.
**Issue:** every user-facing string in C1, C2, C3a is hardcoded.
**Deferral rationale:** project-wide refactor.
**Trigger:** dedicated v0.2 / v0.3 milestone.
**Effort:** ~500+ LOC across project.

### B-024 — `no_alternatives_reason` field on CounterfactualSummary

**Source:** S5 critique round 1 Drawback 12.
**Issue:** when only one option exists, alternatives=() is returned silently.
**Proposed change:** optional `no_alternatives_reason: str | None` field.
**Deferral rationale:** S1 dataclass change.
**Trigger:** when first counterfactual UI is built.
**Effort:** ~15 LOC across S1 + S5.

### B-025 — City-aware contextual messaging (HIGH-VALUE; SCHEDULED FOR v0.2)

**Source:** S5 critique round 1 Drawback 9.
**Issue:** messages are static. Critique example: "FAR limits in Chennai..." vs generic.

**Why this is worth keeping (NOT rejected):**
1. Product fundamentally city-specific — TNCDBR, DCPR 2034, MPD-2021, BBMP, UDCPR, GHMC. Generic messaging underutilises the moat.
2. Data is already there. `Brief.plot.city` exists; C2 keys logic by city; KB rules are city-keyed.
3. Trust calibration — contractor says "side setback in Velachery is 1.5m per TNCDBR Schedule III"; generic messaging loses that.

**Why deferred:**
1. S5 doesn't currently receive a Brief; threading city in requires either S1 dataclass change (add `city` to ExtremeCase) or signature changes through S5/S6 callsites.
2. Doing it inside S5 = changing S1 deliverables = Pattern E.
3. Adding it later is non-breaking.

**Triage:** medium-high.
**Trigger:** v0.2 product polish before public launch.
**Effort:** ~150 LOC across S1 + S2 + S5 + tests, ~1 dedicated session.

---

## Origin: Session 21 continued (S5 code critique round 2)

These items came from the code-critique step (D-066 second critique): the spec was clean but the code revealed additional concerns.

### B-026 — Code D2 partial pre-work (preflight string constants extracted)

**Source:** S5 code critique round 2 Drawback 2 (lightweight version applied as v1.1 fix).
**Status:** PARTIALLY DONE in v1.1. Module-level `_EARLY_PLOT_HINT_SUFFIX` and `_REASON_*` constants exist in `preflight.py`. Full message-key registry (B-023) is the proper extension.
**Triage:** N/A — supersession into B-023.

---

*Owner: Ramalingam.*

*Suggested triage order (most-correctness-first):*
*1. B-002, B-010 — C2 correctness gaps (CheckResult details);*
*2. B-013 — robustness of S4 error classification (worth doing before S6);*
*3. B-003 — city coverage (Mumbai/Pune stilt);*
*4. B-025 — city-aware messaging (high product value, scheduled v0.2);*
*5. B-011 — Brief schema for parking/coverage (cleaner S4);*
*6. B-014 — Setbacks classification refinement (low cost, real UX win);*
*7. B-007 — BHK flexibility signal in C1;*
*8. B-022 — aggregated counterfactual (S6 design decision);*
*9. B-018, B-020 — UX polish requiring S1 dataclass changes;*
*10. B-004 — circulation factor consistency;*
*11. B-005, B-006, B-008, B-009, B-012, B-015, B-016, B-017, B-019, B-021, B-023, B-024 — incremental polish;*
*12. B-001, B-026 — DX / supersession items (lowest priority).*

---

## Origin: Session 21 continued (S6 spec critique rounds + B-027 spec critique round + B-027 code critique round)

### B-028 — Per-case limit semantics revisit

**Source:** S6 critique round 1 D3.
**Issue:** parent spec § 4.3 mandates `PER_CASE_LIMIT = 3`, but the semantic ("same case_id appears 3 times") is questionable in practice — successful applies typically advance to a different case via re-detection.
**Status:** Implement parent spec literally for v1.0; revisit when real user data shows whether the 3-iteration cap fires meaningfully.
**Trigger:** post-launch user data.

### B-029 — Structured `non_relaxable_blockers` field on ResolvedBrief

**Source:** S6 critique round 1 D6.
**Issue:** when Preview Mode fires, ECs not in `_EC_TO_RELAXED_CONSTRAINT` map (EC-002, EC-003, EC-008, EC-009) are silently absent from `relaxed_constraints`. UI computes via diff with `unresolved_blockers` for v1.0.
**Proposed fix:** add structured `non_relaxable_blockers: tuple[ExtremeCaseId, ...]` field on ResolvedBrief.
**Deferral rationale:** S1 dataclass change.
**Trigger:** when S7 (API) needs structured serialization for the frontend.

### B-030 — `option_strategy` enum migration

**Source:** B-027 critique round 1 D2.
**Issue:** ResolutionOption has 2 booleans (is_preview_mode, is_different_plot_option). Adding more strategies (change_city, change_zoning) means more booleans → polluted dataclass.
**Proposed fix:** `option_strategy: Enum {REGULAR, PREVIEW, DIFFERENT_PLOT, ...}` replaces boolean flags.
**Deferral rationale:** acceptable for now per critique. Boolean form is structurally guarded by P1 (mutual exclusivity) + P6 (constraints when different-plot=True).
**Trigger:** when 3rd strategy lands.
**Effort:** ~80 LOC across S1 + S3 + S5 + S6.

### B-031 — `different_plot_reason` field

**Source:** B-027 critique round 1 D5.
**Issue:** is_different_plot_option is boolean. Doesn't capture HARD recommendation vs SOFT fallback, or WHY (legal vs spatial vs budget).
**Proposed fix:** `different_plot_reason: Optional[str]` or Enum.
**Deferral rationale:** future-ready extension. Not needed for v1.0.
**Trigger:** when UX surfaces the soft/hard distinction.
**Effort:** ~30 LOC across S1 + S3 + S5.

### B-032 — `case_has_different_plot_option` meta flag

**Source:** S6 critique round 2 D7.
**Issue:** when promotion fires but a case has no different-plot option, S6 silently does nothing for that case. UI may need to explain absence.
**Proposed fix:** add `case_has_different_plot_option: bool` field, derived at sort time.
**Deferral rationale:** nice-to-have per critique. Not blocking v1.0.
**Trigger:** when S7/UI requires the affordance.
**Effort:** ~25 LOC across S6 + tests.

### B-033 — `triggering_case_ids` on DifferentPlotPromotionEvent

**Source:** S6 critique round 2 D9.
**Issue:** event has trigger reason + iteration. Doesn't capture WHICH cases caused the promotion. Hurts debugging and explainability.
**Proposed fix:** add `triggering_case_ids: tuple[ExtremeCaseId, ...]` to the event dataclass.
**Deferral rationale:** useful but not blocking v1.0.
**Trigger:** when debugging or explainability requirements surface.
**Effort:** ~15 LOC.

### B-034 — Incremental counterfactual building

**Source:** S6 critique round 2 D11.
**Issue:** all counterfactuals built at terminal state. N decisions → N computations at termination time → latency spike at the worst possible moment (final user-facing step).
**Proposed fix:** build counterfactual per decision incrementally as each apply succeeds.
**Deferral rationale:** acceptable for v1.0. ≤7 counterfactuals × microseconds = ~milliseconds total.
**Trigger:** when measurement shows actual user-perceived latency.
**Effort:** ~30 LOC.

### B-035 — First-class `DIFFERENT_PLOT_SUPPORTED_ECS` constant

**Source:** B-027 code critique round 2 D1 (spec-implementation drift).
**Issue:** the test currently uses a test-local `_ECS_WITH_DIFFERENT_PLOT_OPTION` frozenset. The spec separately documents (in B-027 v1.1 patch notes) which ECs S3 emits different-plot for. Two sources of truth for one contract.
**Proposed fix:** promote to a first-class constant in `domain/extreme_case.py` or a dedicated registry module: `DIFFERENT_PLOT_SUPPORTED_ECS: frozenset[ExtremeCaseId]`. Both S3 (assert option emission matches) and S6 (sanity check during promotion) and tests reference the same constant.
**Deferral rationale:** post-B-027 polish; current test catches drift; no immediate consumer requires the structured form.
**Trigger:** S6 build (S6 may benefit from importing this directly).
**Effort:** ~15 LOC.

### B-036 — `space_impact_type` enum (subsumes B-027 D2 + D6 + D10)

**Source:** B-027 code critique round 2 D2 (semantic overload of space_impact_sqft=0); D6 (counterfactual ranking implicit exclusion); D10 (rationale only in docstring).
**Issue:** `space_impact_sqft=0` is overloaded — "no spatial change" for regular options vs "not applicable" for different-plot options. Downstream consumers (S5 counterfactual ranking) implicitly trust that different-plot won't be ranked spatially.
**Proposed fix:** replace `space_impact_sqft: int` with `space_impact: Union[NumericImpact, NotApplicableImpact]` or add `space_impact_type: Literal["NUMERIC", "NOT_APPLICABLE"]` field.
**Deferral rationale:** Pattern E surgery to fix now (touches S1 dataclass + every option construction + S5 ranking). No current downstream consumer corrupts behavior. Helper P8 docstring documents the semantics.
**Trigger:** when a downstream consumer aggregates `space_impact_sqft` across options inappropriately.
**Effort:** ~150 LOC across S1 + S3 + S5.

### B-037 — Severity classification as structured mapping

**Source:** B-027 code critique round 2 D4.
**Issue:** `classify_case_severity` uses explicit `if c.case_id == EC_006 or EC_002 or EC_010_LOW` checks. Not extensible to new ECs (open/closed principle).
**Proposed fix:** structured map (`SEVERITY_MAP: dict[ExtremeCaseId, Severity]`) or enum field on ExtremeCaseId.
**Deferral rationale:** the closed set of 10 ECs is itself part of locked parent spec v0.2.1. Adding EC_011 is a major spec event, not silent code drift. Refactor when the closed set actually opens.
**Trigger:** parent spec change adding EC_011 or beyond.
**Effort:** ~30 LOC.

### B-038 — Enum return type for `classify_case_severity`

**Source:** B-027 code critique round 2 D9.
**Issue:** function returns raw strings ("critical", "moderate"). No compile-time safety; typo-prone.
**Proposed fix:** `class Severity(Enum): CRITICAL = "critical"; MODERATE = "moderate"`. Update caller and tests.
**Deferral rationale:** self-contained S5 function with one caller currently. Real improvement, no urgency.
**Trigger:** v0.2 polish pass.
**Effort:** ~20 LOC across S5 + tests.

### Critique items pushed back per D-067 (NOT logged as backlog — rejected)

These are documented for transparency but explicitly rejected during B-027 code critique round 2:

- **B-027 critique D3 — caller-frame inspection enforcement.** Hostile to legitimate test-fixture construction; brittle in Python; future devs work around it confusingly. Existing P1+P6 structural validation is adequate.
- **B-027 critique D5 — graceful degradation on missing OptionGenerator dispatch.** Loud failure is correct for internal invariants. Detector and option_generator are coupled by spec; missing dispatch is a programmer bug, not runtime input. Masking would hide real bugs.
- **B-027 critique D7 — rule-engine refactor for early-plot-hint predicates.** YAGNI on 3 named predicates with clear meaning. A "rule engine" optimises for hypothetical future triggers we don't have.

# v0_2_backlog.md addendum — items logged Session 23 (S7a spec)

Append these to the existing backlog file (after B-039). All three
were logged during the S7a SPEC critique cycles per D-067; pushed back
in spec rounds, retained as backlog work for later.

---

### B-040 — Schema migration layer for GateState serialization

**Source:** S7a SPEC critique round 1 #9 (schema versioning rigidity).
**Issue:** S7a v1.0 spec § 4.3 (P8 patch) softened the schema-version
rejection so that an absent `_schema_version` field loads as v1, and
only an explicit different value triggers `SchemaVersionError`. This
is sufficient for v0.1 since there is no v2 schema yet to migrate
from.
**Proposed fix:** when a v2 schema is on the horizon (e.g., new
GateState fields, removed fields, renamed fields), build a real
migration layer:
  - Version registry mapping schema_version → loader function
  - Each loader knows how to read its version AND upgrade to current
  - Deprecation warnings logged when loading old versions
  - Migration tests (round-trip every supported old version through
    the upgrade path)
**Deferral rationale:** premature. No v2 schema exists. Building
migration infrastructure for a single version is solving an
imaginary problem.
**Trigger:** when a real schema change is being planned (e.g., during
S7b or post-Component-3a deployment). The trigger is "we're about to
break wire compatibility," not "v0.1 is shipped."
**Effort:** ~120 LOC + tests in `gate_state.py` + a new
`gate_state_migrations.py` module.

---

### B-041 — Retrofit BriefStorage with WAL + retry + prune-on-resume + periodic prune

**Source:** S7a SPEC critique round 1 #5 (SQLite concurrency) + round 2 #10 (storage pruning idle accumulation).
**Issue:** S7a v1.0 spec ships SQLite hardenings for `GateStateStorage`:
  - PRAGMA journal_mode=WAL on every connection (P5)
  - Write retry: 3 attempts with 50/100/200 ms backoff on
    "database is locked" (P5)
  - Per-token single-flight lock for read-then-write sequences (P11)
  - Atomic state+cache co-write via BEGIN IMMEDIATE (P13)

`BriefStorage` (utils/brief_storage.py, v0.9 Session B) shipped
WITHOUT these hardenings. It uses the same `/tmp/buildemup_*.db`
SQLite-on-ephemeral-disk pattern. Symmetry says retrofit so the two
storage classes share behaviour.

Round 2 also flagged **storage pruning is non-deterministic** because
prune happens only on save() — idle systems with no incoming saves
accumulate expired rows indefinitely. For solo-founder pre-PMF on
Railway /tmp ephemeral storage every redeploy is a full wipe, so this
is a non-issue today; matters at scale or when storage moves off /tmp.

**Proposed fix:** retrofit BriefStorage with:
  - WAL pragma on connection open (~2 LOC + test)
  - Retry-on-locked wrapper around execute() (~10 LOC + test)
  - Prune-on-resume sweep — when resume() is called, opportunistically
    prune expired rows for that token's neighbours (~5 LOC)
  - Periodic prune helper for caller-driven scheduled cleanup (~10 LOC
    + test) — wired up by S7b's deployment scheduler when it lands
**Deferral rationale:** BriefStorage v0.9 is shipping fine for weeks.
Retrofitting mid-S7a is scope creep; doing it as a focused B-### item
post-S7a keeps the work isolated and reviewable.
**Trigger:** either (a) a real concurrency bug surfaces in BriefStorage
production logs, or (b) proactive polish during a v0.10 cleanup pass,
or (c) when S7b lands and the scheduler hook is wired up.
**Effort:** ~50 LOC + 4 tests in `utils/brief_storage.py` and its
test file.

---

### B-042 — Project-wide auth (token binding to client_id, rotation, session scoping)

**Source:** S7a SPEC critique round 1 #10 (token = full access) +
round 2 #8 (request_id trust model unsafe) + round 2 #13 (session
token SPOF — verbatim repeat of round 1 #10).
**Issue:** Both `BriefStorage` and `GateStateStorage` use opaque
24-char-hex tokens as authorization. Possession of a token grants full
access to the underlying resource. There is:
  - No binding to user_id or client_id
  - No token rotation
  - No expiration refresh
  - No scoping (a token is all-or-nothing per resource)

This is a known limitation in the v0.1 threat model: **single-tenant,
unauthenticated public API**. A malicious client with a token already
has full access; reusing request_id to "block progression" is
achievable today by simply not sending requests. Adversarial robustness
is an auth-feature scope, not a per-storage-class fix.

**Proposed fix:** a project-wide auth layer that solves this for
BOTH storage classes simultaneously. Components:
  - User authentication (likely OAuth — Google/Apple sign-in given
    Indian-mobile-first audience)
  - Token-to-user binding (tokens become single-user only)
  - Token rotation on each save (optional; trade-off vs replay
    semantics)
  - Per-session scoping (a token grants access to one specific
    resource, not the whole storage class)
  - Rate limiting per user
**Deferral rationale:** auth is a separate component-scale feature.
Likely C0 in v3 architecture or a cross-cutting concern. Solving
piecemeal for one storage class leaves the other exposed.
**Trigger:** when the project goes from solo-founder demo to public
launch (likely post-PMF), OR when a real abuse incident surfaces, OR
when payments/personalization need user identity anyway.
**Effort:** significant — multi-session work with its own spec cycle.
Touches every API endpoint, every storage class, deployment config,
and the front-end auth flow.

---

## Backlog count after Session 23

39 items total: B-001 through B-042, with B-026 superseded into B-023.

Recent additions (Session 22 → Session 23):
- B-039 (Session 22) — option-generation caching
- B-040 (Session 23) — schema migration layer
- B-041 (Session 23) — BriefStorage WAL retrofit + prune sweep
- B-042 (Session 23) — project-wide auth

---

## Origin: Sessions 24-28 (additions captured by per-session delta files; condensed mirror per Rule 9)

The following entries are filed in detail across `backlog_session_24_addendum.md`, `backlog_session_24_additions.md`, `backlog_session_25.md`, `backlog_session_26_S8_critique_delta.md`, `backlog_session_27.md`, and `backlog_session_28.md`. Condensed table here for the canonical view per Rule 9 (spec is canonical; canonical backlog mirrors).

| ID | One-line description | Origin | Status |
|---|---|---|---|
| B-043 | `gate_state_storage.save_existing` rollback bug masks TokenNotFoundError | S24 | OUT (post-launch) |
| B-044 | Storage-layer dependency-injection refactor | S24 | OUT |
| B-045 | Defense-in-depth validation in `from_dict` methods | S24 | OUT |
| B-046 | API response versioning strategy | S24 | OUT |
| B-048 | Email hook retry (gated on measured Resend failure rate) | S25 | OUT until rate measured |
| B-049 | Automated post-deploy hook execution verification | S25 | OUT |
| B-050 | SQLite FK enforcement on storage connections | S25 | OUT |
| B-051 | Reconcile env-var name drift (`BUILDEMUP_DATABASE_PATH` vs `BUILDEMUP_GATE_DB_PATH`) | S25 | OUT |
| B-052 | Validate scheduler-state index selectivity at production scale | S25 | OUT |
| B-053 | Log shipping to managed log platform (with audit-log retention) | S25 | OUT |
| B-054 | Test-justification linting CI plugin | S26 S8 round 3 | OUT |
| B-055 | Concurrency tuning post-launch | S26 S8 first post-LOCK | OUT |
| B-056 | Formalise § 1.2 (ii) additive-read-accessor carve-out language at next S8 spec-amendment cycle | S27 (Flag A adjudication) | OUT |
| **B-057** | **Visible trace_id on case.html success render** | **S28 audit** | **OUT (cosmetic)** |
| **B-058** | **Full-walk e2e tests (case→resolve→done with seeded chain)** | **S28 audit** | **OUT (depth, not breadth)** |
| **B-059** | **done.js: PER_CASE_LIMIT_REACHED gets its own success message** | **S28 audit** | **OUT (cosmetic)** |
| **B-060** | **tests/e2e/__init__.py docstring "7 files"→"8 files"** | **S28 audit** | **OUT (cosmetic)** |
| **B-061** | **SQLite 503 adaptive backoff `min(2^n,30)+jitter` + lock-frequency metric (refines B-055)** | **S28 critique #2** | **OUT (post-launch)** |
| **B-062** | **Startup cross-check: `prod_env + C3A_TEST_MODE=1 → sys.exit(1)` per § 9.7/P32** | **S28 critique #5** | **OUT (defense-in-depth)** |
| **B-063** | **CI pipeline: Tier-2 e2e mandatory pre-merge gate** | **S28 critique #13** | **OUT (CI orchestration)** |
| **B-064** | **Static asset CSP + Cache-Control headers in `_serve_static`** | **S28 critique #14** | **OUT (security hardening)** |
| **B-065** | **`metric_failures_total` counter inside the existing P22 swallow path (NOT alerting)** | **S28 critique #9 kernel** | **OUT (counter, not alert)** |
| **B-066** | **Polygon plots (L-shaped, irregular) support** | **C4 v0.1 critique walk #13 alignment** | **OUT (v1 = rectangular)** |
| **B-067** | **Per-month sun-path declination (vs solstice envelope)** | **C4 v0.1 critique walk #4** | **OUT (envelope sufficient for v1 room-bias)** |
| **B-068** | **`effective_open_sides` post-setback usable openness** | **C4 v0.1 critique walk #8** | **OUT (defer until C5 ships)** |
| **B-069** | **Composite-zone internal sub-classification (composite-dry vs composite-humid)** | **C4 v0.3 web research** | **OUT (NBC 2016 = single COMPOSITE)** |
| **B-070** | **IMD wind-rose data per city (vs single-direction citation)** | **C4 v0.3 self-critique** | **OUT (4-field model sufficient v1)** |
| **B-071** | **Latitude-band climate fallback for unknown cities** | **C4 v0.3 critique #3** | **OUT (v1 = explicit supported-cities list)** |
| **B-072** | **C7 retrofit to consume PlotAnalysis.soil_estimate (single-source-of-truth alignment)** | **C4 v0.4 Path B** | **OUT (defer until layout pipeline C5-C16 stable)** |

## Backlog count after Session 28

**69 entries** total. B-001 through B-072 issued, with B-026 superseded into B-023, and B-047 unused. Active backlog: 62 items, all OUT-of-scope for current builds.

Filed per Rule 9.2 (always-file directive — codified end of S28; memory line 12). B-066/067/068 added during C4 v0.1 → v0.2 critique walk; B-069/070 added during C4 v0.2 → v0.3 web-research pass (the pass Ramalingam caught me skipping per Rule 7 web-search requirement).


---

# Session 30 (S30) additions — B-094 through B-106

Filed during C5 critique walk + C6 v0.1 → v0.5 LOCKED (4 critique walks). Companion file: `backlog_session_30.md` (this directory) for session-context details. Full per-item rationale lives in the chronological specs under `02_specs_chronological/17–22`.

## B-094 — Orthogonalize width_fit vs aspect_ratio_fit

**Origin**: C5 critique walk (S30), item 9.
**Status**: VALID-BUT-BACKLOG.
**Description**: `score_width_fit` and `score_aspect_ratio_fit` both read plot dimensions; partial overlap creates double-counting risk on edge cases (e.g., 6×18m plots).
**Trigger**: When B-090 yields ≥ 50 real-plan datapoints; check residual correlation > 0.7.
**S30-scope verdict**: OUT — pre-empirical refinement.
**Effort**: S (≤ 0.5 day post-B-090).

## B-095 — FloorRoomBrief enrichment for downstream components

**Origin**: C5 critique walk (S30), item 10.
**Status**: BACKLOG (intentional v1 deferral).
**Description**: v1 `FloorRoomBrief` carries only counts + boolean flags. Real planning needs bedroom types (master/guest/kids), per-room minimum sizes, adjacency preferences, hierarchy.
**Trigger**: When C6 or C9 are scoped; coordinate with C1 brief flow.
**S30-scope verdict**: OUT — downstream concern; topology selection at C5 deliberately operates on coarse counts.
**Effort**: M (~ 1-2 days; affects C1 brief schema, C6, C9 contracts).

## B-096 — Externally expose 8-direction output

**Origin**: C6 v0.1 § 9 (originally "8-dir granularity"); demoted to internal-adopted in C6 v0.3 § 14.9.
**Status**: BACKLOG (internal-adopted; external-output deferred).
**Description**: 8-direction internal computation for Vastu is now active in C6 v0.5 LOCKED. Public output surface stays 4-direction (compatible with C4's PlotOrientation enum).
**Trigger**: When downstream consumers ask for 8-dir externally.
**S30-scope verdict**: OUT — internal already adopted; external output not currently needed.
**Effort**: M.

## B-097 — Multi-floor per-floor orientation

**Origin**: C6 v0.1 § 9.
**Status**: BACKLOG.
**Description**: Each floor independently oriented (different per-floor zone-band assignments).
**Trigger**: When C9 or C10 introduce multi-floor placement.
**S30-scope verdict**: OUT — v1 is single-floor.
**Effort**: L.

## B-098 — HOT_DRY and COLD climate zones

**Origin**: C6 v0.1 § 9.
**Status**: BACKLOG (reserved enum values).
**Description**: NBC's 5-zone classification includes hot-dry and cold; v1 has no city mapped to either. C6 sun/wind tables for these zones are reserved.
**Trigger**: When a v1 city maps to either climate zone.
**S30-scope verdict**: OUT — no use case.
**Effort**: S.

## B-099 — Populate vastu_engine KB for FULL tier

**Origin**: C6 v0.1 § 9; reaffirmed C6 § 14.8 + 4 critique walks (held against soft-degradation reversal each time).
**Status**: BACKLOG — **HARD-BLOCKING for FULL tier**.
**Description**: C6 FULL tier requires the `vastu_engine` KB to be populated with the full 8-dir × N-function table. Until populated, FULL raises `NotImplementedError("FULL tier requires vastu_engine KB; B-099. Use PARTIAL.")`. OFF and PARTIAL remain fully functional.
**Trigger**: When ≥ 1 FULL-tier user request is observed in pilots, or when KB authoring is scheduled.
**S30-scope verdict**: OUT — KB authoring work; mechanical pressure to populate (C6 design decision).
**Effort**: M (KB authoring + integration).

## B-100 — Building massing rotation engine ("Meaning A" of orientation)

**Origin**: C6 design discussion (S30 — Q1 framing); § 9.
**Status**: BACKLOG.
**Description**: Rotation of building's long axis on the plot — distinct from C6's functional priority ("Meaning B"). Currently constrained by plot dimensions + C5 topology.
**Trigger**: When non-rectangular plots arrive (also gated by B-066).
**S30-scope verdict**: OUT — no use case yet.
**Effort**: L.

## B-101 — Signal interaction terms

**Origin**: C6 v0.2 walk item 1.
**Status**: BACKLOG (pre-empirical).
**Description**: Replace pure linear `function_scores = sun + wind + vastu` blend with interaction terms (`sun × wind` cooling effect; `vastu × road` alignment). Without empirical data, interaction terms are arbitrary; B-090 must precede.
**Trigger**: When B-090 yields ≥ 50 datapoints and fit residuals show non-linearity.
**S30-scope verdict**: OUT — pre-empirical.
**Effort**: M.

## B-102 — Location-aware wind & continuous climate scaling

**Origin**: C6 v0.2 walk items 2 and 12 (combined).
**Status**: BACKLOG (C4 territory).
**Description**: Extend C4 `PlotAnalysis` with `prevailing_wind_direction`, `humidity_index`, latitude-dependent solar; replace C6's static climate-zone tables with continuous functions. Mumbai vs Chennai vs Kochi differentiation.
**Trigger**: When B-090 reveals city-level variance > zone-level variance.
**S30-scope verdict**: OUT — C4 enrichment program; C6 reads zone, not city.
**Effort**: L.

## B-103 — Dynamic hysteresis threshold

**Origin**: C6 v0.2 walk item 5; raised in 4 walks total.
**Status**: BACKLOG (pre-empirical).
**Description**: Replace static `SWAP_HYSTERESIS_THRESHOLD = 0.10` with `f(confidence, aspect_ratio, climate_strength)`.
**Trigger**: Post-B-090; same gate as B-101.
**S30-scope verdict**: OUT — pre-empirical; static threshold workable for v1.
**Effort**: S.

## B-104 — Entropy- or variance-based confidence metric

**Origin**: C6 v0.2 walk item 8; raised in 4 walks total. v0.4 § 14.15 currently uses margin-clamped formula.
**Status**: BACKLOG (v1.x improvement).
**Description**: Replace margin-clamped `(top - second) / max(top, 0.1)` with normalized-entropy or variance-based metric. Distribution-aware; better for multi-near-tie cases.
**Trigger**: When real-world feedback shows margin-clamped misleads downstream consumers.
**S30-scope verdict**: OUT — margin-clamped is web-supported best-of-simple-options for v1.
**Effort**: S.

## B-105 — C6 ↔ C8 layout-feasibility feedback loop

**Origin**: C6 v0.2 walk item 11.
**Status**: BACKLOG (post-C8).
**Description**: Iterative re-scoring of C6 orientation choices against C8 corridor-feasibility output. Currently C6 is one-shot (no feedback).
**Trigger**: After C8 ships and is stable.
**S30-scope verdict**: OUT — premature without C8.
**Effort**: L.

## B-106 — SERVICE-band-only secondary-road bonus on corner plots

**Origin**: C6 v0.4 walk item 9 (formalized after deferral noted in v0.3 § 4.1.3 / v0.4 § 12).
**Status**: BACKLOG (post-deployment empirical).
**Description**: Soft preference for SERVICE band facing the secondary road on corner plots. Real architectural pattern (service entries on the secondary road for delivery, garbage). C6 v0.5 LOCKED enforces only the entry-on-road hard constraint; this is the soft optimization layered on top.
**Trigger**: (a) corner-plot share of v1 production usage exceeds 25%, OR (b) ≥ 5 user complaints about service entry placement on corner plots.
**S30-scope verdict**: OUT — v0.3 just consolidated road handling; Pattern A risk in re-amending too soon.
**Effort**: S.

---

## B-107 — Intercardinal `plot.facing` support (extend C6 scoring to 8-direction externally)

**Origin**: C6 v0.6 § 14.19 (S31 pre-code Q&A round, Q1-B). Surfaced when pre-code spec/codebase cross-check found `domain/envelope.py:PlotOrientation` is 8-direction (not 4-direction as the v0.5 spec assumed) and C5's `default_zone_bands(facing)` produces intercardinal zone_bands when `plot.facing` is intercardinal.
**Status**: BACKLOG (deferred-but-non-blocking for v1).
**Description**: Extend C6 scoring to handle intercardinal `plot.facing` (NORTHEAST, SOUTHEAST, SOUTHWEST, NORTHWEST). Touches: sun/wind score tables (add NE/SE/SW/NW rows), weighted-avg aggregation rule, Hamming distance over 8-dir keyspace, validator invariant 9, ~10–15 new tests, plus design dialogue on whether scoring tables interpolate from cardinals or use independent intercardinal values. C6 v1 raises `NotImplementedError("intercardinal facing reserved; B-107. v1 supports cardinal facing only.")` at the input boundary.
**Trigger**: (a) ≥ 1 v1 production input has intercardinal `plot.facing`, OR (b) ≥ 5 user requests for diagonal-plot orientation support.
**S31-scope verdict**: OUT — v1 supports cardinal facing only. Mirrors B-066 (non-RECTANGULAR shape) and B-098 (HOT_DRY / COLD climate) defer-with-explicit-fail pattern.
**Effort**: M.
**Related**: B-066 (non-RECTANGULAR shape — same defer-with-fail pattern), B-098 (HOT_DRY/COLD climate — same pattern), B-096 (8-dir external output — adjacent concern).

---

**Total session adds**: 13 (B-094 → B-106). New canonical max: **B-106**.

---

**S31 patch-round add (mid-session, pre-code C6 v0.6 patch)**: 1 (B-107). New canonical max: **B-107**.

---

## Origin: Session 31 (S31 — C8 v0.5 LOCK, S31 close)

C8 v0.5 LOCKED at S31 close after 5 critique walks. Per Rule 9.2 (always-file-backlog), all 19 backlog items surfaced during walks #1–#5 are filed here with concrete B-NNN numbers. Items B-108 through B-126 mirror exactly what's in C8 v0.5 LOCKED § 12 (this file is the project-level mirror of the spec-level enumeration; spec is canonical per Rule 9).

### B-108 — Primary-source verification of NBC residential corridor minimum width

**Origin**: C8 v0.1 § 3 dataclass docstring + § 11 web-research surface (originally placeholder B-NNN-A).
**Status**: BACKLOG (Pattern C avoidance — surface uncertainty rather than ship hardcoded unverified value).
**Description**: Architecture-v2 spec asserts "NBC: 0.9m interior residential" for corridor minimum width. S31 web research located NBC Part 4 references but did not retrieve the exact corridor-width clause for residential; TNCDBR rule 42 referenced but text not surfaced. Resolve by retrieving actual NBC Part 4 + TNCDBR rule 42 text and confirming 0.9m figure (or correcting default).
**Trigger**: Before any v1 production deployment that depends on building-code compliance claims; OR before any user-facing copy that cites NBC corridor minimums.
**S31-scope verdict**: OUT — v1 ships with 0.9m as default + configurable override. Verification is a pre-prod task, not a build-blocker.
**Effort**: S (~1 hour: locate NBC Part 4 PDF, locate TNCDBR rule 42 text, update default value if needed).

### B-109 — CorridorTooNarrowError handling: graceful fallback vs raise

**Origin**: C8 v0.1 § 4.3 width-assignment fallback chain (originally placeholder B-NNN-B).
**Status**: BACKLOG (deferred design dialogue).
**Description**: When plot is too small to fit `regulatory_min_width_m` corridor on the required topology axis, v1 raises `CorridorTooNarrowError`. Real product behavior may need graceful fallback (e.g., suggest different topology, propose no-corridor degenerate path, or flag for user manual override). Resolve via product-decision dialogue + downstream consumer needs.
**Trigger**: First user-reported case OR when C9 (Room Sizer) needs to know whether to expect corridor or not.
**S31-scope verdict**: OUT — v1 raises; defer graceful handling to product-decision round.
**Effort**: M.

### B-110 — C5 ↔ C8 length-drift integration test (already concrete pre-LOCK)

**Origin**: C8 v0.2 § 4.5 (replaces removed v0.1 § 4.5 sanity check).
**Status**: BACKLOG (low effort; should land soon after C8 SHIP).
**Description**: Cross-component integration test that exercises real C5 candidates through real C8 and asserts `c5.approx_length_m` vs `c8.total_length_m` drift is within an empirically-derived envelope (likely ±20% based on grid-quantization range). Detects systemic divergence (C5 sketch heuristic out of sync with C8 reality) without false-alarming on legitimate per-candidate variation.
**Trigger**: C8 SHIPs.
**S31-scope verdict**: OUT of C8-build scope; in scope as follow-up integration task.
**Effort**: S.

### B-111 — Rotated structural grid support

**Origin**: C8 v0.1 § 4.2 grid-snapping algorithm assumes axis-aligned grid (originally placeholder B-NNN-C).
**Status**: BACKLOG.
**Description**: v1 assumes `Grid.columns` are axis-aligned cardinal arrays. C7 may eventually produce grids rotated to plot-edge angles (e.g., for non-rectangular plots). C8 needs to support rotated snap geometry then.
**Trigger**: C7 produces a rotated grid (currently rectangular-only via B-066 chain).
**S31-scope verdict**: OUT — gated by B-066 / C7 capability.
**Effort**: M.

### B-112 — TNCDBR rule 42 + city-specific corridor-width overrides

**Origin**: C8 v0.1 § 8 KB references (originally placeholder B-NNN-D).
**Status**: BACKLOG.
**Description**: Different cities/states may have stricter or looser corridor-width rules than NBC. v1 uses NBC default everywhere. Future: per-city KB lookup keyed on `plot_analysis.plot.city`, with TN cities deferring to TNCDBR rule 42, etc.
**Trigger**: User reports plan-rejection due to local rule mismatch; OR product decision to claim regional regulatory accuracy.
**S31-scope verdict**: OUT — v1 single-default acceptable for MVP.
**Effort**: M.

### B-113 — Diagonal corridor segments

**Origin**: C8 v0.1 § 3 invariant 3 (axis-aligned only) (originally placeholder B-NNN-E).
**Status**: BACKLOG.
**Description**: Some plot shapes / aesthetic preferences benefit from diagonal corridor runs (e.g., aligning with diagonal sight line). v1 enforces axis-aligned for simplicity + grid-snap predictability.
**Trigger**: Architectural preference signal from users OR non-rectangular plot support (B-066) opens diagonal naturally.
**S31-scope verdict**: OUT.
**Effort**: L.

### B-114 — Multi-floor vertical corridor coordination

**Origin**: C8 v0.1 § 9 (originally placeholder B-NNN-F).
**Status**: BACKLOG.
**Description**: When C12 (Vertical Alignment) ships, multi-floor plans need their corridors stacked to align with stairs across floors. v1 is single-floor.
**Trigger**: C12 ships.
**S31-scope verdict**: OUT — gated by C12.
**Effort**: M.

### B-115 — Variable-width corridor along a single segment (independent of taper system)

**Origin**: C8 v0.1 § 4.3 (originally placeholder B-NNN-G).
**Status**: BACKLOG.
**Description**: Architectural pattern: bell-mouth widening at entry (1.5m at door, narrows to 1.2m). Distinct from v0.4's taper-zone-at-junction system; this is mid-segment width variation independent of junctions.
**Trigger**: Aesthetic / experience-quality signal.
**S31-scope verdict**: OUT.
**Effort**: M.

### B-116 — Per-room ZoneBandEnvelope refinement (C9 / C11a override hook)

**Origin**: C8 v0.2 § 14.1 known-unknown surface (originally placeholder B-NNN-H).
**Status**: BACKLOG (deferred design dialogue).
**Description**: When C9 ships, may want to refine band extents based on actual furniture-fit calculations rather than accepting C8's uniform-strip model. Resolve via C8/C9 contract dialogue at C9-build time.
**Trigger**: C9 LOCK or first failing C9 test that reveals strip model is too coarse.
**S31-scope verdict**: OUT — v1 ships with strip model.
**Effort**: M.

### B-117 — Cross-segment width interaction model (variable widths along path connectivity)

**Origin**: C8 v0.2 § 4.3 (originally placeholder B-NNN-I).
**Status**: BACKLOG.
**Description**: Define how non-junction segments interact when widths differ across the corridor path. Distinct from B-115 (single-segment variation) and from v0.4's taper system (junction-only width transitions). Captures path-wide width orchestration.
**Trigger**: Aesthetic / experience-quality signal OR first user complaint about path-level width inconsistency.
**S31-scope verdict**: OUT.
**Effort**: S.

### B-118 — Area-budget-aware corridor sizing

**Origin**: C8 v0.2 critique walk Drawback 6 (originally placeholder B-NNN-J).
**Status**: BACKLOG.
**Description**: Full system loop where C8's width responds to C9's room-sizing pressure (e.g., narrow corridor when C9 reports rooms are tight). v1 is one-way: C8 publishes area, C9 reads it. Bidirectional negotiation deferred.
**Trigger**: Empirical signal that v1 corridor area choices systematically push C9 over feasibility thresholds.
**S31-scope verdict**: OUT — v1's one-way contract is deliberate Pattern E avoidance.
**Effort**: L.

### B-119 — Band-importance-weighted strip allocation

**Origin**: C8 v0.3 § 14.16 (originally placeholder B-NNN-K).
**Status**: BACKLOG.
**Description**: v1 ships uniform-thickness strips. Real residential plans have non-uniform proportions: PUBLIC typically larger than SERVICE; PRIVATE often fragmented. Refine via empirical weighting calibrated against C9 + C11a behavior data.
**Trigger**: (a) C9 reports systematic room-fit failures attributable to coarse band proportions, OR (b) C11a needs to mutate band proportions as part of its operators.
**S31-scope verdict**: OUT — needs empirical data not available yet.
**Effort**: M.

### B-120 — Polygon-union via shapely (if axis-aligned algorithm proves insufficient)

**Origin**: C8 v0.3 § 14.14 (originally placeholder B-NNN-L).
**Status**: BACKLOG (probabilistically low-need).
**Description**: v1 implements axis-aligned-rectangle + right-triangle union via sweep-line (no external dependency). If v2 introduces diagonal segments (B-113) or other non-axis-aligned geometry, sweep-line becomes insufficient.
**Trigger**: B-113 ships OR diagonal/curved corridor segments enter v1.
**S31-scope verdict**: OUT — v1 axis-aligned-only by spec.
**Effort**: S.

### B-121 — Junction transition segments / fillets

**Origin**: C8 v0.3 § 14.12 (originally placeholder B-NNN-M).
**Status**: BACKLOG (aesthetic refinement).
**Description**: v1 enforces equal width at junctions via taper zones (eliminates step discontinuities). Architecturally finer designs use fillets (curved transitions) at junctions for visual polish. Implementing requires non-axis-aligned geometry (currently forbidden by § 14.1.3).
**Trigger**: B-113 ships OR aesthetic-quality signal from real-plan reviews.
**S31-scope verdict**: OUT — v1 axis-aligned + taper-zones is simplest correct design.
**Effort**: M.

### B-122 — Empirical thresholds for consumption_band

**Origin**: C8 v0.3 § 14.15 (originally placeholder B-NNN-N).
**Status**: BACKLOG (calibration; pre-empirical).
**Description**: v1 ships LOW/MEDIUM/HIGH thresholds at 12% / 20% as educated-guess defaults. Calibrate against real Indian residential plans (target dataset: ResPlan or comparable; ~100+ plans across plot sizes and tier classifications) to validate or revise thresholds.
**Trigger**: C8 SHIPs + ≥ 50 v1-production plans with measured consumption fractions OR explicit calibration sprint.
**S31-scope verdict**: OUT — calibration without data.
**Effort**: S (one analyst-day with the data).

### B-123 — Width-selection scoring + taper-length empirical calibration

**Origin**: C8 v0.4 § 14.19 (scoring weights) + § 14.20 / § 4.3.1 (taper-length default) (originally placeholder B-NNN-O).
**Status**: BACKLOG (calibration; pre-empirical).
**Description**: Two related calibration questions: (a) `under_comfort_penalty_ratio = 2.0` default produces architecturally-sensible results across 7 C7 bay sizes per S31 verification, but 2:1 ratio is educated guess; validate against real-plan satisfaction surveys or downstream feasibility data. (b) Taper-zone length default `min(bay_x, bay_y)` is reasoned-not-standards-bound (no industry-standards guidance found at S31 web research); validate against real-plan rendering and architect feedback.
**Trigger**: C8 SHIPs + ≥ 50 v1 production plans with measured corridor-quality signals OR explicit calibration sprint.
**S31-scope verdict**: OUT — calibration without data.
**Effort**: S (one analyst-day with data).

### B-124 — Width interpolation in junction-adjacent regions implementation

**Origin**: C8 v0.4 § 14.20 implementation work (originally placeholder B-NNN-P).
**Status**: BACKLOG (build-time, not spec-time).
**Description**: Local-propagation algorithm (§ 14.20) requires `CorridorSegment` to model variable width via taper zones with linear interpolation. v0.5 LOCKED defines contract; implementation must translate to working code with attention to edge cases: very-short segments (taper truncation per § 4.3.1), segments with both ends as junctions, zero-width-difference junctions.
**Trigger**: C8 build session.
**S31-scope verdict**: OUT — implementation work, not spec.
**Effort**: M (real architectural work; ~2-3 days).

### B-125 — Envelope-symmetry secondary-criterion weight calibration

**Origin**: C8 v0.4 § 14.21 (`envelope_symmetry_weight = 0.3` default) (originally placeholder B-NNN-Q).
**Status**: BACKLOG (calibration).
**Description**: 0.3 weight is educated guess balancing primary edge-snap criterion against secondary envelope-symmetry. Validate against real-plan rendering: does secondary criterion meaningfully stabilize ZoneBandEnvelope placement, or is it noise? Tune weight if needed.
**Trigger**: C8 SHIPs + visual review of 20+ production plans with grid-offset envelopes.
**S31-scope verdict**: OUT.
**Effort**: S.

### B-126 — Caller-side retry helper for CorridorDispatchError

**Origin**: C8 v0.5 critique walk #4 Drawback 3 (originally placeholder B-NNN-R).
**Status**: BACKLOG (downstream-component-orchestration concern; NOT a C8 spec defect).
**Description**: When higher-level pipeline orchestrator receives `CorridorDispatchError` from C8, it must hand-roll retry logic. v0.5 § 14.23 enriched-diagnostic contract makes retry *possible* via metadata fields but doesn't make it *easy*. A `retry_with_next_candidate()` helper utility would standardize the retry contract across pipeline consumers.

**Why NOT a C8 concern** (per industry consensus on retry/circuit-breaker patterns, verified S31 web research): recovery orchestration belongs to *caller*, not *callee*. AWS Prescriptive Guidance, AppMaster, Temporal all converge: callee exposes diagnostic metadata; caller decides retry policy. v0.5's § 14.23 follows this pattern correctly. Adding helper to C8 would couple C8 to caller-side retry policy (Pattern E risk).

**Where helper belongs**: in a higher-level pipeline-orchestration component (likely C14 or new pipeline orchestrator), NOT in C8.
**Trigger**: First higher-level pipeline component that consumes C8 output and needs to handle dispatch failures gracefully.
**S31-scope verdict**: OUT — pipeline-orchestration concern, not C8-build-time. Filed as C8 backlog item per Ramalingam direction at walk #4 close (option B) for full audit-trail visibility.
**Effort**: S (helper is a small wrapper; orchestrator is separate work).

---

**S31 session total adds**: 19 items (B-108 through B-126; B-110 was placeholder-pre-LOCK, became concrete). Pre-S31 max: B-107. **New canonical max: B-126**.

**Cross-reference**: spec § 12 of `28_C8_SPEC_v0_5_LOCKED.md` is canonical; this file is the project-level mirror per Rule 9.


---

## S32 additions — pre-build empirical findings (4 May 2026)

### B-127 — Reconstruct C6 production tests from SPEC v0.7 § 7

**Origin**: S32 pre-build doubt resolution. C6 v0.7 review file header claims 186 tests across 6 test files (`test_c6_failure_modes.py`, `test_c6_schema.py`, `test_c6_vastu_kb.py`, `test_c6_signals.py`, `test_c6_optimizer.py`, `test_c6_select.py`). Empirical inspection at S32 open: zero `test_c6_*.py` files exist in `06_upstream_codebase/buildemup/tests/validation/` of v8 bundle. The 186 tests were authored during S31 build but did not survive into the v8 bundle.
**Status**: BACKLOG (high importance; not C8-blocking).
**Description**: Reconstruct from spec § 7 test plan in `26_C6_SPEC_v0_7_LOCKED.md`. C6 spec contract is trusted via its public API for the C8 build (verified at S32 open: `from buildemup.components.c06 import prioritize_orientation, OrientedCandidate, OrientationPriority` succeeds after C6 deploy from review file).
**Trigger**: After C8 SHIP, OR before any future critique walk on C6 that requires reproducible test evidence.
**S32-scope verdict**: OUT — C8 build is the priority. C6 spec contract trusted via public API.
**Effort**: M (~half a session).

### B-128 — Bundle integrity check should verify SHIPPED components have production code in upstream

**Origin**: S32 pre-build doubt resolution. v8 bundle INTEGRITY CHECK passed (claimed `tests baseline 1725/1 unchanged`) despite C6 production code being absent from `06_upstream_codebase/`. Empirical re-test at S32 open with the bundle alone: 1539 passed / 1 skipped (NOT 1725). The S31 INTEGRITY CHECK relied on a stated count without executing pytest against the bundle's own tree.
**Status**: BACKLOG (process improvement; applies to all future bundle handoffs from this session forward).
**Description**: Future bundles must include an executable integrity step: clone the bundle's `06_upstream_codebase/`, run pytest, confirm the claimed test count actually reproduces. Any SHIPPED component whose production code is not in the upstream snapshot is a SHIP-claim violation. Add to Rule 10.6 INTEGRITY CHECK protocol as a mandatory check before bundle delivery.
**Trigger**: Next handoff bundle (v9 / S32 close).
**S32-scope verdict**: PROCESS-LEVEL — applies to S32's own bundle assembly; do not skip.
**Effort**: S (~30 minutes to write the verification protocol; adopting it adds ~10 minutes per handoff).

### S32 deploy-from-review-file action (audit trail)

**Action taken at S32 open**: deployed C6 from `03_code_chronological/S31_C6_v0_7_review/buildemup_c06_consolidated_v0_7.py` into `/home/claude/work/buildemup/components/c06/` by splitting at the 6 FILE markers (no content modification). Deploy verified: import succeeds, 1539 baseline preserved (no regressions; no new tests since C6 tests not in bundle per B-127).

**Adjusted SHIP target for S32**: ~1539 baseline + ~155 C8 new = **~1694 passed / 1 skipped** (NOT 1880 as the original handoff projected, since C6's 186 tests are missing per B-127).

**Post-S32 max**: B-128.

### B-129 — Spec § 4.3.1 truncation rule conflicts with Inv 20 (length/2 vs length/4)

**Origin**: S32 C8 implementation. While building junction_propagation, hit Inv 20 violation on the spec's own § 4.10 BRANCH worked example (PRIMARY=1.65m, BRANCH=1.20m, bay_min=3.3m, BRANCH length=5m).

**The conflict**:
- § 4.3.1 truncation rule: `taper_zone_m ≤ segment_length / 2 (per side)`. For length=5m, max_allowed=2.5m.
- Inv 20: `constant_middle_length ≥ length / 2`. For length=5m, requires middle ≥ 2.5m, i.e., total taper-overhead ≤ 2.5m.

If both ends have a taper at length/2 each, total taper = length, leaving 0 for middle → Inv 20 violated.

The spec's own § 4.10 worked example (BRANCH single-end-taper of 3.3m on length=5m) computes `middle = 5 - 3.3 = 1.7m < length/2 = 2.5m` — Inv 20 also violated as written.

**S32 implementation deviation** (to make build LOCKABLE): the schema's Inv 20 check now counts only **actual** tapers (ends where width differs from constant_width), not 2× always. Under this interpretation:
- BRANCH with single junction (only start tapers): n_tapers=1, total = 1 × taper_zone_m
- For BRANCH 5m / bay 3.3m: truncation fires (3.3 > 2.5), taper=2.5, middle = 5 - 2.5 = 2.5 ≥ 2.5 ✓

This matches the spec's worked-example *intent* (one-end taper, middle preserved) while satisfying Inv 20 strictly.

**Status**: BACKLOG (spec defect; implementation workaround in place; not C8-blocking).

**Resolution path**: v0.6 PROPOSED amendment to § 4.3.1 + Inv 20:
- (a) Clarify that Inv 20 counts actual tapers only (where start_width or end_width != constant_width).
- (b) Update truncation rule to clamp to `length / (2 + 2 × N)` where N = number of tapered ends ∈ {1, 2}, ensuring Inv 20 holds for both single-end and double-end tapers.
- (c) Re-run § 4.10 worked example arithmetic.

**Trigger**: Next C8 spec amendment cycle. Ramalingam adjudicates (Rule 8); spec moves to v0.6 PROPOSED → LOCK.

**S32-scope verdict**: OUT — deviation documented; implementation matches spec intent; spec text inconsistency to be resolved at next walk.

**Effort**: S (~30 min for spec text update + worked-example re-verification).

**Post-S32 max**: B-129.

---

# S33 ADDITIONS (5 May 2026)

S33 added 24 backlog entries across the C8 critique walk and C9 spec arc. 12 were RESOLVED via this session's patches; 1 was CLOSED into spec body; 11 are OPEN for future sessions.

---

## B-130 — Sweep-line refactor of `area_accounting.py`

**Origin**: C8 walk #1 (S33).
**Status**: BACKLOG.
**Trigger**: When C11 placement performance becomes a bottleneck OR when the 1cm rasterization shows correctness issues at extreme scale.
**Description**: C8 spec § 4.8 documents a deliberate v1 simplification: 1cm rasterization for polygon union area calculation. The spec's algorithmic ideal is O(N³ log N) sweep-line. v1 simplification is correctness-verified on the 3 spec verification cases; performance has not been an issue at v1 scale. B-130 captures the future-refactor work.
**Effort**: M (sweep-line implementation + Cunningham/CGAL-style edge-case handling).

## B-131 — N-aware `n_tapered_ends` threading — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: After C8 v0.6 amendment, code-side change to thread `n_tapered_ends` through `resolve_taper_zone_m` per the new N-aware math. Patched in `width_selection.py`.

## B-132 — Real grid-alignment measurement — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: `validator.py` previously used a coarse grid-alignment proxy. B-132 replaced with real measurement against `Grid.bay_x_m` / `Grid.bay_y_m`. Surfaced B-145 (filed; deferred).

## B-133 — Typed `CorridorSelfIntersectionError` — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: Self-intersection detection previously raised generic `ValueError`. B-133 introduces typed `CorridorSelfIntersectionError` per spec § 6 / § 14.17.

## B-134 — Junction-snap normalization — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: `topology_dispatch.py` junction handling normalized per spec § 4.7.

## B-135 — Upstream trace IDs threading — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: Provenance now carries upstream `plot_analysis_trace_id` for traceability across C4 → C5 → C6 → C7 → C8 chain.

## B-136 — Envelope-overflow narrowing — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: `area_accounting.py` envelope handling tightened to detect overflow conditions correctly.

## B-137 — BAND_ATTACHMENT tagging — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch (surfaced B-144).
**Description**: `validator.py` Inv 6 adjacency check now tags BAND_ATTACHMENT relationships explicitly. Patch revealed semantic gap → B-144.

## B-138 — ENTRY_STUB construction — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: `corridor_designer.py` ENTRY_STUB type construction per spec § 4.x.

## B-139 — Deferred patch follow-on

**Origin**: C8 walk #1 (S33).
**Status**: BACKLOG.
**Description**: Minor follow-on identified during patch sequence; non-blocking. Defer to C8 walks #2/#3 or to next C8-touch.
**Effort**: S.

## B-140 — Deferred patch follow-on (sweep-line partner of B-130)

**Origin**: C8 walk #1 (S33).
**Status**: BACKLOG.
**Description**: Companion to B-130; captures the test-coverage component of the sweep-line refactor.
**Effort**: S.

## B-141 — Junction taper accumulation cap — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: `junction_propagation.py` taper accumulation now respects the N-aware cap from § 4.10.

## B-142 — NEW centralized `tolerances.py` module — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: Centralized tolerance constants (geometric epsilon, area threshold, etc.) into a single module. Eliminates drift across other modules. NEW file (99 LOC).

## B-143 — Inv 14 explicit defensive check — RESOLVED

**Origin**: C8 walk #1 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: `validator.py` Inv 14 (envelope coverage) now has explicit defensive check.

## B-144 — Inv 6 bay-proximity adjacency — RESOLVED

**Origin**: C8 walk #1, surfaced by B-137 (S33).
**Status**: RESOLVED via S33 patch.
**Description**: After B-137 introduced BAND_ATTACHMENT tagging, the prior coarse Inv 6 adjacency was semantically wrong. B-144 replaces with bay-proximity-aware adjacency per spec intent.

## B-145 — Surfaced by B-132

**Origin**: C8 walk #1, surfaced by B-132 (S33).
**Status**: BACKLOG.
**Description**: B-132's real grid-alignment measurement revealed a downstream issue. Filed for future investigation.
**Effort**: S.

## B-146, B-147 — Walk-on-walk follow-ons

**Origin**: C8 walk #1 (S33).
**Status**: BACKLOG.
**Description**: Minor follow-ons surfaced during the 12-patch sequence; non-blocking; deferred.
**Effort**: S each.

## B-148 — Multi-floor dwelling-tier (whole-dwelling auto-derived from C2)

**Origin**: C9 walk #2 (S33).
**Status**: BACKLOG.
**Trigger**: First multi-floor test case where caller doesn't supply `assumed_total_dwelling_area_m2`.
**Description**: C9 v0.7 supports user-supplied `assumed_total_dwelling_area_m2` (defensive LARGE-pick when not supplied). B-148 lifts this to auto-derive from C2's brief when whole-dwelling area is computable. Requires C2-side amendment to thread total dwelling area through C2 → C3 → ... → C9.
**Effort**: M (cross-component coordination).

## B-149 — Packing-efficiency tightening to ERROR mode

**Origin**: C9 walk #2 (S33).
**Status**: BACKLOG.
**Trigger**: Empirical calibration data from C11 placement runs.
**Description**: C9 Inv 10 (heuristic_packing_check) is WARN by default. v0.7 STRICT mode escalates to RAISE. B-149 examines whether the 0.75 packing efficiency default is correctly calibrated; may need tightening to e.g. 0.8 based on real placement data.
**Effort**: S.

## B-150 — NBC clause verification against authoritative PDF

**Origin**: C9 walk #2 (S33).
**Status**: BACKLOG.
**Trigger**: Regulator/inspector challenge OR pre-launch compliance review.
**Description**: C9 v0.7 NBC values are sourced from secondary sources with documented disagreement (slideshare bye-laws vs InfraLens). Each row carries `source_confidence` (most SECONDARY_CONSENSUS; storeroom SECONDARY_UNVERIFIED). B-150 is a 2-3 day independent verification pass against the authoritative NBC 2016 Part 3 PDF; promotes verified rows to `VERIFIED`.
**Effort**: S (one-time verification pass; no code changes once data is correct).

## B-151 — OTHER subtype-driven sizing

**Origin**: C9 walk #3 (S33).
**Status**: BACKLOG.
**Trigger**: First product feature requiring differentiated study/office/guest-room sizing.
**Description**: C9 v0.7 OTHER category is sized as a generic pool. `other_subtype` field exists but doesn't drive sizing. B-151 introduces sizing differentiation per subtype (study vs guest vs office have different furniture profiles).
**Effort**: M (new KB entries + furniture-floor lookups + tests).

## ~~B-152~~ — Combined placement_risk_level — CLOSED

**Origin**: C9 walk #4 (S33).
**Status**: **CLOSED** at C9 v0.5 (S33).
**Description**: Was filed as BACKLOG at walk #4. Resolved into spec body at v0.5 with `PlacementRiskLevel` enum + severity-weighted derivation. Walk #6 refined to severity-weighted aggregation.
**Resolution**: Spec body §§ 4.7 + 14.31 + 14.36.

## B-NNN-J — `WidthInfeasibleError` typed exception class

**Origin**: C9 walk #6 (S33).
**Status**: TO-BE-IMPLEMENTED IN BUILD.
**Trigger**: C9 build session (S34).
**Description**: C9 spec § 6 specifies typed exception hierarchy. `WidthInfeasibleError` is a build artefact; the file `components/c09/errors.py` will define this class extending `PerCandidateError`. No standalone defect; trivial implementation.

## B-NNN-K — `GridOversizeError` typed exception class

**Origin**: C9 walk #7 (S33).
**Status**: TO-BE-IMPLEMENTED IN BUILD.
**Trigger**: C9 build session (S34).
**Description**: C9 spec § 6 specifies typed exception hierarchy. `GridOversizeError` is a build artefact for STRICT-mode escalation of Inv 18 OVERSIZED. The file `components/c09/errors.py` will define this class extending `PerCandidateError`. No standalone defect; trivial implementation.

---

**Post-S33 max**: B-NNN-K (and 14 numeric items B-130 through B-152).

**Active items needing future-session attention**:
- B-130, B-139, B-140, B-145, B-146, B-147 — C8 deferred follow-ons
- B-148, B-149, B-150, B-151 — C9 build-time and post-build backlog
- B-NNN-J, B-NNN-K — C9 build artefacts

**Resolved this session**: B-127 (C6 reconstruction), B-128 (re-executed protocol), B-129 (C8 amendment), B-131 through B-138 except B-139 (12 patches), B-141, B-142, B-143, B-144 (12 RESOLVED), B-152 (CLOSED into spec).
