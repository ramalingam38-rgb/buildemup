# Master Doc — Session 26 Delta (v3.1 → v3.2-FINAL)

This document **supersedes** the earlier `MASTER_DOC_v3_1_TO_v3_2_DELTA.md`
draft (which only captured up to S8 SPEC v0.1 DRAFT). The full Session 26
arc is far larger than that draft anticipated:

- S7b code build complete (Phases 5–9)
- S7b external critique processed (1 patch + 4 backlog entries)
- **S8 SPEC evolved through 6 critique rounds: v0.1 → v0.1.1 → v0.2 →
  v0.3 → v1.0 → v1.1 → v1.2 LOCKED**
- 35 patches applied + 13 PUSHBACKS preserved + 2 new backlog items
- 5 memory-recorded rules formalized

Apply each zone update in order. This delta REPLACES the prior v3.1→v3.2
delta — discard the earlier file.

**Chain status as of this delta:** v2.9 (last full materialization)
+ v2.9→v3.0 delta (Session 24) + v3.0→v3.1 delta (Session 25) +
v3.1→v3.2-FINAL delta (this session) = **3 deltas accumulated**.
Threshold for consolidation is 3–4 OR before a major ship. **C3a ships
after S8 code build (Sessions 27–30 path).** Recommend a full v4.0
rewrite at C3a SHIP — natural consolidation point.

---

## Zone 1 — Header / version

**Change the version line from:**
```
Version: v3.1 — 1 May 2026 (Session 25 — C3a S7b SPEC v1.0 LOCKED ...)
```

**To:**
```
Version: v3.2 — 2 May 2026 (Session 26 — C3a S7b code build COMPLETE
across all 9 phases + critique-round patch shipped (fallback_error
truncation per external code review); 286/286 c3a tests; 1182/1182
project-wide; S8 SPEC v0.1 → v1.2 LOCKED across 6 critique rounds with
35 patches applied + 13 PUSHBACKS preserved + 2 new backlog items
B-054 + B-055; 5 memory-recorded rules formalized: critique-handling,
LOCK-authority, backlog-visibility-in-spec; ready for Session 27 to
begin S8 code build Phase 1)
```

---

## Zone 2 — Append Session 26 entry to Part 4 session log

Append the following as **§ 4.27** (Session 25 was § 4.26):

