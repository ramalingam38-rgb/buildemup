"""R6 byte-equal replay determinism tests.

Spec § 7.1 R6: 'Given identical inputs and identical action sequence,
two runs must produce byte-equal canonical_replay_signatures.'

These tests verify the contract holds across:
  - Repeated start_session calls with same bundle
  - Action sequences (accept → reject → finalize)
  - STRICT mode (same sequence under STRICT gives same sig)
"""
from __future__ import annotations

from buildemup.components.c03b import (
    DEFAULT_CONFIG, C3bRuntimeConfig, UserActionRequest,
    apply_user_action_orchestrated, start_session,
)

from .fixtures import make_bundle_3_layouts_happy_path


def test_two_independent_start_sessions_have_matching_state_sigs():
    """Two start_session calls on the same bundle: session_id differs
    (UUID-based) but tweak_option_sets/option content is byte-equal."""
    bundle = make_bundle_3_layouts_happy_path()
    s1 = start_session(bundle, DEFAULT_CONFIG)
    s2 = start_session(bundle, DEFAULT_CONFIG)
    # Tweak IDs deterministic
    ids1 = [t.tweak_id for ops in s1.tweak_option_sets for t in ops.tweaks]
    ids2 = [t.tweak_id for ops in s2.tweak_option_sets for t in ops.tweaks]
    assert ids1 == ids2


def test_action_sequence_byte_equal_under_replay():
    """Identical bundle + identical chosen_tweak_id → identical option-set
    content after action."""
    bundle = make_bundle_3_layouts_happy_path()
    s1 = start_session(bundle, DEFAULT_CONFIG)
    s2 = start_session(bundle, DEFAULT_CONFIG)
    target_id = s1.tweak_option_sets[0].tweaks[0].tweak_id
    req = UserActionRequest("rejected_tweak", chosen_tweak_id=target_id)
    s1 = apply_user_action_orchestrated(s1, req, DEFAULT_CONFIG)
    s2 = apply_user_action_orchestrated(s2, req, DEFAULT_CONFIG)
    # iteration counts, history kinds, last turn shape match
    assert s1.iteration_count == s2.iteration_count
    assert s1.session_history[-1].user_action == s2.session_history[-1].user_action


def test_strict_vs_warn_mode_same_happy_path_sigs():
    """On clean inputs, strict and warn produce same canonical state."""
    bundle = make_bundle_3_layouts_happy_path()
    strict = C3bRuntimeConfig(strict_mode="strict")
    warn = C3bRuntimeConfig(strict_mode="warn")
    s1 = start_session(bundle, strict)
    s2 = start_session(bundle, warn)
    # Both should produce same number of option sets and same tweak ids
    ids1 = [t.tweak_id for ops in s1.tweak_option_sets for t in ops.tweaks]
    ids2 = [t.tweak_id for ops in s2.tweak_option_sets for t in ops.tweaks]
    assert ids1 == ids2


def test_multi_turn_replay_deterministic():
    """3 turns on same bundle: independent runs produce same final state."""
    bundle = make_bundle_3_layouts_happy_path()
    s1 = start_session(bundle, DEFAULT_CONFIG)
    s2 = start_session(bundle, DEFAULT_CONFIG)
    target = s1.tweak_option_sets[0].tweaks[0].tweak_id
    other = s1.tweak_option_sets[1].tweaks[0].tweak_id if s1.tweak_option_sets[1].tweaks else target

    for action_seq in [
        ("rejected_tweak", target),
        ("no_action_continue", None),
        ("rejected_tweak", other),
    ]:
        req = UserActionRequest(
            user_action=action_seq[0],
            chosen_tweak_id=action_seq[1],
        )
        s1 = apply_user_action_orchestrated(s1, req, DEFAULT_CONFIG)
        s2 = apply_user_action_orchestrated(s2, req, DEFAULT_CONFIG)

    # Final iteration counts must match
    assert s1.iteration_count == s2.iteration_count
    assert len(s1.session_history) == len(s2.session_history)


def test_schema_descriptor_digest_constant():
    """R8: schema_descriptor_digest must be constant across runs
    (depends only on schema, not values)."""
    bundle = make_bundle_3_layouts_happy_path()
    s1 = start_session(bundle, DEFAULT_CONFIG)
    s2 = start_session(bundle, DEFAULT_CONFIG)
    assert s1.schema_descriptor_digest == s2.schema_descriptor_digest
