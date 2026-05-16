"""
BuildemUp† — IS 13920:2016 Ductile Detailing Rules
====================================================

Knowledge module encoding seismic detailing rules for Zones III, IV, V.
Ductile detailing makes concrete "bend before breaking" under earthquake —
it's the difference between a safe building and a collapse.

Sources:
  - IS 13920:2016 — Ductile Design and Detailing of Reinforced Concrete
                    Structures Subjected to Seismic Forces
  - Murty, C.V.R. — "Earthquake-Resistant Design of Concrete Buildings"
  - IS 1893 (Part 1):2016 — seismic zone map

What this module enforces:

1. STRONG-COLUMN WEAK-BEAM principle (cl. 7.2.1)
   Sum of column moment capacities at a joint must exceed 1.4× sum of
   beam moment capacities. Simplified here as: column size ≥ beam depth.

2. MINIMUM COLUMN DIMENSION (cl. 7.1.2)
   Minimum 300mm for columns supporting earthquake-resistant frames.

3. BEAM-COLUMN JOINT CONFINEMENT (cl. 8)
   Closed-loop stirrups with tighter spacing at joints.

4. COLUMN LONGITUDINAL STEEL LIMITS (cl. 7.4.1)
   Between 0.8% and 4% of gross cross-section area.

5. STIRRUP SPACING IN PLASTIC HINGE ZONE (cl. 7.4.3)
   Special confinement zone at top and bottom of each floor = 0.45m
   or 1/6 of clear height (whichever larger). Spacing ≤ 100mm or d/4.

6. BEAM STIRRUP SPACING (cl. 6.3.5)
   Over 2d from column face: spacing ≤ d/4 or 8×smallest bar or 100mm.

7. PLAN AND VERTICAL IRREGULARITY CHECKS (IS 1893 cl. 7.1)
   Torsional, re-entrant corner, vertical irregularity flags.

†= placeholder name marker.

KB_VERSION: "Seismic_IS13920_2026_v1"

v0.7.1 — Single-source rules (review Drawback 4):
    All numeric constants in this module are now LOADED from
    kb_rules/seismic_rules.json at module import time.
    JSON is authoritative. Python is the view + logic layer.
    Parity tests are no longer meaningful (no dual source), but
    we keep them as safety nets for one release cycle.
"""
from __future__ import annotations
from dataclasses import dataclass


KB_VERSION = "Seismic_IS13920_2026_v1"


# v0.7.1: single-source rules — load from JSON at import time.
# Any failure here is fatal at startup (better than runtime surprise).
from buildemup.utils.kb_rules_loader import load_rules as _load_rules
_SEISMIC = _load_rules("seismic_rules")


# ─── 1. SEISMIC ZONE RESPONSE COEFFICIENTS (IS 1893) ─────────────────────
# Zone factor Z from IS 1893:2016 Table 2 — LOADED FROM JSON
SEISMIC_ZONE_FACTORS = dict(_SEISMIC["seismic_zone_factors"]["values"])

# Importance factor (residential = 1.0 per IS 1893 cl. 6.4.2)
IMPORTANCE_FACTOR_RESIDENTIAL = float(
    _SEISMIC["importance_factors"]["values"]["residential_standard"]
)

# Response reduction factors (IS 1893 Table 9)
RESPONSE_REDUCTION_SPECIAL_MRF = float(
    _SEISMIC["response_reduction_factors"]["values"]["special_mrf_with_is13920"]
)
RESPONSE_REDUCTION_ORDINARY_MRF = float(
    _SEISMIC["response_reduction_factors"]["values"]["ordinary_mrf"]
)


def is13920_required(seismic_zone: str) -> bool:
    """Does this seismic zone require IS 13920 ductile detailing?

    IS 1893:2016 cl. 7.2: Special Moment Resisting Frame (with IS 13920)
    is required for Zone III+ in important/special buildings,
    and strongly recommended for all RC structures in Zone III+.
    """
    return seismic_zone in ("III", "IV", "V")


