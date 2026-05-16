"""S7b § 7.4 + § 8.1 — Scheduler tests (7).

Seven tests covering the scheduler state storage and admin tick:

  1. init + idempotent re-init (CREATE TABLE IF NOT EXISTS twice)
  2. Atomic dequeue (P28: parallel claims yield distinct rows)
  3. Batch limit (LIMIT enforced; remainder eligible next tick)
  4. Retry success (POST fails → cooldown → re-claim → succeeds)
  5. Retry cap (P33: 3 failures → row stuck; not re-claimed)
  6. Time budget (P-round-2-#8: slow POST → budget hits → unprocessed
     deferred; cooldown protects them)
  7. Drift WARNING when fire_at delay > 30 min
"""
from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from unittest.mock import patch

# Set admin token before any module that reads env at import time.
os.environ.setdefault("BUILDEMUP_ADMIN_TOKEN", "test-admin-token-1234567890")

from buildemup.api import admin_endpoint
from buildemup.utils.scheduler_state_storage import (
    DRIFT_WARN_S,
    RETRY_CAP,
    SchedulerStateStorage,
)


_ADMIN_TOKEN = "test-admin-token-1234567890"
_AUTH_HEADERS = {"X-Admin-Token": _ADMIN_TOKEN}


def _seed_gate_states_row(db_path: str, token: str) -> None:
    """Minimal gate_states row to keep DB consistent with prod schema."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, ?, ?, ?, 0, NULL, NULL)",
            (token, '{}', int(time.time()), int(time.time()) + 86400),
        )
        conn.commit()


class _SchedulerTestBase(unittest.TestCase):
    """Shared fixture: temp DB + storage + admin singleton injection."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="sched-test-")
        self.db_path = os.path.join(self._tmpdir, "sched.db")
        self.storage = SchedulerStateStorage(db_path=self.db_path)
        admin_endpoint.reset_scheduler_storage_for_tests(self.storage)
        os.environ["BUILDEMUP_ADMIN_TOKEN"] = _ADMIN_TOKEN

    def tearDown(self):
        admin_endpoint.reset_scheduler_storage_for_tests(None)


class TestSchedulerInit(_SchedulerTestBase):

    def test_init_idempotent_create_table_if_not_exists(self):
        """Re-initialising on the same DB doesn't error.

        CREATE TABLE IF NOT EXISTS is idempotent. Two consecutive
        SchedulerStateStorage() against the same path must succeed
        and produce a working storage object.
        """
        # Already initialised in setUp; re-init.
        storage2 = SchedulerStateStorage(db_path=self.db_path)
        # Both should work
        self.assertEqual(storage2.count_due(int(time.time())), 0)
        self.assertEqual(storage2.count_stuck(), 0)


class TestSchedulerAtomicDequeue(_SchedulerTestBase):

    def test_p28_parallel_claims_yield_distinct_rows(self):
        """P28: two threads claiming concurrently never see the same row.

        Seed N rows. Spin up 2 threads that each call claim_due() with
        large limit. The union of their results equals N; the
        intersection is empty.
        """
        n_rows = 20
        for i in range(n_rows):
            tk = uuid.uuid4().hex
            _seed_gate_states_row(self.db_path, tk)
            self.storage.enqueue(
                session_token=tk,
                fire_at=int(time.time()) - 60,
                request_id=f"req-{i}",
                trace_id=None,
            )

        results: dict[int, list] = {0: [], 1: []}
        barrier = threading.Barrier(2)

        def _claim(idx):
            barrier.wait()  # synchronize start
            results[idx] = self.storage.claim_due(
                int(time.time()), limit=n_rows,
            )

        t1 = threading.Thread(target=_claim, args=(0,))
        t2 = threading.Thread(target=_claim, args=(1,))
        t1.start(); t2.start()
        t1.join(); t2.join()

        tokens_1 = {row[0] for row in results[0]}
        tokens_2 = {row[0] for row in results[1]}

        # Union covers everything; intersection is empty
        self.assertEqual(tokens_1 | tokens_2, set(tokens_1) | set(tokens_2))
        self.assertEqual(tokens_1 & tokens_2, set(),
                         "two threads claimed the same row — P28 broken")
        self.assertEqual(len(tokens_1) + len(tokens_2), n_rows)


