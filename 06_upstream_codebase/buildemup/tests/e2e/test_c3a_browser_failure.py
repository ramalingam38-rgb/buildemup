"""S8 § 4 e2e — failure-mode browser tests.

Verifies the UI surface handles 4xx and 404 states correctly:
errors render in the error container; users see actionable messages.
"""
from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_case_page_missing_brief_param_shows_error(c3a_test_environment):
    """case.html without ?brief=... renders an error in the
    error-container; it does NOT silently leave a blank page."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/case.html")
    page.wait_for_selector("#error-container", state="attached", timeout=5000)
    # Wait for JS to render the error
    page.wait_for_function(
        "document.getElementById('error-container').innerHTML.length > 0",
        timeout=5000,
    )
    err_html = page.locator("#error-container").inner_html()
    assert "brief" in err_html.lower() or "required" in err_html.lower()


@pytest.mark.e2e
def test_done_page_missing_session_param_shows_error(c3a_test_environment):
    """done.html without ?session=... renders error."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/done.html")
    page.wait_for_function(
        "document.getElementById('error-container').innerHTML.length > 0",
        timeout=5000,
    )
    err_html = page.locator("#error-container").inner_html()
    assert "session" in err_html.lower() or "required" in err_html.lower()


@pytest.mark.e2e
def test_done_page_unknown_session_shows_unknown_token(c3a_test_environment):
    """done.html with unknown session_token surfaces unknown_token
    via /status 404."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(
        f"{env['base_url']}/c3a/done.html?session=ghost-xxx-not-real",
    )
    page.wait_for_function(
        "document.getElementById('error-container').innerHTML.length > 0",
        timeout=5000,
    )
    err_html = page.locator("#error-container").inner_html()
    assert "session not found" in err_html.lower() \
        or "not found" in err_html.lower() \
        or "unknown_token" in err_html.lower()
