"""
BuildemUp — C11a — operator M3B_STAIR_WEST
============================================

Per spec § 2.1 / § 2.2 / § 3.4: M3b repositions the staircase flush
against the WEST envelope wall. The proposed Staircase carries
``anchor=WallAxis.WEST``, with ``origin_x_m = 0.0`` (flush left) and
``origin_y_m`` carried from the source.

Family: STAIRCASE. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY.

Per § 3.4 matrix: M3b → C7.staircase_clearance, C9.Inv_4.
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


_OPERATOR_ID = MutationOperator.M3B_STAIR_WEST


def apply_m3b_stair_west(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M3B_STAIR_WEST. See module docstring."""
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

    # West-anchored: flush at x=0.
    new_staircase = Staircase(
        origin_x_m=0.0,
        origin_y_m=current_staircase.origin_y_m,
        width_m=current_staircase.width_m,
        landing_depth_m=current_staircase.landing_depth_m,
        anchor=WallAxis.WEST,
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


__all__ = ["apply_m3b_stair_west"]
