"""
BuildemUp — C11a — operator M9C_ENTRY_NE_CORNER_E
====================================================

Per spec § 2.1 / § 2.2 / § 3.4: M9c proposes an entry on the **east
wall, north-of-centre** — the only M9 variant whose proposed entry
sits on the east envelope edge rather than the north.

Proposed position: ``(envelope_width_m, envelope_depth_m * 0.75)``.
Per § 3.4 matrix: M9c → C8.entry_approach.

Family: ENTRY. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY.

This variant exists so a plot whose facing direction admits east-edge
entries (E, NE, SE per ``_FACING_TO_EDGES``) can have the entry
proposed there too — diversification beyond north-wall-only.

See ``_m9_helpers`` for the shared probe-path construction.
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


_OPERATOR_ID = MutationOperator.M9C_ENTRY_E


def apply_m9c_entry_ne_corner_e(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M9C_ENTRY_NE_CORNER_E. See module docstring."""
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

    proposed_entry = (envelope_width_m, envelope_depth_m * 0.75)
    return apply_m9_variant(
        operator=_OPERATOR_ID,
        proposed_entry=proposed_entry,
        source=source,
        context=context,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )


__all__ = ["apply_m9c_entry_ne_corner_e"]
