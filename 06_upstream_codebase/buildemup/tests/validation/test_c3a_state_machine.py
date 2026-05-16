"""S8 § 4.2 — C3a state machine traversal tests (~10 tests).

Walks the C3a state machine via HTTP. Includes three "raw" cross-check
tests (round 2 X4) that hand-write field assertions WITHOUT using
_contract.py — these are the ground-truth spec contract that catches
drift in the centralized helpers.

Each test docstring names the specific invariant per § 4.0.1 hygiene.
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
import urllib.error

import pytest

from buildemup.tests.validation import _contract


# ─── HTTP helpers ────────────────────────────────────────────────────
def _post_json(base_url: str, path: str, payload: dict, *,
               headers: dict | None = None):
    data = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(
        f"{base_url}{path}", data=data, headers=h, method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def _get_json(base_url: str, path: str, *, headers: dict | None = None):
    req = urllib.request.Request(f"{base_url}{path}",
                                  headers=headers or {})
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def _seed_state_row(db_path: str, token: str, *,
                     is_terminal: bool = False,
                     termination_reason: str | None = None) -> None:
    state_payload = {
        "is_done": is_terminal,
        "termination_reason": termination_reason,
    }
    now = int(time.time())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, ?, ?, ?, ?, NULL, NULL)",
            (token, json.dumps(state_payload), now, now + 86400,
             1 if is_terminal else 0),
        )
        conn.commit()


# ─── Tests ───────────────────────────────────────────────────────────
class TestStateMachineHTTP:
    """§ 4.2 — happy-path traversal entry points via HTTP."""

    def test_check_with_unknown_brief_returns_410(
        self, live_server, fresh_storage,
    ):
        """§ 5.1 + § 6.5: /check with brief_token that doesn't exist
        returns 410 unknown_or_expired — protects the C2 entry boundary."""
        status, body = _post_json(
            live_server, "/api/extreme-case/check",
            {"brief_token": "nonexistent", "request_id": "req-1"},
        )
        assert status == 410
        _contract.assert_validation_error(body)

    def test_check_with_missing_required_fields_returns_400(
        self, live_server, fresh_storage,
    ):
        """§ 6.5: /check with empty body fails per-field validation."""
        status, body = _post_json(
            live_server, "/api/extreme-case/check", {},
        )
        assert status == 400
        _contract.assert_validation_error(body)

    def test_resolve_with_unknown_session_returns_validation(
        self, live_server, fresh_storage,
    ):
        """§ 5.2: /resolve with unknown session_token → 4xx."""
        status, body = _post_json(
            live_server, "/api/extreme-case/resolve",
            {"session_token": "ghost", "request_id": "r",
             "chosen_option_id": "opt"},
        )
        assert status >= 400 and status < 500
        _contract.assert_validation_error(body)

    def test_abort_on_unknown_session_returns_validation(
        self, live_server, fresh_storage,
    ):
        """§ 5.3: /abort idempotent error path."""
        status, body = _post_json(
            live_server, "/api/extreme-case/abort",
            {"session_token": "ghost", "request_id": "r"},
        )
        assert status >= 400 and status < 500
        _contract.assert_validation_error(body)

    def test_state_transition_visible_via_status(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """§ 5a + § 4.2: a row marked is_terminal=1 is reflected in
        /status.is_terminal (state-machine visibility check)."""
        token = "tok-trans-001"
        _seed_state_row(temp_db_path, token, is_terminal=False)
        status, body = _get_json(
            live_server, f"/api/extreme-case/status?session_token={token}",
        )
        assert status == 200
        assert body["is_terminal"] is False

        # Mark terminal directly via storage; observe via status
        from buildemup.api.c3a_endpoint import _get_storage
        _get_storage().mark_terminal(token)
        # Also bump is_terminal flag on the row
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute(
                "UPDATE gate_states SET is_terminal=1 WHERE token=?",
                (token,),
            )
            conn.commit()

        status2, body2 = _get_json(
            live_server, f"/api/extreme-case/status?session_token={token}",
        )
        assert status2 == 200
        assert body2["is_terminal"] is True

    def test_check_init_to_check_response_shape_parity(
        self, live_server, fresh_storage,
    ):
        """§ 5b.3: GET /check-init with browser UA returns the SAME
        validation-error shape as POST /check would on equivalent input
        (parity verification — wrappers match)."""
        post_status, post_body = _post_json(
            live_server, "/api/extreme-case/check", {},
        )
        get_status, get_body = _get_json(
            live_server,
            "/api/extreme-case/check-init",
            headers={"User-Agent":
                     "Mozilla/5.0 (X11; Linux) Chrome/124.0"},
        )
        # Both empty-input → 400 + validation error shape
        assert post_status == 400
        assert get_status == 400
        _contract.assert_validation_error(post_body)
        _contract.assert_validation_error(get_body)

    def test_status_404_then_seed_then_200(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """§ 5a: status returns 404 before seed, 200 after — verifies
        the read path picks up new rows (no stale-cache bug)."""
        token = "tok-late-001"
        s1, _ = _get_json(
            live_server, f"/api/extreme-case/status?session_token={token}",
        )
        assert s1 == 404
        _seed_state_row(temp_db_path, token)
        s2, body = _get_json(
            live_server, f"/api/extreme-case/status?session_token={token}",
        )
        assert s2 == 200
        assert body["session_token"] == token


# ─── Raw cross-check tests (§ 4.0 round 2 X4) ───────────────────────
# These deliberately do NOT call _contract.* helpers; they hand-write
# every assertion. If _contract.py forgets a field, these tests catch
# the drift.
class TestRawCrossChecks:
    """§ 4.0 round 2 X4: ground-truth contract verification.

    Three raw assertion tests — one per the highest-risk endpoints
    (check, resolve, status). If a _contract.assert_*_response()
    helper grows a bug (forgets to assert a field), these still
    fail because they are not coupled to that helper.
    """

    def test_check_response_shape_raw(self, live_server, fresh_storage):
        """§ 5.1 raw: /check error path. Hand-asserts every field."""
        status, body = _post_json(
            live_server, "/api/extreme-case/check", {},
        )
        # Hand-written, NOT _contract.assert_*
        assert status == 400
        assert isinstance(body, dict)
        assert body.get("ok") is False
        assert "errors" in body
        assert isinstance(body["errors"], list)
        assert len(body["errors"]) >= 1
        for e in body["errors"]:
            assert "code" in e and isinstance(e["code"], str)
            assert "message" in e and isinstance(e["message"], str)
        assert "trace_id" in body
        import re
        assert re.match(r"^[0-9a-f]{16}$", body["trace_id"])

    def test_resolve_response_shape_raw(self, live_server, fresh_storage):
        """§ 5.2 raw: /resolve error path."""
        status, body = _post_json(
            live_server, "/api/extreme-case/resolve", {},
        )
        assert status == 400
        assert body.get("ok") is False
        assert "errors" in body and isinstance(body["errors"], list)
        for e in body["errors"]:
            assert "code" in e
            assert "message" in e
        assert "trace_id" in body
        import re
        assert re.match(r"^[0-9a-f]{16}$", body["trace_id"])

    def test_status_response_shape_raw(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """§ 5a raw: /status success path."""
        token = "tok-raw-status"
        _seed_state_row(temp_db_path, token, is_terminal=False)
        status, body = _get_json(
            live_server, f"/api/extreme-case/status?session_token={token}",
        )
        # Hand-written, every required field
        assert status == 200
        assert body.get("ok") is True
        assert body.get("session_token") == token
        assert "current_state" in body and isinstance(
            body["current_state"], str)
        assert body.get("terminal_state") is None
        assert body.get("is_terminal") is False
        assert "last_updated_at" in body
        assert isinstance(body["last_updated_at"], (int, float))
        assert "trace_id" in body
        import re
        assert re.match(r"^[0-9a-f]{16}$", body["trace_id"])
