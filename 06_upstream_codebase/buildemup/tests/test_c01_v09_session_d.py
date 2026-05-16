"""
v0.9 Session D tests — Bangalore BBMP/UDD + Pune UDCPR + Hyderabad GHMC DCRs.

After Session D, ALL 6 launch cities have real DCR-backed setback rules
(no NBC fallback for any supported city).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────────
# Bangalore BBMP / Karnataka UDD 2026
# ─────────────────────────────────────────────────────────────────────────

def test_bangalore_authority_string():
    """Bangalore now has a real authority (BBMP / UDD), not NBC."""
    from buildemup.utils.kb_rules_loader import (
        get_setback_authority_for_city,
    )
    auth = get_setback_authority_for_city("bangalore")
    assert "BBMP" in auth or "UDD" in auth
    assert "NBC" not in auth
    print(f"PASS bangalore authority: {auth}")


def test_bangalore_disclosure_present():
    """Bangalore disclosure mentions UDD 2025 amendments."""
    from buildemup.utils.kb_rules_loader import get_setback_rules_for_city
    rules = get_setback_rules_for_city("bangalore")
    assert "_disclosure_text" in rules
    assert "UDD" in rules["_disclosure_text"]
    print("PASS bangalore disclosure cites UDD amendments")


def test_bangalore_very_small_plot_under_60sqm():
    """Bangalore <60 sqm uses fixed 0.7m front, 0.6m others (UDD 2026)."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=6.0, depth_m=9.0, facing=PlotOrientation.NORTH,
             city="bangalore", road_width_m=6.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 54 sqm → very_small_plot tier (UDD 2026)
    assert s.front_m == 0.7
    assert s.rear_m == 0.6
    assert s.side_left_m == 0.6
    assert s.side_right_m == 0.6
    print(f"PASS bangalore <60 sqm: F=0.7 / others=0.6 (UDD 2026 fixed)")


def test_bangalore_30x40_plot():
    """Bangalore standard 30×40 ft (~111 sqm) uses small_plot tier."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    # 30×40 ft = 9.144×12.192 m ≈ 111.5 sqm → small_plot tier (60-150)
    p = Plot(width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTH,
             city="bangalore", road_width_m=9.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    assert s.front_m == 0.9
    assert s.rear_m == 0.7
    assert s.side_left_m == 0.7
    print(f"PASS bangalore 30×40ft (~111 sqm): F=0.9 R/S=0.7 (UDD 2026)")


def test_bangalore_large_plot_500_to_4000sqm():
    """Bangalore 500-4000 sqm tier: F=3.0, R=2.0, sides=2.0.

    Note: the >4000 sqm tier (5m all sides) exists in KB but isn't
    reachable through the Plot domain (60m max width × 60m max depth =
    3600 sqm cap). That tier is for layout-engine consumers in v1.0+.
    """
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=40.0, depth_m=60.0, facing=PlotOrientation.NORTH,
             city="bangalore", road_width_m=18.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 2400 sqm → large_plot tier (500-4000)
    assert s.front_m == 3.0
    assert s.rear_m == 2.0
    assert s.side_left_m == 2.0
    assert s.side_right_m == 2.0
    print(f"PASS bangalore 2400 sqm: F=3.0 R/S=2.0")


# ─────────────────────────────────────────────────────────────────────────
# Pune UDCPR Maharashtra
# ─────────────────────────────────────────────────────────────────────────

def test_pune_authority_string():
    """Pune now uses UDCPR Maharashtra, not NBC."""
    from buildemup.utils.kb_rules_loader import (
        get_setback_authority_for_city,
    )
    auth = get_setback_authority_for_city("pune")
    assert "UDCPR" in auth
    assert "NBC" not in auth
    print(f"PASS pune authority: {auth}")


def test_pune_disclosure_present():
    """Pune disclosure mentions UDCPR + non-congested area default."""
    from buildemup.utils.kb_rules_loader import get_setback_rules_for_city
    rules = get_setback_rules_for_city("pune")
    assert "_disclosure_text" in rules
    assert "UDCPR" in rules["_disclosure_text"]
    assert "NON-CONGESTED" in rules["_disclosure_text"]
    print("PASS pune disclosure cites UDCPR + non-congested default")


def test_pune_small_plot_under_100sqm():
    """Pune <100 sqm: front 1.5m, sides+rear 1.0m per UDCPR Table 6."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=8.0, depth_m=10.0, facing=PlotOrientation.NORTH,
             city="pune", road_width_m=9.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 80 sqm → small_plot tier
    assert s.front_m == 1.5
    assert s.rear_m == 1.0
    assert s.side_left_m == 1.0
    print(f"PASS pune <100 sqm: F=1.5 R/S=1.0 (UDCPR Table 6)")


