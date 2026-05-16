"""
v0.7 tests — comprehensive coverage of all 6 Drawbacks from the v0.6 review.

Sections:
  A. Drawback 1 — Global stability / drift check
  B. Drawback 2 — Rich domain methods (Building)
  C. Drawback 3 — Load rules migration + parity
  D. Drawback 4 — Legal compact mode
  E. Drawback 5 — Action-layer recommendations
  F. Drawback 6 — Insights aggregation
  G. Orchestrator integration verification
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────────
# A. Drawback 1 — Global stability / drift check
# ─────────────────────────────────────────────────────────────────────────
def test_concrete_modulus_matches_IS456():
    """IS 456 cl. 6.2.3.1: E_c = 5000 × sqrt(fck). M25 → 25000 MPa."""
    from buildemup.components.c07.global_stability import concrete_modulus_mpa
    assert abs(concrete_modulus_mpa(25) - 25000) < 1
    assert abs(concrete_modulus_mpa(30) - 27386) < 1
    print("PASS E_c matches IS 456 cl. 6.2.3.1 (M25=25000, M30=27386 MPa)")


def test_cracked_section_factor_is_0_7_per_IS1893():
    """IS 1893:2016 cl. 6.4.3: Ie_col = 0.7 × Igross."""
    from buildemup.components.c07 import global_stability as gs
    assert gs.CRACKED_SECTION_FACTOR_COLUMN == 0.70
    assert gs.CRACKED_SECTION_FACTOR_BEAM == 0.35
    print("PASS cracked section factors match IS 1893:2016 cl. 6.4.3")


def test_drift_limit_matches_IS1893():
    """IS 1893:2016 cl. 7.11.1.1: drift ≤ 0.004h."""
    from buildemup.components.c07 import global_stability as gs
    assert gs.SEISMIC_DRIFT_RATIO_LIMIT == 0.004
    print("PASS seismic drift limit = 0.004h per IS 1893:2016 cl. 7.11.1.1")


def test_wind_sway_limit_matches_IS456():
    """IS 456:2000 serviceability: lateral sway ≤ H/500."""
    from buildemup.components.c07 import global_stability as gs
    assert gs.WIND_TOTAL_SWAY_LIMIT_RATIO == 1.0 / 500.0
    print("PASS wind sway limit = H/500 per IS 456 serviceability")


def test_column_stiffness_formula():
    """k = 12·E·Ie / h³ for fixed-fixed column."""
    from buildemup.components.c07.global_stability import (
        column_lateral_stiffness_kn_per_m,
    )
    # 300mm M25 column, 3m storey
    # E = 25000 MPa, I_gross = 300^4 / 12 = 675e6 mm^4
    # Ie = 0.7 × 675e6 = 472.5e6 mm^4
    # k = 12 × 25000 × 472.5e6 / (3000)^3 = 5250 N/mm = 5250 kN/m
    k = column_lateral_stiffness_kn_per_m(300, 3.0, 25.0)
    assert 5000 < k < 5500, f"Expected ~5250 kN/m, got {k}"
    print(f"PASS 300mm M25 column stiffness = {k:.0f} kN/m (expected ~5250)")


def test_well_sized_building_is_safe():
    """G+1 residential with 300mm columns = SAFE."""
    from buildemup.components.c07.global_stability import (
        run_global_stability_check, LoadCase, DriftCheckResult,
    )
    report = run_global_stability_check(
        n_storeys=2, storey_height_m=3.0,
        n_columns_per_storey=12, column_dim_mm=300, fck_mpa=25,
        total_base_shear_kn=150, load_case=LoadCase.SEISMIC,
    )
    assert report.overall_result == DriftCheckResult.SAFE
    print(f"PASS G+1 well-sized = SAFE (util {report.worst_utilization_pct}%)")


def test_undersized_tall_building_fails():
    """G+3 with 230mm columns in Zone IV lateral = FAIL."""
    from buildemup.components.c07.global_stability import (
        run_global_stability_check, LoadCase, DriftCheckResult,
    )
    report = run_global_stability_check(
        n_storeys=4, storey_height_m=3.2,
        n_columns_per_storey=9, column_dim_mm=230, fck_mpa=25,
        total_base_shear_kn=900, load_case=LoadCase.SEISMIC,
    )
    assert report.overall_result == DriftCheckResult.FAIL
    # Worst storey should be the ground storey (highest shear)
    assert report.worst_storey == 1
    print(f"PASS undersized tall = FAIL (util {report.worst_utilization_pct}%)")


def test_method_disclosure_is_honest():
    """Global stability method disclosure must list what we DON'T do."""
    from buildemup.components.c07.global_stability import (
        run_global_stability_check, LoadCase,
    )
    report = run_global_stability_check(
        n_storeys=2, storey_height_m=3.0,
        n_columns_per_storey=12, column_dim_mm=300, fck_mpa=25,
        total_base_shear_kn=150, load_case=LoadCase.SEISMIC,
    )
    d = report.method_disclosure
    assert "NOT a dynamic" in d or "NOT a full" in d or "NOT a stiffness-matrix" in d
    assert "P-delta" in d
    assert "IS 1893" in d
    print("PASS method disclosure is honest about scope limitations")


