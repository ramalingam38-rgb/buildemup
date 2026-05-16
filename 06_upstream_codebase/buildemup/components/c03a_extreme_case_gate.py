"""Component 3a Session 6 — Extreme Case Gate orchestrator.

Per locked S6 SPEC v1.0 + parent C3a spec v0.2.1a § 4.1, § 4.2, § 4.3,
§ 4.4, § 4.5, § 4.8, § 6, § 9.5.

This module exposes a single class — `ExtremeCaseGate` — that wires
together S1 (domain types), S2 (detector + option_generator), S4 (apply
+ error_formatter) and S5 (counterfactual + preflight) into a single
multi-turn user-facing flow.

Three pure methods over an immutable GateState:
  * start(session_id, brief, feasibility_input) → initial GateState
  * apply_user_decision(state, case_id, chosen_option_id, ...) → next
    GateState
  * apply_user_abort(state) → terminal GateState

Strict constraints (§ 2.3):
  * Pure given the injected c2_runner. No I/O, no clock, no random,
    no global state.
  * Returns a new GateState from every method.
  * S6 reads ResolutionOption.is_different_plot_option (added by B-027)
    instead of string-matching option_id / description.
  * user_acknowledged_at is caller-supplied (P5).
  * feasibility_input is sticky on GateState and re-passed to every
    c2_runner call (P4).
  * failed_option_ids_for_current_case (frozenset) is enforced at the
    validation layer — backend never trusts UI discipline (P3).
  * Banner output is typed events (P1) — UI composes copy.
"""
from __future__ import annotations

import dataclasses
from types import MappingProxyType
from typing import Callable, Mapping, Optional

from buildemup.components.c02.feasibility_input import FeasibilityInput
from buildemup.components.c03a.brief_change_apply import apply_brief_changes
from buildemup.components.c03a.counterfactual import build_counterfactual
from buildemup.components.c03a.detector import ExtremeCaseDetector
from buildemup.components.c03a.error_formatter import (
    format_validation_error_for_user,
)
from buildemup.components.c03a.gate_state import (
    DifferentPlotPromotionEvent,
    GateState,
    GateTerminationReason,
    TransitionBannerEvent,
)
from buildemup.components.c03a.gate_termination import (
    MAX_ITERATIONS,
    PER_CASE_LIMIT,
    determine_termination,
)
from buildemup.components.c03a.option_generator import OptionGenerator
from buildemup.components.c03a.preflight import (
    build_preflight_summary,
    classify_case_severity,
)
from buildemup.domain.brief import Brief
from buildemup.domain.extreme_case import (
    BriefChangeIntegrityError,
    BriefMode,
    ExtremeCase,
    ExtremeCaseCategory,
    ExtremeCaseId,
    ExtremeDecision,
    ExtremeDecisionLog,
    PreviewModeAcknowledgment,
    ResolutionOption,
    ResolvedBrief,
)
from buildemup.domain.feasibility import DesignGapAnalysis


# ─────────────────────────────────────────────────────────────────────
# Module-level constants
# ─────────────────────────────────────────────────────────────────────

# Priority order for surfacing cases (parent spec § 4.2):
# LEGAL → SITE → APPROVAL → SPATIAL → BUDGET. Stable sort keeps the
# detection-order tie-breaker among same-category cases.
_PRIORITY_ORDER: dict[ExtremeCaseCategory, int] = {
    ExtremeCaseCategory.LEGAL:    0,
    ExtremeCaseCategory.SITE:     1,
    ExtremeCaseCategory.APPROVAL: 2,
    ExtremeCaseCategory.SPATIAL:  3,
    ExtremeCaseCategory.BUDGET:   4,
}


# Mapping from EC ID → relaxed constraint name surfaced in PREVIEW
# Mode's ResolvedBrief.relaxed_constraints. ECs not in this map cannot
# be relaxed by the layout pipeline; the UI computes the non-relaxable
# subset via diff against unresolved_blockers (Q9 / C2 — backlog B-029
# tracks the structured-field promotion).
_EC_TO_RELAXED_CONSTRAINT: dict[ExtremeCaseId, str] = {
    ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE:
        "AREA_VS_ENVELOPE",
    ExtremeCaseId.EC_004_FAR_EXCEEDED:
        "FAR",
    ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED:
        "GROUND_COVERAGE",
    ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE:
        "PRACTICAL_ENVELOPE_MIN",
    ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED:
        "STILT_MANDATE",
    ExtremeCaseId.EC_010_APPROVAL_BLOCKER:
        "APPROVAL_BLOCKERS",
}


