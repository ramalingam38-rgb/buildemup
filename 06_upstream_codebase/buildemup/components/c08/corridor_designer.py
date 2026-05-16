"""
BuildemUp† — Component 8 (Corridor Designer) — Public orchestrator.

Per C8 SPEC v0.5 LOCKED § 5 invocation contract.

Public entry point:
    designed = design_corridors(
        oriented_candidates=c6_output,
        grid=c7_grid,
        plot_analysis=plot_analysis,
        config=CorridorDesignConfig(),  # optional
    )

Cardinality: 1-3 in → 1-3 out, position-paired (per § 14.3 / Q3).

†= placeholder name marker.
"""
from __future__ import annotations

import time
from typing import Sequence

from buildemup.components.c04.schema import PlotAnalysis, PlotShape
from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    TopologyKind,
    ZoneBand,
)
from buildemup.components.c06.schema import OrientedCandidate
from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08.area_accounting import (
    polygon_union_area_m2,
    segment_additive_area_m2,
)
from buildemup.components.c08.errors import (
    CorridorDispatchError,
    CorridorSelfIntersectionError,
    CorridorTooNarrowError,
)
from buildemup.components.c08.grid_alignment import derive_grid_lines
from buildemup.components.c08.junction_propagation import (
    propagate_junction_widths,
)
from buildemup.components.c08.schema import (
    ConsumptionBand,
    CorridorDesignConfig,
    CorridorDesignedCandidate,
    CorridorPath,
    CorridorProvenance,
    CorridorSegment,
    GridAlignmentReport,
    WidthQuantization,
    ZoneBandEnvelope,
)
from buildemup.components.c08.spatial_model import derive_zone_band_envelopes
from buildemup.components.c08.topology_dispatch import (
    dispatch_topology,
    snap_junctions,
)
from buildemup.components.c08.validator import validate_corridor_path
from buildemup.components.c08.width_selection import select_corridor_width


def _classify_consumption_band(
    fraction: float, thresholds: tuple[float, float],
) -> ConsumptionBand:
    """Classify the envelope-area-fraction into LOW / MEDIUM / HIGH per § 4.9."""
    low_high, mid_high = thresholds
    if fraction < low_high:
        return ConsumptionBand.LOW
    if fraction < mid_high:
        return ConsumptionBand.MEDIUM
    return ConsumptionBand.HIGH


def _trace_id(prefix: str, ts: float) -> str:
    """Build a short trace identifier for provenance.

    DEPRECATED for upstream-trace fields (B-135 / S33): trace IDs that
    correlate to upstream artifacts (oriented_candidate, grid) are now
    propagated directly via _upstream_trace_ids(). This helper is retained
    only as a defensive fallback for cases where upstream lacks a trace_id.
    """
    return f"{prefix}_{int(ts * 1000) % 10**9}"


def _upstream_trace_ids(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    started_at: float,
) -> tuple[str, str]:
    """Resolve the upstream trace IDs for CorridorProvenance (B-135).

    Per § 10 — the trace IDs on CorridorProvenance must correlate to upstream
    artifacts so a downstream debugging pass can answer "what C6 candidate
    produced this corridor?"

    Returns:
        (oriented_candidate_trace_id, grid_trace_id)

    Falls back to synthesized IDs only when upstream lacks a trace field.
    Currently:
      - C6.OrientationPriority.provenance.plot_analysis_trace_id is read for
        oriented_candidate_trace_id (correlates back to C4 plot analysis,
        which is the canonical root of all per-candidate traces).
      - C7.Grid carries no trace_id field today (filed as follow-up backlog
        B-NNN-grid-trace); synthesized fallback is used.
    """
    try:
        oc_trace = oriented_candidate.orientation.provenance.plot_analysis_trace_id
        if not isinstance(oc_trace, str) or not oc_trace:
            oc_trace = _trace_id("c6cand_fallback", started_at)
    except AttributeError:
        oc_trace = _trace_id("c6cand_fallback", started_at)

    # C7 Grid does not yet expose a trace_id field; fallback synthesized.
    # When B-NNN-grid-trace lands, replace with: grid.provenance.trace_id
    grid_trace = _trace_id("c7grid", started_at)
    return oc_trace, grid_trace


def _compute_total_length_m(segments: Sequence[CorridorSegment]) -> float:
    return sum(s.length_m for s in segments)


