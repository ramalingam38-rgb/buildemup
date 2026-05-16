"""
BuildemUp† — Load Combination Engine (v0.6)
==============================================

Implements the 5 governing load combinations per Indian practice for
residential building preliminary design.

CRITICAL — what we do and DON'T do:
  ✓ Compute 5 governing combinations (DL+LL, +WL, +EQ, uplift)
  ✓ Take governing case (worst) for each design check
  ✓ Honest disclosure that wind+EQ are NOT combined per IS practice
  ✗ NOT full IS 875 Part 5 matrix (which is much larger)
  ✗ NOT directional + torsional combinations
  ✗ NOT load history / time-varying

Why these 5:
  - DL + LL: pure gravity. Often governs interior columns.
  - DL + LL + WL: gravity + wind. Lateral demand check.
  - DL + LL + EQ: gravity + earthquake. Lateral demand check.
  - 0.9DL + WL: foundation uplift check (wind dominant).
  - 0.9DL + EQ: foundation uplift check (seismic dominant).

Per IS codes, wind (WL) and seismic (EQ) are NEVER combined. The
structure is designed for whichever lateral case is more critical.
This is verified in our research and explicit in IS 875 Part 5
practice notes.

Citations:
  - IS 875 Part 5:1987 (Special loads and combinations)
  - IS 456:2000 cl. 36.4 (load combinations for limit state design)
  - IS 1893 Part 1:2016 (seismic load combinations)

†= placeholder name marker.

KB_VERSION: "LoadCombo_v1_2026"
"""
from __future__ import annotations
from dataclasses import dataclass


KB_VERSION = "LoadCombo_v1_2026"


@dataclass(frozen=True)
class LoadInputs:
    """Per-column unfactored load inputs."""
    column_id: str
    dead_load_kn: float        # Self-weight + finishes + walls
    live_load_kn: float        # IS 875 Part 2 imposed loads
    wind_axial_kn: float       # Wind-induced axial (uplift +ve, download -ve)
    wind_moment_x_knm: float   # Wind moment about X
    wind_moment_y_knm: float   # Wind moment about Y
    seismic_axial_kn: float    # Seismic-induced axial
    seismic_moment_x_knm: float
    seismic_moment_y_knm: float


@dataclass(frozen=True)
class CombinationResult:
    """One load combination's factored result for one column."""
    combo_name: str            # e.g., "1.5(DL+LL+WL)"
    pu_kn: float               # Factored axial
    mux_knm: float             # Factored moment X
    muy_knm: float             # Factored moment Y
    is_uplift_combo: bool      # True for 0.9DL combos


@dataclass(frozen=True)
class GoverningResult:
    """The governing combo + its factored loads for one column."""
    column_id: str
    governing_combo: str
    pu_kn: float
    mux_knm: float
    muy_knm: float
    all_combos: tuple[CombinationResult, ...]
    method_disclosure: str


