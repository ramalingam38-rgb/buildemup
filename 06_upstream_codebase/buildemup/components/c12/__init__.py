"""
BuildemUp — Component 12 — Multi-Floor Placement & Vertical Alignment Engine
=============================================================================

Per C12 SPEC v1.0 LOCKED at S43 by Ramalingam directive
("Lock it and start coding").

This package implements C12 in the canonical Track 3 numbering. It
consumes RefinedCandidate / MultiFloorRefinedCandidate from C11b plus
the C8 corridor_zones derived view + C9 adjacency_hints field on
FloorRoomBrief, and emits PlacedCandidate / MultiFloorPlacedCandidate
geometry consumed downstream by C13 (Door Placement) and C14
(Unified Evaluation).

v1 SCOPE BOUNDARY (per v0.5-A2 explicit guarantee statement):
  GUARANTEES:
    - Deterministic geometric realization (TIER-1 byte-equal replay)
    - Bounded feasibility placement (slicing_kd_tree algorithm)
    - NBC 2016 doorway feasibility validation
    - Multi-floor vertical alignment within configurable tolerance
  DOES NOT GUARANTEE:
    - Architectural quality (C14 scoring)
    - Human usability (C13 door placement + post-v1 work)
    - Structural realism (B-C12-VOLUMETRIC-ALIGNMENT)
    - Zoning intelligence (B-PROJECT-HIERARCHICAL-PLANNING)
    - Cross-platform replay (B-C12-REPLAY-TIERS)
    - High architectural diversity (B-C12-CSP-PLACEMENT)

S44+ BUILD STATUS:
  Currently shipped foundational layer:
    - versioning (C12_VERSION, expected upstream schema versions)
    - errors (11 failure types per § 4)
    - schema (6 public output dataclasses per § 2.2)
    - config (PlacementConfig per § 2.3)
  Pending build work (S45+):
    - bounds / input_resolution / env_fingerprint
    - slicing-tree placement subpackage
    - vav / mfra / phase1 / phase1b / phase2 / phase3
    - orchestrator
    - telemetry / provenance
    - integration test suite
"""
from __future__ import annotations

from .bounds import (
    DEFAULT_EPSILON_M,
    DEFAULT_GRID_SNAP_M,
    axis_overlap_length,
    rectangle_contains,
    rectangles_overlap,
    snap_to_grid,
)
from .config import PlacementConfig
from .env_fingerprint import (
    C12EnvironmentFingerprint,
    capture_c12_environment_fingerprint,
    compute_c12_cache_key,
)
from .errors import (
    AdjacencyConstraintViolationError,
    C12ConfigurationError,
    CapabilityFlagInconsistencyError,
    CirculationInfeasibilityError,
    DoorwayFeasibilityError,
    GeometricInfeasibilityError,
    LocalPlacementError,
    PerCandidatePlacementError,
    PlacementAlgorithmTimeoutError,
    PlacementError,
    UpstreamSchemaDriftError,
    VerticalAlignmentError,
)
from .input_resolution import (
    NBC_2016_DOORWAY_MIN_BATHROOM_M,
    NBC_2016_DOORWAY_MIN_BEDROOM_M,
    NBC_2016_DOORWAY_MIN_GENERAL_M,
    NBC_2016_DOORWAY_MIN_MAIN_ENTRANCE_M,
    assert_materialized_capability,
    assert_upstream_schema_versions,
    doorway_minimum_for_pair,
    is_canonical_other_room_category,
    list_unknown_other_rooms,
    normalize_other_room_category,
)
from .mfra import absorb_multi_floor_placements
from .orchestrator import (
    MultiFloorPlacementInput,
    SingleFloorPlacementInput,
    place_and_align,
    place_and_align_with_provenance,
)
from .prng import TieBreakPRNG
from .provenance import CandidateProvenanceEntry, PlacementProvenance
from .reachability import all_rooms_reachable
from .schema import (
    FailureRecord,
    MultiFloorPlacedCandidate,
    PlacedCandidate,
    PlacedRoom,
    PlacementBatchResult,
    SharedEdge,
    VerticalAlignmentReport,
)
from .shared_edges import MIN_SHARED_EDGE_LENGTH_M, derive_shared_edges
from .slicing_kd_tree import RoomSpec, place_rooms_slicing_tree
from .telemetry import (
    DEFAULT_TELEMETRY_SINK,
    AdjacencyCoverageEvent,
    IrregularEnvelopeRejectionEvent,
    ListTelemetrySink,
    MfraConvergenceEvent,
    NullTelemetrySink,
    PerformanceEvent,
    PlacementDiversityEvent,
    TelemetrySink,
    UnknownCategoryEvent,
)
from .vav import verify_vertical_alignment
from .versioning import (
    C12_VERSION,
    EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION,
    EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION,
)
from .vertical_core_reservation import (
    VerticalCoreKind,
    VerticalCoreReservation,
    assert_no_internal_conflicts,
    canonicalize_reservations,
    reservations_overlap,
)

