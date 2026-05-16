"""
BuildemUp — C11a — operator M9A_ENTRY_NE_CENTER
=================================================

Per spec § 2.1 / § 2.2 / § 3.4: M9a proposes an entry on the **north
wall, east-of-centre** (within the NE region of the envelope).

Proposed position: ``(envelope_width_m * 0.75, envelope_depth_m)``.
Per § 3.4 matrix: M9a → C8.entry_approach.

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


_OPERATOR_ID = MutationOperator.M9A_ENTRY_CTR


def apply_m9a_entry_ne_center(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M9A_ENTRY_NE_CENTER. See module docstring."""
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

    proposed_entry = (envelope_width_m * 0.75, envelope_depth_m)
    return apply_m9_variant(
        operator=_OPERATOR_ID,
        proposed_entry=proposed_entry,
        source=source,
        context=context,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )


__all__ = ["apply_m9a_entry_ne_center"]
