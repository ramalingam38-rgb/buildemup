"""
BuildemUp† — Component 5 (Topology Selector) zone-band assignments.

Per C5 SPEC v0.9 LOCKED § 4.3 (cumulative through v0.2).

Implements the default zone-band → compass-direction mapping for each
topology (rotated relative to plot.facing) plus the CorridorSketch builder
for each topology.

Q5 adjudication: one default per topology + B-091 (climate-variant overrides
deferred). Pattern E avoidance — climate-aware zone bands when those become
empirically needed, not pre-empirically.

Q2 design (S30): runs_along on COURTYARD (LOOP) is a CONVENTION carrying
plot.facing — the plot's front-of-plot reference. C8 produces the actual
loop geometry.

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import compute_plot_facing_sides
from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    CorridorSketch,
    TopologyKind,
    ZoneBand,
)
from buildemup.domain.envelope import PlotOrientation


# ─── Zone-band assignment ──────────────────────────────────────────────────


def default_zone_bands(
    topology: TopologyKind,
    facing: PlotOrientation,
) -> Mapping[ZoneBand, PlotOrientation]:
    """Default zone-band → compass direction mapping per topology.

    Per C5 SPEC v0.2 § 4.3 (one default per topology; B-091 for climate
    variants).

    The defaults are expressed relative to plot.facing; the helper
    compute_plot_facing_sides() (from c04.schema) translates them to absolute
    compass directions.

    | Topology      | Default assignment                                          |
    |---------------|-------------------------------------------------------------|
    | STRIP         | front=PUBLIC, back=PRIVATE, left=SERVICE, right=CIRCULATION |
    | CENTRAL_SPINE | front=PUBLIC, back=PRIVATE, left=SERVICE, right=CIRCULATION |
    | L_SHAPE       | front=PUBLIC, back=PRIVATE, left=CIRCULATION                 |
    | COURTYARD     | front=PUBLIC, back=PRIVATE, left=SERVICE, right=CIRCULATION |

    Note on duplicates (validator-relevant):
      - All topologies except L_SHAPE assign 4 distinct directions.
      - L_SHAPE assigns 3 (PUBLIC, PRIVATE, CIRCULATION) — junction acts as
        circulation; SERVICE band sits within the public arm at this resolution.
      - The validator (consistency check, v0.5 § 14.7 + v0.6 § 14.5) requires
        the per-topology required-bands set to be present and distinct
        directions for non-COURTYARD topologies.
    """
    sides = compute_plot_facing_sides(facing)        # {"front", "back", "left", "right"}

    if topology == TopologyKind.STRIP:
        return MappingProxyType({
            ZoneBand.PUBLIC:      sides["front"],
            ZoneBand.SERVICE:     sides["left"],
            ZoneBand.CIRCULATION: sides["right"],
            ZoneBand.PRIVATE:     sides["back"],
        })

    if topology == TopologyKind.CENTRAL_SPINE:
        # Central spine: public + service flank one direction; private flanks
        # the opposite; circulation runs front-to-back through the middle.
        # Default v0.2 § 4.3: one_flank=(PUBLIC+SERVICE), other_flank=PRIVATE.
        return MappingProxyType({
            ZoneBand.PUBLIC:      sides["front"],
            ZoneBand.SERVICE:     sides["left"],
            ZoneBand.CIRCULATION: sides["right"],
            ZoneBand.PRIVATE:     sides["back"],
        })

    if topology == TopologyKind.L_SHAPE:
        # L-shape: front_arm=PUBLIC, side_arm=PRIVATE, junction=CIRCULATION.
        # Required bands per v0.6 § 14.5: {PUBLIC, PRIVATE, CIRCULATION}.
        return MappingProxyType({
            ZoneBand.PUBLIC:      sides["front"],
            ZoneBand.PRIVATE:     sides["back"],
            ZoneBand.CIRCULATION: sides["left"],
        })

    if topology == TopologyKind.COURTYARD:
        # Courtyard: front=PUBLIC, sides=SERVICE+PRIVATE, courtyard=CIRCULATION.
        # Per v0.6 § 14.5: COURTYARD is exempted from the distinct-directions
        # rule because the courtyard CIRCULATION band shares space with
        # other bands at this sketch resolution.
        return MappingProxyType({
            ZoneBand.PUBLIC:      sides["front"],
            ZoneBand.SERVICE:     sides["left"],
            ZoneBand.PRIVATE:     sides["right"],
            ZoneBand.CIRCULATION: sides["back"],
        })

    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


# ─── CorridorSketch builder ────────────────────────────────────────────────


def _connectivity_for(kind: TopologyKind) -> ConnectivityType:
    """Connectivity is fully determined by topology kind (v0.3 § 14.6).

    STRIP / CENTRAL_SPINE = LINEAR; L_SHAPE = BRANCHED; COURTYARD = LOOP.
    """
    if kind in (TopologyKind.STRIP, TopologyKind.CENTRAL_SPINE):
        return ConnectivityType.LINEAR
    if kind == TopologyKind.L_SHAPE:
        return ConnectivityType.BRANCHED
    if kind == TopologyKind.COURTYARD:
        return ConnectivityType.LOOP
    raise ValueError(f"unknown TopologyKind: {kind!r}")  # pragma: no cover


def _corridor_position_for(kind: TopologyKind) -> CorridorPosition:
    """Per the consistency validator (v0.5 § 14.7) required positions.

    STRIP -> NONE (small T1) or CENTRAL — v1 default uses CENTRAL because
    sketches at C5 still represent a nominal corridor; corridor erasure on
    small T1 plots is a C8 decision.
    CENTRAL_SPINE -> CENTRAL.
    L_SHAPE -> L_BENT.
    COURTYARD -> PERIMETER.
    """
    if kind == TopologyKind.STRIP:
        return CorridorPosition.CENTRAL
    if kind == TopologyKind.CENTRAL_SPINE:
        return CorridorPosition.CENTRAL
    if kind == TopologyKind.L_SHAPE:
        return CorridorPosition.L_BENT
    if kind == TopologyKind.COURTYARD:
        return CorridorPosition.PERIMETER
    raise ValueError(f"unknown TopologyKind: {kind!r}")  # pragma: no cover


def _approx_length_m_for(kind: TopologyKind, width_m: float, depth_m: float) -> float:
    """Per C5 SPEC v0.3 § 14.6 (D8) approx_length_m formulas.

    The 0.85 / 0.5 / 0.4 multipliers approximate the post-setback usable run.
    Refined by C8.
    """
    if kind == TopologyKind.STRIP:
        return depth_m * 0.85
    if kind == TopologyKind.CENTRAL_SPINE:
        return depth_m * 0.85
    if kind == TopologyKind.L_SHAPE:
        return (width_m + depth_m) * 0.5
    if kind == TopologyKind.COURTYARD:
        return 2.0 * (width_m + depth_m) * 0.4
    raise ValueError(f"unknown TopologyKind: {kind!r}")  # pragma: no cover


def build_corridor_sketch(
    topology: TopologyKind,
    plot_analysis: object,
) -> CorridorSketch:
    """Build the CorridorSketch for a given topology + plot.

    Per C5 SPEC v0.2 § 3 + v0.3 § 14.6 + Q2 design (S30) for COURTYARD.
    """
    plot = plot_analysis.plot
    width_m = plot.width_m
    depth_m = plot.depth_m
    facing = plot.facing

    # runs_along (Q2 — Option C with micro tweak):
    #   For LINEAR (STRIP, CENTRAL_SPINE) and BRANCHED (L_SHAPE) topologies,
    #   runs_along is the corridor's primary direction. For COURTYARD (LOOP),
    #   the corridor has no primary direction; runs_along is then a CONVENTION
    #   carrying plot.facing — the plot's front-of-plot reference. C8 produces
    #   the actual loop geometry.
    runs_along = facing

    # nominal_width_m: 1.2m default (NBC-aligned residential corridor minimum)
    # — refined by C8.
    nominal_width_m = 1.2

    return CorridorSketch(
        position=_corridor_position_for(topology),
        nominal_width_m=nominal_width_m,
        runs_along=runs_along,
        approx_length_m=_approx_length_m_for(topology, width_m, depth_m),
        connectivity_type=_connectivity_for(topology),
    )


__all__ = [
    "default_zone_bands",
    "build_corridor_sketch",
]
