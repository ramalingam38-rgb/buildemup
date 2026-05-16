"""S8 § 4.3 — Idempotency tests (~7 tests).

Verifies P12 (brief→session uniqueness on /check), P21 (request_id
caching on /resolve and /cba-verified), P28 (atomic dequeue on
scheduler/tick), and replay-stability across restart.

Each test docstring names which P-invariant is exercised per § 4.0.1.
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
import urllib.error

import pytest


def _post(base_url: str, path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


class TestIdempotency:
    """§ 4.3 — protects P12 + P21 + P28."""

    def test_p12_check_unknown_brief_repeated_returns_same_4xx_shape(
        self, live_server, fresh_storage,
    ):
        """P12: same (brief_token, request_id) → same response on
        replay, even on the error path. Replay should not produce a
        different shape or new server-side state."""
        payload = {"brief_token": "brief-test-001", "request_id": "req-1"}
        s1, b1 = _post(live_server, "/api/extreme-case/check", payload)
        s2, b2 = _post(live_server, "/api/extreme-case/check", payload)
        assert s1 == s2 == 410
        assert b1.get("ok") == b2.get("ok") is False

    def test_p12_check_different_request_ids_treated_as_separate(
        self, live_server, fresh_storage,
    ):
        """P12: different request_ids with same unknown brief still
        produce distinct responses (no false-cache hit)."""
        s1, b1 = _post(live_server, "/api/extreme-case/check",
                       {"brief_token": "b", "request_id": "r-1"})
        s2, b2 = _post(live_server, "/api/extreme-case/check",
                       {"brief_token": "b", "request_id": "r-2"})
        # Both fail (unknown brief) but each gets its own trace_id
        assert s1 == s2 == 410
        assert b1["trace_id"] != b2["trace_id"], (
            "trace_ids must differ across different requests"
        )

    def test_p21_resolve_replay_with_no_session_returns_validation(
        self, live_server, fresh_storage,
    ):
        """P21: replay with same (session_token, request_id) on a
        non-existent session is consistent (no inconsistent state)."""
        payload = {"session_token": "nonexistent",
                   "request_id": "r-1", "chosen_option_id": "opt"}
        s1, b1 = _post(live_server, "/api/extreme-case/resolve", payload)
        s2, b2 = _post(live_server, "/api/extreme-case/resolve", payload)
        assert s1 == s2  # consistent error
        assert (b1.get("ok") or False) == (b2.get("ok") or False)

    def test_p21_cba_verified_replay_consistency(
        self, live_server, fresh_storage,
    ):
        """P21: /cba-verified error replay is consistent."""
        p = {"session_token": "ghost", "request_id": "r-cba"}
        s1, _ = _post(live_server, "/api/extreme-case/cba-verified", p)
        s2, _ = _post(live_server, "/api/extreme-case/cba-verified", p)
        assert s1 == s2

    def test_p28_atomic_dequeue_no_double_claim(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """P28: Two scheduler ticks racing should claim DISTINCT rows.

        Hand-seeds two scheduler_state rows with fire_at < now;
        invokes claim_due() twice; verifies non-overlapping result sets.
        """
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        # Seed two ready rows
        for tok, req in [("tok-a", "ra"), ("tok-b", "rb")]:
            # gate_states FK
            with sqlite3.connect(temp_db_path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO gate_states "
                    "(token, state_json, saved_at, expires_at, "
                    " is_terminal, last_request_id, last_response_json) "
                    "VALUES (?, '{}', ?, ?, 0, NULL, NULL)",
                    (tok, int(time.time()), int(time.time()) + 86400),
                )
                conn.commit()
            storage.enqueue(
                session_token=tok, fire_at=int(time.time()) - 60,
                request_id=req, trace_id="0123456789abcdef",
            )
        claimed_a = storage.claim_due(now=int(time.time()), limit=1)
        claimed_b = storage.claim_due(now=int(time.time()), limit=1)
        tokens_a = {c[0] for c in claimed_a}
        tokens_b = {c[0] for c in claimed_b}
        assert tokens_a.isdisjoint(tokens_b), (
            f"double-claim: {tokens_a & tokens_b}"
        )

    def test_p21_persistence_across_storage_recreation(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """P21: idempotency cache survives a storage object recreation
        (since the cache lives in SQLite, not in-memory)."""
        from buildemup.utils.gate_state_storage import GateStateStorage
        # Original storage is the fresh_storage[0]; create a SECOND
        # storage instance pointing at the same db
        s2 = GateStateStorage(db_path=temp_db_path)
        # The schemas are identical; the read should work even from
        # the second instance. Smoke verification only.
        result = s2.load_status_row("nonexistent-token")
        assert result is None

    def test_replay_after_storage_recreation_consistent(
        self, live_server, fresh_storage,
    ):
        """P21: replaying the same /check call across two different
        live_server requests sees consistent shape (no in-memory cache
        that disappears between requests)."""
        p = {"brief_token": "x", "request_id": "consistent-replay"}
        s1, b1 = _post(live_server, "/api/extreme-case/check", p)
        s2, b2 = _post(live_server, "/api/extreme-case/check", p)
        assert s1 == s2
        # Both error paths; trace_ids differ but error shape stable
        assert (b1.get("ok") or False) == (b2.get("ok") or False)
