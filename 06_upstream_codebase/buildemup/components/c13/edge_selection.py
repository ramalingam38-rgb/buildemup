"""
BuildemUp — Component 13 — Phase A (edge selection)
====================================================

Per C13 SPEC v1.0 LOCKED:
- v0.1 § 3.1 (base per-room selection)
- v0.3 B6 (3-tier structural priority — replaces v0.2 A8 typology table)
- v0.4 C2 (HARD_LEGALITY NBC vetoes D11.1, D11.4 — D11.2 / D11.3' at Phase F)
- v0.4 C4 (MAX_DOORS_PER_ROOM_V1 hard cap + secondary-door eligibility)
- v0.3 B8 (RoomDoorPreference caller-supplied secondary doors)
- v0.4 C9 (secondary-door graph semantics: primary picked first, then
  secondary)

Phase A responsibility (per v0.7 F1 purity discipline):
  - SELECTS which SharedEdge each room's primary door sits on
  - Optionally SELECTS a secondary edge per room (caller-specified
    via RoomDoorPreference + eligible category check)
  - REJECTS room-edge pairs that violate HARD_LEGALITY single-edge
    NBC vetoes (D11.1, D11.4)
  - DOES NOT decide swing direction (that's Phase B)
  - DOES NOT decide position along edge (that's Phase C)
  - DOES NOT resolve swing-arc conflicts (that's Phase D)
  - DOES NOT verify graph connectivity (that's Phase F)

3-tier structural priority (v0.3 B6):
  Tier 1: main entry room — must succeed first; prefers
          EXTERNAL_ENVELOPE edge (via C12V10EdgeAdapter or native
          C12 v1.1 edge_type)
  Tier 2: corridor-adjacent rooms — iterated lex-ASC by room_id;
          prefers corridor edge with maximum overlap_length_m
          (most placement flexibility — Inv D7 deterministic tie-
          break: lex-ASC corridor_room_id)
  Tier 3: all other rooms — iterated lex-ASC by room_id; picks
          edge minimizing BFS step-depth from main entry through
          already-assigned-door graph; tie-break: lex-ASC edge id

Outputs:
  EdgeSelectionResult — immutable record of:
    - primary_assignments: tuple[(room_id, edge), ...] sorted by
      room_id processing order
    - secondary_assignments: tuple[(room_id, edge), ...] (may be empty)
    - main_entry_room_id: which room owns the main entry door
    - main_entry_edge: the SharedEdge bearing is_main_entry=True

Per Inv D7 (byte-equal replay): all iteration order, tie-break, and
filter logic in this module is canonical and deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .contracts import C13ConsumesFromC12Edge, EdgeType
from .errors import (
    DoorPositionInfeasibleError,
    EntryRoomNotFoundError,
    NbcBathroomKitchenAdjacencyError,
    NbcMasterBedroomAdjacencyError,
)
from .schema import (
    HABITABLE_ROOM_CATEGORIES,
    RoomDoorPreference,
    SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1,
)
from .telemetry import C13TelemetrySink, EdgeSelectionEvent, NullTelemetrySink


# =============================================================================
# Result schema
# =============================================================================

@dataclass(frozen=True)
class EdgeAssignment:
    """One room → edge pick. Frozen for replay determinism."""
    room_id: str
    edge: C13ConsumesFromC12Edge
    is_secondary: bool


@dataclass(frozen=True)
class EdgeSelectionResult:
    """Output of Phase A. Carries per-room edge picks + main-entry
    marker. Consumed by Phase B (swing) and Phase C (position).

    Fields:
      assignments: tuple of EdgeAssignment sorted by (room_id,
          is_secondary). Primary precedes secondary within a room
          per v0.4 C9 (primary always picked before secondary).
      main_entry_room_id: the room owning the main entry door
          (is_main_entry=True will be set on the corresponding Door
          at Phase E assembly).
    """
    assignments: tuple[EdgeAssignment, ...]
    main_entry_room_id: str

    def __post_init__(self) -> None:
        if not self.main_entry_room_id:
            raise ValueError(
                "EdgeSelectionResult.main_entry_room_id must be non-empty."
            )
        # Canonical ordering: (room_id, is_secondary).
        keys = [(a.room_id, a.is_secondary) for a in self.assignments]
        if keys != sorted(keys):
            raise ValueError(
                f"EdgeSelectionResult.assignments must be sorted by "
                f"(room_id, is_secondary); got {keys}."
            )
        # main_entry_room_id must appear among the assignments.
        room_ids_with_primary = {
            a.room_id for a in self.assignments if not a.is_secondary
        }
        if self.main_entry_room_id not in room_ids_with_primary:
            raise ValueError(
                f"EdgeSelectionResult.main_entry_room_id="
                f"{self.main_entry_room_id!r} must have a primary "
                f"assignment in the result; primary rooms: "
                f"{sorted(room_ids_with_primary)}."
            )


# =============================================================================
# Helpers
# =============================================================================

def _edges_touching_room(
    room_id: str,
    edges: tuple[C13ConsumesFromC12Edge, ...],
) -> tuple[C13ConsumesFromC12Edge, ...]:
    """Filter edges that touch a given room. Preserves input order
    (which per C12 Inv 8 is lex-ASC by (room_a_id, room_b_id) — so
    this filter is deterministic for replay)."""
    return tuple(
        e for e in edges
        if e.room_a_id == room_id or e.room_b_id == room_id
    )


def _is_feasible(edge: C13ConsumesFromC12Edge) -> bool:
    """A door can sit on this edge iff doorway_feasible is True
    (C12 already ran NBC minima checks per Inv D2)."""
    return bool(edge.doorway_feasible)


def _other_room(edge: C13ConsumesFromC12Edge, room_id: str) -> str:
    """Given an edge and one room id on it, return the other."""
    if edge.room_a_id == room_id:
        return edge.room_b_id
    if edge.room_b_id == room_id:
        return edge.room_a_id
    raise ValueError(
        f"_other_room: edge ({edge.room_a_id}, {edge.room_b_id}) does "
        f"not touch room_id={room_id!r}."
    )


def _has_corridor_adjacency(
    room_id: str,
    edges: tuple[C13ConsumesFromC12Edge, ...],
    room_categories: dict[str, str],
) -> bool:
    """True if any feasible edge touching the room connects it to a
    corridor (category == 'corridor')."""
    for e in edges:
        if not _is_feasible(e):
            continue
        if e.room_a_id == room_id and room_categories.get(e.room_b_id) == "corridor":
            return True
        if e.room_b_id == room_id and room_categories.get(e.room_a_id) == "corridor":
            return True
    return False


def _categorize_pair(
    edge: C13ConsumesFromC12Edge,
    room_categories: dict[str, str],
) -> tuple[str, str]:
    """Return the (category_a, category_b) tuple for an edge.
    Missing category → ''."""
    return (
        room_categories.get(edge.room_a_id, ""),
        room_categories.get(edge.room_b_id, ""),
    )


# =============================================================================
# NBC single-edge vetoes (HARD_LEGALITY — D11.1, D11.4)
# =============================================================================

# Bathroom / WC categories the NBC veto applies to. Per v0.4 C2 NBC
# 2016 Part 3 wording: "no room containing water-closets shall ...
# open directly into any kitchen or cooking space."
_BATHROOM_CATEGORIES = frozenset({"bathroom", "wc", "powder_room", "toilet"})
_KITCHEN_CATEGORIES = frozenset({"kitchen", "cooking", "kitchen_dining"})
_MASTER_BEDROOM_CATEGORIES = frozenset({"master_bedroom"})


def _violates_d11_1(
    edge: C13ConsumesFromC12Edge,
    room_categories: dict[str, str],
) -> bool:
    """Inv D11.1: no door directly connects a bathroom to a kitchen
    (NBC 2016 Part 3)."""
    cat_a, cat_b = _categorize_pair(edge, room_categories)
    is_bath_kitchen = (
        (cat_a in _BATHROOM_CATEGORIES and cat_b in _KITCHEN_CATEGORIES)
        or (cat_b in _BATHROOM_CATEGORIES and cat_a in _KITCHEN_CATEGORIES)
    )
    return is_bath_kitchen


def _violates_d11_4(
    edge: C13ConsumesFromC12Edge,
    room_categories: dict[str, str],
    *,
    is_main_entry_room_edge: bool,
) -> bool:
    """Inv D11.4: master bedroom MAIN door does not open directly to
    kitchen or bathroom. Per v0.4 C2 wording: this restricts the
    MAIN bedroom door — not all doors of a master bedroom.

    A master bedroom may have a bathroom door (en-suite) — that is a
    secondary door from the master's perspective. v1 enforces the rule
    on the PRIMARY edge selection only.

    Args:
      edge: the candidate edge.
      room_categories: room_id → category map.
      is_main_entry_room_edge: True iff this edge is being considered
          AS the master bedroom's primary (= main bedroom door at v1
          since max_doors typically = 1 for bedrooms).
    """
    if not is_main_entry_room_edge:
        return False
    cat_a, cat_b = _categorize_pair(edge, room_categories)
    # Master bedroom on one side, kitchen/bathroom on the other.
    if cat_a in _MASTER_BEDROOM_CATEGORIES and (
        cat_b in _KITCHEN_CATEGORIES or cat_b in _BATHROOM_CATEGORIES
    ):
        return True
    if cat_b in _MASTER_BEDROOM_CATEGORIES and (
        cat_a in _KITCHEN_CATEGORIES or cat_a in _BATHROOM_CATEGORIES
    ):
        return True
    return False


# =============================================================================
# Main-entry edge selection (Tier 1)
# =============================================================================

def _select_main_entry_edge(
    entry_room_id: str,
    feasible_room_edges: tuple[C13ConsumesFromC12Edge, ...],
    room_categories: dict[str, str],
) -> C13ConsumesFromC12Edge:
    """Per v0.3 B6 Tier 1 + v0.1 § 3.1 step 2.

    Selection rules (in priority order):
      1. EXTERNAL_ENVELOPE edges preferred (any feasible external edge).
         Tie-break: lex-ASC by (room_a_id, room_b_id).
      2. Fallback: any feasible edge touching the entry room.
         Tie-break: lex-ASC.

    Per v0.4 C2 D11.1 / D11.4: NBC vetoes apply at selection time.
    Edges violating either are filtered BEFORE the priority decision.

    Raises DoorPositionInfeasibleError if no eligible edge exists
    (caught by orchestrator under STRICT/WARN dispatch).
    """
    # Filter to NBC-clean edges (D11.1 + D11.4).
    # Entry room is by definition the room whose main door is the
    # building entrance; that's NOT necessarily a master bedroom.
    # D11.4 only fires if entry_room_id IS a master_bedroom (rare/
    # invalid but possible upstream).
    is_master_bedroom_entry = (
        room_categories.get(entry_room_id) in _MASTER_BEDROOM_CATEGORIES
    )
    nbc_clean = []
    for e in feasible_room_edges:
        if _violates_d11_1(e, room_categories):
            continue
        if is_master_bedroom_entry and _violates_d11_4(
            e, room_categories, is_main_entry_room_edge=True,
        ):
            continue
        nbc_clean.append(e)

    if not nbc_clean:
        raise DoorPositionInfeasibleError(
            f"Phase A: no NBC-clean feasible edge available for "
            f"entry room {entry_room_id!r}. NBC vetoes (D11.1/D11.4) "
            f"filtered all candidate edges."
        )

    # Prefer EXTERNAL_ENVELOPE.
    external = [e for e in nbc_clean if e.edge_type == EdgeType.EXTERNAL_ENVELOPE]
    pool = external if external else nbc_clean

    # Canonical ordering: lex-ASC by (room_a_id, room_b_id).
    pool_sorted = sorted(pool, key=lambda e: (e.room_a_id, e.room_b_id))
    return pool_sorted[0]


# =============================================================================
# Tier 2: corridor-adjacent primary selection
# =============================================================================

def _select_corridor_adjacent_edge(
    room_id: str,
    feasible_room_edges: tuple[C13ConsumesFromC12Edge, ...],
    room_categories: dict[str, str],
    *,
    forbid_edges: frozenset[tuple[str, str]],
) -> C13ConsumesFromC12Edge:
    """Per v0.3 B6 Tier 2 + v0.1 § 3.1 step 3.

    Selection rules:
      1. Among feasible edges touching the room AND connecting to a
         corridor, pick the one with MAXIMUM overlap_length_m
         (most placement flexibility — preserved from v0.1).
      2. Tie-break (equal overlap_length_m): lex-ASC by
         (room_a_id, room_b_id).
      3. NBC veto D11.1 filters out bathroom-kitchen pairs at the
         edge level.
      4. forbid_edges excludes edges already picked as someone else's
         primary (prevents two rooms claiming the same edge as primary;
         allowed for secondary doors via v0.4 C9).

    Raises DoorPositionInfeasibleError if no eligible corridor edge.
    """
    candidates = []
    for e in feasible_room_edges:
        edge_id = (e.room_a_id, e.room_b_id)
        if edge_id in forbid_edges:
            continue
        if _violates_d11_1(e, room_categories):
            continue
        # Must connect to a corridor.
        other = _other_room(e, room_id)
        if room_categories.get(other) != "corridor":
            continue
        candidates.append(e)

    if not candidates:
        raise DoorPositionInfeasibleError(
            f"Phase A: room {room_id!r} has no corridor-adjacent "
            f"feasible edge available after forbid_edges + NBC filters."
        )

    # Sort by (-overlap_length_m, room_a_id, room_b_id) so the max
    # overlap comes first, then lex tie-break.
    candidates.sort(key=lambda e: (-e.overlap_length_m, e.room_a_id, e.room_b_id))
    return candidates[0]


# =============================================================================
# Tier 3: lex-ASC fallback
# =============================================================================

def _select_lex_asc_edge(
    room_id: str,
    feasible_room_edges: tuple[C13ConsumesFromC12Edge, ...],
    room_categories: dict[str, str],
    *,
    forbid_edges: frozenset[tuple[str, str]],
    is_master_bedroom: bool,
) -> C13ConsumesFromC12Edge:
    """Per v0.3 B6 Tier 3.

    Selection: lex-ASC by (room_a_id, room_b_id) among feasible edges
    that pass NBC filters and aren't in forbid_edges.

    v0.1 § 3.1 step 4's BFS step-depth heuristic was deferred per
    v0.3 B1 (reverted to lex-ASC; BFS-based circulation quality is
    C14's job per § 0.5 boundary). Lex-ASC is the v1 placeholder —
    deterministic and simple.
    """
    candidates = []
    for e in feasible_room_edges:
        edge_id = (e.room_a_id, e.room_b_id)
        if edge_id in forbid_edges:
            continue
        if _violates_d11_1(e, room_categories):
            continue
        if is_master_bedroom and _violates_d11_4(
            e, room_categories, is_main_entry_room_edge=True,
        ):
            continue
        candidates.append(e)

    if not candidates:
        raise DoorPositionInfeasibleError(
            f"Phase A: room {room_id!r} has no NBC-clean feasible "
            f"edge available (forbid_edges + NBC filters left none)."
        )

    candidates.sort(key=lambda e: (e.room_a_id, e.room_b_id))
    return candidates[0]


# =============================================================================
# Secondary door selection (per v0.3 B8 + v0.4 C4 + v0.4 C9)
# =============================================================================

def _select_secondary_edge(
    room_id: str,
    feasible_room_edges: tuple[C13ConsumesFromC12Edge, ...],
    room_categories: dict[str, str],
    preference: RoomDoorPreference,
    *,
    forbid_edges: frozenset[tuple[str, str]],
) -> Optional[C13ConsumesFromC12Edge]:
    """Per v0.3 B8 + v0.4 C4 + v0.4 C9.

    Selection rules:
      1. Filter to feasible + NBC-clean edges NOT in forbid_edges
         (excludes the room's own primary edge from being reused).
      2. Apply preference filter:
         - 'corridor': prefer edges to corridor rooms
         - 'utility': prefer edges to utility rooms
         - 'external': prefer EXTERNAL_ENVELOPE edges
         - 'none': no preference filter (lex-ASC across all)
      3. Within the preferred subset (if any match), sort lex-ASC.
      4. If no preferred edge exists, fall back to all NBC-clean
         edges and sort lex-ASC.

    Returns None if no eligible edge for a secondary door (room
    cannot have a secondary; orchestrator decides whether this
    violates min_doors).
    """
    nbc_clean = []
    for e in feasible_room_edges:
        edge_id = (e.room_a_id, e.room_b_id)
        if edge_id in forbid_edges:
            continue
        if _violates_d11_1(e, room_categories):
            continue
        nbc_clean.append(e)

    if not nbc_clean:
        return None

    # Apply preference filter.
    pref = preference.secondary_door_preference
    preferred: list[C13ConsumesFromC12Edge] = []
    if pref == "corridor":
        preferred = [
            e for e in nbc_clean
            if room_categories.get(_other_room(e, room_id)) == "corridor"
        ]
    elif pref == "utility":
        preferred = [
            e for e in nbc_clean
            if room_categories.get(_other_room(e, room_id)) == "utility"
        ]
    elif pref == "external":
        preferred = [
            e for e in nbc_clean
            if e.edge_type == EdgeType.EXTERNAL_ENVELOPE
        ]
    # pref == "none" → preferred stays empty → fall through to nbc_clean.

    pool = preferred if preferred else nbc_clean
    pool_sorted = sorted(pool, key=lambda e: (e.room_a_id, e.room_b_id))
    return pool_sorted[0]


# =============================================================================
# Public API — select_edges
# =============================================================================

def select_edges(
    *,
    candidate_signature: str,
    placed_room_ids: tuple[str, ...],
    room_categories: dict[str, str],
    shared_edges: tuple[C13ConsumesFromC12Edge, ...],
    entry_room_id: str,
    room_door_preferences: dict[str, RoomDoorPreference],
    telemetry_sink: Optional[C13TelemetrySink] = None,
) -> EdgeSelectionResult:
    """Phase A entry point.

    DOOR-CENTRIC SELECTION MODEL (clarified in Sub-2 self-analysis):

    A SharedEdge between rooms R and S admits AT MOST ONE primary
    door at v1 — that single door serves BOTH rooms. So Phase A does
    NOT pick a separate primary edge "for each room"; it picks a set
    of edges such that every room is touched by at least one chosen
    edge.

    Iteration order per v0.3 B6 3-tier structural priority:
      Tier 1: entry_room_id (must succeed; preferred EXTERNAL_ENVELOPE)
      Tier 2: corridor-adjacent rooms, lex-ASC by room_id
      Tier 3: remaining rooms, lex-ASC by room_id

    For each room in priority order: if the room is NOT YET touched by
    any chosen edge, pick one for it using the tier's selection rule.
    Otherwise skip (the existing edge already serves this room).

    For each room with RoomDoorPreference.max_doors >= 2 AND eligible
    category, additionally pick a SECONDARY edge (per v0.4 C4 + C9 +
    v0.3 B8). The same-edge constraint still applies to secondary
    doors via 'forbid_edges' (a secondary door cannot reuse an edge
    already chosen as anyone's primary, otherwise it's a duplicate).

    Per Inv D1': each room ends up with min_doors ≤ doors ≤ max_doors.
    Phase A may select FEWER than min_doors for non-eligible rooms;
    the orchestrator catches that as a separate failure mode at
    assembly time.

    Per v0.4 C9 secondary-door graph semantics: "Primary door selected
    first … Secondary door selected after Phase D resolution of
    primary confirmed." Phase A only DOES the selection; Phase D
    validates conflict-resolution outcomes.

    Args:
      candidate_signature: provenance.
      placed_room_ids: lex-ASC tuple of room ids in the candidate.
      room_categories: room_id → category map.
      shared_edges: tuple of C12 SharedEdges (or Protocol-conforming
          objects), already canonically sorted by C12 invariant.
      entry_room_id: which room is the building main entry.
      room_door_preferences: room_id → RoomDoorPreference. Rooms not
          in the map default to (min=1, max=1, secondary_pref='none').
      telemetry_sink: optional sink. None → NullTelemetrySink.

    Returns:
      EdgeSelectionResult.

    Raises:
      EntryRoomNotFoundError: entry_room_id not in placed_room_ids.
      DoorPositionInfeasibleError: the entry room or any room has no
          NBC-clean feasible edge available given the constraints.
    """
    sink: C13TelemetrySink = telemetry_sink or NullTelemetrySink()

    if entry_room_id not in placed_room_ids:
        raise EntryRoomNotFoundError(
            f"Phase A: entry_room_id={entry_room_id!r} not found in "
            f"placed_room_ids={placed_room_ids!r}."
        )

    # Default preference for rooms not explicitly configured.
    def _pref_for(room_id: str) -> RoomDoorPreference:
        if room_id in room_door_preferences:
            return room_door_preferences[room_id]
        return RoomDoorPreference(room_id=room_id)

    # Bucket rooms into Tier 2 (corridor-adjacent, excluding entry) and
    # Tier 3 (rest, excluding entry).
    other_rooms = [r for r in placed_room_ids if r != entry_room_id]
    corridor_adjacent: list[str] = []
    remaining: list[str] = []
    for r in other_rooms:
        edges_touching = _edges_touching_room(r, shared_edges)
        if _has_corridor_adjacency(r, edges_touching, room_categories):
            corridor_adjacent.append(r)
        else:
            remaining.append(r)
    corridor_adjacent.sort()
    remaining.sort()

    # State accumulators:
    # - assignments: list of EdgeAssignment (one entry per (room,
    #   is_secondary) pair representing the room's responsibility
    #   for a door). Same physical edge may appear under multiple
    #   "responsible" rooms if it serves all of them; we deduplicate
    #   by tracking already-chosen edge ids.
    # - chosen_edge_ids: set of (room_a_id, room_b_id) tuples of edges
    #   that already have a door on them.
    # - rooms_touched_by_door: set of room_ids that already have at
    #   least one door connecting them.
    assignments: list[EdgeAssignment] = []
    chosen_edge_ids: set[tuple[str, str]] = set()
    rooms_touched_by_door: set[str] = set()

    def _record_door(
        responsible_room: str,
        edge: C13ConsumesFromC12Edge,
        *,
        is_secondary: bool,
        tier_label: Literal["entry", "corridor_adjacent", "lex_asc"],
        feasible_count: int,
    ) -> None:
        assignments.append(
            EdgeAssignment(
                room_id=responsible_room,
                edge=edge,
                is_secondary=is_secondary,
            )
        )
        chosen_edge_ids.add((edge.room_a_id, edge.room_b_id))
        rooms_touched_by_door.add(edge.room_a_id)
        rooms_touched_by_door.add(edge.room_b_id)
        sink.emit(EdgeSelectionEvent(
            candidate_signature=candidate_signature,
            room_id=responsible_room,
            selected_edge_room_a_id=edge.room_a_id,
            selected_edge_room_b_id=edge.room_b_id,
            selection_tier=tier_label,
            feasible_edge_count=feasible_count,
            is_secondary=is_secondary,
        ))

    # ── Tier 1: main entry ─────────────────────────────────────────
    entry_edges = _edges_touching_room(entry_room_id, shared_edges)
    entry_feasible = tuple(e for e in entry_edges if _is_feasible(e))
    if not entry_feasible:
        raise DoorPositionInfeasibleError(
            f"Phase A: entry room {entry_room_id!r} has no feasible "
            f"shared edge in this candidate."
        )
    main_entry_edge = _select_main_entry_edge(
        entry_room_id, entry_feasible, room_categories,
    )
    _record_door(
        entry_room_id, main_entry_edge,
        is_secondary=False, tier_label="entry",
        feasible_count=len(entry_feasible),
    )

    # ── Tier 2: corridor-adjacent rooms ────────────────────────────
    for room_id in corridor_adjacent:
        if room_id in rooms_touched_by_door:
            # Already served by Tier 1's edge (or a previous Tier-2
            # pick). No new door needed.
            continue
        edges_touching = _edges_touching_room(room_id, shared_edges)
        feasible_touching = tuple(e for e in edges_touching if _is_feasible(e))
        if not feasible_touching:
            raise DoorPositionInfeasibleError(
                f"Phase A: room {room_id!r} (Tier 2 corridor-adjacent) "
                f"has no feasible shared edge."
            )
        chosen = _select_corridor_adjacent_edge(
            room_id, feasible_touching, room_categories,
            forbid_edges=frozenset(chosen_edge_ids),
        )
        _record_door(
            room_id, chosen,
            is_secondary=False, tier_label="corridor_adjacent",
            feasible_count=len(feasible_touching),
        )

    # ── Tier 3: remaining rooms ────────────────────────────────────
    for room_id in remaining:
        if room_id in rooms_touched_by_door:
            continue
        edges_touching = _edges_touching_room(room_id, shared_edges)
        feasible_touching = tuple(e for e in edges_touching if _is_feasible(e))
        if not feasible_touching:
            raise DoorPositionInfeasibleError(
                f"Phase A: room {room_id!r} (Tier 3 lex-ASC) "
                f"has no feasible shared edge."
            )
        is_master = (
            room_categories.get(room_id) in _MASTER_BEDROOM_CATEGORIES
        )
        chosen = _select_lex_asc_edge(
            room_id, feasible_touching, room_categories,
            forbid_edges=frozenset(chosen_edge_ids),
            is_master_bedroom=is_master,
        )
        _record_door(
            room_id, chosen,
            is_secondary=False, tier_label="lex_asc",
            feasible_count=len(feasible_touching),
        )

    # Corridor / circulation rooms that fell out of all tiers may
    # already be served by adjacent rooms' edges. If after Tier 3 a
    # corridor still has no door touching it, that's a real
    # infeasibility (an isolated corridor would have been caught by
    # C12 Inv 11 reachability already).
    for room_id in placed_room_ids:
        if room_id in rooms_touched_by_door:
            continue
        # No door reaches this room — final fallback Tier 3 attempt
        # using full lex-ASC across all feasible edges that touch it.
        edges_touching = _edges_touching_room(room_id, shared_edges)
        feasible_touching = tuple(e for e in edges_touching if _is_feasible(e))
        if not feasible_touching:
            raise DoorPositionInfeasibleError(
                f"Phase A: room {room_id!r} has no feasible edge in "
                f"this candidate (no Tier reached it)."
            )
        is_master = (
            room_categories.get(room_id) in _MASTER_BEDROOM_CATEGORIES
        )
        chosen = _select_lex_asc_edge(
            room_id, feasible_touching, room_categories,
            forbid_edges=frozenset(chosen_edge_ids),
            is_master_bedroom=is_master,
        )
        _record_door(
            room_id, chosen,
            is_secondary=False, tier_label="lex_asc",
            feasible_count=len(feasible_touching),
        )

    # ── Secondary doors (per v0.3 B8 + v0.4 C4 + v0.4 C9) ─────────
    # Iterate room_ids in lex-ASC order to keep replay deterministic.
    for room_id in sorted(placed_room_ids):
        pref = _pref_for(room_id)
        if pref.max_doors < 2:
            continue
        category = room_categories.get(room_id, "")
        if category not in SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1:
            # v0.4 C4: secondary doors prohibited on
            # bedrooms/bathrooms/pooja. Silently skip.
            continue
        edges_touching = _edges_touching_room(room_id, shared_edges)
        feasible_touching = tuple(e for e in edges_touching if _is_feasible(e))
        if not feasible_touching:
            continue
        secondary = _select_secondary_edge(
            room_id, feasible_touching, room_categories, pref,
            forbid_edges=frozenset(chosen_edge_ids),
        )
        if secondary is None:
            continue
        _record_door(
            room_id, secondary,
            is_secondary=True, tier_label="lex_asc",
            feasible_count=len(feasible_touching),
        )

    # Canonical sort: (room_id, is_secondary). EdgeSelectionResult
    # __post_init__ enforces this.
    assignments.sort(key=lambda a: (a.room_id, a.is_secondary))
    return EdgeSelectionResult(
        assignments=tuple(assignments),
        main_entry_room_id=entry_room_id,
    )


__all__ = [
    "EdgeAssignment",
    "EdgeSelectionResult",
    "select_edges",
]
