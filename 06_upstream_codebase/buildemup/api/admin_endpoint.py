"""BuildemUp/BuildEase — Admin endpoint (Component 3a Session 7b Phase 5).

Two POST handlers protected by hmac.compare_digest on the
``X-Admin-Token`` header (env: ``BUILDEMUP_ADMIN_TOKEN``):

  - ``handle_scheduler_tick``  → POST /admin/scheduler/tick
        Claim due fallback rows; fire each via outbound POST to the
        local ``/api/extreme-case/cba-fallback-continue`` endpoint;
        commit on 2xx, record_error on failure or non-2xx.

  - ``handle_scheduler_reset`` → POST /admin/scheduler/reset
        P35 stuck-row recovery. Single-row, idempotent, atomic, audited.
        Refuses to un-fire committed rows (409).

Routes are wired in Phase 8 (api/server.py); these handlers are not
yet reachable over HTTP after Phase 5 alone.

Spec invariants implemented in this module:

  P21 — Scheduler hook idempotent at the worker side. The
        request_id persisted at enqueue time is forwarded on every
        retry, so the cba-fallback-continue handler treats retries
        as P2 idempotency replays.
  P28 — Atomic claim. Enforced inside SchedulerStateStorage.claim_due;
        this module relies on that contract.
  P29 — trace_id propagated end-to-end. The row's persisted trace_id
        (set at pause time) is forwarded as ``X-Trace-Id`` on the
        outbound POST. The tick mints its own trace_id for the tick
        summary line and uses it as a fallback when the row had no
        trace_id at enqueue.
  P30 — Bounded-cardinality log lines. ``c3a.scheduler.tick`` is one
        emit per tick (not per row); session_token never appears
        unmasked in log lines.
  P31 — Server-time authoritative. ``int(time.time())`` is the
        comparison time for claim_due.
  P33 — Claim-then-commit. claim_due increments attempt_count and
        sets last_attempt_at without committing fallback_fired;
        commit_fired runs only on 2xx; record_error on failure /
        non-2xx. Cooldown protects against tight-loop re-claim of a
        row that just failed.
  P35 — Reset is single-row, idempotent, atomic. Enforced inside
        SchedulerStateStorage.reset; the audit log line here is
        emitted unconditionally on every call regardless of outcome.

NB: ``_new_trace_id`` is defined locally per spec § 5.4 (16 hex chars
via ``secrets.token_hex(8)``). This is intentionally distinct from
``utils.logging.new_trace_id()`` (12 chars), which is unchanged by
S7b. Phase 6 will define the same function in ``api/c3a_endpoint.py``;
either of the two can later be made canonical and the other dropped
(deferred decision — small duplication, not worth a refactor mid-build).
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.request
from typing import Mapping, Optional

from buildemup.api.c3a_endpoint import _parse_and_size_check
from buildemup.utils.scheduler_state_storage import (
    ResetOutcome,
    SchedulerStateStorage,
    _mask_token,
)

LOGGER = logging.getLogger(__name__)


# ─── Configuration ───────────────────────────────────────────────────
# Per-tick claim limit. Env-overridable for ops tuning. Spec § 7.4 +
# round 1 #12.
_SCHEDULER_TICK_LIMIT = int(os.environ.get("SCHEDULER_TICK_LIMIT", "100"))

# Soft time budget for one tick. Round 2 #8 — protects against the
# Railway cron HTTP timeout. When exceeded, the loop bails after the
# in-flight row finishes; the remaining claimed rows are NOT
# unclaimed (their attempt_count was incremented at claim time) but
# the cooldown filter (15 min) will let them through on the next
# tick.
_SCHEDULER_TICK_BUDGET_S = 8.0

# Outbound POST configuration. Path is the existing S7a route.
_DEFAULT_INTERNAL_BASE_URL = "http://127.0.0.1:8000"
_CBA_FALLBACK_CONTINUE_PATH = "/api/extreme-case/cba-fallback-continue"
_POST_TIMEOUT_S = 10.0


# ─── trace_id generation (P29) ──────────────────────────────────────
def _new_trace_id() -> str:
    """Internal trace_id generator. Spec § 5.4.

    ``secrets.token_hex(8)`` → 16 hex chars. Matches the
    ``^[0-9a-f]{16}$`` regex that ``handle_cba_fallback_continue``
    will validate against post-Phase-6 (P34).
    """
    return secrets.token_hex(8)


# ─── Storage singleton ──────────────────────────────────────────────
# Mirrors c3a_endpoint's ``_get_storage`` / ``reset_storages_for_tests``
# pattern. Lazy init avoids pulling SQLite open at import time (matters
# for tests that monkey-patch DB paths in setUp).
_scheduler_storage: Optional[SchedulerStateStorage] = None


def _scheduler_state_storage() -> SchedulerStateStorage:
    global _scheduler_storage
    if _scheduler_storage is None:
        _scheduler_storage = SchedulerStateStorage()
    return _scheduler_storage


def reset_scheduler_storage_for_tests(
    scheduler_storage: Optional[SchedulerStateStorage] = None,
) -> None:
    """Inject a test-time SchedulerStateStorage. Pass None to clear."""
    global _scheduler_storage
    _scheduler_storage = scheduler_storage


# ─── Auth ───────────────────────────────────────────────────────────
def _check_admin_token(headers: Mapping[str, str]) -> bool:
    """hmac-constant-time check of X-Admin-Token vs BUILDEMUP_ADMIN_TOKEN.

    Returns False if the env var is unset or the supplied header
    doesn't match. Spec § 7.4 + § 7.5 + § 0.3 (g).
    """
    expected = os.environ.get("BUILDEMUP_ADMIN_TOKEN")
    supplied = headers.get("X-Admin-Token", "") if headers else ""
    if not expected:
        return False
    return hmac.compare_digest(expected, supplied)


# ─── Outbound POST to cba-fallback-continue ────────────────────────
def _post_fallback_continue(
    *,
    session_token: str,
    request_id: str,
    trace_id: str,
) -> tuple[int, dict]:
    """POST to the local cba-fallback-continue endpoint. Returns (status, body).

    Stdlib urllib.request — keeps the dep surface minimal per § 5.6.
    Network errors raise; non-2xx HTTP responses are returned in the
    tuple cleanly (HTTPError is caught and unpacked).

    Body parse is best-effort; non-JSON content yields ``{}`` so the
    caller's ``.get("session_status")`` lookup is safe.
    """
    base = os.environ.get(
        "INTERNAL_API_BASE_URL", _DEFAULT_INTERNAL_BASE_URL,
    )
    url = base.rstrip("/") + _CBA_FALLBACK_CONTINUE_PATH
    body = json.dumps({
        "session_token": session_token,
        "request_id": request_id,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Trace-Id": trace_id,
        },
    )
    try:
        with urllib.request.urlopen(
            req, timeout=_POST_TIMEOUT_S,
        ) as resp:
            status = int(resp.status)
            raw = resp.read()
    except urllib.error.HTTPError as e:
        # Non-2xx — server responded with an error. Treat as a contract
        # response; let the caller decide how to record.
        status = int(e.code)
        try:
            raw = e.read()
        except Exception:
            raw = b""

    parsed: dict
    try:
        decoded = raw.decode("utf-8") if raw else ""
        loaded = json.loads(decoded) if decoded else {}
        parsed = loaded if isinstance(loaded, dict) else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = {}
    return status, parsed


# ─── Per-row processing ────────────────────────────────────────────
def _process_one_fallback(
    token: str,
    trace_id: Optional[str],
    request_id: str,
    attempt_n: int,
    tick_trace: str,
) -> str:
    """Process one claimed row. Returns 'fired' / 'skipped_terminal' / 'failed'.

    P33 commit-on-success / record-error-on-failure split. P29 trace
    forwarding: prefer the row's persisted trace_id over the
    tick-generated one.
    """
    storage = _scheduler_state_storage()
    forward_trace = trace_id or tick_trace
    try:
        status, body = _post_fallback_continue(
            session_token=token,
            request_id=request_id,
            trace_id=forward_trace,
        )
    except Exception as exc:
        err = f"post_exception: {type(exc).__name__}: {exc}"
        storage.record_error(token, err)
        LOGGER.warning(
            "scheduler.tick.failed "
            "(session_token=%s, trace_id=%s, attempt=%s): %s",
            _mask_token(token), forward_trace, attempt_n, err,
        )
        return "failed"

    if 200 <= status < 300:
        if body.get("session_status") == "terminal_replay":
            storage.commit_fired(token)
            LOGGER.info(
                "scheduler.tick.skipped_terminal "
                "(session_token=%s, trace_id=%s)",
                _mask_token(token), forward_trace,
            )
            return "skipped_terminal"
        storage.commit_fired(token)
        return "fired"

    err = f"status_{status}"
    storage.record_error(token, err)
    LOGGER.warning(
        "scheduler.tick.failed "
        "(session_token=%s, trace_id=%s, attempt=%s, status=%s)",
        _mask_token(token), forward_trace, attempt_n, status,
    )
    return "failed"


# ─── handle_scheduler_tick ─────────────────────────────────────────
def handle_scheduler_tick(
    request_body: bytes | str,  # noqa: ARG001 — accepted but unused (POST)
    headers: Mapping[str, str],
) -> tuple[int, dict]:
    """POST /admin/scheduler/tick — claim due rows, fire each. Spec § 7.4.

    Body: ignored (the tick is parameter-less; deliberate, so Railway
    cron can hit it with an empty POST).
    Headers: X-Admin-Token required (hmac.compare_digest).

    Returns (200, summary) on success; (401, unauthorized) on auth
    failure. Per-row failures are reported in the summary counts, not
    by HTTP status — the tick's own work succeeded even if individual
    rows failed.
    """
    if not _check_admin_token(headers):
        return 401, {"ok": False, "code": "unauthorized"}

    tick_trace = _new_trace_id()
    now = int(time.time())
    started = time.monotonic()

    rows = _scheduler_state_storage().claim_due(
        now=now, limit=_SCHEDULER_TICK_LIMIT,
    )

    fired = 0
    skipped_terminal = 0
    failed = 0
    processed = 0
    time_budget_exceeded = False

    for row in rows:
        if (time.monotonic() - started) >= _SCHEDULER_TICK_BUDGET_S:
            time_budget_exceeded = True
            LOGGER.info(
                "scheduler.tick: time budget exceeded; "
                "%s rows deferred to next tick (cooldown protected)",
                len(rows) - processed,
            )
            break

        token, trace_id, request_id, _fire_at, attempt_n = row
        outcome = _process_one_fallback(
            token, trace_id, request_id, attempt_n, tick_trace,
        )
        processed += 1
        if outcome == "fired":
            fired += 1
        elif outcome == "skipped_terminal":
            skipped_terminal += 1
        else:
            failed += 1

    LOGGER.info(json.dumps({
        "msg": "c3a.scheduler.tick",
        "trace_id": tick_trace,
        "due": len(rows),
        "processed": processed,
        "fired": fired,
        "skipped_terminal": skipped_terminal,
        "failed": failed,
        "time_budget_exceeded": time_budget_exceeded,
    }, sort_keys=True))

    return 200, {
        "ok": True,
        "due": len(rows),
        "processed": processed,
        "fired": fired,
        "skipped_terminal": skipped_terminal,
        "failed": failed,
        "time_budget_exceeded": time_budget_exceeded,
        "trace_id": tick_trace,
    }


# ─── handle_scheduler_reset ────────────────────────────────────────
def handle_scheduler_reset(
    request_body: bytes | str,
    headers: Mapping[str, str],
) -> tuple[int, dict]:
    """POST /admin/scheduler/reset — clear attempt fields on a stuck row. § 7.5.

    Body: ``{"session_token": "..."}``.
    Headers: X-Admin-Token required.

    Outcomes (audit-logged on every call regardless of outcome — P35):
      RESET          → 200 + {ok=True,  was_stuck, prior_attempt_count,
                              prior_fallback_error, trace_id}
      ALREADY_FIRED  → 409 + {ok=False, code=already_fired,
                              prior_attempt_count, prior_fallback_error,
                              trace_id}
      NOT_FOUND      → 404 + {ok=False, code=unknown_token, trace_id}

    Body-parse failures use ``_parse_and_size_check`` and inherit the
    c3a structured-errors response shape — intentional reuse of the
    existing parse helper rather than duplicating it.
    """
    if not _check_admin_token(headers):
        return 401, {"ok": False, "code": "unauthorized"}

    trace_id = _new_trace_id()

    parsed, err = _parse_and_size_check(request_body, trace_id)
    if err is not None:
        return err

    token = parsed.get("session_token")
    if not isinstance(token, str) or not token:
        return 400, {
            "ok": False,
            "code": "missing_field",
            "field": "session_token",
            "trace_id": trace_id,
        }

    result = _scheduler_state_storage().reset(token)

    # Audit log — emitted unconditionally on every call (P35).
    LOGGER.info(json.dumps({
        "msg": "c3a.admin.scheduler_reset",
        "trace_id": trace_id,
        "session_token": _mask_token(token),
        "outcome": result.outcome.value,
        "was_stuck": result.was_stuck,
        "prior_attempt_count": result.prior_attempt_count,
        "prior_fallback_error": result.prior_fallback_error,
    }, sort_keys=True))

    if result.outcome is ResetOutcome.NOT_FOUND:
        return 404, {
            "ok": False,
            "code": "unknown_token",
            "trace_id": trace_id,
        }

    if result.outcome is ResetOutcome.ALREADY_FIRED:
        return 409, {
            "ok": False,
            "code": "already_fired",
            "trace_id": trace_id,
            "prior_attempt_count": result.prior_attempt_count,
            "prior_fallback_error": result.prior_fallback_error,
        }

    # ResetOutcome.RESET
    return 200, {
        "ok": True,
        "was_stuck": result.was_stuck,
        "prior_attempt_count": result.prior_attempt_count,
        "prior_fallback_error": result.prior_fallback_error,
        "trace_id": trace_id,
    }


__all__ = [
    "handle_scheduler_tick",
    "handle_scheduler_reset",
    "reset_scheduler_storage_for_tests",
]
