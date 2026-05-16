"""
Component 2 Session F tests.

Coverage:
  - rwh_approval_rules KB: validator + 6 cities + 3 tiers
  - check_rwh_practical: PASS/SOFT_WARN per city + plot tier
  - check_rwh_code_strict: PASS when mandated, SOFT when not
  - compute_rwh_gap: INFO_ONLY when not mandated, None when mandated
  - check_approval_complexity: SIMPLE/MEDIUM/COMPLEX tiers, INFO-only
  - End-to-end with all 18 checks operational
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


# ─── rwh_approval_rules KB ────────────────────────────────────────────

def test_rwh_kb_loads_all_6_cities():
    from buildemup.utils.kb_rules_loader import load_rules, clear_cache
    clear_cache()
    data = load_rules("rwh_approval_rules")
    cities = list(data["rwh_mandate_by_city"].keys())
    assert set(cities) == {
        "chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi",
    }
    print("PASS rwh_approval_rules KB has all 6 launch cities")


def test_rwh_chennai_always_mandatory():
    from buildemup.utils.kb_rules_loader import load_rules
    data = load_rules("rwh_approval_rules")
    assert data["rwh_mandate_by_city"]["chennai"]["always_mandatory"] is True
    print("PASS Chennai RWH always_mandatory=True (TN ordinance 2003)")


def test_rwh_bangalore_threshold_111():
    from buildemup.utils.kb_rules_loader import load_rules
    data = load_rules("rwh_approval_rules")
    assert data["rwh_mandate_by_city"]["bangalore"]["plot_area_threshold_sqm"] == 111
    print("PASS Bangalore RWH threshold = 111 sqm (1200 sqft per BWSSB Act)")


def test_rwh_delhi_has_roof_threshold():
    from buildemup.utils.kb_rules_loader import load_rules
    data = load_rules("rwh_approval_rules")
    assert data["rwh_mandate_by_city"]["delhi"]["roof_area_threshold_sqm"] == 100
    print("PASS Delhi RWH has roof_area threshold (100 sqm)")


def test_approval_kb_has_3_tiers():
    from buildemup.utils.kb_rules_loader import load_rules
    data = load_rules("rwh_approval_rules")
    assert set(data["approval_complexity_tiers"].keys()) == {
        "simple", "medium", "complex",
    }
    print("PASS approval KB has 3 tiers (simple/medium/complex)")


def test_rwh_kb_validator_catches_missing_section():
    from buildemup.utils.kb_rules_loader import (
        _validate_rwh_approval_rules, RuleSchemaError,
    )
    bad = {"_meta": {"_version": "test"}}
    try:
        _validate_rwh_approval_rules(bad)
        assert False
    except RuleSchemaError:
        pass
    print("PASS rwh_approval validator catches missing top-level section")


def test_rwh_kb_validator_catches_non_bool_mandatory():
    from buildemup.utils.kb_rules_loader import (
        _validate_rwh_approval_rules, RuleSchemaError,
    )
    bad = {
        "_meta": {"_version": "test"},
        "rwh_mandate_by_city": {
            "chennai": {
                "always_mandatory": "yes",  # should be bool, not string
                "plot_area_threshold_sqm": None,
                "authority": "x", "regulation": "y",
            },
        },
        "approval_complexity_tiers": {
            "simple": {"typical_timeline_weeks": "1", "typical_authority_path": "x", "user_burden_summary": "y"},
            "medium": {"typical_timeline_weeks": "1", "typical_authority_path": "x", "user_burden_summary": "y"},
            "complex": {"typical_timeline_weeks": "1", "typical_authority_path": "x", "user_burden_summary": "y"},
        },
    }
    try:
        _validate_rwh_approval_rules(bad)
        assert False
    except RuleSchemaError:
        pass
    print("PASS rwh_approval validator catches non-bool always_mandatory")


# ─── RWH Practical ────────────────────────────────────────────────────

def test_rwh_practical_chennai_always_soft_warn():
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_practical,
    )
    brief = _build_brief(city="chennai")
    r = check_rwh_practical(brief)
    assert r.severity.value == "soft_warn"
    assert r.details["always_mandatory"] is True
    print("PASS Chennai RWH always SOFT_WARN (always mandatory)")


def test_rwh_practical_bangalore_below_threshold_passes():
    """100 sqm plot is below Bangalore's 111 threshold → PASS."""
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_practical,
    )
    brief = _build_brief(city="bangalore", plot_width_m=10.0, plot_depth_m=10.0)
    r = check_rwh_practical(brief)
    assert r.severity.value == "pass"
    print("PASS Bangalore 100 sqm (below threshold 111) → RWH not legally required")