def _measure_grid_alignment(
    segments: tuple[CorridorSegment, ...],
    grid: Grid,
    config: CorridorDesignConfig,
) -> tuple[int, int, int]:
    """B-132 (S33): measure real grid-edge alignment.

    For each segment, compute the two wall-edge coordinates (the parallels
    at ±constant_width_m/2 from the centerline) on the segment's
    perpendicular axis. Look up whether each coordinate matches a grid line
    within ``config.epsilon_m``.

    Tapered edges (where the segment width transitions from start_width
    to constant_width or constant_width to end_width) are excluded from
    the aligned/total counts and reported separately, per Inv 17.

    Args:
        segments: corridor segments to measure.
        grid: structural grid carrying ``columns_x_count``/``columns_y_count``
            and bay dimensions; grid lines derived via derive_grid_lines.
        config: epsilon_m for snap tolerance.

    Returns:
        ``(edges_aligned, edges_total, tapered_edges)`` per spec § 4.2 + Inv 17.
    """
    from buildemup.components.c08.grid_alignment import derive_grid_lines
    if not segments:
        return 0, 0, 0
    grid_x_lines, grid_y_lines = derive_grid_lines(grid)
    eps = config.epsilon_m

    edges_aligned = 0
    edges_total = 0
    tapered_edges = 0

    for seg in segments:
        sx0, sy0 = seg.start.point_m
        sx1, sy1 = seg.end.point_m
        is_horizontal = abs(sy0 - sy1) <= eps  # runs along x

        # Each segment has 2 wall edges (on perpendicular sides of centerline).
        # The perpendicular-axis coordinates of those edges:
        if is_horizontal:
            centerline = sy0  # y-axis is perpendicular
            edge_a = centerline - seg.constant_width_m / 2.0
            edge_b = centerline + seg.constant_width_m / 2.0
            grid_lines = grid_y_lines
        else:
            centerline = sx0  # x-axis is perpendicular
            edge_a = centerline - seg.constant_width_m / 2.0
            edge_b = centerline + seg.constant_width_m / 2.0
            grid_lines = grid_x_lines

        # Count tapered edges per Inv 17 (excluded from aligned/total).
        # A segment has a tapered edge for each end where start/end_width
        # differs from constant_width.
        if abs(seg.start_width_m - seg.constant_width_m) > eps:
            tapered_edges += 1
        if abs(seg.end_width_m - seg.constant_width_m) > eps:
            tapered_edges += 1

        # Now check each of the 2 wall edges against grid lines.
        for edge in (edge_a, edge_b):
            edges_total += 1
            for gl in grid_lines:
                if abs(edge - gl) <= eps:
                    edges_aligned += 1
                    break

    return edges_aligned, edges_total, tapered_edges


def _build_grid_alignment_report(
    config: CorridorDesignConfig,
    chosen_fraction: float | None,
    chosen_axis: str | None,
    segments: tuple[CorridorSegment, ...],
    grid: Grid,
) -> GridAlignmentReport:
    """Produce a real, measured GridAlignmentReport (B-132 / S33).

    Per § 4.2: tracks per-edge grid alignment by measuring each wall-edge
    coordinate against the actual grid lines (derived from grid columns).

    Tapered edges are excluded from aligned/total per Inv 17.

    Replaces the v0.5 fabricated-constants implementation, which always
    returned 1.0 for GRID_FRACTIONS, 0.9 for NEAREST_GRID_LINE, 0.0 for
    NONE_FREE_WIDTH — those constants are now true measurements.
    """
    edges_aligned, edges_total, tapered_edges = _measure_grid_alignment(
        segments, grid, config,
    )

    # Real alignment score = aligned / total, capped at 1.0.
    if edges_total > 0:
        score = min(1.0, edges_aligned / edges_total)
    else:
        score = 1.0  # vacuously aligned (no segments)

    return GridAlignmentReport(
        quantization_used=config.width_quantization,
        edges_aligned_count=edges_aligned,
        edges_total_count=edges_total,
        tapered_edges_count=tapered_edges,
        grid_alignment_score=score,
        chosen_width_fraction=chosen_fraction,
        chosen_bay_axis=chosen_axis,
        envelope_symmetry_score=0.0,
    )


