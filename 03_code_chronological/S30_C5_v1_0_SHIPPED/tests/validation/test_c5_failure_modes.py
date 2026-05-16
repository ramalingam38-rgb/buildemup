"""Validation tests for C5 failure modes.

Per C5 SPEC v0.9 LOCKED § 6 + v0.3 § 14.4 (Q7 reversal: no RuntimeError on
all-fail; top is always returned with low_confidence flag).
"""
from __future__ import annotations

import pytest

from buildemup.components.c05 import select_topology
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.floor_brief import FloorRoomBrief
from buildemup.domain.plot import Plot
from buildemup.tests.validation._c5_fixtures import (
    chennai_30x40,
    make_floor_brief,
    make_plot_analysis,
    medium_brief,
)


# ─── FloorRoomBrief input validation ──────────────────────────────────────


def test_floor_room_brief_rejects_negative_bedroom_count():
    with pytest.raises(ValueError, match="bedroom_count"):
        FloorRoomBrief(
            bedroom_count=-1, bathroom_count=2,
            has_kitchen=True, has_living=True,
            has_pooja=False, has_utility=False,
        )


def test_floor_room_brief_rejects_negative_bathroom_count():
    with pytest.raises(ValueError, match="bathroom_count"):
        FloorRoomBrief(
            bedroom_count=2, bathroom_count=-1,
            has_kitchen=True, has_living=True,
            has_pooja=False, has_utility=False,
        )


def test_floor_room_brief_accepts_zero_bedrooms():
    """Zero bedrooms is valid (e.g., studio); scorers handle factor=0."""
    brief = FloorRoomBrief(
        bedroom_count=0, bathroom_count=1,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
    )
    assert brief.bedroom_count == 0


def test_floor_room_brief_accepts_zero_bathrooms():
    brief = FloorRoomBrief(
        bedroom_count=1, bathroom_count=0,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
    )
    assert brief.bathroom_count == 0


# ─── select_topology input validation ─────────────────────────────────────


def test_select_topology_rejects_non_floor_room_brief():
    pa = make_plot_analysis(chennai_30x40())
    with pytest.raises(TypeError, match="FloorRoomBrief"):
        select_topology(pa, {"bedroom_count": 2})              # type: ignore[arg-type]


def test_select_topology_rejects_none_room_brief():
    pa = make_plot_analysis(chennai_30x40())
    with pytest.raises(TypeError, match="FloorRoomBrief"):
        select_topology(pa, None)                               # type: ignore[arg-type]


# ─── B-066: non-rectangular plot rejection ────────────────────────────────


def test_select_topology_rejects_non_rectangular_shape():
    """v1 supports rectangular only — non-rectangular raises NotImplementedError.

    We need a PlotAnalysis with a non-RECTANGULAR shape. C4 currently only
    derives RECTANGULAR (PlotShape.RECTANGULAR is the only kind C4 produces
    for v1). To exercise the C5 guardrail, we mutate a derived PlotAnalysis
    via dataclasses.replace() to substitute a non-RECTANGULAR shape value.
    """
    import dataclasses
    from buildemup.components.c04.schema import PlotShape
    pa = make_plot_analysis(chennai_30x40())
    # Substitute a non-RECTANGULAR shape; PlotShape has other values per c04.schema
    if hasattr(PlotShape, "L_SHAPED"):
        non_rect = PlotShape.L_SHAPED
    elif hasattr(PlotShape, "IRREGULAR"):
        non_rect = PlotShape.IRREGULAR
    else:
        # Any non-RECTANGULAR member; PlotShape is an Enum so iter and pick
        candidates = [s for s in PlotShape if s != PlotShape.RECTANGULAR]
        if not candidates:
            pytest.skip("PlotShape has only RECTANGULAR — cannot exercise B-066 guardrail")
        non_rect = candidates[0]
    pa_mut = dataclasses.replace(pa, shape=non_rect)
    with pytest.raises(NotImplementedError, match="rectangular|B-066"):
        select_topology(pa_mut, medium_brief())


# ─── v0.3 § 14.4 Q7 reversal: top always returned (no RuntimeError) ───────


def test_top_always_returned_even_when_all_low_score():
    """Per Q7 reversal: even when every topology scores below the threshold,
    the top-ranked candidate is returned (with low_confidence=True if applicable).

    On a healthy plot+brief, all 4 topologies score reasonably; we cannot
    naturally produce an all-low-score case via fixtures. We instead verify
    the behavioral guarantee: select_topology never raises RuntimeError on
    valid input.
    """
    pa = make_plot_analysis(chennai_30x40())
    # Try with a degenerate-ish brief (zero bedrooms — bedroom_fit collapses
    # to 0, lowering scores)
    brief_zero = make_floor_brief(bedroom_count=0)
    candidates = select_topology(pa, brief_zero)
    assert len(candidates) >= 1
    # Top candidate is returned regardless of score
    assert candidates[0] is not None


def test_no_runtime_error_on_extreme_inputs():
    """Sweep extreme valid inputs — no RuntimeError should be raised."""
    test_cases = [
        # Tiny plot
        Plot(width_m=5.0, depth_m=5.0, facing=PlotOrientation.NORTH,
             city="chennai", road_width_m=6.0),
        # Very deep plot
        Plot(width_m=8.0, depth_m=30.0, facing=PlotOrientation.SOUTH,
             city="chennai", road_width_m=9.0),
        # Very wide plot
        Plot(width_m=22.0, depth_m=15.0, facing=PlotOrientation.EAST,
             city="bangalore", road_width_m=12.0),
    ]
    for plot in test_cases:
        try:
            pa = make_plot_analysis(plot)
        except (ValueError, NotImplementedError):
            # C4 may legitimately reject extreme plots; not the SUT here
            continue
        for bed in (0, 1, 5, 8):
            brief = make_floor_brief(bedroom_count=bed)
            # Should never raise RuntimeError
            try:
                candidates = select_topology(pa, brief)
                assert len(candidates) >= 1
            except RuntimeError:
                pytest.fail(
                    f"RuntimeError on plot={plot.width_m}×{plot.depth_m}, "
                    f"bed={bed}"
                )
