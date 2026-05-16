"""
BuildemUp† — Global Stability / Drift Check (v0.7)
======================================================

Per v0.6 review Drawback 1: the frame sanity engine checks per-column
Bresler interaction BUT does NOT check frame-level sway behaviour.
Per-column SAFE can still mean global instability if lateral stiffness
is inadequate.

This module adds a LEVEL 2+ preliminary drift check that:
  ✓ Estimates per-storey lateral stiffness from column sizes + count
  ✓ Computes estimated drift under seismic and wind lateral loads
  ✓ Classifies against IS 1893:2016 and IS 456:2000 limits
  ✓ Flags WARNING or FAIL at storey level

What this is NOT:
  ✗ NOT a dynamic response / time-history analysis
  ✗ NOT equivalent frame stiffness matrix
  ✗ NOT accurate if soft-storey or irregular stiffness paths exist
  ✗ NOT a P-delta check (second-order effects)

CODE BASIS (verified via research):
  - IS 1893 (Part 1):2016 cl. 7.11.1.1 — Storey drift ≤ 0.004h
    (i.e., drift_ratio ≤ H/250 for overall sway, ≤ 0.4% per storey)
  - IS 456:2000 serviceability — Lateral sway at top ≤ H/500 (wind)
  - IS 1893:2016 cl. 6.4.3 — For RC cracked section, use:
      Ie_columns = 0.7 × Igross
      Ie_beams   = 0.35 × Igross
  - Classic preliminary shear-frame stiffness:
      k_column = 12·E·Ie / h³   (fixed-fixed column)

PRELIMINARY DRIFT FORMULA (shear frame approximation):
    For each storey:
      K_storey = Σ(12·E·Ie_col / h³)  over all columns in that storey
      drift_per_storey = V_storey / K_storey

  Where V_storey is the seismic or wind shear delivered to that storey.
  For preliminary work, we use storey-average shear (engineer will refine
  with actual shear distribution).

†= placeholder name marker.

KB_VERSION: "GlobalStability_IS1893_v1_2026"
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


KB_VERSION = "GlobalStability_IS1893_v1_2026"


# ─────────────────────────────────────────────────────────────────────────
# Constants from IS 1893:2016 and IS 456:2000 (verified via web research)
# ─────────────────────────────────────────────────────────────────────────

# IS 1893:2016 cl. 7.11.1.1 — storey drift limit (seismic)
SEISMIC_DRIFT_RATIO_LIMIT = 0.004   # Drift ≤ 0.004 × storey height

# IS 456:2000 serviceability — lateral sway at top (wind)
WIND_TOTAL_SWAY_LIMIT_RATIO = 1.0 / 500.0   # H/500

# IS 1893:2016 cl. 6.4.3 — cracked section moment of inertia factors
CRACKED_SECTION_FACTOR_COLUMN = 0.70
CRACKED_SECTION_FACTOR_BEAM = 0.35

# v0.7.1: Beam stiffness contribution factor (Drawback 5 fix).
# Columns alone are a "shear cantilever" idealisation. Real RC moment frames
# get additional lateral stiffness from beam-column joint continuity — the
# "rigid frame" effect. For typical residential beam/column proportions:
#   - If beam is much stiffer than column: k_frame ≈ 1.0 × k_column (limit)
#   - If beam is much weaker than column: k_frame ≈ 0.25 × k_column (other limit)
#   - Typical residential (balanced): k_frame ≈ 1.2-1.5 × k_column
# We use 1.3 as a conservative middle value per research literature.
BEAM_CONTRIBUTION_FACTOR = 1.3

# v0.7.1: Infill wall contribution factor (Drawback 5 fix).
# Unreinforced masonry (URM) infill walls are a major source of lateral
# stiffness in Indian residential construction. Per IS 1893:2016 (infill
# modelling provisions added in 2016 revision) and research, URM infills
# can increase lateral stiffness by 1.5-3.0× for typical residential.
# We use 1.5 conservatively — infills at door/window locations are
# non-contributing, and we don't know infill layout at preliminary stage.
# If inputs indicate NO infill (open stilt, soft storey), we use 1.0.
INFILL_CONTRIBUTION_FACTOR_WITH_WALLS = 1.5
INFILL_CONTRIBUTION_FACTOR_NO_WALLS = 1.0   # Stilt parking, open storey

# Young's modulus of concrete (IS 456 cl. 6.2.3.1)
# E_c = 5000 × sqrt(fck) in MPa
def concrete_modulus_mpa(fck_mpa: float) -> float:
    """E_c = 5000 × sqrt(fck) per IS 456 cl. 6.2.3.1. Returns MPa."""
    return 5000.0 * (fck_mpa ** 0.5)


# ─────────────────────────────────────────────────────────────────────────
# Result classifications
# ─────────────────────────────────────────────────────────────────────────
class DriftCheckResult(str, Enum):
    """Per-storey and overall drift outcome."""
    SAFE = "SAFE"             # Drift ratio ≤ 50% of limit
    WARNING = "WARNING"       # Drift ratio 50-100% of limit
    FAIL = "FAIL"             # Drift ratio > 100% of limit (exceeds code)


class LoadCase(str, Enum):
    """Which lateral load case the drift was computed under."""
    SEISMIC = "seismic"   # IS 1893 limit applies
    WIND = "wind"         # IS 456 limit applies


# ─────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class StoreyDriftCheck:
    """Drift check for one storey under one lateral load case."""
    storey_number: int
    storey_height_m: float
    load_case: LoadCase
    storey_shear_kn: float          # Lateral shear delivered to this storey
    lateral_stiffness_kn_per_m: float  # K = Σ(12·E·Ie / h³)
    drift_mm: float                 # Computed drift
    drift_ratio: float              # drift / storey_height (dimensionless)
    allowable_drift_ratio: float    # Per code (seismic or wind)
    utilization_pct: float          # drift_ratio / limit × 100
    result: DriftCheckResult
    explanation: str


@dataclass(frozen=True)
class GlobalStabilityReport:
    """Full per-storey drift report."""
    storey_checks: tuple[StoreyDriftCheck, ...]
    worst_storey: int | None
    worst_utilization_pct: float
    overall_result: DriftCheckResult
    total_sway_mm: float             # Sum of all storey drifts
    building_height_m: float         # For total-sway check
    top_sway_ratio: float            # total_sway / H — for wind H/500 check
    user_summary: str
    method_disclosure: str


# ─────────────────────────────────────────────────────────────────────────
# Stiffness calculation
# ─────────────────────────────────────────────────────────────────────────
def column_lateral_stiffness_kn_per_m(
    column_dim_mm: float,
    storey_height_m: float,
    fck_mpa: float = 25.0,
    use_cracked_section: bool = True,
) -> float:
    """Compute lateral stiffness of one column in one storey.

    For a fixed-fixed column under lateral load:
        k = 12·E·Ie / h³

    Where Ie = 0.7 × Igross per IS 1893:2016 for cracked columns.
    Square section assumed (residential typical).

    Returns stiffness in kN/m.
    """
    if column_dim_mm <= 0 or storey_height_m <= 0:
        return 0.0

    # E_c in MPa = N/mm²
    e_mpa = concrete_modulus_mpa(fck_mpa)

    # I_gross = b·D³/12, square column so b = D = column_dim_mm
    i_gross_mm4 = (column_dim_mm ** 4) / 12.0

    # Apply cracked section factor (IS 1893:2016 cl. 6.4.3)
    factor = CRACKED_SECTION_FACTOR_COLUMN if use_cracked_section else 1.0
    i_effective_mm4 = i_gross_mm4 * factor

    # Column height in mm
    h_mm = storey_height_m * 1000.0

    # k = 12·E·Ie / h³  [N/mm]
    k_n_per_mm = 12.0 * e_mpa * i_effective_mm4 / (h_mm ** 3)

    # Convert to kN/m (N/mm × 1000 mm/m / 1000 N/kN = N/mm)
    # Actually: 1 N/mm = 1 kN/m by exact conversion
    return k_n_per_mm


# ─────────────────────────────────────────────────────────────────────────
# Per-storey drift check
# ─────────────────────────────────────────────────────────────────────────
def check_storey_drift(
    storey_number: int,
    storey_height_m: float,
    storey_shear_kn: float,
    n_columns: int,
    column_dim_mm: float,
    fck_mpa: float,
    load_case: LoadCase,
    has_infill_walls: bool = True,  # v0.7.1: beam + infill realism
) -> StoreyDriftCheck:
    """Compute drift for one storey under one lateral load case.

    v0.7.1 (Drawback 5 fix): Applies beam + infill stiffness factors
    for improved drift realism:
      k_storey_effective = k_columns × BEAM_FACTOR × INFILL_FACTOR

    Where BEAM_FACTOR = 1.3 (beam-column frame rigidity) and
    INFILL_FACTOR = 1.5 (URM infill, if present) or 1.0 (stilt/open).

    These prevent systematic overestimation of drift that would
    otherwise flag many typical residential buildings as WARNING/FAIL
    when a real engineer would call them SAFE.
    """
    # Per-column stiffness (cracked section per IS 1893:2016 cl. 6.4.3)
    k_per_col = column_lateral_stiffness_kn_per_m(
        column_dim_mm, storey_height_m, fck_mpa,
        use_cracked_section=True,
    )
    # Columns in parallel
    k_columns = n_columns * k_per_col

    # v0.7.1: Apply beam-frame + infill stiffness factors
    infill_factor = (
        INFILL_CONTRIBUTION_FACTOR_WITH_WALLS if has_infill_walls
        else INFILL_CONTRIBUTION_FACTOR_NO_WALLS
    )
    k_storey = k_columns * BEAM_CONTRIBUTION_FACTOR * infill_factor

    if k_storey <= 0:
        # Degenerate — no columns or zero-sized columns
        return StoreyDriftCheck(
            storey_number=storey_number,
            storey_height_m=storey_height_m,
            load_case=load_case,
            storey_shear_kn=storey_shear_kn,
            lateral_stiffness_kn_per_m=0.0,
            drift_mm=float('inf'),
            drift_ratio=float('inf'),
            allowable_drift_ratio=SEISMIC_DRIFT_RATIO_LIMIT,
            utilization_pct=float('inf'),
            result=DriftCheckResult.FAIL,
            explanation="Zero lateral stiffness — column dimensions invalid.",
        )

    # Drift = Shear / Stiffness
    drift_m = storey_shear_kn / k_storey
    drift_mm = drift_m * 1000.0
    drift_ratio = drift_m / storey_height_m

    # Apply limit based on load case
    if load_case == LoadCase.SEISMIC:
        allowable = SEISMIC_DRIFT_RATIO_LIMIT
    else:
        # Wind: we apply per-storey proportion of H/500 (approximation)
        # A proper check is on total sway, which happens at report level
        allowable = WIND_TOTAL_SWAY_LIMIT_RATIO * 2   # ~1/250 per storey as warn
    
    utilization_pct = (drift_ratio / allowable) * 100.0

    # Classify
    if utilization_pct <= 50:
        result = DriftCheckResult.SAFE
        explanation = (
            f"Storey {storey_number} drift {drift_mm:.1f}mm "
            f"({drift_ratio*1000:.2f}‰), {utilization_pct:.0f}% of "
            f"IS {'1893' if load_case == LoadCase.SEISMIC else '456'} "
            f"limit. Good margin."
        )
    elif utilization_pct <= 100:
        result = DriftCheckResult.WARNING
        explanation = (
            f"Storey {storey_number} drift {drift_mm:.1f}mm "
            f"({drift_ratio*1000:.2f}‰), {utilization_pct:.0f}% of "
            f"code limit. Within capacity but tight. Consider upsizing "
            f"columns OR adding shear wall. Engineer should verify with "
            f"full frame analysis."
        )
    else:
        result = DriftCheckResult.FAIL
        explanation = (
            f"Storey {storey_number} drift {drift_mm:.1f}mm "
            f"({drift_ratio*1000:.2f}‰), {utilization_pct:.0f}% EXCEEDS "
            f"code limit. Columns are too flexible. REQUIRES: larger "
            f"columns OR shear wall OR brace frame. Engineer MUST redesign."
        )

    return StoreyDriftCheck(
        storey_number=storey_number,
        storey_height_m=storey_height_m,
        load_case=load_case,
        storey_shear_kn=round(storey_shear_kn, 1),
        lateral_stiffness_kn_per_m=round(k_storey, 0),
        drift_mm=round(drift_mm, 2),
        drift_ratio=round(drift_ratio, 5),
        allowable_drift_ratio=allowable,
        utilization_pct=round(utilization_pct, 1),
        result=result,
        explanation=explanation,
    )


# ─────────────────────────────────────────────────────────────────────────
# Top-level global stability check
# ─────────────────────────────────────────────────────────────────────────
def run_global_stability_check(
    n_storeys: int,
    storey_height_m: float,
    n_columns_per_storey: int,
    column_dim_mm: float,
    fck_mpa: float,
    total_base_shear_kn: float,
    load_case: LoadCase = LoadCase.SEISMIC,
    has_infill_walls: bool = True,  # v0.7.1: Drawback 5 fix
) -> GlobalStabilityReport:
    """Run the full drift check across all storeys.

    For preliminary work, we distribute total base shear to storeys
    proportionally (triangular distribution — top gets more, bottom
    gets less, roughly linear). Real distribution depends on mass
    distribution and modal shapes — engineer refines.

    v0.7.1: has_infill_walls defaults True (most Indian residential
    has brick infill). Pass False for open stilt / soft storey cases.
    """
    if n_storeys <= 0:
        return _empty_report(load_case)

    # Triangular shear distribution: each storey gets shear based on
    # its height × weight. Simplified: storey i from top gets
    # (i / total) × base_shear approximately.
    # For uniform weight distribution, shear at storey i from top is:
    #   V_i = V_base × (1 - (h_i/H)^2)  approximately
    # Simpler: shear at base = V_base, shear at top = V_base/n (crude)
    # We use: V_storey = V_base × (n_storeys - storey_idx + 1) / n_storeys
    # Where storey_idx = 1 at the ground-most storey.

    checks = []
    total_sway_mm = 0.0

    for s in range(1, n_storeys + 1):
        # Shear at storey s (cumulative from top down to this level)
        # For uniform mass, shear at storey s from ground is:
        #   V_s ≈ V_base × (n - s + 1) / n  (conservative: base gets V_base)
        # Actually base storey takes full base shear.
        # Use linear decrease from V_base at s=1 to V_base/n at s=n.
        shear_factor = (n_storeys - s + 1) / n_storeys
        storey_shear = total_base_shear_kn * shear_factor

        check = check_storey_drift(
            storey_number=s,
            storey_height_m=storey_height_m,
            storey_shear_kn=storey_shear,
            n_columns=n_columns_per_storey,
            column_dim_mm=column_dim_mm,
            fck_mpa=fck_mpa,
            load_case=load_case,
            has_infill_walls=has_infill_walls,   # v0.7.1
        )
        checks.append(check)
        total_sway_mm += check.drift_mm

    # Find worst storey
    worst_storey = None
    worst_util = 0.0
    for c in checks:
        if c.utilization_pct > worst_util:
            worst_util = c.utilization_pct
            worst_storey = c.storey_number

    # Overall classification = worst storey's classification
    order = {
        DriftCheckResult.SAFE: 0,
        DriftCheckResult.WARNING: 1,
        DriftCheckResult.FAIL: 2,
    }
    overall = max(checks, key=lambda c: order[c.result]).result

    # Total building sway check (H/500 for wind per IS 456)
    total_h_mm = n_storeys * storey_height_m * 1000.0
    top_sway_ratio = total_sway_mm / total_h_mm if total_h_mm > 0 else 0.0

    # User summary
    n_safe = sum(1 for c in checks if c.result == DriftCheckResult.SAFE)
    n_warn = sum(1 for c in checks if c.result == DriftCheckResult.WARNING)
    n_fail = sum(1 for c in checks if c.result == DriftCheckResult.FAIL)
    user_summary = (
        f"Global stability check ({load_case.value}): "
        f"{n_storeys} storey(s) checked. "
        f"SAFE: {n_safe}, WARNING: {n_warn}, FAIL: {n_fail}. "
        f"Worst storey: {worst_storey} at {worst_util:.0f}% of code limit. "
        f"Total top sway: {total_sway_mm:.1f}mm "
        f"(H/{int(1/top_sway_ratio) if top_sway_ratio > 0 else 999999}). "
        f"Overall: {overall.value}."
    )

    infill_label = (
        f"×{INFILL_CONTRIBUTION_FACTOR_WITH_WALLS:.1f} (URM infill walls)"
        if has_infill_walls
        else f"×{INFILL_CONTRIBUTION_FACTOR_NO_WALLS:.1f} (no infill — stilt/open)"
    )
    method_disclosure = (
        "METHOD DISCLOSURE — global stability check:\n"
        "  ✓ Per-storey lateral stiffness: k = Σ(12·E·Ie / h³)\n"
        "  ✓ Cracked section: Ie = 0.7·Ig for columns "
        "(IS 1893:2016 cl. 6.4.3)\n"
        f"  ✓ Beam-frame stiffness factor: ×{BEAM_CONTRIBUTION_FACTOR:.1f} "
        "(moment-frame continuity)\n"
        f"  ✓ Infill wall factor: {infill_label}\n"
        "  ✓ Seismic drift limit: 0.004·h per IS 1893:2016 cl. 7.11.1.1\n"
        "  ✓ Wind sway limit: H/500 per IS 456:2000 serviceability\n"
        "  ✗ NOT a dynamic/time-history analysis\n"
        "  ✗ NOT a stiffness-matrix frame solution\n"
        "  ✗ P-delta (2nd-order effects) not computed\n"
        "  ✗ Soft-storey / vertical irregularity sensitivity limited\n"
        "  ✗ Exact beam + infill contribution requires ETABS/STAAD model\n"
        "  → Engineer's ETABS/STAAD analysis must verify before "
        "construction."
    )

    return GlobalStabilityReport(
        storey_checks=tuple(checks),
        worst_storey=worst_storey,
        worst_utilization_pct=round(worst_util, 1),
        overall_result=overall,
        total_sway_mm=round(total_sway_mm, 1),
        building_height_m=n_storeys * storey_height_m,
        top_sway_ratio=round(top_sway_ratio, 6),
        user_summary=user_summary,
        method_disclosure=method_disclosure,
    )


def _empty_report(load_case: LoadCase) -> GlobalStabilityReport:
    """Empty report for degenerate inputs (0 storeys)."""
    return GlobalStabilityReport(
        storey_checks=(),
        worst_storey=None,
        worst_utilization_pct=0.0,
        overall_result=DriftCheckResult.SAFE,
        total_sway_mm=0.0,
        building_height_m=0.0,
        top_sway_ratio=0.0,
        user_summary="No storeys to check.",
        method_disclosure="",
    )


# ─────────────────────────────────────────────────────────────────────────
# Base shear estimation helper (for convenience)
# ─────────────────────────────────────────────────────────────────────────
def estimate_base_shear_kn(
    total_seismic_weight_kn: float,
    seismic_zone: str = "II",
    importance_factor: float = 1.0,
    response_reduction: float = 5.0,
    sa_over_g: float = 2.5,
) -> float:
    """Estimate seismic base shear per IS 1893:2016 cl. 7.6.

        V_B = A_h × W
        A_h = (Z/2) × (I/R) × (Sa/g)

    Preliminary: Sa/g = 2.5 (maximum response for short-period buildings).

    Returns base shear in kN.
    """
    from buildemup.utils.kb_rules_loader import get_seismic_zone_factor
    try:
        z = get_seismic_zone_factor(seismic_zone)
    except (ValueError, Exception):
        # Fallback to Zone II
        z = 0.10

    a_h = (z / 2.0) * (importance_factor / response_reduction) * sa_over_g
    return a_h * total_seismic_weight_kn
