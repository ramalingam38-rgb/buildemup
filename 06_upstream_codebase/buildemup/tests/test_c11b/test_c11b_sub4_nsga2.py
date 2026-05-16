"""Sub-4 tests: NSGA-II core — fast non-dominated sort, CDP dominance,
crowding distance, deterministic survivor selection with W6-3 tie-break."""
from __future__ import annotations

import math
from dataclasses import replace

import pytest

from buildemup.components.c11b import (
    ObjectiveVector,
    OperatorClass,
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
)
from buildemup.components.c11b.nsga2.crowding import assign_crowding_distance
from buildemup.components.c11b.nsga2.dominance import (
    dominates_cdp,
    fast_non_dominated_sort,
)
from buildemup.components.c11b.nsga2.selection import _tiebreak_key, select_survivors


def _params(*tuples):
    return RefinedParameters(
        room_dimensions=tuple(
            RoomDimension(room_id=rid, width_m=w, depth_m=d) for rid, w, d in tuples
        )
    )


def _cand(values, cv=0.0, sig="sig", rp=None) -> RefinedCandidate:
    """Helper: build a RefinedCandidate carrying the given objective values."""
    if rp is None:
        rp = _params(("r0", 3.0, 4.0))
    cand = RefinedCandidate.from_operator_class(
        OperatorClass.M0_BASE, rp, sig
    )
    return replace(
        cand,
        objective_vector=ObjectiveVector(
            values=tuple((f"o{i}", v) for i, v in enumerate(values)),
            constraint_violations=cv,
        ),
    )


# ── CDP dominance rules ────────────────────────────────────────────────


def test_cdp_feasible_dominates_infeasible():
    a = _cand([5.0, 5.0], cv=0.0)
    b = _cand([1.0, 1.0], cv=0.5)  # better objectives but infeasible
    assert dominates_cdp(a, b)
    assert not dominates_cdp(b, a)


def test_cdp_both_infeasible_lower_violation_dominates():
    a = _cand([5.0, 5.0], cv=0.2)
    b = _cand([1.0, 1.0], cv=0.5)
    assert dominates_cdp(a, b)
    assert not dominates_cdp(b, a)


def test_cdp_both_infeasible_equal_violations_neither_dominates():
    a = _cand([5.0, 5.0], cv=0.5)
    b = _cand([1.0, 1.0], cv=0.5)
    assert not dominates_cdp(a, b)
    assert not dominates_cdp(b, a)


def test_cdp_both_feasible_standard_pareto():
    a = _cand([1.0, 1.0])
    b = _cand([2.0, 2.0])
    assert dominates_cdp(a, b)
    assert not dominates_cdp(b, a)


def test_cdp_no_dominance_on_trade_off():
    a = _cand([1.0, 5.0])
    b = _cand([5.0, 1.0])
    assert not dominates_cdp(a, b)
    assert not dominates_cdp(b, a)


def test_cdp_strict_dominance_requires_at_least_one_better():
    a = _cand([1.0, 1.0])
    b = _cand([1.0, 1.0])
    assert not dominates_cdp(a, b)
    assert not dominates_cdp(b, a)


def test_cdp_none_objective_vector_returns_false():
    a = RefinedCandidate.from_operator_class(
        OperatorClass.M0_BASE, _params(("r0", 3.0, 4.0)), "s"
    )
    b = _cand([1.0, 1.0])
    assert not dominates_cdp(a, b)
    assert not dominates_cdp(b, a)


# ── fast non-dominated sort ────────────────────────────────────────────


def test_fast_non_dominated_sort_single_front():
    """All trade-off candidates form front 0."""
    pop = (
        _cand([1.0, 5.0], sig="a"),
        _cand([3.0, 3.0], sig="b"),
        _cand([5.0, 1.0], sig="c"),
    )
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 1
    assert set(fronts[0]) == {0, 1, 2}


def test_fast_non_dominated_sort_two_fronts():
    pop = (
        _cand([1.0, 1.0], sig="best"),
        _cand([5.0, 5.0], sig="worst_a"),
        _cand([6.0, 6.0], sig="worst_b"),
    )
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) >= 2
    assert 0 in fronts[0]
    # worst_a + worst_b dominated by best.
    later = set()
    for f in fronts[1:]:
        later.update(f)
    assert later == {1, 2}


