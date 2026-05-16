# Backlog — Session 28 Delta

**Session:** 28
**Date:** 2 May 2026
**Status:** 9 new B-NNN entries filed per Rule 9.2 (always-file backlog directive, codified end of S28).

Source breakdown:
- 4 entries (B-057 → B-060) surfaced by the Session 28 file-by-file audit of pre-existing Phase 5/6 files — see `05_integrity_check/AUDIT_REPORT_PHASE_5_6_FILES_SESSION_28.md`.
- 5 entries (B-061 → B-065) from the Session 28 Rule-7 walk of the external code-critique analysis (15 items; 5 already-documented + 6 misframed-with-pushback + 4 valid-but-backlog).

All 9 are OUT of S8 scope (S8 is LOCKED at v1.2 + 7 phases proposed-complete). None block the S8 ship adjudication or downstream component work.

-----

## B-057 — Visible trace_id on case.html success render

| Field | Value |
|---|---|
| **ID** | B-057 |
| **Description** | `case.js` displays the trace_id only via `displayError` on the error path; on the 200-success path the trace_id is preserved via URL query embedding (`&trace=...` on resolve/abort redirects) but not rendered on the case page itself. Spec § 5.2 line 1637-1639 says: "Display client_trace_id from response (NOT server_trace_id) for support reference, per P43". The current behavior satisfies the SUPPORT-correlation intent (trace IS in the URL the user can copy), but doesn't satisfy a strict reading of "display." |
| **Origin** | Session 28 audit report (B-057 candidate) |
| **Trigger condition** | A user-support incident where someone reports a case-page issue and operators struggle to get the trace_id without coaching them to copy the URL bar. |
| **Effort estimate** | ~5 LOC: add `<p class="c3a-trace" id="case-trace-line">` to case.html; populate from `resp.trace_id` after successful check-init in case.js. |
| **S8/post-S8 scope** | OUT-of-scope for S8. No spec-amendment required — current behavior is a defensible reading of § 5.2 (URL embedding is "displayed"). Defer until support-team feedback says otherwise. |

-----

## B-058 — Full-walk e2e tests (case → resolve → done with seeded backend chain)

| Field | Value |
|---|---|
| **ID** | B-058 |
| **Description** | Each of the existing browser-flow e2e tests (`test_c3a_browser_happy_flow.py`, `test_c3a_browser_cba_flow.py`, `test_c3a_browser_abort.py`) verifies a SUBSET of its named flow (e.g., done.html rendering given a seeded terminal session). None walks the actual end-to-end flow case.html → click resolve → land on done.html. Doing so requires seeding a brief, running C2 feasibility, surfacing an extreme_case via the gate — substantially more setup. |
| **Origin** | Session 28 audit report (B-058 candidate) |
| **Trigger condition** | When a real-world flow regression slips past the current subset tests AND the subset coverage gap is the demonstrable cause (e.g., a redirect-chain bug between case.html → /resolve → done.html). |
| **Effort estimate** | ~80-150 LOC across 3 tests; possibly mock-backed for the C2 feasibility step to avoid pulling C2 into the e2e fixture. |
| **S8/post-S8 scope** | OUT-of-scope. Existing subset coverage + 134-test validation suite (Tier 1) + 24-test e2e suite (Tier 2) collectively cover the integration surfaces. Full-walk is depth, not breadth. |

-----

## B-059 — done.js: PER_CASE_LIMIT_REACHED gets its own success message

| Field | Value |
|---|---|
| **ID** | B-059 |
| **Description** | `done.js` lines 49-61 enumerate terminal-state-specific messages for `CBA_VERIFICATION_PAUSED / CBA_VERIFIED / PREVIEW_MODE / MAX_ITERATIONS_REACHED`, falling through to a generic "Your case has been resolved." for all other states. The fall-through silently catches `PER_CASE_LIMIT_REACHED` (a real `GateTerminationReason` enum value distinct from `MAX_ITERATIONS_REACHED`), which deserves its own message — the user has hit a per-case ceiling, not the global iteration ceiling. |
| **Origin** | Session 28 audit report (B-059 candidate) |
| **Trigger condition** | When user feedback indicates confusion between "case-level" and "iteration-level" limits, or when the `PER_CASE_LIMIT_REACHED` path becomes more common in production. |
| **Effort estimate** | ~2 LOC: one additional `else if` branch in done.js around line 56. |
| **S8/post-S8 scope** | OUT-of-scope. Cosmetic; default fallback is correct ("Your case has been resolved.") just less specific. |

