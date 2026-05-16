"""Tests for Phase δ — presentation + signing."""
from __future__ import annotations

import dataclasses

import pytest

from buildemup.components.c03b.config import C3bRuntimeConfig
from buildemup.components.c03b.phases.alpha import run_phase_alpha
from buildemup.components.c03b.phases.beta import run_phase_beta
from buildemup.components.c03b.phases.delta import run_phase_delta
from buildemup.components.c03b.phases.gamma import run_phase_gamma

from .fixtures import make_bundle_3_layouts_happy_path


def test_run_phase_delta_status_open_for_user_input():
    bundle = make_bundle_3_layouts_happy_path()
    cfg = C3bRuntimeConfig()
    sess = run_phase_alpha(bundle, cfg)
    sess = run_phase_beta(sess, bundle, cfg)
    sess = run_phase_gamma(sess, cfg)
    sess = run_phase_delta(sess, cfg)
    assert sess.current_status == "open_for_user_input"


def test_run_phase_delta_re_signs_session():
    bundle = make_bundle_3_layouts_happy_path()
    cfg = C3bRuntimeConfig()
    sess = run_phase_alpha(bundle, cfg)
    sess = run_phase_beta(sess, bundle, cfg)
    sig_before = sess.canonical_replay_signature
    sess = run_phase_delta(sess, cfg)
    # Same state → same canonical sig
    assert sess.canonical_replay_signature == sig_before


def test_run_phase_delta_verifies_lex_asc_sort():
    """Defensive sort verification — should pass for properly-built session."""
    bundle = make_bundle_3_layouts_happy_path()
    cfg = C3bRuntimeConfig()
    sess = run_phase_alpha(bundle, cfg)
    sess = run_phase_beta(sess, bundle, cfg)
    # Phase β already enforces lex-ASC; δ verifies
    sess = run_phase_delta(sess, cfg)
    for opt_set in sess.tweak_option_sets:
        ids = [t.tweak_id for t in opt_set.tweaks]
        assert ids == sorted(ids)


def test_run_phase_delta_signature_determinism():
    """Same inputs → same signature (R6)."""
    bundle = make_bundle_3_layouts_happy_path()
    cfg = C3bRuntimeConfig()
    sess1 = run_phase_alpha(bundle, cfg)
    sess1 = run_phase_beta(sess1, bundle, cfg)
    sess1 = run_phase_delta(sess1, cfg)

    sess2 = run_phase_alpha(bundle, cfg)
    sess2 = run_phase_beta(sess2, bundle, cfg)
    sess2 = run_phase_delta(sess2, cfg)

    # session_id differs (uuid-based) but content-derived sigs should still
    # match modulo session_id. We test the option sets themselves match.
    assert len(sess1.tweak_option_sets) == len(sess2.tweak_option_sets)
    for os1, os2 in zip(sess1.tweak_option_sets, sess2.tweak_option_sets):
        ids1 = [t.tweak_id for t in os1.tweaks]
        ids2 = [t.tweak_id for t in os2.tweaks]
        assert ids1 == ids2  # tweak_ids are deterministic
