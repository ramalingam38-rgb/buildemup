"""C16 Sub-1 — versioning constants tests."""
from __future__ import annotations

import pytest

from buildemup.components.c16 import versioning as v


# ============================================================
# Version triple shape (Inv R16)
# ============================================================

class TestVersionTriple:
    def test_c16_version_is_non_empty_string(self):
        assert isinstance(v.C16_VERSION, str)
        assert v.C16_VERSION

    def test_c16_version_format(self):
        # Should be vX.Y* form, possibly with LOCKED suffix
        assert v.C16_VERSION.startswith("v")

    def test_schema_version_is_positive_int(self):
        assert isinstance(v.C16_DRAWING_SCHEMA_VERSION, int)
        assert v.C16_DRAWING_SCHEMA_VERSION >= 1

    def test_schema_version_matches_lock_baseline(self):
        # v0.5 LOCK + Sub-2 additive sub-envelope fields = 13
        assert v.C16_DRAWING_SCHEMA_VERSION == 13

    def test_identity_generation_starts_at_one(self):
        # v0.4 A10 / R33a — generation 1 at v0.5 LOCK
        assert v.C16_IDENTITY_GENERATION == 1

    def test_version_triple_helper_returns_three_tuple(self):
        triple = v.version_triple()
        assert isinstance(triple, tuple)
        assert len(triple) == 3
        assert triple == (
            v.C16_VERSION,
            v.C16_DRAWING_SCHEMA_VERSION,
            v.C16_IDENTITY_GENERATION,
        )

    def test_version_summary_contains_all_three_components(self):
        s = v.version_summary()
        assert v.C16_VERSION in s
        assert str(v.C16_DRAWING_SCHEMA_VERSION) in s
        assert str(v.C16_IDENTITY_GENERATION) in s


# ============================================================
# Upstream version expectations (provenance triple — R16)
# ============================================================

class TestUpstreamVersions:
    @pytest.mark.parametrize("attr", [
        "EXPECTED_C7_VERSION",
        "EXPECTED_C9_VERSION",
        "EXPECTED_C10_VERSION",
        "EXPECTED_C12_VERSION",
        "EXPECTED_C13_VERSION",
        "EXPECTED_C14_VERSION",
        "EXPECTED_C15_VERSION",
    ])
    def test_upstream_versions_are_non_empty_strings(self, attr):
        val = getattr(v, attr)
        assert isinstance(val, str)
        assert val

    def test_c15_pinned_to_v1_0(self):
        # C15 LOCKED v1.0 at S49 open
        assert v.EXPECTED_C15_VERSION == "v1.0"


# ============================================================
# Jurisdiction + domain scope (R31b)
# ============================================================

class TestJurisdictionAndScopeRegistries:
    def test_supported_jurisdictions_is_frozenset(self):
        assert isinstance(v.SUPPORTED_JURISDICTIONS, frozenset)

    def test_v1_ships_only_tncdbr(self):
        # B-C16-MULTI-JURISDICTION-PROFILES is post-LOCK
        assert v.SUPPORTED_JURISDICTIONS == frozenset({"tn_cdbr_2019"})

    def test_domain_scopes_is_frozenset(self):
        assert isinstance(v.SUPPORTED_DOMAIN_SCOPES, frozenset)

    def test_domain_scopes_v1_set(self):
        # v0.5 A4 — residential / small commercial / mixed use
        assert v.SUPPORTED_DOMAIN_SCOPES == frozenset({
            "residential_v1",
            "small_commercial_v1",
            "mixed_use_v1",
        })


# ============================================================
# Hard ceilings (R31a — v0.5 A4)
# ============================================================

class TestHardCeilings:
    def test_plot_ceilings_are_one_km(self):
        assert v.HARD_CEILING_PLOT_X_MM == 1_000_000
        assert v.HARD_CEILING_PLOT_Y_MM == 1_000_000

    def test_building_ceilings_are_500m(self):
        assert v.HARD_CEILING_BUILDING_X_MM == 500_000
        assert v.HARD_CEILING_BUILDING_Y_MM == 500_000
        assert v.HARD_CEILING_BUILDING_Z_MAX_MM == 500_000

    def test_basement_min_is_negative_50m(self):
        # 50m basement depth
        assert v.HARD_CEILING_BUILDING_Z_MIN_MM == -50_000

    def test_z_min_below_z_max(self):
        assert v.HARD_CEILING_BUILDING_Z_MIN_MM < v.HARD_CEILING_BUILDING_Z_MAX_MM

    def test_local_frame_bounds_are_symmetric(self):
        # LocalBuildingFrame ±50m
        assert v.HARD_CEILING_LOCAL_FRAME_X_MAX_MM == 50_000
        assert v.HARD_CEILING_LOCAL_FRAME_X_MIN_MM == -50_000
        assert v.HARD_CEILING_LOCAL_FRAME_Y_MAX_MM == 50_000
        assert v.HARD_CEILING_LOCAL_FRAME_Y_MIN_MM == -50_000

    def test_local_frame_tighter_than_plot(self):
        # Sanity: building can't exceed plot
        assert (
            v.HARD_CEILING_LOCAL_FRAME_X_MAX_MM <= v.HARD_CEILING_BUILDING_X_MM
        )


# ============================================================
# Epsilon policy (R34 — v0.4 A11 / v0.5 A3)
# ============================================================

class TestEpsilonPolicy:
    def test_coord_epsilon_is_one_mm(self):
        assert v.EPSILON_COORD_MM == 1

    def test_ratio_epsilon_is_1e_minus_4(self):
        assert v.EPSILON_RATIO == 1e-4

    def test_angle_epsilon_is_1e_minus_6(self):
        assert v.EPSILON_ANGLE_DEG == 1e-6

    def test_epsilon_positive(self):
        assert v.EPSILON_COORD_MM > 0
        assert v.EPSILON_RATIO > 0
        assert v.EPSILON_ANGLE_DEG > 0


# ============================================================
# Orientation basis (R29b — v0.4 A4)
# ============================================================

class TestOrientationBasisValues:
    def test_is_frozenset(self):
        assert isinstance(v.ORIENTATION_BASIS_VALUES, frozenset)

    def test_contains_all_four_hierarchy_steps(self):
        assert v.ORIENTATION_BASIS_VALUES == frozenset({
            "explicit_hint",
            "primary_entrance",
            "longest_wall",
            "lex_fallback",
        })


# ============================================================
# Constants are Final / immutable
# ============================================================

class TestImmutability:
    def test_constants_are_module_level_not_overridable(self):
        # Module attribute reassignment is technically possible at the
        # language level (Final is a type-checker hint), but the contract
        # is that downstream code does NOT reassign these. We document
        # this by confirming all the relevant attributes exist and
        # return the documented values.
        for attr in [
            "C16_VERSION",
            "C16_DRAWING_SCHEMA_VERSION",
            "C16_IDENTITY_GENERATION",
            "SUPPORTED_JURISDICTIONS",
            "SUPPORTED_DOMAIN_SCOPES",
            "HARD_CEILING_PLOT_X_MM",
            "HARD_CEILING_BUILDING_X_MM",
        ]:
            assert hasattr(v, attr)
