# BuildemUp† — v2 Backlog — Session 26 Critique-Round Delta

**Status:** appended after `buildemup_v2_backlog_v0_7_2.md`. Captures
new items surfaced by the external code-level analysis on S7b
(Session 26). Renumbered as B-050 → B-053 to follow the existing S7b
sequence (B-040 through B-049 already taken by spec-tracked items).

**Rule:** every item below was triaged item-by-item against the spec
and against external sources (SQLite docs, AWS Builders' Library,
Microsoft Azure architecture guidance, Railway docs, Datadog/Sonar
audit guidance). The verdicts are documented in the corresponding
session transcript (S26 critique re-analysis). Items the critique
proposed but that turned out to be MISFRAMED are NOT in this list —
they were rejected with reasoning, not deferred.

---

## Triaged-DOWN (rejected, no backlog entry)

The following four critique items were rejected after analysis and do
NOT appear in the backlog. Listed here only so the rejection is
auditable:

- **Critique Item 1** — "claim → POST → commit_fired creates duplicate
  side-effect risk." MISFRAMED. The pattern matches AWS Builders'
  Library / Temporal / Conductor / Microservices.io idempotent-consumer
  guidance verbatim. Already documented in P21 + P33 + spec § 7.6.
- **Critique Item 4** — "no circuit breaker." MISFRAMED. Microsoft
  Azure's circuit-breaker guidance explicitly says don't add one when
  bounded retries cover the case. We have 3-attempt cap + 15min
  cooldown + 100-row batch + 8s budget + stuck exposure + manual
  reset — Azure's exclusion criteria are met.
- **Critique Item 5 (proposed solution only)** — "add `last_reset_at`
  / `last_reset_trace_id` columns on the row." MISFRAMED — strictly
  worse than current log-based audit (loses history on multiple
  resets). Underlying concern (log rotation eating history) IS valid
  → see B-053 below for the right fix.
- **Critique Item 6** — "/health write contention at high probe
  frequency." MISFRAMED. Verified via Railway docs: their healthcheck
  is one-shot per deploy, not periodic. External uptime monitors are
  1–5 min cadence at typical configurations. The premise of "constant
  write locks" doesn't match Railway's actual probe model.

---

## Done in S26 critique round (already shipped, no backlog needed)

- **Critique Item 3 — `fallback_error` truncation to 256 chars.**
  Shipped as one-line patch in `utils/scheduler_state_storage.py`
  + 3 new tests in `test_c03a_session7b_scheduler.py`. Within spec
  bounds (additive). 286/286 c3a, 1182/1182 project-wide.

---

## New backlog entries

### B-050. SQLite FK enforcement on storage connections
- **Origin:** Session 26 / Phase 7 build. Surfaced while writing
  health_endpoint.py: noticed that the spec § 7.4 statement "stuck
  rows expire implicitly via gate_states FK CASCADE on TTL" relies on
  `PRAGMA foreign_keys=ON`, which `_connect()` does not set.
- **Status:** DEFERRED
- **Trigger:** First production incident where stuck `scheduler_state`
  rows accumulate beyond their parent row's TTL (visible via
  `scheduler_stuck_count` on /health). OR: any future component that
  declares an FK and depends on CASCADE behavior.
- **Estimated effort:** Half a day. Add `PRAGMA foreign_keys=ON` to
  `_connect()`. Re-run full suite to catch any tests that quietly
  depended on FK violations being silently ignored.
