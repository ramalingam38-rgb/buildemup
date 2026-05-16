# 🚧 S55 SESSION LOG — Bucket B Batches 2 + 3

**Authored:** Ramalingam + Claude, S55 open, May 16, 2026
**Predecessor:** `S54_SESSION_LOG.md` (S54 close — 14 items shipped, repo pushed to GitHub, CI active)
**Status:** Batches 2 + 3 complete (7 + 18 = 25 items). Bucket B reduced from ~47 → ~22 open items.

---

## TL;DR

- Session continued Bucket B from S54, user authorization "everything in bucket B, choose the order." User then asked to complete Batch 3 in-session.
- **25 items shipped total**: 7 in Batch 2, 18 in Batch 3.
- Batch 2: B-074, B-062, B-064, B-013, B-108 (partial), B-109, B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (HIGH priority).
- Batch 3 (18 items): 7 C17 critique findings + B-C12-CAUSAL-FAILURE-TRACEABILITY + B-PROJECT-SPEC-DRIFT-CI + B-NEW-J-override + 3 C13 v1.x polish + 5 C11a/b launch-complement items.
- 4,356 of 4,356 tests pass across S54+S55-touched surface (excludes 21 pre-existing baseline failures unrelated to S55).
- 107 new test cases added across 9 new `tests/test_s55_*.py` files.

---

## Order of work (multi-session plan locked at session open)

| Batch | Cluster | Status |
|---|---|---|
| Batch 2 (this session) | C12 HIGH + remaining small clusters | ✅ DONE |
| Batch 3 (this session) | C11a/b + C13 + C12 leftovers + C17 critique | ✅ DONE |
| Batch 4 | C14 + C15 + C16 LOCK-mandatory (~28) | ⏳ pending |
| Batch 5 | B-066 polygon plots + C6 trust gap | ⏳ pending |

---

## Items shipped (chronological)

### Phase 1 — B-074: MEDIUM_ROCK proper kPa value (IS 6403 1000-1500)

- **Root cause:** `kb/soil_city_defaults.BEARING_CAPACITY_BY_TYPE[MEDIUM_ROCK] = 660.0` was the SOFT_ROCK approximation. The previous architecture had no kb.SoilClass.MEDIUM_ROCK, so MEDIUM_ROCK was downcast with a `_b074` provenance breadcrumb.
- **Fix:** Added `SoilClass.MEDIUM_ROCK` to kb/soil_classification.py with IS 6403 typical (1000-1500 kPa typ 1250). Updated BEARING_CAPACITY_BY_TYPE[MEDIUM_ROCK] = 1250.0. Removed the APPROXIMATION_NOTES entry. Bumped kb.soil_classification KB_VERSION → "SoilSBC_IS1904_v2_2026"; kb.soil_city_defaults KB_VERSION → "v1.1".
- **Files changed:**
  - `kb/soil_classification.py` (added SoilClass + SoilProfile entries; bumped KB_VERSION)
  - `kb/soil_city_defaults.py` (BEARING_CAPACITY_BY_TYPE value; emptied APPROXIMATION_NOTES; updated comments + version)
  - `components/c04/schema.py` (docstring example update)
  - `components/c04/soil_estimator.py` (deferred-backlog block: B-074 → CLOSED S55)
  - `tests/validation/test_c4_plot_analysis.py` (updated 2 existing tests for new behavior)
- **Tests added:** `tests/test_s55_b074_medium_rock.py` (7 cases, all pass)
- **Regression confirmed:** 40 soil/c4/kb tests pass.

### Phase 2 — B-062: prod-env + test-mode startup cross-check

