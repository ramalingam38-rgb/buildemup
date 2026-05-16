"""
BuildemUp — C11a — operator M9B_ENTRY_NE_CORNER_W
====================================================

Per spec § 2.1 / § 2.2 / § 3.4: M9b proposes an entry on the **north
wall at centre** — the point in the NE region closest to the west
boundary of the NE quadrant.

Proposed position: ``(envelope_width_m / 2, envelope_depth_m)``.
Per § 3.4 matrix: M9b → C8.entry_approach.

Family: ENTRY. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY.

See ``_m9_helpers`` for the shared probe-path construction and
predicate dispatch logic.
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c11a.operators._base import (
    OperatorPreconditionError,
    TierAOperatorContext,
    build_invalid_result,
    require_field,
)
from buildemup.components.c11a.operators._m9_helpers import apply_m9_variant
from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationOperator,
    TopologyFamilyTransitionPolicy,
)


_OPERATOR_ID = MutationOperator.M9B_ENTRY_W


def apply_m9b_entry_ne_corner_w(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M9B_ENTRY_NE_CORNER_W. See module docstring."""
    try:
        envelope_width_m = require_field(
            context, "envelope_width_m", _OPERATOR_ID.value,
        )
        envelope_depth_m = require_field(
            context, "envelope_depth_m", _OPERATOR_ID.value,
        )
    except OperatorPreconditionError as exc:
        return build_invalid_result(
            operator=_OPERATOR_ID,
            source_family_id=source_family_id,
            family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
            invalidity_reason=str(exc),
            rejection_invariant_id=None,
        )

    proposed_entry = (envelope_width_m / 2, envelope_depth_m)
    return apply_m9_variant(
        operator=_OPERATOR_ID,
        proposed_entry=proposed_entry,
        source=source,
        context=context,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )


__all__ = ["apply_m9b_entry_ne_corner_w"]
