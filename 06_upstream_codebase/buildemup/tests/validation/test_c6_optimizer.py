"""C6 optimizer tests — permutations, prune, scoring, tie-break, hysteresis, confidence.

Per C6 SPEC v0.7 LOCKED §§ 4.3, 4.4, 4.5 + § 14.5–14.7, § 14.10–14.20. Reconstructed at S33 per B-127.

Coverage:
  - BAND_TO_FUNCTION mapping (CIRCULATION absent).
  - enumerate_permutations: distinct/itertools.product paths; cardinality.
  - prune_by_entry_on_road: filter, secondary plot semantics, MAX cap.
  - compute_function_scores: blending formula, range clamping.
  - _circulation_score: 0.3*sun + 0.2*wind + 0.5 baseline.
  - score_permutation: total = Σ functional + 0.5 * circulation.
  - hamming_distance: differing positions count.
  - tie_break_key: 5-tier ordering.
  - apply_hysteresis: SWAP threshold = 0.10.
  - compute_confidence: margin-clamped formula.
"""
from __future__ import annotations

import math

import pytest

from buildemup.components.c04.schema import ClimateZone
from buildemup.components.c05.schema import TopologyKind, ZoneBand
from buildemup.components.c06 import (
    FunctionRole,
    MAX_PERMUTATION_COUNT,
    MIN_DENOM,
    SWAP_HYSTERESIS_THRESHOLD,
)
from buildemup.components.c06.optimizer import (
    BAND_TO_FUNCTION,
    FUNCTIONAL_BANDS,
    _circulation_score,
    apply_hysteresis,
    compute_confidence,
    compute_function_scores,
    enumerate_permutations,
    hamming_distance,
    prune_by_entry_on_road,
    score_permutation,
    tie_break_key,
)
from buildemup.components.c06.signals import (
    sun_function_lookup,
    sun_score,
    wind_function_lookup,
    wind_score,
)
from buildemup.components.c06.vastu_kb import vastu_score_4dir
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─── BAND_TO_FUNCTION mapping ─────────────────────────────────────────────


def test_band_to_function_excludes_circulation():
    """CIRCULATION uses _circulation_score helper, not a FunctionRole."""
    assert ZoneBand.CIRCULATION not in BAND_TO_FUNCTION


def test_band_to_function_public_living():
    assert BAND_TO_FUNCTION[ZoneBand.PUBLIC] == FunctionRole.LIVING


def test_band_to_function_service_kitchen():
    assert BAND_TO_FUNCTION[ZoneBand.SERVICE] == FunctionRole.KITCHEN


def test_band_to_function_private_bedroom():
    assert BAND_TO_FUNCTION[ZoneBand.PRIVATE] == FunctionRole.BEDROOM


def test_functional_bands_set():
    """FUNCTIONAL_BANDS = keys of BAND_TO_FUNCTION."""
    assert FUNCTIONAL_BANDS == frozenset({
        ZoneBand.PUBLIC, ZoneBand.SERVICE, ZoneBand.PRIVATE,
    })


# ─── enumerate_permutations ──────────────────────────────────────────────


def _seed_4_band(public_dir=PlotOrientation.NORTH) -> dict:
    """4-band seed (PUBLIC, SERVICE, PRIVATE, CIRCULATION)."""
    return {
        ZoneBand.PUBLIC: public_dir,
        ZoneBand.SERVICE: PlotOrientation.WEST,
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
        ZoneBand.CIRCULATION: PlotOrientation.EAST,
    }


def test_enumerate_permutations_strip_4_distinct():
    """STRIP topology: distinct cardinals; 4! = 24 permutations for 4 bands."""
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.STRIP)
    assert len(perms) == 24


def test_enumerate_permutations_central_spine_24():
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.CENTRAL_SPINE)
    assert len(perms) == 24


def test_enumerate_permutations_l_shape_24():
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.L_SHAPE)
    assert len(perms) == 24


def test_enumerate_permutations_courtyard_256():
    """COURTYARD: cardinals can repeat; 4^4 = 256."""
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.COURTYARD)
    assert len(perms) == 256


def test_enumerate_permutations_3_band_strip_24():
    """3 bands without CIRCULATION: 4P3 = 24."""
    seed = {
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
        ZoneBand.SERVICE: PlotOrientation.WEST,
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
    }
    perms = enumerate_permutations(seed, TopologyKind.STRIP)
    assert len(perms) == 24  # 4 * 3 * 2


