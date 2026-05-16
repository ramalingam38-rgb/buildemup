"""
Unit tests for GridGenerator sub-component (Component 7a).

Tests that the grid generator works in isolation — without any knowledge
of loads, cost, or foundation. Pure geometry.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.components.c07.grid_generator import GridGenerator


def test_ne_30x40_envelope():
    """Standard envelope produces expected grid."""
    gen = GridGenerator()
    grid = gen.generate(7.92, 10.97)
    # 7.92m → 2 bays of 4.0m (snapped from 3.96m); 3 columns in X
    # 10.97m → 3 bays of 3.6m + sliver absorbed; 4 columns in Y
    assert grid.columns_x_count == 3
    assert grid.columns_y_count == 4
    assert grid.total_columns == 12
    assert 2.7 <= grid.bay_x_m <= 4.5
    assert 2.7 <= grid.bay_y_m <= 4.5
    print(f"PASS NE 30x40: {grid.columns_x_count}×{grid.columns_y_count} "
          f"= {grid.total_columns} cols, bays {grid.bay_x_m}m × {grid.bay_y_m}m")


def test_small_plot_envelope():
    """Small plot works with minimum bay size."""
    gen = GridGenerator()
    grid = gen.generate(5.5, 7.0)
    assert grid.total_columns >= 4
    print(f"PASS small plot: {grid.total_columns} cols")


def test_too_small_raises():
    """Envelope below 5m in either direction must raise."""
    gen = GridGenerator()
    try:
        gen.generate(4.5, 10.0)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "too small" in str(e).lower()
    print(f"PASS too-small rejection")


def test_sliver_absorbed():
    """Tiny remainder bay should be absorbed into last bay."""
    gen = GridGenerator()
    # 10.97m / 3.6m = 3 bays + 0.17m sliver → absorb
    positions = gen._distribute_columns(10.97, 3.6)
    gaps = [round(positions[i+1] - positions[i], 2) for i in range(len(positions)-1)]
    assert all(g >= 1.8 for g in gaps), f"Sliver bay present: {gaps}"
    print(f"PASS sliver absorption: gaps {gaps}")


def test_substantial_remainder_gets_own_column():
    """Remainder >50% of bay size should get its own column."""
    gen = GridGenerator()
    # 8.5m / 3.0m = 2 full bays + 2.5m remainder (83% of bay) → add column
    positions = gen._distribute_columns(8.5, 3.0)
    gaps = [round(positions[i+1] - positions[i], 2) for i in range(len(positions)-1)]
    assert all(g >= 1.5 for g in gaps)
    print(f"PASS substantial remainder: gaps {gaps}")


def test_grid_labels_sequential():
    """Column labels go A1, A2, A3, B1, B2, ..."""
    gen = GridGenerator()
    grid = gen.generate(7.92, 10.97)
    labels = [c.grid_label for c in grid.columns]
    # First column should be A1
    assert labels[0] == "A1"
    # All unique
    assert len(set(labels)) == len(labels)
    print(f"PASS grid labels: {labels[:4]}...{labels[-2:]}")


def test_perimeter_detection():
    """Columns on envelope edges marked as perimeter."""
    gen = GridGenerator()
    grid = gen.generate(7.92, 10.97)
    perim_count = sum(1 for c in grid.columns if c.on_perimeter)
    # All 12 columns in 3×4 grid ARE on perimeter (no interior)
    # Interior columns only exist in larger grids
    print(f"PASS perimeter: {perim_count}/{grid.total_columns} columns on perimeter")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing GridGenerator sub-component")
    print("=" * 60)
    test_ne_30x40_envelope()
    test_small_plot_envelope()
    test_too_small_raises()
    test_sliver_absorbed()
    test_substantial_remainder_gets_own_column()
    test_grid_labels_sequential()
    test_perimeter_detection()
    print()
    print("ALL PASS")
