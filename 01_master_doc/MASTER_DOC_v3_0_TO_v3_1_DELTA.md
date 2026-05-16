# Master Doc — Session 25 Delta (v3.0 → v3.1)

This document captures the surgical updates needed to advance the
master design narrative from **v3.0 (Session 24)** to **v3.1
(Session 25)**, per the Update Protocol in Part 13.4. Apply each
zone update in order. The delta is presented this way (rather than
as a full v3.1 rewrite) because Session 25's context budget went
into shipping the S7b SPEC v1.0 LOCKED + Phase 1-4 of the code
build; honest scope-management per Obligation 2.

The next Claude (or Ramalingam) applies these changes to v3.0 and
saves the result as `MASTER_DESIGN_NARRATIVE_v3_1.md`.

---

## Zone 1 — Header / version

**Change the version line from:**
```
Version: v3.0 — 1 May 2026 (Session 24 — C3a S7a code build COMPLETE ...)
```

**To:**
```
Version: v3.1 — 1 May 2026 (Session 25 — C3a S7b SPEC v1.0 LOCKED
across 3 critique rounds; Phase 1-4 of S7b code build shipped
(B-043 surgical fix + new SchedulerStateStorage class +
_ensure_schema extension for scheduler_state table + Resend email
hook + scheduler hook with new signature); 254/254 c3a tests
(253 baseline + 1 B-043 re-add); 1150/1150 project-wide;
P19-P35 invariants defined and 5 of 17 backed by Phase 1-4 code;
Phases 5-9 pending — admin endpoint, c3a_endpoint
instrumentation, /health upgrade, config validation, 29 new
tests; ready for Session 26 to finish S7b code build)
```

---

## Zone 2 — Append Session 25 entry to Part 4 session log

Append the following as **§ 4.26** (Session 24 was § 4.25):

