"""
BuildemUp — C11a — operator M3C_STAIR_NE_CORNER
=================================================

Per spec § 2.1 / § 2.2 / § 3.4: M3c repositions the staircase to the
**NE corner** of the envelope. The proposed Staircase carries
``anchor=WallAxis.NORTH`` (the long edge of the landing footprint sits
flush against the north wall), with origin computed so the east edge
of the footprint coincides with the east envelope wall:

  * ``origin_x_m = envelope_width_m - width_m`` (east-flush)
  * ``origin_y_m = envelope_depth_m - landing_depth_m`` (north-flush)

The W9-d anchor flush check then validates against WallAxis.NORTH.

Family: STAIRCASE. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY.

Per § 3.4 matrix: M3c → C7.staircase_clearance, C9.Inv_4.
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c07.grid_generator import Staircase
from buildemup.components.c07.wall_segment import WallAxis
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


_OPERATOR_ID = MutationOperator.M3C_STAIR_NE


def apply_m3c_stair_ne(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M3C_STAIR_NE. See module docstring."""
    try:
        grid = require_field(context, "grid", _OPERATOR_ID.value)
        current_staircase = require_field(
            context, "staircase", _OPERATOR_ID.value,
        )
    except OperatorPreconditionError as exc:
        return build_invalid_result(
            operator=_OPERATOR_ID,
            source_family_id=source_family_id,
            family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
            invalidity_reason=str(exc),
            rejection_invariant_id=None,
        )

    # NE corner: flush east + flush north.
    new_origin_x = grid.envelope_width_m - current_staircase.width_m
    new_origin_y = grid.envelope_depth_m - current_staircase.landing_depth_m
    new_staircase = Staircase(
        origin_x_m=new_origin_x,
        origin_y_m=new_origin_y,
        width_m=current_staircase.width_m,
        landing_depth_m=current_staircase.landing_depth_m,
        anchor=WallAxis.NORTH,
    )

    predicate_args: dict[tuple[str, str], tuple[tuple, dict]] = {
        ("C7", "staircase_clearance"): ((grid, new_staircase), {}),
        ("C9", "Inv_4"): ((), {}),
    }

    ok, reason, rejection_id = dispatch_predicates(
        _OPERATOR_ID, predicate_args,
    )
    if not ok:
        return build_invalid_result(
            operator=_OPERATOR_ID,
            source_family_id=source_family_id,
            family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
            invalidity_reason=reason or "predicate failure",
            rejection_invariant_id=rejection_id,
        )

    return build_valid_result(
        operator=_OPERATOR_ID,
        source_signature=source_signature,
        source_family_id=source_family_id,
        output_family_id=source_family_id,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    )


__all__ = ["apply_m3c_stair_ne"]
