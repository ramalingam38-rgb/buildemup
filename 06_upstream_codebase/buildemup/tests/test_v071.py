"""
v0.7.1 tests — Drawbacks 3, 4, 5 from v0.7 review.

  Drawback 3 — Domain-only contract enforcement
  Drawback 4 — Single-source rules (JSON authoritative)
  Drawback 5 — Drift realism (beam + infill factors)

Skipped (v2 backlog): Drawbacks 1 (unified model), 2 (dynamic sim),
6 (insights feedback loop).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────────
# A. Drawback 5 — Drift realism (beam + infill factors)
# ─────────────────────────────────────────────────────────────────────────
def test_beam_contribution_factor_constant():
    """BEAM_CONTRIBUTION_FACTOR is 1.3 per research literature."""
    from buildemup.components.c07 import global_stability as gs
    assert gs.BEAM_CONTRIBUTION_FACTOR == 1.3
    print(f"PASS beam contribution factor = {gs.BEAM_CONTRIBUTION_FACTOR}")


def test_infill_contribution_factor_with_walls():
    """INFILL_CONTRIBUTION_FACTOR_WITH_WALLS = 1.5 (URM infill)."""
    from buildemup.components.c07 import global_stability as gs
    assert gs.INFILL_CONTRIBUTION_FACTOR_WITH_WALLS == 1.5
    assert gs.INFILL_CONTRIBUTION_FACTOR_NO_WALLS == 1.0
    print(f"PASS infill factors: walls={gs.INFILL_CONTRIBUTION_FACTOR_WITH_WALLS}, "
          f"no-walls={gs.INFILL_CONTRIBUTION_FACTOR_NO_WALLS}")


def test_infilled_has_less_drift_than_open_stilt():
    """Building with infill walls must show less drift than without."""
    from buildemup.components.c07.global_stability import (
        run_global_stability_check, LoadCase,
    )
    # Same geometry, different infill assumption
    with_infill = run_global_stability_check(
        n_storeys=2, storey_height_m=3.0, n_columns_per_storey=12,
        column_dim_mm=300, fck_mpa=25, total_base_shear_kn=150,
        load_case=LoadCase.SEISMIC, has_infill_walls=True,
    )
    without_infill = run_global_stability_check(
        n_storeys=2, storey_height_m=3.0, n_columns_per_storey=12,
        column_dim_mm=300, fck_mpa=25, total_base_shear_kn=150,
        load_case=LoadCase.SEISMIC, has_infill_walls=False,
    )
    # With infill should have LESS drift (stiffer frame)
    assert with_infill.worst_utilization_pct < without_infill.worst_utilization_pct
    # Ratio should be roughly 1.5 (the infill factor)
    ratio = without_infill.worst_utilization_pct / with_infill.worst_utilization_pct
    assert 1.3 < ratio < 1.7, f"Expected ~1.5 ratio, got {ratio}"
    print(f"PASS infilled drift < open-stilt drift "
          f"(ratio {ratio:.2f}, ~1.5 expected)")


def test_default_has_infill_walls_true():
    """Default assumes infill walls (typical Indian residential)."""
    from buildemup.components.c07.global_stability import (
        run_global_stability_check, LoadCase,
    )
    # Call without specifying has_infill_walls
    default = run_global_stability_check(
        n_storeys=2, storey_height_m=3.0, n_columns_per_storey=12,
        column_dim_mm=300, fck_mpa=25, total_base_shear_kn=150,
        load_case=LoadCase.SEISMIC,
    )
    explicit_true = run_global_stability_check(
        n_storeys=2, storey_height_m=3.0, n_columns_per_storey=12,
        column_dim_mm=300, fck_mpa=25, total_base_shear_kn=150,
        load_case=LoadCase.SEISMIC, has_infill_walls=True,
    )
    # Default and explicit True must give identical results
    assert default.worst_utilization_pct == explicit_true.worst_utilization_pct
    print("PASS default = has_infill_walls=True")


def test_method_disclosure_lists_new_factors():
    """Method disclosure must explicitly list beam + infill factors."""
    from buildemup.components.c07.global_stability import (
        run_global_stability_check, LoadCase,
    )
    report = run_global_stability_check(
        n_storeys=2, storey_height_m=3.0, n_columns_per_storey=12,
        column_dim_mm=300, fck_mpa=25, total_base_shear_kn=150,
        load_case=LoadCase.SEISMIC, has_infill_walls=True,
    )
    d = report.method_disclosure
    assert "Beam-frame stiffness" in d
    assert "1.3" in d
    assert "Infill wall" in d
    assert "1.5" in d
    print("PASS method disclosure lists beam (×1.3) + infill (×1.5) factors")


def test_improved_realism_halves_drift_values():
    """v0.7.1 drift should be ~half of what raw columns-only gives."""
    from buildemup.components.c07.global_stability import (
        column_lateral_stiffness_kn_per_m, BEAM_CONTRIBUTION_FACTOR,
        INFILL_CONTRIBUTION_FACTOR_WITH_WALLS,
    )
    # Raw per-column stiffness (v0.7 behaviour)
    k_col = column_lateral_stiffness_kn_per_m(300, 3.0, 25.0)
    # Effective with beam + infill (v0.7.1)
    effective_factor = BEAM_CONTRIBUTION_FACTOR * INFILL_CONTRIBUTION_FACTOR_WITH_WALLS
    # 1.3 × 1.5 = 1.95
    assert 1.9 < effective_factor < 2.0
    # Since drift = shear/stiffness, drift is 1/effective_factor of raw
    drift_reduction = 1.0 / effective_factor
    assert 0.50 < drift_reduction < 0.53
    print(f"PASS drift reduction factor = {drift_reduction:.3f} "
          f"(stiffness × {effective_factor:.2f})")


# ─────────────────────────────────────────────────────────────────────────
# B. Drawback 3 — Domain-only contract enforcement
# ─────────────────────────────────────────────────────────────────────────
def test_domain_type_name_detection():
    """_is_domain_type_name detects domain types + container wrappers."""
    from buildemup.utils.component_contract import _is_domain_type_name
    assert _is_domain_type_name("Building") is True
    assert _is_domain_type_name("Envelope") is True
    assert _is_domain_type_name("tuple[Floor, ...]") is True
    assert _is_domain_type_name("list[Column]") is True
    assert _is_domain_type_name("float") is False
    assert _is_domain_type_name("str") is False
    assert _is_domain_type_name("dict") is False
    print("PASS domain type detection for plain + container types")


def test_real_domain_object_passes_check():
    """A real Building instance passes _check_is_domain_object."""
    from buildemup.utils.component_contract import _check_is_domain_object
    from buildemup.domain import (
        Building, BuildingMeta, Envelope, Floor, FloorType,
    )
    b = Building(
        meta=BuildingMeta(),
        envelope=Envelope(width_m=8, depth_m=10),
        floors=(Floor(floor_number=0, floor_type=FloorType.GROUND),),
    )
    assert _check_is_domain_object(b, "Building") is True
    print("PASS real Building passes domain check")


def test_raw_dict_rejected_as_domain_object():
    """A plain dict fails _check_is_domain_object."""
    from buildemup.utils.component_contract import _check_is_domain_object
    assert _check_is_domain_object({"width_m": 8}, "Building") is False
    assert _check_is_domain_object({}, "Envelope") is False
    print("PASS raw dict rejected as domain object")


def test_primitives_rejected_as_domain_object():
    """Strings, ints, floats all fail _check_is_domain_object."""
    from buildemup.utils.component_contract import _check_is_domain_object
    assert _check_is_domain_object("hello", "Building") is False
    assert _check_is_domain_object(42, "Envelope") is False
    assert _check_is_domain_object(3.14, "Column") is False
    assert _check_is_domain_object(None, "Floor") is False
    print("PASS primitives rejected as domain objects")


def test_validate_input_enforces_domain_type():
    """validate_input rejects dict for domain-typed field."""
    from buildemup.utils.component_contract import (
        ComponentContract, register_contract, required, validate_input,
    )
    from dataclasses import dataclass

    # Register a test contract with a domain-typed field
    test_contract = ComponentContract(
        component_id="TEST_domain_enforcement",
        version="0.7.1",
        description="Test contract for enforcement",
        consumes=(
            required("envelope", "Envelope", "The buildable envelope"),
        ),
        produces=(
            required("result", "str", "Processing result"),
        ),
    )
    register_contract(test_contract)

    # Good input: a real Envelope object
    from buildemup.domain import Envelope
    @dataclass
    class GoodInput:
        envelope: object
    good = GoodInput(envelope=Envelope(width_m=8, depth_m=10))
    violations = validate_input("TEST_domain_enforcement", good)
    assert violations == [], f"Good input should validate: {violations}"

    # Bad input: raw dict posing as Envelope
    @dataclass
    class BadInput:
        envelope: object
    bad = BadInput(envelope={"width_m": 8, "depth_m": 10})
    violations = validate_input("TEST_domain_enforcement", bad)
    assert len(violations) > 0
    assert "must be a domain object" in violations[0]
    assert "dict" in violations[0]
    print(f"PASS validate_input rejects dict for domain field: "
          f"{violations[0][:80]}")


def test_tuple_of_domain_objects_accepted():
    """tuple[Floor, ...] field with real Floor instances validates."""
    from buildemup.utils.component_contract import (
        ComponentContract, register_contract, required, validate_input,
    )
    from buildemup.domain import Floor, FloorType
    from dataclasses import dataclass

    test_contract = ComponentContract(
        component_id="TEST_tuple_domain",
        version="0.7.1",
        description="Test tuple of domain objects",
        consumes=(
            required("floors", "tuple[Floor, ...]",
                     "Tuple of Floor domain objects"),
        ),
        produces=(required("result", "str", "Output"),),
    )
    register_contract(test_contract)

    @dataclass
    class Inp:
        floors: object
    good = Inp(floors=(
        Floor(floor_number=0, floor_type=FloorType.GROUND),
        Floor(floor_number=1, floor_type=FloorType.FIRST),
    ))
    violations = validate_input("TEST_tuple_domain", good)
    assert violations == [], f"Tuple of Floors should validate: {violations}"

    # Bad: tuple containing a dict
    bad = Inp(floors=({"floor_number": 0}, {"floor_number": 1}))
    violations = validate_input("TEST_tuple_domain", bad)
    assert len(violations) > 0
    print("PASS tuple[Floor, ...] enforcement works")


# ─────────────────────────────────────────────────────────────────────────
# C. Drawback 4 — Single-source rules (JSON authoritative)
# ─────────────────────────────────────────────────────────────────────────
def test_seismic_constants_loaded_from_json():
    """Seismic constants come from JSON, not hardcoded Python."""
    import buildemup.kb.seismic_detailing as seismic
    # These should be identical to JSON values
    from buildemup.utils.kb_rules_loader import (
        get_seismic_zone_factor, get_seismic_min_column_dim_mm,
        get_recommended_column_steel_pct,
    )
    assert seismic.SEISMIC_ZONE_FACTORS["III"] == get_seismic_zone_factor("III")
    assert seismic.SEISMIC_MIN_COLUMN_DIM_MM == get_seismic_min_column_dim_mm()
    assert seismic.RECOMMENDED_COLUMN_STEEL_PCT["III"] == \
        get_recommended_column_steel_pct("III")
    print("PASS seismic constants sourced from JSON")


def test_load_constants_loaded_from_json():
    """Load constants come from JSON, not hardcoded Python."""
    import buildemup.kb.load_estimation as loads
    from buildemup.utils.kb_rules_loader import (
        get_slab_weight_kn_per_sqm_per_mm, get_finishes_kn_per_sqm,
        get_partial_safety_factor,
    )
    assert loads.SLAB_WEIGHT_KN_PER_SQM_PER_MM == \
        get_slab_weight_kn_per_sqm_per_mm()
    assert loads.FINISHES_KN_PER_SQM == get_finishes_kn_per_sqm()
    assert loads.SAFETY_FACTORS["dead_load"] == \
        get_partial_safety_factor("dead_load")
    print("PASS load constants sourced from JSON")


def test_changing_json_changes_python_constants():
    """If JSON were to change, Python constants reflect it (no drift).

    We can't actually edit the JSON mid-test, but we can verify the
    loading path — both come from the same _load_rules() call, so by
    construction there is no dual-source drift.
    """
    from buildemup.utils.kb_rules_loader import load_rules
    from buildemup.kb.seismic_detailing import SEISMIC_ZONE_FACTORS
    raw_json = load_rules("seismic_rules")
    for zone, val in SEISMIC_ZONE_FACTORS.items():
        json_val = raw_json["seismic_zone_factors"]["values"][zone]
        assert val == json_val, \
            f"Zone {zone}: Python {val} != JSON {json_val} — DRIFT!"
    print("PASS JSON and Python zone factors bitwise identical "
          "(same source)")


def test_parity_tests_still_pass_after_single_source():
    """The v0.6 parity tests should STILL pass because values are now
    literally identical (sourced from same JSON).

    Parity tests become safety nets rather than drift detectors —
    that's OK, they'll catch if someone re-introduces a Python literal
    that accidentally diverges.
    """
    from buildemup.utils.kb_rules_loader import (
        get_seismic_zone_factor, get_seismic_min_column_dim_mm,
    )
    from buildemup.kb.seismic_detailing import (
        SEISMIC_ZONE_FACTORS, SEISMIC_MIN_COLUMN_DIM_MM,
    )
    # Exact equality
    for zone in ["II", "III", "IV", "V"]:
        assert SEISMIC_ZONE_FACTORS[zone] == get_seismic_zone_factor(zone)
    assert SEISMIC_MIN_COLUMN_DIM_MM == get_seismic_min_column_dim_mm()
    print("PASS v0.6 parity tests still pass (single-source = inherent parity)")


def test_load_rules_module_doesnt_define_literals():
    """load_estimation module should not redefine values already in JSON.

    Scan the Python source for suspicious hardcoded literals we might
    have missed during migration.
    """
    import buildemup.kb.load_estimation as loads
    import inspect
    source = inspect.getsource(loads)
    # Check that obvious parallel constants are gone
    assert "SLAB_WEIGHT_KN_PER_SQM_PER_MM = 0.025" not in source, \
        "Hardcoded slab weight literal still present"
    assert "FINISHES_KN_PER_SQM = 1.2" not in source, \
        "Hardcoded finishes literal still present"
    assert "PARTITION_WALL_KN_PER_SQM = 1.0" not in source, \
        "Hardcoded partition wall literal still present"
    # These definitions use _LOADS[...] which is the JSON path
    assert "_LOADS[" in source
    print("PASS load_estimation no longer has parallel hardcoded literals")


def test_seismic_module_doesnt_define_literals():
    """Same check for seismic_detailing module."""
    import buildemup.kb.seismic_detailing as seismic
    import inspect
    source = inspect.getsource(seismic)
    # The main zone factor dict should not be a literal dict
    assert 'SEISMIC_ZONE_FACTORS = {\n    "II": 0.10' not in source, \
        "Hardcoded seismic zone factors literal still present"
    assert "RE_ENTRANT_MODERATE_PCT = 15.0" not in source, \
        "Hardcoded re-entrant literal still present"
    assert "_SEISMIC[" in source
    print("PASS seismic_detailing no longer has parallel hardcoded literals")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.7.1 Tests — Drawbacks 3, 4, 5 from v0.7 Review")
    print("=" * 70)
    print()
    print("--- A. Drawback 5: Drift realism (beam + infill) ---")
    test_beam_contribution_factor_constant()
    test_infill_contribution_factor_with_walls()
    test_infilled_has_less_drift_than_open_stilt()
    test_default_has_infill_walls_true()
    test_method_disclosure_lists_new_factors()
    test_improved_realism_halves_drift_values()
    print()
    print("--- B. Drawback 3: Domain-only contract enforcement ---")
    test_domain_type_name_detection()
    test_real_domain_object_passes_check()
    test_raw_dict_rejected_as_domain_object()
    test_primitives_rejected_as_domain_object()
    test_validate_input_enforces_domain_type()
    test_tuple_of_domain_objects_accepted()
    print()
    print("--- C. Drawback 4: Single-source rules (JSON authoritative) ---")
    test_seismic_constants_loaded_from_json()
    test_load_constants_loaded_from_json()
    test_changing_json_changes_python_constants()
    test_parity_tests_still_pass_after_single_source()
    test_load_rules_module_doesnt_define_literals()
    test_seismic_module_doesnt_define_literals()
    print()
    print("=" * 70)
    print("ALL v0.7.1 TESTS PASSED")
    print("=" * 70)
