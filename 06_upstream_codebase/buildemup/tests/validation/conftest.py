"""S8 § 3.2 — Validation suite fixtures.

Layered pytest fixture model per spec § 3.2:
  (a) temp_db_path     — function-scoped unique SQLite path
  (b) fresh_storage    — initialised Gate + Scheduler + Brief stores
  (c) frozen_clock     — patched time.time + datetime.utcnow
  (d) live_server      — in-process HTTPServer thread (function-scoped)
  (e) mocked_resend    — urllib.request patched so the email hook
                         records but does not send
  (f) seeded_brief     — inserts a brief via BriefStorage.save()
                         (Finding 6 — public API, NOT raw SQL)

Tests pull whatever subset they need; pytest's DI assembles them.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from http.server import HTTPServer
from typing import Iterator, Optional
from unittest.mock import patch

import pytest


# ─────────────────────────────────────────────────────────────────────
# (a) temp_db_path — function-scoped unique SQLite path
# ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def temp_db_path(tmp_path) -> str:
    """A fresh SQLite file path under pytest's tmp_path fixture.

    pytest's tmp_path is automatically cleaned at session end, so we
    don't need explicit teardown here.
    """
    return str(tmp_path / f"validation-{uuid.uuid4().hex[:8]}.db")


# ─────────────────────────────────────────────────────────────────────
# (b) fresh_storage — initialised storage backends, injected globally
# ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def fresh_storage(temp_db_path):
    """Construct GateStateStorage + SchedulerStateStorage + BriefStorage
    rooted at `temp_db_path`, inject them into the api modules' singleton
    slots, and yield the trio. Reset all slots on teardown so tests don't
    leak state across runs.
    """
    from buildemup.api import c3a_endpoint, admin_endpoint, brief_endpoint
    from buildemup.utils.gate_state_storage import GateStateStorage
    from buildemup.utils.scheduler_state_storage import SchedulerStateStorage
    from buildemup.utils.brief_storage import BriefStorage

    gate = GateStateStorage(db_path=temp_db_path)
    scheduler = SchedulerStateStorage(db_path=temp_db_path)
    brief = BriefStorage(db_path=temp_db_path)

    c3a_endpoint.reset_storages_for_tests(
        gate_storage=gate, brief_storage=brief,
    )
    admin_endpoint.reset_scheduler_storage_for_tests(scheduler)
    # brief_endpoint may have its own storage slot — guard with hasattr
    if hasattr(brief_endpoint, "reset_storage_for_tests"):
        brief_endpoint.reset_storage_for_tests(brief)

    yield gate, scheduler, brief

    # Teardown
    c3a_endpoint.reset_storages_for_tests(
        gate_storage=None, brief_storage=None,
    )
    admin_endpoint.reset_scheduler_storage_for_tests(None)
    if hasattr(brief_endpoint, "reset_storage_for_tests"):
        brief_endpoint.reset_storage_for_tests(None)


# ─────────────────────────────────────────────────────────────────────
# (c) frozen_clock — patches time.time / datetime.utcnow
# ─────────────────────────────────────────────────────────────────────
class _FrozenClock:
    """A minimal fake clock controllable via .advance(seconds)."""

    def __init__(self, t0: float):
        self._now = float(t0)

    def time(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += float(seconds)


@pytest.fixture
def frozen_clock():
    """Yield a _FrozenClock with t0 = 1_730_000_000 (Oct 2024).

    NOTE: we do not globally patch `time.time` because c3a code paths
    rely on monotonic timing for timeouts (incompatible with a frozen
    wall clock). Tests that need to exercise time-window logic
    (24h fallback, TTL expiry) inject `frozen_clock.time` into the
    specific call sites — typically by monkeypatching the caller.
    """
    return _FrozenClock(1_730_000_000.0)


# ─────────────────────────────────────────────────────────────────────
# (d) live_server — in-process HTTPServer thread on a free port
# ─────────────────────────────────────────────────────────────────────
def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def live_server(fresh_storage):
    """Start the production server.BriefCaptureHandler on a free port
    in a background thread. Yield the base URL. Teardown shuts the
    server down cleanly.
    """
    from buildemup.api.server import BriefCaptureHandler

    port = _free_port()
    srv = HTTPServer(("127.0.0.1", port), BriefCaptureHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    base_url = f"http://127.0.0.1:{port}"
    # Brief warmup so the first request doesn't race the listener.
    time.sleep(0.05)

    yield base_url

    srv.shutdown()
    srv.server_close()
    t.join(timeout=2.0)


# ─────────────────────────────────────────────────────────────────────
# (e) mocked_resend — patches urllib.request.urlopen in the email hook
# ─────────────────────────────────────────────────────────────────────
class _ResendCall:
    """Captured Resend call for assertions."""
    def __init__(self, request_obj):
        self.request = request_obj
        self.url = request_obj.full_url
        self.headers = dict(request_obj.headers)
        try:
            self.body = json.loads(request_obj.data)
        except Exception:
            self.body = None


@pytest.fixture
def mocked_resend():
    """Patch urllib.request.urlopen inside c3a_email_hook so the
    constructed Request is captured but no network call is made.

    Yields a list of _ResendCall objects, ordered by call.
    """
    calls: list[_ResendCall] = []

    class _FakeResponse:
        status = 202

        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"id":"mock"}'

    def _fake_urlopen(req, timeout=None):
        calls.append(_ResendCall(req))
        return _FakeResponse()

    # Only patch within the email hook module's import — avoids breaking
    # other urllib users (e.g., the test client itself).
    with patch(
        "buildemup.api.c3a_email_hook.urllib.request.urlopen",
        side_effect=_fake_urlopen,
    ):
        # Ensure RESEND_API_KEY is set so the hook doesn't no-op out.
        prev = os.environ.get("RESEND_API_KEY")
        os.environ["RESEND_API_KEY"] = "test-resend-key-xxxxxxxxxxxx"
        try:
            yield calls
        finally:
            if prev is None:
                os.environ.pop("RESEND_API_KEY", None)
            else:
                os.environ["RESEND_API_KEY"] = prev


# ─────────────────────────────────────────────────────────────────────
# (f) seeded_brief — insert a brief via the public BriefStorage.save()
# ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def seeded_brief(fresh_storage):
    """Returns a factory `(brief_token=None, **brief_overrides) -> token`.

    Per Finding 6 (§ 3.2 (f)): inserts via BriefStorage.save() — the
    public API — NOT raw SQL. If the brief schema evolves, only
    BriefStorage.save() needs updating, not every call site here.
    """
    _gate, _scheduler, brief = fresh_storage

    def _seed(brief_token: Optional[str] = None, **overrides) -> str:
        # Minimal valid brief shape — sufficient for c3a's brief_token
        # resolution path. c3a does NOT introspect every brief field;
        # it pulls .feasibility-relevant fields downstream.
        payload = {
            "user_email": "test+s8@example.test",
            "city_id": "chennai",
            "plot_dimensions_ft": {"length": 40, "width": 30},
            "plot_orientation_facing": "north",
            "soil_type": "soft_clay",
            "is_in_seismic_zone_iv_or_higher": False,
            "wind_zone": "low",
            "rainfall_zone": "moderate",
            "is_in_corrosive_environment": False,
            "n_bedrooms": 3,
            "expected_floors": 2,
            "footprint_target_sqft": 900,
            "budget_inr": 4_500_000,
            "construction_quality": "standard",
            "construction_phasing": "all_at_once",
            "user_priorities": [
                "structural_safety", "budget_certainty", "vastu_alignment",
            ],
            "is_corner_plot": False,
            "vastu_lock_facing": False,
            "vastu_priority": "advisory",
        }
        payload.update(overrides)
        token, _expires = brief.save(payload, existing_token=brief_token)
        return token

    return _seed