# Abort-reason strings for ExtremeDecisionLog.abort_reason (parent
# spec § 5 + Q11). Kept as a constants block so they're discoverable
# in one place.
_ABORT_REASON_USER             = "USER_ABORTED"
_ABORT_REASON_MAX_ITERATIONS   = "MAX_ITERATIONS_REACHED"
_ABORT_REASON_PER_CASE_LIMIT   = "PER_CASE_LIMIT_REACHED"
_ABORT_REASON_CBA              = "AWAITING_CBA_VERIFICATION"
_ABORT_REASON_PREVIEW          = "USER_CHOSE_PREVIEW_MODE"


# Empty read-only mapping reused at start() — saves an allocation on
# the no-blockers / first-iteration paths and keeps the immutability
# guarantee uniform.
_EMPTY_COUNTS: Mapping[str, int] = MappingProxyType({})


def _freeze_counts(d: dict[str, int]) -> Mapping[str, int]:
    """Wrap a per-case-counts dict in a MappingProxyType so the GateState's
    frozen-dataclass guarantee extends to its mapping members.

    Defensive copy (post-D-066-round-2 #2/#10): we copy `d` into a fresh
    dict before wrapping, so the proxy never shares storage with any
    caller-held reference. This makes the helper self-contained — no
    caller-discipline requirement to discard their reference.
    """
    return MappingProxyType(dict(d))


# ─────────────────────────────────────────────────────────────────────
# Pure helpers (§ 5.4 – § 5.7)
# ─────────────────────────────────────────────────────────────────────

def _sort_cases_by_priority(
    cases: tuple[ExtremeCase, ...],
) -> tuple[ExtremeCase, ...]:
    """Sort by category priority; preserve detection order on ties.

    Python's `sorted` is stable, so cases with the same category land
    in their original detection order — which is what the parent spec
    § 4.2 mandates as the tie-break rule.
    """
    return tuple(
        sorted(cases, key=lambda c: _PRIORITY_ORDER[c.category])
    )


def _promote_different_plot_in_case(case: ExtremeCase) -> ExtremeCase:
    """Mark any is_different_plot_option=True option as recommended.

    Returns a new ExtremeCase with options updated; original untouched.
    Per Q4 / P2, identification uses the explicit B-027 flag rather
    than string-matching option_id or description.

    If the option is already recommended, no-op (avoids spurious
    re-construction). The recommendation_reason is preserved or, if
    absent, defaulted to a short fixed string — ResolutionOption's
    __post_init__ requires recommendation_reason when recommended=True.
    """
    new_options: list[ResolutionOption] = []
    changed = False
    for opt in case.options:
        if opt.is_different_plot_option and not opt.recommended:
            new_options.append(
                dataclasses.replace(
                    opt,
                    recommended=True,
                    recommendation_reason=(
                        opt.recommendation_reason
                        or "different plot promoted by gate logic"
                    ),
                )
            )
            changed = True
        else:
            new_options.append(opt)

    if not changed:
        return case
    return dataclasses.replace(case, options=tuple(new_options))


def _check_different_plot_trigger(
    cases: tuple[ExtremeCase, ...],
    *,
    iteration_count: int,
) -> Optional[str]:
    """Return the trigger reason if "different plot" promotion should
    fire, else None. (§ 5.5 + parent spec § 4.2.)

    Conditions:
      A. EC-002 AND EC-006 both present (any iteration).
      B. ≥2 hard blockers AND iteration_count ≥ 2. Hard blocker =
         classify_case_severity(case) == "critical".

    Public severity API is used per v0.3 S-2 (was private
    _classify_severity in v0.2; B-027 P4 promoted it).
    """
    case_ids = {c.case_id for c in cases}
    if (
        ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT in case_ids
        and ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE in case_ids
    ):
        return "EC002_AND_EC006_COFIRE"

    if iteration_count >= 2:
        critical_count = sum(
            1 for c in cases if classify_case_severity(c) == "critical"
        )
        if critical_count >= 2:
            return "TWO_PLUS_HARD_BLOCKERS_ITER2_PLUS"

    return None


def _maybe_transition_banner(
    *,
    current_case: ExtremeCase,
    previous_resolved_case: ExtremeCase,
    previous_decision: ExtremeDecision,
    iteration: int,
) -> Optional[TransitionBannerEvent]:
    """Build a TransitionBannerEvent if the parent spec § 4.4 conditions
    are met, else None. (§ 5.4.)

    Fires only when:
      - iteration ∈ {2, 3}
      - previous_resolved_case.case_id != current_case.case_id

    Description is passed through in FULL — UI truncates per its display
    rules (P1 subsumes v0.1 D9 truncation).
    """
    if iteration not in (2, 3):
        return None
    if previous_resolved_case.case_id == current_case.case_id:
        return None
    return TransitionBannerEvent(
        previous_case_id=previous_resolved_case.case_id,
        new_case_id=current_case.case_id,
        previous_chosen_option_id=previous_decision.chosen_option_id,
        previous_chosen_option_description=(
            previous_decision.chosen_option_description
        ),
        iteration=iteration,
    )


