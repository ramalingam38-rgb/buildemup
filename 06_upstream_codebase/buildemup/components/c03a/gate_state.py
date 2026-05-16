"""Component 3a Session 6 — gate state + typed banner events.

Per locked S6 SPEC v1.0 §3.1–§3.4. This module contains:

  * GateState — frozen immutable session snapshot returned by every
    ExtremeCaseGate method. S7 (API layer) persists it between HTTP
    calls; S6 itself is stateless beyond its injected c2_runner.
  * GateTerminationReason — enum of the 6 terminal conditions.
  * TransitionBannerEvent — typed event for case-transition UI banners
    (P1: replaces v0.1 free-form strings; UI renders to copy).
  * DifferentPlotPromotionEvent — typed event for the meta-banner that
    fires when "different plot" promotion triggers.

Strict layering: this module imports ONLY from the domain layer, never
from the orchestrator. The orchestrator imports these symbols, not the
other way around.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Mapping, Optional

from buildemup.components.c02.feasibility_input import FeasibilityInput
from buildemup.domain.brief import Brief
from buildemup.domain.extreme_case import (
    ExtremeCase,
    ExtremeCaseId,
    ExtremeDecision,
    PreflightSummary,
    ResolvedBrief,
)
from buildemup.domain.feasibility import DesignGapAnalysis


# ─────────────────────────────────────────────────────────────────────
# Termination reasons (§ 3.2)
# ─────────────────────────────────────────────────────────────────────

class GateTerminationReason(Enum):
    """The 6 terminal conditions for an ExtremeCaseGate session.

    SUCCESS, MAX_ITERATIONS_REACHED and PER_CASE_LIMIT_REACHED come
    out of `determine_termination()` (see gate_termination.py). The
    other three are set directly by orchestrator branches:
      - PREVIEW_MODE → user picked the Preview Mode option
      - USER_ABORTED → user clicked Save and exit
      - CBA_VERIFICATION_PAUSED → option.requires_action == "EMAIL_CBA_CHECKLIST"
    """
    SUCCESS = "SUCCESS"
    PREVIEW_MODE = "PREVIEW_MODE"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    PER_CASE_LIMIT_REACHED = "PER_CASE_LIMIT_REACHED"
    USER_ABORTED = "USER_ABORTED"
    CBA_VERIFICATION_PAUSED = "CBA_VERIFICATION_PAUSED"


# ─────────────────────────────────────────────────────────────────────
# Typed banner events (§ 3.3, § 3.4)  — P1 from v0.2 critique round 1
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TransitionBannerEvent:
    """Typed event for case-transition UI banners.

    Replaces v0.1's free-form string. S7 (API/UI) renders this to copy
    per its locale / formatting rules. S6 produces only structured
    data — no UI string composition.

    Fires only when (per parent spec § 4.4):
      - iteration ∈ {2, 3}
      - previous_resolved_case.case_id != current_case.case_id

    Fields:
      previous_case_id                   — case the user just resolved
      new_case_id                        — case now being surfaced
      previous_chosen_option_id          — option_id user picked
      previous_chosen_option_description — FULL description; UI truncates
                                           to its display constraints (P1
                                           subsumes v0.1 D9 truncation)
      iteration                          — 2 or 3
    """
    previous_case_id: ExtremeCaseId
    new_case_id: ExtremeCaseId
    previous_chosen_option_id: str
    previous_chosen_option_description: str
    iteration: int

    def to_dict(self) -> dict:
        return {
            "previous_case_id": self.previous_case_id.value,
            "new_case_id": self.new_case_id.value,
            "previous_chosen_option_id": self.previous_chosen_option_id,
            "previous_chosen_option_description":
                self.previous_chosen_option_description,
            "iteration": self.iteration,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "TransitionBannerEvent":
        return cls(
            previous_case_id=ExtremeCaseId(payload["previous_case_id"]),
            new_case_id=ExtremeCaseId(payload["new_case_id"]),
            previous_chosen_option_id=payload["previous_chosen_option_id"],
            previous_chosen_option_description=(
                payload["previous_chosen_option_description"]
            ),
            iteration=payload["iteration"],
        )


@dataclass(frozen=True)
class DifferentPlotPromotionEvent:
    """Typed event for the "different plot" meta-banner (parent spec § 4.2).

    Fires when one of two trigger conditions is met:
      - EC002_AND_EC006_COFIRE: EC-002 + EC-006 both present this iteration
      - TWO_PLUS_HARD_BLOCKERS_ITER2_PLUS: ≥2 critical-severity cases at
        iteration_count ≥ 2

    Once attached to GateState, sticky across all subsequent cases per
    Q13 / P6 (Interpretation A): every subsequent case surfaced gets its
    different-plot option marked recommended.
    """
    trigger: Literal[
        "EC002_AND_EC006_COFIRE",
        "TWO_PLUS_HARD_BLOCKERS_ITER2_PLUS",
    ]
    triggered_at_iteration: int

    def to_dict(self) -> dict:
        return {
            "trigger": self.trigger,
            "triggered_at_iteration": self.triggered_at_iteration,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "DifferentPlotPromotionEvent":
        return cls(
            trigger=payload["trigger"],
            triggered_at_iteration=payload["triggered_at_iteration"],
        )


# ─────────────────────────────────────────────────────────────────────
# GateState (§ 3.1)
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GateState:
    """Immutable snapshot of the orchestrator's session state.

    Returned by every ExtremeCaseGate method. S7 (API layer) persists
    this between HTTP calls; S6 itself is stateless beyond its injected
    c2_runner.

    Invariants (§ 6.2):
      - Frozen dataclass; never mutated. Every step returns a new instance.
      - decisions_so_far never decreases in length.
      - iteration_count never decreases.
      - per_case_iteration_counts[case_id] never decreases.
      - failed_option_ids_for_current_case can only grow within a case
        (set semantics — duplicates impossible by construction); resets
        to frozenset() when case advances. Bounded by
        len(current_case.options).
      - different_plot_promoted is sticky — once True, never goes False.
      - meta_banner is sticky — once attached, persists through subsequent
        states.
      - feasibility_input is sticky — set in start(), never changed.
      - is_done True iff termination_reason set iff final_resolved_brief set.
    """
    # Session identity
    session_id: str

    # Brief evolution
    original_brief: Brief
    current_brief: Brief

    # Feasibility input — P4: sticky, carried through every C2 call
    feasibility_input: Optional[FeasibilityInput]

    # C2 latest output
    current_gap_analysis: DesignGapAnalysis

    # Cases & iteration tracking
    remaining_cases: tuple[ExtremeCase, ...]
    decisions_so_far: tuple[ExtremeDecision, ...]
    iteration_count: int
    # per_case_iteration_counts is read-only (Mapping, not dict). The
    # orchestrator wraps the underlying dict with types.MappingProxyType
    # before construction so the frozen-dataclass immutability guarantee
    # extends to its mutable members. (D-066 critique item #2.)
    per_case_iteration_counts: Mapping[str, int]

    # UI affordances — typed events, not strings (P1)
    preflight: Optional[PreflightSummary]
    transition_banner: Optional[TransitionBannerEvent]
    meta_banner: Optional[DifferentPlotPromotionEvent]
    different_plot_promoted: bool

    # Error path — P3: failed options tracked structurally; v0.3 S-1 frozenset
    last_error_message: Optional[str]
    last_error_option_id: Optional[str]
    failed_option_ids_for_current_case: frozenset[str]

    # Termination
    is_done: bool
    termination_reason: Optional[GateTerminationReason]
    final_resolved_brief: Optional[ResolvedBrief]

    # ─── S7a serialization (per S7a SPEC v1.0 LOCKED § 9) ────────────
    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict.

        Per S7a SPEC § 4.1 + § 9.3:
          - frozenset → sorted list
          - tuple → list (handled inside each nested to_dict)
          - Mapping (incl. MappingProxyType) → plain dict
          - Enum → .value
          - None passes through

        Round-trip invariant (P14 with sort_keys=True at JSON layer):
          self.to_dict() == GateState.from_dict(self.to_dict()).to_dict()
        """
        return {
            "_schema_version": "1",
            "session_id": self.session_id,
            "original_brief": self.original_brief.to_dict(),
            "current_brief": self.current_brief.to_dict(),
            "feasibility_input": (
                self.feasibility_input.to_dict()
                if self.feasibility_input is not None else None
            ),
            "current_gap_analysis":
                self.current_gap_analysis.to_dict(),
            "remaining_cases": [
                c.to_dict() for c in self.remaining_cases
            ],
            "decisions_so_far": [
                d.to_dict() for d in self.decisions_so_far
            ],
            "iteration_count": self.iteration_count,
            "per_case_iteration_counts":
                dict(self.per_case_iteration_counts),
            "preflight": (
                self.preflight.to_dict()
                if self.preflight is not None else None
            ),
            "transition_banner": (
                self.transition_banner.to_dict()
                if self.transition_banner is not None else None
            ),
            "meta_banner": (
                self.meta_banner.to_dict()
                if self.meta_banner is not None else None
            ),
            "different_plot_promoted": self.different_plot_promoted,
            "last_error_message": self.last_error_message,
            "last_error_option_id": self.last_error_option_id,
            "failed_option_ids_for_current_case":
                sorted(self.failed_option_ids_for_current_case),
            "is_done": self.is_done,
            "termination_reason": (
                self.termination_reason.value
                if self.termination_reason is not None else None
            ),
            "final_resolved_brief": (
                self.final_resolved_brief.to_dict()
                if self.final_resolved_brief is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "GateState":
        """Reconstruct from JSON-safe dict.

        Per S7a SPEC § 4.3 (P8): _schema_version absent OR == "1" loads
        normally; explicit different value raises SchemaVersionError.
        """
        from types import MappingProxyType

        schema_version = payload.get("_schema_version", "1")
        if schema_version != "1":
            raise SchemaVersionError(
                f"unsupported schema version {schema_version!r} "
                f"(expected '1' or absent)"
            )

        # Lazy imports to avoid module-load circular issues; the domain
        # modules import from this one too.
        from buildemup.components.c02.feasibility_input import FeasibilityInput
        from buildemup.domain.brief import Brief
        from buildemup.domain.extreme_case import (
            ExtremeCase,
            ExtremeDecision,
            PreflightSummary,
            ResolvedBrief,
        )
        from buildemup.domain.feasibility import DesignGapAnalysis

        return cls(
            session_id=payload["session_id"],
            original_brief=Brief.from_dict(payload["original_brief"]),
            current_brief=Brief.from_dict(payload["current_brief"]),
            feasibility_input=(
                FeasibilityInput.from_dict(payload["feasibility_input"])
                if payload.get("feasibility_input") is not None else None
            ),
            current_gap_analysis=DesignGapAnalysis.from_dict(
                payload["current_gap_analysis"]
            ),
            remaining_cases=tuple(
                ExtremeCase.from_dict(c)
                for c in payload["remaining_cases"]
            ),
            decisions_so_far=tuple(
                ExtremeDecision.from_dict(d)
                for d in payload["decisions_so_far"]
            ),
            iteration_count=payload["iteration_count"],
            per_case_iteration_counts=MappingProxyType(
                dict(payload["per_case_iteration_counts"])
            ),
            preflight=(
                PreflightSummary.from_dict(payload["preflight"])
                if payload.get("preflight") is not None else None
            ),
            transition_banner=(
                TransitionBannerEvent.from_dict(payload["transition_banner"])
                if payload.get("transition_banner") is not None else None
            ),
            meta_banner=(
                DifferentPlotPromotionEvent.from_dict(payload["meta_banner"])
                if payload.get("meta_banner") is not None else None
            ),
            different_plot_promoted=payload["different_plot_promoted"],
            last_error_message=payload.get("last_error_message"),
            last_error_option_id=payload.get("last_error_option_id"),
            failed_option_ids_for_current_case=frozenset(
                payload["failed_option_ids_for_current_case"]
            ),
            is_done=payload["is_done"],
            termination_reason=(
                GateTerminationReason(payload["termination_reason"])
                if payload.get("termination_reason") is not None else None
            ),
            final_resolved_brief=(
                ResolvedBrief.from_dict(payload["final_resolved_brief"])
                if payload.get("final_resolved_brief") is not None else None
            ),
        )


# ─────────────────────────────────────────────────────────────────────
# Serialization exceptions (P8 — S7a SPEC § 4.3)
# ─────────────────────────────────────────────────────────────────────

class SchemaVersionError(ValueError):
    """Raised when GateState.from_dict sees an explicit unsupported
    _schema_version value.

    Absent _schema_version field is treated as "1" (legacy load).
    Only an explicit different value triggers this exception.
    """


__all__ = [
    "DifferentPlotPromotionEvent",
    "GateState",
    "GateTerminationReason",
    "SchemaVersionError",
    "TransitionBannerEvent",
]