def test_base_shear_estimator_matches_IS1893():
    """V_B = A_h × W per IS 1893 cl. 7.6.

    For Zone II, I=1.0, R=5.0, Sa/g=2.5:
      A_h = (0.10/2) × (1.0/5.0) × 2.5 = 0.025
      W = 6000 kN → V_B = 150 kN
    """
    from buildemup.components.c07.global_stability import estimate_base_shear_kn
    v_b = estimate_base_shear_kn(6000, "II")
    assert abs(v_b - 150) < 1, f"Expected 150, got {v_b}"
    # Zone IV heavier
    v_b_iv = estimate_base_shear_kn(6000, "IV")
    assert v_b_iv > v_b * 2, f"Zone IV should be > 2× Zone II: {v_b_iv} vs {v_b}"
    print(f"PASS base shear Zone II={v_b:.0f} kN, Zone IV={v_b_iv:.0f} kN")


# ─────────────────────────────────────────────────────────────────────────
# B. Drawback 2 — Rich domain methods on Building
# ─────────────────────────────────────────────────────────────────────────
def test_building_total_imposed_load_kn():
    """Building.total_imposed_load_kn() aggregates across all floors."""
    from buildemup.domain import (
        Building, BuildingMeta, Envelope, Floor, FloorType,
    )
    # 10×10 = 100 sqm plot, G+1 residential
    # Ground: 100 sqm × 2.0 kN/sqm = 200 kN
    # First:  100 sqm × 2.0 kN/sqm = 200 kN
    # Terrace: 100 sqm × 1.5 kN/sqm = 150 kN
    # Total = 550 kN
    b = Building(
        meta=BuildingMeta(),
        envelope=Envelope(width_m=10, depth_m=10),
        floors=(
            Floor(floor_number=0, floor_type=FloorType.GROUND),
            Floor(floor_number=1, floor_type=FloorType.FIRST),
            Floor(floor_number=2, floor_type=FloorType.TERRACE),
        ),
    )
    total = b.total_imposed_load_kn()
    assert abs(total - 550) < 1, f"Expected 550 kN, got {total}"
    print(f"PASS Building.total_imposed_load_kn() = {total} kN")


def test_building_validate_detects_severe_aspect_ratio():
    """validate_for_structural_analysis flags aspect > 6.0."""
    from buildemup.domain import (
        Building, BuildingMeta, Envelope, Floor, FloorType,
    )
    # Very long thin plot: 5m × 50m = aspect 10
    b = Building(
        meta=BuildingMeta(),
        envelope=Envelope(width_m=5, depth_m=50),
        floors=(Floor(floor_number=0, floor_type=FloorType.GROUND),),
    )
    issues = b.validate_for_structural_analysis()
    assert any("aspect ratio" in i.lower() for i in issues)
    print(f"PASS validate detects severe aspect ratio: {len(issues)} issue(s)")


def test_building_validate_clean_for_normal_building():
    """validate_for_structural_analysis returns [] for typical building."""
    from buildemup.domain import (
        Building, BuildingMeta, Envelope, Floor, FloorType,
    )
    b = Building(
        meta=BuildingMeta(),
        envelope=Envelope(width_m=8, depth_m=10),
        floors=(
            Floor(floor_number=0, floor_type=FloorType.GROUND),
            Floor(floor_number=1, floor_type=FloorType.FIRST),
        ),
    )
    issues = b.validate_for_structural_analysis()
    assert issues == [], f"Should be clean, got: {issues}"
    print("PASS validate returns [] for typical building")


