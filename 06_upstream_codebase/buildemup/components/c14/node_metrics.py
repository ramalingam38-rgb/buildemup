"""
BuildemUp — Component 14 — Phase β: node-level metrics
=======================================================

Per C14 SPEC v0.2 LOCKED § 3 Phase β + § 3.5 (Brandes betweenness
SKETCH) + Inv E7 (byte-equal replay determinism via lex-ASC neighbour
ordering).

Phase β reads the GraphTopology from Phase α plus the
`main_entry_room_id` from upstream metadata, and produces three
per-node metric tuples (each lex-ASC by room_id):

- `step_depth_from_entry`: BFS distance from `main_entry_room_id` to
   every other room. Inv E6: main entry's depth is 0. Inv E5: covers
   nodes exactly.
- `connectivity`: degree of each node in the adjacency graph (per
   v0.1 § 1.3). Inv E5: covers nodes exactly.
- `betweenness_rank`: Brandes-derived raw through-count ranked 1..k
   where rank 1 = highest betweenness. Per § 3.5, v0.1 commits to the
   RANK being deterministic + lex-stable on ties, not to the exact
   value formula. Final formula pinning is
   `B-C14-BETWEENNESS-FORMULA-LOCK` (LOCK-mandatory).

Inv E7 determinism strategy:
- Adjacency lists built sorted lex-ASC by neighbour room_id
- BFS queue uses lex-ASC neighbour ordering (FIFO + sorted neighbours)
- Brandes sources iterated in lex-ASC order
- Rank ties broken by room_id lex-ASC (so rank order is byte-stable
   across runs)

Complexity:
- BFS: O(V + E)
- Connectivity: O(V + E)
- Brandes: O(V × (V + E)) — for residential V ≤ ~15, this is bounded
  at ~3,000 ops, well within the 0.5s per-candidate budget (§ 6).
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from .errors import GraphInconsistencyError
from .graph_construction import GraphTopology


# =============================================================================
# Output: NodeMetrics
# =============================================================================

@dataclass(frozen=True)
class NodeMetrics:
    """Phase β output: the three per-node metric tuples.

    Each tuple is `((room_id, value), ...)` sorted lex-ASC by room_id
    (Inv E5). Frozen for replay determinism.
    """
    step_depth_from_entry: tuple[tuple[str, int], ...]
    connectivity: tuple[tuple[str, int], ...]
    betweenness_rank: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for field_name in (
            "step_depth_from_entry",
            "connectivity",
            "betweenness_rank",
        ):
            metric = getattr(self, field_name)
            room_ids = [r for r, _ in metric]
            if room_ids != sorted(room_ids):
                raise GraphInconsistencyError(
                    f"Phase β: {field_name} must be lex-ASC sorted by "
                    f"room_id; got {room_ids}."
                )


# =============================================================================
# Helpers
# =============================================================================

def _build_adjacency(
    nodes: tuple[str, ...],
    edges: tuple[tuple[str, str], ...],
) -> dict[str, tuple[str, ...]]:
    """Build an adjacency map keyed by room_id → lex-ASC tuple of
    neighbour room_ids.

    Determinism: neighbour tuples are sorted lex-ASC so every consumer
    iterating them produces identical sequences (Inv E7).
    """
    adj: dict[str, set[str]] = {r: set() for r in nodes}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return {r: tuple(sorted(adj[r])) for r in nodes}


# =============================================================================
# BFS step-depth (Inv E6)
# =============================================================================

def _bfs_step_depths(
    *,
    adjacency: dict[str, tuple[str, ...]],
    nodes: tuple[str, ...],
    source: str,
) -> dict[str, int]:
    """BFS from `source`. Returns dict room_id → shortest-path step count.

    Per Inv E6 + § 3 Phase β: source depth is 0. Per Inv E15 (trust
    upstream): the graph is connected, so every node is reachable.
    We raise GraphInconsistencyError if a node is NOT reachable
    (defensive against C13 contract drift).

    Determinism: neighbours iterated in lex-ASC order (from
    adjacency); FIFO queue. Same source + same edges → same depths
    every time.
    """
    depth: dict[str, int] = {source: 0}
    queue: deque[str] = deque((source,))
    while queue:
        u = queue.popleft()
        for v in adjacency[u]:  # already lex-ASC sorted
            if v not in depth:
                depth[v] = depth[u] + 1
                queue.append(v)

    # Inv E15 defensive check: every node should be reachable.
    unreachable = [r for r in nodes if r not in depth]
    if unreachable:
        raise GraphInconsistencyError(
            f"Phase β: BFS from {source!r} did not reach "
            f"{sorted(unreachable)!r}. Inv E15 (graph connectivity) "
            f"violated — upstream contract drift from C13 Inv D13."
        )
    return depth


# =============================================================================
# Connectivity (degree)
# =============================================================================

def _compute_connectivity(
    *,
    adjacency: dict[str, tuple[str, ...]],
) -> dict[str, int]:
    """Per v0.1 § 1.3: degree of each node = count of distinct neighbours
    in the adjacency graph."""
    return {r: len(neighbours) for r, neighbours in adjacency.items()}


# =============================================================================
# Brandes betweenness (SKETCH, per § 3.5)
# =============================================================================

def _brandes_betweenness(
    *,
    adjacency: dict[str, tuple[str, ...]],
    nodes: tuple[str, ...],
) -> dict[str, float]:
    """Compute Brandes-style betweenness for every node.

    Per § 3.5 SKETCH formula:
        betweenness(R) = Σ_{(A,B) s.t. A≠B, A≠R, B≠R}
                         (σ_{A,B}(R) / σ_{A,B})

    where σ_{A,B} is the number of shortest A→B paths and σ_{A,B}(R)
    is the count of those that pass through R.

    Standard Brandes implementation: accumulate dependency δ[v] from
    each source by walking the BFS-DAG in reverse-BFS order.

    Pinned formula is the LOCK-mandatory B-C14-BETWEENNESS-FORMULA-LOCK.
    The SKETCH here uses the canonical Brandes 2001 formulation for
    unweighted undirected graphs, with NO halving (so each pair (s,t)
    contributes from BOTH the s-source and t-source iterations — i.e.
    raw counts, factor-of-2 inflated relative to the symmetric form).

    Determinism: sources iterated in lex-ASC order; predecessors
    iterated in lex-ASC order; tie-breaking happens at the rank
    level upstream.

    For k ≤ 1 every node's betweenness is 0 (no pairs).
    """
    betweenness: dict[str, float] = {r: 0.0 for r in nodes}
    if len(nodes) <= 1:
        return betweenness

    # Run Brandes from each source in lex-ASC order.
    for source in nodes:  # nodes is already lex-ASC sorted
        # ── single-source shortest paths via BFS ─────────────────────
        sigma: dict[str, int] = {r: 0 for r in nodes}
        sigma[source] = 1
        dist: dict[str, int] = {source: 0}
        predecessors: dict[str, list[str]] = {r: [] for r in nodes}
        stack: list[str] = []  # nodes in BFS-discovery order
        queue: deque[str] = deque((source,))
        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in adjacency[v]:  # already lex-ASC sorted
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    predecessors[w].append(v)

        # ── accumulation: reverse-BFS order ──────────────────────────
        delta: dict[str, float] = {r: 0.0 for r in nodes}
        while stack:
            w = stack.pop()
            for v in predecessors[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != source:
                betweenness[w] += delta[w]

    return betweenness


def _rank_betweenness(
    *,
    nodes: tuple[str, ...],
    betweenness: dict[str, float],
) -> tuple[tuple[str, int], ...]:
    """Convert raw betweenness scores to ranks 1..k (1 = highest).

    Per § 3.5: ties broken lex-ASC by room_id (i.e., room_id ASC
    secondary key after betweenness DESC primary).

    FP determinism note: ranks are stable for "equal up to ~1e-12"
    because the input betweenness values are accumulated via rational
    arithmetic on small integer counts. For residential graphs of
    n ≤ ~15 the resulting floats are exact rationals or very close.
    No epsilon is applied at v0.2; LOCK-mandatory item
    `B-C14-BETWEENNESS-FORMULA-LOCK` will revisit if FP noise becomes
    observable in production.
    """
    # Sort by (-betweenness, room_id) — DESC betweenness, ASC room_id.
    ordered = sorted(
        nodes, key=lambda r: (-betweenness[r], r)
    )
    # Assign ranks 1..k in that order.
    ranked = tuple((r, idx + 1) for idx, r in enumerate(ordered))
    # Return in lex-ASC by room_id (per Inv E5 sort convention).
    return tuple(sorted(ranked))


# =============================================================================
# Phase β main entry
# =============================================================================

def compute_node_metrics(
    *,
    topology: GraphTopology,
    main_entry_room_id: str,
) -> NodeMetrics:
    """Phase β: compute (step_depth_from_entry, connectivity,
    betweenness_rank).

    Per C14 SPEC v0.2 LOCKED § 3 Phase β.

    Inputs:
      topology: GraphTopology from Phase α (validated nodes / edges /
        primary_edges).
      main_entry_room_id: the BFS source room (already verified to be
        in topology.nodes by Phase α).

    Returns:
      NodeMetrics — frozen, with all three tuples lex-ASC by room_id
      (Inv E5).

    Raises:
      GraphInconsistencyError: if BFS fails to reach every node
        (Inv E15 contract drift) or main_entry_room_id is not in nodes.
    """
    if main_entry_room_id not in set(topology.nodes):
        raise GraphInconsistencyError(
            f"Phase β: main_entry_room_id {main_entry_room_id!r} not in "
            f"topology.nodes ({list(topology.nodes)})."
        )

    adjacency = _build_adjacency(topology.nodes, topology.edges)

    # ── step_depth_from_entry (BFS) ─────────────────────────────────
    depths = _bfs_step_depths(
        adjacency=adjacency,
        nodes=topology.nodes,
        source=main_entry_room_id,
    )
    step_depth_from_entry = tuple(
        (r, depths[r]) for r in topology.nodes  # nodes already lex-ASC
    )

    # ── connectivity (degree) ───────────────────────────────────────
    conn = _compute_connectivity(adjacency=adjacency)
    connectivity = tuple((r, conn[r]) for r in topology.nodes)

    # ── betweenness_rank (Brandes + ranking) ────────────────────────
    raw_betweenness = _brandes_betweenness(
        adjacency=adjacency, nodes=topology.nodes
    )
    betweenness_rank = _rank_betweenness(
        nodes=topology.nodes, betweenness=raw_betweenness
    )

    return NodeMetrics(
        step_depth_from_entry=step_depth_from_entry,
        connectivity=connectivity,
        betweenness_rank=betweenness_rank,
    )


__all__ = [
    "NodeMetrics",
    "compute_node_metrics",
]
