"""
BuildemUp — C11a — operator M1_HORIZ_FLIP
==========================================

Per spec § 2.1 / § 2.2 / § 3.4: M1 is a horizontal flip (mirror across
the y-axis — ``x_new = envelope_width - x_old``). At Tier A SHALLOW
the operator does not regenerate upstream state; the flip is a
geometric reflection that, by construction, preserves:

  * room count / room areas  (C9.Inv_5, C9.Inv_13 stubs)
  * wet-zone plan stability  (C10.Inv_4, C10.Inv_5 stubs)

Family: FLIP. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY (Strip stays Strip; CentralSpine stays CentralSpine).

M1 does NOT call C5.privacy_zoning — horizontal flip swaps east ↔
west, so the road-facing direction set rotates symmetrically and
cannot push PRIVATE into a road-facing slot that wasn't already there.
M2 (vertical flip) is the operator that DOES carry the C5 predicate.

Per § 3.4 matrix: M1 → C9.Inv_5, C9.Inv_13, C10.Inv_4, C10.Inv_5.
All four are structural-property stubs (always pass).
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c11a.operators._base import (
    TierAOperatorContext,
    build_invalid_result,
    build_valid_result,
    dispatch_predicates,
)
from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationOperator,
    TopologyFamilyTransitionPolicy,
)


_OPERATOR_ID = MutationOperator.M1_HORIZ_FLIP


def apply_m1_horiz_flip(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M1_HORIZ_FLIP.

    Predicates dispatched (per § 3.4):
      * C9.Inv_5  (stub — always pass)
      * C9.Inv_13 (stub — always pass)
      * C10.Inv_4 (stub — always pass)
      * C10.Inv_5 (stub — always pass)

    Sub-2 stubs always pass, so M1 always returns valid in production.
    Tests can confirm rejection paths by injecting a failing predicate
    (see test fixtures) — the dispatch_predicates short-circuit logic
    is exercised regardless.
    """
    # All four predicates are stubs; they don't consume args. The
    # dispatch helper still iterates and records the dispatch.
    predicate_args = {
        ("C9", "Inv_5"):  ((), {}),
        ("C9", "Inv_13"): ((), {}),
        ("C10", "Inv_4"): ((), {}),
        ("C10", "Inv_5"): ((), {}),
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

    # Horizontal flip preserves family.
    return build_valid_result(
        operator=_OPERATOR_ID,
        source_signature=source_signature,
        source_family_id=source_family_id,
        output_family_id=source_family_id,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    )


__all__ = ["apply_m1_horiz_flip"]