def design_one_corridor(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    *,
    config: CorridorDesignConfig,
    candidate_index: int = 0,
) -> CorridorDesignedCandidate:
    """Design the corridor for a single OrientedCandidate.

    Internal helper for the public ``design_corridors`` entry point.
    """
    started_at = time.time()
    rule_trace: list[str] = []
    fallback_used = False

    plot = oriented_candidate.topology_candidate
    sketch = plot.corridor_sketch

    # 1. Derive ZoneBandEnvelopes (§ 4.0)
    envelopes = derive_zone_band_envelopes(
        oriented_candidate, grid, config=config,
    )
    rule_trace.append(f"envelopes_derived_n={len(envelopes)}")

    # 2. Determine has_corridor and choose width (or skip)
    is_no_corridor = (
        plot.kind == TopologyKind.STRIP
        and sketch.position == CorridorPosition.NONE
    )
    if is_no_corridor:
        # Degenerate path (§ 4.3.2)
        path = CorridorPath(
            has_corridor=False,
            segments=(),
            envelopes=envelopes,
            total_length_m=0.0,
            total_area_m2=0.0,
            consumption_band=ConsumptionBand.LOW,
            connectivity_type=sketch.connectivity_type,
            grid_alignment=GridAlignmentReport(
                quantization_used=config.width_quantization,
                edges_aligned_count=0,
                edges_total_count=0,
                tapered_edges_count=0,
                grid_alignment_score=1.0,
                chosen_width_fraction=None,
                chosen_bay_axis=None,
            ),
        )
        rule_trace.append("degenerate_path_no_corridor")
    else:
        # 3. Choose corridor width (§ 4.3 + § 4.3.1 envelope-overflow narrowing)
        # B-136 (S33): supply the perpendicular envelope dimension so width
        # selection can narrow on overflow. The corridor sits in the
        # CIRCULATION strip between band envelopes; for the v1 cardinal-strip
        # model, the binding perpendicular dimension is min(envelope_width_m,
        # envelope_depth_m) — whichever bay axis the corridor will run along
        # is determined by select_grid_fraction_width itself.
        envelope_dim_for_width = min(grid.envelope_width_m, grid.envelope_depth_m)
        width_m, chosen_fraction, chosen_axis = select_corridor_width(
            grid, config, envelope_dim_m=envelope_dim_for_width,
        )
        rule_trace.append(
            f"width_selected_{width_m:.3f}m_fraction={chosen_fraction}_axis={chosen_axis}"
        )

        # 4. Dispatch topology (§ 4.1)
        segments = dispatch_topology(
            oriented_candidate, grid, envelopes, width_m,
            config=config, candidate_index=candidate_index,
        )
        rule_trace.append(f"topology_dispatched_{plot.kind.value}_n_segments={len(segments)}")

        # 4.5 Junction-snap normalization (§ 4.7 step 2; B-134 / S33).
        # Force every JUNCTION endpoint to canonical coordinates so that
        # Inv 4 geometric-connectivity is robust against FP drift across
        # multi-segment paths. Idempotent and a no-op when dispatchers
        # already produce coincident tuples (most v1 dispatchers).
        segments = snap_junctions(segments, epsilon_m=config.epsilon_m)
        rule_trace.append("junctions_snapped")

        # 5. Junction-width propagation (§ 4.10)
        propagated, prop_trace = propagate_junction_widths(
            list(segments), config=config, grid=grid,
        )
        segments_tuple = tuple(propagated)
        rule_trace.extend(prop_trace)

        # 6. Area accounting (§ 4.8)
        union_area = polygon_union_area_m2(segments_tuple, cell_m=0.01)
        additive_sum = sum(
            segment_additive_area_m2(s) for s in segments_tuple
        )
        overlap_area = max(0.0, additive_sum - union_area)

        # 7. Envelope-area fraction
        envelope_area = grid.envelope_width_m * grid.envelope_depth_m
        if envelope_area > 0:
            envelope_fraction = union_area / envelope_area
        else:
            envelope_fraction = 0.0

        # 8. Consumption-band classification (§ 4.9)
        consumption_band = _classify_consumption_band(
            envelope_fraction, config.consumption_band_thresholds,
        )

        # 9. Grid-alignment report (real measurement per B-132 / S33)
        grid_report = _build_grid_alignment_report(
            config, chosen_fraction, chosen_axis, segments_tuple, grid,
        )

        path = CorridorPath(
            has_corridor=True,
            segments=segments_tuple,
            envelopes=envelopes,
            total_length_m=_compute_total_length_m(segments_tuple),
            total_area_m2=union_area,
            consumption_band=consumption_band,
            connectivity_type=sketch.connectivity_type,
            grid_alignment=grid_report,
        )

    # 10. Validator (§ 4.6)
    grid_x_lines, grid_y_lines = derive_grid_lines(grid)
    validate_corridor_path(
        path, grid,
        config=config,
        grid_x_lines=grid_x_lines,
        grid_y_lines=grid_y_lines,
    )
    rule_trace.append("validator_ok")

    # 11. Provenance
    if path.has_corridor:
        envelope_area = grid.envelope_width_m * grid.envelope_depth_m
        oc_trace, grid_trace = _upstream_trace_ids(
            oriented_candidate, grid, started_at,
        )
        provenance = CorridorProvenance(
            derived_at=started_at,
            oriented_candidate_trace_id=oc_trace,
            grid_trace_id=grid_trace,
            config_snapshot=config,
            rule_trace=tuple(rule_trace),
            fallback_used=fallback_used,
            envelope_area_consumed_m2=path.total_area_m2,
            envelope_area_fraction=(
                path.total_area_m2 / envelope_area
                if envelope_area > 0 else 0.0
            ),
            additive_sum_m2=sum(
                segment_additive_area_m2(s) for s in path.segments
            ),
            overlap_area_m2=max(
                0.0,
                sum(segment_additive_area_m2(s) for s in path.segments)
                - path.total_area_m2,
            ),
        )
    else:
        oc_trace, grid_trace = _upstream_trace_ids(
            oriented_candidate, grid, started_at,
        )
        provenance = CorridorProvenance(
            derived_at=started_at,
            oriented_candidate_trace_id=oc_trace,
            grid_trace_id=grid_trace,
            config_snapshot=config,
            rule_trace=tuple(rule_trace),
            fallback_used=False,
            envelope_area_consumed_m2=0.0,
            envelope_area_fraction=0.0,
            additive_sum_m2=0.0,
            overlap_area_m2=0.0,
        )

    return CorridorDesignedCandidate(
        oriented_candidate=oriented_candidate,
        corridor_path=path,
        provenance=provenance,
    )