- **Why not now:** Touching `_connect()` is outside S7b's locked
  surface (§ 1.2 carve-outs don't include it). Spec amendment work
  per the spec-first rule. Manual reset is the documented recovery
  path for stuck rows in the meantime; the slow CASCADE doesn't
  break correctness, it just leaves orphaned rows until manual
  cleanup.
- **Tag:** correctness

### B-051. Reconcile env-var name drift (`BUILDEMUP_DATABASE_PATH` vs `BUILDEMUP_GATE_DB_PATH`)
- **Origin:** Session 26 / Phase 8 build. Surfaced while writing
  `_validate_config()` in server.py: spec § 9.7 mandates checking
  `BUILDEMUP_DATABASE_PATH`, but the existing storage code reads
  `BUILDEMUP_GATE_DB_PATH`. An operator setting only the
  spec-compliant one will pass startup validation but storage will
  silently use the default path.
- **Status:** DEFERRED
- **Trigger:** Pre-prod deploy or any DEPLOY.md update. This bites
  the FIRST time someone configures env vars from the spec docs.
- **Estimated effort:** 1 hour. Either:
  (a) `_db_path()` reads `BUILDEMUP_DATABASE_PATH` first, falls back
      to `BUILDEMUP_GATE_DB_PATH` for backward compat, then default.
  (b) Spec amendment: rename to `BUILDEMUP_GATE_DB_PATH` everywhere.
  Path (a) is simpler and breaks nothing.
- **Why not now:** Same reason as B-050 — touches storage-code
  surface that's outside S7b carve-outs. Workaround: set BOTH env
  vars in production until reconciled (documented in the consolidated
  bundle README).
- **Tag:** spec-clarity

### B-052. Validate scheduler-state index selectivity at production scale
- **Origin:** Session 26 critique-round Item 2. Spec § 7.4 specifies
  `idx_fallback_due (fallback_fired, fire_at, attempt_count)` but
  the WHERE clause in `claim_due` also filters on `last_attempt_at`.
  SQLite's "left to right, no skipping, stops at first range" rule
  means at most one of the three range columns benefits from index
  lookup; the others become row-filters.
- **Status:** DEFERRED
- **Trigger:** Scheduler queue depth > 5,000 rows in production
  (visible via `scheduler_due_count` on /health), OR any observed
  tick latency degradation. At v0.1 scale (sub-1k rows) the query
  is fast regardless of plan.
- **Estimated effort:** 1 day. Run `EXPLAIN QUERY PLAN` against
  realistic production data, evaluate options:
  - Partial index `WHERE fallback_fired = 0` (excludes the dominant
    "already-fired" rows from the index entirely).
  - Reorder columns to put the most selective range first.
  - Possibly two indexes (one for the common claim path, one for the
    diagnostic count_due / count_stuck queries).
  Then schema migration via `_ensure_schema` extension.
- **Why not now:** The critique's prescribed reordering doesn't
  actually help (still stops after one range column per SQLite
  rules). Without production query profile, blind reordering is
  guesswork. Schema changes are spec amendment work.
- **Tag:** performance

### B-053. Log shipping to managed log platform (with audit-log retention)
- **Origin:** Session 26 critique-round Item 5. Underlying concern:
  log rotation eats audit history; admin reset audit lines disappear
  after N days. Industry consensus (Datadog, Sonar, AWS, Permit.io)
  is that operational/forensic audit logs belong in a centralized
  log management platform, not in the application database.
- **Status:** DEFERRED
- **Trigger:** First need to investigate an admin reset that
  happened > N days ago (where N = local log retention), OR any
  compliance / SOC2 / customer-due-diligence requirement.
- **Estimated effort:** 1–2 days deploy work, 0 code changes.
  Options on Railway:
  - Loki via Grafana Cloud free tier
  - Datadog (paid, 15-day default retention)
  - CloudWatch Logs (if migrating to AWS)
  - Self-hosted Loki on Railway (cheapest)
  Shipper config (Vector / Promtail / Datadog Agent) reads from
  stdout; our existing structured JSON log lines need no code change.
  Add retention policy: 90 days for `c3a.admin.scheduler_reset` and
  `c3a.scheduler.tick`; 30 days for everything else.
- **Why not now:** Pre-launch — there's no production traffic to
  audit and no compliance requirement yet. Wire up before first
  customer onboards or first admin reset is performed in prod,
  whichever comes first.
- **Tag:** ops

---

## Backlog ID assignments after this delta

| ID | Item | Status |
|---|---|---|
| B-040 | Migrate to Postgres when single-replica SQLite hits limit | DEFERRED |
| B-042 | Project-wide auth + per-session rate limiting | DEFERRED |
| B-043 | save_existing surgical fix | **DONE** (Phase 1) |
| B-044 | (existing — see prior backlog) | DEFERRED |
| B-045 | (existing — see prior backlog) | DEFERRED |
| B-046 | API response versioning | DEFERRED |
| B-048 | Email hook retry under measured failure trigger | DEFERRED |
| B-049 | Automated post-deploy hook execution verification | DEFERRED |
| **B-050** | **SQLite FK enforcement** | **NEW S26 S7b — DEFERRED** |
| **B-051** | **Env-var name drift reconciliation** | **NEW S26 S7b — DEFERRED** |
| **B-052** | **Scheduler index selectivity validation** | **NEW S26 S7b — DEFERRED** |
| **B-053** | **Log shipping with audit retention** | **NEW S26 S7b — DEFERRED** |
| **B-054** | **Test-justification linting CI plugin** | **NEW S26 S8 round 3 — DEFERRED** |
| **B-055** | **Concurrency iteration count post-launch tuning** | **NEW S26 S8 first post-LOCK — DEFERRED** |

---

## B-054 — Test-justification linting CI plugin

**Origin:** Session 26, S8 SPEC critique round 3, finding R3.5
(deferred from PATCH to BACKLOG).

**Description:** Automate enforcement of the § 4.0.1 hygiene rule
(every test must have a docstring justifying which P-invariant or
§ section it exercises). Implement as a pytest-collect plugin that
fails CI if any test class lacks the required justification
docstring. Complementary to the soft 3-consecutive-runs CI trigger
already in § 2.2.

**Trigger condition:** When test-suite growth visibly erodes the
hygiene rule post-S8-ship, OR when a developer manually adds
several tests without docstrings.

**S8-scope:** Out-of-scope. The hygiene rule itself IS in S8
(§ 4.0.1); only the enforcement automation is deferred. Keeps
S8 scope on validation suite, not on testing-infrastructure tooling.

**Effort estimate:** ~2 days for pytest-collect plugin + CI
integration + tests for the plugin.

**Why-not-now:** S8 spec is already at 78 tests + UI + 2 endpoints
+ 3 carve-outs. Adding tooling work would push C3a SHIP further.
Manual code-review enforcement of hygiene rule suffices for v1.

---

## B-055 — Concurrency iteration count post-launch tuning

**Origin:** Session 26, S8 SPEC critique round 4 (first
post-proposed-LOCK adjudication window), Item 2 partial.

**Description:** v1.2 LOCKED specifies 25 iterations per race test
in `test_c3a_concurrency.py` (PL1 reduction from 50, web-verified
diminishing-returns shape per Springer 2023 sublinear flaky-test
detection paper). Post-launch CI metrics may show this should be
retuned — UP if races are slipping through, DOWN if Tier 1 budget
pressure manifests as 3-consecutive-runs-over-25s triggers.

**Trigger condition:** EITHER
(a) Tier 1 budget metric routinely >27s (3-consecutive-runs trigger
    per § 2.2 PL2 fires), OR
(b) Observed race bug slips past 25 iterations in production
    (i.e., a race condition that the 25× test failed to catch).

**S8-scope:** Out-of-scope (post-launch tuning). v1.2 ships with
25 iterations + 3 deterministic worst-case anchor tests (P-3) which
together provide reasonable coverage. B-055 captures the tuning
opportunity for when real CI metrics arrive.

**Effort estimate:** ~1h tuning + measurement + small spec
amendment for the new iteration count (single number change in
§ 4.9 + test parametrize update).

**Why-not-now:** No CI runtime data exists yet (S8 not built).
Setting 25 was data-defensible (Springer paper); changing it
without data is not.

---

## Backlog state at Session 26 close

**9 deferred items total:**
- B-040 Postgres migration (pre-existing)
- B-042 project-wide auth + rate limiting (pre-existing)
- B-049 post-deploy hook verification (pre-existing)
- B-050 SQLite FK enforcement (S26 S7b critique)
- B-051 env-var name drift (S26 S7b critique)
- B-052 scheduler index validation at scale (S26 S7b critique)
- B-053 log shipping with audit retention (S26 S7b critique)
- B-054 test-justification linting (S26 S8 round 3)
- B-055 concurrency iteration tuning post-launch (S26 S8 first
  post-proposed-LOCK)

**None block C3a SHIP.** All have documented triggers for
promotion when conditions warrant.

**Per the new backlog-visibility-in-spec rule (memory #5,
formalized Session 26):** S8 SPEC v1.2 LOCKED § 12 enumerates all
9 items inside the spec doc itself. This backlog file mirrors §
12 — both are kept in sync; the spec is the canonical source of
truth.

---

## Generated end of Session 26 — S8 SPEC v1.2 LOCKED critique cycles complete
