"""Tests for orchestrator — end-to-end workflow + persistence."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from buildemup.components.c03b import (
    DEFAULT_CONFIG, C3bRuntimeConfig, C3bSessionStorage, UserActionRequest,
    apply_user_action_orchestrated, complete_subset_rerun_orchestrated,
    finalize_session, start_session,
)

from .fixtures import (
    make_bundle_3_layouts_happy_path,
    make_bundle_preview_mode,
    make_problem_check,
    make_problem_report,
)


def test_start_session_happy_path_in_memory():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    assert sess.current_status == "open_for_user_input"
    assert len(sess.tweak_option_sets) == 3


def test_start_session_terminal_on_preview_mode():
    sess = start_session(make_bundle_preview_mode(), DEFAULT_CONFIG)
    assert sess.current_status == "abandoned_no_tweaks"


def test_full_workflow_in_memory():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    target = sess.tweak_option_sets[0].tweaks[0]
    sess = apply_user_action_orchestrated(
        sess, UserActionRequest("accepted_tweak", chosen_tweak_id=target.tweak_id),
        DEFAULT_CONFIG,
    )
    assert sess.current_status == "awaiting_subset_rerun"


def test_full_workflow_with_storage():
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b_orchestrator.db"
        storage = C3bSessionStorage(db)
        sess = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        # Verify persisted
        restored = storage.load(sess.session_id)
        assert restored is not None
        assert restored.session_id == sess.session_id


def test_persistence_round_trip_preserves_signature():
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b_rt.db"
        storage = C3bSessionStorage(db)
        sess = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        restored = storage.load(sess.session_id)
        assert restored.canonical_replay_signature == sess.canonical_replay_signature


def test_complete_subset_rerun_orchestrated_routes_correctly():
    """Drive a MEDIUM tweak, complete rerun, verify state transitions."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    medium_tweak = next(
        t for opt_set in sess.tweak_option_sets for t in opt_set.tweaks
        if t.severity_tier == "medium"
    )
    sess = apply_user_action_orchestrated(
        sess,
        UserActionRequest("accepted_tweak", chosen_tweak_id=medium_tweak.tweak_id),
        DEFAULT_CONFIG,
    )
    assert sess.current_status == "awaiting_subset_rerun"

    # Simulate orchestrator-managed rerun (no regression)
    pre_pr = bundle.problem_reports[0]
    sess = complete_subset_rerun_orchestrated(
        sess, medium_tweak.tweak_id, pre_pr, pre_pr, DEFAULT_CONFIG,
    )
    assert sess.current_status == "open_for_user_input"


def test_finalize_session_runs_phase_zeta():
    """Drive a session to resolved state, then finalize_session populates ζ."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    layout_id = sess.tweak_option_sets[0].layout_id
    sess = apply_user_action_orchestrated(
        sess,
        UserActionRequest("finalized_layout_choice", finalize_layout_id=layout_id),
        DEFAULT_CONFIG,
    )
    assert sess.current_status == "resolved_selection_ready"
    final = finalize_session(sess, DEFAULT_CONFIG)
    assert final.resolved_selection is not None


def test_storage_overwrites_on_replay():
    """REPLACE semantics: same session_id, second save overwrites first."""
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b_rep.db"
        storage = C3bSessionStorage(db)
        sess1 = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        # Apply action — generates a new state under same session_id
        target = sess1.tweak_option_sets[0].tweaks[0]
        sess2 = apply_user_action_orchestrated(
            sess1, UserActionRequest("rejected_tweak", chosen_tweak_id=target.tweak_id),
            DEFAULT_CONFIG, storage=storage,
        )
        # Storage now reflects sess2, not sess1
        restored = storage.load(sess1.session_id)
        assert restored.iteration_count == sess2.iteration_count


def test_list_session_ids_returns_lex_asc():
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b_list.db"
        storage = C3bSessionStorage(db)
        s1 = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        s2 = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        s3 = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        ids = storage.list_session_ids()
        assert ids == tuple(sorted(ids))
        assert set(ids) == {s1.session_id, s2.session_id, s3.session_id}


def test_storage_delete():
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b_del.db"
        storage = C3bSessionStorage(db)
        sess = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        assert storage.delete(sess.session_id) is True
        assert storage.load(sess.session_id) is None
        assert storage.delete(sess.session_id) is False    # already gone


def test_strict_vs_warn_mode():
    bundle = make_bundle_3_layouts_happy_path()
    strict = C3bRuntimeConfig(strict_mode="strict")
    warn = C3bRuntimeConfig(strict_mode="warn")
    # Both should succeed on happy-path
    s1 = start_session(bundle, strict)
    s2 = start_session(bundle, warn)
    assert s1.current_status == s2.current_status == "open_for_user_input"