def test_rwh_practical_bangalore_above_threshold_soft_warn():
    """200 sqm plot exceeds Bangalore's 111 threshold → SOFT_WARN."""
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_practical,
    )
    brief = _build_brief(city="bangalore", plot_width_m=12.0, plot_depth_m=17.0)
    r = check_rwh_practical(brief)
    assert r.severity.value == "soft_warn"
    print("PASS Bangalore 204 sqm (above threshold 111) → RWH SOFT_WARN")


def test_rwh_practical_mumbai_above_300_soft_warn():
    """Mumbai threshold is 300 sqm."""
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_practical,
    )
    brief = _build_brief(city="mumbai", plot_width_m=20.0, plot_depth_m=20.0)
    r = check_rwh_practical(brief)
    assert r.severity.value == "soft_warn"
    print("PASS Mumbai 400 sqm (above 300 threshold) → RWH SOFT_WARN")


def test_rwh_practical_mumbai_below_300_passes():
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_practical,
    )
    brief = _build_brief(city="mumbai", plot_width_m=12.0, plot_depth_m=15.0)
    r = check_rwh_practical(brief)
    assert r.severity.value == "pass"
    print("PASS Mumbai 180 sqm (below 300 threshold) → RWH not legally required")


def test_rwh_practical_includes_authority_and_cost():
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_practical,
    )
    brief = _build_brief(city="chennai")
    r = check_rwh_practical(brief)
    assert r.details["authority"] is not None
    assert "CMDA" in r.details["authority"]
    assert "estimated_cost_lakhs_range" in r.details
    print("PASS RWH practical result includes authority + cost range")


def test_rwh_practical_is_cost_category():
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_practical,
    )
    from buildemup.domain.feasibility import CheckCategory
    brief = _build_brief()
    r = check_rwh_practical(brief)
    assert r.category == CheckCategory.COST
    print("PASS RWH check is in COST category")


# ─── RWH Code-Strict ──────────────────────────────────────────────────

def test_rwh_code_strict_soft_warn_when_city_mandates():
    """When city mandates, Code-Strict should ALSO SOFT_WARN (cost adder applies).
    
    This was changed in Session G: previously Code-Strict PASSed when
    city mandated, but that produced the unintuitive result of
    Code-Strict scoring HIGHER than Practical. Now both lanes SOFT_WARN
    for the same situation, matching user expectation.
    """
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_code_strict,
    )
    brief = _build_brief(city="chennai")
    r = check_rwh_code_strict(brief)
    assert r.severity.value == "soft_warn"
    print("PASS RWH code_strict SOFT_WARNs when city mandates (cost adder)")


def test_rwh_code_strict_soft_warn_when_city_doesnt_mandate():
    """When city does NOT mandate, CodeStrict still recommends per NBC sustainability."""
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_code_strict,
    )
    brief = _build_brief(city="bangalore", plot_width_m=10.0, plot_depth_m=10.0)
    r = check_rwh_code_strict(brief)
    assert r.severity.value == "soft_warn"
    assert "NBC" in r.details["nbc_reference"]
    print("PASS RWH code_strict SOFT_WARNs when city doesn't mandate (NBC sustainability)")


# ─── RWH Gap ──────────────────────────────────────────────────────────

def test_rwh_gap_none_when_city_mandates():
    """No divergence when city mandates → no gap."""
    from buildemup.components.c02.sustainability_checks import compute_rwh_gap
    brief = _build_brief(city="chennai")
    g = compute_rwh_gap(brief)
    assert g is None
    print("PASS RWH gap None when city mandates (no divergence)")


def test_rwh_gap_info_only_when_not_mandated():
    """Practical pass + CodeStrict soft_warn → INFO_ONLY gap."""
    from buildemup.components.c02.sustainability_checks import compute_rwh_gap
    from buildemup.domain.feasibility import GapSeverity
    brief = _build_brief(city="bangalore", plot_width_m=10.0, plot_depth_m=10.0)
    g = compute_rwh_gap(brief)
    assert g is not None
    assert g.severity == GapSeverity.INFO_ONLY
    print("PASS RWH gap is INFO_ONLY when city doesn't mandate")


def test_rwh_gap_carries_cost_in_code_strict_value():
    from buildemup.components.c02.sustainability_checks import compute_rwh_gap
    brief = _build_brief(city="bangalore", plot_width_m=10.0, plot_depth_m=10.0)
    g = compute_rwh_gap(brief)
    assert "estimated_cost_lakhs_range" in g.code_strict_value
    print("PASS RWH gap carries cost range in code_strict_value")


# ─── Approval complexity ──────────────────────────────────────────────

