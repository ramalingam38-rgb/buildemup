"""C6 signals tests — sun/wind/road scores, weighting, dominance.

Per C6 SPEC v0.7 LOCKED §§ 4.1.1–4.1.3, 4.2, 4.3 + § 14.18. Reconstructed at S33 per B-127.

Coverage:
  - sun_score: cardinal-only contract; ordering N>E>S>W per spec table.
  - wind_score: 3 supported climates × 4 cardinals; HOT_DRY/COLD raise B-098.
  - road_score: primary=1.0, secondary=0.5, other=0.0; corner-plot semantics.
  - sun_function_lookup, wind_function_lookup: per-function multipliers.
  - compute_weights: climate × tier matrix; sum-normalized weights_applied.
  - compute_signal_dominance: max/sum, threshold gating, defensive zero case.
"""
from __future__ import annotations

import pytest

from buildemup.components.c04.schema import ClimateZone
from buildemup.components.c06 import (
    FunctionRole,
    SIGNAL_DOMINANCE_THRESHOLD,
)
from buildemup.components.c06.signals import (
    compute_signal_dominance,
    compute_weights,
    road_score,
    sun_function_lookup,
    sun_score,
    wind_function_lookup,
    wind_score,
)
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─── sun_score ────────────────────────────────────────────────────────────


def test_sun_score_north_high():
    """NORTH = 0.95 per § 4.1.1."""
    assert sun_score(PlotOrientation.NORTH) == 0.95


def test_sun_score_east_strong():
    """EAST = 0.85."""
    assert sun_score(PlotOrientation.EAST) == 0.85


def test_sun_score_south_moderate():
    """SOUTH = 0.55."""
    assert sun_score(PlotOrientation.SOUTH) == 0.55


def test_sun_score_west_low():
    """WEST = 0.20 (afternoon glare penalty)."""
    assert sun_score(PlotOrientation.WEST) == 0.20


def test_sun_score_ordering_n_east_south_west():
    """Sanity: N > E > S > W."""
    assert sun_score(PlotOrientation.NORTH) > sun_score(PlotOrientation.EAST)
    assert sun_score(PlotOrientation.EAST) > sun_score(PlotOrientation.SOUTH)
    assert sun_score(PlotOrientation.SOUTH) > sun_score(PlotOrientation.WEST)


@pytest.mark.parametrize("intercardinal", [
    PlotOrientation.NORTHEAST, PlotOrientation.SOUTHEAST,
    PlotOrientation.SOUTHWEST, PlotOrientation.NORTHWEST,
])
def test_sun_score_rejects_intercardinal(intercardinal):
    """Cardinal-only contract; intercardinal would be a caller bug."""
    with pytest.raises(ValueError, match=r"cardinal direction"):
        sun_score(intercardinal)


# ─── wind_score ───────────────────────────────────────────────────────────


def test_wind_score_warm_humid_south_high():
    """WARM_HUMID climate: S/SW monsoon flow → SOUTH = 0.9."""
    assert wind_score(PlotOrientation.SOUTH, ClimateZone.WARM_HUMID) == 0.9


def test_wind_score_warm_humid_west_high():
    """WARM_HUMID: WEST also captures monsoon = 0.85."""
    assert wind_score(PlotOrientation.WEST, ClimateZone.WARM_HUMID) == 0.85


def test_wind_score_warm_humid_north_lower():
    """WARM_HUMID: NORTH less favored = 0.6."""
    assert wind_score(PlotOrientation.NORTH, ClimateZone.WARM_HUMID) == 0.6


def test_wind_score_composite_north_high():
    """COMPOSITE: NORTH preferred = 0.7."""
    assert wind_score(PlotOrientation.NORTH, ClimateZone.COMPOSITE) == 0.7


def test_wind_score_composite_south_low():
    """COMPOSITE: SOUTH less optimal = 0.5."""
    assert wind_score(PlotOrientation.SOUTH, ClimateZone.COMPOSITE) == 0.5


