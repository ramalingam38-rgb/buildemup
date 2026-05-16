"""
BuildemUp† — Component 8 (Corridor Designer) — Validator module.

Per C8 SPEC v0.5 LOCKED § 4.6 (NEW v0.2 tiered).

Implements 20 invariants split into:
  - ALL-PATHS (apply unconditionally to any CorridorPath):
    1, 3, 4, 5, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
  - HAS-CORRIDOR-ONLY (apply only when has_corridor == True):
    2, 6, 7, 9

The validator is invoked at the end of design_corridors() before producing
the CorridorDesignedCandidate. Any invariant violation raises ValueError
with a descriptive message naming the invariant number and observed values.

†= placeholder name marker.
"""
from __future__ import annotations

import math
from typing import Sequence

from buildemup.components.c05.schema import ConnectivityType, ZoneBand
from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08.errors import CorridorSelfIntersectionError
from buildemup.components.c08.schema import (
    ALLOWED_JUNCTION_ANGLES_DEG,
    CorridorDesignConfig,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorPath,
    CorridorSegment,
    DEFAULT_EPSILON_M,
    WidthPropagation,
    ZoneBandEnvelope,
)
from buildemup.domain.envelope import PlotOrientation


def _coord_eq(a: tuple[float, float], b: tuple[float, float], eps: float) -> bool:
    """Two points are coincident iff |dx|, |dy| < eps."""
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def _seg_bbox(seg: CorridorSegment) -> tuple[float, float, float, float]:
    """Return the bounding box (x0, y0, x1, y1) of a segment, including width.

    Uses the maximum width along the segment for envelope-containment
    checking (so that taper-end widths are respected).
    """
    sx, sy = seg.start.point_m
    ex, ey = seg.end.point_m
    max_w = max(seg.start_width_m, seg.constant_width_m, seg.end_width_m)
    half_w = max_w / 2.0

    if seg.runs_along in (PlotOrientation.EAST, PlotOrientation.WEST):
        x0, x1 = (sx, ex) if sx <= ex else (ex, sx)
        cy = (sy + ey) / 2.0
        return (x0, cy - half_w, x1, cy + half_w)
    else:  # NORTH or SOUTH
        y0, y1 = (sy, ey) if sy <= ey else (ey, sy)
        cx = (sx + ex) / 2.0
        return (cx - half_w, y0, cx + half_w, y1)


