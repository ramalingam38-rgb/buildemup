"""Tests for session_storage — SQLite WAL persistence."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from buildemup.components.c03b import (
    DEFAULT_CONFIG, C3bSessionStorage, UserActionRequest,
    apply_user_action_orchestrated, start_session,
)
from buildemup.components.c03b.errors import SessionPersistenceError
from buildemup.components.c03b.session_storage import (
    _deserialize_session, _serialize_session,
)
from buildemup.components.c03b.versioning import C3B_SESSION_SCHEMA_VERSION

from .fixtures import make_bundle_3_layouts_happy_path


def test_serialize_session_returns_string():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    payload = _serialize_session(sess)
    assert isinstance(payload, str)
    assert len(payload) > 0


def test_serialize_is_deterministic():
    """Same session → same bytes (replay)."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    p1 = _serialize_session(sess)
    p2 = _serialize_session(sess)
    assert p1 == p2


def test_round_trip_preserves_session():
    """Save + load = original."""
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b.db"
        storage = C3bSessionStorage(db)
        orig = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        restored = storage.load(orig.session_id)
        assert restored.session_id == orig.session_id
        assert restored.current_status == orig.current_status
        assert len(restored.tweak_option_sets) == len(orig.tweak_option_sets)


def test_load_unknown_session_returns_none():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b.db"
        storage = C3bSessionStorage(db)
        assert storage.load("nonexistent_session_id") is None


def test_schema_version_mismatch_raises():
    """Deserialize with wrong schema_version → SessionPersistenceError."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    payload = _serialize_session(sess)
    # Inject wrong schema version
    bad = payload.replace(
        f'"c3b_schema_version":{C3B_SESSION_SCHEMA_VERSION}',
        f'"c3b_schema_version":{C3B_SESSION_SCHEMA_VERSION + 99}',
    )
    with pytest.raises(SessionPersistenceError):
        _deserialize_session(bad)


def test_persistence_after_user_action():
    """Apply an action, persist, load, verify state matches."""
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b.db"
        storage = C3bSessionStorage(db)
        sess = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        target = sess.tweak_option_sets[0].tweaks[0]
        sess2 = apply_user_action_orchestrated(
            sess, UserActionRequest("accepted_tweak", chosen_tweak_id=target.tweak_id),
            DEFAULT_CONFIG, storage=storage,
        )
        restored = storage.load(sess2.session_id)
        assert restored.iteration_count == sess2.iteration_count
        assert len(restored.session_history) == 1


def test_round_trip_preserves_canonical_signature():
    """R6: serialization+deserialization must NOT change canonical sig."""
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b.db"
        storage = C3bSessionStorage(db)
        orig = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        restored = storage.load(orig.session_id)
        assert restored.canonical_replay_signature == orig.canonical_replay_signature


def test_db_file_created_on_init():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b_new.db"
        assert not db.exists()
        _ = C3bSessionStorage(db)
        assert db.exists()