```markdown
### § 4.27 Session 26 — 2 May 2026 — C3a S7b Code Complete + S8 SPEC LOCKED

**Three-part session, split across natural phases:**

#### Part 1 — S7b code build Phases 5–9
- Phase 5: `buildemup/api/admin_endpoint.py` NEW (413 LOC) — handle_scheduler_tick
  + handle_scheduler_reset with hmac auth.
- Phase 6: `buildemup/api/c3a_endpoint.py` MODIFIED (1500→1914 LOC) —
  § 5.4 helpers, § 5.2 instrumentation, § 6.2 helpers, 5 handlers
  renamed `_inner` with public wrappers; updated hook signatures.
- Phase 7: `buildemup/api/health_endpoint.py` NEW (283 LOC) — handle_health()
  with 5 checks.
- Phase 8: `buildemup/api/server.py` REPLACED (224→411 LOC) — _validate_config
  per § 9.7, 3 new routes, _unpack_handler_result helper.
- Phase 9: 7 new test files + 1 smoke (29 c3a + 6 smoke).
- Result: 254/254 c3a tests → 283/283 c3a, 1150/1150 → 1179/1179
  project-wide.

#### Part 2 — S7b external critique processing
- 6-item code-level analysis triaged item-by-item with web verification
  (AWS Builders' Library, Microsoft Azure, Railway docs, sqlite.org,
  Datadog/Sonar). Results:
  - 1 PATCH shipped: truncate fallback_error to FALLBACK_ERROR_MAX_LEN=256
    + 3 tests (283→286 c3a; 1179→1182 project-wide).
  - 4 BACKLOG entries: B-050 SQLite FK enforcement, B-051 env-var name
    drift, B-052 scheduler index validation at scale, B-053 log shipping
    with audit retention.
  - 4 MISFRAMED with documented reasoning.
- Consolidated drop-in zip bundle delivered: `buildemup_c3a_s7b_consolidated.zip`
  (83KB, 25 files).

#### Part 3 — S8 SPEC built and LOCKED across 6 critique rounds
- **v0.1 DRAFT** — Initial draft with Q1 BLOCKING question (UI surfaces vs
  API-level only). v0.1 default reading-(b) minimal with reading-(a)
  flagged inline.
- **v0.1.1 DRAFT** — Q1 RESOLVED by Ramalingam: reading (a) MAXIMAL
  scope. Reading (a) inlined as first-class content. ~3 weeks of work;
  C3a SHIP slips one session.
- **v0.2 DRAFT (Round 1 — 19 patches: 11 self-critique + 8 external)** —
  CRITICAL: trace_id moved from sessionStorage to URL embedding (Finding
  1, web-verified MDN); c3a_email_hook URL-construction added to S8
  carve-out (Finding 2); contract layer `_contract.py` module (External
  Item 1); GET `/api/extreme-case/status` endpoint added (External Item 2).
  Categorized error model RETRYABLE/USER_FIXABLE/TERMINAL added;
  concurrency tests added; axe-core a11y tests added; new invariant P42
  (UI–API contract centralized).
- **v0.3 DRAFT (Round 2 — 11 patches: 8 PATCH + 3 PUSHBACK with docs)** —
  trace_id decoupled into client/server per new P43 invariant; POST-on-load
  NEUTRALIZED via new GET `/api/extreme-case/check-init` wrapper;
  /status threat model documented; enumeration claim PUSHED-BACK
  (122-bit UUID entropy verified infeasible). 2-3 raw cross-check tests
  guard against `_contract.py` drift; concurrency tests strengthened to
  50× looped randomized; /status read-consistency PUSHED-BACK on
  technical claim (verified SQLite WAL = snapshot isolation per
  sqlite.org); error categorization API-change PUSHED-BACK; mapping
  table added. a11y file renamed `test_c3a_a11y_auto.py` +
  `MANUAL_A11Y_CHECKLIST.md`; § 1.3 updated with Deque's verified 57%
  figure; `BUILDEMUP_PUBLIC_URL` added to `_validate_config`; test
  budget hygiene rule § 4.0.1; flow controller defined now (handlePageFlow
  ~12 LOC).
- **v1.0 (Round 3 — 6 patches + 1 backlog)** — Round 3 spot-check
  produced 7 findings (3 IMPORTANT + 4 NICE):
  - R3.1: P43 trace_id surface mapping pinned per surface
  - R3.2: /check-init request_id derivation pinned
    (`"c3a-init-" + sha256(brief_token)[:16]`) for refresh-safety
  - R3.3: Looped concurrency tests now seeded for P36 determinism
  - R3.4: Flow controller dispatches TERMINAL via handleTerminalRedirect
  - R3.6: "Do not forward" email warning relabeled UX hint, NOT security
  - R3.7: Referrer meta tag updated to "no-referrer"
  - R3.5 → BACKLOG B-054: test-justification linting
- **v1.0 → v1.1 (First post-proposed-LOCK adjudication — 2 PATCH +
  5 PUSHBACK + 1 backlog B-055)** —
  - PL1: concurrency loop 50→25 (web-verified diminishing returns from
    Springer 2023)
  - PL2: Tier 1 budget 25s soft warning becomes 3-consecutive-runs CI
    trigger
  - 5 PUSHBACKS: trace_id duality friction (web-verified W3C/OpenTelemetry/
    Datadog/AWS X-Ray use multiple identifiers by design); redirect
    chains (already-documented Q9 design); /status hidden coupling
    (added to fix worse problem); email link security (already in
    B-042); flow controller SPOF (client-side bugs are loud, not
    silent)
  - B-055 NEW: Tune concurrency iteration count post-launch
- **v1.1 PROPOSED → v1.1 LOCKED was bypassed; went straight to v1.2** —
  Critique landed during adjudication window so patches still applied.
  Second post-proposed-LOCK: 3 PATCH (Tier 1 tight-margin acknowledgment;
  surface complexity acknowledgment; /check-init REST-semantics +
  Cache-Control: no-store header — real production gap closed).
- **v1.2 PROPOSED (Third post-proposed-LOCK adjudication — 4 PATCH)** —
  - P-1: test_c3a_observability.py promoted from Tier-1 to Tier-2 e2e;
    Tier-1 target ~27s with 3s buffer; Tier-2 cap 60→75s
  - P-2: Bot-UA filter on /check-init endpoint (§ 5b NEW with ~20-pattern
    UA list; web-verified facebookexternalhit, Slackbot,
    BlueskyPreviewBot, etc. don't all honor robots.txt)
  - P-3: Deterministic worst-case race tests (3 tests barrier-only,
    no jitter)
  - P-4: Direct flow-controller behavior tests in new
    `tests/e2e/test_handle_page_flow.py`
- **v1.2 LOCKED by Ramalingam, 2 May 2026, Session 26.**

#### Part 4 — Memory rules formalized (5 total)
1. (Pre-existing) Three obligations: spec-first, honest context budget,
   master doc + handoff at every session end.
2. (Pre-existing) Project numbering — always Track 3 (canonical
   17-component v3).
3. (Refined Session 26) Critique-handling + own-analysis rule:
   item-by-item, mark each VALID/MISFRAMED/ALREADY-DOCUMENTED/
   SPEC-AMENDMENT/BACKLOG, web-verify external claims, push back on
   wrong items.
4. (NEW Session 26) **LOCK authority rule:** ONLY Ramalingam declares
   LOCK. Claude must never auto-LOCK. Critiques in adjudication
   window remain eligible for PATCH (not just BACKLOG) until
   Ramalingam locks.
5. (NEW Session 26) **Backlog-visibility-in-spec rule:** every backlog
   item referenced or created during a spec's critique cycle MUST be
   enumerated in the LOCKED spec doc itself (§ 12 or equivalent).
   Spec is self-contained; reader doesn't need a separate backlog
   file.

#### Tests at end of session
- 286/286 c3a tests passing
- 1182/1182 project-wide
- No new code shipped against S8 SPEC; that's Session 27's task

#### Status
- 3 of 17 components shipped (C1, C2, C7)
- C3a: S7b shipped + S8 SPEC LOCKED at v1.2; **code build begins
  Session 27**
- Path: Session 27 (Phases 1-3), Session 28 (Phase 4), Session 29
  (Phase 5-6), Session 30 (Phase 7 + C3a SHIPS = 4 of 17)
```

