# S8 SHIP DECLARATION — Session 28

**Adjudication received:** end of Session 28, 2 May 2026
**Authority:** Ramalingam (per Rule 8 — LOCK + SHIP authority belongs to Ramalingam alone)
**Verbatim:** "Finish the s8 ship and the hand off look alright you can proceed"

---

## What is shipped

**S8 SPEC v1.2 LOCKED** — full implementation, Phases 1-7 complete:

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation endpoints (status, check-init, gate_state_storage extension) | ✅ delivered S27 |
| 2 | P43 trace decoupling (handle_cba_fallback_continue) | ✅ delivered S27 |
| 3 | Email hook URL + UX hint | ✅ delivered S27 |
| 4 | Validation suite (134 tests across 11 files) | ✅ delivered S27 |
| 5 | UI surfaces enablement: server.py route guard + meta-tag injection + 9 new tests | ✅ delivered S28 |
| 6 | E2e fixture wiring (C3A_TEST_MODE for live_server_e2e) | ✅ delivered S28 |
| 7 | DEPLOY.md route-guard documentation + smoke check | ✅ delivered S28 |

## SHIP verification (snapshot at SHIP moment)

- **Full project test suite:** 1349 passed, 1 skipped (pre-existing axe-core CDN issue, documented S27), 1415 warnings, 52 subtests passed in 65.43s
- **Validation tier 1 isolated:** 143 passed in 28.23s (under 30s cap, 1.77s headroom)
- **E2e tier 2 isolated:** 24 passed, 1 skipped in 16.72s (well under 75s cap)
- **Net new tests added in S28:** +9 (test_c3a_static_serving.py)
- **Regressions introduced:** zero

## Adjudications closed at SHIP

Both flags from Session 27 are CLOSED — no further code change required:

1. **Flag A** (gate_state_storage.load_status_row additive accessor):
   Option A APPROVED. Code stays as written. **B-056** tracks formal § 1.2 (ii) carve-out language extension at next spec-amendment cycle.

2. **Flag B** (P43 scoping to handle_cba_fallback_continue only):
   Option A CONFIRMED. Other 4 handlers stay unmodified.

## Backlog filed during S8 build (post-LOCK)

9 items filed across S28: B-057 to B-065. None block ship.

- B-057 — case.html visible trace_id on success render (cosmetic)
- B-058 — full-walk e2e tests (case→resolve→done with seeded chain)
- B-059 — done.js PER_CASE_LIMIT_REACHED specific message
- B-060 — tests/e2e/__init__.py docstring "7 files"→"8 files"
- B-061 — SQLite 503 adaptive backoff with jitter + lock-frequency metric (refines B-055)
- B-062 — Startup cross-check: prod_env + C3A_TEST_MODE=1 → sys.exit(1) per § 9.7/P32
- B-063 — CI tier-2 mandatory pre-merge gate
- B-064 — Static asset CSP + Cache-Control headers
- B-065 — metric_failures_total counter inside P22 swallow path (NOT alerting)

## Production deployment status

S8 code is in the working tree at `06_upstream_codebase/buildemup/`. Deployable:
- via `03_code_chronological/S8_phase1_4/buildemup_c3a_s8_phase_1_4_consolidated.zip` (S27 deliverable, Phases 1-4)
- via `03_code_chronological/S8_phase5_7/buildemup_c3a_s8_phase_5_7_consolidated.zip` (S28 deliverable, Phases 5-7)
- OR drop-in by syncing the entire `06_upstream_codebase/buildemup/` tree to the target repo

Smoke check after Railway deploy is documented in `buildemup/DEPLOY.md` § "Smoke check after deploy" — 4 curls covering both new endpoints + static UI + harness gate verification.

## Lifecycle

- v0.1 DRAFT (S22) → v0.2 / v0.3 DRAFT (S23-S25)
- v1.0 PROPOSED (S26 round 1) → SUPERSEDED
- v1.1 PROPOSED (S26 round 2) → SUPERSEDED
- v1.2 PROPOSED (S26 round 3) → SUPERSEDED
- **v1.2 LOCKED** (S27 LOCK adjudication)
- **v1.2 SHIPPED** (S28 SHIP adjudication — this declaration)

S8 is closed. No further C3a work in this build cycle. C3b is deferred until layout pipeline (C4-C16) exists per master doc § 8.3.

## Cross-references

- Spec: `02_specs_chronological/29_S8_SPEC_v1_2_LOCKED.md` (kept LOCKED-named per project convention; SHIP is recorded here, not by renaming spec)
- Code review (full): `03_code_chronological/SESSION_28_S8_FULL_FOR_REVIEW.py` (8649 lines, 42 files)
- Deployment: `buildemup/DEPLOY.md`
- Three-check this session: `05_integrity_check/{GAP,AUDIT,INTEGRITY}_CHECK_SESSION_28_BUILD.md`

---

**S8 v1.2 SHIPPED.**
