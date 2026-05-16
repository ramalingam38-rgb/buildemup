"""C6 vastu_kb tests — VASTU_TABLE_PARTIAL, adjacent_intercardinals, vastu_score_4dir.

Per C6 SPEC v0.7 LOCKED § 4.1.4 + § 14.4 + § 14.19. Reconstructed at S33 per B-127.

Coverage:
  - VASTU_TABLE_PARTIAL: 8-direction × 6-function coverage, immutability,
    range checks, signature placements (NE/POOJA, SE/KITCHEN, SW/BEDROOM,
    NE/WET_AREA = 0.0).
  - adjacent_intercardinals: cardinal-only contract; CCW/CW order.
  - vastu_score_4dir: tier semantics (OFF→0.0, FULL→raise, PARTIAL→table-driven),
    weighted-avg aggregation formula, cardinal-only input.
"""
from __future__ import annotations

import pytest

from buildemup.components.c06 import FunctionRole
from buildemup.components.c06.vastu_kb import (
    VASTU_TABLE_PARTIAL,
    adjacent_intercardinals,
    vastu_score_4dir,
)
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─── VASTU_TABLE_PARTIAL coverage ─────────────────────────────────────────


def test_vastu_table_covers_all_8_directions():
    """Internal table is keyed by all 8 PlotOrientation members (cardinal + intercardinal)."""
    assert set(VASTU_TABLE_PARTIAL.keys()) == set(PlotOrientation)


def test_vastu_table_covers_all_6_functions_per_direction():
    """Every direction's inner mapping covers all 6 FunctionRole members."""
    for d, inner in VASTU_TABLE_PARTIAL.items():
        assert set(inner.keys()) == set(FunctionRole), f"direction {d.value} incomplete"


def test_vastu_table_values_in_range():
    """Every value in [0, 1]."""
    for d, inner in VASTU_TABLE_PARTIAL.items():
        for f, v in inner.items():
            assert 0.0 <= v <= 1.0, f"VASTU[{d.value}][{f.value}] = {v} out of range"


def test_vastu_table_outer_is_immutable():
    """VASTU_TABLE_PARTIAL outer is MappingProxyType."""
    with pytest.raises(TypeError):
        VASTU_TABLE_PARTIAL[PlotOrientation.NORTH] = {}  # type: ignore


def test_vastu_table_inner_is_immutable():
    """Each inner mapping is MappingProxyType."""
    with pytest.raises(TypeError):
        VASTU_TABLE_PARTIAL[PlotOrientation.NORTH][FunctionRole.LIVING] = 0.0  # type: ignore


# ─── Signature placements (per SPEC § 4.1.4) ──────────────────────────────


def test_signature_ne_pooja_max():
    """NE / POOJA = 1.0 (Ishaan kona)."""
    assert VASTU_TABLE_PARTIAL[PlotOrientation.NORTHEAST][FunctionRole.POOJA] == 1.0


def test_signature_se_kitchen_max():
    """SE / KITCHEN = 1.0 (Agni kona)."""
    assert VASTU_TABLE_PARTIAL[PlotOrientation.SOUTHEAST][FunctionRole.KITCHEN] == 1.0


def test_signature_sw_bedroom_max():
    """SW / BEDROOM = 1.0 (master Nairutya)."""
    assert VASTU_TABLE_PARTIAL[PlotOrientation.SOUTHWEST][FunctionRole.BEDROOM] == 1.0


def test_signature_ne_wet_area_zero():
    """NE / WET_AREA = 0.0 (avoid wet at Ishaan kona)."""
    assert VASTU_TABLE_PARTIAL[PlotOrientation.NORTHEAST][FunctionRole.WET_AREA] == 0.0


# ─── adjacent_intercardinals ──────────────────────────────────────────────


def test_adjacent_intercardinals_north():
    """North's neighbours: CCW=NW, CW=NE."""
    ccw, cw = adjacent_intercardinals(PlotOrientation.NORTH)
    assert ccw == PlotOrientation.NORTHWEST
    assert cw == PlotOrientation.NORTHEAST


def test_adjacent_intercardinals_east():
    """East's neighbours: CCW=NE, CW=SE."""
    ccw, cw = adjacent_intercardinals(PlotOrientation.EAST)
    assert ccw == PlotOrientation.NORTHEAST
    assert cw == PlotOrientation.SOUTHEAST


def test_adjacent_intercardinals_south():
    """South's neighbours: CCW=SE, CW=SW."""
    ccw, cw = adjacent_intercardinals(PlotOrientation.SOUTH)
    assert ccw == PlotOrientation.SOUTHEAST
    assert cw == PlotOrientation.SOUTHWEST


