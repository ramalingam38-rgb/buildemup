"""
BuildemUp† — Component 3a Session 5: preflight summary builder.

Per locked S5 SPEC v1.0 (formerly DRAFT v0.2 — locked after critique
round 1 incorporated patches P1–P4).

Public API:
    build_preflight_summary(cases) -> PreflightSummary

Pure function. Reads the initial tuple of detected ExtremeCases and
produces the non-blocking summary screen shown BEFORE the first EC
modal. Per parent spec § 4.7 and v0.2.1 critique #2 + #4: sets correct
expectation that multiple constraints exist and they interact; surfaces
an early "wrong plot" hint when severe-tier conditions present.

v1.0 includes critique-round-1 patches:
  - P2 (Drawback 6): early plot hint inlines specific triggering reasons
  - P3 (Drawback 5): summary_message distinguishes hard blockers from
    trade-offs when critical cases are present

Design references:
  - parent C3a spec § 4.7 (Preflight summary)
  - parent C3a spec § 3.1 (PreflightSummary dataclass)
  - locked S5 spec § 3.2, § 4 Q1 + Q7 + Q8 + Q9 + Q11, § 5.3
  - critique round 1 drawbacks 5 (P3), 6 (P2), 8 (contract), 9 (B-025)

†= placeholder name marker.
"""
from __future__ import annotations

from typing import Optional

from buildemup.domain.extreme_case import (
    ExtremeCase,
    ExtremeCaseCategory,
    ExtremeCaseId,
    PreflightSummary,
    ResolutionProbability,
)


# ─────────────────────────────────────────────────────────────────────
# Early plot hint classifiers (§4 Q1, with detector contracts per P4)
# ─────────────────────────────────────────────────────────────────────

def _is_severe_envelope_shortfall(c: ExtremeCase) -> bool:
    """EC-006: practical envelope below buildable threshold.

    DETECTOR CONTRACT (asserted by tests in test_c03a_session5_detector_contract.py
    per spec P4): S2's _detect_ec006 only fires when the envelope is below
    the buildable threshold. Mere presence of an EC-006 case in the input
    tuple = severe envelope. If S2's logic ever changes, the contract test
    fails loudly rather than S5 producing wrong output.
    """
    return c.case_id == ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE


def _is_low_resolution_approval(c: ExtremeCase) -> bool:
    """EC-010 with LOW probability of resolution (e.g., HT line, water
    course). Indicates the plot itself is the problem, not the design.

    Reads c.resolution_probability directly — no contract dependency.
    """
    return (
        c.case_id == ExtremeCaseId.EC_010_APPROVAL_BLOCKER
        and c.resolution_probability == ResolutionProbability.LOW
    )


def _is_narrow_plot_width(c: ExtremeCase) -> bool:
    """EC-002 — only fires in the severe (narrow) tier.

    DETECTOR CONTRACT (asserted by tests in test_c03a_session5_detector_contract.py
    per spec P4): S2's _detect_ec002 returns None for both physical-tier
    (HARD_FAIL upstream) and comfortable-tier briefs. Only the severe
    tier produces an ExtremeCase. Mere presence = severe narrow-width.

    NB: spec field-name was _is_physical_tier_width in parent C3a spec
    § 4.7; renamed here to match the actual semantics. Backlog B-015
    tracks the parent-spec wording fix.
    """
    return c.case_id == ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT


# ─────────────────────────────────────────────────────────────────────
# Severity classification (§4 Q11 — supports P3)
# ─────────────────────────────────────────────────────────────────────

def classify_case_severity(c: ExtremeCase) -> str:
    """Returns "critical" or "moderate".

    Critical (likely unresolvable; plot may be wrong):
      - EC-006 PRACTICAL_ENVELOPE_BELOW_BUILDABLE (always severe)
      - EC-002 PLOT_WIDTH_INSUFFICIENT (only fires in severe tier)
      - EC-010 APPROVAL_BLOCKER with resolution_probability == LOW

    Moderate (resolvable through trade-offs):
      - All other ECs

    This mirrors the early_plot_hint trigger conditions intentionally —
    if the plot itself is the problem, the case is critical; otherwise
    it's a workable trade-off.

    Backlog B-020 tracks moving severity into a structured field on
    PreflightSummary (S1 dataclass change). Until then, severity is
    derived at runtime here and woven into summary_message via P3.
    """
    if c.case_id == ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE:
        return "critical"
    if c.case_id == ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT:
        return "critical"
    if (
        c.case_id == ExtremeCaseId.EC_010_APPROVAL_BLOCKER
        and c.resolution_probability == ResolutionProbability.LOW
    ):
        return "critical"
    return "moderate"