def test_pune_medium_plot_100_to_200sqm():
    """Pune 100-200 sqm: 1.5m all four sides."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=12.0, depth_m=15.0, facing=PlotOrientation.NORTH,
             city="pune", road_width_m=9.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 180 sqm → medium_plot tier
    assert s.front_m == 1.5
    assert s.rear_m == 1.5
    assert s.side_left_m == 1.5
    assert s.side_right_m == 1.5
    print(f"PASS pune 180 sqm: 1.5m all sides")


def test_pune_continuous_uses_road_width():
    """Pune row housing: front per road width, rear 1.5m, no sides."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=4.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="pune", road_width_m=12.0, plot_type=PlotType.CONTINUOUS)
    s, _ = compute_compliant_setbacks(p)
    assert s.side_left_m == 0.0
    assert s.side_right_m == 0.0
    assert s.rear_m >= 1.5
    print(f"PASS pune CONTINUOUS uses road-width table (rear={s.rear_m})")


# ─────────────────────────────────────────────────────────────────────────
# Hyderabad GHMC G.O. Ms. 168
# ─────────────────────────────────────────────────────────────────────────

def test_hyderabad_authority_string():
    """Hyderabad now uses G.O. Ms. 168, not NBC."""
    from buildemup.utils.kb_rules_loader import (
        get_setback_authority_for_city,
    )
    auth = get_setback_authority_for_city("hyderabad")
    assert "G.O. Ms. 168" in auth
    assert "NBC" not in auth
    print(f"PASS hyderabad authority: {auth}")


def test_hyderabad_disclosure_present():
    """Hyderabad disclosure cites G.O. 168 + non-high-rise scope."""
    from buildemup.utils.kb_rules_loader import get_setback_rules_for_city
    rules = get_setback_rules_for_city("hyderabad")
    assert "_disclosure_text" in rules
    assert "G.O. Ms. 168" in rules["_disclosure_text"]
    assert "non-high-rise" in rules["_disclosure_text"].lower()
    print("PASS hyderabad disclosure cites G.O. 168 + non-high-rise scope")


def test_hyderabad_small_plot_up_to_100sqm():
    """Hyderabad ≤100 sqm: F=1.5 R=1.5 sides=1.0 (G.O. 168 Table-III)."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=8.0, depth_m=12.0, facing=PlotOrientation.NORTH,
             city="hyderabad", road_width_m=9.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 96 sqm → small_plot tier
    assert s.front_m == 1.5
    assert s.rear_m == 1.5
    assert s.side_left_m == 1.0
    assert s.side_right_m == 1.0
    print(f"PASS hyderabad ≤100 sqm: F=1.5 R=1.5 S=1.0 (G.O. 168)")


def test_hyderabad_medium_plot_100_to_300sqm():
    """Hyderabad 100-300 sqm tier: F=2.0 R=2.0 S=1.5."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=12.0, depth_m=18.0, facing=PlotOrientation.NORTH,
             city="hyderabad", road_width_m=9.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 216 sqm → small_medium tier (100-300)
    assert s.front_m == 2.0
    assert s.rear_m == 2.0
    assert s.side_left_m == 1.5
    print(f"PASS hyderabad 216 sqm: F=2.0 R=2.0 S=1.5")


