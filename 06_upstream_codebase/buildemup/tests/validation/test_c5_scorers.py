"""Validation tests for C5 per-criterion scorers + weight machinery.

Per C5 SPEC v0.9 LOCKED § 14 (cumulative).
"""
from __future__ import annotations

import pytest

from buildemup.components.c04.schema import PlotTier
from buildemup.components.c05.scorers import (
    BASE_WEIGHTS,
    TOPOLOGY_MIN_BEDROOMS,
    _topology_base_bedroom_fit,
    compute_raw_scores,
    effective_weights,
    score_aspect_ratio_fit,
    score_bedroom_fit,
    score_climate_fit,
    score_corner_fit,
    score_corridor_overhead,
    score_open_side_count,
    score_width_fit,
)
from buildemup.components.c05.schema import TopologyKind
from buildemup.tests.validation._c5_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    large_brief,
    make_floor_brief,
    make_plot_analysis,
    medium_brief,
    pune_30x40,
    small_brief,
)


# ─── Base weights ─────────────────────────────────────────────────────────


def test_base_weights_sum_to_one():
    """v0.2 § 4.2 + D4 pushback: base weights sum to exactly 1.0."""
    assert abs(sum(BASE_WEIGHTS.values()) - 1.0) < 1e-9


def test_base_weights_immutable():
    with pytest.raises(TypeError):
        BASE_WEIGHTS["new_criterion"] = 0.1                        # type: ignore[index]


# ─── Effective weights (context multipliers) ─────────────────────────────


def test_effective_weights_sum_to_one_default_context():
    """Default context (non-corner, T2) — multipliers all 1.0; sum=1.0."""
    pa = make_plot_analysis(bangalore_40x60())     # T2, non-corner
    weights = effective_weights(pa)
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_effective_weights_sum_to_one_corner_context():
    from buildemup.domain.envelope import PlotOrientation
    from buildemup.domain.plot import Plot
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.EAST,
        city="bangalore", road_width_m=12.0, corner_plot=True,
        second_road_width_m=8.0,
    )
    pa = make_plot_analysis(plot)
    weights = effective_weights(pa)
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_effective_weights_sum_to_one_t3_context():
    pa = make_plot_analysis(delhi_60x90())         # T3
    weights = effective_weights(pa)
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_effective_weights_sum_to_one_t1_context():
    pa = make_plot_analysis(chennai_30x40())       # T1
    weights = effective_weights(pa)
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_max_normalized_weight_under_0_35():
    """v0.4 § 14.5 invariant: no single weight > 0.35 in any context."""
    from buildemup.domain.envelope import PlotOrientation
    from buildemup.domain.plot import Plot
    test_plots = [
        bangalore_40x60(),                         # T2 non-corner
        delhi_60x90(),                             # T3 non-corner
        chennai_30x40(),                           # T1 non-corner
        Plot(
            width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTH,
            city="chennai", road_width_m=9.0, corner_plot=True,
            second_road_width_m=8.0,
        ),                                         # T1 corner
        Plot(
            width_m=12.192, depth_m=18.288, facing=PlotOrientation.EAST,
            city="bangalore", road_width_m=12.0, corner_plot=True,
            second_road_width_m=8.0,
        ),                                         # T2 corner
    ]
    for plot in test_plots:
        pa = make_plot_analysis(plot)
        weights = effective_weights(pa)
        max_w = max(weights.values())
        assert max_w <= 0.35, (
            f"max weight {max_w:.4f} exceeds 0.35 ceiling; weights={dict(weights)}"
        )


# ─── Per-criterion scorer range invariants ────────────────────────────────


def test_each_criterion_in_zero_to_one_range():
    """Every scorer for every topology returns a value in [0, 1]."""
    pa = make_plot_analysis(bangalore_40x60())
    for kind in TopologyKind:
        raw = compute_raw_scores(kind, pa, medium_brief())
        for crit, value in raw.items():
            assert 0.0 <= value <= 1.0, f"{kind.value}/{crit}={value}"


# ─── corner_fit ───────────────────────────────────────────────────────────


