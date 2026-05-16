"""Tests for Phase γ — impact verification."""
from __future__ import annotations

import dataclasses

import pytest

from buildemup.components.c03b.config import C3bRuntimeConfig
from buildemup.components.c03b.errors import ImpactComputationError
from buildemup.components.c03b.phases.alpha import run_phase_alpha
from buildemup.components.c03b.phases.beta import run_phase_beta
from buildemup.components.c03b.phases.gamma import (
    run_phase_gamma,
    verify_tweak_impacts,
)

from .fixtures import (
    make_bundle_3_layouts_happy_path,
    make_tweak_option_light,
)


def test_verify_well_formed_tweak_returns_none():
    tweak = make_tweak_option_light()
    assert verify_tweak_impacts(tweak) is None


def test_verify_phase_beta_output_all_pass():
    """Every tweak from Phase β should pass impact verification."""
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    sess = run_phase_beta(sess, bundle, C3bRuntimeConfig())
    for opt_set in sess.tweak_option_sets:
        for t in opt_set.tweaks:
            assert verify_tweak_impacts(t) is None


def test_run_phase_gamma_passes_through_clean_session():
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    sess = run_phase_beta(sess, bundle, C3bRuntimeConfig())
    sess_after = run_phase_gamma(sess, C3bRuntimeConfig())
    # Tweak counts unchanged
    for before, after in zip(sess.tweak_option_sets, sess_after.tweak_option_sets):
        assert len(before.tweaks) == len(after.tweaks)


def test_run_phase_gamma_is_idempotent():
    bundle = make_bundle_3_layouts_happy_path()
    cfg = C3bRuntimeConfig()
    sess = run_phase_alpha(bundle, cfg)
    sess = run_phase_beta(sess, bundle, cfg)
    sess1 = run_phase_gamma(sess, cfg)
    sess2 = run_phase_gamma(sess1, cfg)
    assert sess1.canonical_replay_signature == sess2.canonical_replay_signature