def test_approval_simple_for_small_low_rise():
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    brief = _build_brief(plot_width_m=12.0, plot_depth_m=15.0)  # 180 sqm, G+0
    r = check_approval_complexity(brief)
    assert r.details["complexity_tier"] == "simple"
    assert r.severity.value == "pass"  # INFO never blocks
    print(f"PASS small low-rise → simple tier ({r.details['typical_timeline_weeks']}w)")


def test_approval_medium_for_mid_plot():
    """400 sqm plot → medium tier."""
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    brief = _build_brief(plot_width_m=20.0, plot_depth_m=20.0)
    r = check_approval_complexity(brief)
    assert r.details["complexity_tier"] == "medium"
    print(f"PASS 400 sqm plot → medium tier ({r.details['typical_timeline_weeks']}w)")


def test_approval_complex_for_large_plot():
    """1225 sqm plot → complex tier."""
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    brief = _build_brief(
        plot_width_m=35.0, plot_depth_m=35.0,
        road_width_m=12.0,
        user_setback_front_m=3.0, user_setback_rear_m=2.0,
        user_setback_side_left_m=2.0, user_setback_side_right_m=2.0,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
            FloorRequirement(2, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
            FloorRequirement(3, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
        budget_min_lakhs=200, budget_max_lakhs=300,
    )
    r = check_approval_complexity(brief)
    assert r.details["complexity_tier"] == "complex"
    assert len(r.details["typical_nocs_required"]) >= 5
    print(f"PASS 1225 sqm plot → complex tier "
          f"({r.details['typical_timeline_weeks']}w, "
          f"{len(r.details['typical_nocs_required'])} NOCs)")


def test_approval_severity_pass_for_simple_medium_softwarn_for_complex():
    """Session K (drawback 6 fix): approval check now SOFT_WARNs when
    tier=complex (16-40 weeks, multiple NOCs, possibly EIA). Returns
    PASS for simple + medium tiers."""
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    # Simple tier (small G+0)
    simple_brief = _build_brief(plot_width_m=12.0, plot_depth_m=15.0)
    simple_r = check_approval_complexity(simple_brief)
    assert simple_r.details["complexity_tier"] == "simple"
    assert simple_r.severity.value == "pass"

    # Complex tier (G+3 large with high road)
    complex_brief = _build_brief(
        plot_width_m=35.0, plot_depth_m=35.0,
        road_width_m=12.0,
        user_setback_front_m=3.0, user_setback_rear_m=2.0,
        user_setback_side_left_m=2.0, user_setback_side_right_m=2.0,
    )
    complex_r = check_approval_complexity(complex_brief)
    assert complex_r.details["complexity_tier"] == "complex"
    assert complex_r.severity.value == "soft_warn"
    print("PASS approval is PASS for simple/medium, SOFT_WARN for complex (Session K)")


def test_approval_includes_user_burden_summary():
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    brief = _build_brief()
    r = check_approval_complexity(brief)
    assert "user_burden_summary" in r.details
    assert len(r.details["user_burden_summary"]) > 20
    print("PASS approval result includes user burden summary")


def test_approval_score_contribution_zero():
    """INFO PASS contributes 0 to score (doesn't move the needle)."""
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    brief = _build_brief()
    r = check_approval_complexity(brief)
    assert r.score_contribution == 0
    print("PASS approval check has 0 score contribution (INFO-only)")


# ─── ALL 18 CHECKS NOW OPERATIONAL — integration test ────────────────

def test_all_18_checks_integrate_for_normal_brief():
    """Every operational check across A-F runs cleanly on a normal brief.
    
    Counts:
      Session A (4): envelope, floor stack, parking width, budget
      Session B (6): FAR, ground coverage, fire access, electric line,
                     water course, stilt mandate
      Session C (1 branched + gap): setbacks
      Session D (2 branched + gaps): solar, ventilation
      Session E (2 branched + gaps): soil, water table
      Session F (2 branched, 1 unbranched): RWH (branched), approval (info)
      
    Total operational: 17 (room minimums deferred to v0.2)
    """
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
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
        check_solar_exposure_practical, check_solar_exposure_code_strict,
        check_cross_ventilation_practical,
        check_cross_ventilation_code_strict,
    )
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_practical, check_soil_type_code_strict,
        check_water_table_practical, check_water_table_code_strict,
    )
    from buildemup.components.c02.sustainability_checks import (
        check_rwh_practical, check_rwh_code_strict,
        check_approval_complexity,
    )

    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),
             RoomRequirement(RoomType.KITCHEN, 1))),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    out = BriefCaptureEngine().execute(inp)
    brief = out.brief
    feas_inp = FeasibilityInput(brief=brief)

    # Run every operational check
    all_results = (
        # Session A
        check_envelope_sufficiency(brief),
        check_floor_stack_feasibility(brief),
        check_parking_width(brief),
        check_budget_feasibility(brief, out.c7_preview_cost),
        # Session B
        check_far_compliance(brief),
        check_ground_coverage_compliance(brief),
        check_fire_tender_access(brief),
        check_electric_line_clearance(brief),
        check_water_course_clearance(brief),
        check_stilt_mandate_compliance(brief),
        # Session C (branched - both lanes)
        check_setback_compliance_practical(brief),
        check_setback_compliance_code_strict(brief),
        # Session D (branched - both lanes)
        check_solar_exposure_practical(brief),
        check_solar_exposure_code_strict(brief),
        check_cross_ventilation_practical(brief),
        check_cross_ventilation_code_strict(brief),
        # Session E (branched - both lanes, FeasibilityInput)
        check_soil_type_practical(feas_inp),
        check_soil_type_code_strict(feas_inp),
        check_water_table_practical(feas_inp),
        check_water_table_code_strict(feas_inp),
        # Session F (branched RWH + info-only approval)
        check_rwh_practical(brief),
        check_rwh_code_strict(brief),
        check_approval_complexity(brief),
    )
    # Should have 23 results (17 unique checks but some branched have 2 lanes)
    assert len(all_results) == 23
    # Every result is a valid CheckResult
    from buildemup.domain.feasibility import CheckResult
    for r in all_results:
        assert isinstance(r, CheckResult)
        assert r.check_id != ""
    print(f"PASS all 23 check results across A-F sessions integrate cleanly")


