"""S8 § 4 e2e — resume-from-email-link flow.

Tests Finding 1: trace_id from URL ?trace= param is preserved
across page navigation when the user lands from a 24h-later email.
"""
from __future__ import annotations

import json
import sqlite3
import time

import pytest


def _seed_active(db_path, token):
    now = int(time.time())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, '{}', ?, ?, 0, NULL, NULL)",
            (token, now, now + 86400),
        )
        conn.commit()


@pytest.mark.e2e
def test_trace_id_preserved_from_url_query(c3a_test_environment):
    """checklist.html with ?trace=<16hex> — _shared.js's traceId()
    must surface that exact value (Finding 1)."""
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-resume-1"
    _seed_active(db_path, token)
    expected_trace = "0123456789abcdef"
    page = env["page"]
    page.goto(
        f"{env['base_url']}/c3a/checklist.html?"
        f"session={token}&trace={expected_trace}"
    )
    page.wait_for_function(
        "typeof traceId === 'function'", timeout=5000,
    )
    actual = page.evaluate("() => traceId()")
    assert actual == expected_trace, (
        f"traceId did not preserve URL value: got {actual!r}"
    )


@pytest.mark.e2e
def test_trace_id_minted_when_no_url_param(c3a_test_environment):
    """When ?trace= is absent, traceId() mints a fresh 16-hex."""
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-resume-2"
    _seed_active(db_path, token)
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/checklist.html?session={token}")
    page.wait_for_function(
        "typeof traceId === 'function'", timeout=5000,
    )
    minted = page.evaluate("() => traceId()")
    import re
    assert re.match(r"^[0-9a-f]{16}$", minted), (
        f"minted trace not 16-hex: {minted!r}"
    )
