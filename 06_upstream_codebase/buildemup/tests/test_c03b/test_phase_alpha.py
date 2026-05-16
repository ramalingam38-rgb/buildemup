"""Tests for Phase α — canonicalization + applicability."""
from __future__ import annotations

import pytest

from buildemup.components.c03b.config import C3bRuntimeConfig
from buildemup.components.c03b.errors import (
    C3bConfigurationError,
    UpstreamSchemaDriftError,
)
from buildemup.components.c03b.phases.alpha import (
    archetype_for_rank,
    check_configuration,
    check_high_ambiguity,
    check_pareto_diversity,
    check_preview_mode,
    check_upstream_versions,
    run_phase_alpha,
)

from .fixtures import (
    make_bundle_3_layouts_happy_path,
    make_bundle_high_ambiguity,
    make_bundle_pareto_collapse,
    make_bundle_preview_mode,
    make_resolved_brief,
)


# ============================================================
# archetype_for_rank
# ============================================================

def test_archetype_for_rank_1_is_cost_efficient():
    assert archetype_for_rank(1) == "cost_efficient"


def test_archetype_for_rank_2_is_everyday_living():
    assert archetype_for_rank(2) == "everyday_living"


def test_archetype_for_rank_3_is_premium_design():
    assert archetype_for_rank(3) == "premium_design"


def test_archetype_for_rank_0_raises():
    with pytest.raises(C3bConfigurationError):
        archetype_for_rank(0)


def test_archetype_for_rank_4_raises():
    with pytest.raises(C3bConfigurationError):
        archetype_for_rank(4)


# ============================================================
# Preview Mode applicability
# ============================================================

def test_preview_mode_check_returns_none_for_normal_brief():
    bundle = make_bundle_3_layouts_happy_path()
    assert check_preview_mode(bundle) is None


def test_preview_mode_check_returns_advisory_for_preview_status():
    bundle = make_bundle_preview_mode()
    msg = check_preview_mode(bundle)
    assert msg is not None
    assert "Preview Mode" in msg or "preview" in msg.lower()


def test_preview_mode_terminates_session():
    sess = run_phase_alpha(make_bundle_preview_mode(), C3bRuntimeConfig())
    assert sess.current_status == "abandoned_no_tweaks"
    assert len(sess.advisory_flags) == 1


# ============================================================
# High-ambiguity (CoverageQuality.LOW) applicability
# ============================================================

def test_high_ambiguity_check_returns_none_for_high_coverage():
    bundle = make_bundle_3_layouts_happy_path()
    assert check_high_ambiguity(bundle) is None


def test_high_ambiguity_check_returns_advisory_for_low_coverage():
    bundle = make_bundle_high_ambiguity()
    msg = check_high_ambiguity(bundle)
    assert msg is not None
    assert "confidence" in msg.lower() or "low" in msg.lower() or "ambig" in msg.lower()


def test_high_ambiguity_terminates_session():
    sess = run_phase_alpha(make_bundle_high_ambiguity(), C3bRuntimeConfig())
    assert sess.current_status == "abandoned_no_tweaks"


# ============================================================
# Pareto collapse applicability
# ============================================================

def test_pareto_check_passes_with_diverse_layouts():
    bundle = make_bundle_3_layouts_happy_path()
    assert check_pareto_diversity(bundle) is None


def test_pareto_check_with_archetype_diverse_layouts_passes_in_v0_5():
    """v0.5 A9 — when C16 returns rank_position triple (1,2,3),
    archetype diversity is satisfied by construction. The pareto-
    collapse fixture from v0.4 (cost+sqft collapsed) is now
    EXPECTED to pass, because A9 catches the missing fourth floor.

    To genuinely trip the pareto floor under v0.5, all of:
      - cost spread < 15%, AND
      - sqft spread < 10%, AND
      - fewer than 2 distinct archetypes (requires degenerate C16)

    must hold. Degenerate C16 is currently impossible per its LOCKED
    invariants, so v0.5 EFFECTIVELY hardens pareto-collapse detection.
    """
    bundle = make_bundle_pareto_collapse()
    # Under v0.5 A9: archetype-diversity (1,2,3 from C16) is intact, so
    # pareto check returns None (no advisory).
    assert check_pareto_diversity(bundle) is None


def test_pareto_collapse_under_v0_5_does_not_terminate_session():
    """Companion to above — Phase α does not terminate when archetype
    diversity is intact, even if numeric floors collapse."""
    sess = run_phase_alpha(make_bundle_pareto_collapse(), C3bRuntimeConfig())
    assert sess.current_status == "open_for_user_input"


# ============================================================
# Configuration check
# ============================================================

def test_check_configuration_accepts_chennai():
    bundle = make_bundle_3_layouts_happy_path()
    check_configuration(bundle, C3bRuntimeConfig())  # no raise


def test_check_configuration_rejects_unknown_jurisdiction():
    import dataclasses
    bundle = make_bundle_3_layouts_happy_path()
    bad_brief = dataclasses.replace(
        bundle.resolved_brief, jurisdiction_profile_id="UNKNOWN_CITY",
    )
    bundle = dataclasses.replace(bundle, resolved_brief=bad_brief)
    with pytest.raises(C3bConfigurationError):
        check_configuration(bundle, C3bRuntimeConfig())


# ============================================================
# Upstream version check
# ============================================================

def test_upstream_versions_accepts_matching_c15():
    bundle = make_bundle_3_layouts_happy_path()
    check_upstream_versions(bundle)  # no raise


def test_upstream_versions_raises_on_c15_drift():
    import dataclasses
    bundle = make_bundle_3_layouts_happy_path()
    bad_pr0 = dataclasses.replace(
        bundle.problem_reports[0], c15_version="v0.0.WRONG",
    )
    new_prs = (bad_pr0,) + bundle.problem_reports[1:]
    bundle = dataclasses.replace(bundle, problem_reports=new_prs)
    with pytest.raises(UpstreamSchemaDriftError):
        check_upstream_versions(bundle)


# ============================================================
# Happy path
# ============================================================

def test_run_phase_alpha_happy_path_returns_skeleton():
    sess = run_phase_alpha(make_bundle_3_layouts_happy_path(), C3bRuntimeConfig())
    assert sess.current_status == "open_for_user_input"
    assert sess.tweak_option_sets == ()
    assert sess.iteration_count == 0
    assert sess.canonical_replay_signature != "0" * 64


def test_run_phase_alpha_sets_iteration_cap_from_config():
    cfg = C3bRuntimeConfig(iteration_cap=3)
    sess = run_phase_alpha(make_bundle_3_layouts_happy_path(), cfg)
    assert sess.iteration_cap == 3


def test_run_phase_alpha_session_id_is_unique():
    cfg = C3bRuntimeConfig()
    s1 = run_phase_alpha(make_bundle_3_layouts_happy_path(), cfg)
    s2 = run_phase_alpha(make_bundle_3_layouts_happy_path(), cfg)
    assert s1.session_id != s2.session_id


def test_run_phase_alpha_carries_brief_signature():
    bundle = make_bundle_3_layouts_happy_path()
    sess = run_phase_alpha(bundle, C3bRuntimeConfig())
    assert sess.source_brief_signature == bundle.resolved_brief.brief_signature
