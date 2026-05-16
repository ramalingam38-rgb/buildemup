"""
v0.1 Session 2 tests — Setback Calculator + KB JSON parity.

Covers SPEC_v0.2 Section 13-B (setback calculation, ~10 tests).
Also includes parity tests between JSON and Python domain constants.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────────
# B. Setback calculation (~10 tests per SPEC_v0.2 Section 13)
# ─────────────────────────────────────────────────────────────────────────

def test_chennai_detached_small_plot():
    """Chennai 50-150 sqm detached → TNCDBR small-plot tier."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0, plot_type=PlotType.DETACHED)
    # 108 sqm → 50-150 tier: 0.9 / 0.7 / 0.7 / 0.0
    s, auth = compute_compliant_setbacks(p)
    assert s.front_m == 0.9
    assert s.rear_m == 0.7
    assert auth == "TNCDBR 2019 (CMDA)"
    print(f"PASS Chennai small plot 108 sqm → {s.describe()}")


def test_chennai_detached_medium_plot():
    """Chennai 150-300 sqm detached → full 4-side 1.5m."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=18.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=9.0, plot_type=PlotType.DETACHED)
    # 216 sqm → 150-300 tier: 1.5 all sides
    s, _ = compute_compliant_setbacks(p)
    assert s.front_m == 1.5
    assert s.rear_m == 1.5
    assert s.side_left_m == 1.5
    assert s.side_right_m == 1.5
    print(f"PASS Chennai medium plot 216 sqm → all-sides 1.5m")


def test_chennai_detached_large_plot_high_building():
    """Chennai >300 sqm, G+3 → larger setbacks."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=20.0, depth_m=20.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=12.0, plot_type=PlotType.DETACHED)
    # 400 sqm with G+3 (12m height) → large-plot high tier: 3.0/2.0/2.0/2.0
    s, _ = compute_compliant_setbacks(p, building_height_m=12.0)
    assert s.front_m == 3.0
    assert s.rear_m == 2.0
    print(f"PASS Chennai large plot G+3 → {s.describe()}")


def test_chennai_continuous_zero_side_setbacks():
    """Chennai CONTINUOUS → sides = 0, front + rear only."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=6.0, depth_m=15.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=6.0, plot_type=PlotType.CONTINUOUS)
    s, _ = compute_compliant_setbacks(p)
    assert s.side_left_m == 0.0
    assert s.side_right_m == 0.0
    assert s.front_m == 0.9        # 6m road → 3.0-7.0 bucket
    assert s.rear_m == 1.0         # TNCDBR CBA rule
    print(f"PASS Chennai CONTINUOUS → sides=0, front={s.front_m}, rear={s.rear_m}")


def test_chennai_continuous_front_scales_with_road():
    """Chennai CONTINUOUS front setback varies by road width bucket."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    # Road 4m → 3.0-7.0 bucket → 0.9m front
    p1 = Plot(width_m=6.0, depth_m=12.0, facing=PlotOrientation.NORTH,
              city="chennai", road_width_m=4.0, plot_type=PlotType.CONTINUOUS)
    s1, _ = compute_compliant_setbacks(p1)
    assert s1.front_m == 0.9

    # Road 10m → 7.0-12.0 bucket → 1.5m front
    p2 = Plot(width_m=6.0, depth_m=12.0, facing=PlotOrientation.NORTH,
              city="chennai", road_width_m=10.0, plot_type=PlotType.CONTINUOUS)
    s2, _ = compute_compliant_setbacks(p2)
    assert s2.front_m == 1.5

    # Road 15m → 12+ bucket → 3.0m front
    p3 = Plot(width_m=6.0, depth_m=12.0, facing=PlotOrientation.NORTH,
              city="chennai", road_width_m=15.0, plot_type=PlotType.CONTINUOUS)
    s3, _ = compute_compliant_setbacks(p3)
    assert s3.front_m == 3.0
    print(f"PASS CONTINUOUS front scales with road: 4m→{s1.front_m}, "
          f"10m→{s2.front_m}, 15m→{s3.front_m}")


