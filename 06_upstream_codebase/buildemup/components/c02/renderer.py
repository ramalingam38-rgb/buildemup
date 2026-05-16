"""
Component 2 — Renderer (Session H).

Pure read-only functions that turn a DesignGapAnalysis into:
  - render_text_summary(analysis, brief) — ~25 lines, quick CLI/email view
  - render_text_full(analysis, brief) — ~100 lines, full report
  - render_json(analysis) — dict for API/frontend, all enums as strings

Design decisions (Session H):
  - Plain text, no ANSI colors (works in email, logs, files)
  - Lead with the answer in first 5 lines (mobile-friendly)
  - Doubts appendix at end of full text (avoid bloating mid-report)
  - JSON shape mirrors DesignGapAnalysis fields exactly, with enum
    .value strings for downstream parseability
  - All money rendered as "₹{N}L" (Indian format, lakhs)
  - Renderer is pure: same input → same output, no side effects

The renderer assumes the orchestrator produced a sensible
DesignGapAnalysis. Validation lives in the orchestrator + domain
__post_init__, not here.
"""
from __future__ import annotations
from dataclasses import is_dataclass, fields, asdict
from enum import Enum
from typing import Any

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    DesignGapAnalysis, FeasibilityReport, CheckResult,
    Gap, Unknown, ActionStep,
)


# ─── Internal helpers ─────────────────────────────────────────────────

def _line(char: str = "─", n: int = 64) -> str:
    """Return a horizontal rule of given char and length."""
    return char * n


def _format_money_lakhs(value: float | None) -> str:
    """Render a number as Indian rupee format (lakhs)."""
    if value is None:
        return "n/a"
    return f"₹{value:.2f}L"


# ─── Unit display helpers (added v0.10.1 — feet UI) ──────────────────
# Engine uses metres internally. Reports show feet first (Indian
# audience preference) with metres in brackets so users can also
# verify against authority documents (which are in metres).

_FT_PER_M = 3.28084
_SQFT_PER_SQM = 10.7639


def _fmt_ft(m: float) -> str:
    """Render a metre value as 'X.X ft (Y.Y m)' for display."""
    return f"{m * _FT_PER_M:.1f} ft ({m:.2f} m)"


def _fmt_area(sqm: float) -> str:
    """Render an area as 'X sqft (Y sqm)' for display."""
    return f"{sqm * _SQFT_PER_SQM:.0f} sqft ({sqm:.0f} sqm)"


def _summarize_check_count(report: FeasibilityReport) -> str:
    """One-line check count summary."""
    return (
        f"Pass: {len(report.passed_checks)}  "
        f"Soft: {len(report.soft_warnings)}  "
        f"Blocking: {len(report.blocking_issues)}  "
        f"N/A: {len(report.not_applicable_checks)}"
    )


def _format_severity_label(sev_value: str) -> str:
    """Convert 'hard_fail' → 'BLOCKING', 'soft_warn' → 'WARNING', etc."""
    mapping = {
        "hard_fail": "BLOCKING",
        "soft_warn": "WARNING",
        "pass": "OK",
        "not_applicable": "N/A",
    }
    return mapping.get(sev_value, sev_value.upper())


def _format_gap_label(severity_value: str) -> str:
    mapping = {
        "blocking_if_not_accepted": "DECISION NEEDED",
        "significant": "SIGNIFICANT",
        "marginal": "MINOR",
        "info_only": "INFO",
    }
    return mapping.get(severity_value, severity_value.upper())


# Drawback 11 fix (Session K): map domain CheckCategory to user-facing
# labels that distinguish legal risk from design quality risk.
# This addresses the reviewer's "Legal vs design not separated" concern
# without restructuring the entire renderer — issues stay grouped by
# severity (most actionable axis) but now carry an at-a-glance category tag.
_CATEGORY_USER_LABEL = {
    "compliance":  "LEGAL",       # NBC / DCR / municipal rules
    "usability":   "DESIGN",      # comfort, daily living quality
    "structural":  "STRUCTURAL",  # foundations, soil, water table
    "cost":        "COST",        # budget, RWH spend, cost adders
    "spatial":     "SPATIAL",     # envelope, FAR, floor stack
    "safety":      "SAFETY",      # fire access, electric clearance
}


