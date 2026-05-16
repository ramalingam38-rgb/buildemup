"""
BuildemUp† — Component 5 (Topology Selector) decision table.

Per C5 SPEC v0.9 LOCKED § 14 (cumulative through v0.2-v0.9).

Implements the multi-branch prior-blending decision table that smoothly maps
(plot, room_brief) to a TopologyPriors quadruple plus provenance metadata.

Cumulative architectural lineage:
  v0.2 § 4.1: hard-filter decision table (4 branches + default)
  v0.3 § 14.1: replace hard filter with soft TopologyPriors (D1)
  v0.3 § 14.2: wide-but-shallow guard (D2 — small in-table fix)
  v0.4 § 14.2: tighten prior spread to {1.0, 0.85, 0.7} (#2)
  v0.4 § 14.4: smooth ramp on shallow plot (#8)
  v0.5 § 14.2: generalize smooth ramps to ALL four thresholds (#4)
  v0.6 § 14.1: multi-branch weighted blending (#2 — no dispatch discontinuity)
  v0.7 § 14.1: PROPER normalization fix (math defect — when raw_total > 1,
               scale all branch weights so they sum to 1; w_default = 0)
  v0.9 § 14.4: capture raw_branch_total in provenance (diagnostic)

Web research (Rule 7): no external standards invoked at this layer; thresholds
trace to the project's architecture doc (Apr 17 session). Empirical recalibration
against Indian-market data is B-090.

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c05.schema import TopologyPriors
from buildemup.domain.floor_brief import FloorRoomBrief


# ─── Architecture-doc thresholds in metric (1 ft = 0.3048 m exact) ──────────
# Q3 adjudication: metric internal; comments may cite ft for traceability.

WIDE_THRESHOLD_M:    float = 26.0 * 0.3048    #  7.9248 m
NARROW_THRESHOLD_M:  float = 22.0 * 0.3048    #  6.7056 m
LARGE_W_THRESHOLD_M: float = 40.0 * 0.3048    # 12.1920 m
LARGE_D_THRESHOLD_M: float = 60.0 * 0.3048    # 18.2880 m

# ─── Smooth-ramp half-widths per v0.5 § 14.2 / NEXT_CLAUDE_HANDOFF #3 ───────
# wide:   ±0.5m around 7.9248m → low=7.4248, high=8.4248
# narrow: ±0.5m around 6.7056m → low=6.2056, high=7.2056
# large_w:±1.0m around 12.192m → low=11.192, high=13.192
# large_d:±1.0m around 18.288m → low=17.288, high=19.288
# shallow: ratio low=0.5, high=0.8

_WIDE_RAMP_LOW    = WIDE_THRESHOLD_M    - 0.5
_WIDE_RAMP_HIGH   = WIDE_THRESHOLD_M    + 0.5
_NARROW_RAMP_LOW  = NARROW_THRESHOLD_M  - 0.5
_NARROW_RAMP_HIGH = NARROW_THRESHOLD_M  + 0.5
_LARGE_W_RAMP_LOW   = LARGE_W_THRESHOLD_M - 1.0
_LARGE_W_RAMP_HIGH  = LARGE_W_THRESHOLD_M + 1.0
_LARGE_D_RAMP_LOW   = LARGE_D_THRESHOLD_M - 1.0
_LARGE_D_RAMP_HIGH  = LARGE_D_THRESHOLD_M + 1.0
_SHALLOW_RAMP_LOW   = 0.5
_SHALLOW_RAMP_HIGH  = 0.8


# ─── Per-branch preferred priors (v0.4 § 14.2 tighter spread {1.0, 0.85, 0.7})

_P_DEFAULT = TopologyPriors(strip=1.0,  central_spine=1.0,  l_shape=0.7, courtyard=0.7)
_P_CORNER  = TopologyPriors(strip=0.85, central_spine=0.7,  l_shape=1.0, courtyard=0.7)
_P_WIDE    = TopologyPriors(strip=1.0,  central_spine=0.85, l_shape=0.7, courtyard=0.7)
_P_NARROW  = TopologyPriors(strip=0.7,  central_spine=1.0,  l_shape=0.7, courtyard=0.7)
_P_LARGE   = TopologyPriors(strip=0.85, central_spine=0.7,  l_shape=0.7, courtyard=1.0)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _smooth_ramp(value: float, low: float, high: float) -> float:
    """Linear ramp: 0.0 when value ≤ low, 1.0 when value ≥ high, linear between.

    Per v0.5 § 14.2 utility (used at every decision-table threshold).
    """
    if high <= low:                                  # defensive (high should always > low)
        return 1.0 if value >= high else 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


# ─── Public entry ──────────────────────────────────────────────────────────


def assign_priors(
    plot_analysis: object,
    room_brief: FloorRoomBrief,
) -> tuple[TopologyPriors, str, Mapping[str, float], float]:
    """Compute the soft prior multipliers for the four topology kinds.

    Per C5 SPEC v0.6 § 14.1 + v0.7 § 14.1 (math fix) + v0.9 § 14.4 (raw total).

    Reads ``plot_analysis.plot.width_m``, ``plot_analysis.plot.depth_m``,
    ``plot_analysis.plot.corner_plot``. The Plot dataclass itself is NOT
    imported here — C5 must consume PlotAnalysis (placeholder guardrail
    test enforces).

    Returns:
        A 4-tuple ``(priors, branch_label, branch_weights, raw_branch_total)``:

          - ``priors``: blended TopologyPriors (each value in [0, 1]).
          - ``branch_label``: human-readable form ``"blend_<dominant>@<weight>"``.
          - ``branch_weights``: frozen mapping with the five normalized weights
            (corner, wide_few_bedrooms, narrow_many_bedrooms, large, default)
            summing to 1.0. For the candidate_decision_table_match field
            and downstream provenance.
          - ``raw_branch_total``: sum of FOUR branch weights BEFORE
            normalization (excludes default). Diagnostic field surfaced in
            TopologyProvenance per v0.9 § 14.4 (#5) — distinguishes scenarios
            that collapse to the same normalized priors.

    Raises:
        AttributeError: if ``plot_analysis.plot`` does not have the expected
        Plot fields. Defensive — C4 contract guarantees these exist.
    """
    plot = plot_analysis.plot
    width_m = plot.width_m
    depth_m = plot.depth_m
    is_corner = bool(plot.corner_plot)

    # ── Smooth-ramp membership factors (v0.5 § 14.2) ─────────────────────
    wide_f       = _smooth_ramp(width_m, _WIDE_RAMP_LOW, _WIDE_RAMP_HIGH)
    narrow_f     = 1.0 - _smooth_ramp(width_m, _NARROW_RAMP_LOW, _NARROW_RAMP_HIGH)
    large_w_f    = _smooth_ramp(width_m, _LARGE_W_RAMP_LOW, _LARGE_W_RAMP_HIGH)
    large_d_f    = _smooth_ramp(depth_m, _LARGE_D_RAMP_LOW, _LARGE_D_RAMP_HIGH)
    # shallow factor: 1.0 = no demotion (depth/width >= 0.8); 0.0 = full demotion (≤ 0.5)
    if width_m > 1e-6:
        ratio_dw = depth_m / width_m
    else:
        ratio_dw = 0.0                               # defensive (Plot validates > 0)
    shallow_f    = _smooth_ramp(ratio_dw, _SHALLOW_RAMP_LOW, _SHALLOW_RAMP_HIGH)

    # ── Brief gating (v0.6 § 14.1) ───────────────────────────────────────
    few_beds  = room_brief.bedroom_count <= 2
    many_beds = room_brief.bedroom_count >= 2

    # ── Per-branch raw weights ───────────────────────────────────────────
    # corner is binary in the input contract (plot.corner_plot is bool); no ramp
    w_corner   = 1.0 if is_corner else 0.0
    w_wide     = wide_f                if (few_beds  and not is_corner) else 0.0
    w_narrow   = narrow_f              if (many_beds and not is_corner) else 0.0
    w_large    = min(large_w_f, large_d_f) if not is_corner else 0.0

    # Apply shallow-plot factor to the wide branch (v0.5 § 14.4 #8 carry-over)
    w_wide *= shallow_f

    # ── v0.9 § 14.4 (#5): capture raw branch total BEFORE normalization ──
    raw_branch_total = w_corner + w_wide + w_narrow + w_large

    # ── v0.7 § 14.1 (#2) MATH DEFECT FIX: proper normalization ───────────
    # When raw sum > 1.0 we MUST scale branch weights down (so they sum to 1)
    # and zero out w_default. Otherwise the blend uses raw weights summing
    # to > 1, producing priors > 1 (the v0.6 bug).
    if raw_branch_total > 1.0:
        scale = 1.0 / raw_branch_total
        w_corner *= scale
        w_wide   *= scale
        w_narrow *= scale
        w_large  *= scale
        w_default = 0.0
    else:
        w_default = 1.0 - raw_branch_total

    # Post-normalization: w_corner + w_wide + w_narrow + w_large + w_default == 1.0

    # ── Convex-combination blend ─────────────────────────────────────────
    blended = TopologyPriors(
        strip = (
            w_corner * _P_CORNER.strip
            + w_wide   * _P_WIDE.strip
            + w_narrow * _P_NARROW.strip
            + w_large  * _P_LARGE.strip
            + w_default* _P_DEFAULT.strip
        ),
        central_spine = (
            w_corner * _P_CORNER.central_spine
            + w_wide   * _P_WIDE.central_spine
            + w_narrow * _P_NARROW.central_spine
            + w_large  * _P_LARGE.central_spine
            + w_default* _P_DEFAULT.central_spine
        ),
        l_shape = (
            w_corner * _P_CORNER.l_shape
            + w_wide   * _P_WIDE.l_shape
            + w_narrow * _P_NARROW.l_shape
            + w_large  * _P_LARGE.l_shape
            + w_default* _P_DEFAULT.l_shape
        ),
        courtyard = (
            w_corner * _P_CORNER.courtyard
            + w_wide   * _P_WIDE.courtyard
            + w_narrow * _P_NARROW.courtyard
            + w_large  * _P_LARGE.courtyard
            + w_default* _P_DEFAULT.courtyard
        ),
    )

    # ── Branch label: dominant by weight (v0.6 § 14.1) ───────────────────
    branches = (
        ("corner",                w_corner),
        ("wide_few_bedrooms",     w_wide),
        ("narrow_many_bedrooms",  w_narrow),
        ("large",                 w_large),
        ("default_strip_or_central", w_default),
    )
    dominant_name, dominant_weight = max(branches, key=lambda kv: kv[1])
    branch_label = f"blend_{dominant_name}@{dominant_weight:.2f}"

    branch_weights = MappingProxyType({
        "corner":                w_corner,
        "wide_few_bedrooms":     w_wide,
        "narrow_many_bedrooms":  w_narrow,
        "large":                 w_large,
        "default":               w_default,
    })

    return blended, branch_label, branch_weights, raw_branch_total


__all__ = [
    "assign_priors",
    "WIDE_THRESHOLD_M",
    "NARROW_THRESHOLD_M",
    "LARGE_W_THRESHOLD_M",
    "LARGE_D_THRESHOLD_M",
]