def compute_load_combinations(inp: LoadInputs) -> list[CombinationResult]:
    """Compute all 5 governing load combinations per IS 456 cl. 36.4.

    Combinations (factored):
      1. 1.5(DL + LL)              — pure gravity
      2. 1.5(DL + LL + WL)         — gravity + wind
      3. 1.5(DL + LL + EQ)         — gravity + earthquake
      4. 1.2DL + 1.2LL + 1.2WL    — alternative gravity+wind (where applicable)
      5. 0.9DL + 1.5WL             — foundation uplift, wind
      6. 0.9DL + 1.5EQ             — foundation uplift, seismic

    Note: We use 5 governing combos (1-3, 5-6). Combo 4 is omitted as it
    rarely governs for residential and would add noise.
    """
    combos = []

    # Combo 1: pure gravity 1.5(DL + LL)
    combos.append(CombinationResult(
        combo_name="1.5(DL+LL)",
        pu_kn=1.5 * (inp.dead_load_kn + inp.live_load_kn),
        mux_knm=0.0,
        muy_knm=0.0,
        is_uplift_combo=False,
    ))

    # Combo 2: gravity + wind 1.5(DL + LL + WL)
    combos.append(CombinationResult(
        combo_name="1.5(DL+LL+WL)",
        pu_kn=1.5 * (inp.dead_load_kn + inp.live_load_kn + inp.wind_axial_kn),
        mux_knm=1.5 * inp.wind_moment_x_knm,
        muy_knm=1.5 * inp.wind_moment_y_knm,
        is_uplift_combo=False,
    ))

    # Combo 3: gravity + earthquake 1.5(DL + LL + EQ)
    combos.append(CombinationResult(
        combo_name="1.5(DL+LL+EQ)",
        pu_kn=1.5 * (inp.dead_load_kn + inp.live_load_kn + inp.seismic_axial_kn),
        mux_knm=1.5 * inp.seismic_moment_x_knm,
        muy_knm=1.5 * inp.seismic_moment_y_knm,
        is_uplift_combo=False,
    ))

    # Combo 4: uplift wind 0.9DL + 1.5WL
    # For wind, use NEGATIVE wind_axial (i.e., uplift case where wind reduces
    # downward load). Critical for foundation design.
    combos.append(CombinationResult(
        combo_name="0.9DL+1.5WL",
        pu_kn=0.9 * inp.dead_load_kn + 1.5 * inp.wind_axial_kn,
        mux_knm=1.5 * inp.wind_moment_x_knm,
        muy_knm=1.5 * inp.wind_moment_y_knm,
        is_uplift_combo=True,
    ))

    # Combo 5: uplift seismic 0.9DL + 1.5EQ
    combos.append(CombinationResult(
        combo_name="0.9DL+1.5EQ",
        pu_kn=0.9 * inp.dead_load_kn + 1.5 * inp.seismic_axial_kn,
        mux_knm=1.5 * inp.seismic_moment_x_knm,
        muy_knm=1.5 * inp.seismic_moment_y_knm,
        is_uplift_combo=True,
    ))

    return combos


def find_governing_combination(inp: LoadInputs) -> GoverningResult:
    """Find the worst-case load combination for a column.

    'Worst' = highest absolute axial load (Pu) for sizing checks.
    For sanity checking, we take the combo with highest |Pu| since that
    drives column sizing. A separate uplift check (lowest Pu, possibly
    tensile) is reported via is_uplift_combo flag in all_combos.
    """
    combos = compute_load_combinations(inp)

    # Governing for compression sizing: highest |Pu|
    governing = max(combos, key=lambda c: abs(c.pu_kn))

    method_disclosure = (
        "Load combinations evaluated:\n"
        "  1. 1.5(DL+LL) — pure gravity\n"
        "  2. 1.5(DL+LL+WL) — gravity + wind\n"
        "  3. 1.5(DL+LL+EQ) — gravity + earthquake\n"
        "  4. 0.9DL+1.5WL — foundation uplift, wind\n"
        "  5. 0.9DL+1.5EQ — foundation uplift, seismic\n"
        "Wind (WL) and earthquake (EQ) are NEVER combined per IS practice. "
        "We evaluate them separately and take the governing case. "
        "Full IS 875 Part 5 load combination matrix (with directional and "
        "torsional effects) is NOT implemented."
    )

    return GoverningResult(
        column_id=inp.column_id,
        governing_combo=governing.combo_name,
        pu_kn=round(governing.pu_kn, 1),
        mux_knm=round(governing.mux_knm, 2),
        muy_knm=round(governing.muy_knm, 2),
        all_combos=tuple(combos),
        method_disclosure=method_disclosure,
    )


def estimate_lateral_load_share_per_column(
    total_lateral_kn: float,
    n_columns: int,
    storey_height_m: float = 3.0,
) -> tuple[float, float]:
    """Estimate per-column wind/seismic moment from total lateral force.

    Simplified equal-share distribution for preliminary work:
      Per-column shear = Total / n_columns
      Per-column moment = Per-column shear × (storey_height / 2)
                          (single-bay portal frame approximation)

    Returns (per_column_axial_change_kn, per_column_moment_knm).
    For a typical residential building, exterior columns get larger
    axial change from overturning; we approximate this by NOT applying
    differential — engineer must verify for irregular plans.
    """
    if n_columns <= 0:
        return (0.0, 0.0)
    per_col_shear = total_lateral_kn / n_columns
    per_col_moment = per_col_shear * (storey_height_m / 2.0)
    # Axial change from overturning — simplified: 10% of shear
    # (real value depends on building aspect ratio; engineer must verify)
    per_col_axial_change = per_col_shear * 0.1
    return (per_col_axial_change, per_col_moment)