def _generate_real_options(
    cases: tuple[ExtremeCase, ...],
    brief: Brief,
    gap_analysis: DesignGapAnalysis,
) -> tuple[ExtremeCase, ...]:
    """Replace S2's placeholder options on each case with S3's real
    options.

    S2's detector returns ExtremeCases with placeholder options to
    satisfy ExtremeCase.__post_init__'s ≥2 invariant. Before any sort
    or surfacing logic runs, S6 must wire OptionGenerator to produce
    real per-EC options. This step is implicit in the S6 spec (every
    helper assumes case.options is real) but explicit in parent
    spec § 4.1 (option list with full content surfaces to the user).

    co_fired_case_ids is computed from the full case set so per-EC
    builders can promote cross-EC strategies (e.g., EC-002↔EC-006
    "different plot" mutual promotion).
    """
    if not cases:
        return cases
    co_fired_case_ids = tuple(c.case_id for c in cases)
    rebuilt: list[ExtremeCase] = []
    for case in cases:
        real_options = OptionGenerator.generate_options(
            case, brief, gap_analysis, co_fired_case_ids,
        )
        rebuilt.append(
            dataclasses.replace(case, options=real_options)
        )
    return tuple(rebuilt)


# ─────────────────────────────────────────────────────────────────────
# ResolvedBrief construction helpers
# ─────────────────────────────────────────────────────────────────────

def _decisions_started_at(
    decisions: tuple[ExtremeDecision, ...],
) -> str:
    """Derive the session start timestamp from the first decision.

    S6 has zero time-related side effects (P5 — no _iso_now, no clock).
    ExtremeDecisionLog requires a started_at string field. We derive it
    from the first decision's caller-supplied user_acknowledged_at;
    when no decisions exist (instant SUCCESS at start()) we use empty
    string. ExtremeDecisionLog.__post_init__ does not enforce non-empty.
    """
    if decisions:
        return decisions[0].user_acknowledged_at
    return ""


def _decisions_completed_at(
    decisions: tuple[ExtremeDecision, ...],
    *,
    aborted: bool,
) -> Optional[str]:
    """Derive the session completion timestamp.

    Aborted sessions: completed_at = None per ExtremeDecisionLog
    docstring ("None if aborted mid-flow"). Clean-finish sessions
    (SUCCESS, PREVIEW_MODE): completed_at = last decision's
    user_acknowledged_at; "" if no decisions exist.
    """
    if aborted:
        return None
    if decisions:
        return decisions[-1].user_acknowledged_at
    return ""


def _build_success_resolved_brief(
    *,
    original_brief: Brief,
    revised_brief: Brief,
    gap_analysis: DesignGapAnalysis,
    decisions: tuple[ExtremeDecision, ...],
    iteration_count: int,
    preflight: Optional["object"] = None,
) -> ResolvedBrief:
    """Build the ResolvedBrief for a SUCCESS termination."""
    log = ExtremeDecisionLog(
        started_at=_decisions_started_at(decisions),
        completed_at=_decisions_completed_at(decisions, aborted=False),
        decisions=decisions,
        iterations_used=iteration_count,
        aborted=False,
        abort_reason=None,
    )
    counterfactuals = tuple(
        build_counterfactual(d) for d in decisions
    )
    return ResolvedBrief(
        original_brief=original_brief,
        revised_brief=revised_brief,
        decision_log=log,
        final_feasibility=gap_analysis,
        mode=BriefMode.BUILDABLE,
        is_layout_ready=True,
        counterfactuals=counterfactuals,
        unresolved_blockers=(),
        relaxed_constraints=(),
        preflight_summary=preflight,
        preview_mode_acknowledgment=None,
    )


def _build_preview_resolved_brief(
    *,
    original_brief: Brief,
    revised_brief: Brief,
    gap_analysis: DesignGapAnalysis,
    decisions: tuple[ExtremeDecision, ...],
    iteration_count: int,
    unresolved: tuple[ExtremeCase, ...],
    preview_acknowledgment: PreviewModeAcknowledgment,
    preflight: Optional["object"] = None,
) -> ResolvedBrief:
    """Build the ResolvedBrief for a PREVIEW_MODE termination.

    Per Q14 / C1: gap_analysis carried forward is the LAST BUILDABLE
    state (state.current_gap_analysis at the moment the user picks
    Preview Mode), NOT a re-run on the preview configuration. Preview
    Mode is by definition non-buildable; re-running C2 against an
    unbuildable brief surfaces the same blockers we already detected,
    adding no information.
    """
    # decision_log on PREVIEW_MODE: aborted=True with the special
    # USER_CHOSE_PREVIEW_MODE reason that ResolvedBrief's invariant
    # explicitly tolerates alongside is_layout_ready=True.
    log = ExtremeDecisionLog(
        started_at=_decisions_started_at(decisions),
        completed_at=_decisions_completed_at(decisions, aborted=True),
        decisions=decisions,
        iterations_used=iteration_count,
        aborted=True,
        abort_reason=_ABORT_REASON_PREVIEW,
    )
    counterfactuals = tuple(
        build_counterfactual(d) for d in decisions
    )
    relaxed = tuple(
        _EC_TO_RELAXED_CONSTRAINT[c.case_id]
        for c in unresolved
        if c.case_id in _EC_TO_RELAXED_CONSTRAINT
    )
    return ResolvedBrief(
        original_brief=original_brief,
        revised_brief=revised_brief,
        decision_log=log,
        final_feasibility=gap_analysis,
        mode=BriefMode.PREVIEW,
        is_layout_ready=True,
        counterfactuals=counterfactuals,
        unresolved_blockers=unresolved,
        relaxed_constraints=relaxed,
        preflight_summary=preflight,
        preview_mode_acknowledgment=preview_acknowledgment,
    )


