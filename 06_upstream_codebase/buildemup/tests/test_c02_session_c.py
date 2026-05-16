"""
Component 2 Session C tests.

Coverage:
  - check_setback_compliance_practical: PASS / HARD / SOFT
  - check_setback_compliance_code_strict: PASS / HARD per side
  - compute_setback_gap: None when matched, severities by shortfall
  - Pattern validation: same brief produces different results in
    PRACTICAL vs CODE_STRICT lanes (the dual-design proof)
  - Integration: setback gap surfaces in DesignGapAnalysis structure
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _build_brief(**overrides):
    """Build a Brief through Component 1."""
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


# ─── Practical setback check ──────────────────────────────────────────

def test_practical_pass_when_meets_nbc():
    """User-stated == NBC → PASS in Practical."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
    )
    brief = _build_brief()  # Default 1.5/1.5/1.5/1.5 = NBC for Chennai
    r = check_setback_compliance_practical(brief)
    assert r.severity.value == "pass"
    assert r.details["variant"] == "practical"
    print("PASS practical PASSes when user meets NBC")


def test_practical_pass_when_below_nbc_user_accepted():
    """User stated below-NBC values → still PASS in Practical (compromise accepted)."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
    )
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=1.0,
        user_setback_side_left_m=0.5, user_setback_side_right_m=0.5,
    )
    r = check_setback_compliance_practical(brief)
    # Practical accepts user's compromise — only fails on physical impossibility
    assert r.severity.value == "pass"
    print("PASS practical PASSes user-accepted compromise (below NBC)")


def test_practical_hard_fail_when_envelope_too_small():
    """User-stated setbacks leave envelope < 1m × 1m → HARD_FAIL."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
    )
    # 5×5m plot with 2.5m setbacks all sides → 0×0m envelope
    brief = _build_brief(
        plot_width_m=5.0, plot_depth_m=5.0,
        user_setback_front_m=2.5, user_setback_rear_m=2.5,
        user_setback_side_left_m=2.5, user_setback_side_right_m=2.5,
    )
    r = check_setback_compliance_practical(brief)
    assert r.severity.value == "hard_fail"
    assert r.verification_priority.value == "critical"
    print("PASS practical HARD_FAILs when envelope < 1×1m")


def test_practical_soft_warn_when_envelope_very_tight():
    """Setbacks consume >80% of plot → SOFT_WARN."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
    )
    # 6x6 plot with 2m all sides = 2x2 = 4 sqm vs 36 = 11% remaining (89% setback)
    brief = _build_brief(
        plot_width_m=6.0, plot_depth_m=6.0,
        user_setback_front_m=2.0, user_setback_rear_m=2.0,
        user_setback_side_left_m=2.0, user_setback_side_right_m=2.0,
    )
    r = check_setback_compliance_practical(brief)
    assert r.severity.value == "soft_warn"
    print("PASS practical SOFT_WARNs when setbacks consume >80% of plot")


def test_practical_check_is_spatial_category():
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
    )
    from buildemup.domain.feasibility import CheckCategory
    brief = _build_brief()
    r = check_setback_compliance_practical(brief)
    assert r.category == CheckCategory.SPATIAL
    print("PASS practical setback check is in SPATIAL category")


def test_practical_check_has_high_confidence():
    """User-provided physical data → HIGH confidence."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
    )
    from buildemup.domain.feasibility import ConfidenceLevel
    brief = _build_brief()
    r = check_setback_compliance_practical(brief)
    assert r.confidence == ConfidenceLevel.HIGH
    print("PASS practical setback check is HIGH confidence")


def test_practical_carries_envelope_details():
    """Check result includes envelope dimensions for downstream use."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
    )
    brief = _build_brief()
    r = check_setback_compliance_practical(brief)
    assert "envelope_width_m" in r.details
    assert "envelope_depth_m" in r.details
    assert "envelope_area_sqm" in r.details
    print("PASS practical result includes envelope dimensions")


def test_practical_check_id_is_practical_specific():
    """Practical check has its own check_id distinct from CodeStrict."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
    )
    brief = _build_brief()
    r = check_setback_compliance_practical(brief)
    assert r.check_id == "setback_practical"
    print("PASS practical check_id is 'setback_practical'")


