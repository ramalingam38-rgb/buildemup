"""
BuildemUp — Component 14 — Sub 3 tests
========================================

Phase γ: layout-level metrics (mean_depth, max_depth, RA, RRA,
integration, graph_size_category).

Per C14 SPEC v0.2 LOCKED § 3 Phase γ + v0.2 A1 + Inv E10/E11'/E11''/
E12'/E17.

Sub 3 target: ~15-20 tests. Covers:

D(k) formula (Krüger & Vieira 2012, web-research-verified):
- D(k) NaN for k < 4
- D(4) = 1/3 exactly (hand-derivable: 2×(4×0+1)/6)
- D monotone-ish: peaks around k=5, decays for large k
- D positive for k ≥ 4

Phase γ on known graph shapes:
- Single node: degenerate but doesn't crash, all NaN for RRA/integration
- 2-node tiny: graph_size_category="tiny", RRA NaN, integration NaN
- 3-node small: graph_size_category="small", RRA NaN (per Inv E11''),
  raw_RA defined
- 4-node star (hand-derivable): MD, raw_RA, real_RA, integration all
  match closed-form arithmetic
- 4-node linear chain (different layout, same k=4): metrics differ
  meaningfully from star
- 5-node "deep" layout vs "shallow" layout: deep produces higher
  mean_depth + raw_RA

Invariant enforcement:
- E10: mean_depth ≤ max_depth ≤ k-1
- E11': raw_RA ≥ 0
- E11'': RRA NaN for k < 4
- E12': integration NaN for k < 4
- E17: category matches k partition

Determinism:
- Same input → same output (no randomness in pure-math path)
- LayoutMetrics is frozen + equality-stable
"""
from __future__ import annotations

import math
from dataclasses import FrozenInstanceError, dataclass

import pytest

from buildemup.components.c14 import (
    GraphTopology,
    LayoutMetrics,
    NodeMetrics,
    compute_layout_metrics,
    compute_node_metrics,
    construct_graph_topology,
)
from buildemup.components.c14.layout_metrics import _diamond_d_value


# =============================================================================
# Door stub (re-used from Sub 2 pattern)
# =============================================================================

@dataclass(frozen=True)
class _StubDoor:
    room_a_id: str
    room_b_id: str


def _door(a: str, b: str) -> _StubDoor:
    return _StubDoor(room_a_id=a, room_b_id=b)


def _pipeline(
    *,
    doors: tuple[_StubDoor, ...],
    placed_room_ids: tuple[str, ...],
    main_entry: str,
) -> LayoutMetrics:
    """Helper: run Phases α → β → γ end-to-end."""
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=placed_room_ids,
        primary_door_ids=frozenset(),
        main_entry_room_id=main_entry,
    )
    m = compute_node_metrics(topology=t, main_entry_room_id=main_entry)
    return compute_layout_metrics(
        node_metrics=m, main_entry_room_id=main_entry, nodes=t.nodes
    )


# =============================================================================
# 1. D(k) formula (Krüger & Vieira 2012)
# =============================================================================

def test_d_value_nan_for_k_below_4():
    """Per Inv E11'': D(k) is undefined / pathological for k < 4."""
    for k in (0, 1, 2, 3):
        assert math.isnan(_diamond_d_value(k))


def test_d_value_at_k_4_is_one_third():
    """Hand-derived: D(4) = 2 × (4 × (log₂(2) − 1) + 1) / (3 × 2)
                          = 2 × (4 × 0 + 1) / 6
                          = 1/3 exactly.

    log₂(6/3) = log₂(2) = 1, so the inner term is (1 − 1) = 0.
    """
    assert math.isclose(_diamond_d_value(4), 1.0 / 3.0, rel_tol=1e-12)


def test_d_value_positive_for_k_ge_4():
    """D must be strictly positive for k ≥ 4 so RRA = RA / D is finite."""
    for k in (4, 5, 6, 7, 10, 15, 20):
        d = _diamond_d_value(k)
        assert d > 0.0, f"D({k}) = {d} should be > 0"
        assert math.isfinite(d)


def test_d_value_decays_for_large_k():
    """Per Teklenburg 1993 simulations: D(k) decays as k → ∞ after a
    small-k peak around k=5–6. We assert D(15) < D(5)."""
    assert _diamond_d_value(15) < _diamond_d_value(5)


