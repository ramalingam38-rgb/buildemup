"""
BuildemUp — Component 13 — Door Placement Engine
=================================================

Per C13 SPEC v1.0 LOCKED at S44 by Ramalingam directive
("Lock it and give me the handoff", path c).

This package implements C13 in the canonical Track 3 numbering. It
consumes PlacedCandidate / MultiFloorPlacedCandidate from C12 plus
the C8 corridor_zones derived view + C9 adjacency_hints field on
FloorRoomBrief, and emits DoorPlacementBatchResult consumed downstream
by C14 (Unified Evaluation — currently unimplemented; C13 architecture
designs against C14's expected contract surface).

v1 SCOPE BOUNDARY (per v0.3 § 0.5 explicit C13/C14 boundary):
  GUARANTEES:
    - Every PlacedRoom has min_doors ≤ doors ≤ max_doors (Inv D1')
    - Every door sits on a doorway_feasible SharedEdge (Inv D2)
    - No swing-arc conflicts (Inv D5)
    - All rooms reachable from main_entry via door-induced graph (Inv D13)
    - Habitable rooms reachable via PRIMARY-door graph (Inv D17)
    - NBC 2016 HARD_LEGALITY vetoes enforced (Inv D11.1, D11.2, D11.4)
    - CONDITIONAL_LEGALITY (D11.3' through-kitchen) evaluated at Phase F
    - Byte-equal replay across runs (Inv D7) via canonical ordering +
      grid snap + total-order tie-break
    - Cache-domain split (geometry/advisory/full per Inv D18 prefix rule)
    - Typestate API: SuccessfulDoorPlacement vs FailedDoorPlacement
      enforces downstream filtering
    - Forward-compat reserved field: AdvisoryFlag.causal_context (v1.0
      always None per Inv D20; v1.x populators per v0.7 F2 semantic
      intent)
  DOES NOT GUARANTEE:
    - Circulation quality scoring (→ C14)
    - Sight-line optimization (→ C14)
    - Privacy gradient (→ C14)
    - Cost / aesthetic tradeoffs (→ C14)
    - Globally optimal door positioning (Phase D is bounded CSP-lite,
      not global optimization)
    - n > 15 rooms convergence (filed under
      B-C13-LARGE-N-CSP-CONVERGENCE for v2+)

S45+ BUILD STATUS (Sub-Session 1 — foundational + support layer):
  Currently shipped:
    - versioning (C13_VERSION, expected upstream schema versions,
      protocol + advisory schema versions, geometric defaults)
    - errors (12 failure types per § 5 + § 0.0 TL;DR taxonomy)
    - contracts (C13ConsumesFromC12Edge Protocol + C12V10EdgeAdapter +
      EdgeType enum)
    - schema (Door, AdvisoryFlag, CausalContext, RoomDoorPreference,
      C13CacheKeys, ConditionalLegalityViolation, FailureRecord,
      SuccessfulDoorPlacement, FailedDoorPlacement,
      DoorPlacementBatchResult + AdvisoryCategory / GeometricFidelity
      enums + category sets)
    - config (DoorPlacementConfig with v1 LOCKED defaults; cache-domain
      partitioning per v0.4 C10)
    - cache_keys (geometry / advisory / full builders; Inv D18 prefix
      construction)
  Pending build work (Sub-Sessions 2+):
    - telemetry (DoorPlacementEvent + PhaseDConvergenceEvent +
      SwingArcConflictEvent etc.; per § 9 + v0.4 C5 mandatory day-1)
    - edge_selection (Phase A: 3-tier priority per v0.3 B6)
    - swing_assignment (Phase B: bathroom-preferred-inward per v0.2 A6)
    - position_selection (Phase C: corner_offset + grid-snap per
      v0.2 A2/A7)
    - conflict_resolution (Phase D: bounded CSP-lite per v0.3 B3/B9,
      visited-state hashing + total-order tie-break)
    - assembly (Phase E: canonical output assembly + cache key
      generation)
    - verification (Phase F: PURE per Inv D22 — D11.3'/D13/D17/D19
      checks only; no mutation)
    - orchestrator (Phase A→F pipeline; STRICT/WARN dispatch)
    - provenance (DoorPlacementProvenance per v0.4 C5)
    - adversarial integration corpus (per
      B-C13-ADVERSARIAL-INTEGRATION-CORPUS)
    - PBT suite (target ≥27: 23 invariants + 3 failure-trigger +
      5 adversarial + 3 adversarial-stacking + 3 semantic-conformance
      per v0.4 C3)
"""
from __future__ import annotations

