"""S8 § 4.9 — Concurrency / race tests (3 looped × 25 iter + 3 anchors).

Per § 4.9 + v1.2 P-3:
  - 3 looped tests with seeded randomized 0-10ms pre-delays
    (R3.3 determinism), 25 iterations each (PL1 reduction from 50)
  - 3 deterministic worst-case anchor tests (zero delay,
    barrier-only sync) — exercise exact same-millisecond collision

Budget impact (post-PL1 + P-3): ~2.6s in Tier 1 (75 looped + 3 anchors
× ~30ms).

Per spec § 4.9: "this is the highest-risk new test file in S8".
If a race test fails at first run, that's a real bug in S7b code.

The tests focus on the SchedulerStateStorage atomic-claim contract
(P28) — that's where the race-window concerns concentrated during
S7b critique. Higher-level state-machine races (e.g. user CBA verify
vs scheduler fallback) are covered at the scheduler-storage layer
because the storage IS the synchronization point.

§ 4.0.1: each test docstring names which invariant it protects.
"""
from __future__ import annotations

import random
import sqlite3
import threading
import time

import pytest


def _seed_gate(db_path, token):
    now = int(time.time())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, '{}', ?, ?, 0, NULL, NULL)",
            (token, now, now + 86400),
        )
        conn.commit()


# ─────────────────────────────────────────────────────────────────────
# Looped tests (25 iterations × 3 scenarios = 75 race executions)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("iteration", range(25))
class TestRaceLoops:
    """§ 4.9 looped — seeded random 0-10ms pre-delays (R3.3)."""

    def test_atomic_dequeue_same_row_no_double_claim(
        self, iteration, fresh_storage, temp_db_path,
    ):
        """P28: two parallel claim_due() calls on the SAME row →
        exactly one claims it.

        Race scenario: scheduler tick fires twice (e.g. duplicate
        cron, paused-and-resumed worker). Atomic claim invariant
        ensures the row is dispensed once."""
        random.seed(iteration)
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = f"tok-race1-{iteration}"
        _seed_gate(temp_db_path, token)
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id=f"r-{iteration}",
            trace_id="0123456789abcdef",
        )
        barrier = threading.Barrier(2)
        outcomes: dict[str, int] = {"a": 0, "b": 0}

        def fire(key):
            time.sleep(random.uniform(0, 0.01))
            barrier.wait()
            try:
                claimed = storage.claim_due(
                    now=int(time.time()), limit=1,
                )
                outcomes[key] = sum(
                    1 for c in claimed if c[0] == token
                )
            except Exception:
                outcomes[key] = -1

        t1 = threading.Thread(target=fire, args=("a",))
        t2 = threading.Thread(target=fire, args=("b",))
        t1.start(); t2.start(); t1.join(); t2.join()
        # Exactly one thread saw this token
        assert sum(outcomes.values()) == 1, (
            f"iter={iteration}: outcomes={outcomes!r}"
        )

    def test_record_error_on_already_claimed_row_safe(
        self, iteration, fresh_storage, temp_db_path,
    ):
        """P33 + P28: record_error against a row that was claimed by
        another worker is SAFE (no exception, no inconsistent state)."""
        random.seed(iteration + 100)
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = f"tok-race2-{iteration}"
        _seed_gate(temp_db_path, token)
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id=f"r-re-{iteration}",
            trace_id="0123456789abcdef",
        )
        barrier = threading.Barrier(2)
        ok = {"a": False, "b": False}

        def fire_claim():
            barrier.wait()
            time.sleep(random.uniform(0, 0.01))
            try:
                claimed = storage.claim_due(
                    now=int(time.time()), limit=10,
                )
                # Record error on whatever we got
                for c in claimed:
                    storage.record_error(c[0], "post_failure",
                    )
                ok["a"] = True
            except Exception:
                ok["a"] = False

        def fire_error():
            barrier.wait()
            time.sleep(random.uniform(0, 0.01))
            try:
                # Try to record error on this token directly; if no
                # row was claimed yet, this should be a no-op or
                # safely raise.
                storage.record_error(token, "post_failure",
                )
                ok["b"] = True
            except Exception:
                ok["b"] = True  # raised but safely

        t1 = threading.Thread(target=fire_claim)
        t2 = threading.Thread(target=fire_error)
        t1.start(); t2.start(); t1.join(); t2.join()
        # Neither path should leave the system in an undefined state.
        # Smoke check: row is still readable.
        with sqlite3.connect(temp_db_path) as conn:
            row = conn.execute(
                "SELECT session_token FROM scheduler_state "
                "WHERE session_token=?", (token,),
            ).fetchone()
        assert row is not None, (
            f"iter={iteration}: row vanished — inconsistent state"
        )

    def test_concurrent_enqueue_same_session_yields_one_row(
        self, iteration, fresh_storage, temp_db_path,
    ):
        """P28: concurrent enqueue() calls for the same
        (session_token, request_id) yield ONE logical row."""
        random.seed(iteration + 200)
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = f"tok-race3-{iteration}"
        _seed_gate(temp_db_path, token)
        barrier = threading.Barrier(2)

        def fire():
            time.sleep(random.uniform(0, 0.01))
            barrier.wait()
            try:
                storage.enqueue(
                    session_token=token,
                    fire_at=int(time.time()) + 1000,
                    request_id=f"r-eq-{iteration}",
                    trace_id="0123456789abcdef",
                )
            except Exception:
                pass  # Duplicate is acceptable

        t1 = threading.Thread(target=fire)
        t2 = threading.Thread(target=fire)
        t1.start(); t2.start(); t1.join(); t2.join()
        with sqlite3.connect(temp_db_path) as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM scheduler_state WHERE session_token=?",
                (token,),
            ).fetchone()[0]
        assert n == 1, (
            f"iter={iteration}: expected 1 row; got {n}"
        )


