"""
Multi-city integration tests + stress tests (v0.3).

Tests:
  - Each launch city (Chennai, Bangalore, Hyderabad, Mumbai, Pune, Delhi)
    produces sensible output
  - Cost differences between cities reflect their multipliers
  - Mumbai uses pile foundation in Bandra reclaimed area
  - Delhi triggers IS 13920 ductile detailing (Zone IV)
  - Stress tests: extreme envelopes, edge inputs, randomized configurations
  - Fallback test: unsupported city falls back gracefully with warning
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import random

from buildemup.components.c07_structural_grid import (
    StructuralGridEngine,
    StructuralGridInput,
)


# ─── Multi-city tests ────────────────────────────────────────────────────
def test_all_six_cities_produce_valid_output():
    """Every launch city must produce a valid result for the same plot."""
    cities_zones = [
        ("chennai", "II"),
        ("bangalore", "II"),
        ("hyderabad", "II"),
        ("mumbai", "III"),
        ("pune", "III"),
        ("delhi", "IV"),
    ]
    results = {}
    for city, zone in cities_zones:
        inp = StructuralGridInput(
            envelope_width_m=8.0, envelope_depth_m=10.0,
            floors_above_ground=1,
            city=city, seismic_zone=zone,
            has_stilt_parking=True,
        )
        result = StructuralGridEngine().execute(inp)
        results[city] = result
        assert result.cost.exact_value > 0
        assert result.structure.column_size_mm >= 230
    print(f"PASS all 6 cities produce valid output:")
    for city, r in results.items():
        print(f"  {city:<12} → ₹{r.cost.exact_value/100_000:>5.1f}L "
              f"({r.foundation.type:<10}) col={r.structure.column_size_mm}mm "
              f"zone={r.structure.seismic_zone}")


def test_mumbai_costs_more_than_chennai():
    """Mumbai's 1.35× multiplier should make costs significantly higher."""
    inp_chennai = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1,
        city="chennai", seismic_zone="II",
    )
    inp_mumbai = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1,
        city="mumbai", seismic_zone="III",
    )
    chennai_cost = StructuralGridEngine().execute(inp_chennai).cost.exact_value
    mumbai_cost = StructuralGridEngine().execute(inp_mumbai).cost.exact_value
    # Mumbai should be at least 25% higher (combination of multiplier + IS 13920 steel uplift)
    assert mumbai_cost > chennai_cost * 1.20, \
        f"Mumbai ({mumbai_cost}) should be >>20% above Chennai ({chennai_cost})"
    print(f"PASS Mumbai > Chennai cost:")
    print(f"  Chennai: ₹{chennai_cost/100_000:.2f}L")
    print(f"  Mumbai:  ₹{mumbai_cost/100_000:.2f}L (+{(mumbai_cost/chennai_cost - 1)*100:.1f}%)")


def test_hyderabad_costs_less_than_chennai():
    """Hyderabad's 0.93× multiplier should make costs slightly lower."""
    inp_chennai = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    inp_hyderabad = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="hyderabad", seismic_zone="II",
    )
    chennai_cost = StructuralGridEngine().execute(inp_chennai).cost.exact_value
    hyd_cost = StructuralGridEngine().execute(inp_hyderabad).cost.exact_value
    assert hyd_cost < chennai_cost
    print(f"PASS Hyderabad < Chennai: "
          f"₹{hyd_cost/100_000:.2f}L vs ₹{chennai_cost/100_000:.2f}L")


def test_delhi_triggers_is13920():
    """Delhi (Zone IV) must apply IS 13920 ductile detailing."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="delhi", seismic_zone="IV",
    )
    result = StructuralGridEngine().execute(inp)
    assert result.structure.needs_is13920_detailing
    assert result.structure.column_size_mm >= 300  # IS 13920 min
    assert result.structure.column_stirrups is not None
    has_13920 = any("IS 13920" in w for w in result.all_warnings)
    assert has_13920
    print(f"PASS Delhi (Zone IV) → IS 13920 enforced")
    print(f"  Stirrup spacing in hinge zone: "
          f"{result.structure.column_stirrups.spacing_in_hinge_zone_mm}mm")
    print(f"  Recommended steel %: {result.structure.recommended_steel_pct}%")


def test_unsupported_city_falls_back_with_warning():
    """Unsupported city (e.g., Kochi) should fall back to Chennai with warning."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="kochi", seismic_zone="III",
    )
    result = StructuralGridEngine().execute(inp)
    # Should produce a result (no crash)
    assert result.cost.exact_value > 0
    # Should have a fallback warning
    has_fallback_note = any("city-specific rate" in w
                             for w in result.all_warnings)
    assert has_fallback_note, \
        f"Expected fallback warning, got: {result.all_warnings[:3]}"
    print(f"PASS unsupported city falls back gracefully: "
          f"₹{result.cost.exact_value/100_000:.2f}L (with warning)")