# ─────────────────────────────────────────────────────────────────────────
# C. Drawback 3 — Load rules JSON migration + parity
# ─────────────────────────────────────────────────────────────────────────
def test_load_rules_loads_without_error():
    """load_rules('load_rules') succeeds with valid JSON."""
    from buildemup.utils.kb_rules_loader import load_rules, clear_cache
    clear_cache()
    data = load_rules("load_rules")
    assert "dead_load" in data
    assert "live_loads_by_floor_type" in data
    assert "partial_safety_factors" in data
    print("PASS load_rules.json loads cleanly")


def test_load_rules_parity_slab_weight():
    """JSON slab weight must match Python SLAB_WEIGHT_KN_PER_SQM_PER_MM."""
    from buildemup.utils.kb_rules_loader import get_slab_weight_kn_per_sqm_per_mm
    from buildemup.kb.load_estimation import SLAB_WEIGHT_KN_PER_SQM_PER_MM
    json_val = get_slab_weight_kn_per_sqm_per_mm()
    assert json_val == SLAB_WEIGHT_KN_PER_SQM_PER_MM, \
        f"JSON {json_val} != Python {SLAB_WEIGHT_KN_PER_SQM_PER_MM}"
    print(f"PASS parity: slab weight = {json_val}")


def test_load_rules_parity_finishes():
    """JSON finishes load must match Python FINISHES_KN_PER_SQM."""
    from buildemup.utils.kb_rules_loader import get_finishes_kn_per_sqm
    from buildemup.kb.load_estimation import FINISHES_KN_PER_SQM
    assert get_finishes_kn_per_sqm() == FINISHES_KN_PER_SQM
    print(f"PASS parity: finishes = {FINISHES_KN_PER_SQM} kN/sqm")


def test_load_rules_parity_live_loads_all_types():
    """Every floor type's live load in JSON matches Python LIVE_LOAD_KN_PER_SQM."""
    from buildemup.utils.kb_rules_loader import get_live_load_kn_per_sqm
    from buildemup.kb.load_estimation import LIVE_LOAD_KN_PER_SQM
    # LIVE_LOAD_KN_PER_SQM is keyed by FloorType enum
    for floor_type, py_val in LIVE_LOAD_KN_PER_SQM.items():
        json_val = get_live_load_kn_per_sqm(floor_type.name)
        assert json_val == py_val, \
            f"Floor type {floor_type.name}: JSON {json_val} != Python {py_val}"
    print(f"PASS parity: {len(LIVE_LOAD_KN_PER_SQM)} live loads match")


def test_load_rules_parity_safety_factors():
    """All partial safety factors match between JSON and Python."""
    from buildemup.utils.kb_rules_loader import get_partial_safety_factor
    from buildemup.kb.load_estimation import SAFETY_FACTORS
    for name, py_val in SAFETY_FACTORS.items():
        json_val = get_partial_safety_factor(name)
        assert json_val == py_val, \
            f"Safety factor {name}: JSON {json_val} != Python {py_val}"
    print(f"PASS parity: {len(SAFETY_FACTORS)} safety factors match")


def test_load_rules_parity_water_tank():
    """Water tank load values match between JSON and Python."""
    from buildemup.utils.kb_rules_loader import get_water_tank_load_kn
    from buildemup.kb.load_estimation import (
        OVERHEAD_WATER_TANK_LOAD_KN,
        OVERHEAD_WATER_TANK_AREA_SQM,
        OVERHEAD_WATER_TANK_DISTRIBUTED_KN_PER_SQM,
    )
    total, area, distributed = get_water_tank_load_kn()
    assert total == OVERHEAD_WATER_TANK_LOAD_KN
    assert area == OVERHEAD_WATER_TANK_AREA_SQM
    assert distributed == OVERHEAD_WATER_TANK_DISTRIBUTED_KN_PER_SQM
    print(f"PASS parity: water tank values match "
          f"({total} kN / {area} sqm / {distributed} kN/sqm)")


def test_load_rules_parity_wall_loads():
    """Wall load values 230mm and 115mm match between JSON and Python."""
    from buildemup.utils.kb_rules_loader import get_wall_load_kn_per_m
    from buildemup.kb.load_estimation import (
        WALL_LOAD_230MM_KN_PER_M, WALL_LOAD_115MM_KN_PER_M,
    )
    assert get_wall_load_kn_per_m(230) == WALL_LOAD_230MM_KN_PER_M
    assert get_wall_load_kn_per_m(115) == WALL_LOAD_115MM_KN_PER_M
    print("PASS parity: wall loads 230mm + 115mm match")


