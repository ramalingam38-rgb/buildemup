"""S8 § 4 e2e — automated a11y scans (5 tests, one per page).

Per round 2 X8 / R3.6 — automated axe-core covers structural
violations (missing labels, contrast, ARIA mis-use, heading order).
Interaction-quality verification is in MANUAL_A11Y_CHECKLIST.md.

axe-core is loaded from a CDN per page; in fully-offline test
environments these tests skip gracefully.
"""
from __future__ import annotations

import json
import sqlite3
import time

import pytest


_AXE_CDN = "https://unpkg.com/axe-core@4.10.0/axe.min.js"


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


def _seed_terminal(db_path, token, reason):
    now = int(time.time())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, ?, ?, ?, 1, NULL, NULL)",
            (token,
             json.dumps({"is_done": True, "termination_reason": reason}),
             now, now + 86400),
        )
        conn.commit()


def _run_axe(page) -> dict:
    """Inject axe-core from CDN and run a scan."""
    try:
        page.add_script_tag(url=_AXE_CDN)
    except Exception as e:
        pytest.skip(f"axe-core CDN unreachable: {e}")
    result = page.evaluate(
        "() => axe.run().then(r => ({ violations: r.violations || [] }))"
    )
    return result


def _assert_no_serious_violations(result):
    """Fail on serious + critical violations only. Minor / moderate
    are flagged for manual triage but don't block CI."""
    blocking = [
        v for v in result.get("violations", [])
        if v.get("impact") in ("serious", "critical")
    ]
    assert not blocking, (
        f"axe-core found {len(blocking)} blocking violations: "
        f"{[v['id'] for v in blocking]}"
    )


@pytest.mark.e2e
def test_a11y_case_page(c3a_test_environment):
    """case.html — initial-load scan (loading state visible)."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/case.html?brief=irrelevant")
    page.wait_for_load_state("domcontentloaded")
    _assert_no_serious_violations(_run_axe(page))


@pytest.mark.e2e
def test_a11y_checklist_page(c3a_test_environment):
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-a11y-cba"
    _seed_active(db_path, token)
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/checklist.html?session={token}")
    page.wait_for_selector(
        "#checklist-container:not(.c3a-hidden)", timeout=5000,
    )
    _assert_no_serious_violations(_run_axe(page))


@pytest.mark.e2e
def test_a11y_done_page(c3a_test_environment):
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-a11y-done"
    _seed_terminal(db_path, token, "SUCCESS")
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/done.html?session={token}")
    page.wait_for_selector(
        "#done-container:not(.c3a-hidden)", timeout=5000,
    )
    _assert_no_serious_violations(_run_axe(page))


@pytest.mark.e2e
def test_a11y_aborted_page(c3a_test_environment):
    env = c3a_test_environment
    _g, _s, _b, db_path = env["storage"]
    token = "tok-a11y-abort"
    _seed_terminal(db_path, token, "USER_ABORTED")
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/aborted.html?session={token}")
    page.wait_for_selector(
        "#aborted-container:not(.c3a-hidden)", timeout=5000,
    )
    _assert_no_serious_violations(_run_axe(page))


@pytest.mark.e2e
def test_a11y_test_harness_page(c3a_test_environment):
    """Test harness should ALSO be accessible — devs use it too."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/_test_harness.html")
    page.wait_for_load_state("domcontentloaded")
    _assert_no_serious_violations(_run_axe(page))
