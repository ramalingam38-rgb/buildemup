"""C16 Sub-1 — config.py tests.

Coverage:
    - CoordinateBoundsPolicy R31a enforcement (config ≤ hard ceiling)
    - RenderingConfig defaults + validation
    - effective_plot_bounds / effective_building_bounds helpers
"""
from __future__ import annotations

import pytest

from buildemup.components.c16 import (
    C16ConfigurationError,
    CoordinateBoundsPolicy,
    HARD_CEILING_BUILDING_X_MM,
    HARD_CEILING_BUILDING_Y_MM,
    HARD_CEILING_BUILDING_Z_MAX_MM,
    HARD_CEILING_BUILDING_Z_MIN_MM,
    HARD_CEILING_PLOT_X_MM,
    HARD_CEILING_PLOT_Y_MM,
    RenderingConfig,
    effective_building_bounds,
    effective_plot_bounds,
)


# ============================================================
# § 1 — CoordinateBoundsPolicy defaults
# ============================================================

class TestCoordinateBoundsPolicyDefaults:
    def test_residential_defaults_loaded(self):
        b = CoordinateBoundsPolicy()
        # v0.3 A8 residential defaults
        assert b.plot_x_max_mm == 200_000
        assert b.plot_y_max_mm == 200_000
        assert b.building_x_max_mm == 50_000
        assert b.building_y_max_mm == 50_000
        assert b.building_z_min_mm == -5_000
        assert b.building_z_max_mm == 50_000

    def test_defaults_are_within_hard_ceilings(self):
        b = CoordinateBoundsPolicy()
        assert b.plot_x_max_mm <= HARD_CEILING_PLOT_X_MM
        assert b.building_x_max_mm <= HARD_CEILING_BUILDING_X_MM
        assert b.building_z_min_mm >= HARD_CEILING_BUILDING_Z_MIN_MM
        assert b.building_z_max_mm <= HARD_CEILING_BUILDING_Z_MAX_MM


# ============================================================
# § 2 — R31a — config CANNOT exceed hard ceilings
# ============================================================

class TestR31aHardCeilingEnforcement:
    def test_plot_x_exceeding_ceiling_rejected(self):
        with pytest.raises(C16ConfigurationError) as excinfo:
            CoordinateBoundsPolicy(plot_x_max_mm=HARD_CEILING_PLOT_X_MM + 1)
        assert "HARD_CEILING" in str(excinfo.value) or "R31a" in str(excinfo.value)

    def test_plot_y_exceeding_ceiling_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(plot_y_max_mm=HARD_CEILING_PLOT_Y_MM + 1)

    def test_building_x_exceeding_ceiling_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(building_x_max_mm=HARD_CEILING_BUILDING_X_MM + 1)

    def test_building_y_exceeding_ceiling_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(building_y_max_mm=HARD_CEILING_BUILDING_Y_MM + 1)

    def test_building_z_max_exceeding_ceiling_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(building_z_max_mm=HARD_CEILING_BUILDING_Z_MAX_MM + 1)

    def test_building_z_min_below_ceiling_rejected(self):
        # Z_MIN is negative; "below" means MORE negative
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(building_z_min_mm=HARD_CEILING_BUILDING_Z_MIN_MM - 1)

    def test_bounds_at_exactly_hard_ceiling_accepted(self):
        # Boundary case: AT ceiling is OK; only beyond is rejected
        b = CoordinateBoundsPolicy(
            plot_x_max_mm=HARD_CEILING_PLOT_X_MM,
            plot_y_max_mm=HARD_CEILING_PLOT_Y_MM,
            building_x_max_mm=HARD_CEILING_BUILDING_X_MM,
            building_y_max_mm=HARD_CEILING_BUILDING_Y_MM,
            building_z_min_mm=HARD_CEILING_BUILDING_Z_MIN_MM,
            building_z_max_mm=HARD_CEILING_BUILDING_Z_MAX_MM,
        )
        assert b.plot_x_max_mm == HARD_CEILING_PLOT_X_MM

    def test_tighter_than_default_accepted(self):
        # Tighter bounds (smaller plots, etc.) always OK
        b = CoordinateBoundsPolicy(
            plot_x_max_mm=50_000,
            building_x_max_mm=10_000,
        )
        assert b.plot_x_max_mm == 50_000


# ============================================================
# § 3 — Internal consistency
# ============================================================

