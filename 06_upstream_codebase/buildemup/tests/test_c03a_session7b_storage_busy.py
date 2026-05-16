"""S7b § 6.2 + § 8.4 — storage_busy 503 + /health scheduler write tests.

Five tests:
  1. handle_check returns 3-tuple (status, body, headers) on lock.
  2. handle_resolve same.
  3. Non-lock OperationalError still propagates (does NOT 503).
  4. server.py end-to-end: HTTP 503 + Retry-After header surfaces.
  5. /health scheduler write check: sentinel INSERT runs and rolls back
     (table contents unchanged after handle_health).
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from unittest.mock import patch

from buildemup.api import c3a_endpoint
from buildemup.api import health_endpoint
from buildemup.api import server as server_mod
from buildemup.utils.scheduler_state_storage import SchedulerStateStorage


class TestStorageBusyHandlerSurface(unittest.TestCase):
    """§ 6.2 — wrappers translate SQLite lock-busy into HTTP 503."""

    def test_handle_check_database_locked_returns_503_three_tuple(self):
        """OperationalError('database is locked') → 503 with Retry-After."""
        def _raise_locked(request_body, trace_id):
            raise sqlite3.OperationalError("database is locked")

        with patch.object(c3a_endpoint, "_handle_check_inner",
                          side_effect=_raise_locked):
            result = c3a_endpoint.handle_check(b'{"x": 1}')

        self.assertEqual(len(result), 3, "expected 3-tuple on storage_busy")
        status, body, headers = result
        self.assertEqual(status, 503)
        self.assertFalse(body["ok"])
        self.assertEqual(body["code"], "storage_busy")
        self.assertEqual(body["retry_after_seconds"], 5)
        self.assertIn("trace_id", body)
        self.assertEqual(headers, {"Retry-After": "5"})

    def test_handle_resolve_database_locked_returns_503(self):
        """Same path on the resolve handler — wrapper is uniform."""
        def _raise_locked(request_body, trace_id):
            raise sqlite3.OperationalError(
                "DATABASE IS LOCKED",  # mixed case OK (matched lower)
            )

        with patch.object(c3a_endpoint, "_handle_resolve_inner",
                          side_effect=_raise_locked):
            result = c3a_endpoint.handle_resolve(b'{"x": 1}')

        self.assertEqual(len(result), 3)
        status, body, headers = result
        self.assertEqual(status, 503)
        self.assertEqual(body["code"], "storage_busy")
        self.assertEqual(headers["Retry-After"], "5")

    def test_non_lock_operational_error_propagates_unchanged(self):
        """Other OperationalErrors (corruption, etc.) MUST re-raise.

        This is the contract that says only the well-known lock-busy
        message gets the 503 treatment; anything else is a genuine
        bug and should be visible to the upstream handler / monitoring.
        """
        def _raise_other(request_body, trace_id):
            raise sqlite3.OperationalError("disk image malformed")

        with patch.object(c3a_endpoint, "_handle_check_inner",
                          side_effect=_raise_other):
            with self.assertRaises(sqlite3.OperationalError) as cm:
                c3a_endpoint.handle_check(b'{"x": 1}')
        self.assertIn("malformed", str(cm.exception))


class TestStorageBusyServerEndToEnd(unittest.TestCase):
    """server.py surfaces the 3-tuple as HTTP 503 + Retry-After header."""

    def setUp(self):
        # Pick a free port
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        self.port = sock.getsockname()[1]
        sock.close()
        self.srv = HTTPServer(
            ("127.0.0.1", self.port), server_mod.BriefCaptureHandler,
        )
        self.thread = threading.Thread(
            target=self.srv.serve_forever, daemon=True,
        )
        self.thread.start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def test_server_surfaces_503_with_retry_after_header(self):
        """End-to-end: lock-busy from inner → HTTP 503 + Retry-After: 5.

        Verifies that server.py's `_unpack_handler_result` correctly
        decomposes the 3-tuple AND that `_send_json` correctly emits
        the extra header before `end_headers()`.
        """
        def _raise_locked(request_body, trace_id):
            raise sqlite3.OperationalError("database is locked")

        with patch.object(c3a_endpoint, "_handle_check_inner",
                          side_effect=_raise_locked):
            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/extreme-case/check",
                data=b'{"x": 1}',
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    self.fail(f"expected 503; got {resp.status}")
            except urllib.error.HTTPError as e:
                status = e.code
                body = json.loads(e.read())
                hdrs = dict(e.headers)

        self.assertEqual(status, 503)
        self.assertEqual(body["code"], "storage_busy")
        self.assertEqual(body["retry_after_seconds"], 5)
        # Header lookup is case-insensitive per HTTP; urllib normalizes
        # to title-case in the dict.
        retry = hdrs.get("Retry-After") or hdrs.get("retry-after")
        self.assertEqual(retry, "5")


class TestHealthSchedulerWritePath(unittest.TestCase):
    """§ 8.4 — /health (b) scheduler_state INSERT-and-ROLLBACK."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="health-write-")
        self.db_path = os.path.join(self._tmpdir, "h.db")
        self.storage = SchedulerStateStorage(db_path=self.db_path)
        health_endpoint.reset_scheduler_storage_for_tests(self.storage)

    def tearDown(self):
        health_endpoint.reset_scheduler_storage_for_tests(None)

    def test_health_check_does_not_leave_sentinel_in_table(self):
        """Sentinel INSERT must roll back; table contents unchanged.

        Before: 0 rows (or N user rows).
        Run handle_health() many times.
        After: still 0 rows (or N user rows). No sentinel persists.
        """
        # Snapshot row count before
        with sqlite3.connect(self.db_path) as conn:
            before = conn.execute(
                "SELECT COUNT(*) FROM scheduler_state",
            ).fetchone()[0]

        # Run health check 10 times
        for _ in range(10):
            status, body = health_endpoint.handle_health(db_path=self.db_path)
            self.assertEqual(status, 200, body)
            self.assertTrue(body["scheduler_writable"])

        # Snapshot row count after; must equal before
        with sqlite3.connect(self.db_path) as conn:
            after = conn.execute(
                "SELECT COUNT(*) FROM scheduler_state",
            ).fetchone()[0]
            # Specifically: sentinel token must NOT be present.
            sentinel_count = conn.execute(
                "SELECT COUNT(*) FROM scheduler_state "
                "WHERE session_token = ?",
                (health_endpoint._HEALTH_SENTINEL_TOKEN,),
            ).fetchone()[0]

        self.assertEqual(after, before, "row count drifted post-health")
        self.assertEqual(sentinel_count, 0, "sentinel leaked into table")


if __name__ == "__main__":
    unittest.main()