def test_all_branched_checks_have_gap_helpers():
    """Every branched check has a corresponding compute_*_gap function."""
    from buildemup.components.c02.branched_checks import (
        compute_setback_gap, compute_solar_gap, compute_ventilation_gap,
    )
    from buildemup.components.c02.site_input_checks import (
        compute_soil_type_gap, compute_water_table_gap,
    )
    from buildemup.components.c02.sustainability_checks import (
        compute_rwh_gap,
    )
    # All 6 branched checks have gap helpers
    helpers = [
        compute_setback_gap, compute_solar_gap, compute_ventilation_gap,
        compute_soil_type_gap, compute_water_table_gap, compute_rwh_gap,
    ]
    assert len(helpers) == 6
    print("PASS all 6 branched checks have corresponding gap helpers")


def test_v0_9_3_baseline_unaffected_by_session_f():
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
    print("PASS v0.9.3 baseline unaffected by Session F")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session F (RWH + Approval Complexity)")
    print("=" * 70)
    print()

    print("--- rwh_approval_rules KB ---")
    test_rwh_kb_loads_all_6_cities()
    test_rwh_chennai_always_mandatory()
    test_rwh_bangalore_threshold_111()
    test_rwh_delhi_has_roof_threshold()
    test_approval_kb_has_3_tiers()
    test_rwh_kb_validator_catches_missing_section()
    test_rwh_kb_validator_catches_non_bool_mandatory()
    print()

    print("--- RWH Practical ---")
    test_rwh_practical_chennai_always_soft_warn()
    test_rwh_practical_bangalore_below_threshold_passes()
    test_rwh_practical_bangalore_above_threshold_soft_warn()
    test_rwh_practical_mumbai_above_300_soft_warn()
    test_rwh_practical_mumbai_below_300_passes()
    test_rwh_practical_includes_authority_and_cost()
    test_rwh_practical_is_cost_category()
    print()

    print("--- RWH Code-Strict ---")
    test_rwh_code_strict_soft_warn_when_city_mandates()
    test_rwh_code_strict_soft_warn_when_city_doesnt_mandate()
    print()

    print("--- RWH Gap ---")
    test_rwh_gap_none_when_city_mandates()
    test_rwh_gap_info_only_when_not_mandated()
    test_rwh_gap_carries_cost_in_code_strict_value()
    print()

    print("--- Approval complexity ---")
    test_approval_simple_for_small_low_rise()
    test_approval_medium_for_mid_plot()
    test_approval_complex_for_large_plot()
    test_approval_severity_pass_for_simple_medium_softwarn_for_complex()
    test_approval_includes_user_burden_summary()
    test_approval_score_contribution_zero()
    print()

    print("--- ALL 18 CHECKS INTEGRATION ---")
    test_all_18_checks_integrate_for_normal_brief()
    test_all_branched_checks_have_gap_helpers()
    test_v0_9_3_baseline_unaffected_by_session_f()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION F TESTS PASSED")
    print("Component 2 has all 18 v0.1 checks operational (1 deferred to v0.2)")
    print("=" * 70)