---

## Zone 3 — Update Part 5 component status table

Update C3a's row in the component table:

**From:**
```
| C3a | C3a Extreme Case Gate | S7a SHIPPED + S7b SPEC v1.0 LOCKED |
```

**To:**
```
| C3a | C3a Extreme Case Gate | S7b SHIPPED + S8 SPEC v1.2 LOCKED;
       code build begins Session 27 |
```

---

## Zone 4 — Update Part 6 backlog summary

Add to Part 6 backlog summary (preserving existing items):

```markdown
**New as of Session 26:**

- **B-050** — SQLite FK enforcement via `PRAGMA foreign_keys=ON`.
  Trigger: stuck-row accumulation incident OR future component
  depending on CASCADE. Effort: 30 min.

- **B-051** — Reconcile env-var name drift `BUILDEMUP_DATABASE_PATH`
  vs `BUILDEMUP_GATE_DB_PATH`. Trigger: pre-prod deploy. Effort:
  30 min.

- **B-052** — Validate scheduler-state index selectivity at production
  scale. Trigger: queue depth >5000 rows OR observed tick latency
  degradation. Effort: 0.5 day.

- **B-053** — Log shipping with audit-log retention to managed log
  platform. Trigger: first need to investigate admin reset >N days
  old OR compliance requirement. Effort: 1-2 days.

- **B-054** — Automate test-justification linting (CI check that
  fails if a test class lacks invariant-justification docstring per
  § 4.0.1 hygiene rule). Trigger: hygiene rule erodes post-S8-ship.
  Effort: 2 days for pytest-collect plugin.

- **B-055** — Tune concurrency test iteration count post-launch
  using actual CI runtime metrics. Trigger: Tier 1 budget routinely
  >27s OR observed race bug slips past 25 iterations. Effort: 1h.

**Backlog state at Session 26 close:** 9 items deferred, all with
documented triggers. None block C3a SHIP. Per the new
backlog-visibility-in-spec rule, S8 SPEC § 12 enumerates all 9
items inside the spec doc itself (the canonical source); this Part 6
entry is a project-wide summary that mirrors it.
```

---

## Zone 5 — Update Part 11 invariants list

Append the 8 new C3a invariants P36–P43 to Part 11:

