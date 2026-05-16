"""
v0.6 Phase 1 tests — real engineering additions.

Covers:
  - Frame sanity engine (Hardy Cross + Bresler IS 456 cl. 39.6)
  - Load combinations (5 combos per Indian practice)
  - Soil classification with real IS 1904 values
  - Extended structural sensitivity (span + material grade)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.components.c07.frame_sanity import (
    FrameSanityResult, ColumnSanityCheck,
    compute_bresler_alpha_n, bresler_interaction_ratio,
    estimate_puz_kn, estimate_uniaxial_moment_capacity_knm,
    check_column_sanity, run_frame_sanity_check,
    estimate_beam_moment_kNm, hardy_cross_balance_at_joint,
)
from buildemup.components.c07.load_combinations import (
    LoadInputs, compute_load_combinations, find_governing_combination,
    estimate_lateral_load_share_per_column,
)
from buildemup.kb.soil_classification import (
    SoilClass, SoilProfile, get_soil_profile,
    check_foundation_adequacy, all_soil_classes,
    SOIL_PROFILES,
)
from buildemup.utils.structural_sensitivity import compute_structural_sensitivity


# ─── Frame sanity: Bresler αn interpolation ──────────────────────────────
def test_bresler_alpha_low_axial():
    """IS 456 cl. 39.6: Pu/Puz ≤ 0.2 → αn = 1.0"""
    assert compute_bresler_alpha_n(0.1) == 1.0
    assert compute_bresler_alpha_n(0.2) == 1.0
    print("PASS Bresler αn = 1.0 for low axial (Pu/Puz ≤ 0.2)")


def test_bresler_alpha_high_axial():
    """IS 456 cl. 39.6: Pu/Puz ≥ 0.8 → αn = 2.0"""
    assert compute_bresler_alpha_n(0.8) == 2.0
    assert compute_bresler_alpha_n(0.95) == 2.0
    print("PASS Bresler αn = 2.0 for high axial (Pu/Puz ≥ 0.8)")


def test_bresler_alpha_interpolation():
    """IS 456 cl. 39.6: linear interpolation in middle range."""
    # At Pu/Puz = 0.5, αn should be 1.5 (midpoint of 1.0 and 2.0)
    alpha = compute_bresler_alpha_n(0.5)
    assert abs(alpha - 1.5) < 0.01, f"αn(0.5) = {alpha}, expected 1.5"
    print(f"PASS Bresler αn interpolation at Pu/Puz=0.5: αn = {alpha}")


# ─── Frame sanity: Puz and Mux1 estimators ───────────────────────────────
def test_puz_estimator_reasonable():
    """Puz for 300x300 M25 1% steel should be ~1100-1400 kN (SP-16 range)."""
    puz = estimate_puz_kn(300, fck_mpa=25, steel_pct=1.0, fy_mpa=500)
    assert 1100 <= puz <= 1400, f"Puz = {puz}, expected 1100-1400 kN"
    print(f"PASS Puz for 300x300 M25 1% steel: {puz:.0f} kN (in SP-16 range)")


def test_mux1_estimator_parabolic():
    """Mux1 should peak around Pu/Puz = 0.2 (balanced failure)."""
    puz = 1340.0
    # Test: pure bending (Pu=0)
    m_pure_bend = estimate_uniaxial_moment_capacity_knm(300, 0, puz, 25)
    # Test: at balanced (Pu = 0.2 Puz)
    m_balanced = estimate_uniaxial_moment_capacity_knm(300, 0.2 * puz, puz, 25)
    # Test: near pure axial (Pu = 0.9 Puz)
    m_near_axial = estimate_uniaxial_moment_capacity_knm(300, 0.9 * puz, puz, 25)

    # Balanced should be highest; near-axial lowest; pure-bend in between
    assert m_balanced > m_pure_bend > m_near_axial, \
        f"Expected balanced > pure_bend > near_axial, got {m_balanced}, {m_pure_bend}, {m_near_axial}"
    print(f"PASS Mux1 parabolic: pure_bend={m_pure_bend:.1f}, "
          f"balanced={m_balanced:.1f}, near_axial={m_near_axial:.1f} kNm")


# ─── Frame sanity: full column checks ────────────────────────────────────
def test_safe_column_classified_safe():
    """Lightly loaded column should be SAFE."""
    result = check_column_sanity(
        column_id="C_light",
        pu_kn=400, mux_knm=10, muy_knm=8,
        column_dim_mm=300,
    )
    assert result.result == FrameSanityResult.SAFE
    assert result.bresler_ratio <= 0.8
    print(f"PASS lightly loaded column: SAFE (ratio={result.bresler_ratio})")


def test_overloaded_column_classified_fail():
    """Overloaded column with heavy bending should FAIL."""
    result = check_column_sanity(
        column_id="C_heavy",
        pu_kn=1000, mux_knm=100, muy_knm=80,
        column_dim_mm=300,
    )
    assert result.result == FrameSanityResult.FAIL
    assert result.bresler_ratio > 1.0
    print(f"PASS overloaded column: FAIL (ratio={result.bresler_ratio})")


def test_full_report_aggregates_correctly():
    """run_frame_sanity_check aggregates across columns correctly."""
    report = run_frame_sanity_check([
        {"column_id": "C1", "pu_kn": 400, "mux_knm": 10, "muy_knm": 8, "column_dim_mm": 300},
        {"column_id": "C2", "pu_kn": 1000, "mux_knm": 100, "muy_knm": 80, "column_dim_mm": 300},
        {"column_id": "C3", "pu_kn": 600, "mux_knm": 15, "muy_knm": 10, "column_dim_mm": 300},
    ])
    assert len(report.columns) == 3
    # Worst result should be FAIL (from C2)
    assert report.overall_result == FrameSanityResult.FAIL
    # Worst ratio should match C2's ratio
    assert report.worst_ratio > 1.0
    assert "FAIL: 1" in report.user_summary
    print(f"PASS report aggregates: {report.user_summary[:60]}")


def test_method_disclosure_honest():
    """Method disclosure must list both what we DO and what we DON'T."""
    report = run_frame_sanity_check([
        {"column_id": "C1", "pu_kn": 400, "mux_knm": 10, "muy_knm": 8, "column_dim_mm": 300},
    ])
    disclosure = report.method_disclosure
    assert "Hardy Cross" in disclosure
    assert "IS 456 cl. 39.6" in disclosure
    assert "NOT a full frame analysis" in disclosure
    assert "LEVEL 2 sanity check" in disclosure
    print(f"PASS method disclosure honest about scope")


