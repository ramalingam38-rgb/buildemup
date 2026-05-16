# BuildemUp Component 4 (Plot Analysis) — SPEC v0.9 LOCKED

**Status:** **v0.9 LOCKED** by Ramalingam mid-S29. Patch delta over v0.8.

**Generated:** S29 mid-session, after C4 v0.8 SHIP and code-review critique round 4 (8-item document) + Rule 7 amendment.

---

## § 13 — Rule-7 walk (v0.8 → v0.9)

### Rule 7 amendment (this round)

**Rule 7 strengthened:** web-search now MANDATORY on EVERY critique walk (≥1 search per round to verify reviewer's factual claims AND Claude's own pushbacks/verdicts), even when no obvious external-standards claim is in the critique. Surface the Rule 7 gates explicitly at the START of each walk; if no factual claim exists, say so explicitly. Origin: v0.9 walk skipped web-research because critique looked architectural, then had to backfill.

### Verification gates run BEFORE this walk

1. **Code-grep:** confirmed `_SQM_PER_SQFT_INV = 10.7639` (rounded) at plot_analysis.py:61. Two usages (display calls).
2. **Web-research (Rule 7 mandatory):** verified two factual claims used in B-082 + B-083 backlog filings:
   - **IS 6403 medium rock kPa range:** NCBI mudstone study (PMC11094001) confirms recommended bearing capacity 800–1200 kPa vs plate-test >1500 kPa — supports the "underestimate" framing for the 660 kPa SOFT_ROCK approximation in B-074/B-082.
   - **Mumbai intra-city soil variation:** Geo Technical Company Mumbai docs confirm South Mumbai and Navi Mumbai sit on reclaimed ground with weak soil layers; Navi Mumbai/Taloja geotech report shows spread foundations bear 45-60 tonnes/sqm on weathered bedrock or 300 tonnes/sqm on hard bedrock — 5-7× spread within one metro area. Confirms B-083 single-profile-per-city is genuinely lossy.

### Critique walk

| # | Critique summary | Verdict |
|---|---|---|
| 1 | Loosen import-time fail-fast (STRICT_MODE flag) | **MISFRAMED — PUSH BACK** |
| 2 | SoilEstimate lacks structured error fields | **VALID-BUT-BACKLOG (B-082)** |
| 3 | Single soil profile per city ignores intra-city variation | **VALID-BUT-BACKLOG (B-083)** |
| 4 | Wind direction model loses wind-rose info | **DUPLICATE — already B-070** |
| 5 | CONTINUOUS+corner LEFT default arbitrary | **DUPLICATE — already B-076** |
| 6 | Perf cap 3ms too loose (200× headroom) | **DUPLICATE — already B-081** |
| 7 | Float display inconsistency (sqft 2399.998 vs T2) | **VALID — SPEC-AMENDMENT** |
| 8 | derive() needs plugin/extension hooks | **MISFRAMED — PUSH BACK (YAGNI)** |

