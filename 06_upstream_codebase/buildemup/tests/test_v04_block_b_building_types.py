"""
v0.4 Block B tests — building type architecture.

Tests:
  - Default building type (residential single-family) works as before
  - Stubbed building types (commercial, educational, etc.) refused gracefully
  - Per-type max floors enforced
  - Importance factor + IS 13920 mandate flow correctly from registry
  - Building type shown in explain output
  - Registry coverage matches scope decisions
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.components.c07_structural_grid import (
    StructuralGridEngine,
    StructuralGridInput,
)
from buildemup.kb.building_types import (
    BuildingType,
    BUILDING_TYPE_REGISTRY,
    get_spec,
    is_fully_implemented,
    fully_implemented_types,
    stubbed_types,
    supported_types,
)
from buildemup.utils.errors import UnsupportedConfigurationError


# ─── Backwards compatibility ─────────────────────────────────────────────
def test_default_is_residential_single_family():
    """Default building_type should be RESIDENTIAL_SINGLE_FAMILY."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    assert inp.building_type == BuildingType.RESIDENTIAL_SINGLE_FAMILY
    print(f"PASS default building_type = RESIDENTIAL_SINGLE_FAMILY")


def test_residential_works_unchanged():
    """Residential single-family must work exactly as before v0.4."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
        building_type=BuildingType.RESIDENTIAL_SINGLE_FAMILY,
    )
    result = StructuralGridEngine().execute(inp)
    assert result.cost.exact_value > 0
    assert result.structure.column_size_mm >= 230
    print(f"PASS residential single-family produces valid output: "
          f"₹{result.cost.exact_value/100_000:.2f}L")


# ─── Stubbed types refused gracefully ────────────────────────────────────
def test_commercial_office_refused_gracefully():
    """Commercial office is stubbed — must refuse with helpful message."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=12.0,
        floors_above_ground=2, city="bangalore", seismic_zone="II",
        building_type=BuildingType.COMMERCIAL_OFFICE,
    )
    try:
        StructuralGridEngine().execute(inp)
        assert False, "Expected refusal for commercial office"
    except UnsupportedConfigurationError as e:
        assert "office" in e.user_message.lower() or "commercial" in e.user_message.lower()
        assert "roadmap" in e.user_message.lower() or "not yet" in e.user_message.lower()
        assert e.suggested_action is not None
        print(f"PASS commercial office refused gracefully")


def test_educational_refused_gracefully():
    """Educational (school) is stubbed — must refuse with helpful message."""
    inp = StructuralGridInput(
        envelope_width_m=12.0, envelope_depth_m=18.0,
        floors_above_ground=2, city="hyderabad", seismic_zone="II",
        building_type=BuildingType.EDUCATIONAL,
    )
    try:
        StructuralGridEngine().execute(inp)
        assert False, "Expected refusal for educational"
    except UnsupportedConfigurationError as e:
        # Educational has importance_factor 1.5 — the user message mentions
        # the building type, not the technical detail
        assert "school" in e.user_message.lower() or "educational" in e.user_message.lower()
        print(f"PASS educational building refused gracefully")


def test_healthcare_refused_gracefully():
    """Healthcare is stubbed — important building requires special design."""
    inp = StructuralGridInput(
        envelope_width_m=15.0, envelope_depth_m=20.0,
        floors_above_ground=2, city="chennai", seismic_zone="II",
        building_type=BuildingType.HEALTHCARE,
    )
    try:
        StructuralGridEngine().execute(inp)
        assert False, "Expected refusal for healthcare"
    except UnsupportedConfigurationError:
        print(f"PASS healthcare building refused gracefully")


# ─── Per-type max floors enforced ────────────────────────────────────────
def test_max_floors_enforced_per_type():
    """If user requests more floors than max for type, refuse helpfully."""
    # Note: this is caught by __post_init__ validation in StructuralGridInput
    # before reaching the execute() per-type check. Either is fine.
    try:
        inp = StructuralGridInput(
            envelope_width_m=10.0, envelope_depth_m=10.0,
            floors_above_ground=10,
            city="chennai", seismic_zone="II",
            building_type=BuildingType.RESIDENTIAL_SINGLE_FAMILY,
        )
        StructuralGridEngine().execute(inp)
        assert False, "Expected refusal for G+10"
    except (UnsupportedConfigurationError, ValueError) as e:
        msg = str(e).lower()
        assert "floor" in msg or "g+" in msg or "supports" in msg or "0-4" in msg
        print(f"PASS G+10 refused")


