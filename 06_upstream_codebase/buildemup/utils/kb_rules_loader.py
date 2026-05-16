"""
BuildemUp† — KB Rules Loader (v0.6)
======================================

Reads numeric rule values from /kb_rules/*.json files.

Design principles (per v0.6 decision):
  1. REPLACE ONLY the read layer, not the logic
       → Python constants become JSON-sourced, but Python functions
         that USE those constants stay untouched.
  2. SCHEMA VALIDATION on every load
       → Missing keys / wrong types cause immediate, loud failure.
         Better to refuse to start than run with garbage data.
  3. CACHE AFTER LOAD
       → Rules are immutable at runtime. Load once, reuse.
  4. PARITY WITH OLD PYTHON CONSTANTS
       → Tests verify that JSON-loaded values match the original
         Python constants exactly. If they diverge, something broke.

Incremental migration plan:
  ✓ Phase 2a: seismic_rules.json (this module)
  ⏳ Phase 3+: load_rules.json, soil_rules.json, material_rates.json (incremental)

†= placeholder name marker.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Root directory for all rule JSON files
_KB_RULES_DIR = Path(__file__).parent.parent / "kb_rules"

# Cache: load each file only once per process
_CACHE: dict[str, dict] = {}


class RuleSchemaError(Exception):
    """Raised when a rule JSON fails schema validation at load time."""

    def __init__(self, module: str, path: str, reason: str):
        self.module = module
        self.path = path
        self.reason = reason
        super().__init__(
            f"[kb_rules/{module}] schema error at {path}: {reason}"
        )


def _ensure_path_exists(data: dict, path: list[str], module: str) -> Any:
    """Walk dict by path, raising RuleSchemaError if any key missing."""
    node = data
    visited = []
    for key in path:
        visited.append(key)
        if not isinstance(node, dict):
            raise RuleSchemaError(
                module, ".".join(visited[:-1]),
                f"expected dict, got {type(node).__name__}",
            )
        if key not in node:
            raise RuleSchemaError(
                module, ".".join(visited),
                f"missing required key '{key}'",
            )
        node = node[key]
    return node


def _validate_seismic_rules(data: dict) -> None:
    """Schema validator for seismic_rules.json.

    Raises RuleSchemaError if anything required is missing or malformed.
    This runs at load time — better to fail loudly than silently corrupt.
    """
    required_paths = [
        ["seismic_zone_factors", "values", "II"],
        ["seismic_zone_factors", "values", "III"],
        ["seismic_zone_factors", "values", "IV"],
        ["seismic_zone_factors", "values", "V"],
        ["importance_factors", "values", "residential_standard"],
        ["response_reduction_factors", "values", "special_mrf_with_is13920"],
        ["response_reduction_factors", "values", "ordinary_mrf"],
        ["is13920_applicability", "required_zones"],
        ["is13920_applicability", "exempt_zones"],
        ["column_minimum_dimensions", "values", "seismic_min_dim_mm"],
        ["column_minimum_dimensions", "values", "absolute_min_dim_mm"],
        ["column_steel_percentages", "values", "minimum_pct"],
        ["column_steel_percentages", "values", "maximum_pct"],
        ["column_steel_percentages", "values", "recommended_pct_by_zone", "II"],
        ["column_steel_percentages", "values", "recommended_pct_by_zone", "III"],
        ["column_steel_percentages", "values", "recommended_pct_by_zone", "IV"],
        ["column_steel_percentages", "values", "recommended_pct_by_zone", "V"],
        ["plan_regularity", "re_entrant_corner", "moderate_limit_pct"],
        ["plan_regularity", "re_entrant_corner", "severe_limit_pct"],
        ["plan_regularity", "plan_aspect_ratio", "moderate_limit_ratio"],
        ["plan_regularity", "plan_aspect_ratio", "severe_limit_ratio"],
        ["slenderness", "short_column_limit"],
        ["regularity_classification_names", "regular"],
        ["regularity_classification_names", "moderate"],
        ["regularity_classification_names", "severe"],
    ]

    for path in required_paths:
        value = _ensure_path_exists(data, path, "seismic_rules")
        # Leaf values should be numbers, strings, or lists of strings
        if isinstance(value, dict):
            raise RuleSchemaError(
                "seismic_rules", ".".join(path),
                f"expected leaf value, got dict",
            )

    # Sanity: zone factors must be positive floats
    zone_factors = data["seismic_zone_factors"]["values"]
    for zone, factor in zone_factors.items():
        if not isinstance(factor, (int, float)) or factor <= 0:
            raise RuleSchemaError(
                "seismic_rules", f"seismic_zone_factors.values.{zone}",
                f"must be positive number, got {factor!r}",
            )

    # Sanity: required_zones and exempt_zones must be lists
    for key in ["required_zones", "exempt_zones"]:
        val = data["is13920_applicability"][key]
        if not isinstance(val, list):
            raise RuleSchemaError(
                "seismic_rules", f"is13920_applicability.{key}",
                f"must be list, got {type(val).__name__}",
            )


def _validate_load_rules(data: dict) -> None:
    """Schema validator for load_rules.json (v0.7).

    Covers dead loads, live loads by floor type, concentrated loads,
    wall loads, partial safety factors.
    """
    required_paths = [
        ["dead_load", "values", "slab_weight_kn_per_sqm_per_mm"],
        ["dead_load", "values", "finishes_kn_per_sqm"],
        ["dead_load", "values", "partition_wall_kn_per_sqm"],
        ["live_loads_by_floor_type", "values", "STILT_PARKING"],
        ["live_loads_by_floor_type", "values", "RESIDENTIAL"],
        ["live_loads_by_floor_type", "values", "TERRACE_ACCESSIBLE"],
        ["live_loads_by_floor_type", "values", "TERRACE_INACCESSIBLE"],
        ["live_loads_by_floor_type", "values", "BALCONY"],
        ["live_loads_by_floor_type", "values", "STAIRCASE"],
        ["concentrated_loads", "overhead_water_tank", "total_load_kn"],
        ["concentrated_loads", "overhead_water_tank", "footprint_sqm"],
        ["concentrated_loads", "overhead_water_tank", "distributed_kn_per_sqm"],
        ["wall_loads", "values", "brick_230mm_3m_height_kn_per_m"],
        ["wall_loads", "values", "brick_115mm_3m_height_kn_per_m"],
        ["partial_safety_factors", "values", "dead_load"],
        ["partial_safety_factors", "values", "live_load"],
        ["partial_safety_factors", "values", "concrete_material"],
        ["partial_safety_factors", "values", "steel_material"],
        ["partial_safety_factors", "values", "seismic_combination"],
    ]
    for path in required_paths:
        value = _ensure_path_exists(data, path, "load_rules")
        if isinstance(value, dict):
            raise RuleSchemaError(
                "load_rules", ".".join(path),
                "expected leaf value, got dict",
            )
    # Live loads must be positive floats
    for floor_type, val in data["live_loads_by_floor_type"]["values"].items():
        if not isinstance(val, (int, float)) or val <= 0:
            raise RuleSchemaError(
                "load_rules", f"live_loads_by_floor_type.values.{floor_type}",
                f"must be positive number, got {val!r}",
            )
    # Safety factors must be ≥ 1.0 (can't be less than unity)
    for name, val in data["partial_safety_factors"]["values"].items():
        if not isinstance(val, (int, float)) or val < 1.0:
            raise RuleSchemaError(
                "load_rules", f"partial_safety_factors.values.{name}",
                f"safety factor must be ≥ 1.0, got {val!r}",
            )


def _validate_setback_rules(data: dict) -> None:
    """Schema validator for setback_rules.json (Component 1 v0.1+).

    v0.9 Session C: now data-driven — validates every non-_meta city
    section, so Mumbai/Delhi/Bangalore/Pune/Hyderabad sections all get
    schema-checked the same way as Chennai.
    """
    # Must have _fallback_nbc
    if "_fallback_nbc" not in data:
        raise RuleSchemaError(
            "setback_rules", "_fallback_nbc", "missing required top-level key"
        )

    # Discover all city sections (anything not starting with _)
    cities = [k for k in data.keys() if not k.startswith("_")]
    if not cities:
        raise RuleSchemaError(
            "setback_rules", "<root>", "no city sections found"
        )

    # _fallback_nbc validates with the same shape as a city
    sections_to_check = list(cities) + ["_fallback_nbc"]

    # Each section must have three plot_type sub-sections
    for section in sections_to_check:
        for plot_type in ["detached", "semi_detached", "continuous"]:
            if plot_type not in data[section]:
                raise RuleSchemaError(
                    "setback_rules",
                    f"{section}.{plot_type}",
                    "missing plot_type section"
                )

    # DETACHED sections must have tiers with required fields.
    # SEMI_DETACHED uses a descriptive rule (inherits from detached), so
    # the tiers requirement applies only when explicit tiers are provided.
    for section in sections_to_check:
        for plot_type in ["detached"]:
            tiers = data[section][plot_type].get("tiers", [])
            if not isinstance(tiers, list) or len(tiers) == 0:
                raise RuleSchemaError(
                    "setback_rules", f"{section}.{plot_type}.tiers",
                    "must be non-empty list"
                )
            for i, tier in enumerate(tiers):
                for field_name in (
                    "plot_area_max_sqm", "front_m", "rear_m",
                    "side_left_m", "side_right_m",
                ):
                    if field_name not in tier:
                        raise RuleSchemaError(
                            "setback_rules",
                            f"{section}.{plot_type}.tiers[{i}].{field_name}",
                            "required field missing"
                        )
                    val = tier[field_name]
                    if not isinstance(val, (int, float)) or val < 0:
                        raise RuleSchemaError(
                            "setback_rules",
                            f"{section}.{plot_type}.tiers[{i}].{field_name}",
                            f"must be non-negative number, got {val!r}"
                        )

    # CONTINUOUS sections must have front_m_by_road_width + rear_m
    for section in sections_to_check:
        cont = data[section]["continuous"]
        if "front_m_by_road_width" not in cont:
            raise RuleSchemaError(
                "setback_rules",
                f"{section}.continuous.front_m_by_road_width",
                "required field missing"
            )
        if "rear_m" not in cont:
            raise RuleSchemaError(
                "setback_rules",
                f"{section}.continuous.rear_m",
                "required field missing"
            )


def _validate_room_minimums(data: dict) -> None:
    """Schema validator for room_minimums.json (Component 1 v0.1).

    Ensures all 12 RoomType enum values are present with valid sizes.
    """
    EXPECTED_ROOM_TYPES = {
        "BEDROOM_MASTER", "BEDROOM_REGULAR",
        "BATHROOM_ATTACHED", "BATHROOM_COMMON",
        "KITCHEN", "LIVING", "DINING", "POOJA",
        "BALCONY", "UTILITY", "STORE", "STAIRCASE",
    }
    minimums = data.get("room_minimums_sqm", {})
    actual_keys = set(minimums.keys())
    missing = EXPECTED_ROOM_TYPES - actual_keys
    if missing:
        raise RuleSchemaError(
            "room_minimums", "room_minimums_sqm",
            f"missing room types: {sorted(missing)}"
        )
    extra = actual_keys - EXPECTED_ROOM_TYPES
    if extra:
        raise RuleSchemaError(
            "room_minimums", "room_minimums_sqm",
            f"unexpected room types: {sorted(extra)}"
        )
    for room_type, entry in minimums.items():
        if not isinstance(entry, dict):
            raise RuleSchemaError(
                "room_minimums",
                f"room_minimums_sqm.{room_type}",
                f"must be dict, got {type(entry).__name__}"
            )
        if "value" not in entry:
            raise RuleSchemaError(
                "room_minimums",
                f"room_minimums_sqm.{room_type}.value",
                "required field missing"
            )
        value = entry["value"]
        if not isinstance(value, (int, float)) or value <= 0:
            raise RuleSchemaError(
                "room_minimums",
                f"room_minimums_sqm.{room_type}.value",
                f"must be positive number, got {value!r}"
            )

    # Circulation factor
    cf = data.get("circulation_factor", {})
    cf_value = cf.get("value")
    if not isinstance(cf_value, (int, float)) or not 1.0 <= cf_value <= 2.0:
        raise RuleSchemaError(
            "room_minimums", "circulation_factor.value",
            f"must be in [1.0, 2.0], got {cf_value!r}"
        )
    # Optional small/large home variants — only validate if present
    for variant_key in ("value_small_home", "value_large_home"):
        variant_val = cf.get(variant_key)
        if variant_val is not None:
            if not isinstance(variant_val, (int, float)) or not 1.0 <= variant_val <= 2.0:
                raise RuleSchemaError(
                    "room_minimums", f"circulation_factor.{variant_key}",
                    f"must be in [1.0, 2.0] if provided, got {variant_val!r}"
                )


_VALIDATORS: dict[str, Any] = {
    "seismic_rules": _validate_seismic_rules,
    "load_rules": _validate_load_rules,   # v0.7: 2nd module migrated
    "setback_rules": _validate_setback_rules,       # Component 1 v0.1
    "room_minimums": _validate_room_minimums,       # Component 1 v0.1
    "coverage_rules": lambda data: _validate_coverage_rules(data),  # C2 Sess B
    "city_feasibility_defaults": lambda data: _validate_city_feasibility_defaults(data),  # C2 Sess E
    "rwh_approval_rules": lambda data: _validate_rwh_approval_rules(data),  # C2 Sess F
}


def _validate_rwh_approval_rules(data: dict) -> None:
    """Schema validator for rwh_approval_rules.json (Component 2 Session F).

    Two top-level sections (besides _meta):
      - rwh_mandate_by_city: per-city RWH mandate threshold rules
      - approval_complexity_tiers: simple/medium/complex tier definitions
    """
    if "_meta" not in data:
        raise RuleSchemaError(
            "rwh_approval_rules", "_meta",
            "missing required _meta section",
        )
    if "rwh_mandate_by_city" not in data:
        raise RuleSchemaError(
            "rwh_approval_rules", "rwh_mandate_by_city",
            "missing required section",
        )
    if "approval_complexity_tiers" not in data:
        raise RuleSchemaError(
            "rwh_approval_rules", "approval_complexity_tiers",
            "missing required section",
        )
    # Validate each city's RWH mandate
    rwh_required = (
        "always_mandatory", "plot_area_threshold_sqm",
        "authority", "regulation",
    )
    for city, rules in data["rwh_mandate_by_city"].items():
        for f in rwh_required:
            if f not in rules:
                raise RuleSchemaError(
                    "rwh_approval_rules",
                    f"rwh_mandate_by_city.{city}.{f}",
                    "missing required field",
                )
        if not isinstance(rules["always_mandatory"], bool):
            raise RuleSchemaError(
                "rwh_approval_rules",
                f"rwh_mandate_by_city.{city}.always_mandatory",
                f"must be boolean, got {type(rules['always_mandatory']).__name__}",
            )
    # Validate approval tiers
    tiers_required = ("simple", "medium", "complex")
    for tier in tiers_required:
        if tier not in data["approval_complexity_tiers"]:
            raise RuleSchemaError(
                "rwh_approval_rules",
                f"approval_complexity_tiers.{tier}",
                "missing required tier section",
            )
        tier_data = data["approval_complexity_tiers"][tier]
        for f in ("typical_timeline_weeks", "typical_authority_path",
                  "user_burden_summary"):
            if f not in tier_data:
                raise RuleSchemaError(
                    "rwh_approval_rules",
                    f"approval_complexity_tiers.{tier}.{f}",
                    "missing required field",
                )


def _validate_city_feasibility_defaults(data: dict) -> None:
    """Schema validator for city_feasibility_defaults.json (C2 Session E).

    Each non-_meta key is a city. Each city must have soil_type +
    soil_typical_sbc_kn_m2 + water_table_depth_m_premonsoon +
    water_table_depth_m_postmonsoon as the core required fields.
    """
    if "_meta" not in data:
        raise RuleSchemaError(
            "city_feasibility_defaults", "_meta",
            "missing required _meta section",
        )
    cities = [k for k in data.keys() if not k.startswith("_")]
    if not cities:
        raise RuleSchemaError(
            "city_feasibility_defaults", "<root>",
            "no city sections found",
        )
    required = (
        "soil_type", "soil_typical_sbc_kn_m2",
        "water_table_depth_m_premonsoon",
        "water_table_depth_m_postmonsoon",
    )
    for city in cities:
        for f in required:
            if f not in data[city]:
                raise RuleSchemaError(
                    "city_feasibility_defaults",
                    f"{city}.{f}",
                    "missing required field",
                )
        sbc = data[city]["soil_typical_sbc_kn_m2"]
        if not isinstance(sbc, (int, float)) or sbc <= 0:
            raise RuleSchemaError(
                "city_feasibility_defaults",
                f"{city}.soil_typical_sbc_kn_m2",
                f"must be positive number, got {sbc!r}",
            )
        for wt_field in ("water_table_depth_m_premonsoon",
                         "water_table_depth_m_postmonsoon"):
            wt = data[city][wt_field]
            if not isinstance(wt, (int, float)) or wt < 0:
                raise RuleSchemaError(
                    "city_feasibility_defaults",
                    f"{city}.{wt_field}",
                    f"must be non-negative number, got {wt!r}",
                )


def _validate_coverage_rules(data: dict) -> None:
    """Schema validator for coverage_rules.json (Component 2 Session B).

    Each non-_meta key is a city. Each city must have base_far,
    max_ground_coverage_pct, authority, regulation. Optional small_plot_far
    for cities with plot-tier exceptions (Delhi).
    """
    if "_meta" not in data:
        raise RuleSchemaError(
            "coverage_rules", "_meta", "missing required _meta section"
        )
    cities = [k for k in data.keys() if not k.startswith("_")]
    if not cities:
        raise RuleSchemaError(
            "coverage_rules", "<root>", "no city sections found"
        )
    required_fields = (
        "base_far", "max_ground_coverage_pct", "authority", "regulation",
    )
    for city in cities:
        for field_name in required_fields:
            if field_name not in data[city]:
                raise RuleSchemaError(
                    "coverage_rules",
                    f"{city}.{field_name}",
                    "missing required field",
                )
        # Sanity: FAR must be positive, GC must be 1-100
        far = data[city]["base_far"]
        if not isinstance(far, (int, float)) or far <= 0:
            raise RuleSchemaError(
                "coverage_rules", f"{city}.base_far",
                f"must be positive number, got {far!r}",
            )
        gc = data[city]["max_ground_coverage_pct"]
        if not isinstance(gc, (int, float)) or gc < 1 or gc > 100:
            raise RuleSchemaError(
                "coverage_rules", f"{city}.max_ground_coverage_pct",
                f"must be in [1, 100], got {gc!r}",
            )


def load_rules(module_name: str) -> dict:
    """Load and validate a rules JSON file. Cached after first load.

    Args:
        module_name: file stem without extension, e.g., "seismic_rules".

    Returns:
        Dict of rule values as parsed from JSON (validated).

    Raises:
        FileNotFoundError: if JSON file doesn't exist.
        RuleSchemaError: if schema validation fails.
    """
    if module_name in _CACHE:
        return _CACHE[module_name]

    path = _KB_RULES_DIR / f"{module_name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Rule file not found: {path}. "
            f"Expected at /kb_rules/{module_name}.json"
        )

    with open(path, "r") as f:
        data = json.load(f)

    validator = _VALIDATORS.get(module_name)
    if validator is None:
        raise RuleSchemaError(
            module_name, "",
            f"no validator registered for this module",
        )
    validator(data)

    _CACHE[module_name] = data
    return data


def clear_cache() -> None:
    """Clear the cache. Used by tests to force re-load."""
    _CACHE.clear()


# ─── Convenience accessors ─────────────────────────────────────────────
# These provide typed access to the rules JSON. Downstream code imports
# these instead of digging into the dict every time.

def get_seismic_zone_factor(zone: str) -> float:
    """Get Z factor (peak ground acceleration fraction) for seismic zone."""
    rules = load_rules("seismic_rules")
    try:
        return float(rules["seismic_zone_factors"]["values"][zone])
    except KeyError:
        raise ValueError(f"Unknown seismic zone: {zone}")


def get_is13920_required_zones() -> list[str]:
    """Get list of seismic zones requiring IS 13920 detailing."""
    rules = load_rules("seismic_rules")
    return list(rules["is13920_applicability"]["required_zones"])


def get_seismic_min_column_dim_mm() -> int:
    """Get minimum column dimension under IS 13920."""
    rules = load_rules("seismic_rules")
    return int(rules["column_minimum_dimensions"]["values"]["seismic_min_dim_mm"])


def get_recommended_column_steel_pct(zone: str) -> float:
    """Get recommended longitudinal steel % for a given seismic zone."""
    rules = load_rules("seismic_rules")
    by_zone = rules["column_steel_percentages"]["values"]["recommended_pct_by_zone"]
    try:
        return float(by_zone[zone])
    except KeyError:
        raise ValueError(f"No recommended steel % for zone {zone}")


def get_re_entrant_corner_limits() -> tuple[float, float]:
    """Get (moderate_pct, severe_pct) re-entrant corner thresholds."""
    rules = load_rules("seismic_rules")
    r = rules["plan_regularity"]["re_entrant_corner"]
    return (float(r["moderate_limit_pct"]), float(r["severe_limit_pct"]))


def get_aspect_ratio_limits() -> tuple[float, float]:
    """Get (moderate_ratio, severe_ratio) aspect ratio thresholds."""
    rules = load_rules("seismic_rules")
    r = rules["plan_regularity"]["plan_aspect_ratio"]
    return (float(r["moderate_limit_ratio"]), float(r["severe_limit_ratio"]))


def get_short_column_slenderness_limit() -> int:
    """Get slenderness limit separating short vs slender columns."""
    rules = load_rules("seismic_rules")
    return int(rules["slenderness"]["short_column_limit"])


def get_column_steel_limits_pct() -> tuple[float, float]:
    """Get (min_pct, max_pct) longitudinal steel limits."""
    rules = load_rules("seismic_rules")
    v = rules["column_steel_percentages"]["values"]
    return (float(v["minimum_pct"]), float(v["maximum_pct"]))


# ─── v0.7: Load rules accessors (2nd migration, per recipe) ──────────────

def get_slab_weight_kn_per_sqm_per_mm() -> float:
    """Slab self-weight coefficient (kN/sqm per mm of slab thickness)."""
    rules = load_rules("load_rules")
    return float(rules["dead_load"]["values"]["slab_weight_kn_per_sqm_per_mm"])


def get_finishes_kn_per_sqm() -> float:
    """Finishes (tiling, flooring, ceiling) dead load."""
    rules = load_rules("load_rules")
    return float(rules["dead_load"]["values"]["finishes_kn_per_sqm"])


def get_partition_wall_kn_per_sqm() -> float:
    """Partition wall allowance distributed over floor area."""
    rules = load_rules("load_rules")
    return float(rules["dead_load"]["values"]["partition_wall_kn_per_sqm"])


def get_live_load_kn_per_sqm(floor_type_name: str) -> float:
    """Get live load per IS 875 Part 2 for a given floor type name.

    Args:
        floor_type_name: 'STILT_PARKING', 'RESIDENTIAL', 'TERRACE_ACCESSIBLE',
                         'TERRACE_INACCESSIBLE', 'BALCONY', 'STAIRCASE'
    """
    rules = load_rules("load_rules")
    try:
        return float(rules["live_loads_by_floor_type"]["values"][floor_type_name])
    except KeyError:
        raise ValueError(f"Unknown floor type for live load: {floor_type_name}")


def get_water_tank_load_kn() -> tuple[float, float, float]:
    """Get (total_load_kn, footprint_sqm, distributed_kn_per_sqm) for 5000L tank."""
    rules = load_rules("load_rules")
    wt = rules["concentrated_loads"]["overhead_water_tank"]
    return (
        float(wt["total_load_kn"]),
        float(wt["footprint_sqm"]),
        float(wt["distributed_kn_per_sqm"]),
    )


def get_wall_load_kn_per_m(wall_thickness_mm: int) -> float:
    """Get linear wall load for 230mm or 115mm brick wall at 3m height.

    Args:
        wall_thickness_mm: 230 or 115
    """
    rules = load_rules("load_rules")
    v = rules["wall_loads"]["values"]
    if wall_thickness_mm == 230:
        return float(v["brick_230mm_3m_height_kn_per_m"])
    elif wall_thickness_mm == 115:
        return float(v["brick_115mm_3m_height_kn_per_m"])
    raise ValueError(
        f"Unsupported wall thickness: {wall_thickness_mm}mm (supported: 115, 230)"
    )


def get_partial_safety_factor(factor_name: str) -> float:
    """Get partial safety factor per IS 456 cl. 36.4.

    Args:
        factor_name: 'dead_load' / 'live_load' / 'concrete_material' /
                     'steel_material' / 'seismic_combination'
    """
    rules = load_rules("load_rules")
    try:
        return float(rules["partial_safety_factors"]["values"][factor_name])
    except KeyError:
        raise ValueError(f"Unknown safety factor: {factor_name}")


# ─── Component 1 v0.1: Setback rules accessors ───────────────────────────

def get_setback_rules_for_city(city: str) -> dict:
    """Get the setback rules section for a city.

    Falls back to '_fallback_nbc' for cities without explicit DCR support.
    """
    rules = load_rules("setback_rules")
    city_lower = city.lower().strip()
    if city_lower in rules and not city_lower.startswith("_"):
        return rules[city_lower]
    # Fallback to NBC general
    return rules["_fallback_nbc"]


def get_setback_authority_for_city(city: str) -> str:
    """Return the source authority string (e.g., 'TNCDBR 2019')."""
    section = get_setback_rules_for_city(city)
    return section.get("_authority", "NBC 2016 general")


# ─── Component 1 v0.1: Room minimums accessors ───────────────────────────

def get_room_minimum_sqm(room_type_name: str) -> float:
    """Get NBC minimum size in sqm for a RoomType by enum name.

    Args:
        room_type_name: Enum name, e.g., 'BEDROOM_MASTER'
    """
    rules = load_rules("room_minimums")
    try:
        return float(rules["room_minimums_sqm"][room_type_name]["value"])
    except KeyError:
        raise ValueError(f"Unknown room type: {room_type_name}")


def get_circulation_factor() -> float:
    """Get the default floor-area circulation multiplier (1.35 typical).

    Per IS 3861-2002: walls 5-10% + horizontal circulation 10-15% +
    vertical circulation 4-5% = ~30-35% overhead. Default = 1.35.
    For size-aware factor, use get_circulation_factor_for_size().
    """
    rules = load_rules("room_minimums")
    return float(rules["circulation_factor"]["value"])


def get_circulation_factor_for_size(
    total_room_area_sqm: float,
) -> tuple[float, str]:
    """Size-aware circulation factor per IS 3861-2002 research.

    Small homes (rooms < 30 sqm/floor) have proportionally more
    circulation overhead. Large homes (rooms > 100 sqm/floor) are
    more efficient.

    Returns:
        (factor, size_label) where size_label is "small", "typical",
        or "large" — used in assumptions disclosure.
    """
    rules = load_rules("room_minimums")
    cf = rules["circulation_factor"]
    small_thresh = float(cf.get("small_home_threshold_sqm", 30.0))
    large_thresh = float(cf.get("large_home_threshold_sqm", 100.0))
    default_val = float(cf["value"])
    small_val = float(cf.get("value_small_home", default_val))
    large_val = float(cf.get("value_large_home", default_val))

    if total_room_area_sqm < small_thresh:
        return small_val, "small"
    if total_room_area_sqm > large_thresh:
        return large_val, "large"
    return default_val, "typical"
