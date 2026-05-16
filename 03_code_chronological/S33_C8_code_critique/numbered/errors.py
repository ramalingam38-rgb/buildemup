"""
BuildemUp† — Component 8 (Corridor Designer) — Errors module.

Per C8 SPEC v0.5 LOCKED § 6 (Failure modes) and § 14.17 / § 14.23.

Three C8-specific exception types:
  - CorridorTooNarrowError (B-109): raised when no GRID_FRACTION candidate
                                     ≥ regulatory_min_width_m fits.
  - CorridorSelfIntersectionError: raised when topology dispatch produces
                                     overlapping segments outside junction
                                     tolerance (programmer error per § 14.17).
  - CorridorDispatchError: raised when topology dispatch fails for an
                            oriented candidate. Carries diagnostic metadata
                            (per § 14.23) for caller-side retry orchestration
                            (B-126). Auto-retry intentionally NOT performed
                            inside C8 (Pattern A pushback).

†= placeholder name marker.
"""
from __future__ import annotations

from typing import Optional


class CorridorTooNarrowError(ValueError):
    """No corridor width >= regulatory_min_width_m fits within the grid.

    Per § 4.3 / § 6 / B-109. Raised when:
      - All GRID_FRACTION candidates × bay_min are below regulatory minimum, OR
      - Envelope-overflow narrowing fallback exhausts the candidate list.

    Graceful-fallback (e.g., narrow plot triggers single-loaded corridor)
    is deferred to B-109 — first user-case-driven implementation.
    """

    def __init__(
        self,
        message: str,
        *,
        bay_min_m: float | None = None,
        regulatory_min_width_m: float | None = None,
        candidate_widths_m: tuple[float, ...] | None = None,
    ) -> None:
        super().__init__(message)
        self.bay_min_m = bay_min_m
        self.regulatory_min_width_m = regulatory_min_width_m
        self.candidate_widths_m = candidate_widths_m


class CorridorSelfIntersectionError(RuntimeError):
    """Topology dispatch produced overlapping segments outside junction tolerance.

    Per § 4.7 / § 14.17. This is a programmer error — the topology dispatcher
    should never produce a self-intersecting corridor. Raised eagerly during
    construction so the bug is surfaced (deliberate-raise per § 14.17).

    Soft fallback (auto-skip + log) was rejected at v0.2 walk #2 (Drawback 8 /
    § 14.17 Pattern A pushback) because it would mask a real defect.
    """

    def __init__(
        self,
        message: str,
        *,
        segment_a_index: int | None = None,
        segment_b_index: int | None = None,
        overlap_box: tuple[float, float, float, float] | None = None,
    ) -> None:
        super().__init__(message)
        self.segment_a_index = segment_a_index
        self.segment_b_index = segment_b_index
        self.overlap_box = overlap_box


class CorridorDispatchError(RuntimeError):
    """Topology dispatch failed for an oriented candidate.

    Per § 6 / § 14.23 (NEW v0.4 enriched). Carries diagnostic metadata so the
    caller can orchestrate retry/skip without coupling C8 to a retry policy:
      - candidate_index: position in the input tuple
      - topology_kind: which TopologyKind was attempted
      - failure_phase: which dispatch phase failed
        ('spatial_model', 'grid_alignment', 'width_selection',
         'endpoint_construction', 'spatial_feasibility', 'validator')
      - suggested_alternative_topologies: tuple of TopologyKind values that
        the caller might try (e.g., narrow plot → STRIP).

    Auto-retry intentionally NOT performed inside C8 (B-126 / § 14.23 +
    industry-consensus circuit-breaker pattern: callee exposes diagnostic
    metadata; caller decides retry policy).
    """

    def __init__(
        self,
        message: str,
        *,
        candidate_index: int | None = None,
        topology_kind: Optional[str] = None,
        failure_phase: Optional[str] = None,
        suggested_alternative_topologies: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.candidate_index = candidate_index
        self.topology_kind = topology_kind
        self.failure_phase = failure_phase
        self.suggested_alternative_topologies = suggested_alternative_topologies


__all__ = [
    "CorridorTooNarrowError",
    "CorridorSelfIntersectionError",
    "CorridorDispatchError",
]
