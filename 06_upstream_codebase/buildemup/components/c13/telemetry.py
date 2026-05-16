"""
BuildemUp — Component 13 — telemetry
=====================================

Per C13 SPEC v1.0 LOCKED § 9 (event types) + v0.4 C5 (mandatory
day-1 PhaseDConvergenceEvent) + v0.4 C5 quality-degradation
disclosure.

C13 emits 6 event types covering selection, swing assignment,
conflict resolution, and overall placement timing:

1. EdgeSelectionEvent (per Phase A primary edge pick)
2. SwingDirectionEvent (per Phase B swing decision, including
   bathroom-outswing exceptions per v0.2 A6)
3. PhaseDConvergenceEvent (per candidate; MANDATORY at v1 per
   v0.4 C5 — captures iterations / branching / convergence proxy
   for B-C13-CONVERGENCE-CORPUS analysis)
4. SwingArcConflictEvent (per detected conflict; resolution path)
5. AdvisoryFlagEmittedEvent (per emitted advisory flag — for
   density-bound monitoring per Inv D16)
6. DoorPlacementCompleteEvent (per candidate, success or failure;
   wallclock + door count)

Telemetry sink protocol mirrors C12 / C11b: a sink instance exposes
an emit(event) method. NullTelemetrySink is the zero-overhead
default. Events are frozen dataclasses for hash stability.

Per v0.4 C5 mandatory disclosure:
> "Phase D terminates at the first conflict-free state within
>  iteration budget. This state may be a local minimum that is
>  conflict-free but ergonomically poor. C14 is responsible for
>  detecting + scoring such cases."
PhaseDConvergenceEvent.convergence_quality_proxy gives an objective
signal (sum of |position shifts| / n_doors) that C14 or external
analysis can consume.

Telemetry is cache-IRRELEVANT (observability layer). Adding event
fields does not bump cache keys. Renaming event types or removing
fields would bump ADVISORY_SCHEMA_VERSION-style governance, but
v1.0 freezes the 6-event vocabulary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from .schema import AdvisoryCategory, AdvisoryFlagKind, C13Phase


# =============================================================================
# Event types (frozen dataclasses for hash stability)
# =============================================================================

@dataclass(frozen=True)
class EdgeSelectionEvent:
    """Per Phase A. One event per primary edge picked for a room.

    Fields:
      candidate_signature: provenance back to source PlacedCandidate.
      room_id: which room's edge was just picked.
      selected_edge_room_a_id / selected_edge_room_b_id: canonical
          ids of the picked edge.
      selection_tier: which v0.3 B6 priority tier matched
          ('entry' / 'corridor_adjacent' / 'lex_asc').
      feasible_edge_count: how many feasible edges the room had
          (for diversity analysis — B-C13-CONVERGENCE-CORPUS uses
          this to detect rooms with one feasible edge vs many).
      is_secondary: True if this was a secondary door selection
          (per v0.3 B8 + v0.4 C4); False if primary.
    """
    candidate_signature: str
    room_id: str
    selected_edge_room_a_id: str
    selected_edge_room_b_id: str
    selection_tier: Literal["entry", "corridor_adjacent", "lex_asc"]
    feasible_edge_count: int
    is_secondary: bool


@dataclass(frozen=True)
class SwingDirectionEvent:
    """Per Phase B. One event per swing-direction decision.

    Fields:
      candidate_signature: provenance.
      room_a_id / room_b_id: the door's canonical edge identifier.
      swing_direction: 'into_room_a' or 'into_room_b'.
      decision_rule: which v0.2 A6 / v0.1 § 3.2 rule fired:
          'main_entry_into_building': main entry always swings inward
          'bathroom_inswing_default': bathroom area >= threshold
          'bathroom_outswing_compact': bathroom area < threshold (A6 (a))
          'smaller_room_inswing': default (door swings INTO smaller
              room so larger room's circulation isn't blocked)
          'fallback_lex_asc': tie-break when areas are equal
              (deterministic per Inv D7).
    """
    candidate_signature: str
    room_a_id: str
    room_b_id: str
    swing_direction: Literal["into_room_a", "into_room_b"]
    decision_rule: Literal[
        "main_entry_into_building",
        "bathroom_inswing_default",
        "bathroom_outswing_compact",
        "smaller_room_inswing",
        "fallback_lex_asc",
    ]


@dataclass(frozen=True)
class PhaseDConvergenceEvent:
    """Per C13 v0.4 C5 MANDATORY day-1 telemetry. One event per
    candidate that reached Phase D.

    Fields:
      candidate_signature: provenance.
      iterations_used: actual Phase D iteration count.
      max_iterations: configured max_conflict_resolution_iterations.
      conflicts_at_start: number of swing-arc conflicts pre-Phase-D.
      conflicts_at_end: number of conflicts at termination
          (0 = converged; >0 = exhausted budget or visited-state
          loop).
      rollbacks_count: number of state rollbacks taken (v0.2 A4
          snapshot pattern).
      branching_factor: total resolution strategies tried summed
          across iterations.
      convergence_quality_proxy: sum of |position shifts| / n_doors
          (per v0.4 C5). Higher values indicate the resolver moved
          doors significantly — may indicate ergonomically poor
          local minimum.
      visited_state_hit: True iff Phase D terminated due to a
          visited-state hash collision (v0.3 B3 loop prevention).
    """
    candidate_signature: str
    iterations_used: int
    max_iterations: int
    conflicts_at_start: int
    conflicts_at_end: int
    rollbacks_count: int
    branching_factor: int
    convergence_quality_proxy: float
    visited_state_hit: bool


@dataclass(frozen=True)
class SwingArcConflictEvent:
    """Per Phase D. One event per detected swing-arc conflict.

    Fields:
      candidate_signature: provenance.
      door_a_room_a_id / door_a_room_b_id: first door's canonical id.
      door_b_room_a_id / door_b_room_b_id: second door's canonical id.
      resolution_strategy: which v0.1 § 3.4 / v0.3 B3 strategy
          applied to resolve. None if conflict persisted.
      resolved: True iff the conflict was resolved within budget.
    """
    candidate_signature: str
    door_a_room_a_id: str
    door_a_room_b_id: str
    door_b_room_a_id: str
    door_b_room_b_id: str
    resolution_strategy: Literal[
        "shift_a",
        "shift_b",
        "flip_a_swing",
        "flip_b_swing",
        "shrink_a_width",
        "shrink_b_width",
        "unresolved",
    ]
    resolved: bool


@dataclass(frozen=True)
class AdvisoryFlagEmittedEvent:
    """Per Phase E. One event per AdvisoryFlag entered into the result.

    Useful for monitoring Inv D16 density (n_rooms × 1.5) — if a
    candidate emits flags approaching the density bound, that's a
    signal worth investigating.

    Fields:
      candidate_signature: provenance.
      flag_kind: which of the 6 LOCKED kinds (per AdvisoryFlagKind).
      affected_room_id: room id this flag pertains to.
      category: AdvisoryCategory enum value (per v0.4 C1).
      severity: 'info' / 'warning' / 'concern'.
    """
    candidate_signature: str
    flag_kind: AdvisoryFlagKind
    affected_room_id: str
    category: AdvisoryCategory
    severity: Literal["info", "warning", "concern"]


@dataclass(frozen=True)
class DoorPlacementCompleteEvent:
    """Per candidate. One event when placement finishes (success OR
    failure). For wallclock + door-count monitoring against the
    per_candidate_wallclock_seconds budget.

    Fields:
      candidate_signature: provenance.
      success: True iff a SuccessfulDoorPlacement was produced.
      door_count: number of doors in result (0 if failure).
      advisory_flag_count: number of advisory flags emitted.
      wallclock_seconds: actual wallclock time consumed.
      terminal_phase: which phase the pipeline reached
          (phaseA / phaseB / phaseC / phaseD / phaseE / phaseF).
          On failure: the phase that surfaced the error.
          On success: always 'phaseF' (verification cleared).
    """
    candidate_signature: str
    success: bool
    door_count: int
    advisory_flag_count: int
    wallclock_seconds: float
    terminal_phase: C13Phase


# =============================================================================
# Sink Protocol + NullTelemetrySink default
# =============================================================================

# Per C12 / C11b precedent: the sink protocol is a single-method
# interface. emit() accepts ANY of the 6 event types as a discriminated
# union (Python's runtime doesn't enforce this, but type checkers can
# via Union — kept loose at runtime for sink-implementation flexibility).
TelemetryEvent = (
    EdgeSelectionEvent
    | SwingDirectionEvent
    | PhaseDConvergenceEvent
    | SwingArcConflictEvent
    | AdvisoryFlagEmittedEvent
    | DoorPlacementCompleteEvent
)


@runtime_checkable
class C13TelemetrySink(Protocol):
    """C13 telemetry sink. Implementations route events to logs,
    metrics backends, or in-memory buffers (for tests).

    Per cache-irrelevance: emit() must NOT mutate the candidate or
    affect output. It is observability only.
    """

    def emit(self, event: TelemetryEvent) -> None:
        """Record a single telemetry event. MUST NOT raise."""
        ...


class NullTelemetrySink:
    """Zero-overhead default. Drops all events on the floor.

    Per C12 precedent: when DoorPlacementConfig.telemetry_sink is None,
    the orchestrator instantiates NullTelemetrySink at entry to keep
    the emit() call sites uniform.
    """

    __slots__ = ()

    def emit(self, event: TelemetryEvent) -> None:
        return None


class InMemoryTelemetrySink:
    """Test/dev sink that retains every emitted event in order.

    Per Inv D7 byte-equal replay: events emitted from a deterministic
    run will be byte-equal across runs. Tests assert on this.

    NOT for production: unbounded memory growth.
    """

    __slots__ = ("_events",)

    def __init__(self) -> None:
        self._events: list[TelemetryEvent] = []

    def emit(self, event: TelemetryEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> tuple[TelemetryEvent, ...]:
        """Immutable view of emitted events for assertion."""
        return tuple(self._events)

    def events_of_type(
        self,
        event_type: type,
    ) -> tuple[TelemetryEvent, ...]:
        """Filtered view by event class. Convenience for tests."""
        return tuple(e for e in self._events if isinstance(e, event_type))

    def clear(self) -> None:
        self._events.clear()


# =============================================================================
# Public exports
# =============================================================================

__all__ = [
    # Event types
    "EdgeSelectionEvent",
    "SwingDirectionEvent",
    "PhaseDConvergenceEvent",
    "SwingArcConflictEvent",
    "AdvisoryFlagEmittedEvent",
    "DoorPlacementCompleteEvent",
    # Sink protocol + impls
    "TelemetryEvent",
    "C13TelemetrySink",
    "NullTelemetrySink",
    "InMemoryTelemetrySink",
]
