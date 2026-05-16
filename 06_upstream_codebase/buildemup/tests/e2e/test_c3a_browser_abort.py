"""S8 § 4 e2e — abort confirmation flow.

Tests aborted.html behavior per § 5.4:
- USER_ABORTED terminal → render abort confirmation
- Other terminal → redirect to /done
- Non-terminal → redirect to /case
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
def test_aborted_page_renders_for_user_aborted(c3a_test_environment):
    """aborted.html renders the abort UX when terminal_state is
    USER_ABORTED."""
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-abort-1"
    _seed(db_path, token, terminal=True, reason="USER_ABORTED")
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/aborted.html?session={token}")
    page.wait_for_selector(
        "#aborted-container:not(.c3a-hidden)", timeout=5000,
    )
    body_text = page.locator("body").inner_text()
    assert "exited" in body_text.lower() or "saved" in body_text.lower()


@pytest.mark.e2e
def test_aborted_page_redirects_for_other_terminal(c3a_test_environment):
    """aborted.html redirects to /done when terminal_state is NOT
    USER_ABORTED."""
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-abort-2"
    _seed(db_path, token, terminal=True, reason="SUCCESS")
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/aborted.html?session={token}")
    page.wait_for_url(f"**/c3a/done.html?session={token}*", timeout=5000)
    assert "/c3a/done.html" in page.url
