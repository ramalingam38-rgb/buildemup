"""S7b § 7.5 + § 8.1 — Admin reset endpoint (P35) tests.

Three tests covering the three documented outcomes of `reset()`:
RESET (a stuck row clears and is re-claimable next tick),
ALREADY_FIRED (committed rows cannot be un-fired; 409),
NOT_FOUND (unknown token → 404). Auth-failure 401 inherits coverage
from the tick endpoint's auth tests per spec § 8.1 (line 1561).
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
import unittest
import uuid

# Set admin token before any module that reads env at import time.
os.environ.setdefault("BUILDEMUP_ADMIN_TOKEN", "test-admin-token-1234567890")

from buildemup.api import admin_endpoint
from buildemup.utils.scheduler_state_storage import SchedulerStateStorage


_ADMIN_TOKEN = "test-admin-token-1234567890"
_AUTH_HEADERS = {"X-Admin-Token": _ADMIN_TOKEN}


def _seed_gate_states_row(db_path: str, token: str) -> None:
    """Insert a minimal gate_states row so FK can be satisfied."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, ?, ?, ?, 0, NULL, NULL)",
            (token, '{}', int(time.time()), int(time.time()) + 86400),
        )
        conn.commit()


class TestAdminReset(unittest.TestCase):
    """P35 admin reset endpoint outcomes."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="reset-test-")
        self.db_path = os.path.join(self._tmpdir, "reset.db")
        self.storage = SchedulerStateStorage(db_path=self.db_path)
        admin_endpoint.reset_scheduler_storage_for_tests(self.storage)
        # Ensure env var matches what the handler will compare against
        os.environ["BUILDEMUP_ADMIN_TOKEN"] = _ADMIN_TOKEN

    def tearDown(self):
        admin_endpoint.reset_scheduler_storage_for_tests(None)

    def test_stuck_row_resets_and_is_reclaimable_next_tick(self):
        """P35: stuck row → reset → was_stuck=True; row eligible again.

        Also asserts the cleared fields: attempt_count = 0,
        last_attempt_at = NULL, fallback_error = NULL. After reset,
        a fresh tick with cooldown elapsed picks the row up again.
        """
        token = uuid.uuid4().hex
        _seed_gate_states_row(self.db_path, token)
        self.storage.enqueue(
            session_token=token,
            fire_at=int(time.time()) - 60,
            request_id="req-stuck",
            trace_id="0123456789abcdef",
        )
        # Force to stuck state (attempt_count = 3, last_attempt_at set,
        # fallback_error populated) by hand.
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE scheduler_state SET "
                " attempt_count = 3, "
                " last_attempt_at = ?, "
                " fallback_error = ? "
                "WHERE session_token = ?",
                (int(time.time()) - 1000, "post_exception: foo", token),
            )
            conn.commit()

        # Confirm count_stuck() sees it
        self.assertEqual(self.storage.count_stuck(), 1)

        # Reset
        status, body = admin_endpoint.handle_scheduler_reset(
            json.dumps({"session_token": token}).encode(),
            _AUTH_HEADERS,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["was_stuck"])
        self.assertEqual(body["prior_attempt_count"], 3)
        self.assertEqual(body["prior_fallback_error"], "post_exception: foo")

        # Row state cleared
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT attempt_count, last_attempt_at, fallback_error "
                "FROM scheduler_state WHERE session_token = ?",
                (token,),
            ).fetchone()
        self.assertEqual(row, (0, None, None))

        # count_stuck → 0; row eligible for re-claim (was due, fired=0,
        # attempt_count=0, no last_attempt_at).
        self.assertEqual(self.storage.count_stuck(), 0)
        rows = self.storage.claim_due(int(time.time()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], token)

    def test_already_fired_row_returns_409_unchanged(self):
        """ALREADY_FIRED → 409; un-firing a committed row is forbidden.

        Refusing this is intentional — if a fallback was committed,
        the user already received the conservative-default response
        and the orchestrator already moved on. Resetting it would let
        the tick fire AGAIN, contradicting P21 idempotency.
        """
        token = uuid.uuid4().hex
        _seed_gate_states_row(self.db_path, token)
        self.storage.enqueue(
            session_token=token,
            fire_at=int(time.time()) - 60,
            request_id="req-fired",
            trace_id=None,
        )
        # Mark fired
        self.storage.commit_fired(token)
        # Snapshot pre-state to verify it's unchanged after the 409
        with sqlite3.connect(self.db_path) as conn:
            pre = conn.execute(
                "SELECT fallback_fired, attempt_count, fallback_error "
                "FROM scheduler_state WHERE session_token = ?",
                (token,),
            ).fetchone()

        status, body = admin_endpoint.handle_scheduler_reset(
            json.dumps({"session_token": token}).encode(),
            _AUTH_HEADERS,
        )
        self.assertEqual(status, 409)
        self.assertFalse(body["ok"])
        self.assertEqual(body["code"], "already_fired")

        # Row state unchanged
        with sqlite3.connect(self.db_path) as conn:
            post = conn.execute(
                "SELECT fallback_fired, attempt_count, fallback_error "
                "FROM scheduler_state WHERE session_token = ?",
                (token,),
            ).fetchone()
        self.assertEqual(pre, post)

    def test_unknown_token_returns_404(self):
        """NOT_FOUND → 404 with code unknown_token. No row created."""
        status, body = admin_endpoint.handle_scheduler_reset(
            json.dumps({"session_token": "no-such-token-zzz"}).encode(),
            _AUTH_HEADERS,
        )
        self.assertEqual(status, 404)
        self.assertFalse(body["ok"])
        self.assertEqual(body["code"], "unknown_token")
        # Confirm reset did NOT side-effect-insert a row
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM scheduler_state",
            ).fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
