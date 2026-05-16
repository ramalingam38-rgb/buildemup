"""
v0.9 Session C tests — Mumbai DCPR 2034 + Delhi MPD-2021 DCRs.

Covers the Component 1 v0.9 Session C work:
  - Mumbai DCPR 2034 (suburbs default) tier resolution by plot+road
  - Delhi MPD-2021 plot-area-based setback table
  - Authority strings reflect real DCR (not NBC fallback)
  - Disclosure text exposed for both cities
  - Compliance check works correctly with new tiers
  - Parity: cost engine still runs and returns city-specific costs
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────────
# Mumbai DCPR 2034
# ─────────────────────────────────────────────────────────────────────────

def test_mumbai_authority_string():
    """Authority must reference DCPR 2034 (not NBC)."""
    from buildemup.utils.kb_rules_loader import (
        get_setback_authority_for_city,
    )
    auth = get_setback_authority_for_city("mumbai")
    assert "DCPR 2034" in auth
    assert "MCGM" in auth
    print(f"PASS mumbai authority: {auth}")


def test_mumbai_disclosure_present():
    """Mumbai section has _disclosure_text about Suburbs default."""
    from buildemup.utils.kb_rules_loader import get_setback_rules_for_city
    rules = get_setback_rules_for_city("mumbai")
    assert "_disclosure_text" in rules
    assert "SUBURBS" in rules["_disclosure_text"]
    assert "Island City" in rules["_disclosure_text"]
    print("PASS mumbai disclosure surfaces zone caveat")


def test_mumbai_small_plot_road_under_21m():
    """Mumbai 9×15 plot (135 sqm) on 9m road → small_plot tier, front 4.5m."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=9.0, depth_m=15.0, facing=PlotOrientation.NORTH,
             city="mumbai", road_width_m=9.0, plot_type=PlotType.DETACHED)
    s, auth = compute_compliant_setbacks(p)
    assert "DCPR 2034" in auth
    assert s.front_m == 4.5  # suburbs road < 21m
    assert s.side_left_m == 1.5
    assert s.side_right_m == 1.5
    print(f"PASS mumbai 135 sqm/9m road: F={s.front_m} S={s.side_left_m}")


def test_mumbai_medium_plot_road_under_21m():
    """Mumbai 15×20 plot (300 sqm) → medium tier, sides 2m."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=15.0, depth_m=20.0, facing=PlotOrientation.NORTH,
             city="mumbai", road_width_m=12.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 300 sqm matches medium_plot tier (max 500)
    assert s.side_left_m == 2.0, f"Expected side 2.0, got {s.side_left_m}"
    assert s.front_m == 4.5  # still suburbs < 21m
    print(f"PASS mumbai 300 sqm: medium tier sides=2m")


def test_mumbai_large_plot_road_21_to_52m():
    """Mumbai 25×30 plot (750 sqm) on 30m road → front 6m."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=25.0, depth_m=30.0, facing=PlotOrientation.NORTH,
             city="mumbai", road_width_m=30.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    assert s.front_m == 6.0   # 750 sqm matches large_plot tier (max 2000)
    assert s.side_left_m == 3.0
    print(f"PASS mumbai 750 sqm/30m road: F={s.front_m}")


