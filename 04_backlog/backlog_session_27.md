# Backlog — Session 27 Delta

**Session:** 27
**Date:** 2 May 2026
**Status:** Both flags adjudicated end of Session 27. **One new B-NNN backlog item created (B-056)** tracking the formal § 1.2 (ii) carve-out language extension that Flag A's approval requires at the next spec amendment cycle.

This file replaces the prior Session 27 version (which had Flags A/B as "awaiting adjudication" — that is now resolved).

-----

## Adjudicated decisions (closed end of Session 27)

### FLAG-A — gate_state_storage additive read accessor — **ADJUDICATED OPTION A APPROVED**

| Field | Value |
|---|---|
| **ID** | FLAG-A (S27) |
| **Status** | **CLOSED — Option A approved by Ramalingam end of Session 27** |
| **Description** | Session 27 added `load_status_row(token)` to `GateStateStorage` even though § 1.2 (ii) FORBIDDEN list includes that file. Interpretation: FORBIDDEN intent is "no behavioural change to existing methods"; pure-additive read accessor preserves that. The spec § 5a.4 implementation outline literally needs `row.is_terminal` + `row.saved_at` access, neither of which the existing public API exposes. |
| **Origin** | Session 27, Phase 1 build |
| **Adjudication** | Option A — accessor stays. Approved as Rule-4 spec-amendment patch. Formal § 1.2 (ii) language extension at next spec-amendment cycle is tracked as **B-056** (see below). |
| **Effort** | Zero further code change. B-056 will handle spec text extension at next amendment cycle. |
| **Reasoning recorded** | (a) Spec author wrote `row.is_terminal` + `row.saved_at` knowing FORBIDDEN was in place — additive interpretation was the author's intent. (b) FORBIDDEN's spirit is behavioural-not-structural; pure-read accessor preserves the lock's purpose. (c) Direct-SQL alternative would duplicate schema knowledge across two modules, paying a real maintenance cost to honour a literal reading the spec author themselves did not honour. |

### FLAG-B — P43 scoping — **ADJUDICATED OPTION A CONFIRMED**