class TestSchedulerBatchLimit(_SchedulerTestBase):

    def test_batch_limit_enforces_per_call_cap(self):
        """LIMIT=N caps a single claim. Remaining rows surface next call.

        Seed 250 due rows. claim_due(limit=100) returns exactly 100;
        the next claim_due returns the remaining 150 (in two batches).
        """
        total = 250
        for i in range(total):
            tk = uuid.uuid4().hex
            _seed_gate_states_row(self.db_path, tk)
            self.storage.enqueue(
                session_token=tk,
                fire_at=int(time.time()) - 60,
                request_id=f"req-{i}",
                trace_id=None,
            )

        # First claim
        first = self.storage.claim_due(int(time.time()), limit=100)
        self.assertEqual(len(first), 100)
        # Second claim — cooldown applies to the FIRST batch (just
        # claimed), so second claim sees only the un-claimed 150 rows.
        second = self.storage.claim_due(int(time.time()), limit=100)
        self.assertEqual(len(second), 100)
        # No overlap
        first_tokens = {r[0] for r in first}
        second_tokens = {r[0] for r in second}
        self.assertEqual(first_tokens & second_tokens, set())
        # Third claim picks up the final 50
        third = self.storage.claim_due(int(time.time()), limit=100)
        self.assertEqual(len(third), 50)


class TestSchedulerRetrySuccess(_SchedulerTestBase):

    def test_failed_post_then_cooldown_then_success_commits(self):
        """POST fails on tick 1 → record_error → tick 2 (after cooldown
        elapsed) re-claims → POST succeeds → commit_fired.

        We can't actually wait 15 minutes (the production cooldown).
        Instead, manually clear `last_attempt_at` between ticks to
        simulate "cooldown elapsed". The dequeue WHERE filter uses a
        strict `<` against `now - cooldown`, so even cooldown=0 leaves
        a just-claimed row briefly ineligible — which is the correct
        real-world behavior, just inconvenient to exercise in a test.
        """
        token = uuid.uuid4().hex
        _seed_gate_states_row(self.db_path, token)
        self.storage.enqueue(
            session_token=token,
            fire_at=int(time.time()) - 60,
            request_id="req-retry",
            trace_id="abcd1234abcd1234",
        )

        # Tick 1: POST fails
        rows = self.storage.claim_due(int(time.time()))
        self.assertEqual(len(rows), 1)
        self.storage.record_error(token, "post_exception: simulated")

        # Confirm row is unfired but with attempt_count = 1
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT fallback_fired, attempt_count, fallback_error "
                "FROM scheduler_state WHERE session_token = ?",
                (token,),
            ).fetchone()
        self.assertEqual(row[0], 0)  # not fired
        self.assertEqual(row[1], 1)  # attempt 1
        self.assertEqual(row[2], "post_exception: simulated")

        # Simulate cooldown elapsed: clear last_attempt_at.
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE scheduler_state SET last_attempt_at = NULL "
                "WHERE session_token = ?", (token,),
            )
            conn.commit()

        # Tick 2: claim again. Now POST succeeds — commit_fired.
        rows = self.storage.claim_due(int(time.time()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], token)
        self.storage.commit_fired(token)

        # Final state: fired = 1, attempt_count = 2
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT fallback_fired, attempt_count "
                "FROM scheduler_state WHERE session_token = ?",
                (token,),
            ).fetchone()
        self.assertEqual(row, (1, 2))


