"""C6 failure-mode tests — every NotImplementedError / TypeError / AssertionError path.

Per C6 SPEC v0.7 LOCKED § 6 + § 14.19. Reconstructed at S33 per B-127.

Coverage of § 6 failure-modes table:
  - Empty tuple → empty tuple (happy-path edge; covered in test_c6_select)
  - candidates not a tuple → TypeError
  - vastu_tier not VastuTier → TypeError
  - plot_analysis not PlotAnalysis → TypeError
  - shape != RECTANGULAR → NotImplementedError(B-066)
  - facing not in cardinals → NotImplementedError(B-107) — NEW v0.6
  - climate is HOT_DRY or COLD → NotImplementedError(B-098)
  - vastu_tier == FULL → deferred NotImplementedError(B-099) on first vastu lookup
  - All perms pruned → falls back to seed (rule_trace records the fallback)

Order-of-checks (per § 6 footnote): intercardinal-facing check fires
*before* climate/Vastu/permutation checks (Pattern A: fail at boundary).
"""
from __future__ import annotations

import dataclasses

import pytest

from buildemup.components.c04.schema import ClimateZone, PlotShape
from buildemup.components.c05 import select_topology
from buildemup.components.c06 import prioritize_orientation
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot
from buildemup.tests.validation._c6_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    make_plot_analysis,
    medium_brief,
    small_brief,
)


# ─── TypeError on bad candidates ─────────────────────────────────────────


def test_candidates_must_be_tuple():
    """list, not tuple → TypeError."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    with pytest.raises(TypeError, match=r"candidates must be a tuple"):
        prioritize_orientation([], pa, VastuTier.OFF)  # type: ignore


def test_candidates_must_be_tuple_not_none():
    """None → TypeError."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    with pytest.raises(TypeError):
        prioritize_orientation(None, pa, VastuTier.OFF)  # type: ignore


# ─── TypeError on bad vastu_tier ─────────────────────────────────────────


def test_vastu_tier_must_be_vastu_tier_enum():
    """String not VastuTier → TypeError."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    with pytest.raises(TypeError, match=r"vastu_tier must be VastuTier"):
        prioritize_orientation(cands, pa, "OFF")  # type: ignore


def test_vastu_tier_must_be_vastu_tier_not_int():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    with pytest.raises(TypeError, match=r"vastu_tier must be VastuTier"):
        prioritize_orientation(cands, pa, 0)  # type: ignore


def test_vastu_tier_check_fires_even_on_empty_input():
    """Empty input still validates vastu_tier type."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    with pytest.raises(TypeError, match=r"vastu_tier must be VastuTier"):
        prioritize_orientation((), pa, "OFF")  # type: ignore


# ─── TypeError on bad plot_analysis ──────────────────────────────────────


def test_plot_analysis_must_be_plot_analysis():
    """Random dict → TypeError."""
    cands = select_topology(make_plot_analysis(bangalore_40x60()), medium_brief())
    with pytest.raises(TypeError, match=r"plot_analysis must be PlotAnalysis"):
        prioritize_orientation(cands, {"plot": "junk"}, VastuTier.OFF)  # type: ignore


def test_plot_analysis_check_fires_even_on_empty_input():
    """Empty input still validates plot_analysis type."""
    with pytest.raises(TypeError, match=r"plot_analysis must be PlotAnalysis"):
        prioritize_orientation((), "not_a_plot_analysis", VastuTier.OFF)  # type: ignore


# ─── B-066: non-RECTANGULAR shape ────────────────────────────────────────


def test_non_rectangular_shape_raises_b066():
    """L_SHAPED plot raises NotImplementedError mentioning B-066."""
    plot = bangalore_40x60()
    pa_real = make_plot_analysis(plot)
    pa_lshaped = dataclasses.replace(pa_real, shape=PlotShape.L_SHAPED)
    cands = select_topology(pa_real, medium_brief())  # use real pa for C5
    with pytest.raises(NotImplementedError, match=r"B-066"):
        prioritize_orientation(cands, pa_lshaped, VastuTier.OFF)


