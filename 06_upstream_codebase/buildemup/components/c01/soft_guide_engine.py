"""
BuildemUp† — Soft-Guide Engine (Component 1).

Per SPEC_v0.2 Section 6 (Drawback 6 fix):

Aggregates soft-guide messages from all sub-modules (setback, parking,
vastu, budget, phased construction, auto-staircase, etc.) and produces:

  soft_guidance:  ALL messages, in order received
  top_guidance:   top 3 prioritised by severity

Priority order (strict):
  1. STRONG_CONCERN
  2. CONCERN
  3. INFO

Within each severity, messages preserve insertion order (stable sort).

This module is a pure aggregator — it doesn't generate messages itself.
Each sub-module has its own generator; this one just sorts & extracts.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.domain.brief import (
    GuidanceMessage, GuidanceSeverity,
)


# Priority weight for sorting — lower number = higher priority
_SEVERITY_PRIORITY: dict[GuidanceSeverity, int] = {
    GuidanceSeverity.STRONG_CONCERN: 0,
    GuidanceSeverity.CONCERN: 1,
    GuidanceSeverity.INFO: 2,
}


def compute_top_guidance(
    all_messages: list[GuidanceMessage] | tuple[GuidanceMessage, ...],
    n: int = 3,
) -> tuple[GuidanceMessage, ...]:
    """Extract the top N messages for prominent display.

    Per SPEC_v0.2 Section 6.2:
    - STRONG_CONCERN messages come first (all of them, if > N)
    - Then CONCERN
    - Then INFO (only if fewer than N from above)
    - Within each severity, insertion order preserved (stable sort)

    Args:
        all_messages: all guidance messages to prioritise
        n: how many to return (default 3 per spec)

    Returns:
        Tuple of up to N messages, sorted by severity then insertion order.
    """
    # Python's sort is stable, so insertion order is preserved within
    # equal-priority groups.
    sorted_msgs = sorted(
        all_messages,
        key=lambda m: _SEVERITY_PRIORITY[m.severity],
    )
    return tuple(sorted_msgs[:n])


def merge_guidance_sources(
    *sources: list[GuidanceMessage] | tuple[GuidanceMessage, ...],
) -> tuple[GuidanceMessage, ...]:
    """Flatten multiple sources of guidance into one ordered tuple.

    Order between sources is positional — sources passed first appear
    first in the merged output. Within each source, order is preserved.

    Typical usage:
      merge_guidance_sources(
          setback_msgs,       # compliance issues first
          parking_msgs,       # structural feasibility next
          budget_msgs,        # financial
          phased_msgs,        # phased construction suggestion
          staircase_msgs,     # auto-staircase info
          vastu_msgs,         # cultural prefs last (usually INFO)
      )
    """
    merged: list[GuidanceMessage] = []
    for source in sources:
        if source:
            merged.extend(source)
    return tuple(merged)


def count_by_severity(
    messages: list[GuidanceMessage] | tuple[GuidanceMessage, ...],
) -> dict[GuidanceSeverity, int]:
    """Count messages per severity level. Useful for summary rendering."""
    counts = {s: 0 for s in GuidanceSeverity}
    for m in messages:
        counts[m.severity] += 1
    return counts


def has_strong_concerns(
    messages: list[GuidanceMessage] | tuple[GuidanceMessage, ...],
) -> bool:
    """True if any message is STRONG_CONCERN.

    Used by BriefCaptureEngine to set risk_level=HIGH.
    Note: risk_level is informational only — we never block. User can
    always override and proceed.
    """
    return any(
        m.severity == GuidanceSeverity.STRONG_CONCERN for m in messages
    )


def compute_risk_level(
    messages: list[GuidanceMessage] | tuple[GuidanceMessage, ...],
) -> str:
    """Compute a coarse LOW/MEDIUM/HIGH risk level from guidance.

    Per v0.9 Drawback #8 fix:
    - HIGH  = any STRONG_CONCERN present
    - MEDIUM = any CONCERN present (no STRONG)
    - LOW   = only INFO (or empty)

    Used instead of a boolean "ready" flag. The word "ready" was
    misleading — it suggested the system approved the plan, when it
    only meant downstream components wouldn't refuse the handshake.
    """
    counts = count_by_severity(messages)
    if counts.get(GuidanceSeverity.STRONG_CONCERN, 0) > 0:
        return "HIGH"
    if counts.get(GuidanceSeverity.CONCERN, 0) > 0:
        return "MEDIUM"
    return "LOW"


# ─────────────────────────────────────────────────────────────────────────
# v0.9.1 — Risk drivers + category grouping
# ─────────────────────────────────────────────────────────────────────────

# Map context-prefix → human-readable category for grouping (Drawback #9 v0.9.1).
# Context strings come from each sub-module that emits guidance:
#   setback_calculator → "setback_violation_*"
#   parking_feasibility → "parking_*"
#   vastu_filter → "vastu_*"
#   budget_bridge → "budget_*"
#   phased_construction → "phased_construction"
#   room_composer → "auto_staircase_added", "circulation_*"
_CATEGORY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("setback", "Compliance"),
    ("parking", "Parking"),
    ("vastu", "Vastu (cultural)"),
    ("budget", "Budget"),
    ("phased", "Budget"),               # phased construction is a budget topic
    ("auto_staircase", "Design"),
    ("circulation", "Design"),
    ("setbacks_compliant", "Compliance"),
)


def _category_for_context(context: str) -> str:
    """Map a guidance context string to a coarse category name.

    Returns "Other" if no prefix matches — defensive default.
    """
    if not context:
        return "Other"
    ctx_lower = context.lower()
    for prefix, category in _CATEGORY_PREFIXES:
        if ctx_lower.startswith(prefix):
            return category
    return "Other"


def group_guidance_by_category(
    messages: list[GuidanceMessage] | tuple[GuidanceMessage, ...],
) -> dict[str, tuple[GuidanceMessage, ...]]:
    """Group guidance messages by category for v0.9.1 drawback #9 fix.

    Returns dict: category_name → tuple of messages in that category.
    Preserves insertion order within each category. Empty categories
    are excluded from the dict.

    Display order (when iterated) is determined by the order categories
    first appear in messages — which matches the order the engine
    produces sub-module outputs (compliance first, then parking, etc.).
    """
    grouped: dict[str, list[GuidanceMessage]] = {}
    for m in messages:
        cat = _category_for_context(m.context)
        grouped.setdefault(cat, []).append(m)
    # Convert to tuple for immutability + matches our other return types
    return {cat: tuple(msgs) for cat, msgs in grouped.items()}


def compute_risk_drivers(
    messages: list[GuidanceMessage] | tuple[GuidanceMessage, ...],
    risk_level: str,
) -> tuple[str, ...]:
    """Explain WHY the risk_level is what it is (Drawback #8 v0.9.1 fix).

    Returns short, human-readable reasons that drove the risk level.
    Pulls from the strongest-severity messages present.

    For risk_level="HIGH": lists STRONG_CONCERN contexts
    For risk_level="MEDIUM": lists CONCERN contexts
    For risk_level="LOW": single line confirming no major issues
    """
    if risk_level == "LOW":
        return (
            "No critical or moderate concerns found",
        )

    if risk_level == "HIGH":
        target_severity = GuidanceSeverity.STRONG_CONCERN
        prefix = "Critical"
    else:  # MEDIUM
        target_severity = GuidanceSeverity.CONCERN
        prefix = "Concern"

    drivers: list[str] = []
    seen_contexts: set[str] = set()
    for m in messages:
        if m.severity != target_severity:
            continue
        # Use the message's first sentence as the driver (compact summary).
        # S54-003 (May 2026): split on ". " (period + space), NOT bare "."
        # — the bare-period split truncated at the first decimal point in
        # numbers (e.g., "Front setback 0.4572m..." became "Front setback 0").
        # Sentence terminators in the engine's text always have a trailing
        # space; decimals don't.
        text = m.text or ""
        first_sentence = text.split(". ")[0].strip()
        # If the message is a single sentence ending in a period, the split
        # returns the full text; strip trailing period for compact display.
        if first_sentence.endswith("."):
            first_sentence = first_sentence[:-1]
        if not first_sentence:
            first_sentence = m.context.replace("_", " ")
        # Dedupe: don't repeat the same context twice
        if m.context in seen_contexts:
            continue
        seen_contexts.add(m.context)
        # Keep drivers concise — first 100 chars
        if len(first_sentence) > 100:
            first_sentence = first_sentence[:97] + "..."
        drivers.append(f"{prefix}: {first_sentence}")

    if not drivers:
        # Defensive: if risk says HIGH but no STRONG_CONCERN found
        # (shouldn't happen — but if it does we say so honestly)
        return (f"{prefix.lower()}-level guidance present (specifics unavailable)",)
    return tuple(drivers)


# ─────────────────────────────────────────────────────────────────────────
# v0.9.2 — Action steps (Drawback #16: "what should you do now?")
# ─────────────────────────────────────────────────────────────────────────

def compute_action_steps(
    messages: list[GuidanceMessage] | tuple[GuidanceMessage, ...],
    risk_level: str,
) -> tuple[str, ...]:
    """Build a numbered action list for v0.9.2 Drawback #16.

    Returns 3-5 user-facing action steps based on risk level + the
    presence of specific issue categories (compliance, budget). Each
    string is one full action sentence; clients render them as a
    numbered list.

    The same logic is mirrored in explain()'s WHAT SHOULD YOU DO NOW?
    section so output is consistent across rendered + structured.
    """
    n_compliance_issues = sum(
        1 for m in messages
        if m.severity == GuidanceSeverity.STRONG_CONCERN
        and m.context.startswith("setback")
    )
    has_budget_concerns = any(
        "budget" in m.context.lower()
        and m.severity in (GuidanceSeverity.STRONG_CONCERN,
                           GuidanceSeverity.CONCERN)
        for m in messages
    )

    actions: list[str] = []
    if risk_level == "HIGH":
        if n_compliance_issues > 0:
            actions.append(
                "Fix compliance issues first — these block municipal "
                "approval. Check the SETBACKS section for which sides "
                "are violating and by how much."
            )
        actions.append(
            "Re-run this brief with adjusted inputs (revised setbacks, "
            "or different plot type if applicable)."
        )
        if has_budget_concerns:
            actions.append(
                "Validate your budget against the all-in estimate — "
                "the structural number alone is only ~40% of total."
            )
        actions.append(
            "When risk drops to LOW or MEDIUM, proceed to Component 2 "
            "(Feasibility) for plan-possibility check."
        )
        actions.append(
            "Show this output to a local architect for early-stage "
            "sanity check — do NOT use this as a construction document."
        )
    elif risk_level == "MEDIUM":
        actions.append(
            "Review the CONCERN items above — they don't block your "
            "design but indicate trade-offs to consider."
        )
        if has_budget_concerns:
            actions.append(
                "Validate your budget — keep a 20% contingency above "
                "the typical all-in number for the industry-typical "
                "15-30% overshoot."
            )
        actions.append(
            "Proceed to Component 2 (Feasibility) when ready — your "
            "brief is captured and can move forward."
        )
        actions.append(
            "Discuss the concern items with your architect early so "
            "the layout phase accounts for them."
        )
    else:  # LOW
        actions.append(
            "Your brief is captured cleanly. Proceed to Component 2 "
            "(Feasibility) for plan-possibility check."
        )
        actions.append(
            "Plan a 20% contingency above the typical all-in cost "
            "estimate — industry data shows 85%+ of projects overshoot."
        )
        actions.append(
            "Begin shortlisting architects familiar with your city's "
            "DCR rules so they can review the layout phase output."
        )
    return tuple(actions)