```markdown
**P36** — C3a validation tests are deterministic (target <0.5%
flake rate, web-verified industry norm).

**P37** — C3a validation tests run in tiered time budgets
(Tier 1: 30s hard cap, ~27s steady-state target with 3s buffer
post-v1.2 P-1; Tier 2 e2e: 75s cap, was 60s pre-v1.2).

**P38** — C3a validation tests are HERMETIC (no network, no real
Resend, no specific clock value, no env-vars beyond test setup).

**P39** — C3a validation tests document the contract (each test
docstring justifies which P-invariant or § section it exercises;
§ 4.0.1 hygiene rule enforced by 3-consecutive-runs CI trigger).

**P40** — C3a UI tests exercise UI through a real browser engine
(Playwright + chromium; no DOM simulation libraries).

**P41** — C3a UI tests use semantic selectors (role-based queries,
not class names or XPath).

**P42** — C3a UI–API contract is centralized in `_contract.py`
with 2-3 raw cross-check tests in `test_c3a_state_machine.py`
guarding against `_contract.py` drift.

**P43** — C3a trace_id is decoupled: server-generated `server_trace_id`
is canonical (used for log correlation + metric lines + X-Trace-Id
header); client-supplied `client_trace_id` is correlation hint
(used in response body + UI display + email link). Structured logs
include both fields. Web-verified industry standard (W3C TraceContext,
OpenTelemetry, Datadog, AWS X-Ray all use multiple identifiers by
design).
```

---

## Zone 6 — Update Part 13 architecture / methodology section

Append a new subsection **§ 13.5 Critique-cycle protocol** (codifies
what was practiced and refined in Session 26):

```markdown
### § 13.5 Critique-cycle protocol (formalized Session 26)

The spec-first discipline (D-066) requires draft → critique → lock
→ code. Session 26's experience with S8 SPEC produced 6 critique
rounds and clarified the protocol:

**Critique-handling rule (memory #3):** when external analysis
arrives OR Claude self-critiques, walk item-by-item with detailed
reasoning. Mark each finding as one of:
- VALID (apply patch)
- MISFRAMED (push back with reasoning, preserve in changelog)
- ALREADY-DOCUMENTED (no action; cite the existing § that handles it)
- SPEC-AMENDMENT (out of current spec scope; opens new amendment cycle)
- BACKLOG (defer to backlog with trigger condition)

Web-search to verify external/library/convention claims before
accepting them.

**LOCK authority rule (memory #4):** ONLY Ramalingam declares LOCK.
Claude proposes patches; Ramalingam adjudicates. Spec versions go
through `proposed-vN-pending-adjudication` state before LOCK.
Critiques arriving in the adjudication window remain eligible for
PATCH (not just BACKLOG) until Ramalingam locks.

**Backlog-visibility-in-spec rule (memory #5):** every backlog item
referenced or created during a spec's critique cycle MUST be
enumerated in the LOCKED spec doc itself. Spec is self-contained;
reader doesn't need a separate backlog file. Format per entry:
ID, description, origin, trigger, scope-or-not, effort estimate.

**Round saturation:** S8 produced patches across all 6 rounds
(R1: 19, R2: 11, R3: 6, post-LOCK 1: 2, post-LOCK 2: 3, post-LOCK 3:
4). Diminishing-returns shape is real (web-verified Springer 2023
sublinear flaky-test detection paper applies analogously). At some
point further rounds enter diminishing returns; Ramalingam decides
when to LOCK.
```

---

## Zone 7 — Update Part 14 NEXT_CLAUDE_HANDOFF reference

Update Part 14 to point at the new handoff file:

```markdown
**Current handoff doc:** `NEXT_CLAUDE_HANDOFF.md` (Session 27 — S8
code build start). Path: see project root.

Session 27's first 3 actions (in order):
1. Read S8 SPEC v1.2 LOCKED + this delta + the handoff
2. Apply this delta to master doc to materialize v3.2
3. Append B-054 + B-055 (and B-050..B-053 final form) to canonical
   backlog file location, mirroring spec § 12

THEN begin S8 code build Phase 1 (server.py + new endpoints
foundation per § 1.2 (ii) carve-outs).
```

---

## Apply order

Apply zones 1 → 7 in order to materialize v3.2 of the master doc
on top of v3.1. Total changes are surgical — no full rewrites.

After application, version line should read v3.2 — 2 May 2026, and
all 8 new P-invariants P36–P43 should be in Part 11.

---

## End of v3.1 → v3.2-FINAL delta