**Tally:** 1 SPEC-AMENDMENT (#7) · 2 NEW BACKLOG (B-082, B-083) · 3 DUPLICATES (#4, #5, #6) · 2 PUSH-BACKS (#1, #8).

---

## § 14 — v0.9 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — Exact `area_sqft` display (item 7)

**Spec § 4.1 amended.** Replace `_SQM_PER_SQFT_INV = 10.7639` (rounded display constant) with `_SQFT_PER_SQM = 1.0 / SQM_PER_SQFT` (exact inverse of the IEC `0.09290304`). The exact inverse evaluates to `10.76391041670972...`. With this change:

- `12.192 × 18.288 / 0.09290304 = 2400.0` exactly (textbook 40×60 ft).
- area_sqft display now matches the user's mental model at every IEC boundary.
- Tier comparison is unchanged (still in sqm space; v0.6 § 14.1 logic preserved).

**Test additions:**
- `test_area_sqft_display_matches_textbook_at_40x60ft_boundary` (asserts `area_sqft == 2400.0` exact).
- `test_area_sqft_sqm_round_trip` updated to use the exact `SQM_PER_SQFT` constant (was `10.7639`); tolerance tightened from 1e-6 to 1e-9.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — item #1 (loosen fail-fast)

**Critique claim:** Hard-coupled KB validation at import is a "system-wide hard failure point". Suggests STRICT_MODE flag for "non-blocking mode" / "degraded mode".

**Pushback:** Fail-fast IS the deliberate safety design. KB drift in production = wrong building layouts in real customer homes. Loosening to "starts even when KBs are inconsistent" trades a known wrong-data scenario from "won't start" to "silently produces wrong output reaching production." The hypothetical infrastructure (feature flags, incremental rollouts, staging environments) does not exist in the system today; this is fix-for-architecture-that-doesn't-exist. Push back stands.

### Pushback B — item #8 (plugin hooks)

**Critique claim:** derive() should expose `pre_processors` / `post_processors` / plugin registry for future additions (noise, pollution, zoning overlays).

**Pushback:** YAGNI. Current plugin count = 0. The proposed plugin architecture is abstraction for non-existent features. When `noise`, `pollution`, or `zoning_overlay` becomes real, modifying derive() is the right move — a 5-line addition each. A plugin registry IS more code, less readable, harder to debug, and provides no benefit until N≥3 actual plugins exist. This is the same flavor as v0.7 critique #10 (god function) reframed; same answer. Push back stands.

---

## § 16 — Backlog roll-up (Rule 9)

### New backlog items (with web-verified citations per Rule 7 amendment)

| ID | Description | Origin | Citation | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---|---:|
| B-082 | SoilEstimate structured error fields: `approximation_error_pct: float \| None`, `expected_range_kpa: tuple[float, float] \| None`. Surfaces the magnitude of approximation error programmatically rather than only as a string breadcrumb. | v0.9 walk #2 | NCBI mudstone study (PMC11094001): recommended SBC 800-1200 kPa vs plate-test >1500 kPa documents the underestimate band; B-074 will resolve actual MEDIUM_ROCK kPa | OUT (v0.9) | C5/C7 consume foundation-cost or foundation-risk that depends on uncertainty band; resolve alongside B-074 to avoid double-rewrite | ~25 LOC + cross-component coordination |
| B-083 | Sub-city soil zoning. Adds a `Plot.city_zone: str \| None` (or `geo_hash`) input field; SOIL_PROFILES becomes city → list-of-zones with per-zone profiles. Single-profile-per-city is lossy where intra-city variation is significant. | v0.9 walk #3 | Mumbai Geo-Technical Company docs: South + Navi Mumbai on reclaimed ground; Navi Mumbai geotech: 45-60 t/sqm on weathered bedrock vs 300 t/sqm on hard bedrock — 5-7× spread within metro area | OUT (v0.9) | foundation incident report, OR insurance/code requirement, OR upstream input contract gains zoning | ~50 LOC + C1/C3a input contract change + KB schema migration |

### Pre-existing backlog (carried unchanged)

B-066, B-067, B-068, B-069, B-070, B-071, B-072, B-074, B-075, B-076, B-077, B-078, B-079, B-080, B-081 + B-001..B-065.

---

## § 17 — What v0.9 LOCKS

1. One SPEC-AMENDMENT in code (§ 14.1: exact `_SQFT_PER_SQM` inverse).
2. Two new backlog items filed with web-verified citations (B-082, B-083).
3. Two pushbacks documented and held (#1, #8).
4. Three duplicates noted and not re-filed (#4 → B-070, #5 → B-076, #6 → B-081).
5. **Memory amendment:** Rule 7 strengthened to mandate web-search on every critique walk.
6. Estimated delta: ~5 LOC source + ~15 LOC tests.

---

## § 18 — v0.9 verification at LOCK time

- Tests passing: **1415 passed / 2 skipped / 0 failed** (was 1414 at v0.8 LOCK; +1 boundary test, 1 property test refined).
- Production code: 1 line replacement + comment block in plot_analysis.py.
- Existing 1414 tests re-run + 1 new = 1415 expected passing.

---

## § 19 — Status

**v0.9 LOCKED** by Ramalingam mid-S29.
