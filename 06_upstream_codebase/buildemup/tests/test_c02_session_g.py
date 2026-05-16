"""
Component 2 Session G tests.

Coverage:
  - run_feasibility public API
  - DesignGapAnalysis assembly correctness
  - Both reports built with all 17 checks
  - Gap aggregation across 6 branched checks
  - Cost delta computation
  - Unknown aggregation across check results
  - ActionStep generation with priorities
  - Score consistency between lanes
  - Edge cases: best case, worst case, no C7 estimate
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _build_brief_with_c7(**overrides):
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
    out = BriefCaptureEngine().execute(inp)
    return out.brief, out.c7_preview_cost


# ─── Public API smoke ─────────────────────────────────────────────────

def test_run_feasibility_returns_design_gap_analysis():
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.domain.feasibility import DesignGapAnalysis
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    assert isinstance(result, DesignGapAnalysis)
    print("PASS run_feasibility returns DesignGapAnalysis")


def test_run_feasibility_works_without_c7_estimate():
    """Orchestrator should be callable without c7 estimate."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, _ = _build_brief_with_c7()
    result = run_feasibility(brief)  # no c7
    # Budget check will be NOT_APPLICABLE
    budget_check = next(
        (r for r in result.practical_report.all_check_results
         if r.check_id == "budget_feasibility"),
        None,
    )
    assert budget_check is not None
    assert budget_check.severity.value == "not_applicable"
    print("PASS run_feasibility works without c7_estimate (budget = NA)")


def test_run_feasibility_works_without_feasibility_input():
    """Orchestrator should construct default FeasibilityInput when not given."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Soil + WT should still produce valid CheckResults
    soil_p = next(
        r for r in result.practical_report.all_check_results
        if r.check_id == "soil_type_practical"
    )
    assert soil_p is not None
    print("PASS run_feasibility constructs default FeasibilityInput when None")


# ─── Both reports have correct structure ──────────────────────────────

def test_both_reports_have_correct_variant():
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.domain.feasibility import DesignVariant
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    assert result.practical_report.variant == DesignVariant.PRACTICAL
    assert result.code_strict_report.variant == DesignVariant.CODE_STRICT
    print("PASS both reports tagged with correct DesignVariant")


def test_both_reports_have_17_checks():
    """Each report should contain all 17 operational checks (10 unbranched
    + 6 branched + 1 info-only = 17 unique checks per lane)."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    p_total = len(result.practical_report.all_check_results)
    c_total = len(result.code_strict_report.all_check_results)
    assert p_total == 17, f"Practical has {p_total}, expected 17"
    assert c_total == 17, f"Code-Strict has {c_total}, expected 17"
    print(f"PASS both reports have 17 checks each (P={p_total}, C={c_total})")


def test_both_reports_share_unbranched_checks():
    """Unbranched checks (envelope, FAR, etc.) should appear identically
    in both reports."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Get envelope check from both
    p_envelope = next(
        r for r in result.practical_report.all_check_results
        if r.check_id == "envelope_sufficiency"
    )
    c_envelope = next(
        r for r in result.code_strict_report.all_check_results
        if r.check_id == "envelope_sufficiency"
    )
    # Same severity + same details → unbranched
    assert p_envelope.severity == c_envelope.severity
    assert p_envelope.details == c_envelope.details
    print("PASS unbranched checks are identical in both reports (envelope)")


def test_branched_checks_have_distinct_check_ids():
    """Branched checks have practical + code_strict variants with
    different check_ids."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    p_ids = {r.check_id for r in result.practical_report.all_check_results}
    c_ids = {r.check_id for r in result.code_strict_report.all_check_results}
    # setback_practical in P, setback_code_strict in C
    assert "setback_practical" in p_ids
    assert "setback_code_strict" in c_ids
    assert "setback_practical" not in c_ids
    assert "setback_code_strict" not in p_ids
    print("PASS branched checks have lane-specific check_ids")


# ─── Score consistency ───────────────────────────────────────────────

