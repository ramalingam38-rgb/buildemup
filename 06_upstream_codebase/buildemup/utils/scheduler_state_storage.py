"""BuildemUp/BuildEase — Scheduler state storage (Component 3a Session 7b).

SQLite-backed persistence for the 24h CBA-fallback scheduler. Stdlib
only. Runs against the SAME SQLite file as gate_state_storage.py
(`scheduler_state` table created via gate_state_storage._ensure_schema
extension per P27 / spec § 1.2 (ii) and § 7.4).

Spec invariants implemented in this module:

  P21 — Scheduler hook idempotent at the worker via P2 reuse on the
        API side (this module records the request_id; the API layer
        does the deduplication on tick-driven POSTs).
  P27 — Scheduler state lives in a separate `scheduler_state` table,
        not on `gate_states`. The `gate_states` schema is unchanged.
  P28 — Atomic claim via single `UPDATE ... RETURNING` statement
        with cooldown filter; race-free under parallel ticks.
  P29 — `trace_id` persisted on the scheduler_state row at enqueue
        time so the admin tick can forward it on the outbound POST.
  P31 — Server-time authoritative for scheduler firing; the dequeue
        compares against caller-supplied `now` (from `time.time()`
        in the tick handler), not against any caller-influenced
        timestamp.
  P33 — At-least-once delivery with bounded retries: claim sets
        attempt_count + last_attempt_at WITHOUT committing
        fallback_fired; commit_fired is a separate UPDATE called
        after a successful POST. Cap at 3 attempts; rows hitting the
        cap stay unprocessed and are surfaced via count_stuck() →
        /health.
  P35 — Admin reset is single-row, idempotent, atomic, audited. The
        reset() method uses BEGIN IMMEDIATE so the read+update is
        race-free vs concurrent ticks.

Requires SQLite >= 3.35 for `UPDATE ... RETURNING` (P28, used in
claim_due). Version check is enforced at startup via
`_validate_config()` per P32 (see api/server.py); this module
itself does not assert at import time.
"""
from __future__ import annotations

import enum
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

from buildemup.utils.gate_state_storage import (
    _connect,
    _execute_with_retry,
    _ensure_schema,
)

LOGGER = logging.getLogger(__name__)


# ─── Configuration ───────────────────────────────────────────────────
# Cooldown between successive claim attempts on the same row, in
# seconds. Default 900s (15 min) matches the Railway cron interval —
# a row whose POST failed on tick N becomes eligible for re-claim on
# tick N+1.
DEFAULT_COOLDOWN_S = 900

# Retry cap per P33. Rows reaching this cap stay unprocessed (until
# manual P35 reset or expiry via gate_states FK CASCADE on TTL).
RETRY_CAP = 3

# Drift threshold for WARNING log lines (round 1 #15). Logged when a
# claimed row's fire_at is more than this many seconds older than now.
DRIFT_WARN_S = 1800  # 30 min

# Max length of fallback_error text stored per row. Prevents DB / WAL
# bloat from large exception strings (multi-KB stack traces, verbose
# downstream error bodies). Per session-26 critique-round patch:
# additive within spec bounds (the spec specifies the column type as
# TEXT but not a size cap). Truncation is post-hoc — callers can
# build whatever error string they want; this module clips before
# persisting.
FALLBACK_ERROR_MAX_LEN = 256


# ─── Outcomes for the admin reset endpoint (P35) ────────────────────
class ResetOutcome(enum.Enum):
    RESET = "reset"
    ALREADY_FIRED = "already_fired"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class ResetResult:
    """Result of SchedulerStateStorage.reset(). P35."""
    outcome: ResetOutcome
    was_stuck: bool = False
    prior_attempt_count: int = 0
    prior_fallback_error: Optional[str] = None


# ─── Claimed-row tuple shape (returned by claim_due) ────────────────
# (session_token, trace_id, request_id, fire_at, attempt_count)
# Documented as a tuple rather than a dataclass to keep the SQL
# RETURNING binding direct.
ClaimedRow = tuple[str, Optional[str], str, int, int]


# ─── Exceptions ─────────────────────────────────────────────────────
class SchedulerStateStorageError(Exception):
    """Base for scheduler-state storage errors."""