def test_load_rules_schema_rejects_negative_safety_factor():
    """Safety factor < 1.0 must be rejected."""
    from buildemup.utils import kb_rules_loader as loader
    # Build minimal bad data with a < 1.0 safety factor
    bad = {
        "dead_load": {"values": {
            "slab_weight_kn_per_sqm_per_mm": 0.025,
            "finishes_kn_per_sqm": 1.2,
            "partition_wall_kn_per_sqm": 1.0,
        }},
        "live_loads_by_floor_type": {"values": {
            "STILT_PARKING": 4.0, "RESIDENTIAL": 2.0,
            "TERRACE_ACCESSIBLE": 3.0, "TERRACE_INACCESSIBLE": 1.5,
            "BALCONY": 3.0, "STAIRCASE": 4.0,
        }},
        "concentrated_loads": {"overhead_water_tank": {
            "total_load_kn": 50, "footprint_sqm": 4.0,
            "distributed_kn_per_sqm": 12.5,
        }},
        "wall_loads": {"values": {
            "brick_230mm_3m_height_kn_per_m": 13.8,
            "brick_115mm_3m_height_kn_per_m": 6.9,
        }},
        "partial_safety_factors": {"values": {
            "dead_load": 0.9,   # BAD: < 1.0
            "live_load": 1.5, "concrete_material": 1.5,
            "steel_material": 1.15, "seismic_combination": 1.2,
        }},
    }
    try:
        loader._validate_load_rules(bad)
        assert False, "Expected RuleSchemaError"
    except loader.RuleSchemaError as e:
        assert "must be ≥ 1.0" in str(e) or "safety factor" in str(e).lower()
        print(f"PASS schema rejects negative safety factor: {e.reason[:50]}")


# ─────────────────────────────────────────────────────────────────────────
# D. Drawback 4 — Legal compact mode
# ─────────────────────────────────────────────────────────────────────────
def test_legal_full_mode_default_has_all_six_sections():
    """Default full mode preserves all 6 sections."""
    from buildemup.utils.legal_disclosures import format_legal_disclosures_block
    block = format_legal_disclosures_block()
    for section in ("STRUCTURAL ENGINEER REQUIRED", "MUNICIPAL PERMIT",
                    "NO ENGINEER VERIFICATION", "LIMITATION OF LIABILITY",
                    "DATA HANDLING", "PRELIMINARY SOIL"):
        assert section in block, f"Missing section: {section}"
    print("PASS full mode has all 6 sections")


def test_legal_compact_mode_is_shorter():
    """Compact mode is strictly shorter than full mode."""
    from buildemup.utils.legal_disclosures import format_legal_disclosures_block
    full = format_legal_disclosures_block(mode="full")
    compact = format_legal_disclosures_block(mode="compact")
    assert len(compact) < len(full) * 0.6, \
        f"Compact {len(compact)} should be much shorter than full {len(full)}"
    print(f"PASS compact is shorter ({len(compact)} vs {len(full)} chars)")


def test_legal_compact_retains_critical_points():
    """Compact mode still mentions: engineer required, no endorsement, not a stamped plan."""
    from buildemup.utils.legal_disclosures import format_legal_disclosures_block
    compact = format_legal_disclosures_block(mode="compact")
    assert "NOT a stamped plan" in compact
    assert "NOT verify or endorse" in compact or "not verify" in compact.lower()
    # Must point to full text
    assert "full" in compact.lower()
    print("PASS compact retains critical legal points")


def test_legal_full_mode_default_unchanged_from_v06():
    """v0.7 default must match v0.6 behaviour exactly (no breaking change)."""
    from buildemup.utils.legal_disclosures import format_legal_disclosures_block
    # Calling without mode argument must work (back-compat)
    default = format_legal_disclosures_block()
    explicit_full = format_legal_disclosures_block(mode="full")
    assert default == explicit_full, "Default and explicit 'full' must be identical"
    print("PASS default mode = full mode (v0.6 back-compat)")


