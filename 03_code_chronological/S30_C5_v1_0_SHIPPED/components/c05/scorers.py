"""
BuildemUp† — Component 5 (Topology Selector) per-criterion scorers.

Per C5 SPEC v0.9 LOCKED § 14 (cumulative through v0.2-v0.9).

Implements:
  - The 7 base criterion scorers, each returning a value in [0, 1]
  - Context-aware weight multipliers (v0.3 § 14.3) with renormalization
  - Per-topology min-bedroom factor (v0.7 § 14.2)
  - Q1 design (S30): _topology_base_bedroom_fit per-topology natural-capacity
    table

Cumulative architectural lineage:
  v0.2 § 4.2: 7 criteria + base weights summing to 1.0
  v0.3 § 14.3: context multipliers (corner / T1 / T3) + renormalization
  v0.5 § 14.5: COURTYARD bedroom-count penalty (#8)
  v0.6 § 14.2: smooth bedroom penalty (#4) — replaced step function
  v0.7 § 14.2: per-topology min-bedrooms (extends penalty to all 4 topologies)

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import ClimateZone, PlotTier
from buildemup.components.c05.schema import TopologyKind
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.floor_brief import FloorRoomBrief


# ─── Base weights (v0.2 § 4.2 + Q4 adjudication: starting values) ───────────
BASE_WEIGHTS: Mapping[str, float] = MappingProxyType({
    "width_fit":         0.25,
    "bedroom_fit":       0.20,
    "open_side_count":   0.15,
    "climate_fit":       0.15,
    "corner_fit":        0.10,
    "aspect_ratio_fit":  0.10,
    "corridor_overhead": 0.05,
})
# Invariant: sum(BASE_WEIGHTS.values()) == 1.0 exactly.
# Locked by tests/validation/test_c5_scorers.py::test_base_weights_sum_to_one.


# ─── Per-topology min bedrooms (v0.7 § 14.2 #8) ─────────────────────────────
TOPOLOGY_MIN_BEDROOMS: Mapping[TopologyKind, int] = MappingProxyType({
    TopologyKind.STRIP:         1,
    TopologyKind.CENTRAL_SPINE: 2,
    TopologyKind.L_SHAPE:       2,
    TopologyKind.COURTYARD:     3,
})


# ─── Context multipliers (v0.3 § 14.3) ──────────────────────────────────────


def _context_weight_multipliers(
    plot_analysis: object,
) -> Mapping[str, float]:
    """Per-context multipliers BEFORE renormalization to sum=1.

    Per C5 SPEC v0.3 § 14.3.

    Reads plot_analysis.plot.corner_plot and plot_analysis.tier.
    """
    plot = plot_analysis.plot
    tier = plot_analysis.tier
    is_corner = bool(plot.corner_plot)

    m: dict[str, float] = {k: 1.0 for k in BASE_WEIGHTS}
    if is_corner:
        m["corner_fit"] = 2.0     # boost: must be decisive on corner plots
        m["width_fit"]  = 0.6     # reduce: width matters less when L-shape is in play
    if tier == PlotTier.T3_LARGE:
        m["width_fit"]         = 0.5    # reduce: large plots fit any topology width-wise
        m["corridor_overhead"] = 2.0    # boost: corridor cost matters on big plots
        m["climate_fit"]       = 1.5    # boost: courtyard becomes a real option
    if tier == PlotTier.T1_COMPACT:
        m["bedroom_fit"] = 1.5    # boost: tight plots → bedroom packing dominates
    return MappingProxyType(m)


def effective_weights(plot_analysis: object) -> Mapping[str, float]:
    """Context-multiplied weights renormalized to sum exactly to 1.0.

    Per C5 SPEC v0.3 § 14.3 + v0.4 § 14.5 (max-weight ≤ 0.35 invariant).
    """
    mults = _context_weight_multipliers(plot_analysis)
    raw = {k: BASE_WEIGHTS[k] * mults[k] for k in BASE_WEIGHTS}
    total = sum(raw.values())
    return MappingProxyType({k: v / total for k, v in raw.items()})


# ─── Per-criterion scorers (each returns [0, 1]) ────────────────────────────


def score_width_fit(topology: TopologyKind, plot_analysis: object) -> float:
    """How well plot width accommodates this topology's bands.

    STRIP needs ≥ ~7.9m comfortably; CENTRAL_SPINE prefers ≤ ~6.7m;
    L_SHAPE / COURTYARD are flexible.
    """
    width = plot_analysis.plot.width_m
    if topology == TopologyKind.STRIP:
        # Best fit at 8m+; degrades below 7m and above 12m (gets unwieldy)
        if width >= 8.0 and width <= 12.0:
            return 1.0
        if width < 8.0:
            # Linear from 0 at 5m to 1 at 8m
            return max(0.0, min(1.0, (width - 5.0) / 3.0))
        # width > 12m
        return max(0.4, 1.0 - (width - 12.0) / 8.0)
    if topology == TopologyKind.CENTRAL_SPINE:
        # Best fit at 6-9m; tolerates wider
        if 6.0 <= width <= 9.0:
            return 1.0
        if width < 6.0:
            return max(0.0, min(1.0, (width - 4.0) / 2.0))
        # width > 9m
        return max(0.5, 1.0 - (width - 9.0) / 6.0)
    if topology == TopologyKind.L_SHAPE:
        # L-shape needs at least ~6m width to bend meaningfully
        if width >= 7.0:
            return 1.0
        return max(0.0, min(1.0, (width - 5.0) / 2.0))
    if topology == TopologyKind.COURTYARD:
        # Courtyard needs serious width (≥ 11m) to fit a real open core
        if width >= 11.0:
            return 1.0
        # Linear from 0 at 8m to 1 at 11m
        return max(0.0, min(1.0, (width - 8.0) / 3.0))
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def _topology_base_bedroom_fit(topology: TopologyKind, bedroom_count: int) -> float:
    """Per-topology natural-capacity score (Q1 design, S30).

    Step function over integer bedroom_count — bedroom_count is fundamentally
    an integer (humans don't have 2.5 bedrooms in a brief), so smoothing here
    would be artificial. The smoothing program (v0.4 § 14.4 / v0.5 § 14.2)
    targets continuous variables (width_m, depth_m, depth/width ratio).

    Sweet spots:
      STRIP:         1-2 (single-row layout)
      CENTRAL_SPINE: 2-4 (dual-flank corridor amortizes well)
      L_SHAPE:       2-3 (two arms, ~1-2 bedrooms per arm)
      COURTYARD:     3-5 (perimeter wraps need ≥3 to surround the open core)
    """
    if topology == TopologyKind.STRIP:
        if bedroom_count in (1, 2):
            return 1.0
        if bedroom_count == 3:
            return 0.7
        return 0.4   # >= 4
    if topology == TopologyKind.CENTRAL_SPINE:
        if bedroom_count in (2, 3, 4):
            return 1.0
        if bedroom_count in (1, 5):
            return 0.7
        return 0.4   # 0 or >= 6
    if topology == TopologyKind.L_SHAPE:
        if bedroom_count in (2, 3):
            return 1.0
        if bedroom_count in (1, 4):
            return 0.7
        return 0.4   # 0 or >= 5
    if topology == TopologyKind.COURTYARD:
        if bedroom_count in (3, 4, 5):
            return 1.0
        if bedroom_count in (2, 6):
            return 0.7
        return 0.4   # 0, 1, or >= 7
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def score_bedroom_fit(topology: TopologyKind, room_brief: FloorRoomBrief) -> float:
    """Bedroom-fit scorer per C5 SPEC v0.7 § 14.2 #8.

    Combines Q1 base table with the per-topology min-bedrooms factor
    ``min(1, bedroom_count / min_bedrooms[topology])``.

    Effect of factor (illustrative, multiplied with the base table):
      STRIP min=1:    factor=1.0 for any bedroom_count >= 1
      CENTRAL_SPINE min=2:  factor=0.5 at 1 bed, 1.0 at 2+
      L_SHAPE min=2:        factor=0.5 at 1 bed, 1.0 at 2+
      COURTYARD min=3:      factor=0.333 at 1, 0.667 at 2, 1.0 at 3+
    """
    base = _topology_base_bedroom_fit(topology, room_brief.bedroom_count)
    min_beds = TOPOLOGY_MIN_BEDROOMS[topology]
    if room_brief.bedroom_count <= 0:
        # bedroom_count==0 should give factor=0 (no bedrooms → topology vacuous)
        factor = 0.0
    else:
        factor = min(1.0, room_brief.bedroom_count / float(min_beds))
    return base * factor


def score_open_side_count(topology: TopologyKind, plot_analysis: object) -> float:
    """More open sides → courtyard's main ventilation benefit weakens → favours
    Strip / CENTRAL_SPINE / L_SHAPE on detached plots.

    Reads plot_analysis.neighbour_context.open_sides (tuple[PlotOrientation, ...]).
    """
    n_open = len(plot_analysis.neighbour_context.open_sides)
    # 0 to 4 open sides; map to per-topology preference
    if topology == TopologyKind.STRIP:
        # Strip benefits from open sides (cross-ventilation along front-back axis)
        return min(1.0, n_open / 3.0)              # 0→0, 3→1, 4→1
    if topology == TopologyKind.CENTRAL_SPINE:
        # Central spine benefits from open flanks (cross-ventilation perpendicular to spine)
        return min(1.0, n_open / 3.0)
    if topology == TopologyKind.L_SHAPE:
        # L-shape works on a corner (2 open sides typical); neutral overall
        return 0.6 + 0.1 * min(1.0, n_open / 4.0)  # 0.6 to 0.7 as opens increase
    if topology == TopologyKind.COURTYARD:
        # Courtyard's main job is ventilation when sides are SHARED.
        # Many open sides → courtyard less needed → score declines.
        # 0 open: 1.0; 1 open: 0.85; 2 open: 0.7; 3 open: 0.5; 4 open: 0.3
        if n_open == 0: return 1.0
        if n_open == 1: return 0.85
        if n_open == 2: return 0.7
        if n_open == 3: return 0.5
        return 0.3
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def score_climate_fit(topology: TopologyKind, plot_analysis: object) -> float:
    """Climate suitability per topology.

    Warm-humid (Chennai, Mumbai) favours cross-ventilation → CENTRAL_SPINE,
    COURTYARD. Composite (Delhi) favours STRIP / CENTRAL_SPINE (less courtyard
    benefit due to dust, hot summers). Temperate (Bangalore, Pune, Hyderabad)
    is forgiving — all topologies workable.

    HOT_DRY and COLD are reserved (no v1 city maps to them).
    """
    cz = plot_analysis.climate_zone
    if cz == ClimateZone.WARM_HUMID:
        if topology == TopologyKind.CENTRAL_SPINE: return 1.0
        if topology == TopologyKind.COURTYARD:    return 0.9
        if topology == TopologyKind.STRIP:        return 0.7
        if topology == TopologyKind.L_SHAPE:      return 0.6
    if cz == ClimateZone.COMPOSITE:
        if topology == TopologyKind.STRIP:         return 0.9
        if topology == TopologyKind.CENTRAL_SPINE: return 0.85
        if topology == TopologyKind.L_SHAPE:       return 0.7
        if topology == TopologyKind.COURTYARD:     return 0.5
    if cz == ClimateZone.TEMPERATE:
        if topology == TopologyKind.STRIP:         return 0.85
        if topology == TopologyKind.CENTRAL_SPINE: return 0.85
        if topology == TopologyKind.L_SHAPE:       return 0.75
        if topology == TopologyKind.COURTYARD:     return 0.7
    if cz == ClimateZone.HOT_DRY:                  # Reserved — no v1 city
        if topology == TopologyKind.COURTYARD:     return 1.0
        if topology == TopologyKind.CENTRAL_SPINE: return 0.7
        if topology == TopologyKind.STRIP:         return 0.5
        if topology == TopologyKind.L_SHAPE:       return 0.5
    if cz == ClimateZone.COLD:                     # Reserved — no v1 city
        if topology == TopologyKind.STRIP:         return 0.85
        if topology == TopologyKind.CENTRAL_SPINE: return 0.85
        if topology == TopologyKind.L_SHAPE:       return 0.7
        if topology == TopologyKind.COURTYARD:     return 0.4
    return 0.6                                     # pragma: no cover (defensive)


def score_corner_fit(topology: TopologyKind, plot_analysis: object) -> float:
    """corner_plot=True heavily favours L_SHAPE; 0 for non-corner.

    Per C5 SPEC v0.2 § 4.2.
    """
    is_corner = bool(plot_analysis.plot.corner_plot)
    if not is_corner:
        # Non-corner: L_SHAPE gets 0; others moderate (corner-fit irrelevant)
        if topology == TopologyKind.L_SHAPE:
            return 0.0
        return 0.7
    # Corner plot
    if topology == TopologyKind.L_SHAPE:    return 1.0
    if topology == TopologyKind.STRIP:      return 0.7
    if topology == TopologyKind.CENTRAL_SPINE: return 0.5
    if topology == TopologyKind.COURTYARD:  return 0.5
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def score_aspect_ratio_fit(topology: TopologyKind, plot_analysis: object) -> float:
    """Aspect ratio (depth/width) suitability.

    aspect_ratio > 1.5 (deep plot) penalizes STRIP (front-to-back layout
    becomes a long corridor problem).
    """
    ar = plot_analysis.aspect_ratio
    if topology == TopologyKind.STRIP:
        if ar <= 1.5:                      return 1.0
        if ar <= 2.0:                      return 0.7
        return max(0.3, 1.0 - (ar - 1.5) / 2.0)
    if topology == TopologyKind.CENTRAL_SPINE:
        # Central spine actually benefits from deeper plots
        if 1.2 <= ar <= 2.5:               return 1.0
        if ar < 1.2:                       return 0.7
        return max(0.5, 1.0 - (ar - 2.5) / 2.0)
    if topology == TopologyKind.L_SHAPE:
        # L-shape works at moderate ratios
        if 0.8 <= ar <= 1.8:               return 1.0
        return 0.7
    if topology == TopologyKind.COURTYARD:
        # Courtyard prefers near-square plots
        if 0.9 <= ar <= 1.4:               return 1.0
        if 0.7 <= ar <= 1.7:               return 0.7
        return 0.4
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def score_corridor_overhead(topology: TopologyKind, plot_analysis: object) -> float:
    """Corridor cost — HIGHER raw means LESS overhead (this is fitness).

    Per C5 SPEC v0.2 § 4.2 + v0.6 § 14.4 (tie-break uses raw value:
    higher raw = less overhead = wins ties).

    plot_analysis is accepted for symmetry with other scorers (allows future
    plot-size-dependent overhead). v1 uses topology-only, but signature is
    stable.
    """
    _ = plot_analysis                                # currently unused; signature stable
    # STRIP has the lowest overhead; COURTYARD the highest.
    if topology == TopologyKind.STRIP:         return 1.0
    if topology == TopologyKind.CENTRAL_SPINE: return 0.8
    if topology == TopologyKind.L_SHAPE:       return 0.6
    if topology == TopologyKind.COURTYARD:     return 0.4
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


# ─── Aggregate scorer (returns Mapping[str, float] for select.py) ──────────


def compute_raw_scores(
    topology: TopologyKind,
    plot_analysis: object,
    room_brief: FloorRoomBrief,
) -> Mapping[str, float]:
    """Return all 7 criterion raw scores for a single topology, frozen.

    Per C5 SPEC v0.2 § 4.2 + v0.5 § 14.4 (ScoreBreakdownEntry construction
    happens in select.py using these raw scores).
    """
    return MappingProxyType({
        "width_fit":         score_width_fit(topology, plot_analysis),
        "bedroom_fit":       score_bedroom_fit(topology, room_brief),
        "open_side_count":   score_open_side_count(topology, plot_analysis),
        "climate_fit":       score_climate_fit(topology, plot_analysis),
        "corner_fit":        score_corner_fit(topology, plot_analysis),
        "aspect_ratio_fit":  score_aspect_ratio_fit(topology, plot_analysis),
        "corridor_overhead": score_corridor_overhead(topology, plot_analysis),
    })


__all__ = [
    "BASE_WEIGHTS",
    "TOPOLOGY_MIN_BEDROOMS",
    "effective_weights",
    "compute_raw_scores",
    "score_width_fit",
    "score_bedroom_fit",
    "score_open_side_count",
    "score_climate_fit",
    "score_corner_fit",
    "score_aspect_ratio_fit",
    "score_corridor_overhead",
]