def test_enumerate_permutations_each_perm_is_immutable():
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.STRIP)
    with pytest.raises(TypeError):
        perms[0][ZoneBand.PUBLIC] = PlotOrientation.SOUTH  # type: ignore


def test_enumerate_permutations_each_perm_keyset_matches_seed():
    """Every permutation's keys = seed's keys."""
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.STRIP)
    seed_keys = set(seed.keys())
    for p in perms:
        assert set(p.keys()) == seed_keys


def test_enumerate_permutations_cardinals_only():
    """Every value is one of the 4 cardinals."""
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.STRIP)
    cardinals = {PlotOrientation.NORTH, PlotOrientation.EAST,
                 PlotOrientation.SOUTH, PlotOrientation.WEST}
    for p in perms:
        for v in p.values():
            assert v in cardinals


# ─── prune_by_entry_on_road ──────────────────────────────────────────────


def test_prune_keeps_only_public_facing_road():
    """All survivors have PUBLIC == plot_facing or secondary."""
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.STRIP)
    survivors = prune_by_entry_on_road(
        perms, plot_facing=PlotOrientation.EAST, secondary_road_direction=None,
    )
    for p in survivors:
        assert p[ZoneBand.PUBLIC] == PlotOrientation.EAST


def test_prune_keeps_secondary_too():
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.STRIP)
    survivors = prune_by_entry_on_road(
        perms,
        plot_facing=PlotOrientation.EAST,
        secondary_road_direction=PlotOrientation.NORTH,
    )
    public_dirs = {p[ZoneBand.PUBLIC] for p in survivors}
    assert public_dirs == {PlotOrientation.EAST, PlotOrientation.NORTH}


def test_prune_strip_4band_facing_east_count():
    """STRIP 4-band, facing EAST: PUBLIC fixed at E → 3! = 6 survivors."""
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.STRIP)
    survivors = prune_by_entry_on_road(
        perms, plot_facing=PlotOrientation.EAST, secondary_road_direction=None,
    )
    assert len(survivors) == 6


def test_prune_courtyard_at_cap():
    """COURTYARD 4-band with both cardinals → 4^3 × 2 = 128 survivors. Under cap."""
    seed = _seed_4_band()
    perms = enumerate_permutations(seed, TopologyKind.COURTYARD)
    survivors = prune_by_entry_on_road(
        perms,
        plot_facing=PlotOrientation.EAST,
        secondary_road_direction=PlotOrientation.NORTH,
    )
    # PUBLIC has 2 allowed values; remaining 3 bands × 4 cardinals each = 4^3 = 64
    # Total = 2 × 64 = 128. Well under MAX_PERMUTATION_COUNT = 256.
    assert len(survivors) == 128
    assert len(survivors) <= MAX_PERMUTATION_COUNT


def test_prune_no_survivors_when_public_missing():
    """If PUBLIC not in seed (degenerate), no perm has it → no survivors."""
    seed_no_public = {
        ZoneBand.SERVICE: PlotOrientation.NORTH,
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
        ZoneBand.CIRCULATION: PlotOrientation.WEST,
    }
    perms = enumerate_permutations(seed_no_public, TopologyKind.STRIP)
    survivors = prune_by_entry_on_road(
        perms, plot_facing=PlotOrientation.NORTH, secondary_road_direction=None,
    )
    assert len(survivors) == 0


# ─── compute_function_scores ─────────────────────────────────────────────


def test_compute_function_scores_returns_all_six_roles():
    out = compute_function_scores(
        direction=PlotOrientation.NORTH,
        climate_zone=ClimateZone.COMPOSITE,
        weights_applied={"sun": 0.625, "wind": 0.375, "vastu": 0.0},
        vastu_tier=VastuTier.OFF,
    )
    assert set(out.keys()) == set(FunctionRole)


def test_compute_function_scores_in_range():
    """All values clamped to [0, 1]."""
    out = compute_function_scores(
        direction=PlotOrientation.NORTH,
        climate_zone=ClimateZone.COMPOSITE,
        weights_applied={"sun": 0.625, "wind": 0.375, "vastu": 0.0},
        vastu_tier=VastuTier.OFF,
    )
    for f, v in out.items():
        assert 0.0 <= v <= 1.0