def _format_check_category(check) -> str:
    """Return a short user-facing tag for a check's category."""
    cat_value = (
        check.category.value if hasattr(check.category, "value")
        else str(check.category)
    )
    return _CATEGORY_USER_LABEL.get(cat_value, cat_value.upper())


# ─── Text renderer: summary (short) ──────────────────────────────────

def render_text_summary(analysis: DesignGapAnalysis, brief: Brief) -> str:
    """Render a ~25-line summary for CLI / email / quick view.

    Sections:
      1. Plot info (1 line)
      2. Practical vs Code-Strict scores (4 lines)
      3. Top 3 critical issues (2-7 lines)
      4. Cost delta + decisions count (2 lines)
    """
    lines = []
    lines.append(_line("="))
    lines.append("BUILDEMUP FEASIBILITY REPORT — SUMMARY")
    lines.append(_line("="))
    lines.append("")

    # Plot info
    plot = brief.plot
    lines.append(
        f"Plot: {_fmt_ft(plot.width_m)} × {_fmt_ft(plot.depth_m)} "
        f"— {_fmt_area(plot.area_sqm)} in {plot.city.title()} "
        f"({len(brief.floors)}-floor build)"
    )
    lines.append("")

    # Both lane scores
    p = analysis.practical_report
    c = analysis.code_strict_report
    p_status = "FEASIBLE" if p.is_feasible else "NOT FEASIBLE"
    c_status = "FEASIBLE" if c.is_feasible else "NOT FEASIBLE"

    # Drawback 1 fix (Session K): when blockers exist, append count to the
    # score line so users can differentiate "40 (1 blocker)" from
    # "40 (3 blockers)" at a glance.
    p_status_full = (
        f"{p_status} ({len(p.blocking_issues)} blockers)"
        if p.blocking_issues else p_status
    )
    c_status_full = (
        f"{c_status} ({len(c.blocking_issues)} blockers)"
        if c.blocking_issues else c_status
    )

    lines.append(f"PRACTICAL:    {p.overall_score:>3}/100 — {p_status_full}")
    lines.append(f"              {_summarize_check_count(p)}")
    if p.blocking_issues:
        # Show first 3 blocker names compactly
        blocker_names = ", ".join(
            b.check_name for b in p.blocking_issues[:3]
        )
        suffix = f" + {len(p.blocking_issues) - 3} more" if len(p.blocking_issues) > 3 else ""
        lines.append(f"              Blockers: {blocker_names}{suffix}")

    lines.append(f"CODE-STRICT:  {c.overall_score:>3}/100 — {c_status_full}")
    lines.append(f"              {_summarize_check_count(c)}")
    if c.blocking_issues:
        blocker_names = ", ".join(
            b.check_name for b in c.blocking_issues[:3]
        )
        suffix = f" + {len(c.blocking_issues) - 3} more" if len(c.blocking_issues) > 3 else ""
        lines.append(f"              Blockers: {blocker_names}{suffix}")

    # Drawback 2 fix (Session K): if any soft warnings are downgraded
    # HARDs, surface this in the summary so users don't underreact.
    p_downgrades = sum(
        1 for r in p.soft_warnings if r.details.get("downgrade_applied")
    )
    if p_downgrades > 0:
        lines.append(
            f"              Note: {p_downgrades} warning(s) downgraded "
            f"from HARD — verify data to confirm severity"
        )
    lines.append("")

    # Top critical action items (from practical lane)
    if p.blocking_issues:
        lines.append("TOP BLOCKING ISSUES (Practical):")
        for issue in p.blocking_issues[:3]:
            lines.append(f"  • {issue.check_name}")
        if len(p.blocking_issues) > 3:
            lines.append(f"  ... and {len(p.blocking_issues) - 3} more")
        lines.append("")
    elif p.soft_warnings:
        lines.append("TOP CONCERNS (Practical):")
        for warn in p.soft_warnings[:3]:
            lines.append(f"  • {warn.check_name}")
        if len(p.soft_warnings) > 3:
            lines.append(f"  ... and {len(p.soft_warnings) - 3} more")
        lines.append("")
    else:
        lines.append("All Practical checks passing. Review Code-Strict gaps below.")
        lines.append("")

    # Cost delta + decisions
    if analysis.gaps:
        lines.append(
            f"Code-Strict adds {_format_money_lakhs(analysis.cost_delta_lakhs)} "
            f"(soil/water table verification, possible RWH)"
        )
    if analysis.user_decisions_required:
        lines.append(
            f"Decisions needed: {len(analysis.user_decisions_required)} "
            f"(see full report)"
        )

    lines.append("")
    lines.append(_line("="))
    return "\n".join(lines)