# ─────────────────────────────────────────────────────────────────────────
# E. Drawback 5 — Action-layer recommendations
# ─────────────────────────────────────────────────────────────────────────
def test_recommendation_dataclass_fields():
    """Recommendation has all required fields."""
    from buildemup.utils.structural_sensitivity import Recommendation
    r = Recommendation(
        action_verb="Keep", action_text="span under 4m",
        threshold_basis="beam depth jump", priority="IMPORTANT",
    )
    assert r.action_verb == "Keep"
    assert r.priority == "IMPORTANT"
    print("PASS Recommendation dataclass structure correct")


def test_every_sensitivity_scenario_has_recommendation():
    """All 4 drivers' scenarios must have a recommendation attached."""
    from buildemup.utils.structural_sensitivity import (
        compute_structural_sensitivity,
    )
    report = compute_structural_sensitivity(
        actual_soil_sbc_t_sqm=10, actual_foundation_type="isolated",
        actual_column_load_kn=500, actual_column_size_mm=300,
        actual_total_cost_rupees=1_500_000,
        actual_longest_span_m=3.8,
    )
    for scenario in report.scenarios:
        assert scenario.recommendation is not None, \
            f"Scenario '{scenario.driver_name}' has no recommendation"
    print(f"PASS all {len(report.scenarios)} scenarios have recommendations")


def test_weak_soil_triggers_critical_recommendation():
    """SBC < 6 T/sqm must trigger CRITICAL priority soil test recommendation."""
    from buildemup.utils.structural_sensitivity import (
        compute_structural_sensitivity,
    )
    # actual_sbc = 8, weaker = 8 × 0.7 = 5.6 → below 6 threshold
    report = compute_structural_sensitivity(
        actual_soil_sbc_t_sqm=8, actual_foundation_type="isolated",
        actual_column_load_kn=500, actual_column_size_mm=300,
        actual_total_cost_rupees=2_000_000,
    )
    soil_scenario = next(s for s in report.scenarios
                         if s.driver_name == "Soil bearing capacity")
    assert soil_scenario.recommendation.priority == "CRITICAL"
    assert "soil test" in soil_scenario.recommendation.action_text.lower()
    print(f"PASS weak soil → [CRITICAL] recommendation")


def test_span_crossing_4m_threshold_triggers_recommendation():
    """Span 3.8 → 4.56 crosses 4.0m boundary, triggers IMPORTANT recommendation."""
    from buildemup.utils.structural_sensitivity import (
        compute_structural_sensitivity,
    )
    report = compute_structural_sensitivity(
        actual_soil_sbc_t_sqm=12, actual_foundation_type="isolated",
        actual_column_load_kn=500, actual_column_size_mm=300,
        actual_total_cost_rupees=1_500_000,
        actual_longest_span_m=3.8,  # +20% scenario = 4.56m, crosses 4.0m
    )
    span_scenario = next(s for s in report.scenarios
                         if s.driver_name == "Longest span")
    assert span_scenario.recommendation is not None
    # Text should mention the 4m threshold
    text = span_scenario.recommendation.action_text.lower()
    assert "4" in text or "span" in text
    print(f"PASS span crossing 4m → recommendation: "
          f"{span_scenario.recommendation.priority}")


def test_top_recommendations_sorted_by_priority():
    """top_recommendations returns CRITICAL first, then IMPORTANT, then OPTIONAL."""
    from buildemup.utils.structural_sensitivity import (
        compute_structural_sensitivity,
    )
    report = compute_structural_sensitivity(
        actual_soil_sbc_t_sqm=8, actual_foundation_type="isolated",
        actual_column_load_kn=500, actual_column_size_mm=300,
        actual_total_cost_rupees=2_000_000,
        actual_longest_span_m=3.8,
    )
    recs = report.top_recommendations
    priorities = [r.priority for r in recs]
    # Must be in order: CRITICAL → IMPORTANT → OPTIONAL
    order = {"CRITICAL": 0, "IMPORTANT": 1, "OPTIONAL": 2}
    prio_indices = [order[p] for p in priorities]
    assert prio_indices == sorted(prio_indices), \
        f"Not sorted by priority: {priorities}"
    print(f"PASS recommendations sorted by priority: {priorities}")


def test_format_recommendations_only_view():
    """format_recommendations_only produces a compact view."""
    from buildemup.utils.structural_sensitivity import (
        compute_structural_sensitivity,
    )
    report = compute_structural_sensitivity(
        actual_soil_sbc_t_sqm=10, actual_foundation_type="isolated",
        actual_column_load_kn=500, actual_column_size_mm=300,
        actual_total_cost_rupees=1_500_000,
    )
    text = report.format_recommendations_only()
    assert "TOP RECOMMENDATIONS" in text
    assert "CRITICAL" in text or "IMPORTANT" in text or "OPTIONAL" in text
    assert "Why:" in text
    print("PASS format_recommendations_only produces compact view")