# =============================================================================
# 2. Phase γ — degenerate small graphs
# =============================================================================

def test_layout_metrics_single_node_all_nan_for_rra_integration():
    """k=1: graph_size_category="tiny"; RRA + integration must be NaN
    (Inv E11'' + E12')."""
    lm = _pipeline(
        doors=(),
        placed_room_ids=("solo",),
        main_entry="solo",
    )
    assert lm.graph_size_category == "tiny"
    assert lm.max_depth == 0
    assert lm.mean_depth == 0.0
    assert math.isnan(lm.real_relative_asymmetry)
    assert math.isnan(lm.integration)


def test_layout_metrics_two_node_tiny_regime():
    """k=2: still tiny. raw_RA may compute (k≥3 not reached → forced 0
    by Phase γ), RRA + integration NaN."""
    doors = (_door("a", "b"),)
    lm = _pipeline(
        doors=doors,
        placed_room_ids=("a", "b"),
        main_entry="a",
    )
    assert lm.graph_size_category == "tiny"
    assert lm.max_depth == 1
    assert lm.mean_depth == 1.0  # one other node at depth 1
    assert lm.raw_relative_asymmetry == 0.0  # forced-zero for k<3
    assert math.isnan(lm.real_relative_asymmetry)
    assert math.isnan(lm.integration)


def test_layout_metrics_three_node_small_regime_raw_ra_defined():
    """k=3: graph_size_category="small". raw_RA is defined by formula
    `2 × (MD − 1) / (k − 2)`. RRA + integration MUST be NaN per Inv
    E11'' (D(3) is degenerate)."""
    # Linear: a — b — c, entry at a → depths [0, 1, 2]
    doors = (_door("a", "b"), _door("b", "c"))
    lm = _pipeline(
        doors=doors,
        placed_room_ids=("a", "b", "c"),
        main_entry="a",
    )
    assert lm.graph_size_category == "small"
    # MD from a = (1+2)/2 = 1.5; RA = 2*(1.5-1)/(3-2) = 1.0
    assert math.isclose(lm.mean_depth, 1.5, rel_tol=1e-12)
    assert math.isclose(lm.raw_relative_asymmetry, 1.0, rel_tol=1e-12)
    assert math.isnan(lm.real_relative_asymmetry)
    assert math.isnan(lm.integration)


# =============================================================================
# 3. Phase γ — hand-derivable 4-node cases
# =============================================================================

def test_layout_metrics_4_node_star_hand_derivable():
    """Star: living = hub at depth 1, three spokes at depth 2 from
    entry (a spoke).

      Entry (depth 0) → Living (depth 1) → {Kitchen, Bedroom} (depth 2)

    Hand check:
      MD(entry) = (1 + 2 + 2) / 3 = 5/3 = 1.6667
      RA(entry) = 2 × (5/3 − 1) / (4 − 2) = 2 × (2/3) / 2 = 2/3 = 0.6667
      D(4) = 1/3
      RRA = (2/3) / (1/3) = 2.0
      integration = 1 / 2 = 0.5
    """
    doors = (
        _door("entry", "living"),
        _door("kitchen", "living"),
        _door("bedroom", "living"),
    )
    lm = _pipeline(
        doors=doors,
        placed_room_ids=("entry", "living", "kitchen", "bedroom"),
        main_entry="entry",
    )
    assert lm.graph_size_category == "normal"
    assert math.isclose(lm.mean_depth, 5.0 / 3.0, rel_tol=1e-12)
    assert lm.max_depth == 2
    assert math.isclose(lm.raw_relative_asymmetry, 2.0 / 3.0, rel_tol=1e-12)
    assert math.isclose(lm.real_relative_asymmetry, 2.0, rel_tol=1e-12)
    assert math.isclose(lm.integration, 0.5, rel_tol=1e-12)


