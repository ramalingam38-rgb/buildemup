"""
v0.1 Session 4 tests — Budget Bridge + Component 7 Handshake + Phased
                       Construction + Soft-Guide + Assumptions.

Covers SPEC_v0.2 Section 13:
  D. Budget estimation via Component 7 (~6 tests)
  E. Soft-guide prioritisation (top 3)
  G. Component 1 → Component 7 handshake (~5 tests)
  I. Assumptions tracking (~3 tests)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _make_brief(budget_min=15, budget_max=25, city="chennai",
                floors_count=2, facing=None, plot_type=None,
                add_stilt=False, vastu=None):
    """Helper to build a Brief quickly."""
    from buildemup.domain import (
        Plot, PlotOrientation, PlotType, Setbacks,
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
        Brief, BudgetRange, VastuTier,
    )
    if facing is None:
        facing = PlotOrientation.NORTH
    if plot_type is None:
        plot_type = PlotType.DETACHED
    if vastu is None:
        vastu = VastuTier.OFF

    plot = Plot(width_m=12, depth_m=15, facing=facing,
                city=city, road_width_m=9, plot_type=plot_type)
    setbacks = Setbacks(1.5, 1.5, 1.5, 1.5)

    floors = []
    if add_stilt:
        floors.append(FloorRequirement(
            floor_number=0, floor_use=FloorUse.STILT_PARKING,
        ))
        # Start residential at floor 1
        start = 1
    else:
        floors.append(FloorRequirement(
            floor_number=0, floor_use=FloorUse.RESIDENTIAL,
            rooms=(
                RoomRequirement(RoomType.LIVING, 1),
                RoomRequirement(RoomType.KITCHEN, 1),
                RoomRequirement(RoomType.BATHROOM_COMMON, 1),
            ),
        ))
        start = 1

    for i in range(start, floors_count):
        floors.append(FloorRequirement(
            floor_number=i, floor_use=FloorUse.RESIDENTIAL,
            rooms=(
                RoomRequirement(RoomType.BEDROOM_MASTER, 1),
                RoomRequirement(RoomType.BATHROOM_ATTACHED, 1),
            ),
        ))

    return Brief(
        plot=plot, user_stated_setbacks=setbacks,
        nbc_compliant_setbacks=setbacks,
        floors=tuple(floors),
        budget_range=BudgetRange(min_lakhs=budget_min, max_lakhs=budget_max),
        vastu_preference=vastu,
    )


# ─────────────────────────────────────────────────────────────────────────
# D. Budget bridge — Component 7 single source of truth
# ─────────────────────────────────────────────────────────────────────────

def test_budget_bridge_returns_cost_from_c7():
    """Bridge successfully extracts cost from Component 7 execution."""
    from buildemup.components.c01.budget_bridge import call_component_7_for_cost
    brief = _make_brief()
    cost, msgs = call_component_7_for_cost(brief)
    assert cost is not None, f"cost should not be None; msgs: {msgs}"
    assert cost.exact_value > 0
    assert cost.range_min <= cost.exact_value <= cost.range_max
    assert "Component 7" in cost.source
    print(f"PASS bridge returns cost: ₹{cost.exact_value/100_000:.1f}L "
          f"(₹{cost.range_min/100_000:.1f}L-{cost.range_max/100_000:.1f}L)")


def test_budget_bridge_cost_is_consistent_with_direct_c7():
    """Bridge cost == running Component 7 directly on the same input."""
    from buildemup.components.c01.budget_bridge import call_component_7_for_cost
    from buildemup.components.c07_structural_grid import StructuralGridEngine
    brief = _make_brief()
    bridge_cost, _ = call_component_7_for_cost(brief)

    sgi = brief.to_structural_grid_input()
    direct_result = StructuralGridEngine().execute(sgi)
    direct_exact = direct_result.cost.exact_value

    # Must be exactly the same (within floating point)
    assert abs(bridge_cost.exact_value - direct_exact) < 1.0
    print(f"PASS bridge cost matches direct C7 output "
          f"(₹{bridge_cost.exact_value:.0f} == ₹{direct_exact:.0f})")


def test_budget_comparison_under_budget_strong_concern():
    """Budget max < 80% of estimate → STRONG_CONCERN."""
    from buildemup.components.c01.budget_bridge import (
        call_component_7_for_cost, compare_budget_to_estimate,
    )
    from buildemup.domain import GuidanceSeverity
    brief = _make_brief(budget_min=1, budget_max=2)    # ~₹1-2L
    cost, _ = call_component_7_for_cost(brief)
    assert cost is not None
    msgs = compare_budget_to_estimate(brief.budget_range, cost)
    assert any(m.severity == GuidanceSeverity.STRONG_CONCERN for m in msgs)
    assert any("below" in m.text.lower() for m in msgs)
    print(f"PASS under-budget → STRONG_CONCERN")


def test_budget_comparison_aligned_info():
    """Budget aligned with estimate → INFO."""
    from buildemup.components.c01.budget_bridge import (
        call_component_7_for_cost, compare_budget_to_estimate,
    )
    from buildemup.domain import GuidanceSeverity, BudgetRange
    brief = _make_brief()
    cost, _ = call_component_7_for_cost(brief)
    # Budget that wraps around the cost — no range check issues
    aligned_budget_min = int(cost.exact_value / 100_000 * 0.90)
    aligned_budget_max = int(cost.exact_value / 100_000 * 1.20)
    budget = BudgetRange(min_lakhs=aligned_budget_min, max_lakhs=aligned_budget_max)
    msgs = compare_budget_to_estimate(budget, cost)
    assert any(m.severity == GuidanceSeverity.INFO for m in msgs)
    print(f"PASS aligned-budget → INFO")


def test_budget_comparison_generous_info():
    """Budget > 150% of estimate → INFO (generous)."""
    from buildemup.components.c01.budget_bridge import (
        call_component_7_for_cost, compare_budget_to_estimate,
    )
    from buildemup.domain import GuidanceSeverity
    brief = _make_brief(budget_min=50, budget_max=100)    # ₹50-100L
    cost, _ = call_component_7_for_cost(brief)
    msgs = compare_budget_to_estimate(brief.budget_range, cost)
    assert any(m.severity == GuidanceSeverity.INFO for m in msgs)
    assert any("generous" in m.text.lower() for m in msgs)
    print(f"PASS over-budget → INFO (generous)")


def test_seismic_zone_lookup():
    """Each supported city maps to its correct IS 1893 zone."""
    from buildemup.components.c01.budget_bridge import (
        get_seismic_zone_for_city,
    )
    assert get_seismic_zone_for_city("chennai") == "II"
    assert get_seismic_zone_for_city("bangalore") == "II"
    assert get_seismic_zone_for_city("hyderabad") == "II"
    assert get_seismic_zone_for_city("mumbai") == "III"
    assert get_seismic_zone_for_city("pune") == "III"
    assert get_seismic_zone_for_city("delhi") == "IV"
    # Unknown city → fallback to III (moderate, conservative)
    assert get_seismic_zone_for_city("atlantis") == "III"
    print("PASS city → seismic zone lookup (6 cities + fallback)")


# ─────────────────────────────────────────────────────────────────────────
# G. Brief → Component 7 handshake
# ─────────────────────────────────────────────────────────────────────────

def test_handshake_envelope_subtracts_setbacks():
    """to_structural_grid_input subtracts setbacks (Drawback 2)."""
    brief = _make_brief()     # plot 12×15 with 1.5m setbacks all around
    sgi = brief.to_structural_grid_input()
    # Envelope = 12 - 1.5 - 1.5 = 9m; 15 - 1.5 - 1.5 = 12m
    assert sgi.envelope_width_m == 9.0
    assert sgi.envelope_depth_m == 12.0
    print(f"PASS envelope: 12×15m plot - 1.5 all sides → "
          f"{sgi.envelope_width_m}×{sgi.envelope_depth_m}m")


def test_handshake_floors_above_ground_counts_load_bearing():
    """floors_above_ground counts every floor with floor_number > 0.

    Per Drawback 3 clarification: STILT + RESIDENTIAL + TERRACE all count.
    """
    # G+1 (2 floors total): floor_number > 0 count = 1
    brief_g1 = _make_brief(floors_count=2)
    sgi = brief_g1.to_structural_grid_input()
    assert sgi.floors_above_ground == 1

    # G+2 (3 floors): floor_number > 0 count = 2
    brief_g2 = _make_brief(floors_count=3)
    sgi2 = brief_g2.to_structural_grid_input()
    assert sgi2.floors_above_ground == 2

    # Stilt + G+1 (3 floors, stilt on floor 0, residential on 1+2):
    # floor_number > 0 count = 2
    brief_stilt = _make_brief(floors_count=3, add_stilt=True)
    sgi3 = brief_stilt.to_structural_grid_input()
    assert sgi3.floors_above_ground == 2
    assert sgi3.has_stilt_parking is True
    print("PASS floors_above_ground counts all load-bearing floors "
          f"(G+1=1, G+2=2, Stilt+G+1=2)")


def test_handshake_seismic_zone_derived_from_city():
    """City determines seismic zone on handshake."""
    for city, expected_zone in [
        ("chennai", "II"), ("mumbai", "III"), ("delhi", "IV"),
    ]:
        brief = _make_brief(city=city)
        sgi = brief.to_structural_grid_input()
        assert sgi.city == city
        assert sgi.seismic_zone == expected_zone
    print("PASS handshake derives seismic_zone from city")


def test_handshake_envelope_capped_at_minimum_5m():
    """If setbacks exceed plot, envelope caps at 5m minimum.

    Component 7 requires envelope ≥ 5m × 5m. Our handshake caps at that
    lower bound so we always produce a valid C7 input — soft-guide will
    separately warn about insufficient buildable area.
    """
    from buildemup.domain import (
        Plot, PlotOrientation, PlotType, Setbacks,
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
        Brief, BudgetRange,
    )
    # Tiny plot with big setbacks — envelope would go below 5m
    plot = Plot(width_m=6, depth_m=6, facing=PlotOrientation.NORTH,
                city="chennai", road_width_m=9)
    setbacks = Setbacks(2.0, 2.0, 2.0, 2.0)    # total 4m each direction
    # 6 - 4 = 2m, but we cap at 5
    floor0 = FloorRequirement(
        floor_number=0, floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(RoomType.LIVING, 1),),
    )
    brief = Brief(plot=plot, user_stated_setbacks=setbacks,
                  nbc_compliant_setbacks=setbacks, floors=(floor0,),
                  budget_range=BudgetRange(10, 15))
    sgi = brief.to_structural_grid_input()
    assert sgi.envelope_width_m == 5.0    # capped at C7 minimum
    assert sgi.envelope_depth_m == 5.0    # capped at C7 minimum
    print("PASS envelope capped at 5m minimum when setbacks too large")


def test_handshake_c7_accepts_brief_output():
    """Component 7 executes successfully on Brief handshake output."""
    from buildemup.components.c07_structural_grid import StructuralGridEngine
    brief = _make_brief()
    sgi = brief.to_structural_grid_input()
    result = StructuralGridEngine().execute(sgi)
    assert result is not None
    assert result.cost.exact_value > 0
    assert result.grid is not None
    print(f"PASS Component 7 accepts brief handshake: "
          f"{len(result.grid.columns) if hasattr(result.grid, 'columns') else 'grid'} produced")


# ─────────────────────────────────────────────────────────────────────────
# Phased construction (Drawback 9)
# ─────────────────────────────────────────────────────────────────────────

def test_phased_construction_suggested_when_under_budget():
    """Budget < 80% of estimate → phased suggestion INFO message."""
    from buildemup.components.c01.phased_construction import (
        suggest_phased_construction_if_needed,
    )
    from buildemup.domain import (
        BudgetRange, CostEstimate, GuidanceSeverity,
    )
    budget = BudgetRange(min_lakhs=3, max_lakhs=4)
    cost = CostEstimate(exact_value=10_00_000, range_min=9_00_000,
                        range_max=11_00_000, confidence="WELL_CONSTRAINED",
                        source="C7")
    msgs = suggest_phased_construction_if_needed(budget, cost)
    assert len(msgs) == 1
    assert msgs[0].severity == GuidanceSeverity.INFO
    assert msgs[0].context == "phased_construction"
    assert "phased" in msgs[0].text.lower()
    # Ground-only estimate = 55% of 10L = 5.5L; text mentions this
    assert "6L" in msgs[0].text or "5L" in msgs[0].text
    print("PASS phased construction suggested when budget < 80% of estimate")


def test_phased_construction_skipped_when_budget_aligned():
    """Budget aligned → no phased suggestion."""
    from buildemup.components.c01.phased_construction import (
        suggest_phased_construction_if_needed,
    )
    from buildemup.domain import BudgetRange, CostEstimate
    budget = BudgetRange(min_lakhs=8, max_lakhs=12)
    cost = CostEstimate(exact_value=10_00_000, range_min=9_00_000,
                        range_max=11_00_000, confidence="WELL_CONSTRAINED",
                        source="C7")
    msgs = suggest_phased_construction_if_needed(budget, cost)
    assert len(msgs) == 0
    print("PASS phased construction NOT suggested when budget aligned")


def test_phased_handles_no_cost_gracefully():
    """If cost is None, phased suggestion returns empty (no crash)."""
    from buildemup.components.c01.phased_construction import (
        suggest_phased_construction_if_needed,
    )
    from buildemup.domain import BudgetRange
    budget = BudgetRange(min_lakhs=1, max_lakhs=2)
    msgs = suggest_phased_construction_if_needed(budget, None)
    assert msgs == []
    print("PASS phased handles None cost gracefully")


# ─────────────────────────────────────────────────────────────────────────
# E. Soft-guide top-3 prioritisation
# ─────────────────────────────────────────────────────────────────────────

def test_top_guidance_strong_first():
    """STRONG_CONCERN messages come first."""
    from buildemup.domain import GuidanceMessage, GuidanceSeverity
    from buildemup.components.c01.soft_guide_engine import compute_top_guidance
    msgs = [
        GuidanceMessage(GuidanceSeverity.INFO, "info1", "a", "Consider"),
        GuidanceMessage(GuidanceSeverity.STRONG_CONCERN, "strong1", "b", "Reconsider"),
        GuidanceMessage(GuidanceSeverity.CONCERN, "concern1", "c", "Review"),
        GuidanceMessage(GuidanceSeverity.INFO, "info2", "d", "Consider"),
    ]
    top = compute_top_guidance(msgs, n=3)
    assert top[0].severity == GuidanceSeverity.STRONG_CONCERN
    assert top[1].severity == GuidanceSeverity.CONCERN
    assert top[2].severity == GuidanceSeverity.INFO
    print("PASS top_guidance: STRONG → CONCERN → INFO order")


def test_top_guidance_stable_within_severity():
    """Within same severity, insertion order preserved."""
    from buildemup.domain import GuidanceMessage, GuidanceSeverity
    from buildemup.components.c01.soft_guide_engine import compute_top_guidance
    msgs = [
        GuidanceMessage(GuidanceSeverity.STRONG_CONCERN, "first_strong", "a", "Reconsider"),
        GuidanceMessage(GuidanceSeverity.STRONG_CONCERN, "second_strong", "b", "Reconsider"),
        GuidanceMessage(GuidanceSeverity.STRONG_CONCERN, "third_strong", "c", "Reconsider"),
    ]
    top = compute_top_guidance(msgs, n=3)
    assert top[0].text == "first_strong"
    assert top[1].text == "second_strong"
    assert top[2].text == "third_strong"
    print("PASS top_guidance is stable within severity (insertion order)")


def test_top_guidance_returns_fewer_than_n_if_not_available():
    """If < N messages, return all available."""
    from buildemup.domain import GuidanceMessage, GuidanceSeverity
    from buildemup.components.c01.soft_guide_engine import compute_top_guidance
    msgs = [GuidanceMessage(GuidanceSeverity.INFO, "only", "a", "Consider")]
    top = compute_top_guidance(msgs, n=3)
    assert len(top) == 1
    print("PASS top_guidance returns fewer when source is smaller")


def test_merge_guidance_sources_preserves_order():
    """merge_guidance_sources flattens in positional order."""
    from buildemup.domain import GuidanceMessage, GuidanceSeverity
    from buildemup.components.c01.soft_guide_engine import merge_guidance_sources
    src1 = [GuidanceMessage(GuidanceSeverity.INFO, "src1_a", "a", "Consider")]
    src2 = [GuidanceMessage(GuidanceSeverity.INFO, "src2_a", "b", "Consider"),
            GuidanceMessage(GuidanceSeverity.INFO, "src2_b", "c", "Consider")]
    src3 = []
    merged = merge_guidance_sources(src1, src2, src3)
    assert [m.text for m in merged] == ["src1_a", "src2_a", "src2_b"]
    print("PASS merge_guidance_sources preserves positional + insertion order")


def test_has_strong_concerns_detects():
    from buildemup.domain import GuidanceMessage, GuidanceSeverity
    from buildemup.components.c01.soft_guide_engine import has_strong_concerns
    mixed = [
        GuidanceMessage(GuidanceSeverity.INFO, "a", "a", "Consider"),
        GuidanceMessage(GuidanceSeverity.STRONG_CONCERN, "b", "b", "Reconsider"),
    ]
    only_info = [
        GuidanceMessage(GuidanceSeverity.INFO, "a", "a", "Consider"),
    ]
    assert has_strong_concerns(mixed) is True
    assert has_strong_concerns(only_info) is False
    assert has_strong_concerns([]) is False
    print("PASS has_strong_concerns correctly identifies severity")


# ─────────────────────────────────────────────────────────────────────────
# I. Assumptions tracking (Drawback 10)
# ─────────────────────────────────────────────────────────────────────────

def test_assumptions_include_defaults():
    """Assumptions list always includes the 5 core concepts.

    v0.9: default strings are now built inline (to include dynamic
    circulation factor), so we check for key concept keywords rather
    than literal string identity with DEFAULT_ASSUMPTIONS.
    """
    from buildemup.components.c01.assumptions_log import (
        build_assumptions_list,
    )
    a = build_assumptions_list(
        plot_type_label="detached",
        vastu_tier_label="off",
        city="chennai",
        used_nbc_fallback=False,
        auto_staircase_added=False,
    )
    joined = " ".join(a).lower()
    # 5 core concepts must be present
    assert "floor-to-floor height" in joined
    assert "rectangular" in joined  # envelope assumption
    assert "circulation factor" in joined
    assert "nbc 2016" in joined  # minimum room sizes
    assert "component 7" in joined  # cost engine
    # Expect at least 6 items (5 defaults + plot type line)
    assert len(a) >= 6
    print(f"PASS assumptions list includes all 5 core concepts "
          f"({len(a)} items total)")


def test_assumptions_adapt_to_plot_type():
    """Continuous/semi-detached/detached each add a specific assumption."""
    from buildemup.components.c01.assumptions_log import build_assumptions_list
    for pt, keyword in [
        ("continuous", "Continuous Building Area"),
        ("semi_detached", "Semi-detached"),
        ("detached", "Detached"),
    ]:
        a = build_assumptions_list(
            plot_type_label=pt, vastu_tier_label="off",
            city="chennai", used_nbc_fallback=False,
            auto_staircase_added=False,
        )
        assert any(keyword in item for item in a), \
            f"{pt} plot type assumption missing keyword '{keyword}'"
    print("PASS assumptions adapt to all 3 plot types")


def test_assumptions_flag_nbc_fallback():
    """NBC fallback gets an explicit disclosure line."""
    from buildemup.components.c01.assumptions_log import build_assumptions_list
    a = build_assumptions_list(
        plot_type_label="detached", vastu_tier_label="off",
        city="mumbai", used_nbc_fallback=True,
        auto_staircase_added=False,
    )
    assert any("NBC 2016 general" in item for item in a)
    assert any("mumbai" in item.lower() for item in a)
    # Compare to chennai (no fallback)
    a_chennai = build_assumptions_list(
        plot_type_label="detached", vastu_tier_label="off",
        city="chennai", used_nbc_fallback=False,
        auto_staircase_added=False,
    )
    # v0.9.1 changed wording from "city-specific DCR" to
    # "Setback rules applied: <authority>. KB version: <ver>"
    assert any(
        ("city-specific DCR" in item)
        or ("Setback rules applied" in item)
        for item in a_chennai
    )
    print("PASS assumptions list discloses NBC fallback vs city DCR")


def test_assumptions_flag_auto_staircase():
    from buildemup.components.c01.assumptions_log import build_assumptions_list
    a_with = build_assumptions_list(
        plot_type_label="detached", vastu_tier_label="off",
        city="chennai", used_nbc_fallback=False,
        auto_staircase_added=True,
    )
    assert any("Staircase auto-added" in item for item in a_with)

    a_without = build_assumptions_list(
        plot_type_label="detached", vastu_tier_label="off",
        city="chennai", used_nbc_fallback=False,
        auto_staircase_added=False,
    )
    assert not any("Staircase auto-added" in item for item in a_without)
    print("PASS assumptions flag auto-staircase only when added")


def test_assumptions_flag_vastu_tier():
    from buildemup.components.c01.assumptions_log import build_assumptions_list
    for tier, keyword in [("off", "OFF"), ("partial", "PARTIAL"), ("full", "FULL")]:
        a = build_assumptions_list(
            plot_type_label="detached", vastu_tier_label=tier,
            city="chennai", used_nbc_fallback=False,
            auto_staircase_added=False,
        )
        assert any(keyword in item for item in a), \
            f"Vastu {tier} → keyword '{keyword}' missing"
    print("PASS assumptions adapt to all 3 vastu tiers")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.1 — Session 4 Tests: Budget Bridge + Handshake")
    print("=" * 70)
    print()
    print("--- D. Budget bridge (Component 7 single source) ---")
    test_budget_bridge_returns_cost_from_c7()
    test_budget_bridge_cost_is_consistent_with_direct_c7()
    test_budget_comparison_under_budget_strong_concern()
    test_budget_comparison_aligned_info()
    test_budget_comparison_generous_info()
    test_seismic_zone_lookup()
    print()
    print("--- G. Brief → Component 7 handshake ---")
    test_handshake_envelope_subtracts_setbacks()
    test_handshake_floors_above_ground_counts_load_bearing()
    test_handshake_seismic_zone_derived_from_city()
    test_handshake_envelope_capped_at_minimum_5m()
    test_handshake_c7_accepts_brief_output()
    print()
    print("--- Phased construction (Drawback 9) ---")
    test_phased_construction_suggested_when_under_budget()
    test_phased_construction_skipped_when_budget_aligned()
    test_phased_handles_no_cost_gracefully()
    print()
    print("--- E. Soft-guide prioritisation (Drawback 6) ---")
    test_top_guidance_strong_first()
    test_top_guidance_stable_within_severity()
    test_top_guidance_returns_fewer_than_n_if_not_available()
    test_merge_guidance_sources_preserves_order()
    test_has_strong_concerns_detects()
    print()
    print("--- I. Assumptions tracking (Drawback 10) ---")
    test_assumptions_include_defaults()
    test_assumptions_adapt_to_plot_type()
    test_assumptions_flag_nbc_fallback()
    test_assumptions_flag_auto_staircase()
    test_assumptions_flag_vastu_tier()
    print()
    print("=" * 70)
    print("ALL SESSION 4 TESTS PASSED")
    print("=" * 70)