# ─────────────────────────────────────────────────────────────────────────
# F. Drawback 6 — Insights aggregation
# ─────────────────────────────────────────────────────────────────────────
def test_aggregate_empty_logs_returns_zero_report():
    """Aggregating empty logs returns an empty but valid report."""
    from buildemup.utils.insights import aggregate_logs
    report = aggregate_logs([])
    assert report.total_executions == 0
    print("PASS empty logs → zero-valued report")


def test_aggregate_counts_executions():
    """Successful + refused + errored executions counted correctly."""
    from buildemup.utils.insights import aggregate_logs
    entries = [
        {"event": "execute_complete", "timestamp": "2026-04-01T10:00:00", "cost": 1500000},
        {"event": "execute_complete", "timestamp": "2026-04-01T11:00:00", "cost": 1200000},
        {"event": "execute_refused", "timestamp": "2026-04-01T12:00:00", "reason": "severe_irregularity"},
        {"event": "execute_errored", "timestamp": "2026-04-01T13:00:00"},
    ]
    report = aggregate_logs(entries)
    assert report.total_executions == 4
    assert report.successful_executions == 2
    assert report.refused_executions == 1
    assert report.errored_executions == 1
    print(f"PASS execution counts: {report.total_executions} total, "
          f"{report.successful_executions} success")


def test_aggregate_cost_distribution():
    """Cost distribution computes min/p25/p50/p75/max correctly."""
    from buildemup.utils.insights import aggregate_logs
    entries = [
        {"event": "execute_complete", "timestamp": "2026-04-01", "cost": c}
        for c in [1_000_000, 1_200_000, 1_500_000, 1_800_000, 2_000_000]
    ]
    report = aggregate_logs(entries)
    cd = report.cost_distribution
    assert cd["min"] == 1_000_000
    assert cd["max"] == 2_000_000
    assert cd["p50"] == 1_500_000
    print(f"PASS cost distribution: min={cd['min']}, median={cd['p50']}, max={cd['max']}")


def test_aggregate_top_warnings():
    """Most frequent warnings ranked correctly."""
    from buildemup.utils.insights import aggregate_logs
    entries = [
        {"event": "execute_complete", "timestamp": "2026-04-01", "warnings": ["Soil test recommended"]},
        {"event": "execute_complete", "timestamp": "2026-04-02", "warnings": ["Soil test recommended"]},
        {"event": "execute_complete", "timestamp": "2026-04-03", "warnings": ["Soil test recommended", "Zone IV confined"]},
        {"event": "execute_complete", "timestamp": "2026-04-04", "warnings": ["Zone IV confined"]},
    ]
    report = aggregate_logs(entries)
    top = report.top_warnings
    # Soil test = 3 occurrences, Zone IV = 2 occurrences
    assert top[0][0].startswith("Soil test")
    assert top[0][1] == 3
    print(f"PASS top warnings ranked: {top[0][0][:30]}... = {top[0][1]}×")


def test_insights_report_format_text():
    """format_text produces multi-line report string."""
    from buildemup.utils.insights import aggregate_logs
    entries = [
        {"event": "execute_complete", "timestamp": "2026-04-01", "cost": 1500000, "city": "chennai"},
        {"event": "execute_complete", "timestamp": "2026-04-02", "cost": 1800000, "city": "bangalore"},
    ]
    report = aggregate_logs(entries)
    text = report.format_text()
    assert "BuildemUp Weekly Insights" in text
    assert "Total executions:" in text
    assert "2026-04-01" in text
    print("PASS insights report format_text produces valid output")


def test_insights_csv_export():
    """to_csv_rows returns header + data rows."""
    from buildemup.utils.insights import aggregate_logs
    entries = [
        {"event": "execute_complete", "timestamp": "2026-04-01", "cost": 1500000, "city": "chennai"},
    ]
    report = aggregate_logs(entries)
    rows = report.to_csv_rows()
    assert rows[0] == ("metric", "value")
    assert len(rows) > 5
    print(f"PASS CSV export: {len(rows)} rows")


