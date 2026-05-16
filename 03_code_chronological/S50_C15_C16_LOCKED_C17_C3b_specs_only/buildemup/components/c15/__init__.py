"""
BuildemUp — Component 15 — Layout Problem Finder
=================================================

Per C15 SPEC v0.2 LOCKED (S46).

C15 ingests one batch of CirculationAnalysisBatchResult from C14 plus an
upstream PlacementBatchResult-shaped context, and produces, per
SuccessfulCirculationAnalysis candidate, a ProblemReport carrying:

- applicable_checks: tuple[ProblemCheck, ...] with status PASS / WARN /
  FAIL and one of three epistemic kinds (regulatory,
  architectural_heuristic, cultural_preference) — per v0.2 A2.
- deferred_checks: tuple[DeferredCheck, ...] for checks that resolve to
  NOT_APPLICABLE on this candidate — per v0.2 A5. Reasons mandatory;
  blocking backlog item optional.
- dimension_summary: tuple[DimensionSummary, ...] reporting per-dimension
  n_applicable / n_pass / n_warn / n_fail / n_deferred. n_applicable is
  REPORTED SEPARATELY from pass/warn/fail counts so downstream cannot
  reconstruct a quality fraction via arithmetic — per v0.2 A10.
- dimensions_not_evaluated: tuple[str, ...] explicitly listing v1 gaps
  (e.g., "natural_light_full", "outdoor_connection_full") — per v0.2 A6.
- unconventional_pattern_hint: optional UnconventionalPatternHint
  surfacing one of five v1-recognized non-Western residential patterns
  (courtyard_centered, split_level_circulation, ritual_procession,
  compact_incremental, multigenerational_segregation) — per v0.2 A7.
- cultural_profile_active: the CulturalProfile value used to pick
  cultural-preference checks. REQUIRED (no default) — per v0.2 A3.

C15 is per-candidate (not per-batch-aggregate). One ProblemReport per
SuccessfulCirculationAnalysis consumed.

**Invariant P0 — STRICTER at v0.2 (A1)**: C15 NEVER computes a single
number representing layout quality, anywhere — not in public API, not
in helpers, not in telemetry, not in cache keys. Purely descriptive.
Aggregation belongs to C17 (the ranker), and even C17 reads C15's
PROBLEM LIST, not a C15 quality fraction. The output of `analyze_problems`
is a typestate result; quality is read by inspecting checks, not by
summing them.

Per §0.5 (v0.2 A9 optimization-pressure disclosure): downstream tools
must not optimize against the count of PASS/FAIL across dimensions
without acknowledging that uniform pass density across dimensions is
not the goal (architectural quality is irreducible to such a metric).

This module re-exports the public surface that downstream consumers
(C17, tests) and the orchestrator itself should import from
`buildemup.components.c15` directly. Sub-1 (S48) ships the
foundational layer only — schema, contracts, errors, config, cache
keys, versioning. Phase modules (α dimension-1..ε orchestrator) ship
in Sub-2 through Sub-5.
"""
from __future__ import annotations

# versioning
from .versioning import (
    C15_VERSION,
    C15_CHECK_REGISTRY_VERSION,
    EXPECTED_C14_VERSION,
    EXPECTED_C14_METRIC_VERSION,
    EXPECTED_ADVISORY_SCHEMA_VERSION,
    DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS,
    DEFAULT_PER_BATCH_WALLCLOCK_SECS,
    MIN_SEVERITY_BASIS_LENGTH,
    TOTAL_DIMENSIONS,
    MIN_DIMENSION_ID,
    MAX_DIMENSION_ID,
    DIMENSIONS_NOT_EVALUATED_V1,
)

# errors
from .errors import (
    ProblemAnalysisError,
    LocalProblemError,
    PerCandidateProblemError,
    UpstreamSchemaDriftError,
    C15ConfigurationError,
    CheckRegistryError,
    MissingMetadataError,
    InconsistentInputError,
)

# contracts
from .contracts import (
    CulturalProfile,
    VALID_CULTURAL_PROFILE_VALUES,
    FloorInfo,
    ProblemAnalysisMetadata,
)

# config
from .config import ProblemFinderConfig

# cache_keys
from .cache_keys import (
    C15CacheKeys,
    derive_c15_cache_keys,
    config_signature_for,
)

