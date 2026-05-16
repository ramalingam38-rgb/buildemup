"""
BuildemUp — Component 14 — Connection-Graph Quality Engine
===========================================================

Per C14 SPEC v0.2 LOCKED.

C14 ingests one batch of DoorPlacementBatchResult from C13 and produces,
per candidate, a CirculationGraphReport carrying:
- Adjacency graph (rooms = nodes, doors = edges) per Hillier convention
- Graph quality metrics (step-depth, mean depth, RA/RRA, integration,
  connectivity, betweenness — per Space Syntax 1984/1987)
- Quality flags split into STRUCTURAL (BOTTLENECK_CONCENTRATION,
  DEAD_END_ISOLATION, CATEGORY_COVERAGE_LOW, TRUNCATION_META) and
  PREFERENCE (TRANSIT_THROUGH_BEDROOM, PRIVACY_GRADIENT_VIOLATION,
  EXCESSIVE_DEPTH, TRUNCATION_META) — per v0.2 A4
- Aggregated AdvisoryFlag passthrough + augmentation

C14 is per-candidate (not per-batch-aggregate). One CirculationGraphReport
per SuccessfulDoorPlacement consumed.

Per § 0.0 (v0.2 A7 disclaimer): C14 is graph abstraction, not lived
experience. Treat metrics as heuristic signals, never authoritative.

Per v0.2 A10: lower depth / higher integration is NOT inherently better.
Preference flags default to severity=info. Severity escalation belongs
to C15.

This module re-exports the public surface that downstream consumers
(C15, C17) and tests should import from `buildemup.components.c14`
directly (no need to drill into sub-modules).
"""
from __future__ import annotations

# versioning
from .versioning import (
    C14_VERSION,
    C14_METRIC_VERSION,
    EXPECTED_C13_VERSION,
    EXPECTED_ADVISORY_SCHEMA_VERSION,
    DEFAULT_FLAG_DENSITY_FACTOR,
    DEFAULT_BETWEENNESS_THRESHOLD,
    DEFAULT_EXCESSIVE_DEPTH_THRESHOLD,
    DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD,
    SMALL_GRAPH_REGIME_TINY,
    SMALL_GRAPH_REGIME_SMALL,
    GRAPH_SIZE_NORMAL_MIN,
)

# errors
from .errors import (
    CirculationAnalysisError,
    LocalCirculationError,
    PerCandidateCirculationError,
    UpstreamSchemaDriftError,
    C14ConfigurationError,
    EntryRoomNotFoundError,
    GraphInconsistencyError,
)

# contracts
from .contracts import (
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
    BEDROOM_CATEGORY_KEYWORDS,
    PUBLIC_CATEGORY_KEYWORDS,
    PRIVATE_CATEGORY_KEYWORDS,
    CIRCULATION_CATEGORY_KEYWORDS,
    ALL_RECOGNIZED_CATEGORY_KEYWORDS,
    RoomMetadata,
)

# config
from .config import CirculationConfig

# cache_keys
from .cache_keys import (
    C14CacheKeys,
    derive_c14_cache_keys,
    config_signature_for,
)

# schema
from .schema import (
    TRUNCATION_META_KIND_VALUE,
    StructuralCirculationFlagKind,
    PreferenceCirculationFlagKind,
    CirculationFlagKind,
    GraphSizeCategory,
    CirculationFlag,
    CirculationGraphReport,
    FailureRecord,
    SuccessfulCirculationAnalysis,
    FailedCirculationAnalysis,
    CirculationAnalysisBatchResult,
)

# graph_construction (Phase α)
from .graph_construction import (
    GraphTopology,
    construct_graph_topology,
)

# node_metrics (Phase β)
from .node_metrics import (
    NodeMetrics,
    compute_node_metrics,
)

# layout_metrics (Phase γ)
from .layout_metrics import (
    LayoutMetrics,
    compute_layout_metrics,
)

# flag_emission (Phase δ)
from .flag_emission import (
    EmittedFlags,
    emit_flags,
)

# advisory_passthrough (Phase ε)
from .advisory_passthrough import (
    AdvisoryBundle,
    assemble_advisory_bundle,
)

# report_assembly (Phase ζ)
from .report_assembly import (
    compute_category_coverage,
    assemble_report,
)

# orchestrator (Sub 5)
from .orchestrator import (
    analyze_circulation,
    analyze_circulation_batch,
)


__all__ = [
    # versioning
    "C14_VERSION",
    "C14_METRIC_VERSION",
    "EXPECTED_C13_VERSION",
    "EXPECTED_ADVISORY_SCHEMA_VERSION",
    "DEFAULT_FLAG_DENSITY_FACTOR",
    "DEFAULT_BETWEENNESS_THRESHOLD",
    "DEFAULT_EXCESSIVE_DEPTH_THRESHOLD",
    "DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD",
    "SMALL_GRAPH_REGIME_TINY",
    "SMALL_GRAPH_REGIME_SMALL",
    "GRAPH_SIZE_NORMAL_MIN",
    # errors
    "CirculationAnalysisError",
    "LocalCirculationError",
    "PerCandidateCirculationError",
    "UpstreamSchemaDriftError",
    "C14ConfigurationError",
    "EntryRoomNotFoundError",
    "GraphInconsistencyError",
    # contracts
    "EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID",
    "BEDROOM_CATEGORY_KEYWORDS",
    "PUBLIC_CATEGORY_KEYWORDS",
    "PRIVATE_CATEGORY_KEYWORDS",
    "CIRCULATION_CATEGORY_KEYWORDS",
    "ALL_RECOGNIZED_CATEGORY_KEYWORDS",
    "RoomMetadata",
    # config
    "CirculationConfig",
    # cache_keys
    "C14CacheKeys",
    "derive_c14_cache_keys",
    "config_signature_for",
    # schema
    "TRUNCATION_META_KIND_VALUE",
    "StructuralCirculationFlagKind",
    "PreferenceCirculationFlagKind",
    "CirculationFlagKind",
    "GraphSizeCategory",
    "CirculationFlag",
    "CirculationGraphReport",
    "FailureRecord",
    "SuccessfulCirculationAnalysis",
    "FailedCirculationAnalysis",
    "CirculationAnalysisBatchResult",
    # graph_construction (Phase α)
    "GraphTopology",
    "construct_graph_topology",
    # node_metrics (Phase β)
    "NodeMetrics",
    "compute_node_metrics",
    # layout_metrics (Phase γ)
    "LayoutMetrics",
    "compute_layout_metrics",
    # flag_emission (Phase δ)
    "EmittedFlags",
    "emit_flags",
    # advisory_passthrough (Phase ε)
    "AdvisoryBundle",
    "assemble_advisory_bundle",
    # report_assembly (Phase ζ)
    "compute_category_coverage",
    "assemble_report",
    # orchestrator (Sub 5)
    "analyze_circulation",
    "analyze_circulation_batch",
]
