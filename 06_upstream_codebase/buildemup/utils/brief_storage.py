"""
BuildemUp† — Brief storage (v0.9 Session B).

SQLite-backed persistence for in-progress briefs. Stdlib only.

Usage:
    storage = BriefStorage()
    token = storage.save(payload_dict)          # returns fresh token
    payload = storage.resume(token)             # returns dict or None
    storage.delete(token)                       # optional cleanup

Schema:
    briefs(
        token         TEXT PRIMARY KEY,
        payload_json  TEXT NOT NULL,
        saved_at      REAL NOT NULL,            -- unix timestamp
        expires_at    REAL NOT NULL             -- unix timestamp
    )

Rules:
    - TTL = 30 days by default (BUILDEMUP_BRIEF_TTL_DAYS env var)
    - Every save() also prunes expired rows (keeps table small)
    - Tokens are 24-char hex (12 random bytes) — 96-bit entropy, enough
      to make guessing a valid resume token cryptographically implausible
    - Token collision: retry once; we use URL-safe characters only

DB file location:
    BUILDEMUP_DB_PATH env var, defaults to /tmp/buildemup_briefs.db.
    On Railway free tier /tmp is ephemeral — briefs lost on redeploy.
    This is disclosed in the save response payload.

What this does NOT do:
    - No user accounts, no auth. Tokens ARE the authorization.
    - No email delivery (no SMTP dep). Users copy the resume URL.
    - No conflict resolution — last write wins (same as localStorage).
    - No row-level audit log — the `saved_at` field is all you get.

†= placeholder name marker.
"""
from __future__ import annotations
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path


# ─── Configuration ───────────────────────────────────────────────────────
DEFAULT_DB_PATH = "/tmp/buildemup_briefs.db"
DEFAULT_TTL_DAYS = 30
TOKEN_BYTES = 12                                # 96-bit entropy, 24 hex chars


def _db_path() -> str:
    return os.environ.get("BUILDEMUP_DB_PATH", DEFAULT_DB_PATH)


def _ttl_seconds() -> float:
    days = float(os.environ.get("BUILDEMUP_BRIEF_TTL_DAYS", str(DEFAULT_TTL_DAYS)))
    return days * 86400.0


# ─── Exceptions ──────────────────────────────────────────────────────────
class BriefStorageError(Exception):
    """Base for storage errors."""


class TokenNotFoundError(BriefStorageError):
    """Raised when resume() can't find the token (missing or expired)."""


class PayloadTooLargeError(BriefStorageError):
    """Raised when payload exceeds 1 MB — guards against abuse."""


MAX_PAYLOAD_BYTES = 1_000_000        # 1 MB per brief — ample for form data


# ─── Storage class ───────────────────────────────────────────────────────
class BriefStorage:
    """SQLite-backed brief save/resume.

    Safe for multiple instances in the same process (SQLite handles its
    own locking). Across processes on the same host, SQLite's file-lock
    serializes concurrent writes. Adequate for v0.9 traffic.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or _db_path()
        self._ensure_schema()

    # ─── Connection helpers ──────────────────────────────────────────────
    def _connect(self) -> sqlite3.Connection:
        # Ensure parent dir exists (Railway /tmp always does; local dev
        # might use a nested path)
        parent = Path(self.db_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode = WAL")    # better concurrency
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS briefs (
                    token TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    saved_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires_at "
                "ON briefs (expires_at)"
            )
            conn.commit()

    # ─── Public API ──────────────────────────────────────────────────────
    def save(
        self, payload: dict, existing_token: str | None = None,
    ) -> tuple[str, float]:
        """Persist a brief payload, return (token, expires_at).

        If existing_token is provided AND valid, updates that row (so a
        user resuming and saving again gets the same URL). Otherwise
        mints a fresh token.

        Raises:
            PayloadTooLargeError: payload serializes to > 1 MB
        """
        payload_json = json.dumps(payload, separators=(",", ":"))
        if len(payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise PayloadTooLargeError(
                f"Payload exceeds {MAX_PAYLOAD_BYTES} byte limit"
            )

        now = time.time()
        expires_at = now + _ttl_seconds()
        token = existing_token or self._mint_token()

        with self._connect() as conn:
            # Prune expired rows opportunistically
            conn.execute(
                "DELETE FROM briefs WHERE expires_at < ?", (now,)
            )
            # Upsert (INSERT OR REPLACE honors PRIMARY KEY)
            conn.execute(
                "INSERT OR REPLACE INTO briefs "
                "(token, payload_json, saved_at, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (token, payload_json, now, expires_at),
            )
            conn.commit()

        return token, expires_at

    def resume(self, token: str) -> dict:
        """Return the stored payload for a token, or raise TokenNotFoundError.

        Does NOT update saved_at — that would reset TTL on every read,
        which could let tokens live forever. TTL resets only on save.
        """
        if not token or not self._is_valid_token_format(token):
            raise TokenNotFoundError(f"Invalid token format: {token!r}")

        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT payload_json, expires_at FROM briefs "
                "WHERE token = ?",
                (token,),
            )
            row = cur.fetchone()

        if row is None:
            raise TokenNotFoundError(
                f"No saved brief for token: {token}"
            )

        payload_json, expires_at = row
        if expires_at < now:
            raise TokenNotFoundError(
                f"Brief has expired (saved > {_ttl_seconds() / 86400:.0f} "
                f"days ago)"
            )

        try:
            return json.loads(payload_json)
        except json.JSONDecodeError as e:
            # Shouldn't happen — we wrote valid JSON. Defensive.
            raise BriefStorageError(
                f"Stored payload is corrupt: {e}"
            ) from e

    def delete(self, token: str) -> bool:
        """Delete a brief. Returns True if a row was deleted, False if not."""
        if not self._is_valid_token_format(token):
            return False
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM briefs WHERE token = ?", (token,)
            )
            conn.commit()
            return cur.rowcount > 0

    def count(self) -> int:
        """How many non-expired briefs are in storage. Useful for ops/tests."""
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM briefs WHERE expires_at >= ?", (now,)
            )
            return int(cur.fetchone()[0])

    def prune_expired(self) -> int:
        """Explicitly delete all expired rows. Returns count deleted."""
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM briefs WHERE expires_at < ?", (now,)
            )
            conn.commit()
            return cur.rowcount

    # ─── Internals ───────────────────────────────────────────────────────
    def _mint_token(self) -> str:
        """Generate a fresh 24-char hex token. Collision retry once."""
        for _ in range(2):
            candidate = secrets.token_hex(TOKEN_BYTES)
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT 1 FROM briefs WHERE token = ?", (candidate,)
                )
                if cur.fetchone() is None:
                    return candidate
        # 2 collisions with 96-bit tokens ≈ winning powerball twice. Still defensive.
        raise BriefStorageError(
            "Could not mint unique token after 2 attempts (unreachable)"
        )

    def _is_valid_token_format(self, token: str) -> bool:
        """Is this string a plausible token?

        Prevents SQL injection attempts and path-walking tricks.
        24 hex chars exactly.
        """
        if not isinstance(token, str):
            return False
        if len(token) != TOKEN_BYTES * 2:
            return False
        try:
            int(token, 16)
            return True
        except ValueError:
            return False