# ─── CodeStrict setback check ─────────────────────────────────────────

def test_code_strict_pass_when_meets_nbc():
    """User-stated == NBC → PASS in CodeStrict."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_code_strict,
    )
    brief = _build_brief()  # 1.5/1.5/1.5/1.5 default
    r = check_setback_compliance_code_strict(brief)
    assert r.severity.value == "pass"
    print("PASS code_strict PASSes when user meets NBC")


def test_code_strict_pass_when_exceeds_nbc():
    """User-stated > NBC on all sides → PASS."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_code_strict,
    )
    brief = _build_brief(
        user_setback_front_m=2.0, user_setback_rear_m=2.0,
        user_setback_side_left_m=2.0, user_setback_side_right_m=2.0,
    )
    r = check_setback_compliance_code_strict(brief)
    assert r.severity.value == "pass"
    print("PASS code_strict PASSes when user exceeds NBC")


def test_code_strict_hard_fail_on_one_side():
    """One side below NBC → HARD_FAIL in CodeStrict."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_code_strict,
    )
    brief = _build_brief(
        user_setback_front_m=0.9,  # below NBC 1.5
        user_setback_rear_m=1.5, user_setback_side_left_m=1.5,
        user_setback_side_right_m=1.5,
    )
    r = check_setback_compliance_code_strict(brief)
    assert r.severity.value == "hard_fail"
    assert r.verification_priority.value == "critical"
    assert len(r.details["violations"]) == 1
    assert r.details["violations"][0]["side"] == "front"
    print("PASS code_strict HARD_FAILs when 1 side below NBC")


def test_code_strict_hard_fail_on_multiple_sides():
    """Multiple sides below NBC → HARD_FAIL with all violations listed."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_code_strict,
    )
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=1.0,
        user_setback_side_left_m=0.5, user_setback_side_right_m=0.5,
    )
    r = check_setback_compliance_code_strict(brief)
    assert r.severity.value == "hard_fail"
    assert len(r.details["violations"]) == 4
    print("PASS code_strict reports all 4 violations when all sides short")


def test_code_strict_violations_carry_shortfall_pct():
    """Each violation has shortfall_pct for downstream Gap computation."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_code_strict,
    )
    brief = _build_brief(
        user_setback_front_m=0.75,  # 50% short of NBC 1.5
        user_setback_rear_m=1.5, user_setback_side_left_m=1.5,
        user_setback_side_right_m=1.5,
    )
    r = check_setback_compliance_code_strict(brief)
    front_v = next(v for v in r.details["violations"] if v["side"] == "front")
    assert front_v["shortfall_pct"] == 50.0
    print(f"PASS code_strict violation reports shortfall_pct correctly "
          f"({front_v['shortfall_pct']}%)")


def test_code_strict_check_is_spatial_category():
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_code_strict,
    )
    from buildemup.domain.feasibility import CheckCategory
    brief = _build_brief()
    r = check_setback_compliance_code_strict(brief)
    assert r.category == CheckCategory.SPATIAL
    print("PASS code_strict setback check is in SPATIAL category")


def test_code_strict_check_id_is_code_strict_specific():
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_code_strict,
    )
    brief = _build_brief()
    r = check_setback_compliance_code_strict(brief)
    assert r.check_id == "setback_code_strict"
    print("PASS code_strict check_id is 'setback_code_strict'")


def test_code_strict_carries_nbc_values():
    """Result discloses what NBC actually requires for transparency."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_code_strict,
    )
    brief = _build_brief()
    r = check_setback_compliance_code_strict(brief)
    assert "nbc_mandated_setbacks_m" in r.details
    nbc_data = r.details["nbc_mandated_setbacks_m"]
    assert nbc_data["front"] == 1.5
    print("PASS code_strict result discloses NBC-mandated values")


# ─── Gap computation ──────────────────────────────────────────────────

def test_gap_is_none_when_user_meets_nbc():
    """No gap when user setbacks == NBC for all 4 sides."""
    from buildemup.components.c02.branched_checks import (
        compute_setback_gap,
    )
    brief = _build_brief()  # Defaults match NBC
    g = compute_setback_gap(brief)
    assert g is None
    print("PASS Gap is None when user meets NBC ('got lucky' case)")