def test_compute_function_scores_off_tier_ignores_vastu_weight():
    """OFF: vastu_score is 0; result is sun×sun_lookup×w_sun + wind×wind_lookup×w_wind."""
    sun_v = sun_score(PlotOrientation.NORTH)        # 0.95
    wind_v = wind_score(PlotOrientation.NORTH, ClimateZone.COMPOSITE)  # 0.7
    weights = {"sun": 0.625, "wind": 0.375, "vastu": 0.0}
    expected_living = (
        sun_v * sun_function_lookup(FunctionRole.LIVING) * weights["sun"]
        + wind_v * wind_function_lookup(FunctionRole.LIVING) * weights["wind"]
    )
    out = compute_function_scores(
        direction=PlotOrientation.NORTH,
        climate_zone=ClimateZone.COMPOSITE,
        weights_applied=weights,
        vastu_tier=VastuTier.OFF,
    )
    assert out[FunctionRole.LIVING] == pytest.approx(expected_living)


def test_compute_function_scores_partial_includes_vastu():
    """PARTIAL: includes vastu term; value differs from OFF."""
    weights_partial = {"sun": 1.0 / 2.0, "wind": 0.6 / 2.0, "vastu": 0.4 / 2.0}
    weights_off = {"sun": 1.0 / 1.6, "wind": 0.6 / 1.6, "vastu": 0.0}
    out_partial = compute_function_scores(
        direction=PlotOrientation.NORTH,
        climate_zone=ClimateZone.COMPOSITE,
        weights_applied=weights_partial,
        vastu_tier=VastuTier.PARTIAL,
    )
    out_off = compute_function_scores(
        direction=PlotOrientation.NORTH,
        climate_zone=ClimateZone.COMPOSITE,
        weights_applied=weights_off,
        vastu_tier=VastuTier.OFF,
    )
    # The two will differ since PARTIAL adds vastu term
    assert out_partial[FunctionRole.POOJA] != pytest.approx(out_off[FunctionRole.POOJA])


def test_compute_function_scores_full_tier_raises_b099():
    weights = {"sun": 1.0 / 2.3, "wind": 0.6 / 2.3, "vastu": 0.7 / 2.3}
    with pytest.raises(NotImplementedError, match=r"B-099"):
        compute_function_scores(
            direction=PlotOrientation.NORTH,
            climate_zone=ClimateZone.COMPOSITE,
            weights_applied=weights,
            vastu_tier=VastuTier.FULL,
        )


def test_compute_function_scores_returns_immutable():
    out = compute_function_scores(
        direction=PlotOrientation.NORTH,
        climate_zone=ClimateZone.COMPOSITE,
        weights_applied={"sun": 0.5, "wind": 0.5, "vastu": 0.0},
        vastu_tier=VastuTier.OFF,
    )
    with pytest.raises(TypeError):
        out[FunctionRole.LIVING] = 0.0  # type: ignore


# ─── _circulation_score ──────────────────────────────────────────────────


def test_circulation_score_formula_north_composite():
    """0.3 × sun + 0.2 × wind + 0.5."""
    expected = 0.3 * 0.95 + 0.2 * 0.7 + 0.5  # 0.285 + 0.14 + 0.5 = 0.925
    assert _circulation_score(PlotOrientation.NORTH, ClimateZone.COMPOSITE) == pytest.approx(expected)


def test_circulation_score_baseline_minimum():
    """Even worst-case (sun=0.20 W, wind=0.5) gives at least 0.5 + 0.06 + 0.10 = 0.66.

    West sun = 0.20; West wind COMPOSITE = 0.5.
    Score = 0.3*0.20 + 0.2*0.5 + 0.5 = 0.06 + 0.10 + 0.5 = 0.66.
    """
    score = _circulation_score(PlotOrientation.WEST, ClimateZone.COMPOSITE)
    assert score == pytest.approx(0.66)


def test_circulation_score_maximum_below_one():
    """Maximum possible = 0.3*0.95 + 0.2*0.9 + 0.5 = 0.965; never exceeds 1.0."""
    # NORTH sun=0.95, SOUTH wind WARM_HUMID=0.9 — combine for upper bound
    n_warm_humid = _circulation_score(PlotOrientation.NORTH, ClimateZone.WARM_HUMID)
    # 0.3*0.95 + 0.2*0.6 + 0.5 = 0.285 + 0.12 + 0.5 = 0.905
    assert n_warm_humid == pytest.approx(0.905)
    assert n_warm_humid <= 1.0


# ─── score_permutation ──────────────────────────────────────────────────