def _build_abort_resolved_brief(
    *,
    original_brief: Brief,
    revised_brief: Brief,
    gap_analysis: DesignGapAnalysis,
    decisions: tuple[ExtremeDecision, ...],
    iteration_count: int,
    abort_reason: str,
    preflight: Optional["object"] = None,
) -> ResolvedBrief:
    """Build the ResolvedBrief for a non-PREVIEW abort termination.

    Per Q11: mode=BUILDABLE (placeholder), is_layout_ready=False,
    counterfactuals=(), unresolved_blockers=() and relaxed_constraints=().
    The "remaining cases at abort time" are preserved on GateState.
    remaining_cases — the orchestrator state, not the ResolvedBrief —
    because S1's ResolvedBrief invariant requires unresolved_blockers
    to be empty when mode == BUILDABLE.

    The abort signal is carried on decision_log.aborted +
    decision_log.abort_reason.
    """
    log = ExtremeDecisionLog(
        started_at=_decisions_started_at(decisions),
        completed_at=_decisions_completed_at(decisions, aborted=True),
        decisions=decisions,
        iterations_used=iteration_count,
        aborted=True,
        abort_reason=abort_reason,
    )
    return ResolvedBrief(
        original_brief=original_brief,
        revised_brief=revised_brief,
        decision_log=log,
        final_feasibility=gap_analysis,
        mode=BriefMode.BUILDABLE,
        is_layout_ready=False,
        counterfactuals=(),
        unresolved_blockers=(),
        relaxed_constraints=(),
        preflight_summary=preflight,
        preview_mode_acknowledgment=None,
    )


# ─────────────────────────────────────────────────────────────────────
# Orchestrator class (§ 3.5)
# ─────────────────────────────────────────────────────────────────────

