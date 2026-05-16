"""
BuildemUp — C11a — operator M9D_ENTRY_OFFSET_NE
=================================================

Per spec § 2.1 / § 2.2 / § 3.4: M9d proposes an entry on the north
wall, offset toward the NE corner — beyond M9a's east-of-centre but
not at the corner itself.

Proposed position: ``(envelope_width_m * 0.85, envelope_depth_m)``.
Per § 3.4 matrix: M9d → C8.entry_approach.

Family: ENTRY. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY.

The four M9 variants together provide a small spread of NE-region
entry positions (M9a 0.75-W, M9b 0.5-W, M9c east-wall, M9d 0.85-W)
so the topology mutation layer can sample diverse but plausible
entries without violating the plot's facing constraints. C8's
predicate decides which of the four are viable per plot.
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


_OPERATOR_ID = MutationOperator.M9D_ENTRY_OFF


def apply_m9d_entry_offset_ne(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M9D_ENTRY_OFFSET_NE. See module docstring."""
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

    proposed_entry = (envelope_width_m * 0.85, envelope_depth_m)
    return apply_m9_variant(
        operator=_OPERATOR_ID,
        proposed_entry=proposed_entry,
        source=source,
        context=context,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )


__all__ = ["apply_m9d_entry_offset_ne"]
