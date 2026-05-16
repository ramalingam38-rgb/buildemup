"""
BuildemUp — Component 12 — orchestrator (top-level entry point)
================================================================

Per C12 SPEC v1.0 LOCKED § 3 (phase orchestration) + § 5 (public API).

Top-level `place_and_align()` orchestrates the full pipeline:

  Phase 0:  schema-version probes + capability-flag assertions
  Phase 0b: corridor zone reservation + reachability BFS
  Phase 1:  single-floor placement (slicing-tree)
  Phase 1b: vertical core reservation (MF only)
  Phase 2:  VAV alignment + MFRA convergence (MF only)
  Phase 3:  shared-edge derivation + adjacency validation

STRICT vs WARN mode dispatch:
- STRICT: any PerCandidatePlacementError raises immediately.
- WARN:  per-candidate failures recorded in batch result; batch continues.

The orchestrator is INTENTIONALLY a thin assembly layer. All the
algorithmic work lives in the per-phase modules. Bug fixes generally
land in the phase modules, not here.

Two public entry points:
- ``place_and_align()`` returns just PlacementBatchResult.
- ``place_and_align_with_provenance()`` returns (BatchResult, Provenance).
  Provenance is the production-useful metadata surface; keeping it
  separate preserves the v1.0 LOCKED PlacementBatchResult schema.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from .config import PlacementConfig
from .env_fingerprint import (
    C12EnvironmentFingerprint,
    capture_c12_environment_fingerprint,
    compute_c12_cache_key,
)
from .errors import (
    AdjacencyConstraintViolationError,
    DoorwayFeasibilityError,
    PerCandidatePlacementError,
)
from .input_resolution import (
    assert_materialized_capability,
    assert_upstream_schema_versions,
)
from .mfra import absorb_multi_floor_placements
from .provenance import CandidateProvenanceEntry, PlacementProvenance
from .schema import (
    FailureRecord,
    MultiFloorPlacedCandidate,
    PlacedCandidate,
    PlacementBatchResult,
)
from .shared_edges import derive_shared_edges
from .slicing_kd_tree import RoomSpec, place_rooms_slicing_tree
from .telemetry import (
    AdjacencyCoverageEvent,
    MfraConvergenceEvent,
    NullTelemetrySink,
    PerformanceEvent,
    TelemetrySink,
)
from .versioning import C12_VERSION
from .vertical_core_reservation import VerticalCoreReservation


# =============================================================================
# Helpers — telemetry + provenance
# =============================================================================


def _resolve_sink(config: PlacementConfig) -> TelemetrySink:
    """Resolve config.telemetry_sink to a TelemetrySink instance.

    Default (None) → NullTelemetrySink (zero-overhead drop-all).
    Configured value MUST be a TelemetrySink instance.
    """
    sink = config.telemetry_sink
    if sink is None:
        return NullTelemetrySink()
    if not isinstance(sink, TelemetrySink):
        raise TypeError(
            f"PlacementConfig.telemetry_sink must be a TelemetrySink "
            f"instance or None; got {type(sink).__name__}."
        )
    return sink


def _count_adjacency_satisfaction(
    hints: tuple[tuple[str, str, str], ...],
    shared_edges: tuple,
) -> tuple[int, int, int, int]:
    """Returns (hard_total, hard_satisfied, soft_total, soft_satisfied).

    Per B-C12-ADJACENCY-COVERAGE-TELEMETRY.
    """
    edge_pairs = {(e.room_a_id, e.room_b_id) for e in shared_edges}
    hard_total = hard_sat = soft_total = soft_sat = 0
    for a, b, kind in hints:
        if a > b:
            a, b = b, a
        adj = (a, b) in edge_pairs
        if kind == "hard":
            hard_total += 1
            if adj:
                hard_sat += 1
        elif kind == "soft":
            soft_total += 1
            if adj:
                soft_sat += 1
    return (hard_total, hard_sat, soft_total, soft_sat)


# =============================================================================
# Single-floor candidate input contract
# =============================================================================

@dataclass(frozen=True)
class SingleFloorPlacementInput:
    """One single-floor placement input. The orchestrator consumes a
    tuple of these (typically built upstream by adapting C11b
    RefinedCandidate + C9 FloorRoomBrief).

    Designed to be testable in isolation without requiring the full
    upstream C11b stack: a future integration adapter (S45) maps
    RefinedCandidate → SingleFloorPlacementInput.
    """
    candidate_signature: str
    capability_mode: str
    placement_safe: bool
    geometry_materialized: bool
    rooms: tuple[RoomSpec, ...]
    envelope_width_m: float
    envelope_depth_m: float
    # Adjacency hints (HARD/SOFT) per v0.2-A5 / C9 amendment.
    # Each entry: (room_a_id, room_b_id, kind_str) where kind_str ∈ {"hard", "soft"}.
    adjacency_hints: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class MultiFloorPlacementInput:
    """Multi-floor placement input.

    Each floor is a SingleFloorPlacementInput plus a floor_label.
    Shared across floors: feature_room_ids_by_floor (per VAV) and
    vertical_cores_reserved (per Phase 1b).
    """
    source_signature: str
    floors: tuple[tuple[str, SingleFloorPlacementInput], ...]  # (label, input)
    feature_room_ids_by_floor: dict[str, set[str]]
    vertical_cores: tuple[VerticalCoreReservation, ...]


# =============================================================================
# Single-floor pipeline
# =============================================================================

def _place_single_floor(
    sf_input: SingleFloorPlacementInput,
    *,
    config: PlacementConfig,
) -> PlacedCandidate:
    """Run Phase 0 + Phase 1 + Phase 3 for one single-floor input.

    Raises PerCandidatePlacementError subclasses on failure.
    """
    # Phase 0 step 3: capability flag assertion
    assert_materialized_capability(
        candidate_signature=sf_input.candidate_signature,
        capability_mode=sf_input.capability_mode,
        placement_safe=sf_input.placement_safe,
        geometry_materialized=sf_input.geometry_materialized,
    )

    # Phase 1: slicing-tree placement
    placed_rooms = place_rooms_slicing_tree(
        sf_input.rooms,
        envelope_width_m=sf_input.envelope_width_m,
        envelope_depth_m=sf_input.envelope_depth_m,
    )

    # Phase 3: shared-edge derivation
    shared_edges = derive_shared_edges(placed_rooms)

    # Inv 12: every HARD-adjacent pair has a doorway_feasible shared edge.
    _validate_hard_adjacencies(
        sf_input.adjacency_hints, shared_edges, sf_input.candidate_signature,
    )

    return PlacedCandidate(
        source_refined_candidate_signature=sf_input.candidate_signature,
        placed_rooms=placed_rooms,
        shared_edges=shared_edges,
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=sf_input.envelope_width_m,
        envelope_depth_m=sf_input.envelope_depth_m,
    )


def _validate_hard_adjacencies(
    hints: tuple[tuple[str, str, str], ...],
    shared_edges: tuple,
    candidate_signature: str,
) -> None:
    """Per Inv 12 + v0.2-A5: every HARD adjacency must be realized
    AND have at least one doorway_feasible shared edge.

    Raises AdjacencyConstraintViolationError if HARD pair is not
    adjacent at all. Raises DoorwayFeasibilityError if adjacent
    but no feasible doorway.
    """
    # Build a lookup: (a, b) → SharedEdge | None
    edge_lookup: dict[tuple[str, str], object] = {}
    for e in shared_edges:
        edge_lookup[(e.room_a_id, e.room_b_id)] = e

    for room_a, room_b, kind in hints:
        if kind != "hard":
            continue  # SOFT hints don't enforce at C12
        # Canonicalize the pair
        if room_a > room_b:
            room_a, room_b = room_b, room_a
        edge = edge_lookup.get((room_a, room_b))
        if edge is None:
            raise AdjacencyConstraintViolationError(
                f"Candidate {candidate_signature!r}: HARD adjacency "
                f"({room_a!r}, {room_b!r}) cannot be satisfied — "
                f"rooms are not adjacent in the placement."
            )
        if not edge.doorway_feasible:
            raise DoorwayFeasibilityError(
                f"Candidate {candidate_signature!r}: HARD adjacency "
                f"({room_a!r}, {room_b!r}) has shared edge but no "
                f"feasible doorway (overlap {edge.overlap_length_m:.3f} m "
                f"< NBC minimum {edge.min_required_clear_width_m:.3f} m)."
            )


# =============================================================================
# Multi-floor pipeline
# =============================================================================

def _place_multi_floor(
    mf_input: MultiFloorPlacementInput,
    *,
    config: PlacementConfig,
) -> MultiFloorPlacedCandidate:
    """Run Phase 0 + Phase 1 (per floor) + Phase 1b + Phase 2 + Phase 3."""
    # Phase 0 + Phase 1 per floor
    per_floor: list[tuple[str, PlacedCandidate]] = []
    for floor_label, sf_input in mf_input.floors:
        pc = _place_single_floor(sf_input, config=config)
        per_floor.append((floor_label, pc))
    per_floor.sort(key=lambda x: x[0])
    per_floor_tuple = tuple(per_floor)

    # Phase 2: VAV + MFRA convergence
    return absorb_multi_floor_placements(
        source_multifloor_signature=mf_input.source_signature,
        per_floor_placements=per_floor_tuple,
        feature_room_ids_by_floor=mf_input.feature_room_ids_by_floor,
        vertical_cores_reserved=mf_input.vertical_cores,
        tolerance_m=config.vertical_alignment_tolerance_m,
        max_realign_iterations=config.multi_floor_max_realign_iterations,
        strict_mode=config.strict_mode,
    )


# =============================================================================
# Top-level entry point
# =============================================================================

def place_and_align(
    *,
    single_floor_inputs: tuple[SingleFloorPlacementInput, ...] = (),
    multi_floor_inputs: tuple[MultiFloorPlacementInput, ...] = (),
    config: PlacementConfig,
    c11b_env_fingerprint_hash: str,
) -> PlacementBatchResult:
    """The C12 public entry point per § 5.

    Args:
      single_floor_inputs: tuple of SingleFloorPlacementInput
        (typically one per RefinedCandidate from C11b).
      multi_floor_inputs: tuple of MultiFloorPlacementInput
        (typically one per MultiFloorRefinedCandidate from C11b).
      config: PlacementConfig (mode, tolerance, budgets).
      c11b_env_fingerprint_hash: upstream C11b env fingerprint hash.

    Returns: PlacementBatchResult (successes + failures).

    Raises:
      LocalPlacementError subclasses (UpstreamSchemaDriftError,
      C12ConfigurationError) ALWAYS halt the batch regardless of mode.

      PerCandidatePlacementError subclasses halt under STRICT mode;
      under WARN they're collected into PlacementBatchResult.failures.
    """
    result, _ = _execute_batch(
        single_floor_inputs=single_floor_inputs,
        multi_floor_inputs=multi_floor_inputs,
        config=config,
        c11b_env_fingerprint_hash=c11b_env_fingerprint_hash,
        collect_provenance=False,
    )
    return result


def place_and_align_with_provenance(
    *,
    single_floor_inputs: tuple[SingleFloorPlacementInput, ...] = (),
    multi_floor_inputs: tuple[MultiFloorPlacementInput, ...] = (),
    config: PlacementConfig,
    c11b_env_fingerprint_hash: str,
) -> tuple[PlacementBatchResult, PlacementProvenance]:
    """Production-observability entry point per B-C12-PROVENANCE-SPLIT
    backlog precursor.

    Identical functional contract to place_and_align(), plus returns
    a PlacementProvenance with run metadata (timing, per-candidate
    outcomes, env fingerprint).

    Telemetry events also emit via config.telemetry_sink if configured.
    """
    return _execute_batch(
        single_floor_inputs=single_floor_inputs,
        multi_floor_inputs=multi_floor_inputs,
        config=config,
        c11b_env_fingerprint_hash=c11b_env_fingerprint_hash,
        collect_provenance=True,
    )


def _execute_batch(
    *,
    single_floor_inputs: tuple[SingleFloorPlacementInput, ...],
    multi_floor_inputs: tuple[MultiFloorPlacementInput, ...],
    config: PlacementConfig,
    c11b_env_fingerprint_hash: str,
    collect_provenance: bool,
) -> tuple[PlacementBatchResult, PlacementProvenance]:
    """Core batch execution shared by both entry points.

    When collect_provenance=False, returns a stub provenance to keep
    the type signature uniform; callers ignore it. Telemetry sink
    receives events regardless of collect_provenance flag.
    """
    sink = _resolve_sink(config)
    batch_start = time.perf_counter()

    # Phase 0 step 4: schema version probes (always runs)
    assert_upstream_schema_versions()

    # Capture C12 env fingerprint + cache key
    env_fp = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash=c11b_env_fingerprint_hash,
        config=config,
    )
    cache_key = compute_c12_cache_key(env_fp)

    successes_sf: list[PlacedCandidate] = []
    successes_mf: list[MultiFloorPlacedCandidate] = []
    failures: list[FailureRecord] = []
    candidate_entries: list[CandidateProvenanceEntry] = []

    # Single-floor candidates
    for sf_input in single_floor_inputs:
        cand_start = time.perf_counter()
        outcome = "success"
        failure_record: FailureRecord | None = None
        try:
            pc = _place_single_floor(sf_input, config=config)
            successes_sf.append(pc)
            # Telemetry: adjacency coverage
            hard_t, hard_s, soft_t, soft_s = _count_adjacency_satisfaction(
                sf_input.adjacency_hints, pc.shared_edges,
            )
            sink.record_adjacency_coverage(AdjacencyCoverageEvent(
                candidate_signature=sf_input.candidate_signature,
                hard_hints_total=hard_t,
                hard_hints_satisfied=hard_s,
                soft_hints_total=soft_t,
                soft_hints_satisfied=soft_s,
            ))
        except PerCandidatePlacementError as exc:
            outcome = "failure"
            failure_record = _failure_from_exc(
                sf_input.candidate_signature, exc, phase="phase1",
            )
            failures.append(failure_record)
            if config.strict_mode:
                # Emit performance event even on raise (telemetry first)
                cand_wall = time.perf_counter() - cand_start
                sink.record_performance(PerformanceEvent(
                    candidate_signature=sf_input.candidate_signature,
                    n_rooms=len(sf_input.rooms),
                    wallclock_seconds=cand_wall,
                    phase="single_floor",
                ))
                raise
        cand_wall = time.perf_counter() - cand_start
        sink.record_performance(PerformanceEvent(
            candidate_signature=sf_input.candidate_signature,
            n_rooms=len(sf_input.rooms),
            wallclock_seconds=cand_wall,
            phase="single_floor",
        ))
        if collect_provenance:
            candidate_entries.append(CandidateProvenanceEntry(
                candidate_signature=sf_input.candidate_signature,
                outcome=outcome,
                wallclock_seconds=cand_wall,
                phase_reached="phase3" if outcome == "success" else "phase1",
                n_rooms=len(sf_input.rooms),
                failure_record=failure_record,
            ))

    # Multi-floor candidates
    for mf_input in multi_floor_inputs:
        cand_start = time.perf_counter()
        outcome = "success"
        failure_record = None
        n_rooms_total = sum(len(f.rooms) for _, f in mf_input.floors)
        try:
            mfc = _place_multi_floor(mf_input, config=config)
            successes_mf.append(mfc)
            # Telemetry: MFRA convergence
            abort_reason: str = "converged"
            if not mfc.alignment_report.converged:
                if mfc.alignment_report.retries_used >= config.multi_floor_max_realign_iterations:
                    abort_reason = "retry_budget_exhausted"
                else:
                    abort_reason = "divergence"
            sink.record_mfra_convergence(MfraConvergenceEvent(
                source_multifloor_signature=mf_input.source_signature,
                n_floors=len(mf_input.floors),
                converged=mfc.alignment_report.converged,
                retries_used=mfc.alignment_report.retries_used,
                delta_progression=mfc.alignment_report.delta_progression,
                final_max_misalignment_m=mfc.alignment_report.final_max_misalignment_m,
                abort_reason=abort_reason,  # type: ignore[arg-type]
            ))
        except PerCandidatePlacementError as exc:
            outcome = "failure"
            failure_record = _failure_from_exc(
                mf_input.source_signature, exc, phase="phase2",
            )
            failures.append(failure_record)
            if config.strict_mode:
                cand_wall = time.perf_counter() - cand_start
                sink.record_performance(PerformanceEvent(
                    candidate_signature=mf_input.source_signature,
                    n_rooms=n_rooms_total,
                    wallclock_seconds=cand_wall,
                    phase="multi_floor",
                ))
                raise
        cand_wall = time.perf_counter() - cand_start
        sink.record_performance(PerformanceEvent(
            candidate_signature=mf_input.source_signature,
            n_rooms=n_rooms_total,
            wallclock_seconds=cand_wall,
            phase="multi_floor",
        ))
        if collect_provenance:
            candidate_entries.append(CandidateProvenanceEntry(
                candidate_signature=mf_input.source_signature,
                outcome=outcome,
                wallclock_seconds=cand_wall,
                phase_reached="phase3" if outcome == "success" else "phase2",
                n_rooms=n_rooms_total,
                failure_record=failure_record,
            ))

    batch_wall = time.perf_counter() - batch_start

    result = PlacementBatchResult(
        placed_candidates=tuple(successes_sf),
        multifloor_placed_candidates=tuple(successes_mf),
        failures=tuple(failures),
        c12_version=C12_VERSION,
        cache_key=cache_key,
    )

    provenance = PlacementProvenance(
        c12_version=C12_VERSION,
        env_fingerprint=env_fp,
        cache_key=cache_key,
        total_wallclock_seconds=batch_wall,
        candidates=tuple(candidate_entries),
        failures=tuple(failures),
    )

    return (result, provenance)


def _failure_from_exc(
    sig: str, exc: PerCandidatePlacementError, *, phase: str,
) -> FailureRecord:
    return FailureRecord(
        candidate_signature=sig,
        error_type=type(exc).__name__,
        error_message=str(exc),
        phase=phase,  # type: ignore[arg-type]
    )


__all__ = [
    "SingleFloorPlacementInput",
    "MultiFloorPlacementInput",
    "place_and_align",
    "place_and_align_with_provenance",
]
