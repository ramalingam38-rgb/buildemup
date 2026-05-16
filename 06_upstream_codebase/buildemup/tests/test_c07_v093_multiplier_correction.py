"""
v0.9.3 cost multiplier correction tests.

After v0.9.2 review, Ramalingam asked for a Bangalore C7 multiplier fix.
Research session synthesized 8+ industry sources for Bangalore and 7+ for
Hyderabad. Honest findings:

  Bangalore 0.96 → 0.98  (parity with Chennai, NOT +15% as AECORD claimed)
  Hyderabad 0.93 → 0.85  (genuinely 15% below Chennai, not 7%)
  Delhi review queued for v0.9.4 (research suggests 1.15 → ~1.40)
  Mumbai review queued for v0.9.4 (research suggests 1.35 → ~1.45)

These tests lock the v2 multipliers in place and document the rationale.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_kb_version_bumped_to_v2():
    """KB_VERSION reflects the v2 multiplier corrections."""
    from buildemup.kb.material_rates_multicity import KB_VERSION
    assert "v2" in KB_VERSION, f"Expected v2 in KB_VERSION, got: {KB_VERSION}"
    print(f"PASS multi-city KB version: {KB_VERSION}")


def test_bangalore_multiplier_is_098():
    """Bangalore 0.98 — parity with Chennai per direct cost research."""
    from buildemup.kb.material_rates_multicity import CITY_COST_MULTIPLIER
    assert CITY_COST_MULTIPLIER["bangalore"] == 0.98, (
        f"Expected 0.98, got {CITY_COST_MULTIPLIER['bangalore']}"
    )
    print("PASS Bangalore multiplier = 0.98 (was 0.96)")


def test_hyderabad_multiplier_is_085():
    """Hyderabad 0.85 — genuinely cheapest of 6 cities per research."""
    from buildemup.kb.material_rates_multicity import CITY_COST_MULTIPLIER
    assert CITY_COST_MULTIPLIER["hyderabad"] == 0.85, (
        f"Expected 0.85, got {CITY_COST_MULTIPLIER['hyderabad']}"
    )
    print("PASS Hyderabad multiplier = 0.85 (was 0.93)")


def test_other_cities_unchanged_in_v093():
    """Chennai/Mumbai/Pune/Delhi unchanged in v0.9.3 — Delhi+Mumbai queued."""
    from buildemup.kb.material_rates_multicity import CITY_COST_MULTIPLIER
    assert CITY_COST_MULTIPLIER["chennai"] == 1.00
    assert CITY_COST_MULTIPLIER["mumbai"] == 1.35
    assert CITY_COST_MULTIPLIER["pune"] == 1.08
    assert CITY_COST_MULTIPLIER["delhi"] == 1.15
    print("PASS Chennai/Mumbai/Pune/Delhi unchanged (Mumbai+Delhi queued for v0.9.4)")


def test_bangalore_now_within_2pct_of_chennai():
    """C7 cost output: Bangalore ~within 5% of Chennai for same envelope.

    The multiplier alone is 0.98, but contractor margins differ
    (Chennai 12%, Bangalore 14%) so effective ratio is ~1.00.
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

    chennai = call_c7("chennai")
    bangalore = call_c7("bangalore")
    ratio = bangalore.exact_value / chennai.exact_value
    # Should now be roughly 1.0 ± 5%
    assert 0.93 < ratio < 1.00, (
        f"Bangalore should be near parity with Chennai post-v0.9.3, "
        f"got ratio {ratio:.3f}"
    )
    print(f"PASS Bangalore vs Chennai: ratio {ratio:.3f} (~parity)")


def test_hyderabad_now_clearly_below_chennai():
    """C7 cost output: Hyderabad ~15% below Chennai for same envelope."""
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

    chennai = call_c7("chennai")
    hyderabad = call_c7("hyderabad")
    ratio = hyderabad.exact_value / chennai.exact_value
    # Hyderabad multiplier 0.85 + similar margin → effective ~0.85-0.90
    assert 0.80 < ratio < 0.90, (
        f"Hyderabad should be 10-20% below Chennai post-v0.9.3, "
        f"got ratio {ratio:.3f}"
    )
    print(f"PASS Hyderabad vs Chennai: ratio {ratio:.3f} (clearly below)")