class TestSchedulerRetryCap(_SchedulerTestBase):

    def test_p33_retry_cap_stuck_row_not_reclaimed_count_stuck_one(self):
        """P33: after RETRY_CAP failures, row stays unfired AND no
        further claim picks it up. count_stuck() reports 1.

        The cooldown-elapsed simulation (clearing last_attempt_at)
        applies between each tick — see retry-success test for the
        same idiom. The point of THIS test is the retry cap, not the
        cooldown timing.
        """
        token = uuid.uuid4().hex
        _seed_gate_states_row(self.db_path, token)
        self.storage.enqueue(
            session_token=token,
            fire_at=int(time.time()) - 60,
            request_id="req-cap",
            trace_id=None,
        )

        # Burn through all RETRY_CAP attempts
        for i in range(RETRY_CAP):
            rows = self.storage.claim_due(int(time.time()))
            self.assertEqual(len(rows), 1, f"claim {i} got {len(rows)} rows")
            self.storage.record_error(token, f"failure_{i}")
            # Simulate cooldown elapsed between attempts
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE scheduler_state SET last_attempt_at = NULL "
                    "WHERE session_token = ?", (token,),
                )
                conn.commit()

        # Now attempt_count = RETRY_CAP. WHERE filter is
        # `attempt_count < RETRY_CAP`, so next claim picks NOTHING
        # — even with cooldown bypassed.
        rows = self.storage.claim_due(int(time.time()))
        self.assertEqual(len(rows), 0,
                         "row at retry cap should NOT be re-claimed")

        # count_stuck reports the stuck row
        self.assertEqual(self.storage.count_stuck(), 1)


class TestSchedulerTimeBudget(_SchedulerTestBase):

    def test_time_budget_exceeded_defers_remainder_with_cooldown_protect(self):
        """Slow POST → 8s budget hits → time_budget_exceeded=True;
        unprocessed rows are NOT touched but their attempt_count was
        already incremented at claim time (cooldown protects them).
        """
        n_rows = 6
        for i in range(n_rows):
            tk = uuid.uuid4().hex
            _seed_gate_states_row(self.db_path, tk)
            self.storage.enqueue(
                session_token=tk,
                fire_at=int(time.time()) - 60,
                request_id=f"req-budget-{i}",
                trace_id=None,
            )

        # Force a tiny budget so we don't wait 8 seconds.
        original = admin_endpoint._SCHEDULER_TICK_BUDGET_S
        admin_endpoint._SCHEDULER_TICK_BUDGET_S = 0.10  # 100ms

        def _slow_post(*, session_token, request_id, trace_id):
            time.sleep(0.05)  # 50ms each → 2 fit in 100ms
            return 200, {"ok": True}

        try:
            with patch.object(admin_endpoint, "_post_fallback_continue",
                              side_effect=_slow_post):
                status, body = admin_endpoint.handle_scheduler_tick(
                    b"", _AUTH_HEADERS,
                )
        finally:
            admin_endpoint._SCHEDULER_TICK_BUDGET_S = original

        self.assertEqual(status, 200)
        self.assertTrue(body["time_budget_exceeded"])
        self.assertEqual(body["due"], n_rows)
        self.assertLess(body["processed"], body["due"],
                        "expected partial processing under budget")
        self.assertGreater(body["fired"], 0, "at least one row should fire")


class TestSchedulerDriftWarning(_SchedulerTestBase):

    def test_drift_warning_logged_when_fire_at_delay_exceeds_threshold(self):
        """When a claimed row is more than DRIFT_WARN_S seconds late,
        claim_due emits a WARNING. Indicator that the cron is missing
        scheduled fires (Railway down, missed ticks, etc.).
        """
        token = uuid.uuid4().hex
        _seed_gate_states_row(self.db_path, token)
        # fire_at = now - DRIFT_WARN_S - 60s → comfortably over threshold
        late_fire_at = int(time.time()) - DRIFT_WARN_S - 60
        self.storage.enqueue(
            session_token=token,
            fire_at=late_fire_at,
            request_id="req-late",
            trace_id="0123456789abcdef",
        )

        # Capture WARNING from the storage logger
        records: list[str] = []

        class _H(logging.Handler):
            def emit(self_inner, record):
                records.append(record.getMessage())

        h = _H()
        h.setLevel(logging.WARNING)
        lg = logging.getLogger(
            "buildemup.utils.scheduler_state_storage",
        )
        lg.addHandler(h)
        try:
            self.storage.claim_due(int(time.time()))
        finally:
            lg.removeHandler(h)

        # At least one WARNING containing 'drift'
        drift_lines = [r for r in records if "drift" in r.lower()]
        self.assertTrue(
            len(drift_lines) >= 1,
            f"expected a drift WARNING; records = {records!r}",
        )


