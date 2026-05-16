"""
BuildemUp — Component 14 — Sub 2 tests
========================================

Phase α (graph_construction) and Phase β (node_metrics).

Per C14 SPEC v0.2 LOCKED § 3 + v0.2 A2 (Inv E3' EXTERNAL exclusion
BOTH sides) + § 3.5 (Brandes betweenness SKETCH).

Sub 2 target: ~20 tests. Covers:

Phase α:
- Happy path (4-room hub-and-spoke)
- EXTERNAL exclusion when EXTERNAL is room_b_id (the v0.1 had this)
- EXTERNAL exclusion when EXTERNAL is room_a_id (the v0.2 A2 critique
  case — what v0.1 would have missed)
- EXTERNAL on either side filtered, edges still canonical
- primary_edges ⊆ edges; canonicalization handles either-orientation
  primary_door_ids
- main_entry_room_id not in placed_room_ids → EntryRoomNotFoundError
- Defensive: non-tuple inputs raise GraphInconsistencyError
- Single-room layout (zero doors → zero edges)
- Door with endpoint not in placed_room_ids → contract drift error
- Duplicate doors on same edge collapse to one edge
- Deterministic: same input → same output

Phase β:
- BFS step-depth correctness on linear chain (entry → A → B → C)
- BFS step-depth correctness on hub-and-spoke (every spoke at depth 2
  through hub at depth 1)
- Main entry at depth 0 (Inv E6)
- Connectivity = node degree (matches adjacency)
- Betweenness rank on linear chain: middle ranks higher than ends
- Betweenness rank on star: hub ranks #1, all spokes tied
- Lex-ASC tie-breaking on ranks
- 1-node graph: depth 0, connectivity 0, rank 1
- main_entry not in nodes → GraphInconsistencyError
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from buildemup.components.c14 import (
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
    EntryRoomNotFoundError,
    GraphInconsistencyError,
    GraphTopology,
    NodeMetrics,
    compute_node_metrics,
    construct_graph_topology,
)


# =============================================================================
# Door stub (structural-typing compatible with _DoorLike)
# =============================================================================

@dataclass(frozen=True)
class _StubDoor:
    """Minimal door for Phase α tests. Mirrors C13's
    canonical-order invariant (room_a < room_b) but does NOT enforce
    it — some tests deliberately violate the canonical order to verify
    Phase α's defensive normalization."""
    room_a_id: str
    room_b_id: str


def _door(a: str, b: str) -> _StubDoor:
    """Build a door without enforcing a < b (Phase α should normalize)."""
    return _StubDoor(room_a_id=a, room_b_id=b)


# =============================================================================
# 1. Phase α — happy paths
# =============================================================================

def test_phase_alpha_single_room_zero_edges():
    """1-room layout: nodes = (room,), edges = (), primary_edges = ()."""
    t = construct_graph_topology(
        doors=(),
        placed_room_ids=("entry_01",),
        primary_door_ids=frozenset(),
        main_entry_room_id="entry_01",
    )
    assert t.nodes == ("entry_01",)
    assert t.edges == ()
    assert t.primary_edges == ()


def test_phase_alpha_hub_and_spoke_4_rooms():
    """Living = hub; entry, kitchen, bedroom each connect only to living."""
    doors = (
        _door("entry_01", "living_01"),
        _door("kitchen_01", "living_01"),
        _door("bedroom_01", "living_01"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("entry_01", "living_01", "kitchen_01", "bedroom_01"),
        primary_door_ids=frozenset({
            ("entry_01", "living_01"),
            ("kitchen_01", "living_01"),
            ("bedroom_01", "living_01"),
        }),
        main_entry_room_id="entry_01",
    )
    # Nodes lex-ASC
    assert t.nodes == ("bedroom_01", "entry_01", "kitchen_01", "living_01")
    # Edges lex-ASC + all primary
    assert t.edges == (
        ("bedroom_01", "living_01"),
        ("entry_01", "living_01"),
        ("kitchen_01", "living_01"),
    )
    assert t.primary_edges == t.edges


def test_phase_alpha_normalizes_reversed_door_orientation():
    """Even though C13 enforces a < b on Door, Phase α uses defensive
    normalization. A door given as ('z', 'a') still produces edge
    ('a', 'z')."""
    doors = (_door("zoom_01", "alpha_01"),)  # b < a, swapped
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("alpha_01", "zoom_01"),
        primary_door_ids=frozenset(),
        main_entry_room_id="alpha_01",
    )
    assert t.edges == (("alpha_01", "zoom_01"),)


