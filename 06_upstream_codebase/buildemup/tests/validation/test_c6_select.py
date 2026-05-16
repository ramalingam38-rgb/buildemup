"""C6 select tests — public orchestrator end-to-end.

Per C6 SPEC v0.7 LOCKED §§ 2, 5 + § 6 + § 4.6. Reconstructed at S33 per B-127.

Coverage:
  - Happy path: full pipeline (C4 → C5 → C6) on multiple plot/brief combos.
  - Cardinality preservation: |output| == |input| (per § 14.3).
  - Empty input handling.
  - Validator invariant 1: direction_priorities cardinal-only.
  - Validator invariant 9 (NEW v0.6): refined_zone_bands values cardinal-only.
  - Provenance correctness: weights, dominance, dominant_signal coherence.
  - Hysteresis behavior: chosen_over_seed flag.
  - All 4 cardinal facings: NORTH, EAST, SOUTH, WEST end-to-end.
  - All 3 supported climates × 3 vastu tiers (excluding FULL — fails).
"""
from __future__ import annotations

import pytest

from buildemup.components.c04 import derive
from buildemup.components.c04.schema import ClimateZone
from buildemup.components.c05 import select_topology
from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c06 import (
    CARDINAL_FACINGS,
    OrientationPriority,
    OrientedCandidate,
    SIGNAL_DOMINANCE_THRESHOLD,
    prioritize_orientation,
)
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot
from buildemup.tests.validation._c6_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    hyderabad_30x40,
    large_brief,
    make_plot_analysis,
    medium_brief,
    mumbai_30x40,
    pune_30x40,
    small_brief,
)


# ─── Happy paths ──────────────────────────────────────────────────────────


def test_happy_path_bangalore_off_tier():
    """3-bed bangalore plot with OFF Vastu — pipeline returns ≥1 candidate."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert len(out) == len(cands)
    assert all(isinstance(o, OrientedCandidate) for o in out)


def test_happy_path_mumbai_partial_tier():
    """WARM_HUMID climate test (mumbai is the cardinal-facing WARM_HUMID fixture; chennai is intercardinal so cannot be used in C6 v1)."""
    plot = mumbai_30x40()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, small_brief())
    out = prioritize_orientation(cands, pa, VastuTier.PARTIAL)
    assert len(out) >= 1


def test_happy_path_delhi_off_large():
    plot = delhi_60x90()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, large_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert len(out) >= 1


def test_happy_path_pune():
    plot = pune_30x40()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert len(out) >= 1


def test_happy_path_hyderabad():
    plot = hyderabad_30x40()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert len(out) >= 1


# ─── Cardinality preservation (§ 14.3 / Q3) ─────────────────────────────


def test_cardinality_preserved():
    """|output| == |input|; position-paired."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert len(out) == len(cands)


def test_position_pairing():
    """out[i].topology_candidate IS cands[i] (same identity)."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for i, o in enumerate(out):
        assert o.topology_candidate is cands[i]


def test_empty_input_returns_empty():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    out = prioritize_orientation((), pa, VastuTier.OFF)
    assert out == ()


def test_empty_input_still_validates_other_args():
    """Empty candidates still trigger TypeError on bad vastu_tier."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    with pytest.raises(TypeError, match=r"vastu_tier must be VastuTier"):
        prioritize_orientation((), pa, "OFF")  # type: ignore


# ─── Validator invariants (§ 4.6) ────────────────────────────────────────


def test_invariant_1_direction_priorities_only_cardinal():
    """Every OrientationPriority.direction_priorities covers exactly cardinals."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert set(o.orientation.direction_priorities.keys()) == CARDINAL_FACINGS


def test_invariant_9_refined_zone_bands_only_cardinal():
    """Every OrientationPriority.refined_zone_bands value is cardinal (NEW v0.6)."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        for b, d in o.orientation.refined_zone_bands.items():
            assert d in CARDINAL_FACINGS, f"Band {b.value} → {d.value} not cardinal"


def test_priority_confidence_in_range():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert 0.0 <= o.orientation.priority_confidence <= 1.0


def test_score_margin_non_negative():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert o.orientation.score_margin >= 0.0


# ─── Provenance ──────────────────────────────────────────────────────────


def test_provenance_carries_climate_profile():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert o.orientation.provenance.climate_profile == pa.climate_zone.value


def test_provenance_carries_vastu_tier():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.PARTIAL)
    for o in out:
        assert o.orientation.provenance.vastu_tier == VastuTier.PARTIAL


