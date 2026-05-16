"""Tests for Component 3a Session 7a — gate state storage layer.

Covers S7a SPEC v1.0 LOCKED § 8.7 TestStorage:
  - test_save_resume_round_trip
  - test_token_collision_retry (via fresh-token semantics)
  - test_expired_token_returns_TokenNotFoundError
  - test_terminal_state_marked_is_terminal_in_db
  - test_terminal_state_NOT_deleted (P4)
  - test_wal_mode_enabled_on_connection (P5)
  - test_concurrent_write_retry_succeeds (P5)
  - test_idempotency_cache_stored_atomically (P2 + P13)
  - test_brief_to_session_uniqueness_prevents_duplicate_check (P12)
  - test_state_and_cache_co_written_atomically (P13)

The single-flight lock test (P11) lives in
test_c03a_session7_api_endpoints.py because it requires the handler
wrapper around the lock.

The deterministic-JSON test (P14) lives in
test_c03a_session7_serialization.py.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import time
import unittest

from buildemup.components.c03a.gate_state import GateState
from buildemup.components.c03a_extreme_case_gate import ExtremeCaseGate
from buildemup.tests.test_c03a_session6_orchestrator_happy import (
    _DetectorPatch,
    _case,
    _make_brief,
    _make_gap_analysis,
    _make_runner,
)
from buildemup.domain.extreme_case import ExtremeCaseId
from buildemup.utils.gate_state_storage import (
    GateStateStorage,
    PayloadTooLargeError,
    TokenNotFoundError,
    new_token,
)


def _build_initial_state(session_id: str = "test-token-aa") -> GateState:
    """Build an in-progress GateState via the real S6 orchestrator."""
    case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
    gap = _make_gap_analysis()
    runner, _ = _make_runner(gap)
    gate = ExtremeCaseGate(c2_runner=runner)
    with _DetectorPatch([(case,)]):
        return gate.start(session_id=session_id, brief=_make_brief())


def _build_terminal_state(session_id: str = "test-token-bb") -> GateState:
    """Build a terminal SUCCESS GateState."""
    case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
    gap = _make_gap_analysis()
    runner, _ = _make_runner(gap)
    gate = ExtremeCaseGate(c2_runner=runner)
    with _DetectorPatch([(case,), ()]):
        s0 = gate.start(session_id=session_id, brief=_make_brief())
        s1 = gate.apply_user_decision(
            state=s0,
            case_id=case.case_id,
            chosen_option_id=case.options[0].option_id,
            user_acknowledged_at="2026-05-01T12:00:00Z",
        )
    return s1


class _TmpStorageMixin:
    """Set up GateStateStorage on a temp DB file, isolated per test."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = os.path.join(self._tmpdir, "gate_states.db")
        self.storage = GateStateStorage(db_path=self._db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)


class TestSaveResumeRoundTrip(_TmpStorageMixin, unittest.TestCase):
    def test_save_resume_round_trip(self):
        state = _build_initial_state()
        token = self.storage.save(state)
        resumed_state, last_req, last_resp = self.storage.resume(token)
        # Structural equivalence per P1.
        self.assertEqual(resumed_state.to_dict(), state.to_dict())
        self.assertIsNone(last_req)
        self.assertIsNone(last_resp)

    def test_save_with_request_id_and_response_caches_them(self):
        state = _build_initial_state()
        resp = {"ok": True, "session_token": state.session_id}
        token = self.storage.save(state, request_id="req-1", response=resp)
        _state, last_req, last_resp = self.storage.resume(token)
        self.assertEqual(last_req, "req-1")
        self.assertEqual(last_resp, resp)


class TestTokenLookup(_TmpStorageMixin, unittest.TestCase):
    def test_unknown_token_raises_TokenNotFoundError(self):
        with self.assertRaises(TokenNotFoundError):
            self.storage.resume("does-not-exist-token-xyz")

    def test_expired_token_returns_TokenNotFoundError(self):
        # Save then artificially expire by patching expires_at directly
        state = _build_initial_state()
        token = self.storage.save(state)
        # Force expiry by direct DB update
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "UPDATE gate_states SET expires_at = ? WHERE token = ?",
                (time.time() - 1.0, token),
            )
            conn.commit()
        with self.assertRaises(TokenNotFoundError):
            self.storage.resume(token)