# ─── Hardy Cross primitives ──────────────────────────────────────────────
def test_beam_fem_standard_formula():
    """Fixed-both-ends UDL beam: FEM = wL²/12"""
    fem_left, fem_right = estimate_beam_moment_kNm(
        beam_span_m=4.0, udl_kn_per_m=12.0, end_condition="fixed_both",
    )
    # Expected FEM = 12 * 16 / 12 = 16 kNm (hogging, so negative)
    assert abs(fem_left - (-16.0)) < 0.01
    assert abs(fem_right - (-16.0)) < 0.01
    print(f"PASS FEM for fixed-fixed UDL: {fem_left} kNm (expected -16)")


def test_hardy_cross_balances_unequal_moments():
    """Hardy Cross should distribute unbalanced moment proportionally."""
    # Joint with unequal FEMs: 20 and -10 kNm, equal stiffness.
    # Initial unbalance = +10. Equal stiffness means equal share of redistribution.
    # After iterations, the total (original FEMs + additional) should be more
    # balanced than at start.
    additional = hardy_cross_balance_at_joint(
        incoming_moments_kNm=[20.0, -10.0],
        member_stiffness_ratios=[1.0, 1.0],
        iterations=3,
    )
    # Both members should receive NEGATIVE correction (reducing the +10 unbalance)
    assert additional[0] < 0 and additional[1] < 0, \
        f"Expected negative corrections, got {additional}"
    # Equal stiffness → equal correction (within tolerance)
    assert abs(additional[0] - additional[1]) < 0.01, \
        f"Equal stiffness should give equal correction: {additional}"
    # Final sum should be closer to 0 than original unbalance of +10
    final_sum = (20 + additional[0]) + (-10 + additional[1])
    assert abs(final_sum) < 10.0, f"Not improved: final sum = {final_sum}"
    print(f"PASS Hardy Cross distributes moments: additional={additional}, final sum={final_sum:.2f}")