def test_wind_score_temperate_uniform():
    """TEMPERATE: uniform 0.7 across all cardinals."""
    for d in [PlotOrientation.NORTH, PlotOrientation.EAST,
              PlotOrientation.SOUTH, PlotOrientation.WEST]:
        assert wind_score(d, ClimateZone.TEMPERATE) == 0.7


def test_wind_score_rejects_hot_dry_climate():
    """HOT_DRY raises NotImplementedError (B-098)."""
    with pytest.raises(NotImplementedError, match=r"B-098"):
        wind_score(PlotOrientation.NORTH, ClimateZone.HOT_DRY)


def test_wind_score_rejects_cold_climate():
    """COLD raises NotImplementedError (B-098)."""
    with pytest.raises(NotImplementedError, match=r"B-098"):
        wind_score(PlotOrientation.NORTH, ClimateZone.COLD)


@pytest.mark.parametrize("intercardinal", [
    PlotOrientation.NORTHEAST, PlotOrientation.SOUTHEAST,
    PlotOrientation.SOUTHWEST, PlotOrientation.NORTHWEST,
])
def test_wind_score_rejects_intercardinal(intercardinal):
    with pytest.raises(ValueError, match=r"cardinal direction"):
        wind_score(intercardinal, ClimateZone.WARM_HUMID)


# ─── road_score ───────────────────────────────────────────────────────────


def test_road_score_primary_facing_one():
    """direction == plot_facing → 1.0 (primary road)."""
    assert road_score(
        direction=PlotOrientation.EAST,
        plot_facing=PlotOrientation.EAST,
    ) == 1.0


def test_road_score_secondary_returns_half():
    """direction == secondary_road_direction → 0.5 (corner plot)."""
    assert road_score(
        direction=PlotOrientation.NORTH,
        plot_facing=PlotOrientation.EAST,
        secondary_road_direction=PlotOrientation.NORTH,
    ) == 0.5


def test_road_score_other_directions_zero():
    """direction not on a road → 0.0."""
    assert road_score(
        direction=PlotOrientation.WEST,
        plot_facing=PlotOrientation.EAST,
    ) == 0.0


def test_road_score_no_secondary_means_only_primary():
    """When secondary is None, only primary returns non-zero."""
    rs_north = road_score(
        direction=PlotOrientation.NORTH,
        plot_facing=PlotOrientation.EAST,
        secondary_road_direction=None,
    )
    assert rs_north == 0.0


def test_road_score_primary_takes_precedence_over_secondary():
    """If direction == both plot_facing and secondary, primary wins."""
    # Defensive case (input data inconsistency); test current behaviour.
    rs = road_score(
        direction=PlotOrientation.EAST,
        plot_facing=PlotOrientation.EAST,
        secondary_road_direction=PlotOrientation.EAST,
    )
    assert rs == 1.0


# ─── sun_function_lookup ──────────────────────────────────────────────────


def test_sun_function_lookup_living_max():
    """LIVING benefits most from sun = 1.0."""
    assert sun_function_lookup(FunctionRole.LIVING) == 1.0


def test_sun_function_lookup_pooja_high():
    """POOJA traditionally gets light = 0.8."""
    assert sun_function_lookup(FunctionRole.POOJA) == 0.8


def test_sun_function_lookup_wet_area_low():
    """WET_AREA needs little sun = 0.3."""
    assert sun_function_lookup(FunctionRole.WET_AREA) == 0.3


def test_sun_function_lookup_utility_low():
    """UTILITY needs little sun = 0.3."""
    assert sun_function_lookup(FunctionRole.UTILITY) == 0.3


def test_sun_function_lookup_covers_all_six_roles():
    """Defensive: every role in [0, 1]."""
    for f in FunctionRole:
        v = sun_function_lookup(f)
        assert 0.0 <= v <= 1.0


# ─── wind_function_lookup ─────────────────────────────────────────────────


def test_wind_function_lookup_bedroom_max():
    """BEDROOM benefits most from wind = 1.0."""
    assert wind_function_lookup(FunctionRole.BEDROOM) == 1.0


def test_wind_function_lookup_living_high():
    """LIVING also benefits = 0.9."""
    assert wind_function_lookup(FunctionRole.LIVING) == 0.9


