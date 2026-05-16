"""
BuildemUp — Component 12 — telemetry
=====================================

Per C12 SPEC v1.0 LOCKED v0.4-A1 backlog items:
- B-C12-PLACEMENT-DIVERSITY-TELEMETRY
- B-C12-MFRA-CONVERGENCE-TELEMETRY
- B-C12-ADJACENCY-COVERAGE-TELEMETRY
- B-C12-PERFORMANCE-TELEMETRY
- B-C12-UNKNOWN-CATEGORY-TELEMETRY
- B-C12-IRREGULAR-ENVELOPE-TELEMETRY

Telemetry is INTENTIONALLY shipped at v1 as data-type definitions +
a sink pattern. The actual emission is wired through the orchestrator
via a config field (TelemetrySink). Production deployments install a
real sink; tests can install a list-collector sink; default is a
NullTelemetrySink that drops everything.

NO global state. NO module-level mutables. Each batch produces its
own telemetry events; the sink is the only place state accumulates.

Per v0.5-A2 + v0.6 governance: telemetry is observability-only at v1.
B-C12-TELEMETRY-LIFECYCLE-GOVERNANCE (Walk #6 Item 8) governs
retention / classification post-v1.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


# =============================================================================
# Event types — frozen dataclasses, one per backlog telemetry stream
# =============================================================================


@dataclass(frozen=True)
class PlacementDiversityEvent:
    """Per B-C12-PLACEMENT-DIVERSITY-TELEMETRY.

    Captures structural diversity properties of one slicing-tree
    output. Aggregated across batches, surfaces bias in the heuristic
    (e.g., always cuts vertically first → repetitive layouts).
    """
    candidate_signature: str
    n_rooms: int
    vertical_cuts_used: int
    horizontal_cuts_used: int
    max_recursion_depth: int


@dataclass(frozen=True)
class MfraConvergenceEvent:
    """Per B-C12-MFRA-CONVERGENCE-TELEMETRY.

    One event per MFRA invocation. delta_progression captures the
    per-retry δ values, enabling distributional analysis of the
    monotonic-δ heuristic's empirical behaviour."""
    source_multifloor_signature: str
    n_floors: int
    converged: bool
    retries_used: int
    delta_progression: tuple[float, ...]
    final_max_misalignment_m: float
    abort_reason: Literal["converged", "retry_budget_exhausted", "divergence"]


@dataclass(frozen=True)
class AdjacencyCoverageEvent:
    """Per B-C12-ADJACENCY-COVERAGE-TELEMETRY.

    Per-candidate counts of (HARD/SOFT) hints that were satisfied
    vs not. Surfaces upstream hint-quality issues without C12 making
    policy decisions."""
    candidate_signature: str
    hard_hints_total: int
    hard_hints_satisfied: int
    soft_hints_total: int
    soft_hints_satisfied: int


@dataclass(frozen=True)
class PerformanceEvent:
    """Per B-C12-PERFORMANCE-TELEMETRY.

    Per-candidate wallclock + room-count snapshot. Aggregated
    distributions catch room counts exceeding the v1 n≤15 assumption
    + performance degradation."""
    candidate_signature: str
    n_rooms: int
    wallclock_seconds: float
    phase: Literal["single_floor", "multi_floor"]


@dataclass(frozen=True)
class UnknownCategoryEvent:
    """Per B-C12-UNKNOWN-CATEGORY-TELEMETRY.

    Emitted when normalize_other_room_category falls through to
    the "other" bucket. Surfaces alias-map growth pressure for
    B-C12-LAYERED-ALIAS-NORMALIZATION."""
    raw_category: str
    normalized_to: str  # always "other" at v1


@dataclass(frozen=True)
class IrregularEnvelopeRejectionEvent:
    """Per B-C12-IRREGULAR-ENVELOPE-TELEMETRY.

    Reserved for when irregular-envelope rejection becomes a
    measurable production phenomenon. v1 doesn't emit these yet
    (no irregular-envelope ingress path until
    B-C12-IRREGULAR-ENVELOPES); the event type is defined so
    future emission doesn't require schema migration."""
    envelope_signature: str
    rejection_reason: str


# =============================================================================
# Sink interface — single Protocol-style ABC for all sinks
# =============================================================================