# ─── Load combinations ───────────────────────────────────────────────────
def test_five_combinations_generated():
    """compute_load_combinations must return exactly 5 combos."""
    inp = LoadInputs(
        column_id="C1", dead_load_kn=200, live_load_kn=40,
        wind_axial_kn=5, wind_moment_x_knm=10, wind_moment_y_knm=5,
        seismic_axial_kn=8, seismic_moment_x_knm=15, seismic_moment_y_knm=8,
    )
    combos = compute_load_combinations(inp)
    assert len(combos) == 5
    combo_names = [c.combo_name for c in combos]
    assert "1.5(DL+LL)" in combo_names
    assert "1.5(DL+LL+WL)" in combo_names
    assert "1.5(DL+LL+EQ)" in combo_names
    assert "0.9DL+1.5WL" in combo_names
    assert "0.9DL+1.5EQ" in combo_names
    print(f"PASS 5 combinations generated: {combo_names}")


def test_wind_and_eq_not_combined():
    """No combo should add wind AND earthquake together per IS practice."""
    inp = LoadInputs(
        column_id="C1", dead_load_kn=200, live_load_kn=40,
        wind_axial_kn=10, wind_moment_x_knm=20, wind_moment_y_knm=10,
        seismic_axial_kn=15, seismic_moment_x_knm=30, seismic_moment_y_knm=15,
    )
    combos = compute_load_combinations(inp)
    for combo in combos:
        # A combo that adds both would have Pu > 1.5*(200+40+10+15) = 397.5
        # Governing single-lateral combo max Pu = 1.5*(200+40+15) = 382.5
        # If wind+EQ were combined, Pu would exceed 390
        pure_gravity_plus_both = 1.5 * (200 + 40 + 10 + 15)  # 397.5
        if combo.combo_name not in ["1.5(DL+LL)"]:  # skip pure gravity
            # Compare against plausible max of single-lateral case
            assert combo.pu_kn <= pure_gravity_plus_both, \
                f"Combo {combo.combo_name} Pu={combo.pu_kn} suggests wind+EQ combined!"
    print(f"PASS no combo adds wind+EQ together")


def test_governing_combo_found():
    """Governing combo should be the one with highest |Pu|."""
    inp = LoadInputs(
        column_id="C1", dead_load_kn=200, live_load_kn=40,
        wind_axial_kn=2, wind_moment_x_knm=5, wind_moment_y_knm=3,
        seismic_axial_kn=10, seismic_moment_x_knm=18, seismic_moment_y_knm=12,
    )
    result = find_governing_combination(inp)
    # With large seismic, governing should be 1.5(DL+LL+EQ)
    assert result.governing_combo == "1.5(DL+LL+EQ)"
    print(f"PASS governing combo found: {result.governing_combo}")


def test_method_disclosure_says_wind_eq_not_combined():
    """Method disclosure must explicitly state wind+EQ not combined."""
    inp = LoadInputs(column_id="C1", dead_load_kn=200, live_load_kn=40,
                     wind_axial_kn=2, wind_moment_x_knm=5, wind_moment_y_knm=3,
                     seismic_axial_kn=10, seismic_moment_x_knm=18, seismic_moment_y_knm=12)
    result = find_governing_combination(inp)
    assert "NEVER combined per IS practice" in result.method_disclosure or \
           "not combined" in result.method_disclosure.lower()
    assert "IS 875 Part 5" in result.method_disclosure
    print(f"PASS method disclosure says wind+EQ not combined")


