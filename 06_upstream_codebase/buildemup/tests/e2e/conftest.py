"""S8 § 3.2 + § 4 — E2E fixtures (Playwright + live server).

Layered fixture model:
  - browser (session-scoped) — single chromium instance for whole session
  - context (function-scoped) — fresh BrowserContext per test
  - page (function-scoped) — fresh Page from context
  - c3a_test_environment — convenience: live_server URL + page +
    fresh storage — what most browser tests need
"""
from __future__ import annotations

import os
import socket
import threading
import time
import uuid
from http.server import HTTPServer
from typing import Iterator

import pytest

# Auto-register the e2e marker for pytest -m e2e selection.
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end browser tests (Tier 2, opt-in via -m e2e)",
    )


# ─── Playwright session/context/page fixtures ────────────────────────
@pytest.fixture(scope="session")
def browser():
    """Single chromium instance per pytest session."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True)
        except Exception as e:
            pytest.skip(f"chromium launch failed: {e}")
        yield b
        b.close()


@pytest.fixture
def context(browser):
    """Fresh BrowserContext per test — isolates cookies/storage/etc."""
    ctx = browser.new_context()
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    p = context.new_page()
    yield p
    p.close()


# ─── Live server fixture (mirrors validation/conftest.py) ────────────
def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def fresh_storage_e2e(tmp_path):
    """E2E version of fresh_storage — same wiring as validation but
    we duplicate here because the validation/conftest.py is scoped
    to that directory."""
    db_path = str(tmp_path / f"e2e-{uuid.uuid4().hex[:8]}.db")
    from buildemup.api import c3a_endpoint, admin_endpoint, brief_endpoint
    from buildemup.utils.gate_state_storage import GateStateStorage
    from buildemup.utils.scheduler_state_storage import SchedulerStateStorage
    from buildemup.utils.brief_storage import BriefStorage

    gate = GateStateStorage(db_path=db_path)
    scheduler = SchedulerStateStorage(db_path=db_path)
    brief = BriefStorage(db_path=db_path)
    c3a_endpoint.reset_storages_for_tests(
        gate_storage=gate, brief_storage=brief)
    admin_endpoint.reset_scheduler_storage_for_tests(scheduler)
    if hasattr(brief_endpoint, "reset_storage_for_tests"):
        brief_endpoint.reset_storage_for_tests(brief)
    yield gate, scheduler, brief, db_path
    c3a_endpoint.reset_storages_for_tests(
        gate_storage=None, brief_storage=None)
    admin_endpoint.reset_scheduler_storage_for_tests(None)
    if hasattr(brief_endpoint, "reset_storage_for_tests"):
        brief_endpoint.reset_storage_for_tests(None)


@pytest.fixture
def live_server_e2e(fresh_storage_e2e):
    """Background HTTPServer for browser-driven tests.

    Sets ``C3A_TEST_MODE=1`` for the lifetime of the fixture so that:
      - § 4.11 — `/c3a/_test_harness.html` is served (otherwise gated
        to 404 in production per Phase 5 patch)
      - § 5.6.1 — `<meta name="c3a-test-mode" content="1">` is injected
        into `/c3a/*.html` responses so `_shared.js isTestMode()`
        returns true (which disables `c3aFetch`'s 503 auto-retry —
        necessary for the e2e tests that observe 503 paths).

    The prior env value (typically unset) is restored on teardown so
    test ordering across processes / parallel runs stays clean.
    """
    from buildemup.api.server import BriefCaptureHandler
    prior_test_mode = os.environ.get("C3A_TEST_MODE")
    os.environ["C3A_TEST_MODE"] = "1"
    port = _free_port()
    srv = HTTPServer(("127.0.0.1", port), BriefCaptureHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    base_url = f"http://127.0.0.1:{port}"
    time.sleep(0.05)
    try:
        yield base_url
    finally:
        srv.shutdown()
        srv.server_close()
        t.join(timeout=2.0)
        if prior_test_mode is None:
            os.environ.pop("C3A_TEST_MODE", None)
        else:
            os.environ["C3A_TEST_MODE"] = prior_test_mode


@pytest.fixture
def c3a_test_environment(live_server_e2e, page, fresh_storage_e2e):
    """One-stop fixture: server URL, page, and the storage trio."""
    return {
        "base_url": live_server_e2e,
        "page": page,
        "storage": fresh_storage_e2e,
    }
