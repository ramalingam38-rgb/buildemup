"""Validation tests for C8 grid quantization + width selection.

Per C8 SPEC v0.5 LOCKED § 4.2 / § 4.3 / § 14.19.
"""
from __future__ import annotations

import pytest

from buildemup.components.c08 import (
    CorridorDesignConfig,
    CorridorTooNarrowError,
    WidthQuantization,
)
from buildemup.components.c08.grid_alignment import (
    derive_grid_lines,
    edge_snap_choice_score,
    find_edge_snap_pair,
)
from buildemup.components.c08.schema import GRID_FRACTION_CANDIDATES
from buildemup.components.c08.width_selection import (
    select_corridor_width,
    select_grid_fraction_width,
    width_selection_score,
)
from buildemup.tests.validation._c8_fixtures import make_grid, make_grid_minimal


# ─── Width selection: 7 C7 bay sizes (spec § 4.3 worked example) ────


def test_width_selection_bay_2_7_chooses_1_35():
    """bay=2.7 → 1.35 (1/2 fraction)."""
    grid = make_grid_minimal(bay_x_m=2.7, bay_y_m=3.0, envelope_width_m=10.0, envelope_depth_m=10.0)
    cfg = CorridorDesignConfig()
    w, f, ax = select_corridor_width(grid, cfg)
    assert w == pytest.approx(1.35, abs=1e-6)
    assert f == 0.5
    assert ax == "x"


def test_width_selection_bay_3_0_chooses_1_50():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.5)
    cfg = CorridorDesignConfig()
    w, _, _ = select_corridor_width(grid, cfg)
    assert w == pytest.approx(1.5, abs=1e-6)


def test_width_selection_bay_3_3_chooses_1_10():
    """bay=3.3 → 1.1 (1/3 fraction); 1.65 (1/2) is rejected as too over-comfort."""
    grid = make_grid_minimal(bay_x_m=3.3, bay_y_m=3.5)
    cfg = CorridorDesignConfig()
    w, f, _ = select_corridor_width(grid, cfg)
    assert w == pytest.approx(1.1, abs=1e-6)
    assert f == pytest.approx(1.0/3.0, abs=1e-6)


def test_width_selection_bay_3_6_chooses_1_20():
    grid = make_grid_minimal(bay_x_m=3.6, bay_y_m=4.0)
    cfg = CorridorDesignConfig()
    w, _, _ = select_corridor_width(grid, cfg)
    assert w == pytest.approx(1.2, abs=1e-6)


def test_width_selection_bay_4_0_chooses_1_33():
    grid = make_grid_minimal(bay_x_m=4.0, bay_y_m=4.5)
    cfg = CorridorDesignConfig()
    w, _, _ = select_corridor_width(grid, cfg)
    assert w == pytest.approx(4.0/3.0, abs=1e-6)


def test_width_selection_bay_4_5_chooses_1_125():
    grid = make_grid_minimal(bay_x_m=4.5, bay_y_m=5.0)
    cfg = CorridorDesignConfig()
    w, f, _ = select_corridor_width(grid, cfg)
    assert w == pytest.approx(1.125, abs=1e-6)
    assert f == 0.25


def test_width_selection_bay_5_0_chooses_1_25():
    grid = make_grid_minimal(bay_x_m=5.0, bay_y_m=5.5)
    cfg = CorridorDesignConfig()
    w, f, _ = select_corridor_width(grid, cfg)
    assert w == pytest.approx(1.25, abs=1e-6)
    assert f == 0.25


# ─── Score function ────────────────────────────────────────


def test_score_under_comfort_uses_ratio_2():
    """Per § 14.19: under-comfort × ratio (default 2.0)."""
    score = width_selection_score(
        candidate_m=1.0, comfort_m=1.2, regulatory_m=0.9, ratio=2.0,
    )
    assert score == pytest.approx(0.4, abs=1e-9)  # (1.2-1.0) × 2


def test_score_over_comfort_uses_ratio_1():
    score = width_selection_score(
        candidate_m=1.5, comfort_m=1.2, regulatory_m=0.9, ratio=2.0,
    )
    assert score == pytest.approx(0.3, abs=1e-9)  # 1.5-1.2


