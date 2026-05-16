"""
Component 3a — Scheduler hook (S7b production wiring per SPEC v1.0 § 7.4).

Per the locked S7b SPEC § 7.4 hook contract:
  - Returns None.
  - Never raises.
  - Idempotent across replays (P21: idempotency at the API layer via P2,
    plus enqueue uses INSERT ... ON CONFLICT DO UPDATE for safety).
  - Pure side effect — no return value carries information.

Production replacement (S7b): the pause path inserts a row into the
`scheduler_state` table (per P27, separate from gate_states); a
Railway cron job hits `/admin/scheduler/tick` every 15 minutes which
atomically claims due rows (P28 + P33) and POSTs to
`/api/extreme-case/cba-fallback-continue`.

Signature changes from the S7a stub (per spec § 7.4):
  - Old: `schedule_fallback_invitation(draft_token, fallback_at)` where
    `fallback_at` was an ISO 8601 string.
  - New: `schedule_fallback_invitation(session_token, fire_at_unix,
    request_id, *, trace_id=None)` where `fire_at_unix` is an INTEGER
    UNIX timestamp. P31 makes server-time the authoritative firing
    decision; ISO strings stay as user-display informational fields.

The c3a_endpoint pause path is updated alongside (§ 1.2 (iv) +
§ 8.7) to compute `fire_at_unix = int(time.time()) + 86400` and pass
the request_id and trace_id through.
"""
from __future__ import annotations

import logging
from typing import Optional

from buildemup.utils.scheduler_state_storage import (
    SchedulerStateStorage,
)

logger = logging.getLogger("buildemup.c3a.scheduler_hook")


# ─── Lazy singleton (matches c3a_endpoint storage pattern) ──────────
# Exposed as a module-level reference so tests can override via
# scheduler_state_storage = FakeStorage().
_scheduler_state_storage: Optional[SchedulerStateStorage] = None


def _get_storage() -> SchedulerStateStorage:
    global _scheduler_state_storage
    if _scheduler_state_storage is None:
        _scheduler_state_storage = SchedulerStateStorage()
    return _scheduler_state_storage


def reset_storage_for_tests(
    storage: Optional[SchedulerStateStorage] = None,
) -> None:
    """Test seam — set the storage instance directly or reset to None."""
    global _scheduler_state_storage
    _scheduler_state_storage = storage


def schedule_fallback_invitation(
    session_token: str,
    fire_at_unix: int,
    request_id: str,
    *,
    trace_id: Optional[str] = None,
) -> None:
    """Enqueue a 24h fallback for the paused session.

    Per P31, `fire_at_unix` is an INTEGER UNIX timestamp computed
    against server clock at the call site (typically
    `int(time.time()) + 86400`). The scheduler tick later compares
    against `int(time.time())` to decide whether the row is due.

    Per § 7.4 contract: returns None; never raises. Enqueue failures
    are logged at WARNING (the storage layer failure shouldn't break
    the user-facing response — the scheduler row is best-effort, like
    the email).

    Args:
        session_token: paused gate session id (= storage token).
        fire_at_unix: UNIX timestamp (int) at which the fallback
                      becomes eligible to fire.
        request_id: idempotency key carried through to the eventual
                    cba-fallback-continue POST. P21 deduplication
                    happens at the API side.
        trace_id: 16-hex correlation ID propagated end-to-end (P29).
                  Stored on the scheduler_state row so the admin tick
                  can forward it as X-Trace-Id on the outbound POST.

    Returns:
        None.
    """
    try:
        _get_storage().enqueue(
            session_token=session_token,
            fire_at=fire_at_unix,
            request_id=request_id,
            trace_id=trace_id,
        )
        logger.info(
            "schedule_fallback_invitation: enqueued "
            "(session_token=%s, fire_at=%d, trace_id=%s)",
            _mask_token(session_token), fire_at_unix, trace_id,
        )
    except Exception as exc:
        logger.warning(
            "schedule_fallback_invitation: enqueue failed "
            "(session_token=%s, trace_id=%s): %r",
            _mask_token(session_token), trace_id, exc,
        )
    return None


def _mask_token(token: str) -> str:
    if not token or len(token) <= 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"


__all__ = [
    "schedule_fallback_invitation",
    "reset_storage_for_tests",
]