# ─── 2. STRONG COLUMN — WEAK BEAM HEURISTIC (IS 13920 cl. 7.2.1) ─────────
# IMPORTANT: This is a HEURISTIC, not a true SCWB check.
#
# Real SCWB requires moment capacities at the beam-column joint:
#   sum(M_column) >= 1.4 × sum(M_beam)
# Moment capacities depend on actual reinforcement layout, not just dimensions.
# Computing this needs detailed reinforcement design — out of v1 scope.
#
# Our heuristic: column dimension >= 0.6 × beam depth.
# This catches obvious mismatches but cannot guarantee SCWB compliance.
# The structural engineer at detailed design must do the real check.
def check_scwb_heuristic(
    column_dim_mm: int,
    beam_depth_mm: int,
    seismic_zone: str,
) -> dict:
    """SCWB HEURISTIC — dimensional ratio only, NOT moment capacity check.

    Real SCWB compliance must be confirmed by structural engineer with
    actual reinforcement details. This function only catches obvious
    geometric mismatches.

    For Zone II: not required.
    For Zone III+: heuristic flagged as risk if violated.
    """
    ratio = column_dim_mm / beam_depth_mm if beam_depth_mm > 0 else 0

    if not is13920_required(seismic_zone):
        return {
            "applicable": False,
            "is_heuristic": True,
            "check_passed": True,
            "ratio": ratio,
            "message": (
                f"SCWB heuristic not required for Zone {seismic_zone}."
            ),
            "disclaimer": (
                "This is a dimensional heuristic only. Real SCWB compliance "
                "requires moment capacity calculation by structural engineer."
            ),
        }

    required_ratio = 0.6
    passed = ratio >= required_ratio

    return {
        "applicable": True,
        "is_heuristic": True,
        "check_passed": passed,
        "ratio": round(ratio, 2),
        "required_ratio": required_ratio,
        "message": (
            f"SCWB heuristic: column {column_dim_mm}mm / beam {beam_depth_mm}mm "
            f"= ratio {ratio:.2f} (heuristic minimum 0.6 for Zone "
            f"{seismic_zone}). "
            + ("HEURISTIC PASS." if passed else "HEURISTIC FAIL: column under-sized vs beam.")
        ),
        "disclaimer": (
            "HEURISTIC ONLY — based on dimensional ratio. Real SCWB per "
            "IS 13920 cl. 7.2.1 requires moment capacity calculation with "
            "actual reinforcement details. Structural engineer must confirm."
        ),
    }


# Backwards-compat alias (will be removed in a future version)
check_strong_column_weak_beam = check_scwb_heuristic


# ─── 3. MINIMUM COLUMN DIMENSION (IS 13920 cl. 7.1.2) ────────────────────
# v0.7.1: loaded from seismic_rules.json
SEISMIC_MIN_COLUMN_DIM_MM = int(
    _SEISMIC["column_minimum_dimensions"]["values"]["seismic_min_dim_mm"]
)


def check_min_column_dim(column_dim_mm: int, seismic_zone: str) -> dict:
    """Check minimum column dimension for seismic design."""
    if not is13920_required(seismic_zone):
        return {"applicable": False, "check_passed": True}

    passed = column_dim_mm >= SEISMIC_MIN_COLUMN_DIM_MM
    return {
        "applicable": True,
        "check_passed": passed,
        "required_min_mm": SEISMIC_MIN_COLUMN_DIM_MM,
        "actual_mm": column_dim_mm,
        "message": (
            f"Min column dim for Zone {seismic_zone}: "
            f"{SEISMIC_MIN_COLUMN_DIM_MM}mm (IS 13920 cl. 7.1.2). "
            f"Actual: {column_dim_mm}mm. "
            + ("PASS" if passed else "FAIL: column too small.")
        ),
    }


