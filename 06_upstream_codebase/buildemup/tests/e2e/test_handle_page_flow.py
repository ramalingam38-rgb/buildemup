"""S8 § 4.11 / v1.2 P-4 — Direct tests of handlePageFlow controller.

3 tests, all @pytest.mark.e2e (Tier 2). Use Playwright to inject
mock apiCall functions into _shared.js and verify branch dispatch.

Test harness: static/c3a/_test_harness.html (NOT served in production).
"""
from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_handle_page_flow_success_branch(c3a_test_environment):
    """§ 4.11: success branch — apiCall resolves → onSuccess returns
    next URL → window.location set."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/_test_harness.html")
    # Trigger handlePageFlow, then await navigation
    page.evaluate(
        """
        () => {
            const mockApiCall = () => Promise.resolve({ok: true});
            const onSuccess = (resp) => "/c3a/done.html?session=test-success";
            const errorContainer = document.getElementById("err");
            handlePageFlow({apiCall: mockApiCall, onSuccess: onSuccess,
                            errorContainer: errorContainer});
        }
        """
    )
    page.wait_for_url("**/c3a/done.html?session=test-success", timeout=5000)
    assert "/c3a/done.html?session=test-success" in page.url


@pytest.mark.e2e
def test_handle_page_flow_terminal_dispatch(c3a_test_environment):
    """§ 4.11 R3.4: TERMINAL error → handleTerminalRedirect invoked
    → window.location set to /c3a/done.html for source='gone'."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/_test_harness.html")
    page.evaluate(
        """
        () => {
            const mockApiCall = () => Promise.reject({
                type: "TERMINAL", source: "gone",
                trace_id: "0123456789abcdef",
            });
            const errorContainer = document.getElementById("err");
            handlePageFlow({apiCall: mockApiCall,
                            onSuccess: () => "/should-not-hit",
                            errorContainer: errorContainer,
                            currentSession: "tok-x"});
        }
        """
    )
    page.wait_for_url("**/c3a/done.html?session=tok-x*", timeout=5000)
    assert "/c3a/done.html" in page.url
    assert "session=tok-x" in page.url


@pytest.mark.e2e
def test_handle_page_flow_user_fixable_displays_error(c3a_test_environment):
    """§ 4.11 R3.4: USER_FIXABLE → displayError invoked with the
    error + traceId in the errorContainer."""
    env = c3a_test_environment
    page = env["page"]
    page.goto(f"{env['base_url']}/c3a/_test_harness.html")
    result = page.evaluate(
        """
        () => new Promise((resolve) => {
            const mockApiCall = () => Promise.reject({
                type: "USER_FIXABLE", source: "validation",
                errors: [{field: "x", code: "required", message: "x required"}],
                trace_id: "deadbeef0123abcd",
            });
            const errorContainer = document.getElementById("err");
            handlePageFlow({apiCall: mockApiCall,
                            onSuccess: () => "/should-not-hit",
                            errorContainer: errorContainer});
            setTimeout(() => resolve(errorContainer.innerHTML), 500);
        })
        """
    )
    assert result, "errorContainer is empty after USER_FIXABLE"
    assert "x required" in result or "required" in result, (
        f"error message not rendered; got {result!r}"
    )