# ─────────────────────────────────────────────────────────────────────────
# G. Orchestrator integration
# ─────────────────────────────────────────────────────────────────────────
def test_orchestrator_populates_global_stability():
    """Component 7 output has global_stability populated for every run."""
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    inp = StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    )
    result = StructuralGridEngine().execute(inp)
    assert result.global_stability is not None
    assert result.global_stability.overall_result.value in (
        "SAFE", "WARNING", "FAIL",
    )
    print(f"PASS global_stability populated: "
          f"{result.global_stability.overall_result.value}")


def test_orchestrator_explain_shows_global_stability_section():
    """explain() has GLOBAL STABILITY section."""
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    inp = StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "GLOBAL STABILITY" in explanation
    assert "IS 1893" in explanation
    print("PASS explain() shows GLOBAL STABILITY section")


def test_orchestrator_explain_shows_top_recommendations_section():
    """explain() has TOP RECOMMENDATIONS section."""
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    inp = StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "TOP RECOMMENDATIONS" in explanation
    assert ("CRITICAL" in explanation or "IMPORTANT" in explanation
            or "OPTIONAL" in explanation)
    print("PASS explain() shows TOP RECOMMENDATIONS section")


def test_orchestrator_does_not_regress_v06_features():
    """All v0.6 features still work in v0.7 output."""
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    inp = StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    )
    result = StructuralGridEngine().execute(inp)
    # All v0.6 fields still populated
    assert "PENDING ENGINEER VALIDATION" in result.validation_status
    assert result.engineering_depth is not None
    assert result.frame_sanity is not None
    assert result.freshness_action in ("OK", "WARN_DEGRADE_CONFIDENCE", "BLOCK_STALE")
    print("PASS v0.6 features preserved in v0.7")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.7 Tests — 6 Drawbacks from v0.6 Review")
    print("=" * 70)
    print()
    print("--- A. Drawback 1: Global stability / drift check ---")
    test_concrete_modulus_matches_IS456()
    test_cracked_section_factor_is_0_7_per_IS1893()
    test_drift_limit_matches_IS1893()
    test_wind_sway_limit_matches_IS456()
    test_column_stiffness_formula()
    test_well_sized_building_is_safe()
    test_undersized_tall_building_fails()
    test_method_disclosure_is_honest()
    test_base_shear_estimator_matches_IS1893()
    print()
    print("--- B. Drawback 2: Rich domain methods ---")
    test_building_total_imposed_load_kn()
    test_building_validate_detects_severe_aspect_ratio()
    test_building_validate_clean_for_normal_building()
    print()
    print("--- C. Drawback 3: Load rules migration + parity ---")
    test_load_rules_loads_without_error()
    test_load_rules_parity_slab_weight()
    test_load_rules_parity_finishes()
    test_load_rules_parity_live_loads_all_types()
    test_load_rules_parity_safety_factors()
    test_load_rules_parity_water_tank()
    test_load_rules_parity_wall_loads()
    test_load_rules_schema_rejects_negative_safety_factor()
    print()
    print("--- D. Drawback 4: Legal compact mode ---")
    test_legal_full_mode_default_has_all_six_sections()
    test_legal_compact_mode_is_shorter()
    test_legal_compact_retains_critical_points()
    test_legal_full_mode_default_unchanged_from_v06()
    print()
    print("--- E. Drawback 5: Action-layer recommendations ---")
    test_recommendation_dataclass_fields()
    test_every_sensitivity_scenario_has_recommendation()
    test_weak_soil_triggers_critical_recommendation()
    test_span_crossing_4m_threshold_triggers_recommendation()
    test_top_recommendations_sorted_by_priority()
    test_format_recommendations_only_view()
    print()
    print("--- F. Drawback 6: Insights aggregation ---")
    test_aggregate_empty_logs_returns_zero_report()
    test_aggregate_counts_executions()
    test_aggregate_cost_distribution()
    test_aggregate_top_warnings()
    test_insights_report_format_text()
    test_insights_csv_export()
    print()
    print("--- G. Orchestrator integration ---")
    test_orchestrator_populates_global_stability()
    test_orchestrator_explain_shows_global_stability_section()
    test_orchestrator_explain_shows_top_recommendations_section()
    test_orchestrator_does_not_regress_v06_features()
    print()
    print("=" * 70)
    print("ALL v0.7 TESTS PASSED")
    print("=" * 70)