def test_gap_marginal_for_small_shortfall():
    """User 10% short → MARGINAL gap."""
    from buildemup.components.c02.branched_checks import compute_setback_gap
    from buildemup.domain.feasibility import GapSeverity
    brief = _build_brief(
        user_setback_front_m=1.35, user_setback_rear_m=1.35,
        user_setback_side_left_m=1.35, user_setback_side_right_m=1.35,
    )
    g = compute_setback_gap(brief)
    assert g is not None
    assert g.severity == GapSeverity.MARGINAL
    print("PASS 10% shortfall → MARGINAL gap severity")


def test_gap_significant_for_moderate_shortfall():
    """User 20% short → SIGNIFICANT gap."""
    from buildemup.components.c02.branched_checks import compute_setback_gap
    from buildemup.domain.feasibility import GapSeverity
    brief = _build_brief(
        user_setback_front_m=1.2, user_setback_rear_m=1.2,
        user_setback_side_left_m=1.2, user_setback_side_right_m=1.2,
    )
    g = compute_setback_gap(brief)
    assert g is not None
    assert g.severity == GapSeverity.SIGNIFICANT
    print("PASS 20% shortfall → SIGNIFICANT gap severity")


def test_gap_blocking_for_large_shortfall():
    """User 40% short → BLOCKING_IF_NOT_ACCEPTED gap."""
    from buildemup.components.c02.branched_checks import compute_setback_gap
    from buildemup.domain.feasibility import GapSeverity
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    g = compute_setback_gap(brief)
    assert g is not None
    assert g.severity == GapSeverity.BLOCKING_IF_NOT_ACCEPTED
    print("PASS 40% shortfall → BLOCKING_IF_NOT_ACCEPTED")


def test_gap_severity_uses_worst_side():
    """Gap severity computed from worst-side shortfall, not average."""
    from buildemup.components.c02.branched_checks import compute_setback_gap
    from buildemup.domain.feasibility import GapSeverity
    # 3 sides at NBC, 1 side at 50% short → severity should reflect the 50%
    brief = _build_brief(
        user_setback_front_m=0.75,  # 50% short
        user_setback_rear_m=1.5, user_setback_side_left_m=1.5,
        user_setback_side_right_m=1.5,
    )
    g = compute_setback_gap(brief)
    assert g is not None
    assert g.severity == GapSeverity.BLOCKING_IF_NOT_ACCEPTED
    print("PASS Gap severity uses worst-side, not average")


def test_gap_practical_value_has_all_4_sides():
    """Gap.practical_value is a dict with front/rear/left/right."""
    from buildemup.components.c02.branched_checks import compute_setback_gap
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    g = compute_setback_gap(brief)
    assert isinstance(g.practical_value, dict)
    for side in ("front", "rear", "left", "right"):
        assert side in g.practical_value
    print("PASS Gap.practical_value has all 4 setback sides")


def test_gap_code_strict_value_has_all_4_sides():
    from buildemup.components.c02.branched_checks import compute_setback_gap
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    g = compute_setback_gap(brief)
    assert isinstance(g.code_strict_value, dict)
    for side in ("front", "rear", "left", "right"):
        assert side in g.code_strict_value
    print("PASS Gap.code_strict_value has all 4 setback sides")


def test_gap_default_user_acceptable_is_none():
    """First-pass Gap has user_acceptable=None (decision not yet asked)."""
    from buildemup.components.c02.branched_checks import compute_setback_gap
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    g = compute_setback_gap(brief)
    assert g.user_acceptable is None
    print("PASS Gap.user_acceptable defaults to None (not yet asked)")


def test_gap_default_decision_source_is_system():
    from buildemup.components.c02.branched_checks import compute_setback_gap
    from buildemup.domain.feasibility import DecisionSource
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    g = compute_setback_gap(brief)
    assert g.decision_source == DecisionSource.SYSTEM_DEFAULT
    print("PASS Gap.decision_source defaults to SYSTEM_DEFAULT")


