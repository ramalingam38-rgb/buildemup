"""
B-050 + B-051 — SQLite FK enforcement and env-var name drift.

B-050: BriefStorage._connect didn't enable foreign_keys PRAGMA. Without
it, FK constraints in schema are not enforced — orphans accumulate.
Fix: add `conn.execute("PRAGMA foreign_keys = ON")` after WAL.

B-051: gate_state_storage._db_path() read only BUILDEMUP_GATE_DB_PATH,
but DEPLOY.md documents BUILDEMUP_DATABASE_PATH as the gate DB env
var. Operators following the docs got a silent default. Fix: support
both with documented precedence (specific wins, general fallback).
"""
from __future__ import annotations

import os
import tempfile
import sqlite3
from pathlib import Path

import pytest


# ─── B-050: SQLite FK enforcement ─────────────────────────────────────

def test_brief_storage_enables_foreign_keys():
    """Every connection from BriefStorage must have foreign_keys=ON."""
    from buildemup.utils.brief_storage import BriefStorage

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        storage = BriefStorage(db_path=db_path)

        conn = storage._connect()
        try:
            cur = conn.execute("PRAGMA foreign_keys")
            (fk_enabled,) = cur.fetchone()
            assert fk_enabled == 1, (
                "B-050 regression: foreign_keys not enabled on connection. "
                f"Got fk={fk_enabled}; expected 1."
            )
        finally:
            conn.close()


def test_brief_storage_fk_setting_is_per_connection():
    """SQLite FK setting is per-connection — each new _connect() must
    set it again."""
    from buildemup.utils.brief_storage import BriefStorage

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        storage = BriefStorage(db_path=str(Path(tmpdir) / "test.db"))
        for i in range(3):
            conn = storage._connect()
            try:
                (fk,) = conn.execute("PRAGMA foreign_keys").fetchone()
                assert fk == 1, f"FK not enabled on connection #{i}"
            finally:
                conn.close()


# ─── B-051: Env-var fallback precedence ───────────────────────────────

def test_gate_db_path_uses_specific_var_when_set():
    """BUILDEMUP_GATE_DB_PATH wins when set (most-specific)."""
    from buildemup.utils import gate_state_storage as gss

    os.environ.pop("BUILDEMUP_DATABASE_PATH", None)
    os.environ.pop("BUILDEMUP_GATE_DB_PATH", None)
    try:
        os.environ["BUILDEMUP_GATE_DB_PATH"] = "/tmp/specific.db"
        os.environ["BUILDEMUP_DATABASE_PATH"] = "/tmp/general.db"
        assert gss._db_path() == "/tmp/specific.db"
    finally:
        os.environ.pop("BUILDEMUP_GATE_DB_PATH", None)
        os.environ.pop("BUILDEMUP_DATABASE_PATH", None)


def test_gate_db_path_falls_back_to_general_var():
    """B-051 fix: BUILDEMUP_DATABASE_PATH works as documented fallback."""
    from buildemup.utils import gate_state_storage as gss

    os.environ.pop("BUILDEMUP_GATE_DB_PATH", None)
    os.environ.pop("BUILDEMUP_DATABASE_PATH", None)
    try:
        os.environ["BUILDEMUP_DATABASE_PATH"] = "/tmp/general.db"
        result = gss._db_path()
        assert result == "/tmp/general.db", (
            f"B-051 regression: BUILDEMUP_DATABASE_PATH ignored. "
            f"Got {result!r} instead of '/tmp/general.db'."
        )
    finally:
        os.environ.pop("BUILDEMUP_DATABASE_PATH", None)


def test_gate_db_path_falls_back_to_default_when_neither_set():
    """Neither env var set → DEFAULT_DB_PATH."""
    from buildemup.utils import gate_state_storage as gss

    os.environ.pop("BUILDEMUP_GATE_DB_PATH", None)
    os.environ.pop("BUILDEMUP_DATABASE_PATH", None)
    result = gss._db_path()
    assert result == gss.DEFAULT_DB_PATH
