"""
BuildemUp — Component 15 — error / failure hierarchy
=====================================================

Per C15 SPEC v0.2 LOCKED (v0.1 § 4 + v0.1 § 5 + v0.2 amendments that
add MissingMetadataError surface area per A3 Inv P17).

The hierarchy mirrors C14's two-tier pattern (which itself mirrors C13):

- **LocalProblemError**: orchestrator-level errors that ALWAYS halt
  (schema drift, configuration invalid, registry inconsistency).
  Always raises regardless of strict_mode.
- **PerCandidateProblemError**: per-candidate analysis failures
  (analysis failed for this candidate; other candidates may succeed).

STRICT vs WARN mode behavior:
- Under STRICT: PerCandidateProblemError raises immediately, halting
  the batch.
- Under WARN: PerCandidateProblemError is caught by the orchestrator,
  recorded in ProblemAnalysisBatchResult.failed (typestate
  FailedProblemAnalysis), and the candidate is skipped; batch continues.

LocalProblemError always raises regardless of mode.

Per v0.1 § 4 final paragraph: **No NBC-style vetoes at C15** — checks
emit problem records, not exceptions. Failing a check produces a
ProblemCheck with status=FAIL and a severity, not a raised exception.

Per Inv P0 (v0.2 A1 STRICTER): no error class returns or carries a
numeric layout-quality score. Failures are descriptive, not aggregative.
"""
from __future__ import annotations


# =============================================================================
# Base classes
# =============================================================================

class ProblemAnalysisError(Exception):
    """Base of all C15 errors.

    All other C15 exception classes inherit from this. Downstream
    consumers can catch `ProblemAnalysisError` to handle any C15
    failure mode generically; for fine-grained dispatch, catch the
    two-tier subclasses (LocalProblemError vs PerCandidateProblemError).
    """


class LocalProblemError(ProblemAnalysisError):
    """Orchestrator-level errors that halt the batch.

    These represent issues with the configuration, the upstream
    contract, the check registry, or the C15 runtime itself — NOT
    with individual candidates.

    ALWAYS raised regardless of strict_mode. Catching this in WARN
    mode and continuing the batch would be a contract violation.
    """


class PerCandidateProblemError(ProblemAnalysisError):
    """Per-candidate problem-analysis failures.

    Under STRICT mode: raised immediately, halting the batch.
    Under WARN mode: caught by the orchestrator, recorded into
    ProblemAnalysisBatchResult.failed (typestate
    FailedProblemAnalysis), and the candidate is skipped.

    Per the typestate discipline inherited from C13 v0.3 B11 +
    C14 v0.2: WARN-mode failures CANNOT be misused as successful
    results because the typestate discrimination is enforced at
    the schema level (FailedProblemAnalysis has no `.report` field
    of type ProblemReport).
    """


# =============================================================================
# Local (orchestrator-level) errors — ALWAYS halt
# =============================================================================

class UpstreamSchemaDriftError(LocalProblemError):
    """Per v0.1 § 4. Mirrors C13/C14 UpstreamSchemaDriftError.

    Raised when an upstream component's schema version constant does
    not match what C15 was built against:
    - C14_VERSION != EXPECTED_C14_VERSION
    - C14_METRIC_VERSION != EXPECTED_C14_METRIC_VERSION
    - ADVISORY_SCHEMA_VERSION != EXPECTED_ADVISORY_SCHEMA_VERSION

    Severity: systemic. Halts the batch immediately under any mode.
    Prevents silent cross-component contract drift.

    Recovery: bump C15's EXPECTED_C14_* constants to match the new
    upstream, run the integration test corpus, then re-deploy.
    """


class C15ConfigurationError(LocalProblemError):
    """Per v0.1 § 4. Configuration-domain errors detected at startup.

    Examples:
    - Negative per_candidate_wallclock_seconds
    - Invalid cache_mode value
    - Strict_mode of non-bool type

    Severity: configuration. Halts the batch immediately under any
    mode. Raised at ProblemFinderConfig.__post_init__ so
    misconfigurations halt at startup, not at first analyze() call.
    """


class CheckRegistryError(LocalProblemError):
    """Per v0.1 § 4 + v0.2 A4 Inv P18.

    Raised at module load when the check registry or severity-rule
    table is internally inconsistent:

    - A check_id appears in the severity-rule table that's not in
      the registered check set (or vice versa)
    - A severity rule's `severity_basis` is shorter than
      MIN_SEVERITY_BASIS_LENGTH (per A4 Inv P18)
    - A check_id pattern violates the `P{dimension}.{check_index}`
      shape (per v0.1 § 1.5)
    - A check's `dimension_id` is outside the legal range [1, 10]
    - Duplicate check_id in the registry

    Severity: systemic. Halts at module import.

    LOCK-mandatory backlog item **B-C15-CHECK-REGISTRY-LOCK** will pin
    the exact registered check set at v1.0 LOCK. Pre-v1.0 walks can
    amend the registry; each amendment bumps C15_CHECK_REGISTRY_VERSION.
    """


# =============================================================================
# Per-candidate errors — STRICT halts, WARN collects
# =============================================================================

class MissingMetadataError(PerCandidateProblemError):
    """Per v0.1 § 4 + v0.2 A3 Inv P17.

    Raised when required threaded metadata is absent for a candidate:

    - `cultural_profile` not provided (Inv P17 NEW per A3 — REQUIRED,
      no default). The reviewer's concern in A3 was that an implicit
      default would harden into "the system's idea of a proper home."
      Making the field required forces every caller to declare which
      cultural lens C15 should apply.
    - `room_categories` empty or missing keys for placed rooms
    - `floor_metadata` empty or inconsistent
    - `main_entry_room_id` not in `placed_room_ids`

    Under STRICT: halts the batch.
    Under WARN: caught + recorded in FailedProblemAnalysis with
    phase="pi" (Phase π — Ingress + metadata resolution).
    """


class InconsistentInputError(PerCandidateProblemError):
    """Per v0.1 § 4.

    Raised when C12/C13/C14 outputs disagree on the room set or other
    cross-component contract for a candidate. Defensive — upstream
    invariants should prevent this — but C15 fails fast to surface
    drift rather than silently producing incoherent reports.

    Examples:
    - C12 PlacedCandidate.placed_rooms has a room_id absent from
      C13 SuccessfulDoorPlacement's door endpoints AND from C14
      CirculationGraphReport's nodes
    - C14 graph has nodes that C12 doesn't list as placed rooms
    - source_placed_candidate_signature mismatch across C13 → C14 →
      metadata for the same candidate

    Under STRICT: halts.
    Under WARN: collected into FailedProblemAnalysis with the phase
    where the inconsistency was detected.
    """


__all__ = [
    # base
    "ProblemAnalysisError",
    "LocalProblemError",
    "PerCandidateProblemError",
    # local (always halt)
    "UpstreamSchemaDriftError",
    "C15ConfigurationError",
    "CheckRegistryError",
    # per-candidate (strict halts / warn collects)
    "MissingMetadataError",
    "InconsistentInputError",
]
