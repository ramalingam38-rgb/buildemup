"""Tests for C3b versioning constants."""
from __future__ import annotations

from buildemup.components.c03b import versioning as V


# ============================================================
# Identity
# ============================================================

def test_c3b_version_is_locked():
    assert V.C3B_VERSION == "v0.7.LOCKED"


def test_schema_version_is_5():
    """Per spec § 5 — bumped 4→5 in v0.7 (compatibility causal graph)."""
    assert V.C3B_SESSION_SCHEMA_VERSION == 5


def test_component_name():
    assert V.COMPONENT_NAME == "c3b_post_layout_tradeoff_negotiation"


# ============================================================
# Expected upstreams
# ============================================================

def test_expected_c15_locked():
    assert V.EXPECTED_C15_VERSION == "v1.0.LOCKED"


def test_expected_c16_locked():
    assert V.EXPECTED_C16_VERSION == "v1.2.LOCKED"


def test_expected_c7_v0_8_locked():
    assert V.EXPECTED_C7_VERSION == "v0.8.LOCKED"


def test_expected_c3a_v0_2_1_locked():
    assert V.EXPECTED_C3A_VERSION == "v0.2.1.LOCKED"


def test_all_expected_upstream_versions_end_with_locked():
    expected_upstreams = [
        V.EXPECTED_C15_VERSION, V.EXPECTED_C16_VERSION,
        V.EXPECTED_C7_VERSION, V.EXPECTED_C10_VERSION,
        V.EXPECTED_C12_VERSION, V.EXPECTED_C13_VERSION,
        V.EXPECTED_C4_VERSION, V.EXPECTED_C3A_VERSION,
    ]
    for v in expected_upstreams:
        assert v.endswith(".LOCKED"), f"Expected upstream {v} must end with .LOCKED"


# ============================================================
# Scope
# ============================================================

def test_tn_cdbr_2019_supported():
    """v1 scope: Chennai jurisdiction only (spec § 1.4 + § 5)."""
    assert "tn_cdbr_2019" in V.SUPPORTED_JURISDICTIONS


def test_residential_v1_supported():
    assert "residential_v1" in V.SUPPORTED_DOMAIN_SCOPES


def test_supported_sets_are_frozen():
    """SUPPORTED_* are frozensets so they participate in hashing safely."""
    assert isinstance(V.SUPPORTED_JURISDICTIONS, frozenset)
    assert isinstance(V.SUPPORTED_DOMAIN_SCOPES, frozenset)


# ============================================================
# Iteration & tweak ceilings (spec § 5 + § 6)
# ============================================================

def test_iteration_cap_default_is_3():
    """v0.5 A8 — lowered from 5 to 3 to address decision fatigue."""
    assert V.ITERATION_CAP_DEFAULT == 3


def test_iteration_cap_hard_ceiling_is_7():
    assert V.ITERATION_CAP_HARD_CEILING == 7


def test_iteration_cap_default_below_hard_ceiling():
    assert V.ITERATION_CAP_DEFAULT < V.ITERATION_CAP_HARD_CEILING


def test_max_tweaks_per_layout_is_6():
    assert V.MAX_TWEAKS_PER_LAYOUT == 6


def test_tweaks_per_layout_hard_ceiling_is_8():
    assert V.TWEAKS_PER_LAYOUT_HARD_CEILING == 8


def test_soft_target_below_hard_ceiling_for_tweaks():
    assert V.MAX_TWEAKS_PER_LAYOUT < V.TWEAKS_PER_LAYOUT_HARD_CEILING


def test_max_represent_count_is_2():
    """Don't re-suggest a rejected tweak more than twice."""
    assert V.MAX_REPRESENT_COUNT == 2


def test_session_history_hard_ceiling_is_50():
    """Defensive ceiling; iteration cap of 7 normally bounds this."""
    assert V.SESSION_HISTORY_HARD_CEILING == 50


def test_expected_layout_count_is_3():
    """Cost Efficient / Everyday Living / Premium Design."""
    assert V.EXPECTED_LAYOUT_COUNT == 3


# ============================================================
# Magnitude ceilings (spec § 6)
# ============================================================

def test_cost_impact_ceiling_is_20_lakh():
    assert V.TWEAK_COST_IMPACT_CEILING_INR == 20_00_000.0


def test_space_impact_ceiling_is_150_sqft():
    assert V.TWEAK_SPACE_IMPACT_CEILING_SQFT == 150.0


# ============================================================
# Pareto floors (spec § 6)
# ============================================================

def test_pareto_floors_match_spec():
    assert V.PARETO_DIVERSITY_FLOOR_SQFT_PCT == 10.0
    assert V.PARETO_DIVERSITY_FLOOR_COST_PCT == 15.0
    assert V.PARETO_DIVERSITY_FLOOR_TOPOLOGY_COUNT == 3


# ============================================================
# Severity thresholds (spec § 3 Phase β 4.2)
# ============================================================

def test_load_bearing_proximity_300mm():
    """Spec § 3 Phase β step 4.2: 'within 300mm of a column'."""
    assert V.LOAD_BEARING_PROXIMITY_MM == 300.0


def test_subset_rerun_fast_ceiling_1s():
    assert V.SUBSET_RERUN_FAST_SECONDS_CEILING == 1.0


def test_subset_rerun_heavy_floor_10s():
    """Spec § 2.4.1: '> 10s requires reclassification'."""
    assert V.SUBSET_RERUN_HEAVY_SECONDS_FLOOR == 10.0


# ============================================================
# Signature constants
# ============================================================

def test_signature_hex_length_64():
    """sha256 = 64 hex chars."""
    assert V.SIGNATURE_HEX_LENGTH == 64


def test_canonical_float_decimals_6():
    assert V.CANONICAL_FLOAT_DECIMALS == 6


# ============================================================
# R2 banned phrases (spec § 7.5)
# ============================================================

def test_c3b_banned_substrings_includes_coercion():
    assert "you should" in V.C3B_BANNED_SUBSTRINGS
    assert "you must" in V.C3B_BANNED_SUBSTRINGS
    assert "you have to" in V.C3B_BANNED_SUBSTRINGS


def test_c3b_banned_substrings_includes_authority():
    """Spec § 7.5 — no authoritative ranking language."""
    assert "best tweak" in V.C3B_BANNED_SUBSTRINGS
    assert "right choice" in V.C3B_BANNED_SUBSTRINGS
    assert "wrong choice" in V.C3B_BANNED_SUBSTRINGS


def test_c3b_banned_substrings_includes_engine_centric():
    """Principle 1 — talk to user, not engine."""
    assert "the system decided" in V.C3B_BANNED_SUBSTRINGS
    assert "algorithm decided" in V.C3B_BANNED_SUBSTRINGS


def test_c3b_replacement_hints_has_alternatives():
    """Every replacement is principle-aligned."""
    assert V.C3B_REPLACEMENT_HINTS["should"] == "could"
    assert V.C3B_REPLACEMENT_HINTS["must"] == "may want to"


def test_banned_substrings_is_tuple_immutable():
    """Tuple so we can hash / share safely."""
    assert isinstance(V.C3B_BANNED_SUBSTRINGS, tuple)
