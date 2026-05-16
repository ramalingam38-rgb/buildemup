"""
v0.6 Phase 2 Part 3 — ComponentContract enforcement.

Ensures every shipping component has a registered ComponentContract.
This is the "CI rule" per the v0.5 review — prevents future components
from drifting in their assumptions silently.

Discovery rule:
  Top-level component modules in /buildemup/components/c{NN}_*.py
  must each register a contract during module import.

If a new component file appears without registering a contract, this
test fails with a clear message telling the developer what to add.
"""
import sys
import os
import importlib
import re
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.utils.component_contract import (
    all_contracts, get_contract, ComponentContract,
    validate_input, validate_output, FieldSpec,
)


# ─── Component discovery ─────────────────────────────────────────────────
COMPONENTS_DIR = Path(__file__).parent.parent / "components"
COMPONENT_FILE_PATTERN = re.compile(r"^c(\d{2})_(.+)\.py$")


def discover_top_level_component_modules() -> list[tuple[str, str]]:
    """Find all top-level component modules.

    A 'top-level component' is a file matching c{NN}_{name}.py at the
    top of /components/ (not inside a sub-package like /components/c07/).

    Returns list of (component_id, module_path) tuples.
    """
    found = []
    for entry in COMPONENTS_DIR.iterdir():
        if entry.is_file():
            m = COMPONENT_FILE_PATTERN.match(entry.name)
            if m:
                num = m.group(1)
                name = m.group(2)
                component_id = f"C{num}_{name}"
                module_path = f"buildemup.components.{entry.stem}"
                found.append((component_id, module_path))
    return sorted(found)


def import_component_module(module_path: str):
    """Import a component module so its contract registration runs."""
    return importlib.import_module(module_path)


# ─── Tests ───────────────────────────────────────────────────────────────
def test_at_least_one_component_exists():
    """Sanity: there is at least one component module to enforce against."""
    components = discover_top_level_component_modules()
    assert len(components) > 0, \
        "No top-level component files found in /components/. Discovery broken?"
    print(f"PASS discovered {len(components)} top-level component(s): "
          f"{[c[0] for c in components]}")


def test_every_component_imports_cleanly():
    """Importing a component must not raise (module-level errors are bugs)."""
    for component_id, module_path in discover_top_level_component_modules():
        try:
            import_component_module(module_path)
        except Exception as e:
            assert False, f"{component_id} import failed: {e}"
    print(f"PASS all components import without error")


def test_every_component_has_registered_contract():
    """Every top-level component must register a ComponentContract.

    This is the CI rule. If a new component ships without registering
    a contract, this test fails with a helpful message telling the
    developer what to add.
    """
    components = discover_top_level_component_modules()
    # Force imports first so any module-level register_contract() calls run
    for _, module_path in components:
        import_component_module(module_path)

    registered = all_contracts()
    missing = []
    for component_id, module_path in components:
        if component_id not in registered:
            missing.append((component_id, module_path))

    if missing:
        msg_lines = [
            "",
            "❌ ComponentContract MISSING for the following component(s):",
            "",
        ]
        for component_id, module_path in missing:
            msg_lines.append(f"  • {component_id} (in {module_path})")
        msg_lines.extend([
            "",
            "EVERY top-level component MUST register a ComponentContract.",
            "This catches assumption drift between components.",
            "",
            "To fix, add this to the bottom of the component module:",
            "",
            "    from buildemup.utils.component_contract import (",
            "        ComponentContract, register_contract, required, optional,",
            "    )",
            "    _CONTRACT = ComponentContract(",
            "        component_id='C07_structural_grid',  # use your component_id",
            "        version='0.6',",
            "        description='What this component does',",
            "        consumes=(",
            "            required('field_name', 'type', 'description', '>=0'),",
            "            ...",
            "        ),",
            "        produces=(",
            "            required('output_field', 'type', 'description'),",
            "            ...",
            "        ),",
            "    )",
            "    register_contract(_CONTRACT)",
            "",
        ])
        assert False, "\n".join(msg_lines)

    print(f"PASS all {len(components)} component(s) have registered contracts")