# ─────────────────────────────────────────────────────────────────────
# Category formatting helpers (§4 Q7 + Q8)
# ─────────────────────────────────────────────────────────────────────

def _unique_categories_preserving_order(
    cases: tuple[ExtremeCase, ...],
) -> tuple[ExtremeCaseCategory, ...]:
    """Deduplicate categories while preserving first-seen order.

    Per Q8: detector emission order is the user-visible order;
    "fixing one may affect the others" reads naturally when categories
    are listed in the order the user will encounter them.
    """
    seen: set = set()
    out: list = []
    for c in cases:
        if c.category not in seen:
            seen.add(c.category)
            out.append(c.category)
    return tuple(out)


def _format_category_list(
    categories: tuple[ExtremeCaseCategory, ...],
) -> str:
    """Render category enum tuple as 'spatial, legal, and budget' or
    'spatial and legal' or 'spatial' (Q7).

    Defensive on empty input — caller guarantees ≥1 category in practice
    (PreflightSummary.__post_init__ enforces total_blocker_count ≥ 1).
    """
    labels = [c.value.lower() for c in categories]
    if len(labels) == 0:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


# ─────────────────────────────────────────────────────────────────────
# P2: early plot hint with reasons (Drawback 6)
# ─────────────────────────────────────────────────────────────────────

# Module-level constant for the early plot hint suffix (post-critique-round-2
# D2 lightweight fix). Centralising the suffix here makes it editable without
# touching function logic; also prepares the pattern for B-023 (full
# message-key registry) when that work happens.
_EARLY_PLOT_HINT_SUFFIX = (
    "You may want to consider whether this plot is the right fit "
    "before working through these trade-offs. We'll show you the "
    "options anyway — your call."
)


# Reason strings — also extracted as module constants for the same reason.
_REASON_ENVELOPE = "the practical buildable envelope is below typical"
_REASON_APPROVAL = "an approval blocker has low probability of resolution"
_REASON_NARROW = "the plot is narrow for your stated bedroom count"


def _build_early_plot_hint(
    cases: tuple[ExtremeCase, ...],
) -> Optional[str]:
    """Build the early plot hint with specific triggering reasons inlined
    (P2 — addresses Drawback 6 from critique round 1).

    Returns None if no triggering condition is met. Otherwise returns a
    single sentence per parent spec § 4.7 wrapper, with the triggering
    reason(s) named inside.

    The wrapper text from parent spec § 4.7 is preserved verbatim. Only
    the leading "based on your plot's characteristics" phrase is replaced
    with the specific reason(s).

    Post-critique-round-2 D4 fix: single-pass scan over `cases` instead
    of three separate any() calls. Functionally equivalent but reads
    cleaner; also short-circuits each flag once True.
    """
    has_envelope = False
    has_approval = False
    has_narrow = False
    for c in cases:
        if not has_envelope and _is_severe_envelope_shortfall(c):
            has_envelope = True
        if not has_approval and _is_low_resolution_approval(c):
            has_approval = True
        if not has_narrow and _is_narrow_plot_width(c):
            has_narrow = True
        # Early exit if all three flags set
        if has_envelope and has_approval and has_narrow:
            break

    reasons: list[str] = []
    if has_envelope:
        reasons.append(_REASON_ENVELOPE)
    if has_approval:
        reasons.append(_REASON_APPROVAL)
    if has_narrow:
        reasons.append(_REASON_NARROW)

    if not reasons:
        return None

    # Join reasons: 1 → as-is; 2 → "X and Y"; 3 → "X, Y, and Z"
    if len(reasons) == 1:
        reason_text = reasons[0]
    elif len(reasons) == 2:
        reason_text = f"{reasons[0]} and {reasons[1]}"
    else:
        reason_text = f"{', '.join(reasons[:-1])}, and {reasons[-1]}"

    return f"Heads up: {reason_text}. {_EARLY_PLOT_HINT_SUFFIX}"


# ─────────────────────────────────────────────────────────────────────
# P3: severity-aware summary message (Drawback 5)
# ─────────────────────────────────────────────────────────────────────