class TestTerminalStatePersistence(_TmpStorageMixin, unittest.TestCase):
    """P4 — terminal sessions are NOT deleted; only TTL prunes them."""

    def test_terminal_state_marked_is_terminal_in_db(self):
        state = _build_terminal_state()
        resp = {"ok": True, "is_done": True}
        token = self.storage.save(state, request_id="r1", response=resp)
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT is_terminal FROM gate_states WHERE token = ?",
                (token,),
            ).fetchone()
        self.assertEqual(row[0], 1)

    def test_terminal_state_NOT_deleted_on_save(self):
        state = _build_terminal_state()
        resp = {"ok": True, "is_done": True}
        token = self.storage.save(state, request_id="r1", response=resp)
        # Do another save to a DIFFERENT token; the prune sweep runs on
        # every save (BriefStorage pattern). Verify the terminal token
        # row is still there afterwards.
        other_state = _build_initial_state(session_id="other-token-cc")
        self.storage.save(other_state)
        # Original terminal row still reachable
        resumed, last_req, last_resp = self.storage.resume(token)
        self.assertTrue(resumed.is_done)
        self.assertEqual(last_req, "r1")
        self.assertEqual(last_resp, resp)


class TestWALMode(_TmpStorageMixin, unittest.TestCase):
    """P5 — SQLite WAL mode is enabled on each connection."""

    def test_wal_mode_enabled_on_connection(self):
        # Force a connection by saving anything
        state = _build_initial_state()
        self.storage.save(state)
        # Open a fresh connection to the same file and check journal_mode
        with sqlite3.connect(self._db_path) as conn:
            mode = conn.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
        self.assertEqual(mode.lower(), "wal")


class TestConcurrentWriteRetry(_TmpStorageMixin, unittest.TestCase):
    """P5 — _execute_with_retry handles transient SQLITE_BUSY."""

    def test_concurrent_writers_both_succeed(self):
        # Two threads save to different tokens concurrently. With WAL +
        # retry logic both should succeed without a "database is locked"
        # error reaching the caller.
        errors = []

        def worker(idx: int):
            try:
                state = _build_initial_state(session_id=f"tk-conc-{idx}")
                self.storage.save(state)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,))
                   for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [],
                         f"concurrent saves errored: {errors!r}")


class TestIdempotencyCacheAtomic(_TmpStorageMixin, unittest.TestCase):
    """P2 + P13 — request_id and response co-written atomically."""

    def test_save_existing_round_trips_state_and_cache(self):
        state0 = _build_initial_state()
        token = self.storage.save(state0, request_id=None, response=None)
        # Now an UPDATE via save_existing
        state1 = _build_terminal_state(session_id=token)
        new_resp = {"ok": True, "is_done": True, "termination": "SUCCESS"}
        self.storage.save_existing(
            token, state1, request_id="req-update-1", response=new_resp,
        )
        resumed, last_req, last_resp = self.storage.resume(token)
        # Per P1 structural equivalence
        self.assertEqual(resumed.to_dict(), state1.to_dict())
        self.assertEqual(last_req, "req-update-1")
        self.assertEqual(last_resp, new_resp)

    # B-043 fix landed in S7b (P19): the manual ROLLBACK in the
    # rowcount==0 branch was removed so the outer except clause is the
    # sole rollback path. TokenNotFoundError now propagates cleanly.
    def test_save_existing_unknown_token_raises(self):
        """P19 / B-043 — save_existing on an unknown token raises
        TokenNotFoundError (was masked by double-rollback before fix).
        """
        state = _build_initial_state()
        with self.assertRaises(TokenNotFoundError):
            self.storage.save_existing(
                "nonexistent-token-12345678",
                state,
                request_id="r1",
                response={"x": 1},
            )


