"""
BuildemUp† — Assumptions Log (Component 1).

Per SPEC_v0.2 Section 10.3 + Drawback 10 fix:

Tracks the assumptions Component 1 made during brief processing,
for display in the ASSUMPTIONS USED section of explain() output.

Why this matters (from v0.7 Transparency Triple principle):
  The system should never have hidden assumptions. Every implicit
  choice (floor height = 3m, rectangular envelope, circulation factor,
  etc.) must be visible to the user. Otherwise they can't evaluate
  whether our output matches their situation.

Rather than hard-coding a long string in the orchestrator, we build
up the list incrementally as Component 1 processes the brief. Each
sub-module adds its own entries.

†= placeholder name marker.
"""
from __future__ import annotations


# Default assumptions that apply to every Component 1 run.
DEFAULT_ASSUMPTIONS: tuple[str, ...] = (
    "Floor-to-floor height: 3.0m (NBC 2016 typical Indian residential).",
    "Buildable envelope assumed rectangular. Layout engine (later component) "
    "may refine shape for L/U-shaped plots.",
    "Circulation factor: 1.30 applied to sum(room areas) to estimate total "
    "floor area. Covers walls, passages, internal circulation.",
    "NBC 2016 Part 3 minimum room sizes used where user didn't specify.",
    "Construction cost estimated via Component 7 cost engine (basic finish "
    "for the plot's city).",
)


def build_assumptions_list(
    *,
    plot_type_label: str,
    vastu_tier_label: str,
    city: str,
    used_nbc_fallback: bool,
    auto_staircase_added: bool,
    circulation_factor_applied: float = 1.35,
    circulation_size_label: str = "typical",
    setback_rules_version: str = "unknown",
    setback_authority: str = "",
) -> tuple[str, ...]:
    """Assemble the full assumptions list for this brief.

    Per SPEC_v0.2 Section 10.3 + v0.9 + v0.9.1 fixes:
    - Circulation factor reports actual value and size band (v0.9 #5)
    - Net usable now disclosed as 80-90% range, not 85% point (v0.9.1 #3)
    - Setback rules tagged with KB version + authority for traceability
      (v0.9.1 #6 — visible audit trail)

    Args:
        plot_type_label: e.g., "detached", "continuous"
        vastu_tier_label: "off", "partial", or "full"
        city: normalized city string
        used_nbc_fallback: True if setback rules used NBC default
        auto_staircase_added: True if ensure_staircase_present added one
        circulation_factor_applied: actual factor used (1.30, 1.35, 1.40)
        circulation_size_label: "small", "typical", or "large"
        setback_rules_version: KB version string (v0.9.1 #6)
        setback_authority: human-readable authority (v0.9.1 #6)

    Returns:
        Tuple of assumption strings in display order.
    """
    # Build default assumptions inline so the circulation line reflects
    # the actual value applied (Drawback #5 v0.9) and net usable shows
    # as range (Drawback #3 v0.9.1).
    assumptions: list[str] = [
        "Floor-to-floor height: 3.0m (NBC 2016 typical Indian residential).",
        "Buildable envelope assumed rectangular. Net usable area shown as "
        "80-90% of gross envelope (range accounts for column grid, "
        "staircase, and unusable corners — varies by layout). "
        "Component 4 layout engine will compute actual usability.",
        f"Circulation factor: {circulation_factor_applied:.2f} applied to "
        f"sum(room areas) — size band '{circulation_size_label}' per "
        f"IS 3861-2002. Walls + horizontal + vertical circulation overhead. "
        f"Based on typical residential layouts.",
        "NBC 2016 Part 3 minimum room sizes used where user didn't specify.",
        "Construction cost estimated via Component 7 cost engine (city-"
        "specific rates, basic finish). All-in typically 2.5× structural "
        "(industry breakdown: structure 40%, finishing 25%, MEP 15%, "
        "interior 12%, misc 8%; source: AECORD 2026 + NBC industry guides).",
    ]

    # Plot type specifics
    if plot_type_label == "continuous":
        assumptions.append(
            "Continuous Building Area: side setbacks = 0 (plot shares "
            "both side walls with neighbours)."
        )
    elif plot_type_label == "semi_detached":
        assumptions.append(
            "Semi-detached plot: shared side has zero setback; other "
            "three sides follow detached-tier rules."
        )
    elif plot_type_label == "detached":
        assumptions.append(
            "Detached plot: full setbacks on all four sides."
        )

    # Setback source (v0.9.1: include KB version + authority for audit trail)
    auth_str = setback_authority or ("NBC 2016" if used_nbc_fallback else city)
    if used_nbc_fallback:
        assumptions.append(
            f"Setback rules: NBC 2016 general (city-specific DCR for "
            f"{city} coming in a later version — current rules are "
            f"conservative). KB version: {setback_rules_version}."
        )
    else:
        assumptions.append(
            f"Setback rules applied: {auth_str}. "
            f"KB version: {setback_rules_version}."
        )

    # Auto-staircase
    if auto_staircase_added:
        assumptions.append(
            "Staircase auto-added to satisfy multi-floor requirement "
            "(user did not specify one). NBC minimum 5.5 sqm used; "
            "user can override."
        )

    # Vastu tier
    if vastu_tier_label == "off":
        assumptions.append("Vastu guidance: OFF (user chose not to include).")
    elif vastu_tier_label == "partial":
        assumptions.append(
            "Vastu guidance: PARTIAL — 7 core items shown as informational "
            "guidance only (never blocking)."
        )
    elif vastu_tier_label == "full":
        assumptions.append(
            "Vastu guidance: FULL — 15+ items shown as informational "
            "guidance only (never blocking)."
        )

    return tuple(assumptions)