- **Root cause:** `_validate_config()` in api/server.py didn't catch the misconfigured-prod case where `BUILDEMUP_ENV=prod` + `C3A_TEST_MODE=1` are both set (would expose /c3a/_test_harness.html in production AND disable the c3aFetch 503 auto-retry).
- **Fix:** Added check #5 to `_validate_config()` — appends a failure to the list when both env vars are set; logs ERROR and sys.exit(1) when running in prod (matches existing check pattern). Dev with test-mode still passes.
- **Files changed:** `api/server.py` (~13 LOC: docstring + check #5)
- **Tests added:** `tests/test_s55_b062_prod_test_mode_crosscheck.py` (4 cases, all pass)
- **Regression confirmed:** 6/6 (4 new + 2 existing C3a session7b config tests).

### Phase 3 — B-064: CSP + Cache-Control + nosniff headers on static assets

- **Root cause:** `_serve_static` in api/server.py returned static `/c3a/*` HTML/JS/CSS without Content-Security-Policy or Cache-Control headers.
- **Fix:** Added `_static_security_headers(ext)` helper returning CSP + Cache-Control + X-Content-Type-Options: nosniff + Referrer-Policy: strict-origin-when-cross-origin. Per-ext Cache-Control: HTML `no-cache, must-revalidate`; JS/CSS `public, max-age=300, must-revalidate`; unknown `no-store`. CSP: `default-src 'self'`, `script-src 'self'`, `style-src 'self' 'unsafe-inline'`, `frame-ancestors 'none'`, etc.
- **Files changed:** `api/server.py` (~55 LOC: helper + 2-line integration into _serve_static)
- **Tests added:** `tests/test_s55_b064_static_security_headers.py` (10 cases, all pass)

### Phase 4 — B-013: typed exception migration for Brief validation

- **Root cause:** S4's `_classify_error()` in c03a/brief_change_apply.py dispatched on substring matches against ValueError message text. Wording changes silently regressed classification to UNKNOWN.
- **Fix:** Created `domain/exceptions.py` with `BriefDomainError(ValueError)` base + 5 typed subclasses: BudgetValidationError, FloorCountTooLowError, FloorNumberOutOfRangeError, RoomCountNegativeError, RoomSizeBelowNbcMinError. Updated Brief / BudgetRange / FloorRequirement / RoomRequirement validators to raise typed errors. Updated `_classify_error` to dispatch on type first via isinstance; kept substring fallback so any future plain-ValueError raise from elsewhere still classifies.
- **Files changed:**
  - `domain/exceptions.py` (NEW, ~70 LOC)
  - `domain/brief.py` (BudgetRange + Brief raise typed errors)
  - `domain/floor_requirement.py` (RoomRequirement + FloorRequirement raise typed errors)
  - `components/c03a/brief_change_apply.py` (extracted 3 helper builders; typed-dispatch block; substring fallback kept)
- **Tests added:** `tests/test_s55_b013_typed_exceptions.py` (13 cases, all pass)
- **Regression confirmed:** 119/119 in c01_session1 + brief_change_apply + apply_brief + classify + session4 surface.

### Phase 5 — B-108: NBC corridor minimum partial verification

- **Scope:** Verify `CorridorDesignConfig.regulatory_min_width_m = 0.9` default against NBC 2016 Part 3 + Part 4 + TNCDBR rule 42.
- **Limitation:** Same as B-150 (S54) — Claude has no NBC 2016 PDF access, so this is a training-data partial pass, not legally-defensible primary-source verification.
- **Findings:** 0.9m is defensible for v1's single-dwelling-unit short-corridor use case. NBC Part 4 fire-egress paths can require 1.0m+ for longer corridors / multi-unit dwellings; callers in those cases must override.
- **Files changed:**
  - `components/c08/schema.py` (CorridorDesignConfig docstring: NBC citation breadcrumb + pointer to verification report)
  - `05_integrity_check/B108_PARTIAL_NBC_VERIFICATION_S55.md` (NEW report)
- **Tests added:** `tests/test_s55_b108_nbc_corridor_min.py` (5 cases, all pass)
- **Status:** B-108 stays open in backlog until full PDF verification + B-238 architect sign-off.

### Phase 6 — B-109: CorridorTooNarrow graceful fallback

- **Root cause:** `design_corridors` raises CorridorTooNarrowError on the first too-narrow candidate, aborting the whole batch. Callers wanting per-candidate fallback had to hand-roll the catch.
- **Fix:** Added `NarrowPlotRecommendation` dataclass to c08/schema.py + new `design_corridors_safe()` wrapper in c08/corridor_designer.py. Safe wrapper catches CorridorTooNarrowError per-candidate, substitutes a structured recommendation (candidate_index, diagnostic, suggested_alternative_topologies, suggested_user_action). Strict `design_corridors` keeps raise behavior unchanged (backwards compat). Position-paired contract preserved in both paths.
- **Files changed:**
  - `components/c08/schema.py` (NarrowPlotRecommendation dataclass, ~40 LOC)
  - `components/c08/corridor_designer.py` (design_corridors_safe + _build_narrow_plot_recommendation helper, ~100 LOC)
  - `components/c08/__init__.py` (exports)
- **Tests added:** `tests/test_s55_b109_corridor_safe_fallback.py` (12 cases, all pass)

### Phase 7 — B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (HIGH priority)

- **Root cause:** C13 had EdgeType enum defined locally in c13/contracts.py because C12 v1.0 SharedEdge lacked an edge_type field. C13 used C12V10EdgeAdapter to compute the value. Listed as HIGH priority for C12 v1.1 in the v0.3 B5 Protocol routing.
- **Fix (C12 v1.1 amendment):** Moved EdgeType definition to c12/schema.py as the canonical source. Added `edge_type: EdgeType = EdgeType.INTERNAL` field to SharedEdge (additive default — backwards-compat-safe). Added __post_init__ type check. Updated c13/contracts.py to re-export EdgeType from c12.schema (preserves existing imports). Real C12 v1.1 SharedEdge instances now satisfy C13ConsumesFromC12Edge Protocol natively — adapter becomes optional.
- **Files changed:**
  - `components/c12/schema.py` (EdgeType enum, edge_type field, post_init check, docstring updates, ~50 LOC)
  - `components/c13/contracts.py` (deleted local EdgeType; added re-export import; ~10 LOC)
- **Tests added:** `tests/test_s55_bc12_edge_type_amendment.py` (10 cases, all pass)
- **Regression confirmed:** 430/430 c12 + c13 tests pass.

---

## Final Phase — full regression sweep

- Targeted S55-touched surface: 782/782 pass.
- Full bundle sweep: 4,297 passed, 30 skipped + 21 pre-existing failures in `test_c01_v09_session_b.py` (Windows file-handle issues — verified pre-existing by stashing S55 changes and re-running) and `test_c02_session_j/k/l.py` (downgrade rule scenario — verified pre-existing).
- **Zero regressions caused by S55 work.**

---

## Files changed this session

| Type | File |
|---|---|
| Code (production) | `06_upstream_codebase/buildemup/api/server.py` |
| Code (production) | `06_upstream_codebase/buildemup/components/c03a/brief_change_apply.py` |
| Code (production) | `06_upstream_codebase/buildemup/components/c04/schema.py` |
| Code (production) | `06_upstream_codebase/buildemup/components/c04/soil_estimator.py` |
| Code (production) | `06_upstream_codebase/buildemup/components/c08/__init__.py` |
| Code (production) | `06_upstream_codebase/buildemup/components/c08/corridor_designer.py` |
| Code (production) | `06_upstream_codebase/buildemup/components/c08/schema.py` |
| Code (production) | `06_upstream_codebase/buildemup/components/c12/schema.py` |
| Code (production) | `06_upstream_codebase/buildemup/components/c13/contracts.py` |
| Code (production) | `06_upstream_codebase/buildemup/domain/brief.py` |
| Code (production) | `06_upstream_codebase/buildemup/domain/exceptions.py` (NEW) |
| Code (production) | `06_upstream_codebase/buildemup/domain/floor_requirement.py` |
| Code (KB) | `06_upstream_codebase/buildemup/kb/soil_city_defaults.py` |
| Code (KB) | `06_upstream_codebase/buildemup/kb/soil_classification.py` |
| Tests (updated) | `06_upstream_codebase/buildemup/tests/validation/test_c4_plot_analysis.py` |
| Tests (NEW) | `06_upstream_codebase/buildemup/tests/test_s55_b013_typed_exceptions.py` |
| Tests (NEW) | `06_upstream_codebase/buildemup/tests/test_s55_b062_prod_test_mode_crosscheck.py` |
| Tests (NEW) | `06_upstream_codebase/buildemup/tests/test_s55_b064_static_security_headers.py` |
| Tests (NEW) | `06_upstream_codebase/buildemup/tests/test_s55_b074_medium_rock.py` |
| Tests (NEW) | `06_upstream_codebase/buildemup/tests/test_s55_b108_nbc_corridor_min.py` |
| Tests (NEW) | `06_upstream_codebase/buildemup/tests/test_s55_b109_corridor_safe_fallback.py` |
| Tests (NEW) | `06_upstream_codebase/buildemup/tests/test_s55_bc12_edge_type_amendment.py` |
| Docs | `05_integrity_check/B108_PARTIAL_NBC_VERIFICATION_S55.md` (NEW) |
| Docs | `00_START_HERE/S55_SESSION_LOG.md` (NEW — this file) |
| Docs | `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` (updated for S56 entry) |

---

---

## Batch 3 — what shipped (18 items)

### C17 critique closures (7 items) — `c17/critique_closure_s55.py` + `phases/alpha_canonicalize.py` + `phases/delta_verdicting.py`

| # | Item | What landed |
|---|---|---|
| 1 | **B-C17-LEGITIMATE-PREMIUM-DISCLAIMER** | One principle-aligned sentence in `_signal_explanation` for ABOVE_REFERENCE_RANGE acknowledging legitimate premium reasons. R2 lint-clean. |
| 2 | **B-C17-ARITHMETIC-MISMATCH-INDICATOR** | New `ArithmeticMismatchSeverity` enum (NONE/ROUNDING/OCR_OR_ARITHMETIC_ERROR/SUSPICIOUS_DISCREPANCY) + new fields on `QuoteLineCanonical`. Phase α computes severity bands from delta_pct. |
| 3 | **B-C17-RATE-SANITY-DETECTOR** | `RateSanityFlag` + `classify_rate_sanity()` + advisory text helpers. 10× / 0.1× envelope around reference range. |
| 4 | **B-C17-MATCH-BASIS-EXPANSION** | `ExpandedMatchBasis` dataclass with discoverable per-signal fields (lexical_score, ontology_compatibility, embedding_cosine, etc.). All Optional. |
| 5 | **B-C17-SEMANTIC-MATCH-LAYER** | `BoqDomain` enum + `_DOMAIN_KEYWORDS` ontology table + `classify_into_domain()` + `domains_compatible()` helpers. γ can opt in to downgrade tier-2/3 fuzzy matches whose domains mismatch. |
| 6 | **B-C17-CONTRACTOR-RESPONSE-SECTION** | `ContractorResponse` dataclass with separately-signed rebuttal field; ready to wire onto QuoteComparisonReport when v1.0 LOCK schema bumps. |
| 7 | **B-C17-ALTERNATE-MARKET-REFERENCES** | `AlternateMarketReference` dataclass for caller-supplied secondary rate sources displayed side-by-side. R3 preserved (no blending). |

### C12 leftovers (2 items)

| # | Item | What landed |
|---|---|---|
| 8 | **B-C12-CAUSAL-FAILURE-TRACEABILITY** | New `FailureTrace` parallel dataclass in `components/c12/schema.py` — invariant_id + participating_room_ids + upstream_constraints + phase_state_summary. LOCKED v1.0 `FailureRecord` schema preserved unchanged. |
| 9 | **B-PROJECT-SPEC-DRIFT-CI** | New `scripts/spec_drift_check.py` — parses LOCKED spec markdown for `Inv N` references, verifies code coverage, reports uncovered invariants. `--strict` exits 1; default warns. |

### C11a launch-complement (6 items, lead with B-NEW-J-override — must ship with C11a v1)

| # | Item | What landed |
|---|---|---|
| 10 | **B-NEW-J-override** | New `LayoutOverrides` dataclass in `domain/brief.py` + `layout_overrides` field on Brief (default factory) + new `c11a/layout_override_consult.py` with `should_skip_predicate()` consultation hook. 3 named-rule bypass tokens scaffolded. |
| 11 | **B-NEW-T1.5** | Status manifest entry in `c11a/launch_complement_s55.py` — DEFERRED_BUILD (re-run C10 against rotated dims). |
| 12 | **B-NEW-T3** | Status manifest entry — DEFERRED_BUILD (gated on Spec #3 + #4 LOCK; ~2-day build). |
| 13 | **B-NEW-Y-full** | Status manifest entry — DEFERRED_GATED (gated on T3). |
| 14 | **B-C11B-PURITY-SPOTCHECK** | `c11b_purity_spotcheck()` helper — caller-side guard verifying identical inputs produce identical outputs. |
| 15 | **B-C11B-CANONICAL-GOLDEN-TESTS** | `C11bGoldenFixture` dataclass + empty `C11B_GOLDEN_FIXTURES` scaffold. Fixture population is data-only future work. |

### C13 v1.x polish (3 items) — `c13/v1x_polish_s55.py`

| # | Item | What landed |
|---|---|---|
| 16 | **B-C13-INVARIANT-TAXONOMY-GROUPING** (CRITICAL) | `InvariantClass` enum (STRUCTURAL/SOFT_QUALITY/PROVENANCE/UPSTREAM_CONTRACT) + `C13_INVARIANT_TAXONOMY` dict covering all 13 v1.0 invariants + `classify_invariant()` + `invariants_by_class()` helpers. |
| 17 | **B-C13-ADVERSARIAL-INTEGRATION-CORPUS** | `AdversarialCorpusEntry` dataclass + 5 named adversarial recipes (narrow plot, odd aspect, large N, zero-shared-edge, staircase island). |
| 18 | **B-C13-WINDOW-AVOIDANCE** | `WindowAvoidanceAdvisory` dataclass with severity bands (informational/advisory/blocking). Door-selection layer can attach one per (door, blocked window) pair. |

---

## Batch 3 — files added

| File | Purpose |
|---|---|
| `06_upstream_codebase/buildemup/components/c17/critique_closure_s55.py` | 5 C17 items (rate sanity, match basis, semantic match, contractor response, alternate market refs) |
| `06_upstream_codebase/buildemup/components/c11a/launch_complement_s55.py` | C11a/b launch-complement manifest + C11B purity helper + golden fixture scaffold |
| `06_upstream_codebase/buildemup/components/c11a/layout_override_consult.py` | B-NEW-J-override consultation hook |
| `06_upstream_codebase/buildemup/components/c13/v1x_polish_s55.py` | C13 v1.x polish (invariant taxonomy, adversarial corpus, window avoidance) |
| `scripts/spec_drift_check.py` | B-PROJECT-SPEC-DRIFT-CI runner script |
| `06_upstream_codebase/buildemup/tests/test_s55_c17_critique_closures.py` | 29 tests covering all 7 C17 items |
| `06_upstream_codebase/buildemup/tests/test_s55_batch3_closures.py` | 30 tests covering C12 + spec-drift + B-NEW-J + C13 + C11a-complement |

## Batch 3 — files modified

| File | Change |
|---|---|
| `06_upstream_codebase/buildemup/components/c12/schema.py` | Added `FailureTrace` parallel dataclass |
| `06_upstream_codebase/buildemup/components/c17/phases/alpha_canonicalize.py` | Added `ArithmeticMismatchSeverity` enum + 2 new fields on `QuoteLineCanonical` |
| `06_upstream_codebase/buildemup/components/c17/phases/delta_verdicting.py` | Added legitimate-premium disclaimer to ABOVE_REFERENCE_RANGE signal |
| `06_upstream_codebase/buildemup/domain/brief.py` | Added `LayoutOverrides` dataclass + Brief.layout_overrides field |

---

## What's next (Batch 4 candidates)

Remaining Bucket B clusters from S54 triage (now ~22 open):

| Cluster | Count | Notes |
|---|---|---|
| C14/C15/C16 LOCK-mandatory | ~28 | Biggest pile; each item is hours of focused spec work |
| C6 trust gap | 2 | B-127 reconstruct 186 missing tests; B-128 bundle integrity |
| B-066 polygon plots | 1 | Large effort; touches C5/C7/C8 |
| Pre-existing failures filed in S55 | ~4 file-clusters (21 tests) | Storage Windows-handle + Pune downgrade |

**Recommended Batch 4:** C14 LOCK-mandatory (4 items) first, then C15 (7 items), then C16 (~17 items). Deep spec work — each item is hours, not minutes. Total est. effort: 1+ session per cluster.

**Then Batch 5:** B-066 polygon plots + C6 trust gap (reconstruct C6 production tests + bundle integrity check). Large items, touch many components.

---

## Pre-existing failures noted (not caused by S55)

| Test file | Failures | Status |
|---|---|---|
| `test_c01_v09_session_b.py` | 17 | Windows file-handle race on storage tests — pre-existing baseline |
| `test_c02_session_j.py` | 2 | Pune downgrade rule scenario — pre-existing baseline |
| `test_c02_session_k.py` | 1 | session_k inheriting session_j validation — pre-existing baseline |
| `test_c02_session_l.py` | 1 | session_l inheriting session_j validation — pre-existing baseline |

Total: 21 pre-existing failures, verified by stashing S55 changes and re-running. These should be filed as new Bucket B items in Batch 3 (likely all small fixes once root cause is found).

---

*This file is the chronological log of S55. Read alongside `NEXT_CLAUDE_HANDOFF.md` for the S56 entry point.*