def test_adjacent_intercardinals_west():
    """West's neighbours: CCW=SW, CW=NW."""
    ccw, cw = adjacent_intercardinals(PlotOrientation.WEST)
    assert ccw == PlotOrientation.SOUTHWEST
    assert cw == PlotOrientation.NORTHWEST


@pytest.mark.parametrize("intercardinal", [
    PlotOrientation.NORTHEAST, PlotOrientation.SOUTHEAST,
    PlotOrientation.SOUTHWEST, PlotOrientation.NORTHWEST,
])
def test_adjacent_intercardinals_rejects_intercardinal(intercardinal):
    """Function only accepts cardinals."""
    with pytest.raises(ValueError, match=r"cardinal PlotOrientation"):
        adjacent_intercardinals(intercardinal)


def test_adjacent_intercardinals_returns_tuple():
    """Return type is a 2-tuple."""
    out = adjacent_intercardinals(PlotOrientation.NORTH)
    assert isinstance(out, tuple)
    assert len(out) == 2


# ─── vastu_score_4dir tier semantics ──────────────────────────────────────


def test_vastu_score_off_tier_returns_zero():
    """OFF tier returns 0.0 regardless of (cardinal, function)."""
    assert vastu_score_4dir(
        PlotOrientation.NORTH, FunctionRole.LIVING, VastuTier.OFF,
    ) == 0.0


def test_vastu_score_off_tier_returns_zero_for_signature_cell():
    """OFF tier returns 0.0 even for the strongest cells."""
    # SOUTHWEST/BEDROOM is the strongest signature; aggregated cardinal would
    # be SOUTH or WEST.
    assert vastu_score_4dir(
        PlotOrientation.SOUTH, FunctionRole.BEDROOM, VastuTier.OFF,
    ) == 0.0


def test_vastu_score_full_tier_raises_b099():
    """FULL tier deferred — raises NotImplementedError mentioning B-099."""
    with pytest.raises(NotImplementedError, match=r"B-099"):
        vastu_score_4dir(
            PlotOrientation.NORTH, FunctionRole.LIVING, VastuTier.FULL,
        )


def test_vastu_score_partial_returns_aggregated_value():
    """PARTIAL aggregates 8-dir → 4-dir via weighted average."""
    # NORTH/POOJA: 1.0×N[POOJA] + 0.5×NW[POOJA] + 0.5×NE[POOJA] / 2.0
    # = (1.0×0.7 + 0.5×0.3 + 0.5×1.0) / 2.0
    # = (0.7 + 0.15 + 0.5) / 2.0
    # = 1.35 / 2.0 = 0.675
    score = vastu_score_4dir(
        PlotOrientation.NORTH, FunctionRole.POOJA, VastuTier.PARTIAL,
    )
    assert score == pytest.approx(0.675)


def test_vastu_score_partial_east_kitchen():
    """EAST/KITCHEN aggregation cross-checks SE signature contribution.

    EAST/KITCHEN = (1.0×0.5 + 0.5×NE[KITCHEN]=0.1 + 0.5×SE[KITCHEN]=1.0) / 2.0
                 = (0.5 + 0.05 + 0.5) / 2.0
                 = 1.05 / 2.0 = 0.525
    """
    score = vastu_score_4dir(
        PlotOrientation.EAST, FunctionRole.KITCHEN, VastuTier.PARTIAL,
    )
    assert score == pytest.approx(0.525)


def test_vastu_score_partial_west_utility_high():
    """WEST/UTILITY aggregation: NW utility = 0.9 raises the WEST cardinal."""
    # WEST/UTILITY = (1.0×0.85 + 0.5×SW[UTILITY]=0.7 + 0.5×NW[UTILITY]=0.9) / 2.0
    #              = (0.85 + 0.35 + 0.45) / 2.0
    #              = 1.65 / 2.0 = 0.825
    score = vastu_score_4dir(
        PlotOrientation.WEST, FunctionRole.UTILITY, VastuTier.PARTIAL,
    )
    assert score == pytest.approx(0.825)


