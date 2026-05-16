"""
BuildemUp — Component 14 — Phase α: graph construction
=======================================================

Per C14 SPEC v0.2 LOCKED § 3 (Phase α) + v0.2 A2 (Inv E3' EXTERNAL
exclusion both sides).

Phase α is pure. It reads C13's `(doors, room_ids, primary_door_ids)`
inputs and produces the three graph-topology tuples:

- `nodes`: sorted `placed_room_ids` (Inv E2; uniqueness enforced)
- `edges`: sorted `(d.room_a_id, d.room_b_id)` for d in doors, EXCLUDING
   any edge where `room_a_id` OR `room_b_id` equals the EXTERNAL
   envelope placeholder (Inv E3' per A2)
- `primary_edges`: subset of `edges` whose canonical `(a, b)` tuple
   appears in `primary_door_ids`

Note on Door's room ordering: per C13's Door.__post_init__, every
Door has `room_a_id < room_b_id` strictly. So edges read directly from
doors are already in canonical (a < b) lex form. We DO normalize
`primary_door_ids` defensively (caller may pass either orientation).

Per the v0.2 A2 critique-walk finding: C12/C13's canonical lex-ASC
edge ordering may place `"EXTERNAL"` (capital E, 0x45) as `room_a_id`
when the partner room id begins with a lowercase letter. v0.1's
single-side EXTERNAL check would have missed those cases, inflating
connectivity[main_entry] by one and distorting every downstream
metric. Phase α uses the contracts.py-exported placeholder and checks
BOTH sides.

No mutation, no backtracking, no optimization. O(|doors| + |rooms|)
construction; the cost is dominated by the canonical sort which is
O(|doors| log |doors|) and O(|rooms| log |rooms|).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .contracts import EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID
from .errors import EntryRoomNotFoundError, GraphInconsistencyError


# =============================================================================
# Door protocol — structural typing so this module doesn't bind to C13's
# concrete Door class (defensive against future C13 amendments that
# preserve the room_a_id / room_b_id surface).
# =============================================================================

@runtime_checkable
class _DoorLike(Protocol):
    """Minimal structural shape Phase α needs from a door.

    Per C13's Door schema, `room_a_id < room_b_id` is hard-enforced.
    Phase α relies on this canonical ordering; if a future schema
    relaxes that contract, Phase α still produces correct output
    because it sorts inside `_canonical_edge()`.
    """
    @property
    def room_a_id(self) -> str: ...
    @property
    def room_b_id(self) -> str: ...


# =============================================================================
# Output: GraphTopology
# =============================================================================

@dataclass(frozen=True)
class GraphTopology:
    """Phase α output: the bare-bones topology consumed by Phases β / γ.

    Frozen for replay determinism (Inv E7). All three tuples in
    canonical lex-ASC order.
    """
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    primary_edges: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        # Sort invariants (mirror the schema's stricter check; we want
        # phase-internal failures to surface as GraphInconsistencyError
        # in the orchestrator, not as ValueError from CirculationGraphReport
        # later).
        if list(self.nodes) != sorted(self.nodes):
            raise GraphInconsistencyError(
                f"Phase α: nodes must be lex-ASC sorted; got "
                f"{list(self.nodes)}."
            )
        if len(set(self.nodes)) != len(self.nodes):
            raise GraphInconsistencyError(
                f"Phase α: nodes must be unique; got duplicates in "
                f"{list(self.nodes)}."
            )
        if list(self.edges) != sorted(self.edges):
            raise GraphInconsistencyError(
                f"Phase α: edges must be lex-ASC sorted; got "
                f"{list(self.edges)}."
            )
        node_set = frozenset(self.nodes)
        for a, b in self.edges:
            if a > b:
                raise GraphInconsistencyError(
                    f"Phase α: each edge requires room_a <= room_b; "
                    f"got ({a!r}, {b!r})."
                )
            if a not in node_set or b not in node_set:
                raise GraphInconsistencyError(
                    f"Phase α: edge ({a!r}, {b!r}) references a room "
                    f"not in nodes set."
                )
        # Inv E4: primary_edges ⊆ edges, sorted.
        if list(self.primary_edges) != sorted(self.primary_edges):
            raise GraphInconsistencyError(
                f"Phase α: primary_edges must be lex-ASC sorted; got "
                f"{list(self.primary_edges)}."
            )
        edge_set = set(self.edges)
        for pe in self.primary_edges:
            if pe not in edge_set:
                raise GraphInconsistencyError(
                    f"Phase α: primary edge {pe} is not in the edges set."
                )


# =============================================================================
# Helpers
# =============================================================================

def _canonical_edge(room_a: str, room_b: str) -> tuple[str, str]:
    """Normalize an edge to canonical (lex-min, lex-max) form.

    Defensive against future Door schema changes that might relax the
    `room_a_id < room_b_id` invariant. Today C13 enforces that
    strictly, so this normalization is a no-op for valid C13 doors —
    but it costs nothing and protects against contract drift.
    """
    if room_a <= room_b:
        return (room_a, room_b)
    return (room_b, room_a)


def _is_external_edge(room_a: str, room_b: str) -> bool:
    """Per v0.2 A2 / Inv E3': exclude edges where EITHER side is the
    EXTERNAL envelope placeholder.

    Critique-walk #1 finding: v0.1's single-side check would miss the
    `("EXTERNAL", "main_entry")` case (lex-valid because uppercase E
    sorts before lowercase m). Phase α checks both sides explicitly.
    """
    return (
        room_a == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID
        or room_b == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID
    )


# =============================================================================
# Phase α main entry
# =============================================================================

def construct_graph_topology(
    *,
    doors: tuple[_DoorLike, ...],
    placed_room_ids: tuple[str, ...],
    primary_door_ids: frozenset[tuple[str, str]],
    main_entry_room_id: str,
) -> GraphTopology:
    """Phase α: build (nodes, edges, primary_edges).

    Per C14 SPEC v0.2 LOCKED § 3 Phase α + v0.2 A2 (Inv E3').

    Inputs:
      doors: every door from the SuccessfulDoorPlacement. EXTERNAL
        edges are filtered out at this stage (per Inv E3'). May be empty
        for a single-room layout.
      placed_room_ids: every room from C12's PlacedCandidate. Becomes
        `nodes` after deduplication + lex-ASC sort.
      primary_door_ids: which doors are primaries. Subset of all
        doors. Edges are normalized to canonical (a<=b) form before
        membership check.
      main_entry_room_id: the room owning the `is_main_entry=True`
        door. Required to exist in placed_room_ids — if not,
        EntryRoomNotFoundError is raised (defensive against C13
        contract drift).

    Returns:
      GraphTopology — frozen, validated against the canonical-sort +
      coverage invariants.

    Raises:
      EntryRoomNotFoundError: main_entry_room_id not in placed_room_ids.
      GraphInconsistencyError: any per-edge / per-room consistency
        violation (defensive against upstream contract drift).
    """
    # ── Defensive arg validation ────────────────────────────────────
    if not isinstance(placed_room_ids, tuple):
        raise GraphInconsistencyError(
            f"construct_graph_topology: placed_room_ids must be a tuple; "
            f"got {type(placed_room_ids).__name__}."
        )
    if not isinstance(doors, tuple):
        raise GraphInconsistencyError(
            f"construct_graph_topology: doors must be a tuple; "
            f"got {type(doors).__name__}."
        )
    if not isinstance(primary_door_ids, frozenset):
        raise GraphInconsistencyError(
            f"construct_graph_topology: primary_door_ids must be a frozenset; "
            f"got {type(primary_door_ids).__name__}."
        )
    if not main_entry_room_id:
        raise GraphInconsistencyError(
            "construct_graph_topology: main_entry_room_id must be non-empty."
        )

    # ── Build nodes (Inv E2: sorted lex-ASC, unique) ────────────────
    nodes_seen: set[str] = set()
    for r in placed_room_ids:
        if not isinstance(r, str) or not r:
            raise GraphInconsistencyError(
                f"construct_graph_topology: every placed_room_id must be "
                f"a non-empty str; got {r!r}."
            )
        nodes_seen.add(r)
    nodes = tuple(sorted(nodes_seen))

    # ── Inv E6 precondition: main entry must be in nodes ────────────
    # (defensive — C13 should never produce a SuccessfulDoorPlacement
    # whose main_entry references a non-placed room).
    if main_entry_room_id not in nodes_seen:
        raise EntryRoomNotFoundError(
            f"main_entry_room_id {main_entry_room_id!r} not found in "
            f"placed_room_ids ({sorted(nodes_seen)})."
        )

    # ── Normalize primary_door_ids to canonical form ────────────────
    canonical_primaries: set[tuple[str, str]] = set()
    for (a, b) in primary_door_ids:
        if not isinstance(a, str) or not isinstance(b, str):
            raise GraphInconsistencyError(
                f"construct_graph_topology: every primary_door_id must "
                f"be a (str, str) tuple; got ({a!r}, {b!r})."
            )
        canonical_primaries.add(_canonical_edge(a, b))

    # ── Build edges from doors, excluding EXTERNAL on either side ───
    edges_seen: set[tuple[str, str]] = set()
    primary_edges_seen: set[tuple[str, str]] = set()
    for d in doors:
        if _is_external_edge(d.room_a_id, d.room_b_id):
            # Per Inv E3' (v0.2 A2): drop edges with EXTERNAL on either
            # side. External doors are entry points, not graph edges.
            continue
        edge = _canonical_edge(d.room_a_id, d.room_b_id)
        # Both endpoints must be in nodes (defensive — C13 should not
        # produce a door whose endpoints aren't in placed_room_ids).
        if edge[0] not in nodes_seen or edge[1] not in nodes_seen:
            raise GraphInconsistencyError(
                f"construct_graph_topology: door edge {edge} references a "
                f"room not in placed_room_ids. Upstream contract drift."
            )
        edges_seen.add(edge)
        if edge in canonical_primaries:
            primary_edges_seen.add(edge)

    edges = tuple(sorted(edges_seen))
    primary_edges = tuple(sorted(primary_edges_seen))

    return GraphTopology(
        nodes=nodes,
        edges=edges,
        primary_edges=primary_edges,
    )


__all__ = [
    "GraphTopology",
    "construct_graph_topology",
]