# ─── Text renderer: full report ──────────────────────────────────────

def render_text_full(
    analysis: DesignGapAnalysis,
    brief: Brief,
    include_doubts: bool = True,
) -> str:
    """Render the complete report (~80-120 lines depending on issue count).

    Sections:
      1. Header + plot info
      2. Both lane scores + status
      3. Practical lane details (blocking, soft, pass counts)
      4. Code-Strict lane details
      5. Gaps + user decisions
      6. Unknowns (verification recommendations)
      7. Action steps prioritized
      8. (Optional) FAQs / common doubts
      9. Footer with caveats
    """
    lines = []

    # ── 1. Header ─────────────────────────────────────────────────────
    lines.append(_line("="))
    lines.append("BUILDEMUP FEASIBILITY REPORT")
    lines.append(_line("="))
    lines.append("")

    plot = brief.plot
    lines.append(f"PLOT")
    lines.append(f"  Location:    {plot.city.title()}")
    lines.append(
        f"  Dimensions:  {_fmt_ft(plot.width_m)} × {_fmt_ft(plot.depth_m)}"
    )
    lines.append(f"  Area:        {_fmt_area(plot.area_sqm)}")
    lines.append(f"  Facing:      {plot.facing.value}")
    lines.append(f"  Plot type:   {plot.plot_type.value}")
    lines.append(f"  Road width:  {_fmt_ft(plot.road_width_m)}")
    lines.append("")

    lines.append(f"BUILD")
    lines.append(f"  Floors:      {len(brief.floors)} ({_describe_floors(brief)})")
    if brief.budget_range:
        lines.append(
            f"  Budget:      ₹{brief.budget_range.min_lakhs}L–"
            f"₹{brief.budget_range.max_lakhs}L"
        )
    lines.append("")

    # ── 2. Both lane scores ───────────────────────────────────────────
    p = analysis.practical_report
    c = analysis.code_strict_report

    lines.append(_line("─"))
    lines.append("OVERALL ASSESSMENT")
    lines.append(_line("─"))
    lines.append("")
    # Session L patch (failure #6 fix): explicit one-line clarifier so
    # users don't equate PRACTICAL with "legally approved" or CODE-STRICT
    # with "the only correct way".
    lines.append(
        "PRACTICAL = commonly built; some compromises may need approval"
    )
    lines.append(
        "workarounds.  CODE-STRICT = strict NBC + DCR compliance with no"
    )
    lines.append("trade-offs.")
    lines.append("")
    p_status = "FEASIBLE" if p.is_feasible else "NOT FEASIBLE"
    c_status = "FEASIBLE" if c.is_feasible else "NOT FEASIBLE"

    # Drawback 1 + 2 fix (Session K): show blocker count + downgrade
    # note inline so users at a glance know the severity profile.
    p_status_full = (
        f"{p_status} ({len(p.blocking_issues)} blockers)"
        if p.blocking_issues else p_status
    )
    c_status_full = (
        f"{c_status} ({len(c.blocking_issues)} blockers)"
        if c.blocking_issues else c_status
    )

    lines.append(f"PRACTICAL design (your stated preferences):")
    lines.append(f"  Score: {p.overall_score}/100 — {p_status_full}")
    lines.append(f"  {_summarize_check_count(p)}")

    p_downgrades = sum(
        1 for r in p.soft_warnings if r.details.get("downgrade_applied")
    )
    if p_downgrades > 0:
        lines.append(
            f"  Note: {p_downgrades} warning(s) downgraded from HARD — "
            f"verify the underlying data to confirm severity"
        )
    lines.append("")
    lines.append(f"CODE-STRICT design (full NBC + DCR compliance):")
    lines.append(f"  Score: {c.overall_score}/100 — {c_status_full}")
    lines.append(f"  {_summarize_check_count(c)}")
    lines.append("")

    # ── 3. Practical lane details ─────────────────────────────────────
    lines.append(_line("─"))
    lines.append(f"PRACTICAL LANE — DETAILS ({len(p.all_check_results)} checks)")
    lines.append(_line("─"))
    lines.extend(_render_lane_details(p))
    lines.append("")

    # ── 4. Code-Strict lane details ───────────────────────────────────
    lines.append(_line("─"))
    lines.append(f"CODE-STRICT LANE — DETAILS ({len(c.all_check_results)} checks)")
    lines.append(_line("─"))
    lines.extend(_render_lane_details(c))
    lines.append("")

    # ── 5. Gaps + decisions ───────────────────────────────────────────
    if analysis.gaps:
        lines.append(_line("─"))
        lines.append(f"GAPS BETWEEN PRACTICAL AND CODE-STRICT ({len(analysis.gaps)})")
        lines.append(_line("─"))
        lines.append("")
        for gap in analysis.gaps:
            lines.append(
                f"[{_format_gap_label(gap.severity.value)}] {gap.check_id}"
            )
            lines.extend(_wrap_indented(
                gap.impact_description, indent="  ", width=70,
            ))
            lines.append("")

    if analysis.user_decisions_required:
        # Walk gaps directly for clean rendering (skip INFO_ONLY)
        decision_gaps = [
            g for g in analysis.gaps
            if g.severity.value != "info_only"
        ]
        if decision_gaps:
            lines.append(_line("─"))
            lines.append(f"DECISIONS NEEDED ({len(decision_gaps)})")
            lines.append(_line("─"))
            lines.append("")
            lines.append(
                "For each gap above, decide: ACCEPT the Practical compromise"
            )
            lines.append(
                "(skip the verification/upgrade) or UPGRADE to Code-Strict?"
            )
            lines.append("")
            for i, gap in enumerate(decision_gaps, 1):
                lines.append(
                    f"  {i}. {gap.check_id} "
                    f"({_format_gap_label(gap.severity.value)})"
                )
            lines.append("")

    # Cost delta
    if analysis.cost_delta_lakhs > 0:
        lines.append(
            f"Estimated cost to upgrade Practical → Code-Strict: "
            f"{_format_money_lakhs(analysis.cost_delta_lakhs)}"
        )
        lines.append(
            "(includes soil + water table verification + possible RWH "
            "installation; redesign cost not included)"
        )
        lines.append("")

    # ── 6. Unknowns ───────────────────────────────────────────────────
    if p.unknowns:
        lines.append(_line("─"))
        lines.append(f"VERIFICATION RECOMMENDED ({len(p.unknowns)} unknowns)")
        lines.append(_line("─"))
        lines.append("")
        for u in p.unknowns:
            lines.append(
                f"[{u.priority.value.upper()}] {u.field_name}"
            )
            if u.user_facing_question:
                # Wrap long questions
                q_text = f"Q: {u.user_facing_question}"
                lines.extend(_wrap_indented(q_text, indent="  ", width=70))
            if u.assumed_value:
                lines.append(f"  Currently assuming: {u.assumed_value}")
            if u.verification_recommendation:
                # Wrap long verification recs
                rec = u.verification_recommendation
                lines.extend(_wrap_indented(rec, indent="  ", width=70))
            lines.append("")

    # ── 7. Action steps ───────────────────────────────────────────────
    if p.action_steps:
        # Sort by priority (lowest = most urgent)
        sorted_actions = sorted(p.action_steps, key=lambda a: a.priority)
        lines.append(_line("─"))
        lines.append(f"ACTION STEPS ({len(sorted_actions)} items, sorted by priority)")
        lines.append(_line("─"))
        lines.append("")
        for i, action in enumerate(sorted_actions, 1):
            # First line: priority + step number
            head = f"  {i}. [P{action.priority}] "
            # Wrap the action text under the head
            wrapped = _wrap_indented(
                action.step_text, indent=" " * len(head), width=70,
            )
            if wrapped:
                # First wrapped line gets the head prefix
                wrapped[0] = head + wrapped[0].lstrip()
                lines.extend(wrapped)
            else:
                lines.append(head + action.step_text)
        lines.append("")

    # ── 8. Doubts appendix ────────────────────────────────────────────
    if include_doubts:
        doubts_lines = _render_doubts_appendix(p)
        if doubts_lines:
            lines.append(_line("─"))
            lines.append("FREQUENTLY ASKED QUESTIONS")
            lines.append(_line("─"))
            lines.append("")
            lines.extend(doubts_lines)

    # ── 9. Footer ─────────────────────────────────────────────────────
    lines.append(_line("="))
    lines.append("REPORT NOTES")
    lines.append(_line("="))
    lines.append(
        "• 'Practical' lane uses your stated preferences. 'Code-Strict' lane"
    )
    lines.append(
        "  applies full NBC + DCR compliance. Gaps show where you've made"
    )
    lines.append("  trade-offs.")
    lines.append(
        "• City-default soil/water table values are educated guesses.  Get"
    )
    lines.append(
        "  verified data (NABL labs, CGWB reports) for design-grade decisions."
    )
    lines.append(
        "• Assumes a rectangular plot with clear, surveyed legal boundaries"
    )
    lines.append(
        "  on a layout that has municipal approval. Irregular plots,"
    )
    lines.append(
        "  encroachments, or unapproved layouts require independent legal"
    )
    lines.append("  verification before any design work.")
    lines.append(
        "• This is a feasibility report, not architectural design or legal"
    )
    lines.append(
        "  advice. Always consult a licensed architect for build approval."
    )
    lines.append("")

    return "\n".join(lines)


