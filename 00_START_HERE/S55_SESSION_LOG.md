# 🚧 S55 SESSION LOG — Bucket B Batch 2

**Authored:** Ramalingam + Claude, S55 open, May 16, 2026
**Predecessor:** `S54_SESSION_LOG.md` (S54 close — 14 items shipped, repo pushed to GitHub, CI active)
**Status:** Batch 2 complete (7 items). Bucket B reduced from ~47 → ~40 open items.

---

## TL;DR

- Session continued Bucket B from where S54 left off, user authorization "everything in bucket B but you can choose what order."
- 7 items shipped in Batch 2: B-074, B-062, B-064, B-013, B-108 (partial), B-109, B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (HIGH priority).
- 4,297 of 4,297 tests pass across S54+S55-touched surface (excluding 21 pre-existing baseline failures in `test_c01_v09_session_b.py` Windows-handle issues + `test_c02_session_j/k/l.py` that were not caused by S55).
- 48 new test cases added across 7 new `tests/test_s55_*.py` files.

---

## Order of work (multi-session plan locked at session open)

| Batch | Cluster | Status |
|---|---|---|
| Batch 2 (this session) | C12 HIGH + remaining small clusters | ✅ DONE |
| Batch 3 | C11a/b + C13 + C12 leftovers + C17 critique | ⏳ pending |
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

## What's next (Batch 3 candidates)

Remaining Bucket B clusters from S54 triage (now ~40 open):

| Cluster | Count | Notes |
|---|---|---|
| C14/C15/C16 LOCK-mandatory | ~28 | Biggest pile; each item is hours of focused spec work |
| C17 critique findings | 7 | Semantic-match, arithmetic-mismatch, rate-sanity OCR |
| C13 v1.x polish | 3 | Invariant taxonomy, adversarial corpus, window avoidance |
| C11a/b launch-complement | 6 | **B-NEW-J-override must ship with C11a v1** |
| C12 critique-walk leftover | 2 | B-C12-CAUSAL-FAILURE-TRACEABILITY, B-PROJECT-SPEC-DRIFT-CI |
| C6 trust gap | 2 | B-127 reconstruct 186 missing tests; B-128 bundle integrity |
| B-066 polygon plots | 1 | Large effort; touches C5/C7/C8 |

**Recommended Batch 3:** C11a/b launch-complement (lead with B-NEW-J-override) + C13 v1.x polish + C12 leftovers. Mid-size effort, mostly post-launch polish for already-shipped components.

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