class TestBriefToSessionUniqueness(_TmpStorageMixin, unittest.TestCase):
    """P12 — (brief_token, request_id) uniqueness for /check idempotency."""

    def test_register_returns_True_first_time(self):
        registered = self.storage.register_brief_session(
            brief_token="brief-aaa",
            request_id="req-1",
            session_token="sess-1",
        )
        self.assertTrue(registered)

    def test_register_returns_False_on_duplicate(self):
        self.storage.register_brief_session(
            brief_token="brief-aaa",
            request_id="req-1",
            session_token="sess-1",
        )
        registered_again = self.storage.register_brief_session(
            brief_token="brief-aaa",
            request_id="req-1",
            session_token="sess-2",  # different session_token
        )
        self.assertFalse(registered_again)
        # And lookup still returns the FIRST session_token
        winner = self.storage.lookup_brief_session(
            brief_token="brief-aaa", request_id="req-1",
        )
        self.assertEqual(winner, "sess-1")

    def test_brief_to_session_uniqueness_prevents_duplicate_check(self):
        """P12 round 2 #2: two threads call /check with same
        (brief_token, request_id); only one wins the registration; both
        observe the same session_token via lookup.
        """
        results: list = []
        barrier = threading.Barrier(4)

        def worker(idx: int):
            barrier.wait()
            session_token = f"sess-thread-{idx}"
            registered = self.storage.register_brief_session(
                brief_token="brief-shared",
                request_id="req-shared",
                session_token=session_token,
            )
            results.append((idx, registered, session_token))

        threads = [threading.Thread(target=worker, args=(i,))
                   for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one winner
        winners = [r for r in results if r[1] is True]
        self.assertEqual(len(winners), 1)
        # All threads see the same session_token via lookup
        winner_session = winners[0][2]
        for _ in range(4):
            looked_up = self.storage.lookup_brief_session(
                brief_token="brief-shared", request_id="req-shared",
            )
            self.assertEqual(looked_up, winner_session)


class TestStateAndCacheCoWriteAtomic(_TmpStorageMixin, unittest.TestCase):
    """P13 round 2 #4 — state + cache co-write is atomic.

    We can't easily fault-inject without monkey-patching sqlite3
    internals, so instead we verify the BEHAVIOURAL invariant: any
    successful resume() returns state and cache that came from the
    SAME save call (never split half-and-half).
    """

    def test_state_and_cache_co_written_atomically(self):
        # Sequence of saves with paired (state, request_id, response).
        # After each, resume() returns the matching pair — never an
        # interleaving like "old state + new cache".
        saves = []
        state0 = _build_initial_state()
        token = self.storage.save(
            state0, request_id="rA", response={"v": "A"},
        )
        saves.append((state0.to_dict(), "rA", {"v": "A"}))

        state1 = _build_terminal_state(session_id=token)
        self.storage.save_existing(
            token, state1, request_id="rB", response={"v": "B"},
        )
        saves.append((state1.to_dict(), "rB", {"v": "B"}))

        # Final resume must reflect the LAST save's pair, never a mix.
        resumed, last_req, last_resp = self.storage.resume(token)
        self.assertEqual(resumed.to_dict(), saves[-1][0])
        self.assertEqual(last_req, saves[-1][1])
        self.assertEqual(last_resp, saves[-1][2])


class TestPayloadTooLarge(_TmpStorageMixin, unittest.TestCase):
    """P9 storage-layer cap (mirrors handler-layer cap)."""

    def test_oversized_serialized_state_raises(self):
        # Build a state with a Brief carrying many additional_requirements
        # to push past 1 MB. We mutate an extreme_case to be huge via
        # the user_facing_message field (not validated for size).
        # Easier: just check the constant is enforced via a synthetic
        # GateState whose to_dict produces > 1 MB.
        from buildemup.utils.gate_state_storage import MAX_PAYLOAD_BYTES
        # Construct a fake state that serializes to > MAX_PAYLOAD_BYTES.
        state = _build_initial_state()
        # Replace user_facing_message on the head case with a huge string
        head_case = state.remaining_cases[0]
        from dataclasses import replace
        huge = "x" * (MAX_PAYLOAD_BYTES + 1024)
        bloated_case = replace(head_case, user_facing_message=huge)
        bloated_state = replace(
            state, remaining_cases=(bloated_case,) + state.remaining_cases[1:],
        )
        with self.assertRaises(PayloadTooLargeError):
            self.storage.save(bloated_state)


class TestNewToken(unittest.TestCase):
    def test_new_token_format(self):
        t = new_token()
        self.assertEqual(len(t), 24)
        # All hex chars
        int(t, 16)  # raises ValueError if not hex


if __name__ == "__main__":
    unittest.main()