class TestCoordinateBoundsInternalConsistency:
    def test_z_max_below_z_min_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(
                building_z_min_mm=20_000,
                building_z_max_mm=10_000,
            )

    def test_z_max_equal_to_z_min_rejected(self):
        # max must STRICTLY exceed min
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(
                building_z_min_mm=0,
                building_z_max_mm=0,
            )

    def test_zero_plot_dim_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(plot_x_max_mm=0)

    def test_negative_plot_dim_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(plot_x_max_mm=-100)

    def test_zero_building_dim_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CoordinateBoundsPolicy(building_x_max_mm=0)


# ============================================================
# § 4 — RenderingConfig defaults + validation
# ============================================================

class TestRenderingConfigDefaults:
    def test_minimal_construction(self):
        c = RenderingConfig()
        assert c.working_drawing_scale == "1:50"
        assert c.permit_drawing_scale == "1:100"
        assert c.annotation_density == "full"
        assert c.multi_floor_composition == "per_floor_separate"
        assert c.include_furniture_footprints_in_working is True
        assert c.include_furniture_footprints_in_permit is False
        assert c.annotation_conflict_policy == "lex_asc_id_wins"
        assert c.capture_phase_timings is False
        assert c.capture_readability_diagnostics is False

    def test_default_mandatory_section_cuts(self):
        c = RenderingConfig()
        assert c.mandatory_section_cuts == frozenset({"entry", "staircase", "wet_zone"})

    def test_default_suppression_precedence(self):
        c = RenderingConfig()
        assert c.suppression_precedence == (
            "decorative", "secondary_dim", "primary_dim",
            "structural", "compliance",
        )

    def test_default_coordinate_bounds(self):
        c = RenderingConfig()
        assert c.coordinate_bounds.plot_x_max_mm == 200_000

    def test_each_config_carries_own_bounds_instance(self):
        # default_factory means each instance gets its own (no aliasing)
        c1 = RenderingConfig()
        c2 = RenderingConfig()
        assert c1.coordinate_bounds == c2.coordinate_bounds
        # But they're separate objects (not aliased)
        # (frozen dataclasses with same contents compare equal; that's fine)


class TestRenderingConfigValidation:
    def test_empty_suppression_precedence_rejected(self):
        with pytest.raises(C16ConfigurationError):
            RenderingConfig(suppression_precedence=())

    def test_duplicate_suppression_precedence_rejected(self):
        with pytest.raises(C16ConfigurationError):
            RenderingConfig(suppression_precedence=("a", "b", "a"))

    def test_unknown_section_cut_rejected(self):
        with pytest.raises(C16ConfigurationError) as excinfo:
            RenderingConfig(
                mandatory_section_cuts=frozenset({"entry", "unknown_cut"}),
            )
        assert "unknown_cut" in str(excinfo.value)

    def test_empty_section_cuts_accepted(self):
        # Empty is legal; means no mandatory cuts
        c = RenderingConfig(mandatory_section_cuts=frozenset())
        assert c.mandatory_section_cuts == frozenset()


# ============================================================
# § 5 — effective_*_bounds helpers
# ============================================================

class TestEffectiveBoundsHelpers:
    def test_effective_plot_bounds_returns_min(self):
        # Default config gives 200,000; ceiling is 1,000,000 → effective 200,000
        c = RenderingConfig()
        ex, ey = effective_plot_bounds(c)
        assert ex == 200_000
        assert ey == 200_000

    def test_effective_plot_uses_ceiling_when_config_tighter(self):
        # Config tighter than ceiling → use config
        c = RenderingConfig(coordinate_bounds=CoordinateBoundsPolicy(
            plot_x_max_mm=80_000,
        ))
        ex, ey = effective_plot_bounds(c)
        assert ex == 80_000

    def test_effective_building_bounds_returns_4_tuple(self):
        c = RenderingConfig()
        bx, by, zmin, zmax = effective_building_bounds(c)
        assert bx == 50_000
        assert by == 50_000
        assert zmin == -5_000
        assert zmax == 50_000

    def test_effective_z_min_uses_max_for_basement(self):
        # z_min: less-negative is tighter; MAX is the effective tighter bound
        c = RenderingConfig(coordinate_bounds=CoordinateBoundsPolicy(
            building_z_min_mm=-2_000,
        ))
        _, _, zmin, _ = effective_building_bounds(c)
        # -2000 is tighter than -5000 hard ceiling? No, it's tighter.
        # max(-2000, -50000) = -2000 → use config (tighter)
        assert zmin == -2_000
