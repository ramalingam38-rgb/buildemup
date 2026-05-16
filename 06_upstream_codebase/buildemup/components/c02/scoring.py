"""
Component 2 — Scoring contract (Drawback #1 from domain review).

Defines how feasibility scores get computed so they don't drift across
versions. Score is 0-100, computed from CheckResult contributions.

The contract:

  Baseline: 100 (all PASS).

  HARD_FAIL: caps overall score at 40 (dramatic visible drop).
             A user with even one HARD_FAIL sees a sub-40 score
             and immediately knows the design is blocked.

  SOFT_WARN: contributes a confidence-weighted penalty.
    HIGH confidence  → -10 per warning
    MEDIUM confidence → -7 per warning
    LOW confidence    → -5 per warning
  Rationale: a HIGH-confidence SOFT_WARN penalises more because we
  trust the data behind it. A LOW-confidence one is partly speculation
  so we discount the penalty.

  PASS: no penalty.
  NOT_APPLICABLE: no penalty.

  Floor: score never goes below 0.
  Ceiling-on-fail: with any HARD_FAIL, score is min(computed, 40).

The score_breakdown returned alongside the score lets the user audit
which check contributed which penalty. This is per Drawback #1 — fixes
the "why is this 72 not 85?" trust problem.
"""
from __future__ import annotations

from buildemup.domain.feasibility import (
    CheckResult, CheckSeverity, ConfidenceLevel,
)


# ─── Penalty constants ────────────────────────────────────────────────
# Tuned for: a typical brief with 18 checks, 2-3 SOFT_WARNs gives ~80
# score (still feasible feel); HARD_FAIL drops dramatically into the
# 30s/40s zone (clear "this is blocked" signal).

SOFT_WARN_PENALTY_BY_CONFIDENCE: dict[ConfidenceLevel, int] = {
    ConfidenceLevel.HIGH: -10,
    ConfidenceLevel.MEDIUM: -7,
    ConfidenceLevel.LOW: -5,
}

HARD_FAIL_SCORE_CAP = 40
"""When ANY HARD_FAIL is present, overall score is capped at this value."""

BASELINE_SCORE = 100


# ─── Public API ───────────────────────────────────────────────────────

def compute_score_contribution(check: CheckResult) -> int:
    """Compute this check's contribution to overall score.

    Returns a non-positive integer (penalty, or 0 for PASS/NA).
    HARD_FAIL contributions are NOT used by compute_overall_score
    directly — instead the HARD_FAIL_SCORE_CAP rule kicks in. But each
    HARD_FAIL still gets a contribution recorded in the breakdown so
    the user can see "this check failed and capped your score."
    """
    if check.severity == CheckSeverity.PASS:
        return 0
    if check.severity == CheckSeverity.NOT_APPLICABLE:
        return 0
    if check.severity == CheckSeverity.SOFT_WARN:
        return SOFT_WARN_PENALTY_BY_CONFIDENCE.get(
            check.confidence, -7  # default to MEDIUM if confidence weird
        )
    if check.severity == CheckSeverity.HARD_FAIL:
        # HARD_FAIL contributions are recorded as -60 (the gap from
        # baseline 100 to cap 40) for breakdown clarity. The actual
        # cap is enforced separately by compute_overall_score.
        return -(BASELINE_SCORE - HARD_FAIL_SCORE_CAP)
    # Defensive: unknown severity counts as no penalty
    return 0


def compute_overall_score(
    check_results: tuple[CheckResult, ...] | list[CheckResult],
) -> tuple[int, dict[str, int]]:
    """Compute the overall feasibility score and per-check breakdown.

    Returns (score, breakdown):
      score: int in [0, 100]
      breakdown: {check_id: contribution_int} — non-positive ints

    Algorithm:
      1. Sum SOFT_WARN penalties weighted by confidence.
      2. If ANY HARD_FAIL exists, cap final score at 40.
      3. Floor at 0.

    Note: PASS and NOT_APPLICABLE checks are still recorded in the
    breakdown with contribution=0 so the breakdown is comprehensive.
    """
    breakdown: dict[str, int] = {}
    soft_warn_total = 0
    has_hard_fail = False

    for check in check_results:
        contribution = compute_score_contribution(check)
        breakdown[check.check_id] = contribution

        if check.severity == CheckSeverity.HARD_FAIL:
            has_hard_fail = True
        elif check.severity == CheckSeverity.SOFT_WARN:
            soft_warn_total += contribution  # negative

    # Apply penalties to baseline
    score = BASELINE_SCORE + soft_warn_total

    # Hard-fail cap: if any HARD_FAIL, score cannot exceed 40
    if has_hard_fail:
        score = min(score, HARD_FAIL_SCORE_CAP)

    # Floor at 0
    score = max(0, score)

    return score, breakdown


def explain_score(score: int, breakdown: dict[str, int]) -> str:
    """Human-readable explanation of how the score was computed.

    Used by explain() to render 'why is this 72 not 85?' transparency.
    """
    lines: list[str] = [
        f"Overall score: {score}/100",
        f"  Starting baseline: {BASELINE_SCORE}",
    ]
    # Group contributions by sign
    penalties = {k: v for k, v in breakdown.items() if v < 0}
    if not penalties:
        lines.append("  No penalties applied — all checks passed.")
    else:
        lines.append("  Penalties applied:")
        for check_id, contribution in sorted(
            penalties.items(), key=lambda x: x[1]  # most-negative first
        ):
            lines.append(f"    • {check_id}: {contribution:+d}")
    if score == HARD_FAIL_SCORE_CAP and any(
        v == -(BASELINE_SCORE - HARD_FAIL_SCORE_CAP)
        for v in breakdown.values()
    ):
        lines.append(
            f"  Note: HARD_FAIL present — score capped at "
            f"{HARD_FAIL_SCORE_CAP}."
        )
    return "\n".join(lines)