# schema
from .schema import (
    CheckStatus,
    CheckSeverity,
    CheckEpistemicKind,
    PhaseLiteral,
    SeverityRule,
    ProblemCheck,
    DeferredCheck,
    UNCONVENTIONAL_PATTERN_NAMES,
    UnconventionalPatternHint,
    DimensionSummary,
    ProblemReport,
    FailureRecord,
    SuccessfulProblemAnalysis,
    FailedProblemAnalysis,
    ProblemAnalysisBatchResult,
    # v0.3 A12 (S48 Path A) — coverage-of-evaluation signal, NOT
    # quality-of-layout signal. Inv P0 STRICTER preserved.
    CoverageQuality,
    DimensionMaturity,
)

# protocol (Sub-2)
from .protocol import (
    Check,
    CheckContext,
    DEP_C12_PLACEMENT,
    DEP_C12_PLACEMENT_GEOMETRY,
    DEP_C14_GRAPH,
    DEP_C14_FLAGS,
    DEP_ROOM_CATEGORIES,
    DEP_FLOOR_METADATA,
    DEP_MAIN_ENTRY,
    DEP_WINDOW_DATA,
    DEP_FURNITURE_FIT,
    DEP_PLOT_FAR_CEILING,
    DEP_ENVELOPE_POLYGON_SUBTRACTION,
    probe_dependencies,
)

# registry (Sub-2)
from .registry import (
    CheckRegistry,
    make_registry,
    build_registry,
)

# severity_rule_table (Sub-2)
from .severity_rule_table import (
    SEVERITY_RULE_TABLE_V_SUB2,
    SEVERITY_RULE_TABLE_V1,
    lookup_severity,
    verify_rule_table_integrity,
)

# orchestrator (Sub-3/4/5/6 — completed)
from .orchestrator import (
    analyze_problems,
    analyze_problems_batch,
)


__all__ = [
    # versioning
    "C15_VERSION",
    "C15_CHECK_REGISTRY_VERSION",
    "EXPECTED_C14_VERSION",
    "EXPECTED_C14_METRIC_VERSION",
    "EXPECTED_ADVISORY_SCHEMA_VERSION",
    "DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS",
    "DEFAULT_PER_BATCH_WALLCLOCK_SECS",
    "MIN_SEVERITY_BASIS_LENGTH",
    "TOTAL_DIMENSIONS",
    "MIN_DIMENSION_ID",
    "MAX_DIMENSION_ID",
    "DIMENSIONS_NOT_EVALUATED_V1",
    # errors
    "ProblemAnalysisError",
    "LocalProblemError",
    "PerCandidateProblemError",
    "UpstreamSchemaDriftError",
    "C15ConfigurationError",
    "CheckRegistryError",
    "MissingMetadataError",
    "InconsistentInputError",
    # contracts
    "CulturalProfile",
    "VALID_CULTURAL_PROFILE_VALUES",
    "FloorInfo",
    "ProblemAnalysisMetadata",
    # config
    "ProblemFinderConfig",
    # cache_keys
    "C15CacheKeys",
    "derive_c15_cache_keys",
    "config_signature_for",
    # schema enums + types
    "CheckStatus",
    "CheckSeverity",
    "CheckEpistemicKind",
    "PhaseLiteral",
    # schema records
    "SeverityRule",
    "ProblemCheck",
    "DeferredCheck",
    "UNCONVENTIONAL_PATTERN_NAMES",
    "UnconventionalPatternHint",
    "DimensionSummary",
    "ProblemReport",
    # schema typestate
    "FailureRecord",
    "SuccessfulProblemAnalysis",
    "FailedProblemAnalysis",
    "ProblemAnalysisBatchResult",
    # v0.3 A12 (S48 Path A) coverage-of-evaluation enums
    "CoverageQuality",
    "DimensionMaturity",
    # protocol (Sub-2)
    "Check",
    "CheckContext",
    "DEP_C12_PLACEMENT",
    "DEP_C12_PLACEMENT_GEOMETRY",
    "DEP_C14_GRAPH",
    "DEP_C14_FLAGS",
    "DEP_ROOM_CATEGORIES",
    "DEP_FLOOR_METADATA",
    "DEP_MAIN_ENTRY",
    "DEP_WINDOW_DATA",
    "DEP_FURNITURE_FIT",
    "DEP_PLOT_FAR_CEILING",
    "DEP_ENVELOPE_POLYGON_SUBTRACTION",
    "probe_dependencies",
    # registry (Sub-2)
    "CheckRegistry",
    "make_registry",
    "build_registry",
    # severity rule table (Sub-2 + v1 complete)
    "SEVERITY_RULE_TABLE_V_SUB2",
    "SEVERITY_RULE_TABLE_V1",
    "lookup_severity",
    "verify_rule_table_integrity",
    # orchestrator
    "analyze_problems",
    "analyze_problems_batch",
]
