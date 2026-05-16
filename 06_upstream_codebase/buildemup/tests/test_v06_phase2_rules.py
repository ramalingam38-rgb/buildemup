"""
v0.6 Phase 2 Part 1 tests — config-driven rules parity + loader.

The single most important test file in v0.6: verifies that the JSON
values in kb_rules/seismic_rules.json EXACTLY match the existing
Python constants in kb/seismic_detailing.py.

If parity ever breaks, one of two things happened:
  1. Someone updated the Python constant without updating the JSON.
  2. Someone updated the JSON without updating the Python.

Either is bad. The test catches it before the regression ships.

Also covers:
  - Schema validation catches malformed JSON
  - Loader caching works
  - All convenience accessors return correct types
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.utils.kb_rules_loader import (
    load_rules, clear_cache, RuleSchemaError,
    get_seismic_zone_factor, get_is13920_required_zones,
    get_seismic_min_column_dim_mm, get_recommended_column_steel_pct,
    get_re_entrant_corner_limits, get_aspect_ratio_limits,
    get_short_column_slenderness_limit, get_column_steel_limits_pct,
)

# Import the OLD Python constants so we can test parity
from buildemup.kb.seismic_detailing import (
    SEISMIC_ZONE_FACTORS,
    IMPORTANCE_FACTOR_RESIDENTIAL,
    RESPONSE_REDUCTION_SPECIAL_MRF,
    RESPONSE_REDUCTION_ORDINARY_MRF,
    SEISMIC_MIN_COLUMN_DIM_MM,
    COLUMN_STEEL_MIN_PCT,
    COLUMN_STEEL_MAX_PCT,
    RECOMMENDED_COLUMN_STEEL_PCT,
    RE_ENTRANT_MODERATE_PCT,
    RE_ENTRANT_SEVERE_PCT,
    ASPECT_MODERATE_LIMIT,
    ASPECT_SEVERE_LIMIT,
    SHORT_COLUMN_SLENDERNESS_LIMIT,
    REGULARITY_REGULAR,
    REGULARITY_MODERATE,
    REGULARITY_SEVERE,
    is13920_required,
)


# ─── Parity tests (JSON values MUST match Python constants) ──────────────
def test_seismic_zone_factors_parity():
    """JSON zone factors must match Python SEISMIC_ZONE_FACTORS exactly."""
    for zone, py_value in SEISMIC_ZONE_FACTORS.items():
        json_value = get_seismic_zone_factor(zone)
        assert abs(json_value - py_value) < 1e-9, \
            f"Zone {zone}: JSON={json_value}, Python={py_value} — DIVERGED"
    print(f"PASS parity: seismic zone factors match for all "
          f"{len(SEISMIC_ZONE_FACTORS)} zones")


def test_importance_factor_parity():
    """JSON residential importance must match Python constant."""
    rules = load_rules("seismic_rules")
    json_val = rules["importance_factors"]["values"]["residential_standard"]
    assert json_val == IMPORTANCE_FACTOR_RESIDENTIAL, \
        f"Importance factor: JSON={json_val}, Python={IMPORTANCE_FACTOR_RESIDENTIAL}"
    print(f"PASS parity: residential importance factor = {json_val}")


def test_response_reduction_factor_parity():
    """JSON R factors match Python constants."""
    rules = load_rules("seismic_rules")
    v = rules["response_reduction_factors"]["values"]
    assert v["special_mrf_with_is13920"] == RESPONSE_REDUCTION_SPECIAL_MRF
    assert v["ordinary_mrf"] == RESPONSE_REDUCTION_ORDINARY_MRF
    print(f"PASS parity: R factors (special={v['special_mrf_with_is13920']}, "
          f"ordinary={v['ordinary_mrf']})")


def test_min_column_dim_parity():
    """JSON seismic min column dim must match Python constant."""
    json_val = get_seismic_min_column_dim_mm()
    assert json_val == SEISMIC_MIN_COLUMN_DIM_MM, \
        f"Min column dim: JSON={json_val}, Python={SEISMIC_MIN_COLUMN_DIM_MM}"
    print(f"PASS parity: seismic min column dim = {json_val}mm")


def test_column_steel_limits_parity():
    """JSON steel percentage limits must match Python constants."""
    min_pct, max_pct = get_column_steel_limits_pct()
    assert min_pct == COLUMN_STEEL_MIN_PCT
    assert max_pct == COLUMN_STEEL_MAX_PCT
    print(f"PASS parity: steel % limits ({min_pct}-{max_pct})")


def test_recommended_steel_by_zone_parity():
    """JSON recommended steel % by zone must match Python RECOMMENDED_COLUMN_STEEL_PCT."""
    for zone, py_pct in RECOMMENDED_COLUMN_STEEL_PCT.items():
        json_pct = get_recommended_column_steel_pct(zone)
        assert abs(json_pct - py_pct) < 1e-9, \
            f"Zone {zone}: JSON={json_pct}, Python={py_pct}"
    print(f"PASS parity: recommended steel % per zone "
          f"({len(RECOMMENDED_COLUMN_STEEL_PCT)} zones)")


def test_re_entrant_limits_parity():
    """JSON re-entrant corner thresholds must match Python constants."""
    mod, sev = get_re_entrant_corner_limits()
    assert mod == RE_ENTRANT_MODERATE_PCT
    assert sev == RE_ENTRANT_SEVERE_PCT
    print(f"PASS parity: re-entrant limits (moderate={mod}%, severe={sev}%)")


def test_aspect_ratio_limits_parity():
    """JSON aspect ratio thresholds must match Python constants."""
    mod, sev = get_aspect_ratio_limits()
    assert mod == ASPECT_MODERATE_LIMIT
    assert sev == ASPECT_SEVERE_LIMIT
    print(f"PASS parity: aspect ratio limits (moderate={mod}, severe={sev})")


def test_slenderness_limit_parity():
    """JSON slenderness limit must match Python constant."""
    json_val = get_short_column_slenderness_limit()
    assert json_val == SHORT_COLUMN_SLENDERNESS_LIMIT
    print(f"PASS parity: slenderness limit = {json_val}")


def test_regularity_names_parity():
    """JSON regularity class names must match Python constants."""
    rules = load_rules("seismic_rules")
    r = rules["regularity_classification_names"]
    assert r["regular"] == REGULARITY_REGULAR
    assert r["moderate"] == REGULARITY_MODERATE
    assert r["severe"] == REGULARITY_SEVERE
    print(f"PASS parity: regularity classification names match")


def test_is13920_required_zones_parity():
    """JSON required zones list must match is13920_required() function output."""
    json_zones = set(get_is13920_required_zones())
    # Test that Python function agrees with JSON for each zone
    for zone in ["II", "III", "IV", "V"]:
        py_required = is13920_required(zone)
        json_required = zone in json_zones
        assert py_required == json_required, \
            f"Zone {zone}: Python={py_required}, JSON={json_required}"
    print(f"PASS parity: IS 13920 applicability agrees for all zones")


# ─── Schema validation tests ─────────────────────────────────────────────
def test_schema_validator_rejects_missing_keys():
    """Missing required keys must cause RuleSchemaError at load time."""
    # Simulate broken JSON in cache by pre-populating with malformed data
    from buildemup.utils import kb_rules_loader as loader
    clear_cache()
    try:
        # Call internal validator directly with bad data
        loader._validate_seismic_rules({"seismic_zone_factors": {"values": {}}})
        assert False, "Expected RuleSchemaError for missing keys"
    except RuleSchemaError as e:
        assert "missing required key" in str(e) or "Zone" in str(e)
        print(f"PASS schema validator catches missing keys: {e.reason[:50]}")


def test_schema_validator_rejects_wrong_type():
    """Zone factor of wrong type must cause RuleSchemaError."""
    from buildemup.utils import kb_rules_loader as loader
    bad_data = {
        "seismic_zone_factors": {"values": {
            "II": "not a number", "III": 0.16, "IV": 0.24, "V": 0.36
        }},
        "importance_factors": {"values": {"residential_standard": 1.0}},
        "response_reduction_factors": {"values": {
            "special_mrf_with_is13920": 5.0, "ordinary_mrf": 3.0
        }},
        "is13920_applicability": {
            "required_zones": ["III", "IV", "V"],
            "exempt_zones": ["II"],
        },
        "column_minimum_dimensions": {"values": {
            "seismic_min_dim_mm": 300, "absolute_min_dim_mm": 230,
        }},
        "column_steel_percentages": {"values": {
            "minimum_pct": 0.8, "maximum_pct": 4.0,
            "recommended_pct_by_zone": {"II": 1.0, "III": 1.2, "IV": 1.5, "V": 2.0},
        }},
        "plan_regularity": {
            "re_entrant_corner": {"moderate_limit_pct": 15, "severe_limit_pct": 30},
            "plan_aspect_ratio": {"moderate_limit_ratio": 4, "severe_limit_ratio": 6},
        },
        "slenderness": {"short_column_limit": 12},
        "regularity_classification_names": {
            "regular": "REGULAR", "moderate": "MOD", "severe": "SEV",
        },
    }
    try:
        loader._validate_seismic_rules(bad_data)
        assert False, "Expected RuleSchemaError for non-numeric zone factor"
    except RuleSchemaError as e:
        assert "positive number" in str(e).lower() or "must be" in str(e).lower()
        print(f"PASS schema validator catches wrong type: {e.reason[:50]}")


def test_schema_validator_rejects_negative_zone_factor():
    """Zone factor ≤ 0 must fail (unphysical)."""
    from buildemup.utils import kb_rules_loader as loader
    bad_data = {
        "seismic_zone_factors": {"values": {"II": -0.1, "III": 0.16, "IV": 0.24, "V": 0.36}},
        "importance_factors": {"values": {"residential_standard": 1.0}},
        "response_reduction_factors": {"values": {
            "special_mrf_with_is13920": 5.0, "ordinary_mrf": 3.0
        }},
        "is13920_applicability": {"required_zones": ["III", "IV", "V"], "exempt_zones": ["II"]},
        "column_minimum_dimensions": {"values": {"seismic_min_dim_mm": 300, "absolute_min_dim_mm": 230}},
        "column_steel_percentages": {"values": {
            "minimum_pct": 0.8, "maximum_pct": 4.0,
            "recommended_pct_by_zone": {"II": 1.0, "III": 1.2, "IV": 1.5, "V": 2.0},
        }},
        "plan_regularity": {
            "re_entrant_corner": {"moderate_limit_pct": 15, "severe_limit_pct": 30},
            "plan_aspect_ratio": {"moderate_limit_ratio": 4, "severe_limit_ratio": 6},
        },
        "slenderness": {"short_column_limit": 12},
        "regularity_classification_names": {"regular": "R", "moderate": "M", "severe": "S"},
    }
    try:
        loader._validate_seismic_rules(bad_data)
        assert False, "Expected RuleSchemaError for negative zone factor"
    except RuleSchemaError as e:
        print(f"PASS schema validator catches negative zone factor")


# ─── Loader infrastructure tests ─────────────────────────────────────────
def test_load_rules_caches_result():
    """Second call to load_rules should not re-read the file."""
    clear_cache()
    a = load_rules("seismic_rules")
    b = load_rules("seismic_rules")
    assert a is b, "Cache should return same object, not reload"
    print(f"PASS load_rules caches result (same object on 2nd call)")


def test_load_rules_raises_on_missing_file():
    """Non-existent module must raise FileNotFoundError."""
    try:
        load_rules("nonexistent_rules")
        assert False, "Expected FileNotFoundError"
    except (FileNotFoundError, RuleSchemaError) as e:
        print(f"PASS missing file raises error")


def test_json_file_has_meta_section():
    """Rule JSON should have _meta with provenance."""
    rules = load_rules("seismic_rules")
    assert "_meta" in rules
    assert "source_standards" in rules["_meta"]
    assert "last_updated" in rules["_meta"]
    print(f"PASS JSON has _meta with provenance")


# ─── Accessor type tests ─────────────────────────────────────────────────
def test_accessor_return_types():
    """All convenience accessors must return correct types."""
    assert isinstance(get_seismic_zone_factor("III"), float)
    assert isinstance(get_is13920_required_zones(), list)
    assert isinstance(get_seismic_min_column_dim_mm(), int)
    assert isinstance(get_recommended_column_steel_pct("III"), float)
    assert isinstance(get_re_entrant_corner_limits(), tuple)
    assert isinstance(get_aspect_ratio_limits(), tuple)
    assert isinstance(get_short_column_slenderness_limit(), int)
    assert isinstance(get_column_steel_limits_pct(), tuple)
    print(f"PASS all accessors return correct types")


def test_accessor_unknown_zone_raises():
    """get_seismic_zone_factor with unknown zone must raise."""
    try:
        get_seismic_zone_factor("VII")   # no such zone
        assert False, "Expected ValueError"
    except ValueError:
        print(f"PASS accessor raises on unknown zone")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.6 Phase 2 Part 1 — Config-Driven Rules (Seismic) + Parity")
    print("=" * 70)
    print()
    print("--- Parity (JSON values == Python constants) ---")
    test_seismic_zone_factors_parity()
    test_importance_factor_parity()
    test_response_reduction_factor_parity()
    test_min_column_dim_parity()
    test_column_steel_limits_parity()
    test_recommended_steel_by_zone_parity()
    test_re_entrant_limits_parity()
    test_aspect_ratio_limits_parity()
    test_slenderness_limit_parity()
    test_regularity_names_parity()
    test_is13920_required_zones_parity()
    print()
    print("--- Schema validation ---")
    test_schema_validator_rejects_missing_keys()
    test_schema_validator_rejects_wrong_type()
    test_schema_validator_rejects_negative_zone_factor()
    print()
    print("--- Loader infrastructure ---")
    test_load_rules_caches_result()
    test_load_rules_raises_on_missing_file()
    test_json_file_has_meta_section()
    print()
    print("--- Accessor types ---")
    test_accessor_return_types()
    test_accessor_unknown_zone_raises()
    print()
    print("=" * 70)
    print("ALL PHASE 2 PART 1 TESTS PASSED")
    print("=" * 70)