def test_score_below_regulatory_is_inf():
    score = width_selection_score(
        candidate_m=0.7, comfort_m=1.2, regulatory_m=0.9, ratio=2.0,
    )
    assert score == float("inf")


def test_score_at_comfort_is_zero():
    score = width_selection_score(
        candidate_m=1.2, comfort_m=1.2, regulatory_m=0.9, ratio=2.0,
    )
    assert score == 0.0


# ─── Width quantization modes ────────────────────────


def test_width_quantization_grid_fractions_returns_fraction():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.5)
    cfg = CorridorDesignConfig(width_quantization=WidthQuantization.GRID_FRACTIONS)
    w, f, ax = select_corridor_width(grid, cfg)
    assert f is not None
    assert ax in ("x", "y")


def test_width_quantization_nearest_grid_line_returns_target():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.5)
    cfg = CorridorDesignConfig(width_quantization=WidthQuantization.NEAREST_GRID_LINE)
    w, f, ax = select_corridor_width(grid, cfg)
    assert w >= cfg.regulatory_min_width_m
    assert f is None
    assert ax is None


def test_width_quantization_none_free_width_returns_target():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.5)
    cfg = CorridorDesignConfig(width_quantization=WidthQuantization.NONE_FREE_WIDTH)
    w, f, _ = select_corridor_width(grid, cfg)
    assert w == cfg.comfort_target_width_m


def test_width_too_narrow_raises():
    """Per § 6 / B-NNN-B."""
    grid = make_grid_minimal(bay_x_m=1.0, bay_y_m=1.0)
    cfg = CorridorDesignConfig(regulatory_min_width_m=0.9)
    with pytest.raises(CorridorTooNarrowError):
        select_grid_fraction_width(grid, cfg)


# ─── Grid line derivation ────────────────────────────


def test_derive_grid_lines_returns_two_tuples():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.5)
    x_lines, y_lines = derive_grid_lines(grid)
    assert isinstance(x_lines, tuple)
    assert isinstance(y_lines, tuple)


def test_derive_grid_lines_sorted_no_dups():
    grid = make_grid_minimal(bay_x_m=3.0, bay_y_m=3.5)
    x_lines, y_lines = derive_grid_lines(grid)
    assert list(x_lines) == sorted(x_lines)
    assert list(y_lines) == sorted(y_lines)
    assert len(set(x_lines)) == len(x_lines)
    assert len(set(y_lines)) == len(y_lines)


# ─── Edge-snap pair finder ─────────────────────────


def test_find_edge_snap_pair_basic():
    """Snap pair separated by exactly target width."""
    cfg = CorridorDesignConfig()
    grid_lines = (0.0, 1.2, 3.0, 6.0)
    pair = find_edge_snap_pair(grid_lines, target_width_m=1.2, target_centerline_m=0.6, envelope_dim_m=6.0, config=cfg)
    assert pair == (0.0, 1.2)


def test_find_edge_snap_pair_no_match():
    cfg = CorridorDesignConfig()
    grid_lines = (0.0, 3.0, 6.0)
    pair = find_edge_snap_pair(grid_lines, target_width_m=1.2, target_centerline_m=2.0, envelope_dim_m=6.0, config=cfg)
    assert pair is None


def test_find_edge_snap_pair_envelope_symmetry_secondary():
    """Per § 4.2.1: envelope-symmetry ties-break."""
    cfg = CorridorDesignConfig(envelope_symmetry_weight=0.3)
    # Two pairs at same width; the centered one should win
    grid_lines = (0.0, 1.2, 4.4, 5.6, 12.0)
    pair = find_edge_snap_pair(grid_lines, target_width_m=1.2, target_centerline_m=6.0, envelope_dim_m=12.0, config=cfg)
    # Pair 4.4-5.6 has centerline 5.0, off-target by 1.0
    # Pair 0.0-1.2 has centerline 0.6, off-target by 5.4
    assert pair == (4.4, 5.6)


def test_edge_snap_choice_score_lower_for_centered():
    cfg = CorridorDesignConfig()
    s_centered = edge_snap_choice_score((4.4, 5.6), 12.0, 5.0, cfg)
    s_offset = edge_snap_choice_score((0.0, 1.2), 12.0, 5.0, cfg)
    assert s_centered < s_offset