```markdown
### § 4.26 Session 25 — C3a S7b SPEC v1.0 LOCKED + Phase 1-4 code build

**Date:** 1 May 2026
**Duration:** single session, comprehensive build per Obligation 2
**Entry state:** S7a code build COMPLETE (Session 24 end);
  253/253 c3a baseline + 65 S7a new = 253 c3a tests (S7a tests
  fold into the 253 count via the integrated discover); 1149/1149
  project-wide; B-043 logged but unfixed; S7b queue prepared in
  NEXT_CLAUDE_HANDOFF.md.

**Work shipped this session — spec drafting:**

1. **S7b SPEC v0.1 DRAFT** — initial draft from the 7-item queue
   in NEXT_CLAUDE_HANDOFF (production email hook, production
   scheduler hook, B-043 fix, metrics + tracing, error-path retry
   policy, Railway deployment config, smoke tests). 1096 lines.
   Self-flagged Q1: storage-lock vs ALTER TABLE contradiction.

2. **S7b SPEC v0.2 DRAFT — round 1 critique applied** (15 items;
   1695 lines):
   - 12 patches: P27-P32 (separate scheduler_state table per round 1
     #1; index per #2; atomic UPDATE...RETURNING per #3; trace_id
     propagation per #5; bounded metric cardinality per #6; admin
     hmac.compare_digest per #7; server-time scheduler firing per
     #9; /health upgrade per #10; SCHEDULER_TICK_LIMIT per #12;
     P32 startup config validation per #13; PII masking per #14;
     drift WARNING per #15)
   - 2 pushbacks documented (round 1 #4 email retry → B-048;
     round 1 #8 lock contention preempt → § 0.3 (h))
   - 2 partials (round 1 #7 admin security: hmac.compare_digest
     accepted, IP allowlist + rotation pushed back; round 1 #11
     smoke hook verification: manual checklist accepted, automation
     → B-049)
   - 2 new backlog items added: B-048 + B-049

3. **S7b SPEC v0.3 DRAFT — round 2 critique applied** (8 items;
   1502 lines):
   - 7 patches: P33 (at-least-once with bounded retries via
     claim-then-commit + 3-attempt cap + scheduler_stuck_count via
     /health, addressing round 2 #1); P34 (trace_id format
     validation regex at trust boundary, round 2 #3); SQLite
     version check moved to _validate_config per P32 (round 2 #2);
     /health adds scheduler write path (round 2 #5); error_class
     "internal" preserves detail via separate WARNING line (round 2
     #6); config validation extended to value sanity (round 2 #7);
     8s soft tick budget (round 2 #8)
   - 1 partial: round 2 #4 (pre-fire status check rejected as
     TOCTOU + Pattern A + storage-coupling; visibility goal
     accepted via response parsing)
   - 0 substantive pushbacks; 0 new backlog items

4. **S7b SPEC v0.4 DRAFT — round 3 critique applied** (1 item;
   776 lines):
   - 1 patch: P35 (admin reset endpoint POST /admin/scheduler/reset
     with single-row, idempotent, atomic, audited semantics; closes
     the operational dead-end created in v0.3 where stuck rows had
     no recovery path other than direct DB surgery)

5. **S7b SPEC v1.0 LOCKED** (2236 lines, fully self-contained per
   Rule 2b). Three critique rounds clean to lock. 17 P-invariants
   P19-P35 defined. § 11.1 BACKLOG ITEMS — FULL DETAIL inlined for
   B-048 + B-049 per Rule 2b spec self-containment.

**Work shipped this session — code build (Phase 1-4):**

1. **Phase 1 — B-043 surgical fix** (P19) at
   `utils/gate_state_storage.py::save_existing` rowcount=0 branch:
   single line removed (manual ROLLBACK), single comment added
   referencing P19. Re-added
   `test_save_existing_unknown_token_raises` to
   `tests/test_c03a_session7_storage.py` — 15 → 16 tests in that
   file. Verified: TokenNotFoundError now propagates cleanly.

2. **Phase 2 — SchedulerStateStorage class** at
   `utils/scheduler_state_storage.py` (NEW, 430 LOC):
   - 7 public methods: enqueue (idempotent UPSERT), claim_due
     (atomic UPDATE...RETURNING with cooldown filter — P28 + P33),
     commit_fired (P33 commit phase), record_error (P33 failure
     diagnostic), count_due (diagnostic for /health), count_stuck
     (P33 stuck-row exposure), reset (P35 admin recovery)
   - ResetOutcome enum + ResetResult dataclass for the reset API
   - Mask helper for log lines
   - Schema extension to `gate_state_storage._ensure_schema`:
     idempotent CREATE TABLE for scheduler_state + index
     idx_fallback_due. gate_states schema byte-identical to S7a.

3. **Phase 3 — Resend email hook** at `api/c3a_email_hook.py`
   (REPLACED stub, ~170 LOC):
   - `send_cba_checklist(to_email, draft_token, fallback_at, *,
     trace_id=None)` — backward-compatible signature add of
     trace_id keyword
   - POST to https://api.resend.com/emails via stdlib
     urllib.request; Authorization: Bearer + Content-Type
   - X-Trace-Id forwarded to Resend as custom header per P29
   - Graceful degrade on missing RESEND_API_KEY (log WARNING +
     return None)
   - Email masking helper per round 1 #14 (`alice@example.com`
     → `a***e@example.com`)
   - HTML email body inlined; minimal styling

4. **Phase 4 — Scheduler hook** at `api/c3a_scheduler_hook.py`
   (REPLACED stub, ~120 LOC):
   - SIGNATURE CHANGE per spec § 7.4 + § 8.7:
     - OLD: `(draft_token, fallback_at)` where fallback_at was ISO
     - NEW: `(session_token, fire_at_unix, request_id, *,
            trace_id=None)` — fire_at is INT UNIX timestamp per P31;
            request_id added positionally for P21 idempotency
   - Body writes to scheduler_state via
     SchedulerStateStorage.enqueue
   - Lazy module-singleton storage with `reset_storage_for_tests`
     test seam matching the c3a_endpoint pattern

**End-to-end sanity test:** enqueue → claim_due (returns row,
attempt_count=1, trace_id propagated) → second claim_due (cooldown
filter blocks re-claim) → commit_fired (stuck_count=0) → reset on
already-fired (returns ALREADY_FIRED outcome) → reset on unknown
token (returns NOT_FOUND outcome). All four behavioral invariants
P28, P29, P33, P35 verified end-to-end via direct module
exercise.

**Acceptance state at session end:**
- 254/254 c3a tests pass (253 baseline + 1 new B-043 re-add)
- 1150/1150 project-wide tests pass (no upstream regression)
- 5 P-invariants P19, P27, P28 (partial), P29 (partial), P33
  (partial), P35 (partial) backed by code; the rest pending
  Phases 5-9
- Spec LOCKED at v1.0; 3 critique rounds clean

**Outstanding (Phase 5-9 — Session 26 build queue):**
- Phase 5: `api/admin_endpoint.py` NEW — handle_scheduler_tick +
  handle_scheduler_reset (~250 LOC)
- Phase 6: `api/c3a_endpoint.py` MODIFIED — instrumentation
  wrapper at all 5 handler entries (P22, P30); HTTP 503
  storage_busy path (§ 6.2); P29 trace_id propagation through
  inner handlers; hook call-site updates for new signatures
  (especially the scheduler hook — c3a_endpoint must compute
  fire_at_unix and pass request_id); ~80 LOC delta
- Phase 7: `/health` endpoint upgrade — write+rollback verify on
  both gate_states and scheduler_state; reports
  scheduler_due_count and scheduler_stuck_count (~50 LOC)
- Phase 8: `api/server.py` MODIFIED — add admin routes; call
  `_validate_config()` at startup per P32; (~30 LOC). New
  `api/_config_validator.py` module with the validator (~50 LOC).
- Phase 9: 29 new tests across 7 new test files + the 2-line
  fake-signature update in
  `tests/test_c03a_session7_hook_ordering.py` per § 8.7
  (~900 LOC)

**Total path to S7b ship + S8 + C3a complete = 4 of 17 components:**
~3 sessions remaining (Session 26 finishes code build; Session 27
code-critique cycle + S7b ship; Session 28 S8 validation suite).
```

