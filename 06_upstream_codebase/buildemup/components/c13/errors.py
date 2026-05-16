"""
BuildemUp — Component 13 — error / failure hierarchy
=====================================================

Per C13 SPEC v1.0 LOCKED (composed from v0.1 § 5 base + v0.4 C2
NBC-grounded vetoes + v0.5 D2 CONDITIONAL_LEGALITY + v0.5 D6
primary-reachability + v0.4 § 0.0 TL;DR taxonomy).

The hierarchy distinguishes:
- LocalPlacementError: orchestrator-level errors that ALWAYS halt
  (schema drift, configuration invalid).
- PerCandidatePlacementError: per-candidate failures (placement failed
  for this candidate; other candidates may succeed).

STRICT vs WARN mode behavior:
- Under STRICT: PerCandidatePlacementError raises immediately,
  halting the batch.
- Under WARN: PerCandidatePlacementError is caught by the orchestrator,
  recorded in DoorPlacementBatchResult.failed (FailedDoorPlacement
  typestate variant per v0.3 B11), and the candidate is skipped;
  the batch continues.

LocalPlacementError always raises regardless of mode.

C13 uses a typestate-discriminated result schema (per v0.3 B11) rather
than C12's mixed-result pattern. Downstream consumers MUST pattern-match
on SuccessfulDoorPlacement vs FailedDoorPlacement — mypy rejects access
to .doors on a FailedDoorPlacement.
"""
from __future__ import annotations


# =============================================================================
# Base classes
# =============================================================================

class DoorPlacementError(Exception):
    """Base of all C13 errors."""


class LocalPlacementError(DoorPlacementError):
    """Orchestrator-level errors that halt the batch.

    These represent issues with the configuration, the upstream
    contract, or the C13 runtime itself — not with individual
    candidates. ALWAYS raised regardless of strict_mode.
    """


class PerCandidatePlacementError(DoorPlacementError):
    """Per-candidate door-placement failures.

    Under STRICT mode: raised immediately, halting the batch.
    Under WARN mode: caught by the orchestrator, recorded into
    DoorPlacementBatchResult.failed (typestate FailedDoorPlacement),
    and the candidate is skipped.

    Per v0.3 B11: WARN-mode failures CANNOT be misused as successful
    results because the typestate discrimination is enforced at the
    schema level.
    """


# =============================================================================
# Local (orchestrator-level) errors — ALWAYS halt
# =============================================================================

class UpstreamSchemaDriftError(LocalPlacementError):
    """Per v0.1 § 1.3 + v0.4 C3 protocol-version probe.

    Raised when an upstream component's schema version constant does
    not match what C13 was built against. Examples:
    - C12_VERSION != EXPECTED_C12_VERSION
    - CORRIDOR_ZONE_SCHEMA_VERSION (C8) != EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION
    - ADJACENCY_HINT_SCHEMA_VERSION (C9) != EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION

    Severity: systemic. Halts the batch immediately under any mode.
    Prevents silent cross-component contract drift.
    """


class C13ConfigurationError(LocalPlacementError):
    """Per v0.1 § 5. DoorPlacementConfig is malformed (negative
    corner_offset, max_doors_per_room exceeding MAX_DOORS_PER_ROOM_V1,
    inconsistent secondary-door config, etc.).

    Validated at orchestrator entry; never surfaces mid-pipeline.
    """


# =============================================================================
# Per-candidate errors — STRICT raises, WARN collects
# =============================================================================

class EntryRoomNotFoundError(PerCandidatePlacementError):
    """Per v0.1 § 5. The DoorPlacementInput.entry_room_id does not
    match any PlacedRoom.room_id in the input candidate.

    Indicates caller error (entry room misidentified) or upstream
    contract violation (entry room removed by C12 placement)."""


class DoorPositionInfeasibleError(PerCandidatePlacementError):
    """Per v0.1 § 3.3 step 3. No conflict-free position exists on the
    selected SharedEdge for a required door, even after applying the
    corner-offset default (v0.2 A2) and grid snap (v0.2 A7).

    Distinct from SwingArcConflictError: this fires when the edge is
    too short to accommodate the door at any position, BEFORE Phase D
    conflict resolution begins."""


class SwingArcConflictError(PerCandidatePlacementError):
    """Per v0.1 § 3.4 + v0.2 A4 + v0.3 B3 + v0.4 C5. Phase D bounded
    CSP-lite conflict resolution exhausted its iteration budget OR
    detected a visited-state loop without resolving all swing-arc
    conflicts.

    Carries telemetry (PhaseDConvergenceEvent) for post-mortem
    convergence analysis (per v0.4 C5)."""