-----

## B-060 — tests/e2e/__init__.py docstring fix ("7 files" → "8 files")

| Field | Value |
|---|---|
| **ID** | B-060 |
| **Description** | `tests/e2e/__init__.py` docstring says "~26 tests across 7 files" but the directory contains 8 test files (test_c3a_browser_happy_flow, _cba_flow, _abort, _resume, _failure, _a11y_auto, _observability, test_handle_page_flow). |
| **Origin** | Session 28 audit report (B-060 candidate) |
| **Trigger condition** | Any cleanup pass on the e2e suite docstrings; or when the file count drifts further from documentation. |
| **Effort estimate** | ~1 LOC. |
| **S8/post-S8 scope** | OUT-of-scope. Cosmetic. Deferring is fine. |

-----

## B-061 — SQLite 503 adaptive backoff with jitter + lock-frequency metric

| Field | Value |
|---|---|
| **ID** | B-061 |
| **Description** | All SQLite lock contention currently maps to a fixed `Retry-After: 5` seconds per spec § 6.2. Refines the existing **B-055** ("Concurrency tuning post-launch") with a concrete proposal: exponential backoff `min(2^retry_count, 30) + random(0, 2)` jitter, plus a `lock_frequency` metric counter feeding alerting/autoscaling. Critique correctly flags thundering-herd risk under sustained contention. |
| **Origin** | Session 28 critique-walk item #2 (verdict: VALID-BUT-BACKLOG). |
| **Trigger condition** | Production telemetry showing repeated 503-storage_busy clusters, OR launch traffic exceeds single-SQLite-write throughput. Same trigger family as B-055; this is the implementation refinement. |
| **Effort estimate** | ~30 LOC in `c3a_endpoint.py` + 1 metric line addition + spec note for the new behavior. |
| **S8/post-S8 scope** | OUT-of-scope for S8. Spec § 6.2 explicitly chose the fixed-5 value for v1; changing it requires a spec-amendment cycle. |

-----

## B-062 — Startup cross-check: prod env vs C3A_TEST_MODE incompatibility

| Field | Value |
|---|---|
| **ID** | B-062 |
| **Description** | Currently nothing prevents a deploy where both `BUILDEMUP_ENV=prod` AND `C3A_TEST_MODE=1` are set simultaneously — a misconfiguration that would expose `/c3a/_test_harness.html` in production AND disable the c3aFetch 503 auto-retry for real users. The new Phase-5 route guard prevents harness exposure when `C3A_TEST_MODE` is unset, but does NOT prevent the misconfigured-prod case. Add a startup assertion to `_validate_config()` per § 9.7 / P32 framework: if `BUILDEMUP_ENV=prod` and `C3A_TEST_MODE=1`, log ERROR and `sys.exit(1)`. |
| **Origin** | Session 28 critique-walk item #5 (verdict: VALID-BUT-BACKLOG; defense-in-depth fit). |
| **Trigger condition** | Either (a) any future spec-amendment cycle, OR (b) incident where prod traffic hits a test-mode-enabled deploy. |
| **Effort estimate** | ~5 LOC in server.py `_validate_config()` + 1 test that confirms the sys.exit fires for the misconfigured combination. |
| **S8/post-S8 scope** | OUT-of-scope for S8 (spec is LOCKED). Mid-build extension to `_PROD_REQUIRED` framework would be Pattern E. The route guard already provides the primary protection. |

-----

## B-063 — CI: Tier-2 e2e suite mandatory pre-merge

| Field | Value |
|---|---|
| **ID** | B-063 |
| **Description** | E2e tests are tagged `@pytest.mark.e2e` and opt-in via `pytest -m e2e`. The pytest-level opt-in is correct (Tier 2 budget separation per § 4 + P37), but the CI pipeline currently treats Tier 2 as optional. Adding a CI stage that runs Tier 2 as a mandatory pre-merge gate prevents shipping with broken e2e flows. |
| **Origin** | Session 28 critique-walk item #13 (verdict: VALID-BUT-BACKLOG; CI orchestration concern). |
| **Trigger condition** | Setting up production-grade CI/CD for the project (currently auto-deploys on `main` push per master doc § 8.4). |
| **Effort estimate** | CI configuration only; no source changes. ~10-30 lines of YAML or equivalent in the deploy pipeline (Railway / GitHub Actions). |
| **S8/post-S8 scope** | OUT-of-scope (CI infrastructure, not C3a code). |

