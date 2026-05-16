"""
BuildemUp — C11a — operator M3A_STAIR_EAST
============================================

Per spec § 2.1 / § 2.2 / § 3.4: M3a repositions the staircase to be
flush against the EAST envelope wall. The proposed Staircase carries
``anchor=WallAxis.EAST``, with ``origin_x_m = envelope_width_m -
width_m`` and ``origin_y_m`` carried from the source staircase.

Family: STAIRCASE. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY.

Per § 3.4 matrix: M3a → C7.staircase_clearance, C9.Inv_4.

Predicate dispatch:
  * C7.staircase_clearance(grid, new_staircase): runs the W9 a/b/c/d
    sub-checks (width, landing depth scaling per K-4 patch, envelope
    overflow, anchor flush) on the proposed footprint.
  * C9.Inv_4: stub (room-graph cardinality preservation is structural).

Pre-conditions:
  * context.grid populated
  * context.staircase populated (carries width_m + landing_depth_m
    from the source — repositioning preserves footprint dimensions)
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


_OPERATOR_ID = MutationOperator.M3A_STAIR_EAST


def apply_m3a_stair_east(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M3A_STAIR_EAST.

    Constructs a proposal Staircase flush with the east wall and
    dispatches the § 3.4 predicates against it. Returns an invalid
    result if W9 fails (e.g., the existing landing depth is smaller
    than the new width-derived requirement on a wider plot).
    """
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

    # Build the proposed east-anchored footprint. Width and landing
    # depth carry from the source; only the position changes.
    new_origin_x = grid.envelope_width_m - current_staircase.width_m
    new_staircase = Staircase(
        origin_x_m=new_origin_x,
        origin_y_m=current_staircase.origin_y_m,
        width_m=current_staircase.width_m,
        landing_depth_m=current_staircase.landing_depth_m,
        anchor=WallAxis.EAST,
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


__all__ = ["apply_m3a_stair_east"]