def test_layout_metrics_4_node_linear_chain_hand_derivable():
    """Linear chain: A — B — C — D, entry at A.
    Depths: A=0, B=1, C=2, D=3.

    Hand check:
      MD(A) = (1+2+3)/3 = 6/3 = 2.0
      RA(A) = 2 × (2.0 − 1) / (4 − 2) = 2 × 1.0 / 2 = 1.0
      D(4) = 1/3
      RRA = 1.0 / (1/3) = 3.0
      integration = 1/3 ≈ 0.3333

    Deep linear chain has HIGHER RA than star (3.0 vs 2.0) →
    higher RRA → LOWER integration (less integrated).
    """
    doors = (
        _door("A", "B"),
        _door("B", "C"),
        _door("C", "D"),
    )
    lm = _pipeline(
        doors=doors,
        placed_room_ids=("A", "B", "C", "D"),
        main_entry="A",
    )
    assert math.isclose(lm.mean_depth, 2.0, rel_tol=1e-12)
    assert lm.max_depth == 3
    assert math.isclose(lm.raw_relative_asymmetry, 1.0, rel_tol=1e-12)
    assert math.isclose(lm.real_relative_asymmetry, 3.0, rel_tol=1e-12)
    assert math.isclose(lm.integration, 1.0 / 3.0, rel_tol=1e-12)


def test_layout_metrics_star_more_integrated_than_chain():
    """Same k=4, different topology: star has HIGHER integration
    (lower RRA) than chain. This is the canonical syntactic finding
    Hillier 1984 builds on."""
    star = _pipeline(
        doors=(
            _door("entry", "living"),
            _door("kitchen", "living"),
            _door("bedroom", "living"),
        ),
        placed_room_ids=("entry", "living", "kitchen", "bedroom"),
        main_entry="entry",
    )
    chain = _pipeline(
        doors=(
            _door("A", "B"),
            _door("B", "C"),
            _door("C", "D"),
        ),
        placed_room_ids=("A", "B", "C", "D"),
        main_entry="A",
    )
    # Star is more integrated (higher integration, lower RRA).
    assert star.integration > chain.integration
    assert star.real_relative_asymmetry < chain.real_relative_asymmetry


# =============================================================================
# 4. Invariants enforced by formula
# =============================================================================

def test_layout_metrics_inv_e10_mean_depth_le_max_depth():
    """Inv E10: mean_depth ≤ max_depth ≤ k-1."""
    lm = _pipeline(
        doors=(
            _door("A", "B"),
            _door("B", "C"),
            _door("C", "D"),
            _door("D", "E"),
        ),
        placed_room_ids=("A", "B", "C", "D", "E"),
        main_entry="A",
    )
    assert lm.mean_depth <= lm.max_depth
    assert lm.max_depth <= 5 - 1  # k - 1


def test_layout_metrics_inv_e11_prime_raw_ra_non_negative():
    """Inv E11': raw_RA ≥ 0 for any connected graph."""
    # Try a variety of shapes
    shapes = [
        (("a", "b"), ("a", "b")),
        (("a", "b"), ("b", "c"), ("c", "d")),
        (("hub", "a"), ("hub", "b"), ("hub", "c"), ("hub", "d")),
    ]
    for shape in shapes:
        doors = tuple(_door(*pair) for pair in shape)
        nodes = tuple(sorted({r for pair in shape for r in pair}))
        lm = _pipeline(
            doors=doors,
            placed_room_ids=nodes,
            main_entry=nodes[0],
        )
        assert lm.raw_relative_asymmetry >= 0.0, (
            f"raw_RA negative for shape {shape}: {lm.raw_relative_asymmetry}"
        )


def test_layout_metrics_inv_e17_category_partition():
    """Inv E17: tiny (k≤2) | small (k=3) | normal (k≥4)."""
    # k=2 → tiny
    lm2 = _pipeline(
        doors=(_door("a", "b"),),
        placed_room_ids=("a", "b"),
        main_entry="a",
    )
    assert lm2.graph_size_category == "tiny"

    # k=3 → small
    lm3 = _pipeline(
        doors=(_door("a", "b"), _door("b", "c")),
        placed_room_ids=("a", "b", "c"),
        main_entry="a",
    )
    assert lm3.graph_size_category == "small"

    # k=4 → normal
    lm4 = _pipeline(
        doors=(_door("a", "b"), _door("b", "c"), _door("c", "d")),
        placed_room_ids=("a", "b", "c", "d"),
        main_entry="a",
    )
    assert lm4.graph_size_category == "normal"