def test_wind_function_lookup_pooja_moderate():
    """POOJA moderate = 0.5."""
    assert wind_function_lookup(FunctionRole.POOJA) == 0.5


def test_wind_function_lookup_utility_low():
    """UTILITY = 0.3."""
    assert wind_function_lookup(FunctionRole.UTILITY) == 0.3


def test_wind_function_lookup_covers_all_six_roles():
    for f in FunctionRole:
        v = wind_function_lookup(f)
        assert 0.0 <= v <= 1.0


# ─── compute_weights ──────────────────────────────────────────────────────


def test_compute_weights_off_tier_warm_humid():
    """OFF tier: vastu = 0; warm humid → wind dominates."""
    raw, applied = compute_weights(ClimateZone.WARM_HUMID, VastuTier.OFF)
    assert raw == {"sun": 0.7, "wind": 1.0, "vastu": 0.0}
    # applied normalizes raw to sum 1.0
    assert applied["sun"] == pytest.approx(0.7 / 1.7)
    assert applied["wind"] == pytest.approx(1.0 / 1.7)
    assert applied["vastu"] == 0.0


def test_compute_weights_off_tier_composite():
    """OFF tier: composite → sun w=1.0, wind w=0.6 (sun dominates)."""
    raw, applied = compute_weights(ClimateZone.COMPOSITE, VastuTier.OFF)
    assert raw == {"sun": 1.0, "wind": 0.6, "vastu": 0.0}


def test_compute_weights_off_tier_temperate():
    """OFF tier: temperate → sun w=1.0, wind w=0.6."""
    raw, _ = compute_weights(ClimateZone.TEMPERATE, VastuTier.OFF)
    assert raw == {"sun": 1.0, "wind": 0.6, "vastu": 0.0}


def test_compute_weights_partial_tier_adds_vastu():
    """PARTIAL tier: vastu = 0.4."""
    raw, _ = compute_weights(ClimateZone.COMPOSITE, VastuTier.PARTIAL)
    assert raw["vastu"] == 0.4


def test_compute_weights_full_tier_higher_vastu():
    """FULL tier: vastu = 0.7 (heavier weight per § 4.2)."""
    raw, _ = compute_weights(ClimateZone.COMPOSITE, VastuTier.FULL)
    assert raw["vastu"] == 0.7


def test_compute_weights_applied_sums_to_one():
    """Normalized applied weights always sum to 1.0 (when raw sum > 0)."""
    for climate in [ClimateZone.WARM_HUMID, ClimateZone.COMPOSITE, ClimateZone.TEMPERATE]:
        for tier in [VastuTier.OFF, VastuTier.PARTIAL, VastuTier.FULL]:
            _, applied = compute_weights(climate, tier)
            assert sum(applied.values()) == pytest.approx(1.0)


def test_compute_weights_raw_immutable():
    """raw is MappingProxyType — assignment raises."""
    raw, _ = compute_weights(ClimateZone.COMPOSITE, VastuTier.OFF)
    with pytest.raises(TypeError):
        raw["sun"] = 0.0  # type: ignore


def test_compute_weights_applied_immutable():
    _, applied = compute_weights(ClimateZone.COMPOSITE, VastuTier.OFF)
    with pytest.raises(TypeError):
        applied["sun"] = 0.0  # type: ignore


def test_compute_weights_rejects_hot_dry():
    with pytest.raises(NotImplementedError, match=r"B-098"):
        compute_weights(ClimateZone.HOT_DRY, VastuTier.OFF)


def test_compute_weights_rejects_cold():
    with pytest.raises(NotImplementedError, match=r"B-098"):
        compute_weights(ClimateZone.COLD, VastuTier.OFF)


def test_compute_weights_rejects_non_vastu_tier():
    with pytest.raises(TypeError, match=r"vastu_tier must be VastuTier"):
        compute_weights(ClimateZone.COMPOSITE, "OFF")  # type: ignore


# ─── compute_signal_dominance ─────────────────────────────────────────────