---

## Zone 3 — Inventory updates

In Part 7 (file inventory), add these new files:

```
api/c3a_email_hook.py             — REPLACED, ~170 LOC
                                    (Phase 3 — Resend wiring)
api/c3a_scheduler_hook.py         — REPLACED, ~120 LOC
                                    (Phase 4 — sig change +
                                     scheduler_state writer)
utils/scheduler_state_storage.py  — NEW, ~430 LOC
                                    (Phase 2 — Session 25)
```

Modified files:
```
utils/gate_state_storage.py            — Phase 1 B-043 fix +
                                          Phase 2 _ensure_schema
                                          extension
                                          (~30 LOC delta)
tests/test_c03a_session7_storage.py    — Phase 1 re-added test
                                          (~15 LOC)
```

Two specs locked this session, all four drafts preserved
chronologically:
```
buildemup_S7b_SPEC_v0_1_DRAFT.txt     — 1096 lines
buildemup_S7b_SPEC_v0_2_DRAFT.txt     — 1695 lines
buildemup_S7b_SPEC_v0_3_DRAFT.txt     — 1502 lines
buildemup_S7b_SPEC_v0_4_DRAFT.txt     —  776 lines
buildemup_S7b_SPEC_v1_0_LOCKED.txt    — 2236 lines (v0.4 inlined
                                                    per Rule 2b)
```

---

## Zone 4 — Build status update (Part 8)

**Test count:** 1150 project-wide (was 1149 in v3.0; +1 new B-043
re-add). 254 c3a (was 253 in v3.0; same +1).

**c3a sub-session status table — replace with:**

| Sub-session | Status     | Tests added | Cumulative c3a tests |
|-------------|------------|-------------|----------------------|
| S1          | ✅ shipped | 24          | 24                   |
| S2          | ✅ shipped | 18          | 42                   |
| S3          | ✅ shipped | 22          | 64                   |
| S4          | ✅ shipped | 31          | 95                   |
| S5          | ✅ shipped | 28          | 123                  |
| S6          | ✅ shipped | 41          | 164                  |
| B-027 fix   | ✅ shipped | 24          | 188                  |
| S7a         | ✅ shipped Session 24 | 65 | 253                  |
| **S7b**     | **🔧 in build (Phase 1-4 of 9 done)** | **+1 (B-043 re-add)** | **254** |
| S8          | ⬜ pending  | TBD         | —                    |

**Component shipping status — update:**

```
3 of 17 components shipped (C1, C2, C7).
C3a in build: 7 of 8 sub-sessions complete (S1-S6, B-027, S7a).
S7b spec LOCKED v1.0; code Phase 1-4 of 9 shipped.
S7b code Phase 5-9 + S8 remaining → path to 4 of 17.
```

---

## Zone 5 — Decisions (Part 9) — APPEND ONLY

