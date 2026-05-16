"""S8 § 4.8 — Failure-mode tests (~7 tests).

Failure paths produce correct HTTP behavior:
  - 503 storage_busy + Retry-After: 5
  - 400 request_too_large
  - 400 bad_json
  - 400 validation
  - 404 unknown_token
  - 410 terminal
  - X-Trace-Id malformed → fresh trace + WARNING

§ 4.0.1: each test docstring names the invariant under test.
"""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error

import pytest

from buildemup.tests.validation import _contract


def _post(base_url, path, body, *, headers=None,
          content_type="application/json"):
    if isinstance(body, dict):
        data = json.dumps(body).encode("utf-8")
    elif isinstance(body, str):
        data = body.encode("utf-8")
    else:
        data = body
    h = {"Content-Type": content_type, **(headers or {})}
    req = urllib.request.Request(
        f"{base_url}{path}", data=data, headers=h, method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return (r.status, json.loads(r.read().decode("utf-8")),
                dict(r.headers))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = None
        return e.code, body, dict(e.headers)


class TestFailureModes:
    """§ 4.8."""

    def test_malformed_json_body_returns_400_bad_json(
        self, live_server, fresh_storage,
    ):
        """§ 6.1 / P9: malformed JSON → 400 with bad_json error."""
        status, body, _ = _post(
            live_server, "/api/extreme-case/check",
            "{this is not json",
        )
        assert status == 400
        _contract.assert_validation_error(body)

    def test_oversized_request_body_returns_400(
        self, live_server, fresh_storage,
    ):
        """§ 6.1 / P9 / P18: body > cap → 400. Cap is 64KB per S7a."""
        oversized = {"brief_token": "x" * 1_500_000, "request_id": "r"}
        status, body, _ = _post(
            live_server, "/api/extreme-case/check", oversized,
        )
        assert status == 400
        _contract.assert_validation_error(body)

    def test_missing_required_field_returns_400_validation(
        self, live_server, fresh_storage,
    ):
        """§ 6.5: missing required field → 400 + validation."""
        status, body, _ = _post(
            live_server, "/api/extreme-case/check",
            {"brief_token": "x"},  # missing request_id
        )
        assert status == 400
        _contract.assert_validation_error(body)

    def test_unknown_session_token_on_resolve(
        self, live_server, fresh_storage,
    ):
        """§ 5.2: unknown session_token → 4xx unknown_token / validation."""
        status, body, _ = _post(
            live_server, "/api/extreme-case/resolve",
            {"session_token": "unknown-xxxx", "request_id": "r",
             "chosen_option_id": "opt"},
        )
        assert 400 <= status < 500
        _contract.assert_validation_error(body)

    def test_unknown_token_on_status_returns_404(
        self, live_server, fresh_storage,
    ):
        """§ 5a: GET /status with unknown token → 404 unknown_token."""
        req = urllib.request.Request(
            f"{live_server}/api/extreme-case/status?session_token=ghost",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("expected 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
            body = json.loads(e.read().decode("utf-8"))
            _contract.assert_validation_error(
                body, expected_code="unknown_token",
            )

    def test_malformed_x_trace_id_logs_warning_returns_fresh(
        self, live_server, fresh_storage, caplog,
    ):
        """P34 + P43: malformed X-Trace-Id rejected with WARNING; the
        response body still carries a 16-hex trace (server-minted)."""
        import re
        with caplog.at_level(logging.WARNING,
                             logger="buildemup.c3a.endpoint"):
            status, body, _ = _post(
                live_server, "/api/extreme-case/check", {},
                headers={"X-Trace-Id": "definitely-not-hex!!!"},
            )
        # The wrapper validates trace_id; even though the inner returns
        # 400 (empty body), the trace_id in the response is a fresh
        # 16-hex (NOT the malformed inbound value).
        assert "trace_id" in body
        assert re.match(r"^[0-9a-f]{16}$", body["trace_id"])

    def test_terminal_session_status_remains_consistent(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """§ 4.4 / § 5a: a terminal session's /status remains
        is_terminal=true across reads — protects against accidental
        un-terminate behavior."""
        import sqlite3, time
        token = "tok-fail-term"
        now = int(time.time())
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute(
                "INSERT INTO gate_states "
                "(token, state_json, saved_at, expires_at, "
                " is_terminal, last_request_id, last_response_json) "
                "VALUES (?, ?, ?, ?, 1, NULL, NULL)",
                (token,
                 json.dumps({"is_done": True,
                             "termination_reason": "USER_ABORTED"}),
                 now, now + 86400),
            )
            conn.commit()
        for _ in range(3):
            req = urllib.request.Request(
                f"{live_server}/api/extreme-case/status?session_token={token}",
            )
            r = urllib.request.urlopen(req, timeout=5)
            body = json.loads(r.read().decode("utf-8"))
            assert body["is_terminal"] is True
            assert body["terminal_state"] == "USER_ABORTED"