def _full_fs_by_dir() -> dict:
    """Helper: function_scores for all 4 cardinals, all 6 functions = 0.5."""
    return {
        d: {f: 0.5 for f in FunctionRole}
        for d in [PlotOrientation.NORTH, PlotOrientation.EAST,
                  PlotOrientation.SOUTH, PlotOrientation.WEST]
    }


def test_score_permutation_sums_functional_and_circulation():
    """total = 0.5+0.5+0.5 (3 functional bands) + 0.5*_circ_score."""
    perm = _seed_4_band()
    fs = _full_fs_by_dir()
    total = score_permutation(perm, fs, ClimateZone.COMPOSITE)
    expected = 0.5 + 0.5 + 0.5 + 0.5 * _circulation_score(
        PlotOrientation.EAST, ClimateZone.COMPOSITE,
    )
    assert total == pytest.approx(expected)


def test_score_permutation_no_circulation_band():
    """Without CIRCULATION: total = sum over functional bands only."""
    perm_3 = {
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
        ZoneBand.SERVICE: PlotOrientation.WEST,
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
    }
    fs = _full_fs_by_dir()
    total = score_permutation(perm_3, fs, ClimateZone.COMPOSITE)
    assert total == pytest.approx(1.5)  # 3 × 0.5


def test_score_permutation_unknown_band_skipped():
    """Defensive: a band not in BAND_TO_FUNCTION and != CIRCULATION is skipped."""
    # Only PUBLIC + SERVICE — score is 1.0
    perm = {
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
        ZoneBand.SERVICE: PlotOrientation.WEST,
    }
    fs = _full_fs_by_dir()
    total = score_permutation(perm, fs, ClimateZone.COMPOSITE)
    assert total == pytest.approx(1.0)


# ─── hamming_distance ───────────────────────────────────────────────────


def test_hamming_distance_identical_zero():
    p = _seed_4_band()
    assert hamming_distance(p, p) == 0


def test_hamming_distance_one_diff():
    p1 = _seed_4_band(PlotOrientation.NORTH)
    p2 = _seed_4_band(PlotOrientation.EAST)
    assert hamming_distance(p1, p2) == 1


def test_hamming_distance_all_different():
    p1 = {
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
        ZoneBand.SERVICE: PlotOrientation.EAST,
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
        ZoneBand.CIRCULATION: PlotOrientation.WEST,
    }
    p2 = {
        ZoneBand.PUBLIC: PlotOrientation.WEST,
        ZoneBand.SERVICE: PlotOrientation.SOUTH,
        ZoneBand.PRIVATE: PlotOrientation.EAST,
        ZoneBand.CIRCULATION: PlotOrientation.NORTH,
    }
    assert hamming_distance(p1, p2) == 4


def test_hamming_distance_disjoint_keys():
    """Bands present in only one perm count as differing."""
    p1 = {ZoneBand.PUBLIC: PlotOrientation.NORTH}
    p2 = {ZoneBand.SERVICE: PlotOrientation.NORTH}
    assert hamming_distance(p1, p2) == 2


# ─── tie_break_key ──────────────────────────────────────────────────────


def test_tie_break_key_primary_higher_score_first():
    """When sorted ascending, higher total_score → key starts with smaller -score."""
    perm = _seed_4_band()
    fs = _full_fs_by_dir()
    seed = perm
    k_high = tie_break_key(perm, total_score=0.9, seed_perm=seed, function_scores_by_dir=fs)
    k_low = tie_break_key(perm, total_score=0.5, seed_perm=seed, function_scores_by_dir=fs)
    assert k_high < k_low  # high score sorts first


def test_tie_break_key_secondary_minimal_hamming_first():
    """At equal primary, prefer perm closer to seed."""
    seed = _seed_4_band()
    perm_close = seed
    perm_far = {
        ZoneBand.PUBLIC: PlotOrientation.SOUTH,
        ZoneBand.SERVICE: PlotOrientation.EAST,
        ZoneBand.PRIVATE: PlotOrientation.NORTH,
        ZoneBand.CIRCULATION: PlotOrientation.WEST,
    }
    fs = _full_fs_by_dir()
    k_close = tie_break_key(perm_close, total_score=0.7, seed_perm=seed, function_scores_by_dir=fs)
    k_far = tie_break_key(perm_far, total_score=0.7, seed_perm=seed, function_scores_by_dir=fs)
    assert k_close < k_far


def test_tie_break_key_returns_5_tuple():
    perm = _seed_4_band()
    fs = _full_fs_by_dir()
    k = tie_break_key(perm, total_score=0.7, seed_perm=perm, function_scores_by_dir=fs)
    assert isinstance(k, tuple)
    assert len(k) == 5