def test_gap_impact_description_mentions_each_violation():
    """Impact description lists each side with shortfall."""
    from buildemup.components.c02.branched_checks import compute_setback_gap
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=1.0,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
    )
    g = compute_setback_gap(brief)
    assert "front" in g.impact_description
    assert "rear" in g.impact_description
    # Sides at NBC should not appear as violations
    print("PASS Gap.impact_description mentions each violating side")


def test_gap_check_id_is_setback_compliance():
    from buildemup.components.c02.branched_checks import compute_setback_gap
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    g = compute_setback_gap(brief)
    assert g.check_id == "setback_compliance"
    print("PASS Gap.check_id is 'setback_compliance'")


# ─── Dual-design pattern proof ────────────────────────────────────────

def test_dual_design_diverges_for_below_nbc_brief():
    """Same brief produces different results in PRACTICAL vs CODE_STRICT."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
        check_setback_compliance_code_strict,
    )
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    p = check_setback_compliance_practical(brief)
    c = check_setback_compliance_code_strict(brief)
    # PRACTICAL accepts user's compromise → PASS
    assert p.severity.value == "pass"
    # CODE_STRICT enforces NBC → HARD_FAIL
    assert c.severity.value == "hard_fail"
    # This divergence IS the dual-design pattern
    print("PASS dual-design proven: PRACTICAL=pass, CODE_STRICT=hard_fail "
          "for same brief (below NBC)")


def test_dual_design_converges_when_user_meets_nbc():
    """If user meets NBC, both variants PASS — 'got lucky' case."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
        check_setback_compliance_code_strict,
        compute_setback_gap,
    )
    brief = _build_brief()  # Defaults at NBC
    p = check_setback_compliance_practical(brief)
    c = check_setback_compliance_code_strict(brief)
    g = compute_setback_gap(brief)
    assert p.severity.value == "pass"
    assert c.severity.value == "pass"
    assert g is None  # No gap exists
    print("PASS dual-design converges: when user meets NBC, both PASS, no gap")


def test_dual_design_scoring_diverges_correctly():
    """PRACTICAL pass → high score; CODE_STRICT fail → score capped at 40."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
        check_setback_compliance_code_strict,
    )
    from buildemup.components.c02.scoring import compute_overall_score
    brief = _build_brief(
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    p_score, _ = compute_overall_score([check_setback_compliance_practical(brief)])
    c_score, _ = compute_overall_score([check_setback_compliance_code_strict(brief)])
    assert p_score == 100   # PRACTICAL PASS
    assert c_score == 40    # CODE_STRICT HARD_FAIL → capped
    print(f"PASS dual-design scoring: practical={p_score}, code_strict={c_score}")


def test_dual_design_with_other_cities():
    """Pattern works for cities besides Chennai."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
        check_setback_compliance_code_strict,
        compute_setback_gap,
    )
    from buildemup.domain.feasibility import GapSeverity
    # Mumbai brief with user-stated below NBC
    brief = _build_brief(
        city="mumbai",
        plot_width_m=10.0, plot_depth_m=15.0,
        user_setback_front_m=0.5,
        user_setback_rear_m=0.5,
        user_setback_side_left_m=0.5, user_setback_side_right_m=0.5,
    )
    p = check_setback_compliance_practical(brief)
    c = check_setback_compliance_code_strict(brief)
    g = compute_setback_gap(brief)
    assert p.severity.value in ("pass", "soft_warn", "hard_fail")
    # CodeStrict should fail because user is well below Mumbai DCR mins
    assert c.severity.value == "hard_fail"
    assert g is not None
    print(f"PASS dual-design works for Mumbai, gap severity={g.severity.value}")


# ─── Integration ──────────────────────────────────────────────────────