def design_corridors(
    oriented_candidates: Sequence[OrientedCandidate],
    grid: Grid,
    plot_analysis: PlotAnalysis,
    *,
    config: CorridorDesignConfig | None = None,
) -> tuple[CorridorDesignedCandidate, ...]:
    """Public entry point. Per § 5.

    Args:
        oriented_candidates: tuple of 1-3 OrientedCandidate from C6.
        grid: Grid from C7.
        plot_analysis: PlotAnalysis from C4.
        config: optional CorridorDesignConfig; defaults are fine for v1.

    Returns:
        Tuple of CorridorDesignedCandidate, one per input candidate,
        position-paired (per § 14.3 / Q3).

    Raises:
        TypeError: when input types are wrong.
        NotImplementedError: when plot.shape != RECTANGULAR (B-066).
        CorridorTooNarrowError, CorridorSelfIntersectionError,
        CorridorDispatchError: per § 6 failure modes.
    """
    if not isinstance(oriented_candidates, tuple):
        # Accept any tuple-like (list ok per Sequence type) but contract is tuple
        if not hasattr(oriented_candidates, "__iter__"):
            raise TypeError(
                f"design_corridors: oriented_candidates must be a tuple/sequence; "
                f"got {type(oriented_candidates).__name__}"
            )
    if not isinstance(grid, Grid):
        raise TypeError(
            f"design_corridors: grid must be Grid; "
            f"got {type(grid).__name__}"
        )
    if not isinstance(plot_analysis, PlotAnalysis):
        raise TypeError(
            f"design_corridors: plot_analysis must be PlotAnalysis; "
            f"got {type(plot_analysis).__name__}"
        )
    if plot_analysis.shape != PlotShape.RECTANGULAR:
        raise NotImplementedError(
            f"design_corridors: only PlotShape.RECTANGULAR is supported in v1; "
            f"got {plot_analysis.shape.value} (see B-066)"
        )

    if config is None:
        config = CorridorDesignConfig()

    candidates_tuple = tuple(oriented_candidates)
    if not candidates_tuple:
        return ()

    results: list[CorridorDesignedCandidate] = []
    for i, oc in enumerate(candidates_tuple):
        if not isinstance(oc, OrientedCandidate):
            raise TypeError(
                f"design_corridors: oriented_candidates[{i}] must be "
                f"OrientedCandidate; got {type(oc).__name__}"
            )
        designed = design_one_corridor(
            oc, grid, plot_analysis,
            config=config, candidate_index=i,
        )
        results.append(designed)

    return tuple(results)


__all__ = [
    "design_corridors",
    "design_one_corridor",
]
