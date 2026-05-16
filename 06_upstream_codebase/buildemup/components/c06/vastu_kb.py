"""
BuildemUp† — Component 6 Vastu KB.

8-direction × 6-function PARTIAL-tier Vastu table + the weighted-average
aggregation rule that maps 8-dir Vastu values to 4-dir cardinal scores.

Per SPEC v0.6 LOCKED § 4.1.4 + § 14.4 + § 14.9 + § 14.19.

ARCHITECTURAL INVARIANT (per § 14.21 — v0.7 consolidation): this module
is the INTERNAL 8-direction half of C6's intentionally-asymmetric
direction model. The EXTERNAL contract is cardinal-only (B-107); the
INTERNAL Vastu KB stays 8-keyed because Vastu's signature placements
(NE/POOJA Ishaan, SE/KITCHEN Agni, SW/BEDROOM master) live at
intercardinal positions in the canonical Mandala. Collapsing this table
to 4-direction would erase ~half its product value. See schema.py
CARDINAL_FACINGS docstring + spec § 14.21 for the consolidated invariant.

Tier handling (§ 6 + § 14.8):
  - OFF      → callers should not invoke this module (vastu_score = 0.0)
  - PARTIAL  → reads from VASTU_TABLE_PARTIAL (this file)
  - FULL     → NotImplementedError; requires populated vastu_engine KB (B-099)

Why this is its own module (Q3 / S31):
  - Tabular KB data, not algorithm — keeps signals.py focused on logic
  - B-099 (FULL tier KB authoring) becomes a self-contained edit
  - Vastu has cultural significance; isolating the table makes future edits
    by domain experts easier to review

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c06.schema import CARDINAL_FACINGS, FunctionRole
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────────
# 8-direction × 6-function Vastu table (PARTIAL tier baseline)
# Per SPEC v0.6 § 4.1.4
# ─────────────────────────────────────────────────────────────────────────────


def _frozen(d: dict[FunctionRole, float]) -> Mapping[FunctionRole, float]:
    """Wrap a per-function dict in MappingProxyType for true immutability."""
    return MappingProxyType(dict(d))


_RAW_VASTU_TABLE: dict[PlotOrientation, dict[FunctionRole, float]] = {
    PlotOrientation.NORTH: {
        FunctionRole.LIVING:   0.85,
        FunctionRole.BEDROOM:  0.6,
        FunctionRole.KITCHEN:  0.3,
        FunctionRole.POOJA:    0.7,
        FunctionRole.WET_AREA: 0.4,
        FunctionRole.UTILITY:  0.5,
    },
    PlotOrientation.NORTHEAST: {
        FunctionRole.LIVING:   0.9,
        FunctionRole.BEDROOM:  0.5,
        FunctionRole.KITCHEN:  0.1,
        FunctionRole.POOJA:    1.0,   # signature NE/pooja per § 4.1.4
        FunctionRole.WET_AREA: 0.0,   # signature NE/wet_area = 0.0 per § 4.1.4
        FunctionRole.UTILITY:  0.3,
    },
    PlotOrientation.EAST: {
        FunctionRole.LIVING:   0.85,
        FunctionRole.BEDROOM:  0.7,
        FunctionRole.KITCHEN:  0.5,
        FunctionRole.POOJA:    0.85,
        FunctionRole.WET_AREA: 0.3,
        FunctionRole.UTILITY:  0.5,
    },
    PlotOrientation.SOUTHEAST: {
        FunctionRole.LIVING:   0.55,
        FunctionRole.BEDROOM:  0.4,
        FunctionRole.KITCHEN:  1.0,   # signature SE/kitchen per § 4.1.4
        FunctionRole.POOJA:    0.3,
        FunctionRole.WET_AREA: 0.4,
        FunctionRole.UTILITY:  0.5,
    },
    PlotOrientation.SOUTH: {
        FunctionRole.LIVING:   0.5,
        FunctionRole.BEDROOM:  0.4,
        FunctionRole.KITCHEN:  0.7,
        FunctionRole.POOJA:    0.2,
        FunctionRole.WET_AREA: 0.5,
        FunctionRole.UTILITY:  0.6,
    },
    PlotOrientation.SOUTHWEST: {
        FunctionRole.LIVING:   0.4,
        FunctionRole.BEDROOM:  1.0,   # signature SW/bedroom per § 4.1.4
        FunctionRole.KITCHEN:  0.4,
        FunctionRole.POOJA:    0.2,
        FunctionRole.WET_AREA: 0.5,
        FunctionRole.UTILITY:  0.7,
    },
    PlotOrientation.WEST: {
        FunctionRole.LIVING:   0.5,
        FunctionRole.BEDROOM:  0.7,
        FunctionRole.KITCHEN:  0.6,
        FunctionRole.POOJA:    0.3,
        FunctionRole.WET_AREA: 0.7,
        FunctionRole.UTILITY:  0.85,
    },
    PlotOrientation.NORTHWEST: {
        FunctionRole.LIVING:   0.55,
        FunctionRole.BEDROOM:  0.6,
        FunctionRole.KITCHEN:  0.7,
        FunctionRole.POOJA:    0.3,
        FunctionRole.WET_AREA: 0.7,
        FunctionRole.UTILITY:  0.9,
    },
}


# Public, immutable view: outer Mapping keyed by all 8 PlotOrientation members,
# inner Mappings keyed by all 6 FunctionRole members.
VASTU_TABLE_PARTIAL: Mapping[PlotOrientation, Mapping[FunctionRole, float]] = (
    MappingProxyType({d: _frozen(table) for d, table in _RAW_VASTU_TABLE.items()})
)


# ─────────────────────────────────────────────────────────────────────────────
# Adjacency (per SPEC v0.6 § 4.1.4)
# ─────────────────────────────────────────────────────────────────────────────


# CCW intercardinal neighbour for each cardinal (compass with N at top,
# rotation = counter-clockwise as viewed from above).
_CCW_ADJACENT: Mapping[PlotOrientation, PlotOrientation] = MappingProxyType({
    PlotOrientation.NORTH: PlotOrientation.NORTHWEST,
    PlotOrientation.EAST:  PlotOrientation.NORTHEAST,
    PlotOrientation.SOUTH: PlotOrientation.SOUTHEAST,
    PlotOrientation.WEST:  PlotOrientation.SOUTHWEST,
})

# CW intercardinal neighbour for each cardinal (clockwise as viewed from above).
_CW_ADJACENT: Mapping[PlotOrientation, PlotOrientation] = MappingProxyType({
    PlotOrientation.NORTH: PlotOrientation.NORTHEAST,
    PlotOrientation.EAST:  PlotOrientation.SOUTHEAST,
    PlotOrientation.SOUTH: PlotOrientation.SOUTHWEST,
    PlotOrientation.WEST:  PlotOrientation.NORTHWEST,
})


def adjacent_intercardinals(cardinal: PlotOrientation) -> tuple[PlotOrientation, PlotOrientation]:
    """Return the two intercardinal neighbours of a cardinal direction.

    Order: (CCW, CW). Per SPEC v0.6 § 4.1.4.

    Raises ValueError if `cardinal` is not in CARDINAL_FACINGS.
    """
    if cardinal not in CARDINAL_FACINGS:
        raise ValueError(
            f"adjacent_intercardinals expects a cardinal PlotOrientation; "
            f"got {cardinal.value} (cardinals: NORTH, EAST, SOUTH, WEST)"
        )
    return (_CCW_ADJACENT[cardinal], _CW_ADJACENT[cardinal])


# ─────────────────────────────────────────────────────────────────────────────
# Vastu score lookup (tier-aware) + 4-dir aggregation
# ─────────────────────────────────────────────────────────────────────────────


def vastu_score_4dir(
    cardinal: PlotOrientation,
    function: FunctionRole,
    tier: VastuTier,
) -> float:
    """Return the Vastu score for (cardinal direction, function) at the given tier.

    Per SPEC v0.6 § 4.1.4 (weighted-average aggregation 8-dir → 4-dir):

        result = (1.0 × VASTU_TABLE[c][f]
                + 0.5 × VASTU_TABLE[ccw_adj(c)][f]
                + 0.5 × VASTU_TABLE[cw_adj(c)][f]) / 2.0

    Tier semantics (§ 6 + § 14.8):
      - OFF     : returns 0.0 (callers should not even invoke us, but defensive)
      - PARTIAL : reads VASTU_TABLE_PARTIAL
      - FULL    : raises NotImplementedError (B-099)

    Raises:
      NotImplementedError if tier == FULL (B-099 — requires vastu_engine KB).
      ValueError if cardinal is not in CARDINAL_FACINGS.
      TypeError if tier is not a VastuTier instance.
    """
    if not isinstance(tier, VastuTier):
        raise TypeError(
            f"vastu_score_4dir: tier must be VastuTier; got {type(tier).__name__}"
        )
    if tier == VastuTier.OFF:
        return 0.0
    if tier == VastuTier.FULL:
        raise NotImplementedError(
            "FULL tier requires vastu_engine KB; B-099. Use PARTIAL."
        )
    # PARTIAL
    if cardinal not in CARDINAL_FACINGS:
        raise ValueError(
            f"vastu_score_4dir expects a cardinal PlotOrientation; "
            f"got {cardinal.value}"
        )
    ccw, cw = adjacent_intercardinals(cardinal)
    return (
        1.0 * VASTU_TABLE_PARTIAL[cardinal][function]
        + 0.5 * VASTU_TABLE_PARTIAL[ccw][function]
        + 0.5 * VASTU_TABLE_PARTIAL[cw][function]
    ) / 2.0


__all__ = [
    "VASTU_TABLE_PARTIAL",
    "adjacent_intercardinals",
    "vastu_score_4dir",
]