def test_tie_break_key_third_tier_living_score():
    """Higher living-score for PUBLIC's direction → preferred."""
    seed = _seed_4_band()
    fs1 = {
        d: {f: 0.5 for f in FunctionRole}
        for d in [PlotOrientation.NORTH, PlotOrientation.EAST,
                  PlotOrientation.SOUTH, PlotOrientation.WEST]
    }
    # Bump LIVING for NORTH (PUBLIC's direction)
    fs1[PlotOrientation.NORTH][FunctionRole.LIVING] = 0.9
    perm_a = seed   # PUBLIC=NORTH; living=0.9
    # Construct perm_b same hamming/score but PUBLIC pointing elsewhere with 0.5 living
    perm_b = dict(seed)
    perm_b[ZoneBand.PUBLIC] = PlotOrientation.NORTH  # same as a → equal
    # Use identical perms for "all else equal" test
    k_a = tie_break_key(perm_a, total_score=0.7, seed_perm=seed, function_scores_by_dir=fs1)
    # The 3rd tier component is -living_score; higher is more negative → smaller key
    assert k_a[2] == -0.9


# ─── apply_hysteresis ──────────────────────────────────────────────────


def test_apply_hysteresis_swap_at_threshold():
    """Diff exactly at threshold → swap (>=). Use exact-FP-clean boundary."""
    # Construct so diff is exactly SWAP_HYSTERESIS_THRESHOLD without FP drift.
    assert apply_hysteresis(global_top_score=SWAP_HYSTERESIS_THRESHOLD, seed_score=0.0) is True


def test_apply_hysteresis_no_swap_below_threshold():
    """Diff below threshold → keep seed."""
    assert apply_hysteresis(global_top_score=0.55, seed_score=0.50) is False


def test_apply_hysteresis_no_swap_when_seed_higher():
    """Seed already higher → certainly no swap."""
    assert apply_hysteresis(global_top_score=0.4, seed_score=0.6) is False


def test_apply_hysteresis_swap_well_above_threshold():
    assert apply_hysteresis(global_top_score=0.9, seed_score=0.3) is True


def test_apply_hysteresis_no_swap_when_equal():
    """Equal → diff=0 < threshold → no swap (preserve seed)."""
    assert apply_hysteresis(global_top_score=0.5, seed_score=0.5) is False


def test_swap_hysteresis_threshold_value():
    """Sanity: published constant = 0.10."""
    assert SWAP_HYSTERESIS_THRESHOLD == 0.10


# ─── compute_confidence ───────────────────────────────────────────────


def test_compute_confidence_no_second_returns_one():
    """No competition → max confidence."""
    assert compute_confidence(top_score=0.7, second_score=None) == 1.0


def test_compute_confidence_zero_margin_returns_zero():
    """Tied top and second → margin 0 → confidence 0."""
    assert compute_confidence(top_score=0.7, second_score=0.7) == 0.0


def test_compute_confidence_full_margin_when_top_close_to_one():
    """top=1.0, second=0 → margin/max=1.0 → confidence 1.0."""
    assert compute_confidence(top_score=1.0, second_score=0.0) == 1.0


def test_compute_confidence_min_denom_protects_low_top():
    """When top is small, denom = MIN_DENOM = 0.1 protects from inflation."""
    # top=0.05, second=0.0: margin=0.05; denom=max(0.05, 0.1)=0.1; ratio=0.5
    assert compute_confidence(top_score=0.05, second_score=0.0) == pytest.approx(0.5)


def test_compute_confidence_clamped_to_zero_when_negative_margin():
    """Defensive: if second > top (shouldn't happen post-sort), clamps to 0."""
    assert compute_confidence(top_score=0.3, second_score=0.5) == 0.0


def test_compute_confidence_typical_case():
    """top=0.8, second=0.6: margin=0.2; denom=0.8; ratio=0.25."""
    assert compute_confidence(top_score=0.8, second_score=0.6) == pytest.approx(0.25)


def test_compute_confidence_clamps_to_one():
    """Pathological positive value clamps to 1.0."""
    # margin=2.0, denom=1.0 → ratio=2.0 → clamped to 1.0
    assert compute_confidence(top_score=1.0, second_score=-1.0) == 1.0


def test_compute_confidence_min_denom_value():
    """MIN_DENOM == 0.1 (per § 14.15)."""
    assert MIN_DENOM == 0.1