# ─── Storage class ──────────────────────────────────────────────────
class SchedulerStateStorage:
    """SQLite-backed scheduler state.

    Shares the SQLite file with GateStateStorage (separate table per
    P27). The schema is created via gate_state_storage._ensure_schema
    on first connection — no separate init required from this class.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path  # None → resolves via _connect at call-time

        # Ensure schema is present (idempotent CREATE TABLE IF NOT
        # EXISTS in _ensure_schema). This piggybacks on
        # gate_state_storage's _ensure_schema since v0.4 extends it
        # to create scheduler_state.
        with _connect(self._db_path) as conn:
            _ensure_schema(conn)

    # ─── enqueue ───────────────────────────────────────────────────
    def enqueue(
        self,
        session_token: str,
        fire_at: int,
        request_id: str,
        *,
        trace_id: Optional[str] = None,
    ) -> None:
        """Insert (or upsert) a scheduler row at pause time.

        Idempotent: if called twice for the same session_token (e.g.
        during a P2 idempotency replay), the second call updates the
        existing row rather than failing. This preserves the original
        fire_at and request_id since SQLite UPSERT keeps the row's
        identity; the trace_id is refreshed.

        P29: trace_id stored so the admin tick can forward it on
        outbound POST as X-Trace-Id.
        P31: caller-supplied `fire_at` MUST be a server-time UNIX
        timestamp (the c3a_endpoint pause path computes
        `int(time.time()) + 86400`). This module does not validate
        the source; the contract lives in the caller.
        """
        now = int(time.time())
        with _connect(self._db_path) as conn:
            _execute_with_retry(conn, "BEGIN IMMEDIATE")
            try:
                _execute_with_retry(
                    conn,
                    "INSERT INTO scheduler_state ("
                    " session_token, fire_at, request_id,"
                    " trace_id, created_at"
                    ") VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(session_token) DO UPDATE SET"
                    " trace_id = excluded.trace_id",
                    (session_token, fire_at, request_id,
                     trace_id, now),
                )
                _execute_with_retry(conn, "COMMIT")
            except Exception:
                _execute_with_retry(conn, "ROLLBACK")
                raise

    # ─── claim_due (P28 + P33 atomic claim) ────────────────────────
    def claim_due(
        self,
        now: int,
        cooldown: int = DEFAULT_COOLDOWN_S,
        limit: int = 100,
    ) -> list[ClaimedRow]:
        """Atomically claim due rows for processing.

        Filters by:
          fallback_fired = 0
          AND attempt_count < RETRY_CAP
          AND fire_at <= now
          AND (last_attempt_at IS NULL OR last_attempt_at < now - cooldown)

        Atomically increments attempt_count and sets last_attempt_at
        on the matching rows. Returns the claimed tuples for the
        caller to POST.

        P28: single UPDATE...RETURNING is the atomicity boundary —
        two parallel ticks claiming the same row: only one wins.
        P33: claim is NOT a commit. fallback_fired stays 0; the
        caller MUST call commit_fired() after a successful POST.
        Failed POSTs leave the row unfired but cooldown-protected
        for the next tick.
        """
        with _connect(self._db_path) as conn:
            cur = _execute_with_retry(
                conn,
                "UPDATE scheduler_state "
                "SET attempt_count = attempt_count + 1,"
                "    last_attempt_at = ? "
                "WHERE rowid IN ("
                " SELECT rowid FROM scheduler_state"
                " WHERE fallback_fired = 0"
                "   AND attempt_count < ?"
                "   AND fire_at <= ?"
                "   AND ("
                "      last_attempt_at IS NULL"
                "      OR last_attempt_at < ?"
                "   )"
                " ORDER BY fire_at ASC"
                " LIMIT ?"
                ") "
                "RETURNING session_token, trace_id, request_id,"
                "          fire_at, attempt_count",
                (now, RETRY_CAP, now, now - cooldown, limit),
            )
            rows: list[ClaimedRow] = list(cur.fetchall())

        # Drift logging — round 1 #15.
        for row in rows:
            fire_at = row[3]
            drift = now - fire_at
            if drift > DRIFT_WARN_S:
                LOGGER.warning(
                    "scheduler.drift: fallback fired %ds late "
                    "(session_token=%s, trace_id=%s)",
                    drift, _mask_token(row[0]), row[1],
                )
        return rows

    # ─── commit_fired (P33 — successful POST commits the row) ─────
    def commit_fired(self, session_token: str) -> None:
        """Mark a claimed row as successfully fired.

        Called by the admin tick after a successful POST to
        /cba-fallback-continue. P33 distinguishes claim
        (attempt_count++, last_attempt_at) from commit
        (fallback_fired = 1).
        """
        with _connect(self._db_path) as conn:
            _execute_with_retry(conn, "BEGIN IMMEDIATE")
            try:
                _execute_with_retry(
                    conn,
                    "UPDATE scheduler_state "
                    "SET fallback_fired = 1 "
                    "WHERE session_token = ?",
                    (session_token,),
                )
                _execute_with_retry(conn, "COMMIT")
            except Exception:
                _execute_with_retry(conn, "ROLLBACK")
                raise

    # ─── record_error (P33 — failed POST records error text) ──────
    def record_error(
        self,
        session_token: str,
        error_text: str,
    ) -> None:
        """Record the failure error text on a claimed-but-unfired row.

        P33: failed POST → row stays fallback_fired=0, attempt_count
        was already incremented during claim, last_attempt_at set.
        This call adds the diagnostic error string for forensic value
        when an operator pulls stuck rows.

        Per session-26 critique-round patch: error_text is truncated
        to FALLBACK_ERROR_MAX_LEN (256) chars before persisting.
        Prevents DB / WAL bloat from large exception strings (multi-KB
        stack traces, verbose downstream error bodies). The first 256
        chars are typically enough to identify the failure class
        (exception type + message head); deeper diagnostics belong in
        structured logs, not in this row.
        """
        truncated = (error_text or "")[:FALLBACK_ERROR_MAX_LEN]
        with _connect(self._db_path) as conn:
            _execute_with_retry(conn, "BEGIN IMMEDIATE")
            try:
                _execute_with_retry(
                    conn,
                    "UPDATE scheduler_state "
                    "SET fallback_error = ? "
                    "WHERE session_token = ?",
                    (truncated, session_token),
                )
                _execute_with_retry(conn, "COMMIT")
            except Exception:
                _execute_with_retry(conn, "ROLLBACK")
                raise

    # ─── count_due (diagnostic for /health) ────────────────────────
    def count_due(self, now: int) -> int:
        """Number of rows currently due to be claimed.

        Diagnostic field for /health (`scheduler_due_count`). Includes
        rows that would NOT pass the cooldown filter — this is a
        snapshot of "fire_at <= now AND fallback_fired = 0", broader
        than what claim_due would actually claim.
        """
        with _connect(self._db_path) as conn:
            row = _execute_with_retry(
                conn,
                "SELECT COUNT(*) FROM scheduler_state "
                "WHERE fallback_fired = 0 AND fire_at <= ?",
                (now,),
            ).fetchone()
        return int(row[0]) if row else 0

    # ─── count_stuck (P33 stuck-row exposure for /health) ─────────
    def count_stuck(self) -> int:
        """Number of rows that have hit the retry cap.

        Operationally this is the alerting signal: the scheduler can't
        deliver to the API. Recovery path is P35 admin reset.
        """
        with _connect(self._db_path) as conn:
            row = _execute_with_retry(
                conn,
                "SELECT COUNT(*) FROM scheduler_state "
                "WHERE fallback_fired = 0 AND attempt_count >= ?",
                (RETRY_CAP,),
            ).fetchone()
        return int(row[0]) if row else 0

    # ─── reset (P35 admin recovery for stuck rows) ────────────────
    def reset(self, session_token: str) -> ResetResult:
        """Atomically reset attempt fields on a non-fired row.

        Read + conditional update inside a single BEGIN IMMEDIATE
        transaction so a concurrent tick cannot observe a half-reset
        row. P35.

        Outcomes:
          NOT_FOUND      — no row matches the session_token.
          ALREADY_FIRED  — row exists but fallback_fired = 1; refuse
                           reset (un-firing a committed row would be
                           a different operation requiring its own
                           spec). Caller surfaces 409.
          RESET          — attempt_count, last_attempt_at, and
                           fallback_error cleared. was_stuck flag
                           reflects whether the prior attempt_count
                           was at or above the retry cap.

        Idempotent: calling reset twice on the same token is safe; the
        second call zeroes already-zero fields with no effect.
        """
        with _connect(self._db_path) as conn:
            _execute_with_retry(conn, "BEGIN IMMEDIATE")
            try:
                row = _execute_with_retry(
                    conn,
                    "SELECT fallback_fired, attempt_count,"
                    " fallback_error "
                    "FROM scheduler_state "
                    "WHERE session_token = ?",
                    (session_token,),
                ).fetchone()

                if row is None:
                    _execute_with_retry(conn, "COMMIT")
                    return ResetResult(
                        outcome=ResetOutcome.NOT_FOUND,
                    )

                fired, attempt_count, error = row
                if fired == 1:
                    _execute_with_retry(conn, "COMMIT")
                    return ResetResult(
                        outcome=ResetOutcome.ALREADY_FIRED,
                        prior_attempt_count=int(attempt_count),
                        prior_fallback_error=error,
                    )

                _execute_with_retry(
                    conn,
                    "UPDATE scheduler_state "
                    "SET attempt_count = 0,"
                    "    last_attempt_at = NULL,"
                    "    fallback_error = NULL "
                    "WHERE session_token = ?",
                    (session_token,),
                )
                _execute_with_retry(conn, "COMMIT")
                return ResetResult(
                    outcome=ResetOutcome.RESET,
                    was_stuck=(int(attempt_count) >= RETRY_CAP),
                    prior_attempt_count=int(attempt_count),
                    prior_fallback_error=error,
                )
            except Exception:
                _execute_with_retry(conn, "ROLLBACK")
                raise


# ─── Token masking helper (for log lines) ───────────────────────────
def _mask_token(token: str) -> str:
    """Mask a session token for log lines: keep first/last 4 chars."""
    if not token or len(token) <= 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"