def test_irregular_shape_raises_b066():
    """IRREGULAR plot also raises NotImplementedError(B-066)."""
    plot = bangalore_40x60()
    pa_real = make_plot_analysis(plot)
    pa_irregular = dataclasses.replace(pa_real, shape=PlotShape.IRREGULAR)
    cands = select_topology(pa_real, medium_brief())
    with pytest.raises(NotImplementedError, match=r"B-066"):
        prioritize_orientation(cands, pa_irregular, VastuTier.OFF)


def test_non_rectangular_message_mentions_v1_constraint():
    """Error message names the v1 constraint."""
    plot = bangalore_40x60()
    pa_real = make_plot_analysis(plot)
    pa_lshaped = dataclasses.replace(pa_real, shape=PlotShape.L_SHAPED)
    cands = select_topology(pa_real, medium_brief())
    with pytest.raises(NotImplementedError, match=r"v1 supports RECTANGULAR only"):
        prioritize_orientation(cands, pa_lshaped, VastuTier.OFF)


# ─── B-107: intercardinal facing rejection (NEW v0.6) ────────────────────


@pytest.mark.parametrize("intercardinal", [
    PlotOrientation.NORTHEAST,
    PlotOrientation.SOUTHEAST,
    PlotOrientation.SOUTHWEST,
    PlotOrientation.NORTHWEST,
])
def test_intercardinal_facing_raises_b107(intercardinal):
    """All four intercardinals raise NotImplementedError(B-107)."""
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=intercardinal,
        city="bangalore", road_width_m=9.0, corner_plot=False,
    )
    pa = make_plot_analysis(plot)
    # C5 may also raise on intercardinal; build a dummy candidate tuple with
    # a real cardinal-facing plot so we can isolate C6's B-107 check.
    cardinal_plot = bangalore_40x60()
    cardinal_pa = make_plot_analysis(cardinal_plot)
    cands = select_topology(cardinal_pa, medium_brief())
    with pytest.raises(NotImplementedError, match=r"B-107"):
        prioritize_orientation(cands, pa, VastuTier.OFF)


def test_intercardinal_facing_message_mentions_cardinal_only():
    """Error message clearly says cardinal-only."""
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.NORTHEAST,
        city="bangalore", road_width_m=9.0, corner_plot=False,
    )
    pa = make_plot_analysis(plot)
    cardinal_plot = bangalore_40x60()
    cardinal_pa = make_plot_analysis(cardinal_plot)
    cands = select_topology(cardinal_pa, medium_brief())
    with pytest.raises(NotImplementedError, match=r"cardinal facing only"):
        prioritize_orientation(cands, pa, VastuTier.OFF)


def test_intercardinal_facing_check_fires_before_climate_check():
    """Order-of-checks: intercardinal raises before climate check.

    Constructed scenario: intercardinal facing AND HOT_DRY climate would each
    raise. We assert B-107 fires (not B-098), proving the ordering.
    """
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.NORTHEAST,
        city="bangalore", road_width_m=9.0, corner_plot=False,
    )
    pa_real = make_plot_analysis(plot)
    # Override climate to HOT_DRY too — both errors are present
    pa_hot_dry_intercardinal = dataclasses.replace(pa_real, climate_zone=ClimateZone.HOT_DRY)
    cardinal_plot = bangalore_40x60()
    cardinal_pa = make_plot_analysis(cardinal_plot)
    cands = select_topology(cardinal_pa, medium_brief())
    # § 6 ordering: facing check fires BEFORE climate check; B-107 wins
    with pytest.raises(NotImplementedError, match=r"B-107"):
        prioritize_orientation(cands, pa_hot_dry_intercardinal, VastuTier.OFF)


@pytest.mark.parametrize("cardinal", [
    PlotOrientation.NORTH,
    PlotOrientation.EAST,
    PlotOrientation.SOUTH,
    PlotOrientation.WEST,
])
def test_cardinal_facing_works_end_to_end(cardinal):
    """Mirror of B-107 rejection: all 4 cardinals succeed."""
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=cardinal,
        city="bangalore", road_width_m=9.0, corner_plot=False,
    )
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert len(out) >= 1


# ─── B-098: HOT_DRY / COLD climate rejection ─────────────────────────────


def test_hot_dry_climate_raises_b098():
    """HOT_DRY climate raises NotImplementedError(B-098)."""
    plot = bangalore_40x60()
    pa_real = make_plot_analysis(plot)
    pa_hot_dry = dataclasses.replace(pa_real, climate_zone=ClimateZone.HOT_DRY)
    cands = select_topology(pa_real, medium_brief())
    with pytest.raises(NotImplementedError, match=r"B-098"):
        prioritize_orientation(cands, pa_hot_dry, VastuTier.OFF)