-----

## B-064 — Static asset hardening: CSP + Cache-Control headers

| Field | Value |
|---|---|
| **ID** | B-064 |
| **Description** | `_serve_static` returns static `/c3a/*` HTML/JS/CSS without Content-Security-Policy or Cache-Control headers. Adding both is sensible defense-in-depth: CSP narrows the script-source surface (mitigates injected-script risk on the email-link landing pages); Cache-Control with sensible TTLs cuts redundant fetches and lets a CDN layer slot in cleanly later. Spec § 5b.3 already mandates `Cache-Control: no-store, no-cache, must-revalidate` for `/check-init` responses; this would extend headers to the static UI surface. |
| **Origin** | Session 28 critique-walk item #14 (verdict: VALID-BUT-BACKLOG). |
| **Trigger condition** | Pre-launch security review, OR observable regression in static-asset load time at scale, OR any CDN integration. |
| **Effort estimate** | ~15 LOC in `_serve_static` + 2-3 tests verifying header presence per content-type. |
| **S8/post-S8 scope** | OUT-of-scope for S8. Real hardening but not specced. |

-----

## B-065 — `metric_failures_total` counter inside the P22 swallow path

| Field | Value |
|---|---|
| **ID** | B-065 |
| **Description** | Spec P22 mandates "best-effort metric emission" — failures in `_emit_handler_metric` are swallowed silently to prevent observability infra from cascading into user-facing failures. This is the right call. But silent swallowing creates a blind-spot risk: an entirely broken metric pipeline would not be visible in operations. Add a process-local counter `metric_failures_total` incremented inside the existing try/except. NOT alerting — that would violate P22. Just a grep-able count for diagnosis when the question "why are no metric lines appearing?" arises. |
| **Origin** | Session 28 critique-walk item #9 (verdict: MISFRAMED for the alerting suggestion; the counter kernel survives as backlog). |
| **Trigger condition** | Operator question "why no metrics?" OR any future observability-pipeline migration. |
| **Effort estimate** | ~5 LOC in `c3a_endpoint.py` `_emit_handler_metric`. |
| **S8/post-S8 scope** | OUT-of-scope for S8 (P22 explicitly chose silent-swallow; modifying mid-build would touch the LOCKED contract). |

-----

## Summary of Session 28 backlog deltas

