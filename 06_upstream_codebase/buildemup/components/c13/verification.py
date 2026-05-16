"""
BuildemUp — Component 13 — Phase F (pure verification)
=======================================================

Per C13 SPEC v1.0 LOCKED:
- v0.2 A9 (Inv D13 — full door-induced reachability)
- v0.5 D2 (Inv D11.3' — kitchen-transit conditional legality)
- v0.5 D6 (Inv D17 — primary-door reachability for habitable rooms)
- v0.7 F1 (Phase F PURE VERIFICATION ONLY — no mutation, no
  optimization, no selection)
- v0.7 Inv D22 (Phase F side-effect-free w.r.t. core schema)

Phase F responsibility (LOCKED per v0.7 F1):
  - PURE VERIFICATION ONLY.
  - No mutation of door positions, hinges, widths, swing directions.
  - No mutation of advisory_flags tuple.
  - No optimization decisions.
  - No selection between alternatives.

Verifications performed at Phase F:
  - Inv D13: full reachability — every PlacedRoom reachable from
    main_entry via the FULL door-induced graph (primary + secondary
    doors).
  - Inv D17: primary-reachability — every HABITABLE room reachable
    from main_entry via the PRIMARY-DOOR-ONLY graph.
  - Inv D11.3': CONDITIONAL_LEGALITY — for each non-kitchen room,
    if the primary-graph shortest path from main_entry traverses a
    kitchen, an alternate route MUST exist (or kitchen-transit is
    not "primary circulation through kitchen for non-kitchen access"
    and is permitted).

Dispatch:
  - STRICT mode → raises specific error subclass on first violation.
  - WARN mode → returns a VerificationReport with violations recorded;
    orchestrator constructs FailureRecord for each.

Phase F returns a VerificationReport. Orchestrator decides how to
package it (SuccessfulDoorPlacement vs FailedDoorPlacement) based on
strict_mode and whether violations occurred.

Per v0.7 F1: future amendments that would add mutation OR optimization
to Phase F MUST FIRST move that responsibility to Phase A/B/C/D/E
(selection + resolution layers), keeping Phase F pure.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .errors import (
    HabitablePrimaryUnreachabilityError,
    NbcThroughBathroomRoutingError,
    PostResolutionUnreachabilityError,
)
from .schema import (
    ConditionalLegalityViolation,
    Door,
    HABITABLE_ROOM_CATEGORIES,
)


# =============================================================================
# Result schema
# =============================================================================

@dataclass(frozen=True)
class VerificationReport:
    """Output of Phase F. Pure record of verification outcomes.

    Fields:
      d13_violations: tuple of room_ids that failed Inv D13
          (unreachable via full door graph).
      d17_violations: tuple of habitable room_ids that failed Inv D17
          (unreachable via primary-door-only graph).
      d11_3_violations: tuple of ConditionalLegalityViolation per Inv
          D11.3' (kitchen-transit when alternate exists).

    Per Inv D7 (byte-equal replay): all violation tuples are sorted
    canonically (lex-ASC by room_id) so two verification runs on the
    same input produce identical output.

    Per Inv D22 (v0.7 F1): VerificationReport is the ONLY side-effect
    Phase F produces. No mutation of the door tuple, advisory_flags,
    or any other Phase A-E artefact.
    """
    d13_violations: tuple[str, ...]
    d17_violations: tuple[str, ...]
    d11_3_violations: tuple[ConditionalLegalityViolation, ...]

    def __post_init__(self) -> None:
        # Canonical ordering per Inv D7.
        if list(self.d13_violations) != sorted(self.d13_violations):
            raise ValueError(
                f"VerificationReport.d13_violations must be sorted "
                f"lex-ASC; got {self.d13_violations}."
            )
        if list(self.d17_violations) != sorted(self.d17_violations):
            raise ValueError(
                f"VerificationReport.d17_violations must be sorted "
                f"lex-ASC; got {self.d17_violations}."
            )
        # Sort key for d11_3 violations: the violated_path tuple
        # itself. Two violations with the same violated_path are
        # logically identical, so this is canonical.
        d11_3_keys = [v.violated_path for v in self.d11_3_violations]
        if d11_3_keys != sorted(d11_3_keys):
            raise ValueError(
                f"VerificationReport.d11_3_violations must be sorted "
                f"lex-ASC by violated_path; got keys {d11_3_keys}."
            )

    @property
    def is_clean(self) -> bool:
        """True iff no violations were detected."""
        return (
            not self.d13_violations
            and not self.d17_violations
            and not self.d11_3_violations
        )


# =============================================================================
# Graph utilities (pure helpers)
# =============================================================================

def _build_adjacency(
    doors: tuple[Door, ...],
    *,
    primary_only: bool,
    primary_door_ids: frozenset[tuple[str, str]],
) -> dict[str, frozenset[str]]:
    """Build an adjacency dict {room: frozenset(neighbour_rooms)} from
    the door tuple.

    Args:
      doors: every Door from Phase E output.
      primary_only: if True, restrict to doors in primary_door_ids
          (per Inv D17). If False, include all doors (per Inv D13).
      primary_door_ids: set of (room_a_id, room_b_id) for doors
          that are primaries. Phase E itself does not tag Door
          objects as primary/secondary (the Door schema has no such
          field); the orchestrator threads this set from Phase A's
          EdgeAssignment.is_secondary metadata.

    Per Inv D7 (replay determinism): adjacency values are frozensets;
    iteration order is BFS-determined, and BFS itself is
    deterministic because Python set iteration is insertion-ordered
    since 3.7 — but to be safe, the BFS helpers below sort
    neighbours lex-ASC before processing.
    """
    adj: dict[str, set[str]] = {}
    for door in doors:
        edge_id = (door.room_a_id, door.room_b_id)
        if primary_only and edge_id not in primary_door_ids:
            continue
        adj.setdefault(door.room_a_id, set()).add(door.room_b_id)
        adj.setdefault(door.room_b_id, set()).add(door.room_a_id)
    return {k: frozenset(v) for k, v in adj.items()}


def _bfs_reachable(
    start: str,
    adjacency: dict[str, frozenset[str]],
    *,
    forbidden: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """BFS from `start`, returning all reachable room ids.

    Args:
      start: starting room id.
      adjacency: room → frozenset of neighbour rooms.
      forbidden: rooms to treat as non-traversable (used for D11.3'
          alternate-route detection: forbid kitchens and check
          whether destination remains reachable).

    Returns frozenset of reachable rooms (includes `start` if not
    forbidden; excludes any rooms in `forbidden`).

    Per Inv D7: neighbour ordering is lex-ASC for deterministic
    visitation, even though BFS reachability is order-independent.
    """
    if start in forbidden:
        return frozenset()
    visited: set[str] = {start}
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        # Sort neighbours for replay determinism.
        for nb in sorted(adjacency.get(node, frozenset())):
            if nb in forbidden:
                continue
            if nb in visited:
                continue
            visited.add(nb)
            queue.append(nb)
    return frozenset(visited)


def _bfs_shortest_path(
    start: str,
    target: str,
    adjacency: dict[str, frozenset[str]],
    *,
    forbidden: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    """BFS shortest path from start to target.

    Returns the path as a tuple of room_ids INCLUDING start + target.
    Empty tuple if unreachable. (start, ) tuple if start == target.

    Args:
      forbidden: rooms to treat as non-traversable (skipped during
          expansion). Used for D11.3' alternate-route discovery
          (forbid kitchens, see if target still reachable).

    Per Inv D7: neighbours iterated lex-ASC so the path returned is
    canonical for replay determinism.
    """
    if start == target:
        return (start,)
    if start in forbidden or target in forbidden:
        return ()
    parent: dict[str, str | None] = {start: None}
    queue: deque[str] = deque([start])
    found = False
    while queue:
        node = queue.popleft()
        if node == target:
            found = True
            break
        for nb in sorted(adjacency.get(node, frozenset())):
            if nb in forbidden:
                continue
            if nb in parent:
                continue
            parent[nb] = node
            queue.append(nb)
    if not found:
        return ()
    # Reconstruct.
    path: list[str] = []
    cur: str | None = target
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return tuple(path)


# =============================================================================
# Verification helpers
# =============================================================================

# Categories considered "kitchen" for D11.3' analysis. Must mirror
# the set used in Phase A NBC vetoes.
_KITCHEN_CATEGORIES = frozenset({"kitchen", "cooking", "kitchen_dining"})


def _verify_d13_full_reachability(
    placed_room_ids: tuple[str, ...],
    full_adjacency: dict[str, frozenset[str]],
    main_entry_room_id: str,
) -> tuple[str, ...]:
    """Inv D13: every placed room reachable from main_entry via the
    full door-induced graph (primary + secondary doors).

    Returns sorted tuple of room_ids that failed reachability.
    Per Inv D7: sorted lex-ASC.
    """
    reachable = _bfs_reachable(main_entry_room_id, full_adjacency)
    violations = sorted(
        r for r in placed_room_ids if r not in reachable
    )
    return tuple(violations)


def _verify_d17_primary_reachability(
    placed_room_ids: tuple[str, ...],
    room_categories: dict[str, str],
    primary_adjacency: dict[str, frozenset[str]],
    main_entry_room_id: str,
) -> tuple[str, ...]:
    """Inv D17: every HABITABLE room reachable from main_entry via the
    PRIMARY-DOOR-ONLY graph.

    Per v0.5 D6: pathological "habitable room reachable only via
    utility secondary door" layouts are forbidden. Service spaces
    (bathroom, utility, store, servant, balcony) may use secondary
    doors only.

    Returns sorted tuple of habitable room_ids that failed primary-
    reachability. Per Inv D7: sorted lex-ASC.
    """
    primary_reachable = _bfs_reachable(
        main_entry_room_id, primary_adjacency,
    )
    violations = sorted(
        r for r in placed_room_ids
        if r != main_entry_room_id
        and room_categories.get(r) in HABITABLE_ROOM_CATEGORIES
        and r not in primary_reachable
    )
    return tuple(violations)


def _verify_d11_3_kitchen_transit(
    placed_room_ids: tuple[str, ...],
    room_categories: dict[str, str],
    primary_adjacency: dict[str, frozenset[str]],
    main_entry_room_id: str,
) -> tuple[ConditionalLegalityViolation, ...]:
    """Inv D11.3' (CONDITIONAL_LEGALITY per v0.5 D2):

    For each non-kitchen, non-entry room R reachable via primary
    graph, if the shortest path from main_entry to R traverses a
    kitchen, check whether an ALTERNATE primary path of equal-or-
    shorter length exists that DOES NOT traverse a kitchen.
      - If alternate exists → VIOLATION (the kitchen transit was
        avoidable). v1 treats this as STRICT/WARN per spec.
      - If no alternate exists → kitchen-transit is unavoidable,
        permitted per v0.5 D2 narrowing.

    Per v0.7 F1: this is pure verification, NOT correction.

    Returns tuple of ConditionalLegalityViolation sorted lex-ASC by
    violated_path (canonical replay order per Inv D7).
    """
    kitchen_rooms = frozenset(
        r for r in placed_room_ids
        if room_categories.get(r) in _KITCHEN_CATEGORIES
    )
    if not kitchen_rooms:
        return ()

    violations: list[ConditionalLegalityViolation] = []
    for room_id in sorted(placed_room_ids):
        # Skip entry and kitchens themselves.
        if room_id == main_entry_room_id:
            continue
        if room_id in kitchen_rooms:
            continue

        # Shortest primary path from main_entry to room_id.
        primary_path = _bfs_shortest_path(
            main_entry_room_id, room_id, primary_adjacency,
        )
        if not primary_path:
            # Not reachable via primary graph — D17 covers this case.
            continue
        if len(primary_path) < 3:
            # No interior rooms — can't traverse a kitchen.
            continue
        interior = primary_path[1:-1]
        if not any(r in kitchen_rooms for r in interior):
            continue

        # Primary path DOES traverse a kitchen; check for alternate.
        alt_path = _bfs_shortest_path(
            main_entry_room_id, room_id, primary_adjacency,
            forbidden=kitchen_rooms,
        )
        if not alt_path:
            # No kitchen-free alternate exists → kitchen transit is
            # unavoidable. PERMITTED per v0.5 D2 narrowing.
            continue

        # Alternate exists → D11.3' VIOLATED.
        violations.append(ConditionalLegalityViolation(
            invariant_id="D11.3",
            violated_path=primary_path,
            alternative_path=alt_path,
            alternative_path_length_grid_units=len(alt_path) - 1,
        ))
    # Sort by violated_path tuple for canonical replay order.
    violations.sort(key=lambda v: v.violated_path)
    return tuple(violations)


# =============================================================================
# Phase F entry point
# =============================================================================

def verify(
    *,
    doors: tuple[Door, ...],
    placed_room_ids: tuple[str, ...],
    room_categories: dict[str, str],
    main_entry_room_id: str,
    primary_door_ids: frozenset[tuple[str, str]],
    strict_mode: bool,
) -> VerificationReport:
    """Phase F entry point — PURE VERIFICATION.

    Args:
      doors: Phase E output (sorted lex-ASC, exactly one is_main_entry).
      placed_room_ids: every room in the candidate (from C12 upstream).
      room_categories: room_id → category map (from C12 upstream).
      main_entry_room_id: which room owns the main entry door.
      primary_door_ids: set of (room_a_id, room_b_id) tuples for
          doors that are PRIMARY (not secondary). Threaded from
          Phase A's EdgeAssignment.is_secondary metadata.
      strict_mode: True → raise on first violation. False (WARN) →
          return a populated VerificationReport.

    Returns:
      VerificationReport (sorted, deterministic).

    Raises (only in strict_mode=True):
      PostResolutionUnreachabilityError: Inv D13 failed.
      HabitablePrimaryUnreachabilityError: Inv D17 failed.
      NbcThroughBathroomRoutingError: Inv D11.3' failed (note: shares
          error class with D11.2 since both are "primary circulation
          routes inappropriately through a service room"; the rationale
          string distinguishes which invariant).

    Per Inv D22: NO mutation. Caller-supplied `doors` tuple is read
    only. Caller-supplied dicts/frozensets are not modified.
    """
    full_adjacency = _build_adjacency(
        doors, primary_only=False, primary_door_ids=primary_door_ids,
    )
    primary_adjacency = _build_adjacency(
        doors, primary_only=True, primary_door_ids=primary_door_ids,
    )

    d13_violations = _verify_d13_full_reachability(
        placed_room_ids, full_adjacency, main_entry_room_id,
    )
    if strict_mode and d13_violations:
        raise PostResolutionUnreachabilityError(
            f"Phase F: Inv D13 failed — {len(d13_violations)} room(s) "
            f"unreachable from {main_entry_room_id!r}: "
            f"{list(d13_violations)}."
        )

    d17_violations = _verify_d17_primary_reachability(
        placed_room_ids, room_categories, primary_adjacency,
        main_entry_room_id,
    )
    if strict_mode and d17_violations:
        raise HabitablePrimaryUnreachabilityError(
            f"Phase F: Inv D17 failed — {len(d17_violations)} "
            f"habitable room(s) reachable only via secondary doors "
            f"from {main_entry_room_id!r}: {list(d17_violations)}."
        )

    d11_3_violations = _verify_d11_3_kitchen_transit(
        placed_room_ids, room_categories, primary_adjacency,
        main_entry_room_id,
    )
    if strict_mode and d11_3_violations:
        first = d11_3_violations[0]
        raise NbcThroughBathroomRoutingError(
            f"Phase F: Inv D11.3' failed — primary path "
            f"{list(first.violated_path)} routes through a kitchen "
            f"when an alternate primary path "
            f"{list(first.alternative_path)} of length "
            f"{first.alternative_path_length_grid_units} exists "
            f"(D11.3' v0.5 narrowing)."
        )

    return VerificationReport(
        d13_violations=d13_violations,
        d17_violations=d17_violations,
        d11_3_violations=d11_3_violations,
    )


__all__ = [
    "VerificationReport",
    "verify",
]