__all__ = [
    # Versioning
    "C12_VERSION",
    "EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION",
    "EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION",
    # Config
    "PlacementConfig",
    # Schema dataclasses
    "PlacedRoom",
    "SharedEdge",
    "PlacedCandidate",
    "VerticalAlignmentReport",
    "MultiFloorPlacedCandidate",
    "FailureRecord",
    "PlacementBatchResult",
    # Errors
    "PlacementError",
    "LocalPlacementError",
    "PerCandidatePlacementError",
    "UpstreamSchemaDriftError",
    "C12ConfigurationError",
    "GeometricInfeasibilityError",
    "CapabilityFlagInconsistencyError",
    "PlacementAlgorithmTimeoutError",
    "CirculationInfeasibilityError",
    "VerticalAlignmentError",
    "DoorwayFeasibilityError",
    "AdjacencyConstraintViolationError",
    # Bounds utilities
    "DEFAULT_EPSILON_M",
    "DEFAULT_GRID_SNAP_M",
    "rectangle_contains",
    "rectangles_overlap",
    "snap_to_grid",
    "axis_overlap_length",
    # PRNG
    "TieBreakPRNG",
    # Env fingerprint
    "C12EnvironmentFingerprint",
    "capture_c12_environment_fingerprint",
    "compute_c12_cache_key",
    # Input resolution (Phase 0 ingress)
    "assert_upstream_schema_versions",
    "assert_materialized_capability",
    "normalize_other_room_category",
    "is_canonical_other_room_category",
    "list_unknown_other_rooms",
    "NBC_2016_DOORWAY_MIN_MAIN_ENTRANCE_M",
    "NBC_2016_DOORWAY_MIN_BEDROOM_M",
    "NBC_2016_DOORWAY_MIN_BATHROOM_M",
    "NBC_2016_DOORWAY_MIN_GENERAL_M",
    "doorway_minimum_for_pair",
    # Shared edge derivation
    "MIN_SHARED_EDGE_LENGTH_M",
    "derive_shared_edges",
    # Reachability (Phase 0b)
    "all_rooms_reachable",
    # Vertical core reservation (Phase 1b)
    "VerticalCoreKind",
    "VerticalCoreReservation",
    "canonicalize_reservations",
    "reservations_overlap",
    "assert_no_internal_conflicts",
    # Slicing-tree placement (Phase 1)
    "RoomSpec",
    "place_rooms_slicing_tree",
    # VAV (Phase 2)
    "verify_vertical_alignment",
    # MFRA (Phase 2)
    "absorb_multi_floor_placements",
    # Orchestrator (top-level entry)
    "SingleFloorPlacementInput",
    "MultiFloorPlacementInput",
    "place_and_align",
    "place_and_align_with_provenance",
    # Telemetry (observability)
    "TelemetrySink",
    "NullTelemetrySink",
    "ListTelemetrySink",
    "DEFAULT_TELEMETRY_SINK",
    "PlacementDiversityEvent",
    "MfraConvergenceEvent",
    "AdjacencyCoverageEvent",
    "PerformanceEvent",
    "UnknownCategoryEvent",
    "IrregularEnvelopeRejectionEvent",
    # Provenance
    "CandidateProvenanceEntry",
    "PlacementProvenance",
]