# ─── Registry coverage matches scope decisions ───────────────────────────
def test_registry_includes_all_supported_types():
    """All 8 supported building types must be in the registry."""
    expected = {
        BuildingType.RESIDENTIAL_SINGLE_FAMILY,
        BuildingType.RESIDENTIAL_MULTI_FAMILY,
        BuildingType.COMMERCIAL_OFFICE,
        BuildingType.RETAIL,
        BuildingType.MIXED_USE,
        BuildingType.EDUCATIONAL,
        BuildingType.HEALTHCARE,
        BuildingType.HOSPITALITY,
    }
    actual = set(BUILDING_TYPE_REGISTRY.keys())
    assert actual == expected, f"Registry mismatch: {actual ^ expected}"
    print(f"PASS registry covers all 8 expected types")


def test_industrial_warehouse_not_in_registry():
    """Industrial and warehouse must NOT be in the registry per scope."""
    type_names = [bt.value for bt in BUILDING_TYPE_REGISTRY.keys()]
    assert "industrial" not in type_names
    assert "warehouse" not in type_names
    print(f"PASS industrial/warehouse correctly excluded")


def test_only_residential_single_family_fully_implemented():
    """In v0.4, only residential_single_family is FULLY_IMPLEMENTED."""
    fully = fully_implemented_types()
    assert fully == [BuildingType.RESIDENTIAL_SINGLE_FAMILY]
    print(f"PASS only residential_single_family is FULLY_IMPLEMENTED in v0.4")


def test_seven_types_are_stubbed():
    """7 of 8 types should be STUBBED (architecturally supported)."""
    stubbed = stubbed_types()
    assert len(stubbed) == 7
    print(f"PASS {len(stubbed)} types architecturally supported but stubbed")


# ─── Importance factor + IS 13920 mandate from registry ──────────────────
def test_educational_has_importance_factor_1_5():
    """Educational is an 'important building' per IS 1893 — factor 1.5."""
    spec = get_spec(BuildingType.EDUCATIONAL)
    assert spec.importance_factor == 1.5
    assert spec.is13920_mandatory_all_zones is True
    print(f"PASS educational has importance_factor 1.5 + IS 13920 mandatory")


def test_healthcare_has_importance_factor_1_5():
    """Healthcare is also 'important' — same treatment as educational."""
    spec = get_spec(BuildingType.HEALTHCARE)
    assert spec.importance_factor == 1.5
    assert spec.is13920_mandatory_all_zones is True
    print(f"PASS healthcare has importance_factor 1.5 + IS 13920 mandatory")


def test_residential_has_normal_importance():
    """Residential is normal importance (1.0)."""
    spec = get_spec(BuildingType.RESIDENTIAL_SINGLE_FAMILY)
    assert spec.importance_factor == 1.0
    assert spec.is13920_mandatory_all_zones is False
    print(f"PASS residential has normal importance factor")


# ─── Building type shown in explain output ───────────────────────────────
def test_building_type_shown_in_explain():
    """explain() must show what building type was designed for."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "Building type:" in explanation
    assert "single family" in explanation.lower() or "single-family" in explanation.lower()
    print(f"PASS building type shown in explain()")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.4 Block B Tests — Building Type Architecture")
    print("=" * 70)
    print()
    print("--- Backwards compatibility ---")
    test_default_is_residential_single_family()
    test_residential_works_unchanged()
    print()
    print("--- Stubbed types refused gracefully ---")
    test_commercial_office_refused_gracefully()
    test_educational_refused_gracefully()
    test_healthcare_refused_gracefully()
    print()
    print("--- Per-type max floors ---")
    test_max_floors_enforced_per_type()
    print()
    print("--- Registry scope ---")
    test_registry_includes_all_supported_types()
    test_industrial_warehouse_not_in_registry()
    test_only_residential_single_family_fully_implemented()
    test_seven_types_are_stubbed()
    print()
    print("--- Importance factor + IS 13920 mandate ---")
    test_educational_has_importance_factor_1_5()
    test_healthcare_has_importance_factor_1_5()
    test_residential_has_normal_importance()
    print()
    print("--- Display ---")
    test_building_type_shown_in_explain()
    print()
    print("=" * 70)
    print("ALL BLOCK B TESTS PASSED")
    print("=" * 70)