class ExtremeCaseGate:
    """Orchestrator for the C3a extreme-case resolution flow.

    Stateless given c2_runner. All session state lives in GateState
    objects passed in and out of methods. S7 (API layer) is responsible
    for persisting GateState between HTTP calls.

    Constants exposed at class level for discoverability:
      MAX_ITERATIONS = 7    # parent spec § 4.3
      PER_CASE_LIMIT = 3    # parent spec § 4.3
    """

    MAX_ITERATIONS: int = MAX_ITERATIONS
    PER_CASE_LIMIT: int = PER_CASE_LIMIT

    def __init__(
        self,
        c2_runner: Callable[
            [Brief, Optional[FeasibilityInput]], DesignGapAnalysis
        ],
    ):
        self._c2_runner = c2_runner

    # ───── start ─────────────────────────────────────────────────

    def start(
        self,
        *,
        session_id: str,
        brief: Brief,
        feasibility_input: Optional[FeasibilityInput] = None,
    ) -> GateState:
        """Steps [1]–[4] of parent spec § 4.1.

        Runs C2 + detection. If no cases, returns terminal SUCCESS.
        Otherwise builds preflight, sorts cases, applies any "different
        plot" promotion, and returns the initial in-progress GateState.

        P4: feasibility_input is stored on the returned GateState so
        every subsequent c2_runner call uses the same input.
        """
        # [1] Run C2
        gap_analysis = self._c2_runner(brief, feasibility_input)

        # [2] Detect ECs (placeholder options)
        cases_raw = ExtremeCaseDetector.detect(gap_analysis, brief)

        # [3] Empty cases → terminal SUCCESS
        if not cases_raw:
            resolved = _build_success_resolved_brief(
                original_brief=brief,
                revised_brief=brief,
                gap_analysis=gap_analysis,
                decisions=(),
                iteration_count=0,
                preflight=None,
            )
            return GateState(
                session_id=session_id,
                original_brief=brief,
                current_brief=brief,
                feasibility_input=feasibility_input,
                current_gap_analysis=gap_analysis,
                remaining_cases=(),
                decisions_so_far=(),
                iteration_count=0,
                per_case_iteration_counts=_EMPTY_COUNTS,
                preflight=None,
                transition_banner=None,
                meta_banner=None,
                different_plot_promoted=False,
                last_error_message=None,
                last_error_option_id=None,
                failed_option_ids_for_current_case=frozenset(),
                is_done=True,
                termination_reason=GateTerminationReason.SUCCESS,
                final_resolved_brief=resolved,
            )

        # Replace placeholder options with real S3 options
        cases_with_options = _generate_real_options(
            cases_raw, brief, gap_analysis,
        )

        # [3.5] Build preflight
        preflight = build_preflight_summary(cases_with_options)

        # [4] Sort + promote different plot
        sorted_cases = _sort_cases_by_priority(cases_with_options)
        promotion_trigger = _check_different_plot_trigger(
            sorted_cases, iteration_count=0,
        )

        if promotion_trigger is not None:
            sorted_cases = tuple(
                _promote_different_plot_in_case(c) for c in sorted_cases
            )
            meta_banner: Optional[DifferentPlotPromotionEvent] = (
                DifferentPlotPromotionEvent(
                    trigger=promotion_trigger,
                    triggered_at_iteration=0,
                )
            )
        else:
            meta_banner = None

        return GateState(
            session_id=session_id,
            original_brief=brief,
            current_brief=brief,
            feasibility_input=feasibility_input,
            current_gap_analysis=gap_analysis,
            remaining_cases=sorted_cases,
            decisions_so_far=(),
            iteration_count=0,
            per_case_iteration_counts=_EMPTY_COUNTS,
            preflight=preflight,
            transition_banner=None,        # iter 0: no transition banner
            meta_banner=meta_banner,
            different_plot_promoted=(promotion_trigger is not None),
            last_error_message=None,
            last_error_option_id=None,
            failed_option_ids_for_current_case=frozenset(),
            is_done=False,
            termination_reason=None,
            final_resolved_brief=None,
        )

    # ───── apply_user_decision ────────────────────────────────────

    def apply_user_decision(
        self,
        *,
        state: GateState,
        case_id: ExtremeCaseId,
        chosen_option_id: str,
        user_acknowledged_at: str,
        preview_mode_acknowledgment: Optional[PreviewModeAcknowledgment] = None,
    ) -> GateState:
        """Steps [5]–[12] of parent spec § 4.1.

        Validates inputs (P3: rejects previously-failed option_ids).
        Handles four branches:
          A. option.is_preview_mode → terminal PREVIEW_MODE state
          B. option.requires_action == "EMAIL_CBA_CHECKLIST" → terminal
             CBA_VERIFICATION_PAUSED state
          C. apply_brief_changes raises BriefChangeIntegrityError →
             return state with last_error_* set + chosen_option_id
             added to failed_option_ids_for_current_case
          D. Apply succeeds → re-run C2 with state.feasibility_input
             (P4), re-detect, check termination, sort + promote, set
             transition banner if applicable, return next GateState.

        Pure given c2_runner.
        """
        # ─── Validation ──────────────────────────────────────────
        if state.is_done:
            raise ValueError(
                "apply_user_decision called on terminal state "
                f"(termination_reason={state.termination_reason})"
            )
        if not state.remaining_cases:
            raise ValueError(
                "apply_user_decision called with no remaining cases"
            )

        current_case = state.remaining_cases[0]
        if current_case.case_id != case_id:
            raise ValueError(
                f"case_id mismatch: got {case_id!r}, current is "
                f"{current_case.case_id!r}"
            )

        chosen_option = next(
            (
                o for o in current_case.options
                if o.option_id == chosen_option_id
            ),
            None,
        )
        if chosen_option is None:
            raise ValueError(
                f"option {chosen_option_id!r} not in current case's options "
                f"(case_id={case_id.value}); "
                f"available={[o.option_id for o in current_case.options]!r}"
            )

        # P3: reject previously-failed options
        if chosen_option_id in state.failed_option_ids_for_current_case:
            raise ValueError(
                f"option {chosen_option_id!r} previously failed for this "
                f"case (case_id={case_id.value}). Pick a different option."
            )

        # P5: caller-supplied timestamp must be non-empty
        if not user_acknowledged_at:
            raise ValueError(
                "user_acknowledged_at is required (caller-supplied ISO "
                "timestamp; backend has no clock side effects)"
            )

        # ─── Branch A: Preview Mode ──────────────────────────────
        if chosen_option.is_preview_mode:
            if preview_mode_acknowledgment is None:
                raise ValueError(
                    "Preview Mode option requires preview_mode_acknowledgment "
                    "(audit invariant per parent spec § 4.5)"
                )
            return self._terminate_preview_mode(
                state=state,
                current_case=current_case,
                chosen_option=chosen_option,
                preview_acknowledgment=preview_mode_acknowledgment,
                user_acknowledged_at=user_acknowledged_at,
            )

        # ─── Branch B: CBA verification ──────────────────────────
        if chosen_option.requires_action == "EMAIL_CBA_CHECKLIST":
            return self._terminate_cba_verification(
                state=state,
                current_case=current_case,
                chosen_option=chosen_option,
                user_acknowledged_at=user_acknowledged_at,
            )

        # ─── Branch C: try apply BriefChange ─────────────────────
        try:
            revised_brief = apply_brief_changes(
                state.current_brief,
                chosen_option.requires_brief_change,
            )
        except BriefChangeIntegrityError as exc:
            return self._handle_apply_error(state, chosen_option, exc)

        # ─── Branch D: apply succeeded — advance ─────────────────
        # v0.3 S-3: iteration_index is 0-BASED. The first decision in a
        # session has iteration_index=0; the second has 1; etc. We pass
        # state.iteration_count BEFORE incrementing it. After this
        # decision is recorded, the gate's iteration_count advances to
        # iteration_count + 1.
        decision = ExtremeDecision(
            case_id=case_id,
            chosen_option_id=chosen_option_id,
            chosen_option_description=chosen_option.description,
            presented_options=current_case.options,
            user_acknowledged_at=user_acknowledged_at,
            iteration_index=state.iteration_count,
        )
        new_decisions = state.decisions_so_far + (decision,)

        # P4: feasibility_input passed through every C2 call
        new_gap_analysis = self._c2_runner(
            revised_brief, state.feasibility_input,
        )
        new_cases_raw = ExtremeCaseDetector.detect(
            new_gap_analysis, revised_brief,
        )

        new_iter = state.iteration_count + 1
        case_id_str = case_id.value
        new_per_case = dict(state.per_case_iteration_counts)
        new_per_case[case_id_str] = new_per_case.get(case_id_str, 0) + 1

        # Termination check (C3 — explicit precedence in helper)
        term = determine_termination(
            new_cases=new_cases_raw,
            iteration_count=new_iter,
            per_case_iteration_counts=_freeze_counts(new_per_case),
            previous_case_id=case_id,
        )

        if term == GateTerminationReason.SUCCESS:
            return self._terminate_success(
                state=state,
                revised_brief=revised_brief,
                new_gap_analysis=new_gap_analysis,
                new_decisions=new_decisions,
                new_iter=new_iter,
                new_per_case=new_per_case,
            )
        if term in (
            GateTerminationReason.MAX_ITERATIONS_REACHED,
            GateTerminationReason.PER_CASE_LIMIT_REACHED,
        ):
            # Cases haven't been option-rebuilt yet; for an abort path
            # the orchestrator surfaces the terminal state and the
            # remaining cases are exposed on GateState.remaining_cases
            # (with placeholder options is acceptable on terminal states
            # — UI doesn't render options on a terminal screen). For
            # callers that want UI-ready cases we still build options.
            new_cases_with_options = _generate_real_options(
                new_cases_raw, revised_brief, new_gap_analysis,
            )
            return self._terminate_abort(
                state=state,
                revised_brief=revised_brief,
                new_gap_analysis=new_gap_analysis,
                new_decisions=new_decisions,
                new_iter=new_iter,
                new_per_case=new_per_case,
                term=term,
                remaining_cases=new_cases_with_options,
            )

        # ─── Continue: replace placeholder options + sort + promote ──
        new_cases_with_options = _generate_real_options(
            new_cases_raw, revised_brief, new_gap_analysis,
        )
        sorted_new_cases = _sort_cases_by_priority(new_cases_with_options)

        # Different-plot promotion (P6 — sticky, applied to ALL cases)
        new_promotion_trigger = _check_different_plot_trigger(
            sorted_new_cases, iteration_count=new_iter,
        )
        promoted = state.different_plot_promoted or (
            new_promotion_trigger is not None
        )
        if promoted:
            sorted_new_cases = tuple(
                _promote_different_plot_in_case(c)
                for c in sorted_new_cases
            )

        # Meta banner: keep existing (sticky) or set new
        if state.meta_banner is not None:
            meta_banner: Optional[DifferentPlotPromotionEvent] = (
                state.meta_banner
            )
        elif new_promotion_trigger is not None:
            meta_banner = DifferentPlotPromotionEvent(
                trigger=new_promotion_trigger,
                triggered_at_iteration=new_iter,
            )
        else:
            meta_banner = None

        # Transition banner (typed event per P1)
        transition_banner = _maybe_transition_banner(
            current_case=sorted_new_cases[0],
            previous_resolved_case=current_case,
            previous_decision=decision,
            iteration=new_iter,
        )

        return GateState(
            session_id=state.session_id,
            original_brief=state.original_brief,
            current_brief=revised_brief,
            feasibility_input=state.feasibility_input,
            current_gap_analysis=new_gap_analysis,
            remaining_cases=sorted_new_cases,
            decisions_so_far=new_decisions,
            iteration_count=new_iter,
            per_case_iteration_counts=_freeze_counts(new_per_case),
            preflight=None,                          # only set on iter 0
            transition_banner=transition_banner,
            meta_banner=meta_banner,
            different_plot_promoted=promoted,
            last_error_message=None,                 # cleared on success
            last_error_option_id=None,
            failed_option_ids_for_current_case=frozenset(),
            is_done=False,
            termination_reason=None,
            final_resolved_brief=None,
        )

    # ───── apply_user_abort ───────────────────────────────────────

    def apply_user_abort(self, state: GateState) -> GateState:
        """Terminal: USER_ABORTED. Brief saved as-is; no C2 re-run.

        Builds an aborted ResolvedBrief from the current state. Calling
        this on an already-terminal state is a programmer error and
        raises ValueError.
        """
        if state.is_done:
            raise ValueError(
                "apply_user_abort called on terminal state "
                f"(termination_reason={state.termination_reason})"
            )
        resolved = _build_abort_resolved_brief(
            original_brief=state.original_brief,
            revised_brief=state.current_brief,
            gap_analysis=state.current_gap_analysis,
            decisions=state.decisions_so_far,
            iteration_count=state.iteration_count,
            abort_reason=_ABORT_REASON_USER,
            preflight=state.preflight,
        )
        return dataclasses.replace(
            state,
            is_done=True,
            termination_reason=GateTerminationReason.USER_ABORTED,
            final_resolved_brief=resolved,
        )

    # ───── private branches ─────────────────────────────────────

    def _handle_apply_error(
        self,
        state: GateState,
        chosen_option: ResolutionOption,
        exc: BriefChangeIntegrityError,
    ) -> GateState:
        """Branch C: apply_brief_changes raised. Surface formatted
        error + add chosen_option_id to failed_option_ids_for_current_case
        (P3). Backend never trusts UI to grey out the failed option.
        """
        formatted = format_validation_error_for_user(exc, chosen_option)
        new_failed = state.failed_option_ids_for_current_case | {
            chosen_option.option_id,
        }
        return dataclasses.replace(
            state,
            last_error_message=formatted,
            last_error_option_id=chosen_option.option_id,
            failed_option_ids_for_current_case=new_failed,
        )

    def _terminate_preview_mode(
        self,
        *,
        state: GateState,
        current_case: ExtremeCase,
        chosen_option: ResolutionOption,
        preview_acknowledgment: PreviewModeAcknowledgment,
        user_acknowledged_at: str,
    ) -> GateState:
        """Terminate with mode=PREVIEW.

        IMPORTANT (Q14 / C1): gap_analysis on the returned ResolvedBrief
        reflects the LAST BUILDABLE STATE of the brief, NOT the preview
        configuration. Preview Mode is by definition non-buildable; we
        do NOT re-run C2 against the preview state. This is intentional:
        re-running C2 against an unbuildable brief surfaces the same
        blockers we already detected, adding no information.

        v0.3 S-3: iteration_index is 0-based; we pass state.iteration_count
        before any increment (Preview Mode does not increment the counter
        because no C2 re-run takes place).
        """
        decision = ExtremeDecision(
            case_id=current_case.case_id,
            chosen_option_id=chosen_option.option_id,
            chosen_option_description=chosen_option.description,
            presented_options=current_case.options,
            user_acknowledged_at=user_acknowledged_at,
            iteration_index=state.iteration_count,
        )
        new_decisions = state.decisions_so_far + (decision,)

        # All remaining cases (including current) are unresolved
        unresolved = state.remaining_cases

        resolved = _build_preview_resolved_brief(
            original_brief=state.original_brief,
            revised_brief=state.current_brief,
            gap_analysis=state.current_gap_analysis,    # last buildable
            decisions=new_decisions,
            iteration_count=state.iteration_count,
            unresolved=unresolved,
            preview_acknowledgment=preview_acknowledgment,
            preflight=state.preflight,
        )

        return dataclasses.replace(
            state,
            decisions_so_far=new_decisions,
            is_done=True,
            termination_reason=GateTerminationReason.PREVIEW_MODE,
            final_resolved_brief=resolved,
        )

    def _terminate_cba_verification(
        self,
        *,
        state: GateState,
        current_case: ExtremeCase,
        chosen_option: ResolutionOption,
        user_acknowledged_at: str,
    ) -> GateState:
        """Terminate with mode=CBA_VERIFICATION_PAUSED.

        Records the decision but does NOT run C2; the brief is paused
        as a draft and S7 (API layer) handles email send + 24h fallback
        per parent spec § 5.4 / § 5.5.
        """
        decision = ExtremeDecision(
            case_id=current_case.case_id,
            chosen_option_id=chosen_option.option_id,
            chosen_option_description=chosen_option.description,
            presented_options=current_case.options,
            user_acknowledged_at=user_acknowledged_at,
            iteration_index=state.iteration_count,
        )
        new_decisions = state.decisions_so_far + (decision,)

        resolved = _build_abort_resolved_brief(
            original_brief=state.original_brief,
            revised_brief=state.current_brief,
            gap_analysis=state.current_gap_analysis,
            decisions=new_decisions,
            iteration_count=state.iteration_count,
            abort_reason=_ABORT_REASON_CBA,
            preflight=state.preflight,
        )

        return dataclasses.replace(
            state,
            decisions_so_far=new_decisions,
            is_done=True,
            termination_reason=GateTerminationReason.CBA_VERIFICATION_PAUSED,
            final_resolved_brief=resolved,
        )

    def _terminate_success(
        self,
        *,
        state: GateState,
        revised_brief: Brief,
        new_gap_analysis: DesignGapAnalysis,
        new_decisions: tuple[ExtremeDecision, ...],
        new_iter: int,
        new_per_case: dict[str, int],
    ) -> GateState:
        """Terminate with mode=BUILDABLE, is_layout_ready=True, no
        unresolved blockers."""
        resolved = _build_success_resolved_brief(
            original_brief=state.original_brief,
            revised_brief=revised_brief,
            gap_analysis=new_gap_analysis,
            decisions=new_decisions,
            iteration_count=new_iter,
            preflight=state.preflight,
        )
        return GateState(
            session_id=state.session_id,
            original_brief=state.original_brief,
            current_brief=revised_brief,
            feasibility_input=state.feasibility_input,
            current_gap_analysis=new_gap_analysis,
            remaining_cases=(),
            decisions_so_far=new_decisions,
            iteration_count=new_iter,
            per_case_iteration_counts=_freeze_counts(new_per_case),
            preflight=None,
            transition_banner=None,
            meta_banner=state.meta_banner,
            different_plot_promoted=state.different_plot_promoted,
            last_error_message=None,
            last_error_option_id=None,
            failed_option_ids_for_current_case=frozenset(),
            is_done=True,
            termination_reason=GateTerminationReason.SUCCESS,
            final_resolved_brief=resolved,
        )

    def _terminate_abort(
        self,
        *,
        state: GateState,
        revised_brief: Brief,
        new_gap_analysis: DesignGapAnalysis,
        new_decisions: tuple[ExtremeDecision, ...],
        new_iter: int,
        new_per_case: dict[str, int],
        term: GateTerminationReason,
        remaining_cases: tuple[ExtremeCase, ...],
    ) -> GateState:
        """Terminate with MAX_ITERATIONS_REACHED or PER_CASE_LIMIT_REACHED.

        ResolvedBrief is BUILDABLE (placeholder per Q11) with
        is_layout_ready=False; the abort signal is on
        decision_log.aborted/abort_reason. Remaining cases are kept on
        GateState.remaining_cases for UI display (so the abort screen
        can show what couldn't be reconciled).
        """
        if term == GateTerminationReason.MAX_ITERATIONS_REACHED:
            abort_reason = _ABORT_REASON_MAX_ITERATIONS
        elif term == GateTerminationReason.PER_CASE_LIMIT_REACHED:
            abort_reason = _ABORT_REASON_PER_CASE_LIMIT
        else:
            # Defensive — not reachable through current call sites.
            raise ValueError(
                f"_terminate_abort called with unsupported term={term!r}"
            )

        resolved = _build_abort_resolved_brief(
            original_brief=state.original_brief,
            revised_brief=revised_brief,
            gap_analysis=new_gap_analysis,
            decisions=new_decisions,
            iteration_count=new_iter,
            abort_reason=abort_reason,
            preflight=state.preflight,
        )

        return GateState(
            session_id=state.session_id,
            original_brief=state.original_brief,
            current_brief=revised_brief,
            feasibility_input=state.feasibility_input,
            current_gap_analysis=new_gap_analysis,
            remaining_cases=remaining_cases,
            decisions_so_far=new_decisions,
            iteration_count=new_iter,
            per_case_iteration_counts=_freeze_counts(new_per_case),
            preflight=None,
            transition_banner=None,
            meta_banner=state.meta_banner,
            different_plot_promoted=state.different_plot_promoted,
            last_error_message=None,
            last_error_option_id=None,
            failed_option_ids_for_current_case=frozenset(),
            is_done=True,
            termination_reason=term,
            final_resolved_brief=resolved,
        )


__all__ = [
    "ExtremeCaseGate",
]