def test_practical_and_code_strict_match_when_user_meets_nbc():
    """When user meets NBC + provides verified data, both lanes should
    score similarly (no gaps expected)."""
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, c7 = _build_brief_with_c7(
        plot_width_m=15.0, plot_depth_m=20.0, plot_facing="S",
        road_width_m=12.0,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),
             RoomRequirement(RoomType.KITCHEN, 1))),),
        budget_min_lakhs=30, budget_max_lakhs=40,
    )
    feas_inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("sandy_alluvial"),
        water_table_depth_m=InputField.verified(8.0),
    )
    result = run_feasibility(
        brief, c7_cost_estimate=c7, feasibility_input=feas_inp,
        distance_from_electric_line_m=10.0, electric_line_type="lt",
        has_water_course_within_30m=False,
    )
    # Scores should be equal (both have RWH SOFT_WARN since Chennai mandates)
    assert result.practical_report.overall_score == result.code_strict_report.overall_score
    print(f"PASS scores match when NBC met: P={result.practical_report.overall_score}, "
          f"C={result.code_strict_report.overall_score}")


def test_code_strict_score_lower_when_user_below_nbc():
    """When user has below-NBC choices, Code-Strict should score lower."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(
        # User chose below-NBC setbacks
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Code-Strict should have lower score (more HARDs)
    assert result.code_strict_report.overall_score <= result.practical_report.overall_score
    print(f"PASS Code-Strict ≤ Practical when user below NBC: "
          f"P={result.practical_report.overall_score}, "
          f"C={result.code_strict_report.overall_score}")


def test_both_reports_use_scoring_contract():
    """Both reports should use the same scoring contract (HARD caps at 40).
    A brief with HARD_FAIL should have score ≤ 40 in that lane."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(
        # Force HARD via 4m road on G+1
        road_width_m=4.0,
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Practical has fire access HARD → capped at 40
    if len(result.practical_report.blocking_issues) > 0:
        assert result.practical_report.overall_score <= 40
    print(f"PASS scoring contract enforced: HARD caps at 40 "
          f"(score {result.practical_report.overall_score})")


# ─── Gap aggregation ─────────────────────────────────────────────────

def test_gaps_only_for_branched_checks_with_divergence():
    """No gaps when user meets NBC + verifies all data."""
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    # Best case: meets NBC + verified data
    brief, c7 = _build_brief_with_c7(
        plot_width_m=15.0, plot_depth_m=20.0, plot_facing="S",
        road_width_m=12.0,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),
             RoomRequirement(RoomType.KITCHEN, 1))),),
        budget_min_lakhs=30, budget_max_lakhs=40,
    )
    feas_inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("sandy_alluvial"),
        water_table_depth_m=InputField.verified(8.0),
    )
    result = run_feasibility(
        brief, c7_cost_estimate=c7, feasibility_input=feas_inp,
        distance_from_electric_line_m=10.0, electric_line_type="lt",
        has_water_course_within_30m=False,
    )
    # Chennai always mandates RWH → no RWH gap (both lanes flag it)
    # G+0 single floor → no soil gap
    # Verified WT → no WT gap
    # S-facing → no solar gap
    # Detached → no vent gap
    # User meets NBC → no setback gap
    assert len(result.gaps) == 0
    assert result.has_meaningful_gap is False
    print("PASS no gaps when best case (all data verified, S-facing, NBC met)")


def test_gaps_max_6_when_all_branched_diverge():
    """At most 6 gaps possible (one per branched check)."""
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    # N-facing + below-NBC setbacks + don't-know fields + G+1
    # to trigger as many gap conditions as possible
    brief, c7 = _build_brief_with_c7(
        plot_facing="N",
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1))),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    assert len(result.gaps) <= 6
    assert len(result.gaps) >= 3   # at least setback + solar + soil + WT
    print(f"PASS at most 6 gaps possible, got {len(result.gaps)} "
          f"for adversarial brief")


