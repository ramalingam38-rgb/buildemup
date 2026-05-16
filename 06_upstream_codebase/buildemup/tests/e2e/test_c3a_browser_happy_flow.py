"""S8 § 4 e2e — happy-path browser tests.

Two tests exercising the page-load + status-driven render paths
that don't require a full state-machine traversal.
"""
from __future__ import annotations

import json
import sqlite3
import time

import pytest


def _seed_terminal_session(db_path, token, reason="SUCCESS"):
    now = int(time.time())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, ?, ?, ?, 1, NULL, NULL)",
            (token, json.dumps({"is_done": True,
                                "termination_reason": reason}),
             now, now + 86400),
        )
        conn.commit()


@pytest.mark.e2e
def test_done_page_renders_terminal_state(c3a_test_environment):
    """done.html renders the terminal-state label after the
    initial /status fetch confirms the session is terminal."""
    env = c3a_test_environment
    _gate, _sched, _brief, db_path = env["storage"]
    token = "tok-e2e-done-1"
    _seed_terminal_session(db_path, token, "SUCCESS")
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/done.html?session={token}")
    page.wait_for_selector(
        "#done-container:not(.c3a-hidden)", timeout=5000,
    )
    label = page.locator("#terminal-label").inner_text()
    assert label == "SUCCESS"


@pytest.mark.e2e
def test_test_harness_loads_shared_js(c3a_test_environment):
    """_test_harness.html loads _shared.js and exposes
    handlePageFlow + traceId on window."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/_test_harness.html")
    has_helpers = page.evaluate(
        "() => typeof handlePageFlow === 'function' && "
        "typeof traceId === 'function' && "
        "typeof c3aFetch === 'function'"
    )
    assert has_helpers