def test_fast_non_dominated_sort_pure_pareto():
    """Five strictly trade-off candidates → 1 front."""
    pop = tuple(_cand([float(i), float(5 - i)], sig=f"s{i}") for i in range(5))
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 1
    assert len(fronts[0]) == 5


# ── crowding distance ──────────────────────────────────────────────────


def test_crowding_extremes_are_infinite():
    pop = (
        _cand([1.0, 5.0], sig="a"),
        _cand([3.0, 3.0], sig="b"),
        _cand([5.0, 1.0], sig="c"),
    )
    crowding = assign_crowding_distance(pop, (0, 1, 2))
    # Extremes on at least one objective → inf.
    assert math.isinf(crowding[0])
    assert math.isinf(crowding[2])


def test_crowding_middle_finite():
    pop = (
        _cand([1.0, 5.0], sig="a"),
        _cand([3.0, 3.0], sig="b"),
        _cand([5.0, 1.0], sig="c"),
    )
    crowding = assign_crowding_distance(pop, (0, 1, 2))
    assert math.isfinite(crowding[1])
    assert crowding[1] >= 0.0


def test_crowding_size_2_or_less_all_infinite():
    pop = (_cand([1.0, 5.0], sig="a"), _cand([5.0, 1.0], sig="b"))
    crowding = assign_crowding_distance(pop, (0, 1))
    assert math.isinf(crowding[0])
    assert math.isinf(crowding[1])


# ── deterministic tie-break (W6-3 + W5-12) ─────────────────────────────


def test_tiebreak_key_layer_1_signature():
    c1 = _cand([1.0, 1.0], sig="aaa")
    c2 = _cand([1.0, 1.0], sig="bbb")
    k1 = _tiebreak_key(c1, 0)
    k2 = _tiebreak_key(c2, 0)
    assert k1 < k2  # lex-ASC by signature


def test_tiebreak_key_layer_3_index_fallback():
    """Same signature, same params → layer-3 candidate_index breaks ties."""
    rp = _params(("r0", 3.0, 4.0))
    c1 = _cand([1.0, 1.0], sig="same", rp=rp)
    c2 = _cand([1.0, 1.0], sig="same", rp=rp)
    k1 = _tiebreak_key(c1, 5)
    k2 = _tiebreak_key(c2, 7)
    assert k1 < k2  # 5 < 7


def test_select_survivors_deterministic_across_runs():
    """Same input population → same output population."""
    pop = (
        _cand([1.0, 5.0], sig="a"),
        _cand([3.0, 3.0], sig="b"),
        _cand([5.0, 1.0], sig="c"),
        _cand([4.0, 4.0], sig="d"),
    )
    out1 = select_survivors(pop, pop_size=2)
    out2 = select_survivors(pop, pop_size=2)
    sigs1 = [c.source_topology_candidate_signature for c in out1]
    sigs2 = [c.source_topology_candidate_signature for c in out2]
    assert sigs1 == sigs2


def test_select_survivors_respects_pop_size():
    pop = tuple(_cand([float(i), float(10 - i)], sig=f"s{i}") for i in range(10))
    out = select_survivors(pop, pop_size=3)
    assert len(out) == 3


def test_select_survivors_rank_takes_precedence():
    """Front-0 candidates win over higher-rank ones."""
    pop = (
        _cand([1.0, 1.0], sig="best"),  # front 0
        _cand([10.0, 10.0], sig="worst"),  # front 1
    )
    out = select_survivors(pop, pop_size=1)
    assert out[0].source_topology_candidate_signature == "best"
    assert out[0].pareto_rank == 0


def test_select_survivors_populates_rank_and_crowding():
    pop = (
        _cand([1.0, 5.0], sig="a"),
        _cand([3.0, 3.0], sig="b"),
        _cand([5.0, 1.0], sig="c"),
    )
    out = select_survivors(pop, pop_size=3)
    for c in out:
        assert c.pareto_rank == 0  # all front-0


def test_select_survivors_empty_returns_empty():
    assert select_survivors((), pop_size=5) == ()
