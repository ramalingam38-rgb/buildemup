"""
BuildemUp — C11a — operator M5_ZONE_SWAP
==========================================

Per spec § 2.1 / § 2.2 / § 3.4 / § 3.6: M5 swaps the directional
assignments of the PUBLIC and PRIVATE zone bands. If the source has

    zone_bands = {PUBLIC: NORTH, PRIVATE: SOUTH, SERVICE: WEST,
                  CIRCULATION: EAST}

then M5 produces

    zone_bands = {PUBLIC: SOUTH, PRIVATE: NORTH, SERVICE: WEST,
                  CIRCULATION: EAST}

SERVICE and CIRCULATION are unchanged.

Family: ZONE. Tier: SHALLOW. Family-transition policy:
TRANSFORMS_FAMILY (per W#5 Q22 + § 3.6 — M5 on a Courtyard turns it
into "STRIP_VESTIGIAL_COURT", which classification is computed by
Sub-4's emergent-classification logic).

Per § 3.4 matrix: M5 → C5.privacy_zoning, C10.Inv_5b (stub).

Pre-conditions:
  * context.zone_bands populated, contains BOTH PUBLIC and PRIVATE
    entries (operator-internal pre-condition — swap is undefined if
    only one is present)
  * context.plot_facing populated
"""
from __future__ import annotations

from typing import Any, Mapping

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


_OPERATOR_ID = MutationOperator.M5_ZONE_SWAP
_FAMILY_POLICY = TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY


def _build_swapped_zone_bands(
    zone_bands: Mapping["ZoneBand", "PlotOrientation"],
) -> Mapping["ZoneBand", "PlotOrientation"]:
    """Return a new mapping with PUBLIC and PRIVATE direction swapped.

    Raises:
        OperatorPreconditionError if either band is missing —
        the swap is undefined.
    """
    # Imported lazily to avoid heavy module-load deps.
    from buildemup.components.c05.schema import ZoneBand

    public_dir = zone_bands.get(ZoneBand.PUBLIC)
    private_dir = zone_bands.get(ZoneBand.PRIVATE)

    if public_dir is None or private_dir is None:
        missing = [
            band.value for band, val in (
                (ZoneBand.PUBLIC, public_dir),
                (ZoneBand.PRIVATE, private_dir),
            ) if val is None
        ]
        raise OperatorPreconditionError(
            f"M5_ZONE_SWAP pre-condition failure: zone_bands missing "
            f"required entries {missing}. Swap is undefined when "
            f"either PUBLIC or PRIVATE is absent."
        )

    new_bands = dict(zone_bands)
    new_bands[ZoneBand.PUBLIC] = private_dir
    new_bands[ZoneBand.PRIVATE] = public_dir
    return new_bands


def apply_m5_zone_swap(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M5_ZONE_SWAP. See module docstring."""
    try:
        zone_bands = require_field(context, "zone_bands", _OPERATOR_ID.value)
        plot_facing = require_field(context, "plot_facing", _OPERATOR_ID.value)
        swapped = _build_swapped_zone_bands(zone_bands)
    except OperatorPreconditionError as exc:
        return build_invalid_result(
            operator=_OPERATOR_ID,
            source_family_id=source_family_id,
            family_transition_policy=_FAMILY_POLICY,
            invalidity_reason=str(exc),
            rejection_invariant_id=None,
        )

    predicate_args: dict[tuple[str, str], tuple[tuple, dict]] = {
        ("C5", "privacy_zoning"): ((swapped, plot_facing), {}),
        ("C10", "Inv_5b"): ((), {}),
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


__all__ = ["apply_m5_zone_swap"]
