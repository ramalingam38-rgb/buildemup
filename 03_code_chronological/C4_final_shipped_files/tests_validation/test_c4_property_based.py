"""Tier-1 property-based tests for C4 (Hypothesis).

Per SPEC v0.5 LOCKED § 7.
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st

from buildemup.components.c04 import derive
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot, PlotType, SUPPORTED_CITIES
from buildemup.tests.validation._c4_fixtures import make_brief


# Plot dim bounds per Plot.__post_init__: 3.0 ≤ width/depth ≤ 60.0.
# Use a narrowed range to avoid sub-600sqft (which raises by spec).
# 8m × 8m ≈ 689 sqft, just over the floor.
_DIM_MIN = 8.0
_DIM_MAX = 60.0
# Road bounds: 1.5 ≤ road ≤ 30.0
_ROAD_MIN = 1.5
_ROAD_MAX = 30.0


@st.composite
def _detached_plots(draw) -> Plot:
    """Strategy: a valid DETACHED Plot anywhere in the supported set."""
    width = draw(st.floats(min_value=_DIM_MIN, max_value=_DIM_MAX, allow_nan=False))
    depth = draw(st.floats(min_value=_DIM_MIN, max_value=_DIM_MAX, allow_nan=False))
    facing = draw(st.sampled_from(list(PlotOrientation)))
    city = draw(st.sampled_from(sorted(SUPPORTED_CITIES)))
    road = draw(st.floats(min_value=_ROAD_MIN, max_value=_ROAD_MAX, allow_nan=False))
    return Plot(
        width_m=width, depth_m=depth, facing=facing,
        city=city, road_width_m=round(road, 3),
        plot_type=PlotType.DETACHED,
    )


@given(_detached_plots())
@settings(max_examples=50, deadline=None)   # deadline=None → don't fail on slow CI
def test_area_sqft_sqm_round_trip(plot):
    """area_sqft and area_sqm round-trip exactly via the IEC factor.

    v0.9 (walk #7): C4 now uses the EXACT 1 sqft = 0.09290304 sqm
    conversion (rather than the rounded 10.7639 inverse), so the round
    trip is exact to float precision.
    """
    from buildemup.components.c04.plot_analysis import SQM_PER_SQFT
    pa = derive(make_brief(plot), now=1.0)
    # Tight tolerance — exact factor + pure float multiply, no cancellation.
    assert abs(pa.area_sqft * SQM_PER_SQFT - pa.area_sqm) < 1e-9


@given(_detached_plots())
@settings(max_examples=50, deadline=None)
def test_aspect_ratio_inverse_for_swap(plot):
    """Swapping width and depth inverts aspect_ratio."""
    pa = derive(make_brief(plot), now=1.0)
    swapped = Plot(
        width_m=plot.depth_m, depth_m=plot.width_m,
        facing=plot.facing, city=plot.city,
        road_width_m=plot.road_width_m, plot_type=plot.plot_type,
    )
    pa_swapped = derive(make_brief(swapped), now=1.0)
    # aspect_ratio = depth/width; swap → 1/original ratio.
    assert abs(pa.aspect_ratio * pa_swapped.aspect_ratio - 1.0) < 1e-9


@given(_detached_plots())
@settings(max_examples=50, deadline=None)
def test_raw_facade_count_in_2_3_4_range(plot):
    """For any plot type + corner combo the raw_facade_count ∈ {2, 3, 4}."""
    pa = derive(make_brief(plot), now=1.0)
    # DETACHED → 4, CONTINUOUS → 2 (or 3 with corner_plot),
    # SEMI_DETACHED → 3 (or 4 with corner_plot).
    assert pa.neighbour_context.raw_facade_count in (2, 3, 4)
    # The raw_facade_count equals len(open_sides) by definition.
    assert pa.neighbour_context.raw_facade_count == len(pa.neighbour_context.open_sides)
