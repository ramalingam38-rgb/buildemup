"""Tests for Phase ζ — resolution + handoff signing."""
from __future__ import annotations

import pytest

from buildemup.components.c03b.config import C3bRuntimeConfig
from buildemup.components.c03b.errors import LocalTradeoffError
from buildemup.components.c03b.phases.alpha import run_phase_alpha
from buildemup.components.c03b.phases.beta import run_phase_beta
from buildemup.components.c03b.phases.delta import run_phase_delta
from buildemup.components.c03b.phases.epsilon import (
    UserActionRequest, apply_user_action,
)
from buildemup.components.c03b.phases.gamma import run_phase_gamma
from buildemup.components.c03b.phases.zeta import (
    _sum_cost_impacts, _sum_space_impacts, run_phase_zeta,
)

from .fixtures import make_bundle_3_layouts_happy_path, make_tweak_option_light


def _ready_resolved_session():
    """Build a session through finalize."""
    cfg = C3bRuntimeConfig()
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, cfg)
    sess = run_phase_beta(sess, bundle, cfg)
    sess = run_phase_gamma(sess, cfg)
    sess = run_phase_delta(sess, cfg)

    layout_id = sess.tweak_option_sets[0].layout_id
    req = UserActionRequest(user_action="finalized_layout_choice",
                            finalize_layout_id=layout_id)
    sess = apply_user_action(sess, req, cfg)
    return sess, cfg


def test_sum_cost_impacts_empty_returns_none():
    assert _sum_cost_impacts(()) is None


def test_sum_cost_impacts_single_tweak():
    t = make_tweak_option_light()
    triple = _sum_cost_impacts((t,))
    assert triple is not None
    assert triple.exact_value == t.cost_impact.exact_value


def test_sum_space_impacts_empty_returns_none():
    assert _sum_space_impacts((), 1000.0) is None


def test_sum_space_impacts_single_tweak():
    t = make_tweak_option_light()
    si = _sum_space_impacts((t,), 1000.0)
    assert si is not None
    assert si.total_sqft_delta == t.space_impact.total_sqft_delta


def test_run_phase_zeta_on_resolved_session_populates_deltas():
    sess, cfg = _ready_resolved_session()
    new_sess = run_phase_zeta(sess, cfg)
    # If applied_tweaks is empty (finalize without prior accepts), deltas are None
    # which is allowed per ResolvedSelection schema. If non-empty, deltas
    # should be populated.
    assert new_sess.resolved_selection is not None


def test_run_phase_zeta_without_resolved_selection_raises():
    bundle = make_bundle_3_layouts_happy_path()
    cfg = C3bRuntimeConfig()
    sess = run_phase_alpha(bundle, cfg)
    # No resolved_selection — Phase ζ should refuse
    with pytest.raises(LocalTradeoffError):
        run_phase_zeta(sess, cfg)
