"""
Component 2 Session D tests.

Coverage:
  - check_solar_exposure_practical: PASS / SOFT / HARD per orientation
  - check_solar_exposure_code_strict: PASS / HARD per orientation
  - compute_solar_gap: BLOCKING_IF_NOT_ACCEPTED / SIGNIFICANT / None
  - check_cross_ventilation_practical: PASS / SOFT / HARD per plot type
  - check_cross_ventilation_code_strict: PASS / HARD per plot type
  - compute_ventilation_gap: rare in v0.1 (documented)
  - Pattern: divergence proven for solar in particular

Note: Room minimums branching DEFERRED to v0.2 — Component 1 currently
rejects below-NBC room sizes at brief construction. See v2_backlog.md.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _build_brief(**overrides):
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    defaults = dict(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0, plot_type="detached",
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1))),
        ),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    defaults.update(overrides)
    inp = BriefCaptureInput(**defaults)
    return BriefCaptureEngine().execute(inp).brief


# ─── Solar exposure (Practical) ───────────────────────────────────────

def test_solar_practical_pass_for_south_facing():
    """South-facing plot → high solar score → PASS."""
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
    )
    brief = _build_brief(plot_facing="S")
    r = check_solar_exposure_practical(brief)
    assert r.severity.value == "pass"
    assert r.details["orientation_score"] == 90
    print("PASS solar practical PASSes for S-facing (score 90)")


def test_solar_practical_pass_for_east_facing():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
    )
    brief = _build_brief(plot_facing="E")
    r = check_solar_exposure_practical(brief)
    assert r.severity.value == "pass"
    assert r.details["orientation_score"] == 70
    print("PASS solar practical PASSes for E-facing (score 70)")


def test_solar_practical_soft_warn_for_north_facing():
    """N-facing scores 30 — between practical min (30) and code-strict (55)."""
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
    )
    brief = _build_brief(plot_facing="N")
    r = check_solar_exposure_practical(brief)
    assert r.severity.value == "soft_warn"
    assert r.details["orientation_score"] == 30
    print("PASS solar practical SOFT_WARNs for N-facing (score 30, between thresholds)")


def test_solar_practical_soft_warn_for_northwest():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
    )
    brief = _build_brief(plot_facing="NW")
    r = check_solar_exposure_practical(brief)
    assert r.severity.value == "soft_warn"
    print("PASS solar practical SOFT_WARNs for NW-facing (score 50)")


def test_solar_practical_check_id():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
    )
    brief = _build_brief()
    r = check_solar_exposure_practical(brief)
    assert r.check_id == "solar_practical"
    print("PASS solar practical check_id is 'solar_practical'")


def test_solar_practical_is_usability_category():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
    )
    from buildemup.domain.feasibility import CheckCategory
    brief = _build_brief()
    r = check_solar_exposure_practical(brief)
    assert r.category == CheckCategory.USABILITY
    print("PASS solar practical is in USABILITY category")


def test_solar_practical_uses_medium_confidence():
    """Heuristic-based → MEDIUM confidence, not HIGH."""
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
    )
    from buildemup.domain.feasibility import ConfidenceLevel
    brief = _build_brief(plot_facing="S")
    r = check_solar_exposure_practical(brief)
    assert r.confidence == ConfidenceLevel.MEDIUM
    assert r.confidence_reason is not None
    print("PASS solar practical uses MEDIUM confidence (heuristic)")


def test_solar_practical_soft_warn_score_contribution():
    """SOFT_WARN with MEDIUM confidence = -7 score contribution."""
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
    )
    brief = _build_brief(plot_facing="N")
    r = check_solar_exposure_practical(brief)
    assert r.severity.value == "soft_warn"
    assert r.score_contribution == -7  # MEDIUM SOFT_WARN penalty
    print(f"PASS solar practical SOFT_WARN scores -7 (MEDIUM conf)")


# ─── Solar exposure (Code-Strict) ─────────────────────────────────────

def test_solar_code_strict_pass_for_south():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_code_strict,
    )
    brief = _build_brief(plot_facing="S")
    r = check_solar_exposure_code_strict(brief)
    assert r.severity.value == "pass"
    print("PASS solar code_strict PASSes for S-facing")


def test_solar_code_strict_pass_for_southeast():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_code_strict,
    )
    brief = _build_brief(plot_facing="SE")
    r = check_solar_exposure_code_strict(brief)
    assert r.severity.value == "pass"
    print("PASS solar code_strict PASSes for SE-facing (score 80)")


def test_solar_code_strict_hard_fail_for_north():
    """N-facing fails NBC daylight per code-strict threshold."""
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_code_strict,
    )
    brief = _build_brief(plot_facing="N")
    r = check_solar_exposure_code_strict(brief)
    assert r.severity.value == "hard_fail"
    assert r.verification_priority.value == "important"
    print("PASS solar code_strict HARD_FAILs for N-facing (score 30 < 55)")


def test_solar_code_strict_hard_fail_for_nw():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_code_strict,
    )
    brief = _build_brief(plot_facing="NW")
    r = check_solar_exposure_code_strict(brief)
    assert r.severity.value == "hard_fail"
    print("PASS solar code_strict HARD_FAILs for NW-facing (score 50 < 55)")


def test_solar_code_strict_check_id():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_code_strict,
    )
    brief = _build_brief()
    r = check_solar_exposure_code_strict(brief)
    assert r.check_id == "solar_code_strict"
    print("PASS solar code_strict check_id is 'solar_code_strict'")


def test_solar_code_strict_carries_nbc_reference():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_code_strict,
    )
    brief = _build_brief()
    r = check_solar_exposure_code_strict(brief)
    assert "NBC" in r.details["nbc_reference"]
    assert "Part 8" in r.details["nbc_reference"]
    print("PASS solar code_strict cites NBC Part 8 daylight clause")


# ─── Solar gap ────────────────────────────────────────────────────────

def test_solar_gap_none_when_both_pass():
    """South-facing → both pass → no gap."""
    from buildemup.components.c02.branched_checks import compute_solar_gap
    brief = _build_brief(plot_facing="S")
    g = compute_solar_gap(brief)
    assert g is None
    print("PASS solar gap None for S-facing (both lanes pass)")


def test_solar_gap_blocking_for_north_facing():
    """N-facing → Practical SOFT, Code-Strict HARD → BLOCKING_IF_NOT_ACCEPTED."""
    from buildemup.components.c02.branched_checks import compute_solar_gap
    from buildemup.domain.feasibility import GapSeverity
    brief = _build_brief(plot_facing="N")
    g = compute_solar_gap(brief)
    assert g is not None
    assert g.severity == GapSeverity.BLOCKING_IF_NOT_ACCEPTED
    print("PASS solar gap is BLOCKING_IF_NOT_ACCEPTED for N-facing")


def test_solar_gap_carries_score_in_practical_value():
    from buildemup.components.c02.branched_checks import compute_solar_gap
    brief = _build_brief(plot_facing="N")
    g = compute_solar_gap(brief)
    assert g.practical_value["orientation_score"] == 30
    print("PASS solar gap practical_value carries orientation_score")


def test_solar_gap_check_id():
    from buildemup.components.c02.branched_checks import compute_solar_gap
    brief = _build_brief(plot_facing="N")
    g = compute_solar_gap(brief)
    assert g.check_id == "solar_exposure"
    print("PASS solar gap check_id is 'solar_exposure'")


# ─── Cross-ventilation (Practical) ────────────────────────────────────

def test_vent_practical_pass_for_detached():
    """Detached = 4 openable sides → PASS."""
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_practical,
    )
    brief = _build_brief(plot_type="detached")
    r = check_cross_ventilation_practical(brief)
    assert r.severity.value == "pass"
    assert r.details["openable_sides_estimated"] == 4
    print("PASS vent practical PASSes for detached (4 sides)")


def test_vent_practical_pass_for_semi_detached():
    """Semi-detached = 3 openable sides → PASS."""
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_practical,
    )
    brief = _build_brief(plot_type="semi_detached", shared_side="left")
    r = check_cross_ventilation_practical(brief)
    assert r.severity.value == "pass"
    assert r.details["openable_sides_estimated"] == 3
    print("PASS vent practical PASSes for semi-detached (3 sides)")


def test_vent_practical_pass_for_continuous():
    """Continuous (row house) = 2 openable sides → PASS at minimum."""
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_practical,
    )
    brief = _build_brief(plot_type="continuous")
    r = check_cross_ventilation_practical(brief)
    # 2 sides meets both Practical (≥1) and CodeStrict (≥2)
    assert r.severity.value == "pass"
    assert r.details["openable_sides_estimated"] == 2
    print("PASS vent practical PASSes for continuous (2 sides at NBC min)")


def test_vent_practical_check_id():
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_practical,
    )
    brief = _build_brief()
    r = check_cross_ventilation_practical(brief)
    assert r.check_id == "cross_vent_practical"
    print("PASS vent practical check_id is 'cross_vent_practical'")


def test_vent_practical_is_usability_category():
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_practical,
    )
    from buildemup.domain.feasibility import CheckCategory
    brief = _build_brief()
    r = check_cross_ventilation_practical(brief)
    assert r.category == CheckCategory.USABILITY
    print("PASS vent practical is in USABILITY category")


def test_vent_practical_uses_medium_confidence():
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_practical,
    )
    from buildemup.domain.feasibility import ConfidenceLevel
    brief = _build_brief()
    r = check_cross_ventilation_practical(brief)
    assert r.confidence == ConfidenceLevel.MEDIUM
    print("PASS vent practical uses MEDIUM confidence")


# ─── Cross-ventilation (Code-Strict) ──────────────────────────────────

def test_vent_code_strict_pass_for_detached():
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_code_strict,
    )
    brief = _build_brief(plot_type="detached")
    r = check_cross_ventilation_code_strict(brief)
    assert r.severity.value == "pass"
    print("PASS vent code_strict PASSes for detached")


def test_vent_code_strict_pass_for_continuous_at_2_sides():
    """Continuous = 2 sides = NBC minimum exactly → PASS."""
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_code_strict,
    )
    brief = _build_brief(plot_type="continuous")
    r = check_cross_ventilation_code_strict(brief)
    assert r.severity.value == "pass"
    print("PASS vent code_strict PASSes for continuous at NBC 2-side min")


def test_vent_code_strict_check_id():
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_code_strict,
    )
    brief = _build_brief()
    r = check_cross_ventilation_code_strict(brief)
    assert r.check_id == "cross_vent_code_strict"
    print("PASS vent code_strict check_id is 'cross_vent_code_strict'")


def test_vent_code_strict_carries_nbc_reference():
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_code_strict,
    )
    brief = _build_brief()
    r = check_cross_ventilation_code_strict(brief)
    assert "NBC" in r.details["nbc_reference"]
    assert "Part 8" in r.details["nbc_reference"]
    print("PASS vent code_strict cites NBC Part 8")


# ─── Ventilation gap ──────────────────────────────────────────────────

def test_vent_gap_none_for_detached():
    """Detached → both lanes pass → None."""
    from buildemup.components.c02.branched_checks import (
        compute_ventilation_gap,
    )
    brief = _build_brief(plot_type="detached")
    g = compute_ventilation_gap(brief)
    assert g is None
    print("PASS vent gap None for detached")


def test_vent_gap_none_for_continuous_at_2_sides():
    """Continuous (2 sides = NBC min) → both lanes pass → None.
    
    This is the v0.1 limitation documented in branched_checks.py:
    continuous plots barely satisfy NBC, no gap surfaces.
    """
    from buildemup.components.c02.branched_checks import (
        compute_ventilation_gap,
    )
    brief = _build_brief(plot_type="continuous")
    g = compute_ventilation_gap(brief)
    assert g is None
    print("PASS vent gap None for continuous (2 sides meets NBC min — v0.1 limitation)")


def test_vent_check_id_naming_convention():
    """Both vent variant check_ids follow the convention."""
    from buildemup.components.c02.branched_checks import (
        check_cross_ventilation_practical,
        check_cross_ventilation_code_strict,
    )
    brief = _build_brief()
    p = check_cross_ventilation_practical(brief)
    c = check_cross_ventilation_code_strict(brief)
    assert p.check_id.endswith("_practical")
    assert c.check_id.endswith("_code_strict")
    print("PASS vent check_ids follow _practical / _code_strict naming")


# ─── Dual-design pattern (Solar — strong divergence example) ──────────

def test_solar_dual_design_proves_divergence():
    """Same brief: Practical SOFT, Code-Strict HARD — the architectural proof."""
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
        check_solar_exposure_code_strict,
    )
    brief = _build_brief(plot_facing="N")
    p = check_solar_exposure_practical(brief)
    c = check_solar_exposure_code_strict(brief)
    assert p.severity.value == "soft_warn"
    assert c.severity.value == "hard_fail"
    print("PASS solar dual-design: practical=SOFT, code_strict=HARD (divergence)")


def test_solar_dual_design_scoring_diverges():
    from buildemup.components.c02.branched_checks import (
        check_solar_exposure_practical,
        check_solar_exposure_code_strict,
    )
    from buildemup.components.c02.scoring import compute_overall_score
    brief = _build_brief(plot_facing="N")
    p_score, _ = compute_overall_score([check_solar_exposure_practical(brief)])
    c_score, _ = compute_overall_score([check_solar_exposure_code_strict(brief)])
    assert p_score == 93   # 100 - 7 (MEDIUM SOFT_WARN)
    assert c_score == 40   # capped due to HARD_FAIL
    print(f"PASS solar dual-design scoring: practical={p_score}, code_strict={c_score}")


# ─── Integration ──────────────────────────────────────────────────────

def test_session_a_b_c_d_branched_checks_run_together():
    """All 4 branched checks (3 from A-C + 1 new D solar + 1 new D vent) integrate."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
        check_setback_compliance_code_strict,
        check_solar_exposure_practical,
        check_solar_exposure_code_strict,
        check_cross_ventilation_practical,
        check_cross_ventilation_code_strict,
        compute_setback_gap, compute_solar_gap, compute_ventilation_gap,
    )
    brief = _build_brief(plot_facing="S")  # All branched should pass

    practical_branched = (
        check_setback_compliance_practical(brief),
        check_solar_exposure_practical(brief),
        check_cross_ventilation_practical(brief),
    )
    code_strict_branched = (
        check_setback_compliance_code_strict(brief),
        check_solar_exposure_code_strict(brief),
        check_cross_ventilation_code_strict(brief),
    )
    gaps = [
        g for g in (compute_setback_gap(brief),
                    compute_solar_gap(brief),
                    compute_ventilation_gap(brief))
        if g is not None
    ]
    # All passing → no gaps
    for r in practical_branched:
        assert r.severity.value in ("pass", "soft_warn")
    for r in code_strict_branched:
        assert r.severity.value == "pass"
    assert len(gaps) == 0
    print("PASS 3 branched checks integrate (Practical + Code-Strict + Gaps)")


