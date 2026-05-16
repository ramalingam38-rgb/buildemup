"""
BuildemUp — Component 14 — error / failure hierarchy
=====================================================

Per C14 SPEC v0.2 LOCKED (v0.1 § 4 + v0.1 § 5 + v0.2 amendments
do not alter the error hierarchy).

The hierarchy mirrors C13's two-tier pattern:
- LocalCirculationError: orchestrator-level errors that ALWAYS halt
  (schema drift, configuration invalid). Always raises regardless
  of strict_mode.
- PerCandidateCirculationError: per-candidate failures (analysis failed
  for this candidate; other candidates may succeed).

STRICT vs WARN mode behavior:
- Under STRICT: PerCandidateCirculationError raises immediately,
  halting the batch.
- Under WARN: PerCandidateCirculationError is caught by the orchestrator,
  recorded in CirculationAnalysisBatchResult.failed (typestate
  FailedCirculationAnalysis), and the candidate is skipped; batch continues.

LocalCirculationError always raises regardless of mode.

Per v0.1 § 4 final paragraph: **No NBC-style vetoes at C14** — those
live at C13. C14 is a read-only analytical pass.
"""
from __future__ import annotations


# =============================================================================
# Base classes
# =============================================================================

class CirculationAnalysisError(Exception):
    """Base of all C14 errors."""


class LocalCirculationError(CirculationAnalysisError):
    """Orchestrator-level errors that halt the batch.

    These represent issues with the configuration, the upstream
    contract, or the C14 runtime itself — NOT with individual candidates.
    ALWAYS raised regardless of strict_mode.
    """


class PerCandidateCirculationError(CirculationAnalysisError):
    """Per-candidate circulation-analysis failures.

    Under STRICT mode: raised immediately, halting the batch.
    Under WARN mode: caught by the orchestrator, recorded into
    CirculationAnalysisBatchResult.failed (typestate
    FailedCirculationAnalysis), and the candidate is skipped.

    Per the typestate discipline inherited from C13 v0.3 B11:
    WARN-mode failures CANNOT be misused as successful results
    because the typestate discrimination is enforced at the schema
    level.
    """


# =============================================================================
# Local (orchestrator-level) errors — ALWAYS halt
# =============================================================================

class UpstreamSchemaDriftError(LocalCirculationError):
    """Per v0.1 § 4. Mirrors C13's UpstreamSchemaDriftError.

    Raised when an upstream component's schema version constant does
    not match what C14 was built against:
    - C13_VERSION != EXPECTED_C13_VERSION
    - ADVISORY_SCHEMA_VERSION != EXPECTED_ADVISORY_SCHEMA_VERSION

    Severity: systemic. Halts the batch immediately under any mode.
    Prevents silent cross-component contract drift.
    """


class C14ConfigurationError(LocalCirculationError):
    """Per v0.1 § 4. Configuration-domain errors detected at startup.

    Examples:
    - Negative flag_density_factor
    - Threshold values out of valid range
    - Inconsistent category-keyword sets

    Severity: configuration. Halts the batch immediately under any mode.
    """


# =============================================================================
# Per-candidate errors — STRICT halts, WARN collects
# =============================================================================

class EntryRoomNotFoundError(PerCandidateCirculationError):
    """Per v0.1 § 4.

    Raised when `main_entry_room_id` is not in `placed_room_ids` for
    a candidate. Defensive — C13 already validates this — but C14
    re-checks at ingress to fail fast on contract drift.
    """


class GraphInconsistencyError(PerCandidateCirculationError):
    """Per v0.1 § 4.

    Raised when the derived graph violates a basic structural invariant
    that should already be enforced upstream (e.g., an edge references
    an unknown room_id). Defensive against C13 contract drift.
    """


__all__ = [
    "CirculationAnalysisError",
    "LocalCirculationError",
    "PerCandidateCirculationError",
    "UpstreamSchemaDriftError",
    "C14ConfigurationError",
    "EntryRoomNotFoundError",
    "GraphInconsistencyError",
]
