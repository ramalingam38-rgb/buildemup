"""BuildemUp/BuildEase — Gate state storage (Component 3a Session 7a).

SQLite-backed persistence for ExtremeCaseGate sessions. Stdlib only.

Mirrors `utils/brief_storage.py` (v0.9 Session B) with the v0.3 spec
hardenings:

  P5  WAL mode + transient-lock retry (3 attempts, exponential backoff)
  P11 Per-token single-flight lock — read-state → compute → save sequence
      is serialised on a single token across threads
  P12 brief_to_session uniqueness index for /check idempotency
  P13 Atomic state + idempotency-cache co-write (single UPDATE, BEGIN
      IMMEDIATE)

Tokens are 24-char hex (12 random bytes), TTL 30 days by default.

What this does NOT do (deferred to S7b):
  - No background daemon for prune (only prune-on-save)
  - No multi-process write coordination (stdlib http.server is single-
    process; not needed for v0.1)
  - No Postgres backend (B-### v1.0 swap)
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
import time
from typing import Optional

from buildemup.components.c03a.gate_state import GateState


# ─── Configuration ───────────────────────────────────────────────────
DEFAULT_DB_PATH = "/tmp/buildemup_gate_states.db"
DEFAULT_TTL_DAYS = 30
TOKEN_BYTES = 12                                # 96-bit entropy, 24 hex
MAX_PAYLOAD_BYTES = 1024 * 1024                 # 1 MB cap on serialized state

# P5 retry tuning (round 1 #5)
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_S = (0.05, 0.10, 0.20)            # 50/100/200 ms

# P11 single-flight: per-process token lock dict (round 2 #15).
# Single-process deployment (stdlib http.server) makes this sufficient.
_session_locks: dict[str, threading.Lock] = {}
_session_locks_master: threading.Lock = threading.Lock()


def _db_path() -> str:
    # B-051 (S54 fix): DEPLOY.md documents BUILDEMUP_DATABASE_PATH as the
    # primary env var for the c3a gate DB, but this code only read
    # BUILDEMUP_GATE_DB_PATH. Operators following the docs got a silent
    # default. Read both: specific (BUILDEMUP_GATE_DB_PATH) wins, general
    # (BUILDEMUP_DATABASE_PATH) is the documented fallback, default last.
    return (
        os.environ.get("BUILDEMUP_GATE_DB_PATH")
        or os.environ.get("BUILDEMUP_DATABASE_PATH")
        or DEFAULT_DB_PATH
    )


def _ttl_seconds() -> float:
    days = float(
        os.environ.get("BUILDEMUP_GATE_TTL_DAYS", str(DEFAULT_TTL_DAYS))
    )
    return days * 86400.0


# ─── Exceptions ──────────────────────────────────────────────────────
class GateStateStorageError(Exception):
    """Base for storage errors."""


class TokenNotFoundError(GateStateStorageError):
    """Raised when resume() can't find the token (missing or expired)."""


class PayloadTooLargeError(GateStateStorageError):
    """Raised when serialized state exceeds MAX_PAYLOAD_BYTES."""


