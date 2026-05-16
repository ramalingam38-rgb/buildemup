"""
BuildemUp† — Component 6 signals.

Sun, wind, and road score tables. Signal weighting (per climate + Vastu tier).
Signal dominance derivation. Per-function multipliers.

Per SPEC v0.6 LOCKED §§ 4.1.1–4.1.3, 4.2, 4.3.

Public surface:
  - sun_score(direction)                                   — cardinal direction → [0, 1]
  - wind_score(direction, climate_zone)                    — cardinal direction → [0, 1]
  - road_score(direction, plot_facing, secondary_road_dir) — cardinal direction → [0, 1]
  - sun_function_lookup(function)                          — per-function multiplier
  - wind_function_lookup(function)                         — per-function multiplier
  - compute_weights(climate_zone, vastu_tier)              — returns (weights_raw, weights_applied)
  - compute_signal_dominance(weights_raw)                  — returns (dominance, dominant_signal)

What's NOT here:
  - Vastu table + 4-dir aggregation → vastu_kb.py
  - Permutation enumeration / scoring / tie-break → optimizer.py
  - Public API → select.py

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import ClimateZone
from buildemup.components.c06.schema import (
    CARDINAL_FACINGS,
    SIGNAL_DOMINANCE_THRESHOLD,
    FunctionRole,
)
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────────
# § 4.1.1 — Sun-score table (cardinal, climate-independent)
# ─────────────────────────────────────────────────────────────────────────────


_SUN_SCORE: Mapping[PlotOrientation, float] = MappingProxyType({
    PlotOrientation.NORTH: 0.95,
    PlotOrientation.EAST:  0.85,
    PlotOrientation.SOUTH: 0.55,
    PlotOrientation.WEST:  0.20,
})


def sun_score(direction: PlotOrientation) -> float:
    """Per-direction sun score. Per SPEC v0.6 § 4.1.1.

    Cardinal direction only. Intercardinal raises ValueError (caller bug
    if reached — input boundary should have caught it via § 6 row 5).
    """
    if direction not in CARDINAL_FACINGS:
        raise ValueError(
            f"sun_score: cardinal direction required (C6 v1); got {direction.value}. "
            f"Intercardinal facing should have been rejected at input boundary (B-107)."
        )
    return _SUN_SCORE[direction]


# ─────────────────────────────────────────────────────────────────────────────
# § 4.1.2 — Wind-score table (cardinal × 3 supported climates)
# ─────────────────────────────────────────────────────────────────────────────


_WIND_SCORE: Mapping[ClimateZone, Mapping[PlotOrientation, float]] = MappingProxyType({
    ClimateZone.WARM_HUMID: MappingProxyType({
        PlotOrientation.NORTH: 0.6,
        PlotOrientation.EAST:  0.7,
        PlotOrientation.SOUTH: 0.9,
        PlotOrientation.WEST:  0.85,
    }),
    ClimateZone.COMPOSITE: MappingProxyType({
        PlotOrientation.NORTH: 0.7,
        PlotOrientation.EAST:  0.6,
        PlotOrientation.SOUTH: 0.5,
        PlotOrientation.WEST:  0.5,
    }),
    ClimateZone.TEMPERATE: MappingProxyType({
        PlotOrientation.NORTH: 0.7,
        PlotOrientation.EAST:  0.7,
        PlotOrientation.SOUTH: 0.7,
        PlotOrientation.WEST:  0.7,
    }),
})


def wind_score(direction: PlotOrientation, climate_zone: ClimateZone) -> float:
    """Per-direction wind score for a supported climate. Per SPEC v0.6 § 4.1.2.

    Raises ValueError if direction is not cardinal.
    Raises NotImplementedError (B-098) if climate is HOT_DRY or COLD.
    """
    if direction not in CARDINAL_FACINGS:
        raise ValueError(
            f"wind_score: cardinal direction required; got {direction.value}"
        )
    if climate_zone not in _WIND_SCORE:
        raise NotImplementedError(
            f"wind_score: climate {climate_zone.value} not supported in v1; B-098. "
            f"Supported: {sorted(c.value for c in _WIND_SCORE)}."
        )
    return _WIND_SCORE[climate_zone][direction]


# ─────────────────────────────────────────────────────────────────────────────
# § 4.1.3 — Road score (provenance-only; does NOT feed function_scores)
# ─────────────────────────────────────────────────────────────────────────────


def road_score(
    direction: PlotOrientation,
    plot_facing: PlotOrientation,
    secondary_road_direction: PlotOrientation | None = None,
) -> float:
    """Per-direction road score. Per SPEC v0.6 § 4.1.3 + § 14.14.

    Returns 1.0 if direction == plot_facing (primary road),
            0.5 if direction == secondary_road_direction (corner plot only),
            0.0 otherwise.

    NOTE: This is provenance-only. road_score does NOT contribute to
    function_scores — entry-on-road is enforced as a hard-constraint
    pruner at § 4.4 step 2 instead. See § 14.14 (v0.3 walk #2 amendment).
    """
    if direction == plot_facing:
        return 1.0
    if secondary_road_direction is not None and direction == secondary_road_direction:
        return 0.5
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# § 4.3 — Per-function lookup multipliers
# ─────────────────────────────────────────────────────────────────────────────


_SUN_FUNCTION_LOOKUP: Mapping[FunctionRole, float] = MappingProxyType({
    FunctionRole.LIVING:   1.0,
    FunctionRole.BEDROOM:  0.7,
    FunctionRole.KITCHEN:  0.6,
    FunctionRole.POOJA:    0.8,
    FunctionRole.WET_AREA: 0.3,
    FunctionRole.UTILITY:  0.3,
})


_WIND_FUNCTION_LOOKUP: Mapping[FunctionRole, float] = MappingProxyType({
    FunctionRole.LIVING:   0.9,
    FunctionRole.BEDROOM:  1.0,
    FunctionRole.KITCHEN:  0.6,
    FunctionRole.POOJA:    0.5,
    FunctionRole.WET_AREA: 0.4,
    FunctionRole.UTILITY:  0.3,
})


def sun_function_lookup(function: FunctionRole) -> float:
    """Per-function sun-affinity multiplier. Per SPEC v0.6 § 4.3."""
    return _SUN_FUNCTION_LOOKUP[function]


def wind_function_lookup(function: FunctionRole) -> float:
    """Per-function wind-affinity multiplier. Per SPEC v0.6 § 4.3 + § 14.11."""
    return _WIND_FUNCTION_LOOKUP[function]


# ─────────────────────────────────────────────────────────────────────────────
# § 4.2 — Signal weighting (per climate + Vastu tier)
# ─────────────────────────────────────────────────────────────────────────────


_VASTU_WEIGHT_BY_TIER: Mapping[VastuTier, float] = MappingProxyType({
    VastuTier.OFF:     0.0,
    VastuTier.PARTIAL: 0.4,
    VastuTier.FULL:    0.7,
})


def compute_weights(
    climate_zone: ClimateZone,
    vastu_tier: VastuTier,
) -> tuple[Mapping[str, float], Mapping[str, float]]:
    """Compute raw + applied (renormalized) signal weights. Per SPEC v0.6 § 4.2.

    Returns:
      (weights_raw, weights_applied) — both Mappings keyed by
      "sun" | "wind" | "vastu", both immutable.

      weights_raw   : per-signal weight pre-normalization (exposed for
                      interpretability / signal_dominance derivation).
      weights_applied: weights_raw renormalized to sum = 1.0 (used in
                      function_scores blending). If raw_total == 0.0,
                      applied is all zeros (defensive; should not happen
                      with valid v1 inputs).

    Raises:
      NotImplementedError (B-098) if climate_zone is not v1-supported.
      TypeError if vastu_tier is not a VastuTier instance.
    """
    if not isinstance(vastu_tier, VastuTier):
        raise TypeError(
            f"compute_weights: vastu_tier must be VastuTier; "
            f"got {type(vastu_tier).__name__}"
        )
    if climate_zone not in _WIND_SCORE:  # same supported set as wind table
        raise NotImplementedError(
            f"compute_weights: climate {climate_zone.value} not supported in v1; "
            f"B-098. Supported: {sorted(c.value for c in _WIND_SCORE)}."
        )

    sun_w = 1.0 if climate_zone in (ClimateZone.COMPOSITE, ClimateZone.TEMPERATE) else 0.7
    wind_w = 1.0 if climate_zone == ClimateZone.WARM_HUMID else 0.6
    vastu_w = _VASTU_WEIGHT_BY_TIER[vastu_tier]

    weights_raw = MappingProxyType({"sun": sun_w, "wind": wind_w, "vastu": vastu_w})
    raw_total = sum(weights_raw.values())
    if raw_total > 0:
        weights_applied = MappingProxyType({
            k: v / raw_total for k, v in weights_raw.items()
        })
    else:
        # Edge case: never happens in v1 valid inputs (sun + wind always > 0)
        weights_applied = MappingProxyType({"sun": 0.0, "wind": 0.0, "vastu": 0.0})

    return (weights_raw, weights_applied)


# ─────────────────────────────────────────────────────────────────────────────
# § 4.2 (v0.5) — Signal dominance derivation
# ─────────────────────────────────────────────────────────────────────────────


def compute_signal_dominance(
    weights_raw: Mapping[str, float],
) -> tuple[float, str | None]:
    """Compute (signal_dominance, dominant_signal) from raw weights.

    Per SPEC v0.6 § 4.2 + § 14.18.

    Returns:
      signal_dominance ∈ [0, 1] = max(weights_raw) / sum(weights_raw).
      dominant_signal: argmax key when dominance >= SIGNAL_DOMINANCE_THRESHOLD,
                       else None.

    Edge case: if all raw weights are zero, returns (0.0, None) defensively.
    """
    raw_total = sum(weights_raw.values())
    if raw_total <= 0.0:
        return (0.0, None)
    max_weight = max(weights_raw.values())
    dominance = max_weight / raw_total
    if dominance >= SIGNAL_DOMINANCE_THRESHOLD:
        # argmax — break ties by the canonical sun → wind → vastu order
        # (deterministic; matches insertion order of the Mapping)
        for k, v in weights_raw.items():
            if v == max_weight:
                return (dominance, k)
    return (dominance, None)


__all__ = [
    "sun_score",
    "wind_score",
    "road_score",
    "sun_function_lookup",
    "wind_function_lookup",
    "compute_weights",
    "compute_signal_dominance",
]

