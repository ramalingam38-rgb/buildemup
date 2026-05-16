"""BuildemUp/BuildEase — Health endpoint (Component 3a Session 7b Phase 7).

Single GET handler:

  ``handle_health()`` → GET /health

Returns 200 + a status dict when both storages are write-capable and
both required tables are present; returns 503 + ``code`` identifying
the failed check otherwise. Latency target < 50ms typical.

The five checks per spec § 8.4 (run in order; first failure short-
circuits):

  (a) gate_states write-capable. ``BEGIN IMMEDIATE`` on a temp
      connection then ``ROLLBACK``. Detects a read-only filesystem,
      a corrupted WAL, or a stuck writer. No data written.

  (b) scheduler_state write-capable. Same shape as (a) but with an
      ``INSERT`` of a sentinel row inside the transaction so the
      write path (not just the lock acquisition) is exercised. The
      ROLLBACK undoes the INSERT — the table contents are unchanged.
      The sentinel uses a well-known token so any row that ever
      escapes the rollback (theoretical, would be a SQLite bug) is
      identifiable in forensics.

  (c) Both required tables present. Single ``sqlite_master`` query
      against the gate_states connection.

  (d) Scheduler queue depth — ``count_due(now)``. Diagnostic only;
      never causes a 503.

  (e) Stuck-row count — ``count_stuck()``. Diagnostic only; never
      causes a 503. Operationally this is the alerting signal for
      "the scheduler can't deliver to the API" (P33). Phase-9 ops
      runbook: alert when ``scheduler_stuck_count > 0`` for >1 tick.

Routes are wired in Phase 8 (api/server.py); this handler is not
yet reachable over HTTP after Phase 7 alone.

Spec invariants implemented in this module:

  P32 — /health is the runtime-side complement to startup config
        validation. Both must pass for a deploy to be considered
        healthy. The ROLLBACK semantics keep this side-effect-free.
  P33 — ``scheduler_stuck_count`` exposure for stuck-row alerting.

Note on FK enforcement: SQLite does NOT enforce FOREIGN KEY
constraints unless ``PRAGMA foreign_keys=ON`` is set per-connection,
and the project's ``_connect`` helper does not set it. So the
sentinel INSERT in check (b) succeeds even though its session_token
is not in gate_states — the check exercises the scheduler_state
write path without needing to seed a corresponding gate_states row.
The production code's reliance on the FK CASCADE for cleanup is a
separate concern (existing pre-S7b behavior); not addressed here.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from typing import Optional

from buildemup.utils.gate_state_storage import _connect, _execute_with_retry
from buildemup.utils.scheduler_state_storage import SchedulerStateStorage

LOGGER = logging.getLogger(__name__)


# ─── Sentinel for the scheduler write-verify INSERT ────────────────
# Any row that escapes the ROLLBACK (would be a SQLite bug) is
# identifiable by this prefix in operational forensics.
_HEALTH_SENTINEL_TOKEN = "__health_sentinel_no_commit__"


# ─── Storage singleton ─────────────────────────────────────────────
# Mirrors the pattern in c3a_endpoint and admin_endpoint. Lazy init
# avoids opening SQLite at import time.
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


# ─── Build-info helpers (best-effort env reads) ────────────────────
def _build_version() -> str:
    """Read BUILDEMUP_VERSION env var; default to 'unknown'."""
    return os.environ.get("BUILDEMUP_VERSION", "unknown")


def _build_sha() -> str:
    """Read BUILDEMUP_BUILD_SHA env var; default to 'unknown'."""
    return os.environ.get("BUILDEMUP_BUILD_SHA", "unknown")


# ─── Individual checks (return None on success, error code on fail) ─
def _check_gate_states_writable(db_path: Optional[str] = None) -> Optional[str]:
    """(a) BEGIN IMMEDIATE + ROLLBACK on the gate_states database.

    Confirms the WAL is functional and the writer slot is acquirable.
    No data is written.
    """
    try:
        with _connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("ROLLBACK")
    except sqlite3.OperationalError as exc:
        LOGGER.warning(
            "health: gate_states write-verify failed: %r", exc,
        )
        return "wal_unwritable"
    except Exception as exc:
        LOGGER.warning(
            "health: gate_states write-verify unexpected error: %r", exc,
        )
        return "internal"
    return None


def _check_scheduler_writable(db_path: Optional[str] = None) -> Optional[str]:
    """(b) BEGIN IMMEDIATE + INSERT sentinel + ROLLBACK on scheduler_state.

    Exercises the actual write path (not just lock acquisition). The
    ROLLBACK undoes the INSERT — table contents are unchanged on success.
    """
    try:
        with _connect(db_path) as conn:
            _execute_with_retry(conn, "BEGIN IMMEDIATE")
            try:
                _execute_with_retry(
                    conn,
                    "INSERT INTO scheduler_state ("
                    " session_token, fire_at, request_id,"
                    " trace_id, created_at"
                    ") VALUES (?, ?, ?, ?, ?)",
                    (
                        _HEALTH_SENTINEL_TOKEN,
                        0,
                        "health-check",
                        None,
                        int(time.time()),
                    ),
                )
            finally:
                # ALWAYS rollback whether the INSERT succeeded or not.
                # If INSERT raised (e.g. UNIQUE conflict because a
                # previous health-check left a row — only possible if
                # SQLite's ROLLBACK itself failed, which we'd want to
                # know about), the ROLLBACK still runs to release
                # the lock; the exception propagates out and we
                # report scheduler_unwritable below.
                _execute_with_retry(conn, "ROLLBACK")
    except sqlite3.OperationalError as exc:
        LOGGER.warning(
            "health: scheduler_state write-verify failed: %r", exc,
        )
        return "scheduler_unwritable"
    except sqlite3.IntegrityError as exc:
        # Sentinel already present (UNIQUE PK conflict) — a prior
        # health-check failed to roll back. Surface as unwritable so
        # operators investigate, but distinguishable in the log.
        LOGGER.warning(
            "health: scheduler_state sentinel collision (rollback "
            "previously failed?): %r", exc,
        )
        return "scheduler_unwritable"
    except Exception as exc:
        LOGGER.warning(
            "health: scheduler_state write-verify unexpected error: %r",
            exc,
        )
        return "internal"
    return None


def _check_tables_present(db_path: Optional[str] = None) -> Optional[str]:
    """(c) Both required tables exist in sqlite_master."""
    try:
        with _connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' "
                "AND name IN ('gate_states', 'scheduler_state')"
            ).fetchall()
        names = {row[0] for row in rows}
        if "gate_states" not in names or "scheduler_state" not in names:
            LOGGER.warning(
                "health: tables_present check failed; found=%r", names,
            )
            return "tables_missing"
    except Exception as exc:
        LOGGER.warning(
            "health: tables_present check unexpected error: %r", exc,
        )
        return "internal"
    return None


# ─── Public handler ────────────────────────────────────────────────
def handle_health(
    db_path: Optional[str] = None,
) -> tuple[int, dict]:
    """GET /health — runtime health probe. Spec § 8.4.

    Args:
        db_path: optional override for unit tests. Production callers
                 (server.py) pass nothing; the default db path is
                 resolved by ``_connect``.

    Returns:
        (200, {ok=True, ...diagnostics...}) when all critical checks
        pass; (503, {ok=False, code=...}) when any critical check
        fails.

    Critical checks (any failure → 503): (a) gate_states writable,
    (b) scheduler_state writable, (c) tables present.

    Diagnostic fields (do NOT cause 503): scheduler_due_count,
    scheduler_stuck_count. If the diagnostic call itself raises, the
    field is reported as -1 and a WARNING is logged — but the overall
    response stays 200 if the critical checks all passed.
    """
    # (a) gate_states writable
    err = _check_gate_states_writable(db_path)
    if err:
        return 503, {"ok": False, "code": err}

    # (b) scheduler_state writable
    err = _check_scheduler_writable(db_path)
    if err:
        return 503, {"ok": False, "code": err}

    # (c) tables present
    err = _check_tables_present(db_path)
    if err:
        return 503, {"ok": False, "code": err}

    # (d) and (e) — diagnostic; never 503
    storage = _scheduler_state_storage()
    now = int(time.time())
    try:
        due_count = storage.count_due(now)
    except Exception as exc:
        LOGGER.warning(
            "health: count_due() failed: %r", exc,
        )
        due_count = -1
    try:
        stuck_count = storage.count_stuck()
    except Exception as exc:
        LOGGER.warning(
            "health: count_stuck() failed: %r", exc,
        )
        stuck_count = -1

    return 200, {
        "ok": True,
        "wal_writable": True,
        "scheduler_writable": True,
        "tables_present": True,
        "scheduler_due_count": due_count,
        "scheduler_stuck_count": stuck_count,
        "version": _build_version(),
        "build_sha": _build_sha(),
    }


__all__ = [
    "handle_health",
    "reset_scheduler_storage_for_tests",
]