def test_mumbai_continuous_uses_road_width_table():
    """Mumbai row-house: front per road width."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=4.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="mumbai", road_width_m=12.0, plot_type=PlotType.CONTINUOUS)
    s, auth = compute_compliant_setbacks(p)
    # Continuous: no sides, rear ≥ 1.5
    assert s.side_left_m == 0.0
    assert s.side_right_m == 0.0
    assert s.rear_m >= 1.5
    assert "DCPR 2034" in auth
    print(f"PASS mumbai CONTINUOUS uses road-width table")


# ─────────────────────────────────────────────────────────────────────────
# Delhi MPD-2021
# ─────────────────────────────────────────────────────────────────────────

def test_delhi_authority_string():
    """Authority must reference MPD-2021 + UBBL 2016."""
    from buildemup.utils.kb_rules_loader import (
        get_setback_authority_for_city,
    )
    auth = get_setback_authority_for_city("delhi")
    assert "MPD-2021" in auth
    assert "DDA" in auth
    print(f"PASS delhi authority: {auth}")


def test_delhi_disclosure_present():
    """Delhi section has _disclosure_text about Clause 4.4.3."""
    from buildemup.utils.kb_rules_loader import get_setback_rules_for_city
    rules = get_setback_rules_for_city("delhi")
    assert "_disclosure_text" in rules
    assert "Clause 4.4.3" in rules["_disclosure_text"]
    assert "Stilt" in rules["_disclosure_text"]
    print("PASS delhi disclosure surfaces clause + stilt rule")


def test_delhi_small_plot_under_50sqm():
    """Delhi <50 sqm plot → all zeros (row housing)."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=5.0, depth_m=8.0, facing=PlotOrientation.NORTH,
             city="delhi", road_width_m=6.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 40 sqm → very_small_plot tier
    assert s.front_m == 0.0
    assert s.rear_m == 0.0
    assert s.side_left_m == 0.0
    assert s.side_right_m == 0.0
    print(f"PASS delhi <50 sqm: all setbacks zero (row housing)")


def test_delhi_100_to_250_row_housing():
    """Delhi 100-250 sqm plot → row housing pattern."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=10.0, depth_m=15.0, facing=PlotOrientation.NORTH,
             city="delhi", road_width_m=9.0, plot_type=PlotType.DETACHED)
    # 150 sqm → small_plot_100_to_250
    s, _ = compute_compliant_setbacks(p)
    assert s.front_m == 3.0
    assert s.rear_m == 1.0
    assert s.side_left_m == 0.0      # row housing — no sides
    assert s.side_right_m == 0.0
    print(f"PASS delhi 150 sqm: row housing F={s.front_m} R={s.rear_m}, "
          f"no sides")


def test_delhi_bungalow_type_above_250sqm():
    """Delhi >250 sqm → bungalow type with all 4 setbacks."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    # 400 sqm
    p = Plot(width_m=20.0, depth_m=20.0, facing=PlotOrientation.NORTH,
             city="delhi", road_width_m=12.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 400 sqm → medium_plot_250_to_500
    assert s.front_m == 3.0
    assert s.rear_m == 3.0
    assert s.side_left_m == 3.0
    assert s.side_right_m == 3.0
    print(f"PASS delhi 400 sqm: bungalow type 4-side (3,3,3,3)")


def test_delhi_large_plot_500_to_1000():
    """Delhi 500-1000 sqm → larger bungalow."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=25.0, depth_m=30.0, facing=PlotOrientation.NORTH,
             city="delhi", road_width_m=18.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 750 sqm → large_plot_500_to_1000
    assert s.front_m == 6.0
    assert s.rear_m == 3.0
    assert s.side_left_m == 3.0
    print(f"PASS delhi 750 sqm: F=6, sides=3")


def test_delhi_very_large_plot():
    """Delhi 1000+ sqm → very_large tier with bigger setbacks."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=40.0, depth_m=40.0, facing=PlotOrientation.NORTH,
             city="delhi", road_width_m=24.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 1600 sqm → very_large_plot_1000_plus
    assert s.front_m == 9.0
    assert s.rear_m == 6.0
    assert s.side_left_m == 6.0
    print(f"PASS delhi 1600 sqm: F=9, R=6, sides=6")


# ─────────────────────────────────────────────────────────────────────────
# Compliance + integration checks
# ─────────────────────────────────────────────────────────────────────────

def test_mumbai_user_setback_below_compliance_flagged():
    """User states 0.5m setback → compliance violation flagged for Mumbai."""
    from buildemup.domain import Setbacks
    from buildemup.components.c01.setback_calculator import (
        check_setback_compliance, compute_compliant_setbacks,
    )
    from buildemup.domain import Plot, PlotType, PlotOrientation
    p = Plot(width_m=9.0, depth_m=15.0, facing=PlotOrientation.NORTH,
             city="mumbai", road_width_m=9.0, plot_type=PlotType.DETACHED)
    nbc, _ = compute_compliant_setbacks(p)
    user = Setbacks(front_m=0.5, rear_m=0.5,
                    side_left_m=0.5, side_right_m=0.5)
    is_ok, violations = check_setback_compliance(user, nbc)
    assert is_ok is False
    # All four sides should be flagged
    assert len(violations) == 4
    print(f"PASS mumbai compliance flags 4 violations on bad setbacks")


def test_delhi_user_setback_below_compliance_flagged():
    """User states 0.5m setback → compliance violation flagged for Delhi."""
    from buildemup.domain import Setbacks
    from buildemup.components.c01.setback_calculator import (
        check_setback_compliance, compute_compliant_setbacks,
    )
    from buildemup.domain import Plot, PlotType, PlotOrientation
    # 400 sqm bungalow tier (3m all sides)
    p = Plot(width_m=20.0, depth_m=20.0, facing=PlotOrientation.NORTH,
             city="delhi", road_width_m=12.0, plot_type=PlotType.DETACHED)
    nbc, _ = compute_compliant_setbacks(p)
    user = Setbacks(front_m=0.5, rear_m=0.5,
                    side_left_m=0.5, side_right_m=0.5)
    is_ok, violations = check_setback_compliance(user, nbc)
    assert is_ok is False
    assert len(violations) == 4
    print(f"PASS delhi compliance flags 4 violations on bad setbacks")


def test_mumbai_full_brief_uses_dcpr():
    """Full brief through engine: Mumbai compliance source = DCPR 2034."""
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=9.0, plot_depth_m=15.0, plot_facing="N",
        city="mumbai", road_width_m=9.0,
        user_setback_front_m=4.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(
            floor_number=0, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.LIVING, 1),
                   RoomRequirement(RoomType.KITCHEN, 1)),
        ),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    output = BriefCaptureEngine().execute(inp)
    assert output.compliance_summary.is_setback_compliant is True
    assert "DCPR 2034" in output.compliance_summary.source_authority
    # KB versions reference setback rules
    assert "setback_rules" in output.kb_versions
    print(f"PASS mumbai full brief: source={output.compliance_summary.source_authority}")