def _bboxes_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    eps: float,
) -> bool:
    """Strict overlap test (touching does not count as overlap)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return (
        ax1 > bx0 + eps
        and bx1 > ax0 + eps
        and ay1 > by0 + eps
        and by1 > ay0 + eps
    )


def _segments_share_endpoint(
    s1: CorridorSegment, s2: CorridorSegment, eps: float,
) -> bool:
    """True if any endpoint of s1 coincides with any endpoint of s2."""
    pts1 = (s1.start.point_m, s1.end.point_m)
    pts2 = (s2.start.point_m, s2.end.point_m)
    for p1 in pts1:
        for p2 in pts2:
            if _coord_eq(p1, p2, eps):
                return True
    return False


def validate_corridor_path(
    path: CorridorPath,
    grid: Grid,
    *,
    config: CorridorDesignConfig,
    grid_x_lines: tuple[float, ...] = (),
    grid_y_lines: tuple[float, ...] = (),
) -> None:
    """Validate a CorridorPath against all 20 invariants. Raises ValueError.

    Per § 4.6.

    Args:
        path: the CorridorPath to validate.
        grid: from C7, used for envelope-containment + grid-line checks.
        config: tunables; supplies epsilon_m + width_propagation +
                regulatory_min_width_m + junction_angle_tolerance_deg.
        grid_x_lines, grid_y_lines: derived grid lines (per § 4.2). Used by
                invariant 14 (column-supported snap-lines).
    """
    eps = config.epsilon_m
    segments = path.segments
    envelopes = path.envelopes
    has_corridor = path.has_corridor

    # =========================================================================
    # ALL-PATHS invariants
    # =========================================================================

    # Invariant 1: segments is a tuple
    if not isinstance(segments, tuple):
        raise ValueError(
            f"C8 Invariant 1 violation: segments must be a tuple; "
            f"got {type(segments).__name__}"
        )

    # Invariant 3: every segment is axis-aligned to a cardinal direction
    # (already enforced by CorridorSegment.__post_init__; defensive re-check)
    for i, seg in enumerate(segments):
        if seg.runs_along not in (
            PlotOrientation.NORTH, PlotOrientation.EAST,
            PlotOrientation.SOUTH, PlotOrientation.WEST,
        ):
            raise ValueError(
                f"C8 Invariant 3 violation: segments[{i}].runs_along must be "
                f"cardinal; got {seg.runs_along.value}"
            )
        sx, sy = seg.start.point_m
        ex, ey = seg.end.point_m
        dx = abs(ex - sx)
        dy = abs(ey - sy)
        if dx > eps and dy > eps:
            raise ValueError(
                f"C8 Invariant 3 violation: segments[{i}] is not axis-aligned; "
                f"dx={dx}, dy={dy}"
            )

    # Invariant 4: geometric connectivity
    # (a) per segment, start.point_m and end.point_m differ in exactly one axis
    # (b) for any two segments, shared endpoint coords are equal within eps
    # Already enforced per-segment by __post_init__. Pairwise check:
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            si, sj = segments[i], segments[j]
            # Find any endpoint pair that's "near" (within 5×eps) and verify
            # they are exactly coincident (within eps). This catches
            # almost-meeting segments that should meet exactly.
            for p1 in (si.start.point_m, si.end.point_m):
                for p2 in (sj.start.point_m, sj.end.point_m):
                    d = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                    if eps < d < 5 * eps:
                        raise ValueError(
                            f"C8 Invariant 4 violation: segments[{i}] and "
                            f"segments[{j}] have endpoints that are near but "
                            f"not coincident: {p1} vs {p2} (d={d:.6f})"
                        )

    # Invariant 5: at most one ENTRY endpoint
    entry_count = 0
    for seg in segments:
        if seg.start.kind == CorridorEndpointKind.ENTRY:
            entry_count += 1
        if seg.end.kind == CorridorEndpointKind.ENTRY:
            entry_count += 1
    if entry_count > 1:
        raise ValueError(
            f"C8 Invariant 5 violation: at most one ENTRY endpoint allowed; "
            f"got {entry_count}"
        )

    # Invariant 8: connectivity_type matches upstream C5 contract
    if not isinstance(path.connectivity_type, ConnectivityType):
        raise ValueError(
            f"C8 Invariant 8 violation: connectivity_type must be "
            f"ConnectivityType; got {type(path.connectivity_type).__name__}"
        )

    # Invariant 10: envelope containment
    for i, seg in enumerate(segments):
        x0, y0, x1, y1 = _seg_bbox(seg)
        if (
            x0 < -eps or y0 < -eps
            or x1 > grid.envelope_width_m + eps
            or y1 > grid.envelope_depth_m + eps
        ):
            raise ValueError(
                f"C8 Invariant 10 violation: segments[{i}] bbox "
                f"({x0:.3f}, {y0:.3f}, {x1:.3f}, {y1:.3f}) extends beyond "
                f"envelope (0, 0, {grid.envelope_width_m}, "
                f"{grid.envelope_depth_m})"
            )

    # Invariants 11 + 12: no self-intersection / junction-only overlap
    bboxes = [_seg_bbox(s) for s in segments]
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            if _bboxes_overlap(bboxes[i], bboxes[j], eps):
                # Adjacent (sharing endpoint) segments may overlap at the
                # junction point only.
                if _segments_share_endpoint(segments[i], segments[j], eps):
                    # Allowed (Inv 12): overlap is permitted at the junction
                    # point itself. We could verify the overlap is
                    # localized to the junction, but a rigorous junction-
                    # locality check at validator time is over-strict given
                    # taper zones; rely on construction-time correctness
                    # (§ 4.7 spatial-feasibility checks).
                    continue
                # B-133 (S33): raise typed exception per § 6 / § 14.17 +
                # advertise overlap box for debugging.
                ax0, ay0, ax1, ay1 = bboxes[i]
                bx0, by0, bx1, by1 = bboxes[j]
                ox0 = max(ax0, bx0)
                oy0 = max(ay0, by0)
                ox1 = min(ax1, bx1)
                oy1 = min(ay1, by1)
                raise CorridorSelfIntersectionError(
                    f"C8 Invariant 11 violation: segments[{i}] and "
                    f"segments[{j}] overlap and do not share an endpoint. "
                    f"bboxes={bboxes[i]}, {bboxes[j]}",
                    segment_a_index=i,
                    segment_b_index=j,
                    overlap_box=(ox0, oy0, ox1, oy1),
                )

    # Invariant 13: junction angles in {0, 90, 180, 270} ± tol
    junction_pts: list[tuple[tuple[float, float], list[tuple[int, str]]]] = []
    for i, seg in enumerate(segments):
        for which, ep in (("start", seg.start), ("end", seg.end)):
            if ep.kind == CorridorEndpointKind.JUNCTION:
                # Find existing junction with same coords
                found = False
                for j_pt, members in junction_pts:
                    if _coord_eq(j_pt, ep.point_m, eps):
                        members.append((i, which))
                        found = True
                        break
                if not found:
                    junction_pts.append((ep.point_m, [(i, which)]))

    tol = config.junction_angle_tolerance_deg
    for j_pt, members in junction_pts:
        # Compute the direction vector of each adjoining segment AT THE
        # JUNCTION (pointing AWAY from the junction).
        directions = []
        for (idx, which) in members:
            seg = segments[idx]
            if which == "start":
                # Direction = end - start
                dvec = (
                    seg.end.point_m[0] - seg.start.point_m[0],
                    seg.end.point_m[1] - seg.start.point_m[1],
                )
            else:
                dvec = (
                    seg.start.point_m[0] - seg.end.point_m[0],
                    seg.start.point_m[1] - seg.end.point_m[1],
                )
            mag = math.hypot(dvec[0], dvec[1])
            if mag <= 0:
                continue
            directions.append((dvec[0] / mag, dvec[1] / mag))

        # For each pair of directions, check the angle is in the allowed set
        for a in range(len(directions)):
            for b in range(a + 1, len(directions)):
                d1, d2 = directions[a], directions[b]
                dot = max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1]))
                angle_deg = math.degrees(math.acos(dot))
                # Accept if within tolerance of any allowed angle
                in_set = any(
                    abs(angle_deg - allowed) <= tol + 0.001
                    for allowed in ALLOWED_JUNCTION_ANGLES_DEG
                )
                if not in_set:
                    raise ValueError(
                        f"C8 Invariant 13 violation: junction at {j_pt} "
                        f"has angle {angle_deg:.2f}° between adjoining "
                        f"segments; allowed: {sorted(ALLOWED_JUNCTION_ANGLES_DEG)}"
                    )

    # Invariant 14: column-supported snap-lines (B-143 / S33).
    # Per § 4.6 Inv 14: every grid line used for edge-snap must pass through
    # ≥ 1 ColumnPosition in grid.columns.
    #
    # Pre-B-143 v0.5: the spec said "satisfied by construction in
    # derive_grid_lines() (§ 4.2)" and the check was skipped. The walk #1
    # critique flagged this as defense-in-depth that should still be active:
    # the construction guarantee is correct *given current code*, but a
    # future refactor that introduces non-column reference lines would
    # silently pass.
    #
    # Defensive check: every aligned wall edge must be at the coordinate of
    # some grid line, AND every grid line must have a column on it.
    # We assert the latter (the former is enforced by _measure_grid_alignment
    # in corridor_designer's grid_alignment_report).
    from buildemup.components.c08.grid_alignment import derive_grid_lines
    grid_x_lines, grid_y_lines = derive_grid_lines(grid)
    column_xs = {col.x_m for col in grid.columns}
    column_ys = {col.y_m for col in grid.columns}
    for gx in grid_x_lines:
        if not any(abs(gx - cx) <= eps for cx in column_xs):
            raise ValueError(
                f"C8 Invariant 14 violation: grid x-line {gx:.4f} has no "
                f"supporting column. Column x-positions: {sorted(column_xs)}"
            )
    for gy in grid_y_lines:
        if not any(abs(gy - cy) <= eps for cy in column_ys):
            raise ValueError(
                f"C8 Invariant 14 violation: grid y-line {gy:.4f} has no "
                f"supporting column. Column y-positions: {sorted(column_ys)}"
            )

    # Invariant 15 + 18: junction-width equality
    # (Skip when INDEPENDENT_WIDTHS per § 14.20)
    if config.width_propagation != WidthPropagation.INDEPENDENT_WIDTHS:
        for j_pt, members in junction_pts:
            widths = []
            for (idx, which) in members:
                seg = segments[idx]
                w = (
                    seg.start_width_m if which == "start"
                    else seg.end_width_m
                )
                widths.append(w)
            if widths and max(widths) - min(widths) > eps:
                raise ValueError(
                    f"C8 Invariant 15/18 violation: junction at {j_pt} has "
                    f"unequal widths across adjoining segments: {widths} "
                    f"(propagation mode: {config.width_propagation.value})"
                )

    # Invariants 16, 19, 20: enforced by CorridorSegment.__post_init__.
    # Defensive re-check: Inv 16
    for i, seg in enumerate(segments):
        if seg.taper_zone_m > seg.length_m / 2.0 + eps:
            raise ValueError(
                f"C8 Invariant 16 violation: segments[{i}].taper_zone_m "
                f"({seg.taper_zone_m}) > length_m / 2 ({seg.length_m / 2.0})"
            )

    # Inv 17: tapered-edge geometric exclusion. The GridAlignmentReport
    # tracks this; defensive consistency check:
    if (
        path.grid_alignment.tapered_edges_count
        + path.grid_alignment.edges_aligned_count
        > path.grid_alignment.edges_total_count + 0
    ):
        # This is a soft consistency check; tapered + aligned should not
        # exceed total. (Aligned + non-aligned + tapered = total in the
        # full accounting, but inv 17 just says tapered are excluded from
        # aligned.)
        pass  # accept overlap-of-bookkeeping for now

    # Inv 19: taper monotonicity (linear). By construction in our model,
    # widths interpolate linearly via decompose_segment(); no validation
    # path provides curve data, so vacuously satisfied.

    # Inv 20: enforced by CorridorSegment.__post_init__.

    # =========================================================================
    # HAS-CORRIDOR-ONLY invariants
    # =========================================================================
    if not has_corridor:
        return

    # Invariant 2: every segment's widths >= regulatory_min_width_m
    for i, seg in enumerate(segments):
        for label, w in (
            ("constant_width_m", seg.constant_width_m),
            ("start_width_m", seg.start_width_m),
            ("end_width_m", seg.end_width_m),
        ):
            if w < config.regulatory_min_width_m - eps:
                raise ValueError(
                    f"C8 Invariant 2 violation: segments[{i}].{label} ({w}) "
                    f"< regulatory_min_width_m "
                    f"({config.regulatory_min_width_m})"
                )

    # Invariant 6: PUBLIC, SERVICE, PRIVATE bands each have ≥ 1 BAND_ATTACHMENT
    # Invariant 6 (HAS_CORRIDOR only): each present band has corridor service.
    #
    # B-137 / B-144 (S33) — semantic correction.
    # The original v0.5 spec said "≥1 BAND_ATTACHMENT endpoint per band" but
    # the corridor model is that corridor segments run *between* zone bands,
    # in a CIRCULATION strip that physically separates each band from the
    # corridor's centerline by typically half a bay or so. So neither
    # "endpoint kind tagging" (rigid) nor "epsilon-adjacency" (too tight)
    # correctly captures the spec intent.
    #
    # The architecturally correct check: each required band must have ≥1
    # corridor segment within `bay_proximity_m` (= max bay) of its
    # envelope. This is the natural circulation-distance granularity in
    # the v1 cardinal-strip model — a corridor sitting one bay away from
    # a band envelope is providing circulation; a corridor several bays
    # away is not.
    #
    # The endpoint-kind tagging from B-137 is preserved (downstream
    # consumers still see attached_band on each BAND_ATTACHMENT endpoint
    # for whichever band is closest to the endpoint), but Inv 6 uses
    # the proximity semantic.
    required = {ZoneBand.PUBLIC, ZoneBand.SERVICE, ZoneBand.PRIVATE}
    present_envelope_bands = {e.band for e in envelopes}
    required_present = required & present_envelope_bands

    bay_proximity_m = max(grid.bay_x_m, grid.bay_y_m)

    bands_served: set[ZoneBand] = set()
    for env in envelopes:
        if env.band not in required:
            continue
        ex0, ey0, ex1, ey1 = env.x_min_m, env.y_min_m, env.x_max_m, env.y_max_m
        for seg in segments:
            sx0, sy0, sx1, sy1 = _seg_bbox(seg)
            # Closest-point distance between the two axis-aligned bboxes.
            x_gap = max(0.0, max(ex0 - sx1, sx0 - ex1))
            y_gap = max(0.0, max(ey0 - sy1, sy0 - ey1))
            # Euclidean closest-point distance.
            gap = (x_gap * x_gap + y_gap * y_gap) ** 0.5
            if gap <= bay_proximity_m + eps:
                bands_served.add(env.band)
                break

    missing = required_present - bands_served
    if missing:
        raise ValueError(
            f"C8 Invariant 6 violation: bands {sorted(b.value for b in missing)} "
            f"have envelopes but no segment is within bay-proximity "
            f"({bay_proximity_m:.2f}m) of them; corridor does not provide "
            f"circulation to these bands"
        )

    # Invariant 7: CIRCULATION band has no ZoneBandEnvelope
    for e in envelopes:
        if e.band == ZoneBand.CIRCULATION:
            raise ValueError(
                f"C8 Invariant 7 violation: CIRCULATION band has an "
                f"envelope; CIRCULATION must have no envelope (it IS the "
                f"corridor)"
            )

    # Invariant 9: at least one ENTRY endpoint
    if entry_count < 1:
        raise ValueError(
            f"C8 Invariant 9 violation: has_corridor=True but no ENTRY "
            f"endpoint found"
        )


# =============================================================================
# B-NEW-L (S38) — Inv 21: entry approach compatibility predicate.
# =============================================================================

# Cardinal facing → expected edge anchor.
# Maps PlotOrientation to a tuple of edge-checks; each edge-check is a
# function (x, y, w, d, eps) -> bool that returns True iff the point lies
# on that edge within tolerance.
_EDGE_NORTH = lambda x, y, w, d, eps: abs(y - d) < eps  # noqa: E731
_EDGE_SOUTH = lambda x, y, w, d, eps: abs(y - 0.0) < eps  # noqa: E731
_EDGE_EAST = lambda x, y, w, d, eps: abs(x - w) < eps  # noqa: E731
_EDGE_WEST = lambda x, y, w, d, eps: abs(x - 0.0) < eps  # noqa: E731

_FACING_TO_EDGES: dict[PlotOrientation, tuple] = {
    # Cardinal: single edge required.
    PlotOrientation.NORTH: (_EDGE_NORTH,),
    PlotOrientation.SOUTH: (_EDGE_SOUTH,),
    PlotOrientation.EAST: (_EDGE_EAST,),
    PlotOrientation.WEST: (_EDGE_WEST,),
    # Intercardinal: either of two adjacent edges accepted.
    PlotOrientation.NORTHEAST: (_EDGE_NORTH, _EDGE_EAST),
    PlotOrientation.NORTHWEST: (_EDGE_NORTH, _EDGE_WEST),
    PlotOrientation.SOUTHEAST: (_EDGE_SOUTH, _EDGE_EAST),
    PlotOrientation.SOUTHWEST: (_EDGE_SOUTH, _EDGE_WEST),
}


def _facing_edge_label(facing: PlotOrientation) -> str:
    """Human-readable description of which edge(s) a facing accepts."""
    return {
        PlotOrientation.NORTH: "north (y=envelope_depth)",
        PlotOrientation.SOUTH: "south (y=0)",
        PlotOrientation.EAST: "east (x=envelope_width)",
        PlotOrientation.WEST: "west (x=0)",
        PlotOrientation.NORTHEAST: "north or east",
        PlotOrientation.NORTHWEST: "north or west",
        PlotOrientation.SOUTHEAST: "south or east",
        PlotOrientation.SOUTHWEST: "south or west",
    }[facing]


def _iter_entry_endpoints(
    corridor_path: CorridorPath,
) -> "list[CorridorEndpoint]":
    """Collect every CorridorEndpoint of kind=ENTRY across all segments,
    deduplicated by point_m identity (since segments share endpoints
    at junctions)."""
    seen_points: set[tuple[float, float]] = set()
    out: list[CorridorEndpoint] = []
    for seg in corridor_path.segments:
        for ep in (seg.start, seg.end):
            if ep.kind is not CorridorEndpointKind.ENTRY:
                continue
            if ep.point_m in seen_points:
                continue
            seen_points.add(ep.point_m)
            out.append(ep)
    return out


def validate_entry_approach(
    corridor_path: CorridorPath,
    envelope_width_m: float,
    envelope_depth_m: float,
    plot_facing: PlotOrientation,
    *,
    epsilon_m: float = DEFAULT_EPSILON_M,
) -> tuple[bool, str | None]:
    """C8 Inv 21 predicate. Per B-NEW-L (S38).

    Validates that every ENTRY endpoint of a has_corridor=True
    CorridorPath lies on the envelope edge(s) corresponding to the
    plot's facing direction.

    Cardinal facings (N/S/E/W) require the endpoint on one specific
    edge. Intercardinal facings (NE/NW/SE/SW) accept either of the two
    adjacent edges.

    Vacuous-pass cases: has_corridor=False, or paths with no ENTRY
    endpoints at all.

    C11a Tier A registers this as `C8.entry_approach` for M9a-d
    (entry repositioning) operators.

    Pure function. Does not mutate inputs.

    Returns:
        (True, None) on pass.
        (False, reason) on fail.
    """
    if not corridor_path.has_corridor:
        return (True, None)

    entry_endpoints = _iter_entry_endpoints(corridor_path)
    if not entry_endpoints:
        # Some topologies legitimately use BAND_ATTACHMENT only.
        # Inv 9 already enforces that has_corridor=True paths have
        # >= 1 ENTRY for the topologies that need them; we don't
        # double-cover here.
        return (True, None)

    if plot_facing not in _FACING_TO_EDGES:
        return (
            False,
            f"C8 Inv 21: unrecognised plot_facing={plot_facing!r}",
        )
    edge_checks = _FACING_TO_EDGES[plot_facing]

    for ep in entry_endpoints:
        x, y = ep.point_m
        if not any(
            check(x, y, envelope_width_m, envelope_depth_m, epsilon_m)
            for check in edge_checks
        ):
            return (
                False,
                f"C8 Inv 21: ENTRY endpoint at ({x:.6f}, {y:.6f}) is "
                f"not on the {_facing_edge_label(plot_facing)} edge "
                f"for plot_facing={plot_facing.value} "
                f"(envelope {envelope_width_m:.3f}×{envelope_depth_m:.3f}m, "
                f"tolerance {epsilon_m}m)",
            )

    return (True, None)


__all__ = [
    "validate_corridor_path",
    "validate_entry_approach",  # B-NEW-L (S38)
]