def test_contract_consumes_and_produces_non_empty():
    """A registered contract must declare at least one consumed AND produced field.

    A component that consumes nothing or produces nothing is suspicious —
    almost certainly an incomplete contract.
    """
    components = discover_top_level_component_modules()
    for _, module_path in components:
        import_component_module(module_path)

    issues = []
    for component_id, contract in all_contracts().items():
        if len(contract.consumes) == 0:
            issues.append(f"{component_id} declares no consumed fields")
        if len(contract.produces) == 0:
            issues.append(f"{component_id} declares no produced fields")

    assert not issues, \
        f"Contract declarations incomplete:\n  " + "\n  ".join(issues)
    print(f"PASS all contracts declare both consumed AND produced fields")


def test_field_spec_has_type_name():
    """Every FieldSpec in every contract must have a non-empty type_name.

    Type names matter for downstream consumers and documentation.
    A FieldSpec with empty type_name is unusable.
    """
    components = discover_top_level_component_modules()
    for _, module_path in components:
        import_component_module(module_path)

    for component_id, contract in all_contracts().items():
        for spec in list(contract.consumes) + list(contract.produces):
            assert spec.type_name and spec.type_name.strip(), \
                f"{component_id}: FieldSpec '{spec.name}' has empty type_name"
    print(f"PASS all FieldSpecs have non-empty type_name")


def test_contract_can_be_documented_for_each_component():
    """format_for_docs() must work for every registered contract."""
    components = discover_top_level_component_modules()
    for _, module_path in components:
        import_component_module(module_path)

    for component_id, contract in all_contracts().items():
        docs = contract.format_for_docs()
        assert component_id in docs
        assert "INPUT (consumes)" in docs
        assert "OUTPUT (produces)" in docs
    print(f"PASS contract docs render for all {len(all_contracts())} components")


def test_registered_contract_validates_clean_for_real_input():
    """Component 7's real input dataclass must validate clean against its contract."""
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    violations = validate_input("C07_structural_grid", inp)
    assert violations == [], f"Real input violations: {violations}"
    print(f"PASS real Component 7 input validates clean against contract")


def test_registered_contract_validates_clean_for_real_output():
    """Component 7's real output must validate clean against its contract."""
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    violations = validate_output("C07_structural_grid", result)
    assert violations == [], f"Real output violations: {violations}"
    print(f"PASS real Component 7 output validates clean against contract")


# ─── Domain layer tests ──────────────────────────────────────────────────
def test_domain_imports_cleanly():
    """Domain layer should import without errors."""
    from buildemup.domain import (
        Building, BuildingMeta, Envelope, PlotOrientation,
        Floor, FloorType, Column, ColumnLocation, DomainGrid,
    )
    print(f"PASS domain layer imports cleanly")


def test_envelope_validation():
    """Envelope rejects too-small dimensions."""
    from buildemup.domain import Envelope
    try:
        Envelope(width_m=2.0, depth_m=10.0)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "too small" in str(e).lower()
        print(f"PASS Envelope rejects too-small width")


def test_envelope_aspect_ratio_calculation():
    """aspect_ratio = long edge / short edge."""
    from buildemup.domain import Envelope
    env = Envelope(width_m=15.0, depth_m=5.0)
    assert env.aspect_ratio == 3.0
    env = Envelope(width_m=5.0, depth_m=20.0)  # depth is long
    assert env.aspect_ratio == 4.0
    print(f"PASS Envelope aspect ratio computed correctly")


def test_envelope_re_entrant_corner_subtracts_from_net_area():
    """Net area = gross area - re-entrant corner area."""
    from buildemup.domain import Envelope
    env = Envelope(width_m=10.0, depth_m=10.0,
                   re_entrant_x_m=2.0, re_entrant_y_m=3.0)
    assert env.area_sqm == 100.0
    assert env.net_area_sqm == 100.0 - 6.0  # 94 sqm
    print(f"PASS net area = gross - re-entrant corner area")


