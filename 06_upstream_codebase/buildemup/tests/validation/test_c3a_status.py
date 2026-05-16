"""S8 § 4.10 — /status and /check-init endpoint validation tests.

12 tests across two endpoint families:
  Part A (5 tests) — /api/extreme-case/status (§ 5a)
  Part B (7 tests) — /api/extreme-case/check-init (§ 5b)
                     incl. 5 bot-UA tests per v1.2 P-2

Each test docstring names the specific invariant or § section it
protects, per § 4.0.1 hygiene rule.
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
import urllib.error
import urllib.parse

import pytest

from buildemup.tests.validation import _contract


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def _seed_gate_state(
    db_path: str,
    *,
    token: str,
    is_terminal: bool = False,
    termination_reason: str | None = None,
) -> int:
    """Insert a minimal gate_states row directly via SQL.

    Tests that need a fully-formed GateState (e.g., for the state
    machine traversal) use the orchestrator; this helper is for
    /status + termination flag verification where we just need the
    row to exist with the right is_terminal / state_json shape.
    """
    state_payload = {
        "is_done": is_terminal,
        "termination_reason": termination_reason,
    }
    now = int(time.time())
    expires_at = now + 86400
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, ?, ?, ?, ?, NULL, NULL)",
            (token, json.dumps(state_payload), now, expires_at,
             1 if is_terminal else 0),
        )
        conn.commit()
    return now


def _http_get(
    base_url: str, path: str, *, headers: dict | None = None,
):
    """GET helper that returns (status, body_dict_or_text, headers).
    Catches HTTPError so 4xx/5xx return their bodies."""
    url = f"{base_url}{path}"
    req = urllib.request.Request(url, headers=headers or {})
    try:
        r = urllib.request.urlopen(req, timeout=5)
        body = r.read().decode("utf-8")
        return r.status, body, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)


def _parse_json(body_text: str) -> dict:
    return json.loads(body_text)


# ─────────────────────────────────────────────────────────────────────
# Part A — /status endpoint (§ 5a)
# ─────────────────────────────────────────────────────────────────────
class TestStatusEndpoint:
    """§ 5a — read-only GET /api/extreme-case/status.

    Protects: P43 trace decoupling on a read endpoint, status
    response shape per § 5a.3, 4xx/404 error semantics per § 5a.3.
    """

    def test_active_session_returns_in_progress(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """§ 5a.3: GET on a non-terminal session returns
        is_terminal=false, terminal_state=null, current_state set."""
        token = "tok-active-001"
        _seed_gate_state(temp_db_path, token=token, is_terminal=False)
        status, body, _ = _http_get(
            live_server,
            f"/api/extreme-case/status?session_token={token}",
        )
        assert status == 200
        resp = _parse_json(body)
        _contract.assert_status_response(resp)
        assert resp["is_terminal"] is False
        assert resp["terminal_state"] is None
        assert resp["session_token"] == token

    def test_terminal_session_mirrors_terminal_state(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """§ 5a.3: GET on a terminal session returns
        is_terminal=true, current_state == terminal_state ==
        GateTerminationReason value."""
        token = "tok-terminal-001"
        _seed_gate_state(
            temp_db_path, token=token, is_terminal=True,
            termination_reason="SUCCESS",
        )
        status, body, _ = _http_get(
            live_server,
            f"/api/extreme-case/status?session_token={token}",
        )
        assert status == 200
        resp = _parse_json(body)
        _contract.assert_status_response(resp)
        assert resp["is_terminal"] is True
        assert resp["terminal_state"] == "SUCCESS"
        assert resp["current_state"] == "SUCCESS"

    def test_unknown_token_returns_404(self, live_server, fresh_storage):
        """§ 5a.3: GET with unknown session_token → 404 +
        unknown_token error code."""
        status, body, _ = _http_get(
            live_server,
            "/api/extreme-case/status?session_token=does-not-exist",
        )
        assert status == 404
        resp = _parse_json(body)
        _contract.assert_validation_error(resp, expected_code="unknown_token")

    def test_missing_token_returns_400_validation(
        self, live_server, fresh_storage,
    ):
        """§ 5a.3: GET without session_token → 400 + validation."""
        status, body, _ = _http_get(
            live_server, "/api/extreme-case/status",
        )
        assert status == 400
        resp = _parse_json(body)
        _contract.assert_validation_error(resp, expected_code="validation")

    def test_p43_trace_decoupling_on_status(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """§ 2.8 P43: when X-Trace-Id is a valid 16-hex, the response
        body's trace_id field is the client trace (correlation hint)."""
        token = "tok-trace-001"
        _seed_gate_state(temp_db_path, token=token)
        client_trace = "deadbeef0123abcd"
        status, body, _ = _http_get(
            live_server,
            f"/api/extreme-case/status?session_token={token}",
            headers={"X-Trace-Id": client_trace},
        )
        assert status == 200
        resp = _parse_json(body)
        # Per P43 mapping: response body trace_id → client_trace_id
        assert resp["trace_id"] == client_trace, (
            f"expected client trace in body; got {resp['trace_id']!r}"
        )