def test_provenance_dominance_below_threshold_implies_none():
    """Validator invariant 8 in provenance schema."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        prov = o.orientation.provenance
        below = prov.signal_dominance < SIGNAL_DOMINANCE_THRESHOLD
        assert (prov.dominant_signal is None) == below


def test_provenance_weights_sum_to_one():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert sum(o.orientation.provenance.weights_applied.values()) == pytest.approx(1.0)


def test_provenance_seed_distance_at_least_zero():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert o.orientation.provenance.seed_distance >= 0


def test_provenance_permutation_search_size_at_least_zero():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert o.orientation.provenance.permutation_search_size >= 0


def test_provenance_rule_trace_is_tuple():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert isinstance(o.orientation.provenance.rule_trace, tuple)


def test_provenance_chosen_over_seed_is_bool():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert isinstance(o.orientation.provenance.chosen_over_seed, bool)


# ─── All 4 cardinal facings ─────────────────────────────────────────────


@pytest.mark.parametrize("facing", [
    PlotOrientation.NORTH, PlotOrientation.EAST,
    PlotOrientation.SOUTH, PlotOrientation.WEST,
])
def test_all_cardinal_facings_work(facing):
    """End-to-end on all 4 cardinal facings."""
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=facing,
        city="bangalore", road_width_m=9.0, corner_plot=False,
    )
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert len(out) >= 1
    # PUBLIC band should face the road (entry-on-road invariant)
    for o in out:
        assert o.orientation.refined_zone_bands[ZoneBand.PUBLIC] == facing


# ─── All 3 climate × 2 supported tiers (FULL fails separately) ─────────


# City fixtures by climate (chennai=WARM_HUMID is intercardinal; use mumbai instead).
_CLIMATE_TO_PLOT_FIXTURE = {
    ClimateZone.WARM_HUMID: mumbai_30x40,    # WEST facing
    ClimateZone.COMPOSITE: delhi_60x90,      # SOUTH facing
    ClimateZone.TEMPERATE: pune_30x40,       # NORTH facing
}


@pytest.mark.parametrize("climate", [
    ClimateZone.WARM_HUMID, ClimateZone.COMPOSITE, ClimateZone.TEMPERATE,
])
@pytest.mark.parametrize("tier", [VastuTier.OFF, VastuTier.PARTIAL])
def test_climate_tier_matrix(climate, tier):
    """All 6 (3 × 2) supported climate×tier combos run end-to-end.

    Climate is selected by city fixture (city → climate via C4's CITY_GEOGRAPHY).
    """
    plot = _CLIMATE_TO_PLOT_FIXTURE[climate]()
    pa = make_plot_analysis(plot)
    assert pa.climate_zone == climate, (
        f"plot fixture {plot.city} produced climate {pa.climate_zone}, expected {climate}"
    )
    cands = select_topology(pa, medium_brief() if climate != ClimateZone.WARM_HUMID else small_brief())
    out = prioritize_orientation(cands, pa, tier)
    assert len(out) >= 1
    # Confirm provenance reports the right climate
    for o in out:
        assert o.orientation.provenance.climate_profile == climate.value


# ─── Hysteresis-related ────────────────────────────────────────────────


def test_seed_distance_zero_when_seed_held():
    """When chosen_over_seed=False, seed_distance == 0."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        if not o.orientation.provenance.chosen_over_seed:
            assert o.orientation.provenance.seed_distance == 0


def test_refined_zone_bands_keyset_matches_seed():
    """C5's seed bandset is preserved in refined_zone_bands."""
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for c, o in zip(cands, out):
        assert set(o.orientation.refined_zone_bands.keys()) == set(c.zone_bands.keys())


# ─── Public band on road (entry-on-road) ─────────────────────────────────


def test_public_band_faces_plot_facing():
    """For a non-corner plot, PUBLIC must face plot.facing (entry-on-road)."""
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.EAST,
        city="bangalore", road_width_m=9.0, corner_plot=False,
    )
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert o.orientation.refined_zone_bands[ZoneBand.PUBLIC] == PlotOrientation.EAST


def test_corner_plot_public_band_on_either_road():
    """Corner plot: PUBLIC on plot_facing OR secondary road direction."""
    plot = Plot(
        width_m=9.144, depth_m=12.192, facing=PlotOrientation.EAST,
        city="chennai", road_width_m=9.0, corner_plot=True,
        second_road_width_m=8.0,
    )
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        public_dir = o.orientation.refined_zone_bands[ZoneBand.PUBLIC]
        # plot_facing is EAST; secondary derived by C4 (NORTH or SOUTH typically)
        # We just assert it's not WEST (definitely not road)
        assert public_dir != PlotOrientation.WEST


# ─── Output type ──────────────────────────────────────────────────────


def test_output_is_tuple():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert isinstance(out, tuple)


def test_each_output_is_oriented_candidate():
    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    for o in out:
        assert isinstance(o, OrientedCandidate)
        assert isinstance(o.orientation, OrientationPriority)