```markdown
### Decision § 9.37 — Scheduler state in a separate table (P27)

**Locked Session 25 during S7b SPEC round 1 critique (item #1).**

**Decision:** Scheduler-related persistence (fire_at,
fallback_fired, attempt_count, last_attempt_at, fallback_error,
trace_id, request_id) lives in a NEW `scheduler_state` table, NOT
on `gate_states`. The S7b carve-out on `gate_state_storage.py` is
narrowly the B-043 surgical fix; the new table is added via an
`_ensure_schema` extension and read/written through a separate
`SchedulerStateStorage` class in a new file.

**Rationale:** v0.1 of the S7b spec proposed adding a
`fallback_fired` column to `gate_states`. Round 1 critique #1
correctly identified this as a spec-internal contradiction:
§ 1.2 stated `gate_states` was locked; § 9.2 added a column to
it. The separation eliminates the contradiction and isolates
scheduler concerns architecturally — no future scheduler-related
schema growth touches the locked gate_states surface.

### Decision § 9.38 — At-least-once scheduler delivery with
bounded retries (P33)

**Locked Session 25 during S7b SPEC round 2 critique (item #1).**

**Decision:** The atomic dequeue (P28) CLAIMS rows (sets
attempt_count + last_attempt_at) without committing
fallback_fired. Successful POST commits the row via a separate
UPDATE setting fallback_fired = 1. Failed POST records
fallback_error and leaves the row unfired; the next tick (after
15-min cooldown) re-claims and retries. Cap at 3 attempts. Stuck
rows (fallback_fired=0 AND attempt_count>=3) stay in the table
and are surfaced via /health `scheduler_stuck_count`.

**Rationale:** v0.2's commit-then-attempt model (mark fired
atomically, then POST) lost data on POST failure — a row marked
fired but not delivered was permanently lost, with no automatic
recovery path. The claim-then-commit split makes the firing
operation idempotent and recoverable: failures are diagnostic
(via fallback_error) and self-recovering (via cooldown +
attempt_count cap). Stuck rows are operationally visible and
recoverable manually via P35 admin reset.

### Decision § 9.39 — Admin reset endpoint for stuck rows (P35)

**Locked Session 25 during S7b SPEC round 3 critique (item #1).**

**Decision:** `POST /admin/scheduler/reset` with body
`{session_token: "..."}` clears attempt_count + last_attempt_at +
fallback_error on a non-fired row, making it eligible for
re-claim by the next tick. Single-row, idempotent, atomic,
audited. Same auth as the tick endpoint
(`X-Admin-Token` via `hmac.compare_digest`). Three outcomes:
RESET (200 + was_stuck flag), ALREADY_FIRED (409 — protects
committed rows), NOT_FOUND (404).

**Rationale:** v0.3 created an operational dead-end — P33's
detection mechanism (`scheduler_stuck_count` exposure via /health)
without a paired recovery endpoint meant the only remediation
path for systemic delivery failures was direct DB surgery
(SQL UPDATE). Round 3 critique correctly identified that
detection-without-action contradicts the API-surface-as-self-
service model the rest of S7b commits to. The reset endpoint is
the missing operational counterpart; adding it makes the design
more coherent rather than adding rules on top of rules
(NOT Pattern D).
```

---

## Zone 6 — Part 11 (Next Step) — REWRITE

Replace the existing "Next step" section with:

```markdown
## Part 11 — Next Step (after Session 25)

**Immediate next:** **S7b CODE BUILD — PHASES 5-9** in Session 26.

The locked spec is at
`02_specs_chronological/21_S7b_SPEC_v1_0_LOCKED.txt`. The build
queue (Phases 5-9) is detailed in `NEXT_CLAUDE_HANDOFF.md` with
file paths, what's done vs pending, and the 17 P-invariants
P19-P35 that need test coverage.

**After S7b code complete:** code-critique cycle (D-066 step 7)
→ S8 validation suite → C3a SHIPPED → 4 of 17 components shipped.

**Long-range (post-C3a):** C3b (Layout Generator), then C4-C17.

**Immediate concrete first action for next Claude:** Read
NEXT_CLAUDE_HANDOFF.md, apply this delta to v3.0 (saving as
v3.1), then resume S7b code build at Phase 5 (admin endpoint).
```

---

## Zone 7 — Footer

**Replace the version line at document end with:**

```
Version: v3.1 — 1 May 2026 (Session 25 — C3a S7b SPEC v1.0
LOCKED across 3 critique rounds; Phase 1-4 of 9 shipped: B-043
surgical fix, SchedulerStateStorage class, _ensure_schema
extension for scheduler_state table, Resend email hook, scheduler
hook with new signature; 254/254 c3a tests; 1150/1150 project
tests; 17 P-invariants P19-P35 defined; D-066/D-067 cycle clean
through 3 spec critique rounds; ready for Session 26 to finish
S7b Phases 5-9 — admin endpoint, c3a_endpoint instrumentation,
/health upgrade, config validation, 29 new tests; path to S7b
ship + S8 + C3a complete = 4 of 17 components in ~3 more sessions)
```

---

## Why a delta — and the canonical-record stance

**Deltas chain as the canonical master record.** This is the
project pattern, not a placeholder for a future rewrite:

- v2.9 is the last full materialization.
- v2.9 → v3.0 delta (Session 24) and v3.0 → v3.1 delta (this
  session) chain on top of it.
- The mental model = source-control commits: each delta captures
  what changed, the chain is the canonical narrative, and
  consolidation into a new full master is a periodic deliberate
  housekeeping action — NOT a per-session ritual.

Rule 6's status block lives in the LATEST delta (Zone 4 + Zone 7
here), so the canonical status surface is always the most recent
delta document.

**Per Obligation 2 (honest context budget):** the master doc is
~3,000 lines. A full rewrite mid-session burns context that's
better spent on the actual deliverable. Capturing deltas precisely
preserves both fidelity and audit trail without the cost.

**When to materialize a full master next:** when the chained delta
count makes orientation hard for a fresh Claude (rule of thumb: 3-4
deltas accumulated, OR before a major component ships, OR when
Ramalingam decides). Until then, read the chain.

---

**End of Session 25 Delta**