def test_hyderabad_large_plot_500_to_750sqm():
    """Hyderabad 500-750 sqm: F=3.0, sides+rear=2.5."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=20.0, depth_m=30.0, facing=PlotOrientation.NORTH,
             city="hyderabad", road_width_m=18.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 600 sqm → large_plot tier
    assert s.front_m == 3.0
    assert s.rear_m == 2.5
    assert s.side_left_m == 2.5
    print(f"PASS hyderabad 600 sqm: F=3.0 R/S=2.5")


def test_hyderabad_huge_plot_over_1000sqm():
    """Hyderabad >1000 sqm: F=4.5, sides+rear=3.0."""
    from buildemup.domain import Plot, PlotType, PlotOrientation
    from buildemup.components.c01.setback_calculator import (
        compute_compliant_setbacks,
    )
    p = Plot(width_m=30.0, depth_m=40.0, facing=PlotOrientation.NORTH,
             city="hyderabad", road_width_m=24.0, plot_type=PlotType.DETACHED)
    s, _ = compute_compliant_setbacks(p)
    # 1200 sqm → huge_plot tier
    assert s.front_m == 4.5
    assert s.rear_m == 3.0
    assert s.side_left_m == 3.0
    print(f"PASS hyderabad 1200 sqm: F=4.5 R/S=3.0")


# ─────────────────────────────────────────────────────────────────────────
# Cross-city integration
# ─────────────────────────────────────────────────────────────────────────

def test_no_city_falls_back_to_nbc_after_session_d():
    """v0.9 Session D milestone: NO supported city uses NBC fallback."""
    from buildemup.utils.kb_rules_loader import (
        get_setback_authority_for_city,
    )
    for city in ["chennai", "mumbai", "delhi",
                 "bangalore", "pune", "hyderabad"]:
        auth = get_setback_authority_for_city(city)
        assert "NBC" not in auth, (
            f"{city} still uses NBC fallback after Session D: {auth}"
        )
    print("PASS no supported city falls back to NBC")


def test_full_brief_with_each_new_city_returns_real_authority():
    """End-to-end: brief through engine for each new city shows real DCR."""
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
    expected = {
        "bangalore": "BBMP",
        "pune":      "UDCPR",
        "hyderabad": "G.O. Ms. 168",
    }
    for city, expected_substr in expected.items():
        inp = BriefCaptureInput(
            plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
            city=city, road_width_m=9.0,
            user_setback_front_m=2.0, user_setback_rear_m=2.0,
            user_setback_side_left_m=2.0, user_setback_side_right_m=2.0,
            floors=floors, budget_min_lakhs=15, budget_max_lakhs=25,
        )
        output = BriefCaptureEngine().execute(inp)
        auth = output.compliance_summary.source_authority
        assert expected_substr in auth, (
            f"{city} brief returned {auth!r}, expected '{expected_substr}'"
        )
    print("PASS bangalore/pune/hyderabad full briefs return real DCR authorities")


def test_disclosure_in_explain_for_pune():
    """Pune brief explain() shows UDCPR disclosure inline."""
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="pune", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(
            floor_number=0, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.LIVING, 1),),
        ),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    engine = BriefCaptureEngine()
    text = engine.explain(inp, engine.execute(inp))
    assert "DCR disclosure" in text
    assert "UDCPR" in text
    assert "NON-CONGESTED" in text
    print("PASS pune UDCPR disclosure rendered inline")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.9 Session D — Bangalore + Pune + Hyderabad DCRs")
    print("=" * 70)
    print()
    print("--- Bangalore BBMP / UDD 2026 ---")
    test_bangalore_authority_string()
    test_bangalore_disclosure_present()
    test_bangalore_very_small_plot_under_60sqm()
    test_bangalore_30x40_plot()
    test_bangalore_large_plot_500_to_4000sqm()
    print()
    print("--- Pune UDCPR Maharashtra ---")
    test_pune_authority_string()
    test_pune_disclosure_present()
    test_pune_small_plot_under_100sqm()
    test_pune_medium_plot_100_to_200sqm()
    test_pune_continuous_uses_road_width()
    print()
    print("--- Hyderabad GHMC G.O. Ms. 168 ---")
    test_hyderabad_authority_string()
    test_hyderabad_disclosure_present()
    test_hyderabad_small_plot_up_to_100sqm()
    test_hyderabad_medium_plot_100_to_300sqm()
    test_hyderabad_large_plot_500_to_750sqm()
    test_hyderabad_huge_plot_over_1000sqm()
    print()
    print("--- Cross-city integration ---")
    test_no_city_falls_back_to_nbc_after_session_d()
    test_full_brief_with_each_new_city_returns_real_authority()
    test_disclosure_in_explain_for_pune()
    print()
    print("=" * 70)
    print("ALL V0.9 SESSION D TESTS PASSED")
    print("=" * 70)