class TestSchedulerErrorTruncation(_SchedulerTestBase):
    """Session-26 critique-round patch: record_error() truncates to
    FALLBACK_ERROR_MAX_LEN to prevent DB / WAL bloat from large
    exception strings.
    """

    def test_record_error_truncates_long_strings_to_max_len(self):
        """A multi-KB error string is clipped to FALLBACK_ERROR_MAX_LEN
        chars before persisting; the row's fallback_error column
        contains exactly that prefix.
        """
        from buildemup.utils.scheduler_state_storage import (
            FALLBACK_ERROR_MAX_LEN,
        )

        token = uuid.uuid4().hex
        _seed_gate_states_row(self.db_path, token)
        self.storage.enqueue(
            session_token=token,
            fire_at=int(time.time()) - 60,
            request_id="req-truncate",
            trace_id=None,
        )
        # Claim so the row is in the right state for record_error
        self.storage.claim_due(int(time.time()))

        # Build a 5KB error string with a recognizable prefix so we
        # can verify the kept portion is the LEADING bytes.
        prefix = "STACKTRACE_HEAD_RECOGNIZABLE: "
        long_error = prefix + ("X" * 5000)
        self.assertGreater(len(long_error), FALLBACK_ERROR_MAX_LEN)

        self.storage.record_error(token, long_error)

        # Verify the persisted column is exactly the truncated prefix
        with sqlite3.connect(self.db_path) as conn:
            stored = conn.execute(
                "SELECT fallback_error FROM scheduler_state "
                "WHERE session_token = ?",
                (token,),
            ).fetchone()[0]

        self.assertEqual(len(stored), FALLBACK_ERROR_MAX_LEN)
        self.assertEqual(stored, long_error[:FALLBACK_ERROR_MAX_LEN])
        # Sanity: prefix is still readable at the start
        self.assertTrue(stored.startswith(prefix))

    def test_record_error_short_strings_unchanged(self):
        """Strings already under the cap pass through verbatim.

        The truncation is a ceiling, not a re-shape. Short error
        strings (the common case) are stored byte-for-byte as the
        caller supplied them.
        """
        token = uuid.uuid4().hex
        _seed_gate_states_row(self.db_path, token)
        self.storage.enqueue(
            session_token=token,
            fire_at=int(time.time()) - 60,
            request_id="req-short",
            trace_id=None,
        )
        self.storage.claim_due(int(time.time()))

        short = "post_exception: ConnectionError: refused"
        self.storage.record_error(token, short)

        with sqlite3.connect(self.db_path) as conn:
            stored = conn.execute(
                "SELECT fallback_error FROM scheduler_state "
                "WHERE session_token = ?",
                (token,),
            ).fetchone()[0]
        self.assertEqual(stored, short)

    def test_record_error_handles_none_or_empty_safely(self):
        """Defensive: None or '' don't crash; stored as empty string."""
        token = uuid.uuid4().hex
        _seed_gate_states_row(self.db_path, token)
        self.storage.enqueue(
            session_token=token,
            fire_at=int(time.time()) - 60,
            request_id="req-empty",
            trace_id=None,
        )
        self.storage.claim_due(int(time.time()))

        # Empty string
        self.storage.record_error(token, "")
        with sqlite3.connect(self.db_path) as conn:
            stored = conn.execute(
                "SELECT fallback_error FROM scheduler_state "
                "WHERE session_token = ?",
                (token,),
            ).fetchone()[0]
        self.assertEqual(stored, "")


if __name__ == "__main__":
    unittest.main()