from .cache_keys import (
    build_advisory_cache_key,
    build_c13_cache_keys,
    build_full_cache_key,
    build_geometry_cache_key,
)
from .config import DoorPlacementConfig
from .conflict_resolution import (
    ConflictResolutionResult,
    DoorState,
    ResolutionStrategy,
    resolve_conflicts,
)
from .contracts import (
    C12V10EdgeAdapter,
    C13ConsumesFromC12Edge,
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
    EdgeType,
)
from .edge_selection import (
    EdgeAssignment,
    EdgeSelectionResult,
    select_edges,
)
from .errors import (
    C13ConfigurationError,
    ConditionalLegalityViolationError,
    DoorPlacementError,
    DoorPositionInfeasibleError,
    EntryRoomNotFoundError,
    HabitablePrimaryUnreachabilityError,
    LocalPlacementError,
    NbcBathroomKitchenAdjacencyError,
    NbcMasterBedroomAdjacencyError,
    NbcThroughBathroomRoutingError,
    PerCandidatePlacementError,
    PostResolutionUnreachabilityError,
    SwingArcConflictError,
    UpstreamSchemaDriftError,
)
from .position_selection import (
    PositionAssignment,
    PositionAssignmentResult,
    assign_positions,
)
from .schema import (
    AdvisoryCategory,
    AdvisoryFlag,
    AdvisoryFlagKind,
    AdvisorySeverity,
    C13CacheKeys,
    C13Phase,
    CausalContext,
    ConditionalLegalityViolation,
    Door,
    DoorPlacementBatchResult,
    FailedDoorPlacement,
    FailureRecord,
    GeometricFidelity,
    HABITABLE_ROOM_CATEGORIES,
    RoomDoorPreference,
    SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1,
    SecondaryDoorPreferenceKind,
    SuccessfulDoorPlacement,
)
from .assembly import assemble_doors
from .swing_assignment import (
    SwingAssignment,
    SwingAssignmentResult,
    SwingDecisionRule,
    assign_swings,
)
from .telemetry import (
    AdvisoryFlagEmittedEvent,
    C13TelemetrySink,
    DoorPlacementCompleteEvent,
    EdgeSelectionEvent,
    InMemoryTelemetrySink,
    NullTelemetrySink,
    PhaseDConvergenceEvent,
    SwingArcConflictEvent,
    SwingDirectionEvent,
    TelemetryEvent,
)
from .verification import VerificationReport, verify
from .orchestrator import place_doors
from .provenance import (
    CandidateProvenanceEntry,
    DoorPlacementProvenance,
    place_doors_with_provenance,
)
from .versioning import (
    ADVISORY_SCHEMA_VERSION,
    C13_EDGE_PROTOCOL_VERSION,
    C13_VERSION,
    DEFAULT_CORNER_OFFSET_M,
    DEFAULT_GRID_SNAP_M,
    DEFAULT_LEAF_THICKNESS_M,
    EXPECTED_C12_VERSION,
    EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION,
    EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION,
    MAX_DOORS_PER_ROOM_V1,
)

__all__ = [
    # Versioning constants
    "C13_VERSION",
    "C13_EDGE_PROTOCOL_VERSION",
    "ADVISORY_SCHEMA_VERSION",
    "MAX_DOORS_PER_ROOM_V1",
    "EXPECTED_C12_VERSION",
    "EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION",
    "EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION",
    "DEFAULT_CORNER_OFFSET_M",
    "DEFAULT_GRID_SNAP_M",
    "DEFAULT_LEAF_THICKNESS_M",
    # Errors — bases
    "DoorPlacementError",
    "LocalPlacementError",
    "PerCandidatePlacementError",
    # Errors — local (always halt)
    "UpstreamSchemaDriftError",
    "C13ConfigurationError",
    # Errors — per-candidate
    "EntryRoomNotFoundError",
    "DoorPositionInfeasibleError",
    "SwingArcConflictError",
    "PostResolutionUnreachabilityError",
    "HabitablePrimaryUnreachabilityError",
    "NbcBathroomKitchenAdjacencyError",
    "NbcThroughBathroomRoutingError",
    "NbcMasterBedroomAdjacencyError",
    "ConditionalLegalityViolationError",
    # Contracts
    "C13ConsumesFromC12Edge",
    "C12V10EdgeAdapter",
    "EdgeType",
    "EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID",
    # Schema — enums + literal vocabs
    "AdvisoryCategory",
    "GeometricFidelity",
    "AdvisoryFlagKind",
    "AdvisorySeverity",
    "SecondaryDoorPreferenceKind",
    "C13Phase",
    # Schema — reserved sentinel
    "CausalContext",
    # Schema — per-element
    "AdvisoryFlag",
    "Door",
    "RoomDoorPreference",
    "C13CacheKeys",
    "ConditionalLegalityViolation",
    "FailureRecord",
    # Schema — typestate result variants
    "SuccessfulDoorPlacement",
    "FailedDoorPlacement",
    "DoorPlacementBatchResult",
    # Schema — category sets
    "HABITABLE_ROOM_CATEGORIES",
    "SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1",
    # Config
    "DoorPlacementConfig",
    # Cache-key builders
    "build_geometry_cache_key",
    "build_advisory_cache_key",
    "build_full_cache_key",
    "build_c13_cache_keys",
    # Telemetry — events
    "EdgeSelectionEvent",
    "SwingDirectionEvent",
    "PhaseDConvergenceEvent",
    "SwingArcConflictEvent",
    "AdvisoryFlagEmittedEvent",
    "DoorPlacementCompleteEvent",
    # Telemetry — sink protocol + impls
    "TelemetryEvent",
    "C13TelemetrySink",
    "NullTelemetrySink",
    "InMemoryTelemetrySink",
    # Phase A — edge selection
    "EdgeAssignment",
    "EdgeSelectionResult",
    "select_edges",
    # Phase B — swing assignment
    "SwingAssignment",
    "SwingAssignmentResult",
    "SwingDecisionRule",
    "assign_swings",
    # Phase C — position selection
    "PositionAssignment",
    "PositionAssignmentResult",
    "assign_positions",
    # Phase D — swing-arc conflict resolution
    "DoorState",
    "ConflictResolutionResult",
    "ResolutionStrategy",
    "resolve_conflicts",
    # Phase E — canonical assembly
    "assemble_doors",
    # Phase F — pure verification
    "VerificationReport",
    "verify",
    # Orchestrator — top-level public API
    "place_doors",
    # Provenance — place_doors_with_provenance + types
    "CandidateProvenanceEntry",
    "DoorPlacementProvenance",
    "place_doors_with_provenance",
]
