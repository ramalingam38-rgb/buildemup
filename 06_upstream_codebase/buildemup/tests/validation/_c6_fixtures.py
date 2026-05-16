"""C6 test helpers — TopologyCandidate builders + PlotAnalysis re-exports.

Per Rule 10.6.1 reconstruction (B-127). C6 v0.7 LOCKED tests rebuilt at S33.

Reuses C5 fixtures (which themselves reuse C4) to avoid duplication. C6 tests
need:
  - A PlotAnalysis (output of c04.derive)
  - A tuple of TopologyCandidate (output of c05.select_topology), used as
    input to c06.prioritize_orientation.

This file builds both. Plot fixtures themselves are RE-EXPORTED from
_c5_fixtures.py — no duplication.
"""
from __future__ import annotations

from buildemup.components.c05 import select_topology
from buildemup.components.c05.schema import TopologyCandidate
from buildemup.tests.validation._c5_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    hyderabad_30x40,
    large_brief,
    make_floor_brief,
    make_plot_analysis,
    medium_brief,
    mumbai_30x40,
    pune_30x40,
    small_brief,
)


__all__ = [
    # Plot fixtures (re-exported)
    "chennai_30x40", "bangalore_40x60", "delhi_60x90",
    "mumbai_30x40", "pune_30x40", "hyderabad_30x40",
    # PlotAnalysis builder
    "make_plot_analysis",
    # FloorRoomBrief builders (re-exported)
    "small_brief", "medium_brief", "large_brief", "make_floor_brief",
    # TopologyCandidate builders
    "make_candidates",
    "first_candidate",
    "single_candidate_tuple",
]


def make_candidates(plot=None, brief=None) -> tuple[TopologyCandidate, ...]:
    """Build a real C5-output candidate tuple for one plot+brief combination.

    Defaults: bangalore_40x60 + medium_brief — a stable T2 / 3-bed reference
    that produces 1-3 candidates including STRIP and CENTRAL_SPINE.
    """
    if plot is None:
        plot = bangalore_40x60()
    if brief is None:
        brief = medium_brief()
    pa = make_plot_analysis(plot)
    return select_topology(pa, brief)


def first_candidate(plot=None, brief=None) -> TopologyCandidate:
    """Convenience: take just the first (top-ranked) candidate."""
    return make_candidates(plot=plot, brief=brief)[0]


def single_candidate_tuple(plot=None, brief=None) -> tuple[TopologyCandidate, ...]:
    """Convenience: a 1-element tuple wrapping the top candidate.

    Useful when a test only needs orientation on one candidate.
    """
    return (first_candidate(plot=plot, brief=brief),)