def test_signal_dominance_off_composite():
    """OFF in COMPOSITE: weights raw = (1.0, 0.6, 0.0). Dominance=1/1.6=0.625, sun."""
    dom, name = compute_signal_dominance({"sun": 1.0, "wind": 0.6, "vastu": 0.0})
    assert dom == pytest.approx(0.625)
    assert name == "sun"


def test_signal_dominance_off_warm_humid():
    """OFF in WARM_HUMID: weights = (0.7, 1.0, 0.0). Dominance=1.0/1.7≈0.588, wind."""
    dom, name = compute_signal_dominance({"sun": 0.7, "wind": 1.0, "vastu": 0.0})
    assert dom == pytest.approx(1.0 / 1.7)
    assert name == "wind"


def test_signal_dominance_partial_temperate_sun():
    """PARTIAL in TEMPERATE: weights = (1.0, 0.6, 0.4). Dom=1.0/2.0=0.5, sun."""
    dom, name = compute_signal_dominance({"sun": 1.0, "wind": 0.6, "vastu": 0.4})
    assert dom == 0.5
    assert name == "sun"


def test_signal_dominance_full_warm_humid_balanced():
    """FULL in WARM_HUMID: weights = (0.7, 1.0, 0.7). Dom=1.0/2.4≈0.417, BELOW threshold → None."""
    dom, name = compute_signal_dominance({"sun": 0.7, "wind": 1.0, "vastu": 0.7})
    assert dom == pytest.approx(1.0 / 2.4)
    assert dom < SIGNAL_DOMINANCE_THRESHOLD
    assert name is None


def test_signal_dominance_above_threshold_named():
    """Just above threshold → dominant_signal named."""
    # Dominance = 0.5, above threshold 0.45
    dom, name = compute_signal_dominance({"sun": 0.5, "wind": 0.3, "vastu": 0.2})
    assert dom == 0.5
    assert name == "sun"


def test_signal_dominance_at_threshold_boundary_inclusive():
    """At exactly 0.45 boundary → dominant_signal named (>= comparison)."""
    # Construct so max/sum == 0.45 exactly
    # weights {"sun": 0.45, "wind": 0.55, "vastu": 0.0}; sum=1.0, max/sum=0.55 NOT 0.45
    # Instead {"sun": 0.45, "wind": 0.30, "vastu": 0.25}; sum=1.0, max/sum=0.45 ✓
    dom, name = compute_signal_dominance({"sun": 0.45, "wind": 0.30, "vastu": 0.25})
    assert dom == pytest.approx(0.45)
    assert name == "sun"


def test_signal_dominance_zero_weights_defensive():
    """All-zero raw weights returns (0.0, None) without raising."""
    dom, name = compute_signal_dominance({"sun": 0.0, "wind": 0.0, "vastu": 0.0})
    assert dom == 0.0
    assert name is None


def test_signal_dominance_argmax_ties_pick_canonical_order():
    """Tie: returns first max-key in canonical sun → wind → vastu order."""
    # All equal: sum=3.0, each=1.0, dom=1/3=0.333; below threshold → None
    dom, name = compute_signal_dominance({"sun": 1.0, "wind": 1.0, "vastu": 1.0})
    # Below threshold, returns None regardless
    assert name is None
    assert dom == pytest.approx(1.0 / 3.0)


def test_signal_dominance_2way_tie_above_threshold_picks_first():
    """Two-way tie above threshold: picks 'sun' (first in canonical order)."""
    # weights: sun=1.0, wind=1.0, vastu=0.1. sum=2.1; max=1.0; dom=1.0/2.1≈0.476 > 0.45
    dom, name = compute_signal_dominance({"sun": 1.0, "wind": 1.0, "vastu": 0.1})
    assert dom > SIGNAL_DOMINANCE_THRESHOLD
    assert name == "sun"


def test_signal_dominance_full_dominance_one():
    """Single non-zero weight → dominance == 1.0."""
    dom, name = compute_signal_dominance({"sun": 1.0, "wind": 0.0, "vastu": 0.0})
    assert dom == 1.0
    assert name == "sun"