# ─── Internal: lane details ──────────────────────────────────────────

def _render_lane_details(report: FeasibilityReport) -> list[str]:
    """Render the per-lane check details. Returns list of lines.

    Session K enhancements:
      - Each issue line carries a [CATEGORY] tag (drawback 11) so users
        can distinguish legal-risk from design-quality-risk at a glance.
      - SOFT_WARNs that were downgraded from HARD_FAIL are flagged
        [DOWNGRADED FROM HARD] (drawback 2) so users understand they
        could become real blockers once data is verified.
    """
    lines = []

    if report.blocking_issues:
        lines.append("")
        lines.append(f"  BLOCKING ({len(report.blocking_issues)}):")
        for issue in report.blocking_issues:
            cat = _format_check_category(issue)
            lines.append(f"    ✗ [{cat}] {issue.check_name}")
            lines.extend(_wrap_indented(issue.message, indent="      ", width=66))

    if report.soft_warnings:
        lines.append("")
        lines.append(f"  WARNINGS ({len(report.soft_warnings)}):")
        for warn in report.soft_warnings:
            cat = _format_check_category(warn)
            # Drawback 2 fix: flag downgraded HARDs prominently
            downgrade_tag = (
                " [DOWNGRADED FROM HARD]"
                if warn.details.get("downgrade_applied") else ""
            )
            lines.append(f"    ! [{cat}]{downgrade_tag} {warn.check_name}")
            lines.extend(_wrap_indented(warn.message, indent="      ", width=66))

    if report.passed_checks:
        lines.append("")
        lines.append(f"  PASSED ({len(report.passed_checks)}):")
        for check in report.passed_checks:
            cat = _format_check_category(check)
            lines.append(f"    ✓ [{cat}] {check.check_name}")

    if report.not_applicable_checks:
        lines.append("")
        lines.append(f"  NOT APPLICABLE ({len(report.not_applicable_checks)}):")
        for na in report.not_applicable_checks:
            lines.append(f"    - {na.check_name}: {na.message[:60]}")

    return lines


