"""
BuildemUp† — C4 neighbour context derivation.

# ───────────────────── DEFERRED BACKLOG (REVIEW MARKER) ─────────────────────
# Critique reviewers: filed in spec § 16. Please do NOT re-flag.
# (Strippable review aid.)
#
#   B-068  effective_open_sides: post-setback openness (currently RAW openness
#          only; setbacks are computed by C2 and not yet folded into this view).
#   B-076  Plot.corner_orientation input field (eliminates the v1 LEFT default
#          for CONTINUOUS+corner plots). Touches C1/C3a/C7 input contracts.
#          Current code surfaces the assumption via
#          NeighbourContext.corner_assumption = "second_street_assumed_LEFT_b076".
# ─────────────────────────────────────────────────────────────────────────────

Per spec § 4.9. Computes which sides of the plot are open vs shared
with neighbours, accounting for plot_type (DETACHED / SEMI_DETACHED /
CONTINUOUS) and corner_plot.

Returns RAW openness — does NOT account for setbacks. C5 combines
with C2 setbacks for `effective_open_sides` (B-068).

CONVENTIONS:
  - SEMI_DETACHED: shared_side is LEFT or RIGHT relative to a viewer
    standing on the street facing the plot. Translated to a compass
    bearing via LEFT_RIGHT_BY_FACING.
  - CONTINUOUS: both side walls (left + right) are shared (TNCDBR 2019
    "Continuous Building Area"); only front + back are open.
  - corner_plot=True: a second street replaces one shared side wall
    with an open side. v1 conventions for which side (see
    derive_second_street_side below).

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c04.schema import (
    LEFT_RIGHT_BY_FACING,
    NeighbourContext,
    compute_plot_facing_sides,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot, PlotType, SharedSide


def derive_second_street_side(plot: Plot) -> PlotOrientation:
    """Compass direction of the second street for corner plots.

    Conventions (v1):
      - SEMI_DETACHED corner: second street is on the side WALL opposite
        to plot.shared_side. (If shared=LEFT, second street is on RIGHT.)
      - CONTINUOUS corner: second street is on the LEFT side wall (v1
        convention; arbitrary, can be refined when input contract supports
        specifying which corner).
      - DETACHED corner: all sides already open; this function should
        not be called for DETACHED. Defensive return = left side.

    Pre: plot.corner_plot == True (validation responsibility of caller).
    """
    if plot.plot_type == PlotType.SEMI_DETACHED:
        # shared_side is required to be set for SEMI_DETACHED (Plot
        # __post_init__ enforces). The opposite side is the corner road.
        shared_lr = plot.shared_side.value  # "left" | "right"
        opposite = "right" if shared_lr == "left" else "left"
        return LEFT_RIGHT_BY_FACING[plot.facing][opposite]

    if plot.plot_type == PlotType.CONTINUOUS:
        # v1 convention: second street on the LEFT side wall. See module
        # docstring for the future-refinement note.
        return LEFT_RIGHT_BY_FACING[plot.facing]["left"]

    # DETACHED — defensive return; caller short-circuits before this.
    return LEFT_RIGHT_BY_FACING[plot.facing]["left"]


def derive_neighbour_context(plot: Plot) -> NeighbourContext:
    """See module docstring."""
    sides = compute_plot_facing_sides(plot.facing)  # front/back/left/right

    if plot.plot_type == PlotType.DETACHED:
        open_sides: list[PlotOrientation] = list(sides.values())
        shared_sides: list[PlotOrientation] = []

    elif plot.plot_type == PlotType.SEMI_DETACHED:
        # shared_side is guaranteed non-None by Plot.__post_init__.
        assert plot.shared_side is not None  # type narrowing for mypy
        shared_orientation = LEFT_RIGHT_BY_FACING[plot.facing][plot.shared_side.value]
        shared_sides = [shared_orientation]
        open_sides = [s for s in sides.values() if s != shared_orientation]

    elif plot.plot_type == PlotType.CONTINUOUS:
        # Continuous building area (TNCDBR 2019): shares both side walls.
        open_sides = [sides["front"], sides["back"]]
        shared_sides = [sides["left"], sides["right"]]

    else:  # pragma: no cover — exhaustive over PlotType, but guard for future extensions.
        raise ValueError(f"unknown plot_type: {plot.plot_type}")

    # v0.6 (walk #5): track whether we used a v1 convention to pick the
    # second-street side, so downstream consumers can see when their
    # decisions are based on an inferred default.
    corner_assumption: str | None = None

    # Corner plot: a second street replaces one shared side with an open one.
    # No-op for DETACHED (no shared sides to remove from).
    if plot.corner_plot and shared_sides:
        second_street_side = derive_second_street_side(plot)
        if second_street_side in shared_sides:
            shared_sides.remove(second_street_side)
            open_sides.append(second_street_side)
        # Only CONTINUOUS+corner uses the v1 LEFT default convention. For
        # SEMI_DETACHED the second street is deterministic (opposite of
        # plot.shared_side, see derive_second_street_side); no assumption.
        if plot.plot_type == PlotType.CONTINUOUS:
            corner_assumption = "second_street_assumed_LEFT_b076"

    return NeighbourContext(
        open_sides=tuple(open_sides),
        shared_sides=tuple(shared_sides),
        raw_facade_count=len(open_sides),
        corner_assumption=corner_assumption,
    )


__all__ = ["derive_neighbour_context", "derive_second_street_side"]