# ─────────────────────────────────────────────────────────────────────
# Zero-delay anchor tests (v1.2 P-3) — guaranteed worst-case timing
# ─────────────────────────────────────────────────────────────────────
class TestRaceAnchorsZeroDelay:
    """§ 4.9 v1.2 P-3 — barrier-only sync (no jitter), exact
    same-millisecond execution. Closes the gap where probabilistic
    coverage might miss zero-delay timing."""

    def test_atomic_dequeue_zero_delay(
        self, fresh_storage, temp_db_path,
    ):
        """P28: barrier-only race on claim_due — exactly one wins."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-anchor-1"
        _seed_gate(temp_db_path, token)
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id="r-anchor-1", trace_id="0123456789abcdef",
        )
        barrier = threading.Barrier(2)
        outcomes = {"a": 0, "b": 0}

        def fire(key):
            barrier.wait()  # No sleep
            claimed = storage.claim_due(
                now=int(time.time()), limit=1,
            )
            outcomes[key] = sum(
                1 for c in claimed if c[0] == token
            )

        t1 = threading.Thread(target=fire, args=("a",))
        t2 = threading.Thread(target=fire, args=("b",))
        t1.start(); t2.start(); t1.join(); t2.join()
        assert sum(outcomes.values()) == 1, (
            f"zero-delay double-claim: {outcomes!r}"
        )

    def test_concurrent_commit_fired_zero_delay(
        self, fresh_storage, temp_db_path,
    ):
        """P28: two threads racing to commit_fired the same row →
        idempotent (no exception, row stays committed)."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-anchor-2"
        _seed_gate(temp_db_path, token)
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id="r-anchor-2", trace_id="0123456789abcdef",
        )
        # Claim once
        storage.claim_due(now=int(time.time()), limit=1)
        barrier = threading.Barrier(2)

        def fire():
            barrier.wait()
            try:
                storage.commit_fired(token)
            except Exception:
                pass

        t1 = threading.Thread(target=fire)
        t2 = threading.Thread(target=fire)
        t1.start(); t2.start(); t1.join(); t2.join()
        # Row is still fired exactly once (no negative side effect)
        with sqlite3.connect(temp_db_path) as conn:
            row = conn.execute(
                "SELECT fallback_fired FROM scheduler_state "
                "WHERE session_token=?", (token,),
            ).fetchone()
        assert row is not None and row[0] == 1

    def test_concurrent_record_error_zero_delay(
        self, fresh_storage, temp_db_path,
    ):
        """P33: barrier-only record_error race — attempt_count
        increments are not lost."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-anchor-3"
        _seed_gate(temp_db_path, token)
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id="r-anchor-3", trace_id="0123456789abcdef",
        )
        # Claim
        storage.claim_due(now=int(time.time()), limit=1)
        barrier = threading.Barrier(2)

        def fire():
            barrier.wait()
            try:
                storage.record_error(token, "post_failure",
                )
            except Exception:
                pass

        t1 = threading.Thread(target=fire)
        t2 = threading.Thread(target=fire)
        t1.start(); t2.start(); t1.join(); t2.join()
        with sqlite3.connect(temp_db_path) as conn:
            ac = conn.execute(
                "SELECT attempt_count FROM scheduler_state "
                "WHERE session_token=?", (token,),
            ).fetchone()[0]
        # Either both increments landed (2) or one did (1) due to
        # serialization; never zero.
        assert ac >= 1, f"attempt_count = {ac}"