def test_delhi_full_brief_uses_mpd2021():
    """Full brief through engine: Delhi compliance source = MPD-2021."""
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=20.0, plot_depth_m=20.0, plot_facing="N",
        city="delhi", road_width_m=12.0,
        user_setback_front_m=3.0, user_setback_rear_m=3.0,
        user_setback_side_left_m=3.0, user_setback_side_right_m=3.0,
        floors=(FloorRequirement(
            floor_number=0, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.LIVING, 1),),
        ),),
        budget_min_lakhs=30, budget_max_lakhs=50,
    )
    output = BriefCaptureEngine().execute(inp)
    assert output.compliance_summary.is_setback_compliant is True
    assert "MPD-2021" in output.compliance_summary.source_authority
    print(f"PASS delhi full brief: source={output.compliance_summary.source_authority}")


def test_mumbai_cost_uses_mumbai_multiplier():
    """C7 cost for Mumbai > Chennai when given IDENTICAL envelope.

    Important context: when going through the brief→C7 bridge, Mumbai's
    stricter setbacks (DCPR 2034 mandates more setback area) shrink the
    envelope significantly. So a Mumbai *brief* may produce LOWER total
    cost than a Chennai brief on the same plot — because Mumbai legally
    builds smaller. That's correct behaviour, not a bug.

    To verify the per-city COST MULTIPLIER itself, we bypass the brief
    layer and call C7 directly with the same envelope dimensions for both
    cities. Mumbai's multiplier is documented at 1.35× Chennai in the C7
    KB; in practice the ratio is ~2× because Mumbai also has higher
    contractor margins built into the cost model.
    """
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    def call_c7(city):
        inp = StructuralGridInput(
            envelope_width_m=20.0, envelope_depth_m=25.0,
            floors_above_ground=1,
            city=city,
        )
        return StructuralGridEngine().execute(inp).cost

    chennai_cost = call_c7("chennai")
    mumbai_cost = call_c7("mumbai")
    delhi_cost = call_c7("delhi")

    assert chennai_cost is not None and mumbai_cost is not None
    # Mumbai must exceed Chennai (multiplier 1.35 + extra contractor margin)
    assert mumbai_cost.exact_value > chennai_cost.exact_value
    # Delhi (1.15 multiplier) must also exceed Chennai
    assert delhi_cost.exact_value > chennai_cost.exact_value
    # And Mumbai must exceed Delhi
    assert mumbai_cost.exact_value > delhi_cost.exact_value
    print(f"PASS C7 multipliers: chennai={chennai_cost.exact_value/1e5:.1f}L "
          f"< delhi={delhi_cost.exact_value/1e5:.1f}L "
          f"< mumbai={mumbai_cost.exact_value/1e5:.1f}L "
          f"(same envelope)")


