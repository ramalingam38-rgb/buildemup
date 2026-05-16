"""
BuildemUp† — Component 8 (Corridor Designer) — Width selection module.

Per C8 SPEC v0.5 LOCKED § 4.3 / § 4.3.1 / § 14.19 / § 14.20.

Three selection modes:
  - GRID_FRACTIONS (default per § 14.2): scored selection over
    {1/4, 1/3, 1/2, 2/3, 3/4} × bay_min using asymmetric penalty
    (under-comfort × ratio (default 2.0) vs over-comfort × 1.0)
    per § 14.19.
  - NEAREST_GRID_LINE: caller-driven; uses grid_alignment.find_edge_snap_pair.
  - NONE_FREE_WIDTH: escape hatch; logged loudly in provenance.

Plus ``resolve_taper_zone_m()`` per § 4.3.1 with truncation fallback.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08.errors import CorridorTooNarrowError
from buildemup.components.c08.schema import (
    GRID_FRACTION_CANDIDATES,
    CorridorDesignConfig,
    WidthQuantization,
)
from buildemup.components.c08.tolerances import ARITHMETIC_M


def width_selection_score(
    candidate_m: float,
    comfort_m: float,
    regulatory_m: float,
    ratio: float,
) -> float:
    """Score for choosing between corridor-width candidates.

    Per § 4.3 / § 14.19.

    Lower is better. Below regulatory minimum is disqualified
    (returns ``float('inf')``).

    Asymmetric penalty:
      - candidate < comfort: penalty = (comfort - candidate) × ratio
      - candidate >= comfort: penalty = (candidate - comfort) × 1.0

    Default ``ratio = 2.0`` (DEFAULT_UNDER_COMFORT_PENALTY_RATIO) reflects
    the empirical finding that under-comfort is more occupant-visible than
    over-comfort, but over-comfort still has a real cost (B-123 calibration).
    """
    if candidate_m < regulatory_m:
        return float("inf")
    diff = candidate_m - comfort_m
    if diff < 0:
        return abs(diff) * ratio
    else:
        return diff * 1.0


def select_grid_fraction_width(
    grid: Grid,
    config: CorridorDesignConfig,
    envelope_dim_m: float | None = None,
) -> tuple[float, float, str]:
    """Pick the corridor width using the GRID_FRACTIONS scoring rule.

    Per § 4.3 + § 14.19 + § 4.3.1 (constrained-plot override; B-136 / S33).

    Args:
        grid: structural grid.
        config: tunables.
        envelope_dim_m: when supplied, the perpendicular dimension of the
            buildable envelope (i.e., how much room the corridor has to
            grow on its perpendicular axis without crossing the envelope
            edge). When the chosen scored width would cause envelope
            overflow at envelope-center placement, narrowing falls back
            through the GRID_FRACTION_CANDIDATES from large to small.
            Falls through to last-eligible only if all narrower candidates
            also overflow. ``None`` (default) preserves v0.5 behavior:
            pick the highest-scoring eligible candidate without overflow
            check.

    Returns:
        ``(width_m, chosen_fraction, chosen_axis)`` where ``chosen_axis`` is
        ``'x'`` if bay_x_m is the smaller (== bay_min) or ``'y'`` otherwise.

    Raises:
        CorridorTooNarrowError if no GRID_FRACTION candidate ≥
        regulatory_min_width_m fits, OR if ``envelope_dim_m`` is supplied
        and even the smallest eligible candidate exceeds
        ``regulatory_min_width_m`` while overflowing the envelope.
    """
    if grid.bay_x_m <= grid.bay_y_m:
        bay_min = grid.bay_x_m
        chosen_axis = "x"
    else:
        bay_min = grid.bay_y_m
        chosen_axis = "y"

    # Build candidate widths
    candidate_widths: list[tuple[float, float]] = [
        (f * bay_min, f) for f in GRID_FRACTION_CANDIDATES
    ]

    # Filter to candidates ≥ regulatory minimum
    eligible = [
        (w, f) for (w, f) in candidate_widths
        if w >= config.regulatory_min_width_m - ARITHMETIC_M
    ]

    if not eligible:
        raise CorridorTooNarrowError(
            f"No GRID_FRACTION candidate >= regulatory_min_width_m "
            f"({config.regulatory_min_width_m}m) on bay_min={bay_min}m. "
            f"Candidates: {[round(w, 3) for w, _ in candidate_widths]}",
            bay_min_m=bay_min,
            regulatory_min_width_m=config.regulatory_min_width_m,
            candidate_widths_m=tuple(w for w, _ in candidate_widths),
        )

    # Score and pick the minimum
    best = min(
        eligible,
        key=lambda pair: width_selection_score(
            pair[0],
            config.comfort_target_width_m,
            config.regulatory_min_width_m,
            config.under_comfort_penalty_ratio,
        ),
    )

    # B-136 (S33): § 4.3.1 constrained-plot override.
    # If the scored width would cause envelope-overflow when placed at
    # envelope-center (corridor's two wall edges fall outside [0, envelope_dim_m]),
    # narrow to the next-smaller eligible candidate.
    if envelope_dim_m is not None and best[0] > envelope_dim_m:
        # Sort eligible smallest-to-largest; pick first that fits envelope.
        eligible_sorted = sorted(eligible, key=lambda p: p[0])
        for w, f in eligible_sorted:
            if w <= envelope_dim_m:
                return w, f, chosen_axis
        # No candidate fits envelope — even the smallest exceeds.
        raise CorridorTooNarrowError(
            f"No GRID_FRACTION candidate fits envelope_dim_m={envelope_dim_m:.3f}m "
            f"while >= regulatory_min_width_m ({config.regulatory_min_width_m}m); "
            f"smallest eligible = {eligible_sorted[0][0]:.3f}m exceeds envelope.",
            bay_min_m=bay_min,
            regulatory_min_width_m=config.regulatory_min_width_m,
            candidate_widths_m=tuple(w for w, _ in candidate_widths),
        )

    return best[0], best[1], chosen_axis


def select_corridor_width(
    grid: Grid,
    config: CorridorDesignConfig,
    envelope_dim_m: float | None = None,
) -> tuple[float, float | None, str | None]:
    """Public dispatch over WidthQuantization modes.

    Per § 4.3 + § 4.3.1 (constrained-plot override — B-136 / S33).

    Args:
        grid: structural grid.
        config: tunables.
        envelope_dim_m: when supplied, the perpendicular envelope dimension
            (corridor must fit within this when placed at envelope-center).
            Triggers narrowing fallback through GRID_FRACTION_CANDIDATES.

    Returns ``(width_m, chosen_fraction_or_None, chosen_axis_or_None)``.

    Raises:
        CorridorTooNarrowError if GRID_FRACTIONS exhausts the eligible list,
        or if envelope_dim_m is supplied and even the smallest candidate
        overflows.
    """
    q = config.width_quantization

    if q == WidthQuantization.GRID_FRACTIONS:
        return select_grid_fraction_width(
            grid, config, envelope_dim_m=envelope_dim_m,
        )

    if q == WidthQuantization.NEAREST_GRID_LINE:
        # Caller (corridor_designer) must combine with edge-snap to derive
        # the actual width. This function returns the desired target width;
        # final width may be perturbed by snap-pair selection.
        target = max(config.comfort_target_width_m, config.regulatory_min_width_m)
        # B-136: clamp to envelope_dim_m if supplied
        if envelope_dim_m is not None and target > envelope_dim_m:
            target = max(config.regulatory_min_width_m, envelope_dim_m)
            if target > envelope_dim_m + ARITHMETIC_M:
                raise CorridorTooNarrowError(
                    f"NEAREST_GRID_LINE: target {target}m exceeds "
                    f"envelope_dim_m={envelope_dim_m}m and clamping below "
                    f"regulatory_min_width_m is not allowed.",
                    bay_min_m=min(grid.bay_x_m, grid.bay_y_m),
                    regulatory_min_width_m=config.regulatory_min_width_m,
                    candidate_widths_m=(target,),
                )
        return target, None, None

    if q == WidthQuantization.NONE_FREE_WIDTH:
        target = max(config.comfort_target_width_m, config.regulatory_min_width_m)
        # B-136: clamp to envelope_dim_m if supplied
        if envelope_dim_m is not None and target > envelope_dim_m:
            target = max(config.regulatory_min_width_m, envelope_dim_m)
            if target > envelope_dim_m + ARITHMETIC_M:
                raise CorridorTooNarrowError(
                    f"NONE_FREE_WIDTH: target {target}m exceeds "
                    f"envelope_dim_m={envelope_dim_m}m and clamping below "
                    f"regulatory_min_width_m is not allowed.",
                    bay_min_m=min(grid.bay_x_m, grid.bay_y_m),
                    regulatory_min_width_m=config.regulatory_min_width_m,
                    candidate_widths_m=(target,),
                )
        return target, None, None

    # Defensive — should never hit due to enum validation in config
    raise ValueError(
        f"select_corridor_width: unknown WidthQuantization {q!r}"
    )


def resolve_taper_zone_m(
    config: CorridorDesignConfig,
    grid: Grid,
    segment_length_m: float,
    n_tapered_ends: int = 1,
) -> tuple[float, bool]:
    """Resolve the taper-zone length for a single segment.

    Per § 4.3.1 (N-aware per C8 SPEC v0.6 PROPOSED — resolves B-129 / B-131).

    Default: ``min(grid.bay_x_m, grid.bay_y_m)`` — bay-scale is the natural
    local unit; the taper should be perceptible relative to the bay.

    N-aware truncation fallback: when the proposed taper would overlap with
    itself or exceed the available bound, truncate per
    ``max_allowed = length / (2 × max(1, n_tapered_ends))``.

      - N=1 (default; one end at junction, other at envelope or no taper):
        max_allowed = length/2 (matches v0.5 LOCKED behavior — no breaking change)
      - N=2 (interior segment, both ends taper at junctions):
        max_allowed = length/4 (Inv 20 N-aware tightening — required when caller
        knows both ends will taper)
      - N=0 (defensive; no taper applied): same as N=1

    Args:
        config: tunables; supplies ``taper_zone_m_default`` override.
        grid: bay dimensions (default proposed = min bay).
        segment_length_m: total segment length.
        n_tapered_ends: number of segment ends that will actually taper
            (0, 1, or 2). Default = 1 preserves v0.5 ``length/2`` semantics
            for bare callers; junction_propagation explicitly passes the
            actual count it computes from the segment topology.

    Returns:
        ``(taper_zone_m, truncated)`` — ``truncated`` is True if fallback fired.
    """
    if config.taper_zone_m_default is not None:
        proposed = float(config.taper_zone_m_default)
    else:
        proposed = min(grid.bay_x_m, grid.bay_y_m)

    # N-aware bound per Inv 20: constant_middle = length - n×taper ≥ length/2
    # → taper ≤ length / (2 × max(1, n))
    n = max(1, n_tapered_ends)
    max_allowed = segment_length_m / (2.0 * n)
    if proposed > max_allowed:
        return max_allowed, True
    return proposed, False


__all__ = [
    "width_selection_score",
    "select_grid_fraction_width",
    "select_corridor_width",
    "resolve_taper_zone_m",
]