def test_semi_detached_zeros_shared_side_only():
    """SEMI_DETACHED → 3 sides per DETACHED, shared side = 0."""
    from buildemup.domain import Plot, PlotType, SharedSide, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    # Shared LEFT
    p_left = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
                  city="chennai", road_width_m=9.0,
                  plot_type=PlotType.SEMI_DETACHED,
                  shared_side=SharedSide.LEFT)
    s_left, _ = compute_compliant_setbacks(p_left)
    assert s_left.side_left_m == 0.0
    # Right side gets whatever the base DETACHED tier said
    # (for 108 sqm, DETACHED tier has side_right_m=0.0 too — coincidence
    # but test it anyway against the DETACHED baseline)

    # Shared RIGHT
    p_right = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
                   city="chennai", road_width_m=9.0,
                   plot_type=PlotType.SEMI_DETACHED,
                   shared_side=SharedSide.RIGHT)
    s_right, _ = compute_compliant_setbacks(p_right)
    assert s_right.side_right_m == 0.0
    print(f"PASS SEMI_DETACHED zeros shared side "
          f"(LEFT shared: L={s_left.side_left_m}; "
          f"RIGHT shared: R={s_right.side_right_m})")


def test_mumbai_and_delhi_use_real_dcr_v09():
    """Mumbai uses DCPR 2034, Delhi uses MPD-2021 (added in v0.9 Session C)."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    # Mumbai 9×12 plot (108 sqm) on 9m road = small plot tier, suburbs
    p = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="mumbai", road_width_m=9.0, plot_type=PlotType.DETACHED)
    s, auth = compute_compliant_setbacks(p)
    assert "DCPR 2034" in auth, f"Expected DCPR 2034, got: {auth}"
    assert s.front_m == 4.5, f"Mumbai 9m road → 4.5m front, got {s.front_m}"
    assert s.side_left_m == 1.5

    # Delhi 9×12 plot (108 sqm) → 100-250 sqm tier (row housing)
    p = Plot(width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="delhi", road_width_m=9.0, plot_type=PlotType.DETACHED)
    s, auth = compute_compliant_setbacks(p)
    assert "MPD-2021" in auth, f"Expected MPD-2021, got: {auth}"
    assert s.front_m == 3.0
    # Row housing pattern at 100-250 sqm: no side setbacks
    assert s.side_left_m == 0.0
    assert s.side_right_m == 0.0
    print("PASS Mumbai uses DCPR 2034, Delhi uses MPD-2021")


def test_all_6_cities_use_real_dcr_after_session_d():
    """v0.9 Session D: ALL 6 launch cities now have real DCRs (not NBC fallback).

    - Chennai: TNCDBR 2019 (CMDA) [v0.1]
    - Mumbai: DCPR 2034 (MCGM) [v0.9 Session C]
    - Delhi: MPD-2021 + UBBL 2016 (DDA) [v0.9 Session C]
    - Bangalore: BBMP / Karnataka UDD [v0.9 Session D]
    - Pune: UDCPR Maharashtra (2020) / PMC [v0.9 Session D]
    - Hyderabad: Telangana G.O. Ms. 168 (GHMC/HMDA) [v0.9 Session D]
    """
    from buildemup.utils.kb_rules_loader import (
        get_setback_authority_for_city,
    )
    expected_authority_substring = {
        "chennai":   "TNCDBR",
        "mumbai":    "DCPR 2034",
        "delhi":     "MPD-2021",
        "bangalore": "BBMP",
        "pune":      "UDCPR",
        "hyderabad": "G.O. Ms. 168",
    }
    for city, expected in expected_authority_substring.items():
        auth = get_setback_authority_for_city(city)
        assert "NBC" not in auth, (
            f"{city} still uses NBC fallback: {auth}"
        )
        assert expected in auth, (
            f"{city} authority should contain '{expected}', got: {auth}"
        )
    print("PASS all 6 launch cities have real DCRs (no NBC fallback for any)")


def test_compliance_check_flags_all_violating_sides():
    """check_setback_compliance reports every side that's violating."""
    from buildemup.domain import Setbacks
    from buildemup.components.c01.setback_calculator import (
        check_setback_compliance,
    )
    # User stated too-small on all 4 sides
    user = Setbacks(1.0, 1.0, 1.0, 1.0)
    nbc = Setbacks(1.5, 1.5, 1.5, 1.5)
    ok, violations = check_setback_compliance(user, nbc)
    assert ok is False
    assert len(violations) == 4  # all 4 sides
    print(f"PASS compliance check flags all 4 violating sides")