def test_corner_fit_zero_for_l_shape_on_non_corner():
    pa = make_plot_analysis(bangalore_40x60())     # non-corner
    assert score_corner_fit(TopologyKind.L_SHAPE, pa) == 0.0


def test_corner_fit_high_for_l_shape_on_corner():
    from buildemup.domain.envelope import PlotOrientation
    from buildemup.domain.plot import Plot
    plot = Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0, corner_plot=True,
        second_road_width_m=8.0,
    )
    pa = make_plot_analysis(plot)
    assert score_corner_fit(TopologyKind.L_SHAPE, pa) == 1.0


# ─── climate_fit ──────────────────────────────────────────────────────────


def test_climate_fit_warm_humid_favours_central_spine():
    """Warm-humid (Chennai/Mumbai) → CENTRAL_SPINE highest climate_fit."""
    pa = make_plot_analysis(chennai_30x40())       # warm_humid
    assert score_climate_fit(TopologyKind.CENTRAL_SPINE, pa) >= score_climate_fit(
        TopologyKind.STRIP, pa
    )
    assert score_climate_fit(TopologyKind.CENTRAL_SPINE, pa) >= score_climate_fit(
        TopologyKind.L_SHAPE, pa
    )


def test_climate_fit_composite_disfavours_courtyard():
    """Delhi (composite) → COURTYARD scores lower than STRIP."""
    pa = make_plot_analysis(delhi_60x90())
    assert score_climate_fit(TopologyKind.COURTYARD, pa) < score_climate_fit(
        TopologyKind.STRIP, pa
    )


# ─── aspect_ratio_fit ─────────────────────────────────────────────────────


def test_aspect_ratio_fit_penalizes_strip_on_deep_plot():
    """A deep plot (high aspect_ratio) penalizes STRIP."""
    pa_shallow = make_plot_analysis(bangalore_40x60())     # ar = 1.5
    pa_deep    = make_plot_analysis(delhi_60x90())          # ar = 1.5
    # Both are AR=1.5 actually. Let's check a known-deep test.
    # bangalore_40x60: 12.192 × 18.288 → ar = 1.5
    # We construct a deeper plot:
    from buildemup.domain.envelope import PlotOrientation
    from buildemup.domain.plot import Plot
    plot_deep = Plot(
        width_m=8.0, depth_m=24.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
    )
    pa_deep = make_plot_analysis(plot_deep)
    assert score_aspect_ratio_fit(TopologyKind.STRIP, pa_deep) < score_aspect_ratio_fit(
        TopologyKind.STRIP, pa_shallow
    )


# ─── corridor_overhead ────────────────────────────────────────────────────


def test_corridor_overhead_strip_lowest():
    """STRIP has lowest overhead → highest raw fitness score."""
    pa = make_plot_analysis(bangalore_40x60())
    assert score_corridor_overhead(TopologyKind.STRIP, pa) > score_corridor_overhead(
        TopologyKind.COURTYARD, pa
    )


def test_corridor_overhead_courtyard_highest():
    pa = make_plot_analysis(bangalore_40x60())
    raws = [
        score_corridor_overhead(k, pa) for k in TopologyKind
    ]
    courtyard_raw = score_corridor_overhead(TopologyKind.COURTYARD, pa)
    assert courtyard_raw == min(raws)


# ─── bedroom_fit (Q1 design + v0.7 § 14.2 factor) ─────────────────────────


def test_topology_min_bedrooms_per_topology():
    """Per v0.7 § 14.2 #8 table."""
    assert TOPOLOGY_MIN_BEDROOMS[TopologyKind.STRIP] == 1
    assert TOPOLOGY_MIN_BEDROOMS[TopologyKind.CENTRAL_SPINE] == 2
    assert TOPOLOGY_MIN_BEDROOMS[TopologyKind.L_SHAPE] == 2
    assert TOPOLOGY_MIN_BEDROOMS[TopologyKind.COURTYARD] == 3