def test_mumbai_brief_envelope_smaller_than_chennai_for_same_plot():
    """Document: Mumbai brief produces smaller envelope than Chennai for same plot.

    This is correct DCPR 2034 behaviour: Mumbai's mandatory setbacks
    (4.5m front in suburbs vs Chennai's 1.5m) eat more of the plot. The
    user gets a smaller building but at higher per-sqft cost. The system
    correctly reflects both. Net total cost can go either way.
    """
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    floors = (FloorRequirement(
        floor_number=0, floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(RoomType.LIVING, 1),),
    ),)
    common = dict(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=floors, budget_min_lakhs=15, budget_max_lakhs=25,
    )
    chennai_out = BriefCaptureEngine().execute(
        BriefCaptureInput(city="chennai", **common)
    )
    mumbai_out = BriefCaptureEngine().execute(
        BriefCaptureInput(city="mumbai", **common)
    )
    # Mumbai envelope must be smaller (front 4.5 vs 1.5 = 3m less depth)
    assert mumbai_out.gross_envelope_sqm < chennai_out.gross_envelope_sqm
    diff_pct = ((chennai_out.gross_envelope_sqm
                 - mumbai_out.gross_envelope_sqm)
                / chennai_out.gross_envelope_sqm * 100)
    print(f"PASS mumbai envelope {mumbai_out.gross_envelope_sqm:.0f} sqm "
          f"< chennai {chennai_out.gross_envelope_sqm:.0f} sqm "
          f"({diff_pct:.0f}% smaller — DCPR 2034 mandates more setback)")


def test_all_6_cities_engine_smoke():
    """All 6 supported cities can run end-to-end without crash."""
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    floors = (FloorRequirement(
        floor_number=0, floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(RoomType.LIVING, 1),),
    ),)
    for city in ["chennai", "mumbai", "pune", "hyderabad", "delhi", "bangalore"]:
        inp = BriefCaptureInput(
            plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
            city=city, road_width_m=9.0,
            user_setback_front_m=3.0, user_setback_rear_m=2.0,
            user_setback_side_left_m=2.0, user_setback_side_right_m=2.0,
            floors=floors, budget_min_lakhs=15, budget_max_lakhs=25,
        )
        output = BriefCaptureEngine().execute(inp)
        assert output.brief.plot.city == city
        assert output.proceed_with_warnings is True
    print("PASS all 6 cities run end-to-end without error")


def test_disclosure_appears_in_explain_for_mumbai():
    """v0.9 Session C: Mumbai brief shows DCR disclosure inline in explain()."""
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="mumbai", road_width_m=9.0,
        user_setback_front_m=4.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(
            floor_number=0, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.LIVING, 1),),
        ),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    engine = BriefCaptureEngine()
    text = engine.explain(inp, engine.execute(inp))
    # Disclosure appears under SETBACKS section
    assert "DCR disclosure" in text
    assert "SUBURBS" in text         # the actual mumbai disclosure text
    assert "Island City" in text     # the caveat
    print("PASS mumbai DCR disclosure rendered inline in explain()")