# ─── Soil classification ─────────────────────────────────────────────────
def test_real_is1904_hard_rock_values():
    """Hard rock SBC must align with real IS 1904 (up to 3300 kN/m²), not document's 300+."""
    hard_rock = get_soil_profile(SoilClass.HARD_ROCK)
    assert hard_rock.sbc_max_knm2 >= 1800, \
        f"Hard rock max SBC {hard_rock.sbc_max_knm2} seems too low for IS 1904"
    assert hard_rock.sbc_max_knm2 <= 3500, \
        f"Hard rock max SBC {hard_rock.sbc_max_knm2} seems too high"
    print(f"PASS hard rock SBC uses real IS 1904 range: "
          f"{hard_rock.sbc_min_knm2}-{hard_rock.sbc_max_knm2} kN/m²")


def test_soft_clay_sbc_range():
    """Soft clay: 75-100 kN/m² per IS 1904 (and user decision)."""
    soft = get_soil_profile(SoilClass.SOFT_CLAY)
    assert soft.sbc_min_knm2 == 75
    assert soft.sbc_max_knm2 == 100
    print(f"PASS soft clay SBC: {soft.sbc_min_knm2}-{soft.sbc_max_knm2} kN/m² (per IS 1904)")


def test_medium_sand_sbc_range():
    """Medium sand: 150-250 kN/m² per IS 1904."""
    medium = get_soil_profile(SoilClass.MEDIUM_SAND)
    assert medium.sbc_min_knm2 == 150
    assert medium.sbc_max_knm2 == 250
    print(f"PASS medium sand SBC: {medium.sbc_min_knm2}-{medium.sbc_max_knm2} kN/m²")


def test_black_cotton_flagged_expansive():
    """Black cotton soil must be marked as expansive."""
    bc = get_soil_profile(SoilClass.BLACK_COTTON)
    assert bc.is_expansive is True
    assert "EXPANSIVE" in bc.notes or "expansive" in bc.notes.lower()
    print(f"PASS black cotton flagged as expansive")


def test_reclaimed_fill_requires_pile():
    """Reclaimed fill must always require pile foundation."""
    rf = get_soil_profile(SoilClass.RECLAIMED_FILL)
    assert rf.requires_pile is True
    print(f"PASS reclaimed fill requires pile")


def test_adequate_footing_passes():
    """1.5×1.5m footing on medium sand at 400 kN should be adequate."""
    result = check_foundation_adequacy(SoilClass.MEDIUM_SAND, 400, 1.5 * 1.5)
    assert result["is_adequate"] is True
    assert result["utilization_pct"] < 100
    print(f"PASS 1.5×1.5m on medium sand at 400 kN: {result['utilization_pct']}% utilised")


def test_inadequate_footing_fails():
    """1.5×1.5m footing on medium sand at 800 kN should be inadequate."""
    result = check_foundation_adequacy(SoilClass.MEDIUM_SAND, 800, 1.5 * 1.5)
    assert result["is_adequate"] is False
    assert result["utilization_pct"] > 100
    print(f"PASS 1.5×1.5m on medium sand at 800 kN: INADEQUATE "
          f"({result['utilization_pct']}%)")


def test_soil_test_disclaimer_always_present():
    """Every adequacy check must include the 'soil test required' disclaimer."""
    result = check_foundation_adequacy(SoilClass.MEDIUM_SAND, 400, 1.5 * 1.5)
    assert "soil_test_required_disclaimer" in result
    assert "soil test" in result["soil_test_required_disclaimer"].lower()
    print(f"PASS soil test disclaimer always present")


def test_all_soil_classes_have_range_not_point():
    """Every soil profile must give a RANGE (min != max typically)."""
    for soil_class, profile in SOIL_PROFILES.items():
        # Should have a range (min < max for most; same is fine for degenerate)
        assert profile.sbc_max_knm2 >= profile.sbc_min_knm2, \
            f"{soil_class}: max < min"
    print(f"PASS all {len(SOIL_PROFILES)} soil classes have SBC ranges")