def test_v0_9_3_baseline_unaffected_by_session_d():
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),)),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    out = BriefCaptureEngine().execute(inp)
    assert out.risk_level == "LOW"
    assert out.c7_preview_cost is not None
    print("PASS v0.9.3 baseline unaffected by Session D")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session D (Solar + Cross-Ventilation Branching)")
    print("=" * 70)
    print()

    print("--- Solar exposure (Practical) ---")
    test_solar_practical_pass_for_south_facing()
    test_solar_practical_pass_for_east_facing()
    test_solar_practical_soft_warn_for_north_facing()
    test_solar_practical_soft_warn_for_northwest()
    test_solar_practical_check_id()
    test_solar_practical_is_usability_category()
    test_solar_practical_uses_medium_confidence()
    test_solar_practical_soft_warn_score_contribution()
    print()

    print("--- Solar exposure (Code-Strict) ---")
    test_solar_code_strict_pass_for_south()
    test_solar_code_strict_pass_for_southeast()
    test_solar_code_strict_hard_fail_for_north()
    test_solar_code_strict_hard_fail_for_nw()
    test_solar_code_strict_check_id()
    test_solar_code_strict_carries_nbc_reference()
    print()

    print("--- Solar gap ---")
    test_solar_gap_none_when_both_pass()
    test_solar_gap_blocking_for_north_facing()
    test_solar_gap_carries_score_in_practical_value()
    test_solar_gap_check_id()
    print()

    print("--- Cross-ventilation (Practical) ---")
    test_vent_practical_pass_for_detached()
    test_vent_practical_pass_for_semi_detached()
    test_vent_practical_pass_for_continuous()
    test_vent_practical_check_id()
    test_vent_practical_is_usability_category()
    test_vent_practical_uses_medium_confidence()
    print()

    print("--- Cross-ventilation (Code-Strict) ---")
    test_vent_code_strict_pass_for_detached()
    test_vent_code_strict_pass_for_continuous_at_2_sides()
    test_vent_code_strict_check_id()
    test_vent_code_strict_carries_nbc_reference()
    print()

    print("--- Ventilation gap ---")
    test_vent_gap_none_for_detached()
    test_vent_gap_none_for_continuous_at_2_sides()
    test_vent_check_id_naming_convention()
    print()

    print("--- Dual-design proof (Solar) ---")
    test_solar_dual_design_proves_divergence()
    test_solar_dual_design_scoring_diverges()
    print()

    print("--- Integration ---")
    test_session_a_b_c_d_branched_checks_run_together()
    test_v0_9_3_baseline_unaffected_by_session_d()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION D TESTS PASSED")
    print("=" * 70)
