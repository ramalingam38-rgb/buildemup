"""Tests for Phase ε — user-turn handling, R14, R15, iteration cap."""
from __future__ import annotations

import dataclasses

import pytest

from buildemup.components.c03b.config import C3bRuntimeConfig
from buildemup.components.c03b.errors import LocalTradeoffError
from buildemup.components.c03b.phases.alpha import run_phase_alpha
from buildemup.components.c03b.phases.beta import run_phase_beta
from buildemup.components.c03b.phases.epsilon import (
    UserActionRequest,
    _count_critical_checks,
    _diff_critical_check_ids,
    apply_user_action,
    check_compatibility_against_history,
    complete_subset_rerun,
)
from buildemup.components.c03b.phases.gamma import run_phase_gamma
from buildemup.components.c03b.phases.delta import run_phase_delta

from .fixtures import make_bundle_3_layouts_happy_path, make_problem_check


def _build_ready_session(cfg=None):
    if cfg is None:
        cfg = C3bRuntimeConfig()
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, cfg)
    sess = run_phase_beta(sess, bundle, cfg)
    sess = run_phase_gamma(sess, cfg)
    sess = run_phase_delta(sess, cfg)
    return sess, bundle


# ============================================================
# accept LIGHT / MEDIUM
# ============================================================

def test_accept_light_tweak_status_remains_open():
    sess, _ = _build_ready_session()
    # Find a LIGHT tweak if one exists; if not, skip
    target = None
    for opt_set in sess.tweak_option_sets:
        for t in opt_set.tweaks:
            if t.severity_tier == "light":
                target = t
                break
        if target:
            break
    if target is None:
        pytest.skip("No LIGHT tweak in default fixture")
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=target.tweak_id)
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.current_status in ("open_for_user_input", "iteration_cap_reached")


def test_accept_medium_tweak_status_awaiting_rerun():
    sess, _ = _build_ready_session()
    target = None
    for opt_set in sess.tweak_option_sets:
        for t in opt_set.tweaks:
            if t.severity_tier == "medium":
                target = t
                break
        if target:
            break
    assert target is not None, "Fixture should produce at least one MEDIUM tweak"
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=target.tweak_id)
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.current_status == "awaiting_subset_rerun"
    assert new_sess.session_history[-1].apply_outcome.apply_status == "rerun_queued"


def test_accept_increments_iteration_count():
    sess, _ = _build_ready_session()
    target = sess.tweak_option_sets[0].tweaks[0]
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=target.tweak_id)
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.iteration_count == sess.iteration_count + 1


def test_accept_appends_session_turn():
    sess, _ = _build_ready_session()
    target = sess.tweak_option_sets[0].tweaks[0]
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=target.tweak_id)
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert len(new_sess.session_history) == 1
    assert new_sess.session_history[0].user_action == "accepted_tweak"
    assert new_sess.session_history[0].chosen_tweak_id == target.tweak_id


# ============================================================
# reject_tweak
# ============================================================

def test_reject_bumps_presented_count():
    sess, _ = _build_ready_session()
    target = sess.tweak_option_sets[0].tweaks[0]
    req = UserActionRequest(user_action="rejected_tweak", chosen_tweak_id=target.tweak_id)
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    # The tweak should still be in option sets but with presented_count > 0
    new_target = None
    for opt_set in new_sess.tweak_option_sets:
        for t in opt_set.tweaks:
            if t.tweak_id == target.tweak_id:
                new_target = t
                break
    if new_target is not None:
        assert new_target.presented_count == 1


def test_reject_appends_session_turn():
    sess, _ = _build_ready_session()
    target = sess.tweak_option_sets[0].tweaks[0]
    req = UserActionRequest(user_action="rejected_tweak", chosen_tweak_id=target.tweak_id)
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.session_history[-1].user_action == "rejected_tweak"


# ============================================================
# no_action_continue
# ============================================================