def test_cold_climate_raises_b098():
    """COLD climate raises NotImplementedError(B-098)."""
    plot = bangalore_40x60()
    pa_real = make_plot_analysis(plot)
    pa_cold = dataclasses.replace(pa_real, climate_zone=ClimateZone.COLD)
    cands = select_topology(pa_real, medium_brief())
    with pytest.raises(NotImplementedError, match=r"B-098"):
        prioritize_orientation(cands, pa_cold, VastuTier.OFF)


def test_hot_dry_message_lists_supported_climates():
    """Error message lists v1-supported climates."""
    plot = bangalore_40x60()
    pa_real = make_plot_analysis(plot)
    pa_hot_dry = dataclasses.replace(pa_real, climate_zone=ClimateZone.HOT_DRY)
    cands = select_topology(pa_real, medium_brief())
    with pytest.raises(NotImplementedError, match=r"warm_humid|composite|temperate"):
        prioritize_orientation(cands, pa_hot_dry, VastuTier.OFF)


# ─── B-099: FULL Vastu tier deferred fail ────────────────────────────────


def test_full_vastu_tier_raises_b099_at_first_vastu_lookup():
    """FULL tier defers; raises during compute_function_scores → vastu_score_4dir."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    with pytest.raises(NotImplementedError, match=r"B-099"):
        prioritize_orientation(cands, pa, VastuTier.FULL)


def test_full_vastu_message_mentions_kb_unavailable():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    with pytest.raises(NotImplementedError, match=r"vastu_engine"):
        prioritize_orientation(cands, pa, VastuTier.FULL)


def test_off_tier_does_not_raise_b099():
    """OFF tier never invokes vastu_score; no B-099 raise."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    # No raise; non-empty output
    assert len(out) >= 1


def test_partial_tier_does_not_raise_b099():
    """PARTIAL tier reads from VASTU_TABLE_PARTIAL; no B-099 raise."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.PARTIAL)
    assert len(out) >= 1


# ─── Order-of-checks: intercardinal before climate, climate before vastu ─


def test_b066_fires_before_b107():
    """Non-RECTANGULAR + intercardinal: B-066 wins (shape checked first)."""
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.NORTHEAST,
        city="bangalore", road_width_m=9.0, corner_plot=False,
    )
    pa_real = make_plot_analysis(plot)
    pa_lshaped_intercardinal = dataclasses.replace(pa_real, shape=PlotShape.L_SHAPED)
    cardinal_plot = bangalore_40x60()
    cardinal_pa = make_plot_analysis(cardinal_plot)
    cands = select_topology(cardinal_pa, medium_brief())
    with pytest.raises(NotImplementedError, match=r"B-066"):
        prioritize_orientation(cands, pa_lshaped_intercardinal, VastuTier.OFF)


def test_b107_fires_before_b098():
    """Intercardinal + HOT_DRY: B-107 wins (facing checked before climate)."""
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.NORTHEAST,
        city="bangalore", road_width_m=9.0, corner_plot=False,
    )
    pa_real = make_plot_analysis(plot)
    pa_combined = dataclasses.replace(pa_real, climate_zone=ClimateZone.HOT_DRY)
    cardinal_plot = bangalore_40x60()
    cardinal_pa = make_plot_analysis(cardinal_plot)
    cands = select_topology(cardinal_pa, medium_brief())
    with pytest.raises(NotImplementedError, match=r"B-107"):
        prioritize_orientation(cands, pa_combined, VastuTier.OFF)


def test_b098_fires_before_b099():
    """HOT_DRY + FULL Vastu: B-098 wins (climate checked before any vastu lookup)."""
    plot = bangalore_40x60()
    pa_real = make_plot_analysis(plot)
    pa_hot_dry = dataclasses.replace(pa_real, climate_zone=ClimateZone.HOT_DRY)
    cands = select_topology(pa_real, medium_brief())
    with pytest.raises(NotImplementedError, match=r"B-098"):
        prioritize_orientation(cands, pa_hot_dry, VastuTier.FULL)