def test_compliance_check_passes_when_compliant():
    """Compliant user stated setbacks → no violations."""
    from buildemup.domain import Setbacks
    from buildemup.components.c01.setback_calculator import (
        check_setback_compliance,
    )
    user = Setbacks(2.0, 2.0, 2.0, 2.0)   # generous
    nbc = Setbacks(1.5, 1.5, 1.5, 1.5)
    ok, violations = check_setback_compliance(user, nbc)
    assert ok is True
    assert len(violations) == 0
    print(f"PASS compliance check passes with generous setbacks")


def test_compliance_check_flags_only_one_side():
    """User violates only one side → only one violation reported."""
    from buildemup.domain import Setbacks
    from buildemup.components.c01.setback_calculator import (
        check_setback_compliance,
    )
    user = Setbacks(1.5, 1.5, 1.0, 1.5)    # left side violated only
    nbc = Setbacks(1.5, 1.5, 1.5, 1.5)
    ok, violations = check_setback_compliance(user, nbc)
    assert ok is False
    assert len(violations) == 1
    assert "Left" in violations[0]
    assert "0.5m below" in violations[0]
    print(f"PASS only the violating side is reported")


def test_corner_plot_uses_wider_road():
    """Corner plot with 2 roads → CONTINUOUS front setback uses wider road."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    # 6m primary road + 15m secondary road → wider = 15m → 3.0 bucket
    p = Plot(width_m=6.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=6.0, plot_type=PlotType.CONTINUOUS,
             corner_plot=True, second_road_width_m=15.0)
    s, _ = compute_compliant_setbacks(p)
    assert s.front_m == 3.0  # uses 15m road (the wider)
    print(f"PASS corner plot uses wider road for front setback")


# ─────────────────────────────────────────────────────────────────────────
# KB Parity tests (JSON ↔ Python)
# ─────────────────────────────────────────────────────────────────────────

def test_room_minimums_json_matches_python_constants():
    """NBC_MINIMUM_ROOM_SIZES_SQM in Python must match room_minimums.json."""
    from buildemup.domain import NBC_MINIMUM_ROOM_SIZES_SQM, RoomType
    from buildemup.utils.kb_rules_loader import get_room_minimum_sqm
    for room_type, py_value in NBC_MINIMUM_ROOM_SIZES_SQM.items():
        json_value = get_room_minimum_sqm(room_type.name)
        assert py_value == json_value, \
            f"{room_type.name}: Python {py_value} != JSON {json_value}"
    print(f"PASS parity: {len(NBC_MINIMUM_ROOM_SIZES_SQM)} "
          f"NBC room minimums match")


def test_setback_rules_loads_with_all_cities():
    """setback_rules.json loads + has chennai + _fallback_nbc."""
    from buildemup.utils.kb_rules_loader import load_rules
    rules = load_rules("setback_rules")
    assert "chennai" in rules
    assert "_fallback_nbc" in rules
    # Each must have all 3 plot types
    for city in ["chennai", "_fallback_nbc"]:
        for pt in ["detached", "semi_detached", "continuous"]:
            assert pt in rules[city], f"Missing {city}.{pt}"
    print("PASS setback_rules.json has chennai + fallback, all 3 plot types")


def test_circulation_factor_is_1_35():
    """circulation_factor default = 1.35 per v0.9 IS 3861-2002 research.

    Walls (5-10%) + horizontal circulation (10-15%) + vertical
    circulation (4-5%) = ~30-35% overhead. Default = 1.35.
    """
    from buildemup.utils.kb_rules_loader import get_circulation_factor
    cf = get_circulation_factor()
    assert cf == 1.35, f"Expected 1.35, got {cf}"
    print(f"PASS circulation_factor default = {cf} "
          f"(per IS 3861-2002 research)")


def test_circulation_factor_size_aware():
    """v0.9: factor varies by per-floor room area."""
    from buildemup.utils.kb_rules_loader import get_circulation_factor_for_size
    # Small home (< 30 sqm/floor)
    factor, label = get_circulation_factor_for_size(15.0)
    assert factor == 1.40
    assert label == "small"
    # Typical (30-100 sqm/floor)
    factor, label = get_circulation_factor_for_size(50.0)
    assert factor == 1.35
    assert label == "typical"
    # Large home (> 100 sqm/floor)
    factor, label = get_circulation_factor_for_size(150.0)
    assert factor == 1.30
    assert label == "large"
    # Boundaries fall into typical
    assert get_circulation_factor_for_size(30.0)[1] == "typical"
    assert get_circulation_factor_for_size(100.0)[1] == "typical"
    print("PASS circulation factor size-aware: small=1.40, "
          "typical=1.35, large=1.30")


def test_setback_schema_rejects_bad_data():
    """_validate_setback_rules catches malformed schemas."""
    from buildemup.utils import kb_rules_loader as loader
    # Missing required key
    try:
        loader._validate_setback_rules({"chennai": {}})
        assert False, "Expected RuleSchemaError"
    except loader.RuleSchemaError as e:
        assert "_fallback_nbc" in str(e) or "missing" in str(e).lower()
    # Missing plot_type section
    try:
        loader._validate_setback_rules({
            "chennai": {"detached": {"tiers": [{
                "plot_area_max_sqm": 100, "front_m": 1.0, "rear_m": 1.0,
                "side_left_m": 1.0, "side_right_m": 1.0,
            }]}},
            "_fallback_nbc": {"detached": {"tiers": [{
                "plot_area_max_sqm": 100, "front_m": 1.0, "rear_m": 1.0,
                "side_left_m": 1.0, "side_right_m": 1.0,
            }]}},
        })
        assert False, "Expected RuleSchemaError for missing semi_detached"
    except loader.RuleSchemaError as e:
        assert "semi_detached" in str(e) or "continuous" in str(e)
    print("PASS setback schema validator rejects malformed data")


def test_room_minimums_schema_rejects_missing_types():
    """_validate_room_minimums catches missing room types."""
    from buildemup.utils import kb_rules_loader as loader
    try:
        loader._validate_room_minimums({
            "room_minimums_sqm": {
                "BEDROOM_MASTER": {"value": 9.5},
                # Missing 11 other room types!
            },
            "circulation_factor": {"value": 1.30},
        })
        assert False, "Expected RuleSchemaError"
    except loader.RuleSchemaError as e:
        assert "missing room types" in str(e)
    print("PASS room_minimums schema rejects incomplete room types")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.1 — Session 2 Tests: Setback Calculator + KB")
    print("=" * 70)
    print()
    print("--- B. Setback calculation ---")
    test_chennai_detached_small_plot()
    test_chennai_detached_medium_plot()
    test_chennai_detached_large_plot_high_building()
    test_chennai_continuous_zero_side_setbacks()
    test_chennai_continuous_front_scales_with_road()
    test_semi_detached_zeros_shared_side_only()
    test_mumbai_and_delhi_use_real_dcr_v09()
    test_all_6_cities_use_real_dcr_after_session_d()
    test_compliance_check_flags_all_violating_sides()
    test_compliance_check_passes_when_compliant()
    test_compliance_check_flags_only_one_side()
    test_corner_plot_uses_wider_road()
    print()
    print("--- KB Parity tests ---")
    test_room_minimums_json_matches_python_constants()
    test_setback_rules_loads_with_all_cities()
    test_circulation_factor_is_1_35()
    test_circulation_factor_size_aware()
    test_setback_schema_rejects_bad_data()
    test_room_minimums_schema_rejects_missing_types()
    print()
    print("=" * 70)
    print("ALL SESSION 2 TESTS PASSED")
    print("=" * 70)