def test_layout_metrics_inv_e11_prime_prime_rra_nan_for_k_lt_4():
    """Inv E11'': real_RA must be NaN for k < 4."""
    for placed_rooms, doors in [
        (("a",), ()),
        (("a", "b"), (_door("a", "b"),)),
        (("a", "b", "c"), (_door("a", "b"), _door("b", "c"))),
    ]:
        lm = _pipeline(
            doors=doors, placed_room_ids=placed_rooms, main_entry=placed_rooms[0]
        )
        assert math.isnan(lm.real_relative_asymmetry), (
            f"k={len(placed_rooms)}: real_RA should be NaN"
        )


def test_layout_metrics_inv_e12_prime_integration_nan_for_k_lt_4():
    """Inv E12': integration must be NaN for k < 4."""
    for placed_rooms, doors in [
        (("a",), ()),
        (("a", "b"), (_door("a", "b"),)),
        (("a", "b", "c"), (_door("a", "b"), _door("b", "c"))),
    ]:
        lm = _pipeline(
            doors=doors, placed_room_ids=placed_rooms, main_entry=placed_rooms[0]
        )
        assert math.isnan(lm.integration), (
            f"k={len(placed_rooms)}: integration should be NaN"
        )


# =============================================================================
# 5. Frozen / replay determinism
# =============================================================================

def test_layout_metrics_is_frozen():
    lm = _pipeline(
        doors=(_door("a", "b"), _door("b", "c"), _door("c", "d")),
        placed_room_ids=("a", "b", "c", "d"),
        main_entry="a",
    )
    with pytest.raises(FrozenInstanceError):
        lm.mean_depth = 999.0  # type: ignore[misc]


def test_layout_metrics_deterministic_replay():
    """Same input → byte-equal LayoutMetrics (Inv E7)."""
    doors = (
        _door("a", "b"),
        _door("b", "c"),
        _door("c", "d"),
        _door("a", "c"),
    )
    rooms = ("a", "b", "c", "d")
    lm1 = _pipeline(doors=doors, placed_room_ids=rooms, main_entry="a")
    lm2 = _pipeline(doors=doors, placed_room_ids=rooms, main_entry="a")
    assert lm1 == lm2


# =============================================================================
# 6. Layout-comparison signature ("deep" vs "shallow")
# =============================================================================

def test_layout_metrics_deeper_layout_has_higher_raw_ra():
    """A 5-node linear chain (deep) should have higher raw_RA than a
    5-node hub-and-spoke (shallow), and consequently lower integration.

    Chain A-B-C-D-E from A: MD = (1+2+3+4)/4 = 2.5; RA = 2×(1.5)/3 = 1.0
    Hub h with 4 spokes from a spoke: MD = (1+2+2+2)/4 = 1.75;
      RA = 2×(0.75)/3 = 0.5
    """
    chain = _pipeline(
        doors=(
            _door("A", "B"),
            _door("B", "C"),
            _door("C", "D"),
            _door("D", "E"),
        ),
        placed_room_ids=("A", "B", "C", "D", "E"),
        main_entry="A",
    )
    hub = _pipeline(
        doors=(
            _door("entry", "hub"),
            _door("hub", "r2"),
            _door("hub", "r3"),
            _door("hub", "r4"),
        ),
        placed_room_ids=("entry", "hub", "r2", "r3", "r4"),
        main_entry="entry",
    )
    assert chain.raw_relative_asymmetry > hub.raw_relative_asymmetry
    assert chain.real_relative_asymmetry > hub.real_relative_asymmetry
    assert chain.integration < hub.integration


def test_layout_metrics_4_node_chain_max_depth_is_3():
    """Sanity: chain of 4 has max_depth = 3 (depth from end = k-1)."""
    lm = _pipeline(
        doors=(_door("A", "B"), _door("B", "C"), _door("C", "D")),
        placed_room_ids=("A", "B", "C", "D"),
        main_entry="A",
    )
    assert lm.max_depth == 3
    # And mean_depth = (1+2+3)/3 = 2.0
    assert math.isclose(lm.mean_depth, 2.0, rel_tol=1e-12)
