"""
BuildemUp† — Budget Bridge (Component 1 → Component 7).

Per SPEC_v0.2 Section 5.1 (Drawback 4 fix):

Component 1 does NOT have its own cost engine. It delegates to Component 7's
cost module via this bridge, and wraps the result in CostEstimate.

This guarantees: the ₹ number Component 1 shows user = the ₹ number
Component 7 shows downstream. No trust loss from inconsistent numbers.

Trade-off accepted: Component 7 runs twice per end-to-end flow (once here
for budget guidance, once downstream for the real output). ~200ms overhead.
Acceptable for a brief-capture flow that takes minutes anyway.

Architecture notes:
  - Brief.to_structural_grid_input() handles the envelope + floor count
    translation (per Drawbacks 2 + 3).
  - This bridge module calls StructuralGridEngine().execute() and wraps
    the cost output.
  - On any failure, we degrade gracefully — return None for cost, emit
    a CONCERN message, don't crash.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import replace

from buildemup.domain.brief import (
    Brief, BudgetRange, CostEstimate,
    GuidanceMessage, GuidanceSeverity,
)
from buildemup.domain.plot import Plot
from buildemup.domain.setbacks import Setbacks
from buildemup.domain.floor_requirement import FloorUse


# IS 1893:2016 seismic zone per city — must match Component 7's launch cities.
# Chennai, Bangalore, Hyderabad → Zone II (low, Z=0.10)
# Mumbai, Pune                  → Zone III (moderate, Z=0.16)
# Delhi                         → Zone IV (high, Z=0.24)
CITY_TO_SEISMIC_ZONE: dict[str, str] = {
    "chennai":    "II",
    "bangalore":  "II",
    "hyderabad":  "II",
    "mumbai":     "III",
    "pune":       "III",
    "delhi":      "IV",
}


def get_seismic_zone_for_city(city: str) -> str:
    """Return IS 1893 seismic zone for a supported city.

    Falls back to Zone III (moderate, conservative) for unknown cities.
    Matches Component 7's launch scope (see Component 7 multicity tests).
    """
    return CITY_TO_SEISMIC_ZONE.get(city.lower().strip(), "III")


def call_component_7_for_cost(
    brief: Brief,
) -> tuple[CostEstimate | None, list[GuidanceMessage]]:
    """Run Component 7 on the brief's structural projection and extract cost.

    Returns:
        (cost_estimate, guidance_messages):
        - cost_estimate: CostEstimate, or None if Component 7 couldn't run
        - guidance_messages: any messages generated during the bridge call
          (errors during Component 7 call surface here as CONCERN)
    """
    messages: list[GuidanceMessage] = []
    # Import locally to avoid a circular-import risk during module load
    try:
        from buildemup.components.c07_structural_grid import (
            StructuralGridEngine,
        )
    except ImportError as e:
        messages.append(GuidanceMessage(
            severity=GuidanceSeverity.CONCERN,
            text=(
                "Could not load the cost engine for budget comparison. "
                "Your budget will be shown without a comparison estimate. "
                "(Technical: Component 7 import failed.)"
            ),
            context="budget_bridge_import_error",
            action_verb="Review",
        ))
        return None, messages

    try:
        sgi = brief.to_structural_grid_input()
    except (ValueError, TypeError) as e:
        messages.append(GuidanceMessage(
            severity=GuidanceSeverity.CONCERN,
            text=(
                f"Could not convert your brief for cost estimation. "
                f"Your budget will be shown without a comparison. "
                f"(Technical: {str(e)[:80]})"
            ),
            context="budget_bridge_conversion_error",
            action_verb="Review",
        ))
        return None, messages

    try:
        engine = StructuralGridEngine()
        result = engine.execute(sgi)
    except Exception as e:
        messages.append(GuidanceMessage(
            severity=GuidanceSeverity.CONCERN,
            text=(
                f"Cost engine did not complete — your budget will be "
                f"shown without a comparison. This can happen when the "
                f"brief has unusual inputs. You can still submit and "
                f"review the remaining output. "
                f"(Technical: {type(e).__name__}.)"
            ),
            context="budget_bridge_execute_error",
            action_verb="Review",
        ))
        return None, messages

    # Extract cost — Component 7 returns a TransparencyTriple with
    # exact_value, low, high, confidence (not range_min/range_max).
    try:
        c7_cost = result.cost
        cost_est = CostEstimate(
            exact_value=float(c7_cost.exact_value),
            range_min=float(c7_cost.low),
            range_max=float(c7_cost.high),
            confidence=str(
                getattr(c7_cost.confidence, "value", c7_cost.confidence)
            ),
            source="Component 7 structural + foundation cost engine",
        )
        return cost_est, messages
    except (AttributeError, ValueError, TypeError) as e:
        messages.append(GuidanceMessage(
            severity=GuidanceSeverity.CONCERN,
            text=(
                f"Cost engine ran but output shape was unexpected — "
                f"budget comparison skipped. "
                f"(Technical: {type(e).__name__}.)"
            ),
            context="budget_bridge_cost_extraction_error",
            action_verb="Review",
        ))
        return None, messages


def compare_budget_to_estimate(
    budget: BudgetRange, estimate: CostEstimate,
) -> list[GuidanceMessage]:
    """Generate soft-guide messages comparing user budget to C7 estimate.

    Per SPEC_v0.2 Section 5.2:
    - Budget max < 80% of estimate → STRONG_CONCERN (+ phased suggestion)
    - Budget within ±20% of estimate → INFO (aligns with typical)
    - Budget > 150% of estimate → INFO (generous, note finishes/margin)

    Note: phased construction suggestion is generated by a separate module
    (phased_construction.py). This function produces the budget comparison
    messages only.
    """
    if estimate is None:
        return []

    est_val = estimate.exact_value    # exact point estimate (INR)
    budget_max = budget.max_rupees
    budget_min = budget.min_rupees

    messages: list[GuidanceMessage] = []

    if budget_max < est_val * 0.80:
        # Under-budget: STRONG_CONCERN
        est_lakhs = est_val / 100_000
        messages.append(GuidanceMessage(
            severity=GuidanceSeverity.STRONG_CONCERN,
            text=(
                f"Your budget (₹{budget.min_lakhs}L–{budget.max_lakhs}L) "
                f"is below the ₹{est_lakhs:.0f}L estimated for this "
                f"design by the cost engine. Options: (a) reduce built "
                f"area, (b) choose basic finishes, (c) increase budget, "
                f"or (d) build in phases (see phased-construction "
                f"suggestion below)."
            ),
            context="budget_under_estimate",
            action_verb="Reconsider",
        ))
    elif budget_min > est_val * 1.50:
        # Generous: INFO
        est_lakhs = est_val / 100_000
        messages.append(GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                f"Your budget (₹{budget.min_lakhs}L–{budget.max_lakhs}L) "
                f"is generous for this design — estimated at ₹"
                f"{est_lakhs:.0f}L. You have room for premium finishes, "
                f"better windows, or margin for interior work later."
            ),
            context="budget_generous",
            action_verb="Consider",
        ))
    else:
        # Aligned (INFO)
        est_lakhs = est_val / 100_000
        messages.append(GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                f"Your budget (₹{budget.min_lakhs}L–{budget.max_lakhs}L) "
                f"is aligned with the ₹{est_lakhs:.0f}L estimate for "
                f"this design. Final cost depends on finishes and "
                f"your engineer's detailed design."
            ),
            context="budget_aligned",
            action_verb="Consider",
        ))

    return messages