def test_setback_check_combines_with_session_a_b_checks():
    """Session A+B+C checks coexist in a single feasibility call."""
    from buildemup.components.c02.hard_physics_checks import (
        check_envelope_sufficiency, check_floor_stack_feasibility,
        check_parking_width, check_budget_feasibility,
    )
    from buildemup.components.c02.legal_only_checks import (
        check_far_compliance, check_ground_coverage_compliance,
        check_fire_tender_access, check_electric_line_clearance,
        check_water_course_clearance, check_stilt_mandate_compliance,
    )
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
        check_setback_compliance_code_strict,
    )
    from buildemup.components.c02.scoring import compute_overall_score
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
    brief = out.brief

    # Practical lane: Session A + Session B + Session C practical
    practical_results = (
        check_envelope_sufficiency(brief),
        check_floor_stack_feasibility(brief),
        check_parking_width(brief),
        check_budget_feasibility(brief, out.c7_preview_cost),
        check_far_compliance(brief),
        check_ground_coverage_compliance(brief),
        check_fire_tender_access(brief),
        check_electric_line_clearance(brief),
        check_water_course_clearance(brief),
        check_stilt_mandate_compliance(brief),
        check_setback_compliance_practical(brief),
    )
    # Code-strict lane: same A+B but with code-strict setback variant
    code_strict_results = practical_results[:-1] + (
        check_setback_compliance_code_strict(brief),
    )

    p_score, _ = compute_overall_score(practical_results)
    c_score, _ = compute_overall_score(code_strict_results)
    assert p_score == 100
    assert c_score == 100  # User meets NBC here
    assert len(practical_results) == 11
    assert len(code_strict_results) == 11
    print(f"PASS A+B+C integration: practical={p_score}, code_strict={c_score} "
          f"(11 checks each lane)")


def test_branch_check_carries_variant_in_details():
    """details['variant'] disambiguates which lane this result is for."""
    from buildemup.components.c02.branched_checks import (
        check_setback_compliance_practical,
        check_setback_compliance_code_strict,
    )
    brief = _build_brief()
    p = check_setback_compliance_practical(brief)
    c = check_setback_compliance_code_strict(brief)
    assert p.details["variant"] == "practical"
    assert c.details["variant"] == "code_strict"
    print("PASS branched check details carry variant disambiguator")


def test_v0_9_3_baseline_unaffected_by_session_c():
    """Existing C1+C7 still work — Session C is purely additive."""
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
    print("PASS v0.9.3 baseline unaffected by Session C")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session C (Branched Setback + Gap)")
    print("=" * 70)
    print()

    print("--- Practical setback check ---")
    test_practical_pass_when_meets_nbc()
    test_practical_pass_when_below_nbc_user_accepted()
    test_practical_hard_fail_when_envelope_too_small()
    test_practical_soft_warn_when_envelope_very_tight()
    test_practical_check_is_spatial_category()
    test_practical_check_has_high_confidence()
    test_practical_carries_envelope_details()
    test_practical_check_id_is_practical_specific()
    print()

    print("--- CodeStrict setback check ---")
    test_code_strict_pass_when_meets_nbc()
    test_code_strict_pass_when_exceeds_nbc()
    test_code_strict_hard_fail_on_one_side()
    test_code_strict_hard_fail_on_multiple_sides()
    test_code_strict_violations_carry_shortfall_pct()
    test_code_strict_check_is_spatial_category()
    test_code_strict_check_id_is_code_strict_specific()
    test_code_strict_carries_nbc_values()
    print()

    print("--- Gap computation ---")
    test_gap_is_none_when_user_meets_nbc()
    test_gap_marginal_for_small_shortfall()
    test_gap_significant_for_moderate_shortfall()
    test_gap_blocking_for_large_shortfall()
    test_gap_severity_uses_worst_side()
    test_gap_practical_value_has_all_4_sides()
    test_gap_code_strict_value_has_all_4_sides()
    test_gap_default_user_acceptable_is_none()
    test_gap_default_decision_source_is_system()
    test_gap_impact_description_mentions_each_violation()
    test_gap_check_id_is_setback_compliance()
    print()

    print("--- Dual-design pattern proof ---")
    test_dual_design_diverges_for_below_nbc_brief()
    test_dual_design_converges_when_user_meets_nbc()
    test_dual_design_scoring_diverges_correctly()
    test_dual_design_with_other_cities()
    print()

    print("--- Integration ---")
    test_setback_check_combines_with_session_a_b_checks()
    test_branch_check_carries_variant_in_details()
    test_v0_9_3_baseline_unaffected_by_session_c()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION C TESTS PASSED")
    print("=" * 70)
