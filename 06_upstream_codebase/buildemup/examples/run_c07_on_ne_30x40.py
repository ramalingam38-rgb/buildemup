"""
Runnable example: Component 7 on the NE 30×40 Chennai plot.

Shows the refactored engine with:
  - 4 split sub-components (grid/structure/foundation/cost)
  - Real IS 875 load estimation (water tank, stilt, terrace)
  - Area-specific warnings (Velachery marshy)
  - Seismic zone gate (Zone III warning, Zone IV refusal)
  - Safety factors exposed (Transparency Triple principle)
  - KB versioning

Usage:
    python examples/run_c07_on_ne_30x40.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.components.c07_structural_grid import (
    StructuralGridEngine,
    StructuralGridInput,
)


def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " BuildemUp† — Component 7 Demo ".center(68) + "║")
    print("║" + " NE 30×40 Chennai Plot — Walkthrough Example ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    inp = StructuralGridInput(
        envelope_width_m=7.92,
        envelope_depth_m=10.97,
        floors_above_ground=1,
        city="chennai",
        area="velachery",
        seismic_zone="II",
        has_stilt_parking=True,
        has_terrace_access=True,
        has_water_tank=True,
        plot_facing="NE",
    )

    engine = StructuralGridEngine()
    result = engine.execute(inp)
    explanation = engine.explain(inp, result)

    print(explanation)

    print()
    print("COLUMN POSITIONS (sample):")
    print(f"  {'Label':<8} {'X (m)':<8} {'Y (m)':<8} {'Perimeter':<10}")
    print(f"  {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 10}")
    for col in result.grid.columns[:6]:
        perim = "yes" if col.on_perimeter else "no"
        print(f"  {col.grid_label:<8} {col.x_m:<8.2f} {col.y_m:<8.2f} {perim:<10}")
    remaining = result.grid.total_columns - 6
    if remaining > 0:
        print(f"  ... and {remaining} more columns")
    print()

    print("LOAD BREAKDOWN (for one interior column):")
    breakdown = result.structure.column_load_breakdown
    print(f"  Tributary area: {breakdown['tributary_area_sqm']:.1f} sqm")
    print(f"  {'Floor type':<25} {'Service kN':>12} {'Factored kN':>14}")
    print(f"  {'─' * 25} {'─' * 12} {'─' * 14}")
    for floor in breakdown["per_floor_loads"]:
        print(f"  {floor['floor_type']:<25} {floor['load_kn']:>12.1f} "
              f"{floor['factored_kn']:>14.1f}")
    print(f"  {'─' * 25} {'─' * 12} {'─' * 14}")
    print(f"  {'TOTAL':<25} {breakdown['total_unfactored_kn']:>12.1f} "
          f"{breakdown['total_factored_kn']:>14.1f}")
    print()


if __name__ == "__main__":
    main()