class PostResolutionUnreachabilityError(PerCandidatePlacementError):
    """Per v0.2 A9 (Inv D13). Phase F detected that the door-induced
    reachability graph (all primary + secondary doors) leaves one or
    more PlacedRooms unreachable from the main_entry.

    Indicates a candidate whose geometry was reachable via shared
    edges (C12 Phase 0b confirmed) but whose door selection failed
    to preserve reachability. May surface from over-eager corridor
    suppression in Phase A or aggressive width reductions in Phase D."""


class HabitablePrimaryUnreachabilityError(PerCandidatePlacementError):
    """Per v0.5 D6 (Inv D17). Phase F detected that one or more
    habitable rooms (bedroom, master_bedroom, guest_bedroom, living,
    dining, kitchen, pooja, study) are reachable from main_entry ONLY
    via secondary doors — i.e., not via the PRIMARY-door-induced graph.

    Distinct from PostResolutionUnreachabilityError: this fires when
    the room IS reachable in the full graph (D13 passes) but only via
    service-circulation routing, which is architecturally pathological
    for habitable spaces."""


class NbcBathroomKitchenAdjacencyError(PerCandidatePlacementError):
    """Per v0.4 C2 (Inv D11.1). A door directly connects a
    water-closet/bathroom room to a kitchen.

    NBC 2016 Part 3 (verified S44 web search 2026-05-13):
    "No room containing water-closets shall be used for any purpose
    except as a lavatory and no such room shall open directly into
    any kitchen or cooking space by a door, window or other opening."

    This is a HARD_LEGALITY veto, not advisory. Surfaces at Phase A
    door-selection time (single-edge check, evaluation-order-independent)."""


class NbcThroughBathroomRoutingError(PerCandidatePlacementError):
    """Per v0.4 C2 (Inv D11.2). A primary circulation path routes
    THROUGH a bathroom (bathroom is not terminal).

    NBC 2016 Part 3 (verified S44): "Every room containing water-closet
    shall have a door completely closing the entrance to it" — bathroom
    is a terminal node in the circulation graph; routing through one
    violates NBC.

    HARD_LEGALITY veto. Surfaces at Phase F when the door-induced
    primary-circulation graph is materialized."""


class NbcMasterBedroomAdjacencyError(PerCandidatePlacementError):
    """Per v0.4 C2 (Inv D11.4). A master bedroom's main door opens
    directly to a kitchen or bathroom.

    NBC 2016 Part 3 (verified S44): kitchen-into-bedroom adjacency is
    restricted; master bedroom is the principal sleeping space and
    requires acoustic + privacy separation from wet zones.

    HARD_LEGALITY veto. Surfaces at Phase A door-selection time."""


class ConditionalLegalityViolationError(PerCandidatePlacementError):
    """Per v0.5 D2 (Inv D11.3' narrowed) + v0.6 E1 (CONDITIONAL_LEGALITY
    classification) + v0.6 E1 (Inv D19 provenance).

    Raised when a primary circulation path routes THROUGH a kitchen for
    accessing a non-kitchen-adjacent room AND an alternate non-kitchen
    route of equal or shorter length exists in the door-induced graph.

    Per v0.5 D2 narrowing: blanket prohibition over open-plan compact
    layouts is over-broad; the violation fires only when forced
    kitchen-transit is AVOIDABLE per the door graph.

    Carries ConditionalLegalityViolation provenance (per v0.6 E1):
    invariant_id, violated_path, alternative_path,
    alternative_path_length_grid_units.

    CONDITIONAL_LEGALITY category — evaluated at Phase F (post-Phase-D
    conflict resolution, post-secondary-door placement) per v0.6 E1
    "evaluated once and only once per candidate."
    """


# =============================================================================
# Public exports
# =============================================================================

__all__ = [
    # Bases
    "DoorPlacementError",
    "LocalPlacementError",
    "PerCandidatePlacementError",
    # Local (always halt)
    "UpstreamSchemaDriftError",
    "C13ConfigurationError",
    # Per-candidate
    "EntryRoomNotFoundError",
    "DoorPositionInfeasibleError",
    "SwingArcConflictError",
    "PostResolutionUnreachabilityError",
    "HabitablePrimaryUnreachabilityError",
    "NbcBathroomKitchenAdjacencyError",
    "NbcThroughBathroomRoutingError",
    "NbcMasterBedroomAdjacencyError",
    "ConditionalLegalityViolationError",
]