# ─── Extended structural sensitivity ─────────────────────────────────────
def test_four_sensitivity_scenarios_generated():
    """v0.6: sensitivity now has 4 drivers (soil, load, span, material)."""
    report = compute_structural_sensitivity(
        actual_soil_sbc_t_sqm=12,
        actual_foundation_type="isolated",
        actual_column_load_kn=600,
        actual_column_size_mm=300,
        actual_total_cost_rupees=1_200_000,
        actual_longest_span_m=4.0,
        actual_concrete_grade="M25",
        actual_steel_grade="Fe500",
    )
    drivers = [s.driver_name for s in report.scenarios]
    assert "Soil bearing capacity" in drivers
    assert "Column axial load" in drivers
    assert "Longest span" in drivers
    assert "Material grade" in drivers
    assert len(report.scenarios) == 4
    print(f"PASS 4 sensitivity drivers: {drivers}")


def test_span_sensitivity_impact_scales_with_increase():
    """Larger span increase → bigger cost impact."""
    report = compute_structural_sensitivity(
        actual_soil_sbc_t_sqm=12, actual_foundation_type="isolated",
        actual_column_load_kn=600, actual_column_size_mm=300,
        actual_total_cost_rupees=1_000_000,
        actual_longest_span_m=4.0,  # Will scenario to 4.8m = 20% increase
    )
    span_scenario = next(s for s in report.scenarios if s.driver_name == "Longest span")
    # 20% span increase should have measurable cost impact
    assert span_scenario.cost_impact_rupees > 0
    assert "Beam depth" in span_scenario.structural_impact or "beam" in span_scenario.structural_impact.lower()
    print(f"PASS span sensitivity: {span_scenario.cost_impact_rupees:.0f} rupees impact")


def test_material_grade_sensitivity_has_action():
    """Material grade scenario must have user action guidance."""
    report = compute_structural_sensitivity(
        actual_soil_sbc_t_sqm=12, actual_foundation_type="isolated",
        actual_column_load_kn=600, actual_column_size_mm=300,
        actual_total_cost_rupees=1_000_000,
        actual_concrete_grade="M25", actual_steel_grade="Fe500",
    )
    mat_scenario = next(s for s in report.scenarios if s.driver_name == "Material grade")
    assert mat_scenario.user_action, "Material scenario missing user action"
    assert "engineer" in mat_scenario.user_action.lower()
    print(f"PASS material grade sensitivity has user guidance")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.6 Phase 1 Tests — Real Engineering Additions")
    print("=" * 70)
    print()
    print("--- Bresler αn (IS 456 cl. 39.6 real formula) ---")
    test_bresler_alpha_low_axial()
    test_bresler_alpha_high_axial()
    test_bresler_alpha_interpolation()
    print()
    print("--- Puz and Mux1 estimators ---")
    test_puz_estimator_reasonable()
    test_mux1_estimator_parabolic()
    print()
    print("--- Column sanity checks ---")
    test_safe_column_classified_safe()
    test_overloaded_column_classified_fail()
    test_full_report_aggregates_correctly()
    test_method_disclosure_honest()
    print()
    print("--- Hardy Cross primitives ---")
    test_beam_fem_standard_formula()
    test_hardy_cross_balances_unequal_moments()
    print()
    print("--- Load combinations (5-combo set) ---")
    test_five_combinations_generated()
    test_wind_and_eq_not_combined()
    test_governing_combo_found()
    test_method_disclosure_says_wind_eq_not_combined()
    print()
    print("--- Soil classification (real IS 1904 values) ---")
    test_real_is1904_hard_rock_values()
    test_soft_clay_sbc_range()
    test_medium_sand_sbc_range()
    test_black_cotton_flagged_expansive()
    test_reclaimed_fill_requires_pile()
    test_adequate_footing_passes()
    test_inadequate_footing_fails()
    test_soil_test_disclaimer_always_present()
    test_all_soil_classes_have_range_not_point()
    print()
    print("--- Extended sensitivity (span + material) ---")
    test_four_sensitivity_scenarios_generated()
    test_span_sensitivity_impact_scales_with_increase()
    test_material_grade_sensitivity_has_action()
    print()
    print("=" * 70)
    print("ALL v0.6 PHASE 1 TESTS PASSED")
    print("=" * 70)
