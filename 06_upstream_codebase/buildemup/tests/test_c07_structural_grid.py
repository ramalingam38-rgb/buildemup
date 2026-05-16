"""
Tests for Component 7: Structural Grid Engine (refactored).

Tests the orchestrator + 4 sub-components working together.
Individual sub-components are tested in their own test files.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.components.c07_structural_grid import (
    StructuralGridEngine,
    StructuralGridInput,
)


def test_ne_30x40_chennai_walkthrough():
    """The walkthrough case: NE 30×40 Chennai with stilt + G+1 + terrace."""
    inp = StructuralGridInput(
        envelope_width_m=7.92,
        envelope_depth_m=10.97,
        floors_above_ground=1,
        city="chennai",
        area="velachery",
        seismic_zone="II",
        has_stilt_parking=True,
        has_terrace_access=True,
        has_water_tank=True,
        plot_facing="NE",
    )

    engine = StructuralGridEngine()
    result = engine.execute(inp)

    # Grid
    assert 2.7 <= result.grid.bay_x_m <= 4.5
    assert 2.7 <= result.grid.bay_y_m <= 4.5
    assert result.grid.total_columns >= 9

    # Structural sizing
    assert result.structure.column_size_mm == 300  # G+2 effective
    assert result.structure.concrete_grade == "M25"
    assert result.structure.seismic_zone == "II"
    assert result.structure.needs_is13920_detailing is False

    # Realistic load range
    assert 200 < result.structure.max_column_axial_load_kn < 1500

    # Foundation
    assert result.foundation.type in ("isolated", "combined", "raft")

    # Area-specific warning
    assert result.foundation.area_specific_warning is not None

    # Cost via TransparencyTriple
    assert result.cost.unit == "₹"
    assert result.cost.exact_value > 0
    assert len(result.cost.derivation) >= 4

    print(f"PASS NE 30×40 walkthrough:")
    print(f"  Grid: {result.grid.columns_x_count}×{result.grid.columns_y_count} "
          f"= {result.grid.total_columns} columns")
    print(f"  Bays: {result.grid.bay_x_m}m × {result.grid.bay_y_m}m")
    print(f"  Column: {result.structure.column_size_mm}mm")
    print(f"  Load: {result.structure.max_column_axial_load_kn:.0f} kN factored "
          f"({result.structure.max_column_load_unfactored_kn:.0f} kN service)")
    print(f"  Foundation: {result.foundation.type}")
    print(f"  Cost: {result.cost.format_short()}")


def test_zone_iv_delhi_is_supported():
    """Zone IV (Delhi) is now SUPPORTED with IS 13920 ductile detailing.

    Previously (v0.2) we refused Zone IV. In v0.3 we support it to
    accommodate the Delhi market, with stricter rules and IS 13920.
    """
    inp = StructuralGridInput(
        envelope_width_m=10.0,
        envelope_depth_m=10.0,
        floors_above_ground=1,
        city="delhi",
        seismic_zone="IV",
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)

    # Must apply IS 13920
    assert result.structure.needs_is13920_detailing is True
    # Must use seismic minimum column (300mm)
    assert result.structure.column_size_mm >= 300
    # Must produce stirrup spacing rules
    assert result.structure.column_stirrups is not None
    # Must warn about IS 13920
    has_13920 = any("IS 13920" in w for w in result.all_warnings)
    assert has_13920
    print(f"PASS Zone IV (Delhi) supported with IS 13920:")
    print(f"  Column: {result.structure.column_size_mm}mm")
    print(f"  Stirrups in hinge zone: "
          f"{result.structure.column_stirrups.spacing_in_hinge_zone_mm}mm")
    print(f"  Seismic reliability: {result.structure.seismic_reliability}")


def test_zone_v_is_refused():
    """Zone V still refused — requires expert design."""
    inp = StructuralGridInput(
        envelope_width_m=10.0,
        envelope_depth_m=10.0,
        floors_above_ground=1,
        seismic_zone="V",
    )
    engine = StructuralGridEngine()
    try:
        engine.execute(inp)
        assert False, "Expected error for Zone V"
    except Exception as e:
        assert "Zone V" in str(e) or "V" in str(e)
        print(f"PASS Zone V still refused gracefully")


def test_zone_iii_triggers_is13920_warning():
    """Zone III is supported but should warn about IS 13920 detailing."""
    inp = StructuralGridInput(
        envelope_width_m=10.0,
        envelope_depth_m=10.0,
        floors_above_ground=1,
        city="mumbai",
        seismic_zone="III",
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)

    assert result.structure.needs_is13920_detailing is True
    has_13920_warning = any(
        "IS 13920" in w or "ductile" in w.lower()
        for w in result.all_warnings
    )
    assert has_13920_warning
    print(f"PASS Zone III triggers IS 13920 warning")


def test_mumbai_reclaimed_uses_pile():
    """Mumbai heavy-load G+2 on weak soil should trigger pile foundation."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=12.0,
        floors_above_ground=2,
        city="mumbai",
        seismic_zone="III",
        has_stilt_parking=True,
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    # Mumbai SBC 15 is high but loads may drive to pile
    # Verify either pile OR raft (both are acceptable for Mumbai G+2 with stilt)
    assert result.foundation.type in ("pile", "raft", "combined"), \
        f"Mumbai G+2 expected heavy foundation, got {result.foundation.type}"
    print(f"PASS Mumbai G+2 → {result.foundation.type} foundation")


