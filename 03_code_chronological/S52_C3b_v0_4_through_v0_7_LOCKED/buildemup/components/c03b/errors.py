"""
C3b — Post-Layout Trade-off Negotiation — error hierarchy
==========================================================

Spec: C3b v0.4.LOCKED § 4. Build session: S52.

Two-tier hierarchy mirrors C16/C17 LOCKED pattern:

    LocalTradeoffError              (always halts; affects whole session)
    │
    ├── UpstreamSchemaDriftError    (SelectionResult / ProblemReport drift)
    ├── C3bConfigurationError       (bad jurisdiction / iteration cap)
    ├── ApplicabilityBoundaryError  (Preview Mode, high_ambiguity, Pareto collapse)
    ├── SessionPersistenceError     (SQLite WAL write failure)
    ├── SubsetRerunOrchestrationError (orchestrator failed; session enters terminal state)
    └── TopologyInvarianceProbeError (v0.2 — Phase β step 4.2 couldn't determine prediction_basis)

    PerTweakError                   (STRICT raises / WARN collects)
    │
    ├── TweakGenerationError        (can't generate a candidate)
    ├── ImpactComputationError      (cost / space / comfort impact failed)
    ├── ConstraintViolationError    (apply would violate hard constraint)
    ├── RecommendationFlagAmbiguityError (can't classify suggested/optional/alternative)
    ├── DownstreamImpactSetMissingError  (v0.2 — empty downstream_impact_set on MEDIUM)
    └── CompatibilityAssertionFailedError (v0.2 — Phase ε apply found "conflicts" against prior tweak)

Rule 11 self-analysis:
  1. The split is *behavioral*, not *structural*: STRICT halts vs WARN
     collects routes by base class, not severity guess. Tests must
     verify the routing happens at orchestrator boundary, not deeper.
  2. UpstreamSchemaDriftError specifically fires when EXPECTED_C*
     versions don't match runtime — caught at Phase α, not later
     where the mismatch produces a baffling AttributeError.
  3. ApplicabilityBoundaryError is the § 1.4 exit ramp. The session
     enters "abandoned_no_tweaks" with an explicit advisory note
     explaining why — not a stack trace.
  4. SubsetRerunOrchestrationError is the only Local error that
     PRODUCES a TradeoffSession in a terminal state — the others
     prevent session creation entirely. Documented because that
     distinction matters at the orchestrator level.
"""
from __future__ import annotations

from typing import Optional


# ============================================================
# § 1 — Base classes
# ============================================================

class C3bError(Exception):
    """Root of all C3b-emitted errors. Useful for catch-all guard
    rails in tests and orchestration boundaries; not normally caught
    in business code."""