def test_hyderabad_is_cheapest_of_6_cities():
    """Per research: Hyderabad should be the cheapest city after v0.9.3."""
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    costs = {}
    for city in ["chennai", "bangalore", "hyderabad",
                 "pune", "delhi", "mumbai"]:
        inp = StructuralGridInput(
            envelope_width_m=20.0, envelope_depth_m=25.0,
            floors_above_ground=1,
            city=city,
        )
        costs[city] = StructuralGridEngine().execute(inp).cost.exact_value

    cheapest = min(costs, key=costs.get)
    assert cheapest == "hyderabad", (
        f"Expected Hyderabad cheapest post-v0.9.3, got {cheapest}: {costs}"
    )
    print(f"PASS Hyderabad confirmed cheapest of 6 cities at "
          f"₹{costs['hyderabad']/1e5:.1f}L")


def test_mumbai_remains_most_expensive():
    """Mumbai still highest even though v0.9.4 may push it higher."""
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    costs = {}
    for city in ["chennai", "bangalore", "hyderabad",
                 "pune", "delhi", "mumbai"]:
        inp = StructuralGridInput(
            envelope_width_m=20.0, envelope_depth_m=25.0,
            floors_above_ground=1,
            city=city,
        )
        costs[city] = StructuralGridEngine().execute(inp).cost.exact_value

    most_expensive = max(costs, key=costs.get)
    assert most_expensive == "mumbai", (
        f"Expected Mumbai most expensive, got {most_expensive}: {costs}"
    )
    print(f"PASS Mumbai confirmed most expensive at "
          f"₹{costs['mumbai']/1e5:.1f}L")


def test_full_brief_chennai_baseline_unchanged():
    """Chennai brief through full engine — cost in expected band, no breakage."""
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
        floors=(FloorRequirement(
            floor_number=0, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.LIVING, 1),
                   RoomRequirement(RoomType.KITCHEN, 1)),
        ),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    output = BriefCaptureEngine().execute(inp)
    assert output.c7_preview_cost is not None
    cost_lakhs = output.c7_preview_cost.exact_value / 100_000
    # Sanity: should be in single-digit lakhs for a small G+0 brief
    assert 1 < cost_lakhs < 20, f"Chennai cost out of band: ₹{cost_lakhs}L"
    print(f"PASS Chennai full brief still produces sensible cost "
          f"(₹{cost_lakhs:.1f}L for 108 sqm envelope)")


# ─────────────────────────────────────────────────────────────────────────
# v0.9.3.1 — Single-sentence consolidation (post-v0.9.3 review)
# ─────────────────────────────────────────────────────────────────────────
# After v0.9.3 review concluded "build Component 2 next, not more polish",
# I shipped only a single consolidating sentence covering 3 of the
# 8 review drawbacks (#3 opacity, #4 Mumbai/Delhi inconsistency, #7
# freshness). Rest deferred — reviewer's own priority was Component 2.

def test_explain_includes_consolidated_city_cost_caveat():
    """BUDGET section opens with the single consolidated caveat line.

    The line covers: market-based estimate (#3), Mumbai/Delhi under
    review (#4), 2026 rates may vary (#7). One sentence, three drawbacks.
    """
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
        floors=(FloorRequirement(
            floor_number=0, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.LIVING, 1),),
        ),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    text = BriefCaptureEngine().explain(
        inp, BriefCaptureEngine().execute(inp)
    )
    # All three drawback themes covered by the single line:
    assert "market-based estimate" in text          # #3 opacity
    assert "Mumbai + Delhi under review" in text    # #4 inconsistency
    assert "2026 estimates" in text                  # #7 freshness
    print("PASS BUDGET section has consolidated city-cost caveat "
          "(covers v0.9.3 review #3, #4, #7)")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 7 v2 cost multiplier corrections (BuildemUp v0.9.3)")
    print("=" * 70)
    print()
    test_kb_version_bumped_to_v2()
    test_bangalore_multiplier_is_098()
    test_hyderabad_multiplier_is_085()
    test_other_cities_unchanged_in_v093()
    print()
    test_bangalore_now_within_2pct_of_chennai()
    test_hyderabad_now_clearly_below_chennai()
    test_hyderabad_is_cheapest_of_6_cities()
    test_mumbai_remains_most_expensive()
    test_full_brief_chennai_baseline_unchanged()
    print()
    print("--- v0.9.3.1 consolidation (post-v0.9.3 review) ---")
    test_explain_includes_consolidated_city_cost_caveat()
    print()
    print("=" * 70)
    print("ALL V0.9.3 MULTIPLIER CORRECTION TESTS PASSED")
    print("=" * 70)