def test_building_floor_count_logic():
    """Building counts floors-above-ground correctly (excludes stilt + terrace)."""
    from buildemup.domain import (
        Building, BuildingMeta, Envelope, Floor, FloorType,
    )
    floors = (
        Floor(floor_number=0, floor_type=FloorType.STILT_PARKING),
        Floor(floor_number=1, floor_type=FloorType.GROUND),
        Floor(floor_number=2, floor_type=FloorType.FIRST),
        Floor(floor_number=3, floor_type=FloorType.TERRACE),
    )
    b = Building(
        meta=BuildingMeta(),
        envelope=Envelope(width_m=8.0, depth_m=10.0),
        floors=floors,
    )
    assert b.floors_above_ground == 2  # GROUND + FIRST only
    assert b.has_stilt_parking is True
    assert b.has_terrace_access is True
    print(f"PASS Building floor count: above_ground={b.floors_above_ground}")


def test_building_with_grid_is_immutable_update():
    """with_grid returns a new Building, doesn't mutate original."""
    from buildemup.domain import (
        Building, BuildingMeta, Envelope, Floor, FloorType, DomainGrid,
    )
    floors = (Floor(floor_number=0, floor_type=FloorType.GROUND),)
    b = Building(
        meta=BuildingMeta(),
        envelope=Envelope(width_m=8.0, depth_m=10.0),
        floors=floors,
    )
    grid = DomainGrid(n_cols=3, n_rows=3, bay_x_m=(4.0, 4.0), bay_y_m=(3.0, 3.0))
    b2 = b.with_grid(grid)
    assert b.grid is None       # Original unchanged
    assert b2.grid is grid      # New one has the grid
    assert b is not b2          # Different objects
    print(f"PASS Building.with_grid() is immutable update")


def test_floor_default_live_load_per_is_875():
    """Floor uses default live load per IS 875 Part 2 by floor type."""
    from buildemup.domain import Floor, FloorType
    # Residential: 2.0 kN/m²
    f = Floor(floor_number=1, floor_type=FloorType.GROUND)
    assert f.effective_live_load_knsqm == 2.0
    # Stilt parking: 4.0 kN/m² (passenger car parking per IS 875 Part 2)
    f = Floor(floor_number=0, floor_type=FloorType.STILT_PARKING)
    assert f.effective_live_load_knsqm == 4.0
    # Override
    f = Floor(floor_number=1, floor_type=FloorType.GROUND, live_load_knsqm=3.5)
    assert f.effective_live_load_knsqm == 3.5
    print(f"PASS Floor default live loads match IS 875 Part 2")


def test_column_validation_rejects_below_min_size():
    """Column with cross-section < 230mm should raise."""
    from buildemup.domain import Column
    try:
        Column(column_id="C1", x_m=0, y_m=0, cross_section_mm=200)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "230mm" in str(e)
        print(f"PASS Column rejects size below 230mm minimum")


def test_grid_longest_bay_drives_sensitivity():
    """DomainGrid.longest_bay_m gives the longest single span — used for sensitivity."""
    from buildemup.domain import DomainGrid
    grid = DomainGrid(
        n_cols=3, n_rows=4,
        bay_x_m=(3.5, 4.2),       # max in X = 4.2
        bay_y_m=(3.0, 3.6, 3.0),  # max in Y = 3.6
    )
    assert grid.longest_bay_m == 4.2
    print(f"PASS DomainGrid.longest_bay_m = {grid.longest_bay_m}m (max of all bays)")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.6 Phase 2 Parts 2+3 — Domain Layer + Contract Enforcement")
    print("=" * 70)
    print()
    print("--- Component contract enforcement ---")
    test_at_least_one_component_exists()
    test_every_component_imports_cleanly()
    test_every_component_has_registered_contract()
    test_contract_consumes_and_produces_non_empty()
    test_field_spec_has_type_name()
    test_contract_can_be_documented_for_each_component()
    test_registered_contract_validates_clean_for_real_input()
    test_registered_contract_validates_clean_for_real_output()
    print()
    print("--- Domain layer ---")
    test_domain_imports_cleanly()
    test_envelope_validation()
    test_envelope_aspect_ratio_calculation()
    test_envelope_re_entrant_corner_subtracts_from_net_area()
    test_building_floor_count_logic()
    test_building_with_grid_is_immutable_update()
    test_floor_default_live_load_per_is_875()
    test_column_validation_rejects_below_min_size()
    test_grid_longest_bay_drives_sensitivity()
    print()
    print("=" * 70)
    print("ALL PHASE 2 PARTS 2+3 TESTS PASSED")
    print("=" * 70)
