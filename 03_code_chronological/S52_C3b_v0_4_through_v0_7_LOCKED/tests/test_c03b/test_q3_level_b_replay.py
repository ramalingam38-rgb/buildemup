"""Q3 Level B audit replay invariant tests.

Per spec § 9.1 B-C3B-Q3-LEVEL-B-AUDIT-REPLAY-TESTS:
  'Verify every SessionTurn's presented_tweaks record reproduces the
  chosen-from-presented invariant under replay.'

The invariant: for every turn where user_action ∈ {accepted_tweak,
rejected_tweak} and chosen_tweak_id is not None, chosen_tweak_id ∈
turn.presented_tweaks. This is enforced at SessionTurn construction
time by the schema, but we re-verify under replay to catch any
post-deserialize drift.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from buildemup.components.c03b import (
    DEFAULT_CONFIG, C3bSessionStorage, UserActionRequest,
    apply_user_action_orchestrated, start_session,
)

from .fixtures import make_bundle_3_layouts_happy_path


def _verify_q3_invariant(session) -> None:
    """Assert chosen ∈ presented for every applicable turn."""
    for turn in session.session_history:
        if turn.chosen_tweak_id is not None and turn.user_action in (
            "accepted_tweak", "rejected_tweak",
        ):
            assert turn.chosen_tweak_id in turn.presented_tweaks, (
                f"Q3 Level B invariant violated: turn {turn.turn_id} "
                f"chosen={turn.chosen_tweak_id} "
                f"not in presented={turn.presented_tweaks}"
            )


def test_q3_invariant_holds_after_single_accept():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    target = sess.tweak_option_sets[0].tweaks[0]
    sess = apply_user_action_orchestrated(
        sess, UserActionRequest("accepted_tweak", chosen_tweak_id=target.tweak_id),
        DEFAULT_CONFIG,
    )
    _verify_q3_invariant(sess)


def test_q3_invariant_holds_after_reject():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    target = sess.tweak_option_sets[0].tweaks[0]
    sess = apply_user_action_orchestrated(
        sess, UserActionRequest("rejected_tweak", chosen_tweak_id=target.tweak_id),
        DEFAULT_CONFIG,
    )
    _verify_q3_invariant(sess)


def test_q3_invariant_holds_after_multiple_turns():
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    # 3 turns
    target1 = sess.tweak_option_sets[0].tweaks[0].tweak_id
    sess = apply_user_action_orchestrated(
        sess, UserActionRequest("rejected_tweak", chosen_tweak_id=target1),
        DEFAULT_CONFIG,
    )
    if sess.tweak_option_sets[1].tweaks:
        target2 = sess.tweak_option_sets[1].tweaks[0].tweak_id
        sess = apply_user_action_orchestrated(
            sess, UserActionRequest("rejected_tweak", chosen_tweak_id=target2),
            DEFAULT_CONFIG,
        )
    _verify_q3_invariant(sess)


def test_q3_invariant_holds_after_persistence_roundtrip():
    """Invariant survives serialize → deserialize."""
    bundle = make_bundle_3_layouts_happy_path()
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "c3b_q3.db"
        storage = C3bSessionStorage(db)
        sess = start_session(bundle, DEFAULT_CONFIG, storage=storage)
        target = sess.tweak_option_sets[0].tweaks[0]
        sess = apply_user_action_orchestrated(
            sess, UserActionRequest("accepted_tweak", chosen_tweak_id=target.tweak_id),
            DEFAULT_CONFIG, storage=storage,
        )
        restored = storage.load(sess.session_id)
        _verify_q3_invariant(restored)


def test_q3_invariant_no_action_continue_has_none_chosen():
    """no_action_continue turns must have chosen_tweak_id=None."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    sess = apply_user_action_orchestrated(
        sess, UserActionRequest("no_action_continue"), DEFAULT_CONFIG,
    )
    assert sess.session_history[-1].chosen_tweak_id is None


def test_q3_invariant_finalize_has_none_chosen():
    """finalized_layout_choice turns must have chosen_tweak_id=None."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = start_session(bundle, DEFAULT_CONFIG)
    layout_id = sess.tweak_option_sets[0].layout_id
    sess = apply_user_action_orchestrated(
        sess,
        UserActionRequest("finalized_layout_choice", finalize_layout_id=layout_id),
        DEFAULT_CONFIG,
    )
    assert sess.session_history[-1].chosen_tweak_id is None