def _wrap_indented(text: str, indent: str = "", width: int = 70) -> list[str]:
    """Wrap text to width, prepending indent to each line.
    Simple word-based wrap — fine for our use."""
    words = text.split()
    if not words:
        return []
    lines = []
    current = indent
    for word in words:
        if len(current) + len(word) + 1 > width and current.strip():
            lines.append(current.rstrip())
            current = indent + word
        else:
            current = current + " " + word if current.strip() else current + word
    if current.strip():
        lines.append(current.rstrip())
    return lines


def _describe_floors(brief: Brief) -> str:
    """Brief floor stack description, e.g. 'G+1 residential + 1 basement'."""
    from collections import Counter
    use_counts = Counter()
    for f in brief.floors:
        use_str = f.floor_use.value if hasattr(f.floor_use, "value") else str(f.floor_use)
        use_counts[use_str] += 1
    parts = [f"{n} {use}" for use, n in use_counts.most_common()]
    return ", ".join(parts)


def _render_doubts_appendix(report: FeasibilityReport) -> list[str]:
    """Render the FAQ section. Groups doubts by check_id, only includes
    checks that have non-empty doubts."""
    lines = []
    seen_check_ids = set()
    for check in report.all_check_results:
        if not check.common_doubts:
            continue
        if check.check_id in seen_check_ids:
            continue
        seen_check_ids.add(check.check_id)
        lines.append(f"About: {check.check_name}")
        for doubt in check.common_doubts:
            lines.extend(_wrap_indented(doubt, indent="  ", width=70))
            lines.append("")
    return lines


