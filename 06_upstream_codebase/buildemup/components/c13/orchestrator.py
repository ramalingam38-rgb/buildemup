"""
BuildemUp — Component 13 — orchestrator
========================================

Per C13 SPEC v1.0 LOCKED:
- v0.1 § 11 (place_doors() public API)
- v0.3 B11 (typestate API: SuccessfulDoorPlacement vs FailedDoorPlacement)
- v0.4 C7 (pipeline conventions — mirror C12 entry-point shape)
- v0.7 F1 (Phase F pure verification — orchestrator handles result
  packaging, NOT Phase F)

place_doors() wires:
  Phase A (edge_selection.select_edges)
   → Phase B (swing_assignment.assign_swings)
   → Phase C (position_selection.assign_positions)
   → Phase D (conflict_resolution.resolve_conflicts)
   → Phase E (assembly.assemble_doors)
   → Phase F (verification.verify)
   → SuccessfulDoorPlacement OR FailedDoorPlacement
   → DoorPlacementBatchResult

Per v0.4 C5 mandatory telemetry day-1: PhaseDConvergenceEvent is
emitted via the configured telemetry_sink (default NullTelemetrySink
when DoorPlacementConfig.telemetry_sink is None).

Per v0.4 C9 secondary-door graph semantics: primary doors selected
first (Phase A), then verified for connectivity (Phase F D17 +
D11.3'). Secondary doors complete the full graph (Phase F D13).

Per v0.3 B11 typestate: every PlacedCandidate produces EITHER a
SuccessfulDoorPlacement OR a FailedDoorPlacement — never both, never
mixed.

STRICT vs WARN dispatch (per v0.1 § 5):
- LocalPlacementError (UpstreamSchemaDriftError, C13ConfigurationError):
  ALWAYS halts the batch, regardless of strict_mode.
- PerCandidatePlacementError (DoorPositionInfeasibleError,
  SwingArcConflictError, PostResolutionUnreachabilityError,
  HabitablePrimaryUnreachabilityError, NbcBathroomKitchenAdjacencyError,
  NbcThroughBathroomRoutingError, NbcMasterBedroomAdjacencyError,
  ConditionalLegalityViolationError, EntryRoomNotFoundError):
    - STRICT → raise immediately (halts batch).
    - WARN → caught, packaged into FailedDoorPlacement, batch continues.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .assembly import assemble_doors
from .cache_keys import build_c13_cache_keys
from .conflict_resolution import resolve_conflicts
from .config import DoorPlacementConfig
from .contracts import C12V10EdgeAdapter, C13ConsumesFromC12Edge
from .edge_selection import select_edges
from .errors import (
    C13ConfigurationError,
    ConditionalLegalityViolationError,
    DoorPlacementError,
    EntryRoomNotFoundError,
    LocalPlacementError,
    NbcThroughBathroomRoutingError,
    PerCandidatePlacementError,
    UpstreamSchemaDriftError,
)
from .position_selection import assign_positions
from .schema import (
    AdvisoryFlag,
    ConditionalLegalityViolation,
    Door,
    DoorPlacementBatchResult,
    FailedDoorPlacement,
    FailureRecord,
    GeometricFidelity,
    RoomDoorPreference,
    SuccessfulDoorPlacement,
)
from .swing_assignment import assign_swings
from .telemetry import C13TelemetrySink, NullTelemetrySink
from .verification import verify
from .versioning import (
    ADVISORY_SCHEMA_VERSION,
    C13_EDGE_PROTOCOL_VERSION,
    C13_VERSION,
    DEFAULT_LEAF_THICKNESS_M,
)


# Entry-room keywords (must mirror C12 input_resolution.py's
# entrance_keywords). Centralized here so C13's entry-room
# resolution is auditable.
_ENTRY_ROOM_KEYWORDS = frozenset({
    "main_entrance", "entrance", "entry", "foyer",
})


# =============================================================================
# Entry-room resolution
# =============================================================================

def _resolve_entry_room_id(
    placed_rooms_tuple: tuple,
) -> str:
    """Identify the main entry room from a candidate's placed rooms.

    A candidate has exactly one entry room: the room whose category
    matches an entry keyword. If zero or multiple match, raise
    EntryRoomNotFoundError.

    Args:
      placed_rooms_tuple: tuple of objects with .room_id and .category
          attributes (duck-typed against C12 PlacedRoom).

    Raises:
      EntryRoomNotFoundError: zero or ≥2 entry rooms found.
    """
    entry_candidates = [
        r.room_id for r in placed_rooms_tuple
        if r.category.lower() in _ENTRY_ROOM_KEYWORDS
    ]
    if len(entry_candidates) == 0:
        raise EntryRoomNotFoundError(
            f"No entry room found in placed_rooms. Expected exactly "
            f"one room with category in {sorted(_ENTRY_ROOM_KEYWORDS)}."
        )
    if len(entry_candidates) > 1:
        raise EntryRoomNotFoundError(
            f"Multiple entry rooms found ({sorted(entry_candidates)}); "
            f"expected exactly one with category in "
            f"{sorted(_ENTRY_ROOM_KEYWORDS)}."
        )
    return entry_candidates[0]


# =============================================================================
# Per-candidate pipeline
# =============================================================================

@dataclass(frozen=True)
class _CandidateContext:
    """Internal: derived per-candidate inputs after ingress
    normalization. Not part of the public API."""
    candidate_signature: str
    placed_room_ids: tuple[str, ...]
    room_categories: dict[str, str]
    room_areas: dict[str, float]
    shared_edges: tuple[C13ConsumesFromC12Edge, ...]
    entry_room_id: str


def _ingest_candidate(placed_candidate) -> _CandidateContext:
    """Normalize one PlacedCandidate into the inputs C13 phases need.

    Per v0.4 C7 pipeline conventions: ingestion is a separate phase
    from the algorithmic phases A-F (canonical: phase0 ingress).
    Failures here are LocalPlacementError (UpstreamSchemaDriftError /
    C13ConfigurationError) — they halt the batch regardless of mode.

    Args:
      placed_candidate: a C12 PlacedCandidate (duck-typed; only
          .source_refined_candidate_signature, .placed_rooms,
          .shared_edges are read).

    Raises:
      UpstreamSchemaDriftError: candidate missing required fields.
    """
    try:
        sig = placed_candidate.source_refined_candidate_signature
        placed_rooms = placed_candidate.placed_rooms
        shared_edges = placed_candidate.shared_edges
    except AttributeError as e:
        raise UpstreamSchemaDriftError(
            f"PlacedCandidate missing required attribute: {e}"
        ) from e

    entry_room_id = _resolve_entry_room_id(placed_rooms)

    # Room areas: width × depth from C12 PlacedRoom.
    room_areas: dict[str, float] = {}
    room_categories: dict[str, str] = {}
    placed_room_ids: list[str] = []
    for r in placed_rooms:
        room_areas[r.room_id] = r.width_m * r.depth_m
        room_categories[r.room_id] = r.category
        placed_room_ids.append(r.room_id)
    placed_room_ids.sort()

    # Wrap each C12 SharedEdge in the Protocol-conforming adapter.
    adapted_edges = tuple(
        C12V10EdgeAdapter(e) for e in shared_edges
    )

    return _CandidateContext(
        candidate_signature=sig,
        placed_room_ids=tuple(placed_room_ids),
        room_categories=room_categories,
        room_areas=room_areas,
        shared_edges=adapted_edges,
        entry_room_id=entry_room_id,
    )


def _classify_error_phase(error: Exception) -> str:
    """Map a per-candidate error class to its originating phase.

    Used to populate FailureRecord.phase (typed as C13Phase Literal).

    Some error classes (notably DoorPositionInfeasibleError) are
    raised from BOTH Phase A (no feasible edge for a room) and
    Phase C (clear_width > overlap_length on a chosen edge). The
    classifier disambiguates via the error message prefix, which
    edge_selection.py and position_selection.py both populate with
    "Phase A:" / "Phase C:" tags by convention.
    """
    err_type = type(error).__name__
    err_msg = str(error)
    # Phase A errors.
    if err_type in (
        "EntryRoomNotFoundError",
    ):
        return "phaseA"
    # Phase A also surfaces NBC bathroom/kitchen edge vetoes when
    # they leave a room with no feasible edge, but those manifest
    # as DoorPositionInfeasibleError. The dedicated NBC* errors are
    # reserved for explicit single-edge veto raise paths (not used
    # in the v1 implementation — Phase A FILTERS rather than raises).
    if err_type in (
        "NbcBathroomKitchenAdjacencyError",
        "NbcMasterBedroomAdjacencyError",
    ):
        return "phaseA"
    if err_type == "DoorPositionInfeasibleError":
        # Could come from Phase A (no feasible edge for a room) or
        # Phase C (clear_width > overlap). Disambiguate via the
        # message prefix tag set by each phase's raise sites.
        if err_msg.startswith("Phase A:"):
            return "phaseA"
        if err_msg.startswith("Phase C:"):
            return "phaseC"
        # Default: Phase C (the historically more common origin).
        return "phaseC"
    # Phase D errors.
    if err_type == "SwingArcConflictError":
        return "phaseD"
    # Phase F errors.
    if err_type in (
        "PostResolutionUnreachabilityError",
        "HabitablePrimaryUnreachabilityError",
        "NbcThroughBathroomRoutingError",
        "ConditionalLegalityViolationError",
    ):
        return "phaseF"
    return "phase0"  # fallback


def _build_failure_record(
    candidate_signature: str,
    error: Exception,
    *,
    d11_3_provenance: Optional[ConditionalLegalityViolation] = None,
) -> FailureRecord:
    """Construct a FailureRecord, enforcing Inv D19 for CONDITIONAL_LEGALITY.

    Args:
      candidate_signature: provenance.
      error: the caught PerCandidatePlacementError.
      d11_3_provenance: required when error is
          ConditionalLegalityViolationError (Inv D19); else None.
    """
    err_type = type(error).__name__
    # Inv D19 — CONDITIONAL_LEGALITY requires provenance.
    if err_type == "ConditionalLegalityViolationError":
        if d11_3_provenance is None:
            raise ValueError(
                "Internal error: ConditionalLegalityViolationError "
                "requires d11_3_provenance per Inv D19; got None."
            )
        return FailureRecord(
            candidate_signature=candidate_signature,
            error_type=err_type,
            error_message=str(error),
            phase=_classify_error_phase(error),
            conditional_legality_violation=d11_3_provenance,
        )
    return FailureRecord(
        candidate_signature=candidate_signature,
        error_type=err_type,
        error_message=str(error),
        phase=_classify_error_phase(error),
        conditional_legality_violation=None,
    )


def _place_one(
    placed_candidate,
    config: DoorPlacementConfig,
    cache_keys,
    telemetry_sink: C13TelemetrySink,
) -> SuccessfulDoorPlacement | FailedDoorPlacement:
    """Run the A→F pipeline on one PlacedCandidate.

    Returns either SuccessfulDoorPlacement (clean run, no violations)
    or FailedDoorPlacement (per-candidate error caught in WARN mode).

    In strict_mode this still raises on per-candidate errors; the
    caller (place_doors) decides whether to convert.
    """
    ctx = _ingest_candidate(placed_candidate)

    # ── Phase A ────────────────────────────────────────────────────
    edge_result = select_edges(
        candidate_signature=ctx.candidate_signature,
        placed_room_ids=ctx.placed_room_ids,
        room_categories=ctx.room_categories,
        shared_edges=ctx.shared_edges,
        entry_room_id=ctx.entry_room_id,
        room_door_preferences={},  # v1: caller-side via separate API
        telemetry_sink=telemetry_sink,
    )

    # ── Phase B ────────────────────────────────────────────────────
    swing_result = assign_swings(
        candidate_signature=ctx.candidate_signature,
        edge_result=edge_result,
        room_categories=ctx.room_categories,
        room_areas=ctx.room_areas,
        bathroom_outswing_area_threshold_m2=(
            config.bathroom_outswing_area_threshold_m2
        ),
        telemetry_sink=telemetry_sink,
    )

    # ── Phase C ────────────────────────────────────────────────────
    # default_clear_width_m=0.0 means "use edge NBC minimum"; lift
    # that to the edge's min_required_clear_width_m at v1 by using
    # a small positive value. The Phase C entry point requires
    # positive clear_width to validate Inv D10, so use the larger of
    # config + 0.75m NBC bathroom floor.
    effective_clear_width = max(config.default_clear_width_m, 0.75)
    position_result = assign_positions(
        edge_result=edge_result,
        default_clear_width_m=effective_clear_width,
        corner_offset_m=config.corner_offset_m,
        grid_snap_m=config.grid_snap_m,
    )

    # ── Phase D ────────────────────────────────────────────────────
    conflict_result = resolve_conflicts(
        candidate_signature=ctx.candidate_signature,
        edge_result=edge_result,
        swing_result=swing_result,
        position_result=position_result,
        max_conflict_resolution_iterations=(
            config.max_conflict_resolution_iterations
        ),
        grid_snap_m=config.grid_snap_m,
        strict_mode=config.strict_mode,
        telemetry_sink=telemetry_sink,
        main_entry_room_id=edge_result.main_entry_room_id,
    )

    # ── Phase E ────────────────────────────────────────────────────
    doors = assemble_doors(
        conflict_result=conflict_result,
        edge_result=edge_result,
        leaf_thickness_m=DEFAULT_LEAF_THICKNESS_M,
        geometric_fidelity=GeometricFidelity.APPROXIMATE,
    )

    # ── Phase F ────────────────────────────────────────────────────
    primary_door_ids = frozenset(
        (a.edge.room_a_id, a.edge.room_b_id)
        for a in edge_result.assignments
        if not a.is_secondary
    )
    report = verify(
        doors=doors,
        placed_room_ids=ctx.placed_room_ids,
        room_categories=ctx.room_categories,
        main_entry_room_id=edge_result.main_entry_room_id,
        primary_door_ids=primary_door_ids,
        strict_mode=config.strict_mode,
    )

    # In WARN mode, a non-clean report still produces a Failed result
    # (orchestrator preserves the partial doors for debug). In STRICT
    # mode, verify() would have raised already.
    if not report.is_clean and not config.strict_mode:
        # Pick the most severe violation for the FailureRecord.
        # Severity order: D13 > D17 > D11.3'.
        if report.d13_violations:
            from .errors import PostResolutionUnreachabilityError
            err = PostResolutionUnreachabilityError(
                f"WARN: {len(report.d13_violations)} room(s) "
                f"unreachable: {list(report.d13_violations)}."
            )
            return FailedDoorPlacement(
                source_placed_candidate_signature=ctx.candidate_signature,
                failure_record=_build_failure_record(
                    ctx.candidate_signature, err,
                ),
                partial_doors=doors,
                partial_advisory_flags=swing_result.advisory_flags,
            )
        if report.d17_violations:
            from .errors import HabitablePrimaryUnreachabilityError
            err = HabitablePrimaryUnreachabilityError(
                f"WARN: {len(report.d17_violations)} habitable room(s) "
                f"only reachable via secondary doors: "
                f"{list(report.d17_violations)}."
            )
            return FailedDoorPlacement(
                source_placed_candidate_signature=ctx.candidate_signature,
                failure_record=_build_failure_record(
                    ctx.candidate_signature, err,
                ),
                partial_doors=doors,
                partial_advisory_flags=swing_result.advisory_flags,
            )
        # D11.3' violation: build ConditionalLegalityViolationError
        # with provenance per Inv D19.
        first = report.d11_3_violations[0]
        err = ConditionalLegalityViolationError(
            f"WARN: Inv D11.3' — primary path "
            f"{list(first.violated_path)} traverses a kitchen when "
            f"alternate path {list(first.alternative_path)} exists."
        )
        return FailedDoorPlacement(
            source_placed_candidate_signature=ctx.candidate_signature,
            failure_record=_build_failure_record(
                ctx.candidate_signature, err,
                d11_3_provenance=first,
            ),
            partial_doors=doors,
            partial_advisory_flags=swing_result.advisory_flags,
        )

    # Success path — package SuccessfulDoorPlacement.
    return SuccessfulDoorPlacement(
        source_placed_candidate_signature=ctx.candidate_signature,
        doors=doors,
        advisory_flags=swing_result.advisory_flags,
        geometric_fidelity=GeometricFidelity.APPROXIMATE,
        cache_keys=cache_keys,
    )


# =============================================================================
# place_doors() public API
# =============================================================================

def place_doors(
    *,
    placed_candidates: Iterable,
    config: DoorPlacementConfig,
    c12_cache_key: str,
) -> DoorPlacementBatchResult:
    """Top-level C13 entry point.

    For each PlacedCandidate, runs Phases A→F and packages the result.

    Per v0.1 § 11 + v0.3 B11 typestate API.

    Args:
      placed_candidates: iterable of C12 PlacedCandidate (or any
          object with .source_refined_candidate_signature,
          .placed_rooms, .shared_edges).
      config: DoorPlacementConfig governing strict_mode + Phase A-D
          defaults + telemetry sink.
      c12_cache_key: PlacementBatchResult.cache_key from C12.

    Returns:
      DoorPlacementBatchResult with successful + failed tuples sorted
      lex-ASC by source_placed_candidate_signature.

    Raises:
      UpstreamSchemaDriftError: a PlacedCandidate is malformed.
      C13ConfigurationError: config invariants violated (should be
          caught at DoorPlacementConfig construction, not here).
      Per-candidate errors: only in strict_mode=True. In WARN mode,
          per-candidate failures are caught and packaged into
          FailedDoorPlacement.
    """
    # Resolve telemetry sink.
    raw_sink = config.telemetry_sink
    if raw_sink is None:
        telemetry_sink: C13TelemetrySink = NullTelemetrySink()
    else:
        telemetry_sink = raw_sink  # type: ignore[assignment]

    # Build cache keys once for the batch.
    cache_keys = build_c13_cache_keys(
        config=config,
        upstream_c12_cache_key=c12_cache_key,
    )

    successes: list[SuccessfulDoorPlacement] = []
    failures: list[FailedDoorPlacement] = []

    for placed_candidate in placed_candidates:
        try:
            result = _place_one(
                placed_candidate, config, cache_keys, telemetry_sink,
            )
            if isinstance(result, SuccessfulDoorPlacement):
                successes.append(result)
            else:
                failures.append(result)
        except LocalPlacementError:
            # Always halt regardless of strict_mode.
            raise
        except PerCandidatePlacementError as e:
            if config.strict_mode:
                raise
            # WARN mode: package as FailedDoorPlacement and continue.
            # We need a candidate_signature to record. If ingest failed
            # before that's known, fall back to a stable string.
            sig = getattr(
                placed_candidate, "source_refined_candidate_signature",
                "unknown_candidate",
            )
            failures.append(FailedDoorPlacement(
                source_placed_candidate_signature=sig,
                failure_record=_build_failure_record(sig, e),
                partial_doors=(),
                partial_advisory_flags=(),
            ))

    # Canonical sort: lex-ASC by source signature.
    successes.sort(key=lambda s: s.source_placed_candidate_signature)
    failures.sort(key=lambda f: f.source_placed_candidate_signature)

    return DoorPlacementBatchResult(
        successful=tuple(successes),
        failed=tuple(failures),
        c13_version=C13_VERSION,
        c13_edge_protocol_version=C13_EDGE_PROTOCOL_VERSION,
        advisory_schema_version=ADVISORY_SCHEMA_VERSION,
        cache_key=cache_keys.full_cache_key,
    )


__all__ = [
    "place_doors",
]
