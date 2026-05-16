"""B-109 (S55): CorridorTooNarrow graceful fallback via design_corridors_safe.

The strict `design_corridors` raises `CorridorTooNarrowError` on the
first candidate that doesn't fit a regulatory-min-width corridor. The
new `design_corridors_safe` wrapper catches that per-candidate error
and returns a `NarrowPlotRecommendation` in its place — keeping siblings
in the result so the caller can surface a structured guidance to the
user instead of aborting the whole batch.
"""
from __future__ import annotations

import pytest

from buildemup.components.c04.schema import PlotShape
from buildemup.components.c08 import (
    CorridorDesignConfig,
    CorridorDesignedCandidate,
    CorridorTooNarrowError,
    NarrowPlotRecommendation,
    design_corridors,
    design_corridors_safe,
)
from buildemup.components.c08.corridor_designer import (
    _build_narrow_plot_recommendation,
)
from buildemup.tests.validation._c8_fixtures import real_pipeline


# ─────────────────────────────────────────────────────────────────────
# Schema — NarrowPlotRecommendation exists with the expected shape
# ─────────────────────────────────────────────────────────────────────

def test_narrow_plot_recommendation_has_expected_fields():
    rec = NarrowPlotRecommendation(
        candidate_index=0,
        message="too narrow",
        bay_min_m=1.0,
        regulatory_min_width_m=0.9,
        candidate_widths_m=(0.5, 0.6),
        suggested_alternative_topologies=("STRIP",),
        suggested_user_action="switch_to_strip",
    )
    assert rec.candidate_index == 0
    assert rec.message == "too narrow"
    assert rec.bay_min_m == 1.0
    assert rec.regulatory_min_width_m == 0.9
    assert rec.candidate_widths_m == (0.5, 0.6)
    assert rec.suggested_alternative_topologies == ("STRIP",)
    assert rec.suggested_user_action == "switch_to_strip"


def test_narrow_plot_recommendation_is_frozen():
    """Recommendation is immutable like every other C8 dataclass."""
    rec = NarrowPlotRecommendation(candidate_index=0, message="x")
    with pytest.raises((AttributeError, Exception)):
        rec.candidate_index = 5  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────
# _build_narrow_plot_recommendation — error → recommendation mapping
# ─────────────────────────────────────────────────────────────────────

def test_build_recommendation_carries_error_diagnostic_fields():
    err = CorridorTooNarrowError(
        "no fit",
        bay_min_m=1.0,
        regulatory_min_width_m=0.9,
        candidate_widths_m=(0.5, 0.6, 0.7),
    )
    oriented, _, _ = real_pipeline()
    rec = _build_narrow_plot_recommendation(err, oriented[0], candidate_index=2)
    assert rec.candidate_index == 2
    assert rec.message == "no fit"
    assert rec.bay_min_m == 1.0
    assert rec.regulatory_min_width_m == 0.9
    assert rec.candidate_widths_m == (0.5, 0.6, 0.7)
    # Default suggestion is at least STRIP for any unknown topology kind
    assert "STRIP" in rec.suggested_alternative_topologies


# ─────────────────────────────────────────────────────────────────────
# Integration — happy path (no narrow candidates)
# ─────────────────────────────────────────────────────────────────────

def test_safe_returns_designed_candidates_on_happy_path():
    """When every candidate fits a normal corridor, safe returns the
    same CorridorDesignedCandidate tuple as strict design_corridors."""
    oriented, pa, grid = real_pipeline()
    safe_results = design_corridors_safe(oriented, grid, pa)
    strict_results = design_corridors(oriented, grid, pa)
    assert len(safe_results) == len(strict_results)
    for r in safe_results:
        assert isinstance(r, CorridorDesignedCandidate)


def test_safe_position_paired_with_input():
    """Length of result equals length of input (position-paired contract)."""
    oriented, pa, grid = real_pipeline()
    safe_results = design_corridors_safe(oriented, grid, pa)
    assert len(safe_results) == len(oriented)


# ─────────────────────────────────────────────────────────────────────
# Integration — narrow path (regulatory_min_width above plausibility)
# ─────────────────────────────────────────────────────────────────────

def test_safe_returns_recommendation_when_regulatory_min_impossible():
    """When config sets an impossible regulatory_min_width_m, every
    candidate should be substituted by a NarrowPlotRecommendation rather
    than aborting the batch."""
    oriented, pa, grid = real_pipeline()
    impossible_cfg = CorridorDesignConfig(
        regulatory_min_width_m=99.0,
        comfort_target_width_m=99.0,  # honor the post-init invariant
    )
    safe_results = design_corridors_safe(
        oriented, grid, pa, config=impossible_cfg,
    )
    assert len(safe_results) == len(oriented)
    for r in safe_results:
        assert isinstance(r, NarrowPlotRecommendation)


def test_safe_recommendation_carries_position_index():
    """Each NarrowPlotRecommendation must carry the input index it
    replaces, so the caller can match it back to oriented[i]."""
    oriented, pa, grid = real_pipeline()
    impossible_cfg = CorridorDesignConfig(
        regulatory_min_width_m=99.0, comfort_target_width_m=99.0,
    )
    safe_results = design_corridors_safe(
        oriented, grid, pa, config=impossible_cfg,
    )
    for i, r in enumerate(safe_results):
        assert isinstance(r, NarrowPlotRecommendation)
        assert r.candidate_index == i


def test_strict_design_corridors_still_raises_on_narrow_plot():
    """Backwards compat: strict path must still raise — callers depending
    on raise behavior keep working unchanged."""
    oriented, pa, grid = real_pipeline()
    impossible_cfg = CorridorDesignConfig(
        regulatory_min_width_m=99.0, comfort_target_width_m=99.0,
    )
    with pytest.raises(CorridorTooNarrowError):
        design_corridors(oriented, grid, pa, config=impossible_cfg)


# ─────────────────────────────────────────────────────────────────────
# Input validation — mirrors design_corridors strict path
# ─────────────────────────────────────────────────────────────────────

def test_safe_rejects_non_grid():
    oriented, pa, _ = real_pipeline()
    with pytest.raises(TypeError, match="grid"):
        design_corridors_safe(oriented, "not a grid", pa)  # type: ignore[arg-type]


def test_safe_rejects_non_plot_analysis():
    oriented, _, grid = real_pipeline()
    with pytest.raises(TypeError, match="plot_analysis"):
        design_corridors_safe(oriented, grid, "not a PA")  # type: ignore[arg-type]


def test_safe_rejects_non_rectangular_plot():
    """B-066 still applies: only PlotShape.RECTANGULAR supported."""
    from dataclasses import replace
    oriented, pa, grid = real_pipeline()
    bad_pa = replace(pa, shape=PlotShape.L_SHAPED)
    with pytest.raises(NotImplementedError, match="RECTANGULAR"):
        design_corridors_safe(oriented, grid, bad_pa)


def test_safe_empty_input_returns_empty():
    _, pa, grid = real_pipeline()
    assert design_corridors_safe((), grid, pa) == ()
