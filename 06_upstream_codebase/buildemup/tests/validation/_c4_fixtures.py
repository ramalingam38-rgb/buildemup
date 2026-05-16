"""C4 test helpers — minimal stubs for the ResolvedBrief contract.

C4 only reads `brief.revised_brief.plot` and `brief.revised_brief.trace_id`.
Building a full ResolvedBrief in unit tests is needlessly heavy (and
couples C4 unit tests to C3a domain code). We use lightweight namespace
stubs with the two attributes C4 actually consumes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from buildemup.domain.plot import Plot, PlotType, SharedSide, SoilType
from buildemup.domain.envelope import PlotOrientation


@dataclass(frozen=True)
class _RevisedStub:
    plot: Plot
    trace_id: str


@dataclass(frozen=True)
class _BriefStub:
    revised_brief: _RevisedStub


def make_brief(plot: Plot, *, trace_id: str = "trace-test-001") -> _BriefStub:
    """Return a minimal stub satisfying C4's ResolvedBrief contract."""
    return _BriefStub(revised_brief=_RevisedStub(plot=plot, trace_id=trace_id))


def chennai_30x40() -> Plot:
    """30×40 ft Chennai plot (≈ 9.144 × 12.192 m, ~1200 sqft = T1)."""
    return Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTHEAST,
        city="chennai", road_width_m=9.0,
    )


def bangalore_40x60() -> Plot:
    """40×60 ft Bangalore plot (12.192 × 18.288 m exactly = textbook 2400 sqft → T2).

    v0.5 needed a nudge to 12.20 × 18.30 because tier was classified in
    sqft space and 12.192 × 18.288 × 10.7639 = 2399.998 (one ulp short
    of the boundary). v0.6 (walk #1) compares in sqm using the exact
    factor 0.09290304 — 12.192 × 18.288 = 222.967296 sqm matches
    _T2_MIN_SQM = 2400 × 0.09290304 = 222.967296 sqm exactly. Fixture
    restored to the textbook 40×60 ft to also serve as the boundary
    test case.
    """
    return Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.EAST,
        city="bangalore", road_width_m=12.0,
    )


def delhi_60x90() -> Plot:
    """60×90 ft Delhi plot (≈ 18.288 × 27.432 m, ~5400 sqft = T3)."""
    return Plot(
        width_m=18.288, depth_m=27.432, facing=PlotOrientation.SOUTH,
        city="delhi", road_width_m=15.0,
    )


def mumbai_30x40() -> Plot:
    return Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.WEST,
        city="mumbai", road_width_m=9.0,
    )


def pune_30x40() -> Plot:
    return Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTH,
        city="pune", road_width_m=8.0,
    )


def hyderabad_30x40() -> Plot:
    return Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTH,
        city="hyderabad", road_width_m=9.0,
    )