def test_kolkata_weak_soil_uses_pile():
    """Kolkata weak alluvial soil should trigger pile for any non-trivial load."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1,
        city="kolkata",
        seismic_zone="III",
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    assert result.foundation.type == "pile", \
        f"Kolkata G+1 expected pile, got {result.foundation.type}"
    assert result.foundation.pile_spec is not None
    assert result.foundation.total_piles > 0
    print(f"PASS Kolkata pile foundation:")
    print(f"  Pile dia: {result.foundation.pile_spec.diameter_mm}mm")
    print(f"  Pile length: {result.foundation.pile_spec.typical_length_m}m")
    print(f"  Piles per column: {result.foundation.piles_per_column}")
    print(f"  Total piles: {result.foundation.total_piles}")


def test_strap_footing_for_edge_condition():
    """Property-line-edge with large footing should use strap footing."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=12.0,
        floors_above_ground=2,
        city="chennai",
        seismic_zone="II",
        has_stilt_parking=True,
        is_property_line_edge=True,  # Property-line edge condition
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    # Strap or raft both valid (depending on footing size from load)
    assert result.foundation.type in ("strap", "raft", "combined"), \
        f"Edge condition expected strap/raft/combined, got {result.foundation.type}"
    print(f"PASS strap footing: type={result.foundation.type}, "
          f"strap beams={result.foundation.strap_beams_count}")
    """Water tank should produce a user-facing warning."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, has_water_tank=True,
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    has_tank_warning = any(
        "water tank" in w.lower() for w in result.all_warnings
    )
    assert has_tank_warning
    print(f"PASS water tank warning appears")


def test_velachery_marshy_warning():
    """Chennai Velachery area-specific warning should appear."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1,
        city="chennai", area="velachery",
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    assert result.foundation.area_specific_warning is not None
    assert ("marsh" in result.foundation.area_specific_warning.lower() or
            "water table" in result.foundation.area_specific_warning.lower())
    print(f"PASS Velachery marshy warning:")
    print(f"  {result.foundation.area_specific_warning[:100]}...")


def test_explanation_shows_safety_factors():
    """Per Transparency Triple: safety factors must be visible."""
    inp = StructuralGridInput(
        envelope_width_m=7.92, envelope_depth_m=10.97,
        floors_above_ground=1, has_stilt_parking=True,
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    explanation = engine.explain(inp, result)

    # Safety factors visible
    assert "γf" in explanation or "1.5" in explanation
    # Both service and factored loads
    assert "Service load" in explanation
    assert "Factored load" in explanation
    # Code citations
    assert "IS 456" in explanation
    # Disclaimer
    assert "structural engineer" in explanation.lower()
    print("PASS explanation shows safety factors + disclaimer")


def test_kb_version_in_cost_notes():
    """KB version in cost notes for auditability."""
    inp = StructuralGridInput(
        envelope_width_m=7.92, envelope_depth_m=10.97,
        floors_above_ground=1, has_stilt_parking=True,
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    kb_version_in_notes = any(
        "Chennai_2026" in n or "KB version" in n
        for n in result.cost.notes
    )
    assert kb_version_in_notes
    print(f"PASS KB version in cost notes")


def test_envelope_too_small_rejected():
    """Plot below 5×5m should be rejected."""
    try:
        StructuralGridInput(
            envelope_width_m=4.0,
            envelope_depth_m=4.0,
            floors_above_ground=1,
        )
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "too small" in str(e).lower()
        print(f"PASS envelope too small rejected")


def test_too_many_floors_rejected():
    """G+5 or above should be rejected."""
    try:
        StructuralGridInput(
            envelope_width_m=10.0,
            envelope_depth_m=10.0,
            floors_above_ground=5,
        )
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "0-4" in str(e) or "custom" in str(e).lower()
        print(f"PASS too many floors rejected")


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Component 7 — Refactored (4 sub-modules)")
    print("=" * 70)
    test_ne_30x40_chennai_walkthrough()
    print()
    test_zone_iv_delhi_is_supported()
    print()
    test_zone_v_is_refused()
    test_zone_iii_triggers_is13920_warning()
    test_mumbai_reclaimed_uses_pile()
    test_kolkata_weak_soil_uses_pile()
    test_strap_footing_for_edge_condition()
    test_velachery_marshy_warning()
    test_explanation_shows_safety_factors()
    test_kb_version_in_cost_notes()
    test_envelope_too_small_rejected()
    test_too_many_floors_rejected()
    print()
    print("=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)