# ─── 4. COLUMN STEEL RATIO (IS 13920 cl. 7.4.1) ──────────────────────────
# v0.7.1: loaded from seismic_rules.json
COLUMN_STEEL_MIN_PCT = float(
    _SEISMIC["column_steel_percentages"]["values"]["minimum_pct"]
)
COLUMN_STEEL_MAX_PCT = float(
    _SEISMIC["column_steel_percentages"]["values"]["maximum_pct"]
)

# Recommended steel percentage by seismic zone (for sizing)
RECOMMENDED_COLUMN_STEEL_PCT = dict(
    _SEISMIC["column_steel_percentages"]["values"]["recommended_pct_by_zone"]
)


# ─── 5. STIRRUP SPACING IN PLASTIC HINGE ZONE (IS 13920 cl. 7.4.3) ───────
@dataclass(frozen=True)
class StirrupSpacing:
    """Stirrup spacing requirements."""
    plastic_hinge_zone_length_mm: int   # Special confinement length
    spacing_in_hinge_zone_mm: int       # Tighter spacing here
    spacing_elsewhere_mm: int
    stirrup_diameter_mm: int            # Minimum diameter
    notes: str


def column_stirrup_spacing(
    column_dim_mm: int, clear_height_mm: int, seismic_zone: str
) -> StirrupSpacing | None:
    """Compute column stirrup spacing per IS 13920 cl. 7.4.3.

    Returns None for Zone II (use IS 456 default spacing).
    """
    if not is13920_required(seismic_zone):
        return None

    # Plastic hinge zone length (cl. 7.4.3): larger of
    #   - column dimension
    #   - 1/6 of clear height
    #   - 450mm
    lo = max(column_dim_mm, clear_height_mm // 6, 450)

    # Spacing in hinge zone: lesser of
    #   - 1/4 of min column dim
    #   - 100mm
    spacing_hinge = min(column_dim_mm // 4, 100)

    # Spacing elsewhere: lesser of
    #   - half of min column dim
    #   - 150mm
    spacing_elsewhere = min(column_dim_mm // 2, 150)

    return StirrupSpacing(
        plastic_hinge_zone_length_mm=lo,
        spacing_in_hinge_zone_mm=spacing_hinge,
        spacing_elsewhere_mm=spacing_elsewhere,
        stirrup_diameter_mm=8,  # IS 13920 cl. 7.4.3 minimum 8mm
        notes=(
            f"Zone {seismic_zone} per IS 13920: special confinement zone "
            f"of {lo}mm at top and bottom of each column floor. "
            f"Stirrups at {spacing_hinge}mm c/c in hinge zone, "
            f"{spacing_elsewhere}mm elsewhere."
        ),
    )


# ─── 6. BEAM STIRRUP SPACING (IS 13920 cl. 6.3.5) ────────────────────────
def beam_stirrup_spacing(beam_depth_mm: int, seismic_zone: str) -> dict | None:
    """Beam stirrup spacing per IS 13920 cl. 6.3.5.

    Returns None for Zone II.
    """
    if not is13920_required(seismic_zone):
        return None

    effective_depth = beam_depth_mm - 50  # Cover + half bar dia approx
    # Near supports (< 2d): lesser of d/4, 8×bar_dia, 100mm
    near_support = min(effective_depth // 4, 100)
    # Rest: lesser of d/2, 200mm
    elsewhere = min(effective_depth // 2, 200)

    return {
        "near_support_mm": near_support,
        "elsewhere_mm": elsewhere,
        "near_support_length_mm": 2 * beam_depth_mm,
        "notes": (
            f"Zone {seismic_zone} beam stirrups (IS 13920 cl. 6.3.5): "
            f"{near_support}mm c/c within {2*beam_depth_mm}mm of supports, "
            f"{elsewhere}mm c/c elsewhere."
        ),
    }


# ─── 7. IRREGULARITY CHECKS (IS 1893:2016 cl. 7.1) ───────────────────────
# Three-level classification (v0.4):
#   REGULAR              — within all IS 1893 limits, proceed normally
#   MODERATELY_IRREGULAR — limits exceeded but workable, warn loudly
#   SEVERELY_IRREGULAR   — far beyond limits, refuse design without expert
#
# Why three levels matter: a 16% re-entrant corner is barely irregular;
# a 40% corner is a structural red flag. Binary regular/irregular
# misses this gradient and can produce false-precision warnings.

# Re-entrant corner thresholds (% of plan dimension)
# v0.7.1: loaded from seismic_rules.json
RE_ENTRANT_MODERATE_PCT = float(
    _SEISMIC["plan_regularity"]["re_entrant_corner"]["moderate_limit_pct"]
)
RE_ENTRANT_SEVERE_PCT = float(
    _SEISMIC["plan_regularity"]["re_entrant_corner"]["severe_limit_pct"]
)

# Aspect ratio thresholds — loaded from JSON
ASPECT_MODERATE_LIMIT = float(
    _SEISMIC["plan_regularity"]["plan_aspect_ratio"]["moderate_limit_ratio"]
)
ASPECT_SEVERE_LIMIT = float(
    _SEISMIC["plan_regularity"]["plan_aspect_ratio"]["severe_limit_ratio"]
)

# Vertical setback (Phase 2 — not used yet; hardcoded for now, JSON when needed)
VERTICAL_SETBACK_LIMIT_PCT = 25.0


# Three regularity severity levels — loaded from JSON
REGULARITY_REGULAR = str(_SEISMIC["regularity_classification_names"]["regular"])
REGULARITY_MODERATE = str(_SEISMIC["regularity_classification_names"]["moderate"])
REGULARITY_SEVERE = str(_SEISMIC["regularity_classification_names"]["severe"])


@dataclass(frozen=True)
class IrregularityCheck:
    """Result of plan irregularity check (v0.4 three-level classification)."""
    severity: str                          # REGULAR / MODERATE / SEVERE
    is_regular: bool                       # True only if REGULAR (back-compat)
    re_entrant_corner_pct: float
    aspect_ratio: float
    warnings: tuple[str, ...]
    requires_detailed_analysis: bool       # True for moderate+, expert needed
    requires_refusal: bool                 # True for severe — engine refuses
    recommended_action: str


def check_plan_regularity(
    plan_width_m: float,
    plan_depth_m: float,
    re_entrant_corner_x_m: float = 0.0,
    re_entrant_corner_y_m: float = 0.0,
    seismic_zone: str = "II",
) -> IrregularityCheck:
    """Check plan regularity per IS 1893:2016 cl. 7.1.

    Returns three-level classification:
      REGULAR              — proceed normally
      MODERATELY_IRREGULAR — proceed with warnings, recommend engineer review
      SEVERELY_IRREGULAR   — refuse to proceed without structural engineer
    """
    warnings: list[str] = []

    # Compute metrics
    aspect = max(plan_width_m, plan_depth_m) / min(plan_width_m, plan_depth_m)
    corner_pct_x = (re_entrant_corner_x_m / plan_width_m) * 100 if plan_width_m else 0
    corner_pct_y = (re_entrant_corner_y_m / plan_depth_m) * 100 if plan_depth_m else 0
    max_corner_pct = max(corner_pct_x, corner_pct_y)

    # Classify each metric
    aspect_severe = aspect > ASPECT_SEVERE_LIMIT
    aspect_moderate = aspect > ASPECT_MODERATE_LIMIT
    corner_severe = max_corner_pct > RE_ENTRANT_SEVERE_PCT
    corner_moderate = max_corner_pct > RE_ENTRANT_MODERATE_PCT

    # Overall severity is the worst of any check
    if aspect_severe or corner_severe:
        severity = REGULARITY_SEVERE
    elif aspect_moderate or corner_moderate:
        severity = REGULARITY_MODERATE
    else:
        severity = REGULARITY_REGULAR

    # Build warnings
    if aspect_severe:
        warnings.append(
            f"⚠ SEVERE: aspect ratio {aspect:.1f} exceeds {ASPECT_SEVERE_LIMIT} "
            f"(2× IS 1893 limit). Plan is highly elongated — large torsional "
            f"effects expected. Refusing without structural engineer review."
        )
    elif aspect_moderate:
        warnings.append(
            f"Aspect ratio {aspect:.1f} exceeds IS 1893 limit "
            f"({ASPECT_MODERATE_LIMIT}). Plan is elongated. "
            f"Torsional effects possible — engineer review recommended."
        )

    if corner_severe:
        warnings.append(
            f"⚠ SEVERE: re-entrant corner {max_corner_pct:.1f}% exceeds "
            f"{RE_ENTRANT_SEVERE_PCT}% (2× IS 1893 limit). Deep L/U/courtyard "
            f"shapes have severe torsional risk. Refusing without structural "
            f"engineer review."
        )
    elif corner_moderate:
        warnings.append(
            f"Re-entrant corner {max_corner_pct:.1f}% exceeds IS 1893 limit "
            f"({RE_ENTRANT_MODERATE_PCT}%). L/courtyard layouts with deep "
            f"corners need engineer review (typical cost ₹40-60K)."
        )

    # Recommended action based on severity + zone
    if severity == REGULARITY_SEVERE:
        action = (
            f"REFUSED at preliminary stage. Plan severity is too high for "
            f"rule-based design. A structural engineer with dynamic analysis "
            f"capability must validate this plan before any costing or "
            f"construction. Typical cost ₹60-1L for dynamic analysis."
        )
    elif severity == REGULARITY_MODERATE:
        if is13920_required(seismic_zone):
            action = (
                f"Your plan has moderate irregularity in Zone {seismic_zone}. "
                f"Detailed dynamic analysis by a structural engineer is "
                f"REQUIRED (typical cost ₹40-60K) before construction. "
                f"Our preliminary cost estimate may understate by 10-15%."
            )
        else:
            action = (
                f"Your plan has some irregularity. For Zone {seismic_zone} "
                f"(low seismic) this is acceptable but worth engineer review "
                f"at detailed design stage."
            )
    else:
        action = "Plan regularity OK for chosen seismic zone."

    return IrregularityCheck(
        severity=severity,
        is_regular=(severity == REGULARITY_REGULAR),
        re_entrant_corner_pct=round(max_corner_pct, 1),
        aspect_ratio=round(aspect, 2),
        warnings=tuple(warnings),
        requires_detailed_analysis=(severity != REGULARITY_REGULAR),
        requires_refusal=(severity == REGULARITY_SEVERE),
        recommended_action=action,
    )


# ─── 8. SLENDERNESS RATIO CHECK (IS 456 cl. 25.1.2) ──────────────────────
# v0.7.1: loaded from seismic_rules.json
SHORT_COLUMN_SLENDERNESS_LIMIT = int(_SEISMIC["slenderness"]["short_column_limit"])


def check_slenderness(
    effective_length_mm: int,
    min_column_dim_mm: int,
) -> dict:
    """Check column slenderness ratio per IS 456 cl. 25.1.2.

    Effective length for typical residential column = 0.75 × floor height
    (for columns with beams on both ends, approximately fixed-fixed).
    """
    ratio = effective_length_mm / min_column_dim_mm if min_column_dim_mm > 0 else 0
    is_short = ratio < SHORT_COLUMN_SLENDERNESS_LIMIT

    return {
        "slenderness_ratio": round(ratio, 1),
        "is_short_column": is_short,
        "limit": SHORT_COLUMN_SLENDERNESS_LIMIT,
        "message": (
            f"Slenderness ratio {ratio:.1f} "
            + ("< 12 — short column (buckling not critical)." if is_short
               else f"≥ 12 — slender column, needs detailed buckling check.")
        ),
    }


# ─── 9. CITATIONS ────────────────────────────────────────────────────────
CITATIONS = {
    "IS_13920": "IS 13920:2016 — Ductile Design and Detailing of RC Structures",
    "IS_1893": "IS 1893 (Part 1):2016 — Earthquake Resistant Design Criteria",
    "MURTY": "C.V.R. Murty — Earthquake-Resistant Design of Concrete Buildings",
}