| Field | Value |
|---|---|
| **ID** | FLAG-B (S27) |
| **Status** | **CLOSED — Option A confirmed by Ramalingam end of Session 27** |
| **Description** | Session 27 applied P43 (server/client trace decoupling) only to `handle_cba_fallback_continue` since the other 4 handlers don't accept inbound headers and therefore have no client_trace_id input to capture. § 2.8's "every handler" wording is logically respected (all handlers mint server_trace_id; client_trace_id is null where there's no header source). |
| **Origin** | Session 27, Phase 2 build |
| **Adjudication** | Option A — scoping correct. No other handlers modified. |
| **Effort** | Zero further code change. |
| **Reasoning recorded** | The other 4 handlers already mint fresh trace_id locally (since S7b). P43 isn't asking for new behaviour from them — it's describing existing behaviour and adding client_trace_id capture for handlers that can capture one. Only `handle_cba_fallback_continue` accepts headers today. Modifying the other 4 to accept unused `headers` parameters would force a § 1.2 (ii) handler-logic carve-out extension for zero observable behaviour delta. |

-----

## NEW backlog item (per Rule 9.1)

### B-056 — Formalise § 1.2 (ii) additive-read-accessor carve-out language at next S8 spec-amendment cycle

| Field | Value |
|---|---|
| **ID** | B-056 |
| **Description** | Extend § 1.2 (ii) FORBIDDEN-list language to formally permit purely-additive read accessors when a downstream § 5a/§ 5b implementation outline references fields not exposed by existing public API. Such additions must (a) touch no existing method, (b) introduce no behavioural change, (c) be flagged in the session's AUDIT report. Codifies the Flag-A approval into spec text so future sessions don't re-litigate. |
| **Origin** | Session 27, Flag A adjudication (Ramalingam approved Option A; this entry tracks the deferred spec-text extension). |
| **Trigger condition** | Any future S8 spec-amendment cycle opens (e.g., post-launch critique round, S9 boundary, or unrelated correction batch). |
| **S8-scope** | OUT-of-scope (spec-meta; does not block ship). The current `load_status_row()` code is already approved-and-merged via Flag-A adjudication; B-056 only formalises the spec text. |
| **Effort estimate** | ~10 minutes during next amendment cycle: edit § 1.2 (ii), add the carve-out paragraph, lock the new spec version per Rule 8. No code change. |
| **Suggested wording (for reference at amendment time)** | "No modification to gate_state_storage.py or scheduler_state_storage.py *except purely-additive read accessors when a downstream § 5a/§ 5b implementation outline references fields not exposed by existing public API.* Such additions must (a) touch no existing method, (b) introduce no behavioural change, (c) be flagged in the session's AUDIT report." (Ramalingam adjusts wording at amendment time.) |

-----

## Phase 5–7 deferred work (per Ramalingam's mid-session directive to stop at Phase 4)

These are not B-NNN backlog items because they're **in-spec scheduled work**, not deferred enhancements. They go to Session 28 directly.

### Phase 5 remainder — corrected accounting (Session 28 retro-audit)

The entry bundle ALREADY contained spec-referencing implementations for case/checklist/done/aborted HTML and JS, plus _test_harness.html and _shared.{css,js}. Session 27 did NOT create them. Phase 5 work for Session 28 is therefore:

- Audit existing Phase 5 files against spec § 5.2–5.4 per `SESSION_28_CORRECTIVE_INSTRUCTIONS.md § 3`
- 5 static GET routes wired into `server.py` (the only Phase 5 work correctly deferred from Phase 1 per Pattern B)
- Per-page CSS files (`case.css`, `checklist.css`, `done.css`, `aborted.css`) — not present in entry bundle; add only if audit determines they're needed

### Phase 6 — corrected accounting (Session 28 retro-audit)

The entry bundle ALREADY contained `tests/e2e/` with conftest, playwright config, 7 e2e test files, MANUAL_A11Y_CHECKLIST.md. Session 28 work is:

- Audit existing Phase 6 files against spec § 4.7 + § 4.11 per `SESSION_28_CORRECTIVE_INSTRUCTIONS.md § 3`
- Add gap-filling tests only after audit identifies real gaps
- Run `playwright install chromium` first; if it fails, write any new tests to spec without execution

### Phase 7

- Update `buildemup/DEPLOY.md` per § 9.3 (new C3a UI URLs, BUILDEMUP_PUBLIC_URL, 2 new endpoints)
- Run full project test suite (target ~1260+ tests)
- Run `smoke_c3a_deploy.py` if Railway preview available
- Present "ready to ship"; **DO NOT declare ship** — Ramalingam's call per Rule 8

-----

## Pre-existing backlog items still relevant to S8

(Listed for visibility per Rule 9.1 "pre-existing items the spec depends on must be enumerated".)

| ID | Description | Trigger | S8-scope |
|---|---|---|---|
| B-040 | Postgres migration | Scale need beyond SQLite single-file | OUT (dev acceptable) |
| B-042 | Auth + rate-limit + view-tokens | Production-grade hardening for /status, /check-init beyond UA spoofing + email forwarding protection | OUT (acknowledged in § 5a.5; UX hint substitutes for now) |
| B-049 | (per spec § 12) | (per spec) | OUT |
| B-050 | FK enforcement | Schema correctness review | OUT |
| B-051 | Env-var rename | Naming consistency pass | OUT |
| B-052 | Scheduler index | Query performance tuning | OUT |
| B-053 | Log shipping | Observability productionization | OUT |
| B-054 | Test-justification linting (auto-pytest collect plugin) | Manual § 4.0.1 enforcement becomes burdensome | OUT |
| B-055 | Concurrency tuning post-launch | CI metrics show race slips after launch | OUT |
| **B-056** | **Formalise § 1.2 (ii) additive-read-accessor carve-out language** | **Next S8 spec-amendment cycle** | **OUT (spec-meta)** |

None block Phase 5–7 work. None block Ramalingam's S8 ship adjudication.

-----

## Summary of Session 27 backlog deltas

- 1 new B-NNN entry: **B-056** (Flag-A approval needs formal spec text)
- 2 flags closed via Ramalingam adjudication: **FLAG-A** (Option A approved), **FLAG-B** (Option A confirmed)
- 0 entries deleted or downgraded

The chain holds.