@pytest.mark.parametrize("cardinal", [
    PlotOrientation.NORTH, PlotOrientation.EAST,
    PlotOrientation.SOUTH, PlotOrientation.WEST,
])
@pytest.mark.parametrize("function", list(FunctionRole))
def test_vastu_score_partial_all_cardinals_all_functions_in_range(cardinal, function):
    """Aggregated PARTIAL score in [0, 1.5] (intermediate); but spec contract
    expects [0, ~1] in practice. Test at minimum that the function never
    raises and returns a finite non-negative number."""
    score = vastu_score_4dir(cardinal, function, VastuTier.PARTIAL)
    assert 0.0 <= score
    # Aggregation formula upper bound: max value 1.0 across all 3 contributing
    # cells = (1.0*1.0 + 0.5*1.0 + 0.5*1.0) / 2.0 = 1.0. So bounded above by 1.0.
    assert score <= 1.0 + 1e-9


def test_vastu_score_rejects_intercardinal_in_partial():
    """PARTIAL tier rejects intercardinal direction (cardinal-only contract)."""
    with pytest.raises(ValueError, match=r"cardinal PlotOrientation"):
        vastu_score_4dir(
            PlotOrientation.NORTHEAST, FunctionRole.LIVING, VastuTier.PARTIAL,
        )


def test_vastu_score_rejects_non_vastu_tier():
    """tier must be a VastuTier instance (TypeError on string, etc.)."""
    with pytest.raises(TypeError, match=r"tier must be VastuTier"):
        vastu_score_4dir(
            PlotOrientation.NORTH, FunctionRole.LIVING, "PARTIAL",  # type: ignore
        )


def test_vastu_score_partial_pooja_north_higher_than_pooja_south():
    """NORTH/POOJA aggregation (with NW=0.3 + NE=1.0 neighbors) is high.

    Sanity check: NORTH is the dominant cardinal for POOJA after aggregation
    (NE signature 1.0 boosts NORTH and EAST equally, but NORTH's own value
    of 0.7 dominates SOUTH's 0.2).
    """
    n_pooja = vastu_score_4dir(
        PlotOrientation.NORTH, FunctionRole.POOJA, VastuTier.PARTIAL,
    )
    s_pooja = vastu_score_4dir(
        PlotOrientation.SOUTH, FunctionRole.POOJA, VastuTier.PARTIAL,
    )
    assert n_pooja > s_pooja


def test_vastu_score_partial_north_bedroom_actual_value():
    """Pin actual computed value for NORTH/BEDROOM (smoothed aggregation).

    NORTH/BEDROOM = (1.0×0.6 + 0.5×NW[BEDROOM]=0.6 + 0.5×NE[BEDROOM]=0.5) / 2.0
                  = (0.6 + 0.3 + 0.25) / 2.0
                  = 0.575
    """
    score = vastu_score_4dir(
        PlotOrientation.NORTH, FunctionRole.BEDROOM, VastuTier.PARTIAL,
    )
    assert score == pytest.approx(0.575)


def test_vastu_score_partial_south_bedroom_actual_value():
    """Pin actual computed value for SOUTH/BEDROOM after aggregation smoothing.

    SOUTH/BEDROOM = (1.0×0.4 + 0.5×SE[BEDROOM]=0.4 + 0.5×SW[BEDROOM]=1.0) / 2.0
                  = (0.4 + 0.2 + 0.5) / 2.0
                  = 0.55

    Note: even though SW/BEDROOM is the signature 1.0, SOUTH cardinal
    aggregates to a LOWER value than NORTH (0.575) because NW/BEDROOM=0.6
    boosts NORTH while SE/BEDROOM=0.4 drags SOUTH down. This is an
    intentional smoothing property of weighted-avg aggregation per § 4.1.4.
    """
    score = vastu_score_4dir(
        PlotOrientation.SOUTH, FunctionRole.BEDROOM, VastuTier.PARTIAL,
    )
    assert score == pytest.approx(0.55)


def test_vastu_score_partial_kitchen_west_higher_than_east_after_aggregation():
    """WEST/KITCHEN > EAST/KITCHEN after aggregation despite SE/KITCHEN signature.

    EAST/KITCHEN = (1.0×0.5 + 0.5×0.1 + 0.5×1.0) / 2.0 = 0.525
    WEST/KITCHEN = (1.0×0.6 + 0.5×0.4 + 0.5×0.7) / 2.0 = 0.575

    NW/KITCHEN = 0.7 lifts WEST above EAST. Documents the smoothing property.
    """
    e_kit = vastu_score_4dir(
        PlotOrientation.EAST, FunctionRole.KITCHEN, VastuTier.PARTIAL,
    )
    w_kit = vastu_score_4dir(
        PlotOrientation.WEST, FunctionRole.KITCHEN, VastuTier.PARTIAL,
    )
    assert w_kit > e_kit