# ─── JSON renderer ───────────────────────────────────────────────────

# Drawback 9 fix (Session K): label maps for JSON enrichment so frontend
# consumers don't need to ship their own enum-to-label dictionary. Raw
# enum values are kept as-is; labels are added alongside.

_CHECK_SEVERITY_LABEL = {
    "hard_fail":      "BLOCKING",
    "soft_warn":      "WARNING",
    "pass":           "OK",
    "not_applicable": "N/A",
}

_GAP_SEVERITY_LABEL = {
    "blocking_if_not_accepted": "DECISION NEEDED",
    "significant":              "SIGNIFICANT",
    "marginal":                 "MINOR",
    "info_only":                "INFO",
}


def render_json(analysis: DesignGapAnalysis) -> dict[str, Any]:
    """Convert DesignGapAnalysis to a JSON-serializable dict.

    All enums → .value strings. All dataclasses → dicts via asdict.
    Tuples → lists for JSON compatibility.

    Session K enhancement (drawback 9): every dict that has a 'severity'
    field also gets a 'severity_label' string with the human-readable
    form (BLOCKING / WARNING / DECISION NEEDED / etc.). Likewise every
    'category' gets a 'category_label'. This avoids forcing API
    consumers to ship their own enum-to-label dictionary.
    """
    raw = _to_json_dict(analysis)
    return _enrich_with_labels(raw)


def _enrich_with_labels(obj: Any) -> Any:
    """Walk the JSON dict and add severity_label / category_label fields
    next to severity / category fields. Leaves all other fields unchanged.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k] = _enrich_with_labels(v)
        # Add labels alongside raw values when the keys exist
        if "severity" in out and isinstance(out["severity"], str):
            # Distinguish gap severities from check severities by value
            sev = out["severity"]
            if sev in _GAP_SEVERITY_LABEL:
                out["severity_label"] = _GAP_SEVERITY_LABEL[sev]
            elif sev in _CHECK_SEVERITY_LABEL:
                out["severity_label"] = _CHECK_SEVERITY_LABEL[sev]
        if "category" in out and isinstance(out["category"], str):
            cat = out["category"]
            if cat in _CATEGORY_USER_LABEL:
                out["category_label"] = _CATEGORY_USER_LABEL[cat]
        return out
    if isinstance(obj, list):
        return [_enrich_with_labels(item) for item in obj]
    return obj


def _to_json_dict(obj: Any) -> Any:
    """Recursively convert any object to a JSON-friendly dict.

    Handles:
      - dataclasses → dict via field walking
      - enums → .value
      - tuples → lists
      - dicts → dicts (recursively)
      - other → as-is (str, int, float, bool, None)
    """
    if obj is None:
        return None
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        out = {}
        for f in fields(obj):
            out[f.name] = _to_json_dict(getattr(obj, f.name))
        return out
    if isinstance(obj, (list, tuple)):
        return [_to_json_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_json_dict(v) for k, v in obj.items()}
    # Primitives + other types
    return obj