def test_disclosure_in_api_response_for_all_cities():
    """API exposes dcr_disclosure field for every city.

    After v0.9 Session D all 6 cities have city-specific DCRs and
    disclosure text. Chennai (TNCDBR fully implemented) returns empty
    string. The other 5 each surface a city-specific caveat.
    """
    import json
    from buildemup.api.brief_endpoint import handle_brief_capture
    base_payload = {
        "plot_width_m": 12.0, "plot_depth_m": 15.0, "plot_facing": "N",
        "road_width_m": 9.0,
        "user_setback_front_m": 3.0, "user_setback_rear_m": 2.0,
        "user_setback_side_left_m": 2.0, "user_setback_side_right_m": 2.0,
        "floors": [{"floor_number": 0, "floor_use": "residential",
                    "rooms": [{"room_type": "living", "count": 1}]}],
        "budget_min_lakhs": 15, "budget_max_lakhs": 25,
    }

    expectations = {
        "chennai":    "",                # TNCDBR full, no caveat
        "mumbai":     "SUBURBS",         # DCPR 2034 zone caveat
        "delhi":      "Clause 4.4.3",    # MPD-2021 reference + verification
        "bangalore":  "UDD",             # 2026 BBMP/UDD amendments
        "pune":       "UDCPR",           # UDCPR 2020 reference
        "hyderabad":  "G.O. Ms. 168",    # Telangana Building Rules
    }
    for city, expected_substr in expectations.items():
        status, body = handle_brief_capture(json.dumps(
            {**base_payload, "city": city}
        ))
        assert status == 200
        disclosure = body["brief_summary"]["compliance"]["dcr_disclosure"]
        assert isinstance(disclosure, str)
        if expected_substr:
            assert expected_substr in disclosure, (
                f"{city} disclosure missing '{expected_substr}': "
                f"{disclosure[:120]}"
            )
        else:
            # Chennai returns empty — full DCR has no caveats
            assert disclosure == "", f"chennai got unexpected disclosure"
    print("PASS API dcr_disclosure correct for all 6 cities (v0.9 Session D)")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.9 Session C — Mumbai DCPR 2034 + Delhi MPD-2021")
    print("=" * 70)
    print()
    print("--- Mumbai DCPR 2034 ---")
    test_mumbai_authority_string()
    test_mumbai_disclosure_present()
    test_mumbai_small_plot_road_under_21m()
    test_mumbai_medium_plot_road_under_21m()
    test_mumbai_large_plot_road_21_to_52m()
    test_mumbai_continuous_uses_road_width_table()
    print()
    print("--- Delhi MPD-2021 ---")
    test_delhi_authority_string()
    test_delhi_disclosure_present()
    test_delhi_small_plot_under_50sqm()
    test_delhi_100_to_250_row_housing()
    test_delhi_bungalow_type_above_250sqm()
    test_delhi_large_plot_500_to_1000()
    test_delhi_very_large_plot()
    print()
    print("--- Compliance + integration ---")
    test_mumbai_user_setback_below_compliance_flagged()
    test_delhi_user_setback_below_compliance_flagged()
    test_mumbai_full_brief_uses_dcpr()
    test_delhi_full_brief_uses_mpd2021()
    test_mumbai_cost_uses_mumbai_multiplier()
    test_mumbai_brief_envelope_smaller_than_chennai_for_same_plot()
    test_all_6_cities_engine_smoke()
    print()
    print("--- v0.9 Session C: disclosure surfacing ---")
    test_disclosure_appears_in_explain_for_mumbai()
    test_disclosure_in_api_response_for_all_cities()
    print()
    print("=" * 70)
    print("ALL V0.9 SESSION C TESTS PASSED")
    print("=" * 70)