# ─── Connection helpers ─────────────────────────────────────────────
def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode (P5)."""
    path = db_path or _db_path()
    # Ensure parent dir exists for non-default paths
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10.0, isolation_level=None)
    # P5: WAL mode (idempotent across opens)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")  # WAL-recommended
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if not present."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS gate_states ("
        " token TEXT PRIMARY KEY,"
        " state_json TEXT NOT NULL,"
        " saved_at REAL NOT NULL,"
        " expires_at REAL NOT NULL,"
        " is_terminal INTEGER NOT NULL DEFAULT 0,"
        " last_request_id TEXT,"
        " last_response_json TEXT"
        ")"
    )
    # P12: brief_to_session uniqueness index for /check idempotency.
    # PRIMARY KEY enforces uniqueness on (brief_token, request_id).
    conn.execute(
        "CREATE TABLE IF NOT EXISTS brief_to_session ("
        " brief_token TEXT NOT NULL,"
        " request_id TEXT NOT NULL,"
        " session_token TEXT NOT NULL,"
        " created_at REAL NOT NULL,"
        " PRIMARY KEY (brief_token, request_id)"
        ")"
    )
    # P27 (S7b): scheduler_state lives in a SEPARATE table from
    # gate_states. P33: at-least-once delivery with bounded retries
    # via attempt_count + last_attempt_at + fallback_error.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scheduler_state ("
        " session_token TEXT PRIMARY KEY,"
        " fire_at INTEGER NOT NULL,"
        " fallback_fired INTEGER NOT NULL DEFAULT 0,"
        " attempt_count INTEGER NOT NULL DEFAULT 0,"
        " last_attempt_at INTEGER,"
        " fallback_error TEXT,"
        " trace_id TEXT,"
        " request_id TEXT NOT NULL,"
        " created_at INTEGER NOT NULL,"
        " FOREIGN KEY (session_token)"
        "   REFERENCES gate_states(token)"
        "   ON DELETE CASCADE"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fallback_due "
        "ON scheduler_state ("
        " fallback_fired, fire_at, attempt_count"
        ")"
    )


def _execute_with_retry(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple = (),
) -> sqlite3.Cursor:
    """Execute with P5 retry on 'database is locked'."""
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError as exc:
            if "database is locked" not in str(exc):
                raise
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_BACKOFF_S[attempt])
    # All attempts exhausted; re-raise
    assert last_exc is not None
    raise last_exc


# ─── Single-flight lock helper (P11) ───────────────────────────────
def get_session_lock(token: str) -> threading.Lock:
    """Return (creating if needed) the per-token single-flight lock.

    The endpoint layer holds this lock across the read-state → compute
    → save sequence so two concurrent requests on the same token are
    serialised. Per-process scope (stdlib http.server is single-process).
    """
    with _session_locks_master:
        lock = _session_locks.get(token)
        if lock is None:
            lock = threading.Lock()
            _session_locks[token] = lock
        return lock


# ─── Storage class ─────────────────────────────────────────────────
class GateStateStorage:
    """SQLite-backed save/resume for ExtremeCaseGate sessions.

    Public surface:
      save(state, request_id=None, response=None) -> token
      save_existing(token, state, request_id, response) -> None
      resume(token) -> (GateState, last_request_id, last_response)
      mark_terminal(token) -> None
      register_brief_session(brief_token, request_id, session_token) -> bool
      lookup_brief_session(brief_token, request_id) -> Optional[str]

    No public delete(): terminal sessions persist until TTL expiry
    (P4 — round 1 #4).
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or _db_path()
        # Ensure schema exists at construction time
        with _connect(self._db_path) as conn:
            _ensure_schema(conn)

    # ─── Save a NEW session (gate.start path) ──────────────────────
    def save(
        self,
        state: GateState,
        *,
        request_id: Optional[str] = None,
        response: Optional[dict] = None,
    ) -> str:
        """Persist a fresh GateState; return the generated token.

        The token returned is also state.session_id; the caller is
        expected to have used a fresh token via _new_token() when
        invoking gate.start(session_id=...).

        request_id + response are stored for idempotency replay
        (P2 + P13).
        """
        token = state.session_id
        if not token:
            raise ValueError("GateState.session_id must be set before save")
        state_json = self._serialize_state(state)
        response_json = (
            json.dumps(response, sort_keys=True, ensure_ascii=False)
            if response is not None
            else None
        )
        now = time.time()
        expires_at = now + _ttl_seconds()
        is_terminal = 1 if state.is_done else 0

        with _connect(self._db_path) as conn:
            self._prune_expired(conn, now)
            # P13 atomic write — single UPDATE / INSERT
            _execute_with_retry(conn, "BEGIN IMMEDIATE")
            try:
                _execute_with_retry(
                    conn,
                    "INSERT INTO gate_states "
                    "(token, state_json, saved_at, expires_at, is_terminal, "
                    " last_request_id, last_response_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(token) DO UPDATE SET "
                    " state_json=excluded.state_json,"
                    " saved_at=excluded.saved_at,"
                    " expires_at=excluded.expires_at,"
                    " is_terminal=excluded.is_terminal,"
                    " last_request_id=excluded.last_request_id,"
                    " last_response_json=excluded.last_response_json",
                    (
                        token, state_json, now, expires_at, is_terminal,
                        request_id, response_json,
                    ),
                )
                _execute_with_retry(conn, "COMMIT")
            except Exception:
                _execute_with_retry(conn, "ROLLBACK")
                raise
        return token

    # ─── Save UPDATE (gate.apply_user_decision / abort path) ────────
    def save_existing(
        self,
        token: str,
        state: GateState,
        *,
        request_id: str,
        response: dict,
    ) -> None:
        """Update an existing session row WITH its idempotency cache.

        Used by /resolve, /abort, /cba-verified, /cba-fallback-continue
        — all of which receive a request_id and produce a cacheable
        response. Atomicity is per P13 (single UPDATE in a transaction).
        """
        state_json = self._serialize_state(state)
        response_json = json.dumps(
            response, sort_keys=True, ensure_ascii=False,
        )
        now = time.time()
        is_terminal = 1 if state.is_done else 0
        # We do NOT extend expires_at on update — TTL is from creation.

        with _connect(self._db_path) as conn:
            _execute_with_retry(conn, "BEGIN IMMEDIATE")
            try:
                cur = _execute_with_retry(
                    conn,
                    "UPDATE gate_states SET "
                    " state_json=?, saved_at=?, is_terminal=?,"
                    " last_request_id=?, last_response_json=? "
                    "WHERE token=?",
                    (
                        state_json, now, is_terminal,
                        request_id, response_json, token,
                    ),
                )
                if cur.rowcount == 0:
                    # B-043 fix (P19): don't manually rollback —
                    # the outer except handles the single rollback.
                    raise TokenNotFoundError(
                        f"save_existing: token not found: {token!r}"
                    )
                _execute_with_retry(conn, "COMMIT")
            except Exception:
                _execute_with_retry(conn, "ROLLBACK")
                raise

    # ─── Resume ────────────────────────────────────────────────────
    def resume(
        self, token: str,
    ) -> tuple[GateState, Optional[str], Optional[dict]]:
        """Fetch (state, last_request_id, last_response).

        Raises TokenNotFoundError on missing or TTL-expired tokens.
        Terminal sessions are returned normally (P3 + P4 — round 1 #3
        + #4).
        """
        with _connect(self._db_path) as conn:
            row = _execute_with_retry(
                conn,
                "SELECT state_json, expires_at, last_request_id, "
                " last_response_json "
                "FROM gate_states WHERE token=?",
                (token,),
            ).fetchone()
        if row is None:
            raise TokenNotFoundError(f"unknown token: {token!r}")
        state_json, expires_at, last_request_id, last_response_json = row
        if expires_at < time.time():
            raise TokenNotFoundError(f"expired token: {token!r}")
        state = self._deserialize_state(state_json)
        last_response = (
            json.loads(last_response_json)
            if last_response_json is not None
            else None
        )
        return state, last_request_id, last_response

    # ─── /status read accessor (S8 § 5a.4) ─────────────────────────
    # ADDITIVE-ONLY method introduced for the new GET
    # /api/extreme-case/status endpoint. Pure read; no behavioral
    # change to any existing call site. Returns the storage-level
    # snapshot fields the /status response needs (is_terminal,
    # saved_at, optional termination_reason) without coupling the
    # endpoint module to the gate_states schema.
    #
    # Lightweight by design: does NOT round-trip through
    # GateState.from_dict — /status only needs three primitive
    # fields and parsing the full GateState would (a) require every
    # gate_states row to satisfy the full constructor schema even
    # for rows hand-seeded by tests, and (b) waste cycles on a
    # read-only API path. We pull termination_reason directly out of
    # the state_json dict and return it as a string-or-None.
    def load_status_row(
        self, token: str,
    ) -> Optional[tuple[Optional[str], bool, float]]:
        """Fetch (termination_reason_value, is_terminal, saved_at) for
        /status.

        Returns None if the token is unknown OR TTL-expired (parity
        with `resume()`). Does NOT update or invalidate anything.
        """
        with _connect(self._db_path) as conn:
            row = _execute_with_retry(
                conn,
                "SELECT state_json, expires_at, is_terminal, saved_at "
                "FROM gate_states WHERE token=?",
                (token,),
            ).fetchone()
        if row is None:
            return None
        state_json, expires_at, is_terminal, saved_at = row
        if expires_at < time.time():
            return None
        # Lightweight extract: just termination_reason. Tolerant of
        # rows that don't carry it (None / missing → None).
        termination_reason: Optional[str] = None
        try:
            payload = json.loads(state_json) if state_json else {}
            tr = payload.get("termination_reason")
            if tr is not None:
                # Stored as enum .value (string). Defend if a future
                # writer stores the enum name differently.
                termination_reason = str(tr)
        except (json.JSONDecodeError, AttributeError, TypeError):
            termination_reason = None
        return termination_reason, bool(is_terminal), float(saved_at)

    # ─── Mark terminal (advisory; the row is also flagged on save) ─
    def mark_terminal(self, token: str) -> None:
        """Set is_terminal=1 explicitly. Idempotent."""
        with _connect(self._db_path) as conn:
            _execute_with_retry(
                conn,
                "UPDATE gate_states SET is_terminal=1 WHERE token=?",
                (token,),
            )

    # ─── /check idempotency: brief→session lookup table ───────────
    def register_brief_session(
        self,
        brief_token: str,
        request_id: str,
        session_token: str,
    ) -> bool:
        """Record (brief_token, request_id) → session_token mapping.

        Returns True if registered; False if the (brief_token,
        request_id) pair already exists (uniqueness collision per P12).
        On collision, the caller looks up the existing session_token
        via lookup_brief_session() and replays its cached response.
        """
        try:
            with _connect(self._db_path) as conn:
                _execute_with_retry(
                    conn,
                    "INSERT INTO brief_to_session "
                    "(brief_token, request_id, session_token, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (brief_token, request_id, session_token, time.time()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def lookup_brief_session(
        self,
        brief_token: str,
        request_id: str,
    ) -> Optional[str]:
        """Return session_token if (brief_token, request_id) is registered."""
        with _connect(self._db_path) as conn:
            row = _execute_with_retry(
                conn,
                "SELECT session_token FROM brief_to_session "
                "WHERE brief_token=? AND request_id=?",
                (brief_token, request_id),
            ).fetchone()
        return row[0] if row is not None else None

    # ─── Serialization (uses GateState.to_dict / from_dict) ────────
    @staticmethod
    def _serialize_state(state: GateState) -> str:
        payload = state.to_dict()
        s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        if len(s.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise PayloadTooLargeError(
                f"serialized GateState exceeds {MAX_PAYLOAD_BYTES} bytes"
            )
        return s

    @staticmethod
    def _deserialize_state(state_json: str) -> GateState:
        payload = json.loads(state_json)
        return GateState.from_dict(payload)

    # ─── Internal: prune expired rows on every save (BriefStorage pattern) ─
    @staticmethod
    def _prune_expired(conn: sqlite3.Connection, now: float) -> None:
        _execute_with_retry(
            conn,
            "DELETE FROM gate_states WHERE expires_at < ?",
            (now,),
        )
        _execute_with_retry(
            conn,
            "DELETE FROM brief_to_session WHERE created_at < ?",
            (now - _ttl_seconds(),),
        )


# ─── Token generation ────────────────────────────────────────────────
def new_token() -> str:
    """Generate a fresh 24-char hex token (96 bits of entropy)."""
    return secrets.token_hex(TOKEN_BYTES)


__all__ = [
    "GateStateStorage",
    "GateStateStorageError",
    "TokenNotFoundError",
    "PayloadTooLargeError",
    "MAX_PAYLOAD_BYTES",
    "get_session_lock",
    "new_token",
]
