"""C8 test helpers — fixtures for Grid, segments, envelopes, OrientedCandidates.

Reuses C5/C6 fixtures where possible.
"""
from __future__ import annotations

from buildemup.components.c05 import select_topology
from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c06 import prioritize_orientation
from buildemup.components.c07.grid_generator import (
    ColumnPosition,
    Grid,
    GridGenerator,
)
from buildemup.components.c08.schema import (
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
    ZoneBandEnvelope,
)
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c5_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    make_plot_analysis,
    medium_brief,
    small_brief,
)


def make_grid(*, width_m: float = 12.0, depth_m: float = 12.0) -> Grid:
    """Build a Grid via GridGenerator. Width/depth must be >= 5m."""
    return GridGenerator().generate(envelope_width_m=width_m, envelope_depth_m=depth_m)


def make_grid_minimal(
    *, bay_x_m: float = 3.0, bay_y_m: float = 3.0,
    envelope_width_m: float = 12.0, envelope_depth_m: float = 12.0,
    n_columns_x: int = 4, n_columns_y: int = 4,
) -> Grid:
    """Build a Grid with explicit bay sizes by hand."""
    columns = []
    for ix in range(n_columns_x):
        for iy in range(n_columns_y):
            columns.append(ColumnPosition(
                f"{chr(ord('A')+ix)}{iy+1}",
                ix * bay_x_m, iy * bay_y_m, True,
            ))
    return Grid(
        columns=columns,
        bay_x_m=bay_x_m,
        bay_y_m=bay_y_m,
        columns_x_count=n_columns_x,
        columns_y_count=n_columns_y,
        envelope_width_m=envelope_width_m,
        envelope_depth_m=envelope_depth_m,
    )


def make_segment(
    *,
    runs_along: PlotOrientation = PlotOrientation.EAST,
    start_pt: tuple[float, float] = (0.0, 5.0),
    end_pt: tuple[float, float] = (10.0, 5.0),
    width_m: float = 1.2,
    start_width_m: float | None = None,
    end_width_m: float | None = None,
    taper_zone_m: float = 0.0,
    kind: CorridorSegmentKind = CorridorSegmentKind.PRIMARY,
    start_kind: CorridorEndpointKind = CorridorEndpointKind.ENTRY,
    end_kind: CorridorEndpointKind = CorridorEndpointKind.BAND_ATTACHMENT,
) -> CorridorSegment:
    """Helper to build a CorridorSegment for tests."""
    if start_width_m is None:
        start_width_m = width_m
    if end_width_m is None:
        end_width_m = width_m
    sx, sy = start_pt
    ex, ey = end_pt
    length = max(abs(ex - sx), abs(ey - sy))
    return CorridorSegment(
        kind=kind,
        start=CorridorEndpoint(kind=start_kind, point_m=start_pt),
        end=CorridorEndpoint(kind=end_kind, point_m=end_pt),
        constant_width_m=width_m,
        start_width_m=start_width_m,
        end_width_m=end_width_m,
        taper_zone_m=taper_zone_m,
        length_m=length,
        runs_along=runs_along,
    )


def make_envelope(
    *,
    band: ZoneBand = ZoneBand.PUBLIC,
    direction: PlotOrientation = PlotOrientation.NORTH,
    x_min: float = 0.0, y_min: float = 8.0,
    x_max: float = 10.0, y_max: float = 10.0,
) -> ZoneBandEnvelope:
    return ZoneBandEnvelope(
        band=band, direction=direction,
        x_min_m=x_min, y_min_m=y_min,
        x_max_m=x_max, y_max_m=y_max,
    )


def real_pipeline(
    *, plot_factory=bangalore_40x60, brief_factory=medium_brief,
):
    """Run C4 → C5 → C6 → C7. Returns (oriented, plot_analysis, grid)."""
    plot = plot_factory()
    plot_analysis = make_plot_analysis(plot)
    brief = brief_factory()
    candidates = select_topology(plot_analysis, brief)
    oriented = prioritize_orientation(
        candidates, plot_analysis, VastuTier.PARTIAL,
    )
    grid = GridGenerator().generate(
        envelope_width_m=plot_analysis.plot.width_m,
        envelope_depth_m=plot_analysis.plot.depth_m,
    )
    return oriented, plot_analysis, grid
