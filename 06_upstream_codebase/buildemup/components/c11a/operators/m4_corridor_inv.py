"""
BuildemUp — C11a — operator M4_CORRIDOR_INV
=============================================

Per spec § 2.1 / § 2.2 / § 3.4: M4 inverts the corridor topology of
the source candidate. At Tier A SHALLOW the inversion is conceptual —
operator-level metadata captures the proposed circulation reshape but
the actual CorridorPath rewrite is deferred to Sub-4 / Tier B
regeneration. M4 here:

  1. Pre-checks ``has_corridor=True`` on the source (operators with
     ``has_corridor=False`` cannot invert anything → operator-internal
     pre-condition failure).
  2. Dispatches its § 3.4 predicates (both stubs at v1).
  3. Returns a TRANSFORMS_FAMILY result — the source family signature
     is changed by the inversion (e.g., CentralSpine becomes Strip).

Family: CORRIDOR. Tier: SHALLOW. Family-transition policy:
TRANSFORMS_FAMILY (per W#5 Q22 adjudication: "M4 corridor inversion
converts central-spine to edge-strip but the room-graph is preserved
— TRANSFORMS_FAMILY, not INVALIDATES_FAMILY").

Per § 3.4 matrix: M4 → C9.Inv_4 (stub), C10.Inv_5 (stub).

Output_family_id is set to ``transformed_from_<source>`` at Sub-2
since the precise post-inversion family classification is part of
Sub-4's emergent-classification logic (§ 2.3 ``classify_lineage_depth``
hooks). The placeholder is canonical and Sub-4 will refine.
"""
from __future__ import annotations

from typing import Any

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


_OPERATOR_ID = MutationOperator.M4_CORRIDOR_INV
_FAMILY_POLICY = TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY


def apply_m4_corridor_inv(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M4_CORRIDOR_INV.

    Pre-conditions:
      * context.corridor_path populated AND ``has_corridor=True``.

    Returns invalid (operator-internal pre-condition failure) if the
    source has no corridor — the inversion is undefined. The
    rejection_invariant_id is None in that case (not an upstream-rule
    rejection).
    """
    try:
        corridor_path = require_field(
            context, "corridor_path", _OPERATOR_ID.value,
        )
    except OperatorPreconditionError as exc:
        return build_invalid_result(
            operator=_OPERATOR_ID,
            source_family_id=source_family_id,
            family_transition_policy=_FAMILY_POLICY,
            invalidity_reason=str(exc),
            rejection_invariant_id=None,
        )

    if not corridor_path.has_corridor:
        return build_invalid_result(
            operator=_OPERATOR_ID,
            source_family_id=source_family_id,
            family_transition_policy=_FAMILY_POLICY,
            invalidity_reason=(
                "M4_CORRIDOR_INV pre-condition failure: source candidate "
                "has has_corridor=False; corridor inversion is undefined "
                "for corridor-free topologies (e.g., small Strips)."
            ),
            rejection_invariant_id=None,
        )

    # Dispatch the two stub predicates per § 3.4.
    predicate_args: dict[tuple[str, str], tuple[tuple, dict]] = {
        ("C9", "Inv_4"):  ((), {}),
        ("C10", "Inv_5"): ((), {}),
    }

    ok, reason, rejection_id = dispatch_predicates(
        _OPERATOR_ID, predicate_args,
    )
    if not ok:
        return build_invalid_result(
            operator=_OPERATOR_ID,
            source_family_id=source_family_id,
            family_transition_policy=_FAMILY_POLICY,
            invalidity_reason=reason or "predicate failure",
            rejection_invariant_id=rejection_id,
        )

    return build_valid_result(
        operator=_OPERATOR_ID,
        source_signature=source_signature,
        source_family_id=source_family_id,
        output_family_id=f"transformed_from_{source_family_id}",
        family_transition_policy=_FAMILY_POLICY,
    )


__all__ = ["apply_m4_corridor_inv"]