def test_no_action_continue_status_remains():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="no_action_continue")
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.current_status == "open_for_user_input"


def test_no_action_does_not_bump_iteration_count():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="no_action_continue")
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.iteration_count == sess.iteration_count


# ============================================================
# finalize_layout_choice
# ============================================================

def test_finalize_layout_choice_resolves_session():
    sess, _ = _build_ready_session()
    layout_id = sess.tweak_option_sets[0].layout_id
    req = UserActionRequest(user_action="finalized_layout_choice",
                            finalize_layout_id=layout_id)
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.current_status == "resolved_selection_ready"
    assert new_sess.resolved_selection is not None
    assert new_sess.resolved_selection.chosen_layout_id == layout_id


def test_finalize_without_layout_id_raises():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="finalized_layout_choice", finalize_layout_id=None)
    with pytest.raises(LocalTradeoffError):
        apply_user_action(sess, req, C3bRuntimeConfig())


# ============================================================
# kicked_back_to_c3a
# ============================================================

def test_kicked_back_to_c3a_is_terminal():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="kicked_back_to_c3a")
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.current_status == "kicked_back_to_c3a"


def test_subsequent_action_on_terminal_session_raises():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="kicked_back_to_c3a")
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    # Try another action
    follow = UserActionRequest(user_action="no_action_continue")
    with pytest.raises(LocalTradeoffError):
        apply_user_action(new_sess, follow, C3bRuntimeConfig())


# ============================================================
# abandoned_session — picks rank-0 layout
# ============================================================

def test_abandoned_picks_rank_0_layout():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="abandoned_session")
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.current_status == "abandoned_no_tweaks"
    assert new_sess.resolved_selection is not None
    assert new_sess.resolved_selection.chosen_layout_archetype == "cost_efficient"


def test_abandoned_has_zero_applied_tweaks():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="abandoned_session")
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    assert new_sess.resolved_selection.applied_tweaks == ()


# ============================================================
# Q3 Level B invariant — chosen ∈ presented
# ============================================================

def test_chosen_tweak_id_not_in_presented_raises():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id="nonexistent_tweak_id")
    with pytest.raises(LocalTradeoffError):
        apply_user_action(sess, req, C3bRuntimeConfig())


def test_accepted_tweak_requires_chosen_id():
    sess, _ = _build_ready_session()
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=None)
    with pytest.raises(LocalTradeoffError):
        apply_user_action(sess, req, C3bRuntimeConfig())


def test_session_turn_records_presented_tweaks():
    """R12 Q3 Level B: every SessionTurn records what was presented."""
    sess, _ = _build_ready_session()
    target = sess.tweak_option_sets[0].tweaks[0]
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=target.tweak_id)
    new_sess = apply_user_action(sess, req, C3bRuntimeConfig())
    turn = new_sess.session_history[0]
    # chosen_tweak_id MUST be in presented_tweaks
    assert turn.chosen_tweak_id in turn.presented_tweaks


# ============================================================
# Iteration cap (spec § 3 Phase ε step 4)
# ============================================================

def test_iteration_cap_reached_fires_advisory():
    cfg = C3bRuntimeConfig(iteration_cap=1, full_recompute_threshold=1)
    sess, _ = _build_ready_session(cfg)
    target = sess.tweak_option_sets[0].tweaks[0]
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=target.tweak_id)
    new_sess = apply_user_action(sess, req, cfg)
    assert new_sess.current_status == "iteration_cap_reached"
    # Advisory flag should mention the cap
    cap_flags = [
        f for f in new_sess.advisory_flags
        if f.kind == "iteration_cap_warning_nudge"
    ]
    assert len(cap_flags) >= 1


# ============================================================
# R14 regression detection
# ============================================================

def test_count_critical_checks():
    from buildemup.components.c15.schema import CheckSeverity, CheckStatus
    from .fixtures import make_problem_report
    crit = make_problem_check(
        check_id="P1.1", dimension_id=1, status=CheckStatus.FAIL,
        severity=CheckSeverity.CRITICAL,
    )
    pr = make_problem_report(checks=(crit,))
    assert _count_critical_checks(pr) == 1


