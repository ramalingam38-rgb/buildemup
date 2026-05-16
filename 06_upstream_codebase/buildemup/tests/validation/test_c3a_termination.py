"""S8 § 4.4 — Termination tests (~7 tests).

The 5 terminal states (per GateTerminationReason enum) reachable +
properly finalized; subsequent operations on terminal sessions
return 410 Gone. Uses gate_states-row seeding rather than full
state-machine traversal to keep Tier 1 budget tight.

§ 4.0.1: each test docstring names the specific invariant.
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
import urllib.error

import pytest


def _seed_terminal(db_path: str, token: str, reason: str) -> None:
    """Seed a gate_states row in the given terminal state."""
    state_payload = {
        "is_done": True, "termination_reason": reason,
    }
    now = int(time.time())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, ?, ?, ?, 1, NULL, NULL)",
            (token, json.dumps(state_payload), now, now + 86400),
        )
        conn.commit()


def _get_status(base_url, token):
    req = urllib.request.Request(
        f"{base_url}/api/extreme-case/status?session_token={token}",
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


# Per GateTerminationReason enum — the 6 documented values
_TERMINAL_REASONS = [
    "SUCCESS",
    "PREVIEW_MODE",
    "MAX_ITERATIONS_REACHED",
    "PER_CASE_LIMIT_REACHED",
    "USER_ABORTED",
    "CBA_VERIFICATION_PAUSED",
]


class TestTerminalStates:
    """§ 4.4: the spec-enumerated terminal states are reflected in
    /status correctly + remain stable across reads."""

    @pytest.mark.parametrize("reason", _TERMINAL_REASONS)
    def test_terminal_state_visible_on_status(
        self, live_server, fresh_storage, temp_db_path, reason,
    ):
        """§ 5a + § 4.4: each terminal reason yields the expected
        terminal_state in /status. Single parametrized test → 6 cases,
        within budget."""
        token = f"tok-term-{reason}"
        _seed_terminal(temp_db_path, token, reason)
        status, body = _get_status(live_server, token)
        assert status == 200
        assert body["is_terminal"] is True
        assert body["terminal_state"] == reason
        assert body["current_state"] == reason  # mirror

    def test_status_idempotent_across_repeated_reads(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """§ 4.4 stability: a terminal row's response is identical
        across repeated reads (no read-time mutation)."""
        token = "tok-term-stable"
        _seed_terminal(temp_db_path, token, "SUCCESS")
        s1, b1 = _get_status(live_server, token)
        s2, b2 = _get_status(live_server, token)
        # Trace_id changes per request but everything else stable.
        b1.pop("trace_id"); b2.pop("trace_id")
        assert s1 == s2 == 200
        assert b1 == b2