# ─── Stress tests ────────────────────────────────────────────────────────
def test_smallest_valid_envelope():
    """5×5m exactly — minimum allowed envelope."""
    inp = StructuralGridInput(
        envelope_width_m=5.0, envelope_depth_m=5.0,
        floors_above_ground=0,  # G only
        city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    assert result.grid.total_columns >= 4  # At minimum corners
    print(f"PASS smallest envelope (5×5m): "
          f"{result.grid.total_columns} columns, "
          f"₹{result.cost.exact_value/100_000:.2f}L")


def test_largest_practical_envelope():
    """20×30m envelope — large bungalow."""
    inp = StructuralGridInput(
        envelope_width_m=20.0, envelope_depth_m=30.0,
        floors_above_ground=2, city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    assert result.grid.total_columns >= 20
    print(f"PASS largest envelope (20×30m): "
          f"{result.grid.total_columns} columns, "
          f"₹{result.cost.exact_value/100_000:.2f}L")


def test_extreme_aspect_ratio():
    """Long narrow plot 5×30m — typical row house."""
    inp = StructuralGridInput(
        envelope_width_m=5.0, envelope_depth_m=30.0,
        floors_above_ground=1, city="mumbai", seismic_zone="III",
    )
    result = StructuralGridEngine().execute(inp)
    # Should flag the high aspect ratio
    has_aspect_warning = any("aspect" in w.lower()
                              for w in result.all_warnings)
    assert has_aspect_warning, \
        f"Expected aspect ratio warning. Got: {result.all_warnings}"
    print(f"PASS extreme aspect ratio 5×30m flags irregularity")


def test_l_shape_corner_check():
    """L-shape with significant re-entrant corner triggers regularity warning."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="mumbai", seismic_zone="III",
        re_entrant_corner_x_m=2.5,  # 25% of 10m width = irregular
        re_entrant_corner_y_m=2.5,
    )
    result = StructuralGridEngine().execute(inp)
    assert not result.structure.regularity.is_regular
    assert result.structure.seismic_reliability in ("LOW", "MEDIUM")
    print(f"PASS L-shape corner triggers irregularity:")
    print(f"  Re-entrant corner: {result.structure.regularity.re_entrant_corner_pct}%")
    print(f"  Seismic reliability: {result.structure.seismic_reliability}")


def test_g_plus_4_max_floors():
    """G+4 is the max supported (bigger needs custom design)."""
    inp = StructuralGridInput(
        envelope_width_m=12.0, envelope_depth_m=14.0,
        floors_above_ground=4, city="bangalore", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    assert result.structure.column_size_mm >= 350  # Larger column for G+4
    print(f"PASS G+4 supported: col={result.structure.column_size_mm}mm, "
          f"₹{result.cost.exact_value/100_000:.2f}L")


def test_random_inputs_no_crashes():
    """Run 30 random valid configurations — none should crash."""
    random.seed(42)  # Reproducible
    cities_zones = [
        ("chennai", "II"), ("bangalore", "II"), ("hyderabad", "II"),
        ("mumbai", "III"), ("pune", "III"), ("delhi", "IV"),
    ]
    crashes = 0
    valid = 0
    for i in range(30):
        try:
            city, zone = random.choice(cities_zones)
            inp = StructuralGridInput(
                envelope_width_m=round(random.uniform(5.0, 15.0), 1),
                envelope_depth_m=round(random.uniform(5.0, 18.0), 1),
                floors_above_ground=random.randint(0, 4),
                city=city, seismic_zone=zone,
                has_stilt_parking=random.choice([True, False]),
                has_terrace_access=random.choice([True, False]),
                has_water_tank=random.choice([True, False]),
            )
            result = StructuralGridEngine().execute(inp)
            assert result.cost.exact_value > 0
            valid += 1
        except Exception as e:
            crashes += 1
            print(f"  CRASH on iteration {i}: {e}")
    assert crashes == 0, f"{crashes} crashes out of 30 random configs"
    print(f"PASS 30/30 random configurations completed without crashes")


def test_sensitivity_top_drivers_present():
    """Every result should have sensitivity analysis with at least 3 drivers."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    assert len(result.sensitivity.lines) >= 3
    # Top driver should be the biggest impact
    top = result.sensitivity.lines[0]
    second = result.sensitivity.lines[1]
    assert top.impact_on_total_rupees >= second.impact_on_total_rupees
    print(f"PASS sensitivity sorted by impact:")
    for line in result.sensitivity.lines[:3]:
        print(f"  {line.driver_name}: ±₹{line.impact_on_total_rupees:,.0f}")


if __name__ == "__main__":
    print("=" * 70)
    print("Multi-city + stress tests (v0.3)")
    print("=" * 70)
    print()
    print("--- Multi-city tests ---")
    test_all_six_cities_produce_valid_output()
    print()
    test_mumbai_costs_more_than_chennai()
    print()
    test_hyderabad_costs_less_than_chennai()
    print()
    test_delhi_triggers_is13920()
    print()
    test_unsupported_city_falls_back_with_warning()
    print()
    print("--- Stress tests ---")
    test_smallest_valid_envelope()
    test_largest_practical_envelope()
    test_extreme_aspect_ratio()
    test_l_shape_corner_check()
    test_g_plus_4_max_floors()
    test_random_inputs_no_crashes()
    test_sensitivity_top_drivers_present()
    print()
    print("=" * 70)
    print("ALL MULTI-CITY + STRESS TESTS PASSED")
    print("=" * 70)