class LocalTradeoffError(C3bError):
    """LOCAL errors — affect the WHOLE session.

    Always halt. Independent of strict_mode. The session either:
      - never starts (constructor / Phase α refusal), OR
      - enters a terminal "abandoned_no_tweaks" / "kicked_back_to_c3a"
        state with explicit advisory."""

    def __init__(
        self,
        message:        str,
        *,
        session_id:     Optional[str] = None,
        phase:          Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.session_id = session_id
        self.phase = phase


class PerTweakError(C3bError):
    """PER-TWEAK errors — affect ONE tweak candidate only.

    STRICT mode: raised. WARN mode: collected to a failure list;
    the affected tweak is dropped from the option set, other tweaks
    proceed."""

    def __init__(
        self,
        message:         str,
        *,
        tweak_id:        Optional[str] = None,
        layout_id:       Optional[str] = None,
        reason:          Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.tweak_id = tweak_id
        self.layout_id = layout_id
        self.reason = reason


# ============================================================
# § 2 — LocalTradeoffError subclasses (spec § 4.1)
# ============================================================

class UpstreamSchemaDriftError(LocalTradeoffError):
    """Upstream component's schema doesn't match expected LOCKED
    version. E.g., SelectionResult v0.9 received but EXPECTED_C15_VERSION
    pins v1.0.LOCKED.

    Halts at Phase α before any tweak generation."""

    def __init__(
        self,
        message:           str,
        *,
        expected_version:  Optional[str] = None,
        observed_version:  Optional[str] = None,
        upstream:          Optional[str] = None,
    ) -> None:
        super().__init__(message, phase="alpha")
        self.expected_version = expected_version
        self.observed_version = observed_version
        self.upstream = upstream


class C3bConfigurationError(LocalTradeoffError):
    """Bad jurisdiction, unsupported domain scope, or invalid
    iteration cap. Caught at C3bRuntimeConfig construction OR Phase α
    pre-flight."""

    def __init__(
        self,
        message:         str,
        *,
        offending_field: Optional[str] = None,
        offending_value: Optional[object] = None,
    ) -> None:
        super().__init__(message)
        self.offending_field = offending_field
        self.offending_value = offending_value


class ApplicabilityBoundaryError(LocalTradeoffError):
    """The input SelectionResult fails § 1.4 applicability boundary:
    Preview Mode unresolved, ProblemReport.overall_report_tier ==
    'high_ambiguity', or Pareto-front collapse below diversity floor.

    Does NOT halt error-style; instead produces a TradeoffSession
    with current_status='abandoned_no_tweaks' and an advisory note.
    The exception form here is used during construction guard rails
    in tests; the runtime path emits the terminal session."""

    def __init__(
        self,
        message:        str,
        *,
        boundary_kind:  Optional[str] = None,
        diagnostic:     Optional[str] = None,
    ) -> None:
        super().__init__(message, phase="alpha")
        self.boundary_kind = boundary_kind  # "preview_mode" / "high_ambiguity" / "pareto_collapse"
        self.diagnostic = diagnostic


class SessionPersistenceError(LocalTradeoffError):
    """SQLite WAL write failed. Inherits S6 BriefStorage hardening
    pattern from C3a precedent."""

    def __init__(
        self,
        message:    str,
        *,
        operation:  Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.operation = operation  # "write" / "read" / "checkpoint"


class CorruptionDetectedError(SessionPersistenceError):
    """v0.6 B4 — raised at session load when the event-log checkpoint
    hash chain doesn't reconstruct the expected canonical_replay_signature
    of the loaded session. Indicates partial-write corruption or
    tampering.

    The session may still be loadable from the snapshot for forensic
    inspection, but should NOT be resumed as if intact. Caller decides
    recovery strategy.
    """

    def __init__(
        self,
        message:           str,
        *,
        session_id:        Optional[str] = None,
        expected_hash:     Optional[str] = None,
        observed_hash:     Optional[str] = None,
        last_known_good_sequence: Optional[int] = None,
    ) -> None:
        super().__init__(message, operation="load")
        self.session_id = session_id
        self.expected_hash = expected_hash
        self.observed_hash = observed_hash
        self.last_known_good_sequence = last_known_good_sequence


class SubsetRerunOrchestrationError(LocalTradeoffError):
    """The external subset-rerun orchestrator (for MEDIUM tweaks) failed.
    Session enters terminal 'abandoned_no_tweaks' state with explicit
    advisory listing the failed components."""

    def __init__(
        self,
        message:                str,
        *,
        failed_components:      Optional[tuple[str, ...]] = None,
        rerun_request_id:       Optional[str] = None,
    ) -> None:
        super().__init__(message, phase="epsilon")
        self.failed_components = failed_components or ()
        self.rerun_request_id = rerun_request_id


class TopologyInvarianceProbeError(LocalTradeoffError):
    """Phase β step 4.2 couldn't determine the
    TopologyInvarianceResult.prediction_basis confidently for a
    candidate tweak. SAFETY BIAS: the candidate is auto-classified
    HEAVY by default (removed from option set, MutationEnvelope
    generated for buffering).

    This subclasses LocalTradeoffError to flag the probe failure
    upstream of routing — but the SAFE outcome (auto-promote-to-HEAVY)
    is taken inside the catching code, not by raising. The exception
    form here is for unit-test reachability of the probe failure
    code path."""

    def __init__(
        self,
        message:           str,
        *,
        tweak_category:    Optional[str] = None,
        prediction_basis:  Optional[str] = None,
    ) -> None:
        super().__init__(message, phase="beta")
        self.tweak_category = tweak_category
        self.prediction_basis = prediction_basis


# ============================================================
# § 3 — PerTweakError subclasses (spec § 4.2)
# ============================================================

class TweakGenerationError(PerTweakError):
    """Can't generate a candidate for a ProblemReport check.
    E.g., a check is about cross-floor circulation but cross-floor
    tweaks are out-of-scope in v1.0 → the tweak isn't generated;
    the check is preserved in ProblemReport, NOT a hard error."""

    def __init__(
        self,
        message:                  str,
        *,
        problem_check_id:         Optional[str] = None,
        tweak_category_attempted: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.problem_check_id = problem_check_id
        self.tweak_category_attempted = tweak_category_attempted


class ImpactComputationError(PerTweakError):
    """Phase γ couldn't compute cost / space / comfort impact for a
    tweak. E.g., RateProvider lookup failed for a finish_upgrade
    material."""

    def __init__(
        self,
        message:     str,
        *,
        impact_dim:  Optional[str] = None,  # "cost" / "space" / "comfort"
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.impact_dim = impact_dim


class ConstraintViolationError(PerTweakError):
    """Applying this tweak would violate a hard constraint (NBC
    minimum room area, structural feasibility, etc.). The tweak is
    REMOVED from the option set BEFORE surfacing to the user.

    Spec § 4.2: this is a per-tweak filter, NOT a hard error stopping
    the session."""

    def __init__(
        self,
        message:         str,
        *,
        constraint:      Optional[str] = None,
        violated_value:  Optional[object] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.constraint = constraint
        self.violated_value = violated_value


class RecommendationFlagAmbiguityError(PerTweakError):
    """Phase γ can't unambiguously classify a tweak as
    suggested/optional/alternative."""


class DownstreamImpactSetMissingError(PerTweakError):
    """v0.2 (spec § 2.4.1): a MEDIUM tweak's
    SubsetRerunRequest.downstream_impact_set is empty. Hard error
    per the contract — empty impact set means we couldn't compute
    what to rerun, which means we can't safely apply."""


class CompatibilityAssertionFailedError(PerTweakError):
    """v0.2 (R15, spec § 7.3): Phase ε apply step found a
    CompatibilityAssertion.result == 'conflicts' against an
    already-applied tweak. STRICT halts the apply; WARN surfaces the
    conflict to the user with the 3-option resolution."""

    def __init__(
        self,
        message:                  str,
        *,
        conflicting_tweak_id:     Optional[str] = None,
        assertion_kind:           Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.conflicting_tweak_id = conflicting_tweak_id
        self.assertion_kind = assertion_kind


# ============================================================
# § 4 — Public surface
# ============================================================

__all__ = [
    # Bases
    "C3bError", "LocalTradeoffError", "PerTweakError",
    # Local subclasses
    "UpstreamSchemaDriftError",
    "C3bConfigurationError",
    "ApplicabilityBoundaryError",
    "SessionPersistenceError",
    "CorruptionDetectedError",
    "SubsetRerunOrchestrationError",
    "TopologyInvarianceProbeError",
    # Per-tweak subclasses
    "TweakGenerationError",
    "ImpactComputationError",
    "ConstraintViolationError",
    "RecommendationFlagAmbiguityError",
    "DownstreamImpactSetMissingError",
    "CompatibilityAssertionFailedError",
]