def _build_severity_aware_message(
    *,
    total: int,
    categories: tuple[ExtremeCaseCategory, ...],
    critical_count: int,
) -> str:
    """Build summary_message with severity awareness (P3 — addresses
    Drawback 5 from critique round 1).

    Four cases:
      1. total == 1, critical_count == 1:
         "1 hard blocker that may not be resolvable" phrasing.
      2. total == 1, critical_count == 0:
         Verbatim parent spec singular phrasing.
      3. total > 1, critical_count == 0:
         Verbatim parent spec multi-blocker phrasing.
      4. total > 1, critical_count > 0:
         Parent spec phrasing + critical breakdown ("X are hard blockers
         that may not be resolvable; the others are trade-offs.").
    """
    if total == 1:
        if critical_count == 1:
            return (
                "We found 1 hard blocker affecting your plan. "
                "It may not be resolvable. Let's see what's possible."
            )
        return (
            "We found 1 constraint affecting your plan. "
            "Let's work through it."
        )

    category_names = _format_category_list(categories)
    base = (
        f"We found {total} constraints affecting your plan: "
        f"{category_names}."
    )

    if critical_count == 0:
        return f"{base} Fixing one may affect the others."

    # Multi-blocker with critical breakdown
    non_critical = total - critical_count
    if critical_count == 1:
        critical_phrase = "1 is a hard blocker that may not be resolvable"
    else:
        critical_phrase = (
            f"{critical_count} are hard blockers that may not be resolvable"
        )

    if non_critical == 1:
        others_phrase = "the other is a trade-off"
    elif non_critical == 0:
        # All cases are critical — no "others" clause
        return (
            f"{base} All {total} are hard blockers that may not be "
            f"resolvable. Fixing one may affect the others."
        )
    else:
        others_phrase = "the others are trade-offs"

    return (
        f"{base} {critical_phrase}; {others_phrase}. "
        f"Fixing one may affect the others."
    )


# ─────────────────────────────────────────────────────────────────────
# Public API (§3.2)
# ─────────────────────────────────────────────────────────────────────

def build_preflight_summary(
    cases: tuple[ExtremeCase, ...],
) -> PreflightSummary:
    """Build the non-blocking preflight screen summary shown before the
    first EC modal.

    Per parent spec § 4.7 algorithm + locked S5 spec patches P2 + P3:
      1. Compute total = len(cases). Caller guarantees total ≥ 1
         (PreflightSummary.__post_init__ enforces this).
      2. Compute unique_categories — deduped, first-seen order.
      3. Compute critical_count — cases for which classify_case_severity
         returns "critical".
      4. Build summary_message via _build_severity_aware_message (P3).
      5. Build early_plot_hint via _build_early_plot_hint (P2).
      6. Return PreflightSummary.

    Pure function — no side effects.

    Args:
        cases: detected ExtremeCases for this brief. Must be non-empty
            (PreflightSummary's __post_init__ enforces this).

    Returns:
        PreflightSummary with summary_message and (optional) early_plot_hint.

    Raises:
        ValueError — only via PreflightSummary.__post_init__ if
            len(cases) < 1.
    """
    total = len(cases)
    unique_categories = _unique_categories_preserving_order(cases)
    critical_count = sum(
        1 for c in cases if classify_case_severity(c) == "critical"
    )

    summary_message = _build_severity_aware_message(
        total=total,
        categories=unique_categories,
        critical_count=critical_count,
    )

    early_plot_hint = _build_early_plot_hint(cases)

    return PreflightSummary(
        total_blocker_count=total,
        blocker_categories=unique_categories,
        summary_message=summary_message,
        early_plot_hint=early_plot_hint,
    )


# B-027 P7 (post-code-critique-round-2): backward-compatibility wrapper
# for the previous private name. Emits DeprecationWarning when called so
# any caller still using the old name sees noisy feedback. The pure-alias
# form previously here was silent, which made the TODO removal harder to
# trigger. Wrapper form makes it loud.
#
# TODO: remove this entire block after S6 ships and we've confirmed no
# remaining callers. Track via grep or by removing and running full
# suite — if anything fails, ship the rename to that caller first.

import warnings as _warnings


def _classify_severity(c: ExtremeCase) -> str:
    """DEPRECATED. Use classify_case_severity instead.

    Kept temporarily during the B-027 transition. Will be removed after
    S6 ships.
    """
    _warnings.warn(
        "_classify_severity is deprecated; use classify_case_severity. "
        "Will be removed after S6 ships.",
        DeprecationWarning,
        stacklevel=2,
    )
    return classify_case_severity(c)
