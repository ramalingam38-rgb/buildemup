"""Component 3a Session 6 — termination precedence helper.

Per locked S6 SPEC v1.0 § 3.6 + Q15 (C3 patch addressing critique D11).

This is a pure single-function module: `determine_termination` decides
whether SUCCESS, MAX_ITERATIONS_REACHED or PER_CASE_LIMIT_REACHED
should fire after a C2 re-run, with EXPLICIT precedence to remove
ambiguity when multiple conditions hold simultaneously.

PREVIEW_MODE / USER_ABORTED / CBA_VERIFICATION_PAUSED do NOT go through
this helper — they are set directly by the orchestrator's branch logic.
"""
from __future__ import annotations

from typing import Mapping, Optional

from buildemup.components.c03a.gate_state import GateTerminationReason
from buildemup.domain.extreme_case import ExtremeCase, ExtremeCaseId


# Constants pulled out so the helper module is self-contained and the
# numbers can be referenced without importing the orchestrator.
# These are the canonical values from parent spec § 4.3.
MAX_ITERATIONS = 7
PER_CASE_LIMIT = 3


def determine_termination(
    *,
    new_cases: tuple[ExtremeCase, ...],
    iteration_count: int,
    per_case_iteration_counts: Mapping[str, int],
    previous_case_id: Optional[ExtremeCaseId],
) -> Optional[GateTerminationReason]:
    """Decide which run-driven termination (if any) should fire after
    a C2 re-run + EC re-detection.

    EXPLICIT PRECEDENCE (C3 — addresses critique round 1 D11):

      1. SUCCESS                 (highest priority)
      2. MAX_ITERATIONS_REACHED
      3. PER_CASE_LIMIT_REACHED  (lowest priority)

    Conditions are checked in this exact order; first match wins.

    Rationale for precedence:
      - SUCCESS first: empty cases means we're done; iteration count
        and per-case count are irrelevant.
      - MAX_ITERATIONS before PER_CASE_LIMIT: if we hit iteration 7 with
        blockers AND the same case_id has been resolved 3 times, the
        iteration cap is the more user-meaningful message ("we tried
        7 times, can't reconcile") than the per-case message. Tie-break:
        present the more general failure first.

    Args:
      new_cases: ECs detected after the latest C2 run. Empty tuple
                 indicates SUCCESS.
      iteration_count: total iterations completed so far (post-increment).
      per_case_iteration_counts: dict[case_id_str, count] of how many
                 times each case_id has been resolved successfully.
      previous_case_id: the case_id the user JUST resolved. Used to look
                 up the per-case count for that case, since the per-case
                 limit fires on the case that keeps coming back.

    Returns:
      GateTerminationReason if a termination condition fires; None if
      the orchestrator should continue to the next iteration.

    PREVIEW_MODE / USER_ABORTED / CBA_VERIFICATION_PAUSED do NOT go
    through this helper — they are set directly by apply_user_decision /
    apply_user_abort.
    """
    # Precedence 1: SUCCESS — no cases left, regardless of counts
    if not new_cases:
        return GateTerminationReason.SUCCESS

    # Precedence 2: MAX_ITERATIONS_REACHED — hit the global cap
    if iteration_count >= MAX_ITERATIONS:
        return GateTerminationReason.MAX_ITERATIONS_REACHED

    # Precedence 3: PER_CASE_LIMIT_REACHED — same case_id has been
    # resolved PER_CASE_LIMIT times and is STILL in the remaining
    # set. We check the previous case (the one just resolved) since
    # that is the one whose recurrence the limit is meant to detect.
    # If the previous case is no longer in remaining_cases the user
    # successfully advanced past it; we only fire when it persists.
    if previous_case_id is not None:
        prev_count = per_case_iteration_counts.get(previous_case_id.value, 0)
        if prev_count >= PER_CASE_LIMIT:
            still_present = any(
                c.case_id == previous_case_id for c in new_cases
            )
            if still_present:
                return GateTerminationReason.PER_CASE_LIMIT_REACHED

    return None


__all__ = [
    "MAX_ITERATIONS",
    "PER_CASE_LIMIT",
    "determine_termination",
]
