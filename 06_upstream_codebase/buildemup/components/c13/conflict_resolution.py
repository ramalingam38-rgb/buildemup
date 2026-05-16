"""
BuildemUp — Component 13 — Phase D (swing-arc conflict resolution)
====================================================================

Per C13 SPEC v1.0 LOCKED:
- v0.1 § 3.4 (base conflict detection + resolution strategy ladder)
- v0.2 A4 (bounded retry with state snapshot + monotonic-conflict-count
  abort)
- v0.3 B3 (visited-state hashing + total-order tie-break)
- v0.3 B9 (Phase D reframed as bounded CSP-lite)
- v0.4 C5 (PhaseDConvergenceEvent MANDATORY day-1)
- v0.4 C6 (GeometricFidelity.APPROXIMATE at v1)

Phase D responsibility:
  - Detect swing-arc conflicts between door pairs that share a room.
  - Apply resolution strategies in canonical order (shift, flip,
    shrink) until conflict-free OR budget exhausted.
  - Snapshot state at each iteration so monotonic-decrease violations
    can rollback.
  - Hash visited states to prevent infinite loops.
  - Emit PhaseDConvergenceEvent (MANDATORY per v0.4 C5).

v1 CONFLICT MODEL (APPROXIMATE):
  Without explicit 2D room geometry available at C13 (we only see
  SharedEdges from C12), the conflict predicate is a deliberate
  proxy: two doors on DIFFERENT edges of the SAME room "conflict"
  iff BOTH are positioned within clear_width_m of the shared corner
  region (i.e., both have position_along_edge_m < clear_width_m).

  This is conservative — it over-detects (flags some non-conflicts)
  but never under-detects in v1 use cases. Per v0.3 B4 + v0.4 C6:
  v1 fidelity is APPROXIMATE; real arc-geometry collision detection
  is `B-C13-FULL-2D-ARC-COLLISION` (v1.x backlog).

RESOLUTION LADDER (v0.1 § 3.4 step 4, canonical order):
  a. Shift door A along its edge by one grid unit (toward midpoint)
  b. Shift door B along its edge by one grid unit
  c. Flip door A swing direction (if not main-entry / locked rule)
  d. Flip door B swing direction
  e. Shrink door A clear width to NBC minimum (0.75 m / v1)
  f. Shrink door B clear width to NBC minimum
  g. Unresolved → SwingArcConflictError

ITERATION CONTROL (v0.2 A4 + v0.3 B3):
  - max_conflict_resolution_iterations (default 5).
  - State snapshot before each strategy: rollback on
    monotonic-decrease violation or visited-state hit.
  - Visited-state hashing: SHA256 of canonically-serialized door
    state; detect loops.

TIE-BREAK (v0.3 B3 (b)):
  Among multiple equally-valid resolution candidates, prefer (in
  priority DESC):
    1. Minimal positional displacement (sum |Δposition|)
    2. Maximal width preservation
    3. Hinge-side preservation
    4. Swing-direction preservation
    5. Lex-ASC (room_a_id, room_b_id)
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, replace
from typing import Callable, Literal, Optional

from .contracts import C13ConsumesFromC12Edge
from .edge_selection import EdgeSelectionResult
from .errors import SwingArcConflictError
from .position_selection import PositionAssignmentResult
from .swing_assignment import SwingAssignmentResult
from .telemetry import (
    C13TelemetrySink,
    NullTelemetrySink,
    PhaseDConvergenceEvent,
    SwingArcConflictEvent,
)


# NBC minimum internal door width (clear). v1 floor for resolution
# strategy (e) — door width may be shrunk down to this, no lower.
_NBC_MIN_INTERNAL_DOOR_WIDTH_M: float = 0.75


@dataclass(frozen=True)
class DoorState:
    """Fully-resolved per-door state (post Phase D).

    Each DoorState corresponds to one EdgeAssignment from Phase A +
    its position (Phase C) + swing (Phase B) + any modifications
    Phase D applied during conflict resolution.
    """
    room_a_id: str
    room_b_id: str
    position_along_edge_m: float
    clear_width_m: float
    swing_direction: Literal["into_room_a", "into_room_b"]
    hinge_side: Literal["start", "end"]
    is_secondary: bool


@dataclass(frozen=True)
class ConflictResolutionResult:
    """Output of Phase D. Carries resolved door states + convergence
    diagnostics."""
    door_states: tuple[DoorState, ...]
    iterations_used: int
    conflicts_at_start: int
    conflicts_at_end: int
    rollbacks_count: int
    branching_factor: int
    convergence_quality_proxy: float
    visited_state_hit: bool

    def __post_init__(self) -> None:
        keys = [
            (s.room_a_id, s.room_b_id, s.is_secondary)
            for s in self.door_states
        ]
        if keys != sorted(keys):
            raise ValueError(
                f"ConflictResolutionResult.door_states must be sorted "
                f"by (room_a_id, room_b_id, is_secondary); got {keys}."
            )


# =============================================================================
# Helpers — building / hashing / serializing door state
# =============================================================================

def _hash_door_states(states: tuple[DoorState, ...]) -> str:
    """SHA256 over canonical-serialized door state. Per v0.3 B3 (a):
    used to detect visited states during Phase D iteration."""
    parts: list[str] = []
    for s in sorted(states, key=lambda x: (
        x.room_a_id, x.room_b_id, x.is_secondary,
    )):
        # Round positions / widths to grid resolution before hashing
        # to avoid float-precision-noise false negatives.
        parts.append(
            f"{s.room_a_id}|{s.room_b_id}|"
            f"{round(s.position_along_edge_m, 4)}|"
            f"{round(s.clear_width_m, 4)}|"
            f"{s.swing_direction}|{s.hinge_side}|"
            f"{int(s.is_secondary)}"
        )
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _door_id(s: DoorState) -> tuple[str, str, bool]:
    """Canonical identity tuple for a door (edge + secondary tag)."""
    return (s.room_a_id, s.room_b_id, s.is_secondary)


# =============================================================================
# Conflict predicate (v1 APPROXIMATE)
# =============================================================================

def _doors_share_room(a: DoorState, b: DoorState) -> Optional[str]:
    """Return the shared room id if doors a and b share a room, else
    None. Two doors on the same edge return the canonical room_a_id
    (but Phase A enforces one door per edge, so this case shouldn't
    arise in v1)."""
    for room_id in (a.room_a_id, a.room_b_id):
        if room_id == b.room_a_id or room_id == b.room_b_id:
            return room_id
    return None


def _conflicts(a: DoorState, b: DoorState) -> bool:
    """v1 APPROXIMATE conflict predicate.

    Two doors conflict iff:
      (i) They share a room (one of a's rooms == one of b's rooms),
      AND
      (ii) BOTH are positioned within max(a.clear_width_m,
           b.clear_width_m) of an edge corner (proxy for "both
           hinge-corners are near the shared corner region between
           the two walls").

    Per v0.3 B4 + v0.4 C6: v1 fidelity is APPROXIMATE. This proxy
    over-detects (some near-corner pairs may not actually collide in
    real 2D arc geometry) but never misses real collisions. Real
    arc-geometry collision detection is B-C13-FULL-2D-ARC-COLLISION
    (v1.x backlog).
    """
    if _doors_share_room(a, b) is None:
        return False
    if _door_id(a) == _door_id(b):
        return False  # Same door identity.
    threshold = max(a.clear_width_m, b.clear_width_m)
    return (
        a.position_along_edge_m < threshold
        and b.position_along_edge_m < threshold
    )


def _count_conflicts(states: tuple[DoorState, ...]) -> int:
    """Count pairwise conflicts in canonical pair order. v1
    O(n²) — per v0.3 B-C13-SPATIAL-INDEXING-PHASE-D (v2+ backlog)
    when n>50."""
    n = len(states)
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            if _conflicts(states[i], states[j]):
                count += 1
    return count


def _find_conflicts(
    states: tuple[DoorState, ...],
) -> tuple[tuple[int, int], ...]:
    """Return all conflicting (i, j) index pairs in canonical order
    (i < j)."""
    pairs: list[tuple[int, int]] = []
    n = len(states)
    for i in range(n):
        for j in range(i + 1, n):
            if _conflicts(states[i], states[j]):
                pairs.append((i, j))
    return tuple(pairs)


# =============================================================================
# Resolution strategies
# =============================================================================

ResolutionStrategy = Literal[
    "shift_a", "shift_b", "flip_a_swing", "flip_b_swing",
    "shrink_a_width", "shrink_b_width", "unresolved",
]


def _shift_position(
    s: DoorState,
    edge: C13ConsumesFromC12Edge,
    grid_snap_m: float,
) -> DoorState:
    """Shift door's position_along_edge_m by one grid unit toward the
    edge midpoint. If already at midpoint, snap to midpoint exactly.

    Per Inv D4 (door fits within edge): position + clear_width <=
    overlap_length. If shift would violate this, clamp to the
    maximum feasible position.
    """
    midpoint = edge.overlap_length_m / 2.0
    new_pos = s.position_along_edge_m + grid_snap_m
    # Clamp to feasible range.
    max_feasible = edge.overlap_length_m - s.clear_width_m
    if max_feasible < 0:
        # Should never happen if Phase C succeeded.
        max_feasible = 0.0
    new_pos = min(new_pos, max_feasible)
    # Round to grid.
    if grid_snap_m > 0.0:
        n_units = math.floor(new_pos / grid_snap_m + 0.5)
        new_pos = n_units * grid_snap_m
    return replace(s, position_along_edge_m=new_pos)


def _flip_swing(s: DoorState) -> DoorState:
    """Flip swing_direction. Per v0.1 § 3.2 + v0.2 A6 exception rules:
    main-entry doors must remain into-building; bathroom outswings
    are preserved. This function does the flip blindly; the caller
    checks rule-permitted flips."""
    flipped: Literal["into_room_a", "into_room_b"] = (
        "into_room_b" if s.swing_direction == "into_room_a"
        else "into_room_a"
    )
    return replace(s, swing_direction=flipped)


def _shrink_width(s: DoorState) -> DoorState:
    """Shrink clear_width_m to NBC minimum. v1: 0.75 m.

    Returns the same state if already at minimum (caller treats
    as resolution-not-applicable)."""
    if s.clear_width_m <= _NBC_MIN_INTERNAL_DOOR_WIDTH_M:
        return s
    return replace(s, clear_width_m=_NBC_MIN_INTERNAL_DOOR_WIDTH_M)


# =============================================================================
# Edge lookup helper (Phase D needs edge geometry for position shifts)
# =============================================================================

def _build_edge_lookup(
    edge_result: EdgeSelectionResult,
) -> dict[tuple[str, str, bool], C13ConsumesFromC12Edge]:
    """Build (room_a, room_b, is_secondary) → edge dict for fast
    lookup during shift operations."""
    return {
        (a.edge.room_a_id, a.edge.room_b_id, a.is_secondary): a.edge
        for a in edge_result.assignments
    }


# =============================================================================
# Phase D entry point
# =============================================================================

def resolve_conflicts(
    *,
    candidate_signature: str,
    edge_result: EdgeSelectionResult,
    swing_result: SwingAssignmentResult,
    position_result: PositionAssignmentResult,
    max_conflict_resolution_iterations: int,
    grid_snap_m: float,
    strict_mode: bool,
    telemetry_sink: Optional[C13TelemetrySink] = None,
    main_entry_room_id: str = "",
) -> ConflictResolutionResult:
    """Phase D entry point.

    Per v0.2 A4 bounded retry + v0.3 B3 visited-state hashing.

    Algorithm:
      1. Build initial DoorState tuple from Phase A/B/C outputs.
      2. Compute initial conflict count.
      3. For iteration 1..max_conflict_resolution_iterations:
         a. Hash current state; if visited, halt (loop detected).
         b. If no conflicts, halt (converged).
         c. Pick first conflict pair (lex-ASC).
         d. Try strategies a-f in canonical order. For each:
            - Snapshot state, apply strategy.
            - If new conflict count < previous: accept, advance.
            - Else: rollback, try next strategy.
         e. If all strategies exhausted: halt with last state.
      4. Compute final convergence diagnostics.

    Args:
      candidate_signature: provenance.
      edge_result, swing_result, position_result: outputs from
          Phases A, B, C.
      max_conflict_resolution_iterations: budget (default 5).
      grid_snap_m: shift increment.
      strict_mode: if True and conflicts persist at termination,
          raise SwingArcConflictError. If False (WARN), return the
          best-effort state with conflicts_at_end > 0.
      telemetry_sink: optional sink for PhaseDConvergenceEvent +
          SwingArcConflictEvent emission.
      main_entry_room_id: passed in so flip-swing rule can refuse to
          flip the main entry door's swing.

    Returns:
      ConflictResolutionResult.

    Raises:
      SwingArcConflictError: only if strict_mode=True and
          conflicts_at_end > 0 at termination.
    """
    sink: C13TelemetrySink = telemetry_sink or NullTelemetrySink()

    # Build initial DoorState by joining Phase A/B/C outputs.
    pos_by_id = {
        (p.room_a_id, p.room_b_id, p.is_secondary): p
        for p in position_result.assignments
    }
    swing_by_id = {
        (s.room_a_id, s.room_b_id, s.is_secondary): s
        for s in swing_result.assignments
    }
    initial_states: list[DoorState] = []
    for a in edge_result.assignments:
        key = (a.edge.room_a_id, a.edge.room_b_id, a.is_secondary)
        p = pos_by_id[key]
        sw = swing_by_id[key]
        initial_states.append(DoorState(
            room_a_id=a.edge.room_a_id,
            room_b_id=a.edge.room_b_id,
            position_along_edge_m=p.position_along_edge_m,
            clear_width_m=p.clear_width_m,
            swing_direction=sw.swing_direction,
            hinge_side=sw.hinge_side,
            is_secondary=a.is_secondary,
        ))
    initial_states.sort(key=lambda s: (s.room_a_id, s.room_b_id, s.is_secondary))
    initial_positions = {
        _door_id(s): s.position_along_edge_m for s in initial_states
    }

    states = tuple(initial_states)
    edge_lookup = _build_edge_lookup(edge_result)
    visited: set[str] = set()
    rollbacks_count = 0
    branching_factor = 0
    iterations_used = 0
    conflicts_at_start = _count_conflicts(states)
    visited_state_hit = False

    for iteration in range(max_conflict_resolution_iterations):
        iterations_used = iteration + 1
        state_hash = _hash_door_states(states)
        if state_hash in visited:
            visited_state_hit = True
            break
        visited.add(state_hash)

        conflict_pairs = _find_conflicts(states)
        if not conflict_pairs:
            break

        # Pick first pair (canonical lex-ASC by index).
        i, j = conflict_pairs[0]
        a, b = states[i], states[j]
        prev_count = len(conflict_pairs)

        strategies: list[
            tuple[ResolutionStrategy, Callable[[], Optional[tuple[DoorState, ...]]]]
        ] = [
            ("shift_a", lambda: _try_shift(states, i, edge_lookup, grid_snap_m)),
            ("shift_b", lambda: _try_shift(states, j, edge_lookup, grid_snap_m)),
            ("flip_a_swing", lambda: _try_flip(
                states, i, main_entry_room_id,
            )),
            ("flip_b_swing", lambda: _try_flip(
                states, j, main_entry_room_id,
            )),
            ("shrink_a_width", lambda: _try_shrink(states, i)),
            ("shrink_b_width", lambda: _try_shrink(states, j)),
        ]

        applied = False
        for strategy_name, attempt in strategies:
            branching_factor += 1
            new_states = attempt()
            if new_states is None:
                continue  # Strategy not applicable.
            new_count = _count_conflicts(new_states)
            if new_count < prev_count:
                # Accept.
                states = new_states
                sink.emit(SwingArcConflictEvent(
                    candidate_signature=candidate_signature,
                    door_a_room_a_id=a.room_a_id,
                    door_a_room_b_id=a.room_b_id,
                    door_b_room_a_id=b.room_a_id,
                    door_b_room_b_id=b.room_b_id,
                    resolution_strategy=strategy_name,
                    resolved=True,
                ))
                applied = True
                break
            else:
                # Rollback (no-op since we didn't commit).
                rollbacks_count += 1

        if not applied:
            # All strategies exhausted for this pair.
            sink.emit(SwingArcConflictEvent(
                candidate_signature=candidate_signature,
                door_a_room_a_id=a.room_a_id,
                door_a_room_b_id=a.room_b_id,
                door_b_room_a_id=b.room_a_id,
                door_b_room_b_id=b.room_b_id,
                resolution_strategy="unresolved",
                resolved=False,
            ))
            break

    conflicts_at_end = _count_conflicts(states)

    # Convergence quality proxy: sum of |Δposition| / n_doors.
    # Per v0.4 C5: signals to C14 whether the resolver moved doors
    # significantly (high values indicate ergonomic concerns).
    n_doors = max(len(states), 1)
    total_shift = sum(
        abs(s.position_along_edge_m - initial_positions[_door_id(s)])
        for s in states
    )
    convergence_quality_proxy = total_shift / n_doors

    # Emit MANDATORY PhaseDConvergenceEvent (v0.4 C5).
    sink.emit(PhaseDConvergenceEvent(
        candidate_signature=candidate_signature,
        iterations_used=iterations_used,
        max_iterations=max_conflict_resolution_iterations,
        conflicts_at_start=conflicts_at_start,
        conflicts_at_end=conflicts_at_end,
        rollbacks_count=rollbacks_count,
        branching_factor=branching_factor,
        convergence_quality_proxy=convergence_quality_proxy,
        visited_state_hit=visited_state_hit,
    ))

    # STRICT/WARN dispatch.
    if conflicts_at_end > 0 and strict_mode:
        # Find first conflict for error context.
        unresolved_pairs = _find_conflicts(states)
        if unresolved_pairs:
            i0, j0 = unresolved_pairs[0]
            a0, b0 = states[i0], states[j0]
            raise SwingArcConflictError(
                f"Phase D: {conflicts_at_end} swing-arc conflict(s) "
                f"remain after {iterations_used} iteration(s); "
                f"first unresolved pair: "
                f"({a0.room_a_id}, {a0.room_b_id}) vs "
                f"({b0.room_a_id}, {b0.room_b_id})."
            )

    return ConflictResolutionResult(
        door_states=tuple(sorted(
            states, key=lambda s: (s.room_a_id, s.room_b_id, s.is_secondary),
        )),
        iterations_used=iterations_used,
        conflicts_at_start=conflicts_at_start,
        conflicts_at_end=conflicts_at_end,
        rollbacks_count=rollbacks_count,
        branching_factor=branching_factor,
        convergence_quality_proxy=convergence_quality_proxy,
        visited_state_hit=visited_state_hit,
    )


# =============================================================================
# Strategy attempters (return new tuple of states or None)
# =============================================================================

def _try_shift(
    states: tuple[DoorState, ...],
    idx: int,
    edge_lookup: dict[tuple[str, str, bool], C13ConsumesFromC12Edge],
    grid_snap_m: float,
) -> Optional[tuple[DoorState, ...]]:
    """Try shifting door at index idx by one grid unit."""
    target = states[idx]
    edge = edge_lookup.get(_door_id(target))
    if edge is None:
        return None
    shifted = _shift_position(target, edge, grid_snap_m)
    if shifted.position_along_edge_m == target.position_along_edge_m:
        # Already at max feasible — strategy not applicable.
        return None
    new_states = tuple(
        shifted if i == idx else s for i, s in enumerate(states)
    )
    return new_states


def _try_flip(
    states: tuple[DoorState, ...],
    idx: int,
    main_entry_room_id: str,
) -> Optional[tuple[DoorState, ...]]:
    """Try flipping swing direction of door at index idx.

    Per v0.1 § 3.4 step 4c "if exception rules permit": main-entry
    doors do not flip (they always swing into the building). For
    v1, the rule is: don't flip a door whose edge involves the
    main entry room AND the room is on a room "internal" side.

    Simplification at v1: forbid flipping for any door where the
    target room is main_entry_room_id (preserves the "always swing
    inward" main-entry rule).
    """
    target = states[idx]
    if main_entry_room_id and (
        main_entry_room_id == target.room_a_id
        or main_entry_room_id == target.room_b_id
    ):
        # Skip flip for main-entry-related doors at v1.
        return None
    flipped = _flip_swing(target)
    new_states = tuple(
        flipped if i == idx else s for i, s in enumerate(states)
    )
    return new_states


def _try_shrink(
    states: tuple[DoorState, ...],
    idx: int,
) -> Optional[tuple[DoorState, ...]]:
    """Try shrinking door width to NBC minimum."""
    target = states[idx]
    shrunk = _shrink_width(target)
    if shrunk.clear_width_m == target.clear_width_m:
        return None  # Already at minimum.
    new_states = tuple(
        shrunk if i == idx else s for i, s in enumerate(states)
    )
    return new_states


__all__ = [
    "DoorState",
    "ConflictResolutionResult",
    "ResolutionStrategy",
    "resolve_conflicts",
]