def test_diff_critical_check_ids_finds_new_critical():
    from buildemup.components.c15.schema import CheckSeverity, CheckStatus
    from .fixtures import make_problem_report
    pre = make_problem_report(
        checks=(make_problem_check(check_id="P1.1", dimension_id=1,
                                    status=CheckStatus.FAIL,
                                    severity=CheckSeverity.CRITICAL),),
    )
    post = make_problem_report(
        checks=(
            make_problem_check(check_id="P1.1", dimension_id=1,
                              status=CheckStatus.FAIL,
                              severity=CheckSeverity.CRITICAL),
            make_problem_check(check_id="P2.1", dimension_id=2,
                              status=CheckStatus.FAIL,
                              severity=CheckSeverity.CRITICAL),
        ),
    )
    newly_critical = _diff_critical_check_ids(pre, post)
    assert "P2.1" in newly_critical


def test_complete_subset_rerun_no_regression():
    """When post PR has same critical count, no regression flag."""
    cfg = C3bRuntimeConfig()
    sess, bundle = _build_ready_session(cfg)
    target = next(
        t for opt_set in sess.tweak_option_sets for t in opt_set.tweaks
        if t.severity_tier == "medium"
    )
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=target.tweak_id)
    sess = apply_user_action(sess, req, cfg)
    pre_pr = bundle.problem_reports[0]
    new_sess = complete_subset_rerun(sess, target.tweak_id, pre_pr, pre_pr, cfg)
    assert new_sess.session_history[-1].apply_outcome.regression_detected is False
    assert new_sess.current_status == "open_for_user_input"


def test_complete_subset_rerun_regression_fires_advisory():
    """When post PR has MORE critical checks, regression flag fires."""
    from buildemup.components.c15.schema import CheckSeverity, CheckStatus
    from .fixtures import make_problem_report
    cfg = C3bRuntimeConfig()
    sess, bundle = _build_ready_session(cfg)
    target = next(
        t for opt_set in sess.tweak_option_sets for t in opt_set.tweaks
        if t.severity_tier == "medium"
    )
    req = UserActionRequest(user_action="accepted_tweak", chosen_tweak_id=target.tweak_id)
    sess = apply_user_action(sess, req, cfg)

    pre_pr = bundle.problem_reports[0]
    post_pr = make_problem_report(
        checks=(
            make_problem_check(check_id="P3.1", dimension_id=3,
                              status=CheckStatus.FAIL,
                              severity=CheckSeverity.CRITICAL,
                              affected_room_ids=("master_001",)),
            make_problem_check(check_id="P3.2", dimension_id=3,
                              status=CheckStatus.FAIL,
                              severity=CheckSeverity.CRITICAL,
                              affected_room_ids=("master_001",)),
        ),
        upstream_cache_key="post_rerun",
    )
    new_sess = complete_subset_rerun(sess, target.tweak_id, pre_pr, post_pr, cfg)
    assert new_sess.session_history[-1].apply_outcome.regression_detected is True
    regression_flags = [
        f for f in new_sess.advisory_flags
        if f.kind == "regression_after_apply"
    ]
    assert len(regression_flags) >= 1


# ============================================================
# R15 compatibility check
# ============================================================

def test_compatibility_against_empty_history_returns_empty():
    from .fixtures import make_tweak_option_light
    t = make_tweak_option_light()
    assert check_compatibility_against_history(t, ()) == ()


def test_compatibility_against_prior_emits_one_assertion_per_prior():
    from .fixtures import make_tweak_option_light
    t = make_tweak_option_light()
    assertions = check_compatibility_against_history(t, ("prior_1", "prior_2"))
    assert len(assertions) == 2
    assert all(a.result == "compatible" for a in assertions)