# =============================================================================
# 2. Phase α — EXTERNAL exclusion (v0.2 A2 Inv E3' — BOTH sides)
# =============================================================================

def test_phase_alpha_excludes_external_when_room_b():
    """The v0.1 case: door is (main_entry, EXTERNAL). EXTERNAL is room_b
    because lowercase 'm' (0x6D) > uppercase 'E' (0x45), wait — actually
    that means EXTERNAL < main_entry lex, so EXTERNAL should be room_a.
    Use a room id starting with a non-letter or digit to be safe.

    To make EXTERNAL be room_b: pair it with a room id that sorts AFTER
    'EXTERNAL'. 'main_entry' (lowercase 'm', 0x6D) > 'EXTERNAL'
    (uppercase 'E', 0x45) lex — so canonical (a,b) = ('EXTERNAL', 'main_entry').
    To force EXTERNAL into room_b position, use a partner starting BEFORE
    'EXTERNAL' lex, e.g. 'AAA_room'.
    """
    EXT = EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID
    # 'AAA_room' < 'EXTERNAL' lex (uppercase A 0x41 < uppercase E 0x45)
    doors = (
        _door("AAA_room", EXT),
        _door("AAA_room", "interior_01"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("AAA_room", "interior_01"),
        primary_door_ids=frozenset(),
        main_entry_room_id="AAA_room",
    )
    # EXTERNAL door is filtered; only the interior door remains.
    assert t.edges == (("AAA_room", "interior_01"),)


def test_phase_alpha_excludes_external_when_room_a():
    """The v0.2 A2 critique-walk case: EXTERNAL is room_a (because
    uppercase 'E' < lowercase letters lex). v0.1's single-side check
    would have missed this. v0.2 catches it via _is_external_edge
    checking BOTH sides.

    'EXTERNAL' (uppercase, 0x45) < 'main_entry' (lowercase, 0x6D) lex,
    so canonical edge is ('EXTERNAL', 'main_entry') with EXTERNAL as
    room_a.
    """
    EXT = EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID
    doors = (
        _door(EXT, "main_entry"),  # EXTERNAL on either input position
        _door("main_entry", "living"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("living", "main_entry"),
        primary_door_ids=frozenset(),
        main_entry_room_id="main_entry",
    )
    # The EXTERNAL door dropped despite EXTERNAL being lex-first.
    assert t.edges == (("living", "main_entry"),)


def test_phase_alpha_excludes_external_input_order_swapped():
    """Defensive: even if a malformed door has EXTERNAL as input
    room_a_id (despite the canonical contract saying it should be lex
    secondary), Phase α still drops it. This protects against any
    upstream that doesn't canonicalize doors properly."""
    EXT = EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID
    # Both orientations should drop
    doors = (
        _door(EXT, "room_01"),
        _door("room_02", EXT),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("room_01", "room_02"),
        primary_door_ids=frozenset(),
        main_entry_room_id="room_01",
    )
    assert t.edges == ()


# =============================================================================
# 3. Phase α — primary_edges
# =============================================================================

def test_phase_alpha_primary_edges_subset_of_edges():
    doors = (
        _door("entry_01", "living_01"),
        _door("kitchen_01", "living_01"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("entry_01", "kitchen_01", "living_01"),
        primary_door_ids=frozenset({("entry_01", "living_01")}),
        main_entry_room_id="entry_01",
    )
    assert t.primary_edges == (("entry_01", "living_01"),)
    # Subset relation
    assert set(t.primary_edges).issubset(set(t.edges))


def test_phase_alpha_primary_edges_normalized():
    """primary_door_ids passed in either orientation should be
    canonicalized by Phase α before subset check."""
    doors = (_door("aa", "zz"),)
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("aa", "zz"),
        primary_door_ids=frozenset({("zz", "aa")}),  # reversed
        main_entry_room_id="aa",
    )
    # Should still match — canonicalized to ('aa', 'zz').
    assert t.primary_edges == (("aa", "zz"),)


# =============================================================================
# 4. Phase α — defensive
# =============================================================================

def test_phase_alpha_entry_not_in_placed_rooms_raises():
    with pytest.raises(EntryRoomNotFoundError):
        construct_graph_topology(
            doors=(),
            placed_room_ids=("room_a",),
            primary_door_ids=frozenset(),
            main_entry_room_id="room_b",  # not in placed
        )


def test_phase_alpha_door_endpoint_not_in_placed_rooms_raises():
    """Contract drift: a door references a room not in placed_room_ids."""
    doors = (_door("room_a", "ghost_room"),)
    with pytest.raises(GraphInconsistencyError, match="not in placed_room_ids"):
        construct_graph_topology(
            doors=doors,
            placed_room_ids=("room_a",),  # no ghost_room
            primary_door_ids=frozenset(),
            main_entry_room_id="room_a",
        )


def test_phase_alpha_non_tuple_doors_raises():
    with pytest.raises(GraphInconsistencyError, match="doors must be a tuple"):
        construct_graph_topology(
            doors=[],  # type: ignore[arg-type]
            placed_room_ids=("a",),
            primary_door_ids=frozenset(),
            main_entry_room_id="a",
        )


def test_phase_alpha_duplicate_doors_collapse_to_one_edge():
    """Two doors on the same room pair → one edge (set semantics).

    Per C13 a room pair typically has 1 door, but no contract forbids
    multiple. C14 treats the adjacency relation, not the count of doors.
    """
    doors = (
        _door("a", "b"),
        _door("a", "b"),  # duplicate
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("a", "b"),
        primary_door_ids=frozenset(),
        main_entry_room_id="a",
    )
    assert t.edges == (("a", "b"),)


def test_phase_alpha_deterministic_replay():
    """Same input → byte-equal output (Inv E7)."""
    doors = (
        _door("kitchen", "living"),
        _door("entry", "living"),
        _door("bedroom", "living"),
    )
    rooms = ("entry", "living", "bedroom", "kitchen")
    primaries = frozenset({("entry", "living")})
    t1 = construct_graph_topology(
        doors=doors,
        placed_room_ids=rooms,
        primary_door_ids=primaries,
        main_entry_room_id="entry",
    )
    t2 = construct_graph_topology(
        doors=doors,
        placed_room_ids=rooms,
        primary_door_ids=primaries,
        main_entry_room_id="entry",
    )
    assert t1 == t2


# =============================================================================
# 5. Phase β — BFS step-depth
# =============================================================================

def test_phase_beta_single_node_depth_zero():
    t = construct_graph_topology(
        doors=(),
        placed_room_ids=("solo",),
        primary_door_ids=frozenset(),
        main_entry_room_id="solo",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="solo")
    assert m.step_depth_from_entry == (("solo", 0),)
    assert m.connectivity == (("solo", 0),)


def test_phase_beta_linear_chain_depths():
    """entry — A — B — C: depths 0, 1, 2, 3."""
    doors = (
        _door("A", "entry"),
        _door("A", "B"),
        _door("B", "C"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("entry", "A", "B", "C"),
        primary_door_ids=frozenset(),
        main_entry_room_id="entry",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="entry")
    depths = dict(m.step_depth_from_entry)
    assert depths == {"entry": 0, "A": 1, "B": 2, "C": 3}


def test_phase_beta_hub_and_spoke_depths():
    """Entry → living(hub) → kitchen / bedroom. Spokes at depth 2."""
    doors = (
        _door("entry", "living"),
        _door("kitchen", "living"),
        _door("bedroom", "living"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("entry", "living", "kitchen", "bedroom"),
        primary_door_ids=frozenset(),
        main_entry_room_id="entry",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="entry")
    depths = dict(m.step_depth_from_entry)
    assert depths == {"entry": 0, "living": 1, "kitchen": 2, "bedroom": 2}


def test_phase_beta_disconnected_graph_raises():
    """Inv E15 contract drift: BFS doesn't reach every node."""
    doors = (_door("a", "b"),)  # a-b connected; c isolated
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("a", "b", "c"),
        primary_door_ids=frozenset(),
        main_entry_room_id="a",
    )
    with pytest.raises(GraphInconsistencyError, match="E15"):
        compute_node_metrics(topology=t, main_entry_room_id="a")


def test_phase_beta_main_entry_not_in_nodes_raises():
    t = construct_graph_topology(
        doors=(),
        placed_room_ids=("a",),
        primary_door_ids=frozenset(),
        main_entry_room_id="a",
    )
    with pytest.raises(GraphInconsistencyError, match="not in topology.nodes"):
        compute_node_metrics(topology=t, main_entry_room_id="ghost")


# =============================================================================
# 6. Phase β — connectivity (degree)
# =============================================================================

def test_phase_beta_connectivity_matches_degree():
    """Hub-and-spoke: hub degree = #spokes; each spoke degree = 1."""
    doors = (
        _door("entry", "living"),
        _door("kitchen", "living"),
        _door("bedroom", "living"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("entry", "living", "kitchen", "bedroom"),
        primary_door_ids=frozenset(),
        main_entry_room_id="entry",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="entry")
    conn = dict(m.connectivity)
    assert conn == {"entry": 1, "living": 3, "kitchen": 1, "bedroom": 1}


# =============================================================================
# 7. Phase β — betweenness rank
# =============================================================================

def test_phase_beta_betweenness_linear_chain():
    """A — B — C — D — E (5 nodes linear). Middle (C) is the chokepoint.

    By Brandes betweenness for a 5-node path: C has the highest
    betweenness (rank 1), then B/D tied, then A/E tied at the ends.

    Per the SKETCH formula's lex-ASC tie-break: B should rank 2, D
    rank 3 (B < D lex), A rank 4, E rank 5 (A < E lex).
    """
    doors = (
        _door("A", "B"),
        _door("B", "C"),
        _door("C", "D"),
        _door("D", "E"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("A", "B", "C", "D", "E"),
        primary_door_ids=frozenset(),
        main_entry_room_id="A",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="A")
    ranks = dict(m.betweenness_rank)
    # C is the most-bottlenecked.
    assert ranks["C"] == 1
    # B and D are tied for second-highest betweenness. Lex tie-break:
    # B (rank 2) before D (rank 3).
    assert ranks["B"] == 2
    assert ranks["D"] == 3
    # A and E are tied at zero (leaves of the path). Lex tie-break.
    assert ranks["A"] == 4
    assert ranks["E"] == 5


def test_phase_beta_betweenness_hub_rank_one():
    """Hub-and-spoke: hub ranks #1, all spokes tied (betweenness=0).

    Spokes lex-ASC: bedroom, entry, kitchen → ranks 2, 3, 4.
    """
    doors = (
        _door("entry", "living"),
        _door("kitchen", "living"),
        _door("bedroom", "living"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("entry", "living", "kitchen", "bedroom"),
        primary_door_ids=frozenset(),
        main_entry_room_id="entry",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="entry")
    ranks = dict(m.betweenness_rank)
    assert ranks["living"] == 1
    # Spokes all betweenness=0; lex-ASC tie-break: bedroom, entry, kitchen.
    assert ranks["bedroom"] == 2
    assert ranks["entry"] == 3
    assert ranks["kitchen"] == 4


def test_phase_beta_betweenness_ranks_unique_and_cover_one_to_k():
    """Inv at the schema level (E5 + betweenness_rank range): every rank
    is in [1, k] and each rank is unique (a permutation of 1..k)."""
    doors = (
        _door("A", "B"),
        _door("B", "C"),
        _door("C", "D"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("A", "B", "C", "D"),
        primary_door_ids=frozenset(),
        main_entry_room_id="A",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="A")
    ranks = sorted(r for _, r in m.betweenness_rank)
    assert ranks == [1, 2, 3, 4]


def test_phase_beta_metric_tuples_lex_sorted_by_room_id():
    """Inv E5: all three tuples covered nodes lex-ASC."""
    doors = (
        _door("zebra", "alpha"),
        _door("alpha", "monkey"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("zebra", "alpha", "monkey"),
        primary_door_ids=frozenset(),
        main_entry_room_id="alpha",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="alpha")
    for tup in (m.step_depth_from_entry, m.connectivity, m.betweenness_rank):
        keys = [r for r, _ in tup]
        assert keys == sorted(keys)
        assert keys == ["alpha", "monkey", "zebra"]


def test_phase_beta_deterministic_replay():
    """Same input → byte-equal NodeMetrics (Inv E7)."""
    doors = (
        _door("a", "b"),
        _door("b", "c"),
        _door("c", "d"),
        _door("a", "c"),  # introduces a shortest-path tie via Brandes
    )
    rooms = ("a", "b", "c", "d")
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=rooms,
        primary_door_ids=frozenset(),
        main_entry_room_id="a",
    )
    m1 = compute_node_metrics(topology=t, main_entry_room_id="a")
    m2 = compute_node_metrics(topology=t, main_entry_room_id="a")
    assert m1 == m2


def test_phase_beta_triangle_all_tied():
    """3-node triangle: every node has betweenness = 0 (every pair has
    a direct edge → no shortest path uses an intermediary)."""
    doors = (
        _door("a", "b"),
        _door("b", "c"),
        _door("a", "c"),
    )
    t = construct_graph_topology(
        doors=doors,
        placed_room_ids=("a", "b", "c"),
        primary_door_ids=frozenset(),
        main_entry_room_id="a",
    )
    m = compute_node_metrics(topology=t, main_entry_room_id="a")
    ranks = dict(m.betweenness_rank)
    # Lex-ASC tie-break (all zero betweenness): a=1, b=2, c=3.
    assert ranks == {"a": 1, "b": 2, "c": 3}
