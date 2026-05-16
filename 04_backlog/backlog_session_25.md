## Session 25 backlog additions

Added during Session 25 in the S7b SPEC critique cycles (round 1
disposition per D-067 push-back rule). Both items are deferred —
NOT blocking for S7b ship — and gated on measurable triggers per
the spec § 11.1 detail.

---

### B-048 — Email hook retry (gated on measured Resend failure rate)

**Severity:** Low (v0.1) → Medium (post-PMF when email volume scales)
**Source:** S7b SPEC round 1 critique #4 (PUSHBACK + BACKLOG per D-067).

**Symptom (today):** Production email hook
(`api/c3a_email_hook.py::send_cba_checklist`) makes a single HTTP
attempt to Resend with a 5-second timeout. No retry. The decision
is justified at v0.1 by P20 (scheduler 24h fallback IS the
reliability layer).

**Why deferred from S7b v1.0:** Synchronous retry inside the hook
adds 0.5s + 1s = 1.5s worst-case user-visible latency on every
email failure (the handler doesn't return until the hook returns).
Without measurement, the trade is wrong: accepting fixed 1.5s
latency on EVERY failure to rescue an unknown fraction of failures.
The scheduler 24h fallback (P21 + P33) is the documented
reliability layer.

**Proposed fix when triggered:** 1 retry, 1s backoff (single
attempt). No persistence, no queue. Stays inside the existing hook
function. Approximately 30 LOC + 2 tests.

**Trigger:** production Resend failure rate > 1% over a 30-day
window AND the failures are predominantly transient (network,
rate-limit) not permanent (verification, suppression). BOTH data
points needed before activating.

**Effort:** Sub-30-minute fix once trigger conditions are met.

---

### B-049 — Automated post-deploy hook execution verification

**Severity:** Low (v0.1) → Medium (post-PMF when deploy cadence
increases)
**Source:** S7b SPEC round 1 critique #11 (PARTIAL — manual
checklist accepted for v0.1, automation logged here).

**Symptom (today):** Smoke tests
(`tests/smoke_c3a_deploy.py`) verify endpoint contract — that
POSTing to /resolve returns 200 with the expected response shape.
They do NOT verify the email actually got sent to Resend or the
scheduler row actually got written into scheduler_state.
Post-deploy verification of hook side-effects is a manual
checklist (S7b SPEC § 8.5):
1. Check Resend dashboard for N emails sent matching the smoke
   pause flow.
2. Query scheduler_state for the expected new rows.
3. Force a fire_at = now on a smoke row and confirm the next
   /admin/scheduler/tick fires.
4. Validate /admin/scheduler/reset is reachable with admin token
   (404 on nonexistent token is the success signal).

**Why deferred from S7b v1.0:** Automation requires either:
(a) A test-mode email address with API readback (Resend has a
    sandbox endpoint `delivered@resend.dev` that logs but doesn't
    deliver — smoke could query it).
(b) A hook-counter telemetry surface that smoke tests can query
    via a /admin/test-counters endpoint or similar.
Both are real work, neither blocks ship.

**Proposed fix when triggered:** Option (a) preferred — smoke uses
Resend's `delivered@resend.dev` test address for pause flows, then
queries Resend's API to verify the message was logged. Adds
approximately 50 LOC + integration with the smoke runner.

**Trigger:** First time the manual checklist catches a real wiring
bug (operator-recorded), OR when the smoke-test cadence increases
beyond what a manual checklist can sustain (multiple deploys/day).

**Effort:** 1 sub-session (~50 LOC + smoke integration).

---

## Backlog count after Session 25

48 items total: B-001 through B-049, with B-026 superseded into
B-023 (so 48 active = 49 numbers minus 1 superseded).

Recent additions:
- B-040 (Session 23) — schema migration layer
- B-041 (Session 23) — BriefStorage WAL retrofit + prune sweep
- B-042 (Session 23) — project-wide auth
- B-043 (Session 24) — gate_state_storage.save_existing rollback
                        bug — **CLOSED in Session 25** (Phase 1
                        of S7b code build; P19 invariant; surgical
                        fix shipped)
- B-044 (Session 24 addendum) — storage-layer DI refactor
- B-045 (Session 24 addendum) — defense-in-depth from_dict
                                 validation
- B-046 (Session 24 addendum) — API response versioning strategy
- **B-047** (Session 25 internal — author-tracked) — Hosted job
                                 queue for scheduler if Railway
                                 cron reliability becomes a measured
                                 pain point. NOT formally added —
                                 documented in S7b SPEC § 0.3 (d)
                                 as a standing pushback. Skipping
                                 to B-048 in numbering.
- **B-048 (Session 25)** — Email hook retry under measured failure
                            trigger
- **B-049 (Session 25)** — Automated post-deploy hook execution
                            verification

---

## Items NOT added to backlog this session (transparent for future
readers, per D-067)

Round 1 round 2 round 3 critique surfaced 24 items total across
the three rounds. The dispositions that did NOT result in backlog
items (not just because the items were patched into spec, but
because they were rejected on principle):

**Round 1 #8** — "Move compute outside the storage transaction;
add jitter to retries." REJECTED. The compute step depends on the
lock-protected read-state; moving outside means computing from
stale data → lost-update bug. Same framing was rejected in S7a
D-067 round 3 (item #3). Documented in spec § 0.3 (h).

**Round 1 partial #7** — "IP allowlist + token rotation for admin
endpoints." REJECTED IP allowlist and rotation. Railway cron source
IPs not documented as stable; rotation adds state for low marginal
gain. ACCEPTED hmac.compare_digest only. § 0.3 (g).

**Round 2 #4** — "Pre-check session status before firing scheduler
tick." REJECTED the pre-check pattern (TOCTOU race + Pattern A +
storage coupling); ACCEPTED the visibility goal via response
parsing. § 0.3 (i).

These three are recorded in the locked spec § 0.3 standing
pushback list and should NOT re-surface in future critique rounds
absent new information.
