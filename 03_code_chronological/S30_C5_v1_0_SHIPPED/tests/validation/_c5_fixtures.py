"""C5 test helpers — FloorRoomBrief builders + PlotAnalysis wrapper.

Per Q3 design (S30 — adopted as proposed).

C5 tests need:
  - A FloorRoomBrief (NEW domain dataclass per C5 SPEC § 2)
  - A PlotAnalysis (output of c04.derive)

This file builds both. Plot fixtures themselves are RE-EXPORTED from
_c4_fixtures.py — no duplication.
"""
from __future__ import annotations

import time

from buildemup.components.c04 import derive
from buildemup.components.c04.schema import PlotAnalysis
from buildemup.domain.floor_brief import FloorRoomBrief
from buildemup.tests.validation._c4_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    hyderabad_30x40,
    make_brief,
    mumbai_30x40,
    pune_30x40,
)


__all__ = [
    # Plot fixtures (re-exported from C4)
    "chennai_30x40", "bangalore_40x60", "delhi_60x90",
    "mumbai_30x40", "pune_30x40", "hyderabad_30x40",
    # PlotAnalysis builder
    "make_plot_analysis",
    # FloorRoomBrief builders
    "small_brief", "medium_brief", "large_brief", "make_floor_brief",
    # Stability test baselines
    "baseline_test_plot", "baseline_test_brief",
]


# ─── PlotAnalysis builder ────────────────────────────────────────────────


def make_plot_analysis(
    plot, *, trace_id: str = "trace-c5-test", now: float | None = None
) -> PlotAnalysis:
    """Build a PlotAnalysis by calling c04.derive() on a plot fixture.

    Used by C5 tests instead of constructing PlotAnalysis directly — keeps
    C5 tests downstream of the actual C4 contract.
    """
    if now is None:
        now = time.time()
    brief_stub = make_brief(plot, trace_id=trace_id)
    return derive(brief_stub, now=now)


# ─── FloorRoomBrief builders ─────────────────────────────────────────────


def small_brief() -> FloorRoomBrief:
    """1-bedroom ground-floor brief. Pairs with chennai_30x40 / mumbai_30x40."""
    return FloorRoomBrief(
        bedroom_count=1, bathroom_count=1,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
    )


def medium_brief() -> FloorRoomBrief:
    """3-bedroom ground-floor brief. Pairs with bangalore_40x60."""
    return FloorRoomBrief(
        bedroom_count=3, bathroom_count=2,
        has_kitchen=True, has_living=True,
        has_pooja=True, has_utility=True,
    )


def large_brief() -> FloorRoomBrief:
    """4-bedroom ground-floor brief. Pairs with delhi_60x90 (T3)."""
    return FloorRoomBrief(
        bedroom_count=4, bathroom_count=3,
        has_kitchen=True, has_living=True,
        has_pooja=True, has_utility=True,
        other_rooms=("study",),
    )


def make_floor_brief(
    *,
    bedroom_count: int = 2,
    bathroom_count: int = 2,
    has_kitchen: bool = True,
    has_living: bool = True,
    has_pooja: bool = False,
    has_utility: bool = False,
    other_rooms: tuple[str, ...] = (),
    floor_label: str = "ground",
) -> FloorRoomBrief:
    """Generic FloorRoomBrief builder for parametrized tests."""
    return FloorRoomBrief(
        bedroom_count=bedroom_count, bathroom_count=bathroom_count,
        has_kitchen=has_kitchen, has_living=has_living,
        has_pooja=has_pooja, has_utility=has_utility,
        other_rooms=other_rooms, floor_label=floor_label,
    )


# ─── Stability test baselines (v0.8 § 14.3) ──────────────────────────────


def baseline_test_plot():
    """The fixed plot used by test_c5_stability.py perturbation tests.

    9.0 × 12.0 m, NORTH-facing, chennai. NOT exactly any of the C4 fixtures
    so perturbation ±0.1m doesn't accidentally hit a fixture boundary.

    The Plot import here is permitted: this file lives in
    buildemup.tests.validation, NOT buildemup.components.c05; the
    forbidden-import test (test_c5_consumes_plot_analysis.py) scans
    only the c05 package via pkgutil.walk_packages.
    """
    from buildemup.domain.envelope import PlotOrientation
    from buildemup.domain.plot import Plot
    return Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
    )


def baseline_test_brief() -> FloorRoomBrief:
    """The fixed brief used by test_c5_stability.py perturbation tests.

    3-bedroom is in the sweet spot for STRIP, CENTRAL_SPINE, AND L_SHAPE,
    so the topology choice is decided by plot dims + scoring, not by the
    bedroom-fit factor alone.
    """
    return FloorRoomBrief(
        bedroom_count=3, bathroom_count=2,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
    )