class TelemetrySink(ABC):
    """Abstract sink for C12 telemetry events.

    Implementations:
      - NullTelemetrySink: drops everything (production default).
      - ListTelemetrySink: collects into in-memory lists (tests).
      - Application-specific sinks: push to Prometheus / OTLP / etc.

    Methods are intentionally narrow: one per event type. Adding new
    event types requires extending the sink interface, which is the
    right governance signal (per Walk #6 Item 8 lifecycle concerns).
    """

    @abstractmethod
    def record_diversity(self, event: PlacementDiversityEvent) -> None: ...

    @abstractmethod
    def record_mfra_convergence(self, event: MfraConvergenceEvent) -> None: ...

    @abstractmethod
    def record_adjacency_coverage(self, event: AdjacencyCoverageEvent) -> None: ...

    @abstractmethod
    def record_performance(self, event: PerformanceEvent) -> None: ...

    @abstractmethod
    def record_unknown_category(self, event: UnknownCategoryEvent) -> None: ...

    @abstractmethod
    def record_irregular_envelope_rejection(
        self, event: IrregularEnvelopeRejectionEvent,
    ) -> None: ...


class NullTelemetrySink(TelemetrySink):
    """Drops all events. Production default — zero overhead when
    telemetry is not actively configured.

    Per Rule of "no surprises": a default config produces zero
    telemetry payload; opting in is explicit."""

    def record_diversity(self, event: PlacementDiversityEvent) -> None:
        pass

    def record_mfra_convergence(self, event: MfraConvergenceEvent) -> None:
        pass

    def record_adjacency_coverage(self, event: AdjacencyCoverageEvent) -> None:
        pass

    def record_performance(self, event: PerformanceEvent) -> None:
        pass

    def record_unknown_category(self, event: UnknownCategoryEvent) -> None:
        pass

    def record_irregular_envelope_rejection(
        self, event: IrregularEnvelopeRejectionEvent,
    ) -> None:
        pass


@dataclass
class ListTelemetrySink(TelemetrySink):
    """Collects events into in-memory lists. Test-friendly.

    NOT frozen (lists mutate). Each list field is independently
    mutable to avoid cross-contamination across event types.

    Production code SHOULD NOT use this sink — memory grows unbounded.
    Production sinks should batch + flush externally.
    """
    diversity_events: list = field(default_factory=list)
    mfra_events: list = field(default_factory=list)
    adjacency_events: list = field(default_factory=list)
    performance_events: list = field(default_factory=list)
    unknown_category_events: list = field(default_factory=list)
    irregular_envelope_events: list = field(default_factory=list)

    def record_diversity(self, event: PlacementDiversityEvent) -> None:
        self.diversity_events.append(event)

    def record_mfra_convergence(self, event: MfraConvergenceEvent) -> None:
        self.mfra_events.append(event)

    def record_adjacency_coverage(self, event: AdjacencyCoverageEvent) -> None:
        self.adjacency_events.append(event)

    def record_performance(self, event: PerformanceEvent) -> None:
        self.performance_events.append(event)

    def record_unknown_category(self, event: UnknownCategoryEvent) -> None:
        self.unknown_category_events.append(event)

    def record_irregular_envelope_rejection(
        self, event: IrregularEnvelopeRejectionEvent,
    ) -> None:
        self.irregular_envelope_events.append(event)

    def total_events(self) -> int:
        return (
            len(self.diversity_events)
            + len(self.mfra_events)
            + len(self.adjacency_events)
            + len(self.performance_events)
            + len(self.unknown_category_events)
            + len(self.irregular_envelope_events)
        )


# Module-level default — safe to import + use without configuration.
DEFAULT_TELEMETRY_SINK: TelemetrySink = NullTelemetrySink()


__all__ = [
    # Event types
    "PlacementDiversityEvent",
    "MfraConvergenceEvent",
    "AdjacencyCoverageEvent",
    "PerformanceEvent",
    "UnknownCategoryEvent",
    "IrregularEnvelopeRejectionEvent",
    # Sink interface + implementations
    "TelemetrySink",
    "NullTelemetrySink",
    "ListTelemetrySink",
    "DEFAULT_TELEMETRY_SINK",
]