def test_strip_no_bedroom_penalty_at_any_count():
    """STRIP min=1 ⇒ factor=1.0 for any bedroom_count >= 1."""
    for bed in (1, 2, 3, 4, 5):
        # factor = min(1, bed/1) = 1 for bed >= 1
        # base table: STRIP {1,2}=1.0, 3=0.7, >=4=0.4
        brief = make_floor_brief(bedroom_count=bed)
        result = score_bedroom_fit(TopologyKind.STRIP, brief)
        expected = _topology_base_bedroom_fit(TopologyKind.STRIP, bed) * 1.0
        assert result == pytest.approx(expected)


def test_courtyard_penalized_for_few_bedrooms():
    """COURTYARD's min=3 ⇒ factor < 1 for bedroom_count < 3."""
    brief_1 = make_floor_brief(bedroom_count=1)
    brief_3 = make_floor_brief(bedroom_count=3)
    score_1 = score_bedroom_fit(TopologyKind.COURTYARD, brief_1)
    score_3 = score_bedroom_fit(TopologyKind.COURTYARD, brief_3)
    assert score_1 < score_3


def test_topology_base_bedroom_fit_q1_table():
    """Q1 design (S30) — exhaustive table check."""
    cases = [
        # (topology, bedroom_count, expected_base)
        (TopologyKind.STRIP, 1, 1.0),
        (TopologyKind.STRIP, 2, 1.0),
        (TopologyKind.STRIP, 3, 0.7),
        (TopologyKind.STRIP, 4, 0.4),
        (TopologyKind.STRIP, 5, 0.4),
        (TopologyKind.CENTRAL_SPINE, 1, 0.7),
        (TopologyKind.CENTRAL_SPINE, 2, 1.0),
        (TopologyKind.CENTRAL_SPINE, 3, 1.0),
        (TopologyKind.CENTRAL_SPINE, 4, 1.0),
        (TopologyKind.CENTRAL_SPINE, 5, 0.7),
        (TopologyKind.CENTRAL_SPINE, 6, 0.4),
        (TopologyKind.L_SHAPE, 1, 0.7),
        (TopologyKind.L_SHAPE, 2, 1.0),
        (TopologyKind.L_SHAPE, 3, 1.0),
        (TopologyKind.L_SHAPE, 4, 0.7),
        (TopologyKind.L_SHAPE, 5, 0.4),
        (TopologyKind.COURTYARD, 1, 0.4),
        (TopologyKind.COURTYARD, 2, 0.7),
        (TopologyKind.COURTYARD, 3, 1.0),
        (TopologyKind.COURTYARD, 4, 1.0),
        (TopologyKind.COURTYARD, 5, 1.0),
        (TopologyKind.COURTYARD, 6, 0.7),
        (TopologyKind.COURTYARD, 7, 0.4),
    ]
    for topology, bed, expected in cases:
        actual = _topology_base_bedroom_fit(topology, bed)
        assert actual == pytest.approx(expected), (
            f"{topology.value}/bed={bed}: got {actual}, expected {expected}"
        )


def test_score_bedroom_fit_zero_at_zero_bedrooms():
    """0 bedrooms ⇒ factor=0 ⇒ score 0 (topology vacuous without bedrooms)."""
    brief = make_floor_brief(bedroom_count=0)
    for kind in TopologyKind:
        assert score_bedroom_fit(kind, brief) == 0.0


# ─── open_side_count ──────────────────────────────────────────────────────


def test_open_side_count_courtyard_decreases_with_more_open_sides():
    """Many open sides → courtyard ventilation benefit weakens → score drops."""
    # All v1 fixtures are detached → 4 open sides.
    pa_detached = make_plot_analysis(chennai_30x40())
    # Assert detached → courtyard score is LESS than 1 (the no-open-sides max)
    assert score_open_side_count(TopologyKind.COURTYARD, pa_detached) < 1.0


# ─── compute_raw_scores ───────────────────────────────────────────────────


def test_compute_raw_scores_returns_all_seven_criteria():
    pa = make_plot_analysis(bangalore_40x60())
    for kind in TopologyKind:
        raw = compute_raw_scores(kind, pa, medium_brief())
        assert set(raw.keys()) == set(BASE_WEIGHTS.keys())
        assert len(raw) == 7