- **9 new B-NNN entries:** B-057, B-058, B-059, B-060 (audit-report candidates) + B-061, B-062, B-063, B-064, B-065 (Rule-7 critique-walk verdicts).
- **All OUT of S8 scope.** None block S8 ship adjudication.
- **Filed per new Rule 9.2** (always-file backlog directive, codified end of S28; memory line 12).
- **5 critique items** were verdicted ALREADY-DOCUMENTED (#1, #6, #7, #12, #15) — no backlog entries needed; existing spec/code citations cover them.
- **6 critique items** were verdicted MISFRAMED with pushback (#3, #4, #8, #9-alerting-half, #10, #11). Of those, the kernel of #9 (counter-without-alerting) survived as B-065.

The chain holds.

-----

## Addendum — C4 v0.1 critique walk additions (B-066, B-067, B-068)

These three items were surfaced during the Session 28 walk of the external critique of C4 SPEC v0.1 DRAFT (17 items total; 13 patched into v0.2 PROPOSED, 3 deferred to backlog per Rule 9.2 always-file directive, 1 misframed-with-pushback, 1 already-documented).

-----

## B-066 — Polygon plots (L-shaped, irregular) support

| Field | Value |
|---|---|
| **ID** | B-066 |
| **Description** | C4 v1 hardcodes `PlotShape.RECTANGULAR` because Plot dataclass only carries `width_m × depth_m`. Polygon support requires upstream changes (C1 polygon entry UI, Plot dataclass extension to `vertices: list[Point]`) plus C4 shape-detection logic plus C5 L-shape topology. The `shape_metadata: dict` forward-compat hook in C4 v0.2 (per critique #13) anticipates this; today it's empty. |
| **Origin** | C4 SPEC v0.2 PROPOSED § 4.2 + critique walk #13 alignment |
| **Trigger condition** | When C1 grows polygon entry — i.e., a UI for non-rectangular plot vertices. Real Indian residential plots are sometimes L-shaped (~5-10% market share per architect interviews); irregular plots are rarer (~2-3%). Trigger when those segments matter for product reach OR when a specific customer demands it. |
| **Effort estimate** | ~150 LOC: new `shape_detection.py` (compute shape from vertices + bounding box) + L-shape topology in C5 + Plot dataclass extension + C1 UI changes + tests. Probably a 1-2 session build with its own spec cycle. |
| **C4 v0.2 scope verdict** | OUT — v1 is rectangular-only by upstream contract. Forward-compat hook in `shape_metadata` field reserves the extension surface. |

-----

## B-067 — Per-month sun-path declination (vs solstice envelope)

| Field | Value |
|---|---|
| **ID** | B-067 |
| **Description** | C4 v1 computes solar geometry at the two solstices (June 21 + Dec 21), giving the envelope every other day fits inside. v1 uses this for room-placement BIAS in C5/C6 (which side gets afternoon sun), not for shading studies. The critique correctly points out that intermediate-month accuracy degrades — e.g., March/September equinox geometry is mid-envelope. For shading-study features (overhang depth, sunshade dimensioning, photovoltaic siting), per-month declination is needed. |
| **Origin** | C4 SPEC v0.1 DRAFT-Q #3 + v0.2 critique walk item #4 |
| **Trigger condition** | When C5/C6 (or a future shading-study layer) adds features requiring intermediate-month accuracy. Most likely trigger: passive-solar-design feature, sunshade overhang sizing, or PV-panel placement. |
| **Effort estimate** | ~60 LOC: 12-element monthly declination table (closed-form Cooper 1969 evaluated at mid-month days; no astronomy lib needed) + interpolation helper + tests. Self-contained; no upstream/downstream coupling changes. |
| **C4 v0.2 scope verdict** | OUT — solstice envelope is sufficient for v1's room-placement BIAS use case. |

-----

## B-068 — `effective_open_sides` post-setback usable openness

| Field | Value |
|---|---|
| **ID** | B-068 |
| **Description** | C4 v1 emits `NeighbourContext.open_sides` as RAW openness — sides where there's no neighbour wall. This does NOT account for setbacks. A side might be "open" yet too narrow post-setback (e.g., 1.5m setback on a 6m-wide plot leaves 3m effective width — too narrow for a meaningful window). The critique proposes adding `effective_open_sides: list[PlotOrientation]` that reflects post-setback usable sides. v0.2 documents the gap and defers the field — partly because the C4↔C2-setback coupling decision (does C4 take setbacks as input? Or does C5 do the combine?) needs real C5 usage data to make well. |
| **Origin** | C4 SPEC v0.2 critique walk item #8 |
| **Trigger condition** | When C5 ships AND real layout outcomes show that `open_sides` over-estimates facade usability (e.g., C5 places windows on a "open" side that is post-setback unusable). |
| **Effort estimate** | ~20 LOC if added to C4: 1 new field + setback-input plumbing through bridge layer. ~10 LOC if added as a C5 helper that combines C4 output with C2 setbacks. Decision deferred. |
| **C4 v0.2 scope verdict** | OUT — defer until C5 ships and the coupling decision can be made empirically rather than speculatively. v0.2 documentation in § 4.9 makes the limitation explicit so C5 author knows to combine. |

-----

## Updated Session 28 backlog total

12 entries filed in S28 (was 9; +3 from C4 v0.1 critique walk):

- **From S28 audit:** B-057, B-058, B-059, B-060
- **From S8 critique walk:** B-061, B-062, B-063, B-064, B-065
- **From C4 v0.1 critique walk:** B-066, B-067, B-068

All filed per Rule 9.2 (always-file directive).

-----

## Addendum 2 — C4 v0.2 → v0.3 web-research walk additions (B-069, B-070)

These two items were surfaced during the Session 28 web-research pass on C4 v0.2 (the pass Ramalingam caught me skipping per Rule 7's "Web-search to verify external claims before accepting" mandate). Web research uncovered factual errors in v0.2 (NBC 2016 climate zones — see backlog file `buildemup_C4_SPEC_v0_3_PROPOSED.md` § 13 for the corrections); these two items are out-of-scope for v1 but worth tracking.

-----

## B-069 — Composite-zone internal sub-classification (composite-dry vs composite-humid)

| Field | Value |
|---|---|
| **ID** | B-069 |
| **Description** | NBC 2016 Part 8 Section 1 defines a single `COMPOSITE` zone for cities where no single climate type dominates ≥6 months (Delhi is the canonical example). Recent academic literature (Sciencedirect 2023-2025; refining-Indian-climate-zoning papers) has shown this single zone groups climatically diverse cities — Delhi composite leans hot-dry-with-cold-winters, while Lucknow composite leans warm-humid-with-cold-winters. Refined classifications propose splitting into "composite-dry" and "composite-humid" sub-zones. |
| **Origin** | C4 SPEC v0.3 PROPOSED § 4.5 + web-research pass on v0.2 |
| **Trigger condition** | When downstream layout outcomes (C5+) systematically diverge between Delhi-style and Lucknow-style composite cities AND user feedback or thermal-comfort metrics show v1's single-COMPOSITE classification is the cause. |
| **Effort estimate** | ~30 LOC: enum extension to add `COMPOSITE_DRY` / `COMPOSITE_HUMID` + per-city sub-tag in `CITY_GEOGRAPHY` + updates to `BASELINE_ROOM_ORIENTATION_GUIDELINES` + downstream consumer updates in C5/C6. Plus a spec amendment cycle. |
| **C4 v0.3 scope verdict** | OUT — NBC 2016 verbatim is the right anchor for v1 (single COMPOSITE). Refining mid-build = Pattern E. Wait for ship-data evidence. |

-----

## B-070 — IMD wind-rose data per city (vs current single-direction citation)

| Field | Value |
|---|---|
| **ID** | B-070 |
| **Description** | C4 v0.3 § 4.6 emits a 4-field `WindContext` (primary / secondary / monsoon / speed) per city, sourced from IMD climatology summaries cited per-city in code comments. This is a substantial improvement over v0.1's single-direction model (per critique #5), but full IMD wind-rose data (8-direction frequency tables per city per season) would let C5 cross-ventilation logic optimize window-pair angles more accurately than 4 cardinal labels can. |
| **Origin** | C4 SPEC v0.3 PROPOSED § 4.6 + v0.3 self-critique pass |
| **Trigger condition** | When ventilation-correctness incidents surface in production (e.g., C5 places windows on a side that turns out to receive minimal cross-ventilation in measured data) AND the 4-field model is the demonstrable cause. |
| **Effort estimate** | ~20 LOC: 8-direction wind-rose tables per city + interpolation helper in WindContext + tests. Closed-form once data is in hand. |
| **C4 v0.3 scope verdict** | OUT — 4-field model is sufficient for v1 cross-ventilation positioning. Wind-rose refinement is a precision tweak, not a correctness fix. |

-----

## Updated Session 28 backlog total

14 entries filed in S28 (was 12; +2 from C4 v0.2 → v0.3 web-research pass):

- **From S28 audit:** B-057, B-058, B-059, B-060
- **From S8 critique walk:** B-061, B-062, B-063, B-064, B-065
- **From C4 v0.1 critique walk:** B-066, B-067, B-068
- **From C4 v0.2 → v0.3 web-research walk:** B-069, B-070

All filed per Rule 9.2 (always-file directive).

-----

## Addendum 3 — C4 v0.3 critique walk additions (B-071)

The C4 v0.3 PROPOSED received its second external critique round (17 items). 12 valid patches applied (proposed for v0.4), 2 misframed with pushback, 1 already-documented, 1 valid-but-backlog (filed below per Rule 9.2). Additionally, Claude's own self-critique pass surfaced 5 items, all valid patches for v0.4.

-----

## B-071 — Latitude-band climate fallback for cities outside CITY_GEOGRAPHY

| Field | Value |
|---|---|
| **ID** | B-071 |
| **Description** | C4 v1 raises ValueError when `plot.city` is not in `CITY_GEOGRAPHY`. The external critic correctly identifies that this prevents the platform from serving any city outside the explicit supported-list (currently 10 cities). A latitude-band fallback (e.g., `8-15°N → likely WARM_HUMID`, `15-23°N → COMPOSITE`, `23+°N → COMPOSITE/COLD`) plus a "regional cluster" mapping (tier-2 cities reuse a known city profile by proximity) would let the platform handle unknown cities with degraded confidence rather than hard-fail. v1 stance: hard-fail with clear error is better than guess-and-be-wrong. |
| **Origin** | C4 v0.3 critique #3 (2nd external round) — same family as v0.1 critique #3. Filed at v0.3→v0.4 cycle since the v0.3 spec § 8 listed it as "Other candidates (not filed)" — Rule 9.2 always-file directive means it should be a real B-NNN. |
| **Trigger condition** | Product expansion to tier-2/tier-3 cities (e.g., Coimbatore, Vadodara, Indore) without per-city KB entries. |
| **Effort estimate** | ~30 LOC fallback resolver + tests. Plus a `confidence` field on `PlotAnalysis` itself indicating "city was looked up directly" vs "fell back to nearest cluster." |
| **C4 scope verdict** | OUT — v1 supported-cities list is intentionally explicit. Hard-fail with clear "add city to all 3 KBs together" error message is the right v1 behavior. Fallback is post-launch when the cost of "city not supported" exceeds the cost of "wrong climate guess." |

-----

## Updated Session 28 backlog total

13 entries filed in S28 (was 12; +1 from C4 v0.3 critique walk):

- **From S28 audit:** B-057, B-058, B-059, B-060
- **From S8 critique walk:** B-061, B-062, B-063, B-064, B-065
- **From C4 v0.1 critique walk:** B-066, B-067, B-068
- **From C4 v0.2 → v0.3 web-research walk:** B-069, B-070
- **From C4 v0.3 → v0.4 critique walk:** **B-071**

All filed per Rule 9.2.

-----

## Addendum 4 — C4 v0.4 Path B applied (B-072)

Ramalingam selected Path B for v0.3→v0.4: produce a single v0.4 PROPOSED with all VALID-PATCH items applied, all 4 hygiene items applied, all 5 self-critique items applied, road-width thresholds reverted to universal, and C7 retrofit filed as backlog. Done.

-----

## B-072 — C7 retrofit to consume `PlotAnalysis.soil_estimate`

| Field | Value |
|---|---|
| **ID** | B-072 |
| **Description** | C4 SPEC § 1 declares `PlotAnalysis` the "preferred single source of truth" for plot-derived properties, including soil. C7 (already shipped v0.7.3) currently re-derives soil from `kb/soil_foundation_rules.SOIL_PROFILES` directly rather than consuming `PlotAnalysis.soil_estimate`. This is intentional pre-C4 design, NOT a regression — but it's a single-source-of-truth violation that should be cleaned up once the layout pipeline (C5–C16) is stable enough that retrofitting C7 doesn't risk breaking Era 1 cost-engine code paths. |
| **Origin** | C4 SPEC § 1 deferred since v0.1; explicit Path B confirmation v0.4. Companion to External critique #1 (v0.1 round) which surfaced the same concern. |
| **Trigger condition** | When the layout pipeline (C5 through C16) is shipped and stable. Specifically: when C5 consumes `PlotAnalysis.soil_estimate` and produces topology decisions that feed C7; at that point C7 should consume the same `PlotAnalysis.soil_estimate` rather than re-derive (Pattern E avoidance — touching C7 mid-build = scope creep). |
| **Effort estimate** | ~30 LOC in C7 + retrofit tests. Add `c4_compatibility.py` shim if needed for backward compat with any C7 consumers that still pass raw `Plot`. |
| **C4 v0.4 scope verdict** | OUT — C7 is shipped Era 1 code; retrofitting mid-build is Pattern E. The "preferred single source of truth" wording in § 1 explicitly calls this out as deferred. |

-----

## Updated Session 28 backlog total

14 entries filed in S28 (was 13; +1 from C4 v0.3 → v0.4 Path B):

- **From S28 audit:** B-057, B-058, B-059, B-060
- **From S8 critique walk:** B-061, B-062, B-063, B-064, B-065
- **From C4 v0.1 critique walk:** B-066, B-067, B-068
- **From C4 v0.2 → v0.3 web-research walk:** B-069, B-070
- **From C4 v0.3 → v0.4 critique walk:** B-071
- **From C4 v0.4 Path B application:** **B-072**

All filed per Rule 9.2.
