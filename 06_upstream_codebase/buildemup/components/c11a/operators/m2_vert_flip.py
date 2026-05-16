"""
BuildemUp — C11a — operator M2_VERT_FLIP
==========================================

Per spec § 2.1 / § 2.2 / § 3.4: M2 is a vertical flip (mirror across
the x-axis — ``y_new = envelope_depth - y_old``). Unlike M1, vertical
flip swaps the NORTH ↔ SOUTH zone-band assignments — so a topology
that placed PRIVATE on NORTH ends up with PRIVATE on SOUTH after M2.
This may push PRIVATE into a road-facing direction (e.g., a south-
facing plot now has bedrooms on the road-facing edge), which the C5
``validate_privacy_zoning`` predicate rejects.

Family: FLIP. Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY.

Per § 3.4 matrix: M2 → C5.privacy_zoning, C9.Inv_5, C9.Inv_13,
C10.Inv_5.

The proposed mutation is constructed by mapping each existing
``zone_bands`` entry's PlotOrientation through the vertical-flip
mapping (N↔S, NE↔SE, NW↔SW; E and W unchanged). The flipped mapping
is then passed to ``validate_privacy_zoning`` together with the
plot's facing direction.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

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


_OPERATOR_ID = MutationOperator.M2_VERT_FLIP


# Vertical-flip mapping — north flips to south and vice versa.
# Intercardinals: NE ↔ SE, NW ↔ SW. East and West unchanged (the flip
# is across the x-axis, so east/west cardinals are invariants).
def _vflip_orientation(o: "PlotOrientation") -> "PlotOrientation":
    """Map a PlotOrientation through a vertical flip across the x-axis."""
    # Imported lazily to avoid pulling envelope domain at module load.
    from buildemup.domain.envelope import PlotOrientation
    return {
        PlotOrientation.NORTH:     PlotOrientation.SOUTH,
        PlotOrientation.SOUTH:     PlotOrientation.NORTH,
        PlotOrientation.NORTHEAST: PlotOrientation.SOUTHEAST,
        PlotOrientation.SOUTHEAST: PlotOrientation.NORTHEAST,
        PlotOrientation.NORTHWEST: PlotOrientation.SOUTHWEST,
        PlotOrientation.SOUTHWEST: PlotOrientation.NORTHWEST,
        PlotOrientation.EAST:      PlotOrientation.EAST,
        PlotOrientation.WEST:      PlotOrientation.WEST,
    }[o]


def _build_flipped_zone_bands(
    zone_bands: Mapping["ZoneBand", "PlotOrientation"],
) -> Mapping["ZoneBand", "PlotOrientation"]:
    """Return a new zone_bands mapping with each direction vflipped."""
    return {band: _vflip_orientation(direction)
            for band, direction in zone_bands.items()}


def apply_m2_vert_flip(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M2_VERT_FLIP.

    Predicates dispatched (per § 3.4 matrix in registry order):
      * C5.privacy_zoning — runs against flipped zone_bands + plot_facing
      * C9.Inv_5  (stub)
      * C9.Inv_13 (stub)
      * C10.Inv_5 (stub)

    Pre-conditions on context (raises OperatorPreconditionError →
    invalid result):
      * ``zone_bands`` populated (mapping ZoneBand → PlotOrientation)
      * ``plot_facing`` populated (PlotOrientation)
    """
    try:
        zone_bands = require_field(context, "zone_bands", _OPERATOR_ID.value)
        plot_facing = require_field(context, "plot_facing", _OPERATOR_ID.value)
    except OperatorPreconditionError as exc:
        return build_invalid_result(
            operator=_OPERATOR_ID,
            source_family_id=source_family_id,
            family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
            invalidity_reason=str(exc),
            rejection_invariant_id=None,
        )

    flipped_zone_bands = _build_flipped_zone_bands(zone_bands)

    # Dispatch predicates with per-id args.
    predicate_args: dict[tuple[str, str], tuple[tuple, dict]] = {
        ("C5", "privacy_zoning"): ((flipped_zone_bands, plot_facing), {}),
        ("C9", "Inv_5"):  ((), {}),
        ("C9", "Inv_13"): ((), {}),
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

    return build_valid_result(
        operator=_OPERATOR_ID,
        source_signature=source_signature,
        source_family_id=source_family_id,
        output_family_id=source_family_id,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    )


__all__ = ["apply_m2_vert_flip"]