# ─────────────────────────────────────────────────────────────────────
# Part B — /check-init endpoint (§ 5b) — 7 tests incl. v1.2 P-2 bot-UA
# ─────────────────────────────────────────────────────────────────────
_BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0"


class TestCheckInitEndpoint:
    """§ 5b — POST-neutralizing GET wrapper + bot-UA filter (v1.2 P-2)."""

    def test_browser_ua_missing_brief_returns_400(
        self, live_server, fresh_storage,
    ):
        """§ 5b.3: legitimate UA with missing query → 400 from inner
        POST /check validator."""
        status, body, _headers = _http_get(
            live_server,
            "/api/extreme-case/check-init",
            headers={"User-Agent": _BROWSER_UA},
        )
        assert status == 400
        resp = _parse_json(body)
        _contract.assert_validation_error(resp)

    def test_browser_ua_carries_no_cache_headers(
        self, live_server, fresh_storage,
    ):
        """§ 5b.3 + v1.1 Item 7: Cache-Control: no-store on every
        legitimate-UA response."""
        _status, _body, headers = _http_get(
            live_server,
            "/api/extreme-case/check-init",
            headers={"User-Agent": _BROWSER_UA},
        )
        cc = headers.get("Cache-Control") or headers.get("cache-control")
        assert cc is not None and "no-store" in cc, (
            f"missing Cache-Control no-store: {cc!r}"
        )

    def test_bot_ua_facebook_returns_html_no_session(
        self, live_server, fresh_storage, temp_db_path,
    ):
        """v1.2 P-2 § 5b.4: facebookexternalhit gets HTML preview;
        NO session row created."""
        status, body, headers = _http_get(
            live_server,
            "/api/extreme-case/check-init?brief=t&request_id=r",
            headers={"User-Agent": "facebookexternalhit/1.1"},
        )
        assert status == 200
        ct = headers.get("Content-Type") or headers.get("content-type") or ""
        assert "text/html" in ct.lower()
        assert "<!DOCTYPE html>" in body
        # NO session created in DB.
        with sqlite3.connect(temp_db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM gate_states",
            ).fetchone()[0]
        assert count == 0, f"bot UA created {count} session rows"

    def test_bot_ua_slackbot_returns_html(self, live_server, fresh_storage):
        """v1.2 P-2: SlackBot link-unfurl gets HTML preview."""
        status, body, headers = _http_get(
            live_server,
            "/api/extreme-case/check-init?brief=t&request_id=r",
            headers={"User-Agent": "Slackbot-LinkExpanding 1.0"},
        )
        assert status == 200
        ct = (headers.get("Content-Type")
              or headers.get("content-type") or "")
        assert "text/html" in ct.lower()

    def test_bot_ua_telegram_returns_html(self, live_server, fresh_storage):
        """v1.2 P-2: TelegramBot gets HTML preview."""
        status, _body, headers = _http_get(
            live_server,
            "/api/extreme-case/check-init?brief=t&request_id=r",
            headers={"User-Agent": "TelegramBot (like TwitterBot)"},
        )
        assert status == 200
        ct = (headers.get("Content-Type")
              or headers.get("content-type") or "")
        assert "text/html" in ct.lower()

    def test_empty_ua_returns_html_suspicious_default(
        self, live_server, fresh_storage,
    ):
        """v1.2 P-2 § 5b.5: empty/missing UA → suspicious; HTML preview."""
        status, body, headers = _http_get(
            live_server,
            "/api/extreme-case/check-init?brief=t&request_id=r",
            headers={"User-Agent": ""},
        )
        assert status == 200
        ct = (headers.get("Content-Type")
              or headers.get("content-type") or "")
        assert "text/html" in ct.lower()
        assert "<!DOCTYPE html>" in body

    def test_bot_ua_no_cache_header(self, live_server, fresh_storage):
        """§ 5b.4: bot path also carries no-cache headers (prevents
        CDN caching of preview HTML)."""
        _status, _body, headers = _http_get(
            live_server,
            "/api/extreme-case/check-init?brief=t&request_id=r",
            headers={"User-Agent": "googlebot/2.1"},
        )
        cc = headers.get("Cache-Control") or headers.get("cache-control")
        assert cc is not None and "no-store" in cc