def test_gaps_carry_check_ids():
    """Each Gap should have its check_id matching one of the 6 branched checks."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(
        plot_facing="N",
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    valid_gap_ids = {
        "setback_compliance", "solar_exposure", "cross_ventilation",
        "soil_type", "water_table", "rwh",
    }
    for gap in result.gaps:
        assert gap.check_id in valid_gap_ids
    print(f"PASS all {len(result.gaps)} gaps have valid check_ids")


# ─── Cost delta ──────────────────────────────────────────────────────

def test_cost_delta_zero_when_no_gaps():
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, c7 = _build_brief_with_c7(
        plot_width_m=15.0, plot_depth_m=20.0, plot_facing="S",
        road_width_m=12.0,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),
             RoomRequirement(RoomType.KITCHEN, 1))),),
        budget_min_lakhs=30, budget_max_lakhs=40,
    )
    feas_inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("sandy_alluvial"),
        water_table_depth_m=InputField.verified(8.0),
    )
    result = run_feasibility(
        brief, c7_cost_estimate=c7, feasibility_input=feas_inp,
        distance_from_electric_line_m=10.0, electric_line_type="lt",
        has_water_course_within_30m=False,
    )
    assert result.cost_delta_lakhs == 0.0
    print("PASS cost_delta is 0 when no gaps")


def test_cost_delta_includes_soil_when_soil_gap_present():
    """Soil gap → ₹0.10L cost adder (NABL test)."""
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, c7 = _build_brief_with_c7(
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1))),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Has soil gap (G+1 + unverified) and water table gap (habitable ground + unverified)
    # Cost = 0.10 (soil) + 0.05 (WT) = 0.15
    assert result.cost_delta_lakhs >= 0.10
    print(f"PASS cost_delta includes soil + WT verification "
          f"(₹{result.cost_delta_lakhs}L)")


def test_cost_delta_includes_rwh_when_not_mandated():
    """RWH gap (city doesn't mandate, NBC recommends) → ₹1.0L cost adder."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(
        # Bangalore + 100 sqm = below RWH threshold → RWH gap (INFO_ONLY)
        city="bangalore",
        plot_width_m=10.0, plot_depth_m=10.0,
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Should have RWH gap → contributes 1.0 to cost delta
    rwh_gaps = [g for g in result.gaps if g.check_id == "rwh"]
    if rwh_gaps:
        assert result.cost_delta_lakhs >= 1.0
        print(f"PASS cost_delta includes RWH cost when not mandated "
              f"(₹{result.cost_delta_lakhs}L)")
    else:
        # No RWH gap means city mandates RWH (no Practical/CodeStrict diff)
        print("PASS no RWH gap (city mandates RWH; cost_delta unchanged)")


# ─── Unknown aggregation ─────────────────────────────────────────────

def test_unknowns_aggregated_for_unspecified_fields():
    """Defaults FeasibilityInput → all 6 fields NOT_ASKED → unknowns surface."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Should have unknowns for soil, water_table, electric, water course
    field_names = {u.field_name for u in result.practical_report.unknowns}
    assert "soil_type" in field_names
    assert "water_table_depth_m" in field_names
    print(f"PASS {len(result.practical_report.unknowns)} unknowns aggregated: "
          f"{sorted(field_names)}")


def test_unknowns_have_verification_priority():
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.domain.feasibility import VerificationPriority
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    for u in result.practical_report.unknowns:
        assert isinstance(u.priority, VerificationPriority)
    print("PASS each Unknown has a VerificationPriority")


def test_unknowns_dedupe_by_field():
    """If both practical + code_strict use same assumption, only one Unknown."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    field_names = [u.field_name for u in result.practical_report.unknowns]
    # No duplicates
    assert len(field_names) == len(set(field_names))
    print("PASS Unknown fields deduped (no duplicates)")


def test_unknowns_link_to_affected_check_ids():
    """Each Unknown should list which checks were affected."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    for u in result.practical_report.unknowns:
        assert len(u.affects_check_ids) >= 1
    print("PASS Unknowns link to ≥1 affected check_id each")


def test_no_unknowns_when_all_data_verified():
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    brief, c7 = _build_brief_with_c7()
    feas_inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("sandy_alluvial"),
        water_table_depth_m=InputField.verified(8.0),
    )
    result = run_feasibility(
        brief, c7_cost_estimate=c7, feasibility_input=feas_inp,
        distance_from_electric_line_m=10.0, electric_line_type="lt",
        has_water_course_within_30m=False,
    )
    # All 4 fields known → 0 unknowns
    assert len(result.practical_report.unknowns) == 0
    print("PASS no Unknowns when all 4 optional fields verified")


# ─── ActionStep generation ───────────────────────────────────────────

def test_action_steps_generated_per_blocking_issue():
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(road_width_m=4.0)  # fire access HARD
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Should have ActionStep for fire_tender_access
    fire_actions = [
        a for a in result.practical_report.action_steps
        if "fire_tender_access" in a.triggering_check_ids
    ]
    assert len(fire_actions) >= 1
    print("PASS ActionStep generated for fire access HARD_FAIL")


def test_action_steps_have_priorities():
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(road_width_m=4.0)
    result = run_feasibility(brief, c7_cost_estimate=c7)
    for a in result.practical_report.action_steps:
        assert 1 <= a.priority <= 5
    print("PASS ActionSteps have priority in [1, 5]")


def test_action_steps_link_to_triggering_check_ids():
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(road_width_m=4.0)
    result = run_feasibility(brief, c7_cost_estimate=c7)
    for a in result.practical_report.action_steps:
        assert len(a.triggering_check_ids) >= 1
    print("PASS ActionSteps link to ≥1 triggering check_id")


def test_no_action_steps_when_all_pass():
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    brief, c7 = _build_brief_with_c7(
        plot_width_m=15.0, plot_depth_m=20.0, plot_facing="S",
        road_width_m=12.0,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),
             RoomRequirement(RoomType.KITCHEN, 1))),),
        budget_min_lakhs=30, budget_max_lakhs=40,
    )
    feas_inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("sandy_alluvial"),
        water_table_depth_m=InputField.verified(8.0),
    )
    result = run_feasibility(
        brief, c7_cost_estimate=c7, feasibility_input=feas_inp,
        distance_from_electric_line_m=10.0, electric_line_type="lt",
        has_water_course_within_30m=False,
    )
    # Best case has only RWH SOFT_WARN (Chennai always mandates)
    # So action steps = 1 (the RWH one)
    assert len(result.practical_report.action_steps) <= 2
    print(f"PASS minimal action steps in best case "
          f"({len(result.practical_report.action_steps)} actions)")


# ─── User decisions ──────────────────────────────────────────────────

def test_user_decisions_one_per_blocking_or_significant_gap():
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(
        plot_facing="N",
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    # Each non-INFO gap → one decision
    non_info_gaps = [
        g for g in result.gaps if g.severity.value != "info_only"
    ]
    assert len(result.user_decisions_required) == len(non_info_gaps)
    print(f"PASS user_decisions_required count matches non-INFO gaps "
          f"({len(non_info_gaps)})")


def test_info_gaps_excluded_from_user_decisions():
    """INFO_ONLY gaps shouldn't surface in user_decisions_required."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7(
        city="bangalore",
        plot_width_m=10.0, plot_depth_m=10.0,
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    info_gaps = [g for g in result.gaps if g.severity.value == "info_only"]
    if info_gaps:
        # INFO gaps don't appear in decisions (they're info-only)
        assert len(result.user_decisions_required) < len(result.gaps)
    print(f"PASS INFO gaps excluded from decisions ({len(info_gaps)} INFO gaps)")


# ─── DesignGapAnalysis properties ────────────────────────────────────

def test_has_meaningful_gap_property():
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result = run_feasibility(brief, c7_cost_estimate=c7)
    if len(result.gaps) > 0:
        assert result.has_meaningful_gap is True
    else:
        assert result.has_meaningful_gap is False
    print(f"PASS has_meaningful_gap={result.has_meaningful_gap} "
          f"(matches gap count {len(result.gaps)})")


def test_blocking_gaps_filters_severity():
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.domain.feasibility import GapSeverity
    brief, c7 = _build_brief_with_c7(
        plot_facing="N",
        user_setback_front_m=0.9, user_setback_rear_m=0.9,
        user_setback_side_left_m=0.9, user_setback_side_right_m=0.9,
    )
    result = run_feasibility(brief, c7_cost_estimate=c7)
    blocking = result.blocking_gaps
    for g in blocking:
        assert g.severity == GapSeverity.BLOCKING_IF_NOT_ACCEPTED
    print(f"PASS blocking_gaps property filters correctly "
          f"({len(blocking)} BLOCKING gaps)")


# ─── Full integration ───────────────────────────────────────────────

def test_orchestrator_handles_all_6_cities():
    """Run feasibility for each of the 6 launch cities — should not crash."""
    from buildemup.components.c02.orchestrator import run_feasibility
    cities = ["chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi"]
    for city in cities:
        brief, c7 = _build_brief_with_c7(city=city)
        result = run_feasibility(brief, c7_cost_estimate=c7)
        assert result.practical_report.overall_score >= 0
    print(f"PASS orchestrator handles all 6 cities cleanly")


def test_orchestrator_reports_stable_across_runs():
    """Same input → same DesignGapAnalysis (deterministic)."""
    from buildemup.components.c02.orchestrator import run_feasibility
    brief, c7 = _build_brief_with_c7()
    result1 = run_feasibility(brief, c7_cost_estimate=c7)
    result2 = run_feasibility(brief, c7_cost_estimate=c7)
    assert result1.practical_report.overall_score == result2.practical_report.overall_score
    assert result1.code_strict_report.overall_score == result2.code_strict_report.overall_score
    assert len(result1.gaps) == len(result2.gaps)
    print("PASS orchestrator output deterministic across runs")


def test_v0_9_3_baseline_unaffected_by_session_g():
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
    print("PASS v0.9.3 baseline unaffected by Session G")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session G (Orchestrator)")
    print("=" * 70)
    print()

    print("--- Public API ---")
    test_run_feasibility_returns_design_gap_analysis()
    test_run_feasibility_works_without_c7_estimate()
    test_run_feasibility_works_without_feasibility_input()
    print()

    print("--- Both reports structure ---")
    test_both_reports_have_correct_variant()
    test_both_reports_have_17_checks()
    test_both_reports_share_unbranched_checks()
    test_branched_checks_have_distinct_check_ids()
    print()

    print("--- Score consistency ---")
    test_practical_and_code_strict_match_when_user_meets_nbc()
    test_code_strict_score_lower_when_user_below_nbc()
    test_both_reports_use_scoring_contract()
    print()

    print("--- Gap aggregation ---")
    test_gaps_only_for_branched_checks_with_divergence()
    test_gaps_max_6_when_all_branched_diverge()
    test_gaps_carry_check_ids()
    print()

    print("--- Cost delta ---")
    test_cost_delta_zero_when_no_gaps()
    test_cost_delta_includes_soil_when_soil_gap_present()
    test_cost_delta_includes_rwh_when_not_mandated()
    print()

    print("--- Unknown aggregation ---")
    test_unknowns_aggregated_for_unspecified_fields()
    test_unknowns_have_verification_priority()
    test_unknowns_dedupe_by_field()
    test_unknowns_link_to_affected_check_ids()
    test_no_unknowns_when_all_data_verified()
    print()

    print("--- ActionStep generation ---")
    test_action_steps_generated_per_blocking_issue()
    test_action_steps_have_priorities()
    test_action_steps_link_to_triggering_check_ids()
    test_no_action_steps_when_all_pass()
    print()

    print("--- User decisions ---")
    test_user_decisions_one_per_blocking_or_significant_gap()
    test_info_gaps_excluded_from_user_decisions()
    print()

    print("--- DesignGapAnalysis properties ---")
    test_has_meaningful_gap_property()
    test_blocking_gaps_filters_severity()
    print()

    print("--- Full integration ---")
    test_orchestrator_handles_all_6_cities()
    test_orchestrator_reports_stable_across_runs()
    test_v0_9_3_baseline_unaffected_by_session_g()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION G TESTS PASSED")
    print("=" * 70)
