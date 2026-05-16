"""S8 § 4 e2e — CBA checklist flow.

Tests checklist.html's status-first behavior per § 5.3:
- Terminal session → redirect to /done
- Non-terminal session → render checklist
"""
from __future__ import annotations

import json
import sqlite3
import time

import pytest


def _seed(db_path, token, *, terminal=False, reason=None):
    now = int(time.time())
    sj = {"is_done": terminal, "termination_reason": reason}
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, ?, ?, ?, ?, NULL, NULL)",
            (token, json.dumps(sj), now, now + 86400,
             1 if terminal else 0),
        )
        conn.commit()


@pytest.mark.e2e
def test_checklist_renders_for_active_session(c3a_test_environment):
    """checklist.html renders the form when /status returns
    is_terminal=false."""
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-cba-active"
    _seed(db_path, token, terminal=False)
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/checklist.html?session={token}")
    page.wait_for_selector(
        "#checklist-container:not(.c3a-hidden)", timeout=5000,
    )
    assert page.locator("#confirm-btn").is_visible()


@pytest.mark.e2e
def test_checklist_redirects_when_already_terminal(c3a_test_environment):
    """checklist.html redirects to /done when /status reports
    the session is already terminal (stale email link case)."""
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-cba-stale"
    _seed(db_path, token, terminal=True, reason="CBA_VERIFICATION_PAUSED")
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/checklist.html?session={token}")
    page.wait_for_url(f"**/c3a/done.html?session={token}*", timeout=5000)
    assert "/c3a/done.html" in page.url
