"""
BuildemUp† — Phased Construction Guidance (Component 1).

Per SPEC_v0.2 Section 5.3 (Drawback 9 fix):

When the user's budget is below 80% of the Component 7 estimate,
suggest phased construction — build ground floor now with columns
and foundation designed for future vertical expansion.

This is how many Indian middle-class families actually build. The
suggestion gives them a realistic path forward instead of just
flagging "your budget is too low."

Rough cost split (for ground-only estimate):
  - Foundation + ground slab + columns: ~55% of full structure cost
  - Upper floors (walls, slabs, steel above ground): ~45%
  These ratios are approximate. Component 7 v2 may expose stage-by-stage
  costs more precisely; for v0.1 we use the 55% rule of thumb.

This module produces guidance messages only — it does NOT re-run
Component 7 with a modified brief to compute ground-only cost exactly.
Doing that would double C7 runs per request (premature optimization
for v0.1).

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.domain.brief import (
    BudgetRange, CostEstimate, GuidanceMessage, GuidanceSeverity,
)


# Fraction of full G+N cost that ground floor alone accounts for.
# Includes foundation + ground slab + ground columns + upper columns
# (designed for future expansion but cast up to ground level).
GROUND_FLOOR_COST_FRACTION = 0.55


def suggest_phased_construction_if_needed(
    budget: BudgetRange,
    estimate: CostEstimate | None,
) -> list[GuidanceMessage]:
    """If budget is below 80% of estimate, suggest phased construction.

    Per SPEC_v0.2 Section 5.3:
    Message includes a rough estimate for ground-floor-only (55% of full)
    and explains that columns/foundation can be designed for future
    vertical expansion.

    Returns:
      List with one INFO message if budget < 80% of estimate, else [].
      (The STRONG_CONCERN about under-budget is emitted separately by
      budget_bridge.compare_budget_to_estimate; this module adds a
      constructive suggestion alongside it.)
    """
    if estimate is None:
        return []
    est_val = estimate.exact_value
    if budget.max_rupees >= est_val * 0.80:
        # Not under-budget by enough to trigger the phased suggestion.
        return []

    ground_only_cost = est_val * GROUND_FLOOR_COST_FRACTION
    return [GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=(
            f"Consider phased construction: build the ground floor now "
            f"(estimated ₹{ground_only_cost/100_000:.0f}L — about "
            f"{GROUND_FLOOR_COST_FRACTION*100:.0f}% of the full design), "
            f"with the foundation and columns designed for future "
            f"vertical expansion. Many Indian families build this way — "
            f"ground floor first, upper floors in 2-5 years when budget "
            f"allows. Your engineer can design columns to handle the "
            f"future load from day one."
        ),
        context="phased_construction",
        action_verb="Consider",
    )]
