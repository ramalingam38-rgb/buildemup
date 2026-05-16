"""
BuildemUp — C11a — operators._m9_helpers
==========================================

Shared helpers for the four M9 entry-repositioning operators.

Per spec § 2.1 / § 3.4: M9a/b/c/d propose a new ENTRY endpoint position
in the NE region of the envelope and validate it against C8 Inv 21
(``validate_entry_approach``). The four variants differ only in the
target position:

  * M9a — NE center  : (envelope_width / 2 + envelope_width / 4,
                        envelope_depth)        — north wall, east-of-centre
  * M9b — NE corner W: (envelope_width / 2,
                        envelope_depth)        — north wall, centre
  * M9c — NE corner E: (envelope_width,
                        envelope_depth / 2 + envelope_depth / 4)
                                                — east wall, north-of-centre
  * M9d — NE offset  : (envelope_width * 0.75,
                        envelope_depth * 0.9)   — north wall, near NE corner

Tier A SHALLOW: the operator constructs a **minimal probe**
``CorridorPath`` containing a single ENTRY endpoint at the proposed
position and dispatches ``validate_entry_approach`` on it. The probe
is sufficient to ask C8's question — "is an ENTRY at (x, y) valid for
the plot's facing direction?" — without reconstructing the candidate's
full corridor structure (which is Sub-4 / Tier B work).

If the predicate fails, the operator returns invalid with
``rejection_invariant_id="C8.entry_approach"``.

Family: ENTRY. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY (entry repositioning does not transform topology
family).
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c08.schema import (
    ConnectivityType,
    ConsumptionBand,
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorPath,
    CorridorSegment,
    CorridorSegmentKind,
    GridAlignmentReport,
    WidthQuantization,
)
from buildemup.components.c11a.operators._base import (
    OperatorPreconditionError,
    TierAOperatorContext,
    build_invalid_result,
    build_valid_result,
    dispatch_predicates,
    require_field,
)
from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationOperator,
    TopologyFamilyTransitionPolicy,
)
from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# Probe-path builder
# =============================================================================


_PROBE_WIDTH_M = 1.2          # nominal corridor width (Indian residential default)
_PROBE_INLAND_M = 1.0         # how far the probe segment runs from the wall


def build_entry_probe_path(
    entry_point: tuple[float, float],
    envelope_width_m: float,
    envelope_depth_m: float,
) -> CorridorPath:
    """Construct a minimal-valid CorridorPath holding a single ENTRY
    endpoint at ``entry_point``.

    The probe is ONLY used to call validate_entry_approach. It carries:
      * ``has_corridor=True``
      * one PRIMARY segment with the ENTRY endpoint at ``entry_point``
        and a partner DEAD_END endpoint inland
      * a free-width GridAlignmentReport (no quantisation; advisory)
      * ConsumptionBand.LOW (advisory; not read by the predicate)

    The partner endpoint is placed inland by ``_PROBE_INLAND_M``
    metres in the direction perpendicular to the wall the entry sits
    on. We infer "which wall" from the entry's coordinates relative
    to the envelope:

      * y == envelope_depth (north wall) → partner runs SOUTH
      * y == 0              (south wall) → partner runs NORTH
      * x == envelope_width (east  wall) → partner runs WEST
      * x == 0              (west  wall) → partner runs EAST

    For NE-region entries (y == envelope_depth or x == envelope_width),
    the orientation choice is unambiguous; M9a/b/d sit on the north
    wall, M9c sits on the east wall.

    If the entry isn't on any wall (which would be an operator-internal
    bug at v1), the function raises ``ValueError`` so we don't silently
    construct a probe that misrepresents the proposal.
    """
    x, y = entry_point
    eps = 1e-6

    if abs(y - envelope_depth_m) < eps:
        # North wall — partner south of entry.
        partner_xy = (x, y - _PROBE_INLAND_M)
        runs = PlotOrientation.SOUTH
    elif abs(y - 0.0) < eps:
        # South wall — partner north.
        partner_xy = (x, y + _PROBE_INLAND_M)
        runs = PlotOrientation.NORTH
    elif abs(x - envelope_width_m) < eps:
        # East wall — partner west.
        partner_xy = (x - _PROBE_INLAND_M, y)
        runs = PlotOrientation.WEST
    elif abs(x - 0.0) < eps:
        # West wall — partner east.
        partner_xy = (x + _PROBE_INLAND_M, y)
        runs = PlotOrientation.EAST
    else:
        raise ValueError(
            f"build_entry_probe_path: entry_point {entry_point} is not "
            f"on any envelope wall (envelope "
            f"{envelope_width_m}x{envelope_depth_m}). M9 operators "
            f"propose entries on a wall by construction; this indicates "
            f"an operator-internal bug."
        )

    entry_endpoint = CorridorEndpoint(
        kind=CorridorEndpointKind.ENTRY,
        point_m=(float(x), float(y)),
    )
    inland_endpoint = CorridorEndpoint(
        kind=CorridorEndpointKind.DEAD_END,
        point_m=(float(partner_xy[0]), float(partner_xy[1])),
    )
    segment = CorridorSegment(
        kind=CorridorSegmentKind.PRIMARY,
        start=entry_endpoint,
        end=inland_endpoint,
        constant_width_m=_PROBE_WIDTH_M,
        start_width_m=_PROBE_WIDTH_M,
        end_width_m=_PROBE_WIDTH_M,
        taper_zone_m=0.0,
        length_m=_PROBE_INLAND_M,
        runs_along=runs,
    )
    grid_align = GridAlignmentReport(
        quantization_used=WidthQuantization.NONE_FREE_WIDTH,
        edges_aligned_count=0,
        edges_total_count=0,
        tapered_edges_count=0,
        grid_alignment_score=0.0,
    )
    return CorridorPath(
        has_corridor=True,
        segments=(segment,),
        envelopes=(),
        total_length_m=_PROBE_INLAND_M,
        total_area_m2=_PROBE_WIDTH_M * _PROBE_INLAND_M,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=ConnectivityType.LINEAR,
        grid_alignment=grid_align,
    )


# =============================================================================
# Shared M9 apply core
# =============================================================================


def apply_m9_variant(
    *,
    operator: MutationOperator,
    proposed_entry: tuple[float, float],
    source: Any,
    context: TierAOperatorContext,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Run the shared M9 dispatch path for any of the four variants.

    The variant-specific logic is the choice of ``proposed_entry``,
    which the per-variant operator file computes from the envelope.

    Pre-conditions: ``envelope_width_m``, ``envelope_depth_m``,
    ``plot_facing`` populated in the context.
    """
    try:
        envelope_width_m = require_field(
            context, "envelope_width_m", operator.value,
        )
        envelope_depth_m = require_field(
            context, "envelope_depth_m", operator.value,
        )
        plot_facing = require_field(
            context, "plot_facing", operator.value,
        )
        probe_path = build_entry_probe_path(
            proposed_entry, envelope_width_m, envelope_depth_m,
        )
    except (OperatorPreconditionError, ValueError) as exc:
        return build_invalid_result(
            operator=operator,
            source_family_id=source_family_id,
            family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
            invalidity_reason=str(exc),
            rejection_invariant_id=None,
        )

    predicate_args: dict[tuple[str, str], tuple[tuple, dict]] = {
        ("C8", "entry_approach"): (
            (probe_path, envelope_width_m, envelope_depth_m, plot_facing),
            {},
        ),
    }

    ok, reason, rejection_id = dispatch_predicates(operator, predicate_args)
    if not ok:
        return build_invalid_result(
            operator=operator,
            source_family_id=source_family_id,
            family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
            invalidity_reason=reason or "predicate failure",
            rejection_invariant_id=rejection_id,
        )

    return build_valid_result(
        operator=operator,
        source_signature=source_signature,
        source_family_id=source_family_id,
        output_family_id=source_family_id,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    )


__all__ = [
    "build_entry_probe_path",
    "apply_m9_variant",
]
