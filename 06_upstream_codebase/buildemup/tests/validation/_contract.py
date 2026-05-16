"""S8 § 4.0 — Centralized contract module (P42).

Plain-function shape assertions for every C3a response surface. NOT a
test file; pytest doesn't collect this. Imported by test files that
touch JSON responses to keep the contract DRY.

Per External Item 1 reasoning: without centralization each test
redefines the shape, creating drift; with centralization, adding a
field is one update here that's automatically validated everywhere.

Cross-check guard (§ 4.0 round 2 X4): three "raw" tests in
test_c3a_state_machine.py deliberately do NOT use these helpers —
they hand-write field assertions for the happy-path responses. If a
helper here forgets to assert a field, the raw tests catch the drift.

The helpers are not Pydantic / OpenAPI / any DSL — just `assert`
statements. The pushback against schema DSLs (§ 0.3 (g)) stands.
"""
from __future__ import annotations

import re
from typing import Any

# 16 lowercase hex chars — the canonical c3a trace_id format (P34).
_TRACE_ID_RE = re.compile(r"^[0-9a-f]{16}$")


def _assert_trace_id(resp: dict) -> None:
    assert "trace_id" in resp, "missing trace_id in response"
    assert isinstance(resp["trace_id"], str), \
        f"trace_id not string: {type(resp['trace_id'])}"
    assert _TRACE_ID_RE.match(resp["trace_id"]), \
        f"trace_id not 16-hex: {resp['trace_id']!r}"


# ─── Success-shape assertions ────────────────────────────────────────

def assert_check_response(resp: dict) -> None:
    """200 response shape from POST /api/extreme-case/check (§ 5.1).

    Two valid sub-shapes (per S7a § 5):
      - terminal SUCCESS:
            ok=True, session_token, resolved_brief, trace_id
      - in-progress:
            ok=True, session_token, extreme_case (or current_case),
            trace_id
    """
    assert resp.get("ok") is True, f"ok!=True: {resp!r}"
    assert "session_token" in resp, "missing session_token"
    assert isinstance(resp["session_token"], str)
    assert resp["session_token"], "empty session_token"
    _assert_trace_id(resp)
    # One of two outcome shapes:
    has_resolved = "resolved_brief" in resp or "final_resolved_brief" in resp
    has_case = (
        "extreme_case" in resp or "current_case" in resp
        or "session_status" in resp
    )
    assert has_resolved or has_case, (
        f"check response carries neither terminal nor in-progress payload: "
        f"keys={list(resp.keys())!r}"
    )


def assert_resolve_response(resp: dict) -> None:
    """200 response shape from POST /api/extreme-case/resolve (§ 5.2)."""
    assert resp.get("ok") is True, f"ok!=True: {resp!r}"
    assert "session_token" in resp
    _assert_trace_id(resp)


def assert_abort_response(resp: dict) -> None:
    """200 response shape from POST /api/extreme-case/abort (§ 5.3)."""
    assert resp.get("ok") is True, f"ok!=True: {resp!r}"
    assert "session_token" in resp
    _assert_trace_id(resp)


def assert_cba_verified_response(resp: dict) -> None:
    """200 response shape from POST /api/extreme-case/cba-verified."""
    assert resp.get("ok") is True
    assert "session_token" in resp
    _assert_trace_id(resp)


def assert_status_response(resp: dict) -> None:
    """200 response shape from GET /api/extreme-case/status (§ 5a.3)."""
    assert resp.get("ok") is True
    assert "session_token" in resp and isinstance(resp["session_token"], str)
    assert "current_state" in resp and isinstance(resp["current_state"], str)
    assert "is_terminal" in resp and isinstance(resp["is_terminal"], bool)
    # terminal_state is None for in-progress, str for terminal.
    assert resp.get("terminal_state") is None or \
        isinstance(resp["terminal_state"], str)
    if resp["is_terminal"]:
        assert resp["terminal_state"] is not None, (
            "is_terminal=true requires terminal_state set"
        )
        assert resp["terminal_state"] == resp["current_state"], (
            "terminal: current_state must mirror terminal_state"
        )
    assert "last_updated_at" in resp
    assert isinstance(resp["last_updated_at"], (int, float))
    _assert_trace_id(resp)


# ─── Error-shape assertions ──────────────────────────────────────────

def assert_validation_error(resp: dict, *, expected_code: str = None) -> None:
    """4xx validation-error shape (§ 6.5):
        { ok=False, errors=[{code, message[, field]}], trace_id }
    """
    assert resp.get("ok") is False, f"ok!=False: {resp!r}"
    assert "errors" in resp and isinstance(resp["errors"], list)
    assert resp["errors"], "errors list is empty"
    for e in resp["errors"]:
        assert isinstance(e, dict)
        assert "code" in e and isinstance(e["code"], str)
        assert "message" in e and isinstance(e["message"], str)
    if expected_code is not None:
        codes = [e["code"] for e in resp["errors"]]
        assert expected_code in codes, (
            f"expected code {expected_code!r}; got {codes!r}"
        )
    _assert_trace_id(resp)


def assert_storage_busy_error(resp: dict) -> None:
    """503 storage_busy shape (§ 6.2 round 2 X4 — NEW v0.2):
        { ok=False, code='storage_busy', retry_after_seconds=5,
          trace_id }
    Caller should ALSO check `Retry-After: 5` header if accessible.
    """
    assert resp.get("ok") is False
    assert resp.get("code") == "storage_busy", \
        f"code!=storage_busy: {resp.get('code')!r}"
    assert resp.get("retry_after_seconds") == 5
    _assert_trace_id(resp)
